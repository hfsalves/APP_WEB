from __future__ import annotations

from flask import Blueprint, abort, jsonify, render_template, request
from flask_login import current_user, login_required

from services.phc_close_dates_service import (
    PhcCloseDatesError,
    ensure_phc_close_dates_menu,
    list_close_dates,
    update_all_close_dates,
    update_close_date,
)


bp = Blueprint("phc_close_dates", __name__)


def _guard(api: bool = False):
    if not bool(getattr(current_user, "ADMIN", False)):
        if api:
            return jsonify({"ok": False, "error": "Sem permissão para gerir datas fechadas."}), 403
        abort(403)
    return None


@bp.route("/phc-close-dates")
@login_required
def page():
    guarded = _guard()
    if guarded:
        return guarded
    try:
        list_close_dates()
    except PhcCloseDatesError:
        abort(404)
    return render_template("phc_close_dates.html")


@bp.route("/api/phc-close-dates")
@login_required
def api_list():
    guarded = _guard(api=True)
    if guarded:
        return guarded
    try:
        return jsonify({"ok": True, "items": list_close_dates()})
    except PhcCloseDatesError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 404


@bp.route("/api/phc-close-dates/<int:feid>", methods=["PUT"])
@login_required
def api_update(feid: int):
    guarded = _guard(api=True)
    if guarded:
        return guarded
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify({"ok": True, "item": update_close_date(feid, payload.get("value"))})
    except PhcCloseDatesError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@bp.route("/api/phc-close-dates/apply-all", methods=["POST"])
@login_required
def api_update_all():
    guarded = _guard(api=True)
    if guarded:
        return guarded
    payload = request.get_json(silent=True) or {}
    try:
        results = update_all_close_dates(payload.get("value"))
        failures = [item for item in results if not item["ok"]]
        return jsonify({"ok": not failures, "results": results, "failures": len(failures)})
    except PhcCloseDatesError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
