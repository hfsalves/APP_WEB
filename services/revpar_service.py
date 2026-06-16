from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import date, datetime, timedelta
from functools import lru_cache

from flask_login import current_user
from sqlalchemy import text

from models import db


MONTHS_PT = [
    ("Jan", "Janeiro"),
    ("Fev", "Fevereiro"),
    ("Mar", "Marco"),
    ("Abr", "Abril"),
    ("Mai", "Maio"),
    ("Jun", "Junho"),
    ("Jul", "Julho"),
    ("Ago", "Agosto"),
    ("Set", "Setembro"),
    ("Out", "Outubro"),
    ("Nov", "Novembro"),
    ("Dez", "Dezembro"),
]


def _clean(value):
    return (str(value or "")).strip()


def _to_date(value):
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return value


def _float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _variation(current, previous):
    current = _float(current)
    previous = _float(previous)
    if abs(previous) < 0.005:
        return None
    return ((current - previous) / abs(previous)) * 100


def _days_in_month(year, month):
    return calendar.monthrange(year, month)[1]


def _safe_same_month_day(year, source_date):
    day = min(source_date.day, _days_in_month(year, source_date.month))
    return date(year, source_date.month, day)


def _month_bounds(year, month):
    return date(year, month, 1), date(year, month, _days_in_month(year, month))


def _available_nights_between(year, month, first_checkin, period_start=None, period_end=None):
    first_checkin = _to_date(first_checkin)
    if first_checkin is None:
        return 0

    month_start, month_end = _month_bounds(year, month)
    start = max(month_start, first_checkin, period_start or month_start)
    end = min(month_end, period_end or month_end)

    if end < start:
        return 0
    return (end - start).days + 1


def _month_available_nights(year, month, first_checkin):
    return _available_nights_between(year, month, first_checkin)


@lru_cache(maxsize=256)
def column_exists(table_name, column_name):
    sql = text(
        """
        SELECT 1
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = :table_name
          AND COLUMN_NAME = :column_name
        """
    )
    row = db.session.execute(
        sql,
        {"table_name": table_name.upper(), "column_name": column_name.upper()},
    ).first()
    return row is not None


def _is_admin_user():
    try:
        return bool(
            getattr(current_user, "admin", False)
            or getattr(current_user, "ADMIN", False)
            or getattr(current_user, "is_admin", False)
        )
    except Exception:
        return False


def _current_feid():
    for attr in ("feid", "FEID", "empresa", "EMPRESA"):
        value = getattr(current_user, attr, None)
        if value not in (None, ""):
            return value
    return None


def _al_filters(alias="AL", tipo=None, alojamento=None, params=None, scoped=True):
    params = params if params is not None else {}
    clauses = ["LTRIM(RTRIM(ISNULL({}.NOME, ''))) <> ''".format(alias)]

    tipo_clean = _clean(tipo).upper()
    if tipo_clean in ("GESTAO", "GESTÃO"):
        clauses.append("UPPER(LTRIM(RTRIM(ISNULL({}.TIPO, '')))) IN ('GESTAO', 'GESTÃO')".format(alias))
    elif tipo_clean in ("EXPLORACAO", "EXPLORAÇÃO"):
        clauses.append("UPPER(LTRIM(RTRIM(ISNULL({}.TIPO, '')))) IN ('EXPLORACAO', 'EXPLORAÇÃO')".format(alias))

    alojamento_clean = _clean(alojamento)
    if alojamento_clean:
        clauses.append(
            "LTRIM(RTRIM(ISNULL({}.NOME, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI = :alojamento COLLATE SQL_Latin1_General_CP1_CI_AI".format(
                alias
            )
        )
        params["alojamento"] = alojamento_clean

    feid = _current_feid()
    if scoped and feid and not _is_admin_user() and column_exists("AL", "FEID"):
        clauses.append("{}.FEID = :feid".format(alias))
        params["feid"] = feid

    return clauses


def _reservation_filters():
    return [
        "RS.DATAIN IS NOT NULL",
        "RS.DATAOUT IS NOT NULL",
        "CAST(RS.DATAOUT AS date) > CAST(RS.DATAIN AS date)",
        "ISNULL(RS.CANCELADA, 0) = 0",
        "ABS(((ISNULL(RS.ESTADIA, 0) + ISNULL(RS.LIMPEZA, 0)) / 1.06) - ISNULL(RS.COMISSAO, 0)) > 0.005",
    ]


def _join_al_rs():
    return """
    INNER JOIN dbo.AL AL
      ON LTRIM(RTRIM(ISNULL(AL.NOME, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI
       = LTRIM(RTRIM(ISNULL(RS.ALOJAMENTO, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI
    """


def list_revpar_alojamentos(tipo=None, alojamento=None):
    params = {}
    where = _al_filters("AL", tipo=tipo, alojamento=alojamento, params=params)
    sql = text(
        """
        SELECT
          LTRIM(RTRIM(ISNULL(AL.NOME, ''))) AS NOME,
          LTRIM(RTRIM(ISNULL(AL.TIPO, ''))) AS TIPO
        FROM dbo.AL AL
        WHERE {where}
        ORDER BY LTRIM(RTRIM(ISNULL(AL.NOME, '')))
        """.format(where=" AND ".join(where))
    )
    rows = db.session.execute(sql, params).mappings().all()
    return [{"nome": _clean(row["NOME"]), "tipo": _clean(row["TIPO"])} for row in rows]


def _first_checkins(tipo=None, alojamento=None):
    params = {}
    where = _reservation_filters()
    where.extend(_al_filters("AL", tipo=tipo, alojamento=alojamento, params=params))

    sql = text(
        """
        SELECT
          LTRIM(RTRIM(ISNULL(AL.NOME, ''))) AS ALOJAMENTO,
          MIN(CAST(RS.DATAIN AS date)) AS FIRST_CHECKIN
        FROM dbo.RS RS
        {join_al}
        WHERE {where}
        GROUP BY LTRIM(RTRIM(ISNULL(AL.NOME, '')))
        """.format(join_al=_join_al_rs(), where=" AND ".join(where))
    )
    rows = db.session.execute(sql, params).mappings().all()
    return {_clean(row["ALOJAMENTO"]): _to_date(row["FIRST_CHECKIN"]) for row in rows}


def _reservation_rows(year, tipo=None, alojamento=None):
    params = {
        "range_start": date(year - 1, 1, 1),
        "range_end": date(year + 1, 1, 1),
    }
    where = _reservation_filters()
    where.extend(
        [
            "CAST(RS.DATAIN AS date) < :range_end",
            "CAST(RS.DATAOUT AS date) > :range_start",
        ]
    )
    where.extend(_al_filters("AL", tipo=tipo, alojamento=alojamento, params=params))

    sql = text(
        """
        SELECT
          LTRIM(RTRIM(ISNULL(AL.NOME, ''))) AS ALOJAMENTO,
          LTRIM(RTRIM(ISNULL(AL.TIPO, ''))) AS TIPO,
          CAST(RS.DATAIN AS date) AS DATAIN,
          CAST(RS.DATAOUT AS date) AS DATAOUT,
          ISNULL(RS.ESTADIA, 0) AS ESTADIA,
          ISNULL(RS.LIMPEZA, 0) AS LIMPEZA,
          ISNULL(RS.COMISSAO, 0) AS COMISSAO
        FROM dbo.RS RS
        {join_al}
        WHERE {where}
        """.format(join_al=_join_al_rs(), where=" AND ".join(where))
    )
    return db.session.execute(sql, params).mappings().all()


def compute_revpar(year, tipo=None, alojamento=None):
    year = int(year)
    previous_year = year - 1
    today = date.today()
    is_ytd = year == today.year
    visible_last_month = today.month if is_ytd else 12
    visible_months = list(range(1, visible_last_month + 1))
    current_total_start = date(year, 1, 1)
    current_total_end = today if is_ytd else date(year, 12, 31)
    previous_total_start = date(previous_year, 1, 1)
    previous_total_end = _safe_same_month_day(previous_year, today) if is_ytd else date(previous_year, 12, 31)
    alojamentos = list_revpar_alojamentos(tipo=tipo, alojamento=alojamento)
    first_checkin = _first_checkins(tipo=tipo, alojamento=alojamento)
    revenue = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    total_revenue = defaultdict(lambda: {"current": 0.0, "previous": 0.0})

    range_start = date(previous_year, 1, 1)
    range_end = date(year + 1, 1, 1)

    for row in _reservation_rows(year, tipo=tipo, alojamento=alojamento):
        nome = _clean(row["ALOJAMENTO"])
        datain = _to_date(row["DATAIN"])
        dataout = _to_date(row["DATAOUT"])
        if not nome or not datain or not dataout or dataout <= datain:
            continue

        nights = (dataout - datain).days
        if nights <= 0:
            continue

        net_value = ((_float(row["ESTADIA"]) + _float(row["LIMPEZA"])) / 1.06) - _float(row["COMISSAO"])
        if abs(net_value) < 0.005:
            continue

        value_per_night = net_value / nights
        night = datain
        while night < dataout:
            if range_start <= night < range_end:
                if current_total_start <= night <= current_total_end:
                    total_revenue[nome]["current"] += value_per_night
                if previous_total_start <= night <= previous_total_end:
                    total_revenue[nome]["previous"] += value_per_night

                if night.year == year and night.month in visible_months:
                    if not is_ytd or night <= today:
                        revenue[nome][year][night.month] += value_per_night
                elif night.year == previous_year and night.month in visible_months:
                    revenue[nome][previous_year][night.month] += value_per_night
            night += timedelta(days=1)

    rows = []
    totals = {
        "current_revenue": 0.0,
        "previous_revenue": 0.0,
        "current_available": 0,
        "previous_available": 0,
        "months": [],
    }

    for month in visible_months:
        totals["months"].append(
            {
                "month": month,
                "current_revenue": 0.0,
                "previous_revenue": 0.0,
                "current_available": 0,
                "previous_available": 0,
            }
        )

    for al in alojamentos:
        nome = al["nome"]
        tipo_al = al["tipo"]
        first = first_checkin.get(nome)
        item = {
            "alojamento": nome,
            "tipo": tipo_al,
            "months": [],
            "current_revenue_total": 0.0,
            "previous_revenue_total": 0.0,
            "current_available_total": 0,
            "previous_available_total": 0,
        }

        for month in visible_months:
            current_revenue = revenue[nome][year][month]
            previous_revenue = revenue[nome][previous_year][month]
            current_month_start, current_month_end = _month_bounds(year, month)
            if is_ytd and month == today.month:
                current_month_end = today
            current_available = _available_nights_between(
                year,
                month,
                first,
                period_start=current_month_start,
                period_end=current_month_end,
            )
            previous_available = _month_available_nights(previous_year, month, first)
            current_revpar = current_revenue / current_available if current_available else 0.0
            previous_revpar = previous_revenue / previous_available if previous_available else 0.0

            item["current_available_total"] += _available_nights_between(
                year,
                month,
                first,
                period_start=current_total_start,
                period_end=current_total_end,
            )
            item["previous_available_total"] += _available_nights_between(
                previous_year,
                month,
                first,
                period_start=previous_total_start,
                period_end=previous_total_end,
            )

            totals_month = totals["months"][month - 1]
            totals_month["current_revenue"] += current_revenue
            totals_month["previous_revenue"] += previous_revenue
            totals_month["current_available"] += current_available
            totals_month["previous_available"] += previous_available

            item["months"].append(
                {
                    "month": month,
                    "current": round(current_revpar, 2),
                    "previous": round(previous_revpar, 2),
                    "delta_pct": _variation(current_revpar, previous_revpar),
                    "current_revenue": round(current_revenue, 2),
                    "previous_revenue": round(previous_revenue, 2),
                    "current_available": current_available,
                    "previous_available": previous_available,
                }
            )

        item["current_revenue_total"] = total_revenue[nome]["current"]
        item["previous_revenue_total"] = total_revenue[nome]["previous"]
        current_total = (
            item["current_revenue_total"] / item["current_available_total"]
            if item["current_available_total"]
            else 0.0
        )
        previous_total = (
            item["previous_revenue_total"] / item["previous_available_total"]
            if item["previous_available_total"]
            else 0.0
        )
        item["current_total"] = round(current_total, 2)
        item["previous_total"] = round(previous_total, 2)
        item["delta_total_pct"] = _variation(current_total, previous_total)
        item["current_revenue_total"] = round(item["current_revenue_total"], 2)
        item["previous_revenue_total"] = round(item["previous_revenue_total"], 2)
        rows.append(item)

    totals["current_revenue"] = sum(row["current_revenue_total"] for row in rows)
    totals["previous_revenue"] = sum(row["previous_revenue_total"] for row in rows)
    totals["current_available"] = sum(row["current_available_total"] for row in rows)
    totals["previous_available"] = sum(row["previous_available_total"] for row in rows)
    totals["current_revpar"] = (
        round(totals["current_revenue"] / totals["current_available"], 2)
        if totals["current_available"]
        else 0.0
    )
    totals["previous_revpar"] = (
        round(totals["previous_revenue"] / totals["previous_available"], 2)
        if totals["previous_available"]
        else 0.0
    )
    totals["delta_pct"] = _variation(totals["current_revpar"], totals["previous_revpar"])

    for month_total in totals["months"]:
        current_revpar = (
            month_total["current_revenue"] / month_total["current_available"]
            if month_total["current_available"]
            else 0.0
        )
        previous_revpar = (
            month_total["previous_revenue"] / month_total["previous_available"]
            if month_total["previous_available"]
            else 0.0
        )
        month_total["current"] = round(current_revpar, 2)
        month_total["previous"] = round(previous_revpar, 2)
        month_total["delta_pct"] = _variation(current_revpar, previous_revpar)
        month_total["current_revenue"] = round(month_total["current_revenue"], 2)
        month_total["previous_revenue"] = round(month_total["previous_revenue"], 2)

    return {
        "ano": year,
        "ano_anterior": previous_year,
        "is_ytd": is_ytd,
        "period": {
            "current_start": current_total_start.isoformat(),
            "current_end": current_total_end.isoformat(),
            "previous_start": previous_total_start.isoformat(),
            "previous_end": previous_total_end.isoformat(),
        },
        "months": [
            {"number": idx + 1, "short": short, "name": name}
            for idx, (short, name) in enumerate(MONTHS_PT)
            if (idx + 1) in visible_months
        ],
        "filters": {
            "tipo": _clean(tipo) or "Todos",
            "alojamento": _clean(alojamento),
        },
        "alojamentos": list_revpar_alojamentos(tipo=tipo),
        "rows": rows,
        "totals": totals,
    }
