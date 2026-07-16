from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import pyodbc

from services.colaborador_despesas_service import _phc_conn_str, list_expense_companies
from services.colaborador_ferias_service import _date_value, _fp_columns, _holiday_days


WINDOW_DAYS = 56
WEEKDAY_LABELS = ("Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom")


def _week_start(value: Any = None) -> date:
    if isinstance(value, datetime):
        target = value.date()
    elif isinstance(value, date):
        target = value
    else:
        try:
            target = date.fromisoformat(str(value or "").strip())
        except ValueError:
            target = date.today()
    return target - timedelta(days=target.weekday())


def _period_statuses(start: date, end: date, rows: list[Any], holidays: set[str]) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for row in rows:
        date_start = _date_value(row.DATAI)
        date_end = _date_value(row.DATAF)
        if not date_start or not date_end:
            continue
        current = max(date_start, start)
        last = min(date_end, end)
        if last < current:
            continue
        status = "approved" if bool(row.FECHADO) else "pending"
        while current <= last:
            key = current.isoformat()
            if current.weekday() < 5 and key not in holidays:
                if status == "approved" or key not in statuses:
                    statuses[key] = status
            current += timedelta(days=1)
    return statuses


def _company_employees(company: dict[str, Any], start: date, end: date) -> list[dict[str, Any]]:
    phc_db = str(company.get("phc_db") or "").strip()
    phc_server = str(company.get("phc_server") or "").strip()
    if not phc_db:
        return []

    with pyodbc.connect(_phc_conn_str(phc_db, phc_server), timeout=15) as connection:
        cursor = connection.cursor()
        fp_columns = _fp_columns(cursor)
        if not {"no", "datai", "dataf", "fechado"}.issubset(fp_columns):
            return []
        rejected_filter = "AND ISNULL(FP.U_REJEITA, 0) = 0" if "u_rejeita" in fp_columns else ""
        rows = cursor.execute(f"""
            SELECT
                PE.NO,
                LTRIM(RTRIM(ISNULL(PE.NOME, ''))) AS NOME,
                LTRIM(RTRIM(ISNULL(PE.STADESC, ''))) AS ESTADO,
                FP.DATAI,
                FP.DATAF,
                ISNULL(FP.FECHADO, 0) AS FECHADO
            FROM dbo.PE AS PE
            LEFT JOIN dbo.FP AS FP
              ON FP.NO = PE.NO
             AND FP.DATAF >= ?
             AND FP.DATAI <= ?
             {rejected_filter}
            WHERE ISNULL(PE.NO, 0) <> 0
              AND ISNULL(PE.STATUS, 1) <> 3
            ORDER BY LTRIM(RTRIM(ISNULL(PE.NOME, ''))), PE.NO
        """, start, end).fetchall()
        holidays: set[str] = set()
        for year in range(start.year, end.year + 1):
            holidays.update(_holiday_days(cursor, year))

    grouped: dict[int, dict[str, Any]] = {}
    periods_by_employee: dict[int, list[Any]] = {}
    for row in rows:
        no = int(row.NO or 0)
        if not no:
            continue
        if no not in grouped:
            grouped[no] = {
                "no": no,
                "nome": str(row.NOME or "").strip(),
                "empresa": str(company.get("nome") or "").strip(),
                "phc_db": phc_db,
            }
            periods_by_employee[no] = []
        if _date_value(row.DATAI) and _date_value(row.DATAF):
            periods_by_employee[no].append(row)

    employees: list[dict[str, Any]] = []
    for no, employee in grouped.items():
        employee["statuses"] = _period_statuses(start, end, periods_by_employee[no], holidays)
        employee["holidays"] = holidays
        employees.append(employee)
    return employees


def list_ferias_aprovacao(week: Any = None) -> dict[str, Any]:
    start = _week_start(week)
    end = start + timedelta(days=WINDOW_DAYS - 1)
    days = [
        {
            "key": (start + timedelta(days=index)).isoformat(),
            "day": (start + timedelta(days=index)).day,
            "month": (start + timedelta(days=index)).strftime("%m"),
            "weekday": WEEKDAY_LABELS[(start + timedelta(days=index)).weekday()],
            "weekend": (start + timedelta(days=index)).weekday() >= 5,
            "week_break": index > 0 and index % 7 == 0,
        }
        for index in range(WINDOW_DAYS)
    ]
    employees: list[dict[str, Any]] = []
    warnings: list[str] = []
    for company in list_expense_companies():
        try:
            employees.extend(_company_employees(company, start, end))
        except Exception:
            warnings.append(str(company.get("nome") or company.get("phc_db") or "Empresa"))

    employees.sort(key=lambda employee: (employee["empresa"].casefold(), employee["nome"].casefold(), employee["no"]))
    return {
        "start": start,
        "end": end,
        "previous_week": start - timedelta(days=7),
        "next_week": start + timedelta(days=7),
        "days": days,
        "employees": employees,
        "warnings": warnings,
    }
