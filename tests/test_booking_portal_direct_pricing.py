"""End-to-end invariants for PortoBreak-only direct prices."""

from datetime import date
from decimal import Decimal
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from services import booking_portal_pricing as pricing
from services import booking_portal_service as portal


class PortoBreakStayPricingTests(unittest.TestCase):
    def test_airbnb_search_url_uses_nmpesquisa_room_id_and_current_search(self):
        self.assertEqual(
            portal.build_airbnb_search_url(
                "21329922", date(2027, 2, 1), date(2027, 2, 4), 2
            ),
            "https://www.airbnb.pt/rooms/21329922?adults=2&check_in=2027-02-01&check_out=2027-02-04",
        )
        self.assertEqual(
            portal.build_airbnb_search_url(
                "https://www.airbnb.pt/rooms/21329922", date(2027, 2, 1), date(2027, 2, 4), 2
            ),
            "",
        )

    def test_stay_comparison_uses_each_real_airbnb_night(self):
        comparison = pricing.stay_price_comparison([
            Decimal("100.00"), Decimal("120.00"), Decimal("40.00"),
        ])
        self.assertEqual(comparison, {
            "nights": 3,
            "airbnb": Decimal("260.00"),
            "portobreak": Decimal("249.00"),
            "saving": Decimal("11.00"),
        })

    def test_catalog_comparisons_are_loaded_in_one_read_only_batch(self):
        rows = [
            {"property_name": "Stay One", "base_price": "80", "day": date(2030, 10, 1), "price": "100"},
            {"property_name": "Stay One", "base_price": "80", "day": date(2030, 10, 2), "price": "120"},
            {"property_name": "Stay Two", "base_price": "50", "day": None, "price": None},
        ]
        fake_db = Mock()
        fake_db.session.execute.return_value.mappings.return_value.all.return_value = rows
        with patch.object(pricing, "db", fake_db):
            comparisons = pricing.get_stay_price_comparisons(
                ["Stay One", "Stay Two"], date(2030, 10, 1), date(2030, 10, 3)
            )

        fake_db.session.execute.assert_called_once()
        sql = str(fake_db.session.execute.call_args.args[0]).upper()
        self.assertIn("PR_CALC_DAY", sql)
        self.assertIn("PR_ALOJAMENTO", sql)
        self.assertNotIn("UPDATE ", sql)
        self.assertEqual(comparisons["Stay One"], {
            "nights": 2,
            "airbnb": Decimal("220.00"),
            "portobreak": Decimal("211.00"),
            "saving": Decimal("9.00"),
        })
        self.assertEqual(comparisons["Stay Two"], {
            "nights": 2,
            "airbnb": Decimal("100.00"),
            "portobreak": Decimal("96.00"),
            "saving": Decimal("4.00"),
        })

    def test_channel_pricing_engine_remains_independent_from_portobreak_rule(self):
        channel_engine = (Path(__file__).resolve().parents[1] / "price_engine.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("booking_portal_pricing", channel_engine)
        self.assertNotIn("portobreak_nightly_price", channel_engine)
        self.assertIn("FATOR_BOOKING", channel_engine)
        self.assertIn("SYNC_BOOKING", channel_engine)

    def _nightly_prices(self):
        source_rows = [
            {"DIA": date(2030, 10, 1), "PRECO_FINAL": Decimal("100.00")},
            {"DIA": date(2030, 10, 2), "PRECO_FINAL": Decimal("120.00")},
            {"DIA": date(2030, 10, 3), "PRECO_FINAL": Decimal("40.00")},
        ]
        nightly_result = Mock()
        nightly_result.mappings.return_value.all.return_value = source_rows
        base_result = Mock()
        base_result.mappings.return_value.first.return_value = {"PRECO_BASE": Decimal("90.00")}
        fake_db = Mock()
        fake_db.session.execute.side_effect = [nightly_result, base_result]
        with patch.object(portal, "db", fake_db):
            prices = portal._price_manager_nightly_prices(
                "Test Stay", date(2030, 10, 1), date(2030, 10, 4)
            )
        return source_rows, prices

    def test_each_night_is_discounted_before_the_stay_is_summed(self):
        source_rows, prices = self._nightly_prices()
        self.assertEqual(
            [item["valor_airbnb"] for item in prices],
            [Decimal("100.00"), Decimal("120.00"), Decimal("40.00")],
        )
        self.assertEqual(
            [item["valor"] for item in prices],
            [Decimal("96"), Decimal("115"), Decimal("38")],
        )
        self.assertEqual(sum(item["valor"] for item in prices), Decimal("249"))
        self.assertEqual([row["PRECO_FINAL"] for row in source_rows], [
            Decimal("100.00"), Decimal("120.00"), Decimal("40.00"),
        ])

    def test_cleaning_and_existing_fees_are_not_discounted(self):
        _, prices = self._nightly_prices()
        stay = {
            "id": "stay-1",
            "nome_interno": "Test Stay",
            "valor_extra": Decimal("10.00"),
            "extra_mais_que": 2,
            "taxa_limpeza": Decimal("37.50"),
        }
        with (
            patch.object(portal, "get_alojamento", return_value=stay),
            patch.object(portal, "_price_manager_nightly_prices", return_value=prices),
        ):
            result = portal.calcular_preco(
                "stay-1", date(2030, 10, 1), date(2030, 10, 4), 3
            )

        self.assertEqual(result["preco_noites_airbnb"], Decimal("260.00"))
        self.assertEqual(result["preco_noites"], Decimal("249.00"))
        self.assertEqual(result["poupanca_noites"], Decimal("11.00"))
        self.assertEqual(result["hospedes_extra_total"], Decimal("30.00"))
        self.assertEqual(result["limpeza"], Decimal("37.50"))
        self.assertEqual(result["taxa_turistica"], Decimal("27.00"))
        self.assertEqual(result["valor"], Decimal("343.50"))
        self.assertEqual(result["preco_total_airbnb"], Decimal("354.50"))
        self.assertEqual(result["preco_total_portobreak"], Decimal("343.50"))

    def test_the_calculated_total_is_the_booking_snapshot_and_stripe_amount(self):
        _, prices = self._nightly_prices()
        stay = {
            "id": "stay-1",
            "nome": "Test Stay",
            "nome_interno": "Test Stay",
            "valor_extra": Decimal("0.00"),
            "extra_mais_que": 0,
            "taxa_limpeza": Decimal("30.00"),
        }
        with (
            patch.object(portal, "get_alojamento", return_value=stay),
            patch.object(portal, "_price_manager_nightly_prices", return_value=prices),
        ):
            quote = portal.calcular_preco(
                "stay-1", date(2030, 10, 1), date(2030, 10, 4), 1
            )

        fake_db = Mock()
        with (
            patch.object(portal, "db", fake_db),
            patch.object(portal, "get_alojamento", return_value=stay),
            patch.object(portal, "alojamento_disponivel", return_value=True),
            patch.object(portal, "alojamento_datas_permitidas", return_value={"allowed": True}),
            patch.object(portal, "calcular_preco", return_value=quote),
        ):
            request_result = portal.criar_pedido_reserva(
                "stay-1",
                {"checkin": "2030-10-01", "checkout": "2030-10-04", "adultos": 1},
                {"nome": "Guest", "email": "guest@example.com"},
            )

        booking_insert = fake_db.session.execute.call_args_list[-1]
        self.assertEqual(booking_insert.args[1]["preco_estimado"], quote["valor"])
        booking_data = json.loads(booking_insert.args[1]["dados_json"])
        self.assertEqual(booking_data["preco"]["limpeza"], "30.00")
        self.assertEqual(request_result["preco"]["valor"], quote["valor"])

        stripe_db = Mock()
        stripe_request = Mock(return_value={
            "id": "cs_test_1", "url": "https://checkout.stripe.test/1", "status": "open",
        })
        booking_snapshot = {
            "PBBKSTAMP": request_result["id"],
            "PBUSERSTAMP": None,
            "AL_NOME": "Test Stay",
            "CHECKIN": date(2030, 10, 1),
            "CHECKOUT": date(2030, 10, 4),
            "CLIENTE_EMAIL": "guest@example.com",
            "PRECO_ESTIMADO": quote["valor"],
            "PRECO_LABEL": quote["label"],
            "ESTADO": "PENDENTE",
        }
        with (
            patch.object(portal, "db", stripe_db),
            patch.object(portal, "_portal_payment_require_table"),
            patch.object(portal, "portal_stripe_mode", return_value="TEST"),
            patch.object(portal, "_portal_stripe_secret_key", return_value="sk_test_example"),
            patch.object(portal, "_portal_test_payment_booking", return_value=booking_snapshot),
            patch.object(portal, "_portal_stripe_request", stripe_request),
        ):
            portal.criar_checkout_teste_portal(
                request_result["id"],
                success_url="https://example.com/success",
                cancel_url="https://example.com/cancel",
            )

        stripe_payload = stripe_request.call_args.args[2]
        self.assertEqual(
            stripe_payload["line_items[0][price_data][unit_amount]"],
            str(int(quote["valor"] * 100)),
        )

    def test_operational_reservation_keeps_the_same_total_and_cleaning_fee(self):
        total = Decimal("294.00")
        payment = {
            "PBPAYSTAMP": "payment-1",
            "PBBKSTAMP": "booking-1",
            "RSSTAMP": None,
            "PAGAMENTO_ESTADO": "PAGO",
            "ALSTAMP": "stay-1",
            "CHECKIN": date(2030, 10, 1),
            "CHECKOUT": date(2030, 10, 4),
            "NOITES": 3,
            "ADULTOS": 1,
            "CRIANCAS": 0,
            "BEBES": 0,
            "CLIENTE_NOME": "Guest",
            "CLIENTE_EMAIL": "guest@example.com",
            "CLIENTE_TELEFONE": "",
            "CLIENTE_MORADA": "",
            "CLIENTE_PAIS": "Portugal",
            "CLIENTE_NIF": "",
            "PRECO_ESTIMADO": total,
            "OBSERVACOES": "",
            "TXLIMPEZA": Decimal("37.50"),
            "DADOS_JSON": '{"preco":{"limpeza":"37.50"}}',
            "ALOJAMENTO_INTERNO": "Test Stay",
        }
        payment_result = Mock()
        payment_result.mappings.return_value.first.return_value = payment
        conflict_result = Mock()
        conflict_result.scalar.return_value = None
        fake_db = Mock()
        fake_db.session.execute.side_effect = [
            payment_result, conflict_result, Mock(), Mock(), Mock(),
        ]

        with (
            patch.object(portal, "db", fake_db),
            patch.object(portal, "_portal_payment_require_table"),
        ):
            portal.registar_reserva_portal_pagamento("payment-1")

        reservation_params = fake_db.session.execute.call_args_list[2].args[1]
        self.assertEqual(reservation_params["limpeza"], Decimal("37.50"))
        self.assertEqual(reservation_params["estadia"] + reservation_params["limpeza"], total)


if __name__ == "__main__":
    unittest.main()
