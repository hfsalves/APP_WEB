from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from models import Acessos
from services.push_service import (
    PushConfigurationError,
    deactivate_push_subscription,
    get_user_push_summary,
    get_vapid_public_key,
    save_push_subscription,
    send_event_notification,
    send_push_to_user,
)


bp = Blueprint("push_notifications", __name__)


def _has_permission(table_name: str, action: str) -> bool:
    if getattr(current_user, "ADMIN", False):
        return True
    row = (
        Acessos.query
        .filter_by(utilizador=current_user.LOGIN, tabela=table_name)
        .first()
    )
    if not row:
        return False
    return bool(getattr(row, action, False))


def _can_send_manual() -> bool:
    return bool(getattr(current_user, "ADMIN", False) or _has_permission("PUSH", "editar"))


def _can_view_user_push(userstamp: str) -> bool:
    stamp = str(userstamp or "").strip()
    if not stamp:
        return False
    if getattr(current_user, "ADMIN", False):
        return True
    if str(getattr(current_user, "USSTAMP", "") or "").strip() == stamp:
        return True
    return _has_permission("PUSH", "consultar")


@bp.get("/api/push/public-key")
@login_required
def api_push_public_key():
    try:
        return jsonify({"publicKey": get_vapid_public_key()})
    except PushConfigurationError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.post("/api/push/subscribe")
@login_required
def api_push_subscribe():
    payload = request.get_json(silent=True) or {}
    subscription = payload.get("subscription") or payload
    try:
        data = save_push_subscription(
            current_user.USSTAMP,
            subscription,
            platform=payload.get("platform"),
            useragent=payload.get("userAgent"),
            device_label=payload.get("deviceLabel"),
        )
        return jsonify({"ok": True, "device": data})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.post("/api/push/unsubscribe")
@login_required
def api_push_unsubscribe():
    payload = request.get_json(silent=True) or {}
    endpoint = payload.get("endpoint")
    pushdevstamp = payload.get("pushdevstamp")
    try:
        count = deactivate_push_subscription(endpoint=endpoint, pushdevstamp=pushdevstamp)
        return jsonify({"ok": True, "deactivated": count})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.post("/api/push/send-manual")
@login_required
def api_push_send_manual():
    if not _can_send_manual():
        return jsonify({"error": "Sem permissão para enviar notificações manuais."}), 403
    payload = request.get_json(silent=True) or {}
    userstamp = str(payload.get("userstamp") or "").strip()
    title = str(payload.get("title") or "").strip()
    body = str(payload.get("body") or "").strip()
    target_url = str(payload.get("target_url") or payload.get("url") or "").strip()
    if not userstamp:
        return jsonify({"error": "Utilizador em falta."}), 400
    if not title:
        return jsonify({"error": "Título obrigatório."}), 400
    if not body:
        return jsonify({"error": "Mensagem obrigatória."}), 400
    try:
        result = send_push_to_user(
            userstamp,
            title,
            body,
            url=target_url or "/",
            event_type="MANUAL",
            sent_by_userstamp=current_user.USSTAMP,
            extra_payload={"url": target_url or "/"},
        )
        return jsonify({"ok": True, "result": result})
    except PushConfigurationError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.post("/api/push/test-self")
@login_required
def api_push_test_self():
    try:
        result = send_event_notification(
            "MANUAL",
            current_user.USSTAMP,
            context={
                "title": "Teste de notificações",
                "body": "As notificações push da app estão ativas neste dispositivo.",
                "url": "/monitor",
            },
            sent_by_userstamp=current_user.USSTAMP,
        )
        return jsonify({"ok": True, "result": result})
    except PushConfigurationError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.get("/api/push/user/<userstamp>/summary")
@login_required
def api_push_user_summary(userstamp):
    if not _can_view_user_push(userstamp):
        return jsonify({"error": "Sem permissão para consultar notificações deste utilizador."}), 403
    try:
        data = get_user_push_summary(userstamp)
        data["can_send_manual"] = _can_send_manual()
        data["is_self"] = str(current_user.USSTAMP or "").strip() == str(userstamp or "").strip()
        return jsonify(data)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
