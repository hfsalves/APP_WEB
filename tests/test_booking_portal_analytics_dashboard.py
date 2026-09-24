from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from flask import Flask
from flask_login import LoginManager, UserMixin
from sqlalchemy import create_engine, insert

from blueprints.booking_portal_analytics import bp as dashboard_blueprint
from services.booking_portal_analytics_dashboard import (
    DashboardPeriodError,
    build_dashboard,
    dashboard_period,
)
from services.booking_portal_analytics_store import (
    conversions,
    ensure_schema,
    pageviews,
    sessions,
    totals,
    visitors,
)


@pytest.fixture()
def analytics_engine():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    ensure_schema(engine)
    with engine.begin() as conn:
        conn.exec_driver_sql("""
            CREATE TABLE AL (
                ALSTAMP TEXT PRIMARY KEY, NMPESQUISA TEXT, NMAIRBNB TEXT, NOME TEXT
            )
        """)
        conn.exec_driver_sql("""
            CREATE TABLE PB_BOOKING_REQUESTS (PBBKSTAMP TEXT PRIMARY KEY, ALSTAMP TEXT)
        """)
        conn.exec_driver_sql("""
            CREATE TABLE PB_STRIPE_TEST_PAYMENTS (
                PBBKSTAMP TEXT, AMBIENTE TEXT, ESTADO TEXT, STRIPE_STATUS TEXT
            )
        """)
        conn.exec_driver_sql("INSERT INTO AL VALUES ('prop-1', 'Alegria Studio', '', '')")
        conn.exec_driver_sql("INSERT INTO PB_BOOKING_REQUESTS VALUES ('book-1', 'prop-1')")
        conn.exec_driver_sql("INSERT INTO PB_STRIPE_TEST_PAYMENTS VALUES ('book-1', 'LIVE', 'PAGO', 'paid')")

        observed = datetime(2026, 9, 20, 12)
        consent = datetime(2026, 9, 20, 11, 59)
        conn.execute(insert(visitors), [
            {"visitor_id": "visitor-human", "created_at": observed, "last_seen_at": observed, "demographic_source": "unknown"},
            {"visitor_id": "visitor-validation", "created_at": observed, "last_seen_at": observed, "demographic_source": "unknown"},
        ])
        session_base = {
            "started_at": observed,
            "last_seen_at": observed,
            "engagement_seen_at": observed,
            "country_source": "edge",
            "browser": "Safari",
            "os": "iOS",
            "language": "pt",
            "entry_page": "catalog",
            "referrer_host": "google.com",
            "medium": "organic",
            "campaign": "",
            "consent_version": "1",
            "consent_at": consent,
        }
        conn.execute(insert(sessions), [
            dict(session_base, session_id="session-human", visitor_id="visitor-human", country="PT", device="mobile", source="google", active_seconds=120, page_views=2, traffic_class="HUMAN", human_score=75, classification_reason="consented_javascript"),
            dict(session_base, session_id="session-validation", visitor_id="visitor-validation", country="ZZ", device="desktop", source="codex-validation", active_seconds=10, page_views=1, traffic_class="LIKELY_HUMAN", human_score=20, classification_reason="consented_javascript"),
        ])
        conn.execute(insert(pageviews), [
            {"page_id": "page-1", "session_id": "session-human", "created_at": observed, "last_seen_at": observed, "page_kind": "catalog", "property_id": None, "lang": "pt", "view_mode": "list", "search_json": '{"adultos":2,"checkin":"2026-10-01","checkout":"2026-10-04","has_query":true}', "active_seconds": 40},
            {"page_id": "page-2", "session_id": "session-human", "created_at": observed, "last_seen_at": observed, "page_kind": "property", "property_id": "prop-1", "lang": "pt", "view_mode": "detail", "search_json": '{}', "active_seconds": 80},
            {"page_id": "page-validation", "session_id": "session-validation", "created_at": observed, "last_seen_at": observed, "page_kind": "catalog", "property_id": None, "lang": "pt", "view_mode": "list", "search_json": '{}', "active_seconds": 10},
        ])
        conn.execute(insert(conversions), {"booking_id": "book-1", "session_id": "session-human", "created_at": observed})
        total_base = {
            "hour": observed.replace(minute=0), "page_kind": "catalog", "property_id": "", "device": "mobile",
            "country": "PT", "referrer_host": "", "has_search": False,
        }
        conn.execute(insert(totals), [
            dict(total_base, bucket_key="human", source="direct", is_bot=False, requests=10),
            dict(total_base, bucket_key="bot", source="unknown", is_bot=True, requests=5),
            dict(total_base, bucket_key="validation", source="codex-validation", is_bot=False, requests=3),
        ])
    return engine


def test_dashboard_excludes_bots_and_validation_by_default(analytics_engine):
    period = dashboard_period("2026-09-20", "2026-09-20")
    data = build_dashboard(analytics_engine, period)

    assert data["kpis"] == {
        "visitors": 1,
        "sessions": 1,
        "pageviews": 2,
        "searches": 1,
        "checkouts": 1,
        "payments": 0,
        "bookings": 1,
        "requests": 15,
        "average_active_seconds": 120,
        "pageviews_per_session": 2.0,
        "accesses": 10,
        "bot_accesses": 5,
        "visits": None,
        "paid_bookings": 1,
    }
    assert data["data_quality"]["validation_sessions_excluded"] == 1
    assert data["data_quality"]["validation_requests_excluded"] == 3
    assert data["properties"][0]["name"] == "Alegria Studio"
    assert data["searches"]["average_nights"] == 3.0
    assert data["searches"]["average_guests"] == 2.0
    assert data["recent_sessions"][0]["source"] == "google"


def test_dashboard_can_show_technical_traffic_explicitly(analytics_engine):
    period = dashboard_period("2026-09-20", "2026-09-20")
    data = build_dashboard(analytics_engine, period, include_bots=True, include_validation=True)

    assert data["kpis"]["requests"] == 18
    assert data["kpis"]["accesses"] == 13
    assert data["kpis"]["bot_accesses"] == 5
    assert data["kpis"]["sessions"] == 2
    assert data["kpis"]["pageviews"] == 3
    assert data["data_quality"]["validation_sessions_excluded"] == 0


def test_dashboard_period_uses_lisbon_days_and_limits_range():
    period = dashboard_period("2026-03-29", "2026-03-29", today=date(2026, 3, 29))
    assert period["start_utc"] == datetime(2026, 3, 29, 0)
    assert period["end_utc"] == datetime(2026, 3, 29, 23)

    with pytest.raises(DashboardPeriodError):
        dashboard_period("2026-01-01", "2026-09-21")


def test_dashboard_frontend_does_not_render_private_identifiers():
    project = Path(__file__).resolve().parents[1]
    template = (project / "templates" / "booking_portal_analytics.html").read_text()
    javascript = (project / "static" / "js" / "booking_portal_analytics_dashboard.js").read_text()

    assert "visitor_id" not in template
    assert "session_id" not in template
    assert "visitor_id" not in javascript
    assert "session_id" not in javascript
    assert "textContent" in javascript


def test_dashboard_mobile_layout_is_compact_and_uses_card_tables():
    project = Path(__file__).resolve().parents[1]
    template = (project / "templates" / "booking_portal_analytics.html").read_text()
    stylesheet = (project / "static" / "css" / "booking_portal_analytics_dashboard.css").read_text()
    javascript = (project / "static" / "js" / "booking_portal_analytics_dashboard.js").read_text()

    assert ".pb-analytics-contextbar .sz_contextbar_left { flex: 0 0 auto; }" in stylesheet
    assert ".pb-kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }" in stylesheet
    assert "grid-template-areas: \"breadcrumbs\" \"title\" \"subtitle\"" in stylesheet
    assert template.count("pb-mobile-card-table") == 2
    assert "cell.dataset.label = label" in javascript


def test_dashboard_page_requires_an_admin_login():
    app = Flask(__name__)
    app.secret_key = "test"
    login_manager = LoginManager(app)
    login_manager.login_view = "login"
    app.add_url_rule("/login", "login", lambda: "login")
    app.register_blueprint(dashboard_blueprint)

    class User(UserMixin):
        def __init__(self, user_id, admin):
            self.id = user_id
            self.ADMIN = admin

    users = {"admin": User("admin", True), "user": User("user", False)}

    @login_manager.user_loader
    def load_user(user_id):
        return users.get(user_id)

    client = app.test_client()
    assert client.get("/analytics/portobreak").status_code == 302

    with client.session_transaction() as session:
        session["_user_id"] = "user"
        session["_fresh"] = True
    assert client.get("/analytics/portobreak").status_code == 403

    with client.session_transaction() as session:
        session["_user_id"] = "admin"
        session["_fresh"] = True
    with patch("blueprints.booking_portal_analytics.render_template", return_value="dashboard"):
        response = client.get("/analytics/portobreak")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "dashboard"
