"""GuestSpaTur transfer requests dashboard."""

from __future__ import annotations

import io
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Blueprint, abort, jsonify, render_template, request, send_file
from flask_login import current_user, login_required

from models import Acessos, db
from services.multiempresa_service import MissingCurrentEntityError, get_current_feid
from services.transfer_dashboard_service import (
    TARGET_FEID,
    TransferDashboardError,
    build_transfer_dashboard,
    build_transfer_workbook,
    transfer_filters,
    transfer_period,
)


bp = Blueprint("transfer_dashboard", __name__)
logger = logging.getLogger(__name__)
LISBON = ZoneInfo("Europe/Lisbon")


def _has_access() -> bool:
    if bool(getattr(current_user, "ADMIN", False)):
        return True
    login = str(getattr(current_user, "LOGIN", "") or "").strip()
    if not login:
        return False
    access = Acessos.query.filter_by(utilizador=login, tabela="TRANSFERS").first()
    return bool(access and access.consultar)


def _require_access() -> None:
    if not _has_access():
        abort(403)
    try:
        current_feid = get_current_feid()
    except MissingCurrentEntityError:
        abort(403)
    if current_feid != TARGET_FEID:
        abort(403)


def _request_payload() -> dict:
    period = transfer_period(request.args.get("period"), request.args.get("start"), request.args.get("end"))
    return build_transfer_dashboard(db.engine, period, transfer_filters(request.args), feid=TARGET_FEID)


@bp.get("/dashboard/transfers")
@login_required
def dashboard_page():
    _require_access()
    period = transfer_period(request.args.get("period"), request.args.get("start"), request.args.get("end"))
    return render_template(
        "transfer_dashboard.html",
        initial_period=period["mode"],
        initial_start=period["start"].isoformat() if period.get("start") else "",
        initial_end=period["end"].isoformat() if period.get("end") else "",
    )


@bp.get("/api/dashboard/transfers")
@login_required
def dashboard_data():
    _require_access()
    try:
        response = jsonify({"ok": True, "data": _request_payload()})
    except TransferDashboardError as exc:
        response = jsonify({"ok": False, "error": str(exc)})
        response.status_code = 400
    except Exception:
        logger.exception("Erro ao carregar o resumo de transfers.")
        response = jsonify({"ok": False, "error": "Não foi possível carregar os pedidos de transfer."})
        response.status_code = 500
    response.headers["Cache-Control"] = "private, no-store, max-age=0"
    return response


@bp.get("/dashboard/transfers/export.xlsx")
@login_required
def dashboard_export():
    _require_access()
    try:
        payload = _request_payload()
        exported_at = datetime.now(LISBON)
        content = build_transfer_workbook(payload, exported_at=exported_at)
    except TransferDashboardError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception:
        logger.exception("Erro ao exportar o resumo de transfers.")
        return jsonify({"ok": False, "error": "Não foi possível exportar os pedidos de transfer."}), 500
    return send_file(
        io.BytesIO(content),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"transfers_{exported_at:%Y%m%d_%H%M}.xlsx",
        max_age=0,
    )

