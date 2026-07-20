import hashlib
import os
import re
import shutil
import tempfile
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import pyodbc
from flask import current_app
from PIL import Image, ImageOps
from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from sqlalchemy import text
from werkzeug.utils import secure_filename

from models import db


ALLOWED_EXPENSE_FILE_EXTENSIONS = {
    '.pdf',
    '.png',
    '.jpg',
    '.jpeg',
    '.webp',
    '.heic',
    '.heif',
}
EXCLUDED_EXPENSE_PLATES = {"24-ZF-99"}
PHC_CONVERSION_RATE = Decimal("200.482")
PHC_NOTES_FRAIS_NDOS = 120
PHC_NOTES_FRAIS_NMDOS = "Notes de Frais"

_schema_ready_databases: set[str] = set()


def _new_stamp() -> str:
    return uuid.uuid4().hex.upper()[:25]


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value or default)
    except Exception:
        return default


def _safe_decimal(value: Any) -> Decimal:
    raw = str(value if value is not None else '').strip().replace(',', '.')
    if not raw:
        return Decimal('0.00')
    try:
        return Decimal(raw).quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError):
        return Decimal('0.00')


def _safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or '').strip().lower() in {'1', 'true', 'on', 'yes', 'sim'}


def _phc_value(value: Any) -> Decimal:
    return (_safe_decimal(value) * PHC_CONVERSION_RATE).quantize(Decimal('0.00001'), rounding=ROUND_HALF_UP)


def _vat_amounts_from_gross(gross_value: Any, rate_value: Any) -> tuple[Decimal, Decimal]:
    gross = _safe_decimal(gross_value)
    rate = _safe_decimal(rate_value)
    if rate <= 0:
        return gross, Decimal('0.00')
    divisor = Decimal('1') + (rate / Decimal('100'))
    net = (gross / divisor).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    vat = (gross - net).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return net, vat


def _decimal_label(value: Any, places: int = 4) -> str:
    number = _safe_decimal(value)
    quant = Decimal('1') if number == number.to_integral_value() else Decimal('0.' + ('0' * max(0, places - 1)) + '1')
    label = format(number.quantize(quant, rounding=ROUND_HALF_UP), 'f')
    return label.rstrip('0').rstrip('.') if '.' in label else label


def _column_exists(table_name: str, column_name: str) -> bool:
    return bool(db.session.execute(text("""
        SELECT 1
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo'
          AND TABLE_NAME = :table_name
          AND COLUMN_NAME = :column_name
    """), {
        'table_name': table_name,
        'column_name': column_name,
    }).scalar())


def _existing_column(table_name: str, candidates: list[str]) -> str:
    rows = db.session.execute(text("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo'
          AND TABLE_NAME = :table_name
    """), {'table_name': table_name}).mappings().all()
    available = {
        str(row.get('COLUMN_NAME') or '').strip().upper(): str(row.get('COLUMN_NAME') or '').strip()
        for row in rows
    }
    for candidate in candidates:
        if candidate.upper() in available:
            return available[candidate.upper()]
    return ''


def _fe_phc_database_column() -> str:
    return _existing_column('FE', [
        'PHC_DATABASE', 'PHC_DB', 'DBPHC', 'BDPHC',
        'ERP_DATABASE', 'ERP_DB', 'DBERP', 'BDERP',
        'DATABASE_NAME', 'DB_NAME', 'DBNAME',
        'BASEDADOS', 'BASE_DADOS', 'BD', 'NOMEBD',
    ])


def _fe_phc_server_column() -> str:
    return _existing_column('FE', [
        'PHC_SERVER', 'SERVER_PHC', 'ERP_SERVER', 'SERVER_ERP',
        'SQLSERVER', 'SQL_SERVER', 'SERVIDOR', 'SERVER',
    ])


def _qident(name: str) -> str:
    return '[' + str(name or '').replace(']', ']]') + ']'


def _file_hash(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _conn_part(conn_str: str, key: str) -> str:
    match = re.search(rf"(?:^|;){re.escape(key)}=([^;]*)", conn_str or "", flags=re.IGNORECASE)
    return str(match.group(1) or "").strip() if match else ""


def _replace_conn_part(conn_str: str, key: str, value: str) -> str:
    clean_value = str(value or "").strip()
    if re.search(rf"(?:^|;){re.escape(key)}=", conn_str or "", flags=re.IGNORECASE):
        return re.sub(
            rf"((?:^|;){re.escape(key)}=)[^;]*",
            rf"\g<1>{clean_value}",
            conn_str,
            count=1,
            flags=re.IGNORECASE,
        )
    return conn_str.rstrip(";") + f";{key}={clean_value};"


def _client_conn_str() -> str:
    conn_map = current_app.config.get("DB_CONN_STRS") or {}
    client_conn = str(conn_map.get("client") or conn_map.get("default") or "").strip()
    if not client_conn:
        raise RuntimeError("Ligacao client/GR360_CORE nao configurada.")
    return client_conn


def _phc_conn_str(database_name: str, server_name: str = "") -> str:
    conn_str = _replace_conn_part(_client_conn_str(), "DATABASE", database_name)
    server = str(server_name or "").strip()
    if server:
        current_server = _conn_part(conn_str, "SERVER")
        port = ""
        if "," in current_server and "," not in server:
            port = current_server.split(",", 1)[1].strip()
        conn_str = _replace_conn_part(conn_str, "SERVER", f"{server},{port}" if port else server)
    return conn_str


def _phc_db_hint(company_name: str) -> str:
    key = re.sub(r"[^A-Z0-9]+", "", str(company_name or "").upper())
    if "FRANCE" in key or key.endswith("FR"):
        return "HSOLS_FR"
    if "PORTUGAL" in key or key.endswith("PT"):
        return "HSOLS_PT"
    if "ALLEMAGNE" in key or "ALEMANHA" in key or key.endswith("DE"):
        return "HSOLS_DE"
    if "MAROC" in key or "MARROC" in key or key.endswith("MA"):
        return "HSOLS_MA"
    if "INTERSOL" in key:
        return "INTERSOL"
    return ""


def ensure_colaborador_despesas_schema() -> None:
    try:
        database_name = str(db.session.execute(text('SELECT DB_NAME()')).scalar() or '').strip() or '__default__'
    except Exception:
        database_name = '__default__'
    if database_name in _schema_ready_databases:
        return

    db.session.execute(text("""
        IF OBJECT_ID('dbo.COLAB_DESPESA_CAB', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.COLAB_DESPESA_CAB (
                DESPCABSTAMP varchar(25) NOT NULL
                    CONSTRAINT PK_COLAB_DESPESA_CAB PRIMARY KEY,
                USSTAMP varchar(25) NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_CAB_USSTAMP DEFAULT '',
                LOGIN varchar(60) NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_CAB_LOGIN DEFAULT '',
                PENO int NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_CAB_PENO DEFAULT 0,
                PENOME nvarchar(160) NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_CAB_PENOME DEFAULT N'',
                PEFEID int NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_CAB_PEFEID DEFAULT 0,
                FEID int NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_CAB_FEID DEFAULT 0,
                EMPRESA nvarchar(200) NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_CAB_EMPRESA DEFAULT N'',
                PHC_DB varchar(128) NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_CAB_PHCDB DEFAULT '',
                PHC_SERVER varchar(128) NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_CAB_PHCSERVER DEFAULT '',
                ESTADO varchar(20) NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_CAB_ESTADO DEFAULT 'RASCUNHO',
                DTCRI datetime NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_CAB_DTCRI DEFAULT GETDATE(),
                DTALT datetime NULL,
                USERCRIACAO varchar(60) NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_CAB_USERCRI DEFAULT '',
                USERALTERACAO varchar(60) NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_CAB_USERALT DEFAULT ''
            );

            CREATE INDEX IX_COLAB_DESPESA_CAB_USER_ESTADO
                ON dbo.COLAB_DESPESA_CAB (USSTAMP, LOGIN, ESTADO, DTCRI DESC);
        END
    """))

    db.session.execute(text("""
        IF OBJECT_ID('dbo.COLAB_DESPESA_LINHA', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.COLAB_DESPESA_LINHA (
                DESPLINHASTAMP varchar(25) NOT NULL
                    CONSTRAINT PK_COLAB_DESPESA_LINHA PRIMARY KEY,
                DESPCABSTAMP varchar(25) NOT NULL,
                ORDEM int NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_LINHA_ORDEM DEFAULT 0,
                DATA_DESPESA date NULL,
                TIPO varchar(30) NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_LINHA_TIPO DEFAULT '',
                VALOR decimal(18,2) NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_LINHA_VALOR DEFAULT 0,
                KMS decimal(12,2) NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_LINHA_KMS DEFAULT 0,
                VIATURA varchar(50) NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_LINHA_VIATURA DEFAULT '',
                OBS nvarchar(100) NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_LINHA_OBS DEFAULT N'',
                DEVOLUCAO_OBS nvarchar(500) NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_LINHA_DEVOLUCAO_OBS DEFAULT N'',
                REF varchar(50) NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_LINHA_REF DEFAULT '',
                DESIGN nvarchar(200) NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_LINHA_DESIGN DEFAULT N'',
                CCUSTO varchar(80) NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_LINHA_CCUSTO DEFAULT '',
                FEID int NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_LINHA_FEID DEFAULT 0,
                EMPRESA nvarchar(200) NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_LINHA_EMPRESA DEFAULT N'',
                TABIVA int NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_LINHA_TABIVA DEFAULT 0,
                TAXAIVA decimal(9,4) NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_LINHA_TAXAIVA DEFAULT 0,
                VALOR_SEM_IVA decimal(18,2) NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_LINHA_VALSEMIVA DEFAULT 0,
                VALOR_IVA decimal(18,2) NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_LINHA_VALIVA DEFAULT 0,
                PAGO_CARTAO_CREDITO bit NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_LINHA_CARTAO DEFAULT 0,
                ESTADO varchar(20) NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_LINHA_ESTADO DEFAULT 'RASCUNHO',
                ANULADA bit NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_LINHA_ANULADA DEFAULT 0,
                FICHEIRO_ORIGINAL nvarchar(255) NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_LINHA_FORIG DEFAULT N'',
                FICHEIRO nvarchar(255) NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_LINHA_FICH DEFAULT N'',
                CAMINHO nvarchar(500) NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_LINHA_CAMINHO DEFAULT N'',
                MIME_TYPE varchar(120) NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_LINHA_MIME DEFAULT '',
                EXT varchar(20) NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_LINHA_EXT DEFAULT '',
                TAMANHO bigint NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_LINHA_TAMANHO DEFAULT 0,
                FILE_HASH varchar(64) NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_LINHA_HASH DEFAULT '',
                DTCRI datetime NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_LINHA_DTCRI DEFAULT GETDATE(),
                DTALT datetime NULL,
                USERCRIACAO varchar(60) NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_LINHA_USERCRI DEFAULT '',
                USERALTERACAO varchar(60) NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_LINHA_USERALT DEFAULT '',
                CONSTRAINT FK_COLAB_DESPESA_LINHA_CAB
                    FOREIGN KEY (DESPCABSTAMP)
                    REFERENCES dbo.COLAB_DESPESA_CAB (DESPCABSTAMP)
            );

            CREATE INDEX IX_COLAB_DESPESA_LINHA_CAB_ORDEM
                ON dbo.COLAB_DESPESA_LINHA (DESPCABSTAMP, ANULADA, ORDEM, DTCRI);
        END
    """))

    db.session.execute(text("""
        IF COL_LENGTH('dbo.COLAB_DESPESA_LINHA', 'FEID') IS NULL
        BEGIN
            ALTER TABLE dbo.COLAB_DESPESA_LINHA
            ADD FEID int NOT NULL
                CONSTRAINT DF_COLAB_DESPESA_LINHA_FEID DEFAULT 0;
        END
    """))
    db.session.execute(text("""
        IF COL_LENGTH('dbo.COLAB_DESPESA_LINHA', 'EMPRESA') IS NULL
        BEGIN
            ALTER TABLE dbo.COLAB_DESPESA_LINHA
            ADD EMPRESA nvarchar(200) NOT NULL
                CONSTRAINT DF_COLAB_DESPESA_LINHA_EMPRESA DEFAULT N'';
        END
    """))
    db.session.execute(text("""
        IF COL_LENGTH('dbo.COLAB_DESPESA_LINHA', 'REF') IS NULL
        BEGIN
            ALTER TABLE dbo.COLAB_DESPESA_LINHA
            ADD REF varchar(50) NOT NULL
                CONSTRAINT DF_COLAB_DESPESA_LINHA_REF DEFAULT '';
        END
    """))
    db.session.execute(text("""
        IF COL_LENGTH('dbo.COLAB_DESPESA_LINHA', 'DESIGN') IS NULL
        BEGIN
            ALTER TABLE dbo.COLAB_DESPESA_LINHA
            ADD DESIGN nvarchar(200) NOT NULL
                CONSTRAINT DF_COLAB_DESPESA_LINHA_DESIGN DEFAULT N'';
        END
    """))
    db.session.execute(text("""
        IF COL_LENGTH('dbo.COLAB_DESPESA_LINHA', 'CCUSTO') IS NULL
        BEGIN
            ALTER TABLE dbo.COLAB_DESPESA_LINHA
            ADD CCUSTO varchar(80) NOT NULL
                CONSTRAINT DF_COLAB_DESPESA_LINHA_CCUSTO DEFAULT '';
        END
    """))
    db.session.execute(text("""
        IF COL_LENGTH('dbo.COLAB_DESPESA_LINHA', 'TABIVA') IS NULL
        BEGIN
            ALTER TABLE dbo.COLAB_DESPESA_LINHA
            ADD TABIVA int NOT NULL
                CONSTRAINT DF_COLAB_DESPESA_LINHA_TABIVA DEFAULT 0;
        END
    """))
    db.session.execute(text("""
        IF COL_LENGTH('dbo.COLAB_DESPESA_LINHA', 'TAXAIVA') IS NULL
        BEGIN
            ALTER TABLE dbo.COLAB_DESPESA_LINHA
            ADD TAXAIVA decimal(9,4) NOT NULL
                CONSTRAINT DF_COLAB_DESPESA_LINHA_TAXAIVA DEFAULT 0;
        END
    """))
    db.session.execute(text("""
        IF COL_LENGTH('dbo.COLAB_DESPESA_LINHA', 'VALOR_SEM_IVA') IS NULL
        BEGIN
            ALTER TABLE dbo.COLAB_DESPESA_LINHA
            ADD VALOR_SEM_IVA decimal(18,2) NOT NULL
                CONSTRAINT DF_COLAB_DESPESA_LINHA_VALSEMIVA DEFAULT 0;
        END
    """))
    db.session.execute(text("""
        IF COL_LENGTH('dbo.COLAB_DESPESA_LINHA', 'VALOR_IVA') IS NULL
        BEGIN
            ALTER TABLE dbo.COLAB_DESPESA_LINHA
            ADD VALOR_IVA decimal(18,2) NOT NULL
                CONSTRAINT DF_COLAB_DESPESA_LINHA_VALIVA DEFAULT 0;
        END
    """))
    db.session.execute(text("""
        IF COL_LENGTH('dbo.COLAB_DESPESA_LINHA', 'PAGO_CARTAO_CREDITO') IS NULL
        BEGIN
            ALTER TABLE dbo.COLAB_DESPESA_LINHA
            ADD PAGO_CARTAO_CREDITO bit NOT NULL
                CONSTRAINT DF_COLAB_DESPESA_LINHA_CARTAO DEFAULT 0;
        END
    """))
    db.session.execute(text("""
        IF COL_LENGTH('dbo.COLAB_DESPESA_LINHA', 'DEVOLUCAO_OBS') IS NULL
        BEGIN
            ALTER TABLE dbo.COLAB_DESPESA_LINHA
            ADD DEVOLUCAO_OBS nvarchar(500) NOT NULL
                CONSTRAINT DF_COLAB_DESPESA_LINHA_DEVOLUCAO_OBS DEFAULT N'';
        END
    """))
    db.session.execute(text("""
        IF COL_LENGTH('dbo.COLAB_DESPESA_LINHA', 'PHC_STATUS') IS NULL
        BEGIN
            ALTER TABLE dbo.COLAB_DESPESA_LINHA
            ADD PHC_STATUS varchar(20) NOT NULL
                CONSTRAINT DF_COLAB_DESPESA_LINHA_PHC_STATUS DEFAULT '';
        END
    """))
    db.session.execute(text("""
        IF COL_LENGTH('dbo.COLAB_DESPESA_LINHA', 'PHC_BOSTAMP') IS NULL
        BEGIN
            ALTER TABLE dbo.COLAB_DESPESA_LINHA
            ADD PHC_BOSTAMP varchar(25) NOT NULL
                CONSTRAINT DF_COLAB_DESPESA_LINHA_PHC_BOSTAMP DEFAULT '';
        END
    """))
    db.session.execute(text("""
        IF COL_LENGTH('dbo.COLAB_DESPESA_LINHA', 'PHC_BISTAMP') IS NULL
        BEGIN
            ALTER TABLE dbo.COLAB_DESPESA_LINHA
            ADD PHC_BISTAMP varchar(25) NOT NULL
                CONSTRAINT DF_COLAB_DESPESA_LINHA_PHC_BISTAMP DEFAULT '';
        END
    """))
    db.session.execute(text("""
        IF COL_LENGTH('dbo.COLAB_DESPESA_LINHA', 'PHC_DTENVIO') IS NULL
        BEGIN
            ALTER TABLE dbo.COLAB_DESPESA_LINHA
            ADD PHC_DTENVIO datetime NULL;
        END
    """))
    db.session.execute(text("""
        IF COL_LENGTH('dbo.COLAB_DESPESA_LINHA', 'PHC_ERRO') IS NULL
        BEGIN
            ALTER TABLE dbo.COLAB_DESPESA_LINHA
            ADD PHC_ERRO nvarchar(500) NOT NULL
                CONSTRAINT DF_COLAB_DESPESA_LINHA_PHC_ERRO DEFAULT N'';
        END
    """))
    db.session.execute(text("""
        UPDATE L
        SET FEID = ISNULL(NULLIF(L.FEID, 0), H.FEID),
            EMPRESA = CASE
                WHEN LTRIM(RTRIM(ISNULL(L.EMPRESA, ''))) = '' THEN ISNULL(H.EMPRESA, '')
                ELSE L.EMPRESA
            END
        FROM dbo.COLAB_DESPESA_LINHA L
        INNER JOIN dbo.COLAB_DESPESA_CAB H
          ON H.DESPCABSTAMP = L.DESPCABSTAMP
        WHERE ISNULL(L.FEID, 0) = 0
           OR LTRIM(RTRIM(ISNULL(L.EMPRESA, ''))) = '';
    """))

    db.session.commit()
    _schema_ready_databases.add(database_name)


def _employee_has_company_credit_card(phc_db: str, phc_server: str, peno: int) -> bool:
    if not phc_db or not peno:
        return False
    try:
        with pyodbc.connect(_phc_conn_str(phc_db, phc_server), timeout=8) as conn:
            cursor = conn.cursor()
            row = cursor.execute("""
                SELECT TOP 1
                    CASE WHEN ISNULL(PE2.U_CARCRED, 0) <> 0 THEN 1 ELSE 0 END AS TEM_CARTAO_CREDITO
                FROM dbo.PE
                INNER JOIN dbo.PE2
                    ON PE.PESTAMP = PE2.PE2STAMP
                WHERE PE.NO = ?
            """, int(peno)).fetchone()
            return bool(row and row[0])
    except Exception:
        current_app.logger.exception('Erro ao verificar o cartão de crédito do colaborador na PE2.')
        return False


def get_colaborador_context(user) -> dict[str, Any]:
    userstamp = str(getattr(user, 'USSTAMP', '') or '').strip()
    login = str(getattr(user, 'LOGIN', '') or '').strip()
    phc_db_col = _fe_phc_database_column()
    phc_server_col = _fe_phc_server_column()
    phc_db_select = f"LTRIM(RTRIM(ISNULL(FE.{_qident(phc_db_col)}, ''))) AS PHC_DB" if phc_db_col else "CAST('' AS varchar(128)) AS PHC_DB"
    phc_server_select = f"LTRIM(RTRIM(ISNULL(FE.{_qident(phc_server_col)}, ''))) AS PHC_SERVER" if phc_server_col else "CAST('' AS varchar(128)) AS PHC_SERVER"
    row = db.session.execute(text(f"""
        SELECT TOP 1
            ISNULL(U.PENO, 0) AS PENO,
            LTRIM(RTRIM(ISNULL(U.PENOME, ''))) AS PENOME,
            ISNULL(U.PEFEID, 0) AS PEFEID,
            LTRIM(RTRIM(ISNULL(U.PEEMPRESA, ''))) AS PEEMPRESA,
            ISNULL(FE.FEID, 0) AS FEID,
            LTRIM(RTRIM(ISNULL(FE.NOME, ''))) AS FE_NOME,
            {phc_db_select},
            {phc_server_select}
        FROM dbo.US U
        LEFT JOIN dbo.FE FE
          ON FE.FEID = U.PEFEID
        WHERE (:userstamp <> '' AND U.USSTAMP = :userstamp)
           OR (:userstamp = '' AND U.LOGIN = :login)
    """), {
        'userstamp': userstamp,
        'login': login,
    }).mappings().first() or {}

    colaborador = {
        'userstamp': userstamp,
        'login': login,
        'peno': int(row.get('PENO') or 0),
        'penome': str(row.get('PENOME') or '').strip(),
        'pefeid': int(row.get('PEFEID') or 0),
        'feid': int(row.get('FEID') or 0),
        'empresa': str(row.get('FE_NOME') or row.get('PEEMPRESA') or '').strip(),
        'phc_db': str(row.get('PHC_DB') or '').strip(),
        'phc_server': str(row.get('PHC_SERVER') or '').strip(),
    }
    colaborador['tem_cartao_credito'] = _employee_has_company_credit_card(
        colaborador['phc_db'],
        colaborador['phc_server'],
        colaborador['peno'],
    )
    colaborador['completo'] = bool(
        colaborador['peno']
        and colaborador['penome']
        and colaborador['pefeid']
        and colaborador['phc_db']
    )
    return colaborador


def list_expense_companies() -> list[dict[str, Any]]:
    ensure_colaborador_despesas_schema()
    e_cluster_filter = "AND ISNULL(E_CLUSTER, 0) = 0" if _column_exists('FE', 'E_CLUSTER') else ""
    phc_db_col = _fe_phc_database_column()
    phc_server_col = _fe_phc_server_column()
    phc_db_select = f"LTRIM(RTRIM(ISNULL({_qident(phc_db_col)}, ''))) AS PHC_DB" if phc_db_col else "CAST('' AS varchar(128)) AS PHC_DB"
    phc_server_select = f"LTRIM(RTRIM(ISNULL({_qident(phc_server_col)}, ''))) AS PHC_SERVER" if phc_server_col else "CAST('' AS varchar(128)) AS PHC_SERVER"
    rows = db.session.execute(text(f"""
        SELECT
            ISNULL(FEID, 0) AS FEID,
            LTRIM(RTRIM(ISNULL(NOME, ''))) AS NOME,
            {phc_db_select},
            {phc_server_select}
        FROM dbo.FE
        WHERE ISNULL(FEID, 0) <> 0
          {e_cluster_filter}
        ORDER BY LTRIM(RTRIM(ISNULL(NOME, '')))
    """)).mappings().all()
    return [
        {
            'feid': int(row.get('FEID') or 0),
            'nome': str(row.get('NOME') or '').strip(),
            'phc_db': str(row.get('PHC_DB') or '').strip(),
            'phc_server': str(row.get('PHC_SERVER') or '').strip(),
        }
        for row in rows
        if int(row.get('FEID') or 0)
    ]


def _expense_company_by_feid(feid: int) -> dict[str, Any]:
    if not feid:
        return {}
    e_cluster_filter = "AND ISNULL(E_CLUSTER, 0) = 0" if _column_exists('FE', 'E_CLUSTER') else ""
    phc_db_col = _fe_phc_database_column()
    phc_server_col = _fe_phc_server_column()
    logo_col = _existing_column('FE', ['LOGOTIPO_PATH'])
    phc_db_select = f"LTRIM(RTRIM(ISNULL({_qident(phc_db_col)}, ''))) AS PHC_DB" if phc_db_col else "CAST('' AS varchar(128)) AS PHC_DB"
    phc_server_select = f"LTRIM(RTRIM(ISNULL({_qident(phc_server_col)}, ''))) AS PHC_SERVER" if phc_server_col else "CAST('' AS varchar(128)) AS PHC_SERVER"
    logo_select = f"LTRIM(RTRIM(ISNULL({_qident(logo_col)}, ''))) AS LOGOTIPO_PATH" if logo_col else "CAST('' AS varchar(500)) AS LOGOTIPO_PATH"
    row = db.session.execute(text(f"""
        SELECT TOP 1
            ISNULL(FEID, 0) AS FEID,
            LTRIM(RTRIM(ISNULL(NOME, ''))) AS NOME,
            {phc_db_select},
            {phc_server_select},
            {logo_select}
        FROM dbo.FE
        WHERE ISNULL(FEID, 0) = :feid
          {e_cluster_filter}
    """), {'feid': feid}).mappings().first()
    return {
        'feid': int(row.get('FEID') or 0),
        'nome': str(row.get('NOME') or '').strip(),
        'phc_db': str(row.get('PHC_DB') or '').strip(),
        'phc_server': str(row.get('PHC_SERVER') or '').strip(),
        'logo_path': str(row.get('LOGOTIPO_PATH') or '').strip(),
    } if row else {}


def _pick_column(columns: set[str], candidates: list[str]) -> str:
    for candidate in candidates:
        if candidate.upper() in columns:
            return candidate.upper()
    return ''


def _sql_identifier(name: str) -> str:
    return '[' + str(name or '').replace(']', ']]') + ']'


def list_expense_vat_rates(feid: int) -> list[dict[str, Any]]:
    ensure_colaborador_despesas_schema()
    company = _expense_company_by_feid(_safe_int(feid))
    phc_db = str(company.get('phc_db') or '').strip()
    if not phc_db:
        return []

    try:
        with pyodbc.connect(_phc_conn_str(phc_db, str(company.get('phc_server') or '').strip()), timeout=8) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT UPPER(COLUMN_NAME)
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = 'dbo'
                  AND TABLE_NAME = 'TAXASIVA'
            """)
            columns = {str(row[0] or '').strip().upper() for row in cursor.fetchall()}
            if not columns:
                return []

            code_col = _pick_column(columns, ['TABIVA', 'CODIGO', 'COD', 'CODIVA', 'ID'])
            rate_col = _pick_column(columns, ['TAXAIVA', 'TAXA', 'PERCENTAGEM', 'VALOR'])
            desc_col = _pick_column(columns, ['DESCRICAO', 'DESCR', 'NOME', 'DESIGN'])
            inactive_col = _pick_column(columns, ['INACTIVO', 'INATIVO'])
            if not code_col or not rate_col:
                return []

            desc_expr = f"LTRIM(RTRIM(ISNULL(CONVERT(varchar(160), {_sql_identifier(desc_col)}), '')))" if desc_col else "CAST('' AS varchar(160))"
            inactive_filter = f"AND ISNULL({_sql_identifier(inactive_col)}, 0) = 0" if inactive_col else ""
            cursor.execute(f"""
                SELECT TOP 100
                    CONVERT(varchar(30), {_sql_identifier(code_col)}) AS TABIVA,
                    TRY_CONVERT(decimal(9,4), {_sql_identifier(rate_col)}) AS TAXAIVA,
                    {desc_expr} AS DESCRICAO
                FROM dbo.TAXASIVA
                WHERE {_sql_identifier(code_col)} IS NOT NULL
                  {inactive_filter}
                ORDER BY TRY_CONVERT(int, {_sql_identifier(code_col)}), {_sql_identifier(code_col)}
            """)
            rows = cursor.fetchall()
    except Exception:
        current_app.logger.exception('Erro ao obter taxas de IVA da TAXASIVA do PHC.')
        return []

    rates: list[dict[str, Any]] = []
    for row in rows:
        tabiva = str(row.TABIVA or '').strip()
        taxaiva = _safe_decimal(row.TAXAIVA)
        descricao = str(row.DESCRICAO or '').strip()
        if not tabiva:
            continue
        label_parts = [tabiva, f"{_decimal_label(taxaiva)}%"]
        if descricao:
            label_parts.append(descricao)
        rates.append({
            'tabiva': tabiva,
            'taxaiva': float(taxaiva),
            'descricao': descricao,
            'label': ' · '.join(label_parts),
        })
    return rates


def list_expense_cost_centers(limit: int = 500) -> list[str]:
    ensure_colaborador_despesas_schema()
    if not db.session.execute(text("SELECT OBJECT_ID('dbo.V_CCT', 'V')")).scalar():
        return []
    safe_limit = max(1, min(int(limit or 500), 1000))
    rows = db.session.execute(text("""
        SELECT DISTINCT TOP """ + str(safe_limit) + """
            LTRIM(RTRIM(ISNULL(CCUSTO, ''))) AS CCUSTO
        FROM dbo.V_CCT
        WHERE LTRIM(RTRIM(ISNULL(CCUSTO, ''))) <> ''
        ORDER BY LTRIM(RTRIM(ISNULL(CCUSTO, '')))
    """)).mappings().all()
    return [str(row.get('CCUSTO') or '').strip() for row in rows if str(row.get('CCUSTO') or '').strip()]


def search_expense_articles(feid: int, term: str, limit: int = 12) -> list[dict[str, Any]]:
    ensure_colaborador_despesas_schema()
    clean_term = str(term or '').strip()
    if len(clean_term) < 1:
        return []
    safe_limit = max(1, min(int(limit or 12), 30))
    unidade_select = "LTRIM(RTRIM(ISNULL(S.UNIDADE, ''))) AS UNIDADE," if _column_exists('ST', 'UNIDADE') else "CAST('' AS varchar(20)) AS UNIDADE,"
    base_sql = f"""
        SELECT TOP {safe_limit}
            LTRIM(RTRIM(ISNULL(S.REF, ''))) AS REF,
            LTRIM(RTRIM(ISNULL(S.DESIGN, ''))) AS DESIGN,
            {unidade_select}
            LTRIM(RTRIM(ISNULL(S.FAMILIA, ''))) AS FAMILIA
        FROM dbo.ST S
        WHERE (
            LTRIM(RTRIM(ISNULL(S.REF, ''))) LIKE :term
            OR LTRIM(RTRIM(ISNULL(S.DESIGN, ''))) LIKE :term
        )
        {{feid_filter}}
        ORDER BY LTRIM(RTRIM(ISNULL(S.REF, '')))
    """
    params = {'term': f'%{clean_term}%'}
    clean_feid = _safe_int(feid)
    rows = []
    if clean_feid:
        scoped_params = {**params, 'feid': clean_feid}
        rows = db.session.execute(text(base_sql.replace('{feid_filter}', 'AND ISNULL(S.FEID, 0) = :feid')), scoped_params).mappings().all()
    if not rows:
        rows = db.session.execute(text(base_sql.replace('{feid_filter}', '')), params).mappings().all()
    return [
        {
            'ref': str(row.get('REF') or '').strip(),
            'design': str(row.get('DESIGN') or '').strip(),
            'unidade': str(row.get('UNIDADE') or '').strip(),
            'familia': str(row.get('FAMILIA') or '').strip(),
        }
        for row in rows
    ]


def search_expense_vehicles(term: str, limit: int = 12) -> list[dict[str, Any]]:
    ensure_colaborador_despesas_schema()
    clean_term = str(term or '').strip()
    if len(clean_term) < 1:
        return []
    if not db.session.execute(text("SELECT OBJECT_ID('dbo.VA', 'U')")).scalar():
        return []
    safe_limit = max(1, min(int(limit or 12), 30))
    excluded_sql = ", ".join(f"'{plate}'" for plate in sorted(EXCLUDED_EXPENSE_PLATES))
    cols = {
        str(row.get('COLUMN_NAME') or '').strip().upper()
        for row in db.session.execute(text("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'dbo'
              AND TABLE_NAME = 'VA'
        """)).mappings().all()
    }
    marca_select = "LTRIM(RTRIM(ISNULL(MARCA, ''))) AS MARCA" if 'MARCA' in cols else "CAST('' AS varchar(80)) AS MARCA"
    modelo_select = "LTRIM(RTRIM(ISNULL(MODELO, ''))) AS MODELO" if 'MODELO' in cols else "CAST('' AS varchar(80)) AS MODELO"
    nofrota_select = "LTRIM(RTRIM(ISNULL(NOFROTA, ''))) AS NOFROTA" if 'NOFROTA' in cols else "CAST('' AS varchar(80)) AS NOFROTA"
    inactive_filter = "AND ISNULL(INATIVO, 0) = 0" if 'INATIVO' in cols else ""
    search_parts = ["LTRIM(RTRIM(ISNULL(MATRICULA, ''))) LIKE :term"]
    if 'MARCA' in cols:
        search_parts.append("LTRIM(RTRIM(ISNULL(MARCA, ''))) LIKE :term")
    if 'MODELO' in cols:
        search_parts.append("LTRIM(RTRIM(ISNULL(MODELO, ''))) LIKE :term")
    if 'NOFROTA' in cols:
        search_parts.append("LTRIM(RTRIM(ISNULL(NOFROTA, ''))) LIKE :term")
    rows = db.session.execute(text(f"""
        SELECT TOP {safe_limit}
            LTRIM(RTRIM(ISNULL(MATRICULA, ''))) AS MATRICULA,
            {marca_select},
            {modelo_select},
            {nofrota_select}
        FROM dbo.VA
        WHERE LTRIM(RTRIM(ISNULL(MATRICULA, ''))) <> ''
          AND UPPER(LTRIM(RTRIM(ISNULL(MATRICULA, '')))) NOT IN ({excluded_sql})
          {inactive_filter}
          AND ({' OR '.join(search_parts)})
        ORDER BY LTRIM(RTRIM(ISNULL(MATRICULA, '')))
    """), {
        'term': f'%{clean_term}%',
    }).mappings().all()
    return [
        {
            'matricula': str(row.get('MATRICULA') or '').strip(),
            'marca': str(row.get('MARCA') or '').strip(),
            'modelo': str(row.get('MODELO') or '').strip(),
            'nofrota': str(row.get('NOFROTA') or '').strip(),
        }
        for row in rows
    ]


def _pe_default_ccusto(phc_db: str, phc_server: str, peno: int) -> str:
    database_name = str(phc_db or '').strip()
    if not database_name or not peno:
        return ''
    try:
        with pyodbc.connect(_phc_conn_str(database_name, phc_server), timeout=8) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT TOP 1 LTRIM(RTRIM(ISNULL(CONVERT(varchar(80), ccusto), ''))) FROM dbo.PE WHERE no = ?", int(peno))
            row = cursor.fetchone()
            return str(row[0] or '').strip() if row else ''
    except Exception:
        current_app.logger.exception('Erro ao obter CCUSTO por defeito da PE.')
        return ''


def get_or_create_draft_header(user) -> dict[str, Any]:
    ensure_colaborador_despesas_schema()
    colaborador = get_colaborador_context(user)
    header = db.session.execute(text("""
        SELECT TOP 1 *
        FROM dbo.COLAB_DESPESA_CAB
        WHERE ESTADO = 'RASCUNHO'
          AND (
            (:userstamp <> '' AND USSTAMP = :userstamp)
            OR (:userstamp = '' AND LOGIN = :login)
          )
        ORDER BY DTCRI DESC
    """), {
        'userstamp': colaborador['userstamp'],
        'login': colaborador['login'],
    }).mappings().first()
    if header:
        return {'header': dict(header), 'colaborador': colaborador}

    stamp = _new_stamp()
    db.session.execute(text("""
        INSERT INTO dbo.COLAB_DESPESA_CAB
        (DESPCABSTAMP, USSTAMP, LOGIN, PENO, PENOME, PEFEID, FEID, EMPRESA, PHC_DB, PHC_SERVER,
         ESTADO, USERCRIACAO, USERALTERACAO)
        VALUES
        (:stamp, :userstamp, :login, :peno, :penome, :pefeid, :feid, :empresa, :phc_db, :phc_server,
         'RASCUNHO', :login, :login)
    """), {
        'stamp': stamp,
        'userstamp': colaborador['userstamp'],
        'login': colaborador['login'],
        'peno': colaborador['peno'],
        'penome': colaborador['penome'],
        'pefeid': colaborador['pefeid'],
        'feid': colaborador['feid'],
        'empresa': colaborador['empresa'],
        'phc_db': colaborador['phc_db'],
        'phc_server': colaborador['phc_server'],
    })
    db.session.commit()
    header = db.session.execute(text("""
        SELECT TOP 1 *
        FROM dbo.COLAB_DESPESA_CAB
        WHERE DESPCABSTAMP = :stamp
    """), {'stamp': stamp}).mappings().first()
    return {'header': dict(header or {}), 'colaborador': colaborador}


def _user_header_scope_sql() -> str:
    return """
        EXISTS (
            SELECT 1
            FROM dbo.COLAB_DESPESA_CAB H
            WHERE H.DESPCABSTAMP = L.DESPCABSTAMP
              AND H.ESTADO = 'RASCUNHO'
              AND (
                (:userstamp <> '' AND H.USSTAMP = :userstamp)
                OR (:userstamp = '' AND H.LOGIN = :login)
              )
        )
    """


def list_draft_lines(header_stamp: str) -> list[dict[str, Any]]:
    ensure_colaborador_despesas_schema()
    rows = db.session.execute(text("""
        SELECT *
        FROM dbo.COLAB_DESPESA_LINHA
        WHERE DESPCABSTAMP = :header_stamp
          AND ISNULL(ANULADA, 0) = 0
          AND ESTADO IN ('RASCUNHO', 'FECHADO')
        ORDER BY ORDEM, DTCRI
    """), {'header_stamp': str(header_stamp or '').strip()}).mappings().all()
    return [serialize_line(row) for row in rows]


def list_expense_processing_users() -> list[dict[str, Any]]:
    ensure_colaborador_despesas_schema()
    rows = db.session.execute(text("""
        SELECT
            LTRIM(RTRIM(ISNULL(H.LOGIN, ''))) AS LOGIN,
            LTRIM(RTRIM(ISNULL(H.PENOME, ''))) AS PENOME,
            ISNULL(H.PENO, 0) AS PENO,
            COUNT(1) AS TOTAL
        FROM dbo.COLAB_DESPESA_LINHA L
        INNER JOIN dbo.COLAB_DESPESA_CAB H
          ON H.DESPCABSTAMP = L.DESPCABSTAMP
        WHERE ISNULL(L.ANULADA, 0) = 0
          AND UPPER(LTRIM(RTRIM(ISNULL(L.ESTADO, '')))) = 'FECHADO'
        GROUP BY
            LTRIM(RTRIM(ISNULL(H.LOGIN, ''))),
            LTRIM(RTRIM(ISNULL(H.PENOME, ''))),
            ISNULL(H.PENO, 0)
        ORDER BY LTRIM(RTRIM(ISNULL(H.PENOME, ''))), LTRIM(RTRIM(ISNULL(H.LOGIN, '')))
    """)).mappings().all()
    return [
        {
            'login': str(row.get('LOGIN') or '').strip(),
            'nome': str(row.get('PENOME') or row.get('LOGIN') or '').strip(),
            'peno': int(row.get('PENO') or 0),
            'total': int(row.get('TOTAL') or 0),
        }
        for row in rows
    ]


def list_expenses_for_processing(filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    ensure_colaborador_despesas_schema()
    filters = filters or {}
    clauses = [
        "ISNULL(L.ANULADA, 0) = 0",
        "UPPER(LTRIM(RTRIM(ISNULL(L.ESTADO, '')))) = 'FECHADO'",
        "LTRIM(RTRIM(ISNULL(L.PHC_BOSTAMP, ''))) = ''",
    ]
    params: dict[str, Any] = {}
    date_from = str(filters.get('date_from') or '').strip()
    date_to = str(filters.get('date_to') or '').strip()
    user_login = str(filters.get('user') or filters.get('login') or '').strip()
    if date_from:
        clauses.append("L.DATA_DESPESA >= TRY_CONVERT(date, :date_from)")
        params['date_from'] = date_from
    if date_to:
        clauses.append("L.DATA_DESPESA <= TRY_CONVERT(date, :date_to)")
        params['date_to'] = date_to
    if user_login:
        clauses.append("LTRIM(RTRIM(ISNULL(H.LOGIN, ''))) = :user_login")
        params['user_login'] = user_login
    where_sql = " AND ".join(clauses)
    rows = db.session.execute(text(f"""
        SELECT
            L.*,
            H.USSTAMP,
            H.LOGIN,
            H.PENO,
            H.PENOME,
            H.PEFEID,
            H.PHC_DB,
            H.PHC_SERVER,
            ISNULL(NULLIF(L.FEID, 0), H.FEID) AS LINHA_FEID,
            COALESCE(NULLIF(L.EMPRESA, ''), H.EMPRESA, '') AS LINHA_EMPRESA
        FROM dbo.COLAB_DESPESA_LINHA L
        INNER JOIN dbo.COLAB_DESPESA_CAB H
          ON H.DESPCABSTAMP = L.DESPCABSTAMP
        WHERE {where_sql}
        ORDER BY L.DATA_DESPESA DESC, H.PENOME, L.DTCRI DESC
    """), params).mappings().all()

    items: list[dict[str, Any]] = []
    ccusto_cache: dict[tuple[str, str, int], str] = {}
    for row in rows:
        item = serialize_line(row)
        ccusto = str(item.get('ccusto') or '').strip()
        if not ccusto:
            cache_key = (
                str(row.get('PHC_DB') or '').strip(),
                str(row.get('PHC_SERVER') or '').strip(),
                int(row.get('PENO') or 0),
            )
            if cache_key not in ccusto_cache:
                ccusto_cache[cache_key] = _pe_default_ccusto(cache_key[0], cache_key[1], cache_key[2])
            ccusto = ccusto_cache.get(cache_key, '')
        item.update({
            'userstamp': str(row.get('USSTAMP') or '').strip(),
            'login': str(row.get('LOGIN') or '').strip(),
            'peno': int(row.get('PENO') or 0),
            'penome': str(row.get('PENOME') or '').strip(),
            'pefeid': int(row.get('PEFEID') or 0),
            'feid': int(row.get('LINHA_FEID') or item.get('feid') or 0),
            'empresa': str(row.get('LINHA_EMPRESA') or item.get('empresa') or '').strip(),
            'phc_db': str(row.get('PHC_DB') or '').strip(),
            'phc_server': str(row.get('PHC_SERVER') or '').strip(),
            'ccusto': ccusto,
        })
        items.append(item)
    return items


def serialize_line(row: dict[str, Any]) -> dict[str, Any]:
    data_value = row.get('DATA_DESPESA')
    if isinstance(data_value, date):
        data_value = data_value.isoformat()
    file_path = str(row.get('CAMINHO') or '').strip()
    return {
        'stamp': str(row.get('DESPLINHASTAMP') or '').strip(),
        'header_stamp': str(row.get('DESPCABSTAMP') or '').strip(),
        'ordem': int(row.get('ORDEM') or 0),
        'data_despesa': str(data_value or '').strip(),
        'tipo': str(row.get('TIPO') or '').strip(),
        'valor': float(row.get('VALOR') or 0),
        'kms': float(row.get('KMS') or 0),
        'viatura': str(row.get('VIATURA') or '').strip(),
        'obs': str(row.get('OBS') or '').strip(),
        'devolucao_obs': str(row.get('DEVOLUCAO_OBS') or '').strip(),
        'ref': str(row.get('REF') or '').strip(),
        'design': str(row.get('DESIGN') or '').strip(),
        'ccusto': str(row.get('CCUSTO') or '').strip(),
        'feid': int(row.get('FEID') or 0),
        'empresa': str(row.get('EMPRESA') or '').strip(),
        'tabiva': str(row.get('TABIVA') or '').strip(),
        'taxaiva': float(row.get('TAXAIVA') or 0),
        'valor_sem_iva': float(row.get('VALOR_SEM_IVA') or 0),
        'valor_iva': float(row.get('VALOR_IVA') or 0),
        'pago_cartao_credito': bool(row.get('PAGO_CARTAO_CREDITO') or False),
        'phc_status': str(row.get('PHC_STATUS') or '').strip(),
        'phc_bostamp': str(row.get('PHC_BOSTAMP') or '').strip(),
        'phc_bistamp': str(row.get('PHC_BISTAMP') or '').strip(),
        'estado': str(row.get('ESTADO') or '').strip(),
        'file_original': str(row.get('FICHEIRO_ORIGINAL') or '').strip(),
        'file_name': str(row.get('FICHEIRO') or '').strip(),
        'file_path': file_path,
        'file_url': _expense_public_file_url(file_path),
        'mime_type': str(row.get('MIME_TYPE') or '').strip(),
        'file_ext': str(row.get('EXT') or '').strip(),
        'file_size': int(row.get('TAMANHO') or 0),
    }


def _store_line_file(file_storage, header_stamp: str, line_stamp: str) -> dict[str, Any]:
    original_name = secure_filename(str(getattr(file_storage, 'filename', '') or '').strip())
    if not original_name:
        raise ValueError('Nome de ficheiro inválido.')
    _, ext = os.path.splitext(original_name)
    ext = ext.lower().strip()
    if ext not in ALLOWED_EXPENSE_FILE_EXTENSIONS:
        raise ValueError(f'Extensão {ext or "(sem extensão)"} não suportada.')

    relative_dir = os.path.join('static', 'uploads', 'colaborador_despesas', header_stamp)
    absolute_dir = os.path.join(current_app.root_path, relative_dir)
    os.makedirs(absolute_dir, exist_ok=True)
    safe_name = f'{line_stamp}{ext}'
    absolute_path = os.path.join(absolute_dir, safe_name)
    file_storage.save(absolute_path)
    return {
        'original': original_name,
        'name': safe_name,
        'path': f'/{relative_dir.replace(os.sep, "/")}/{safe_name}',
        'mime': str(getattr(file_storage, 'mimetype', '') or '').strip(),
        'ext': ext,
        'size': os.path.getsize(absolute_path),
        'hash': _file_hash(absolute_path),
    }


def upsert_expense_line(user, payload: dict[str, Any], file_storage=None) -> dict[str, Any]:
    draft = get_or_create_draft_header(user)
    header = draft.get('header') or {}
    header_stamp = str(header.get('DESPCABSTAMP') or '').strip()
    colaborador = draft.get('colaborador') or {}
    login = str(colaborador.get('login') or '').strip()
    userstamp = str(colaborador.get('userstamp') or '').strip()
    line_stamp = str(payload.get('stamp') or payload.get('line_stamp') or '').strip()
    is_new = not line_stamp
    if is_new:
        line_stamp = _new_stamp()
        ordem = _safe_int(db.session.execute(text("""
            SELECT ISNULL(MAX(ORDEM), 0) + 10
            FROM dbo.COLAB_DESPESA_LINHA
            WHERE DESPCABSTAMP = :header_stamp
        """), {'header_stamp': header_stamp}).scalar(), 10)
        db.session.execute(text("""
            INSERT INTO dbo.COLAB_DESPESA_LINHA
            (DESPLINHASTAMP, DESPCABSTAMP, ORDEM, FEID, EMPRESA, USERCRIACAO, USERALTERACAO)
            VALUES (:stamp, :header_stamp, :ordem, :feid, :empresa, :login, :login)
        """), {
            'stamp': line_stamp,
            'header_stamp': header_stamp,
            'ordem': ordem,
            'feid': int(header.get('FEID') or colaborador.get('feid') or colaborador.get('pefeid') or 0),
            'empresa': str(header.get('EMPRESA') or colaborador.get('empresa') or '').strip(),
            'login': login,
        })
    else:
        existing = db.session.execute(text(f"""
            SELECT TOP 1 L.DESPLINHASTAMP, L.ESTADO
            FROM dbo.COLAB_DESPESA_LINHA L
            WHERE L.DESPLINHASTAMP = :stamp
              AND {_user_header_scope_sql()}
        """), {
            'stamp': line_stamp,
            'userstamp': userstamp,
            'login': login,
        }).mappings().first()
        if not existing:
            raise ValueError('Despesa não encontrada.')
        if str(existing.get('ESTADO') or '').strip().upper() != 'RASCUNHO':
            raise ValueError('Despesa fechada.')

    file_payload = None
    if file_storage:
        file_payload = _store_line_file(file_storage, header_stamp, line_stamp)

    data_despesa = str(payload.get('data_despesa') or '').strip() or None
    tipo = str(payload.get('tipo') or '').strip().upper()[:30]
    valor = _safe_decimal(payload.get('valor'))
    kms = _safe_decimal(payload.get('kms'))
    viatura = str(payload.get('viatura') or '').strip()[:50]
    obs = str(payload.get('obs') or '').strip()[:100]
    pago_cartao_credito = _safe_bool(payload.get('pago_cartao_credito')) and bool(colaborador.get('tem_cartao_credito'))
    line_feid = _safe_int(payload.get('feid') or payload.get('empresa_feid'))
    if not line_feid:
        line_feid = _safe_int(header.get('FEID') or colaborador.get('feid') or colaborador.get('pefeid'))
    company = _expense_company_by_feid(line_feid) if line_feid else {}
    if not company and line_feid:
        raise ValueError('Empresa inválida para despesas.')
    empresa = str(company.get('nome') or header.get('EMPRESA') or colaborador.get('empresa') or '').strip()[:200]

    params = {
        'stamp': line_stamp,
        'data_despesa': data_despesa,
        'tipo': tipo,
        'valor': valor,
        'kms': kms,
        'viatura': viatura,
        'obs': obs,
        'pago_cartao_credito': pago_cartao_credito,
        'feid': int(company.get('feid') or line_feid or 0),
        'empresa': empresa,
        'login': login,
    }
    file_sql = ''
    if file_payload:
        file_sql = """,
            FICHEIRO_ORIGINAL = :file_original,
            FICHEIRO = :file_name,
            CAMINHO = :file_path,
            MIME_TYPE = :mime_type,
            EXT = :file_ext,
            TAMANHO = :file_size,
            FILE_HASH = :file_hash
        """
        params.update({
            'file_original': file_payload['original'],
            'file_name': file_payload['name'],
            'file_path': file_payload['path'],
            'mime_type': file_payload['mime'],
            'file_ext': file_payload['ext'],
            'file_size': file_payload['size'],
            'file_hash': file_payload['hash'],
        })

    db.session.execute(text(f"""
        UPDATE dbo.COLAB_DESPESA_LINHA
        SET DATA_DESPESA = TRY_CONVERT(date, :data_despesa),
            TIPO = :tipo,
            VALOR = :valor,
            KMS = :kms,
            VIATURA = :viatura,
            OBS = :obs,
            PAGO_CARTAO_CREDITO = :pago_cartao_credito,
            FEID = :feid,
            EMPRESA = :empresa,
            ESTADO = 'RASCUNHO',
            ANULADA = 0,
            DTALT = GETDATE(),
            USERALTERACAO = :login
            {file_sql}
        WHERE DESPLINHASTAMP = :stamp
    """), params)
    db.session.execute(text("""
        UPDATE dbo.COLAB_DESPESA_CAB
        SET DTALT = GETDATE(),
            USERALTERACAO = :login
        WHERE DESPCABSTAMP = :header_stamp
    """), {
        'header_stamp': header_stamp,
        'login': login,
    })
    db.session.commit()

    row = db.session.execute(text("""
        SELECT TOP 1 *
        FROM dbo.COLAB_DESPESA_LINHA
        WHERE DESPLINHASTAMP = :stamp
    """), {'stamp': line_stamp}).mappings().first()
    return {
        'ok': True,
        'created': is_new,
        'header_stamp': header_stamp,
        'line': serialize_line(row or {}),
    }


def update_expense_processing_classification(line_stamp: str, payload: dict[str, Any], user) -> dict[str, Any]:
    ensure_colaborador_despesas_schema()
    stamp = str(line_stamp or payload.get('stamp') or '').strip()
    if not stamp:
        raise ValueError('Despesa inválida.')

    feid = _safe_int(payload.get('feid') or payload.get('empresa_feid'))
    company = _expense_company_by_feid(feid) if feid else {}
    if feid and not company:
        raise ValueError('Empresa inválida.')

    login = str(getattr(user, 'LOGIN', '') or getattr(user, 'login', '') or '').strip()
    params = {
        'stamp': stamp,
        'viatura': str(payload.get('viatura') or payload.get('matricula') or '').strip()[:50],
        'ref': str(payload.get('ref') or '').strip()[:50],
        'design': str(payload.get('design') or '').strip()[:200],
        'ccusto': str(payload.get('ccusto') or '').strip()[:80],
        'feid': int(company.get('feid') or feid or 0),
        'empresa': str(company.get('nome') or payload.get('empresa') or '').strip()[:200],
        'login': login,
    }
    if not params['feid']:
        current = db.session.execute(text("""
            SELECT TOP 1
                ISNULL(L.FEID, 0) AS FEID,
                LTRIM(RTRIM(ISNULL(L.EMPRESA, ''))) AS EMPRESA
            FROM dbo.COLAB_DESPESA_LINHA L
            WHERE L.DESPLINHASTAMP = :stamp
        """), {'stamp': stamp}).mappings().first() or {}
        params['feid'] = int(current.get('FEID') or 0)
        params['empresa'] = str(current.get('EMPRESA') or '').strip()

    current_line = db.session.execute(text("""
        SELECT TOP 1 ISNULL(VALOR, 0) AS VALOR
        FROM dbo.COLAB_DESPESA_LINHA
        WHERE DESPLINHASTAMP = :stamp
    """), {'stamp': stamp}).mappings().first() or {}
    valor = _safe_decimal(payload.get('valor') if 'valor' in payload else current_line.get('VALOR'))
    taxaiva = _safe_decimal(payload.get('taxaiva'))
    valor_sem_iva, valor_iva = _vat_amounts_from_gross(valor, taxaiva)
    params.update({
        'valor': valor,
        'tabiva': _safe_int(payload.get('tabiva')),
        'taxaiva': taxaiva,
        'valor_sem_iva': valor_sem_iva,
        'valor_iva': valor_iva,
    })

    result = db.session.execute(text("""
        UPDATE dbo.COLAB_DESPESA_LINHA
        SET VIATURA = :viatura,
            REF = :ref,
            DESIGN = :design,
            CCUSTO = :ccusto,
            VALOR = :valor,
            FEID = :feid,
            EMPRESA = :empresa,
            TABIVA = :tabiva,
            TAXAIVA = :taxaiva,
            VALOR_SEM_IVA = :valor_sem_iva,
            VALOR_IVA = :valor_iva,
            DTALT = GETDATE(),
            USERALTERACAO = :login
        WHERE DESPLINHASTAMP = :stamp
          AND ISNULL(ANULADA, 0) = 0
          AND UPPER(LTRIM(RTRIM(ISNULL(ESTADO, '')))) = 'FECHADO'
    """), params)
    if result.rowcount == 0:
        raise ValueError('Despesa não encontrada.')
    db.session.commit()
    row = db.session.execute(text("""
        SELECT TOP 1 *
        FROM dbo.COLAB_DESPESA_LINHA
        WHERE DESPLINHASTAMP = :stamp
    """), {'stamp': stamp}).mappings().first()
    return {'ok': True, 'line': serialize_line(row or {})}


def _phc_columns(cursor, table_name: str) -> set[str]:
    cursor.execute("""
        SELECT LOWER(COLUMN_NAME)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo'
          AND TABLE_NAME = ?
    """, table_name)
    return {str(row[0] or '').strip().lower() for row in cursor.fetchall()}


def _phc_insert(cursor, table_name: str, values: dict[str, Any]) -> dict[str, Any]:
    columns = _phc_columns(cursor, table_name)
    filtered = {key: value for key, value in values.items() if key.lower() in columns}
    if not filtered:
        raise RuntimeError(f"Sem colunas válidas para inserir em {table_name}.")
    cursor.execute(
        f"INSERT INTO dbo.{table_name} ({', '.join(filtered.keys())}) VALUES ({', '.join(['?'] * len(filtered))})",
        list(filtered.values()),
    )
    return filtered


def _phc_tax_rates(cursor) -> list[dict[str, Any]]:
    columns = _phc_columns(cursor, 'TAXASIVA')
    code_col = _pick_column({col.upper() for col in columns}, ['TABIVA', 'CODIGO', 'COD', 'CODIVA', 'ID'])
    rate_col = _pick_column({col.upper() for col in columns}, ['TAXAIVA', 'TAXA', 'PERCENTAGEM', 'VALOR'])
    if not code_col or not rate_col:
        return []
    cursor.execute(f"""
        SELECT
            CONVERT(varchar(30), {_sql_identifier(code_col)}) AS TABIVA,
            TRY_CONVERT(decimal(9,4), {_sql_identifier(rate_col)}) AS TAXAIVA
        FROM dbo.TAXASIVA
        WHERE {_sql_identifier(code_col)} IS NOT NULL
        ORDER BY TRY_CONVERT(int, {_sql_identifier(code_col)}), {_sql_identifier(code_col)}
    """)
    return [
        {
            'tabiva': str(row.TABIVA or '').strip(),
            'taxaiva': _safe_decimal(row.TAXAIVA),
        }
        for row in cursor.fetchall()
        if str(row.TABIVA or '').strip()
    ]


def _resolve_phc_supplier(cursor, peno: int) -> dict[str, Any]:
    if not peno:
        raise ValueError('O utilizador não tem número de colaborador.')
    cursor.execute("""
        SELECT TOP 1
            LTRIM(RTRIM(ISNULL(CONVERT(varchar(60), NCONT), ''))) AS NCONT,
            LTRIM(RTRIM(ISNULL(NOME, ''))) AS NOME
        FROM dbo.PE
        WHERE NO = ?
    """, int(peno))
    pe = cursor.fetchone()
    if not pe:
        raise ValueError(f'Colaborador PE.NO={peno} não existe na base PHC.')
    ncont = str(pe.NCONT or '').strip()
    if not ncont:
        raise ValueError(f'Colaborador PE.NO={peno} não tem contribuinte preenchido.')
    cursor.execute("""
        SELECT TOP 1
            ISNULL(NO, 0) AS NO,
            LTRIM(RTRIM(ISNULL(NOME, ''))) AS NOME,
            LTRIM(RTRIM(ISNULL(NCONT, ''))) AS NCONT,
            LTRIM(RTRIM(ISNULL(MORADA, ''))) AS MORADA,
            LTRIM(RTRIM(ISNULL(LOCAL, ''))) AS LOCAL,
            LTRIM(RTRIM(ISNULL(CODPOST, ''))) AS CODPOST,
            LTRIM(RTRIM(ISNULL(CCUSTO, ''))) AS CCUSTO,
            LTRIM(RTRIM(ISNULL(FREF, ''))) AS FREF,
            ISNULL(ESTAB, 0) AS ESTAB
        FROM dbo.FL
        WHERE LTRIM(RTRIM(ISNULL(NCONT, ''))) = ?
          AND ISNULL(INACTIVO, 0) = 0
        ORDER BY ISNULL(NO, 0)
    """, ncont)
    fl = cursor.fetchone()
    if not fl:
        raise ValueError(f'Não existe fornecedor FL ativo com contribuinte {ncont} para o colaborador {pe.NOME or peno}.')
    return {
        'no': int(fl.NO or 0),
        'nome': str(fl.NOME or '').strip(),
        'ncont': str(fl.NCONT or '').strip(),
        'morada': str(fl.MORADA or '').strip(),
        'local': str(fl.LOCAL or '').strip(),
        'codpost': str(fl.CODPOST or '').strip() or '0000-000',
        'ccusto': str(fl.CCUSTO or '').strip(),
        'fref': str(fl.FREF or '').strip(),
        'estab': int(fl.ESTAB or 0),
    }


def _phc_article(cursor, ref: str) -> dict[str, Any]:
    clean_ref = str(ref or '').strip()
    columns = _phc_columns(cursor, 'ST')
    if not columns:
        raise ValueError('A tabela ST não existe ou não está acessível na base PHC.')

    design_expr = "LTRIM(RTRIM(ISNULL(DESIGN, '')))" if 'design' in columns else "CAST('' AS varchar(200))"
    unidade_expr = "LTRIM(RTRIM(ISNULL(UNIDADE, '')))" if 'unidade' in columns else "CAST('und' AS varchar(20))"
    familia_expr = "LTRIM(RTRIM(ISNULL(FAMILIA, '')))" if 'familia' in columns else "CAST('' AS varchar(80))"
    stipo_expr = "ISNULL(STIPO, 1)" if 'stipo' in columns else "CAST(1 AS int)"
    cursor.execute(f"""
        SELECT TOP 1
            LTRIM(RTRIM(ISNULL(REF, ''))) AS REF,
            {design_expr} AS DESIGN,
            {unidade_expr} AS UNIDADE,
            {familia_expr} AS FAMILIA,
            {stipo_expr} AS STIPO
        FROM dbo.ST
        WHERE LTRIM(RTRIM(ISNULL(REF, ''))) = ?
    """, clean_ref)
    row = cursor.fetchone()
    if not row:
        raise ValueError(f'Referência {clean_ref} não existe no PHC.')
    return {
        'ref': str(row.REF or '').strip(),
        'design': str(row.DESIGN or '').strip(),
        'unidade': str(row.UNIDADE or '').strip() or 'und',
        'familia': str(row.FAMILIA or '').strip(),
        'stipo': int(row.STIPO or 1),
    }


def _phc_company_info(cursor) -> dict[str, str]:
    cursor.execute("""
        SELECT TOP 1
            LTRIM(RTRIM(ISNULL(nomecomp, ''))) AS NOME,
            LTRIM(RTRIM(ISNULL(morada, ''))) AS MORADA,
            LTRIM(RTRIM(ISNULL(local, ''))) AS LOCALIDADE,
            LTRIM(RTRIM(ISNULL(codpost, ''))) AS CODPOST,
            LTRIM(RTRIM(ISNULL(ncont, ''))) AS NIF
        FROM dbo.E1
    """)
    row = cursor.fetchone()
    if not row:
        return {}
    return {
        "nome": str(row.NOME or "").strip(),
        "morada": str(row.MORADA or "").strip(),
        "localidade": str(row.LOCALIDADE or "").strip(),
        "codpost": str(row.CODPOST or "").strip(),
        "nif": str(row.NIF or "").strip(),
    }


def _local_or_remote_file_path(path_value: str) -> str:
    clean = str(path_value or "").strip()
    if not clean:
        return ""
    if os.path.isabs(clean) and os.path.exists(clean):
        return clean
    candidate = os.path.join(current_app.root_path, clean.lstrip("/").replace("/", os.sep))
    if os.path.exists(candidate):
        return candidate
    return _cache_remote_expense_file("/" + clean.lstrip("/"))


def _clean_pdf_filename(value: str, fallback: str = "documento") -> str:
    name = re.sub(r"[^\w.\- ]+", "-", str(value or "").strip(), flags=re.UNICODE)
    name = re.sub(r"\s+", " ", name).strip(" .-_")
    return (name or fallback)[:120]


def _expense_local_file_path(file_path: str) -> str:
    clean = str(file_path or "").strip()
    if not clean:
        return ""
    parsed = urlparse(clean)
    if parsed.scheme in {"http", "https"}:
        return _cache_remote_expense_file(clean)
    if os.path.isabs(clean) and os.path.exists(clean):
        return clean
    relative = clean.lstrip("/").replace("/", os.sep)
    candidate = os.path.join(current_app.root_path, relative)
    if os.path.exists(candidate):
        return candidate
    return _cache_remote_expense_file(clean)


def _expense_public_base_urls() -> list[str]:
    values = [
        os.environ.get("COLAB_DESPESAS_PUBLIC_BASE_URLS"),
        os.environ.get("COLAB_DESPESAS_PUBLIC_BASE_URL"),
        current_app.config.get("COLAB_DESPESAS_PUBLIC_BASE_URLS"),
        current_app.config.get("COLAB_DESPESAS_PUBLIC_BASE_URL"),
        "https://app.gr360flooringsystems.com",
    ]
    urls: list[str] = []
    for value in values:
        for item in re.split(r"[;\n,]", str(value or "")):
            item = item.strip().rstrip("/")
            if item and item not in urls:
                urls.append(item)
    return urls


def _expense_public_file_url(file_path: str) -> str:
    clean = str(file_path or "").strip()
    if not clean:
        return ""
    parsed = urlparse(clean)
    if parsed.scheme in {"http", "https"}:
        return clean
    bases = _expense_public_base_urls()
    if not bases:
        return clean
    return f"{bases[0]}{'/' + clean.lstrip('/')}"


def _remote_expense_urls(file_path: str) -> list[str]:
    clean = str(file_path or "").strip()
    if not clean:
        return []
    parsed = urlparse(clean)
    if parsed.scheme in {"http", "https"}:
        return [clean]
    public_path = "/" + clean.lstrip("/")
    return [f"{base}{public_path}" for base in _expense_public_base_urls()]


def _cache_remote_expense_file(file_path: str) -> str:
    urls = _remote_expense_urls(file_path)
    if not urls:
        return ""
    clean_name = os.path.basename(urlparse(urls[0]).path or "") or f"{_new_stamp()}.bin"
    _, ext = os.path.splitext(clean_name)
    cache_name = f"{hashlib.sha1(str(file_path).encode('utf-8')).hexdigest()}{ext or '.bin'}"
    cache_dir = os.path.join(current_app.root_path, "static", "uploads", "colaborador_despesas", "_remote_cache")
    os.makedirs(cache_dir, exist_ok=True)
    destination = os.path.join(cache_dir, cache_name)
    if os.path.exists(destination) and os.path.getsize(destination) > 0:
        return destination
    for url in urls:
        try:
            request = Request(url, headers={"User-Agent": "GR360 Expenses/1.0"})
            with urlopen(request, timeout=25) as response:
                if int(getattr(response, "status", 200) or 200) >= 400:
                    continue
                with open(destination, "wb") as handle:
                    shutil.copyfileobj(response, handle)
            if os.path.exists(destination) and os.path.getsize(destination) > 0:
                return destination
        except Exception:
            current_app.logger.info("Não foi possível obter anexo remoto da despesa em %s.", url, exc_info=True)
    try:
        if os.path.exists(destination) and os.path.getsize(destination) == 0:
            os.remove(destination)
    except OSError:
        pass
    return ""


def _target_phc_pdf_path(phc_db: str, obrano: int, supplier_name: str, year: int) -> tuple[str, str, str]:
    db_name = str(phc_db or "").strip()
    filename_base = _clean_pdf_filename(f"NDF-{int(obrano or 0):04d}-{str(supplier_name or '').strip().upper()}", f"NDF-{int(obrano or 0):04d}")
    filename = f"{filename_base}.pdf"
    unc_root = str(current_app.config.get("PHC_GED_UNC_ROOT") or os.environ.get("PHC_GED_UNC_ROOT") or r"\\10.0.1.11\ged").strip().rstrip("\\/")
    phc_fullname = "\\".join([unc_root, db_name.upper(), "NOTE_FRAIS", str(year), filename])

    write_root = str(current_app.config.get("PHC_GED_WRITE_ROOT") or os.environ.get("PHC_GED_WRITE_ROOT") or "").strip()
    if write_root:
        output_dir = os.path.join(write_root, db_name.upper(), "NOTE_FRAIS", str(year))
        os.makedirs(output_dir, exist_ok=True)
        return os.path.join(output_dir, filename), phc_fullname, filename

    if os.name == "nt":
        output_dir = "\\".join([unc_root, db_name.upper(), "NOTE_FRAIS", str(year)])
        os.makedirs(output_dir, exist_ok=True)
        return "\\".join([output_dir, filename]), phc_fullname, filename

    raise RuntimeError(
        "Não consigo escrever o PDF no GED do PHC a partir desta máquina. "
        f"Monte/configure PHC_GED_WRITE_ROOT para apontar para {phc_fullname}."
    )


def _draw_text_line(pdf: canvas.Canvas, x: float, y: float, text_value: str, size: int = 9, bold: bool = False) -> float:
    pdf.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    pdf.drawString(x, y, str(text_value or ""))
    return y - (size + 4)


def _build_cover_pdf(path: str, prepared_lines: list[dict[str, Any]], supplier: dict[str, Any], obrano: int, dataobra: Any, total_net: Decimal, total_vat: Decimal, company_info: dict[str, str] | None = None, logo_path: str = "") -> None:
    pdf = canvas.Canvas(path, pagesize=A4)
    width, height = A4
    margin = 16 * mm
    y = height - margin

    header_bottom = height - 34 * mm
    pdf.setFillColor(colors.white)
    pdf.rect(0, header_bottom, width, 34 * mm, fill=1, stroke=0)
    if logo_path and os.path.exists(logo_path):
        try:
            logo_box_x = margin
            logo_box_y = height - 27 * mm
            logo_box_w = 42 * mm
            logo_box_h = 22 * mm
            with Image.open(logo_path) as logo_source:
                logo = ImageOps.exif_transpose(logo_source)
                logo.thumbnail((int(40 * mm), int(20 * mm)))
                tmp_logo = path + ".logo.png"
                logo.convert("RGBA").save(tmp_logo, "PNG")
            try:
                pdf.drawImage(
                    tmp_logo,
                    logo_box_x,
                    logo_box_y + 1 * mm,
                    width=logo_box_w,
                    height=logo_box_h - 2 * mm,
                    preserveAspectRatio=True,
                    mask="auto",
                )
            finally:
                try:
                    os.remove(tmp_logo)
                except OSError:
                    pass
        except Exception:
            current_app.logger.info("Não foi possível desenhar o logotipo da empresa no PDF.", exc_info=True)

    company_info = company_info or {}
    text_x = margin + 50 * mm
    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(text_x, height - 10 * mm, (company_info.get("nome") or "").upper()[:80])
    pdf.setFont("Helvetica", 8)
    postal_line = " ".join(part for part in [company_info.get("codpost") or "", company_info.get("localidade") or ""] if part).strip()
    if company_info.get("localidade") and company_info.get("localidade", "").lower() in (company_info.get("codpost") or "").lower():
        postal_line = company_info.get("codpost") or ""
    company_lines = [
        company_info.get("morada") or "",
        postal_line,
        f"NIF: {company_info.get('nif')}" if company_info.get("nif") else "",
    ]
    line_y = height - 15 * mm
    for line in [item for item in company_lines if item]:
        pdf.drawString(text_x, line_y, line[:95])
        line_y -= 4 * mm

    pdf.setFillColor(colors.HexColor("#12304f"))
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawRightString(width - margin, height - 13 * mm, f"NDF #{int(obrano or 0):04d}")
    pdf.setFont("Helvetica", 9)
    pdf.drawRightString(width - margin, height - 19 * mm, datetime.now().strftime("%d/%m/%Y %H:%M"))
    pdf.setStrokeColor(colors.HexColor("#12304f"))
    pdf.setLineWidth(3)
    pdf.line(margin, header_bottom, width - margin, header_bottom)

    y = height - 44 * mm
    pdf.setFillColor(colors.black)
    y = _draw_text_line(pdf, margin, y, f"Colaborador: {supplier.get('nome') or ''}", 11, True)
    y = _draw_text_line(pdf, margin, y, f"Contribuinte: {supplier.get('ncont') or ''}", 9)
    y = _draw_text_line(pdf, margin, y, f"Data dossier: {dataobra.strftime('%d/%m/%Y') if hasattr(dataobra, 'strftime') else dataobra}", 9)
    y -= 8

    total_gross = (total_net + total_vat).quantize(Decimal("0.01"))
    y = _draw_text_line(pdf, margin, y, f"Total sem IVA: {_decimal_label(total_net, 2)} EUR", 10, True)
    y = _draw_text_line(pdf, margin, y, f"IVA: {_decimal_label(total_vat, 2)} EUR", 10, True)
    y = _draw_text_line(pdf, margin, y, f"Total com IVA: {_decimal_label(total_gross, 2)} EUR", 10, True)
    y -= 10

    headers = ["Data", "Tipo", "Ref.", "Designacao", "C. custo", "Total"]
    col_widths = [23 * mm, 23 * mm, 34 * mm, 58 * mm, 25 * mm, 24 * mm]
    x = margin
    pdf.setFillColor(colors.HexColor("#e8eef5"))
    pdf.rect(margin, y - 5, sum(col_widths), 18, fill=1, stroke=0)
    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 8)
    for idx, header in enumerate(headers):
        pdf.drawString(x + 2, y, header)
        x += col_widths[idx]
    y -= 14
    pdf.setFont("Helvetica", 8)

    for line in prepared_lines:
        row = line["row"]
        if y < 30 * mm:
            pdf.showPage()
            y = height - margin
            pdf.setFont("Helvetica", 8)
        values = [
            row.get("DATA_DESPESA").strftime("%d/%m/%Y") if hasattr(row.get("DATA_DESPESA"), "strftime") else str(row.get("DATA_DESPESA") or ""),
            str(row.get("TIPO") or ""),
            str(row.get("REF") or ""),
            str(row.get("DESIGN") or line.get("article", {}).get("design") or "")[:42],
            str(line.get("ccusto") or ""),
            f"{_decimal_label(line.get('gross'), 2)} EUR",
        ]
        x = margin
        for idx, value in enumerate(values):
            pdf.drawString(x + 2, y, value[:46])
            x += col_widths[idx]
        y -= 12

    pdf.save()


def _build_image_page_pdf(path: str, image_path: str, title: str) -> None:
    pdf = canvas.Canvas(path, pagesize=A4)
    width, height = A4
    margin = 14 * mm
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(margin, height - margin, title[:95])

    with Image.open(image_path) as source_image:
        image = ImageOps.exif_transpose(source_image)
        image.thumbnail((int(width - 2 * margin), int(height - 3 * margin)))
        tmp_image = path + ".png"
        image.convert("RGB").save(tmp_image, "PNG")
    try:
        image_width, image_height = Image.open(tmp_image).size
        max_width = width - 2 * margin
        max_height = height - 3 * margin
        ratio = min(max_width / image_width, max_height / image_height)
        draw_width = image_width * ratio
        draw_height = image_height * ratio
        pdf.drawImage(tmp_image, (width - draw_width) / 2, margin, width=draw_width, height=draw_height, preserveAspectRatio=True, anchor="c")
        pdf.save()
    finally:
        try:
            os.remove(tmp_image)
        except OSError:
            pass


def _create_notes_frais_pdf(prepared_lines: list[dict[str, Any]], supplier: dict[str, Any], obrano: int, dataobra: Any, phc_db: str, total_net: Decimal, total_vat: Decimal, company_info: dict[str, str] | None = None, logo_path: str = "") -> dict[str, Any]:
    year = date.today().year
    output_path, phc_fullname, fname = _target_phc_pdf_path(phc_db, obrano, str(supplier.get("nome") or ""), year)
    writer = PdfWriter()

    with tempfile.TemporaryDirectory(prefix="ndf_pdf_") as tmpdir:
        cover_path = os.path.join(tmpdir, "cover.pdf")
        _build_cover_pdf(cover_path, prepared_lines, supplier, obrano, dataobra, total_net, total_vat, company_info, logo_path)
        for page in PdfReader(cover_path).pages:
            writer.add_page(page)

        for index, line in enumerate(prepared_lines, start=1):
            row = line["row"]
            source = _expense_local_file_path(str(row.get("CAMINHO") or ""))
            if not source:
                continue
            ext = os.path.splitext(source)[1].lower()
            title = f"Anexo {index} - {row.get('DATA_DESPESA') or ''} - {row.get('TIPO') or ''} - {_decimal_label(row.get('VALOR'), 2)} EUR"
            if ext == ".pdf":
                try:
                    for page in PdfReader(source).pages:
                        writer.add_page(page)
                except Exception:
                    current_app.logger.exception("Erro ao anexar PDF da despesa %s.", row.get("DESPLINHASTAMP"))
                continue
            if ext in {".jpg", ".jpeg", ".png", ".webp"}:
                image_pdf = os.path.join(tmpdir, f"image_{index}.pdf")
                try:
                    _build_image_page_pdf(image_pdf, source, title)
                    for page in PdfReader(image_pdf).pages:
                        writer.add_page(page)
                except Exception:
                    current_app.logger.exception("Erro ao anexar imagem da despesa %s.", row.get("DESPLINHASTAMP"))

        with open(output_path, "wb") as handle:
            writer.write(handle)

    return {
        "path": output_path,
        "fullname": phc_fullname,
        "fname": fname,
        "fext": "pdf",
        "flen": os.path.getsize(output_path) if os.path.exists(output_path) else 0,
    }


def _insert_phc_anexo(cursor, bostamp: str, pdf_info: dict[str, Any], user_inis: str, now_sql: datetime, hour: str) -> str:
    anexosstamp = _new_stamp()
    _phc_insert(cursor, "ANEXOS", {
        "anexosstamp": anexosstamp,
        "oritable": "BO",
        "tabnm": "Dossiers Internos",
        "resumo": "NDF",
        "grupo": "",
        "recstamp": bostamp,
        "uniqueid": "",
        "descricao": "Resumo de despesas e anexos",
        "bdados": pyodbc.Binary(b""),
        "fullname": str(pdf_info.get("fullname") or ""),
        "fname": str(pdf_info.get("fname") or "")[:150],
        "fext": "pdf",
        "flen": int(pdf_info.get("flen") or 0),
        "tipo": 2,
        "passw": "",
        "origem": "",
        "keylook": "",
        "tpdos": PHC_NOTES_FRAIS_NDOS,
        "tpdoc": 0,
        "ausrinis": user_inis,
        "ausrdata": now_sql,
        "ausrhora": hour,
        "eusrinis": user_inis,
        "eusrdata": now_sql,
        "eusrhora": hour,
        "anexopaistamp": "",
        "assinatura": 0,
        "timestamp": 0,
        "anexoversaostamp": "",
        "versao": 1,
        "idustamp": "",
        "ousrinis": user_inis,
        "ousrdata": now_sql,
        "ousrhora": hour,
        "usrinis": user_inis,
        "usrdata": now_sql,
        "usrhora": hour,
        "marcada": 0,
        "zipado": 0,
        "bdadosstamp": "",
        "invisivel": 0,
        "checkout": 0,
        "cuserno": 0,
        "cusername": "",
        "usnoopen": 0,
        "usnaopen": "",
        "isemail": 0,
        "emailid": "",
        "emaildata": date(1900, 1, 1),
        "startwkf": 0,
        "wtwstamp": "",
        "emailsubj": "",
        "privado": 0,
        "nivel": 0,
        "lsgq": 0,
        "u_enviado": 0,
        "u_jaobra": 0,
        "fiscrel": 0,
        "original": 1,
        "filestorageid": "",
        "marcadoenviar": 0,
        "ziparquivodigital": 0,
    })
    return anexosstamp


def _load_processing_lines_for_launch(stamps: list[str]) -> list[dict[str, Any]]:
    clean_stamps = [str(stamp or '').strip() for stamp in stamps if str(stamp or '').strip()]
    if not clean_stamps:
        raise ValueError('Seleciona pelo menos uma despesa.')
    if len(clean_stamps) > 100:
        raise ValueError('Seleciona no máximo 100 despesas de cada vez.')
    params = {f's{i}': stamp for i, stamp in enumerate(clean_stamps)}
    in_sql = ', '.join(f':s{i}' for i in range(len(clean_stamps)))
    rows = db.session.execute(text(f"""
        SELECT
            L.*,
            H.USSTAMP,
            H.LOGIN,
            H.PENO,
            H.PENOME,
            H.PEFEID,
            ISNULL(NULLIF(L.FEID, 0), H.FEID) AS LINHA_FEID,
            COALESCE(NULLIF(L.EMPRESA, ''), H.EMPRESA, '') AS LINHA_EMPRESA
        FROM dbo.COLAB_DESPESA_LINHA L
        INNER JOIN dbo.COLAB_DESPESA_CAB H
          ON H.DESPCABSTAMP = L.DESPCABSTAMP
        WHERE L.DESPLINHASTAMP IN ({in_sql})
          AND ISNULL(L.ANULADA, 0) = 0
          AND UPPER(LTRIM(RTRIM(ISNULL(L.ESTADO, '')))) = 'FECHADO'
          AND LTRIM(RTRIM(ISNULL(L.PHC_BOSTAMP, ''))) = ''
    """), params).mappings().all()
    found = {str(row.get('DESPLINHASTAMP') or '').strip() for row in rows}
    missing = [stamp for stamp in clean_stamps if stamp not in found]
    if missing:
        raise ValueError('Algumas despesas já foram lançadas, anuladas ou não estão fechadas.')
    return [dict(row) for row in rows]


def launch_expenses_to_phc(stamps: list[str], user) -> dict[str, Any]:
    ensure_colaborador_despesas_schema()
    lines = _load_processing_lines_for_launch(stamps)
    feids = {int(row.get('LINHA_FEID') or 0) for row in lines}
    logins = {str(row.get('LOGIN') or '').strip().lower() for row in lines}
    penos = {int(row.get('PENO') or 0) for row in lines}
    if len(feids) != 1:
        raise ValueError('Só podes lançar despesas da mesma empresa de cada vez.')
    if len(logins) != 1 or len(penos) != 1:
        raise ValueError('Só podes lançar despesas do mesmo colaborador de cada vez.')

    for row in lines:
        if not str(row.get('REF') or '').strip():
            raise ValueError('Não é possível lançar despesas sem referência.')

    feid = next(iter(feids))
    peno = next(iter(penos))
    company = _expense_company_by_feid(feid)
    phc_db = str(company.get('phc_db') or '').strip() or _phc_db_hint(str(company.get('nome') or lines[0].get('LINHA_EMPRESA') or ''))
    phc_server = str(company.get('phc_server') or '').strip()
    if not phc_db:
        raise ValueError('A empresa selecionada não tem base de dados PHC configurada.')

    login = str(getattr(user, 'LOGIN', '') or getattr(user, 'login', '') or '').strip() or 'APP'
    user_inis = login[:3].upper() or 'APP'
    today_value = date.today()
    # dataobra follows the latest selected expense date where available.
    dataobra = max((row.get('DATA_DESPESA') for row in lines if row.get('DATA_DESPESA')), default=today_value)

    with pyodbc.connect(_phc_conn_str(phc_db, phc_server), timeout=30) as conn:
        conn.autocommit = False
        cursor = conn.cursor()
        try:
            supplier = _resolve_phc_supplier(cursor, peno)
            company_info = _phc_company_info(cursor)
            logo_path = _local_or_remote_file_path(str(company.get('logo_path') or ''))
            prepared_lines = []
            for index, row in enumerate(lines, start=1):
                article = _phc_article(cursor, str(row.get('REF') or '').strip())
                gross = _safe_decimal(row.get('VALOR'))
                taxaiva = _safe_decimal(row.get('TAXAIVA'))
                net, vat = _vat_amounts_from_gross(gross, taxaiva)
                tabiva = _safe_int(row.get('TABIVA'))
                ccusto = str(row.get('CCUSTO') or supplier.get('ccusto') or '').strip()
                prepared_lines.append({
                    'row': row,
                    'article': article,
                    'gross': gross,
                    'net': net,
                    'vat': vat,
                    'tabiva': tabiva,
                    'taxaiva': taxaiva,
                    'ccusto': ccusto,
                    'lordem': index * 10000,
                    'bistamp': _new_stamp(),
                })

            cursor.execute("""
                SELECT ISNULL(MAX(TRY_CONVERT(int, OBRANO)), 0) + 1
                FROM dbo.BO WITH (UPDLOCK, HOLDLOCK)
                WHERE NDOS = ?
                  AND BOANO = ?
            """, PHC_NOTES_FRAIS_NDOS, today_value.year)
            obrano = int(cursor.fetchone()[0] or 1)
            bostamp = _new_stamp()
            now_sql = datetime.now()
            hour = now_sql.strftime('%H:%M:%S')
            total_net = sum((line['net'] for line in prepared_lines), Decimal('0.00')).quantize(Decimal('0.01'))
            total_vat = sum((line['vat'] for line in prepared_lines), Decimal('0.00')).quantize(Decimal('0.01'))
            total_deb = total_net
            header_ccusto = str(prepared_lines[0].get('ccusto') or supplier.get('ccusto') or '').strip()
            cursor.execute("""
                SELECT TOP 1 LTRIM(RTRIM(ISNULL(MOEDA, '')))
                FROM dbo.BO
                WHERE NDOS = ?
                  AND LTRIM(RTRIM(ISNULL(MOEDA, ''))) <> ''
                ORDER BY DATAOBRA DESC, OBRANO DESC
            """, PHC_NOTES_FRAIS_NDOS)
            currency_row = cursor.fetchone()
            phc_currency = str(currency_row[0] or '').strip() if currency_row else 'EURO'
            tax_by_code: dict[int, dict[str, Decimal]] = {}
            for line in prepared_lines:
                bucket = tax_by_code.setdefault(line['tabiva'], {'taxa': line['taxaiva'], 'base': Decimal('0.00'), 'iva': Decimal('0.00')})
                bucket['base'] += line['net']
                bucket['iva'] += line['vat']

            bo_values = {
                'bostamp': bostamp,
                'nmdos': PHC_NOTES_FRAIS_NMDOS,
                'ndos': PHC_NOTES_FRAIS_NDOS,
                'obrano': obrano,
                'boano': today_value.year,
                'dataobra': dataobra,
                'dataopen': date(1900, 1, 1),
                'datafecho': date(1900, 1, 1),
                'nome': supplier['nome'][:55],
                'no': supplier['no'],
                'ncont': supplier['ncont'],
                'morada': supplier['morada'],
                'local': supplier['local'],
                'codpost': supplier['codpost'],
                'estab': supplier['estab'],
                'moeda': phc_currency or 'EURO',
                'ccusto': header_ccusto,
                'fref': supplier.get('fref') or '',
                'totaldeb': _phc_value(total_deb),
                'etotaldeb': total_deb,
                'total': _phc_value(total_net),
                'etotal': total_net,
                'fechada': 0,
                'ousrinis': user_inis,
                'ousrdata': now_sql,
                'ousrhora': hour,
                'usrinis': user_inis,
                'usrdata': now_sql,
                'usrhora': hour,
            }
            bo_cols = _phc_columns(cursor, 'BO')
            for tabiva, totals in tax_by_code.items():
                if tabiva <= 0:
                    continue
                for suffix in ('1', '2'):
                    base_col = f'ebo{tabiva}{suffix}_bins'
                    vat_col = f'ebo{tabiva}{suffix}_iva'
                    local_base_col = f'bo{tabiva}{suffix}_bins'
                    local_vat_col = f'bo{tabiva}{suffix}_iva'
                    if base_col in bo_cols:
                        bo_values[base_col] = totals['base'].quantize(Decimal('0.01'))
                    if vat_col in bo_cols:
                        bo_values[vat_col] = totals['iva'].quantize(Decimal('0.01'))
                    if local_base_col in bo_cols:
                        bo_values[local_base_col] = _phc_value(totals['base'])
                    if local_vat_col in bo_cols:
                        bo_values[local_vat_col] = _phc_value(totals['iva'])
            _phc_insert(cursor, 'BO', bo_values)
            _phc_insert(cursor, 'BO2', {
                'bo2stamp': bostamp,
                'processo': header_ccusto,
                'subproc': '',
                'area': '',
                'vencimento': 0,
                'armazem': 0,
                'ousrinis': user_inis,
                'ousrdata': now_sql,
                'ousrhora': hour,
                'usrinis': user_inis,
                'usrdata': now_sql,
                'usrhora': hour,
            })
            _phc_insert(cursor, 'BO3', {
                'bo3stamp': bostamp,
                'u_aprovdat': date(1900, 1, 1),
                'u_aprovusr': '',
                'arquivadodigital': 0,
                'ousrinis': user_inis,
                'ousrdata': now_sql,
                'ousrhora': hour,
                'usrinis': user_inis,
                'usrdata': now_sql,
                'usrhora': hour,
            })

            tax_rates = _phc_tax_rates(cursor)
            if not tax_rates:
                tax_rates = [{'tabiva': str(code), 'taxaiva': values['taxa']} for code, values in sorted(tax_by_code.items())]
            for rate in tax_rates:
                code = _safe_int(rate.get('tabiva'))
                totals = tax_by_code.get(code, {'base': Decimal('0.00'), 'iva': Decimal('0.00'), 'taxa': _safe_decimal(rate.get('taxaiva'))})
                _phc_insert(cursor, 'BOT', {
                    'botstamp': _new_stamp(),
                    'bostamp': bostamp,
                    'codigo': code,
                    'taxa': _safe_decimal(rate.get('taxaiva')),
                    'ebaseinc': totals['base'].quantize(Decimal('0.01')),
                    'baseinc': _phc_value(totals['base']),
                    'evalor': totals['iva'].quantize(Decimal('0.01')),
                    'valor': _phc_value(totals['iva']),
                    'ousrinis': user_inis,
                    'ousrdata': now_sql,
                    'ousrhora': hour,
                    'usrinis': user_inis,
                    'usrdata': now_sql,
                    'usrhora': hour,
                })

            for line in prepared_lines:
                row = line['row']
                article = line['article']
                net = line['net'].quantize(Decimal('0.01'))
                local_net = _phc_value(net)
                bi_values = {
                    'bistamp': line['bistamp'],
                    'bostamp': bostamp,
                    'nmdos': PHC_NOTES_FRAIS_NMDOS,
                    'ndos': PHC_NOTES_FRAIS_NDOS,
                    'obrano': obrano,
                    'boano': today_value.year,
                    'dataobra': dataobra,
                    'ref': article['ref'],
                    'design': (str(row.get('DESIGN') or '').strip() or article['design'])[:60],
                    'qtt': Decimal('1.0000'),
                    'qtt2': Decimal('1.0000'),
                    'pu': local_net,
                    'debito': local_net,
                    'edebito': net,
                    'ttdeb': local_net,
                    'ettdeb': net,
                    'pcusto': local_net,
                    'epcusto': net,
                    'prorc': local_net,
                    'iva': line['taxaiva'],
                    'tabiva': line['tabiva'],
                    'ivaincl': 0,
                    'unidade': article['unidade'],
                    'stipo': article['stipo'],
                    'no': supplier['no'],
                    'nome': supplier['nome'][:55],
                    'lobs': str(row.get('VIATURA') or '').strip()[:60],
                    'lobs2': str(row.get('OBS') or '').strip()[:60],
                    'ccusto': line['ccusto'],
                    'bofref': supplier.get('fref') or '',
                    'bifref': supplier.get('fref') or '',
                    'familia': article.get('familia') or '',
                    'lordem': line['lordem'],
                    'armazem': 1,
                    'ousrinis': user_inis,
                    'ousrdata': now_sql,
                    'ousrhora': hour,
                    'usrinis': user_inis,
                    'usrdata': now_sql,
                    'usrhora': hour,
                }
                _phc_insert(cursor, 'BI', bi_values)
                _phc_insert(cursor, 'BI2', {
                    'bi2stamp': line['bistamp'],
                    'bostamp': bostamp,
                    'fnstamp': '',
                    'fodocnome': '',
                    'foadoc': '',
                    'fistamp': '',
                    'origbistamp': '',
                    'ousrinis': user_inis,
                    'ousrdata': now_sql,
                    'ousrhora': hour,
                    'usrinis': user_inis,
                    'usrdata': now_sql,
                    'usrhora': hour,
                })

            pdf_info = _create_notes_frais_pdf(prepared_lines, supplier, obrano, dataobra, phc_db, total_net, total_vat, company_info, logo_path)
            anexosstamp = _insert_phc_anexo(cursor, bostamp, pdf_info, user_inis, now_sql, hour)
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    line_params = {
        'bostamp': bostamp,
        'login': login,
    }
    for line in prepared_lines:
        stamp = str(line['row'].get('DESPLINHASTAMP') or '').strip()
        db.session.execute(text("""
            UPDATE dbo.COLAB_DESPESA_LINHA
            SET PHC_STATUS = 'LANCADO',
                PHC_BOSTAMP = :bostamp,
                PHC_BISTAMP = :bistamp,
                PHC_DTENVIO = GETDATE(),
                PHC_ERRO = N'',
                DTALT = GETDATE(),
                USERALTERACAO = :login
            WHERE DESPLINHASTAMP = :stamp
        """), {
            **line_params,
            'bistamp': line['bistamp'],
            'stamp': stamp,
        })
    db.session.commit()
    return {
        'ok': True,
        'phc_db': phc_db,
        'bostamp': bostamp,
        'obrano': obrano,
        'nmdos': PHC_NOTES_FRAIS_NMDOS,
        'linhas': len(prepared_lines),
        'anexosstamp': anexosstamp,
        'total_sem_iva': float(total_net),
        'total_iva': float(total_vat),
        'total_com_iva': float((total_net + total_vat).quantize(Decimal('0.01'))),
    }


def delete_expense_line(user, line_stamp: str) -> dict[str, Any]:
    ensure_colaborador_despesas_schema()
    colaborador = get_colaborador_context(user)
    stamp = str(line_stamp or '').strip()
    result = db.session.execute(text(f"""
        UPDATE L
        SET ANULADA = 1,
            ESTADO = 'ANULADA',
            DTALT = GETDATE(),
            USERALTERACAO = :login
        FROM dbo.COLAB_DESPESA_LINHA L
        WHERE L.DESPLINHASTAMP = :stamp
          AND L.ESTADO = 'RASCUNHO'
          AND {_user_header_scope_sql()}
    """), {
        'stamp': stamp,
        'userstamp': str(colaborador.get('userstamp') or '').strip(),
        'login': str(colaborador.get('login') or '').strip(),
    })
    if result.rowcount == 0:
        raise ValueError('Despesa não encontrada.')
    db.session.commit()
    return {'ok': True, 'stamp': stamp}


def delete_expense_processing_line(line_stamp: str, user) -> dict[str, Any]:
    """Soft-delete an unposted expense from the administrative processing queue."""
    ensure_colaborador_despesas_schema()
    stamp = str(line_stamp or '').strip()
    if not stamp:
        raise ValueError('Despesa inválida.')

    login = str(getattr(user, 'LOGIN', '') or getattr(user, 'login', '') or '').strip()
    result = db.session.execute(text("""
        UPDATE dbo.COLAB_DESPESA_LINHA
        SET ANULADA = 1,
            ESTADO = 'ANULADA',
            DTALT = GETDATE(),
            USERALTERACAO = :login
        WHERE DESPLINHASTAMP = :stamp
          AND ISNULL(ANULADA, 0) = 0
          AND UPPER(LTRIM(RTRIM(ISNULL(ESTADO, '')))) = 'FECHADO'
          AND LTRIM(RTRIM(ISNULL(PHC_BOSTAMP, ''))) = ''
    """), {'stamp': stamp, 'login': login})
    if result.rowcount == 0:
        raise ValueError('A despesa não está disponível para eliminar.')
    db.session.commit()
    return {'ok': True, 'stamp': stamp, 'estado': 'ANULADA'}


def return_expense_from_processing(line_stamp: str, observation: str, user) -> dict[str, Any]:
    """Return an unposted expense to the collaborator for review and validation."""
    ensure_colaborador_despesas_schema()
    stamp = str(line_stamp or '').strip()
    if not stamp:
        raise ValueError('Despesa inválida.')
    observation = str(observation or '').strip()
    if not observation:
        raise ValueError('Indique uma observação para devolver a despesa.')
    if len(observation) > 500:
        raise ValueError('A observação não pode ultrapassar 500 caracteres.')

    login = str(getattr(user, 'LOGIN', '') or getattr(user, 'login', '') or '').strip()
    result = db.session.execute(text("""
        UPDATE dbo.COLAB_DESPESA_LINHA
        SET ANULADA = 0,
            ESTADO = 'RASCUNHO',
            DEVOLUCAO_OBS = :observation,
            DTALT = GETDATE(),
            USERALTERACAO = :login
        WHERE DESPLINHASTAMP = :stamp
          AND ISNULL(ANULADA, 0) = 0
          AND UPPER(LTRIM(RTRIM(ISNULL(ESTADO, '')))) = 'FECHADO'
          AND LTRIM(RTRIM(ISNULL(PHC_BOSTAMP, ''))) = ''
    """), {'stamp': stamp, 'login': login, 'observation': observation})
    if result.rowcount == 0:
        raise ValueError('A despesa não está disponível para devolver ao colaborador.')
    db.session.commit()
    return {'ok': True, 'stamp': stamp, 'estado': 'RASCUNHO'}


def close_expense_line(user, line_stamp: str) -> dict[str, Any]:
    ensure_colaborador_despesas_schema()
    colaborador = get_colaborador_context(user)
    stamp = str(line_stamp or '').strip()
    result = db.session.execute(text(f"""
        UPDATE L
        SET ESTADO = 'FECHADO',
            DEVOLUCAO_OBS = N'',
            DTALT = GETDATE(),
            USERALTERACAO = :login
        FROM dbo.COLAB_DESPESA_LINHA L
        WHERE L.DESPLINHASTAMP = :stamp
          AND ISNULL(L.ANULADA, 0) = 0
          AND {_user_header_scope_sql()}
    """), {
        'stamp': stamp,
        'userstamp': str(colaborador.get('userstamp') or '').strip(),
        'login': str(colaborador.get('login') or '').strip(),
    })
    if result.rowcount == 0:
        raise ValueError('Despesa não encontrada.')
    db.session.commit()
    return {'ok': True, 'stamp': stamp, 'estado': 'FECHADO'}
