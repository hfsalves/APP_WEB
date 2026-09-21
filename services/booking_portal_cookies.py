"""Purpose-specific choices, separate from the essential booking session."""

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from flask import current_app, request
from itsdangerous import BadData, URLSafeTimedSerializer


CONSENT_COOKIE = "portobreak_privacy"
LANG_COOKIE = "portobreak_lang"
CONSENT_VERSION = "2026-09-21.1"
CONSENT_MAX_AGE = 180 * 24 * 60 * 60
LANG_MAX_AGE = 365 * 24 * 60 * 60
LANGUAGES = {"pt", "en", "es", "fr"}
PUBLIC_HOSTS = {"portobreak.com", "www.portobreak.com"}
UI_PATH = Path(__file__).resolve().parent.parent / "content" / "booking_portal" / "cookie_ui.json"


def _serializer():
    return URLSafeTimedSerializer(current_app.secret_key, salt="portobreak-cookie-preferences-v1")


def _public_host():
    host = request.host.split(":", 1)[0].lower()
    forwarded = (request.headers.get("X-Forwarded-Host") or "").split(",", 1)[0].strip().lower()
    return forwarded if forwarded in PUBLIC_HOSTS else host


def cookie_is_secure():
    # Public cookies remain Secure even when HTTPS terminates at the proxy.
    return request.is_secure or _public_host() in PUBLIC_HOSTS


def is_same_origin_request():
    try:
        origin = urlsplit(request.headers.get("Origin") or "")
    except ValueError:
        return False
    if origin.scheme not in {"http", "https"} or origin.path or origin.query or origin.fragment:
        return False
    expected_host = _public_host() if _public_host() in PUBLIC_HOSTS else request.host.lower()
    return (
        origin.netloc.lower() == expected_host
        and (not cookie_is_secure() or origin.scheme == "https")
        and request.headers.get("Sec-Fetch-Site", "same-origin") == "same-origin"
    )


def read_cookie_consent():
    value = request.cookies.get(CONSENT_COOKIE)
    if not value:
        return None
    try:
        choice = _serializer().loads(value, max_age=CONSENT_MAX_AGE)
    except BadData:
        return None
    if not isinstance(choice, dict) or choice.get("version") != CONSENT_VERSION:
        return None
    if any(type(choice.get(key)) is not bool for key in ("preferences", "external_maps", "analytics")):
        return None
    if not isinstance(choice.get("decided_at"), str) or type(choice.get("expires_at")) is not int:
        return None
    if choice["expires_at"] <= int(datetime.now(timezone.utc).timestamp()):
        return None
    return choice


def save_cookie_consent(response, *, preferences, external_maps, lang, analytics=False):
    if any(type(value) is not bool for value in (preferences, external_maps, analytics)):
        raise ValueError("Cookie preferences must be boolean values")
    now = datetime.now(timezone.utc)
    choice = {
        "version": CONSENT_VERSION,
        "decided_at": now.isoformat(timespec="seconds"),
        "expires_at": int(now.timestamp()) + CONSENT_MAX_AGE,
        "preferences": preferences,
        "external_maps": external_maps,
        "analytics": analytics,
    }
    response.set_cookie(
        CONSENT_COOKIE, _serializer().dumps(choice), max_age=CONSENT_MAX_AGE,
        secure=cookie_is_secure(), httponly=True, samesite="Lax", path="/",
    )
    apply_language_cookie(response, lang, choice)
    return choice


def apply_language_cookie(response, lang, choice):
    if choice and choice["preferences"] and lang in LANGUAGES:
        if request.cookies.get(LANG_COOKIE) != lang:
            response.set_cookie(
                LANG_COOKIE, lang, max_age=LANG_MAX_AGE, secure=cookie_is_secure(),
                httponly=True, samesite="Lax", path="/",
            )
    elif LANG_COOKIE in request.cookies:
        response.delete_cookie(LANG_COOKIE, path="/", secure=cookie_is_secure(), httponly=True, samesite="Lax")
    return response


def cookie_ui(lang):
    return json.loads(UI_PATH.read_text(encoding="utf-8"))[lang if lang in LANGUAGES else "pt"]
