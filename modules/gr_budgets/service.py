from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import re
from typing import Any
import unicodedata

import pyodbc
from flask import render_template

from modules.gr_subcontractor_measurements.service import (
    PHC_ZERO_DATE,
    SubcontractorMeasurementsError,
    SubcontractorMeasurementsNotFoundError,
    SubcontractorMeasurementsValidationError,
    _company_for_user,
    _client_conn_str,
    _currency_code,
    _date_iso,
    _decimal,
    _fetch_rows,
    _money,
    _number_value,
    _new_stamp,
    _phc_columns,
    _phc_conn_str,
    _phc_insert,
    _phc_tax_rates,
    _phc_value,
    _qty,
    _text_value,
    _user_inis,
    list_companies_for_user,
)


MAX_RESULTS = 300
DEFAULT_SERIES_NAME = "Devis"
CLIENT_BUDGET_SERIES = (
    "devis",
    "etude et execution",
    "devis perdu",
)
INTERSOL_RESTRICTED_BUDGET_NDOS = (115, 122)
INTERSOL_OWN_BUDGET_SALESPERSONS = frozenset({10, 11, 12, 13, 14})
INTERSOL_AGENCY_BUDGET_SALESPERSONS = {
    20: ("INTERSOL-ALSACE",),
    21: ("INTERSOL-LORRAINE",),
    22: ("INTERSOL-LORRAINE", "INTERSOL-CHAMPAGNE"),
}
_APP_ROOT = Path(__file__).resolve().parents[2]
_COMPANY_LOGO_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".webp"})


class BudgetsError(SubcontractorMeasurementsError):
    """Erro funcional do ecrã de orçamentos."""


class BudgetsValidationError(SubcontractorMeasurementsValidationError, BudgetsError):
    pass


class BudgetsNotFoundError(SubcontractorMeasurementsNotFoundError, BudgetsError):
    pass


class BudgetsConflictError(BudgetsError):
    status_code = 409


class BudgetsCreditLimitError(BudgetsValidationError):
    status_code = 422

    def __init__(self, message: str, credit: dict[str, Any]):
        super().__init__(message)
        self.credit = credit


def _company_logo_path(
    festamp: Any,
    configured_path: Any,
    *,
    app_root: Path | None = None,
) -> str:
    """Resolve a logo owned by this FE record, never one from another FE folder."""
    root = (app_root or _APP_ROOT).resolve()
    storage_root = (root / "storage" / "fe_logos").resolve()
    clean_festamp = _text_value(festamp)
    company_dir = (storage_root / clean_festamp).resolve() if clean_festamp else None
    if company_dir is not None and not company_dir.is_relative_to(storage_root):
        company_dir = None

    configured = _text_value(configured_path).replace("\\", "/")
    if configured:
        configured_file = Path(configured)
        if not configured_file.is_absolute():
            configured_file = root / configured_file
        configured_file = configured_file.resolve()
        belongs_to_company = company_dir is not None and configured_file.is_relative_to(company_dir)
        outside_managed_storage = not configured_file.is_relative_to(storage_root)
        if (
            configured_file.is_file()
            and configured_file.suffix.casefold() in _COMPANY_LOGO_EXTENSIONS
            and (belongs_to_company or outside_managed_storage)
        ):
            return str(configured_file)

    # Recover from a stale/wrong LOGOTIPO_PATH by looking only inside the
    # directory keyed by this FE.FESTAMP. No cross-company fallback is allowed.
    if company_dir is not None and company_dir.is_dir():
        candidates = [
            path
            for path in company_dir.iterdir()
            if path.is_file() and path.suffix.casefold() in _COMPANY_LOGO_EXTENSIONS
        ]
        if candidates:
            return str(max(candidates, key=lambda path: path.stat().st_mtime_ns).resolve())
    return ""


def _company_with_print_settings(company: dict[str, Any]) -> dict[str, Any]:
    """Add print assets stored in the selected application's FE record."""
    enriched = dict(company or {})
    try:
        with pyodbc.connect(_client_conn_str(), timeout=10) as conn:
            cursor = conn.cursor()
            columns = _phc_columns(cursor, "FE")
            if "logotipo_path" not in columns:
                return enriched
            rows = _fetch_rows(
                cursor,
                """
                SELECT TOP 1
                    LTRIM(RTRIM(ISNULL(FESTAMP, ''))) AS FESTAMP,
                    LTRIM(RTRIM(ISNULL(LOGOTIPO_PATH, ''))) AS LOGOTIPO_PATH
                FROM dbo.FE
                WHERE FEID = ?
                """,
                (int(enriched.get("feid") or 0),),
            )
        if rows:
            enriched["festamp"] = _text_value(rows[0].get("FESTAMP"))
            enriched["logo_path"] = _company_logo_path(
                enriched["festamp"],
                rows[0].get("LOGOTIPO_PATH"),
            )
    except Exception:
        # A falta de logótipo não deve impedir a emissão do documento.
        enriched["logo_path"] = ""
    return enriched


def _bool_value(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "sim", "yes", "y"}
    return bool(value)


def _budget_is_in_preparation(row: dict[str, Any]) -> bool:
    return not any(
        _bool_value(row.get(field))
        for field in ("APROVADO", "FECHADA", "ADJUDICADO", "ANULADO")
    )


def _budget_can_be_edited(row: dict[str, Any]) -> bool:
    """Approved budgets may be reopened; terminal business states may not."""
    return not any(
        _bool_value(row.get(field))
        for field in ("FECHADA", "ADJUDICADO", "ANULADO")
    )


def _business_date_iso(value: Any) -> str:
    parsed = value.date() if isinstance(value, datetime) else value
    if isinstance(parsed, date) and parsed.year <= 1900:
        return ""
    return _date_iso(value)


def _revision_token(date_value: Any, time_value: Any) -> str:
    date_part = _date_iso(date_value)
    time_part = _text_value(time_value)
    return f"{date_part}|{time_part}" if date_part or time_part else ""


def _percent(value: Any) -> float:
    return float(_decimal(value).quantize(Decimal("0.01")))


def _write_money(value: Any) -> Decimal:
    return _decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _write_oci_purchase_price(row: dict[str, Any]) -> Decimal:
    """Prefer the normalized text still visible in the OCI input.

    Keeping this second representation prevents a stale numeric value in the
    browser state from silently replacing the price the user just entered.
    Older clients do not send it and continue to use ``purchase_price``.
    """
    visible_value = row.get("purchase_price_text")
    if visible_value is not None and _text_value(visible_value):
        return _write_money(visible_value)
    return _write_money(row.get("purchase_price"))


def _item_path(value: Any) -> tuple[tuple[int, int, str], ...]:
    label = _text_value(value).strip()
    if not label:
        return ((1, 0, ""),)
    path: list[tuple[int, int, str]] = []
    for segment in label.split("."):
        token = segment.strip()
        match = re.match(r"^(\d+)(.*)$", token)
        if match:
            path.append((0, int(match.group(1)), match.group(2).strip().casefold()))
        else:
            path.append((1, 0, token.casefold()))
    return tuple(path)


def _line_item_sort_key(line: dict[str, Any]) -> tuple[Any, ...]:
    label = line.get("item_label") if line.get("item_label") not in (None, "") else line.get("item")
    return (
        _item_path(label),
        _number_value(line.get("order")),
        _text_value(line.get("bistamp")),
    )


def _optional_column(
    columns: set[str], table_alias: str, column: str, result_alias: str, default_sql: str = "NULL"
) -> str:
    if column.lower() in columns:
        return f"{table_alias}.[{column}] AS [{result_alias}]"
    return f"{default_sql} AS [{result_alias}]"


def _optional_first_column(
    columns: set[str], table_alias: str, candidates: tuple[str, ...], result_alias: str, default_sql: str = "NULL"
) -> str:
    for column in candidates:
        if column.lower() in columns:
            return f"{table_alias}.[{column}] AS [{result_alias}]"
    return f"{default_sql} AS [{result_alias}]"


def _uses_portuguese_component_designations(company: dict[str, Any]) -> bool:
    """Betaoconcept keeps the component catalogue in PHC's Portuguese descriptions."""
    database_key = _series_name_key(company.get("phc_db")).replace(" ", "")
    company_key = _series_name_key(company.get("name")).replace(" ", "")
    return database_key == "hsols_pt" or "betaoconcept" in company_key


def _article_designation_expression(
    company: dict[str, Any],
    columns: set[str],
    table_alias: str = "S",
    fallback_sql: str | None = None,
) -> str:
    """Return the PHC article designation required by the selected company.

    PHC stores article translations in five LANGn/LANGDESn pairs on ST.  Only
    Betaoconcept must force Portuguese here; every other company keeps the
    standard ST.DESIGN behaviour. Missing columns or translations always fall
    back to the supplied designation.
    """
    fallback = fallback_sql or f"{table_alias}.[DESIGN]"
    if not _uses_portuguese_component_designations(company):
        return fallback

    language_pairs = [
        (f"LANG{index}", f"LANGDES{index}")
        for index in range(1, 6)
        if f"lang{index}" in columns and f"langdes{index}" in columns
    ]
    if not language_pairs:
        return fallback

    portuguese_cases = "\n".join(
        f"""WHEN (
                        UPPER(LTRIM(RTRIM(ISNULL({table_alias}.[{language_column}], ''))))
                            COLLATE Latin1_General_CI_AI LIKE 'PORTUG%'
                        OR REPLACE(REPLACE(
                            UPPER(LTRIM(RTRIM(ISNULL({table_alias}.[{language_column}], '')))),
                            '-', ''), '_', '') COLLATE Latin1_General_CI_AI IN ('PT', 'PTPT')
                    )
                    THEN NULLIF(LTRIM(RTRIM(ISNULL({table_alias}.[{designation_column}], ''))), '')"""
        for language_column, designation_column in language_pairs
    )
    return f"COALESCE(CASE\n{portuguese_cases}\nEND, {fallback})"


def _oci_designation_fallback(columns: set[str], table_alias: str = "O") -> str:
    if "u_design" in columns:
        return (
            f"COALESCE(NULLIF(LTRIM(RTRIM(ISNULL({table_alias}.[U_DESIGN], ''))), ''), "
            f"{table_alias}.[DESIGN])"
        )
    return f"{table_alias}.[DESIGN]"


def _e1_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": _text_value(row.get("COMPANY_NAME")),
        "address": _text_value(row.get("ADDRESS")),
        "postal_code": _text_value(row.get("POSTAL_CODE")),
        "city": _text_value(row.get("CITY")),
        "country": _text_value(row.get("COUNTRY")),
        "vat_number": _text_value(row.get("VAT_NUMBER")),
        "phone": _text_value(row.get("PHONE")),
        "email": _text_value(row.get("EMAIL")),
        "siret": _text_value(row.get("SIRET")),
        "capital": _text_value(row.get("CAPITAL")),
    }


def _load_e1_company(cursor) -> dict[str, Any]:
    columns = _phc_columns(cursor, "E1")
    if not columns:
        raise BudgetsError("A tabela E1 não existe na base PHC desta empresa.")
    order_parts = []
    if "estab" in columns:
        order_parts.append("ISNULL(E1.ESTAB, 0)")
    if "e1stamp" in columns:
        order_parts.append("E1.E1STAMP")
    order_sql = "ORDER BY " + ", ".join(order_parts) if order_parts else ""
    rows = _fetch_rows(
        cursor,
        f"""
        SELECT TOP 1
            {_optional_first_column(columns, 'E1', ('NOMECOMP', 'NOME'), 'COMPANY_NAME', "''")},
            {_optional_first_column(columns, 'E1', ('MORADA',), 'ADDRESS', "''")},
            {_optional_first_column(columns, 'E1', ('CODPOST',), 'POSTAL_CODE', "''")},
            {_optional_first_column(columns, 'E1', ('LOCAL',), 'CITY', "''")},
            {_optional_first_column(columns, 'E1', ('CODPAIS', 'PAIS'), 'COUNTRY', "''")},
            {_optional_first_column(columns, 'E1', ('NCONT',), 'VAT_NUMBER', "''")},
            {_optional_first_column(columns, 'E1', ('TELEFONE', 'TELEF', 'TEL'), 'PHONE', "''")},
            {_optional_first_column(columns, 'E1', ('EMAIL', 'MAIL'), 'EMAIL', "''")},
            {_optional_first_column(columns, 'E1', ('SIRET', 'CONSREG', 'U_SIRET'), 'SIRET', "''")},
            {_optional_first_column(columns, 'E1', ('ECAPSOCIAL', 'CAPITAL', 'CAPSOC', 'CAPSOCIAL', 'U_CAPITAL'), 'CAPITAL', "''")}
        FROM dbo.E1 E1
        {order_sql}
        """,
        (),
    )
    if not rows:
        raise BudgetsError("A tabela E1 não tem a ficha da empresa configurada.")
    return _e1_payload(rows[0])


def _pick_default_series(rows: list[dict[str, Any]]) -> int:
    for row in rows:
        if _text_value(row.get("name")).casefold() == DEFAULT_SERIES_NAME.casefold():
            return int(row.get("ndos") or 0)
    return int(rows[0].get("ndos") or 0) if rows else 0


def _series_name_key(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", _text_value(value))
    without_accents = "".join(character for character in normalized if not unicodedata.combining(character))
    return " ".join(without_accents.casefold().split())


def _intersol_budget_visibility_predicate(
    salesperson_number: Any,
    table_alias: str = "B",
) -> tuple[str, tuple[Any, ...]]:
    alias = table_alias if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", table_alias or "") else "B"
    salesperson = int(_number_value(salesperson_number))
    scope_sql = ""
    scope_params: tuple[Any, ...] = ()

    if salesperson in INTERSOL_OWN_BUDGET_SALESPERSONS:
        scope_sql = f"{alias}.VENDEDOR = ?"
        scope_params = (salesperson,)
    elif salesperson in INTERSOL_AGENCY_BUDGET_SALESPERSONS:
        agencies = INTERSOL_AGENCY_BUDGET_SALESPERSONS[salesperson]
        placeholders = ", ".join("?" for _ in agencies)
        scope_sql = f"{alias}.MAQUINA IN ({placeholders})"
        scope_params = tuple(agencies)

    if not scope_sql:
        return "1 = 1", ()

    ndos_placeholders = ", ".join("?" for _ in INTERSOL_RESTRICTED_BUDGET_NDOS)
    return (
        f"({alias}.NDOS NOT IN ({ndos_placeholders}) OR ({scope_sql}))",
        tuple(INTERSOL_RESTRICTED_BUDGET_NDOS) + scope_params,
    )


def _budget_visibility_predicate(
    company: dict[str, Any],
    user,
    table_alias: str = "B",
) -> tuple[str, tuple[Any, ...]]:
    if _text_value(company.get("phc_db")).casefold() != "intersol":
        return "1 = 1", ()
    return _intersol_budget_visibility_predicate(
        getattr(user, "VENDEDOR", 0),
        table_alias,
    )


def _series_rows(cursor) -> list[dict[str, Any]]:
    rows = _fetch_rows(
        cursor,
        """
        SELECT DISTINCT
            ISNULL(NDOS, 0) AS NDOS,
            LTRIM(RTRIM(ISNULL(NMDOS, ''))) AS NMDOS,
            ISNULL(QTTDEC, 3) AS QTTDEC,
            ISNULL(PREDEC, 4) AS PREDEC,
            ISNULL(ORCAMENTO, 0) AS ORCAMENTO,
            ISNULL(OCI, 0) AS OCI,
            ISNULL(ARMAZEM, 1) AS ARMAZEM,
            ISNULL(OCUPACAO, 0) AS OCUPACAO,
            LTRIM(RTRIM(ISNULL(TIPOSAFT, ''))) AS TIPOSAFT,
            LTRIM(RTRIM(ISNULL(IDSERIE, ''))) AS IDSERIE
        FROM dbo.TS
        WHERE UPPER(LTRIM(RTRIM(ISNULL(NMDOS, '')))) = 'DEVIS'
           OR (ISNULL(ORCAMENTO, 0) = 1 AND ISNULL(OCI, 0) = 1)
        ORDER BY NMDOS, NDOS
        """,
        (),
    )
    allowed_order = {name: index for index, name in enumerate(CLIENT_BUDGET_SERIES)}
    result = [
        {
            "ndos": int(_number_value(row.get("NDOS"))),
            "name": _text_value(row.get("NMDOS")),
            "quantity_decimals": int(_number_value(row.get("QTTDEC"))),
            "price_decimals": int(_number_value(row.get("PREDEC"))),
            "is_budget": _bool_value(row.get("ORCAMENTO")),
            "uses_oci": _bool_value(row.get("OCI")),
            "warehouse": int(_number_value(row.get("ARMAZEM"))) or 1,
            "occupation": int(_number_value(row.get("OCUPACAO"))),
            "saft_type": _text_value(row.get("TIPOSAFT")),
            "series_id": _text_value(row.get("IDSERIE")),
        }
        for row in rows
        if (
            int(_number_value(row.get("NDOS"))) > 0
            and _series_name_key(row.get("NMDOS")) in allowed_order
        )
    ]
    return sorted(
        result,
        key=lambda row: (
            allowed_order[_series_name_key(row.get("name"))],
            int(row.get("ndos") or 0),
        ),
    )


def get_budget_series(feid: Any, user) -> dict[str, Any]:
    company = _company_for_user(feid, user)
    with pyodbc.connect(_phc_conn_str(company["phc_db"], company.get("phc_server", "")), timeout=15) as conn:
        cursor = conn.cursor()
        rows = _series_rows(cursor)
        tax_rates = _tax_rate_rows(cursor)
    return {
        "company": company,
        "rows": rows,
        "default_ndos": _pick_default_series(rows),
        "tax_rates": tax_rates,
    }


def _tax_rate_rows(cursor) -> list[dict[str, Any]]:
    return [
        {
            "table": int(_number_value(row.get("tabiva"))),
            "rate": _percent(row.get("taxaiva")),
        }
        for row in _phc_tax_rates(cursor)
        if int(_number_value(row.get("tabiva"))) > 0
    ]


def get_budget_salespeople(feid: Any, user) -> dict[str, Any]:
    company = _company_for_user(feid, user)
    with pyodbc.connect(_phc_conn_str(company["phc_db"], company.get("phc_server", "")), timeout=15) as conn:
        cursor = conn.cursor()
        columns = _phc_columns(cursor, "CM3")
        if not columns:
            raise BudgetsError("A tabela CM3 não existe no PHC desta empresa.")
        rows = _fetch_rows(
            cursor,
            f"""
            SELECT
                CM3STAMP,
                CM,
                CMDESC,
                {_optional_column(columns, 'C', 'NOME', 'NOME', "''")},
                {_optional_column(columns, 'C', 'INACTIVO', 'INACTIVO', '0')}
            FROM dbo.CM3 C
            WHERE LTRIM(RTRIM(ISNULL(CMDESC, ''))) <> ''
            ORDER BY ISNULL(INACTIVO, 0), CMDESC, CM
            """,
            (),
        )
    return {
        "company": company,
        "rows": [_salesperson_payload(row) for row in rows],
    }


def _salesperson_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "stamp": _text_value(row.get("CM3STAMP")),
        "number": int(_number_value(row.get("CM"))),
        "name": _text_value(row.get("CMDESC")) or _text_value(row.get("NOME")),
        "inactive": _bool_value(row.get("INACTIVO")),
    }


def search_budget_clients(feid: Any, query: Any, user) -> dict[str, Any]:
    company = _company_for_user(feid, user)
    search = _text_value(query)[:120]
    if not search:
        return {"company": company, "rows": []}
    like = f"%{search}%"
    starts = f"{search}%"
    with pyodbc.connect(_phc_conn_str(company["phc_db"], company.get("phc_server", "")), timeout=15) as conn:
        cursor = conn.cursor()
        client_columns = _phc_columns(cursor, "CL")
        rows = _fetch_rows(
            cursor,
            f"""
            SELECT TOP 40
                CLSTAMP,
                NO,
                ESTAB,
                NOME,
                NCONT,
                LOCAL,
                CONTACTO,
                EMAIL,
                TELEFONE,
                VENDEDOR,
                VENDNM,
                {_optional_column(client_columns, 'CL', 'TABIVA', 'VAT_TABLE', '0')}
            FROM dbo.CL CL
            WHERE ISNULL(INACTIVO, 0) = 0
              AND CL.ESTAB = 0
              AND (
                    NOME LIKE ?
                 OR CONVERT(varchar(20), NO) LIKE ?
                 OR NCONT LIKE ?
                 OR LOCAL LIKE ?
                 OR EMAIL LIKE ?
              )
            ORDER BY
                CASE
                    WHEN CONVERT(varchar(20), NO) = ? THEN 0
                    WHEN NOME LIKE ? THEN 1
                    ELSE 2
                END,
                NOME,
                NO,
                ESTAB
            """,
            (like, like, like, like, like, search, starts),
        )
        tax_rates = {
            int(_number_value(row.get("tabiva"))): _decimal(row.get("taxaiva"))
            for row in _phc_tax_rates(cursor)
            if int(_number_value(row.get("tabiva"))) > 0
        }
    return {
        "company": company,
        "rows": [_client_payload(row, tax_rates) for row in rows],
    }


def _client_payload(row: dict[str, Any], tax_rates: dict[int, Decimal] | None = None) -> dict[str, Any]:
    vat_table = int(_number_value(row.get("VAT_TABLE") if row.get("VAT_TABLE") is not None else row.get("TABIVA")))
    vat_rate = (tax_rates or {}).get(vat_table, Decimal("0"))
    return {
        "stamp": _text_value(row.get("CLSTAMP")),
        "number": int(_number_value(row.get("NO"))),
        "establishment": int(_number_value(row.get("ESTAB"))),
        "name": _text_value(row.get("NOME")),
        "vat_number": _text_value(row.get("NCONT")),
        "locality": _text_value(row.get("LOCAL")),
        "contact": _text_value(row.get("CONTACTO")),
        "email": _text_value(row.get("EMAIL")),
        "phone": _text_value(row.get("TELEFONE")),
        "vat_table": vat_table,
        "vat_rate": _percent(vat_rate),
        "salesperson_number": int(_number_value(row.get("VENDEDOR"))),
        "salesperson": _text_value(row.get("VENDNM")),
    }


def _parse_ndos(value: Any, series: list[dict[str, Any]]) -> int:
    try:
        ndos = int(value or 0)
    except (TypeError, ValueError) as exc:
        raise BudgetsValidationError("Série de orçamento inválida.") from exc
    valid = {int(row.get("ndos") or 0) for row in series}
    if not ndos:
        ndos = _pick_default_series(series)
    if not ndos or ndos not in valid:
        raise BudgetsValidationError("Série de orçamento inexistente nesta empresa.")
    return ndos


def _parse_year(value: Any) -> int:
    raw = _text_value(value)
    if not raw:
        return datetime.now().year
    try:
        year = int(raw)
    except ValueError as exc:
        raise BudgetsValidationError("Ano inválido.") from exc
    if year < 1900 or year > 2200:
        raise BudgetsValidationError("Ano inválido.")
    return year


def list_budgets(filters: dict[str, Any], user) -> dict[str, Any]:
    company = _company_for_user(filters.get("feid"), user)
    search = _text_value(filters.get("q"))[:120]
    year = _parse_year(filters.get("year"))

    with pyodbc.connect(_phc_conn_str(company["phc_db"], company.get("phc_server", "")), timeout=20) as conn:
        cursor = conn.cursor()
        series = _series_rows(cursor)
        ndos = _parse_ndos(filters.get("ndos"), series)
        where = ["B.NDOS = ?", "B.BOANO = ?"]
        params: list[Any] = [ndos, year]
        visibility_sql, visibility_params = _budget_visibility_predicate(company, user, "B")
        where.append(visibility_sql)
        params.extend(visibility_params)
        if search:
            like = f"%{search}%"
            where.append(
                "(CONVERT(varchar(20), B.OBRANO) LIKE ? OR B.NOME LIKE ? OR B.TRAB1 LIKE ? "
                "OR B.OBRANOME LIKE ? OR B.VENDNM LIKE ? OR B2.PROCESSO LIKE ?)"
            )
            params.extend([like] * 6)

        rows = _fetch_rows(
            cursor,
            f"""
            SELECT TOP {MAX_RESULTS}
                B.BOSTAMP,
                B.NDOS,
                B.NMDOS,
                B.OBRANO,
                B.BOANO,
                B.DATAOBRA,
                B.NO,
                B.NOME,
                B.TRAB1,
                B.OBRANOME,
                B.VENDNM,
                B.MOEDA,
                B.ETOTALDEB,
                B.ECUSTO,
                B.APROVADO,
                B.FECHADA,
                B2.PROCESSO,
                B2.AREA,
                B2.ADJUDICADO,
                B2.ANULADO,
                ISNULL(LINES.LINE_COUNT, 0) AS LINE_COUNT
            FROM dbo.BO B
            LEFT JOIN dbo.BO2 B2 ON B2.BO2STAMP = B.BOSTAMP
            OUTER APPLY (
                SELECT COUNT_BIG(1) AS LINE_COUNT
                FROM dbo.BI I
                WHERE I.BOSTAMP = B.BOSTAMP
            ) LINES
            WHERE {' AND '.join(where)}
            ORDER BY B.DATAOBRA DESC, B.OBRANO DESC, B.BOSTAMP DESC
            """,
            tuple(params),
        )

    return {
        "company": company,
        "series": series,
        "selected_ndos": ndos,
        "year": year,
        "limit": MAX_RESULTS,
        "rows": [_budget_summary(row, company) for row in rows],
    }


def _budget_summary(row: dict[str, Any], company: dict[str, Any]) -> dict[str, Any]:
    return {
        "bostamp": _text_value(row.get("BOSTAMP")),
        "ndos": int(_number_value(row.get("NDOS"))),
        "series": _text_value(row.get("NMDOS")),
        "number": int(_number_value(row.get("OBRANO"))),
        "year": int(_number_value(row.get("BOANO"))),
        "date": _business_date_iso(row.get("DATAOBRA")),
        "client_number": int(_number_value(row.get("NO"))),
        "client_name": _text_value(row.get("NOME")),
        "work_name": _text_value(row.get("TRAB1")),
        "locality": _text_value(row.get("OBRANOME")),
        "salesperson": _text_value(row.get("VENDNM")),
        "process": _text_value(row.get("PROCESSO")),
        "area": _text_value(row.get("AREA")),
        "currency": _currency_code(row.get("MOEDA"), company),
        "total": _money(row.get("ETOTALDEB")),
        "cost": _money(row.get("ECUSTO")),
        "approved": _bool_value(row.get("APROVADO")),
        "closed": _bool_value(row.get("FECHADA")),
        "awarded": _bool_value(row.get("ADJUDICADO")),
        "cancelled": _bool_value(row.get("ANULADO")),
        "line_count": int(_number_value(row.get("LINE_COUNT"))),
    }


def get_budget_detail(feid: Any, bostamp: str, user) -> dict[str, Any]:
    company = _company_with_print_settings(_company_for_user(feid, user))
    clean_stamp = _text_value(bostamp)
    if not clean_stamp:
        raise BudgetsValidationError("Orçamento não indicado.")

    with pyodbc.connect(_phc_conn_str(company["phc_db"], company.get("phc_server", "")), timeout=20) as conn:
        cursor = conn.cursor()
        bo_columns = _phc_columns(cursor, "BO")
        bo2_columns = _phc_columns(cursor, "BO2")
        bo3_columns = _phc_columns(cursor, "BO3")
        visibility_sql, visibility_params = _budget_visibility_predicate(company, user, "B")
        header_rows = _fetch_rows(
            cursor,
            f"""
            SELECT
                B.BOSTAMP, B.NMDOS, B.NDOS, B.OBRANO, B.BOANO, B.DATAOBRA,
                B.NO, B.ESTAB, B.NOME, B.TRAB1, B.OBRANOME, B.LOCAL, B.MORADA,
                B.CODPOST, B.VENDEDOR, B.VENDNM, B.SERIE, B.ZONA, B.NOPAT,
                B.MOEDA, B.ETOTALDEB, B.ECUSTO, B.APROVADO, B.FECHADA, B.OBS, B.FREF,
                B.CCUSTO, B.COBRANCA, B.TECNICO, B.TECNNM,
                B.USRDATA AS BO_USRDATA, B.USRHORA AS BO_USRHORA,
                {_optional_column(bo_columns, 'B', 'U_MARGEM', 'U_MARGEM', '0')},
                {_optional_column(bo_columns, 'B', 'U_EMARGEM', 'U_EMARGEM', '0')},
                {_optional_column(bo2_columns, 'B2', 'PROCESSO', 'PROCESSO', "''")},
                {_optional_column(bo2_columns, 'B2', 'AREA', 'AREA', "''")},
                {_optional_column(bo2_columns, 'B2', 'EMAIL', 'EMAIL', "''")},
                {_optional_column(bo2_columns, 'B2', 'TELEFONE', 'TELEFONE', "''")},
                {_optional_column(bo2_columns, 'B2', 'ADJUDICADO', 'ADJUDICADO', '0')},
                {_optional_column(bo2_columns, 'B2', 'ORCAMENTO', 'ORCAMENTO', '0')},
                {_optional_column(bo2_columns, 'B2', 'ANULADO', 'ANULADO', '0')},
                {_optional_column(bo3_columns, 'B3', 'U_APROVDAT', 'U_APROVDAT')},
                {_optional_column(bo3_columns, 'B3', 'U_APROVUSR', 'U_APROVUSR', "''")},
                {_optional_column(bo3_columns, 'B3', 'MOTANUL', 'MOTANUL', "''")}
            FROM dbo.BO B
            LEFT JOIN dbo.BO2 B2 ON B2.BO2STAMP = B.BOSTAMP
            LEFT JOIN dbo.BO3 B3 ON B3.BO3STAMP = B.BOSTAMP
            WHERE B.BOSTAMP = ?
              AND {visibility_sql}
            """,
            (clean_stamp, *visibility_params),
        )
        if not header_rows:
            raise BudgetsNotFoundError("Orçamento não encontrado no PHC desta empresa.")

        bi_columns = _phc_columns(cursor, "BI")
        bi2_columns = _phc_columns(cursor, "BI2")
        line_rows = _fetch_rows(
            cursor,
            f"""
            SELECT
                I.BOSTAMP, I.BISTAMP, I.LORDEM, I.LITEM, I.REF, I.DESIGN, I.DGERAL,
                I.DESCONTO, I.DESC2, I.EDEBITO, I.ETTDEB, I.IVA, I.TABIVA,
                I.QTT, I.EPCUSTO, I.ECUSTOIND, I.TEMOCI, I.UNIDADE,
                {_optional_column(bi_columns, 'I', 'U_ESPESS', 'U_ESPESS', '0')},
                {_optional_column(bi_columns, 'I', 'U_ALT', 'U_ALT', '0')},
                {_optional_column(bi_columns, 'I', 'U_BLOQPV', 'U_BLOQPV', '0')},
                {_optional_column(bi_columns, 'I', 'U_BOMBA', 'U_BOMBA', '0')},
                {_optional_column(bi_columns, 'I', 'U_MO', 'U_MO', '0')},
                {_optional_column(bi_columns, 'I', 'U_OPCAO', 'U_OPCAO', '0')},
                {_optional_column(bi_columns, 'I', 'U_SIMULT', 'U_SIMULT', '0')},
                {_optional_column(bi_columns, 'I', 'U_PRORATA', 'U_PRORATA', '0')},
                {_optional_column(bi_columns, 'I', 'U_VARIANTE', 'U_VARIANTE', '0')},
                {_optional_column(bi2_columns, 'I2', 'QTTCOMPRA', 'QTTCOMPRA', '0')},
                {_optional_column(bi2_columns, 'I2', 'QTTENC', 'QTTENC', '0')},
                {_optional_column(bi2_columns, 'I2', 'U_APROVA', 'U_APROVA', '0')},
                {_optional_column(bi2_columns, 'I2', 'U_DESAPRO', 'U_DESAPRO', '0')}
            FROM dbo.BI I
            LEFT JOIN dbo.BI2 I2 ON I2.BI2STAMP = I.BISTAMP
            WHERE I.BOSTAMP = ?
            ORDER BY I.LORDEM, I.LITEM, I.BISTAMP
            """,
            (clean_stamp,),
        )
        oci_columns = _phc_columns(cursor, "OCI")
        oci_rows = []
        if oci_columns:
            # OCI.U_DESIGN is the technical snapshot authored for the budget.
            # Do not replace it with an ST catalogue translation at print time.
            oci_designation_sql = _oci_designation_fallback(oci_columns, "O")
            oci_rows = _fetch_rows(
                cursor,
                f"""
                SELECT
                    O.OCISTAMP, O.BOSTAMP, O.BISTAMP, O.REF, O.DESIGN, O.FAMILIA,
                    O.QTT, O.PCUSTO, O.EPCUSTO, O.UNIDADE, O.QTTTOTAL, O.RENDIM,
                    O.NIVEL, O.LNIVEL, O.QTTFINAL,
                    {_optional_column(oci_columns, 'O', 'U_FORFAIT', 'U_FORFAIT', '0')},
                    {_optional_column(oci_columns, 'O', 'U_AREA', 'U_AREA', '0')},
                    {_optional_column(oci_columns, 'O', 'U_ESPESS', 'U_ESPESS', '0')},
                    {_optional_column(oci_columns, 'O', 'U_VOLUME', 'U_VOLUME', '0')},
                    {_optional_column(oci_columns, 'O', 'U_PESO', 'U_PESO', '0')},
                    {_optional_column(oci_columns, 'O', 'U_CONSUMO', 'U_CONSUMO', '0')},
                    {_optional_column(oci_columns, 'O', 'U_COEF', 'U_COEF', '0')},
                    {_optional_column(oci_columns, 'O', 'U_FORMULA', 'U_FORMULA', "''")},
                    {_optional_column(oci_columns, 'O', 'U_DESIGN', 'U_DESIGN', "''")},
                    {_optional_column(oci_columns, 'O', 'U_PVENDA', 'U_PVENDA', '0')},
                    {oci_designation_sql} AS [ARTICLE_DESIGN]
                FROM dbo.OCI O
                INNER JOIN dbo.BI I ON I.BISTAMP = O.BISTAMP
                LEFT JOIN dbo.STFAMI F
                       ON LTRIM(RTRIM(ISNULL(F.REF, ''))) = LTRIM(RTRIM(ISNULL(O.FAMILIA, '')))
                WHERE I.BOSTAMP = ?
                  AND LTRIM(RTRIM(ISNULL(O.REF, ''))) <> 'XZ'
                ORDER BY I.LORDEM, ISNULL(F.TXTQLOOK, 'ZZ'), O.NIVEL, O.OCISTAMP
                """,
                (clean_stamp,),
            )
        # BOT differs slightly between PHC versions. Fetch the complete tax rows,
        # then normalise known column names in _vat_payload.
        tax_rows = _fetch_rows(cursor, "SELECT T.* FROM dbo.BOT T WHERE T.BOSTAMP = ?", (clean_stamp,))
        tax_rates = _tax_rate_rows(cursor)
        client_tax_table = 0
        cl_columns = _phc_columns(cursor, "CL")
        if "tabiva" in cl_columns:
            client_tax = _fetch_rows(
                cursor,
                "SELECT TOP 1 TABIVA FROM dbo.CL WHERE NO = ? AND ESTAB = ?",
                (header_rows[0].get("NO"), header_rows[0].get("ESTAB")),
            )
            if client_tax:
                client_tax_table = int(_number_value(client_tax[0].get("TABIVA")))
        company["e1"] = _load_e1_company(cursor)

    header = _header_payload(header_rows[0], company)
    lines = sorted((_line_payload(row) for row in line_rows), key=_line_item_sort_key)
    oci_by_line: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in oci_rows:
        payload = _oci_payload(row)
        oci_by_line[payload["line_stamp"]].append(payload)
    for line in lines:
        line["technical_lines"] = oci_by_line.get(line["bistamp"], [])
    default_vat_table, default_vat_rate = _budget_default_vat(lines, tax_rates, client_tax_table)
    header["default_vat_table"] = default_vat_table
    header["default_vat_rate"] = _percent(default_vat_rate)
    return {
        "company": company,
        "header": header,
        "lines": lines,
        "totals": _totals_payload(header, lines),
        "vat_rows": [_vat_payload(row) for row in tax_rows],
        "tax_rates": tax_rates,
    }


def get_budget_detail_by_number(feid: Any, number: Any, year: Any, user) -> dict[str, Any]:
    """Resolve a Devis by its visible PHC number, then load its complete detail."""
    company = _company_for_user(feid, user)
    try:
        document_number = int(number)
    except (TypeError, ValueError) as exc:
        raise BudgetsValidationError("Número de Devis inválido.") from exc
    document_year = _parse_year(year)
    with pyodbc.connect(_phc_conn_str(company["phc_db"], company.get("phc_server", "")), timeout=15) as conn:
        cursor = conn.cursor()
        visibility_sql, visibility_params = _budget_visibility_predicate(company, user, "B")
        rows = _fetch_rows(
            cursor,
            f"""
            SELECT TOP 1 B.BOSTAMP
            FROM dbo.BO B
            WHERE B.NDOS = 115 AND B.OBRANO = ? AND B.BOANO = ?
              AND {visibility_sql}
            ORDER BY B.BOSTAMP DESC
            """,
            (document_number, document_year, *visibility_params),
        )
    if not rows:
        raise BudgetsNotFoundError("Devis não encontrado no PHC desta empresa.")
    return get_budget_detail(feid, _text_value(rows[0].get("BOSTAMP")), user)


def _header_payload(row: dict[str, Any], company: dict[str, Any]) -> dict[str, Any]:
    return {
        **_budget_summary(row, company),
        "establishment": int(_number_value(row.get("ESTAB"))),
        "address": _text_value(row.get("MORADA")),
        "postal_code": _text_value(row.get("CODPOST")),
        "place": _text_value(row.get("LOCAL")),
        "salesperson_number": int(_number_value(row.get("VENDEDOR"))),
        "attention": _text_value(row.get("SERIE")),
        "zone": _text_value(row.get("ZONA")),
        "contact_number": int(_number_value(row.get("NOPAT"))),
        "margin_percentage": _percent(row.get("U_MARGEM")),
        "margin_value": _money(row.get("U_EMARGEM")),
        "observations": _text_value(row.get("OBS")),
        "reference": _text_value(row.get("FREF")),
        "cost_center": _text_value(row.get("CCUSTO")),
        "payment_terms": _text_value(row.get("COBRANCA")),
        "technician_number": int(_number_value(row.get("TECNICO"))),
        "technician": _text_value(row.get("TECNNM")),
        "email": _text_value(row.get("EMAIL")),
        "phone": _text_value(row.get("TELEFONE")),
        "is_budget": _bool_value(row.get("ORCAMENTO")),
        "approval_date": _business_date_iso(row.get("U_APROVDAT")),
        "approval_user": _text_value(row.get("U_APROVUSR")),
        "cancellation_reason": _text_value(row.get("MOTANUL")),
        "revision": _revision_token(row.get("BO_USRDATA"), row.get("BO_USRHORA")),
    }


def _line_payload(row: dict[str, Any]) -> dict[str, Any]:
    quantity = _decimal(row.get("QTT"))
    unit_cost = _decimal(row.get("EPCUSTO"))
    thickness = _decimal(row.get("U_ESPESS"))
    total = _decimal(row.get("ETTDEB"))
    cost_total = quantity * unit_cost
    profit = total - cost_total
    margin = (profit / total * Decimal("100")) if total else Decimal("0")
    return {
        "bistamp": _text_value(row.get("BISTAMP")),
        "budget_stamp": _text_value(row.get("BOSTAMP")),
        "order": _number_value(row.get("LORDEM")),
        "item": int(_number_value(row.get("LITEM"))),
        "item_label": _text_value(row.get("LITEM")),
        "reference": _text_value(row.get("REF")),
        "designation": _text_value(row.get("DESIGN")),
        "description": _text_value(row.get("DGERAL")),
        "discount_1": _percent(row.get("DESCONTO")),
        "discount_2": _percent(row.get("DESC2")),
        "unit_price": _qty(row.get("EDEBITO")),
        "total": _qty(total),
        "vat_rate": _percent(row.get("IVA")),
        "vat_table": int(_number_value(row.get("TABIVA"))),
        "quantity": _qty(quantity),
        "surface": _qty(quantity),
        "unit": _text_value(row.get("UNIDADE")),
        "unit_cost": _qty(unit_cost),
        "indirect_cost": _qty(row.get("ECUSTOIND")),
        "cost_total": _qty(cost_total),
        "thickness": _qty(thickness),
        "volume": _qty(quantity * thickness),
        "height": _qty(row.get("U_ALT")),
        "blocked_price": _bool_value(row.get("U_BLOQPV")),
        "pump": _bool_value(row.get("U_BOMBA")),
        "has_technical_detail": _bool_value(row.get("TEMOCI")),
        "labour": _bool_value(row.get("U_MO")),
        "option": _bool_value(row.get("U_OPCAO")),
        "simultaneous": _bool_value(row.get("U_SIMULT")),
        "pro_rata": _bool_value(row.get("U_PRORATA")),
        "pro_rata_percentage": _percent(row.get("U_PRORATA")),
        "variant": _bool_value(row.get("U_VARIANTE")) or _bool_value(row.get("U_ALT")),
        "approved": _bool_value(row.get("U_APROVA")),
        "disapproved": _bool_value(row.get("U_DESAPRO")),
        "purchase_quantity": _qty(row.get("QTTCOMPRA")),
        "ordered_quantity": _qty(row.get("QTTENC")),
        "margin_percentage": _percent(margin),
        "margin_per_unit": _qty(_decimal(row.get("EDEBITO")) - unit_cost),
        "margin_value": _qty(profit),
        "profit": _qty(profit),
    }


def _budget_default_vat(
    lines: list[dict[str, Any]],
    tax_rates: list[dict[str, Any]],
    client_tax_table: Any = 0,
) -> tuple[int, Decimal]:
    """Choose the VAT inherited by a new position in an existing budget."""
    rates: dict[int, Decimal] = {}
    for row in tax_rates:
        table = int(_number_value(row.get("table") if row.get("table") is not None else row.get("tabiva")))
        rate = row.get("rate") if row.get("rate") is not None else row.get("taxaiva")
        if table > 0:
            rates[table] = _decimal(rate)
    client_table = int(_number_value(client_tax_table))
    if client_table in rates:
        return client_table, rates[client_table]

    # A client may have no default VAT table. In an existing dossier, inherit
    # the table used by the largest taxable amount instead of creating a 0% line.
    bases: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    occurrences: dict[int, int] = defaultdict(int)
    for line in lines:
        if _bool_value(line.get("variant")) or _bool_value(line.get("option")):
            continue
        table = int(_number_value(line.get("vat_table")))
        if table not in rates:
            continue
        bases[table] += abs(_decimal(line.get("total")))
        occurrences[table] += 1
    if bases:
        table = max(bases, key=lambda code: (bases[code], occurrences[code], -code))
        return table, rates[table]

    table = 2 if 2 in rates else next(iter(rates), 0)
    return table, rates.get(table, Decimal("0"))


def _totals_payload(header: dict[str, Any], lines: list[dict[str, Any]]) -> dict[str, Any]:
    calculated_total = sum((_decimal(line.get("total")) for line in lines), Decimal("0"))
    calculated_cost = sum((_decimal(line.get("cost_total")) for line in lines), Decimal("0"))
    total = _decimal(header.get("total")) or calculated_total
    cost = _decimal(header.get("cost")) or calculated_cost
    profit = total - cost
    margin = (profit / total * Decimal("100")) if total else Decimal("0")
    return {
        "total": _money(total),
        "cost": _money(cost),
        "profit": _money(profit),
        "margin_percentage": _percent(margin),
        "line_count": len(lines),
    }


def _first_number(row: dict[str, Any], *names: str) -> Decimal:
    for name in names:
        if name in row and row.get(name) is not None:
            return _decimal(row.get(name))
    return Decimal("0")


def _vat_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "rate": _percent(_first_number(row, "IVA", "TAXA", "TAXAIVA", "PERIVA")),
        "taxable_amount": _money(
            _first_number(row, "EBASEINC", "EINCIDENCIA", "INCIDENCIA", "BASEIVA", "BASE", "ETTDEB", "VALORBASE")
        ),
        "amount": _money(_first_number(row, "EVALOR", "ETIVA", "VALOR", "VALORIVA", "IVA_VALOR", "TOTALIVA")),
        "table": int(_number_value(row.get("TABIVA"))),
    }


def budget_print_payload(detail: dict[str, Any]) -> dict[str, Any]:
    """Transform a raw Devis detail into its client-facing print model."""
    language = _budget_print_language(detail.get("company") or {})
    primary: list[dict[str, Any]] = []
    children: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for line in detail.get("lines") or []:
        item = str(line.get("item_label") or "").strip()
        reference = str(line.get("reference") or "").strip().upper()
        is_plus_value = reference in {"PVL", "MVL"}
        if is_plus_value and "." in item:
            adjustment = dict(line)
            if language == "pt":
                adjustment["adjustment_label"] = "MENOR-VALIA" if reference == "MVL" else "MAIOR-VALIA"
            else:
                adjustment["adjustment_label"] = "MOINS-VALUE" if reference == "MVL" else "PLUS-VALUE"
            children[item.split(".", 1)[0]].append(adjustment)
        else:
            primary.append(line)

    articles, pro_rata = [], []
    for line in primary:
        if line.get("pro_rata") or str(line.get("reference") or "").strip().upper() == "PP":
            pro_rata.append(line)
            continue
        article = dict(line)
        # The commercial description printed on a budget is the snapshot kept
        # in BI.DGERAL. BI.DESIGN is only the catalogue/designation fallback.
        article["designation"] = _text_value(article.get("description")) or _text_value(article.get("designation"))
        if "ZZ" in {
            _text_value(article.get("reference")).upper(),
            _text_value(article.get("item_label")).upper(),
        }:
            article["designation"] = "DESCONTO" if language == "pt" else "ESCOMPTE"
        article["plus_values"] = children.get(str(line.get("item_label") or "").strip(), [])
        article["technical_lines"] = list(line.get("technical_lines") or [])
        article["display_total"] = _budget_line_display_total(article)
        articles.append(article)

    priced_articles = [row for row in articles if not row.get("option") and not row.get("variant")]
    discount_articles = [
        row
        for row in priced_articles
        if "ZZ" in {
            _text_value(row.get("reference")).upper(),
            _text_value(row.get("item_label")).upper(),
        }
    ]
    goods_articles = [row for row in priced_articles if row not in discount_articles]
    goods_total = sum((_decimal(row.get("total")) for row in goods_articles), Decimal("0"))
    discount_total = sum((_decimal(row.get("total")) for row in discount_articles), Decimal("0"))
    commercial_total = goods_total + discount_total
    pro_rata_total = sum((_decimal(row.get("total")) for row in pro_rata), Decimal("0"))
    net_total = commercial_total + pro_rata_total
    vat_rows = [row for row in detail.get("vat_rows") or [] if _decimal(row.get("amount"))]
    if not vat_rows:
        bases: dict[Decimal, Decimal] = defaultdict(lambda: Decimal("0"))
        for row in [*priced_articles, *pro_rata]:
            bases[_decimal(row.get("vat_rate"))] += _decimal(row.get("total"))
        vat_rows = [
            {"rate": _percent(rate), "taxable_amount": _money(base), "amount": _money(base * rate / 100), "table": 0}
            for rate, base in sorted(bases.items())
        ]
    vat_total = sum((_decimal(row.get("amount")) for row in vat_rows), Decimal("0"))
    return {
        "company": detail.get("company") or {}, "header": detail.get("header") or {},
        "language": language,
        "articles": articles, "pro_rata": pro_rata, "vat_rows": vat_rows,
        "options": [row for row in articles if row.get("option")],
        "variants": [row for row in articles if row.get("variant") and not row.get("option")],
        "totals": {"goods_total": _money(goods_total), "discount_total": _money(discount_total),
                   "commercial_total": _money(commercial_total), "pro_rata_total": _money(pro_rata_total),
                   "net_total": _money(net_total), "vat_total": _money(vat_total),
                   "gross_total": _money(net_total + vat_total)},
    }


def _budget_line_display_total(line: dict[str, Any]) -> Decimal:
    stored_total = _decimal(line.get("total"))
    if stored_total or not (line.get("option") or line.get("variant")):
        return stored_total
    # PHC commonly applies a 100% discount to option/variant rows so they do
    # not contribute to the document total.  For the client printout we still
    # need to show the commercial value of the alternative itself.
    calculated = _decimal(line.get("quantity")) * _decimal(line.get("unit_price"))
    return calculated.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _format_fr_number(value: Any, decimals: int = 2) -> str:
    amount = _decimal(value).quantize(Decimal("1").scaleb(-decimals))
    raw = f"{amount:,.{decimals}f}"
    return raw.replace(",", " ").replace(".", ",")


def _format_fr_quantity(value: Any) -> str:
    return _format_fr_number(value, 3)


def _format_fr_date(value: Any) -> str:
    if isinstance(value, str):
        raw = value.strip()
        if len(raw) >= 10 and raw[4:5] == "-" and raw[7:8] == "-":
            return f"{raw[8:10]}.{raw[5:7]}.{raw[:4]}"
    iso = _business_date_iso(value)
    return f"{iso[8:10]}.{iso[5:7]}.{iso[:4]}" if iso else ""


def _format_grouped_identifier(value: Any, groups: tuple[int, ...]) -> str:
    raw = _text_value(value)
    prefix = "".join(char for char in raw if char.isalpha()).upper()
    digits = "".join(char for char in raw if char.isdigit())
    if not digits:
        return raw
    chunks, offset = [], 0
    for size in groups:
        if offset >= len(digits):
            break
        chunks.append(digits[offset:offset + size])
        offset += size
    if offset < len(digits):
        chunks.append(digits[offset:])
    if prefix and chunks:
        return prefix + chunks[0] + ((" " + " ".join(chunks[1:])) if len(chunks) > 1 else "")
    return " ".join(chunks)


def _format_company_capital(value: Any) -> str:
    raw = _text_value(value)
    if not raw:
        return ""
    if "€" in raw or "EUR" in raw.upper():
        return raw
    # PHC monetary fields normally arrive as Decimal values using a dot as
    # decimal separator. Preserve already-localised text values such as
    # ``900.000,00`` while formatting native numeric values in French style.
    if isinstance(value, (int, float, Decimal)) or ("," not in raw and raw.replace(".", "", 1).isdigit()):
        return f"{_format_fr_number(value)} €"
    return f"{raw} €"


def _budget_pdf_style(value: Any = "modern") -> str:
    return "classic" if _text_value(value).casefold() == "classic" else "modern"


def _budget_print_language(company: dict[str, Any]) -> str:
    return "pt" if _text_value(company.get("phc_db")).casefold() == "hsols_pt" else "fr"


def _budget_print_labels(language: str) -> dict[str, str]:
    if language == "pt":
        return {
            "document_title": "Orçamento N.º",
            "original": "ORIGINAL",
            "not_approved": "NÃO APROVADO",
            "salesperson": "Vendedor:",
            "salesperson_sub": "Salesman:",
            "work": "Obra:",
            "work_sub": "Construction Site:",
            "date": "Data:",
            "date_sub": "Date:",
            "client_number": "N.º Cliente:",
            "client_number_sub": "Client Nr.:",
            "client": "Cliente:",
            "client_sub": "Client:",
            "address": "Morada:",
            "address_sub": "Address:",
            "item": "Artigo",
            "item_sub": "Item",
            "designation": "Designação",
            "designation_sub": "Description",
            "quantity": "Qtd.",
            "quantity_sub": "Qty",
            "unit": "Un.",
            "unit_sub": "Un.",
            "unit_price": "P. Unit.",
            "unit_price_sub": "Unit Price",
            "line_total": "Total",
            "line_total_sub": "Net Amount",
            "amount_total": "Total:",
            "amount_total_sub": "Total Goods:",
            "pro_rata_total": "Prorata:",
            "pro_rata_total_sub": "Prorata:",
            "discounts": "Descontos:",
            "discounts_sub": "Discounts:",
            "net_total": "Total Líquido:",
            "net_total_sub": "Net Amount:",
            "vat": "IVA:",
            "vat_sub": "VAT:",
            "gross_total": "TOTAL:",
            "signature": "Assinatura",
            "signature_text": "A aceitação do orçamento pelo Cliente vale como aceitação, compreensão e leitura das CGVE anexas.",
            "option": "OPÇÃO",
            "variant": "ALTERNATIVA",
            "options": "Opções",
            "variants": "Alternativas",
            "vat_footer": "N.º Contribuinte:",
            "siret_footer": "N.º Siret:",
            "capital_footer": "Capital Social:",
        }
    return {
        "document_title": "Devis N°",
        "original": "ORIGINAL",
        "not_approved": "NON APPROUVÉ",
        "salesperson": "Chargé d’Affaires:",
        "salesperson_sub": "Salesman:",
        "work": "Chantier:",
        "work_sub": "Construction Site:",
        "date": "Date:",
        "date_sub": "Date:",
        "client_number": "N° Client:",
        "client_number_sub": "Client Nr.:",
        "client": "Client:",
        "client_sub": "Client:",
        "address": "Adresse:",
        "address_sub": "Address:",
        "item": "Article",
        "item_sub": "Item",
        "designation": "Designation",
        "designation_sub": "Description",
        "quantity": "Qté.",
        "quantity_sub": "Qty",
        "unit": "Un.",
        "unit_sub": "Un.",
        "unit_price": "P.U.H.T",
        "unit_price_sub": "Unit Price",
        "line_total": "Total H.T.",
        "line_total_sub": "Net Amount",
        "amount_total": "Total HT :",
        "amount_total_sub": "Amount:",
        "pro_rata_total": "Prorata :",
        "pro_rata_total_sub": "Prorata:",
        "discounts": "Escomptes :",
        "discounts_sub": "Discounts:",
        "net_total": "Total HT NET:",
        "net_total_sub": "Net Amount:",
        "vat": "TVA:",
        "vat_sub": "VAT:",
        "gross_total": "TOTAL TTC:",
        "signature": "Signature",
        "signature_text": "l'acceptation du devis par le Client vaut acceptation, compréhension et lecture des CGVE jointes.",
        "option": "OPTION",
        "variant": "VARIANTE",
        "options": "Options",
        "variants": "Variantes",
        "vat_footer": "N° TVA Intracom.:",
        "siret_footer": "N° Siret :",
        "capital_footer": "Capital Social :",
    }


def _budget_company_meta(company: dict[str, Any]) -> dict[str, str]:
    e1 = company.get("e1") or {}
    company_name = _text_value(e1.get("name")) or _text_value(company.get("name"))
    postal_code = _text_value(e1.get("postal_code"))
    city = _text_value(e1.get("city"))
    postal_city = postal_code if city and city.casefold() in postal_code.casefold() else " ".join(
        part for part in (postal_code, city) if part
    )
    return {
        "name": company_name.upper(),
        "address": _text_value(e1.get("address")),
        "postal_city": postal_city,
        "phone": _text_value(e1.get("phone")),
        "email": _text_value(e1.get("email")),
        "vat": _format_grouped_identifier(e1.get("vat_number"), (2, 3, 3, 3)),
        "siret": _format_grouped_identifier(e1.get("siret"), (3, 3, 3, 5)),
        "capital": _format_company_capital(e1.get("capital")),
    }


def render_budget_pdf_html(
    detail: dict[str, Any],
    style: Any = "modern",
    suppress_running: bool = False,
) -> str:
    """Render the A4 client printout. The caller is responsible for PDF conversion."""
    document = budget_print_payload(detail)
    header = document["header"]
    company = document["company"]
    print_language = document["language"]
    company_meta = _budget_company_meta(company)
    from services.ft_pdf_service import build_logo_payload

    return render_template(
        "gr_budgets/devis_pdf.html",
        document=document,
        company=company_meta,
        logo=build_logo_payload(_text_value(company.get("logo_path")), fallback_path=""),
        approved=bool(header.get("approved")),
        theme=_budget_pdf_style(style),
        print_language=print_language,
        labels=_budget_print_labels(print_language),
        suppress_running=bool(suppress_running),
        fmt_money=_format_fr_number,
        fmt_quantity=_format_fr_quantity,
        fmt_date=_format_fr_date,
    )


def decorate_budget_browser_pdf(pdf_bytes: bytes, detail: dict[str, Any]) -> bytes:
    """Add repeating budget furniture when the browser is the PDF engine.

    Chromium does not support CSS running elements. The HTML hides those
    elements for Chromium, and this pass draws them into the reserved page
    margins without touching the general-terms page.
    """
    import io

    from pypdf import PdfReader, PdfWriter
    from reportlab.lib.colors import HexColor
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.pdfgen import canvas

    source = PdfReader(io.BytesIO(pdf_bytes))
    pages = list(source.pages)
    if not pages:
        return pdf_bytes

    terms_start = next(
        (
            index
            for index, page in enumerate(pages)
            if "condicoes gerais de venda" in _series_name_key(page.extract_text())
            or "conditions generales de vente" in _series_name_key(page.extract_text())
        ),
        len(pages) - 1 if len(pages) > 1 else len(pages),
    )
    document = budget_print_payload(detail)
    header = document["header"]
    company = _budget_company_meta(document["company"])
    labels = _budget_print_labels(document["language"])
    millimetre = 72 / 25.4
    red = HexColor("#d32632")
    dark = HexColor("#303236")
    muted = HexColor("#77797d")

    def fitted(value: Any, font: str, size: float, max_width: float) -> str:
        text = _text_value(value)
        if stringWidth(text, font, size) <= max_width:
            return text
        suffix = "..."
        while text and stringWidth(text + suffix, font, size) > max_width:
            text = text[:-1]
        return text.rstrip() + suffix if text else suffix

    def labelled(c, x: float, y: float, label: str, value: Any, width: float, bold_value: bool = False):
        size = 7.6
        c.setFillColor(dark)
        c.setFont("Helvetica", size)
        c.drawString(x, y, label)
        label_width = stringWidth(label, "Helvetica", size) + 3
        value_font = "Helvetica-Bold" if bold_value else "Helvetica"
        c.setFont(value_font, size)
        c.drawString(x + label_width, y, fitted(value, value_font, size, max(8, width - label_width)))

    def sublabel(c, x: float, y: float, value: str):
        c.setFillColor(muted)
        c.setFont("Helvetica-Oblique", 5.8)
        c.drawString(x, y, value)

    def draw_header(c, width: float, height: float):
        left = 17 * millimetre
        right = width - left
        title_y = height - 8.5 * millimetre
        c.setFillColor(dark)
        c.setFont("Helvetica-Bold", 12.5)
        c.drawRightString(right, title_y, f"{labels['document_title']} {int(header.get('number') or 0)}")
        c.setStrokeColor(red)
        c.setLineWidth(1.2)
        c.line(left, height - 11.8 * millimetre, right, height - 11.8 * millimetre)

        first_y = height - 18.2 * millimetre
        col1, col2, col3 = left + 1 * millimetre, left + 50 * millimetre, left + 143 * millimetre
        labelled(c, col1, first_y, labels["client_number"] + " ", header.get("client_number"), 47 * millimetre)
        labelled(c, col2, first_y, labels["client"] + " ", header.get("client_name"), 91 * millimetre, True)
        labelled(c, col3, first_y, labels["date"] + " ", _format_fr_date(header.get("date")), 32 * millimetre)
        sublabel(c, col1, first_y - 3.2 * millimetre, labels["client_number_sub"])
        sublabel(c, col2, first_y - 3.2 * millimetre, labels["client_sub"])
        sublabel(c, col3, first_y - 3.2 * millimetre, labels["date_sub"])

        second_y = height - 27.2 * millimetre
        labelled(c, col1, second_y, labels["salesperson"] + " ", header.get("salesperson"), 68 * millimetre)
        work = _text_value(header.get("work_name"))
        locality = _text_value(header.get("locality"))
        if locality:
            work = f"{work} | {locality}" if work else locality
        labelled(c, left + 73 * millimetre, second_y, labels["work"] + " ", work, 102 * millimetre)
        sublabel(c, col1, second_y - 3.2 * millimetre, labels["salesperson_sub"])
        sublabel(c, left + 73 * millimetre, second_y - 3.2 * millimetre, labels["work_sub"])

    def draw_footer(c, width: float):
        left = 17 * millimetre
        right = width - left
        c.setStrokeColor(red)
        c.setLineWidth(1.2)
        c.line(left, 25 * millimetre, right, 25 * millimetre)
        c.setFillColor(HexColor("#46494e"))
        c.setFont("Helvetica-Bold", 6.2)
        legal = (
            f"{labels['vat_footer']} {company['vat']}    "
            + (f"{labels['siret_footer']} {company['siret']}    " if company["siret"] else "")
            + f"{labels['capital_footer']} {company['capital']}"
        )
        c.drawCentredString(width / 2, 20.5 * millimetre, fitted(legal, "Helvetica-Bold", 6.2, 176 * millimetre))

        columns = (
            (left, ("GR 360 Flooring Systems", company["address"], company["postal_city"])),
            (left + 63 * millimetre, ("FRANCE : HSOLS France", "ALLEMAGNE : HSOLS Industriefussboden", "PORTUGAL : BetãoConcept")),
            (left + 127 * millimetre, ("ESPAGNE : MG SOLERAS Industriales", "MAROC : HSOLS Sarlau", "SUISSE : HSOLS Schweiz")),
        )
        for x, lines in columns:
            y = 15.5 * millimetre
            for line_index, line in enumerate(lines):
                font = "Helvetica-Bold" if x == left and line_index == 0 else "Helvetica"
                c.setFont(font, 6.2)
                c.setFillColor(muted)
                c.drawString(x, y, fitted(line, font, 6.2, 54 * millimetre))
                y -= 3.1 * millimetre

    writer = PdfWriter()
    for index, page in enumerate(pages):
        if index < terms_start:
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            overlay_stream = io.BytesIO()
            overlay_canvas = canvas.Canvas(overlay_stream, pagesize=(width, height))
            if index > 0:
                draw_header(overlay_canvas, width, height)
            draw_footer(overlay_canvas, width)
            overlay_canvas.save()
            overlay_page = PdfReader(io.BytesIO(overlay_stream.getvalue())).pages[0]
            page.merge_page(overlay_page, over=True)
        writer.add_page(page)
    if source.metadata:
        writer.add_metadata({key: value for key, value in source.metadata.items() if isinstance(value, str)})
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def get_budget_technical_options(feid: Any, user) -> dict[str, Any]:
    company = _company_for_user(feid, user)
    with pyodbc.connect(_phc_conn_str(company["phc_db"], company.get("phc_server", "")), timeout=20) as conn:
        cursor = conn.cursor()
        st_columns = _phc_columns(cursor, "ST")
        if not st_columns:
            raise BudgetsError("A tabela ST não existe no PHC desta empresa.")
        stfami_columns = _phc_columns(cursor, "STFAMI")
        if not {"ref", "nome", "txtqlook"}.issubset(stfami_columns):
            raise BudgetsError("A tabela STFAMI não tem a configuração necessária para selecionar componentes.")
        active_filter = "AND ISNULL(S.INACTIVO, 0) = 0" if "inactivo" in st_columns else ""
        component_designation_sql = _article_designation_expression(company, st_columns, "S")
        ouvrage_rows = _fetch_rows(
            cursor,
            f"""
            SELECT
                S.STSTAMP,
                S.REF,
                S.DESIGN,
                S.FAMILIA,
                S.UNIDADE,
                S.EPV1,
                S.EPCUSTO,
                S.PCUSTO,
                S.TABIVA
            FROM dbo.ST S
            WHERE UPPER(LTRIM(RTRIM(ISNULL(S.FAMILIA, '')))) = 'OUVRAGE'
              {active_filter}
            ORDER BY S.DESIGN, S.REF
            """,
            (),
        )
        component_family_rows = _fetch_rows(
            cursor,
            """
            SELECT
                F.STFAMISTAMP,
                F.REF,
                F.NOME,
                F.TXTQLOOK,
                (
                    SELECT COUNT_BIG(1)
                    FROM dbo.ST S
                    WHERE LTRIM(RTRIM(ISNULL(S.FAMILIA, ''))) = LTRIM(RTRIM(F.REF))
                ) AS ARTICLE_COUNT
            FROM dbo.STFAMI F
            WHERE LTRIM(RTRIM(ISNULL(F.TXTQLOOK, ''))) > ''
            ORDER BY F.TXTQLOOK, F.REF
            """,
            (),
        )
        component_rows = _fetch_rows(
            cursor,
            f"""
            SELECT
                S.STSTAMP,
                S.REF,
                {component_designation_sql} AS DESIGN,
                S.FAMILIA,
                S.UNIDADE,
                S.EPV1,
                S.EPCUSTO,
                S.PCUSTO,
                S.TABIVA,
                {_optional_column(st_columns, 'S', 'INACTIVO', 'INACTIVO', '0')},
                {_optional_column(st_columns, 'S', 'U_FORMULA', 'U_FORMULA', "''")},
                {_optional_column(st_columns, 'S', 'U_FORFAIT', 'U_FORFAIT', '0')}
            FROM dbo.ST S
            INNER JOIN dbo.STFAMI F
                    ON LTRIM(RTRIM(ISNULL(S.FAMILIA, ''))) = LTRIM(RTRIM(F.REF))
            WHERE LTRIM(RTRIM(ISNULL(F.TXTQLOOK, ''))) > ''
            ORDER BY F.TXTQLOOK, S.DESIGN, S.REF
            """,
            (),
        )
        formula_columns = _phc_columns(cursor, "U_FORMULAS")
        formula_rows = []
        if {"nome", "formula"}.issubset(formula_columns):
            formula_rows = _fetch_rows(
                cursor,
                "SELECT NOME, FORMULA FROM dbo.U_FORMULAS ORDER BY NOME",
                (),
            )
        unit_rows = []
        if _phc_columns(cursor, "DYTABLE"):
            unit_rows = _fetch_rows(
                cursor,
                """
                SELECT DISTINCT LTRIM(RTRIM(ISNULL(CAMPO, ''))) AS CAMPO
                FROM dbo.DYTABLE
                WHERE ENTITYNAME = 'st_unidade'
                  AND LTRIM(RTRIM(ISNULL(CAMPO, ''))) <> ''
                ORDER BY CAMPO
                """,
                (),
            )
    return {
        "company": company,
        "ouvrages": [_ouvrage_payload(row) for row in ouvrage_rows],
        "formulas": [_formula_payload(row) for row in formula_rows],
        "component_families": [_component_family_payload(row) for row in component_family_rows],
        "components": [_component_payload(row) for row in component_rows],
        "units": [_text_value(row.get("CAMPO")) for row in unit_rows],
    }


def _ouvrage_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "stamp": _text_value(row.get("STSTAMP")),
        "reference": _text_value(row.get("REF")),
        "designation": _text_value(row.get("DESIGN")),
        "family": _text_value(row.get("FAMILIA")),
        "unit": _text_value(row.get("UNIDADE")),
        "sale_price": _qty(row.get("EPV1")),
        "purchase_price": _qty(row.get("EPCUSTO")) or _qty(row.get("PCUSTO")),
        "vat_table": int(_number_value(row.get("TABIVA"))),
    }


def _formula_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": _text_value(row.get("NOME")),
        "expression": _text_value(row.get("FORMULA")),
    }


def _component_family_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "stamp": _text_value(row.get("STFAMISTAMP")),
        "reference": _text_value(row.get("REF")),
        "name": _text_value(row.get("NOME")) or _text_value(row.get("REF")),
        "lookup_order": _text_value(row.get("TXTQLOOK")),
        "article_count": int(_number_value(row.get("ARTICLE_COUNT"))),
    }


def _component_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "stamp": _text_value(row.get("STSTAMP")),
        "reference": _text_value(row.get("REF")),
        "designation": _text_value(row.get("DESIGN")),
        "family": _text_value(row.get("FAMILIA")),
        "unit": _text_value(row.get("UNIDADE")),
        "purchase_price": _qty(row.get("EPCUSTO")),
        "base_purchase_price": _qty(row.get("PCUSTO")),
        "sale_price": _qty(row.get("EPV1")),
        "vat_table": int(_number_value(row.get("TABIVA"))),
        "inactive": _bool_value(row.get("INACTIVO")),
        "formula": _text_value(row.get("U_FORMULA")),
        "forfait": _qty(row.get("U_FORFAIT")),
    }


def get_budget_line_oci(feid: Any, bistamp: Any, user) -> dict[str, Any]:
    company = _company_for_user(feid, user)
    clean_stamp = _text_value(bistamp)
    if not clean_stamp:
        raise BudgetsValidationError("Linha do orçamento não indicada.")

    with pyodbc.connect(_phc_conn_str(company["phc_db"], company.get("phc_server", "")), timeout=20) as conn:
        cursor = conn.cursor()
        bi_columns = _phc_columns(cursor, "BI")
        bi2_columns = _phc_columns(cursor, "BI2")
        visibility_sql, visibility_params = _budget_visibility_predicate(company, user, "B")
        line_rows = _fetch_rows(
            cursor,
            f"""
            SELECT
                I.BOSTAMP, I.BISTAMP, I.LORDEM, I.LITEM, I.REF, I.DESIGN, I.DGERAL,
                I.DESCONTO, I.DESC2, I.EDEBITO, I.ETTDEB, I.IVA, I.TABIVA,
                I.QTT, I.EPCUSTO, I.ECUSTOIND, I.TEMOCI, I.UNIDADE,
                {_optional_column(bi_columns, 'I', 'U_ESPESS', 'U_ESPESS', '0')},
                {_optional_column(bi_columns, 'I', 'U_ALT', 'U_ALT', '0')},
                {_optional_column(bi_columns, 'I', 'U_BLOQPV', 'U_BLOQPV', '0')},
                {_optional_column(bi_columns, 'I', 'U_BOMBA', 'U_BOMBA', '0')},
                {_optional_column(bi_columns, 'I', 'U_MO', 'U_MO', '0')},
                {_optional_column(bi_columns, 'I', 'U_OPCAO', 'U_OPCAO', '0')},
                {_optional_column(bi_columns, 'I', 'U_SIMULT', 'U_SIMULT', '0')},
                {_optional_column(bi_columns, 'I', 'U_PRORATA', 'U_PRORATA', '0')},
                {_optional_column(bi_columns, 'I', 'U_VARIANTE', 'U_VARIANTE', '0')},
                {_optional_column(bi2_columns, 'I2', 'QTTCOMPRA', 'QTTCOMPRA', '0')},
                {_optional_column(bi2_columns, 'I2', 'QTTENC', 'QTTENC', '0')},
                {_optional_column(bi2_columns, 'I2', 'U_APROVA', 'U_APROVA', '0')},
                {_optional_column(bi2_columns, 'I2', 'U_DESAPRO', 'U_DESAPRO', '0')}
            FROM dbo.BI I
            INNER JOIN dbo.BO B ON B.BOSTAMP = I.BOSTAMP
            LEFT JOIN dbo.BI2 I2 ON I2.BI2STAMP = I.BISTAMP
            WHERE I.BISTAMP = ?
              AND {visibility_sql}
            """,
            (clean_stamp, *visibility_params),
        )
        if not line_rows:
            raise BudgetsNotFoundError("Linha do orçamento não encontrada no PHC desta empresa.")

        oci_columns = _phc_columns(cursor, "OCI")
        if not oci_columns:
            raise BudgetsError("A tabela OCI não existe no PHC desta empresa.")
        oci_designation_sql = _oci_designation_fallback(oci_columns, "O")
        oci_rows = _fetch_rows(
            cursor,
            f"""
            SELECT
                O.OCISTAMP, O.BOSTAMP, O.BISTAMP, O.REF, O.DESIGN, O.FAMILIA,
                O.QTT, O.PCUSTO, O.EPCUSTO, O.UNIDADE, O.QTTTOTAL, O.RENDIM,
                O.NIVEL, O.LNIVEL, O.QTTFINAL,
                {_optional_column(oci_columns, 'O', 'U_FORFAIT', 'U_FORFAIT', '0')},
                {_optional_column(oci_columns, 'O', 'U_AREA', 'U_AREA', '0')},
                {_optional_column(oci_columns, 'O', 'U_ESPESS', 'U_ESPESS', '0')},
                {_optional_column(oci_columns, 'O', 'U_VOLUME', 'U_VOLUME', '0')},
                {_optional_column(oci_columns, 'O', 'U_PESO', 'U_PESO', '0')},
                {_optional_column(oci_columns, 'O', 'U_CONSUMO', 'U_CONSUMO', '0')},
                {_optional_column(oci_columns, 'O', 'U_COEF', 'U_COEF', '0')},
                {_optional_column(oci_columns, 'O', 'U_FORMULA', 'U_FORMULA', "''")},
                    {_optional_column(oci_columns, 'O', 'U_DESIGN', 'U_DESIGN', "''")},
                    {_optional_column(oci_columns, 'O', 'U_PVENDA', 'U_PVENDA', '0')},
                    {oci_designation_sql} AS [ARTICLE_DESIGN]
                FROM dbo.OCI O
                LEFT JOIN dbo.STFAMI F
                   ON LTRIM(RTRIM(ISNULL(F.REF, ''))) = LTRIM(RTRIM(ISNULL(O.FAMILIA, '')))
            WHERE O.BISTAMP = ?
              AND LTRIM(RTRIM(ISNULL(O.REF, ''))) <> 'XZ'
            ORDER BY ISNULL(F.TXTQLOOK, 'ZZ'), O.NIVEL, O.OCISTAMP
            """,
            (clean_stamp,),
        )
        parent = line_rows[0]
        parent_item = _text_value(parent.get("LITEM"))
        plus_value_rows = []
        if parent_item:
            plus_value_rows = _fetch_rows(
                cursor,
                f"""
                SELECT
                    I.BOSTAMP, I.BISTAMP, I.LORDEM, I.LITEM, I.REF, I.DESIGN, I.DGERAL,
                    I.FAMILIA, I.EDEBITO, I.UNIDADE,
                    {_optional_column(bi_columns, 'I', 'U_FORMULA', 'U_FORMULA', "''")},
                    {_optional_column(bi_columns, 'I', 'U_COEF', 'U_COEF', '0')},
                    {_optional_column(bi_columns, 'I', 'U_CONSUMO', 'U_CONSUMO', '0')}
                FROM dbo.BI I
                WHERE I.BOSTAMP = ?
                  AND UPPER(LTRIM(RTRIM(ISNULL(I.REF, '')))) IN ('PVL', 'MVL')
                  AND LTRIM(RTRIM(ISNULL(I.LITEM, ''))) LIKE ?
                ORDER BY I.LORDEM, I.LITEM, I.BISTAMP
                """,
                (_text_value(parent.get("BOSTAMP")), f"{parent_item}.%"),
            )
    return {
        "company": company,
        "line": _line_payload(line_rows[0]),
        "rows": [_oci_payload(row) for row in oci_rows]
        + [_plus_value_payload(row) for row in plus_value_rows],
        "study_cost": 0.1,
    }


def _oci_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "stamp": _text_value(row.get("OCISTAMP")),
        "budget_stamp": _text_value(row.get("BOSTAMP")),
        "line_stamp": _text_value(row.get("BISTAMP")),
        "reference": _text_value(row.get("REF")),
        "designation": (
            _text_value(row.get("U_DESIGN"))
            or _text_value(row.get("DESIGN"))
        ),
        "family": _text_value(row.get("FAMILIA")),
        "quantity": _qty(row.get("QTT")),
        "purchase_price": _qty(row.get("EPCUSTO")),
        "base_purchase_price": _qty(row.get("PCUSTO")),
        "unit": _text_value(row.get("UNIDADE")),
        "total_quantity": _qty(row.get("QTTTOTAL")),
        "yield": _qty(row.get("RENDIM")),
        "level": _qty(row.get("NIVEL")),
        "level_label": _text_value(row.get("LNIVEL")),
        "final_quantity": _qty(row.get("QTTFINAL")),
        "forfait": _qty(row.get("U_FORFAIT")),
        "area": _qty(row.get("U_AREA")),
        "thickness": _qty(row.get("U_ESPESS")),
        "volume": _qty(row.get("U_VOLUME")),
        "weight": _qty(row.get("U_PESO")),
        "consumption": _qty(row.get("U_CONSUMO")),
        "coefficient": _qty(row.get("U_COEF")),
        "formula": _text_value(row.get("U_FORMULA")),
        "sale_price": _qty(row.get("U_PVENDA")),
        "is_plus_value": False,
    }


def _plus_value_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "stamp": _text_value(row.get("BISTAMP")),
        "budget_stamp": _text_value(row.get("BOSTAMP")),
        "line_stamp": "",
        "reference": _text_value(row.get("REF")),
        "designation": _text_value(row.get("DGERAL")) or _text_value(row.get("DESIGN")),
        "family": _text_value(row.get("FAMILIA")),
        "quantity": 0.0,
        "purchase_price": _qty(row.get("EDEBITO")),
        "base_purchase_price": 0.0,
        "unit": _text_value(row.get("UNIDADE")),
        "total_quantity": 0.0,
        "yield": 0.0,
        "level": _number_value(row.get("LORDEM")),
        "level_label": _text_value(row.get("LITEM")),
        "final_quantity": 0.0,
        "forfait": 0.0,
        "area": 0.0,
        "thickness": 0.0,
        "volume": 0.0,
        "weight": 0.0,
        "consumption": _qty(row.get("U_CONSUMO")),
        "coefficient": _qty(row.get("U_COEF")),
        "formula": _text_value(row.get("U_FORMULA")) or "PRIX FIXE",
        "sale_price": _qty(row.get("EDEBITO")),
        "is_plus_value": True,
    }


def _parse_budget_write_date(value: Any) -> date:
    raw = _text_value(value)
    if not raw:
        return date.today()
    try:
        return datetime.strptime(raw[:10], "%Y-%m-%d").date()
    except ValueError as exc:
        raise BudgetsValidationError("Data do orçamento inválida.") from exc


def _phc_currency(value: Any) -> str:
    code = _text_value(value).upper().replace("€", "EUR")
    return "EURO" if code in {"", "EUR", "EURO", "EUROS"} else code[:10]


def _column_lengths(cursor, table_name: str) -> dict[str, int | None]:
    rows = _fetch_rows(
        cursor,
        """
        SELECT LOWER(COLUMN_NAME) AS COLUMN_NAME, CHARACTER_MAXIMUM_LENGTH AS MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = ?
        """,
        (table_name,),
    )
    return {
        _text_value(row.get("COLUMN_NAME")): (
            int(row.get("MAXIMUM_LENGTH")) if row.get("MAXIMUM_LENGTH") not in (None, -1) else None
        )
        for row in rows
    }


def _limited(value: Any, lengths: dict[str, int | None], column: str) -> str:
    text = _text_value(value)
    maximum = lengths.get(column.lower())
    return text[:maximum] if maximum and maximum > 0 else text


def _phc_update(cursor, table_name: str, values: dict[str, Any], key_column: str, key_value: Any) -> int:
    columns = _phc_columns(cursor, table_name)
    filtered = {
        key: value
        for key, value in values.items()
        if key.lower() in columns and key.lower() != key_column.lower()
    }
    if not filtered:
        raise BudgetsError(f"Sem colunas válidas para atualizar {table_name}.")
    cursor.execute(
        f"UPDATE dbo.[{table_name}] SET "
        + ", ".join(f"[{key}] = ?" for key in filtered)
        + f" WHERE [{key_column}] = ?",
        [*filtered.values(), key_value],
    )
    return int(cursor.rowcount or 0)


def _next_budget_number(cursor, ndos: int, year: int) -> int:
    cursor.execute(
        """
        SELECT ISNULL(MAX(TRY_CONVERT(int, OBRANO)), 0) + 1
        FROM dbo.BO WITH (UPDLOCK, HOLDLOCK)
        WHERE NDOS = ? AND BOANO = ?
        """,
        ndos,
        year,
    )
    return int(cursor.fetchone()[0] or 1)


def _line_order_for_write(line: dict[str, Any], index: int) -> int:
    supplied = int(_number_value(line.get("order")))
    if supplied > 0:
        return supplied
    label = _text_value(line.get("item_label") or line.get("item") or index)
    parts = [int(part) for part in label.split(".") if part.isdigit()]
    if not parts:
        return index * 10000
    return parts[0] * 10000 + sum(part * max(1, 100 // (10 ** offset)) for offset, part in enumerate(parts[1:]))


def _write_client(cursor, number: Any, establishment: Any) -> dict[str, Any]:
    customer_number = int(_number_value(number))
    customer_establishment = int(_number_value(establishment))
    if customer_number <= 0:
        raise BudgetsValidationError("Selecione um cliente válido.")
    columns = _phc_columns(cursor, "CL")
    rows = _fetch_rows(
        cursor,
        f"""
        SELECT TOP 1 CLSTAMP, NO, ESTAB, NOME, NCONT, MORADA, LOCAL, CODPOST, ZONA,
               TELEFONE, CONTACTO, EMAIL, VENDEDOR, VENDNM, PNCONT, PAIS,
               COBRANCA, TPSTAMP, TPDESC, LANG,
               {_optional_column(columns, 'CL', 'TABIVA', 'VAT_TABLE', '0')}
        FROM dbo.CL WITH (UPDLOCK, HOLDLOCK)
        WHERE NO = ? AND ESTAB = ? AND ISNULL(INACTIVO, 0) = 0
        """,
        (customer_number, customer_establishment),
    )
    if not rows:
        raise BudgetsValidationError("O cliente selecionado já não está disponível no PHC.")
    return rows[0]


def _write_salesperson(cursor, value: Any) -> dict[str, Any]:
    number = int(_number_value(value))
    if number <= 0:
        return {"CM": 0, "CMDESC": ""}
    rows = _fetch_rows(
        cursor,
        """
        SELECT TOP 1 CM, CMDESC
        FROM dbo.CM3 WITH (UPDLOCK, HOLDLOCK)
        WHERE CM = ? AND LTRIM(RTRIM(ISNULL(CMDESC, ''))) <> ''
        """,
        (number,),
    )
    if not rows:
        raise BudgetsValidationError("O comercial selecionado já não está disponível no PHC.")
    return rows[0]


def _write_country(cursor, client: dict[str, Any]) -> tuple[str, str]:
    code = _text_value(client.get("PNCONT"))
    if not code:
        return "", ""
    rows = _fetch_rows(
        cursor,
        """
        SELECT TOP 1 NOME
        FROM dbo.PAISES
        WHERE UPPER(LTRIM(RTRIM(ISNULL(NOMEABRV, '')))) = UPPER(?)
           OR UPPER(LTRIM(RTRIM(ISNULL(NOMEABRVSAFT, '')))) = UPPER(?)
        """,
        (code, code),
    )
    return code, (_text_value(rows[0].get("NOME")) if rows else "")


def _approval_credit_payload(row: dict[str, Any], document_total: Any) -> dict[str, Any]:
    insurance = _write_money(row.get("U_SEGURO"))
    credit_limit = _write_money(row.get("EPLAFOND"))
    account_balance = _write_money(row.get("ESALDO"))
    open_execution = _write_money(row.get("BO_ABERTO"))
    budget_total = _write_money(document_total)
    total_credit = _write_money(insurance + credit_limit)
    open_total = _write_money(account_balance + open_execution)
    available = _write_money(total_credit - open_total - budget_total)
    return {
        "insurance": float(insurance),
        "credit_limit": float(credit_limit),
        "total_credit": float(total_credit),
        "account_balance": float(account_balance),
        "open_execution": float(open_execution),
        "budget_total": float(budget_total),
        "open_total": float(open_total),
        "available": float(available),
    }


def _approval_has_credit(credit: dict[str, Any], override_limit: Any = 0) -> bool:
    available = _write_money(credit.get("available"))
    required = _write_money(
        _decimal(credit.get("open_total")) + _decimal(credit.get("budget_total"))
    )
    return available >= 0 or _write_money(override_limit) > required


def _phc_user_identity(cursor, user) -> tuple[str, str]:
    login = _text_value(getattr(user, "LOGIN", ""))
    rows = _fetch_rows(
        cursor,
        """
        SELECT TOP 1
            LTRIM(RTRIM(ISNULL(USERCODE, ''))) AS USERCODE,
            LTRIM(RTRIM(ISNULL(INICIAIS, ''))) AS INICIAIS
        FROM dbo.US
        WHERE UPPER(LTRIM(RTRIM(ISNULL(USERCODE, '')))) = UPPER(?)
        ORDER BY ISNULL(INACTIVO, 0), USERNO
        """,
        (login,),
    )
    if not rows:
        return login, _user_inis(user)
    return _text_value(rows[0].get("USERCODE")) or login, _text_value(rows[0].get("INICIAIS")) or _user_inis(user)


def _approval_override_limit(cursor, usercode: str) -> Decimal:
    try:
        rows = _fetch_rows(
            cursor,
            """
            SELECT TOP 1 ISNULL(PLAFOND, 0) AS PLAFOND
            FROM HSOLS_MASTER.dbo.U_APROPLAF
            WHERE UPPER(LTRIM(RTRIM(ISNULL(USERCODE, '')))) = UPPER(?)
            """,
            (usercode,),
        )
    except pyodbc.Error:
        return Decimal("0")
    return _write_money(rows[0].get("PLAFOND")) if rows else Decimal("0")


def set_budget_approval(feid: Any, bostamp: str, approved: bool, user) -> dict[str, Any]:
    """Approve/unapprove a PHC Devis using the same credit rules as the PHC button."""
    company = _company_for_user(feid, user)
    clean_stamp = _text_value(bostamp)
    if not clean_stamp:
        raise BudgetsValidationError("Orçamento não indicado.")
    target_approved = _bool_value(approved)
    now_sql = datetime.now()
    audit_date = now_sql.date()
    audit_time = now_sql.strftime("%H:%M:%S")

    with pyodbc.connect(_phc_conn_str(company["phc_db"], company.get("phc_server", "")), timeout=30) as conn:
        conn.autocommit = False
        cursor = conn.cursor()
        try:
            visibility_sql, visibility_params = _budget_visibility_predicate(company, user, "B")
            rows = _fetch_rows(
                cursor,
                f"""
                SELECT TOP 1
                    B.BOSTAMP, B.NDOS, B.NMDOS, B.NO, B.ESTAB, B.ETOTALDEB,
                    B.APROVADO, B.FECHADA,
                    ISNULL(B2.ADJUDICADO, 0) AS ADJUDICADO,
                    ISNULL(B2.ANULADO, 0) AS ANULADO
                FROM dbo.BO B WITH (UPDLOCK, HOLDLOCK)
                LEFT JOIN dbo.BO2 B2 WITH (UPDLOCK, HOLDLOCK)
                       ON B2.BO2STAMP = B.BOSTAMP
                WHERE B.BOSTAMP = ?
                  AND {visibility_sql}
                """,
                (clean_stamp, *visibility_params),
            )
            if not rows:
                raise BudgetsNotFoundError("Orçamento não encontrado no PHC desta empresa.")
            budget = rows[0]
            if _series_name_key(budget.get("NMDOS")) != "devis":
                raise BudgetsValidationError("A aprovação só está disponível para dossiers Devis.")
            if any(_bool_value(budget.get(field)) for field in ("FECHADA", "ADJUDICADO", "ANULADO")):
                raise BudgetsValidationError("O orçamento está fechado, adjudicado ou anulado e não pode ser alterado.")
            if target_approved == _bool_value(budget.get("APROVADO")):
                conn.rollback()
                return {"bostamp": clean_stamp, "approved": target_approved, "credit": None}

            usercode, user_inis = _phc_user_identity(cursor, user)
            credit: dict[str, Any] | None = None
            if target_approved and not _bool_value(budget.get("APROVADO")):
                credit_rows = _fetch_rows(
                    cursor,
                    """
                    SELECT TOP 1
                        ISNULL(C.U_SEGURO, 0) AS U_SEGURO,
                        ISNULL(C.EPLAFOND, 0) AS EPLAFOND,
                        ISNULL(C.ESALDO, 0) AS ESALDO,
                        ISNULL(EXECUTION.BO_ABERTO, 0) AS BO_ABERTO
                    FROM dbo.CL C
                    OUTER APPLY (
                        SELECT ROUND(ISNULL(SUM(
                            CASE WHEN ISNULL(I.QTT, 0) - ISNULL(I.QTT2, 0) < 0 THEN 0
                                 ELSE ISNULL(I.QTT, 0) - ISNULL(I.QTT2, 0) END
                            * ISNULL(I.EDEBITO, 0)
                        ), 0), 2) AS BO_ABERTO
                        FROM dbo.BO E
                        LEFT JOIN dbo.BI I ON I.BOSTAMP = E.BOSTAMP
                        WHERE E.NO = C.NO
                          AND E.ESTAB = C.ESTAB
                          AND E.NDOS = 122
                          AND ISNULL(E.FECHADA, 0) = 0
                    ) EXECUTION
                    WHERE C.NO = ? AND C.ESTAB = ?
                    """,
                    (int(_number_value(budget.get("NO"))), int(_number_value(budget.get("ESTAB")))),
                )
                if not credit_rows:
                    raise BudgetsValidationError("O cliente do orçamento já não está disponível no PHC.")
                credit = _approval_credit_payload(credit_rows[0], budget.get("ETOTALDEB"))
                override_limit = _approval_override_limit(cursor, usercode)
                credit["override_limit"] = float(override_limit)
                if not _approval_has_credit(credit, override_limit):
                    raise BudgetsCreditLimitError("Não existe plafond suficiente para aprovar este orçamento.", credit)

            _phc_update(
                cursor,
                "BO",
                {
                    "aprovado": 1 if target_approved else 0,
                    "usrinis": user_inis,
                    "usrdata": audit_date,
                    "usrhora": audit_time,
                },
                "BOSTAMP",
                clean_stamp,
            )
            _phc_update(
                cursor,
                "BO3",
                {
                    "u_aprovdat": now_sql if target_approved else PHC_ZERO_DATE,
                    "u_aprovusr": user_inis if target_approved else "",
                    "usrdata": audit_date,
                    "usrhora": audit_time,
                },
                "BO3STAMP",
                clean_stamp,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    return {"bostamp": clean_stamp, "approved": target_approved, "credit": credit}


def _line_technical_rows(line: dict[str, Any]) -> list[dict[str, Any]]:
    rows = line.get("_ociRows")
    if not isinstance(rows, list):
        rows = line.get("technical_lines")
    return [row for row in (rows or []) if isinstance(row, dict)]


def save_budget(payload: dict[str, Any], user) -> dict[str, Any]:
    """Create or update a PHC Devis and all of its dependent records atomically."""
    if not isinstance(payload, dict):
        raise BudgetsValidationError("Dados do orçamento inválidos.")
    company = _company_for_user(payload.get("feid"), user)
    header = payload.get("header") or {}
    if not isinstance(header, dict):
        raise BudgetsValidationError("Cabeçalho do orçamento inválido.")
    payload_lines = payload.get("lines") or []
    if not isinstance(payload_lines, list):
        raise BudgetsValidationError("Linhas do orçamento inválidas.")

    clean_bostamp = _text_value(payload.get("bostamp") or header.get("bostamp"))
    creating = not clean_bostamp
    dataobra = _parse_budget_write_date(header.get("date"))
    now_sql = datetime.now()
    audit_date = now_sql.date()
    audit_time = now_sql.strftime("%H:%M:%S")
    user_inis = _user_inis(user)
    conn_str = _phc_conn_str(company["phc_db"], company.get("phc_server", ""))

    with pyodbc.connect(conn_str, timeout=30) as conn:
        conn.autocommit = False
        cursor = conn.cursor()
        try:
            series = _series_rows(cursor)
            ndos = _parse_ndos(payload.get("ndos") or header.get("ndos"), series)
            selected_series = next(row for row in series if int(row.get("ndos") or 0) == ndos)
            nmdos = _text_value(selected_series.get("name"))

            existing_header: dict[str, Any] | None = None
            existing_line_stamps: set[str] = set()
            if creating:
                bostamp = _new_stamp()
                boano = dataobra.year
                obrano = _next_budget_number(cursor, ndos, boano)
            else:
                visibility_sql, visibility_params = _budget_visibility_predicate(company, user, "B")
                rows = _fetch_rows(
                    cursor,
                    f"""
                    SELECT B.BOSTAMP, B.NDOS, B.NMDOS, B.OBRANO, B.BOANO,
                           B.USRDATA, B.USRHORA, B.APROVADO, B.FECHADA,
                           ISNULL(B2.ADJUDICADO, 0) AS ADJUDICADO,
                           ISNULL(B2.ANULADO, 0) AS ANULADO
                    FROM dbo.BO B WITH (UPDLOCK, HOLDLOCK)
                    LEFT JOIN dbo.BO2 B2 WITH (UPDLOCK, HOLDLOCK)
                           ON B2.BO2STAMP = B.BOSTAMP
                    WHERE B.BOSTAMP = ?
                      AND {visibility_sql}
                    """,
                    (clean_bostamp, *visibility_params),
                )
                if not rows:
                    raise BudgetsNotFoundError("O orçamento já não existe no PHC desta empresa.")
                existing_header = rows[0]
                if not _budget_can_be_edited(existing_header):
                    raise BudgetsConflictError(
                        "O orçamento está fechado, adjudicado ou anulado e não pode ser alterado."
                    )
                current_revision = _revision_token(existing_header.get("USRDATA"), existing_header.get("USRHORA"))
                requested_revision = _text_value(header.get("revision"))
                if not requested_revision or requested_revision != current_revision:
                    raise BudgetsConflictError(
                        "O orçamento foi alterado por outro utilizador. Atualize os dados antes de voltar a gravar."
                    )
                bostamp = clean_bostamp
                ndos = int(_number_value(existing_header.get("NDOS")))
                nmdos = _text_value(existing_header.get("NMDOS"))
                obrano = int(_number_value(existing_header.get("OBRANO")))
                boano = int(_number_value(existing_header.get("BOANO")))
                existing_line_stamps = {
                    _text_value(row.get("BISTAMP"))
                    for row in _fetch_rows(
                        cursor,
                        "SELECT BISTAMP FROM dbo.BI WITH (UPDLOCK, HOLDLOCK) WHERE BOSTAMP = ?",
                        (bostamp,),
                    )
                }

            client = _write_client(
                cursor,
                header.get("client_number"),
                header.get("establishment"),
            )
            salesperson = _write_salesperson(cursor, header.get("salesperson_number"))
            country_code, country_name = _write_country(cursor, client)
            currency = _phc_currency(header.get("currency"))

            bo_lengths = _column_lengths(cursor, "BO")
            bo2_lengths = _column_lengths(cursor, "BO2")
            bi_lengths = _column_lengths(cursor, "BI")
            bi2_lengths = _column_lengths(cursor, "BI2")
            oci_lengths = _column_lengths(cursor, "OCI")
            tax_rates = {
                int(_number_value(row.get("tabiva"))): _decimal(row.get("taxaiva"))
                for row in _phc_tax_rates(cursor)
                if int(_number_value(row.get("tabiva"))) > 0
            }
            default_tax_code = 2 if 2 in tax_rates else (next(iter(tax_rates), 0))
            client_tax_code = int(_number_value(client.get("VAT_TABLE")))
            if client_tax_code not in tax_rates:
                client_tax_code = 0

            references = sorted(
                {
                    _text_value(line.get("reference")).upper()
                    for line in payload_lines
                    if isinstance(line, dict) and _text_value(line.get("reference"))
                }
            )
            article_taxes: dict[str, int] = {}
            if references:
                placeholders = ", ".join("?" for _ in references)
                article_taxes = {
                    _text_value(row.get("REF")).upper(): int(_number_value(row.get("TABIVA")))
                    for row in _fetch_rows(
                        cursor,
                        f"SELECT REF, TABIVA FROM dbo.ST WHERE UPPER(LTRIM(RTRIM(REF))) IN ({placeholders})",
                        tuple(references),
                    )
                }

            prepared_lines: list[dict[str, Any]] = []
            used_stamps: set[str] = set()
            tax_totals: dict[int, dict[str, Decimal]] = {
                code: {"base": Decimal("0"), "iva": Decimal("0"), "rate": rate}
                for code, rate in tax_rates.items()
            }
            for index, raw_line in enumerate(payload_lines, start=1):
                if not isinstance(raw_line, dict):
                    raise BudgetsValidationError(f"Linha {index} inválida.")
                supplied_stamp = _text_value(raw_line.get("bistamp"))
                if supplied_stamp and supplied_stamp in existing_line_stamps:
                    bistamp = supplied_stamp
                    line_exists = True
                elif not supplied_stamp or supplied_stamp.lower().startswith("draft-"):
                    bistamp = _new_stamp()
                    line_exists = False
                else:
                    raise BudgetsValidationError(f"A linha {index} não pertence a este orçamento.")
                if bistamp in used_stamps:
                    raise BudgetsValidationError("Existem linhas duplicadas no orçamento.")
                used_stamps.add(bistamp)

                reference = _limited(raw_line.get("reference"), bi_lengths, "ref")
                item_label = _limited(raw_line.get("item_label") or raw_line.get("item") or index, bi_lengths, "litem")
                designation = _limited(raw_line.get("designation"), bi_lengths, "design")
                description = _limited(raw_line.get("description") or designation, bi_lengths, "dgeral")
                quantity = _decimal(raw_line.get("quantity")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
                unit_price = _write_money(raw_line.get("unit_price"))
                discount_1 = _decimal(raw_line.get("discount_1"))
                discount_2 = _decimal(raw_line.get("discount_2"))
                variant = _bool_value(raw_line.get("variant"))
                option = _bool_value(raw_line.get("option"))
                excluded = variant or option
                if excluded:
                    discount_1 = Decimal("100")
                factor = (Decimal("1") - discount_1 / Decimal("100")) * (
                    Decimal("1") - discount_2 / Decimal("100")
                )
                total = _write_money(unit_price * quantity * factor)
                technical_unit_cost = _write_money(
                    raw_line.get("_technical_unit_cost")
                    if raw_line.get("_technical_unit_cost") is not None
                    else raw_line.get("unit_cost")
                )
                stored_unit_cost = Decimal("0") if excluded else technical_unit_cost
                stored_cost_total = _write_money(stored_unit_cost * quantity)
                vat_code = int(_number_value(raw_line.get("vat_table")))
                if vat_code <= 0:
                    article_tax_code = article_taxes.get(reference.upper(), 0)
                    vat_code = client_tax_code or (
                        article_tax_code if article_tax_code in tax_rates else default_tax_code
                    )
                vat_rate = tax_rates.get(vat_code, _decimal(raw_line.get("vat_rate")))
                if vat_code not in tax_totals:
                    tax_totals[vat_code] = {"base": Decimal("0"), "iva": Decimal("0"), "rate": vat_rate}
                tax_totals[vat_code]["base"] += total
                tax_totals[vat_code]["iva"] += total * vat_rate / Decimal("100")

                technical_rows = _line_technical_rows(raw_line)
                non_plus_rows = [
                    row for row in technical_rows
                    if _text_value(row.get("reference")).upper() not in {"PVL", "MVL", "XZ"}
                    and not _bool_value(row.get("is_plus_value"))
                ]
                prepared_lines.append(
                    {
                        "source": raw_line,
                        "bistamp": bistamp,
                        "exists": line_exists,
                        "reference": reference,
                        "designation": designation,
                        "description": description,
                        "item_label": item_label,
                        "order": _line_order_for_write(raw_line, index),
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "total": Decimal("0") if excluded else total,
                        "unit_cost": stored_unit_cost,
                        "cost_total": stored_cost_total,
                        "discount_1": discount_1,
                        "discount_2": discount_2,
                        "vat_code": vat_code,
                        "vat_rate": vat_rate,
                        "variant": variant,
                        "option": option,
                        "technical_rows": non_plus_rows,
                        "has_technical": _bool_value(raw_line.get("has_technical_detail")) or bool(non_plus_rows),
                    }
                )

            for totals in tax_totals.values():
                totals["base"] = _write_money(totals["base"])
                totals["iva"] = _write_money(totals["iva"])
            total_deb = _write_money(sum((line["total"] for line in prepared_lines), Decimal("0")))
            total_cost = _write_money(sum((line["cost_total"] for line in prepared_lines), Decimal("0")))
            total_quantity = sum((line["quantity"] for line in prepared_lines), Decimal("0"))
            total_vat = _write_money(sum((row["iva"] for row in tax_totals.values()), Decimal("0")))
            margin_value = _write_money(total_deb - total_cost)
            margin_percentage = (
                margin_value / total_deb * Decimal("100") if total_deb else Decimal("0")
            )

            customer_number = int(_number_value(client.get("NO")))
            customer_establishment = int(_number_value(client.get("ESTAB")))
            customer_name = _limited(client.get("NOME"), bo_lengths, "nome")
            work_name = _limited(header.get("work_name"), bo_lengths, "trab1")
            work_locality = _limited(header.get("locality"), bo_lengths, "obranome")
            attention = _limited(header.get("attention"), bo_lengths, "serie")
            salesperson_number = int(_number_value(salesperson.get("CM")))
            salesperson_name = _limited(salesperson.get("CMDESC"), bo_lengths, "vendnm")

            bo_values: dict[str, Any] = {
                "nmdos": nmdos,
                "ndos": ndos,
                "obrano": obrano,
                "boano": boano,
                "dataobra": dataobra,
                "nome": customer_name,
                "no": customer_number,
                "estab": customer_establishment,
                "ncont": _limited(client.get("NCONT"), bo_lengths, "ncont"),
                "morada": _limited(client.get("MORADA"), bo_lengths, "morada"),
                "local": _limited(client.get("LOCAL"), bo_lengths, "local"),
                "codpost": _limited(client.get("CODPOST"), bo_lengths, "codpost"),
                "zona": _limited(client.get("ZONA"), bo_lengths, "zona"),
                "trab1": work_name,
                "obranome": work_locality,
                "vendedor": salesperson_number,
                "vendnm": salesperson_name,
                "serie": attention,
                "moeda": currency,
                "etotaldeb": total_deb,
                "totaldeb": _phc_value(total_deb),
                "sdeb4": _phc_value(total_deb),
                "esdeb4": total_deb,
                "sqtt14": total_quantity,
                "bo_2tvall": _phc_value(total_deb),
                "ebo_2tvall": total_deb,
                "bo_totp2": _phc_value(total_deb),
                "ebo_totp2": total_deb,
                "ecusto": total_cost,
                "custo": _phc_value(total_cost),
                "u_emargem": margin_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                "u_margem": margin_percentage.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                # Any update, including one to an approved budget, reopens the
                # document and requires a fresh approval in PHC.
                "aprovado": 0,
                "usrinis": user_inis,
                "usrdata": audit_date,
                "usrhora": audit_time,
            }
            if creating:
                bo_values.update(
                    {
                        "bostamp": bostamp,
                        "dataopen": date.today(),
                        "datafecho": PHC_ZERO_DATE,
                        "fechada": 0,
                        "aprovado": 0,
                        "ocupacao": int(_number_value(selected_series.get("occupation"))),
                        "memissao": currency,
                        "cobranca": _limited(client.get("COBRANCA"), bo_lengths, "cobranca"),
                        "tpstamp": _limited(client.get("TPSTAMP"), bo_lengths, "tpstamp"),
                        "tpdesc": _limited(client.get("TPDESC"), bo_lengths, "tpdesc"),
                        "lang": _limited(client.get("LANG"), bo_lengths, "lang"),
                        "ousrinis": user_inis,
                        "ousrdata": audit_date,
                        "ousrhora": audit_time,
                    }
                )

            bo_columns = _phc_columns(cursor, "BO")
            for column in bo_columns:
                if re.fullmatch(r"e?bo\d+[12]_(?:bins|iva)", column):
                    bo_values[column] = Decimal("0")
            for code, totals in tax_totals.items():
                if code <= 0:
                    continue
                for prefix, value in (
                    (f"ebo{code}2_bins", totals["base"]),
                    (f"ebo{code}2_iva", totals["iva"]),
                    (f"bo{code}2_bins", _phc_value(totals["base"])),
                    (f"bo{code}2_iva", _phc_value(totals["iva"])),
                ):
                    if prefix in bo_columns:
                        bo_values[prefix] = value

            bo2_values = {
                "bo2stamp": bostamp,
                "processo": _limited(header.get("process"), bo2_lengths, "processo"),
                "area": _limited(header.get("area"), bo2_lengths, "area"),
                "armazem": int(_number_value(selected_series.get("warehouse"))) or 1,
                "morada": _limited(client.get("MORADA"), bo2_lengths, "morada"),
                "local": _limited(client.get("LOCAL"), bo2_lengths, "local"),
                "codpost": _limited(client.get("CODPOST"), bo2_lengths, "codpost"),
                "cladrszona": _limited(client.get("ZONA"), bo2_lengths, "cladrszona"),
                "telefone": _limited(client.get("TELEFONE"), bo2_lengths, "telefone"),
                "contacto": _limited(client.get("CONTACTO"), bo2_lengths, "contacto"),
                "email": _limited(client.get("EMAIL"), bo2_lengths, "email"),
                "etotalciva": (total_deb + total_vat).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                "usrinis": user_inis,
                "usrdata": now_sql,
                "usrhora": audit_time,
            }
            if creating:
                bo2_values.update(
                    {
                        "adjudicado": 0,
                        "orcamento": 0,
                        "anulado": 0,
                        "autotipo": 1,
                        "pdtipo": 1,
                        "tiposaft": _limited(selected_series.get("saft_type"), bo2_lengths, "tiposaft"),
                        "idserie": _limited(selected_series.get("series_id"), bo2_lengths, "idserie"),
                        "carga": _limited("N/Instalações", bo2_lengths, "carga"),
                        "ousrinis": user_inis,
                        "ousrdata": now_sql,
                        "ousrhora": audit_time,
                    }
                )
            bo3_values = {
                "bo3stamp": bostamp,
                "codpais": country_code,
                "descpais": country_name,
                "u_aprovdat": PHC_ZERO_DATE,
                "u_aprovusr": "",
                "usrinis": user_inis,
                "usrdata": audit_date,
                "usrhora": audit_time,
            }
            if creating:
                bo3_values.update(
                    {
                        "u_aprovdat": PHC_ZERO_DATE,
                        "u_aprovusr": "",
                        "taxpointdt": date.today(),
                        "arquivadodigital": 0,
                        "ousrinis": user_inis,
                        "ousrdata": now_sql,
                        "ousrhora": audit_time,
                    }
                )

            if creating:
                _phc_insert(cursor, "BO2", bo2_values)
                _phc_insert(cursor, "BO3", bo3_values)
            else:
                if not _phc_update(cursor, "BO2", bo2_values, "BO2STAMP", bostamp):
                    _phc_insert(cursor, "BO2", bo2_values)
                if not _phc_update(cursor, "BO3", bo3_values, "BO3STAMP", bostamp):
                    _phc_insert(cursor, "BO3", bo3_values)

            cursor.execute("DELETE FROM dbo.BOT WHERE BOSTAMP = ?", bostamp)
            for code, totals in sorted(tax_totals.items()):
                rate = totals.get("rate", Decimal("0"))
                _phc_insert(
                    cursor,
                    "BOT",
                    {
                        "botstamp": _new_stamp(),
                        "bostamp": bostamp,
                        "codigo": code,
                        "taxa": rate,
                        "ebaseinc": totals["base"],
                        "baseinc": _phc_value(totals["base"]),
                        "evalor": totals["iva"],
                        "valor": _phc_value(totals["iva"]),
                        "ousrinis": user_inis,
                        "ousrdata": audit_date,
                        "ousrhora": audit_time,
                        "usrinis": user_inis,
                        "usrdata": audit_date,
                        "usrhora": audit_time,
                    },
                )

            obsolete = existing_line_stamps - used_stamps
            if obsolete:
                placeholders = ", ".join("?" for _ in obsolete)
                values = tuple(obsolete)
                cursor.execute(f"DELETE FROM dbo.OCI WHERE BISTAMP IN ({placeholders})", values)
                cursor.execute(f"DELETE FROM dbo.BI2 WHERE BI2STAMP IN ({placeholders})", values)
                cursor.execute(f"DELETE FROM dbo.BI WHERE BISTAMP IN ({placeholders})", values)

            for prepared in prepared_lines:
                source = prepared["source"]
                bistamp = prepared["bistamp"]
                line_values = {
                    "bistamp": bistamp,
                    "bostamp": bostamp,
                    "nmdos": nmdos,
                    "ndos": ndos,
                    "obrano": obrano,
                    "dataobra": dataobra,
                    "lordem": prepared["order"],
                    "litem": prepared["item_label"],
                    "ref": prepared["reference"],
                    "design": prepared["designation"],
                    "dgeral": prepared["description"],
                    "familia": _limited(source.get("family"), bi_lengths, "familia"),
                    "qtt": prepared["quantity"],
                    "qtt2": 0,
                    "unidade": _limited(source.get("unit"), bi_lengths, "unidade"),
                    "edebito": prepared["unit_price"],
                    "ettdeb": prepared["total"],
                    "epcusto": prepared["unit_cost"],
                    "ecustoind": prepared["unit_cost"],
                    "desconto": prepared["discount_1"],
                    "desc2": prepared["discount_2"],
                    "iva": prepared["vat_rate"],
                    "tabiva": prepared["vat_code"],
                    "ivaincl": 0,
                    "armazem": int(_number_value(selected_series.get("warehouse"))) or 1,
                    "stipo": 4,
                    "no": customer_number,
                    "estab": customer_establishment,
                    "nome": customer_name,
                    "serie": attention,
                    "rdata": dataobra,
                    "obranome": work_locality,
                    "morada": _limited(client.get("MORADA"), bi_lengths, "morada"),
                    "local": _limited(client.get("LOCAL"), bi_lengths, "local"),
                    "codpost": _limited(client.get("CODPOST"), bi_lengths, "codpost"),
                    "zona": _limited(client.get("ZONA"), bi_lengths, "zona"),
                    "vendedor": salesperson_number,
                    "vendnm": salesperson_name,
                    "ccusto": _limited(header.get("cost_center"), bi_lengths, "ccusto"),
                    "temoci": int(prepared["has_technical"]),
                    "u_espess": _decimal(source.get("thickness")),
                    "u_bloqpv": 1 if prepared["has_technical"] else _bool_value(source.get("blocked_price")),
                    "u_simult": _bool_value(source.get("simultaneous")),
                    "u_bomba": _bool_value(source.get("pump")),
                    "u_mo": _bool_value(source.get("labour")),
                    "u_alt": prepared["variant"],
                    "u_opcao": prepared["option"],
                    "u_itemalt": _limited(source.get("u_itemalt"), bi_lengths, "u_itemalt"),
                    "u_formula": _limited(source.get("u_formula"), bi_lengths, "u_formula"),
                    "u_coef": _decimal(source.get("coefficient")),
                    "u_consumo": _decimal(source.get("consumption")),
                    "u_prorata": _decimal(
                        source.get("pro_rata_percentage")
                        if source.get("pro_rata_percentage") is not None
                        else (source.get("discount_2") if _bool_value(source.get("pro_rata")) else 0)
                    ),
                    "usrinis": user_inis,
                    "usrdata": audit_date,
                    "usrhora": audit_time,
                }
                if not prepared["exists"]:
                    line_values.update(
                        {
                            "fechada": 0,
                            "dataopen": date.today(),
                            "datafecho": PHC_ZERO_DATE,
                            "ousrinis": user_inis,
                            "ousrdata": audit_date,
                            "ousrhora": audit_time,
                        }
                    )
                    _phc_insert(cursor, "BI", line_values)
                else:
                    _phc_update(cursor, "BI", line_values, "BISTAMP", bistamp)

                bi2_values = {
                    "bi2stamp": bistamp,
                    "bostamp": bostamp,
                    "morada": _limited(client.get("MORADA"), bi2_lengths, "morada"),
                    "local": _limited(client.get("LOCAL"), bi2_lengths, "local"),
                    "codpost": _limited(client.get("CODPOST"), bi2_lengths, "codpost"),
                    "cladrszona": _limited(client.get("ZONA"), bi2_lengths, "cladrszona"),
                    "telefone": _limited(client.get("TELEFONE"), bi2_lengths, "telefone"),
                    "contacto": _limited(client.get("CONTACTO"), bi2_lengths, "contacto"),
                    "email": _limited(client.get("EMAIL"), bi2_lengths, "email"),
                    "u_aprova": 0,
                    "u_desapro": 0,
                    "u_dtaprova": PHC_ZERO_DATE,
                    "u_respons": "",
                    "usrinis": user_inis,
                    "usrdata": now_sql,
                    "usrhora": audit_time,
                }
                if prepared["exists"]:
                    if not _phc_update(cursor, "BI2", bi2_values, "BI2STAMP", bistamp):
                        _phc_insert(cursor, "BI2", bi2_values)
                else:
                    bi2_values.update(
                        {
                            "u_aprova": 0,
                            "u_desapro": 0,
                            "ousrinis": user_inis,
                            "ousrdata": now_sql,
                            "ousrhora": audit_time,
                        }
                    )
                    _phc_insert(cursor, "BI2", bi2_values)

                cursor.execute("DELETE FROM dbo.OCI WHERE BISTAMP = ?", bistamp)
                if prepared["has_technical"]:
                    for oci_index, row in enumerate(prepared["technical_rows"], start=1):
                        purchase_price = _write_oci_purchase_price(row)
                        cost_per_unit = _write_money(row.get("cost_per_unit"))
                        component_quantity = cost_per_unit / purchase_price if purchase_price else Decimal("0")
                        if not cost_per_unit and purchase_price:
                            component_quantity = _decimal(row.get("quantity"))
                        _phc_insert(
                            cursor,
                            "OCI",
                            {
                                "ocistamp": _new_stamp(),
                                "bostamp": bostamp,
                                "bistamp": bistamp,
                                "ref": _limited(row.get("reference"), oci_lengths, "ref"),
                                "design": _limited(row.get("designation"), oci_lengths, "design"),
                                "familia": _limited(row.get("family"), oci_lengths, "familia"),
                                "armazem": 1,
                                "qtt": component_quantity,
                                "pcusto": _write_money(row.get("base_purchase_price")),
                                "epcusto": purchase_price,
                                "unidade": _limited(row.get("unit"), oci_lengths, "unidade"),
                                "qtttotal": component_quantity * prepared["quantity"],
                                "nivel": 0,
                                "u_forfait": _write_money(row.get("forfait")),
                                "u_area": _decimal(row.get("area")),
                                "u_espess": _decimal(row.get("thickness")),
                                "u_volume": _decimal(row.get("volume")),
                                "u_peso": _decimal(row.get("weight")),
                                "u_consumo": _decimal(row.get("consumption")),
                                "u_coef": _decimal(row.get("coefficient")),
                                "u_formula": _limited(row.get("formula"), oci_lengths, "u_formula"),
                                "u_design": _limited(row.get("designation"), oci_lengths, "u_design"),
                                "u_pvenda": _write_money(row.get("sale_price")),
                                "ousrinis": user_inis,
                                "ousrdata": audit_date,
                                "ousrhora": audit_time,
                                "usrinis": user_inis,
                                "usrdata": audit_date,
                                "usrhora": audit_time,
                            },
                        )
                    _phc_insert(
                        cursor,
                        "OCI",
                        {
                            "ocistamp": _new_stamp(),
                            "bostamp": bostamp,
                            "bistamp": bistamp,
                            "ref": "XZ",
                            "design": "Frais d´etude",
                            "armazem": 1,
                            "qtt": 1,
                            "epcusto": Decimal("0.10"),
                            "qtttotal": prepared["quantity"],
                            "ousrinis": user_inis,
                            "ousrdata": audit_date,
                            "ousrhora": audit_time,
                            "usrinis": user_inis,
                            "usrdata": audit_date,
                            "usrhora": audit_time,
                        },
                    )

            if creating:
                _phc_insert(cursor, "BO", bo_values)
            else:
                _phc_update(cursor, "BO", bo_values, "BOSTAMP", bostamp)
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    return {
        "created": creating,
        "bostamp": bostamp,
        "number": obrano,
        "year": boano,
    }


__all__ = [
    "BudgetsCreditLimitError",
    "BudgetsError",
    "get_budget_detail",
    "get_budget_line_oci",
    "get_budget_salespeople",
    "get_budget_series",
    "get_budget_technical_options",
    "list_budgets",
    "list_companies_for_user",
    "save_budget",
    "set_budget_approval",
    "search_budget_clients",
]
