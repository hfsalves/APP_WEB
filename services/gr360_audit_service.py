from __future__ import annotations

import json
import logging
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Mapping

from flask import current_app, g, has_request_context, request
from flask_login import current_user
from sqlalchemy import text

from services.odbc_driver import get_sql_server_odbc_driver, normalize_pyodbc_conn_str_driver


logger = logging.getLogger("stationzero.gr360_audit")

DEFAULT_AUDIT_TABLES = {"*"}
TRUE_VALUES = {"1", "true", "yes", "y", "on", "sim"}
SENSITIVE_NAME_PARTS = (
    "PASSWORD",
    "PASSWD",
    "PWD",
    "PASSWORD_HASH",
    "PASSWORD_ALGO",
    "PASSWORD_RESET",
    "RESET_TOKEN",
    "TOKEN",
    "API_KEY",
    "APIKEY",
    "SECRET",
    "COOKIE",
    "SESSION",
    "CONNECTION_STRING",
    "CONN_STR",
    "DATABASE_URL",
)
REDACTED_VALUE = "***REDACTED***"


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in TRUE_VALUES


def _config_get(config: Mapping[str, Any], key: str, default: Any = None) -> Any:
    try:
        return config.get(key, default)  # type: ignore[attr-defined]
    except Exception:
        return default


def normalize_table_name(table_name: str) -> str:
    return str(table_name or "").strip().upper()


def enabled_table_set(config: Mapping[str, Any] | None = None) -> set[str]:
    config = config or {}
    raw = _config_get(config, "GR360_AUDIT_TABLES", "")
    if isinstance(raw, (set, tuple, list)):
        values = raw
    else:
        values = str(raw or "").split(",")
    tables = {normalize_table_name(item) for item in values if normalize_table_name(item)}
    return tables or set(DEFAULT_AUDIT_TABLES)


def is_gr360_audit_context(
    config: Mapping[str, Any],
    *,
    current_target: str | None,
    require_request_context: bool = False,
) -> bool:
    """Return True only when the current context is explicitly GR360.

    This is intentionally conservative: any missing/unknown value disables
    auditing so GuestSpaTur cannot accidentally open or write to GR360_LOG.
    """
    if require_request_context and not has_request_context():
        return False
    if not _truthy(_config_get(config, "GR360_AUDIT_ENABLED")):
        return False

    expected_target = str(_config_get(config, "GR360_AUDIT_TARGET", "client") or "").strip().lower()
    resolved_target = str(current_target or "").strip().lower()
    if not expected_target or resolved_target != expected_target:
        return False

    expected_db = str(_config_get(config, "GR360_AUDIT_EXPECTED_DATABASE", "GR360_CORE") or "").strip().upper()
    source_db = str(
        _config_get(config, "GR360_AUDIT_SOURCE_DATABASE")
        or _config_get(config, "DB_CLIENT_NAME")
        or ""
    ).strip().upper()
    if not expected_db or source_db != expected_db:
        return False

    return True


def current_db_target() -> str:
    resolver = current_app.config.get("DB_CURRENT_TARGET_RESOLVER")
    if not callable(resolver):
        return ""
    try:
        return str(resolver() or "").strip().lower()
    except Exception:
        return ""


def should_audit_table(table_name: str, config: Mapping[str, Any] | None = None) -> bool:
    table = normalize_table_name(table_name)
    if not table:
        return False
    using_current_app = config is None
    config = current_app.config if using_current_app else config
    enabled_tables = enabled_table_set(config)
    if "*" not in enabled_tables and table not in enabled_tables:
        return False
    return is_gr360_audit_context(
        config,
        current_target=current_db_target() if using_current_app else _config_get(config, "CURRENT_DB_TARGET", ""),
        require_request_context=using_current_app,
    )


def _is_sensitive_field(name: str) -> bool:
    upper = str(name or "").strip().upper()
    return any(part in upper for part in SENSITIVE_NAME_PARTS)


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.isoformat(sep=" ", timespec="microseconds")
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bytes):
        return f"<bytes:{len(value)}>"
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    return value


def redact_data(data: Any) -> Any:
    if data is None:
        return None
    if isinstance(data, Mapping):
        redacted: dict[str, Any] = {}
        for key, value in data.items():
            key_text = str(key)
            redacted[key_text] = REDACTED_VALUE if _is_sensitive_field(key_text) else redact_data(value)
        return redacted
    if isinstance(data, list):
        return [redact_data(item) for item in data]
    if isinstance(data, tuple):
        return [redact_data(item) for item in data]
    return _jsonable(data)


def _normalized_for_compare(value: Any) -> Any:
    value = _jsonable(value)
    if value == "":
        return ""
    return value


def calculate_changed_data(before: Mapping[str, Any] | None, after: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    before_map = dict(before or {})
    after_map = dict(after or {})
    keys = sorted(set(before_map) | set(after_map))
    changed: dict[str, dict[str, Any]] = {}
    for key in keys:
        if _is_sensitive_field(str(key)):
            continue
        old_value = _normalized_for_compare(before_map.get(key))
        new_value = _normalized_for_compare(after_map.get(key))
        if old_value != new_value:
            changed[str(key)] = {"before": old_value, "after": new_value}
    return redact_data(changed) or {}


def _json_dumps_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(redact_data(value), ensure_ascii=False, default=str)


def _new_stamp_25() -> str:
    return uuid.uuid4().hex.upper()[:25]


def _correlation_id() -> str | None:
    if not has_request_context():
        return None
    cid = getattr(g, "gr360_audit_correlation_id", None)
    if not cid:
        cid = str(uuid.uuid4())
        g.gr360_audit_correlation_id = cid
    return cid


def _client_ip() -> str:
    if not has_request_context():
        return ""
    forwarded = str(request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    return forwarded or str(request.remote_addr or "").strip()


def _actor_login() -> str:
    try:
        if current_user and current_user.is_authenticated:
            return str(getattr(current_user, "LOGIN", "") or getattr(current_user, "login", "") or "").strip()
    except Exception:
        pass
    return ""


def _actor_usstamp() -> str:
    try:
        if current_user and current_user.is_authenticated:
            return str(getattr(current_user, "USSTAMP", "") or getattr(current_user, "usstamp", "") or "").strip()
    except Exception:
        pass
    return ""


def _build_log_conn_str(config: Mapping[str, Any]) -> str:
    explicit = str(_config_get(config, "GR360_AUDIT_LOG_CONN_STR") or "").strip()
    if explicit:
        return normalize_pyodbc_conn_str_driver(explicit)

    server = str(_config_get(config, "GR360_AUDIT_LOG_SERVER") or "").strip()
    user = str(_config_get(config, "GR360_AUDIT_LOG_USER") or "").strip()
    password = str(_config_get(config, "GR360_AUDIT_LOG_PASSWORD") or "").strip()
    if not server or not user or not password:
        return ""

    port = str(_config_get(config, "GR360_AUDIT_LOG_PORT") or "").strip()
    database = str(_config_get(config, "GR360_AUDIT_LOG_DATABASE", "GR360_LOG") or "GR360_LOG").strip()
    host = f"{server},{port}" if port else server
    driver = get_sql_server_odbc_driver()
    return (
        f"DRIVER={{{driver}}};"
        f"SERVER={host};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        "TrustServerCertificate=Yes;"
        "Application Name=APP_WEB_GR360_AUDIT"
    )


def _default_connection_factory(conn_str: str):
    import pyodbc

    return pyodbc.connect(conn_str, autocommit=True, timeout=5)


def write_logapp_entry(
    payload: Mapping[str, Any],
    *,
    config: Mapping[str, Any] | None = None,
    connection_factory: Callable[[str], Any] | None = None,
) -> bool:
    config = config or current_app.config
    conn_str = _build_log_conn_str(config)
    if not conn_str:
        logger.warning("Auditoria GR360 ativa, mas GR360_AUDIT_LOG_* nao esta configurado.")
        return False

    factory = connection_factory or _default_connection_factory
    sql = """
        INSERT INTO dbo.LOGAPP
        (
            LOGAPPSTAMP, OCCURRED_AT_UTC, CORRELATION_ID, APP_NAME, ENVIRONMENT,
            ACTOR_LOGIN, ACTOR_USSTAMP, REQUEST_METHOD, REQUEST_PATH, CLIENT_IP,
            DATABASE_NAME, SCHEMA_NAME, TABLE_NAME, ACTION, RECORD_KEY,
            BEFORE_DATA, AFTER_DATA, CHANGED_DATA, QUERY_TEXT, STATUS,
            ERROR_MESSAGE, METADATA
        )
        VALUES
        (
            ?, SYSUTCDATETIME(), ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?
        )
    """
    values = (
        payload.get("LOGAPPSTAMP") or _new_stamp_25(),
        payload.get("CORRELATION_ID"),
        payload.get("APP_NAME") or "APP_WEB",
        payload.get("ENVIRONMENT") or "production",
        payload.get("ACTOR_LOGIN") or None,
        payload.get("ACTOR_USSTAMP") or None,
        payload.get("REQUEST_METHOD") or None,
        payload.get("REQUEST_PATH") or None,
        payload.get("CLIENT_IP") or None,
        payload.get("DATABASE_NAME") or "GR360_CORE",
        payload.get("SCHEMA_NAME") or "dbo",
        payload.get("TABLE_NAME"),
        payload.get("ACTION"),
        payload.get("RECORD_KEY") or "{}",
        payload.get("BEFORE_DATA"),
        payload.get("AFTER_DATA"),
        payload.get("CHANGED_DATA"),
        payload.get("QUERY_TEXT"),
        payload.get("STATUS") or "success",
        payload.get("ERROR_MESSAGE"),
        payload.get("METADATA"),
    )
    try:
        with factory(conn_str) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, values)
        return True
    except Exception:
        logger.exception("Falha ao escrever auditoria GR360 em LOGAPP.")
        return False


def audit_table_write(
    *,
    table_name: str,
    action: str,
    record_key: Mapping[str, Any] | None,
    before_data: Mapping[str, Any] | None = None,
    after_data: Mapping[str, Any] | None = None,
    status: str = "success",
    error_message: str | None = None,
    query_text: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    database_name: str | None = None,
) -> bool:
    if not should_audit_table(table_name):
        return False

    config = current_app.config
    action_value = str(action or "").strip().upper()
    if action_value == "SELECT" and not _truthy(config.get("GR360_AUDIT_SELECT_ENABLED")):
        return False

    before_redacted = redact_data(before_data)
    after_redacted = redact_data(after_data)
    changed = calculate_changed_data(before_redacted, after_redacted)
    payload = {
        "LOGAPPSTAMP": _new_stamp_25(),
        "CORRELATION_ID": _correlation_id(),
        "APP_NAME": str(config.get("GR360_AUDIT_APP_NAME") or "APP_WEB")[:80],
        "ENVIRONMENT": str(config.get("GR360_AUDIT_ENVIRONMENT") or config.get("ENVIRONMENT") or "production")[:30],
        "ACTOR_LOGIN": _actor_login()[:100],
        "ACTOR_USSTAMP": _actor_usstamp()[:25],
        "REQUEST_METHOD": (request.method if has_request_context() else "")[:10],
        "REQUEST_PATH": (request.full_path.rstrip("?") if has_request_context() else "")[:500],
        "CLIENT_IP": _client_ip()[:64],
        "DATABASE_NAME": str(database_name or config.get("GR360_AUDIT_SOURCE_DATABASE") or "GR360_CORE")[:128],
        "SCHEMA_NAME": "dbo",
        "TABLE_NAME": normalize_table_name(table_name)[:128],
        "ACTION": action_value,
        "RECORD_KEY": _json_dumps_or_none(record_key or {}) or "{}",
        "BEFORE_DATA": _json_dumps_or_none(before_redacted),
        "AFTER_DATA": _json_dumps_or_none(after_redacted),
        "CHANGED_DATA": _json_dumps_or_none(changed),
        "QUERY_TEXT": query_text,
        "STATUS": str(status or "success").strip().lower()[:20],
        "ERROR_MESSAGE": (str(error_message or "")[:2000] or None),
        "METADATA": _json_dumps_or_none(metadata or {}),
    }
    return write_logapp_entry(payload, config=config)


def audit_select(*, table_name: str, record_key: Mapping[str, Any] | None = None, metadata: Mapping[str, Any] | None = None) -> bool:
    return audit_table_write(
        table_name=table_name,
        action="SELECT",
        record_key=record_key or {},
        status="success",
        metadata=metadata or {},
    )


def audited_execute_write(
    session,
    statement,
    params: Mapping[str, Any] | None = None,
    *,
    table_name: str,
    action: str,
    record_key: Mapping[str, Any] | None,
    before_loader: Callable[[Any], Mapping[str, Any] | None] | None = None,
    after_loader: Callable[[Any], Mapping[str, Any] | None] | None = None,
    query_text: str | None = None,
    metadata: Mapping[str, Any] | None = None,
):
    """Execute a direct SQLAlchemy write and emit a central GR360 audit event.

    This helper exists for new/direct db.session.execute(...) operations. The
    operation result is always returned; any audit error is swallowed by
    audit_table_write/write_logapp_entry.
    """
    before = before_loader(session) if before_loader else None
    result = session.execute(statement, params or {})
    after = after_loader(session) if after_loader else None
    audit_table_write(
        table_name=table_name,
        action=action,
        record_key=record_key or {},
        before_data=before,
        after_data=after,
        query_text=query_text or str(statement),
        metadata=metadata or {"source": "audited_execute_write"},
    )
    return result


def fetch_record_by_key(session, table_name: str, key: Mapping[str, Any]) -> dict[str, Any] | None:
    table = normalize_table_name(table_name)
    clauses = []
    params = {}
    for index, (field, value) in enumerate((key or {}).items()):
        field_name = normalize_table_name(field)
        if not field_name.replace("_", "").isalnum():
            continue
        param_name = f"k{index}"
        clauses.append(f"{field_name} = :{param_name}")
        params[param_name] = value
    if not table or not clauses:
        return None
    row = session.execute(text(f"SELECT TOP 1 * FROM dbo.{table} WHERE {' AND '.join(clauses)}"), params).mappings().first()
    return dict(row) if row else None
