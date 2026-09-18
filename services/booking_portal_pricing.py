"""Indicative nightly prices for public listings, not checkout totals."""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from sqlalchemy import bindparam, text

from models import db


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
    """One availability/price lookup per page; never recalculate or write prices."""
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
        prices.update(select_from_prices(rows, today))
    return prices
