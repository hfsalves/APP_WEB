"""Monthly reservation calendar for authenticated owner-portal users."""

from __future__ import annotations

import logging
from datetime import date

from flask import Blueprint, abort, jsonify, render_template, request
from flask_login import current_user, login_required

from models import db
from services.client_reservations_calendar_service import ClientCalendarError, build_client_calendar


bp = Blueprint("client_calendar", __name__)
logger = logging.getLogger(__name__)


def _client_identity() -> tuple[int, int]:
    try:
        client_no = int(str(getattr(current_user, "CLNO", "") or "").strip())
    except (TypeError, ValueError):
        client_no = 0
    try:
        establishment = max(0, int(str(getattr(current_user, "CLESTAB", "") or "0").strip()))
    except (TypeError, ValueError):
        establishment = 0
    if client_no <= 0 or not str(getattr(current_user, "CLNOME", "") or "").strip():
        abort(403)
    return client_no, establishment


@bp.get("/cliente/calendario")
@bp.get("/portal_cliente/calendario")
@login_required
def calendar_page():
    _client_identity()
    return render_template(
        "cliente_calendario.html",
        page_title="Calendário de Reservas",
        initial_month=date.today().strftime("%Y-%m"),
    )


@bp.get("/api/cliente/calendario")
@login_required
def calendar_data():
    client_no, establishment = _client_identity()
    include_cancelled = str(request.args.get("include_cancelled") or "").strip().lower() in {"1", "true", "yes", "on"}
    try:
        payload = build_client_calendar(
            db.engine,
            client_no,
            establishment,
            lodging=request.args.get("alojamento"),
            start=request.args.get("start"),
            months=request.args.get("months"),
            include_cancelled=include_cancelled,
        )
        response = jsonify({"ok": True, "data": payload})
    except ClientCalendarError as exc:
        response = jsonify({"ok": False, "error": str(exc)})
        response.status_code = 400
    except Exception:
        logger.exception("Erro ao carregar o calendário de reservas do proprietário.")
        response = jsonify({"ok": False, "error": "Não foi possível carregar o calendário de reservas."})
        response.status_code = 500
    response.headers["Cache-Control"] = "private, no-store, max-age=0"
    return response
