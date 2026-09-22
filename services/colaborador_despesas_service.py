import hashlib
import json
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
from services.document_duplicate_service import acquire_duplicate_lock, find_exact_file_duplicate


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


class ExpensePhcConfigurationError(ValueError):
    """The selected Portal company cannot be resolved to a PHC database."""


class ExpensePhcQueryError(RuntimeError):
    """A configured PHC database could not be queried."""


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


def _expense_company_currency(company: dict[str, Any], requested: Any = '') -> str:
    phc_db = str(company.get('phc_db') or '').strip().upper()
    requested_currency = str(requested or '').strip().upper()
    if phc_db in {'HSOLS_MA', 'HSOLS_MAROC'}:
        return 'MAD'
    return requested_currency or 'EUR'


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
        IF COL_LENGTH('dbo.COLAB_DESPESA_LINHA', 'VERSION') IS NULL
            ALTER TABLE dbo.COLAB_DESPESA_LINHA ADD VERSION int NOT NULL
                CONSTRAINT DF_COLAB_DESPESA_LINHA_VERSION DEFAULT 1;
        IF COL_LENGTH('dbo.COLAB_DESPESA_LINHA', 'MOEDA') IS NULL
            ALTER TABLE dbo.COLAB_DESPESA_LINHA ADD MOEDA varchar(10) NOT NULL
                CONSTRAINT DF_COLAB_DESPESA_LINHA_MOEDA DEFAULT 'EUR';
        IF COL_LENGTH('dbo.COLAB_DESPESA_LINHA', 'REFERENCIA_DOCUMENTO') IS NULL
            ALTER TABLE dbo.COLAB_DESPESA_LINHA ADD REFERENCIA_DOCUMENTO nvarchar(160) NOT NULL
                CONSTRAINT DF_COLAB_DESPESA_LINHA_REFERENCIA_DOCUMENTO DEFAULT N'';
        IF COL_LENGTH('dbo.COLAB_DESPESA_LINHA', 'CAMPO_ORIGEM_JSON') IS NULL
            ALTER TABLE dbo.COLAB_DESPESA_LINHA ADD CAMPO_ORIGEM_JSON nvarchar(max) NOT NULL
                CONSTRAINT DF_COLAB_DESPESA_LINHA_CAMPO_ORIGEM DEFAULT N'{}';
        IF COL_LENGTH('dbo.COLAB_DESPESA_LINHA', 'ARQUIVO_ESTADO') IS NULL
            ALTER TABLE dbo.COLAB_DESPESA_LINHA ADD ARQUIVO_ESTADO varchar(20) NOT NULL
                CONSTRAINT DF_COLAB_DESPESA_LINHA_ARQUIVO_ESTADO DEFAULT '';
        IF COL_LENGTH('dbo.COLAB_DESPESA_LINHA', 'ARQUIVO_DATA') IS NULL
            ALTER TABLE dbo.COLAB_DESPESA_LINHA ADD ARQUIVO_DATA datetime NULL;
        IF COL_LENGTH('dbo.COLAB_DESPESA_LINHA', 'ARQUIVO_POR') IS NULL
            ALTER TABLE dbo.COLAB_DESPESA_LINHA ADD ARQUIVO_POR varchar(60) NOT NULL
                CONSTRAINT DF_COLAB_DESPESA_LINHA_ARQUIVO_POR DEFAULT '';
        IF COL_LENGTH('dbo.COLAB_DESPESA_LINHA', 'PHC_OBRANO') IS NULL
            ALTER TABLE dbo.COLAB_DESPESA_LINHA ADD PHC_OBRANO int NOT NULL
                CONSTRAINT DF_COLAB_DESPESA_LINHA_PHC_OBRANO DEFAULT 0;
        IF COL_LENGTH('dbo.COLAB_DESPESA_LINHA', 'PHC_NMDOS') IS NULL
            ALTER TABLE dbo.COLAB_DESPESA_LINHA ADD PHC_NMDOS varchar(80) NOT NULL
                CONSTRAINT DF_COLAB_DESPESA_LINHA_PHC_NMDOS DEFAULT '';
    """))
    db.session.execute(text("""
        IF OBJECT_ID('dbo.COLAB_DESPESA_CONTAB_LINHA', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.COLAB_DESPESA_CONTAB_LINHA (
                DESPCONTABSTAMP varchar(25) NOT NULL CONSTRAINT PK_COLAB_DESPESA_CONTAB PRIMARY KEY,
                DESPLINHASTAMP varchar(25) NOT NULL,
                ORDEM int NOT NULL CONSTRAINT DF_COLAB_DESPESA_CONTAB_ORDEM DEFAULT 10,
                ARTIGO_REF varchar(50) NOT NULL CONSTRAINT DF_COLAB_DESPESA_CONTAB_ARTIGO DEFAULT '',
                DESIGN nvarchar(200) NOT NULL CONSTRAINT DF_COLAB_DESPESA_CONTAB_DESIGN DEFAULT N'',
                REFERENCIA nvarchar(160) NOT NULL CONSTRAINT DF_COLAB_DESPESA_CONTAB_REFERENCIA DEFAULT N'',
                CCUSTO varchar(80) NOT NULL CONSTRAINT DF_COLAB_DESPESA_CONTAB_CCUSTO DEFAULT '',
                MATRICULA varchar(50) NOT NULL CONSTRAINT DF_COLAB_DESPESA_CONTAB_MATRICULA DEFAULT '',
                TABIVA int NOT NULL CONSTRAINT DF_COLAB_DESPESA_CONTAB_TABIVA DEFAULT 0,
                TAXAIVA decimal(9,4) NOT NULL CONSTRAINT DF_COLAB_DESPESA_CONTAB_TAXAIVA DEFAULT 0,
                TOTAL_SEM_IVA decimal(18,2) NOT NULL CONSTRAINT DF_COLAB_DESPESA_CONTAB_NET DEFAULT 0,
                VALOR_IVA decimal(18,2) NOT NULL CONSTRAINT DF_COLAB_DESPESA_CONTAB_IVA DEFAULT 0,
                TOTAL_COM_IVA decimal(18,2) NOT NULL CONSTRAINT DF_COLAB_DESPESA_CONTAB_GROSS DEFAULT 0,
                CAMPO_ORIGEM_JSON nvarchar(max) NOT NULL CONSTRAINT DF_COLAB_DESPESA_CONTAB_ORIGEM DEFAULT N'{}',
                DTCRI datetime NOT NULL CONSTRAINT DF_COLAB_DESPESA_CONTAB_DTCRI DEFAULT GETDATE(),
                DTALT datetime NULL,
                USERCRIACAO varchar(60) NOT NULL CONSTRAINT DF_COLAB_DESPESA_CONTAB_USERCRI DEFAULT '',
                USERALTERACAO varchar(60) NOT NULL CONSTRAINT DF_COLAB_DESPESA_CONTAB_USERALT DEFAULT '',
                CONSTRAINT FK_COLAB_DESPESA_CONTAB_LINHA FOREIGN KEY (DESPLINHASTAMP)
                    REFERENCES dbo.COLAB_DESPESA_LINHA (DESPLINHASTAMP)
            );
            CREATE INDEX IX_COLAB_DESPESA_CONTAB_DESPESA
                ON dbo.COLAB_DESPESA_CONTAB_LINHA (DESPLINHASTAMP, ORDEM, DTCRI);
        END

        IF OBJECT_ID('dbo.COLAB_DESPESA_HIST', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.COLAB_DESPESA_HIST (
                DESPHISTSTAMP varchar(25) NOT NULL CONSTRAINT PK_COLAB_DESPESA_HIST PRIMARY KEY,
                DESPLINHASTAMP varchar(25) NOT NULL,
                ACAO varchar(30) NOT NULL CONSTRAINT DF_COLAB_DESPESA_HIST_ACAO DEFAULT '',
                DETALHE_JSON nvarchar(max) NOT NULL CONSTRAINT DF_COLAB_DESPESA_HIST_DETALHE DEFAULT N'{}',
                UTILIZADOR varchar(60) NOT NULL CONSTRAINT DF_COLAB_DESPESA_HIST_USER DEFAULT '',
                DTCRI datetime NOT NULL CONSTRAINT DF_COLAB_DESPESA_HIST_DTCRI DEFAULT GETDATE()
            );
            CREATE INDEX IX_COLAB_DESPESA_HIST_DESPESA
                ON dbo.COLAB_DESPESA_HIST (DESPLINHASTAMP, DTCRI DESC);
        END

        IF OBJECT_ID('dbo.COLAB_DESPESA_LANCAMENTO', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.COLAB_DESPESA_LANCAMENTO (
                LANCAMENTO_CHAVE varchar(64) NOT NULL CONSTRAINT PK_COLAB_DESPESA_LANCAMENTO PRIMARY KEY,
                ESTADO varchar(20) NOT NULL CONSTRAINT DF_COLAB_DESPESA_LANC_ESTADO DEFAULT 'EM_CURSO',
                PHC_DB varchar(128) NOT NULL CONSTRAINT DF_COLAB_DESPESA_LANC_DB DEFAULT '',
                PHC_BOSTAMP varchar(25) NOT NULL CONSTRAINT DF_COLAB_DESPESA_LANC_BO DEFAULT '',
                PHC_OBRANO int NOT NULL CONSTRAINT DF_COLAB_DESPESA_LANC_NO DEFAULT 0,
                PHC_NMDOS varchar(80) NOT NULL CONSTRAINT DF_COLAB_DESPESA_LANC_DOC DEFAULT '',
                UTILIZADOR varchar(60) NOT NULL CONSTRAINT DF_COLAB_DESPESA_LANC_USER DEFAULT '',
                DTCRI datetime NOT NULL CONSTRAINT DF_COLAB_DESPESA_LANC_DTCRI DEFAULT GETDATE(),
                DTALT datetime NULL
            );
        END
    """))
    db.session.execute(text("""
        INSERT INTO dbo.COLAB_DESPESA_CONTAB_LINHA
            (DESPCONTABSTAMP, DESPLINHASTAMP, ORDEM, ARTIGO_REF, DESIGN, REFERENCIA,
             CCUSTO, MATRICULA, TABIVA, TAXAIVA, TOTAL_SEM_IVA, VALOR_IVA, TOTAL_COM_IVA,
             CAMPO_ORIGEM_JSON, USERCRIACAO, USERALTERACAO)
        SELECT LEFT(REPLACE(CONVERT(varchar(36), NEWID()), '-', ''), 25),
               L.DESPLINHASTAMP, 10, L.REF, L.DESIGN, L.REFERENCIA_DOCUMENTO,
               L.CCUSTO, L.VIATURA, L.TABIVA, L.TAXAIVA, L.VALOR_SEM_IVA, L.VALOR_IVA, L.VALOR,
               L.CAMPO_ORIGEM_JSON, L.USERCRIACAO, L.USERALTERACAO
        FROM dbo.COLAB_DESPESA_LINHA L
        WHERE NOT EXISTS (
            SELECT 1 FROM dbo.COLAB_DESPESA_CONTAB_LINHA C
            WHERE C.DESPLINHASTAMP = L.DESPLINHASTAMP
        );
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


def _expense_phc_target(feid: int) -> tuple[dict[str, Any], str]:
    """Resolve a Portal FEID to its PHC target, never to the active Portal DB."""
    company = _expense_company_by_feid(_safe_int(feid))
    if not company or not _safe_int(company.get('feid')):
        raise ExpensePhcConfigurationError('Empresa inválida.')
    phc_db = str(company.get('phc_db') or '').strip()
    if not phc_db:
        raise ExpensePhcConfigurationError('Empresa sem configuração PHC.')
    return company, _phc_conn_str(phc_db, str(company.get('phc_server') or '').strip())


def _phc_cursor_columns(cursor, table_name: str) -> set[str]:
    cursor.execute("""
        SELECT UPPER(COLUMN_NAME)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo' AND UPPER(TABLE_NAME) = UPPER(?)
    """, table_name)
    return {str(row[0] or '').strip().upper() for row in cursor.fetchall()}


def _pick_column(columns: set[str], candidates: list[str]) -> str:
    for candidate in candidates:
        if candidate.upper() in columns:
            return candidate.upper()
    return ''


def _sql_identifier(name: str) -> str:
    return '[' + str(name or '').replace(']', ']]') + ']'


def list_expense_vat_rates(feid: int) -> list[dict[str, Any]]:
    ensure_colaborador_despesas_schema()
    company, conn_str = _expense_phc_target(feid)

    try:
        with pyodbc.connect(conn_str, timeout=8) as conn:
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
    except ExpensePhcConfigurationError:
        raise
    except Exception as exc:
        current_app.logger.exception('Erro ao obter taxas de IVA da TAXASIVA do PHC.')
        raise ExpensePhcQueryError('Erro ao consultar o PHC.') from exc

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


def list_expense_cost_centers(limit: int = 500, feid: int = 0, with_description: bool = False, term: str = '') -> list[Any]:
    ensure_colaborador_despesas_schema()
    safe_limit = max(1, min(int(limit or 500), 1000))
    _, conn_str = _expense_phc_target(feid)
    clean_term = str(term or '').strip()
    try:
        with pyodbc.connect(conn_str, timeout=8) as conn:
            cursor = conn.cursor()
            columns = _phc_cursor_columns(cursor, 'CCT')
            if 'CCUSTO' not in columns:
                raise ExpensePhcQueryError('Erro ao consultar o PHC.')
            design_col = _pick_column(columns, ['U_DESIGN', 'DESIGN', 'DESCRICAO', 'NOME'])
            inactive_col = _pick_column(columns, ['INACTIVO', 'INATIVO'])
            design_expr = f"LTRIM(RTRIM(ISNULL(CONVERT(nvarchar(200), {_sql_identifier(design_col)}), '')))" if design_col else "CAST('' AS nvarchar(200))"
            inactive_filter = f"AND ISNULL({_sql_identifier(inactive_col)}, 0) = 0" if inactive_col else ''
            search_filter = f"AND (LTRIM(RTRIM(ISNULL(CCUSTO, ''))) LIKE ? OR {design_expr} LIKE ?)" if clean_term else ''
            params = [f'%{clean_term}%', f'%{clean_term}%'] if clean_term else []
            cursor.execute(f"""
                SELECT DISTINCT TOP {safe_limit}
                    LTRIM(RTRIM(ISNULL(CCUSTO, ''))) AS CCUSTO,
                    {design_expr} AS DESCRICAO
                FROM dbo.CCT
                WHERE LTRIM(RTRIM(ISNULL(CCUSTO, ''))) <> ''
                  {inactive_filter} {search_filter}
                ORDER BY LTRIM(RTRIM(ISNULL(CCUSTO, '')))
            """, params)
            rows = cursor.fetchall()
    except (ExpensePhcConfigurationError, ExpensePhcQueryError):
        raise
    except Exception as exc:
        current_app.logger.exception('Erro ao pesquisar centros de custo no PHC.')
        raise ExpensePhcQueryError('Erro ao consultar o PHC.') from exc
    if with_description:
        return [
            {'ccusto': str(row.CCUSTO or '').strip(), 'design': str(row.DESCRICAO or '').strip()}
            for row in rows if str(row.CCUSTO or '').strip()
        ]
    return [str(row.CCUSTO or '').strip() for row in rows if str(row.CCUSTO or '').strip()]


def _expense_cost_center_by_code(feid: int, code: str) -> str:
    """Return the canonical active PHC cost-centre code for an exact match."""
    clean_code = str(code or '').strip()
    if not clean_code:
        return ''
    _, conn_str = _expense_phc_target(feid)
    try:
        with pyodbc.connect(conn_str, timeout=8) as conn:
            cursor = conn.cursor()
            columns = _phc_cursor_columns(cursor, 'CCT')
            if 'CCUSTO' not in columns:
                raise ExpensePhcQueryError('Erro ao consultar o PHC.')
            inactive_col = _pick_column(columns, ['INACTIVO', 'INATIVO'])
            inactive_filter = f"AND ISNULL({_sql_identifier(inactive_col)}, 0) = 0" if inactive_col else ''
            cursor.execute(f"""
                SELECT TOP 1 LTRIM(RTRIM(ISNULL(CCUSTO, ''))) AS CCUSTO
                FROM dbo.CCT
                WHERE UPPER(LTRIM(RTRIM(ISNULL(CCUSTO, '')))) = UPPER(?)
                  {inactive_filter}
            """, clean_code)
            row = cursor.fetchone()
    except (ExpensePhcConfigurationError, ExpensePhcQueryError):
        raise
    except Exception as exc:
        current_app.logger.exception('Erro ao validar centro de custo no PHC.')
        raise ExpensePhcQueryError('Erro ao consultar o PHC.') from exc
    return str(row.CCUSTO or '').strip() if row else ''


def search_expense_articles(feid: int, term: str, limit: int = 12) -> list[dict[str, Any]]:
    ensure_colaborador_despesas_schema()
    clean_term = str(term or '').strip()
    if len(clean_term) < 1:
        return []
    safe_limit = max(1, min(int(limit or 12), 30))
    _, conn_str = _expense_phc_target(feid)
    try:
        with pyodbc.connect(conn_str, timeout=8) as conn:
            cursor = conn.cursor()
            columns = _phc_cursor_columns(cursor, 'ST')
            if not {'REF', 'DESIGN'}.issubset(columns):
                raise ExpensePhcQueryError('Erro ao consultar o PHC.')
            unidade_select = "LTRIM(RTRIM(ISNULL(S.UNIDADE, '')))" if 'UNIDADE' in columns else "CAST('' AS varchar(20))"
            familia_select = "LTRIM(RTRIM(ISNULL(S.FAMILIA, '')))" if 'FAMILIA' in columns else "CAST('' AS varchar(80))"
            inactive_column = _pick_column(columns, ['INACTIVO', 'INATIVO'])
            inactive_filter = f"AND ISNULL(S.{_sql_identifier(inactive_column)}, 0) = 0" if inactive_column else ''
            cursor.execute(f"""
                SELECT TOP {safe_limit}
                    LTRIM(RTRIM(ISNULL(S.REF, ''))) AS REF,
                    LTRIM(RTRIM(ISNULL(S.DESIGN, ''))) AS DESIGN,
                    {unidade_select} AS UNIDADE,
                    {familia_select} AS FAMILIA
                FROM dbo.ST S
                WHERE (LTRIM(RTRIM(ISNULL(S.REF, ''))) LIKE ?
                    OR LTRIM(RTRIM(ISNULL(S.DESIGN, ''))) LIKE ?)
                  {inactive_filter}
                ORDER BY CASE WHEN UPPER(LTRIM(RTRIM(ISNULL(S.REF, '')))) = UPPER(?) THEN 0 ELSE 1 END,
                         LTRIM(RTRIM(ISNULL(S.REF, '')))
            """, f'%{clean_term}%', f'%{clean_term}%', clean_term)
            rows = cursor.fetchall()
    except (ExpensePhcConfigurationError, ExpensePhcQueryError):
        raise
    except Exception as exc:
        current_app.logger.exception('Erro ao pesquisar artigos no PHC.')
        raise ExpensePhcQueryError('Erro ao consultar o PHC.') from exc
    return [
        {
            'ref': str(row.REF or '').strip(),
            'design': str(row.DESIGN or '').strip(),
            'unidade': str(row.UNIDADE or '').strip(),
            'familia': str(row.FAMILIA or '').strip(),
        }
        for row in rows
    ]


def search_expense_vehicles(term: str, limit: int = 12, feid: int = 0) -> list[dict[str, Any]]:
    ensure_colaborador_despesas_schema()
    clean_term = str(term or '').strip()
    if len(clean_term) < 1:
        return []
    safe_limit = max(1, min(int(limit or 12), 30))
    excluded_sql = ", ".join(f"'{plate}'" for plate in sorted(EXCLUDED_EXPENSE_PLATES))
    _, conn_str = _expense_phc_target(feid)
    try:
        conn = pyodbc.connect(conn_str, timeout=8)
        cursor = conn.cursor()
        cols = _phc_cursor_columns(cursor, 'VA')
    except ExpensePhcConfigurationError:
        raise
    except Exception as exc:
        current_app.logger.exception('Erro ao ligar ao PHC para pesquisar viaturas.')
        raise ExpensePhcQueryError('Erro ao consultar o PHC.') from exc
    if 'MATRICULA' not in cols:
        conn.close()
        raise ExpensePhcQueryError('Erro ao consultar o PHC.')
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
    try:
        params = [f'%{clean_term}%'] * len(search_parts)
        cursor.execute(f"""
            SELECT TOP {safe_limit}
                LTRIM(RTRIM(ISNULL(MATRICULA, ''))) AS MATRICULA,
                {marca_select}, {modelo_select}, {nofrota_select}
            FROM dbo.VA
            WHERE LTRIM(RTRIM(ISNULL(MATRICULA, ''))) <> ''
              AND UPPER(LTRIM(RTRIM(ISNULL(MATRICULA, '')))) NOT IN ({excluded_sql})
              {inactive_filter}
              AND ({' OR '.join(part.replace(':term', '?') for part in search_parts)})
            ORDER BY CASE WHEN UPPER(LTRIM(RTRIM(ISNULL(MATRICULA, '')))) = UPPER(?) THEN 0 ELSE 1 END,
                     LTRIM(RTRIM(ISNULL(MATRICULA, '')))
        """, params + [clean_term])
        rows = cursor.fetchall()
    except Exception as exc:
        current_app.logger.exception('Erro ao pesquisar viaturas no PHC.')
        raise ExpensePhcQueryError('Erro ao consultar o PHC.') from exc
    finally:
        conn.close()
    return [
        {
            'matricula': str(row.MATRICULA or '').strip(),
            'marca': str(row.MARCA or '').strip(),
            'modelo': str(row.MODELO or '').strip(),
            'nofrota': str(row.NOFROTA or '').strip(),
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
          AND ESTADO IN ('RASCUNHO', 'FECHADO', 'DEVOLVIDA')
          AND LTRIM(RTRIM(ISNULL(PHC_BOSTAMP, ''))) = ''
        ORDER BY ORDEM, DTCRI
    """), {'header_stamp': str(header_stamp or '').strip()}).mappings().all()
    return [serialize_line(row) for row in rows]


def list_expense_processing_users(filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    ensure_colaborador_despesas_schema()
    filters = filters or {}
    clauses = [
        "ISNULL(L.ANULADA, 0) = 0",
        "UPPER(LTRIM(RTRIM(ISNULL(L.ESTADO, '')))) = 'FECHADO'",
        "LTRIM(RTRIM(ISNULL(L.PHC_BOSTAMP, ''))) = ''",
    ]
    params: dict[str, Any] = {}
    if str(filters.get('date_from') or '').strip():
        clauses.append("L.DATA_DESPESA >= TRY_CONVERT(date, :date_from)")
        params['date_from'] = str(filters.get('date_from')).strip()
    if str(filters.get('date_to') or '').strip():
        clauses.append("L.DATA_DESPESA <= TRY_CONVERT(date, :date_to)")
        params['date_to'] = str(filters.get('date_to')).strip()
    rows = db.session.execute(text(f"""
        SELECT
            LTRIM(RTRIM(ISNULL(H.LOGIN, ''))) AS LOGIN,
            LTRIM(RTRIM(ISNULL(H.PENOME, ''))) AS PENOME,
            ISNULL(H.PENO, 0) AS PENO,
            COUNT(1) AS TOTAL
        FROM dbo.COLAB_DESPESA_LINHA L
        INNER JOIN dbo.COLAB_DESPESA_CAB H
          ON H.DESPCABSTAMP = L.DESPCABSTAMP
        WHERE {' AND '.join(clauses)}
        GROUP BY
            LTRIM(RTRIM(ISNULL(H.LOGIN, ''))),
            LTRIM(RTRIM(ISNULL(H.PENOME, ''))),
            ISNULL(H.PENO, 0)
        ORDER BY LTRIM(RTRIM(ISNULL(H.PENOME, ''))), LTRIM(RTRIM(ISNULL(H.LOGIN, '')))
    """), params).mappings().all()
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
        ORDER BY L.DATA_DESPESA ASC, H.PENOME, L.DTCRI ASC
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
        company_data = _expense_company_by_feid(int(item.get('feid') or 0))
        item['moeda'] = _expense_company_currency(company_data, item.get('moeda'))
        items.append(item)
    _attach_processing_details(items)
    return items


def _json_object(value: Any) -> dict[str, Any]:
    try:
        parsed = json.loads(str(value or '{}'))
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def _serialize_accounting_line(row: dict[str, Any]) -> dict[str, Any]:
    return {
        'stamp': str(row.get('DESPCONTABSTAMP') or '').strip(),
        'ordem': int(row.get('ORDEM') or 0),
        'artigo_ref': str(row.get('ARTIGO_REF') or '').strip(),
        'design': str(row.get('DESIGN') or '').strip(),
        'referencia': str(row.get('REFERENCIA') or '').strip(),
        'ccusto': str(row.get('CCUSTO') or '').strip(),
        'matricula': str(row.get('MATRICULA') or '').strip(),
        'tabiva': str(row.get('TABIVA') or '').strip(),
        'taxaiva': float(row.get('TAXAIVA') or 0),
        'total_sem_iva': float(row.get('TOTAL_SEM_IVA') or 0),
        'valor_iva': float(row.get('VALOR_IVA') or 0),
        'total_com_iva': float(row.get('TOTAL_COM_IVA') or 0),
        'origens': _json_object(row.get('CAMPO_ORIGEM_JSON')),
    }


def _attach_processing_details(items: list[dict[str, Any]]) -> None:
    stamps = [str(item.get('stamp') or '').strip() for item in items if item.get('stamp')]
    if not stamps:
        return
    params = {f's{i}': stamp for i, stamp in enumerate(stamps)}
    in_sql = ', '.join(f':s{i}' for i in range(len(stamps)))
    rows = db.session.execute(text(f"""
        SELECT *
        FROM dbo.COLAB_DESPESA_CONTAB_LINHA
        WHERE DESPLINHASTAMP IN ({in_sql})
        ORDER BY DESPLINHASTAMP, ORDEM, DTCRI
    """), params).mappings().all()
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row.get('DESPLINHASTAMP') or '').strip(), []).append(_serialize_accounting_line(row))
    for item in items:
        accounting = grouped.get(str(item.get('stamp') or ''), [])
        item['accounting_lines'] = accounting
        item['version'] = int(item.get('version') or 1)
        item['origens'] = item.get('origens') or {}
        net = sum(Decimal(str(line.get('total_sem_iva') or 0)) for line in accounting)
        vat = sum(Decimal(str(line.get('valor_iva') or 0)) for line in accounting)
        gross = sum(Decimal(str(line.get('total_com_iva') or 0)) for line in accounting)
        item['linhas_total_sem_iva'] = float(net.quantize(Decimal('0.01')))
        item['linhas_total_iva'] = float(vat.quantize(Decimal('0.01')))
        item['linhas_total_com_iva'] = float(gross.quantize(Decimal('0.01')))
        item['diferenca'] = float((Decimal(str(item.get('valor') or 0)) - gross).quantize(Decimal('0.01')))


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
        'moeda': str(row.get('MOEDA') or 'EUR').strip() or 'EUR',
        'referencia_documento': str(row.get('REFERENCIA_DOCUMENTO') or '').strip(),
        'origens': _json_object(row.get('CAMPO_ORIGEM_JSON')),
        'version': int(row.get('VERSION') or 1),
        'arquivo_estado': str(row.get('ARQUIVO_ESTADO') or '').strip(),
        'phc_obrano': int(row.get('PHC_OBRANO') or 0),
        'phc_nmdos': str(row.get('PHC_NMDOS') or '').strip(),
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
    was_returned = False
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
        was_returned = str(existing.get('ESTADO') or '').strip().upper() == 'DEVOLVIDA'
        if str(existing.get('ESTADO') or '').strip().upper() not in {'RASCUNHO', 'DEVOLVIDA'}:
            raise ValueError('Despesa fechada.')

    file_payload = None
    try:
        if file_storage:
            file_payload = _store_line_file(file_storage, header_stamp, line_stamp)
            acquire_duplicate_lock(db.session, file_payload.get('hash'))
            duplicate = find_exact_file_duplicate(
                db.session,
                file_payload.get('hash'),
                exclude_expense_id=line_stamp,
            )
            if duplicate:
                try:
                    absolute_path = os.path.join(current_app.root_path, file_payload['path'].lstrip('/'))
                    if os.path.isfile(absolute_path):
                        os.remove(absolute_path)
                except OSError:
                    current_app.logger.warning('Não foi possível remover comprovativo duplicado.', exc_info=True)
                source_label = 'Documents AI' if duplicate.get('source_area') == 'document_ai' else 'Despesas'
                raise ValueError(
                    f"Este comprovativo já existe em {source_label} "
                    f"({duplicate.get('file_name') or duplicate.get('record_id')})."
                )
    except Exception:
        # A linha nova ainda não pode sobreviver a uma validação de ficheiro falhada.
        db.session.rollback()
        raise

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
    if was_returned:
        _record_expense_history(line_stamp, 'CORRECAO_COLABORADOR', {}, login)
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


def _legacy_update_expense_processing_classification(line_stamp: str, payload: dict[str, Any], user) -> dict[str, Any]:
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


def update_expense_processing_classification(line_stamp: str, payload: dict[str, Any], user) -> dict[str, Any]:
    """Persist an expense and all of its accounting lines with optimistic locking."""
    ensure_colaborador_despesas_schema()
    stamp = str(line_stamp or payload.get('stamp') or '').strip()
    if not stamp:
        raise ValueError('Despesa inválida.')
    expected_version = _safe_int(payload.get('version'), 0)
    if expected_version <= 0:
        raise ValueError('A versão da despesa é obrigatória. Atualiza a lista e tenta novamente.')

    current = db.session.execute(text("""
        SELECT TOP 1 * FROM dbo.COLAB_DESPESA_LINHA WITH (UPDLOCK, ROWLOCK)
        WHERE DESPLINHASTAMP = :stamp
          AND ISNULL(ANULADA, 0) = 0
          AND UPPER(LTRIM(RTRIM(ISNULL(ESTADO, '')))) = 'FECHADO'
          AND LTRIM(RTRIM(ISNULL(PHC_BOSTAMP, ''))) = ''
    """), {'stamp': stamp}).mappings().first()
    if not current:
        raise ValueError('Despesa não encontrada.')
    if int(current.get('VERSION') or 1) != expected_version:
        raise ValueError('Despesa alterada por outro utilizador.')

    feid = _safe_int(payload.get('feid') or current.get('FEID'))
    company = _expense_company_by_feid(feid) if feid else {}
    if not company:
        raise ValueError('Escolhe uma empresa válida.')
    login = str(getattr(user, 'LOGIN', '') or getattr(user, 'login', '') or '').strip()
    expense_date = str(payload.get('data_despesa') or current.get('DATA_DESPESA') or '').strip()[:10] or None
    currency = _expense_company_currency(company, payload.get('moeda') or current.get('MOEDA'))[:10]
    # OBS belongs to the collaborator and is immutable in CdG.
    comment = str(current.get('OBS') or '').strip()[:100]
    lines = payload.get('accounting_lines')
    if not isinstance(lines, list) or not lines:
        raise ValueError('A despesa tem de ter pelo menos uma linha contabilística.')

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    cost_center_cache: dict[str, str] = {}
    valid_rates = {str(value.get('tabiva') or '').strip(): value for value in list_expense_vat_rates(feid)}
    for index, raw in enumerate(lines, start=1):
        raw = raw if isinstance(raw, dict) else {}
        line_id = str(raw.get('stamp') or '').strip()[:25]
        if not line_id or line_id in seen:
            line_id = _new_stamp()
        seen.add(line_id)
        gross = _safe_decimal(raw.get('total_com_iva'))
        rate = _safe_decimal(raw.get('taxaiva'))
        if gross < 0 and not bool(getattr(user, 'ADMIN', False)):
            raise ValueError('Os valores negativos não estão autorizados neste ecrã.')
        net, vat = _vat_amounts_from_gross(gross, rate)
        submitted_net = _safe_decimal(raw.get('total_sem_iva'))
        submitted_vat = _safe_decimal(raw.get('valor_iva'))
        if ('total_sem_iva' in raw and abs(submitted_net - net) > Decimal('0.01')) or (
            'valor_iva' in raw and abs(submitted_vat - vat) > Decimal('0.01')
        ):
            raise ValueError('Totais incoerentes.')
        article_ref = str(raw.get('artigo_ref') or '').strip()
        if not article_ref:
            raise ValueError('Escolhe um Artigo.')
        article_matches = search_expense_articles(feid, article_ref, limit=30)
        article = next((value for value in article_matches if str(value.get('ref') or '').strip().casefold() == article_ref.casefold()), None)
        if not article:
            raise ValueError('Artigo não encontrado.')
        ccusto = str(raw.get('ccusto') or '').strip()
        ccusto_key = ccusto.casefold()
        if ccusto_key not in cost_center_cache:
            cost_center_cache[ccusto_key] = _expense_cost_center_by_code(feid, ccusto)
        canonical_ccusto = cost_center_cache[ccusto_key]
        if ccusto and not canonical_ccusto:
            raise ValueError('Centro de Custo não encontrado.')
        plate = str(raw.get('matricula') or '').strip()
        if plate:
            vehicles = search_expense_vehicles(plate, limit=30, feid=feid)
            if not any(str(value.get('matricula') or '').strip().casefold() == plate.casefold() for value in vehicles):
                raise ValueError('Matrícula não encontrada.')
        tabiva = str(raw.get('tabiva') or '').strip()
        if tabiva not in valid_rates or abs(_safe_decimal(valid_rates[tabiva].get('taxaiva')) - rate) > Decimal('0.0001'):
            raise ValueError('Taxa de IVA não encontrada para a Empresa.')
        origins = raw.get('origens') if isinstance(raw.get('origens'), dict) else {}
        normalized.append({
            'stamp': line_id,
            'expense_stamp': stamp,
            'order': index * 10,
            'article': str(article.get('ref') or '').strip()[:50],
            'design': str(article.get('design') or '').strip()[:200],
            'reference': str(raw.get('referencia') or '').strip()[:160],
            'ccusto': canonical_ccusto[:80],
            'plate': plate[:50],
            'tabiva': _safe_int(tabiva),
            'taxaiva': rate,
            'net': net,
            'vat': vat,
            'gross': gross,
            'origins': json.dumps(origins, ensure_ascii=False),
            'login': login,
        })

    first = normalized[0]
    total_gross = sum((line['gross'] for line in normalized), Decimal('0.00')).quantize(Decimal('0.01'))
    db.session.execute(text("""
        UPDATE dbo.COLAB_DESPESA_LINHA
        SET DATA_DESPESA = TRY_CONVERT(date, :expense_date),
            FEID = :feid, EMPRESA = :empresa, MOEDA = :currency, OBS = :comment,
            REF = :article, DESIGN = :design, REFERENCIA_DOCUMENTO = :reference,
            CCUSTO = :ccusto, VIATURA = :plate, TABIVA = :tabiva, TAXAIVA = :taxaiva,
            VALOR_SEM_IVA = :net, VALOR_IVA = :vat, VALOR = :expense_value,
            VERSION = VERSION + 1, DTALT = GETDATE(), USERALTERACAO = :login
        WHERE DESPLINHASTAMP = :stamp AND VERSION = :expected_version
    """), {
        'stamp': stamp, 'expense_date': expense_date, 'feid': feid,
        'empresa': str(company.get('nome') or '').strip()[:200], 'currency': currency,
        'comment': comment, 'article': first['article'], 'design': first['design'],
        'reference': first['reference'], 'ccusto': first['ccusto'], 'plate': first['plate'],
        'tabiva': first['tabiva'], 'taxaiva': first['taxaiva'], 'net': first['net'],
        'vat': first['vat'], 'expense_value': _safe_decimal(payload.get('valor') if 'valor' in payload else current.get('VALOR')),
        'login': login, 'expected_version': expected_version,
    })
    db.session.execute(text("DELETE FROM dbo.COLAB_DESPESA_CONTAB_LINHA WHERE DESPLINHASTAMP = :stamp"), {'stamp': stamp})
    for line in normalized:
        db.session.execute(text("""
            INSERT INTO dbo.COLAB_DESPESA_CONTAB_LINHA
                (DESPCONTABSTAMP, DESPLINHASTAMP, ORDEM, ARTIGO_REF, DESIGN, REFERENCIA,
                 CCUSTO, MATRICULA, TABIVA, TAXAIVA, TOTAL_SEM_IVA, VALOR_IVA, TOTAL_COM_IVA,
                 CAMPO_ORIGEM_JSON, USERCRIACAO, USERALTERACAO)
            VALUES (:stamp, :expense_stamp, :order, :article, :design, :reference,
                    :ccusto, :plate, :tabiva, :taxaiva, :net, :vat, :gross,
                    :origins, :login, :login)
        """), line)
    _record_expense_history(stamp, 'ALTERADA', {'version': expected_version + 1, 'linhas': len(normalized), 'total_linhas': float(total_gross)}, login)
    db.session.commit()
    row = db.session.execute(text("SELECT TOP 1 * FROM dbo.COLAB_DESPESA_LINHA WHERE DESPLINHASTAMP = :stamp"), {'stamp': stamp}).mappings().first()
    item = serialize_line(row or {})
    _attach_processing_details([item])
    return {'ok': True, 'line': item}


def _record_expense_history(stamp: str, action: str, detail: dict[str, Any], login: str) -> None:
    db.session.execute(text("""
        INSERT INTO dbo.COLAB_DESPESA_HIST
            (DESPHISTSTAMP, DESPLINHASTAMP, ACAO, DETALHE_JSON, UTILIZADOR)
        VALUES (:hist, :stamp, :action, :detail, :login)
    """), {
        'hist': _new_stamp(), 'stamp': stamp, 'action': str(action or '')[:30],
        'detail': json.dumps(detail or {}, ensure_ascii=False, default=str), 'login': str(login or '')[:60],
    })


def _phc_columns(cursor, table_name: str) -> set[str]:
    cursor.execute("""
        SELECT LOWER(COLUMN_NAME)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo'
          AND TABLE_NAME = ?
    """, table_name)
    return {str(row[0] or '').strip().lower() for row in cursor.fetchall()}


def _phc_character_maximum_length(cursor, table_name: str, column_name: str) -> int | None:
    """Returns a text column limit from the target PHC database."""
    cursor.execute("""
        SELECT CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo'
          AND TABLE_NAME = ?
          AND COLUMN_NAME = ?
    """, table_name, column_name)
    row = cursor.fetchone()
    try:
        length = int(row[0]) if row and row[0] is not None else 0
    except (TypeError, ValueError):
        length = 0
    return length if length > 0 else None


def _phc_text(value: Any, maximum_length: int | None, fallback_length: int) -> str:
    text_value = str(value or '').strip()
    return text_value[:maximum_length or fallback_length]


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


def _employee_taxpayer(cursor, peno: int) -> dict[str, str]:
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
    return {
        'ncont': ncont,
        'nome': str(pe.NOME or '').strip(),
    }


def _resolve_phc_supplier(cursor, ncont: str, employee_name: str = '') -> dict[str, Any]:
    ncont = str(ncont or '').strip()
    if not ncont:
        raise ValueError('O colaborador não tem contribuinte preenchido.')
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
        employee_label = str(employee_name or '').strip() or 'selecionado'
        raise ValueError(f'Não existe fornecedor FL ativo com contribuinte {ncont} para o colaborador {employee_label}.')
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

    currency = str((prepared_lines[0].get('row') or {}).get('MOEDA') or 'EUR').strip().upper() or 'EUR'
    total_gross = (total_net + total_vat).quantize(Decimal("0.01"))
    y = _draw_text_line(pdf, margin, y, f"Total sem IVA: {_decimal_label(total_net, 2)} {currency}", 10, True)
    y = _draw_text_line(pdf, margin, y, f"IVA: {_decimal_label(total_vat, 2)} {currency}", 10, True)
    y = _draw_text_line(pdf, margin, y, f"Total com IVA: {_decimal_label(total_gross, 2)} {currency}", 10, True)
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
            f"{_decimal_label(line.get('gross'), 2)} {currency}",
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

        attached_expenses: set[str] = set()
        for index, line in enumerate(prepared_lines, start=1):
            row = line["row"]
            expense_stamp = str(row.get("DESPLINHASTAMP") or "")
            if expense_stamp in attached_expenses:
                continue
            attached_expenses.add(expense_stamp)
            source = _expense_local_file_path(str(row.get("CAMINHO") or ""))
            if not source:
                continue
            ext = os.path.splitext(source)[1].lower()
            currency = str(row.get('MOEDA') or 'EUR').strip().upper() or 'EUR'
            title = f"Anexo {index} - {row.get('DATA_DESPESA') or ''} - {row.get('TIPO') or ''} - {_decimal_label(row.get('VALOR'), 2)} {currency}"
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
            H.PHC_DB,
            H.PHC_SERVER,
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
    result = [dict(row) for row in rows]
    items = [{'stamp': str(row.get('DESPLINHASTAMP') or '')} for row in result]
    _attach_processing_details(items)
    line_map = {str(item.get('stamp') or ''): item.get('accounting_lines') or [] for item in items}
    for row in result:
        row['ACCOUNTING_LINES'] = line_map.get(str(row.get('DESPLINHASTAMP') or ''), [])
    return result


def _expense_launch_preflight(lines: list[dict[str, Any]], company: dict[str, Any]) -> list[str]:
    """Validate the complete batch before any PHC row or launch lock is created."""
    errors: list[str] = []
    phc_db = str(company.get('phc_db') or '').strip()
    phc_server = str(company.get('phc_server') or '').strip()
    currencies = {str(row.get('MOEDA') or '').strip().upper() for row in lines}
    if any(not re.fullmatch(r'[A-Z]{3}', currency or '') for currency in currencies):
        errors.append('Moeda ISO inválida.')
    for row in lines:
        label = str(row.get('DATA_DESPESA') or row.get('DESPLINHASTAMP') or 'Despesa')
        if row.get('VALOR') is None:
            errors.append(f'{label}: total em falta.')
        if not str(row.get('CAMINHO') or '').strip():
            errors.append(f'{label}: justificativo em falta.')
        accounting = row.get('ACCOUNTING_LINES') or []
        if not accounting:
            errors.append(f'{label}: sem linha contabilística.')
        for index, accounting_line in enumerate(accounting, start=1):
            prefix = f'{label}, linha {index}'
            if not str(accounting_line.get('artigo_ref') or '').strip():
                errors.append(f'{prefix}: Artigo em falta.')
            if not str(accounting_line.get('ccusto') or '').strip():
                errors.append(f'{prefix}: Centro de Custo em falta.')
            if not str(accounting_line.get('tabiva') or '').strip():
                errors.append(f'{prefix}: IVA em falta.')
            gross = _safe_decimal(accounting_line.get('total_com_iva'))
            net = _safe_decimal(accounting_line.get('total_sem_iva'))
            vat = _safe_decimal(accounting_line.get('valor_iva'))
            if gross < 0:
                errors.append(f'{prefix}: valor negativo não autorizado.')
            if abs((net + vat) - gross) > Decimal('0.01'):
                errors.append(f'{prefix}: Totais incoerentes.')
    if errors or not phc_db:
        if not phc_db:
            errors.append('Empresa sem configuração PHC.')
        return errors

    try:
        with pyodbc.connect(_phc_conn_str(phc_db, phc_server), timeout=15) as target_conn:
            cursor = target_conn.cursor()
            valid_rates = {str(rate.get('tabiva') or '').strip(): _safe_decimal(rate.get('taxaiva')) for rate in _phc_tax_rates(cursor)}
            for row in lines:
                label = str(row.get('DATA_DESPESA') or row.get('DESPLINHASTAMP') or 'Despesa')
                for index, accounting_line in enumerate(row.get('ACCOUNTING_LINES') or [], start=1):
                    ref = str(accounting_line.get('artigo_ref') or '').strip()
                    try:
                        _phc_article(cursor, ref)
                    except ValueError:
                        errors.append(f'{label}, linha {index}: Artigo PHC inválido.')
                    ccusto = str(accounting_line.get('ccusto') or '').strip()
                    if ccusto:
                        found = cursor.execute("SELECT TOP 1 1 FROM dbo.CCT WHERE UPPER(LTRIM(RTRIM(ISNULL(CCUSTO,''))))=UPPER(?) AND ISNULL(INACTIVO,0)=0", ccusto).fetchone()
                        if not found:
                            errors.append(f'{label}, linha {index}: Centro de Custo inválido.')
                    tabiva = str(accounting_line.get('tabiva') or '').strip()
                    rate = _safe_decimal(accounting_line.get('taxaiva'))
                    if tabiva not in valid_rates or abs(valid_rates[tabiva] - rate) > Decimal('0.0001'):
                        errors.append(f'{label}, linha {index}: IVA inválido para a Empresa.')
            source_company = _expense_company_by_feid(_safe_int(lines[0].get('PEFEID')))
            employee_db = str(lines[0].get('PHC_DB') or source_company.get('phc_db') or '').strip()
            employee_server = str(lines[0].get('PHC_SERVER') or source_company.get('phc_server') or '').strip()
            if not _safe_int(lines[0].get('PENO')):
                errors.append('Número PHC do colaborador em falta.')
            elif not employee_db:
                errors.append('Empresa do colaborador sem configuração PHC.')
            else:
                try:
                    if employee_db.upper() == phc_db.upper():
                        employee = _employee_taxpayer(cursor, _safe_int(lines[0].get('PENO')))
                    else:
                        with pyodbc.connect(_phc_conn_str(employee_db, employee_server), timeout=15) as source_conn:
                            employee = _employee_taxpayer(source_conn.cursor(), _safe_int(lines[0].get('PENO')))
                    _resolve_phc_supplier(cursor, employee['ncont'], employee['nome'])
                except ValueError as exc:
                    errors.append(str(exc))
    except Exception as exc:
        current_app.logger.exception('Erro no controlo integral de despesas no PHC.')
        errors.append('Erro ao consultar o PHC durante o controlo integral.')
    return errors


def launch_expenses_to_phc(stamps: list[str], user) -> dict[str, Any]:
    ensure_colaborador_despesas_schema()
    requested_stamps = sorted({str(stamp or '').strip() for stamp in stamps if str(stamp or '').strip()})
    if not requested_stamps:
        raise ValueError('Seleciona pelo menos uma despesa.')
    batch_key = hashlib.sha256('|'.join(requested_stamps).encode('utf-8')).hexdigest()
    previous = db.session.execute(text("""
        SELECT TOP 1 * FROM dbo.COLAB_DESPESA_LANCAMENTO
        WHERE LANCAMENTO_CHAVE=:batch_key
    """), {'batch_key': batch_key}).mappings().first()
    previous_state = str((previous or {}).get('ESTADO') or '').strip().upper()
    if previous_state in {'PHC_CRIADO', 'LANCADO'}:
        params = {f's{i}': stamp for i, stamp in enumerate(requested_stamps)}
        in_sql = ', '.join(f':s{i}' for i in range(len(requested_stamps)))
        params.update({
            'bostamp': str(previous.get('PHC_BOSTAMP') or ''),
            'obrano': int(previous.get('PHC_OBRANO') or 0),
            'nmdos': str(previous.get('PHC_NMDOS') or PHC_NOTES_FRAIS_NMDOS),
        })
        db.session.execute(text(f"""
            UPDATE dbo.COLAB_DESPESA_LINHA SET PHC_STATUS='LANCADO',
                PHC_BOSTAMP=:bostamp, PHC_OBRANO=:obrano, PHC_NMDOS=:nmdos,
                ARQUIVO_ESTADO='LANCADA', ARQUIVO_DATA=COALESCE(ARQUIVO_DATA,GETDATE()),
                PHC_DTENVIO=COALESCE(PHC_DTENVIO,GETDATE())
            WHERE DESPLINHASTAMP IN ({in_sql})
              AND LTRIM(RTRIM(ISNULL(PHC_BOSTAMP,''))) IN ('', :bostamp)
        """), params)
        db.session.execute(text("""
            UPDATE dbo.COLAB_DESPESA_LANCAMENTO SET ESTADO='LANCADO', DTALT=GETDATE()
            WHERE LANCAMENTO_CHAVE=:batch_key
        """), {'batch_key': batch_key})
        db.session.commit()
        return {
            'ok': True, 'recovered': True,
            'phc_db': str(previous.get('PHC_DB') or ''),
            'bostamp': str(previous.get('PHC_BOSTAMP') or ''),
            'obrano': int(previous.get('PHC_OBRANO') or 0),
            'nmdos': str(previous.get('PHC_NMDOS') or PHC_NOTES_FRAIS_NMDOS),
            'linhas': len(requested_stamps),
        }
    lines = _load_processing_lines_for_launch(stamps)
    feids = {int(row.get('LINHA_FEID') or 0) for row in lines}
    logins = {str(row.get('LOGIN') or '').strip().lower() for row in lines}
    penos = {int(row.get('PENO') or 0) for row in lines}
    currencies = {str(row.get('MOEDA') or 'EUR').strip().upper() or 'EUR' for row in lines}
    if len(feids) != 1:
        raise ValueError('Só podes lançar despesas da mesma empresa de cada vez.')
    if len(logins) != 1 or len(penos) != 1:
        raise ValueError('Só podes lançar despesas do mesmo colaborador de cada vez.')
    if len(currencies) != 1:
        raise ValueError('Só podes lançar despesas da mesma moeda de cada vez.')

    feid = next(iter(feids))
    peno = next(iter(penos))
    company = _expense_company_by_feid(feid)
    phc_db = str(company.get('phc_db') or '').strip() or _phc_db_hint(str(company.get('nome') or lines[0].get('LINHA_EMPRESA') or ''))
    phc_server = str(company.get('phc_server') or '').strip()
    if not phc_db:
        raise ValueError('A empresa selecionada não tem base de dados PHC configurada.')
    validation_errors = _expense_launch_preflight(lines, company)
    if validation_errors:
        raise ValueError('Não foi possível validar:\n' + '\n'.join(validation_errors))

    marker = f'EXP:{batch_key[:24]}'
    existing_launch = db.session.execute(text("""
        SELECT TOP 1 * FROM dbo.COLAB_DESPESA_LANCAMENTO WITH (UPDLOCK, HOLDLOCK)
        WHERE LANCAMENTO_CHAVE = :batch_key
    """), {'batch_key': batch_key}).mappings().first()
    owns_launch = not bool(existing_launch) or str((existing_launch or {}).get('ESTADO') or '').upper() == 'FALHOU'
    if owns_launch:
        launch_params = {
            'batch_key': batch_key, 'phc_db': phc_db,
            'login': str(getattr(user, 'LOGIN', '') or getattr(user, 'login', '') or '').strip(),
        }
        if existing_launch:
            db.session.execute(text("""
                UPDATE dbo.COLAB_DESPESA_LANCAMENTO SET ESTADO='EM_CURSO', PHC_DB=:phc_db,
                    UTILIZADOR=:login, DTALT=GETDATE() WHERE LANCAMENTO_CHAVE=:batch_key
            """), launch_params)
        else:
            db.session.execute(text("""
                INSERT INTO dbo.COLAB_DESPESA_LANCAMENTO
                    (LANCAMENTO_CHAVE, ESTADO, PHC_DB, UTILIZADOR)
                VALUES (:batch_key, 'EM_CURSO', :phc_db, :login)
            """), launch_params)
        db.session.commit()
    else:
        db.session.commit()
        if str(existing_launch.get('ESTADO') or '').upper() == 'LANCADO':
            return {
                'ok': True, 'recovered': True, 'phc_db': str(existing_launch.get('PHC_DB') or ''),
                'bostamp': str(existing_launch.get('PHC_BOSTAMP') or ''),
                'obrano': int(existing_launch.get('PHC_OBRANO') or 0),
                'nmdos': str(existing_launch.get('PHC_NMDOS') or PHC_NOTES_FRAIS_NMDOS),
                'linhas': len(lines),
            }
        with pyodbc.connect(_phc_conn_str(phc_db, phc_server), timeout=15) as recovery_conn:
            recovery_cursor = recovery_conn.cursor()
            bo_columns = _phc_columns(recovery_cursor, 'BO')
            if 'maquina' in bo_columns:
                recovered = recovery_cursor.execute(
                    "SELECT TOP 1 BOSTAMP, OBRANO, NMDOS FROM dbo.BO WHERE NDOS=? AND MAQUINA=?",
                    PHC_NOTES_FRAIS_NDOS, marker,
                ).fetchone()
                if recovered:
                    recovered_bostamp, recovered_obrano, recovered_nmdos = str(recovered[0] or ''), int(recovered[1] or 0), str(recovered[2] or PHC_NOTES_FRAIS_NMDOS)
                    for row in lines:
                        expense_stamp = str(row.get('DESPLINHASTAMP') or '')
                        db.session.execute(text("""
                            UPDATE dbo.COLAB_DESPESA_LINHA SET PHC_STATUS='LANCADO',
                                PHC_BOSTAMP=:bostamp, PHC_OBRANO=:obrano, PHC_NMDOS=:nmdos,
                                ARQUIVO_ESTADO='LANCADA', ARQUIVO_DATA=GETDATE(), PHC_DTENVIO=GETDATE()
                            WHERE DESPLINHASTAMP=:stamp
                        """), {'stamp': expense_stamp, 'bostamp': recovered_bostamp, 'obrano': recovered_obrano, 'nmdos': recovered_nmdos})
                    db.session.execute(text("""
                        UPDATE dbo.COLAB_DESPESA_LANCAMENTO SET ESTADO='LANCADO',
                            PHC_BOSTAMP=:bostamp, PHC_OBRANO=:obrano, PHC_NMDOS=:nmdos, DTALT=GETDATE()
                        WHERE LANCAMENTO_CHAVE=:batch_key
                    """), {'batch_key': batch_key, 'bostamp': recovered_bostamp, 'obrano': recovered_obrano, 'nmdos': recovered_nmdos})
                    db.session.commit()
                    return {'ok': True, 'recovered': True, 'phc_db': phc_db, 'bostamp': recovered_bostamp, 'obrano': recovered_obrano, 'nmdos': recovered_nmdos, 'linhas': len(lines)}
        raise ValueError('Este lançamento já está em processamento. Atualiza a lista antes de tentar novamente.')

    # The employee record belongs to the company in the user's profile. The
    # destination company may be different, so resolve the employee's NIF in
    # the source PE first and only then look up FL.NCONT in the destination.
    source_company = _expense_company_by_feid(_safe_int(lines[0].get('PEFEID')))
    employee_phc_db = str(lines[0].get('PHC_DB') or source_company.get('phc_db') or '').strip()
    employee_phc_server = str(lines[0].get('PHC_SERVER') or source_company.get('phc_server') or '').strip()
    if not employee_phc_db:
        raise ValueError('A empresa do colaborador não tem base de dados PHC configurada.')

    login = str(getattr(user, 'LOGIN', '') or getattr(user, 'login', '') or '').strip() or 'APP'
    user_inis = login[:3].upper() or 'APP'
    today_value = date.today()
    dataobra = today_value

    with pyodbc.connect(_phc_conn_str(phc_db, phc_server), timeout=30) as conn:
        conn.autocommit = False
        cursor = conn.cursor()
        pdf_info: dict[str, Any] = {}
        try:
            if employee_phc_db.upper() == phc_db.upper():
                employee = _employee_taxpayer(cursor, peno)
            else:
                with pyodbc.connect(_phc_conn_str(employee_phc_db, employee_phc_server), timeout=30) as employee_conn:
                    employee = _employee_taxpayer(employee_conn.cursor(), peno)
            supplier = _resolve_phc_supplier(cursor, employee['ncont'], employee['nome'])
            company_info = _phc_company_info(cursor)
            logo_path = _local_or_remote_file_path(str(company.get('logo_path') or ''))
            prepared_lines = []
            sequence = 0
            for row in lines:
              for accounting_line in row.get('ACCOUNTING_LINES') or []:
                sequence += 1
                article = _phc_article(cursor, str(accounting_line.get('artigo_ref') or '').strip())
                gross = _safe_decimal(accounting_line.get('total_com_iva'))
                taxaiva = _safe_decimal(accounting_line.get('taxaiva'))
                net, vat = _vat_amounts_from_gross(gross, taxaiva)
                is_dkv = str(row.get('TIPO') or '').strip().upper() == 'DKV'
                # DKV is paid directly by the company. Keep the expense line
                # for traceability, but it must not create a reimbursable
                # Notes de Frais value in PHC.
                phc_net = Decimal('0.00') if is_dkv else net
                phc_vat = Decimal('0.00') if is_dkv else vat
                tabiva = _safe_int(accounting_line.get('tabiva'))
                ccusto = str(accounting_line.get('ccusto') or supplier.get('ccusto') or '').strip()
                prepared_lines.append({
                    'row': row,
                    'accounting_line': accounting_line,
                    'article': article,
                    'gross': gross,
                    'net': net,
                    'vat': vat,
                    'phc_net': phc_net,
                    'phc_vat': phc_vat,
                    'tabiva': tabiva,
                    'taxaiva': taxaiva,
                    'ccusto': ccusto,
                    'lordem': sequence * 10000,
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
            total_net = sum((line['phc_net'] for line in prepared_lines), Decimal('0.00')).quantize(Decimal('0.01'))
            total_vat = sum((line['phc_vat'] for line in prepared_lines), Decimal('0.00')).quantize(Decimal('0.01'))
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
            phc_currency = next(iter(currencies)) or (str(currency_row[0] or '').strip() if currency_row else 'EUR')
            tax_by_code: dict[int, dict[str, Decimal]] = {}
            for line in prepared_lines:
                bucket = tax_by_code.setdefault(line['tabiva'], {'taxa': line['taxaiva'], 'base': Decimal('0.00'), 'iva': Decimal('0.00')})
                bucket['base'] += line['phc_net']
                bucket['iva'] += line['phc_vat']

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
                'maquina': marker,
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

            # BI differs between PHC databases. In particular HSOLS_FR has a
            # shorter LOBS2 than other companies, so respect the actual schema.
            bi_lobs_length = _phc_character_maximum_length(cursor, 'BI', 'LOBS')
            bi_lobs2_length = _phc_character_maximum_length(cursor, 'BI', 'LOBS2')
            for line in prepared_lines:
                row = line['row']
                article = line['article']
                phc_net = line['phc_net'].quantize(Decimal('0.01'))
                local_net = _phc_value(phc_net)
                bi_values = {
                    'bistamp': line['bistamp'],
                    'bostamp': bostamp,
                    'nmdos': PHC_NOTES_FRAIS_NMDOS,
                    'ndos': PHC_NOTES_FRAIS_NDOS,
                    'obrano': obrano,
                    'boano': today_value.year,
                    'dataobra': row.get('DATA_DESPESA') or dataobra,
                    'ref': article['ref'],
                    'design': (str(line.get('accounting_line', {}).get('design') or '').strip() or article['design'])[:60],
                    'qtt': Decimal('1.0000'),
                    # QTT2 is the quantity satisfied by downstream documents.
                    # A new internal dossier line must always start unsatisfied.
                    'qtt2': Decimal('0.0000'),
                    'pu': local_net,
                    'debito': local_net,
                    'edebito': phc_net,
                    'ttdeb': local_net,
                    'ettdeb': phc_net,
                    'pcusto': local_net,
                    'epcusto': phc_net,
                    'prorc': local_net,
                    'iva': line['taxaiva'],
                    'tabiva': line['tabiva'],
                    'ivaincl': 0,
                    'unidade': article['unidade'],
                    'stipo': article['stipo'],
                    'no': supplier['no'],
                    'nome': supplier['nome'][:55],
                    'lobs': _phc_text(line.get('accounting_line', {}).get('matricula'), bi_lobs_length, 60),
                    'lobs2': _phc_text(
                        f"EXP:{row.get('DESPLINHASTAMP')} LIN:{line.get('accounting_line', {}).get('stamp')} {row.get('OBS') or ''}",
                        bi_lobs2_length,
                        60,
                    ),
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
            # Durable recovery point: PHC has committed, Portal stamps may still
            # need reconciliation after a lost response or Portal DB failure.
            db.session.execute(text("""
                UPDATE dbo.COLAB_DESPESA_LANCAMENTO SET ESTADO='PHC_CRIADO',
                    PHC_BOSTAMP=:bostamp, PHC_OBRANO=:obrano, PHC_NMDOS=:nmdos,
                    DTALT=GETDATE() WHERE LANCAMENTO_CHAVE=:batch_key
            """), {
                'batch_key': batch_key, 'bostamp': bostamp, 'obrano': obrano,
                'nmdos': PHC_NOTES_FRAIS_NMDOS,
            })
            db.session.commit()
        except Exception:
            conn.rollback()
            launch_state = str(db.session.execute(text("""
                SELECT ESTADO FROM dbo.COLAB_DESPESA_LANCAMENTO
                WHERE LANCAMENTO_CHAVE=:batch_key
            """), {'batch_key': batch_key}).scalar() or '').upper()
            if launch_state != 'PHC_CRIADO':
                generated_pdf = str(pdf_info.get('path') or '').strip()
                if generated_pdf and os.path.isfile(generated_pdf):
                    try:
                        os.remove(generated_pdf)
                    except OSError:
                        current_app.logger.warning('Não foi possível limpar o PDF de um lançamento revertido.', exc_info=True)
                db.session.execute(text("""
                    UPDATE dbo.COLAB_DESPESA_LANCAMENTO SET ESTADO='FALHOU', DTALT=GETDATE()
                    WHERE LANCAMENTO_CHAVE=:batch_key
                """), {'batch_key': batch_key})
                db.session.commit()
            raise

    line_params = {
        'bostamp': bostamp,
        'login': login,
    }
    expense_bistamps: dict[str, str] = {}
    for line in prepared_lines:
        expense_bistamps.setdefault(str(line['row'].get('DESPLINHASTAMP') or ''), line['bistamp'])
    for row in lines:
        stamp = str(row.get('DESPLINHASTAMP') or '').strip()
        db.session.execute(text("""
            UPDATE dbo.COLAB_DESPESA_LINHA
            SET PHC_STATUS = 'LANCADO',
                PHC_BOSTAMP = :bostamp,
                PHC_BISTAMP = :bistamp,
                PHC_OBRANO = :obrano,
                PHC_NMDOS = :nmdos,
                ARQUIVO_ESTADO = 'LANCADA',
                ARQUIVO_DATA = GETDATE(),
                ARQUIVO_POR = :login,
                PHC_DTENVIO = GETDATE(),
                PHC_ERRO = N'',
                DTALT = GETDATE(),
                USERALTERACAO = :login
            WHERE DESPLINHASTAMP = :stamp
        """), {
            **line_params,
            'bistamp': expense_bistamps.get(stamp, ''),
            'stamp': stamp,
            'obrano': obrano,
            'nmdos': PHC_NOTES_FRAIS_NMDOS,
        })
        _record_expense_history(stamp, 'LANCADA_PHC', {
            'phc_db': phc_db, 'bostamp': bostamp, 'obrano': obrano,
            'nmdos': PHC_NOTES_FRAIS_NMDOS,
        }, login)
    db.session.commit()
    db.session.execute(text("""
        UPDATE dbo.COLAB_DESPESA_LANCAMENTO SET ESTADO='LANCADO',
            PHC_BOSTAMP=:bostamp, PHC_OBRANO=:obrano, PHC_NMDOS=:nmdos, DTALT=GETDATE()
        WHERE LANCAMENTO_CHAVE=:batch_key
    """), {
        'batch_key': batch_key, 'bostamp': bostamp, 'obrano': obrano,
        'nmdos': PHC_NOTES_FRAIS_NMDOS,
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
        SET ANULADA = 0,
            ESTADO = 'ELIMINADA',
            ARQUIVO_ESTADO = 'ELIMINADA',
            ARQUIVO_DATA = GETDATE(),
            ARQUIVO_POR = :login,
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
    _record_expense_history(stamp, 'ELIMINADA', {}, login)
    db.session.commit()
    return {'ok': True, 'stamp': stamp, 'estado': 'ELIMINADA'}


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
            ESTADO = 'DEVOLVIDA',
            DEVOLUCAO_OBS = :observation,
            ARQUIVO_ESTADO = 'DEVOLVIDA',
            ARQUIVO_DATA = GETDATE(),
            ARQUIVO_POR = :login,
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
    _record_expense_history(stamp, 'DEVOLVIDA', {'observacao': observation}, login)
    db.session.commit()
    return {'ok': True, 'stamp': stamp, 'estado': 'DEVOLVIDA'}


def list_expense_processing_archive(filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    ensure_colaborador_despesas_schema()
    filters = filters or {}
    clauses = ["UPPER(LTRIM(RTRIM(ISNULL(L.ESTADO, '')))) IN ('DEVOLVIDA', 'ELIMINADA', 'LANCADA') OR LTRIM(RTRIM(ISNULL(L.PHC_BOSTAMP, ''))) <> ''"]
    params: dict[str, Any] = {}
    if str(filters.get('date_from') or '').strip():
        clauses.append("COALESCE(L.ARQUIVO_DATA, L.PHC_DTENVIO, L.DTALT, L.DTCRI) >= TRY_CONVERT(date, :date_from)")
        params['date_from'] = str(filters.get('date_from')).strip()
    if str(filters.get('date_to') or '').strip():
        clauses.append("COALESCE(L.ARQUIVO_DATA, L.PHC_DTENVIO, L.DTALT, L.DTCRI) < DATEADD(day, 1, TRY_CONVERT(date, :date_to))")
        params['date_to'] = str(filters.get('date_to')).strip()
    if str(filters.get('user') or '').strip():
        clauses.append("LTRIM(RTRIM(ISNULL(H.LOGIN, ''))) = :user_login")
        params['user_login'] = str(filters.get('user')).strip()
    rows = db.session.execute(text(f"""
        SELECT L.*, H.LOGIN, H.PENO, H.PENOME, H.PEFEID, H.PHC_DB, H.PHC_SERVER,
               ISNULL(NULLIF(L.FEID, 0), H.FEID) AS LINHA_FEID,
               COALESCE(NULLIF(L.EMPRESA, ''), H.EMPRESA, '') AS LINHA_EMPRESA
        FROM dbo.COLAB_DESPESA_LINHA L
        INNER JOIN dbo.COLAB_DESPESA_CAB H ON H.DESPCABSTAMP = L.DESPCABSTAMP
        WHERE ({clauses[0]}) {' '.join('AND ' + c for c in clauses[1:])}
        ORDER BY COALESCE(L.ARQUIVO_DATA, L.PHC_DTENVIO, L.DTALT, L.DTCRI) DESC, L.DTCRI DESC
    """), params).mappings().all()
    items = []
    for row in rows:
        item = serialize_line(row)
        item.update({
            'login': str(row.get('LOGIN') or '').strip(), 'peno': int(row.get('PENO') or 0),
            'penome': str(row.get('PENOME') or '').strip(), 'feid': int(row.get('LINHA_FEID') or 0),
            'empresa': str(row.get('LINHA_EMPRESA') or '').strip(),
        })
        item['moeda'] = _expense_company_currency(_expense_company_by_feid(int(item.get('feid') or 0)), item.get('moeda'))
        items.append(item)
    _attach_processing_details(items)
    return items


def delete_expense_processing_pdf(line_stamp: str, user) -> dict[str, Any]:
    ensure_colaborador_despesas_schema()
    stamp = str(line_stamp or '').strip()
    row = db.session.execute(text("""
        SELECT TOP 1 CAMINHO FROM dbo.COLAB_DESPESA_LINHA
        WHERE DESPLINHASTAMP = :stamp AND LTRIM(RTRIM(ISNULL(PHC_BOSTAMP, ''))) = ''
    """), {'stamp': stamp}).mappings().first()
    if not row:
        raise ValueError('A despesa não está disponível para remover o PDF.')
    login = str(getattr(user, 'LOGIN', '') or '').strip()
    db.session.execute(text("""
        UPDATE dbo.COLAB_DESPESA_LINHA SET FICHEIRO_ORIGINAL=N'', FICHEIRO=N'', CAMINHO=N'',
            MIME_TYPE='', EXT='', TAMANHO=0, FILE_HASH='', VERSION=VERSION+1,
            DTALT=GETDATE(), USERALTERACAO=:login WHERE DESPLINHASTAMP=:stamp
    """), {'stamp': stamp, 'login': login})
    _record_expense_history(stamp, 'PDF_ELIMINADO', {}, login)
    db.session.commit()
    local_path = _expense_local_file_path(str(row.get('CAMINHO') or ''))
    try:
        if local_path and os.path.isfile(local_path) and os.path.realpath(local_path).startswith(os.path.realpath(current_app.root_path)):
            os.remove(local_path)
    except OSError:
        current_app.logger.warning('Não foi possível remover o PDF da despesa %s.', stamp, exc_info=True)
    return {'ok': True, 'stamp': stamp}


def upload_expense_processing_pdf(line_stamp: str, file_storage, user) -> dict[str, Any]:
    ensure_colaborador_despesas_schema()
    stamp = str(line_stamp or '').strip()
    if not file_storage or not str(getattr(file_storage, 'filename', '') or '').lower().endswith('.pdf'):
        raise ValueError('Seleciona um ficheiro PDF.')
    size = int(getattr(file_storage, 'content_length', 0) or 0)
    stream = getattr(file_storage, 'stream', None)
    if stream and not size:
        stream.seek(0, os.SEEK_END); size = stream.tell(); stream.seek(0)
    if size > 50 * 1024 * 1024:
        raise ValueError('O PDF não pode ultrapassar 50 MB.')
    row = db.session.execute(text("""
        SELECT TOP 1 DESPCABSTAMP, CAMINHO FROM dbo.COLAB_DESPESA_LINHA
        WHERE DESPLINHASTAMP=:stamp AND ESTADO='FECHADO'
          AND LTRIM(RTRIM(ISNULL(PHC_BOSTAMP, '')))=''
    """), {'stamp': stamp}).mappings().first()
    if not row:
        raise ValueError('A despesa não está disponível para receber o PDF.')
    if str(row.get('CAMINHO') or '').strip():
        raise ValueError('Esta despesa já tem um PDF. Elimina-o antes de carregar outro.')
    stored = _store_line_file(file_storage, str(row.get('DESPCABSTAMP') or ''), stamp)
    login = str(getattr(user, 'LOGIN', '') or '').strip()
    db.session.execute(text("""
        UPDATE dbo.COLAB_DESPESA_LINHA SET FICHEIRO_ORIGINAL=:original, FICHEIRO=:name,
            CAMINHO=:path, MIME_TYPE=:mime, EXT=:ext, TAMANHO=:size, FILE_HASH=:hash,
            VERSION=VERSION+1, DTALT=GETDATE(), USERALTERACAO=:login
        WHERE DESPLINHASTAMP=:stamp
    """), {**stored, 'stamp': stamp, 'login': login})
    _record_expense_history(stamp, 'PDF_CARREGADO', {'ficheiro': stored['original'], 'tamanho': stored['size']}, login)
    db.session.commit()
    return {'ok': True, 'stamp': stamp, 'file_url': _expense_public_file_url(stored['path'])}


def reanalyze_expense_processing_pdf(line_stamp: str, user) -> dict[str, Any]:
    """Run the shared OCR cascade and fill only still-empty expense fields."""
    from services.document_ai_processing_orchestrator import extract_document_with_cascade

    ensure_colaborador_despesas_schema()
    stamp = str(line_stamp or '').strip()
    row = db.session.execute(text("""
        SELECT TOP 1 * FROM dbo.COLAB_DESPESA_LINHA
        WHERE DESPLINHASTAMP=:stamp AND ESTADO='FECHADO'
          AND LTRIM(RTRIM(ISNULL(PHC_BOSTAMP, '')))=''
    """), {'stamp': stamp}).mappings().first()
    if not row:
        raise ValueError('A despesa não está disponível para análise.')
    path = _expense_local_file_path(str(row.get('CAMINHO') or ''))
    if not path:
        raise ValueError('Esta despesa não tem PDF disponível.')
    extraction = extract_document_with_cascade(
        path, str(row.get('EXT') or '.pdf'), str(row.get('MIME_TYPE') or 'application/pdf'),
        document_stamp=stamp,
    )
    if not extraction.get('ok'):
        raise ValueError('A análise IA não conseguiu ler este documento. A despesa foi mantida sem alterações.')
    extracted_text = str(extraction.get('text') or '')
    reference = ''
    reference_match = re.search(
        r'(?im)\b(?:facture|fatura|invoice|receipt|re[çc]u|n[ºo°]|ref(?:erence|erência)?)\s*[:#-]?\s*([A-Z0-9][A-Z0-9./_-]{2,30})',
        extracted_text,
    )
    if reference_match:
        reference = str(reference_match.group(1) or '').strip()[:160]
    expense_date = ''
    date_match = re.search(r'\b(\d{1,2})[/.\-](\d{1,2})[/.\-](20\d{2})\b', extracted_text)
    if date_match:
        try:
            expense_date = date(int(date_match.group(3)), int(date_match.group(2)), int(date_match.group(1))).isoformat()
        except ValueError:
            expense_date = ''
    origins = _json_object(row.get('CAMPO_ORIGEM_JSON'))
    updates = {
        'reference': str(row.get('REFERENCIA_DOCUMENTO') or '').strip() or reference,
        'expense_date': row.get('DATA_DESPESA') or expense_date or None,
    }
    if not str(row.get('REFERENCIA_DOCUMENTO') or '').strip() and reference:
        origins['referencia_documento'] = 'IA'
    if not row.get('DATA_DESPESA') and expense_date:
        origins['data_despesa'] = 'IA'
    login = str(getattr(user, 'LOGIN', '') or '').strip()
    db.session.execute(text("""
        UPDATE dbo.COLAB_DESPESA_LINHA SET REFERENCIA_DOCUMENTO=:reference,
            DATA_DESPESA=TRY_CONVERT(date,:expense_date), CAMPO_ORIGEM_JSON=:origins,
            VERSION=VERSION+1, DTALT=GETDATE(), USERALTERACAO=:login
        WHERE DESPLINHASTAMP=:stamp
    """), {
        'stamp': stamp, 'reference': updates['reference'], 'expense_date': updates['expense_date'],
        'origins': json.dumps(origins, ensure_ascii=False), 'login': login,
    })
    if reference:
        db.session.execute(text("""
            UPDATE dbo.COLAB_DESPESA_CONTAB_LINHA SET REFERENCIA=:reference,
                CAMPO_ORIGEM_JSON=CASE WHEN LTRIM(RTRIM(ISNULL(CAMPO_ORIGEM_JSON,''))) IN ('','{}')
                    THEN N'{"referencia":"IA"}' ELSE CAMPO_ORIGEM_JSON END,
                DTALT=GETDATE(), USERALTERACAO=:login
            WHERE DESPLINHASTAMP=:stamp AND LTRIM(RTRIM(ISNULL(REFERENCIA,'')))=''
        """), {'stamp': stamp, 'reference': reference, 'login': login})
    _record_expense_history(stamp, 'ANALISE_IA', {
        'method': extraction.get('method'), 'engine': extraction.get('engine'),
        'reference_found': bool(reference), 'date_found': bool(expense_date),
    }, login)
    db.session.commit()
    refreshed = db.session.execute(text("SELECT TOP 1 * FROM dbo.COLAB_DESPESA_LINHA WHERE DESPLINHASTAMP=:stamp"), {'stamp': stamp}).mappings().first()
    item = serialize_line(refreshed or {})
    _attach_processing_details([item])
    return {'ok': True, 'line': item, 'message': 'Documento analisado. Os valores manuais foram preservados.'}


def permanently_delete_archived_expense(line_stamp: str, user) -> dict[str, Any]:
    ensure_colaborador_despesas_schema()
    stamp = str(line_stamp or '').strip()
    row = db.session.execute(text("""
        SELECT TOP 1 CAMINHO, ESTADO, PHC_BOSTAMP
        FROM dbo.COLAB_DESPESA_LINHA WITH (UPDLOCK, ROWLOCK)
        WHERE DESPLINHASTAMP = :stamp
    """), {'stamp': stamp}).mappings().first()
    if not row:
        raise ValueError('Despesa não encontrada.')
    if str(row.get('PHC_BOSTAMP') or '').strip():
        raise ValueError('Uma despesa lançada no PHC não pode ser eliminada do arquivo.')
    if str(row.get('ESTADO') or '').strip().upper() not in {'DEVOLVIDA', 'ELIMINADA'}:
        raise ValueError('A despesa não está disponível para eliminação definitiva.')
    db.session.execute(text("DELETE FROM dbo.COLAB_DESPESA_CONTAB_LINHA WHERE DESPLINHASTAMP=:stamp"), {'stamp': stamp})
    db.session.execute(text("DELETE FROM dbo.COLAB_DESPESA_HIST WHERE DESPLINHASTAMP=:stamp"), {'stamp': stamp})
    db.session.execute(text("DELETE FROM dbo.COLAB_DESPESA_LINHA WHERE DESPLINHASTAMP=:stamp"), {'stamp': stamp})
    db.session.commit()
    path = _expense_local_file_path(str(row.get('CAMINHO') or ''))
    try:
        if path and os.path.isfile(path) and os.path.realpath(path).startswith(os.path.realpath(current_app.root_path)):
            os.remove(path)
    except OSError:
        current_app.logger.warning('Não foi possível remover o anexo arquivado %s.', stamp, exc_info=True)
    return {'ok': True, 'stamp': stamp}


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
