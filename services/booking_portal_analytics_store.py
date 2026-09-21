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
    Column("entry_page", String(32), nullable=False),
    Column("referrer_host", String(253), nullable=False, server_default=""),
    Column("source", String(128), nullable=False, server_default="unknown"),
    Column("medium", String(128), nullable=False, server_default=""),
    Column("campaign", String(128), nullable=False, server_default=""),
    Column("consent_version", String(32), nullable=False),
    Column("consent_at", UTCDateTime, nullable=False),
    Column("active_seconds", Integer, nullable=False, server_default="0"),
    Column("page_views", Integer, nullable=False, server_default="0"),
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
    Column("has_search", Boolean, nullable=False),
    Column("is_bot", Boolean, nullable=False),
    Column("requests", Integer, nullable=False, server_default="0"),
    CheckConstraint("requests >= 0", name="CK_PB_ANALYTICS_TOTAL_REQUESTS"),
)
conversions = Table(
    "PB_ANALYTICS_CONVERSIONS", metadata,
    Column("booking_id", String(36), primary_key=True),
    Column("session_id", String(36), ForeignKey(sessions.c.session_id), nullable=False),
    Column("created_at", UTCDateTime, nullable=False),
)
Index("IX_PB_ANALYTICS_VISITORS_LAST", visitors.c.last_seen_at)
Index("IX_PB_ANALYTICS_SESSIONS_VISITOR", sessions.c.visitor_id, sessions.c.started_at)
Index("IX_PB_ANALYTICS_SESSIONS_LAST", sessions.c.last_seen_at)
Index("IX_PB_ANALYTICS_PAGES_SESSION", pageviews.c.session_id, pageviews.c.created_at)
Index("IX_PB_ANALYTICS_PAGES_CREATED", pageviews.c.created_at)
Index("IX_PB_ANALYTICS_TOTALS_HOUR", totals.c.hour, totals.c.page_kind)
Index("IX_PB_ANALYTICS_CONVERSIONS_SESSION", conversions.c.session_id)
Index("IX_PB_ANALYTICS_CONVERSIONS_CREATED", conversions.c.created_at)

SESSION_TIMEOUT = timedelta(minutes=30)
SEARCH_KEYS = frozenset(("checkin", "checkout", "adultos", "criancas", "bebes", "has_query"))


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
    """Add only these five analytics tables; never change existing app tables."""
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
        "has_search": bool(dimensions.get("has_search")),
        "is_bot": bool(dimensions.get("is_bot")),
    }
    serialized = json.dumps(values, default=lambda value: value.isoformat(), sort_keys=True, separators=(",", ":"))
    key = hashlib.sha256(serialized.encode()).hexdigest()

    def operation(conn):
        result = conn.execute(update(totals).where(totals.c.bucket_key == key).values(requests=totals.c.requests + 1))
        if result.rowcount == 0:
            conn.execute(insert(totals).values(bucket_key=key, requests=1, **values))
        return {"accepted": True, "bucket_key": key}

    return _run(engine, operation)


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
                entry_page=_text(context.get("page_kind"), 32, "unknown"),
                referrer_host=_text(context.get("referrer_host"), 253),
                source=_text(context.get("source"), 128, "unknown"),
                medium=_text(context.get("medium"), 128), campaign=_text(context.get("campaign"), 128),
                consent_version=_text(consent["version"], 32), consent_at=_utc(consent["decided_at"]),
                active_seconds=0, page_views=0,
            ))
        search = {key: value for key, value in (context.get("search") or {}).items() if key in SEARCH_KEYS}
        conn.execute(insert(pageviews).values(
            page_id=page_id, session_id=session_id, created_at=now, last_seen_at=now,
            page_kind=_text(context.get("page_kind"), 32, "unknown"),
            property_id=_text(context.get("property_id"), 64) or None,
            lang=_text(context.get("lang"), 8, "pt"), view_mode=_text(context.get("view_mode"), 16, "list"),
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


def prune(engine, now):
    """Retain granular events 90 days, aggregates and orphan visitors 180 days."""
    now = _utc(now)
    granular_cutoff, aggregate_cutoff = now - timedelta(days=90), now - timedelta(days=180)

    def operation(conn):
        expired_sessions = select(sessions.c.session_id).where(sessions.c.last_seen_at < granular_cutoff)
        removed = {}
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
