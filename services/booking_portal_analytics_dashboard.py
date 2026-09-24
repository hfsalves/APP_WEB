"""Read-only PortoBreak Analytics v2 aggregates for the StationZero dashboard.

Commercial metrics only use consented sessions. HTTP request buckets remain
technical diagnostics and are never labelled as visitors or visits.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import bindparam, inspect, select, text

from services.booking_portal_analytics_store import conversions, events, pageviews, sessions, totals

LISBON = ZoneInfo("Europe/Lisbon")
VALIDATION_SOURCES = frozenset({"codex-validation", "stationzero-validation"})
MAX_RANGE_DAYS = 180
TRAFFIC_FILTERS = {
    # Legacy sessions predate v2 scoring.  They remain available under
    # "Todos", but are deliberately not treated as commercial human traffic.
    "commercial": frozenset({"HUMAN", "LIKELY_HUMAN"}),
    "human": frozenset({"HUMAN"}), "likely_human": frozenset({"LIKELY_HUMAN"}),
    "suspected": frozenset({"SUSPECTED_BOT"}), "bots": frozenset({"BOT"}), "all": None,
}
PAGE_LABELS = {
    "catalog": "Catálogo", "property": "Alojamento", "booking_form": "Checkout",
    "payment_result": "Resultado do pagamento", "map_quote": "Simulação no mapa",
    "login": "Entrada na conta", "my_bookings": "As minhas reservas",
    "cancellation_policy": "Política de cancelamento", "terms": "Termos e condições",
    "privacy": "Política de privacidade", "cookies": "Política de cookies", "legal": "Informação legal",
}
CLASS_LABELS = {"HUMAN": "Humano", "LIKELY_HUMAN": "Provavelmente humano",
                "SUSPECTED_BOT": "Suspeito", "BOT": "Bot", "UNKNOWN": "Não atribuível",
                "LEGACY": "Histórico (legacy)"}


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
    start_local, end_local = datetime.combine(start_date, time.min, LISBON), datetime.combine(end_date + timedelta(days=1), time.min, LISBON)
    return {"start": start_date, "end": end_date, "start_utc": start_local.astimezone(timezone.utc).replace(tzinfo=None),
            "end_utc": end_local.astimezone(timezone.utc).replace(tzinfo=None), "days": (end_date - start_date).days + 1}


def _local_day(value):
    if value is None:
        return None
    return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value).astimezone(LISBON).date()


def _iso(value):
    if value is None:
        return None
    return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value).astimezone(LISBON).isoformat(timespec="seconds")


def _seconds(value): return max(0, int(value or 0))
def _pct(a, b): return round(a / b * 100, 1) if b else None


def _rank(counter, *, limit=20, labels=None, total=None):
    labels, total = labels or {}, sum(counter.values()) if total is None else total
    return [{"key": str(key or "unknown"), "label": labels.get(key, str(key or "Desconhecido")), "value": int(value), "share": _pct(value, total)}
            for key, value in counter.most_common(limit)]


def _class(row):
    if bool(row.get("is_bot")):
        return "BOT"
    value = str(row.get("traffic_class") or "LEGACY").upper()
    return value if value in CLASS_LABELS else "LEGACY"


def _request_reason(row):
    """Keep the historical explicit bot marker intelligible after v2.

    Older aggregate rows have no score/reason columns.  Their ``is_bot`` value
    is still a valid historical classification, but must not be displayed as a
    mysterious ``legacy`` reason.
    """
    reason = str(row.get("classification_reason") or "").strip()
    if bool(row.get("is_bot")) and (not reason or reason == "legacy"):
        return "known_bot_legacy"
    return reason or "unspecified"


def _request_score(row):
    score = int(row.get("bot_score") or 0)
    return 100 if bool(row.get("is_bot")) and score == 0 else score


def _in_quality(row, traffic):
    allowed = TRAFFIC_FILTERS.get(traffic, TRAFFIC_FILTERS["commercial"])
    return allowed is None or _class(row) in allowed


def _validation(row): return str(row.get("source") or "").strip().lower() in VALIDATION_SOURCES


def _search(row):
    try: return json.loads(row.get("search_json") or "{}")
    except (TypeError, ValueError): return {}


def _estimated_entry_key(row):
    """Conservative anonymous-entry estimate, with no persistent identity.

    The aggregate table deliberately contains no IP, cookie or browser
    fingerprint.  One entry is therefore counted per matching hour/context,
    after removing known and suspected automation.  It is a useful commercial
    estimate, not a claim of perfectly deduplicated people.
    """
    return (
        row.get("hour"), str(row.get("country") or "ZZ"),
        str(row.get("device") or "unknown"), str(row.get("source") or "unknown"),
        str(row.get("referrer_host") or ""), str(row.get("currency") or "EUR"),
        bool(row.get("has_search")),
    )


def _names(conn, ids, tables):
    ids = sorted({str(value).strip() for value in ids if value})
    if not ids or "AL" not in tables: return {}
    table = "dbo.AL" if conn.dialect.name == "mssql" else "AL"
    statement = text(f"""SELECT LTRIM(RTRIM(ALSTAMP)) AS id,
        COALESCE(NULLIF(TRIM(COALESCE(NMAIRBNB, '')), ''), NULLIF(TRIM(COALESCE(NOME, '')), ''), TRIM(COALESCE(NMPESQUISA, ''))) AS name
        FROM {table} WHERE LTRIM(RTRIM(ALSTAMP)) IN :ids""").bindparams(bindparam("ids", expanding=True))
    try: return {str(row["id"]): str(row["name"] or row["id"]) for row in conn.execute(statement, {"ids": ids}).mappings()}
    except Exception: return {}


def _booking_details(conn, booking_ids, tables):
    booking_ids = sorted({str(value).strip() for value in booking_ids if value})
    result = {item: {"paid": False, "property_id": ""} for item in booking_ids}
    if not booking_ids or "PB_BOOKING_REQUESTS" not in tables: return result
    prefix = "dbo." if conn.dialect.name == "mssql" else ""
    query = text(f"SELECT PBBKSTAMP AS booking_id, TRIM(COALESCE(ALSTAMP, '')) AS property_id FROM {prefix}PB_BOOKING_REQUESTS WHERE PBBKSTAMP IN :ids").bindparams(bindparam("ids", expanding=True))
    for row in conn.execute(query, {"ids": booking_ids}).mappings(): result[str(row["booking_id"])] = {"paid": False, "property_id": str(row["property_id"] or "")}
    if "PB_STRIPE_TEST_PAYMENTS" in tables:
        query = text(f"""SELECT DISTINCT PBBKSTAMP AS booking_id FROM {prefix}PB_STRIPE_TEST_PAYMENTS
            WHERE PBBKSTAMP IN :ids AND UPPER(COALESCE(AMBIENTE, '')) = 'LIVE'
              AND (UPPER(COALESCE(ESTADO, '')) = 'PAGO' OR LOWER(COALESCE(STRIPE_STATUS, '')) = 'paid')"""
        ).bindparams(bindparam("ids", expanding=True))
        for row in conn.execute(query, {"ids": booking_ids}).mappings(): result.setdefault(str(row["booking_id"]), {"property_id": ""})["paid"] = True
    return result


def build_dashboard(engine, period, *, traffic="commercial", include_bots=False, include_validation=False):
    """Return commercial metrics plus separate, non-person technical requests."""
    traffic = "all" if include_bots else traffic if traffic in TRAFFIC_FILTERS else "commercial"
    start, end = period["start_utc"], period["end_utc"]
    with engine.connect() as conn:
        total_rows = [dict(x) for x in conn.execute(select(totals).where(totals.c.hour >= start, totals.c.hour < end)).mappings()]
        all_sessions = [dict(x) for x in conn.execute(select(sessions).where(sessions.c.started_at >= start, sessions.c.started_at < end)).mappings()]
        ids = {x["session_id"] for x in all_sessions}
        all_pages = [dict(x) for x in conn.execute(select(pageviews).where(pageviews.c.created_at >= start, pageviews.c.created_at < end)).mappings() if x["session_id"] in ids]
        all_events = [dict(x) for x in conn.execute(select(events).where(events.c.created_at >= start, events.c.created_at < end)).mappings() if x["session_id"] in ids]
        all_conversions = [dict(x) for x in conn.execute(select(conversions).where(conversions.c.created_at >= start, conversions.c.created_at < end)).mappings() if x["session_id"] in ids]
        table_names = {name.upper() for name in inspect(engine).get_table_names()}
        booking_details = _booking_details(conn, [x["booking_id"] for x in all_conversions], table_names)
        property_names = _names(conn, [x.get("property_id") for x in all_pages] + [x.get("property_id") for x in booking_details.values()], table_names)

    validation_ids = {x["session_id"] for x in all_sessions if _validation(x)}
    validation_requests = sum(int(x.get("requests") or 0) for x in total_rows if _validation(x))
    if not include_validation:
        total_rows = [x for x in total_rows if not _validation(x)]
        all_sessions = [x for x in all_sessions if x["session_id"] not in validation_ids]
        ids = {x["session_id"] for x in all_sessions}
        all_pages, all_events, all_conversions = ([x for x in rows if x["session_id"] in ids] for rows in (all_pages, all_events, all_conversions))

    session_rows = [x for x in all_sessions if _in_quality(x, traffic)]
    visible = {x["session_id"] for x in session_rows}
    page_rows, event_rows, conversion_rows = ([x for x in rows if x["session_id"] in visible] for rows in (all_pages, all_events, all_conversions))
    by_id = {x["session_id"]: x for x in session_rows}
    event_names = defaultdict(set)
    for row in event_rows: event_names[row["session_id"]].add(str(row.get("event_name") or ""))

    searched = {x["session_id"] for x in event_rows if x.get("event_name") == "SEARCH"}
    searched |= {x["session_id"] for x in page_rows if _search(x).get("checkin") and _search(x).get("checkout")}
    results = {x["session_id"] for x in page_rows if x.get("page_kind") == "catalog" and _search(x)}
    property_sessions = {x["session_id"] for x in page_rows if x.get("page_kind") == "property"}
    checkouts = {x["session_id"] for x in event_rows if x.get("event_name") == "CHECKOUT_START"} | {x["session_id"] for x in conversion_rows}
    payments = {x["session_id"] for x in event_rows if x.get("event_name") == "PAYMENT_START"} | {x["session_id"] for x in conversion_rows if x.get("payment_started_at")}
    successful_ids = {x["booking_id"] for x in conversion_rows if x.get("booking_success_at") or booking_details.get(x["booking_id"], {}).get("paid")}
    booked_sessions = {x["session_id"] for x in conversion_rows if x["booking_id"] in successful_ids}

    request_counts, reason_counts = Counter(), Counter()
    for row in total_rows:
        n = int(row.get("requests") or 0); request_counts[_class(row)] += n; reason_counts[_request_reason(row)] += n
    total_requests = sum(request_counts.values())
    confirmed_visitors = len({x["visitor_id"] for x in session_rows})
    estimated_entries = {
        _estimated_entry_key(row) for row in total_rows
        if _class(row) not in {"BOT", "SUSPECTED_BOT"}
    }
    estimated_visitors = len(estimated_entries)
    sessions_count, pageview_count = len(session_rows), len(page_rows)

    days, cursor = [], period["start"]
    while cursor <= period["end"]: days.append(cursor); cursor += timedelta(days=1)
    timeline = {day: {"date": day.isoformat(), "requests": 0, "estimated_visitors": 0, "visitors": set(), "sessions": 0, "pageviews": 0, "searches": 0, "checkouts": 0, "payments": 0, "bookings": 0} for day in days}
    for row in total_rows:
        if (day := _local_day(row.get("hour"))) in timeline: timeline[day]["requests"] += int(row.get("requests") or 0)
    for row in session_rows:
        if (day := _local_day(row.get("started_at"))) in timeline: timeline[day]["sessions"] += 1; timeline[day]["visitors"].add(row["visitor_id"])
    for entry in estimated_entries:
        if (day := _local_day(entry[0])) in timeline: timeline[day]["estimated_visitors"] += 1
    for row in page_rows:
        if (day := _local_day(row.get("created_at"))) in timeline: timeline[day]["pageviews"] += 1
    for values, name in ((searched, "searches"), (checkouts, "checkouts"), (payments, "payments"), (booked_sessions, "bookings")):
        for session_id in values:
            if (row := by_id.get(session_id)) and (day := _local_day(row.get("started_at"))) in timeline: timeline[day][name] += 1
    timeline_rows = []
    for day in days:
        item = timeline[day]; item["visitors"] = len(item["visitors"]); timeline_rows.append(item)

    sources = Counter(str(x.get("source") or "unknown") for x in session_rows if str(x.get("source") or "") != "internal")
    countries = defaultdict(set)
    for row in session_rows: countries[str(row.get("country") or "ZZ")].add(row["visitor_id"])
    country_counts = Counter({key: len(value) for key, value in countries.items()})
    # Aggregate rows are useful historic technical evidence, but are never
    # presented as visitors. Keep them separately so v1 data stays visible.
    request_countries = Counter()
    request_pages = Counter()
    for row in total_rows:
        count = int(row.get("requests") or 0)
        request_countries[str(row.get("country") or "ZZ")] += count
        request_pages[str(row.get("page_kind") or "unknown")] += count
    estimated_countries = Counter(entry[1] for entry in estimated_entries)
    page_counts, page_active = Counter(), Counter()
    for row in page_rows: page_counts[str(row.get("page_kind") or "unknown")] += 1; page_active[str(row.get("page_kind") or "unknown")] += _seconds(row.get("active_seconds"))
    pages = _rank(page_counts, labels=PAGE_LABELS)
    for item in pages: item["active_seconds"] = page_active[item["key"]]
    property_views, property_active = Counter(), Counter()
    for row in page_rows:
        if row.get("property_id"): property_views[str(row["property_id"])] += 1; property_active[str(row["property_id"])] += _seconds(row.get("active_seconds"))
    property_bookings = Counter(booking_details.get(x["booking_id"], {}).get("property_id") for x in conversion_rows if x["booking_id"] in successful_ids)
    properties = sorted(({"property_id": key, "name": property_names.get(key, key), "views": property_views[key], "active_seconds": property_active[key], "bookings": property_bookings[key], "conversion_rate": _pct(property_bookings[key], property_views[key])} for key in set(property_views) | set(property_bookings)), key=lambda x: (x["views"], x["bookings"]), reverse=True)[:20]

    recent = []
    for row in sorted(session_rows, key=lambda x: x.get("started_at") or datetime.min, reverse=True)[:50]:
        sid = row["session_id"]
        recent.append({"started_at": _iso(row.get("started_at")), "country": str(row.get("country") or "ZZ"), "country_source": str(row.get("country_source") or "unknown"), "device": str(row.get("device") or "unknown"), "browser": str(row.get("browser") or "unknown"), "os": str(row.get("os") or "unknown"), "language": str(row.get("language") or ""), "source": str(row.get("source") or "unknown"), "page_views": int(row.get("page_views") or 0), "active_seconds": _seconds(row.get("active_seconds")), "traffic_class": _class(row), "bot_score": int(row.get("bot_score") or 0), "human_score": int(row.get("human_score") or 0), "classification_reason": str(row.get("classification_reason") or ""), "events": sorted(event_names[sid]), "checkout": sid in checkouts, "payment": sid in payments, "booked": sid in booked_sessions})

    diagnostic_classes = {"SUSPECTED_BOT", "BOT"} if traffic in {"suspected", "bots", "all"} else set()
    diagnostics = [{"kind": "request", "traffic_class": _class(x), "bot_score": _request_score(x), "reason": _request_reason(x), "country": str(x.get("country") or "ZZ"), "client": str(x.get("device") or "unknown"), "pages": PAGE_LABELS.get(str(x.get("page_kind") or ""), str(x.get("page_kind") or "")), "requests": int(x.get("requests") or 0), "active_seconds": None, "events": []} for x in sorted(total_rows, key=lambda x: int(x.get("requests") or 0), reverse=True) if _class(x) in diagnostic_classes]
    diagnostics += [{"kind": "session", "traffic_class": x["traffic_class"], "bot_score": x["bot_score"], "reason": x["classification_reason"], "country": x["country"], "client": f"{x['browser']} · {x['os']}", "pages": str(x["page_views"]), "requests": None, "active_seconds": x["active_seconds"], "events": x["events"]} for x in recent if x["traffic_class"] in diagnostic_classes]
    active = sum(_seconds(x.get("active_seconds")) for x in session_rows)
    search_contexts = [_search(x) for x in page_rows]
    nights, night_count, guests, guest_count = 0, 0, 0, 0
    for item in search_contexts:
        try:
            if item.get("checkin") and item.get("checkout"):
                duration = (date.fromisoformat(item["checkout"]) - date.fromisoformat(item["checkin"])).days
                if 0 < duration <= 365: nights += duration; night_count += 1
        except (TypeError, ValueError): pass
        count = sum(int(item.get(key) or 0) for key in ("adultos", "criancas", "bebes"))
        if count: guests += count; guest_count += 1
    return {"generated_at": _iso(datetime.now(timezone.utc)), "period": {"start": period["start"].isoformat(), "end": period["end"].isoformat(), "days": period["days"]}, "filters": {"traffic": traffic, "include_validation": bool(include_validation)},
            "kpis": {"visitors": estimated_visitors, "confirmed_visitors": confirmed_visitors, "sessions": sessions_count, "pageviews": pageview_count, "searches": len(searched), "checkouts": len(checkouts), "payments": len(payments), "bookings": len(successful_ids), "requests": total_requests, "average_active_seconds": round(active / sessions_count) if sessions_count else None, "pageviews_per_session": round(pageview_count / sessions_count, 1) if sessions_count else None, "accesses": total_requests - request_counts["BOT"], "bot_accesses": request_counts["BOT"], "visits": estimated_visitors, "paid_bookings": len(successful_ids)},
            "timeline": timeline_rows, "sources": _rank(sources), "countries": _rank(country_counts), "estimated_countries": _rank(estimated_countries), "request_countries": _rank(request_countries), "devices": _rank(Counter(str(x.get("device") or "unknown") for x in session_rows)), "browsers": _rank(Counter(str(x.get("browser") or "unknown") for x in session_rows)), "operating_systems": _rank(Counter(str(x.get("os") or "unknown") for x in session_rows)), "languages": _rank(Counter(str(x.get("language") or "unknown") for x in session_rows)), "pages": pages, "request_pages": _rank(request_pages, labels=PAGE_LABELS), "properties": properties, "recent_sessions": recent,
            "searches": {"average_nights": round(nights / night_count, 1) if night_count else None, "average_guests": round(guests / guest_count, 1) if guest_count else None, "pageviews_with_dates": night_count},
            "searches_detail": {"sessions_with_dates": len({x["session_id"] for x in page_rows if _search(x).get("checkin") and _search(x).get("checkout")})},
            "funnel": [{"key": key, "label": label, "value": value, "rate": _pct(value, previous) if previous is not None else None} for key, label, value, previous in (("visitors", "Visitantes confirmados", confirmed_visitors, None), ("search", "Pesquisa", len(searched), confirmed_visitors), ("results", "Resultados", len(results), len(searched)), ("property", "Alojamento", len(property_sessions), len(results)), ("checkout", "Checkout", len(checkouts), len(property_sessions)), ("payment", "Pagamento iniciado", len(payments), len(checkouts)), ("booking", "Reserva concluída", len(booked_sessions), len(payments)))],
            "traffic_quality": {"request_classes": _rank(request_counts, labels=CLASS_LABELS), "session_classes": _rank(Counter(_class(x) for x in all_sessions), labels=CLASS_LABELS), "request_reasons": _rank(reason_counts), "diagnostics": diagnostics[:60]},
            "data_quality": {"unattributable_requests": total_requests, "unknown_country_sessions": sum(1 for x in session_rows if str(x.get("country") or "ZZ") == "ZZ"), "validation_sessions_excluded": len(validation_ids) if not include_validation else 0, "validation_requests_excluded": validation_requests if not include_validation else 0, "granular_retention_days": 90, "aggregate_retention_days": 180},
            "definitions": {"request": "Pedido HTTP de uma página pública; não é uma pessoa nem uma visita.", "visitor_estimate": "Estimativa de entradas não-bot por contexto/hora, sem identificador persistente; não equivale a pessoas únicas exatas.", "pageview": "Página confirmada pelo JavaScript após consentimento analítico.", "visitor": "Navegador lógico com consentimento; não é uma pessoa garantidamente distinta.", "session": "Interações do mesmo visitante com até 30 minutos de inatividade.", "active_time": "Tempo ativo estimado apenas para sessões consentidas; ausência de medição não é zero.", "country": "País aproximado da ligação, não nacionalidade."}}
