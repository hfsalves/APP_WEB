"""Explicit, dated payroll mappings. Unknown categories are never assumed zero."""
from __future__ import annotations

from datetime import date, timedelta
import json
import os

from flask import current_app


CATEGORIES = ("km", "ac_nacional", "ac_estrangeiro")
DEFAULT_CONFIG = {
    "HSOLS_PT": [{
        "version": "hsols-pt-2026-v1",
        "valid_from": "2026-01-01",
        "valid_to": "2026-12-31",
        "currency": "EUR",
        "codes": {"km": [60], "ac_nacional": None, "ac_estrangeiro": [40]},
    }],
}


class TravelMapsError(Exception):
    status_code = 400


class SourceUnavailable(TravelMapsError):
    status_code = 502


def period_bounds(year, month) -> tuple[date, date]:
    try:
        year, month = int(str(year)), int(str(month))
        if not 2000 <= year <= 2100:
            raise ValueError
        start = date(year, month, 1)
        end = date(year + (month == 12), 1 if month == 12 else month + 1, 1)
        return start, end
    except (TypeError, ValueError):
        raise TravelMapsError("Indique um ano entre 2000 e 2100 e um mês entre 1 e 12.") from None


def map_period(year, month):
    """Operational cycle, labelled by its closing/payroll month; both dates inclusive."""
    payroll_start, _ = period_bounds(year, month)
    previous = payroll_start - timedelta(days=1)
    return {'basis': '22_21', 'start': previous.replace(day=22).isoformat(),
            'end': payroll_start.replace(day=21).isoformat()}


def document_period(payroll):
    """Missing metadata denotes a historical calendar-month map, never a new cycle."""
    value = payroll.get('map_period')
    if value is not None:
        if value != map_period(payroll['year'], payroll['month']):
            raise TravelMapsError('Período do mapa inválido.')
        return dict(value)
    start, end = period_bounds(payroll['year'], payroll['month'])
    return {'basis': 'CALENDAR_MONTH', 'start': start.isoformat(), 'end': (end-timedelta(days=1)).isoformat()}


def map_bounds(payroll):
    """Half-open query/calendar bounds for the exact version being processed."""
    value = document_period(payroll)
    return date.fromisoformat(value['start']), date.fromisoformat(value['end'])+timedelta(days=1)


def payroll_rule(database: str, start: date, end: date) -> dict | None:
    raw = current_app.config.get("GR_TRAVEL_MAPS_CONFIG")
    if raw is None:
        raw = os.environ.get("GR_TRAVEL_MAPS_CONFIG")
    try:
        config = DEFAULT_CONFIG if raw is None else json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(config, dict):
            raise ValueError
        rules = config.get(database.upper(), [])
        if not isinstance(rules, list):
            raise ValueError
        matches = []
        for rule in rules:
            valid_from = date.fromisoformat(rule["valid_from"])
            valid_to = date.fromisoformat(rule["valid_to"])
            # A change within the month requires an explicit split, not a guessed rate/code.
            if valid_from < end and valid_to >= start:
                if valid_from > start or valid_to.toordinal() < end.toordinal() - 1:
                    raise TravelMapsError("O mapeamento muda durante este mês; configure um período mensal inequívoco.")
                matches.append(rule)
        if len(matches) > 1:
            raise ValueError
        if not matches:
            return None
        rule = matches[0]
        codes = rule["codes"]
        seen = set()
        clean = {}
        for category in CATEGORIES:
            values = codes.get(category)
            if values is not None:
                if not isinstance(values, list) or any(type(code) is not int or not 0 <= code <= 999 for code in values):
                    raise ValueError
                for code in values:
                    if code in seen:
                        raise ValueError
                    seen.add(code)
            clean[category] = values
        if rule["currency"] != "EUR" or not str(rule["version"]).strip():
            # This reader uses PRRE.ERE/ERVU. Other currencies need their own adapter.
            raise ValueError
        return {**rule, "codes": clean}
    except TravelMapsError:
        raise
    except (KeyError, TypeError, ValueError, AttributeError):
        raise TravelMapsError("Configuração de rubricas inválida ou sobreposta. Verifique GR_TRAVEL_MAPS_CONFIG.") from None
