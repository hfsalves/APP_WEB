from datetime import date

from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required

from services.revpar_service import compute_revpar, list_revpar_alojamentos


bp = Blueprint("analytics_revpar", __name__)


def _selected_year():
    raw_year = request.args.get("ano", type=int)
    if raw_year and 2000 <= raw_year <= 2100:
        return raw_year
    return date.today().year


@bp.route("/analytics/revpar")
@login_required
def revpar_page():
    selected_year = _selected_year()
    current_year = date.today().year
    years = list(range(current_year + 1, current_year - 7, -1))
    if selected_year not in years:
        years.insert(0, selected_year)

    return render_template(
        "analytics_revpar.html",
        ano=selected_year,
        anos=years,
        tipo=request.args.get("tipo", "Todos"),
        alojamento=request.args.get("alojamento", ""),
    )


@bp.route("/api/analytics/revpar")
@login_required
def api_revpar_data():
    selected_year = _selected_year()
    tipo = request.args.get("tipo", "Todos")
    alojamento = request.args.get("alojamento", "")

    try:
        data = compute_revpar(selected_year, tipo=tipo, alojamento=alojamento)
        return jsonify({"ok": True, "data": data})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@bp.route("/api/analytics/revpar/alojamentos")
@login_required
def api_revpar_alojamentos():
    tipo = request.args.get("tipo", "Todos")
    try:
        return jsonify({"ok": True, "alojamentos": list_revpar_alojamentos(tipo=tipo)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
