"""Create INTERSOL supplier delivery notes from controlled Contract lines."""

import hashlib
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Any

from services.document_ai_purchase_order_service import _clean, _decimal, _rows, _stable_stamp


def _intersol_series(cursor) -> dict[str, dict[str, Any]]:
    """Discover and verify the demonstrated INTERSOL Contract/GdR series."""
    from services.document_ai_service import _normalize_text

    rows = _rows(cursor, 'SELECT NDOS,NMDOS FROM dbo.TS WITH (NOLOCK)')
    contracts = [
        row for row in rows
        if int(row.get('ndos') or 0) == 119
        and _normalize_text(row.get('nmdos')).replace(' ', '') == 'contrat'
    ]
    deliveries = [
        row for row in rows
        if int(row.get('ndos') or 0) == 130
        and _normalize_text(row.get('nmdos')).replace('.', '').replace(' ', '')
        in {'bonlivraisonfourn', 'bondelivraisonfourn'}
    ]
    if len(contracts) != 1 or len(deliveries) != 1:
        raise ValueError(
            'A configuração INTERSOL exige as séries Contrato 119 e Bon Livraison Fourn. 130 em TS.'
        )
    return {
        'contract': {'ndos': 119, 'name': _clean(contracts[0].get('nmdos'))},
        'delivery_note': {'ndos': 130, 'name': _clean(deliveries[0].get('nmdos'))},
    }


def _source_and_document(document: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    from services import document_ai_service as svc

    controlled = dict(document or {})
    source = svc._phc_origin_source(dict(controlled.get('customer') or {}))
    database = _clean(source.get('phc_db')).upper()
    if source.get('kind') != 'phc' or not database:
        raise ValueError('A Entidade selecionada não tem uma base PHC configurada.')
    if database != 'INTERSOL':
        raise ValueError(
            'Criar GdR a partir de Contrato está disponível apenas em INTERSOL; '
            'HSOLS_FR/GR360 continuam bloqueadas sem exemplo e configuração comprovados.'
        )
    return source, controlled


def _delivery_number(document: dict[str, Any], requested: str = '') -> str:
    selected = _clean(requested)
    def delivery_numbers(lines):
        for line in lines or []:
            if not isinstance(line, dict):
                continue
            value = _clean(line.get('origin_delivery_note_number'))
            if value:
                yield value
            children = line.get('sub_lines')
            if not isinstance(children, list):
                children = line.get('sublines')
            if isinstance(children, list):
                yield from delivery_numbers(children)

    available = list(dict.fromkeys(
        delivery_numbers(document.get('lines') or [])
    ))
    if selected:
        if selected not in available:
            raise ValueError('A GdR selecionada já não pertence às linhas controladas.')
        return selected
    if len(available) != 1:
        raise ValueError('Seleciona exatamente uma GdR para criar no PHC.')
    return available[0]


def _load_contract(cursor, contract_stamp: str, *, for_update: bool) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    lock = 'WITH (UPDLOCK,HOLDLOCK)' if for_update else 'WITH (NOLOCK)'
    headers = _rows(cursor, f"""
        SELECT TOP 1 BO.BOSTAMP,BO.NDOS,BO.NMDOS,BO.OBRANO,BO.BOANO,
            BO.DATAOBRA,BO.NO,ISNULL(BO.ESTAB,0) ESTAB,BO.NOME,BO.NCONT,
            BO.MORADA,BO.LOCAL,BO.CODPOST,BO.CCUSTO,BO.MOEDA,
            ISNULL(BO.FECHADA,0) FECHADA,ISNULL(BO2.ANULADO,0) ANULADO
        FROM dbo.BO BO {lock}
        LEFT JOIN dbo.BO2 BO2 {lock} ON BO2.BO2STAMP=BO.BOSTAMP
        WHERE BO.BOSTAMP=?
    """, contract_stamp)
    if not headers:
        raise ValueError('O Contrato selecionado já não existe no PHC.')
    lines = _rows(cursor, f"""
        SELECT BI.* FROM dbo.BI BI {lock}
        WHERE BI.BOSTAMP=? ORDER BY BI.LORDEM,BI.BISTAMP
    """, contract_stamp)
    return headers[0], lines


def _plan(
    cursor,
    document: dict[str, Any],
    requested_number: str = '',
    *,
    for_update: bool,
    existing_delivery_stamp: str = '',
) -> dict[str, Any]:
    from services import document_ai_service as svc

    number = _delivery_number(document, requested_number)
    effective = svc._effective_portal_lines(document.get('lines') or [])
    selected = [line for line in effective if _clean(line.get('origin_delivery_note_number')) == number]
    if not selected:
        raise ValueError('A GdR selecionada não contém linhas Portal efetivas.')
    selected = svc._assert_effective_portal_lines(
        selected, require_origin=True, require_cost_center=True,
    )
    contract_stamps = {_clean(line.get('phc_origin_stamp') or line.get('bostamp')) for line in selected}
    contract_stamps.discard('')
    if len(contract_stamps) != 1:
        raise ValueError('Cada GdR deve retomar linhas de um único Contrato PHC.')
    contract_stamp = next(iter(contract_stamps))
    series = _intersol_series(cursor)
    contract, source_lines = _load_contract(cursor, contract_stamp, for_update=for_update)
    if int(contract.get('ndos') or 0) != series['contract']['ndos']:
        raise ValueError('A origem selecionada não é o Contrato INTERSOL da série 119.')
    if bool(contract.get('anulado')):
        raise ValueError('O Contrato selecionado está anulado no PHC.')
    if bool(contract.get('fechada')) and not existing_delivery_stamp:
        raise ValueError('O Contrato selecionado está fechado no PHC.')

    supplier = svc._phc_provisional_supplier(cursor, dict(document.get('supplier') or {}))
    if (
        int(contract.get('no') or 0) != int(supplier.get('no') or 0)
        or int(contract.get('estab') or 0) != int(supplier.get('estab') or 0)
    ):
        raise ValueError('O fornecedor controlado não coincide com o Contrato PHC.')
    source_by_stamp = {_clean(row.get('bistamp')): row for row in source_lines}
    planned = []
    requested_by_source: dict[str, Decimal] = defaultdict(Decimal)
    for position, line in enumerate(selected, start=1):
        source_stamp = _clean(line.get('phc_origin_line_stamp') or line.get('bistamp'))
        source_line = source_by_stamp.get(source_stamp)
        if not source_line:
            raise ValueError(f'Linha {position}: o BISTAMP do Contrato já não existe.')
        article = _clean(line.get('article_ref') or line.get('article') or line.get('ref'))
        if article.upper() != _clean(source_line.get('ref')).upper():
            raise ValueError(f'Linha {position}: o Artigo não coincide com a linha do Contrato.')
        ccusto = _clean(line.get('ccusto') or line.get('project_ccusto') or line.get('cost_center'))
        if ccusto.upper() != _clean(source_line.get('ccusto')).upper():
            raise ValueError(f'Linha {position}: o Centro de Custo não coincide com a linha do Contrato.')
        quantity = _decimal(
            line.get('quantity') if line.get('quantity') is not None else line.get('qty'),
            f'Linha {position}: quantidade',
        )
        if quantity <= 0 or quantity != quantity.quantize(Decimal('0.0001')):
            raise ValueError(f'Linha {position}: confirma uma quantidade positiva com até quatro casas decimais.')
        source_quantity = abs(_decimal(source_line.get('qtt') or 0, 'Quantidade contratada'))
        if source_quantity <= 0:
            raise ValueError(f'Linha {position}: a linha do Contrato não tem quantidade válida.')
        foreign_total = abs(_decimal(
            source_line.get('ettdeb')
            if source_line.get('ettdeb') is not None
            else _decimal(source_line.get('edebito') or source_line.get('pu') or 0, 'PU') * source_quantity,
            'Total do Contrato',
        ))
        local_total = abs(_decimal(
            source_line.get('ttdeb')
            if source_line.get('ttdeb') is not None
            else _decimal(source_line.get('debito') or 0, 'PU local') * source_quantity,
            'Total local do Contrato',
        ))
        requested_by_source[source_stamp] += quantity
        planned.append({
            'portal_line_index': int(line.get('portal_line_index', position - 1)),
            'portal_subline_index': line.get('portal_subline_index'),
            'portal_line_id': _clean(line.get('portal_line_id')),
            'source': source_line,
            'quantity': quantity,
            'ccusto': ccusto,
            'foreign_net': (foreign_total * quantity / source_quantity).quantize(Decimal('0.01')),
            'local_net': (local_total * quantity / source_quantity).quantize(Decimal('0.01')),
            'tax_rate': _decimal(source_line.get('iva') or 0, 'IVA'),
            'tax_code': int(source_line.get('tabiva') or 0),
        })
    existing_by_source: dict[str, Decimal] = defaultdict(Decimal)
    if existing_delivery_stamp:
        for row in _rows(cursor, """
            SELECT OBISTAMP,SUM(ABS(ISNULL(QTT,0))) QTT
            FROM dbo.BI WITH (UPDLOCK,HOLDLOCK)
            WHERE BOSTAMP=? GROUP BY OBISTAMP
        """, existing_delivery_stamp):
            existing_by_source[_clean(row.get('obistamp'))] += abs(
                _decimal(row.get('qtt') or 0, 'Quantidade já criada')
            )
    for source_stamp, requested in requested_by_source.items():
        source_line = source_by_stamp[source_stamp]
        contracted = abs(_decimal(source_line.get('qtt') or 0, 'Quantidade contratada'))
        satisfied = abs(_decimal(source_line.get('qtt2') or 0, 'Quantidade já retomada'))
        if requested > contracted - satisfied + existing_by_source[source_stamp]:
            raise ValueError(
                f'A quantidade da GdR excede o saldo disponível da linha de Contrato {source_stamp}.'
            )
    return {
        'delivery_number': number,
        'series': series,
        'contract': contract,
        'contract_stamp': contract_stamp,
        'supplier': supplier,
        'lines': planned,
        'source_lines': source_lines,
        'requested_by_source': requested_by_source,
    }


def _header_stamp(document_stamp: str, delivery_number: str, contract_stamp: str) -> str:
    return _stable_stamp('DOCGDR', f'{document_stamp}:{delivery_number}:{contract_stamp}')


def _line_stamp(document_stamp: str, delivery_number: str, portal_line_id: str, position: int) -> str:
    identity = portal_line_id or f'position-{position}'
    return _stable_stamp('GDRLIN', f'{document_stamp}:{delivery_number}:{identity}')


def _result(
    plan: dict[str, Any],
    header: dict[str, Any],
    database: str,
    document_stamp: str,
    *,
    duplicate: bool,
) -> dict[str, Any]:
    lines = []
    for index, row in enumerate(plan['lines'], start=1):
        lines.append({
            'portal_line_index': row['portal_line_index'],
            'portal_subline_index': row.get('portal_subline_index'),
            'portal_line_id': row['portal_line_id'],
            'line_stamp': _line_stamp(
                document_stamp, plan['delivery_number'], row['portal_line_id'], index,
            ),
            'origin_line_stamp': _clean(row['source'].get('bistamp')),
            'quantity': float(row['quantity']),
        })
    return {
        'ok': True,
        'duplicate': duplicate,
        'bostamp': _clean(header.get('bostamp')),
        'ndos': int(header.get('ndos') or 0),
        'document_name': _clean(header.get('nmdos')),
        'number': int(header.get('obrano') or 0),
        'year': int(header.get('boano') or 0),
        'date': str(header.get('dataobra') or '')[:10],
        'phc_database': database,
        'delivery_note_number': plan['delivery_number'],
        'contract_stamp': plan['contract_stamp'],
        'line_stamps': lines,
        'message': (
            f'GdR n.º {int(header.get("obrano") or 0)} já estava criada no PHC.'
            if duplicate else f'GdR n.º {int(header.get("obrano") or 0)} criada no PHC.'
        ),
    }


def preview_delivery_note(document: dict[str, Any], delivery_number: str = '') -> dict[str, Any]:
    import pyodbc
    from services.phc_user_import_service import _phc_conn_str

    source, controlled = _source_and_document(document)
    database = _clean(source.get('phc_db'))
    with pyodbc.connect(_phc_conn_str(database, source.get('phc_server') or ''), timeout=15) as connection:
        plan = _plan(connection.cursor(), controlled, delivery_number, for_update=False)
    return {
        'ok': True,
        'phc_database': database,
        'delivery_note_number': plan['delivery_number'],
        'series': plan['series']['delivery_note'],
        'contract': {
            'stamp': plan['contract_stamp'],
            'number': int(plan['contract'].get('obrano') or 0),
            'year': int(plan['contract'].get('boano') or 0),
            'name': _clean(plan['contract'].get('nmdos')),
        },
        'supplier': {
            'no': int(plan['supplier'].get('no') or 0),
            'estab': int(plan['supplier'].get('estab') or 0),
            'name': _clean(plan['supplier'].get('name')),
        },
        'lines': [{
            'portal_line_index': row['portal_line_index'],
            'portal_line_id': row['portal_line_id'],
            'article': _clean(row['source'].get('ref')),
            'description': _clean(row['source'].get('design')),
            'quantity': float(row['quantity']),
            'available_quantity': float(
                abs(_decimal(row['source'].get('qtt') or 0, 'Quantidade'))
                - abs(_decimal(row['source'].get('qtt2') or 0, 'Quantidade retomada'))
            ),
            'unit': _clean(row['source'].get('unidade')),
            'project': row['ccusto'],
        } for row in plan['lines']],
    }


def create_delivery_note(
    document: dict[str, Any],
    document_stamp: str,
    delivery_number: str,
    requested_by: str,
    attachment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    import pyodbc
    from services import document_ai_service as svc
    from services.phc_user_import_service import _phc_conn_str

    source, controlled = _source_and_document(document)
    database = _clean(source.get('phc_db'))
    clean_delivery_number = _delivery_number(controlled, delivery_number)
    # The contract stamp is needed for the deterministic lock/header identity.
    effective = svc._effective_portal_lines(controlled.get('lines') or [])
    selected = [line for line in effective if _clean(line.get('origin_delivery_note_number')) == clean_delivery_number]
    contract_stamps = {_clean(line.get('phc_origin_stamp') or line.get('bostamp')) for line in selected}
    contract_stamps.discard('')
    if len(contract_stamps) != 1:
        raise ValueError('Cada GdR deve retomar linhas de um único Contrato PHC.')
    contract_stamp = next(iter(contract_stamps))
    stable_header = _header_stamp(document_stamp, clean_delivery_number, contract_stamp)
    connection = pyodbc.connect(
        _phc_conn_str(database, source.get('phc_server') or ''), timeout=15, autocommit=False,
    )
    try:
        cursor = connection.cursor()
        cursor.execute('SET TRANSACTION ISOLATION LEVEL SERIALIZABLE')
        lock = cursor.execute("""
            DECLARE @result int;
            EXEC @result=sp_getapplock @Resource=?,@LockMode='Exclusive',
                @LockOwner='Transaction',@LockTimeout=15000;
            SELECT @result;
        """, f'DOC_AI_GDR_{database}_{stable_header}').fetchone()
        if not lock or int(lock[0]) < 0:
            raise ValueError('Outra operação está a criar esta GdR. Tenta novamente.')

        existing = _rows(cursor, """
            SELECT TOP 1 BO.BOSTAMP,BO.NDOS,BO.NMDOS,BO.OBRANO,BO.BOANO,BO.DATAOBRA,
                ISNULL(BO2.ANULADO,0) ANULADO
            FROM dbo.BO BO WITH (UPDLOCK,HOLDLOCK)
            LEFT JOIN dbo.BO2 BO2 WITH (UPDLOCK,HOLDLOCK) ON BO2.BO2STAMP=BO.BOSTAMP
            WHERE BO.BOSTAMP=?
        """, stable_header)
        plan = _plan(
            cursor,
            controlled,
            clean_delivery_number,
            for_update=True,
            existing_delivery_stamp=stable_header if existing else '',
        )
        expected_line_stamps = [
            _line_stamp(document_stamp, clean_delivery_number, row['portal_line_id'], index)
            for index, row in enumerate(plan['lines'], start=1)
        ]
        if existing:
            if (
                len(existing) != 1
                or int(existing[0].get('ndos') or 0) != plan['series']['delivery_note']['ndos']
                or bool(existing[0].get('anulado'))
            ):
                raise ValueError('Já existe um documento incompatível com a identidade desta GdR.')
            current = _rows(cursor, """
                SELECT BISTAMP,OBISTAMP,OOBISTAMP,QTT FROM dbo.BI WITH (UPDLOCK,HOLDLOCK)
                WHERE BOSTAMP=? ORDER BY LORDEM,BISTAMP
            """, stable_header)
            if len(current) != len(expected_line_stamps):
                raise ValueError('A GdR já existente tem linhas diferentes; verifica-a no PHC.')
            for index, row in enumerate(current):
                planned = plan['lines'][index]
                source_stamp = _clean(planned['source'].get('bistamp'))
                if (
                    _clean(row.get('bistamp')) != expected_line_stamps[index]
                    or _clean(row.get('obistamp')) != source_stamp
                    or _clean(row.get('oobistamp')) != source_stamp
                    or _decimal(row.get('qtt') or 0, 'Quantidade') != planned['quantity']
                ):
                    raise ValueError('A GdR já existente tem dados diferentes; verifica-a no PHC.')
            connection.rollback()
            return _result(plan, existing[0], database, document_stamp, duplicate=True)

        delivery = plan['series']['delivery_note']
        contract = plan['contract']
        now = datetime.now()
        user = svc._phc_correspondence_user(cursor, requested_by)
        initials = _clean(user.get('initials') or requested_by or 'DOC')[:3]
        audit = {
            'ousrinis': initials, 'ousrdata': now, 'ousrhora': now.strftime('%H:%M:%S'),
            'usrinis': initials, 'usrdata': now, 'usrhora': now.strftime('%H:%M:%S'),
        }
        document_date = _clean(controlled.get('document_date'))
        try:
            delivery_date = datetime.fromisoformat(document_date[:10])
        except ValueError as exc:
            raise ValueError('Confirma a data antes de criar a GdR.') from exc
        year = delivery_date.year
        number = int(cursor.execute("""
            SELECT ISNULL(MAX(OBRANO),0)+1 FROM dbo.BO WITH (UPDLOCK,HOLDLOCK)
            WHERE NDOS=? AND BOANO=?
        """, delivery['ndos'], year).fetchone()[0])
        header = {
            'bostamp': stable_header, 'ndos': delivery['ndos'], 'nmdos': delivery['name'],
            'obrano': number, 'boano': year, 'dataobra': delivery_date, 'dataopen': delivery_date,
            'datafecho': delivery_date, 'no': contract.get('no'), 'estab': contract.get('estab'),
            'nome': contract.get('nome'), 'ncont': contract.get('ncont'), 'morada': contract.get('morada'),
            'local': contract.get('local'), 'codpost': contract.get('codpost'),
            'ccusto': contract.get('ccusto'), 'moeda': contract.get('moeda'),
            'maquina': clean_delivery_number[:20], 'fechada': 1,
            'obs': f'DOC_AI_GDR:{document_stamp}:{clean_delivery_number}'[:250], **audit,
        }
        foreign_net = sum((row['foreign_net'] for row in plan['lines']), Decimal('0'))
        local_net = sum((row['local_net'] for row in plan['lines']), Decimal('0'))
        foreign_tax = sum((
            (row['foreign_net'] * row['tax_rate'] / Decimal('100')).quantize(Decimal('0.01'))
            for row in plan['lines']
        ), Decimal('0'))
        local_tax = sum((
            (row['local_net'] * row['tax_rate'] / Decimal('100')).quantize(Decimal('0.01'))
            for row in plan['lines']
        ), Decimal('0'))
        header.update({
            'etotaldeb': foreign_net, 'totaldeb': local_net,
            'etotal': foreign_net + foreign_tax, 'total': local_net + local_tax,
        })
        svc._phc_insert_values(cursor, 'BO', header)
        svc._phc_insert_values(cursor, 'BO2', {'bo2stamp': stable_header, 'anulado': 0, **audit})
        svc._phc_insert_values(cursor, 'BO3', {'bo3stamp': stable_header, **audit})
        taxes: dict[int, list[Decimal]] = defaultdict(lambda: [Decimal('0'), Decimal('0'), Decimal('0'), Decimal('0')])
        for row in plan['lines']:
            bucket = taxes[row['tax_code']]
            bucket[0] += row['foreign_net']
            bucket[1] += row['local_net']
            bucket[2] += (row['foreign_net'] * row['tax_rate'] / Decimal('100')).quantize(Decimal('0.01'))
            bucket[3] += (row['local_net'] * row['tax_rate'] / Decimal('100')).quantize(Decimal('0.01'))
        for code, values in taxes.items():
            svc._phc_insert_values(cursor, 'BOT', {
                'botstamp': svc._new_stamp(), 'bostamp': stable_header,
                'codigo': code,
                'taxa': next(row['tax_rate'] for row in plan['lines'] if row['tax_code'] == code),
                'ebaseinc': values[0], 'baseinc': values[1],
                'evalor': values[2], 'valor': values[3], **audit,
            })

        result_lines = []
        for index, row in enumerate(plan['lines'], start=1):
            origin = row['source']
            line_stamp = expected_line_stamps[index - 1]
            copied = {
                key: origin.get(key)
                for key in (
                    'ref', 'design', 'unidade', 'edebito', 'debito', 'pu', 'iva', 'tabiva',
                    'ivaincl', 'armazem', 'stipo', 'familia', 'pcusto', 'epcusto', 'prorc',
                    'desconto', 'desc2', 'desc3', 'desc4', 'desc5', 'desc6', 'lobs', 'lobs2',
                )
                if origin.get(key) is not None
            }
            copied.update({
                'bistamp': line_stamp, 'bostamp': stable_header,
                'ndos': delivery['ndos'], 'nmdos': delivery['name'],
                'obrano': number, 'boano': year, 'dataobra': delivery_date,
                'no': contract.get('no'), 'nome': contract.get('nome'),
                'qtt': row['quantity'], 'qtt2': row['quantity'], 'fechada': 1,
                'ettdeb': row['foreign_net'], 'ttdeb': row['local_net'],
                'ccusto': row['ccusto'], 'lordem': index * 1000,
                'obistamp': origin.get('bistamp'), 'oobistamp': origin.get('bistamp'),
                'oobostamp': plan['contract_stamp'], **audit,
            })
            svc._phc_insert_values(cursor, 'BI', copied)
            svc._phc_insert_values(cursor, 'BI2', {'bi2stamp': line_stamp, 'bostamp': stable_header, **audit})
            result_lines.append({
                'portal_line_index': row['portal_line_index'],
                'portal_subline_index': row.get('portal_subline_index'),
                'portal_line_id': row['portal_line_id'],
                'line_stamp': line_stamp,
                'origin_line_stamp': _clean(origin.get('bistamp')),
                'quantity': float(row['quantity']),
            })

        for source_stamp, requested_quantity in plan['requested_by_source'].items():
            source_line = next(row for row in plan['source_lines'] if _clean(row.get('bistamp')) == source_stamp)
            satisfied = abs(_decimal(source_line.get('qtt2') or 0, 'Quantidade retomada')) + requested_quantity
            cursor.execute("""
                UPDATE dbo.BI SET QTT2=?,FECHADA=CASE WHEN ?>=ABS(ISNULL(QTT,0)) THEN 1 ELSE 0 END,
                    NDOC=?,NMDOC=?,FNO=?,USRINIS=?,USRDATA=?,USRHORA=?
                WHERE BISTAMP=? AND BOSTAMP=?
            """, satisfied, satisfied, delivery['ndos'], delivery['name'], number,
                           initials, now, audit['usrhora'], source_stamp, plan['contract_stamp'])
            if int(getattr(cursor, 'rowcount', 1)) != 1:
                raise ValueError('Uma linha do Contrato foi alterada durante a criação da GdR.')
        cursor.execute("""
            UPDATE dbo.BO SET FECHADA=CASE WHEN EXISTS (
                SELECT 1 FROM dbo.BI WHERE BOSTAMP=? AND ABS(ISNULL(QTT,0))>ABS(ISNULL(QTT2,0))
            ) THEN 0 ELSE 1 END,
            DATAFECHO=CASE WHEN EXISTS (
                SELECT 1 FROM dbo.BI WHERE BOSTAMP=? AND ABS(ISNULL(QTT,0))>ABS(ISNULL(QTT2,0))
            ) THEN DATAFECHO ELSE ? END,USRINIS=?,USRDATA=?,USRHORA=?
            WHERE BOSTAMP=?
        """, plan['contract_stamp'], plan['contract_stamp'], now, initials, now,
                       audit['usrhora'], plan['contract_stamp'])

        attachment_data = dict(attachment or {})
        attachment_path = _clean(attachment_data.get('path'))
        attachment_bytes = attachment_data.get('bytes') or b''
        attachment_stamp = ''
        if attachment_path and attachment_bytes:
            attachment_stamp = _stable_stamp('GDRANX', stable_header)
            svc._phc_insert_values(cursor, 'ANEXOS', {
                'anexosstamp': attachment_stamp, 'oritable': 'BO', 'tabnm': 'Dossiers Internos',
                'recstamp': stable_header, 'uniqueid': f'DOC_AI_GDR:{stable_header}',
                'descricao': hashlib.sha256(attachment_bytes).hexdigest(),
                'resumo': delivery['name'], 'fullname': attachment_path,
                'fname': _clean(attachment_data.get('name')), 'fext': 'pdf',
                'flen': len(attachment_bytes), 'tipo': 2, 'tpdoc': delivery['ndos'],
                'bdados': pyodbc.Binary(b''), **audit,
            })
        connection.commit()
        return {
            'ok': True, 'duplicate': False, 'bostamp': stable_header,
            'ndos': delivery['ndos'], 'document_name': delivery['name'],
            'number': number, 'year': year, 'date': delivery_date.date().isoformat(),
            'phc_database': database, 'delivery_note_number': clean_delivery_number,
            'contract_stamp': plan['contract_stamp'], 'anexosstamp': attachment_stamp,
            'line_stamps': result_lines,
            'message': f'GdR n.º {number} criada no PHC.',
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
