from __future__ import annotations

from datetime import date, datetime, timedelta
import re
import uuid

import pyodbc
from flask import Blueprint, current_app, g, jsonify, render_template, request, session
from flask_login import current_user, login_required
from sqlalchemy import text

from i18n import BASE_LANGUAGE, SESSION_LANGUAGE_KEY, extract_user_language, normalize_language, reload_translations
from models import db


bp = Blueprint(
    "gr_management_map",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/gr_management_map/static",
)

NO_ACCESS_ORIGIN = "__MAPA_GESTAO_GR_SEM_ACESSO__"

MAPA_GESTAO_GR_I18N_KEYS = [
    "mapa_gestao_gr.title",
    "mapa_gestao_gr.subtitle",
    "mapa_gestao_gr.origin",
    "mapa_gestao_gr.all_origins",
    "mapa_gestao_gr.no_origin",
    "mapa_gestao_gr.origins_count",
    "mapa_gestao_gr.date_start",
    "mapa_gestao_gr.date_end",
    "mapa_gestao_gr.cost_center",
    "mapa_gestao_gr.all_centers",
    "mapa_gestao_gr.no_center",
    "mapa_gestao_gr.centers_count",
    "mapa_gestao_gr.centers_available",
    "mapa_gestao_gr.no_centers_filters",
    "mapa_gestao_gr.accesses",
    "mapa_gestao_gr.collapse_all",
    "mapa_gestao_gr.expand_all",
    "mapa_gestao_gr.family",
    "mapa_gestao_gr.month_jan",
    "mapa_gestao_gr.month_feb",
    "mapa_gestao_gr.month_mar",
    "mapa_gestao_gr.month_apr",
    "mapa_gestao_gr.month_may",
    "mapa_gestao_gr.month_jun",
    "mapa_gestao_gr.month_jul",
    "mapa_gestao_gr.month_aug",
    "mapa_gestao_gr.month_sep",
    "mapa_gestao_gr.month_oct",
    "mapa_gestao_gr.month_nov",
    "mapa_gestao_gr.month_dec",
    "mapa_gestao_gr.total",
    "mapa_gestao_gr.weight",
    "mapa_gestao_gr.loading",
    "mapa_gestao_gr.access_modal_title",
    "mapa_gestao_gr.access_modal_hint",
    "mapa_gestao_gr.user",
    "mapa_gestao_gr.search_user",
    "mapa_gestao_gr.clear_accesses",
    "mapa_gestao_gr.users_empty",
    "mapa_gestao_gr.origins_empty",
    "mapa_gestao_gr.admin_full_access",
    "mapa_gestao_gr.accesses_unsaved",
    "mapa_gestao_gr.accesses_saved",
    "mapa_gestao_gr.select_origins",
    "mapa_gestao_gr.all",
    "mapa_gestao_gr.none",
    "mapa_gestao_gr.select_cost_centers",
    "mapa_gestao_gr.selected",
    "mapa_gestao_gr.type",
    "mapa_gestao_gr.costs",
    "mapa_gestao_gr.revenue",
    "mapa_gestao_gr.balance",
    "mapa_gestao_gr.accumulated",
    "mapa_gestao_gr.no_access",
    "mapa_gestao_gr.no_data_filters",
    "mapa_gestao_gr.no_visible_data",
    "mapa_gestao_gr.filters_all_origins",
    "mapa_gestao_gr.filters_no_origins",
    "mapa_gestao_gr.detail",
    "mapa_gestao_gr.detail_select_value",
    "mapa_gestao_gr.detail_empty",
    "mapa_gestao_gr.detail_loading",
    "mapa_gestao_gr.detail_records",
    "mapa_gestao_gr.detail_total",
    "mapa_gestao_gr.detail_error",
    "mapa_gestao_gr.document",
    "mapa_gestao_gr.number",
    "mapa_gestao_gr.date",
    "mapa_gestao_gr.name",
    "mapa_gestao_gr.reference",
    "mapa_gestao_gr.description",
    "mapa_gestao_gr.quantity",
    "mapa_gestao_gr.price",
    "common.apply",
    "common.clear",
    "common.cancel",
    "common.close",
    "common.save",
]


@bp.errorhandler(Exception)
def _gr_management_map_error(exc: Exception):
    try:
        current_app.logger.exception("Erro no modulo mapa_gestao_gr")
    except Exception:
        pass
    return jsonify({"error": str(exc) or "Erro interno no mapa de gestao GR."}), 500


def _hsols_master_conn_str() -> str:
    conn_map = current_app.config.get("DB_CONN_STRS") or {}
    client_conn = str(conn_map.get("client") or "").strip()
    if not client_conn:
        raise RuntimeError("Ligacao client/GR360_CORE nao configurada.")
    if re.search(r"(?:^|;)DATABASE=", client_conn, flags=re.IGNORECASE):
        return re.sub(
            r"((?:^|;)DATABASE=)[^;]*",
            r"\1HSOLS_MASTER",
            client_conn,
            count=1,
            flags=re.IGNORECASE,
        )
    return client_conn.rstrip(";") + ";DATABASE=HSOLS_MASTER;"


def _master_rows(sql: str, params: list | tuple | None = None) -> list[dict]:
    with pyodbc.connect(_hsols_master_conn_str(), timeout=10) as conn:
        cursor = conn.cursor()
        values = params or []
        if isinstance(values, (list, tuple)):
            cursor.execute(sql, *values)
        else:
            cursor.execute(sql, values)
        columns = [col[0] for col in cursor.description or []]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _master_view_columns(view_name: str) -> dict[str, str]:
    safe_name = re.sub(r"[^A-Za-z0-9_]", "", str(view_name or ""))
    if not safe_name:
        return {}
    with pyodbc.connect(_hsols_master_conn_str(), timeout=10) as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT TOP 0 * FROM dbo.{safe_name}")
        return {str(col[0]).upper(): str(col[0]) for col in cursor.description or []}


def _column_expr(columns: dict[str, str], candidates: list[str], alias: str, kind: str = "text") -> str:
    column_name = None
    for candidate in candidates:
        column_name = columns.get(str(candidate or "").upper())
        if column_name:
            break
    if not column_name:
        if kind == "number":
            return f"CAST(0 AS decimal(18, 6)) AS {alias}"
        if kind == "date":
            return f"CAST(NULL AS date) AS {alias}"
        return f"CAST('' AS nvarchar(4000)) AS {alias}"
    quoted = f"[{column_name}]"
    if kind == "number":
        return f"ISNULL({quoted}, 0) AS {alias}"
    if kind == "date":
        return f"CAST({quoted} AS date) AS {alias}"
    return f"LTRIM(RTRIM(ISNULL(CAST({quoted} AS nvarchar(4000)), ''))) AS {alias}"


def _parse_date_param(value: str | None, fallback: date) -> date:
    raw = str(value or "").strip()
    if not raw:
        return fallback
    try:
        return datetime.strptime(raw[:10], "%Y-%m-%d").date()
    except ValueError:
        return fallback


def _parse_list_param(value: str | None) -> list[str]:
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


def _normalize_origin_key(value: str | None) -> str:
    return str(value or "").strip().replace("-", "_").upper()


def _origin_sql_expr(column: str) -> str:
    return f"UPPER(REPLACE(LTRIM(RTRIM(ISNULL({column}, ''))), '-', '_'))"


def _session_first_language() -> str:
    active_language = normalize_language(getattr(g, "language", None))
    if active_language:
        return active_language
    session_key = current_app.config.get("I18N_SESSION_KEY", SESSION_LANGUAGE_KEY)
    session_language = normalize_language(session.get(session_key) or session.get("lang"))
    if session_language:
        return session_language
    user_language = ""
    try:
        if current_user.is_authenticated:
            user_language = extract_user_language(current_user)
    except Exception:
        user_language = ""
    return normalize_language(user_language or current_app.config.get("DEFAULT_LANGUAGE")) or "pt_PT"


def _map_i18n_payload(language: str) -> dict[str, str]:
    catalogs = reload_translations()
    active_language = normalize_language(language) or BASE_LANGUAGE
    active_catalog = catalogs.get(active_language, {}) or {}
    base_catalog = catalogs.get(BASE_LANGUAGE, {}) or {}
    payload: dict[str, str] = {}
    for key in MAPA_GESTAO_GR_I18N_KEYS:
        value = active_catalog.get(key)
        if value is None:
            value = base_catalog.get(key, key)
        payload[key] = str(value)
    return payload


def _default_period(today: date | None = None) -> tuple[date, date]:
    current = today or date.today()
    if current.month == 1:
        year = current.year - 1
        return date(year, 1, 1), date(year, 12, 31)
    start = date(current.year, 1, 1)
    end = date(current.year, current.month, 1) - timedelta(days=1)
    return start, end


def _is_admin_user() -> bool:
    raw_admin = getattr(current_user, "ADMIN", False)
    if str(raw_admin).strip().lower() in {"1", "true", "yes", "sim"} or raw_admin is True:
        return True
    login = str(getattr(current_user, "LOGIN", "") or "").strip()
    usstamp = str(getattr(current_user, "USSTAMP", "") or "").strip()
    if not login and not usstamp:
        return False
    try:
        row = db.session.execute(
            text("""
                SELECT TOP 1 ISNULL(ADMIN, 0) AS admin
                FROM dbo.US
                WHERE (:usstamp <> '' AND USSTAMP = :usstamp)
                   OR (:login <> '' AND LOGIN = :login)
                ORDER BY CASE WHEN USSTAMP = :usstamp THEN 0 ELSE 1 END
            """),
            {"usstamp": usstamp, "login": login},
        ).mappings().first()
        value = row.get("admin") if row else 0
        return str(value).strip().lower() in {"1", "true", "yes", "sim"} or value is True
    except Exception:
        db.session.rollback()
        return False


def _current_login() -> str:
    return str(getattr(current_user, "LOGIN", "") or "").strip()


def _current_usstamp() -> str:
    return str(getattr(current_user, "USSTAMP", "") or "").strip()


def _ensure_access_schema() -> None:
    db.session.execute(text("""
        IF OBJECT_ID('dbo.GR_MAPA_GESTAO_ACESSOS', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.GR_MAPA_GESTAO_ACESSOS
            (
                GRMAPACESSOSTAMP varchar(25) NOT NULL
                    CONSTRAINT PK_GR_MAPA_GESTAO_ACESSOS PRIMARY KEY,
                USSTAMP varchar(25) NOT NULL,
                LOGIN varchar(60) NOT NULL,
                ORIGEM varchar(80) NOT NULL,
                ATIVO bit NOT NULL
                    CONSTRAINT DF_GR_MAPA_GESTAO_ACESSOS_ATIVO DEFAULT (1),
                DTCRI datetime NOT NULL
                    CONSTRAINT DF_GR_MAPA_GESTAO_ACESSOS_DTCRI DEFAULT (GETDATE()),
                USERCRIACAO varchar(60) NOT NULL
                    CONSTRAINT DF_GR_MAPA_GESTAO_ACESSOS_USERCRIACAO DEFAULT ('')
            );
        END;

        IF NOT EXISTS (
            SELECT 1
            FROM sys.indexes
            WHERE object_id = OBJECT_ID('dbo.GR_MAPA_GESTAO_ACESSOS')
              AND name = 'UX_GR_MAPA_GESTAO_ACESSOS_USER_ORIGEM'
        )
        BEGIN
            CREATE UNIQUE INDEX UX_GR_MAPA_GESTAO_ACESSOS_USER_ORIGEM
            ON dbo.GR_MAPA_GESTAO_ACESSOS (USSTAMP, ORIGEM);
        END;
    """))
    db.session.commit()


def _available_origins() -> list[str]:
    rows = _master_rows("""
        SELECT origem
        FROM (
            SELECT DISTINCT UPPER(REPLACE(LTRIM(RTRIM(ISNULL(BDADOS, ''))), '-', '_')) AS origem
            FROM dbo.V_CUSTO_ORIGENS
            WHERE LTRIM(RTRIM(ISNULL(BDADOS, ''))) <> ''
            UNION
            SELECT DISTINCT UPPER(REPLACE(LTRIM(RTRIM(ISNULL(BDADOS, ''))), '-', '_')) AS origem
            FROM dbo.V_FT_ORIGENS
            WHERE LTRIM(RTRIM(ISNULL(BDADOS, ''))) <> ''
        ) AS origins
        ORDER BY origem
    """)
    return [str(row.get("origem") or "").strip() for row in rows if str(row.get("origem") or "").strip()]


def _allowed_origins_for_current_user() -> list[str] | None:
    if _is_admin_user():
        return None
    _ensure_access_schema()
    rows = db.session.execute(
        text("""
            SELECT DISTINCT LTRIM(RTRIM(ISNULL(ORIGEM, ''))) AS origem
            FROM dbo.GR_MAPA_GESTAO_ACESSOS
            WHERE ATIVO = 1
              AND LTRIM(RTRIM(ISNULL(ORIGEM, ''))) <> ''
              AND (
                    USSTAMP = :usstamp
                 OR (:login <> '' AND LOGIN = :login)
              )
            ORDER BY origem
        """),
        {"usstamp": _current_usstamp(), "login": _current_login()},
    ).mappings().all()
    return [_normalize_origin_key(row.get("origem")) for row in rows if _normalize_origin_key(row.get("origem"))]


def _effective_origins(requested_origins: list[str]) -> tuple[list[str], list[str] | None, bool]:
    allowed_origins = _allowed_origins_for_current_user()
    normalized_requested = [_normalize_origin_key(origem) for origem in requested_origins if _normalize_origin_key(origem)]
    if allowed_origins is None:
        return normalized_requested, None, True
    if not allowed_origins:
        return [NO_ACCESS_ORIGIN], [], False
    allowed_set = set(allowed_origins)
    if normalized_requested:
        effective = [origem for origem in normalized_requested if origem in allowed_set]
    else:
        effective = allowed_origins
    return (effective or [NO_ACCESS_ORIGIN], allowed_origins, bool(effective))


def _base_filters() -> tuple[date, date, list[str], list[str]]:
    default_start, default_end = _default_period()
    start = _parse_date_param(request.args.get("data_inicio"), default_start)
    end = _parse_date_param(request.args.get("data_fim"), default_end)
    if end < start:
        start, end = end, start
    requested_origins = _parse_list_param(request.args.get("origens"))
    origens, _allowed_origins, _has_access = _effective_origins(requested_origins)
    ccustos = _parse_list_param(request.args.get("ccustos"))
    if len(ccustos) > 200:
        ccustos = []
    return (start, end, origens, ccustos)


def _filtered_where(
    *,
    date_column: str,
    origin_column: str = "BDADOS",
    ccusto_column: str = "CCUSTO",
    include_origins: bool = True,
    include_ccustos: bool = True,
) -> tuple[str, dict]:
    start, end, origens, ccustos = _base_filters()
    params: dict = {"data_inicio": start, "data_fim_exclusive": end + timedelta(days=1)}
    where_parts = [
        f"{date_column} >= ?",
        f"{date_column} < ?",
    ]
    ordered_values: list = [params["data_inicio"], params["data_fim_exclusive"]]

    if include_origins and origens:
        where_parts.append(f"{_origin_sql_expr(origin_column)} IN (" + ",".join("?" for _ in origens) + ")")
        ordered_values.extend(origens)
    if include_ccustos and ccustos:
        where_parts.append(f"LTRIM(RTRIM(ISNULL({ccusto_column}, ''))) IN (" + ",".join("?" for _ in ccustos) + ")")
        ordered_values.extend(ccustos)

    return " AND ".join(where_parts), {"values": ordered_values}


def _cost_where(include_origins: bool = True, include_ccustos: bool = True) -> tuple[str, dict]:
    return _filtered_where(
        date_column="DATA",
        origin_column="BDADOS",
        ccusto_column="CCUSTO",
        include_origins=include_origins,
        include_ccustos=include_ccustos,
    )


def _sales_where(include_origins: bool = True, include_ccustos: bool = True) -> tuple[str, dict]:
    return _filtered_where(
        date_column="FDATA",
        origin_column="BDADOS",
        ccusto_column="CCUSTO_GERAL",
        include_origins=include_origins,
        include_ccustos=include_ccustos,
    )


def _level_from_ref(ref: str) -> int:
    return str(ref or "").count(".") + 1


def _sort_key(ref: str):
    parts = []
    for part in str(ref or "").split("."):
        try:
            parts.append((0, int(part)))
        except ValueError:
            parts.append((1, part))
    return parts


def _row_get(row: dict, key: str, default=None):
    if key in row:
        return row.get(key, default)
    target = str(key or "").lower()
    for row_key, value in row.items():
        if str(row_key or "").lower() == target:
            return value
    return default


def _ensure_family_node(nodes: dict, ref: str) -> dict:
    clean = str(ref or "").strip()
    if clean not in nodes:
        nodes[clean] = {
            "ref": clean,
            "nome": clean,
            "nivel": _level_from_ref(clean),
            "meses": [0.0] * 12,
            "total": 0.0,
            "orc_meses": [0.0] * 12,
            "orc_total": 0.0,
        }
    return nodes[clean]


def _is_revenue_ref(ref: str) -> bool:
    clean = str(ref or "").strip()
    return clean == "7" or clean.startswith("7.")


@bp.route("/gr_planning/mapa_gestao_gr")
@bp.route("/gr_planning/mapa-gestao-gr")
@login_required
def mapa_gestao_gr_page():
    reload_translations()
    _ensure_access_schema()
    is_admin = _is_admin_user()
    allowed_origins = _allowed_origins_for_current_user()
    default_start, default_end = _default_period()
    map_language = _session_first_language()
    map_i18n = _map_i18n_payload(map_language)

    def map_t(key: str, **kwargs) -> str:
        text_value = map_i18n.get(str(key or ""), str(key or ""))
        if kwargs:
            try:
                return text_value.format(**kwargs)
            except Exception:
                return text_value
        return text_value

    return render_template(
        "gr_management_map/mapa_gestao_gr.html",
        page_title="Mapa Gestao GR",
        ano_atual=default_start.year,
        data_inicio_default=default_start.isoformat(),
        data_fim_default=default_end.isoformat(),
        is_admin=is_admin,
        has_map_access=is_admin or bool(allowed_origins),
        mapa_gestao_gr_language=map_language,
        mapa_gestao_gr_i18n=map_i18n,
        map_t=map_t,
    )


@bp.route("/api/mapa_gestao_gr/origens")
@login_required
def api_mapa_gestao_gr_origens():
    try:
        allowed_origins = _allowed_origins_for_current_user()
        if allowed_origins == []:
            return jsonify({"options": [], "is_admin": False, "has_access": False})
        cost_where_sql, cost_bind = _cost_where(include_origins=False, include_ccustos=True)
        sales_where_sql, sales_bind = _sales_where(include_origins=False, include_ccustos=True)
        rows = _master_rows(
            f"""
            SELECT origem
            FROM (
                SELECT DISTINCT UPPER(REPLACE(LTRIM(RTRIM(ISNULL(BDADOS, ''))), '-', '_')) AS origem
                FROM dbo.V_CUSTO_ORIGENS
                WHERE {cost_where_sql}
                  AND LTRIM(RTRIM(ISNULL(BDADOS, ''))) <> ''
                UNION
                SELECT DISTINCT UPPER(REPLACE(LTRIM(RTRIM(ISNULL(BDADOS, ''))), '-', '_')) AS origem
                FROM dbo.V_FT_ORIGENS
                WHERE {sales_where_sql}
                  AND LTRIM(RTRIM(ISNULL(BDADOS, ''))) <> ''
            ) AS origins
            ORDER BY origem
            """,
            list(cost_bind["values"]) + list(sales_bind["values"]),
        )
        options = [_normalize_origin_key(row.get("origem")) for row in rows if _normalize_origin_key(row.get("origem"))]
        if allowed_origins is not None:
            allowed_set = set(allowed_origins)
            options = [origem for origem in options if origem in allowed_set]
        return jsonify({"options": options, "is_admin": allowed_origins is None, "has_access": True})
    except Exception as exc:
        return jsonify({"error": f"Erro ao obter origens: {exc}"}), 500


@bp.route("/api/mapa_gestao_gr/ccustos")
@login_required
def api_mapa_gestao_gr_ccustos():
    try:
        allowed_origins = _allowed_origins_for_current_user()
        if allowed_origins == []:
            return jsonify({"options": [], "is_admin": False, "has_access": False})
        where_sql, bind = _cost_where(include_origins=True, include_ccustos=False)
        rows = _master_rows(
            f"""
            SELECT DISTINCT LTRIM(RTRIM(ISNULL(CCUSTO, ''))) AS ccusto
            FROM dbo.V_CUSTO_ORIGENS
            WHERE {where_sql}
              AND LTRIM(RTRIM(ISNULL(CCUSTO, ''))) <> ''
            ORDER BY ccusto
            """,
            bind["values"],
        )
        return jsonify({"options": [{"ccusto": row["ccusto"], "tipo": ""} for row in rows if row.get("ccusto")]})
    except Exception as exc:
        return jsonify({"error": f"Erro ao obter centros de custo: {exc}"}), 500


@bp.route("/api/mapa_gestao_gr/acessos", methods=["GET", "POST"])
@login_required
def api_mapa_gestao_gr_acessos():
    if not _is_admin_user():
        return jsonify({"error": "Sem permissoes para gerir acessos."}), 403

    try:
        _ensure_access_schema()
        if request.method == "GET":
            users = db.session.execute(text("""
                SELECT
                    LTRIM(RTRIM(ISNULL(USSTAMP, ''))) AS usstamp,
                    LTRIM(RTRIM(ISNULL(LOGIN, ''))) AS login,
                    LTRIM(RTRIM(ISNULL(NOME, ''))) AS nome,
                    ISNULL(ADMIN, 0) AS admin
                FROM dbo.US
                WHERE LTRIM(RTRIM(ISNULL(LOGIN, ''))) <> ''
                ORDER BY LOGIN
            """)).mappings().all()
            assignments = db.session.execute(text("""
                SELECT
                    LTRIM(RTRIM(ISNULL(USSTAMP, ''))) AS usstamp,
                    LTRIM(RTRIM(ISNULL(LOGIN, ''))) AS login,
                    LTRIM(RTRIM(ISNULL(ORIGEM, ''))) AS origem
                FROM dbo.GR_MAPA_GESTAO_ACESSOS
                WHERE ATIVO = 1
                ORDER BY LOGIN, ORIGEM
            """)).mappings().all()
            return jsonify(
                {
                    "is_admin": True,
                    "origens": _available_origins(),
                    "users": [
                        {
                            "usstamp": str(row.get("usstamp") or "").strip(),
                            "login": str(row.get("login") or "").strip(),
                            "nome": str(row.get("nome") or "").strip(),
                            "admin": bool(row.get("admin")),
                        }
                        for row in users
                    ],
                    "assignments": [
                        {
                            "usstamp": str(row.get("usstamp") or "").strip(),
                            "login": str(row.get("login") or "").strip(),
                            "origem": _normalize_origin_key(row.get("origem")),
                        }
                        for row in assignments
                        if _normalize_origin_key(row.get("origem"))
                    ],
                }
            )

        payload = request.get_json(silent=True) or {}
        access_rows = payload.get("access") if isinstance(payload, dict) else []
        if not isinstance(access_rows, list):
            return jsonify({"error": "Payload invalido."}), 400

        valid_users = {
            str(row.get("usstamp") or "").strip(): {
                "login": str(row.get("login") or "").strip(),
                "nome": str(row.get("nome") or "").strip(),
            }
            for row in db.session.execute(text("""
                SELECT
                    LTRIM(RTRIM(ISNULL(USSTAMP, ''))) AS usstamp,
                    LTRIM(RTRIM(ISNULL(LOGIN, ''))) AS login,
                    LTRIM(RTRIM(ISNULL(NOME, ''))) AS nome
                FROM dbo.US
            """)).mappings().all()
        }
        valid_origins = set(_normalize_origin_key(origin) for origin in _available_origins())
        normalized: list[tuple[str, str, str]] = []
        seen: set[tuple[str, str]] = set()
        for item in access_rows:
            if not isinstance(item, dict):
                continue
            usstamp = str(item.get("usstamp") or "").strip()
            if not usstamp or usstamp not in valid_users:
                continue
            login = str(valid_users[usstamp].get("login") or "").strip()
            for origem in item.get("origens") or []:
                clean_origin = _normalize_origin_key(origem)
                key = (usstamp, clean_origin)
                if clean_origin and clean_origin in valid_origins and key not in seen:
                    normalized.append((usstamp, login, clean_origin))
                    seen.add(key)

        db.session.execute(text("DELETE FROM dbo.GR_MAPA_GESTAO_ACESSOS"))
        for usstamp, login, origem in normalized:
            db.session.execute(
                text("""
                    INSERT INTO dbo.GR_MAPA_GESTAO_ACESSOS
                        (GRMAPACESSOSTAMP, USSTAMP, LOGIN, ORIGEM, ATIVO, DTCRI, USERCRIACAO)
                    VALUES
                        (:stamp, :usstamp, :login, :origem, 1, :dtcri, :usercriacao)
                """),
                {
                    "stamp": uuid.uuid4().hex[:25],
                    "usstamp": usstamp,
                    "login": login,
                    "origem": origem,
                    "dtcri": datetime.now(),
                    "usercriacao": _current_login(),
                },
            )
        db.session.commit()
        return jsonify({"ok": True, "saved": len(normalized)})
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": f"Erro ao gerir acessos: {exc}"}), 500


@bp.route("/api/mapa_gestao_gr/detalhe")
@login_required
def api_mapa_gestao_gr_detalhe():
    familia = str(request.args.get("familia") or "").strip()
    if not familia:
        return jsonify({"error": "Familia obrigatoria."}), 400

    try:
        allowed_origins = _allowed_origins_for_current_user()
        if allowed_origins == []:
            return jsonify({"has_access": False, "rows": [], "total": 0})

        mes_raw = str(request.args.get("mes") or "").strip().lower()
        mes = None
        if mes_raw and mes_raw != "all":
            try:
                mes_val = int(mes_raw)
                if 1 <= mes_val <= 12:
                    mes = mes_val
            except (TypeError, ValueError):
                mes = None
        include_children = str(request.args.get("include_children") or "").strip().lower() in {"1", "true", "yes", "sim"}
        include_sales = familia in {"7", "7.1", "7.1.1"}

        rows: list[dict] = []
        total_sum = 0.0

        if not _is_revenue_ref(familia):
            cost_columns = _master_view_columns("V_CUSTO_ORIGENS")
            where_sql, bind = _cost_where(include_origins=True, include_ccustos=True)
            where_parts = [where_sql]
            values = list(bind["values"])
            if include_children:
                where_parts.append("(LTRIM(RTRIM(ISNULL(FAMILIA, ''))) = ? OR LTRIM(RTRIM(ISNULL(FAMILIA, ''))) LIKE ?)")
                values.extend([familia, f"{familia}.%"])
            else:
                where_parts.append("LTRIM(RTRIM(ISNULL(FAMILIA, ''))) = ?")
                values.append(familia)
            if mes:
                where_parts.append("MONTH(DATA) = ?")
                values.append(mes)
            cost_rows = _master_rows(
                f"""
                SELECT
                    {_column_expr(cost_columns, ["BDADOS"], "origem")},
                    {_column_expr(cost_columns, ["STAMP", "CUSTOSTAMP", "FNSTAMP", "FOSTAMP"], "stamp")},
                    {_column_expr(cost_columns, ["NMDOC", "DOCNOME", "DOCUMENTO", "TIPO"], "documento")},
                    {_column_expr(cost_columns, ["NRDOC", "NDOC", "FNO", "ADOC", "NUMERO"], "numero")},
                    {_column_expr(cost_columns, ["DATA"], "data", "date")},
                    {_column_expr(cost_columns, ["NOME", "FORNECEDOR", "CLIENTE"], "nome")},
                    {_column_expr(cost_columns, ["CCUSTO", "FNCCUSTO"], "ccusto")},
                    {_column_expr(cost_columns, ["FAMILIA"], "familia")},
                    {_column_expr(cost_columns, ["REF", "REFERENCIA"], "referencia")},
                    {_column_expr(cost_columns, ["DESIGN", "DESIGNACAO", "DESCR"], "designacao")},
                    {_column_expr(cost_columns, ["QTT", "QUANTIDADE"], "quantidade", "number")},
                    {_column_expr(cost_columns, ["EPV", "PRECO"], "preco", "number")},
                    {_column_expr(cost_columns, ["TOTAL", "ETILIQUIDO", "ETTILIQ", "VALOR"], "total", "number")}
                FROM dbo.V_CUSTO_ORIGENS
                WHERE {" AND ".join(where_parts)}
                ORDER BY DATA, documento, numero
                """,
                values,
            )
            rows.extend(cost_rows)

        if include_sales:
            sales_columns = _master_view_columns("V_FT_ORIGENS")
            where_sql, bind = _sales_where(include_origins=True, include_ccustos=True)
            where_parts = [where_sql]
            values = list(bind["values"])
            if mes:
                where_parts.append("MONTH(FDATA) = ?")
                values.append(mes)
            sales_rows = _master_rows(
                f"""
                SELECT
                    {_column_expr(sales_columns, ["BDADOS"], "origem")},
                    {_column_expr(sales_columns, ["FTSTAMP", "STAMP"], "stamp")},
                    {_column_expr(sales_columns, ["NMDOC", "DOCUMENTO", "TIPO"], "documento")},
                    {_column_expr(sales_columns, ["FNO", "NDOC", "NUMERO"], "numero")},
                    {_column_expr(sales_columns, ["FDATA"], "data", "date")},
                    {_column_expr(sales_columns, ["NOME", "CLIENTE"], "nome")},
                    {_column_expr(sales_columns, ["CCUSTO_GERAL", "CCUSTO"], "ccusto")},
                    CAST('7.1.1' AS nvarchar(20)) AS familia,
                    {_column_expr(sales_columns, ["REF", "REFERENCIA"], "referencia")},
                    {_column_expr(sales_columns, ["DESIGN", "DESIGNACAO", "DESCR"], "designacao")},
                    {_column_expr(sales_columns, ["QTT", "QUANTIDADE"], "quantidade", "number")},
                    {_column_expr(sales_columns, ["EPV", "PRECO"], "preco", "number")},
                    {_column_expr(sales_columns, ["ETTILIQ"], "total", "number")}
                FROM dbo.V_FT_ORIGENS
                WHERE {" AND ".join(where_parts)}
                ORDER BY FDATA, documento, numero
                """,
                values,
            )
            rows.extend(sales_rows)

        out = []
        for row in rows:
            total = float(_row_get(row, "total") or 0)
            total_sum += total
            data_val = _row_get(row, "data")
            if isinstance(data_val, (datetime, date)):
                data_val = data_val.strftime("%Y-%m-%d")
            elif data_val:
                data_val = str(data_val)[:10]
            out.append(
                {
                    "origem": str(_row_get(row, "origem") or "").strip(),
                    "stamp": str(_row_get(row, "stamp") or "").strip(),
                    "documento": str(_row_get(row, "documento") or "").strip(),
                    "numero": str(_row_get(row, "numero") or "").strip(),
                    "data": data_val or "",
                    "nome": str(_row_get(row, "nome") or "").strip(),
                    "ccusto": str(_row_get(row, "ccusto") or "").strip(),
                    "familia": str(_row_get(row, "familia") or "").strip(),
                    "referencia": str(_row_get(row, "referencia") or "").strip(),
                    "designacao": str(_row_get(row, "designacao") or "").strip(),
                    "quantidade": round(float(_row_get(row, "quantidade") or 0), 4),
                    "preco": round(float(_row_get(row, "preco") or 0), 4),
                    "total": round(total, 2),
                }
            )

        return jsonify({"has_access": True, "rows": out, "total": round(total_sum, 2)})
    except Exception as exc:
        return jsonify({"error": f"Erro ao obter detalhe GR: {exc}"}), 500


@bp.route("/api/mapa_gestao_gr")
@login_required
def api_mapa_gestao_gr():
    try:
        allowed_origins = _allowed_origins_for_current_user()
        if allowed_origins == []:
            return jsonify(
                {
                    "has_access": False,
                    "message": "Nao tem acesso ao Mapa Gestao GR.",
                    "data_inicio": _parse_date_param(request.args.get("data_inicio"), date.today()).isoformat(),
                    "data_fim": _parse_date_param(request.args.get("data_fim"), date.today()).isoformat(),
                    "origens": [],
                    "ccustos": [],
                    "total_geral": 0,
                    "total_custos": 0,
                    "total_proveitos": 0,
                    "resultado": 0,
                    "familias": [],
                    "familias_ignoradas": [],
                    "familias_ignoradas_count": 0,
                    "kpis": {"total_custos": 0, "total_proveitos": 0, "resultado": 0},
                }
            )
        start, end, origens, ccustos = _base_filters()
        family_rows = db.session.execute(text("""
            SELECT
                LTRIM(RTRIM(ISNULL(REF, ''))) AS ref,
                LTRIM(RTRIM(ISNULL(NOME, ''))) AS nome
            FROM V_STFAMI
            WHERE LTRIM(RTRIM(ISNULL(REF, ''))) <> ''
            ORDER BY REF
        """)).mappings().all()
        where_sql, bind = _cost_where(include_origins=True, include_ccustos=True)
        cost_rows = _master_rows(
            f"""
            SELECT
                LTRIM(RTRIM(ISNULL(FAMILIA, ''))) AS familia,
                MONTH(DATA) AS mes,
                SUM(ISNULL(TOTAL, 0)) AS total
            FROM dbo.V_CUSTO_ORIGENS
            WHERE {where_sql}
              AND LTRIM(RTRIM(ISNULL(FAMILIA, ''))) <> ''
            GROUP BY LTRIM(RTRIM(ISNULL(FAMILIA, ''))), MONTH(DATA)
            ORDER BY LTRIM(RTRIM(ISNULL(FAMILIA, ''))), MONTH(DATA)
            """,
            bind["values"],
        )
        sales_where_sql, sales_bind = _sales_where(include_origins=True, include_ccustos=True)
        sales_rows = _master_rows(
            f"""
            SELECT
                MONTH(FDATA) AS mes,
                SUM(ISNULL(ETTILIQ, 0)) AS total
            FROM dbo.V_FT_ORIGENS
            WHERE {sales_where_sql}
            GROUP BY MONTH(FDATA)
            ORDER BY MONTH(FDATA)
            """,
            sales_bind["values"],
        )
    except Exception as exc:
        return jsonify({"error": f"Erro ao obter custos GR: {exc}"}), 500

    families: dict = {}
    for row in family_rows:
        ref = str(_row_get(row, "ref") or "").strip()
        if not ref:
            continue
        node = _ensure_family_node(families, ref)
        node["nome"] = str(_row_get(row, "nome") or "").strip() or ref

    ignored_families: set[str] = set()
    for row in cost_rows:
        ref = str(_row_get(row, "familia") or "").strip()
        if not ref or ref not in families:
            if ref:
                ignored_families.add(ref)
            continue
        try:
            month = int(_row_get(row, "mes") or 0)
        except (TypeError, ValueError):
            month = 0
        value = float(_row_get(row, "total") or 0)
        if not ref or month < 1 or month > 12:
            continue
        parts = ref.split(".")
        while parts:
            current_ref = ".".join(parts)
            node = families.get(current_ref)
            if node is None:
                parts = parts[:-1]
                continue
            node["meses"][month - 1] += value
            node["total"] += value
            parts = parts[:-1]

    for row in sales_rows:
        try:
            month = int(_row_get(row, "mes") or 0)
        except (TypeError, ValueError):
            month = 0
        value = float(_row_get(row, "total") or 0)
        if month < 1 or month > 12:
            continue
        parts = ["7", "1", "1"]
        while parts:
            current_ref = ".".join(parts)
            node = families.get(current_ref)
            if node is not None:
                node["meses"][month - 1] += value
                node["total"] += value
            parts = parts[:-1]

    total_custos = sum(
        float(node.get("total") or 0)
        for node in families.values()
        if int(node.get("nivel") or 1) == 1 and not _is_revenue_ref(str(node.get("ref") or ""))
    )
    total_proveitos = sum(
        float(node.get("total") or 0)
        for node in families.values()
        if int(node.get("nivel") or 1) == 1 and _is_revenue_ref(str(node.get("ref") or ""))
    )
    resultado = total_proveitos - total_custos
    result = []
    for node in sorted(families.values(), key=lambda item: _sort_key(item["ref"])):
        total = float(node.get("total") or 0)
        is_revenue = _is_revenue_ref(str(node.get("ref") or ""))
        result.append(
            {
                "ref": node["ref"],
                "nome": node.get("nome") or node["ref"],
                "nivel": node.get("nivel") or 1,
                "meses": [round(float(value or 0), 2) for value in node["meses"]],
                "total": round(total, 2),
                "percent": None if is_revenue else round((total / total_custos * 100) if total_custos else 0, 2),
                "orc_meses": [0.0] * 12,
                "orc_total": 0.0,
            }
        )

    return jsonify(
        {
            "data_inicio": start.isoformat(),
            "data_fim": end.isoformat(),
            "origens": origens,
            "ccustos": ccustos,
            "total_geral": round(float(total_custos or 0), 2),
            "total_custos": round(float(total_custos or 0), 2),
            "total_proveitos": round(float(total_proveitos or 0), 2),
            "resultado": round(float(resultado or 0), 2),
            "familias": result,
            "familias_ignoradas": sorted(ignored_families)[:50],
            "familias_ignoradas_count": len(ignored_families),
            "kpis": {
                "total_custos": round(float(total_custos or 0), 2),
                "total_proveitos": round(float(total_proveitos or 0), 2),
                "resultado": round(float(resultado or 0), 2),
            },
        }
    )
