"""Public discovery never indexes checkout, guest links or personal parameters.

The real blueprint and templates run in a lightweight Flask app. Every catalog
lookup is a fixture; no app bootstrap, live database, email or payment is used.
"""

import copy
import json
from html.parser import HTMLParser
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, unquote, urlsplit
from xml.etree import ElementTree

from flask import Flask
from sqlalchemy.exc import SQLAlchemyError

from blueprints.booking_portal import bp
from services.booking_portal_seo import (
    PUBLIC_ENDPOINTS,
    build_booking_seo,
    is_public_origin,
    public_base_url,
    public_url,
)
from services.booking_portal_service import get_public_alojamento_ids


ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = {"pt", "en", "es", "fr"}
PUBLIC_ORIGIN = "https://portobreak.com"
PROPERTY = {
    "id": "stay-one",
    "nome": "Estúdio & Jardim",
    "descricao": "Um estúdio confortável para descobrir o Porto.",
    "descricao_curta": "Um estúdio confortável para descobrir o Porto.",
    "localizacao": "Porto, Centro",
    "capacidade": 4,
    "lot_adultos": 4,
    "lot_criancas": 0,
    "licenca": "123456/AL",
    "tipologia": "T1",
    "foto_principal": "https://szeroapp.com/static/stay.jpg",
    "fotos": [{"url": "https://szeroapp.com/static/stay.jpg", "alt": "Estúdio"}],
    "tem_mapa": False,
    "morada": "PRIVATE STREET ADDRESS 17",
    "codpost": "PRIVATE POSTCODE",
    "lat": 41.123456789,
    "lon": -8.123456789,
    "token": "PRIVATE-GUEST-TOKEN",
    "preco_desde": "99 €",
}


class PageHead(HTMLParser):
    """Inspect rendered markup, including JSON-LD script-boundary escaping."""

    def __init__(self, markup):
        super().__init__(convert_charrefs=True)
        self.in_head = False
        self.in_title = False
        self.active_json = None
        self.title = ""
        self.meta = {}
        self.links = []
        self.json_scripts = []
        self.script_attributes = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "head":
            self.in_head = True
        if not self.in_head:
            return
        if tag == "title":
            self.in_title = True
        elif tag == "meta":
            self.meta[attrs.get("name") or attrs.get("property")] = attrs.get("content")
        elif tag == "link":
            self.links.append(attrs)
        elif tag == "script":
            self.script_attributes.append(attrs)
            if attrs.get("type") == "application/ld+json":
                self.active_json = ""

    def handle_data(self, value):
        if self.in_title:
            self.title += value
        if self.active_json is not None:
            self.active_json += value

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        elif tag == "script" and self.active_json is not None:
            self.json_scripts.append(self.active_json)
            self.active_json = None
        elif tag == "head":
            self.in_head = False

    @property
    def canonical(self):
        matches = [item["href"] for item in self.links if item.get("rel") == "canonical"]
        return matches[0] if len(matches) == 1 else None

    @property
    def alternates(self):
        return {
            item["hreflang"]: item["href"]
            for item in self.links
            if item.get("rel") == "alternate" and item.get("hreflang")
        }


class BookingPortalSeoTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(
            __name__,
            template_folder=str(ROOT / "templates"),
            static_folder=str(ROOT / "static"),
        )
        self.app.config.update(
            TESTING=True,
            SECRET_KEY="seo-tests-only",
            PORTOBREAK_PUBLIC_BASE_URL=PUBLIC_ORIGIN,
        )
        self.app.register_blueprint(bp)
        self.client = self.app.test_client()
        self.property = copy.deepcopy(PROPERTY)

        fixtures = {
            "_portal_current_user": {"return_value": None},
            "get_public_amenity_filters": {"return_value": []},
            "get_alojamento": {"side_effect": lambda *_args, **_kwargs: copy.deepcopy(self.property)},
            "get_alojamentos_disponiveis_page": {"side_effect": self.catalog},
            "get_calendario_ocupacao": {"return_value": {
                "occupied": [], "blocked_checkin": [], "blocked_checkout": [], "min_nights": 1,
            }},
            "alojamento_disponivel": {"return_value": True},
            "alojamento_datas_permitidas": {"return_value": {"allowed": True, "errors": []}},
            "calcular_preco": {"return_value": {"valor": None, "label": "Preco sob consulta", "noites": 0, "linhas": []}},
            "get_public_alojamento_ids": {"return_value": ["stay-one", "A&B", "stay-one", ""]},
            "confirmar_email_portal": {"return_value": "invalid"},
            "verificar_assinatura_webhook_stripe_portal": {"return_value": False},
        }
        for name, options in fixtures.items():
            patcher = patch("blueprints.booking_portal." + name, **options)
            patcher.start()
            self.addCleanup(patcher.stop)

    def catalog(self, **kwargs):
        page = max(1, min(int(kwargs.get("page") or 1), 3))
        return {
            "items": [copy.deepcopy(self.property)], "total": 40, "page": page,
            "pages": 3, "per_page": 18, "has_prev": page > 1, "has_next": page < 3,
            "prev_page": page - 1 if page > 1 else None,
            "next_page": page + 1 if page < 3 else None,
        }

    def get(self, path, **kwargs):
        kwargs.setdefault("base_url", PUBLIC_ORIGIN)
        return self.client.get(path, **kwargs)

    def head(self, path, **kwargs):
        response = self.get(path, **kwargs)
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True)[:300])
        return PageHead(response.get_data(as_text=True))

    def assert_robots(self, value, *, follow):
        directives = {part.strip() for part in value.split(",")}
        self.assertIn("noindex", directives)
        self.assertIn("follow" if follow else "nofollow", directives)

    def test_public_catalog_has_localized_metadata_and_reciprocal_languages(self):
        titles = set()
        for lang in LANGUAGES:
            with self.subTest(lang=lang):
                head = self.head("/reservas?lang=" + lang)
                titles.add(head.title)
                self.assertTrue(head.meta["description"])
                self.assertNotIn("noindex", head.meta["robots"])
                self.assertEqual(head.canonical, PUBLIC_ORIGIN + "/reservas?lang=" + lang)
                self.assertEqual(head.meta["og:url"], head.canonical)
                self.assertEqual(head.meta["og:title"], head.title)
                self.assertTrue(head.meta["og:image"].startswith("https://"))
                self.assertEqual(set(head.alternates), LANGUAGES | {"x-default"})
                for alternate_lang in LANGUAGES:
                    self.assertEqual(head.alternates[alternate_lang], PUBLIC_ORIGIN + "/reservas?lang=" + alternate_lang)
                self.assertEqual(head.alternates["x-default"], head.alternates["pt"])
        self.assertEqual(len(titles), 4)

    def test_public_legal_pages_have_clean_canonicals_in_every_language(self):
        paths = (
            "politica-cancelamento", "termos-condicoes", "politica-privacidade",
            "politica-cookies", "informacao-legal",
        )
        for path in paths:
            for lang in LANGUAGES:
                with self.subTest(path=path, lang=lang):
                    head = self.head(f"/reservas/{path}?lang={lang}&checkin=2030-10-14&return_to=/reservas/stay-one/reservar&token=DO-NOT-PUBLISH")
                    self.assertEqual(head.canonical, f"{PUBLIC_ORIGIN}/reservas/{path}?lang={lang}")
                    self.assertEqual(set(head.alternates), LANGUAGES | {"x-default"})
                    self.assertNotIn("DO-NOT-PUBLISH", json.dumps(head.meta))
                    self.assertNotIn("noindex", head.meta["robots"])

    def test_pagination_keeps_each_catalog_page_canonical(self):
        head = self.head("/reservas?lang=en&page=2&utm_source=test")
        parsed = urlsplit(head.canonical)
        self.assertEqual(parsed.path, "/reservas")
        self.assertEqual(parse_qs(parsed.query), {"lang": ["en"], "page": ["2"]})
        for url in head.alternates.values():
            self.assertEqual(parse_qs(urlsplit(url).query)["page"], ["2"])
        self.assertNotIn("noindex", head.meta["robots"])

    def test_filtered_catalog_is_not_indexed_or_canonicalized_with_filters(self):
        for key, value in (
            ("q", "test"), ("query", "test"), ("checkin", "2030-10-14"),
            ("checkout", "2030-10-16"), ("adultos", "2"), ("criancas", "1"),
            ("bebes", "1"), ("hospedes", "2"),
        ):
            with self.subTest(key=key):
                head = self.head(f"/reservas?lang=pt&page=2&{key}={value}")
                self.assert_robots(head.meta["robots"], follow=True)
                self.assertEqual(head.canonical, PUBLIC_ORIGIN + "/reservas?lang=pt")

    def test_detail_canonical_removes_dates_guests_tracking_and_tokens(self):
        head = self.head("/reservas/stay-one?lang=fr&checkin=2030-10-14&checkout=2030-10-16&adultos=2&session_id=DO-NOT-PUBLISH&utm_source=test")
        self.assertEqual(head.canonical, PUBLIC_ORIGIN + "/reservas/stay-one?lang=fr")
        self.assertNotIn("noindex", head.meta["robots"])
        self.assertIn(self.property["nome"], head.title)
        self.assertNotIn("DO-NOT-PUBLISH", json.dumps(head.meta))
        self.assertNotIn("2030-10-14", "".join(head.json_scripts))

    def test_detail_title_does_not_repeat_brand_already_in_property_name(self):
        self.property["nome"] = "Porto Prime Studios - C - by PortoBreak"
        head = self.head("/reservas/stay-one?lang=pt")
        self.assertEqual(head.title, self.property["nome"])

    def test_legacy_alias_uses_current_canonical_routes(self):
        for path, canonical in (
            ("/portal-reservas", "/reservas"),
            ("/portal-reservas/alojamento/stay-one", "/reservas/stay-one"),
            ("/portal-reservas/politica-cancelamento", "/reservas/politica-cancelamento"),
        ):
            with self.subTest(path=path):
                head = self.head(path + "?lang=es")
                self.assertEqual(head.canonical, PUBLIC_ORIGIN + canonical + "?lang=es")

    def test_local_and_unknown_hosts_never_index_public_pages(self):
        for origin in ("http://127.0.0.1:8001", "http://localhost", "https://preview.example"):
            with self.subTest(origin=origin):
                head = self.head("/reservas?lang=pt", base_url=origin)
                self.assert_robots(head.meta["robots"], follow=True)
                self.assertEqual(head.canonical, PUBLIC_ORIGIN + "/reservas?lang=pt")

    def test_proxy_host_detection_matches_only_configured_public_domain(self):
        for host, expected in (
            ("portobreak.com", True), ("www.portobreak.com", True),
            ("portobreak.com, internal-proxy", True),
            ("portobreak.com.attacker.example", False), ("localhost", False),
            ("attacker@portobreak.com", False), ("portobreak.com/unexpected", False),
        ):
            with self.subTest(host=host), self.app.test_request_context(
                "/reservas", base_url="http://127.0.0.1:8001", headers={"X-Forwarded-Host": host}
            ):
                self.assertIs(is_public_origin(), expected)
                self.assertEqual(public_url("booking_portal.index", lang="pt"), PUBLIC_ORIGIN + "/reservas?lang=pt")

    def test_private_html_has_no_public_metadata_or_structured_data(self):
        for path in (
            "/reservas/entrar", "/reservas/recuperar-password",
            "/reservas/redefinir-password/SECRET-RESET-TOKEN",
            "/reservas/stay-one/reservar", "/reservas/validar-email/SECRET-EMAIL-TOKEN",
        ):
            with self.subTest(path=path):
                head = self.head(path + "?lang=pt&token=DO-NOT-PUBLISH")
                self.assert_robots(head.meta["robots"], follow=False)
                self.assertIsNone(head.canonical)
                self.assertEqual(head.alternates, {})
                self.assertEqual(head.json_scripts, [])
                self.assertFalse(any(str(key).startswith(("og:", "twitter:")) for key in head.meta))

    def test_private_redirects_errors_and_json_are_also_noindex(self):
        paths = {
            "/reservas/minhas-reservas": 302,
            "/reservas/portal/SECRET-INVALID-TOKEN": 404,
            "/reservas/pagamento/resultado?session_id=PRIVATE-CHECKOUT": 404,
            "/reservas/preferencias-cookies": 200,
            "/reservas/stay-one/ocupacao": 200,
            "/reservas/stay-one/ocupacao?start=invalid": 400,
        }
        for path, status in paths.items():
            with self.subTest(path=path):
                response = self.get(path)
                self.assertEqual(response.status_code, status)
                self.assert_robots(response.headers.get("X-Robots-Tag", ""), follow=False)

    def test_private_post_failures_cannot_be_indexed(self):
        for path, status in (
            ("/reservas/preferencias-cookies", 403),
            ("/reservas/stripe/webhook", 400),
        ):
            with self.subTest(path=path):
                response = self.client.post(path, base_url=PUBLIC_ORIGIN, json={})
                self.assertEqual(response.status_code, status)
                self.assert_robots(response.headers.get("X-Robots-Tag", ""), follow=False)

    def test_missing_public_property_is_noindex(self):
        with patch("blueprints.booking_portal.get_alojamento", return_value=None):
            response = self.get("/reservas/missing?lang=pt")
        self.assertEqual(response.status_code, 404)
        self.assert_robots(response.headers.get("X-Robots-Tag", ""), follow=False)

    def test_jsonld_excludes_property_address_coordinates_price_and_private_fields(self):
        head = self.head("/reservas/stay-one?lang=pt")
        self.assertTrue(head.json_scripts)
        raw = "".join(head.json_scripts)
        for script in head.json_scripts:
            self.assertIsNotNone(json.loads(script))
        for value in ("PRIVATE STREET", "PRIVATE POSTCODE", "PRIVATE-GUEST-TOKEN", "41.123456789", "-8.123456789"):
            self.assertNotIn(value, raw)
        for field in ('"geo"', '"streetAddress"', '"offers"', '"price"', '"aggregateRating"'):
            self.assertNotIn(field, raw)

    def test_metadata_and_jsonld_escape_untrusted_property_text(self):
        self.property["nome"] = 'Estúdio "Azul" </script><script id="injected">alert(1)</script> & Jardim'
        self.property["descricao"] = 'Descrição "especial" </script><img src=x onerror=alert(1)>'
        head = self.head("/reservas/stay-one?lang=pt")
        self.assertFalse(any(item.get("id") == "injected" for item in head.script_attributes))
        self.assertTrue(head.json_scripts)
        for script in head.json_scripts:
            json.loads(script)
            self.assertNotIn("</script>", script.lower())
        self.assertIsNotNone(head.canonical)
        self.assertTrue(head.meta["description"])

    def test_metadata_does_not_publish_signed_or_untrusted_image_urls(self):
        for image in (
            "https://szeroapp.com/static/stay.jpg?token=PRIVATE-IMAGE-TOKEN",
            "https://attacker.example/track.jpg",
            "javascript:alert(1)", "https://user:password@szeroapp.com/private.jpg",
        ):
            with self.subTest(image=image):
                self.property["foto_principal"] = image
                head = self.head("/reservas/stay-one?lang=pt")
                self.assertTrue(head.meta["og:image"].startswith(PUBLIC_ORIGIN + "/static/"))
                self.assertNotIn("PRIVATE-IMAGE-TOKEN", json.dumps(head.meta) + "".join(head.json_scripts))

    def test_sitemap_is_valid_deduplicated_xml_with_four_languages(self):
        response = self.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        self.assertIn("xml", response.mimetype)
        root = ElementTree.fromstring(response.data)
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        nodes = root.findall("s:url", ns)
        locations = [node.findtext("s:loc", namespaces=ns) for node in nodes]
        self.assertEqual(len(locations), len(set(locations)))
        self.assertEqual(len(locations), (6 + 2) * 4)
        self.assertTrue(any("A&B" in unquote(url) for url in locations))
        for location in locations:
            self.assertTrue(location.startswith(PUBLIC_ORIGIN + "/reservas"))
            self.assertEqual(set(parse_qs(urlsplit(location).query)), {"lang"})
            self.assertIn(parse_qs(urlsplit(location).query)["lang"][0], LANGUAGES)
        for private_path in ("/portal/", "/reservar", "/pagamento", "/minhas-reservas", "/entrar", "/preferencias-cookies"):
            self.assertFalse(any(private_path in location for location in locations))

    def test_sitemap_escapes_xml_metacharacters(self):
        self.app.config["PORTOBREAK_PUBLIC_BASE_URL"] = PUBLIC_ORIGIN + "/portal&site"
        response = self.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"portal&amp;site", response.data)
        root = ElementTree.fromstring(response.data)
        for node in root:
            self.assertTrue(node[0].text.startswith(PUBLIC_ORIGIN + "/portal&site/reservas"))

    def test_sitemap_database_failure_is_retryable_not_an_empty_success(self):
        with patch("blueprints.booking_portal.get_public_alojamento_ids", side_effect=SQLAlchemyError("offline")), self.assertLogs(self.app.logger, level="ERROR"):
            response = self.get("/sitemap.xml")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.headers["Retry-After"], "300")
        self.assertIn("no-store", response.headers["Cache-Control"])
        self.assertNotIn(b"<urlset", response.data)

    def test_sitemap_inventory_selects_only_active_named_public_identifiers(self):
        with patch("services.booking_portal_service.db") as fake_db:
            fake_db.session.execute.return_value.scalars.return_value.all.return_value = [" first ", "", None, "second"]
            identifiers = get_public_alojamento_ids()
        self.assertEqual(identifiers, ["first", "second"])
        sql = " ".join(str(fake_db.session.execute.call_args.args[0]).split()).upper()
        self.assertIn("SELECT DISTINCT LTRIM(RTRIM(AL.ALSTAMP)) AS ID", sql)
        self.assertIn("ISNULL(AL.INATIVO, 0) = 0", sql)
        self.assertIn("ISNULL(AL.FECHADO, 0) = 0", sql)
        self.assertIn("LTRIM(RTRIM(ISNULL(AL.NOME, ''))) <> ''", sql)
        for private_field in ("MORADA", "DESCRICAO", "CLIENTE", "TELEFONE", "EMAIL"):
            self.assertNotIn(private_field, sql)

    def test_robots_publishes_sitemap_only_on_public_origin(self):
        public = self.get("/robots.txt")
        self.assertEqual(public.status_code, 200)
        self.assertEqual(public.mimetype, "text/plain")
        self.assertIn("Sitemap: " + PUBLIC_ORIGIN + "/sitemap.xml", public.get_data(as_text=True))
        for origin in ("http://localhost", "http://127.0.0.1:8001", "https://preview.example"):
            with self.subTest(origin=origin):
                response = self.get("/robots.txt", base_url=origin)
                self.assertEqual(response.status_code, 200)
                self.assertIn("Disallow: /", response.get_data(as_text=True))
                self.assertNotIn("Sitemap:", response.get_data(as_text=True))

    def test_public_urls_are_built_from_configuration_not_request_host(self):
        with self.app.test_request_context("/reservas?lang=en", base_url="https://attacker.example"):
            self.assertEqual(public_base_url(), PUBLIC_ORIGIN)
            self.assertFalse(is_public_origin())
            self.assertEqual(public_url("booking_portal.index", lang="en"), PUBLIC_ORIGIN + "/reservas?lang=en")
            self.assertIn("booking_portal.index", PUBLIC_ENDPOINTS)
            self.assertNotIn("booking_portal.reserve", PUBLIC_ENDPOINTS)
            metadata = build_booking_seo("en", {"pagination": {"page": 1}, "search": {"has_search": False}})
            self.assert_robots(metadata["robots"], follow=True)
            self.assertEqual(metadata["canonical"], PUBLIC_ORIGIN + "/reservas?lang=en")

    def test_invalid_public_base_configuration_falls_back_to_known_origin(self):
        for value in (
            "https://user:password@portobreak.com", "https://portobreak.com?token=PRIVATE",
            "https://portobreak.com#fragment", "javascript:alert(1)",
            "https://portobreak.com:invalid", "https://portobreak.com/../private",
        ):
            with self.subTest(value=value), self.app.test_request_context("/reservas"):
                self.app.config["PORTOBREAK_PUBLIC_BASE_URL"] = value
                self.assertEqual(public_base_url(), PUBLIC_ORIGIN)

    def test_public_url_whitelists_route_parameters_and_preserves_configured_prefix(self):
        self.app.config["PORTOBREAK_PUBLIC_BASE_URL"] = PUBLIC_ORIGIN + "/portal/"
        with self.app.test_request_context("/reservas?token=PRIVATE"):
            url = public_url(
                "booking_portal.detail", lang="es", al_id="A&B / suite",
                checkin="2030-10-14", session_id="PRIVATE", token="PRIVATE", return_to="/private",
            )
            self.assertTrue(url.startswith(PUBLIC_ORIGIN + "/portal/reservas/"))
            self.assertIn("A%26B%20%2F%20suite", url)
            self.assertEqual(parse_qs(urlsplit(url).query), {"lang": ["es"]})
            self.assertNotIn("PRIVATE", url)

    def test_helper_private_context_does_not_leak_tokens_to_metadata(self):
        with self.app.test_request_context("/reservas/redefinir-password/SECRET?lang=pt&email=private@example.com", base_url=PUBLIC_ORIGIN):
            metadata = build_booking_seo("pt", {"page_title": "Definir password"})
            self.assert_robots(metadata["robots"], follow=False)
            self.assertFalse(metadata["canonical"])
            self.assertFalse(metadata["alternates"])
            self.assertFalse(metadata["jsonld"])
            self.assertNotIn("SECRET", json.dumps(metadata))
            self.assertNotIn("private@example.com", json.dumps(metadata))


if __name__ == "__main__":
    unittest.main()
