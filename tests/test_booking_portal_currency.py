from datetime import date
from decimal import Decimal
from unittest.mock import Mock, patch

from flask import Flask
import pytest

from services import booking_portal_currency as currency
from services import booking_portal_service as portal
from blueprints import booking_portal as portal_blueprint


GBP = {
    "code": "GBP", "symbol": "£", "rate": "0.85000000",
    "effective_rate": "0.86275000", "margin_percent": "1.5000",
    "rate_date": "2026-09-22", "source": currency.ECB_SOURCE,
}


def test_initial_currency_detection_is_bounded_to_supported_countries():
    assert currency.detect_currency("PT") == "EUR"
    assert currency.detect_currency("FR") == "EUR"
    assert currency.detect_currency("GB") == "GBP"
    assert currency.detect_currency("US") == "USD"
    assert currency.detect_currency("CA") == "EUR"
    assert currency.detect_currency(None) == "EUR"


def test_ecb_rates_are_units_of_foreign_currency_per_euro():
    payload = b'''<?xml version="1.0" encoding="UTF-8"?>
    <Envelope xmlns="http://www.gesmes.org/xml/2002-08-01"
      xmlns:e="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
      <e:Cube><e:Cube time="2026-09-22"><e:Cube currency="USD" rate="1.1800"/>
      <e:Cube currency="GBP" rate="0.8700"/></e:Cube></e:Cube>
    </Envelope>'''
    rate_date, rates = currency.parse_ecb_daily_xml(payload)
    assert rate_date == date(2026, 9, 22)
    assert rates == {
        "EUR": Decimal("1.00000000"),
        "GBP": Decimal("0.87000000"),
        "USD": Decimal("1.18000000"),
    }


def test_margin_and_rounding_are_applied_only_after_eur_pricing():
    converted = currency.convert_stay_breakdown(
        direct_nights=249, airbnb_nights=260, extra=30,
        cleaning=37.50, tourist_tax=27, snapshot=GBP,
    )
    assert converted == {
        "direct_nights": Decimal("214.82"),
        "airbnb_nights": Decimal("224.32"),
        "extra": Decimal("25.88"),
        "cleaning": Decimal("32.35"),
        "tourist_tax": Decimal("23.29"),
        "direct_total": Decimal("296.34"),
        "airbnb_total": Decimal("305.84"),
        "saving": Decimal("9.50"),
        "currency": "GBP",
    }
    assert currency.convert_eur(47, GBP, whole=True) == Decimal("41")
    assert currency.amount_to_minor_units(converted["direct_total"], "GBP") == 29634


@pytest.mark.parametrize(("currency_code", "amount", "base_rate", "effective_rate", "margin", "minor"), [
    ("EUR", Decimal("343.50"), Decimal("1"), Decimal("1"), Decimal("0"), "34350"),
    ("GBP", Decimal("296.30"), Decimal("0.85000000"), Decimal("0.86275000"), Decimal("1.5000"), "29630"),
    ("USD", Decimal("400.60"), Decimal("1.14900000"), Decimal("1.16623500"), Decimal("1.5000"), "40060"),
])
def test_stripe_checkout_uses_the_exact_stored_presentment_amount_and_currency(
    currency_code, amount, base_rate, effective_rate, margin, minor,
):
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY="currency-test")
    booking = {
        "PBBKSTAMP": "booking-1", "PBUSERSTAMP": None, "AL_NOME": "Test Stay",
        "CHECKIN": date(2030, 10, 1), "CHECKOUT": date(2030, 10, 4),
        "CLIENTE_EMAIL": "guest@example.com", "PRECO_ESTIMADO": Decimal("343.50"),
        "PRECO_LABEL": "343.50 EUR", "ESTADO": "PENDENTE",
        "MOEDA_APRESENTACAO": currency_code, "VALOR_APRESENTADO": amount,
        "CAMBIO_APRESENTACAO": effective_rate, "CAMBIO_BASE": base_rate,
        "FX_MARGIN_PERCENT": margin, "FX_DATA_TAXA": date(2026, 9, 22),
        "FX_FONTE": currency.ECB_SOURCE,
    }
    fake_db = Mock()
    stripe_request = Mock(return_value={
        "id": "cs_test_1", "url": "https://checkout.stripe.test/1", "status": "open",
    })
    with (
        app.app_context(),
        patch.object(portal, "db", fake_db),
        patch.object(portal, "_portal_payment_require_table"),
        patch.object(portal, "portal_stripe_mode", return_value="TEST"),
        patch.object(portal, "_portal_stripe_secret_key", return_value="sk_test_example"),
        patch.object(portal, "_portal_test_payment_booking", return_value=booking),
        patch.object(portal, "_portal_stripe_request", stripe_request),
    ):
        result = portal.criar_checkout_teste_portal(
            "booking-1", success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
        )

    payload = stripe_request.call_args.args[2]
    assert payload["line_items[0][price_data][currency]"] == currency_code.lower()
    assert payload["line_items[0][price_data][unit_amount]"] == minor
    assert payload["payment_intent_data[metadata][pb_payment_id]"] == result["id"]
    insert_params = fake_db.session.execute.call_args_list[0].args[1]
    assert insert_params["eur_amount"] == Decimal("343.50")
    assert insert_params["amount"] == amount
    assert insert_params["currency"] == currency_code


def test_manual_currency_choice_persists_independently_from_language_and_search():
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY="currency-session-test")
    app.register_blueprint(portal_blueprint.bp)
    with patch.object(portal_blueprint, "load_currency_snapshot", return_value=GBP):
        client = app.test_client()
        response = client.post("/reservas/moeda", data={
            "currency": "GBP",
            "return_to": "/reservas?lang=pt&checkin=2030-10-01&checkout=2030-10-03",
        })
    assert response.status_code == 302
    assert response.headers["Location"].endswith(
        "/reservas?lang=pt&checkin=2030-10-01&checkout=2030-10-03"
    )
    with client.session_transaction() as session:
        assert session[portal_blueprint.PORTAL_CURRENCY_SESSION_KEY]["code"] == "GBP"


def test_stripe_net_comes_from_the_real_balance_transaction_and_updates_rs():
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY="stripe-net-test")
    fake_db = Mock()
    payment = {
        "PBPAYSTAMP": "pay-1", "PBBKSTAMP": "booking-1", "RSSTAMP": "rs-1",
        "PAYMENT_INTENT_ID": "pi_1", "CHARGE_ID": None,
        "BALANCE_TRANSACTION_ID": None, "MOEDA": "GBP", "VALOR": Decimal("441.00"),
    }
    stripe_request = Mock(return_value={
        "id": "pi_1",
        "latest_charge": {
            "id": "ch_1",
            "balance_transaction": {
                "id": "txn_1", "net": 49327, "currency": "eur",
            },
        },
    })
    with (
        app.app_context(),
        patch.object(portal, "db", fake_db),
        patch.object(portal, "_portal_payment_identifier", return_value=payment),
        patch.object(portal, "_portal_stripe_request", stripe_request),
    ):
        result = portal._portal_reconcile_stripe_payment("pay-1")

    assert result["net"] == Decimal("493.27")
    assert result["net_currency"] == "EUR"
    assert result["charge_id"] == "ch_1"
    assert result["balance_transaction_id"] == "txn_1"
    params = [call.args[1] for call in fake_db.session.execute.call_args_list]
    assert params[0]["net"] == Decimal("493.27")
    assert params[1]["rsstamp"] == "rs-1"
    assert fake_db.session.commit.call_count == 1
