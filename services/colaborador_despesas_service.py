import hashlib
import os
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from flask import current_app
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


def _file_hash(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


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
                OBS nvarchar(500) NOT NULL
                    CONSTRAINT DF_COLAB_DESPESA_LINHA_OBS DEFAULT N'',
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

    db.session.commit()
    _schema_ready_databases.add(database_name)


def get_colaborador_context(user) -> dict[str, Any]:
    userstamp = str(getattr(user, 'USSTAMP', '') or '').strip()
    login = str(getattr(user, 'LOGIN', '') or '').strip()
    row = db.session.execute(text("""
        SELECT TOP 1
            ISNULL(U.PENO, 0) AS PENO,
            LTRIM(RTRIM(ISNULL(U.PENOME, ''))) AS PENOME,
            ISNULL(U.PEFEID, 0) AS PEFEID,
            LTRIM(RTRIM(ISNULL(U.PEEMPRESA, ''))) AS PEEMPRESA,
            ISNULL(FE.FEID, 0) AS FEID,
            LTRIM(RTRIM(ISNULL(FE.NOME, ''))) AS FE_NOME,
            LTRIM(RTRIM(ISNULL(FE.PHC_DB, ''))) AS PHC_DB,
            LTRIM(RTRIM(ISNULL(FE.PHC_SERVER, ''))) AS PHC_SERVER
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
    colaborador['completo'] = bool(
        colaborador['peno']
        and colaborador['penome']
        and colaborador['pefeid']
        and colaborador['phc_db']
    )
    return colaborador


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
          AND ESTADO = 'RASCUNHO'
        ORDER BY ORDEM, DTCRI
    """), {'header_stamp': str(header_stamp or '').strip()}).mappings().all()
    return [serialize_line(row) for row in rows]


def serialize_line(row: dict[str, Any]) -> dict[str, Any]:
    data_value = row.get('DATA_DESPESA')
    if isinstance(data_value, date):
        data_value = data_value.isoformat()
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
        'estado': str(row.get('ESTADO') or '').strip(),
        'file_original': str(row.get('FICHEIRO_ORIGINAL') or '').strip(),
        'file_name': str(row.get('FICHEIRO') or '').strip(),
        'file_path': str(row.get('CAMINHO') or '').strip(),
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
            (DESPLINHASTAMP, DESPCABSTAMP, ORDEM, USERCRIACAO, USERALTERACAO)
            VALUES (:stamp, :header_stamp, :ordem, :login, :login)
        """), {
            'stamp': line_stamp,
            'header_stamp': header_stamp,
            'ordem': ordem,
            'login': login,
        })
    else:
        existing = db.session.execute(text(f"""
            SELECT TOP 1 L.DESPLINHASTAMP
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

    file_payload = None
    if file_storage:
        file_payload = _store_line_file(file_storage, header_stamp, line_stamp)

    data_despesa = str(payload.get('data_despesa') or '').strip() or None
    tipo = str(payload.get('tipo') or '').strip().upper()[:30]
    valor = _safe_decimal(payload.get('valor'))
    kms = _safe_decimal(payload.get('kms'))
    viatura = str(payload.get('viatura') or '').strip()[:50]
    obs = str(payload.get('obs') or '').strip()[:500]

    params = {
        'stamp': line_stamp,
        'data_despesa': data_despesa,
        'tipo': tipo,
        'valor': valor,
        'kms': kms,
        'viatura': viatura,
        'obs': obs,
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


def close_expense_line(user, line_stamp: str) -> dict[str, Any]:
    ensure_colaborador_despesas_schema()
    colaborador = get_colaborador_context(user)
    stamp = str(line_stamp or '').strip()
    result = db.session.execute(text(f"""
        UPDATE L
        SET ESTADO = 'FECHADO',
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
