"""Consent decisions are isolated from the database and booking integrations."""

import unittest
from datetime import datetime, timezone
from http.cookies import SimpleCookie
from unittest.mock import patch

from flask import Flask, jsonify
from itsdangerous import URLSafeTimedSerializer

from blueprints.booking_portal import _resolve_lang, bp
from services.booking_portal_cookies import (
    CONSENT_COOKIE,
    CONSENT_MAX_AGE,
    CONSENT_VERSION,
    LANG_COOKIE,
    read_cookie_consent,
)


class BookingPortalCookieTests(unittest.TestCase):
    endpoint = "/reservas/preferencias-cookies"

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SECRET_KEY="cookie-tests-only")
        self.app.register_blueprint(bp)

        @self.app.route("/test/current-preferences")
        def current_preferences():
            return jsonify(consent=read_cookie_consent(), lang=_resolve_lang())

        self.client = self.app.test_client()
        self.serializer = URLSafeTimedSerializer(
            self.app.secret_key, salt="portobreak-cookie-preferences-v1"
        )

    def post_preferences(self, preferences=False, external_maps=False, **kwargs):
        options = {
            "json": {"preferences": preferences, "external_maps": external_maps},
            "headers": {"Origin": "http://localhost", "Sec-Fetch-Site": "same-origin"},
        }
        options.update(kwargs)
        return self.client.post(self.endpoint, **options)

    def cookies_set_by(self, response):
        cookies = SimpleCookie()
        for header in response.headers.getlist("Set-Cookie"):
            cookies.load(header)
        return cookies

    def signed_choice(self, **changes):
        now = datetime.now(timezone.utc)
        choice = {
            "version": CONSENT_VERSION,
            "decided_at": now.isoformat(timespec="seconds"),
            "expires_at": int(now.timestamp()) + CONSENT_MAX_AGE,
            "preferences": True,
            "external_maps": True,
        }
        choice.update(changes)
        return self.serializer.dumps(choice)

    def assert_private_response(self, response):
        self.assertIn("no-store", response.cache_control)
        self.assertTrue(response.cache_control.private)
        self.assertIn("Cookie", response.vary)

    def test_first_visit_does_not_create_optional_or_consent_cookies(self):
        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json["consent"])
        self.assertEqual(response.headers.getlist("Set-Cookie"), [])
        self.assert_private_response(response)

    def test_optional_purposes_are_saved_independently(self):
        for preferences in (False, True):
            for external_maps in (False, True):
                with self.subTest(preferences=preferences, external_maps=external_maps):
                    self.client = self.app.test_client()
                    response = self.post_preferences(preferences, external_maps)
                    self.assertEqual(response.status_code, 200)
                    consent = response.json["consent"]
                    self.assertIs(consent["preferences"], preferences)
                    self.assertIs(consent["external_maps"], external_maps)
                    self.assertEqual(consent["version"], CONSENT_VERSION)
                    self.assertEqual(self.client.get(self.endpoint).json["consent"], consent)
                    self.assertEqual(LANG_COOKIE in self.cookies_set_by(response), preferences)
                    self.assert_private_response(response)

    def test_accepting_preferences_remembers_selected_language(self):
        response = self.client.post(
            self.endpoint + "?lang=fr",
            json={"preferences": True, "external_maps": False},
            headers={"Origin": "http://localhost"},
        )

        self.assertEqual(self.cookies_set_by(response)[LANG_COOKIE].value, "fr")
        state = self.client.get("/test/current-preferences").json
        self.assertEqual(state["lang"], "fr")

    def test_rejecting_preferences_deletes_previously_remembered_language(self):
        self.post_preferences(True, True)
        response = self.post_preferences(False, True)
        deleted = self.cookies_set_by(response)[LANG_COOKIE]

        self.assertEqual(deleted.value, "")
        self.assertEqual(deleted["max-age"], "0")
        self.assertIsNone(self.client.get_cookie(LANG_COOKIE))
        self.assertFalse(self.client.get(self.endpoint).json["consent"]["preferences"])

    def test_legacy_language_cookie_is_ignored_and_deleted_without_consent(self):
        self.client.set_cookie(LANG_COOKIE, "fr")
        state = self.client.get(
            "/test/current-preferences", headers={"Accept-Language": "en"}
        ).json
        self.assertEqual(state["lang"], "en")

        response = self.client.get(self.endpoint)
        self.assertIsNone(response.json["consent"])
        self.assertEqual(self.cookies_set_by(response)[LANG_COOKIE]["max-age"], "0")

    def test_tampered_expired_obsolete_and_malformed_choices_fail_closed(self):
        now = int(datetime.now(timezone.utc).timestamp())
        tokens = {
            "tampered": self.signed_choice() + "corrupted",
            "decision_expired": self.signed_choice(expires_at=now - 1),
            "obsolete_version": self.signed_choice(version="old-version"),
            "integer_boolean": self.signed_choice(preferences=1),
            "string_boolean": self.signed_choice(external_maps="true"),
            "missing_timestamp": self.signed_choice(decided_at=None),
            "string_expiration": self.signed_choice(expires_at=str(now + 100)),
            "non_object": self.serializer.dumps([True, True]),
        }
        with patch("itsdangerous.timed.time.time", return_value=now - CONSENT_MAX_AGE - 60):
            tokens["signature_expired"] = self.signed_choice()

        for reason, token in tokens.items():
            with self.subTest(reason=reason):
                self.client.set_cookie(CONSENT_COOKIE, token)
                self.client.set_cookie(LANG_COOKIE, "fr")
                response = self.client.get(self.endpoint, headers={"Accept-Language": "en"})
                self.assertIsNone(response.json["consent"])
                self.assertNotIn(CONSENT_COOKIE, self.cookies_set_by(response))
                self.assertEqual(self.cookies_set_by(response)[LANG_COOKIE]["max-age"], "0")

    def test_requests_from_wrong_or_missing_origin_cannot_save_a_choice(self):
        origins = (
            {},
            {"Origin": "https://another.example"},
            {"Origin": "null"},
            {"Origin": "http://localhost/unexpected-path"},
            {"Origin": "http://localhost", "Sec-Fetch-Site": "cross-site"},
        )
        for headers in origins:
            with self.subTest(headers=headers):
                response = self.post_preferences(True, True, headers=headers)
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.headers.getlist("Set-Cookie"), [])
                self.assert_private_response(response)

    def test_non_boolean_missing_extra_or_non_object_choices_are_rejected(self):
        payloads = (
            {"preferences": "true", "external_maps": False},
            {"preferences": True, "external_maps": 1},
            {"preferences": None, "external_maps": False},
            {"preferences": False},
            {"preferences": False, "external_maps": False, "analytics": True},
            [True, False],
        )
        for payload in payloads:
            with self.subTest(payload=payload):
                response = self.post_preferences(json=payload)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.headers.getlist("Set-Cookie"), [])
                self.assert_private_response(response)

    def test_public_https_cookies_have_security_flags_and_bounded_lifetimes(self):
        response = self.post_preferences(
            True, True,
            base_url="https://portobreak.com",
            headers={"Origin": "https://portobreak.com"},
        )

        self.assertEqual(response.status_code, 200)
        cookies = self.cookies_set_by(response)
        for name in (CONSENT_COOKIE, LANG_COOKIE):
            with self.subTest(cookie=name):
                self.assertTrue(cookies[name]["secure"])
                self.assertTrue(cookies[name]["httponly"])
                self.assertEqual(cookies[name]["samesite"], "Lax")
                self.assertEqual(cookies[name]["path"], "/")
                self.assertGreater(int(cookies[name]["max-age"]), 0)
        self.assertEqual(int(cookies[CONSENT_COOKIE]["max-age"]), CONSENT_MAX_AGE)

    def test_public_host_keeps_secure_cookies_behind_http_proxy(self):
        response = self.post_preferences(
            True, False,
            base_url="http://portobreak.com",
            headers={"Origin": "https://portobreak.com"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.cookies_set_by(response)[CONSENT_COOKIE]["secure"])

    def test_insecure_public_origin_is_rejected(self):
        response = self.post_preferences(
            True, True,
            base_url="http://portobreak.com",
            headers={"Origin": "http://portobreak.com"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.headers.getlist("Set-Cookie"), [])

    def test_reading_choice_does_not_renew_its_expiry_or_signature(self):
        created = self.post_preferences(True, False)
        original = self.cookies_set_by(created)[CONSENT_COOKIE].value
        response = self.client.get(self.endpoint)

        self.assertEqual(response.json["consent"], created.json["consent"])
        self.assertNotIn(CONSENT_COOKIE, self.cookies_set_by(response))
        self.assertEqual(self.client.get_cookie(CONSENT_COOKIE).value, original)
        self.assert_private_response(response)


if __name__ == "__main__":
    unittest.main()
