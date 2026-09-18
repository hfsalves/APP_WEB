"""Responsive navigation reuses real portal URLs without cookies or live services."""

from html.parser import HTMLParser
from pathlib import Path
import unittest
from urllib.parse import parse_qs, urlsplit

from flask import Flask, render_template

from blueprints.booking_portal import _language_links, _resolve_lang, _t, bp


ROOT = Path(__file__).resolve().parents[1]


class NavigationMarkup(HTMLParser):
    def __init__(self, markup):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.forms = []
        self.summaries = []
        self.details = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a":
            self.links.append(attrs)
        elif tag == "form":
            self.forms.append(attrs)
        elif tag == "summary":
            self.summaries.append(attrs)
        elif tag == "details":
            self.details.append(attrs)


class BookingPortalNavigationTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(
            __name__, template_folder=str(ROOT / "templates"),
            static_folder=str(ROOT / "static"),
        )
        self.app.config.update(TESTING=True, SECRET_KEY="navigation-tests-only")
        self.app.register_blueprint(bp)

    def test_shared_language_links_preserve_dates_party_search_page_and_property(self):
        filters = {
            "checkin": "2030-10-14", "checkout": "2030-10-17", "adultos": "2",
            "criancas": "1", "bebes": "1", "q": "Porto & Centro", "page": "3", "lang": "pt",
        }
        for path in ("/reservas", "/reservas/stay-one", "/reservas/stay-one/reservar"):
            with self.subTest(path=path), self.app.test_request_context(path, query_string=filters):
                html = render_template(
                    "booking_portal/_language_switcher.html", lang="pt", language_links=_language_links("pt"),
                )
                markup = NavigationMarkup(html)
                self.assertEqual(len(markup.links), 4)
                self.assertEqual([link["href"] for link in markup.links], [item["url"] for item in _language_links("pt")])
                for link in markup.links:
                    parsed = urlsplit(link["href"])
                    self.assertEqual(parsed.path, path)
                    expected = {key: [value] for key, value in filters.items()}
                    expected["lang"] = [link["hreflang"]]
                    self.assertEqual(parse_qs(parsed.query), expected)

    def test_current_flag_and_full_names_are_accessible_without_language_cookie(self):
        names = {"pt": "Português", "en": "English", "es": "Español", "fr": "Français"}
        for lang, name in names.items():
            with self.subTest(lang=lang), self.app.test_request_context("/reservas?lang=" + lang):
                self.assertEqual(_resolve_lang(), lang)
                html = render_template(
                    "booking_portal/_language_switcher.html", lang=lang, language_links=_language_links(lang),
                )
                markup = NavigationMarkup(html)
                self.assertEqual(len(markup.details), 1)
                self.assertNotIn("open", markup.details[0])
                self.assertTrue(markup.summaries[0]["aria-label"].endswith(": " + name))
                active = [link for link in markup.links if link.get("aria-current") == "true"]
                self.assertEqual([link["lang"] for link in active], [lang])
                for full_name in names.values():
                    self.assertIn(full_name, html)
                self.assertEqual(html.count('class="booking-language-flag"'), 5)
                self.assertNotIn("http://", html)
                self.assertNotIn("https://", html)

    def test_signed_out_account_keeps_login_url_accessible_label_and_icon(self):
        with self.app.test_request_context("/reservas?lang=fr"):
            html = render_template("booking_portal/_account_menu.html", portal_user=None, lang="fr", t=_t("fr"))
        markup = NavigationMarkup(html)
        self.assertEqual(len(markup.links), 1)
        self.assertEqual(markup.links[0]["href"], "/reservas/entrar?lang=fr")
        self.assertEqual(markup.links[0]["aria-label"], _t("fr")["login"])
        self.assertEqual(markup.links[0]["title"], _t("fr")["login"])
        self.assertNotIn("booking-account-desktop-label", html)
        self.assertIn('class="booking-account-mobile-icon"', html)
        self.assertEqual(markup.details, [])

    def test_signed_in_account_uses_existing_native_menu_and_post_logout(self):
        with self.app.test_request_context("/reservas?lang=pt"):
            html = render_template(
                "booking_portal/_account_menu.html", portal_user={"nome": "Ana Silva"}, lang="pt", t=_t("pt"),
            )
        markup = NavigationMarkup(html)
        self.assertEqual(len(markup.details), 1)
        self.assertIn("data-booking-navigation-menu", markup.details[0])
        self.assertNotIn("open", markup.details[0])
        self.assertIn("Ana Silva", markup.summaries[0]["aria-label"])
        self.assertEqual(markup.summaries[0]["title"], "Ana Silva")
        self.assertNotIn("booking-account-desktop-label", html)
        self.assertIn('class="booking-account-mobile-icon"', html)
        self.assertEqual(markup.forms, [{"method": "post", "action": "/reservas/sair?lang=pt"}])
        self.assertEqual(markup.links[0]["href"], "/reservas/minhas-reservas?lang=pt")

    def test_every_full_portal_template_uses_shared_language_control_and_assets(self):
        templates = [path for path in (ROOT / "templates/booking_portal").glob("*.html") if not path.name.startswith("_")]
        self.assertEqual(len(templates), 12)
        for path in templates:
            with self.subTest(template=path.name):
                source = path.read_text()
                self.assertEqual(source.count("include 'booking_portal/_language_switcher.html'"), 1)
                self.assertEqual(source.count("include 'booking_portal/_fonts.html'"), 1)
        with self.app.test_request_context("/reservas"):
            html = render_template("booking_portal/_fonts.html")
        self.assertEqual(html.count("booking_mobile_navigation.css"), 1)
        self.assertEqual(html.count("booking_mobile_navigation.js"), 1)
        self.assertIn("defer", html)

    def test_controls_are_global_and_only_header_layout_changes_at_breakpoints(self):
        css = (ROOT / "static/css/booking_mobile_navigation.css").read_text()
        shared, responsive = css.split("@media (max-width: 980px)", 1)
        self.assertIn("body .booking-mobile-language {", shared)
        self.assertIn("body .booking-account-mobile-icon {", shared)
        self.assertIn("width: 44px;", shared)
        self.assertIn("body .booking-mobile-language-dropdown {", shared)
        self.assertNotIn(".booking-topbar", shared)
        self.assertNotIn("grid-template-columns", shared)
        self.assertIn("grid-column: 1 / -1;", responsive)
        self.assertNotIn("width: min(220px, 100%);", responsive)
        self.assertIn("width: min(160px, 100%);", responsive)
        self.assertEqual(responsive.count("width: min(160px, 100%);"), 1)
        with self.app.test_request_context("/reservas"):
            html = render_template(
                "booking_portal/_language_switcher.html", lang="pt", language_links=_language_links("pt"),
                language_switcher_nav=True,
            )
        self.assertNotIn("booking-language-desktop", html)
        self.assertEqual(html.count('class="booking-mobile-language"'), 1)
        for label in ("PT", "EN", "ES", "FR"):
            self.assertNotIn(">" + label + "</a>", html)

    def test_tablet_and_phone_share_the_same_compact_logo_source(self):
        source = (ROOT / "templates/booking_portal/index.html").read_text()
        self.assertIn('<source media="(max-width: 980px)"', source)
        self.assertIn("images/booking_portal/portobreak-logo-simple.png", source)
        self.assertNotIn('<source media="(max-width: 768px)"', source)

    def test_menu_keyboard_and_outside_click_behavior_is_not_viewport_gated(self):
        js = (ROOT / "static/js/booking_mobile_navigation.js").read_text()
        self.assertNotIn("matchMedia", js)
        self.assertNotIn("mobile.matches", js)
        self.assertIn('addEventListener("click"', js)
        self.assertIn('addEventListener("keydown"', js)
        self.assertIn('event.key !== "Escape"', js)
        self.assertIn("other.open = false", js)


if __name__ == "__main__":
    unittest.main()
