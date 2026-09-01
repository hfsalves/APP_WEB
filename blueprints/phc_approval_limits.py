from __future__ import annotations

from flask import Blueprint, abort, jsonify, render_template, request
from flask_login import current_user, login_required

from services.phc_approval_limits_service import (
    PhcApprovalLimitsError,
    create_approval_limit,
    delete_approval_limit,
    list_approval_limits,
    list_phc_users,
    update_approval_limit,
)


bp = Blueprint("phc_approval_limits", __name__)


def _guard(api: bool = False):
    if not bool(getattr(current_user, "ADMIN", False)):
        if api:
            return jsonify({"ok": False, "error": "Sem permissão para gerir plafonds de aprovação."}), 403
        abort(403)
    return None


def _error(exc: PhcApprovalLimitsError):
    return jsonify({"ok": False, "error": str(exc)}), getattr(exc, "status_code", 400)


@bp.route("/approval-limits")
@login_required
def page():
    guarded = _guard()
    if guarded:
        return guarded
    return render_template("phc_approval_limits.html")


@bp.route("/api/approval-limits")
@login_required
def api_list():
    guarded = _guard(api=True)
    if guarded:
        return guarded
    try:
        return jsonify({"ok": True, "items": list_approval_limits()})
    except PhcApprovalLimitsError as exc:
        return _error(exc)


@bp.route("/api/approval-limits/users")
@login_required
def api_users():
    guarded = _guard(api=True)
    if guarded:
        return guarded
    try:
        return jsonify({"ok": True, "items": list_phc_users()})
    except PhcApprovalLimitsError as exc:
        return _error(exc)


@bp.route("/api/approval-limits", methods=["POST"])
@login_required
def api_create():
    guarded = _guard(api=True)
    if guarded:
        return guarded
    try:
        item = create_approval_limit(request.get_json(silent=True) or {}, current_user)
        return jsonify({"ok": True, "item": item}), 201
    except PhcApprovalLimitsError as exc:
        return _error(exc)


@bp.route("/api/approval-limits/<stamp>", methods=["PUT"])
@login_required
def api_update(stamp: str):
    guarded = _guard(api=True)
    if guarded:
        return guarded
    try:
        item = update_approval_limit(stamp, request.get_json(silent=True) or {}, current_user)
        return jsonify({"ok": True, "item": item})
    except PhcApprovalLimitsError as exc:
        return _error(exc)


@bp.route("/api/approval-limits/<stamp>", methods=["DELETE"])
@login_required
def api_delete(stamp: str):
    guarded = _guard(api=True)
    if guarded:
        return guarded
    try:
        delete_approval_limit(stamp)
        return jsonify({"ok": True})
    except PhcApprovalLimitsError as exc:
        return _error(exc)

