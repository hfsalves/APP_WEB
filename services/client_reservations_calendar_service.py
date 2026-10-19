"""Read-only monthly reservation calendars for the owner portal."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import text


DEFAULT_MONTHS = 12
MAX_MONTHS = 12


class ClientCalendarError(ValueError):
    pass


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _as_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = _clean(value)
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def _as_money(value: Any) -> float:
    try:
        return round(float(value or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def _month_start(value: Any = None, *, today: date | None = None) -> date:
    today = today or date.today()
    raw = _clean(value)
    if not raw:
        return today.replace(day=1)
    try:
        parsed = datetime.strptime(raw[:7], "%Y-%m").date()
    except ValueError as exc:
        raise ClientCalendarError("Indique um mês inicial válido.") from exc
    if parsed.year < 2000 or parsed.year > 2100:
        raise ClientCalendarError("O mês inicial está fora do intervalo permitido.")
    return parsed.replace(day=1)


def _add_months(value: date, months: int) -> date:
    index = (value.year * 12) + (value.month - 1) + int(months)
    return date(index // 12, (index % 12) + 1, 1)


def calendar_window(start: Any = None, months: Any = None, *, today: date | None = None) -> dict[str, Any]:
    start_date = _month_start(start, today=today)
    try:
        count = int(months or DEFAULT_MONTHS)
    except (TypeError, ValueError):
        count = DEFAULT_MONTHS
    if count < 1 or count > MAX_MONTHS:
        raise ClientCalendarError(f"O calendário pode apresentar entre 1 e {MAX_MONTHS} meses.")
    return {
        "start": start_date,
        "end": _add_months(start_date, count),
        "months": count,
    }


def _owner_lodgings(engine, client_no: int, establishment: int = 0) -> list[str]:
    conditions = [
        "COALESCE(INATIVO, 0) = 0",
        "COALESCE(CLIENTID, 0) = :client_no",
        "LTRIM(RTRIM(COALESCE(NOME, ''))) <> ''",
    ]
    params: dict[str, Any] = {"client_no": int(client_no)}
    if int(establishment or 0) > 0:
        conditions.append("COALESCE(CLESTAB, 0) = :establishment")
        params["establishment"] = int(establishment)
    prefix = "dbo." if engine.dialect.name == "mssql" else ""
    statement = text(f"""
        SELECT LTRIM(RTRIM(COALESCE(NOME, ''))) AS NOME
        FROM {prefix}AL
        WHERE {' AND '.join(conditions)}
        ORDER BY LTRIM(RTRIM(COALESCE(NOME, '')))
    """)
    with engine.connect() as connection:
        rows = connection.execute(statement, params).mappings().all()
    return [_clean(row.get("NOME")) for row in rows if _clean(row.get("NOME"))]


def _reservation_rows(
    engine,
    client_no: int,
    establishment: int,
    lodging: str,
    window: dict[str, Any],
    include_cancelled: bool,
) -> list[dict[str, Any]]:
    conditions = [
        "COALESCE(AL.INATIVO, 0) = 0",
        "COALESCE(AL.CLIENTID, 0) = :client_no",
        "LTRIM(RTRIM(COALESCE(AL.NOME, ''))) = LTRIM(RTRIM(:lodging))",
        "RS.DATAIN IS NOT NULL",
        "RS.DATAOUT IS NOT NULL",
        "RS.DATAIN < :window_end",
        "RS.DATAOUT >= :window_start",
    ]
    params: dict[str, Any] = {
        "client_no": int(client_no),
        "lodging": lodging,
        "window_start": window["start"],
        "window_end": window["end"],
    }
    if int(establishment or 0) > 0:
        conditions.append("COALESCE(AL.CLESTAB, 0) = :establishment")
        params["establishment"] = int(establishment)
    if not include_cancelled:
        conditions.append("COALESCE(RS.CANCELADA, 0) = 0")

    prefix = "dbo." if engine.dialect.name == "mssql" else ""
    statement = text(f"""
        SELECT
            RS.RSSTAMP,
            LTRIM(RTRIM(COALESCE(RS.RESERVA, ''))) AS RESERVA,
            LTRIM(RTRIM(COALESCE(RS.ALOJAMENTO, ''))) AS ALOJAMENTO,
            RS.DATAIN,
            RS.DATAOUT,
            COALESCE(RS.HORAIN, '') AS HORAIN,
            COALESCE(RS.HORAOUT, '') AS HORAOUT,
            LTRIM(RTRIM(COALESCE(RS.NOME, ''))) AS HOSPEDE,
            COALESCE(RS.ADULTOS, 0) AS ADULTOS,
            COALESCE(RS.CRIANCAS, 0) AS CRIANCAS,
            COALESCE(RS.BEBES, 0) AS BEBES,
            COALESCE(RS.ESTADIA, 0) AS ESTADIA,
            COALESCE(RS.LIMPEZA, 0) AS LIMPEZA,
            COALESCE(RS.COMISSAO, 0) AS COMISSAO,
            COALESCE(RS.PCANCEL, 0) AS PCANCEL,
            LTRIM(RTRIM(COALESCE(RS.ORIGEM, ''))) AS ORIGEM,
            COALESCE(RS.CANCELADA, 0) AS CANCELADA,
            RS.DTCANCEL,
            COALESCE(AL.FTLIMPEZA, 0) AS FTLIMPEZA
        FROM {prefix}RS AS RS
        INNER JOIN {prefix}AL AS AL
          ON LTRIM(RTRIM(COALESCE(AL.NOME, ''))) = LTRIM(RTRIM(COALESCE(RS.ALOJAMENTO, '')))
        WHERE {' AND '.join(conditions)}
        ORDER BY RS.DATAIN, RS.DATAOUT, RS.RESERVA
    """)
    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(statement, params).mappings()]


def build_client_calendar(
    engine,
    client_no: int,
    establishment: int = 0,
    *,
    lodging: Any = None,
    start: Any = None,
    months: Any = None,
    include_cancelled: bool = False,
    today: date | None = None,
) -> dict[str, Any]:
    if int(client_no or 0) <= 0:
        raise ClientCalendarError("Cliente associado inválido.")
    window = calendar_window(start, months, today=today)
    lodgings = _owner_lodgings(engine, int(client_no), int(establishment or 0))
    requested = _clean(lodging)
    if requested and requested not in lodgings:
        raise ClientCalendarError("O alojamento selecionado não pertence a este proprietário.")
    selected = requested or (lodgings[0] if lodgings else "")
    raw_rows = (
        _reservation_rows(
            engine,
            int(client_no),
            int(establishment or 0),
            selected,
            window,
            bool(include_cancelled),
        )
        if selected
        else []
    )
    reservations = []
    for row in raw_rows:
        checkin = _as_date(row.get("DATAIN"))
        checkout = _as_date(row.get("DATAOUT"))
        if not checkin or not checkout:
            continue
        stay_value = _as_money(row.get("ESTADIA"))
        cleaning_value = _as_money(row.get("LIMPEZA"))
        platform_commission = _as_money(row.get("COMISSAO"))
        invoice_cleaning = bool(row.get("FTLIMPEZA") or 0)
        total_value = _as_money(stay_value + cleaning_value)
        net_value = _as_money(
            stay_value - platform_commission
            if invoice_cleaning
            else total_value - platform_commission
        )
        reservations.append({
            "rsstamp": _clean(row.get("RSSTAMP")),
            "reservation": _clean(row.get("RESERVA")),
            "lodging": _clean(row.get("ALOJAMENTO")) or selected,
            "checkin": checkin.isoformat(),
            "checkout": checkout.isoformat(),
            "checkin_time": _clean(row.get("HORAIN")),
            "checkout_time": _clean(row.get("HORAOUT")),
            "guest": _clean(row.get("HOSPEDE")),
            "people": int(row.get("ADULTOS") or 0) + int(row.get("CRIANCAS") or 0) + int(row.get("BEBES") or 0),
            "origin": _clean(row.get("ORIGEM")),
            "stay_value": stay_value,
            "cleaning_value": cleaning_value,
            "platform_commission": platform_commission,
            "total_value": total_value,
            "net_value": net_value,
            "cancellation_value": _as_money(row.get("PCANCEL")),
            "cancelled": bool(row.get("CANCELADA") or 0),
            "cancelled_at": _as_date(row.get("DTCANCEL")).isoformat() if _as_date(row.get("DTCANCEL")) else None,
        })
    return {
        "lodgings": lodgings,
        "selected_lodging": selected,
        "start": window["start"].isoformat(),
        "end": window["end"].isoformat(),
        "months": window["months"],
        "include_cancelled": bool(include_cancelled),
        "reservations": reservations,
    }
