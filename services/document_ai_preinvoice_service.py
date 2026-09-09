"""Management pre-invoices: resolve immediate sources before any PHC write."""

import hashlib
import json
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def _decimal(value):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError('Quantidade ou valor em falta/invalido na Pre-Fatura.') from exc
    if not result.is_finite():
        raise ValueError('Quantidade ou valor invalido na Pre-Fatura.')
    return result


def _money(value):
    return _decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _clean(value):
    return str(value or '').strip()


def payload_fingerprint(document, origins):
    fields = ('document_type', 'document_number', 'document_date', 'currency',
              'customer', 'supplier', 'lines', 'totals', 'taxes', 'origin_project')
    content = {'document': {key: document.get(key) for key in fields}, 'origins': sorted(_clean(o.get('stamp')) for o in origins
                                                     if o.get('document_type') != 'proforma_invoice')}
    return hashlib.sha256(json.dumps(content, sort_keys=True, default=str,
                                    separators=(',', ':')).encode()).hexdigest()


def plan_preinvoice(document, source_lines, headers):
    """Return explicit, quantity-limited BI allocations; never guess an ambiguous source."""
    from services.document_ai_service import _effective_portal_lines

    lines = _effective_portal_lines(document.get('lines') or [])
    if not lines:
        raise ValueError('Confirma as linhas antes de criar a Pre-Fatura.')
    sources = {_clean(row['bistamp']): row for row in source_lines}
    consumed = defaultdict(Decimal)
    planned = []
    for index, line in enumerate(lines, 1):
        quantity = _decimal(line.get('quantity') if line.get('quantity') is not None else line.get('qty'))
        if quantity != quantity.quantize(Decimal('0.0001')):
            raise ValueError(f'Linha {index}: a quantidade excede a precisao PHC de quatro casas decimais.')
        if quantity <= 0:
            raise ValueError(f'Linha {index}: confirma uma quantidade positiva na origem.')
        reference = _clean(line.get('article_ref') or line.get('article'))
        if not reference:
            raise ValueError(f'Linha {index}: associa o artigo PHC.')
        allocations = line.get('bc_allocations') or []
        if not allocations:
            header_stamp = _clean(line.get('phc_origin_stamp'))
            line_stamp = _clean(line.get('phc_origin_line_stamp'))
            candidates = [row for row in source_lines
                          if _clean(row.get('ref')) == reference
                          and (not header_stamp or _clean(row['bostamp']) == header_stamp)
                          and (not line_stamp or _clean(row['bistamp']) == line_stamp)]
            # A selected GdR/STSE supersedes its ancestor for this same source line.
            predecessors = {_clean(row.get('obistamp')) for row in candidates}
            candidates = [row for row in candidates if _clean(row['bistamp']) not in predecessors]
            if len(candidates) != 1:
                raise ValueError(f'Linha {index}: associa a linha de origem imediata e distribui as quantidades.')
            allocations = [{'origin_stamp': candidates[0]['bostamp'],
                            'origin_line_stamp': candidates[0]['bistamp'], 'quantity': quantity}]
        if sum((_decimal(part.get('quantity')) for part in allocations), Decimal(0)) != quantity:
            raise ValueError(f'Linha {index}: a quantidade distribuida nao coincide com a linha.')
        net = _money(line.get('net_amount'))
        allocated_net = Decimal(0)
        for part_index, part in enumerate(allocations):
            stamp = _clean(part.get('origin_line_stamp'))
            source = sources.get(stamp)
            if not source or _clean(source['bostamp']) != _clean(part.get('origin_stamp')):
                raise ValueError(f'Linha {index}: a linha de origem nao pertence aos documentos associados.')
            header = headers[_clean(source['bostamp'])]
            is_order = _clean(header.get('nmdos')).casefold() == 'bon commande fournisseur'
            if not is_order and int(header['ndos']) not in {102, 119, 129, 130}:
                raise ValueError(f'Linha {index}: cria e associa a Situacao de Trabalhos antes da Pre-Fatura.')
            if any(_clean(other.get('obistamp')) == stamp for other in source_lines):
                raise ValueError(f'Linha {index}: seleciona a GdR/Situacao, nao a sua origem anterior.')
            if _clean(source.get('ref')) != reference:
                raise ValueError(f'Linha {index}: o artigo nao coincide com a origem PHC.')
            if bool(source.get('fechada')) or bool(header.get('fechada')) or bool(header.get('anulado')):
                raise ValueError(f'Linha {index}: a origem esta fechada ou anulada; atualiza Origem.')
            if bool(source.get('ivaincl')):
                raise ValueError(f'Linha {index}: origem com IVA incluido requer verificacao PHC antes da criacao.')
            qty = _decimal(part.get('quantity'))
            if qty <= 0 or qty != qty.quantize(Decimal('0.0001')):
                raise ValueError(f'Linha {index}: a distribuicao tem uma quantidade invalida.')
            consumed[stamp] += qty
            already = max(_decimal(source.get('qtt2') or 0), _decimal(source.get('reused_qty') or 0))
            if consumed[stamp] > _decimal(source['qtt']) - already:
                raise ValueError(f'Linha {index}: a quantidade disponivel mudou no PHC; atualiza Origem.')
            ccusto = _clean(line.get('cost_center') or line.get('ccusto') or line.get('project_ccusto')
                            or (document.get('origin_project') or {}).get('ccusto'))
            if not ccusto or ccusto != _clean(source.get('ccusto')):
                raise ValueError(f'Linha {index}: confirma a Obra/Centro de Custo na origem.')
            rate = _decimal(line.get('tax_rate'))
            if rate != _decimal(source.get('iva')):
                raise ValueError(f'Linha {index}: corrige a taxa de IVA na origem antes de validar.')
            part_net = (_money(net * qty / quantity) if part_index < len(allocations) - 1
                        else net - allocated_net)
            allocated_net += part_net
            expected = _decimal(source.get('edebito')) * qty
            for field in ('desconto', 'desc2', 'desc3', 'desc4', 'desc5', 'desc6'):
                expected *= 1 - _decimal(source.get(field) or 0) / 100
            if abs(_money(expected) - part_net) > Decimal('0.02'):
                raise ValueError(f'Linha {index}: corrige o preco/descontos da origem antes de validar.')
            planned.append({'source': source, 'quantity': qty, 'net': part_net,
                            'tax': _money(part_net * rate / 100), 'rate': rate, 'ccusto': ccusto})
    totals = document.get('totals') or {}
    net = sum((p['net'] for p in planned), Decimal(0))
    tax = sum((p['tax'] for p in planned), Decimal(0))
    for value, key in ((net, 'net_total'), (tax, 'tax_total'), (net + tax, 'gross_total')):
        if abs(value - _money(totals.get(key))) > Decimal('0.02'):
            raise ValueError('Os totais da Pre-Fatura nao coincidem com o documento. Confirma linhas e IVA.')
    return planned


def _rows(cursor, sql, *params):
    cursor.execute(sql, *params)
    keys = [column[0].lower() for column in cursor.description]
    return [dict(zip(keys, row)) for row in cursor.fetchall()]


def create_preinvoice(document, origins, reception, document_stamp, file_bytes, requested_by):
    import pyodbc
    from services import document_ai_service as svc
    from services.phc_user_import_service import _phc_conn_str

    source = svc._phc_origin_source(document.get('customer') or {})
    database = _clean(source.get('phc_db'))
    if source.get('kind') != 'phc' or not database or database.upper() != _clean(reception.get('phc_database')).upper():
        raise ValueError('A Entidade nao coincide com a Compra criada na Rececao.')
    if not file_bytes or not _clean(reception.get('fostamp')):
        raise ValueError('Falta confirmar a Compra e o PDF original da Rececao.')
    currency = _clean(document.get('currency')).upper()
    if currency not in {'EUR', 'EURO'}:
        raise ValueError('A criacao de Pre-Fatura nesta moeda requer validacao do cambio PHC.')
    selected = [o for o in origins if o.get('document_type') != 'proforma_invoice']
    stamps = sorted({_clean(o.get('stamp')) for o in selected if _clean(o.get('stamp'))})
    if not stamps:
        raise ValueError('Associa as origens antes de validar no Controlo de Gestao.')
    if any(_clean(o.get('phc_database')).upper() != database.upper() for o in selected):
        raise ValueError('As origens devem pertencer a mesma base PHC da Entidade.')
    fingerprint = payload_fingerprint(document, selected)
    # Two Portal imports linked to the same Reception FO must not create two BOs.
    marker = f'DOC_AI_PF:{_clean(reception["fostamp"])}'
    connection = pyodbc.connect(_phc_conn_str(database, source.get('phc_server') or ''),
                                timeout=15, autocommit=False)
    try:
        cursor = connection.cursor()
        cursor.execute('SET TRANSACTION ISOLATION LEVEL SERIALIZABLE')
        lock = cursor.execute("""
            DECLARE @r int;
            EXEC @r=sp_getapplock @Resource=?, @LockMode='Exclusive',
                @LockOwner='Transaction', @LockTimeout=15000;
            SELECT @r;
        """, marker).fetchone()
        if not lock or lock[0] < 0:
            raise ValueError('Outra validacao esta em curso. Tenta novamente.')
        existing = _rows(cursor, """
            SELECT B.BOSTAMP,B.NDOS,B.NMDOS,B.OBRANO,B.BOANO,A.ANEXOSSTAMP,A.FULLNAME,A.DESCRICAO
            FROM ANEXOS A WITH (UPDLOCK,HOLDLOCK) JOIN BO B ON B.BOSTAMP=A.RECSTAMP
            WHERE A.ORITABLE='BO' AND A.UNIQUEID=?
        """, marker)
        if existing:
            if len(existing) != 1 or _clean(existing[0]['descricao']) != fingerprint:
                raise ValueError('Ja existe uma Pre-Fatura para este documento com dados diferentes. Verifica no PHC.')
            header = existing[0]
            if not svc._document_ai_pdf_is_confirmed({'unc_path': header['fullname'],
                    'write_path': header['fullname'], 'storage': 'local' if svc.os.name == 'nt' else 'smb'}, file_bytes):
                raise ValueError('O PDF da Pre-Fatura existente nao pode ser confirmado no GED.')
            connection.rollback()
            return _result(header, database, fingerprint, True)

        if any(o.get('document_type') == 'proforma_invoice' for o in origins):
            raise ValueError('Ja existe uma Pre-Fatura associada. Reconcilia-a antes de criar outro documento.')

        series = _rows(cursor, 'SELECT NDOS,NMDOS FROM TS')
        series = [row for row in series if svc._normalize_text(row['nmdos']).replace('-', '').replace(' ', '')
                  in {'prefacture', 'prefatura', 'prefactura'}]
        if len(series) != 1:
            raise ValueError('Nao foi possivel identificar uma unica serie Pre-Fatura em TS.NMDOS.')
        ndos, name = int(series[0]['ndos']), _clean(series[0]['nmdos'])
        purchase_config = svc._phc_provisional_purchase_doc_config(cursor, database, 'invoice')
        supplier = svc._phc_provisional_supplier(cursor, document.get('supplier') or {})
        purchase = _rows(cursor, 'SELECT NO,ESTAB,MOEDA,ADOC,DOCCODE FROM FO WITH (UPDLOCK,HOLDLOCK) WHERE FOSTAMP=?', reception['fostamp'])
        if not purchase or int(purchase[0]['no']) != supplier['no'] or int(purchase[0]['estab']) != supplier['estab']:
            raise ValueError('O fornecedor nao coincide com a Compra da Rececao.')
        if int(purchase[0]['doccode']) != purchase_config['doccode']:
            raise ValueError('O tipo de Compra da Rececao nao corresponde a uma fatura.')
        if _clean(purchase[0]['adoc']) != _clean(document.get('document_number')):
            raise ValueError('O numero da fatura mudou desde a Rececao. Corrige a Compra antes de validar.')
        pdf = _rows(cursor, "SELECT TOP 1 FULLNAME FROM ANEXOS WHERE ORITABLE='FO' AND RECSTAMP=? AND FEXT='pdf' ORDER BY USRDATA DESC", reception['fostamp'])
        if not pdf or not svc._document_ai_pdf_is_confirmed({'unc_path': pdf[0]['fullname'],
                'write_path': pdf[0]['fullname'], 'storage': 'local' if svc.os.name == 'nt' else 'smb'}, file_bytes):
            raise ValueError('O PDF original nao esta confirmado no GED da Rececao.')
        placeholders = ','.join('?' for _ in stamps)
        rows = _rows(cursor, f"SELECT B.*,B2.ANULADO FROM BO B WITH (UPDLOCK,HOLDLOCK) LEFT JOIN BO2 B2 ON B2.BO2STAMP=B.BOSTAMP WHERE B.BOSTAMP IN ({placeholders})", *stamps)
        headers = {_clean(row['bostamp']): row for row in rows}
        if len(headers) != len(stamps):
            raise ValueError('Uma origem ja nao existe. Atualiza Origem.')
        if any(int(h['no']) != supplier['no'] or int(h.get('estab') or 0) != supplier['estab']
               or _clean(h.get('moeda')).upper() not in {'EUR', 'EURO'} for h in rows):
            raise ValueError('Fornecedor, estabelecimento ou moeda das origens nao coincidem com a fatura.')
        source_lines = _rows(cursor, f'SELECT * FROM BI WITH (UPDLOCK,HOLDLOCK) WHERE BOSTAMP IN ({placeholders}) ORDER BY BISTAMP', *stamps)
        for row in source_lines:
            row['reused_qty'] = cursor.execute("""
                SELECT ISNULL(SUM(I.QTT),0) FROM BI I WITH (UPDLOCK,HOLDLOCK)
                LEFT JOIN BO2 B2 ON B2.BO2STAMP=I.BOSTAMP
                WHERE I.OBISTAMP=? AND I.NDOS=? AND ISNULL(B2.ANULADO,0)=0
            """, row['bistamp'], ndos).fetchone()[0]
        planned = plan_preinvoice(document, source_lines, headers)
        for source_line in {part['source']['bistamp']: part['source'] for part in planned}.values():
            if int(headers[_clean(source_line['bostamp'])]['ndos']) == 129:
                contract = cursor.execute('SELECT B.BOSTAMP FROM BI I JOIN BO B ON B.BOSTAMP=I.BOSTAMP WHERE I.BISTAMP=? AND B.NDOS=128 AND B.BOSTAMP=?',
                                          source_line.get('obistamp'), source_line.get('oobostamp')).fetchone()
                if not contract:
                    raise ValueError('A Situacao de Trabalhos nao conserva a ligacao ao Contrato Sub.Emp. Corrige a origem no PHC.')
        source_attachments = _rows(cursor, f"SELECT RECSTAMP,FULLNAME,FNAME,FEXT,FLEN FROM ANEXOS WHERE ORITABLE='BO' AND RECSTAMP IN ({placeholders}) AND FEXT='pdf'", *stamps)
        required_pdf = {part['source']['bostamp'] for part in planned
                        if int(headers[_clean(part['source']['bostamp'])]['ndos']) == 130}
        if required_pdf - {row['recstamp'] for row in source_attachments if _clean(row['fullname'])}:
            raise ValueError('Falta o PDF de uma GdR na origem PHC. Anexa-o antes de validar.')
        for attachment in source_attachments:
            if not svc._document_ai_pdf_is_confirmed({'unc_path': attachment['fullname'],
                    'write_path': attachment['fullname'], 'storage': 'local' if svc.os.name == 'nt' else 'smb'}):
                raise ValueError('Um PDF de origem nao esta acessivel no GED. Confirma o anexo antes de validar.')
        # Validate all fields needed for identity/lineage instead of silently dropping them.
        for table, required in {'BO': {'bostamp','ndos','obrano'},
                                'BI': {'bistamp','bostamp','obistamp','oobistamp','oobostamp','qtt','qtt2'},
                                'ANEXOS': {'uniqueid','recstamp','fullname','descricao'}}.items():
            if not required.issubset(svc._phc_table_columns(cursor, table)):
                raise ValueError(f'A estrutura PHC de {table} nao suporta a integracao requerida.')
        by_code, _ = svc._phc_tax_configuration(cursor)
        for part in planned:
            if by_code.get(int(part['source']['tabiva'])) != part['rate']:
                raise ValueError('A tabela de IVA da origem mudou; confirma o IVA no PHC.')
        now = datetime.now()
        if not document.get('document_date'):
            raise ValueError('Confirma a data da fatura.')
        try:
            doc_date = datetime.fromisoformat(str(document['document_date'])[:10])
        except ValueError as exc:
            raise ValueError('A data da fatura nao e valida.') from exc
        doc_date = svc._phc_provisional_effective_datetime(cursor, database, doc_date, now)
        number = int(cursor.execute('SELECT ISNULL(MAX(OBRANO),0)+1 FROM BO WITH (UPDLOCK,HOLDLOCK) WHERE NDOS=? AND BOANO=?', ndos, doc_date.year).fetchone()[0])
        factor = svc._phc_base_currency_per_euro(cursor)
        def local(value):
            return svc._phc_local_amount(value, factor)
        stamp = svc._new_stamp()
        user = svc._phc_correspondence_user(cursor, requested_by)
        initials = _clean(user.get('initials') or requested_by)[:3]
        audit = {'ousrinis': initials, 'ousrdata': now, 'ousrhora': now.strftime('%H:%M:%S'),
                 'usrinis': initials, 'usrdata': now, 'usrhora': now.strftime('%H:%M:%S')}
        net = sum((p['net'] for p in planned), Decimal(0))
        tax = sum((p['tax'] for p in planned), Decimal(0))
        taxes = defaultdict(lambda: [Decimal(0), Decimal(0)])
        for part in planned:
            values = taxes[int(part['source']['tabiva'])]
            values[0] += part['net']; values[1] += part['tax']
        header = {'bostamp': stamp, 'ndos': ndos, 'nmdos': name, 'obrano': number, 'boano': doc_date.year,
                  'dataobra': doc_date, 'dataopen': doc_date, 'datafecho': datetime(1900,1,1),
                  'no': supplier['no'], 'estab': supplier['estab'], 'nome': supplier['name'],
                  'ncont': supplier['tax_id'], 'morada': supplier['address'], 'local': supplier['city'],
                  'codpost': supplier['postal_code'], 'moeda': purchase[0]['moeda'],
                  'ccusto': planned[0]['ccusto'] if len({p['ccusto'] for p in planned}) == 1 else '',
                  'fref': _clean(document.get('document_number'))[:20], 'fechada': 0,
                  'etotaldeb': net, 'totaldeb': local(net), 'etotal': net+tax, 'total': local(net+tax), **audit}
        for code, (base, vat) in taxes.items():
            for suffix in ('1', '2'):
                header.update({f'ebo{code}{suffix}_bins': base, f'bo{code}{suffix}_bins': local(base),
                               f'ebo{code}{suffix}_iva': vat, f'bo{code}{suffix}_iva': local(vat)})
        svc._phc_insert_values(cursor, 'BO', header)
        svc._phc_insert_values(cursor, 'BO2', {'bo2stamp': stamp, 'anulado': 0, **audit})
        svc._phc_insert_values(cursor, 'BO3', {'bo3stamp': stamp, **audit})
        for code, (base, vat) in taxes.items():
            svc._phc_insert_values(cursor, 'BOT', {'botstamp': svc._new_stamp(), 'bostamp': stamp,
                'codigo': code, 'taxa': by_code[code], 'ebaseinc': base, 'baseinc': local(base),
                'evalor': vat, 'valor': local(vat), **audit})
        quantities = defaultdict(Decimal)
        for index, part in enumerate(planned, 1):
            origin = part['source']
            bi_stamp = svc._new_stamp()
            values = {key: origin.get(key) for key in ('ref','design','unidade','edebito','debito','pu',
                'iva','tabiva','ivaincl','armazem','stipo','familia','pcusto','epcusto','prorc',
                'desconto','desc2','desc3','desc4','desc5','desc6','lobs','lobs2') if origin.get(key) is not None}
            values.update({'bistamp': bi_stamp, 'bostamp': stamp, 'ndos': ndos, 'nmdos': name,
                'obrano': number, 'boano': doc_date.year, 'dataobra': doc_date, 'no': supplier['no'],
                'nome': supplier['name'], 'qtt': part['quantity'], 'qtt2': 0, 'fechada': 0,
                'ettdeb': part['net'], 'ttdeb': local(part['net']), 'ccusto': part['ccusto'],
                'lordem': index*1000, 'obistamp': origin['bistamp'], 'oobistamp': origin['bistamp'],
                'ndoc': purchase_config['doccode'], 'nmdoc': purchase_config['docname'], 'fno': 0,
                # Native PHC preserves the inherited contract/order header here.
                'oobostamp': _clean(origin.get('oobostamp')), **audit})
            svc._phc_insert_values(cursor, 'BI', values)
            svc._phc_insert_values(cursor, 'BI2', {'bi2stamp': bi_stamp, 'bostamp': stamp, **audit})
            quantities[_clean(origin['bistamp'])] += part['quantity']
        for source_stamp, qty in quantities.items():
            original = next(row for row in source_lines if _clean(row['bistamp']) == source_stamp)
            satisfied = max(_decimal(original.get('qtt2') or 0), _decimal(original.get('reused_qty') or 0)) + qty
            cursor.execute('UPDATE BI SET QTT2=?, FECHADA=CASE WHEN ?>=QTT THEN 1 ELSE 0 END,NDOC=?,NMDOC=?,FNO=?,USRINIS=?,USRDATA=?,USRHORA=? WHERE BISTAMP=?',
                           satisfied, satisfied, ndos, name, number, initials, now, audit['usrhora'], source_stamp)
        for source_stamp in sorted({_clean(part['source']['bostamp']) for part in planned}):
            cursor.execute('UPDATE BO SET FECHADA=1,DATAFECHO=?,USRINIS=?,USRDATA=?,USRHORA=? WHERE BOSTAMP=? AND NOT EXISTS (SELECT 1 FROM BI WHERE BOSTAMP=? AND QTT>ISNULL(QTT2,0))',
                           now, initials, now, audit['usrhora'], source_stamp, source_stamp)
        attachment = svc._new_stamp()
        svc._phc_insert_values(cursor, 'ANEXOS', {'anexosstamp': attachment, 'oritable': 'BO',
            'tabnm': 'Dossiers Internos', 'recstamp': stamp, 'uniqueid': marker, 'descricao': fingerprint,
            'resumo': name, 'fullname': pdf[0]['fullname'], 'fext': 'pdf', 'flen': len(file_bytes),
            'tipo': 2, 'tpdoc': ndos, 'bdados': pyodbc.Binary(b''), **audit})
        for index, source_attachment in enumerate(source_attachments):
            svc._phc_insert_values(cursor, 'ANEXOS', {
                **{key: source_attachment[key] for key in ('fullname', 'fname', 'fext', 'flen')},
                'anexosstamp': svc._new_stamp(), 'oritable': 'BO', 'tabnm': 'Dossiers Internos',
                'recstamp': stamp, 'uniqueid': f'{marker}:SOURCE:{index}',
                'resumo': 'Origem', 'descricao': _clean(source_attachment['recstamp']),
                'tipo': 2, 'tpdoc': ndos, 'bdados': pyodbc.Binary(b''), **audit})
        connection.commit()
        return _result({**header, 'anexosstamp': attachment, 'fullname': pdf[0]['fullname']}, database, fingerprint, False)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _result(header, database, fingerprint, duplicate):
    return {'bostamp': _clean(header['bostamp']), 'ndos': int(header['ndos']),
            'document_type': 'proforma_invoice', 'document_name': _clean(header['nmdos']),
            'number': int(header['obrano']), 'year': int(header['boano']), 'phc_database': database,
            'anexosstamp': _clean(header['anexosstamp']), 'ged_path': _clean(header['fullname']),
            'ged_confirmed': True, 'payload_fingerprint': fingerprint, 'duplicate': duplicate}
