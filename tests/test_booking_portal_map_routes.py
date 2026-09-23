"""Map API contracts, using fake inventory and prices and prohibiting DB access."""

import copy
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit

from flask import Flask
from sqlalchemy.exc import SQLAlchemyError

from blueprints.booking_portal import _t, bp


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_MARKER = "PRIVATE-MAP-TEST-NOT-FOR-PUBLIC-JSON"
PROPERTY = {
    "id": "map-stay",
    "nome": "Casa com varanda",
    "descricao": "Uma casa para descobrir o Porto.",
    "descricao_curta": "Uma casa no Porto.",
    "localizacao": "Porto",
    "capacidade": 4,
    "lot_adultos": 3,
    "lot_criancas": 1,
    "berco": True,
    "tipologia": "T2",
    "foto_principal": "/static/map-stay.jpg",
    "fotos": [{"url": "/static/map-stay.jpg", "alt": "Sala"}],
    "preco_desde": "95 EUR",
    "airbnb_room_id": "21329922",
    "licenca": PRIVATE_MARKER,
    "morada": PRIVATE_MARKER,
    "nome_interno": PRIVATE_MARKER,
    "maps_url": "https://example.invalid/" + PRIVATE_MARKER,
    "owner": {"email": PRIVATE_MARKER},
    "access_code": PRIVATE_MARKER,
}
QUOTE = {
    "valor": Decimal("444.00"),
    "label": "444.00 EUR",
    "noites": 3,
    "hospedes": 3,
    "preco_noites_airbnb_label": "336.00 EUR",
    "preco_noites_label": "324.00 EUR",
    "preco_total_airbnb_label": "456.00 EUR",
    "preco_total_portobreak_label": "444.00 EUR",
    "poupanca_noites_label": "12.00 EUR",
    "hospedes_extra": 1,
    "hospedes_extra_total_label": "60.00 EUR",
    "limpeza_label": "33.00 EUR",
    "taxa_turistica_label": "27.00 EUR",
    "taxa_turistica_dias": 3,
    "linhas": [{"label": "old untranslated line", "value": "444.00 EUR"}],
    "precos_noite": [{"internal_price_manager_id": PRIVATE_MARKER}],
    "internal": PRIVATE_MARKER,
}
SEARCH = {
    "checkin": "2035-10-14",
    "checkout": "2035-10-17",
    "adultos": "2",
    "criancas": "1",
    "bebes": "1",
    "lang": "en",
}
CATALOG_ITEM_KEYS = {"id", "name", "lat", "lon", "available", "detail_url", "quote_url"}
QUOTE_KEYS = {
    "id", "name", "image", "tipologia", "capacity", "location", "from_price",
    "price", "available", "reserve_enabled", "errors", "notes", "detail_url",
    "reserve_url", "dates", "guest_summary", "cancellation",
}


class BookingPortalMapRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(
            __name__,
            template_folder=str(ROOT / "templates"),
            static_folder=str(ROOT / "static"),
        )
        self.app.config.update(TESTING=True, SECRET_KEY="map-route-tests-only")
        self.app.register_blueprint(bp)
        self.client = self.app.test_client()
        self.property = copy.deepcopy(PROPERTY)
        self.mocks = {}
        self.catalog_data = {
            "items": [{
                "id": "map-stay", "name": PROPERTY["nome"], "lat": 41.16, "lon": -8.61,
                "available": True, "morada": PRIVATE_MARKER, "licenca": PRIVATE_MARKER,
                "private_metadata": {"owner": PRIVATE_MARKER},
            }],
            "total": 100, "matched": 22, "missing_coordinates": 2,
            "has_search": True, "has_dates": True,
        }
        fixtures = {
            "_portal_current_user": {"return_value": None},
            "get_map_catalog": {"side_effect": lambda *_a, **_k: copy.deepcopy(self.catalog_data)},
            "get_alojamento": {"side_effect": lambda *_a, **_k: copy.deepcopy(self.property)},
            "alojamento_disponivel": {"return_value": True},
            "alojamento_datas_permitidas": {"return_value": {"allowed": True, "errors": []}},
            "calcular_preco": {"side_effect": lambda *_a, **_k: copy.deepcopy(QUOTE)},
            "get_alojamentos_disponiveis_page": {"return_value": {
                "items": [copy.deepcopy(PROPERTY)], "total": 1, "page": 1, "pages": 1,
                "per_page": 18, "has_prev": False, "has_next": False,
            }},
            "get_calendario_ocupacao": {"side_effect": AssertionError("A popup must not load the full calendar")},
        }
        for name, options in fixtures.items():
            patcher = patch("blueprints.booking_portal." + name, create=name == "get_map_catalog", **options)
            self.mocks[name] = patcher.start()
            self.addCleanup(patcher.stop)

        # Even an accidental service call cannot reach an application database.
        self.db_calls = {
            method: Mock(side_effect=AssertionError("Map routes must not access the database in these tests"))
            for method in ("execute", "add", "add_all", "delete", "flush", "commit")
        }
        db_patch = patch("models.db.session", SimpleNamespace(**self.db_calls))
        db_patch.start()
        self.addCleanup(db_patch.stop)
        self.write_mocks = []
        for name in ("criar_pedido_reserva", "criar_checkout_teste_portal", "queue_email", "send_email_now"):
            patcher = patch("blueprints.booking_portal." + name, side_effect=AssertionError("Map browsing must not write or send"))
            self.write_mocks.append(patcher.start())
            self.addCleanup(patcher.stop)

    def tearDown(self):
        for mock in [*self.write_mocks, *self.db_calls.values()]:
            mock.assert_not_called()

    def get_quote(self, query=None):
        response = self.client.get("/reservas/map-stay/simulacao-mapa", query_string=SEARCH if query is None else query)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)
        return response, response.get_json()

    def assert_private_no_store(self, response):
        self.assertTrue(response.cache_control.private)
        self.assertTrue(response.cache_control.no_store)

    def assert_link(self, url, path, query):
        parsed = urlsplit(url)
        self.assertFalse(parsed.netloc)
        self.assertEqual(parsed.path, path)
        self.assertEqual(parse_qs(parsed.query), {key: [value] for key, value in query.items()})

    def test_catalog_exposes_only_public_marker_fields_and_counts(self):
        response = self.client.get("/reservas/mapa-dados", query_string=SEARCH)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)
        payload = response.get_json()
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(set(payload["items"][0]), CATALOG_ITEM_KEYS)
        self.assertEqual(payload["items"][0]["available"], True)
        self.assertEqual((payload["total"], payload["matched"], payload["missing_coordinates"]), (100, 22, 2))
        self.assertTrue(payload["has_search"])
        self.assertTrue(payload["has_dates"])
        self.assertNotIn(PRIVATE_MARKER, response.get_data(as_text=True))
        self.assert_private_no_store(response)
        self.mocks["get_alojamento"].assert_not_called()
        self.mocks["calcular_preco"].assert_not_called()

    def test_catalog_passes_normalized_filters_and_preserves_booking_context_in_links(self):
        query = {**SEARCH, "lang": "fr", "q": "Porto & Centro", "page": "6"}
        response = self.client.get("/reservas/mapa-dados", query_string=query)
        self.assertEqual(response.status_code, 200)
        marker = response.get_json()["items"][0]
        args, kwargs = self.mocks["get_map_catalog"].call_args
        params = args[0] if args else kwargs["params"]
        self.assertEqual(params["checkin"], date(2035, 10, 14))
        self.assertEqual(params["checkout"], date(2035, 10, 17))
        self.assertEqual((params["adultos"], params["criancas"], params["bebes"], params["hospedes"]), (2, 1, 1, 3))
        self.assertEqual(params["query"], "Porto & Centro")
        self.assertEqual(params["raw"]["lang"], "fr")
        expected = {**SEARCH, "lang": "fr"}
        self.assert_link(marker["detail_url"], "/reservas/map-stay", expected)
        self.assert_link(marker["quote_url"], "/reservas/map-stay/simulacao-mapa", {**expected, "q": query["q"]})

    def test_catalog_without_dates_identifies_undated_markers_without_pricing(self):
        self.catalog_data.update(has_search=False, has_dates=False)
        response = self.client.get("/reservas/mapa-dados", query_string={"lang": "es"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertFalse(data["has_dates"])
        self.assertFalse(data["has_search"])
        self.assertTrue(data["items"][0]["available"])
        self.assertNotIn("price", data["items"][0])
        self.mocks["calcular_preco"].assert_not_called()

    def test_quote_without_dates_has_only_starting_price_and_no_reservation_action(self):
        response, data = self.get_quote({"lang": "en"})
        self.assertIsNone(data["price"])
        self.assertIsNone(data["available"])
        self.assertFalse(data["reserve_enabled"])
        self.assertEqual(data["from_price"], PROPERTY["preco_desde"])
        self.assertEqual(data["errors"], [])
        self.assert_private_no_store(response)
        self.mocks["calcular_preco"].assert_not_called()
        self.mocks["alojamento_disponivel"].assert_not_called()
        self.mocks["alojamento_datas_permitidas"].assert_not_called()

    def test_valid_quote_is_an_estimate_with_localized_price_lines_and_public_fields_only(self):
        response, data = self.get_quote()
        self.assertEqual(set(data), QUOTE_KEYS)
        self.assertEqual((data["id"], data["name"], data["image"]), (PROPERTY["id"], PROPERTY["nome"], PROPERTY["foto_principal"]))
        self.assertEqual((data["capacity"], data["location"], data["tipologia"]), (4, "Porto", "T2"))
        self.assertEqual(set(data["price"]), {
            "label", "airbnb_total_label", "airbnb_url", "direct_total_label", "saving_label",
            "lines", "nights", "is_estimate",
        })
        self.assertEqual(data["price"]["label"], "444.00 EUR")
        self.assertEqual(data["price"]["airbnb_total_label"], "456.00 EUR")
        self.assertEqual(
            data["price"]["airbnb_url"],
            "https://www.airbnb.pt/rooms/21329922?adults=2&check_in=2035-10-14&check_out=2035-10-17",
        )
        self.assertEqual(data["price"]["direct_total_label"], "444.00 EUR")
        self.assertEqual(data["price"]["saving_label"], "12.00 EUR")
        self.assertEqual(data["price"]["nights"], 3)
        self.assertIs(data["price"]["is_estimate"], True)
        self.assertIs(data["available"], True)
        self.assertIs(data["reserve_enabled"], True)
        self.assertEqual(data["dates"], {"checkin": SEARCH["checkin"], "checkout": SEARCH["checkout"]})
        self.assertEqual(data["guest_summary"], "2 Adults / 1 Children / 1 Babies")
        self.assertEqual(data["errors"], [])
        lines = data["price"]["lines"]
        self.assertEqual(len(lines), 4)
        self.assertEqual([line["value"] for line in lines], ["324.00 EUR", "60.00 EUR", "33.00 EUR", "27.00 EUR"])
        self.assertTrue(all(set(line) == {"label", "value"} for line in lines))
        self.assertEqual(lines[0]["label"], _t("en")["nights_line"] + " (3)")
        self.assertEqual(lines[2]["label"], _t("en")["cleaning_fee"])
        self.assertNotIn(PRIVATE_MARKER, response.get_data(as_text=True))
        self.assert_private_no_store(response)
        self.mocks["get_alojamento"].assert_called_once_with("map-stay", lang="en")
        self.mocks["calcular_preco"].assert_called_once_with("map-stay", date(2035, 10, 14), date(2035, 10, 17), 3)
        self.mocks["alojamento_disponivel"].assert_called_once_with("map-stay", date(2035, 10, 14), date(2035, 10, 17))
        self.mocks["get_calendario_ocupacao"].assert_not_called()

    def test_quote_links_preserve_dates_party_and_language_in_all_languages(self):
        for lang in ("pt", "en", "es", "fr"):
            with self.subTest(lang=lang):
                query = {**SEARCH, "lang": lang}
                _, data = self.get_quote(query)
                self.assert_link(data["detail_url"], "/reservas/map-stay", query)
                self.assert_link(data["reserve_url"], "/reservas/map-stay/reservar", query)
                self.assertEqual(set(data["cancellation"]), {"label", "url"})
                cancellation_query = parse_qs(urlsplit(data["cancellation"]["url"]).query)
                self.assertEqual(cancellation_query["lang"], [lang])
                self.assertEqual(cancellation_query["checkin"], [SEARCH["checkin"]])
                self.assertTrue(data["cancellation"]["label"])

    def test_legacy_guest_count_survives_reservation_link_as_adults(self):
        query = {"checkin": SEARCH["checkin"], "checkout": SEARCH["checkout"], "hospedes": "3", "lang": "fr"}
        _, data = self.get_quote(query)
        reserve_query = parse_qs(urlsplit(data["reserve_url"]).query)
        self.assertEqual(reserve_query["adultos"], ["3"])
        self.assertEqual(reserve_query["lang"], ["fr"])
        self.assertEqual(self.mocks["calcular_preco"].call_args.args[-1], 3)

    def test_invalid_dates_do_not_quote_or_enable_reservation(self):
        for change, key in (
            ({"checkin": "not-a-date"}, "invalid_date"),
            ({"checkout": ""}, "need_dates"),
            ({"checkout": SEARCH["checkin"]}, "checkout_after_checkin"),
            ({"checkout": "2035-10-13"}, "checkout_after_checkin"),
        ):
            with self.subTest(change=change):
                _, data = self.get_quote({**SEARCH, **change})
                self.assertIn(_t("en")[key], data["errors"])
                self.assertIsNone(data["price"])
                self.assertIs(data["available"], False)
                self.assertFalse(data["reserve_enabled"])
        self.mocks["calcular_preco"].assert_not_called()
        self.mocks["alojamento_disponivel"].assert_not_called()

    def test_party_validation_blocks_quote_and_reservation(self):
        cases = (
            ({"adultos": "4", "criancas": "0"}, _t("en")["adults_capacity_error"].format(max=3)),
            ({"adultos": "3", "criancas": "2"}, _t("en")["total_capacity_error"].format(max=4)),
            ({"bebes": "3"}, _t("en")["babies_capacity_error"]),
            ({"adultos": "", "criancas": "1"}, _t("en")["need_adult"]),
            ({"adultos": "-1"}, _t("en")["invalid_guests"]),
            ({"adultos": "many"}, _t("en")["invalid_guests"]),
        )
        for change, message in cases:
            with self.subTest(change=change):
                _, data = self.get_quote({**SEARCH, **change})
                self.assertIn(message, data["errors"])
                self.assertIsNone(data["price"])
                self.assertIs(data["available"], False)
                self.assertFalse(data["reserve_enabled"])
        self.mocks["calcular_preco"].assert_not_called()
        self.mocks["alojamento_disponivel"].assert_not_called()

    def test_minimum_nights_and_blocked_arrival_departure_gaps_block_quote(self):
        for code, translation in (
            ("min_nights", _t("en")["calendar_min_nights"].format(min=5)),
            ("blocked_checkin", _t("en")["calendar_blocked_checkin"]),
            ("blocked_checkout", _t("en")["calendar_blocked_checkout"]),
        ):
            with self.subTest(code=code):
                self.mocks["alojamento_datas_permitidas"].return_value = {
                    "allowed": False, "errors": [code], "min_nights": 5,
                }
                _, data = self.get_quote()
                self.assertIn(translation, data["errors"])
                self.assertIsNone(data["price"])
                self.assertIs(data["available"], False)
                self.assertFalse(data["reserve_enabled"])
        self.mocks["calcular_preco"].assert_not_called()
        self.mocks["alojamento_disponivel"].assert_not_called()

    def test_occupied_dates_never_enable_a_reservation(self):
        self.mocks["alojamento_disponivel"].return_value = False
        _, data = self.get_quote()
        self.assertIs(data["available"], False)
        self.assertIs(data["reserve_enabled"], False)
        self.assertIsNone(data["price"])
        self.assertIn(_t("en")["unavailable_selected"], data["errors"])
        self.mocks["calcular_preco"].assert_not_called()

    def test_available_dates_without_a_usable_price_do_not_enable_reservation(self):
        self.mocks["calcular_preco"].side_effect = None
        self.mocks["calcular_preco"].return_value = {
            "valor": None, "label": "Preco sob consulta", "noites": 3, "linhas": [],
        }
        _, data = self.get_quote()
        self.assertIs(data["available"], True)
        self.assertIsNone(data["price"])
        self.assertIs(data["reserve_enabled"], False)
        self.assertTrue(data["errors"])

    def test_crib_note_is_informational_and_does_not_block_valid_dates(self):
        self.property["berco"] = False
        _, data = self.get_quote()
        self.assertIn(_t("en")["crib_unavailable"], data["notes"])
        self.assertEqual(data["errors"], [])
        self.assertTrue(data["reserve_enabled"])

    def test_unknown_property_returns_404_without_pricing_or_booking(self):
        self.property = None
        response = self.client.get("/reservas/missing/simulacao-mapa", query_string=SEARCH)
        self.assertEqual(response.status_code, 404)
        self.mocks["calcular_preco"].assert_not_called()
        self.mocks["alojamento_disponivel"].assert_not_called()

    def test_database_errors_return_generic_uncacheable_json_without_private_details(self):
        for service, path in (
            ("get_map_catalog", "/reservas/mapa-dados"),
            ("get_alojamento", "/reservas/map-stay/simulacao-mapa"),
        ):
            with self.subTest(service=service), patch.object(self.app.logger, "exception"):
                self.mocks[service].side_effect = SQLAlchemyError(PRIVATE_MARKER)
                response = self.client.get(path, query_string=SEARCH)
                self.assertEqual(response.status_code, 503)
                self.assertTrue(response.is_json)
                self.assertEqual(set(response.get_json()), {"error"})
                self.assertTrue(response.get_json()["error"])
                self.assertNotIn(PRIVATE_MARKER, response.get_data(as_text=True))
                self.assert_private_no_store(response)

    def test_map_endpoints_are_read_only(self):
        for path in ("/reservas/mapa-dados", "/reservas/map-stay/simulacao-mapa"):
            with self.subTest(path=path):
                response = self.client.post(path, json=SEARCH)
                self.assertEqual(response.status_code, 405)
        self.mocks["calcular_preco"].assert_not_called()

    def test_initial_catalog_render_only_configures_map_and_does_not_fetch_markers(self):
        with patch("blueprints.booking_portal._render_booking_template", return_value="catalog") as render:
            response = self.client.get("/reservas", query_string=SEARCH)
        self.assertEqual(response.status_code, 200)
        self.mocks["get_map_catalog"].assert_not_called()
        self.mocks["calcular_preco"].assert_not_called()
        self.assertTrue(render.call_args.kwargs["catalog_map"])


if __name__ == "__main__":
    unittest.main()
