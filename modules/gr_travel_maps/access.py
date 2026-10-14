from __future__ import annotations

from flask import current_app
from sqlalchemy import text

from models import db
from services.gr360_audit_service import is_gr360_audit_context


ACL_TABLE = "RH_MAPAS"


def in_gr360_context() -> bool:
    # Reuse the pure context guard; no audit connection or planning import.
    resolver = current_app.config.get("DB_CURRENT_TARGET_RESOLVER")
    try:
        target = resolver() if callable(resolver) else ""
    except Exception:
        return False
    config = {
        "GR360_AUDIT_ENABLED": True,
        "GR360_AUDIT_TARGET": "client",
        "GR360_AUDIT_EXPECTED_DATABASE": "GR360_CORE",
        "GR360_AUDIT_SOURCE_DATABASE": current_app.config.get("DB_CLIENT_NAME")
        or current_app.config.get("GR360_HUB_SOURCE_DATABASE"),
    }
    return is_gr360_audit_context(config, current_target=target)


def can_consult(user, permissions: dict | None = None) -> bool:
    if not getattr(user, "is_authenticated", False) or not in_gr360_context():
        return False
    if getattr(user, "ADMIN", False) or getattr(user, "DEV", False):
        return True
    if permissions is not None:
        return bool(permissions.get(ACL_TABLE, {}).get("consultar"))
    login = str(getattr(user, "LOGIN", "") or "").strip()
    if not login:
        return False
    return db.session.execute(text("""
        SELECT TOP 1 1 FROM dbo.ACESSOS
        WHERE UTILIZADOR = :login
          AND UPPER(LTRIM(RTRIM(TABELA))) = :table AND CONSULTAR = 1
    """), {"login": login, "table": ACL_TABLE}).first() is not None


def can_change(user, *, validate=False) -> bool:
    if not can_consult(user):
        return False
    if getattr(user, "ADMIN", False) or getattr(user, "DEV", False):
        return True
    # Existing ACL columns; validation is deliberately a separate permission.
    column = "CONSULTAR" if validate else "EDITAR"
    table = "RH_MAPAS_VALIDAR" if validate else ACL_TABLE
    return db.session.execute(text(f"""
        SELECT TOP 1 1 FROM dbo.ACESSOS
        WHERE UTILIZADOR = :login AND UPPER(LTRIM(RTRIM(TABELA))) = :table
          AND {column} = 1
    """), {"login": str(getattr(user, "LOGIN", "") or "").strip(), "table": table}).first() is not None
