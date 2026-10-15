"""Read-only SQL adapters. No app initialization, schema creation or PHC writes."""
from __future__ import annotations

from contextlib import contextmanager
import pyodbc
from flask import current_app

from modules.gr_subcontractor_measurements.service import _phc_conn_str
from .config import SourceUnavailable


MAX_ROWS = 20000


@contextmanager
def reader(company: dict):
    connection = None
    try:
        connection = pyodbc.connect(
            _phc_conn_str(company["phc_db"], company.get("phc_server", "")),
            timeout=10, autocommit=False, attrs_before={101: 1},  # SQL_MODE_READ_ONLY
        )
        connection.timeout = 25
        yield connection.cursor()
    except pyodbc.Error as exc:
        # Neither connection strings nor salary rows belong in the error response/log.
        current_app.logger.warning("Mapas PHC: falha de leitura (SQLSTATE %s).", str(exc.args[0])[:5])
        raise SourceUnavailable("Não foi possível consultar o PHC. Os valores estão indisponíveis; tente novamente.") from None
    finally:
        if connection is not None:
            try:
                connection.rollback()
            finally:
                connection.close()


def rows(cursor, sql: str, params=()) -> list[dict]:
    cursor.execute(sql, tuple(params))
    result = cursor.fetchmany(MAX_ROWS + 1)
    if len(result) > MAX_ROWS:
        raise SourceUnavailable("A consulta excede o limite de leitura. Não foram apresentados totais parciais.")
    names = [item[0].upper() for item in cursor.description]
    return [dict(zip(names, row)) for row in result]


def columns(cursor, table: str) -> set[str]:
    return {row["COLUMN_NAME"].upper() for row in rows(cursor, """
        SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = ?
    """, (table,))}


def require(actual, required, table):
    if not set(required).issubset(actual):
        raise SourceUnavailable(f"A estrutura PHC de {table} não é compatível com esta leitura.")


def optional(alias, actual, name, default="NULL"):
    return f"{alias}.[{name}]" if name in actual else default


def payroll_rows(company, start, end, codes: list[int]) -> list[dict]:
    with reader(company) as cursor:
        pr = columns(cursor, "PR")
        line = columns(cursor, "PRRE")
        pe = columns(cursor, "PE")
        require(pr, ("PRSTAMP", "NO", "NOME", "DATA", "RECIBO"), "PR")
        require(line, ("PRSTAMP", "PRRESTAMP", "CR", "REM", "RQTT", "ERVU", "ERE"), "PRRE")
        require(pe, ("NO", "PESTAMP"), "PE")
        code_filter = f"L.CR IN ({','.join('?' for _ in codes)})" if codes else "1 = 0"
        return rows(cursor, f"""
            WITH employees AS (
                SELECT NO, MAX(PESTAMP) AS PESTAMP, COUNT(*) AS IDENTITIES
                FROM dbo.PE GROUP BY NO
            )
            SELECT P.PRSTAMP, P.NO, P.NOME, P.RECIBO, P.DATA,
                   {optional('P', pr, 'MESREF')} AS MESREF,
                   {optional('P', pr, 'ANO')} AS ANO,
                   {optional('P', pr, 'STATUS')} AS STATUS,
                   CASE WHEN E.IDENTITIES = 1 THEN E.PESTAMP END AS PESTAMP,
                   ISNULL(E.IDENTITIES, 0) AS IDENTITIES,
                   L.PRRESTAMP, L.CR, L.REM, L.RQTT, L.ERVU, L.ERE,
                   {optional('L', line, 'DTREF')} AS DTREF,
                   {optional('L', line, 'ORIPRRESTAMP')} AS ORIPRRESTAMP
            FROM dbo.PR P
            LEFT JOIN employees E ON E.NO = P.NO
            LEFT JOIN dbo.PRRE L ON L.PRSTAMP = P.PRSTAMP AND {code_filter}
            WHERE P.DATA >= ? AND P.DATA < ?
            ORDER BY P.NOME, P.NO, P.DATA, P.RECIBO, P.PRSTAMP, L.PRRESTAMP
        """, (*codes, start, end))


def employee_details(company, pestamp):
    """Read only the selected employee's current address and vehicle, never all PE data."""
    with reader(company) as cursor:
        pe, pe2 = columns(cursor, 'PE'), columns(cursor, 'PE2')
        require(pe, ('PESTAMP',), 'PE')
        fields = {'PE': [name for name in ('PESTAMP', 'MORADA', 'CODPOST', 'LOCAL', 'U_MATPRO') if name in pe],
                  'PE2': [name for name in ('PE2STAMP', 'MATRICULA') if name in pe2]}
        records = rows(cursor, 'SELECT ' + ', '.join(f'[{name}]' for name in fields['PE']) +
                       ' FROM dbo.PE WHERE PESTAMP = ?', (pestamp,))
        if len(records) != 1:
            raise SourceUnavailable('A ficha PE do trabalhador não tem uma correspondência única.')
        vehicles = []
        if 'PE2STAMP' in pe2 and 'MATRICULA' in pe2:
            vehicles = rows(cursor, 'SELECT PE2STAMP, MATRICULA FROM dbo.PE2 WHERE PE2STAMP = ?', (pestamp,))
        if len(vehicles) > 1:
            raise SourceUnavailable('A ficha PE2 do trabalhador tem correspondências múltiplas.')
        return {'pe': records[0], 'pe2': vehicles[0] if vehicles else None, 'fields': fields}


def measurement_rows(company, start, end) -> tuple[list[dict], list[dict]]:
    with reader(company) as cursor:
        series = rows(cursor, """
            SELECT NDOS, NMDOS FROM dbo.TS
            WHERE LTRIM(RTRIM(NMDOS)) COLLATE Latin1_General_CI_AI
                IN ('Situation de Travaux', 'Auto de Medição')
            ORDER BY NDOS
        """)
        if not series:
            return [], []
        bo, bo2, bi, opc = (columns(cursor, table) for table in ("BO", "BO2", "BI", "OPC"))
        require(bo, ("BOSTAMP", "NDOS", "DATAOBRA", "OBRANO", "NMDOS", "NOME", "NO", "CCUSTO"), "BO")
        require(bo2, ("BO2STAMP", "ANULADO", "PROCESSO"), "BO2")
        require(bi, ("BOSTAMP", "BISTAMP", "QTT", "ETTDEB"), "BI")
        require(opc, ("OPCSTAMP", "PROCESSO", "DESCRICAO"), "OPC")
        codes = [int(row["NDOS"]) for row in series]
        placeholders = ",".join("?" for _ in codes)
        address = optional("O", opc, "U_MORADA")
        locality = optional("O", opc, "U_LOCAL")
        result = rows(cursor, f"""
            SELECT B.BOSTAMP, B.NDOS, B.NMDOS, B.OBRANO, B.DATAOBRA,
                   B.NO AS CLIENT_NO, B.NOME AS CLIENT_NAME, B.CCUSTO, B2.PROCESSO,
                   W.OPCSTAMP, W.DESCRICAO, W.MORADA, W.LOCALIDADE, W.WORK_MATCHES,
                   L.LINE_COUNT, L.POSITIVE_LINES
            FROM dbo.BO B
            INNER JOIN dbo.BO2 B2 ON B2.BO2STAMP = B.BOSTAMP
            OUTER APPLY (
                SELECT COUNT(*) AS LINE_COUNT,
                       SUM(CASE WHEN QTT > 0 OR ETTDEB > 0 THEN 1 ELSE 0 END) AS POSITIVE_LINES
                FROM dbo.BI WHERE BOSTAMP = B.BOSTAMP
            ) L
            OUTER APPLY (
                SELECT COUNT(*) AS WORK_MATCHES,
                       CASE WHEN COUNT(*) = 1 THEN MAX(O.OPCSTAMP) END AS OPCSTAMP,
                       CASE WHEN COUNT(*) = 1 THEN MAX(O.DESCRICAO) END AS DESCRICAO,
                       CASE WHEN COUNT(*) = 1 THEN MAX({address}) END AS MORADA,
                       CASE WHEN COUNT(*) = 1 THEN MAX({locality}) END AS LOCALIDADE
                FROM dbo.OPC O
                WHERE NULLIF(LTRIM(RTRIM(B2.PROCESSO)), '') IS NOT NULL
                  AND O.PROCESSO = B2.PROCESSO
            ) W
            WHERE B.NDOS IN ({placeholders}) AND B2.ANULADO = 0
              AND B.DATAOBRA >= ? AND B.DATAOBRA < ?
            ORDER BY B.DATAOBRA, B.OBRANO, B.BOSTAMP
        """, (*codes, start, end))
        return result, series


def planned_work_rows(company, stamps):
    """Resolve master planning works by shared OPCSTAMP, never by code suffix."""
    if not stamps:
        return []
    if len(stamps) > 500:
        raise SourceUnavailable('Demasiadas obras no planeamento deste trabalhador.')
    with reader(company) as cursor:
        actual = columns(cursor, 'OPC')
        require(actual, ('OPCSTAMP', 'PROCESSO', 'NOME'), 'OPC')
        return rows(cursor, f"""SELECT O.OPCSTAMP, O.PROCESSO, O.NOME,
            {optional('O', actual, 'U_MORADA')} AS MORADA,
            {optional('O', actual, 'U_LOCAL')} AS LOCALIDADE
            FROM dbo.OPC O WHERE O.OPCSTAMP IN ({','.join('?' for _ in stamps)}) ORDER BY O.OPCSTAMP, O.PROCESSO""", stamps)
