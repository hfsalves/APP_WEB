from __future__ import annotations

from datetime import date, timedelta

from flask import Blueprint, abort, jsonify, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import text

from models import db
from services.guestspa_ferias_service import (
    apply_guestspa_ferias_approval_action,
    apply_guestspa_ferias_changes,
    list_guestspa_ferias,
    list_guestspa_ferias_aprovacao,
)


bp = Blueprint("guestspa_ferias", __name__)


def _can_approve() -> bool:
    if bool(getattr(current_user, "ADMIN", False)):
        return True
    login = str(getattr(current_user, "LOGIN", "") or "").strip()
    return bool(login and db.session.execute(text("""
        SELECT TOP 1 1 FROM dbo.ACESSOS
        WHERE LOWER(LTRIM(RTRIM(ISNULL(UTILIZADOR, '')))) = LOWER(:login)
          AND UPPER(LTRIM(RTRIM(ISNULL(TABELA, '')))) = 'GUESTSPA_FERIAS_APROVACAO'
          AND ISNULL(CONSULTAR, 0) = 1
    """), {"login": login}).scalar())


@bp.route("/guestspa/ferias")
@login_required
def guestspa_ferias_page():
    payload = list_guestspa_ferias(current_user, request.args.get("ano"))
    return render_template(
        "guestspa_ferias.html", page_title="Férias", colaborador=payload["colaborador"], year=payload["year"],
        vacation_days=payload["vacation_days"], vacation_pending_days=payload["pending_vacation_days"],
        vacation_unmark_request_days=payload["unmark_request_days"], vacation_holiday_days=payload["holiday_days"],
        vacation_periods=payload["periods"], vacation_working_days=payload["working_days"], vacation_warning=payload["warning"],
    )


@bp.route("/guestspa/api/ferias")
@login_required
def guestspa_ferias_api():
    try:
        return jsonify(list_guestspa_ferias(current_user, request.args.get("ano")))
    except Exception:
        db.session.rollback()
        return jsonify({"ok": False, "error": "Erro ao listar férias."}), 500


@bp.route("/guestspa/api/ferias/alteracoes", methods=["POST"])
@login_required
def guestspa_ferias_save():
    try:
        return jsonify(apply_guestspa_ferias_changes(current_user, request.get_json(silent=True) or {}))
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"ok": False, "error": "Erro ao gravar alterações de férias."}), 500


@bp.route("/guestspa/ferias/aprovacao")
@login_required
def guestspa_ferias_aprovacao_page():
    if not _can_approve():
        abort(403)
    try:
        payload = list_guestspa_ferias_aprovacao(request.args.get("semana"), request.args.get("inicio"), request.args.get("fim"))
    except Exception:
        today = date.today()
        start = today - timedelta(days=today.weekday())
        payload = {"start": start, "end": start + timedelta(days=55), "previous_week": start - timedelta(days=7),
                   "previous_end": start + timedelta(days=48), "next_week": start + timedelta(days=7),
                   "next_end": start + timedelta(days=62), "days": [], "months": [], "employees": [],
                   "warnings": ["a base de dados da GuestSpa"], "companies": [{"feid": 1, "nome": "GuestSpaTur"}], "selected_feid": 1}
    if request.args.get("fragment") == "1":
        return render_template("_guestspa_ferias_aprovacao_grid.html", **payload)
    return render_template("guestspa_ferias_aprovacao.html", page_title="Aprovação de férias", **payload)


@bp.route("/guestspa/api/ferias/aprovacao/alteracoes", methods=["POST"])
@login_required
def guestspa_ferias_aprovacao_save():
    if not _can_approve():
        return jsonify({"ok": False, "error": "Sem permissão para aprovar férias."}), 403
    try:
        return jsonify(apply_guestspa_ferias_approval_action(current_user, request.get_json(silent=True) or {}))
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"ok": False, "error": "Erro ao aplicar decisão de férias."}), 500
