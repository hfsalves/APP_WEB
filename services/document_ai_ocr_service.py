import base64
import importlib.util
import io
import json
import os
import shutil
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

from flask import current_app
from sqlalchemy import text

from models import db


def _para_value(code: str, default: str = '') -> str:
    key = str(code or '').strip()
    if not key:
        return default
    try:
        para_map = current_app.config.get('PARA_VALUES') or {}
        value = para_map.get(key)
        if value in (None, ''):
            value = para_map.get(key.upper())
        if value not in (None, ''):
            return str(value).strip()
    except Exception:
        para_map = {}
    try:
        row = db.session.execute(
            text("""
                SELECT TOP 1 PARAMETRO, TIPO, CVALOR, DVALOR, NVALOR, LVALOR
                FROM dbo.PARA
                WHERE UPPER(LTRIM(RTRIM(PARAMETRO))) = UPPER(LTRIM(RTRIM(:code)))
            """),
            {'code': key},
        ).mappings().first()
        if not row:
            return default
        tipo = str(row.get('TIPO') or '').strip().upper()
        if tipo == 'N':
            return str(row.get('NVALOR') or '')
        if tipo == 'D':
            return str(row.get('DVALOR') or '')
        if tipo == 'L':
            return '1' if bool(row.get('LVALOR') or 0) else '0'
        return str(row.get('CVALOR') or '').strip() or default
    except Exception:
        return default


def _document_ai_api_key() -> str:
    return (
        _para_value('DOC_AI_OPENAI_API_KEY')
        or _para_value('SHOP_TRANSLATE_OPENAI_API_KEY')
        or _para_value('OPENAI_API_KEY')
        or os.getenv('DOC_AI_OPENAI_API_KEY')
        or os.getenv('SHOP_TRANSLATE_OPENAI_API_KEY')
        or os.getenv('OPENAI_API_KEY')
        or ''
    ).strip()


def _document_ai_ocr_model() -> str:
    return (
        _para_value('DOC_AI_OPENAI_OCR_MODEL')
        or _para_value('DOC_AI_OPENAI_MODEL')
        or _para_value('SHOP_TRANSLATE_MODEL')
        or _para_value('OPENAI_MODEL')
        or os.getenv('DOC_AI_OPENAI_OCR_MODEL')
        or os.getenv('DOC_AI_OPENAI_MODEL')
        or os.getenv('SHOP_TRANSLATE_MODEL')
        or os.getenv('OPENAI_MODEL')
        or 'gpt-4.1-mini'
    ).strip()


def _extract_openai_text(payload: dict[str, Any]) -> str:
    direct = str(payload.get('output_text') or '').strip()
    if direct:
        return direct
    for output in payload.get('output') or []:
        for content in output.get('content') or []:
            if content.get('type') == 'output_text':
                text_value = str(content.get('text') or '').strip()
                if text_value:
                    return text_value
    return ''


def _strip_json_fence(raw_text: str) -> str:
    text_value = str(raw_text or '').strip()
    if not text_value.startswith('```'):
        return text_value
    lines = text_value.splitlines()
    if lines and lines[0].startswith('```'):
        lines = lines[1:]
    if lines and lines[-1].strip() == '```':
        lines = lines[:-1]
    return '\n'.join(lines).strip()


def _pytesseract_python_available() -> bool:
    return bool(
        importlib.util.find_spec('pytesseract')
        and importlib.util.find_spec('PIL')
    )


def _openai_ocr_available() -> bool:
    return bool(_document_ai_api_key())


def _resolve_tesseract_cmd() -> str:
    candidates = []
    env_cmd = (
        _para_value('DOC_AI_TESSERACT_CMD')
        or _para_value('TESSERACT_CMD')
        or os.getenv('DOC_AI_TESSERACT_CMD')
        or os.getenv('TESSERACT_CMD')
        or os.getenv('TESSERACT_PATH')
        or ''
    ).strip()
    if env_cmd:
        candidates.append(env_cmd)
    root_path = getattr(current_app, 'root_path', '') or ''
    if root_path:
        candidates.extend([
            os.path.join(root_path, '.tools', 'tesseract', 'tesseract.exe'),
            os.path.join(root_path, 'tools', 'tesseract', 'tesseract.exe'),
        ])
    candidates.extend([
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    ])
    on_path = shutil.which('tesseract')
    if on_path:
        candidates.append(on_path)
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate
    return ''


def _resolve_tessdata_prefix(tesseract_cmd: str) -> str:
    candidates = []
    env_prefix = (
        _para_value('DOC_AI_TESSDATA_PREFIX')
        or _para_value('TESSDATA_PREFIX')
        or os.getenv('DOC_AI_TESSDATA_PREFIX')
        or os.getenv('TESSDATA_PREFIX')
        or ''
    ).strip()
    if env_prefix:
        candidates.append(env_prefix)
    if tesseract_cmd:
        base_dir = os.path.dirname(tesseract_cmd)
        candidates.append(os.path.join(base_dir, 'tessdata'))
    for candidate in candidates:
        if candidate and os.path.isdir(candidate):
            return candidate
    return ''


def _local_ocr_available() -> bool:
    return _pytesseract_python_available() and bool(_resolve_tesseract_cmd())


def ocr_engine_available() -> bool:
    return _local_ocr_available() or _openai_ocr_available()


def _make_empty_payload(message: str, engine: str | None = None) -> dict[str, Any]:
    return {
        'ok': False,
        'engine': engine,
        'text': '',
        'blocks': [],
        'raw_json': {},
        'warnings': [message],
    }


def _line_blocks_from_lines(lines: list[str], page_number: int, page_label: str, image_width: int = 0, image_height: int = 0) -> list[dict[str, Any]]:
    blocks = []
    for idx, line in enumerate(lines, start=1):
        text_value = str(line or '').strip()
        if not text_value:
            continue
        blocks.append({
            'id': f'ocr-{page_number}-{idx}',
            'page': page_number,
            'line_no': idx,
            'text': text_value,
            'left': 0,
            'top': 0,
            'width': 0,
            'height': 0,
            'page_width': int(image_width or 0),
            'page_height': int(image_height or 0),
            'page_label': page_label,
        })
    return blocks


def _ocr_image_with_pytesseract(image, page_number: int = 1, page_label: str = '') -> dict[str, Any]:
    if not _pytesseract_python_available():
        return _make_empty_payload('Dependências Python do OCR não estão instaladas.', None)

    try:
        import pytesseract
    except Exception as exc:
        return _make_empty_payload(f'Não foi possível inicializar OCR: {exc}', None)

    tesseract_cmd = _resolve_tesseract_cmd()
    if not tesseract_cmd:
        return _make_empty_payload('Binário Tesseract não encontrado no servidor.', 'pytesseract')
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    tessdata_prefix = _resolve_tessdata_prefix(tesseract_cmd)
    if tessdata_prefix:
        os.environ['TESSDATA_PREFIX'] = tessdata_prefix

    try:
        image_width, image_height = image.size
        config = '--oem 3 --psm 6'
        raw = pytesseract.image_to_data(
            image,
            lang='eng+por',
            config=config,
            output_type=pytesseract.Output.DICT,
        )
        blocks = []
        lines = []
        total = len(raw.get('text', []) or [])
        for idx in range(total):
            chunk = str((raw.get('text') or [''])[idx] or '').strip()
            if not chunk:
                continue
            line_no = int(((raw.get('line_num') or [0])[idx] or 0))
            block = {
                'id': f'ocr-{page_number}-{idx + 1}',
                'page': page_number,
                'line_no': line_no or idx + 1,
                'text': chunk,
                'left': int(((raw.get('left') or [0])[idx] or 0)),
                'top': int(((raw.get('top') or [0])[idx] or 0)),
                'width': int(((raw.get('width') or [0])[idx] or 0)),
                'height': int(((raw.get('height') or [0])[idx] or 0)),
                'page_width': int(image_width or 0),
                'page_height': int(image_height or 0),
            }
            blocks.append(block)
            lines.append(chunk)
        text_value = '\n'.join(lines).strip()
        return {
            'ok': bool(text_value),
            'engine': 'pytesseract',
            'text': text_value,
            'blocks': blocks,
            'raw_json': {'page_label': page_label, 'ocr': raw, 'config': config, 'lang': 'eng+por'},
            'warnings': [] if text_value else ['OCR local não devolveu texto utilizável.'],
        }
    except Exception as exc:
        return _make_empty_payload(f'Falha no OCR local: {exc}', 'pytesseract')


def _openai_ocr_schema() -> dict[str, Any]:
    return {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'text': {'type': 'string'},
            'lines': {'type': 'array', 'items': {'type': 'string'}},
        },
        'required': ['text', 'lines'],
    }


def _ocr_image_with_openai(image, page_number: int = 1, page_label: str = '') -> dict[str, Any]:
    api_key = _document_ai_api_key()
    if not api_key:
        return _make_empty_payload('OpenAI OCR indisponível: API key não configurada.', 'openai')

    try:
        buffer = io.BytesIO()
        image.convert('RGB').save(buffer, format='PNG')
        encoded = base64.b64encode(buffer.getvalue()).decode('ascii')
        image_url = f'data:image/png;base64,{encoded}'
        body = {
            'model': _document_ai_ocr_model(),
            'input': [
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'input_text',
                            'text': (
                                'Transcribe the document image exactly as visible. '
                                'Return only JSON following the schema, preserving line breaks and reading order. '
                                'Do not summarize.'
                            ),
                        },
                        {
                            'type': 'input_image',
                            'image_url': image_url,
                            'detail': 'high',
                        },
                    ],
                }
            ],
            'text': {
                'format': {
                    'type': 'json_schema',
                    'name': 'document_ai_ocr',
                    'schema': _openai_ocr_schema(),
                }
            },
        }
        req = urllib_request.Request(
            'https://api.openai.com/v1/responses',
            data=json.dumps(body).encode('utf-8'),
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        with urllib_request.urlopen(req, timeout=60) as response:
            payload_response = json.loads(response.read().decode('utf-8'))
        raw_text = _strip_json_fence(_extract_openai_text(payload_response))
        parsed = json.loads(raw_text or '{}')
        text_value = str(parsed.get('text') or '').strip()
        lines = [str(item or '').strip() for item in (parsed.get('lines') or []) if str(item or '').strip()]
        if not lines and text_value:
            lines = [line.strip() for line in text_value.splitlines() if line.strip()]
        image_width, image_height = image.size
        blocks = _line_blocks_from_lines(lines, page_number, page_label, image_width, image_height)
        return {
            'ok': bool(text_value or lines),
            'engine': 'openai_responses',
            'text': text_value or '\n'.join(lines).strip(),
            'blocks': blocks,
            'raw_json': {
                'page_label': page_label,
                'provider': 'openai_responses',
                'model': _document_ai_ocr_model(),
                'response': payload_response,
            },
            'warnings': [] if (text_value or lines) else ['OpenAI OCR não devolveu texto utilizável.'],
        }
    except urllib_error.HTTPError as exc:
        details = ''
        try:
            details = exc.read().decode('utf-8')
        except Exception:
            details = str(exc)
        return _make_empty_payload(f'Falha no OCR OpenAI: {details[:280]}', 'openai_responses')
    except Exception as exc:
        return _make_empty_payload(f'Falha no OCR OpenAI: {exc}', 'openai_responses')


def _best_ocr_payload(*payloads: dict[str, Any]) -> dict[str, Any]:
    usable = []
    for payload in payloads:
        if not payload:
            continue
        text_value = str(payload.get('text') or '').strip()
        if text_value:
            usable.append((len(text_value), payload))
    if usable:
        usable.sort(key=lambda item: item[0], reverse=True)
        return usable[0][1]
    for payload in payloads:
        if payload:
            return payload
    return _make_empty_payload('Nenhum motor OCR disponível.', None)


def extract_image_text(image_path: str) -> dict[str, Any]:
    if not ocr_engine_available():
        return _make_empty_payload('Motor OCR não disponível no servidor.', None)

    try:
        from PIL import Image
    except Exception as exc:
        return _make_empty_payload(f'Não foi possível inicializar OCR: {exc}', None)

    try:
        image = Image.open(image_path)
        return extract_image_text_from_object(image, page_number=1, page_label=image_path)
    except Exception as exc:
        return _make_empty_payload(f'Falha no OCR: {exc}', None)


def extract_image_text_from_object(image, page_number: int = 1, page_label: str = '') -> dict[str, Any]:
    local_payload = _ocr_image_with_pytesseract(image, page_number=page_number, page_label=page_label)
    if local_payload.get('ok'):
        return local_payload
    openai_payload = _ocr_image_with_openai(image, page_number=page_number, page_label=page_label)
    if openai_payload.get('ok'):
        warnings = list(local_payload.get('warnings') or [])
        if warnings:
            openai_payload['warnings'] = warnings + list(openai_payload.get('warnings') or [])
        return openai_payload
    best = _best_ocr_payload(local_payload, openai_payload)
    warnings = []
    warnings.extend(local_payload.get('warnings') or [])
    warnings.extend(openai_payload.get('warnings') or [])
    best['warnings'] = list(dict.fromkeys(warnings))
    return best
