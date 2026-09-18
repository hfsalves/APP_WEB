"""Read-only, unpaginated map inventory with approximate public coordinates.

One inventory query and, only for valid date searches, one reservation query.
No prices, photographs, descriptions, guest records or exact addresses are
loaded. Availability is evaluated afresh; a map marker is not a booking hold.
"""

from collections import defaultdict
from datetime import date
import math

from sqlalchemy import text

from models import db
from services.booking_portal_service import (
    _add_months,
    _alojamento_adult_capacity_sql,
    _alojamento_capacity_sql,
    _range_touches_medium_high_season,
    _to_date,
)


_PUBLIC_WHERE = """
    LTRIM(RTRIM(ISNULL(AL.ALSTAMP, ''))) <> ''
    AND LTRIM(RTRIM(ISNULL(AL.NOME, ''))) <> ''
    AND ISNULL(AL.INATIVO, 0) = 0
    AND ISNULL(AL.FECHADO, 0) = 0
"""
_SEARCH_COLUMNS = ("NOME", "NMAIRBNB", "NMPESQUISA", "LOCAL", "MORADA", "ZONA")


def _inventory_sql(has_query):
    # Compute the same CI/AI LIKE match in SQL without returning private search
    # fields (including the exact address or the internal reservation name).
    matches = " OR ".join(
        f"LTRIM(RTRIM(ISNULL(AL.{column}, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI "
        "LIKE :query COLLATE SQL_Latin1_General_CP1_CI_AI"
        for column in _SEARCH_COLUMNS
    ) if has_query else "1 = 1"
    return f"""
        SELECT
            LTRIM(RTRIM(AL.ALSTAMP)) AS ID,
            COALESCE(NULLIF(LTRIM(RTRIM(ISNULL(AL.NMAIRBNB, ''))), ''),
                     LTRIM(RTRIM(ISNULL(AL.NOME, '')))) AS PUBLIC_NAME,
            AL.LAT, AL.LON,
            ISNULL(AL.INATIVO, 0) AS INATIVO,
            ISNULL(AL.FECHADO, 0) AS FECHADO,
            CAST(({_alojamento_adult_capacity_sql()}) AS int) AS ADULT_CAPACITY,
            CAST(({_alojamento_capacity_sql()}) AS int) AS TOTAL_CAPACITY,
            CAST(ISNULL(AL.NOITES, 1) AS int) AS MIN_NIGHTS,
            CASE WHEN ({matches}) THEN 1 ELSE 0 END AS QUERY_MATCH
        FROM dbo.AL AS AL
        WHERE {_PUBLIC_WHERE}
        ORDER BY PUBLIC_NAME, ID
    """


_INTERVAL_SQL = f"""
    SELECT
        LTRIM(RTRIM(AL.ALSTAMP)) AS ID,
        CAST(RS.DATAIN AS date) AS DATAIN,
        CAST(RS.DATAOUT AS date) AS DATAOUT
    FROM dbo.AL AS AL
    INNER JOIN dbo.RS AS RS ON
        LTRIM(RTRIM(ISNULL(RS.ALOJAMENTO, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI
        = LTRIM(RTRIM(ISNULL(AL.NOME, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI
    WHERE {_PUBLIC_WHERE}
      AND RS.DATAIN IS NOT NULL
      AND RS.DATAOUT IS NOT NULL
      AND ISNULL(RS.CANCELADA, 0) = 0
      AND CAST(RS.DATAIN AS date) < :query_end
      AND CAST(RS.DATAOUT AS date) > :query_start
"""


def _count(value):
    """Counts from parsed search parameters or the database, never floats."""
    if value is None or value == "":
        return 0
    try:
        number = int(str(value).strip())
        return number if number >= 0 else None
    except (ValueError, TypeError):
        return None


def _truthy_flag(value):
    return value is True or str(value or "").strip().lower() in {"1", "true", "yes"}


def _coordinate(value, limit):
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(str(value).strip().replace(",", "."))
    except (ValueError, TypeError, OverflowError):
        return None
    # Zero values are missing-coordinate sentinels in this portal's AL data,
    # matching booking_portal_service._to_float rather than placing them at sea.
    if not math.isfinite(number) or abs(number) > limit or abs(number) < 0.000001:
        return None
    return round(number, 3)


def _shift(day, offset):
    # Defensive saturation for corrupt minimum-night settings or extreme dates.
    ordinal = min(date.max.toordinal(), max(date.min.toordinal(), day.toordinal() + offset))
    return date.fromordinal(ordinal)


def _calendar_window(checkin, checkout):
    """Same month window as alojamento_datas_permitidas/get_calendario_ocupacao."""
    start = checkin.replace(day=1)
    months = max(2, (checkout.year - start.year) * 12 + checkout.month - start.month + 2)
    try:
        end = _add_months(start, months)
    except (ValueError, OverflowError):
        end = date.max
    return start, end


def _date_match(checkin, checkout, minimum_nights, intervals, window):
    """Evaluate only the requested interval; do not expand occupied calendars."""
    if (checkout - checkin).days < minimum_nights:
        return False
    gap = max(0, minimum_nights - 1)
    query_start = _shift(window[0], -gap)
    query_end = _shift(window[1], gap)
    for starts, ends in intervals:
        # Keep each property's exact existing calendar query boundaries even
        # though the bulk SQL uses the maximum gap across the whole inventory.
        if starts >= query_end or ends <= query_start:
            continue
        if starts < checkout and ends > checkin:
            return False
        checkin_gap = (checkin - ends).days
        if 1 <= checkin_gap <= gap and _range_touches_medium_high_season(ends, checkin):
            return False
        checkout_gap = (starts - checkout).days
        if 1 <= checkout_gap <= gap and _range_touches_medium_high_season(checkout, starts):
            return False
    return True


def _capacity_match(row, adults, children, guests, babies):
    # Babies do not consume the adults+children capacity. As in
    # _guest_constraints, up to two are allowed; crib availability is a note.
    if babies > 2:
        return False
    adult_capacity = _count(row.get("ADULT_CAPACITY")) or 0
    total_capacity = _count(row.get("TOTAL_CAPACITY")) or 0
    if adults:
        return adults <= adult_capacity and adults + children <= total_capacity
    if children:
        return children <= total_capacity
    if guests:
        return guests <= total_capacity
    return True


def get_map_catalog(params: dict) -> dict:
    """All public properties, blue for matches and grey for non-matches.

    ``total`` counts the full public inventory; ``items`` contains only valid
    georeferenced properties and ``matched`` counts blue markers in that list.
    No persistent cache is used. Exceptions propagate for the route's error UI.
    """
    query = str(params.get("query") or "").strip()
    counts = [_count(params.get(key)) for key in ("adultos", "criancas", "hospedes", "bebes")]
    adults, children, guests, babies = [value or 0 for value in counts]
    checkin = _to_date(params.get("checkin"))
    checkout = _to_date(params.get("checkout"))
    has_dates = bool(checkin and checkout and checkout > checkin)
    invalid_dates = bool(checkin or checkout or params.get("checkin") or params.get("checkout")) and not has_dates
    errors = bool(params.get("errors") or invalid_dates or None in counts)
    # _search_params rejects an unaccompanied child/baby. Preserve that safety
    # even when the helper is called directly with an incomplete parameter dict.
    errors = errors or bool((children or babies) and not adults)
    has_search = bool(params.get("has_search") or query or any(counts) or checkin or checkout or errors)

    rows = db.session.execute(text(_inventory_sql(bool(query))), {"query": f"%{query}%"} if query else {}).mappings().all()
    inventory = []
    seen = set()
    for row in rows:
        identifier = str(row.get("ID") or "").strip()
        name = str(row.get("PUBLIC_NAME") or "").strip()
        if not identifier or not name or identifier in seen or _truthy_flag(row.get("INATIVO")) or _truthy_flag(row.get("FECHADO")):
            continue
        seen.add(identifier)
        inventory.append(row)

    candidates = []
    for row in inventory:
        lat, lon = _coordinate(row.get("LAT"), 90), _coordinate(row.get("LON"), 180)
        if lat is not None and lon is not None:
            candidates.append((row, lat, lon))

    intervals = defaultdict(list)
    window = None
    if has_dates and not errors and candidates:
        window = _calendar_window(checkin, checkout)
        maximum_gap = max(max(1, _count(row.get("MIN_NIGHTS")) or 1) - 1 for row, _, _ in candidates)
        bookings = db.session.execute(text(_INTERVAL_SQL), {
            "query_start": _shift(window[0], -maximum_gap),
            "query_end": _shift(window[1], maximum_gap),
        }).mappings().all()
        for booking in bookings:
            starts, ends = _to_date(booking.get("DATAIN")), _to_date(booking.get("DATAOUT"))
            if starts and ends and ends > starts and not _truthy_flag(booking.get("CANCELADA")):
                intervals[str(booking.get("ID") or "").strip()].append((starts, ends))

    items = []
    for row, lat, lon in candidates:
        identifier = str(row["ID"]).strip()
        available = not errors and (
            not has_search or (
                (not query or _truthy_flag(row.get("QUERY_MATCH")))
                and _capacity_match(row, adults, children, guests, babies)
                and (not has_dates or _date_match(
                    checkin, checkout, max(1, _count(row.get("MIN_NIGHTS")) or 1),
                    intervals[identifier], window,
                ))
            )
        )
        # Explicit allowlist is the privacy boundary. Do not return SQL rows.
        items.append({
            "id": identifier, "name": str(row["PUBLIC_NAME"]).strip(),
            "lat": lat, "lon": lon, "available": bool(available),
        })
    return {
        "items": items, "total": len(inventory),
        "matched": sum(item["available"] for item in items),
        "missing_coordinates": len(inventory) - len(items),
        "has_search": has_search, "has_dates": has_dates,
    }
