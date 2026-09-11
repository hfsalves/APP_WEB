"""Dedicated PHC accounting workflow for Document AI supplier credit notes.

The demonstrated PHC relationship is deliberately narrow: the provisional FO
created by Reception is retained and every resulting FN points at one original
FN through FN.OFNSTAMP.  BISTAMP/GdR relationships are never inferred here.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from decimal import Decimal
from typing import Any


SUPPORTED_DATABASES = {'HSOLS_FR', 'INTERSOL'}


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal('0')


def _clean(value: Any) -> str:
    return str(value or '').strip()


def _rows(cursor, sql: str, *params: Any) -> list[dict[str, Any]]:
    result = cursor.execute(sql, *params)
    columns = [str(item[0]).lower() for item in (result.description or [])]
    return [dict(zip(columns, row)) for row in result.fetchall()]


def _source(document_data: dict[str, Any], reception: dict[str, Any]) -> tuple[dict[str, Any], str, str]:
    from services.document_ai_service import _phc_origin_source

    source = _phc_origin_source(dict(document_data.get('customer') or {}))
    database = _clean(reception.get('phc_database') or source.get('phc_db')).upper()
    fostamp = _clean(reception.get('fostamp'))
    if not fostamp or not database:
        raise ValueError('A Nota de Crédito criada pela Receção não tem uma identidade PHC completa.')
    if source.get('kind') != 'phc' or _clean(source.get('phc_db')).upper() != database:
        raise ValueError('A base PHC da Nota de Crédito não coincide com a Entidade selecionada.')
    if database == 'GR360':
        raise ValueError('A escrita de Notas de Crédito em GR360 está bloqueada até existir série e exemplo real validados.')
    if database not in SUPPORTED_DATABASES:
        raise ValueError(f'A contabilização de Notas de Crédito ainda não está validada para a base {database}.')
    return source, database, fostamp


def _effective_lines(document_data: dict[str, Any]) -> list[dict[str, Any]]:
    from services.document_ai_service import _effective_portal_lines

    lines = _effective_portal_lines(document_data.get('lines') or [])
    if not lines:
        raise ValueError('A Nota de Crédito não contém linhas efetivas.')
    return lines


def _mapping(lines: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    original_fo = ''
    mapped: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        fostamp = _clean(line.get('credit_origin_fostamp'))
        fnstamp = _clean(line.get('credit_origin_fnstamp'))
        confirmed = bool(line.get('credit_origin_confirmed'))
        if not fostamp or not fnstamp or not confirmed:
            raise ValueError('Associa manualmente cada linha da Nota de Crédito à linha FN original.')
        if original_fo and fostamp != original_fo:
            raise ValueError('Todas as linhas da Nota de Crédito têm de pertencer à mesma FO original.')
        original_fo = fostamp
        mapped.append({
            'portal_index': index,
            'portal_line_id': _clean(line.get('portal_line_id') or line.get('line_id') or f'line-{index + 1}'),
            'fostamp': fostamp,
            'fnstamp': fnstamp,
            'line': line,
        })
    if len({item['fnstamp'] for item in mapped}) != len(mapped):
        raise ValueError('Cada linha efetiva da Nota de Crédito exige uma linha FN original distinta.')
    return original_fo, mapped


def _credit_sign(current_lines: list[dict[str, Any]]) -> Decimal:
    """Preserve the PHC series convention; never invert an extracted value twice."""
    return Decimal('-1') if sum((_decimal(row.get('etiliquido')) for row in current_lines), Decimal()) < 0 else Decimal('1')


def _validate_capacity(origin: dict[str, Any], used: dict[str, Any], qty: Decimal, value: Decimal) -> None:
    if qty + _decimal(used.get('used_qtt')) > abs(_decimal(origin.get('qtt'))) + Decimal('0.0001'):
        raise ValueError('A quantidade creditada excede o saldo da linha FN original.')
    if value + _decimal(used.get('used_value')) > abs(_decimal(origin.get('etiliquido'))) + Decimal('0.02'):
        raise ValueError('O valor creditado excede o saldo da linha FN original.')


def _candidate_score(header: dict[str, Any], document: dict[str, Any]) -> tuple[int, list[str]]:
    from services.document_ai_service import _normalize_text

    score = 0
    reasons: list[str] = []
    needle = _normalize_text(' '.join(str(value or '') for value in (
        document.get('original_invoice_number'), document.get('origin_reference'),
        document.get('document_number'),
    )))
    haystack = _normalize_text(f"{header.get('adoc', '')} {header.get('docnome', '')}")
    if needle and any(token and token in haystack for token in needle.split() if len(token) >= 3):
        score += 60
        reasons.append('referência')
    wanted = abs(_decimal(dict(document.get('totals') or {}).get('gross_total')))
    actual = abs(_decimal(header.get('etotal') or header.get('total')))
    if wanted and abs(wanted - actual) <= Decimal('0.02'):
        score += 30
        reasons.append('valor')
    if _clean(document.get('document_date')) and _clean(header.get('docdata')):
        score += 10
        reasons.append('data')
    return score, reasons


def search_originals(document_data: dict[str, Any], reception: dict[str, Any], limit: int = 20) -> dict[str, Any]:
    """Return proposals only; no candidate is automatically confirmed."""
    import pyodbc
    from services.phc_user_import_service import _phc_conn_str

    document = dict(document_data or {})
    source, database, current_fostamp = _source(document, reception)
    connection = pyodbc.connect(
        _phc_conn_str(database, _clean(source.get('phc_server'))), timeout=15, autocommit=True,
    )
    try:
        cursor = connection.cursor()
        current = _rows(cursor, """
            SELECT TOP 1 CAST(ISNULL(NO,0) AS int) AS no, CAST(ISNULL(ESTAB,0) AS int) AS estab
            FROM dbo.FO WHERE FOSTAMP=?
        """, current_fostamp)
        if not current:
            raise ValueError('A Nota de Crédito criada pela Receção já não existe no PHC.')
        headers = _rows(cursor, """
            SELECT TOP (?) FOSTAMP AS fostamp, LTRIM(RTRIM(ISNULL(DOCNOME,''))) AS docnome,
                LTRIM(RTRIM(ISNULL(ADOC,''))) AS adoc, DOCDATA AS docdata,
                ISNULL(TOTAL,0) AS total, ISNULL(ETOTAL,0) AS etotal,
                CAST(ISNULL(NO,0) AS int) AS no, CAST(ISNULL(ESTAB,0) AS int) AS estab
            FROM dbo.FO
            WHERE NO=? AND ESTAB=? AND FOSTAMP<>? AND CAST(ISNULL(DOCCODE,0) AS int)<>3
            ORDER BY DOCDATA DESC, DATA DESC
        """, max(1, min(int(limit or 20), 50)), current[0]['no'], current[0]['estab'], current_fostamp)
        candidates = []
        for header in headers:
            lines = _rows(cursor, """
                SELECT FNSTAMP AS fnstamp, FOSTAMP AS fostamp,
                    LTRIM(RTRIM(ISNULL(REF,''))) AS ref, LTRIM(RTRIM(ISNULL(DESIGN,''))) AS design,
                    ISNULL(QTT,0) AS qtt, ISNULL(EPV,0) AS epv,
                    ISNULL(ETILIQUIDO,0) AS etiliquido, ISNULL(IVA,0) AS iva,
                    LTRIM(RTRIM(ISNULL(UNIDADE,''))) AS unidade, ISNULL(LORDEM,0) AS lordem
                FROM dbo.FN WHERE FOSTAMP=? ORDER BY LORDEM, FNSTAMP
            """, header['fostamp'])
            score, reasons = _candidate_score(header, document)
            candidates.append({**header, 'score': score, 'reasons': reasons, 'lines': lines})
        candidates.sort(key=lambda item: (-int(item['score']), str(item.get('docdata') or '')), reverse=False)
        return {'ok': True, 'phc_database': database, 'candidates': candidates, 'auto_selected': False}
    finally:
        connection.close()


def finalize_credit_note(
    document_data: dict[str, Any], reception: dict[str, Any], requested_by: str,
) -> dict[str, Any]:
    """Finalize the Reception FO atomically and set only FN.OFNSTAMP lineage."""
    import pyodbc
    from services.phc_user_import_service import _phc_conn_str
    from services.document_ai_service import (
        _new_stamp, _phc_correspondence_user, _phc_insert_values,
        _phc_update_values,
    )

    document = dict(document_data or {})
    source, database, current_fostamp = _source(document, reception)
    original_fostamp, mapped = _mapping(_effective_lines(document))
    connection = pyodbc.connect(
        _phc_conn_str(database, _clean(source.get('phc_server'))), timeout=15, autocommit=False,
    )
    try:
        cursor = connection.cursor()
        cursor.execute('SET TRANSACTION ISOLATION LEVEL SERIALIZABLE')
        lock = cursor.execute("""
            DECLARE @result int; EXEC @result=sp_getapplock @Resource=?, @LockMode='Exclusive',
            @LockOwner='Transaction', @LockTimeout=15000; SELECT @result;
        """, f'DOC_AI_CREDIT_FINALIZE_{database}_{current_fostamp}').fetchone()
        if not lock or int(lock[0]) < 0:
            raise RuntimeError('Não foi possível reservar a contabilização da Nota de Crédito.')

        current_headers = _rows(cursor, """
            SELECT FOSTAMP AS fostamp, CAST(ISNULL(DOCCODE,0) AS int) AS doccode,
                LTRIM(RTRIM(ISNULL(DOCNOME,''))) AS docnome, LTRIM(RTRIM(ISNULL(ADOC,''))) AS adoc,
                CAST(ISNULL(NO,0) AS int) AS no, CAST(ISNULL(ESTAB,0) AS int) AS estab,
                DATA AS data, LTRIM(RTRIM(ISNULL(OBS,''))) AS obs
            FROM dbo.FO WITH (UPDLOCK,HOLDLOCK) WHERE FOSTAMP=?
        """, current_fostamp)
        originals = _rows(cursor, """
            SELECT FOSTAMP AS fostamp, CAST(ISNULL(NO,0) AS int) AS no,
                CAST(ISNULL(ESTAB,0) AS int) AS estab
            FROM dbo.FO WITH (UPDLOCK,HOLDLOCK) WHERE FOSTAMP=?
        """, original_fostamp)
        if not current_headers or not originals:
            raise ValueError('A Nota de Crédito ou a FO original já não existe no PHC.')
        current, original = current_headers[0], originals[0]
        if int(current['doccode']) != 3:
            raise ValueError('O documento criado na Receção não é uma Nota de Crédito (DOCCODE 3).')
        if (int(current['no']), int(current['estab'])) != (int(original['no']), int(original['estab'])):
            raise ValueError('A Nota de Crédito e a FO original não pertencem ao mesmo fornecedor.')
        attachment = _rows(cursor, """
            SELECT TOP 1 ANEXOSSTAMP AS anexosstamp FROM dbo.ANEXOS WITH (UPDLOCK,HOLDLOCK)
            WHERE RECSTAMP=? AND ORITABLE='FO' AND UNIQUEID LIKE 'DOC_AI:%:FO'
        """, current_fostamp)
        current_lines = _rows(cursor, """
            SELECT FNSTAMP AS fnstamp, LTRIM(RTRIM(ISNULL(OFNSTAMP,''))) AS ofnstamp,
                LTRIM(RTRIM(ISNULL(REF,''))) AS ref, ISNULL(QTT,0) AS qtt,
                ISNULL(EPV,0) AS epv, ISNULL(ETILIQUIDO,0) AS etiliquido
            FROM dbo.FN WITH (UPDLOCK,HOLDLOCK) WHERE FOSTAMP=? ORDER BY LORDEM,FNSTAMP
        """, current_fostamp)
        wanted = [item['fnstamp'] for item in mapped]
        if current_lines and [row['ofnstamp'] for row in current_lines] == wanted:
            connection.rollback()
            return {'ok': True, 'duplicate': True, 'fostamp': current_fostamp,
                    'original_fostamp': original_fostamp, 'original_fnstamps': wanted,
                    'phc_database': database, 'final_line_count': len(current_lines),
                    'message': 'A Nota de Crédito já estava contabilizada com esta origem.'}
        if not attachment or not current_lines or any(row['ofnstamp'] for row in current_lines):
            raise ValueError('A Nota de Crédito provisória foi alterada no PHC; nenhuma linha foi substituída.')

        placeholders = ','.join('?' for _ in wanted)
        source_lines = _rows(cursor, f"""
            SELECT FNSTAMP AS fnstamp, FOSTAMP AS fostamp,
                LTRIM(RTRIM(ISNULL(REF,''))) AS ref, LTRIM(RTRIM(ISNULL(DESIGN,''))) AS design,
                ISNULL(QTT,0) AS qtt, ISNULL(PV,0) AS pv, ISNULL(EPV,0) AS epv,
                ISNULL(TILIQUIDO,0) AS tiliquido, ISNULL(ETILIQUIDO,0) AS etiliquido,
                ISNULL(IVA,0) AS iva, CAST(ISNULL(TABIVA,0) AS int) AS tabiva,
                CAST(ISNULL(ARMAZEM,1) AS int) AS armazem, LTRIM(RTRIM(ISNULL(UNIDADE,''))) AS unidade,
                LTRIM(RTRIM(ISNULL(FNCCUSTO,''))) AS fnccusto
            FROM dbo.FN WITH (UPDLOCK,HOLDLOCK)
            WHERE FNSTAMP IN ({placeholders}) AND FOSTAMP=?
        """, *wanted, original_fostamp)
        by_stamp = {row['fnstamp']: row for row in source_lines}
        if set(by_stamp) != set(wanted):
            raise ValueError('Uma linha FN original selecionada já não pertence à FO original.')
        used_rows = _rows(cursor, f"""
            SELECT LTRIM(RTRIM(OFNSTAMP)) AS ofnstamp,
                SUM(ABS(ISNULL(QTT,0))) AS used_qtt, SUM(ABS(ISNULL(ETILIQUIDO,0))) AS used_value
            FROM dbo.FN WITH (UPDLOCK,HOLDLOCK)
            WHERE OFNSTAMP IN ({placeholders}) AND FOSTAMP<>?
            GROUP BY LTRIM(RTRIM(OFNSTAMP))
        """, *wanted, current_fostamp)
        used = {row['ofnstamp']: row for row in used_rows}

        # Retain the sign convention already created by Reception. Comparison is
        # always by magnitude, avoiding a second inversion on old positive series.
        sign = _credit_sign(current_lines)
        planned = []
        for item in mapped:
            line, origin = item['line'], by_stamp[item['fnstamp']]
            qty = abs(_decimal(line.get('qty') if line.get('qty') is not None else line.get('quantity')))
            value = abs(_decimal(line.get('net_amount') if line.get('net_amount') is not None else line.get('total')))
            if qty == 0:
                qty = Decimal('1')
            if value == 0:
                value = abs(qty * _decimal(line.get('unit_price') or origin['epv']))
            already = used.get(item['fnstamp']) or {}
            _validate_capacity(origin, already, qty, value)
            planned.append((item, origin, qty * sign, value * sign))

        now = datetime.now()
        initials = _clean(_phc_correspondence_user(cursor, requested_by).get('initials') or requested_by or 'DOC')[:3]
        time_text = now.strftime('%H:%M:%S')
        cursor.execute('DELETE FROM dbo.FN WHERE FOSTAMP=?', current_fostamp)
        for order, (item, origin, qty, value) in enumerate(planned, 1):
            unit_price = (value / qty).quantize(Decimal('0.000001')) if qty else _decimal(origin['epv'])
            _phc_insert_values(cursor, 'FN', {
                'fnstamp': _new_stamp(), 'fostamp': current_fostamp, 'ofnstamp': item['fnstamp'],
                'bistamp': '', 'ref': origin['ref'], 'design': _clean(item['line'].get('description') or origin['design']),
                'docnome': current['docnome'], 'adoc': current['adoc'], 'unidade': origin['unidade'],
                'qtt': qty, 'pv': unit_price, 'epv': unit_price, 'tiliquido': value,
                'etiliquido': value, 'iva': origin['iva'], 'tabiva': int(origin['tabiva']),
                'armazem': int(origin['armazem']), 'lordem': order * 1000, 'data': current['data'],
                'fnccusto': origin['fnccusto'], 'stns': 1, 'ivaincl': 0,
                'ousrinis': initials, 'ousrdata': now, 'ousrhora': time_text,
                'usrinis': initials, 'usrdata': now, 'usrhora': time_text,
            })
        net = sum((row[3] for row in planned), Decimal())
        tax = sum((row[3] * _decimal(row[1]['iva']) / Decimal('100') for row in planned), Decimal()).quantize(Decimal('0.01'))
        _phc_update_values(cursor, 'FO', {
            'total': net + tax, 'etotal': net + tax, 'ivain': net, 'eivain': net,
            'ttiliq': net, 'ettiliq': net, 'ttiva': tax, 'ettiva': tax,
            'obs': 'Contabilizada pela Leitura Inteligente; origem FN confirmada manualmente.',
            'usrinis': initials, 'usrdata': now, 'usrhora': time_text,
        }, 'FOSTAMP=?', [current_fostamp])
        connection.commit()
        return {'ok': True, 'duplicate': False, 'fostamp': current_fostamp,
                'original_fostamp': original_fostamp, 'original_fnstamps': wanted,
                'phc_database': database, 'final_line_count': len(planned),
                'message': 'Nota de Crédito contabilizada na FO criada pela Receção.'}
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def mapping_fingerprint(document_data: dict[str, Any]) -> str:
    _, mapped = _mapping(_effective_lines(document_data))
    raw = '|'.join(f"{item['portal_line_id']}:{item['fostamp']}:{item['fnstamp']}" for item in mapped)
    return hashlib.sha256(raw.encode()).hexdigest()
