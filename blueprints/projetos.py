from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from models import Acessos
from services.project_service import (
    ProjectNotFoundError,
    ProjectServiceError,
    ProjectValidationError,
    get_project_detail,
    get_project_meta,
    get_project_task,
    list_projects,
    save_project,
    save_project_task,
)


bp = Blueprint("projetos", __name__)


def _has_acl(table_name, action="consultar"):
    if getattr(current_user, "ADMIN", False):
        return True
    acesso = Acessos.query.filter_by(utilizador=current_user.LOGIN, tabela=table_name).first()
    return bool(acesso and getattr(acesso, action, False))


def _can_projects(action="consultar"):
    return any(_has_acl(name, action) for name in ("PROJ", "TAREFAS", "roadmap", "projetos"))


def _forbidden():
    return jsonify({"error": "Sem permissao para aceder ao modulo de projetos."}), 403


def _handle_service_error(exc):
    if isinstance(exc, ProjectValidationError):
        return jsonify({"error": str(exc)}), 400
    if isinstance(exc, ProjectNotFoundError):
        return jsonify({"error": str(exc)}), 404
    return jsonify({"error": str(exc)}), 500


@bp.route("/projetos")
@bp.route("/projetos_roadmap")
@bp.route("/roadmap")
@login_required
def projetos_page():
    if not _can_projects("consultar"):
        return ("Sem permissao para consultar projetos.", 403)
    return render_template("projetos.html", page_title="Projetos", page_name="Projetos")


@bp.route("/projetos/<projstamp>")
@bp.route("/projetos_roadmap/<projstamp>")
@bp.route("/roadmap/<projstamp>")
@login_required
def projeto_detail_page(projstamp):
    if not _can_projects("consultar"):
        return ("Sem permissao para consultar projetos.", 403)
    return render_template(
        "projeto_detalhe.html",
        page_title="Projeto",
        page_name="Projeto",
        projstamp=projstamp,
    )


@bp.route("/api/projetos/meta", methods=["GET"])
@login_required
def api_project_meta():
    if not _can_projects("consultar"):
        return _forbidden()
    try:
        return jsonify({"ok": True, "meta": get_project_meta()})
    except ProjectServiceError as exc:
        return _handle_service_error(exc)


@bp.route("/api/projetos", methods=["GET", "POST"])
@login_required
def api_projects():
    if request.method == "GET":
        if not _can_projects("consultar"):
            return _forbidden()
        try:
            args = request.args.to_dict(flat=True)
            args["current_user"] = getattr(current_user, "LOGIN", "") or ""
            return jsonify({"ok": True, **list_projects(args)})
        except ProjectServiceError as exc:
            return _handle_service_error(exc)

    if not (_can_projects("inserir") or _can_projects("editar")):
        return _forbidden()
    try:
        payload = request.get_json(silent=True) or {}
        return jsonify({"ok": True, **save_project(payload, getattr(current_user, "LOGIN", "") or "")})
    except ProjectServiceError as exc:
        return _handle_service_error(exc)


@bp.route("/api/projetos/<projstamp>", methods=["GET", "PUT"])
@login_required
def api_project_detail(projstamp):
    if request.method == "GET":
        if not _can_projects("consultar"):
            return _forbidden()
        try:
            return jsonify({"ok": True, **get_project_detail(projstamp)})
        except ProjectServiceError as exc:
            return _handle_service_error(exc)

    if not _can_projects("editar"):
        return _forbidden()
    try:
        payload = request.get_json(silent=True) or {}
        return jsonify(
            {
                "ok": True,
                **save_project(payload, getattr(current_user, "LOGIN", "") or "", projstamp=projstamp),
            }
        )
    except ProjectServiceError as exc:
        return _handle_service_error(exc)


@bp.route("/api/projetos/<projstamp>/tarefas", methods=["GET", "POST"])
@login_required
def api_project_tasks(projstamp):
    if request.method == "GET":
        if not _can_projects("consultar"):
            return _forbidden()
        try:
            detail = get_project_detail(projstamp)
            return jsonify({"ok": True, "tasks": detail["tasks"], "summary": detail["summary"]})
        except ProjectServiceError as exc:
            return _handle_service_error(exc)

    if not (_can_projects("editar") or _has_acl("TAREFAS", "inserir")):
        return _forbidden()
    try:
        payload = request.get_json(silent=True) or {}
        return jsonify(
            {
                "ok": True,
                **save_project_task(projstamp, payload, getattr(current_user, "LOGIN", "") or ""),
            }
        )
    except ProjectServiceError as exc:
        return _handle_service_error(exc)


@bp.route("/api/projetos/<projstamp>/tarefas/<tarefastamp>", methods=["GET", "PUT"])
@login_required
def api_project_task_detail(projstamp, tarefastamp):
    if request.method == "GET":
        if not _can_projects("consultar"):
            return _forbidden()
        try:
            return jsonify({"ok": True, **get_project_task(projstamp, tarefastamp)})
        except ProjectServiceError as exc:
            return _handle_service_error(exc)

    if not (_can_projects("editar") or _has_acl("TAREFAS", "editar")):
        return _forbidden()
    try:
        payload = request.get_json(silent=True) or {}
        return jsonify(
            {
                "ok": True,
                **save_project_task(
                    projstamp,
                    payload,
                    getattr(current_user, "LOGIN", "") or "",
                    tarefastamp=tarefastamp,
                ),
            }
        )
    except ProjectServiceError as exc:
        return _handle_service_error(exc)
