from datetime import date

from services.tourist_tax_service import build_tourist_tax_rows, period_bounds


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
