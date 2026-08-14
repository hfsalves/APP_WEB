from __future__ import annotations

import re
import uuid
from datetime import date, datetime, timedelta
from functools import lru_cache
from typing import Any

from flask_login import current_user
from sqlalchemy import text

from models import db
from services.multiempresa_service import MissingCurrentEntityError, get_current_feid


class LaundrySupportError(Exception):
    pass


def _stamp() -> str:
    return uuid.uuid4().hex.upper()[:25]


def _text(value: Any, limit: int | None = None) -> str:
    result = str(value or '').strip()
    return result[:limit] if limit else result


def _current_feid() -> int:
    try:
        return int(get_current_feid() or 0)
    except MissingCurrentEntityError:
        return 0


def _is_admin() -> bool:
    return bool(getattr(current_user, 'ADMIN', False) or getattr(current_user, 'DEV', False))


@lru_cache(maxsize=32)
def _table_columns(table_name: str) -> frozenset[str]:
    rows = db.session.execute(text("""
        SELECT UPPER(COLUMN_NAME)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = :table_name
    """), {'table_name': table_name.upper()}).fetchall()
    return frozenset(str(row[0] or '').strip().upper() for row in rows if row and row[0])


def ensure_laundry_support_menu() -> None:
    """Expose laundry support next to the cleaning planner, with the same module access."""
    row = db.session.execute(text("""
        SELECT TOP 1 MENUSTAMP
        FROM dbo.MENU
        WHERE LTRIM(RTRIM(ISNULL(URL, ''))) = '/apoio-lavandaria'
    """)).scalar()
    menu_stamp = _text(row, 25)
    if not menu_stamp:
        menu_stamp = _stamp()
        db.session.execute(text("""
            INSERT INTO dbo.MENU (
                MENUSTAMP, ORDEM, NOME, TABELA, URL, ADMIN, ICONE, FORM, ORDERBY, NOVO, INATIVO
            ) VALUES (
                :stamp, 61, 'Lavandaria', 'LP', '/apoio-lavandaria', 0,
                'fa-solid fa-shirt', '', '', 0, 0
            )
        """), {'stamp': menu_stamp})

    planner_module = db.session.execute(text("""
        SELECT TOP 1 MODSTAMP
        FROM dbo.MOD_OBJETOS
        WHERE MENUSTAMP = '4C7B14B8-13A3-497F-9018-A'
          AND ISNULL(ATIVO, 0) = 1
    """)).scalar()
    if planner_module:
        existing = db.session.execute(text("""
            SELECT TOP 1 1
            FROM dbo.MOD_OBJETOS
            WHERE MENUSTAMP = :menu_stamp
        """), {'menu_stamp': menu_stamp}).scalar()
        if not existing:
            db.session.execute(text("""
                INSERT INTO dbo.MOD_OBJETOS (
                    MODOBJSTAMP, MODSTAMP, TIPO, OBJKEY, OBJNOME, OBJROTA, MENUSTAMP,
                    ORDEM, ATIVO, DTCRI, USERCRIACAO, USERALTERACAO
                ) VALUES (
                    :object_stamp, :module_stamp, 'MENU', 'APOIO_LAVANDARIA',
                    'Lavandaria', '/apoio-lavandaria', :menu_stamp,
                    61, 1, GETDATE(), 'APP', 'APP'
                )
            """), {
                'object_stamp': _stamp(),
                'module_stamp': _text(planner_module, 25),
                'menu_stamp': menu_stamp,
            })
    db.session.commit()


def parse_period(data_ini_raw: str | None, data_fim_raw: str | None) -> tuple[date, date]:
    today = date.today()
    default_start = today
    default_end = today + timedelta(days=6)

    def parse(value: str | None, default: date) -> date:
        raw = _text(value, 10)
        if not raw:
            return default
        try:
            return datetime.strptime(raw, '%Y-%m-%d').date()
        except ValueError as exc:
            raise LaundrySupportError('Indica datas válidas para o período.') from exc

    data_ini = parse(data_ini_raw, default_start)
    data_fim = parse(data_fim_raw, default_end)
    if data_fim < data_ini:
        raise LaundrySupportError('A data final não pode ser anterior à data inicial.')
    if (data_fim - data_ini).days > 62:
        raise LaundrySupportError('Escolhe um período até 63 dias.')
    return data_ini, data_fim


def _to_int(value: Any) -> int:
    try:
        return max(0, int(float(value or 0)))
    except (TypeError, ValueError):
        return 0


def _base_beds(tipologia: str, lotacao: int) -> int:
    """Return the fixed beds to make, using the initial GuestSpa rules."""
    normalized = re.sub(r'\s+', '', _text(tipologia).upper())
    match = re.search(r'T(\d+)', normalized)
    type_number = int(match.group(1)) if match else 0

    if type_number == 0:
        return 1
    if type_number == 1:
        # T1s with capacity 4 or 5 have two double beds. A sofa bed is only
        # added when the specific check-in reservation requests it.
        return 2 if lotacao >= 4 else 1
    return max(1, type_number)


def _linen_for_cleaning(tipologia: str, lotacao: int, sofa_cama: bool) -> dict[str, int]:
    camas = _base_beds(tipologia, lotacao)
    sofa = 1 if sofa_cama else 0
    superficies = camas + sofa
    return {
        'camas': camas,
        'sofa_cama': sofa,
        'lencois': superficies,
        'capas': superficies,
        'fronhas': superficies * 2,
        'toalhas_rosto': superficies * 2,
        'toalhas_banho': superficies * 2,
    }


def _scope_sql(lp_cols: frozenset[str], al_cols: frozenset[str], current_feid: int) -> tuple[str, dict[str, int]]:
    if not current_feid or _is_admin():
        return '', {}
    parts: list[str] = []
    if 'FEID' in lp_cols:
        parts.append('ISNULL(LP.FEID, 0) = :current_feid')
    if 'FEID' in al_cols:
        parts.append('ISNULL(AL.FEID, 0) = :current_feid')
    if 'FEID_GESTOR' in al_cols:
        parts.append('ISNULL(AL.FEID_GESTOR, 0) = :current_feid')
    if not parts:
        return '', {}
    return f"AND ({' OR '.join(parts)})", {'current_feid': current_feid}


def laundry_plan(data_ini: date, data_fim: date) -> dict[str, Any]:
    lp_cols = _table_columns('LP')
    al_cols = _table_columns('AL')
    rs_cols = _table_columns('RS')
    required = {'DATA', 'ALOJAMENTO'}
    if not required.issubset(lp_cols):
        raise LaundrySupportError('A tabela de limpezas não tem os campos necessários.')
    if not {'NOME', 'TIPOLOGIA'}.issubset(al_cols):
        raise LaundrySupportError('A tabela de alojamentos não tem os campos necessários.')

    lotacao_column = 'LOTADULTOS' if 'LOTADULTOS' in al_cols else ('LOTACAO' if 'LOTACAO' in al_cols else '')
    lotacao_sql = f'CAST(ISNULL(AL.{lotacao_column}, 0) AS int)' if lotacao_column else '0'
    rs_sofa_sql = 'ISNULL(RS.SOFACAMA, 0)' if 'SOFACAMA' in rs_cols else '0'
    rs_code_sql = "LTRIM(RTRIM(ISNULL(RS.RESERVA, '')))" if 'RESERVA' in rs_cols else "''"
    rs_name_sql = "LTRIM(RTRIM(ISNULL(RS.NOME, '')))" if 'NOME' in rs_cols else "''"
    rs_stamp_sql = "LTRIM(RTRIM(ISNULL(RS.RSSTAMP, '')))" if 'RSSTAMP' in rs_cols else "''"
    cancelled_sql = 'AND ISNULL(RS.CANCELADA, 0) = 0' if 'CANCELADA' in rs_cols else ''
    lp_stamp_sql = "LTRIM(RTRIM(ISNULL(LP.LPSTAMP, '')))" if 'LPSTAMP' in lp_cols else "''"
    hour_sql = "LTRIM(RTRIM(ISNULL(LP.HORA, '')))" if 'HORA' in lp_cols else "''"
    finished_sql = 'ISNULL(LP.TERMINADA, 0)' if 'TERMINADA' in lp_cols else '0'
    scope_sql, scope_params = _scope_sql(lp_cols, al_cols, _current_feid())
    active_sql = ''
    if 'INATIVO' in al_cols:
        active_sql += ' AND ISNULL(AL.INATIVO, 0) = 0'
    if 'FECHADO' in al_cols:
        active_sql += ' AND ISNULL(AL.FECHADO, 0) = 0'

    rows = db.session.execute(text(f"""
        SELECT
            {lp_stamp_sql} AS LPSTAMP,
            CAST(LP.DATA AS date) AS DATA,
            {hour_sql} AS HORA,
            LTRIM(RTRIM(ISNULL(LP.ALOJAMENTO, ''))) AS ALOJAMENTO,
            LTRIM(RTRIM(ISNULL(AL.TIPOLOGIA, ''))) AS TIPOLOGIA,
            {lotacao_sql} AS LOTACAO,
            {finished_sql} AS TERMINADA,
            CI.RESERVA,
            CI.HOSPEDE,
            CI.SOFACAMA
        FROM dbo.LP AS LP
        INNER JOIN dbo.AL AS AL
          ON UPPER(LTRIM(RTRIM(ISNULL(AL.NOME, '')))) = UPPER(LTRIM(RTRIM(ISNULL(LP.ALOJAMENTO, ''))))
        OUTER APPLY (
            SELECT TOP 1
                {rs_code_sql} AS RESERVA,
                {rs_name_sql} AS HOSPEDE,
                {rs_sofa_sql} AS SOFACAMA
            FROM dbo.RS AS RS
            WHERE UPPER(LTRIM(RTRIM(ISNULL(RS.ALOJAMENTO, '')))) = UPPER(LTRIM(RTRIM(ISNULL(LP.ALOJAMENTO, ''))))
              AND CAST(RS.DATAIN AS date) = CAST(LP.DATA AS date)
              {cancelled_sql}
            ORDER BY RS.DATAIN, {rs_stamp_sql}
        ) AS CI
        WHERE CAST(LP.DATA AS date) BETWEEN :data_ini AND :data_fim
          AND LTRIM(RTRIM(ISNULL(LP.ALOJAMENTO, ''))) <> ''
          {active_sql}
          {scope_sql}
        ORDER BY CAST(LP.DATA AS date), {hour_sql}, LTRIM(RTRIM(ISNULL(LP.ALOJAMENTO, '')))
    """), {
        'data_ini': data_ini,
        'data_fim': data_fim,
        **scope_params,
    }).mappings().all()

    totals = {
        'limpezas': 0,
        'lencois': 0,
        'capas': 0,
        'fronhas': 0,
        'toalhas_rosto': 0,
        'toalhas_banho': 0,
    }
    days_by_key: dict[str, dict[str, Any]] = {}
    for row in rows:
        row_date = row.get('DATA')
        if not isinstance(row_date, date):
            continue
        pieces = _linen_for_cleaning(
            _text(row.get('TIPOLOGIA')),
            _to_int(row.get('LOTACAO')),
            bool(_to_int(row.get('SOFACAMA'))),
        )
        key = row_date.isoformat()
        day = days_by_key.setdefault(key, {
            'data': key,
            'limpezas': 0,
            'lencois': 0,
            'capas': 0,
            'fronhas': 0,
            'toalhas_rosto': 0,
            'toalhas_banho': 0,
            'items': [],
        })
        item = {
            'lpstamp': _text(row.get('LPSTAMP')),
            'hora': _text(row.get('HORA')),
            'alojamento': _text(row.get('ALOJAMENTO')),
            'tipologia': _text(row.get('TIPOLOGIA')),
            'lotacao': _to_int(row.get('LOTACAO')),
            'terminada': bool(_to_int(row.get('TERMINADA'))),
            'reserva': _text(row.get('RESERVA')),
            'hospede': _text(row.get('HOSPEDE')),
            **pieces,
        }
        day['items'].append(item)
        day['limpezas'] += 1
        totals['limpezas'] += 1
        for piece in ('lencois', 'capas', 'fronhas', 'toalhas_rosto', 'toalhas_banho'):
            day[piece] += pieces[piece]
            totals[piece] += pieces[piece]

    return {
        'data_ini': data_ini.isoformat(),
        'data_fim': data_fim.isoformat(),
        'totals': totals,
        'days': list(days_by_key.values()),
    }
