import hashlib
import fnmatch
import importlib.util
import io
import json
import mimetypes
import os
import re
import shutil
import threading
import uuid
from datetime import date, datetime
from decimal import Decimal
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from flask import current_app
from sqlalchemy import text

from models import db, DocInbox, DocParser, DocProcessLog, DocSource, DocTemplate, DocTemplateField
from services.document_ai_llm_service import llm_suggestions_available, suggest_template_definition
from services.document_ai_ocr_service import ocr_engine_available
from services.document_ai_processing_orchestrator import extract_document_with_cascade
from services.multiempresa_service import MissingCurrentEntityError, get_current_feid


DOC_AI_ALLOWED_UPLOAD_EXTENSIONS = {
    '.pdf',
    '.png',
    '.jpg',
    '.jpeg',
    '.tif',
    '.tiff',
    '.bmp',
    '.webp',
}

DOC_AI_DOC_TYPES = [
    {'value': 'invoice', 'label': 'Fatura'},
    {'value': 'credit_note', 'label': 'Nota de crédito'},
    {'value': 'purchase_order', 'label': 'Nota de encomenda'},
    {'value': 'delivery_note', 'label': 'Guia'},
    {'value': 'unknown', 'label': 'Desconhecido'},
]

DOC_AI_DOC_TYPE_TERMS = {
    'invoice': {
        'strong': ['invoice', 'facture', 'fatura', 'factura'],
        'normal': ['bill to', 'amount due', 'montant facture', 'total facture'],
        'weak': ['vat', 'iva', 'total'],
    },
    'credit_note': {
        'strong': ['credit note', 'nota de credito', 'nota de crédito', 'avoir', 'avoir facture'],
        'normal': ['credit memo', 'note de credit'],
        'weak': ['credito', 'credit'],
    },
    'purchase_order': {
        'strong': ['purchase order', 'nota de encomenda', 'bon de commande', 'bon commande'],
        'normal': ['commande fournisseur', 'order no', 'encomenda'],
        'weak': ['commande', 'order'],
    },
    'delivery_note': {
        'strong': [
            "bon d'enlevement",
            "bon d'enlèvement",
            'bon enlevement',
            'bon de livraison',
            'bon livraison',
            'bon de reception',
            'bon de réception',
            'delivery note',
            'guia de transporte',
            'packing slip',
        ],
        'normal': [
            'bon d enlevement',
            'bon d enlevement reception',
            'enlevement reception',
            'livraison',
            'reception transporteur',
            'transporteur routier',
            'poids total bl',
            'guia',
        ],
        'weak': ['transporteur', 'reception', 'enlevement', 'bl'],
    },
}

DOC_AI_STATUSES = [
    {'value': 'new', 'label': 'Novo'},
    {'value': 'text_extracted', 'label': 'Texto extraído'},
    {'value': 'template_unknown', 'label': 'Template desconhecido'},
    {'value': 'review_required', 'label': 'Por validar'},
    {'value': 'parsed_ok', 'label': 'Processado'},
    {'value': 'parse_error', 'label': 'Erro'},
]

DOC_AI_CANONICAL_SCHEMA = {
    'document_type': 'invoice',
    'supplier': {'supplier_no': None, 'tax_id': '', 'name': ''},
    'customer': {'tax_id': '', 'name': ''},
    'document_number': '',
    'document_date': '',
    'due_date': '',
    'currency': '',
    'totals': {'net_total': 0, 'tax_total': 0, 'gross_total': 0},
    'taxes': [],
    'lines': [],
    'warnings': [],
}

DOC_AI_GENERIC_FIELD_CONFIGS = {
    'document_number': {
        'label': 'Número documento',
        'anchors': ['invoice no', 'invoice number', 'document no', 'document number', 'factura n', 'fatura n', 'fatura nº', 'fatura no', 'doc no'],
        'regex': r'(?i)(?:invoice|document|factura|fatura)[^A-Z0-9]{0,12}(?:no|nr|n[oº])?[^A-Z0-9]{0,8}([A-Z0-9][A-Z0-9\/\.\-]{2,})',
        'postprocess': 'text',
    },
    'document_date': {
        'label': 'Data documento',
        'anchors': ['invoice date', 'date', 'document date', 'data', 'datum'],
        'regex': r'(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4})',
        'postprocess': 'date',
    },
    'due_date': {
        'label': 'Data vencimento',
        'anchors': ['due date', 'payment due', 'data vencimento', 'vencimento'],
        'regex': r'(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4})',
        'postprocess': 'date',
    },
    'currency': {
        'label': 'Moeda',
        'anchors': ['currency', 'moeda', 'devise'],
        'regex': r'\b(EUR|USD|GBP|CHF|BRL|AOA|MZN)\b',
        'postprocess': 'currency',
    },
    'gross_total': {
        'label': 'Total bruto',
        'anchors': ['grand total', 'total amount', 'amount due', 'total', 'total a pagar', 'total documento'],
        'regex': r'(-?\d{1,3}(?:[.\s]\d{3})*(?:,\d{2})|-?\d+(?:[.,]\d{2}))',
        'postprocess': 'decimal',
    },
    'net_total': {
        'label': 'Total líquido',
        'anchors': ['subtotal', 'net total', 'taxable amount', 'base tributável', 'base'],
        'regex': r'(-?\d{1,3}(?:[.\s]\d{3})*(?:,\d{2})|-?\d+(?:[.,]\d{2}))',
        'postprocess': 'decimal',
    },
    'tax_total': {
        'label': 'IVA total',
        'anchors': ['vat total', 'iva', 'tax total', 'imposto'],
        'regex': r'(-?\d{1,3}(?:[.\s]\d{3})*(?:,\d{2})|-?\d+(?:[.,]\d{2}))',
        'postprocess': 'decimal',
    },
    'supplier_tax_id': {
        'label': 'NIF fornecedor',
        'anchors': ['vat', 'tax id', 'nif', 'vat no', 'vat number'],
        'regex': r'\b(?:PT|ES|FR|DE|IT|NL|BE)?\s?(\d{9,14})\b',
        'postprocess': 'tax_id',
    },
    'supplier_name': {
        'label': 'Nome fornecedor',
        'anchors': ['supplier', 'fornecedor', 'vendor'],
        'regex': r'(?i)(?:supplier|fornecedor|vendor)\s*[:\-]\s*(.+)',
        'postprocess': 'text',
    },
    'customer_tax_id': {
        'label': 'NIF cliente',
        'anchors': ['customer vat', 'customer tax id', 'nif cliente'],
        'regex': r'\b(?:PT|ES|FR|DE|IT|NL|BE)?\s?(\d{9,14})\b',
        'postprocess': 'tax_id',
    },
    'customer_name': {
        'label': 'Nome cliente',
        'anchors': ['customer', 'bill to', 'cliente'],
        'regex': r'(?i)(?:customer|bill to|cliente)\s*[:\-]\s*(.+)',
        'postprocess': 'text',
    },
}

DOC_AI_DEFAULT_LINE_RULES = {
    'enabled': True,
    'header_aliases': ['ref', 'reference', 'description', 'designação', 'descricao', 'qty', 'quantidade', 'price', 'preço', 'amount', 'valor'],
    'stop_keywords': ['total', 'subtotal', 'iva', 'vat', 'amount due'],
    'start_anchor': '',
    'end_anchor': '',
    'columns': {},
}

_schema_ready_databases: set[str] = set()
_schema_ready_lock = threading.Lock()
_column_exists_cache: dict[tuple[str, str], bool] = {}


def _new_stamp() -> str:
    return uuid.uuid4().hex.upper()[:25]


def _now() -> datetime:
    return datetime.utcnow()


def _json_default(value: Any):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=_json_default)


def _json_loads(value: Any, fallback):
    if value in (None, ''):
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return fallback


def _normalize_text(value: Any) -> str:
    raw = str(value or '').strip().lower()
    if not raw:
        return ''
    replacements = {
        'ã': 'a', 'á': 'a', 'à': 'a', 'â': 'a',
        'é': 'e', 'ê': 'e',
        'í': 'i',
        'ó': 'o', 'ô': 'o', 'õ': 'o',
        'ú': 'u',
        'ç': 'c',
    }
    for src, dst in replacements.items():
        raw = raw.replace(src, dst)
    raw = re.sub(r'\s+', ' ', raw)
    return raw.strip()


def _digits_only(value: Any) -> str:
    return re.sub(r'\D+', '', str(value or ''))


def _safe_decimal(value: Any) -> float | None:
    if value in (None, ''):
        return None
    text_value = str(value).strip()
    if not text_value:
        return None
    text_value = text_value.replace('\u00a0', ' ')
    text_value = re.sub(r'[^0-9,\.\-]', '', text_value)
    if text_value.count(',') and text_value.count('.'):
        if text_value.rfind(',') > text_value.rfind('.'):
            text_value = text_value.replace('.', '').replace(',', '.')
        else:
            text_value = text_value.replace(',', '')
    elif text_value.count(',') and not text_value.count('.'):
        text_value = text_value.replace('.', '').replace(',', '.')
    else:
        text_value = text_value.replace(',', '')
    try:
        return float(text_value)
    except Exception:
        return None


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _column_exists(table_name: str, column_name: str) -> bool:
    key = (str(table_name or '').upper(), str(column_name or '').upper())
    if key in _column_exists_cache:
        return _column_exists_cache[key]
    exists = bool(db.session.execute(
        text("SELECT CASE WHEN COL_LENGTH(:table_name, :column_name) IS NULL THEN 0 ELSE 1 END"),
        {'table_name': f"dbo.{key[0]}", 'column_name': key[1]},
    ).scalar())
    _column_exists_cache[key] = exists
    return exists


def _fl_feid_filter_sql(alias: str = 'FL') -> str:
    if not _column_exists('FL', 'FEID'):
        return ''
    prefix = f"{alias}." if alias else ''
    return f" AND ISNULL({prefix}FEID, 0) = :feid"


def _safe_date_iso(value: Any) -> str:
    raw = str(value or '').strip()
    if not raw:
        return ''
    formats = (
        '%Y-%m-%d', '%Y/%m/%d',
        '%d-%m-%Y', '%d/%m/%Y',
        '%d.%m.%Y', '%Y.%m.%d',
    )
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except Exception:
            pass
    try:
        return datetime.fromisoformat(raw).date().isoformat()
    except Exception:
        return ''


def _guess_mime_type(filename: str) -> str:
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or 'application/octet-stream'


def _is_pdf(file_ext: str, mime_type: str) -> bool:
    ext = str(file_ext or '').lower()
    mime = str(mime_type or '').lower()
    return ext == '.pdf' or 'pdf' in mime


def _is_image(file_ext: str, mime_type: str) -> bool:
    ext = str(file_ext or '').lower()
    mime = str(mime_type or '').lower()
    return ext in {'.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp', '.webp'} or mime.startswith('image/')


def _file_hash(full_path: str) -> str:
    digest = hashlib.sha256()
    with open(full_path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(65536), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _split_lines(text_value: str) -> list[str]:
    return [line.strip() for line in str(text_value or '').splitlines() if str(line or '').strip()]


def _make_blocks_from_pages(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blocks = []
    for page in pages:
        page_no = _safe_int(page.get('page'), 0) or 1
        lines = _split_lines(page.get('text') or '')
        for idx, line in enumerate(lines, start=1):
            blocks.append({
                'id': f'p{page_no}-l{idx}',
                'page': page_no,
                'line_no': idx,
                'text': line,
            })
    return blocks


def _extract_pdf_blocks_with_fitz(file_path: str) -> dict[str, Any] | None:
    if not importlib.util.find_spec('fitz'):
        return None
    try:
        import fitz  # type: ignore
    except Exception:
        return None

    pages = []
    blocks = []
    all_text = []
    with fitz.open(file_path) as pdf:
        for page_no, page in enumerate(pdf, start=1):
            rect = page.rect
            page_width = round(float(rect.width or 0), 2)
            page_height = round(float(rect.height or 0), 2)
            pages.append({'page': page_no, 'width': page_width, 'height': page_height})
            raw = page.get_text('dict') or {}
            line_no = 0
            page_lines = []
            for block in (raw.get('blocks') or []):
                if _safe_int(block.get('type'), 0) != 0:
                    continue
                for line in (block.get('lines') or []):
                    spans = line.get('spans') or []
                    text_value = ''.join(str(span.get('text') or '') for span in spans).strip()
                    if not text_value:
                        continue
                    line_no += 1
                    bbox = line.get('bbox') or block.get('bbox') or [0, 0, 0, 0]
                    try:
                        x0, y0, x1, y1 = [float(item or 0) for item in bbox[:4]]
                    except Exception:
                        x0 = y0 = x1 = y1 = 0.0
                    blocks.append({
                        'id': f'pdf-p{page_no}-l{line_no}',
                        'page': page_no,
                        'line_no': line_no,
                        'text': text_value,
                        'left': round(x0, 2),
                        'top': round(y0, 2),
                        'width': round(max(x1 - x0, 0.0), 2),
                        'height': round(max(y1 - y0, 0.0), 2),
                        'page_width': page_width,
                        'page_height': page_height,
                    })
                    page_lines.append(text_value)
            if page_lines:
                all_text.append('\n'.join(page_lines))
    return {
        'pages': pages,
        'blocks': blocks,
        'text': '\n'.join(chunk for chunk in all_text if chunk).strip(),
    }


def _build_preview_pages(blocks: list[dict[str, Any]], raw_pages: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    page_map: dict[int, dict[str, Any]] = {}
    for raw_page in raw_pages or []:
        page_no = _safe_int(raw_page.get('page'), 0) or 1
        page_map[page_no] = {
            'page': page_no,
            'width': _safe_decimal(raw_page.get('width')) or 0,
            'height': _safe_decimal(raw_page.get('height')) or 0,
        }
    for block in blocks or []:
        page_no = _safe_int(block.get('page'), 0) or 1
        page_entry = page_map.setdefault(page_no, {'page': page_no, 'width': 0, 'height': 0})
        page_entry['width'] = max(float(page_entry.get('width') or 0), float(_safe_decimal(block.get('page_width')) or 0))
        page_entry['height'] = max(float(page_entry.get('height') or 0), float(_safe_decimal(block.get('page_height')) or 0))
    return [page_map[key] for key in sorted(page_map)]


def _document_storage_root() -> str:
    configured_root = (
        os.environ.get('DOCUMENT_AI_STORAGE_ROOT')
        or current_app.config.get('DOCUMENT_AI_STORAGE_ROOT')
        or current_app.root_path
    )
    return os.path.abspath(os.path.expanduser(str(configured_root or current_app.root_path).strip()))


def _document_local_path(path_value: str) -> str:
    raw = str(path_value or '').strip()
    if not raw:
        return ''
    parsed = urlparse(raw)
    if parsed.scheme in {'http', 'https'}:
        file_name = os.path.basename(parsed.path or '') or _new_stamp()
        return os.path.join(_document_storage_root(), 'static', 'images', 'document_ai', file_name)
    expanded = os.path.expanduser(raw)
    normalized_public_path = expanded.replace('\\', '/')
    if normalized_public_path.startswith('/static/'):
        return os.path.abspath(os.path.join(_document_storage_root(), normalized_public_path.lstrip('/').replace('/', os.sep)))
    if os.path.isabs(expanded):
        return os.path.abspath(expanded)
    return os.path.abspath(os.path.join(_document_storage_root(), expanded.lstrip('/').replace('/', os.sep)))


def _document_public_base_urls() -> list[str]:
    values = [
        os.environ.get('DOCUMENT_AI_PUBLIC_BASE_URLS'),
        os.environ.get('DOCUMENT_AI_PUBLIC_BASE_URL'),
        current_app.config.get('DOCUMENT_AI_PUBLIC_BASE_URLS'),
        current_app.config.get('DOCUMENT_AI_PUBLIC_BASE_URL'),
    ]
    urls: list[str] = []
    for value in values:
        for item in re.split(r'[;\n,]', str(value or '')):
            item = item.strip().rstrip('/')
            if item and item not in urls:
                urls.append(item)
    return urls


def _download_document_file(source_url: str, destination_path: str) -> bool:
    if not source_url or not destination_path:
        return False
    try:
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        request = Request(source_url, headers={'User-Agent': 'GR360 DocumentAI/1.0'})
        with urlopen(request, timeout=20) as response:
            if int(getattr(response, 'status', 200) or 200) >= 400:
                return False
            with open(destination_path, 'wb') as handle:
                shutil.copyfileobj(response, handle)
        return os.path.isfile(destination_path) and os.path.getsize(destination_path) > 0
    except Exception:
        current_app.logger.info('Document AI: nao foi possivel obter ficheiro remoto %s', source_url, exc_info=True)
        return False


def _try_cache_document_from_public_url(path_value: str, destination_path: str) -> bool:
    raw = str(path_value or '').strip()
    if not raw or not destination_path:
        return False
    parsed = urlparse(raw)
    if parsed.scheme in {'http', 'https'}:
        return _download_document_file(raw, destination_path)
    if not raw.startswith('/'):
        return False
    for base_url in _document_public_base_urls():
        if _download_document_file(urljoin(f'{base_url}/', raw.lstrip('/')), destination_path):
            return True
    return False


def _mapped_document_path(path_value: str) -> str:
    raw = str(path_value or '').strip()
    if not raw:
        return ''
    normalized_path = _normalize_source_path_for_match(raw)
    for source_prefix, local_prefix in _document_source_path_mappings():
        normalized_prefix = _normalize_source_path_for_match(source_prefix)
        if not normalized_prefix:
            continue
        if normalized_path == normalized_prefix or normalized_path.startswith(f'{normalized_prefix}/'):
            source_prefix_slash = source_prefix.replace('\\', '/').rstrip('/')
            suffix = raw.replace('\\', '/').rstrip('/')[len(source_prefix_slash):].lstrip('/')
            candidate = os.path.abspath(os.path.join(os.path.expanduser(local_prefix), *suffix.split('/')))
            if os.path.isfile(candidate):
                return candidate
    return ''


def _document_absolute_path(document: DocInbox) -> str:
    raw_path = str(document.file_path or '').strip()
    absolute_path = _document_local_path(raw_path)
    if absolute_path and os.path.isfile(absolute_path):
        return absolute_path

    mapped_path = _mapped_document_path(raw_path)
    if mapped_path:
        return mapped_path

    if absolute_path and _try_cache_document_from_public_url(raw_path, absolute_path):
        return absolute_path

    return absolute_path


def _document_preview_payload(document: DocInbox, blocks: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    absolute_path = _document_absolute_path(document)
    current_blocks = list(blocks or [])
    preview_pages = _build_preview_pages(current_blocks)
    if _is_pdf(document.file_ext, document.mime_type):
        if not current_blocks or not any(block.get('page_width') and block.get('height') and block.get('width') for block in current_blocks):
            fitz_payload = _extract_pdf_blocks_with_fitz(absolute_path)
            if fitz_payload and fitz_payload.get('blocks'):
                current_blocks = fitz_payload.get('blocks') or current_blocks
                preview_pages = fitz_payload.get('pages') or preview_pages
        elif not preview_pages:
            fitz_payload = _extract_pdf_blocks_with_fitz(absolute_path)
            if fitz_payload:
                preview_pages = fitz_payload.get('pages') or preview_pages
    return current_blocks, preview_pages


def canonical_result_base(document_type: str = 'unknown') -> dict[str, Any]:
    data = json.loads(json.dumps(DOC_AI_CANONICAL_SCHEMA))
    data['document_type'] = document_type or 'unknown'
    return data


def _ensure_document_ai_schema():
    try:
        database_name = str(db.session.execute(text('SELECT DB_NAME()')).scalar() or '').strip() or '__default__'
    except Exception:
        database_name = '__default__'

    with _schema_ready_lock:
        if database_name in _schema_ready_databases:
            return

        migration_path = os.path.join(current_app.root_path, 'migrations', 'doc_intelligence.sql')
        if not os.path.isfile(migration_path):
            raise FileNotFoundError(f'Ficheiro de migration não encontrado: {migration_path}')

        with open(migration_path, 'r', encoding='utf-8') as handle:
            sql_script = handle.read()

        statements = [
            chunk.strip()
            for chunk in re.split(r'^\s*GO\s*$', sql_script, flags=re.MULTILINE | re.IGNORECASE)
            if chunk and chunk.strip()
        ]
        for statement in statements:
            db.session.execute(text(statement))
        db.session.commit()
        _schema_ready_databases.add(database_name)


def _ensure_document_sources_schema():
    _ensure_document_ai_schema()
    db.session.execute(text("""
        IF OBJECT_ID('dbo.DOC_SOURCE', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.DOC_SOURCE (
                DOCSOURCESTAMP varchar(25) NOT NULL
                    CONSTRAINT PK_DOC_SOURCE PRIMARY KEY,
                NOME varchar(120) NOT NULL
                    CONSTRAINT DF_DOC_SOURCE_NOME DEFAULT '',
                PASTA nvarchar(500) NOT NULL
                    CONSTRAINT DF_DOC_SOURCE_PASTA DEFAULT N'',
                PADRAO_FICHEIROS varchar(120) NOT NULL
                    CONSTRAINT DF_DOC_SOURCE_PADRAO DEFAULT '',
                SUBPASTAS bit NOT NULL
                    CONSTRAINT DF_DOC_SOURCE_SUBPASTAS DEFAULT 0,
                ATIVO bit NOT NULL
                    CONSTRAINT DF_DOC_SOURCE_ATIVO DEFAULT 1,
                INTERVALO_MINUTOS int NOT NULL
                    CONSTRAINT DF_DOC_SOURCE_INTERVALO DEFAULT 5,
                ULTIMA_EXECUCAO datetime NULL,
                ULTIMO_ESTADO varchar(30) NOT NULL
                    CONSTRAINT DF_DOC_SOURCE_ULT_ESTADO DEFAULT '',
                ULTIMA_MENSAGEM nvarchar(500) NOT NULL
                    CONSTRAINT DF_DOC_SOURCE_ULT_MSG DEFAULT N'',
                DTCRI datetime NOT NULL
                    CONSTRAINT DF_DOC_SOURCE_DTCRI DEFAULT GETDATE(),
                DTALT datetime NULL,
                USERCRIACAO varchar(50) NOT NULL
                    CONSTRAINT DF_DOC_SOURCE_USERCRI DEFAULT '',
                USERALTERACAO varchar(50) NOT NULL
                    CONSTRAINT DF_DOC_SOURCE_USERALT DEFAULT ''
            );

            CREATE INDEX IX_DOC_SOURCE_ATIVO
                ON dbo.DOC_SOURCE (ATIVO, NOME);
        END
    """))
    db.session.commit()


def _ensure_default_parser() -> DocParser:
    parser = DocParser.query.filter_by(codigo='TEXT_RULES_V1').first()
    if parser:
        return parser
    parser = DocParser(
        docparserstamp=_new_stamp(),
        codigo='TEXT_RULES_V1',
        nome='Text Rules Parser',
        descricao='Parser textual base para documentos de compra com anchors, regex e regras.',
        familia='text_rules',
        versao='1.0',
        schema_output_json=_json_dumps(DOC_AI_CANONICAL_SCHEMA),
        ativo=True,
        dtcri=_now(),
        usercriacao='system',
        useralteracao='system',
    )
    db.session.add(parser)
    db.session.commit()
    return parser


def _document_log(document_stamp: str, phase: str, status: str, message: str, detail: dict[str, Any] | None = None):
    log = DocProcessLog(
        docprocesslogstamp=_new_stamp(),
        docinstamp=document_stamp,
        fase=str(phase or '').strip()[:40] or 'general',
        status=str(status or '').strip()[:20] or 'info',
        mensagem=str(message or '').strip()[:255],
        detalhe_json=_json_dumps(detail or {}),
        dtcri=_now(),
    )
    db.session.add(log)


def _supplier_candidates_from_text(text_value: str) -> list[str]:
    candidates = []
    for match in re.finditer(r'\b(?:PT|ES|FR|DE|IT|NL|BE)?\s?(\d{9,14})\b', str(text_value or ''), re.IGNORECASE):
        digits = _digits_only(match.group(1))
        if 9 <= len(digits) <= 14 and digits not in candidates:
            candidates.append(digits)
    return candidates[:12]


def _serialize_fe_row(row: dict[str, Any] | None, score: float = 0, matched_by: str = '') -> dict[str, Any]:
    if not row:
        return {}
    name = str(row.get('NOMEFISCAL') or row.get('NOME') or '').strip()
    return {
        'feid': _safe_int(row.get('FEID'), 0) or None,
        'name': name,
        'tax_id': _digits_only(row.get('NIF')),
        'score': round(float(score or 0), 4),
        'matched_by': matched_by,
    }


def _load_fe_entities() -> list[dict[str, Any]]:
    rows = db.session.execute(text("""
        SELECT
            CAST(ISNULL(FEID, 0) AS int) AS FEID,
            LTRIM(RTRIM(ISNULL(NOME, ''))) AS NOME,
            LTRIM(RTRIM(ISNULL(NOMEFISCAL, ''))) AS NOMEFISCAL,
            LTRIM(RTRIM(CAST(ISNULL(NIF, 0) AS varchar(40)))) AS NIF
        FROM dbo.FE
        WHERE ISNULL(FEID, 0) <> 0
          AND (ISNULL(NOME, '') <> '' OR ISNULL(NOMEFISCAL, '') <> '')
    """)).mappings().all()
    return [dict(row) for row in rows]


def resolve_fe_entity(value: str, match_mode: str = 'auto') -> dict[str, Any]:
    raw = str(value or '').strip()
    if not raw:
        return {}

    digits = _digits_only(raw)
    if len(digits) >= 6 and match_mode in ('auto', 'tax_id'):
        row = db.session.execute(text("""
            SELECT TOP 1
                CAST(ISNULL(FEID, 0) AS int) AS FEID,
                LTRIM(RTRIM(ISNULL(NOME, ''))) AS NOME,
                LTRIM(RTRIM(ISNULL(NOMEFISCAL, ''))) AS NOMEFISCAL,
                LTRIM(RTRIM(CAST(ISNULL(NIF, 0) AS varchar(40)))) AS NIF
            FROM dbo.FE
            WHERE REPLACE(REPLACE(REPLACE(REPLACE(LTRIM(RTRIM(CAST(ISNULL(NIF, 0) AS varchar(40)))), ' ', ''), '-', ''), '.', ''), '/', '') = :digits
            ORDER BY ISNULL(NOMEFISCAL, ISNULL(NOME, ''))
        """), {'digits': digits}).mappings().first()
        if row:
            return _serialize_fe_row(dict(row), 0.99, 'tax_id')

    normalized_raw = _normalize_text(raw)
    if len(normalized_raw) < 3:
        return {}

    best: dict[str, Any] = {}
    best_score = 0.0
    for entity in _load_fe_entities():
        names = [
            str(entity.get('NOMEFISCAL') or '').strip(),
            str(entity.get('NOME') or '').strip(),
        ]
        for name in names:
            normalized_name = _normalize_text(name)
            if not normalized_name or len(normalized_name) < 3:
                continue
            name_tokens = [token for token in normalized_name.split(' ') if len(token) > 2]
            token_hits = sum(1 for token in name_tokens if token in normalized_raw)
            token_score = token_hits / max(len(name_tokens), 1)
            ratio = SequenceMatcher(None, normalized_name, normalized_raw).ratio()
            score = max(token_score * 0.86, ratio * 0.7)
            if normalized_name in normalized_raw or normalized_raw in normalized_name:
                score = max(score, 0.9)
            if score > best_score:
                best_score = score
                best = entity
    if best and best_score >= 0.35:
        return _serialize_fe_row(best, best_score, 'name')
    return {}


def identify_fe_entity_from_text(text_value: str) -> dict[str, Any]:
    normalized_text = _normalize_text(text_value)
    for vat in _supplier_candidates_from_text(text_value):
        match = resolve_fe_entity(vat, 'tax_id')
        if match:
            return match

    best: dict[str, Any] = {}
    best_score = 0.0
    for entity in _load_fe_entities():
        names = [
            str(entity.get('NOMEFISCAL') or '').strip(),
            str(entity.get('NOME') or '').strip(),
        ]
        for name in names:
            normalized_name = _normalize_text(name)
            if not normalized_name or len(normalized_name) < 4:
                continue
            name_tokens = [token for token in normalized_name.split(' ') if len(token) > 2]
            token_hits = sum(1 for token in name_tokens if token in normalized_text)
            token_score = token_hits / max(len(name_tokens), 1)
            ratio = SequenceMatcher(None, normalized_name, normalized_text).ratio()
            score = max(token_score * 0.86, ratio * 0.6)
            if normalized_name in normalized_text:
                score = max(score, 0.92)
            if score > best_score:
                best_score = score
                best = entity
    if best and best_score >= 0.35:
        return _serialize_fe_row(best, best_score, 'name')
    return {}


def _load_suppliers(feid: int | None = None) -> list[dict[str, Any]]:
    feid_filter = _fl_feid_filter_sql('FL') if feid else ''
    feid_select = "CAST(ISNULL(FL.FEID, 0) AS int)" if _column_exists('FL', 'FEID') else "CAST(0 AS int)"
    rows = db.session.execute(text("""
        SELECT
            CAST(FL.NO AS int) AS NO,
            LTRIM(RTRIM(ISNULL(FL.NOME, ''))) AS NOME,
            LTRIM(RTRIM(ISNULL(FL.NIF, ''))) AS NIF,
            {feid_select} AS FEID
        FROM dbo.FL FL
        WHERE ISNULL(FL.NOME, '') <> ''
        {feid_filter}
        ORDER BY FL.NOME
    """.format(feid_filter=feid_filter, feid_select=feid_select)), {'feid': int(feid or 0)}).mappings().all()
    return [dict(row) for row in rows]


def search_suppliers(value: str, feid: int | None = None, limit: int = 8) -> list[dict[str, Any]]:
    if not _safe_int(feid, 0):
        raise ValueError('Identifica primeiro a Entidade FE do cliente.')
    raw = str(value or '').strip()
    normalized_raw = _normalize_text(raw)
    digits = _digits_only(raw)
    if len(normalized_raw) < 2 and len(digits) < 2:
        return []

    results: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()
    for supplier in _load_suppliers(feid):
        supplier_no = _safe_int(supplier.get('NO'), 0)
        supplier_feid = _safe_int(supplier.get('FEID'), 0)
        key = (supplier_feid, supplier_no)
        if key in seen:
            continue
        seen.add(key)

        name = str(supplier.get('NOME') or '').strip()
        tax_id = _digits_only(supplier.get('NIF'))
        no_text = str(supplier_no or '')
        normalized_name = _normalize_text(name)

        score = 0.0
        matched_by = ''
        if digits:
            if tax_id and digits == tax_id:
                score = 0.99
                matched_by = 'tax_id'
            elif tax_id and (digits in tax_id or tax_id in digits):
                score = max(score, 0.88)
                matched_by = matched_by or 'tax_id'
            elif no_text and digits == no_text:
                score = max(score, 0.96)
                matched_by = matched_by or 'number'
            elif no_text and digits in no_text:
                score = max(score, 0.72)
                matched_by = matched_by or 'number'

        if normalized_raw and normalized_name:
            if normalized_raw == normalized_name:
                score = max(score, 0.98)
                matched_by = matched_by or 'name'
            elif normalized_raw in normalized_name or normalized_name in normalized_raw:
                score = max(score, 0.9)
                matched_by = matched_by or 'name'
            name_tokens = [token for token in normalized_name.split(' ') if len(token) > 2]
            raw_tokens = [token for token in normalized_raw.split(' ') if len(token) > 2]
            if name_tokens and raw_tokens:
                token_hits = sum(1 for token in raw_tokens if token in normalized_name)
                token_score = token_hits / max(len(raw_tokens), 1)
                score = max(score, token_score * 0.84)
                if token_hits:
                    matched_by = matched_by or 'name'
            ratio = SequenceMatcher(None, normalized_name, normalized_raw).ratio()
            if ratio >= 0.35:
                score = max(score, ratio * 0.82)
                matched_by = matched_by or 'name'

        if score < 0.32:
            continue
        results.append({
            'no': supplier_no,
            'name': name,
            'tax_id': tax_id,
            'feid': supplier_feid or (int(feid or 0) or None),
            'score': round(min(score, 0.99), 4),
            'matched_by': matched_by or 'name',
        })

    results.sort(key=lambda item: (-float(item.get('score') or 0), str(item.get('name') or '')))
    return results[:max(1, min(int(limit or 8), 20))]


def identify_supplier_from_text(text_value: str, feid: int | None = None) -> dict[str, Any]:
    normalized_text = _normalize_text(text_value)
    vat_candidates = _supplier_candidates_from_text(text_value)
    best = {
        'supplier_no': None,
        'supplier_name': '',
        'supplier_tax_id': '',
        'score': 0.0,
        'matched_by': '',
    }

    for vat in vat_candidates:
        feid_filter = _fl_feid_filter_sql('FL') if feid else ''
        row = db.session.execute(text("""
            SELECT TOP 1
                CAST(FL.NO AS int) AS NO,
                LTRIM(RTRIM(ISNULL(FL.NOME, ''))) AS NOME,
                LTRIM(RTRIM(ISNULL(FL.NIF, ''))) AS NIF
            FROM dbo.FL FL
            WHERE REPLACE(REPLACE(REPLACE(REPLACE(LTRIM(RTRIM(ISNULL(FL.NIF, ''))), ' ', ''), '-', ''), '.', ''), '/', '') = :vat
            {feid_filter}
        """.format(feid_filter=feid_filter)), {
            'vat': vat,
            'feid': int(feid or 0),
        }).mappings().first()
        if row:
            return {
                'supplier_no': _safe_int(row.get('NO'), 0) or None,
                'supplier_name': str(row.get('NOME') or '').strip(),
                'supplier_tax_id': _digits_only(row.get('NIF')),
                'score': 0.98,
                'matched_by': 'vat',
                'feid': int(feid or 0) or None,
            }

    suppliers = _load_suppliers(feid)
    for supplier in suppliers:
        supplier_name = str(supplier.get('NOME') or '').strip()
        normalized_name = _normalize_text(supplier_name)
        if not normalized_name or len(normalized_name) < 4:
            continue
        token_hits = 0
        name_tokens = [token for token in normalized_name.split(' ') if len(token) > 2]
        for token in name_tokens:
            if token in normalized_text:
                token_hits += 1
        token_score = token_hits / max(len(name_tokens), 1)
        ratio = SequenceMatcher(None, normalized_name, normalized_text).ratio()
        if token_score < 0.35 and ratio < 0.15:
            continue
        score = max(token_score * 0.85, ratio * 0.6)
        if normalized_name in normalized_text:
            score = max(score, 0.88)
        if score > best['score']:
            best = {
                'supplier_no': _safe_int(supplier.get('NO'), 0) or None,
                'supplier_name': supplier_name,
                'supplier_tax_id': _digits_only(supplier.get('NIF')),
                'score': round(min(score, 0.92), 4),
                'matched_by': 'name',
                'feid': int(feid or 0) or None,
            }
    return best


def _doc_type_term_hits(normalized_text: str, terms: list[str]) -> list[str]:
    hits = []
    for term in terms:
        normalized_term = _normalize_text(term)
        if not normalized_term:
            continue
        if re.fullmatch(r'[a-z0-9]{1,3}', normalized_term):
            if re.search(rf'\b{re.escape(normalized_term)}\b', normalized_text):
                hits.append(term)
            continue
        if normalized_term in normalized_text:
            hits.append(term)
    return hits


def classify_document_type(text_value: str, supplier_match: dict[str, Any] | None = None, template_match: dict[str, Any] | None = None) -> dict[str, Any]:
    normalized = _normalize_text(text_value)
    score_map = {
        'invoice': 0.0,
        'credit_note': 0.0,
        'purchase_order': 0.0,
        'delivery_note': 0.0,
        'unknown': 0.2,
    }
    reasons: list[str] = []

    if template_match and 'forced' in (template_match.get('reasons') or []) and template_match.get('doc_type'):
        forced_type = str(template_match.get('doc_type') or 'unknown').strip() or 'unknown'
        return {
            'doc_type': forced_type,
            'score': 0.99,
            'supplier_no': (supplier_match or {}).get('supplier_no'),
            'reasons': ['forced_template'],
        }

    strong_hits_by_type: dict[str, list[str]] = {}
    for doc_type, term_group in DOC_AI_DOC_TYPE_TERMS.items():
        strong_hits = _doc_type_term_hits(normalized, list(term_group.get('strong') or []))
        if strong_hits:
            strong_hits_by_type[doc_type] = strong_hits
            score_map[doc_type] += 0.72 + min(0.18, len(strong_hits) * 0.06)
        normal_hits = _doc_type_term_hits(normalized, list(term_group.get('normal') or []))
        weak_hits = _doc_type_term_hits(normalized, list(term_group.get('weak') or []))
        score_map[doc_type] += len(normal_hits) * 0.24
        score_map[doc_type] += len(weak_hits) * 0.06
        if strong_hits or normal_hits:
            reasons.extend([f'{doc_type}:{term}' for term in [*strong_hits, *normal_hits][:6]])

    if strong_hits_by_type:
        best_strong_type = max(strong_hits_by_type.keys(), key=lambda item: score_map.get(item, 0))
        return {
            'doc_type': best_strong_type,
            'score': round(min(score_map.get(best_strong_type, 0.92), 0.99), 4),
            'supplier_no': (supplier_match or {}).get('supplier_no'),
            'reasons': [f'strong_term:{term}' for term in strong_hits_by_type.get(best_strong_type, [])],
        }

    if re.search(r'\biva\b|\bvat\b', normalized):
        score_map['invoice'] += 0.12
        score_map['credit_note'] += 0.04
        reasons.append('tax_term')
    if re.search(r'\btotal\b', normalized):
        score_map['invoice'] += 0.1
        score_map['credit_note'] += 0.05
        reasons.append('total_term')
    if re.search(r'\bguia\b|\btransporte\b|\blivraison\b|\benlevement\b', normalized):
        score_map['delivery_note'] += 0.14
        reasons.append('delivery_term')
    if re.search(r'\bencomenda\b|\border\b|\bcommande\b', normalized):
        score_map['purchase_order'] += 0.14
        reasons.append('order_term')
    if template_match and template_match.get('doc_type') and template_match.get('score', 0) > 0.55:
        score_map[str(template_match.get('doc_type'))] = max(
            score_map.get(str(template_match.get('doc_type')), 0),
            min(0.98, float(template_match.get('score') or 0) + 0.08),
        )
        reasons.append('template_match')

    best_type = 'unknown'
    best_score = 0.2
    for doc_type, score in score_map.items():
        if score > best_score:
            best_type = doc_type
            best_score = score

    return {
        'doc_type': best_type,
        'score': round(min(best_score, 0.99), 4),
        'supplier_no': (supplier_match or {}).get('supplier_no'),
        'reasons': reasons[:10],
    }


def _load_document_rows(limit: int = 80) -> list[dict[str, Any]]:
    rows = db.session.execute(text(f"""
        SELECT TOP {max(1, min(limit, 500))}
            D.DOCINSTAMP,
            D.FILE_NAME,
            D.PROCESSING_STATUS,
            D.DTCRI,
            D.DTPROC
        FROM dbo.DOC_INBOX D
        ORDER BY D.DTCRI DESC
    """)).mappings().all()
    return [dict(row) for row in rows]


def _serialize_parser(parser: DocParser | dict[str, Any] | None) -> dict[str, Any] | None:
    if not parser:
        return None
    if isinstance(parser, dict):
        return {
            'id': str(parser.get('DOCPARSERSTAMP') or parser.get('docparserstamp') or '').strip(),
            'code': str(parser.get('CODIGO') or parser.get('codigo') or '').strip(),
            'name': str(parser.get('NOME') or parser.get('nome') or '').strip(),
            'family': str(parser.get('FAMILIA') or parser.get('familia') or '').strip(),
            'version': str(parser.get('VERSAO') or parser.get('versao') or '').strip(),
            'active': bool(parser.get('ATIVO') if 'ATIVO' in parser else parser.get('ativo')),
        }
    return {
        'id': parser.docparserstamp,
        'code': parser.codigo,
        'name': parser.nome,
        'family': parser.familia,
        'version': parser.versao,
        'active': bool(parser.ativo),
    }


def _serialize_template(template: DocTemplate, include_definition: bool = False) -> dict[str, Any]:
    supplier_name = ''
    if template.fornecedor_no:
        feid_filter = _fl_feid_filter_sql('FL') if template.feid else ''
        row = db.session.execute(text("""
            SELECT TOP 1 LTRIM(RTRIM(ISNULL(NOME, ''))) AS NOME
            FROM dbo.FL FL
            WHERE CAST(NO AS int) = :supplier_no
            {feid_filter}
        """.format(feid_filter=feid_filter)), {
            'supplier_no': template.fornecedor_no,
            'feid': int(template.feid or 0),
        }).mappings().first()
        supplier_name = str((row or {}).get('NOME') or '').strip()

    parser = None
    if template.docparserstamp:
        parser = db.session.get(DocParser, template.docparserstamp)

    payload = {
        'id': template.doctemplatestamp,
        'name': template.nome,
        'description': template.descricao or '',
        'feid': template.feid,
        'supplier_no': template.fornecedor_no,
        'supplier_name': supplier_name,
        'doc_type': template.doc_type or 'unknown',
        'language': template.idioma or '',
        'fingerprint': template.fingerprint or '',
        'score_min_match': float(template.score_minimo_match or 0),
        'parser': _serialize_parser(parser),
        'parser_id': template.docparserstamp or '',
        'parser_version': template.parser_version or '',
        'active': bool(template.ativo),
        'created_at': template.dtcri.isoformat() if template.dtcri else None,
        'updated_at': template.dtalt.isoformat() if template.dtalt else None,
    }
    if include_definition:
        payload['match_rules'] = _json_loads(template.regras_identificacao_json, {})
        payload['definition'] = _json_loads(template.definition_json, {})
        field_rows = (
            DocTemplateField.query
            .filter_by(doctemplatestamp=template.doctemplatestamp)
            .order_by(DocTemplateField.ordem, DocTemplateField.field_key)
            .all()
        )
        payload['fields'] = [
            {
                'id': row.doctemplatefieldstamp,
                'field_key': row.field_key,
                'label': row.label or row.field_key,
                'order': row.ordem or 0,
                'required': bool(row.required),
                'match_mode': row.match_mode or 'anchor_regex',
                'anchors': _json_loads(row.anchors_json, []),
                'regex': row.regex_pattern or '',
                'aliases': _json_loads(row.aliases_json, []),
                'postprocess': row.postprocess or '',
                'config': _json_loads(row.config_json, {}),
                'active': bool(row.ativo),
            }
            for row in field_rows
        ]
    return payload


def _load_template_candidates(supplier_no: int | None, doc_type: str, feid: int | None = None) -> list[DocTemplate]:
    query = DocTemplate.query.filter_by(ativo=True)
    doc_type = str(doc_type or '').strip()
    if doc_type and doc_type != 'unknown':
        query = query.filter(text("(DOC_TYPE = :doc_type OR DOC_TYPE = 'unknown')")).params(doc_type=doc_type)
    if feid:
        query = query.filter(text("(FEID IS NULL OR FEID = 0 OR FEID = :feid)")).params(feid=int(feid or 0))
    templates = query.order_by(
        text("CASE WHEN ISNULL(FEID, 0) = 0 THEN 1 ELSE 0 END"),
        text("CASE WHEN FORNECEDOR_NO IS NULL THEN 1 ELSE 0 END"),
        DocTemplate.fornecedor_no.desc(),
        DocTemplate.nome.asc(),
    ).all()
    if supplier_no is None:
        return templates
    ordered = [item for item in templates if item.fornecedor_no == supplier_no]
    ordered.extend([item for item in templates if item.fornecedor_no is None])
    return ordered


def _template_definition_payload(template: DocTemplate) -> dict[str, Any]:
    definition = _json_loads(template.definition_json, {})
    field_rows = (
        DocTemplateField.query
        .filter_by(doctemplatestamp=template.doctemplatestamp, ativo=True)
        .order_by(DocTemplateField.ordem, DocTemplateField.field_key)
        .all()
    )
    fields = {}
    for row in field_rows:
        fields[row.field_key] = {
            'label': row.label or row.field_key,
            'anchors': _json_loads(row.anchors_json, []),
            'regex': row.regex_pattern or '',
            'aliases': _json_loads(row.aliases_json, []),
            'required': bool(row.required),
            'postprocess': row.postprocess or '',
            'config': _json_loads(row.config_json, {}),
            'match_mode': row.match_mode or 'anchor_regex',
        }
    if fields:
        definition['fields'] = fields
    definition['match'] = definition.get('match') or _json_loads(template.regras_identificacao_json, {})
    definition['doc_type'] = definition.get('doc_type') or template.doc_type or 'unknown'
    definition['parser_id'] = template.docparserstamp or ''
    definition['parser_version'] = template.parser_version or ''
    return definition


def _evaluate_template_match(template: DocTemplate, text_value: str, supplier_no: int | None, doc_type: str, feid: int | None = None) -> dict[str, Any]:
    definition = _template_definition_payload(template)
    match_rules = definition.get('match') or {}
    normalized = _normalize_text(text_value)
    score = 0.0
    reasons = []

    if template.feid and feid and int(template.feid or 0) == int(feid or 0):
        score += 0.18
        reasons.append('feid')
    elif template.feid and int(template.feid or 0) != int(feid or 0):
        return {'template': template, 'score': 0.0, 'reasons': ['feid_mismatch'], 'doc_type': definition.get('doc_type') or template.doc_type}

    if template.fornecedor_no and supplier_no and int(template.fornecedor_no) == int(supplier_no):
        score += 0.28
        reasons.append('supplier')
    elif template.fornecedor_no and supplier_no and int(template.fornecedor_no) != int(supplier_no):
        return {'template': template, 'score': 0.0, 'reasons': ['supplier_mismatch'], 'doc_type': definition.get('doc_type') or template.doc_type}

    template_doc_type = str(definition.get('doc_type') or template.doc_type or 'unknown').strip() or 'unknown'
    if doc_type and doc_type != 'unknown' and template_doc_type not in ('', 'unknown'):
        if template_doc_type == doc_type:
            score += 0.22
            reasons.append('doc_type')
        else:
            score -= 0.08

    keywords = [item for item in (match_rules.get('keywords') or []) if str(item or '').strip()]
    required = [item for item in (match_rules.get('required') or []) if str(item or '').strip()]
    forbidden = [item for item in (match_rules.get('forbidden') or []) if str(item or '').strip()]

    keyword_hits = 0
    for keyword in keywords:
        if _normalize_text(keyword) in normalized:
            keyword_hits += 1
    if keywords:
        score += min(0.42, keyword_hits * 0.10)
        if keyword_hits:
            reasons.append(f'keywords:{keyword_hits}')

    field_anchor_hits = 0
    for field_def in (definition.get('fields') or {}).values():
        anchors = [item for item in (field_def.get('anchors') or []) if str(item or '').strip()]
        if any(_normalize_text(anchor) in normalized for anchor in anchors):
            field_anchor_hits += 1
    if field_anchor_hits:
        score += min(0.26, field_anchor_hits * 0.045)
        reasons.append(f'field_anchors:{field_anchor_hits}')

    for item in forbidden:
        if _normalize_text(item) in normalized:
            return {'template': template, 'score': 0.0, 'reasons': ['forbidden'], 'doc_type': template_doc_type}

    if required:
        missing = [item for item in required if _normalize_text(item) not in normalized]
        if missing:
            if template.fornecedor_no and supplier_no and int(template.fornecedor_no) == int(supplier_no):
                score -= min(0.18, len(missing) * 0.06)
                reasons.append(f'missing_required_soft:{len(missing)}')
            else:
                return {'template': template, 'score': 0.0, 'reasons': ['missing_required'], 'doc_type': template_doc_type}
        score += min(0.2, len(required) * 0.05)
        reasons.append('required')

    if template.fingerprint and _normalize_text(template.fingerprint) in normalized:
        score += 0.18
        reasons.append('fingerprint')

    return {
        'template': template,
        'score': round(max(score, 0.0), 4),
        'reasons': reasons,
        'doc_type': template_doc_type,
    }


def _choose_best_template(text_value: str, supplier_no: int | None, doc_type: str, feid: int | None = None) -> dict[str, Any] | None:
    candidates = _load_template_candidates(supplier_no, doc_type, feid)
    best_payload = None
    for template in candidates:
        evaluated = _evaluate_template_match(template, text_value, supplier_no, doc_type, feid)
        min_score = float(template.score_minimo_match or 0)
        if evaluated['score'] < min_score:
            continue
        if not best_payload or evaluated['score'] > best_payload['score']:
            best_payload = evaluated
    return best_payload


def _apply_postprocess(value: Any, postprocess: str) -> Any:
    mode = str(postprocess or '').strip().lower()
    if value is None:
        return ''
    if mode == 'decimal':
        decimal_value = _safe_decimal(value)
        return 0 if decimal_value is None else round(decimal_value, 2)
    if mode == 'date':
        return _safe_date_iso(value)
    if mode == 'currency':
        matched = re.search(r'\b([A-Z]{3})\b', str(value or '').upper())
        return matched.group(1) if matched else str(value or '').strip().upper()
    if mode == 'tax_id':
        return _digits_only(value)
    return str(value or '').strip()


def _extract_value_after_anchor(candidate_text: str, anchor: str) -> str:
    normalized_anchor = _normalize_text(anchor)
    raw_text = str(candidate_text or '').strip()
    normalized_raw = _normalize_text(raw_text)
    pos = normalized_raw.find(normalized_anchor)
    if pos < 0:
        return raw_text
    suffix = raw_text[pos + len(anchor):].strip(' \t\r\n:.-')
    return suffix or raw_text


def _extract_field_from_text(lines: list[str], full_text: str, field_key: str, config: dict[str, Any]) -> dict[str, Any]:
    anchors = [str(item or '').strip() for item in (config.get('anchors') or []) if str(item or '').strip()]
    aliases = [str(item or '').strip() for item in (config.get('aliases') or []) if str(item or '').strip()]
    regex_pattern = str(config.get('regex') or '').strip()
    postprocess = str(config.get('postprocess') or '').strip()
    config_payload = config.get('config') or {}
    sample_text = str(config_payload.get('sample_text') or config_payload.get('sample_value') or '').strip()
    normalized_sample = _normalize_text(sample_text)
    search_terms = anchors + aliases
    candidate_windows = []
    for idx, line in enumerate(lines):
        normalized_line = _normalize_text(line)
        for term in search_terms:
            if _normalize_text(term) and _normalize_text(term) in normalized_line:
                window = '\n'.join(lines[idx:idx + 2])
                candidate_windows.append((window, term, idx))
                break

    if normalized_sample:
        for idx, line in enumerate(lines):
            if normalized_sample in _normalize_text(line):
                return {
                    'field_key': field_key,
                    'value': _apply_postprocess(sample_text, postprocess),
                    'raw_value': sample_text,
                    'matched_anchor': sample_text,
                    'line_index': idx,
                    'confidence': 0.96,
                }

    if not candidate_windows:
        candidate_windows = [(full_text, '', -1)]

    for candidate_text, term, line_idx in candidate_windows:
        extracted = ''
        exact_line = lines[line_idx] if 0 <= line_idx < len(lines) else candidate_text.splitlines()[0]
        if normalized_sample and normalized_sample in _normalize_text(candidate_text):
            return {
                'field_key': field_key,
                'value': _apply_postprocess(sample_text, postprocess),
                'raw_value': sample_text,
                'matched_anchor': term or sample_text,
                'line_index': line_idx,
                'confidence': 0.94 if term else 0.9,
            }
        if regex_pattern:
            try:
                match = re.search(regex_pattern, candidate_text, re.IGNORECASE | re.MULTILINE)
            except re.error:
                match = None
            if match:
                extracted = next((group for group in match.groups() if group is not None), match.group(0))
        elif term:
            extracted = _extract_value_after_anchor(exact_line, term)
        if not extracted and term:
            extracted = _extract_value_after_anchor(exact_line, term)
        if extracted:
            return {
                'field_key': field_key,
                'value': _apply_postprocess(extracted, postprocess),
                'raw_value': extracted,
                'matched_anchor': term,
                'line_index': line_idx,
                'confidence': 0.72 if term else 0.55,
            }

    if regex_pattern:
        try:
            match = re.search(regex_pattern, full_text, re.IGNORECASE | re.MULTILINE)
        except re.error:
            match = None
        if match:
            extracted = next((group for group in match.groups() if group is not None), match.group(0))
            return {
                'field_key': field_key,
                'value': _apply_postprocess(extracted, postprocess),
                'raw_value': extracted,
                'matched_anchor': '',
                'line_index': -1,
                'confidence': 0.62,
            }

    return {
        'field_key': field_key,
        'value': '' if postprocess != 'decimal' else 0,
        'raw_value': '',
        'matched_anchor': '',
        'line_index': -1,
        'confidence': 0.0,
    }


def _set_nested_result(target: dict[str, Any], field_key: str, value: Any):
    if field_key == 'document_number':
        target['document_number'] = str(value or '').strip()
        return
    if field_key == 'document_date':
        target['document_date'] = str(value or '').strip()
        return
    if field_key == 'due_date':
        target['due_date'] = str(value or '').strip()
        return
    if field_key == 'currency':
        target['currency'] = str(value or '').strip()
        return
    if field_key == 'supplier_tax_id':
        target['supplier']['tax_id'] = str(value or '').strip()
        return
    if field_key == 'supplier_name':
        target['supplier']['name'] = str(value or '').strip()
        return
    if field_key == 'customer_tax_id':
        target['customer']['tax_id'] = str(value or '').strip()
        return
    if field_key == 'customer_name':
        target['customer']['name'] = str(value or '').strip()
        return
    if field_key == 'gross_total':
        target['totals']['gross_total'] = float(value or 0)
        return
    if field_key == 'net_total':
        target['totals']['net_total'] = float(value or 0)
        return
    if field_key == 'tax_total':
        target['totals']['tax_total'] = float(value or 0)
        return
    if field_key.startswith('tax_base_') or field_key.startswith('tax_amount_'):
        suffix = field_key.split('_')[-1]
        try:
            rate = int(suffix)
        except Exception:
            rate = 0
        taxes = target.setdefault('taxes', [])
        bucket = next((item for item in taxes if int(item.get('tax_rate') or 0) == rate), None)
        numeric_value = float(value or 0)
        if bucket is None and numeric_value == 0:
            return
        if bucket is None:
            bucket = {
                'tax_rate': rate,
                'taxable_base': 0.0,
                'tax_amount': 0.0,
                'gross_total': 0.0,
            }
            taxes.append(bucket)
        if field_key.startswith('tax_base_'):
            bucket['taxable_base'] = numeric_value
        else:
            bucket['tax_amount'] = numeric_value
        bucket['gross_total'] = round(float(bucket.get('taxable_base') or 0) + float(bucket.get('tax_amount') or 0), 2)
        return
    target[field_key] = value


def _extract_lines_table(lines: list[str], line_rules: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    rules = dict(DOC_AI_DEFAULT_LINE_RULES)
    if line_rules:
        rules.update(line_rules)
    if not rules.get('enabled'):
        return []

    def _find_anchor_index(items: list[str], anchor: str, start: int = 0) -> int:
        normalized_anchor = _normalize_text(anchor)
        if not normalized_anchor:
            return -1
        for idx in range(max(0, start), len(items)):
            if normalized_anchor in _normalize_text(items[idx]):
                return idx
        return -1

    def _parse_line_with_columns(raw_line: str, positions: list[tuple[str, int]]) -> dict[str, Any] | None:
        if not positions:
            return None
        normalized_line = _normalize_text(raw_line)
        if len(normalized_line) < 2:
            return None
        row_values: dict[str, str] = {}
        for idx, (column_key, start_pos) in enumerate(positions):
            end_pos = positions[idx + 1][1] if idx + 1 < len(positions) else len(raw_line)
            segment = raw_line[start_pos:end_pos].strip(' \t|')
            row_values[column_key] = segment

        if not any(item for item in row_values.values()):
            return None

        ref_value = row_values.get('ref', '')
        description_value = row_values.get('description', '')
        qty_value = _safe_decimal(row_values.get('qty', '')) or 0
        unit_price_value = _safe_decimal(row_values.get('unit_price', '')) or 0
        discount_value = _safe_decimal(row_values.get('discount', '')) or 0
        total_value = _safe_decimal(row_values.get('total', '')) or 0
        vat_value = _safe_decimal(row_values.get('vat', '')) or 0

        if not description_value and not ref_value and not total_value:
            return None

        return {
            'ref': str(ref_value or '')[:120],
            'description': str(description_value or raw_line).strip()[:400],
            'qty': qty_value,
            'unit': '',
            'unit_price': unit_price_value,
            'discount': discount_value,
            'tax_rate': vat_value,
            'net_amount': total_value,
            'tax_amount': round(total_value * (vat_value / 100.0), 2) if vat_value else 0,
            'gross_amount': round(total_value + (total_value * (vat_value / 100.0)), 2) if vat_value else total_value,
        }

    def _parse_line_by_tokens(raw_line: str, configured_columns: dict[str, Any]) -> dict[str, Any] | None:
        text_value = re.sub(r'\s+', ' ', str(raw_line or '').replace('*1', ' ').replace('*I', ' ')).strip()
        if len(text_value) < 4:
            return None

        money_matches = list(re.finditer(r'-?\d{1,3}(?:[.\s]\d{3})*(?:,\d{2})|-?\d+(?:[.,]\d{2})', text_value))
        percent_matches = list(re.finditer(r'(\d+(?:[.,]\d+)?)\s*%', text_value))
        if not money_matches:
            return None

        first_money = money_matches[0]
        prefix = text_value[:first_money.start()].strip()
        prefix_tokens = prefix.split()
        qty_index = -1
        qty_value = 0.0
        for idx in range(len(prefix_tokens) - 1, -1, -1):
            token = prefix_tokens[idx].strip()
            if re.fullmatch(r'\d+(?:[.,]\d+)?', token):
                qty_index = idx
                qty_value = _safe_decimal(token) or 0.0
                break

        ref_value = ''
        description_value = ''
        unit_value = ''
        if prefix_tokens:
            if qty_index >= 0:
                has_ref = bool((configured_columns or {}).get('ref'))
                ref_value = prefix_tokens[0] if has_ref else ''
                desc_start = 1 if has_ref and len(prefix_tokens) > 1 else 0
                description_tokens = prefix_tokens[desc_start:qty_index]
                description_value = ' '.join(description_tokens).strip()
                unit_value = ' '.join(prefix_tokens[qty_index + 1:]).strip()
            else:
                has_ref = bool((configured_columns or {}).get('ref'))
                ref_value = prefix_tokens[0] if has_ref else ''
                description_tokens = prefix_tokens[1:] if has_ref else prefix_tokens
                description_value = ' '.join(description_tokens).strip()

        money_values = [_safe_decimal(match.group(0)) or 0.0 for match in money_matches]
        unit_price_value = money_values[0] if money_values else 0.0
        total_value = money_values[-1] if money_values else 0.0
        discount_value = 0.0
        if len(money_values) >= 3 and bool((configured_columns or {}).get('discount')):
            discount_value = money_values[-2]
        vat_value = _safe_decimal(percent_matches[-1].group(1)) if percent_matches else 0.0

        if not description_value and not ref_value:
            description_value = text_value

        if not description_value and not total_value and not qty_value:
            return None

        tax_amount_value = round(total_value * ((vat_value or 0.0) / 100.0), 2) if vat_value else 0.0
        gross_amount_value = round(total_value + tax_amount_value, 2) if total_value else 0.0
        return {
            'ref': str(ref_value or '')[:120],
            'description': str(description_value or text_value).strip()[:400],
            'qty': qty_value,
            'unit': str(unit_value or '')[:20],
            'unit_price': unit_price_value,
            'discount': discount_value,
            'tax_rate': vat_value or 0.0,
            'net_amount': total_value,
            'tax_amount': tax_amount_value,
            'gross_amount': gross_amount_value or total_value,
        }

    header_aliases = [_normalize_text(item) for item in (rules.get('header_aliases') or []) if str(item or '').strip()]
    stop_keywords = [_normalize_text(item) for item in (rules.get('stop_keywords') or []) if str(item or '').strip()]
    start_anchor = str(rules.get('start_anchor') or '').strip()
    end_anchor = str(rules.get('end_anchor') or '').strip()
    columns = rules.get('columns') or {}

    header_index = _find_anchor_index(lines, start_anchor) if start_anchor else -1
    if header_index < 0:
        for idx, line in enumerate(lines):
            normalized_line = _normalize_text(line)
            hits = sum(1 for alias in header_aliases if alias and alias in normalized_line)
            if hits >= 2:
                header_index = idx
                break
    if header_index < 0:
        return []

    data_start_index = header_index + 1
    if start_anchor and 0 <= header_index < len(lines):
        header_line_normalized = _normalize_text(lines[header_index])
        configured_column_anchors = [
            _normalize_text((config or {}).get('anchor'))
            for config in (columns.values() if isinstance(columns, dict) else [])
            if _normalize_text((config or {}).get('anchor'))
        ]
        looks_like_header = any(anchor in header_line_normalized for anchor in configured_column_anchors) or (
            sum(1 for alias in header_aliases if alias and alias in header_line_normalized) >= 2
        )
        if not looks_like_header:
            data_start_index = header_index

    end_index = _find_anchor_index(lines, end_anchor, header_index + 1) if end_anchor else -1
    end_index = end_index if end_index >= 0 else len(lines)

    normalized_header = _normalize_text(lines[header_index])
    column_positions: list[tuple[str, int]] = []
    for column_key, config in (columns.items() if isinstance(columns, dict) else []):
        anchor = str((config or {}).get('anchor') or '').strip()
        normalized_anchor = _normalize_text(anchor)
        if not normalized_anchor:
            continue
        position = normalized_header.find(normalized_anchor)
        if position >= 0:
            column_positions.append((column_key, position))
    column_positions.sort(key=lambda item: item[1])

    results = []
    for raw_line in lines[data_start_index:end_index]:
        normalized_line = _normalize_text(raw_line)
        if any(keyword in normalized_line for keyword in stop_keywords):
            break
        if len(raw_line.strip()) < 4:
            continue
        heuristic = _parse_line_by_tokens(raw_line, columns if isinstance(columns, dict) else {})
        if heuristic:
            results.append(heuristic)
            continue
        structured = _parse_line_with_columns(raw_line, column_positions)
        if structured:
            results.append(structured)
            continue
        amounts = re.findall(r'-?\d{1,3}(?:[.\s]\d{3})*(?:,\d{2})|-?\d+(?:[.,]\d{2})', raw_line)
        qty_match = re.search(r'(^|\s)(\d+(?:[.,]\d+)?)\s+', raw_line)
        description = re.sub(r'\s{2,}', ' ', raw_line).strip()
        if len(amounts) < 1 and not qty_match:
            continue
        qty = _safe_decimal(qty_match.group(2)) if qty_match else 0
        gross = _safe_decimal(amounts[-1]) if amounts else 0
        unit_price = _safe_decimal(amounts[-2]) if len(amounts) >= 2 else 0
        results.append({
            'ref': '',
            'description': description[:400],
            'qty': qty or 0,
            'unit': '',
            'unit_price': unit_price or 0,
            'discount': 0,
            'tax_rate': 0,
            'net_amount': gross or 0,
            'tax_amount': 0,
            'gross_amount': gross or 0,
        })
    return results


def _group_text_blocks_rows(blocks: list[dict[str, Any]], line_rules: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    area = (line_rules or {}).get('area') if isinstance(line_rules, dict) else None
    area_page = _safe_int((area or {}).get('page'), 0) or None
    area_left = _safe_decimal((area or {}).get('left')) if isinstance(area, dict) else None
    area_top = _safe_decimal((area or {}).get('top')) if isinstance(area, dict) else None
    area_width = _safe_decimal((area or {}).get('width')) if isinstance(area, dict) else None
    area_height = _safe_decimal((area or {}).get('height')) if isinstance(area, dict) else None
    use_area = all(value is not None and value > 0 for value in (area_width, area_height)) and area_left is not None and area_top is not None

    filtered = []
    for block in blocks or []:
        text_value = str(block.get('text') or '').strip()
        if not text_value:
            continue
        page_no = _safe_int(block.get('page'), 0) or 1
        if area_page and page_no != area_page:
            continue
        if use_area:
            page_width = _safe_decimal(block.get('page_width')) or 0
            page_height = _safe_decimal(block.get('page_height')) or 0
            left = _safe_decimal(block.get('left')) or 0
            top = _safe_decimal(block.get('top')) or 0
            width = _safe_decimal(block.get('width')) or 0
            height = _safe_decimal(block.get('height')) or 0
            if page_width > 0 and page_height > 0 and width > 0 and height > 0:
                center_x = (left + (width / 2.0)) / page_width
                center_y = (top + (height / 2.0)) / page_height
                if not (
                    area_left <= center_x <= (area_left + area_width)
                    and area_top <= center_y <= (area_top + area_height)
                ):
                    continue
        filtered.append({
            'page': page_no,
            'line_no': _safe_int(block.get('line_no'), 0),
            'top': _safe_decimal(block.get('top')) or 0,
            'left': _safe_decimal(block.get('left')) or 0,
            'height': _safe_decimal(block.get('height')) or 0,
            'text': text_value,
        })

    if not filtered:
        return [
            {
                'page': _safe_int(block.get('page'), 0) or 1,
                'line_no': _safe_int(block.get('line_no'), 0),
                'text': str(block.get('text') or '').strip(),
                'blocks': [block],
            }
            for block in blocks or []
            if str(block.get('text') or '').strip()
        ]

    grouped: list[list[dict[str, Any]]] = []
    filtered.sort(key=lambda item: (item['page'], item['line_no'] if item['line_no'] > 0 else 999999, item['top'], item['left']))
    for block in filtered:
        appended = False
        if grouped:
            last_group = grouped[-1]
            last = last_group[-1]
            same_page = last['page'] == block['page']
            same_line_no = block['line_no'] > 0 and last['line_no'] > 0 and last['line_no'] == block['line_no']
            top_tolerance = max(float(last.get('height') or 0) * 0.65, float(block.get('height') or 0) * 0.65, 10.0)
            same_visual_row = abs(float(last.get('top') or 0) - float(block.get('top') or 0)) <= top_tolerance
            if same_page and (same_line_no or same_visual_row):
                last_group.append(block)
                appended = True
        if not appended:
            grouped.append([block])

    rows = []
    for row_blocks in grouped:
        row_blocks.sort(key=lambda item: item['left'])
        row_text = ' '.join(str(item.get('text') or '').strip() for item in row_blocks if str(item.get('text') or '').strip())
        row_text = re.sub(r'\s{2,}', ' ', row_text).strip()
        if row_text:
            rows.append({
                'page': row_blocks[0].get('page'),
                'line_no': row_blocks[0].get('line_no'),
                'text': row_text,
                'blocks': row_blocks,
            })
    return rows


def _group_text_blocks_for_lines(blocks: list[dict[str, Any]], line_rules: dict[str, Any] | None = None) -> list[str]:
    return [str(item.get('text') or '').strip() for item in _group_text_blocks_rows(blocks, line_rules) if str(item.get('text') or '').strip()]


def _extract_lines_from_grouped_rows(block_rows: list[dict[str, Any]], line_rules: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    rules = dict(DOC_AI_DEFAULT_LINE_RULES)
    if line_rules:
        rules.update(line_rules)
    if not rules.get('enabled'):
        return []

    rows = [item for item in (block_rows or []) if str(item.get('text') or '').strip()]
    if not rows:
        return []

    def _find_row_index(anchor: str, start: int = 0) -> int:
        normalized_anchor = _normalize_text(anchor)
        if not normalized_anchor:
            return -1
        for idx in range(max(0, start), len(rows)):
            if normalized_anchor in _normalize_text(rows[idx].get('text') or ''):
                return idx
        return -1

    def _text_from_blocks(items: list[dict[str, Any]]) -> str:
        ordered = sorted(items or [], key=lambda item: (_safe_decimal(item.get('left')) or 0))
        return re.sub(r'\s{2,}', ' ', ' '.join(str(item.get('text') or '').strip() for item in ordered if str(item.get('text') or '').strip())).strip()

    def _find_header_block(anchor: str, header_blocks: list[dict[str, Any]]) -> dict[str, Any] | None:
        normalized_anchor = _normalize_text(anchor)
        if not normalized_anchor:
            return None
        best = None
        best_score = -1
        for item in header_blocks or []:
            block_text = _normalize_text(item.get('text') or '')
            if not block_text:
                continue
            if normalized_anchor in block_text or block_text in normalized_anchor:
                score = min(len(normalized_anchor), len(block_text))
                if normalized_anchor == block_text:
                    score += 1000
                if score > best_score:
                    best = item
                    best_score = score
        return best

    def _extract_percent(raw: str) -> float:
        match = re.search(r'(\d+(?:[.,]\d+)?)\s*%', str(raw or ''))
        return _safe_decimal(match.group(1)) if match else (_safe_decimal(raw) or 0.0)

    start_anchor = str(rules.get('start_anchor') or '').strip()
    end_anchor = str(rules.get('end_anchor') or '').strip()
    header_aliases = [_normalize_text(item) for item in (rules.get('header_aliases') or []) if str(item or '').strip()]
    stop_keywords = [_normalize_text(item) for item in (rules.get('stop_keywords') or []) if str(item or '').strip()]
    columns = rules.get('columns') or {}

    header_index = _find_row_index(start_anchor) if start_anchor else -1
    if header_index < 0:
        for idx, row in enumerate(rows):
            normalized_row = _normalize_text(row.get('text') or '')
            hits = sum(1 for alias in header_aliases if alias and alias in normalized_row)
            if hits >= 2:
                header_index = idx
                break
    if header_index < 0:
        return []

    end_index = _find_row_index(end_anchor, header_index + 1) if end_anchor else -1
    end_index = end_index if end_index >= 0 else len(rows)
    header_blocks = list(rows[header_index].get('blocks') or [])

    column_defs = []
    for column_key, config in (columns.items() if isinstance(columns, dict) else []):
        anchor = str((config or {}).get('anchor') or '').strip()
        header_block = _find_header_block(anchor, header_blocks)
        if not header_block:
            continue
        left = _safe_decimal(header_block.get('left')) or 0.0
        width = _safe_decimal(header_block.get('width')) or 0.0
        right = left + width
        center = left + (width / 2.0)
        column_defs.append({
            'key': column_key,
            'anchor': anchor,
            'left': left,
            'right': right,
            'center': center,
        })

    column_defs.sort(key=lambda item: item['center'])
    if not column_defs:
        return []

    boundaries = []
    for idx, item in enumerate(column_defs):
        left_boundary = -10**9 if idx == 0 else (column_defs[idx - 1]['center'] + item['center']) / 2.0
        right_boundary = 10**9 if idx == len(column_defs) - 1 else (item['center'] + column_defs[idx + 1]['center']) / 2.0
        boundaries.append((item['key'], left_boundary, right_boundary, item))

    qty_def = next((item for item in column_defs if item['key'] == 'qty'), None)
    price_def = next((item for item in column_defs if item['key'] == 'unit_price'), None)

    results = []
    for row in rows[header_index + 1:end_index]:
        normalized_row = _normalize_text(row.get('text') or '')
        if any(keyword in normalized_row for keyword in stop_keywords):
            break
        row_blocks = list(row.get('blocks') or [])
        if not row_blocks:
            continue

        assigned: dict[str, list[dict[str, Any]]] = {item['key']: [] for item in column_defs}
        unit_blocks: list[dict[str, Any]] = []
        for block in row_blocks:
            block_text = str(block.get('text') or '').strip()
            if not block_text:
                continue
            left = _safe_decimal(block.get('left')) or 0.0
            width = _safe_decimal(block.get('width')) or 0.0
            center = left + (width / 2.0)

            if qty_def and price_def and qty_def['center'] < center < price_def['center']:
                if re.fullmatch(r'[A-Z]{1,6}', block_text.strip(), re.IGNORECASE):
                    unit_blocks.append(block)
                    continue

            chosen_key = None
            for key, left_boundary, right_boundary, _meta in boundaries:
                if left_boundary <= center < right_boundary:
                    chosen_key = key
                    break
            if chosen_key:
                assigned.setdefault(chosen_key, []).append(block)

        ref_value = _text_from_blocks(assigned.get('ref', []))
        description_value = _text_from_blocks(assigned.get('description', []))
        qty_value = _safe_decimal(_text_from_blocks(assigned.get('qty', []))) or 0.0
        unit_value = _text_from_blocks(unit_blocks)
        unit_price_value = _safe_decimal(_text_from_blocks(assigned.get('unit_price', []))) or 0.0
        discount_raw = _text_from_blocks(assigned.get('discount', []))
        discount_value = _safe_decimal(discount_raw) or 0.0
        total_value = _safe_decimal(_text_from_blocks(assigned.get('total', []))) or 0.0
        vat_raw = _text_from_blocks(assigned.get('vat', []))
        vat_value = _extract_percent(vat_raw)

        if not description_value and not ref_value:
            continue

        tax_amount_value = round(total_value * ((vat_value or 0.0) / 100.0), 2) if vat_value else 0.0
        gross_amount_value = round(total_value + tax_amount_value, 2) if total_value else 0.0
        results.append({
            'ref': str(ref_value or '')[:120],
            'description': str(description_value or '').strip()[:400],
            'qty': qty_value,
            'unit': str(unit_value or '')[:20],
            'unit_price': unit_price_value,
            'discount': discount_value,
            'tax_rate': vat_value or 0.0,
            'net_amount': total_value,
            'tax_amount': tax_amount_value,
            'gross_amount': gross_amount_value or total_value,
        })

    return results


def _execute_template_parse(text_value: str, blocks: list[dict[str, Any]], template_payload: dict[str, Any] | None, supplier_match: dict[str, Any], doc_type_info: dict[str, Any]) -> dict[str, Any]:
    definition = template_payload.get('definition') if template_payload else {}
    fields_config = definition.get('fields') if definition else {}
    if not fields_config:
        fields_config = DOC_AI_GENERIC_FIELD_CONFIGS
    lines = [str(block.get('text') or '').strip() for block in blocks if str(block.get('text') or '').strip()]
    if not lines:
        lines = _split_lines(text_value)
    result = canonical_result_base(doc_type_info.get('doc_type') or 'unknown')
    result['supplier']['supplier_no'] = supplier_match.get('supplier_no')
    if supplier_match.get('supplier_tax_id'):
        result['supplier']['tax_id'] = supplier_match.get('supplier_tax_id')
    if supplier_match.get('supplier_name'):
        result['supplier']['name'] = supplier_match.get('supplier_name')

    extracted_fields = []
    field_confidences = []
    for field_key, config in fields_config.items():
        if not isinstance(config, dict):
            continue
        extracted = _extract_field_from_text(lines, text_value, field_key, config)
        _set_nested_result(result, field_key, extracted.get('value'))
        extracted_fields.append(extracted)
        field_confidences.append(float(extracted.get('confidence') or 0))

    line_rules = definition.get('lines') if isinstance(definition.get('lines'), dict) else DOC_AI_DEFAULT_LINE_RULES
    grouped_line_rows = _group_text_blocks_rows(blocks, line_rules)
    grouped_line_texts = [str(item.get('text') or '').strip() for item in grouped_line_rows if str(item.get('text') or '').strip()]
    parsed_lines = _extract_lines_from_grouped_rows(grouped_line_rows, line_rules)
    if not parsed_lines:
        parsed_lines = _extract_lines_table(grouped_line_texts or lines, line_rules)
    if parsed_lines:
        result['lines'] = parsed_lines
    warnings = []
    if not parsed_lines and (line_rules or {}).get('enabled'):
        warnings.append('Não foi possível detetar linhas com confiança suficiente.')

    result['warnings'] = warnings
    average_confidence = sum(field_confidences) / max(len(field_confidences), 1)
    return {
        'result': result,
        'extracted_fields': extracted_fields,
        'warnings': warnings,
        'confidence': round(min(0.99, average_confidence), 4),
    }


def _validate_parse_result(parse_payload: dict[str, Any], template_match: dict[str, Any] | None) -> dict[str, Any]:
    result = parse_payload.get('result') or canonical_result_base('unknown')
    warnings = list(result.get('warnings') or [])
    errors = []

    if not str(result.get('document_number') or '').strip():
        warnings.append('Número do documento não detetado.')
    if not str(result.get('document_date') or '').strip():
        warnings.append('Data do documento não detetada.')
    if float((result.get('totals') or {}).get('gross_total') or 0) <= 0:
        warnings.append('Total bruto não detetado com segurança.')
    if not result.get('supplier', {}).get('supplier_no'):
        warnings.append('Fornecedor não identificado automaticamente.')

    status = 'parsed_ok'
    if errors:
        status = 'parse_error'
    elif not template_match:
        status = 'template_unknown'
    elif warnings:
        status = 'review_required'

    return {
        'status': status,
        'warnings': warnings,
        'errors': errors,
    }


def _pdf_extract_with_fitz(file_path: str) -> dict[str, Any] | None:
    fitz_payload = _extract_pdf_blocks_with_fitz(file_path)
    if not fitz_payload:
        return None
    return {
        'engine': 'fitz',
        'text': fitz_payload.get('text') or '',
        'blocks': fitz_payload.get('blocks') or [],
        'raw_json': {'pages': fitz_payload.get('pages') or []},
        'warnings': [],
    }


def _pdf_extract_with_pypdf(file_path: str) -> dict[str, Any] | None:
    if not importlib.util.find_spec('pypdf'):
        return None
    from pypdf import PdfReader  # type: ignore

    reader = PdfReader(file_path)
    pages = []
    chunks = []
    for idx, page in enumerate(reader.pages, start=1):
        text_value = page.extract_text() or ''
        pages.append({'page': idx, 'text': text_value})
        if text_value.strip():
            chunks.append(text_value)
    blocks = _make_blocks_from_pages(pages)
    return {
        'engine': 'pypdf',
        'text': '\n'.join(chunks).strip(),
        'blocks': blocks,
        'raw_json': {'pages': pages},
        'warnings': [],
    }


def _pdf_ocr_with_fitz(file_path: str) -> dict[str, Any] | None:
    if not (importlib.util.find_spec('fitz') and ocr_engine_available()):
        return None
    try:
        import fitz  # type: ignore
        from PIL import Image
        import pytesseract
    except Exception:
        return None

    warnings = []
    pages = []
    all_blocks = []
    all_lines = []
    with fitz.open(file_path) as pdf:
        for page_no, page in enumerate(pdf, start=1):
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            image = Image.open(io.BytesIO(pix.tobytes('png')))
            raw = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            page_blocks = []
            total = len(raw.get('text', []) or [])
            for idx in range(total):
                chunk = str((raw.get('text') or [''])[idx] or '').strip()
                if not chunk:
                    continue
                block = {
                    'id': f'ocr-p{page_no}-{idx + 1}',
                    'page': page_no,
                    'line_no': _safe_int((raw.get('line_num') or [0])[idx], idx + 1),
                    'text': chunk,
                    'left': _safe_int((raw.get('left') or [0])[idx], 0),
                    'top': _safe_int((raw.get('top') or [0])[idx], 0),
                    'width': _safe_int((raw.get('width') or [0])[idx], 0),
                    'height': _safe_int((raw.get('height') or [0])[idx], 0),
                    'page_width': _safe_int(pix.width, 0),
                    'page_height': _safe_int(pix.height, 0),
                }
                page_blocks.append(block)
                all_blocks.append(block)
                all_lines.append(chunk)
            pages.append({'page': page_no, 'block_count': len(page_blocks), 'width': _safe_int(pix.width, 0), 'height': _safe_int(pix.height, 0)})
    warnings.append('Texto obtido por OCR de fallback.')
    return {
        'engine': 'pdf_ocr_fitz_pytesseract',
        'text': '\n'.join(all_lines).strip(),
        'blocks': all_blocks,
        'raw_json': {'pages': pages},
        'warnings': warnings,
    }


def extract_document_text(
    file_path: str,
    file_ext: str = '',
    mime_type: str = '',
    document_stamp: str = '',
    force_mode: str = 'auto',
    manual_adjustments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return extract_document_with_cascade(
        file_path=file_path,
        file_ext=file_ext,
        mime_type=mime_type,
        document_stamp=document_stamp,
        force_mode=force_mode,
        manual_adjustments=manual_adjustments,
    )


def _doc_queryset_sql(filters: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    where_parts = []
    params: dict[str, Any] = {}
    status = str(filters.get('status') or '').strip()
    if status:
        where_parts.append("UPPER(LTRIM(RTRIM(ISNULL(D.PROCESSING_STATUS, '')))) = :status")
        params['status'] = status.upper()
    doc_type = str(filters.get('doc_type') or '').strip()
    if doc_type:
        where_parts.append("UPPER(LTRIM(RTRIM(ISNULL(D.DOC_TYPE_DETECTED, '')))) = :doc_type")
        params['doc_type'] = doc_type.upper()
    supplier = str(filters.get('supplier') or '').strip()
    if supplier:
        where_parts.append("""
            (
                CAST(ISNULL(D.FORNECEDOR_NO, 0) AS varchar(30)) LIKE :supplier_like
                OR UPPER(LTRIM(RTRIM(ISNULL(F.NOME, '')))) LIKE :supplier_like
            )
        """)
        params['supplier_like'] = f"%{supplier.upper()}%"
    search = str(filters.get('search') or '').strip()
    if search:
        where_parts.append("""
            (
                UPPER(LTRIM(RTRIM(ISNULL(D.FILE_NAME, '')))) LIKE :search_like
                OR UPPER(LTRIM(RTRIM(ISNULL(T.NOME, '')))) LIKE :search_like
                OR UPPER(LTRIM(RTRIM(ISNULL(F.NOME, '')))) LIKE :search_like
                OR UPPER(LTRIM(RTRIM(ISNULL(D.FORNECEDOR_NOME_DETETADO, '')))) LIKE :search_like
                OR UPPER(LTRIM(RTRIM(ISNULL(FE.NOME, '')))) LIKE :search_like
                OR UPPER(LTRIM(RTRIM(ISNULL(FE.NOMEFISCAL, '')))) LIKE :search_like
            )
        """)
        params['search_like'] = f"%{search.upper()}%"
    date_from = str(filters.get('date_from') or '').strip()
    if date_from:
        where_parts.append("CAST(D.DTCRI AS date) >= :date_from")
        params['date_from'] = date_from
    date_to = str(filters.get('date_to') or '').strip()
    if date_to:
        where_parts.append("CAST(D.DTCRI AS date) <= :date_to")
        params['date_to'] = date_to
    where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ''
    return where_sql, params


def list_documents(filters: dict[str, Any] | None = None) -> dict[str, Any]:
    _ensure_document_ai_schema()
    query_filters = filters or {}
    where_sql, params = _doc_queryset_sql(query_filters)
    rows = db.session.execute(text(f"""
        SELECT
            D.DOCINSTAMP,
            D.FILE_NAME,
            D.FILE_PATH,
            D.FILE_EXT,
            D.MIME_TYPE,
            D.EXTRACTION_METHOD,
            D.EXTRACTION_QUALITY_SCORE,
            D.DOC_TYPE_DETECTED,
            D.FEID,
            ISNULL(NULLIF(FE.NOMEFISCAL, ''), ISNULL(FE.NOME, '')) AS FE_NOME,
            LTRIM(RTRIM(CAST(ISNULL(FE.NIF, 0) AS varchar(40)))) AS FE_NIF,
            D.FORNECEDOR_NO,
            ISNULL(F.NOME, D.FORNECEDOR_NOME_DETETADO) AS FORNECEDOR_NOME,
            D.DOCTEMPLATESTAMP,
            ISNULL(T.NOME, '') AS TEMPLATE_NOME,
            D.CONFIDENCE_SCORE,
            D.PROCESSING_STATUS,
            D.DTCRI,
            D.DTPROC
        FROM dbo.DOC_INBOX D
        LEFT JOIN dbo.FE FE
          ON CAST(FE.FEID AS int) = D.FEID
        LEFT JOIN dbo.FL F
          ON CAST(F.NO AS int) = D.FORNECEDOR_NO
        LEFT JOIN dbo.DOC_TEMPLATE T
          ON T.DOCTEMPLATESTAMP = D.DOCTEMPLATESTAMP
        {where_sql}
        ORDER BY D.DTCRI DESC
    """), params).mappings().all()

    items = []
    counts = {}
    for row in rows:
        status = str(row.get('PROCESSING_STATUS') or 'new').strip()
        counts[status] = counts.get(status, 0) + 1
        items.append({
            'id': str(row.get('DOCINSTAMP') or '').strip(),
            'file_name': str(row.get('FILE_NAME') or '').strip(),
            'file_path': str(row.get('FILE_PATH') or '').strip(),
            'file_ext': str(row.get('FILE_EXT') or '').strip(),
            'mime_type': str(row.get('MIME_TYPE') or '').strip(),
            'extraction_method': str(row.get('EXTRACTION_METHOD') or 'failed').strip() or 'failed',
            'extraction_quality_score': float(row.get('EXTRACTION_QUALITY_SCORE') or 0),
            'doc_type': str(row.get('DOC_TYPE_DETECTED') or 'unknown').strip() or 'unknown',
            'feid': _safe_int(row.get('FEID'), 0) or None,
            'entity_name': str(row.get('FE_NOME') or '').strip(),
            'entity_tax_id': _digits_only(row.get('FE_NIF')),
            'supplier_no': _safe_int(row.get('FORNECEDOR_NO'), 0) or None,
            'supplier_name': str(row.get('FORNECEDOR_NOME') or '').strip(),
            'template_id': str(row.get('DOCTEMPLATESTAMP') or '').strip(),
            'template_name': str(row.get('TEMPLATE_NOME') or '').strip(),
            'confidence': float(row.get('CONFIDENCE_SCORE') or 0),
            'status': status,
            'created_at': row.get('DTCRI').isoformat() if row.get('DTCRI') else None,
            'processed_at': row.get('DTPROC').isoformat() if row.get('DTPROC') else None,
        })

    return {'items': items, 'counts': counts, 'statuses': DOC_AI_STATUSES, 'doc_types': DOC_AI_DOC_TYPES}


def _serialize_document_source(source: DocSource) -> dict[str, Any]:
    folder = str(source.pasta or '').strip()
    resolved_folder = _resolve_document_source_folder(folder)
    return {
        'id': source.docsourcestamp,
        'name': source.nome or '',
        'folder': folder,
        'file_pattern': source.padrao_ficheiros or '',
        'include_subfolders': bool(source.subpastas),
        'active': bool(source.ativo),
        'interval_minutes': int(source.intervalo_minutos or 5),
        'last_run_at': source.ultima_execucao.isoformat() if source.ultima_execucao else None,
        'last_status': source.ultimo_estado or '',
        'last_message': source.ultima_mensagem or '',
        'folder_exists': bool(resolved_folder and os.path.isdir(resolved_folder)),
        'created_at': source.dtcri.isoformat() if source.dtcri else None,
        'updated_at': source.dtalt.isoformat() if source.dtalt else None,
        'created_by': source.usercriacao or '',
        'updated_by': source.useralteracao or '',
    }


def list_document_sources() -> dict[str, Any]:
    _ensure_document_sources_schema()
    rows = (
        DocSource.query
        .order_by(DocSource.ativo.desc(), DocSource.nome.asc())
        .all()
    )
    return {'items': [_serialize_document_source(row) for row in rows]}


def get_document_source(source_id: str) -> dict[str, Any]:
    _ensure_document_sources_schema()
    source = db.session.get(DocSource, str(source_id or '').strip())
    if not source:
        raise ValueError('Origem não encontrada.')
    return _serialize_document_source(source)


def _normalize_document_source_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    body = payload or {}
    name = str(body.get('name') or body.get('nome') or '').strip()
    folder = str(body.get('folder') or body.get('pasta') or '').strip()
    if not name:
        raise ValueError('Indique o nome da origem.')
    if not folder:
        raise ValueError('Indique a pasta da origem.')
    return {
        'name': name[:120],
        'folder': folder[:500],
        'file_pattern': str(body.get('file_pattern') or body.get('padrao_ficheiros') or '').strip()[:120],
        'include_subfolders': bool(body.get('include_subfolders') or body.get('subpastas')),
        'active': bool(body.get('active', body.get('ativo', True))),
        'interval_minutes': max(1, min(1440, _safe_int(body.get('interval_minutes') or body.get('intervalo_minutos'), 5))),
    }


def save_document_source(payload: dict[str, Any] | None, user_login: str, source_id: str = '') -> dict[str, Any]:
    _ensure_document_sources_schema()
    normalized = _normalize_document_source_payload(payload)
    source = db.session.get(DocSource, str(source_id or '').strip()) if source_id else None
    now = _now()
    user = str(user_login or '').strip()[:50]
    if source is None:
        source = DocSource(
            docsourcestamp=_new_stamp(),
            dtcri=now,
            usercriacao=user,
        )
        db.session.add(source)
    source.nome = normalized['name']
    source.pasta = normalized['folder']
    source.padrao_ficheiros = normalized['file_pattern']
    source.subpastas = normalized['include_subfolders']
    source.ativo = normalized['active']
    source.intervalo_minutos = normalized['interval_minutes']
    source.dtalt = now
    source.useralteracao = user
    db.session.commit()
    return _serialize_document_source(source)


def delete_document_source(source_id: str) -> dict[str, Any]:
    _ensure_document_sources_schema()
    source = db.session.get(DocSource, str(source_id or '').strip())
    if not source:
        raise ValueError('Origem não encontrada.')
    deleted_id = source.docsourcestamp
    db.session.delete(source)
    db.session.commit()
    return {'ok': True, 'id': deleted_id}


def _document_source_patterns(pattern_value: str | None) -> list[str]:
    patterns = [
        item.strip()
        for item in re.split(r'[;,]', str(pattern_value or '').strip())
        if item.strip()
    ]
    if patterns:
        return patterns
    return [f'*{ext}' for ext in sorted(DOC_AI_ALLOWED_UPLOAD_EXTENSIONS)]


def _document_source_file_matches(file_name: str, patterns: list[str]) -> bool:
    lower_name = str(file_name or '').lower()
    return any(fnmatch.fnmatch(lower_name, pattern.lower()) for pattern in patterns)


def _document_source_min_year() -> int:
    try:
        return max(1900, int(os.environ.get('DOCUMENT_AI_MIN_YEAR', '2026') or 2026))
    except Exception:
        return 2026


def _path_year_segments(base_folder: str, path_value: str) -> list[int]:
    try:
        relative_path = os.path.relpath(path_value, base_folder)
    except ValueError:
        relative_path = path_value
    years = []
    for part in re.split(r'[\\/]+', str(relative_path or '')):
        if re.fullmatch(r'(19|20)\d{2}', part or ''):
            years.append(int(part))
    return years


def _document_source_file_in_min_year(base_folder: str, file_path: str, min_year: int) -> bool:
    years = _path_year_segments(base_folder, file_path)
    if years:
        return max(years) >= min_year
    try:
        return datetime.fromtimestamp(os.path.getmtime(file_path)).year >= min_year
    except Exception:
        return True


def _normalize_source_path_for_match(path_value: str) -> str:
    return str(path_value or '').strip().replace('\\', '/').rstrip('/').lower()


def _document_source_path_mappings() -> list[tuple[str, str]]:
    raw_value = str(os.environ.get('DOCUMENT_AI_PATH_MAPS') or '').strip()
    mappings = []
    for item in re.split(r'[;\n]', raw_value):
        if '=' not in item:
            continue
        source_prefix, local_prefix = item.split('=', 1)
        source_prefix = source_prefix.strip()
        local_prefix = os.path.expanduser(local_prefix.strip())
        if source_prefix and local_prefix:
            mappings.append((source_prefix, local_prefix))
    return mappings


def _resolve_document_source_folder(folder_value: str) -> str:
    folder = os.path.expanduser(str(folder_value or '').strip())
    if not folder:
        return ''
    folder_slash = folder.replace('\\', '/').rstrip('/')
    normalized_folder = _normalize_source_path_for_match(folder)
    for source_prefix, local_prefix in _document_source_path_mappings():
        source_prefix_slash = source_prefix.replace('\\', '/').rstrip('/')
        normalized_prefix = _normalize_source_path_for_match(source_prefix)
        if not normalized_prefix:
            continue
        if normalized_folder == normalized_prefix or normalized_folder.startswith(f'{normalized_prefix}/'):
            suffix = folder_slash[len(source_prefix_slash):].lstrip('/')
            return os.path.abspath(os.path.join(local_prefix, *[part for part in suffix.split('/') if part]))
    return os.path.abspath(folder)


def _iter_document_source_files(source: DocSource, limit: int = 50) -> list[str]:
    folder = _resolve_document_source_folder(str(source.pasta or '').strip())
    if not os.path.isdir(folder):
        raise FileNotFoundError(f'Pasta não encontrada: {source.pasta}')
    current_app.logger.info(
        "Document AI robot: origem %s resolvida para %s.",
        source.nome or source.docsourcestamp,
        folder,
    )
    patterns = _document_source_patterns(source.padrao_ficheiros)
    matched_files = []
    max_files = max(1, int(limit or 50))
    min_year = _document_source_min_year()
    if source.subpastas:
        for root, dir_names, file_names in os.walk(folder):
            dir_names[:] = [
                dir_name
                for dir_name in dir_names
                if not (re.fullmatch(r'(19|20)\d{2}', dir_name or '') and int(dir_name) < min_year)
            ]
            for file_name in file_names:
                file_path = os.path.join(root, file_name)
                if (
                    _document_source_file_matches(file_name, patterns)
                    and _document_source_file_in_min_year(folder, file_path, min_year)
                ):
                    matched_files.append(file_path)
                    if len(matched_files) >= max_files:
                        return matched_files
    else:
        with os.scandir(folder) as entries:
            for entry in entries:
                if (
                    entry.is_file()
                    and _document_source_file_matches(entry.name, patterns)
                    and _document_source_file_in_min_year(folder, entry.path, min_year)
                ):
                    matched_files.append(entry.path)
                    if len(matched_files) >= max_files:
                        break
    return matched_files


def scan_document_source(source: DocSource, limit: int = 50, requested_by: str = 'document_ai_robot') -> dict[str, Any]:
    _ensure_document_sources_schema()
    stats = {
        'source_id': source.docsourcestamp,
        'source_name': source.nome or '',
        'found': 0,
        'imported': 0,
        'skipped': 0,
        'errors': 0,
        'items': [],
    }
    now = _now()
    try:
        current_app.logger.info(
            "Document AI robot: a analisar origem %s com ano mínimo %s.",
            source.nome or source.docsourcestamp,
            _document_source_min_year(),
        )
        file_paths = _iter_document_source_files(source, limit=limit)
        stats['found'] = len(file_paths)
        current_app.logger.info(
            "Document AI robot: origem %s devolveu %s ficheiro(s) candidato(s) neste ciclo.",
            source.nome or source.docsourcestamp,
            stats['found'],
        )
        for file_path in file_paths[:max(1, int(limit or 50))]:
            try:
                current_app.logger.info("Document AI robot: a importar %s.", file_path)
                payload = ingest_local_document_file(
                    file_path,
                    created_by=requested_by,
                    source_table='DOC_SOURCE',
                    source_recstamp=source.docsourcestamp,
                )
                if payload.get('skipped'):
                    stats['skipped'] += 1
                else:
                    stats['imported'] += 1
                stats['items'].append({
                    'path': file_path,
                    'id': payload.get('id'),
                    'skipped': bool(payload.get('skipped')),
                    'error': '',
                })
            except Exception as exc:
                stats['errors'] += 1
                stats['items'].append({
                    'path': file_path,
                    'id': '',
                    'skipped': False,
                    'error': str(exc),
                })
                try:
                    db.session.rollback()
                except Exception:
                    pass
        status = 'ok' if stats['errors'] == 0 else 'warning'
        message = f"{stats['imported']} importado(s), {stats['skipped']} duplicado(s), {stats['errors']} erro(s)."
    except Exception as exc:
        try:
            db.session.rollback()
        except Exception:
            pass
        stats['errors'] += 1
        status = 'error'
        message = str(exc)

    fresh_source = db.session.get(DocSource, source.docsourcestamp)
    if fresh_source:
        fresh_source.ultima_execucao = now
        fresh_source.ultimo_estado = status
        fresh_source.ultima_mensagem = message[:500]
        fresh_source.dtalt = _now()
        fresh_source.useralteracao = requested_by[:50]
        db.session.commit()
    stats['status'] = status
    stats['message'] = message
    return stats


def scan_document_sources(source_id: str = '', limit_per_source: int = 50, requested_by: str = 'document_ai_robot') -> dict[str, Any]:
    _ensure_document_sources_schema()
    query = DocSource.query.filter_by(ativo=True)
    if str(source_id or '').strip():
        query = query.filter_by(docsourcestamp=str(source_id or '').strip())
    sources = query.order_by(DocSource.nome.asc()).all()
    current_app.logger.info("Document AI robot: %s origem(ns) ativa(s) encontrada(s).", len(sources))
    results = [scan_document_source(source, limit=limit_per_source, requested_by=requested_by) for source in sources]
    return {
        'ok': True,
        'sources': len(results),
        'found': sum(int(item.get('found') or 0) for item in results),
        'imported': sum(int(item.get('imported') or 0) for item in results),
        'skipped': sum(int(item.get('skipped') or 0) for item in results),
        'errors': sum(int(item.get('errors') or 0) for item in results),
        'results': results,
    }


def _serialize_document(document: DocInbox, include_logs: bool = False) -> dict[str, Any]:
    template = db.session.get(DocTemplate, document.doctemplatestamp) if document.doctemplatestamp else None
    parser = db.session.get(DocParser, document.docparserstamp) if document.docparserstamp else None
    supplier_name = ''
    if document.fornecedor_no:
        feid_filter = _fl_feid_filter_sql('FL') if document.feid else ''
        row = db.session.execute(text("""
            SELECT TOP 1 LTRIM(RTRIM(ISNULL(NOME, ''))) AS NOME
            FROM dbo.FL FL
            WHERE CAST(FL.NO AS int) = :no
            {feid_filter}
        """.format(feid_filter=feid_filter)), {
            'no': document.fornecedor_no,
            'feid': int(document.feid or 0),
        }).mappings().first()
        supplier_name = str((row or {}).get('NOME') or '').strip()
    customer_entity = {}
    if document.feid:
        row = db.session.execute(text("""
            SELECT TOP 1
                CAST(ISNULL(FEID, 0) AS int) AS FEID,
                LTRIM(RTRIM(ISNULL(NOME, ''))) AS NOME,
                LTRIM(RTRIM(ISNULL(NOMEFISCAL, ''))) AS NOMEFISCAL,
                LTRIM(RTRIM(CAST(ISNULL(NIF, 0) AS varchar(40)))) AS NIF
            FROM dbo.FE
            WHERE CAST(ISNULL(FEID, 0) AS int) = :feid
        """), {'feid': int(document.feid or 0)}).mappings().first()
        customer_entity = _serialize_fe_row(dict(row), 1, 'stored') if row else {}

    payload = {
        'id': document.docinstamp,
        'feid': document.feid,
        'entity': customer_entity,
        'anexosstamp': document.anexosstamp or '',
        'source_table': document.source_table or '',
        'source_recstamp': document.source_recstamp or '',
        'file_name': document.file_name or '',
        'file_path': document.file_path or '',
        'file_ext': document.file_ext or '',
        'mime_type': document.mime_type or '',
        'file_hash': document.file_hash or '',
        'file_size': int(document.file_size or 0),
        'extracted_text': document.extracted_text or '',
        'extraction_method': document.extraction_method or 'failed',
        'extraction_quality_score': float(document.extraction_quality_score or 0),
        'extraction_notes': _json_loads(document.extraction_notes_json, {}),
        'preprocessed_image_path': document.preprocessed_image_path or '',
        'ocr_raw_json': _json_loads(document.ocr_raw_json, {}),
        'text_blocks': _json_loads(document.text_blocks_json, []),
        'processing_stage': document.processing_stage or 'new',
        'last_processing_error': document.last_processing_error or '',
        'doc_type': document.doc_type_detected or 'unknown',
        'supplier_no': document.fornecedor_no,
        'supplier_name_detected': document.fornecedor_nome_detetado or supplier_name or '',
        'supplier_tax_id_detected': document.fornecedor_nif_detetado or '',
        'template': _serialize_template(template, include_definition=True) if template else None,
        'parser': _serialize_parser(parser),
        'parser_version': document.parser_version or '',
        'confidence': float(document.confidence_score or 0),
        'status': document.processing_status or 'new',
        'result': _json_loads(document.json_resultado, canonical_result_base(document.doc_type_detected or 'unknown')),
        'warnings': _json_loads(document.warnings_json, []),
        'errors': _json_loads(document.errors_json, []),
        'processing_meta': _json_loads(document.processing_meta_json, {}),
        'created_at': document.dtcri.isoformat() if document.dtcri else None,
        'updated_at': document.dtalt.isoformat() if document.dtalt else None,
        'processed_at': document.dtproc.isoformat() if document.dtproc else None,
        'created_by': document.usercriacao or '',
        'updated_by': document.useralteracao or '',
        'supplier_name': supplier_name or document.fornecedor_nome_detetado or '',
    }
    if include_logs:
        logs = (
            DocProcessLog.query
            .filter_by(docinstamp=document.docinstamp)
            .order_by(DocProcessLog.dtcri.desc())
            .all()
        )
        payload['logs'] = [
            {
                'id': log.docprocesslogstamp,
                'phase': log.fase,
                'status': log.status,
                'message': log.mensagem,
                'detail': _json_loads(log.detalhe_json, {}),
                'created_at': log.dtcri.isoformat() if log.dtcri else None,
            }
            for log in logs
        ]
    return payload


def _build_template_draft(document_payload: dict[str, Any]) -> dict[str, Any]:
    result = document_payload.get('result') or canonical_result_base(document_payload.get('doc_type'))
    supplier_no = document_payload.get('supplier_no')
    default_name = _default_template_name(
        document_payload.get('feid'),
        supplier_no,
        document_payload.get('doc_type') or 'unknown',
    )
    fields = []
    for key, base_config in DOC_AI_GENERIC_FIELD_CONFIGS.items():
        existing_value = None
        if key == 'document_number':
            existing_value = result.get('document_number')
        elif key == 'document_date':
            existing_value = result.get('document_date')
        elif key == 'currency':
            existing_value = result.get('currency')
        elif key == 'supplier_tax_id':
            existing_value = result.get('supplier', {}).get('tax_id')
        elif key == 'supplier_name':
            existing_value = result.get('supplier', {}).get('name')
        elif key == 'customer_tax_id':
            existing_value = result.get('customer', {}).get('tax_id')
        elif key == 'customer_name':
            existing_value = result.get('customer', {}).get('name')
        elif key == 'gross_total':
            existing_value = result.get('totals', {}).get('gross_total')
        elif key == 'net_total':
            existing_value = result.get('totals', {}).get('net_total')
        elif key == 'tax_total':
            existing_value = result.get('totals', {}).get('tax_total')
        fields.append({
            'field_key': key,
            'label': base_config.get('label') or key,
            'order': len(fields) + 1,
            'required': key in ('document_number', 'document_date', 'gross_total'),
            'match_mode': 'anchor_regex',
            'anchors': list(base_config.get('anchors') or []),
            'regex': base_config.get('regex') or '',
            'aliases': [],
            'postprocess': base_config.get('postprocess') or '',
            'config': {'sample_value': existing_value},
            'active': True,
        })
    return {
        'name': default_name or 'Novo template',
        'description': 'Template sugerido a partir do documento atual.',
        'feid': document_payload.get('feid'),
        'supplier_no': supplier_no,
        'doc_type': document_payload.get('doc_type') or 'unknown',
        'language': '',
        'fingerprint': '',
        'score_min_match': 0.55,
        'match_rules': {'keywords': [], 'required': [], 'forbidden': []},
        'lines': DOC_AI_DEFAULT_LINE_RULES,
        'fields': fields,
        'definition_json': {
            'doc_type': document_payload.get('doc_type') or 'unknown',
            'match': {'keywords': [], 'required': [], 'forbidden': []},
            'fields': {
                item['field_key']: {
                    'anchors': item['anchors'],
                    'regex': item['regex'],
                    'aliases': item['aliases'],
                    'required': item['required'],
                    'postprocess': item['postprocess'],
                    'config': item['config'],
                }
                for item in fields
            },
            'lines': DOC_AI_DEFAULT_LINE_RULES,
        },
    }


def get_document_detail(document_stamp: str) -> dict[str, Any]:
    _ensure_document_ai_schema()
    document = db.session.get(DocInbox, str(document_stamp or '').strip())
    if not document:
        raise ValueError('Documento não encontrado.')
    payload = _serialize_document(document, include_logs=True)
    preview_blocks, preview_pages = _document_preview_payload(document, payload.get('text_blocks') or [])
    payload['text_blocks'] = preview_blocks
    payload['preview'] = {
        'type': 'pdf' if _is_pdf(document.file_ext, document.mime_type) else ('image' if _is_image(document.file_ext, document.mime_type) else 'file'),
        'page_count': len(preview_pages) or 1,
        'pages': preview_pages,
        'supports_highlight': any(block.get('left') is not None and block.get('top') is not None for block in preview_blocks),
    }
    payload['available_templates'] = [
        _serialize_template(item, include_definition=False)
        for item in _load_template_candidates(payload.get('supplier_no'), payload.get('doc_type'), payload.get('feid'))
    ]
    payload['template_draft'] = _build_template_draft(payload)
    payload['llm'] = {'available': llm_suggestions_available()}
    return payload


def get_document_preview_page(document_stamp: str, page_number: int = 1) -> dict[str, Any]:
    _ensure_document_ai_schema()
    document = db.session.get(DocInbox, str(document_stamp or '').strip())
    if not document:
        raise ValueError('Documento não encontrado.')

    absolute_path = _document_absolute_path(document)
    if not os.path.isfile(absolute_path):
        raise FileNotFoundError('Ficheiro original não encontrado.')

    if _is_pdf(document.file_ext, document.mime_type):
        if not importlib.util.find_spec('fitz'):
            raise RuntimeError('Preview PDF indisponível: fitz não está instalado.')
        import fitz  # type: ignore

        with fitz.open(absolute_path) as pdf:
            page_index = max(0, min(int(page_number or 1) - 1, len(pdf) - 1))
            page = pdf[page_index]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            return {
                'kind': 'bytes',
                'data': pix.tobytes('png'),
                'mime_type': 'image/png',
                'file_name': f'{document.docinstamp}-p{page_index + 1}.png',
            }

    return {
        'kind': 'file',
        'path': absolute_path,
        'mime_type': document.mime_type or mimetypes.guess_type(absolute_path)[0] or 'application/octet-stream',
        'file_name': document.file_name or os.path.basename(absolute_path),
    }


def get_document_original_file(document_stamp: str) -> dict[str, Any]:
    _ensure_document_ai_schema()
    document = db.session.get(DocInbox, str(document_stamp or '').strip())
    if not document:
        raise ValueError('Documento não encontrado.')
    absolute_path = _document_absolute_path(document)
    if not os.path.isfile(absolute_path):
        raise FileNotFoundError('Ficheiro original não encontrado.')
    return {
        'path': absolute_path,
        'mime_type': document.mime_type or mimetypes.guess_type(absolute_path)[0] or 'application/octet-stream',
        'file_name': document.file_name or os.path.basename(absolute_path),
    }


def _safe_document_file_path(path_value: str | None) -> str:
    raw = str(path_value or '').strip()
    if not raw:
        return ''
    absolute_path = _document_local_path(raw)
    root_path = _document_storage_root()
    app_root_path = os.path.abspath(current_app.root_path)
    if absolute_path != root_path and absolute_path.startswith(root_path + os.sep):
        return absolute_path
    if absolute_path != app_root_path and absolute_path.startswith(app_root_path + os.sep):
        return absolute_path
    return ''


def delete_document_from_inbox(document_stamp: str, deleted_by: str = '') -> dict[str, Any]:
    _ensure_document_ai_schema()
    stamp = str(document_stamp or '').strip()
    document = db.session.get(DocInbox, stamp)
    if not document:
        raise ValueError('Documento não encontrado.')

    paths_to_delete = [
        _safe_document_file_path(document.file_path),
        _safe_document_file_path(document.preprocessed_image_path),
    ]
    original_name = document.file_name or ''
    anexo_stamp = str(document.anexosstamp or '').strip()

    DocProcessLog.query.filter_by(docinstamp=document.docinstamp).delete(synchronize_session=False)
    if anexo_stamp:
        db.session.execute(text("""
            DELETE FROM dbo.ANEXOS
            WHERE ANEXOSSTAMP = :anexo_stamp
               OR (TABELA = 'DOC_INBOX' AND RECSTAMP = :docinstamp)
        """), {
            'anexo_stamp': anexo_stamp,
            'docinstamp': document.docinstamp,
        })
    else:
        db.session.execute(text("""
            DELETE FROM dbo.ANEXOS
            WHERE TABELA = 'DOC_INBOX' AND RECSTAMP = :docinstamp
        """), {'docinstamp': document.docinstamp})
    db.session.delete(document)
    db.session.commit()

    removed_files = []
    for file_path in {path for path in paths_to_delete if path}:
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
                removed_files.append(file_path)
        except Exception:
            current_app.logger.warning(
                'Nao foi possivel remover ficheiro documental %s por %s',
                file_path,
                deleted_by or 'unknown',
                exc_info=True,
            )

    return {
        'ok': True,
        'id': stamp,
        'file_name': original_name,
        'removed_files': len(removed_files),
    }


def _store_file(uploaded_file, folder_name: str = 'document_ai') -> dict[str, Any]:
    original_name = str(getattr(uploaded_file, 'filename', '') or '').strip()
    _, ext = os.path.splitext(original_name)
    ext = ext.lower().strip()
    if ext not in DOC_AI_ALLOWED_UPLOAD_EXTENSIONS:
        raise ValueError(f'Extensão {ext or "(sem extensão)"} não suportada.')
    stamp = _new_stamp()
    safe_name = f'{stamp}{ext}'
    relative_dir = os.path.join('static', 'images', folder_name)
    absolute_dir = os.path.join(_document_storage_root(), relative_dir)
    os.makedirs(absolute_dir, exist_ok=True)
    absolute_path = os.path.join(absolute_dir, safe_name)
    uploaded_file.save(absolute_path)
    return {
        'original_name': original_name,
        'file_name': safe_name,
        'absolute_path': absolute_path,
        'public_path': f'/{relative_dir.replace(os.sep, "/")}/{safe_name}',
        'file_ext': ext,
        'mime_type': _guess_mime_type(original_name),
        'size': os.path.getsize(absolute_path),
        'hash': _file_hash(absolute_path),
    }


def _store_local_file(source_path: str, folder_name: str = 'document_ai') -> dict[str, Any]:
    absolute_source = os.path.abspath(os.path.expanduser(str(source_path or '').strip()))
    if not os.path.isfile(absolute_source):
        raise FileNotFoundError(f'Ficheiro não encontrado: {source_path}')
    original_name = os.path.basename(absolute_source)
    _, ext = os.path.splitext(original_name)
    ext = ext.lower().strip()
    if ext not in DOC_AI_ALLOWED_UPLOAD_EXTENSIONS:
        raise ValueError(f'Extensão {ext or "(sem extensão)"} não suportada.')
    stamp = _new_stamp()
    safe_name = f'{stamp}{ext}'
    relative_dir = os.path.join('static', 'images', folder_name)
    absolute_dir = os.path.join(_document_storage_root(), relative_dir)
    os.makedirs(absolute_dir, exist_ok=True)
    absolute_path = os.path.join(absolute_dir, safe_name)
    shutil.copy2(absolute_source, absolute_path)
    return {
        'original_name': original_name,
        'file_name': safe_name,
        'absolute_path': absolute_path,
        'public_path': f'/{relative_dir.replace(os.sep, "/")}/{safe_name}',
        'file_ext': ext,
        'mime_type': _guess_mime_type(original_name),
        'size': os.path.getsize(absolute_path),
        'hash': _file_hash(absolute_path),
        'source_path': absolute_source,
    }


def process_document(
    document_stamp: str,
    requested_by: str = '',
    forced_template_stamp: str = '',
    reprocess_mode: str = 'auto',
    manual_adjustments: dict[str, Any] | None = None,
    working_template_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _ensure_document_ai_schema()
    _ensure_default_parser()
    document = db.session.get(DocInbox, str(document_stamp or '').strip())
    if not document:
        raise ValueError('Documento não encontrado.')

    logs_before = DocProcessLog.query.filter_by(docinstamp=document.docinstamp).all()
    for item in logs_before:
        db.session.delete(item)
    db.session.flush()

    _document_log(document.docinstamp, 'ingest', 'info', 'Início do processamento documental.', {
        'file_name': document.file_name,
        'requested_by': requested_by,
        'reprocess_mode': reprocess_mode,
        'manual_adjustments': manual_adjustments or {},
    })

    try:
        document.processing_stage = 'extract_text'
        document.last_processing_error = ''
        extraction = extract_document_text(
            _document_absolute_path(document),
            document.file_ext,
            document.mime_type,
            document_stamp=document.docinstamp,
            force_mode=reprocess_mode,
            manual_adjustments=manual_adjustments,
        )
        document.extracted_text = str(extraction.get('text') or '').strip()
        document.extraction_method = str(extraction.get('method') or 'failed').strip() or 'failed'
        document.extraction_quality_score = float((extraction.get('quality') or {}).get('score') or 0)
        document.extraction_notes_json = _json_dumps(extraction.get('notes') or {})
        document.preprocessed_image_path = str(extraction.get('preprocessed_image_path') or '').strip() or None
        document.ocr_raw_json = _json_dumps(extraction.get('raw_json') or {})
        document.text_blocks_json = _json_dumps(extraction.get('blocks') or [])
        document.processing_stage = 'text_extracted'

        _document_log(document.docinstamp, 'extract_text', 'ok' if extraction.get('ok') else 'warning', 'Extração textual concluída.', {
            'warnings': extraction.get('warnings') or [],
            'engine': extraction.get('engine'),
            'method': document.extraction_method,
            'quality': extraction.get('quality') or {},
            'fallback_used': bool(extraction.get('fallback_used')),
        })

        if not document.extracted_text:
            document.confidence_score = 0
            document.processing_status = 'parse_error'
            document.doc_type_detected = 'unknown'
            document.json_resultado = _json_dumps(canonical_result_base('unknown'))
            document.warnings_json = _json_dumps(extraction.get('warnings') or [])
            document.errors_json = _json_dumps(['Não foi possível extrair texto utilizável do documento.'])
            document.processing_meta_json = _json_dumps({
                'extraction': {
                    'method': document.extraction_method,
                    'quality_score': float(document.extraction_quality_score or 0),
                    'notes': _json_loads(document.extraction_notes_json, {}),
                    'preprocessed_image_path': document.preprocessed_image_path or '',
                    'fallback_used': bool(extraction.get('fallback_used')),
                },
                'ocr_available': ocr_engine_available(),
            })
            document.processing_stage = 'failed'
            document.last_processing_error = 'text_extraction_failed'
            document.dtproc = _now()
            document.dtalt = _now()
            document.useralteracao = requested_by or document.useralteracao or document.usercriacao
            db.session.commit()
            return get_document_detail(document.docinstamp)

        customer_match = identify_fe_entity_from_text(document.extracted_text or '')
        if customer_match.get('feid'):
            document.feid = customer_match.get('feid')
        _document_log(document.docinstamp, 'customer_detect', 'ok' if customer_match.get('feid') else 'warning', 'Entidade FE analisada.', customer_match)

        document.processing_stage = 'supplier_detect'
        supplier_match = identify_supplier_from_text(document.extracted_text or '', document.feid)
        document.fornecedor_no = supplier_match.get('supplier_no')
        document.fornecedor_nif_detetado = supplier_match.get('supplier_tax_id') or ''
        document.fornecedor_nome_detetado = supplier_match.get('supplier_name') or ''
        _document_log(document.docinstamp, 'supplier_detect', 'ok' if supplier_match.get('supplier_no') else 'warning', 'Fornecedor analisado.', supplier_match)

        document.processing_stage = 'template_match'
        pre_template_doc_type = classify_document_type(document.extracted_text or '', supplier_match, None)
        runtime_template = _build_runtime_template_payload(working_template_payload, requested_by) if working_template_payload else None
        template_match = None
        if forced_template_stamp:
            forced_template = db.session.get(DocTemplate, str(forced_template_stamp or '').strip())
            if forced_template and forced_template.ativo:
                template_match = {
                    'template': forced_template,
                    'score': 0.99,
                    'reasons': ['forced'],
                    'doc_type': forced_template.doc_type or pre_template_doc_type.get('doc_type') or 'unknown',
                }
        if not template_match and runtime_template:
            template_match = {
                'template': runtime_template,
                'score': 0.99,
                'reasons': ['working_template'],
                'doc_type': runtime_template.get('doc_type') or pre_template_doc_type.get('doc_type') or 'unknown',
            }
        if not template_match:
            template_match = _choose_best_template(
                document.extracted_text or '',
                supplier_match.get('supplier_no'),
                pre_template_doc_type.get('doc_type') or 'unknown',
                document.feid,
            )
        _document_log(document.docinstamp, 'template_match', 'ok' if template_match else 'warning', 'Template selecionado.' if template_match else 'Sem template válido.', {
            'template_id': (
                str((template_match.get('template') or {}).get('id') or '').strip()
                if template_match and isinstance(template_match.get('template'), dict)
                else (template_match['template'].doctemplatestamp if template_match else '')
            ),
            'score': template_match.get('score') if template_match else 0,
            'reasons': template_match.get('reasons') if template_match else [],
        })

        document.processing_stage = 'parse'
        doc_type_info = classify_document_type(document.extracted_text or '', supplier_match, template_match)
        document.doc_type_detected = doc_type_info.get('doc_type') or 'unknown'
        _document_log(document.docinstamp, 'doc_type_detect', 'ok', 'Tipo documental classificado.', doc_type_info)

        template_payload = None
        if template_match:
            template = template_match.get('template')
            if isinstance(template, dict):
                document.doctemplatestamp = str(template.get('id') or '').strip() or None
                document.docparserstamp = str(template.get('parser_id') or '').strip()
                document.parser_version = str(template.get('parser_version') or '').strip()
                template_payload = {
                    'template': template,
                    'definition': template.get('definition') or {},
                }
            else:
                document.doctemplatestamp = template.doctemplatestamp
                document.docparserstamp = template.docparserstamp or ''
                document.parser_version = template.parser_version or ''
                template_payload = {
                    'template': _serialize_template(template, include_definition=True),
                    'definition': _template_definition_payload(template),
                }
        else:
            default_parser = _ensure_default_parser()
            document.doctemplatestamp = None
            document.docparserstamp = default_parser.docparserstamp
            document.parser_version = default_parser.versao

        parse_payload = _execute_template_parse(
            document.extracted_text or '',
            _json_loads(document.text_blocks_json, []),
            template_payload,
            supplier_match,
            doc_type_info,
        )
        validation = _validate_parse_result(parse_payload, template_match)

        result_payload = parse_payload.get('result') or canonical_result_base(document.doc_type_detected or 'unknown')
        result_payload['document_type'] = document.doc_type_detected or 'unknown'
        if supplier_match.get('supplier_no') and not result_payload['supplier'].get('supplier_no'):
            result_payload['supplier']['supplier_no'] = supplier_match.get('supplier_no')
        if supplier_match.get('supplier_tax_id') and not result_payload['supplier'].get('tax_id'):
            result_payload['supplier']['tax_id'] = supplier_match.get('supplier_tax_id')
        if supplier_match.get('supplier_name') and not result_payload['supplier'].get('name'):
            result_payload['supplier']['name'] = supplier_match.get('supplier_name')
        if customer_match.get('feid'):
            result_payload.setdefault('customer', {})
            result_payload['customer']['feid'] = customer_match.get('feid')
            if customer_match.get('tax_id') and not result_payload['customer'].get('tax_id'):
                result_payload['customer']['tax_id'] = customer_match.get('tax_id')
            if customer_match.get('name') and not result_payload['customer'].get('name'):
                result_payload['customer']['name'] = customer_match.get('name')

        confidence_parts = [
            float(supplier_match.get('score') or 0),
            float(doc_type_info.get('score') or 0),
            float(parse_payload.get('confidence') or 0),
            float(template_match.get('score') or 0) if template_match else 0,
            float(document.extraction_quality_score or 0),
        ]
        populated_parts = [item for item in confidence_parts if item > 0]
        overall_confidence = round(sum(populated_parts) / max(len(populated_parts), 1), 4)

        document.confidence_score = overall_confidence
        document.processing_status = validation.get('status') or 'review_required'
        document.json_resultado = _json_dumps(result_payload)
        document.warnings_json = _json_dumps(validation.get('warnings') or [])
        document.errors_json = _json_dumps(validation.get('errors') or [])
        document.processing_meta_json = _json_dumps({
            'supplier_match': supplier_match,
            'customer_match': customer_match,
            'doc_type': doc_type_info,
            'template_match': {
                'template_id': (
                    str((template_match.get('template') or {}).get('id') or '').strip()
                    if template_match and isinstance(template_match.get('template'), dict)
                    else template_match['template'].doctemplatestamp
                ),
                'score': template_match.get('score'),
                'reasons': template_match.get('reasons'),
            } if template_match else {},
            'extraction': {
                'engine': extraction.get('engine'),
                'method': document.extraction_method,
                'quality_score': float(document.extraction_quality_score or 0),
                'notes': _json_loads(document.extraction_notes_json, {}),
                'preprocessed_image_path': document.preprocessed_image_path or '',
                'fallback_used': bool(extraction.get('fallback_used')),
                'reprocess_mode': reprocess_mode,
            },
            'ocr_available': ocr_engine_available(),
        })
        document.processing_stage = 'completed'
        document.last_processing_error = ''
        document.dtproc = _now()
        document.dtalt = _now()
        document.useralteracao = requested_by or document.useralteracao or document.usercriacao

        _document_log(document.docinstamp, 'parse', 'ok' if validation.get('status') != 'parse_error' else 'error', 'Parsing concluído.', {
            'status': validation.get('status'),
            'confidence': overall_confidence,
            'warnings': validation.get('warnings'),
            'errors': validation.get('errors'),
            'extraction_method': document.extraction_method,
        })

        db.session.commit()
        payload = get_document_detail(document.docinstamp)
        if runtime_template:
            payload['template_draft'] = runtime_template
        return payload
    except Exception as exc:
        current_app.logger.exception('Erro no processamento documental')
        db.session.rollback()
        document = db.session.get(DocInbox, str(document_stamp or '').strip())
        if document:
            document.processing_status = 'parse_error'
            document.processing_stage = 'failed'
            document.last_processing_error = str(exc)
            document.dtproc = _now()
            document.dtalt = _now()
            document.useralteracao = requested_by or document.useralteracao or document.usercriacao
            _document_log(document.docinstamp, 'parse', 'error', 'Falha no processamento documental.', {'error': str(exc)})
            db.session.commit()
        raise


def ingest_uploaded_document(uploaded_file, created_by: str, source_table: str = '', source_recstamp: str = '') -> dict[str, Any]:
    _ensure_document_ai_schema()
    stored = _store_file(uploaded_file)
    return _create_inbox_document_from_stored_file(stored, created_by, source_table, source_recstamp)


def _create_inbox_document_from_stored_file(
    stored: dict[str, Any],
    created_by: str,
    source_table: str = '',
    source_recstamp: str = '',
) -> dict[str, Any]:
    try:
        feid = get_current_feid(db.session)
    except (MissingCurrentEntityError, Exception):
        feid = None

    document = DocInbox(
        docinstamp=_new_stamp(),
        feid=feid,
        source_table=str(source_table or '').strip() or None,
        source_recstamp=str(source_recstamp or '').strip() or None,
        file_name=stored['original_name'],
        file_path=stored['public_path'],
        file_ext=stored['file_ext'],
        mime_type=stored['mime_type'],
        file_hash=stored['hash'],
        file_size=stored['size'],
        doc_type_detected='unknown',
        confidence_score=0,
        processing_status='new',
        extracted_text='',
        extraction_method='failed',
        extraction_quality_score=0,
        extraction_notes_json='{}',
        preprocessed_image_path=None,
        ocr_raw_json='{}',
        text_blocks_json='[]',
        processing_stage='new',
        last_processing_error='',
        json_resultado=_json_dumps(canonical_result_base('unknown')),
        warnings_json='[]',
        errors_json='[]',
        processing_meta_json='{}',
        dtcri=_now(),
        dtalt=_now(),
        usercriacao=created_by or '',
        useralteracao=created_by or '',
    )
    db.session.add(document)
    db.session.flush()

    anexo_stamp = _new_stamp()
    db.session.execute(text("""
        INSERT INTO dbo.ANEXOS
            (ANEXOSSTAMP, TABELA, RECSTAMP, DESCRICAO, FICHEIRO, CAMINHO, TIPO, DATA, UTILIZADOR)
        VALUES
            (:stamp, :table_name, :recstamp, :descricao, :file_name, :caminho, :tipo, :data, :utilizador)
    """), {
        'stamp': anexo_stamp,
        'table_name': 'DOC_INBOX',
        'recstamp': document.docinstamp,
        'descricao': 'Documento compra',
        'file_name': stored['original_name'],
        'caminho': stored['public_path'],
        'tipo': stored['file_ext'].lstrip('.'),
        'data': date.today(),
        'utilizador': created_by or '',
    })
    document.anexosstamp = anexo_stamp
    db.session.commit()
    return process_document(document.docinstamp, requested_by=created_by or '')


def ingest_local_document_file(
    file_path: str,
    created_by: str = 'document_ai_robot',
    source_table: str = 'DOC_SOURCE',
    source_recstamp: str = '',
) -> dict[str, Any]:
    _ensure_document_ai_schema()
    absolute_path = os.path.abspath(os.path.expanduser(str(file_path or '').strip()))
    file_hash = _file_hash(absolute_path)
    existing = DocInbox.query.filter_by(file_hash=file_hash).first()
    if existing:
        return {
            'ok': True,
            'skipped': True,
            'reason': 'duplicate_hash',
            'id': existing.docinstamp,
            'file_name': existing.file_name or os.path.basename(absolute_path),
            'source_path': absolute_path,
        }
    stored = _store_local_file(absolute_path)
    return _create_inbox_document_from_stored_file(stored, created_by, source_table, source_recstamp)


def reprocess_document(
    document_stamp: str,
    requested_by: str,
    forced_template_stamp: str = '',
    reprocess_mode: str = 'auto',
    manual_adjustments: dict[str, Any] | None = None,
    working_template_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return process_document(
        document_stamp,
        requested_by=requested_by,
        forced_template_stamp=forced_template_stamp,
        reprocess_mode=reprocess_mode,
        manual_adjustments=manual_adjustments,
        working_template_payload=working_template_payload,
    )


def _build_runtime_template_payload(payload: dict[str, Any] | None, requested_by: str = '') -> dict[str, Any] | None:
    if not isinstance(payload, dict) or not payload:
        return None
    normalized = _normalize_template_payload(payload, requested_by or '')
    definition = _json_loads(normalized.get('definition_json'), {})
    match_rules = _json_loads(normalized.get('match_rules_json'), {})
    parser = db.session.get(DocParser, normalized.get('parser_id')) if normalized.get('parser_id') else None
    runtime_template = {
        'id': str(payload.get('id') or '').strip(),
        'name': normalized.get('name') or 'Template runtime',
        'description': normalized.get('description') or '',
        'feid': normalized.get('feid'),
        'supplier_no': normalized.get('supplier_no'),
        'supplier_name': '',
        'doc_type': normalized.get('doc_type') or 'unknown',
        'language': normalized.get('language') or '',
        'fingerprint': normalized.get('fingerprint') or '',
        'score_min_match': float(normalized.get('score_min_match') or 0.55),
        'parser': _serialize_parser(parser),
        'parser_id': normalized.get('parser_id') or '',
        'parser_version': normalized.get('parser_version') or '',
        'active': bool(normalized.get('active', True)),
        'match_rules': match_rules,
        'definition': definition,
        'fields': [],
        'lines': definition.get('lines') or {},
    }
    runtime_template['fields'] = [
        {
            'id': '',
            'field_key': item.get('field_key') or '',
            'label': item.get('label') or item.get('field_key') or '',
            'order': item.get('order') or (idx + 1),
            'required': bool(item.get('required')),
            'match_mode': item.get('match_mode') or 'anchor_regex',
            'anchors': list(item.get('anchors') or []),
            'regex': item.get('regex') or '',
            'aliases': list(item.get('aliases') or []),
            'postprocess': item.get('postprocess') or '',
            'config': item.get('config') or {},
            'active': bool(item.get('active', True)),
        }
        for idx, item in enumerate(normalized.get('fields') or [])
    ]
    return runtime_template


def save_document_review(document_stamp: str, payload: dict[str, Any], requested_by: str) -> dict[str, Any]:
    _ensure_document_ai_schema()
    document = db.session.get(DocInbox, str(document_stamp or '').strip())
    if not document:
        raise ValueError('Documento não encontrado.')

    result = payload.get('result') or {}
    warnings = payload.get('warnings') or []
    errors = payload.get('errors') or []
    processing_status = str(payload.get('status') or '').strip() or 'review_required'
    doc_type = str(payload.get('doc_type') or result.get('document_type') or document.doc_type_detected or 'unknown').strip() or 'unknown'
    supplier_no = payload.get('supplier_no')
    template_id = str(payload.get('template_id') or '').strip()

    if supplier_no not in (None, ''):
        document.fornecedor_no = _safe_int(supplier_no, 0) or None
    customer_payload = result.get('customer') or {}
    customer_feid = _safe_int(payload.get('feid') or customer_payload.get('feid'), 0)
    if not customer_feid:
        customer_match = resolve_fe_entity(customer_payload.get('tax_id') or customer_payload.get('name') or '')
        customer_feid = _safe_int(customer_match.get('feid'), 0)
        if customer_match:
            customer_payload['feid'] = customer_feid
            customer_payload['name'] = customer_payload.get('name') or customer_match.get('name') or ''
            customer_payload['tax_id'] = customer_payload.get('tax_id') or customer_match.get('tax_id') or ''
            result['customer'] = customer_payload
    if customer_feid:
        document.feid = customer_feid
    document.doc_type_detected = doc_type
    document.doctemplatestamp = template_id or None
    document.json_resultado = _json_dumps(result or canonical_result_base(doc_type))
    document.warnings_json = _json_dumps(warnings)
    document.errors_json = _json_dumps(errors)
    document.processing_status = processing_status
    document.confidence_score = float(payload.get('confidence') or document.confidence_score or 0)
    document.dtalt = _now()
    document.dtproc = _now()
    document.useralteracao = requested_by or document.useralteracao

    _document_log(document.docinstamp, 'review', 'ok', 'Validação humana gravada.', {
        'status': processing_status,
        'template_id': template_id,
        'supplier_no': document.fornecedor_no,
        'feid': document.feid,
    })
    db.session.commit()
    return get_document_detail(document.docinstamp)


def _normalize_template_payload(payload: dict[str, Any], requested_by: str) -> dict[str, Any]:
    parser_id = str(payload.get('parser_id') or '').strip()
    parser = db.session.get(DocParser, parser_id) if parser_id else _ensure_default_parser()
    if not parser:
        parser = _ensure_default_parser()

    fields = []
    raw_fields = payload.get('fields') or []
    if isinstance(raw_fields, dict):
        raw_fields = list(raw_fields.values())
    for idx, raw_field in enumerate(raw_fields, start=1):
        if not isinstance(raw_field, dict):
            continue
        field_key = str(raw_field.get('field_key') or '').strip()
        if not field_key:
            continue
        anchors = raw_field.get('anchors') or []
        aliases = raw_field.get('aliases') or []
        field_payload = {
            'field_key': field_key,
            'label': str(raw_field.get('label') or field_key).strip(),
            'order': _safe_int(raw_field.get('order'), idx),
            'required': bool(raw_field.get('required')),
            'match_mode': str(raw_field.get('match_mode') or 'anchor_regex').strip(),
            'anchors': [str(item or '').strip() for item in anchors if str(item or '').strip()],
            'regex': str(raw_field.get('regex') or '').strip(),
            'aliases': [str(item or '').strip() for item in aliases if str(item or '').strip()],
            'postprocess': str(raw_field.get('postprocess') or '').strip(),
            'config': raw_field.get('config') or {},
            'active': bool(raw_field.get('active', True)),
        }
        fields.append(field_payload)

    match_rules = payload.get('match_rules') or {}
    lines_payload = payload.get('lines') or DOC_AI_DEFAULT_LINE_RULES
    definition_json = payload.get('definition_json')
    if not isinstance(definition_json, dict):
        definition_json = {
            'doc_type': str(payload.get('doc_type') or 'unknown').strip() or 'unknown',
            'match': match_rules,
            'fields': {
                item['field_key']: {
                    'anchors': item['anchors'],
                    'regex': item['regex'],
                    'aliases': item['aliases'],
                    'required': item['required'],
                    'postprocess': item['postprocess'],
                    'config': item['config'],
                    'match_mode': item['match_mode'],
                }
                for item in fields
            },
            'lines': lines_payload,
        }

    return {
        'name': str(payload.get('name') or 'Novo template').strip(),
        'description': str(payload.get('description') or '').strip(),
        'feid': _safe_int(payload.get('feid'), 0) or None,
        'supplier_no': _safe_int(payload.get('supplier_no'), 0) or None,
        'doc_type': str(payload.get('doc_type') or 'unknown').strip() or 'unknown',
        'language': str(payload.get('language') or '').strip(),
        'fingerprint': str(payload.get('fingerprint') or '').strip(),
        'score_min_match': float(payload.get('score_min_match') or 0.55),
        'parser_id': parser.docparserstamp,
        'parser_version': parser.versao,
        'active': bool(payload.get('active', True)),
        'match_rules_json': _json_dumps(match_rules),
        'definition_json': _json_dumps(definition_json),
        'fields': fields,
        'requested_by': requested_by or '',
    }


def _document_ai_supplier_name(supplier_no: int | None, feid: int | None = None) -> str:
    supplier_no = _safe_int(supplier_no, 0)
    if not supplier_no:
        return ''
    feid_filter = _fl_feid_filter_sql('FL') if feid else ''
    row = db.session.execute(text("""
        SELECT TOP 1 LTRIM(RTRIM(ISNULL(FL.NOME, ''))) AS NOME
        FROM dbo.FL FL
        WHERE CAST(FL.NO AS int) = :supplier_no
        {feid_filter}
        ORDER BY FL.NOME
    """.format(feid_filter=feid_filter)), {
        'supplier_no': supplier_no,
        'feid': int(feid or 0),
    }).mappings().first()
    return str((row or {}).get('NOME') or '').strip()


def _document_ai_entity_name(feid: int | None) -> str:
    feid = _safe_int(feid, 0)
    if not feid:
        return ''
    row = db.session.execute(text("""
        SELECT TOP 1 LTRIM(RTRIM(ISNULL(NULLIF(NOMEFISCAL, ''), NOME))) AS NOME
        FROM dbo.FE
        WHERE CAST(ISNULL(FEID, 0) AS int) = :feid
    """), {'feid': feid}).mappings().first()
    return str((row or {}).get('NOME') or '').strip()


def _document_ai_doc_type_label(doc_type: str) -> str:
    value = str(doc_type or '').strip() or 'unknown'
    for item in DOC_AI_DOC_TYPES:
        if item.get('value') == value:
            return str(item.get('label') or value).strip()
    return value


def _default_template_name(feid: int | None, supplier_no: int | None, doc_type: str) -> str:
    supplier_name = _document_ai_supplier_name(supplier_no, feid)
    entity_name = _document_ai_entity_name(feid)
    doc_label = _document_ai_doc_type_label(doc_type)
    parts = [doc_label]
    if supplier_name:
        parts.append(supplier_name)
    if entity_name:
        parts.append(entity_name)
    return ' · '.join(parts)[:120] or 'Novo template'


def _template_name_is_placeholder(name: str) -> bool:
    normalized = _normalize_text(name)
    if not normalized:
        return True
    return (
        normalized in ('novo template', 'template')
        or 'unknown' in normalized
        or 'desconhecido' in normalized
    )


def _unique_text_list(values: list[Any]) -> list[str]:
    out = []
    seen = set()
    for value in values or []:
        text_value = str(value or '').strip()
        key = _normalize_text(text_value)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(text_value)
    return out


def _name_keyword_variants(name: str) -> list[str]:
    raw = re.sub(r'\s+', ' ', str(name or '').strip())
    if not raw:
        return []
    suffixes = {'SA', 'SAS', 'SARL', 'LDA', 'LIMITED', 'LTD', 'GMBH', 'BV', 'SL'}
    tokens = raw.split(' ')
    variants = [raw]
    if len(tokens) > 1 and tokens[0].upper() in suffixes:
        variants.append(' '.join([*tokens[1:], tokens[0]]))
        variants.append(' '.join(tokens[1:]))
    if len(tokens) > 1 and tokens[-1].upper() in suffixes:
        variants.append(' '.join(tokens[:-1]))
    return _unique_text_list(variants)


def _default_template_keywords(feid: int | None, supplier_no: int | None, doc_type: str) -> list[str]:
    keywords = []
    if str(doc_type or '').strip() == 'delivery_note':
        keywords.append('BON')
    keywords.extend(_name_keyword_variants(_document_ai_supplier_name(supplier_no, feid)))
    keywords.extend(_name_keyword_variants(_document_ai_entity_name(feid)))
    return _unique_text_list(keywords)


def _find_template_by_identity(feid: int | None, supplier_no: int | None, doc_type: str) -> DocTemplate | None:
    feid = _safe_int(feid, 0)
    supplier_no = _safe_int(supplier_no, 0)
    doc_type = str(doc_type or '').strip()
    if not feid or not supplier_no or not doc_type or doc_type == 'unknown':
        return None
    return (
        DocTemplate.query
        .filter(DocTemplate.feid == feid)
        .filter(DocTemplate.fornecedor_no == supplier_no)
        .filter(DocTemplate.doc_type == doc_type)
        .order_by(DocTemplate.ativo.desc(), DocTemplate.dtalt.desc(), DocTemplate.nome.asc())
        .first()
    )


def save_template(payload: dict[str, Any], requested_by: str, template_stamp: str = '') -> dict[str, Any]:
    _ensure_document_ai_schema()
    normalized = _normalize_template_payload(payload or {}, requested_by or '')
    if _template_name_is_placeholder(normalized['name']):
        normalized['name'] = _default_template_name(normalized['feid'], normalized['supplier_no'], normalized['doc_type'])
    if template_stamp:
        template = db.session.get(DocTemplate, str(template_stamp or '').strip())
        if not template:
            raise ValueError('Template não encontrado.')
        template.dtalt = _now()
        template.useralteracao = requested_by or template.useralteracao
    else:
        template = DocTemplate(
            doctemplatestamp=_new_stamp(),
            dtcri=_now(),
            usercriacao=requested_by or '',
            useralteracao=requested_by or '',
        )
        db.session.add(template)

    template.nome = normalized['name']
    template.descricao = normalized['description']
    template.feid = normalized['feid']
    template.fornecedor_no = normalized['supplier_no']
    template.doc_type = normalized['doc_type']
    template.idioma = normalized['language']
    template.fingerprint = normalized['fingerprint']
    template.score_minimo_match = normalized['score_min_match']
    template.regras_identificacao_json = normalized['match_rules_json']
    template.definition_json = normalized['definition_json']
    template.docparserstamp = normalized['parser_id']
    template.parser_version = normalized['parser_version']
    template.ativo = normalized['active']
    if not template.dtcri:
        template.dtcri = _now()
    if not template.dtalt:
        template.dtalt = _now()

    db.session.flush()
    existing_rows = DocTemplateField.query.filter_by(doctemplatestamp=template.doctemplatestamp).all()
    for row in existing_rows:
        db.session.delete(row)
    db.session.flush()

    for field in normalized['fields']:
        db.session.add(DocTemplateField(
            doctemplatefieldstamp=_new_stamp(),
            doctemplatestamp=template.doctemplatestamp,
            field_key=field['field_key'],
            label=field['label'],
            ordem=field['order'],
            required=field['required'],
            match_mode=field['match_mode'],
            anchors_json=_json_dumps(field['anchors']),
            regex_pattern=field['regex'] or None,
            aliases_json=_json_dumps(field['aliases']),
            postprocess=field['postprocess'] or None,
            config_json=_json_dumps(field['config']),
            ativo=field['active'],
            dtcri=_now(),
            dtalt=_now(),
            usercriacao=requested_by or '',
            useralteracao=requested_by or '',
        ))
    db.session.commit()
    return _serialize_template(template, include_definition=True)


def list_templates(filters: dict[str, Any] | None = None) -> dict[str, Any]:
    _ensure_document_ai_schema()
    filters = filters or {}
    items = DocTemplate.query.order_by(
        text("CASE WHEN DTALT IS NULL THEN 1 ELSE 0 END"),
        DocTemplate.dtalt.desc(),
        DocTemplate.nome.asc(),
    ).all()
    out = []
    search = _normalize_text(filters.get('search'))
    doc_type = str(filters.get('doc_type') or '').strip()
    supplier_filter = str(filters.get('supplier') or '').strip()
    active_filter = str(filters.get('active') or '').strip().lower()
    for item in items:
        serialized = _serialize_template(item, include_definition=False)
        if search and search not in _normalize_text(f"{serialized['name']} {serialized['supplier_name']}"):
            continue
        if doc_type and serialized['doc_type'] != doc_type:
            continue
        if supplier_filter and supplier_filter not in str(serialized.get('supplier_no') or '') and supplier_filter.upper() not in str(serialized.get('supplier_name') or '').upper():
            continue
        if active_filter == 'active' and not serialized['active']:
            continue
        if active_filter == 'inactive' and serialized['active']:
            continue
        out.append(serialized)
    return {
        'items': out,
        'doc_types': DOC_AI_DOC_TYPES,
        'parsers': [_serialize_parser(item) for item in DocParser.query.filter_by(ativo=True).order_by(DocParser.nome.asc()).all()],
        'documents': _load_document_rows(limit=80),
        'llm': {'available': llm_suggestions_available()},
    }


def get_template_detail(template_stamp: str) -> dict[str, Any]:
    _ensure_document_ai_schema()
    template = db.session.get(DocTemplate, str(template_stamp or '').strip())
    if not template:
        raise ValueError('Template não encontrado.')
    return _serialize_template(template, include_definition=True)


def toggle_template_active(template_stamp: str, requested_by: str) -> dict[str, Any]:
    _ensure_document_ai_schema()
    template = db.session.get(DocTemplate, str(template_stamp or '').strip())
    if not template:
        raise ValueError('Template não encontrado.')
    template.ativo = not bool(template.ativo)
    template.dtalt = _now()
    template.useralteracao = requested_by or template.useralteracao
    db.session.commit()
    return _serialize_template(template, include_definition=True)


def test_template(template_stamp: str, document_stamp: str) -> dict[str, Any]:
    _ensure_document_ai_schema()
    template = db.session.get(DocTemplate, str(template_stamp or '').strip())
    document = db.session.get(DocInbox, str(document_stamp or '').strip())
    if not template:
        raise ValueError('Template não encontrado.')
    if not document:
        raise ValueError('Documento não encontrado.')
    supplier_match = {
        'supplier_no': document.fornecedor_no,
        'supplier_tax_id': document.fornecedor_nif_detetado or '',
        'supplier_name': document.fornecedor_nome_detetado or '',
        'score': float(document.confidence_score or 0),
    }
    doc_type_info = {'doc_type': document.doc_type_detected or 'unknown', 'score': 0.8}
    payload = _execute_template_parse(
        document.extracted_text or '',
        _json_loads(document.text_blocks_json, []),
        {'template': _serialize_template(template, include_definition=True), 'definition': _template_definition_payload(template)},
        supplier_match,
        doc_type_info,
    )
    validation = _validate_parse_result(payload, {'template': template, 'score': 0.9})
    return {
        'template': _serialize_template(template, include_definition=True),
        'document_id': document.docinstamp,
        'result': payload.get('result') or {},
        'warnings': validation.get('warnings') or [],
        'errors': validation.get('errors') or [],
        'status': validation.get('status') or 'review_required',
        'confidence': payload.get('confidence') or 0,
    }


def save_template_from_document(document_stamp: str, payload: dict[str, Any], requested_by: str) -> dict[str, Any]:
    template_payload = dict(payload or {})
    document = db.session.get(DocInbox, str(document_stamp or '').strip())
    result_payload = template_payload.get('result') if isinstance(template_payload.get('result'), dict) else {}
    supplier_payload = result_payload.get('supplier') if isinstance(result_payload.get('supplier'), dict) else {}
    customer_payload = result_payload.get('customer') if isinstance(result_payload.get('customer'), dict) else {}

    if document:
        if not _safe_int(template_payload.get('feid'), 0):
            template_payload['feid'] = document.feid
        if not _safe_int(template_payload.get('supplier_no'), 0):
            template_payload['supplier_no'] = document.fornecedor_no
        if not str(template_payload.get('doc_type') or '').strip() or str(template_payload.get('doc_type') or '').strip() == 'unknown':
            template_payload['doc_type'] = document.doc_type_detected or 'unknown'

    if not _safe_int(template_payload.get('feid'), 0):
        customer_match = resolve_fe_entity(customer_payload.get('tax_id') or customer_payload.get('name') or '')
        if customer_match.get('feid'):
            template_payload['feid'] = customer_match.get('feid')

    feid = _safe_int(template_payload.get('feid'), 0)
    supplier_no = _safe_int(template_payload.get('supplier_no'), 0)
    if not supplier_no:
        supplier_query = supplier_payload.get('tax_id') or supplier_payload.get('name') or template_payload.get('supplier_name') or ''
        matches = search_suppliers(supplier_query, feid=feid, limit=1) if supplier_query and feid else []
        if matches:
            supplier_no = _safe_int(matches[0].get('no'), 0)
            template_payload['supplier_no'] = supplier_no

    doc_type = str(template_payload.get('doc_type') or '').strip() or 'unknown'
    if not feid:
        raise ValueError('Identifica primeiro a Entidade FE do cliente antes de guardar o template.')
    if not supplier_no:
        raise ValueError('Identifica primeiro o fornecedor antes de guardar o template.')
    if not doc_type or doc_type == 'unknown':
        raise ValueError('Define primeiro o tipo de documento antes de guardar o template.')

    match_rules = template_payload.get('match_rules') if isinstance(template_payload.get('match_rules'), dict) else {}
    match_rules['keywords'] = _unique_text_list([
        *(match_rules.get('keywords') or []),
        *_default_template_keywords(feid, supplier_no, doc_type),
    ])
    template_payload['match_rules'] = match_rules

    template_stamp = str(template_payload.get('id') or '').strip()
    replacing_existing = False
    if template_stamp:
        selected_template = db.session.get(DocTemplate, template_stamp)
        if selected_template and (
            _safe_int(selected_template.feid, 0) == feid
            and _safe_int(selected_template.fornecedor_no, 0) == supplier_no
            and str(selected_template.doc_type or '').strip() == doc_type
        ):
            replacing_existing = True
        else:
            template_stamp = ''

    if not template_stamp:
        existing_template = _find_template_by_identity(feid, supplier_no, doc_type)
        if existing_template:
            template_stamp = existing_template.doctemplatestamp
            replacing_existing = True

    saved = save_template(template_payload, requested_by=requested_by, template_stamp=template_stamp)
    saved['action'] = 'updated' if replacing_existing else 'created'
    if document:
        document.doctemplatestamp = saved.get('id')
        document.feid = feid
        document.fornecedor_no = supplier_no
        document.doc_type_detected = doc_type
        document.dtalt = _now()
        document.useralteracao = requested_by or document.useralteracao
        _document_log(document.docinstamp, 'template_save', 'ok', 'Template guardado a partir da validação.', {'template_id': saved.get('id')})
        db.session.commit()
    return saved


def document_ai_lookups() -> dict[str, Any]:
    _ensure_document_ai_schema()
    _ensure_default_parser()
    return {
        'doc_types': DOC_AI_DOC_TYPES,
        'statuses': DOC_AI_STATUSES,
        'parsers': [_serialize_parser(item) for item in DocParser.query.filter_by(ativo=True).order_by(DocParser.nome.asc()).all()],
        'documents': _load_document_rows(limit=80),
        'llm': {'available': llm_suggestions_available()},
    }


def suggest_template(payload: dict[str, Any]) -> dict[str, Any]:
    return suggest_template_definition(payload or {})
