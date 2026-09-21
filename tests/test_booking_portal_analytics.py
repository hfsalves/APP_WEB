"""HTTP measurement contracts, isolated from production and app.py startup."""

import json
import unittest
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

from flask import Flask, make_response
from sqlalchemy import select

from blueprints.booking_portal import bp
from models import db
from services import booking_portal_analytics as analytics
from services import booking_portal_analytics_store as store


class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(SECRET_KEY="analytics-tests", TESTING=True,
            SQLALCHEMY_DATABASE_URI="sqlite://", PORTOBREAK_ANALYTICS_ALLOW_LOCAL=True)
        db.init_app(self.app)
        self.app.register_blueprint(bp)

        def catalog():
            return make_response(json.dumps(analytics.browser_config("en")))

        self.app.view_functions["booking_portal.index"] = catalog
        self.client = self.app.test_client()
        with self.app.app_context():
            store.ensure_schema(db.engine)
        analytics._limits.clear()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()

    def rows(self, table):
        with self.app.app_context(), db.engine.connect() as conn:
            return [dict(row) for row in conn.execute(select(table)).mappings()]

    def consent(self, allowed):
        return self.client.post("/reservas/preferencias-cookies", json={
            "analytics": allowed, "preferences": False, "external_maps": False,
        }, headers={"Origin": "http://localhost"})

    def config(self, path="/reservas", headers=None):
        return json.loads(self.client.get(path, headers=headers).data)

    def event(self, payload, **kwargs):
        return self.client.post("/reservas/analitica/eventos", json=payload,
            headers=kwargs.pop("headers", {"Origin": "http://localhost"}), **kwargs)

    def page(self, config=None, page_id=None):
        return {"type": "pageview", "context": (config or self.config())["context"],
                "page_id": page_id or str(uuid.uuid4())}

    def test_no_consent_counts_requests_not_visitors(self):
        self.config()
        self.config()
        self.assertEqual(sum(row["requests"] for row in self.rows(store.totals)), 2)
        self.assertEqual(self.rows(store.visitors), [])
        self.assertEqual(self.rows(store.sessions), [])
        self.assertIsNone(self.client.get_cookie(analytics.VISITOR_COOKIE))
        response = self.event(self.page())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.rows(store.pageviews), [])

    def test_consent_creates_signed_identity_and_idempotent_page(self):
        self.consent(True)
        payload = self.page()
        for _ in range(2):
            response = self.event(payload)
            self.assertEqual(response.status_code, 200, response.json)
        self.assertEqual(len(self.rows(store.pageviews)), 1)
        self.assertEqual(self.rows(store.sessions)[0]["page_views"], 1)
        self.assertTrue(self.client.get_cookie(analytics.VISITOR_COOKIE).http_only)
        self.assertTrue(self.client.get_cookie(analytics.SESSION_COOKIE).http_only)
        self.assertIsNone(self.rows(store.visitors)[0]["gender"])
        self.assertIsNone(self.rows(store.visitors)[0]["age_band"])

    def test_revoke_deletes_identifiers_and_stops_future_events(self):
        self.consent(True)
        payload = self.page()
        self.assertEqual(self.event(payload).status_code, 200)
        response = self.consent(False)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.client.get_cookie(analytics.VISITOR_COOKIE))
        self.assertIsNone(self.client.get_cookie(analytics.SESSION_COOKIE))
        self.assertEqual(self.event(payload).status_code, 403)
        self.assertEqual(len(self.rows(store.pageviews)), 1)

    def test_untrusted_country_and_sensitive_parameters_are_not_retained(self):
        self.consent(True)
        config = self.config("/reservas?checkin=2026-10-12&checkout=2026-10-14&adultos=2"
            "&q=private-email%40example.com&token=secret&session_id=cs_secret"
            "&utm_source=Google&utm_campaign=autumn-2026&utm_medium=email", headers={
                "Referer": "https://www.google.com/search?q=personal-query",
                "CF-IPCountry": "PT", "User-Agent": "Mozilla/5.0 Chrome/152.0",
            })
        self.event(self.page(config))
        session = self.rows(store.sessions)[0]
        self.assertEqual(session["country"], "ZZ")
        self.assertEqual(session["referrer_host"], "www.google.com")
        self.assertEqual(session["source"], "Google")
        self.assertEqual(session["campaign"], "autumn-2026")
        search = json.loads(self.rows(store.pageviews)[0]["search_json"])
        self.assertEqual(search, {"checkin": "2026-10-12", "checkout": "2026-10-14", "adultos": 2, "has_query": True})
        serialized = str(self.rows(store.sessions) + self.rows(store.pageviews) + self.rows(store.totals))
        for secret in ("private-email", "personal-query", "cs_secret", "152.0"):
            self.assertNotIn(secret, serialized)

    def test_country_only_accepted_from_trusted_proxy(self):
        for peer, expected in (("127.0.0.1", "ZZ"), ("162.158.0.1", "PT")):
            with self.app.test_request_context("/reservas", headers={"CF-IPCountry": "PT"},
                environ_base={"REMOTE_ADDR": peer}):
                self.assertEqual(analytics.request_traits()["country"], expected)
        self.app.config["PORTOBREAK_ANALYTICS_TRUSTED_PROXY_CIDRS"] = "127.0.0.1/32"
        with self.app.test_request_context("/reservas", headers={"CF-IPCountry": "ES"},
            environ_base={"REMOTE_ADDR": "127.0.0.1"}):
            self.assertEqual(analytics.request_traits()["country"], "ES")

    def test_country_accepted_through_verified_local_nginx_cloudflare_chain(self):
        with self.app.test_request_context("/reservas", headers={
            "CF-IPCountry": "PT",
            "X-Forwarded-For": "198.51.100.25, 162.158.0.1",
        }, environ_base={"REMOTE_ADDR": "127.0.0.1"}):
            self.assertEqual(analytics.request_traits()["country"], "PT")

        # A caller cannot make itself trusted by prepending a Cloudflare IP;
        # Nginx appends the actual direct peer as the right-most hop.
        with self.app.test_request_context("/reservas", headers={
            "CF-IPCountry": "PT",
            "X-Forwarded-For": "162.158.0.1, 203.0.113.25",
        }, environ_base={"REMOTE_ADDR": "127.0.0.1"}):
            self.assertEqual(analytics.request_traits()["country"], "ZZ")

    def test_bad_origin_payloads_signatures_and_durations_are_rejected(self):
        self.consent(True)
        payload = self.page()
        self.assertEqual(self.event(payload, headers={"Origin": "https://bad.example"}).status_code, 403)
        self.assertEqual(self.event(dict(payload, context="bad")).status_code, 400)
        self.assertEqual(self.event(dict(payload, email="private@example.com")).status_code, 400)
        self.assertEqual(self.event(dict(payload, page_id="invalid")).status_code, 400)
        self.event(payload)
        for value in (True, -1, "15", 86401):
            self.assertEqual(self.event({"type": "engagement", "page_id": payload["page_id"],
                "active_seconds": value}).status_code, 400)

    def test_idle_session_recovery_requires_new_page_and_session(self):
        self.consent(True)
        now = datetime(2026, 9, 21, 10, 0)
        payload = self.page()
        with patch.object(analytics, "_now") as clock:
            clock.return_value = now
            self.assertEqual(self.event(payload).status_code, 200)
            clock.return_value = now + timedelta(minutes=31)
            response = self.event({"type": "engagement", "page_id": payload["page_id"], "active_seconds": 10})
            self.assertEqual(response.status_code, 409)
            self.assertIsNone(self.client.get_cookie(analytics.SESSION_COOKIE))
            self.assertEqual(self.event(self.page()).status_code, 200)
            renewed_cookie = self.client.get_cookie(analytics.SESSION_COOKIE).value
            old_tab = self.event({"type": "engagement", "page_id": payload["page_id"], "active_seconds": 15})
            self.assertEqual(old_tab.status_code, 409)
            self.assertEqual(self.client.get_cookie(analytics.SESSION_COOKIE).value, renewed_cookie)
            self.assertEqual(self.event(self.page()).status_code, 200)
        self.assertEqual(len(self.rows(store.sessions)), 2)

    def test_preview_host_is_disabled_by_default(self):
        self.app.config.pop("PORTOBREAK_ANALYTICS_ALLOW_LOCAL")
        self.app.config["PORTOBREAK_ANALYTICS_ENABLED"] = True
        self.assertFalse(self.config()["enabled"])
        self.assertEqual(self.rows(store.totals), [])
        with self.app.test_request_context("/reservas", base_url="https://portobreak.com"):
            self.assertTrue(analytics.enabled())

    def test_analytics_failure_does_not_break_page(self):
        with patch.object(store, "record_total", side_effect=RuntimeError("offline")):
            self.assertEqual(self.client.get("/reservas").status_code, 200)

    def test_bots_are_separate_aggregates_without_sessions(self):
        config = self.config(headers={"User-Agent": "Googlebot/2.1"})
        self.assertFalse(config["enabled"])
        self.assertTrue(self.rows(store.totals)[0]["is_bot"])
        self.assertEqual(self.rows(store.visitors), [])

    def test_schema_has_no_raw_identifiers_or_private_content_columns(self):
        names = {c.name.lower() for table in store.metadata.tables.values() for c in table.columns}
        self.assertFalse(names & {"ip", "ip_cliente", "user_agent", "email", "nome", "url", "token", "password"})


if __name__ == "__main__":
    unittest.main()
