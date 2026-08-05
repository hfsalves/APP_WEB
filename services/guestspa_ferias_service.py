from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import text

from models import db


PHC_DB = "Guest_Spa_Tur"
PHC_PREFIX = "[Guest_Spa_Tur].[dbo]"
REQUEST_TABLE = "dbo.GUESTSPA_FERIAS_PEDIDO_DESMARCAR"
WINDOW_DAYS = 56
MAX_WINDOW_DAYS = 365
MONTH_LABELS = (
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
)


def _safe_year(value: Any) -> int:
    try:
        value = int(value or date.today().year)
    except (TypeError, ValueError):
        value = date.today().year
    return value if 2000 <= value <= 2100 else date.today().year


def _stamp() -> str:
    return uuid.uuid4().hex.upper()[:25]


def _date_value(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    return value if isinstance(value, date) else None


def _date_or_none(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value or "").strip())
    except ValueError:
        return None


def _login(user: Any) -> str:
    return str(getattr(user, "LOGIN", "") or "APP").strip()[:30] or "APP"


def _employee_context(user: Any) -> dict[str, Any]:
    row = db.session.execute(text("""
        SELECT TOP 1
            ISNULL(PENO, 0) AS PENO,
            LTRIM(RTRIM(ISNULL(PENOME, ''))) AS PENOME,
            LTRIM(RTRIM(ISNULL(LOGIN, ''))) AS LOGIN,
            LTRIM(RTRIM(ISNULL(USSTAMP, ''))) AS USSTAMP
        FROM dbo.US
        WHERE USSTAMP = :userstamp
    """), {"userstamp": str(getattr(user, "USSTAMP", "") or "")}).mappings().first()
    peno = int((row or {}).get("PENO") or 0)
    return {
        "peno": peno,
        "penome": str((row or {}).get("PENOME") or "").strip(),
        "login": str((row or {}).get("LOGIN") or _login(user)).strip(),
        "userstamp": str((row or {}).get("USSTAMP") or "").strip(),
        "empresa": "GuestSpaTur",
        "completo": bool(peno),
    }


def ensure_guestspa_ferias_schema() -> None:
    db.session.execute(text(f"""
        IF OBJECT_ID('{REQUEST_TABLE}', 'U') IS NULL
        BEGIN
            CREATE TABLE {REQUEST_TABLE} (
                PEDIDOSTAMP varchar(25) NOT NULL
                    CONSTRAINT PK_GUESTSPA_FERIAS_PEDIDO_DESMARCAR PRIMARY KEY,
                USSTAMP varchar(25) NOT NULL
                    CONSTRAINT DF_GUESTSPA_FERIAS_PEDIDO_USSTAMP DEFAULT '',
                LOGIN varchar(60) NOT NULL
                    CONSTRAINT DF_GUESTSPA_FERIAS_PEDIDO_LOGIN DEFAULT '',
                PENO int NOT NULL
                    CONSTRAINT DF_GUESTSPA_FERIAS_PEDIDO_PENO DEFAULT 0,
                PENOME nvarchar(160) NOT NULL
                    CONSTRAINT DF_GUESTSPA_FERIAS_PEDIDO_PENOME DEFAULT N'',
                FPSTAMP varchar(25) NOT NULL
                    CONSTRAINT DF_GUESTSPA_FERIAS_PEDIDO_FPSTAMP DEFAULT '',
                DATA_FERIAS date NOT NULL,
                ESTADO varchar(20) NOT NULL
                    CONSTRAINT DF_GUESTSPA_FERIAS_PEDIDO_ESTADO DEFAULT 'PENDENTE',
                DTCRI datetime NOT NULL
                    CONSTRAINT DF_GUESTSPA_FERIAS_PEDIDO_DTCRI DEFAULT GETDATE(),
                DTALT datetime NULL,
                USERCRIACAO varchar(60) NOT NULL
                    CONSTRAINT DF_GUESTSPA_FERIAS_PEDIDO_USERCRI DEFAULT '',
                USERALTERACAO varchar(60) NOT NULL
                    CONSTRAINT DF_GUESTSPA_FERIAS_PEDIDO_USERALT DEFAULT ''
            );
            CREATE INDEX IX_GUESTSPA_FERIAS_PEDIDO_COLAB_ESTADO
                ON {REQUEST_TABLE} (PENO, ESTADO, DATA_FERIAS);
        END
    """))
    db.session.commit()


def _date_from_mmdd(year: int, value: Any) -> date | None:
    try:
        raw = int(value or 0)
        return date(year, raw // 100, raw % 100) if raw else None
    except (TypeError, ValueError):
        return None


def holiday_days(year: int) -> set[str]:
    rows = db.session.execute(text(f"""
        SELECT DATA, DATAF, ISNULL(FIXO, 0) AS FIXO,
               ISNULL(DIAI, 0) AS DIAI, ISNULL(DIAF, 0) AS DIAF
        FROM {PHC_PREFIX}.[FF]
        WHERE (ISNULL(FIXO, 0) = 1 AND ISNULL(DIAI, 0) > 0)
           OR (ISNULL(FIXO, 0) = 0 AND DATAF >= :start_date AND DATA <= :end_date)
    """), {"start_date": date(year, 1, 1), "end_date": date(year, 12, 31)}).mappings()
    result: set[str] = set()
    for row in rows:
        start = _date_from_mmdd(year, row["DIAI"]) if row["FIXO"] else _date_value(row["DATA"])
        end = _date_from_mmdd(year, row["DIAF"]) if row["FIXO"] else _date_value(row["DATAF"])
        end = end or start
        if not start or not end:
            continue
        if end < start:
            start, end = end, start
        current = max(start, date(year, 1, 1))
        last = min(end, date(year, 12, 31))
        while current <= last:
            result.add(current.isoformat())
            current += timedelta(days=1)
    return result


def working_days(start: date, end: date, holidays: set[str]) -> set[date]:
    return {
        start + timedelta(days=index)
        for index in range((end - start).days + 1)
        if (start + timedelta(days=index)).weekday() < 5
        and (start + timedelta(days=index)).isoformat() not in holidays
    }


def day_ranges(days: set[date], holidays: set[str]) -> list[tuple[date, date]]:
    if not days:
        return []
    ranges: list[tuple[date, date]] = []
    start = previous = min(days)
    for current in sorted(days - {start}):
        between = previous + timedelta(days=1)
        while between < current and (between.weekday() >= 5 or between.isoformat() in holidays):
            between += timedelta(days=1)
        if between != current:
            ranges.append((start, previous))
            start = current
        previous = current
    ranges.append((start, previous))
    return ranges


def _calendar_ranges_without_days(start: date, end: date, excluded: set[date]) -> list[tuple[date, date]]:
    ranges: list[tuple[date, date]] = []
    range_start: date | None = None
    current = start
    while current <= end:
        if current in excluded:
            if range_start:
                ranges.append((range_start, current - timedelta(days=1)))
                range_start = None
        elif range_start is None:
            range_start = current
        current += timedelta(days=1)
    if range_start:
        ranges.append((range_start, end))
    return ranges


def _fp_rows(peno: int, start: date, end: date) -> list[dict[str, Any]]:
    rows = db.session.execute(text(f"""
        SELECT LTRIM(RTRIM(ISNULL(FPSTAMP, ''))) AS FPSTAMP, DATAI, DATAF,
               ISNULL(FECHADO, 0) AS FECHADO,
               LTRIM(RTRIM(ISNULL(PESTAMP, ''))) AS PESTAMP,
               LTRIM(RTRIM(ISNULL(ANO, ''))) AS ANO
        FROM {PHC_PREFIX}.[FP]
        WHERE NO = :peno AND DATAF >= :start_date AND DATAI <= :end_date
        ORDER BY DATAI, DATAF
    """), {"peno": peno, "start_date": start, "end_date": end}).mappings()
    return [
        {"fpstamp": str(row["FPSTAMP"] or "").strip(), "start": _date_value(row["DATAI"]),
         "end": _date_value(row["DATAF"]), "fechado": bool(row["FECHADO"]),
         "pestamp": str(row["PESTAMP"] or "").strip(), "ano": str(row["ANO"] or "").strip()}
        for row in rows if _date_value(row["DATAI"]) and _date_value(row["DATAF"])
    ]


def _employee_stamp(peno: int) -> str:
    value = db.session.execute(text(f"""
        SELECT TOP 1 LTRIM(RTRIM(ISNULL(PESTAMP, '')))
        FROM {PHC_PREFIX}.[PE] WHERE NO = :peno
    """), {"peno": peno}).scalar()
    if not value:
        raise ValueError("Colaborador não encontrado na tabela PE da GuestSpa.")
    return str(value).strip()


def _insert_fp(peno: int, pestamp: str, start: date, end: date, holidays: set[str], login: str, fechado: bool) -> None:
    days = working_days(start, end, holidays)
    if not days:
        return
    now = datetime.now()
    db.session.execute(text(f"""
        INSERT INTO {PHC_PREFIX}.[FP]
        (FPSTAMP, NO, DATAI, DATAF, ANO, DIAS, PMES, PANO, FECHADO, PESTAMP,
         PESUPSTAMPFE, OBS, PROCESSADA, PRSTAMP, PESUPNOMEFE, ABSSTAMP,
         NAOFALTAS, ISFPADMISSAO, ISMDIAS, HORAI, HORAF,
         OUSRINIS, OUSRDATA, OUSRHORA, USRINIS, USRDATA, USRHORA, MARCADA)
        VALUES
        (:stamp, :peno, :start_date, :end_date, :ano, :days, :month, :year, :fechado, :pestamp,
         '', '', 0, '', '', '', '', 0, 0, '', '',
         :login, :now, :time, :login, :now, :time, 0)
    """), {
        "stamp": _stamp(), "peno": peno, "start_date": start, "end_date": end,
        "ano": str(start.year), "days": len(days), "month": start.month, "year": start.year,
        "fechado": 1 if fechado else 0, "pestamp": pestamp, "login": login,
        "now": now, "time": now.strftime("%H:%M:%S"),
    })


def _request_days(peno: int, start: date, end: date) -> set[str]:
    ensure_guestspa_ferias_schema()
    return {
        value.isoformat() for value in db.session.execute(text(f"""
            SELECT DATA_FERIAS FROM {REQUEST_TABLE}
            WHERE PENO = :peno AND ESTADO = 'PENDENTE'
              AND DATA_FERIAS BETWEEN :start_date AND :end_date
        """), {"peno": peno, "start_date": start, "end_date": end}).scalars()
        if isinstance(value, date)
    }


def list_guestspa_ferias(user: Any, year: Any = None) -> dict[str, Any]:
    target_year = _safe_year(year)
    employee = _employee_context(user)
    payload = {"ok": True, "year": target_year, "colaborador": employee, "vacation_days": [],
               "pending_vacation_days": [], "unmark_request_days": [], "holiday_days": [],
               "periods": [], "marked_days": 0, "working_days": 0, "warning": ""}
    if not employee["completo"]:
        payload["warning"] = "O utilizador não tem uma ficha de colaborador associada."
        return payload
    start, end = date(target_year, 1, 1), date(target_year, 12, 31)
    try:
        holidays = holiday_days(target_year)
        approved: set[str] = set()
        pending: set[str] = set()
        periods = []
        for row in _fp_rows(employee["peno"], start, end):
            row_days = working_days(max(row["start"], start), min(row["end"], end), holidays)
            bucket = approved if row["fechado"] else pending
            bucket.update(day.isoformat() for day in row_days)
            periods.append({"fpstamp": row["fpstamp"], "datai": row["start"].isoformat(),
                            "dataf": row["end"].isoformat(), "ano": row["ano"],
                            "dias": len(row_days), "fechado": row["fechado"], "marcada": False,
                            "processada": False, "validado": False, "enviado": False, "obs": ""})
        pending.difference_update(approved)
        payload.update({"vacation_days": sorted(approved), "pending_vacation_days": sorted(pending),
                        "unmark_request_days": sorted(_request_days(employee["peno"], start, end)),
                        "holiday_days": sorted(holidays), "periods": periods,
                        "marked_days": len(approved | pending), "working_days": len(approved | pending)})
    except Exception as exc:
        payload["warning"] = f"Erro ao ler férias na GuestSpa: {exc}"
    return payload


def _parse_year_days(values: Any, year: int) -> set[date]:
    if not isinstance(values, list):
        return set()
    return {day for value in values if (day := _date_or_none(value)) and day.year == year}


def apply_guestspa_ferias_changes(user: Any, payload: dict[str, Any]) -> dict[str, Any]:
    ensure_guestspa_ferias_schema()
    year = _safe_year(payload.get("year"))
    employee = _employee_context(user)
    if not employee["completo"]:
        raise ValueError("O utilizador não tem uma ficha de colaborador associada.")
    add = _parse_year_days(payload.get("add_days"), year)
    remove_pending = _parse_year_days(payload.get("remove_pending_days"), year)
    request_unmark = _parse_year_days(payload.get("request_approved_unmark_days"), year)
    cancel_unmark = _parse_year_days(payload.get("cancel_approved_unmark_request_days"), year)
    if not (add or remove_pending or request_unmark or cancel_unmark):
        raise ValueError("Não existem alterações para gravar.")
    holidays = holiday_days(year)
    invalid = {day for day in add | remove_pending | request_unmark | cancel_unmark if day.weekday() >= 5 or day.isoformat() in holidays}
    if invalid:
        raise ValueError("Só é possível alterar dias úteis que não sejam feriados.")
    rows = _fp_rows(employee["peno"], date(year, 1, 1), date(year, 12, 31))
    approved: dict[date, str] = {}
    pending: set[date] = set()
    pending_rows: list[dict[str, Any]] = []
    for row in rows:
        row_days = working_days(row["start"], row["end"], holidays)
        if row["fechado"]:
            approved.update({day: row["fpstamp"] for day in row_days})
        else:
            pending.update(row_days)
            pending_rows.append(row)
    if add & (set(approved) | pending):
        raise ValueError("Existem dias selecionados que já estão marcados.")
    if remove_pending - pending:
        raise ValueError("Só pode desmarcar férias pendentes de aprovação.")
    if request_unmark - set(approved):
        raise ValueError("Só pode pedir a desmarcação de férias aprovadas.")
    request_keys = _request_days(employee["peno"], date(year, 1, 1), date(year, 12, 31))
    if cancel_unmark - {date.fromisoformat(value) for value in request_keys}:
        raise ValueError("Só pode cancelar pedidos de desmarcação pendentes.")
    stamp = _employee_stamp(employee["peno"])
    for row in pending_rows:
        removed = remove_pending & working_days(row["start"], row["end"], holidays)
        if not removed:
            continue
        db.session.execute(text(f"DELETE FROM {PHC_PREFIX}.[FP] WHERE FPSTAMP = :stamp"), {"stamp": row["fpstamp"]})
        for begin, finish in _calendar_ranges_without_days(row["start"], row["end"], removed):
            _insert_fp(employee["peno"], row["pestamp"] or stamp, begin, finish, holidays, employee["login"], False)
    for begin, finish in day_ranges(add, holidays):
        _insert_fp(employee["peno"], stamp, begin, finish, holidays, employee["login"], False)
    for day in cancel_unmark:
        db.session.execute(text(f"""DELETE FROM {REQUEST_TABLE}
            WHERE PENO=:peno AND DATA_FERIAS=:day AND ESTADO='PENDENTE'"""), {"peno": employee["peno"], "day": day})
    created = 0
    for day in request_unmark:
        if day.isoformat() in request_keys:
            continue
        db.session.execute(text(f"""
            INSERT INTO {REQUEST_TABLE}
            (PEDIDOSTAMP, USSTAMP, LOGIN, PENO, PENOME, FPSTAMP, DATA_FERIAS, ESTADO, USERCRIACAO, USERALTERACAO)
            VALUES (:stamp, :userstamp, :login, :peno, :penome, :fpstamp, :day, 'PENDENTE', :login, :login)
        """), {"stamp": _stamp(), "userstamp": employee["userstamp"], "login": employee["login"],
               "peno": employee["peno"], "penome": employee["penome"], "fpstamp": approved[day], "day": day})
        created += 1
    db.session.commit()
    return {"ok": True, "added": len(add), "removed_pending": len(remove_pending),
            "requested_approved_unmark": created, "cancelled_approved_unmark_request": len(cancel_unmark)}


def _week_start(value: Any = None) -> date:
    return (_date_or_none(value) or date.today()) - timedelta(days=(_date_or_none(value) or date.today()).weekday())


def list_guestspa_ferias_aprovacao(week: Any = None, start_value: Any = None, end_value: Any = None) -> dict[str, Any]:
    start = _date_or_none(start_value) or _week_start(week)
    end = _date_or_none(end_value) or (start + timedelta(days=WINDOW_DAYS - 1))
    if end < start:
        end = start
    if (end - start).days >= MAX_WINDOW_DAYS:
        end = start + timedelta(days=MAX_WINDOW_DAYS - 1)
    holidays: set[str] = set()
    for year in range(start.year, end.year + 1):
        holidays.update(holiday_days(year))
    people = db.session.execute(text(f"""
        SELECT NO, LTRIM(RTRIM(ISNULL(NOME, ''))) AS NOME
        FROM {PHC_PREFIX}.[PE]
        WHERE ISNULL(NO, 0) <> 0 AND ISNULL(STATUS, 1) <> 3
        ORDER BY LTRIM(RTRIM(ISNULL(NOME, ''))), NO
    """)).mappings().all()
    request_rows = db.session.execute(text(f"""
        SELECT PENO, DATA_FERIAS FROM {REQUEST_TABLE}
        WHERE ESTADO='PENDENTE' AND DATA_FERIAS BETWEEN :start_date AND :end_date
    """), {"start_date": start, "end_date": end}).mappings().all()
    requests: dict[int, set[str]] = {}
    for row in request_rows:
        value = _date_value(row["DATA_FERIAS"])
        if value:
            requests.setdefault(int(row["PENO"] or 0), set()).add(value.isoformat())
    employees = []
    for person in people:
        peno = int(person["NO"] or 0)
        statuses: dict[str, str] = {}
        for row in _fp_rows(peno, start, end):
            state = "approved" if row["fechado"] else "pending"
            for day in working_days(max(start, row["start"]), min(end, row["end"]), holidays):
                if state == "approved" or day.isoformat() not in statuses:
                    statuses[day.isoformat()] = state
        employees.append({"no": peno, "nome": str(person["NOME"] or "").strip(), "empresa": "GuestSpaTur",
                          "feid": 1, "statuses": statuses, "holidays": holidays,
                          "unmark_request_days": requests.get(peno, set())})
    days = [{"key": (start + timedelta(days=index)).isoformat(), "day": (start + timedelta(days=index)).day,
             "month": (start + timedelta(days=index)).strftime("%m"),
             "weekend": (start + timedelta(days=index)).weekday() >= 5, "week_break": index > 0 and index % 7 == 0}
            for index in range((end - start).days + 1)]
    months: list[dict[str, Any]] = []
    for day in days:
        key = day["key"][:7]
        if not months or months[-1]["key"] != key:
            months.append({"key": key, "label": f"{MONTH_LABELS[int(day['month']) - 1]} {key[:4]}", "span": 0})
        months[-1]["span"] += 1
    return {"start": start, "end": end, "previous_week": start - timedelta(days=7), "previous_end": end - timedelta(days=7),
            "next_week": start + timedelta(days=7), "next_end": end + timedelta(days=7), "days": days, "months": months,
            "employees": employees, "warnings": [], "companies": [{"feid": 1, "nome": "GuestSpaTur"}], "selected_feid": 1}


def apply_guestspa_ferias_approval_action(user: Any, payload: dict[str, Any]) -> dict[str, Any]:
    action = str(payload.get("action") or "").strip().lower()
    if action not in {"approve", "reject", "remove", "mark", "accept_removal", "reject_removal"}:
        raise ValueError("Ação de férias inválida.")
    try:
        peno = int(payload.get("peno") or 0)
    except (TypeError, ValueError):
        peno = 0
    selected = {_date_or_none(value) for value in (payload.get("days") or [])}
    selected.discard(None)
    if not peno or not selected:
        raise ValueError("Selecione pelo menos um dia de férias.")
    start, end = min(selected), max(selected)
    holidays: set[str] = set()
    for year in range(start.year, end.year + 1):
        holidays.update(holiday_days(year))
    if any(day.weekday() >= 5 or day.isoformat() in holidays for day in selected):
        raise ValueError("Só pode alterar dias úteis que não sejam feriados.")
    rows = _fp_rows(peno, start, end)
    by_day: dict[date, dict[str, Any]] = {}
    for row in rows:
        for day in working_days(row["start"], row["end"], holidays):
            if day in selected and (day not in by_day or row["fechado"]):
                by_day[day] = row
    pending_requests = _request_days(peno, start, end)
    states = {day: ("removal" if day.isoformat() in pending_requests else ("approved" if by_day.get(day, {}).get("fechado") else ("pending" if day in by_day else "empty"))) for day in selected}
    expected = {"approve": "pending", "reject": "pending", "remove": "approved", "mark": "empty", "accept_removal": "removal", "reject_removal": "removal"}[action]
    if any(state != expected for state in states.values()):
        raise ValueError("Os dias selecionados já não estão todos no estado esperado. Atualize a grelha e tente novamente.")
    login = _login(user)
    stamp = _employee_stamp(peno)
    if action == "mark":
        for begin, finish in day_ranges(selected, holidays):
            _insert_fp(peno, stamp, begin, finish, holidays, login, False)
    elif action != "reject_removal":
        chosen: dict[str, set[date]] = {}
        for day, row in by_day.items():
            chosen.setdefault(row["fpstamp"], set()).add(day)
        for row in rows:
            days = chosen.get(row["fpstamp"], set())
            if not days:
                continue
            all_days = working_days(row["start"], row["end"], holidays)
            db.session.execute(text(f"DELETE FROM {PHC_PREFIX}.[FP] WHERE FPSTAMP=:stamp"), {"stamp": row["fpstamp"]})
            for begin, finish in _calendar_ranges_without_days(row["start"], row["end"], days):
                _insert_fp(peno, row["pestamp"] or stamp, begin, finish, holidays, login, row["fechado"])
            if action == "approve":
                for begin, finish in day_ranges(days, holidays):
                    _insert_fp(peno, row["pestamp"] or stamp, begin, finish, holidays, login, True)
            # GuestSpa FP has no rejected state. Rejection simply removes the pending request.
    if action in {"accept_removal", "reject_removal"}:
        state = "ACEITE" if action == "accept_removal" else "REJEITADO"
        for day in selected:
            db.session.execute(text(f"""UPDATE {REQUEST_TABLE}
                SET ESTADO=:state, DTALT=GETDATE(), USERALTERACAO=:login
                WHERE PENO=:peno AND DATA_FERIAS=:day AND ESTADO='PENDENTE'"""),
                               {"state": state, "login": login, "peno": peno, "day": day})
    db.session.commit()
    return {"ok": True, "action": action, "days": len(selected)}
