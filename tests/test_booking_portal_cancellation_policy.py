from datetime import date
from urllib.parse import parse_qs, urlsplit

from app import app
from blueprints.booking_portal import _cancellation_policy_context, _cancellation_policy_url


def test_cancellation_policy_matches_business_example():
    policy = _cancellation_policy_context(date(2026, 9, 29), "pt", today=date(2026, 9, 18))

    assert policy["free_until"] == "2026-09-18"
    assert policy["partial_from"] == "2026-09-19"
    assert policy["no_refund_from"] == "2026-09-29"
    assert policy["free_message_text"] == "Cancelamento gratuito até 18 de setembro."
    assert policy["partial_message_text"] == "A partir de 19 de setembro às 00:00, o reembolso é de 50%."
    assert policy["none_message_text"] == "A partir de 29 de setembro às 00:00, não existe direito a reembolso."
    assert policy["show_free_cancellation"] is True


def test_free_cancellation_message_stops_at_midnight_of_partial_period():
    policy = _cancellation_policy_context(date(2026, 9, 29), "pt", today=date(2026, 9, 19))

    assert policy["show_free_cancellation"] is False
    assert policy["policy_link"] == "Políticas de cancelamento"


def test_cancellation_policy_without_checkin_has_no_specific_dates():
    policy = _cancellation_policy_context(None, "pt")

    assert policy["has_dates"] is False
    assert "free_message_text" not in policy


def test_cancellation_policy_is_localized():
    policy = _cancellation_policy_context(date(2026, 9, 29), "en")

    assert policy["free_message_text"] == "Free cancellation until 18 September."
    assert policy["partial_message_text"] == "From 19 September at 00:00, the refund is 50%."


def test_cancellation_policy_url_keeps_exact_reservation_location():
    return_to = "/reservas/12?lang=pt&checkin=2026-10-14&checkout=2026-10-16&adults=2"

    with app.test_request_context():
        policy_url = _cancellation_policy_url(date(2026, 10, 14), "pt", return_to)

    query = parse_qs(urlsplit(policy_url).query)
    assert query["checkin"] == ["2026-10-14"]
    assert query["return_to"] == [return_to]


def test_cancellation_policy_url_rejects_external_return_location():
    with app.test_request_context():
        policy_url = _cancellation_policy_url(
            date(2026, 10, 14),
            "pt",
            "https://example.com/reservas/12",
        )

    assert "return_to=" not in policy_url
