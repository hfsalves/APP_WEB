"""Catalog presentation checks without a live database or booking writes."""

import copy
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from flask import Flask

from blueprints.booking_portal import _pagination_context, _t, bp


ROOT = Path(__file__).resolve().parents[1]
PROPERTY = {
    "id": "stay-one",
    "nome": "Estúdio do Porto",
    "descricao": "Um estúdio confortável.",
    "descricao_curta": "Um estúdio confortável.",
    "localizacao": "Porto",
    "capacidade": 2,
    "lot_adultos": 2,
    "lot_criancas": 0,
    "licenca": "HIDDEN-REGISTRATION-123456/AL",
    "tipologia": "T0",
    "foto_principal": "/static/stay.jpg",
    "fotos": [{"url": "/static/stay.jpg", "alt": "Estúdio"}],
    "tem_mapa": False,
    "preco_desde": "99 €",
    "airbnb_room_id": "21329922",
}
SEARCH_PRICE = {
    "nights": 2,
    "airbnb": Decimal("96.00"),
    "portobreak": Decimal("92.00"),
    "saving": Decimal("4.00"),
    "airbnb_label": "96.00 EUR",
    "portobreak_label": "92.00 EUR",
    "airbnb_total": Decimal("132.00"),
    "portobreak_total": Decimal("128.00"),
    "airbnb_total_label": "132.00 EUR",
    "portobreak_total_label": "128.00 EUR",
    "saving_label": "4.00 EUR",
    "airbnb_url": "https://www.airbnb.pt/rooms/21329922?adults=2&check_in=2030-10-14&check_out=2030-10-16",
}


class VisibleBodyText(HTMLParser):
    def __init__(self, markup):
        super().__init__(convert_charrefs=True)
        self.in_body = False
        self.hidden_depth = 0
        self.parts = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        if tag == "body":
            self.in_body = True
        elif tag in {"script", "style"}:
            self.hidden_depth += 1

    def handle_endtag(self, tag):
        if tag == "body":
            self.in_body = False
        elif tag in {"script", "style"}:
            self.hidden_depth -= 1

    def handle_data(self, data):
        if self.in_body and not self.hidden_depth:
            self.parts.append(data)


class PaginationMarkup(HTMLParser):
    def __init__(self, markup):
        super().__init__(convert_charrefs=True)
        self.items = []
        self.current = None
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set(attrs.get("class", "").split())
        if tag in {"a", "span"} and classes.intersection({"booking-page-link", "booking-page-number"}):
            self.current = {"tag": tag, "attrs": attrs, "classes": classes, "text": ""}
            self.items.append(self.current)

    def handle_data(self, data):
        if self.current:
            self.current["text"] += data

    def handle_endtag(self, tag):
        if self.current and tag == self.current["tag"]:
            self.current = None


class BookingPortalCatalogUiTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(
            __name__,
            template_folder=str(ROOT / "templates"),
            static_folder=str(ROOT / "static"),
        )
        self.app.config.update(TESTING=True, SECRET_KEY="catalog-ui-tests-only")
        self.app.register_blueprint(bp)
        self.client = self.app.test_client()
        fixtures = {
            "_portal_current_user": {"return_value": None},
            "get_alojamento": {"side_effect": lambda *_a, **_k: copy.deepcopy(PROPERTY)},
            "get_alojamentos_disponiveis_page": {"side_effect": self.catalog},
            "get_calendario_ocupacao": {"return_value": {
                "occupied": [], "blocked_checkin": [], "blocked_checkout": [], "min_nights": 1,
            }},
            "alojamento_disponivel": {"return_value": True},
            "alojamento_datas_permitidas": {"return_value": {"allowed": True, "errors": []}},
            "calcular_preco": {"return_value": {
                "valor": None, "label": "Preço sob consulta", "noites": 0, "linhas": [],
            }},
        }
        for name, options in fixtures.items():
            patcher = patch("blueprints.booking_portal." + name, **options)
            patcher.start()
            self.addCleanup(patcher.stop)

    def catalog(self, **kwargs):
        page = max(1, min(int(kwargs.get("page") or 1), 6))
        item = copy.deepcopy(PROPERTY)
        if kwargs.get("checkin") and kwargs.get("checkout"):
            item["preco_estadia"] = copy.deepcopy(SEARCH_PRICE)
        return {
            "items": [item], "total": 100, "page": page,
            "pages": 6, "per_page": 18, "has_prev": page > 1, "has_next": page < 6,
        }

    def test_dated_catalog_shows_real_stay_comparison_instead_of_from_price(self):
        response = self.client.get("/reservas", query_string={
            "lang": "pt", "checkin": "2030-10-14", "checkout": "2030-10-16",
        })
        self.assertEqual(response.status_code, 200)
        markup = response.get_data(as_text=True)
        self.assertIn('class="booking-card-price-reference"', markup)
        self.assertIn("Preço Airbnb", markup)
        self.assertIn('class="booking-airbnb-badge"', markup)
        self.assertIn('href="https://www.airbnb.pt/rooms/21329922?adults=2&amp;check_in=2030-10-14&amp;check_out=2030-10-16"', markup)
        self.assertIn('<span class="booking-airbnb-price">132.00 EUR</span>', markup)
        self.assertNotIn("<del>132.00 EUR</del>", markup)
        self.assertIn("Reserva direta", markup)
        self.assertIn("128.00 EUR", markup)
        self.assertIn("Poupa 4.00 EUR", markup)
        self.assertIn("2 noites", markup)
        self.assertNotIn("<small>desde</small>", markup)

    def test_undated_catalog_keeps_from_price_without_total_saving(self):
        response = self.client.get("/reservas", query_string={"lang": "pt"})
        self.assertEqual(response.status_code, 200)
        markup = response.get_data(as_text=True)
        self.assertIn("<small>desde</small>", markup)
        self.assertIn("<strong>99 €</strong>", markup)
        self.assertNotIn('class="booking-card-price-reference"', markup)
        self.assertNotIn('class="booking-price-saving"', markup)

    def test_commercial_price_copy_exists_in_every_portal_language(self):
        expected = {
            "pt": ("Preço Airbnb", "Reserva direta", "Poupa 4.00 EUR"),
            "en": ("Airbnb price", "Direct booking", "You save 4.00 EUR"),
            "es": ("Precio en Airbnb", "Reserva directa", "Ahorras 4.00 EUR"),
            "fr": ("Prix Airbnb", "Réservation directe", "Vous économisez 4.00 EUR"),
        }
        for lang, labels in expected.items():
            with self.subTest(lang=lang):
                response = self.client.get("/reservas", query_string={
                    "lang": lang, "checkin": "2030-10-14", "checkout": "2030-10-16",
                })
                markup = response.get_data(as_text=True)
                for label in labels:
                    self.assertIn(label, markup)

    def test_every_page_is_shown_from_first_middle_and_last_page(self):
        for pages, page in ((6, 1), (6, 3), (6, 6), (1, 1), (12, 6)):
            with self.subTest(pages=pages, page=page), self.app.test_request_context("/reservas"):
                pagination = _pagination_context({"page": page, "pages": pages}, "pt")
                links = pagination["page_links"]
                self.assertEqual([item["page"] for item in links], list(range(1, pages + 1)))
                self.assertEqual([item["page"] for item in links if item["active"]], [page])
                self.assertEqual(bool(pagination["prev_url"]), page > 1)
                self.assertEqual(bool(pagination["next_url"]), page < pages)

    def test_all_pagination_links_preserve_search_filters_and_language(self):
        filters = {
            "checkin": "2030-10-14", "checkout": "2030-10-16", "adultos": "2",
            "criancas": "1", "bebes": "1", "hospedes": "3", "q": "Porto & Centro",
            "lang": "fr", "page": "3",
        }
        with self.app.test_request_context("/reservas", query_string=filters):
            pagination = _pagination_context({"page": 3, "pages": 6}, "fr")
        for page, url in [
            *((item["page"], item["url"]) for item in pagination["page_links"]),
            (2, pagination["prev_url"]), (4, pagination["next_url"]),
        ]:
            with self.subTest(page=page):
                parsed = urlsplit(url)
                self.assertEqual(parsed.path, "/reservas")
                expected = {key: [value] for key, value in filters.items()}
                expected["page"] = [str(page)]
                self.assertEqual(parse_qs(parsed.query), expected)

    def test_registration_is_not_visible_in_catalog_detail_or_reservation(self):
        for lang in ("pt", "en", "es", "fr"):
            for path in ("/reservas", "/reservas/stay-one", "/reservas/stay-one/reservar"):
                with self.subTest(lang=lang, path=path):
                    response = self.client.get(path, query_string={"lang": lang})
                    self.assertEqual(response.status_code, 200)
                    markup = response.get_data(as_text=True)
                    visible = "".join(VisibleBodyText(markup).parts)
                    self.assertIn(PROPERTY["nome"], visible)
                    self.assertNotIn(PROPERTY["licenca"], visible)
                    self.assertNotIn('class="booking-license"', markup)

    def test_rendered_catalog_includes_the_sixth_page(self):
        response = self.client.get("/reservas?lang=pt")
        self.assertEqual(response.status_code, 200)
        markup = response.get_data(as_text=True)
        self.assertIn('href="/reservas?lang=pt&amp;page=6">6</a>', markup)
        self.assertEqual(markup.count('class="booking-page-number'), 7)  # wrapper plus six pages

    def test_pagination_arrows_keep_localized_labels_disabled_semantics_and_filtered_urls(self):
        for lang in ("pt", "en", "es", "fr"):
            for page in (1, 5, 6):
                with self.subTest(lang=lang, page=page):
                    query = {
                        "lang": lang, "page": str(page), "checkin": "2030-10-14", "checkout": "2030-10-18",
                        "adultos": "2", "criancas": "1", "bebes": "1", "hospedes": "3", "q": "Porto & Centro",
                    }
                    response = self.client.get("/reservas", query_string=query)
                    self.assertEqual(response.status_code, 200)
                    pagination = PaginationMarkup(response.get_data(as_text=True))
                    numbers = [item for item in pagination.items if "booking-page-number" in item["classes"]]
                    self.assertEqual([item["text"].strip() for item in numbers], [str(number) for number in range(1, 7)])
                    active = [item for item in numbers if item["attrs"].get("aria-current") == "page"]
                    self.assertEqual([item["text"].strip() for item in active], [str(page)])

                    for direction, key, destination, enabled in (
                        ("prev", "previous", page - 1, page > 1), ("next", "next", page + 1, page < 6),
                    ):
                        controls = [item for item in pagination.items if "booking-page-" + direction in item["classes"]]
                        self.assertEqual(len(controls), 1)
                        control = controls[0]
                        label = _t(lang)[key]
                        self.assertEqual(control["attrs"].get("aria-label"), label)
                        self.assertEqual(control["text"].strip(), label)  # retained for the desktop label
                        if not enabled:
                            self.assertEqual(control["tag"], "span")
                            self.assertEqual(control["attrs"].get("aria-disabled"), "true")
                            self.assertNotIn("href", control["attrs"])
                            self.assertIn("is-disabled", control["classes"])
                        else:
                            self.assertEqual(control["tag"], "a")
                            self.assertNotEqual(control["attrs"].get("aria-disabled"), "true")
                            parsed = urlsplit(control["attrs"]["href"])
                            self.assertEqual(parsed.path, "/reservas")
                            expected = {name: [value] for name, value in query.items()}
                            expected["page"] = [str(destination)]
                            self.assertEqual(parse_qs(parsed.query), expected)

    def test_arrow_only_pagination_presentation_is_limited_to_mobile(self):
        css = (ROOT / "static/css/booking_portal.css").read_text()
        desktop, mobile = css.split("@media (max-width: 720px)", 1)
        selector = ".booking-pagination .booking-page-link::before"
        self.assertNotIn(selector, desktop)
        self.assertIn(selector, mobile)
        rule = re.search(r"\.booking-pagination \.booking-page-link\s*\{([^}]+)\}", mobile)
        self.assertIsNotNone(rule)
        self.assertIn("font-size: 0;", rule.group(1))
        icon = re.search(r"\.booking-pagination \.booking-page-link::before\s*\{([^}]+)\}", mobile)
        self.assertIsNotNone(icon)
        self.assertIn("data:image/svg+xml", icon.group(1))
        self.assertIn('.booking-pagination .booking-page-next::before { transform: rotate(180deg); }', mobile)


if __name__ == "__main__":
    unittest.main()
