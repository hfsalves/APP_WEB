import os

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import bindparam, text

from models import Acessos, db
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

DEFAULT_INTEGRATION_TOKEN = "w2QBCh_4pNBvznHUTLngsQLWbICbnGeD7o2llLZP_oi1LywZSnVNj5UPByWsL6UC"


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


def _text(value, default="") -> str:
    if value is None:
        return default
    return str(value).strip()


def _as_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        values = value
    else:
        values = [value]
    out = []
    for item in values:
        text_value = _text(item)
        if text_value:
            out.append(text_value)
    return out


def _integration_token() -> str:
    return (
        _text(current_app.config.get("NOTIFICATION_API_TOKEN"))
        or _text(current_app.config.get("SYNC_ENGINE_TOKEN"))
        or _text(current_app.config.get("INTEGRATION_API_TOKEN"))
        or _text(os.environ.get("NOTIFICATION_API_TOKEN"))
        or _text(os.environ.get("SYNC_ENGINE_TOKEN"))
        or _text(os.environ.get("INTEGRATION_API_TOKEN"))
        or DEFAULT_INTEGRATION_TOKEN
    )


def _require_integration_token():
    expected = _integration_token()
    auth = _text(request.headers.get("Authorization"))
    received = ""
    if auth.lower().startswith("bearer "):
        received = auth[7:].strip()
    if not received:
        received = _text(request.headers.get("X-Internal-Token") or request.args.get("token"))
    if not expected or received != expected:
        return jsonify({"error": "Unauthorized"}), 401
    return None


def _userstamps_from_logins(logins: list[str]) -> list[str]:
    if not logins:
        return []
    rows = db.session.execute(text("""
        SELECT USSTAMP
        FROM dbo.US
        WHERE UPPER(LTRIM(RTRIM(ISNULL(LOGIN,'')))) IN :logins
          AND ISNULL(USSTAMP,'') <> ''
          AND ISNULL(INATIVO,0) = 0
    """).bindparams(bindparam("logins", expanding=True)), {
        "logins": [item.strip().upper() for item in logins if item.strip()],
    }).mappings().all()
    return [_text(row.get("USSTAMP")) for row in rows if _text(row.get("USSTAMP"))]


def _userstamps_from_teams(teams: list[str]) -> list[str]:
    if not teams:
        return []
    rows = db.session.execute(text("""
        SELECT USSTAMP
        FROM dbo.US
        WHERE UPPER(LTRIM(RTRIM(ISNULL(EQUIPA,'')))) IN :teams
          AND ISNULL(USSTAMP,'') <> ''
          AND ISNULL(INATIVO,0) = 0
    """).bindparams(bindparam("teams", expanding=True)), {
        "teams": [item.strip().upper() for item in teams if item.strip()],
    }).mappings().all()
    return [_text(row.get("USSTAMP")) for row in rows if _text(row.get("USSTAMP"))]


def _all_active_userstamps() -> list[str]:
    rows = db.session.execute(text("""
        SELECT USSTAMP
        FROM dbo.US
        WHERE ISNULL(USSTAMP,'') <> ''
          AND ISNULL(INATIVO,0) = 0
        ORDER BY ISNULL(NOME,''), ISNULL(LOGIN,'')
    """)).mappings().all()
    return [_text(row.get("USSTAMP")) for row in rows if _text(row.get("USSTAMP"))]


def _resolve_notification_targets(payload: dict) -> list[str]:
    targets = payload.get("targets") if isinstance(payload.get("targets"), dict) else {}
    recipients = payload.get("recipients") if isinstance(payload.get("recipients"), dict) else {}
    sources = [payload, targets, recipients]

    userstamps = []
    logins = []
    teams = []
    broadcast = False
    for source in sources:
        userstamps.extend(_as_list(source.get("userstamp")))
        userstamps.extend(_as_list(source.get("userstamps")))
        userstamps.extend(_as_list(source.get("user")))
        userstamps.extend(_as_list(source.get("users")))
        logins.extend(_as_list(source.get("login")))
        logins.extend(_as_list(source.get("logins")))
        teams.extend(_as_list(source.get("team")))
        teams.extend(_as_list(source.get("teams")))
        teams.extend(_as_list(source.get("equipa")))
        teams.extend(_as_list(source.get("equipas")))
        broadcast = broadcast or bool(source.get("broadcast") or source.get("all"))

    resolved = []
    if broadcast:
        resolved.extend(_all_active_userstamps())
    resolved.extend(userstamps)
    resolved.extend(_userstamps_from_logins(logins))
    resolved.extend(_userstamps_from_teams(teams))

    deduped = []
    seen = set()
    for stamp in resolved:
        clean = _text(stamp)
        key = clean.upper()
        if clean and key not in seen:
            seen.add(key)
            deduped.append(clean)
    return deduped


def _idempotency_already_processed(idempotency_key: str) -> bool:
    key = _text(idempotency_key)
    if not key:
        return False
    try:
        row = db.session.execute(text("""
            SELECT TOP 1 1
            FROM dbo.PUSH_LOG
            WHERE JSON_VALUE(PAYLOAD, '$.idempotency_key') = :key
        """), {"key": key}).first()
        return row is not None
    except Exception:
        pattern = f'%"{key}"%'
        row = db.session.execute(text("""
            SELECT TOP 1 1
            FROM dbo.PUSH_LOG
            WHERE PAYLOAD LIKE :pattern
        """), {"pattern": pattern}).first()
        return row is not None


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


@bp.post("/api/integrations/notifications/events")
def api_integration_notification_event():
    denied = _require_integration_token()
    if denied:
        return denied

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"error": "Payload JSON invalido."}), 400

    event_type = _text(payload.get("event_type") or payload.get("event") or "MANUAL").upper()
    context = payload.get("context") if isinstance(payload.get("context"), dict) else {}
    context = dict(context)

    title = _text(payload.get("title"))
    body = _text(payload.get("body") or payload.get("message"))
    target_url = _text(payload.get("target_url") or payload.get("url") or context.get("url"))
    idempotency_key = _text(payload.get("idempotency_key") or payload.get("external_id"))

    for key in (
        "reservation_code",
        "reserva",
        "alojamento",
        "checkin",
        "checkout",
        "hospede",
        "origem",
        "source",
    ):
        if key in payload and key not in context:
            context[key] = payload.get(key)
    if title:
        context["title"] = title
    if body:
        context["body"] = body
    if target_url:
        context["url"] = target_url
    if idempotency_key:
        context["idempotency_key"] = idempotency_key

    if idempotency_key and _idempotency_already_processed(idempotency_key):
        return jsonify({
            "ok": True,
            "duplicate": True,
            "idempotency_key": idempotency_key,
            "sent": 0,
            "targets": 0,
            "results": [],
        })

    userstamps = _resolve_notification_targets(payload)
    if not userstamps:
        return jsonify({
            "error": "Destinatarios em falta. Usa userstamps, logins, teams/equipas ou broadcast=true."
        }), 400

    if payload.get("dry_run"):
        return jsonify({
            "ok": True,
            "dry_run": True,
            "event_type": event_type,
            "targets": len(userstamps),
            "userstamps": userstamps,
        })

    try:
        results = []
        for userstamp in userstamps:
            result = send_event_notification(
                event_type,
                userstamp,
                context=context,
                sent_by_userstamp=None,
            )
            result["userstamp"] = userstamp
            results.append(result)

        sent = sum(int(item.get("sent") or 0) for item in results)
        devices = sum(int(item.get("devices") or 0) for item in results)
        return jsonify({
            "ok": True,
            "event_type": event_type,
            "idempotency_key": idempotency_key or None,
            "targets": len(userstamps),
            "devices": devices,
            "sent": sent,
            "status": "SENT" if sent else "FAILED",
            "results": results,
        })
    except PushConfigurationError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception("Erro ao processar evento externo de notificacao.")
        return jsonify({"error": str(exc)}), 500


@bp.post("/api/integrations/notifications/send")
def api_integration_notification_send():
    denied = _require_integration_token()
    if denied:
        return denied

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"error": "Payload JSON invalido."}), 400

    login = _text(
        payload.get("login")
        or payload.get("LOGIN")
        or payload.get("utilizador")
        or payload.get("user")
    )
    assunto = _text(
        payload.get("assunto")
        or payload.get("subject")
        or payload.get("title")
        or payload.get("titulo")
    )
    texto = _text(
        payload.get("texto")
        or payload.get("text")
        or payload.get("body")
        or payload.get("mensagem")
        or payload.get("message")
    )
    target_url = _text(payload.get("url") or payload.get("target_url")) or "/"

    if not login:
        return jsonify({"error": "LOGIN em falta."}), 400
    if not assunto:
        return jsonify({"error": "Assunto em falta."}), 400
    if not texto:
        return jsonify({"error": "Texto em falta."}), 400

    userstamps = _userstamps_from_logins([login])
    if not userstamps:
        return jsonify({"error": f"Utilizador nao encontrado ou inativo: {login}"}), 404

    if payload.get("dry_run"):
        return jsonify({
            "ok": True,
            "dry_run": True,
            "login": login,
            "userstamp": userstamps[0],
            "assunto": assunto,
            "texto": texto,
            "url": target_url,
        })

    try:
        result = send_push_to_user(
            userstamps[0],
            assunto,
            texto,
            url=target_url,
            event_type=_text(payload.get("event_type")) or "MANUAL",
            sent_by_userstamp=None,
            extra_payload={
                "login": login,
                "url": target_url,
                "source": "integration_api",
            },
        )
        return jsonify({
            "ok": True,
            "login": login,
            "userstamp": userstamps[0],
            "result": result,
        })
    except PushConfigurationError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception("Erro ao enviar notificacao externa direta.")
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
