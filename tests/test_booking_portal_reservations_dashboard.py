from datetime import date
from unittest.mock import patch

import pytest
from flask import Flask
from flask_login import LoginManager, UserMixin
from sqlalchemy import create_engine

from blueprints.booking_portal_reservations import bp as reservations_blueprint
from services.booking_portal_reservations_dashboard import (
    ReservationsDashboardError,
    build_reservations_dashboard,
    dashboard_filters,
    reservations_period,
)


@pytest.fixture()
def reservations_engine():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as conn:
        conn.exec_driver_sql("""
            CREATE TABLE PB_BOOKING_REQUESTS (
                PBBKSTAMP TEXT PRIMARY KEY, ALSTAMP TEXT, AL_NOME TEXT, CHECKIN DATE, CHECKOUT DATE,
                NOITES INTEGER, ADULTOS INTEGER, CRIANCAS INTEGER, BEBES INTEGER,
                CLIENTE_NOME TEXT, CLIENTE_EMAIL TEXT, CLIENTE_TELEFONE TEXT, CLIENTE_PAIS TEXT,
                ESTADO TEXT, PRECO_ESTIMADO NUMERIC, DTCRI DATETIME
            )
        """)
        conn.exec_driver_sql("""
            CREATE TABLE PB_STRIPE_TEST_PAYMENTS (
                PBPAYSTAMP TEXT PRIMARY KEY, PBBKSTAMP TEXT, ESTADO TEXT, AMBIENTE TEXT, MOEDA TEXT,
                VALOR NUMERIC, STRIPE_STATUS TEXT, RSSTAMP TEXT, DTCRI DATETIME, DTALT DATETIME
            )
        """)
        conn.exec_driver_sql("CREATE TABLE RS (RSSTAMP TEXT PRIMARY KEY, RESERVA TEXT, CANCELADA INTEGER)")
        conn.exec_driver_sql("""
            INSERT INTO PB_BOOKING_REQUESTS VALUES
            ('book-live','al-1','Alegria Studio','2026-10-12','2026-10-14',2,2,0,0,'Ana','ana@example.com','','PT','CONFIRMADO',129,'2026-09-11 19:03:29'),
            ('book-test','al-1','Alegria Studio','2026-10-20','2026-10-23',3,2,1,0,'João','joao@example.com','','PT','CONFIRMADO',279,'2026-09-12 10:00:00'),
            ('book-pending','al-2','Campanhã Living','2026-11-01','2026-11-03',2,2,0,0,'Maria','maria@example.com','','ES','PENDENTE',210,'2026-09-13 10:00:00')
        """)
        conn.exec_driver_sql("""
            INSERT INTO PB_STRIPE_TEST_PAYMENTS VALUES
            ('pay-live','book-live','PAGO','LIVE','EUR',129,'paid','rs-live','2026-09-11 19:05:00','2026-09-11 19:06:00'),
            ('pay-test','book-test','PAGO_TESTE','TEST','EUR',279,'paid','rs-test','2026-09-12 10:05:00','2026-09-12 10:06:00')
        """)
        conn.exec_driver_sql("INSERT INTO RS VALUES ('rs-live','PB123',0)")
    return engine


def test_dashboard_separates_live_revenue_from_test_payments(reservations_engine):
    period = reservations_period("2026-09-01", "2026-09-30")
    data = build_reservations_dashboard(reservations_engine, period)

    assert data["kpis"] == {
        "requests": 3,
        "live_paid": 1,
        "live_revenue": 129.0,
        "test_paid": 1,
        "test_revenue": 279.0,
        "pending": 1,
        "nights_sold": 2,
        "average_ticket": 129.0,
    }
    assert data["reservations"][0]["status"] == "pending"
    assert {item["key"] for item in data["status_breakdown"]} == {"pending", "paid"}


def test_dashboard_filters_status_property_environment_and_text(reservations_engine):
    period = reservations_period("2026-09-01", "2026-09-30")
    filters = dashboard_filters({"status": "paid", "property_id": "al-1", "environment": "LIVE", "query": "ana"})
    data = build_reservations_dashboard(reservations_engine, period, filters)

    assert data["pagination"]["total"] == 1
    assert data["reservations"][0]["reservation_code"] == "PB123"
    assert data["kpis"]["live_revenue"] == 129.0
    assert data["kpis"]["test_revenue"] == 0.0


def test_reservations_period_defaults_and_limits():
    period = reservations_period(today=date(2026, 9, 22))
    assert period["start"] == date(2026, 6, 25)
    assert period["end"] == date(2026, 9, 22)
    with pytest.raises(ReservationsDashboardError):
        reservations_period("2024-01-01", "2026-09-22")


def test_reservations_dashboard_page_requires_admin_login():
    app = Flask(__name__)
    app.secret_key = "test"
    login_manager = LoginManager(app)
    login_manager.login_view = "login"
    app.add_url_rule("/login", "login", lambda: "login")
    app.register_blueprint(reservations_blueprint)

    class User(UserMixin):
        def __init__(self, user_id, admin):
            self.id = user_id
            self.ADMIN = admin

    users = {"admin": User("admin", True), "user": User("user", False)}

    @login_manager.user_loader
    def load_user(user_id):
        return users.get(user_id)

    client = app.test_client()
    assert client.get("/dashboard/portobreak/reservas").status_code == 302
    with client.session_transaction() as session:
        session["_user_id"] = "user"
        session["_fresh"] = True
    assert client.get("/dashboard/portobreak/reservas").status_code == 403
    with client.session_transaction() as session:
        session["_user_id"] = "admin"
        session["_fresh"] = True
    with patch("blueprints.booking_portal_reservations.render_template", return_value="dashboard"):
        response = client.get("/dashboard/portobreak/reservas")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "dashboard"
