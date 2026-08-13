from __future__ import annotations

import re
import uuid
from datetime import date, datetime
from functools import lru_cache
from typing import Any

from flask_login import current_user
from sqlalchemy import text

from models import db
from services.multiempresa_service import MissingCurrentEntityError, get_current_feid


TABLE_NAME = 'dbo.MENSAGEM_PREDEFINIDA'
DATE_TOKEN_RE = re.compile(r'(?<![A-Za-z0-9])(\d{4})(?![A-Za-z0-9])')
TAG_RE = re.compile(r'{{\s*([a-zA-Z0-9_]+)\s*}}')


class PredefinedMessagesError(Exception):
    pass


def _stamp() -> str:
    return uuid.uuid4().hex.upper()[:25]


def _text(value: Any, limit: int | None = None) -> str:
    text_value = str(value or '').strip()
    return text_value[:limit] if limit else text_value


def _current_feid() -> int:
    try:
        return int(get_current_feid() or 0)
    except MissingCurrentEntityError as exc:
        raise PredefinedMessagesError('Empresa ativa nao definida na sessao.') from exc


def _is_admin() -> bool:
    return bool(getattr(current_user, 'ADMIN', False) or getattr(current_user, 'DEV', False))


def _login() -> str:
    return _text(getattr(current_user, 'LOGIN', '') or getattr(current_user, 'USSTAMP', '') or 'APP', 60)


@lru_cache(maxsize=64)
def column_exists(table_name: str, column_name: str) -> bool:
    row = db.session.execute(text("""
        SELECT 1
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo'
          AND TABLE_NAME = :table_name
          AND COLUMN_NAME = :column_name
    """), {
        'table_name': table_name.upper(),
        'column_name': column_name.upper(),
    }).first()
    return row is not None


def ensure_predefined_messages_schema() -> None:
    db.session.execute(text(f"""
        IF OBJECT_ID('{TABLE_NAME}', 'U') IS NULL
        BEGIN
            CREATE TABLE {TABLE_NAME} (
                MENSAGEMSTAMP varchar(25) NOT NULL
                    CONSTRAINT PK_MENSAGEM_PREDEFINIDA PRIMARY KEY,
                FEID int NOT NULL
                    CONSTRAINT DF_MENSAGEM_PREDEFINIDA_FEID DEFAULT 0,
                TITULO varchar(120) NOT NULL
                    CONSTRAINT DF_MENSAGEM_PREDEFINIDA_TITULO DEFAULT '',
                CATEGORIA varchar(60) NOT NULL
                    CONSTRAINT DF_MENSAGEM_PREDEFINIDA_CATEGORIA DEFAULT '',
                MENSAGEM nvarchar(max) NOT NULL
                    CONSTRAINT DF_MENSAGEM_PREDEFINIDA_MENSAGEM DEFAULT N'',
                TAGS varchar(500) NOT NULL
                    CONSTRAINT DF_MENSAGEM_PREDEFINIDA_TAGS DEFAULT '',
                ATIVA bit NOT NULL
                    CONSTRAINT DF_MENSAGEM_PREDEFINIDA_ATIVA DEFAULT 1,
                ORDEM int NOT NULL
                    CONSTRAINT DF_MENSAGEM_PREDEFINIDA_ORDEM DEFAULT 0,
                DTCRI datetime NOT NULL
                    CONSTRAINT DF_MENSAGEM_PREDEFINIDA_DTCRI DEFAULT GETDATE(),
                DTALT datetime NULL,
                USERCRIACAO varchar(60) NOT NULL
                    CONSTRAINT DF_MENSAGEM_PREDEFINIDA_USERCRI DEFAULT '',
                USERALTERACAO varchar(60) NOT NULL
                    CONSTRAINT DF_MENSAGEM_PREDEFINIDA_USERALT DEFAULT ''
            );
            CREATE INDEX IX_MENSAGEM_PREDEFINIDA_FEID_ATIVA
                ON {TABLE_NAME} (FEID, ATIVA, ORDEM, TITULO);
        END
    """))
    db.session.commit()


def ensure_predefined_messages_menu() -> None:
    """Expose the tool in Operacao, following the same access model as reservations."""
    row = db.session.execute(text("""
        SELECT TOP 1 MENUSTAMP
        FROM dbo.MENU
        WHERE LTRIM(RTRIM(ISNULL(URL, ''))) = '/mensagens-predefinidas'
    """)).scalar()
    menu_stamp = _text(row, 25)
    if not menu_stamp:
        menu_stamp = _stamp()
        db.session.execute(text("""
            INSERT INTO dbo.MENU (
                MENUSTAMP, ORDEM, NOME, TABELA, URL, ADMIN, ICONE, FORM, ORDERBY, NOVO, INATIVO
            ) VALUES (
                :stamp, 205, 'Mensagens', 'RS', '/mensagens-predefinidas', 0, 'fa-solid fa-message', '', '', 0, 0
            )
        """), {'stamp': menu_stamp})

    # Empresas com módulos ativos filtram a sidebar por MOD_OBJETOS. A mensagem
    # pertence ao mesmo módulo PMS das Reservas e herda o mesmo acesso (RS).
    pms_module = db.session.execute(text("""
        SELECT TOP 1 MODSTAMP
        FROM dbo.MOD_OBJETOS
        WHERE MENUSTAMP = 'F40B1E2D-3589-47AD-A884-F'
          AND ISNULL(ATIVO, 0) = 1
    """)).scalar()
    if pms_module:
        object_exists = db.session.execute(text("""
            SELECT TOP 1 1
            FROM dbo.MOD_OBJETOS
            WHERE MENUSTAMP = :menu_stamp
        """), {'menu_stamp': menu_stamp}).scalar()
        if not object_exists:
            db.session.execute(text("""
                INSERT INTO dbo.MOD_OBJETOS (
                    MODOBJSTAMP, MODSTAMP, TIPO, OBJKEY, OBJNOME, OBJROTA, MENUSTAMP,
                    ORDEM, ATIVO, DTCRI, USERCRIACAO, USERALTERACAO
                ) VALUES (
                    :object_stamp, :module_stamp, 'MENU', 'MENSAGENS_PREDEFINIDAS',
                    'Mensagens', '/mensagens-predefinidas', :menu_stamp,
                    205, 1, GETDATE(), 'APP', 'APP'
                )
            """), {
                'object_stamp': _stamp(),
                'module_stamp': _text(pms_module, 25),
                'menu_stamp': menu_stamp,
            })
    db.session.commit()


def _message_scope() -> tuple[int, int]:
    return _current_feid(), 1 if _is_admin() else 0


def _message_row(row: Any) -> dict[str, Any]:
    data = dict(row)
    return {
        'id': _text(data.get('MENSAGEMSTAMP')),
        'feid': int(data.get('FEID') or 0),
        'titulo': _text(data.get('TITULO')),
        'categoria': _text(data.get('CATEGORIA')),
        'mensagem': str(data.get('MENSAGEM') or ''),
        'tags': _text(data.get('TAGS')),
        'ativa': bool(data.get('ATIVA') or 0),
        'ordem': int(data.get('ORDEM') or 0),
        'dtalt': data.get('DTALT').isoformat(timespec='minutes') if data.get('DTALT') else '',
    }


def list_messages() -> list[dict[str, Any]]:
    current_feid, is_admin = _message_scope()
    rows = db.session.execute(text(f"""
        SELECT
            MENSAGEMSTAMP, FEID, TITULO, CATEGORIA, MENSAGEM, TAGS, ATIVA, ORDEM,
            ISNULL(DTALT, DTCRI) AS DTALT
        FROM {TABLE_NAME}
        WHERE ATIVA = 1
          AND (FEID IN (0, :current_feid) OR :is_admin = 1)
        ORDER BY ORDEM, TITULO, MENSAGEMSTAMP
    """), {'current_feid': current_feid, 'is_admin': is_admin}).mappings().all()
    return [_message_row(row) for row in rows]


def get_message(message_id: str, *, include_inactive: bool = True) -> dict[str, Any] | None:
    current_feid, is_admin = _message_scope()
    status_filter = '' if include_inactive else 'AND ATIVA = 1'
    row = db.session.execute(text(f"""
        SELECT
            MENSAGEMSTAMP, FEID, TITULO, CATEGORIA, MENSAGEM, TAGS, ATIVA, ORDEM,
            ISNULL(DTALT, DTCRI) AS DTALT
        FROM {TABLE_NAME}
        WHERE MENSAGEMSTAMP = :message_id
          {status_filter}
          AND (FEID IN (0, :current_feid) OR :is_admin = 1)
    """), {
        'message_id': _text(message_id, 25),
        'current_feid': current_feid,
        'is_admin': is_admin,
    }).mappings().first()
    return _message_row(row) if row else None


def save_message(message_id: str | None, payload: dict[str, Any]) -> dict[str, Any]:
    current_feid, is_admin = _message_scope()
    title = _text(payload.get('titulo'), 120)
    body = str(payload.get('mensagem') or '').strip()
    if not title:
        raise PredefinedMessagesError('Indica o titulo da mensagem.')
    if not body:
        raise PredefinedMessagesError('Indica o texto da mensagem.')

    try:
        order = int(payload.get('ordem') or 0)
    except (TypeError, ValueError):
        order = 0

    data = {
        'titulo': title,
        'categoria': _text(payload.get('categoria'), 60),
        'mensagem': body,
        'tags': _text(payload.get('tags'), 500),
        'ativa': 1 if payload.get('ativa', True) not in (False, 0, '0', 'false', 'False') else 0,
        'ordem': order,
        'user': _login(),
    }
    message_id = _text(message_id, 25)
    if message_id:
        existing = get_message(message_id)
        if not existing:
            raise PredefinedMessagesError('Mensagem nao encontrada ou sem permissao.')
        db.session.execute(text(f"""
            UPDATE {TABLE_NAME}
            SET TITULO = :titulo,
                CATEGORIA = :categoria,
                MENSAGEM = :mensagem,
                TAGS = :tags,
                ATIVA = :ativa,
                ORDEM = :ordem,
                DTALT = GETDATE(),
                USERALTERACAO = :user
            WHERE MENSAGEMSTAMP = :message_id
              AND (FEID IN (0, :current_feid) OR :is_admin = 1)
        """), {**data, 'message_id': message_id, 'current_feid': current_feid, 'is_admin': is_admin})
    else:
        message_id = _stamp()
        db.session.execute(text(f"""
            INSERT INTO {TABLE_NAME} (
                MENSAGEMSTAMP, FEID, TITULO, CATEGORIA, MENSAGEM, TAGS, ATIVA, ORDEM,
                DTCRI, USERCRIACAO, USERALTERACAO
            ) VALUES (
                :message_id, :feid, :titulo, :categoria, :mensagem, :tags, :ativa, :ordem,
                GETDATE(), :user, :user
            )
        """), {**data, 'message_id': message_id, 'feid': current_feid})
    db.session.commit()
    saved = get_message(message_id)
    if not saved:
        raise PredefinedMessagesError('Nao foi possivel obter a mensagem gravada.')
    return saved


def delete_message(message_id: str) -> None:
    current_feid, is_admin = _message_scope()
    result = db.session.execute(text(f"""
        DELETE FROM {TABLE_NAME}
        WHERE MENSAGEMSTAMP = :message_id
          AND (FEID IN (0, :current_feid) OR :is_admin = 1)
    """), {
        'message_id': _text(message_id, 25),
        'current_feid': current_feid,
        'is_admin': is_admin,
    })
    if not result.rowcount:
        raise PredefinedMessagesError('Mensagem nao encontrada ou sem permissao.')
    db.session.commit()


def _clean_date(value: Any) -> str:
    if isinstance(value, datetime):
        value = value.date()
    return value.isoformat() if isinstance(value, date) else ''


def _date_token(query: str) -> tuple[date | None, str]:
    match = DATE_TOKEN_RE.search(query)
    if not match:
        return None, query
    raw = match.group(1)
    try:
        parsed = date(date.today().year, int(raw[2:]), int(raw[:2]))
    except ValueError:
        return None, query
    return parsed, (query[:match.start()] + query[match.end():]).strip()


def _al_column_expr(column: str, alias: str, output: str) -> str:
    if column_exists('AL', column):
        return f"LTRIM(RTRIM(ISNULL({alias}.[{column}], ''))) AS {output}"
    return f"'' AS {output}"


def search_reservations(query: str, limit: int = 30) -> list[dict[str, Any]]:
    current_feid = _current_feid()
    query = _text(query, 160)
    if len(query) < 2:
        return []

    date_filter, text_filter = _date_token(query)
    params: dict[str, Any] = {'current_feid': current_feid, 'limit': max(1, min(int(limit or 30), 50))}
    where = [
        'ISNULL(RS.CANCELADA, 0) = 0',
        "LTRIM(RTRIM(ISNULL(RS.ALOJAMENTO, ''))) <> ''",
        'CAST(RS.DATAOUT AS date) >= CAST(GETDATE() AS date)',
    ]
    if date_filter:
        where.append('(CAST(RS.DATAIN AS date) = :target_date OR CAST(RS.DATAOUT AS date) = :target_date)')
        params['target_date'] = date_filter
    if text_filter:
        where.append("""
            (
                LTRIM(RTRIM(ISNULL(RS.ALOJAMENTO, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI LIKE :text_filter
                OR LTRIM(RTRIM(ISNULL(RS.NOME, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI LIKE :text_filter
                OR LTRIM(RTRIM(ISNULL(RS.RESERVA, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI LIKE :text_filter
            )
        """)
        params['text_filter'] = f"%{text_filter}%"

    feid_filter = """
        AND (
            ISNULL(AL.FEID, 0) = :current_feid
            OR ISNULL(AL.FEID_GESTOR, 0) = :current_feid
            OR ISNULL(RS.FEID, 0) = :current_feid
        )
    """ if not _is_admin() else ''
    rows = db.session.execute(text(f"""
        SELECT TOP (:limit)
            LTRIM(RTRIM(ISNULL(RS.RSSTAMP, ''))) AS RSSTAMP,
            LTRIM(RTRIM(ISNULL(RS.RESERVA, ''))) AS RESERVA,
            LTRIM(RTRIM(ISNULL(RS.ALOJAMENTO, ''))) AS ALOJAMENTO,
            LTRIM(RTRIM(ISNULL(RS.NOME, ''))) AS HOSPEDE,
            CAST(RS.DATAIN AS date) AS DATAIN,
            CAST(RS.DATAOUT AS date) AS DATAOUT,
            ISNULL(RS.NOITES, 0) AS NOITES,
            ISNULL(RS.ADULTOS, 0) AS ADULTOS,
            ISNULL(RS.CRIANCAS, 0) AS CRIANCAS,
            {_al_column_expr('TIPOLOGIA', 'AL', 'TIPOLOGIA')},
            {_al_column_expr('MORADA', 'AL', 'MORADA')},
            {_al_column_expr('LOCAL', 'AL', 'LOCAL')},
            {_al_column_expr('CODPOST', 'AL', 'CODPOST')},
            {_al_column_expr('LICENCA', 'AL', 'LICENCA')}
        FROM dbo.RS AS RS
        LEFT JOIN dbo.AL AS AL
          ON LTRIM(RTRIM(ISNULL(AL.NOME, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI
           = LTRIM(RTRIM(ISNULL(RS.ALOJAMENTO, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI
        WHERE {' AND '.join(where)}
          {feid_filter}
        ORDER BY
            CASE WHEN :target_date IS NOT NULL AND CAST(RS.DATAIN AS date) = :target_date THEN 0
                 WHEN :target_date IS NOT NULL AND CAST(RS.DATAOUT AS date) = :target_date THEN 1
                 ELSE 2 END,
            CAST(RS.DATAIN AS date), CAST(RS.DATAOUT AS date), RS.RESERVA
    """), {**params, 'target_date': date_filter}).mappings().all()

    return [{
        'id': _text(row.get('RSSTAMP')),
        'reserva': _text(row.get('RESERVA')),
        'alojamento': _text(row.get('ALOJAMENTO')),
        'hospede': _text(row.get('HOSPEDE')),
        'checkin': _clean_date(row.get('DATAIN')),
        'checkout': _clean_date(row.get('DATAOUT')),
        'noites': int(row.get('NOITES') or 0),
        'adultos': int(row.get('ADULTOS') or 0),
        'criancas': int(row.get('CRIANCAS') or 0),
        'tipologia': _text(row.get('TIPOLOGIA')),
        'morada': _text(row.get('MORADA')),
        'local': _text(row.get('LOCAL')),
        'codpost': _text(row.get('CODPOST')),
        'licenca': _text(row.get('LICENCA')),
    } for row in rows]


def render_message(message: str, reservation: dict[str, Any] | None = None) -> str:
    reservation = reservation or {}
    values = {
        'reserva': reservation.get('reserva', ''),
        'hospede': reservation.get('hospede', ''),
        'alojamento': reservation.get('alojamento', ''),
        'checkin': reservation.get('checkin', ''),
        'checkout': reservation.get('checkout', ''),
        'noites': reservation.get('noites', ''),
        'adultos': reservation.get('adultos', ''),
        'criancas': reservation.get('criancas', ''),
        'tipologia': reservation.get('tipologia', ''),
        'morada': reservation.get('morada', ''),
        'local': reservation.get('local', ''),
        'codpost': reservation.get('codpost', ''),
        'licenca': reservation.get('licenca', ''),
    }
    return TAG_RE.sub(lambda match: str(values.get(match.group(1).lower(), match.group(0))), str(message or ''))
