from __future__ import annotations

import time

from flask import Blueprint, abort, jsonify, make_response, render_template, request, session
from flask_login import current_user, login_required
from sqlalchemy import text

from models import db
from services.credential_vault_service import (
    PERMISSION_FIELDS,
    VaultConfigurationError,
    VaultError,
    VaultValidationError,
    audit_event,
    clean_item_payload,
    decrypt_secret,
    encrypt_secret,
    ensure_schema,
    new_stamp,
    public_item,
    user_permissions,
)
from services.multiempresa_service import get_current_feid


bp = Blueprint("credential_vault", __name__)
REAUTH_SESSION_KEY = "CREDENTIAL_VAULT_REAUTH"
REAUTH_GUARD_SESSION_KEY = "CREDENTIAL_VAULT_REAUTH_GUARD"
REAUTH_SECONDS = 300
REAUTH_MAX_FAILURES = 5
REAUTH_LOCK_SECONDS = 300


def _actor() -> dict[str, str]:
    return {
        "login": str(getattr(current_user, "LOGIN", "") or "").strip(),
        "stamp": str(getattr(current_user, "USSTAMP", "") or "").strip(),
    }


def _feid() -> int:
    try:
        return int(get_current_feid() or 0)
    except Exception:
        return 0


def _request_meta() -> dict[str, str]:
    forwarded = str(request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    return {
        "ip": (forwarded or str(request.remote_addr or "").strip())[:64],
        "user_agent": str(request.headers.get("User-Agent") or "").strip()[:500],
        "request_path": str(request.full_path or request.path or "").rstrip("?")[:500],
    }


def _audit(action: str, success: bool, *, credential_stamp: str = "", reason: str = "") -> None:
    actor = _actor()
    audit_event(
        db.session,
        action=action,
        success=success,
        user_login=actor["login"],
        user_stamp=actor["stamp"],
        credential_stamp=credential_stamp,
        feid=_feid(),
        reason=reason,
        **_request_meta(),
    )


def _permissions() -> dict[str, bool]:
    if bool(getattr(current_user, "ADMIN", False)):
        return {field: True for field in PERMISSION_FIELDS}
    return user_permissions(db.session, _actor()["login"])


def _permission_error(permission: str, *, credential_stamp: str = ""):
    _audit("ACESSO_NEGADO", False, credential_stamp=credential_stamp, reason=f"Sem permissão: {permission}")
    db.session.commit()
    return jsonify({"ok": False, "error": "Não tens permissão para esta operação."}), 403


def _require(permission: str, *, credential_stamp: str = ""):
    if _permissions().get(permission, False):
        return None
    return _permission_error(permission, credential_stamp=credential_stamp)


def _no_store(response):
    response.headers["Cache-Control"] = "no-store, no-cache, max-age=0, must-revalidate, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def _reauth_valid() -> bool:
    state = session.get(REAUTH_SESSION_KEY) or {}
    return (
        str(state.get("user_stamp") or "") == _actor()["stamp"]
        and int(state.get("expires_at") or 0) >= int(time.time())
    )


@bp.before_request
def _prepare_schema():
    if not current_user.is_authenticated:
        return None
    try:
        ensure_schema(db.session)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return None


@bp.get("/credenciais")
@login_required
def page():
    denied = _require("consultar")
    if denied:
        abort(403)
    permissions = _permissions()
    _audit("CONSULTAR", True, reason="Abertura do ecrã")
    db.session.commit()
    return _no_store(make_response(render_template("credential_vault.html", vault_permissions=permissions)))


@bp.get("/api/credential-vault/items")
@login_required
def list_items():
    denied = _require("consultar")
    if denied:
        return denied
    search = str(request.args.get("q") or "").strip()[:200]
    active = str(request.args.get("active") or "1").strip().lower()
    clauses = ["FEID=:feid"]
    params: dict[str, object] = {"feid": _feid()}
    if active in {"1", "true", "active"}:
        clauses.append("ISNULL(ATIVO,0)=1")
    elif active in {"0", "false", "inactive"}:
        clauses.append("ISNULL(ATIVO,0)=0")
    if search:
        clauses.append("(CATEGORIA LIKE :search OR DESCRICAO LIKE :search OR LOGIN LIKE :search)")
        params["search"] = f"%{search}%"
    rows = db.session.execute(text(f"""
        SELECT CREDENCIALSTAMP, CATEGORIA, DESCRICAO, URL, LOGIN, NOTAS, ATIVO,
               DTCRI_UTC, DTALT_UTC, USERCRIACAO, USERALTERACAO
        FROM dbo.CREDENCIAL_VAULT
        WHERE {' AND '.join(clauses)}
        ORDER BY CATEGORIA, DESCRICAO, CREDENCIALSTAMP
    """), params).mappings().all()
    _audit("CONSULTAR", True, reason=f"Listagem: {len(rows)} registo(s)")
    db.session.commit()
    return _no_store(jsonify({
        "ok": True,
        "items": [public_item(row) for row in rows],
        "permissions": _permissions(),
    }))


@bp.post("/api/credential-vault/items")
@login_required
def create_item():
    denied = _require("criar")
    if denied:
        return denied
    body = request.get_json(silent=True) or {}
    try:
        values = clean_item_payload(body)
        stamp = new_stamp()
        encrypted = encrypt_secret(body.get("password"), stamp=stamp, feid=_feid())
        db.session.execute(text("""
            INSERT INTO dbo.CREDENCIAL_VAULT
                (CREDENCIALSTAMP, FEID, CATEGORIA, DESCRICAO, URL, LOGIN,
                 SEGREDO_CIPHERTEXT, SEGREDO_NONCE, SEGREDO_KEY_VERSION,
                 NOTAS, ATIVO, USERCRIACAO, USERALTERACAO)
            VALUES
                (:stamp, :feid, :categoria, :descricao, :url, :login,
                 :ciphertext, :nonce, :key_version,
                 :notas, :ativo, :actor, :actor)
        """), {
            **values,
            **encrypted,
            "stamp": stamp,
            "feid": _feid(),
            "actor": _actor()["login"],
            "ativo": 1 if values["ativo"] else 0,
        })
        _audit("CRIAR", True, credential_stamp=stamp)
        db.session.commit()
        return jsonify({"ok": True, "stamp": stamp}), 201
    except (VaultValidationError, VaultConfigurationError) as exc:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception:
        db.session.rollback()
        raise


@bp.put("/api/credential-vault/items/<stamp>")
@login_required
def update_item(stamp: str):
    target = str(stamp or "").strip()[:25]
    denied = _require("editar", credential_stamp=target)
    if denied:
        return denied
    body = request.get_json(silent=True) or {}
    row = db.session.execute(text("""
        SELECT CREDENCIALSTAMP, ISNULL(ATIVO,0) AS ATIVO FROM dbo.CREDENCIAL_VAULT
        WHERE CREDENCIALSTAMP=:stamp AND FEID=:feid
    """), {"stamp": target, "feid": _feid()}).mappings().first()
    if not row:
        return jsonify({"ok": False, "error": "Credencial não encontrada."}), 404
    try:
        values = clean_item_payload(body)
        if bool(row.get("ATIVO") or 0) != bool(values["ativo"]) and not _permissions().get("desativar", False):
            return _permission_error("desativar", credential_stamp=target)
        params: dict[str, object] = {
            **values,
            "stamp": target,
            "feid": _feid(),
            "actor": _actor()["login"],
            "ativo": 1 if values["ativo"] else 0,
        }
        password = str(body.get("password") or "")
        secret_sql = ""
        if password:
            params.update(encrypt_secret(password, stamp=target, feid=_feid()))
            secret_sql = """,
                SEGREDO_CIPHERTEXT=:ciphertext,
                SEGREDO_NONCE=:nonce,
                SEGREDO_KEY_VERSION=:key_version"""
        db.session.execute(text(f"""
            UPDATE dbo.CREDENCIAL_VAULT
            SET CATEGORIA=:categoria, DESCRICAO=:descricao, URL=:url, LOGIN=:login,
                NOTAS=:notas, ATIVO=:ativo, DTALT_UTC=SYSUTCDATETIME(), USERALTERACAO=:actor
                {secret_sql}
            WHERE CREDENCIALSTAMP=:stamp AND FEID=:feid
        """), params)
        _audit("EDITAR", True, credential_stamp=target, reason="Password alterada" if password else "Metadados alterados")
        db.session.commit()
        return jsonify({"ok": True})
    except (VaultValidationError, VaultConfigurationError) as exc:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception:
        db.session.rollback()
        raise


@bp.delete("/api/credential-vault/items/<stamp>")
@login_required
def deactivate_item(stamp: str):
    target = str(stamp or "").strip()[:25]
    denied = _require("desativar", credential_stamp=target)
    if denied:
        return denied
    result = db.session.execute(text("""
        UPDATE dbo.CREDENCIAL_VAULT
        SET ATIVO=0, DTALT_UTC=SYSUTCDATETIME(), USERALTERACAO=:actor
        WHERE CREDENCIALSTAMP=:stamp AND FEID=:feid AND ISNULL(ATIVO,0)=1
    """), {"actor": _actor()["login"], "stamp": target, "feid": _feid()})
    if not (result.rowcount or 0):
        db.session.rollback()
        return jsonify({"ok": False, "error": "Credencial ativa não encontrada."}), 404
    _audit("DESATIVAR", True, credential_stamp=target)
    db.session.commit()
    return jsonify({"ok": True})


@bp.post("/api/credential-vault/reauth")
@login_required
def reauthenticate():
    body = request.get_json(silent=True) or {}
    password = str(body.get("password") or "")
    now = int(time.time())
    guard = session.get(REAUTH_GUARD_SESSION_KEY) or {}
    locked_until = int(guard.get("locked_until") or 0)
    if locked_until > now:
        _audit("REAUTENTICAR", False, reason="Temporariamente bloqueado")
        db.session.commit()
        return _no_store(jsonify({
            "ok": False,
            "error": "Demasiadas tentativas. Tenta novamente dentro de alguns minutos.",
        })), 429
    try:
        valid = bool(password and current_user.check_password(password))
    except Exception:
        valid = False
    if not valid:
        session.pop(REAUTH_SESSION_KEY, None)
        failures = int(guard.get("failures") or 0) + 1
        session[REAUTH_GUARD_SESSION_KEY] = {
            "failures": failures,
            "locked_until": now + REAUTH_LOCK_SECONDS if failures >= REAUTH_MAX_FAILURES else 0,
        }
        _audit("REAUTENTICAR", False, reason="Password inválida")
        db.session.commit()
        return _no_store(jsonify({"ok": False, "error": "Password inválida."})), 401
    session.pop(REAUTH_GUARD_SESSION_KEY, None)
    expires_at = now + REAUTH_SECONDS
    session[REAUTH_SESSION_KEY] = {"user_stamp": _actor()["stamp"], "expires_at": expires_at}
    _audit("REAUTENTICAR", True)
    db.session.commit()
    return _no_store(jsonify({"ok": True, "expires_at": expires_at}))


@bp.post("/api/credential-vault/items/<stamp>/secret")
@login_required
def get_secret(stamp: str):
    target = str(stamp or "").strip()[:25]
    body = request.get_json(silent=True) or {}
    action = str(body.get("action") or "reveal").strip().lower()
    permission = "copiar" if action == "copy" else "revelar"
    audit_action = "COPIAR" if action == "copy" else "REVELAR"
    denied = _require(permission, credential_stamp=target)
    if denied:
        return denied
    if not _reauth_valid():
        _audit(audit_action, False, credential_stamp=target, reason="Reautenticação necessária")
        db.session.commit()
        return _no_store(jsonify({
            "ok": False,
            "error": "Confirma novamente a tua password.",
            "code": "REAUTH_REQUIRED",
        })), 401
    row = db.session.execute(text("""
        SELECT CREDENCIALSTAMP, FEID, SEGREDO_CIPHERTEXT, SEGREDO_NONCE, SEGREDO_KEY_VERSION
        FROM dbo.CREDENCIAL_VAULT
        WHERE CREDENCIALSTAMP=:stamp AND FEID=:feid AND ISNULL(ATIVO,0)=1
    """), {"stamp": target, "feid": _feid()}).mappings().first()
    if not row:
        return _no_store(jsonify({"ok": False, "error": "Credencial ativa não encontrada."})), 404
    try:
        secret = decrypt_secret(
            row.get("SEGREDO_CIPHERTEXT"),
            row.get("SEGREDO_NONCE"),
            stamp=target,
            feid=int(row.get("FEID") or 0),
            key_version=int(row.get("SEGREDO_KEY_VERSION") or 0),
        )
        _audit(audit_action, True, credential_stamp=target)
        db.session.commit()
        return _no_store(jsonify({"ok": True, "secret": secret, "hide_after_seconds": 20}))
    except VaultError as exc:
        _audit(audit_action, False, credential_stamp=target, reason=str(exc))
        db.session.commit()
        return _no_store(jsonify({"ok": False, "error": str(exc)})), 500


@bp.get("/api/credential-vault/permissions")
@login_required
def list_permissions():
    denied = _require("administrar")
    if denied:
        return denied
    rows = db.session.execute(text("""
        SELECT U.LOGIN, U.NOME, ISNULL(U.ADMIN,0) AS USER_ADMIN,
               ISNULL(P.CONSULTAR,0) AS CONSULTAR,
               ISNULL(P.CRIAR,0) AS CRIAR,
               ISNULL(P.EDITAR,0) AS EDITAR,
               ISNULL(P.DESATIVAR,0) AS DESATIVAR,
               ISNULL(P.REVELAR,0) AS REVELAR,
               ISNULL(P.COPIAR,0) AS COPIAR,
               ISNULL(P.ADMINISTRAR,0) AS ADMINISTRAR
        FROM dbo.US U
        LEFT JOIN dbo.CREDENCIAL_VAULT_PERMISSAO P
          ON LOWER(LTRIM(RTRIM(P.LOGIN)))=LOWER(LTRIM(RTRIM(U.LOGIN))) AND ISNULL(P.ATIVO,0)=1
        WHERE ISNULL(U.IS_ACTIVE,1)=1 AND ISNULL(U.INATIVO,0)=0
        ORDER BY U.NOME, U.LOGIN
    """)).mappings().all()
    items = []
    for row in rows:
        is_admin = bool(row.get("USER_ADMIN") or 0)
        items.append({
            "login": str(row.get("LOGIN") or "").strip(),
            "nome": str(row.get("NOME") or "").strip(),
            "is_admin": is_admin,
            **{
                field: is_admin or bool(row.get(field.upper()) or 0)
                for field in PERMISSION_FIELDS
            },
        })
    _audit("PERMISSOES", True, reason="Consulta")
    db.session.commit()
    return _no_store(jsonify({"ok": True, "items": items, "fields": list(PERMISSION_FIELDS)}))


@bp.put("/api/credential-vault/permissions/<login>")
@login_required
def save_permissions(login: str):
    denied = _require("administrar")
    if denied:
        return denied
    target_login = str(login or "").strip()[:100]
    exists = db.session.execute(text("""
        SELECT TOP 1 LOGIN FROM dbo.US
        WHERE LOWER(LTRIM(RTRIM(LOGIN)))=LOWER(:login) AND ISNULL(IS_ACTIVE,1)=1 AND ISNULL(INATIVO,0)=0
    """), {"login": target_login}).scalar()
    if not exists:
        return jsonify({"ok": False, "error": "Utilizador não encontrado."}), 404
    target_is_admin = db.session.execute(text("""
        SELECT TOP 1 ISNULL(ADMIN,0) FROM dbo.US
        WHERE LOWER(LTRIM(RTRIM(LOGIN)))=LOWER(:login)
    """), {"login": target_login}).scalar()
    if bool(target_is_admin):
        return jsonify({
            "ok": False,
            "error": "Os utilizadores ADMIN têm todas as permissões do cofre por defeito.",
        }), 400
    body = request.get_json(silent=True) or {}
    values = {field: 1 if bool(body.get(field)) else 0 for field in PERMISSION_FIELDS}
    if values["administrar"]:
        values["consultar"] = 1
    if target_login.lower() == _actor()["login"].lower() and not values["administrar"]:
        other_admins = db.session.execute(text("""
            SELECT COUNT(*) FROM dbo.CREDENCIAL_VAULT_PERMISSAO
            WHERE ISNULL(ATIVO,0)=1 AND ISNULL(ADMINISTRAR,0)=1
              AND LOWER(LTRIM(RTRIM(LOGIN)))<>LOWER(:login)
        """), {"login": target_login}).scalar()
        if int(other_admins or 0) == 0:
            return jsonify({
                "ok": False,
                "error": "O cofre tem de manter pelo menos um administrador.",
            }), 400
    db.session.execute(text("""
        MERGE dbo.CREDENCIAL_VAULT_PERMISSAO AS T
        USING (SELECT :login AS LOGIN) AS S
          ON LOWER(LTRIM(RTRIM(T.LOGIN)))=LOWER(LTRIM(RTRIM(S.LOGIN)))
        WHEN MATCHED THEN UPDATE SET
          CONSULTAR=:consultar, CRIAR=:criar, EDITAR=:editar, DESATIVAR=:desativar,
          REVELAR=:revelar, COPIAR=:copiar, ADMINISTRAR=:administrar,
          ATIVO=1, DTALT_UTC=SYSUTCDATETIME(), USERALTERACAO=:actor
        WHEN NOT MATCHED THEN INSERT
          (PERMISSAOSTAMP, LOGIN, CONSULTAR, CRIAR, EDITAR, DESATIVAR, REVELAR, COPIAR, ADMINISTRAR, ATIVO, USERALTERACAO)
        VALUES
          (:stamp, :login, :consultar, :criar, :editar, :desativar, :revelar, :copiar, :administrar, 1, :actor);
    """), {
        **values,
        "stamp": new_stamp(),
        "login": target_login,
        "actor": _actor()["login"],
    })
    _audit("PERMISSOES", True, reason=f"Alteração de permissões: {target_login}")
    db.session.commit()
    return jsonify({"ok": True})
