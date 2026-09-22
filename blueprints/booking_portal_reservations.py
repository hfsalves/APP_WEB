"""Private StationZero dashboard for PortoBreak portal reservations."""

from __future__ import annotations

import logging

from flask import Blueprint, abort, jsonify, render_template, request
from flask_login import current_user, login_required

from models import Acessos, db
from services.booking_portal_reservations_dashboard import (
    ReservationsDashboardError,
    build_reservations_dashboard,
    dashboard_filters,
    reservations_period,
)


bp = Blueprint("booking_portal_reservations", __name__)
logger = logging.getLogger(__name__)


def _has_dashboard_access() -> bool:
    if bool(getattr(current_user, "ADMIN", False)):
        return True
    login = str(getattr(current_user, "LOGIN", "") or "").strip()
    if not login:
        return False
    access = Acessos.query.filter_by(utilizador=login, tabela="PB_RESERVATIONS").first()
    return bool(access and access.consultar)


def _require_access() -> None:
    if not _has_dashboard_access():
        abort(403)


@bp.get("/dashboard/portobreak/reservas")
@login_required
def dashboard_page():
    _require_access()
    period = reservations_period(request.args.get("start"), request.args.get("end"))
    return render_template(
        "booking_portal_reservations.html",
        period_start=period["start"].isoformat(),
        period_end=period["end"].isoformat(),
        selected_status=request.args.get("status", ""),
        selected_property=request.args.get("property_id", ""),
        selected_environment=request.args.get("environment", ""),
        selected_query=request.args.get("query", ""),
    )


@bp.get("/api/dashboard/portobreak/reservas")
@login_required
def dashboard_data():
    _require_access()
    try:
        period = reservations_period(request.args.get("start"), request.args.get("end"))
        payload = build_reservations_dashboard(db.engine, period, dashboard_filters(request.args))
        response = jsonify({"ok": True, "data": payload})
    except ReservationsDashboardError as exc:
        response = jsonify({"ok": False, "error": str(exc)})
        response.status_code = 400
    except Exception:
        logger.exception("Failed to build PortoBreak reservations dashboard")
        response = jsonify({"ok": False, "error": "Não foi possível carregar as reservas do portal."})
        response.status_code = 500
    response.headers["Cache-Control"] = "private, no-store, max-age=0"
    return response
