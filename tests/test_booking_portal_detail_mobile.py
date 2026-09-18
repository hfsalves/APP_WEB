"""Detail editors preserve one GET form, availability rules and a no-JS fallback."""

import copy
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from flask import Flask

from blueprints.booking_portal import bp


ROOT = Path(__file__).resolve().parents[1]
PROPERTY = {
    "id": "mobile-detail-stay", "nome": "Apartamento do Porto",
    "descricao": "Apartamento para toda a família.", "descricao_curta": "Apartamento no Porto.",
    "localizacao": "Porto", "capacidade": 6, "lot_adultos": 4,
    "lot_criancas": 2, "berco": True, "tipologia": "T2", "licenca": "123/AL",
    "foto_principal": "/static/stay.jpg", "fotos": [], "tem_mapa": False,
    "preco_desde": "100 EUR",
}
SELECTION = {
    "checkin": "2030-10-06", "checkout": "2030-10-09",
    "adultos": "4", "criancas": "2", "bebes": "1",
}


class DetailMarkup(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, markup):
        super().__init__(convert_charrefs=True)
        self.nodes = []
        self.stack = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        node = {"tag": tag, "attrs": dict(attrs), "ancestors": tuple(self.stack)}
        self.nodes.append(node)
        if tag not in self.VOID:
            self.stack.append(len(self.nodes) - 1)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.nodes[self.stack[index]]["tag"] == tag:
                self.stack = self.stack[:index]
                return

    def matching(self, attribute, value=None):
        return [node for node in self.nodes if attribute in node["attrs"]
                and (value is None or node["attrs"][attribute] == value)]

    def descendants(self, node):
        index = self.nodes.index(node)
        return [candidate for candidate in self.nodes if index in candidate["ancestors"]]


class BookingPortalDetailMobileTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__, template_folder=str(ROOT / "templates"), static_folder=str(ROOT / "static"))
        self.app.config.update(TESTING=True, SECRET_KEY="detail-mobile-tests-only")
        self.app.register_blueprint(bp)
        self.client = self.app.test_client()
        fixtures = {
            "_portal_current_user": {"return_value": None},
            "get_alojamento": {"side_effect": lambda *_a, **_k: copy.deepcopy(PROPERTY)},
            "get_calendario_ocupacao": {"side_effect": lambda *_a, **_k: {
                "occupied": ["2030-10-20"], "blocked_checkin": ["2030-10-21"],
                "blocked_checkout": ["2030-10-22"], "min_nights": 3,
            }},
            "alojamento_disponivel": {"return_value": True},
            "alojamento_datas_permitidas": {"return_value": {"allowed": True, "errors": []}},
            "calcular_preco": {"return_value": {
                "valor": 300, "label": "300 EUR", "noites": 3, "linhas": [],
            }},
        }
        for name, options in fixtures.items():
            patcher = patch("blueprints.booking_portal." + name, **options)
            patcher.start()
            self.addCleanup(patcher.stop)

    def render(self, lang="pt", **overrides):
        values = {**SELECTION, "lang": lang, **overrides}
        response = self.client.get("/reservas/" + PROPERTY["id"], query_string=values)
        self.assertEqual(response.status_code, 200)
        markup = response.get_data(as_text=True)
        return DetailMarkup(markup), markup, values

    def test_each_language_keeps_one_get_form_and_one_input_per_parameter(self):
        for lang in ("pt", "en", "es", "fr"):
            with self.subTest(lang=lang):
                dom, _, values = self.render(lang)
                forms = dom.matching("data-booking-calendar-form")
                self.assertEqual(len(forms), 1)
                form = forms[0]
                self.assertEqual(form["attrs"]["method"], "get")
                self.assertEqual(form["attrs"]["action"], "/reservas/" + PROPERTY["id"])
                inputs = [node["attrs"] for node in dom.descendants(form) if node["tag"] == "input"]
                self.assertEqual(len(inputs), len(values))
                self.assertEqual({item["name"]: item["value"] for item in inputs}, values)
                for name in values:
                    self.assertEqual(len(dom.matching("name", name)), 1)
                update = dom.matching("data-update-button")
                self.assertEqual(len(update), 1)
                self.assertIn(update[0], dom.descendants(form))
                self.assertEqual(update[0]["attrs"]["type"], "submit")
                self.assertNotIn("disabled", update[0]["attrs"])

    def test_calendar_and_guest_fields_have_no_duplicate_or_hidden_fallback(self):
        dom, _, _ = self.render()
        form = dom.matching("data-booking-calendar-form")[0]
        descendants = dom.descendants(form)
        for attribute in ("data-calendar", "data-calendar-months", "data-guest-adults", "data-guest-children", "data-guest-babies"):
            matches = dom.matching(attribute)
            self.assertEqual(len(matches), 1, attribute)
            self.assertIn(matches[0], descendants)
            self.assertNotIn("hidden", matches[0]["attrs"])
            self.assertNotIn("disabled", matches[0]["attrs"])
        fields = {node["attrs"]["name"]: node["attrs"] for node in descendants if node["tag"] == "input"}
        for name, minimum, maximum in (("adultos", "1", "4"), ("criancas", "0", "2"), ("bebes", "0", "2")):
            self.assertEqual(fields[name]["type"], "number")
            self.assertEqual((fields[name]["min"], fields[name]["max"]), (minimum, maximum))
        for name in ("checkin", "checkout"):
            self.assertEqual(fields[name]["type"], "hidden")
        self.assertEqual(form["attrs"]["data-max-adults"], "4")
        self.assertEqual(form["attrs"]["data-max-children"], "2")
        self.assertEqual(form["attrs"]["data-max-guests"], "6")
        self.assertEqual(form["attrs"]["data-has-crib"], "1")

    def test_reserve_action_preserves_confirmed_selection(self):
        for lang in ("pt", "en", "es", "fr"):
            with self.subTest(lang=lang):
                dom, _, values = self.render(lang)
                links = dom.matching("data-detail-reserve-action")
                self.assertEqual(len(links), 1)
                self.assertEqual(links[0]["tag"], "a")
                target = urlsplit(links[0]["attrs"]["href"])
                self.assertEqual(target.path, "/reservas/" + PROPERTY["id"] + "/reservar")
                params = parse_qs(target.query)
                for name, value in values.items():
                    self.assertEqual(params[name], [value])

    def test_guest_capacity_errors_cannot_enable_reservation(self):
        dom, _, _ = self.render(adultos="5")
        self.assertIn("disabled", dom.matching("data-update-button")[0]["attrs"])
        reserve = dom.matching("data-detail-reserve-action")
        self.assertEqual(len(reserve), 1)
        self.assertEqual(reserve[0]["tag"], "button")
        self.assertIn("disabled", reserve[0]["attrs"])

    def test_mobile_editor_controls_point_to_unique_accessible_targets(self):
        for lang in ("pt", "en", "es", "fr"):
            with self.subTest(lang=lang):
                dom, markup, _ = self.render(lang)
                controls = dom.matching("data-detail-mobile-controls")
                self.assertEqual(len(controls), 1)
                date_triggers = dom.matching("data-detail-date-trigger")
                self.assertEqual({node["attrs"]["data-detail-date-trigger"] for node in date_triggers}, {"checkin", "checkout"})
                self.assertEqual(len(date_triggers), 2)
                for node in date_triggers:
                    self.assertIn(node, dom.descendants(controls[0]))
                    self.assertEqual(node["tag"], "button")
                    self.assertEqual(node["attrs"]["type"], "button")
                    self.assertEqual(node["attrs"]["aria-haspopup"], "dialog")
                    self.assertEqual(node["attrs"]["aria-controls"], "bookingDetailCalendar")
                guest_trigger = dom.matching("data-detail-guests-trigger")
                self.assertEqual(len(guest_trigger), 1)
                self.assertEqual(guest_trigger[0]["attrs"]["type"], "button")
                self.assertEqual(guest_trigger[0]["attrs"]["aria-expanded"], "false")
                self.assertEqual(guest_trigger[0]["attrs"]["aria-controls"], "bookingDetailGuests")
                for identifier in ("bookingDetailForm", "bookingDetailCalendar", "bookingDetailGuests"):
                    self.assertEqual(len(dom.matching("id", identifier)), 1)
                for node in date_triggers + guest_trigger:
                    for identifier in node["attrs"].get("aria-labelledby", "").split():
                        self.assertEqual(len(dom.matching("id", identifier)), 1)
                for attribute in ("data-detail-static-summary", "data-detail-calendar-home", "data-detail-guests-home",
                                  "data-detail-calendar-slot", "data-detail-guests-slot", "data-detail-guest-summary"):
                    self.assertEqual(len(dom.matching(attribute)), 1)
                self.assertIn("css/booking_detail_mobile.css", markup)
                self.assertIn("js/booking_detail_mobile.js", markup)

    def test_guest_fields_remain_associated_with_get_form_when_moved(self):
        dom, _, _ = self.render()
        form_id = dom.matching("data-booking-calendar-form")[0]["attrs"]["id"]
        for attribute in ("data-guest-adults", "data-guest-children", "data-guest-babies"):
            self.assertEqual(dom.matching(attribute)[0]["attrs"]["form"], form_id)
        dialog = dom.matching("data-detail-calendar-dialog")[0]
        self.assertEqual(dialog["tag"], "dialog")
        self.assertNotIn("open", dialog["attrs"])
        self.assertTrue(dialog["attrs"].get("aria-label") or dialog["attrs"].get("aria-labelledby"))
        for close in dom.matching("data-detail-calendar-close"):
            self.assertEqual(close["attrs"]["type"], "button")
        self.assertGreaterEqual(len(dom.matching("data-detail-calendar-close")), 1)
        self.assertIn("hidden", dom.matching("data-detail-guest-popover")[0]["attrs"])

    def test_recalculation_notice_is_localized_and_reservation_action_is_identifiable(self):
        translated = []
        for lang in ("pt", "en", "es", "fr"):
            with self.subTest(lang=lang):
                dom, markup, _ = self.render(lang)
                notice = dom.matching("data-detail-update-notice")
                self.assertEqual(len(notice), 1)
                self.assertIn("hidden", notice[0]["attrs"])
                self.assertEqual(len(dom.matching("data-detail-reserve-action")), 1)
                match = re.search(r'<script[^>]*id="booking-i18n"[^>]*>(.*?)</script>', markup, re.DOTALL)
                self.assertIsNotNone(match)
                translations = json.loads(match.group(1))
                hint = translations["update_selection_hint"]
                self.assertTrue(hint.strip())
                translated.append(hint)
        self.assertEqual(len(set(translated)), 4)
        dom, _, _ = self.render(adultos="5")
        self.assertEqual(len(dom.matching("data-detail-reserve-action")), 1)
        self.assertEqual(dom.matching("data-detail-reserve-action")[0]["tag"], "button")

    def test_mobile_styles_are_opt_in_and_do_not_hide_original_desktop_fields(self):
        css = (ROOT / "static/css/booking_detail_mobile.css").read_text()
        shared, mobile = css.split("@media (max-width: 720px)", 1)
        self.assertIn(".booking-detail-inline-slot { display: contents; }", shared)
        self.assertIn(".booking-detail-mobile-controls", shared)
        self.assertIn(".booking-detail-calendar-dialog { display: none; }", shared)
        self.assertNotIn("[data-detail-static-summary]", shared)
        self.assertNotIn(".booking-guest-grid", shared)
        self.assertNotIn(".booking-calendar {", shared)
        self.assertIn("[data-mobile-detail-enhanced] [data-detail-static-summary]", mobile)
        self.assertIn(".booking-detail-calendar-dialog[open]", mobile)
        self.assertIn(".booking-detail-guest-popover[hidden] { display: none; }", mobile)
        self.assertIn("font-size: 16px", mobile)  # Guest fields must not trigger iOS input zoom.

    def test_mobile_script_reuses_nodes_and_defers_until_original_calendar_is_initialized(self):
        dom, markup, _ = self.render()
        scripts = [node for node in dom.nodes if node["tag"] == "script"
                   and "js/booking_detail_mobile.js" in node["attrs"].get("src", "")]
        self.assertEqual(len(scripts), 1)
        self.assertIn("defer", scripts[0]["attrs"])
        self.assertLess(markup.index("css/booking_portal.css"), markup.index("css/booking_detail_mobile.css"))
        source = (ROOT / "static/js/booking_detail_mobile.js").read_text()
        self.assertIn('window.matchMedia("(max-width: 720px)")', source)
        for operation in ("calendarSlot.appendChild(calendar)", "guestsSlot.appendChild(guestGrid)",
                          "calendarHome.appendChild(calendar)", "guestsHome.appendChild(guestGrid)"):
            self.assertIn(operation, source)
        for forbidden in ("cloneNode", "innerHTML", "localStorage", "sessionStorage", "document.cookie", "fetch("):
            self.assertNotIn(forbidden, source)

    def test_quote_baseline_uses_server_dates_before_hidden_input_normalization(self):
        source = (ROOT / "static/js/booking_detail_mobile.js").read_text()
        match = re.search(r"const originalValues = (.*?);", source, re.DOTALL)
        self.assertIsNotNone(match)
        baseline = match.group(1)
        self.assertIn("calendar.dataset.selectedCheckin", baseline)
        self.assertIn("calendar.dataset.selectedCheckout", baseline)
        # Hidden input.value changes defaultValue as well; it is not an SSR snapshot.
        self.assertNotIn("checkin.defaultValue", baseline)
        self.assertNotIn("checkout.defaultValue", baseline)
        self.assertNotIn("inputs.map", baseline)


if __name__ == "__main__":
    unittest.main()
