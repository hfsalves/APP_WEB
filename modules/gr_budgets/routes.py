from __future__ import annotations

from flask import Blueprint, Response, jsonify, render_template, request
from flask_login import current_user, login_required

from models import Acessos, db
from modules.gr_subcontractor_measurements.service import SubcontractorMeasurementsError

from .service import (
    BudgetsError,
    get_budget_detail,
    get_budget_detail_by_number,
    get_budget_line_oci,
    get_budget_salespeople,
    get_budget_series,
    get_budget_technical_options,
    list_budgets,
    render_budget_pdf_html,
    list_companies_for_user,
    search_budget_clients,
)
from services.ft_pdf_service import generate_ft_pdf_bytes, generate_ft_pdf_bytes_xhtml2pdf


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


@bp.route("/api/gr_orcamentos/comerciais")
@login_required
def api_salespeople():
    if not _has_acl():
        return _forbidden()
    try:
        return jsonify({"ok": True, **get_budget_salespeople(request.args.get("feid"), current_user)})
    except Exception as exc:
        return _handle_error(exc)


@bp.route("/api/gr_orcamentos/clientes")
@login_required
def api_clients():
    if not _has_acl():
        return _forbidden()
    try:
        return jsonify(
            {
                "ok": True,
                **search_budget_clients(
                    request.args.get("feid"),
                    request.args.get("q") or "",
                    current_user,
                ),
            }
        )
    except Exception as exc:
        return _handle_error(exc)


@bp.route("/api/gr_orcamentos/opcoes-tecnicas")
@login_required
def api_technical_options():
    if not _has_acl():
        return _forbidden()
    try:
        return jsonify({"ok": True, **get_budget_technical_options(request.args.get("feid"), current_user)})
    except Exception as exc:
        return _handle_error(exc)


@bp.route("/api/gr_orcamentos/oci")
@login_required
def api_line_oci():
    if not _has_acl():
        return _forbidden()
    try:
        return jsonify(
            {
                "ok": True,
                **get_budget_line_oci(
                    request.args.get("feid"),
                    request.args.get("bistamp") or "",
                    current_user,
                ),
            }
        )
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


@bp.route("/api/gr_orcamentos/orcamento/<bostamp>/pdf/html")
@login_required
def api_budget_pdf_html(bostamp):
    if not _has_acl():
        return _forbidden()
    try:
        detail = get_budget_detail(request.args.get("feid"), bostamp, current_user)
        return Response(
            render_budget_pdf_html(detail, request.args.get("style")),
            content_type="text/html; charset=utf-8",
            headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
        )
    except Exception as exc:
        return _handle_error(exc)


@bp.route("/api/gr_orcamentos/orcamento/<bostamp>/pdf")
@login_required
def api_budget_pdf(bostamp):
    if not _has_acl():
        return _forbidden()
    try:
        detail = get_budget_detail(request.args.get("feid"), bostamp, current_user)
        html = render_budget_pdf_html(detail, request.args.get("style"))
        try:
            pdf_bytes = generate_ft_pdf_bytes(html)
            engine = "weasy/chrome"
        except Exception:
            pdf_bytes = generate_ft_pdf_bytes_xhtml2pdf(html)
            engine = "xhtml2pdf-fallback"
        number = int((detail.get("header") or {}).get("number") or 0)
        return Response(
            pdf_bytes,
            content_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="Devis_{number or bostamp}.pdf"',
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "X-PDF-Engine": engine,
            },
        )
    except Exception as exc:
        return _handle_error(exc)


@bp.route("/api/gr_orcamentos/devis/<int:number>/pdf")
@login_required
def api_budget_pdf_by_number(number):
    if not _has_acl():
        return _forbidden()
    try:
        detail = get_budget_detail_by_number(request.args.get("feid"), number, request.args.get("year"), current_user)
        html = render_budget_pdf_html(detail, request.args.get("style"))
        try:
            pdf_bytes = generate_ft_pdf_bytes(html)
            engine = "weasy/chrome"
        except Exception:
            pdf_bytes = generate_ft_pdf_bytes_xhtml2pdf(html)
            engine = "xhtml2pdf-fallback"
        return Response(
            pdf_bytes,
            content_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="Devis_{number}.pdf"',
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "X-PDF-Engine": engine,
            },
        )
    except Exception as exc:
        return _handle_error(exc)
