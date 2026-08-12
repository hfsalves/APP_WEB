from __future__ import annotations

import re
from urllib.parse import urlparse

from flask import Blueprint, Response, jsonify, render_template, request
from flask_login import current_user, login_required

from i18n import BASE_LANGUAGE, js_translations, reload_translations, translate
from models import Acessos, db
from modules.gr_subcontractor_measurements.service import SubcontractorMeasurementsError

from .service import (
    assign_budget_work,
    BudgetsCreditLimitError,
    BudgetsError,
    convert_budget_to_execution,
    get_budget_detail,
    get_budget_detail_by_number,
    get_budget_line_oci,
    get_budget_salespeople,
    get_budget_series,
    get_budget_technical_options,
    list_budgets,
    render_budget_pdf_html,
    decorate_budget_browser_pdf,
    save_budget,
    search_budget_works,
    set_budget_approval,
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


_BUDGET_ERROR_KEYS = {
    "A tabela E1 não existe na base PHC desta empresa.": "gr_budgets.error.company_data_unavailable",
    "A tabela E1 não tem a ficha da empresa configurada.": "gr_budgets.error.company_configuration",
    "A tabela CM3 não existe no PHC desta empresa.": "gr_budgets.error.salespeople_unavailable",
    "Série de orçamento inválida.": "gr_budgets.error.series_invalid",
    "Série de orçamento inexistente nesta empresa.": "gr_budgets.error.series_missing",
    "Ano inválido.": "gr_budgets.error.year_invalid",
    "Orçamento não indicado.": "gr_budgets.error.budget_missing",
    "Orçamento não encontrado no PHC desta empresa.": "gr_budgets.error.budget_not_found",
    "O orçamento já não existe no PHC desta empresa.": "gr_budgets.error.budget_not_found",
    "Número de Devis inválido.": "gr_budgets.error.budget_number_invalid",
    "Devis não encontrado no PHC desta empresa.": "gr_budgets.error.budget_not_found",
    "A tabela ST não existe no PHC desta empresa.": "gr_budgets.error.components_table_unavailable",
    "A tabela STFAMI não tem a configuração necessária para selecionar componentes.": "gr_budgets.error.components_configuration",
    "Linha do orçamento não indicada.": "gr_budgets.error.line_missing",
    "Linha do orçamento não encontrada no PHC desta empresa.": "gr_budgets.error.line_not_found",
    "A tabela OCI não existe no PHC desta empresa.": "gr_budgets.error.no_technical_structure",
    "Data do orçamento inválida.": "gr_budgets.error.date_invalid",
    "Selecione um cliente válido.": "gr_budgets.error.client_invalid",
    "O cliente selecionado já não está disponível no PHC.": "gr_budgets.error.client_unavailable",
    "O cliente do orçamento já não está disponível no PHC.": "gr_budgets.error.client_unavailable",
    "O comercial selecionado já não está disponível no PHC.": "gr_budgets.error.salesperson_unavailable",
    "Dados do orçamento inválidos.": "gr_budgets.error.budget_invalid",
    "Cabeçalho do orçamento inválido.": "gr_budgets.error.header_invalid",
    "Linhas do orçamento inválidas.": "gr_budgets.error.budget_lines_invalid",
    "O orçamento já não está em preparação e não pode ser alterado.": "gr_budgets.error.budget_not_in_preparation",
    "O orçamento está fechado, adjudicado ou anulado e não pode ser alterado.": "gr_budgets.error.budget_locked",
    "O orçamento foi alterado por outro utilizador. Atualize os dados antes de voltar a gravar.": "gr_budgets.error.budget_stale",
    "Existem linhas duplicadas no orçamento.": "gr_budgets.error.budget_lines_duplicate",
    "A aprovação só está disponível para dossiers Devis.": "gr_budgets.error.approval_devis_only",
    "Não existe plafond suficiente para aprovar este orçamento.": "gr_budgets.error.approval_credit_limit",
    "A série Étude et Exécution não existe nesta empresa.": "gr_budgets.error.execution_series_missing",
    "A conversão só está disponível para dossiers Devis.": "gr_budgets.error.conversion_devis_only",
    "Indique se o orçamento cria uma obra nova ou é um aditamento.": "gr_budgets.error.conversion_target_invalid",
    "Selecione uma obra existente.": "gr_budgets.error.work_required",
    "A obra selecionada não está disponível nesta empresa.": "gr_budgets.error.work_unavailable",
    "Não foi possível determinar o processo PHC da obra.": "gr_budgets.error.work_process_unavailable",
}


def _budget_i18n_payload() -> dict[str, str]:
    catalogs = reload_translations()
    keys = [
        key
        for key in (catalogs.get(BASE_LANGUAGE, {}) or {})
        if str(key).startswith("gr_budgets.")
    ]
    return js_translations(keys)


def _localized_error_message(exc: Exception) -> str:
    message = str(exc or "").strip()
    key = _BUDGET_ERROR_KEYS.get(message)
    if key:
        return translate(key)

    line_match = re.fullmatch(r"Linha (\d+) inválida\.", message)
    if line_match:
        return translate("gr_budgets.error.budget_line_invalid", line=line_match.group(1))
    owned_match = re.fullmatch(r"A linha (\d+) não pertence a este orçamento\.", message)
    if owned_match:
        return translate("gr_budgets.error.budget_line_not_owned", line=owned_match.group(1))
    if message.startswith("Sem colunas válidas para atualizar "):
        return translate("gr_budgets.error.no_valid_update_fields")
    return translate("gr_budgets.error.generic")


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


def _has_write_acl(creating: bool) -> bool:
    if getattr(current_user, "ADMIN", False) or getattr(current_user, "DEV", False):
        return True
    login = (getattr(current_user, "LOGIN", "") or "").strip()
    if not login:
        return False
    aliases = ("GR_ORCAMENTOS", "ORCAMENTOS", "GR_BUDGETS", "DEVIS")
    rows = (
        Acessos.query.filter(Acessos.utilizador == login)
        .filter(db.func.upper(db.func.ltrim(db.func.rtrim(Acessos.tabela))).in_(aliases))
        .all()
    )
    field = "inserir" if creating else "editar"
    return any(bool(getattr(row, field, False)) for row in rows)


def _forbidden(api: bool = True):
    message = translate("gr_budgets.error.forbidden_consult")
    return (jsonify({"error": message}), 403) if api else (message, 403)


def _handle_error(exc: Exception):
    if isinstance(exc, (BudgetsError, SubcontractorMeasurementsError)):
        payload = {"error": _localized_error_message(exc)}
        if isinstance(exc, BudgetsCreditLimitError):
            payload["credit"] = exc.credit
        return jsonify(payload), getattr(exc, "status_code", 500)
    return jsonify({"error": translate("gr_budgets.error.generic")}), 500


def _hub_return_url(value: str | None) -> str:
    """Only retain an internal return link back to a Hub 360 dossier."""
    candidate = str(value or "").strip()
    parsed = urlparse(candidate)
    if not candidate or parsed.scheme or parsed.netloc or not parsed.path.startswith("/obra-360/"):
        return ""
    return candidate


@bp.route("/gr360_orcamentos")
@bp.route("/gr_orcamentos")
@bp.route("/orcamentos")
@login_required
def page():
    if not _has_acl():
        return _forbidden(api=False)
    return render_template(
        "gr_budgets/budgets.html",
        gr_budgets_i18n=_budget_i18n_payload(),
        hub_return_url=_hub_return_url(request.args.get("return_to")),
    )


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


@bp.route("/api/gr_orcamentos/obras")
@login_required
def api_works():
    if not _has_acl():
        return _forbidden()
    try:
        return jsonify(
            {
                "ok": True,
                **search_budget_works(
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


@bp.route("/api/gr_orcamentos/orcamento", methods=["POST"])
@login_required
def api_save_budget():
    payload = request.get_json(silent=True) or {}
    creating = not bool(str(payload.get("bostamp") or "").strip())
    if not _has_write_acl(creating):
        key = "gr_budgets.error.forbidden_create" if creating else "gr_budgets.error.forbidden_edit"
        return jsonify({"error": translate(key)}), 403
    try:
        return jsonify({"ok": True, **save_budget(payload, current_user)})
    except Exception as exc:
        return _handle_error(exc)


@bp.route("/api/gr_orcamentos/orcamento/<bostamp>/aprovacao", methods=["POST"])
@login_required
def api_budget_approval(bostamp):
    if not _has_write_acl(False):
        return jsonify({"error": translate("gr_budgets.error.forbidden_edit")}), 403
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload.get("approved"), bool):
        return jsonify({"error": translate("gr_budgets.error.approval_invalid_state")}), 400
    try:
        return jsonify(
            {
                "ok": True,
                **set_budget_approval(
                    payload.get("feid"),
                    bostamp,
                    payload.get("approved"),
                    current_user,
                ),
            }
        )
    except Exception as exc:
        return _handle_error(exc)


@bp.route("/api/gr_orcamentos/orcamento/<bostamp>/converter-estudo-execucao", methods=["POST"])
@login_required
def api_budget_convert_execution(bostamp):
    if not _has_write_acl(False):
        return jsonify({"error": translate("gr_budgets.error.forbidden_edit")}), 403
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify(
            {
                "ok": True,
                **convert_budget_to_execution(
                    payload.get("feid"),
                    bostamp,
                    payload.get("target"),
                    payload.get("opcstamp"),
                    current_user,
                ),
            }
        )
    except Exception as exc:
        return _handle_error(exc)


@bp.route("/api/gr_orcamentos/orcamento/<bostamp>/obra", methods=["POST"])
@login_required
def api_budget_assign_work(bostamp):
    if not _has_write_acl(False):
        return jsonify({"error": translate("gr_budgets.error.forbidden_edit")}), 403
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify(
            {
                "ok": True,
                **assign_budget_work(
                    payload.get("feid"),
                    bostamp,
                    payload.get("opcstamp"),
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
        style = request.args.get("style")
        html = render_budget_pdf_html(detail, style)
        try:
            pdf_bytes, engine = generate_ft_pdf_bytes(html, return_engine=True)
            if engine == "browser":
                pdf_bytes = decorate_budget_browser_pdf(pdf_bytes, detail)
        except Exception:
            fallback_html = render_budget_pdf_html(detail, style, suppress_running=True)
            pdf_bytes = generate_ft_pdf_bytes_xhtml2pdf(fallback_html)
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
        style = request.args.get("style")
        html = render_budget_pdf_html(detail, style)
        try:
            pdf_bytes, engine = generate_ft_pdf_bytes(html, return_engine=True)
            if engine == "browser":
                pdf_bytes = decorate_budget_browser_pdf(pdf_bytes, detail)
        except Exception:
            fallback_html = render_budget_pdf_html(detail, style, suppress_running=True)
            pdf_bytes = generate_ft_pdf_bytes_xhtml2pdf(fallback_html)
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
