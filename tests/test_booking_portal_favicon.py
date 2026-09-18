"""The portal opts into its own icon without changing the application icon."""

import base64
from pathlib import Path
import unittest
from xml.etree import ElementTree

from flask import Flask, render_template


ROOT = Path(__file__).resolve().parents[1]
ICON = "images/booking_portal/portobreak-favicon.svg"


class BookingPortalFaviconTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(
            __name__, template_folder=str(ROOT / "templates"),
            static_folder=str(ROOT / "static"),
        )
        self.app.config["TESTING"] = True

    def render(self, template, **context):
        with self.app.test_request_context():
            return render_template(template, **context)

    def test_shared_head_includes_icon_even_without_seo_context(self):
        for context in ({}, {"seo": {"title": "Portal", "robots": "noindex"}}):
            head = self.render("booking_portal/_seo.html", **context)
            self.assertIn(ICON + "?v=2", head)
            self.assertIn('rel="icon" type="image/svg+xml" sizes="any"', head)
            self.assertNotIn("images/favicon.ico", head)

    def test_guest_icon_follows_existing_portobreak_brand_condition(self):
        for portobreak in (False, True):
            page = self.render(
                "r_public.html", public_v2=portobreak,
                invalid=True, page_data={"invalid_reason": "not_found"},
            )
            head = page.split("</head>", 1)[0]
            self.assertEqual(ICON in head, portobreak)

    def test_asset_is_self_contained_and_preserves_original_logo(self):
        response = self.app.test_client().get("/static/" + ICON)
        self.addCleanup(response.close)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "image/svg+xml")
        svg = ElementTree.fromstring(response.data)
        self.assertEqual(svg.attrib["viewBox"], "0 0 64 64")
        background = svg.find("{http://www.w3.org/2000/svg}rect")
        self.assertEqual(background.attrib["fill"], "#123f67")
        self.assertEqual(background.attrib["rx"], "13")
        symbol = svg.find("{http://www.w3.org/2000/svg}svg")
        self.assertEqual(symbol.attrib["viewBox"], "4 0 176 176")
        self.assertEqual(symbol.attrib["filter"], "url(#white-logo)")
        matrix = svg.find(".//{http://www.w3.org/2000/svg}feColorMatrix")
        self.assertEqual(matrix.attrib["values"].split(), "0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 1 0".split())
        image = svg.find(".//{http://www.w3.org/2000/svg}image")
        self.assertIsNotNone(image)
        self.assertTrue(image.attrib["href"].startswith("data:image/png;base64,"))
        original = ROOT / "static/images/booking_portal/portobreak-logo-compact.png"
        self.assertEqual(base64.b64decode(image.attrib["href"].split(",", 1)[1]), original.read_bytes())

    def test_stationzero_keeps_its_existing_icon(self):
        template = (ROOT / "templates/sz_base.html").read_text()
        self.assertIn("filename='images/favicon.ico'", template)
        self.assertNotIn("booking_portal/_favicon.html", template)
        response = self.app.test_client().get("/static/images/favicon.ico")
        self.addCleanup(response.close)
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
