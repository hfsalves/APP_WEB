from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
import io
import mimetypes
import os
from typing import Any

import pyodbc

from modules.gr_subcontractor_measurements.service import (
    SubcontractorMeasurementsError,
    SubcontractorMeasurementsNotFoundError,
    SubcontractorMeasurementsValidationError,
    PHC_ZERO_DATE,
    _company_for_user,
    _currency_code,
    _date_iso,
    _decimal,
    _fetch_rows,
    _int_value,
    _money,
    _new_stamp,
    _number_value,
    _phc_columns,
    _phc_conn_str,
    _phc_insert,
    _phc_tax_rates,
    _phc_value,
    _qty,
    _stamp_key,
    _text_value,
    _user_inis,
    list_companies_for_user,
)


class ClientMeasurementsError(SubcontractorMeasurementsError):
    pass


class ClientMeasurementsValidationError(SubcontractorMeasurementsValidationError):
    pass


class ClientMeasurementsNotFoundError(SubcontractorMeasurementsNotFoundError):
    pass


def _parse_filter_date(value: Any):
    from datetime import datetime

    raw = _text_value(value)
    if not raw:
        return None
    try:
        return datetime.strptime(raw[:10], "%Y-%m-%d").date()
    except ValueError as exc:
        raise ClientMeasurementsValidationError("Data invalida.") from exc


def _resolve_series(cursor) -> dict[str, dict[str, Any]]:
    rows = _fetch_rows(
        cursor,
        """
        SELECT NDOS, NMDOS, QTTDEC, PREDEC, MEDICAO, ORCAMENTO
        FROM dbo.TS WITH (NOLOCK)
        WHERE NMDOS COLLATE Latin1_General_CI_AI = 'Etude et Execution'
           OR NMDOS COLLATE Latin1_General_CI_AI = 'Situation de Travaux'
           OR NMDOS COLLATE Latin1_General_CI_AI LIKE '%Travaux%Avoir%'
        ORDER BY NDOS
        """,
        (),
    )
    budget = next(
        (row for row in rows if _text_value(row.get("NMDOS")).lower().replace("é", "e") in {"etude et execution"}),
        None,
    )
    auto = next(
        (row for row in rows if _text_value(row.get("NMDOS")).lower() == "situation de travaux"),
        None,
    )
    credit = next((row for row in rows if "avoir" in _text_value(row.get("NMDOS")).lower()), None)
    if not budget or not auto:
        raise ClientMeasurementsError(
            "A empresa nao tem as series Etude et Execution e Situation de Travaux configuradas."
        )
    return {"budget": budget, "auto": auto, "credit": credit or {}}


def _series_payload(series: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        key: {
            "ndos": int(_number_value(row.get("NDOS"))),
            "name": _text_value(row.get("NMDOS")),
            "qty_decimals": int(_number_value(row.get("QTTDEC"))),
            "price_decimals": int(_number_value(row.get("PREDEC"))),
        }
        for key, row in series.items()
        if row
    }


def list_budgets(filters: dict[str, Any], user) -> dict[str, Any]:
    company = _company_for_user(filters.get("feid"), user)
    data_inicio = _parse_filter_date(filters.get("data_inicio"))
    data_fim = _parse_filter_date(filters.get("data_fim"))
    ccusto = _text_value(filters.get("ccusto"))
    cliente = _text_value(filters.get("cliente"))
    only_open = str(filters.get("only_open") or "1").strip().lower() not in {"0", "false", "no"}

    conn_str = _phc_conn_str(company["phc_db"], company.get("phc_server") or "")
    with pyodbc.connect(conn_str, timeout=30) as conn:
        cursor = conn.cursor()
        series = _resolve_series(cursor)
        budget_ndos = int(_number_value(series["budget"].get("NDOS")))
        auto_ndos = int(_number_value(series["auto"].get("NDOS")))

        where = ["C.NDOS = ?", "ISNULL(C2.ANULADO, 0) = 0"]
        params: list[Any] = [budget_ndos]
        if data_inicio:
            where.append("C.DATAOBRA >= ?")
            params.append(data_inicio)
        if data_fim:
            where.append("C.DATAOBRA <= ?")
            params.append(data_fim)
        if ccusto:
            like = f"%{ccusto}%"
            where.append("(C.CCUSTO LIKE ? OR C2.PROCESSO LIKE ? OR C.OBRANOME LIKE ?)")
            params.extend([like, like, like])
        if cliente:
            like = f"%{cliente}%"
            if cliente.isdigit():
                where.append("(C.NO = ? OR C.NOME LIKE ?)")
                params.extend([int(cliente), like])
            else:
                where.append("C.NOME LIKE ?")
                params.append(like)
        if only_open:
            where.append("ISNULL(C.FECHADA, 0) = 0")

        sql = f"""
            WITH line_chain AS (
                SELECT
                    A.BOSTAMP AS AUTO_STAMP,
                    ABI.BISTAMP AS AUTO_LINE_STAMP,
                    ISNULL(ABI.ETTDEB, 0) AS AUTO_VALUE,
                    ABI.BISTAMP AS CURRENT_LINE_STAMP,
                    ABI.OOBISTAMP AS PARENT_LINE_STAMP,
                    0 AS DEPTH
                FROM dbo.BO A WITH (NOLOCK)
                INNER JOIN dbo.BO2 A2 WITH (NOLOCK) ON A2.BO2STAMP = A.BOSTAMP
                INNER JOIN dbo.BI ABI WITH (NOLOCK) ON ABI.BOSTAMP = A.BOSTAMP
                WHERE A.NDOS = ? AND ISNULL(A2.ANULADO, 0) = 0

                UNION ALL

                SELECT
                    LC.AUTO_STAMP,
                    LC.AUTO_LINE_STAMP,
                    LC.AUTO_VALUE,
                    P.BISTAMP,
                    P.OOBISTAMP,
                    LC.DEPTH + 1
                FROM line_chain LC
                INNER JOIN dbo.BI P WITH (NOLOCK) ON P.BISTAMP = LC.PARENT_LINE_STAMP
                WHERE LC.DEPTH < 20
            ),
            mapped_lines AS (
                SELECT DISTINCT
                    LC.AUTO_STAMP,
                    LC.AUTO_LINE_STAMP,
                    LC.AUTO_VALUE,
                    ROOT.BOSTAMP AS SOURCE_BOSTAMP
                FROM line_chain LC
                INNER JOIN dbo.BI ROOT WITH (NOLOCK) ON ROOT.BISTAMP = LC.CURRENT_LINE_STAMP
                INNER JOIN dbo.BO RB WITH (NOLOCK)
                    ON RB.BOSTAMP = ROOT.BOSTAMP AND RB.NDOS = ?
            ),
            execs AS (
                SELECT SOURCE_BOSTAMP, SUM(AUTO_VALUE) AS EXEC_VALUE
                FROM mapped_lines
                GROUP BY SOURCE_BOSTAMP
            ),
            auto_links AS (
                SELECT DISTINCT AUTO_STAMP, SOURCE_BOSTAMP FROM mapped_lines
                UNION
                SELECT DISTINCT A.BOSTAMP, A2.ADJBOSTAMP
                FROM dbo.BO A WITH (NOLOCK)
                INNER JOIN dbo.BO2 A2 WITH (NOLOCK) ON A2.BO2STAMP = A.BOSTAMP
                INNER JOIN dbo.BO SRC WITH (NOLOCK)
                    ON SRC.BOSTAMP = A2.ADJBOSTAMP AND SRC.NDOS = ?
                WHERE A.NDOS = ? AND ISNULL(A2.ANULADO, 0) = 0
            ),
            auto_counts AS (
                SELECT SOURCE_BOSTAMP, COUNT(DISTINCT AUTO_STAMP) AS AUTO_COUNT
                FROM auto_links
                GROUP BY SOURCE_BOSTAMP
            )
            SELECT TOP 300
                C.BOSTAMP, C.NDOS, C.NMDOS, C.OBRANO, C.BOANO, C.DATAOBRA,
                C.NO, C.NOME, C.CCUSTO, C.FECHADA, C.MOEDA, C.ETOTALDEB,
                C2.PROCESSO,
                ISNULL(E.EXEC_VALUE, 0) AS EXEC_VALUE,
                ISNULL(AC.AUTO_COUNT, 0) AS AUTO_COUNT
            FROM dbo.BO C WITH (NOLOCK)
            LEFT JOIN dbo.BO2 C2 WITH (NOLOCK) ON C2.BO2STAMP = C.BOSTAMP
            LEFT JOIN execs E ON E.SOURCE_BOSTAMP = C.BOSTAMP
            LEFT JOIN auto_counts AC ON AC.SOURCE_BOSTAMP = C.BOSTAMP
            WHERE {" AND ".join(where)}
            ORDER BY C.DATAOBRA DESC, C.OBRANO DESC, C.BOSTAMP DESC
            OPTION (MAXRECURSION 30)
        """
        rows = _fetch_rows(
            cursor,
            sql,
            tuple([auto_ndos, budget_ndos, budget_ndos, auto_ndos, *params]),
        )

    budgets = []
    for row in rows:
        total = _decimal(row.get("ETOTALDEB"))
        executed = _decimal(row.get("EXEC_VALUE"))
        remaining = total - executed
        progress = Decimal("0")
        if total:
            progress = (executed / total * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        budgets.append(
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
                "remaining_value": _money(remaining),
                "progress": float(progress),
                "auto_count": int(_number_value(row.get("AUTO_COUNT"))),
            }
        )
    return {"company": company, "series": _series_payload(series), "rows": budgets}


def get_budget_detail(feid: Any, bostamp: str, user) -> dict[str, Any]:
    company = _company_for_user(feid, user)
    clean_bostamp = _text_value(bostamp)
    if not clean_bostamp:
        raise ClientMeasurementsValidationError("Orcamento obrigatorio.")

    conn_str = _phc_conn_str(company["phc_db"], company.get("phc_server") or "")
    with pyodbc.connect(conn_str, timeout=30) as conn:
        cursor = conn.cursor()
        series = _resolve_series(cursor)
        budget_ndos = int(_number_value(series["budget"].get("NDOS")))
        auto_ndos = int(_number_value(series["auto"].get("NDOS")))
        header_rows = _fetch_rows(
            cursor,
            """
            SELECT TOP 1
                C.BOSTAMP, C.NMDOS, C.OBRANO, C.BOANO, C.DATAOBRA,
                C.NO, C.NOME, C.CCUSTO, C.FECHADA, C.MOEDA, C.ETOTALDEB,
                C2.PROCESSO
            FROM dbo.BO C WITH (NOLOCK)
            LEFT JOIN dbo.BO2 C2 WITH (NOLOCK) ON C2.BO2STAMP = C.BOSTAMP
            WHERE C.NDOS = ? AND C.BOSTAMP = ? AND ISNULL(C2.ANULADO, 0) = 0
            """,
            (budget_ndos, clean_bostamp),
        )
        if not header_rows:
            raise ClientMeasurementsNotFoundError("Orcamento nao encontrado.")
        header = header_rows[0]

        line_rows = _fetch_rows(
            cursor,
            """
            WITH line_chain AS (
                SELECT
                    ABI.BISTAMP AS AUTO_LINE_STAMP,
                    ISNULL(ABI.QTT, 0) AS AUTO_QTY,
                    ISNULL(ABI.ETTDEB, 0) AS AUTO_VALUE,
                    ABI.BISTAMP AS CURRENT_LINE_STAMP,
                    ABI.OOBISTAMP AS PARENT_LINE_STAMP,
                    0 AS DEPTH
                FROM dbo.BO A WITH (NOLOCK)
                INNER JOIN dbo.BO2 A2 WITH (NOLOCK) ON A2.BO2STAMP = A.BOSTAMP
                INNER JOIN dbo.BI ABI WITH (NOLOCK) ON ABI.BOSTAMP = A.BOSTAMP
                WHERE A.NDOS = ? AND ISNULL(A2.ANULADO, 0) = 0

                UNION ALL

                SELECT LC.AUTO_LINE_STAMP, LC.AUTO_QTY, LC.AUTO_VALUE,
                       P.BISTAMP, P.OOBISTAMP, LC.DEPTH + 1
                FROM line_chain LC
                INNER JOIN dbo.BI P WITH (NOLOCK) ON P.BISTAMP = LC.PARENT_LINE_STAMP
                WHERE LC.DEPTH < 20
            ),
            execs AS (
                SELECT ROOT.BISTAMP,
                       SUM(LC.AUTO_QTY) AS EXEC_QTY,
                       SUM(LC.AUTO_VALUE) AS EXEC_VALUE,
                       COUNT(*) AS AUTO_LINE_COUNT
                FROM line_chain LC
                INNER JOIN dbo.BI ROOT WITH (NOLOCK) ON ROOT.BISTAMP = LC.CURRENT_LINE_STAMP
                WHERE ROOT.NDOS = ? AND ROOT.BOSTAMP = ?
                GROUP BY ROOT.BISTAMP
            )
            SELECT
                BI.BISTAMP, BI.BOSTAMP, BI.REF, BI.DESIGN, BI.UNIDADE,
                BI.QTT, BI.EDEBITO, BI.ETTDEB, BI.IVA, BI.TABIVA,
                BI.CCUSTO, BI.LORDEM, BI.LOBS,
                ISNULL(E.EXEC_QTY, 0) AS EXEC_QTY,
                ISNULL(E.EXEC_VALUE, 0) AS EXEC_VALUE,
                ISNULL(E.AUTO_LINE_COUNT, 0) AS AUTO_LINE_COUNT
            FROM dbo.BI BI WITH (NOLOCK)
            LEFT JOIN execs E ON E.BISTAMP = BI.BISTAMP
            WHERE BI.NDOS = ? AND BI.BOSTAMP = ?
            ORDER BY BI.LORDEM, BI.BISTAMP
            OPTION (MAXRECURSION 30)
            """,
            (auto_ndos, budget_ndos, clean_bostamp, budget_ndos, clean_bostamp),
        )

        auto_rows = _fetch_rows(
            cursor,
            """
            WITH line_chain AS (
                SELECT A.BOSTAMP AUTO_STAMP, BI.BISTAMP CURRENT_LINE_STAMP,
                       BI.OOBISTAMP PARENT_LINE_STAMP, 0 DEPTH
                FROM dbo.BO A WITH (NOLOCK)
                INNER JOIN dbo.BO2 A2 WITH (NOLOCK) ON A2.BO2STAMP=A.BOSTAMP
                INNER JOIN dbo.BI BI WITH (NOLOCK) ON BI.BOSTAMP=A.BOSTAMP
                WHERE A.NDOS=? AND ISNULL(A2.ANULADO,0)=0
                UNION ALL
                SELECT LC.AUTO_STAMP,P.BISTAMP,P.OOBISTAMP,LC.DEPTH+1
                FROM line_chain LC INNER JOIN dbo.BI P WITH (NOLOCK)
                    ON P.BISTAMP=LC.PARENT_LINE_STAMP
                WHERE LC.DEPTH<20
            ), links AS (
                SELECT DISTINCT LC.AUTO_STAMP
                FROM line_chain LC INNER JOIN dbo.BI ROOT WITH (NOLOCK)
                    ON ROOT.BISTAMP=LC.CURRENT_LINE_STAMP
                WHERE ROOT.NDOS=? AND ROOT.BOSTAMP=?
                UNION
                SELECT A.BOSTAMP
                FROM dbo.BO A WITH (NOLOCK)
                INNER JOIN dbo.BO2 A2 WITH (NOLOCK) ON A2.BO2STAMP=A.BOSTAMP
                WHERE A.NDOS=? AND A2.ADJBOSTAMP=? AND ISNULL(A2.ANULADO,0)=0
            )
            SELECT A.BOSTAMP
            FROM links L INNER JOIN dbo.BO A WITH (NOLOCK) ON A.BOSTAMP=L.AUTO_STAMP
            OPTION (MAXRECURSION 30)
            """,
            (auto_ndos, budget_ndos, clean_bostamp, auto_ndos, clean_bostamp),
        )

    lines = []
    for row in line_rows:
        qty = _decimal(row.get("QTT"))
        value = _decimal(row.get("ETTDEB"))
        executed_qty = _decimal(row.get("EXEC_QTY"))
        executed_value = _decimal(row.get("EXEC_VALUE"))
        remaining_qty = qty - executed_qty
        remaining_value = value - executed_value
        progress = Decimal("0")
        if qty:
            progress = (executed_qty / qty * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        elif value:
            progress = (executed_value / value * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        lines.append(
            {
                "bistamp": _text_value(row.get("BISTAMP")),
                "ref": _text_value(row.get("REF")),
                "design": _text_value(row.get("DESIGN")),
                "unit": _text_value(row.get("UNIDADE")),
                "qty": _qty(qty),
                "unit_price": _money(row.get("EDEBITO")),
                "value": _money(value),
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
                "measurable": bool(qty or value),
            }
        )

    total = _decimal(header.get("ETOTALDEB"))
    executed = sum((_decimal(line["executed_value"]) for line in lines), Decimal("0"))
    contract = {
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
        "auto_count": len({_text_value(row.get("BOSTAMP")) for row in auto_rows}),
    }
    return {
        "company": company,
        "series": _series_payload(series),
        "contract": contract,
        "autos": [],
        "lines": lines,
    }


def get_budget_autos(feid: Any, bostamp: str, user) -> dict[str, Any]:
    detail = get_budget_detail(feid, bostamp, user)
    company = detail["company"]
    contract = detail["contract"]
    series = detail["series"]
    budget_ndos = int(series["budget"]["ndos"])
    auto_ndos = int(series["auto"]["ndos"])
    clean_bostamp = _text_value(bostamp)

    conn_str = _phc_conn_str(company["phc_db"], company.get("phc_server") or "")
    with pyodbc.connect(conn_str, timeout=30) as conn:
        cursor = conn.cursor()
        auto_rows = _fetch_rows(
            cursor,
            """
            WITH line_chain AS (
                SELECT A.BOSTAMP AUTO_STAMP, BI.BISTAMP CURRENT_LINE_STAMP,
                       BI.OOBISTAMP PARENT_LINE_STAMP, 0 DEPTH
                FROM dbo.BO A WITH (NOLOCK)
                INNER JOIN dbo.BO2 A2 WITH (NOLOCK) ON A2.BO2STAMP=A.BOSTAMP
                INNER JOIN dbo.BI BI WITH (NOLOCK) ON BI.BOSTAMP=A.BOSTAMP
                WHERE A.NDOS=? AND ISNULL(A2.ANULADO,0)=0
                UNION ALL
                SELECT LC.AUTO_STAMP,P.BISTAMP,P.OOBISTAMP,LC.DEPTH+1
                FROM line_chain LC INNER JOIN dbo.BI P WITH (NOLOCK)
                    ON P.BISTAMP=LC.PARENT_LINE_STAMP
                WHERE LC.DEPTH<20
            ), links AS (
                SELECT DISTINCT LC.AUTO_STAMP
                FROM line_chain LC INNER JOIN dbo.BI ROOT WITH (NOLOCK)
                    ON ROOT.BISTAMP=LC.CURRENT_LINE_STAMP
                WHERE ROOT.NDOS=? AND ROOT.BOSTAMP=?
                UNION
                SELECT A.BOSTAMP
                FROM dbo.BO A WITH (NOLOCK)
                INNER JOIN dbo.BO2 A2 WITH (NOLOCK) ON A2.BO2STAMP=A.BOSTAMP
                WHERE A.NDOS=? AND A2.ADJBOSTAMP=? AND ISNULL(A2.ANULADO,0)=0
            )
            SELECT A.BOSTAMP,A.NMDOS,A.OBRANO,A.BOANO,A.DATAOBRA,A.FECHADA,
                   A.ETOTALDEB,A.MOEDA,ISNULL(A2.AUTONO,0) AUTONO
            FROM links L INNER JOIN dbo.BO A WITH (NOLOCK) ON A.BOSTAMP=L.AUTO_STAMP
            LEFT JOIN dbo.BO2 A2 WITH (NOLOCK) ON A2.BO2STAMP=A.BOSTAMP
            ORDER BY A.DATAOBRA DESC,A.OBRANO DESC,A.BOSTAMP DESC
            OPTION (MAXRECURSION 30)
            """,
            (auto_ndos, budget_ndos, clean_bostamp, auto_ndos, clean_bostamp),
        )
        auto_stamps = [_text_value(row.get("BOSTAMP")) for row in auto_rows]
        line_rows: list[dict[str, Any]] = []
        attachment_rows: list[dict[str, Any]] = []
        if auto_stamps:
            placeholders = ", ".join("?" for _ in auto_stamps)
            line_rows = _fetch_rows(
                cursor,
                f"""
                SELECT BI.BOSTAMP,BI.BISTAMP,BI.OOBISTAMP,BI.REF,BI.DESIGN,
                       BI.UNIDADE,BI.QTT,BI.EDEBITO,BI.ETTDEB,BI.IVA,
                       BI.TABIVA,BI.CCUSTO,BI.LORDEM,BI2.PERCNEW,
                       BI2.QTTMEDIDA,BI2.QTTFALTA,BI2.QTTNEW,
                       BI2.EQTTMEDIDAVAL,BI2.EQTTFALTAVAL,BI2.EVALNEW
                FROM dbo.BI BI WITH (NOLOCK)
                LEFT JOIN dbo.BI2 BI2 WITH (NOLOCK) ON BI2.BI2STAMP=BI.BISTAMP
                WHERE BI.NDOS=? AND BI.BOSTAMP IN ({placeholders})
                ORDER BY BI.BOSTAMP,BI.LORDEM,BI.BISTAMP
                """,
                tuple([auto_ndos, *auto_stamps]),
            )
            attachment_rows = _fetch_rows(
                cursor,
                f"""
                WITH ranked AS (
                    SELECT A.ANEXOSSTAMP,A.RECSTAMP,A.DESCRICAO,A.FNAME,A.FEXT,A.FLEN,
                           ROW_NUMBER() OVER (
                               PARTITION BY LTRIM(RTRIM(ISNULL(A.RECSTAMP,'')))
                               ORDER BY CASE WHEN LOWER(LTRIM(RTRIM(ISNULL(A.FEXT,''))))='pdf' THEN 0 ELSE 1 END,
                                        A.AUSRDATA DESC,A.ANEXOSSTAMP DESC
                           ) RN
                    FROM dbo.ANEXOS A WITH (NOLOCK)
                    WHERE LTRIM(RTRIM(ISNULL(A.ORITABLE,'')))='BO'
                      AND LTRIM(RTRIM(ISNULL(A.RECSTAMP,''))) IN ({placeholders})
                )
                SELECT * FROM ranked WHERE RN=1
                """,
                tuple(auto_stamps),
            )

    lines_by_auto: dict[str, list[dict[str, Any]]] = {}
    for row in line_rows:
        source_qty = _decimal(row.get("QTTMEDIDA")) + _decimal(row.get("QTTFALTA"))
        current_qty = _decimal(row.get("QTTNEW")) or _decimal(row.get("QTT"))
        source_value = _decimal(row.get("EQTTMEDIDAVAL")) + _decimal(row.get("EQTTFALTAVAL"))
        current_value = _decimal(row.get("EVALNEW")) or _decimal(row.get("ETTDEB"))
        current_percent = _decimal(row.get("PERCNEW"))
        if source_qty:
            current_percent = current_qty / source_qty * Decimal("100")
        elif source_value:
            current_percent = current_value / source_value * Decimal("100")
        lines_by_auto.setdefault(_text_value(row.get("BOSTAMP")), []).append(
            {
                "bistamp": _text_value(row.get("BISTAMP")),
                "source_bistamp": _text_value(row.get("OOBISTAMP")),
                "ref": _text_value(row.get("REF")),
                "design": _text_value(row.get("DESIGN")),
                "unit": _text_value(row.get("UNIDADE")),
                "qty": _qty(row.get("QTT")),
                "unit_price": _money(row.get("EDEBITO")),
                "value": _money(row.get("ETTDEB")),
                "percent": float(current_percent.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
                "vat": _number_value(row.get("IVA")),
                "vat_code": int(_number_value(row.get("TABIVA"))),
                "cost_center": _text_value(row.get("CCUSTO")),
                "order": int(_number_value(row.get("LORDEM"))),
            }
        )
    attachments = {}
    for row in attachment_rows:
        recstamp = _text_value(row.get("RECSTAMP"))
        ext = _text_value(row.get("FEXT")).lower()
        name = _text_value(row.get("FNAME") or row.get("DESCRICAO") or "Anexo")
        if ext and not name.lower().endswith(f".{ext}"):
            name = f"{name}.{ext}"
        attachments[recstamp] = {
            "stamp": _text_value(row.get("ANEXOSSTAMP")),
            "name": name,
            "description": _text_value(row.get("DESCRICAO")),
            "ext": ext,
            "size": int(_number_value(row.get("FLEN"))),
        }

    currency = contract.get("currency") or "EUR"
    autos = []
    for row in auto_rows:
        stamp = _text_value(row.get("BOSTAMP"))
        autos.append(
            {
                "bostamp": stamp,
                "doc_name": _text_value(row.get("NMDOS")),
                "number": int(_number_value(row.get("OBRANO"))),
                "year": int(_number_value(row.get("BOANO"))),
                "date": _date_iso(row.get("DATAOBRA")),
                "closed": bool(row.get("FECHADA")),
                "value": _money(row.get("ETOTALDEB")),
                "currency": _currency_code(row.get("MOEDA"), company) or currency,
                "contract_auto_number": int(_number_value(row.get("AUTONO"))),
                "lines": lines_by_auto.get(stamp, []),
                "attachment": attachments.get(stamp),
            }
        )
    return {"company": company, "series": series, "contract": contract, "autos": autos}


def get_auto_attachment_file(feid: Any, anexosstamp: str, user) -> dict[str, Any]:
    company = _company_for_user(feid, user)
    clean_stamp = _text_value(anexosstamp)
    if not clean_stamp:
        raise ClientMeasurementsValidationError("Anexo obrigatorio.")

    conn_str = _phc_conn_str(company["phc_db"], company.get("phc_server") or "")
    with pyodbc.connect(conn_str, timeout=20) as conn:
        cursor = conn.cursor()
        auto_ndos = int(_number_value(_resolve_series(cursor)["auto"].get("NDOS")))
        rows = _fetch_rows(
            cursor,
            """
            SELECT TOP 1
                A.ANEXOSSTAMP, A.RECSTAMP, A.DESCRICAO, A.FULLNAME,
                A.FNAME, A.FEXT, A.FLEN, DATALENGTH(A.BDADOS) AS BDADOS_LEN,
                A.BDADOS
            FROM dbo.ANEXOS A WITH (NOLOCK)
            INNER JOIN dbo.BO B WITH (NOLOCK)
              ON LTRIM(RTRIM(ISNULL(A.RECSTAMP, ''))) = LTRIM(RTRIM(ISNULL(B.BOSTAMP, '')))
            WHERE LTRIM(RTRIM(ISNULL(A.ANEXOSSTAMP, ''))) = ?
              AND LTRIM(RTRIM(ISNULL(A.ORITABLE, ''))) = 'BO'
              AND B.NDOS = ?
            """,
            (clean_stamp, auto_ndos),
        )
    if not rows:
        raise ClientMeasurementsNotFoundError("Anexo nao encontrado.")

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
        return {"mode": "bytes", "stream": io.BytesIO(data), "filename": filename, "mime": mime}

    fullname = _text_value(row.get("FULLNAME"))
    if fullname and os.path.isfile(fullname):
        return {"mode": "path", "path": fullname, "filename": filename, "mime": mime}

    raise ClientMeasurementsNotFoundError(
        "O anexo existe no PHC, mas o ficheiro nao esta acessivel a partir deste servidor."
    )


def _parse_auto_date(value: Any) -> date:
    raw = _text_value(value)
    if not raw:
        return date.today()
    try:
        return datetime.strptime(raw[:10], "%Y-%m-%d").date()
    except ValueError as exc:
        raise ClientMeasurementsValidationError("Data do auto invalida.") from exc


def _next_auto_obrano(cursor, auto_ndos: int, year: int) -> int:
    cursor.execute(
        """
        SELECT ISNULL(MAX(TRY_CONVERT(int, OBRANO)), 0) + 1
        FROM dbo.BO WITH (UPDLOCK, HOLDLOCK)
        WHERE NDOS = ? AND BOANO = ?
        """,
        auto_ndos,
        year,
    )
    return int(cursor.fetchone()[0] or 1)


def _next_budget_autono(cursor, budget_ndos: int, auto_ndos: int, budget_bostamp: str) -> int:
    rows = _fetch_rows(
        cursor,
        """
        WITH line_chain AS (
            SELECT A.BOSTAMP AS AUTO_STAMP, BI.BISTAMP AS CURRENT_LINE_STAMP,
                   BI.OOBISTAMP AS PARENT_LINE_STAMP, 0 AS DEPTH
            FROM dbo.BO A WITH (UPDLOCK, HOLDLOCK)
            INNER JOIN dbo.BO2 A2 WITH (UPDLOCK, HOLDLOCK) ON A2.BO2STAMP = A.BOSTAMP
            INNER JOIN dbo.BI BI WITH (UPDLOCK, HOLDLOCK) ON BI.BOSTAMP = A.BOSTAMP
            WHERE A.NDOS = ? AND ISNULL(A2.ANULADO, 0) = 0

            UNION ALL

            SELECT LC.AUTO_STAMP, P.BISTAMP, P.OOBISTAMP, LC.DEPTH + 1
            FROM line_chain LC
            INNER JOIN dbo.BI P WITH (UPDLOCK, HOLDLOCK) ON P.BISTAMP = LC.PARENT_LINE_STAMP
            WHERE LC.DEPTH < 20
        ), links AS (
            SELECT DISTINCT LC.AUTO_STAMP
            FROM line_chain LC
            INNER JOIN dbo.BI ROOT WITH (UPDLOCK, HOLDLOCK) ON ROOT.BISTAMP = LC.CURRENT_LINE_STAMP
            WHERE ROOT.NDOS = ? AND ROOT.BOSTAMP = ?

            UNION

            SELECT A.BOSTAMP
            FROM dbo.BO A WITH (UPDLOCK, HOLDLOCK)
            INNER JOIN dbo.BO2 A2 WITH (UPDLOCK, HOLDLOCK) ON A2.BO2STAMP = A.BOSTAMP
            WHERE A.NDOS = ? AND A2.ADJBOSTAMP = ? AND ISNULL(A2.ANULADO, 0) = 0
        )
        SELECT ISNULL(MAX(TRY_CONVERT(int, A2.AUTONO)), 0) + 1 AS NEXT_NO
        FROM links L
        INNER JOIN dbo.BO2 A2 WITH (UPDLOCK, HOLDLOCK) ON A2.BO2STAMP = L.AUTO_STAMP
        OPTION (MAXRECURSION 30)
        """,
        (auto_ndos, budget_ndos, budget_bostamp, auto_ndos, budget_bostamp),
    )
    return int(_number_value(rows[0].get("NEXT_NO"))) if rows else 1


def _load_budget_for_insert(
    cursor,
    budget_ndos: int,
    auto_ndos: int,
    budget_bostamp: str,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, dict[str, Decimal]]]:
    header_rows = _fetch_rows(
        cursor,
        """
        SELECT TOP 1 C.*, C2.PROCESSO, C2.ANULADO
        FROM dbo.BO C WITH (UPDLOCK, HOLDLOCK)
        LEFT JOIN dbo.BO2 C2 WITH (UPDLOCK, HOLDLOCK) ON C2.BO2STAMP = C.BOSTAMP
        WHERE C.NDOS = ? AND C.BOSTAMP = ?
        """,
        (budget_ndos, budget_bostamp),
    )
    if not header_rows or bool(header_rows[0].get("ANULADO")):
        raise ClientMeasurementsNotFoundError("Orcamento nao encontrado.")
    header = header_rows[0]
    if bool(header.get("FECHADA")):
        raise ClientMeasurementsValidationError("Nao e possivel medir um orcamento fechado.")

    line_rows = _fetch_rows(
        cursor,
        """
        SELECT BI.*
        FROM dbo.BI BI WITH (UPDLOCK, HOLDLOCK)
        WHERE BI.NDOS = ? AND BI.BOSTAMP = ?
        ORDER BY BI.LORDEM, BI.BISTAMP
        """,
        (budget_ndos, budget_bostamp),
    )
    lines = {_stamp_key(row.get("BISTAMP")): row for row in line_rows if _stamp_key(row.get("BISTAMP"))}

    executed_rows = _fetch_rows(
        cursor,
        """
        WITH line_chain AS (
            SELECT ABI.BISTAMP AS AUTO_LINE_STAMP,
                   ISNULL(ABI.QTT, 0) AS AUTO_QTY,
                   ISNULL(ABI.ETTDEB, 0) AS AUTO_VALUE,
                   ABI.BISTAMP AS CURRENT_LINE_STAMP,
                   ABI.OOBISTAMP AS PARENT_LINE_STAMP,
                   0 AS DEPTH
            FROM dbo.BO A WITH (UPDLOCK, HOLDLOCK)
            INNER JOIN dbo.BO2 A2 WITH (UPDLOCK, HOLDLOCK) ON A2.BO2STAMP = A.BOSTAMP
            INNER JOIN dbo.BI ABI WITH (UPDLOCK, HOLDLOCK) ON ABI.BOSTAMP = A.BOSTAMP
            WHERE A.NDOS = ? AND ISNULL(A2.ANULADO, 0) = 0

            UNION ALL

            SELECT LC.AUTO_LINE_STAMP, LC.AUTO_QTY, LC.AUTO_VALUE,
                   P.BISTAMP, P.OOBISTAMP, LC.DEPTH + 1
            FROM line_chain LC
            INNER JOIN dbo.BI P WITH (UPDLOCK, HOLDLOCK) ON P.BISTAMP = LC.PARENT_LINE_STAMP
            WHERE LC.DEPTH < 20
        )
        SELECT ROOT.BISTAMP,
               SUM(LC.AUTO_QTY) AS EXEC_QTY,
               SUM(LC.AUTO_VALUE) AS EXEC_VALUE
        FROM line_chain LC
        INNER JOIN dbo.BI ROOT WITH (UPDLOCK, HOLDLOCK) ON ROOT.BISTAMP = LC.CURRENT_LINE_STAMP
        WHERE ROOT.NDOS = ? AND ROOT.BOSTAMP = ?
        GROUP BY ROOT.BISTAMP
        OPTION (MAXRECURSION 30)
        """,
        (auto_ndos, budget_ndos, budget_bostamp),
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
    tolerance = Decimal("0.0001")

    for item in payload_lines:
        source_bistamp = _text_value(item.get("bistamp"))
        source_key = _stamp_key(source_bistamp)
        if not source_key or source_key in seen:
            continue
        seen.add(source_key)
        source = source_lines.get(source_key)
        if not source:
            raise ClientMeasurementsValidationError(f"Linha de orcamento invalida ({source_bistamp}).")

        budget_qty = _decimal(source.get("QTT"))
        budget_value = _decimal(source.get("ETTDEB"))
        unit_price = _decimal(source.get("EDEBITO"))
        if not unit_price and budget_qty:
            unit_price = budget_value / budget_qty

        used = executed.get(source_key, {"qty": Decimal("0"), "value": Decimal("0")})
        prior_qty = max(Decimal("0"), used["qty"])
        prior_value = max(Decimal("0"), used["value"])
        remaining_qty = max(Decimal("0"), budget_qty - prior_qty)
        remaining_value = max(Decimal("0"), budget_value - prior_value)

        qty = _decimal(item.get("qty")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        if qty <= 0:
            percent_hint = _decimal(item.get("percent"))
            amount_hint = _decimal(item.get("value"))
            if budget_qty and percent_hint > 0:
                qty = (budget_qty * percent_hint / Decimal("100")).quantize(
                    Decimal("0.0001"), rounding=ROUND_HALF_UP
                )
            elif unit_price and amount_hint > 0:
                qty = (amount_hint / unit_price).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        if qty <= 0:
            continue
        if qty > remaining_qty + tolerance:
            raise ClientMeasurementsValidationError("Uma das linhas mede acima da quantidade pendente.")

        amount_raw = qty * unit_price if unit_price else Decimal("0")
        if not amount_raw and budget_qty:
            amount_raw = budget_value * qty / budget_qty
        if not amount_raw:
            amount_raw = _decimal(item.get("value"))
        amount = amount_raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if amount > remaining_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) + Decimal("0.01"):
            raise ClientMeasurementsValidationError("Uma das linhas mede acima do valor pendente.")
        if amount <= 0:
            continue

        current_percent = Decimal("0")
        prior_percent = Decimal("0")
        cumulative_percent = Decimal("0")
        if budget_qty:
            current_percent = qty / budget_qty * Decimal("100")
            prior_percent = prior_qty / budget_qty * Decimal("100")
            cumulative_percent = (prior_qty + qty) / budget_qty * Decimal("100")
        elif budget_value:
            current_percent = amount / budget_value * Decimal("100")
            prior_percent = prior_value / budget_value * Decimal("100")
            cumulative_percent = (prior_value + amount) / budget_value * Decimal("100")

        prepared.append(
            {
                "bistamp": _new_stamp(),
                "source": source,
                "source_bistamp": _text_value(source.get("BISTAMP")) or source_bistamp,
                "qty": qty,
                "amount": amount,
                "amount_raw": amount_raw.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP),
                "unit_price": unit_price.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP),
                "prior_qty": prior_qty,
                "prior_value": prior_value,
                "remaining_qty": remaining_qty,
                "remaining_value": remaining_value,
                "current_percent": current_percent.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                "prior_percent": prior_percent.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                "cumulative_percent": min(Decimal("100"), cumulative_percent).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                ),
            }
        )

    if not prepared:
        raise ClientMeasurementsValidationError("Indique pelo menos uma linha com quantidade a medir.")
    return prepared


def _build_tax_totals(prepared_lines: list[dict[str, Any]]) -> dict[int, dict[str, Decimal]]:
    totals: dict[int, dict[str, Decimal]] = {}
    for line in prepared_lines:
        source = line["source"]
        code = int(_number_value(source.get("TABIVA")))
        rate = _decimal(source.get("IVA"))
        bucket = totals.setdefault(code, {"base": Decimal("0.00"), "iva": Decimal("0.00"), "taxa": rate})
        bucket["base"] += line["amount"]
        bucket["iva"] += (line["amount"] * rate / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        bucket["taxa"] = rate
    return totals


def create_measurement_auto(payload: dict[str, Any], user) -> dict[str, Any]:
    company = _company_for_user(payload.get("feid"), user)
    budget_bostamp = _text_value(payload.get("bostamp"))
    if not budget_bostamp:
        raise ClientMeasurementsValidationError("Orcamento obrigatorio.")
    payload_lines = payload.get("lines") or []
    if not isinstance(payload_lines, list):
        raise ClientMeasurementsValidationError("Linhas invalidas.")

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
            series = _resolve_series(cursor)
            budget_ndos = int(_number_value(series["budget"].get("NDOS")))
            budget_nmdos = _text_value(series["budget"].get("NMDOS"))
            auto_ndos = int(_number_value(series["auto"].get("NDOS")))
            auto_nmdos = _text_value(series["auto"].get("NMDOS"))

            header, source_lines, executed = _load_budget_for_insert(
                cursor, budget_ndos, auto_ndos, budget_bostamp
            )
            prepared_lines = _prepare_measurement_lines(source_lines, executed, payload_lines)
            tax_totals = _build_tax_totals(prepared_lines)
            total_deb = sum((line["amount"] for line in prepared_lines), Decimal("0.00")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            total_iva = sum((row["iva"] for row in tax_totals.values()), Decimal("0.00")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            obrano = _next_auto_obrano(cursor, auto_ndos, dataobra.year)
            autono = _next_budget_autono(cursor, budget_ndos, auto_ndos, budget_bostamp)
            process = _text_value(header.get("PROCESSO") or header.get("CCUSTO"))
            customer_no = int(_number_value(header.get("NO")))
            customer_name = _text_value(header.get("NOME"))[:55]
            currency = _text_value(header.get("MOEDA")) or "EURO"

            bo_values = {
                "bostamp": bostamp,
                "nmdos": auto_nmdos,
                "ndos": auto_ndos,
                "obrano": obrano,
                "boano": dataobra.year,
                "dataobra": dataobra,
                "dataopen": date.today(),
                "datafecho": PHC_ZERO_DATE,
                "nome": customer_name,
                "no": customer_no,
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
                    "adjbostamp": budget_bostamp,
                    "autobostamp": bostamp,
                    "autos": 1,
                    "autotipo": 1,
                    "autoper": 30,
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
                tax_rates = [
                    {"tabiva": str(code), "taxaiva": values["taxa"]}
                    for code, values in sorted(tax_totals.items())
                ]
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
                _phc_insert(
                    cursor,
                    "BI",
                    {
                        "bistamp": line["bistamp"],
                        "bostamp": bostamp,
                        "nmdos": auto_nmdos,
                        "ndos": auto_ndos,
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
                        "no": customer_no,
                        "nome": customer_name,
                        "ccusto": _text_value(source.get("CCUSTO") or header.get("CCUSTO") or process),
                        "bofref": _text_value(source.get("BOFREF") or header.get("FREF")),
                        "bifref": _text_value(source.get("BIFREF") or header.get("FREF")),
                        "familia": _text_value(source.get("FAMILIA")),
                        "lordem": line_no,
                        "lobs": _text_value(source.get("LOBS")),
                        "lobs2": _text_value(source.get("LOBS2")),
                        "oobistamp": line["source_bistamp"],
                        "oobostamp": budget_bostamp,
                        "obistamp": line["source_bistamp"],
                        "fechada": 0,
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
                    "BI2",
                    {
                        "bi2stamp": line["bistamp"],
                        "bostamp": bostamp,
                        "fnstamp": "",
                        "fodocnome": "",
                        "foadoc": "",
                        "fistamp": "",
                        "origbistamp": "",
                        "qttmedida": line["prior_qty"],
                        "qttmedidaval": _phc_value(line["prior_value"]),
                        "eqttmedidaval": line["prior_value"],
                        "qttmedidaperc": line["prior_percent"],
                        "qttfalta": line["remaining_qty"],
                        "qttfaltaval": _phc_value(line["remaining_value"]),
                        "eqttfaltaval": line["remaining_value"],
                        "qttnew": line["qty"],
                        "valnew": _phc_value(line["amount_raw"]),
                        "evalnew": line["amount_raw"],
                        "percnew": line["cumulative_percent"],
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
        "nmdos": auto_nmdos,
        "source_nmdos": budget_nmdos,
        "total": _money(total_deb),
        "line_count": len(prepared_lines),
        "company": company,
    }


__all__ = [
    "ClientMeasurementsError",
    "create_measurement_auto",
    "get_auto_attachment_file",
    "get_budget_autos",
    "get_budget_detail",
    "list_budgets",
    "list_companies_for_user",
]
