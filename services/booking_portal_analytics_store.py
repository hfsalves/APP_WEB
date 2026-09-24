"""Private, consent-aware portal analytics persistence (no Flask dependencies).

All times are UTC.  Only explicitly selected analytics dimensions are written;
raw requests, addresses, user agents and customer records never enter this store.
Call ``ensure_schema`` explicitly during deployment, not on incoming requests.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, Integer,
    MetaData, String, Table, Text, case, delete, exists, insert, select, update,
)
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.dialects.mssql import DATETIME2


metadata = MetaData()
UTCDateTime = DateTime().with_variant(DATETIME2(precision=6), "mssql")
visitors = Table(
    "PB_ANALYTICS_VISITORS", metadata,
    Column("visitor_id", String(36), primary_key=True),
    Column("created_at", UTCDateTime, nullable=False),
    Column("last_seen_at", UTCDateTime, nullable=False),
    # Reserved for an explicit, separately designed voluntary demographic survey.
    Column("gender", String(32), nullable=True),
    Column("age_band", String(16), nullable=True),
    Column("demographic_source", String(24), nullable=False, server_default="unknown"),
)
sessions = Table(
    "PB_ANALYTICS_SESSIONS", metadata,
    Column("session_id", String(36), primary_key=True),
    Column("visitor_id", String(36), ForeignKey(visitors.c.visitor_id), nullable=False),
    Column("started_at", UTCDateTime, nullable=False),
    Column("last_seen_at", UTCDateTime, nullable=False),
    Column("engagement_seen_at", UTCDateTime, nullable=False),
    Column("country", String(2), nullable=False, server_default="ZZ"),
    Column("country_source", String(24), nullable=False, server_default="unknown"),
    Column("device", String(16), nullable=False, server_default="unknown"),
    Column("browser", String(32), nullable=False, server_default="unknown"),
    Column("os", String(32), nullable=False, server_default="unknown"),
    Column("language", String(8), nullable=False),
    Column("currency", String(3), nullable=False, server_default="EUR"),
    Column("entry_page", String(32), nullable=False),
    Column("referrer_host", String(253), nullable=False, server_default=""),
    Column("source", String(128), nullable=False, server_default="unknown"),
    Column("medium", String(128), nullable=False, server_default=""),
    Column("campaign", String(128), nullable=False, server_default=""),
    Column("consent_version", String(32), nullable=False),
    Column("consent_at", UTCDateTime, nullable=False),
    Column("active_seconds", Integer, nullable=False, server_default="0"),
    Column("page_views", Integer, nullable=False, server_default="0"),
    # v2 quality is deliberately behavioural, not identity-based.  It is only
    # meaningful for consented sessions, where the browser may send events.
    Column("traffic_class", String(24), nullable=False, server_default="LEGACY"),
    Column("base_bot_score", Integer, nullable=False, server_default="0"),
    Column("bot_score", Integer, nullable=False, server_default="0"),
    Column("human_score", Integer, nullable=False, server_default="0"),
    Column("classification_reason", String(512), nullable=False, server_default="legacy"),
    Column("js_seen", Boolean, nullable=False, server_default="0"),
    CheckConstraint("active_seconds >= 0 AND page_views >= 0", name="CK_PB_ANALYTICS_SESSION_COUNTS"),
)
pageviews = Table(
    "PB_ANALYTICS_PAGEVIEWS", metadata,
    Column("page_id", String(36), primary_key=True),
    Column("session_id", String(36), ForeignKey(sessions.c.session_id), nullable=False),
    Column("created_at", UTCDateTime, nullable=False),
    Column("last_seen_at", UTCDateTime, nullable=False),
    Column("page_kind", String(32), nullable=False),
    Column("property_id", String(64), nullable=True),
    Column("lang", String(8), nullable=False),
    Column("currency", String(3), nullable=False, server_default="EUR"),
    Column("view_mode", String(16), nullable=False),
    Column("search_json", Text, nullable=False),
    Column("active_seconds", Integer, nullable=False, server_default="0"),
    CheckConstraint("active_seconds >= 0", name="CK_PB_ANALYTICS_PAGE_ACTIVE"),
)
totals = Table(
    "PB_ANALYTICS_TOTALS", metadata,
    Column("bucket_key", String(64), primary_key=True),
    Column("hour", UTCDateTime, nullable=False),
    Column("page_kind", String(32), nullable=False),
    Column("property_id", String(64), nullable=False, server_default=""),
    Column("device", String(16), nullable=False),
    Column("country", String(2), nullable=False),
    Column("referrer_host", String(253), nullable=False, server_default=""),
    Column("source", String(128), nullable=False),
    Column("currency", String(3), nullable=False, server_default="EUR"),
    Column("has_search", Boolean, nullable=False),
    Column("is_bot", Boolean, nullable=False),
    # These are request-level observations, never a claim of a unique person.
    # Legacy buckets retain LEGACY until a new v2 observation is recorded.
    Column("traffic_class", String(24), nullable=False, server_default="LEGACY"),
    Column("bot_score", Integer, nullable=False, server_default="0"),
    Column("classification_reason", String(160), nullable=False, server_default="legacy"),
    Column("requests", Integer, nullable=False, server_default="0"),
    CheckConstraint("requests >= 0", name="CK_PB_ANALYTICS_TOTAL_REQUESTS"),
)
conversions = Table(
    "PB_ANALYTICS_CONVERSIONS", metadata,
    Column("booking_id", String(36), primary_key=True),
    Column("session_id", String(36), ForeignKey(sessions.c.session_id), nullable=False),
    Column("created_at", UTCDateTime, nullable=False),
    Column("payment_started_at", UTCDateTime, nullable=True),
    Column("booking_success_at", UTCDateTime, nullable=True),
)
events = Table(
    "PB_ANALYTICS_EVENTS", metadata,
    Column("event_id", String(36), primary_key=True),
    Column("session_id", String(36), ForeignKey(sessions.c.session_id), nullable=False),
    Column("page_id", String(36), ForeignKey(pageviews.c.page_id), nullable=False),
    Column("created_at", UTCDateTime, nullable=False),
    Column("event_name", String(48), nullable=False),
    Column("event_json", Text, nullable=False),
)
Index("IX_PB_ANALYTICS_VISITORS_LAST", visitors.c.last_seen_at)
Index("IX_PB_ANALYTICS_SESSIONS_VISITOR", sessions.c.visitor_id, sessions.c.started_at)
Index("IX_PB_ANALYTICS_SESSIONS_LAST", sessions.c.last_seen_at)
Index("IX_PB_ANALYTICS_SESSIONS_CLASS", sessions.c.traffic_class, sessions.c.started_at)
Index("IX_PB_ANALYTICS_PAGES_SESSION", pageviews.c.session_id, pageviews.c.created_at)
Index("IX_PB_ANALYTICS_PAGES_CREATED", pageviews.c.created_at)
Index("IX_PB_ANALYTICS_TOTALS_HOUR", totals.c.hour, totals.c.page_kind)
Index("IX_PB_ANALYTICS_TOTALS_CLASS", totals.c.traffic_class, totals.c.hour)
Index("IX_PB_ANALYTICS_CONVERSIONS_SESSION", conversions.c.session_id)
Index("IX_PB_ANALYTICS_CONVERSIONS_CREATED", conversions.c.created_at)
Index("IX_PB_ANALYTICS_EVENTS_SESSION", events.c.session_id, events.c.created_at)
Index("IX_PB_ANALYTICS_EVENTS_NAME", events.c.event_name, events.c.created_at)

SESSION_TIMEOUT = timedelta(minutes=30)
SEARCH_KEYS = frozenset(("checkin", "checkout", "adultos", "criancas", "bebes", "has_query"))
TRAFFIC_CLASSES = frozenset(("LEGACY", "UNKNOWN", "LIKELY_HUMAN", "HUMAN", "SUSPECTED_BOT", "BOT"))
LEGAL_PAGE_KINDS = frozenset(("cookies", "privacy", "terms", "legal", "cancellation_policy"))


def _traffic_class(value, default="UNKNOWN"):
    value = str(value or default).strip().upper()
    return value if value in TRAFFIC_CLASSES else default


def _score(value, maximum=100):
    try:
        return min(maximum, max(0, int(value or 0)))
    except (TypeError, ValueError):
        return 0


class AnalyticsConflict(ValueError):
    """An identifier belongs to another visitor/session, or no longer exists."""


class SessionExpired(ValueError):
    """The caller must create a fresh session and page after inactivity."""


def _utc(value):
    if not isinstance(value, datetime):
        value = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _text(value, limit, default=""):
    return str(value if value is not None else default)[:limit]


def _country(value):
    value = str(value or "ZZ").upper()
    return value if len(value) == 2 and value.isascii() and value.isalpha() else "ZZ"


def ensure_schema(engine):
    """Add only the dedicated analytics tables; never change existing app tables."""
    metadata.create_all(engine)


def _run(engine, operation):
    # Unique insert races are expected for new visitors and aggregate buckets.
    # Roll back the complete transaction before retrying; never continue a failed one.
    for attempt in range(5):
        try:
            with engine.begin() as conn:
                return operation(conn)
        except IntegrityError:
            if attempt == 4:
                raise
        except OperationalError as exc:
            message = str(exc).lower()
            if attempt == 4 or not any(x in message for x in ("deadlock", "database is locked", "40001", "1205")):
                raise
        time.sleep(0.01 * (attempt + 1))


def _locked(conn, table, criterion):
    statement = select(table).where(criterion)
    if conn.dialect.name == "mssql":
        statement = statement.with_hint(table, "WITH (UPDLOCK, HOLDLOCK)", "mssql")
    return conn.execute(statement).mappings().first()


def _touch_visitor(conn, visitor_id, now, create=False):
    # This write lock serializes sessions/pages of the same consented visitor,
    # including on SQLite, where SELECT FOR UPDATE is unavailable.
    result = conn.execute(update(visitors).where(visitors.c.visitor_id == visitor_id).values(
        last_seen_at=case((visitors.c.last_seen_at < now, now), else_=visitors.c.last_seen_at)
    ))
    if result.rowcount == 0:
        if not create:
            raise AnalyticsConflict("Unknown visitor")
        conn.execute(insert(visitors).values(visitor_id=visitor_id, created_at=now, last_seen_at=now))


def _session(conn, session_id, visitor_id, now):
    row = _locked(conn, sessions, sessions.c.session_id == session_id)
    if row is not None:
        if row["visitor_id"] != visitor_id:
            raise AnalyticsConflict("Session belongs to another visitor")
        if now - row["last_seen_at"] > SESSION_TIMEOUT:
            raise SessionExpired("Session expired after 30 minutes of inactivity")
    return row


def record_total(engine, dimensions: dict, now):
    """Increment an anonymous hourly request bucket atomically; not unique people."""
    hour = _utc(now).replace(minute=0, second=0, microsecond=0)
    values = {
        "hour": hour,
        "page_kind": _text(dimensions.get("page_kind"), 32, "unknown"),
        "property_id": _text(dimensions.get("property_id"), 64),
        "device": _text(dimensions.get("device"), 16, "unknown"),
        "country": _country(dimensions.get("country")),
        "referrer_host": _text(dimensions.get("referrer_host"), 253),
        "source": _text(dimensions.get("source"), 128, "unknown"),
        "currency": _text(dimensions.get("currency"), 3, "EUR"),
        "has_search": bool(dimensions.get("has_search")),
        "is_bot": bool(dimensions.get("is_bot")),
        "traffic_class": _traffic_class(
            dimensions.get("traffic_class"), "BOT" if dimensions.get("is_bot") else "UNKNOWN"
        ),
        "bot_score": _score(dimensions.get("bot_score")),
        "classification_reason": _text(dimensions.get("classification_reason"), 160, "unspecified"),
    }
    serialized = json.dumps(values, default=lambda value: value.isoformat(), sort_keys=True, separators=(",", ":"))
    key = hashlib.sha256(serialized.encode()).hexdigest()

    def operation(conn):
        result = conn.execute(update(totals).where(totals.c.bucket_key == key).values(requests=totals.c.requests + 1))
        if result.rowcount == 0:
            conn.execute(insert(totals).values(bucket_key=key, requests=1, **values))
        return {"accepted": True, "bucket_key": key}

    return _run(engine, operation)


def _session_signal_summary(conn, session_id, session, now):
    """Recompute quality from stored, consented behaviour.

    This deliberately uses only page kinds and allowlisted event names already
    stored for the session.  It never reads or derives a browser fingerprint.
    """
    page_rows = conn.execute(select(
        pageviews.c.page_kind, pageviews.c.property_id, pageviews.c.created_at,
    ).where(pageviews.c.session_id == session_id)).mappings().all()
    event_rows = conn.execute(select(events.c.event_name).where(
        events.c.session_id == session_id
    )).mappings().all()
    page_kinds = [str(row["page_kind"] or "") for row in page_rows]
    properties = {str(row["property_id"] or "") for row in page_rows if row["property_id"]}
    event_names = {str(row["event_name"] or "") for row in event_rows}
    event_count = len(event_rows)
    legal_count = sum(kind in LEGAL_PAGE_KINDS for kind in page_kinds)
    page_count = len(page_rows)
    elapsed = max(0, int((_utc(now) - session["started_at"]).total_seconds()))

    bot_score = _score(session.get("base_bot_score"))
    reasons = []
    if bot_score >= 100:
        reasons.append("known_automation")
    # A signed pageview is a strong, but not absolute, human signal.  Events
    # add confidence and are never inferred from a URL alone.
    human_score = 20 if bool(session.get("js_seen")) else 0
    event_weights = {
        "SEARCH": 25, "DATE_SELECT": 20, "GUEST_SELECT": 10,
        "FILTER": 10, "GALLERY_INTERACTION": 10, "LANGUAGE_CHANGE": 5,
        "CURRENCY_CHANGE": 5, "WHATSAPP_CLICK": 15, "LOGIN_SUCCESS": 40,
        "CHECKOUT_START": 40, "PAYMENT_START": 50, "BOOKING_SUCCESS": 80,
    }
    human_score += sum(weight for name, weight in event_weights.items() if name in event_names)
    human_score = _score(human_score)

    # These thresholds deliberately require a combination of behaviour.  A
    # direct visit, missing referrer, legal-page read or lack of a search is
    # never sufficient on its own to label somebody as a bot.
    if not event_count and len(properties) >= 8:
        bot_score = max(bot_score, 55)
        reasons.append("sequential_property_crawl")
    if not event_count and legal_count >= 3 and page_count >= 4:
        bot_score = max(bot_score, 40)
        reasons.append("legal_page_crawl")
    if not event_count and page_count >= 12 and elapsed <= 120:
        bot_score = max(bot_score, 70)
        reasons.append("rapid_page_sequence")

    if bot_score >= 80:
        traffic_class = "BOT"
    elif bot_score >= 35:
        traffic_class = "SUSPECTED_BOT"
    elif human_score >= 60:
        traffic_class = "HUMAN"
    elif human_score >= 20:
        traffic_class = "LIKELY_HUMAN"
    else:
        traffic_class = "UNKNOWN"
    if not reasons:
        reasons.append("consented_javascript" if human_score else "insufficient_signals")
    return {
        "traffic_class": traffic_class,
        "bot_score": bot_score,
        "human_score": human_score,
        "classification_reason": ";".join(dict.fromkeys(reasons))[:512],
    }


def _refresh_session_classification(conn, session_id, now):
    session = _locked(conn, sessions, sessions.c.session_id == session_id)
    if session is None:
        raise AnalyticsConflict("Unknown session")
    values = _session_signal_summary(conn, session_id, session, now)
    conn.execute(update(sessions).where(sessions.c.session_id == session_id).values(**values))
    return values


def record_pageview(engine, *, visitor_id, session_id, page_id, context: dict, traits: dict, consent: dict, now):
    """Create an idempotent consented page view and first-touch session context."""
    now = _utc(now)

    def operation(conn):
        _touch_visitor(conn, visitor_id, now, create=True)
        session = _session(conn, session_id, visitor_id, now)
        page = _locked(conn, pageviews, pageviews.c.page_id == page_id)
        if page is not None:
            if page["session_id"] != session_id:
                raise AnalyticsConflict("Page belongs to another session")
            return {"accepted": True, "session_id": session_id, "page_id": page_id, "created": False}
        if session is None:
            conn.execute(insert(sessions).values(
                session_id=session_id, visitor_id=visitor_id,
                started_at=now, last_seen_at=now, engagement_seen_at=now,
                country=_country(traits.get("country")),
                country_source=_text(traits.get("country_source"), 24, "unknown"),
                device=_text(traits.get("device"), 16, "unknown"),
                browser=_text(traits.get("browser"), 32, "unknown"),
                os=_text(traits.get("os"), 32, "unknown"),
                language=_text(context.get("lang"), 8, "pt"),
                currency=_text(context.get("currency"), 3, "EUR"),
                entry_page=_text(context.get("page_kind"), 32, "unknown"),
                referrer_host=_text(context.get("referrer_host"), 253),
                source=_text(context.get("source"), 128, "unknown"),
                medium=_text(context.get("medium"), 128), campaign=_text(context.get("campaign"), 128),
                consent_version=_text(consent["version"], 32), consent_at=_utc(consent["decided_at"]),
                active_seconds=0, page_views=0,
                traffic_class=_traffic_class(traits.get("traffic_class"), "UNKNOWN"),
                base_bot_score=_score(traits.get("bot_score")),
                bot_score=_score(traits.get("bot_score")),
                human_score=20,  # a consented, signed browser pageview proves JS ran
                classification_reason=_text(traits.get("classification_reason"), 512, "javascript_pageview"),
                js_seen=True,
            ))
        search = {key: value for key, value in (context.get("search") or {}).items() if key in SEARCH_KEYS}
        conn.execute(insert(pageviews).values(
            page_id=page_id, session_id=session_id, created_at=now, last_seen_at=now,
            page_kind=_text(context.get("page_kind"), 32, "unknown"),
            property_id=_text(context.get("property_id"), 64) or None,
            lang=_text(context.get("lang"), 8, "pt"),
            currency=_text(context.get("currency"), 3, "EUR"),
            view_mode=_text(context.get("view_mode"), 16, "list"),
            search_json=json.dumps(search, ensure_ascii=True, sort_keys=True, separators=(",", ":")),
            active_seconds=0,
        ))
        session_updates = {
            "page_views": sessions.c.page_views + 1,
            "last_seen_at": case((sessions.c.last_seen_at < now, now), else_=sessions.c.last_seen_at),
        }
        # A country header may become available after the session started (for
        # example after a proxy configuration is corrected). Enrich only an
        # unknown value; first-touch attribution and known countries stay fixed.
        observed_country = _country(traits.get("country"))
        if session is not None and session["country"] == "ZZ" and observed_country != "ZZ":
            session_updates["country"] = observed_country
            session_updates["country_source"] = _text(traits.get("country_source"), 24, "unknown")
        conn.execute(update(sessions).where(sessions.c.session_id == session_id).values(**session_updates))
        _refresh_session_classification(conn, session_id, now)
        return {"accepted": True, "session_id": session_id, "page_id": page_id, "created": True}

    return _run(engine, operation)


def record_engagement(engine, *, visitor_id, session_id, page_id, active_seconds: int, now):
    """Accept cumulative, monotonic active time, bounded by server elapsed time."""
    now = _utc(now)

    def operation(conn):
        _touch_visitor(conn, visitor_id, now)
        session = _session(conn, session_id, visitor_id, now)
        page = _locked(conn, pageviews, pageviews.c.page_id == page_id)
        if session is None or page is None or page["session_id"] != session_id:
            raise AnalyticsConflict("Unknown session or page ownership mismatch")
        elapsed = max(0, int((now - page["created_at"]).total_seconds()))
        value = max(page["active_seconds"], min(max(0, int(active_seconds)), elapsed))
        delta = value - page["active_seconds"]
        session_elapsed = max(0, int((now - session["engagement_seen_at"]).total_seconds()))
        credited = min(delta, session_elapsed)
        conn.execute(update(pageviews).where(pageviews.c.page_id == page_id).values(
            active_seconds=value, last_seen_at=max(now, page["last_seen_at"]),
        ))
        conn.execute(update(sessions).where(sessions.c.session_id == session_id).values(
            active_seconds=sessions.c.active_seconds + credited,
            last_seen_at=max(now, session["last_seen_at"]),
            # Duplicate/replayed heartbeats must not consume another tab's interval.
            engagement_seen_at=max(now, session["engagement_seen_at"]) if delta else session["engagement_seen_at"],
        ))
        return {"accepted": True, "session_id": session_id, "page_id": page_id,
                "active_seconds": value, "session_active_seconds": session["active_seconds"] + credited}

    return _run(engine, operation)


def link_booking(engine, *, visitor_id, session_id, booking_id, now):
    """Attach only an opaque booking request ID to an existing, recent session."""
    now = _utc(now)

    def operation(conn):
        _touch_visitor(conn, visitor_id, now)
        session = _session(conn, session_id, visitor_id, now)
        if session is None:
            raise AnalyticsConflict("Unknown session")
        conversion = _locked(conn, conversions, conversions.c.booking_id == booking_id)
        if conversion is not None:
            if conversion["session_id"] != session_id:
                raise AnalyticsConflict("Booking already belongs to another session")
            return {"accepted": True, "created": False}
        conn.execute(insert(conversions).values(booking_id=booking_id, session_id=session_id, created_at=now))
        conn.execute(update(sessions).where(sessions.c.session_id == session_id).values(
            last_seen_at=max(now, session["last_seen_at"]),
        ))
        return {"accepted": True, "created": True}

    return _run(engine, operation)


def record_event(engine, *, visitor_id, session_id, page_id, event_id, event_name, event_data, now):
    """Store an idempotent, allowlisted interaction against its owned page."""
    now = _utc(now)
    serialized = json.dumps(event_data, ensure_ascii=True, sort_keys=True, separators=(",", ":"))

    def operation(conn):
        _touch_visitor(conn, visitor_id, now)
        session = _session(conn, session_id, visitor_id, now)
        page = _locked(conn, pageviews, pageviews.c.page_id == page_id)
        if session is None or page is None or page["session_id"] != session_id:
            raise AnalyticsConflict("Unknown session or page ownership mismatch")
        existing = _locked(conn, events, events.c.event_id == event_id)
        if existing is not None:
            if existing["session_id"] != session_id or existing["page_id"] != page_id:
                raise AnalyticsConflict("Event belongs to another page")
            return {"accepted": True, "created": False, "session_id": session_id}
        conn.execute(insert(events).values(
            event_id=event_id, session_id=session_id, page_id=page_id,
            created_at=now, event_name=_text(event_name, 48), event_json=serialized,
        ))
        conn.execute(update(sessions).where(sessions.c.session_id == session_id).values(
            last_seen_at=max(now, session["last_seen_at"]),
        ))
        classification = _refresh_session_classification(conn, session_id, now)
        return {"accepted": True, "created": True, "session_id": session_id,
                "traffic_class": classification["traffic_class"]}

    return _run(engine, operation)


def record_server_event(engine, *, visitor_id, session_id, event_name, now):
    """Record a trusted server-side outcome against the session's latest page.

    Authentication and payment transitions cannot rely on a browser callback;
    this keeps those events in the same event stream without storing customer
    data or an additional identifier.
    """
    now = _utc(now)

    def operation(conn):
        _touch_visitor(conn, visitor_id, now)
        session = _session(conn, session_id, visitor_id, now)
        if session is None:
            raise AnalyticsConflict("Unknown session")
        page = conn.execute(select(pageviews.c.page_id).where(
            pageviews.c.session_id == session_id
        ).order_by(pageviews.c.created_at.desc()).limit(1)).scalar_one_or_none()
        if not page:
            raise AnalyticsConflict("Session has no page")
        # Server outcomes are recorded once per event type and session.  This
        # makes redirects/retries harmless without needing a browser event ID.
        existing = conn.execute(select(events.c.event_id).where(
            events.c.session_id == session_id, events.c.event_name == event_name,
        )).scalar_one_or_none()
        if existing:
            return {"accepted": True, "created": False, "session_id": session_id}
        event_id = hashlib.sha256(f"{session_id}:{event_name}".encode()).hexdigest()[:36]
        conn.execute(insert(events).values(
            event_id=event_id, session_id=session_id, page_id=page,
            created_at=now, event_name=_text(event_name, 48), event_json="{}",
        ))
        conn.execute(update(sessions).where(sessions.c.session_id == session_id).values(
            last_seen_at=max(now, session["last_seen_at"]),
        ))
        classification = _refresh_session_classification(conn, session_id, now)
        return {"accepted": True, "created": True, "session_id": session_id,
                "traffic_class": classification["traffic_class"]}

    return _run(engine, operation)


def mark_payment_started(engine, *, booking_id, now):
    """Persist a payment start for an already-linked, consented conversion."""
    now = _utc(now)

    def operation(conn):
        row = _locked(conn, conversions, conversions.c.booking_id == booking_id)
        if row is None:
            return {"accepted": False, "created": False}
        if row.get("payment_started_at") is None:
            conn.execute(update(conversions).where(conversions.c.booking_id == booking_id).values(
                payment_started_at=now
            ))
            return {"accepted": True, "created": True}
        return {"accepted": True, "created": False}

    return _run(engine, operation)


def mark_booking_success(engine, *, booking_id, now):
    """Persist a confirmed booking outcome once; Stripe retries are idempotent."""
    now = _utc(now)

    def operation(conn):
        row = _locked(conn, conversions, conversions.c.booking_id == booking_id)
        if row is None:
            return {"accepted": False, "created": False}
        if row.get("booking_success_at") is None:
            conn.execute(update(conversions).where(conversions.c.booking_id == booking_id).values(
                booking_success_at=now
            ))
            return {"accepted": True, "created": True}
        return {"accepted": True, "created": False}

    return _run(engine, operation)


def prune(engine, now):
    """Retain granular events 90 days, aggregates and orphan visitors 180 days."""
    now = _utc(now)
    granular_cutoff, aggregate_cutoff = now - timedelta(days=90), now - timedelta(days=180)

    def operation(conn):
        expired_sessions = select(sessions.c.session_id).where(sessions.c.last_seen_at < granular_cutoff)
        removed = {}
        removed["events"] = conn.execute(delete(events).where(
            (events.c.created_at < granular_cutoff) | events.c.session_id.in_(expired_sessions)
        )).rowcount
        removed["conversions"] = conn.execute(delete(conversions).where(
            (conversions.c.created_at < granular_cutoff) | conversions.c.session_id.in_(expired_sessions)
        )).rowcount
        removed["pageviews"] = conn.execute(delete(pageviews).where(
            (pageviews.c.created_at < granular_cutoff) | pageviews.c.session_id.in_(expired_sessions)
        )).rowcount
        removed["sessions"] = conn.execute(delete(sessions).where(sessions.c.last_seen_at < granular_cutoff)).rowcount
        removed["totals"] = conn.execute(delete(totals).where(totals.c.hour < aggregate_cutoff)).rowcount
        removed["visitors"] = conn.execute(delete(visitors).where(
            (visitors.c.last_seen_at < aggregate_cutoff) &
            ~exists(select(sessions.c.session_id).where(sessions.c.visitor_id == visitors.c.visitor_id))
        )).rowcount
        return removed

    return _run(engine, operation)
