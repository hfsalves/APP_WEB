from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request, send_file
from flask_login import current_user, login_required

from models import Acessos, db
from modules.gr_subcontractor_measurements.service import SubcontractorMeasurementsError

from .service import (
    ClientMeasurementsError,
    create_measurement_auto,
    get_auto_attachment_file,
    get_budget_autos,
    get_budget_detail,
    list_budgets,
    list_companies_for_user,
)


bp = Blueprint("gr_client_measurements", __name__)


def _current_login() -> str:
    return (getattr(current_user, "LOGIN", "") or "").strip()


def _has_acl(action: str = "consultar") -> bool:
    if getattr(current_user, "ADMIN", False) or getattr(current_user, "DEV", False):
        return True
    if action == "consultar":
        try:
            if list_companies_for_user(current_user):
                return True
        except Exception:
            pass
    login = _current_login()
    if not login:
        return False
    aliases = (
        "CLIENT_AUTOS",
        "GR_AUTOS_CLIENTES",
        "AUTOS_CLIENTES",
        "GR_CLIENT_MEASUREMENTS",
    )
    rows = (
        Acessos.query.filter(Acessos.utilizador == login)
        .filter(db.func.upper(db.func.ltrim(db.func.rtrim(Acessos.tabela))).in_(aliases))
        .all()
    )
    return any(bool(getattr(row, action, False)) for row in rows)


def _forbidden():
    return jsonify({"error": "Sem permissao para consultar autos de clientes."}), 403


def _write_forbidden():
    return jsonify({"error": "Sem permissao para gravar autos de clientes."}), 403


def _handle_error(exc: Exception):
    if isinstance(exc, (ClientMeasurementsError, SubcontractorMeasurementsError)):
        return jsonify({"error": str(exc)}), getattr(exc, "status_code", 500)
    return jsonify({"error": str(exc)}), 500


@bp.route("/gr360_autos_clientes")
@bp.route("/gr_autos_clientes")
@bp.route("/autos_clientes")
@login_required
def page():
    if not _has_acl("consultar"):
        return ("Sem permissao para consultar autos de clientes.", 403)
    return render_template(
        "gr_subcontractor_measurements/autos_subempreitada.html",
        screen_title="Autos de Clientes",
        screen_breadcrumb="GR360 / SITUATIONS DE TRAVAUX CLIENTS",
        source_plural="Orçamentos",
        source_singular="Orçamento",
        source_total_label="Total orçamentado",
        source_value_label="Orçamentado",
        party_label="Cliente",
        party_placeholder="Nome ou numero",
        api_base="/api/gr_autos_clientes",
        write_enabled=True,
    )


@bp.route("/api/gr_autos_clientes/empresas")
@login_required
def api_companies():
    if not _has_acl("consultar"):
        return _forbidden()
    try:
        return jsonify({"ok": True, "rows": list_companies_for_user(current_user)})
    except Exception as exc:
        return _handle_error(exc)


@bp.route("/api/gr_autos_clientes/contratos")
@login_required
def api_budgets():
    if not _has_acl("consultar"):
        return _forbidden()
    try:
        filters = request.args.to_dict(flat=True)
        filters["cliente"] = filters.get("cliente") or filters.get("fornecedor") or ""
        return jsonify({"ok": True, **list_budgets(filters, current_user)})
    except Exception as exc:
        return _handle_error(exc)


@bp.route("/api/gr_autos_clientes/contrato")
@login_required
def api_budget_detail():
    if not _has_acl("consultar"):
        return _forbidden()
    try:
        return jsonify(
            {
                "ok": True,
                **get_budget_detail(request.args.get("feid"), request.args.get("bostamp") or "", current_user),
            }
        )
    except Exception as exc:
        return _handle_error(exc)


@bp.route("/api/gr_autos_clientes/autos", methods=["POST"])
@login_required
def api_create_auto():
    if not _has_acl("inserir"):
        return _write_forbidden()
    try:
        return jsonify({"ok": True, "auto": create_measurement_auto(request.get_json(silent=True) or {}, current_user)})
    except Exception as exc:
        return _handle_error(exc)


@bp.route("/api/gr_autos_clientes/autos", methods=["GET"])
@login_required
def api_budget_autos():
    if not _has_acl("consultar"):
        return _forbidden()
    try:
        return jsonify(
            {
                "ok": True,
                **get_budget_autos(request.args.get("feid"), request.args.get("bostamp") or "", current_user),
            }
        )
    except Exception as exc:
        return _handle_error(exc)


@bp.route("/api/gr_autos_clientes/anexo")
@login_required
def api_auto_attachment():
    if not _has_acl("consultar"):
        return _forbidden()
    try:
        file_info = get_auto_attachment_file(
            request.args.get("feid"), request.args.get("anexosstamp") or "", current_user
        )
        if file_info.get("mode") == "path":
            return send_file(
                file_info["path"],
                mimetype=file_info.get("mime") or "application/octet-stream",
                as_attachment=False,
                download_name=file_info.get("filename") or "anexo.pdf",
                max_age=0,
                conditional=True,
            )
        return send_file(
            file_info["stream"],
            mimetype=file_info.get("mime") or "application/octet-stream",
            as_attachment=False,
            download_name=file_info.get("filename") or "anexo.pdf",
            max_age=0,
        )
    except Exception as exc:
        return _handle_error(exc)
