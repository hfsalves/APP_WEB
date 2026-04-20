from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import importlib.util
from pathlib import Path
import re
import sys
from types import ModuleType
from typing import Any

from flask import current_app, request


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


def get_api_access_scope(path: str) -> str | None:
    normalized = (path or "").strip().strip("/")
    for scope, patterns in API_SCOPE_PATTERNS:
        if any(pattern.match(normalized) for pattern in patterns):
            return scope
    return None


def is_allowed_api_path(path: str) -> bool:
    return get_api_access_scope(path) is not None


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
