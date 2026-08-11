from __future__ import annotations

from flask import Blueprint, abort, current_app, jsonify, render_template, request, url_for
from flask_login import current_user, login_required

from services.obra_360_service import (
    add_recent_work,
    can_consult_opc,
    card_data,
    get_work_cost_lines,
    get_work_cost_subgroups,
    get_work_production_detail,
    get_hub_tab_access_matrix,
    hub_tabs_for_user,
    is_gr360_hub_context,
    overview_for_work,
    recent_works,
    resolve_work,
    save_hub_tab_access_matrix,
    search_works,
    CARD_TAB_CODES,
    can_access_hub_tab,
)
from services.opc_phc_info_service import (
    get_opc_auto_lines,
    get_opc_invoice_lines,
    get_opc_logistics_lines,
    get_opc_payment_lines,
    get_opc_purchase_lines,
    get_opc_receipt_lines,
    get_opc_subcontractor_auto_lines,
)


bp = Blueprint("obra_360", __name__)


def _guard(api: bool = False):
    if not is_gr360_hub_context():
        abort(404)
    if not can_consult_opc(current_user):
        if api:
            return jsonify({"error": "Sem permissão para consultar obras."}), 403
        abort(403)
    if not hub_tabs_for_user(current_user):
        if api:
            return jsonify({"error": "Sem acesso a secções do dossiê de obra."}), 403
        abort(403)
    return None


def _admin_guard():
    if not bool(getattr(current_user, "ADMIN", False)):
        return jsonify({"ok": False, "error": "Sem permissão para gerir acessos."}), 403
    return None


def _tab_guard(tab_code: str):
    if not can_access_hub_tab(current_user, tab_code):
        return jsonify({"ok": False, "error": "Sem acesso a esta secção do dossiê."}), 403
    return None


@bp.route("/obra-360/<string:codigo>")
@login_required
def page(codigo: str):
    guarded = _guard()
    if guarded:
        return guarded
    return render_template(
        "obra_360.html",
        codigo=(codigo or "").strip(),
        obra360_is_admin=bool(getattr(current_user, "ADMIN", False)),
    )


@bp.route("/api/obra-360/search")
@login_required
def api_search():
    guarded = _guard(api=True)
    if guarded:
        return guarded
    return jsonify({"ok": True, "works": search_works(request.args.get("q", ""), current_user)})


@bp.route("/api/obra-360/recent")
@login_required
def api_recent():
    guarded = _guard(api=True)
    if guarded:
        return guarded
    return jsonify({"ok": True, "works": recent_works(current_user)})


@bp.route("/api/obra-360/<string:codigo>/overview")
@login_required
def api_overview(codigo: str):
    guarded = _guard(api=True)
    if guarded:
        return guarded
    resolved = resolve_work(codigo, current_user)
    if resolved["status"] == "missing":
        return jsonify({"ok": False, "error": "Obra não encontrada."}), 404
    if resolved["status"] == "ambiguous":
        return jsonify({"ok": False, "ambiguous": True, "works": resolved["works"]}), 409
    work = resolved["work"]
    add_recent_work(work)
    payload = overview_for_work(work)
    hub_url = url_for("obra_360.page", codigo=work["codigo"])
    payload.update({
        "ok": True,
        "allowed_tabs": sorted(hub_tabs_for_user(current_user)),
        "form_url": url_for("generic.opc_projetos_form", record_stamp=work["opcstamp"], return_to=hub_url),
    })
    return jsonify(payload)


@bp.route("/api/obra-360/<string:codigo>/cards/<string:card_code>")
@login_required
def api_card(codigo: str, card_code: str):
    guarded = _guard(api=True)
    if guarded:
        return guarded
    required_tab = CARD_TAB_CODES.get(card_code)
    if required_tab and not can_access_hub_tab(current_user, required_tab):
        return jsonify({"ok": False, "error": "Sem acesso a esta secção do dossiê."}), 403
    resolved = resolve_work(codigo, current_user)
    if resolved["status"] != "ok":
        return jsonify({"ok": False, "error": "Obra não encontrada ou ambígua."}), 404
    try:
        hub_url = url_for("obra_360.page", codigo=resolved["work"]["codigo"])
        card = card_data(
            resolved["work"],
            card_code,
            url_for("generic.opc_projetos_form", record_stamp=resolved["work"]["opcstamp"], return_to=hub_url),
            current_user,
        )
        if card_code == "orcamento":
            for row in card.get("rows") or []:
                bostamp = str(row.get("oristamp") or "").strip()
                feid = row.get("source_feid")
                if bostamp and feid:
                    row["open_url"] = url_for(
                        "gr_budgets.page",
                        feid=feid,
                        bostamp=bostamp,
                        return_to=hub_url,
                    )
    except KeyError:
        return jsonify({"ok": False, "error": "Card inválido."}), 404
    return jsonify({"ok": True, "card": card})


@bp.route("/api/obra-360/<string:codigo>/contratos-se/<string:contract_stamp>/detalhe")
@login_required
def api_subcontractor_contract_detail(codigo: str, contract_stamp: str):
    guarded = _guard(api=True)
    if guarded:
        return guarded
    tab_guarded = _tab_guard("autos")
    if tab_guarded:
        return tab_guarded
    resolved = resolve_work(codigo, current_user)
    if resolved["status"] != "ok":
        return jsonify({"ok": False, "error": "Obra não encontrada ou ambígua."}), 404
    try:
        from modules.gr_subcontractor_measurements.service import get_contract_detail
        from services.opc_phc_info_service import get_opc_phc_info

        source = (get_opc_phc_info(resolved["work"]["opcstamp"]).get("fonte") or {})
        return jsonify({
            "ok": True,
            **get_contract_detail(source.get("feid"), contract_stamp, current_user),
        })
    except Exception:
        current_app.logger.exception(
            "Erro ao carregar detalhe do contrato de subempreitada %s da obra %s",
            contract_stamp,
            resolved["work"]["codigo"],
        )
        return jsonify({"ok": False, "error": "Não foi possível carregar o contrato de subempreitada agora."}), 502


@bp.route("/api/obra-360/acessos", methods=["GET", "PUT"])
@login_required
def api_accesses():
    guarded = _guard(api=True)
    if guarded:
        return guarded
    admin_guarded = _admin_guard()
    if admin_guarded:
        return admin_guarded
    if request.method == "GET":
        return jsonify({"ok": True, **get_hub_tab_access_matrix()})
    payload = request.get_json(silent=True) or {}
    users = payload.get("users")
    if not isinstance(users, list):
        return jsonify({"ok": False, "error": "Dados de acessos inválidos."}), 400
    save_hub_tab_access_matrix(users, str(getattr(current_user, "LOGIN", "") or ""))
    return jsonify({"ok": True})


@bp.route("/api/obra-360/<string:codigo>/custos/<string:family>/subgrupos")
@login_required
def api_cost_subgroups(codigo: str, family: str):
    guarded = _guard(api=True)
    if guarded:
        return guarded
    tab_guarded = _tab_guard("custos")
    if tab_guarded:
        return tab_guarded
    resolved = resolve_work(codigo, current_user)
    if resolved["status"] != "ok":
        return jsonify({"ok": False, "error": "Obra não encontrada ou ambígua."}), 404
    try:
        return jsonify({"ok": True, **get_work_cost_subgroups(resolved["work"], family)})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception:
        current_app.logger.exception("Erro ao carregar subgrupos de custos %s da obra %s", family, resolved["work"]["codigo"])
        return jsonify({"ok": False, "error": "Não foi possível carregar os subgrupos de custos agora."}), 502


@bp.route("/api/obra-360/<string:codigo>/custos/<string:family>/linhas")
@login_required
def api_cost_lines(codigo: str, family: str):
    guarded = _guard(api=True)
    if guarded:
        return guarded
    tab_guarded = _tab_guard("custos")
    if tab_guarded:
        return tab_guarded
    resolved = resolve_work(codigo, current_user)
    if resolved["status"] != "ok":
        return jsonify({"ok": False, "error": "Obra não encontrada ou ambígua."}), 404
    try:
        return jsonify({"ok": True, **get_work_cost_lines(resolved["work"], family)})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception:
        current_app.logger.exception("Erro ao carregar movimentos de custos %s da obra %s", family, resolved["work"]["codigo"])
        return jsonify({"ok": False, "error": "Não foi possível carregar os movimentos de custos agora."}), 502


@bp.route("/api/obra-360/<string:codigo>/producao/<string:plan_stamp>/detalhe")
@login_required
def api_production_detail(codigo: str, plan_stamp: str):
    guarded = _guard(api=True)
    if guarded:
        return guarded
    tab_guarded = _tab_guard("producao")
    if tab_guarded:
        return tab_guarded
    resolved = resolve_work(codigo, current_user)
    if resolved["status"] != "ok":
        return jsonify({"ok": False, "error": "Obra não encontrada ou ambígua."}), 404
    try:
        return jsonify({"ok": True, **get_work_production_detail(resolved["work"], plan_stamp)})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception:
        current_app.logger.exception(
            "Erro ao carregar detalhe da marcação de produção %s da obra %s",
            plan_stamp,
            resolved["work"]["codigo"],
        )
        return jsonify({"ok": False, "error": "Não foi possível carregar o detalhe de produção agora."}), 502


@bp.route("/api/obra-360/<string:codigo>/autos/<string:auto_stamp>/linhas")
@login_required
def api_auto_lines(codigo: str, auto_stamp: str):
    guarded = _guard(api=True)
    if guarded:
        return guarded
    tab_guarded = _tab_guard("autos")
    if tab_guarded:
        return tab_guarded
    resolved = resolve_work(codigo, current_user)
    if resolved["status"] != "ok":
        return jsonify({"ok": False, "error": "Obra não encontrada ou ambígua."}), 404
    try:
        return jsonify({"ok": True, **get_opc_auto_lines(resolved["work"]["opcstamp"], auto_stamp)})
    except Exception:
        current_app.logger.exception(
            "Erro ao carregar linhas do auto %s da obra %s",
            auto_stamp,
            resolved["work"]["codigo"],
        )
        return jsonify({"ok": False, "error": "Não foi possível carregar as linhas deste auto agora."}), 502


@bp.route("/api/obra-360/<string:codigo>/autos-subempreiteiro/<string:auto_stamp>/linhas")
@login_required
def api_subcontractor_auto_lines(codigo: str, auto_stamp: str):
    guarded = _guard(api=True)
    if guarded:
        return guarded
    tab_guarded = _tab_guard("autos")
    if tab_guarded:
        return tab_guarded
    resolved = resolve_work(codigo, current_user)
    if resolved["status"] != "ok":
        return jsonify({"ok": False, "error": "Obra não encontrada ou ambígua."}), 404
    try:
        return jsonify({"ok": True, **get_opc_subcontractor_auto_lines(resolved["work"]["opcstamp"], auto_stamp)})
    except Exception:
        current_app.logger.exception(
            "Erro ao carregar linhas do auto de subempreitada %s da obra %s",
            auto_stamp,
            resolved["work"]["codigo"],
        )
        return jsonify({"ok": False, "error": "Não foi possível carregar as linhas deste auto de subempreitada agora."}), 502


@bp.route("/api/obra-360/<string:codigo>/logistica/<string:document_kind>/<string:document_stamp>/linhas")
@login_required
def api_logistics_lines(codigo: str, document_kind: str, document_stamp: str):
    guarded = _guard(api=True)
    if guarded:
        return guarded
    tab_guarded = _tab_guard("blbc")
    if tab_guarded:
        return tab_guarded
    if document_kind not in {"bl", "bc"}:
        return jsonify({"ok": False, "error": "Tipo de documento inválido."}), 404
    resolved = resolve_work(codigo, current_user)
    if resolved["status"] != "ok":
        return jsonify({"ok": False, "error": "Obra não encontrada ou ambígua."}), 404
    try:
        return jsonify({"ok": True, **get_opc_logistics_lines(resolved["work"]["opcstamp"], document_stamp, document_kind)})
    except Exception:
        current_app.logger.exception(
            "Erro ao carregar linhas do documento %s da obra %s",
            document_stamp,
            resolved["work"]["codigo"],
        )
        return jsonify({"ok": False, "error": "Não foi possível carregar as linhas deste documento agora."}), 502


@bp.route("/api/obra-360/<string:codigo>/compras/<string:purchase_stamp>/linhas")
@login_required
def api_purchase_lines(codigo: str, purchase_stamp: str):
    guarded = _guard(api=True)
    if guarded:
        return guarded
    tab_guarded = _tab_guard("compras")
    if tab_guarded:
        return tab_guarded
    resolved = resolve_work(codigo, current_user)
    if resolved["status"] != "ok":
        return jsonify({"ok": False, "error": "Obra não encontrada ou ambígua."}), 404
    try:
        return jsonify({"ok": True, **get_opc_purchase_lines(resolved["work"]["opcstamp"], purchase_stamp)})
    except Exception:
        current_app.logger.exception(
            "Erro ao carregar linhas da compra %s da obra %s",
            purchase_stamp,
            resolved["work"]["codigo"],
        )
        return jsonify({"ok": False, "error": "Não foi possível carregar as linhas desta compra agora."}), 502


@bp.route("/api/obra-360/<string:codigo>/recebimentos/<string:receipt_stamp>/linhas")
@login_required
def api_receipt_lines(codigo: str, receipt_stamp: str):
    guarded = _guard(api=True)
    if guarded:
        return guarded
    tab_guarded = _tab_guard("recebimentos")
    if tab_guarded:
        return tab_guarded
    resolved = resolve_work(codigo, current_user)
    if resolved["status"] != "ok":
        return jsonify({"ok": False, "error": "Obra não encontrada ou ambígua."}), 404
    try:
        return jsonify({"ok": True, **get_opc_receipt_lines(resolved["work"]["opcstamp"], receipt_stamp)})
    except Exception:
        current_app.logger.exception("Erro ao carregar linhas do recebimento %s da obra %s", receipt_stamp, resolved["work"]["codigo"])
        return jsonify({"ok": False, "error": "Não foi possível carregar as linhas deste recebimento agora."}), 502


@bp.route("/api/obra-360/<string:codigo>/pagamentos/<string:payment_stamp>/linhas")
@login_required
def api_payment_lines(codigo: str, payment_stamp: str):
    guarded = _guard(api=True)
    if guarded:
        return guarded
    tab_guarded = _tab_guard("recebimentos")
    if tab_guarded:
        return tab_guarded
    resolved = resolve_work(codigo, current_user)
    if resolved["status"] != "ok":
        return jsonify({"ok": False, "error": "Obra não encontrada ou ambígua."}), 404
    try:
        return jsonify({"ok": True, **get_opc_payment_lines(resolved["work"]["opcstamp"], payment_stamp)})
    except Exception:
        current_app.logger.exception("Erro ao carregar linhas do pagamento %s da obra %s", payment_stamp, resolved["work"]["codigo"])
        return jsonify({"ok": False, "error": "Não foi possível carregar as linhas deste pagamento agora."}), 502


@bp.route("/api/obra-360/<string:codigo>/faturas/<string:invoice_stamp>/linhas")
@login_required
def api_invoice_lines(codigo: str, invoice_stamp: str):
    guarded = _guard(api=True)
    if guarded:
        return guarded
    tab_guarded = _tab_guard("faturacao")
    if tab_guarded:
        return tab_guarded
    resolved = resolve_work(codigo, current_user)
    if resolved["status"] != "ok":
        return jsonify({"ok": False, "error": "Obra não encontrada ou ambígua."}), 404
    try:
        return jsonify({"ok": True, **get_opc_invoice_lines(resolved["work"]["opcstamp"], invoice_stamp)})
    except Exception:
        current_app.logger.exception(
            "Erro ao carregar linhas da fatura %s da obra %s",
            invoice_stamp,
            resolved["work"]["codigo"],
        )
        return jsonify({"ok": False, "error": "Não foi possível carregar as linhas desta fatura agora."}), 502
