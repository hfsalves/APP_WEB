from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from services.client_reservations_calendar_service import (
    ClientCalendarError,
    build_client_calendar,
    calendar_window,
)


@pytest.fixture()
def calendar_engine():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE AL (
                ALSTAMP TEXT PRIMARY KEY,
                NOME TEXT,
                INATIVO INTEGER DEFAULT 0,
                CLIENTID INTEGER DEFAULT 0,
                CLESTAB INTEGER DEFAULT 0,
                FTLIMPEZA INTEGER DEFAULT 0,
                FEID INTEGER DEFAULT 0
            )
        """))
        connection.execute(text("""
            CREATE TABLE RS (
                RSSTAMP TEXT PRIMARY KEY,
                RESERVA TEXT,
                ALOJAMENTO TEXT,
                DATAIN DATE,
                DATAOUT DATE,
                HORAIN TEXT,
                HORAOUT TEXT,
                NOME TEXT,
                ADULTOS INTEGER,
                CRIANCAS INTEGER,
                BEBES INTEGER,
                ESTADIA REAL DEFAULT 0,
                LIMPEZA REAL DEFAULT 0,
                COMISSAO REAL DEFAULT 0,
                PCANCEL REAL DEFAULT 0,
                ORIGEM TEXT,
                CANCELADA INTEGER DEFAULT 0,
                DTCANCEL DATE,
                FEID INTEGER DEFAULT 0
            )
        """))
        connection.execute(text("""
            INSERT INTO AL (ALSTAMP, NOME, CLIENTID, CLESTAB, FTLIMPEZA, FEID) VALUES
              ('a1', 'Casa Azul', 10, 0, 0, 3),
              ('a2', 'Casa Verde', 10, 0, 0, 2),
              ('a3', 'Casa de Outro', 11, 0, 0, 2),
              ('a4', 'Casa Filial', 10, 2, 1, 2)
        """))
        connection.execute(text("""
            INSERT INTO RS
              (RSSTAMP, RESERVA, ALOJAMENTO, DATAIN, DATAOUT, HORAIN, HORAOUT, NOME,
               ADULTOS, CRIANCAS, BEBES, ESTADIA, LIMPEZA, COMISSAO, PCANCEL,
               ORIGEM, CANCELADA, DTCANCEL, FEID)
            VALUES
              ('r1', 'BOOK-1', 'Casa Azul', '2026-09-29', '2026-10-03', '16:00', '11:00', 'Ana', 2, 1, 0, 300, 40, 45, 0, 'Airbnb', 0, NULL, 2),
              ('r2', 'BOOK-2', 'Casa Azul', '2026-10-12', '2026-10-15', '15:00', '10:00', 'Bruno', 2, 0, 1, 250, 40, 35, 90, 'Booking', 1, '2026-10-01', 2),
              ('r3', 'BOOK-3', 'Casa Verde', '2026-11-01', '2026-11-04', '15:00', '11:00', 'Carla', 1, 0, 0, 200, 30, 25, 0, 'Direta', 0, NULL, 2),
              ('r4', 'BOOK-X', 'Casa de Outro', '2026-10-10', '2026-10-12', '15:00', '11:00', 'Outro', 4, 0, 0, 180, 35, 20, 0, 'Airbnb', 0, NULL, 2),
              ('r5', 'BOOK-F', 'Casa Filial', '2026-10-20', '2026-10-22', '15:00', '11:00', 'Filial', 2, 0, 0, 220, 35, 30, 0, 'Airbnb', 0, NULL, 2)
        """))
    return engine


def test_calendar_window_defaults_to_twelve_months():
    window = calendar_window(today=date(2026, 10, 19))
    assert window == {"start": date(2026, 10, 1), "end": date(2027, 10, 1), "months": 12}


def test_calendar_is_scoped_to_owner_and_keeps_cross_entity_reservations(calendar_engine):
    payload = build_client_calendar(
        calendar_engine,
        10,
        lodging="Casa Azul",
        start="2026-10",
        today=date(2026, 10, 19),
    )
    assert payload["lodgings"] == ["Casa Azul", "Casa Filial", "Casa Verde"]
    assert [row["reservation"] for row in payload["reservations"]] == ["BOOK-1"]
    assert payload["reservations"][0]["people"] == 3
    assert payload["reservations"][0]["total_value"] == 340.0
    assert payload["reservations"][0]["net_value"] == 295.0


def test_calendar_can_include_cancelled_reservations(calendar_engine):
    payload = build_client_calendar(
        calendar_engine,
        10,
        lodging="Casa Azul",
        start="2026-10",
        include_cancelled=True,
    )
    assert [row["reservation"] for row in payload["reservations"]] == ["BOOK-1", "BOOK-2"]
    assert payload["reservations"][1]["cancelled"] is True


def test_calendar_respects_establishment_scope(calendar_engine):
    payload = build_client_calendar(calendar_engine, 10, 2, start="2026-10")
    assert payload["lodgings"] == ["Casa Filial"]
    assert payload["selected_lodging"] == "Casa Filial"
    assert [row["reservation"] for row in payload["reservations"]] == ["BOOK-F"]
    assert payload["reservations"][0]["net_value"] == 190.0


def test_calendar_rejects_lodging_from_another_owner(calendar_engine):
    with pytest.raises(ClientCalendarError, match="não pertence"):
        build_client_calendar(calendar_engine, 10, lodging="Casa de Outro", start="2026-10")


def test_calendar_frontend_contract():
    project = Path(__file__).resolve().parents[1]
    template = (project / "templates" / "cliente_calendario.html").read_text(encoding="utf-8")
    javascript = (project / "static" / "js" / "cliente_calendario.js").read_text(encoding="utf-8")
    stylesheet = (project / "static" / "css" / "cliente_calendario.css").read_text(encoding="utf-8")
    assert "clientCalendarLodging" in template
    assert "clientCalendarStart" in template
    assert "months: '1'" in javascript
    assert "client-calendar-week" in stylesheet
    assert "client-calendar-reservation" in stylesheet
    assert "rawStartPosition" in javascript
    assert "rawEndPosition" in javascript
    assert "repeat(7" in stylesheet
