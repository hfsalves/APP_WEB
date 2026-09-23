"""Native PortoBreak WhatsApp click-to-chat configuration and message building."""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from urllib.parse import urlencode
from zoneinfo import ZoneInfo


WHATSAPP_TIMEZONE = "Europe/Lisbon"
WHATSAPP_OPEN_MINUTE = 9 * 60 + 30
WHATSAPP_CLOSE_MINUTE = 23 * 60
DEFAULT_WHATSAPP_NUMBER = "351934266823"
_LISBON = ZoneInfo(WHATSAPP_TIMEZONE)


def normalize_whatsapp_number(value) -> str:
    number = re.sub(r"\D+", "", str(value or ""))
    return number if 8 <= len(number) <= 15 and not number.startswith("0") else ""


def configured_whatsapp_number(config) -> str:
    return normalize_whatsapp_number(
        config.get("PORTOBREAK_WHATSAPP_NUMBER") or DEFAULT_WHATSAPP_NUMBER
    )


def portugal_time(moment=None) -> datetime:
    current = moment or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(_LISBON)


def support_is_open(moment=None) -> bool:
    local = portugal_time(moment)
    minute = local.hour * 60 + local.minute
    return WHATSAPP_OPEN_MINUTE <= minute < WHATSAPP_CLOSE_MINUTE


def _date_label(value) -> str:
    if isinstance(value, datetime):
        value = value.date()
    if not isinstance(value, date):
        try:
            value = date.fromisoformat(str(value or "")[:10])
        except (TypeError, ValueError):
            return ""
    return value.strftime("%d/%m/%Y")


def _guest_count(search) -> int | None:
    try:
        value = (search or {}).get("hospedes")
        if value is None:
            adults = (search or {}).get("adultos")
            children = (search or {}).get("criancas")
            value = (int(adults or 0) + int(children or 0)) or None
        count = int(value)
        return count if 1 <= count <= 50 else None
    except (TypeError, ValueError):
        return None


def build_message(copy: dict, *, property_name="", search=None) -> str:
    search = search or {}
    checkin = _date_label(search.get("checkin"))
    checkout = _date_label(search.get("checkout"))
    has_dates = bool(checkin and checkout)
    guests = _guest_count(search)
    guest_label = copy["whatsapp_guest"] if guests == 1 else copy["whatsapp_guests"]
    values = {
        "property": str(property_name or "").strip(),
        "checkin": checkin,
        "checkout": checkout,
        "guests": guests,
        "guest_label": guest_label,
    }
    prefix = "whatsapp_property" if values["property"] else "whatsapp_generic"
    suffix = "_dates_guests" if has_dates and guests else "_dates" if has_dates else "_guests" if guests else ""
    return copy[prefix + suffix].format(**values)


def build_whatsapp_context(config, copy: dict, *, property_name="", search=None, moment=None) -> dict:
    number = configured_whatsapp_number(config)
    message = build_message(copy, property_name=property_name, search=search)
    return {
        "enabled": bool(number),
        "number": number,
        "url": f"https://wa.me/{number}?{urlencode({'text': message})}" if number else "",
        "message": message,
        "timezone": WHATSAPP_TIMEZONE,
        "open_minute": WHATSAPP_OPEN_MINUTE,
        "close_minute": WHATSAPP_CLOSE_MINUTE,
        "server_open": support_is_open(moment),
        "property_id": str((search or {}).get("property_id") or ""),
    }
