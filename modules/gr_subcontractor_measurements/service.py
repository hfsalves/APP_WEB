from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
import io
import mimetypes
import os
import re
import uuid

import pyodbc
from flask import current_app


CONTRACT_NDOS = 128
MEASUREMENT_NDOS = 129
MEASUREMENT_NMDOS = "Situation Travaux ST"
PHC_CONVERSION_RATE = Decimal("200.482")
PHC_ZERO_DATE = date(1900, 1, 1)


class SubcontractorMeasurementsError(Exception):
    status_code = 500


class SubcontractorMeasurementsValidationError(SubcontractorMeasurementsError):
    status_code = 400


class SubcontractorMeasurementsNotFoundError(SubcontractorMeasurementsError):
    status_code = 404


def _text_value(value: Any) -> str:
    return str(value or "").strip()


def _stamp_key(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "").upper())


def _number_value(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except Exception:
        return 0.0


def _date_iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return ""


def _decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    raw = str(value if value is not None else "").strip().replace(",", ".")
    if not raw:
        return Decimal("0")
    try:
        return Decimal(raw)
    except Exception:
        return Decimal("0")


def _new_stamp() -> str:
    return uuid.uuid4().hex.upper()[:25]


def _sql_identifier(name: str) -> str:
    return "[" + str(name or "").replace("]", "]]") + "]"


def _money(value: Any) -> float:
    return float(_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _qty(value: Any) -> float:
    return float(_decimal(value).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


def _int_value(value: Any) -> int:
    return int(_number_value(value))


def _phc_value(value: Any) -> Decimal:
    return (_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) * PHC_CONVERSION_RATE).quantize(
        Decimal("0.00001"),
        rounding=ROUND_HALF_UP,
    )


def _is_morocco_company(company: dict[str, Any]) -> bool:
    text = " ".join(
        _text_value(company.get(key)).upper()
        for key in ("name", "phc_db", "country")
    )
    return any(token in text for token in ("MAROC", "MARRO", "MOROCCO", "MA ", "SARLAU"))


def _currency_code(value: Any = "", company: dict[str, Any] | None = None) -> str:
    raw = _text_value(value).upper()
    normalized = raw.replace(".", "").replace(" ", "")
    if normalized in {"", "EURO", "EUROS", "EUR", "€"}:
        if company and _is_morocco_company(company):
            return "MAD"
        return "EUR"
    if normalized in {"MAD", "DH", "DHS", "DIRHAM", "DIRHAMS"}:
        return "MAD"
    return normalized[:3] or ("MAD" if company and _is_morocco_company(company) else "EUR")


def _conn_part(conn_str: str, key: str) -> str:
    match = re.search(rf"(?:^|;){re.escape(key)}=([^;]*)", conn_str or "", flags=re.IGNORECASE)
    return str(match.group(1) or "").strip() if match else ""


def _replace_conn_part(conn_str: str, key: str, value: str) -> str:
    clean_value = str(value or "").strip()
    if re.search(rf"(?:^|;){re.escape(key)}=", conn_str or "", flags=re.IGNORECASE):
        return re.sub(
            rf"((?:^|;){re.escape(key)}=)[^;]*",
            rf"\g<1>{clean_value}",
            conn_str,
            count=1,
            flags=re.IGNORECASE,
        )
    return conn_str.rstrip(";") + f";{key}={clean_value};"


def _client_conn_str() -> str:
    conn_map = current_app.config.get("DB_CONN_STRS") or {}
    conn_str = str(conn_map.get("client") or conn_map.get("default") or "").strip()
    if not conn_str:
        raise SubcontractorMeasurementsError("Ligacao client/GR360_CORE nao configurada.")
    return conn_str


def _phc_conn_str(database_name: str, server_name: str = "") -> str:
    database = _text_value(database_name)
    if not database:
        raise SubcontractorMeasurementsValidationError("Empresa sem base PHC configurada.")
    conn_str = _replace_conn_part(_client_conn_str(), "DATABASE", database)
    server = _text_value(server_name)
    if server:
        current_server = _conn_part(conn_str, "SERVER")
        port = ""
        if "," in current_server and "," not in server:
            port = current_server.split(",", 1)[1].strip()
        conn_str = _replace_conn_part(conn_str, "SERVER", f"{server},{port}" if port else server)
    return conn_str


def _has_table(table_name: str) -> bool:
    with pyodbc.connect(_client_conn_str(), timeout=10) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT 1
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'dbo'
              AND TABLE_NAME = ?
            """,
            table_name,
        )
        return cursor.fetchone() is not None


def _has_column(table_name: str, column_name: str) -> bool:
    with pyodbc.connect(_client_conn_str(), timeout=10) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT 1
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'dbo'
              AND TABLE_NAME = ?
              AND COLUMN_NAME = ?
            """,
            table_name,
            column_name,
        )
        return cursor.fetchone() is not None


def list_companies_for_user(user) -> list[dict[str, Any]]:
    if not _has_table("FE") or not _has_column("FE", "PHC_DB"):
        raise SubcontractorMeasurementsError("A tabela FE nao tem configuracao PHC_DB.")

    active_filter = "AND ISNULL(FE.ATIVA, 1) = 1" if _has_column("FE", "ATIVA") else ""
    phc_server_select = (
        "LTRIM(RTRIM(ISNULL(FE.PHC_SERVER, ''))) AS PHC_SERVER"
        if _has_column("FE", "PHC_SERVER")
        else "CAST('' AS varchar(128)) AS PHC_SERVER"
    )
    name_select = (
        "LTRIM(RTRIM(ISNULL(NULLIF(FE.NOMEFISCAL, ''), ISNULL(FE.NOME, '')))) AS NOME"
        if _has_column("FE", "NOMEFISCAL")
        else "LTRIM(RTRIM(ISNULL(FE.NOME, ''))) AS NOME"
    )
    country_select = (
        "LTRIM(RTRIM(ISNULL(FE.PAISISO2, ''))) AS PAISISO2"
        if _has_column("FE", "PAISISO2")
        else "CAST('' AS varchar(8)) AS PAISISO2"
    )
    currency_select = (
        "LTRIM(RTRIM(ISNULL(FE.MOEDA, ''))) AS MOEDA"
        if _has_column("FE", "MOEDA")
        else "CAST('' AS varchar(16)) AS MOEDA"
    )

    is_admin = bool(getattr(user, "ADMIN", False) or getattr(user, "DEV", False))
    params: list[Any] = []
    join_sql = ""
    user_filter = ""
    if not is_admin:
        if not _has_table("US_FE"):
            raise SubcontractorMeasurementsError("A tabela US_FE nao existe para validar acessos por empresa.")
        join_sql = "INNER JOIN dbo.US_FE UF ON UF.FEID = FE.FEID"
        user_filter = """
          AND LTRIM(RTRIM(ISNULL(UF.USSTAMP, ''))) = ?
          AND ISNULL(UF.ATIVO, 0) = 1
        """
        params.append(_text_value(getattr(user, "USSTAMP", "")))

    with pyodbc.connect(_client_conn_str(), timeout=10) as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT DISTINCT
                ISNULL(FE.FEID, 0) AS FEID,
                {name_select},
                LTRIM(RTRIM(ISNULL(FE.PHC_DB, ''))) AS PHC_DB,
                {phc_server_select},
                {country_select},
                {currency_select}
            FROM dbo.FE FE
            {join_sql}
            WHERE LTRIM(RTRIM(ISNULL(FE.PHC_DB, ''))) <> ''
              {active_filter}
              {user_filter}
            ORDER BY NOME, PHC_DB
            """,
            tuple(params),
        )
        columns = [str(col[0]) for col in cursor.description or []]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return [
        {
            "feid": int(row.get("FEID") or 0),
            "name": _text_value(row.get("NOME")) or _text_value(row.get("PHC_DB")),
            "phc_db": _text_value(row.get("PHC_DB")),
            "phc_server": _text_value(row.get("PHC_SERVER")),
            "country": _text_value(row.get("PAISISO2")),
            "currency": _currency_code(row.get("MOEDA"), {
                "name": _text_value(row.get("NOME")),
                "phc_db": _text_value(row.get("PHC_DB")),
                "country": _text_value(row.get("PAISISO2")),
            }),
        }
        for row in rows
    ]


def _company_for_user(feid: Any, user) -> dict[str, Any]:
    clean_feid = int(feid or 0)
    companies = list_companies_for_user(user)
    for company in companies:
        if int(company.get("feid") or 0) == clean_feid:
            return company
    raise SubcontractorMeasurementsValidationError("Empresa PHC sem acesso ou inexistente.")


def _parse_filter_date(value: Any) -> date | None:
    raw = _text_value(value)
    if not raw:
        return None
    try:
        return datetime.strptime(raw[:10], "%Y-%m-%d").date()
    except ValueError as exc:
        raise SubcontractorMeasurementsValidationError("Data invalida.") from exc


def _fetch_rows(cursor, sql: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
    cursor.execute(sql, params)
    columns = [str(col[0]) for col in cursor.description or []]
    rows: list[dict[str, Any]] = []
    for row in cursor.fetchall():
        item: dict[str, Any] = {}
        for column, value in zip(columns, row):
            item[column] = value
            item[column.upper()] = value
            item[column.lower()] = value
        rows.append(item)
    return rows


def _phc_columns(cursor, table_name: str) -> set[str]:
    cursor.execute(
        """
        SELECT LOWER(COLUMN_NAME)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo'
          AND TABLE_NAME = ?
        """,
        table_name,
    )
    return {str(row[0] or "").strip().lower() for row in cursor.fetchall()}


def _pick_column(columns: set[str], candidates: list[str]) -> str:
    available = {str(column or "").strip().upper() for column in columns}
    for candidate in candidates:
        if candidate.upper() in available:
            return candidate.upper()
    return ""


def _phc_insert(cursor, table_name: str, values: dict[str, Any]) -> dict[str, Any]:
    columns = _phc_columns(cursor, table_name)
    filtered = {key: value for key, value in values.items() if key.lower() in columns}
    if not filtered:
        raise SubcontractorMeasurementsError(f"Sem colunas validas para inserir em {table_name}.")
    cursor.execute(
        f"INSERT INTO dbo.{table_name} ({', '.join(filtered.keys())}) VALUES ({', '.join(['?'] * len(filtered))})",
        list(filtered.values()),
    )
    return filtered


def _phc_tax_rates(cursor) -> list[dict[str, Any]]:
    columns = _phc_columns(cursor, "TAXASIVA")
    if not columns:
        return []
    code_col = _pick_column(columns, ["TABIVA", "CODIGO", "COD", "CODIVA", "ID"])
    rate_col = _pick_column(columns, ["TAXAIVA", "TAXA", "PERCENTAGEM", "VALOR"])
    if not code_col or not rate_col:
        return []
    cursor.execute(
        f"""
        SELECT
            CONVERT(varchar(30), {_sql_identifier(code_col)}) AS TABIVA,
            TRY_CONVERT(decimal(9,4), {_sql_identifier(rate_col)}) AS TAXAIVA
        FROM dbo.TAXASIVA
        WHERE {_sql_identifier(code_col)} IS NOT NULL
        ORDER BY TRY_CONVERT(int, {_sql_identifier(code_col)}), {_sql_identifier(code_col)}
        """
    )
    return [
        {
            "tabiva": _text_value(row.TABIVA),
            "taxaiva": _decimal(row.TAXAIVA),
        }
        for row in cursor.fetchall()
        if _text_value(row.TABIVA)
    ]


def list_contracts(filters: dict[str, Any], user) -> dict[str, Any]:
    company = _company_for_user(filters.get("feid"), user)
    data_inicio = _parse_filter_date(filters.get("data_inicio"))
    data_fim = _parse_filter_date(filters.get("data_fim"))
    ccusto = _text_value(filters.get("ccusto"))
    fornecedor = _text_value(filters.get("fornecedor"))
    only_open = str(filters.get("only_open") or "1").strip().lower() not in {"0", "false", "no"}

    where = ["C.NDOS = ?", "ISNULL(C2.ANULADO, 0) = 0"]
    params: list[Any] = [CONTRACT_NDOS]
    if data_inicio:
        where.append("C.DATAOBRA >= ?")
        params.append(data_inicio)
    if data_fim:
        where.append("C.DATAOBRA <= ?")
        params.append(data_fim)
    if ccusto:
        where.append("(C.CCUSTO LIKE ? OR C2.PROCESSO LIKE ?)")
        like = f"%{ccusto}%"
        params.extend([like, like])
    if fornecedor:
        fornecedor_like = f"%{fornecedor}%"
        if fornecedor.isdigit():
            where.append("(C.NO = ? OR C.NOME LIKE ?)")
            params.extend([int(fornecedor), fornecedor_like])
        else:
            where.append("C.NOME LIKE ?")
            params.append(fornecedor_like)
    if only_open:
        where.append("ISNULL(C.FECHADA, 0) = 0")

    sql = f"""
        WITH execs AS (
            SELECT
                A2.ADJBOSTAMP AS BOSTAMP,
                SUM(ISNULL(ABI.ETTDEB, 0)) AS EXEC_VALUE,
                COUNT(DISTINCT A.BOSTAMP) AS AUTO_COUNT,
                SUM(CASE WHEN ISNULL(A.FECHADA, 0) = 1 THEN 1 ELSE 0 END) AS CLOSED_AUTO_LINE_COUNT
            FROM dbo.BO A WITH (NOLOCK)
            INNER JOIN dbo.BO2 A2 WITH (NOLOCK)
                ON A2.BO2STAMP = A.BOSTAMP
            INNER JOIN dbo.BI ABI WITH (NOLOCK)
                ON ABI.BOSTAMP = A.BOSTAMP
            WHERE A.NDOS = ?
              AND ISNULL(A2.ANULADO, 0) = 0
              AND LTRIM(RTRIM(ISNULL(A2.ADJBOSTAMP, ''))) <> ''
            GROUP BY A2.ADJBOSTAMP
        )
        SELECT TOP 300
            C.BOSTAMP,
            C.NDOS,
            C.NMDOS,
            C.OBRANO,
            C.BOANO,
            C.DATAOBRA,
            C.NO,
            C.NOME,
            C.CCUSTO,
            C.FECHADA,
            C.MOEDA,
            C.ETOTALDEB,
            C2.PROCESSO,
            ISNULL(E.EXEC_VALUE, 0) AS EXEC_VALUE,
            ISNULL(E.AUTO_COUNT, 0) AS AUTO_COUNT
        FROM dbo.BO C WITH (NOLOCK)
        LEFT JOIN dbo.BO2 C2 WITH (NOLOCK)
            ON C2.BO2STAMP = C.BOSTAMP
        LEFT JOIN execs E
            ON E.BOSTAMP = C.BOSTAMP
        WHERE {" AND ".join(where)}
        ORDER BY C.DATAOBRA DESC, C.OBRANO DESC, C.BOSTAMP DESC
    """

    with pyodbc.connect(_phc_conn_str(company["phc_db"], company.get("phc_server") or ""), timeout=20) as conn:
        rows = _fetch_rows(conn.cursor(), sql, tuple([MEASUREMENT_NDOS, *params]))

    contracts = []
    for row in rows:
        total = _decimal(row.get("ETOTALDEB"))
        executed = _decimal(row.get("EXEC_VALUE"))
        balance = total - executed
        progress = Decimal("0")
        if total:
            progress = (executed / total * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        contracts.append(
            {
                "bostamp": _text_value(row.get("BOSTAMP")),
                "doc_name": _text_value(row.get("NMDOS")),
                "number": int(_number_value(row.get("OBRANO"))),
                "year": int(_number_value(row.get("BOANO"))),
                "date": _date_iso(row.get("DATAOBRA")),
                "supplier_no": int(_number_value(row.get("NO"))),
                "supplier_name": _text_value(row.get("NOME")),
                "cost_center": _text_value(row.get("CCUSTO") or row.get("PROCESSO")),
                "process": _text_value(row.get("PROCESSO")),
                "closed": bool(row.get("FECHADA")),
                "currency": _currency_code(row.get("MOEDA"), company),
                "contract_value": _money(total),
                "executed_value": _money(executed),
                "remaining_value": _money(balance),
                "progress": float(progress),
                "auto_count": int(_number_value(row.get("AUTO_COUNT"))),
            }
        )

    return {"company": company, "rows": contracts}


def get_contract_detail(feid: Any, bostamp: str, user) -> dict[str, Any]:
    company = _company_for_user(feid, user)
    clean_bostamp = _text_value(bostamp)
    if not clean_bostamp:
        raise SubcontractorMeasurementsValidationError("Contrato obrigatorio.")

    with pyodbc.connect(_phc_conn_str(company["phc_db"], company.get("phc_server") or ""), timeout=20) as conn:
        cursor = conn.cursor()
        header_rows = _fetch_rows(
            cursor,
            """
            SELECT TOP 1
                C.BOSTAMP,
                C.NDOS,
                C.NMDOS,
                C.OBRANO,
                C.BOANO,
                C.DATAOBRA,
                C.NO,
                C.NOME,
                C.CCUSTO,
                C.FECHADA,
                C.ETOTALDEB,
                C.MOEDA,
                C2.PROCESSO,
                C2.AUTOS,
                C2.AUTOTIPO,
                C2.AUTONO
            FROM dbo.BO C WITH (NOLOCK)
            LEFT JOIN dbo.BO2 C2 WITH (NOLOCK)
                ON C2.BO2STAMP = C.BOSTAMP
            WHERE C.NDOS = ?
              AND C.BOSTAMP = ?
            """,
            (CONTRACT_NDOS, clean_bostamp),
        )
        if not header_rows:
            raise SubcontractorMeasurementsNotFoundError("Contrato nao encontrado.")
        header = header_rows[0]

        auto_rows = _fetch_rows(
            cursor,
            """
            SELECT
                A.BOSTAMP,
                A.OBRANO,
                A.BOANO,
                A.DATAOBRA,
                A.FECHADA,
                A.ETOTALDEB,
                A2.AUTONO
            FROM dbo.BO A WITH (NOLOCK)
            INNER JOIN dbo.BO2 A2 WITH (NOLOCK)
                ON A2.BO2STAMP = A.BOSTAMP
            WHERE A.NDOS = ?
              AND A2.ADJBOSTAMP = ?
              AND ISNULL(A2.ANULADO, 0) = 0
            ORDER BY A.DATAOBRA, A.OBRANO, A.BOSTAMP
            """,
            (MEASUREMENT_NDOS, clean_bostamp),
        )

        line_rows = _fetch_rows(
            cursor,
            """
            WITH execs AS (
                SELECT
                    ABI.OOBISTAMP AS BISTAMP,
                    SUM(ISNULL(ABI.QTT, 0)) AS EXEC_QTY,
                    SUM(ISNULL(ABI.ETTDEB, 0)) AS EXEC_VALUE,
                    COUNT(*) AS AUTO_LINE_COUNT
                FROM dbo.BO A WITH (NOLOCK)
                INNER JOIN dbo.BO2 A2 WITH (NOLOCK)
                    ON A2.BO2STAMP = A.BOSTAMP
                INNER JOIN dbo.BI ABI WITH (NOLOCK)
                    ON ABI.BOSTAMP = A.BOSTAMP
                WHERE A.NDOS = ?
                  AND A2.ADJBOSTAMP = ?
                  AND ISNULL(A2.ANULADO, 0) = 0
                  AND LTRIM(RTRIM(ISNULL(ABI.OOBISTAMP, ''))) <> ''
                GROUP BY ABI.OOBISTAMP
            )
            SELECT
                BI.BISTAMP,
                BI.BOSTAMP,
                BI.REF,
                BI.DESIGN,
                BI.UNIDADE,
                BI.QTT,
                BI.EDEBITO,
                BI.ETTDEB,
                BI.IVA,
                BI.TABIVA,
                BI.CCUSTO,
                BI.LORDEM,
                BI.LOBS,
                ISNULL(E.EXEC_QTY, 0) AS EXEC_QTY,
                ISNULL(E.EXEC_VALUE, 0) AS EXEC_VALUE,
                ISNULL(E.AUTO_LINE_COUNT, 0) AS AUTO_LINE_COUNT
            FROM dbo.BI BI WITH (NOLOCK)
            LEFT JOIN execs E
                ON E.BISTAMP = BI.BISTAMP
            WHERE BI.NDOS = ?
              AND BI.BOSTAMP = ?
            ORDER BY BI.LORDEM, BI.BISTAMP
            """,
            (MEASUREMENT_NDOS, clean_bostamp, CONTRACT_NDOS, clean_bostamp),
        )

    lines = []
    for row in line_rows:
        contract_qty = _decimal(row.get("QTT"))
        contract_value = _decimal(row.get("ETTDEB"))
        executed_qty = _decimal(row.get("EXEC_QTY"))
        executed_value = _decimal(row.get("EXEC_VALUE"))
        remaining_qty = contract_qty - executed_qty
        remaining_value = contract_value - executed_value
        progress = Decimal("0")
        if contract_qty:
            progress = (executed_qty / contract_qty * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        elif contract_value:
            progress = (executed_value / contract_value * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        lines.append(
            {
                "bistamp": _text_value(row.get("BISTAMP")),
                "ref": _text_value(row.get("REF")),
                "design": _text_value(row.get("DESIGN")),
                "unit": _text_value(row.get("UNIDADE")),
                "qty": _qty(contract_qty),
                "unit_price": _money(row.get("EDEBITO")),
                "value": _money(contract_value),
                "vat": _number_value(row.get("IVA")),
                "vat_code": int(_number_value(row.get("TABIVA"))),
                "cost_center": _text_value(row.get("CCUSTO")),
                "order": int(_number_value(row.get("LORDEM"))),
                "notes": _text_value(row.get("LOBS")),
                "executed_qty": _qty(executed_qty),
                "executed_value": _money(executed_value),
                "remaining_qty": _qty(remaining_qty),
                "remaining_value": _money(remaining_value),
                "progress": float(progress),
                "auto_line_count": int(_number_value(row.get("AUTO_LINE_COUNT"))),
                "measurable": bool(contract_qty or contract_value),
            }
        )

    total = _decimal(header.get("ETOTALDEB"))
    executed = sum((_decimal(line["executed_value"]) for line in lines), Decimal("0"))
    return {
        "company": company,
        "contract": {
            "bostamp": _text_value(header.get("BOSTAMP")),
            "doc_name": _text_value(header.get("NMDOS")),
            "number": int(_number_value(header.get("OBRANO"))),
            "year": int(_number_value(header.get("BOANO"))),
            "date": _date_iso(header.get("DATAOBRA")),
            "supplier_no": int(_number_value(header.get("NO"))),
            "supplier_name": _text_value(header.get("NOME")),
            "cost_center": _text_value(header.get("CCUSTO") or header.get("PROCESSO")),
            "process": _text_value(header.get("PROCESSO")),
            "currency": _currency_code(header.get("MOEDA"), company),
            "closed": bool(header.get("FECHADA")),
            "contract_value": _money(total),
            "executed_value": _money(executed),
            "remaining_value": _money(total - executed),
            "auto_count": len(auto_rows),
        },
        "autos": [
            {
                "bostamp": _text_value(row.get("BOSTAMP")),
                "number": int(_number_value(row.get("OBRANO"))),
                "year": int(_number_value(row.get("BOANO"))),
                "date": _date_iso(row.get("DATAOBRA")),
                "closed": bool(row.get("FECHADA")),
                "value": _money(row.get("ETOTALDEB")),
                "contract_auto_number": int(_number_value(row.get("AUTONO"))),
            }
            for row in auto_rows
        ],
        "lines": lines,
    }


def get_contract_autos(feid: Any, bostamp: str, user) -> dict[str, Any]:
    company = _company_for_user(feid, user)
    clean_bostamp = _text_value(bostamp)
    if not clean_bostamp:
        raise SubcontractorMeasurementsValidationError("Contrato obrigatorio.")

    with pyodbc.connect(_phc_conn_str(company["phc_db"], company.get("phc_server") or ""), timeout=20) as conn:
        cursor = conn.cursor()
        contract_rows = _fetch_rows(
            cursor,
            """
            SELECT TOP 1
                C.BOSTAMP,
                C.NMDOS,
                C.OBRANO,
                C.BOANO,
                C.DATAOBRA,
                C.NO,
                C.NOME,
                C.CCUSTO,
                C.MOEDA,
                C2.PROCESSO
            FROM dbo.BO C WITH (NOLOCK)
            LEFT JOIN dbo.BO2 C2 WITH (NOLOCK)
                ON C2.BO2STAMP = C.BOSTAMP
            WHERE C.NDOS = ?
              AND C.BOSTAMP = ?
            """,
            (CONTRACT_NDOS, clean_bostamp),
        )
        if not contract_rows:
            raise SubcontractorMeasurementsNotFoundError("Contrato nao encontrado.")
        contract = contract_rows[0]

        auto_rows = _fetch_rows(
            cursor,
            """
            SELECT
                A.BOSTAMP,
                A.NMDOS,
                A.OBRANO,
                A.BOANO,
                A.DATAOBRA,
                A.FECHADA,
                A.ETOTALDEB,
                A.NO,
                A.NOME,
                A.CCUSTO,
                A2.PROCESSO,
                A2.AUTONO
            FROM dbo.BO A WITH (NOLOCK)
            INNER JOIN dbo.BO2 A2 WITH (NOLOCK)
                ON A2.BO2STAMP = A.BOSTAMP
            WHERE A.NDOS = ?
              AND A2.ADJBOSTAMP = ?
              AND ISNULL(A2.ANULADO, 0) = 0
            ORDER BY A.DATAOBRA DESC, A.OBRANO DESC, A.BOSTAMP DESC
            """,
            (MEASUREMENT_NDOS, clean_bostamp),
        )

        auto_stamps = [_text_value(row.get("BOSTAMP")) for row in auto_rows if _text_value(row.get("BOSTAMP"))]
        line_rows: list[dict[str, Any]] = []
        attachment_rows: list[dict[str, Any]] = []
        if auto_stamps:
            placeholders = ", ".join("?" for _ in auto_stamps)
            line_rows = _fetch_rows(
                cursor,
                f"""
                SELECT
                    BI.BOSTAMP,
                    BI.BISTAMP,
                    BI.OOBISTAMP,
                    BI.REF,
                    BI.DESIGN,
                    BI.UNIDADE,
                    BI.QTT,
                    BI.EDEBITO,
                    BI.ETTDEB,
                    BI.IVA,
                    BI.TABIVA,
                    BI.CCUSTO,
                    BI.LORDEM,
                    BI2.QTTFALTA,
                    BI2.QTTNEW,
                    BI2.PERCNEW,
                    BI2.EVALNEW
                FROM dbo.BI BI WITH (NOLOCK)
                LEFT JOIN dbo.BI2 BI2 WITH (NOLOCK)
                    ON BI2.BI2STAMP = BI.BISTAMP
                WHERE BI.NDOS = ?
                  AND BI.BOSTAMP IN ({placeholders})
                ORDER BY BI.BOSTAMP, BI.LORDEM, BI.BISTAMP
                """,
                tuple([MEASUREMENT_NDOS, *auto_stamps]),
            )
            attachment_rows = _fetch_rows(
                cursor,
                f"""
                WITH ranked AS (
                    SELECT
                        A.ANEXOSSTAMP,
                        A.RECSTAMP,
                        A.DESCRICAO,
                        A.FULLNAME,
                        A.FNAME,
                        A.FEXT,
                        A.FLEN,
                        A.AUSRDATA,
                        ROW_NUMBER() OVER (
                            PARTITION BY LTRIM(RTRIM(ISNULL(A.RECSTAMP, '')))
                            ORDER BY
                                CASE WHEN LOWER(LTRIM(RTRIM(ISNULL(A.FEXT, '')))) = 'pdf' THEN 0 ELSE 1 END,
                                A.AUSRDATA DESC,
                                A.ANEXOSSTAMP DESC
                        ) AS RN
                    FROM dbo.ANEXOS A WITH (NOLOCK)
                    WHERE LTRIM(RTRIM(ISNULL(A.ORITABLE, ''))) = 'BO'
                      AND LTRIM(RTRIM(ISNULL(A.RECSTAMP, ''))) IN ({placeholders})
                )
                SELECT *
                FROM ranked
                WHERE RN = 1
                """,
                tuple(auto_stamps),
            )

    lines_by_auto: dict[str, list[dict[str, Any]]] = {}
    for row in line_rows:
        auto_stamp = _text_value(row.get("BOSTAMP"))
        qty = _decimal(row.get("QTTNEW"))
        if not qty:
            qty = _decimal(row.get("QTT"))
        value = _decimal(row.get("EVALNEW"))
        if not value:
            value = _decimal(row.get("ETTDEB"))
        percent = _decimal(row.get("PERCNEW"))
        lines_by_auto.setdefault(auto_stamp, []).append(
            {
                "bistamp": _text_value(row.get("BISTAMP")),
                "source_bistamp": _text_value(row.get("OOBISTAMP")),
                "ref": _text_value(row.get("REF")),
                "design": _text_value(row.get("DESIGN")),
                "unit": _text_value(row.get("UNIDADE")),
                "qty": _qty(qty),
                "unit_price": _money(row.get("EDEBITO")),
                "value": _money(value),
                "percent": float(percent.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
                "vat": _number_value(row.get("IVA")),
                "vat_code": int(_number_value(row.get("TABIVA"))),
                "cost_center": _text_value(row.get("CCUSTO")),
                "order": int(_number_value(row.get("LORDEM"))),
            }
        )

    attachments_by_auto: dict[str, dict[str, Any]] = {}
    for row in attachment_rows:
        recstamp = _text_value(row.get("RECSTAMP"))
        ext = _text_value(row.get("FEXT")).lower()
        fname = _text_value(row.get("FNAME") or row.get("DESCRICAO") or "Anexo")
        filename = fname
        if ext and not filename.lower().endswith(f".{ext}"):
            filename = f"{filename}.{ext}"
        attachments_by_auto[recstamp] = {
            "stamp": _text_value(row.get("ANEXOSSTAMP")),
            "name": filename,
            "description": _text_value(row.get("DESCRICAO")),
            "ext": ext,
            "size": _int_value(row.get("FLEN")),
        }

    currency = _currency_code(contract.get("MOEDA"), company)
    return {
        "company": company,
        "contract": {
            "bostamp": _text_value(contract.get("BOSTAMP")),
            "doc_name": _text_value(contract.get("NMDOS")),
            "number": int(_number_value(contract.get("OBRANO"))),
            "year": int(_number_value(contract.get("BOANO"))),
            "date": _date_iso(contract.get("DATAOBRA")),
            "supplier_no": int(_number_value(contract.get("NO"))),
            "supplier_name": _text_value(contract.get("NOME")),
            "cost_center": _text_value(contract.get("CCUSTO") or contract.get("PROCESSO")),
            "process": _text_value(contract.get("PROCESSO")),
            "currency": currency,
        },
        "autos": [
            {
                "bostamp": _text_value(row.get("BOSTAMP")),
                "doc_name": _text_value(row.get("NMDOS")),
                "number": int(_number_value(row.get("OBRANO"))),
                "year": int(_number_value(row.get("BOANO"))),
                "contract_auto_number": int(_number_value(row.get("AUTONO"))),
                "date": _date_iso(row.get("DATAOBRA")),
                "closed": bool(row.get("FECHADA")),
                "value": _money(row.get("ETOTALDEB")),
                "currency": currency,
                "cost_center": _text_value(row.get("CCUSTO") or row.get("PROCESSO")),
                "attachment": attachments_by_auto.get(_text_value(row.get("BOSTAMP"))),
                "lines": lines_by_auto.get(_text_value(row.get("BOSTAMP")), []),
            }
            for row in auto_rows
        ],
    }


def get_auto_attachment_file(feid: Any, anexosstamp: str, user) -> dict[str, Any]:
    company = _company_for_user(feid, user)
    clean_stamp = _text_value(anexosstamp)
    if not clean_stamp:
        raise SubcontractorMeasurementsValidationError("Anexo obrigatorio.")

    with pyodbc.connect(_phc_conn_str(company["phc_db"], company.get("phc_server") or ""), timeout=20) as conn:
        cursor = conn.cursor()
        rows = _fetch_rows(
            cursor,
            """
            SELECT TOP 1
                A.ANEXOSSTAMP,
                A.RECSTAMP,
                A.DESCRICAO,
                A.FULLNAME,
                A.FNAME,
                A.FEXT,
                A.FLEN,
                DATALENGTH(A.BDADOS) AS BDADOS_LEN,
                A.BDADOS
            FROM dbo.ANEXOS A WITH (NOLOCK)
            INNER JOIN dbo.BO B WITH (NOLOCK)
              ON LTRIM(RTRIM(ISNULL(A.RECSTAMP, ''))) = LTRIM(RTRIM(ISNULL(B.BOSTAMP, '')))
            WHERE LTRIM(RTRIM(ISNULL(A.ANEXOSSTAMP, ''))) = ?
              AND LTRIM(RTRIM(ISNULL(A.ORITABLE, ''))) = 'BO'
              AND B.NDOS = ?
            """,
            (clean_stamp, MEASUREMENT_NDOS),
        )
    if not rows:
        raise SubcontractorMeasurementsNotFoundError("Anexo nao encontrado.")

    row = rows[0]
    ext = _text_value(row.get("FEXT")).lower() or "pdf"
    fname = _text_value(row.get("FNAME") or row.get("DESCRICAO") or "anexo")
    filename = fname if fname.lower().endswith(f".{ext}") else f"{fname}.{ext}"
    mime = mimetypes.guess_type(filename)[0] or ("application/pdf" if ext == "pdf" else "application/octet-stream")
    data = row.get("BDADOS")
    if data and _int_value(row.get("BDADOS_LEN")) > 0:
        if isinstance(data, memoryview):
            data = data.tobytes()
        elif not isinstance(data, bytes):
            data = bytes(data)
        return {
            "mode": "bytes",
            "stream": io.BytesIO(data),
            "filename": filename,
            "mime": mime,
        }

    fullname = _text_value(row.get("FULLNAME"))
    if fullname and os.path.isfile(fullname):
        return {
            "mode": "path",
            "path": fullname,
            "filename": filename,
            "mime": mime,
        }

    raise SubcontractorMeasurementsNotFoundError(
        "O anexo existe no PHC, mas o ficheiro nao esta acessivel a partir deste servidor."
    )


def _parse_auto_date(value: Any) -> date:
    raw = _text_value(value)
    if not raw:
        return date.today()
    try:
        return datetime.strptime(raw[:10], "%Y-%m-%d").date()
    except ValueError as exc:
        raise SubcontractorMeasurementsValidationError("Data do auto invalida.") from exc


def _user_inis(user) -> str:
    login = _text_value(getattr(user, "LOGIN", "")) or _text_value(getattr(user, "email", "")) or "APP"
    clean = re.sub(r"[^A-Z0-9]", "", login.upper())
    return (clean[:3] or "APP").ljust(3)[:3]


def _next_measurement_obrano(cursor, year: int) -> int:
    cursor.execute(
        """
        SELECT ISNULL(MAX(TRY_CONVERT(int, OBRANO)), 0) + 1
        FROM dbo.BO WITH (UPDLOCK, HOLDLOCK)
        WHERE NDOS = ?
          AND BOANO = ?
        """,
        MEASUREMENT_NDOS,
        year,
    )
    return int(cursor.fetchone()[0] or 1)


def _next_contract_autono(cursor, contract_bostamp: str) -> int:
    cursor.execute(
        """
        SELECT ISNULL(MAX(TRY_CONVERT(int, A2.AUTONO)), 0) + 1
        FROM dbo.BO2 A2 WITH (UPDLOCK, HOLDLOCK)
        INNER JOIN dbo.BO A WITH (UPDLOCK, HOLDLOCK)
            ON A.BOSTAMP = A2.BO2STAMP
        WHERE A.NDOS = ?
          AND A2.ADJBOSTAMP = ?
          AND ISNULL(A2.ANULADO, 0) = 0
        """,
        MEASUREMENT_NDOS,
        contract_bostamp,
    )
    return int(cursor.fetchone()[0] or 1)


def _load_contract_for_insert(cursor, contract_bostamp: str) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, dict[str, Decimal]]]:
    header_rows = _fetch_rows(
        cursor,
        """
        SELECT TOP 1
            C.BOSTAMP,
            C.NDOS,
            C.NMDOS,
            C.OBRANO,
            C.BOANO,
            C.DATAOBRA,
            C.NO,
            C.NOME,
            C.NCONT,
            C.MORADA,
            C.LOCAL,
            C.CODPOST,
            C.ESTAB,
            C.CCUSTO,
            C.FREF,
            C.MOEDA,
            C.FECHADA,
            C2.PROCESSO
        FROM dbo.BO C WITH (UPDLOCK, HOLDLOCK)
        LEFT JOIN dbo.BO2 C2 WITH (UPDLOCK, HOLDLOCK)
            ON C2.BO2STAMP = C.BOSTAMP
        WHERE C.NDOS = ?
          AND C.BOSTAMP = ?
        """,
        (CONTRACT_NDOS, contract_bostamp),
    )
    if not header_rows:
        raise SubcontractorMeasurementsNotFoundError("Contrato nao encontrado.")
    header = header_rows[0]
    if bool(header.get("FECHADA")):
        raise SubcontractorMeasurementsValidationError("Nao e possivel medir um contrato fechado.")

    line_rows = _fetch_rows(
        cursor,
        """
        SELECT BI.*
        FROM dbo.BI BI WITH (UPDLOCK, HOLDLOCK)
        WHERE BI.NDOS = ?
          AND BI.BOSTAMP = ?
        ORDER BY BI.LORDEM, BI.BISTAMP
        """,
        (CONTRACT_NDOS, contract_bostamp),
    )
    lines = {_stamp_key(row.get("BISTAMP")): row for row in line_rows if _stamp_key(row.get("BISTAMP"))}

    executed_rows = _fetch_rows(
        cursor,
        """
        SELECT
            ABI.OOBISTAMP AS BISTAMP,
            SUM(ISNULL(ABI.QTT, 0)) AS EXEC_QTY,
            SUM(ISNULL(ABI.ETTDEB, 0)) AS EXEC_VALUE
        FROM dbo.BO A WITH (UPDLOCK, HOLDLOCK)
        INNER JOIN dbo.BO2 A2 WITH (UPDLOCK, HOLDLOCK)
            ON A2.BO2STAMP = A.BOSTAMP
        INNER JOIN dbo.BI ABI WITH (UPDLOCK, HOLDLOCK)
            ON ABI.BOSTAMP = A.BOSTAMP
        WHERE A.NDOS = ?
          AND A2.ADJBOSTAMP = ?
          AND ISNULL(A2.ANULADO, 0) = 0
          AND LTRIM(RTRIM(ISNULL(ABI.OOBISTAMP, ''))) <> ''
        GROUP BY ABI.OOBISTAMP
        """,
        (MEASUREMENT_NDOS, contract_bostamp),
    )
    executed = {
        _stamp_key(row.get("BISTAMP")): {
            "qty": _decimal(row.get("EXEC_QTY")),
            "value": _decimal(row.get("EXEC_VALUE")),
        }
        for row in executed_rows
    }
    return header, lines, executed


def _prepare_measurement_lines(
    source_lines: dict[str, dict[str, Any]],
    executed: dict[str, dict[str, Decimal]],
    payload_lines: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []
    seen: set[str] = set()

    for item in payload_lines:
        source_bistamp = _text_value(item.get("bistamp"))
        source_key = _stamp_key(source_bistamp)
        if not source_key or source_key in seen:
            continue
        seen.add(source_key)
        source = source_lines.get(source_key)
        if not source:
            examples = ", ".join(list(source_lines.keys())[:3])
            raise SubcontractorMeasurementsValidationError(
                f"Linha de contrato invalida ({source_bistamp}). Linhas carregadas: {len(source_lines)}"
                + (f"; exemplo: {examples}" if examples else ".")
            )

        contract_qty = _decimal(source.get("QTT"))
        contract_value = _decimal(source.get("ETTDEB"))
        unit_price = _decimal(source.get("EDEBITO"))
        if not unit_price and contract_qty:
            unit_price = contract_value / contract_qty

        used = executed.get(source_key, {"qty": Decimal("0"), "value": Decimal("0")})
        remaining_qty = contract_qty - used["qty"]
        remaining_value = contract_value - used["value"]

        qty = _decimal(item.get("qty")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        if qty <= 0:
            percent = _decimal(item.get("percent"))
            amount_hint = _decimal(item.get("value"))
            if contract_qty and percent > 0:
                qty = (contract_qty * percent / Decimal("100")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            elif unit_price and amount_hint > 0:
                qty = (amount_hint / unit_price).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        if qty <= 0:
            continue
        if remaining_qty < Decimal("0"):
            remaining_qty = Decimal("0")
        if qty > remaining_qty + Decimal("0.0001"):
            raise SubcontractorMeasurementsValidationError("Uma das linhas mede acima da quantidade pendente.")

        amount_raw = qty * unit_price if unit_price else Decimal("0")
        if not amount_raw and contract_qty:
            amount_raw = contract_value * qty / contract_qty
        if not amount_raw:
            amount_raw = _decimal(item.get("value"))
        amount = amount_raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if amount > remaining_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) + Decimal("0.01"):
            raise SubcontractorMeasurementsValidationError("Uma das linhas mede acima do valor pendente.")
        if amount <= 0:
            continue

        percent = Decimal("0")
        if contract_qty:
            percent = (qty / contract_qty * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        elif contract_value:
            percent = (amount / contract_value * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        prepared.append(
            {
                "bistamp": _new_stamp(),
                "source": source,
                "source_bistamp": _text_value(source.get("BISTAMP")) or source_bistamp,
                "qty": qty,
                "amount": amount,
                "amount_raw": amount_raw.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP),
                "percent": percent,
                "unit_price": unit_price.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP),
            }
        )

    if not prepared:
        raise SubcontractorMeasurementsValidationError("Indique pelo menos uma linha com quantidade a medir.")
    return prepared


def _build_tax_totals(prepared_lines: list[dict[str, Any]]) -> dict[int, dict[str, Decimal]]:
    totals: dict[int, dict[str, Decimal]] = {}
    for line in prepared_lines:
        source = line["source"]
        code = int(_number_value(source.get("TABIVA")))
        rate = _decimal(source.get("IVA"))
        bucket = totals.setdefault(code, {"base": Decimal("0.00"), "iva": Decimal("0.00"), "taxa": rate})
        bucket["base"] += line["amount"]
        bucket["iva"] += (line["amount"] * rate / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        bucket["taxa"] = rate
    return totals


def create_measurement_auto(payload: dict[str, Any], user) -> dict[str, Any]:
    company = _company_for_user(payload.get("feid"), user)
    contract_bostamp = _text_value(payload.get("bostamp"))
    if not contract_bostamp:
        raise SubcontractorMeasurementsValidationError("Contrato obrigatorio.")
    payload_lines = payload.get("lines") or []
    if not isinstance(payload_lines, list):
        raise SubcontractorMeasurementsValidationError("Linhas invalidas.")

    dataobra = _parse_auto_date(payload.get("data_auto"))
    now_sql = datetime.now()
    hour = now_sql.strftime("%H:%M:%S")
    user_inis = _user_inis(user)
    bostamp = _new_stamp()

    conn_str = _phc_conn_str(company["phc_db"], company.get("phc_server") or "")
    with pyodbc.connect(conn_str, timeout=30) as conn:
        conn.autocommit = False
        cursor = conn.cursor()
        try:
            header, source_lines, executed = _load_contract_for_insert(cursor, contract_bostamp)
            prepared_lines = _prepare_measurement_lines(source_lines, executed, payload_lines)
            tax_totals = _build_tax_totals(prepared_lines)
            total_deb = sum((line["amount"] for line in prepared_lines), Decimal("0.00")).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )
            total_iva = sum((row["iva"] for row in tax_totals.values()), Decimal("0.00")).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )

            obrano = _next_measurement_obrano(cursor, dataobra.year)
            autono = _next_contract_autono(cursor, contract_bostamp)
            process = _text_value(header.get("PROCESSO") or header.get("CCUSTO"))
            supplier_no = int(_number_value(header.get("NO")))
            supplier_name = _text_value(header.get("NOME"))[:55]
            currency = _text_value(header.get("MOEDA")) or "EURO"

            bo_values = {
                "bostamp": bostamp,
                "nmdos": MEASUREMENT_NMDOS,
                "ndos": MEASUREMENT_NDOS,
                "obrano": obrano,
                "boano": dataobra.year,
                "dataobra": dataobra,
                "dataopen": date.today(),
                "datafecho": PHC_ZERO_DATE,
                "nome": supplier_name,
                "no": supplier_no,
                "ncont": _text_value(header.get("NCONT")),
                "morada": _text_value(header.get("MORADA")),
                "local": _text_value(header.get("LOCAL")),
                "codpost": _text_value(header.get("CODPOST")),
                "estab": int(_number_value(header.get("ESTAB"))),
                "moeda": currency,
                "ccusto": _text_value(header.get("CCUSTO") or process),
                "fref": _text_value(header.get("FREF")),
                "totaldeb": _phc_value(total_deb),
                "etotaldeb": total_deb,
                "total": _phc_value(total_deb + total_iva),
                "etotal": (total_deb + total_iva).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                "fechada": 0,
                "ousrinis": user_inis,
                "ousrdata": now_sql,
                "ousrhora": hour,
                "usrinis": user_inis,
                "usrdata": now_sql,
                "usrhora": hour,
            }
            bo_cols = _phc_columns(cursor, "BO")
            for tabiva, totals in tax_totals.items():
                if tabiva <= 0:
                    continue
                for suffix in ("1", "2"):
                    base_col = f"ebo{tabiva}{suffix}_bins"
                    vat_col = f"ebo{tabiva}{suffix}_iva"
                    local_base_col = f"bo{tabiva}{suffix}_bins"
                    local_vat_col = f"bo{tabiva}{suffix}_iva"
                    if base_col in bo_cols:
                        bo_values[base_col] = totals["base"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    if vat_col in bo_cols:
                        bo_values[vat_col] = totals["iva"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    if local_base_col in bo_cols:
                        bo_values[local_base_col] = _phc_value(totals["base"])
                    if local_vat_col in bo_cols:
                        bo_values[local_vat_col] = _phc_value(totals["iva"])
            _phc_insert(cursor, "BO", bo_values)

            _phc_insert(
                cursor,
                "BO2",
                {
                    "bo2stamp": bostamp,
                    "processo": process,
                    "adjbostamp": contract_bostamp,
                    "autobostamp": bostamp,
                    "autos": 1,
                    "autotipo": 2,
                    "autoper": 0,
                    "autono": autono,
                    "adjudicado": 1,
                    "orcamento": 0,
                    "anulado": 0,
                    "armazem": int(_number_value((prepared_lines[0]["source"] or {}).get("ARMAZEM"))) or 1,
                    "ousrinis": user_inis,
                    "ousrdata": now_sql,
                    "ousrhora": hour,
                    "usrinis": user_inis,
                    "usrdata": now_sql,
                    "usrhora": hour,
                },
            )
            _phc_insert(
                cursor,
                "BO3",
                {
                    "bo3stamp": bostamp,
                    "u_aprovdat": PHC_ZERO_DATE,
                    "u_aprovusr": "",
                    "arquivadodigital": 0,
                    "ousrinis": user_inis,
                    "ousrdata": now_sql,
                    "ousrhora": hour,
                    "usrinis": user_inis,
                    "usrdata": now_sql,
                    "usrhora": hour,
                },
            )

            tax_rates = _phc_tax_rates(cursor)
            if not tax_rates:
                tax_rates = [{"tabiva": str(code), "taxaiva": values["taxa"]} for code, values in sorted(tax_totals.items())]
            for rate in tax_rates:
                code = int(_number_value(rate.get("tabiva")))
                totals = tax_totals.get(
                    code,
                    {"base": Decimal("0.00"), "iva": Decimal("0.00"), "taxa": _decimal(rate.get("taxaiva"))},
                )
                _phc_insert(
                    cursor,
                    "BOT",
                    {
                        "botstamp": _new_stamp(),
                        "bostamp": bostamp,
                        "codigo": code,
                        "taxa": _decimal(rate.get("taxaiva")),
                        "ebaseinc": totals["base"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                        "baseinc": _phc_value(totals["base"]),
                        "evalor": totals["iva"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                        "valor": _phc_value(totals["iva"]),
                        "ousrinis": user_inis,
                        "ousrdata": now_sql,
                        "ousrhora": hour,
                        "usrinis": user_inis,
                        "usrdata": now_sql,
                        "usrhora": hour,
                    },
                )

            for idx, line in enumerate(prepared_lines, start=1):
                source = line["source"]
                line_no = int(_number_value(source.get("LORDEM"))) or idx * 1000
                bi_values = {
                    "bistamp": line["bistamp"],
                    "bostamp": bostamp,
                    "nmdos": MEASUREMENT_NMDOS,
                    "ndos": MEASUREMENT_NDOS,
                    "obrano": obrano,
                    "boano": dataobra.year,
                    "dataobra": dataobra,
                    "dataopen": date.today(),
                    "datafecho": PHC_ZERO_DATE,
                    "ref": _text_value(source.get("REF")),
                    "design": _text_value(source.get("DESIGN"))[:60],
                    "qtt": line["qty"],
                    "qtt2": line["qty"],
                    "unidade": _text_value(source.get("UNIDADE")),
                    "pu": source.get("PU") if source.get("PU") is not None else _phc_value(line["unit_price"]),
                    "debito": source.get("DEBITO") if source.get("DEBITO") is not None else _phc_value(line["unit_price"]),
                    "edebito": line["unit_price"],
                    "ttdeb": _phc_value(line["amount"]),
                    "ettdeb": line["amount"],
                    "pcusto": source.get("PCUSTO") if source.get("PCUSTO") is not None else Decimal("0"),
                    "epcusto": source.get("EPCUSTO") if source.get("EPCUSTO") is not None else Decimal("0"),
                    "prorc": source.get("PRORC") if source.get("PRORC") is not None else Decimal("0"),
                    "iva": _decimal(source.get("IVA")),
                    "tabiva": int(_number_value(source.get("TABIVA"))),
                    "ivaincl": int(_number_value(source.get("IVAINCL"))),
                    "armazem": int(_number_value(source.get("ARMAZEM"))) or 1,
                    "stipo": int(_number_value(source.get("STIPO"))),
                    "no": supplier_no,
                    "nome": supplier_name,
                    "ccusto": _text_value(source.get("CCUSTO") or header.get("CCUSTO") or process),
                    "bofref": _text_value(source.get("BOFREF") or header.get("FREF")),
                    "bifref": _text_value(source.get("BIFREF") or header.get("FREF")),
                    "familia": _text_value(source.get("FAMILIA")),
                    "lordem": line_no,
                    "lobs": _text_value(source.get("LOBS")),
                    "lobs2": _text_value(source.get("LOBS2")),
                    "oobistamp": line["source_bistamp"],
                    "oobostamp": contract_bostamp,
                    "obistamp": line["source_bistamp"],
                    "fechada": 0,
                    "ousrinis": user_inis,
                    "ousrdata": now_sql,
                    "ousrhora": hour,
                    "usrinis": user_inis,
                    "usrdata": now_sql,
                    "usrhora": hour,
                }
                _phc_insert(cursor, "BI", bi_values)
                _phc_insert(
                    cursor,
                    "BI2",
                    {
                        "bi2stamp": line["bistamp"],
                        "bostamp": bostamp,
                        "fnstamp": "",
                        "fodocnome": "",
                        "foadoc": "",
                        "fistamp": "",
                        "origbistamp": "",
                        "qttmedida": Decimal("0"),
                        "qttfalta": _decimal(source.get("QTT")),
                        "qttnew": line["qty"],
                        "percnew": line["percent"],
                        "valnew": _phc_value(line["amount_raw"]),
                        "evalnew": line["amount_raw"],
                        "ousrinis": user_inis,
                        "ousrdata": now_sql,
                        "ousrhora": hour,
                        "usrinis": user_inis,
                        "usrdata": now_sql,
                        "usrhora": hour,
                    },
                )

            conn.commit()
        except Exception:
            conn.rollback()
            raise

    return {
        "bostamp": bostamp,
        "obrano": obrano,
        "boano": dataobra.year,
        "autono": autono,
        "nmdos": MEASUREMENT_NMDOS,
        "total": _money(total_deb),
        "line_count": len(prepared_lines),
        "company": company,
    }
