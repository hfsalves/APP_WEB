from __future__ import annotations

from datetime import date

from flask import Blueprint, abort, render_template, request, url_for

from services.booking_portal_service import (
    alojamento_disponivel,
    calcular_preco,
    get_alojamento,
    get_alojamentos_disponiveis,
    get_noites_ocupadas,
)


bp = Blueprint("booking_portal", __name__)


def _parse_date_arg(name: str):
    value = str(request.args.get(name) or "").strip()
    if not value:
        return None, ""
    try:
        return date.fromisoformat(value), ""
    except Exception:
        return None, "Data invalida."


def _parse_hospedes_arg():
    value = str(request.args.get("hospedes") or "").strip()
    if not value:
        return None, ""
    try:
        number = int(value)
        if number <= 0 or number > 50:
            return None, "Indique um numero de hospedes valido."
        return number, ""
    except Exception:
        return None, "Indique um numero de hospedes valido."


def _search_params():
    checkin, checkin_error = _parse_date_arg("checkin")
    checkout, checkout_error = _parse_date_arg("checkout")
    hospedes, hospedes_error = _parse_hospedes_arg()
    query = str(request.args.get("q") or request.args.get("query") or "").strip()

    errors = []
    for error in (checkin_error, checkout_error, hospedes_error):
        if error and error not in errors:
            errors.append(error)

    if (checkin and not checkout) or (checkout and not checkin):
        errors.append("Indique as datas de check-in e check-out.")
    if checkin and checkout and checkout <= checkin:
        errors.append("A data de check-out deve ser posterior ao check-in.")

    return {
        "checkin": checkin,
        "checkout": checkout,
        "hospedes": hospedes,
        "query": query,
        "errors": errors,
        "has_search": any([checkin, checkout, hospedes, query]),
        "raw": {
            "checkin": request.args.get("checkin", ""),
            "checkout": request.args.get("checkout", ""),
            "hospedes": request.args.get("hospedes", ""),
            "query": query,
        },
    }


def _detail_url(al_id: str, params: dict):
    query = {}
    for key in ("checkin", "checkout", "hospedes"):
        value = (params.get("raw") or {}).get(key)
        if value:
            query[key] = value
    return url_for("booking_portal.detail", al_id=al_id, **query)


@bp.route("/portal-reservas")
@bp.route("/reservas")
def index():
    params = _search_params()
    query_allowed = not params["errors"]
    alojamentos = get_alojamentos_disponiveis(
        checkin=params["checkin"] if query_allowed else None,
        checkout=params["checkout"] if query_allowed else None,
        hospedes=params["hospedes"] if query_allowed else None,
        query=params["query"] if query_allowed else None,
    )
    for alojamento in alojamentos:
        alojamento["detail_url"] = _detail_url(alojamento["id"], params)

    return render_template(
        "booking_portal/index.html",
        alojamentos=alojamentos,
        search=params,
        page_title="Reservas",
    )


@bp.route("/portal-reservas/alojamento/<al_id>")
@bp.route("/reservas/<al_id>")
def detail(al_id):
    params = _search_params()
    alojamento = get_alojamento(al_id)
    if not alojamento:
        abort(404)

    disponibilidade = None
    preco = calcular_preco(al_id, params["checkin"], params["checkout"], params["hospedes"])
    if params["checkin"] and params["checkout"] and not params["errors"]:
        disponibilidade = alojamento_disponivel(al_id, params["checkin"], params["checkout"])

    calendar_start = (params["checkin"] or date.today()).replace(day=1)
    calendario = {
        "initial_month": calendar_start.isoformat(),
        "occupied": get_noites_ocupadas(al_id, start=calendar_start, months=12),
    }

    return render_template(
        "booking_portal/detail.html",
        alojamento=alojamento,
        search=params,
        disponibilidade=disponibilidade,
        preco=preco,
        calendario=calendario,
        page_title=alojamento["nome"],
    )
