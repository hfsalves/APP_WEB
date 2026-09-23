"""PortoBreak-only pricing derived from the channel nightly price source."""

from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_FLOOR, ROUND_HALF_UP
from zoneinfo import ZoneInfo

from sqlalchemy import bindparam, text

from models import db


PORTOBREAK_NIGHTLY_FACTOR = Decimal("0.96")
PORTOBREAK_MIN_NIGHTLY_SAVING = Decimal("1")
_MONEY = Decimal("0.01")
_WHOLE_EURO = Decimal("1")


def portobreak_nightly_price(airbnb_price) -> Decimal:
    """Return the PortoBreak rate for one night as a whole-euro amount.

    The theoretical direct rate is 96% of the Airbnb-equivalent rate. It is
    rounded to the nearest euro (ROUND_HALF_UP), then capped at the greatest
    whole-euro value that is at least EUR 1 below the source rate.

    A positive source price below EUR 1 cannot satisfy the minimum saving and
    is therefore returned as zero, which the public portal treats as unpriced.
    """
    try:
        source_price = Decimal(str(airbnb_price)).quantize(_MONEY, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")
    if not source_price.is_finite() or source_price <= 0:
        return Decimal("0")

    theoretical = (source_price * PORTOBREAK_NIGHTLY_FACTOR).quantize(
        _WHOLE_EURO,
        rounding=ROUND_HALF_UP,
    )
    maximum_with_minimum_saving = (source_price - PORTOBREAK_MIN_NIGHTLY_SAVING).quantize(
        _WHOLE_EURO,
        rounding=ROUND_FLOOR,
    )
    if maximum_with_minimum_saving < 0:
        return Decimal("0")
    return min(theoretical, maximum_with_minimum_saving)


AVAILABLE_PRICES_SQL = """
    SELECT
        LTRIM(RTRIM(AL.ALSTAMP)) AS al_id,
        D.[DATA] AS day,
        D.PRECO_FINAL AS price
    FROM dbo.AL AS AL
    INNER JOIN dbo.PR_CALC_DAY AS D
      ON LTRIM(RTRIM(ISNULL(D.AL_NOME, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI
       = LTRIM(RTRIM(ISNULL(AL.NOME, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI
    WHERE AL.ALSTAMP IN :al_ids
      AND LTRIM(RTRIM(ISNULL(AL.NOME, ''))) <> ''
      AND ISNULL(AL.INATIVO, 0) = 0
      AND ISNULL(AL.FECHADO, 0) = 0
      AND D.[DATA] >= :today
      AND D.PRECO_FINAL > 0
      AND NOT EXISTS (
          SELECT 1
          FROM dbo.RS AS RS
          WHERE LTRIM(RTRIM(ISNULL(RS.ALOJAMENTO, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI
              = LTRIM(RTRIM(ISNULL(AL.NOME, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI
            AND ISNULL(RS.CANCELADA, 0) = 0
            AND RS.DATAIN IS NOT NULL
            AND RS.DATAOUT IS NOT NULL
            AND CAST(RS.DATAIN AS date) <= D.[DATA]
            AND CAST(RS.DATAOUT AS date) > D.[DATA]
      )
"""

STAY_PRICES_SQL = """
    SELECT
        LTRIM(RTRIM(PA.AL_NOME)) AS property_name,
        PA.PRECO_BASE AS base_price,
        CAST(D.[DATA] AS date) AS day,
        D.PRECO_FINAL AS price
    FROM dbo.PR_ALOJAMENTO AS PA
    LEFT JOIN dbo.PR_CALC_DAY AS D
      ON LTRIM(RTRIM(D.AL_NOME)) = LTRIM(RTRIM(PA.AL_NOME))
     AND CAST(D.[DATA] AS date) >= :checkin
     AND CAST(D.[DATA] AS date) < :checkout
    WHERE LTRIM(RTRIM(PA.AL_NOME)) IN :property_names
      AND ISNULL(PA.ATIVO, 1) = 1
"""


def _source_price(value) -> Decimal:
    try:
        price = Decimal(str(value)).quantize(_MONEY, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.00")
    return price if price.is_finite() and price > 0 else Decimal("0.00")


def stay_price_comparison(airbnb_nightly_prices) -> dict | None:
    """Aggregate real source and direct nightly prices without reversing a formula."""
    source_prices = [_source_price(value) for value in (airbnb_nightly_prices or ())]
    if not source_prices or any(value <= 0 for value in source_prices):
        return None
    direct_prices = [portobreak_nightly_price(value) for value in source_prices]
    if any(value <= 0 for value in direct_prices):
        return None
    airbnb_total = sum(source_prices, Decimal("0.00")).quantize(_MONEY)
    direct_total = sum(direct_prices, Decimal("0.00")).quantize(_MONEY)
    return {
        "nights": len(source_prices),
        "airbnb": airbnb_total,
        "portobreak": direct_total,
        "saving": (airbnb_total - direct_total).quantize(_MONEY),
    }


def get_stay_price_comparisons(property_names, checkin: date, checkout: date) -> dict[str, dict]:
    """Load real nightly comparisons for a catalog page in one read-only query."""
    names = list(dict.fromkeys(str(value or "").strip() for value in (property_names or ())))
    names = [value for value in names if value]
    if not names or not isinstance(checkin, date) or not isinstance(checkout, date) or checkout <= checkin:
        return {}

    query = text(STAY_PRICES_SQL).bindparams(bindparam("property_names", expanding=True))
    rows = db.session.execute(query, {
        "property_names": names,
        "checkin": checkin,
        "checkout": checkout,
    }).mappings().all()
    base_prices = {}
    prices_by_property_day = {}
    display_names = {}
    for row in rows:
        property_name = str(row.get("property_name") or "").strip()
        if not property_name:
            continue
        key = property_name.casefold()
        display_names[key] = property_name
        base_prices[key] = _source_price(row.get("base_price"))
        day = row.get("day")
        if isinstance(day, datetime):
            day = day.date()
        if isinstance(day, date):
            prices_by_property_day[(key, day)] = _source_price(row.get("price"))

    result = {}
    for requested_name in names:
        key = requested_name.casefold()
        nightly = []
        day = checkin
        while day < checkout:
            nightly.append(prices_by_property_day.get((key, day)) or base_prices.get(key))
            day += timedelta(days=1)
        comparison = stay_price_comparison(nightly)
        if comparison:
            result[requested_name] = comparison
            canonical_name = display_names.get(key)
            if canonical_name:
                result[canonical_name] = comparison
    return result


def select_from_prices(rows, today: date) -> dict[str, Decimal]:
    """Choose the minimum within the FIRST available 30/60/90/all window.

    Rows must already exclude occupied nights. All future prices are considered
    in the final window, with no arbitrary one-year cut-off or base-price fallback.
    """
    selected = {}
    for row in rows:
        al_id = str(row.get("al_id") or "").strip()
        day = row.get("day")
        if isinstance(day, datetime):
            day = day.date()
        if not isinstance(day, date):
            try:
                day = date.fromisoformat(str(day or ""))
            except ValueError:
                continue
        offset = (day - today).days
        if not al_id or offset < 0:
            continue
        try:
            price = Decimal(str(row.get("price")))
        except (InvalidOperation, ValueError):
            continue
        if not price.is_finite() or price <= 0:
            continue
        window = 0 if offset < 30 else 1 if offset < 60 else 2 if offset < 90 else 3
        candidate = (window, price)
        if al_id not in selected or candidate < selected[al_id]:
            selected[al_id] = candidate
    return {al_id: value[1].quantize(Decimal("0.01")) for al_id, value in selected.items()}


def get_from_prices(al_ids, today: date | None = None) -> dict[str, Decimal]:
    """Return PortoBreak starting prices without modifying channel prices."""
    identifiers = list(dict.fromkeys(str(value or "").strip() for value in (al_ids or ())))
    identifiers = [value for value in identifiers if value]
    if not identifiers:
        return {}
    today = today or datetime.now(ZoneInfo("Europe/Lisbon")).date()
    query = text(AVAILABLE_PRICES_SQL).bindparams(bindparam("al_ids", expanding=True))
    prices = {}
    # Protect SQL Server's parameter limit for callers requesting a whole catalog.
    for start in range(0, len(identifiers), 500):
        rows = db.session.execute(query, {
            "al_ids": identifiers[start:start + 500], "today": today,
        }).mappings().all()
        selected = select_from_prices(rows, today)
        prices.update({
            al_id: direct_price
            for al_id, source_price in selected.items()
            if (direct_price := portobreak_nightly_price(source_price)) > 0
        })
    return prices
