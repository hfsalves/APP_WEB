from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pyodbc
from sqlalchemy import text

from models import db
from services.colaborador_despesas_service import get_colaborador_context, _phc_conn_str


def _safe_year(value: Any) -> int:
    try:
        year = int(value or date.today().year)
    except Exception:
        year = date.today().year
    return year if 2000 <= year <= 2100 else date.today().year


def _new_stamp() -> str:
    return uuid.uuid4().hex.upper()[:25]


def ensure_colaborador_ferias_schema() -> None:
    db.session.execute(text("""
        IF OBJECT_ID('dbo.COLAB_FERIAS_PEDIDO_DESMARCAR', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.COLAB_FERIAS_PEDIDO_DESMARCAR (
                PEDIDOSTAMP varchar(25) NOT NULL
                    CONSTRAINT PK_COLAB_FERIAS_PEDIDO_DESMARCAR PRIMARY KEY,
                USSTAMP varchar(25) NOT NULL
                    CONSTRAINT DF_COLAB_FERIAS_PEDIDO_USSTAMP DEFAULT '',
                LOGIN varchar(60) NOT NULL
                    CONSTRAINT DF_COLAB_FERIAS_PEDIDO_LOGIN DEFAULT '',
                PENO int NOT NULL
                    CONSTRAINT DF_COLAB_FERIAS_PEDIDO_PENO DEFAULT 0,
                PENOME nvarchar(160) NOT NULL
                    CONSTRAINT DF_COLAB_FERIAS_PEDIDO_PENOME DEFAULT N'',
                PEFEID int NOT NULL
                    CONSTRAINT DF_COLAB_FERIAS_PEDIDO_PEFEID DEFAULT 0,
                PHC_DB varchar(128) NOT NULL
                    CONSTRAINT DF_COLAB_FERIAS_PEDIDO_PHCDB DEFAULT '',
                PHC_SERVER varchar(128) NOT NULL
                    CONSTRAINT DF_COLAB_FERIAS_PEDIDO_PHCSERVER DEFAULT '',
                FPSTAMP varchar(25) NOT NULL
                    CONSTRAINT DF_COLAB_FERIAS_PEDIDO_FPSTAMP DEFAULT '',
                DATA_FERIAS date NOT NULL,
                ESTADO varchar(20) NOT NULL
                    CONSTRAINT DF_COLAB_FERIAS_PEDIDO_ESTADO DEFAULT 'PENDENTE',
                DTCRI datetime NOT NULL
                    CONSTRAINT DF_COLAB_FERIAS_PEDIDO_DTCRI DEFAULT GETDATE(),
                DTALT datetime NULL,
                USERCRIACAO varchar(60) NOT NULL
                    CONSTRAINT DF_COLAB_FERIAS_PEDIDO_USERCRI DEFAULT '',
                USERALTERACAO varchar(60) NOT NULL
                    CONSTRAINT DF_COLAB_FERIAS_PEDIDO_USERALT DEFAULT ''
            );

            CREATE INDEX IX_COLAB_FERIAS_PEDIDO_COLAB_ESTADO
                ON dbo.COLAB_FERIAS_PEDIDO_DESMARCAR (PENO, PHC_DB, ESTADO, DATA_FERIAS);
        END
    """))
    db.session.commit()


def _date_value(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _fp_columns(cursor) -> set[str]:
    cursor.execute("""
        SELECT LOWER(COLUMN_NAME) AS COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo'
          AND TABLE_NAME = 'FP'
    """)
    return {str(row[0] or "").strip().lower() for row in cursor.fetchall()}


def _period_days(start: date, end: date, year: int) -> list[str]:
    min_day = date(year, 1, 1)
    max_day = date(year, 12, 31)
    current = max(start, min_day)
    last = min(end, max_day)
    days: list[str] = []
    while current <= last:
        days.append(current.isoformat())
        current += timedelta(days=1)
    return days


def _date_from_mmdd(year: int, value: Any) -> date | None:
    try:
        raw = int(value or 0)
    except Exception:
        return None
    if raw <= 0:
        return None
    month = raw // 100
    day = raw % 100
    try:
        return date(year, month, day)
    except Exception:
        return None


def _holiday_days(cursor, year: int) -> set[str]:
    cursor.execute("SELECT OBJECT_ID('dbo.FF','U')")
    if not cursor.fetchone()[0]:
        return set()
    cursor.execute("""
        SELECT DATA, DATAF, ISNULL(FIXO, 0) AS FIXO, ISNULL(DIAI, 0) AS DIAI, ISNULL(DIAF, 0) AS DIAF
        FROM dbo.FF
        WHERE (
            ISNULL(FIXO, 0) = 1
            AND ISNULL(DIAI, 0) > 0
        )
        OR (
            ISNULL(FIXO, 0) = 0
            AND DATAF >= ?
            AND DATA <= ?
        )
    """, date(year, 1, 1), date(year, 12, 31))
    days: set[str] = set()
    for row in cursor.fetchall():
        if bool(row.FIXO):
            start = _date_from_mmdd(year, row.DIAI)
            end = _date_from_mmdd(year, row.DIAF) or start
        else:
            start = _date_value(row.DATA)
            end = _date_value(row.DATAF) or start
        if not start or not end:
            continue
        if end < start:
            start, end = end, start
        days.update(_period_days(start, end, year))
    return days


def _working_vacation_days(start: date, end: date, year: int, holidays: set[str]) -> list[str]:
    return [
        day_key
        for day_key in _period_days(start, end, year)
        if date.fromisoformat(day_key).weekday() < 5 and day_key not in holidays
    ]


def _pending_unmark_request_days(colaborador: dict[str, Any], year: int) -> set[str]:
    ensure_colaborador_ferias_schema()
    rows = db.session.execute(text("""
        SELECT DATA_FERIAS
        FROM dbo.COLAB_FERIAS_PEDIDO_DESMARCAR
        WHERE PENO = :peno
          AND PHC_DB = :phc_db
          AND ESTADO = 'PENDENTE'
          AND DATA_FERIAS >= :date_start
          AND DATA_FERIAS <= :date_end
    """), {
        'peno': int(colaborador.get('peno') or 0),
        'phc_db': str(colaborador.get('phc_db') or '').strip(),
        'date_start': date(year, 1, 1),
        'date_end': date(year, 12, 31),
    }).scalars().all()
    return {
        value.isoformat()
        for value in rows
        if isinstance(value, date)
    }


def list_colaborador_ferias(user, year: int | str | None = None) -> dict[str, Any]:
    target_year = _safe_year(year)
    colaborador = get_colaborador_context(user)
    phc_db = str(colaborador.get("phc_db") or "").strip()
    phc_server = str(colaborador.get("phc_server") or "").strip()
    peno = int(colaborador.get("peno") or 0)
    result = {
        "ok": True,
        "year": target_year,
        "colaborador": colaborador,
        "vacation_days": [],
        "pending_vacation_days": [],
        "unmark_request_days": [],
        "holiday_days": [],
        "periods": [],
        "marked_days": 0,
        "holiday_count": 0,
        "working_days": 0,
        "warning": "",
    }
    if not peno or not phc_db:
        result["warning"] = "Ficha de colaborador incompleta."
        return result

    year_start = date(target_year, 1, 1)
    year_end = date(target_year, 12, 31)
    try:
        with pyodbc.connect(_phc_conn_str(phc_db, phc_server), timeout=15) as conn:
            cursor = conn.cursor()
            columns = _fp_columns(cursor)
            required = {"no", "datai", "dataf"}
            missing = sorted(required - columns)
            if missing:
                result["warning"] = f"Campos em falta na FP: {', '.join(missing)}"
                return result
            holidays = _holiday_days(cursor, target_year)
            rejected_filter = "AND ISNULL(U_REJEITA, 0) = 0" if "u_rejeita" in columns else ""
            validado_select = "ISNULL(U_VALIDADO, 0) AS U_VALIDADO," if "u_validado" in columns else "CAST(0 AS bit) AS U_VALIDADO,"
            enviado_select = "ISNULL(U_ENVIADO, 0) AS U_ENVIADO," if "u_enviado" in columns else "CAST(0 AS bit) AS U_ENVIADO,"
            rows = cursor.execute(f"""
                SELECT
                    LTRIM(RTRIM(ISNULL(FPSTAMP, ''))) AS FPSTAMP,
                    NO,
                    DATAI,
                    DATAF,
                    LTRIM(RTRIM(ISNULL(ANO, ''))) AS ANO,
                    ISNULL(DIAS, 0) AS DIAS,
                    ISNULL(FECHADO, 0) AS FECHADO,
                    ISNULL(MARCADA, 0) AS MARCADA,
                    ISNULL(PROCESSADA, 0) AS PROCESSADA,
                    {validado_select}
                    {enviado_select}
                    LTRIM(RTRIM(ISNULL(OBS, ''))) AS OBS
                FROM dbo.FP
                WHERE NO = ?
                  AND DATAF >= ?
                  AND DATAI <= ?
                  {rejected_filter}
                ORDER BY DATAI, DATAF
            """, peno, year_start, year_end).fetchall()
    except Exception as exc:
        result["warning"] = f"Erro ao ler férias no PHC: {exc}"
        return result

    days: set[str] = set()
    pending_days: set[str] = set()
    periods: list[dict[str, Any]] = []
    working_days = Decimal("0")
    for row in rows:
        start = _date_value(row.DATAI)
        end = _date_value(row.DATAF)
        if not start or not end:
            continue
        if end < start:
            start, end = end, start
        period_days = _working_vacation_days(start, end, target_year, holidays)
        if bool(row.FECHADO):
            days.update(period_days)
        else:
            pending_days.update(period_days)
        try:
            working_days += Decimal(str(row.DIAS or 0))
        except Exception:
            pass
        periods.append({
            "fpstamp": str(row.FPSTAMP or "").strip(),
            "datai": start.isoformat(),
            "dataf": end.isoformat(),
            "ano": str(row.ANO or "").strip(),
            "dias": float(row.DIAS or 0),
            "fechado": bool(row.FECHADO),
            "marcada": bool(row.MARCADA),
            "processada": bool(row.PROCESSADA),
            "validado": bool(row.U_VALIDADO),
            "enviado": bool(row.U_ENVIADO),
            "obs": str(row.OBS or "").strip(),
        })

    pending_days.difference_update(days)
    result["vacation_days"] = sorted(days)
    result["pending_vacation_days"] = sorted(pending_days)
    result["holiday_days"] = sorted(holidays)
    result["unmark_request_days"] = sorted(_pending_unmark_request_days(colaborador, target_year))
    result["periods"] = periods
    result["marked_days"] = len(days) + len(pending_days)
    result["holiday_count"] = len(holidays)
    result["working_days"] = float(working_days)
    return result


def _parse_days(values: Any, year: int) -> set[date]:
    if not isinstance(values, list):
        return set()
    parsed: set[date] = set()
    for value in values:
        try:
            parsed_day = date.fromisoformat(str(value or '').strip())
        except ValueError:
            continue
        if parsed_day.year == year:
            parsed.add(parsed_day)
    return parsed


def _fp_rows(cursor, peno: int, year: int) -> list[dict[str, Any]]:
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    rows = cursor.execute("""
        SELECT
            LTRIM(RTRIM(ISNULL(FPSTAMP, ''))) AS FPSTAMP,
            NO,
            DATAI,
            DATAF,
            LTRIM(RTRIM(ISNULL(ANO, ''))) AS ANO,
            ISNULL(FECHADO, 0) AS FECHADO,
            LTRIM(RTRIM(ISNULL(PESTAMP, ''))) AS PESTAMP
        FROM dbo.FP
        WHERE NO = ?
          AND DATAF >= ?
          AND DATAI <= ?
          AND ISNULL(U_REJEITA, 0) = 0
        ORDER BY DATAI, DATAF
    """, peno, start, end).fetchall()
    return [
        {
            'fpstamp': str(row.FPSTAMP or '').strip(),
            'datai': _date_value(row.DATAI),
            'dataf': _date_value(row.DATAF),
            'ano': str(row.ANO or '').strip(),
            'fechado': bool(row.FECHADO),
            'pestamp': str(row.PESTAMP or '').strip(),
        }
        for row in rows
        if _date_value(row.DATAI) and _date_value(row.DATAF)
    ]


def _contiguous_ranges(days: set[date], holidays: set[str]) -> list[tuple[date, date]]:
    if not days:
        return []
    ordered = sorted(days)
    ranges: list[tuple[date, date]] = []
    start = ordered[0]
    previous = ordered[0]
    for current in ordered[1:]:
        between = previous + timedelta(days=1)
        can_join = True
        while between < current:
            if between.weekday() < 5 and between.isoformat() not in holidays:
                can_join = False
                break
            between += timedelta(days=1)
        if not can_join:
            ranges.append((start, previous))
            start = current
        previous = current
    ranges.append((start, previous))
    return ranges


def _calendar_ranges_without_days(start: date, end: date, excluded: set[date]) -> list[tuple[date, date]]:
    ranges: list[tuple[date, date]] = []
    current_start: date | None = None
    current = start
    while current <= end:
        if current in excluded:
            if current_start:
                ranges.append((current_start, current - timedelta(days=1)))
                current_start = None
        elif not current_start:
            current_start = current
        current += timedelta(days=1)
    if current_start:
        ranges.append((current_start, end))
    return ranges


def _insert_pending_fp(cursor, columns: set[str], *, peno: int, pestamp: str, start: date, end: date, ano: str, holidays: set[str], login: str) -> None:
    work_days = len(_working_vacation_days(start, end, start.year, holidays))
    if not work_days:
        return
    now = datetime.now()
    values = {
        'fpstamp': _new_stamp(),
        'no': peno,
        'datai': start,
        'dataf': end,
        'ano': (ano or str(start.year))[:4],
        'dias': work_days,
        'pmes': start.month,
        'pano': start.year,
        'fechado': 0,
        'pestamp': pestamp,
        'pesupstampfe': '',
        'obs': '',
        'processada': 0,
        'prstamp': '',
        'ousrinis': login[:30],
        'ousrdata': now,
        'ousrhora': now.strftime('%H:%M:%S'),
        'usrinis': login[:30],
        'usrdata': now,
        'usrhora': now.strftime('%H:%M:%S'),
        'marcada': 0,
        'isfpadmissao': 0,
        'pesupnomefe': '',
        'absstamp': '',
        'naofaltas': '',
        'ismdias': 0,
        'horai': '',
        'horaf': '',
        'u_enviado': 0,
        'u_rejeita': 0,
        'u_validado': 0,
    }
    selected = {key: value for key, value in values.items() if key in columns}
    cursor.execute(
        f"INSERT INTO dbo.FP ({', '.join('[' + key + ']' for key in selected)}) "
        f"VALUES ({', '.join('?' for _ in selected)})",
        list(selected.values()),
    )


def apply_colaborador_ferias_changes(user, payload: dict[str, Any]) -> dict[str, Any]:
    ensure_colaborador_ferias_schema()
    year = _safe_year(payload.get('year'))
    colaborador = get_colaborador_context(user)
    peno = int(colaborador.get('peno') or 0)
    phc_db = str(colaborador.get('phc_db') or '').strip()
    phc_server = str(colaborador.get('phc_server') or '').strip()
    if not peno or not phc_db:
        raise ValueError('Ficha de colaborador incompleta.')

    add_days = _parse_days(payload.get('add_days'), year)
    remove_pending_days = _parse_days(payload.get('remove_pending_days'), year)
    request_approved_unmark_days = _parse_days(payload.get('request_approved_unmark_days'), year)
    if not (add_days or remove_pending_days or request_approved_unmark_days):
        raise ValueError('Não existem alterações para gravar.')

    login = str(colaborador.get('login') or '').strip()
    userstamp = str(colaborador.get('userstamp') or '').strip()
    with pyodbc.connect(_phc_conn_str(phc_db, phc_server), timeout=15) as conn:
        cursor = conn.cursor()
        columns = _fp_columns(cursor)
        if not {'fpstamp', 'no', 'datai', 'dataf', 'fechado', 'pestamp'}.issubset(columns):
            raise ValueError('A tabela FP não tem os campos necessários para marcar férias.')
        holidays = _holiday_days(cursor, year)
        invalid_days = {
            day for day in add_days | remove_pending_days | request_approved_unmark_days
            if day.weekday() >= 5 or day.isoformat() in holidays
        }
        if invalid_days:
            raise ValueError('Só é possível alterar dias úteis que não sejam feriados.')

        employee = cursor.execute("""
            SELECT TOP 1 LTRIM(RTRIM(ISNULL(PESTAMP, ''))) AS PESTAMP
            FROM dbo.PE
            WHERE NO = ?
        """, peno).fetchone()
        if not employee:
            raise ValueError('Colaborador não encontrado na tabela PE do PHC.')
        employee_stamp = str(employee.PESTAMP or '').strip()
        rows = _fp_rows(cursor, peno, year)

        approved_days: dict[date, str] = {}
        pending_rows: list[dict[str, Any]] = []
        pending_days: set[date] = set()
        for row in rows:
            start = row['datai']
            end = row['dataf']
            if not start or not end:
                continue
            work_days = {date.fromisoformat(key) for key in _working_vacation_days(start, end, year, holidays)}
            if row['fechado']:
                approved_days.update({day: row['fpstamp'] for day in work_days})
            else:
                pending_rows.append(row)
                pending_days.update(work_days)

        if add_days & (set(approved_days) | pending_days):
            raise ValueError('Existem dias selecionados que já estão marcados.')
        if remove_pending_days - pending_days:
            raise ValueError('Só pode desmarcar férias que estejam pendentes de aprovação.')
        if request_approved_unmark_days - set(approved_days):
            raise ValueError('Só pode pedir a desmarcação de férias aprovadas.')

        for row in pending_rows:
            start = row['datai']
            end = row['dataf']
            if not start or not end:
                continue
            row_work_days = {date.fromisoformat(key) for key in _working_vacation_days(start, end, year, holidays)}
            removed_from_row = remove_pending_days & row_work_days
            if not removed_from_row:
                continue
            cursor.execute('DELETE FROM dbo.FP WHERE FPSTAMP = ?', row['fpstamp'])
            for range_start, range_end in _calendar_ranges_without_days(start, end, removed_from_row):
                _insert_pending_fp(
                    cursor,
                    columns,
                    peno=peno,
                    pestamp=row['pestamp'] or employee_stamp,
                    start=range_start,
                    end=range_end,
                    ano=row['ano'],
                    holidays=holidays,
                    login=login,
                )

        for range_start, range_end in _contiguous_ranges(add_days, holidays):
            _insert_pending_fp(
                cursor,
                columns,
                peno=peno,
                pestamp=employee_stamp,
                start=range_start,
                end=range_end,
                ano=str(year),
                holidays=holidays,
                login=login,
            )
        conn.commit()

    created_requests = 0
    for day in sorted(request_approved_unmark_days):
        fpstamp = approved_days.get(day, '')
        existing = db.session.execute(text("""
            SELECT 1
            FROM dbo.COLAB_FERIAS_PEDIDO_DESMARCAR
            WHERE PENO = :peno
              AND PHC_DB = :phc_db
              AND FPSTAMP = :fpstamp
              AND DATA_FERIAS = :data_ferias
              AND ESTADO = 'PENDENTE'
        """), {
            'peno': peno,
            'phc_db': phc_db,
            'fpstamp': fpstamp,
            'data_ferias': day,
        }).scalar()
        if existing:
            continue
        db.session.execute(text("""
            INSERT INTO dbo.COLAB_FERIAS_PEDIDO_DESMARCAR
            (PEDIDOSTAMP, USSTAMP, LOGIN, PENO, PENOME, PEFEID, PHC_DB, PHC_SERVER,
             FPSTAMP, DATA_FERIAS, ESTADO, USERCRIACAO, USERALTERACAO)
            VALUES
            (:stamp, :userstamp, :login, :peno, :penome, :pefeid, :phc_db, :phc_server,
             :fpstamp, :data_ferias, 'PENDENTE', :login, :login)
        """), {
            'stamp': _new_stamp(),
            'userstamp': userstamp,
            'login': login,
            'peno': peno,
            'penome': str(colaborador.get('penome') or '').strip(),
            'pefeid': int(colaborador.get('pefeid') or 0),
            'phc_db': phc_db,
            'phc_server': phc_server,
            'fpstamp': fpstamp,
            'data_ferias': day,
        })
        created_requests += 1
    db.session.commit()
    return {
        'ok': True,
        'added': len(add_days),
        'removed_pending': len(remove_pending_days),
        'requested_approved_unmark': created_requests,
    }
