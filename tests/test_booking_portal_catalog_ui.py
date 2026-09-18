"""Catalog presentation checks without a live database or booking writes."""

import copy
from html.parser import HTMLParser
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from flask import Flask

from blueprints.booking_portal import _pagination_context, bp


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
        return {
            "items": [copy.deepcopy(PROPERTY)], "total": 100, "page": page,
            "pages": 6, "per_page": 18, "has_prev": page > 1, "has_next": page < 6,
        }

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


if __name__ == "__main__":
    unittest.main()
