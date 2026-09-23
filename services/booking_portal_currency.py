"""PortoBreak presentation/payment currencies over an immutable EUR base."""

from __future__ import annotations

import logging
import threading
import time
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

from flask import current_app
from sqlalchemy import text

from models import db


ECB_DAILY_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
ECB_SOURCE = "ECB euro foreign exchange reference rates"
SUPPORTED_CURRENCIES = {
    "EUR": {"symbol": "€", "name": "Euro", "minor_units": 2, "symbol_position": "suffix"},
    "GBP": {"symbol": "£", "name": "Pound sterling", "minor_units": 2, "symbol_position": "prefix"},
    "USD": {"symbol": "$", "name": "US dollar", "minor_units": 2, "symbol_position": "prefix"},
}
EUROZONE_COUNTRIES = frozenset({
    "AT", "BE", "HR", "CY", "EE", "FI", "FR", "DE", "GR", "IE", "IT",
    "LV", "LT", "LU", "MT", "NL", "PT", "SK", "SI", "ES",
})
DEFAULT_MARGIN_PERCENT = Decimal("1.5000")
_DEC2 = Decimal("0.01")
_DEC4 = Decimal("0.0001")
_DEC8 = Decimal("0.00000001")
_WHOLE = Decimal("1")
_refresh_lock = threading.Lock()
_refresh_running = False
_last_freshness_check = 0.0


def _decimal(value, quantizer=_DEC2, default="0") -> Decimal:
    try:
        result = Decimal(str(value if value is not None else default))
        if not result.is_finite():
            raise InvalidOperation
        return result.quantize(quantizer, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default).quantize(quantizer, rounding=ROUND_HALF_UP)


def normalize_currency(value, default="EUR") -> str:
    code = str(value or "").strip().upper()
    return code if code in SUPPORTED_CURRENCIES else default


def detect_currency(country_code) -> str:
    country = str(country_code or "").strip().upper()
    if country == "GB":
        return "GBP"
    if country == "US":
        return "USD"
    return "EUR"


def _margin_percent() -> Decimal:
    try:
        row = db.session.execute(text("""
            SELECT TOP 1 NVALOR, CVALOR
            FROM dbo.PARA
            WHERE UPPER(LTRIM(RTRIM(PARAMETRO))) = 'FX_MARGIN_PERCENT'
        """)).mappings().first()
        value = (row or {}).get("NVALOR")
        if value is None:
            value = (row or {}).get("CVALOR")
    except Exception:
        db.session.rollback()
        value = None
    configured = current_app.config.get("PORTOBREAK_FX_MARGIN_PERCENT")
    margin = _decimal(value if value not in (None, "") else configured, _DEC4, str(DEFAULT_MARGIN_PERCENT))
    return min(Decimal("20.0000"), max(Decimal("0.0000"), margin))


def _rate_row(currency: str) -> dict | None:
    if currency == "EUR":
        today = datetime.now(timezone.utc).date().isoformat()
        return {"currency": "EUR", "rate": Decimal("1"), "rate_date": today, "source": ECB_SOURCE}
    try:
        row = db.session.execute(text("""
            SELECT TOP 1 MOEDA, TAXA_POR_EUR, DATA_TAXA, FONTE
            FROM dbo.PB_FX_RATES
            WHERE MOEDA = :currency AND ATIVA = 1 AND TAXA_POR_EUR > 0
        """), {"currency": currency}).mappings().first()
    except Exception:
        db.session.rollback()
        return None
    if not row:
        return None
    return {
        "currency": currency,
        "rate": _decimal(row.get("TAXA_POR_EUR"), _DEC8),
        "rate_date": str(row.get("DATA_TAXA") or "")[:10],
        "source": str(row.get("FONTE") or ECB_SOURCE)[:120],
    }


def load_currency_snapshot(currency) -> dict:
    requested = normalize_currency(currency)
    row = _rate_row(requested)
    if not row:
        requested = "EUR"
        row = _rate_row("EUR")
    margin = Decimal("0") if requested == "EUR" else _margin_percent()
    rate = _decimal(row["rate"], _DEC8)
    effective = (rate * (Decimal("1") + margin / Decimal("100"))).quantize(_DEC8, rounding=ROUND_HALF_UP)
    return {
        "code": requested,
        "symbol": SUPPORTED_CURRENCIES[requested]["symbol"],
        "rate": f"{rate:.8f}",
        "effective_rate": f"{effective:.8f}",
        "margin_percent": f"{margin:.4f}",
        "rate_date": row["rate_date"],
        "source": row["source"],
    }


def validate_currency_snapshot(value) -> dict | None:
    if not isinstance(value, dict):
        return None
    code = normalize_currency(value.get("code"), default="")
    if not code:
        return None
    rate = _decimal(value.get("rate"), _DEC8)
    effective = _decimal(value.get("effective_rate"), _DEC8)
    margin = _decimal(value.get("margin_percent"), _DEC4)
    if rate <= 0 or effective <= 0 or margin < 0 or margin > 20:
        return None
    return {
        "code": code,
        "symbol": SUPPORTED_CURRENCIES[code]["symbol"],
        "rate": f"{rate:.8f}",
        "effective_rate": f"{effective:.8f}",
        "margin_percent": f"{margin:.4f}",
        "rate_date": str(value.get("rate_date") or "")[:10],
        "source": str(value.get("source") or "")[:120],
    }


def convert_eur(value, snapshot: dict, *, whole=False) -> Decimal:
    amount = _decimal(value)
    effective = _decimal((snapshot or {}).get("effective_rate"), _DEC8, "1")
    code = normalize_currency((snapshot or {}).get("code"))
    precision = _WHOLE if whole else Decimal(1).scaleb(-SUPPORTED_CURRENCIES[code]["minor_units"])
    return (amount * effective).quantize(precision, rounding=ROUND_HALF_UP)


def format_money(value, currency, *, whole=False) -> str:
    code = normalize_currency(currency)
    details = SUPPORTED_CURRENCIES[code]
    decimals = 0 if whole else details["minor_units"]
    amount = _decimal(value, _WHOLE if whole else Decimal(1).scaleb(-decimals))
    number = f"{amount:.{decimals}f}"
    return (
        f"{number} {details['symbol']}"
        if details["symbol_position"] == "suffix"
        else f"{details['symbol']}{number}"
    )


def amount_to_minor_units(value, currency) -> int:
    code = normalize_currency(currency)
    factor = Decimal(10) ** SUPPORTED_CURRENCIES[code]["minor_units"]
    return int((_decimal(value) * factor).quantize(_WHOLE, rounding=ROUND_HALF_UP))


def convert_stay_breakdown(*, direct_nights, airbnb_nights, extra, cleaning, tourist_tax, snapshot) -> dict:
    code = normalize_currency((snapshot or {}).get("code"))
    precision = Decimal(1).scaleb(-SUPPORTED_CURRENCIES[code]["minor_units"])
    values = {
        "direct_nights": convert_eur(direct_nights, snapshot),
        "airbnb_nights": convert_eur(airbnb_nights, snapshot),
        "extra": convert_eur(extra, snapshot),
        "cleaning": convert_eur(cleaning, snapshot),
        "tourist_tax": convert_eur(tourist_tax, snapshot),
    }
    common = values["extra"] + values["cleaning"] + values["tourist_tax"]
    values["direct_total"] = (values["direct_nights"] + common).quantize(precision)
    values["airbnb_total"] = (values["airbnb_nights"] + common).quantize(precision)
    values["saving"] = (values["airbnb_total"] - values["direct_total"]).quantize(precision)
    values["currency"] = code
    return values


def parse_ecb_daily_xml(payload: bytes) -> tuple[date, dict[str, Decimal]]:
    root = ET.fromstring(payload)
    namespace = {"fx": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref"}
    cube = root.find(".//fx:Cube[@time]", namespace)
    if cube is None:
        raise ValueError("ECB response does not contain a reference date")
    rate_date = date.fromisoformat(str(cube.attrib.get("time") or ""))
    rates = {"EUR": Decimal("1.00000000")}
    for item in list(cube):
        code = str(item.attrib.get("currency") or "").upper()
        if code not in SUPPORTED_CURRENCIES or code == "EUR":
            continue
        rate = _decimal(item.attrib.get("rate"), _DEC8)
        if rate > 0:
            rates[code] = rate
    missing = set(SUPPORTED_CURRENCIES) - set(rates)
    if missing:
        raise ValueError("ECB response is missing: " + ", ".join(sorted(missing)))
    return rate_date, rates


def fetch_ecb_daily(*, opener=urlopen) -> tuple[date, dict[str, Decimal]]:
    request = Request(ECB_DAILY_URL, headers={
        "User-Agent": "StationZero-PortoBreak/1.0",
        "Accept": "application/xml, text/xml;q=0.9",
    })
    with opener(request, timeout=15) as response:
        return parse_ecb_daily_xml(response.read())


def refresh_fx_rates(*, opener=urlopen) -> dict:
    """Atomically store a complete ECB snapshot; failed downloads preserve old rows."""
    rate_date, rates = fetch_ecb_daily(opener=opener)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for code, rate in rates.items():
        result = db.session.execute(text("""
            UPDATE dbo.PB_FX_RATES
            SET TAXA_POR_EUR = :rate, DATA_TAXA = :rate_date, ATUALIZADO_EM = :now,
                FONTE = :source, ATIVA = 1, ULTIMO_ERRO = NULL
            WHERE MOEDA = :currency
        """), {"currency": code, "rate": rate, "rate_date": rate_date, "now": now, "source": ECB_SOURCE})
        if result.rowcount == 0:
            db.session.execute(text("""
                INSERT INTO dbo.PB_FX_RATES
                    (MOEDA, TAXA_POR_EUR, DATA_TAXA, ATUALIZADO_EM, FONTE, ATIVA, ULTIMO_ERRO)
                VALUES (:currency, :rate, :rate_date, :now, :source, 1, NULL)
            """), {"currency": code, "rate": rate, "rate_date": rate_date, "now": now, "source": ECB_SOURCE})
    db.session.commit()
    return {"date": rate_date.isoformat(), "rates": {key: str(value) for key, value in rates.items()}}


def _record_refresh_error(exc: Exception) -> None:
    try:
        db.session.execute(text("""
            UPDATE dbo.PB_FX_RATES
            SET ULTIMO_ERRO = :error
            WHERE MOEDA IN ('EUR', 'GBP', 'USD')
        """), {"error": f"{type(exc).__name__}: {str(exc)}"[:1000]})
        db.session.commit()
    except Exception:
        db.session.rollback()


def _rates_are_fresh() -> bool:
    try:
        latest = db.session.execute(text("""
            SELECT MIN(ATUALIZADO_EM) FROM dbo.PB_FX_RATES
            WHERE ATIVA = 1 AND MOEDA IN ('EUR', 'GBP', 'USD')
        """)).scalar()
        count = int(db.session.execute(text("""
            SELECT COUNT(*) FROM dbo.PB_FX_RATES
            WHERE ATIVA = 1 AND MOEDA IN ('EUR', 'GBP', 'USD') AND TAXA_POR_EUR > 0
        """)).scalar() or 0)
    except Exception:
        db.session.rollback()
        return True  # Schema is deployed explicitly; never hammer ECB when it is absent.
    if count != 3 or not latest:
        return False
    if latest.tzinfo is not None:
        latest = latest.astimezone(timezone.utc).replace(tzinfo=None)
    return (datetime.now(timezone.utc).replace(tzinfo=None) - latest).total_seconds() < 20 * 60 * 60


def schedule_fx_refresh(app) -> None:
    """Start at most one non-blocking refresh after a local freshness check."""
    global _last_freshness_check, _refresh_running
    if app.testing:
        return
    now = time.monotonic()
    with _refresh_lock:
        if _refresh_running or now - _last_freshness_check < 300:
            return
        _last_freshness_check = now
    if _rates_are_fresh():
        return
    with _refresh_lock:
        if _refresh_running:
            return
        _refresh_running = True

    def worker():
        global _refresh_running
        try:
            with app.app_context():
                refresh_fx_rates()
        except Exception as exc:
            _record_refresh_error(exc)
            logging.getLogger("stationzero.portobreak.fx").warning(
                "PortoBreak ECB FX refresh failed; keeping last valid rates (%s)", type(exc).__name__
            )
        finally:
            try:
                with app.app_context():
                    db.session.remove()
            finally:
                with _refresh_lock:
                    _refresh_running = False

    threading.Thread(target=worker, name="portobreak-fx-refresh", daemon=True).start()
