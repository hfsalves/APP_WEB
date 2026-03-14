import csv
import io
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.parse import unquote

from sqlalchemy import text, bindparam


SUPPLIER_NO = 15
ARTICLE_REF = 'TX.SERVICO'
FO_DOCCODE = 104
FO_DOCNOME = 'V/Fatura Comissões'
DEFAULT_CCUSTO = 'SEDE'
UNIT_DEFAULT = 'UN'
MONEY_QUANT = Decimal('0.01')
IMPORT_TAX_RATE = Decimal('23.00')
IMPORT_TABIVA = 2
INVOICE_PATTERN = re.compile(r'(AIUC-\d{3,}-[A-Z]{2}-\d{2,})', re.IGNORECASE)


HEADER_ALIASES = {
    'document': [
        'documento', 'numero documento', 'número documento', 'invoice', 'invoice number',
        'invoice no', 'invoice id', 'document', 'document number', 'tax invoice',
        'numero fatura', 'número fatura', 'fatura', 'invoice or receipt',
    ],
    'confirmation_code': [
        'confirmation code', 'reservation code', 'codigo confirmacao', 'código confirmação',
        'codigo de confirmacao', 'código de confirmação', 'reservation confirmation code',
        'confirmation number', 'reservation number', 'codigo reserva', 'código reserva',
    ],
    'service_date': [
        'service date', 'data servico', 'data serviço', 'data do servico', 'data do serviço', 'date', 'issue date',
        'transaction date', 'service start date', 'service end date',
    ],
    'listing': [
        'listing', 'anuncio', 'anúncio', 'nome do anuncio', 'nome do anúncio', 'listing name', 'property', 'accommodation',
    ],
    'listing_id': [
        'listing id', 'id anuncio', 'id anúncio', 'id do anuncio', 'id do anúncio', 'property id', 'anuncio id',
    ],
    'address': [
        'address', 'morada', 'listing address', 'property address',
    ],
    'issuer': [
        'issuer', 'supplier', 'vendor', 'entidade emissora', 'emitente',
    ],
    'vat_number': [
        'vat', 'vat number', 'tax id', 'tax number', 'nif', 'nif/vat', 'vat id',
    ],
    'net_amount': [
        'net', 'net amount', 'subtotal', 'valor liquido', 'valor líquido',
        'amount excl vat', 'amount excl. vat', 'tax exclusive amount',
    ],
    'vat_amount': [
        'vat amount', 'valor do iva', 'valor iva', 'tax amount', 'valor imposto',
    ],
    'total_amount': [
        'total', 'gross', 'gross amount', 'valor total', 'valor bruto', 'total amount',
        'amount incl vat', 'amount incl. vat', 'tax inclusive amount',
    ],
    'currency': [
        'currency', 'moeda', 'curr', 'currency code',
    ],
    'pdf_url': [
        'pdf', 'pdf url', 'invoice pdf', 'download pdf', 'link pdf',
    ],
}


def _normalize_token(value):
    text_value = str(value or '').strip().lower()
    if not text_value:
        return ''
    normalized = unicodedata.normalize('NFKD', text_value)
    normalized = ''.join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = re.sub(r'[\r\n\t]+', ' ', normalized)
    normalized = re.sub(r'[^a-z0-9]+', ' ', normalized)
    return re.sub(r'\s+', ' ', normalized).strip()


def _truncate(value, limit):
    return str(value or '').strip()[:limit]


def _format_date_iso(value):
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return ''


def _decimal_to_float(value):
    if value is None:
        return None
    return float(value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP))


def decode_csv_bytes(file_bytes):
    for encoding in ('utf-8-sig', 'utf-8', 'cp1252', 'latin-1'):
        try:
            return file_bytes.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return file_bytes.decode('utf-8', errors='replace'), 'utf-8-replace'


def detect_csv_delimiter(sample_text):
    try:
        dialect = csv.Sniffer().sniff(sample_text[:4096], delimiters=';,|\t')
        return dialect.delimiter
    except Exception:
        counts = {delim: sample_text.count(delim) for delim in (';', ',', '\t', '|')}
        return max(counts, key=counts.get) if any(counts.values()) else ';'


def parse_decimal(raw_value):
    if raw_value is None:
        return None
    if isinstance(raw_value, Decimal):
        return raw_value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    text_value = str(raw_value).strip()
    if not text_value:
        return None
    text_value = text_value.replace('\u00a0', '').replace('€', '').replace('EUR', '').replace('eur', '')
    text_value = text_value.replace(' ', '')
    negative = False
    if text_value.startswith('(') and text_value.endswith(')'):
        negative = True
        text_value = text_value[1:-1]
    if ',' in text_value and '.' in text_value:
        if text_value.rfind(',') > text_value.rfind('.'):
            text_value = text_value.replace('.', '').replace(',', '.')
        else:
            text_value = text_value.replace(',', '')
    elif ',' in text_value:
        text_value = text_value.replace('.', '').replace(',', '.')
    else:
        text_value = text_value.replace(',', '')
    text_value = re.sub(r'[^0-9.\-]', '', text_value)
    if negative and not text_value.startswith('-'):
        text_value = f'-{text_value}'
    if not text_value or text_value in {'-', '.', '-.'}:
        return None
    try:
        return Decimal(text_value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return None


def parse_date(raw_value):
    if isinstance(raw_value, datetime):
        return raw_value.date()
    if isinstance(raw_value, date):
        return raw_value
    text_value = str(raw_value or '').strip()
    if not text_value:
        return None
    for fmt in (
        '%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d',
        '%d.%m.%Y', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S',
        '%d/%m/%Y %H:%M', '%Y-%m-%dT%H:%M:%S',
    ):
        try:
            return datetime.strptime(text_value, fmt).date()
        except Exception:
            continue
    try:
        return datetime.fromisoformat(text_value.replace('Z', '+00:00')).date()
    except Exception:
        return None


def extract_airbnb_invoice_number(raw_value):
    raw_text = str(raw_value or '').strip()
    if not raw_text:
        return {
            'value': '',
            'source': 'empty',
            'message': 'Primeira coluna vazia.',
        }

    direct_match = INVOICE_PATTERN.search(raw_text)
    if direct_match:
        return {
            'value': direct_match.group(1).upper(),
            'source': 'direct' if '://' not in raw_text else 'url-regex',
            'message': 'Documento identificado por padrão AIUC.',
        }

    if '://' in raw_text or raw_text.startswith('www.'):
        decoded = unquote(raw_text)
        url_match = INVOICE_PATTERN.search(decoded)
        if url_match:
            return {
                'value': url_match.group(1).upper(),
                'source': 'url',
                'message': 'Documento extraído de URL.',
            }
        parts = [p for p in re.split(r'[/?&#=]+', decoded) if p]
        for part in parts:
            cleaned = re.sub(r'[^A-Za-z0-9\-]', '', part or '').upper()
            if re.fullmatch(r'[A-Z0-9][A-Z0-9\-]{7,80}', cleaned):
                return {
                    'value': cleaned,
                    'source': 'url-segment',
                    'message': 'Documento inferido de segmento do link.',
                }
        return {
            'value': '',
            'source': 'url',
            'message': 'Não foi possível extrair o documento do link.',
        }

    cleaned = re.sub(r'\s+', '', raw_text).upper()
    cleaned = re.sub(r'[^A-Z0-9\-]', '', cleaned)
    if re.fullmatch(r'[A-Z0-9][A-Z0-9\-]{7,80}', cleaned):
        return {
            'value': cleaned,
            'source': 'fallback',
            'message': 'Documento usado diretamente após limpeza.',
        }

    return {
        'value': '',
        'source': 'invalid',
        'message': 'Formato de documento inválido.',
    }


def build_airbnb_column_map(headers):
    normalized_headers = [_normalize_token(h) for h in headers]
    mapping = {}
    for key, aliases in HEADER_ALIASES.items():
        for idx, normalized in enumerate(normalized_headers):
            if not normalized:
                continue
            normalized_compact = normalized.replace(' ', '')
            if normalized == _normalize_token(key) or normalized_compact == _normalize_token(key).replace(' ', ''):
                mapping[key] = idx
                break
            for alias in aliases:
                alias_norm = _normalize_token(alias)
                alias_compact = alias_norm.replace(' ', '')
                if (
                    normalized == alias_norm or
                    normalized_compact == alias_compact or
                    (' ' in alias_norm and alias_norm in normalized)
                ):
                    mapping[key] = idx
                    break
            if key in mapping:
                break
    if headers and 'document' not in mapping:
        mapping['document'] = 0
    return mapping


def _load_supplier_and_article(session):
    supplier = session.execute(text("""
        SELECT TOP 1
            NO,
            ISNULL(NOME,'') AS NOME,
            ISNULL(NCONT,'') AS NCONT,
            ISNULL(MORADA,'') AS MORADA,
            ISNULL(LOCAL,'') AS LOCAL,
            ISNULL(CODPOST,'') AS CODPOST
        FROM dbo.V_FL
        WHERE NO = :no
    """), {'no': SUPPLIER_NO}).mappings().first()

    article = session.execute(text("""
        SELECT TOP 1
            ISNULL(REF,'') AS REF,
            ISNULL(DESIGN,'') AS DESIGN,
            ISNULL(TABIVA, 0) AS TABIVA,
            ISNULL(FAMILIA,'') AS FAMILIA
        FROM dbo.V_ST
        WHERE LTRIM(RTRIM(ISNULL(REF,''))) = :ref
    """), {'ref': ARTICLE_REF}).mappings().first()

    return (
        dict(supplier) if supplier else None,
        dict(article) if article else None,
    )


def _document_exists(session, document_number):
    if not document_number:
        return False
    row = session.execute(text("""
        SELECT TOP 1 FOSTAMP
        FROM dbo.FO
        WHERE ISNULL(DOCCODE, 0) = :doccode
          AND LTRIM(RTRIM(ISNULL(ADOC,''))) = :adoc
    """), {'doccode': FO_DOCCODE, 'adoc': document_number}).mappings().first()
    return bool(row)


def _guess_pdf_url(raw_row, mapping):
    for key in ('pdf_url', 'document'):
        idx = mapping.get(key)
        if idx is None:
            continue
        value = raw_row[idx] if idx < len(raw_row) else ''
        if '://' in str(value or ''):
            return str(value or '').strip()
    return ''


def _compute_tax_rate(net_amount, vat_amount):
    if not net_amount or net_amount == 0 or not vat_amount:
        return Decimal('0.00')
    try:
        return ((vat_amount / net_amount) * Decimal('100')).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal('0.00')


def _compute_import_vat(net_amount):
    amount = parse_decimal(net_amount) or Decimal('0.00')
    vat_amount = (amount * IMPORT_TAX_RATE / Decimal('100')).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    total_amount = (amount + vat_amount).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    return amount, vat_amount, total_amount


def _build_observations(preview_row):
    return 'OK - Tudo validado'


def _build_line_design(article_design, preview_row):
    confirmation_code = _truncate(preview_row.get('confirmation_code'), 30)
    text_value = f'TAXA SERVIÇO - Reserva {confirmation_code}'.strip()
    return _truncate(text_value, 60) or _truncate(article_design, 60) or 'TAXA SERVIÇO'


def preview_airbnb_commissions_csv(session, file_storage):
    if not file_storage:
        raise ValueError('Ficheiro CSV em falta.')

    file_bytes = file_storage.read()
    if not file_bytes:
        raise ValueError('O ficheiro está vazio.')

    decoded_text, encoding_used = decode_csv_bytes(file_bytes)
    delimiter = detect_csv_delimiter(decoded_text)
    stream = io.StringIO(decoded_text)
    reader = csv.reader(stream, delimiter=delimiter)
    rows = list(reader)
    if not rows:
        raise ValueError('O ficheiro não contém linhas.')

    headers = [str(value or '').strip() for value in rows[0]]
    if not any(headers):
        raise ValueError('Cabeçalho CSV inválido.')

    mapping = build_airbnb_column_map(headers)
    supplier, article = _load_supplier_and_article(session)
    logs = [
        f'encoding={encoding_used}',
        f'delimiter={repr(delimiter)}',
        f'headers={headers}',
        f'supplier_found={bool(supplier)}',
        f'article_found={bool(article)}',
    ]

    data_rows = [row for row in rows[1:] if any(str(cell or '').strip() for cell in row)]
    confirmation_codes = []
    confirmation_idx = mapping.get('confirmation_code')
    if confirmation_idx is not None:
        for raw_row in data_rows:
            if confirmation_idx < len(raw_row):
                code = str(raw_row[confirmation_idx] or '').strip()
                if code:
                    confirmation_codes.append(code)

    reservation_dates = {}
    if confirmation_codes:
        try:
            rs_rows = session.execute(
                text("""
                    SELECT
                        LTRIM(RTRIM(ISNULL(RESERVA,''))) AS RESERVA,
                        CAST(DATAIN AS date) AS DATAIN
                    FROM dbo.RS
                    WHERE LTRIM(RTRIM(ISNULL(RESERVA,''))) IN :codes
                """).bindparams(bindparam('codes', expanding=True)),
                {'codes': sorted(set(confirmation_codes))}
            ).mappings().all()
            reservation_dates = {
                str(row.get('RESERVA') or '').strip(): _format_date_iso(row.get('DATAIN'))
                for row in rs_rows
                if str(row.get('RESERVA') or '').strip()
            }
        except Exception:
            reservation_dates = {}
            logs.append('reservation_lookup_failed=True')

    preview_rows = []
    total = 0
    valid = 0
    duplicates = 0
    errors = 0

    for row_index, raw_row in enumerate(rows[1:], start=2):
        if not any(str(cell or '').strip() for cell in raw_row):
            continue
        total += 1
        get_value = lambda key: str(raw_row[mapping[key]]).strip() if mapping.get(key) is not None and mapping[key] < len(raw_row) else ''

        raw_document = get_value('document')
        document_info = extract_airbnb_invoice_number(raw_document)
        service_date = parse_date(get_value('service_date'))
        net_amount = parse_decimal(get_value('net_amount'))
        csv_vat_amount = parse_decimal(get_value('vat_amount'))
        csv_total_amount = parse_decimal(get_value('total_amount'))
        confirmation_code = get_value('confirmation_code')
        reservation_checkin = reservation_dates.get(confirmation_code, '')
        listing = get_value('listing')
        listing_id = get_value('listing_id')
        address = get_value('address')
        issuer = get_value('issuer')
        vat_number = get_value('vat_number')
        currency = (get_value('currency') or 'EUR').upper()[:11]
        pdf_url = _guess_pdf_url(raw_row, mapping)

        issues = []
        if not supplier:
            issues.append('Fornecedor v_fl no=15 não encontrado.')
        if not article:
            issues.append("Artigo v_st ref='TX.SERVICO' não encontrado.")
        if not document_info['value']:
            issues.append(document_info['message'])
        if not service_date:
            issues.append('Data do serviço inválida.')
        if net_amount is None:
            issues.append('Valor líquido inválido.')
        vat_amount = Decimal('0.00')
        total_amount = Decimal('0.00')
        if net_amount is not None:
            _, vat_amount, total_amount = _compute_import_vat(net_amount)

        duplicate = False
        if document_info['value']:
            duplicate = _document_exists(session, document_info['value'])
            if duplicate:
                issues.append('Documento já existe.')

        status = 'ok'
        can_import = True
        message = 'Pronto a importar.'
        if duplicate:
            status = 'duplicate'
            can_import = False
            duplicates += 1
            message = 'Documento já existente.'
        if issues and not duplicate:
            status = 'error'
            can_import = False
            errors += 1
            message = ' | '.join(issues)
        if status == 'ok':
            valid += 1

        tax_rate = IMPORT_TAX_RATE
        preview_row = {
            'row_no': row_index,
            'document_raw': raw_document,
            'document': document_info['value'],
            'document_source': document_info['source'],
            'service_date': _format_date_iso(service_date),
            'confirmation_code': confirmation_code,
            'reservation_checkin': reservation_checkin,
            'listing': listing,
            'listing_id': listing_id,
            'address': address,
            'issuer': issuer,
            'vat_number': vat_number,
            'net_amount': _decimal_to_float(net_amount) or 0.0,
            'vat_amount': _decimal_to_float(vat_amount) or 0.0,
            'total_amount': _decimal_to_float(total_amount) or 0.0,
            'csv_vat_amount': _decimal_to_float(csv_vat_amount) or 0.0,
            'csv_total_amount': _decimal_to_float(csv_total_amount) or 0.0,
            'currency': currency or 'EUR',
            'pdf_url': pdf_url,
            'status': status,
            'message': message,
            'can_import': can_import,
            'tax_rate': _decimal_to_float(tax_rate) or 0.0,
        }
        preview_rows.append(preview_row)
        logs.append(f"row={row_index} doc={preview_row['document'] or '<empty>'} status={status} source={document_info['source']}")

    return {
        'ok': True,
        'headers': headers,
        'mapping': mapping,
        'rows': preview_rows,
        'stats': {
            'total_rows': total,
            'valid_rows': valid,
            'error_rows': errors,
            'duplicate_rows': duplicates,
            'ready_rows': valid,
        },
        'dependencies': {
            'supplier_found': bool(supplier),
            'supplier_name': (supplier or {}).get('NOME', ''),
            'article_found': bool(article),
            'article_ref': (article or {}).get('REF', ''),
        },
        'logs': logs,
    }


def _build_fo_payload(stamp_factory, supplier, preview_row, user_login):
    service_date = parse_date(preview_row.get('service_date')) or date.today()
    reservation_checkin = parse_date(preview_row.get('reservation_checkin')) or service_date
    net_amount, vat_amount, total_amount = _compute_import_vat(preview_row.get('net_amount'))
    observations = _build_observations(preview_row)
    return {
        'FOSTAMP': stamp_factory(),
        'DOCNOME': FO_DOCNOME,
        'ADOC': _truncate(preview_row.get('document'), 60),
        'NOME': _truncate((supplier or {}).get('NOME', ''), 55),
        'ETOTAL': total_amount,
        'DATA': reservation_checkin,
        'TIPO': 'FO',
        'DOCDATA': service_date,
        'FOANO': reservation_checkin.year,
        'DOCCODE': FO_DOCCODE,
        'NO': SUPPLIER_NO,
        'CCUSTO': DEFAULT_CCUSTO,
        'PDATA': reservation_checkin,
        'PLANO': 0,
        'EIVAIN': net_amount,
        'ETTIVA': vat_amount,
        'EFINV': 0,
        'ETTILIQ': net_amount,
        'MORADA': _truncate((supplier or {}).get('MORADA', ''), 55),
        'LOCAL': _truncate((supplier or {}).get('LOCAL', ''), 43),
        'CODPOST': _truncate((supplier or {}).get('CODPOST', ''), 45),
        'NCONT': _truncate((supplier or {}).get('NCONT', ''), 20),
        'NMAPROV': '',
        'DTAPROV': reservation_checkin,
        'APROVADO': 0,
        'NOME2': '',
        'TPSTAMP': 'ADM26031347840,632337955 ',
        'TPDESC': 'AIRBNB',
        'OLLOCAL': 'WEB',
        'OUSRINIS': user_login or '',
        'OUSRDATA': reservation_checkin,
        'OUSRHORA': datetime.now().strftime('%H:%M'),
        'OBS': observations,
        'QR_CODE': '',
        'COLAB': '',
        'SYNC': 0,
        'IMPUTAR': 0,
        'IMPUTMES': 0,
        'IMPUTANO': 0,
        'IMPUTVALOR': Decimal('0.00'),
        'IMPUTDESIGN': '',
        'NIMPUTAR': 0,
        'EIVAV1': vat_amount,
        'EIVAV2': Decimal('0.00'),
        'EIVAV3': Decimal('0.00'),
        'EIVAV4': Decimal('0.00'),
        'EIVAV5': Decimal('0.00'),
        'EIVAV6': Decimal('0.00'),
        'EIVAV7': Decimal('0.00'),
        'EIVAV8': Decimal('0.00'),
        'EIVAV9': Decimal('0.00'),
    }


def _build_fn_payload(stamp_factory, article, preview_row, fo_stamp):
    service_date = parse_date(preview_row.get('service_date')) or date.today()
    net_amount, vat_amount, _ = _compute_import_vat(preview_row.get('net_amount'))
    tax_rate = IMPORT_TAX_RATE
    return {
        'FNSTAMP': stamp_factory(),
        'FOSTAMP': fo_stamp,
        'REF': _truncate((article or {}).get('REF', ARTICLE_REF), 18),
        'DESIGN': _build_line_design((article or {}).get('DESIGN', ''), preview_row),
        'UNIDADE': UNIT_DEFAULT,
        'TAXAIVA': tax_rate,
        'QTT': Decimal('1.00'),
        'IVA': vat_amount,
        'IVAINCL': 0,
        'TABIVA': IMPORT_TABIVA,
        'LORDEM': 1,
        'ETILIQUIDO': net_amount,
        'EPV': net_amount,
        'FNCCUSTO': DEFAULT_CCUSTO,
        'FAMILIA': _truncate((article or {}).get('FAMILIA', ''), 18),
        'DTCUSTO': service_date,
    }


def import_airbnb_commissions_rows(session, rows, user_login, stamp_factory):
    supplier, article = _load_supplier_and_article(session)
    if not supplier:
        raise ValueError('Fornecedor v_fl no=15 não encontrado.')
    if not article:
        raise ValueError("Artigo v_st ref='TX.SERVICO' não encontrado.")

    created = []
    skipped = []
    failed = []
    logs = []

    fo_insert_sql = text("""
        INSERT INTO dbo.FO
        (
            FOSTAMP, DOCNOME, ADOC, NOME, ETOTAL, DATA, TIPO, DOCDATA, FOANO, DOCCODE, NO, CCUSTO,
            PDATA, PLANO, EIVAIN, ETTIVA, EFINV, ETTILIQ, MORADA, LOCAL, CODPOST, NCONT,
            NMAPROV, DTAPROV, APROVADO, NOME2, TPSTAMP, TPDESC, OLLOCAL, OUSRINIS, OUSRDATA, OUSRHORA,
            OBS, QR_CODE, COLAB, SYNC, IMPUTAR, IMPUTMES, IMPUTANO, IMPUTVALOR, IMPUTDESIGN, NIMPUTAR,
            EIVAV1, EIVAV2, EIVAV3, EIVAV4, EIVAV5, EIVAV6, EIVAV7, EIVAV8, EIVAV9
        )
        VALUES
        (
            :FOSTAMP, :DOCNOME, :ADOC, :NOME, :ETOTAL, :DATA, :TIPO, :DOCDATA, :FOANO, :DOCCODE, :NO, :CCUSTO,
            :PDATA, :PLANO, :EIVAIN, :ETTIVA, :EFINV, :ETTILIQ, :MORADA, :LOCAL, :CODPOST, :NCONT,
            :NMAPROV, :DTAPROV, :APROVADO, :NOME2, :TPSTAMP, :TPDESC, :OLLOCAL, :OUSRINIS, :OUSRDATA, :OUSRHORA,
            :OBS, :QR_CODE, :COLAB, :SYNC, :IMPUTAR, :IMPUTMES, :IMPUTANO, :IMPUTVALOR, :IMPUTDESIGN, :NIMPUTAR,
            :EIVAV1, :EIVAV2, :EIVAV3, :EIVAV4, :EIVAV5, :EIVAV6, :EIVAV7, :EIVAV8, :EIVAV9
        )
    """)

    fn_insert_sql = text("""
        INSERT INTO dbo.FN
        (
            FNSTAMP, FOSTAMP, REF, DESIGN, UNIDADE, TAXAIVA, QTT, IVA, IVAINCL, TABIVA,
            LORDEM, ETILIQUIDO, EPV, FNCCUSTO, FAMILIA, DTCUSTO
        )
        VALUES
        (
            :FNSTAMP, :FOSTAMP, :REF, :DESIGN, :UNIDADE, :TAXAIVA, :QTT, :IVA, :IVAINCL, :TABIVA,
            :LORDEM, :ETILIQUIDO, :EPV, :FNCCUSTO, :FAMILIA, :DTCUSTO
        )
    """)

    for raw_row in rows or []:
        preview_row = dict(raw_row or {})
        row_no = int(preview_row.get('row_no') or 0)
        document_number = _truncate(preview_row.get('document'), 60)
        if not preview_row.get('can_import'):
            skipped.append({
                'row_no': row_no,
                'document': document_number,
                'message': preview_row.get('message') or 'Linha não elegível para importação.',
            })
            continue

        try:
            if _document_exists(session, document_number):
                skipped.append({
                    'row_no': row_no,
                    'document': document_number,
                    'message': 'Documento já existe.',
                })
                logs.append(f'row={row_no} skipped duplicate doc={document_number}')
                continue

            fo_payload = _build_fo_payload(stamp_factory, supplier, preview_row, user_login)
            fn_payload = _build_fn_payload(stamp_factory, article, preview_row, fo_payload['FOSTAMP'])

            session.execute(fo_insert_sql, fo_payload)
            session.execute(fn_insert_sql, fn_payload)
            session.commit()

            created.append({
                'row_no': row_no,
                'document': document_number,
                'fostamp': fo_payload['FOSTAMP'],
                'fnstamp': fn_payload['FNSTAMP'],
            })
            logs.append(f'row={row_no} imported doc={document_number} fostamp={fo_payload["FOSTAMP"]}')
        except Exception as exc:
            session.rollback()
            failed.append({
                'row_no': row_no,
                'document': document_number,
                'message': str(exc),
            })
            logs.append(f'row={row_no} failed doc={document_number} error={exc}')

    return {
        'ok': True,
        'created': created,
        'skipped': skipped,
        'failed': failed,
        'stats': {
            'created': len(created),
            'skipped': len(skipped),
            'failed': len(failed),
        },
        'logs': logs,
    }
