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

from models import Acessos, db
from services.auth_service import get_table_columns
from services.multiempresa_service import get_current_feid, get_user_entities


ACTIVE_CARD_CODES = {"orcamento", "autos_cliente", "faturas_cliente", "bl", "bc"}
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


def card_data(work: Mapping[str, Any], code: str, form_url: str) -> dict[str, Any]:
    if code not in CARD_SPEC_BY_CODE:
        raise KeyError(code)
    card = _card_shell(code)
    if code not in ACTIVE_CARD_CODES:
        return card
    try:
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
        elif code in {"bl", "bc"}:
            rows = [row for row in list(data.get("logistics") or []) if row.get("kind") == code]
            value = _sum_rows(rows, "total")
            label = "PHC / Bons de livraison de fornecedor" if code == "bl" else "PHC / Bons de commande de fornecedor"
        else:
            rows = [row for row in list(data.get("autos") or []) if row.get("faturado")]
            value = float(data.get("autos_total_faturado") or 0)
            label = "PHC / FT e FT2 emitidos"
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
