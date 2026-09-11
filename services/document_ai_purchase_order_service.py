"""Create and correct PHC supplier purchase orders from controlled Document AI data."""

import hashlib
import json
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any


def _clean(value: Any) -> str:
    return str(value or '').strip()


def _decimal(value: Any, label: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f'{label} não é válido.') from exc
    if not result.is_finite():
        raise ValueError(f'{label} não é válido.')
    return result


def _money(value: Any, label: str = 'O valor') -> Decimal:
    return _decimal(value, label).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _unit_price(value: Any, label: str) -> Decimal:
    return _decimal(value, label).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)


def _rows(cursor, sql: str, *params: Any) -> list[dict[str, Any]]:
    cursor.execute(sql, *params)
    columns = [str(item[0]).lower() for item in cursor.description or []]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


FLOW_CONFIG = {
    'purchase_order': {
        'label': 'Nota de Encomenda', 'lock': 'NDE', 'stamp': 'DOCNDE',
        'matches': lambda value: value in {'boncommandefournisseur', 'notadeencomendafornecedor'},
    },
    'contract': {
        'label': 'Contrato', 'lock': 'CONTRACT', 'stamp': 'DOCCON',
        'matches': lambda value: 'contrat' in value and 'soustraitant' not in value and 'souttraitant' not in value,
    },
    'subcontract': {
        'label': 'Contrato Sub.Emp.', 'lock': 'SUBCONTRACT', 'stamp': 'DOCSUB',
        'matches': lambda value: 'contrat' in value and ('soustraitant' in value or 'souttraitant' in value),
    },
}


def _flow_config(family: str) -> dict[str, Any]:
    config = FLOW_CONFIG.get(_clean(family).lower())
    if not config:
        raise ValueError('Família de documento PHC inválida.')
    return config


def _purchase_order_series(cursor, family: str = 'purchase_order') -> dict[str, Any]:
    from services.document_ai_service import _normalize_text

    config = _flow_config(family)
    matches = []
    for row in _rows(cursor, 'SELECT NDOS,NMDOS FROM dbo.TS WITH (NOLOCK)'):
        normalized = _normalize_text(row.get('nmdos')).replace('-', '').replace(' ', '')
        if config['matches'](normalized):
            matches.append(row)
    if len(matches) != 1:
        raise ValueError(f"Não foi possível identificar uma única série de {config['label']} em TS.NMDOS.")
    return {'ndos': int(matches[0]['ndos']), 'name': _clean(matches[0]['nmdos'])}


def _stable_stamp(prefix: str, value: str) -> str:
    clean_prefix = ''.join(char for char in prefix.upper() if char.isalnum())[:6]
    return f'{clean_prefix}{hashlib.sha1(value.encode()).hexdigest().upper()}'[:25]


def _planned_line_stamp(document_stamp: str, row: dict[str, Any], position: int, prefix: str = 'DNELIN') -> str:
    """Keep a new PHC line stable when Portal lines are reordered or retried."""
    existing = _clean(row.get('bistamp'))
    if existing:
        return existing
    identity = _clean(row.get('portal_line_id')) or f'position-{position}'
    return _stable_stamp(prefix, f'{document_stamp}:{identity}')


def _snapshot(header: dict[str, Any], lines: list[dict[str, Any]]) -> str:
    content = {
        'header': {
            key: header.get(key)
            for key in ('bostamp', 'ndos', 'obrano', 'boano', 'dataobra', 'no', 'estab', 'ccusto',
                        'moeda', 'fechada', 'anulado', 'etotaldeb', 'etotal')
        },
        'lines': [{
            key: row.get(key)
            for key in ('bistamp', 'ref', 'design', 'qtt', 'qtt2', 'unidade', 'edebito', 'ettdeb',
                        'iva', 'tabiva', 'ccusto', 'dataobra', 'fechada', 'lordem')
        } for row in lines],
    }
    return hashlib.sha256(json.dumps(content, sort_keys=True, default=str, separators=(',', ':')).encode()).hexdigest()


def _source_and_document(document: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    from services import document_ai_service as svc

    controlled = dict(document or {})
    source = svc._phc_origin_source(dict(controlled.get('customer') or {}))
    if source.get('kind') != 'phc' or not _clean(source.get('phc_db')):
        raise ValueError('A Entidade selecionada não tem uma base PHC configurada.')
    return source, controlled


def _load_current(cursor, origin_stamp: str, *, for_update: bool = False,
                  label: str = 'Nota de Encomenda') -> tuple[dict[str, Any], list[dict[str, Any]]]:
    lock = 'WITH (UPDLOCK,HOLDLOCK)' if for_update else 'WITH (NOLOCK)'
    headers = _rows(cursor, f"""
        SELECT TOP 1 BO.BOSTAMP,BO.NDOS,BO.NMDOS,BO.OBRANO,BO.BOANO,BO.DATAOBRA,
            BO.NO,ISNULL(BO.ESTAB,0) ESTAB,BO.NOME,BO.CCUSTO,BO.MOEDA,
            ISNULL(BO.FECHADA,0) FECHADA,ISNULL(BO.ETOTALDEB,0) ETOTALDEB,
            ISNULL(BO.ETOTAL,0) ETOTAL,ISNULL(BO2.ANULADO,0) ANULADO
        FROM dbo.BO BO {lock}
        LEFT JOIN dbo.BO2 BO2 {lock} ON BO2.BO2STAMP=BO.BOSTAMP
        WHERE BO.BOSTAMP=?
    """, origin_stamp)
    if not headers:
        raise ValueError(f'{label} já não existe no PHC.')
    lines = _rows(cursor, f"""
        SELECT BI.BISTAMP,BI.BOSTAMP,BI.REF,BI.DESIGN,ISNULL(BI.QTT,0) QTT,
            ISNULL(BI.QTT2,0) QTT2,BI.UNIDADE,ISNULL(BI.EDEBITO,0) EDEBITO,
            ISNULL(BI.ETTDEB,0) ETTDEB,ISNULL(BI.IVA,0) IVA,
            ISNULL(BI.TABIVA,0) TABIVA,BI.CCUSTO,BI.DATAOBRA,
            ISNULL(BI.FECHADA,0) FECHADA,ISNULL(BI.LORDEM,0) LORDEM,
            BI.OBISTAMP,BI.OOBISTAMP,BI.OOBOSTAMP
        FROM dbo.BI BI {lock}
        WHERE BI.BOSTAMP=? ORDER BY BI.LORDEM,BI.BISTAMP
    """, origin_stamp)
    return headers[0], lines


def _normalize_plan(cursor, document: dict[str, Any], current_lines: list[dict[str, Any]] | None = None,
                    origin_stamp: str = '', family: str = 'purchase_order') -> dict[str, Any]:
    from services import document_ai_service as svc

    supplier = svc._phc_provisional_supplier(cursor, dict(document.get('supplier') or {}))
    config = _flow_config(family)
    series = _purchase_order_series(cursor, family)
    raw_lines = svc._assert_effective_portal_lines(
        document.get('lines') or [],
        require_origin=bool(origin_stamp),
        require_cost_center=False,
    )

    document_date = _clean(document.get('document_date'))
    try:
        header_date = datetime.fromisoformat(document_date[:10])
    except ValueError as exc:
        raise ValueError(f"Confirma a data do documento antes de criar {config['label']}.") from exc
    currency = _clean(document.get('currency')).upper()
    if currency == 'EUR':
        currency = 'EURO'
    if not currency:
        raise ValueError(f"Confirma a moeda antes de criar {config['label']}.")

    project_default = _clean((document.get('origin_project') or {}).get('ccusto'))
    projects = {_clean(line.get('ccusto') or line.get('project_ccusto') or project_default) for line in raw_lines}
    projects.discard('')
    if len(projects) != 1:
        raise ValueError('Escolhe uma única Obra/Centro de Custo para a Nota de Encomenda.')
    project = next(iter(projects))
    if not cursor.execute("SELECT TOP 1 1 FROM dbo.BO WITH (NOLOCK) WHERE LTRIM(RTRIM(ISNULL(CCUSTO,'')))=?", project).fetchone():
        raise ValueError(f'A Obra/Centro de Custo {project} já não existe no PHC.')

    article_refs = list(dict.fromkeys(_clean(line.get('article_ref') or line.get('article')) for line in raw_lines))
    if any(not ref for ref in article_refs):
        raise ValueError('Associa um artigo PHC a todas as linhas.')
    placeholders = ','.join('?' for _ in article_refs)
    articles = _rows(cursor, f"""
        SELECT REF,DESIGN,UNIDADE,FAMILIA,ISNULL(TABIVA,0) TABIVA
        FROM dbo.ST WITH (NOLOCK)
        WHERE REF IN ({placeholders}) AND ISNULL(INACTIVO,0)=0
    """, *article_refs)
    article_map = {_clean(item.get('ref')).upper(): item for item in articles}
    missing_articles = [ref for ref in article_refs if ref.upper() not in article_map]
    if missing_articles:
        raise ValueError(f'O artigo {missing_articles[0]} não existe ou está inativo no PHC.')

    by_code, by_rate = svc._phc_tax_configuration(cursor)
    current = list(current_lines or [])
    current_by_stamp = {_clean(row.get('bistamp')): row for row in current}
    current_by_ref: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in current:
        current_by_ref[_clean(row.get('ref')).upper()].append(row)
    used_stamps: set[str] = set()
    planned = []
    for index, line in enumerate(raw_lines):
        quantity = _decimal(line.get('quantity') if line.get('quantity') is not None else line.get('qty'), f'Linha {index + 1}: quantidade')
        if quantity <= 0 or quantity != quantity.quantize(Decimal('0.0001')):
            raise ValueError(f'Linha {index + 1}: confirma uma quantidade positiva com até quatro casas decimais.')
        unit = _clean(line.get('unit'))
        if not unit:
            raise ValueError(f'Linha {index + 1}: confirma a unidade.')
        unit_price = _unit_price(line.get('unit_price'), f'Linha {index + 1}: preço unitário')
        line_total = _money(line.get('net_amount'), f'Linha {index + 1}: valor líquido')
        if abs(line_total - _money(quantity * unit_price)) > Decimal('0.02'):
            raise ValueError(f'Linha {index + 1}: quantidade, preço unitário e valor líquido não coincidem.')
        tax_rate = _money(line.get('tax_rate'), f'Linha {index + 1}: taxa de IVA')
        tax_code = svc._phc_tax_code(tax_rate, by_rate)
        if by_code.get(tax_code) != tax_rate:
            raise ValueError(f'Linha {index + 1}: a taxa de IVA mudou no PHC.')
        ref = _clean(line.get('article_ref') or line.get('article'))
        article = article_map[ref.upper()]
        description = _clean(line.get('description'))
        if not description:
            raise ValueError(f'Linha {index + 1}: confirma a designação.')
        line_date_text = _clean(line.get('date') or line.get('data') or document_date)
        try:
            line_date = datetime.fromisoformat(line_date_text[:10])
        except ValueError as exc:
            raise ValueError(f'Linha {index + 1}: confirma a data.') from exc

        mapped_stamp = _clean(line.get('phc_origin_line_stamp'))
        allocations = [part for part in (line.get('bc_allocations') or [])
                       if _clean(part.get('origin_stamp')) == origin_stamp]
        if len(allocations) == 1:
            mapped_stamp = _clean(allocations[0].get('origin_line_stamp'))
        if origin_stamp and not mapped_stamp:
            same_ref = [row for row in current_by_ref.get(ref.upper(), []) if _clean(row.get('bistamp')) not in used_stamps]
            if len(same_ref) == 1:
                mapped_stamp = _clean(same_ref[0].get('bistamp'))
            elif len(current) == len(raw_lines) and index < len(current):
                mapped_stamp = _clean(current[index].get('bistamp'))
        if mapped_stamp and mapped_stamp not in current_by_stamp:
            raise ValueError(f'Linha {index + 1}: a linha PHC associada já não pertence a esta Nota de Encomenda.')
        if mapped_stamp in used_stamps:
            raise ValueError(f'Linha {index + 1}: a mesma linha PHC foi associada mais do que uma vez.')
        if mapped_stamp:
            used_stamps.add(mapped_stamp)
        planned.append({
            'portal_line_index': index,
            'portal_line_id': _clean(line.get('portal_line_id')),
            'bistamp': mapped_stamp,
            'ref': ref,
            'design': description,
            'quantity': quantity,
            'unit': unit,
            'unit_price': unit_price,
            'line_total': line_total,
            'tax_rate': tax_rate,
            'tax_code': tax_code,
            'ccusto': project,
            'date': line_date,
            'article': article,
        })

    net = sum((row['line_total'] for row in planned), Decimal('0'))
    tax = sum((row['line_total'] * row['tax_rate'] / Decimal('100')).quantize(Decimal('0.01')) for row in planned)
    return {
        'series': series,
        'supplier': supplier,
        'currency': currency,
        'project': project,
        'date': header_date,
        'lines': planned,
        'net': net,
        'tax': tax,
        'gross': net + tax,
    }


def _public_line(row: dict[str, Any]) -> dict[str, Any]:
    return {
        'portal_line_index': row.get('portal_line_index'),
        'line_stamp': _clean(row.get('bistamp')),
        'article': _clean(row.get('ref')),
        'description': _clean(row.get('design')),
        'quantity': float(row.get('quantity') if row.get('quantity') is not None else row.get('qtt') or 0),
        'unit': _clean(row.get('unit') or row.get('unidade')),
        'unit_price': float(row.get('unit_price') if row.get('unit_price') is not None else row.get('edebito') or 0),
        'line_total': float(row.get('line_total') if row.get('line_total') is not None else row.get('ettdeb') or 0),
        'tax_rate': float(row.get('tax_rate') if row.get('tax_rate') is not None else row.get('iva') or 0),
        'project': _clean(row.get('ccusto')),
        'date': (row.get('date') or row.get('dataobra')).date().isoformat()
                if isinstance(row.get('date') or row.get('dataobra'), datetime)
                else _clean(row.get('date') or row.get('dataobra'))[:10],
    }


def preview_purchase_order(document: dict[str, Any], origin_stamp: str = '', family: str = 'purchase_order') -> dict[str, Any]:
    import pyodbc
    from services.phc_user_import_service import _phc_conn_str

    source, controlled = _source_and_document(document)
    database = _clean(source.get('phc_db'))
    with pyodbc.connect(_phc_conn_str(database, source.get('phc_server') or ''), timeout=15) as connection:
        cursor = connection.cursor()
        current_header: dict[str, Any] = {}
        current_lines: list[dict[str, Any]] = []
        if origin_stamp:
            current_header, current_lines = _load_current(cursor, origin_stamp, label=_flow_config(family)['label'])
        config = _flow_config(family)
        plan = _normalize_plan(cursor, controlled, current_lines, origin_stamp, family)
        if origin_stamp and int(current_header.get('ndos') or 0) != int(plan['series']['ndos']):
            raise ValueError(f"A origem selecionada não pertence à série de {config['label']} desta Entidade.")
        if origin_stamp and int(current_header.get('no') or 0) != int(plan['supplier']['no']):
            raise ValueError(f"O fornecedor controlado não coincide com {config['label']} selecionado.")
        snapshot = _snapshot(current_header, current_lines) if origin_stamp else ''
        return {
            'ok': True,
            'mode': 'correct' if origin_stamp else 'create',
            'phc_database': database,
            'series': plan['series'],
            'supplier': {'no': int(plan['supplier']['no']), 'estab': int(plan['supplier']['estab']), 'name': plan['supplier']['name']},
            'project': plan['project'],
            'currency': plan['currency'],
            'snapshot': snapshot,
            'current': {
                'origin': {
                    'stamp': _clean(current_header.get('bostamp')),
                    'number': int(current_header.get('obrano') or 0),
                    'year': int(current_header.get('boano') or 0),
                } if current_header else None,
                'lines': [_public_line(row) for row in current_lines],
            },
            'proposal': {
                'date': plan['date'].date().isoformat(),
                'net_total': float(plan['net']),
                'tax_total': float(plan['tax']),
                'gross_total': float(plan['gross']),
                'lines': [_public_line(row) for row in plan['lines']],
            },
        }


def apply_purchase_order(document: dict[str, Any], document_stamp: str, requested_by: str,
                         origin_stamp: str = '', expected_snapshot: str = '',
                         family: str = 'purchase_order') -> dict[str, Any]:
    import pyodbc
    from services import document_ai_service as svc
    from services.phc_user_import_service import _phc_conn_str

    source, controlled = _source_and_document(document)
    config = _flow_config(family)
    database = _clean(source.get('phc_db'))
    mode = 'correct' if origin_stamp else 'create'
    stable_header_stamp = origin_stamp or _stable_stamp(config['stamp'], document_stamp)
    connection = pyodbc.connect(_phc_conn_str(database, source.get('phc_server') or ''), timeout=15, autocommit=False)
    try:
        cursor = connection.cursor()
        cursor.execute('SET TRANSACTION ISOLATION LEVEL SERIALIZABLE')
        lock = cursor.execute("""
            DECLARE @result int;
            EXEC @result=sp_getapplock @Resource=?,@LockMode='Exclusive',
                @LockOwner='Transaction',@LockTimeout=15000;
            SELECT @result;
        """, f"DOC_AI_{config['lock']}_{database}_{stable_header_stamp}").fetchone()
        if not lock or int(lock[0]) < 0:
            raise ValueError(f"Outra operação está a alterar {config['label']}. Tenta novamente.")

        current_header: dict[str, Any] = {}
        current_lines: list[dict[str, Any]] = []
        existing = cursor.execute('SELECT TOP 1 BOSTAMP FROM dbo.BO WITH (UPDLOCK,HOLDLOCK) WHERE BOSTAMP=?', stable_header_stamp).fetchone()
        if existing:
            current_header, current_lines = _load_current(
                cursor, stable_header_stamp, for_update=True, label=config['label']
            )
        if mode == 'correct' and not current_header:
            raise ValueError(f"{config['label']} já não existe no PHC.")
        plan = _normalize_plan(cursor, controlled, current_lines, stable_header_stamp if current_header else '', family)

        if current_header:
            if int(current_header.get('ndos') or 0) != int(plan['series']['ndos']):
                raise ValueError(f"{config['label']} existente pertence a outra série PHC.")
            if int(current_header.get('no') or 0) != int(plan['supplier']['no']):
                raise ValueError(f"O fornecedor de {config['label']} mudou no PHC.")
            actual_snapshot = _snapshot(current_header, current_lines)
            if expected_snapshot and expected_snapshot != actual_snapshot:
                raise ValueError(f"{config['label']} foi alterado por outro utilizador. Reabre a comparação.")
            if bool(current_header.get('fechada')) or bool(current_header.get('anulado')):
                raise ValueError(f"{config['label']} está fechado ou anulado e não pode ser corrigido.")
            stamps = [_clean(row.get('bistamp')) for row in current_lines]
            if any(bool(row.get('fechada')) or abs(_decimal(row.get('qtt2') or 0, 'Quantidade satisfeita')) > Decimal('0.0001') for row in current_lines):
                raise ValueError(f"{config['label']} já tem linhas satisfeitas ou fechadas e não pode ser corrigido.")
            if stamps:
                placeholders = ','.join('?' for _ in stamps)
                reused = cursor.execute(f"""
                    SELECT TOP 1 1 FROM dbo.BI WITH (UPDLOCK,HOLDLOCK)
                    WHERE BOSTAMP<>? AND (OBISTAMP IN ({placeholders}) OR OOBISTAMP IN ({placeholders}))
                """, stable_header_stamp, *stamps, *stamps).fetchone()
                if reused:
                    raise ValueError(f"Uma linha de {config['label']} já foi retomada noutro documento PHC.")

        now = datetime.now()
        user = svc._phc_correspondence_user(cursor, requested_by)
        initials = _clean(user.get('initials') or requested_by or 'DOC')[:3]
        audit = {'usrinis': initials, 'usrdata': now, 'usrhora': now.strftime('%H:%M:%S')}
        create_audit = {'ousrinis': initials, 'ousrdata': now, 'ousrhora': now.strftime('%H:%M:%S')}
        factor = svc._phc_base_currency_per_euro(cursor)
        supplier_currency = _clean(plan['supplier'].get('currency')).upper()
        if supplier_currency == 'EUR':
            supplier_currency = 'EURO'
        if plan['currency'] == 'EURO':
            euro = lambda value: Decimal(value)
            local = lambda value: svc._phc_local_amount(Decimal(value), factor)
        elif supplier_currency and plan['currency'] == supplier_currency:
            local = lambda value: Decimal(value)
            euro = lambda value: (Decimal(value) / factor).quantize(Decimal('0.00001')) if factor else Decimal(value)
        else:
            raise ValueError('A moeda controlada não coincide com a moeda do fornecedor/base PHC.')

        if current_header:
            number = int(current_header['obrano'])
            year = int(current_header['boano'])
        else:
            year = plan['date'].year
            number = int(cursor.execute("""
                SELECT ISNULL(MAX(OBRANO),0)+1 FROM dbo.BO WITH (UPDLOCK,HOLDLOCK)
                WHERE NDOS=? AND BOANO=?
            """, plan['series']['ndos'], year).fetchone()[0])

        header_values = {
            'ndos': plan['series']['ndos'], 'nmdos': plan['series']['name'],
            'obrano': number, 'boano': year, 'dataobra': plan['date'], 'dataopen': plan['date'],
            'no': plan['supplier']['no'], 'estab': plan['supplier']['estab'], 'nome': plan['supplier']['name'],
            'ncont': plan['supplier']['tax_id'], 'morada': plan['supplier']['address'],
            'local': plan['supplier']['city'], 'codpost': plan['supplier']['postal_code'],
            'moeda': plan['currency'], 'ccusto': plan['project'], 'fechada': 0,
            'etotaldeb': euro(plan['net']), 'totaldeb': local(plan['net']),
            'etotal': euro(plan['gross']), 'total': local(plan['gross']), **audit,
        }
        taxes: dict[int, list[Decimal]] = defaultdict(lambda: [Decimal('0'), Decimal('0')])
        for row in plan['lines']:
            taxes[int(row['tax_code'])][0] += row['line_total']
            taxes[int(row['tax_code'])][1] += (row['line_total'] * row['tax_rate'] / Decimal('100')).quantize(Decimal('0.01'))
        for code, (base, tax) in taxes.items():
            for suffix in ('1', '2'):
                header_values.update({
                    f'ebo{code}{suffix}_bins': euro(base), f'bo{code}{suffix}_bins': local(base),
                    f'ebo{code}{suffix}_iva': euro(tax), f'bo{code}{suffix}_iva': local(tax),
                })

        if current_header:
            svc._phc_update_values(cursor, 'BO', header_values, 'BOSTAMP=?', [stable_header_stamp])
            cursor.execute('DELETE FROM dbo.BOT WHERE BOSTAMP=?', stable_header_stamp)
        else:
            svc._phc_insert_values(cursor, 'BO', {'bostamp': stable_header_stamp, **header_values, **create_audit})
            svc._phc_insert_values(cursor, 'BO2', {'bo2stamp': stable_header_stamp, 'anulado': 0, **audit, **create_audit})
            svc._phc_insert_values(cursor, 'BO3', {'bo3stamp': stable_header_stamp, **audit, **create_audit})
        for code, (base, tax) in taxes.items():
            svc._phc_insert_values(cursor, 'BOT', {
                'botstamp': svc._new_stamp(), 'bostamp': stable_header_stamp, 'codigo': code,
                'taxa': next(row['tax_rate'] for row in plan['lines'] if int(row['tax_code']) == code),
                'ebaseinc': euro(base), 'baseinc': local(base), 'evalor': euro(tax), 'valor': local(tax),
                **audit, **create_audit,
            })

        retained: set[str] = set()
        result_lines = []
        for index, row in enumerate(plan['lines'], 1):
            line_stamp = _planned_line_stamp(document_stamp, row, index, f"{config['stamp']}L")
            retained.add(line_stamp)
            article = row['article']
            values = {
                'bostamp': stable_header_stamp, 'ndos': plan['series']['ndos'], 'nmdos': plan['series']['name'],
                'obrano': number, 'boano': year, 'dataobra': row['date'],
                'no': plan['supplier']['no'], 'nome': plan['supplier']['name'],
                'ref': row['ref'], 'design': row['design'], 'unidade': row['unit'],
                'familia': article.get('familia'),
                'qtt': row['quantity'], 'qtt2': 0, 'fechada': 0,
                'edebito': euro(row['unit_price']), 'debito': local(row['unit_price']),
                'ettdeb': euro(row['line_total']), 'ttdeb': local(row['line_total']),
                'iva': row['tax_rate'], 'tabiva': row['tax_code'], 'ivaincl': 0,
                'ccusto': row['ccusto'], 'lordem': index * 1000, **audit,
            }
            if row.get('bistamp'):
                svc._phc_update_values(cursor, 'BI', values, 'BISTAMP=? AND BOSTAMP=?', [line_stamp, stable_header_stamp])
            else:
                svc._phc_insert_values(cursor, 'BI', {'bistamp': line_stamp, **values, **create_audit})
                svc._phc_insert_values(cursor, 'BI2', {'bi2stamp': line_stamp, 'bostamp': stable_header_stamp, **audit, **create_audit})
            result_lines.append({
                'portal_line_index': int(row['portal_line_index']), 'line_stamp': line_stamp,
                'article_ref': row['ref'], 'quantity': float(row['quantity']),
            })
        if current_header:
            removed = [_clean(row.get('bistamp')) for row in current_lines if _clean(row.get('bistamp')) not in retained]
            if removed:
                placeholders = ','.join('?' for _ in removed)
                cursor.execute(f'DELETE FROM dbo.BI2 WHERE BI2STAMP IN ({placeholders})', *removed)
                cursor.execute(f'DELETE FROM dbo.BI WHERE BISTAMP IN ({placeholders}) AND BOSTAMP=?', *removed, stable_header_stamp)

        connection.commit()
        return {
            'ok': True, 'mode': mode, 'duplicate': bool(existing and not origin_stamp),
            'bostamp': stable_header_stamp, 'ndos': int(plan['series']['ndos']),
            'document_name': plan['series']['name'], 'number': number, 'year': year,
            'date': plan['date'].date().isoformat(), 'phc_database': database,
            'supplier_no': int(plan['supplier']['no']), 'supplier_name': plan['supplier']['name'],
            'ccusto': plan['project'], 'currency': plan['currency'], 'line_stamps': result_lines,
            'family': family,
            'message': f"{config['label']} n.º {number} {'corrigido' if mode == 'correct' else 'criado'} no PHC.",
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
