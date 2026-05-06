import base64
import hashlib
import json
import uuid
from datetime import datetime

from flask import current_app
from sqlalchemy import text
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid

from models import db
from services.qr_atcud_service import get_param


DEFAULT_NOTIFICATION_EVENTS = [
    "CLEANING_ASSIGNED",
    "MAINTENANCE_ASSIGNED",
    "TASK_REASSIGNED",
    "TASK_OVERDUE",
    "MANUAL",
]


class PushConfigurationError(RuntimeError):
    pass


def _new_stamp() -> str:
    return uuid.uuid4().hex.upper()[:25]


def _safe_text(value, default="") -> str:
    if value is None:
        return default
    return str(value).strip()


def _normalize_event_type(event_type: str) -> str:
    code = _safe_text(event_type).upper()
    return code or "MANUAL"


def _endpoint_hash(endpoint: str) -> str:
    return hashlib.sha256(_safe_text(endpoint).encode("utf-8")).hexdigest().upper()


def _json_dumps(value) -> str:
    return json.dumps(value or {}, ensure_ascii=False, default=str)


def _table_columns(table_name: str) -> set[str]:
    rows = db.session.execute(text("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = :table_name
    """), {"table_name": table_name}).mappings().all()
    return {str(r.get("COLUMN_NAME") or "").strip().upper() for r in rows}


def _column_exists(table_name: str, column_name: str) -> bool:
    return _safe_text(column_name).upper() in _table_columns(table_name)


def _table_exists(table_name: str) -> bool:
    row = db.session.execute(text("""
        SELECT 1
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = :table_name
    """), {"table_name": table_name}).fetchone()
    return row is not None


def _param_value(code: str, default=None):
    env_value = current_app.config.get(code)
    if env_value not in (None, ""):
        return env_value
    try:
        value = get_param(db.session, code, default)
    except Exception:
        value = default
    return value


def _get_vapid_config() -> dict:
    public_key = _safe_text(_param_value("VAPID_PUBLIC_KEY", ""))
    private_key = _load_vapid_private_key()
    subject = _safe_text(_param_value("VAPID_SUBJECT", ""))
    if not public_key or not private_key or not subject:
        raise PushConfigurationError(
            "Configuracao VAPID em falta. Preenche VAPID_PUBLIC_KEY, VAPID_SUBJECT e a chave privada em VAPID_PRIVATE_KEY, VAPID_PRIVATE_KEY_B64 ou VAPID_PRIVATE_KEY_1/_2/_3."
        )
    return {
        "public_key": public_key,
        "private_key": private_key,
        "subject": subject,
    }


def get_vapid_public_key() -> str:
    return _get_vapid_config()["public_key"]


def _private_key_to_vapid(private_key) -> Vapid:
    return Vapid(private_key)


def _private_key_from_raw_scalar(key_bytes: bytes):
    if len(key_bytes) != 32:
        return None
    scalar = int.from_bytes(key_bytes, byteorder="big")
    if scalar <= 0:
        return None
    return ec.derive_private_key(scalar, ec.SECP256R1())


def _normalize_private_key_bytes(key_bytes: bytes) -> Vapid | None:
    data = bytes(key_bytes or b"").strip()
    if not data:
        return None

    if b"BEGIN" in data:
        data = data.replace(b"\\r\\n", b"\n").replace(b"\\n", b"\n")
        private_key = serialization.load_pem_private_key(data, password=None)
        return _private_key_to_vapid(private_key)

    try:
        private_key = serialization.load_der_private_key(data, password=None)
        return _private_key_to_vapid(private_key)
    except Exception:
        pass

    private_key = _private_key_from_raw_scalar(data)
    if private_key is not None:
        return _private_key_to_vapid(private_key)

    return None


def _normalize_private_key_value(raw_value: str) -> Vapid | str:
    value = _safe_text(raw_value)
    if not value:
        return ""
    value = value.strip().strip('"').strip("'").replace("\\r\\n", "\n").replace("\\n", "\n")

    if "BEGIN PRIVATE KEY" in value:
        try:
            return _normalize_private_key_bytes(value.encode("utf-8"))
        except Exception as exc:
            raise PushConfigurationError(
                "Chave privada VAPID invalida. Confirma se o valor em VAPID_PRIVATE_KEY e uma chave privada PEM PKCS8 completa."
            ) from exc

    compact_value = "".join(value.split())
    decoded_candidates = []
    for candidate in [compact_value, value]:
        candidate = _safe_text(candidate)
        if not candidate:
            continue
        padded = candidate + ("=" * ((4 - len(candidate) % 4) % 4))
        try:
            decoded_candidates.append(base64.urlsafe_b64decode(padded.encode("utf-8")))
        except Exception:
            pass
        try:
            decoded_candidates.append(base64.b64decode(padded.encode("utf-8")))
        except Exception:
            pass

    for key_bytes in decoded_candidates:
        try:
            vapid = _normalize_private_key_bytes(key_bytes)
            if vapid is not None:
                return vapid
        except Exception:
            pass

    raise PushConfigurationError(
        "Chave privada VAPID invalida. Usa uma chave privada P-256 em PEM, DER/base64 ou no formato compacto de 32 bytes gerado para Web Push."
    )


def _load_vapid_private_key() -> Vapid | str:
    direct = _safe_text(_param_value("VAPID_PRIVATE_KEY", ""))
    if direct:
        return _normalize_private_key_value(direct)

    compact = _safe_text(_param_value("VAPID_PRIVATE_KEY_B64", ""))
    if compact:
        return _normalize_private_key_value(compact)

    parts = []
    for idx in range(1, 10):
        part = _safe_text(_param_value(f"VAPID_PRIVATE_KEY_{idx}", ""))
        if not part:
            break
        parts.append(part)
    if parts:
        return _normalize_private_key_value("".join(parts))
    return ""


def _load_user_row(userstamp: str):
    usstamp = _safe_text(userstamp)
    if not usstamp:
        return None
    cols = _table_columns("US")
    select_parts = [
        "USSTAMP",
        "ISNULL(LOGIN,'') AS LOGIN",
        "ISNULL(NOME,'') AS NOME",
        "ISNULL(EQUIPA,'') AS EQUIPA",
    ]
    if "INATIVO" in cols:
        select_parts.append("ISNULL(INATIVO,0) AS INATIVO")
    else:
        select_parts.append("0 AS INATIVO")
    row = db.session.execute(text(f"""
        SELECT TOP 1 {", ".join(select_parts)}
        FROM dbo.US
        WHERE USSTAMP = :userstamp
    """), {"userstamp": usstamp}).mappings().first()
    return dict(row) if row else None


def _load_users_by_team(team_name: str) -> list[dict]:
    team = _safe_text(team_name)
    if not team:
        return []
    cols = _table_columns("US")
    where_parts = ["LTRIM(RTRIM(ISNULL(EQUIPA,''))) = :equipa"]
    if "INATIVO" in cols:
        where_parts.append("ISNULL(INATIVO,0) = 0")
    rows = db.session.execute(text(f"""
        SELECT USSTAMP, ISNULL(LOGIN,'') AS LOGIN, ISNULL(NOME,'') AS NOME
        FROM dbo.US
        WHERE {" AND ".join(where_parts)}
        ORDER BY NOME, LOGIN
    """), {"equipa": team}).mappings().all()
    return [dict(r) for r in rows]


def _ensure_user_default_preferences(userstamp: str):
    usstamp = _safe_text(userstamp)
    if not usstamp or not _table_exists("NOTIF_PREF"):
        return
    for event_type in DEFAULT_NOTIFICATION_EVENTS:
        db.session.execute(text("""
            IF NOT EXISTS (
                SELECT 1
                FROM dbo.NOTIF_PREF
                WHERE USERSTAMP = :userstamp
                  AND UPPER(LTRIM(RTRIM(EVENT_TYPE))) = :event_type
            )
            BEGIN
                INSERT INTO dbo.NOTIF_PREF
                (
                    NOTIFPREFSTAMP, USERSTAMP, EVENT_TYPE, PUSH_ENABLED, CREATED_AT, UPDATED_AT
                )
                VALUES
                (
                    :stamp, :userstamp, :event_type, 1, GETDATE(), NULL
                )
            END
        """), {
            "stamp": _new_stamp(),
            "userstamp": usstamp,
            "event_type": event_type,
        })
    db.session.commit()


def _preference_enabled(userstamp: str, event_type: str) -> bool:
    usstamp = _safe_text(userstamp)
    code = _normalize_event_type(event_type)
    if not usstamp or code == "MANUAL":
        # Envio manual ignora preferencia para permitir contacto explicito do backoffice.
        return True
    _ensure_user_default_preferences(usstamp)
    row = db.session.execute(text("""
        SELECT TOP 1 ISNULL(PUSH_ENABLED,1) AS PUSH_ENABLED
        FROM dbo.NOTIF_PREF
        WHERE USERSTAMP = :userstamp
          AND UPPER(LTRIM(RTRIM(EVENT_TYPE))) = :event_type
    """), {"userstamp": usstamp, "event_type": code}).mappings().first()
    return bool((row or {}).get("PUSH_ENABLED", 1))


def _active_devices_for_user(userstamp: str) -> list[dict]:
    usstamp = _safe_text(userstamp)
    if not usstamp:
        return []
    rows = db.session.execute(text("""
        SELECT
            PUSHDEVSTAMP,
            USERSTAMP,
            ENDPOINT,
            P256DH,
            AUTH,
            ISNULL(PLATFORM,'') AS PLATFORM,
            ISNULL(USERAGENT,'') AS USERAGENT,
            ISNULL(DEVICE_LABEL,'') AS DEVICE_LABEL,
            ISNULL(IS_ACTIVE,1) AS IS_ACTIVE
        FROM dbo.PUSH_DEVICE
        WHERE USERSTAMP = :userstamp
          AND ISNULL(IS_ACTIVE,1) = 1
        ORDER BY ISNULL(LAST_SEEN, CREATED_AT) DESC, CREATED_AT DESC
    """), {"userstamp": usstamp}).mappings().all()
    return [dict(r) for r in rows]


def _log_push(
    *,
    userstamp: str | None,
    pushdevstamp: str | None,
    sent_by_userstamp: str | None,
    event_type: str,
    title: str,
    body: str,
    target_url: str | None,
    payload,
    status: str,
    response_info: str | None = None,
    sent_at=None,
) -> str:
    stamp = _new_stamp()
    db.session.execute(text("""
        INSERT INTO dbo.PUSH_LOG
        (
            PUSHLOGSTAMP, USERSTAMP, PUSHDEVSTAMP, SENT_BY_USERSTAMP, EVENT_TYPE,
            TITLE, BODY, TARGET_URL, PAYLOAD, STATUS, RESPONSE_INFO, CREATED_AT, SENT_AT
        )
        VALUES
        (
            :stamp, :userstamp, :pushdevstamp, :sent_by, :event_type,
            :title, :body, :target_url, :payload, :status, :response_info, GETDATE(), :sent_at
        )
    """), {
        "stamp": stamp,
        "userstamp": _safe_text(userstamp) or None,
        "pushdevstamp": _safe_text(pushdevstamp) or None,
        "sent_by": _safe_text(sent_by_userstamp) or None,
        "event_type": _normalize_event_type(event_type),
        "title": _safe_text(title),
        "body": _safe_text(body),
        "target_url": _safe_text(target_url) or None,
        "payload": _json_dumps(payload),
        "status": _safe_text(status).upper() or "PENDING",
        "response_info": _safe_text(response_info) or None,
        "sent_at": sent_at,
    })
    db.session.commit()
    return stamp


def save_push_subscription(userstamp: str, subscription: dict, platform=None, useragent=None, device_label=None) -> dict:
    usstamp = _safe_text(userstamp)
    endpoint = _safe_text((subscription or {}).get("endpoint"))
    keys = (subscription or {}).get("keys") or {}
    p256dh = _safe_text(keys.get("p256dh"))
    auth = _safe_text(keys.get("auth"))

    if not usstamp:
        raise ValueError("Utilizador invalido.")
    if not endpoint or not p256dh or not auth:
        raise ValueError("Subscription incompleta.")

    endpoint_hash = _endpoint_hash(endpoint)
    row = db.session.execute(text("""
        SELECT TOP 1 PUSHDEVSTAMP
        FROM dbo.PUSH_DEVICE
        WHERE ENDPOINT_HASH = :endpoint_hash
    """), {"endpoint_hash": endpoint_hash}).mappings().first()

    payload = {
        "userstamp": usstamp,
        "platform": _safe_text(platform),
        "useragent": _safe_text(useragent),
        "device_label": _safe_text(device_label),
    }

    if row:
        pushdevstamp = _safe_text(row.get("PUSHDEVSTAMP"))
        db.session.execute(text("""
            UPDATE dbo.PUSH_DEVICE
            SET USERSTAMP = :userstamp,
                ENDPOINT = :endpoint,
                P256DH = :p256dh,
                AUTH = :auth,
                PLATFORM = :platform,
                USERAGENT = :useragent,
                DEVICE_LABEL = :device_label,
                IS_ACTIVE = 1,
                LAST_SEEN = GETDATE(),
                UPDATED_AT = GETDATE(),
                LAST_ERROR_AT = NULL,
                LAST_ERROR_MSG = NULL
            WHERE PUSHDEVSTAMP = :pushdevstamp
        """), {
            "pushdevstamp": pushdevstamp,
            "userstamp": usstamp,
            "endpoint": endpoint,
            "p256dh": p256dh,
            "auth": auth,
            "platform": _safe_text(platform) or None,
            "useragent": _safe_text(useragent)[:500] or None,
            "device_label": _safe_text(device_label)[:100] or None,
        })
    else:
        pushdevstamp = _new_stamp()
        db.session.execute(text("""
            INSERT INTO dbo.PUSH_DEVICE
            (
                PUSHDEVSTAMP, USERSTAMP, ENDPOINT, ENDPOINT_HASH, P256DH, AUTH,
                PLATFORM, USERAGENT, DEVICE_LABEL, IS_ACTIVE,
                LAST_SEEN, CREATED_AT, UPDATED_AT
            )
            VALUES
            (
                :pushdevstamp, :userstamp, :endpoint, :endpoint_hash, :p256dh, :auth,
                :platform, :useragent, :device_label, 1,
                GETDATE(), GETDATE(), GETDATE()
            )
        """), {
            "pushdevstamp": pushdevstamp,
            "userstamp": usstamp,
            "endpoint": endpoint,
            "endpoint_hash": endpoint_hash,
            "p256dh": p256dh,
            "auth": auth,
            "platform": _safe_text(platform) or None,
            "useragent": _safe_text(useragent)[:500] or None,
            "device_label": _safe_text(device_label)[:100] or None,
        })
    db.session.commit()
    return {
        "pushdevstamp": pushdevstamp,
        "endpoint_hash": endpoint_hash,
        **payload,
    }


def deactivate_push_subscription(endpoint=None, pushdevstamp=None) -> int:
    endpoint_hash = _endpoint_hash(endpoint) if endpoint else None
    stamp = _safe_text(pushdevstamp)
    if not endpoint_hash and not stamp:
        return 0
    res = db.session.execute(text("""
        UPDATE dbo.PUSH_DEVICE
        SET IS_ACTIVE = 0,
            UPDATED_AT = GETDATE()
        WHERE (:pushdevstamp IS NOT NULL AND PUSHDEVSTAMP = :pushdevstamp)
           OR (:endpoint_hash IS NOT NULL AND ENDPOINT_HASH = :endpoint_hash)
    """), {
        "pushdevstamp": stamp or None,
        "endpoint_hash": endpoint_hash or None,
    })
    db.session.commit()
    return int(res.rowcount or 0)


def _build_push_payload(title: str, body: str, url=None, event_type="MANUAL", extra_payload=None) -> dict:
    payload = {
        "title": _safe_text(title),
        "body": _safe_text(body),
        "url": _safe_text(url) or "/",
        "icon": "/static/icons/icon-192.png",
        "badge": "/static/icons/icon-192.png",
        "eventType": _normalize_event_type(event_type),
    }
    if isinstance(extra_payload, dict):
        payload.update(extra_payload)
    return payload


def send_push_to_device(pushdevstamp: str, title: str, body: str, url=None, event_type="MANUAL", sent_by_userstamp=None, extra_payload=None) -> dict:
    stamp = _safe_text(pushdevstamp)
    if not stamp:
        raise ValueError("Dispositivo invalido.")
    row = db.session.execute(text("""
        SELECT TOP 1
            PUSHDEVSTAMP, USERSTAMP, ENDPOINT, P256DH, AUTH, ISNULL(IS_ACTIVE,1) AS IS_ACTIVE
        FROM dbo.PUSH_DEVICE
        WHERE PUSHDEVSTAMP = :pushdevstamp
    """), {"pushdevstamp": stamp}).mappings().first()
    if not row:
        return {"status": "NOT_FOUND", "pushdevstamp": stamp}
    device = dict(row)
    if not bool(device.get("IS_ACTIVE", 1)):
        return {"status": "INACTIVE", "pushdevstamp": stamp}

    try:
        from pywebpush import WebPushException, webpush
    except Exception as exc:
        raise PushConfigurationError(
            "Biblioteca pywebpush indisponivel. Instala-a no ambiente Python."
        ) from exc

    vapid = _get_vapid_config()
    payload = _build_push_payload(title, body, url, event_type, extra_payload)
    subscription = {
        "endpoint": device["ENDPOINT"],
        "keys": {
            "p256dh": device["P256DH"],
            "auth": device["AUTH"],
        },
    }
    try:
        webpush(
            subscription_info=subscription,
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=vapid["private_key"],
            vapid_claims={"sub": vapid["subject"]},
            ttl=60,
        )
        db.session.execute(text("""
            UPDATE dbo.PUSH_DEVICE
            SET LAST_PUSH_AT = GETDATE(),
                LAST_SEEN = GETDATE(),
                UPDATED_AT = GETDATE(),
                LAST_ERROR_AT = NULL,
                LAST_ERROR_MSG = NULL
            WHERE PUSHDEVSTAMP = :pushdevstamp
        """), {"pushdevstamp": stamp})
        db.session.commit()
        _log_push(
            userstamp=device.get("USERSTAMP"),
            pushdevstamp=stamp,
            sent_by_userstamp=sent_by_userstamp,
            event_type=event_type,
            title=title,
            body=body,
            target_url=url,
            payload=payload,
            status="SENT",
            response_info="OK",
            sent_at=datetime.now(),
        )
        return {"status": "SENT", "pushdevstamp": stamp}
    except WebPushException as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        message = _safe_text(str(exc))[:1000]
        is_invalid = status_code in (404, 410)
        db.session.execute(text("""
            UPDATE dbo.PUSH_DEVICE
            SET IS_ACTIVE = CASE WHEN :deactivate = 1 THEN 0 ELSE IS_ACTIVE END,
                UPDATED_AT = GETDATE(),
                LAST_ERROR_AT = GETDATE(),
                LAST_ERROR_MSG = :message
            WHERE PUSHDEVSTAMP = :pushdevstamp
        """), {
            "deactivate": 1 if is_invalid else 0,
            "message": message,
            "pushdevstamp": stamp,
        })
        db.session.commit()
        _log_push(
            userstamp=device.get("USERSTAMP"),
            pushdevstamp=stamp,
            sent_by_userstamp=sent_by_userstamp,
            event_type=event_type,
            title=title,
            body=body,
            target_url=url,
            payload=payload,
            status="FAILED",
            response_info=f"{status_code or 'ERR'} {message}",
            sent_at=datetime.now(),
        )
        return {"status": "FAILED", "pushdevstamp": stamp, "status_code": status_code, "message": message}


def send_push_to_user(userstamp: str, title: str, body: str, url=None, event_type="MANUAL", sent_by_userstamp=None, extra_payload=None) -> dict:
    usstamp = _safe_text(userstamp)
    if not usstamp:
        raise ValueError("Utilizador invalido.")
    if not _preference_enabled(usstamp, event_type):
        return {"status": "SKIPPED_PREF", "devices": 0, "results": []}

    devices = _active_devices_for_user(usstamp)
    if not devices:
        return {"status": "NO_DEVICES", "devices": 0, "results": []}

    results = []
    for device in devices:
        result = send_push_to_device(
            device.get("PUSHDEVSTAMP"),
            title,
            body,
            url=url,
            event_type=event_type,
            sent_by_userstamp=sent_by_userstamp,
            extra_payload=extra_payload,
        )
        results.append(result)

    sent_count = sum(1 for item in results if item.get("status") == "SENT")
    return {
        "status": "SENT" if sent_count else "FAILED",
        "devices": len(devices),
        "sent": sent_count,
        "results": results,
    }


def _event_message(event_type: str, context=None) -> tuple[str, str, str]:
    ctx = context or {}
    code = _normalize_event_type(event_type)
    if code == "CLEANING_ASSIGNED":
        alojamento = _safe_text(ctx.get("alojamento"), "Alojamento")
        data_txt = _safe_text(ctx.get("data"))
        hora_txt = _safe_text(ctx.get("hora"))
        when = " ".join(part for part in [data_txt, hora_txt] if part)
        body = f"{alojamento}{' - ' + when if when else ''}"
        return "Nova limpeza atribuída", body, _safe_text(ctx.get("url")) or "/monitor"
    if code == "MAINTENANCE_ASSIGNED":
        title = "Nova manutenção atribuída"
        body = _safe_text(ctx.get("body")) or "Tens uma nova manutenção."
        return title, body, _safe_text(ctx.get("url")) or "/monitor"
    if code == "TASK_REASSIGNED":
        title = "Tarefa reagendada"
        body = _safe_text(ctx.get("body")) or "Foi reagendada uma tarefa associada ao teu trabalho."
        return title, body, _safe_text(ctx.get("url")) or "/monitor"
    if code == "TASK_OVERDUE":
        title = "Tarefa em atraso"
        body = _safe_text(ctx.get("body")) or "Tens uma tarefa por tratar."
        return title, body, _safe_text(ctx.get("url")) or "/monitor"
    return (
        _safe_text(ctx.get("title"), "Notificação"),
        _safe_text(ctx.get("body"), ""),
        _safe_text(ctx.get("url")) or "/",
    )


def send_event_notification(event_type: str, userstamp: str, context=None, sent_by_userstamp=None) -> dict:
    title, body, url = _event_message(event_type, context)
    extra_payload = dict(context or {})
    return send_push_to_user(
        userstamp,
        title,
        body,
        url=url,
        event_type=event_type,
        sent_by_userstamp=sent_by_userstamp,
        extra_payload=extra_payload,
    )


def send_push_to_team(team_name: str, event_type: str, context=None, sent_by_userstamp=None) -> dict:
    users = _load_users_by_team(team_name)
    results = []
    for user in users:
        results.append(send_event_notification(event_type, user.get("USSTAMP"), context=context, sent_by_userstamp=sent_by_userstamp))
    sent = sum(1 for item in results if item.get("status") == "SENT")
    return {"team": _safe_text(team_name), "users": len(users), "sent": sent, "results": results}


def cleanup_invalid_subscriptions() -> int:
    res = db.session.execute(text("""
        UPDATE dbo.PUSH_DEVICE
        SET IS_ACTIVE = 0,
            UPDATED_AT = GETDATE()
        WHERE ISNULL(IS_ACTIVE,1) = 1
          AND LAST_ERROR_AT IS NOT NULL
          AND (
                UPPER(ISNULL(LAST_ERROR_MSG,'')) LIKE '%404%'
             OR UPPER(ISNULL(LAST_ERROR_MSG,'')) LIKE '%410%'
          )
    """))
    db.session.commit()
    return int(res.rowcount or 0)


def get_user_push_summary(userstamp: str, limit_logs: int = 5) -> dict:
    usstamp = _safe_text(userstamp)
    if not usstamp:
        raise ValueError("Utilizador invalido.")
    _ensure_user_default_preferences(usstamp)
    user_row = _load_user_row(usstamp) or {}
    devices = db.session.execute(text("""
        SELECT
            PUSHDEVSTAMP,
            ISNULL(PLATFORM,'') AS PLATFORM,
            ISNULL(DEVICE_LABEL,'') AS DEVICE_LABEL,
            ISNULL(USERAGENT,'') AS USERAGENT,
            ISNULL(IS_ACTIVE,1) AS IS_ACTIVE,
            LAST_SEEN,
            LAST_PUSH_AT,
            LAST_ERROR_AT,
            ISNULL(LAST_ERROR_MSG,'') AS LAST_ERROR_MSG
        FROM dbo.PUSH_DEVICE
        WHERE USERSTAMP = :userstamp
        ORDER BY ISNULL(IS_ACTIVE,1) DESC, ISNULL(LAST_SEEN, CREATED_AT) DESC, CREATED_AT DESC
    """), {"userstamp": usstamp}).mappings().all()
    logs = db.session.execute(text(f"""
        SELECT TOP {max(1, int(limit_logs or 5))}
            L.PUSHLOGSTAMP,
            L.EVENT_TYPE,
            L.TITLE,
            L.STATUS,
            L.CREATED_AT,
            L.SENT_AT,
            ISNULL(U.NOME, ISNULL(U.LOGIN,'')) AS SENT_BY_NAME
        FROM dbo.PUSH_LOG AS L
        LEFT JOIN dbo.US AS U
          ON U.USSTAMP = L.SENT_BY_USERSTAMP
        WHERE L.USERSTAMP = :userstamp
        ORDER BY L.CREATED_AT DESC
    """), {"userstamp": usstamp}).mappings().all()
    prefs = db.session.execute(text("""
        SELECT EVENT_TYPE, ISNULL(PUSH_ENABLED,1) AS PUSH_ENABLED
        FROM dbo.NOTIF_PREF
        WHERE USERSTAMP = :userstamp
        ORDER BY EVENT_TYPE
    """), {"userstamp": usstamp}).mappings().all()
    active_devices = sum(1 for d in devices if bool(d.get("IS_ACTIVE", 1)))
    return {
        "user": {
            "USSTAMP": user_row.get("USSTAMP"),
            "NOME": user_row.get("NOME"),
            "LOGIN": user_row.get("LOGIN"),
        },
        "active_devices": active_devices,
        "devices": [dict(r) for r in devices],
        "logs": [dict(r) for r in logs],
        "preferences": [dict(r) for r in prefs],
    }
