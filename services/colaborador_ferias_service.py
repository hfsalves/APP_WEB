from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pyodbc

from services.colaborador_despesas_service import get_colaborador_context, _phc_conn_str


def _safe_year(value: Any) -> int:
    try:
        year = int(value or date.today().year)
    except Exception:
        year = date.today().year
    return year if 2000 <= year <= 2100 else date.today().year


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
    result["periods"] = periods
    result["marked_days"] = len(days) + len(pending_days)
    result["holiday_count"] = len(holidays)
    result["working_days"] = float(working_days)
    return result
