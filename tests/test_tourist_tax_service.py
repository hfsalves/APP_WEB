from datetime import date

from services.tourist_tax_service import build_tourist_tax_rows, night_limit, period_bounds, reservation_origin


def test_cross_month_booking_uses_only_nights_in_period_and_incremental_limit():
    rows, warnings = build_tourist_tax_rows([{"ALSTAMP": "a", "ALOJAMENTO": "BALCONY", "RESERVA": "HMEXP22AWD", "DATAIN": date(2026, 8, 31), "DATAOUT": date(2026, 9, 8), "NOITES": 8, "ADULTOS": 1, "CRIANCAS": 0}], date(2026, 9, 1), date(2026, 9, 30))
    assert not warnings
    assert rows[0]["noites_periodo"] == 7
    assert rows[0]["dormidas_acima_limite"] == 1


def test_casa_do_crasto_uses_three_night_limit():
    rows, _ = build_tourist_tax_rows([{"ALSTAMP": "a", "ALOJAMENTO": "Casa do Crasto", "RESERVA": "123", "DATAIN": date(2026, 9, 1), "DATAOUT": date(2026, 9, 6), "NOITES": 5, "ADULTOS": 2, "CRIANCAS": 0}], date(2026, 9, 1), date(2026, 9, 30))
    assert rows[0]["limite_noites"] == 3
    assert rows[0]["dormidas_acima_limite"] == 4


def test_quarter_bounds():
    assert period_bounds(2026, "trimestral", 3) == (date(2026, 7, 1), date(2026, 9, 30), "2026-Q3")


def test_delivery_type_filters_the_accommodations_from_al_configuration():
    source = [
        {"ALSTAMP": "a", "ALOJAMENTO": "BALCONY", "TAXATURPERIODO": "Mensal", "RESERVA": "H1", "DATAIN": date(2026, 9, 1), "DATAOUT": date(2026, 9, 3), "NOITES": 2, "ADULTOS": 1, "CRIANCAS": 0},
        {"ALSTAMP": "b", "ALOJAMENTO": "PORTO", "TAXATURPERIODO": "Trimestral", "RESERVA": "H2", "DATAIN": date(2026, 9, 1), "DATAOUT": date(2026, 9, 3), "NOITES": 2, "ADULTOS": 1, "CRIANCAS": 0},
    ]
    rows, _ = build_tourist_tax_rows(source, date(2026, 9, 1), date(2026, 9, 30), "Mensal")
    assert [row["alojamento"] for row in rows] == ["BALCONY"]


def test_internal_and_unknown_reservations_are_excluded_and_unknown_is_reported():
    source = [
        {"ALSTAMP": "a", "ALOJAMENTO": "BALCONY", "RESERVA": "I123", "DATAIN": date(2026, 9, 1), "DATAOUT": date(2026, 9, 2), "NOITES": 1, "ADULTOS": 1, "CRIANCAS": 0},
        {"ALSTAMP": "a", "ALOJAMENTO": "BALCONY", "RESERVA": "X123", "DATAIN": date(2026, 9, 1), "DATAOUT": date(2026, 9, 2), "NOITES": 1, "ADULTOS": 1, "CRIANCAS": 0},
    ]
    rows, warnings = build_tourist_tax_rows(source, date(2026, 9, 1), date(2026, 9, 30))
    assert rows == []
    assert len(warnings) == 1
    assert reservation_origin("123") == "Booking"


def test_amarante_location_uses_three_night_limit():
    assert night_limit("Outro alojamento", "AMARANTE", "") == 3


def test_unmapped_accommodation_is_excluded_and_reported():
    rows, warnings = build_tourist_tax_rows([
        {"ALSTAMP": "", "ALOJAMENTO": "Sem ficha AL", "RESERVA": "H123", "DATAIN": date(2026, 9, 1), "DATAOUT": date(2026, 9, 3), "NOITES": 2, "ADULTOS": 1, "CRIANCAS": 0},
    ], date(2026, 9, 1), date(2026, 9, 30))
    assert rows == []
    assert "sem correspondência em AL" in warnings[0]


def test_invalid_dates_are_excluded_and_reported():
    rows, warnings = build_tourist_tax_rows([
        {"ALSTAMP": "a", "ALOJAMENTO": "BALCONY", "RESERVA": "H123", "DATAIN": date(2026, 9, 3), "DATAOUT": date(2026, 9, 3), "NOITES": 1, "ADULTOS": 1, "CRIANCAS": 0},
    ], date(2026, 9, 1), date(2026, 9, 30))
    assert rows == []
    assert "datas/NOITES inválidas" in warnings[0]


def test_official_nights_are_used_and_incompatibility_is_reported():
    rows, warnings = build_tourist_tax_rows([
        {"ALSTAMP": "a", "ALOJAMENTO": "BALCONY", "RESERVA": "H123", "DATAIN": date(2026, 9, 1), "DATAOUT": date(2026, 9, 5), "NOITES": 3, "ADULTOS": 1, "CRIANCAS": 0},
    ], date(2026, 9, 1), date(2026, 9, 30))
    assert rows[0]["noites_periodo"] == 3
    assert "NOITES incompatível" in warnings[0]
