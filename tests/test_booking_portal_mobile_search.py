"""Responsive guest picker reuses the same fields and GET contract at every width."""

from html.parser import HTMLParser
from pathlib import Path
import re
import unittest
from unittest.mock import patch

from flask import Flask

from blueprints.booking_portal import bp


ROOT = Path(__file__).resolve().parents[1]


def css_block(source, marker):
    """Read one balanced CSS block; nested media selectors stay within the block."""
    start = source.index("{", source.index(marker)) + 1
    depth = 1
    for index in range(start, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index]
    raise AssertionError("Unclosed CSS block: " + marker)


def css_rule(source, selector_ending):
    for selectors, declarations in re.findall(r"([^{}]+)\{([^{}]*)\}", source):
        if any(selector.strip().endswith(selector_ending) for selector in selectors.split(",")):
            return {name.strip(): value.strip() for declaration in declarations.split(";")
                    for name, separator, value in [declaration.partition(":")] if separator}
    raise AssertionError("Missing CSS rule ending in " + selector_ending)


def grid_tracks(value):
    """Split tracks on whitespace outside minmax()/clamp(), not inside functions."""
    tracks = []
    depth = 0
    track = ""
    for char in value:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        if char.isspace() and not depth:
            if track:
                tracks.append(track)
                track = ""
        else:
            track += char
    if track:
        tracks.append(track)
    return tracks


class SearchForm(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.inside = False
        self.inputs = []
        self.buttons = []
        self.form = {}
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form" and "data-search-form" in attrs:
            self.inside = True
            self.form = attrs
        if self.inside and tag == "input":
            self.inputs.append(attrs)
        if self.inside and tag == "button":
            self.buttons.append(attrs)

    def handle_endtag(self, tag):
        if tag == "form":
            self.inside = False


class BookingPortalMobileSearchTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__, template_folder=str(ROOT / "templates"), static_folder=str(ROOT / "static"))
        self.app.config.update(TESTING=True, SECRET_KEY="mobile-search-tests-only")
        self.app.register_blueprint(bp)
        for name, result in (
            ("_portal_current_user", None),
            ("get_alojamentos_disponiveis_page", {"items": [], "total": 0, "page": 1, "pages": 1}),
        ):
            patcher = patch("blueprints.booking_portal." + name, return_value=result)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_every_filter_still_has_exactly_one_submitted_input(self):
        for lang in ("pt", "en", "es", "fr"):
            values = {"lang": lang, "checkin": "2030-10-14", "checkout": "2030-10-18",
                      "adultos": "2", "criancas": "1", "bebes": "1", "q": "Porto & Centro"}
            response = self.app.test_client().get("/reservas", query_string=values)
            self.assertEqual(response.status_code, 200)
            form = SearchForm(response.get_data(as_text=True))
            self.assertEqual(form.form["method"], "get")
            self.assertEqual(form.form["action"], "/reservas")
            self.assertEqual(len(form.inputs), len(values))
            self.assertEqual({item["name"]: item["value"] for item in form.inputs}, values)
            self.assertEqual(sum(button.get("type") == "submit" for button in form.buttons), 1)
            self.assertEqual(sum(button.get("type") == "button" for button in form.buttons), 4)
            self.assertEqual(
                {button["data-search-date-toggle"] for button in form.buttons if "data-search-date-toggle" in button},
                {"checkin", "checkout"},
            )

    def test_dates_and_guest_constraints_remain_native(self):
        response = self.app.test_client().get("/reservas")
        fields = {item["name"]: item for item in SearchForm(response.get_data(as_text=True)).inputs}
        self.assertEqual(fields["checkin"]["type"], "date")
        self.assertEqual(fields["checkout"]["type"], "date")
        for name, minimum, maximum in (("adultos", "1", "50"), ("criancas", "0", "50"), ("bebes", "0", "10")):
            self.assertEqual(fields[name]["type"], "number")
            self.assertEqual((fields[name]["min"], fields[name]["max"]), (minimum, maximum))
            self.assertNotIn("disabled", fields[name])

    def test_shared_picker_does_not_store_or_transmit_preferences(self):
        source = (ROOT / "static/js/booking_mobile_search.js").read_text()
        for forbidden in ("fetch(", "localStorage", "document.cookie", "sessionStorage"):
            self.assertNotIn(forbidden, source)
        self.assertNotIn("matchMedia", source)
        self.assertIn('toggle.setAttribute("aria-expanded", "true")', source)
        self.assertIn('form.addEventListener("invalid"', source)

    def test_guest_picker_is_shared_while_layout_remains_responsive(self):
        css = (ROOT / "static/css/booking_mobile_search.css").read_text()
        shared_rules, _ = css.split("@media", 1)
        self.assertIn("display: contents", shared_rules)  # fallback without JS
        self.assertIn(".booking-mobile-party-toggle {\n  display: grid", shared_rules)
        self.assertIn(".booking-search-party-fields {\n  display: none", shared_rules)
        self.assertIn(".booking-search-party[data-open] .booking-search-party-fields { display: grid; }", shared_rules)
        self.assertIn("@media (min-width: 721px) and (max-width: 980px)", css)
        self.assertIn("@media (max-width: 720px)", css)

    def test_desktop_header_places_logo_search_and_controls_in_one_row(self):
        css = (ROOT / "static/css/booking_mobile_search.css").read_text()
        desktop = css_block(css, "@media (min-width: 981px) {")
        header = css_rule(desktop, ".booking-topbar")
        stack = css_rule(desktop, ".booking-search-stack")
        nav = css_rule(desktop, ".booking-nav")
        search = css_rule(desktop, ".booking-search")
        actions = css_rule(desktop, ".booking-top-actions")
        self.assertEqual(len(grid_tracks(header["grid-template-columns"])), 3)
        self.assertEqual(stack["display"], "contents")
        self.assertEqual((nav["grid-column"], nav["grid-row"]), ("1", "1"))
        self.assertEqual((search["grid-column"], search["grid-row"]), ("2", "1"))
        self.assertEqual((actions["grid-column"], actions["grid-row"]), ("3", "1"))
        self.assertEqual(search["min-width"], "0")

    def test_desktop_controls_stretch_to_search_height_without_clipping_menus(self):
        css = (ROOT / "static/css/booking_mobile_search.css").read_text()
        desktop = css_block(css, "@media (min-width: 981px) {")
        actions = css_rule(desktop, ".booking-top-actions")
        self.assertEqual(actions["align-self"], "stretch")
        self.assertEqual(actions["align-items"], "center")
        self.assertNotRegex(actions.get("height", "auto"), r"\d+px$")
        self.assertIn("border", actions)
        self.assertTrue("background" in actions or "background-color" in actions)
        self.assertNotIn(actions.get("overflow"), ("hidden", "clip"))
        template = (ROOT / "templates/booking_portal/index.html").read_text()
        self.assertLess(template.index("css/booking_portal.css"), template.index("css/booking_mobile_search.css"))

    def test_tablet_and_mobile_keep_logo_and_controls_above_full_width_search(self):
        css = (ROOT / "static/css/booking_mobile_navigation.css").read_text()
        compact = css_block(css, "@media (max-width: 980px)")
        header = css_rule(compact, ".booking-topbar")
        search = css_rule(compact, ".booking-search")
        actions = css_rule(compact, ".booking-top-actions")
        self.assertEqual(len(grid_tracks(header["grid-template-columns"])), 2)
        self.assertEqual(search["grid-column"], "1 / -1")
        self.assertEqual((actions["grid-column"], actions["grid-row"]), ("2", "1"))


if __name__ == "__main__":
    unittest.main()
