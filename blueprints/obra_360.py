from __future__ import annotations

from flask import Blueprint, abort, current_app, jsonify, render_template, request, url_for
from flask_login import current_user, login_required

from services.obra_360_service import (
    add_recent_work,
    can_consult_opc,
    card_data,
    is_gr360_hub_context,
    overview_for_work,
    recent_works,
    resolve_work,
    search_works,
)
from services.opc_phc_info_service import get_opc_auto_lines, get_opc_logistics_lines


bp = Blueprint("obra_360", __name__)


def _guard(api: bool = False):
    if not is_gr360_hub_context():
        abort(404)
    if not can_consult_opc(current_user):
        if api:
            return jsonify({"error": "Sem permissão para consultar obras."}), 403
        abort(403)
    return None


@bp.route("/obra-360/<string:codigo>")
@login_required
def page(codigo: str):
    guarded = _guard()
    if guarded:
        return guarded
    return render_template("obra_360.html", codigo=(codigo or "").strip())


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
        "form_url": url_for("generic.opc_projetos_form", record_stamp=work["opcstamp"], return_to=hub_url),
    })
    return jsonify(payload)


@bp.route("/api/obra-360/<string:codigo>/cards/<string:card_code>")
@login_required
def api_card(codigo: str, card_code: str):
    guarded = _guard(api=True)
    if guarded:
        return guarded
    resolved = resolve_work(codigo, current_user)
    if resolved["status"] != "ok":
        return jsonify({"ok": False, "error": "Obra não encontrada ou ambígua."}), 404
    try:
        hub_url = url_for("obra_360.page", codigo=resolved["work"]["codigo"])
        card = card_data(
            resolved["work"],
            card_code,
            url_for("generic.opc_projetos_form", record_stamp=resolved["work"]["opcstamp"], return_to=hub_url),
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


@bp.route("/api/obra-360/<string:codigo>/autos/<string:auto_stamp>/linhas")
@login_required
def api_auto_lines(codigo: str, auto_stamp: str):
    guarded = _guard(api=True)
    if guarded:
        return guarded
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


@bp.route("/api/obra-360/<string:codigo>/logistica/<string:document_kind>/<string:document_stamp>/linhas")
@login_required
def api_logistics_lines(codigo: str, document_kind: str, document_stamp: str):
    guarded = _guard(api=True)
    if guarded:
        return guarded
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
