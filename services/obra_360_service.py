"""Read-only aggregation layer for the GR360 Hub de Obra 360.

The Hub starts with the synchronised OPC record and only asks PHC for the
sections that the user opens.  It deliberately has no schema side effects.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from threading import Lock
from time import monotonic
from typing import Any, Mapping

from flask import current_app, has_request_context, session
from sqlalchemy import text
import pyodbc

from models import Acessos, db
from services.auth_service import get_table_columns
from services.multiempresa_service import get_current_feid, get_user_entities


ACTIVE_CARD_CODES = {
    "orcamento", "compras", "autos_cliente", "autos_subempreiteiro", "contratos_se",
    "faturas_cliente", "recebimentos", "pagamentos", "bl", "bc", "custos",
    "producao", "anexos",
}
HUB_TAB_SPECS = (
    ("resumo", "Resumo"),
    ("comercial", "Comercial"),
    ("compras", "Compras"),
    ("blbc", "BC/BL"),
    ("autos", "Autos"),
    ("faturacao", "Faturação"),
    ("recebimentos", "Tesouraria"),
    ("custos", "Custos"),
    ("producao", "Produção"),
    ("documentos", "Documentos"),
)
HUB_TAB_CODES = {code for code, _label in HUB_TAB_SPECS}
CARD_TAB_CODES = {
    "orcamento": "comercial", "contrato": "comercial", "adicionais": "comercial",
    "compras": "compras", "bl": "blbc", "bc": "blbc",
    "autos_cliente": "autos", "autos_subempreiteiro": "autos", "contratos_se": "autos",
    "faturas_cliente": "faturacao", "recebimentos": "recebimentos",
    "pagamentos": "recebimentos", "custos": "custos", "producao": "producao",
    "anexos": "documentos",
}
PHC_CACHE_SECONDS = 30
_phc_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_phc_cache_lock = Lock()

CARD_SPECS = (
    ("orcamento", "Orçamento", "Orçamento", "commercial"),
    ("contrato", "Contrato / adjudicado", "Contrato / adjudicado", "commercial"),
    ("adicionais", "Adicionais", "Adicionais", "commercial"),
    ("compras", "Compras", "Compras", "purchases"),
    ("bc", "BC", "BC", "logistics"),
    ("bl", "BL", "BL", "logistics"),
    ("faturas_fornecedor", "Faturas de fornecedor", "Faturas de fornecedor", "purchases"),
    ("autos_cliente", "Autos de cliente", "Autos de cliente", "autos"),
    ("autos_subempreiteiro", "Autos de subempreiteiro", "Autos de subempreiteiro", "autos"),
    ("contratos_se", "Contratos SE", "Contratos SE", "autos"),
    ("faturas_cliente", "Faturas de cliente", "Faturas de cliente", "invoicing"),
    ("fornecedores", "Fornecedores", "Fornecedores", "purchases"),
    ("materiais", "Materiais", "Materiais", "production"),
    ("producao", "Produção", "Produção", "production"),
    ("custos", "Custos", "Custos", "costs"),
    ("proveitos", "Proveitos", "Proveitos", "financial"),
    ("recebimentos", "Recebimentos", "Recebimentos", "financial"),
    ("pagamentos", "Pagamentos", "Pagamentos", "financial"),
    ("anexos", "Anexos", "Anexos", "documents"),
    ("margem", "Margem", "Margem", "financial"),
)
CARD_SPEC_BY_CODE = {item[0]: item for item in CARD_SPECS}


def is_gr360_hub_context(
    config: Mapping[str, Any] | None = None,
    *,
    current_target: str | None = None,
    require_request_context: bool = True,
) -> bool:
    """Return True only for the explicitly configured GR360_CORE context."""
    using_current_app = config is None
    if using_current_app and require_request_context and not has_request_context():
        return False
    config = current_app.config if using_current_app else (config or {})
    expected_target = str(config.get("GR360_HUB_TARGET", "client") or "").strip().lower()
    expected_database = str(config.get("GR360_HUB_EXPECTED_DATABASE", "GR360_CORE") or "").strip().upper()
    database = str(
        config.get("DB_CLIENT_NAME")
        or config.get("GR360_HUB_SOURCE_DATABASE")
        or config.get("GR360_AUDIT_SOURCE_DATABASE")
        or ""
    ).strip().upper()
    if current_target is None and using_current_app:
        resolver = config.get("DB_CURRENT_TARGET_RESOLVER")
        try:
            current_target = resolver() if callable(resolver) else ""
        except Exception:
            current_target = ""
    return bool(
        expected_target
        and expected_database
        and str(current_target or "").strip().lower() == expected_target
        and database == expected_database
    )


def can_consult_opc(user) -> bool:
    if bool(getattr(user, "ADMIN", False)) or bool(getattr(user, "DEV", False)):
        return True
    login = str(getattr(user, "LOGIN", "") or "").strip()
    if not login:
        return False
    row = Acessos.query.filter_by(utilizador=login, tabela="OPC").first()
    return bool(row and getattr(row, "consultar", False))


def ensure_hub_tab_access_schema() -> None:
    """Create the GR360-local access matrix for Hub tabs when needed."""
    db.session.execute(text("""
        IF OBJECT_ID('dbo.OBRA360_ACESSOS', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.OBRA360_ACESSOS (
                OBRA360ACESSOSTAMP varchar(25) NOT NULL
                    CONSTRAINT PK_OBRA360_ACESSOS PRIMARY KEY,
                USSTAMP varchar(25) NOT NULL,
                TAB_CODE varchar(30) NOT NULL,
                ATIVO bit NOT NULL CONSTRAINT DF_OBRA360_ACESSOS_ATIVO DEFAULT (1),
                DTCRI datetime NOT NULL CONSTRAINT DF_OBRA360_ACESSOS_DTCRI DEFAULT (GETDATE()),
                DTALT datetime NOT NULL CONSTRAINT DF_OBRA360_ACESSOS_DTALT DEFAULT (GETDATE()),
                USERALTERACAO varchar(60) NOT NULL CONSTRAINT DF_OBRA360_ACESSOS_USERALT DEFAULT ('')
            );
            CREATE UNIQUE INDEX UX_OBRA360_ACESSOS_USER_TAB
                ON dbo.OBRA360_ACESSOS (USSTAMP, TAB_CODE);
        END
    """))
    db.session.commit()


def hub_tabs_for_user(user) -> set[str]:
    if bool(getattr(user, "ADMIN", False)) or bool(getattr(user, "DEV", False)):
        return set(HUB_TAB_CODES)
    ensure_hub_tab_access_schema()
    userstamp = _text_value(getattr(user, "USSTAMP", ""))
    if not userstamp:
        return set()
    rows = db.session.execute(text("""
        SELECT TAB_CODE, ATIVO
          FROM dbo.OBRA360_ACESSOS
         WHERE USSTAMP = :usstamp
    """), {"usstamp": userstamp}).mappings().all()
    # Existing users keep their current Hub access until an admin saves a matrix for them.
    if not rows:
        return set(HUB_TAB_CODES)
    return {
        _text_value(row.get("TAB_CODE"))
        for row in rows
        if bool(row.get("ATIVO")) and _text_value(row.get("TAB_CODE")) in HUB_TAB_CODES
    }


def can_access_hub_tab(user, tab_code: str) -> bool:
    return str(tab_code or "").strip().lower() in hub_tabs_for_user(user)


def get_hub_tab_access_matrix() -> dict[str, Any]:
    ensure_hub_tab_access_schema()
    users = db.session.execute(text("""
        SELECT USSTAMP, LOGIN, NOME, ADMIN, DEV
          FROM dbo.US
         WHERE LTRIM(RTRIM(ISNULL(LOGIN, ''))) <> ''
         ORDER BY NOME, LOGIN
    """)).mappings().all()
    access_rows = db.session.execute(text("""
        SELECT USSTAMP, TAB_CODE, ATIVO
          FROM dbo.OBRA360_ACESSOS
    """)).mappings().all()
    saved = {}
    for row in access_rows:
        stamp = _text_value(row.get("USSTAMP"))
        saved.setdefault(stamp, set())
        if bool(row.get("ATIVO")):
            saved[stamp].add(_text_value(row.get("TAB_CODE")))
    result = []
    for row in users:
        stamp = _text_value(row.get("USSTAMP"))
        administrator = bool(row.get("ADMIN")) or bool(row.get("DEV"))
        tabs = set(HUB_TAB_CODES) if administrator or stamp not in saved else saved[stamp]
        result.append({
            "usstamp": stamp,
            "login": _text_value(row.get("LOGIN")),
            "nome": _text_value(row.get("NOME")),
            "admin": administrator,
            "tabs": sorted(tab for tab in tabs if tab in HUB_TAB_CODES),
        })
    return {"tabs": [{"code": code, "label": label} for code, label in HUB_TAB_SPECS], "users": result}


def save_hub_tab_access_matrix(users: list[Mapping[str, Any]], changed_by: str) -> None:
    ensure_hub_tab_access_schema()
    known_users = {
        _text_value(row.get("USSTAMP")): bool(row.get("ADMIN")) or bool(row.get("DEV"))
        for row in db.session.execute(text("SELECT USSTAMP, ADMIN, DEV FROM dbo.US")).mappings().all()
    }
    for user in users:
        stamp = _text_value(user.get("usstamp"))
        if not stamp or stamp not in known_users or known_users[stamp]:
            continue
        requested_tabs = {str(tab or "").strip().lower() for tab in (user.get("tabs") or [])}
        requested_tabs &= HUB_TAB_CODES
        db.session.execute(text("DELETE FROM dbo.OBRA360_ACESSOS WHERE USSTAMP = :usstamp"), {"usstamp": stamp})
        for tab_code in requested_tabs:
            db.session.execute(text("""
                INSERT INTO dbo.OBRA360_ACESSOS
                    (OBRA360ACESSOSTAMP, USSTAMP, TAB_CODE, ATIVO, DTCRI, DTALT, USERALTERACAO)
                VALUES (LEFT(REPLACE(CONVERT(varchar(36), NEWID()), '-', ''), 25),
                        :usstamp, :tab_code, 1, GETDATE(), GETDATE(), :changed_by)
            """), {"usstamp": stamp, "tab_code": tab_code, "changed_by": str(changed_by or "")[:60]})
    db.session.commit()


def _text_value(value: Any) -> str:
    return str(value or "").strip()


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _opc_columns() -> set[str]:
    return {str(column).upper() for column in get_table_columns(db.session, "OPC")}


def _column_expr(columns: set[str], name: str, alias: str) -> str:
    if name.upper() not in columns:
        return f"CAST('' AS nvarchar(1)) AS {alias}"
    return f"LTRIM(RTRIM(ISNULL(CAST([{name}] AS nvarchar(240)), ''))) AS {alias}"


def _allowed_sources(user) -> list[dict[str, Any]] | None:
    if bool(getattr(user, "ADMIN", False)) or bool(getattr(user, "DEV", False)):
        return None
    userstamp = _text_value(getattr(user, "USSTAMP", ""))
    entities = get_user_entities(db.session, userstamp) if userstamp else []
    feids: set[int] = set()
    for item in entities:
        try:
            feid = int(item.get("FEID") or 0)
        except (TypeError, ValueError):
            feid = 0
        if feid:
            feids.add(feid)
    if not feids:
        try:
            feids.add(int(get_current_feid()))
        except Exception:
            return []
    placeholders = ", ".join(f":feid_{index}" for index, _ in enumerate(sorted(feids)))
    params = {f"feid_{index}": value for index, value in enumerate(sorted(feids))}
    rows = db.session.execute(text(f"""
        SELECT FEID, LTRIM(RTRIM(ISNULL(NOME, ''))) AS NOME,
               LTRIM(RTRIM(ISNULL(PHC_DB, ''))) AS PHC_DB
          FROM dbo.FE
         WHERE FEID IN ({placeholders})
           AND ISNULL(ATIVA, 1) = 1
    """), params).mappings().all()
    return [dict(row) for row in rows]


def _origin_is_allowed(origin: str, sources: list[dict[str, Any]] | None) -> bool:
    if sources is None:
        return True
    from services.opc_phc_info_service import _origin_phc_db_hint

    normalized_origin = "".join(char for char in _text_value(origin).upper() if char.isalnum())
    origin_db = _origin_phc_db_hint(origin)
    for source in sources:
        source_name = "".join(char for char in _text_value(source.get("NOME")).upper() if char.isalnum())
        source_db = _text_value(source.get("PHC_DB")).upper()
        if origin_db and origin_db == source_db:
            return True
        if source_name and (source_name in normalized_origin or normalized_origin in source_name):
            return True
    return False


def _search_rows(query: str, limit: int = 20) -> list[dict[str, Any]]:
    columns = _opc_columns()
    if not {"OPCSTAMP", "PROCESSO"}.issubset(columns):
        return []
    select_parts = [
        _column_expr(columns, "OPCSTAMP", "opcstamp"),
        _column_expr(columns, "PROCESSO", "processo"),
        _column_expr(columns, "DESCRICAO", "descricao"),
        _column_expr(columns, "NOME", "cliente"),
        _column_expr(columns, "U_ORIGEM", "origem"),
        _column_expr(columns, "DATAI", "data_inicio"),
        _column_expr(columns, "DATAF", "data_fim"),
        _column_expr(columns, "DATAFECHO", "data_fecho"),
    ]
    query_columns = [name for name in ("PROCESSO", "DESCRICAO", "NOME", "U_ORIGEM") if name in columns]
    if not query_columns:
        return []
    where = " OR ".join(f"CAST([{name}] AS nvarchar(240)) LIKE :query" for name in query_columns)
    rows = db.session.execute(text(f"""
        SELECT TOP ({max(1, min(int(limit), 50))}) {", ".join(select_parts)}
          FROM dbo.OPC
         WHERE {where}
         ORDER BY CASE WHEN CAST([PROCESSO] AS nvarchar(240)) = :exact THEN 0 ELSE 1 END,
                  [PROCESSO]
    """), {"query": f"%{query}%", "exact": query}).mappings().all()
    return [{key: _json_value(value) for key, value in dict(row).items()} for row in rows]


def _work_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    closed = bool(_text_value(row.get("data_fecho")))
    return {
        "opcstamp": _text_value(row.get("opcstamp")),
        "codigo": _text_value(row.get("processo")),
        "ccusto": _text_value(row.get("processo")),
        "designacao": _text_value(row.get("descricao")),
        "cliente": _text_value(row.get("cliente")),
        "responsavel": "",
        "empresa": _text_value(row.get("origem")),
        "origem": _text_value(row.get("origem")),
        "estado": "Fechada" if closed else "Em curso",
        "data_inicio": row.get("data_inicio"),
        "data_fim": row.get("data_fim"),
    }


def search_works(query: str, user, limit: int = 12) -> list[dict[str, Any]]:
    clean_query = _text_value(query)
    if len(clean_query) < 2:
        return []
    sources = _allowed_sources(user)
    return [
        _work_payload(row)
        for row in _search_rows(clean_query, limit=limit * 3)
        if _origin_is_allowed(_text_value(row.get("origem")), sources)
    ][:limit]


def resolve_work(code: str, user) -> dict[str, Any]:
    candidates = search_works(code, user, limit=20)
    exact = [item for item in candidates if item["codigo"].upper() == _text_value(code).upper()]
    candidates = exact or candidates
    if not candidates:
        return {"status": "missing", "works": []}
    if len(candidates) > 1:
        return {"status": "ambiguous", "works": candidates}
    return {"status": "ok", "work": candidates[0]}


def _empty_indicator(code: str, title: str) -> dict[str, Any]:
    return {
        "code": code,
        "title": title,
        "value": None,
        "currency": "EUR",
        "status": "sem_dados",
        "source": "Ainda sem dados integrados",
        "updated_at": None,
        "drilldown_available": False,
        "record_count": None,
    }


def overview_for_work(work: Mapping[str, Any]) -> dict[str, Any]:
    indicators = {
        key: _empty_indicator(key, title)
        for key, title in (
            ("adjudicado", "Adjudicado"),
            ("adicionais", "Adicionais"),
            ("orcamento", "Orçamento"),
            ("comprometido", "Comprometido"),
            ("custo_real", "Custo real"),
            ("faturado", "Faturado"),
            ("recebido", "Recebido"),
            ("margem_atual", "Margem atual"),
            ("margem_prevista", "Margem prevista final"),
        )
    }
    return {"work": dict(work), "indicators": indicators, "cards": [_card_shell(item[0]) for item in CARD_SPECS]}


def _card_shell(code: str) -> dict[str, Any]:
    spec = CARD_SPEC_BY_CODE[code]
    active = code in ACTIVE_CARD_CODES
    return {
        "code": code,
        "title": spec[1],
        "section": spec[3],
        "state": "loading" if active else "preparation",
        "status": "parcial" if active else "sem_dados",
        "message": "A carregar dados PHC..." if active else "Em preparação. Ainda sem dados integrados.",
        "value": None,
        "currency": "EUR",
        "record_count": None,
        "source": "PHC" if active else "Ainda sem dados integrados",
        "updated_at": None,
        "drilldown_available": active,
        "open_url": None,
        "rows": [],
    }


def _cached_phc_info(opcstamp: str) -> dict[str, Any]:
    now = monotonic()
    with _phc_cache_lock:
        cached = _phc_cache.get(opcstamp)
        if cached and now - cached[0] < PHC_CACHE_SECONDS:
            return cached[1]
    from services.opc_phc_info_service import get_opc_phc_info

    data = get_opc_phc_info(opcstamp)
    with _phc_cache_lock:
        _phc_cache[opcstamp] = (monotonic(), data)
    return data


def _sum_rows(rows: list[Mapping[str, Any]], field: str) -> float:
    return round(sum(float(row.get(field) or 0) for row in rows), 2)


def _documents_by_stamp(rows: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """PHC returns one aggregation row per VAT rate; the Hub shows documents."""
    documents: dict[str, dict[str, Any]] = {}
    for row in rows:
        item = dict(row)
        stamp = _text_value(item.get("oristamp"))
        if not stamp:
            continue
        current = documents.get(stamp)
        if current is None:
            documents[stamp] = item
            continue
        for field in ("producao", "ajustes", "multas", "adiantamento", "prorata", "ret_garantia", "ret_fim_trabalho", "outras_retencoes", "iva", "total_iva"):
            current[field] = round(float(current.get(field) or 0) + float(item.get(field) or 0), 2)
        current["faturado"] = bool(current.get("faturado") or item.get("faturado"))
    return list(documents.values())


def _management_family_names() -> dict[str, str]:
    """Return the same family labels used by the Management Map."""
    rows = db.session.execute(text("""
        SELECT LTRIM(RTRIM(ISNULL(REF, ''))) AS REF,
               LTRIM(RTRIM(ISNULL(NOME, ''))) AS NOME
          FROM dbo.v_stfami
         WHERE LTRIM(RTRIM(ISNULL(REF, ''))) <> ''
    """)).mappings().all()
    return {
        _text_value(row.get("REF")): _text_value(row.get("NOME"))
        for row in rows
        if _text_value(row.get("REF"))
    }


def _cost_center_candidates(work: Mapping[str, Any]) -> list[str]:
    """Map OPC's global process code to the code used by Management Maps."""
    candidates = [_text_value(work.get("ccusto")), _text_value(work.get("codigo"))]
    try:
        from services.opc_phc_info_service import _phc_process_code

        candidates.append(_phc_process_code(
            _text_value(work.get("codigo")),
            _text_value(work.get("origem")),
        ))
    except Exception:
        pass
    unique: list[str] = []
    for candidate in candidates:
        candidate = _text_value(candidate)
        if candidate and candidate not in unique:
            unique.append(candidate)
    return unique


def _cost_family_rows(work: Mapping[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    """Read cost totals from v_custo, the source of the Management Map.

    An OPC process can have a global prefix while the Management Map stores the
    operational company prefix.  Prefer the OPC code whenever it has entries,
    otherwise use its mapped company variant.  This avoids mixing two works
    that could happen to share the same numeric suffix.
    """
    candidates = _cost_center_candidates(work)
    if not candidates:
        return "", []
    placeholders = ", ".join(f":ccusto_{index}" for index in range(len(candidates)))
    params = {f"ccusto_{index}": value for index, value in enumerate(candidates)}
    rows = db.session.execute(text(f"""
        SELECT
            LTRIM(RTRIM(ISNULL(CCUSTO, ''))) AS CCUSTO,
            LTRIM(RTRIM(ISNULL(FAMILIA, ''))) AS FAMILIA,
            SUM(ISNULL(TOTAL, 0)) AS TOTAL,
            COUNT(1) AS RECORD_COUNT,
            MAX(DATA) AS UPDATED_AT
          FROM dbo.v_custo
         WHERE LTRIM(RTRIM(ISNULL(CCUSTO, ''))) IN ({placeholders})
           AND LTRIM(RTRIM(ISNULL(FAMILIA, ''))) <> ''
           AND LEFT(LTRIM(RTRIM(ISNULL(FAMILIA, ''))), 1) <> '9'
         GROUP BY LTRIM(RTRIM(ISNULL(CCUSTO, ''))),
                  LTRIM(RTRIM(ISNULL(FAMILIA, '')))
    """), params).mappings().all()
    by_cost_center: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        ccusto = _text_value(row.get("CCUSTO"))
        family = _text_value(row.get("FAMILIA"))
        if not ccusto or not family:
            continue
        by_cost_center.setdefault(ccusto, []).append({
            "family": family,
            "total": float(row.get("TOTAL") or 0),
            "record_count": int(row.get("RECORD_COUNT") or 0),
            "updated_at": _json_value(row.get("UPDATED_AT")),
        })
    for candidate in candidates:
        if by_cost_center.get(candidate):
            return candidate, by_cost_center[candidate]
    return "", []


def get_work_cost_groups(work: Mapping[str, Any]) -> dict[str, Any]:
    """Return level-one Management Map families for a single work."""
    ccusto, rows = _cost_family_rows(work)
    family_names = _management_family_names()
    groups: dict[str, dict[str, Any]] = {}
    for row in rows:
        family = _text_value(row.get("family"))
        major = family.split(".", 1)[0]
        if len(major) != 1 or not major.isdigit() or major == "9":
            continue
        group = groups.setdefault(major, {
            "family": major,
            "title": f"{major} · {family_names.get(major) or 'Família de custos'}",
            "value": 0.0,
            "record_count": 0,
            "updated_at": None,
        })
        group["value"] += float(row.get("total") or 0)
        group["record_count"] += int(row.get("record_count") or 0)
        current_updated = group.get("updated_at")
        row_updated = row.get("updated_at")
        if row_updated and (not current_updated or str(row_updated) > str(current_updated)):
            group["updated_at"] = row_updated
    result = []
    for group in groups.values():
        group["value"] = round(float(group["value"] or 0), 2)
        group.update({
            "state": "available",
            "status": "confirmado",
            "message": "Dados confirmados.",
            "currency": "EUR",
            "source": "Mapa de Gestão / v_custo",
            "drilldown_available": True,
        })
        result.append(group)
    result.sort(key=lambda group: int(group["family"]))
    return {
        "ccusto": ccusto,
        "groups": result,
        "total": round(sum(group["value"] for group in result), 2),
        "record_count": sum(group["record_count"] for group in result),
        "updated_at": max((group.get("updated_at") for group in result if group.get("updated_at")), default=None),
    }


def get_work_cost_subgroups(work: Mapping[str, Any], family: str) -> dict[str, Any]:
    """Aggregate direct subgroups for a level-one cost family."""
    major = _text_value(family)
    if len(major) != 1 or not major.isdigit() or major == "9":
        raise ValueError("Família de custo inválida.")
    ccusto, rows = _cost_family_rows(work)
    family_names = _management_family_names()
    groups: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = _text_value(row.get("family"))
        parts = value.split(".")
        if parts[0] != major:
            continue
        subgroup = ".".join(parts[:2]) if len(parts) > 1 else major
        group = groups.setdefault(subgroup, {
            "family": subgroup,
            "title": f"{subgroup} · {family_names.get(subgroup) or family_names.get(major) or 'Sem designação'}",
            "total": 0.0,
            "record_count": 0,
            "updated_at": None,
        })
        group["total"] += float(row.get("total") or 0)
        group["record_count"] += int(row.get("record_count") or 0)
        updated = row.get("updated_at")
        if updated and (not group["updated_at"] or str(updated) > str(group["updated_at"])):
            group["updated_at"] = updated
    result = []
    for group in groups.values():
        group["total"] = round(float(group["total"] or 0), 2)
        result.append(group)
    result.sort(key=lambda group: [int(piece) if piece.isdigit() else piece for piece in group["family"].split(".")])
    return {"ccusto": ccusto, "family": major, "subgroups": result}


def get_work_cost_lines(work: Mapping[str, Any], family: str) -> dict[str, Any]:
    """Return the individual Management Map movements for a cost subgroup."""
    requested_family = _text_value(family)
    if not requested_family or any(not piece.isdigit() for piece in requested_family.split(".")):
        raise ValueError("Subgrupo de custo inválido.")
    ccusto, _ = _cost_family_rows(work)
    if not ccusto:
        return {"ccusto": "", "family": requested_family, "lines": [], "total": 0.0}
    rows = db.session.execute(text("""
        SELECT
            ORIGEM,
            STAMP,
            NMDOC,
            NRDOC,
            DATA,
            NOME,
            CCUSTO,
            FAMILIA,
            REF,
            DESIGN,
            QTT,
            EPV,
            TOTAL,
            CABSTAMP
          FROM dbo.v_custo
         WHERE LTRIM(RTRIM(ISNULL(CCUSTO, ''))) = :ccusto
           AND (LTRIM(RTRIM(ISNULL(FAMILIA, ''))) = :family
                OR LTRIM(RTRIM(ISNULL(FAMILIA, ''))) LIKE :family_like)
         ORDER BY DATA, NMDOC, NRDOC, STAMP
    """), {"ccusto": ccusto, "family": requested_family, "family_like": f"{requested_family}.%"}).mappings().all()
    lines = []
    total = 0.0
    for row in rows:
        value = float(row.get("TOTAL") or 0)
        total += value
        lines.append({
            "origin": _text_value(row.get("ORIGEM")),
            "stamp": _text_value(row.get("STAMP")),
            "document": _text_value(row.get("NMDOC")),
            "number": _text_value(row.get("NRDOC")),
            "date": _json_value(row.get("DATA")),
            "supplier": _text_value(row.get("NOME")),
            "ccusto": _text_value(row.get("CCUSTO")),
            "family": _text_value(row.get("FAMILIA")),
            "reference": _text_value(row.get("REF")),
            "designation": _text_value(row.get("DESIGN")),
            "quantity": float(row.get("QTT") or 0),
            "unit_price": float(row.get("EPV") or 0),
            "total": round(value, 2),
            "cabstamp": _text_value(row.get("CABSTAMP")),
        })
    return {"ccusto": ccusto, "family": requested_family, "lines": lines, "total": round(total, 2)}


def _master_rows(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    """Read planning data from the shared HSOLS_MASTER source."""
    from modules.gr_management_map.routes import _hsols_master_conn_str

    with pyodbc.connect(_hsols_master_conn_str(), timeout=10) as connection:
        cursor = connection.cursor()
        cursor.execute(sql, *params)
        columns = [column[0] for column in cursor.description or []]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _production_process_candidates(work: Mapping[str, Any]) -> list[str]:
    candidates = [_text_value(work.get("codigo")), _text_value(work.get("ccusto"))]
    try:
        from services.opc_phc_info_service import _phc_process_code

        candidates.append(_phc_process_code(
            _text_value(work.get("codigo")),
            _text_value(work.get("origem")),
        ))
    except Exception:
        pass
    unique: list[str] = []
    for candidate in candidates:
        candidate = candidate.upper()
        if candidate and candidate not in unique:
            unique.append(candidate)
    return unique


def get_work_production_assignments(work: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return the planning assignments for a work with their execution state."""
    processes = _production_process_candidates(work)
    if not processes:
        return []
    placeholders = ", ".join("?" for _ in processes)
    rows = _master_rows(f"""
        SELECT
            p.u_planostamp AS plan_stamp,
            LTRIM(RTRIM(ISNULL(p.processo, ''))) AS processo,
            CAST(p.data AS date) AS data,
            LTRIM(RTRIM(ISNULL(p.fref, ''))) AS equipa_codigo,
            LTRIM(RTRIM(ISNULL(f.nmfref, ''))) AS equipa,
            COUNT(am.u_amstamp) AS intervencoes,
            SUM(CASE WHEN am.u_amstamp IS NOT NULL AND ISNULL(am.fechado, 0) = 0 THEN 1 ELSE 0 END) AS intervencoes_abertas,
            MAX(am.usrdata) AS updated_at
          FROM dbo.u_plano p
          LEFT JOIN dbo.fref f ON f.fref = p.fref
          LEFT JOIN dbo.u_am am ON am.planostamp = p.u_planostamp
         WHERE UPPER(LTRIM(RTRIM(ISNULL(p.processo, '')))) IN ({placeholders})
         GROUP BY p.u_planostamp, p.processo, p.data, p.fref, f.nmfref
         ORDER BY CAST(p.data AS date) DESC, p.u_planostamp DESC
    """, tuple(processes))
    assignments = []
    for row in rows:
        interventions = int(row.get("intervencoes") or 0)
        open_interventions = int(row.get("intervencoes_abertas") or 0)
        if not interventions:
            status = "planeada"
            state_label = "Planeada"
        elif open_interventions:
            status = "em_execucao"
            state_label = "Em execução"
        else:
            status = "concluida"
            state_label = "Concluída"
        assignments.append({
            "plan_stamp": _text_value(row.get("plan_stamp")),
            "processo": _text_value(row.get("processo")),
            "date": _json_value(row.get("data")),
            "team_code": _text_value(row.get("equipa_codigo")),
            "team": _text_value(row.get("equipa")) or "Equipa por definir",
            "status": status,
            "status_label": state_label,
            "intervention_count": interventions,
            "updated_at": _json_value(row.get("updated_at")),
        })
    return assignments


def get_work_production_detail(work: Mapping[str, Any], plan_stamp: str) -> dict[str, Any]:
    """Return recorded interventions and their actual team members for a plan."""
    stamp = _text_value(plan_stamp)
    if not stamp:
        raise ValueError("Marcação de produção inválida.")
    processes = _production_process_candidates(work)
    if not processes:
        return {"assignment": {}, "interventions": []}
    placeholders = ", ".join("?" for _ in processes)
    assignment_rows = _master_rows(f"""
        SELECT TOP 1
            p.u_planostamp AS plan_stamp,
            LTRIM(RTRIM(ISNULL(p.processo, ''))) AS processo,
            CAST(p.data AS date) AS data,
            LTRIM(RTRIM(ISNULL(p.fref, ''))) AS team_code,
            LTRIM(RTRIM(ISNULL(f.nmfref, ''))) AS team
          FROM dbo.u_plano p
          LEFT JOIN dbo.fref f ON f.fref = p.fref
         WHERE p.u_planostamp = ?
           AND UPPER(LTRIM(RTRIM(ISNULL(p.processo, '')))) IN ({placeholders})
    """, tuple([stamp, *processes]))
    if not assignment_rows:
        raise ValueError("Marcação de produção não encontrada para esta obra.")
    assignment_row = assignment_rows[0]
    intervention_rows = _master_rows("""
        SELECT
            am.u_amstamp AS intervention_stamp,
            CAST(am.data AS date) AS data,
            LTRIM(RTRIM(ISNULL(CONVERT(nvarchar(max), am.dgeral), ''))) AS descricao,
            LTRIM(RTRIM(ISNULL(CONVERT(nvarchar(max), am.acabamento), ''))) AS acabamento,
            LTRIM(RTRIM(ISNULL(CONVERT(nvarchar(max), am.obs), ''))) AS observacoes,
            ISNULL(am.qtt, 0) AS quantidade,
            ISNULL(am.kgferro, 0) AS kg_ferro,
            ISNULL(am.m2serragem, 0) AS m2_serragem,
            ISNULL(am.m3betao, 0) AS m3_betao,
            ISNULL(am.fechado, 0) AS fechado,
            ISNULL(am.confirmado, 0) AS confirmado
          FROM dbo.u_am am
         WHERE am.planostamp = ?
         ORDER BY am.litem, am.u_amstamp
    """, (stamp,))
    interventions = []
    for intervention in intervention_rows:
        intervention_stamp = _text_value(intervention.get("intervention_stamp"))
        members = _master_rows("""
            SELECT
                LTRIM(RTRIM(ISNULL(CONVERT(nvarchar(max), nome), ''))) AS nome,
                no,
                ISNULL(qtt, 0) AS quantidade,
                ISNULL(presente, 0) AS presente,
                ISNULL(disponivel, 0) AS disponivel
              FROM dbo.u_aml
             WHERE u_amstamp = ?
             ORDER BY LTRIM(RTRIM(ISNULL(nome, ''))), no
        """, (intervention_stamp,))
        interventions.append({
            "stamp": intervention_stamp,
            "date": _json_value(intervention.get("data")),
            "description": _text_value(intervention.get("descricao")),
            "finish": _text_value(intervention.get("acabamento")),
            "notes": _text_value(intervention.get("observacoes")),
            "quantity": float(intervention.get("quantidade") or 0),
            "kg_ferro": float(intervention.get("kg_ferro") or 0),
            "m2_serragem": float(intervention.get("m2_serragem") or 0),
            "m3_betao": float(intervention.get("m3_betao") or 0),
            "status": "Concluída" if bool(intervention.get("fechado")) else "Em execução",
            "members": [{
                "name": _text_value(member.get("nome")),
                "number": _text_value(member.get("no")),
                "quantity": float(member.get("quantidade") or 0),
                "kg_ferro": float(member.get("kg_ferro") or 0),
                "m2_serragem": float(member.get("m2_serragem") or 0),
                "present": bool(member.get("presente")),
                "available": bool(member.get("disponivel")),
            } for member in members],
        })
    return {
        "assignment": {
            "plan_stamp": _text_value(assignment_row.get("plan_stamp")),
            "processo": _text_value(assignment_row.get("processo")),
            "date": _json_value(assignment_row.get("data")),
            "team": _text_value(assignment_row.get("team")) or "Equipa por definir",
            "team_code": _text_value(assignment_row.get("team_code")),
        },
        "interventions": interventions,
    }


def card_data(work: Mapping[str, Any], code: str, form_url: str, user=None) -> dict[str, Any]:
    if code not in CARD_SPEC_BY_CODE:
        raise KeyError(code)
    card = _card_shell(code)
    if code not in ACTIVE_CARD_CODES:
        return card
    try:
        if code == "custos":
            costs = get_work_cost_groups(work)
            card.update({
                "state": "available",
                "status": "confirmado",
                "message": "Dados confirmados.",
                "value": costs["total"],
                "record_count": costs["record_count"],
                "source": "Mapa de Gestão / v_custo",
                "updated_at": costs["updated_at"],
                "groups": costs["groups"],
                "rows": [],
            })
            return card
        if code == "producao":
            assignments = get_work_production_assignments(work)
            card.update({
                "state": "available",
                "status": "confirmado",
                "message": "Marcações de produção do planeamento.",
                "value": None,
                "record_count": len(assignments),
                "source": "Planeamento / Equipas e intervenções",
                "updated_at": max((item.get("updated_at") for item in assignments if item.get("updated_at")), default=None),
                "assignments": assignments,
                "rows": [],
            })
            return card
        if code == "anexos":
            from services.opc_phc_info_service import get_opc_attachments

            documents = get_opc_attachments(_text_value(work.get("opcstamp")))
            rows = list(documents.get("attachments") or [])
            source_name = _text_value((documents.get("source") or {}).get("name")) or "PHC"
            card.update({
                "state": "available",
                "status": "confirmado",
                "message": "Anexos associados à ficha da obra no PHC.",
                "value": None,
                "record_count": len(rows),
                "source": f"PHC / Anexos da obra · {source_name}",
                "display_mode": "count",
                "rows": rows,
            })
            return card
        data = _cached_phc_info(_text_value(work.get("opcstamp")))
        source_name = _text_value((data.get("fonte") or {}).get("nome")) or "PHC"
        if code == "orcamento":
            rows = list(data.get("orcamentos") or [])
            value = _sum_rows(rows, "total_iva")
            label = "PHC / Dossiers de orçamento"
        elif code == "autos_cliente":
            rows = _documents_by_stamp(list(data.get("autos") or []))
            value = _sum_rows(rows, "total_iva")
            label = "PHC / Autos de cliente"
        elif code == "autos_subempreiteiro":
            rows = list(data.get("autos_subempreiteiro") or [])
            value = _sum_rows(rows, "total")
            label = "PHC / Situation Travaux ST"
        elif code == "contratos_se":
            if user is None:
                raise RuntimeError("Utilizador não indicado para consultar contratos de subempreitada.")
            from modules.gr_subcontractor_measurements.service import list_contracts

            source_feid = int((data.get("fonte") or {}).get("feid") or 0)
            process = _text_value((data.get("obra") or {}).get("phc_processo"))
            contracts = list_contracts({"feid": source_feid, "ccusto": process, "only_open": "0"}, user)
            rows = [{
                "oristamp": _text_value(item.get("bostamp")),
                "descricao": f"{_text_value(item.get('doc_name'))} nº {_text_value(item.get('number'))}",
                "data": _text_value(item.get("date")),
                "processo": _text_value(item.get("process")),
                "fornecedor": _text_value(item.get("supplier_name")),
                "ccusto": _text_value(item.get("cost_center")),
                "total": float(item.get("contract_value") or 0),
                "executado": float(item.get("executed_value") or 0),
                "autos": int(item.get("auto_count") or 0),
                "estado": "Fechado" if bool(item.get("closed")) else "Em curso",
            } for item in contracts.get("rows") or []]
            value = _sum_rows(rows, "total")
            label = "PHC / Contratos de subempreitada"
        elif code == "compras":
            rows = list(data.get("compras") or [])
            value = _sum_rows(rows, "total")
            label = "PHC / Compras de fornecedor (FO, FO2 e FOT)"
        elif code == "recebimentos":
            rows = list(data.get("recebimentos") or [])
            value = _sum_rows(rows, "total")
            label = "PHC / Recibos (RE, RL e CC)"
        elif code == "pagamentos":
            rows = list(data.get("pagamentos") or [])
            value = _sum_rows(rows, "total")
            label = "PHC / Pagamentos (PO, PL e FC)"
        elif code in {"bl", "bc"}:
            rows = [row for row in list(data.get("logistics") or []) if row.get("kind") == code]
            value = _sum_rows(rows, "total")
            label = "PHC / Bons de livraison de fornecedor" if code == "bl" else "PHC / Bons de commande de fornecedor"
        else:
            rows = list(data.get("faturas_cliente") or [])
            value = _sum_rows(rows, "total")
            label = "PHC / FT, FT2 e FTT emitidos"
        source_feid = int((data.get("fonte") or {}).get("feid") or 0)
        normalized_rows = []
        for row in rows:
            item = dict(row)
            if source_feid:
                item["source_feid"] = source_feid
            normalized_rows.append(item)
        card.update({
            "state": "available",
            "status": "confirmado",
            "message": "Dados confirmados.",
            "value": value,
            "record_count": len(rows),
            "source": f"{label} · {source_name}",
            "open_url": None,
            "rows": normalized_rows,
        })
        return card
    except Exception as exc:
        current_app.logger.exception("Erro ao carregar card Obra 360 %s", code)
        card.update({
            "state": "error",
            "status": "parcial",
            "message": "Não foi possível atualizar este card agora.",
            "error": str(exc),
        })
        return card


def add_recent_work(work: Mapping[str, Any]) -> None:
    recent = [item for item in (session.get("obra360_recent") or []) if item.get("opcstamp") != work.get("opcstamp")]
    recent.insert(0, {key: work.get(key) for key in ("opcstamp", "codigo", "ccusto", "designacao", "cliente", "estado", "empresa")})
    session["obra360_recent"] = recent[:6]


def recent_works(user) -> list[dict[str, Any]]:
    sources = _allowed_sources(user)
    return [
        item for item in (session.get("obra360_recent") or [])
        if _origin_is_allowed(_text_value(item.get("empresa")), sources)
    ]
