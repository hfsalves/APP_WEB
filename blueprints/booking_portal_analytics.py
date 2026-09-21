"""Private StationZero dashboard for PortoBreak portal analytics."""

from __future__ import annotations

import logging

from flask import Blueprint, abort, jsonify, render_template, request
from flask_login import current_user, login_required

from models import db
from services.booking_portal_analytics_dashboard import (
    DashboardPeriodError,
    build_dashboard,
    dashboard_period,
)


bp = Blueprint("booking_portal_analytics", __name__)
logger = logging.getLogger(__name__)


def _require_admin() -> None:
    if not bool(getattr(current_user, "ADMIN", False)):
        abort(403)


def _flag(name: str) -> bool:
    return str(request.args.get(name, "")).strip().lower() in {"1", "true", "yes", "on"}


@bp.get("/analytics/portobreak")
@login_required
def dashboard_page():
    _require_admin()
    period = dashboard_period(request.args.get("start"), request.args.get("end"))
    response = render_template(
        "booking_portal_analytics.html",
        period_start=period["start"].isoformat(),
        period_end=period["end"].isoformat(),
    )
    return response


@bp.get("/api/analytics/portobreak")
@login_required
def dashboard_data():
    _require_admin()
    try:
        period = dashboard_period(request.args.get("start"), request.args.get("end"))
        payload = build_dashboard(
            db.engine,
            period,
            include_bots=_flag("include_bots"),
            include_validation=_flag("include_validation"),
        )
        response = jsonify({"ok": True, "data": payload})
    except DashboardPeriodError as exc:
        response = jsonify({"ok": False, "error": str(exc)})
        response.status_code = 400
    except Exception:
        logger.exception("Failed to build PortoBreak analytics dashboard")
        response = jsonify({"ok": False, "error": "Não foi possível carregar a analítica do portal."})
        response.status_code = 500

    response.headers["Cache-Control"] = "private, no-store, max-age=0"
    return response
