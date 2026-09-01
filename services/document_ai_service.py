import hashlib
import fnmatch
import importlib.util
import io
import json
import mimetypes
import ntpath
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import threading
import unicodedata
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from flask import current_app, has_app_context
from sqlalchemy import text

from models import db, DocInbox, DocParser, DocProcessLog, DocSource, DocTemplate, DocTemplateField
from services.document_ai_llm_service import classify_document_visual, llm_suggestions_available, suggest_template_definition
from services.document_ai_ocr_service import ocr_engine_available
from services.document_ai_processing_orchestrator import extract_document_with_cascade
from services.document_duplicate_service import acquire_duplicate_lock, evaluate_duplicate_match, find_exact_file_duplicate
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
    {'value': 'provisional_invoice', 'label': 'Fatura Provisória'},
    {'value': 'credit_note', 'label': 'Nota de Crédito'},
    {'value': 'contract', 'label': 'Contrato'},
    {'value': 'subcontract', 'label': 'Contrato de SubEmpreitada'},
    {'value': 'purchase_order', 'label': 'Nota de Encomenda'},
    {'value': 'delivery_note', 'label': 'Guia de Remessa'},
    {'value': 'bank_statement', 'label': 'Extrato Bancário'},
    {'value': 'mail', 'label': 'Correio'},
    {'value': 'advertising', 'label': 'Publicidade'},
    {'value': 'unknown', 'label': 'Desconhecido'},
]

DOC_AI_DOC_TYPE_ALIASES = {
    'contrat': 'contract',
    'contract': 'contract',
    'contrato': 'contract',
    'contrat_sous_traitant': 'subcontract',
    'contrat_sout_traitant': 'subcontract',
    'contract_subcontractor': 'subcontract',
    'sub_contract': 'subcontract',
    'subcontract': 'subcontract',
    'subcontract_contract': 'subcontract',
    'bon_de_livraison': 'delivery_note',
    'delivery': 'delivery_note',
    'delivery_note': 'delivery_note',
    'guia': 'delivery_note',
    'bon_de_commande': 'purchase_order',
    'purchase_order': 'purchase_order',
    'nota_de_encomenda': 'purchase_order',
    'avoir': 'credit_note',
    'credit_note': 'credit_note',
    'nota_de_credito': 'credit_note',
}


def normalize_document_type(value: Any) -> str:
    """Return the public canonical type without leaking source-system aliases."""
    normalized = _normalize_text(value or 'unknown').replace(' ', '_').replace('-', '_')
    return DOC_AI_DOC_TYPE_ALIASES.get(normalized, normalized or 'unknown')

DOC_AI_PURCHASE_INVOICE_CORRESPONDENCE_TYPE = 'FAC'
DOC_AI_PURCHASE_CREDIT_NOTE_CORRESPONDENCE_TYPE = 'NC'

# A pasta-base da GED pertence à empresa configurada na FE. O nome fiscal não
# é uma chave segura (por exemplo, Betãoconcept usa a base PHC HSOLS_PT).
DOC_AI_GED_FOLDER_BY_PHC_DATABASE = {
    'HSOLS_FR': 'HSOLS_FR',
    'HSOLS_PT': 'HSOLS_PT',
    'GR360': 'HSOLS_GR360_PT',
    'HSOLS_DE': 'HSOLS_DE',
    'HSOLS_ES': 'HSOLS_ES',
    'HSOLS_MA': 'HSOLS_MA',
    'HSOLS_CH': 'HSOLS_CH',
    'INTERSOL': 'HSOLS_INTERSOL_AL',
}
DOC_AI_INTERSOL_GED_FOLDERS = {
    'HSOLS_INTERSOL_AL', 'HSOLS_INTERSOL_LOR', 'HSOLS_INTERSOL_CH',
}


def _missing_intersol_agency(customer: dict[str, Any] | None) -> bool:
    customer = dict(customer or {})
    database_name = str(customer.get('phc_database') or '').strip().upper()
    ged_folder = str(customer.get('ged_folder') or '').strip().upper()
    is_intersol = database_name == 'INTERSOL' or ged_folder.startswith('HSOLS_INTERSOL_')
    return is_intersol and ged_folder not in DOC_AI_INTERSOL_GED_FOLDERS


def _ged_folder_from_phc_database(value: Any) -> str:
    database_name = str(value or '').strip().upper()
    mapped = DOC_AI_GED_FOLDER_BY_PHC_DATABASE.get(database_name, '')
    if mapped:
        return mapped
    # As restantes empresas usam na GED exatamente a chave PHC indicada na FE
    # (HSOLS_FR_GE, HSOLS_G2S, HSOLS_GHA, HSOLS_IND, etc.).
    if re.fullmatch(r'(?:HSOLS|GR360)_[A-Z0-9_]+', database_name):
        return database_name
    return ''

DOC_AI_DOC_TYPE_TERMS = {
    'invoice': {
        'strong': ['invoice', 'facture', 'fatura', 'factura', 'décompte de frais', 'decompte de frais'],
        'normal': ['bill to', 'amount due', 'montant facture', 'total facture', 'frais de dossier', 'commission'],
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
    'bank_statement': {
        'strong': ['releve de compte', 'relevé de compte', 'extrait de compte', 'compte courant professionnel'],
        'normal': ['solde initial', 'solde final', 'date valeur', 'mouvements', 'relevé bancaire', 'releve bancaire'],
        'weak': ['iban', 'bic'],
    },
    'mail': {
        'strong': ['lettre d information', 'lettre information', 'courrier d information'],
        'normal': ['lettre', 'courrier', 'avis'],
        'weak': ['information'],
    },
}

DOC_AI_STATUSES = [
    {'value': 'new', 'label': 'Novo'},
    {'value': 'text_extracted', 'label': 'Texto extraído'},
    {'value': 'template_unknown', 'label': 'Template desconhecido'},
    {'value': 'review_required', 'label': 'Por validar'},
    {'value': 'parsed_ok', 'label': 'Processado'},
    {'value': 'provisional_invoice', 'label': 'Fatura Provisória'},
    {'value': 'parse_error', 'label': 'Erro'},
]

DOC_AI_CANONICAL_SCHEMA = {
    'document_type': 'invoice',
    'invoice_type': 'unknown',
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


def _fl_tax_id_column() -> str:
    if _column_exists('FL', 'NIF'):
        return 'NIF'
    if _column_exists('FL', 'NCONT'):
        return 'NCONT'
    return ''


def _cl_tax_id_column() -> str:
    if _column_exists('CL', 'NIF'):
        return 'NIF'
    if _column_exists('CL', 'NCONT'):
        return 'NCONT'
    return ''


def _first_existing_column(table_name: str, candidates: list[str]) -> str:
    for candidate in candidates:
        if _column_exists(table_name, candidate):
            return candidate
    return ''


def _fe_supplier_source(feid: int | None) -> dict[str, Any]:
    clean_feid = _safe_int(feid, 0)
    if not clean_feid:
        return {'kind': 'app', 'feid': None, 'tax_field': _fl_tax_id_column().lower() or 'unknown'}

    database_column = _first_existing_column('FE', [
        'PHC_DATABASE', 'PHC_DB', 'DBPHC', 'BDPHC',
        'ERP_DATABASE', 'ERP_DB', 'DBERP', 'BDERP',
        'DATABASE_NAME', 'DB_NAME', 'DBNAME',
        'BASEDADOS', 'BASE_DADOS', 'BD', 'NOMEBD',
    ])
    if not database_column:
        for configured in _configured_phc_sources():
            if _safe_int(configured.get('FEID'), 0) == clean_feid:
                return {
                    'kind': 'phc',
                    'feid': clean_feid,
                    'tax_field': 'ncont',
                    'phc_db': str(configured.get('PHC_DB') or '').strip(),
                    'phc_server': str(configured.get('PHC_SERVER') or '').strip(),
                }
        return {'kind': 'app', 'feid': clean_feid, 'tax_field': _fl_tax_id_column().lower() or 'unknown'}

    server_column = _first_existing_column('FE', [
        'PHC_SERVER', 'SERVER_PHC', 'ERP_SERVER', 'SERVER_ERP',
        'SQLSERVER', 'SQL_SERVER', 'SERVIDOR', 'SERVER',
    ])
    server_select = f"LTRIM(RTRIM(ISNULL(FE.[{server_column}], '')))" if server_column else "CAST('' AS varchar(128))"
    row = db.session.execute(text(f"""
        SELECT TOP 1
            LTRIM(RTRIM(ISNULL(FE.[{database_column}], ''))) AS PHC_DB,
            {server_select} AS PHC_SERVER
        FROM dbo.FE FE
        WHERE FE.FEID = :feid
    """), {'feid': clean_feid}).mappings().first() or {}
    phc_db = str(row.get('PHC_DB') or '').strip()
    if not phc_db:
        for configured in _configured_phc_sources():
            if _safe_int(configured.get('FEID'), 0) == clean_feid:
                return {
                    'kind': 'phc',
                    'feid': clean_feid,
                    'tax_field': 'ncont',
                    'phc_db': str(configured.get('PHC_DB') or '').strip(),
                    'phc_server': str(configured.get('PHC_SERVER') or '').strip(),
                }
        return {'kind': 'app', 'feid': clean_feid, 'tax_field': _fl_tax_id_column().lower() or 'unknown'}
    return {
        'kind': 'phc',
        'feid': clean_feid,
        'tax_field': 'ncont',
        'phc_db': phc_db,
        'phc_server': str(row.get('PHC_SERVER') or '').strip(),
    }


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
    if not os.path.isfile(absolute_path):
        return current_blocks, preview_pages
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
    phc_database = str(row.get('PHC_DB') or '').strip()
    return {
        'feid': _safe_int(row.get('FEID'), 0) or None,
        'name': name,
        'tax_id': _digits_only(row.get('NIF')),
        'phc_database': phc_database,
        'ged_folder': _ged_folder_from_phc_database(phc_database),
        'score': round(float(score or 0), 4),
        'matched_by': matched_by,
    }


def _fe_entity_by_id(feid: int | None) -> dict[str, Any]:
    clean_feid = _safe_int(feid, 0)
    if not clean_feid:
        return {}
    try:
        entities = _load_fe_entities()
    except RuntimeError:
        # Mantém os helpers reutilizáveis em tarefas/testes sem contexto Flask.
        return {}
    for entity in entities:
        if _safe_int(entity.get('FEID'), 0) == clean_feid:
            return _serialize_fe_row(entity, 1, 'feid')
    return {}


def _load_fe_entities() -> list[dict[str, Any]]:
    configured = _configured_phc_sources()
    if configured:
        return [{
            'FEID': _safe_int(row.get('FEID'), 0),
            'NOME': str(row.get('NOME') or '').strip(),
            'NOMEFISCAL': str(row.get('NOMEFISCAL') or '').strip(),
            'NIF': str(row.get('NIF') or '').strip(),
            'PHC_DB': str(row.get('PHC_DB') or '').strip(),
            'PHC_SERVER': str(row.get('PHC_SERVER') or '').strip(),
        } for row in configured]
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
        for entity in _load_fe_entities():
            if _digits_only(entity.get('NIF')) == digits:
                return _serialize_fe_row(entity, 0.99, 'tax_id')

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


def search_fe_entities(value: str = '', limit: int = 20) -> list[dict[str, Any]]:
    raw = str(value or '').strip()
    normalized_raw = _normalize_text(raw)
    digits = _digits_only(raw)
    results = []
    for entity in _load_fe_entities():
        serialized = _serialize_fe_row(entity)
        name = str(serialized.get('name') or '')
        tax_id = str(serialized.get('tax_id') or '')
        if not raw:
            score = 1.0
        else:
            normalized_name = _normalize_text(name)
            if digits and digits in tax_id:
                score = 1.0 if digits == tax_id else 0.92
            elif normalized_raw in normalized_name:
                score = 0.95
            else:
                score = SequenceMatcher(None, normalized_name, normalized_raw).ratio()
            if score < 0.3:
                continue
        serialized['score'] = round(score, 4)
        results.append(serialized)
    results.sort(key=lambda item: (-float(item.get('score') or 0), str(item.get('name') or '')))
    return results[:max(1, min(int(limit or 20), 50))]


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
            min_name_length = 2 if any(char.isdigit() for char in normalized_name) else 4
            if not normalized_name or len(normalized_name) < min_name_length:
                continue
            min_token_length = 2 if any(char.isdigit() for char in normalized_name) else 3
            name_tokens = [token for token in normalized_name.split(' ') if len(token) >= min_token_length]
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
    source = _fe_supplier_source(feid)
    if source.get('kind') == 'phc':
        import pyodbc
        from services.colaborador_despesas_service import _phc_conn_str

        with pyodbc.connect(
            _phc_conn_str(str(source.get('phc_db') or ''), str(source.get('phc_server') or '')),
            timeout=8,
        ) as connection:
            cursor = connection.cursor()
            rows = cursor.execute("""
                SELECT
                    CAST(ISNULL(FL.NO, 0) AS int) AS NO,
                    CAST(ISNULL(FL.ESTAB, 0) AS int) AS ESTAB,
                    LTRIM(RTRIM(ISNULL(FL.NOME, ''))) AS NOME,
                    LTRIM(RTRIM(ISNULL(FL.NOME2, ''))) AS NOME2,
                    LTRIM(RTRIM(CAST(ISNULL(FL.NCONT, '') AS varchar(40)))) AS NIF,
                    LTRIM(RTRIM(ISNULL(FL.MORADA, ''))) AS MORADA,
                    LTRIM(RTRIM(ISNULL(FL.LOCAL, ''))) AS LOCAL,
                    LTRIM(RTRIM(ISNULL(FL.CODPOST, ''))) AS CODPOST
                FROM dbo.FL FL
                WHERE ISNULL(FL.NOME, '') <> ''
                ORDER BY FL.NOME
            """).fetchall()
        return [{
            'NO': _safe_int(row[0], 0),
            'ESTAB': _safe_int(row[1], 0),
            'NOME': str(row[2] or '').strip(),
            'NOME2': str(row[3] or '').strip(),
            'NIF': str(row[4] or '').strip(),
            'MORADA': str(row[5] or '').strip(),
            'LOCAL': str(row[6] or '').strip(),
            'CODPOST': str(row[7] or '').strip(),
            'FEID': _safe_int(feid, 0),
            'TAX_FIELD': 'ncont',
            'SOURCE': 'phc',
        } for row in rows]

    feid_filter = _fl_feid_filter_sql('FL') if feid else ''
    feid_select = "CAST(ISNULL(FL.FEID, 0) AS int)" if _column_exists('FL', 'FEID') else "CAST(0 AS int)"
    tax_column = _fl_tax_id_column()
    tax_select = f"LTRIM(RTRIM(CAST(ISNULL(FL.{tax_column}, '') AS varchar(40))))" if tax_column else "CAST('' AS varchar(40))"
    estab_select = "CAST(ISNULL(FL.ESTAB, 0) AS int)" if _column_exists('FL', 'ESTAB') else "CAST(0 AS int)"
    name2_select = "LTRIM(RTRIM(ISNULL(FL.NOME2, '')))" if _column_exists('FL', 'NOME2') else "CAST('' AS varchar(80))"
    address_select = "LTRIM(RTRIM(ISNULL(FL.MORADA, '')))" if _column_exists('FL', 'MORADA') else "CAST('' AS varchar(80))"
    city_select = "LTRIM(RTRIM(ISNULL(FL.LOCAL, '')))" if _column_exists('FL', 'LOCAL') else "CAST('' AS varchar(80))"
    postal_select = "LTRIM(RTRIM(ISNULL(FL.CODPOST, '')))" if _column_exists('FL', 'CODPOST') else "CAST('' AS varchar(30))"
    rows = db.session.execute(text("""
        SELECT
            CAST(FL.NO AS int) AS NO,
            {estab_select} AS ESTAB,
            LTRIM(RTRIM(ISNULL(FL.NOME, ''))) AS NOME,
            {name2_select} AS NOME2,
            {tax_select} AS NIF,
            {address_select} AS MORADA,
            {city_select} AS LOCAL,
            {postal_select} AS CODPOST,
            {feid_select} AS FEID
        FROM dbo.FL FL
        WHERE ISNULL(FL.NOME, '') <> ''
        {feid_filter}
        ORDER BY FL.NOME
    """.format(feid_filter=feid_filter, feid_select=feid_select, tax_select=tax_select,
               estab_select=estab_select, name2_select=name2_select, address_select=address_select,
               city_select=city_select, postal_select=postal_select)), {'feid': int(feid or 0)}).mappings().all()
    return [{
        **dict(row),
        'TAX_FIELD': str(source.get('tax_field') or 'unknown'),
        'SOURCE': 'app',
    } for row in rows]


def _party_location_score(context: dict[str, Any] | None, party: dict[str, Any]) -> float:
    context = dict(context or {})
    wanted_postal = _normalize_text(context.get('postal_code'))
    wanted_city = _normalize_text(context.get('city'))
    wanted_address = _normalize_text(context.get('address'))
    candidate_postal = _normalize_text(party.get('CODPOST') or party.get('postal_code'))
    candidate_city = _normalize_text(party.get('LOCAL') or party.get('city'))
    candidate_address = _normalize_text(party.get('MORADA') or party.get('address'))
    scores = []
    if wanted_postal and candidate_postal:
        scores.append(1.0 if wanted_postal == candidate_postal else SequenceMatcher(None, wanted_postal, candidate_postal).ratio())
    if wanted_city and candidate_city:
        scores.append(1.0 if wanted_city == candidate_city else SequenceMatcher(None, wanted_city, candidate_city).ratio())
    if wanted_address and candidate_address:
        scores.append(SequenceMatcher(None, wanted_address, candidate_address).ratio())
    return round(max(scores or [0.0]), 4)


def search_suppliers(value: str, feid: int | None = None, limit: int = 8, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    if not _safe_int(feid, 0):
        raise ValueError('Identifica primeiro a Entidade FE do cliente.')
    raw = str(value or '').strip()
    normalized_raw = _normalize_text(raw)
    digits = _digits_only(raw)
    if len(normalized_raw) < 2 and len(digits) < 2:
        return []

    results: list[dict[str, Any]] = []
    seen: set[tuple[int, int, int]] = set()
    for supplier in _load_suppliers(feid):
        supplier_no = _safe_int(supplier.get('NO'), 0)
        supplier_feid = _safe_int(supplier.get('FEID'), 0)
        supplier_estab = _safe_int(supplier.get('ESTAB'), 0)
        key = (supplier_feid, supplier_no, supplier_estab)
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
            elif len(tax_id) >= 6 and len(digits) >= 6 and (digits in tax_id or tax_id in digits):
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
            'estab': supplier_estab,
            'name': name,
            'short_name': str(supplier.get('NOME2') or '').strip(),
            'tax_id': tax_id,
            'feid': supplier_feid or (int(feid or 0) or None),
            'score': round(min(score, 0.99), 4),
            'matched_by': matched_by or 'name',
            'tax_field': str(supplier.get('TAX_FIELD') or 'unknown').lower(),
            'source': str(supplier.get('SOURCE') or 'app').lower(),
            'address': str(supplier.get('MORADA') or '').strip(),
            'city': str(supplier.get('LOCAL') or '').strip(),
            'postal_code': str(supplier.get('CODPOST') or '').strip(),
            'location_score': _party_location_score(context, supplier),
        })

    results.sort(key=lambda item: (-float(item.get('location_score') or 0), -float(item.get('score') or 0), str(item.get('name') or ''), int(item.get('estab') or 0)))
    return results[:max(1, min(int(limit or 8), 20))]


def _load_customers(feid: int) -> list[dict[str, Any]]:
    source = _fe_supplier_source(feid)
    if source.get('kind') == 'phc':
        import pyodbc
        from services.colaborador_despesas_service import _phc_conn_str

        with pyodbc.connect(
            _phc_conn_str(str(source.get('phc_db') or ''), str(source.get('phc_server') or '')),
            timeout=8,
        ) as connection:
            rows = connection.cursor().execute("""
                SELECT CAST(ISNULL(CL.NO, 0) AS int),
                       CAST(ISNULL(CL.ESTAB, 0) AS int),
                       LTRIM(RTRIM(ISNULL(CL.NOME, ''))),
                       LTRIM(RTRIM(ISNULL(CL.NOME2, ''))),
                       LTRIM(RTRIM(CAST(ISNULL(CL.NCONT, '') AS varchar(40)))),
                       LTRIM(RTRIM(ISNULL(CL.MORADA, ''))),
                       LTRIM(RTRIM(ISNULL(CL.LOCAL, ''))),
                       LTRIM(RTRIM(ISNULL(CL.CODPOST, '')))
                FROM dbo.CL CL
                WHERE ISNULL(CL.NOME, '') <> ''
                ORDER BY CL.NOME
            """).fetchall()
        return [{
            'NO': _safe_int(row[0], 0), 'ESTAB': _safe_int(row[1], 0),
            'NOME': str(row[2] or '').strip(), 'NOME2': str(row[3] or '').strip(),
            'NIF': str(row[4] or '').strip(), 'MORADA': str(row[5] or '').strip(),
            'LOCAL': str(row[6] or '').strip(), 'CODPOST': str(row[7] or '').strip(), 'FEID': feid,
            'TAX_FIELD': 'ncont', 'SOURCE': 'phc',
        } for row in rows]

    feid_select = "CAST(ISNULL(CL.FEID, 0) AS int)" if _column_exists('CL', 'FEID') else "CAST(0 AS int)"
    feid_filter = "AND ISNULL(CL.FEID, 0) = :feid" if _column_exists('CL', 'FEID') else ''
    tax_column = _cl_tax_id_column()
    tax_select = f"LTRIM(RTRIM(CAST(ISNULL(CL.{tax_column}, '') AS varchar(40))))" if tax_column else "CAST('' AS varchar(40))"
    estab_select = "CAST(ISNULL(CL.ESTAB, 0) AS int)" if _column_exists('CL', 'ESTAB') else "CAST(0 AS int)"
    name2_select = "LTRIM(RTRIM(ISNULL(CL.NOME2, '')))" if _column_exists('CL', 'NOME2') else "CAST('' AS varchar(80))"
    address_select = "LTRIM(RTRIM(ISNULL(CL.MORADA, '')))" if _column_exists('CL', 'MORADA') else "CAST('' AS varchar(80))"
    city_select = "LTRIM(RTRIM(ISNULL(CL.LOCAL, '')))" if _column_exists('CL', 'LOCAL') else "CAST('' AS varchar(80))"
    postal_select = "LTRIM(RTRIM(ISNULL(CL.CODPOST, '')))" if _column_exists('CL', 'CODPOST') else "CAST('' AS varchar(30))"
    rows = db.session.execute(text(f"""
        SELECT CAST(ISNULL(CL.NO, 0) AS int) AS NO,
               {estab_select} AS ESTAB,
               LTRIM(RTRIM(ISNULL(CL.NOME, ''))) AS NOME,
               {name2_select} AS NOME2,
               {tax_select} AS NIF,
               {address_select} AS MORADA,
               {city_select} AS LOCAL,
               {postal_select} AS CODPOST,
               {feid_select} AS FEID
        FROM dbo.CL CL
        WHERE ISNULL(CL.NOME, '') <> '' {feid_filter}
        ORDER BY CL.NOME
    """), {'feid': feid}).mappings().all()
    return [{**dict(row), 'TAX_FIELD': tax_column.lower() or 'unknown', 'SOURCE': 'app'} for row in rows]


def search_customers(value: str, feid: int | None = None, limit: int = 8, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    clean_feid = _safe_int(feid, 0)
    if not clean_feid:
        raise ValueError('Identifica primeiro a Entidade FE.')
    raw = str(value or '').strip()
    normalized_raw = _normalize_text(raw)
    digits = _digits_only(raw)
    if len(normalized_raw) < 2 and len(digits) < 2:
        return []
    results = []
    seen = set()
    for customer in _load_customers(clean_feid):
        customer_no = _safe_int(customer.get('NO'), 0)
        customer_estab = _safe_int(customer.get('ESTAB'), 0)
        key = (_safe_int(customer.get('FEID'), clean_feid), customer_no, customer_estab)
        if not customer_no or key in seen:
            continue
        seen.add(key)
        name = str(customer.get('NOME') or '').strip()
        tax_id = _digits_only(customer.get('NIF'))
        normalized_name = _normalize_text(name)
        score = 0.0
        matched_by = ''
        if digits and tax_id:
            if digits == tax_id:
                score, matched_by = 0.99, 'tax_id'
            elif len(tax_id) >= 6 and len(digits) >= 6 and (digits in tax_id or tax_id in digits):
                score, matched_by = 0.88, 'tax_id'
        if normalized_raw and normalized_name:
            ratio = SequenceMatcher(None, normalized_name, normalized_raw).ratio()
            if normalized_raw == normalized_name:
                score, matched_by = max(score, 0.98), matched_by or 'name'
            elif normalized_raw in normalized_name or normalized_name in normalized_raw:
                score, matched_by = max(score, 0.9), matched_by or 'name'
            elif ratio >= 0.35:
                score, matched_by = max(score, ratio * 0.82), matched_by or 'name'
        if score < 0.32:
            continue
        results.append({
            'no': customer_no, 'estab': customer_estab, 'name': name,
            'short_name': str(customer.get('NOME2') or '').strip(),
            'tax_id': tax_id, 'feid': key[0],
            'score': round(min(score, 0.99), 4), 'matched_by': matched_by or 'name',
            'tax_field': str(customer.get('TAX_FIELD') or 'unknown').lower(),
            'source': str(customer.get('SOURCE') or 'app').lower(),
            'address': str(customer.get('MORADA') or '').strip(),
            'city': str(customer.get('LOCAL') or '').strip(),
            'postal_code': str(customer.get('CODPOST') or '').strip(),
            'location_score': _party_location_score(context, customer),
        })
    results.sort(key=lambda item: (-float(item.get('location_score') or 0), -float(item.get('score') or 0), str(item.get('name') or ''), int(item.get('estab') or 0)))
    return results[:max(1, min(int(limit or 8), 20))]


def search_external_parties(value: str, feid: int | None = None, limit: int = 12, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    clean_limit = max(1, min(int(limit or 12), 20))
    suppliers = []
    customers = []
    try:
        suppliers = [
            {**item, 'party_role': 'supplier', 'party_label': 'Fornecedor'}
            for item in search_suppliers(value, feid=feid, limit=clean_limit, context=context)
        ]
    except Exception:
        current_app.logger.exception('Não foi possível pesquisar a FL durante a pesquisa de correio')
    try:
        customers = [
            {**item, 'party_role': 'customer', 'party_label': 'Cliente'}
            for item in search_customers(value, feid=feid, limit=clean_limit, context=context)
        ]
    except Exception:
        current_app.logger.exception('Não foi possível pesquisar a CL durante a pesquisa de correio')
    results = suppliers + customers
    results.sort(key=lambda item: (-float(item.get('score') or 0), str(item.get('name') or ''), str(item.get('party_role') or '')))
    return results[:clean_limit]


def reconcile_extracted_document(document_data: dict[str, Any] | None) -> dict[str, Any]:
    result = dict(document_data or {})
    is_mail = str(result.get('document_type') or '').strip().lower() == 'mail'
    customer = dict(result.get('customer') or {})
    supplier = dict(result.get('supplier') or {})

    llm_customer_name = str(customer.get('name') or '').strip()
    llm_customer_tax_id = _digits_only(customer.get('tax_id'))
    customer_match = {}
    if llm_customer_tax_id:
        customer_match = resolve_fe_entity(llm_customer_tax_id, 'tax_id')
    if not customer_match and llm_customer_name:
        customer_match = resolve_fe_entity(llm_customer_name, 'name')
    if (
        customer_match
        and customer_match.get('matched_by') != 'tax_id'
        and float(customer_match.get('score') or 0) < 0.6
    ):
        customer_match = {}

    if customer_match.get('feid'):
        customer.update({
            'feid': customer_match.get('feid'),
            'name': customer_match.get('name') or llm_customer_name,
            'tax_id': customer_match.get('tax_id') or llm_customer_tax_id,
            'phc_database': customer_match.get('phc_database') or '',
            'ged_folder': customer_match.get('ged_folder') or '',
            'llm_name': llm_customer_name,
            'llm_tax_id': llm_customer_tax_id,
            'match_score': customer_match.get('score') or 0,
            'matched_by': customer_match.get('matched_by') or '',
        })
    elif is_mail:
        customer.update({
            'name': '',
            'tax_id': '',
            'llm_name': llm_customer_name,
            'llm_tax_id': llm_customer_tax_id,
            'match_score': 0,
            'matched_by': '',
        })
    result['customer'] = customer

    llm_supplier_name = str(supplier.get('name') or '').strip()
    llm_supplier_tax_id = _digits_only(supplier.get('tax_id'))
    feid = _safe_int(customer_match.get('feid'), 0)
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, int, int, int]] = set()

    def add_candidates(items: list[dict[str, Any]], party_role: str = 'supplier'):
        for item in items:
            role = str(item.get('party_role') or party_role or 'supplier')
            key = (role, _safe_int(item.get('feid'), feid), _safe_int(item.get('no'), 0), _safe_int(item.get('estab'), 0))
            if not key[2] or key in seen:
                continue
            seen.add(key)
            candidates.append({**dict(item), 'party_role': role, 'party_label': 'Cliente' if role == 'customer' else 'Fornecedor'})

    supplier_lookup_error = ''
    try:
        if feid and llm_supplier_tax_id:
            if is_mail:
                add_candidates(search_external_parties(llm_supplier_tax_id, feid=feid, limit=12, context=supplier))
            else:
                add_candidates(search_suppliers(llm_supplier_tax_id, feid=feid, limit=12, context=supplier))
        if feid and llm_supplier_name:
            if is_mail:
                add_candidates(search_external_parties(llm_supplier_name, feid=feid, limit=12, context=supplier))
            else:
                add_candidates(search_suppliers(llm_supplier_name, feid=feid, limit=12, context=supplier))
    except Exception as exc:
        current_app.logger.exception('Erro ao reconciliar fornecedor extraído na FL')
        supplier_lookup_error = str(exc)
    candidates.sort(key=lambda item: (-float(item.get('location_score') or 0), -float(item.get('score') or 0), str(item.get('name') or ''), int(item.get('estab') or 0)))
    candidates = candidates[:12]

    selected = candidates[0] if candidates else {}
    selected_score = float(selected.get('score') or 0)
    next_score = float(candidates[1].get('score') or 0) if len(candidates) > 1 else 0
    same_party_establishments = {
        (str(item.get('party_role') or 'supplier'), _safe_int(item.get('no'), 0), _safe_int(item.get('estab'), 0))
        for item in candidates
        if _safe_int(item.get('no'), 0) == _safe_int(selected.get('no'), 0)
        and str(item.get('party_role') or 'supplier') == str(selected.get('party_role') or 'supplier')
    }
    establishment_is_unambiguous = len(same_party_establishments) <= 1 or (
        float(selected.get('location_score') or 0) >= 0.72
        and float(selected.get('location_score') or 0) - float(candidates[1].get('location_score') or 0) >= 0.08
    )
    tax_match = bool(
        selected
        and selected.get('matched_by') == 'tax_id'
        and selected_score >= 0.95
        and establishment_is_unambiguous
    )
    confident_name_match = bool(
        selected
        and establishment_is_unambiguous
        and (
            selected_score >= 0.86
            or (selected_score >= 0.72 and selected_score - next_score >= 0.12)
        )
    )
    auto_matched = tax_match or confident_name_match

    supplier.update({
        'llm_name': llm_supplier_name,
        'llm_tax_id': llm_supplier_tax_id,
    })
    if is_mail:
        selected_role = str(selected.get('party_role') or result.get('external_party_role') or 'unknown')
        supplier['supplier_no'] = None
        supplier['customer_no'] = None
        supplier['feid'] = feid or None
        if auto_matched:
            result['external_party_role'] = selected_role
            supplier.update({
                ('customer_no' if selected_role == 'customer' else 'supplier_no'): selected.get('no'),
                'estab': selected.get('estab') or 0,
                'name': selected.get('name') or llm_supplier_name,
                'short_name': selected.get('short_name') or '',
                'tax_id': selected.get('tax_id') or llm_supplier_tax_id,
                'address': selected.get('address') or supplier.get('address') or '',
                'city': selected.get('city') or supplier.get('city') or '',
                'postal_code': selected.get('postal_code') or supplier.get('postal_code') or '',
                'match_score': selected_score,
                'matched_by': selected.get('matched_by') or '',
            })
        else:
            supplier['match_score'] = selected_score
            supplier['matched_by'] = ''
    elif auto_matched:
        supplier.update({
            'supplier_no': selected.get('no'),
            'estab': selected.get('estab') or 0,
            'name': selected.get('name') or llm_supplier_name,
            'short_name': selected.get('short_name') or '',
            'tax_id': selected.get('tax_id') or llm_supplier_tax_id,
            'address': selected.get('address') or supplier.get('address') or '',
            'city': selected.get('city') or supplier.get('city') or '',
            'postal_code': selected.get('postal_code') or supplier.get('postal_code') or '',
            'feid': selected.get('feid') or feid,
            'match_score': selected_score,
            'matched_by': selected.get('matched_by') or '',
        })
    else:
        supplier['supplier_no'] = None
        supplier['feid'] = feid or None
        supplier['match_score'] = selected_score
        supplier['matched_by'] = ''
    result['supplier'] = supplier

    return {
        'document': result,
        'matching': {
            'customer_matched': bool(customer_match.get('feid')),
            'customer': customer_match,
            'supplier_matched': auto_matched,
            'supplier_needs_selection': bool(feid and not auto_matched),
            'supplier_candidates': candidates,
            'supplier_lookup_error': supplier_lookup_error,
            'supplier_query': {
                'name': llm_supplier_name,
                'tax_id': llm_supplier_tax_id,
                'feid': feid or None,
                'source': str(selected.get('source') or ''),
                'tax_field': str(selected.get('tax_field') or ''),
            },
        },
    }


DOC_AI_PHC_PURCHASE_FLOW = [
    {'key': 'purchase_order', 'label': 'Nota de Encomenda', 'ndos': 102, 'order': 1},
    {'key': 'delivery_note', 'label': 'Guia de Remessa', 'ndos': 130, 'order': 2},
    {'key': 'proforma_invoice', 'label': 'Pré-Fatura', 'ndos': 218, 'order': 3},
    {'key': 'invoice', 'label': 'Fatura', 'table': 'FO', 'order': 4},
]

DOC_AI_INTEGRATION_ACCESS_TYPES = [
    ('purchase_order', 'Nota de Encomenda', 'PURCHASE_ORDER'),
    ('delivery_note', 'Guia de Remessa', 'DELIVERY_NOTE'),
    ('proforma_invoice', 'Pré-Fatura', 'PROFORMA_INVOICE'),
    ('provisional_invoice', 'Fatura Provisória', 'PROVISIONAL_INVOICE'),
    ('invoice', 'Fatura', 'INVOICE'),
    ('correspondence', 'Correspondência', 'CORRESPONDENCE'),
]


def _normalize_document_integration_access(payload: dict[str, Any] | None) -> dict[str, bool]:
    source = dict(payload or {})
    return {
        key: str(source.get(key, '')).strip().lower() in {'1', 'true', 'yes', 'on'}
        if not isinstance(source.get(key), bool) else source[key]
        for key, _label, _column in DOC_AI_INTEGRATION_ACCESS_TYPES
    }


def list_document_integration_access_users(query: str = '', limit: int = 30) -> list[dict[str, Any]]:
    _ensure_document_ai_schema()
    clean_query = str(query or '').strip()
    safe_limit = max(1, min(_safe_int(limit, 30), 60))
    like_query = f'%{clean_query}%'
    permission_columns = ', '.join(
        f'ISNULL(A.{column}, 0) AS {column}'
        for _key, _label, column in DOC_AI_INTEGRATION_ACCESS_TYPES
    )
    rows = db.session.execute(text(f"""
        SELECT TOP ({safe_limit})
            LTRIM(RTRIM(ISNULL(U.LOGIN, ''))) AS LOGIN,
            LTRIM(RTRIM(ISNULL(U.NOME, ''))) AS NOME,
            LTRIM(RTRIM(ISNULL(U.EMAIL, ''))) AS EMAIL,
            {permission_columns}
        FROM dbo.US U
        LEFT JOIN dbo.DOC_AI_INTEGRATION_ACCESS A
          ON A.LOGIN = U.LOGIN
        WHERE LTRIM(RTRIM(ISNULL(U.LOGIN, ''))) <> ''
          AND (
              :query = ''
              OR U.LOGIN LIKE :like_query
              OR U.NOME LIKE :like_query
              OR U.EMAIL LIKE :like_query
          )
        ORDER BY U.NOME, U.LOGIN
    """), {'query': clean_query, 'like_query': like_query}).mappings().all()
    results = []
    for row in rows:
        item = dict(row)
        results.append({
            'login': str(item.get('LOGIN') or '').strip(),
            'name': str(item.get('NOME') or '').strip(),
            'email': str(item.get('EMAIL') or '').strip(),
            'permissions': {
                key: bool(item.get(column))
                for key, _label, column in DOC_AI_INTEGRATION_ACCESS_TYPES
            },
        })
    return results


def save_document_integration_access(
    login: str,
    permissions: dict[str, Any] | None,
    requested_by: str,
) -> dict[str, Any]:
    _ensure_document_ai_schema()
    clean_login = str(login or '').strip()
    if not clean_login:
        raise ValueError('Seleciona um utilizador.')
    user = db.session.execute(text("""
        SELECT TOP 1 LTRIM(RTRIM(ISNULL(LOGIN, ''))) LOGIN,
            LTRIM(RTRIM(ISNULL(NOME, ''))) NOME
        FROM dbo.US WHERE LOGIN = :login
    """), {'login': clean_login}).mappings().first()
    if not user:
        raise ValueError('O utilizador selecionado já não existe.')
    normalized = _normalize_document_integration_access(permissions)
    columns = {column: 1 if normalized[key] else 0 for key, _label, column in DOC_AI_INTEGRATION_ACCESS_TYPES}
    assignments = ', '.join(f'{column} = :{column}' for column in columns)
    insert_columns = ', '.join(columns)
    insert_values = ', '.join(f':{column}' for column in columns)
    params = {
        'stamp': _new_stamp(), 'login': clean_login, 'requested_by': requested_by or '',
        **columns,
    }
    db.session.execute(text(f"""
        IF EXISTS (SELECT 1 FROM dbo.DOC_AI_INTEGRATION_ACCESS WHERE LOGIN = :login)
        BEGIN
            UPDATE dbo.DOC_AI_INTEGRATION_ACCESS
               SET {assignments}, DTALT = GETDATE(), USERALTERACAO = :requested_by
             WHERE LOGIN = :login;
        END
        ELSE
        BEGIN
            INSERT INTO dbo.DOC_AI_INTEGRATION_ACCESS (
                DOCACCESSSTAMP, LOGIN, {insert_columns}, DTCRI, USERCRIACAO, USERALTERACAO
            ) VALUES (
                :stamp, :login, {insert_values}, GETDATE(), :requested_by, :requested_by
            );
        END
    """), params)
    db.session.commit()
    return {
        'ok': True,
        'message': 'Acessos de integração atualizados.',
        'user': {'login': clean_login, 'name': str(user.get('NOME') or '').strip()},
        'permissions': normalized,
    }


def get_document_integration_access(login: str) -> dict[str, bool]:
    _ensure_document_ai_schema()
    clean_login = str(login or '').strip()
    if not clean_login:
        return _normalize_document_integration_access({})
    columns = ', '.join(
        f'ISNULL({column}, 0) AS {column}'
        for _key, _label, column in DOC_AI_INTEGRATION_ACCESS_TYPES
    )
    row = db.session.execute(text(f"""
        SELECT TOP 1 {columns}
        FROM dbo.DOC_AI_INTEGRATION_ACCESS
        WHERE LOGIN = :login
    """), {'login': clean_login}).mappings().first() or {}
    return {
        key: bool(row.get(column))
        for key, _label, column in DOC_AI_INTEGRATION_ACCESS_TYPES
    }


def document_integration_access_enabled(login: str, document_type: str) -> bool:
    clean_type = str(document_type or '').strip().lower()
    if clean_type not in {key for key, _label, _column in DOC_AI_INTEGRATION_ACCESS_TYPES}:
        return False
    return bool(get_document_integration_access(login).get(clean_type))


def _phc_contract_flow_stages(cursor) -> list[dict[str, Any]]:
    rows = cursor.execute("""
        SELECT CAST(ISNULL(NDOS, 0) AS int), LTRIM(RTRIM(ISNULL(NMDOS, '')))
        FROM dbo.TS WITH (NOLOCK)
        WHERE LOWER(LTRIM(RTRIM(ISNULL(NMDOS, '')))) LIKE '%contrat%'
           OR LOWER(LTRIM(RTRIM(ISNULL(NMDOS, '')))) LIKE '%situation%trav%st%'
        ORDER BY ISNULL(NDOS, 0)
    """).fetchall()
    stages = []
    seen = set()
    for row in rows:
        ndos = _safe_int(row[0], 0)
        label = str(row[1] or '').strip()
        if not ndos or ndos in seen or not label:
            continue
        seen.add(ndos)
        normalized_label = _normalize_text(label)
        is_work_situation = 'situation' in normalized_label and 'trav' in normalized_label and 'st' in normalized_label.split()
        is_subcontract = 'sous traitant' in normalized_label or 'sout traitant' in normalized_label
        stages.append({
            'key': 'subcontract_measurement' if is_work_situation else ('subcontract_contract' if is_subcontract else 'contract'),
            'document_type': 'work_situation' if is_work_situation else ('subcontract' if is_subcontract else 'contract'),
            'origin_family': 'work_situation' if is_work_situation else ('subcontract' if is_subcontract else 'contract'),
            'label': label,
            'ndos': ndos,
            'order': 3 if is_work_situation else (2 if is_subcontract else 1),
        })
    return stages


def _phc_origin_family(origin: dict[str, Any] | None) -> str:
    candidate = dict(origin or {})
    document_type = str(candidate.get('document_type') or '').strip().lower()
    key = str(candidate.get('key') or candidate.get('stage_key') or '').strip().lower()
    ndos = _safe_int(candidate.get('ndos'), 0)
    if document_type == 'purchase_order' or key == 'purchase_order' or ndos == 102:
        return 'bc'
    if document_type == 'delivery_note' or key == 'delivery_note' or ndos == 130:
        return 'delivery_note'
    if document_type == 'work_situation' or key == 'subcontract_measurement' or ndos == 129:
        return 'work_situation'
    if document_type == 'subcontract' or key == 'subcontract_contract' or ndos == 128:
        return 'subcontract'
    if document_type == 'contract' or key == 'contract' or ndos == 119:
        return 'contract'
    return ''


def _validate_phc_origin_combination(origins: list[dict[str, Any]], candidate: dict[str, Any]) -> None:
    family = _phc_origin_family(candidate)
    primary_families = {'bc', 'contract', 'subcontract'}
    existing_primary = [item for item in origins if _phc_origin_family(item) in primary_families]
    existing_family = _phc_origin_family(existing_primary[0]) if existing_primary else ''

    if family in primary_families:
        if existing_family and existing_family != family:
            raise ValueError('Retira a origem associada antes de mudar de família.')
        if family in {'contract', 'subcontract'} and existing_primary:
            raise ValueError('Contrato associado.')
        return
    if family == 'delivery_note' and existing_family != 'bc':
        raise ValueError('Associa primeiro uma Nota de Encomenda.')
    if family == 'work_situation':
        if existing_family != 'subcontract':
            raise ValueError('Associa primeiro um Contrato Sout-Traitant.')
        if any(_phc_origin_family(item) == 'work_situation' for item in origins):
            raise ValueError('Situação de Trabalho associada.')


def _document_date_value(value: Any) -> datetime:
    raw = str(value or '').strip()
    try:
        return datetime.fromisoformat(raw[:10])
    except Exception:
        return datetime.now()


def _configured_phc_sources() -> list[dict[str, Any]]:
    import pyodbc

    conn_map = current_app.config.get('DB_CONN_STRS') or {}
    conn_str = str(conn_map.get('client') or '').strip()
    if not conn_str:
        return []
    try:
        with pyodbc.connect(conn_str, timeout=10) as connection:
            cursor = connection.cursor()
            cursor.execute("""
                SELECT
                    ISNULL(FEID, 0) AS FEID,
                    LTRIM(RTRIM(ISNULL(NOME, ''))) AS NOME,
                    LTRIM(RTRIM(ISNULL(NOMEFISCAL, ''))) AS NOMEFISCAL,
                    LTRIM(RTRIM(CONVERT(varchar(40), ISNULL(NIF, 0)))) AS NIF,
                    LTRIM(RTRIM(ISNULL(PHC_DB, ''))) AS PHC_DB,
                    LTRIM(RTRIM(ISNULL(PHC_SERVER, ''))) AS PHC_SERVER
                FROM dbo.FE
                WHERE LTRIM(RTRIM(ISNULL(PHC_DB, ''))) <> ''
                  AND ISNULL(ATIVA, 1) = 1
                ORDER BY ISNULL(FEID, 0)
            """)
            columns = [str(item[0]).upper() for item in cursor.description or []]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception:
        current_app.logger.exception('Erro ao carregar empresas com PHC configurado para origens documentais')
        return []


def _phc_origin_source(customer: dict[str, Any]) -> dict[str, Any]:
    feid = _safe_int(customer.get('feid'), 0)
    if feid:
        try:
            current_source = _fe_supplier_source(feid)
            if current_source.get('kind') == 'phc':
                return current_source
        except Exception:
            current_app.logger.info('Configuração PHC não disponível na FE atual.', exc_info=True)

    customer_tax = _digits_only(customer.get('tax_id'))
    customer_name = _normalize_text(customer.get('name'))
    best = {}
    best_score = 0.0
    for source in _configured_phc_sources():
        source_tax = _digits_only(source.get('NIF'))
        source_names = [
            _normalize_text(source.get('NOMEFISCAL')),
            _normalize_text(source.get('NOME')),
        ]
        score = 0.0
        if customer_tax and source_tax and customer_tax == source_tax:
            score = 1.0
        if customer_name:
            for source_name in source_names:
                if not source_name:
                    continue
                ratio = SequenceMatcher(None, customer_name, source_name).ratio()
                if customer_name in source_name or source_name in customer_name:
                    ratio = max(ratio, 0.94)
                score = max(score, ratio)
        if feid and _safe_int(source.get('FEID'), 0) == feid:
            score = max(score, 1.0)
        if score > best_score:
            best_score = score
            best = source
    if not best or best_score < 0.62:
        return {}
    return {
        'kind': 'phc',
        'feid': _safe_int(best.get('FEID'), 0) or feid or None,
        'tax_field': 'ncont',
        'phc_db': str(best.get('PHC_DB') or '').strip(),
        'phc_server': str(best.get('PHC_SERVER') or '').strip(),
        'company_name': str(best.get('NOMEFISCAL') or best.get('NOME') or '').strip(),
        'match_score': round(best_score, 4),
    }


def get_next_phc_correspondence_reference(
    customer_data: dict[str, Any] | None,
    year: int | str | None = None,
) -> dict[str, Any]:
    """Return the next annual incoming-correspondence reference for one PHC company.

    CR.REF is shared by every received document type in a company database and CR.ANO
    is the annual partition. This only previews the next value; the definitive value
    must be rechecked in the transaction that eventually creates the CR row.
    """
    import pyodbc
    from services.phc_user_import_service import _phc_conn_str

    customer = dict(customer_data or {})
    target_year = _safe_int(year, datetime.now().year)
    if target_year < 2000 or target_year > 2100:
        target_year = datetime.now().year

    source = _phc_origin_source(customer)
    database_name = str(source.get('phc_db') or '').strip()
    if source.get('kind') != 'phc' or not database_name:
        raise ValueError('A entidade selecionada não tem uma base PHC configurada para consultar a correspondência.')

    with pyodbc.connect(
        _phc_conn_str(database_name, str(source.get('phc_server') or '').strip()),
        timeout=10,
    ) as connection:
        row = connection.cursor().execute("""
            SELECT ISNULL(MAX(CAST(ISNULL(REF, 0) AS bigint)), 0)
            FROM dbo.CR WITH (NOLOCK)
            WHERE CAST(ISNULL(ANO, 0) AS int) = ?
              AND ISNULL(ENVIADA, 0) = 0
        """, target_year).fetchone()

    last_reference = _safe_int(row[0] if row else 0, 0)
    return {
        'available': True,
        'reference': last_reference + 1,
        'last_reference': last_reference,
        'year': target_year,
        'feid': source.get('feid') or customer.get('feid'),
        'phc_database': database_name,
        'company_name': str(source.get('company_name') or customer.get('name') or '').strip(),
        'provisional': True,
    }


def _correspondence_safe_part(value: Any, fallback: str = '') -> str:
    cleaned = unicodedata.normalize('NFKC', str(value or ''))
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', '_', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip(' ._-').upper()
    return cleaned or fallback


def _phc_party_number(value: Any, establishment: Any = None) -> str:
    number = _safe_int(value, 0)
    if not number:
        return ''
    estab = _safe_int(establishment, 0)
    return f'{number}_{estab}' if estab > 0 else str(number)


def _correspondence_company_folder(customer: dict[str, Any], source: dict[str, Any]) -> str:
    explicit = _correspondence_safe_part(customer.get('ged_folder'), '')
    if explicit:
        return explicit
    return _ged_folder_from_phc_database(
        customer.get('phc_database') or source.get('phc_db')
    )


def _phc_correspondence_agency_origin(customer: dict[str, Any], source: dict[str, Any]) -> str:
    database_name = str(customer.get('phc_database') or source.get('phc_db') or '').strip().upper()
    if database_name != 'INTERSOL':
        return ''
    folder = _correspondence_company_folder(customer, source)
    return {
        'HSOLS_INTERSOL_AL': 'INTERSOL-ALSACE',
        'HSOLS_INTERSOL_LOR': 'INTERSOL-LORRAINE',
        'HSOLS_INTERSOL_CH': 'INTERSOL-CHAMPAGNE',
    }.get(folder, 'INTERSOL-ALSACE')


def _correspondence_month_folder(moment: datetime) -> str:
    months = ('JANV', 'FEV', 'MARS', 'AVR', 'MAI', 'JUIN', 'JUIL', 'AOUT', 'SEPT', 'OCT', 'NOV', 'DEC')
    return f'{moment.month} {months[moment.month - 1]} {str(moment.year)[-2:]}'


def _correspondence_file_name(
    document_data: dict[str, Any],
    reference: int,
    party: dict[str, Any],
) -> str:
    doc_type = str(document_data.get('document_type') or '').strip().lower()
    prefix = 'RB' if doc_type == 'bank_statement' else 'L'
    role = str(document_data.get('external_party_role') or '').strip().lower()
    party_number = _safe_int(
        party.get('customer_no') if role == 'customer' else party.get('supplier_no') or party.get('no'),
        0,
    )
    party_number_label = _phc_party_number(party_number, party.get('estab'))
    party_name = _correspondence_safe_part(party.get('short_name') or party.get('name2') or party.get('name') or party.get('llm_name'), 'REMETENTE')
    party_name = re.sub(r'\b(SARL|EURL|LDA|LIMITADA|SA|SAS|SPA|SL|SRL)\b[\s.,]*$', '', party_name, flags=re.IGNORECASE).strip() or 'REMETENTE'
    party_name = party_name[:60]
    title = _correspondence_safe_part(document_data.get('mail_title'), '')[:25]
    document_date = _safe_date_iso(document_data.get('document_date')) or date.today().isoformat()
    parts = [prefix, str(reference).zfill(3)]
    if role in {'customer', 'supplier'} and party_number_label:
        parts.append(party_number_label)
    parts.append(party_name)
    if title:
        parts.append(title)
    parts.append(document_date)
    return f"{'-'.join(filter(None, parts))}.pdf"


def _correspondence_type_config(document_type: Any) -> dict[str, str]:
    clean_type = str(document_type or '').strip().lower()
    if clean_type == 'bank_statement':
        return {'type': 'RB', 'folder': 'RB', 'label': 'relevé bancário'}
    return {'type': 'L', 'folder': 'LETTRE', 'label': 'correspondência'}


def _correspondence_ged_paths(
    document_data: dict[str, Any],
    source: dict[str, Any],
    reference: int,
    party: dict[str, Any],
    received_at: datetime,
) -> dict[str, str]:
    company_folder = _correspondence_company_folder(document_data.get('customer') or {}, source)
    if not company_folder:
        raise ValueError('Não foi possível determinar a pasta GED da entidade.')
    category = 'COURRIER_INTERNE_EXTERIEUR'
    inbox_folder = 'Courriers Reçus'
    file_name = _correspondence_file_name(document_data, reference, party)
    unc_root = str(
        current_app.config.get('PHC_GED_UNC_ROOT')
        or os.environ.get('PHC_GED_UNC_ROOT')
        or r'\\10.0.1.11\ged'
    ).strip().rstrip('\\/')
    relative_parts = (
        company_folder,
        category,
        inbox_folder,
        str(received_at.year),
        _correspondence_month_folder(received_at),
        file_name,
    )
    unc_path = '\\'.join((unc_root, *relative_parts))
    write_root = str(
        current_app.config.get('PHC_GED_WRITE_ROOT')
        or os.environ.get('PHC_GED_WRITE_ROOT')
        or ''
    ).strip()
    storage = 'local' if write_root or os.name == 'nt' else 'smb'
    write_path = os.path.join(write_root, *relative_parts) if write_root else unc_path
    return {
        'company_folder': company_folder,
        'category': category,
        'inbox_folder': inbox_folder,
        'file_name': file_name,
        'unc_path': unc_path,
        'write_path': write_path,
        'storage': storage,
    }


def _phc_table_columns(cursor, table_name: str) -> set[str]:
    rows = cursor.execute("""
        SELECT LOWER(COLUMN_NAME)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = ?
    """, str(table_name or '').strip()).fetchall()
    return {str(row[0] or '').strip().lower() for row in rows}


def _phc_insert_values(cursor, table_name: str, values: dict[str, Any]) -> None:
    columns = _phc_table_columns(cursor, table_name)
    filtered = {key: value for key, value in values.items() if key.lower() in columns}
    if not filtered:
        raise RuntimeError(f'Não existem colunas válidas para inserir em {table_name}.')
    cursor.execute(
        f"INSERT INTO dbo.{table_name} ({', '.join(filtered)}) VALUES ({', '.join('?' for _ in filtered)})",
        list(filtered.values()),
    )


def _phc_text_column_limit(cursor, table_name: str, column_name: str, fallback: int) -> int:
    try:
        row = cursor.execute("""
            SELECT CHARACTER_MAXIMUM_LENGTH
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'dbo' AND UPPER(TABLE_NAME) = UPPER(?)
              AND UPPER(COLUMN_NAME) = UPPER(?)
        """, table_name, column_name).fetchone()
        limit = _safe_int(row[0] if row else None, fallback)
        return limit if limit > 0 else fallback
    except Exception:
        return fallback


def _phc_correspondence_user(cursor, login: str) -> dict[str, Any]:
    clean_login = str(login or '').strip()
    row = cursor.execute("""
        SELECT TOP 1
            CAST(ISNULL(USERNO, 0) AS int),
            LTRIM(RTRIM(ISNULL(USERNAME, ''))),
            LTRIM(RTRIM(ISNULL(INICIAIS, ''))),
            LTRIM(RTRIM(ISNULL(USERCODE, '')))
        FROM dbo.US WITH (NOLOCK)
        WHERE LOWER(LTRIM(RTRIM(ISNULL(USERCODE, '')))) = LOWER(?)
           OR LOWER(LTRIM(RTRIM(ISNULL(EMAIL, '')))) = LOWER(?)
        ORDER BY CASE WHEN LOWER(LTRIM(RTRIM(ISNULL(USERCODE, '')))) = LOWER(?) THEN 0 ELSE 1 END
    """, clean_login, clean_login, clean_login).fetchone()
    if not row:
        return {'no': 0, 'name': clean_login, 'initials': clean_login[:3].upper(), 'code': clean_login}
    return {
        'no': _safe_int(row[0], 0),
        'name': str(row[1] or clean_login).strip(),
        'initials': str(row[2] or row[3] or clean_login).strip()[:3],
        'code': str(row[3] or clean_login).strip(),
    }


def _phc_correspondence_party(cursor, document_data: dict[str, Any]) -> dict[str, Any]:
    supplied = dict(document_data.get('supplier') or {})
    role = str(document_data.get('external_party_role') or '').strip().lower()
    table_name = 'CL' if role == 'customer' else ('FL' if role == 'supplier' else '')
    number = _safe_int(supplied.get('customer_no') if role == 'customer' else supplied.get('supplier_no') or supplied.get('no'), 0)
    estab = _safe_int(supplied.get('estab'), 0)
    if table_name and number:
        row = cursor.execute(
            f"SELECT TOP 1 CAST(ISNULL(NO, 0) AS int), LTRIM(RTRIM(ISNULL(NOME, ''))), CAST(ISNULL(ESTAB, 0) AS int), LTRIM(RTRIM(ISNULL(NOME2, ''))) FROM dbo.{table_name} WITH (NOLOCK) WHERE NO = ? AND ISNULL(ESTAB, 0) = ?",
            number, estab,
        ).fetchone()
        if not row:
            raise ValueError(f'O {"cliente" if table_name == "CL" else "fornecedor"} nº {number} já não existe no PHC.')
        return {'name': str(row[1] or '').strip()[:80], 'short_name': str(row[3] or '').strip()[:80], 'no': _safe_int(row[0], 0), 'estab': _safe_int(row[2], 0), 'origin': table_name, 'role': role}
    name = str(supplied.get('name') or supplied.get('llm_name') or '').strip()
    if not name:
        raise ValueError('Identifica ou escreve o nome do remetente antes de submeter.')
    return {'name': name[:80], 'no': 0, 'estab': 0, 'origin': 'CR', 'role': 'unknown'}


def submit_correspondence_to_phc(
    document_data: dict[str, Any] | None,
    file_bytes: bytes,
    original_file_name: str,
    requested_by: str,
) -> dict[str, Any]:
    import pyodbc
    from services.phc_user_import_service import _phc_conn_str

    document = dict(document_data or {})
    correspondence_type = str(document.get('document_type') or '').strip().lower()
    if correspondence_type not in {'mail', 'bank_statement'}:
        raise ValueError('Este circuito de submissão aceita apenas correspondência e relevés bancários.')
    if not file_bytes or not str(original_file_name or '').lower().endswith('.pdf'):
        raise ValueError('O PDF original é obrigatório para submeter a correspondência.')
    customer = dict(document.get('customer') or {})
    if not _safe_int(customer.get('feid'), 0):
        raise ValueError('Escolhe a entidade antes de submeter.')
    source = _phc_origin_source(customer)
    database_name = str(source.get('phc_db') or '').strip()
    if source.get('kind') != 'phc' or not database_name:
        raise ValueError('A entidade selecionada não tem uma base PHC configurada.')

    received_at = datetime.now()
    target_year = received_at.year
    content_hash = hashlib.sha256(file_bytes).hexdigest()
    unique_id = f'DOC_AI:{content_hash}'
    created_file = False
    write_path = ''
    connection = pyodbc.connect(
        _phc_conn_str(database_name, str(source.get('phc_server') or '').strip()),
        timeout=15,
        autocommit=False,
    )
    try:
        cursor = connection.cursor()
        cursor.execute('SET TRANSACTION ISOLATION LEVEL SERIALIZABLE')
        lock_result = cursor.execute("""
            DECLARE @result int;
            EXEC @result = sp_getapplock @Resource=?, @LockMode='Exclusive', @LockOwner='Transaction', @LockTimeout=15000;
            SELECT @result;
        """, f'DOC_AI_CR_{database_name}_{target_year}').fetchone()
        if not lock_result or _safe_int(lock_result[0], -999) < 0:
            raise RuntimeError('Não foi possível reservar a numeração da correspondência. Tenta novamente.')

        duplicate = cursor.execute("""
            SELECT TOP 1 C.CRSTAMP, C.REF, C.ANO, A.FULLNAME
            FROM dbo.ANEXOS A WITH (UPDLOCK, HOLDLOCK)
            INNER JOIN dbo.CR C ON C.CRSTAMP = A.RECSTAMP
            WHERE A.ORITABLE = 'CR' AND A.UNIQUEID = ?
            ORDER BY C.ANO DESC, C.REF DESC
        """, unique_id).fetchone()
        if duplicate:
            connection.rollback()
            return {
                'ok': True,
                'duplicate': True,
                'message': f'Este PDF já foi submetido como correspondência nº {_safe_int(duplicate[1], 0)}.',
                'crstamp': str(duplicate[0] or '').strip(),
                'reference': _safe_int(duplicate[1], 0),
                'year': _safe_int(duplicate[2], target_year),
                'phc_database': database_name,
                'ged_path': str(duplicate[3] or '').strip(),
            }

        row = cursor.execute("""
            SELECT ISNULL(MAX(CAST(ISNULL(REF, 0) AS bigint)), 0)
            FROM dbo.CR WITH (UPDLOCK, HOLDLOCK)
            WHERE CAST(ISNULL(ANO, 0) AS int) = ? AND ISNULL(ENVIADA, 0) = 0
        """, target_year).fetchone()
        reference = _safe_int(row[0] if row else 0, 0) + 1
        party = _phc_correspondence_party(cursor, document)
        user = _phc_correspondence_user(cursor, requested_by)
        type_config = _correspondence_type_config(correspondence_type)
        ged = _correspondence_ged_paths(document, source, reference, {**(document.get('supplier') or {}), **party}, received_at)
        write_path = ged['write_path']
        created_file = _write_document_ai_pdf(ged, file_bytes)

        now_time = received_at.strftime('%H:%M:%S')
        document_date = _document_date_value(document.get('document_date'))
        title = str(document.get('mail_title') or '').strip()[:80]
        subject = os.path.splitext(ged['file_name'])[0][:80]
        crstamp = _new_stamp()
        anexosstamp = _new_stamp()
        _phc_insert_values(cursor, 'CR', {
            'crstamp': crstamp,
            'data': document_date,
            'empresa': party['name'],
            'assunto': subject,
            'ref': reference,
            'obs': '',
            'refemp': title,
            'rdata': received_at,
            'entrada': received_at,
            'ano': target_year,
            'tipo': type_config['type'],
            'enviada': 0,
            'iniciais': '',
            'nenviada': 0,
            'no': party['no'],
            'estab': party['estab'],
            'origem': party['origin'],
            'ousrinis': user['initials'],
            'ousrdata': received_at,
            'ousrhora': now_time,
            'usrinis': user['initials'],
            'usrdata': received_at,
            'usrhora': now_time,
            'marcada': 0,
            'pasta': type_config['folder'],
            'wtwd': '',
            'wtwstamp': '',
            'intid': '',
            'u_origem': _phc_correspondence_agency_origin(customer, source),
        })
        attachment_origin = (
            f'{type_config["label"].capitalize()}\rData da correspondência: {document_date.strftime("%d.%m.%Y %H:%M:%S")}\r'
            f'Empresa: {party["name"]}\rAssunto: {subject}\rReferência: {reference:10d}\r'
            f'Observações: \rPasta: {type_config["folder"]}\r'
        )
        _phc_insert_values(cursor, 'ANEXOS', {
            'anexosstamp': anexosstamp,
            'oritable': 'CR',
            'tabnm': 'Correspondência',
            'resumo': type_config['type'],
            'grupo': '',
            'recstamp': crstamp,
            'uniqueid': unique_id,
            'descricao': title,
            'bdados': pyodbc.Binary(b''),
            'fullname': ged['unc_path'],
            'fname': os.path.splitext(ged['file_name'])[0][:150],
            'fext': 'pdf',
            'flen': 0,
            'tipo': 2,
            'passw': '',
            'origem': attachment_origin,
            'keylook': '',
            'tpdos': 0,
            'tpdoc': 0,
            'ausrinis': user['initials'],
            'ausrdata': received_at,
            'ausrhora': now_time,
            'usnoopen': user['no'],
            'usnaopen': user['name'][:55],
            'u_enviado': 1,
            'ousrinis': user['initials'],
            'ousrdata': received_at,
            'ousrhora': now_time,
            'usrinis': user['initials'],
            'usrdata': received_at,
            'usrhora': now_time,
        })
        connection.commit()
        return {
            'ok': True,
            'duplicate': False,
            'message': f'{type_config["label"].capitalize()} nº {reference} criada no PHC.',
            'crstamp': crstamp,
            'anexosstamp': anexosstamp,
            'reference': reference,
            'year': target_year,
            'phc_database': database_name,
            'file_name': ged['file_name'],
            'ged_path': ged['unc_path'],
            'party': party,
        }
    except Exception:
        try:
            connection.rollback()
        finally:
            if created_file and write_path:
                try:
                    _remove_document_ai_pdf(ged)
                except Exception:
                    current_app.logger.warning('Não foi possível remover o PDF do GED após rollback: %s', write_path, exc_info=True)
        raise
    finally:
        connection.close()


DOC_AI_PROVISIONAL_ARTICLE_REF = 'Z.00.00.000.0000'
DOC_AI_PURCHASE_INVOICE_DOCCODE = 55
DOC_AI_PURCHASE_CREDIT_NOTE_DOCCODE = 3


def _is_provisional_purchase_source_type(value: Any) -> bool:
    return str(value or '').strip().lower() in {'invoice', 'provisional_invoice', 'credit_note'}


def _is_credit_note_source_type(value: Any) -> bool:
    return str(value or '').strip().lower() in {'credit_note'}


def _phc_provisional_purchase_doc_config(cursor, database_name: str, document_type: Any) -> dict[str, Any]:
    is_credit_note = _is_credit_note_source_type(document_type)
    doccode = DOC_AI_PURCHASE_CREDIT_NOTE_DOCCODE if is_credit_note else DOC_AI_PURCHASE_INVOICE_DOCCODE
    docname_row = cursor.execute("""
        SELECT TOP 1 LTRIM(RTRIM(ISNULL(DOCNOME, '')))
        FROM dbo.FO WITH (NOLOCK)
        WHERE DOCCODE = ? AND ISNULL(DOCNOME, '') <> ''
        ORDER BY DATA DESC
    """, doccode).fetchone()
    docname = str(docname_row[0] or '').strip() if docname_row else ''
    clean_database = str(database_name or '').strip().upper()
    if not docname:
        if is_credit_note:
            docname = 'V/Nt. Crédito' if clean_database in {'HSOLS_PT', 'GR360'} else 'V/Avoir'
        else:
            docname = 'V/Fatura' if clean_database in {'HSOLS_PT', 'GR360'} else 'V/Facture'
    return {
        'is_credit_note': is_credit_note,
        'doccode': doccode,
        'docname': docname,
        'file_prefix': 'NC' if is_credit_note else 'FAC',
        'correspondence_type': DOC_AI_PURCHASE_CREDIT_NOTE_CORRESPONDENCE_TYPE if is_credit_note else DOC_AI_PURCHASE_INVOICE_CORRESPONDENCE_TYPE,
        'label': 'nota de crédito' if is_credit_note else 'fatura',
        'phc_label': 'Nota de Crédito' if is_credit_note else 'Fatura Provisória',
    }


def _phc_provisional_effective_datetime(cursor, database_name: str, document_date: datetime, received_at: datetime) -> datetime:
    """Data operacional da compra provisória: data do documento, salvo mês PHC fechado.

    Primeiro tenta respeitar a data de fecho registada na empresa PHC. Quando
    essa data não existe/não é útil, pode ser indicada por configuração. Sem
    configuração, mantém-se a data do documento, evitando arquivar Julho em
    Agosto só porque o processamento ocorreu em Agosto.
    """
    closed_row = None
    try:
        closed_row = cursor.execute("""
            SELECT
                MAX(CASE WHEN ISNULL(DATAFECHO, '19000101') > '19000101' THEN DATAFECHO ELSE NULL END),
                MAX(CASE WHEN ISNULL(U_DTFECHO, '19000101') > '19000101' THEN U_DTFECHO ELSE NULL END)
            FROM dbo.E1 WITH (NOLOCK)
        """).fetchone()
    except Exception:
        closed_row = None
    closed_dates = [
        value for value in (closed_row or [])
        if isinstance(value, datetime) and value.date() > date(1900, 1, 1)
    ]
    if closed_dates:
        closed_until = max(closed_dates)
        if document_date.date() <= closed_until.date():
            if closed_until.month == 12:
                open_date = datetime(closed_until.year + 1, 1, 1)
            else:
                open_date = datetime(closed_until.year, closed_until.month + 1, 1)
            return open_date.replace(
                hour=received_at.hour,
                minute=received_at.minute,
                second=received_at.second,
                microsecond=received_at.microsecond,
            )

    clean_database = str(database_name or '').strip().upper()
    setting_names = [
        f'DOCUMENT_AI_PHC_OPEN_MONTH_{clean_database}',
        'DOCUMENT_AI_PHC_OPEN_MONTH',
    ]
    configured = ''
    for name in setting_names:
        configured = str(current_app.config.get(name) or os.environ.get(name) or '').strip()
        if configured:
            break
    open_month = re.match(r'^(\d{4})-(\d{1,2})$', configured)
    if not open_month:
        return document_date.replace(
            hour=received_at.hour,
            minute=received_at.minute,
            second=received_at.second,
            microsecond=received_at.microsecond,
        )
    open_year = _safe_int(open_month.group(1), document_date.year)
    open_month_number = max(1, min(_safe_int(open_month.group(2), document_date.month), 12))
    open_date = datetime(open_year, open_month_number, 1)
    current_month = datetime(document_date.year, document_date.month, 1)
    if current_month < open_date:
        return open_date.replace(
            hour=received_at.hour,
            minute=received_at.minute,
            second=received_at.second,
            microsecond=received_at.microsecond,
        )
    return document_date.replace(
        hour=received_at.hour,
        minute=received_at.minute,
        second=received_at.second,
        microsecond=received_at.microsecond,
    )


def _phc_money(value: Any) -> Decimal:
    parsed = _safe_decimal(value)
    return Decimal(str(parsed if parsed is not None else 0)).quantize(Decimal('0.01'))


def _split_phc_line_design(value: Any, width: int = 60) -> list[str]:
    clean_value = re.sub(r'\s+', ' ', str(value or '')).strip()
    if not clean_value:
        return ['']
    return textwrap.wrap(
        clean_value,
        width=max(1, int(width or 60)),
        break_long_words=True,
        break_on_hyphens=False,
        replace_whitespace=True,
        drop_whitespace=True,
    ) or ['']


def _expand_phc_invoice_lines(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    expanded = []
    line_order = 0
    for line in lines:
        chunks = _split_phc_line_design(line.get('description'), 60)
        for chunk_index, chunk in enumerate(chunks):
            line_order += 1000
            expanded.append({
                **line,
                'description': chunk,
                'continuation': chunk_index > 0,
                'lordem': line_order,
            })
    return expanded


def _phc_provisional_supplier(cursor, supplier_data: dict[str, Any]) -> dict[str, Any]:
    matched = _phc_origin_supplier(cursor, supplier_data)
    supplier_no = _safe_int(matched.get('no'), 0)
    supplier_estab = _safe_int(matched.get('estab'), 0)
    if not supplier_no:
        raise ValueError('Escolhe um fornecedor existente no PHC antes de submeter a Fatura Provisória.')
    row = cursor.execute("""
        SELECT TOP 1
            CAST(ISNULL(NO, 0) AS int), CAST(ISNULL(ESTAB, 0) AS int),
            LTRIM(RTRIM(ISNULL(NOME, ''))), LTRIM(RTRIM(ISNULL(NOME2, ''))),
            LTRIM(RTRIM(ISNULL(MORADA, ''))), LTRIM(RTRIM(ISNULL(LOCAL, ''))),
            LTRIM(RTRIM(ISNULL(CODPOST, ''))), LTRIM(RTRIM(CONVERT(varchar(40), ISNULL(NCONT, '')))),
            LTRIM(RTRIM(ISNULL(MOEDA, ''))), LTRIM(RTRIM(ISNULL(PAIS, ''))),
            LTRIM(RTRIM(ISNULL(TPSTAMP, ''))), LTRIM(RTRIM(ISNULL(TPDESC, ''))),
            LTRIM(RTRIM(ISNULL(LANG, ''))), LTRIM(RTRIM(ISNULL(CCUSTO, ''))),
            LTRIM(RTRIM(ISNULL(NCUSTO, '')))
        FROM dbo.FL WITH (UPDLOCK, HOLDLOCK)
        WHERE NO = ? AND ISNULL(ESTAB, 0) = ?
    """, supplier_no, supplier_estab).fetchone()
    if not row:
        raise ValueError(f'O fornecedor nº {supplier_no} já não existe no PHC.')
    keys = ('no', 'estab', 'name', 'name2', 'address', 'city', 'postal_code', 'tax_id',
            'currency', 'country', 'tpstamp', 'tpdesc', 'lang', 'ccusto', 'ncusto')
    return dict(zip(keys, row))


def _phc_tax_configuration(cursor) -> tuple[dict[int, Decimal], dict[Decimal, int]]:
    rows = cursor.execute("""
        SELECT CAST(ISNULL(CODIGO, 0) AS int), CAST(ISNULL(TAXA, 0) AS decimal(10, 4))
        FROM dbo.TAXASIVA WITH (NOLOCK)
        WHERE CAST(ISNULL(CODIGO, 0) AS int) BETWEEN 1 AND 9
        ORDER BY CAST(ISNULL(CODIGO, 0) AS int)
    """).fetchall()
    by_code = {int(row[0]): Decimal(str(row[1])).quantize(Decimal('0.01')) for row in rows}
    # Algumas bases conservam tabelas antigas com a mesma percentagem. O PHC
    # usa a primeira tabela configurada (por exemplo, tabela 2 para IVA a 20%)
    # e não a última ocorrência da taxa.
    by_rate: dict[Decimal, int] = {}
    for code, rate in by_code.items():
        by_rate.setdefault(rate, code)
    return by_code, by_rate


def _phc_tax_code(rate: Decimal, by_rate: dict[Decimal, int]) -> int:
    normalized = rate.quantize(Decimal('0.01'))
    if normalized in by_rate:
        return by_rate[normalized]
    if normalized == 0 and Decimal('0.00') in by_rate:
        return by_rate[Decimal('0.00')]
    raise ValueError(f'A taxa de IVA {normalized}% não está configurada na base PHC selecionada.')


def _phc_base_currency_per_euro(cursor) -> Decimal:
    """Obtém o fator moeda-base/EUR usado pela própria base PHC.

    As bases existentes guardam em paralelo os valores na moeda-base histórica
    e em euros. Usar documentos já calculados pelo PHC evita assumir que todas
    as empresas têm a mesma moeda-base.
    """
    rows = cursor.execute("""
        SELECT TOP 25
            CAST(ABS(TOTAL / NULLIF(ETOTAL, 0)) AS decimal(19, 6))
        FROM dbo.FO WITH (NOLOCK)
        WHERE ABS(ISNULL(ETOTAL, 0)) > 0.01
          AND ABS(ISNULL(TOTAL, 0)) > 0.01
          AND UPPER(LTRIM(RTRIM(ISNULL(MOEDA, '')))) IN ('EUR', 'EURO')
          AND ABS(TOTAL / NULLIF(ETOTAL, 0)) BETWEEN 0.01 AND 10000
        ORDER BY DATA DESC, OUSRDATA DESC
    """).fetchall()
    factors = sorted(Decimal(str(row[0])) for row in rows if row and row[0] is not None)
    if not factors:
        return Decimal('1.000000')
    middle = len(factors) // 2
    if len(factors) % 2:
        return factors[middle]
    return ((factors[middle - 1] + factors[middle]) / Decimal('2')).quantize(Decimal('0.000001'))


def _phc_local_amount(value: Decimal, factor: Decimal, *, whole: bool = False) -> Decimal:
    quantum = Decimal('1') if whole else Decimal('0.00001')
    return (value * factor).quantize(quantum)


def _ensure_phc_provisional_article(cursor, requested_by: str, moment: datetime) -> dict[str, Any]:
    row = cursor.execute("""
        SELECT TOP 1 STSTAMP, LTRIM(RTRIM(ISNULL(REF, ''))), LTRIM(RTRIM(ISNULL(DESIGN, '')))
        FROM dbo.ST WITH (UPDLOCK, HOLDLOCK)
        WHERE LTRIM(RTRIM(REF)) = ?
    """, DOC_AI_PROVISIONAL_ARTICLE_REF).fetchone()
    if row:
        return {'stamp': str(row[0] or '').strip(), 'ref': str(row[1] or '').strip(), 'design': str(row[2] or '').strip()}
    initials = str(requested_by or 'DOC')[:3].upper()
    stamp = _new_stamp()
    _phc_insert_values(cursor, 'ST', {
        'ststamp': stamp,
        'ref': DOC_AI_PROVISIONAL_ARTICLE_REF,
        'design': 'ARTIGO GENÉRICO - DOCUMENT AI',
        'familia': '',
        'stock': 0,
        'unidade': 'UN',
        'tabiva': 5,
        'usaid': 1,
        'stns': 1,
        'sujinv': 0,
        'inactivo': 0,
        'ousrinis': initials,
        'ousrdata': moment,
        'ousrhora': moment.strftime('%H:%M:%S'),
        'usrinis': initials,
        'usrdata': moment,
        'usrhora': moment.strftime('%H:%M:%S'),
        'marcada': 0,
    })
    return {'stamp': stamp, 'ref': DOC_AI_PROVISIONAL_ARTICLE_REF, 'design': 'ARTIGO GENÉRICO - DOCUMENT AI'}


def _provisional_invoice_ged_paths(
    document: dict[str, Any],
    source: dict[str, Any],
    supplier: dict[str, Any],
    reference: int,
    document_date: datetime,
    file_prefix: str = 'FAC',
) -> list[dict[str, str]]:
    company_folder = _correspondence_company_folder(document.get('customer') or {}, source)
    if not company_folder:
        raise ValueError('Não foi possível determinar a pasta GED da entidade.')
    supplier_name = _correspondence_safe_part(supplier.get('short_name') or supplier.get('name2') or supplier.get('name'), 'FORNECEDOR')[:55]
    document_number = _correspondence_safe_part(document.get('document_number'), 'SEM-DOCUMENTO')[:45]
    supplier_number = _phc_party_number(supplier.get('no'), supplier.get('estab'))
    clean_prefix = _correspondence_safe_part(file_prefix, 'FAC')[:12]
    file_name = f'{clean_prefix}-{str(reference).zfill(3)}-{supplier_number}-{supplier_name}-{document_number}.pdf'
    unc_root = str(
        current_app.config.get('PHC_GED_UNC_ROOT')
        or os.environ.get('PHC_GED_UNC_ROOT')
        or r'\\10.0.1.11\ged'
    ).strip().rstrip('\\/')
    write_root = str(
        current_app.config.get('PHC_GED_WRITE_ROOT')
        or os.environ.get('PHC_GED_WRITE_ROOT')
        or ''
    ).strip()
    storage = 'local' if write_root or os.name == 'nt' else 'smb'
    results = []
    for key, label, category, subfolders in (
        ('correspondence', 'Correio recebido', 'COURRIER_INTERNE_EXTERIEUR', ('Courriers Reçus',)),
        ('purchase', 'Faturas de fornecedor', 'FACTURATION_FOURNISSEURS', ()),
    ):
        parts = (
            company_folder,
            category,
            *subfolders,
            str(document_date.year),
            _correspondence_month_folder(document_date),
            file_name,
        )
        unc_path = '\\'.join((unc_root, *parts))
        results.append({
            'key': key,
            'label': label,
            'file_name': file_name,
            'unc_path': unc_path,
            'write_path': os.path.join(write_root, *parts) if write_root else unc_path,
            'storage': storage,
        })
    return results


def _document_ai_smb_session(unc_path: str) -> None:
    try:
        import smbclient
    except ImportError as exc:
        raise RuntimeError('O cliente SMB necessário para escrever diretamente no servidor GED não está instalado.') from exc
    parts = [part for part in str(unc_path or '').lstrip('\\').split('\\') if part]
    if len(parts) < 2:
        raise ValueError('O caminho UNC do GED não é válido.')
    server = parts[0]
    username = str(
        current_app.config.get('PHC_GED_SMB_USER')
        or os.environ.get('PHC_GED_SMB_USER')
        or os.environ.get('DOCUMENT_AI_SMB_USER')
        or ''
    ).strip()
    password = str(
        current_app.config.get('PHC_GED_SMB_PASSWORD')
        or os.environ.get('PHC_GED_SMB_PASSWORD')
        or os.environ.get('DOCUMENT_AI_SMB_PASSWORD')
        or ''
    )
    domain = str(
        current_app.config.get('PHC_GED_SMB_DOMAIN')
        or os.environ.get('PHC_GED_SMB_DOMAIN')
        or os.environ.get('DOCUMENT_AI_SMB_DOMAIN')
        or ''
    ).strip()
    if (not username or not password) and os.name != 'nt' and sys.platform == 'darwin':
        try:
            metadata_result = subprocess.run(
                ['security', 'find-generic-password', '-s', 'APP_WEB_PHC_GED_SMB'],
                check=True, capture_output=True, text=True,
            )
            metadata = f'{metadata_result.stdout}\n{metadata_result.stderr}'
            secret = subprocess.run(
                ['security', 'find-generic-password', '-s', 'APP_WEB_PHC_GED_SMB', '-w'],
                check=True, capture_output=True, text=True,
            ).stdout.rstrip('\r\n')
            account_hex = re.search(r'"acct"<blob>=0x([0-9A-Fa-f]+)', metadata)
            account_text = re.search(r'"acct"<blob>="([^"]+)"', metadata)
            account = ''
            if account_hex:
                account = bytes.fromhex(account_hex.group(1)).decode('utf-8')
            elif account_text:
                account = account_text.group(1)
            if account and secret:
                username = account
                password = secret
        except Exception:
            pass
    if domain and username and '\\' not in username and '@' not in username:
        username = f'{domain}\\{username}'
    try:
        smbclient.register_session(
            server,
            username=username or None,
            password=password or None,
            connection_timeout=15,
        )
    except Exception as exc:
        hint = (
            'Configura PHC_GED_SMB_USER e PHC_GED_SMB_PASSWORD no serviço da aplicação.'
            if not username or not password else
            'Confirma as credenciais SMB configuradas para o serviço da aplicação.'
        )
        raise RuntimeError(f'Não foi possível autenticar diretamente no servidor GED {server}. {hint}') from exc


def _document_ai_file_digest(handle) -> bytes:
    digest = hashlib.sha256()
    while True:
        chunk = handle.read(1024 * 1024)
        if not chunk:
            break
        digest.update(chunk)
    return digest.digest()


def _write_document_ai_pdf(target: dict[str, str], file_bytes: bytes) -> bool:
    write_path = target['write_path']
    if target.get('storage') == 'smb':
        import smbclient
        unc_path = target['unc_path']
        _document_ai_smb_session(unc_path)
        parent = ntpath.dirname(unc_path)
        smbclient.makedirs(parent, exist_ok=True)
        expected_digest = hashlib.sha256(file_bytes).digest()
        if smbclient.path.exists(unc_path):
            with smbclient.open_file(unc_path, mode='rb') as existing_file:
                if _document_ai_file_digest(existing_file) != expected_digest:
                    raise FileExistsError(f'Já existe no GED um ficheiro diferente com o nome {target["file_name"]}.')
            return False
        temporary_path = f'{unc_path}.docai-{uuid.uuid4().hex}.tmp'
        try:
            with smbclient.open_file(temporary_path, mode='wb') as handle:
                handle.write(file_bytes)
            smbclient.replace(temporary_path, unc_path)
            return True
        finally:
            if smbclient.path.exists(temporary_path):
                smbclient.remove(temporary_path)
    os.makedirs(os.path.dirname(write_path), exist_ok=True)
    if os.path.exists(write_path):
        with open(write_path, 'rb') as existing_file:
            if hashlib.sha256(existing_file.read()).digest() != hashlib.sha256(file_bytes).digest():
                raise FileExistsError(f'Já existe no GED um ficheiro diferente com o nome {target["file_name"]}.')
        return False
    descriptor, temporary_path = tempfile.mkstemp(prefix='.docai-', suffix='.tmp', dir=os.path.dirname(write_path))
    try:
        with os.fdopen(descriptor, 'wb') as handle:
            handle.write(file_bytes)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, write_path)
        return True
    finally:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)


def _remove_document_ai_pdf(target: dict[str, str]) -> None:
    if target.get('storage') == 'smb':
        import smbclient
        _document_ai_smb_session(target['unc_path'])
        if smbclient.path.exists(target['unc_path']):
            smbclient.remove(target['unc_path'])
        return
    if os.path.exists(target['write_path']):
        os.remove(target['write_path'])


def _document_ai_find_app_users(search_terms: list[str]) -> list[dict[str, Any]]:
    terms = []
    for term in search_terms:
        clean = str(term or '').strip()
        if clean and clean not in terms:
            terms.append(clean)
    if not terms:
        return []
    clauses = []
    params: dict[str, Any] = {}
    for index, term in enumerate(terms):
        key = f'term_{index}'
        like_key = f'like_{index}'
        params[key] = term.lower()
        params[like_key] = f'%{term.lower()}%'
        clauses.append(
            f"LOWER(LTRIM(RTRIM(ISNULL(LOGIN, '')))) = :{key} "
            f"OR LOWER(LTRIM(RTRIM(ISNULL(EMAIL, '')))) = :{key} "
            f"OR LOWER(LTRIM(RTRIM(ISNULL(NOME, '')))) LIKE :{like_key} "
            f"OR LOWER(LTRIM(RTRIM(ISNULL(LOGIN, '')))) LIKE :{like_key}"
        )
    rows = db.session.execute(text(f"""
        SELECT USSTAMP, LOGIN, NOME, EMAIL
        FROM dbo.US WITH (NOLOCK)
        WHERE ISNULL(INATIVO, 0) = 0
          AND ISNULL(IS_ACTIVE, 1) = 1
          AND ({' OR '.join(f'({clause})' for clause in clauses)})
    """), params).mappings().all()
    return [dict(row) for row in rows]


def _document_ai_userstamp_from_value(value: Any) -> str:
    clean = str(value or '').strip()
    if not clean:
        return ''
    row = db.session.execute(text("""
        SELECT TOP 1 USSTAMP
        FROM dbo.US WITH (NOLOCK)
        WHERE ISNULL(INATIVO, 0) = 0
          AND ISNULL(IS_ACTIVE, 1) = 1
          AND (
              LOWER(LTRIM(RTRIM(ISNULL(USSTAMP, '')))) = LOWER(:value)
              OR LOWER(LTRIM(RTRIM(ISNULL(LOGIN, '')))) = LOWER(:value)
              OR LOWER(LTRIM(RTRIM(ISNULL(EMAIL, '')))) = LOWER(:value)
              OR LOWER(LTRIM(RTRIM(ISNULL(NOME, '')))) = LOWER(:value)
              OR LTRIM(RTRIM(CAST(ISNULL(PENO, 0) AS varchar(20)))) = :value
          )
    """), {'value': clean}).mappings().first()
    return str(row.get('USSTAMP') or '').strip() if row else ''


def _document_ai_accounting_responsible_userstamp(customer: dict[str, Any]) -> str:
    feid = _safe_int(customer.get('feid') or customer.get('FEID'), 0)
    if not feid:
        return ''
    try:
        columns = [str(row[0] or '').strip() for row in db.session.execute(text("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'FE'
        """)).fetchall()]
        wanted = {
            'respcontab', 'resp_contab', 'responsavelcontabilidade', 'responsavel_contabilidade',
            'contabilidade', 'contabilista', 'usercontab', 'user_contab', 'uscontab', 'u_contab',
            'peno', 'contab_user', 'accounting_user', 'accounting_responsible',
        }
        candidates = [column for column in columns if _normalize_text(column).replace(' ', '_') in wanted]
        for column in candidates:
            row = db.session.execute(text(f"""
                SELECT TOP 1 LTRIM(RTRIM(CAST(ISNULL([{column}], '') AS varchar(255)))) AS VALUE
                FROM dbo.FE WITH (NOLOCK)
                WHERE FEID = :feid
            """), {'feid': feid}).mappings().first()
            userstamp = _document_ai_userstamp_from_value(row.get('VALUE') if row else '')
            if userstamp:
                return userstamp
    except Exception:
        current_app.logger.info('Não foi possível identificar responsável contabilístico da FE %s.', feid, exc_info=True)
    return ''


def _document_ai_provisional_alert_recipients(customer: dict[str, Any]) -> list[str]:
    fixed_users = _document_ai_find_app_users([
        'António Rocha',
        'Mickael Silva',
        'Mickaël Silva',
        'António Guimarães',
        'António Cruz',
    ])
    recipients = [str(row.get('USSTAMP') or '').strip() for row in fixed_users]
    accounting_userstamp = _document_ai_accounting_responsible_userstamp(customer)
    if accounting_userstamp:
        recipients.append(accounting_userstamp)
    seen: set[str] = set()
    result = []
    for userstamp in recipients:
        if userstamp and userstamp not in seen:
            seen.add(userstamp)
            result.append(userstamp)
    return result


def _notify_document_ai_provisional_created(result: dict[str, Any], document: dict[str, Any], supplier: dict[str, Any], requested_by: str) -> None:
    try:
        from services.push_service import send_push_to_user

        customer = dict(document.get('customer') or {})
        recipients = _document_ai_provisional_alert_recipients(customer)
        if not recipients:
            current_app.logger.info('Document AI: provisória criada sem destinatários de alerta configurados.')
            return
        sender = _document_ai_userstamp_from_value(requested_by)
        document_type = str(document.get('document_type') or '').strip().lower()
        title = 'Avoir provisório criado' if _is_credit_note_source_type(document_type) else 'Fatura provisória criada'
        number = str(result.get('document_number') or document.get('document_number') or '').strip()
        database_name = str(result.get('phc_database') or '').strip()
        supplier_name = str(supplier.get('name') or supplier.get('name2') or '').strip()
        body = ' · '.join(part for part in [number, supplier_name, database_name] if part)[:240]
        for userstamp in recipients:
            send_push_to_user(
                userstamp,
                title,
                body or 'Documento criado pela Leitura Inteligente.',
                url='/document_ai/inbox',
                event_type='DOCUMENT_AI_PROVISIONAL_CREATED',
                sent_by_userstamp=sender,
            )
    except Exception:
        current_app.logger.warning('Falhou envio de alerta Document AI após criação de provisória.', exc_info=True)


def submit_provisional_invoice_to_phc(
    document_data: dict[str, Any] | None,
    file_bytes: bytes,
    original_file_name: str,
    requested_by: str,
) -> dict[str, Any]:
    import pyodbc
    from services.phc_user_import_service import _phc_conn_str

    document = dict(document_data or {})
    if not _is_provisional_purchase_source_type(document.get('document_type')):
        raise ValueError('Este circuito aceita apenas faturas ou notas de crédito de fornecedor para lançar no PHC.')
    if not file_bytes or not str(original_file_name or '').lower().endswith('.pdf'):
        raise ValueError('O PDF original é obrigatório para submeter a Fatura Provisória.')
    document_number = str(document.get('document_number') or '').strip()
    if not document_number:
        raise ValueError('Confirma o número da Fatura Provisória antes de submeter.')
    lines = [dict(item or {}) for item in (document.get('lines') or []) if isinstance(item, dict)]
    if not lines:
        raise ValueError('A Fatura Provisória tem de ter pelo menos uma linha.')
    customer = dict(document.get('customer') or {})
    if not _safe_int(customer.get('feid'), 0):
        raise ValueError('Escolhe a entidade antes de submeter.')
    source = _phc_origin_source(customer)
    database_name = str(source.get('phc_db') or '').strip()
    if source.get('kind') != 'phc' or not database_name:
        raise ValueError('A entidade selecionada não tem uma base PHC configurada.')

    received_at = datetime.now()
    document_date = _document_date_value(document.get('document_date'))
    due_date = _document_date_value(document.get('due_date') or document.get('document_date'))
    unique_root = f'DOC_AI:{hashlib.sha256(file_bytes).hexdigest()}'
    created_paths: list[str] = []
    ged_targets: list[dict[str, str]] = []
    connection = pyodbc.connect(
        _phc_conn_str(database_name, str(source.get('phc_server') or '').strip()),
        timeout=15,
        autocommit=False,
    )
    try:
        cursor = connection.cursor()
        doc_config = _phc_provisional_purchase_doc_config(cursor, database_name, document.get('document_type'))
        effective_at = _phc_provisional_effective_datetime(cursor, database_name, document_date, received_at)
        year = effective_at.year
        cursor.execute('SET TRANSACTION ISOLATION LEVEL SERIALIZABLE')
        lock = cursor.execute("""
            DECLARE @result int;
            EXEC @result = sp_getapplock @Resource=?, @LockMode='Exclusive', @LockOwner='Transaction', @LockTimeout=15000;
            SELECT @result;
        """, f'DOC_AI_PP_{database_name}_{doc_config["doccode"]}_{year}_{_normalize_text(document_number)}').fetchone()
        if not lock or _safe_int(lock[0], -999) < 0:
            raise RuntimeError('Não foi possível reservar a integração deste documento provisório. Tenta novamente.')

        supplier = _phc_provisional_supplier(cursor, dict(document.get('supplier') or {}))
        duplicate = cursor.execute("""
            SELECT TOP 1 F.FOSTAMP, F.ADOC, A.FULLNAME
            FROM dbo.FO F WITH (UPDLOCK, HOLDLOCK)
            LEFT JOIN dbo.ANEXOS A ON A.RECSTAMP = F.FOSTAMP AND A.ORITABLE = 'FO'
            WHERE F.DOCCODE = ? AND F.NO = ?
              AND (A.UNIQUEID = ? OR LTRIM(RTRIM(F.ADOC)) = ?)
            ORDER BY F.DATA DESC
        """, doc_config['doccode'], supplier['no'], f'{unique_root}:FO', document_number).fetchone()
        if duplicate:
            correspondence = cursor.execute("""
                SELECT TOP 1 C.CRSTAMP, C.REF, C.ANO
                FROM dbo.ANEXOS A WITH (UPDLOCK, HOLDLOCK)
                INNER JOIN dbo.CR C ON C.CRSTAMP = A.RECSTAMP
                WHERE A.ORITABLE = 'CR' AND A.UNIQUEID = ?
                ORDER BY C.ANO DESC, C.REF DESC
            """, f'{unique_root}:CR').fetchone()
            connection.rollback()
            return {
                'ok': True,
                'duplicate': True,
                'message': f'O documento {document_number} deste fornecedor já existe no PHC como {doc_config["docname"]}.',
                'fostamp': str(duplicate[0] or '').strip(),
                'crstamp': str(correspondence[0] or '').strip() if correspondence else '',
                'reference': _safe_int(correspondence[1], 0) if correspondence else 0,
                'year': _safe_int(correspondence[2], datetime.now().year) if correspondence else datetime.now().year,
                'document_number': str(duplicate[1] or '').strip(),
                'phc_database': database_name,
                'ged_path': str(duplicate[2] or '').strip(),
            }

        reference_row = cursor.execute("""
            SELECT ISNULL(MAX(CAST(ISNULL(REF, 0) AS bigint)), 0)
            FROM dbo.CR WITH (UPDLOCK, HOLDLOCK)
            WHERE CAST(ISNULL(ANO, 0) AS int) = ? AND ISNULL(ENVIADA, 0) = 0
        """, year).fetchone()
        reference = _safe_int(reference_row[0] if reference_row else 0, 0) + 1
        user = _phc_correspondence_user(cursor, requested_by)
        article = _ensure_phc_provisional_article(cursor, requested_by, received_at)
        tax_by_code, tax_by_rate = _phc_tax_configuration(cursor)
        ged_targets = _provisional_invoice_ged_paths(document, source, supplier, reference, document_date, doc_config['file_prefix'])
        for target in ged_targets:
            if _write_document_ai_pdf(target, file_bytes):
                created_paths.append(target['write_path'])

        normalized_lines = []
        fn_unit_width = _phc_text_column_limit(cursor, 'FN', 'UNIDADE', 4)
        tax_groups: dict[int, dict[str, Decimal]] = {}
        for index, line in enumerate(lines, start=1):
            qty = _phc_money(line.get('qty'))
            if qty == 0:
                qty = Decimal('1.00')
            unit_price = _phc_money(line.get('unit_price'))
            discount = _phc_money(line.get('discount'))
            net = _phc_money(line.get('net_amount'))
            if net == 0 and unit_price != 0:
                net = (qty * unit_price * (Decimal('1.00') - discount / Decimal('100.00'))).quantize(Decimal('0.01'))
            rate = _phc_money(line.get('tax_rate'))
            code = _phc_tax_code(rate, tax_by_rate)
            tax_amount = (net * rate / Decimal('100.00')).quantize(Decimal('0.01'))
            group = tax_groups.setdefault(code, {'rate': rate, 'base': Decimal('0.00'), 'tax': Decimal('0.00')})
            group['base'] += net
            group['tax'] += tax_amount
            normalized_lines.append({
                'index': index,
                'description': str(line.get('description') or article['design']).strip(),
                'qty': qty,
                'unit': str(line.get('unit') or 'UN').strip()[:fn_unit_width],
                'unit_price': unit_price,
                'discount': discount,
                'net': net,
                'rate': rate,
                'code': code,
            })

        calculated_net = sum((item['net'] for item in normalized_lines), Decimal('0.00'))
        calculated_tax = sum((item['tax'] for item in tax_groups.values()), Decimal('0.00'))
        totals = dict(document.get('totals') or {})
        net_total = _phc_money(totals.get('net_total')) or calculated_net
        tax_total = _phc_money(totals.get('tax_total')) if totals.get('tax_total') not in (None, '') else calculated_tax
        gross_total = _phc_money(totals.get('gross_total')) or (net_total + tax_total)
        physical_lines = _expand_phc_invoice_lines(normalized_lines)
        project = dict(document.get('origin_project') or {})
        ccusto = str(project.get('ccusto') or supplier.get('ccusto') or '').strip()[:20]
        currency = str(document.get('currency') or supplier.get('currency') or 'EURO').strip().upper()[:11] or 'EURO'
        if currency in {'EUR', '€'}:
            currency = 'EURO'
        base_currency_factor = _phc_base_currency_per_euro(cursor) if currency == 'EURO' else Decimal('1.000000')
        local_net_total = _phc_local_amount(net_total, base_currency_factor)
        local_tax_total = _phc_local_amount(tax_total, base_currency_factor)
        local_gross_total = _phc_local_amount(gross_total, base_currency_factor)
        docname = doc_config['docname']
        initials = str(user.get('initials') or requested_by or 'DOC')[:3]
        time_text = received_at.strftime('%H:%M:%S')
        fostamp = _new_stamp()
        crstamp = _new_stamp()

        tax_header_values: dict[str, Decimal] = {}
        for code, values in tax_groups.items():
            local_tax = _phc_local_amount(values['tax'], base_currency_factor, whole=True)
            tax_header_values.update({
                f'ivav{code}': local_tax,
                f'eivav{code}': values['tax'],
                f'paivav{code}': local_tax,
                f'epaivav{code}': values['tax'],
            })
        _phc_insert_values(cursor, 'FO', {
            'fostamp': fostamp, 'docnome': docname, 'adoc': document_number[:60],
            'nome': str(supplier['name'])[:55], 'nome2': str(supplier['name2'])[:55],
            'total': local_gross_total, 'etotal': gross_total, 'data': effective_at, 'tipo': 'FO',
            'docdata': document_date, 'foano': year, 'doccode': doc_config['doccode'],
            'no': supplier['no'], 'estab': supplier['estab'], 'ccusto': ccusto,
            'ncusto': str(supplier['ncusto'])[:20], 'moeda': currency, 'totmoeda': 0,
            'pdata': due_date, 'plano': 0, 'ivain': local_net_total, 'ttiva': local_tax_total,
            'ttiliq': local_net_total, 'eivain': net_total, 'ettiva': tax_total, 'ettiliq': net_total,
            'paivain': _phc_local_amount(net_total, base_currency_factor, whole=True),
            'epaivain': net_total,
            'patotal': _phc_local_amount(gross_total, base_currency_factor, whole=True),
            'epatotal': gross_total,
            'morada': str(supplier['address'])[:55], 'local': str(supplier['city'])[:43],
            'codpost': str(supplier['postal_code'])[:45], 'ncont': str(supplier['tax_id'])[:20],
            'tpstamp': str(supplier['tpstamp'])[:25], 'tpdesc': str(supplier['tpdesc'])[:30],
            'lang': str(supplier['lang'])[:20], 'aprovado': 0,
            'obs': 'Criado pela Leitura Inteligente com artigo genérico.',
            'ousrinis': initials, 'ousrdata': received_at, 'ousrhora': time_text,
            'usrinis': initials, 'usrdata': received_at, 'usrhora': time_text,
            **tax_header_values,
        })

        fo2_values = {
            'fo2stamp': fostamp, 'formapag': 1, 'olcodigo': 'P10001',
            'taxpointdt': document_date, 'dataven': due_date, 'plano': 0,
            'rowidindex': str(uuid.uuid4()).upper(),
            'ousrinis': initials, 'ousrdata': received_at, 'ousrhora': time_text,
            'usrinis': initials, 'usrdata': received_at, 'usrhora': time_text,
        }
        fo2_values.update({f'ivatx{code}': rate for code, rate in tax_by_code.items()})
        _phc_insert_values(cursor, 'FO2', fo2_values)

        for item in physical_lines:
            continuation = bool(item.get('continuation'))
            _phc_insert_values(cursor, 'FN', {
                'fnstamp': _new_stamp(), 'fostamp': fostamp,
                'ref': '' if continuation else DOC_AI_PROVISIONAL_ARTICLE_REF,
                'design': item['description'],
                'docnome': docname, 'adoc': document_number[:50],
                'unidade': '' if continuation else item['unit'],
                'taxaiva': 0,
                'iva': 0 if continuation else item['rate'],
                'qtt': 0 if continuation else item['qty'],
                'pv': 0 if continuation else _phc_local_amount(item['unit_price'], base_currency_factor),
                'epv': 0 if continuation else item['unit_price'],
                'tiliquido': 0 if continuation else _phc_local_amount(item['net'], base_currency_factor, whole=True),
                'etiliquido': 0 if continuation else item['net'],
                'ivaincl': 0, 'tabiva': item['code'], 'armazem': 1,
                'lordem': item['lordem'], 'data': effective_at,
                'stns': 0 if continuation else 1, 'fnccusto': ccusto, 'familia': '',
                'ousrinis': initials, 'ousrdata': received_at, 'ousrhora': time_text,
                'usrinis': initials, 'usrdata': received_at, 'usrhora': time_text,
            })

        for code, values in tax_groups.items():
            _phc_insert_values(cursor, 'FOT', {
                'fotstamp': _new_stamp(), 'fostamp': fostamp, 'codigo': code,
                'taxa': values['rate'],
                'baseinc': _phc_local_amount(values['base'], base_currency_factor, whole=True),
                'ebaseinc': values['base'],
                'valor': _phc_local_amount(values['tax'], base_currency_factor, whole=True),
                'evalor': values['tax'],
                'ousrinis': initials, 'ousrdata': received_at, 'ousrhora': time_text,
                'usrinis': initials, 'usrdata': received_at, 'usrhora': time_text,
            })

        subject = os.path.splitext(ged_targets[0]['file_name'])[0][:80]
        _phc_insert_values(cursor, 'CR', {
            'crstamp': crstamp, 'data': document_date, 'empresa': str(supplier['name'])[:80],
            'assunto': subject, 'ref': reference, 'refemp': document_number[:80],
            'rdata': received_at, 'entrada': received_at, 'ano': year,
            'tipo': doc_config['correspondence_type'],
            'enviada': 0, 'nenviada': 0, 'no': supplier['no'],
            'estab': supplier['estab'], 'origem': 'FL',
            'pasta': doc_config['correspondence_type'],
            'ousrinis': initials, 'ousrdata': received_at, 'ousrhora': time_text,
            'usrinis': initials, 'usrdata': received_at, 'usrhora': time_text,
            'u_origem': _phc_correspondence_agency_origin(customer, source),
        })

        for target, recstamp, oritable, tabnm, summary, unique_suffix in (
            (
                ged_targets[0], crstamp, 'CR', 'Correspondência',
                doc_config['correspondence_type'], 'CR',
            ),
            (ged_targets[1], fostamp, 'FO', 'Compras a Fornecedores', doc_config['correspondence_type'], 'FO'),
        ):
            _phc_insert_values(cursor, 'ANEXOS', {
                'anexosstamp': _new_stamp(), 'oritable': oritable, 'tabnm': tabnm,
                'resumo': summary, 'grupo': '', 'recstamp': recstamp,
                'uniqueid': f'{unique_root}:{unique_suffix}',
                'descricao': f'{docname} {document_number}'[:100], 'bdados': pyodbc.Binary(b''),
                'fullname': target['unc_path'], 'fname': os.path.splitext(target['file_name'])[0][:150],
                'fext': 'pdf', 'flen': len(file_bytes), 'tipo': 2, 'tpdoc': doc_config['doccode'] if oritable == 'FO' else 0,
                'original': 1 if oritable == 'FO' else 0,
                'ausrinis': initials, 'ausrdata': received_at, 'ausrhora': time_text,
                'usnoopen': user['no'], 'usnaopen': str(user['name'])[:55], 'u_enviado': 1,
                'ousrinis': initials, 'ousrdata': received_at, 'ousrhora': time_text,
                'usrinis': initials, 'usrdata': received_at, 'usrhora': time_text,
            })

        connection.commit()
        result = {
            'ok': True, 'duplicate': False,
            'message': f'{doc_config["label"].capitalize()} {document_number} integrada como {docname} no PHC com {len(physical_lines)} linha(s).',
            'fostamp': fostamp, 'crstamp': crstamp, 'reference': reference,
            'year': year, 'document_number': document_number,
            'phc_database': database_name, 'file_name': ged_targets[1]['file_name'],
            'ged_path': ged_targets[1]['unc_path'],
            'ged_paths': [{'label': target['label'], 'path': target['unc_path']} for target in ged_targets],
            'article_ref': DOC_AI_PROVISIONAL_ARTICLE_REF,
            'doccode': doc_config['doccode'],
            'docname': docname,
            'effective_date': effective_at.date().isoformat(),
            'source_line_count': len(normalized_lines),
            'phc_line_count': len(physical_lines),
        }
        _notify_document_ai_provisional_created(result, document, supplier, requested_by)
        return result
    except Exception:
        try:
            connection.rollback()
        finally:
            for path in created_paths:
                try:
                    target = next((item for item in ged_targets if item['write_path'] == path), None)
                    if target:
                        _remove_document_ai_pdf(target)
                except Exception:
                    current_app.logger.warning('Não foi possível remover o PDF do GED apó rollback: %s', path, exc_info=True)
        raise
    finally:
        connection.close()


def _phc_origin_supplier(cursor, supplier: dict[str, Any]) -> dict[str, Any]:
    supplier_no = _safe_int(supplier.get('supplier_no') or supplier.get('no'), 0)
    supplier_estab = _safe_int(supplier.get('estab'), 0)
    supplier_tax = _digits_only(supplier.get('tax_id'))
    supplier_name = str(supplier.get('name') or supplier.get('llm_name') or '').strip()
    if supplier_no:
        row = cursor.execute("""
            SELECT TOP 1 NO, LTRIM(RTRIM(ISNULL(NOME, ''))) NOME,
                LTRIM(RTRIM(CONVERT(varchar(40), ISNULL(NCONT, '')))) NCONT,
                CAST(ISNULL(ESTAB, 0) AS int) ESTAB
            FROM dbo.FL WHERE NO = ? AND ISNULL(ESTAB, 0) = ?
        """, supplier_no, supplier_estab).fetchone()
        if row:
            return {'no': _safe_int(row[0], 0), 'name': str(row[1] or '').strip(), 'tax_id': _digits_only(row[2]), 'estab': _safe_int(row[3], 0), 'matched_by': 'number'}
    if supplier_tax:
        row = cursor.execute("""
            SELECT TOP 1 NO, LTRIM(RTRIM(ISNULL(NOME, ''))) NOME,
                LTRIM(RTRIM(CONVERT(varchar(40), ISNULL(NCONT, '')))) NCONT,
                CAST(ISNULL(ESTAB, 0) AS int) ESTAB
            FROM dbo.FL
            WHERE REPLACE(REPLACE(REPLACE(REPLACE(LTRIM(RTRIM(CONVERT(varchar(40), ISNULL(NCONT, '')))), ' ', ''), '-', ''), '.', ''), '/', '') = ?
            ORDER BY CASE WHEN ISNULL(ESTAB, 0) = ? THEN 0 ELSE 1 END, ISNULL(ESTAB, 0)
        """, supplier_tax, supplier_estab).fetchone()
        if row:
            return {'no': _safe_int(row[0], 0), 'name': str(row[1] or '').strip(), 'tax_id': _digits_only(row[2]), 'estab': _safe_int(row[3], 0), 'matched_by': 'ncont'}
    normalized_name = _normalize_text(supplier_name)
    if not normalized_name:
        return {}
    rows = cursor.execute("""
        SELECT NO, LTRIM(RTRIM(ISNULL(NOME, ''))) NOME,
            LTRIM(RTRIM(CONVERT(varchar(40), ISNULL(NCONT, '')))) NCONT,
            CAST(ISNULL(ESTAB, 0) AS int) ESTAB
        FROM dbo.FL WHERE ISNULL(NOME, '') <> ''
    """).fetchall()
    best_row = None
    best_score = 0.0
    for row in rows:
        candidate_name = _normalize_text(row[1])
        score = SequenceMatcher(None, normalized_name, candidate_name).ratio()
        if normalized_name in candidate_name or candidate_name in normalized_name:
            score = max(score, 0.92)
        if score > best_score:
            best_score = score
            best_row = row
    if best_row and best_score >= 0.65:
        return {
            'no': _safe_int(best_row[0], 0),
            'name': str(best_row[1] or '').strip(),
            'tax_id': _digits_only(best_row[2]),
            'estab': _safe_int(best_row[3], 0),
            'matched_by': 'name',
            'score': round(best_score, 4),
        }
    return {}


def search_phc_projects(customer_data: dict[str, Any] | None, query: str = '', limit: int = 20) -> dict[str, Any]:
    import pyodbc
    from services.phc_user_import_service import _phc_conn_str

    customer = dict(customer_data or {})
    source = _phc_origin_source(customer)
    if not source.get('phc_db'):
        raise ValueError('A empresa identificada não tem uma base PHC configurada.')
    clean_query = str(query or '').strip()
    like_query = f'%{clean_query}%'
    safe_limit = max(1, min(int(limit or 20), 50))
    with pyodbc.connect(_phc_conn_str(source['phc_db'], source.get('phc_server') or ''), timeout=12) as connection:
        cursor = connection.cursor()
        rows = cursor.execute("""
            SELECT TOP (?)
                LTRIM(RTRIM(ISNULL(BO.CCUSTO, ''))) CCUSTO,
                MAX(LTRIM(RTRIM(ISNULL(BO.MAQUINA, '')))) MAQUINA,
                MAX(LTRIM(RTRIM(ISNULL(BO.LOCAL, '')))) LOCAL,
                MAX(BO.DATAOBRA) ULTIMA_DATA,
                COUNT(DISTINCT BO.BOSTAMP) DOCUMENTOS
            FROM dbo.BO BO WITH (NOLOCK)
            WHERE LTRIM(RTRIM(ISNULL(BO.CCUSTO, ''))) <> ''
              AND (
                    ? = ''
                    OR BO.CCUSTO LIKE ?
                    OR BO.MAQUINA LIKE ?
                    OR BO.LOCAL LIKE ?
                    OR BO.OBRANOME LIKE ?
              )
            GROUP BY LTRIM(RTRIM(ISNULL(BO.CCUSTO, '')))
            ORDER BY MAX(BO.DATAOBRA) DESC, LTRIM(RTRIM(ISNULL(BO.CCUSTO, '')))
        """, safe_limit, clean_query, like_query, like_query, like_query, like_query).fetchall()
    return {
        'items': [{
            'ccusto': str(row[0] or '').strip(),
            'machine': str(row[1] or '').strip(),
            'location': str(row[2] or '').strip(),
            'last_date': row[3].date().isoformat() if isinstance(row[3], datetime) else str(row[3] or '')[:10],
            'document_count': _safe_int(row[4], 0),
        } for row in rows],
        'phc_database': str(source.get('phc_db') or ''),
    }


def search_phc_articles(customer_data: dict[str, Any] | None, query: str = '', limit: int = 20) -> dict[str, Any]:
    import pyodbc
    from services.phc_user_import_service import _phc_conn_str

    customer = dict(customer_data or {})
    source = _phc_origin_source(customer)
    if not source.get('phc_db'):
        raise ValueError('A empresa identificada não tem uma base PHC configurada.')
    clean_query = str(query or '').strip()
    like_query = f'%{clean_query}%'
    safe_limit = max(1, min(int(limit or 20), 50))
    with pyodbc.connect(_phc_conn_str(source['phc_db'], source.get('phc_server') or ''), timeout=12) as connection:
        rows = connection.cursor().execute("""
            SELECT TOP (?)
                LTRIM(RTRIM(ISNULL(ST.REF, ''))) REF,
                LTRIM(RTRIM(ISNULL(ST.DESIGN, ''))) DESIGN,
                LTRIM(RTRIM(ISNULL(ST.UNIDADE, ''))) UNIDADE,
                LTRIM(RTRIM(ISNULL(ST.FAMILIA, ''))) FAMILIA
            FROM dbo.ST ST WITH (NOLOCK)
            WHERE ISNULL(ST.INACTIVO, 0) = 0
              AND LTRIM(RTRIM(ISNULL(ST.REF, ''))) <> ''
              AND (
                    ? = ''
                    OR ST.REF LIKE ?
                    OR ST.DESIGN LIKE ?
                    OR ST.FAMILIA LIKE ?
              )
            ORDER BY LTRIM(RTRIM(ISNULL(ST.REF, '')))
        """, safe_limit, clean_query, like_query, like_query, like_query).fetchall()
    return {
        'items': [{
            'ref': str(row[0] or '').strip(),
            'design': str(row[1] or '').strip(),
            'unit': str(row[2] or '').strip(),
            'family': str(row[3] or '').strip(),
        } for row in rows],
        'phc_database': str(source.get('phc_db') or ''),
    }


def search_phc_vehicles(customer_data: dict[str, Any] | None, query: str = '', limit: int = 20) -> dict[str, Any]:
    import pyodbc
    from services.phc_user_import_service import _phc_conn_str

    customer = dict(customer_data or {})
    source = _phc_origin_source(customer)
    if not source.get('phc_db'):
        raise ValueError('A empresa identificada não tem uma base PHC configurada.')
    clean_query = str(query or '').strip()
    like_query = f'%{clean_query}%'
    safe_limit = max(1, min(int(limit or 20), 50))
    with pyodbc.connect(_phc_conn_str(source['phc_db'], source.get('phc_server') or ''), timeout=12) as connection:
        rows = connection.cursor().execute("""
            SELECT TOP (?)
                LTRIM(RTRIM(ISNULL(V.MATRICULA, ''))) MATRICULA,
                MAX(LTRIM(RTRIM(ISNULL(V.MARCA, '')))) MARCA,
                MAX(LTRIM(RTRIM(ISNULL(V.MODELO, '')))) MODELO,
                MAX(LTRIM(RTRIM(ISNULL(V.NOFROTA, '')))) NOFROTA,
                MAX(LTRIM(RTRIM(ISNULL(V.VASTAMP, '')))) VASTAMP
            FROM dbo.V_ALL_VA V WITH (NOLOCK)
            WHERE ISNULL(V.INACTIVO, 0) = 0
              AND LTRIM(RTRIM(ISNULL(V.MATRICULA, ''))) <> ''
              AND (
                    ? = ''
                    OR V.MATRICULA LIKE ?
                    OR V.MARCA LIKE ?
                    OR V.MODELO LIKE ?
                    OR V.NOFROTA LIKE ?
              )
            GROUP BY LTRIM(RTRIM(ISNULL(V.MATRICULA, '')))
            ORDER BY LTRIM(RTRIM(ISNULL(V.MATRICULA, '')))
        """, safe_limit, clean_query, like_query, like_query, like_query, like_query).fetchall()
    return {
        'items': [{
            'registration': str(row[0] or '').strip(),
            'brand': str(row[1] or '').strip(),
            'model': str(row[2] or '').strip(),
            'fleet_number': str(row[3] or '').strip(),
            'vehicle_stamp': str(row[4] or '').strip(),
        } for row in rows],
        'phc_database': str(source.get('phc_db') or ''),
        'source': 'V_ALL_VA',
    }


def _origin_line_tokens(lines: list[dict[str, Any]]) -> tuple[set[str], set[str]]:
    refs = set()
    tokens = set()
    for line in lines or []:
        ref = _normalize_text(line.get('ref'))
        if ref:
            refs.add(ref.replace(' ', ''))
        description = _normalize_text(line.get('description') or line.get('design'))
        tokens.update(token for token in description.split(' ') if len(token) >= 4)
    return refs, tokens


def _explicit_document_origins(document_data: dict[str, Any]) -> list[dict[str, Any]]:
    origins = []
    seen = set()
    for raw in document_data.get('origin_references') or []:
        if not isinstance(raw, dict):
            continue
        document_type = str(raw.get('document_type') or '').strip()
        document_number = str(raw.get('document_number') or '').strip()
        key = (_normalize_text(document_type), _normalize_text(document_number).replace(' ', ''))
        if not document_number or key in seen:
            continue
        seen.add(key)
        origins.append({
            'document_type': document_type,
            'document_number': document_number,
            'visible_text': str(raw.get('visible_text') or '').strip(),
            'page': _safe_int(raw.get('page'), 0) or None,
        })
    for line in document_data.get('lines') or []:
        if not isinstance(line, dict):
            continue
        description = str(line.get('description') or line.get('design') or '').strip()
        normalized_description = _normalize_text(description)
        for match in re.finditer(
            r'\bref(?:erence)?\.?\s+client\s*[:#nº°.\-]*\s*([a-z0-9][a-z0-9./_-]*)',
            normalized_description,
        ):
            customer_reference = str(match.group(1) or '').strip()
            reference_key = ('purchase_order', _origin_number_key(customer_reference))
            if not customer_reference or reference_key in seen:
                continue
            seen.add(reference_key)
            origins.append({
                'document_type': 'purchase_order',
                'document_number': customer_reference,
                'visible_text': f'Réf. Client: {customer_reference}',
                'page': None,
            })
        document_number = str(line.get('origin_delivery_note_number') or '').strip()
        key = ('delivery_note', _normalize_text(document_number).replace(' ', ''))
        if not document_number or key in seen:
            continue
        seen.add(key)
        origins.append({
            'document_type': 'delivery_note',
            'document_number': document_number,
            'visible_text': 'Referência de Guia de Remessa associada às linhas da fatura',
            'page': None,
        })
    return origins


def _origin_number_key(value: Any) -> str:
    normalized = _normalize_text(value)
    return re.sub(r'[^a-z0-9]', '', normalized)


def _document_origin_quantity(lines: list[dict[str, Any]]) -> float:
    commercial_lines = [
        line for line in lines or []
        if isinstance(line, dict)
        and not bool(line.get('_virtual_split_allocation'))
        and str(line.get('origin_delivery_note_number') or '').strip()
        and abs(float(line.get('qty') or line.get('quantity') or 0)) > 0
    ]
    quantity_lines = commercial_lines or [
        line for line in lines or []
        if isinstance(line, dict)
        and not bool(line.get('_virtual_split_allocation'))
        and abs(float(line.get('qty') or line.get('quantity') or 0)) > 0
    ]
    return round(sum(abs(float(line.get('qty') or line.get('quantity') or 0)) for line in quantity_lines), 4)


def _line_mapping_similarity(current_line: dict[str, Any], origin_line: dict[str, Any]) -> tuple[float, list[str]]:
    score = 0.0
    reasons = []
    current_ref = _origin_number_key(current_line.get('ref'))
    origin_ref = _origin_number_key(origin_line.get('ref'))
    if current_ref and origin_ref and current_ref == origin_ref:
        score += 0.45
        reasons.append('Referência coincidente')

    current_qty = abs(float(current_line.get('qty') or current_line.get('quantity') or 0))
    origin_qty = abs(float(origin_line.get('pending_qty') or origin_line.get('qty') or 0))
    if current_qty > 0 and origin_qty > 0:
        qty_difference = abs(current_qty - origin_qty) / max(current_qty, origin_qty)
        if qty_difference <= 0.02:
            score += 0.4
            reasons.append('Quantidade coincidente')
        elif qty_difference <= 0.15:
            score += 0.32
            reasons.append('Quantidade próxima')
        elif qty_difference <= 0.35:
            score += 0.16

    current_description = _normalize_text(current_line.get('description') or current_line.get('design'))
    origin_description = _normalize_text(origin_line.get('description') or origin_line.get('design'))
    if current_description and origin_description:
        sequence_score = SequenceMatcher(None, current_description, origin_description).ratio()
        current_tokens = {token for token in current_description.split() if len(token) >= 4}
        origin_tokens = {token for token in origin_description.split() if len(token) >= 4}
        token_score = len(current_tokens & origin_tokens) / max(1, min(len(current_tokens), len(origin_tokens)))
        description_score = max(sequence_score, token_score)
        score += min(description_score, 1.0) * 0.48
        if description_score >= 0.45:
            reasons.append('Descrição semelhante')
    return round(min(score, 0.99), 4), reasons


def _match_document_lines_to_origin(
    document_lines: list[dict[str, Any]],
    origin_lines: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    indexed_current = [
        (index, line) for index, line in enumerate(document_lines or [])
        if isinstance(line, dict)
        and not bool(line.get('_virtual_split_allocation'))
        and abs(float(line.get('qty') or line.get('quantity') or 0)) > 0
    ]
    delivery_current = [item for item in indexed_current if str(item[1].get('origin_delivery_note_number') or '').strip()]
    if delivery_current:
        indexed_current = delivery_current
    usable_origins = [
        (index, line) for index, line in enumerate(origin_lines or [])
        if isinstance(line, dict) and str(line.get('ref') or '').strip()
    ]
    if not indexed_current or not usable_origins:
        return []

    positive_origins = [item for item in usable_origins if abs(float(item[1].get('pending_qty') or item[1].get('qty') or 0)) > 0]
    current_total = round(sum(abs(float(line.get('qty') or line.get('quantity') or 0)) for _, line in indexed_current), 4)
    if len(positive_origins) == 1 and current_total > 0:
        origin_index, origin_line = positive_origins[0]
        origin_quantity = abs(float(origin_line.get('pending_qty') or origin_line.get('qty') or 0))
        quantity_difference = abs(current_total - origin_quantity) / max(current_total, origin_quantity)
        if quantity_difference <= 0.1:
            return [{
                'document_line_index': current_index,
                'origin_line_index': origin_index,
                'origin_ref': str(origin_line.get('ref') or '').strip(),
                'origin_description': str(origin_line.get('description') or origin_line.get('design') or '').strip(),
                'origin_quantity': origin_quantity,
                'score': round(min(0.99, 0.86 + ((1.0 - quantity_difference) * 0.13)), 4),
                'reasons': ['Quantidade agregada coincide', 'Única linha quantitativa da Nota de Encomenda'],
            } for current_index, _ in indexed_current]

    ranked_pairs = []
    for current_index, current_line in indexed_current:
        for origin_index, origin_line in usable_origins:
            score, reasons = _line_mapping_similarity(current_line, origin_line)
            if score >= 0.42:
                ranked_pairs.append((score, current_index, origin_index, current_line, origin_line, reasons))
    ranked_pairs.sort(key=lambda item: item[0], reverse=True)
    used_current = set()
    used_origin = set()
    matches = []
    for score, current_index, origin_index, _current_line, origin_line, reasons in ranked_pairs:
        if current_index in used_current or origin_index in used_origin:
            continue
        used_current.add(current_index)
        used_origin.add(origin_index)
        matches.append({
            'document_line_index': current_index,
            'origin_line_index': origin_index,
            'origin_ref': str(origin_line.get('ref') or '').strip(),
            'origin_description': str(origin_line.get('description') or origin_line.get('design') or '').strip(),
            'origin_quantity': abs(float(origin_line.get('pending_qty') or origin_line.get('qty') or 0)),
            'score': score,
            'reasons': reasons,
        })
    matches.sort(key=lambda item: int(item.get('document_line_index') or 0))
    return matches


def _score_phc_origin_candidate(
    candidate: dict[str, Any],
    document_data: dict[str, Any],
    candidate_lines: list[dict[str, Any]],
) -> tuple[float, list[str]]:
    current_date = _document_date_value(document_data.get('document_date'))
    candidate_date = candidate.get('date') or current_date
    if not isinstance(candidate_date, datetime):
        candidate_date = _document_date_value(candidate_date)
    day_distance = abs((current_date.date() - candidate_date.date()).days)
    stage_weights = {218: 0.34, 130: 0.29, 102: 0.24}
    score = 0.22 if str(candidate.get('document_type') or '').strip() == 'contract' else stage_weights.get(_safe_int(candidate.get('ndos'), 0), 0.2)
    reasons = ['Mesmo fornecedor']
    candidate_type = str(candidate.get('document_type') or '').strip()
    candidate_number = _origin_number_key(candidate.get('number'))
    for explicit_origin in _explicit_document_origins(document_data):
        explicit_number = _origin_number_key(explicit_origin.get('document_number'))
        explicit_type = str(explicit_origin.get('document_type') or '').strip()
        if explicit_number and candidate_number and explicit_number == candidate_number:
            score += 0.48 if not explicit_type or explicit_type == candidate_type else 0.38
            reasons.insert(0, f'Referência explícita no PDF: {explicit_origin.get("document_number")}')
            break
    date_score = max(0.0, 1.0 - (day_distance / 365.0))
    score += date_score * 0.22
    if day_distance <= 45:
        reasons.append(f'Data próxima ({day_distance} dias)')

    current_refs, current_tokens = _origin_line_tokens(document_data.get('lines') or [])
    candidate_refs, candidate_tokens = _origin_line_tokens(candidate_lines)
    if current_refs and candidate_refs:
        overlap = len(current_refs & candidate_refs) / max(1, min(len(current_refs), len(candidate_refs)))
        score += overlap * 0.25
        if overlap:
            reasons.append(f'{round(overlap * 100)}% das referências coincidem')
    if current_tokens and candidate_tokens:
        token_overlap = len(current_tokens & candidate_tokens) / max(1, min(len(current_tokens), len(candidate_tokens)))
        score += min(token_overlap, 1.0) * 0.12
        if token_overlap >= 0.2:
            reasons.append('Descrições semelhantes')

    current_quantity = _document_origin_quantity(document_data.get('lines') or [])
    candidate_quantity = round(sum(
        abs(float(line.get('pending_qty') or 0))
        for line in candidate_lines or []
        if isinstance(line, dict)
    ), 4)
    if current_quantity > 0 and candidate_quantity > 0:
        quantity_difference = abs(current_quantity - candidate_quantity) / max(current_quantity, candidate_quantity)
        if quantity_difference <= 0.1:
            score += (1.0 - quantity_difference) * 0.24
            reasons.append(f'Quantidade pendente coincide ({candidate_quantity:g})')

    gross_total = float((document_data.get('totals') or {}).get('gross_total') or 0)
    candidate_total = float(candidate.get('total') or 0)
    if gross_total > 0 and candidate_total > 0:
        relative_difference = abs(gross_total - candidate_total) / max(gross_total, candidate_total)
        if relative_difference <= 0.1:
            score += (1.0 - relative_difference) * 0.12
            reasons.append('Valor total próximo')
    return round(min(score, 0.99), 4), reasons


def search_phc_document_origins(document_data: dict[str, Any] | None, limit_per_stage: int = 6) -> dict[str, Any]:
    import pyodbc
    from services.phc_user_import_service import _phc_conn_str

    document = dict(document_data or {})
    customer = dict(document.get('customer') or {})
    supplier = dict(document.get('supplier') or {})
    selected_project = dict(document.get('origin_project') or {})
    project_ccusto = str(selected_project.get('ccusto') or '').strip()
    explicit_origins = _explicit_document_origins(document)
    source = _phc_origin_source(customer)
    if not source.get('phc_db'):
        raise ValueError('A empresa identificada não tem uma base PHC configurada.')
    if not project_ccusto:
        return {
            'available': True,
            'phc_database': source.get('phc_db') or '',
            'company_name': source.get('company_name') or customer.get('name') or '',
            'supplier': {},
            'current_document_type': str(document.get('document_type') or 'unknown').strip(),
            'current_document_number': str(document.get('document_number') or ''),
            'detected_origins': explicit_origins,
            'selected_project': None,
            'suggested_origin': None,
            'stages': [],
            'candidate_count': 0,
            'message': 'Seleciona primeiro a obra para procurar origens elegíveis.',
        }

    current_type = str(document.get('document_type') or 'unknown').strip()
    allowed_by_type = {
        'delivery_note': [102],
        'proforma_invoice': [102, 130],
        'invoice': [102, 130, 218],
        'credit_note': [102, 130, 218],
        'debit_note': [102, 130, 218],
    }
    allowed_ndos = list(allowed_by_type.get(current_type, [102, 130, 218]))
    current_date = _document_date_value(document.get('document_date'))
    date_from = current_date - timedelta(days=730)
    date_to = current_date + timedelta(days=31)

    with pyodbc.connect(_phc_conn_str(source['phc_db'], source.get('phc_server') or ''), timeout=12) as connection:
        cursor = connection.cursor()
        phc_supplier = _phc_origin_supplier(cursor, supplier)
        if not phc_supplier.get('no'):
            raise ValueError('O fornecedor não foi encontrado na FL da empresa PHC.')
        contract_stages = _phc_contract_flow_stages(cursor) if current_type in {
            'proforma_invoice', 'invoice', 'credit_note', 'debit_note',
        } else []
        allowed_ndos.extend(
            stage['ndos'] for stage in contract_stages
            if stage.get('ndos') not in allowed_ndos
        )
        ndos_placeholders = ','.join('?' for _ in allowed_ndos)
        project_filter_sql = " AND LTRIM(RTRIM(ISNULL(BO.CCUSTO, ''))) = ?" if project_ccusto else ''
        header_params = [phc_supplier['no'], *allowed_ndos, date_from, date_to]
        if project_ccusto:
            header_params.append(project_ccusto)
        header_rows = cursor.execute(f"""
            SELECT TOP 160
                BO.BOSTAMP, BO.NDOS, LTRIM(RTRIM(ISNULL(BO.NMDOS, ''))) NMDOS,
                BO.OBRANO, BO.BOANO, BO.DATAOBRA, BO.NO,
                LTRIM(RTRIM(ISNULL(BO.NOME, ''))) NOME,
                LTRIM(RTRIM(ISNULL(BO.CCUSTO, ''))) CCUSTO,
                LTRIM(RTRIM(ISNULL(BO.MAQUINA, ''))) MAQUINA,
                LTRIM(RTRIM(ISNULL(BO.LOCAL, ''))) LOCAL,
                ISNULL(BO.ETOTAL, 0) ETOTAL,
                ISNULL(BO.FECHADA, 0) FECHADA
            FROM dbo.BO BO WITH (NOLOCK)
            LEFT JOIN dbo.BO2 BO2 WITH (NOLOCK) ON BO2.BO2STAMP = BO.BOSTAMP
            WHERE BO.NO = ?
              AND BO.NDOS IN ({ndos_placeholders})
              AND ISNULL(BO2.ANULADO, 0) = 0
              AND ISNULL(BO.FECHADA, 0) = 0
              AND BO.DATAOBRA >= ?
              AND BO.DATAOBRA <= ?
              {project_filter_sql}
            ORDER BY BO.DATAOBRA DESC, BO.BOANO DESC, BO.OBRANO DESC
        """, *header_params).fetchall()
        columns = [str(item[0]).upper() for item in cursor.description or []]
        headers = [dict(zip(columns, row)) for row in header_rows]
        stamps = [str(item.get('BOSTAMP') or '').strip() for item in headers if str(item.get('BOSTAMP') or '').strip()]
        lines_by_stamp: dict[str, list[dict[str, Any]]] = {stamp: [] for stamp in stamps}
        predecessors_by_stamp: dict[str, set[str]] = {stamp: set() for stamp in stamps}
        if stamps:
            for offset in range(0, len(stamps), 80):
                stamp_chunk = stamps[offset:offset + 80]
                placeholders = ','.join('?' for _ in stamp_chunk)
                line_rows = cursor.execute(f"""
                    SELECT
                        BI.BOSTAMP, BI.BISTAMP,
                        LTRIM(RTRIM(ISNULL(BI.REF, ''))) REF,
                        LTRIM(RTRIM(ISNULL(BI.DESIGN, ''))) DESIGN,
                        ISNULL(BI.QTT, 0) QTT,
                        ISNULL(BI.EDEBITO, 0) EDEBITO,
                        ISNULL(BI.ETTDEB, 0) ETTDEB,
                        ISNULL(BI.LORDEM, 0) LORDEM,
                        ISNULL(BI.FECHADA, 0) LINE_FECHADA,
                        LTRIM(RTRIM(ISNULL(BI.OBISTAMP, ''))) OBISTAMP,
                        LTRIM(RTRIM(ISNULL(BI.OOBISTAMP, ''))) OOBISTAMP,
                        LTRIM(RTRIM(ISNULL(BI2.ORIGBISTAMP, ''))) ORIGBISTAMP
                    FROM dbo.BI BI WITH (NOLOCK)
                    LEFT JOIN dbo.BI2 BI2 WITH (NOLOCK) ON BI2.BI2STAMP = BI.BISTAMP
                    WHERE BI.BOSTAMP IN ({placeholders})
                    ORDER BY BI.BOSTAMP, BI.LORDEM
                """, *stamp_chunk).fetchall()
                line_columns = [str(item[0]).upper() for item in cursor.description or []]
                parent_line_stamps = set()
                parsed_lines = []
                for row in line_rows:
                    item = dict(zip(line_columns, row))
                    parsed_lines.append(item)
                    for key in ('OBISTAMP', 'OOBISTAMP', 'ORIGBISTAMP'):
                        parent_stamp = str(item.get(key) or '').strip()
                        if parent_stamp:
                            parent_line_stamps.add(parent_stamp)
                for item in parsed_lines:
                    original_qty = abs(float(item.get('QTT') or 0))
                    pending_qty = 0.0 if bool(item.get('LINE_FECHADA') or 0) else original_qty
                    lines_by_stamp.setdefault(str(item.get('BOSTAMP') or '').strip(), []).append({
                        'line_stamp': str(item.get('BISTAMP') or '').strip(),
                        'line_order': float(item.get('LORDEM') or 0),
                        'ref': str(item.get('REF') or '').strip(),
                        'description': str(item.get('DESIGN') or '').strip(),
                        'qty': float(item.get('QTT') or 0),
                        'pending_qty': pending_qty,
                        'unit_price': float(item.get('EDEBITO') or 0),
                        'line_total': float(item.get('ETTDEB') or 0),
                    })
                if parent_line_stamps:
                    parent_list = list(parent_line_stamps)
                    for parent_offset in range(0, len(parent_list), 80):
                        parent_chunk = parent_list[parent_offset:parent_offset + 80]
                        parent_placeholders = ','.join('?' for _ in parent_chunk)
                        parent_rows = cursor.execute(f"""
                            SELECT BISTAMP, BOSTAMP FROM dbo.BI WITH (NOLOCK)
                            WHERE BISTAMP IN ({parent_placeholders})
                        """, *parent_chunk).fetchall()
                        parent_map = {str(row[0] or '').strip(): str(row[1] or '').strip() for row in parent_rows}
                        for item in parsed_lines:
                            child_header = str(item.get('BOSTAMP') or '').strip()
                            for key in ('OBISTAMP', 'OOBISTAMP', 'ORIGBISTAMP'):
                                parent_header = parent_map.get(str(item.get(key) or '').strip(), '')
                                if parent_header and parent_header != child_header:
                                    predecessors_by_stamp.setdefault(child_header, set()).add(parent_header)

    flow_stages = [*DOC_AI_PHC_PURCHASE_FLOW, *contract_stages]
    flow_lookup = {int(item.get('ndos') or 0): item for item in flow_stages if item.get('ndos')}
    candidates = []
    for header in headers:
        stamp = str(header.get('BOSTAMP') or '').strip()
        pending_quantity = round(sum(float(line.get('pending_qty') or 0) for line in lines_by_stamp.get(stamp) or []), 4)
        if pending_quantity <= 0:
            continue
        candidate = {
            'origin_key': f'BO:{stamp}',
            'table': 'BO',
            'stamp': stamp,
            'ndos': _safe_int(header.get('NDOS'), 0),
            'document_type': (flow_lookup.get(_safe_int(header.get('NDOS'), 0)) or {}).get('document_type') or (flow_lookup.get(_safe_int(header.get('NDOS'), 0)) or {}).get('key') or 'unknown',
            'stage_label': (flow_lookup.get(_safe_int(header.get('NDOS'), 0)) or {}).get('label') or str(header.get('NMDOS') or '').strip(),
            'number': str(_safe_int(header.get('OBRANO'), 0) or ''),
            'year': _safe_int(header.get('BOANO'), 0) or None,
            'date': header.get('DATAOBRA'),
            'total': float(header.get('ETOTAL') or 0),
            'closed': bool(header.get('FECHADA') or 0),
            'supplier_no': phc_supplier.get('no'),
            'supplier_name': phc_supplier.get('name') or '',
            'ccusto': str(header.get('CCUSTO') or '').strip(),
            'project_machine': str(header.get('MAQUINA') or '').strip(),
            'project_location': str(header.get('LOCAL') or '').strip(),
            'line_count': len(lines_by_stamp.get(stamp) or []),
            'lines': lines_by_stamp.get(stamp) or [],
            'pending_quantity': pending_quantity,
            'predecessor_stamps': sorted(predecessors_by_stamp.get(stamp) or []),
        }
        score, reasons = _score_phc_origin_candidate(candidate, document, lines_by_stamp.get(stamp) or [])
        candidate['score'] = score
        candidate['reasons'] = reasons
        candidate['line_matches'] = _match_document_lines_to_origin(
            document.get('lines') or [],
            lines_by_stamp.get(stamp) or [],
        ) if candidate['document_type'] == 'purchase_order' else []
        candidate['date'] = candidate['date'].date().isoformat() if isinstance(candidate['date'], datetime) else str(candidate['date'] or '')[:10]
        candidates.append(candidate)
    candidates.sort(key=lambda item: (float(item.get('score') or 0), str(item.get('date') or '')), reverse=True)

    stages = []
    eligible_stages = [
        stage for stage in sorted(flow_stages, key=lambda item: int(item.get('order') or 0), reverse=True)
        if stage.get('ndos') in allowed_ndos
    ]
    for display_order, stage in enumerate(eligible_stages, start=1):
        ndos = stage.get('ndos')
        stage_candidates = [item for item in candidates if item.get('ndos') == ndos]
        stage_candidates.sort(key=lambda item: (float(item.get('score') or 0), str(item.get('date') or '')), reverse=True)
        if not stage_candidates:
            continue
        stages.append({
            'key': stage['key'],
            'label': stage['label'],
            'order': stage['order'],
            'display_order': display_order,
            'candidates': stage_candidates[:max(1, min(int(limit_per_stage or 6), 12))],
        })
    return {
        'available': True,
        'phc_database': source.get('phc_db') or '',
        'company_name': source.get('company_name') or customer.get('name') or '',
        'supplier': phc_supplier,
        'current_document_type': current_type,
        'current_document_number': str(document.get('document_number') or ''),
        'detected_origins': explicit_origins,
        'selected_project': selected_project if project_ccusto else None,
        'suggested_origin': candidates[0] if candidates else None,
        'stages': stages,
        'candidate_count': sum(len(stage.get('candidates') or []) for stage in stages),
    }


def get_phc_document_origin_detail(
    document_stamp: str,
    origin_stamp: str,
) -> dict[str, Any]:
    """Return an origin and its lines exclusively from the configured PHC database."""
    import pyodbc
    from services.phc_user_import_service import _phc_conn_str

    cached = get_cached_llm_extraction(document_stamp)
    document_data = dict((cached or {}).get('document') or {})
    customer = dict(document_data.get('customer') or {})
    source = _phc_origin_source(customer)
    clean_stamp = str(origin_stamp or '').strip()
    if not source.get('phc_db'):
        raise ValueError('A empresa identificada não tem uma base PHC configurada.')
    if not clean_stamp:
        raise ValueError('A origem PHC não é válida.')

    with pyodbc.connect(_phc_conn_str(source['phc_db'], source.get('phc_server') or ''), timeout=12) as connection:
        cursor = connection.cursor()
        header = cursor.execute("""
            SELECT TOP 1
                BO.BOSTAMP, BO.NDOS, LTRIM(RTRIM(ISNULL(BO.NMDOS, ''))),
                BO.OBRANO, BO.BOANO, BO.DATAOBRA, ISNULL(BO.ETOTAL, 0)
            FROM dbo.BO BO WITH (NOLOCK)
            WHERE BO.BOSTAMP = ?
        """, clean_stamp).fetchone()
        if not header:
            raise ValueError('A origem já não existe no PHC.')

        bi_columns = {
            str(row[0] or '').upper()
            for row in cursor.execute("""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'BI'
            """).fetchall()
        }
        registration_column = next(
            (name for name in ('LOBS', 'MATRICULA', 'VIATURA', 'U_MATRICULA') if name in bi_columns),
            '',
        )
        registration_sql = f"LTRIM(RTRIM(ISNULL(BI.[{registration_column}], '')))" if registration_column else "CAST('' AS varchar(1))"
        line_rows = cursor.execute(f"""
            SELECT
                LTRIM(RTRIM(ISNULL(BI.REF, ''))),
                LTRIM(RTRIM(ISNULL(BI.DESIGN, ''))),
                ISNULL(BI.QTT, 0),
                ISNULL(BI.EDEBITO, 0),
                ISNULL(BI.ETTDEB, 0),
                ISNULL(BI.IVA, 0),
                LTRIM(RTRIM(ISNULL(BI.CCUSTO, ''))),
                {registration_sql},
                BO.DATAOBRA
            FROM dbo.BI BI WITH (NOLOCK)
            INNER JOIN dbo.BO BO WITH (NOLOCK) ON BO.BOSTAMP = BI.BOSTAMP
            WHERE BI.BOSTAMP = ?
            ORDER BY BI.LORDEM, BI.BISTAMP
        """, clean_stamp).fetchall()

    flow_lookup = {
        int(item.get('ndos') or 0): item
        for item in DOC_AI_PHC_PURCHASE_FLOW
        if item.get('ndos')
    }
    ndos = _safe_int(header[1], 0)
    stage = flow_lookup.get(ndos) or {}
    rows = [{
        'article': str(row[0] or '').strip(),
        'description': str(row[1] or '').strip(),
        'quantity': float(row[2] or 0),
        'unit_price': float(row[3] or 0),
        'line_total': float(row[4] or 0),
        'tax_rate': float(row[5] or 0),
        'project': str(row[6] or '').strip(),
        'registration': str(row[7] or '').strip(),
        'date': row[8].date().isoformat() if isinstance(row[8], datetime) else str(row[8] or '')[:10],
    } for row in line_rows]
    return {
        'ok': True,
        'origin': {
            'stamp': str(header[0] or '').strip(),
            'document_type': stage.get('document_type') or stage.get('key') or 'unknown',
            'stage_label': stage.get('label') or str(header[2] or '').strip(),
            'number': str(_safe_int(header[3], 0) or ''),
            'year': _safe_int(header[4], 0) or None,
            'date': header[5].date().isoformat() if isinstance(header[5], datetime) else str(header[5] or '')[:10],
            'total': float(header[6] or 0),
        },
        'lines': rows,
        'show_registration': any(row['registration'] for row in rows),
        'source': 'PHC',
    }


def save_document_phc_origin(
    document_stamp: str,
    origin: dict[str, Any] | None,
    document_data: dict[str, Any] | None,
    requested_by: str,
) -> dict[str, Any]:
    document = db.session.get(DocInbox, str(document_stamp or '').strip())
    if not document:
        raise ValueError('Documento do inbox não encontrado.')
    candidate = dict(origin or {})
    if candidate.get('table') != 'BO' or not str(candidate.get('stamp') or '').strip():
        raise ValueError('Seleciona uma origem PHC válida.')
    search_payload = search_phc_document_origins(document_data or {}, limit_per_stage=12)
    valid_candidates = {
        str(item.get('stamp') or '').strip(): item
        for stage in search_payload.get('stages') or []
        for item in stage.get('candidates') or []
    }
    selected = valid_candidates.get(str(candidate.get('stamp') or '').strip())
    if not selected:
        raise ValueError('A origem selecionada já não está disponível entre os candidatos deste fornecedor.')
    meta = _json_loads(document.processing_meta_json, {})
    selected_origin = {
        **selected,
        'origin_family': _phc_origin_family(selected),
        'phc_database': search_payload.get('phc_database') or '',
        'linked_at': _now().isoformat(),
        'linked_by': requested_by or '',
    }
    origins = get_phc_origins_from_meta(meta)
    origins = [item for item in origins if str(item.get('stamp') or '').strip() != str(selected_origin.get('stamp') or '').strip()]
    _validate_phc_origin_combination(origins, selected_origin)
    origins.append(selected_origin)
    meta['phc_origins'] = origins
    meta.pop('phc_origin', None)
    document.processing_meta_json = _json_dumps(meta)
    document.dtalt = _now()
    document.useralteracao = requested_by or document.useralteracao or ''
    db.session.commit()
    return {
        'ok': True,
        'message': 'Origem PHC adicionada ao documento.',
        'origin': selected_origin,
        'origins': origins,
        'version': _document_draft_version(document),
    }


def get_phc_origins_from_meta(meta: dict[str, Any] | None) -> list[dict[str, Any]]:
    payload = dict(meta or {})
    origins = payload.get('phc_origins')
    if isinstance(origins, list):
        return [dict(item) for item in origins if isinstance(item, dict) and str(item.get('stamp') or '').strip()]
    legacy = payload.get('phc_origin')
    return [dict(legacy)] if isinstance(legacy, dict) and str(legacy.get('stamp') or '').strip() else []


def get_document_phc_origins(document_stamp: str) -> list[dict[str, Any]]:
    document = db.session.get(DocInbox, str(document_stamp or '').strip())
    if not document:
        return []
    return get_phc_origins_from_meta(_json_loads(document.processing_meta_json, {}))


def get_document_phc_origin(document_stamp: str) -> dict[str, Any] | None:
    origins = get_document_phc_origins(document_stamp)
    return origins[0] if origins else None


def clear_document_phc_origin(document_stamp: str, requested_by: str, origin_stamp: str = '') -> dict[str, Any]:
    document = db.session.get(DocInbox, str(document_stamp or '').strip())
    if not document:
        raise ValueError('Documento do inbox não encontrado.')
    meta = _json_loads(document.processing_meta_json, {})
    origins = get_phc_origins_from_meta(meta)
    clean_stamp = str(origin_stamp or '').strip()
    if clean_stamp:
        remaining = [item for item in origins if str(item.get('stamp') or '').strip() != clean_stamp]
        removed_count = len(origins) - len(remaining)
    else:
        remaining = []
        removed_count = len(origins)
    if remaining:
        meta['phc_origins'] = remaining
    else:
        meta.pop('phc_origins', None)
    meta.pop('phc_origin', None)
    document.processing_meta_json = _json_dumps(meta)
    document.dtalt = _now()
    document.useralteracao = requested_by or document.useralteracao or ''
    db.session.commit()
    return {
        'ok': True,
        'removed': bool(removed_count),
        'message': 'Origem PHC desmarcada.' if clean_stamp else 'Origens PHC desmarcadas.',
        'origins': remaining,
        'version': _document_draft_version(document),
    }


def save_document_adjusted_lines(
    document_stamp: str,
    lines: list[dict[str, Any]],
    requested_by: str,
) -> dict[str, Any]:
    document = db.session.get(DocInbox, str(document_stamp or '').strip())
    if not document:
        raise ValueError('Documento do inbox não encontrado.')
    if not isinstance(lines, list) or len(lines) > 2000 or any(not isinstance(line, dict) for line in lines):
        raise ValueError('As linhas ajustadas não são válidas.')
    meta = _json_loads(document.processing_meta_json, {})
    cached = meta.get('llm_full_extraction')
    if not isinstance(cached, dict) or not isinstance(cached.get('document'), dict):
        raise ValueError('O documento ainda não tem uma leitura guardada para ajustar.')
    cached_document = dict(cached.get('document') or {})
    cached_document['lines'] = [dict(line) for line in lines]
    cached['document'] = cached_document
    cached['adjusted_at'] = _now().isoformat()
    cached['adjusted_by'] = requested_by or ''
    meta['llm_full_extraction'] = cached
    document.processing_meta_json = _json_dumps(meta)
    document.json_resultado = _json_dumps(cached_document)
    document.dtalt = _now()
    document.useralteracao = requested_by or document.useralteracao or ''
    db.session.commit()
    return {
        'ok': True,
        'message': 'Repartição das linhas guardada no inbox.',
        'line_count': len(lines),
        'version': _document_draft_version(document),
    }


def _document_workflow_payload(document: DocInbox) -> dict[str, Any]:
    validation = {
        'reception_validated': bool(getattr(document, 'reception_validated', False)),
        'management_validated': bool(getattr(document, 'management_validated', False)),
        'accounting_validated': bool(getattr(document, 'accounting_validated', False)),
    }
    if not has_app_context():
        return {**validation, 'assignments': []}
    assignments = db.session.execute(text("""
        SELECT VIEW_CODE, STATE_CODE, ATIVO, VALIDADO, SOURCE_VIEW
        FROM dbo.DOC_AI_WORKFLOW_ASSIGNMENT
        WHERE DOCINSTAMP=:document_id
        ORDER BY DTALT DESC, DTCRI DESC
    """), {'document_id': document.docinstamp}).mappings().all()
    return {
        **validation,
        'assignments': [
            {
                'view': str(row.get('VIEW_CODE') or '').strip().lower(),
                'state': str(row.get('STATE_CODE') or '').strip().lower(),
                'active': bool(row.get('ATIVO')),
                'validated': bool(row.get('VALIDADO')),
                'source': str(row.get('SOURCE_VIEW') or '').strip().lower(),
            }
            for row in assignments
        ],
    }


def get_cached_llm_extraction(document_stamp: str) -> dict[str, Any] | None:
    document = db.session.get(DocInbox, str(document_stamp or '').strip())
    if not document:
        return None
    meta = _json_loads(document.processing_meta_json, {})
    cached = meta.get('llm_full_extraction')
    if (
        not isinstance(cached, dict)
        or _safe_int(cached.get('version'), 0) < 4
        or not isinstance(cached.get('document'), dict)
    ):
        return None
    cached_document = dict(cached.get('document') or {})
    customer = dict(cached_document.get('customer') or {})
    entity = _fe_entity_by_id(customer.get('feid') or getattr(document, 'feid', None))
    if entity:
        customer.update({
            'feid': entity.get('feid'),
            'phc_database': entity.get('phc_database') or '',
            'ged_folder': entity.get('ged_folder') or '',
        })
        cached_document['customer'] = customer

    cached_matching = dict(cached.get('matching') or {})
    if entity:
        cached_matching['customer'] = {
            **dict(cached_matching.get('customer') or {}),
            **entity,
        }

    workflow = {
        **dict(meta.get('workflow') or {}),
        **_document_workflow_payload(document),
    }
    return {
        'ok': True,
        'available': True,
        'cached': True,
        'document_id': document.docinstamp,
        'version': _document_draft_version(document),
        'model': str(cached.get('model') or 'LLM'),
        'document': cached_document,
        'matching': cached_matching,
        'saved_at': str(cached.get('saved_at') or ''),
        'processing_status': str(getattr(document, 'processing_status', '') or ''),
        'workflow': workflow,
        'phc_integration': dict(meta.get('phc_integration') or {}),
        'duplicate_detection': dict(meta.get('duplicate_detection') or {}),
        'duplicate_override': dict(meta.get('duplicate_override') or {}),
    }


def mark_document_control_ok(
    document_stamp: str,
    requested_by: str,
    reviewed_document: dict[str, Any] | None = None,
) -> dict[str, Any]:
    document = db.session.get(DocInbox, str(document_stamp or '').strip())
    if not document:
        raise ValueError('Documento do inbox não encontrado.')
    meta = _json_loads(document.processing_meta_json, {})
    cached = meta.get('llm_full_extraction') or {}
    document_data = dict(reviewed_document or {}) or (cached.get('document') if isinstance(cached, dict) else {})
    if not isinstance(document_data, dict):
        document_data = {}
    document_type = str(document_data.get('document_type') or '').strip().lower()
    if not _is_provisional_purchase_source_type(document_type):
        raise ValueError('O Controlo OK aplica-se apenas a documentos de compra preparados para Fatura Provisória.')
    customer = dict(document_data.get('customer') or {})
    supplier = dict(document_data.get('supplier') or {})
    if not _safe_int(customer.get('feid'), 0):
        raise ValueError('Identifica a sociedade antes do Contrôle OK.')
    if not _safe_int(supplier.get('supplier_no') or supplier.get('no'), 0):
        raise ValueError('Identifica o fornecedor antes do Contrôle OK.')
    if not str(document_data.get('document_number') or '').strip():
        raise ValueError('Confirma o número do documento antes do Contrôle OK.')
    if not [line for line in (document_data.get('lines') or []) if isinstance(line, dict)]:
        raise ValueError('Confirma pelo menos uma linha antes do Contrôle OK.')
    origins = get_phc_origins_from_meta(meta)
    if not any(_phc_origin_family(origin) in {'', 'bc', 'contract', 'subcontract'} for origin in origins):
        raise ValueError('Falta associar uma Nota de Encomenda ou um Contrato.')
    now = _now()
    workflow = dict(meta.get('workflow') or {})
    workflow.update({
        'control_ok': True,
        'control_at': now.isoformat(),
        'control_by': requested_by or '',
        'validation_status': 'awaiting_validation',
        'validation_error': '',
    })
    meta['workflow'] = workflow
    if isinstance(cached, dict):
        cached['document'] = document_data
        cached['controlled_at'] = now.isoformat()
        cached['controlled_by'] = requested_by or ''
        meta['llm_full_extraction'] = cached
    document.processing_meta_json = _json_dumps(meta)
    document.json_resultado = _json_dumps(document_data)
    document.invoice_type = _infer_invoice_type(document_data, getattr(document, 'extracted_text', ''))
    document.feid = _safe_int(customer.get('feid'), 0) or document.feid
    document.fornecedor_no = _safe_int(supplier.get('supplier_no') or supplier.get('no'), 0) or document.fornecedor_no
    document.fornecedor_nome_detetado = str(supplier.get('name') or supplier.get('llm_name') or '')[:120]
    document.fornecedor_nif_detetado = str(supplier.get('tax_id') or '')[:40]
    document.processing_stage = 'controlled'
    document.processing_status = 'parsed_ok'
    document.management_validated = True
    document.management_validated_at = now
    document.management_validated_by = requested_by or ''
    document.last_processing_error = ''
    document.dtalt = now
    document.useralteracao = requested_by or document.useralteracao or ''
    db.session.commit()
    return {'ok': True, 'document_id': document.docinstamp, 'workflow': workflow}


def preflight_document_inbox_stage(
    document_stamp: str,
    view: str,
    reviewed_document: dict[str, Any] | None = None,
    requested_by: str = '',
    allow_duplicate_override: bool = False,
) -> dict[str, Any]:
    """Validate a workflow transition without changing the document."""
    document = db.session.get(DocInbox, str(document_stamp or '').strip())
    if not document:
        raise ValueError('Documento do inbox não encontrado.')
    stage = _normalize_document_inbox_view(view)
    result = dict(reviewed_document or {}) or _json_loads(document.json_resultado, {})
    document_type = str(result.get('document_type') or document.doc_type_detected or 'unknown').strip().lower()
    result.setdefault('document_type', document_type)
    result.setdefault('invoice_type', _normalize_invoice_type(document.invoice_type))
    from services.document_ai_distribution_service import assert_document_distribution_available
    from services.document_ai_required_info_service import evaluate_required_info
    if stage == 'home':
        duplicates = _refresh_document_duplicate_state(document, result)
        if duplicates:
            meta = _json_loads(document.processing_meta_json, {})
            duplicate_ids = sorted(str(item.get('document_id') or '') for item in duplicates)
            previous_override = dict(meta.get('duplicate_override') or {})
            previous_ids = sorted(str(value or '') for value in (previous_override.get('document_ids') or []))
            if duplicate_ids != previous_ids:
                if not allow_duplicate_override:
                    return {
                        'ok': False,
                        'view': stage,
                        'duplicate_confirmation_required': True,
                        'duplicates': duplicates,
                        'message': 'Documento duplicado. Confirma o documento existente antes de validar.',
                    }
                meta['duplicate_override'] = {
                    'document_ids': duplicate_ids,
                    'confirmed_at': _now().isoformat(),
                    'confirmed_by': requested_by or '',
                }
                document.processing_meta_json = _json_dumps(meta)
                _document_log(document.docinstamp, 'duplicate_override', 'warning', 'Validação excecional de duplicado confirmada.', {
                    'duplicate_document_ids': duplicate_ids,
                    'confirmed_by': requested_by or '',
                })
                db.session.commit()
        assessment = assess_document_reception(
            result,
            stored_feid=document.feid,
            stored_supplier_no=document.fornecedor_no,
            processing_status=document.processing_status,
        )
        if assessment['multiple_documents']:
            raise ValueError('O PDF contém vários documentos.')
        if str(document.processing_status or '').strip().lower() == 'parse_error':
            raise ValueError('Erro de leitura.')
        required_info = evaluate_required_info(
            result, stage, stored_feid=document.feid,
            stored_supplier_no=document.fornecedor_no,
            processing_meta=_json_loads(document.processing_meta_json, {}),
        )
        if _missing_intersol_agency(result.get('customer')):
            required_info = dict(required_info)
            required_info['ok'] = False
            required_info['missing'] = list(dict.fromkeys([
                *(required_info.get('missing') or []), 'intersol_agency',
            ]))
            required_info['messages'] = list(dict.fromkeys([
                *(required_info.get('messages') or []), 'Falta a agência.',
            ]))
            required_info['targets'] = list(dict.fromkeys([
                *(required_info.get('targets') or []), 'docAiExtractModeCard',
            ]))
        reception_messages = {
            'entity': 'Falta a entidade.',
            'supplier': 'Falta o fornecedor.',
            'classification': 'Falta a classificação.',
            'invoice_type': 'Falta o tipo de fatura.',
        }
        reception_targets = {
            'entity': 'docAiExtractCustomerCard',
            'supplier': 'docAiExtractSupplierCard',
            'classification': 'docAiExtractModeCard',
            'invoice_type': 'docAiExtractModeCard',
        }
        canonical_missing = [
            code for code in assessment['missing']
            if code in reception_messages
        ]
        if canonical_missing:
            required_info = dict(required_info)
            required_info['ok'] = False
            required_info['missing'] = list(dict.fromkeys([
                *(required_info.get('missing') or []), *canonical_missing,
            ]))
            required_info['messages'] = list(dict.fromkeys([
                *(required_info.get('messages') or []),
                *(reception_messages[code] for code in canonical_missing),
            ]))
            required_info['targets'] = sorted(set([
                *(required_info.get('targets') or []),
                *(reception_targets[code] for code in canonical_missing),
            ]))
        if not required_info['ok']:
            return {
                'ok': False, 'view': stage, 'assessment': assessment,
                'duplicates': duplicates, 'required_info': required_info,
                'message': required_info['messages'][0],
            }
        assert_document_distribution_available(document, stage, document_type)
        return {'ok': True, 'view': stage, 'assessment': assessment, 'duplicates': duplicates, 'required_info': required_info}
    if not bool(document.reception_validated):
        raise ValueError('O documento ainda não foi validado pela Receção.')
    if stage == 'management':
        if document_type not in {'invoice', 'provisional_invoice'}:
            raise ValueError('Este documento não pertence ao Controlo de Gestão.')
    if stage == 'accounting':
        assignment_state = db.session.execute(text("""
            SELECT TOP (1) STATE_CODE FROM dbo.DOC_AI_WORKFLOW_ASSIGNMENT
            WHERE DOCINSTAMP=:document_id AND VIEW_CODE='accounting' AND ATIVO=1
            ORDER BY DTALT DESC, DTCRI DESC
        """), {'document_id': document.docinstamp}).scalar()
        if str(assignment_state or '').strip().lower() == 'pending':
            return {
                'ok': False, 'view': stage, 'distribution_pending': True,
                'message': 'O documento ainda está pendente em Contabilidade.',
            }
        if not assignment_state and document_type != 'credit_note' and not bool(document.management_validated):
            raise ValueError('O documento ainda não foi validado pelo Controlo de Gestão.')
    required_info = evaluate_required_info(
        result, stage, stored_feid=document.feid,
        stored_supplier_no=document.fornecedor_no,
        processing_meta=_json_loads(document.processing_meta_json, {}),
    )
    if not required_info['ok']:
        return {
            'ok': False, 'view': stage, 'required_info': required_info,
            'message': required_info['messages'][0],
        }
    assert_document_distribution_available(document, stage, document_type)
    return {'ok': True, 'view': stage, 'required_info': required_info}


def _integrate_reception_document(
    document: DocInbox,
    document_data: dict[str, Any],
    requested_by: str,
    integration_permissions: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Run the historical PHC reception action once and persist its identity."""
    meta = _json_loads(document.processing_meta_json, {})
    existing = dict(meta.get('phc_integration') or {})
    if existing.get('status') == 'confirmed' and (existing.get('crstamp') or existing.get('fostamp')):
        return existing

    document_type = str(document_data.get('document_type') or '').strip().lower()
    is_correspondence = document_type in {'mail', 'bank_statement'}
    is_provisional_purchase = _is_provisional_purchase_source_type(document_type)
    if not is_correspondence and not is_provisional_purchase:
        return existing

    permission_key = 'correspondence' if is_correspondence else 'provisional_invoice'
    if integration_permissions is not None and not bool(integration_permissions.get(permission_key)):
        raise PermissionError('Sem permissão para executar a integração PHC desta validação.')

    absolute_path = _document_absolute_path(document)
    if not absolute_path or not os.path.isfile(absolute_path):
        raise FileNotFoundError('O PDF original não está disponível para concluir a validação.')
    with open(absolute_path, 'rb') as handle:
        file_bytes = handle.read()
    if not file_bytes:
        raise ValueError('O PDF original está vazio.')

    if is_correspondence:
        result = submit_correspondence_to_phc(
            document_data,
            file_bytes,
            document.file_name or os.path.basename(absolute_path),
            requested_by,
        )
        integration_type = 'correspondence'
    else:
        result = submit_provisional_invoice_to_phc(
            document_data,
            file_bytes,
            document.file_name or os.path.basename(absolute_path),
            requested_by,
        )
        integration_type = 'provisional_invoice'

    integration = {
        'type': integration_type,
        'status': 'confirmed',
        'integrated_at': _now().isoformat(),
        'integrated_by': requested_by or '',
        **{
            key: result.get(key)
            for key in (
                'crstamp', 'fostamp', 'reference', 'year', 'document_number',
                'phc_database', 'file_name', 'ged_path', 'ged_paths', 'duplicate',
            )
            if result.get(key) not in (None, '')
        },
    }
    meta['phc_integration'] = integration
    document.processing_meta_json = _json_dumps(meta)
    if is_provisional_purchase:
        document.processing_status = 'provisional_invoice'
    document.last_processing_error = ''
    document.dtalt = _now()
    document.useralteracao = requested_by or document.useralteracao or ''
    return integration


def validate_document_inbox_stage(
    document_stamp: str,
    view: str,
    requested_by: str,
    reviewed_document: dict[str, Any] | None = None,
    integration_permissions: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Persist a business workflow transition after server-side validation."""
    stage = _normalize_document_inbox_view(view)
    document = db.session.get(DocInbox, str(document_stamp or '').strip())
    if not document:
        raise ValueError('Documento do inbox não encontrado.')

    def completed_payload() -> dict[str, Any] | None:
        completed = {
            'home': bool(getattr(document, 'reception_validated', False)),
            'management': bool(getattr(document, 'management_validated', False)),
            'accounting': bool(getattr(document, 'accounting_validated', False)),
        }[stage]
        if not completed:
            return None
        existing_integration = dict(
            _json_loads(getattr(document, 'processing_meta_json', ''), {}).get('phc_integration') or {}
        )
        return {
            'ok': True,
            'already_validated': True,
            'document_id': document.docinstamp,
            'view': stage,
            'reception_validated': bool(getattr(document, 'reception_validated', False)),
            'management_validated': bool(getattr(document, 'management_validated', False)),
            'accounting_validated': bool(getattr(document, 'accounting_validated', False)),
            'distribution': {'ok': True, 'unchanged': True},
            'phc_integration': existing_integration,
        }

    already_completed = completed_payload()
    if already_completed:
        return already_completed
    db.session.execute(text("""
        SELECT DOCINSTAMP
        FROM dbo.DOC_INBOX WITH (UPDLOCK, HOLDLOCK)
        WHERE DOCINSTAMP=:document_id
    """), {'document_id': document.docinstamp}).scalar_one()
    db.session.refresh(document)
    now = _now()
    already_completed = completed_payload()
    if already_completed:
        return already_completed
    result = dict(reviewed_document or {}) or _json_loads(document.json_resultado, {})
    if reviewed_document:
        customer = dict(result.get('customer') or {})
        supplier = dict(result.get('supplier') or {})
        document.json_resultado = _json_dumps(result)
        document.feid = _safe_int(customer.get('feid'), 0) or document.feid
        document.fornecedor_no = _safe_int(supplier.get('supplier_no') or supplier.get('no'), 0) or document.fornecedor_no
        document.fornecedor_nome_detetado = str(supplier.get('name') or supplier.get('llm_name') or '')[:120]
        document.fornecedor_nif_detetado = str(supplier.get('tax_id') or '')[:40]
        document.doc_type_detected = str(result.get('document_type') or document.doc_type_detected or 'unknown')[:30]
    document_type = str(result.get('document_type') or document.doc_type_detected or 'unknown').strip().lower()
    invoice_type = _normalize_invoice_type(result.get('invoice_type') or document.invoice_type)
    if invoice_type == 'unknown':
        invoice_type = _infer_invoice_type(result, document.extracted_text)

    preflight = preflight_document_inbox_stage(
        document.docinstamp,
        stage,
        result,
        requested_by=requested_by,
    )
    if not preflight.get('ok'):
        raise ValueError(str(preflight.get('message') or 'Não foi possível validar a etapa documental.'))

    if stage == 'home':
        integration = _integrate_reception_document(
            document,
            result,
            requested_by,
            integration_permissions=integration_permissions,
        )
        document.reception_validated = True
        document.reception_validated_at = now
        document.reception_validated_by = requested_by or ''
    elif stage == 'management':
        document.management_validated = True
        document.management_validated_at = now
        document.management_validated_by = requested_by or ''
    else:
        document.accounting_validated = True
        document.accounting_validated_at = now
        document.accounting_validated_by = requested_by or ''

    from services.document_ai_distribution_service import apply_document_distribution
    distribution = apply_document_distribution(document, stage, requested_by)

    document.invoice_type = invoice_type
    document.processing_stage = f'{stage}_validated'
    document.dtalt = now
    document.useralteracao = requested_by or document.useralteracao or ''
    _document_log(document.docinstamp, 'workflow', 'ok', f'Etapa {stage} validada.', {
        'view': stage,
        'requested_by': requested_by or '',
    })
    db.session.commit()
    return {
        'ok': True,
        'document_id': document.docinstamp,
        'view': stage,
        'reception_validated': bool(document.reception_validated),
        'management_validated': bool(document.management_validated),
        'accounting_validated': bool(document.accounting_validated),
        'distribution': distribution,
        'phc_integration': integration if stage == 'home' else dict(
            _json_loads(document.processing_meta_json, {}).get('phc_integration') or {}
        ),
    }


def require_document_control_ok(document_stamp: str) -> None:
    document = db.session.get(DocInbox, str(document_stamp or '').strip())
    if not document:
        raise ValueError('Documento do inbox não encontrado.')
    workflow = _json_loads(document.processing_meta_json, {}).get('workflow') or {}
    if not bool(workflow.get('control_ok')):
        raise ValueError('Efetua primeiro o Contrôle OK antes de validar.')


def mark_document_validation_error(document_stamp: str, error: str, requested_by: str) -> None:
    document = db.session.get(DocInbox, str(document_stamp or '').strip())
    if not document:
        return
    now = _now()
    meta = _json_loads(document.processing_meta_json, {})
    workflow = dict(meta.get('workflow') or {})
    workflow.update({
        'validation_status': 'error',
        'validation_error': str(error or '')[:2000],
        'validation_at': now.isoformat(),
        'validation_by': requested_by or '',
    })
    meta['workflow'] = workflow
    document.processing_meta_json = _json_dumps(meta)
    document.last_processing_error = str(error or '')[:4000]
    document.processing_stage = 'validation_error'
    document.dtalt = now
    document.useralteracao = requested_by or document.useralteracao or ''
    db.session.commit()


def reset_llm_extraction(document_stamp: str, requested_by: str) -> None:
    document = db.session.get(DocInbox, str(document_stamp or '').strip())
    if not document:
        raise ValueError('Documento do inbox não encontrado.')
    meta = _json_loads(document.processing_meta_json, {})
    meta.pop('llm_full_extraction', None)
    meta.pop('phc_origin', None)
    meta.pop('phc_origins', None)
    integrated_as_provisional = (
        str((meta.get('phc_integration') or {}).get('type') or '').strip().lower()
        == 'provisional_invoice'
    )
    document.processing_meta_json = _json_dumps(meta)
    document.json_resultado = _json_dumps(canonical_result_base('unknown'))
    document.fornecedor_no = None
    document.fornecedor_nome_detetado = ''
    document.fornecedor_nif_detetado = ''
    document.doc_type_detected = 'unknown'
    document.confidence_score = 0
    document.extraction_method = 'failed'
    document.extraction_quality_score = 0
    document.processing_stage = 'new'
    document.processing_status = 'provisional_invoice' if integrated_as_provisional else 'new'
    document.last_processing_error = ''
    document.dtproc = None
    document.dtalt = _now()
    document.useralteracao = requested_by or document.useralteracao or ''
    db.session.commit()


def save_llm_extraction(document_stamp: str, payload: dict[str, Any], requested_by: str) -> dict[str, Any]:
    document = db.session.get(DocInbox, str(document_stamp or '').strip())
    if not document:
        raise ValueError('Documento do inbox não encontrado.')
    document_data = dict(payload.get('document') or {})
    matching = dict(payload.get('matching') or {})
    customer = dict(document_data.get('customer') or {})
    supplier = dict(document_data.get('supplier') or {})
    confidence = max(0.0, min(1.0, float(document_data.get('confidence') or 0)))
    now = _now()
    meta = _json_loads(document.processing_meta_json, {})
    meta['llm_full_extraction'] = {
        'version': 4,
        'model': str(payload.get('model') or 'LLM'),
        'document': document_data,
        'matching': matching,
        'saved_at': now.isoformat(),
        'saved_by': requested_by or '',
    }
    document.processing_meta_json = _json_dumps(meta)
    document.json_resultado = _json_dumps(document_data)
    document.feid = _safe_int(customer.get('feid'), 0) or document.feid
    document.fornecedor_no = _safe_int(supplier.get('supplier_no') or supplier.get('no'), 0) or None
    document.fornecedor_nome_detetado = str(supplier.get('name') or supplier.get('llm_name') or '')[:120]
    document.fornecedor_nif_detetado = str(supplier.get('tax_id') or '')[:40]
    document.doc_type_detected = str(document_data.get('document_type') or 'unknown')[:30]
    document.invoice_type = _infer_invoice_type(document_data, getattr(document, 'extracted_text', ''))
    document.confidence_score = confidence
    document.extraction_method = 'llm_visual'
    document.extraction_quality_score = confidence
    document.processing_stage = 'llm_extracted'
    integrated_as_provisional = (
        str((meta.get('phc_integration') or {}).get('type') or '').strip().lower()
        == 'provisional_invoice'
    )
    document.processing_status = (
        'provisional_invoice'
        if integrated_as_provisional
        or str(document_data.get('document_type') or '').strip().lower() == 'provisional_invoice'
        else ('parsed_ok' if confidence >= 0.75 else 'review_required')
    )
    document.last_processing_error = ''
    document.dtproc = now
    document.dtalt = now
    document.useralteracao = requested_by or document.useralteracao or ''
    _refresh_document_duplicate_state(document, document_data)
    db.session.commit()
    return get_cached_llm_extraction(document.docinstamp) or {}


def mark_document_as_provisional_invoice(
    document_stamp: str,
    integration_result: dict[str, Any] | None,
    requested_by: str,
    expected_file_hash: str = '',
) -> dict[str, Any]:
    document = db.session.get(DocInbox, str(document_stamp or '').strip())
    if not document:
        raise ValueError('Documento do inbox não encontrado.')
    expected_hash = str(expected_file_hash or '').strip().lower()
    stored_hash = str(document.file_hash or '').strip().lower()
    if expected_hash and stored_hash and expected_hash != stored_hash:
        raise ValueError('O documento submetido não corresponde ao documento selecionado no inbox.')
    result = dict(integration_result or {})
    now = _now()
    meta = _json_loads(document.processing_meta_json, {})
    meta['phc_integration'] = {
        'type': 'provisional_invoice',
        'fostamp': str(result.get('fostamp') or '').strip(),
        'document_number': str(result.get('document_number') or '').strip(),
        'phc_database': str(result.get('phc_database') or '').strip(),
        'duplicate': bool(result.get('duplicate')),
        'integrated_at': now.isoformat(),
        'integrated_by': requested_by or '',
    }
    workflow = dict(meta.get('workflow') or {})
    workflow.update({
        'control_ok': True,
        'validation_status': 'accounting',
        'validation_error': '',
        'validation_at': now.isoformat(),
        'validation_by': requested_by or '',
    })
    meta['workflow'] = workflow
    document.processing_meta_json = _json_dumps(meta)
    document.processing_stage = 'phc_integrated'
    document.processing_status = 'provisional_invoice'
    document.dtalt = now
    document.useralteracao = requested_by or document.useralteracao or ''
    db.session.commit()
    return {
        'ok': True,
        'document_id': document.docinstamp,
        'status': document.processing_status,
    }


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
        tax_column = _fl_tax_id_column()
        if not tax_column:
            break
        row = db.session.execute(text("""
            SELECT TOP 1
                CAST(FL.NO AS int) AS NO,
                LTRIM(RTRIM(ISNULL(FL.NOME, ''))) AS NOME,
                LTRIM(RTRIM(CAST(ISNULL(FL.{tax_column}, '') AS varchar(40)))) AS NIF
            FROM dbo.FL FL
            WHERE REPLACE(REPLACE(REPLACE(REPLACE(LTRIM(RTRIM(CAST(ISNULL(FL.{tax_column}, '') AS varchar(40)))), ' ', ''), '-', ''), '.', ''), '/', '') = :vat
            {feid_filter}
        """.format(feid_filter=feid_filter, tax_column=tax_column)), {
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
        'bank_statement': 0.0,
        'mail': 0.0,
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

    bank_context = bool(re.search(
        r'\b(?:iban|bic|solde|debit|débit|credit|crédit|date valeur|mouvement|mouvements|banque|bpi france|credit mutuel|crédit mutuel)\b',
        normalized,
    ))
    if strong_hits_by_type.get('bank_statement') and not bank_context:
        strong_hits_by_type.pop('bank_statement', None)
        score_map['bank_statement'] = min(score_map.get('bank_statement', 0), 0.42)
        reasons.append('bank_statement_guarded_without_bank_context')

    credit_terms = [term for term in strong_hits_by_type.get('credit_note', []) if _normalize_text(term) in normalized]
    if credit_terms:
        return {
            'doc_type': 'credit_note',
            'score': round(min(score_map.get('credit_note', 0.92), 0.99), 4),
            'supplier_no': (supplier_match or {}).get('supplier_no'),
            'reasons': [f'strong_term:{term}' for term in credit_terms],
        }

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
    if bank_context and re.search(r'\breleve\b|\brelevé\b|\bextrait\b|\bcompte\b', normalized):
        score_map['bank_statement'] += 0.2
        reasons.append('bank_statement_context')
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
        'doc_type': normalize_document_type(template.doc_type),
        'doc_type_label': _document_ai_doc_type_label(template.doc_type),
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
    feid = _safe_int(filters.get('feid'), 0)
    if feid > 0:
        where_parts.append('CAST(ISNULL(D.FEID, 0) AS int) = :feid')
        params['feid'] = feid
    allowed_feids = filters.get('allowed_feids')
    if allowed_feids is not None:
        normalized_feids = sorted({_safe_int(value, 0) for value in allowed_feids if _safe_int(value, 0) > 0})
        if not normalized_feids:
            where_parts.append('1 = 0')
        else:
            placeholders = []
            for index, allowed_feid in enumerate(normalized_feids):
                key = f'allowed_feid_{index}'
                placeholders.append(f':{key}')
                params[key] = allowed_feid
            where_parts.append(f"CAST(ISNULL(D.FEID, 0) AS int) IN ({', '.join(placeholders)})")
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


DOC_AI_INBOX_VIEWS = [
    {'value': 'home', 'label': 'Receção'},
    {'value': 'management', 'label': 'Controlo de Gestão'},
    {'value': 'accounting', 'label': 'Contabilidade'},
]

DOC_AI_INBOX_UNSPLIT_SOURCE_SQL = """
NULLIF(
    JSON_VALUE(
        CASE WHEN ISJSON(ISNULL(D.PROCESSING_META_JSON, '')) = 1
             THEN D.PROCESSING_META_JSON ELSE '{}'
        END,
        '$.split_output.batch_id'
    ),
    ''
) IS NULL
"""


def _normalize_document_inbox_view(value: Any) -> str:
    normalized = str(value or '').strip().lower()
    valid_values = {item['value'] for item in DOC_AI_INBOX_VIEWS}
    return normalized if normalized in valid_values else 'home'


def _document_inbox_scope_sql(view: str = 'home', archived: bool = False) -> str:
    normalized = _normalize_document_inbox_view(view)
    latest_event = f"""
        ISNULL((
            SELECT TOP (1) VE.EVENT_CODE
            FROM dbo.DOC_AI_VIEW_EVENT VE
            WHERE VE.DOCINSTAMP=D.DOCINSTAMP AND VE.VIEW_CODE='{normalized}'
            ORDER BY VE.DTCRI DESC, VE.DOCVIEWEVENTSTAMP DESC
        ), '')
    """.strip()
    if archived:
        workflow_scope = {
            'home': 'ISNULL(D.RECEPTION_VALIDATED, 0) = 1',
            'management': """
                EXISTS (
                    SELECT 1 FROM dbo.DOC_AI_WORKFLOW_ASSIGNMENT WA
                    WHERE WA.DOCINSTAMP=D.DOCINSTAMP AND WA.VIEW_CODE='management'
                      AND WA.VALIDADO=1
                )
                OR (
                    NOT EXISTS (SELECT 1 FROM dbo.DOC_AI_WORKFLOW_ASSIGNMENT WX WHERE WX.DOCINSTAMP=D.DOCINSTAMP)
                    AND ISNULL(D.MANAGEMENT_VALIDATED, 0) = 1
                )
            """,
            'accounting': """
                EXISTS (
                    SELECT 1 FROM dbo.DOC_AI_WORKFLOW_ASSIGNMENT WA
                    WHERE WA.DOCINSTAMP=D.DOCINSTAMP AND WA.VIEW_CODE='accounting'
                      AND WA.VALIDADO=1
                )
                OR (
                    NOT EXISTS (SELECT 1 FROM dbo.DOC_AI_WORKFLOW_ASSIGNMENT WX WHERE WX.DOCINSTAMP=D.DOCINSTAMP)
                    AND ISNULL(D.ACCOUNTING_VALIDATED, 0) = 1
                )
            """,
        }[normalized]
        workflow_scope = f"({latest_event} = 'deleted') OR ({latest_event} <> 'deleted' AND ({workflow_scope}))"
    else:
        workflow_scope = {
            'home': 'ISNULL(D.RECEPTION_VALIDATED, 0) = 0',
            'management': """
                EXISTS (
                    SELECT 1 FROM dbo.DOC_AI_WORKFLOW_ASSIGNMENT WA
                    WHERE WA.DOCINSTAMP=D.DOCINSTAMP AND WA.VIEW_CODE='management'
                      AND WA.ATIVO=1 AND WA.VALIDADO=0
                )
                OR (
                    NOT EXISTS (SELECT 1 FROM dbo.DOC_AI_WORKFLOW_ASSIGNMENT WX WHERE WX.DOCINSTAMP=D.DOCINSTAMP)
                    AND ISNULL(D.RECEPTION_VALIDATED, 0) = 1
                    AND ISNULL(D.MANAGEMENT_VALIDATED, 0) = 0
                    AND LOWER(LTRIM(RTRIM(ISNULL(D.DOC_TYPE_DETECTED, ''))))
                        IN ('invoice', 'provisional_invoice')
                )
            """,
            'accounting': """
                EXISTS (
                    SELECT 1 FROM dbo.DOC_AI_WORKFLOW_ASSIGNMENT WA
                    WHERE WA.DOCINSTAMP=D.DOCINSTAMP AND WA.VIEW_CODE='accounting'
                      AND WA.ATIVO=1 AND WA.VALIDADO=0
                )
                OR (
                    NOT EXISTS (SELECT 1 FROM dbo.DOC_AI_WORKFLOW_ASSIGNMENT WX WHERE WX.DOCINSTAMP=D.DOCINSTAMP)
                    AND ISNULL(D.RECEPTION_VALIDATED, 0) = 1
                    AND ISNULL(D.ACCOUNTING_VALIDATED, 0) = 0
                    AND LOWER(LTRIM(RTRIM(ISNULL(D.DOC_TYPE_DETECTED, ''))))
                        IN ('invoice', 'provisional_invoice', 'credit_note')
                )
            """,
        }[normalized].strip()
        workflow_scope = f"({latest_event} <> 'deleted') AND ({workflow_scope})"
    return f'({DOC_AI_INBOX_UNSPLIT_SOURCE_SQL.strip()}) AND ({workflow_scope})'


def _normalize_invoice_type(value: Any) -> str:
    normalized = _normalize_text(value).replace(' ', '_')
    aliases = {
        'betao': 'concrete',
        'concrete': 'concrete',
        'beton': 'concrete',
        'material': 'material',
        'materiais': 'material',
        'materiel': 'material',
        'services': 'services',
        'service': 'services',
        'servicos': 'services',
    }
    return aliases.get(normalized, 'unknown')


def _invoice_type_label(value: Any) -> str:
    return {
        'concrete': 'Betão',
        'material': 'Material',
        'services': 'Serviços',
    }.get(_normalize_invoice_type(value), '-')


def _infer_invoice_type(result: dict[str, Any], extracted_text: Any = '') -> str:
    explicit = _normalize_invoice_type(result.get('invoice_type'))
    if explicit != 'unknown':
        return explicit
    fragments = [str(extracted_text or '')]
    for line in result.get('lines') or []:
        if isinstance(line, dict):
            fragments.extend((str(line.get('description') or ''), str(line.get('ref') or '')))
    normalized = _normalize_text(' '.join(fragments))
    if any(token in normalized for token in ('beton', 'concrete', 'betao', 'toupie')):
        return 'concrete'
    if any(token in normalized for token in ('honoraires', 'prestation', 'service', 'main d oeuvre', 'consult')):
        return 'services'
    if any(isinstance(line, dict) and str(line.get('description') or '').strip() for line in (result.get('lines') or [])):
        return 'material'
    return 'unknown'


def assess_document_reception(
    document_data: dict[str, Any] | None,
    *,
    stored_feid: Any = 0,
    stored_supplier_no: Any = 0,
    processing_status: Any = '',
) -> dict[str, Any]:
    """Return the canonical Receção completeness state and its separate reasons."""
    result = dict(document_data or {})
    customer = dict(result.get('customer') or {})
    supplier = dict(result.get('supplier') or {})
    raw_type = _normalize_text(result.get('document_type') or 'unknown').replace(' ', '_')
    document_type = {
        'publicidade': 'advertising',
        'publicity': 'advertising',
        'advertisement': 'advertising',
    }.get(raw_type, raw_type or 'unknown')
    feid = _safe_int(customer.get('feid') or stored_feid, 0)
    supplier_no = _safe_int(supplier.get('supplier_no') or supplier.get('no') or stored_supplier_no, 0)
    supplier_absent = bool(
        result.get('supplier_explicitly_absent')
        or supplier.get('explicitly_absent')
        or supplier.get('without_supplier')
    )
    batch = dict(result.get('document_batch') or {})
    multiple_documents = bool(batch.get('contains_multiple_documents'))
    invoice_type = _normalize_invoice_type(result.get('invoice_type'))

    missing = []
    if not feid:
        missing.append('entity')
    if not supplier_no and not (document_type == 'advertising' and supplier_absent):
        missing.append('supplier')
    if document_type == 'unknown':
        missing.append('classification')
    if document_type in {'invoice', 'provisional_invoice'} and invoice_type == 'unknown':
        missing.append('invoice_type')

    reasons = []
    if multiple_documents:
        reasons.append('Vários documentos no PDF')
    if 'entity' in missing:
        reasons.append('Falta Entidade')
    if 'supplier' in missing:
        reasons.append('Falta Fornecedor')
    if 'classification' in missing:
        reasons.append('Identificação Impossível')
    if str(processing_status or '').strip().lower() == 'parse_error':
        reasons.append('Erro de leitura')

    meaningful = [
        feid,
        supplier_no,
        document_type if document_type != 'unknown' else '',
        invoice_type if invoice_type != 'unknown' else '',
    ]
    if multiple_documents or str(processing_status or '').strip().lower() == 'parse_error':
        state = 'Bloqueio'
    elif not missing:
        state = 'OK'
    elif any(meaningful):
        state = 'Ação'
    else:
        state = 'Bloqueio'
    return {
        'state': state,
        'reasons': reasons,
        'missing': missing,
        'document_type': document_type,
        'invoice_type': invoice_type,
        'multiple_documents': multiple_documents,
        'supplier_explicitly_absent': supplier_absent,
    }


def normalize_document_duplicate_identity(
    document_data: dict[str, Any] | None,
    *,
    stored_feid: Any = 0,
    stored_supplier_no: Any = 0,
    stored_supplier_tax_id: Any = '',
    file_hash: Any = '',
) -> dict[str, Any]:
    """Build the stable business identity used by the duplicate index."""
    result = dict(document_data or {})
    customer = dict(result.get('customer') or {})
    supplier = dict(result.get('supplier') or {})
    totals = dict(result.get('totals') or {})
    raw_type = _normalize_text(result.get('document_type') or 'unknown').replace(' ', '_')
    doc_class = 'invoice' if raw_type in {'invoice', 'provisional_invoice'} else raw_type
    document_date = _safe_date_iso(result.get('document_date'))
    gross_total = _safe_decimal(totals.get('gross_total'))
    if gross_total is not None:
        gross_total = float(Decimal(str(gross_total)).quantize(Decimal('0.01')))
    return {
        'feid': _safe_int(customer.get('feid') or stored_feid, 0) or None,
        'supplier_no': _safe_int(
            supplier.get('supplier_no') or supplier.get('no') or stored_supplier_no,
            0,
        ) or None,
        'supplier_tax_id': _digits_only(supplier.get('tax_id') or stored_supplier_tax_id),
        'doc_class': doc_class or 'unknown',
        'document_number': re.sub(r'[^A-Z0-9]', '', str(result.get('document_number') or '').upper()),
        'document_date': document_date or None,
        'document_year': int(document_date[:4]) if document_date else None,
        'gross_total': gross_total,
        'currency': re.sub(r'[^A-Z]', '', str(result.get('currency') or '').upper())[:12],
        'file_hash': str(file_hash or '').strip().lower(),
    }


def document_duplicate_identities_match(left: dict[str, Any], right: dict[str, Any]) -> str:
    """Return the central duplicate match type, preserving the public API."""
    return str(evaluate_duplicate_match(left, right).get('match_type') or '')


def _sync_document_duplicate_index(document: DocInbox, result: dict[str, Any] | None = None) -> dict[str, Any]:
    processing_meta = _json_loads(document.processing_meta_json, {})
    identity = normalize_document_duplicate_identity(
        result if isinstance(result, dict) else _json_loads(document.json_resultado, {}),
        stored_feid=document.feid,
        stored_supplier_no=document.fornecedor_no,
        stored_supplier_tax_id=document.fornecedor_nif_detetado,
        file_hash=processing_meta.get('content_hash') or document.file_hash,
    )
    params = {
        'docinstamp': document.docinstamp,
        **identity,
        'processing_stage': str(document.processing_stage or '')[:40],
        'archived': bool(document.accounting_validated),
    }
    db.session.execute(text("""
        MERGE dbo.DOC_DUPLICATE_INDEX AS target
        USING (SELECT :docinstamp AS DOCINSTAMP) AS source
           ON target.DOCINSTAMP = source.DOCINSTAMP
        WHEN MATCHED THEN UPDATE SET
            FEID = :feid,
            FORNECEDOR_NO = :supplier_no,
            FORNECEDOR_NIF = :supplier_tax_id,
            DOC_CLASS = :doc_class,
            DOC_NUMBER_NORMALIZED = :document_number,
            DOC_DATE = :document_date,
            DOC_YEAR = :document_year,
            GROSS_TOTAL = :gross_total,
            CURRENCY = :currency,
            FILE_HASH = :file_hash,
            PROCESSING_STAGE = :processing_stage,
            ATIVO = 1,
            ARQUIVADO = :archived,
            DTALT = GETDATE()
        WHEN NOT MATCHED THEN INSERT (
            DOCINSTAMP, FEID, FORNECEDOR_NO, FORNECEDOR_NIF, DOC_CLASS,
            DOC_NUMBER_NORMALIZED, DOC_DATE, DOC_YEAR, GROSS_TOTAL, CURRENCY,
            FILE_HASH, PROCESSING_STAGE, ATIVO, ARQUIVADO, DTALT
        ) VALUES (
            :docinstamp, :feid, :supplier_no, :supplier_tax_id, :doc_class,
            :document_number, :document_date, :document_year, :gross_total, :currency,
            :file_hash, :processing_stage, 1, :archived, GETDATE()
        );
    """), params)
    return identity


def find_document_duplicates(
    document: DocInbox,
    result: dict[str, Any] | None = None,
    *,
    sync_current: bool = True,
) -> list[dict[str, Any]]:
    identity = (
        _sync_document_duplicate_index(document, result)
        if sync_current
        else normalize_document_duplicate_identity(
            result if isinstance(result, dict) else _json_loads(document.json_resultado, {}),
            stored_feid=document.feid,
            stored_supplier_no=document.fornecedor_no,
            stored_supplier_tax_id=document.fornecedor_nif_detetado,
            file_hash=_json_loads(document.processing_meta_json, {}).get('content_hash') or document.file_hash,
        )
    )
    rows = db.session.execute(text("""
        SELECT
            I.DOCINSTAMP, I.FEID, I.FORNECEDOR_NO, I.FORNECEDOR_NIF,
            I.DOC_CLASS, I.DOC_NUMBER_NORMALIZED, I.DOC_DATE, I.DOC_YEAR,
            I.GROSS_TOTAL, I.CURRENCY, I.FILE_HASH, I.PROCESSING_STAGE,
            D.FILE_NAME, D.RECEPTION_VALIDATED, D.MANAGEMENT_VALIDATED,
            D.ACCOUNTING_VALIDATED
        FROM dbo.DOC_DUPLICATE_INDEX I
        INNER JOIN dbo.DOC_INBOX D ON D.DOCINSTAMP = I.DOCINSTAMP
        WHERE I.ATIVO = 1
          AND I.DOCINSTAMP <> :docinstamp
          AND (
                (:file_hash <> '' AND I.FILE_HASH = :file_hash)
                OR (
                    :doc_class <> 'unknown'
                    AND I.DOC_CLASS = :doc_class
                    AND (
                        (ISNULL(:feid, 0) > 0 AND I.FEID = :feid)
                        OR (ISNULL(:supplier_no, 0) > 0 AND I.FORNECEDOR_NO = :supplier_no)
                        OR (:supplier_tax_id <> '' AND I.FORNECEDOR_NIF = :supplier_tax_id)
                        OR (:document_number <> '' AND I.DOC_NUMBER_NORMALIZED = :document_number)
                    )
                )
          )
        ORDER BY I.DTALT DESC
    """), {'docinstamp': document.docinstamp, **identity}).mappings().all()
    duplicates = []
    for row in rows:
        candidate = {
            'feid': _safe_int(row.get('FEID'), 0) or None,
            'supplier_no': _safe_int(row.get('FORNECEDOR_NO'), 0) or None,
            'supplier_tax_id': _digits_only(row.get('FORNECEDOR_NIF')),
            'doc_class': str(row.get('DOC_CLASS') or ''),
            'document_number': str(row.get('DOC_NUMBER_NORMALIZED') or ''),
            'document_date': row.get('DOC_DATE').isoformat() if row.get('DOC_DATE') else None,
            'document_year': _safe_int(row.get('DOC_YEAR'), 0) or None,
            'gross_total': float(row.get('GROSS_TOTAL')) if row.get('GROSS_TOTAL') is not None else None,
            'currency': str(row.get('CURRENCY') or ''),
            'file_hash': str(row.get('FILE_HASH') or '').lower(),
        }
        assessment = evaluate_duplicate_match(identity, candidate)
        match_type = str(assessment.get('match_type') or '')
        if match_type:
            duplicates.append({
                'document_id': str(row.get('DOCINSTAMP') or ''),
                'file_name': str(row.get('FILE_NAME') or ''),
                'match_type': match_type,
                'classification': str(assessment.get('classification') or 'new'),
                'score': int(assessment.get('score') or 0),
                'matching_fields': list(assessment.get('matching_fields') or []),
                'missing_fields': list(assessment.get('missing_fields') or []),
                'processing_stage': str(row.get('PROCESSING_STAGE') or ''),
                'reception_validated': bool(row.get('RECEPTION_VALIDATED')),
                'management_validated': bool(row.get('MANAGEMENT_VALIDATED')),
                'accounting_validated': bool(row.get('ACCOUNTING_VALIDATED')),
            })
    return duplicates


def _refresh_document_duplicate_state(
    document: DocInbox,
    result: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    duplicates = find_document_duplicates(document, result, sync_current=True)
    meta = _json_loads(document.processing_meta_json, {})
    meta['duplicate_detection'] = {
        'checked_at': _now().isoformat(),
        'duplicates': duplicates,
        'blocked': bool(duplicates),
    }
    document.processing_meta_json = _json_dumps(meta)
    return duplicates


def record_document_duplicate_decision(
    document_stamp: str,
    duplicate_document_stamp: str,
    decision: str,
    requested_by: str = '',
) -> dict[str, Any]:
    """Persist a user's duplicate decision and keep the supporting evidence."""
    document = db.session.get(DocInbox, str(document_stamp or '').strip())
    duplicate_document = db.session.get(DocInbox, str(duplicate_document_stamp or '').strip())
    if not document or not duplicate_document or document.docinstamp == duplicate_document.docinstamp:
        raise ValueError('Correspondência de duplicado inválida.')
    normalized_decision = str(decision or '').strip().lower()
    if normalized_decision not in {'different', 'associate'}:
        raise ValueError('Decisão de duplicado inválida.')

    now = _now()
    meta = _json_loads(document.processing_meta_json, {})
    decisions = list(meta.get('duplicate_decisions') or [])
    decisions.append({
        'decision': normalized_decision,
        'duplicate_document_id': duplicate_document.docinstamp,
        'decided_at': now.isoformat(),
        'decided_by': requested_by or '',
    })
    meta['duplicate_decisions'] = decisions[-20:]
    meta['duplicate_resolution'] = {
        'decision': normalized_decision,
        'duplicate_document_id': duplicate_document.docinstamp,
        'decided_at': now.isoformat(),
        'decided_by': requested_by or '',
    }
    document.processing_meta_json = _json_dumps(meta)
    document.dtalt = now
    document.useralteracao = requested_by or document.useralteracao or ''
    _document_log(
        document.docinstamp,
        'duplicate_decision',
        'warning' if normalized_decision == 'different' else 'ok',
        'Documento confirmado como diferente.' if normalized_decision == 'different' else 'Documento associado ao registo existente.',
        meta['duplicate_resolution'],
    )
    if normalized_decision == 'associate':
        db.session.execute(text("""
            UPDATE dbo.DOC_DUPLICATE_INDEX
            SET ATIVO = 0, DTALT = GETDATE()
            WHERE DOCINSTAMP = :document_stamp
        """), {'document_stamp': document.docinstamp})
        db.session.execute(text("""
            INSERT INTO dbo.DOC_AI_VIEW_EVENT (
                DOCVIEWEVENTSTAMP, DOCINSTAMP, VIEW_CODE, EVENT_CODE,
                PREVIOUS_STATE, USUARIO, DTCRI
            ) VALUES (
                :event_stamp, :document_stamp, 'home', 'deleted',
                'duplicate_associated', :requested_by, GETDATE()
            )
        """), {
            'event_stamp': _new_stamp(),
            'document_stamp': document.docinstamp,
            'requested_by': str(requested_by or '')[:50],
        })
    db.session.commit()
    return {
        'ok': True,
        'decision': normalized_decision,
        'document_id': document.docinstamp,
        'duplicate_document_id': duplicate_document.docinstamp,
        'open_document_id': duplicate_document.docinstamp if normalized_decision == 'associate' else document.docinstamp,
    }


def _document_inbox_global_total(view: str = 'home', archived: bool = False) -> int:
    from services.document_ai_distribution_service import ensure_document_ai_distribution_schema
    ensure_document_ai_distribution_schema()
    scope_sql = _document_inbox_scope_sql(view, archived)
    value = db.session.execute(text(f"""
        SELECT COUNT_BIG(1)
        FROM dbo.DOC_INBOX D
        WHERE {scope_sql}
    """)).scalar()
    return max(_safe_int(value, 0), 0)


def document_belongs_to_inbox_view(document_stamp: str, view: str, archived: bool = False) -> bool:
    """Check document scope server-side before applying view-specific actions."""
    _ensure_document_ai_schema()
    from services.document_ai_distribution_service import ensure_document_ai_distribution_schema
    ensure_document_ai_distribution_schema()
    scope_sql = _document_inbox_scope_sql(view, archived)
    value = db.session.execute(text(f"""
        SELECT TOP (1) 1
        FROM dbo.DOC_INBOX D
        WHERE D.DOCINSTAMP = :document_stamp
          AND {scope_sql}
    """), {'document_stamp': str(document_stamp or '').strip()}).scalar()
    return bool(value)


def list_documents(filters: dict[str, Any] | None = None) -> dict[str, Any]:
    _ensure_document_ai_schema()
    from services.document_ai_distribution_service import ensure_document_ai_distribution_schema
    ensure_document_ai_distribution_schema()
    query_filters = filters or {}
    inbox_view = _normalize_document_inbox_view(query_filters.get('view'))
    archived = str(query_filters.get('archived') or '').strip().lower() in {'1', 'true', 'yes', 'sim', 'on'}
    where_sql, params = _doc_queryset_sql(query_filters)
    scope_sql = _document_inbox_scope_sql(inbox_view, archived)
    if where_sql:
        where_sql = f"{where_sql} AND {scope_sql}"
    else:
        where_sql = f"WHERE {scope_sql}"
    supplier_entity_where = "AND ISNULL(FL.FEID, 0) = ISNULL(D.FEID, 0)" if _column_exists('FL', 'FEID') else ''
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
            D.SOURCE_TABLE,
            D.SOURCE_RECSTAMP,
            D.JSON_RESULTADO,
            D.PROCESSING_META_JSON,
            D.INVOICE_TYPE,
            D.RECEPTION_VALIDATED,
            D.MANAGEMENT_VALIDATED,
            D.ACCOUNTING_VALIDATED,
            WA.STATE_CODE AS WORKFLOW_STATE,
            VE.EVENT_CODE AS VIEW_EVENT_CODE,
            VE.PREVIOUS_STATE AS VIEW_PREVIOUS_STATE,
            D.DTCRI,
            D.DTPROC
        FROM dbo.DOC_INBOX D
        LEFT JOIN dbo.FE FE
          ON CAST(FE.FEID AS int) = D.FEID
        OUTER APPLY (
            SELECT TOP (1) FL.NOME
            FROM dbo.FL FL
            WHERE CAST(FL.NO AS int) = D.FORNECEDOR_NO
              {supplier_entity_where}
            ORDER BY ISNULL(FL.INATIVO, 0), FL.NOME
        ) F
        LEFT JOIN dbo.DOC_TEMPLATE T
          ON T.DOCTEMPLATESTAMP = D.DOCTEMPLATESTAMP
        OUTER APPLY (
            SELECT TOP (1) A.STATE_CODE
            FROM dbo.DOC_AI_WORKFLOW_ASSIGNMENT A
            WHERE A.DOCINSTAMP=D.DOCINSTAMP AND A.VIEW_CODE=:workflow_view
            ORDER BY A.DTALT DESC, A.DTCRI DESC
        ) WA
        OUTER APPLY (
            SELECT TOP (1) E.EVENT_CODE, E.PREVIOUS_STATE
            FROM dbo.DOC_AI_VIEW_EVENT E
            WHERE E.DOCINSTAMP=D.DOCINSTAMP AND E.VIEW_CODE=:workflow_view
            ORDER BY E.DTCRI DESC, E.DOCVIEWEVENTSTAMP DESC
        ) VE
        {where_sql}
        ORDER BY
            TRY_CONVERT(date, JSON_VALUE(CASE WHEN ISJSON(D.JSON_RESULTADO) = 1 THEN D.JSON_RESULTADO ELSE '{{}}' END, '$.document_date')) ASC,
            D.DTCRI ASC,
            D.DOCINSTAMP ASC
    """), {**params, 'workflow_view': inbox_view}).mappings().all()

    entity_scope_sql = ''
    entity_params: dict[str, Any] = {}
    allowed_feids = query_filters.get('allowed_feids')
    if allowed_feids is not None:
        normalized_feids = sorted({_safe_int(value, 0) for value in allowed_feids if _safe_int(value, 0) > 0})
        if not normalized_feids:
            entity_scope_sql = 'AND 1 = 0'
        else:
            placeholders = []
            for index, allowed_feid in enumerate(normalized_feids):
                key = f'entity_allowed_feid_{index}'
                placeholders.append(f':{key}')
                entity_params[key] = allowed_feid
            entity_scope_sql = f"AND CAST(FE.FEID AS int) IN ({', '.join(placeholders)})"
    entity_rows = db.session.execute(text(f"""
        SELECT DISTINCT
            CAST(FE.FEID AS int) AS FEID,
            LTRIM(RTRIM(ISNULL(NULLIF(FE.NOMEFISCAL, ''), ISNULL(FE.NOME, '')))) AS NOME
        FROM dbo.DOC_INBOX D
        INNER JOIN dbo.FE FE ON CAST(FE.FEID AS int) = D.FEID
        WHERE ISNULL(D.FEID, 0) > 0
          {entity_scope_sql}
        ORDER BY NOME
    """), entity_params).mappings().all()

    required_fields_map: dict[str, list[str]] = {}
    if inbox_view == 'management':
        from services.document_ai_required_info_service import required_fields_by_class
        required_fields_map = required_fields_by_class(inbox_view)
    items = []
    counts = {}
    for row in rows:
        result_data = _json_loads(row.get('JSON_RESULTADO'), {})
        processing_meta = _json_loads(row.get('PROCESSING_META_JSON'), {})
        integrated_as_provisional = (
            str((processing_meta.get('phc_integration') or {}).get('type') or '').strip().lower()
            == 'provisional_invoice'
        )
        status = (
            'provisional_invoice'
            if integrated_as_provisional
            or str(row.get('DOC_TYPE_DETECTED') or '').strip().lower() == 'provisional_invoice'
            else str(row.get('PROCESSING_STATUS') or 'new').strip()
        )
        batch_meta = dict(processing_meta.get('batch') or {})
        customer = dict(result_data.get('customer') or {})
        supplier = dict(result_data.get('supplier') or {})
        totals = dict(result_data.get('totals') or {})
        origin_project = dict(result_data.get('origin_project') or {})
        cost_center = str(origin_project.get('ccusto') or '').strip()
        if not cost_center:
            for result_line in result_data.get('lines') or []:
                if not isinstance(result_line, dict):
                    continue
                cost_center = str(result_line.get('ccusto') or result_line.get('project_ccusto') or '').strip()
                if cost_center:
                    break
        document_number = str(result_data.get('document_number') or '').strip()
        document_date = str(result_data.get('document_date') or '').strip()
        document_type = normalize_document_type(
            result_data.get('document_type') or row.get('DOC_TYPE_DETECTED') or 'unknown'
        )
        invoice_type = _normalize_invoice_type(result_data.get('invoice_type') or row.get('INVOICE_TYPE'))
        if invoice_type == 'unknown':
            invoice_type = _infer_invoice_type(result_data)
        reception_assessment = assess_document_reception(
            result_data,
            stored_feid=row.get('FEID'),
            stored_supplier_no=row.get('FORNECEDOR_NO'),
            processing_status=status,
        )
        duplicate_detection = dict(processing_meta.get('duplicate_detection') or {})
        duplicate_matches = [
            item for item in (duplicate_detection.get('duplicates') or [])
            if isinstance(item, dict)
        ]
        if inbox_view == 'management':
            from services.document_ai_distribution_service import normalize_distribution_document_class
            from services.document_ai_required_info_service import evaluate_required_info
            resolved_origins = get_phc_origins_from_meta(processing_meta)
            origin_references = [
                item for item in (result_data.get('origin_references') or [])
                if isinstance(item, dict) and any(str(value or '').strip() for value in item.values())
            ]
            has_resolved_origin = bool(resolved_origins)
            management_assessment = evaluate_required_info(
                result_data,
                inbox_view,
                stored_feid=row.get('FEID'),
                stored_supplier_no=row.get('FORNECEDOR_NO'),
                processing_meta=processing_meta,
                required_fields=required_fields_map.get(normalize_distribution_document_class(document_type), []),
            )
            if management_assessment['ok']:
                business_state = 'OK'
            elif not has_resolved_origin and not origin_references:
                business_state = 'Bloqueio'
            else:
                business_state = 'Ação'
        elif inbox_view == 'accounting':
            workflow_state = str(row.get('WORKFLOW_STATE') or '').strip().lower()
            business_state = {
                'pending': 'Pendente',
                'validated': 'Validado',
                'none': 'Validado',
                'automatic': 'Validado',
            }.get(workflow_state, 'Validado' if document_type == 'credit_note' else (
                'Validado' if bool(row.get('MANAGEMENT_VALIDATED')) else 'Pendente'
            ))
        else:
            business_state = reception_assessment['state']
            if duplicate_matches:
                business_state = 'Bloqueio'
        if archived:
            business_state = 'Eliminado' if str(row.get('VIEW_EVENT_CODE') or '') == 'deleted' else 'Validado'
        display_type = document_type
        if inbox_view == 'management':
            display_type = invoice_type
        elif inbox_view == 'accounting':
            display_type = 'credit_note' if document_type == 'credit_note' else invoice_type
        display_type_label = (
            _invoice_type_label(display_type)
            if display_type in {'concrete', 'material', 'services', 'unknown'} and inbox_view != 'home'
            else next((item['label'] for item in DOC_AI_DOC_TYPES if item['value'] == display_type), display_type or '-')
        )
        counts[status] = counts.get(status, 0) + 1
        items.append({
            'id': str(row.get('DOCINSTAMP') or '').strip(),
            'file_name': str(row.get('FILE_NAME') or '').strip(),
            'file_path': str(row.get('FILE_PATH') or '').strip(),
            'file_ext': str(row.get('FILE_EXT') or '').strip(),
            'mime_type': str(row.get('MIME_TYPE') or '').strip(),
            'extraction_method': str(row.get('EXTRACTION_METHOD') or 'failed').strip() or 'failed',
            'extraction_quality_score': float(row.get('EXTRACTION_QUALITY_SCORE') or 0),
            'doc_type': display_type,
            'doc_type_label': display_type_label,
            'document_type': document_type,
            'document_type_label': next(
                (item['label'] for item in DOC_AI_DOC_TYPES if item['value'] == document_type),
                document_type or '-',
            ),
            'invoice_type': invoice_type,
            'invoice_type_label': _invoice_type_label(invoice_type),
            'business_state': business_state,
            'previous_business_state': str(row.get('VIEW_PREVIOUS_STATE') or '').strip(),
            'business_reasons': (
                list(reception_assessment['reasons']) + (['Documento duplicado'] if duplicate_matches else [])
            ) if inbox_view == 'home' else (
                list(management_assessment['messages']) if inbox_view == 'management' else []
            ),
            'business_missing': reception_assessment['missing'] if inbox_view == 'home' else (
                list(management_assessment['missing']) if inbox_view == 'management' else []
            ),
            'duplicate_matches': duplicate_matches,
            'feid': _safe_int(row.get('FEID'), 0) or None,
            'entity_name': str(row.get('FE_NOME') or customer.get('name') or '').strip(),
            'entity_tax_id': _digits_only(row.get('FE_NIF')),
            'supplier_no': _safe_int(row.get('FORNECEDOR_NO'), 0) or None,
            'supplier_name': str(row.get('FORNECEDOR_NOME') or supplier.get('name') or '').strip(),
            'cost_center': cost_center,
            'document_number': document_number,
            'document_date': document_date,
            'document_value': float(totals.get('gross_total') or 0),
            'currency': str(result_data.get('currency') or '').strip(),
            'template_id': str(row.get('DOCTEMPLATESTAMP') or '').strip(),
            'template_name': str(row.get('TEMPLATE_NOME') or '').strip(),
            'confidence': float(row.get('CONFIDENCE_SCORE') or 0),
            'status': status,
            'reception_validated': bool(row.get('RECEPTION_VALIDATED')),
            'management_validated': bool(row.get('MANAGEMENT_VALIDATED')),
            'accounting_validated': bool(row.get('ACCOUNTING_VALIDATED')),
            'batch_id': str(row.get('SOURCE_RECSTAMP') or '').strip() if str(row.get('SOURCE_TABLE') or '').strip() == 'DOC_AI_BATCH' else '',
            'batch_index': _safe_int(batch_meta.get('index'), 0) or None,
            'batch_count': _safe_int(batch_meta.get('count'), 0) or None,
            'created_at': row.get('DTCRI').isoformat() if row.get('DTCRI') else None,
            'processed_at': row.get('DTPROC').isoformat() if row.get('DTPROC') else None,
        })

    return {
        'items': items,
        'total': len(items),
        'archived': archived,
        'view': inbox_view,
        'views': DOC_AI_INBOX_VIEWS,
        'counts': counts,
        'statuses': DOC_AI_STATUSES,
        'doc_types': list(DOC_AI_DOC_TYPES),
        'invoice_types': [
            {'value': 'concrete', 'label': 'Betão'},
            {'value': 'material', 'label': 'Material'},
            {'value': 'services', 'label': 'Serviços'},
            {'value': 'unknown', 'label': '-'},
        ],
        'entities': [
            {'feid': _safe_int(row.get('FEID'), 0), 'name': str(row.get('NOME') or '').strip()}
            for row in entity_rows
        ],
    }


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
        'version': _document_draft_version(document),
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
    processing_workflow = dict((payload.get('processing_meta') or {}).get('workflow') or {})
    payload['workflow'] = {
        **processing_workflow,
        **_document_workflow_payload(document),
    }
    return payload


class DocumentDraftConflictError(RuntimeError):
    def __init__(self, current_version: str):
        super().__init__('Documento alterado por outro utilizador.')
        self.current_version = current_version


def _document_draft_version(document: DocInbox) -> str:
    value = getattr(document, 'dtalt', None) or getattr(document, 'dtcri', None)
    return value.isoformat(timespec='microseconds') if value else ''


def save_document_draft(
    document_stamp: str,
    payload: dict[str, Any],
    requested_by: str,
) -> dict[str, Any]:
    """Persist editable analysis data without advancing its business workflow."""
    _ensure_document_ai_schema()
    stamp = str(document_stamp or '').strip()
    locked = db.session.execute(text("""
        SELECT DOCINSTAMP, DTALT, DTCRI
        FROM dbo.DOC_INBOX WITH (UPDLOCK, ROWLOCK)
        WHERE DOCINSTAMP=:document_id
    """), {'document_id': stamp}).mappings().first()
    if not locked:
        raise ValueError('Documento não encontrado.')

    current_value = locked.get('DTALT') or locked.get('DTCRI')
    current_version = current_value.isoformat(timespec='microseconds') if current_value else ''
    expected_version = str(payload.get('expected_version') or '').strip()
    if expected_version and expected_version != current_version:
        db.session.rollback()
        raise DocumentDraftConflictError(current_version)

    document = db.session.get(DocInbox, stamp)
    if not document:
        raise ValueError('Documento não encontrado.')
    result = payload.get('document')
    if not isinstance(result, dict):
        raise ValueError('Rascunho documental inválido.')

    customer = dict(result.get('customer') or {})
    supplier = dict(result.get('supplier') or {})
    document_type = normalize_document_type(
        result.get('document_type') or document.doc_type_detected or 'unknown'
    )
    invoice_type = _normalize_invoice_type(result.get('invoice_type'))
    if document_type not in {'invoice', 'provisional_invoice', 'credit_note', 'debit_note'}:
        invoice_type = 'unknown'

    document.feid = _safe_int(customer.get('feid'), 0) or None
    if bool(result.get('supplier_explicitly_absent') or supplier.get('explicitly_absent')):
        document.fornecedor_no = None
    else:
        document.fornecedor_no = _safe_int(supplier.get('supplier_no') or supplier.get('no'), 0) or None
    document.fornecedor_nome_detetado = str(supplier.get('name') or supplier.get('llm_name') or '')[:120]
    document.fornecedor_nif_detetado = str(supplier.get('tax_id') or '')[:40]
    document.doc_type_detected = document_type
    document.invoice_type = invoice_type
    document.json_resultado = _json_dumps(result)
    meta = _json_loads(document.processing_meta_json, {})
    cached = meta.get('llm_full_extraction')
    if isinstance(cached, dict):
        cached = dict(cached)
        cached['document'] = result
        cached['draft_saved_at'] = _now().isoformat()
        cached['draft_saved_by'] = str(requested_by or '')[:50]
        meta['llm_full_extraction'] = cached
        document.processing_meta_json = _json_dumps(meta)
    document.dtalt = _now()
    document.useralteracao = str(requested_by or '')[:50]
    db.session.commit()
    return {
        'ok': True,
        'document_id': document.docinstamp,
        'version': _document_draft_version(document),
    }


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


def _document_first_page_image_bytes(absolute_path: str, file_ext: str, mime_type: str) -> tuple[bytes, str]:
    if _is_image(file_ext, mime_type):
        with open(absolute_path, 'rb') as handle:
            return handle.read(), mime_type or mimetypes.guess_type(absolute_path)[0] or 'image/png'
    if not _is_pdf(file_ext, mime_type):
        return b'', ''
    if not importlib.util.find_spec('fitz'):
        return b'', ''
    try:
        import fitz  # type: ignore
        with fitz.open(absolute_path) as pdf:
            if len(pdf) < 1:
                return b'', ''
            pix = pdf[0].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            return pix.tobytes('png'), 'image/png'
    except Exception:
        current_app.logger.info('Document AI: nao foi possivel renderizar primeira pagina para LLM.', exc_info=True)
        return b'', ''


def _document_number_from_visible_text(text_value: str) -> str:
    raw = str(text_value or '')
    patterns = [
        r'\bBon\s+de\s+livraison\s*(?:n[°ºo]\s*)?[:#-]?\s*([A-Z0-9][A-Z0-9./_-]{2,30})',
        r'\b(?:Facture|Invoice|Avoir|Credit\s+note|Nota\s+de\s+cr[eé]dito)\s*(?:n[°ºo]\s*)?[:#-]?\s*([A-Z0-9][A-Z0-9./_-]{2,30})',
        r'\b(?:N[°ºo]|No|Nº)\s*[:#-]?\s*([A-Z0-9][A-Z0-9./_-]{2,30})',
    ]
    for pattern in patterns:
        match = re.search(pattern, raw, flags=re.IGNORECASE)
        if match:
            return str(match.group(1) or '').strip().strip('.;,')
    return ''


def _classification_supplier_looks_operational(supplier_name: str) -> bool:
    normalized = _normalize_text(supplier_name)
    operational_terms = (
        'centrale',
        'chantier',
        'adresse livraison',
        'adresse client',
        'receptionnaire',
        'chauffeur',
    )
    return any(term in normalized for term in operational_terms)


def _correct_visual_supplier_payload(classification: dict[str, Any], extracted_text: str) -> dict[str, Any]:
    supplier_payload = classification.get('supplier') if isinstance(classification.get('supplier'), dict) else {}
    supplier_name = str(supplier_payload.get('name') or '').strip()
    normalized_text = _normalize_text(extracted_text)
    if _classification_supplier_looks_operational(supplier_name) and 'fehr' in normalized_text:
        supplier_payload['name'] = 'Fehr Béton S.A.S.'
        supplier_payload['tax_id'] = supplier_payload.get('tax_id') or 'FR00728501230'
        supplier_payload['corrected_from'] = supplier_name
        classification['supplier'] = supplier_payload
    return classification


def _postprocess_visual_classification(
    classification: dict[str, Any],
    extracted_text: str,
    supplier_candidates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not isinstance(classification, dict):
        return {}
    classification = _correct_visual_supplier_payload(classification, extracted_text)
    supplier_payload = classification.get('supplier') if isinstance(classification.get('supplier'), dict) else {}
    if _classification_supplier_looks_operational(str(supplier_payload.get('name') or '')):
        original_supplier_name = str(supplier_payload.get('name') or '').strip()
        best_candidate = next(
            (
                item for item in (supplier_candidates or [])
                if float(item.get('score') or 0) >= 0.35 and str(item.get('name') or '').strip()
            ),
            None,
        )
        if best_candidate:
            supplier_payload['supplier_no'] = best_candidate.get('supplier_no') or supplier_payload.get('supplier_no') or 0
            supplier_payload['name'] = best_candidate.get('name') or supplier_payload.get('name') or ''
            supplier_payload['tax_id'] = best_candidate.get('tax_id') or supplier_payload.get('tax_id') or ''
            supplier_payload['corrected_from'] = supplier_payload.get('corrected_from') or original_supplier_name
            classification['supplier'] = supplier_payload
    if not str(classification.get('document_number') or '').strip():
        document_number = _document_number_from_visible_text(extracted_text)
        if document_number:
            classification['document_number'] = document_number
    normalized_lines = []
    for item in classification.get('lines') or []:
        if not isinstance(item, dict):
            continue
        description = str(item.get('description') or '').strip()
        qty = _safe_decimal(item.get('qty')) or 0
        if not description and not qty:
            continue
        normalized_lines.append({
            'ref': str(item.get('ref') or '').strip(),
            'description': description,
            'qty': float(qty),
            'unit': str(item.get('unit') or '').strip(),
            'unit_price': float(_safe_decimal(item.get('unit_price')) or 0),
            'discount': float(_safe_decimal(item.get('discount')) or 0),
            'tax_rate': float(_safe_decimal(item.get('tax_rate')) or 0),
            'net_amount': float(_safe_decimal(item.get('net_amount')) or 0),
            'gross_amount': float(_safe_decimal(item.get('gross_amount')) or 0),
        })
    classification['lines'] = normalized_lines
    return classification


def _supplier_candidates_for_llm(text_value: str, feid: int | None = None, limit: int = 40) -> list[dict[str, Any]]:
    normalized_text = _normalize_text(text_value)
    digits_text = _digits_only(text_value)
    candidates = []
    for supplier in _load_suppliers(feid):
        supplier_no = _safe_int(supplier.get('NO'), 0)
        name = str(supplier.get('NOME') or '').strip()
        tax_id = _digits_only(supplier.get('NIF'))
        normalized_name = _normalize_text(name)
        if not name:
            continue
        score = 0.0
        if tax_id and tax_id in digits_text:
            score = max(score, 0.99)
        if normalized_name and normalized_name in normalized_text:
            score = max(score, 0.95)
        name_tokens = [token for token in normalized_name.split(' ') if len(token) > 2]
        if name_tokens:
            token_hits = sum(1 for token in name_tokens if token in normalized_text)
            score = max(score, token_hits / max(len(name_tokens), 1))
        if any(token in normalized_text for token in name_tokens):
            score = max(score, 0.4)
        candidates.append({
            'supplier_no': supplier_no,
            'name': name,
            'tax_id': tax_id,
            'score': round(float(score or 0), 4),
        })
    candidates.sort(key=lambda item: (-float(item.get('score') or 0), str(item.get('name') or '')))
    scored = [item for item in candidates if float(item.get('score') or 0) >= 0.35]
    selected = scored[:max(1, min(int(limit or 40), 80))]
    if len(selected) < 12:
        selected.extend([item for item in candidates if item not in selected][:12 - len(selected)])
    return selected[:max(1, min(int(limit or 40), 80))]


def classify_document_with_llm(document_stamp: str, requested_by: str = '') -> dict[str, Any]:
    _ensure_document_ai_schema()
    document = db.session.get(DocInbox, str(document_stamp or '').strip())
    if not document:
        raise ValueError('Documento não encontrado.')

    absolute_path = _document_absolute_path(document)
    if not os.path.isfile(absolute_path):
        raise FileNotFoundError('Ficheiro original não encontrado.')

    file_bytes = b''
    if _is_pdf(document.file_ext, document.mime_type):
        try:
            if os.path.getsize(absolute_path) <= 20 * 1024 * 1024:
                with open(absolute_path, 'rb') as handle:
                    file_bytes = handle.read()
        except Exception:
            file_bytes = b''
    image_bytes, image_mime_type = _document_first_page_image_bytes(absolute_path, document.file_ext, document.mime_type)
    supplier_candidates = _supplier_candidates_for_llm(document.extracted_text or '', document.feid, limit=50)
    payload = classify_document_visual({
        'file_name': document.file_name or os.path.basename(absolute_path),
        'mime_type': document.mime_type or mimetypes.guess_type(absolute_path)[0] or 'application/octet-stream',
        'file_bytes': file_bytes,
        'image_bytes': image_bytes,
        'image_mime_type': image_mime_type,
        'extracted_text': document.extracted_text or '',
        'supplier_candidates': supplier_candidates,
    })
    if payload.get('ok') and isinstance(payload.get('classification'), dict):
        classification = _postprocess_visual_classification(payload.get('classification') or {}, document.extracted_text or '', supplier_candidates)
        payload['classification'] = classification
        customer_payload = classification.get('customer') if isinstance(classification.get('customer'), dict) else {}
        supplier_payload = classification.get('supplier') if isinstance(classification.get('supplier'), dict) else {}
        customer_match = resolve_fe_entity(customer_payload.get('tax_id') or customer_payload.get('name') or '')
        if customer_match.get('feid'):
            customer_payload['feid'] = customer_match.get('feid')
            customer_payload['matched_name'] = customer_match.get('name') or ''
            classification['customer'] = customer_payload
            document.feid = customer_match.get('feid')
        supplier_match = {}
        supplier_query = supplier_payload.get('tax_id') or supplier_payload.get('name') or ''
        if supplier_query and (customer_match.get('feid') or document.feid):
            candidates = search_suppliers(supplier_query, feid=customer_match.get('feid') or document.feid, limit=1)
            if candidates:
                supplier_match = candidates[0]
                supplier_payload['supplier_no'] = supplier_match.get('no') or supplier_match.get('supplier_no')
                supplier_payload['matched_name'] = supplier_match.get('name') or supplier_match.get('supplier_name') or ''
                classification['supplier'] = supplier_payload
                document.fornecedor_no = supplier_payload.get('supplier_no')
        doc_type = str(classification.get('document_type') or '').strip() or 'unknown'
        if doc_type:
            document.doc_type_detected = doc_type
            document.dtalt = _now()
            document.useralteracao = requested_by or document.useralteracao or document.usercriacao
            meta = _json_loads(document.processing_meta_json, {})
            meta['llm_visual_classification'] = {
                'doc_type': doc_type,
                'confidence': classification.get('confidence'),
                'mode': payload.get('mode') or '',
                'model': payload.get('model') or '',
                'reason': classification.get('reason') or '',
                'supplier_no': supplier_payload.get('supplier_no') if isinstance(supplier_payload, dict) else None,
                'feid': customer_payload.get('feid') if isinstance(customer_payload, dict) else None,
            }
            document.processing_meta_json = _json_dumps(meta)
            _document_log(document.docinstamp, 'llm_classify', 'ok', 'Documento classificado por LLM visual.', meta['llm_visual_classification'])
            db.session.commit()
    return payload


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


def _append_document_view_event(
    document_stamp: str,
    view: str,
    event_code: str,
    requested_by: str = '',
    previous_state: str = '',
) -> dict[str, Any]:
    _ensure_document_ai_schema()
    stamp = str(document_stamp or '').strip()
    normalized_view = _normalize_document_inbox_view(view)
    document = db.session.get(DocInbox, stamp)
    if not document:
        raise ValueError('Documento não encontrado.')
    normalized_event = str(event_code or '').strip().lower()
    if normalized_event not in {'deleted', 'recovered', 'validated'}:
        raise ValueError('Evento documental inválido.')
    db.session.execute(text("""
        INSERT INTO dbo.DOC_AI_VIEW_EVENT (
            DOCVIEWEVENTSTAMP, DOCINSTAMP, VIEW_CODE, EVENT_CODE,
            PREVIOUS_STATE, USUARIO, DTCRI
        ) VALUES (
            :event_stamp, :document_stamp, :view_code, :event_code,
            :previous_state, :requested_by, GETDATE()
        )
    """), {
        'event_stamp': _new_stamp(),
        'document_stamp': stamp,
        'view_code': normalized_view,
        'event_code': normalized_event,
        'previous_state': str(previous_state or '').strip()[:30],
        'requested_by': str(requested_by or '').strip()[:50],
    })
    _document_log(
        stamp,
        f'view_{normalized_event}',
        'ok',
        {
            'deleted': 'Documento eliminado logicamente.',
            'recovered': 'Documento recuperado.',
            'validated': 'Arquivo documental regularizado como validado.',
        }[normalized_event],
        {'view': normalized_view, 'previous_state': str(previous_state or '').strip()},
    )
    db.session.commit()
    return {
        'ok': True,
        'id': stamp,
        'view': normalized_view,
        'event': normalized_event,
        'file_name': document.file_name or '',
    }


def regularize_document_archives(requested_by: str = '', dry_run: bool = True) -> dict[str, Any]:
    """Backfill explicit archive events without changing workflow or PHC data."""
    _ensure_document_ai_schema()
    evidence_sql = {
        'home': 'ISNULL(D.RECEPTION_VALIDATED, 0) = 1',
        'management': """
            EXISTS (
                SELECT 1 FROM dbo.DOC_AI_WORKFLOW_ASSIGNMENT WA
                WHERE WA.DOCINSTAMP=D.DOCINSTAMP AND WA.VIEW_CODE='management' AND WA.VALIDADO=1
            ) OR (
                NOT EXISTS (SELECT 1 FROM dbo.DOC_AI_WORKFLOW_ASSIGNMENT WX WHERE WX.DOCINSTAMP=D.DOCINSTAMP)
                AND ISNULL(D.MANAGEMENT_VALIDATED, 0) = 1
            )
        """,
        'accounting': """
            EXISTS (
                SELECT 1 FROM dbo.DOC_AI_WORKFLOW_ASSIGNMENT WA
                WHERE WA.DOCINSTAMP=D.DOCINSTAMP AND WA.VIEW_CODE='accounting' AND WA.VALIDADO=1
            ) OR (
                NOT EXISTS (SELECT 1 FROM dbo.DOC_AI_WORKFLOW_ASSIGNMENT WX WHERE WX.DOCINSTAMP=D.DOCINSTAMP)
                AND ISNULL(D.ACCOUNTING_VALIDATED, 0) = 1
            )
        """,
    }
    examined = corrected = unchanged = 0
    per_view: dict[str, dict[str, int]] = {}
    candidates: list[tuple[str, str]] = []
    for view, evidence in evidence_sql.items():
        rows = db.session.execute(text(f"""
            SELECT D.DOCINSTAMP,
                   ISNULL((
                       SELECT TOP (1) E.EVENT_CODE
                       FROM dbo.DOC_AI_VIEW_EVENT E
                       WHERE E.DOCINSTAMP=D.DOCINSTAMP AND E.VIEW_CODE=:view_code
                       ORDER BY E.DTCRI DESC, E.DOCVIEWEVENTSTAMP DESC
                   ), '') AS LATEST_EVENT
            FROM dbo.DOC_INBOX D
            WHERE ({evidence})
        """), {'view_code': view}).mappings().all()
        view_corrected = sum(1 for row in rows if not str(row.get('LATEST_EVENT') or '').strip())
        view_unchanged = len(rows) - view_corrected
        examined += len(rows)
        corrected += view_corrected
        unchanged += view_unchanged
        per_view[view] = {
            'examined': len(rows),
            'corrected': view_corrected,
            'unchanged': view_unchanged,
        }
        candidates.extend(
            (str(row.get('DOCINSTAMP') or '').strip(), view)
            for row in rows if not str(row.get('LATEST_EVENT') or '').strip()
        )

    ambiguous = 0
    try:
        ambiguous = int(db.session.execute(text("""
            SELECT COUNT_BIG(1)
            FROM dbo.DOC_DUPLICATE_INDEX DI
            INNER JOIN dbo.DOC_INBOX D ON D.DOCINSTAMP=DI.DOCINSTAMP
            WHERE ISNULL(DI.ARQUIVADO, 0)=1
              AND ISNULL(D.ACCOUNTING_VALIDATED, 0)=0
              AND NOT EXISTS (
                  SELECT 1 FROM dbo.DOC_AI_WORKFLOW_ASSIGNMENT WA
                  WHERE WA.DOCINSTAMP=D.DOCINSTAMP AND WA.VIEW_CODE='accounting' AND WA.VALIDADO=1
              )
        """)).scalar() or 0)
    except Exception:
        current_app.logger.exception('Não foi possível contar arquivos Document AI ambíguos')

    if not dry_run:
        for document_stamp, view in candidates:
            db.session.execute(text("""
                INSERT INTO dbo.DOC_AI_VIEW_EVENT (
                    DOCVIEWEVENTSTAMP, DOCINSTAMP, VIEW_CODE, EVENT_CODE,
                    PREVIOUS_STATE, USUARIO, DTCRI
                ) VALUES (
                    :event_stamp, :document_stamp, :view_code, 'validated',
                    '', :requested_by, GETDATE()
                )
            """), {
                'event_stamp': _new_stamp(),
                'document_stamp': document_stamp,
                'view_code': view,
                'requested_by': str(requested_by or '').strip()[:50],
            })
        db.session.commit()
    return {
        'dry_run': bool(dry_run),
        'examined': examined,
        'corrected': corrected,
        'unchanged': unchanged,
        'ambiguous_unchanged': ambiguous,
        'per_view': per_view,
    }


def delete_document_from_inbox(document_stamp: str, view: str, deleted_by: str = '') -> dict[str, Any]:
    """Archive a document only in the requested view; never destroy business data."""
    normalized_view = _normalize_document_inbox_view(view)
    previous_state = ''
    for item in list_documents({'view': normalized_view}).get('items', []):
        if str(item.get('id') or '') == str(document_stamp or '').strip():
            previous_state = str(item.get('business_state') or '').strip()
            break
    return _append_document_view_event(
        document_stamp,
        normalized_view,
        'deleted',
        deleted_by,
        previous_state,
    )


def recover_document_to_inbox(document_stamp: str, view: str, recovered_by: str = '') -> dict[str, Any]:
    """Recover a logically deleted document in one view without rerunning processing."""
    normalized_view = _normalize_document_inbox_view(view)
    if not document_belongs_to_inbox_view(document_stamp, normalized_view, archived=True):
        raise ValueError('Documento eliminado não encontrado neste arquivo.')
    latest_event = db.session.execute(text("""
        SELECT TOP (1) EVENT_CODE, PREVIOUS_STATE
        FROM dbo.DOC_AI_VIEW_EVENT
        WHERE DOCINSTAMP=:document_stamp AND VIEW_CODE=:view_code
        ORDER BY DTCRI DESC, DOCVIEWEVENTSTAMP DESC
    """), {
        'document_stamp': str(document_stamp or '').strip(),
        'view_code': normalized_view,
    }).mappings().first()
    if str((latest_event or {}).get('EVENT_CODE') or '') != 'deleted':
        raise ValueError('Este documento não está eliminado nesta vista.')
    return _append_document_view_event(
        document_stamp,
        normalized_view,
        'recovered',
        recovered_by,
        str((latest_event or {}).get('PREVIOUS_STATE') or ''),
    )


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
    preserved_processing_meta = _json_loads(document.processing_meta_json, {})

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
            failure_meta = dict(preserved_processing_meta)
            failure_meta.update({
                'extraction': {
                    'method': document.extraction_method,
                    'quality_score': float(document.extraction_quality_score or 0),
                    'notes': _json_loads(document.extraction_notes_json, {}),
                    'preprocessed_image_path': document.preprocessed_image_path or '',
                    'fallback_used': bool(extraction.get('fallback_used')),
                },
                'ocr_available': ocr_engine_available(),
            })
            document.processing_meta_json = _json_dumps(failure_meta)
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
        completed_meta = dict(preserved_processing_meta)
        completed_meta.update({
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
        document.processing_meta_json = _json_dumps(completed_meta)
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

        _refresh_document_duplicate_state(document, result_payload)
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


def ensure_llm_inbox_document(
    file_name: str,
    file_bytes: bytes,
    created_by: str,
    document_stamp: str = '',
) -> dict[str, Any]:
    from werkzeug.datastructures import FileStorage

    _ensure_document_ai_schema()
    requested_stamp = str(document_stamp or '').strip()
    if requested_stamp:
        requested = db.session.get(DocInbox, requested_stamp)
        if not requested:
            raise ValueError('Documento do inbox não encontrado.')
        return {'id': requested.docinstamp, 'created': False, 'duplicate': False}

    content_hash = hashlib.sha256(file_bytes or b'').hexdigest()
    existing = DocInbox.query.filter_by(file_hash=content_hash).order_by(DocInbox.dtcri.desc()).first()
    if existing:
        _document_log(existing.docinstamp, 'duplicate_rejected', 'warning', 'Leitura repetida recusada pelo hash do ficheiro.', {
            'source_table': 'DOC_AI_LLM',
            'requested_by': created_by or '',
            'file_name': str(file_name or ''),
            'score': 100,
            'matching_fields': ['file_hash'],
        })
        db.session.commit()
        return {'id': existing.docinstamp, 'created': False, 'duplicate': True}

    uploaded = FileStorage(
        stream=io.BytesIO(file_bytes or b''),
        filename=str(file_name or 'documento.pdf'),
        content_type='application/pdf',
    )
    stored = _store_file(uploaded)
    detail = _create_inbox_document_from_stored_file(
        stored,
        created_by,
        source_table='DOC_AI_LLM',
        process_after_create=False,
    )
    return {'id': str(detail.get('id') or ''), 'created': True, 'duplicate': False}


def find_llm_inbox_document(file_bytes: bytes) -> str:
    """Return an existing inbox stamp for this PDF without creating a record."""
    _ensure_document_ai_schema()
    content_hash = hashlib.sha256(file_bytes or b'').hexdigest()
    existing = DocInbox.query.filter_by(file_hash=content_hash).order_by(DocInbox.dtcri.desc()).first()
    return str(existing.docinstamp or '') if existing else ''


def _safe_split_file_part(value: Any, fallback: str, max_length: int = 100) -> str:
    normalized = unicodedata.normalize('NFKD', str(value or '').strip())
    ascii_value = normalized.encode('ascii', 'ignore').decode('ascii')
    safe_value = re.sub(r'[^A-Za-z0-9]+', '_', ascii_value).strip('_')
    return (safe_value or fallback)[:max(8, int(max_length or 100))].rstrip('_')


def _anexos_display_filename(value: Any, max_length: int = 100) -> str:
    file_name = os.path.basename(str(value or '').replace('\\', '/')).strip()
    if not file_name:
        return ''
    max_length = max(16, int(max_length or 100))
    if len(file_name) <= max_length:
        return file_name
    stem, extension = os.path.splitext(file_name)
    digest = hashlib.sha1(file_name.encode('utf-8', errors='ignore')).hexdigest()[:8]
    extension = extension[:20]
    stem_limit = max_length - len(extension) - len(digest) - 1
    if stem_limit < 8:
        return file_name[:max_length]
    return f'{stem[:stem_limit].rstrip()}-{digest}{extension}'


def _split_document_prefix(document_type: str) -> str:
    normalized = _normalize_text(document_type).replace(' ', '_')
    if normalized in ('delivery_note', 'guia', 'bon_de_livraison') or 'delivery' in normalized:
        return 'BL'
    if normalized in ('invoice', 'proforma_invoice', 'fatura', 'facture') or 'invoice' in normalized:
        return 'FAC'
    return 'DOC'


def _split_pdf_parts(file_bytes: bytes, document_batch: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not file_bytes:
        raise ValueError('O PDF está vazio.')
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(io.BytesIO(file_bytes))
    if reader.is_encrypted:
        try:
            reader.decrypt('')
        except Exception as exc:
            raise ValueError('Não é possível separar um PDF protegido por palavra-passe.') from exc
    page_count = len(reader.pages)
    if page_count < 2:
        raise ValueError('O PDF tem apenas uma página.')

    raw_documents = list((document_batch or {}).get('documents') or [])
    boundaries = []
    seen_starts = set()
    for raw_item in raw_documents:
        if not isinstance(raw_item, dict):
            continue
        start_page = _safe_int(raw_item.get('start_page'), 0)
        if start_page < 1 or start_page > page_count or start_page in seen_starts:
            continue
        seen_starts.add(start_page)
        boundaries.append({**raw_item, 'start_page': start_page})
    boundaries.sort(key=lambda item: item['start_page'])
    if len(boundaries) < 2 or boundaries[0]['start_page'] != 1:
        raise ValueError('As fronteiras devolvidas pelo LLM não permitem separar o PDF com segurança.')

    parts = []
    for index, boundary in enumerate(boundaries):
        start_page = boundary['start_page']
        end_page = boundaries[index + 1]['start_page'] - 1 if index + 1 < len(boundaries) else page_count
        if end_page < start_page:
            raise ValueError('Foi encontrado um intervalo de páginas inválido.')
        writer = PdfWriter()
        for page_index in range(start_page - 1, end_page):
            writer.add_page(reader.pages[page_index])
        output = io.BytesIO()
        writer.write(output)
        part_bytes = output.getvalue()
        if not part_bytes:
            raise ValueError(f'Não foi possível criar o documento iniciado na página {start_page}.')
        parts.append({
            **boundary,
            'start_page': start_page,
            'end_page': end_page,
            'pdf_bytes': part_bytes,
        })
    return parts


def _store_split_pdf_bytes(pdf_bytes: bytes, original_name: str) -> dict[str, Any]:
    stamp = _new_stamp()
    safe_name = f'{stamp}.pdf'
    relative_dir = os.path.join('static', 'images', 'document_ai')
    absolute_dir = os.path.join(_document_storage_root(), relative_dir)
    os.makedirs(absolute_dir, exist_ok=True)
    absolute_path = os.path.join(absolute_dir, safe_name)
    with open(absolute_path, 'wb') as handle:
        handle.write(pdf_bytes)
    return {
        'original_name': original_name,
        'file_name': safe_name,
        'absolute_path': absolute_path,
        'public_path': f'/{relative_dir.replace(os.sep, "/")}/{safe_name}',
        'file_ext': '.pdf',
        'mime_type': 'application/pdf',
        'size': os.path.getsize(absolute_path),
    }


def _split_supplier_payload(boundary: dict[str, Any], document_data: dict[str, Any]) -> dict[str, Any]:
    customer = dict(document_data.get('customer') or {})
    root_supplier = dict(document_data.get('supplier') or {})
    feid = _safe_int(customer.get('feid'), 0)
    supplier_name = str(boundary.get('supplier_name') or root_supplier.get('name') or '').strip()
    supplier_tax_id = _digits_only(boundary.get('supplier_tax_id') or root_supplier.get('tax_id'))
    boundary_name = str(boundary.get('supplier_name') or '').strip()
    boundary_tax_id = _digits_only(boundary.get('supplier_tax_id'))
    same_as_root = bool(
        (not boundary_name and not boundary_tax_id)
        or (boundary_tax_id and boundary_tax_id == _digits_only(root_supplier.get('tax_id')))
        or (boundary_name and _normalize_text(boundary_name) == _normalize_text(root_supplier.get('name')))
    )
    selected = {}
    if feid:
        try:
            candidates = []
            if supplier_tax_id:
                candidates.extend(search_suppliers(supplier_tax_id, feid=feid, limit=5))
            if supplier_name:
                known = {(item.get('feid'), item.get('no')) for item in candidates}
                candidates.extend(
                    item for item in search_suppliers(supplier_name, feid=feid, limit=5)
                    if (item.get('feid'), item.get('no')) not in known
                )
            candidates.sort(key=lambda item: -float(item.get('score') or 0))
            if candidates and float(candidates[0].get('score') or 0) >= 0.72:
                selected = candidates[0]
        except Exception:
            current_app.logger.exception('Erro ao identificar fornecedor de documento separado')
    return {
        'feid': feid or None,
        'supplier_no': selected.get('no') or (root_supplier.get('supplier_no') if same_as_root else None) or None,
        'name': str(selected.get('name') or supplier_name).strip(),
        'tax_id': str(selected.get('tax_id') or supplier_tax_id).strip(),
    }


def _document_group_payload(batch_stamp: str, current_document_id: str = '') -> dict[str, Any]:
    documents = DocInbox.query.filter_by(
        source_table='DOC_AI_BATCH',
        source_recstamp=str(batch_stamp or '').strip(),
    ).all()
    items = []
    for document in documents:
        meta = _json_loads(document.processing_meta_json, {})
        batch = dict(meta.get('batch') or {})
        items.append({
            'id': document.docinstamp,
            'file_name': document.file_name or '',
            'index': _safe_int(batch.get('index'), 0),
            'count': _safe_int(batch.get('count'), len(documents)),
            'start_page': _safe_int(batch.get('start_page'), 0),
            'end_page': _safe_int(batch.get('end_page'), 0),
            'document_type': document.doc_type_detected or 'unknown',
            'document_number': str((document.json_resultado and _json_loads(document.json_resultado, {}).get('document_number')) or ''),
        })
    items.sort(key=lambda item: (item.get('index') or 999999, item.get('file_name') or ''))
    current_index = next((index for index, item in enumerate(items) if item.get('id') == current_document_id), 0)
    return {
        'grouped': len(items) > 0,
        'batch_id': str(batch_stamp or '').strip(),
        'count': len(items),
        'current_index': current_index,
        'documents': items,
    }


def get_document_group(document_stamp: str) -> dict[str, Any]:
    _ensure_document_ai_schema()
    document = db.session.get(DocInbox, str(document_stamp or '').strip())
    if not document:
        raise ValueError('Documento não encontrado.')
    if document.source_table != 'DOC_AI_BATCH' or not document.source_recstamp:
        return {'grouped': False, 'batch_id': '', 'count': 0, 'current_index': 0, 'documents': []}
    return _document_group_payload(document.source_recstamp, document.docinstamp)


def split_extracted_pdf_into_inbox(
    file_bytes: bytes,
    file_name: str,
    document_batch: dict[str, Any] | None,
    document_data: dict[str, Any] | None,
    created_by: str,
    source_document_id: str = '',
) -> dict[str, Any]:
    _ensure_document_ai_schema()
    parts = _split_pdf_parts(file_bytes, document_batch)
    batch_stamp = _new_stamp()
    total = len(parts)
    root_data = dict(document_data or {})
    customer = dict(root_data.get('customer') or {})
    source_document = db.session.get(DocInbox, str(source_document_id or '').strip()) if source_document_id else None
    created_paths = []
    created_documents = []
    skipped_duplicates = []
    now = _now()
    try:
        for index, part in enumerate(parts, start=1):
            document_type = str(part.get('document_type') or 'unknown').strip() or 'unknown'
            document_number = str(part.get('document_number') or '').strip()
            supplier = _split_supplier_payload(part, root_data)
            prefix = _split_document_prefix(document_type)
            supplier_part = _safe_split_file_part(supplier.get('name'), 'FORNECEDOR', 110)
            number_part = _safe_split_file_part(document_number, f'SEM_NUMERO_{index}', 70)
            output_name = f'{prefix}_{supplier_part}_{number_part}.pdf'[:260]
            content_hash = hashlib.sha256(part.get('pdf_bytes') or b'').hexdigest()
            acquire_duplicate_lock(db.session, content_hash)
            duplicate = find_exact_file_duplicate(db.session, content_hash)
            if duplicate:
                skipped_duplicates.append({
                    'part': index,
                    'file_name': output_name,
                    **duplicate,
                })
                continue
            stored = _store_split_pdf_bytes(part.get('pdf_bytes') or b'', output_name)
            created_paths.append(stored['absolute_path'])

            result = canonical_result_base(document_type)
            result['document_number'] = document_number
            result['supplier'] = {
                'supplier_no': supplier.get('supplier_no'),
                'tax_id': supplier.get('tax_id') or '',
                'name': supplier.get('name') or '',
            }
            result['customer'] = {
                'tax_id': str(customer.get('tax_id') or ''),
                'name': str(customer.get('name') or ''),
                'feid': supplier.get('feid') or customer.get('feid'),
            }
            batch_meta = {
                'id': batch_stamp,
                'index': index,
                'count': total,
                'source_document_id': str(source_document_id or '').strip(),
                'source_file_name': str(file_name or '').strip(),
                'start_page': part.get('start_page'),
                'end_page': part.get('end_page'),
            }
            unique_hash = hashlib.sha256(f'{batch_stamp}:{index}:{content_hash}'.encode('utf-8')).hexdigest()
            document = DocInbox(
                docinstamp=_new_stamp(),
                feid=supplier.get('feid') or customer.get('feid') or None,
                source_table='DOC_AI_BATCH',
                source_recstamp=batch_stamp,
                file_name=output_name,
                file_path=stored['public_path'],
                file_ext='.pdf',
                mime_type='application/pdf',
                file_hash=unique_hash,
                file_size=stored['size'],
                extracted_text='',
                extraction_method='split_pdf',
                extraction_quality_score=1,
                extraction_notes_json='{}',
                preprocessed_image_path=None,
                ocr_raw_json='{}',
                text_blocks_json='[]',
                processing_stage='split_ready',
                last_processing_error='',
                doc_type_detected=document_type,
                fornecedor_no=supplier.get('supplier_no'),
                fornecedor_nif_detetado=supplier.get('tax_id') or '',
                fornecedor_nome_detetado=supplier.get('name') or '',
                confidence_score=max(0, min(1, float(part.get('confidence') or 0))),
                processing_status='new',
                json_resultado=_json_dumps(result),
                warnings_json='[]',
                errors_json='[]',
                processing_meta_json=_json_dumps({
                    'batch': batch_meta,
                    'content_hash': content_hash,
                    'llm_boundary': {key: value for key, value in part.items() if key != 'pdf_bytes'},
                }),
                dtcri=now,
                dtalt=now,
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
                    (:stamp, 'DOC_INBOX', :recstamp, :descricao, :file_name, :caminho, 'pdf', :data, :utilizador)
            """), {
                'stamp': anexo_stamp,
                'recstamp': document.docinstamp,
                'descricao': f'Documento separado {index}/{total}',
                'file_name': _anexos_display_filename(output_name),
                'caminho': stored['public_path'],
                'data': date.today(),
                'utilizador': created_by or '',
            })
            document.anexosstamp = anexo_stamp
            created_documents.append(document)

        if source_document:
            source_meta = _json_loads(source_document.processing_meta_json, {})
            source_meta['split_output'] = {
                'batch_id': batch_stamp,
                'count': len(created_documents),
                'duplicates_skipped': len(skipped_duplicates),
                'created_at': now.isoformat(),
                'created_by': created_by or '',
            }
            source_document.processing_meta_json = _json_dumps(source_meta)
            source_document.dtalt = now
            source_document.useralteracao = created_by or source_document.useralteracao or ''
        db.session.commit()
    except Exception:
        db.session.rollback()
        for path in created_paths:
            try:
                if os.path.isfile(path):
                    os.remove(path)
            except Exception:
                current_app.logger.warning('Não foi possível remover PDF parcial após rollback: %s', path, exc_info=True)
        raise

    group = _document_group_payload(batch_stamp, created_documents[0].docinstamp if created_documents else '')
    return {
        'ok': True,
        'message': (
            f'{len(created_documents)} documentos separados e adicionados ao inbox.'
            + (f' {len(skipped_duplicates)} duplicado(s) ignorado(s).' if skipped_duplicates else '')
        ),
        'group': group,
        'duplicates': skipped_duplicates,
    }


def _create_inbox_document_from_stored_file(
    stored: dict[str, Any],
    created_by: str,
    source_table: str = '',
    source_recstamp: str = '',
    process_after_create: bool = True,
) -> dict[str, Any]:
    acquire_duplicate_lock(db.session, stored.get('hash'))
    duplicate = find_exact_file_duplicate(db.session, stored.get('hash'))
    if duplicate:
        try:
            if stored.get('absolute_path') and os.path.isfile(stored['absolute_path']):
                os.remove(stored['absolute_path'])
        except OSError:
            current_app.logger.warning('Não foi possível remover upload documental duplicado.', exc_info=True)
        if duplicate.get('source_area') == 'document_ai':
            _document_log(
                str(duplicate.get('record_id') or ''),
                'duplicate_rejected',
                'warning',
                'Importação repetida recusada pelo hash do ficheiro.',
                {
                    'source_table': str(source_table or '').strip(),
                    'source_recstamp': str(source_recstamp or '').strip(),
                    'requested_by': created_by or '',
                    'file_name': stored.get('original_name') or '',
                    'score': 100,
                    'matching_fields': ['file_hash'],
                },
            )
            db.session.commit()
            detail = get_document_detail(str(duplicate.get('record_id') or ''))
            detail.update({
                'created': False,
                'duplicate': True,
                'duplicate_detection': duplicate,
            })
            return detail
        raise ValueError(
            f"Este ficheiro já existe em Despesas ({duplicate.get('file_name') or duplicate.get('record_id')})."
        )

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
        'file_name': _anexos_display_filename(stored['original_name']),
        'caminho': stored['public_path'],
        'tipo': stored['file_ext'].lstrip('.'),
        'data': date.today(),
        'utilizador': created_by or '',
    })
    document.anexosstamp = anexo_stamp
    db.session.commit()
    if not process_after_create:
        return get_document_detail(document.docinstamp)
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

    supplier_payload = dict(result.get('supplier') or {})
    if bool(result.get('supplier_explicitly_absent') or supplier_payload.get('explicitly_absent')):
        document.fornecedor_no = None
    elif supplier_no not in (None, ''):
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
    document.invoice_type = _normalize_invoice_type(result.get('invoice_type') or document.invoice_type)
    if document.invoice_type == 'unknown':
        document.invoice_type = _infer_invoice_type(result, document.extracted_text)
    document.doctemplatestamp = template_id or None
    document.json_resultado = _json_dumps(result or canonical_result_base(doc_type))
    document.warnings_json = _json_dumps(warnings)
    document.errors_json = _json_dumps(errors)
    document.processing_status = processing_status
    document.confidence_score = float(payload.get('confidence') or document.confidence_score or 0)
    document.dtalt = _now()
    document.dtproc = _now()
    document.useralteracao = requested_by or document.useralteracao

    if processing_status == 'parsed_ok':
        customer = dict(result.get('customer') or {})
        supplier = dict(result.get('supplier') or {})
        required_values = [
            _safe_int(customer.get('feid') or document.feid, 0),
            _safe_int(supplier.get('supplier_no') or supplier.get('no') or document.fornecedor_no, 0),
            str(result.get('document_number') or '').strip(),
            str(result.get('document_date') or '').strip(),
            doc_type if doc_type != 'unknown' else '',
        ]
        if doc_type in {'invoice', 'provisional_invoice'}:
            required_values.append(document.invoice_type if document.invoice_type != 'unknown' else '')
        if not all(required_values):
            raise ValueError('Completa os dados obrigatórios antes de validar na Receção.')
        document.reception_validated = True
        document.reception_validated_at = document.dtalt
        document.reception_validated_by = requested_by or ''

    _document_log(document.docinstamp, 'review', 'ok', 'Validação humana gravada.', {
        'status': processing_status,
        'template_id': template_id,
        'supplier_no': document.fornecedor_no,
        'feid': document.feid,
    })
    _refresh_document_duplicate_state(document, result)
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
    value = normalize_document_type(doc_type)
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
