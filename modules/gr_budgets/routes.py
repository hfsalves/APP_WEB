from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from models import Acessos, db
from modules.gr_subcontractor_measurements.service import SubcontractorMeasurementsError

from .service import (
    BudgetsError,
    get_budget_detail,
    get_budget_series,
    list_budgets,
    list_companies_for_user,
)


bp = Blueprint(
    "gr_budgets",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/gr_budgets/static",
)


def _has_acl() -> bool:
    if getattr(current_user, "ADMIN", False) or getattr(current_user, "DEV", False):
        return True
    try:
        if list_companies_for_user(current_user):
            return True
    except Exception:
        pass
    login = (getattr(current_user, "LOGIN", "") or "").strip()
    if not login:
        return False
    aliases = ("GR_ORCAMENTOS", "ORCAMENTOS", "GR_BUDGETS", "DEVIS")
    rows = (
        Acessos.query.filter(Acessos.utilizador == login)
        .filter(db.func.upper(db.func.ltrim(db.func.rtrim(Acessos.tabela))).in_(aliases))
        .all()
    )
    return any(bool(getattr(row, "consultar", False)) for row in rows)


def _forbidden(api: bool = True):
    message = "Sem permissão para consultar orçamentos."
    return (jsonify({"error": message}), 403) if api else (message, 403)


def _handle_error(exc: Exception):
    if isinstance(exc, (BudgetsError, SubcontractorMeasurementsError)):
        return jsonify({"error": str(exc)}), getattr(exc, "status_code", 500)
    return jsonify({"error": str(exc)}), 500


@bp.route("/gr360_orcamentos")
@bp.route("/gr_orcamentos")
@bp.route("/orcamentos")
@login_required
def page():
    if not _has_acl():
        return _forbidden(api=False)
    return render_template("gr_budgets/budgets.html")


@bp.route("/api/gr_orcamentos/empresas")
@login_required
def api_companies():
    if not _has_acl():
        return _forbidden()
    try:
        return jsonify({"ok": True, "rows": list_companies_for_user(current_user)})
    except Exception as exc:
        return _handle_error(exc)


@bp.route("/api/gr_orcamentos/series")
@login_required
def api_series():
    if not _has_acl():
        return _forbidden()
    try:
        return jsonify({"ok": True, **get_budget_series(request.args.get("feid"), current_user)})
    except Exception as exc:
        return _handle_error(exc)


@bp.route("/api/gr_orcamentos/orcamentos")
@login_required
def api_budgets():
    if not _has_acl():
        return _forbidden()
    try:
        return jsonify({"ok": True, **list_budgets(request.args.to_dict(flat=True), current_user)})
    except Exception as exc:
        return _handle_error(exc)


@bp.route("/api/gr_orcamentos/orcamento")
@login_required
def api_budget_detail():
    if not _has_acl():
        return _forbidden()
    try:
        return jsonify(
            {
                "ok": True,
                **get_budget_detail(
                    request.args.get("feid"),
                    request.args.get("bostamp") or "",
                    current_user,
                ),
            }
        )
    except Exception as exc:
        return _handle_error(exc)

