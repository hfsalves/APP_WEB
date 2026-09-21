"""The catalog date picker enhances the existing GET search without inventory calls."""

from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest.mock import patch

from flask import Flask

from blueprints.booking_portal import bp


ROOT = Path(__file__).resolve().parents[1]
BUNDLED_NODE = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"
NODE = shutil.which("node") or (str(BUNDLED_NODE) if BUNDLED_NODE.is_file() else None)


class SearchCalendarMarkup(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.nodes = []
        self.config_text = ""
        self.inside_config = False
        self.inside_form = False
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form" and "data-search-form" in attrs:
            self.inside_form = True
        self.nodes.append((tag, attrs, self.inside_form))
        if tag == "script" and attrs.get("id") == "booking-search-calendar-config":
            self.inside_config = True

    def handle_endtag(self, tag):
        if tag == "form":
            self.inside_form = False
        if tag == "script":
            self.inside_config = False

    def handle_data(self, data):
        if self.inside_config:
            self.config_text += data


class BookingPortalSearchCalendarTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__, template_folder=str(ROOT / "templates"), static_folder=str(ROOT / "static"))
        self.app.config.update(TESTING=True, SECRET_KEY="search-calendar-tests-only")
        self.app.register_blueprint(bp)
        for name, result in (
            ("_portal_current_user", None),
            ("get_alojamentos_disponiveis_page", {"items": [], "total": 0, "page": 1, "pages": 1}),
        ):
            patcher = patch("blueprints.booking_portal." + name, return_value=result)
            patcher.start()
            self.addCleanup(patcher.stop)
        occupied = patch("blueprints.booking_portal.get_calendario_ocupacao", side_effect=AssertionError("Search has no property availability calendar"))
        occupied.start()
        self.addCleanup(occupied.stop)

    def test_all_languages_keep_native_dates_get_values_and_accessible_calendar(self):
        for lang in ("pt", "en", "es", "fr"):
            with self.subTest(lang=lang):
                values = {"lang": lang, "checkin": "2030-10-14", "checkout": "2030-10-18",
                          "adultos": "2", "criancas": "1", "bebes": "1", "q": "Porto & Centro", "view": "map"}
                response = self.app.test_client().get("/reservas", query_string=values)
                self.assertEqual(response.status_code, 200)
                parsed = SearchCalendarMarkup(response.get_data(as_text=True))
                inputs = [attrs for tag, attrs, inside in parsed.nodes if tag == "input" and inside]
                self.assertEqual(len(inputs), len(values))
                self.assertEqual({attrs["name"]: attrs["value"] for attrs in inputs}, values)
                for field in ("checkin", "checkout"):
                    attrs = next(item for item in inputs if item["name"] == field)
                    self.assertEqual(attrs["type"], "date")
                    self.assertNotIn("disabled", attrs)
                    self.assertNotIn("hidden", attrs)
                    toggle = next(attrs for tag, attrs, inside in parsed.nodes
                                  if inside and attrs.get("data-search-date-toggle") == field)
                    self.assertEqual(toggle["type"], "button")
                    self.assertEqual(toggle["aria-haspopup"], "dialog")
                    self.assertEqual(toggle["aria-expanded"], "false")
                    self.assertIn("aria-controls", toggle)
                dialogs = [(attrs, inside) for tag, attrs, inside in parsed.nodes
                           if tag == "dialog" and "data-search-calendar" in attrs]
                self.assertEqual(len(dialogs), 1)
                dialog, inside = dialogs[0]
                self.assertFalse(inside, "Calendar buttons must not accidentally submit the GET search")
                self.assertIn("aria-labelledby", dialog)
                self.assertNotIn("open", dialog)
                config = json.loads(parsed.config_text)
                self.assertEqual(config["lang"], lang)
                for key in ("calendar_start", "calendar_pick_checkout", "checkout_after_checkin", "checkin", "checkout", "choose"):
                    self.assertTrue(config["labels"][key], key)

    def test_calendar_assets_preserve_no_script_fallback_and_have_no_inventory_endpoint(self):
        response = self.app.test_client().get("/reservas?lang=pt")
        parsed = SearchCalendarMarkup(response.get_data(as_text=True))
        scripts = [attrs for tag, attrs, _ in parsed.nodes if tag == "script"]
        script = next(attrs for attrs in scripts if "booking_search_calendar.js" in attrs.get("src", ""))
        self.assertIn("defer", script)
        form = next(attrs for tag, attrs, _ in parsed.nodes if tag == "form" and "data-search-form" in attrs)
        self.assertNotIn("data-date-picker-enhanced", form)
        self.assertNotIn("occupied", parsed.config_text.lower())
        source = (ROOT / "static/js/booking_search_calendar.js").read_text()
        for forbidden in ("fetch(", "localStorage", "document.cookie", "sessionStorage", ".requestSubmit(", ".submit("):
            self.assertNotIn(forbidden, source)

    @unittest.skipUnless(NODE, "Node.js is required for isolated calendar behavior checks")
    def test_real_javascript_calendar_behavior(self):
        result = subprocess.run([NODE, str(ROOT / "tests/booking_search_calendar.test.js")],
                                cwd=ROOT, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
