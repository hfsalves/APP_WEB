"""First-party PortoBreak measurement. No fingerprinting or raw request logging.

Unconsented requests only increment coarse counters. Visitor/session identifiers
are issued only after a fresh, purpose-specific analytics consent.
"""

import hashlib
import ipaddress
import os
import re
import threading
import time
import uuid
from datetime import date, datetime, timezone
from urllib.parse import urlsplit

from flask import current_app, jsonify, request, url_for
from itsdangerous import BadData, URLSafeTimedSerializer

from models import db
from services.booking_portal_cookies import (
    PUBLIC_HOSTS, cookie_is_secure, is_same_origin_request, read_cookie_consent,
)
from services import booking_portal_analytics_store as store

VISITOR_COOKIE = "portobreak_visitor"
SESSION_COOKIE = "portobreak_analytics_session"
VISITOR_MAX_AGE = 180 * 86400
SESSION_MAX_AGE = 30 * 60
CONTEXT_MAX_AGE = 86400
PAGE_KINDS = {
    "index": "catalog", "detail": "property", "reserve": "booking_form",
    "map_quote": "map_quote", "payment_result": "payment_result",
    "login": "login", "my_bookings": "my_bookings",
    "cancellation_policy": "cancellation_policy", "terms": "terms",
    "privacy": "privacy", "cookies": "cookies", "legal": "legal",
}
# Verify ranges against https://www.cloudflare.com/ips/ when deploying updates.
CF_NETWORKS = tuple(ipaddress.ip_network(value) for value in (
    "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22",
    "141.101.64.0/18", "108.162.192.0/18", "190.93.240.0/20", "188.114.96.0/20",
    "197.234.240.0/22", "198.41.128.0/17", "162.158.0.0/15", "104.16.0.0/13",
    "104.24.0.0/14", "172.64.0.0/13", "131.0.72.0/22", "2400:cb00::/32",
    "2606:4700::/32", "2803:f800::/32", "2405:b500::/32", "2405:8100::/32",
    "2a06:98c0::/29", "2c0f:f248::/32",
))
LOCAL_PROXY_NETWORKS = (
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
)
BOT = re.compile(r"bot\b|crawler|spider|headless|curl/|wget/|python|httpclient|scanner|preview|facebookexternalhit", re.I)
_lock = threading.Lock()
_limits = {}
_last_prune = 0.0


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _setting(name, default=None):
    return current_app.config.get(name, os.environ.get(name, default))


def _flag(name, default=False):
    return str(_setting(name, str(default))).lower() in {"1", "true", "yes", "on"}


def enabled():
    if current_app.testing and not (
        current_app.config.get("PORTOBREAK_ANALYTICS_ENABLED") is True
        or current_app.config.get("PORTOBREAK_ANALYTICS_ALLOW_LOCAL") is True
    ):
        return False
    if not _flag("PORTOBREAK_ANALYTICS_ENABLED", True):
        return False
    # Preview/admin hosts must not contaminate the production statistics. Do not
    # infer a public host from a caller-controlled forwarded header.
    host = (request.host.split(":", 1)[0]).lower()
    return host in PUBLIC_HOSTS or _flag("PORTOBREAK_ANALYTICS_ALLOW_LOCAL", False)


def _serializer(purpose):
    return URLSafeTimedSerializer(current_app.secret_key, salt="portobreak-analytics-" + purpose)


def _uuid(value):
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        return None


def _identity(name, purpose, age):
    try:
        return _uuid(_serializer(purpose).loads(request.cookies.get(name, ""), max_age=age))
    except BadData:
        return None


def _identities():
    return (_identity(VISITOR_COOKIE, "visitor", VISITOR_MAX_AGE),
            _identity(SESSION_COOKIE, "session", SESSION_MAX_AGE))


def clear_identity_cookies(response):
    for name in (VISITOR_COOKIE, SESSION_COOKIE):
        if name in request.cookies:
            response.delete_cookie(name, path="/", secure=cookie_is_secure(),
                                   httponly=True, samesite="Lax")
    return response


def _set_identities(response, visitor_id, session_id, consent):
    remaining = max(0, consent["expires_at"] - int(time.time()))
    for name, purpose, value, max_age in (
        (VISITOR_COOKIE, "visitor", visitor_id, VISITOR_MAX_AGE),
        (SESSION_COOKIE, "session", session_id, SESSION_MAX_AGE),
    ):
        response.set_cookie(name, _serializer(purpose).dumps(value),
                            max_age=min(max_age, remaining), path="/",
                            secure=cookie_is_secure(), httponly=True, samesite="Lax")
    return response


def _referrer_host():
    try:
        parsed = urlsplit(request.referrer or "")
        host = (parsed.hostname or "").lower()
        if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
            return ""
        # Referrers without a dotted public-looking domain are not retained.
        if len(host) > 190 or not re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,63}", host):
            return ""
        if host in PUBLIC_HOSTS or host == request.host.split(":", 1)[0].lower():
            return "internal"
        return host
    except ValueError:
        return ""


def _campaign(name):
    # No term/content/click IDs or arbitrary free text; reject likely PII.
    value = (request.args.get("utm_" + name) or "").strip()
    if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_-]{0,63}", value):
        return ""
    if re.search(r"\d{7,}", value):
        return ""
    return value


def _source(host):
    if host == "internal":
        return "internal"
    if not host:
        return "unknown"  # Missing Referer is NOT proof of direct acquisition.
    if any(host == domain or host.endswith("." + domain) for domain in
           ("google.com", "google.pt", "bing.com", "duckduckgo.com", "yahoo.com")):
        return "search"
    if any(host == domain or host.endswith("." + domain) for domain in
           ("instagram.com", "facebook.com", "tiktok.com", "linkedin.com", "t.co")):
        return "social"
    return "referral"


def safe_context(lang="pt"):
    suffix = (request.endpoint or "").removeprefix("booking_portal.")
    kind = PAGE_KINDS.get(suffix)
    if not kind:
        return None
    property_id = str((request.view_args or {}).get("al_id") or "")
    if not re.fullmatch(r"[a-zA-Z0-9-]{1,50}", property_id):
        property_id = ""
    search = {}
    for key in ("checkin", "checkout"):
        try:
            value = date.fromisoformat(request.args.get(key, ""))
            if 2000 <= value.year <= 2100:
                search[key] = value.isoformat()
        except ValueError:
            pass
    for key in ("adultos", "criancas", "bebes"):
        value = request.args.get(key, "")
        if value.isdigit() and len(value) <= 2 and 0 <= int(value) <= 50:
            search[key] = int(value)
    if request.args.get("q") or request.args.get("query"):
        search["has_query"] = True
    host = _referrer_host()
    return {
        "page_kind": kind, "property_id": property_id,
        "lang": lang if lang in {"pt", "en", "es", "fr"} else "pt",
        "view_mode": "map" if request.args.get("view") == "map" else "list",
        "search": search, "referrer_host": host,
        "source": _campaign("source") or _source(host),
        "medium": _campaign("medium"), "campaign": _campaign("campaign"),
    }


def _address(value):
    try:
        return ipaddress.ip_address(str(value or "").strip())
    except ValueError:
        return None


def _in_networks(address, networks):
    return address is not None and any(address in network for network in networks)


def _cloudflare_reached_local_proxy():
    """Verify the hop before local Nginx instead of trusting caller headers.

    With ``$proxy_add_x_forwarded_for``, the right-most X-Forwarded-For value is
    the peer that connected to Nginx. For a genuine proxied request that peer is
    Cloudflare. A direct caller cannot pass this check merely by prepending a
    forged Cloudflare address, because Nginx appends its real address last.
    """
    peer = _address(request.remote_addr)
    if not _in_networks(peer, LOCAL_PROXY_NETWORKS):
        return False
    forwarded = [
        _address(value)
        for value in str(request.headers.get("X-Forwarded-For") or "").split(",")
        if value.strip()
    ]
    forwarded = [value for value in forwarded if value is not None]
    if forwarded and _in_networks(forwarded[-1], CF_NETWORKS):
        return True
    return _in_networks(_address(request.headers.get("X-Real-IP")), CF_NETWORKS)


def _trusted_country():
    try:
        peer = _address(request.remote_addr)
        networks = list(CF_NETWORKS)
        configured = str(_setting("PORTOBREAK_ANALYTICS_TRUSTED_PROXY_CIDRS", ""))
        networks.extend(ipaddress.ip_network(v.strip()) for v in configured.split(",") if v.strip())
        trusted = _in_networks(peer, networks) or _cloudflare_reached_local_proxy()
    except ValueError:
        trusted = False
    country = request.headers.get("CF-IPCountry", "").upper()
    if trusted and re.fullmatch(r"[A-Z]{2}", country) and country not in {"XX", "ZZ"}:
        return country, "cloudflare_estimate"
    return "ZZ", "unknown"


def request_traits():
    ua = request.headers.get("User-Agent", "")[:1024]
    device = "tablet" if re.search(r"iPad|Tablet|Android(?!.*Mobile)", ua, re.I) else (
        "mobile" if re.search(r"Mobile|iPhone|iPod", ua, re.I) else "desktop" if ua else "unknown")
    browser = next((label for expression, label in (
        (r"Edg/|EdgiOS|EdgA/", "Edge"), (r"OPR/|Opera", "Opera"),
        (r"Firefox|FxiOS", "Firefox"), (r"Chrome|CriOS", "Chrome"),
        (r"Safari", "Safari"),
    ) if re.search(expression, ua)), "Other")
    operating_system = next((label for expression, label in (
        (r"iPhone|iPad|iPod", "iOS"), (r"Android", "Android"),
        (r"Windows", "Windows"), (r"Macintosh|Mac OS", "macOS"),
        (r"Linux", "Linux"),
    ) if re.search(expression, ua)), "Other")
    country, country_source = _trusted_country()
    return {"device": device, "browser": browser, "os": operating_system,
            "country": country, "country_source": country_source}


def browser_config(lang):
    context = safe_context(lang)
    active = enabled() and context is not None and not BOT.search(request.user_agent.string)
    return {"enabled": bool(active),
            "endpoint": url_for("booking_portal.analytics_events"),
            "context": _serializer("context").dumps(context) if active else ""}


def _prune_if_due(engine):
    global _last_prune
    with _lock:
        if time.monotonic() - _last_prune < 3600:
            return
        _last_prune = time.monotonic()
    store.prune(engine, _now())


def record_response(response):
    consent = read_cookie_consent()
    if not consent or not consent.get("analytics"):
        clear_identity_cookies(response)
    context = safe_context(request.args.get("lang", "pt"))
    if not enabled() or request.method != "GET" or response.status_code != 200 or not context:
        return response
    if not (response.mimetype == "text/html" or context["page_kind"] == "map_quote"):
        return response
    traits = request_traits()
    dimensions = {key: context[key] for key in ("page_kind", "property_id", "referrer_host", "source")}
    # Aggregate arbitrary campaign sources into a bounded acquisition category.
    dimensions["source"] = _source(context["referrer_host"])
    dimensions.update(device=traits["device"], country=traits["country"],
                      has_search=bool(context["search"]),
                      is_bot=bool(BOT.search(request.user_agent.string)))
    try:
        engine = db.engine
        store.record_total(engine, dimensions, _now())
        # Map popups fetch a quote without navigating to a new document.
        # Record that step only for an already consented, active session.
        if context["page_kind"] == "map_quote" and consent and consent.get("analytics"):
            visitor_id, session_id = _identities()
            if visitor_id and session_id:
                try:
                    store.record_pageview(engine, visitor_id=visitor_id, session_id=session_id,
                        page_id=str(uuid.uuid4()), context=context, traits=traits,
                        consent=consent, now=_now())
                except (store.SessionExpired, store.AnalyticsConflict):
                    pass
        _prune_if_due(engine)
    except Exception as exc:
        # Analytics must never break bookings or leak request/SQL parameters.
        current_app.logger.warning("PortoBreak aggregate analytics unavailable (%s)", type(exc).__name__)
    return response


def _rate_allowed(visitor_id):
    key = visitor_id or hashlib.sha256((request.remote_addr or "unknown").encode()).hexdigest()
    minute = int(time.monotonic() // 60)
    with _lock:
        if len(_limits) > 8000:
            _limits.clear()
        count, previous = _limits.get(key, (0, minute))
        count = count + 1 if previous == minute else 1
        _limits[key] = (count, minute)
    return count <= 120


def collect_event():
    def reply(status, **payload):
        response = jsonify(payload)
        response.status_code = status
        response.headers["Cache-Control"] = "private, no-store"
        response.vary.add("Cookie")
        return response

    consent = read_cookie_consent()
    if not enabled() or not is_same_origin_request() or not consent or not consent.get("analytics"):
        return clear_identity_cookies(reply(403, error="analytics_not_allowed"))
    if BOT.search(request.user_agent.string):
        return reply(403, error="automated_client")
    if not request.is_json or request.content_length is None or request.content_length > 8192:
        return reply(400, error="invalid_payload")
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not _uuid(payload.get("page_id")):
        return reply(400, error="invalid_payload")
    visitor_id, session_id = _identities()
    if not _rate_allowed(visitor_id):
        return reply(429, error="rate_limit")
    now = _now()
    try:
        if payload.get("type") == "pageview" and set(payload) == {"type", "context", "page_id"}:
            try:
                context = _serializer("context").loads(payload["context"], max_age=CONTEXT_MAX_AGE)
            except (BadData, TypeError):
                return reply(400, error="invalid_context")
            if not isinstance(context, dict) or context.get("page_kind") not in PAGE_KINDS.values():
                return reply(400, error="invalid_context")
            visitor_id = visitor_id or str(uuid.uuid4())
            session_id = session_id or str(uuid.uuid4())
            result = store.record_pageview(db.engine, visitor_id=visitor_id, session_id=session_id,
                page_id=_uuid(payload["page_id"]), context=context, traits=request_traits(), consent=consent, now=now)
        elif payload.get("type") == "engagement" and set(payload) == {"type", "page_id", "active_seconds"}:
            seconds = payload["active_seconds"]
            if type(seconds) is not int or seconds < 0 or seconds > 86400:
                return reply(400, error="invalid_duration")
            if not visitor_id or not session_id:
                return reply(409, error="session_expired")
            result = store.record_engagement(db.engine, visitor_id=visitor_id, session_id=session_id,
                page_id=_uuid(payload["page_id"]), active_seconds=seconds, now=now)
        else:
            return reply(400, error="invalid_event")
        response = reply(200, accepted=True, page_id=payload["page_id"])
        return _set_identities(response, visitor_id, result.get("session_id", session_id), consent)
    except store.SessionExpired:
        # Remove the idle session so the browser can start a fresh page/session.
        response = reply(409, error="session_expired")
        response.delete_cookie(SESSION_COOKIE, path="/", secure=cookie_is_secure(), httponly=True, samesite="Lax")
        return response
    except store.AnalyticsConflict:
        # An old tab may hold a page from a previous session while another tab
        # already renewed the shared cookie. Replace its page, not that valid
        # cookie, otherwise tabs would repeatedly invalidate each other.
        return reply(409, error="page_session_mismatch")
    except Exception as exc:
        current_app.logger.warning("PortoBreak session analytics unavailable (%s)", type(exc).__name__)
        return reply(503, error="analytics_unavailable")


def associate_booking(booking_id):
    consent = read_cookie_consent()
    if not enabled() or not consent or not consent.get("analytics"):
        return
    visitor_id, session_id = _identities()
    if not visitor_id or not session_id:
        return
    try:
        store.link_booking(db.engine, visitor_id=visitor_id, session_id=session_id,
                           booking_id=booking_id, now=_now())
    except Exception as exc:
        current_app.logger.warning("PortoBreak conversion analytics unavailable (%s)", type(exc).__name__)
