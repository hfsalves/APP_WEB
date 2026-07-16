from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import pyodbc
from sqlalchemy import text

from models import db
from services.colaborador_despesas_service import _phc_conn_str, list_expense_companies
from services.colaborador_ferias_service import (
    _date_value,
    _fp_columns,
    _holiday_days,
    ensure_colaborador_ferias_schema,
)


WINDOW_DAYS = 56
MAX_WINDOW_DAYS = 365
MONTH_LABELS = (
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
)


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


def _pending_unmark_requests(company: dict[str, Any], start: date, end: date) -> dict[int, set[str]]:
    ensure_colaborador_ferias_schema()
    rows = db.session.execute(text("""
        SELECT PENO, DATA_FERIAS
        FROM dbo.COLAB_FERIAS_PEDIDO_DESMARCAR
        WHERE PHC_DB = :phc_db
          AND ESTADO = 'PENDENTE'
          AND DATA_FERIAS >= :start_date
          AND DATA_FERIAS <= :end_date
    """), {
        'phc_db': str(company.get('phc_db') or '').strip(),
        'start_date': start,
        'end_date': end,
    }).mappings().all()
    requests: dict[int, set[str]] = {}
    for row in rows:
        day = _date_value(row.get('DATA_FERIAS'))
        peno = int(row.get('PENO') or 0)
        if peno and day:
            requests.setdefault(peno, set()).add(day.isoformat())
    return requests


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

    requests = _pending_unmark_requests(company, start, end)
    employees: list[dict[str, Any]] = []
    for no, employee in grouped.items():
        employee["statuses"] = _period_statuses(start, end, periods_by_employee[no], holidays)
        employee["holidays"] = holidays
        employee["unmark_request_days"] = requests.get(no, set())
        employee["feid"] = int(company.get('feid') or 0)
        employees.append(employee)
    return employees


def _date_or_none(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value or "").strip())
    except ValueError:
        return None


def list_ferias_aprovacao(week: Any = None, start_value: Any = None, end_value: Any = None, company_feid: Any = None) -> dict[str, Any]:
    start = _date_or_none(start_value) or _week_start(week)
    end = _date_or_none(end_value) or (start + timedelta(days=WINDOW_DAYS - 1))
    if end < start:
        end = start
    if (end - start).days >= MAX_WINDOW_DAYS:
        end = start + timedelta(days=MAX_WINDOW_DAYS - 1)
    try:
        selected_feid = int(company_feid or 0)
    except (TypeError, ValueError):
        selected_feid = 0

    companies = list_expense_companies()
    selected_company = next((company for company in companies if int(company.get("feid") or 0) == selected_feid), None)
    if selected_feid and not selected_company:
        selected_feid = 0
    visible_companies = [selected_company] if selected_company else companies
    day_count = (end - start).days + 1
    days = [
        {
            "key": (start + timedelta(days=index)).isoformat(),
            "day": (start + timedelta(days=index)).day,
            "month": (start + timedelta(days=index)).strftime("%m"),
            "weekend": (start + timedelta(days=index)).weekday() >= 5,
            "week_break": index > 0 and index % 7 == 0,
        }
        for index in range(day_count)
    ]
    months: list[dict[str, Any]] = []
    for day in days:
        month_key = day["key"][:7]
        if not months or months[-1]["key"] != month_key:
            months.append({
                "key": month_key,
                "label": f"{MONTH_LABELS[int(day['month']) - 1]} {month_key[:4]}",
                "span": 0,
            })
        months[-1]["span"] += 1
    employees: list[dict[str, Any]] = []
    warnings: list[str] = []
    for company in visible_companies:
        try:
            employees.extend(_company_employees(company, start, end))
        except Exception:
            warnings.append(str(company.get("nome") or company.get("phc_db") or "Empresa"))

    employees.sort(key=lambda employee: (employee["empresa"].casefold(), employee["nome"].casefold(), employee["no"]))
    return {
        "start": start,
        "end": end,
        "previous_week": start - timedelta(days=7),
        "previous_end": end - timedelta(days=7),
        "next_week": start + timedelta(days=7),
        "next_end": end + timedelta(days=7),
        "days": days,
        "months": months,
        "employees": employees,
        "warnings": warnings,
        "companies": companies,
        "selected_feid": selected_feid,
    }


def _parse_action_days(values: Any) -> set[date]:
    if not isinstance(values, list):
        return set()
    result: set[date] = set()
    for value in values:
        parsed = _date_or_none(value)
        if parsed:
            result.add(parsed)
    return result


def _working_days(start: date, end: date, holidays: set[str]) -> set[date]:
    days: set[date] = set()
    current = start
    while current <= end:
        if current.weekday() < 5 and current.isoformat() not in holidays:
            days.add(current)
        current += timedelta(days=1)
    return days


def _day_ranges(days: set[date], holidays: set[str]) -> list[tuple[date, date]]:
    if not days:
        return []
    ordered = sorted(days)
    ranges: list[tuple[date, date]] = []
    start = ordered[0]
    previous = ordered[0]
    for current in ordered[1:]:
        between = previous + timedelta(days=1)
        contiguous = True
        while between < current:
            if between.weekday() < 5 and between.isoformat() not in holidays:
                contiguous = False
                break
            between += timedelta(days=1)
        if not contiguous:
            ranges.append((start, previous))
            start = current
        previous = current
    ranges.append((start, previous))
    return ranges


def _insert_fp_period(
    cursor,
    columns: set[str],
    *,
    peno: int,
    pestamp: str,
    start: date,
    end: date,
    holidays: set[str],
    login: str,
    fechado: bool = False,
    rejeitado: bool = False,
) -> None:
    work_days = len(_working_days(start, end, holidays))
    if not work_days:
        return
    now = datetime.now()
    values = {
        'fpstamp': uuid4_stamp(),
        'no': peno,
        'datai': start,
        'dataf': end,
        'ano': str(start.year)[:4],
        'dias': work_days,
        'pmes': start.month,
        'pano': start.year,
        'fechado': 1 if fechado else 0,
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
        'u_rejeita': 1 if rejeitado else 0,
        'u_validado': 0,
    }
    selected = {key: value for key, value in values.items() if key in columns}
    cursor.execute(
        f"INSERT INTO dbo.FP ({', '.join('[' + key + ']' for key in selected)}) "
        f"VALUES ({', '.join('?' for _ in selected)})",
        list(selected.values()),
    )


def uuid4_stamp() -> str:
    import uuid

    return uuid.uuid4().hex.upper()[:25]


def _approval_rows(cursor, peno: int, start: date, end: date, columns: set[str]) -> list[dict[str, Any]]:
    rejected = "AND ISNULL(U_REJEITA, 0) = 0" if 'u_rejeita' in columns else ''
    rows = cursor.execute(f"""
        SELECT
            LTRIM(RTRIM(ISNULL(FPSTAMP, ''))) AS FPSTAMP,
            DATAI,
            DATAF,
            ISNULL(FECHADO, 0) AS FECHADO,
            LTRIM(RTRIM(ISNULL(PESTAMP, ''))) AS PESTAMP
        FROM dbo.FP
        WHERE NO = ?
          AND DATAF >= ?
          AND DATAI <= ?
          {rejected}
        ORDER BY DATAI, DATAF
    """, peno, start, end).fetchall()
    return [
        {
            'fpstamp': str(row.FPSTAMP or '').strip(),
            'start': _date_value(row.DATAI),
            'end': _date_value(row.DATAF),
            'fechado': bool(row.FECHADO),
            'pestamp': str(row.PESTAMP or '').strip(),
        }
        for row in rows
        if _date_value(row.DATAI) and _date_value(row.DATAF)
    ]


def _approval_login(user: Any) -> str:
    for attribute in ('username', 'usercode', 'login', 'name'):
        value = getattr(user, attribute, '')
        if value:
            return str(value).strip()
    return 'APP'


def apply_ferias_approval_action(user: Any, payload: dict[str, Any]) -> dict[str, Any]:
    action = str(payload.get('action') or '').strip().lower()
    action_map = {
        'approve': 'approve',
        'reject': 'reject',
        'remove': 'remove',
        'mark': 'mark',
        'accept_removal': 'accept_removal',
        'reject_removal': 'reject_removal',
    }
    if action not in action_map:
        raise ValueError('Ação de férias inválida.')
    try:
        feid = int(payload.get('feid') or 0)
        peno = int(payload.get('peno') or 0)
    except (TypeError, ValueError):
        raise ValueError('Colaborador inválido.')
    selected_days = _parse_action_days(payload.get('days'))
    if not feid or not peno or not selected_days:
        raise ValueError('Selecione pelo menos um dia de férias.')

    company = next((item for item in list_expense_companies() if int(item.get('feid') or 0) == feid), None)
    if not company:
        raise ValueError('Empresa não encontrada.')
    phc_db = str(company.get('phc_db') or '').strip()
    phc_server = str(company.get('phc_server') or '').strip()
    if not phc_db:
        raise ValueError('A empresa não tem base de dados PHC configurada.')

    start, end = min(selected_days), max(selected_days)
    login = _approval_login(user)
    ensure_colaborador_ferias_schema()
    pending_requests = {
        _date_value(value)
        for value in db.session.execute(text("""
            SELECT DATA_FERIAS
            FROM dbo.COLAB_FERIAS_PEDIDO_DESMARCAR
            WHERE PENO = :peno
              AND PHC_DB = :phc_db
              AND ESTADO = 'PENDENTE'
              AND DATA_FERIAS >= :start_date
              AND DATA_FERIAS <= :end_date
        """), {'peno': peno, 'phc_db': phc_db, 'start_date': start, 'end_date': end}).scalars().all()
        if _date_value(value)
    }

    with pyodbc.connect(_phc_conn_str(phc_db, phc_server), timeout=15) as connection:
        cursor = connection.cursor()
        columns = _fp_columns(cursor)
        required = {'fpstamp', 'no', 'datai', 'dataf', 'fechado', 'pestamp'}
        missing = sorted(required - columns)
        if missing:
            raise ValueError(f"A tabela FP não tem os campos necessários: {', '.join(missing)}.")
        holidays: set[str] = set()
        for year in range(start.year, end.year + 1):
            holidays.update(_holiday_days(cursor, year))
        invalid_days = {day for day in selected_days if day.weekday() >= 5 or day.isoformat() in holidays}
        if invalid_days:
            raise ValueError('Só pode alterar dias úteis que não sejam feriados.')
        rows = _approval_rows(cursor, peno, start, end, columns)
        by_day: dict[date, dict[str, Any]] = {}
        for row in rows:
            for day in _working_days(row['start'], row['end'], holidays):
                if day in selected_days:
                    existing = by_day.get(day)
                    if not existing or row['fechado']:
                        by_day[day] = row

        states = {
            day: ('removal' if day in pending_requests else ('approved' if by_day.get(day, {}).get('fechado') else ('pending' if day in by_day else 'empty')))
            for day in selected_days
        }
        expected = {
            'approve': 'pending',
            'reject': 'pending',
            'remove': 'approved',
            'mark': 'empty',
            'accept_removal': 'removal',
            'reject_removal': 'removal',
        }[action]
        if any(state != expected for state in states.values()):
            raise ValueError('Os dias selecionados já não estão todos no estado esperado. Atualize a grelha e tente novamente.')
        if action == 'reject' and 'u_rejeita' not in columns:
            raise ValueError('A tabela FP desta empresa não suporta a rejeição de férias.')

        employee = cursor.execute("""
            SELECT TOP 1 LTRIM(RTRIM(ISNULL(PESTAMP, ''))) AS PESTAMP
            FROM dbo.PE
            WHERE NO = ?
        """, peno).fetchone()
        if not employee:
            raise ValueError('Colaborador não encontrado na tabela PE do PHC.')
        employee_stamp = str(employee.PESTAMP or '').strip()

        if action == 'mark':
            for range_start, range_end in _day_ranges(selected_days, holidays):
                _insert_fp_period(
                    cursor, columns, peno=peno, pestamp=employee_stamp,
                    start=range_start, end=range_end, holidays=holidays, login=login,
                )
        elif action not in {'reject_removal'}:
            selected_by_stamp: dict[str, set[date]] = {}
            for day, row in by_day.items():
                selected_by_stamp.setdefault(row['fpstamp'], set()).add(day)
            for row in rows:
                chosen = selected_by_stamp.get(row['fpstamp'], set())
                if not chosen:
                    continue
                row_days = _working_days(row['start'], row['end'], holidays)
                # Quando a decisão abrange todo o período, preservamos o registo
                # original do PHC. Evita recriar intervalos que atravessam fins de semana.
                if chosen == row_days:
                    if action == 'approve':
                        cursor.execute('UPDATE dbo.FP SET FECHADO = 1 WHERE FPSTAMP = ?', row['fpstamp'])
                    elif action == 'reject':
                        cursor.execute('UPDATE dbo.FP SET U_REJEITA = 1 WHERE FPSTAMP = ?', row['fpstamp'])
                    else:
                        cursor.execute('DELETE FROM dbo.FP WHERE FPSTAMP = ?', row['fpstamp'])
                    continue
                cursor.execute('DELETE FROM dbo.FP WHERE FPSTAMP = ?', row['fpstamp'])
                remaining = row_days - chosen
                for range_start, range_end in _day_ranges(remaining, holidays):
                    _insert_fp_period(
                        cursor, columns, peno=peno, pestamp=row['pestamp'] or employee_stamp,
                        start=range_start, end=range_end, holidays=holidays, login=login,
                        fechado=row['fechado'],
                    )
                if action == 'approve':
                    for range_start, range_end in _day_ranges(chosen, holidays):
                        _insert_fp_period(
                            cursor, columns, peno=peno, pestamp=row['pestamp'] or employee_stamp,
                            start=range_start, end=range_end, holidays=holidays, login=login,
                            fechado=True,
                        )
                elif action == 'reject':
                    for range_start, range_end in _day_ranges(chosen, holidays):
                        _insert_fp_period(
                            cursor, columns, peno=peno, pestamp=row['pestamp'] or employee_stamp,
                            start=range_start, end=range_end, holidays=holidays, login=login,
                            rejeitado=True,
                        )
        connection.commit()

    if action in {'accept_removal', 'reject_removal'}:
        new_state = 'ACEITE' if action == 'accept_removal' else 'REJEITADO'
        for day in selected_days:
            db.session.execute(text("""
                UPDATE dbo.COLAB_FERIAS_PEDIDO_DESMARCAR
                SET ESTADO = :estado,
                    DTALT = GETDATE(),
                    USERALTERACAO = :login
                WHERE PENO = :peno
                  AND PHC_DB = :phc_db
                  AND ESTADO = 'PENDENTE'
                  AND DATA_FERIAS = :day
            """), {
                'estado': new_state,
                'login': login,
                'peno': peno,
                'phc_db': phc_db,
                'day': day,
            })
        db.session.commit()

    return {'ok': True, 'action': action, 'days': len(selected_days)}
