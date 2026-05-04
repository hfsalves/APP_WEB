from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import lru_cache
import importlib.util
from pathlib import Path
import re
import sys
from types import ModuleType
from typing import Any

from flask import current_app, request
from sqlalchemy import text

from models import db


LEGACY_DIR = Path(__file__).resolve().parents[2] / "planeamento"
LEGACY_STATIC_DIR = LEGACY_DIR / "static"

LEGACY_SCRIPT_FILES = [
    "main.js",
    "week-navigation.js",
    "filter-state.js",
    "planning-project-filter.js",
    "assignment-lines.js",
    "assignment-menu.js",
    "production-close.js",
    "planning-debug.js",
]

TEAM_MANAGEMENT_SCRIPT_FILES = [
    "filter-state.js",
    "team-management.js",
    "team-absences.js",
    "team-roles.js",
    "team-regularizations.js",
]

MONTHLY_SHEET_SCRIPT_FILES = [
    "main.js",
]

MONTHLY_SHEET_INTERSOL_SCRIPT_FILES = [
    "main.js",
]

GR_MONITOR_DEFAULT_PAST_DAYS = 30
GR_MONITOR_DEFAULT_FUTURE_DAYS = 60

SHARED_API_PATTERNS = [
    re.compile(r"^employees$"),
]

MONTHLY_SHEET_API_PATTERNS = [
    re.compile(r"^monthly-detail$"),
    re.compile(r"^maintenance$"),
]

MONTHLY_SHEET_INTERSOL_API_PATTERNS = [
    re.compile(r"^intersol/monthly-detail$"),
    re.compile(r"^intersol/monthly-export$"),
    re.compile(r"^intersol/prime-records/[^/]+/validation$"),
]

PLANNING_API_PATTERNS = [
    re.compile(r"^debug-user$"),
    re.compile(r"^planning-teams$"),
    re.compile(r"^production-finitions$"),
    re.compile(r"^plans$"),
    re.compile(r"^plans/[^/]+$"),
    re.compile(r"^plans/[^/]+/values$"),
    re.compile(r"^plan-lines$"),
    re.compile(r"^plan-lines/[^/]+$"),
    re.compile(r"^plans/[^/]+/plan-lines$"),
    re.compile(r"^plans/[^/]+/production-records$"),
    re.compile(r"^production-records/[^/]+$"),
    re.compile(r"^production-records/[^/]+/lines$"),
    re.compile(r"^production-lines/[^/]+$"),
    re.compile(r"^projects/[^/]+/budget-items$"),
    re.compile(r"^production/close-week$"),
]

TEAM_MANAGEMENT_API_PATTERNS = [
    re.compile(r"^team-memberships$"),
    re.compile(r"^team-absences$"),
    re.compile(r"^team-absences/[^/]+$"),
    re.compile(r"^team-intersol-roles$"),
    re.compile(r"^team-intersol-roles/[^/]+$"),
    re.compile(r"^team-intersol-regularizations$"),
    re.compile(r"^team-intersol-regularizations/[^/]+$"),
]

API_SCOPE_PATTERNS = (
    ("shared", SHARED_API_PATTERNS),
    ("monthly_sheet", MONTHLY_SHEET_API_PATTERNS),
    ("monthly_sheet_intersol", MONTHLY_SHEET_INTERSOL_API_PATTERNS),
    ("planning", PLANNING_API_PATTERNS),
    ("team_management", TEAM_MANAGEMENT_API_PATTERNS),
)


@dataclass(frozen=True)
class LegacyConfig:
    server: str
    database: str
    username: str
    password: str
    driver: str = "ODBC Driver 17 for SQL Server"

    def as_odbc_string(self) -> str:
        return (
            f"DRIVER={{{self.driver}}};"
            f"SERVER={self.server};"
            f"DATABASE={self.database};"
            f"UID={self.username};"
            f"PWD={self.password};"
            "TrustServerCertificate=Yes;"
        )


@dataclass
class LegacyEnvironment:
    app_module: ModuleType
    database_module: ModuleType
    app: Any
    database: Any


def _extract_sql_part(conn_str: str, key: str) -> str:
    pattern = re.compile(rf"{re.escape(key)}=([^;]+)", re.IGNORECASE)
    match = pattern.search(conn_str or "")
    return (match.group(1).strip() if match else "")


def _build_hsols_master_config() -> LegacyConfig:
    conn_map = current_app.config.get("DB_CONN_STRS") or {}
    client_conn = str(conn_map.get("client") or "").strip()
    if not client_conn:
        raise RuntimeError("Ligação client/GR360_CORE não configurada na app.")
    server = _extract_sql_part(client_conn, "SERVER")
    username = _extract_sql_part(client_conn, "UID")
    password = _extract_sql_part(client_conn, "PWD")
    driver = _extract_sql_part(client_conn, "DRIVER").strip("{}") or "ODBC Driver 17 for SQL Server"
    if not server or not username:
        raise RuntimeError("Não foi possível derivar a ligação HSOLS_MASTER a partir da ligação client.")
    return LegacyConfig(
        server=server,
        database="HSOLS_MASTER",
        username=username,
        password=password,
        driver=driver,
    )


def _load_module_from_path(module_name: str, file_path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Não foi possível carregar {file_path.name}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _import_legacy_environment(signature: tuple[str, str, str, str, str]) -> LegacyEnvironment:
    cfg = LegacyConfig(*signature)
    preserved: dict[str, ModuleType | None] = {}
    injected: dict[str, ModuleType] = {}
    for name in ("config", "database", "markets", "i18n", "intersol_monthly"):
        preserved[name] = sys.modules.get(name)
    try:
        config_module = ModuleType("config")
        config_module.MSSQLConfig = LegacyConfig
        config_module.get_mssql_config = lambda: cfg
        sys.modules["config"] = config_module
        injected["config"] = config_module

        for name in ("markets", "i18n", "intersol_monthly"):
            module = _load_module_from_path(f"gr_planning_legacy_{name}", LEGACY_DIR / f"{name}.py")
            sys.modules[name] = module
            injected[name] = module

        database_module = _load_module_from_path("gr_planning_legacy_database", LEGACY_DIR / "database.py")
        sys.modules["database"] = database_module
        injected["database"] = database_module

        app_module = _load_module_from_path("gr_planning_legacy_app", LEGACY_DIR / "app.py")
        app = getattr(app_module, "app", None)
        database = getattr(database_module, "database", None)
        if app is None or database is None:
            raise RuntimeError("O legado planeamento não expôs a app Flask ou a ligação à base de dados.")
        return LegacyEnvironment(
            app_module=app_module,
            database_module=database_module,
            app=app,
            database=database,
        )
    finally:
        for name in ("config", "database", "markets", "i18n", "intersol_monthly"):
            previous = preserved.get(name)
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


@lru_cache(maxsize=4)
def _legacy_environment_cached(signature: tuple[str, str, str, str, str]) -> LegacyEnvironment:
    return _import_legacy_environment(signature)


def get_legacy_environment() -> LegacyEnvironment:
    cfg = _build_hsols_master_config()
    return _legacy_environment_cached((cfg.server, cfg.database, cfg.username, cfg.password, cfg.driver))


def get_hsols_user(login_value: str | None) -> dict[str, Any] | None:
    login_code = (login_value or "").strip()
    if not login_code:
        return None
    env = get_legacy_environment()
    return env.database.fetch_user_by_code(login_code)


def can_access_planning(login_value: str | None) -> tuple[bool, dict[str, Any] | None]:
    user = get_hsols_user(login_value)
    if not user:
        return False, None
    allowed = bool(user.get("u_planning") or user.get("u_admin") or user.get("u_adminis"))
    return allowed, user


def can_access_team_management(login_value: str | None) -> tuple[bool, dict[str, Any] | None]:
    user = get_hsols_user(login_value)
    if not user:
        return False, None
    allowed = bool(user.get("u_teams") or user.get("u_admin"))
    return allowed, user


def can_access_monthly_sheet(login_value: str | None) -> tuple[bool, dict[str, Any] | None]:
    user = get_hsols_user(login_value)
    if not user:
        return False, None
    allowed = bool(user.get("u_admin"))
    return allowed, user


def can_access_monthly_sheet_intersol(login_value: str | None) -> tuple[bool, dict[str, Any] | None]:
    user = get_hsols_user(login_value)
    if not user:
        return False, None
    allowed = bool(user.get("u_adminis"))
    return allowed, user


def can_access_monitor(login_value: str | None) -> tuple[bool, dict[str, Any] | None]:
    user = get_hsols_user(login_value)
    if not user:
        return False, None
    allowed = bool(
        user.get("u_planning")
        or user.get("u_teams")
        or user.get("u_admin")
        or user.get("u_adminis")
    )
    return allowed, user


def get_api_access_scope(path: str) -> str | None:
    normalized = (path or "").strip().strip("/")
    for scope, patterns in API_SCOPE_PATTERNS:
        if any(pattern.match(normalized) for pattern in patterns):
            return scope
    return None


def is_allowed_api_path(path: str) -> bool:
    return get_api_access_scope(path) is not None


def _coerce_iso_date(value: Any) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value or "").strip()
    if not text:
        return ""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text[:19], fmt).date().isoformat()
        except ValueError:
            continue
    return text[:10]


def _coerce_float(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _parse_date_param(value: Any, fallback: date) -> date:
    text_value = str(value or "").strip()
    if not text_value:
        return fallback
    try:
        return datetime.strptime(text_value[:10], "%Y-%m-%d").date()
    except ValueError:
        return fallback


def _main_table_columns(table_name: str) -> set[str]:
    rows = db.session.execute(
        text("SELECT UPPER(COLUMN_NAME) AS CN FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = :table_name"),
        {"table_name": table_name},
    ).fetchall()
    return {str(row[0] or "").upper() for row in rows}


def _main_table_exists(table_name: str) -> bool:
    return db.session.execute(
        text("SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = :table_name"),
        {"table_name": table_name},
    ).first() is not None


def fetch_gr_monitor_tasks(
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    today = date.today()
    start = start_date or (today - timedelta(days=GR_MONITOR_DEFAULT_PAST_DAYS))
    end = end_date or (today + timedelta(days=GR_MONITOR_DEFAULT_FUTURE_DAYS))
    cols = _main_table_columns("TAREFAS")
    if not cols:
        return []

    def col(name: str) -> bool:
        return name.upper() in cols

    select_parts = [
        "CAST(T.TAREFASSTAMP AS varchar(50)) AS id" if col("TAREFASSTAMP") else "'' AS id",
        "CONVERT(varchar(10), T.DATA, 23) AS date" if col("DATA") else "'' AS date",
        "LEFT(CONVERT(varchar(8), T.HORA, 108), 5) AS time" if col("HORA") else "'' AS time",
        "LTRIM(RTRIM(ISNULL(CAST(T.TAREFA AS varchar(255)), ''))) AS title" if col("TAREFA") else "'' AS title",
        "LTRIM(RTRIM(ISNULL(CAST(T.DESCRICAO AS varchar(max)), ''))) AS description" if col("DESCRICAO") else "'' AS description",
        "LTRIM(RTRIM(ISNULL(CAST(T.ORIGEM AS varchar(20)), ''))) AS origin" if col("ORIGEM") else "'' AS origin",
        "LTRIM(RTRIM(ISNULL(CAST(T.ORISTAMP AS varchar(50)), ''))) AS origin_stamp" if col("ORISTAMP") else "'' AS origin_stamp",
        "LTRIM(RTRIM(ISNULL(CAST(T.UTILIZADOR AS varchar(60)), ''))) AS user_code" if col("UTILIZADOR") else "'' AS user_code",
        "LTRIM(RTRIM(ISNULL(U.NOME, T.UTILIZADOR))) AS user_name" if col("UTILIZADOR") else "'' AS user_name",
        "LTRIM(RTRIM(ISNULL(FE.NOME, ''))) AS company_name" if col("FEID") else "'' AS company_name",
        "LTRIM(RTRIM(ISNULL(CAST(T.ALOJAMENTO AS varchar(120)), ''))) AS location" if col("ALOJAMENTO") else "'' AS location",
        "ISNULL(T.PRIORIDADE, 0) AS priority" if col("PRIORIDADE") else "0 AS priority",
        "ISNULL(T.ESTADO, 0) AS status_code" if col("ESTADO") else "0 AS status_code",
        "LTRIM(RTRIM(ISNULL(TE.NOME, ''))) AS status_name" if col("ESTADO") and _main_table_exists("TAREFAEST") else "'' AS status_name",
    ]
    if col("TRATADO"):
        treated_expr = "CASE WHEN ISNULL(T.TRATADO, 0) = 1 THEN 1 ELSE 0 END"
    elif col("ESTADO") and _main_table_exists("TAREFAEST"):
        treated_expr = "CASE WHEN ISNULL(TE.FINAL, 0) = 1 THEN 1 ELSE 0 END"
    else:
        treated_expr = "0"
    select_parts.append(f"{treated_expr} AS treated")
    select_parts.append("CONVERT(varchar(10), T.DTTRATADO, 23) AS treated_date" if col("DTTRATADO") else "'' AS treated_date")
    select_parts.append("CONVERT(varchar(10), T.DTCONCLUIDA, 23) AS completed_date" if col("DTCONCLUIDA") else "'' AS completed_date")

    joins = []
    if col("UTILIZADOR"):
        joins.append("LEFT JOIN US U ON U.LOGIN = T.UTILIZADOR")
    if col("FEID"):
        joins.append("LEFT JOIN FE ON FE.FEID = T.FEID")
    if col("ESTADO") and _main_table_exists("TAREFAEST"):
        joins.append("LEFT JOIN TAREFAEST TE ON TE.CODIGO = T.ESTADO")

    where = []
    params: dict[str, Any] = {"start": start, "end": end}
    if col("DATA"):
        where.append("CAST(T.DATA AS date) BETWEEN :start AND :end")
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    order_sql = "ORDER BY T.DATA, T.HORA, T.TAREFASSTAMP" if col("DATA") and col("HORA") and col("TAREFASSTAMP") else ""
    sql = text(f"""
        SELECT {", ".join(select_parts)}
        FROM TAREFAS T
        {" ".join(joins)}
        {where_sql}
        {order_sql}
    """)

    rows = db.session.execute(sql, params).mappings().all()
    return [
        {
            "id": str(row.get("id") or "").strip(),
            "date": _coerce_iso_date(row.get("date")),
            "time": str(row.get("time") or "").strip(),
            "title": str(row.get("title") or "").strip(),
            "description": str(row.get("description") or "").strip(),
            "origin": str(row.get("origin") or "").strip(),
            "origin_stamp": str(row.get("origin_stamp") or "").strip(),
            "user_code": str(row.get("user_code") or "").strip(),
            "user_name": str(row.get("user_name") or row.get("user_code") or "").strip(),
            "company_name": str(row.get("company_name") or "").strip(),
            "location": str(row.get("location") or "").strip(),
            "priority": int(row.get("priority") or 0),
            "status_code": int(row.get("status_code") or 0),
            "status_name": str(row.get("status_name") or "").strip(),
            "treated": int(row.get("treated") or 0),
            "treated_date": _coerce_iso_date(row.get("treated_date")),
            "completed_date": _coerce_iso_date(row.get("completed_date")),
        }
        for row in rows
    ]


def fetch_gr_task_status_options() -> list[dict[str, Any]]:
    if not _main_table_exists("TAREFAEST"):
        return []
    rows = db.session.execute(text("""
        SELECT CODIGO, NOME, ISNULL(FINAL, 0) AS FINAL
        FROM TAREFAEST
        WHERE ISNULL(ATIVO, 1) = 1
        ORDER BY ISNULL(ORDEM, 0), CODIGO
    """)).mappings().all()
    return [
        {
            "code": int(row.get("CODIGO") or 0),
            "name": str(row.get("NOME") or "").strip(),
            "final": int(row.get("FINAL") or 0),
        }
        for row in rows
    ]


def update_gr_task_status(task_id: str, status_code: int, user_login: str = "") -> dict[str, Any]:
    normalized_id = str(task_id or "").strip()
    if not normalized_id:
        raise ValueError("missing_task_id")
    cols = _main_table_columns("TAREFAS")
    if "ESTADO" not in cols:
        raise ValueError("task_status_unavailable")

    status_row = None
    if _main_table_exists("TAREFAEST"):
        status_row = db.session.execute(text("""
            SELECT CODIGO, NOME, ISNULL(FINAL, 0) AS FINAL
            FROM TAREFAEST
            WHERE CODIGO = :code
        """), {"code": status_code}).mappings().first()
        if not status_row:
            raise ValueError("invalid_status")

    is_final = int((status_row or {}).get("FINAL") or 0) == 1
    set_parts = ["ESTADO = :status_code"]
    params: dict[str, Any] = {
        "task_id": normalized_id,
        "status_code": int(status_code),
    }
    if "TRATADO" in cols:
        set_parts.append("TRATADO = :treated")
        params["treated"] = 1 if is_final else 0
    if "DTTRATADO" in cols:
        set_parts.append("DTTRATADO = CASE WHEN :treated_date_flag = 1 THEN GETDATE() ELSE CONVERT(date, '19000101') END")
        params["treated_date_flag"] = 1 if is_final else 0
    if "DTCONCLUIDA" in cols:
        set_parts.append("DTCONCLUIDA = CASE WHEN :completed_date_flag = 1 THEN SYSDATETIME() ELSE NULL END")
        params["completed_date_flag"] = 1 if is_final else 0
    if "DTALTERACAO" in cols:
        set_parts.append("DTALTERACAO = SYSDATETIME()")
    if "USERALTERACAO" in cols:
        set_parts.append("USERALTERACAO = :user_login")
        params["user_login"] = str(user_login or "").strip()

    result = db.session.execute(text(f"""
        UPDATE TAREFAS
        SET {", ".join(set_parts)}
        WHERE TAREFASSTAMP = :task_id
    """), params)
    if result.rowcount == 0:
        db.session.rollback()
        raise ValueError("task_not_found")
    db.session.commit()
    return {
        "ok": True,
        "status_code": int(status_code),
        "status_name": str((status_row or {}).get("NOME") or "").strip(),
        "treated": 1 if is_final else 0,
    }


def open_legacy_request(
    legacy_path: str,
    *,
    login_value: str,
    method: str = "GET",
    query_string: Any = None,
    data: bytes | None = None,
    content_type: str | None = None,
    access_mode: str = "planning",
    legacy_user: dict[str, Any] | None = None,
) -> Any:
    resolved_legacy_user = legacy_user
    if resolved_legacy_user is None:
        if access_mode == "planning":
            allowed, resolved_legacy_user = can_access_planning(login_value)
        elif access_mode == "monthly_sheet":
            allowed, resolved_legacy_user = can_access_monthly_sheet(login_value)
        elif access_mode == "monthly_sheet_intersol":
            allowed, resolved_legacy_user = can_access_monthly_sheet_intersol(login_value)
        elif access_mode == "team_management":
            allowed, resolved_legacy_user = can_access_team_management(login_value)
        elif access_mode == "shared":
            allowed, resolved_legacy_user = can_access_planning(login_value)
            if not allowed or not resolved_legacy_user:
                allowed, resolved_legacy_user = can_access_monthly_sheet(login_value)
            if not allowed or not resolved_legacy_user:
                allowed, resolved_legacy_user = can_access_monthly_sheet_intersol(login_value)
            if not allowed or not resolved_legacy_user:
                allowed, resolved_legacy_user = can_access_team_management(login_value)
        else:
            raise ValueError(f"Modo de acesso legado invalido: {access_mode}")
        if not allowed or not resolved_legacy_user:
            raise PermissionError("Utilizador sem permissao para aceder ao modulo GR Planning.")
    env = get_legacy_environment()
    with env.app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user"] = resolved_legacy_user
            sess["language"] = "pt"
        return client.open(
            legacy_path,
            method=method,
            query_string=query_string,
            data=data,
            content_type=content_type,
            follow_redirects=False,
        )


def _extract_body_from_html(html: str) -> str:
    match = re.search(r"<body[^>]*>(.*)</body>", html, flags=re.IGNORECASE | re.DOTALL)
    return match.group(1) if match else html


def _extract_balanced_block(source: str, start_marker: str, tag_name: str) -> tuple[str, int, int]:
    start = source.find(start_marker)
    if start < 0:
        return "", -1, -1
    open_pat = re.compile(rf"<{tag_name}\b", re.IGNORECASE)
    close_pat = re.compile(rf"</{tag_name}>", re.IGNORECASE)
    pos = start
    depth = 0
    end = -1
    while pos < len(source):
        next_open = open_pat.search(source, pos)
        next_close = close_pat.search(source, pos)
        if next_close is None:
            break
        if next_open and next_open.start() < next_close.start():
            depth += 1
            pos = next_open.end()
            continue
        depth -= 1
        pos = next_close.end()
        if depth == 0:
            end = pos
            break
    if end < 0:
        return "", start, -1
    return source[start:end], start, end


def _extract_body_attr(html: str, attr_name: str) -> str:
    pattern = re.compile(rf"{re.escape(attr_name)}=(['\"])(.*?)\1", re.IGNORECASE | re.DOTALL)
    match = pattern.search(html)
    return match.group(2) if match else ""


def _legacy_static_prefix() -> str:
    return "/gr_planning/legacy-static/"


def _extract_inline_script_blocks(html: str) -> str:
    script_pattern = re.compile(
        r"<script(?![^>]*\bsrc=)[^>]*>.*?</script>",
        flags=re.IGNORECASE | re.DOTALL,
    )
    return "\n".join(match.group(0) for match in script_pattern.finditer(html))


def _rewrite_common_legacy_markup(body_html: str) -> str:
    body_html = re.sub(
        r'(["\'])/static/',
        rf"\1{_legacy_static_prefix()}",
        body_html,
        flags=re.IGNORECASE,
    )
    body_html = re.sub(
        r'(["\'])/api/',
        r"\1/api/",
        body_html,
        flags=re.IGNORECASE,
    )
    return body_html


def rewrite_legacy_body_html(html: str) -> tuple[str, dict[str, str]]:
    body_html = _extract_body_from_html(html).replace("\x00", "")
    filters_html, _, _ = _extract_balanced_block(body_html, '<div class="filters-layout">', "div")
    planning_head_html, _, _ = _extract_balanced_block(body_html, '<section class="planning-head-card">', "section")
    planning_main_html, _, _ = _extract_balanced_block(body_html, '<main class="dashboard-main">', "main")
    assignment_modal_pos = body_html.find('<div id="assignment-modal"')
    modals_html = body_html[assignment_modal_pos:] if assignment_modal_pos >= 0 else ""
    body_html = "\n".join(part for part in (
        filters_html,
        planning_head_html,
        planning_main_html,
        modals_html,
    ) if part)
    body_html = _rewrite_common_legacy_markup(body_html)
    body_html = body_html.replace('action="/"', 'action="/gr_planning"')
    body_html = body_html.replace('href="/"', 'href="/gr_planning"')
    meta = {
        "week_start": _extract_body_attr(html, "data-week-start"),
        "week_end": _extract_body_attr(html, "data-week-end"),
    }
    return body_html, meta


def build_planning_page(login_value: str) -> tuple[str, dict[str, str]]:
    response = open_legacy_request(
        "/",
        login_value=login_value,
        method="GET",
        query_string=request.args,
        access_mode="planning",
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Legado respondeu com erro {response.status_code}.")
    html = response.get_data(as_text=True)
    return rewrite_legacy_body_html(html)


def rewrite_team_management_body_html(html: str) -> tuple[str, dict[str, str]]:
    body_html = _extract_body_from_html(html).replace("\x00", "")
    filters_html, _, _ = _extract_balanced_block(body_html, '<section class="filters-card"', "section")
    db_error_html, _, _ = _extract_balanced_block(body_html, '<p class="error">', "p")
    layout_html, _, _ = _extract_balanced_block(body_html, '<div class="team-management-layout"', "div")
    team_action_modal_pos = body_html.find('<div id="team-action-modal"')
    modals_html = body_html[team_action_modal_pos:] if team_action_modal_pos >= 0 else ""
    body_html = "\n".join(part for part in (
        filters_html,
        db_error_html,
        layout_html,
        modals_html,
    ) if part)
    body_html = _rewrite_common_legacy_markup(body_html)
    body_html = body_html.replace('action="/teams"', 'action="/gr_planning/teams"')
    body_html = body_html.replace("action='/teams'", "action='/gr_planning/teams'")
    body_html = body_html.replace('href="/teams"', 'href="/gr_planning/teams"')
    body_html = body_html.replace("href='/teams'", "href='/gr_planning/teams'")
    meta = {
        "reference_date": _extract_body_attr(html, "data-reference-date"),
        "week_start": _extract_body_attr(html, "data-week-start"),
        "week_end": _extract_body_attr(html, "data-week-end"),
        "team_options": _extract_body_attr(html, "data-team-options"),
    }
    return body_html, meta


def build_team_management_page(
    login_value: str,
    *,
    legacy_user: dict[str, Any] | None = None,
) -> tuple[str, dict[str, str]]:
    response = open_legacy_request(
        "/teams",
        login_value=login_value,
        method="GET",
        query_string=request.args,
        access_mode="team_management",
        legacy_user=legacy_user,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Legado respondeu com erro {response.status_code}.")
    html = response.get_data(as_text=True)
    return rewrite_team_management_body_html(html)


def rewrite_monthly_sheet_body_html(html: str) -> tuple[str, dict[str, str]]:
    body_html = _extract_body_from_html(html).replace("\x00", "")
    filters_html, _, _ = _extract_balanced_block(body_html, '<div class="filters-layout">', "div")
    main_html, _, _ = _extract_balanced_block(body_html, '<main class="dashboard-main">', "main")
    detail_modal_pos = body_html.find('<div id="monthly-detail-modal"')
    modals_html = body_html[detail_modal_pos:] if detail_modal_pos >= 0 else ""
    body_html = "\n".join(part for part in (
        filters_html,
        main_html,
        modals_html,
    ) if part)
    body_html = _rewrite_common_legacy_markup(body_html)
    body_html = body_html.replace('action="/folha-mensal"', 'action="/gr_planning/folha-mensal"')
    body_html = body_html.replace("action='/folha-mensal'", "action='/gr_planning/folha-mensal'")
    body_html = body_html.replace('href="/folha-mensal"', 'href="/gr_planning/folha-mensal"')
    body_html = body_html.replace("href='/folha-mensal'", "href='/gr_planning/folha-mensal'")
    meta = {
        "inline_script_html": _extract_inline_script_blocks(html),
    }
    return body_html, meta


def build_monthly_sheet_page(
    login_value: str,
    *,
    legacy_user: dict[str, Any] | None = None,
) -> tuple[str, dict[str, str]]:
    response = open_legacy_request(
        "/folha-mensal",
        login_value=login_value,
        method="GET",
        query_string=request.args,
        access_mode="monthly_sheet",
        legacy_user=legacy_user,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Legado respondeu com erro {response.status_code}.")
    html = response.get_data(as_text=True)
    return rewrite_monthly_sheet_body_html(html)


def rewrite_monthly_sheet_intersol_body_html(html: str) -> tuple[str, dict[str, str]]:
    body_html = _extract_body_from_html(html).replace("\x00", "")
    filters_html, _, _ = _extract_balanced_block(body_html, '<div class="filters-layout">', "div")
    main_html, _, _ = _extract_balanced_block(body_html, '<main class="dashboard-main">', "main")
    detail_modal_pos = body_html.find('<div id="monthly-detail-modal"')
    modals_html = body_html[detail_modal_pos:] if detail_modal_pos >= 0 else ""
    body_html = "\n".join(part for part in (
        filters_html,
        main_html,
        modals_html,
    ) if part)
    body_html = _rewrite_common_legacy_markup(body_html)
    for legacy_path in ("/intersol/folha-mensal", "/folha-mensal-intersol"):
        body_html = body_html.replace(f'action="{legacy_path}"', 'action="/gr_planning/folha-mensal-intersol"')
        body_html = body_html.replace(f"action='{legacy_path}'", "action='/gr_planning/folha-mensal-intersol'")
        body_html = body_html.replace(f'href="{legacy_path}"', 'href="/gr_planning/folha-mensal-intersol"')
        body_html = body_html.replace(f"href='{legacy_path}'", "href='/gr_planning/folha-mensal-intersol'")
    inline_script_html = _extract_inline_script_blocks(html)
    inline_script_html = inline_script_html.replace(
        "/api/intersol/monthly-export",
        "/api/gr_planning/intersol/monthly-export",
    )
    meta = {
        "inline_script_html": inline_script_html,
    }
    return body_html, meta


def build_monthly_sheet_intersol_page(
    login_value: str,
    *,
    legacy_user: dict[str, Any] | None = None,
) -> tuple[str, dict[str, str]]:
    response = open_legacy_request(
        "/intersol/folha-mensal",
        login_value=login_value,
        method="GET",
        query_string=request.args,
        access_mode="monthly_sheet_intersol",
        legacy_user=legacy_user,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Legado respondeu com erro {response.status_code}.")
    html = response.get_data(as_text=True)
    return rewrite_monthly_sheet_intersol_body_html(html)
