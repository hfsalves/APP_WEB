from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from io import BytesIO

from flask import Blueprint, abort, current_app, jsonify, make_response, render_template, request, send_file
from flask_login import current_user, login_required
from sqlalchemy import text

from models import db
from services.employee_insurance_service import (
    ACCESS_TABLE,
    audit_consultation,
    build_employee_insurance_workbook,
    employee_insurance_report,
    profession_mappings,
    record_issue,
    save_profession_mapping,
)


bp = Blueprint("employee_insurance", __name__)


def _has_access(permission: str = "CONSULTAR") -> bool:
    if bool(getattr(current_user, "ADMIN", False)):
        return True
    login = str(getattr(current_user, "LOGIN", "") or "").strip()
    if not login:
        return False
    allowed_column = permission if permission in {"CONSULTAR", "EDITAR"} else "CONSULTAR"
    return bool(db.session.execute(text(f"""
        SELECT TOP 1 1
        FROM dbo.ACESSOS
        WHERE LOWER(LTRIM(RTRIM(ISNULL(UTILIZADOR, '')))) = LOWER(:login)
          AND UPPER(LTRIM(RTRIM(ISNULL(TABELA, '')))) = :table_name
          AND ISNULL({allowed_column}, 0) = 1
    """), {"login": login, "table_name": ACCESS_TABLE}).scalar())


def _require(permission: str = "CONSULTAR") -> None:
    if not _has_access(permission):
        abort(403)


def _filters() -> dict[str, str]:
    return {
        "q": str(request.args.get("q") or "").strip()[:100],
        "nacionalidade": str(request.args.get("nacionalidade") or "").strip()[:60],
        "profissao": str(request.args.get("profissao") or "").strip()[:20],
        "ordenar": str(request.args.get("ordenar") or "nome").strip()[:30],
        "direcao": "desc" if str(request.args.get("direcao") or "").lower() == "desc" else "asc",
    }


def _json_value(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return value


def _private(response):
    response.headers["Cache-Control"] = "no-store, private, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@bp.route("/dashboard/mapa-seguradora")
@login_required
def page():
    _require()
    return _private(make_response(render_template(
        "employee_insurance.html",
        page_title="Mapa para seguradora",
        can_edit_professions=_has_access("EDITAR"),
    )))


@bp.route("/dashboard/api/mapa-seguradora")
@login_required
def api_report():
    _require()
    filters = _filters()
    try:
        report = employee_insurance_report(filters)
        audit_consultation(getattr(current_user, "LOGIN", ""), filters)
        public_report = {
            key: value for key, value in report.items()
            if key not in {"atuais_todos", "saidas_todas"}
        }
        return _private(jsonify({"ok": True, **_json_value(public_report)}))
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Erro ao gerar o mapa de funcionários para a seguradora.")
        return _private(jsonify({"ok": False, "error": "Não foi possível gerar o mapa para a seguradora."})), 500


@bp.route("/dashboard/api/mapa-seguradora/exportar")
@login_required
def export():
    _require()
    filters = _filters()
    scope = "visivel" if str(request.args.get("ambito") or "").lower() == "visivel" else "todos"
    try:
        report = employee_insurance_report(filters)
        rows = report["atuais"] if scope == "visivel" else report["atuais_todos"]
        departures = report["saidas"] if scope == "visivel" else report["saidas_todas"]
        report["ambito"] = scope
        content = build_employee_insurance_workbook(report, rows, departures)
        record_issue(getattr(current_user, "LOGIN", ""), report, filters, scope)
        filename = f"mapa-seguradora-guestspatur-{date.today().isoformat()}.xlsx"
        response = send_file(
            BytesIO(content), as_attachment=True, download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        return _private(response)
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Erro ao exportar o mapa de funcionários para a seguradora.")
        return _private(jsonify({"ok": False, "error": "Não foi possível exportar o mapa para a seguradora."})), 500


@bp.route("/dashboard/api/mapa-seguradora/profissoes", methods=["GET", "POST"])
@login_required
def professions():
    _require("EDITAR")
    if request.method == "GET":
        return _private(jsonify({"ok": True, "profissoes": profession_mappings()}))
    payload = request.get_json(silent=True) or {}
    try:
        save_profession_mapping(payload.get("codigo"), payload.get("descricao"), getattr(current_user, "LOGIN", ""))
        return _private(jsonify({"ok": True, "message": "Correspondência profissional guardada."}))
    except ValueError as exc:
        db.session.rollback()
        return _private(jsonify({"ok": False, "error": str(exc)})), 400
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Erro ao guardar a correspondência profissional.")
        return _private(jsonify({"ok": False, "error": "Não foi possível guardar a correspondência profissional."})), 500
