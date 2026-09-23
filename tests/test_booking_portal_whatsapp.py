"""PortoBreak native WhatsApp contact context, schedule and localized messages."""

from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

import pytest

from blueprints.booking_portal import _t
from services.booking_portal_whatsapp import (
    build_whatsapp_context,
    configured_whatsapp_number,
    support_is_open,
)


@pytest.mark.parametrize(
    ("instant", "expected"),
    [
        (datetime(2026, 1, 15, 9, 29, tzinfo=timezone.utc), False),
        (datetime(2026, 1, 15, 9, 30, tzinfo=timezone.utc), True),
        (datetime(2026, 1, 15, 22, 59, tzinfo=timezone.utc), True),
        (datetime(2026, 1, 15, 23, 0, tzinfo=timezone.utc), False),
        # Europe/Lisbon is UTC+1 in July: these UTC instants are the same local boundaries.
        (datetime(2026, 7, 15, 8, 29, tzinfo=timezone.utc), False),
        (datetime(2026, 7, 15, 8, 30, tzinfo=timezone.utc), True),
        (datetime(2026, 7, 15, 21, 59, tzinfo=timezone.utc), True),
        (datetime(2026, 7, 15, 22, 0, tzinfo=timezone.utc), False),
    ],
)
def test_support_schedule_uses_portugal_time_with_dst(instant, expected):
    assert support_is_open(instant) is expected


def test_visitor_timezone_does_not_change_portugal_schedule():
    instant = datetime(2026, 7, 15, 8, 30, tzinfo=timezone.utc)
    tokyo_view = instant.astimezone(ZoneInfo("Asia/Tokyo"))
    new_york_view = instant.astimezone(ZoneInfo("America/New_York"))
    assert support_is_open(tokyo_view) is True
    assert support_is_open(new_york_view) is True


def test_number_has_one_central_default_and_accepts_environment_override():
    assert configured_whatsapp_number({}) == "351934266823"
    assert configured_whatsapp_number({"PORTOBREAK_WHATSAPP_NUMBER": "+351 912 345 678"}) == "351912345678"
    assert configured_whatsapp_number({"PORTOBREAK_WHATSAPP_NUMBER": "invalid"}) == ""


@pytest.mark.parametrize(
    ("lang", "generic", "specific"),
    [
        ("pt", "Olá! Procuro alojamento no Porto de 01/02/2027 a 04/02/2027 para 2 hóspedes.",
         "Olá! Estou interessado no Bessa - Casinha Típica, de 01/02/2027 a 04/02/2027, para 2 hóspedes."),
        ("en", "Hi! I'm looking for a place to stay in Porto from 01/02/2027 to 04/02/2027 for 2 guests.",
         "Hi! I'm interested in Bessa - Casinha Típica, from 01/02/2027 to 04/02/2027, for 2 guests."),
        ("es", "¡Hola! Busco alojamiento en Oporto del 01/02/2027 al 04/02/2027 para 2 huéspedes.",
         "¡Hola! Me interesa Bessa - Casinha Típica, del 01/02/2027 al 04/02/2027, para 2 huéspedes."),
        ("fr", "Bonjour ! Je cherche un hébergement à Porto du 01/02/2027 au 04/02/2027 pour 2 voyageurs.",
         "Bonjour ! Je suis intéressé(e) par Bessa - Casinha Típica, du 01/02/2027 au 04/02/2027, pour 2 voyageurs."),
    ],
)
def test_localized_catalog_and_property_messages(lang, generic, specific):
    search = {"checkin": "2027-02-01", "checkout": "2027-02-04", "hospedes": 2}
    generic_context = build_whatsapp_context({}, _t(lang), search=search)
    property_context = build_whatsapp_context({}, _t(lang), property_name="Bessa - Casinha Típica", search=search)
    assert generic_context["message"] == generic
    assert property_context["message"] == specific
    parsed = urlsplit(property_context["url"])
    assert parsed.scheme == "https" and parsed.netloc == "wa.me" and parsed.path == "/351934266823"
    assert parse_qs(parsed.query) == {"text": [specific]}


def test_messages_do_not_invent_missing_dates_or_guests():
    copy = _t("pt")
    assert build_whatsapp_context({}, copy)["message"] == "Olá! Preciso de ajuda para encontrar um alojamento no Porto."
    assert build_whatsapp_context({}, copy, property_name="Bessa")["message"] == "Olá! Estou interessado no Bessa."
    assert build_whatsapp_context({}, copy, search={"hospedes": 1})["message"] == "Olá! Procuro alojamento no Porto para 1 hóspede."
    partial_dates = {"checkin": "2027-02-01", "hospedes": 2}
    assert "01/02/2027" not in build_whatsapp_context({}, copy, search=partial_dates)["message"]

