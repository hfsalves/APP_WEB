"""Read-only operational dashboard for PortoBreak portal reservations."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from sqlalchemy import inspect, text


LISBON = ZoneInfo("Europe/Lisbon")
MAX_RANGE_DAYS = 730
STATUS_LABELS = {
    "pending": "Pendente",
    "checkout": "Checkout iniciado",
    "paid": "Paga",
    "confirmed": "Confirmada",
    "failed": "Pagamento falhado",
    "expired": "Checkout expirado",
    "cancelled": "Cancelada",
}
VALID_STATUSES = frozenset(STATUS_LABELS)
VALID_ENVIRONMENTS = frozenset({"LIVE", "TEST"})


class ReservationsDashboardError(ValueError):
    pass


def _date(value, default):
    if not value:
        return default
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ReservationsDashboardError("Indique datas válidas.") from exc


def reservations_period(start=None, end=None, *, today=None):
    today = today or datetime.now(LISBON).date()
    end_date = _date(end, today)
    start_date = _date(start, end_date - timedelta(days=89))
    if end_date < start_date:
        raise ReservationsDashboardError("A data final não pode ser anterior à inicial.")
    if (end_date - start_date).days + 1 > MAX_RANGE_DAYS:
        raise ReservationsDashboardError(f"O período máximo é de {MAX_RANGE_DAYS} dias.")
    start_local = datetime.combine(start_date, time.min, LISBON)
    end_local = datetime.combine(end_date + timedelta(days=1), time.min, LISBON)
    return {
        "start": start_date,
        "end": end_date,
        "start_utc": start_local.astimezone(timezone.utc).replace(tzinfo=None),
        "end_utc": end_local.astimezone(timezone.utc).replace(tzinfo=None),
        "days": (end_date - start_date).days + 1,
    }


def dashboard_filters(values):
    values = values or {}
    status = str(values.get("status") or "").strip().lower()
    environment = str(values.get("environment") or "").strip().upper()
    return {
        "status": status if status in VALID_STATUSES else "",
        "property_id": str(values.get("property_id") or "").strip(),
        "environment": environment if environment in VALID_ENVIRONMENTS else "",
        "query": str(values.get("query") or "").strip()[:120],
        "page": max(1, _int(values.get("page"), 1)),
        "page_size": min(100, max(10, _int(values.get("page_size"), 25))),
    }


def _int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _decimal(value):
    try:
        return Decimal(str(value or 0))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def _date_value(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = str(value or "").strip()
    try:
        return date.fromisoformat(raw[:10]) if raw else None
    except ValueError:
        return None


def _datetime_value(value):
    if isinstance(value, datetime):
        return value
    raw = str(value or "").strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(raw) if raw else None
    except ValueError:
        return None


def _lisbon_iso(value):
    parsed = _datetime_value(value)
    if not parsed:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(LISBON).isoformat(timespec="seconds")


def _money(value):
    return float(_decimal(value).quantize(Decimal("0.01")))


def _derived_status(row):
    request_state = str(row.get("request_status") or "").strip().upper()
    payment_state = str(row.get("payment_status") or "").strip().upper()
    stripe_state = str(row.get("stripe_status") or "").strip().lower()
    if bool(row.get("cancelled")) or request_state == "CANCELADO":
        return "cancelled"
    if payment_state in {"PAGO", "PAGO_TESTE"} or stripe_state == "paid":
        return "paid"
    if payment_state == "FALHADO":
        return "failed"
    if payment_state == "EXPIRADO":
        return "expired"
    if payment_state == "CRIADO":
        return "checkout"
    if request_state == "CONFIRMADO":
        return "confirmed"
    return "pending"


def _empty_payload(period, filters):
    return {
        "period": {"start": period["start"].isoformat(), "end": period["end"].isoformat()},
        "filters": filters,
        "options": {"properties": [], "statuses": STATUS_LABELS},
        "kpis": {
            "requests": 0, "live_paid": 0, "live_revenue": 0.0, "test_paid": 0,
            "test_revenue": 0.0, "pending": 0, "nights_sold": 0, "average_ticket": None,
        },
        "status_breakdown": [], "timeline": [], "properties": [], "reservations": [],
        "pagination": {"page": 1, "page_size": filters["page_size"], "pages": 1, "total": 0},
    }


def _fetch_rows(conn, period, prefix):
    statement = text(f"""
        WITH payment_ranked AS (
            SELECT P.*,
                   ROW_NUMBER() OVER (
                       PARTITION BY P.PBBKSTAMP
                       ORDER BY COALESCE(P.DTALT, P.DTCRI) DESC, P.PBPAYSTAMP DESC
                   ) AS RN
            FROM {prefix}PB_STRIPE_TEST_PAYMENTS AS P
        )
        SELECT
            B.PBBKSTAMP AS booking_id,
            B.ALSTAMP AS property_id,
            B.AL_NOME AS property_name,
            B.CHECKIN AS checkin,
            B.CHECKOUT AS checkout,
            B.NOITES AS nights,
            B.ADULTOS AS adults,
            B.CRIANCAS AS children,
            B.BEBES AS babies,
            B.CLIENTE_NOME AS customer_name,
            B.CLIENTE_EMAIL AS customer_email,
            B.CLIENTE_TELEFONE AS customer_phone,
            B.CLIENTE_PAIS AS customer_country,
            B.ESTADO AS request_status,
            B.PRECO_ESTIMADO AS estimated_value,
            B.DTCRI AS created_at,
            P.PBPAYSTAMP AS payment_id,
            P.ESTADO AS payment_status,
            P.AMBIENTE AS environment,
            P.MOEDA AS currency,
            P.VALOR AS paid_value,
            P.STRIPE_STATUS AS stripe_status,
            P.RSSTAMP AS rsstamp,
            R.RESERVA AS reservation_code,
            R.CANCELADA AS cancelled
        FROM {prefix}PB_BOOKING_REQUESTS AS B
        LEFT JOIN payment_ranked AS P ON P.PBBKSTAMP = B.PBBKSTAMP AND P.RN = 1
        LEFT JOIN {prefix}RS AS R ON R.RSSTAMP = P.RSSTAMP
        WHERE B.DTCRI >= :start_utc AND B.DTCRI < :end_utc
        ORDER BY B.DTCRI DESC, B.PBBKSTAMP DESC
    """)
    return [dict(row) for row in conn.execute(statement, {
        "start_utc": period["start_utc"], "end_utc": period["end_utc"],
    }).mappings()]


def _property_options(conn, prefix):
    rows = conn.execute(text(f"""
        SELECT B.ALSTAMP AS id, MAX(B.AL_NOME) AS name
        FROM {prefix}PB_BOOKING_REQUESTS AS B
        GROUP BY B.ALSTAMP
        ORDER BY MAX(B.AL_NOME)
    """)).mappings()
    return [{"id": str(row["id"] or ""), "name": str(row["name"] or row["id"] or "")} for row in rows]


def _matches(row, filters):
    if filters["status"] and row["status"] != filters["status"]:
        return False
    if filters["property_id"] and row["property_id"] != filters["property_id"]:
        return False
    if filters["environment"] and row["environment"] != filters["environment"]:
        return False
    query = filters["query"].casefold()
    if query:
        haystack = " ".join(str(row.get(key) or "") for key in (
            "reservation_code", "booking_id", "customer_name", "customer_email", "property_name",
        )).casefold()
        if query not in haystack:
            return False
    return True


def _serialize(row):
    status = _derived_status(row)
    environment = str(row.get("environment") or "").strip().upper()
    payment_status = str(row.get("payment_status") or "").strip().upper()
    paid = status == "paid"
    return {
        "booking_id": str(row.get("booking_id") or ""),
        "property_id": str(row.get("property_id") or ""),
        "property_name": str(row.get("property_name") or ""),
        "checkin": (_date_value(row.get("checkin")) or "").isoformat() if _date_value(row.get("checkin")) else None,
        "checkout": (_date_value(row.get("checkout")) or "").isoformat() if _date_value(row.get("checkout")) else None,
        "nights": _int(row.get("nights")),
        "adults": _int(row.get("adults")),
        "children": _int(row.get("children")),
        "babies": _int(row.get("babies")),
        "customer_name": str(row.get("customer_name") or ""),
        "customer_email": str(row.get("customer_email") or ""),
        "customer_phone": str(row.get("customer_phone") or ""),
        "customer_country": str(row.get("customer_country") or ""),
        "request_status": str(row.get("request_status") or "").strip().upper(),
        "status": status,
        "status_label": STATUS_LABELS[status],
        "estimated_value": _money(row.get("estimated_value")),
        "payment_status": payment_status,
        "environment": environment,
        "currency": str(row.get("currency") or "EUR").strip().upper(),
        "paid_value": _money(row.get("paid_value")) if row.get("paid_value") is not None else None,
        "paid": paid,
        "live_paid": paid and environment == "LIVE",
        "test_paid": paid and environment == "TEST",
        "reservation_code": str(row.get("reservation_code") or "").strip(),
        "rsstamp": str(row.get("rsstamp") or "").strip(),
        "created_at": _lisbon_iso(row.get("created_at")),
    }


def build_reservations_dashboard(engine, period, filters=None):
    filters = dashboard_filters(filters)
    table_names = {name.upper() for name in inspect(engine).get_table_names()}
    required = {"PB_BOOKING_REQUESTS", "PB_STRIPE_TEST_PAYMENTS", "RS"}
    if not required.issubset(table_names):
        return _empty_payload(period, filters)

    prefix = "dbo." if engine.dialect.name == "mssql" else ""
    with engine.connect() as conn:
        raw_rows = _fetch_rows(conn, period, prefix)
        property_options = _property_options(conn, prefix)

    rows = [_serialize(row) for row in raw_rows]
    rows = [row for row in rows if _matches(row, filters)]
    status_counts = Counter(row["status"] for row in rows)
    live_rows = [row for row in rows if row["live_paid"]]
    test_rows = [row for row in rows if row["test_paid"]]
    live_revenue = sum((_decimal(row["paid_value"]) for row in live_rows), Decimal("0"))
    test_revenue = sum((_decimal(row["paid_value"]) for row in test_rows), Decimal("0"))

    timeline = defaultdict(lambda: {"requests": 0, "paid": 0, "live_revenue": Decimal("0")})
    properties = defaultdict(lambda: {
        "requests": 0, "live_paid": 0, "test_paid": 0,
        "live_revenue": Decimal("0"), "live_nights": 0,
    })
    for row in rows:
        created = _datetime_value(row["created_at"])
        if created:
            key = created.date().isoformat()
            timeline[key]["requests"] += 1
            timeline[key]["paid"] += int(row["paid"])
            if row["live_paid"]:
                timeline[key]["live_revenue"] += _decimal(row["paid_value"])
        prop = properties[(row["property_id"], row["property_name"])]
        prop["requests"] += 1
        if row["live_paid"]:
            prop["live_paid"] += 1
            prop["live_nights"] += row["nights"]
            prop["live_revenue"] += _decimal(row["paid_value"])
        if row["test_paid"]:
            prop["test_paid"] += 1

    total = len(rows)
    pages = max(1, (total + filters["page_size"] - 1) // filters["page_size"])
    page = min(filters["page"], pages)
    offset = (page - 1) * filters["page_size"]
    page_rows = rows[offset:offset + filters["page_size"]]

    return {
        "period": {"start": period["start"].isoformat(), "end": period["end"].isoformat()},
        "filters": dict(filters, page=page),
        "options": {"properties": property_options, "statuses": STATUS_LABELS},
        "kpis": {
            "requests": total,
            "live_paid": len(live_rows),
            "live_revenue": _money(live_revenue),
            "test_paid": len(test_rows),
            "test_revenue": _money(test_revenue),
            "pending": status_counts["pending"] + status_counts["checkout"],
            "nights_sold": sum(row["nights"] for row in live_rows),
            "average_ticket": _money(live_revenue / len(live_rows)) if live_rows else None,
        },
        "status_breakdown": [
            {"key": key, "label": label, "value": status_counts[key]}
            for key, label in STATUS_LABELS.items() if status_counts[key]
        ],
        "timeline": [
            {"date": key, "requests": value["requests"], "paid": value["paid"], "live_revenue": _money(value["live_revenue"])}
            for key, value in sorted(timeline.items())
        ],
        "properties": [
            {
                "id": key[0], "name": key[1], "requests": value["requests"],
                "live_paid": value["live_paid"], "test_paid": value["test_paid"],
                "live_revenue": _money(value["live_revenue"]), "live_nights": value["live_nights"],
            }
            for key, value in sorted(properties.items(), key=lambda item: (-item[1]["requests"], item[0][1]))
        ],
        "reservations": page_rows,
        "pagination": {"page": page, "page_size": filters["page_size"], "pages": pages, "total": total},
    }
