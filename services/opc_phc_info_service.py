from __future__ import annotations

from decimal import Decimal
import re
from typing import Any

import pyodbc
from flask import current_app
from sqlalchemy import text

from models import db


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
        raise RuntimeError("Ligacao client/GR360_CORE nao configurada.")
    return conn_str


def _phc_conn_str(database_name: str, server_name: str = "") -> str:
    conn_str = _replace_conn_part(_client_conn_str(), "DATABASE", database_name)
    server = str(server_name or "").strip()
    if server:
        current_server = _conn_part(conn_str, "SERVER")
        port = ""
        if "," in current_server and "," not in server:
            port = current_server.split(",", 1)[1].strip()
        conn_str = _replace_conn_part(conn_str, "SERVER", f"{server},{port}" if port else server)
    return conn_str


def _norm(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "", str(value or "").upper())


def _origin_phc_db_hint(origin: str) -> str:
    key = _norm(origin)
    if key.startswith("INTERSOL"):
        return "INTERSOL"
    if "FRANCE" in key:
        return "HSOLS_FR"
    if "ALLEMAGNE" in key or "ALEMANHA" in key or key.endswith("DE"):
        return "HSOLS_DE"
    if "ESPAGNE" in key or "ESPANHA" in key:
        return "HSOLS_ES"
    if "MAROC" in key or "MARROC" in key:
        return "HSOLS_MA"
    if "PORTUGAL" in key:
        return "HSOLS_PT"
    if "G2S" in key:
        return "HSOLS_G2S"
    if "GRE" in key:
        return "HSOLS_GRE"
    return ""


def _origin_phc_process_prefix(origin: str, database_name: str = "") -> str:
    key = _norm(origin)
    db_key = _norm(database_name)
    if key.startswith("INTERSOL") or "FRANCE" in key or db_key.endswith("FR"):
        return "FR"
    if "ALLEMAGNE" in key or "ALEMANHA" in key or key.endswith("DE") or db_key.endswith("DE"):
        return "DE"
    if "ESPAGNE" in key or "ESPANHA" in key or db_key.endswith("ES"):
        return "ES"
    if "MAROC" in key or "MARROC" in key or db_key.endswith("MA"):
        return "MA"
    if "PORTUGAL" in key or db_key.endswith("PT"):
        return "PT"
    if "G2S" in key or db_key.endswith("G2S"):
        return "GS"
    if "GRE" in key or db_key.endswith("GRE"):
        return "GR"
    return ""


def _phc_process_code(opc_processo: str, origin: str, database_name: str = "") -> str:
    processo = _as_text(opc_processo).upper()
    prefix = _origin_phc_process_prefix(origin, database_name)
    if not processo or not prefix:
        return processo
    if processo.startswith(prefix):
        return processo
    match = re.match(r"^[A-Z]+(\d+)$", processo)
    if match:
        return f"{prefix}{match.group(1)}"
    return processo


def _resolve_phc_source(origin: str) -> dict:
    hint = _origin_phc_db_hint(origin)
    rows = db.session.execute(text("""
        SELECT
            ISNULL(FEID, 0) AS FEID,
            LTRIM(RTRIM(ISNULL(NOME, ''))) AS NOME,
            LTRIM(RTRIM(ISNULL(PHC_DB, ''))) AS PHC_DB,
            LTRIM(RTRIM(ISNULL(PHC_SERVER, ''))) AS PHC_SERVER
        FROM dbo.FE
        WHERE ISNULL(ATIVA, 1) = 1
          AND LTRIM(RTRIM(ISNULL(PHC_DB, ''))) <> ''
        ORDER BY ISNULL(FEID, 0)
    """)).mappings().all()
    sources = [dict(row) for row in rows]
    if hint:
        for source in sources:
            if str(source.get("PHC_DB") or "").strip().upper() == hint.upper():
                return source
    origin_key = _norm(origin)
    for source in sources:
        if _norm(source.get("NOME") or "") and _norm(source.get("NOME") or "") in origin_key:
            return source
    raise RuntimeError(f"Empresa PHC nao encontrada para a origem da obra: {origin or '(vazia)'}")


def _as_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except Exception:
        return 0.0


def _as_text(value: Any) -> str:
    return str(value or "").strip()


def _row_dict(columns: list[str], row) -> dict:
    raw = dict(zip(columns, row))
    return {
        "processo": _as_text(raw.get("processo")),
        "origem": _as_text(raw.get("origem")),
        "oristamp": _as_text(raw.get("oristamp")),
        "descricao": _as_text(raw.get("descr")),
        "ordem": _as_float(raw.get("ordem")),
        "producao": _as_float(raw.get("nonajustments")),
        "ajustes": _as_float(raw.get("ajustments")),
        "multas": _as_float(raw.get("amendes")),
        "adiantamento": _as_float(raw.get("acompte")),
        "prorata": _as_float(raw.get("prorata")),
        "ret_garantia": _as_float(raw.get("retgarantie")),
        "ret_fim_trabalho": _as_float(raw.get("retfintrav")),
        "outras_retencoes": _as_float(raw.get("autret")),
        "iva_percentagem": _as_float(raw.get("tvap")),
        "iva": _as_float(raw.get("tvaval")),
        "total_iva": _as_float(raw.get("totalttc")),
        "desc_financeiro": _as_float(raw.get("descfinanceiro")),
        "faturado": bool(raw.get("faturado")),
        "ftstamp": _as_text(raw.get("ftstamp")),
        "ft_descricao": _as_text(raw.get("ftdescr")),
        "orcamento": bool(raw.get("orcamento")),
    }


def _fetch_all(cursor, sql: str, params: tuple = ()) -> list[dict]:
    cursor.execute(sql, params)
    columns = [col[0].lower() for col in cursor.description]
    return [_row_dict(columns, row) for row in cursor.fetchall()]


def _has_column(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute("""
        SELECT 1
        FROM sys.columns
        WHERE object_id = OBJECT_ID(?)
          AND UPPER(name) = UPPER(?)
    """, (f"dbo.{table_name}", column_name))
    return cursor.fetchone() is not None


def _with_uret_iva(sql: str, has_uret_iva: bool) -> str:
    if not has_uret_iva:
        return (
            sql.replace("GROUP BY U.ORISTAMP, __URET_IVA_EXPR__", "GROUP BY U.ORISTAMP")
               .replace("__URET_IVA_EXPR__", "CAST(0 AS decimal(9,3))")
        )
    expr = "CAST(ISNULL(U.IVA, 0) AS decimal(9,3))"
    return sql.replace("__URET_IVA_EXPR__", expr)


ORCAMENTOS_SQL = """
WITH linhas AS (
    SELECT
        BO2.PROCESSO,
        BO.BOSTAMP,
        BO.NMDOS,
        BO.OBRANO,
        BO.DATAOBRA,
        BO.MARCA,
        CAST(ISNULL(BI.IVA, 0) AS decimal(9,3)) AS TVAP,
        CAST(ROUND(CAST(BI.QTT * BI.EDEBITO * (1.0 - ISNULL(BI.DESCONTO,0)/100.0) AS decimal(19,6)), 2) AS decimal(19,2)) AS BASE_LIN
    FROM BO
    JOIN BO2 ON BO2.BO2STAMP = BO.BOSTAMP
    JOIN BI ON BI.BOSTAMP = BO.BOSTAMP
    WHERE BO.NDOS = 122
      AND LTRIM(RTRIM(ISNULL(BO2.PROCESSO, ''))) = ?
),
agg AS (
    SELECT
        PROCESSO, BOSTAMP, NMDOS, OBRANO, DATAOBRA, MARCA, TVAP,
        SUM(BASE_LIN) AS TOTAL
    FROM linhas
    GROUP BY PROCESSO, BOSTAMP, NMDOS, OBRANO, DATAOBRA, MARCA, TVAP
)
SELECT
    PROCESSO AS processo,
    'BO' AS origem,
    BOSTAMP AS oristamp,
    CAST(LTRIM(RTRIM(ISNULL(NMDOS, ''))) + ' nº ' + CAST(CAST(ISNULL(OBRANO, 0) AS numeric(18,0)) AS varchar(30)) + ' de ' + CONVERT(varchar(10), DATAOBRA, 120) AS varchar(240)) AS descr,
    CAST(100 AS numeric(10,0)) AS ordem,
    TOTAL AS nonajustments,
    CAST(0 AS decimal(19,2)) AS ajustments,
    CAST(0 AS decimal(19,2)) AS amendes,
    CAST(0 AS decimal(19,2)) AS acompte,
    CAST(0 AS decimal(19,2)) AS prorata,
    CAST(0 AS decimal(19,2)) AS retgarantie,
    CAST(0 AS decimal(19,2)) AS retfintrav,
    CAST(0 AS decimal(19,2)) AS autret,
    TVAP AS tvap,
    CAST(ROUND(TOTAL * TVAP / 100.0, 2) AS decimal(19,2)) AS tvaval,
    CAST(TOTAL + ROUND(TOTAL * TVAP / 100.0, 2) AS decimal(19,2)) AS totalttc,
    CAST(0 AS decimal(19,2)) AS descfinanceiro,
    CAST(0 AS bit) AS faturado,
    CAST('' AS varchar(25)) AS ftstamp,
    CAST('' AS varchar(240)) AS ftdescr,
    CAST(1 AS bit) AS orcamento
FROM agg
ORDER BY DATAOBRA, BOSTAMP, TVAP
"""


AUTOS_SQL = """
WITH doc AS (
    SELECT
        BO.BOSTAMP,
        BO.NDOS,
        BO.NMDOS,
        BO.OBRANO,
        BO.DATAOBRA,
        ISNULL(BO.U_RG, 0) AS BO_RG,
        ISNULL(BO.U_RFT, 0) AS BO_RFT,
        ISNULL(BO.U_PRORATA, 0) AS BO_PRORATA,
        LTRIM(RTRIM(BO.MAQUINA)) AS STNUM,
        CAST(BO.MARCA AS varchar(30)) AS COMMCLI,
        CAST(BO2.PROCESSO AS varchar(50)) AS PROCESSO,
        CASE
            WHEN ISNUMERIC(LTRIM(RTRIM(BO.MAQUINA))) = 1 THEN CONVERT(numeric(10,0), LTRIM(RTRIM(BO.MAQUINA)))
            WHEN LTRIM(RTRIM(BO.MAQUINA)) = 'AVOIR' THEN 8500
            WHEN LTRIM(RTRIM(BO.MAQUINA)) = 'FACTURE' THEN 9000
            WHEN LTRIM(RTRIM(BO.MAQUINA)) = 'DGD' THEN 9999
            ELSE 100
        END AS ORDEM,
        CASE WHEN BO.NDOS = 124 THEN -1 ELSE 1 END AS SGN
    FROM BO
    JOIN BO2 ON BO2.BO2STAMP = BO.BOSTAMP
    WHERE BO.NDOS IN (118, 124)
      AND LTRIM(RTRIM(ISNULL(BO2.PROCESSO, ''))) = ?
),
bi_c AS (
    SELECT
        BI.BOSTAMP,
        BI.BISTAMP,
        CASE
            WHEN NULLIF(LTRIM(RTRIM(BI.REF)), '') IS NULL THEN 'PROD'
            WHEN BI.REF IN ('VENTES.P.SERV.', 'V.01.01.000.0021') THEN 'PROD'
            WHEN BI.REF IN ('AJUST.CHANTIER', 'AJUSTEMENT') THEN 'AJUST'
            WHEN BI.REF = 'AMENDE' THEN 'AMENDE'
            WHEN BI.REF = 'AVANCE.CLIENT' THEN 'ACOMPTE'
            WHEN BI.REF = 'PRORATA' THEN 'PRORATA_LINHA'
            ELSE 'OUTRO'
        END AS CLS,
        CAST(ISNULL(BI.IVA, 0) AS decimal(9,3)) AS TVAP,
        CAST(ROUND(CAST(BI.QTT * BI.EDEBITO * (1.0 - ISNULL(BI.DESCONTO,0)/100.0) AS decimal(19,6)), 2) AS decimal(19,2)) AS BASE_LIN
    FROM BI
    JOIN doc D ON D.BOSTAMP = BI.BOSTAMP
),
bi_agg AS (
    SELECT
        BOSTAMP,
        TVAP,
        SUM(CASE WHEN CLS='PROD' THEN BASE_LIN ELSE 0 END) AS PROD,
        SUM(CASE WHEN CLS='AJUST' THEN BASE_LIN ELSE 0 END) AS AJUST,
        SUM(CASE WHEN CLS='AMENDE' THEN BASE_LIN ELSE 0 END) AS AMENDES,
        SUM(CASE WHEN CLS='ACOMPTE' THEN BASE_LIN ELSE 0 END) AS ACOMPTE,
        SUM(CASE WHEN CLS='PRORATA_LINHA' THEN BASE_LIN ELSE 0 END) AS PRORATA_LINHA
    FROM bi_c
    GROUP BY BOSTAMP, TVAP
),
bi_totals AS (
    SELECT
        BOSTAMP,
        SUM(PROD) AS PROD_TOTAL,
        COUNT(*) AS TAX_COUNT
    FROM bi_agg
    GROUP BY BOSTAMP
),
uret AS (
    SELECT
        U.ORISTAMP AS BOSTAMP,
        __URET_IVA_EXPR__ AS TVAP,
        SUM(CASE WHEN U.REF='RG' THEN ISNULL(U.VALOR,0) ELSE 0 END) AS RG,
        SUM(CASE WHEN U.REF='RFT' THEN ISNULL(U.VALOR,0) ELSE 0 END) AS RFT,
        SUM(CASE WHEN U.REF='PRORATA' THEN ISNULL(U.VALOR,0) ELSE 0 END) AS PRORATA_RET,
        SUM(CASE WHEN U.REF NOT IN ('RG','RFT','PRORATA') THEN ISNULL(U.VALOR,0) ELSE 0 END) AS AUTRET
    FROM U_RET U
    JOIN doc D ON D.BOSTAMP = U.ORISTAMP
    WHERE U.ORIGEM='BO'
    GROUP BY U.ORISTAMP, __URET_IVA_EXPR__
),
uret_doc AS (
    SELECT
        U.ORISTAMP AS BOSTAMP,
        COUNT(*) AS URET_COUNT
    FROM U_RET U
    JOIN doc D ON D.BOSTAMP = U.ORISTAMP
    WHERE U.ORIGEM='BO'
    GROUP BY U.ORISTAMP
),
taxas AS (
    SELECT BOSTAMP, TVAP FROM bi_agg
    UNION
    SELECT BOSTAMP, TVAP FROM uret
),
calc AS (
    SELECT
        D.PROCESSO,
        D.BOSTAMP,
        D.NMDOS,
        D.OBRANO,
        D.DATAOBRA,
        D.STNUM,
        D.ORDEM,
        D.SGN,
        T.TVAP,
        ISNULL(B.PROD,0) AS PROD,
        ISNULL(B.AJUST,0) AS AJUST,
        ISNULL(B.AMENDES,0) AS AMENDES,
        ISNULL(B.ACOMPTE,0) AS ACOMPTE,
        ISNULL(B.PRORATA_LINHA,0) + CASE
            WHEN ISNULL(UD.URET_COUNT, 0) = 0 THEN
                CASE
                    WHEN ISNULL(DT.PROD_TOTAL, 0) <> 0 THEN ISNULL(D.BO_PRORATA, 0) * ISNULL(B.PROD, 0) / DT.PROD_TOTAL
                    WHEN ISNULL(DT.TAX_COUNT, 0) <> 0 THEN ISNULL(D.BO_PRORATA, 0) / DT.TAX_COUNT
                    ELSE ISNULL(D.BO_PRORATA, 0)
                END
            ELSE ISNULL(U.PRORATA_RET,0)
        END AS PRORATA,
        CASE
            WHEN ISNULL(UD.URET_COUNT, 0) = 0 THEN
                CASE
                    WHEN ISNULL(DT.PROD_TOTAL, 0) <> 0 THEN ISNULL(D.BO_RG, 0) * ISNULL(B.PROD, 0) / DT.PROD_TOTAL
                    WHEN ISNULL(DT.TAX_COUNT, 0) <> 0 THEN ISNULL(D.BO_RG, 0) / DT.TAX_COUNT
                    ELSE ISNULL(D.BO_RG, 0)
                END
            ELSE ISNULL(U.RG,0)
        END AS RG,
        CASE
            WHEN ISNULL(UD.URET_COUNT, 0) = 0 THEN
                CASE
                    WHEN ISNULL(DT.PROD_TOTAL, 0) <> 0 THEN ISNULL(D.BO_RFT, 0) * ISNULL(B.PROD, 0) / DT.PROD_TOTAL
                    WHEN ISNULL(DT.TAX_COUNT, 0) <> 0 THEN ISNULL(D.BO_RFT, 0) / DT.TAX_COUNT
                    ELSE ISNULL(D.BO_RFT, 0)
                END
            ELSE ISNULL(U.RFT,0)
        END AS RFT,
        ISNULL(U.AUTRET,0) AS AUTRET
    FROM taxas T
    JOIN doc D ON D.BOSTAMP = T.BOSTAMP
    LEFT JOIN bi_agg B ON B.BOSTAMP = T.BOSTAMP AND B.TVAP = T.TVAP
    LEFT JOIN bi_totals DT ON DT.BOSTAMP = T.BOSTAMP
    LEFT JOIN uret U ON U.BOSTAMP = T.BOSTAMP AND U.TVAP = T.TVAP
    LEFT JOIN uret_doc UD ON UD.BOSTAMP = T.BOSTAMP
),
final AS (
    SELECT
        C.*,
        ((C.PROD - C.AJUST) - C.RG - C.RFT - C.AUTRET - C.PRORATA) AS BASE_NET
    FROM calc C
)
SELECT
    F.PROCESSO AS processo,
    'BO' AS origem,
    F.BOSTAMP AS oristamp,
    CAST(LTRIM(RTRIM(ISNULL(F.NMDOS, ''))) + ' nº ' + CAST(CAST(ISNULL(F.OBRANO, 0) AS numeric(18,0)) AS varchar(30)) + ' de ' + CONVERT(varchar(10), F.DATAOBRA, 120) AS varchar(240)) AS descr,
    F.ORDEM AS ordem,
    CAST((F.PROD - F.AJUST) * F.SGN AS decimal(19,2)) AS nonajustments,
    CAST(F.AJUST * F.SGN AS decimal(19,2)) AS ajustments,
    CAST(F.AMENDES * F.SGN AS decimal(19,2)) AS amendes,
    CAST(F.ACOMPTE * F.SGN AS decimal(19,2)) AS acompte,
    CAST(F.PRORATA * F.SGN AS decimal(19,2)) AS prorata,
    CAST(F.RG * F.SGN AS decimal(19,2)) AS retgarantie,
    CAST(F.RFT * F.SGN AS decimal(19,2)) AS retfintrav,
    CAST(F.AUTRET * F.SGN AS decimal(19,2)) AS autret,
    F.TVAP AS tvap,
    CAST(ROUND(F.BASE_NET * F.TVAP / 100.0, 2) * F.SGN AS decimal(19,2)) AS tvaval,
    CAST((F.BASE_NET + ROUND(F.BASE_NET * F.TVAP / 100.0, 2)) * F.SGN AS decimal(19,2)) AS totalttc,
    CAST(0 AS decimal(19,2)) AS descfinanceiro,
    CAST(CASE WHEN INV.FTSTAMP IS NULL THEN 0 ELSE 1 END AS bit) AS faturado,
    ISNULL(INV.FTSTAMP, '') AS ftstamp,
    ISNULL(INV.FTDESCR, '') AS ftdescr,
    CAST(0 AS bit) AS orcamento
FROM final F
OUTER APPLY (
    SELECT TOP 1
        FT.FTSTAMP,
        CAST(ISNULL(FT.NMDOC, 'Fatura') + ' nº ' + CAST(CAST(FT.FNO AS numeric(18,0)) AS varchar(30)) + ' de ' + REPLACE(CONVERT(char(10), FT.FDATA, 23), '-', '.') AS varchar(240)) AS FTDESCR
    FROM BI
    JOIN FI ON FI.BISTAMP = BI.BISTAMP
    JOIN FT ON FT.FTSTAMP = FI.FTSTAMP AND FT.NDOC IN (1,4)
    WHERE BI.BOSTAMP = F.BOSTAMP
      AND CAST(ISNULL(FI.IVA, 0) AS decimal(9,3)) = F.TVAP
    ORDER BY FT.FDATA, FT.FNO
) INV
ORDER BY F.ORDEM, F.DATAOBRA, F.BOSTAMP, F.TVAP
"""


FT_STANDALONE_SQL = """
WITH docs AS (
    SELECT
        FT.FTSTAMP,
        FT.NDOC,
        FT.NMDOC,
        FT.FNO,
        FT.FDATA,
        FT2.PROCESSO,
        CASE
            WHEN ISNUMERIC(LTRIM(RTRIM(ISNULL(FT.ENCOMENDA, '')))) = 1 THEN CONVERT(numeric(10,0), LTRIM(RTRIM(FT.ENCOMENDA)))
            WHEN FT.NDOC = 4 THEN 8500
            ELSE 9000
        END AS ORDEM
    FROM FT
    JOIN FT2 ON FT2.FT2STAMP = FT.FTSTAMP
    WHERE FT.NDOC IN (1,4)
      AND LTRIM(RTRIM(ISNULL(FT2.PROCESSO, ''))) = ?
      AND NOT EXISTS (
          SELECT 1
          FROM FI
          JOIN BI ON BI.BISTAMP = FI.BISTAMP
          JOIN BO ON BO.BOSTAMP = BI.BOSTAMP AND BO.NDOS IN (118,124)
          WHERE FI.FTSTAMP = FT.FTSTAMP
      )
),
fi_c AS (
    SELECT
        FI.FTSTAMP,
        CASE
            WHEN FI.REF IN ('AJUST.CHANTIER','AJUSTEMENT') THEN 'AJUST'
            WHEN FI.REF = 'AMENDE' THEN 'AMENDE'
            WHEN FI.REF = 'AVANCE.CLIENT' THEN 'ACOMPTE'
            WHEN FI.REF = 'PRORATA' THEN 'PRORATA_LINHA'
            WHEN NULLIF(LTRIM(RTRIM(FI.REF)), '') IS NULL THEN 'PROD'
            WHEN FI.REF IN ('VENTES.P.SERV.','V.01.01.000.0021') THEN 'PROD'
            ELSE 'OUTRO'
        END AS CLS,
        CAST(ISNULL(FI.IVA, 0) AS decimal(9,3)) AS TVAP,
        CAST(ROUND(CAST(FI.QTT * FI.EPV * (1.0 - ISNULL(FI.DESCONTO,0)/100.0) AS decimal(19,6)), 2) AS decimal(19,2)) AS BASE_LIN
    FROM FI
    JOIN docs D ON D.FTSTAMP = FI.FTSTAMP
),
fi_agg AS (
    SELECT
        FTSTAMP,
        TVAP,
        SUM(CASE WHEN CLS='PROD' THEN BASE_LIN ELSE 0 END) AS PROD,
        SUM(CASE WHEN CLS='AJUST' THEN BASE_LIN ELSE 0 END) AS AJUST,
        SUM(CASE WHEN CLS='AMENDE' THEN BASE_LIN ELSE 0 END) AS AMENDES,
        SUM(CASE WHEN CLS='ACOMPTE' THEN BASE_LIN ELSE 0 END) AS ACOMPTE,
        SUM(CASE WHEN CLS='PRORATA_LINHA' THEN BASE_LIN ELSE 0 END) AS PRORATA_LINHA
    FROM fi_c
    GROUP BY FTSTAMP, TVAP
),
uret AS (
    SELECT
        U.ORISTAMP AS FTSTAMP,
        __URET_IVA_EXPR__ AS TVAP,
        SUM(CASE WHEN U.REF='RG' THEN ISNULL(U.VALOR,0) ELSE 0 END) AS RG,
        SUM(CASE WHEN U.REF='RFT' THEN ISNULL(U.VALOR,0) ELSE 0 END) AS RFT,
        SUM(CASE WHEN U.REF='PRORATA' THEN ISNULL(U.VALOR,0) ELSE 0 END) AS PRORATA_RET,
        SUM(CASE WHEN U.REF NOT IN ('RG','RFT','PRORATA') THEN ISNULL(U.VALOR,0) ELSE 0 END) AS AUTRET
    FROM U_RET U
    JOIN docs D ON D.FTSTAMP = U.ORISTAMP
    WHERE U.ORIGEM='FT'
    GROUP BY U.ORISTAMP, __URET_IVA_EXPR__
),
taxas AS (
    SELECT FTSTAMP, TVAP FROM fi_agg
    UNION
    SELECT FTSTAMP, TVAP FROM uret
),
calc AS (
    SELECT
        D.PROCESSO,
        D.FTSTAMP,
        D.NMDOC,
        D.FNO,
        D.FDATA,
        D.ORDEM,
        T.TVAP,
        ISNULL(F.PROD,0) AS PROD,
        ISNULL(F.AJUST,0) AS AJUST,
        ISNULL(F.AMENDES,0) AS AMENDES,
        ISNULL(F.ACOMPTE,0) AS ACOMPTE,
        ISNULL(F.PRORATA_LINHA,0) + ISNULL(U.PRORATA_RET,0) AS PRORATA,
        ISNULL(U.RG,0) AS RG,
        ISNULL(U.RFT,0) AS RFT,
        ISNULL(U.AUTRET,0) AS AUTRET
    FROM taxas T
    JOIN docs D ON D.FTSTAMP = T.FTSTAMP
    LEFT JOIN fi_agg F ON F.FTSTAMP = T.FTSTAMP AND F.TVAP = T.TVAP
    LEFT JOIN uret U ON U.FTSTAMP = T.FTSTAMP AND U.TVAP = T.TVAP
)
SELECT
    PROCESSO AS processo,
    'FT' AS origem,
    FTSTAMP AS oristamp,
    CAST(ISNULL(NMDOC, 'Fatura') + ' nº ' + CAST(CAST(FNO AS numeric(18,0)) AS varchar(30)) + ' de ' + REPLACE(CONVERT(char(10), FDATA, 23), '-', '.') AS varchar(240)) AS descr,
    ORDEM AS ordem,
    CAST(PROD - AJUST AS decimal(19,2)) AS nonajustments,
    CAST(AJUST AS decimal(19,2)) AS ajustments,
    CAST(AMENDES AS decimal(19,2)) AS amendes,
    CAST(ACOMPTE AS decimal(19,2)) AS acompte,
    CAST(PRORATA AS decimal(19,2)) AS prorata,
    CAST(RG AS decimal(19,2)) AS retgarantie,
    CAST(RFT AS decimal(19,2)) AS retfintrav,
    CAST(AUTRET AS decimal(19,2)) AS autret,
    TVAP AS tvap,
    CAST(ROUND(((PROD - AJUST) - RG - RFT - AUTRET - PRORATA) * TVAP / 100.0, 2) AS decimal(19,2)) AS tvaval,
    CAST(((PROD - AJUST) - RG - RFT - AUTRET - PRORATA) + ROUND(((PROD - AJUST) - RG - RFT - AUTRET - PRORATA) * TVAP / 100.0, 2) AS decimal(19,2)) AS totalttc,
    CAST(0 AS decimal(19,2)) AS descfinanceiro,
    CAST(1 AS bit) AS faturado,
    FTSTAMP AS ftstamp,
    CAST(ISNULL(NMDOC, 'Fatura') + ' nº ' + CAST(CAST(FNO AS numeric(18,0)) AS varchar(30)) + ' de ' + REPLACE(CONVERT(char(10), FDATA, 23), '-', '.') AS varchar(240)) AS ftdescr,
    CAST(0 AS bit) AS orcamento
FROM calc
ORDER BY ORDEM, FDATA, FTSTAMP, TVAP
"""


def get_opc_phc_info(record_stamp: str) -> dict:
    row = db.session.execute(text("""
        SELECT TOP 1
            LTRIM(RTRIM(ISNULL(OPCSTAMP, ''))) AS OPCSTAMP,
            LTRIM(RTRIM(ISNULL(PROCESSO, ''))) AS PROCESSO,
            LTRIM(RTRIM(ISNULL(DESCRICAO, ''))) AS DESCRICAO,
            LTRIM(RTRIM(ISNULL(U_ORIGEM, ''))) AS U_ORIGEM
        FROM dbo.OPC
        WHERE LTRIM(RTRIM(ISNULL(OPCSTAMP, ''))) = :stamp
    """), {"stamp": str(record_stamp or "").strip()}).mappings().first()
    if not row:
        raise RuntimeError("Obra OPC nao encontrada.")

    processo = _as_text(row.get("PROCESSO"))
    source = _resolve_phc_source(row.get("U_ORIGEM") or "")
    database_name = _as_text(source.get("PHC_DB"))
    phc_processo = _phc_process_code(processo, row.get("U_ORIGEM") or "", database_name)
    conn_str = _phc_conn_str(database_name, source.get("PHC_SERVER") or "")

    with pyodbc.connect(conn_str, timeout=15) as conn:
        cursor = conn.cursor()
        has_uret_iva = _has_column(cursor, "U_RET", "IVA")
        orcamentos = _fetch_all(cursor, ORCAMENTOS_SQL, (phc_processo,))
        autos = _fetch_all(cursor, _with_uret_iva(AUTOS_SQL, has_uret_iva), (phc_processo,))
        autos.extend(_fetch_all(cursor, _with_uret_iva(FT_STANDALONE_SQL, has_uret_iva), (phc_processo,)))
        autos.sort(key=lambda item: (item.get("ordem") or 0, item.get("descricao") or "", item.get("iva_percentagem") or 0))

    return {
        "obra": {
            "opcstamp": _as_text(row.get("OPCSTAMP")),
            "processo": processo,
            "phc_processo": phc_processo,
            "descricao": _as_text(row.get("DESCRICAO")),
            "origem": _as_text(row.get("U_ORIGEM")),
        },
        "fonte": {
            "feid": int(source.get("FEID") or 0),
            "nome": _as_text(source.get("NOME")),
            "phc_db": database_name,
            "phc_server": _as_text(source.get("PHC_SERVER")),
        },
        "orcamentos": orcamentos,
        "autos": autos,
    }
