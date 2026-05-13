# blueprints/generic_crud.py

from flask import Blueprint, render_template, request, jsonify, abort, current_app, g
from flask_login import login_required, current_user
from sqlalchemy import MetaData, Table, select, text, String, or_, and_, exists, bindparam
from app import db
from models import Campo, Menu, Acessos, CamposModal, Linhas
from services.db_i18n_service import translate_db_record
from services.multiempresa_service import get_current_feid, MissingCurrentEntityError
import uuid
from datetime import date, timedelta, datetime
import json
import re
import os
from decimal import Decimal
import xml.etree.ElementTree as ET
from urllib import request as urllib_request, error as urllib_error
from werkzeug.utils import secure_filename

bp = Blueprint('generic', __name__, url_prefix='/generic')

MONITOR_DEFAULT_FEID = 2

ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
VIES_CHECKVAT_URL = 'https://ec.europa.eu/taxation_customs/vies/services/checkVatService'
VIES_SOAP_NS = 'http://schemas.xmlsoap.org/soap/envelope/'
VIES_TYPES_NS = 'urn:ec.europa.eu:taxud:vies:services:checkVat:types'
EVENT_CURSOR_SQL_PARAM_RE = re.compile(r'\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}')
EVENT_CURSOR_SQL_FORBIDDEN_RE = re.compile(
    r'\b(insert|update|delete|drop|alter|create|exec|execute|merge|truncate|grant|revoke|backup|restore|use|into)\b',
    re.IGNORECASE,
)

# --------------------------------------------------
# FO: pagamento (V_FC) helper
# --------------------------------------------------
def fo_pagamento_status(fostamp: str):
    """
    Determina se um documento FO (FOSTAMP) estÃ¡ incluÃ­do em pagamento
    atravÃ©s da view dbo.V_FC (FOSTAMP).

    Regras:
      - se SUM(EDEBF) ou SUM(ECREDF) != 0 => tem regularizaÃ§Ã£o => parcial/total
      - se ABERTO = SUM((ECRED-ECREDF) - (EDEB-EDEBF)) == 0 => totalmente pago
    """
    fs = (fostamp or '').strip()
    if not fs:
        return {
            'status': 'none',
            'locked': False,
            'aberto': 0.0,
            'regularizado': 0.0,
            'edebf': 0.0,
            'ecredf': 0.0,
        }

    sql = text("""
        SELECT
          SUM(ISNULL(EDEBF,0)) AS EDEBF,
          SUM(ISNULL(ECREDF,0)) AS ECREDF,
          SUM(
            (ISNULL(ECRED,0) - ISNULL(ECREDF,0)) - (ISNULL(EDEB,0) - ISNULL(EDEBF,0))
          ) AS ABERTO
        FROM dbo.V_FC
        WHERE LTRIM(RTRIM(ISNULL(FOSTAMP,''))) = :fs
    """)
    row = db.session.execute(sql, {'fs': fs}).mappings().first() or {}
    edebf = float(row.get('EDEBF') or 0)
    ecredf = float(row.get('ECREDF') or 0)
    aberto = float(row.get('ABERTO') or 0)

    regularizado = abs(edebf) + abs(ecredf)
    tol = 0.005
    if regularizado <= tol:
        status = 'none'
        locked = False
    else:
        if abs(aberto) <= tol:
            status = 'full'
            locked = True
        else:
            status = 'partial'
            locked = True

    return {
        'status': status,
        'locked': locked,
        'aberto': aberto,
        'regularizado': regularizado,
        'edebf': edebf,
        'ecredf': ecredf,
    }

# --------------------------------------------------
# ACL helper
# --------------------------------------------------
def has_permission(table_name: str, action: str) -> bool:
    # superâ€admin vÃª tudo
    if getattr(current_user, 'ADMIN', False):
        return True
    acesso = (
        Acessos.query
               .filter_by(utilizador=current_user.LOGIN, tabela=table_name)
               .first()
    )
    if not acesso:
        return False
    return getattr(acesso, action, False)


def has_cleaning_planner_access() -> bool:
    """Custom planner access is granted by MENU/ACESSOS on planner2."""
    try:
        if getattr(current_user, 'ADMIN', False):
            return True
        if bool(getattr(current_user, 'LPADMIN', False)):
            return True
        if has_permission('planner2', 'consultar'):
            return True
        if has_permission('LP', 'consultar'):
            return True
    except Exception:
        return False
    return False


def _current_language():
    return getattr(g, 'language', None)


def _translated_menu_label(menu_item, fallback: str) -> str:
    return translate_db_record(
        'MENU',
        getattr(menu_item, 'menustamp', ''),
        fallback_text=fallback,
        language=_current_language(),
    )


def _translated_campo_label(campo, fallback: str = '') -> str:
    fallback_text = fallback or getattr(campo, 'descricao', '') or getattr(campo, 'nmcampo', '')
    return translate_db_record(
        'CAMPOS',
        getattr(campo, 'camposstamp', ''),
        fallback_text=fallback_text,
        language=_current_language(),
    )


def _menu_uses_exact_widths(table_name: str) -> bool:
    table_key = (table_name or '').strip().upper()
    if not table_key:
        return False
    if not _column_exists('MENU', 'LARGURAS_EXATAS'):
        return False
    row = db.session.execute(text("""
        SELECT TOP 1 ISNULL(LARGURAS_EXATAS, 0) AS LARGURAS_EXATAS
          FROM dbo.MENU
         WHERE UPPER(LTRIM(RTRIM(ISNULL(TABELA, '')))) = :table_name
         ORDER BY ISNULL(ORDEM, 0), LTRIM(RTRIM(ISNULL(MENUSTAMP, '')))
    """), {'table_name': table_key}).mappings().first()
    return bool(row and int(row.get('LARGURAS_EXATAS') or 0) == 1)


def _menu_uses_list_exact_widths(menu_stamp: str = '', table_name: str = '') -> bool:
    if not _column_exists('MENU', 'LARGURAS_EXATAS_LISTA'):
        return False
    stamp = (menu_stamp or '').strip()
    table_key = (table_name or '').strip().upper()
    if stamp:
        row = db.session.execute(text("""
            SELECT TOP 1 ISNULL(LARGURAS_EXATAS_LISTA, 0) AS LARGURAS_EXATAS_LISTA
              FROM dbo.MENU
             WHERE LTRIM(RTRIM(ISNULL(MENUSTAMP, ''))) = :menustamp
        """), {'menustamp': stamp}).mappings().first()
        return bool(row and int(row.get('LARGURAS_EXATAS_LISTA') or 0) == 1)
    if not table_key:
        return False
    row = db.session.execute(text("""
        SELECT TOP 1 ISNULL(LARGURAS_EXATAS_LISTA, 0) AS LARGURAS_EXATAS_LISTA
          FROM dbo.MENU
         WHERE UPPER(LTRIM(RTRIM(ISNULL(TABELA, '')))) = :table_name
         ORDER BY ISNULL(ORDEM, 0), LTRIM(RTRIM(ISNULL(MENUSTAMP, '')))
    """), {'table_name': table_key}).mappings().first()
    return bool(row and int(row.get('LARGURAS_EXATAS_LISTA') or 0) == 1)


def _resolve_menu_stamp(table_name: str, requested_menustamp: str = '') -> str:
    requested = (requested_menustamp or '').strip()
    table_key = (table_name or '').strip().upper()
    if requested:
        row = db.session.execute(text("""
            SELECT TOP 1 LTRIM(RTRIM(ISNULL(MENUSTAMP, ''))) AS MENUSTAMP
            FROM dbo.MENU
            WHERE LTRIM(RTRIM(ISNULL(MENUSTAMP, ''))) = :menustamp
              AND UPPER(LTRIM(RTRIM(ISNULL(TABELA, '')))) = :table_name
        """), {'menustamp': requested, 'table_name': table_key}).mappings().first()
        if row:
            return str(row.get('MENUSTAMP') or '').strip()
    if not table_key:
        return ''
    row = db.session.execute(text("""
        SELECT TOP 1 LTRIM(RTRIM(ISNULL(MENUSTAMP, ''))) AS MENUSTAMP
        FROM dbo.MENU
        WHERE UPPER(LTRIM(RTRIM(ISNULL(TABELA, '')))) = :table_name
        ORDER BY ISNULL(ORDEM, 0), LTRIM(RTRIM(ISNULL(MENUSTAMP, '')))
    """), {'table_name': table_key}).mappings().first()
    return str(row.get('MENUSTAMP') or '').strip() if row else ''


def _prepare_event_cursor_sql(raw_sql: str):
    sql = (raw_sql or '').strip()
    if not sql:
        raise ValueError('SQL em falta.')
    if ';' in sql:
        raise ValueError('A query do cursor so pode conter uma instrucao.')
    if not re.match(r'^\s*(select|with)\b', sql, re.IGNORECASE):
        raise ValueError('A query do cursor tem de comecar por SELECT ou WITH.')
    if EVENT_CURSOR_SQL_FORBIDDEN_RE.search(sql):
        raise ValueError('A query do cursor so permite leitura.')

    param_names = []

    def replace_param(match):
        name = str(match.group(1) or '').strip()
        if name and name not in param_names:
            param_names.append(name)
        return f':{name}'

    compiled_sql = EVENT_CURSOR_SQL_PARAM_RE.sub(replace_param, sql)
    return compiled_sql, param_names


def _normalize_event_cursor_param_value(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return str(value)


def _event_cursor_json_value(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, list):
        return [_event_cursor_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _event_cursor_json_value(item) for key, item in value.items()}
    return str(value)


LOOKUP_FILTER_FORBIDDEN_RE = re.compile(
    r'\b(insert|update|delete|drop|alter|create|exec|execute|merge|truncate|grant|revoke|backup|restore|use|into|select|with|from|join|union)\b',
    re.IGNORECASE,
)


def _quote_sql_identifier(value: str) -> str:
    raw = str(value or '').strip()
    if not raw:
        raise ValueError('Identificador SQL em falta.')
    return '[' + raw.replace(']', ']]') + ']'


def _parse_lookup_props(raw_props) -> dict:
    if isinstance(raw_props, dict):
        return dict(raw_props)
    try:
        parsed = json.loads(str(raw_props or '').strip() or '{}')
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _lookup_prop(props: dict, *names: str) -> str:
    if not isinstance(props, dict):
        return ''
    for name in names:
        if name in props:
            return str(props.get(name) or '').strip()
    return ''


def _split_lookup_fields(value: str) -> list[str]:
    return [
        part.strip().strip('[]').strip()
        for part in re.split(r'[,;\n]+', str(value or ''))
        if part.strip().strip('[]').strip()
    ]


def _resolve_lookup_column(column_map: dict[str, str], requested: str, label: str) -> str:
    raw = str(requested or '').strip().strip('[]').strip()
    key = raw.upper()
    if not key or key not in column_map:
        raise ValueError(f'{label} invalido ou inexistente: {raw or "-"}')
    return column_map[key]


def _lookup_state_value(state: dict, name: str):
    if not isinstance(state, dict):
        return None
    raw_name = str(name or '').strip()
    if not raw_name:
        return None
    for key in (raw_name, raw_name.upper(), raw_name.lower()):
        if key in state:
            return state.get(key)
    upper_name = raw_name.upper()
    for key, value in state.items():
        if str(key or '').strip().upper() == upper_name:
            return value
    return None


def _prepare_lookup_filter(raw_filter: str, form_state: dict):
    filter_sql = str(raw_filter or '').strip()
    if not filter_sql:
        return '', {}
    if ';' in filter_sql or '--' in filter_sql or '/*' in filter_sql or '*/' in filter_sql:
        raise ValueError('A expressao de filtro contem tokens nao permitidos.')
    if LOOKUP_FILTER_FORBIDDEN_RE.search(filter_sql):
        raise ValueError('A expressao de filtro so pode conter condicoes de leitura.')

    params = {}

    def replace_param(match):
        name = str(match.group(1) or '').strip()
        param_name = f'lookup_filter_{len(params)}'
        params[param_name] = _normalize_event_cursor_param_value(_lookup_state_value(form_state, name))
        return f':{param_name}'

    compiled = EVENT_CURSOR_SQL_PARAM_RE.sub(replace_param, filter_sql)
    return compiled, params


def _load_lookup_object_props(menustamp: str, object_name: str, table_name: str = '', target_field: str = '') -> dict:
    stamp = str(menustamp or '').strip()
    name = str(object_name or '').strip()
    if not stamp or not name:
        return {}

    def _has_lookup_source(props: dict) -> bool:
        return bool(
            _lookup_prop(props, 'lookup_table', 'table', 'source')
            and _lookup_prop(props, 'lookup_value_field', 'value_field', 'source_field')
        )

    first_table_field_props = {}
    if _column_exists('MENU_OBJETOS', 'MENUOBJSTAMP') and _column_exists('MENU_OBJETOS', 'PROPRIEDADES'):
        row = db.session.execute(text("""
            SELECT TOP 1
                UPPER(LTRIM(RTRIM(ISNULL(TIPO, '')))) AS TIPO,
                ISNULL(PROPRIEDADES, '{}') AS PROPRIEDADES
            FROM dbo.MENU_OBJETOS
            WHERE LTRIM(RTRIM(ISNULL(MENUSTAMP, ''))) = :menustamp
              AND UPPER(LTRIM(RTRIM(ISNULL(NMCAMPO, '')))) = UPPER(:object_name)
              AND ISNULL(ATIVO, 1) = 1
        """), {'menustamp': stamp, 'object_name': name}).mappings().first()
        if row and str(row.get('TIPO') or '').strip().upper() == 'TABLE_FIELD':
            props = _parse_lookup_props(row.get('PROPRIEDADES'))
            if _has_lookup_source(props):
                return props
            if props:
                first_table_field_props = props

    screen_table = str(table_name or '').strip().upper()
    if not screen_table:
        menu_row = db.session.execute(text("""
            SELECT TOP 1 UPPER(LTRIM(RTRIM(ISNULL(TABELA, '')))) AS TABELA
            FROM dbo.MENU
            WHERE LTRIM(RTRIM(ISNULL(MENUSTAMP, ''))) = :menustamp
        """), {'menustamp': stamp}).mappings().first()
        screen_table = str((menu_row or {}).get('TABELA') or '').strip().upper()
    if not screen_table or not _column_exists('CAMPOS', 'PROPRIEDADES'):
        return first_table_field_props

    field_candidates = []
    for candidate in (name, target_field):
        normalized = str(candidate or '').strip().upper()
        if normalized and normalized not in field_candidates:
            field_candidates.append(normalized)
    for field_name in field_candidates:
        row = db.session.execute(text("""
            SELECT TOP 1
                UPPER(LTRIM(RTRIM(ISNULL(TIPO, '')))) AS TIPO,
                ISNULL(PROPRIEDADES, '{}') AS PROPRIEDADES
            FROM dbo.CAMPOS
            WHERE UPPER(LTRIM(RTRIM(ISNULL(TABELA, '')))) = :table_name
              AND UPPER(LTRIM(RTRIM(ISNULL(NMCAMPO, '')))) = :field_name
        """), {'table_name': screen_table, 'field_name': field_name}).mappings().first()
        if row and str(row.get('TIPO') or '').strip().upper() == 'TABLE_FIELD':
            props = _parse_lookup_props(row.get('PROPRIEDADES'))
            if _has_lookup_source(props):
                return props
            if props and not first_table_field_props:
                first_table_field_props = props

    return first_table_field_props


def _normalize_menu_variable_name(value: str) -> str:
    raw = re.sub(r'[^A-Z0-9_]+', '_', str(value or '').strip().upper())
    raw = re.sub(r'_+', '_', raw).strip('_')
    return raw[:60]


def _load_menu_variables_for_menu(menustamp: str) -> dict[str, dict]:
    stamp = (menustamp or '').strip()
    if not stamp or not _column_exists('MENU_VARIAVEIS', 'MENUVARSTAMP'):
        return {}

    rows = db.session.execute(text("""
        SELECT
            LTRIM(RTRIM(ISNULL(NOME, ''))) AS NOME,
            LTRIM(RTRIM(ISNULL(DESCRICAO, ''))) AS DESCRICAO,
            UPPER(LTRIM(RTRIM(ISNULL(TIPO, 'TEXT')))) AS TIPO,
            LTRIM(RTRIM(ISNULL(VALOR_DEFAULT, ''))) AS VALOR_DEFAULT,
            ISNULL(PROPRIEDADES, '{}') AS PROPRIEDADES
        FROM dbo.MENU_VARIAVEIS
        WHERE LTRIM(RTRIM(ISNULL(MENUSTAMP, ''))) = :menustamp
          AND ISNULL(ATIVO, 1) = 1
        ORDER BY ISNULL(ORDEM, 0), LTRIM(RTRIM(ISNULL(DESCRICAO, ''))), LTRIM(RTRIM(ISNULL(NOME, '')))
    """), {'menustamp': stamp}).mappings().all()

    variables = {}
    for row in rows:
        props = {}
        raw_props = row.get('PROPRIEDADES')
        if isinstance(raw_props, dict):
            props = dict(raw_props)
        else:
            try:
                parsed = json.loads(str(raw_props or '').strip() or '{}')
                if isinstance(parsed, dict):
                    props = parsed
            except Exception:
                props = {}
        variable_name = _normalize_menu_variable_name(row.get('NOME'))
        if not variable_name:
            continue
        variables[variable_name] = {
            'name': variable_name,
            'descricao': str(row.get('DESCRICAO') or '').strip(),
            'tipo': str(row.get('TIPO') or 'TEXT').strip().upper(),
            'valor_default': str(row.get('VALOR_DEFAULT') or '').strip(),
            'propriedades': props,
        }
    return variables


def _load_menu_objects_for_menu(menustamp: str) -> list[dict]:
    stamp = (menustamp or '').strip()
    if not stamp or not _column_exists('MENU_OBJETOS', 'MENUOBJSTAMP'):
        return []
    variables_map = _load_menu_variables_for_menu(stamp)

    rows = db.session.execute(text("""
        SELECT
            LTRIM(RTRIM(ISNULL(NMCAMPO, ''))) AS NMCAMPO,
            LTRIM(RTRIM(ISNULL(DESCRICAO, ''))) AS DESCRICAO,
            UPPER(LTRIM(RTRIM(ISNULL(TIPO, 'TEXT')))) AS TIPO,
            ISNULL(ORDEM, 0) AS ORDEM,
            ISNULL(TAM, 5) AS TAM,
            ISNULL(ORDEM_MOBILE, ISNULL(ORDEM, 0)) AS ORDEM_MOBILE,
            ISNULL(TAM_MOBILE, ISNULL(TAM, 5)) AS TAM_MOBILE,
            ISNULL(VISIVEL, 1) AS VISIVEL,
            ISNULL(RONLY, 0) AS RONLY,
            ISNULL(OBRIGATORIO, 0) AS OBRIGATORIO,
            LTRIM(RTRIM(ISNULL(CONDICAO_VISIVEL, ''))) AS CONDICAO_VISIVEL,
            LTRIM(RTRIM(ISNULL(COMBO, ''))) AS COMBO,
            ISNULL(DECIMAIS, 0) AS DECIMAIS,
            MINIMO AS MINIMO,
            MAXIMO AS MAXIMO,
            ISNULL(PROPRIEDADES, '{}') AS PROPRIEDADES
        FROM dbo.MENU_OBJETOS
        WHERE LTRIM(RTRIM(ISNULL(MENUSTAMP, ''))) = :menustamp
          AND ISNULL(ATIVO, 1) = 1
        ORDER BY ISNULL(ORDEM, 0), LTRIM(RTRIM(ISNULL(DESCRICAO, ''))), LTRIM(RTRIM(ISNULL(NMCAMPO, '')))
    """), {'menustamp': stamp}).mappings().all()

    objects = []
    for row in rows:
        props = {}
        raw_props = row.get('PROPRIEDADES')
        if isinstance(raw_props, dict):
            props = dict(raw_props)
        else:
            try:
                parsed = json.loads(str(raw_props or '').strip() or '{}')
                if isinstance(parsed, dict):
                    props = parsed
            except Exception:
                props = {}
        variable_name = _normalize_menu_variable_name(props.get('variable_name'))
        bound_variable = variables_map.get(variable_name) if variable_name else None
        if bound_variable:
            props['variable_name'] = bound_variable['name']
            props['variable_label'] = bound_variable['descricao'] or bound_variable['name']
            props['variable_type'] = bound_variable['tipo']
            props['variable_default'] = bound_variable['valor_default']
            props['variable_help_text'] = str((bound_variable.get('propriedades') or {}).get('help_text') or '').strip()
        objects.append({
            'name': str(row.get('NMCAMPO') or '').strip(),
            'descricao': str(row.get('DESCRICAO') or '').strip(),
            'tipo': str(row.get('TIPO') or 'TEXT').strip().upper(),
            'lista': False,
            'filtro': False,
            'filtrodefault': '',
            'admin': False,
            'primary_key': False,
            'readonly': bool(int(row.get('RONLY') or 0) == 1),
            'combo': str(row.get('COMBO') or '').strip(),
            'virtual': None,
            'ordem': int(row.get('ORDEM') or 0),
            'tam': int(row.get('TAM') or 5),
            'ordem_mobile': int(row.get('ORDEM_MOBILE') or 0),
            'tam_mobile': int(row.get('TAM_MOBILE') or 5),
            'condicao_visivel': str(row.get('CONDICAO_VISIVEL') or '').strip(),
            'visivel': bool(int(row.get('VISIVEL') or 0) == 1),
            'obrigatorio': bool(int(row.get('OBRIGATORIO') or 0) == 1),
            'precisao': None,
            'decimais': int(row.get('DECIMAIS') or 0),
            'minimo': None if row.get('MINIMO') is None else str(row.get('MINIMO')).strip(),
            'maximo': None if row.get('MAXIMO') is None else str(row.get('MAXIMO')).strip(),
            'is_menu_object': True,
            'ui_only': True,
            'propriedades': props,
        })
    return objects


def _normalize_menu_event_name(value: str) -> str:
    raw = re.sub(r'[^a-z0-9_]+', '_', str(value or '').strip().lower())
    raw = re.sub(r'_+', '_', raw).strip('_')
    return raw


def _load_menu_screen_events(menustamp: str) -> dict[str, dict]:
    stamp = (menustamp or '').strip()
    if not stamp or not _column_exists('MENU_EVENTOS', 'MENUEVENTOSTAMP'):
        return {}

    rows = db.session.execute(text("""
        SELECT
            LTRIM(RTRIM(ISNULL(EVENTO, ''))) AS EVENTO,
            ISNULL(FLUXO, '{}') AS FLUXO
        FROM dbo.MENU_EVENTOS
        WHERE LTRIM(RTRIM(ISNULL(MENUSTAMP, ''))) = :menustamp
          AND ISNULL(ATIVO, 1) = 1
        ORDER BY LTRIM(RTRIM(ISNULL(EVENTO, '')))
    """), {'menustamp': stamp}).mappings().all()

    events = {}
    for row in rows:
        event_name = _normalize_menu_event_name(row.get('EVENTO'))
        if not event_name:
            continue
        flow = {}
        raw_flow = row.get('FLUXO')
        if isinstance(raw_flow, dict):
            flow = dict(raw_flow)
        else:
            try:
                parsed = json.loads(str(raw_flow or '').strip() or '{}')
                if isinstance(parsed, dict):
                    flow = parsed
            except Exception:
                flow = {}
        if isinstance(flow.get('lines'), list):
            events[event_name] = flow
    return events

# --------------------------------------------------
# Helper: reflect a table by name
# --------------------------------------------------
def _current_db_bind():
    try:
        return db.session.get_bind()
    except Exception:
        return db.engine


def _clean_identifier_part(value: str) -> str:
    return str(value or '').strip().strip('[]').strip()


def _split_table_identifier(table_name: str) -> tuple[str, str]:
    raw = str(table_name or '').strip().replace('[', '').replace(']', '')
    parts = [part.strip() for part in raw.split('.') if part.strip()]
    if len(parts) >= 2:
        return parts[-2], parts[-1]
    return 'dbo', parts[0] if parts else ''


def _resolve_table_identifier(table_name: str) -> tuple[str, str]:
    requested_schema, requested_table = _split_table_identifier(table_name)
    requested_schema = _clean_identifier_part(requested_schema) or 'dbo'
    requested_table = _clean_identifier_part(requested_table)
    if not requested_table:
        return requested_schema, ''

    row = db.session.execute(text("""
        SELECT TOP 1
            S.name AS SCHEMA_NAME,
            T.name AS TABLE_NAME
        FROM sys.objects T
        INNER JOIN sys.schemas S
            ON S.schema_id = T.schema_id
        WHERE T.type IN ('U', 'V')
          AND T.is_ms_shipped = 0
          AND UPPER(T.name) = UPPER(:table_name)
          AND (
              UPPER(S.name) = UPPER(:schema_name)
              OR :explicit_schema = 0
          )
        ORDER BY
            CASE WHEN UPPER(S.name) = UPPER(:schema_name) THEN 0 ELSE 1 END,
            CASE WHEN S.name = 'dbo' THEN 0 ELSE 1 END,
            CASE WHEN T.type = 'U' THEN 0 ELSE 1 END,
            S.name,
            T.name
    """), {
        'schema_name': requested_schema,
        'table_name': requested_table,
        'explicit_schema': 0 if '.' not in str(table_name or '') else 1,
    }).mappings().first()
    if row:
        schema_name = str(row.get('SCHEMA_NAME') or '').strip()
        physical_table = str(row.get('TABLE_NAME') or '').strip()
        if schema_name and physical_table:
            return schema_name, physical_table
    return requested_schema, requested_table


def get_table(table_name):
    meta = MetaData()
    schema_name, physical_table = _resolve_table_identifier(table_name)
    if not physical_table:
        abort(404, f"Tabela {table_name} não encontrada")
    try:
        return Table(
            physical_table,
            meta,
            schema=schema_name,
            autoload_with=_current_db_bind()
        )
    except Exception as e:
        current_app.logger.error(f"Erro ao refletir tabela {schema_name}.{physical_table} ({table_name}): {e}")
        abort(404, f"Tabela {table_name} não encontrada")


def _column_exists(table_name: str, column_name: str) -> bool:
    schema_name, physical_table = _resolve_table_identifier(table_name)
    if not physical_table or not str(column_name or '').strip():
        return False
    row = db.session.execute(text("""
        SELECT 1
        FROM sys.columns C
        INNER JOIN sys.objects T
            ON T.object_id = C.object_id
        INNER JOIN sys.schemas S
            ON S.schema_id = T.schema_id
        WHERE T.type IN ('U', 'V')
          AND UPPER(S.name) = UPPER(:schema_name)
          AND UPPER(T.name) = UPPER(:table_name)
          AND UPPER(C.name) = UPPER(:column_name)
    """), {
        'schema_name': schema_name,
        'table_name': physical_table,
        'column_name': str(column_name or '').strip(),
    }).first()
    return bool(row)


def _table_is_fe_scoped(table_name: str) -> bool:
    tn = (table_name or '').strip().upper()
    return tn not in ('',) and _column_exists(tn, 'FEID')


def _is_partner_table(table_name: str) -> bool:
    return (table_name or '').strip().upper() in ('CL', 'FL')


def _current_feid_or_abort() -> int:
    try:
        return get_current_feid()
    except MissingCurrentEntityError as exc:
        abort(403, str(exc))


def _normalize_vies_text(value) -> str:
    if value is None:
        return ''
    raw = str(value).replace('\r\n', '\n').replace('\r', '\n')
    lines = []
    for line in raw.split('\n'):
        clean = re.sub(r'\s+', ' ', (line or '').strip())
        if clean and clean != '---':
            lines.append(clean)
    return '\n'.join(lines)


def _normalize_vies_vat(vat_value: str) -> tuple[str, str]:
    raw = re.sub(r'[^A-Z0-9]', '', str(vat_value or '').upper())
    if len(raw) >= 3 and raw[:2].isalpha():
        return raw[:2], raw[2:]
    return 'PT', raw


def _is_valid_portuguese_nif(vat_number: str) -> bool:
    digits = re.sub(r'\D', '', str(vat_number or ''))
    if len(digits) != 9:
        return False
    total = sum(int(digits[idx]) * (9 - idx) for idx in range(8))
    check_digit = 11 - (total % 11)
    if check_digit >= 10:
        check_digit = 0
    return check_digit == int(digits[8])


def _parse_vies_address(address: str, country_code: str = 'PT') -> dict[str, str]:
    normalized = _normalize_vies_text(address)
    lines = [line.strip(' ,;') for line in normalized.split('\n') if line.strip(' ,;')]
    result = {
        'morada': '',
        'codpost': '',
        'local': '',
        'address': normalized,
    }
    if not lines:
        return result

    upper_country = (country_code or 'PT').strip().upper()
    if upper_country == 'PT':
        for idx in range(len(lines) - 1, -1, -1):
            match = re.match(r'^(?P<codpost>\d{4}-\d{3})(?:\s+(?P<local>.+))?$', lines[idx], re.IGNORECASE)
            if match:
                result['codpost'] = (match.group('codpost') or '').strip().upper()
                result['local'] = (match.group('local') or '').strip()
                morada_lines = lines[:idx]
                result['morada'] = ', '.join(morada_lines).strip(' ,')
                break

    if not result['morada']:
        if len(lines) > 1:
            result['morada'] = ', '.join(lines[:-1]).strip(' ,')
            if not result['local'] and not result['codpost']:
                result['local'] = lines[-1]
        else:
            result['morada'] = lines[0]

    return result


def _extract_vies_fault(xml_bytes: bytes) -> tuple[str, str]:
    try:
        root = ET.fromstring(xml_bytes)
    except Exception:
        return '', ''
    ns = {'soap': VIES_SOAP_NS}
    fault = root.find('.//soap:Fault', ns)
    if fault is None:
        return '', ''
    code = (fault.findtext('faultcode') or '').strip()
    message = (fault.findtext('faultstring') or '').strip()
    return code, message


def _friendly_vies_error_message(raw_message: str) -> str:
    token = (raw_message or '').strip().upper()
    if 'INVALID_INPUT' in token:
        return 'NIF inválido para consulta no VIES.'
    if 'SERVICE_UNAVAILABLE' in token or 'SERVER_BUSY' in token or 'TIMEOUT' in token:
        return 'O serviço VIES está temporariamente indisponível.'
    if 'MS_UNAVAILABLE' in token:
        return 'O serviço VIES do país indicado está indisponível.'
    return 'Não foi possível obter dados do VIES.'


def _fetch_vies_info(vat_value: str) -> dict:
    country_code, vat_number = _normalize_vies_vat(vat_value)
    if len(country_code) != 2 or not vat_number:
        raise ValueError('NIF inválido para consulta no VIES.')
    if country_code == 'PT' and not _is_valid_portuguese_nif(vat_number):
        raise ValueError('O NIF introduzido não é válido. Se for um NIF português, confirma os 9 dígitos e o dígito de controlo.')

    envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="{VIES_SOAP_NS}" xmlns:urn="{VIES_TYPES_NS}">
  <soapenv:Header/>
  <soapenv:Body>
    <urn:checkVat>
      <urn:countryCode>{country_code}</urn:countryCode>
      <urn:vatNumber>{vat_number}</urn:vatNumber>
    </urn:checkVat>
  </soapenv:Body>
</soapenv:Envelope>""".encode('utf-8')

    req = urllib_request.Request(
        VIES_CHECKVAT_URL,
        data=envelope,
        headers={
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': '',
        },
        method='POST',
    )

    try:
        with urllib_request.urlopen(req, timeout=20) as resp:
            response_bytes = resp.read()
    except urllib_error.HTTPError as exc:
        response_bytes = exc.read() or b''
        _, fault_message = _extract_vies_fault(response_bytes)
        raise RuntimeError(_friendly_vies_error_message(fault_message or str(exc))) from exc
    except urllib_error.URLError as exc:
        raise RuntimeError('Não foi possível ligar ao serviço VIES.') from exc

    try:
        root = ET.fromstring(response_bytes)
    except Exception as exc:
        raise RuntimeError('Resposta inválida do serviço VIES.') from exc

    ns = {
        'soap': VIES_SOAP_NS,
        'vies': VIES_TYPES_NS,
    }
    fault = root.find('.//soap:Fault', ns)
    if fault is not None:
        raise RuntimeError(_friendly_vies_error_message(fault.findtext('faultstring') or ''))

    response_node = root.find('.//vies:checkVatResponse', ns)
    if response_node is None:
        raise RuntimeError('Resposta inválida do serviço VIES.')

    valid = (response_node.findtext('vies:valid', default='', namespaces=ns) or '').strip().lower() == 'true'
    response_country = (response_node.findtext('vies:countryCode', default=country_code, namespaces=ns) or country_code).strip().upper()
    response_vat = (response_node.findtext('vies:vatNumber', default=vat_number, namespaces=ns) or vat_number).strip().upper()
    name = _normalize_vies_text(response_node.findtext('vies:name', default='', namespaces=ns))
    address = _normalize_vies_text(response_node.findtext('vies:address', default='', namespaces=ns))
    parsed_address = _parse_vies_address(address, response_country)

    return {
        'valid': valid,
        'country_code': response_country,
        'vat_number': response_vat,
        'name': name,
        'address': address,
        'morada': parsed_address.get('morada', ''),
        'codpost': parsed_address.get('codpost', ''),
        'local': parsed_address.get('local', ''),
    }


def _next_incremental_no(table_name: str, current_feid: int | None = None) -> int:
    tn = (table_name or '').strip().upper()
    if not tn or not _column_exists(tn, 'NO'):
        return 1
    sql = text(f"""
        SELECT ISNULL(MAX(TRY_CAST(NO AS int)), 0) + 1 AS NEXT_NO
          FROM dbo.{tn}
         WHERE 1 = 1
         {_sql_feid_clause(tn) if current_feid is not None else ''}
    """)
    params = {'current_feid': current_feid} if current_feid is not None else {}
    value = db.session.execute(sql, params).scalar()
    try:
        next_no = int(value or 1)
    except Exception:
        next_no = 1
    return max(1, next_no)


def _record_no_exists(table_name: str, no_value, current_feid: int | None = None, exclude_stamp: str | None = None) -> bool:
    tn = (table_name or '').strip().upper()
    if not tn or not _column_exists(tn, 'NO'):
        return False
    pk_name = f"{tn}STAMP"
    exclude_sql = f" AND ISNULL({pk_name}, '') <> :exclude_stamp" if exclude_stamp else ''
    sql = text(f"""
        SELECT TOP 1 1
          FROM dbo.{tn}
         WHERE TRY_CAST(NO AS int) = :no
         {_sql_feid_clause(tn) if current_feid is not None else ''}
         {exclude_sql}
    """)
    params = {'no': int(no_value)}
    if current_feid is not None:
        params['current_feid'] = current_feid
    if exclude_stamp:
        params['exclude_stamp'] = exclude_stamp
    return bool(db.session.execute(sql, params).first())


def _generate_stamp_value(max_length: int | None = None) -> str:
    raw = str(uuid.uuid4()).upper()
    if isinstance(max_length, int) and max_length > 0:
        return raw[:max_length]
    return raw[:25]


def _ensure_named_stamp(table, table_name: str, clean: dict) -> None:
    tn = (table_name or '').strip().upper()
    stamp_name = f"{tn}STAMP"
    if stamp_name not in table.c:
        return
    current_value = clean.get(stamp_name)
    if str(current_value or '').strip():
        return
    column = table.c[stamp_name]
    if getattr(column, 'server_default', None) is not None or getattr(column, 'default', None) is not None:
        return
    python_type = getattr(column.type, 'python_type', None)
    try:
        if python_type not in (str,):
            return
    except Exception:
        return
    clean[stamp_name] = _generate_stamp_value(getattr(column.type, 'length', None))


def _apply_feid_scope_stmt(stmt, table, table_name: str, mode: str = 'read'):
    tn = (table_name or '').strip().upper()
    if _table_is_fe_scoped(tn):
        current_feid = _current_feid_or_abort()
        if tn == 'AL' and hasattr(table.c, 'FEID_GESTOR'):
            stmt = stmt.where(or_(
                getattr(table.c, 'FEID') == current_feid,
                getattr(table.c, 'FEID_GESTOR') == current_feid,
            ))
        elif tn == 'RS' and mode == 'read' and hasattr(table.c, 'ALOJAMENTO'):
            al_table = get_table('AL')
            owner_visibility = exists(
                select(1)
                .select_from(al_table)
                .where(
                    and_(
                        al_table.c.NOME == table.c.ALOJAMENTO,
                        al_table.c.FEID == current_feid,
                    )
                )
            )
            stmt = stmt.where(or_(
                getattr(table.c, 'FEID') == current_feid,
                owner_visibility,
            ))
        elif tn == 'RS' and mode == 'write' and hasattr(table.c, 'ALOJAMENTO'):
            al_table = get_table('AL')
            manager_or_owner_write = exists(
                select(1)
                .select_from(al_table)
                .where(
                    and_(
                        al_table.c.NOME == table.c.ALOJAMENTO,
                        or_(
                            and_(
                                al_table.c.FEID_GESTOR.isnot(None),
                                al_table.c.FEID_GESTOR != 0,
                                al_table.c.FEID_GESTOR == current_feid,
                            ),
                            and_(
                                or_(al_table.c.FEID_GESTOR.is_(None), al_table.c.FEID_GESTOR == 0),
                                getattr(table.c, 'FEID') == current_feid,
                            ),
                        ),
                    )
                )
            )
            stmt = stmt.where(manager_or_owner_write)
        else:
            stmt = stmt.where(getattr(table.c, 'FEID') == current_feid)
    return stmt


def _sql_feid_clause(table_name: str, alias: str = '', param_name: str = 'current_feid', mode: str = 'read') -> str:
    tn = (table_name or '').strip().upper()
    if not _table_is_fe_scoped(tn):
        return ''
    prefix = f'{alias}.' if alias else ''
    if tn == 'AL' and _column_exists('AL', 'FEID_GESTOR'):
        return (
            f" AND (ISNULL({prefix}FEID, 0) = :{param_name}"
            f" OR ISNULL({prefix}FEID_GESTOR, 0) = :{param_name})"
        )
    if tn == 'RS' and mode == 'read' and _column_exists('RS', 'ALOJAMENTO'):
        rs_aloj = f"{prefix}ALOJAMENTO" if prefix else "ALOJAMENTO"
        return (
            f" AND (ISNULL({prefix}FEID, 0) = :{param_name}"
            f" OR EXISTS ("
            f"     SELECT 1"
            f"       FROM dbo.AL ALV"
            f"      WHERE LTRIM(RTRIM(ISNULL(ALV.NOME,''))) = LTRIM(RTRIM(ISNULL({rs_aloj},'')))"
            f"        AND ISNULL(ALV.FEID, 0) = :{param_name}"
            f" ))"
        )
    if tn == 'RS' and mode == 'write' and _column_exists('RS', 'ALOJAMENTO') and _column_exists('AL', 'FEID_GESTOR'):
        rs_aloj = f"{prefix}ALOJAMENTO" if prefix else "ALOJAMENTO"
        return (
            f" AND EXISTS ("
            f"     SELECT 1"
            f"       FROM dbo.AL ALV"
            f"      WHERE LTRIM(RTRIM(ISNULL(ALV.NOME,''))) = LTRIM(RTRIM(ISNULL({rs_aloj},'')))"
            f"        AND ("
            f"              (ISNULL(ALV.FEID_GESTOR, 0) <> 0 AND ISNULL(ALV.FEID_GESTOR, 0) = :{param_name})"
            f"           OR (ISNULL(ALV.FEID_GESTOR, 0) = 0 AND ISNULL({prefix}FEID, 0) = :{param_name})"
            f"        )"
            f" )"
        )
    return f" AND ISNULL({prefix}FEID, 0) = :{param_name}"


def al_fotos_table_exists() -> bool:
    try:
        row = db.session.execute(text("""
            SELECT 1
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'AL_FOTOS'
        """)).fetchone()
        return row is not None
    except Exception:
        return False

def ensure_al_fotos_schema() -> bool:
    if not al_fotos_table_exists():
        return False
    if not _column_exists('AL_FOTOS', 'CHECKIN'):
        db.session.execute(text("""
            ALTER TABLE dbo.AL_FOTOS
            ADD CHECKIN BIT NOT NULL
                CONSTRAINT DF_AL_FOTOS_CHECKIN DEFAULT (0)
        """))
        db.session.commit()
    return True

# --------------------------------------------------
# Views para front-end
# --------------------------------------------------
@bp.route('/view/calendar/')
@login_required
def view_calendar():
    return render_template('calendar.html')

@bp.route('/view/<table_name>/', defaults={'record_stamp': None}, strict_slashes=False)
@bp.route('/view/<table_name>/<record_stamp>')
@login_required
def view_table(table_name, record_stamp):
    requested_menu_stamp = (request.args.get('menustamp') or '').strip()
    menu_item = None
    if requested_menu_stamp:
        menu_item = Menu.query.filter_by(menustamp=requested_menu_stamp, tabela=table_name).first()
    if menu_item is None:
        menu_item = Menu.query.filter_by(tabela=table_name).first()
    menu_label = _translated_menu_label(menu_item, menu_item.nome) if menu_item else table_name.capitalize()
    return render_template(
        'dynamic_list.html',
        table_name=table_name,
        record_stamp=record_stamp,
        menu_label=menu_label,
        menu_stamp=(menu_item.menustamp if menu_item else '')
    )

@bp.route('/form/<table_name>/', defaults={'record_stamp': None}, strict_slashes=False)
@bp.route('/form/<table_name>/<record_stamp>')
@login_required
def edit_table(table_name, record_stamp):
    from models import MenuBotoes
    requested_menu_stamp = (request.args.get('menustamp') or '').strip()
    menu_item = None
    if requested_menu_stamp:
        menu_item = Menu.query.filter_by(menustamp=requested_menu_stamp, tabela=table_name).first()
    if menu_item is None:
        menu_item = Menu.query.filter_by(tabela=table_name).first()
    menu_label = _translated_menu_label(menu_item, menu_item.nome) if menu_item else table_name.capitalize()
    exact_widths = _menu_uses_exact_widths(table_name)

    botoes_query = MenuBotoes.query.filter_by(
        TABELA=table_name, ATIVO=True
    ).order_by(MenuBotoes.ORDEM)

    botoes = [{
        'NOME': b.NOME,
        'ICONE': b.ICONE,
        'TEXTO': b.TEXTO,
        'COR': b.COR,
        'TIPO': b.TIPO,
        'ACAO': b.ACAO,
        'CONDICAO': b.CONDICAO,
        'DESTINO': b.DESTINO
    } for b in botoes_query]
    
    linhas_exist = Linhas.query.filter_by(MAE=table_name).count() > 0


    return render_template(
        'dynamic_form.html',
        table_name=table_name,
        record_stamp=record_stamp,
        menu_label=menu_label,
        botoes=botoes,
        linhas_exist=linhas_exist,
        exact_widths=exact_widths,
        menu_stamp=(menu_item.menustamp if menu_item else '')
    )


@bp.route('/api/us/<usstamp>/empresas', methods=['GET'])
@login_required
def us_empresas_list(usstamp):
    if not has_permission('US', 'consultar'):
        return jsonify({'error': 'Sem permissão para consultar utilizadores'}), 403
    try:
        usstamp = (usstamp or '').strip()
        if not usstamp:
            return jsonify({'error': 'USSTAMP em falta'}), 400

        fe_active_filter = "AND ISNULL(FE.ATIVA, 0) = 1" if _column_exists('FE', 'ATIVA') else ""
        rows = db.session.execute(text(f"""
            SELECT
                UF.USFESTAMP,
                UF.USSTAMP,
                UF.FEID,
                ISNULL(FE.NOME, '') AS FE_NOME,
                ISNULL(UF.ATIVO, 0) AS ATIVO,
                ISNULL(UF.PRINCIPAL, 0) AS PRINCIPAL
            FROM dbo.US_FE UF
            INNER JOIN dbo.FE FE
                ON FE.FEID = UF.FEID
            WHERE
                UF.USSTAMP = :usstamp
                {fe_active_filter}
            ORDER BY ISNULL(UF.PRINCIPAL, 0) DESC, ISNULL(FE.NOME, ''), UF.FEID
        """), {'usstamp': usstamp}).mappings().all()

        fe_options = db.session.execute(text(f"""
            SELECT
                FEID,
                ISNULL(NOME, '') AS NOME
            FROM dbo.FE
            WHERE 1=1
            {fe_active_filter}
            ORDER BY ISNULL(NOME, ''), FEID
        """)).mappings().all()

        return jsonify({
            'rows': [dict(r) for r in rows],
            'fe_options': [dict(r) for r in fe_options],
        })
    except Exception as e:
        current_app.logger.exception('Erro ao carregar US_FE')
        return jsonify({'error': str(e)}), 500


@bp.route('/api/us/<usstamp>/empresas', methods=['POST'])
@login_required
def us_empresas_create(usstamp):
    if not has_permission('US', 'editar'):
        return jsonify({'error': 'Sem permissão para editar utilizadores'}), 403
    try:
        usstamp = (usstamp or '').strip()
        payload = request.get_json(force=True) or {}
        feid = int(payload.get('FEID') or 0)
        ativo = bool(payload.get('ATIVO', True))
        principal = bool(payload.get('PRINCIPAL', False))
        if not usstamp:
            return jsonify({'error': 'USSTAMP em falta'}), 400
        if feid <= 0:
            return jsonify({'error': 'Empresa inválida'}), 400

        dup = db.session.execute(text("""
            SELECT TOP 1 USFESTAMP
            FROM dbo.US_FE
            WHERE USSTAMP = :usstamp
              AND FEID = :feid
        """), {'usstamp': usstamp, 'feid': feid}).mappings().first()
        if dup:
            return jsonify({'error': 'Esta empresa já está associada ao utilizador.'}), 400

        usfestamp = uuid.uuid4().hex.upper()[:25]
        now = datetime.now()
        user_login = (getattr(current_user, 'LOGIN', '') or '').strip()

        if principal:
            db.session.execute(text("""
                UPDATE dbo.US_FE
                   SET PRINCIPAL = 0,
                       DTAlteracao = :dtalt,
                       USERALTERACAO = :useralt
                 WHERE USSTAMP = :usstamp
            """), {'usstamp': usstamp, 'dtalt': now, 'useralt': user_login})

        db.session.execute(text("""
            INSERT INTO dbo.US_FE
            (
                USFESTAMP, USSTAMP, FEID, ATIVO, PRINCIPAL,
                DTCriacao, DTAlteracao, USERCRIACAO, USERALTERACAO
            )
            VALUES
            (
                :USFESTAMP, :USSTAMP, :FEID, :ATIVO, :PRINCIPAL,
                :DTCriacao, :DTAlteracao, :USERCRIACAO, :USERALTERACAO
            )
        """), {
            'USFESTAMP': usfestamp,
            'USSTAMP': usstamp,
            'FEID': feid,
            'ATIVO': ativo,
            'PRINCIPAL': principal,
            'DTCriacao': now,
            'DTAlteracao': now,
            'USERCRIACAO': user_login,
            'USERALTERACAO': user_login,
        })
        db.session.commit()
        return jsonify({'success': True, 'USFESTAMP': usfestamp}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Erro ao criar US_FE')
        return jsonify({'error': str(e)}), 500


@bp.route('/api/us/<usstamp>/empresas/<usfestamp>', methods=['PUT'])
@login_required
def us_empresas_update(usstamp, usfestamp):
    if not has_permission('US', 'editar'):
        return jsonify({'error': 'Sem permissão para editar utilizadores'}), 403
    try:
        usstamp = (usstamp or '').strip()
        usfestamp = (usfestamp or '').strip()
        payload = request.get_json(force=True) or {}
        ativo = bool(payload.get('ATIVO', True))
        principal = bool(payload.get('PRINCIPAL', False))
        if not usstamp or not usfestamp:
            return jsonify({'error': 'Dados em falta'}), 400

        exists = db.session.execute(text("""
            SELECT TOP 1 USFESTAMP
            FROM dbo.US_FE
            WHERE USFESTAMP = :usfestamp
              AND USSTAMP = :usstamp
        """), {'usfestamp': usfestamp, 'usstamp': usstamp}).mappings().first()
        if not exists:
            return jsonify({'error': 'Associação não encontrada'}), 404

        now = datetime.now()
        user_login = (getattr(current_user, 'LOGIN', '') or '').strip()

        if principal:
            db.session.execute(text("""
                UPDATE dbo.US_FE
                   SET PRINCIPAL = 0,
                       DTAlteracao = :dtalt,
                       USERALTERACAO = :useralt
                 WHERE USSTAMP = :usstamp
                   AND USFESTAMP <> :usfestamp
            """), {'usstamp': usstamp, 'usfestamp': usfestamp, 'dtalt': now, 'useralt': user_login})

        db.session.execute(text("""
            UPDATE dbo.US_FE
               SET ATIVO = :ativo,
                   PRINCIPAL = :principal,
                   DTAlteracao = :dtalt,
                   USERALTERACAO = :useralt
             WHERE USFESTAMP = :usfestamp
               AND USSTAMP = :usstamp
        """), {
            'ativo': ativo,
            'principal': principal,
            'dtalt': now,
            'useralt': user_login,
            'usfestamp': usfestamp,
            'usstamp': usstamp,
        })
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Erro ao atualizar US_FE')
        return jsonify({'error': str(e)}), 500


@bp.route('/api/us/<usstamp>/empresas/<usfestamp>', methods=['DELETE'])
@login_required
def us_empresas_delete(usstamp, usfestamp):
    if not has_permission('US', 'editar'):
        return jsonify({'error': 'Sem permissão para editar utilizadores'}), 403
    try:
        usstamp = (usstamp or '').strip()
        usfestamp = (usfestamp or '').strip()
        if not usstamp or not usfestamp:
            return jsonify({'error': 'Dados em falta'}), 400

        res = db.session.execute(text("""
            DELETE FROM dbo.US_FE
             WHERE USFESTAMP = :usfestamp
               AND USSTAMP = :usstamp
        """), {'usfestamp': usfestamp, 'usstamp': usstamp})
        if not res.rowcount:
            db.session.rollback()
            return jsonify({'error': 'Associação não encontrada'}), 404
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Erro ao eliminar US_FE')
        return jsonify({'error': str(e)}), 500


@bp.route('/api/al_fotos/<alstamp>', methods=['GET'])
@login_required
def al_fotos_list(alstamp):
    try:
        if not ensure_al_fotos_schema():
            return jsonify({'error': 'Tabela AL_FOTOS inexistente. Executa a migration primeiro.'}), 400
        alstamp = (alstamp or '').strip()
        if not alstamp:
            return jsonify([])
        rows = db.session.execute(text("""
            SELECT
                ALFOTOSTAMP,
                ALSTAMP,
                FICHEIRO,
                CAMINHO,
                ALT_TEXT,
                ORDEM,
                CAPA,
                CHECKIN,
                ATIVO,
                DTCRI,
                DTALT,
                UTILIZADOR
            FROM dbo.AL_FOTOS
            WHERE ALSTAMP = :alstamp
            ORDER BY CAPA DESC, ORDEM ASC, DTCRI ASC
        """), {'alstamp': alstamp}).mappings().all()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        current_app.logger.exception('Erro ao listar AL_FOTOS')
        return jsonify({'error': str(e)}), 500


@bp.route('/api/al_fotos/<alstamp>/upload', methods=['POST'])
@login_required
def al_fotos_upload(alstamp):
    try:
        if not ensure_al_fotos_schema():
            return jsonify({'error': 'Tabela AL_FOTOS inexistente. Executa a migration primeiro.'}), 400
        alstamp = (alstamp or '').strip()
        if not alstamp:
            return jsonify({'error': 'ALSTAMP em falta'}), 400

        files = request.files.getlist('files')
        if not files:
            single = request.files.get('file')
            if single:
                files = [single]
        files = [f for f in files if f and f.filename]
        if not files:
            return jsonify({'error': 'Nenhum ficheiro enviado'}), 400

        target_dir = os.path.join(current_app.static_folder, 'images', 'alojamentos')
        os.makedirs(target_dir, exist_ok=True)
        user_login = (getattr(current_user, 'LOGIN', None) or getattr(current_user, 'NOME', None) or '').strip() or None

        existing = db.session.execute(text("""
            SELECT
                ISNULL(MAX(ORDEM), -1) AS MAX_ORDEM,
                MAX(CASE WHEN CAPA = 1 THEN 1 ELSE 0 END) AS TEM_CAPA
            FROM dbo.AL_FOTOS
            WHERE ALSTAMP = :alstamp
        """), {'alstamp': alstamp}).mappings().first() or {}
        next_ordem = int(existing.get('MAX_ORDEM') or -1) + 1
        has_cover = bool(existing.get('TEM_CAPA'))

        inserted = []
        for idx, photo in enumerate(files):
            safe_name = secure_filename(photo.filename or '')
            ext = os.path.splitext(safe_name)[1].lower()
            if ext not in ALLOWED_IMAGE_EXTENSIONS:
                return jsonify({'error': f'Formato inválido: {safe_name or photo.filename}'}), 400

            photo_stamp = uuid.uuid4().hex[:25]
            new_name = f"{uuid.uuid4().hex}{ext}"
            save_path = os.path.join(target_dir, new_name)
            photo.save(save_path)
            rel_path = f"images/alojamentos/{new_name}"
            is_cover = 1 if (not has_cover and idx == 0) else 0

            db.session.execute(text("""
                INSERT INTO dbo.AL_FOTOS
                (
                    ALFOTOSTAMP,
                    ALSTAMP,
                    FICHEIRO,
                    CAMINHO,
                    ALT_TEXT,
                    ORDEM,
                    CAPA,
                    CHECKIN,
                    ATIVO,
                    DTCRI,
                    DTALT,
                    UTILIZADOR
                )
                VALUES
                (
                    :stamp,
                    :alstamp,
                    :ficheiro,
                    :caminho,
                    :alt_text,
                    :ordem,
                    :capa,
                    0,
                    1,
                    GETDATE(),
                    GETDATE(),
                    :utilizador
                )
            """), {
                'stamp': photo_stamp,
                'alstamp': alstamp,
                'ficheiro': safe_name or photo.filename,
                'caminho': rel_path,
                'alt_text': request.form.get('alt_text', '').strip() or None,
                'ordem': next_ordem,
                'capa': is_cover,
                'utilizador': user_login,
            })
            next_ordem += 1
            inserted.append({'ALFOTOSTAMP': photo_stamp, 'CAMINHO': rel_path})

        db.session.commit()
        return jsonify({'success': True, 'items': inserted})
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Erro ao carregar AL_FOTOS')
        return jsonify({'error': str(e)}), 500


@bp.route('/api/al_fotos/<alstamp>/capa/<alfotostamp>', methods=['POST'])
@login_required
def al_fotos_set_capa(alstamp, alfotostamp):
    try:
        if not ensure_al_fotos_schema():
            return jsonify({'error': 'Tabela AL_FOTOS inexistente. Executa a migration primeiro.'}), 400
        alstamp = (alstamp or '').strip()
        alfotostamp = (alfotostamp or '').strip()
        if not alstamp or not alfotostamp:
            return jsonify({'error': 'Dados em falta'}), 400

        exists = db.session.execute(text("""
            SELECT 1
            FROM dbo.AL_FOTOS
            WHERE ALSTAMP = :alstamp
              AND ALFOTOSTAMP = :stamp
        """), {'alstamp': alstamp, 'stamp': alfotostamp}).fetchone()
        if not exists:
            return jsonify({'error': 'Foto não encontrada'}), 404

        db.session.execute(text("""
            UPDATE dbo.AL_FOTOS
            SET CAPA = 0,
                DTALT = GETDATE()
            WHERE ALSTAMP = :alstamp
        """), {'alstamp': alstamp})
        db.session.execute(text("""
            UPDATE dbo.AL_FOTOS
            SET CAPA = 1,
                DTALT = GETDATE()
            WHERE ALSTAMP = :alstamp
              AND ALFOTOSTAMP = :stamp
        """), {'alstamp': alstamp, 'stamp': alfotostamp})
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Erro ao definir capa AL_FOTOS')
        return jsonify({'error': str(e)}), 500


@bp.route('/api/al_fotos/<alstamp>/checkin/<alfotostamp>', methods=['POST'])
@login_required
def al_fotos_set_checkin(alstamp, alfotostamp):
    try:
        if not ensure_al_fotos_schema():
            return jsonify({'error': 'Tabela AL_FOTOS inexistente. Executa a migration primeiro.'}), 400
        alstamp = (alstamp or '').strip()
        alfotostamp = (alfotostamp or '').strip()
        if not alstamp or not alfotostamp:
            return jsonify({'error': 'Dados em falta'}), 400

        photo = db.session.execute(text("""
            SELECT TOP 1 ISNULL(CHECKIN, 0) AS CHECKIN
            FROM dbo.AL_FOTOS
            WHERE ALSTAMP = :alstamp
              AND ALFOTOSTAMP = :stamp
        """), {'alstamp': alstamp, 'stamp': alfotostamp}).mappings().first()
        if not photo:
            return jsonify({'error': 'Foto não encontrada'}), 404

        payload = request.get_json(silent=True) or {}
        if 'checkin' in payload:
            checkin = 1 if bool(payload.get('checkin')) else 0
        else:
            checkin = 0 if int(photo.get('CHECKIN') or 0) else 1

        db.session.execute(text("""
            UPDATE dbo.AL_FOTOS
            SET CHECKIN = :checkin,
                DTALT = GETDATE()
            WHERE ALSTAMP = :alstamp
              AND ALFOTOSTAMP = :stamp
        """), {'checkin': checkin, 'alstamp': alstamp, 'stamp': alfotostamp})
        db.session.commit()
        return jsonify({'success': True, 'CHECKIN': checkin})
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Erro ao definir check-in AL_FOTOS')
        return jsonify({'error': str(e)}), 500


@bp.route('/api/al_fotos/<alstamp>/ordem', methods=['POST'])
@login_required
def al_fotos_set_ordem(alstamp):
    try:
        if not ensure_al_fotos_schema():
            return jsonify({'error': 'Tabela AL_FOTOS inexistente. Executa a migration primeiro.'}), 400
        alstamp = (alstamp or '').strip()
        payload = request.get_json(silent=True) or {}
        items = payload.get('items') or []
        if not alstamp or not isinstance(items, list) or not items:
            return jsonify({'error': 'Ordenação inválida'}), 400

        cleaned = []
        seen = set()
        for stamp in items:
            value = str(stamp or '').strip()
            if not value or value in seen:
                continue
            seen.add(value)
            cleaned.append(value)

        rows = db.session.execute(text("""
            SELECT ALFOTOSTAMP
            FROM dbo.AL_FOTOS
            WHERE ALSTAMP = :alstamp
        """), {'alstamp': alstamp}).fetchall()
        existing = {r[0] for r in rows}
        if not existing:
            return jsonify({'error': 'Sem fotos para ordenar'}), 404

        final_order = [stamp for stamp in cleaned if stamp in existing]
        final_order.extend([stamp for stamp in existing if stamp not in final_order])

        for idx, stamp in enumerate(final_order):
            db.session.execute(text("""
                UPDATE dbo.AL_FOTOS
                SET ORDEM = :ordem,
                    DTALT = GETDATE()
                WHERE ALSTAMP = :alstamp
                  AND ALFOTOSTAMP = :stamp
            """), {'ordem': idx, 'alstamp': alstamp, 'stamp': stamp})

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Erro ao ordenar AL_FOTOS')
        return jsonify({'error': str(e)}), 500


@bp.route('/api/al_fotos/<alstamp>/<alfotostamp>', methods=['DELETE'])
@login_required
def al_fotos_delete(alstamp, alfotostamp):
    try:
        if not ensure_al_fotos_schema():
            return jsonify({'error': 'Tabela AL_FOTOS inexistente. Executa a migration primeiro.'}), 400
        alstamp = (alstamp or '').strip()
        alfotostamp = (alfotostamp or '').strip()
        if not alstamp or not alfotostamp:
            return jsonify({'error': 'Dados em falta'}), 400

        photo = db.session.execute(text("""
            SELECT ALFOTOSTAMP, CAMINHO, CAPA
            FROM dbo.AL_FOTOS
            WHERE ALSTAMP = :alstamp
              AND ALFOTOSTAMP = :stamp
        """), {'alstamp': alstamp, 'stamp': alfotostamp}).mappings().first()
        if not photo:
            return jsonify({'error': 'Foto não encontrada'}), 404

        db.session.execute(text("""
            DELETE FROM dbo.AL_FOTOS
            WHERE ALSTAMP = :alstamp
              AND ALFOTOSTAMP = :stamp
        """), {'alstamp': alstamp, 'stamp': alfotostamp})

        if photo.get('CAPA'):
            replacement = db.session.execute(text("""
                SELECT TOP 1 ALFOTOSTAMP
                FROM dbo.AL_FOTOS
                WHERE ALSTAMP = :alstamp
                ORDER BY ORDEM ASC, DTCRI ASC
            """), {'alstamp': alstamp}).fetchone()
            if replacement:
                db.session.execute(text("""
                    UPDATE dbo.AL_FOTOS
                    SET CAPA = 1,
                        DTALT = GETDATE()
                    WHERE ALSTAMP = :alstamp
                      AND ALFOTOSTAMP = :stamp
                """), {'alstamp': alstamp, 'stamp': replacement[0]})

        db.session.commit()

        caminho = str(photo.get('CAMINHO') or '').strip().replace('/', os.sep)
        if caminho:
            abs_path = os.path.join(current_app.static_folder, caminho)
            if os.path.isfile(abs_path):
                try:
                    os.remove(abs_path)
                except OSError:
                    current_app.logger.warning('Não foi possível remover ficheiro %s', abs_path)

        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Erro ao apagar AL_FOTOS')
        return jsonify({'error': str(e)}), 500

@bp.route('/fo_compras_form/', defaults={'record_stamp': None})
@bp.route('/fo_compras_form/<record_stamp>')
@login_required
def fo_compras_form(record_stamp):
    menu_item  = Menu.query.filter_by(tabela='FO').first()
    menu_label = _translated_menu_label(menu_item, menu_item.nome) if menu_item else "FO - Compras"
    return render_template(
        'fo_compras_form.html',
        record_stamp=record_stamp,
        menu_label=menu_label
    )

@bp.route('/api/fo/pagamento/<fostamp>', methods=['GET'])
@login_required
def api_fo_pagamento(fostamp):
    try:
        return jsonify(fo_pagamento_status(fostamp))
    except Exception as e:
        current_app.logger.exception('Erro em api_fo_pagamento')
        return jsonify({'error': str(e)}), 500

@bp.route('/api/fo/tp_options')
@login_required
def fo_tp_options():
    try:
        sql = text("""
            SELECT TPSTAMP, TPDESC, DIAS, OLLOCAL
            FROM V_TP
            ORDER BY TPDESC
        """)
        rows = db.session.execute(sql).fetchall()
        return jsonify([dict(r._mapping) for r in rows])
    except Exception as e:
        current_app.logger.exception('Erro em fo_tp_options')
        return jsonify({'error': str(e)}), 500

@bp.route('/api/fo/search_artigos')
@login_required
def fo_search_artigos():
    term = (request.args.get('q') or '').strip()
    if len(term) < 2:
        return jsonify([])
    try:
        current_feid = _current_feid_or_abort()
        unidade_select = "LTRIM(RTRIM(ISNULL(S.UNIDADE, ''))) AS UNIDADE," if _column_exists('ST', 'UNIDADE') else "CAST('' AS varchar(10)) AS UNIDADE,"
        sql = text("""
            SELECT TOP 10
                LTRIM(RTRIM(ISNULL(S.REF, ''))) AS REF,
                LTRIM(RTRIM(ISNULL(S.DESIGN, ''))) AS DESIGN,
                """ + unidade_select + """
                ISNULL(S.TABIVA, 0) AS TABIVA,
                LTRIM(RTRIM(ISNULL(S.FAMILIA, ''))) AS FAMILIA
            FROM dbo.ST AS S
            WHERE ISNULL(S.FEID, 0) = :feid
              AND (
                LTRIM(RTRIM(ISNULL(S.REF, ''))) LIKE :t
                OR LTRIM(RTRIM(ISNULL(S.DESIGN, ''))) LIKE :t
              )
            ORDER BY LTRIM(RTRIM(ISNULL(S.REF, '')))
        """)
        rows = db.session.execute(sql, {'feid': current_feid, 't': f'%{term}%'}).fetchall()
        return jsonify([dict(r._mapping) for r in rows])
    except Exception as e:
        current_app.logger.exception('Erro em fo_search_artigos')
        return jsonify({'error': str(e)}), 500

@bp.route('/api/fo/artigos')
@login_required
def fo_artigos():
    """
    Lista artigos para seleÃ§Ã£o via modal.
    Querystring:
      - q (opcional): termo de pesquisa (REF/DESIGN/FAMILIA)
      - limit (opcional): mÃ¡ximo de registos (default 200, max 500)
    """
    try:
        current_feid = _current_feid_or_abort()
        term = (request.args.get('q') or '').strip()
        unidade_select = "LTRIM(RTRIM(ISNULL(s.UNIDADE, ''))) AS UNIDADE," if _column_exists('ST', 'UNIDADE') else "CAST('' AS varchar(10)) AS UNIDADE,"
        try:
            limit = int(request.args.get('limit', 200))
        except Exception:
            limit = 200
        if limit < 1:
            limit = 1
        if limit > 500:
            limit = 500

        if term:
            sql = text(f"""
                SELECT TOP {limit}
                    LTRIM(RTRIM(ISNULL(s.REF, ''))) AS REF,
                    LTRIM(RTRIM(ISNULL(s.DESIGN, ''))) AS DESIGN,
                    {unidade_select}
                    LTRIM(RTRIM(ISNULL(s.FAMILIA, ''))) AS FAMILIA,
                    f.NOME AS FAMILIA_NOME,
                    ISNULL(s.TABIVA, 0) AS TABIVA
                FROM dbo.ST s
                LEFT JOIN V_STFAMI f
                  ON f.REF COLLATE DATABASE_DEFAULT = LTRIM(RTRIM(ISNULL(s.FAMILIA, ''))) COLLATE DATABASE_DEFAULT
                WHERE ISNULL(s.FEID, 0) = :feid
                  AND (
                   LTRIM(RTRIM(ISNULL(s.REF, ''))) LIKE :t
                   OR LTRIM(RTRIM(ISNULL(s.DESIGN, ''))) LIKE :t
                   OR LTRIM(RTRIM(ISNULL(s.FAMILIA, ''))) LIKE :t
                   OR f.NOME LIKE :t
                  )
                ORDER BY LTRIM(RTRIM(ISNULL(s.REF, '')))
            """)
            params = {'feid': current_feid, 't': f'%{term}%'}
        else:
            sql = text(f"""
                SELECT TOP {limit}
                    LTRIM(RTRIM(ISNULL(s.REF, ''))) AS REF,
                    LTRIM(RTRIM(ISNULL(s.DESIGN, ''))) AS DESIGN,
                    {unidade_select}
                    LTRIM(RTRIM(ISNULL(s.FAMILIA, ''))) AS FAMILIA,
                    f.NOME AS FAMILIA_NOME,
                    ISNULL(s.TABIVA, 0) AS TABIVA
                FROM dbo.ST s
                LEFT JOIN V_STFAMI f
                  ON f.REF COLLATE DATABASE_DEFAULT = LTRIM(RTRIM(ISNULL(s.FAMILIA, ''))) COLLATE DATABASE_DEFAULT
                WHERE ISNULL(s.FEID, 0) = :feid
                ORDER BY LTRIM(RTRIM(ISNULL(s.REF, '')))
            """)
            params = {'feid': current_feid}

        rows = db.session.execute(sql, params).fetchall()
        return jsonify([dict(r._mapping) for r in rows])
    except Exception as e:
        current_app.logger.exception('Erro em fo_artigos')
        return jsonify({'error': str(e)}), 500

@bp.route('/api/fo/artigos_familia', methods=['POST'])
@login_required
def fo_artigos_familia():
    """
    Devolve FAMILIA por REF, usando a tabela ST.
    Body: { "refs": ["A1", "B2", ...] }
    """
    try:
        current_feid = _current_feid_or_abort()
        body = request.get_json(silent=True) or {}
        refs = body.get('refs') or []
        if not isinstance(refs, list):
            refs = []
        cleaned = []
        seen = set()
        for r in refs:
            if r is None:
                continue
            val = str(r).strip()
            if not val:
                continue
            key = val.upper()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(val)
            if len(cleaned) >= 200:
                break
        if not cleaned:
            return jsonify({})

        sql = text("""
            SELECT
                LTRIM(RTRIM(ISNULL(REF, ''))) AS REF,
                LTRIM(RTRIM(ISNULL(FAMILIA, ''))) AS FAMILIA
            FROM dbo.ST
            WHERE ISNULL(FEID, 0) = :feid
              AND REF IN :refs
        """).bindparams(bindparam('refs', expanding=True))

        rows = db.session.execute(sql, {'feid': current_feid, 'refs': cleaned}).fetchall()
        out = {}
        for r in rows:
            ref = (r._mapping.get('REF') or '').strip()
            fam = (r._mapping.get('FAMILIA') or '').strip()
            if ref:
                out[ref] = fam
        return jsonify(out)
    except Exception as e:
        current_app.logger.exception('Erro em fo_artigos_familia')
        return jsonify({'error': str(e)}), 500

@bp.route('/api/fo/search_cliente')
@login_required
def fo_search_cliente():
    term = (request.args.get('q') or '').strip()
    if len(term) < 2:
        return jsonify([])
    try:
        sql = text("""
            SELECT TOP 10 NO, NOME, NCONT, MORADA, LOCAL, CODPOST
            FROM V_FL
            WHERE NOME LIKE :t
            ORDER BY NOME
        """)
        rows = db.session.execute(sql, {'t': f'%{term}%'}).fetchall()
        return jsonify([dict(r._mapping) for r in rows])
    except Exception as e:
        current_app.logger.exception('Erro em fo_search_cliente')
        return jsonify({'error': str(e)}), 500

@bp.route('/api/fo/taxas')
@login_required
def fo_taxas():
    try:
        sql = text("""
            SELECT TABIVA, TAXAIVA
            FROM V_TAXASIVA
            ORDER BY TABIVA
        """)
        rows = db.session.execute(sql).fetchall()
        return jsonify([dict(r._mapping) for r in rows])
    except Exception as e:
        current_app.logger.exception('Erro em fo_taxas')
        return jsonify({'error': str(e)}), 500

@bp.route('/api/fo/contratos')
@login_required
def fo_contratos():
    """
    Lista contratos (cabeçalhos) a partir do ERP.
    Se ?no=... vier preenchido (fornecedor), filtra pelo mesmo fornecedor.
    """
    try:
        no = request.args.get('no', '').strip()
        no_int = int(no) if no and no.isdigit() else 0
        erp_db = (current_app.config.get('ERP_CONTRATOS_DB') or 'GUEST_SPA_TUR').strip()
        if not re.fullmatch(r'[A-Za-z0-9_]+', erp_db):
            erp_db = 'GUEST_SPA_TUR'
        sql = text(f"""
            SELECT
                BOSTAMP,
                NDOS,
                NMDOS,
                OBRANO,
                NO,
                NOME,
                MAQUINA,
                ETOTALDEB
            FROM [{erp_db}].[dbo].[BO]
            WHERE NDOS = 14
              AND FECHADA = 0
              AND (:no = 0 OR NO = :no)
            ORDER BY OBRANO DESC, BOSTAMP DESC
        """)
        rows = db.session.execute(sql, {'no': no_int}).fetchall()
        return jsonify([dict(r._mapping) for r in rows])
    except Exception as e:
        current_app.logger.exception('Erro em fo_contratos')
        return jsonify({'error': str(e)}), 500

@bp.route('/api/fo/contratos/<bostamp>/linhas')
@login_required
def fo_contrato_linhas(bostamp):
    """
    Linhas do contrato (ERP) por BOSTAMP.
    """
    try:
        if not bostamp:
            return jsonify([])
        erp_db = (current_app.config.get('ERP_CONTRATOS_DB') or 'GUEST_SPA_TUR').strip()
        if not re.fullmatch(r'[A-Za-z0-9_]+', erp_db):
            erp_db = 'GUEST_SPA_TUR'
        sql = text(f"""
            SELECT
                BOSTAMP,
                BISTAMP,
                REF,
                DESIGN,
                QTT,
                EDEBITO,
                ETTDEB,
                CCUSTO,
                IVA,
                TABIVA
            FROM [{erp_db}].[dbo].[BI]
            WHERE NDOS = 14
              AND BOSTAMP = :bostamp
            ORDER BY BISTAMP
        """)
        rows = db.session.execute(sql, {'bostamp': bostamp}).fetchall()
        return jsonify([dict(r._mapping) for r in rows])
    except Exception as e:
        current_app.logger.exception('Erro em fo_contrato_linhas')
        return jsonify({'error': str(e)}), 500

# --------------------------------------------------
# API: DESCRIBE ou LISTAGEM
# --------------------------------------------------
@bp.route('/api/<table_name>', methods=['GET'])
@login_required
def list_or_describe(table_name):
    if request.args.get('action') == 'describe':
        include_screen_meta = str(request.args.get('include_screen_meta') or '').strip().lower() in {'1', 'true', 'yes'}
        table = get_table(table_name)
        column_meta = {col.name.upper(): col for col in table.columns} if table is not None else {}
        campos = Campo.query.filter_by(tabela=table_name).order_by(Campo.ordem).all()
        menu_stamp = _resolve_menu_stamp(table_name, request.args.get('menustamp') or '')
        visible_map = {}
        numeric_meta_map = {}
        list_layout_map = {}
        properties_map = {}
        if _column_exists(table_name='CAMPOS', column_name='VISIVEL'):
            visible_rows = db.session.execute(text("""
                SELECT
                    UPPER(LTRIM(RTRIM(ISNULL(NMCAMPO, '')))) AS NMCAMPO,
                    ISNULL(VISIVEL, 1) AS VISIVEL
                FROM dbo.CAMPOS
                WHERE UPPER(LTRIM(RTRIM(ISNULL(TABELA, '')))) = :table_name
            """), {'table_name': str(table_name or '').strip().upper()}).mappings().all()
            visible_map = {
                str(row.get('NMCAMPO') or '').strip().upper(): bool(int(row.get('VISIVEL') or 0) == 1)
                for row in visible_rows
            }
        if _column_exists(table_name='CAMPOS', column_name='DECIMAIS') or _column_exists(table_name='CAMPOS', column_name='MINIMO') or _column_exists(table_name='CAMPOS', column_name='MAXIMO'):
            numeric_rows = db.session.execute(text("""
                SELECT
                    UPPER(LTRIM(RTRIM(ISNULL(NMCAMPO, '')))) AS NMCAMPO,
                    ISNULL(DECIMAIS, 0) AS DECIMAIS,
                    MINIMO AS MINIMO,
                    MAXIMO AS MAXIMO
                FROM dbo.CAMPOS
                WHERE UPPER(LTRIM(RTRIM(ISNULL(TABELA, '')))) = :table_name
            """), {'table_name': str(table_name or '').strip().upper()}).mappings().all()
            numeric_meta_map = {
                str(row.get('NMCAMPO') or '').strip().upper(): {
                    'decimais': int(row.get('DECIMAIS') or 0),
                    'minimo': None if row.get('MINIMO') is None else str(row.get('MINIMO')).strip(),
                    'maximo': None if row.get('MAXIMO') is None else str(row.get('MAXIMO')).strip(),
                }
                for row in numeric_rows
            }
        if _column_exists(table_name='CAMPOS', column_name='ORDEM_LISTA') or _column_exists(table_name='CAMPOS', column_name='TAM_LISTA'):
            list_order_select = "ISNULL(ORDEM_LISTA, CASE WHEN ISNULL(LISTA, 0) = 1 THEN ISNULL(ORDEM, 0) ELSE 0 END) AS ORDEM_LISTA" if _column_exists(table_name='CAMPOS', column_name='ORDEM_LISTA') else "CASE WHEN ISNULL(LISTA, 0) = 1 THEN ISNULL(ORDEM, 0) ELSE 0 END AS ORDEM_LISTA"
            list_width_select = "ISNULL(TAM_LISTA, ISNULL(TAM, 5)) AS TAM_LISTA" if _column_exists(table_name='CAMPOS', column_name='TAM_LISTA') else "ISNULL(TAM, 5) AS TAM_LISTA"
            list_mobile_order_select = "ISNULL(ORDEM_LISTA_MOBILE, 0) AS ORDEM_LISTA_MOBILE" if _column_exists(table_name='CAMPOS', column_name='ORDEM_LISTA_MOBILE') else "CAST(0 AS int) AS ORDEM_LISTA_MOBILE"
            list_mobile_width_select = "ISNULL(TAM_LISTA_MOBILE, ISNULL(TAM_MOBILE, ISNULL(TAM, 5))) AS TAM_LISTA_MOBILE" if _column_exists(table_name='CAMPOS', column_name='TAM_LISTA_MOBILE') else "ISNULL(TAM_MOBILE, ISNULL(TAM, 5)) AS TAM_LISTA_MOBILE"
            list_mobile_bold_select = "ISNULL(LISTA_MOBILE_BOLD, 0) AS LISTA_MOBILE_BOLD" if _column_exists(table_name='CAMPOS', column_name='LISTA_MOBILE_BOLD') else "CAST(0 AS bit) AS LISTA_MOBILE_BOLD"
            list_mobile_italic_select = "ISNULL(LISTA_MOBILE_ITALIC, 0) AS LISTA_MOBILE_ITALIC" if _column_exists(table_name='CAMPOS', column_name='LISTA_MOBILE_ITALIC') else "CAST(0 AS bit) AS LISTA_MOBILE_ITALIC"
            list_mobile_show_label_select = "ISNULL(LISTA_MOBILE_SHOW_LABEL, 1) AS LISTA_MOBILE_SHOW_LABEL" if _column_exists(table_name='CAMPOS', column_name='LISTA_MOBILE_SHOW_LABEL') else "CAST(1 AS bit) AS LISTA_MOBILE_SHOW_LABEL"
            list_mobile_label_select = "LTRIM(RTRIM(ISNULL(LISTA_MOBILE_LABEL, ''))) AS LISTA_MOBILE_LABEL" if _column_exists(table_name='CAMPOS', column_name='LISTA_MOBILE_LABEL') else "LTRIM(RTRIM(ISNULL(DESCRICAO, ''))) AS LISTA_MOBILE_LABEL"
            list_rows = db.session.execute(text("""
                SELECT
                    UPPER(LTRIM(RTRIM(ISNULL(NMCAMPO, '')))) AS NMCAMPO,
                    """ + list_order_select + """,
                    """ + list_width_select + """,
                    """ + list_mobile_order_select + """,
                    """ + list_mobile_width_select + """,
                    """ + list_mobile_bold_select + """,
                    """ + list_mobile_italic_select + """,
                    """ + list_mobile_show_label_select + """,
                    """ + list_mobile_label_select + """
                FROM dbo.CAMPOS
                WHERE UPPER(LTRIM(RTRIM(ISNULL(TABELA, '')))) = :table_name
            """), {'table_name': str(table_name or '').strip().upper()}).mappings().all()
            list_layout_map = {
                str(row.get('NMCAMPO') or '').strip().upper(): {
                    'ordem_lista': int(row.get('ORDEM_LISTA') or 0),
                    'tam_lista': int(row.get('TAM_LISTA') or 5),
                    'ordem_lista_mobile': int(row.get('ORDEM_LISTA_MOBILE') or 0),
                    'tam_lista_mobile': int(row.get('TAM_LISTA_MOBILE') or 5),
                    'lista_mobile_bold': bool(row.get('LISTA_MOBILE_BOLD')),
                    'lista_mobile_italic': bool(row.get('LISTA_MOBILE_ITALIC')),
                    'lista_mobile_show_label': bool(row.get('LISTA_MOBILE_SHOW_LABEL') if row.get('LISTA_MOBILE_SHOW_LABEL') is not None else 1),
                    'lista_mobile_label': str(row.get('LISTA_MOBILE_LABEL') or '').strip(),
                }
                for row in list_rows
            }
        if _column_exists(table_name='CAMPOS', column_name='PROPRIEDADES'):
            properties_rows = db.session.execute(text("""
                SELECT
                    UPPER(LTRIM(RTRIM(ISNULL(NMCAMPO, '')))) AS NMCAMPO,
                    ISNULL(PROPRIEDADES, '{}') AS PROPRIEDADES
                FROM dbo.CAMPOS
                WHERE UPPER(LTRIM(RTRIM(ISNULL(TABELA, '')))) = :table_name
            """), {'table_name': str(table_name or '').strip().upper()}).mappings().all()
            properties_map = {
                str(row.get('NMCAMPO') or '').strip().upper(): _parse_lookup_props(row.get('PROPRIEDADES'))
                for row in properties_rows
            }
        pk_name = f"{table_name.upper()}STAMP"
        cols = []
        for c in campos:
            col_ref = column_meta.get(c.nmcampo.upper())
            col_type = getattr(col_ref, 'type', None) if col_ref is not None else None
            precision = getattr(col_type, 'precision', None) if col_type is not None else None
            scale = getattr(col_type, 'scale', None) if col_type is not None else None
            numeric_meta = numeric_meta_map.get(c.nmcampo.upper(), {})
            list_layout = list_layout_map.get(c.nmcampo.upper(), {})
            translated_description = _translated_campo_label(c, c.descricao)
            raw_list_mobile_label = str(list_layout.get('lista_mobile_label', c.descricao or c.nmcampo) or '').strip()
            if not raw_list_mobile_label or raw_list_mobile_label == str(c.descricao or c.nmcampo or '').strip():
                list_mobile_label = str(translated_description or c.nmcampo or '').strip()
            else:
                list_mobile_label = raw_list_mobile_label
            cols.append({
                'name':             c.nmcampo,
                'descricao':        translated_description,
                'tipo':             c.tipo,
                'lista':            bool(c.lista),
                'filtro':           bool(c.filtro) if c.tipo != 'VIRTUAL' else False,
                'filtrodefault':    (c.filtrodefault or '').strip() if bool(c.filtro) and c.tipo != 'VIRTUAL' else '',
                'admin':            bool(c.admin),
                'primary_key':      (c.nmcampo == pk_name),
                'readonly':         True if c.tipo == 'VIRTUAL' else bool(c.ronly),
                'combo':            c.combo,
                'virtual':          c.virtual if c.tipo == 'VIRTUAL' else None,
                'ordem':            c.ordem,
                'tam':              c.tam,
                'ordem_lista':      list_layout.get('ordem_lista', c.ordem if bool(c.lista) else 0),
                'tam_lista':        list_layout.get('tam_lista', c.tam),
                'ordem_lista_mobile': list_layout.get('ordem_lista_mobile', 0),
                'tam_lista_mobile': list_layout.get('tam_lista_mobile', c.tam_mobile if getattr(c, 'tam_mobile', None) else c.tam),
                'lista_mobile_bold': bool(list_layout.get('lista_mobile_bold', False)),
                'lista_mobile_italic': bool(list_layout.get('lista_mobile_italic', False)),
                'lista_mobile_show_label': bool(list_layout.get('lista_mobile_show_label', True)),
                'lista_mobile_label': list_mobile_label,
                'ordem_mobile':     c.ordem_mobile,
                'tam_mobile':       c.tam_mobile,
                'condicao_visivel': c.condicao_visivel,
                'visivel':          visible_map.get(c.nmcampo.upper(), True),
                'obrigatorio':      c.obrigatorio,
                'precisao':         precision,
                'decimais':         numeric_meta.get('decimais') if 'decimais' in numeric_meta else scale,
                'minimo':           numeric_meta.get('minimo'),
                'maximo':           numeric_meta.get('maximo'),
                'propriedades':     properties_map.get(c.nmcampo.upper(), {}),
            })
        cols.extend(_load_menu_objects_for_menu(menu_stamp))
        if include_screen_meta:
            return jsonify({
                'columns': cols,
                'screen': {
                    'menustamp': menu_stamp,
                    'events': _load_menu_screen_events(menu_stamp),
                    'list_use_exact_widths': _menu_uses_list_exact_widths(menu_stamp=menu_stamp, table_name=table_name),
                },
            })
        return jsonify(cols)


    # 2) LISTAGEM
    if not has_permission(table_name, 'consultar'):
        abort(403, 'Sem permissÃ£o para consultar')

    table = get_table(table_name)
    stmt  = select(table)
    stmt  = _apply_feid_scope_stmt(stmt, table, table_name, mode='read')
    campos_filtro = Campo.query.filter_by(tabela=table_name, filtro=True).all()

    def resolve_default_token(raw_value: str):
        token = (raw_value or '').strip()
        if not token:
            return ''
        lower = token.lower()
        today = date.today()
        if lower == 'today':
            return today.isoformat()
        if lower == 'month_start':
            return today.replace(day=1).isoformat()
        if lower == 'month_end':
            next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
            return (next_month - timedelta(days=1)).isoformat()
        if lower == 'year_start':
            return today.replace(month=1, day=1).isoformat()
        if lower == 'year_end':
            return today.replace(month=12, day=31).isoformat()
        match = re.fullmatch(r'today\s*([+-])\s*(\d+)', lower)
        if match:
            delta = int(match.group(2))
            if match.group(1) == '-':
                delta *= -1
            return (today + timedelta(days=delta)).isoformat()
        return token

    def apply_default_filters(base_stmt):
        stmt_local = base_stmt
        for campo in campos_filtro:
            default_raw = (campo.filtrodefault or '').strip()
            if not default_raw:
                continue

            field_name = (campo.nmcampo or '').strip()
            if not field_name or not hasattr(table.c, field_name):
                continue
            col = getattr(table.c, field_name)

            if campo.tipo == 'DATE':
                if (
                    f'{field_name}_from' in request.args or
                    f'{field_name}_to' in request.args or
                    f'__clear_default__{field_name}_from' in request.args or
                    f'__clear_default__{field_name}_to' in request.args
                ):
                    continue
                start_raw, end_raw = (default_raw.split('|', 1) + [''])[:2] if '|' in default_raw else (default_raw, '')
                start_val = resolve_default_token(start_raw)
                end_val = resolve_default_token(end_raw)
                if start_val:
                    stmt_local = stmt_local.where(col >= start_val)
                if end_val:
                    stmt_local = stmt_local.where(col <= end_val)
                continue

            if field_name in request.args or f'__clear_default__{field_name}' in request.args:
                continue

            match = re.match(r'^(>=|<=|=|>|<|like)\s*:(.*)$', default_raw, re.IGNORECASE)
            explicit_operator = bool(match)
            operator = match.group(1).lower() if match else '='
            value = resolve_default_token(match.group(2) if match else default_raw)
            if value == '':
                continue

            if operator == 'like':
                stmt_local = stmt_local.where(col.like(f"%{value}%"))
            elif operator == '>':
                stmt_local = stmt_local.where(col > value)
            elif operator == '<':
                stmt_local = stmt_local.where(col < value)
            elif operator == '>=':
                stmt_local = stmt_local.where(col >= value)
            elif operator == '<=':
                stmt_local = stmt_local.where(col <= value)
            else:
                if not explicit_operator and isinstance(col.type, String):
                    stmt_local = stmt_local.where(col.like(f"%{value}%"))
                else:
                    stmt_local = stmt_local.where(col == value)
        return stmt_local

    stmt = apply_default_filters(stmt)

    # 3) FILTROS via query string
    for key, value in request.args.items():
        if key == 'action' or key.startswith('__clear_default__'):
            continue

        # intervalo de datas: campo_from e campo_to
        if key.endswith('_from'):
            col_name = key[:-5]
            if hasattr(table.c, col_name):
                stmt = stmt.where(getattr(table.c, col_name) >= value)
            continue

        if key.endswith('_to'):
            col_name = key[:-3]
            if hasattr(table.c, col_name):
                stmt = stmt.where(getattr(table.c, col_name) <= value)
            continue

        # filtros normais
        if hasattr(table.c, key):
            col = getattr(table.c, key)
            # texto: contÃ©m via LIKE
            if isinstance(col.type, String):
                stmt = stmt.where(col.like(f"%{value}%"))
            else:
                stmt = stmt.where(col == value)

    menu_item = Menu.query.filter_by(tabela=table_name).first()
    menu_orderby = ((getattr(menu_item, 'orderby', '') or '').strip() if menu_item else '')

    def apply_default_order(base_stmt):
        order_cols = []
        for cn in ('ORDEM', 'DATA', 'HORA', 'NOME'):
            if hasattr(table.c, cn):
                order_cols.append(getattr(table.c, cn))
        return base_stmt.order_by(*order_cols) if order_cols else base_stmt

    if menu_orderby:
        stmt = stmt.order_by(text(menu_orderby))
    else:
        stmt = apply_default_order(stmt)

    # 5) executa e retorna JSON
    try:
        try:
            rows = db.session.execute(stmt).fetchall()
        except Exception:
            if not menu_orderby:
                raise
            current_app.logger.exception(
                "Falha ao aplicar MENU.ORDERBY em %s: %s",
                table_name,
                menu_orderby
            )
            rows = db.session.execute(apply_default_order(stmt.order_by(None))).fetchall()
        records = [dict(r._mapping) for r in rows]
        # 1. Recolhe os campos VIRTUAL para esta tabela
        virtual_fields = (
            Campo.query
                .filter_by(tabela=table_name, tipo='VIRTUAL')
                .all()
        )

        # 2. Identifica o nome do PK
        pk_name = f"{table_name.upper()}STAMP"

        # 3. Para cada campo virtual e registo, executa a subquery
        for campo in virtual_fields:
            sql = text(campo.virtual)  # exemplo: SELECT TOP 1 VALOR ... WHERE CLIENTE = :pk
            for rec in records:
                pk_value = rec.get(pk_name)
                if not pk_value:
                    continue
                try:
                    val = db.session.execute(sql, {'pk': pk_value}).scalar()
                except Exception as e:
                    val = None  # ou logar erro
                rec[campo.nmcampo] = val
        return jsonify(records)
    except Exception as e:
        current_app.logger.exception(f"Falha ao listar {table_name}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/<table_name>/next_no', methods=['GET'])
@login_required
def partner_next_no(table_name):
    tn = (table_name or '').strip().upper()
    if not _is_partner_table(tn):
        abort(404)
    if not has_permission(tn, 'inserir'):
        abort(403, 'Sem permissão para inserir')
    current_feid = _current_feid_or_abort() if _table_is_fe_scoped(tn) else None
    return jsonify({'NO': _next_incremental_no(tn, current_feid)})


@bp.route('/api/<table_name>/vies_lookup', methods=['GET'])
@login_required
def partner_vies_lookup(table_name):
    tn = (table_name or '').strip().upper()
    if not _is_partner_table(tn):
        abort(404)
    if not (has_permission(tn, 'consultar') or has_permission(tn, 'editar') or has_permission(tn, 'inserir')):
        abort(403, 'Sem permissão')

    nif = (request.args.get('nif') or '').strip()
    if not nif:
        return jsonify({'ok': False, 'error': 'NIF em falta.'}), 400

    try:
        result = _fetch_vies_info(nif)
    except ValueError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 502
    except Exception as exc:
        current_app.logger.exception('Erro inesperado ao consultar VIES')
        return jsonify({'ok': False, 'error': 'Não foi possível consultar o VIES.'}), 500

    payload = {
        'ok': True,
        'valid': bool(result.get('valid')),
        'country_code': result.get('country_code') or '',
        'vat_number': result.get('vat_number') or '',
        'name': result.get('name') or '',
        'address': result.get('address') or '',
        'nome': result.get('name') or '',
        'morada': result.get('morada') or '',
        'codpost': result.get('codpost') or '',
        'local': result.get('local') or '',
        'message': 'Dados obtidos do VIES.' if result.get('valid') else 'O NIF indicado não está válido no VIES.',
    }
    return jsonify(payload)

# --------------------------------------------------
# API: opÃ§Ãµes para COMBO
# --------------------------------------------------
@bp.route('/api/options', methods=['GET'])
@login_required
def combo_options():
    q = request.args.get('query')
    try:
        rows = db.session.execute(text(q)).fetchall()
    except Exception as e:
        current_app.logger.exception("Erro em combo_options")
        return jsonify({'error': str(e)}), 500

    results = []
    for r in rows:
        if len(r) == 1:
            results.append({'value': r[0], 'text': str(r[0])})
        else:
            results.append({'value': r[0], 'text': r[1]})
    return jsonify(results)


@bp.route('/api/menu_object_lookup', methods=['POST'])
@login_required
def menu_object_lookup():
    try:
        payload = request.get_json(silent=True) or {}
        menustamp = str(payload.get('menustamp') or '').strip()
        object_name = str(payload.get('object_name') or '').strip()
        q = str(payload.get('q') or '').strip()
        exact_mode = str(payload.get('mode') or '').strip().lower() in {'value', 'exact'}
        if 'exact_value' in payload or 'value' in payload:
            exact_mode = True
        exact_value = payload.get('exact_value') if 'exact_value' in payload else payload.get('value')
        exact_value = '' if exact_value is None else str(exact_value).strip()
        if not menustamp or not object_name:
            return jsonify({'success': False, 'error': 'Objeto de pesquisa em falta.'}), 400

        payload_config = payload.get('config') if isinstance(payload.get('config'), dict) else {}
        requested_target_field = str(
            payload_config.get('lookup_target_field')
            or payload_config.get('target_field')
            or payload_config.get('field_name')
            or ''
        ).strip()
        props = _load_lookup_object_props(
            menustamp,
            object_name,
            payload.get('table_name'),
            requested_target_field,
        )
        if not props:
            return jsonify({'success': False, 'error': 'Objeto de pesquisa nao encontrado.'}), 404

        lookup_table = _lookup_prop(props, 'lookup_table', 'table', 'source')
        display_fields_raw = _lookup_prop(props, 'lookup_display_fields', 'display_fields')
        value_field_raw = _lookup_prop(props, 'lookup_value_field', 'value_field', 'source_field')
        target_field = _lookup_prop(props, 'lookup_target_field', 'target_field', 'field_name')
        filter_expr = _lookup_prop(props, 'lookup_filter', 'filter', 'where')
        if not lookup_table:
            return jsonify({'success': False, 'error': 'Tabela de pesquisa em falta.'}), 400
        if not value_field_raw:
            return jsonify({'success': False, 'error': 'Campo valor em falta.'}), 400
        if not q and not (exact_mode and exact_value):
            return jsonify({'success': True, 'rows': [], 'target_field': target_field})

        schema_name, physical_table = _resolve_table_identifier(lookup_table)
        if not physical_table:
            return jsonify({'success': False, 'error': 'Tabela de pesquisa invalida.'}), 400
        screen_table = str(payload.get('table_name') or '').strip()
        has_screen_access = bool(screen_table) and (
            has_permission(screen_table, 'consultar')
            or has_permission(screen_table, 'editar')
            or has_permission(screen_table, 'inserir')
        )
        if not (
            getattr(current_user, 'ADMIN', False)
            or has_permission(physical_table, 'consultar')
            or has_permission(lookup_table, 'consultar')
            or has_screen_access
        ):
            return jsonify({'success': False, 'error': 'Sem permissao para consultar a tabela de pesquisa.'}), 403

        table = get_table(f'{schema_name}.{physical_table}')
        column_map = {
            str(column.name or '').strip().upper(): str(column.name or '').strip()
            for column in table.columns
            if str(column.name or '').strip()
        }
        value_field = _resolve_lookup_column(column_map, value_field_raw, 'Campo valor')
        display_requests = _split_lookup_fields(display_fields_raw)
        if not display_requests:
            display_requests = [value_field]
        display_columns = []
        seen_display = set()
        for requested in display_requests:
            column_name = _resolve_lookup_column(column_map, requested, 'Campo visivel')
            key = column_name.upper()
            if key not in seen_display:
                seen_display.add(key)
                display_columns.append(column_name)

        search_columns = []
        seen_search = set()
        for column_name in [*display_columns, value_field]:
            key = column_name.upper()
            if key not in seen_search:
                seen_search.add(key)
                search_columns.append(column_name)

        form_state = payload.get('form_state') if isinstance(payload.get('form_state'), dict) else {}
        lookup_state = dict(form_state)
        lookup_state.update({
            'TABLE_NAME': str(payload.get('table_name') or '').strip(),
            'RECORD_STAMP': str(payload.get('record_stamp') or '').strip(),
            'MENU_STAMP': menustamp,
            'CURRENT_USER': getattr(current_user, 'LOGIN', '') or '',
            'USER': getattr(current_user, 'LOGIN', '') or '',
        })
        try:
            lookup_state['FEID'] = get_current_feid()
        except MissingCurrentEntityError:
            lookup_state['FEID'] = None

        alias = 'LKP'
        table_ref = f'{_quote_sql_identifier(schema_name)}.{_quote_sql_identifier(physical_table)}'
        select_parts = [f'{alias}.{_quote_sql_identifier(value_field)} AS [__value]']
        for column_name in display_columns:
            select_parts.append(f'{alias}.{_quote_sql_identifier(column_name)} AS {_quote_sql_identifier(column_name)}')

        if exact_mode:
            params = {'lookup_value': exact_value}
            where_parts = [
                f"LTRIM(RTRIM(CONVERT(NVARCHAR(4000), {alias}.{_quote_sql_identifier(value_field)}))) = :lookup_value"
            ]
            top_count = 1
        else:
            params = {'lookup_q': f'%{q.upper()}%'}
            search_sql = ' OR '.join(
                f'UPPER(CONVERT(NVARCHAR(4000), {alias}.{_quote_sql_identifier(column_name)})) LIKE :lookup_q'
                for column_name in search_columns
            )
            where_parts = [f'({search_sql})']
            top_count = 25
        filter_sql, filter_params = _prepare_lookup_filter(filter_expr, lookup_state)
        if filter_sql:
            where_parts.append(f'({filter_sql})')
            params.update(filter_params)

        sql = f"""
            SELECT TOP {top_count}
                {', '.join(select_parts)}
            FROM {table_ref} {alias}
            WHERE {' AND '.join(where_parts)}
        """
        scope_table_name = physical_table if schema_name.lower() == 'dbo' else f'{schema_name}.{physical_table}'
        if _table_is_fe_scoped(scope_table_name):
            params['lookup_feid'] = _current_feid_or_abort()
            sql += _sql_feid_clause(scope_table_name, alias=alias, param_name='lookup_feid', mode='read')
        sql += f' ORDER BY {alias}.{_quote_sql_identifier(display_columns[0] if display_columns else value_field)}'

        result_rows = db.session.execute(text(sql), params).mappings().all()
        rows = []
        for row in result_rows:
            raw_value = row.get('__value')
            display_values = [_event_cursor_json_value(row.get(column_name)) for column_name in display_columns]
            label_parts = [
                str(value).strip()
                for value in display_values
                if value is not None and str(value).strip()
            ]
            label = ' · '.join(label_parts) or ('' if raw_value is None else str(raw_value).strip())
            row_payload = {value_field: _event_cursor_json_value(raw_value)}
            for column_name in display_columns:
                row_payload[column_name] = _event_cursor_json_value(row.get(column_name))
            rows.append({
                'value': _event_cursor_json_value(raw_value),
                'label': label,
                'display': display_values,
                'row': row_payload,
            })

        return jsonify({
            'success': True,
            'rows': rows,
            'target_field': target_field,
        })
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        if hasattr(exc, 'code') and hasattr(exc, 'description'):
            raise
        current_app.logger.exception('Erro na pesquisa incremental de objeto de menu.')
        return jsonify({'success': False, 'error': str(exc)}), 500

# --------------------------------------------------
# API: marcar MN como tratada
# --------------------------------------------------
@bp.route('/api/mn/tratar', methods=['POST'])
@login_required
def mn_tratar():
    data = request.get_json(silent=True) or {}
    mnstamp = data.get('MNSTAMP') or data.get('mnstamp')
    if not mnstamp:
        return jsonify({'ok': False, 'error': 'MNSTAMP em falta'}), 400

    # PermissÃ£o: MN admin ou permissÃ£o de editar tabela MN (se existir ACL)
    allowed = getattr(current_user, 'MNADMIN', False) or has_permission('MN', 'editar')
    if not allowed:
        return jsonify({'ok': False, 'error': 'Sem permissÃ£o'}), 403

    try:
        params = {'user': current_user.LOGIN, 'stamp': mnstamp}
        sql = text(f"""
            UPDATE MN
            SET TRATADO = 1,
                NMTRATADO = :user,
                DTTRATADO = CAST(GETDATE() AS date)
            WHERE MNSTAMP = :stamp
            {_sql_feid_clause('MN')}
        """)
        if _table_is_fe_scoped('MN'):
            params['current_feid'] = _current_feid_or_abort()
        db.session.execute(sql, params)
        db.session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Erro ao marcar MN como tratada')
        return jsonify({'ok': False, 'error': str(e)}), 500


# --------------------------------------------------
# API: criar tarefa manual (Nota Tarefa)
# --------------------------------------------------
@bp.route('/api/tarefas/nova', methods=['POST'])
@login_required
def api_tarefa_nova():
    data = request.get_json(silent=True) or {}
    utilizador = (data.get('UTILIZADOR') or current_user.LOGIN or '').strip()
    data_str   = (data.get('DATA') or '').strip()      # YYYY-MM-DD
    hora_str   = (data.get('HORA') or '').strip()      # HH:MM
    tarefa     = (data.get('TAREFA') or '').strip()
    duracao    = int(data.get('DURACAO') or 60)
    aloj       = (data.get('ALOJAMENTO') or '').strip()

    if not tarefa:
        return jsonify({'ok': False, 'error': 'TAREFA obrigatória'}), 400
    if not data_str or not hora_str or duracao <= 0:
        return jsonify({'ok': False, 'error': 'Verifica DATA, HORA e DURACAO'}), 400

    # Opcional: validação de permissões para inserir em TAREFAS
    if not has_permission('TAREFAS', 'inserir') and not getattr(current_user, 'ADMIN', False):
        return jsonify({'ok': False, 'error': 'Sem permissão para criar tarefas'}), 403

    tarefastamp = uuid.uuid4().hex[:25].upper()
    try:
        scoped = _table_is_fe_scoped('TAREFAS')
        sql = text(f"""
            INSERT INTO TAREFAS (
              TAREFASSTAMP, UTILIZADOR, DATA, HORA, DURACAO,
              TAREFA, ALOJAMENTO, ORIGEM, ORISTAMP, TRATADO, DTTRATADO, NMTRATADO
              {', FEID' if scoped else ''}
            ) VALUES (
              :id, :util, :data, :hora, :dur,
              :tarefa, :aloj, '', '', 0, CAST('1900-01-01' AS date), ''
              {', :feid' if scoped else ''}
            )
        """)
        params = {
            'id': tarefastamp,
            'util': utilizador,
            'data': data_str,
            'hora': hora_str,
            'dur': duracao,
            'tarefa': tarefa,
            'aloj': aloj
        }
        if scoped:
            params['feid'] = MONITOR_DEFAULT_FEID
        db.session.execute(sql, params)
        db.session.commit()
        return jsonify({'ok': True, 'TAREFASSTAMP': tarefastamp})
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Erro ao criar tarefa manual')
        return jsonify({'ok': False, 'error': str(e)}), 500

# --------------------------------------------------
# API: criar registo Luggage Storage (LS)
# --------------------------------------------------
@bp.route('/api/ls_novo', methods=['POST'])
@login_required
def api_ls_novo():
    try:
        is_admin = bool(getattr(current_user, 'ADMIN', False))
        is_ls_admin = bool(getattr(current_user, 'LSADMIN', False))
    except Exception:
        is_admin = False
        is_ls_admin = False

    if not (is_admin or is_ls_admin):
        return jsonify({'ok': False, 'error': 'Sem permissão'}), 403

    data = request.get_json(silent=True) or {}

    try:
        util = (current_user.LOGIN or '').strip()
    except Exception:
        util = ''

    DATA = (data.get('DATA') or '').strip()
    HORA = (data.get('HORA') or '').strip()[:5]
    QTT  = int(data.get('QTT') or 0)
    TAG1 = int(data.get('TAG1') or 0)
    TAG2 = int(data.get('TAG2') or 0)
    TAG3 = int(data.get('TAG3') or 0)
    TAG4 = int(data.get('TAG4') or 0)
    TAG5 = int(data.get('TAG5') or 0)
    HOSPEDE = 1 if (data.get('HOSPEDE') in (True, 1, '1', 'true', 'True')) else 0
    NOME  = (data.get('NOME')  or '').strip()
    EMAIL = (data.get('EMAIL') or '').strip()
    NIF   = (data.get('NIF')   or '').strip()
    VALOR = float(data.get('VALOR') or (QTT * 4))

    if not (DATA and HORA and QTT > 0 and TAG1 > 0 and util):
        return jsonify({'ok': False, 'error': 'Dados obrigatórios em falta'}), 400

    if HOSPEDE == 1:
        NOME = ''
        EMAIL = ''
        NIF = ''

    try:
        sql = text("""
            INSERT INTO LS (
              UTILIZADOR, DATA, HORA, QTT,
              TAG1, TAG2, TAG3, TAG4, TAG5,
              VALOR, HOSPEDE, NOME, EMAIL, NIF
            ) VALUES (
              :UTILIZADOR, :DATA, :HORA, :QTT,
              :TAG1, :TAG2, :TAG3, :TAG4, :TAG5,
              :VALOR, :HOSPEDE, :NOME, :EMAIL, :NIF
            )
        """)
        db.session.execute(sql, {
            'UTILIZADOR': util,
            'DATA': DATA,
            'HORA': HORA,
            'QTT': QTT,
            'TAG1': TAG1,
            'TAG2': TAG2,
            'TAG3': TAG3,
            'TAG4': TAG4,
            'TAG5': TAG5,
            'VALOR': VALOR,
            'HOSPEDE': HOSPEDE,
            'NOME': NOME,
            'EMAIL': EMAIL,
            'NIF': NIF
        })
        db.session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Erro ao criar Luggage Storage (LS)')
        return jsonify({'ok': False, 'error': str(e)}), 500

# --------------------------------------------------
# API: tarefas do monitor com filtro por utilizador/origem
# --------------------------------------------------
@bp.route('/api/monitor_tasks_filtered', methods=['GET'])
@login_required
def monitor_tasks_filtered():
    only_mine = request.args.get('only_mine', '1') in ('1', 'true', 'True')
    current_feid = _current_feid_or_abort() if _table_is_fe_scoped('TAREFAS') else None

    is_mn_admin = bool(getattr(current_user, 'MNADMIN', False))
    is_lp_admin = bool(getattr(current_user, 'LPADMIN', False))

    where = []
    params = {'user': current_user.LOGIN}
    if current_feid is not None:
        params['current_feid'] = current_feid

    if only_mine:
        # LPADMIN: ver sempre FS, mesmo quando only_mine=1
        if is_lp_admin:
            where.append("(UTILIZADOR = :user OR UPPER(ISNULL(ORIGEM,'')) = 'FS')")
        else:
            where.append("UTILIZADOR = :user")
    else:
        origins = []
        if is_mn_admin:
            origins.append("'MN'")
        if is_lp_admin:
            origins.extend(["'LP'", "'FS'"])
        if origins:
            # Incluir tarefas sem origem (NULL/''), além das de origem permitida
            where.append(f"(ORIGEM IN ({', '.join(origins)}) OR ORIGEM IS NULL OR LTRIM(RTRIM(ORIGEM)) = '')")
        else:
            # fallback para apenas as do prÃ³prio
            where.append("UTILIZADOR = :user")

    # Regras de data: todas as atrasadas, e tratadas apenas Ãºltimos 7 dias
    # Implementamos como (TRATADO=0) OR (TRATADO=1 AND DATA >= hoje-7)
    where.append("(TRATADO = 0 OR DATA >= DATEADD(day, -7, CAST(GETDATE() AS date)))")

    where_sql = (" WHERE " + " AND ".join(where)) if where else ""

    sql = text(f"""
        SELECT 
            T.TAREFASSTAMP,
            CONVERT(varchar(10), T.DATA, 23)       AS DATA,        -- YYYY-MM-DD
            LEFT(CONVERT(varchar(8), T.HORA, 108), 5) AS HORA,     -- HH:MM
            T.TAREFA,
            T.ALOJAMENTO,
            T.TRATADO,
            CONVERT(varchar(10), T.DTTRATADO, 23)  AS DTTRATADO,
            T.ORIGEM,
            T.UTILIZADOR,
            U.NOME AS UTILIZADOR_NOME,
            U.COR  AS UTILIZADOR_COR
        FROM TAREFAS T
        LEFT JOIN US U ON U.LOGIN = T.UTILIZADOR
        {where_sql}
        {_sql_feid_clause('TAREFAS', 'T')}
        ORDER BY 
          T.DATA,
          CASE WHEN UPPER(T.UTILIZADOR) = UPPER(:user) THEN 0 ELSE 1 END,
          T.HORA
    """)
    try:
        rows = db.session.execute(sql, params).fetchall()
        base_rows = [dict(r._mapping) for r in rows]

        # Regra urgente: Se o utilizador tiver LP num alojamento num dia,
        # incluir MN/FS desse alojamento/dia (mesmo de outros utilizadores),
        # sem necessidade de aplicar filtros.
        # Implementação: só ativa quando only_mine=True (caso típico do utilizador comum).
        # Regra urgente ativa sempre: com base nas LP do utilizador atual,
        # incluir MN/FS do mesmo alojamento/dia, independentemente de filtros.
        if True:
            try:
                # Pairs (DATA, ALOJAMENTO) de LP do utilizador na mesma janela lógica
                lp_sql = text(
                    """
                    SELECT CONVERT(varchar(10), DATA, 23) AS DATA,
                           ISNULL(ALOJAMENTO,'')           AS ALOJAMENTO
                    FROM TAREFAS
                    WHERE UPPER(ISNULL(ORIGEM,'')) = 'LP'
                      AND UPPER(UTILIZADOR) = UPPER(:u)
                      AND (TRATADO = 0 OR DATA >= DATEADD(day, -7, CAST(GETDATE() AS date)))
                      {_sql_feid_clause('TAREFAS')}
                    """
                )
                lp_params = {'u': current_user.LOGIN}
                if current_feid is not None:
                    lp_params['current_feid'] = current_feid
                lp_pairs = [(r.DATA, r.ALOJAMENTO) for r in db.session.execute(lp_sql, lp_params)]

                if lp_pairs:
                    # Construir WHERE por pares (DATA, ALOJAMENTO)
                    def build_pair_where(alias_data: str, alias_aloj: str, prefix: str):
                        conds = []
                        bind = {}
                        for idx, (d, a) in enumerate(lp_pairs):
                            kd, ka = f"{prefix}d{idx}", f"{prefix}a{idx}"
                            bind[kd] = d
                            bind[ka] = a
                            conds.append(f"({alias_data} = :{kd} AND ISNULL({alias_aloj},'') = :{ka})")
                        return ("(" + " OR ".join(conds) + ")", bind) if conds else ("1=0", {})

                    extra = []

                    # TAREFAS extra (de outros utilizadores) para MN/FS que coincidam com (DATA, ALOJAMENTO)
                    try:
                        tf_where_pairs, tf_bind = build_pair_where('T.DATA', 'T.ALOJAMENTO', 't')
                        tf_sql = text(
                                f"""
                                SELECT 
                                  T.TAREFASSTAMP,
                                  CONVERT(varchar(10), T.DATA, 23)       AS DATA,
                                  LEFT(CONVERT(varchar(8), T.HORA, 108), 5) AS HORA,
                                  T.TAREFA,
                                  ISNULL(T.ALOJAMENTO,'')                 AS ALOJAMENTO,
                                  T.TRATADO,
                                  CONVERT(varchar(10), T.DTTRATADO, 23)   AS DTTRATADO,
                                  ISNULL(T.ORIGEM,'')                      AS ORIGEM,
                                  T.UTILIZADOR,
                                  U.NOME                                   AS UTILIZADOR_NOME,
                                  U.COR                                    AS UTILIZADOR_COR
                                FROM TAREFAS T
                                LEFT JOIN US U ON U.LOGIN = T.UTILIZADOR
                                WHERE {tf_where_pairs}
                                  AND (T.TRATADO = 0 OR T.DATA >= DATEADD(day, -7, CAST(GETDATE() AS date)))
                                  AND T.DATA >= CAST(GETDATE() AS date)
                                  AND UPPER(ISNULL(T.ORIGEM,'')) IN ('MN','FS')
                                  {_sql_feid_clause('TAREFAS', 'T')}
                                """
                            )
                        if current_feid is not None:
                            tf_bind['current_feid'] = current_feid
                        for r in db.session.execute(tf_sql, tf_bind).mappings().all():
                            extra.append(dict(r))
                    except Exception:
                        pass

                    # MN extra (não agendadas): usa INCIDENCIA, junta nome/cor do utilizador
                    try:
                        mn_where_pairs, mn_bind = build_pair_where('M.DATA', 'M.ALOJAMENTO', 'm')
                        mn_sql = text(
                            f"""
                            SELECT
                              CONVERT(varchar(10), M.DATA, 23)   AS DATA,
                              '00:00'                            AS HORA,
                              ISNULL(M.ALOJAMENTO,'')            AS ALOJAMENTO,
                              'MN'                               AS ORIGEM,
                              M.INCIDENCIA                       AS TAREFA,
                              ISNULL(M.TRATADO,0)                AS TRATADO,
                              CONVERT(varchar(10), M.DTTRATADO, 23) AS DTTRATADO,
                              ISNULL(M.NOME,'')                  AS UTILIZADOR,
                              U.NOME                             AS UTILIZADOR_NOME,
                              U.COR                              AS UTILIZADOR_COR
                            FROM MN M
                            LEFT JOIN US U ON U.LOGIN = M.NOME
                            WHERE {mn_where_pairs}
                              AND (ISNULL(M.TRATADO,0) = 0 OR M.DATA >= DATEADD(day, -7, CAST(GETDATE() AS date)))
                              AND M.DATA >= CAST(GETDATE() AS date)
                              AND M.MNSTAMP NOT IN (SELECT ORISTAMP FROM TAREFAS)
                              {_sql_feid_clause('MN', 'M')}
                            """
                        )
                        if _table_is_fe_scoped('MN'):
                            mn_bind['current_feid'] = _current_feid_or_abort()
                        for r in db.session.execute(mn_sql, mn_bind).mappings().all():
                            extra.append(dict(r))
                    except Exception:
                        pass

                    # FS extra (não agendadas): usa ITEM, junta nome/cor do utilizador
                    try:
                        fs_where_pairs, fs_bind = build_pair_where('F.DATA', 'F.ALOJAMENTO', 'f')
                        fs_sql = text(
                            f"""
                            SELECT
                              CONVERT(varchar(10), F.DATA, 23)   AS DATA,
                              '00:00'                            AS HORA,
                              ISNULL(F.ALOJAMENTO,'')            AS ALOJAMENTO,
                              'FS'                               AS ORIGEM,
                              F.ITEM                             AS TAREFA,
                              ISNULL(F.TRATADO,0)                AS TRATADO,
                              CONVERT(varchar(10), F.DTTRATADO, 23) AS DTTRATADO,
                              ISNULL(F.USERNAME,'')              AS UTILIZADOR,
                              U.NOME                             AS UTILIZADOR_NOME,
                              U.COR                              AS UTILIZADOR_COR
                            FROM FS F
                            LEFT JOIN US U ON U.LOGIN = F.USERNAME
                            WHERE {fs_where_pairs}
                              AND (ISNULL(F.TRATADO,0) = 0 OR F.DATA >= DATEADD(day, -7, CAST(GETDATE() AS date)))
                              AND F.DATA >= CAST(GETDATE() AS date)
                              AND F.FSSTAMP NOT IN (SELECT ORISTAMP FROM TAREFAS)
                              {_sql_feid_clause('FS', 'F')}
                            """
                        )
                        if _table_is_fe_scoped('FS'):
                            fs_bind['current_feid'] = _current_feid_or_abort()
                        for r in db.session.execute(fs_sql, fs_bind).mappings().all():
                            extra.append(dict(r))
                    except Exception:
                        pass

                    if extra:
                        # Evitar duplicados por chave lógica
                        seen = set(
                            f"{x.get('ORIGEM','')}|{x.get('DATA','')}|{x.get('HORA','')}|{x.get('ALOJAMENTO','')}|{x.get('TAREFA','')}|{x.get('UTILIZADOR','')}"
                            for x in base_rows
                        )
                        for r in extra:
                            k = f"{r.get('ORIGEM','')}|{r.get('DATA','')}|{r.get('HORA','')}|{r.get('ALOJAMENTO','')}|{r.get('TAREFA','')}|{r.get('UTILIZADOR','')}"
                            if k in seen:
                                continue
                            seen.add(k)
                            # garantir campos esperados
                            if not r.get('HORA'):
                                r['HORA'] = '00:00'
                            r.setdefault('TAREFASSTAMP', None)
                            base_rows.append(r)

            except Exception:
                # Não falhar o endpoint por causa da lógica extra
                pass

        # ordena por data/hora para consistência
        try:
            base_rows.sort(key=lambda x: (str(x.get('DATA') or ''), str(x.get('HORA') or '')))
        except Exception:
            pass

        return jsonify(base_rows)
    except Exception as e:
        current_app.logger.exception('Erro em monitor_tasks_filtered')
        return jsonify({'error': str(e)}), 500

# --------------------------------------------------
# API: tarefas do monitor filtradas por lista de utilizadores (multi)
# --------------------------------------------------
@bp.route('/api/monitor_tasks_by_users', methods=['GET'])
@login_required
def monitor_tasks_by_users():
    users_param = (request.args.get('users') or '').strip()
    origins_param = (request.args.get('origins') or '').strip()
    aloj_param = (request.args.get('aloj') or '').strip()
    current_feid = _current_feid_or_abort() if _table_is_fe_scoped('TAREFAS') else None
    if not users_param:
        # por defeito, devolve as do pr�prio utilizador
        users = [current_user.LOGIN]
    else:
        users = []
        seen = set()
        for u in [p.strip() for p in users_param.split(',') if p.strip()]:
            key = u.upper()
            if key not in seen:
                users.append(u)
                seen.add(key)
        if not users:
            return jsonify([])

    # constr�i IN din�mico
    params = {}
    if current_feid is not None:
        params['current_feid'] = current_feid
    placeholders = []
    for i, u in enumerate(users):
        pn = f'u{i}'
        params[pn] = u
        placeholders.append(f':{pn}')

    where = []
    where.append("UPPER(T.UTILIZADOR) IN (" + ", ".join(placeholders) + ")")

    # Filtro opcional por origem: tokens MN,LP,FS,__EMPTY__
    if origins_param:
        oris = []
        seen_o = set()
        include_empty = False
        for o in [p.strip() for p in origins_param.split(',') if p.strip()]:
            ou = o.upper()
            if ou == '__EMPTY__':
                include_empty = True
                continue
            if ou not in seen_o:
                seen_o.add(ou)
                oris.append(ou)
        ori_clause = []
        if oris:
            o_placeholders = []
            for i, ov in enumerate(oris):
                on = f'o{i}'
                params[on] = ov
                o_placeholders.append(f':{on}')
            ori_clause.append("UPPER(T.ORIGEM) IN (" + ", ".join(o_placeholders) + ")")
        if include_empty:
            ori_clause.append("(T.ORIGEM IS NULL OR LTRIM(RTRIM(T.ORIGEM)) = '')")
        if ori_clause:
            where.append("(" + " OR ".join(ori_clause) + ")")

    # Filtro opcional por alojamento: lista de nomes e token __EMPTY__
    if aloj_param:
        al_list = []
        seen_a = set()
        include_empty_al = False
        for a in [p.strip() for p in aloj_param.split(',') if p.strip()]:
            au = a.upper()
            if au == '__EMPTY__':
                include_empty_al = True
                continue
            if au not in seen_a:
                seen_a.add(au)
                al_list.append(a)
        al_clause = []
        if al_list:
            a_placeholders = []
            for i, av in enumerate(al_list):
                an = f'a{i}'
                params[an] = av
                a_placeholders.append(f':{an}')
            al_clause.append("UPPER(T.ALOJAMENTO) IN (" + ", ".join(a_placeholders) + ")")
        if include_empty_al:
            al_clause.append("(T.ALOJAMENTO IS NULL OR LTRIM(RTRIM(T.ALOJAMENTO)) = '')")
        if al_clause:
            where.append("(" + " OR ".join(al_clause) + ")")

    where.append("(T.TRATADO = 0 OR T.DATA >= DATEADD(day, -7, CAST(GETDATE() AS date)))")
    where_sql = " WHERE " + " AND ".join(where)

    params['me'] = current_user.LOGIN

    sql = text(f"""
        SELECT 
            T.TAREFASSTAMP,
            CONVERT(varchar(10), T.DATA, 23)         AS DATA,
            LEFT(CONVERT(varchar(8), T.HORA, 108), 5) AS HORA,
            T.TAREFA,
            T.ALOJAMENTO,
            T.TRATADO,
            T.ORIGEM,
            T.UTILIZADOR,
            U.NOME AS UTILIZADOR_NOME,
            U.COR  AS UTILIZADOR_COR
        FROM TAREFAS T
        LEFT JOIN US U ON U.LOGIN = T.UTILIZADOR
        {where_sql}
        {_sql_feid_clause('TAREFAS', 'T')}
        ORDER BY 
          T.DATA,
          CASE WHEN UPPER(T.UTILIZADOR) = UPPER(:me) THEN 0 ELSE 1 END,
          T.HORA
    """)
    try:
        rows = db.session.execute(sql, params).fetchall()
        return jsonify([dict(r._mapping) for r in rows])
    except Exception as e:
        current_app.logger.exception('Erro em monitor_tasks_by_users')
        return jsonify({'error': str(e)}), 500

# --------------------------------------------------
# API: Tarefas tratar/reabrir
# --------------------------------------------------
@bp.route('/api/tarefas/tratar', methods=['POST'])
@login_required
def tarefa_tratar():
    data = request.get_json(silent=True) or {}
    tid = data.get('id')
    if not tid:
        return jsonify({'ok': False, 'error': 'ID em falta'}), 400
    current_feid = _current_feid_or_abort() if _table_is_fe_scoped('TAREFAS') else None
    try:
        # Regra: utilizadores com registo de tempos não podem concluir limpezas via monitor
        try:
            is_tempos = int(getattr(current_user, 'TEMPOS', 0) or 0) == 1
            is_admin = bool(getattr(current_user, 'ADMIN', False) or getattr(current_user, 'LPADMIN', False))
        except Exception:
            is_tempos = False
            is_admin = False

        if is_tempos and not is_admin:
            origem = db.session.execute(text("""
                SELECT UPPER(LTRIM(RTRIM(ISNULL(ORIGEM,'')))) AS ORIGEM
                FROM TAREFAS
                WHERE TAREFASSTAMP = :id
                """ + _sql_feid_clause('TAREFAS')
            ), {'id': tid, **({'current_feid': current_feid} if current_feid is not None else {})}).scalar()
            if origem is None:
                return jsonify({'ok': False, 'error': 'Tarefa não encontrada'}), 404
            if str(origem).upper() == 'LP':
                return jsonify({'ok': False, 'error': 'A conclusão das limpezas deve ser feita no Registo de Limpezas.'}), 403

        sql = text(f"""
            UPDATE TAREFAS
            SET TRATADO = 1,
                NMTRATADO = :user,
                DTTRATADO = CAST(GETDATE() AS date)
            WHERE TAREFASSTAMP = :id
            {_sql_feid_clause('TAREFAS')}
        """)
        params = {'user': current_user.LOGIN, 'id': tid}
        if current_feid is not None:
            params['current_feid'] = current_feid
        db.session.execute(sql, params)
        db.session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Erro ao tratar tarefa')
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/api/tarefas/reabrir', methods=['POST'])
@login_required
def tarefa_reabrir():
    data = request.get_json(silent=True) or {}
    tid = data.get('id')
    if not tid:
        return jsonify({'ok': False, 'error': 'ID em falta'}), 400
    try:
        sql = text(f"""
            UPDATE TAREFAS
            SET TRATADO = 0,
                NMTRATADO = '',
                DTTRATADO = CAST('1900-01-01' AS date)
            WHERE TAREFASSTAMP = :id
            {_sql_feid_clause('TAREFAS')}
        """)
        params = {'id': tid}
        if _table_is_fe_scoped('TAREFAS'):
            params['current_feid'] = _current_feid_or_abort()
        db.session.execute(sql, params)
        db.session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Erro ao reabrir tarefa')
        return jsonify({'ok': False, 'error': str(e)}), 500

# --------------------------------------------------
# API: RS search and update OBS
# --------------------------------------------------
@bp.route('/api/rs/search')
@login_required
def rs_search():
    date_in   = request.args.get('date')
    reserva   = request.args.get('reserva')
    if not date_in and not reserva:
        return jsonify({'error': 'Indica data ou reserva'}), 400

    try:
        params = {}
        if date_in:
            sql = text(f"""
                SELECT RSSTAMP, RESERVA, ALOJAMENTO, CONVERT(varchar(10), DATAIN, 23) AS DATAIN,
                       NOITES, ADULTOS, CRIANCAS, OBS, NOME, ISNULL(BERCO,0) AS BERCO, ISNULL(SOFACAMA,0) AS SOFACAMA
                FROM RS
                WHERE DATAIN = :date AND (CANCELADA = 0 OR CANCELADA IS NULL)
                {_sql_feid_clause('RS', mode='read')}
                ORDER BY ALOJAMENTO
            """)
            params['date'] = date_in
        else:
            sql = text(f"""
                SELECT RSSTAMP, RESERVA, ALOJAMENTO, CONVERT(varchar(10), DATAIN, 23) AS DATAIN,
                       NOITES, ADULTOS, CRIANCAS, OBS, NOME, ISNULL(BERCO,0) AS BERCO, ISNULL(SOFACAMA,0) AS SOFACAMA
                FROM RS
                WHERE RESERVA = :reserva AND (CANCELADA = 0 OR CANCELADA IS NULL)
                {_sql_feid_clause('RS', mode='read')}
            """)
            params['reserva'] = reserva
        if _table_is_fe_scoped('RS'):
            params['current_feid'] = _current_feid_or_abort()
        rows = db.session.execute(sql, params).fetchall()
        return jsonify([dict(r._mapping) for r in rows])
    except Exception as e:
        current_app.logger.exception('Erro em rs_search')
        return jsonify({'error': str(e)}), 500

@bp.route('/api/rs/obs', methods=['POST'])
@login_required
def rs_update_obs():
    data = request.get_json(silent=True) or {}
    reserva = data.get('reserva')
    obs     = data.get('obs', '')
    berco   = 1 if data.get('berco') else 0
    sofacama= 1 if data.get('sofacama') else 0
    if not reserva:
        return jsonify({'ok': False, 'error': 'Reserva em falta'}), 400
    try:
        sql = text(f"""
            UPDATE RS
            SET OBS = :obs,
                BERCO = :berco,
                SOFACAMA = :sofacama
            WHERE RESERVA = :reserva
            {_sql_feid_clause('RS', mode='write')}
        """)
        params = {'obs': obs, 'reserva': reserva, 'berco': berco, 'sofacama': sofacama}
        if _table_is_fe_scoped('RS'):
            params['current_feid'] = _current_feid_or_abort()
        db.session.execute(sql, params)
        db.session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Erro em rs_update_obs')
        return jsonify({'ok': False, 'error': str(e)}), 500

# --------------------------------------------------
# API: registro Ãºnico
# --------------------------------------------------
@bp.route('/api/<table_name>/<record_stamp>', methods=['GET'])
@login_required
def get_record(table_name, record_stamp):
    if not has_permission(table_name, 'consultar'):
        abort(403, 'Sem permissÃ£o para consultar')

    table = get_table(table_name)
    pk    = getattr(table.c, f"{table_name.upper()}STAMP")
    stmt  = select(table).where(pk == record_stamp)
    stmt  = _apply_feid_scope_stmt(stmt, table, table_name, mode='read')
    row   = db.session.execute(stmt).fetchone()
    if not row:
        abort(404, f"Registro nÃ£o encontrado: {record_stamp}")

    # Base: dados reais
    rec = dict(row._mapping)

    # ðŸ” Adiciona campos virtuais
    virtual_fields = (
        Campo.query
             .filter_by(tabela=table_name, tipo='VIRTUAL')
             .all()
    )
    pk_value = rec.get(f"{table_name.upper()}STAMP")

    for campo in virtual_fields:
        try:
            val = db.session.execute(text(campo.virtual), {'pk': pk_value}).scalar()
        except Exception as e:
            val = None
        rec[campo.nmcampo] = val

    return jsonify(rec)


# --------------------------------------------------
# API: inserir novo registro
# --------------------------------------------------
@bp.route('/api/<table_name>', methods=['POST'])
@login_required
def create_record(table_name):
    if not has_permission(table_name, 'inserir'):
        abort(403, 'Sem permissÃ£o para inserir')

    table = get_table(table_name)
    data  = request.get_json() or {}
    tn = (table_name or '').strip().upper()
    current_feid = _current_feid_or_abort() if _table_is_fe_scoped(table_name) else None

    # Se vier chave vazia para o PK, removemos
    pk_name = f"{table_name.upper()}STAMP"
    if pk_name in data and not data[pk_name]:
        data.pop(pk_name)

    # â€” Filtra sÃ³ colunas vÃ¡lidas â€”
    col_map = {c.name.lower(): c.name for c in table.c}
    clean   = {}
    for k, v in data.items():
        lk = k.lower()
        if lk in col_map:
            clean[col_map[lk]] = v
    # â€” end filtra â€”

    _ensure_named_stamp(table, table_name, clean)

    if current_feid is not None:
        clean['FEID'] = current_feid

    if _is_partner_table(tn) and 'NO' in col_map:
        raw_no = clean.get('NO')
        raw_text = '' if raw_no is None else str(raw_no).strip()
        if raw_text == '':
            clean['NO'] = _next_incremental_no(tn, current_feid)
        else:
            try:
                clean['NO'] = int(float(raw_text.replace(',', '.')))
            except Exception:
                label = 'cliente' if tn == 'CL' else 'fornecedor'
                return jsonify({'error': f'Número de {label} inválido.'}), 400
        if _record_no_exists(tn, clean['NO'], current_feid):
            label = 'cliente' if tn == 'CL' else 'fornecedor'
            return jsonify({'error': f'Já existe um {label} com o número {clean["NO"]}.'}), 400

    # Bloqueio: FO/FN incluÃ­do(s) em pagamento nÃ£o podem ser alterados
    try:
        if tn == 'FN':
            fs = (clean.get('FOSTAMP') or '').strip()
            if fs and fo_pagamento_status(fs).get('locked'):
                return jsonify({'error': 'Documento incluido em pagamento. Nao pode ser alterado.'}), 403
    except Exception:
        # nÃ£o bloquear por falhas no check; deixa seguir e o erro aparece no commit se existir
        pass

    try:
        ins = table.insert().inline().values(**clean)
        db.session.execute(ins)
        db.session.commit()
        return jsonify({'success': True}), 201
    except Exception as e:
        current_app.logger.exception(f"Falha ao criar {table_name}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# --------------------------------------------------
# API: obter ORIGEM e ORISTAMP de uma TAREFA
# --------------------------------------------------
@bp.route('/api/tarefa_origin/<tarefas_stamp>', methods=['GET'])
@login_required
def tarefa_origin(tarefas_stamp):
    if not tarefas_stamp:
        return jsonify({'error': 'TAREFASSTAMP em falta'}), 400
    # Permissão básica: consultar TAREFAS
    if not has_permission('TAREFAS', 'consultar') and not getattr(current_user, 'ADMIN', False):
        return jsonify({'error': 'Sem permissão'}), 403
    try:
        params = {'id': tarefas_stamp}
        sql = text(f"""
            SELECT TOP 1 ORIGEM, ORISTAMP
            FROM TAREFAS
            WHERE TAREFASSTAMP = :id
            {_sql_feid_clause('TAREFAS')}
        """)
        if _table_is_fe_scoped('TAREFAS'):
            params['current_feid'] = _current_feid_or_abort()
        row = db.session.execute(sql, params).mappings().first()
        if not row:
            return jsonify({}), 404
        return jsonify({'ORIGEM': row['ORIGEM'] or '', 'ORISTAMP': row['ORISTAMP'] or ''})
    except Exception as e:
        current_app.logger.exception('Erro em tarefa_origin')
        return jsonify({'error': str(e)}), 500

# --------------------------------------------------
# API: atualizar registro
# --------------------------------------------------
@bp.route('/api/<table_name>/<record_stamp>', methods=['PUT'])
@login_required
def update_record(table_name, record_stamp):
    if not has_permission(table_name, 'editar'):
        abort(403, 'Sem permissÃ£o para editar')

    table = get_table(table_name)
    data  = request.get_json() or {}
    tn = (table_name or '').strip().upper()
    # filtra sÃ³ colunas vÃ¡lidas
    col_map = {c.name.lower(): c.name for c in table.c}
    clean   = {}
    for k, v in data.items():
        lk = k.lower()
        if lk in col_map:
            clean[col_map[lk]] = v
    data = clean

    if _is_partner_table(tn) and 'NO' in data:
        data.pop('NO', None)

    pk = getattr(table.c, f"{table_name.upper()}STAMP")

    # Bloqueio: FO/FN incluÃ­do(s) em pagamento nÃ£o podem ser alterados
    try:
        if tn == 'FO':
            if fo_pagamento_status(record_stamp).get('locked'):
                return jsonify({'error': 'Documento incluido em pagamento. Nao pode ser alterado.'}), 403
        elif tn == 'FN':
            row = db.session.execute(
                text("SELECT TOP 1 LTRIM(RTRIM(ISNULL(FOSTAMP,''))) AS FOSTAMP FROM dbo.FN WHERE FNSTAMP = :id"),
                {'id': record_stamp}
            ).mappings().first()
            fs = (row or {}).get('FOSTAMP') or ''
            if fs and fo_pagamento_status(fs).get('locked'):
                return jsonify({'error': 'Documento incluido em pagamento. Nao pode ser alterado.'}), 403
    except Exception:
        pass

    try:
        upd = table.update().where(pk == record_stamp)
        upd = _apply_feid_scope_stmt(upd, table, table_name, mode='write')
        upd = upd.values(**data)
        res = db.session.execute(upd)
        if res.rowcount == 0:
            abort(404)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.exception(f"Falha ao atualizar {table_name}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# --------------------------------------------------
# API: apagar registro
# --------------------------------------------------
@bp.route('/api/<table_name>/<record_stamp>', methods=['DELETE'])
@login_required
def delete_record(table_name, record_stamp):
    # Bloqueio: FO/FN incluÃ­do(s) em pagamento nÃ£o podem ser eliminados
    try:
        tn = (table_name or '').strip().upper()
        if tn == 'FO':
            if fo_pagamento_status(record_stamp).get('locked'):
                return jsonify({'error': 'Documento incluido em pagamento. Nao pode ser eliminado.'}), 403
        elif tn == 'FN':
            row = db.session.execute(
                text("SELECT TOP 1 LTRIM(RTRIM(ISNULL(FOSTAMP,''))) AS FOSTAMP FROM dbo.FN WHERE FNSTAMP = :id"),
                {'id': record_stamp}
            ).mappings().first()
            fs = (row or {}).get('FOSTAMP') or ''
            if fs and fo_pagamento_status(fs).get('locked'):
                return jsonify({'error': 'Documento incluido em pagamento. Nao pode ser eliminado.'}), 403
    except Exception:
        pass

    if not has_permission(table_name, 'eliminar'):
        abort(403, 'Sem permissÃ£o para eliminar')

    table = get_table(table_name)
    pk = getattr(table.c, f"{table_name.upper()}STAMP")
    stmt = table.delete().where(pk == record_stamp)
    stmt = _apply_feid_scope_stmt(stmt, table, table_name, mode='write')
    result = db.session.execute(stmt)
    db.session.commit()

    if result.rowcount == 0:
        abort(404, "Registo nÃ£o encontrado")

    return jsonify(success=True)

# --------------------------------------------------
# API: linhas dinÃ¢micas
# --------------------------------------------------
@bp.route('/api/linhas/<mae>', methods=['GET'])
@login_required
def api_linhas(mae):
    if not has_permission(mae, 'consultar'):
        abort(403, 'Sem permissÃ£o para consultar linhas deste registo')

    linhas = Linhas.query.filter_by(MAE=mae).all()
    resultado = []
    for l in linhas:
        resultado.append({
            'LINHASSTAMP': l.LINHASSTAMP,
            'TABELA':      l.TABELA,
            'LIGACAO':     l.LIGACAO,
            'LIGACAOMAE':  l.LIGACAOMAE,
            'CAMPOSCAB':   l.LIGACAO,
            'CAMPOSLIN':   l.LIGACAOMAE
        })
    return jsonify(resultado)

# --------------------------------------------------
# API: detalhes dinÃ¢micos
# --------------------------------------------------
@bp.route('/api/dynamic_details/<mae>/<record_stamp>', methods=['GET'])
@login_required
def api_dynamic_details(mae, record_stamp):
    if not has_permission(mae, 'consultar'):
        abort(403, 'Sem permissÃ£o para ver detalhes')

    detalhes = []
    for defn in Linhas.query.filter_by(MAE=mae):
        tabela     = defn.TABELA.strip()
        ligacao    = (defn.LIGACAO or '').strip()
        ligacaomae = defn.LIGACAOMAE.strip()

        # --- monta o SQL dinamicamente ---
        if ligacao.upper().startswith('SELECT') or ' ' in ligacao:
            sql = ligacao.replace("{RECORD_STAMP}", ":record")
        elif ligacao:
            sql = f"SELECT * FROM {tabela} WHERE {ligacao} = :record"
        elif ligacaomae:
            sql = f"SELECT * FROM {tabela} WHERE {ligacaomae} = :record"
        else:
            abort(500, f"DefiniÃ§Ã£o invÃ¡lida para detalhe {tabela}")

        # <<< AQUI: executa e define `rows` >>>
        rows = db.session.execute(text(sql), {"record": record_stamp}).mappings().all()

        # metadados de colunas para a lista
        pk_name = f"{tabela.upper()}STAMP"

        # buscar os campos visÃ­veis na lista
        cols = list(
            Campo.query
                .filter_by(tabela=tabela, lista=True)
                .order_by(Campo.ordem)
                .all()
        )

        # garantir que a PK estÃ¡ incluÃ­da (mesmo que lista=False)
        pk_name = f"{tabela.upper()}STAMP"
        if not any(c.nmcampo.upper() == pk_name for c in cols):
            # cria um campo fake, nÃ£o vem da tabela Campo
            from types import SimpleNamespace
            cols.insert(0, SimpleNamespace(nmcampo=pk_name, descricao='ID', ordem=0))

        campos = [
            {
                "CAMPO": c.nmcampo,
                "LABEL": _translated_campo_label(c, c.descricao),
                "CAMPODESTINO": c.nmcampo,
                "VISIVEL": c.nmcampo.upper() != pk_name
            }
            for c in cols
        ]

        # mapeia camposcab / camposlin
        camposcab = [c.strip() for c in (defn.CAMPOSCAB or '').split(',') if c.strip()]
        camposlin = [c.strip() for c in (defn.CAMPOSLIN or '').split(',') if c.strip()]

        # <<< e sÃ³ aqui Ã© que usas `rows` >>>
        detalhes.append({
            "linhasstamp": defn.LINHASSTAMP,
            "tabela":      tabela,
            "campos":      campos,
            "rows":        [dict(r) for r in rows],
            "camposcab":   camposcab,
            "camposlin":   camposlin
        })

    return jsonify(detalhes)


# --------------------------------------------------
# API: tarefas para calendar
# --------------------------------------------------
from datetime import datetime

@bp.route('/api/calendar_tasks', methods=['GET'])
@login_required
def api_calendar_tasks():
    start = request.args.get('start')
    end   = request.args.get('end')
    if not start or not end:
        abort(400, 'Precisamos de start e end em formato YYYY-MM-DD')
    try:
        datetime.strptime(start, '%Y-%m-%d')
        datetime.strptime(end,   '%Y-%m-%d')
    except ValueError:
        abort(400, 'Formato de data invÃ¡lido')

    sql = text("""
    SELECT
      ta.TAREFASSTAMP,
      CONVERT(varchar(10), ta.DATA, 23) AS DATA,
      ta.HORA,
      ta.DURACAO,
      ta.TAREFA,
      ta.ALOJAMENTO,
      ta.UTILIZADOR,
      ta.ORIGEM,
      ta.ORISTAMP,
      ta.TRATADO,
      COALESCE(u.COR, tc.COR, eq.COR, '#333333') AS COR
    FROM TAREFAS ta
    LEFT JOIN US    u  ON u.LOGIN    = ta.UTILIZADOR
    LEFT JOIN TEC   tc ON tc.NOME    = u.TECNICO
    LEFT JOIN EQ    eq ON eq.NOME    = u.EQUIPA
    WHERE ta.DATA BETWEEN :start AND :end
      """ + _sql_feid_clause('TAREFAS', 'ta') + """
    ORDER BY ta.DATA, ta.HORA
    """)
    params = {'start': start, 'end': end}
    if _table_is_fe_scoped('TAREFAS'):
        params['current_feid'] = _current_feid_or_abort()
    rows = db.session.execute(sql, params).mappings().all()
    tarefas = [dict(r) for r in rows]
    return jsonify(tarefas)


# In generic_crud.py (add within the existing Blueprint `bp`)

from datetime import date, datetime

@bp.route('/planner/', defaults={'planner_date': None})
@bp.route('/planner/<planner_date>')
@login_required
def view_planner(planner_date):
    try:
        if planner_date:
            datetime.strptime(planner_date, '%Y-%m-%d')  # valida formato
        else:
            planner_date = date.today().isoformat()
    except ValueError:
        return "Formato de data invÃ¡lido (usa YYYY-MM-DD)", 400

    return render_template('planner.html', planner_date=planner_date)


@bp.route('/planeamento_limpezas/', defaults={'planner_date': None})
@bp.route('/planeamento_limpezas/<planner_date>')
@login_required
def view_planeamento_limpezas(planner_date):
    if not has_cleaning_planner_access():
        abort(403, 'Sem permissão para consultar')
    try:
        if planner_date:
            datetime.strptime(planner_date, '%Y-%m-%d')
        else:
            planner_date = date.today().isoformat()
    except ValueError:
        return "Formato de data inválido (usa YYYY-MM-DD)", 400

    return render_template('planeamento_limpezas.html', planner_date=planner_date, page_title='Planeamento de Limpezas')



@bp.route('/api/cleaning_plan')
@login_required
def api_cleaning_plan():
    """
    Return JSON payload with lodging cleaning plan for a given date.
    Query params:
      - date: 'YYYY-MM-DD'
    """
    if not has_cleaning_planner_access():
        return jsonify({'error': 'Sem permissão para consultar'}), 403
    date = request.args.get('date')
    try:
        cols = db.session.execute(text("""
            SELECT UPPER(COLUMN_NAME) AS COL
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'RS'
        """)).fetchall()
        rs_cols = {str(r[0] or '').strip().upper() for r in cols if r and r[0]}
    except Exception:
        rs_cols = set()

    try:
        al_cols = db.session.execute(text("""
            SELECT UPPER(COLUMN_NAME) AS COL
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'AL'
        """)).fetchall()
        al_cols = {str(r[0] or '').strip().upper() for r in al_cols if r and r[0]}
    except Exception:
        al_cols = set()

    def build_guest_expr(alias: str, field_name: str) -> str:
        candidates = ['NOME', 'HOSPEDE', 'NOMEHOSPEDE', 'CLIENTE', 'NOMECLIENTE', 'NMAIRBNB', 'HOSPEDE_NOME']
        cols = [c for c in candidates if c in rs_cols]
        if not cols:
            return f"'' AS {field_name}"
        parts = [f"NULLIF(LTRIM(RTRIM({alias}.[{c}])), '')" for c in cols]
        return f"COALESCE({', '.join(parts)}, '') AS {field_name}"

    def build_country_expr(alias: str, field_name: str) -> str:
        candidates = ['PAIS', 'NACIONALIDADE', 'NACAO']
        cols = [c for c in candidates if c in rs_cols]
        if not cols:
            return f"'' AS {field_name}"
        parts = [f"NULLIF(LTRIM(RTRIM({alias}.[{c}])), '')" for c in cols]
        return f"COALESCE({', '.join(parts)}, '') AS {field_name}"

    def build_al_expr(column: str, field_name: str) -> str:
        if column not in al_cols:
            return f"'' AS {field_name}"
        return f"NULLIF(LTRIM(RTRIM(al.[{column}])), '') AS {field_name}"

    guest_expr = build_guest_expr('co', 'checkout_guest')
    guest_in_expr = build_guest_expr('ci', 'checkin_guest')
    guest_occ_expr = build_guest_expr('oc_r', 'occupied_guest')
    country_expr = build_country_expr('co', 'checkout_country')
    country_in_expr = build_country_expr('ci', 'checkin_country')
    country_occ_expr = build_country_expr('oc_r', 'occupied_country')

    al_codpost_expr = build_al_expr('CODPOST', 'al_codpost')
    al_local_expr = build_al_expr('LOCAL', 'al_local')
    al_morada_expr = build_al_expr('MORADA', 'al_morada')
    al_lptempo_expr = "ISNULL(al.[LPTEMPO], 0) AS cleaning_minutes" if 'LPTEMPO' in al_cols else "0 AS cleaning_minutes"

    sql = text(f"""
        SELECT
          al.ALSTAMP             AS al_stamp,
          al.NOME                 AS lodging,
          al.TIPOLOGIA            AS typology,
          al.ZONA                 AS zone,
          {al_lptempo_expr},
          {al_codpost_expr},
          {al_local_expr},
          {al_morada_expr},
          -- Última equipa que limpou
          lc.last_date            AS last_clean_date,
          lc.last_hour            AS last_clean_hour,
          lc.last_team            AS last_team,
          CASE
            WHEN lc.last_date IS NOT NULL
             AND NOT EXISTS (
                SELECT 1
                FROM RS rs_clean
                WHERE rs_clean.ALOJAMENTO = al.NOME
                  AND rs_clean.CANCELADA = 0
                  AND rs_clean.DATAIN >= lc.last_date
                  AND rs_clean.DATAIN < :date
             )
            THEN 1 ELSE 0
          END AS clean_since_last,
          -- Check-out do dia
          co.HORAOUT              AS checkout_time,
          co.RESERVA              AS checkout_reservation,
          co.ADULTOS + co.CRIANCAS AS checkout_people,
          co.NOITES               AS checkout_nights,
          {guest_expr},
          {country_expr},
          -- Check-in do dia
          ci.HORAIN               AS checkin_time,
          ci.RESERVA              AS checkin_reservation,
          ci.ADULTOS + ci.CRIANCAS AS checkin_people,
          ci.NOITES               AS checkin_nights,
          {guest_in_expr},
          {country_in_expr},
          ISNULL(oc_r.ADULTOS,0) + ISNULL(oc_r.CRIANCAS,0) AS occupied_people,
          ISNULL(oc_r.NOITES,0) AS occupied_nights,
          {guest_occ_expr},
          {country_occ_expr},
          -- Limpezas já agendadas no dia
          pl_day.LPSTAMP          AS cleaning_id,
          pl_day.HORA             AS cleaning_time,
          pl_day.EQUIPA           AS cleaning_team,
          pl_day.TERMINADA        AS cleaning_done,
          pl_day.HOSPEDES         AS cleaning_guests,
          pl_day.NOITES           AS cleaning_nights,
          pl_day.OBS              AS cleaning_notes,
          ta.TAREFASSTAMP         AS cleaning_task_id,
          ta.TRATADO              AS cleaning_task_done,
          ta.HORAINI              AS cleaning_started_at,
          ta.HORAFIM              AS cleaning_finished_at,
          ta.UTILIZADOR_NOME      AS cleaning_task_user,
          -- Limpeza adiada (entre hoje e o próximo check-in)
          (
            SELECT TOP 1 LP.DATA
            FROM LP
            WHERE LP.ALOJAMENTO = al.NOME
              AND LP.DATA > :date
              AND (
                    (SELECT MIN(RS.DATAIN)
                     FROM RS
                     WHERE RS.ALOJAMENTO = al.NOME
                       AND RS.CANCELADA = 0
                       AND RS.DATAIN > :date) IS NULL
                 OR LP.DATA < (
                     SELECT MIN(RS.DATAIN)
                     FROM RS
                     WHERE RS.ALOJAMENTO = al.NOME
                       AND RS.CANCELADA = 0
                       AND RS.DATAIN > :date)
                )
            ORDER BY LP.DATA ASC
          ) AS postponed_date,
          (
            SELECT TOP 1 LP.EQUIPA
            FROM LP
            WHERE LP.ALOJAMENTO = al.NOME
              AND LP.DATA > :date
              AND (
                    (SELECT MIN(RS.DATAIN)
                     FROM RS
                     WHERE RS.ALOJAMENTO = al.NOME
                       AND RS.CANCELADA = 0
                       AND RS.DATAIN > :date) IS NULL
                 OR LP.DATA < (
                     SELECT MIN(RS.DATAIN)
                     FROM RS
                     WHERE RS.ALOJAMENTO = al.NOME
                       AND RS.CANCELADA = 0
                       AND RS.DATAIN > :date)
                )
            ORDER BY LP.DATA ASC
          ) AS postponed_team,
          -- O estado (1:checkout, 2:checkin, 3:ocupado, 4:vazio)
          CASE
            WHEN co.RSSTAMP IS NOT NULL THEN 1
            WHEN ci.RSSTAMP IS NOT NULL THEN 2
            WHEN oc.RSSTAMP IS NOT NULL THEN 3
            ELSE 4
          END AS planner_status,
          0 AS cost
        FROM AL al
        OUTER APPLY (
          SELECT TOP 1
            LP.DATA AS last_date,
            LP.HORA AS last_hour,
            LP.EQUIPA AS last_team
          FROM LP
          WHERE LP.ALOJAMENTO = al.NOME
            AND LP.DATA < :date
          ORDER BY LP.DATA DESC, LP.HORA DESC, LP.LPSTAMP DESC
        ) lc
        -- Apenas reservas NÃO canceladas
        LEFT JOIN RS co ON co.ALOJAMENTO = al.NOME AND co.DATAOUT = :date AND co.CANCELADA = 0
        LEFT JOIN RS ci ON ci.ALOJAMENTO = al.NOME AND ci.DATAIN = :date AND ci.CANCELADA = 0
        LEFT JOIN (
          SELECT RSSTAMP, ALOJAMENTO
          FROM RS
          WHERE CANCELADA = 0
            AND DATAIN < :date AND DATAOUT > :date
        ) oc ON oc.ALOJAMENTO = al.NOME
        LEFT JOIN RS oc_r ON oc_r.RSSTAMP = oc.RSSTAMP
        LEFT JOIN LP pl_day ON pl_day.ALOJAMENTO = al.NOME AND pl_day.DATA = :date
        OUTER APPLY (
          SELECT TOP 1
            T.TAREFASSTAMP,
            ISNULL(T.TRATADO, 0) AS TRATADO,
            ISNULL(T.HORAINI, '') AS HORAINI,
            ISNULL(T.HORAFIM, '') AS HORAFIM,
            ISNULL(U.NOME, T.UTILIZADOR) AS UTILIZADOR_NOME
          FROM dbo.TAREFAS AS T
          LEFT JOIN dbo.US AS U ON U.LOGIN = T.UTILIZADOR
          WHERE pl_day.LPSTAMP IS NOT NULL
            AND LTRIM(RTRIM(ISNULL(T.ORIGEM, ''))) = 'LP'
            AND CAST(T.DATA AS date) = :date
            AND LTRIM(RTRIM(ISNULL(T.ALOJAMENTO, ''))) = LTRIM(RTRIM(ISNULL(pl_day.ALOJAMENTO, '')))
            AND (
              LTRIM(RTRIM(ISNULL(T.ORISTAMP, ''))) = LTRIM(RTRIM(ISNULL(pl_day.LPSTAMP, '')))
              OR (
                LTRIM(RTRIM(ISNULL(T.ORISTAMP, ''))) = ''
                AND LTRIM(RTRIM(ISNULL(T.HORA, ''))) = LTRIM(RTRIM(ISNULL(pl_day.HORA, '')))
              )
            )
          ORDER BY
            CASE WHEN LTRIM(RTRIM(ISNULL(T.ORISTAMP, ''))) = LTRIM(RTRIM(ISNULL(pl_day.LPSTAMP, ''))) THEN 0 ELSE 1 END,
            T.TAREFASSTAMP
        ) ta
        
        ORDER BY planner_status, al.ZONA, al.NOME
    """)
    # Execute and fetch mappings
    rows = db.session.execute(sql, {'date': date}).mappings().all()

    # Convert RowMapping to plain dicts for JSON serialization
    result = [dict(row) for row in rows]
    return jsonify(result)


@bp.route('/api/planner2_teams')
@login_required
def api_planner2_teams():
    if not has_cleaning_planner_access():
        return jsonify({'error': 'Sem permissão para consultar'}), 403
    try:
        raw_date = str(request.args.get('date') or '').strip()
        planner_date = None
        if raw_date:
            try:
                planner_date = datetime.strptime(raw_date[:10], '%Y-%m-%d').date()
            except Exception:
                return jsonify({'error': 'Data inválida'}), 400

        cols = db.session.execute(text("""
            SELECT UPPER(COLUMN_NAME) AS COL
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'EQ'
        """)).fetchall()
        eq_cols = {str(r[0] or '').strip().upper() for r in cols if r and r[0]}

        select_cols = ["LTRIM(RTRIM(ISNULL(NOME,''))) AS NOME"]
        if 'COR' in eq_cols:
            select_cols.append("ISNULL(COR,'') AS COR")
        else:
            select_cols.append("'' AS COR")
        select_cols.append("""
            CASE WHEN EXISTS (
                SELECT 1
                FROM dbo.US AS U_ADMIN
                WHERE LTRIM(RTRIM(ISNULL(U_ADMIN.EQUIPA, ''))) = LTRIM(RTRIM(ISNULL(EQ.NOME, '')))
                  AND ISNULL(U_ADMIN.LPADMIN, 0) = 1
            ) THEN 1 ELSE 0 END AS LPADMIN
        """)
        order_expr = 'ORDER BY NOME'
        if 'ORDEM' in eq_cols:
            order_expr = 'ORDER BY ORDEM, NOME'

        where_clauses = ["LTRIM(RTRIM(ISNULL(NOME,''))) <> ''"]
        if 'INATIVO' in eq_cols:
            where_clauses.append("ISNULL(INATIVO, 0) = 0")
        params = {}
        if planner_date:
            where_clauses.append("""
                NOT EXISTS (
                    SELECT 1
                    FROM dbo.US AS U
                    INNER JOIN dbo.ND AS ND
                        ON LTRIM(RTRIM(ISNULL(ND.UTILIZADOR, ''))) = LTRIM(RTRIM(ISNULL(U.LOGIN, '')))
                    WHERE LTRIM(RTRIM(ISNULL(U.EQUIPA, ''))) = LTRIM(RTRIM(ISNULL(EQ.NOME, '')))
                      AND CAST(ND.DATA AS date) = :planner_date
                )
            """)
            params['planner_date'] = planner_date

        sql = text(f"""
            SELECT {', '.join(select_cols)}
            FROM dbo.EQ
            WHERE {' AND '.join(where_clauses)}
            {order_expr}
        """)
        rows = db.session.execute(sql, params).mappings().all()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        current_app.logger.exception('Erro ao carregar equipas do planner2')
        return jsonify({'error': str(e)}), 500

@bp.route("/api/LP/gravar", methods=["POST"])
@login_required
def api_gravar_limpezas():
    if not has_cleaning_planner_access():
        return jsonify(success=False, message='Sem permissão para gravar'), 403
    current_feid = None
    if _table_is_fe_scoped('LP'):
        try:
            current_feid = get_current_feid()
        except MissingCurrentEntityError:
            return jsonify(success=False, message='Empresa ativa não definida.'), 400
    limpezas = request.get_json()
    if not limpezas:
        return jsonify(success=False, message="Nenhum dado recebido"), 400
    push_queue = []
    for lp in limpezas:
        lpstamp = lp.get("LPSTAMP") or lp.get("lpstamp")
        if lpstamp:
            previous = db.session.execute(text("""
                SELECT TOP 1
                    ISNULL(ALOJAMENTO,'') AS ALOJAMENTO,
                    CONVERT(varchar(10), DATA, 23) AS DATA,
                    ISNULL(HORA,'') AS HORA,
                    ISNULL(EQUIPA,'') AS EQUIPA
                FROM LP
                WHERE LPSTAMP = :lpstamp
            """), {"lpstamp": lpstamp}).mappings().first()
            res = db.session.execute(
                text("""
                UPDATE LP
                SET ALOJAMENTO = :alojamento,
                    DATA = :data,
                    HORA = :hora,
                    EQUIPA = :equipa
                    {feid_sql}
                WHERE LPSTAMP = :lpstamp
                """.format(
                    feid_sql=', FEID = :feid' if current_feid is not None else ''
                )),
                dict(
                    lpstamp=lpstamp,
                    alojamento=lp["ALOJAMENTO"],
                    data=lp["DATA"],
                    hora=lp["HORA"],
                    equipa=lp["EQUIPA"],
                    **({'feid': current_feid} if current_feid is not None else {})
                )
            )
            if res.rowcount:
                prev = dict(previous or {})
                changed = any([
                    str(prev.get("ALOJAMENTO") or "") != str(lp.get("ALOJAMENTO") or ""),
                    str(prev.get("DATA") or "") != str(lp.get("DATA") or ""),
                    str(prev.get("HORA") or "") != str(lp.get("HORA") or ""),
                    str(prev.get("EQUIPA") or "") != str(lp.get("EQUIPA") or ""),
                ])
                if changed and str(lp.get("EQUIPA") or "").strip():
                    push_queue.append({
                        "event_type": "TASK_REASSIGNED" if str(prev.get("EQUIPA") or "").strip() else "CLEANING_ASSIGNED",
                        "team": lp["EQUIPA"],
                        "context": {
                            "alojamento": lp.get("ALOJAMENTO"),
                            "data": lp.get("DATA"),
                            "hora": lp.get("HORA"),
                            "body": f"{lp.get('ALOJAMENTO') or 'Alojamento'} - {lp.get('DATA') or ''} {lp.get('HORA') or ''}".strip(),
                            "url": "/monitor",
                        },
                    })
                continue
        # Verifica se jÃ¡ existe (mesmo ALOJAMENTO, DATA, HORA, EQUIPA)
        reg = db.session.execute(
            text("""
            SELECT LPSTAMP FROM LP WHERE
              ALOJAMENTO = :alojamento
              AND DATA = :data
              AND HORA = :hora
              AND EQUIPA = :equipa
              {feid_where}
            """.format(
                feid_where='AND FEID = :feid' if current_feid is not None else ''
            )), dict(
                alojamento=lp["ALOJAMENTO"],
                data=lp["DATA"],
                hora=lp["HORA"],
                equipa=lp["EQUIPA"],
                **({'feid': current_feid} if current_feid is not None else {})
            )
        ).fetchone()
        if reg:
            continue  # jÃ¡ existe, nÃ£o grava de novo
        # SenÃ£o, cria
        db.session.execute(
            text("""
            INSERT INTO LP (LPSTAMP, ALOJAMENTO, DATA, HORA, EQUIPA, TERMINADA, CUSTO, HOSPEDES, NOITES, OBS{feid_cols})
            VALUES (:lpstamp, :alojamento, :data, :hora, :equipe, 0, 0, 0, 0, ''{feid_vals})
            """.format(
                feid_cols=', FEID' if current_feid is not None else '',
                feid_vals=', :feid' if current_feid is not None else '',
            )),
            dict(
                lpstamp=uuid.uuid4().hex[:25],
                alojamento=lp["ALOJAMENTO"],
                data=lp["DATA"],
                hora=lp["HORA"],
                equipe=lp["EQUIPA"],
                **({'feid': current_feid} if current_feid is not None else {})
            )
        )
        if str(lp.get("EQUIPA") or "").strip():
            push_queue.append({
                "event_type": "CLEANING_ASSIGNED",
                "team": lp["EQUIPA"],
                "context": {
                    "alojamento": lp.get("ALOJAMENTO"),
                    "data": lp.get("DATA"),
                    "hora": lp.get("HORA"),
                    "url": "/monitor",
                },
            })
    db.session.commit()
    if push_queue:
        try:
            from services.push_service import send_push_to_team
            for item in push_queue:
                send_push_to_team(
                    item.get("team"),
                    item.get("event_type") or "CLEANING_ASSIGNED",
                    context=item.get("context") or {},
                    sent_by_userstamp=getattr(current_user, "USSTAMP", None),
                )
        except Exception:
            current_app.logger.exception("Erro ao enviar notificações push de limpeza.")
    return jsonify(success=True)


@bp.route("/api/LP/<lpstamp>/planner-delete", methods=["DELETE"])
@login_required
def api_delete_planner_limpeza(lpstamp):
    if not has_cleaning_planner_access():
        return jsonify({'error': 'Sem permissão para eliminar'}), 403

    lpstamp = (lpstamp or '').strip()
    if not lpstamp:
        return jsonify({'error': 'LPSTAMP em falta'}), 400

    current_feid = None
    if _table_is_fe_scoped('LP'):
        try:
            current_feid = get_current_feid()
        except MissingCurrentEntityError:
            return jsonify({'error': 'Empresa ativa não definida.'}), 400

    is_admin = bool(getattr(current_user, 'ADMIN', False) or getattr(current_user, 'LPADMIN', False))

    try:
        if is_admin or current_feid is None:
            result = db.session.execute(
                text("DELETE FROM dbo.LP WHERE LPSTAMP = :lpstamp"),
                {'lpstamp': lpstamp},
            )
        elif _column_exists('AL', 'FEID_GESTOR'):
            result = db.session.execute(
                text(
                    """
                    DELETE LP
                    FROM dbo.LP AS LP
                    WHERE LP.LPSTAMP = :lpstamp
                      AND EXISTS (
                          SELECT 1
                          FROM dbo.AL AS ALV
                          WHERE LTRIM(RTRIM(ISNULL(ALV.NOME,''))) = LTRIM(RTRIM(ISNULL(LP.ALOJAMENTO,'')))
                            AND (
                                (ISNULL(ALV.FEID_GESTOR, 0) <> 0 AND ISNULL(ALV.FEID_GESTOR, 0) = :current_feid)
                                OR
                                (ISNULL(ALV.FEID_GESTOR, 0) = 0 AND ISNULL(LP.FEID, 0) = :current_feid)
                            )
                      )
                    """
                ),
                {'lpstamp': lpstamp, 'current_feid': current_feid},
            )
        else:
            result = db.session.execute(
                text("DELETE FROM dbo.LP WHERE LPSTAMP = :lpstamp AND FEID = :current_feid"),
                {'lpstamp': lpstamp, 'current_feid': current_feid},
            )

        if int(result.rowcount or 0) == 0:
            db.session.rollback()
            return jsonify({'error': 'Sem permissão para eliminar esta limpeza na empresa ativa.'}), 403

        db.session.commit()
        return jsonify({'success': True})
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception('Erro ao eliminar limpeza do planner')
        return jsonify({'error': str(exc)}), 500


_osm_geocode_cache = {}
_osm_distance_cache = {}


def _osm_fetch_json(url: str):
    from urllib.request import Request, urlopen
    req = Request(
        url,
        headers={
            "User-Agent": "APP_WEB/1.0 (planner)"
        }
    )
    with urlopen(req, timeout=12) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _osm_geocode(address: str):
    if not address:
        return None
    addr = address.strip()
    if "portugal" not in addr.lower():
        addr = f"{addr}, Portugal"
    key = addr.lower().strip()
    if key in _osm_geocode_cache:
        return _osm_geocode_cache[key]
    from urllib.parse import quote
    postcode_match = re.search(r"\b\d{4}-\d{3}\b", addr)
    city = ''
    if ',' in addr:
        parts = [p.strip() for p in addr.split(',') if p.strip()]
        parts = [p for p in parts if p.lower() != 'portugal']
        if parts:
            city = parts[-1]
            if postcode_match:
                city = city.replace(postcode_match.group(0), '').strip()
    if postcode_match and city:
        postalcode = postcode_match.group(0)
        primary = f"{postalcode} {city}, Portugal"
        url = f"https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=pt&q={quote(primary)}"
    elif postcode_match:
        postalcode = postcode_match.group(0)
        primary = f"{postalcode}, Portugal"
        url = f"https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=pt&q={quote(primary)}"
    else:
        url = f"https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=pt&q={quote(addr)}"
    try:
        data = _osm_fetch_json(url)
        if not data:
            fallback_url = f"https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=pt&q={quote(addr)}"
            data = _osm_fetch_json(fallback_url)
        if not data:
            _osm_geocode_cache[key] = None
            return None
        lat = float(data[0]["lat"])
        lon = float(data[0]["lon"])
        _osm_geocode_cache[key] = (lat, lon)
        return lat, lon
    except Exception:
        _osm_geocode_cache[key] = None
        return None


def _osm_distance(addr_from: str, addr_to: str):
    if not addr_from or not addr_to:
        return None
    if addr_from.strip().lower() == addr_to.strip().lower():
        return {"km": 0.0, "seconds": 0}
    key = f"{addr_from}|||{addr_to}".lower().strip()
    if key in _osm_distance_cache:
        return _osm_distance_cache[key]
    coords_from = _osm_geocode(addr_from)
    coords_to = _osm_geocode(addr_to)
    if not coords_from or not coords_to:
        _osm_distance_cache[key] = None
        return None
    lat1, lon1 = coords_from
    lat2, lon2 = coords_to
    url = f"https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
    try:
        data = _osm_fetch_json(url)
        if not data or not data.get("routes"):
            _osm_distance_cache[key] = None
            return None
        route = data["routes"][0] or {}
        meters = route.get("distance", 0) or 0
        seconds = route.get("duration", 0) or 0
        km = round(float(meters) / 1000.0, 2)
        res = {"km": km, "seconds": int(seconds)}
        _osm_distance_cache[key] = res
        return res
    except Exception:
        _osm_distance_cache[key] = None
        return None


def _rotas_distance(orig_stamp: str, dest_stamp: str):
    if not orig_stamp or not dest_stamp:
        return None
    o = str(orig_stamp).strip()
    d = str(dest_stamp).strip()
    if not o or not d:
        return None
    if o == d:
        return {"km": 0.0, "seconds": 0}
    if o > d:
        o, d = d, o
    try:
        row = db.session.execute(text("""
            SELECT TOP 1 Km, Segundos
            FROM dbo.ROTAS
            WHERE OrigemStamp = :o AND DestinoStamp = :d
        """), {'o': o, 'd': d}).mappings().first()
        if not row:
            return None
        km = row.get("Km")
        seconds = row.get("Segundos")
        if km is None and seconds is None:
            return None
        return {
            "km": float(km or 0),
            "seconds": int(seconds or 0)
        }
    except Exception:
        return None


@bp.route("/api/osm_distances", methods=["POST"])
@login_required
def api_osm_distances():
    payload = request.get_json() or {}
    pairs = payload.get("pairs") or []
    results = {}
    for p in pairs:
        key = p.get("key") or ""
        from_stamp = (p.get("from_stamp") or p.get("fromStamp") or "").strip()
        to_stamp = (p.get("to_stamp") or p.get("toStamp") or "").strip()
        if from_stamp or to_stamp:
            if not key:
                a = from_stamp.lower().strip()
                b = to_stamp.lower().strip()
                key = f"{a}|||{b}" if a <= b else f"{b}|||{a}"
            rotas = _rotas_distance(from_stamp, to_stamp)
            results[key] = rotas
            continue
        addr_from = (p.get("from") or "").strip()
        addr_to = (p.get("to") or "").strip()
        if not key:
            key = f"{addr_from}|||{addr_to}".strip()
        results[key] = _osm_distance(addr_from, addr_to)
    return jsonify(results)

@bp.route('/api/update_campo', methods=['POST'])
@login_required
def update_campo():
    if not getattr(current_user, 'DEV', False):
        return jsonify(success=False, error="Acesso negado")

    data = request.get_json()
    tabela = data.get('tabela')
    campo  = data.get('campo')

    if not tabela or not campo:
        return jsonify(success=False, error="Tabela ou campo em falta")

    # Verifica que tipo de update vamos fazer
    updates = []
    params = {}

    if 'ordem' in data:
        updates.append("ORDEM = :ordem")
        params["ordem"] = data.get("ordem")

    if 'tam' in data:
        updates.append("TAM = :tam")
        params["tam"] = data.get("tam")

    if 'ordem_mobile' in data:
        updates.append("ORDEM_MOBILE = :ordem_mobile")
        params["ordem_mobile"] = data.get("ordem_mobile")

    if 'tam_mobile' in data:
        updates.append("TAM_MOBILE = :tam_mobile")
        params["tam_mobile"] = data.get("tam_mobile")

    if not updates:
        return jsonify(success=False, error="Nenhum campo para atualizar")

    sql = f"""
        UPDATE CAMPOS
        SET {', '.join(updates)}
        WHERE TABELA = :tabela AND NMCAMPO = :campo
    """

    params["tabela"] = tabela
    params["campo"] = campo

    try:
        db.session.execute(text(sql), params)
        db.session.commit()
        return jsonify(success=True)
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, error=str(e))


@bp.route('/api/tarefas/tratar', methods=['POST'])
@login_required
def tratar_tarefa():
    data = request.get_json()
    tarefa_id = data.get('id')

    if not tarefa_id:
        return jsonify({'error': 'Falta o ID da tarefa'}), 400

    try:
        # Regra: utilizadores com registo de tempos não podem concluir limpezas via monitor
        try:
            is_tempos = int(getattr(current_user, 'TEMPOS', 0) or 0) == 1
            is_admin = bool(getattr(current_user, 'ADMIN', False) or getattr(current_user, 'LPADMIN', False))
        except Exception:
            is_tempos = False
            is_admin = False

        if is_tempos and not is_admin:
            origem = db.session.execute(text("""
                SELECT UPPER(LTRIM(RTRIM(ISNULL(ORIGEM,'')))) AS ORIGEM
                FROM TAREFAS
                WHERE TAREFASSTAMP = :id
            """), {'id': tarefa_id}).scalar()
            if origem is None:
                return jsonify({'error': 'Tarefa não encontrada'}), 404
            if str(origem).upper() == 'LP':
                return jsonify({'error': 'A conclusão das limpezas deve ser feita no Registo de Limpezas.'}), 403

        sql = text("UPDATE TAREFAS SET TRATADO = 1 WHERE TAREFASSTAMP = :id")
        db.session.execute(sql, {'id': tarefa_id})
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/tarefas/reabrir', methods=['POST'])
@login_required
def reabrir_tarefa():
    data = request.get_json()
    tarefa_id = data.get('id')

    if not tarefa_id:
        return jsonify({'error': 'Falta o ID da tarefa'}), 400

    try:
        sql = text("""
            UPDATE TAREFAS
            SET TRATADO = 0,
                NMTRATADO = '',
                DTTRATADO = CAST('1900-01-01' AS date)
            WHERE TAREFASSTAMP = :id
        """)
        db.session.execute(sql, {'id': tarefa_id})
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

from flask import request, jsonify, abort
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import text

@bp.route('/api/monitor_tasks', methods=['GET'])
@login_required
def api_monitor_tasks():
    hoje = datetime.today().date()
    start = hoje - timedelta(days=7)
    end = hoje + timedelta(days=7)

    sql = text("""
    SELECT
      ta.TAREFASSTAMP,
      CONVERT(varchar(10), ta.DATA, 23) AS DATA,
      ta.HORA,
      ta.DURACAO,
      ta.TAREFA,
      ta.ALOJAMENTO,
      ta.UTILIZADOR,
      ta.ORIGEM,
      ta.ORISTAMP,
      ta.TRATADO,
      COALESCE(u.COR, tc.COR, eq.COR, '#333333') AS COR
    FROM TAREFAS ta
    LEFT JOIN US    u  ON u.LOGIN    = ta.UTILIZADOR
    LEFT JOIN TEC   tc ON tc.NOME    = u.TECNICO
    LEFT JOIN EQ    eq ON eq.NOME    = u.EQUIPA
    WHERE ta.DATA BETWEEN :start AND :end
      AND UPPER(ta.UTILIZADOR) = UPPER(:user)
    ORDER BY ta.DATA, ta.HORA
    """)

    rows = db.session.execute(sql, {
        'start': start.isoformat(),
        'end': end.isoformat(),
        'user': current_user.LOGIN
    }).mappings().all()

    tarefas = [dict(r) for r in rows]
    return jsonify(tarefas)


@bp.route('/api/mn_incidente', methods=['POST'])
@login_required
def criar_mn_incidente():
    """
    Endpoint dedicado para criar uma nova incidÃªncia na tabela MN
    Garante que o campo TRATADO Ã© sempre booleano.
    """
    from sqlalchemy import text
    import uuid
    data = request.get_json() or {}

    # Campos obrigatÃ³rios
    obrigatorios = ['ALOJAMENTO', 'DATA', 'NOME', 'INCIDENCIA']
    for campo in obrigatorios:
        if not data.get(campo):
            return jsonify({'error': f'Campo obrigatÃ³rio em falta: {campo}'}), 400

    # Campos automÃ¡ticos/defaults
    mnstamp = uuid.uuid4().hex[:25].upper()
    tratado = str(data.get('TRATADO', '0')).lower() in ['1', 'true', 'on']
    urgente = 1 if str(data.get('URGENTE', '0')).lower() in ['1','true','on'] else 0
    dttratado = data.get('DTTRATADO', None) or None
    nmtratado = data.get('NMTRATADO', '')
    dttratado = data.get('DTTRATADO') or '1900-01-01'

    scoped = _table_is_fe_scoped('MN')
    sql = text(f"""
        INSERT INTO MN (MNSTAMP, ALOJAMENTO, DATA, NOME, INCIDENCIA, URGENTE, TRATADO, DTTRATADO, NMTRATADO{', FEID' if scoped else ''})
        VALUES (:mnstamp, :alojamento, :data, :nome, :incidencia, :urgente, :tratado, :dttratado, :nmtratado{', :feid' if scoped else ''})
    """)
    try:
        params = {
            'mnstamp': mnstamp,
            'alojamento': data['ALOJAMENTO'],
            'data': data['DATA'],
            'nome': data['NOME'],
            'incidencia': data['INCIDENCIA'],
            'urgente': urgente,
            'tratado': tratado,
            'dttratado': dttratado,
            'nmtratado': nmtratado
        }
        if scoped:
            params['feid'] = MONITOR_DEFAULT_FEID
        db.session.execute(sql, params)
        db.session.commit()
        return jsonify({'success': True, 'MNSTAMP': mnstamp}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/fs_falta', methods=['POST'])
@login_required
def api_fs_falta():
    from sqlalchemy import text
    import uuid

    data = request.get_json() or {}
    obrig = ['ALOJAMENTO', 'DATA', 'USERNAME', 'ITEM']
    for c in obrig:
        if not data.get(c):
            return jsonify({'error': f'Campo obrigatÃ³rio em falta: {c}'}), 400

    fsstamp = uuid.uuid4().hex[:25].upper()

    urgente    = str(data.get('URGENTE', '0')).lower() in ('1','true','on')
    tratado    = str(data.get('TRATADO', '0')).lower() in ('1','true','on')
    tratadopor = data.get('TRATADOPOR') or ''
    dttratado  = data.get('DTTRATADO') or '1900-01-01'  # mantÃ©m alinhado com o teu default

    scoped = _table_is_fe_scoped('FS')
    sql = text(f"""
        INSERT INTO FS (FSSTAMP{', FEID' if scoped else ''}, ALOJAMENTO, DATA, USERNAME, ITEM, URGENTE, TRATADO, TRATADOPOR, DTTRATADO)
        VALUES (:FSSTAMP{', :FEID' if scoped else ''}, :ALOJAMENTO, :DATA, :USERNAME, :ITEM, :URGENTE, :TRATADO, :TRATADOPOR, :DTTRATADO)
    """)

    try:
        params = {
            'FSSTAMP': fsstamp,
            'ALOJAMENTO': data['ALOJAMENTO'],
            'DATA': data['DATA'],
            'USERNAME': data['USERNAME'],
            'ITEM': data['ITEM'],
            'URGENTE': 1 if urgente else 0,
            'TRATADO': 1 if tratado else 0,
            'TRATADOPOR': tratadopor,
            'DTTRATADO': dttratado
        }
        if scoped:
            params['FEID'] = MONITOR_DEFAULT_FEID
        db.session.execute(sql, params)
        db.session.commit()
        return jsonify({'success': True, 'FSSTAMP': fsstamp}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500



@bp.route('/api/profile/fields', methods=['GET'])
@login_required
def api_profile_fields():
    """
    Devolve os campos configurados para o formulÃ¡rio de perfil:
      - SÃ³ campos da tabela US
      - SÃ³ tipo ADMIN=1 na CAMPOS
      - Lista o nome, tipo, descriÃ§Ã£o
    """
    from app import db
    try:
        rows = db.session.execute(
            text("""
                SELECT nmcampo, tipo, descricao
                FROM CAMPOS
                WHERE tabela = 'US' AND admin = 1
                ORDER BY ordem
            """)
        ).fetchall()
        fields = [
            dict(zip(['nmcampo', 'tipo', 'descricao'], row))
            for row in rows
        ]
    except Exception as e:
        return {'error': str(e)}, 500

    return {'fields': fields}

from sqlalchemy import text

@bp.route("/api/tarefa_info/<stamp>")
@login_required
def tarefa_info(stamp):
    result = db.session.execute(
        db.text("SELECT dbo.info_tarefa(:stamp) AS info"),
        {"stamp": stamp}
    ).fetchone()
    
    return jsonify({"info": result.info if result else ""})

# === Monitor: ManutenÃ§Ãµes nÃ£o agendadas + Agendamento em TAREFAS =================
from sqlalchemy import text

@bp.route('/api/monitor/mn-nao-agendadas', methods=['GET'])
@login_required
def api_mn_nao_agendadas():
    """Lista MN por agendar (sem entrada em TAREFAS). SÃ³ para MNADMIN."""
    if not getattr(current_user, 'MNADMIN', 0):
        abort(403, 'Sem permissÃ£o de manutenÃ§Ã£o')

    sql = text("""
        SELECT 
          MNSTAMP,
          NOME,
          ALOJAMENTO,
          INCIDENCIA,
          ISNULL(URGENTE,0) AS URGENTE,
          CONVERT(varchar(10), DATA, 23) AS DATA
        FROM MN
        WHERE TRATADO = 0
          AND MNSTAMP NOT IN (
            SELECT ORISTAMP FROM TAREFAS
            WHERE UPPER(ISNULL(ORIGEM,'')) = 'MN'
          )
        ORDER BY DATA DESC, MNSTAMP
    """)
    rows = db.session.execute(sql).mappings().all()
    return jsonify({'rows': [dict(r) for r in rows]})

@bp.route('/api/monitor/proximos', methods=['GET'])
@login_required
def api_monitor_proximos():
    aloj = (request.args.get('alojamento') or '').strip()
    if not aloj:
        return jsonify({'error': 'Alojamento em falta'}), 400
    hoje = date.today().isoformat()
    out = {}
    try:
        rs_out = db.session.execute(text(
            """
            SELECT TOP 1 CONVERT(varchar(10), DATAOUT, 23) AS DATAOUT, HORAOUT
            FROM RS
            WHERE ALOJAMENTO = :aloj AND DATAOUT >= :hoje AND (CANCELADA = 0 OR CANCELADA IS NULL)
            ORDER BY DATAOUT, HORAOUT
            """
        ), { 'aloj': aloj, 'hoje': hoje }).mappings().first()
        if rs_out:
            out['rs_out'] = { 'DATAOUT': rs_out['DATAOUT'], 'HORAOUT': rs_out['HORAOUT'] }

        rs_in = db.session.execute(text(
            """
            SELECT TOP 1 CONVERT(varchar(10), DATAIN, 23) AS DATAIN, HORAIN
            FROM RS
            WHERE ALOJAMENTO = :aloj AND DATAIN >= :hoje AND (CANCELADA = 0 OR CANCELADA IS NULL)
            ORDER BY DATAIN, HORAIN
            """
        ), { 'aloj': aloj, 'hoje': hoje }).mappings().first()
        if rs_in:
            out['rs_in'] = { 'DATAIN': rs_in['DATAIN'], 'HORAIN': rs_in['HORAIN'] }

        lp = db.session.execute(text(
            """
            SELECT TOP 1 CONVERT(varchar(10), DATA, 23) AS DATA, HORA, EQUIPA
            FROM LP
            WHERE ALOJAMENTO = :aloj AND DATA >= :hoje
            ORDER BY DATA, HORA
            """
        ), { 'aloj': aloj, 'hoje': hoje }).mappings().first()
        if lp:
            out['lp'] = { 'DATA': lp['DATA'], 'HORA': lp['HORA'], 'EQUIPA': lp['EQUIPA'] }

        return jsonify(out)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/event/cursor_query', methods=['POST'])
@login_required
def event_cursor_query():
    try:
        payload = request.get_json(silent=True) or {}
        table_name = str(payload.get('table_name') or '').strip()
        if not table_name:
            return jsonify({'success': False, 'error': 'table_name em falta.'}), 400
        if not (
            getattr(current_user, 'ADMIN', False)
            or has_permission(table_name, 'consultar')
            or has_permission(table_name, 'editar')
            or has_permission(table_name, 'inserir')
        ):
            return jsonify({'success': False, 'error': 'Sem permissao para executar o cursor SQL neste ecra.'}), 403

        compiled_sql, param_names = _prepare_event_cursor_sql(payload.get('sql') or '')
        raw_params = payload.get('params') if isinstance(payload.get('params'), dict) else {}
        bind_params = {
            name: _normalize_event_cursor_param_value(raw_params.get(name))
            for name in param_names
        }

        result = db.session.execute(text(compiled_sql), bind_params)
        columns = [str(col) for col in result.keys()]
        rows = [
            {str(key): _event_cursor_json_value(value) for key, value in dict(row).items()}
            for row in result.mappings().all()
        ]
        return jsonify({
            'success': True,
            'columns': columns,
            'rows': rows,
        })
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception('Erro ao executar cursor SQL do editor de eventos')
        return jsonify({'success': False, 'error': str(exc)}), 500

@bp.route('/api/monitor/outs', methods=['GET'])
@login_required
def api_monitor_outs():
    aloj = (request.args.get('alojamento') or '').strip()
    if not aloj:
        return jsonify({'error': 'Alojamento em falta'}), 400
    hoje = date.today().isoformat()
    try:
        outs = db.session.execute(text(
            """
            SELECT TOP 10 CONVERT(varchar(10), DATAOUT, 23) AS DATAOUT, HORAOUT
            FROM RS
            WHERE ALOJAMENTO = :aloj AND DATAOUT >= :hoje AND (CANCELADA = 0 OR CANCELADA IS NULL)
            ORDER BY DATAOUT, HORAOUT
            """
        ), { 'aloj': aloj, 'hoje': hoje }).mappings().all()

        result = []
        for o in outs:
            dataout = o['DATAOUT']
            # próximo checkin após este checkout
            inrow = db.session.execute(text(
                """
                SELECT TOP 1 CONVERT(varchar(10), DATAIN, 23) AS DATAIN, HORAIN
                FROM RS
                WHERE ALOJAMENTO = :aloj AND DATAIN >= :dataout AND (CANCELADA = 0 OR CANCELADA IS NULL)
                ORDER BY DATAIN, HORAIN
                """
            ), { 'aloj': aloj, 'dataout': dataout }).mappings().first()
            # limpeza marcada para a data do checkout
            lprow = db.session.execute(text(
                """
                SELECT TOP 1 HORA, EQUIPA
                FROM LP
                WHERE ALOJAMENTO = :aloj AND DATA = :dataout
                ORDER BY HORA
                """
            ), { 'aloj': aloj, 'dataout': dataout }).mappings().first()

            result.append({
                'DATAOUT': o['DATAOUT'],
                'HORAOUT': o['HORAOUT'],
                'DATAIN': (inrow['DATAIN'] if inrow else None),
                'HORAIN': (inrow['HORAIN'] if inrow else None),
                'LPHORA': (lprow['HORA'] if lprow else None),
                'LPEQUIPA': (lprow['EQUIPA'] if lprow else None),
            })

        return jsonify({'rows': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/mn/<mnstamp>', methods=['GET'])
@login_required
def api_mn_get(mnstamp):
    try:
        row = db.session.execute(text(
            """
            SELECT TOP 1 MNSTAMP, NOME, ALOJAMENTO, INCIDENCIA,
                   CONVERT(varchar(10), DATA, 23) AS DATA
            FROM MN
            WHERE MNSTAMP = :id
            """
        ), { 'id': mnstamp }).mappings().first()
        if not row:
            return jsonify({'error': 'MN não encontrada'}), 404
        return jsonify(dict(row))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/monitor/fs-nao-agendadas', methods=['GET'])
@login_required
def api_fs_nao_agendadas():
    """Lista FS pendentes (sem entrada em TAREFAS)."""
    sql = text("""
        SELECT 
          FSSTAMP,
          ALOJAMENTO,
          USERNAME,
          ITEM,
          ISNULL(URGENTE,0) AS URGENTE,
          CONVERT(varchar(10), DATA, 23) AS DATA
        FROM FS
        WHERE TRATADO = 0
          AND FSSTAMP NOT IN (
            SELECT ORISTAMP FROM TAREFAS
            WHERE UPPER(ISNULL(ORIGEM,'')) = 'FS'
          )
        ORDER BY DATA DESC, FSSTAMP
    """)
    rows = db.session.execute(sql).mappings().all()
    return jsonify({'rows': [dict(r) for r in rows]})

@bp.route('/api/fs/tratar', methods=['POST'])
@login_required
def api_fs_tratar():
    data = request.get_json(silent=True) or {}
    fsstamp = data.get('FSSTAMP') or data.get('fsstamp')
    if not fsstamp:
        return jsonify({'ok': False, 'error': 'FSSTAMP em falta'}), 400

    # Permissão: LP admin ou permissão de editar FS
    allowed = getattr(current_user, 'LPADMIN', False) or has_permission('FS', 'editar') or getattr(current_user, 'ADMIN', False)
    if not allowed:
        return jsonify({'ok': False, 'error': 'Sem permissão'}), 403

    try:
        sql = text("""
            UPDATE FS
            SET TRATADO   = 1,
                NMTRATADO = :user,
                DTTRATADO = CAST(GETDATE() AS date)
            WHERE FSSTAMP = :stamp
        """)
        db.session.execute(sql, {'user': current_user.LOGIN, 'stamp': fsstamp})
        db.session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/tarefas/from-mn', methods=['POST'])
@login_required
def api_criar_tarefa_from_mn():
    """Cria uma TAREFA a partir de uma MN nÃ£o agendada."""
    if not getattr(current_user, 'MNADMIN', 0):
        abort(403, 'Sem permissÃ£o de manutenÃ§Ã£o')

    data = request.get_json() or {}
    mnstamp = data.get('MNSTAMP')
    data_str = data.get('DATA')   # YYYY-MM-DD
    hora_str = data.get('HORA')   # HH:MM

    if not mnstamp or not data_str or not hora_str:
        return jsonify({'ok': False, 'error': 'ParÃ¢metros obrigatÃ³rios: MNSTAMP, DATA, HORA'}), 400

    # Buscar incidÃªncia e alojamento da MN
    mn = db.session.execute(
        text("""
            SELECT 
              INCIDENCIA,
              ALOJAMENTO
            FROM MN
            WHERE MNSTAMP = :mnstamp
        """),
        {'mnstamp': mnstamp}
    ).fetchone()

    if not mn:
        return jsonify({'ok': False, 'error': 'MN nÃ£o encontrada'}), 404

    # Inserir na TAREFAS
    # Nota: a coluna chama-se DURACAO (conforme queries acima neste ficheiro)
    scoped = _table_is_fe_scoped('TAREFAS')
    ins = text(f"""
        INSERT INTO TAREFAS (
            TAREFASSTAMP, ORIGEM, ORISTAMP, UTILIZADOR,
            DATA, HORA, DURACAO, TAREFA, ALOJAMENTO, TRATADO
            {', FEID' if scoped else ''}
        )
        VALUES (
            LEFT(NEWID(), 25), 'MN', :oristamp, :utilizador,
            :data, :hora, :duracao, :tarefa, :alojamento, 0
            {', :feid' if scoped else ''}
        )
    """)
    try:
        # Utilizador alvo: respeita UTILIZADOR enviado, se presente; caso contrário, usa o utilizador autenticado
        req_util = (data.get('UTILIZADOR') or '').strip()
        utilizador_dest = req_util if req_util else getattr(current_user, 'LOGIN', None)
        params = {
            'oristamp':   mnstamp,
            'utilizador': utilizador_dest,
            'data':       data_str,
            'hora':       hora_str,
            'duracao':    60,
            'tarefa':     mn.INCIDENCIA,
            'alojamento': mn.ALOJAMENTO
        }
        if scoped:
            params['feid'] = MONITOR_DEFAULT_FEID
        db.session.execute(ins, params)
        db.session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


# --------------------------------------------------
# API: obter "pedido por" para tarefas de MN/FS
# --------------------------------------------------
@bp.route('/api/tarefa_requester', methods=['GET'])
@login_required
def tarefa_requester():
    try:
        origem = (request.args.get('origem') or '').strip().upper()
        oristamp = (request.args.get('oristamp') or '').strip()
        if origem not in ('MN','FS') or not oristamp:
            return jsonify({'utilizador': '', 'nome': ''})
        if origem == 'MN':
            sql = text("SELECT TOP 1 ISNULL(UTILIZADOR,'') AS UTILIZADOR FROM MN WHERE MNSTAMP = :s")
        else:
            # FS pode usar USERNAME em algumas bases; tenta ambos
            sql = text("SELECT TOP 1 ISNULL(UTILIZADOR, ISNULL(USERNAME,'')) AS UTILIZADOR FROM FS WHERE FSSTAMP = :s")
        row = db.session.execute(sql, {'s': oristamp}).fetchone()
        login = (row[0] if row else '') or ''
        nome = ''
        if login:
            try:
                r2 = db.session.execute(text("SELECT TOP 1 ISNULL(NOME,'') FROM US WHERE LOGIN = :u"), {'u': login}).fetchone()
                nome = (r2[0] if r2 else '') or ''
            except Exception:
                nome = ''
        return jsonify({'utilizador': login, 'nome': nome})
    except Exception as e:
        return jsonify({'utilizador': '', 'nome': '', 'error': str(e) }), 500
