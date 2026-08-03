from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

import pyodbc

from modules.gr_subcontractor_measurements.service import (
    SubcontractorMeasurementsError,
    SubcontractorMeasurementsNotFoundError,
    SubcontractorMeasurementsValidationError,
    _company_for_user,
    _currency_code,
    _date_iso,
    _decimal,
    _fetch_rows,
    _money,
    _number_value,
    _phc_columns,
    _phc_conn_str,
    _qty,
    _text_value,
    list_companies_for_user,
)


MAX_RESULTS = 300
DEFAULT_SERIES_NAME = "Devis"


class BudgetsError(SubcontractorMeasurementsError):
    """Erro funcional do ecrã de orçamentos."""


class BudgetsValidationError(SubcontractorMeasurementsValidationError, BudgetsError):
    pass


class BudgetsNotFoundError(SubcontractorMeasurementsNotFoundError, BudgetsError):
    pass


def _bool_value(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "sim", "yes", "y"}
    return bool(value)


def _business_date_iso(value: Any) -> str:
    parsed = value.date() if isinstance(value, datetime) else value
    if isinstance(parsed, date) and parsed.year <= 1900:
        return ""
    return _date_iso(value)


def _percent(value: Any) -> float:
    return float(_decimal(value).quantize(Decimal("0.01")))


def _optional_column(
    columns: set[str], table_alias: str, column: str, result_alias: str, default_sql: str = "NULL"
) -> str:
    if column.lower() in columns:
        return f"{table_alias}.[{column}] AS [{result_alias}]"
    return f"{default_sql} AS [{result_alias}]"


def _pick_default_series(rows: list[dict[str, Any]]) -> int:
    for row in rows:
        if _text_value(row.get("name")).casefold() == DEFAULT_SERIES_NAME.casefold():
            return int(row.get("ndos") or 0)
    return int(rows[0].get("ndos") or 0) if rows else 0


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
            ISNULL(OCI, 0) AS OCI
        FROM dbo.TS
        WHERE UPPER(LTRIM(RTRIM(ISNULL(NMDOS, '')))) = 'DEVIS'
           OR (ISNULL(ORCAMENTO, 0) = 1 AND ISNULL(OCI, 0) = 1)
        ORDER BY NMDOS, NDOS
        """,
        (),
    )
    return [
        {
            "ndos": int(_number_value(row.get("NDOS"))),
            "name": _text_value(row.get("NMDOS")),
            "quantity_decimals": int(_number_value(row.get("QTTDEC"))),
            "price_decimals": int(_number_value(row.get("PREDEC"))),
            "is_budget": _bool_value(row.get("ORCAMENTO")),
            "uses_oci": _bool_value(row.get("OCI")),
        }
        for row in rows
        if int(_number_value(row.get("NDOS"))) > 0
    ]


def get_budget_series(feid: Any, user) -> dict[str, Any]:
    company = _company_for_user(feid, user)
    with pyodbc.connect(_phc_conn_str(company["phc_db"], company.get("phc_server", "")), timeout=15) as conn:
        rows = _series_rows(conn.cursor())
    return {"company": company, "rows": rows, "default_ndos": _pick_default_series(rows)}


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
        "awarded": _bool_value(row.get("ADJUDICADO")),
        "cancelled": _bool_value(row.get("ANULADO")),
        "line_count": int(_number_value(row.get("LINE_COUNT"))),
    }


def get_budget_detail(feid: Any, bostamp: str, user) -> dict[str, Any]:
    company = _company_for_user(feid, user)
    clean_stamp = _text_value(bostamp)
    if not clean_stamp:
        raise BudgetsValidationError("Orçamento não indicado.")

    with pyodbc.connect(_phc_conn_str(company["phc_db"], company.get("phc_server", "")), timeout=20) as conn:
        cursor = conn.cursor()
        bo_columns = _phc_columns(cursor, "BO")
        bo2_columns = _phc_columns(cursor, "BO2")
        bo3_columns = _phc_columns(cursor, "BO3")
        header_rows = _fetch_rows(
            cursor,
            f"""
            SELECT
                B.BOSTAMP, B.NMDOS, B.NDOS, B.OBRANO, B.BOANO, B.DATAOBRA,
                B.NO, B.ESTAB, B.NOME, B.TRAB1, B.OBRANOME, B.LOCAL, B.MORADA,
                B.CODPOST, B.VENDEDOR, B.VENDNM, B.SERIE, B.ZONA, B.NOPAT,
                B.MOEDA, B.ETOTALDEB, B.ECUSTO, B.APROVADO, B.OBS, B.FREF,
                B.CCUSTO, B.COBRANCA, B.TECNICO, B.TECNNM,
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
            """,
            (clean_stamp,),
        )
        if not header_rows:
            raise BudgetsNotFoundError("Orçamento não encontrado no PHC desta empresa.")

        bi_columns = _phc_columns(cursor, "BI")
        bi2_columns = _phc_columns(cursor, "BI2")
        line_rows = _fetch_rows(
            cursor,
            f"""
            SELECT
                I.BISTAMP, I.LORDEM, I.LITEM, I.REF, I.DESIGN, I.DGERAL,
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

    header = _header_payload(header_rows[0], company)
    lines = [_line_payload(row) for row in line_rows]
    return {"company": company, "header": header, "lines": lines, "totals": _totals_payload(header, lines)}


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
    }


def _line_payload(row: dict[str, Any]) -> dict[str, Any]:
    quantity = _decimal(row.get("QTT"))
    unit_cost = _decimal(row.get("EPCUSTO"))
    total = _decimal(row.get("ETTDEB"))
    cost_total = quantity * unit_cost
    profit = total - cost_total
    margin = (profit / total * Decimal("100")) if total else Decimal("0")
    return {
        "bistamp": _text_value(row.get("BISTAMP")),
        "order": _number_value(row.get("LORDEM")),
        "item": int(_number_value(row.get("LITEM"))),
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
        "unit": _text_value(row.get("UNIDADE")),
        "unit_cost": _qty(unit_cost),
        "indirect_cost": _qty(row.get("ECUSTOIND")),
        "cost_total": _qty(cost_total),
        "thickness": _qty(row.get("U_ESPESS")),
        "height": _qty(row.get("U_ALT")),
        "blocked_price": _bool_value(row.get("U_BLOQPV")),
        "pump": _bool_value(row.get("U_BOMBA")),
        "has_technical_detail": _bool_value(row.get("TEMOCI")),
        "labour": _bool_value(row.get("U_MO")),
        "option": _bool_value(row.get("U_OPCAO")),
        "simultaneous": _bool_value(row.get("U_SIMULT")),
        "pro_rata": _bool_value(row.get("U_PRORATA")),
        "variant": _bool_value(row.get("U_VARIANTE")),
        "approved": _bool_value(row.get("U_APROVA")),
        "disapproved": _bool_value(row.get("U_DESAPRO")),
        "purchase_quantity": _qty(row.get("QTTCOMPRA")),
        "ordered_quantity": _qty(row.get("QTTENC")),
        "margin_percentage": _percent(margin),
        "profit": _qty(profit),
    }


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


__all__ = [
    "BudgetsError",
    "get_budget_detail",
    "get_budget_series",
    "list_budgets",
    "list_companies_for_user",
]
