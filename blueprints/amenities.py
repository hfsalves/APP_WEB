"""Backoffice matrix and catalogue management for accommodation amenities."""

from __future__ import annotations

import logging

from flask import Blueprint, abort, jsonify, render_template, request
from flask_login import current_user, login_required

from blueprints.generic_crud import has_permission
from models import db
from services.amenities_service import (
    CATEGORIES,
    CATEGORY_LABELS,
    ICON_OPTIONS,
    amenity_exists,
    bulk_set_relations,
    create_amenity,
    list_amenities,
    list_matrix,
    property_in_scope,
    set_relation,
    update_amenity,
)
from services.multiempresa_service import MissingCurrentEntityError, get_current_feid


bp = Blueprint("amenities", __name__)
logger = logging.getLogger(__name__)


def _can_view() -> bool:
    return bool(getattr(current_user, "ADMIN", False) or has_permission("AL", "consultar"))


def _can_edit() -> bool:
    return bool(getattr(current_user, "ADMIN", False) or has_permission("AL", "editar"))


def _require_view() -> None:
    if not _can_view():
        abort(403)


def _require_edit() -> None:
    if not _can_edit():
        abort(403)


def _feid() -> int:
    try:
        return int(get_current_feid())
    except MissingCurrentEntityError as exc:
        abort(403, str(exc))


@bp.get("/alojamentos/comodidades")
@login_required
def page():
    _require_view()
    return render_template("amenities.html", page_title="Comodidades dos Alojamentos")


@bp.get("/api/alojamentos/comodidades")
@login_required
def state():
    _require_view()
    matrix = list_matrix(_feid())
    return jsonify({
        "ok": True,
        "properties": matrix["properties"],
        "amenities": list_amenities(include_inactive=True),
        "relations": matrix["relations"],
        "zones": matrix["zones"],
        "categories": [{"code": code, "label": CATEGORY_LABELS[code]} for code in CATEGORIES],
        "icons": list(ICON_OPTIONS),
        "can_edit": _can_edit(),
    })


@bp.put("/api/alojamentos/comodidades/relation")
@login_required
def relation():
    _require_edit()
    payload = request.get_json(silent=True) or {}
    alojamento = str(payload.get("alojamento") or "").strip()
    try:
        amenity_id = int(payload.get("amenity_id"))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Comodidade inválida."}), 400
    enabled = bool(payload.get("enabled"))
    if not property_in_scope(alojamento, _feid()):
        return jsonify({"ok": False, "error": "Alojamento inválido ou sem acesso."}), 404
    if not amenity_exists(amenity_id, active_only=enabled):
        return jsonify({"ok": False, "error": "Comodidade inválida ou inativa."}), 404
    try:
        set_relation(alojamento, amenity_id, enabled)
        db.session.commit()
        return jsonify({"ok": True, "enabled": enabled})
    except Exception:
        db.session.rollback()
        logger.exception("Erro ao atualizar relação de comodidade")
        return jsonify({"ok": False, "error": "Não foi possível guardar a alteração."}), 500


@bp.put("/api/alojamentos/comodidades/bulk")
@login_required
def bulk_relation():
    _require_edit()
    payload = request.get_json(silent=True) or {}
    try:
        amenity_id = int(payload.get("amenity_id"))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Comodidade inválida."}), 400
    enabled = bool(payload.get("enabled"))
    alojamentos = payload.get("alojamentos")
    if not isinstance(alojamentos, list) or len(alojamentos) > 1000:
        return jsonify({"ok": False, "error": "Lista de alojamentos inválida."}), 400
    if not amenity_exists(amenity_id, active_only=enabled):
        return jsonify({"ok": False, "error": "Comodidade inválida ou inativa."}), 404
    try:
        count = bulk_set_relations(alojamentos, amenity_id, enabled, _feid())
        return jsonify({"ok": True, "count": count, "enabled": enabled})
    except PermissionError as exc:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(exc)}), 403
    except Exception:
        db.session.rollback()
        logger.exception("Erro na operação em massa de comodidades")
        return jsonify({"ok": False, "error": "Não foi possível concluir a operação em massa."}), 500


@bp.post("/api/alojamentos/comodidades/catalog")
@login_required
def catalog_create():
    _require_edit()
    try:
        item = create_amenity(request.get_json(silent=True) or {})
        return jsonify({"ok": True, "item": item}), 201
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception:
        db.session.rollback()
        logger.exception("Erro ao criar comodidade")
        return jsonify({"ok": False, "error": "Não foi possível criar a comodidade."}), 500


@bp.put("/api/alojamentos/comodidades/catalog/<int:amenity_id>")
@login_required
def catalog_update(amenity_id: int):
    _require_edit()
    try:
        item = update_amenity(amenity_id, request.get_json(silent=True) or {})
        return jsonify({"ok": True, "item": item})
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(exc)}), 400
    except LookupError as exc:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(exc)}), 404
    except Exception:
        db.session.rollback()
        logger.exception("Erro ao editar comodidade")
        return jsonify({"ok": False, "error": "Não foi possível guardar a comodidade."}), 500
