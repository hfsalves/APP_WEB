from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from flask import Blueprint, Response, abort, jsonify, render_template, request, send_from_directory
from flask_login import current_user, login_required

from models import Acessos

from .service import (
    LEGACY_SCRIPT_FILES,
    LEGACY_STATIC_DIR,
    MONTHLY_SHEET_SCRIPT_FILES,
    MONTHLY_SHEET_INTERSOL_SCRIPT_FILES,
    build_planning_page,
    build_monthly_sheet_page,
    build_monthly_sheet_intersol_page,
    build_team_management_page,
    can_access_monitor,
    can_access_monthly_sheet,
    can_access_monthly_sheet_intersol,
    can_access_planning,
    can_access_team_management,
    fetch_gr_task_status_options,
    fetch_gr_monitor_tasks,
    get_api_access_scope,
    open_legacy_request,
    _parse_date_param,
    update_gr_task_status,
    TEAM_MANAGEMENT_SCRIPT_FILES,
)


bp = Blueprint(
    "gr_planning",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/gr_planning/static",
)


def _current_login_value() -> str:
    return (getattr(current_user, "LOGIN", "") or "").strip()


def _ensure_planning_access() -> dict:
    allowed, legacy_user = can_access_planning(_current_login_value())
    if not allowed or not legacy_user:
        abort(403)
    return legacy_user


def _ensure_team_management_access() -> dict:
    allowed, legacy_user = can_access_team_management(_current_login_value())
    if not allowed or not legacy_user:
        abort(403)
    return legacy_user


def _ensure_monthly_sheet_access() -> dict:
    allowed, legacy_user = can_access_monthly_sheet(_current_login_value())
    if not allowed or not legacy_user:
        abort(403)
    return legacy_user


def _ensure_monthly_sheet_intersol_access() -> dict:
    allowed, legacy_user = can_access_monthly_sheet_intersol(_current_login_value())
    if not allowed or not legacy_user:
        abort(403)
    return legacy_user


def _ensure_monitor_access() -> dict:
    if _has_app_task_access("consultar"):
        return {}
    allowed, legacy_user = can_access_monitor(_current_login_value())
    if not allowed or not legacy_user:
        abort(403)
    return legacy_user


def _ensure_monitor_edit_access() -> dict:
    if _has_app_task_access("editar"):
        return {}
    allowed, legacy_user = can_access_monitor(_current_login_value())
    if not allowed or not legacy_user:
        abort(403)
    return legacy_user


def _has_app_task_access(action: str = "consultar") -> bool:
    if getattr(current_user, "ADMIN", False) or getattr(current_user, "DEV", False):
        return True
    login = _current_login_value()
    if not login:
        return False
    row = Acessos.query.filter_by(utilizador=login, tabela="TAREFAS").first()
    return bool(row and getattr(row, action, False))


def _monitor_user_filter() -> str | None:
    if getattr(current_user, "ADMIN", False) or getattr(current_user, "DEV", False):
        return None
    return _current_login_value()


def _relay_legacy_response(legacy_response) -> Response:
    response = Response(
        legacy_response.get_data(),
        status=legacy_response.status_code,
        content_type=legacy_response.content_type,
    )
    for key, value in legacy_response.headers.items():
        lower = key.lower()
        if lower in {"content-length", "transfer-encoding", "content-type", "connection"}:
            continue
        response.headers[key] = value
    return response


@bp.route("/gr360_planning")
@bp.route("/gr_planning")
@login_required
def index():
    _ensure_planning_access()
    planning_html, page_meta = build_planning_page(_current_login_value())
    return render_template(
        "gr_planning/gr360_index.html",
        planning_html=planning_html,
        page_meta=page_meta,
        legacy_script_files=LEGACY_SCRIPT_FILES,
    )


@bp.route("/gr360_planning/teams")
@bp.route("/gr_planning/teams")
@login_required
def team_management():
    legacy_user = _ensure_team_management_access()
    team_management_html, page_meta = build_team_management_page(
        _current_login_value(),
        legacy_user=legacy_user,
    )
    return render_template(
        "gr_planning/team_management_index.html",
        team_management_html=team_management_html,
        page_meta=page_meta,
        legacy_script_files=TEAM_MANAGEMENT_SCRIPT_FILES,
    )


@bp.route("/gr360_planning/folha-mensal")
@bp.route("/gr_planning/folha-mensal")
@bp.route("/gr360_planning/monthly_sheet_index")
@bp.route("/gr_planning/monthly_sheet_index")
@login_required
def monthly_sheet():
    legacy_user = _ensure_monthly_sheet_access()
    monthly_html, page_meta = build_monthly_sheet_page(
        _current_login_value(),
        legacy_user=legacy_user,
    )
    return render_template(
        "gr_planning/monthly_sheet_index.html",
        monthly_html=monthly_html,
        page_meta=page_meta,
        legacy_script_files=MONTHLY_SHEET_SCRIPT_FILES,
    )


@bp.route("/gr360_planning/intersol/folha-mensal")
@bp.route("/gr_planning/intersol/folha-mensal")
@bp.route("/gr360_planning/folha-mensal-intersol")
@bp.route("/gr_planning/folha-mensal-intersol")
@bp.route("/gr360_planning/folha_mensal_intersol")
@bp.route("/gr_planning/folha_mensal_intersol")
@bp.route("/gr360_planning/monthly_sheet_intersol_index")
@bp.route("/gr_planning/monthly_sheet_intersol_index")
@login_required
def monthly_sheet_intersol():
    legacy_user = _ensure_monthly_sheet_intersol_access()
    monthly_html, page_meta = build_monthly_sheet_intersol_page(
        _current_login_value(),
        legacy_user=legacy_user,
    )
    return render_template(
        "gr_planning/monthly_sheet_intersol_index.html",
        monthly_html=monthly_html,
        page_meta=page_meta,
        legacy_script_files=MONTHLY_SHEET_INTERSOL_SCRIPT_FILES,
    )


@bp.route("/gr360_monitor")
@bp.route("/gr_monitor")
@bp.route("/gr_planning/monitor")
@login_required
def gr_monitor():
    _ensure_monitor_access()
    return render_template("gr_planning/gr_monitor.html")


@bp.route("/api/gr_planning/monitor/tasks")
@login_required
def gr_monitor_tasks():
    _ensure_monitor_access()
    today = date.today()
    start = _parse_date_param(request.args.get("start"), today - timedelta(days=30))
    end = _parse_date_param(request.args.get("end"), today + timedelta(days=60))
    return jsonify({
        "rows": fetch_gr_monitor_tasks(
            start_date=start,
            end_date=end,
            user_code=_monitor_user_filter(),
        ),
    })


@bp.route("/api/gr_planning/monitor/status-options")
@login_required
def gr_monitor_status_options():
    _ensure_monitor_access()
    return jsonify({"rows": fetch_gr_task_status_options()})


@bp.route("/api/gr_planning/monitor/tasks/<task_id>/status", methods=["POST"])
@login_required
def gr_monitor_task_status(task_id: str):
    _ensure_monitor_edit_access()
    body = request.get_json(silent=True) or {}
    try:
        status_code = int(body.get("status_code"))
        user_login = (getattr(current_user, "LOGIN", "") or "").strip()
        return jsonify(update_gr_task_status(
            task_id,
            status_code,
            user_login=user_login,
            restrict_user_code=_monitor_user_filter(),
        ))
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@bp.route("/gr_planning/legacy-static/<path:filename>")
@login_required
def legacy_static(filename: str):
    safe_root = str(Path(LEGACY_STATIC_DIR).resolve())
    return send_from_directory(safe_root, filename)


@bp.route("/api/gr_planning/<path:legacy_path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@login_required
def legacy_api_proxy(legacy_path: str):
    api_scope = get_api_access_scope(legacy_path)
    if not api_scope:
        abort(404)
    if api_scope == "monthly_sheet":
        legacy_user = _ensure_monthly_sheet_access()
    elif api_scope == "monthly_sheet_intersol":
        legacy_user = _ensure_monthly_sheet_intersol_access()
    elif api_scope == "planning":
        legacy_user = _ensure_planning_access()
    elif api_scope == "team_management":
        legacy_user = _ensure_team_management_access()
    else:
        allowed, legacy_user = can_access_planning(_current_login_value())
        if not allowed or not legacy_user:
            allowed, legacy_user = can_access_monthly_sheet(_current_login_value())
        if not allowed or not legacy_user:
            allowed, legacy_user = can_access_monthly_sheet_intersol(_current_login_value())
        if not allowed or not legacy_user:
            allowed, legacy_user = can_access_team_management(_current_login_value())
        if not allowed or not legacy_user:
            abort(403)
    legacy_response = open_legacy_request(
        f"/api/{legacy_path}",
        login_value=_current_login_value(),
        method=request.method,
        query_string=request.args,
        data=request.get_data(),
        content_type=request.content_type,
        access_mode=api_scope,
        legacy_user=legacy_user,
    )
    return _relay_legacy_response(legacy_response)
