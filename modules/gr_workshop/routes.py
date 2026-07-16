from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from models import Acessos, db

from .service import (
    WORKSHOP_STATES,
    WorkshopError,
    annul_sheet,
    assign_sheet_mechanic,
    ensure_schema_available,
    get_sheet,
    list_mechanics,
    list_planning_week,
    list_articles,
    list_sheets,
    list_vehicles,
    list_work_types,
    plan_sheet,
    save_sheet,
    save_work_type,
    suggest_workshop_job,
    unplan_sheet,
    workshop_ai_available,
)


bp = Blueprint(
    "gr_workshop",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/gr_workshop/static",
)


def _current_login() -> str:
    return (getattr(current_user, "LOGIN", "") or "").strip()


def _has_acl(table_name: str, action: str = "consultar") -> bool:
    if getattr(current_user, "ADMIN", False) or getattr(current_user, "DEV", False):
        return True
    login = _current_login()
    if not login:
        return False
    row = (
        Acessos.query.filter(Acessos.utilizador == login)
        .filter(db.func.upper(db.func.ltrim(db.func.rtrim(Acessos.tabela))) == str(table_name or "").strip().upper())
        .first()
    )
    return bool(row and getattr(row, action, False))


def _can_sheet(action: str = "consultar") -> bool:
    return _has_acl("OFICINA_FOLHA", action) or _has_acl("oficina", action) or _has_acl("gr_oficina", action)


def _can_work_type(action: str = "consultar") -> bool:
    return _has_acl("OFICINA_TRAB", action) or _can_sheet(action)


def _forbidden():
    return jsonify({"error": "Sem permissão para aceder à folha de obra de oficina."}), 403


def _handle_error(exc: Exception):
    if isinstance(exc, WorkshopError):
        return jsonify({"error": str(exc)}), getattr(exc, "status_code", 500)
    return jsonify({"error": str(exc)}), 500


@bp.route("/gr360_oficina")
@bp.route("/gr_oficina")
@bp.route("/oficina")
@login_required
def workshop_page():
    if not _can_sheet("consultar"):
        return ("Sem permissão para consultar folhas de obra.", 403)
    return render_template("gr_workshop/oficina.html", states=WORKSHOP_STATES)


@bp.route("/gr360_oficina/planeamento")
@bp.route("/gr_oficina/planeamento")
@bp.route("/oficina/planeamento")
@login_required
def workshop_planning_page():
    if not _can_sheet("consultar"):
        return ("Sem permissão para consultar planeamento de oficina.", 403)
    return render_template("gr_workshop/planeamento_oficina.html")


@bp.route("/api/gr_oficina/meta")
@login_required
def api_meta():
    if not _can_sheet("consultar"):
        return _forbidden()
    try:
        ensure_schema_available()
        return jsonify(
            {
                "ok": True,
                "states": WORKSHOP_STATES,
                "mechanics": list_mechanics(),
                "permissions": {
                    "insert": _can_sheet("inserir"),
                    "edit": _can_sheet("editar"),
                    "delete": _can_sheet("eliminar"),
                    "workTypes": _can_work_type("editar") or _can_work_type("inserir"),
                    "aiSuggestion": workshop_ai_available() and (_can_sheet("inserir") or _can_sheet("editar")),
                },
            }
        )
    except Exception as exc:
        return _handle_error(exc)


@bp.route("/api/gr_oficina/vehicles")
@login_required
def api_vehicles():
    if not _can_sheet("consultar"):
        return _forbidden()
    try:
        return jsonify({"ok": True, "rows": list_vehicles(request.args.get("q") or "")})
    except Exception as exc:
        return _handle_error(exc)


@bp.route("/api/gr_oficina/artigos")
@login_required
def api_articles():
    if not _can_sheet("consultar"):
        return _forbidden()
    try:
        return jsonify({"ok": True, "rows": list_articles(request.args.get("q") or "")})
    except Exception as exc:
        return _handle_error(exc)


@bp.route("/api/gr_oficina/mecanicos")
@login_required
def api_mechanics():
    if not _can_sheet("consultar"):
        return _forbidden()
    try:
        ensure_schema_available()
        return jsonify({"ok": True, "rows": list_mechanics()})
    except Exception as exc:
        return _handle_error(exc)


@bp.route("/api/gr_oficina/trabalhos", methods=["GET", "POST"])
@login_required
def api_work_types():
    if request.method == "GET":
        if not _can_sheet("consultar"):
            return _forbidden()
        try:
            include_inactive = str(request.args.get("include_inactive") or "").strip().lower() in {"1", "true", "yes"}
            return jsonify(
                {
                    "ok": True,
                    "rows": list_work_types(request.args.get("q") or "", include_inactive=include_inactive),
                }
            )
        except Exception as exc:
            return _handle_error(exc)

    if not (_can_work_type("inserir") or _can_work_type("editar")):
        return _forbidden()
    try:
        payload = request.get_json(silent=True) or {}
        return jsonify({"ok": True, **save_work_type(payload, _current_login())})
    except Exception as exc:
        return _handle_error(exc)


@bp.route("/api/gr_oficina/trabalhos/<stamp>", methods=["PUT"])
@login_required
def api_work_type_detail(stamp: str):
    if not _can_work_type("editar"):
        return _forbidden()
    try:
        payload = request.get_json(silent=True) or {}
        return jsonify({"ok": True, **save_work_type(payload, _current_login(), stamp=stamp)})
    except Exception as exc:
        return _handle_error(exc)


@bp.route("/api/gr_oficina/ai/sugestao", methods=["POST"])
@login_required
def api_ai_suggestion():
    if not (_can_sheet("inserir") or _can_sheet("editar")):
        return _forbidden()
    try:
        payload = request.get_json(silent=True) or {}
        return jsonify({"ok": True, "suggestion": suggest_workshop_job(payload)})
    except Exception as exc:
        return _handle_error(exc)


@bp.route("/api/gr_oficina/folhas", methods=["GET", "POST"])
@login_required
def api_sheets():
    if request.method == "GET":
        if not _can_sheet("consultar"):
            return _forbidden()
        try:
            return jsonify({"ok": True, **list_sheets(request.args.to_dict(flat=True))})
        except Exception as exc:
            return _handle_error(exc)

    if not (_can_sheet("inserir") or _can_sheet("editar")):
        return _forbidden()
    try:
        payload = request.get_json(silent=True) or {}
        return jsonify({"ok": True, **save_sheet(payload, _current_login())})
    except Exception as exc:
        return _handle_error(exc)


@bp.route("/api/gr_oficina/folhas/<stamp>", methods=["GET", "PUT", "DELETE"])
@login_required
def api_sheet_detail(stamp: str):
    if request.method == "GET":
        if not _can_sheet("consultar"):
            return _forbidden()
        try:
            return jsonify({"ok": True, **get_sheet(stamp)})
        except Exception as exc:
            return _handle_error(exc)

    if request.method == "DELETE":
        if not _can_sheet("eliminar"):
            return _forbidden()
        try:
            return jsonify({"ok": True, **annul_sheet(stamp, _current_login())})
        except Exception as exc:
            return _handle_error(exc)

    if not _can_sheet("editar"):
        return _forbidden()
    try:
        payload = request.get_json(silent=True) or {}
        return jsonify({"ok": True, **save_sheet(payload, _current_login(), stamp=stamp)})
    except Exception as exc:
        return _handle_error(exc)


@bp.route("/api/gr_oficina/planeamento", methods=["GET"])
@login_required
def api_planning_week():
    if not _can_sheet("consultar"):
        return _forbidden()
    try:
        return jsonify({"ok": True, **list_planning_week(request.args.to_dict(flat=True))})
    except Exception as exc:
        return _handle_error(exc)


@bp.route("/api/gr_oficina/planeamento/<stamp>", methods=["PUT", "DELETE"])
@login_required
def api_plan_sheet(stamp: str):
    if not _can_sheet("editar"):
        return _forbidden()
    try:
        if request.method == "DELETE":
            return jsonify({"ok": True, **unplan_sheet(stamp, _current_login())})
        payload = request.get_json(silent=True) or {}
        return jsonify({"ok": True, **plan_sheet(stamp, payload, _current_login())})
    except Exception as exc:
        return _handle_error(exc)


@bp.route("/api/gr_oficina/planeamento/<stamp>/mecanico", methods=["PUT"])
@login_required
def api_plan_sheet_mechanic(stamp: str):
    if not _can_sheet("editar"):
        return _forbidden()
    try:
        payload = request.get_json(silent=True) or {}
        return jsonify({"ok": True, **assign_sheet_mechanic(stamp, payload, _current_login())})
    except Exception as exc:
        return _handle_error(exc)
