import hmac
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy import text
from werkzeug.security import check_password_hash, generate_password_hash

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import InvalidHashError, VerifyMismatchError
except Exception:  # pragma: no cover - fallback defensivo
    PasswordHasher = None
    InvalidHashError = Exception
    VerifyMismatchError = Exception


logger = logging.getLogger("stationzero.auth")

LOCK_AFTER_FAILURES = 5
LOCK_MINUTES = 15
HASH_ALGO_ARGON2ID = "argon2id"
HASH_ALGO_SCRYPT = "scrypt"

BASE_USER_COLUMNS = [
    "USSTAMP",
    "LOGIN",
    "NOME",
    "EMAIL",
    "COR",
    "PASSWORD",
    "ADMIN",
    "EQUIPA",
    "DEV",
    "HOME",
    "MNADMIN",
    "LPADMIN",
    "LSADMIN",
    "FOTO",
    "TEMPOS",
    "VIEWMODE",
]

OPTIONAL_USER_COLUMNS = [
    "PASSWORD_HASH",
    "PASSWORD_ALGO",
    "PASSWORD_MIGRADA",
    "PASSWORD_CHANGED_AT",
    "PASSWORD_RESET_REQUIRED",
    "FAILED_LOGIN_COUNT",
    "LOCKED_UNTIL",
    "LAST_LOGIN_AT",
    "IS_ACTIVE",
    "INATIVO",
    "IDIOMA",
    "LANG",
    "LANGUAGE",
    "LOCALE",
    "PREFERRED_LANGUAGE",
    "PREFERRED_LOCALE",
]

USER_LANGUAGE_COLUMN = "LANGUAGE"

_TABLE_COLUMNS_CACHE: Dict[str, set[str]] = {}
_HAS_ARGON2 = PasswordHasher is not None
_ARGON2_HASHER = PasswordHasher() if _HAS_ARGON2 else None


@dataclass
class AuthenticationResult:
    success: bool
    row: Optional[Dict[str, Any]] = None
    user_message: str = "Credenciais inv?lidas"
    reason: str = "invalid_credentials"
    migrated: bool = False


def _normalized_table_key(table_name: str) -> str:
    return f"dbo.{table_name}".upper()


def _session_cache_namespace(session) -> str:
    try:
        bind = session.get_bind()
    except Exception:
        bind = None

    if bind is None:
        return "bind:default"

    engine = getattr(bind, "engine", None) or bind
    return f"bind:{id(engine)}"


def _qualified_table_key(session, table_name: str) -> str:
    return f"{_session_cache_namespace(session)}::{_normalized_table_key(table_name)}"


def get_table_columns(session, table_name: str) -> set[str]:
    cache_key = _qualified_table_key(session, table_name)
    if cache_key in _TABLE_COLUMNS_CACHE:
        return _TABLE_COLUMNS_CACHE[cache_key]

    rows = session.execute(
        text(
            """
            SELECT c.name
              FROM sys.columns c
             WHERE c.object_id = OBJECT_ID(:object_name)
            """
        ),
        {"object_name": f"dbo.{table_name}"},
    ).scalars().all()
    columns = {str(name).upper() for name in rows}
    _TABLE_COLUMNS_CACHE[cache_key] = columns
    return columns


def clear_table_columns_cache(table_name: Optional[str] = None) -> None:
    if not table_name:
        _TABLE_COLUMNS_CACHE.clear()
        return
    normalized = _normalized_table_key(table_name)
    stale_keys = [key for key in _TABLE_COLUMNS_CACHE if key.endswith(f"::{normalized}")]
    for cache_key in stale_keys:
        _TABLE_COLUMNS_CACHE.pop(cache_key, None)


def has_table_column(session, table_name: str, column_name: str) -> bool:
    return str(column_name or "").strip().upper() in get_table_columns(session, table_name)


def ensure_user_language_column(session) -> bool:
    if has_table_column(session, "US", USER_LANGUAGE_COLUMN):
        return False

    try:
        session.execute(
            text(
                """
                IF COL_LENGTH('dbo.US', 'LANGUAGE') IS NULL
                BEGIN
                    ALTER TABLE dbo.US ADD [LANGUAGE] NVARCHAR(10) NULL
                END
                """
            )
        )
        session.commit()
        clear_table_columns_cache("US")
        logger.info("Coluna dbo.US.LANGUAGE criada automaticamente para i18n")
        return has_table_column(session, "US", USER_LANGUAGE_COLUMN)
    except Exception:
        session.rollback()
        raise


def set_user_language_preference(
    session,
    *,
    user_stamp: str = "",
    login_value: str = "",
    language: str = "",
) -> bool:
    language_value = str(language or "").strip()
    if not language_value or not has_table_column(session, "US", USER_LANGUAGE_COLUMN):
        return False

    params: Dict[str, Any] = {"language": language_value}
    where_sql = ""
    if user_stamp:
        where_sql = "USSTAMP = :user_stamp"
        params["user_stamp"] = str(user_stamp).strip()
    elif login_value:
        where_sql = "LOGIN = :login"
        params["login"] = str(login_value).strip()
    else:
        return False

    try:
        result = session.execute(
            text(
                f"""
                UPDATE US
                   SET [LANGUAGE] = :language
                 WHERE {where_sql}
                """
            ),
            params,
        )
        session.commit()
        return (result.rowcount or 0) > 0
    except Exception:
        session.rollback()
        raise


def _selectable_user_columns(session) -> list[str]:
    available = get_table_columns(session, "US")
    selectable = [col for col in BASE_USER_COLUMNS if col.upper() in available]
    selectable.extend(col for col in OPTIONAL_USER_COLUMNS if col.upper() in available)
    return selectable


def _normalize_user_row(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not row:
        return None

    normalized = dict(row)
    normalized.setdefault("PASSWORD_HASH", None)
    normalized.setdefault("PASSWORD_ALGO", None)
    normalized.setdefault("PASSWORD_MIGRADA", False)
    normalized.setdefault("PASSWORD_CHANGED_AT", None)
    normalized.setdefault("PASSWORD_RESET_REQUIRED", False)
    normalized.setdefault("FAILED_LOGIN_COUNT", 0)
    normalized.setdefault("LOCKED_UNTIL", None)
    normalized.setdefault("LAST_LOGIN_AT", None)
    normalized.setdefault("IS_ACTIVE", True)
    normalized.setdefault("INATIVO", 0)
    return normalized


def get_user_auth_row(session, login_value: str) -> Optional[Dict[str, Any]]:
    selectable = _selectable_user_columns(session)
    sql = text(
        f"""
        SELECT {", ".join(selectable)}
          FROM US
         WHERE LOGIN = :login
        """
    )
    row = session.execute(sql, {"login": (login_value or "").strip()}).mappings().first()
    return _normalize_user_row(row)


def get_user_by_stamp(session, user_stamp: str) -> Optional[Dict[str, Any]]:
    selectable = _selectable_user_columns(session)
    sql = text(
        f"""
        SELECT {", ".join(selectable)}
          FROM US
         WHERE USSTAMP = :stamp
        """
    )
    row = session.execute(sql, {"stamp": (user_stamp or "").strip()}).mappings().first()
    return _normalize_user_row(row)


def is_user_active(row: Dict[str, Any]) -> bool:
    if "IS_ACTIVE" in row and row["IS_ACTIVE"] is not None:
        return bool(row["IS_ACTIVE"])
    if "INATIVO" in row and row["INATIVO"] is not None:
        return not bool(row["INATIVO"])
    return True


def is_temporarily_locked(row: Dict[str, Any], now: Optional[datetime] = None) -> bool:
    now = now or datetime.now()
    locked_until = row.get("LOCKED_UNTIL")
    return bool(locked_until and locked_until > now)


def verify_legacy_password(row: Dict[str, Any], plaintext: str) -> bool:
    stored = row.get("PASSWORD")
    if stored is None:
        return False
    return hmac.compare_digest(str(stored), str(plaintext or ""))


def _verify_argon2_hash(stored_hash: str, plaintext: str) -> bool:
    if not _ARGON2_HASHER:
        return False
    try:
        return _ARGON2_HASHER.verify(stored_hash, plaintext or "")
    except (VerifyMismatchError, InvalidHashError):
        return False


def verify_password_hash(row: Dict[str, Any], plaintext: str) -> bool:
    stored_hash = (row.get("PASSWORD_HASH") or "").strip()
    if not stored_hash:
        return False

    algo = (row.get("PASSWORD_ALGO") or "").strip().lower()
    if algo == HASH_ALGO_ARGON2ID or (not algo and stored_hash.startswith("$argon2")):
        return _verify_argon2_hash(stored_hash, plaintext)

    try:
        return check_password_hash(stored_hash, plaintext or "")
    except Exception:
        return False


def hash_password(plaintext: str) -> tuple[str, str]:
    if _ARGON2_HASHER:
        return _ARGON2_HASHER.hash(plaintext or ""), HASH_ALGO_ARGON2ID

    return generate_password_hash(plaintext or "", method=HASH_ALGO_SCRYPT), HASH_ALGO_SCRYPT


def migrate_password(session, user_stamp: str, plaintext: str) -> tuple[str, str]:
    password_hash, password_algo = hash_password(plaintext)
    now = datetime.now()
    available = get_table_columns(session, "US")
    update_parts = []
    params: Dict[str, Any] = {"user_stamp": user_stamp}

    if "PASSWORD_HASH" in available:
        update_parts.append("PASSWORD_HASH = :password_hash")
        params["password_hash"] = password_hash
    if "PASSWORD_ALGO" in available:
        update_parts.append("PASSWORD_ALGO = :password_algo")
        params["password_algo"] = password_algo
    if "PASSWORD_MIGRADA" in available:
        update_parts.append("PASSWORD_MIGRADA = 1")
    if "PASSWORD_CHANGED_AT" in available:
        update_parts.append("PASSWORD_CHANGED_AT = :changed_at")
        params["changed_at"] = now

    if update_parts:
        session.execute(
            text(
                f"""
                UPDATE US
                   SET {", ".join(update_parts)}
                 WHERE USSTAMP = :user_stamp
                """
            ),
            params,
        )
        logger.info(
            "Password migrada automaticamente para hash seguro",
            extra={"login_userstamp": user_stamp, "password_algo": password_algo},
        )
    else:
        logger.warning(
            "Migra??o de password adiada: colunas seguras ainda n?o existem em dbo.US",
            extra={"login_userstamp": user_stamp},
        )
    return password_hash, password_algo


def register_login_failure(session, row: Dict[str, Any], now: Optional[datetime] = None) -> Dict[str, Any]:
    now = now or datetime.now()
    available = get_table_columns(session, "US")
    current_failures = int(row.get("FAILED_LOGIN_COUNT") or 0) + 1
    locked_until = None
    if current_failures >= LOCK_AFTER_FAILURES:
        locked_until = now + timedelta(minutes=LOCK_MINUTES)

    update_parts = []
    params: Dict[str, Any] = {"user_stamp": row["USSTAMP"]}
    if "FAILED_LOGIN_COUNT" in available:
        update_parts.append("FAILED_LOGIN_COUNT = :failed_login_count")
        params["failed_login_count"] = current_failures
    if "LOCKED_UNTIL" in available:
        update_parts.append("LOCKED_UNTIL = :locked_until")
        params["locked_until"] = locked_until

    if update_parts:
        session.execute(
            text(
                f"""
                UPDATE US
                   SET {", ".join(update_parts)}
                 WHERE USSTAMP = :user_stamp
                """
            ),
            params,
        )
        session.commit()

    if locked_until:
        logger.warning(
            "Conta bloqueada temporariamente ap?s falhas de login",
            extra={
                "login": row.get("LOGIN"),
                "userstamp": row.get("USSTAMP"),
                "failed_login_count": current_failures,
                "locked_until": locked_until.isoformat(),
            },
        )
    else:
        logger.warning(
            "Login falhado",
            extra={"login": row.get("LOGIN"), "userstamp": row.get("USSTAMP"), "failed_login_count": current_failures},
        )

    row["FAILED_LOGIN_COUNT"] = current_failures
    row["LOCKED_UNTIL"] = locked_until
    return row


def register_login_success(session, row: Dict[str, Any], now: Optional[datetime] = None) -> None:
    now = now or datetime.now()
    available = get_table_columns(session, "US")
    update_parts = []
    params: Dict[str, Any] = {"user_stamp": row["USSTAMP"]}

    if "LAST_LOGIN_AT" in available:
        update_parts.append("LAST_LOGIN_AT = :last_login_at")
        params["last_login_at"] = now
    if "FAILED_LOGIN_COUNT" in available:
        update_parts.append("FAILED_LOGIN_COUNT = 0")
    if "LOCKED_UNTIL" in available:
        update_parts.append("LOCKED_UNTIL = NULL")

    if update_parts:
        session.execute(
            text(
                f"""
                UPDATE US
                   SET {", ".join(update_parts)}
                 WHERE USSTAMP = :user_stamp
                """
            ),
            params,
        )
        session.commit()

    logger.info(
        "Login bem-sucedido",
        extra={"login": row.get("LOGIN"), "userstamp": row.get("USSTAMP"), "migrated": bool(row.get("PASSWORD_MIGRADA"))},
    )


def set_password_for_user(session, user_stamp: str, plaintext: str) -> str:
    password_hash, password_algo = hash_password(plaintext)
    now = datetime.now()
    available = get_table_columns(session, "US")
    update_parts = []
    params: Dict[str, Any] = {"user_stamp": user_stamp}

    if "PASSWORD" in available:
        update_parts.append("PASSWORD = :legacy_password")
        params["legacy_password"] = plaintext
    if "PASSWORD_HASH" in available:
        update_parts.append("PASSWORD_HASH = :password_hash")
        params["password_hash"] = password_hash
    if "PASSWORD_ALGO" in available:
        update_parts.append("PASSWORD_ALGO = :password_algo")
        params["password_algo"] = password_algo
    if "PASSWORD_MIGRADA" in available:
        update_parts.append("PASSWORD_MIGRADA = 1")
    if "PASSWORD_CHANGED_AT" in available:
        update_parts.append("PASSWORD_CHANGED_AT = :changed_at")
        params["changed_at"] = now
    if "PASSWORD_RESET_REQUIRED" in available:
        update_parts.append("PASSWORD_RESET_REQUIRED = 0")
    if "FAILED_LOGIN_COUNT" in available:
        update_parts.append("FAILED_LOGIN_COUNT = 0")
    if "LOCKED_UNTIL" in available:
        update_parts.append("LOCKED_UNTIL = NULL")

    session.execute(
        text(
            f"""
            UPDATE US
               SET {", ".join(update_parts)}
             WHERE USSTAMP = :user_stamp
            """
        ),
        params,
    )
    session.commit()
    return password_algo


def authenticate_user(session, login_value: str, plaintext: str) -> AuthenticationResult:
    now = datetime.now()
    login_clean = (login_value or "").strip()
    row = get_user_auth_row(session, login_clean)

    if not row:
        logger.warning("Login falhado: utilizador inexistente", extra={"login": login_clean})
        return AuthenticationResult(success=False, user_message="Credenciais inv?lidas", reason="user_not_found")

    if not is_user_active(row):
        logger.warning("Login recusado: utilizador inativo", extra={"login": row.get("LOGIN"), "userstamp": row.get("USSTAMP")})
        return AuthenticationResult(success=False, row=row, user_message="Conta inativa", reason="inactive")

    if is_temporarily_locked(row, now):
        logger.warning(
            "Login recusado: conta temporariamente bloqueada",
            extra={
                "login": row.get("LOGIN"),
                "userstamp": row.get("USSTAMP"),
                "locked_until": row.get("LOCKED_UNTIL").isoformat() if row.get("LOCKED_UNTIL") else None,
            },
        )
        return AuthenticationResult(
            success=False,
            row=row,
            user_message="Conta temporariamente bloqueada. Tente novamente dentro de alguns minutos.",
            reason="locked",
        )

    migrated = False
    password_hash = (row.get("PASSWORD_HASH") or "").strip()
    if password_hash:
        if not verify_password_hash(row, plaintext):
            register_login_failure(session, row, now)
            return AuthenticationResult(success=False, row=row, user_message="Credenciais inv?lidas", reason="invalid_password")
    else:
        if not verify_legacy_password(row, plaintext):
            register_login_failure(session, row, now)
            return AuthenticationResult(success=False, row=row, user_message="Credenciais inv?lidas", reason="invalid_password")
        available = get_table_columns(session, "US")
        if "PASSWORD_HASH" in available:
            migrate_password(session, row["USSTAMP"], plaintext)
            row["PASSWORD_MIGRADA"] = True
            migrated = True

    register_login_success(session, row, now)
    row["FAILED_LOGIN_COUNT"] = 0
    row["LOCKED_UNTIL"] = None
    row["LAST_LOGIN_AT"] = now
    return AuthenticationResult(success=True, row=row, migrated=migrated, reason="success")
