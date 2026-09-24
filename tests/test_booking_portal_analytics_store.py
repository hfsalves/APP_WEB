"""Analytics storage stays additive, private, idempotent and concurrency-safe."""

import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import create_engine, event, inspect, select
from sqlalchemy.dialects import mssql
from sqlalchemy.schema import CreateTable

from services import booking_portal_analytics_store as store


class AnalyticsStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.engine = create_engine("sqlite:///" + str(Path(self.temp.name) / "analytics.sqlite"), connect_args={"timeout": 10})
        self.addCleanup(self.engine.dispose)

        @event.listens_for(self.engine, "connect")
        def foreign_keys(dbapi_connection, _):
            dbapi_connection.execute("PRAGMA foreign_keys=ON")

        store.ensure_schema(self.engine)
        self.now = datetime(2026, 9, 21, 12, 0, 0)
        self.context = {"page_kind": "property", "property_id": "property-id", "lang": "pt", "view_mode": "list",
                        "referrer_host": "www.google.com", "source": "google", "medium": "organic", "campaign": "",
                        "search": {"checkin": "2026-10-10", "checkout": "2026-10-12", "adultos": 2, "has_query": True}}
        self.traits = {"country": "PT", "country_source": "cloudflare", "device": "mobile", "browser": "Chrome", "os": "Android"}
        self.consent = {"version": "v2", "decided_at": self.now}

    def page(self, visitor="visitor-1", session="session-1", page="page-1", seconds=0, **kwargs):
        return store.record_pageview(self.engine, visitor_id=visitor, session_id=session, page_id=page,
                                     context=kwargs.get("context", self.context), traits=self.traits, consent=self.consent,
                                     now=self.now + timedelta(seconds=seconds))

    def heartbeat(self, active, seconds, page="page-1", visitor="visitor-1", session="session-1"):
        return store.record_engagement(self.engine, visitor_id=visitor, session_id=session, page_id=page,
                                       active_seconds=active, now=self.now + timedelta(seconds=seconds))

    def rows(self, table):
        with self.engine.connect() as conn:
            return list(conn.execute(select(table)).mappings())

    def test_schema_is_explicit_additive_and_repeatable(self):
        store.ensure_schema(self.engine)
        self.assertEqual(set(inspect(self.engine).get_table_names()), {t.name for t in store.metadata.tables.values()})
        self.assertEqual(len(store.metadata.tables), 6)

    def test_idempotent_page_and_first_touch_session(self):
        self.assertTrue(self.page()["created"])
        self.assertFalse(self.page(seconds=10)["created"])
        other_context = {**self.context, "source": "internal", "referrer_host": "portobreak.com", "page_kind": "booking"}
        self.page(page="page-2", seconds=20, context=other_context)
        session = self.rows(store.sessions)[0]
        self.assertEqual(session["page_views"], 2)
        self.assertEqual(session["source"], "google")
        self.assertEqual(session["entry_page"], "property")
        self.assertEqual(session["consent_at"], self.now)
        visitor = self.rows(store.visitors)[0]
        self.assertIsNone(visitor["gender"])
        self.assertIsNone(visitor["age_band"])
        self.assertEqual(visitor["demographic_source"], "unknown")

    def test_unknown_session_country_can_be_enriched_but_not_overwritten(self):
        unknown_traits = {**self.traits, "country": "ZZ", "country_source": "unknown"}
        store.record_pageview(
            self.engine, visitor_id="visitor-1", session_id="session-1", page_id="page-1",
            context=self.context, traits=unknown_traits, consent=self.consent, now=self.now,
        )
        self.page(page="page-2", seconds=10)
        session = self.rows(store.sessions)[0]
        self.assertEqual(session["country"], "PT")
        self.assertEqual(session["country_source"], "cloudflare")

        other_traits = {**self.traits, "country": "ES", "country_source": "cloudflare"}
        store.record_pageview(
            self.engine, visitor_id="visitor-1", session_id="session-1", page_id="page-3",
            context=self.context, traits=other_traits, consent=self.consent,
            now=self.now + timedelta(seconds=20),
        )
        self.assertEqual(self.rows(store.sessions)[0]["country"], "PT")

    def test_no_raw_request_or_unapproved_search_fields_are_saved(self):
        context = {**self.context, "raw_url": "/private/secret", "search": {**self.context["search"], "q": "someone@example.com", "token": "secret"}}
        traits = {**self.traits, "ip": "192.0.2.123", "user_agent": "RAW-UA", "gender": "guessed"}
        store.record_pageview(self.engine, visitor_id="visitor-1", session_id="session-1", page_id="page-1",
                              context=context, traits=traits, consent=self.consent, now=self.now)
        page = self.rows(store.pageviews)[0]
        self.assertEqual(json.loads(page["search_json"]), self.context["search"])
        all_rows = str([self.rows(table) for table in store.metadata.tables.values()])
        for forbidden in ("someone@example.com", "secret", "192.0.2.123", "RAW-UA", "guessed"):
            self.assertNotIn(forbidden, all_rows)

    def test_identifiers_cannot_be_rebound_to_another_session_or_visitor(self):
        self.page()
        with self.assertRaises(store.AnalyticsConflict):
            self.page(visitor="visitor-2", page="page-2")
        with self.assertRaises(store.AnalyticsConflict):
            self.page(session="session-2")
        with self.assertRaises(store.AnalyticsConflict):
            self.heartbeat(10, 10, visitor="visitor-2")
        self.assertEqual(len(self.rows(store.visitors)), 1)
        self.assertEqual(len(self.rows(store.sessions)), 1)

    def test_inactivity_boundary_and_expired_session_require_new_ids(self):
        self.page()
        self.page(page="page-boundary", seconds=1800)
        with self.assertRaises(store.SessionExpired):
            self.page(page="page-expired", seconds=3601)
        with self.assertRaises(store.SessionExpired):
            self.heartbeat(50, 3601)
        self.page(session="session-2", page="page-new", seconds=3601)
        self.assertEqual(len(self.rows(store.sessions)), 2)
        self.assertEqual(self.rows(store.visitors)[0]["last_seen_at"], self.now + timedelta(seconds=3601))

    def test_heartbeats_are_monotonic_and_capped_by_server_wall_time(self):
        self.page()
        result = self.heartbeat(99999, 15)
        self.assertEqual(result["active_seconds"], 15)
        self.assertEqual(result["session_active_seconds"], 15)
        self.assertEqual(self.heartbeat(15, 20)["session_active_seconds"], 15)
        self.assertEqual(self.heartbeat(10, 25)["active_seconds"], 15)
        self.assertEqual(self.heartbeat(25, 30)["session_active_seconds"], 25)
        self.assertEqual(self.heartbeat(-10, 31)["active_seconds"], 25)

    def test_concurrent_tabs_do_not_double_active_session_time(self):
        self.page()
        self.page(page="page-2", seconds=5)
        self.assertEqual(self.heartbeat(10, 10)["session_active_seconds"], 10)
        self.assertEqual(self.heartbeat(10, 15, page="page-2")["session_active_seconds"], 15)
        self.assertEqual(self.heartbeat(20, 20)["session_active_seconds"], 20)
        self.assertEqual(self.heartbeat(15, 20, page="page-2")["session_active_seconds"], 20)
        self.assertEqual(sum(row["active_seconds"] for row in self.rows(store.pageviews)), 35)

    def test_utc_normalization_and_no_backwards_timestamps(self):
        self.consent["decided_at"] = "2026-09-21T13:00:00+01:00"
        store.record_pageview(self.engine, visitor_id="visitor-1", session_id="session-1", page_id="page-1",
                              context=self.context, traits=self.traits, consent=self.consent,
                              now=self.now.replace(hour=13, tzinfo=timezone(timedelta(hours=1))))
        self.heartbeat(10, 10)
        self.heartbeat(1, 5)
        self.assertEqual(self.rows(store.sessions)[0]["last_seen_at"], self.now + timedelta(seconds=10))
        self.assertEqual(self.rows(store.sessions)[0]["consent_at"], self.now)

    def test_totals_are_hourly_atomic_under_concurrency(self):
        dimensions = {"page_kind": "catalog", "device": "desktop", "country": "pt", "source": "unknown", "has_search": True, "is_bot": False}
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda _: store.record_total(self.engine, dimensions, self.now), range(80)))
        rows = self.rows(store.totals)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["requests"], 80)
        self.assertEqual(rows[0]["country"], "PT")
        store.record_total(self.engine, dimensions, self.now + timedelta(hours=1))
        self.assertEqual(len(self.rows(store.totals)), 2)

    def test_pageviews_are_idempotent_under_concurrency(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.page(), range(16)))
        self.assertEqual(sum(result["created"] for result in results), 1)
        self.assertEqual(self.rows(store.sessions)[0]["page_views"], 1)

    def test_booking_link_requires_owned_recent_session_and_is_idempotent(self):
        self.page()
        args = dict(visitor_id="visitor-1", session_id="session-1", booking_id="booking-1", now=self.now)
        self.assertTrue(store.link_booking(self.engine, **args)["created"])
        self.assertFalse(store.link_booking(self.engine, **args)["created"])
        self.page(session="session-2", page="page-2")
        with self.assertRaises(store.AnalyticsConflict):
            store.link_booking(self.engine, **{**args, "session_id": "session-2"})
        with self.assertRaises(store.SessionExpired):
            store.link_booking(self.engine, **{**args, "now": self.now + timedelta(minutes=31)})
        self.assertEqual(len(self.rows(store.conversions)), 1)

    def test_whatsapp_event_is_owned_idempotent_and_keeps_only_approved_data(self):
        self.page()
        args = dict(
            visitor_id="visitor-1", session_id="session-1", page_id="page-1",
            event_id="event-1", event_name="WHATSAPP_CLICK",
            event_data={"within_hours": True}, now=self.now,
        )
        self.assertTrue(store.record_event(self.engine, **args)["created"])
        self.assertFalse(store.record_event(self.engine, **args)["created"])
        event = self.rows(store.events)[0]
        self.assertEqual(event["event_name"], "WHATSAPP_CLICK")
        self.assertEqual(json.loads(event["event_json"]), {"within_hours": True})
        with self.assertRaises(store.AnalyticsConflict):
            store.record_event(self.engine, **{**args, "session_id": "another"})

    def test_consented_interactions_promote_a_session_to_human(self):
        self.page()
        for number, name in enumerate(("SEARCH", "DATE_SELECT", "GUEST_SELECT"), start=1):
            result = store.record_event(
                self.engine, visitor_id="visitor-1", session_id="session-1", page_id="page-1",
                event_id=f"event-{number}", event_name=name, event_data={},
                now=self.now + timedelta(seconds=number),
            )
        session = self.rows(store.sessions)[0]
        self.assertEqual(result["traffic_class"], "HUMAN")
        self.assertEqual(session["traffic_class"], "HUMAN")
        self.assertGreaterEqual(session["human_score"], 60)
        self.assertIn("consented_javascript", session["classification_reason"])

    def test_server_outcomes_and_conversion_states_are_idempotent(self):
        self.page()
        self.assertTrue(store.link_booking(
            self.engine, visitor_id="visitor-1", session_id="session-1", booking_id="booking-1", now=self.now,
        )["created"])
        self.assertTrue(store.mark_payment_started(self.engine, booking_id="booking-1", now=self.now)["created"])
        self.assertFalse(store.mark_payment_started(self.engine, booking_id="booking-1", now=self.now)["created"])
        self.assertTrue(store.mark_booking_success(self.engine, booking_id="booking-1", now=self.now)["created"])
        self.assertFalse(store.mark_booking_success(self.engine, booking_id="booking-1", now=self.now)["created"])
        outcome = store.record_server_event(
            self.engine, visitor_id="visitor-1", session_id="session-1", event_name="LOGIN_SUCCESS", now=self.now,
        )
        self.assertTrue(outcome["created"])
        self.assertFalse(store.record_server_event(
            self.engine, visitor_id="visitor-1", session_id="session-1", event_name="LOGIN_SUCCESS", now=self.now,
        )["created"])
        conversion = self.rows(store.conversions)[0]
        self.assertIsNotNone(conversion["payment_started_at"])
        self.assertIsNotNone(conversion["booking_success_at"])
        self.assertEqual(self.rows(store.sessions)[0]["traffic_class"], "HUMAN")

    def test_prune_child_first_with_foreign_keys_and_retention_boundaries(self):
        for label, days in (("old", 181), ("expired", 91), ("boundary", 90), ("recent", 1)):
            created = self.now - timedelta(days=days)
            store.record_pageview(self.engine, visitor_id=label, session_id=label, page_id=label,
                                  context=self.context, traits=self.traits, consent=self.consent, now=created)
            store.link_booking(self.engine, visitor_id=label, session_id=label, booking_id=label, now=created)
            store.record_total(self.engine, {"page_kind": "catalog"}, created)
        removed = store.prune(self.engine, self.now)
        self.assertEqual(removed, {"events": 0, "conversions": 2, "pageviews": 2, "sessions": 2, "totals": 1, "visitors": 1})
        self.assertEqual({row["session_id"] for row in self.rows(store.sessions)}, {"boundary", "recent"})
        self.assertEqual({row["visitor_id"] for row in self.rows(store.visitors)}, {"expired", "boundary", "recent"})

    def test_mssql_lock_hints_compile_without_for_update(self):
        statement = select(store.sessions).with_hint(store.sessions, "WITH (UPDLOCK, HOLDLOCK)", "mssql")
        compiled = str(statement.compile(dialect=mssql.dialect()))
        self.assertIn("WITH (UPDLOCK, HOLDLOCK)", compiled)

    def test_mssql_metadata_and_migration_use_microsecond_datetime2(self):
        ddl = "\n".join(str(CreateTable(table).compile(dialect=mssql.dialect())) for table in store.metadata.sorted_tables)
        migration = (Path(__file__).resolve().parents[1] / "migrations" / "booking_portal_analytics.sql").read_text()
        self.assertEqual(ddl.count("DATETIME2(6)"), 13)
        self.assertEqual(migration.count("DATETIME2(6)"), 15)
        self.assertNotIn(" DATETIME ", ddl)

    def test_replayed_page_cannot_overwrite_original_payload(self):
        self.page()
        result = self.page(seconds=1, context={**self.context, "property_id": "changed", "search": {"adultos": 9}})
        self.assertFalse(result["created"])
        page = self.rows(store.pageviews)[0]
        self.assertEqual(page["property_id"], "property-id")
        self.assertEqual(json.loads(page["search_json"])["adultos"], 2)
        self.assertEqual(self.rows(store.sessions)[0]["page_views"], 1)

    def test_invalid_payload_rolls_back_new_visitor_and_session(self):
        with self.assertRaises(TypeError):
            self.page(context={**self.context, "search": {"adultos": object()}})
        self.assertEqual(self.rows(store.visitors), [])
        self.assertEqual(self.rows(store.sessions), [])
        self.assertEqual(self.rows(store.pageviews), [])


if __name__ == "__main__":
    unittest.main()
