"""Read-only aggregates for the private StationZero PortoBreak dashboard."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import bindparam, inspect, select, text

from services.booking_portal_analytics_store import (
    conversions, pageviews, sessions, totals,
)


LISBON = ZoneInfo("Europe/Lisbon")
VALIDATION_SOURCES = frozenset({"codex-validation", "stationzero-validation"})
MAX_RANGE_DAYS = 180
PAGE_LABELS = {
    "catalog": "Catálogo",
    "property": "Alojamento",
    "booking_form": "Formulário de reserva",
    "payment_result": "Resultado do pagamento",
    "map_quote": "Simulação no mapa",
    "login": "Entrada na conta",
    "my_bookings": "As minhas reservas",
    "cancellation_policy": "Política de cancelamento",
    "terms": "Termos e condições",
    "privacy": "Política de privacidade",
    "cookies": "Política de cookies",
    "legal": "Informação legal",
}


class DashboardPeriodError(ValueError):
    pass


def _date(value, default):
    if not value:
        return default
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise DashboardPeriodError("Indique datas válidas.") from exc


def dashboard_period(start=None, end=None, *, today=None):
    today = today or datetime.now(LISBON).date()
    end_date = _date(end, today)
    start_date = _date(start, end_date - timedelta(days=29))
    if end_date < start_date:
        raise DashboardPeriodError("A data final não pode ser anterior à inicial.")
    if (end_date - start_date).days + 1 > MAX_RANGE_DAYS:
        raise DashboardPeriodError(f"O período máximo é de {MAX_RANGE_DAYS} dias.")
    start_local = datetime.combine(start_date, time.min, LISBON)
    end_local = datetime.combine(end_date + timedelta(days=1), time.min, LISBON)
    return {
        "start": start_date,
        "end": end_date,
        "start_utc": start_local.astimezone(timezone.utc).replace(tzinfo=None),
        "end_utc": end_local.astimezone(timezone.utc).replace(tzinfo=None),
        "days": (end_date - start_date).days + 1,
    }


def _local_day(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(LISBON).date()


def _iso(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(LISBON).isoformat(timespec="seconds")


def _pct(numerator, denominator):
    return round((numerator / denominator * 100), 1) if denominator else None


def _seconds(value):
    value = max(0, int(value or 0))
    return value


def _rank(counter, *, limit=10, labels=None, total=None):
    total = sum(counter.values()) if total is None else total
    labels = labels or {}
    return [
        {
            "key": str(key or "unknown"),
            "label": labels.get(key, str(key or "Desconhecido")),
            "value": int(value),
            "share": _pct(value, total),
        }
        for key, value in counter.most_common(limit)
    ]


def _search_summary(rows):
    with_query = with_dates = total_nights = nights_count = total_guests = guests_count = 0
    checkin_months = Counter()
    for row in rows:
        try:
            values = json.loads(row.get("search_json") or "{}")
        except (TypeError, ValueError):
            values = {}
        if values.get("has_query"):
            with_query += 1
        checkin, checkout = values.get("checkin"), values.get("checkout")
        if checkin and checkout:
            try:
                start, finish = date.fromisoformat(checkin), date.fromisoformat(checkout)
                nights = (finish - start).days
                if 0 < nights <= 365:
                    with_dates += 1
                    total_nights += nights
                    nights_count += 1
                    checkin_months[start.strftime("%Y-%m")] += 1
            except ValueError:
                pass
        guests = sum(int(values.get(key) or 0) for key in ("adultos", "criancas", "bebes"))
        if guests:
            total_guests += guests
            guests_count += 1
    return {
        "pageviews_with_text_query": with_query,
        "pageviews_with_dates": with_dates,
        "average_nights": round(total_nights / nights_count, 1) if nights_count else None,
        "average_guests": round(total_guests / guests_count, 1) if guests_count else None,
        "checkin_months": _rank(checkin_months, limit=12),
    }


def _table_names(engine):
    return {name.upper() for name in inspect(engine).get_table_names()}


def _property_names(conn, ids, table_names):
    ids = sorted({str(value).strip() for value in ids if value})
    if not ids or "AL" not in table_names:
        return {}
    table = "dbo.AL" if conn.dialect.name == "mssql" else "AL"
    statement = text(f"""
        SELECT LTRIM(RTRIM(ALSTAMP)) AS id,
               COALESCE(NULLIF(TRIM(COALESCE(NMAIRBNB, '')), ''),
                        NULLIF(TRIM(COALESCE(NOME, '')), ''),
                        TRIM(COALESCE(NMPESQUISA, ''))) AS name
        FROM {table}
        WHERE LTRIM(RTRIM(ALSTAMP)) IN :ids
    """).bindparams(bindparam("ids", expanding=True))
    try:
        return {str(row["id"]): str(row["name"] or row["id"]) for row in conn.execute(statement, {"ids": ids}).mappings()}
    except Exception:
        return {}


def _booking_details(conn, booking_ids, table_names):
    booking_ids = sorted({str(value).strip() for value in booking_ids if value})
    result = {booking_id: {"paid": False, "property_id": ""} for booking_id in booking_ids}
    if not booking_ids or "PB_BOOKING_REQUESTS" not in table_names:
        return result
    prefix = "dbo." if conn.dialect.name == "mssql" else ""
    booking_sql = text(f"""
        SELECT PBBKSTAMP AS booking_id, TRIM(COALESCE(ALSTAMP, '')) AS property_id
        FROM {prefix}PB_BOOKING_REQUESTS WHERE PBBKSTAMP IN :ids
    """).bindparams(bindparam("ids", expanding=True))
    for row in conn.execute(booking_sql, {"ids": booking_ids}).mappings():
        result[str(row["booking_id"])] = {"paid": False, "property_id": str(row["property_id"] or "")}
    if "PB_STRIPE_TEST_PAYMENTS" in table_names:
        payment_sql = text(f"""
            SELECT DISTINCT PBBKSTAMP AS booking_id
            FROM {prefix}PB_STRIPE_TEST_PAYMENTS
            WHERE PBBKSTAMP IN :ids AND UPPER(COALESCE(AMBIENTE, '')) = 'LIVE'
              AND (UPPER(COALESCE(ESTADO, '')) = 'PAGO' OR LOWER(COALESCE(STRIPE_STATUS, '')) = 'paid')
        """).bindparams(bindparam("ids", expanding=True))
        for row in conn.execute(payment_sql, {"ids": booking_ids}).mappings():
            booking_id = str(row["booking_id"])
            result.setdefault(booking_id, {"property_id": ""})["paid"] = True
    return result


def _validation_session(row):
    return str(row.get("source") or "").strip().lower() in VALIDATION_SOURCES


def build_dashboard(engine, period, *, include_bots=False, include_validation=False):
    start_utc, end_utc = period["start_utc"], period["end_utc"]
    with engine.connect() as conn:
        total_rows = [dict(row) for row in conn.execute(
            select(totals).where(totals.c.hour >= start_utc, totals.c.hour < end_utc)
        ).mappings()]
        session_rows = [dict(row) for row in conn.execute(
            select(sessions).where(sessions.c.started_at >= start_utc, sessions.c.started_at < end_utc)
        ).mappings()]
        session_by_id = {row["session_id"]: row for row in session_rows}
        page_rows = [dict(row) for row in conn.execute(
            select(pageviews).where(pageviews.c.created_at >= start_utc, pageviews.c.created_at < end_utc)
        ).mappings() if row["session_id"] in session_by_id]
        conversion_rows = [dict(row) for row in conn.execute(
            select(conversions).where(conversions.c.created_at >= start_utc, conversions.c.created_at < end_utc)
        ).mappings() if row["session_id"] in session_by_id]
        table_names = _table_names(engine)

        validation_ids = {row["session_id"] for row in session_rows if _validation_session(row)}
        validation_accesses = sum(
            int(row.get("requests") or 0)
            for row in total_rows
            if str(row.get("source") or "").strip().lower() in VALIDATION_SOURCES
        )
        if not include_validation:
            total_rows = [
                row for row in total_rows
                if str(row.get("source") or "").strip().lower() not in VALIDATION_SOURCES
            ]
            session_rows = [row for row in session_rows if row["session_id"] not in validation_ids]
            page_rows = [row for row in page_rows if row["session_id"] not in validation_ids]
            conversion_rows = [row for row in conversion_rows if row["session_id"] not in validation_ids]
        bot_accesses = sum(int(row.get("requests") or 0) for row in total_rows if row.get("is_bot"))
        if not include_bots:
            total_rows = [row for row in total_rows if not row.get("is_bot")]

        visible_session_ids = {row["session_id"] for row in session_rows}
        page_rows = [row for row in page_rows if row["session_id"] in visible_session_ids]
        conversion_rows = [row for row in conversion_rows if row["session_id"] in visible_session_ids]
        booking_details = _booking_details(conn, [row["booking_id"] for row in conversion_rows], table_names)

        property_ids = [row.get("property_id") for row in total_rows]
        property_ids.extend(row.get("property_id") for row in page_rows)
        property_ids.extend(item.get("property_id") for item in booking_details.values())
        property_names = _property_names(conn, property_ids, table_names)

    accesses = sum(int(row.get("requests") or 0) for row in total_rows)
    visitor_count = len({row["visitor_id"] for row in session_rows})
    session_count = len(session_rows)
    pageview_count = len(page_rows)
    booking_count = len(conversion_rows)
    paid_count = sum(1 for row in conversion_rows if booking_details.get(row["booking_id"], {}).get("paid"))
    active_total = sum(_seconds(row.get("active_seconds")) for row in session_rows)
    single_page = sum(1 for row in session_rows if int(row.get("page_views") or 0) <= 1)

    days = []
    cursor = period["start"]
    while cursor <= period["end"]:
        days.append(cursor)
        cursor += timedelta(days=1)
    series = {day: {"date": day.isoformat(), "accesses": 0, "visitors": set(), "sessions": 0,
                    "pageviews": 0, "bookings": 0, "paid": 0} for day in days}
    for row in total_rows:
        day = _local_day(row.get("hour"))
        if day in series:
            series[day]["accesses"] += int(row.get("requests") or 0)
    for row in session_rows:
        day = _local_day(row.get("started_at"))
        if day in series:
            series[day]["sessions"] += 1
            series[day]["visitors"].add(row["visitor_id"])
    for row in page_rows:
        day = _local_day(row.get("created_at"))
        if day in series:
            series[day]["pageviews"] += 1
    for row in conversion_rows:
        day = _local_day(row.get("created_at"))
        if day in series:
            series[day]["bookings"] += 1
            if booking_details.get(row["booking_id"], {}).get("paid"):
                series[day]["paid"] += 1
    timeline = []
    for day in days:
        item = series[day]
        item["visitors"] = len(item["visitors"])
        timeline.append(item)

    source_counts = Counter()
    for row in total_rows:
        source = str(row.get("source") or "unknown")
        # Internal page-to-page navigation is activity, not acquisition.
        if source != "internal":
            source_counts[source] += int(row.get("requests") or 0)
    source_sessions = Counter(str(row.get("source") or "unknown") for row in session_rows)
    source_conversions = Counter()
    session_lookup = {row["session_id"]: row for row in session_rows}
    for row in conversion_rows:
        source_conversions[str(session_lookup[row["session_id"]].get("source") or "unknown")] += 1
    source_breakdown = _rank(source_counts, limit=12)
    for item in source_breakdown:
        item["sessions"] = source_sessions.get(item["key"], 0)
        item["conversions"] = source_conversions.get(item["key"], 0)
        item["conversion_rate"] = _pct(item["conversions"], item["sessions"])

    page_counts = Counter()
    for row in total_rows:
        page_counts[str(row.get("page_kind") or "unknown")] += int(row.get("requests") or 0)
    page_active = Counter()
    for row in page_rows:
        page_active[str(row.get("page_kind") or "unknown")] += _seconds(row.get("active_seconds"))
    page_breakdown = _rank(page_counts, limit=20, labels=PAGE_LABELS)
    for item in page_breakdown:
        item["active_seconds"] = page_active[item["key"]]

    property_views = Counter()
    for row in total_rows:
        if row.get("property_id"):
            property_views[str(row["property_id"])] += int(row.get("requests") or 0)
    property_active = Counter()
    for row in page_rows:
        if row.get("property_id"):
            property_active[str(row["property_id"])] += _seconds(row.get("active_seconds"))
    property_bookings = Counter()
    property_paid = Counter()
    for row in conversion_rows:
        detail = booking_details.get(row["booking_id"], {})
        property_id = detail.get("property_id")
        if property_id:
            property_bookings[property_id] += 1
            property_paid[property_id] += int(bool(detail.get("paid")))
    property_keys = set(property_views) | set(property_bookings)
    properties = sorted(({
        "property_id": key,
        "name": property_names.get(key, key),
        "views": property_views[key],
        "active_seconds": property_active[key],
        "bookings": property_bookings[key],
        "paid": property_paid[key],
        "conversion_rate": _pct(property_bookings[key], property_views[key]),
    } for key in property_keys), key=lambda row: (row["views"], row["bookings"]), reverse=True)[:20]

    recent = []
    converted_sessions = {row["session_id"] for row in conversion_rows}
    paid_sessions = {row["session_id"] for row in conversion_rows if booking_details.get(row["booking_id"], {}).get("paid")}
    for row in sorted(session_rows, key=lambda item: item.get("started_at") or datetime.min, reverse=True)[:50]:
        recent.append({
            "started_at": _iso(row.get("started_at")),
            "last_seen_at": _iso(row.get("last_seen_at")),
            "country": str(row.get("country") or "ZZ"),
            "country_source": str(row.get("country_source") or "unknown"),
            "device": str(row.get("device") or "unknown"),
            "browser": str(row.get("browser") or "unknown"),
            "os": str(row.get("os") or "unknown"),
            "language": str(row.get("language") or ""),
            "source": str(row.get("source") or "unknown"),
            "medium": str(row.get("medium") or ""),
            "campaign": str(row.get("campaign") or ""),
            "page_views": int(row.get("page_views") or 0),
            "active_seconds": _seconds(row.get("active_seconds")),
            "converted": row["session_id"] in converted_sessions,
            "paid": row["session_id"] in paid_sessions,
        })

    country_accesses = Counter()
    device_accesses = Counter()
    for row in total_rows:
        request_count = int(row.get("requests") or 0)
        country_accesses[str(row.get("country") or "ZZ")] += request_count
        device_accesses[str(row.get("device") or "unknown")] += request_count

    return {
        "generated_at": _iso(datetime.now(timezone.utc)),
        "period": {"start": period["start"].isoformat(), "end": period["end"].isoformat(), "days": period["days"]},
        "filters": {"include_bots": bool(include_bots), "include_validation": bool(include_validation)},
        "kpis": {
            "accesses": accesses,
            "bot_accesses": bot_accesses,
            "visitors": visitor_count,
            "sessions": session_count,
            "pageviews": pageview_count,
            "pageviews_per_session": round(pageview_count / session_count, 1) if session_count else None,
            "average_active_seconds": round(active_total / session_count) if session_count else None,
            "single_page_rate": _pct(single_page, session_count),
            "bookings": booking_count,
            "paid_bookings": paid_count,
            "session_conversion_rate": _pct(booking_count, session_count),
            "payment_rate": _pct(paid_count, booking_count),
        },
        "timeline": timeline,
        "sources": source_breakdown,
        "countries": _rank(country_accesses, limit=20),
        "devices": _rank(device_accesses),
        "browsers": _rank(Counter(str(row.get("browser") or "unknown") for row in session_rows)),
        "operating_systems": _rank(Counter(str(row.get("os") or "unknown") for row in session_rows)),
        "languages": _rank(Counter(str(row.get("language") or "unknown") for row in session_rows)),
        "pages": page_breakdown,
        "properties": properties,
        "searches": {
            **_search_summary(page_rows),
            "accesses_with_search": sum(
                int(row.get("requests") or 0) for row in total_rows if row.get("has_search")
            ),
        },
        "recent_sessions": recent,
        "data_quality": {
            "unknown_country_sessions": sum(1 for row in session_rows if str(row.get("country") or "ZZ") == "ZZ"),
            "unknown_country_accesses": sum(
                int(row.get("requests") or 0) for row in total_rows if str(row.get("country") or "ZZ") == "ZZ"
            ),
            "validation_sessions_excluded": len(validation_ids) if not include_validation else 0,
            "validation_accesses_excluded": validation_accesses if not include_validation else 0,
            "gender_known": 0,
            "age_band_known": 0,
            "granular_retention_days": 90,
            "aggregate_retention_days": 180,
        },
        "definitions": {
            "accesses": "Pedidos de páginas públicas, não pessoas únicas.",
            "visitors": "Navegadores com consentimento, não pessoas garantidamente distintas.",
            "active_time": "Tempo estimado com a página visível e atividade recente.",
            "country": "País aproximado da ligação; não representa nacionalidade.",
        },
    }
