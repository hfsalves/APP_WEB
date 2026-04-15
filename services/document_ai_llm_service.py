import json
import os
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
        pass
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


def _document_ai_model() -> str:
    return (
        _para_value('DOC_AI_OPENAI_MODEL')
        or _para_value('SHOP_TRANSLATE_MODEL')
        or _para_value('OPENAI_MODEL')
        or os.getenv('DOC_AI_OPENAI_MODEL')
        or os.getenv('SHOP_TRANSLATE_MODEL')
        or os.getenv('OPENAI_MODEL')
        or 'gpt-4o-mini'
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


def _field_suggestion_schema() -> dict[str, Any]:
    return {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'name': {'type': 'string'},
            'fingerprint': {'type': 'string'},
            'doc_type': {'type': 'string'},
            'score_min_match': {'type': 'number'},
            'match_rules': {
                'type': 'object',
                'additionalProperties': False,
                'properties': {
                    'keywords': {'type': 'array', 'items': {'type': 'string'}},
                    'required': {'type': 'array', 'items': {'type': 'string'}},
                    'forbidden': {'type': 'array', 'items': {'type': 'string'}},
                },
                'required': ['keywords', 'required', 'forbidden'],
            },
            'fields': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'additionalProperties': False,
                    'properties': {
                        'field_key': {'type': 'string'},
                        'label': {'type': 'string'},
                        'required': {'type': 'boolean'},
                        'anchors': {'type': 'array', 'items': {'type': 'string'}},
                        'regex': {'type': 'string'},
                        'aliases': {'type': 'array', 'items': {'type': 'string'}},
                        'postprocess': {'type': 'string'},
                    },
                    'required': ['field_key', 'label', 'required', 'anchors', 'regex', 'aliases', 'postprocess'],
                },
            },
            'lines': {
                'type': 'object',
                'additionalProperties': False,
                'properties': {
                    'enabled': {'type': 'boolean'},
                    'header_aliases': {'type': 'array', 'items': {'type': 'string'}},
                    'stop_keywords': {'type': 'array', 'items': {'type': 'string'}},
                },
                'required': ['enabled', 'header_aliases', 'stop_keywords'],
            },
            'notes': {'type': 'array', 'items': {'type': 'string'}},
        },
        'required': ['name', 'fingerprint', 'doc_type', 'score_min_match', 'match_rules', 'fields', 'lines', 'notes'],
    }


def llm_suggestions_available() -> bool:
    return bool(_document_ai_api_key())


def suggest_template_definition(context: dict[str, Any]) -> dict[str, Any]:
    if not llm_suggestions_available():
        return {
            'ok': False,
            'available': False,
            'message': 'Integração LLM indisponível. Configura SHOP_TRANSLATE_OPENAI_API_KEY na tabela PARA.',
            'suggestion': None,
        }

    source_context = context or {}
    request_payload = {
        'task': 'document_template_suggestion',
        'goal': 'Infer a robust text-based parsing template for purchase documents using anchors, regex and keyword rules.',
        'rules': [
            'Return JSON only.',
            'Prefer text anchors and textual patterns over fixed coordinates.',
            'Do not invent values not visible in the document text.',
            'Keep regex practical and minimal.',
            'When uncertain, leave anchors or regex empty rather than fabricating.',
            'Fields should focus on document_number, document_date, supplier_tax_id, supplier_name, customer_name, currency, net_total, tax_total and gross_total.',
        ],
        'context': {
            'document_type': source_context.get('document_type') or 'unknown',
            'supplier_no': source_context.get('supplier_no'),
            'supplier_name': source_context.get('supplier_name') or '',
            'file_name': source_context.get('file_name') or '',
            'selected_text': source_context.get('selected_text') or '',
            'current_template': source_context.get('current_template') or {},
            'current_result': source_context.get('current_result') or {},
            'extracted_text_sample': str(source_context.get('extracted_text') or '')[:12000],
        },
    }

    body = {
        'model': _document_ai_model(),
        'input': [
            {
                'role': 'system',
                'content': [
                    {
                        'type': 'input_text',
                        'text': (
                            'You design structured parsing templates for business purchase documents. '
                            'Return valid JSON only, following the required schema.'
                        ),
                    }
                ],
            },
            {
                'role': 'user',
                'content': [
                    {
                        'type': 'input_text',
                        'text': json.dumps(request_payload, ensure_ascii=False),
                    }
                ],
            },
        ],
        'text': {
            'format': {
                'type': 'json_schema',
                'name': 'document_ai_template_suggestion',
                'schema': _field_suggestion_schema(),
            }
        },
    }

    req = urllib_request.Request(
        'https://api.openai.com/v1/responses',
        data=json.dumps(body).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {_document_ai_api_key()}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )

    try:
        with urllib_request.urlopen(req, timeout=40) as response:
            payload_response = json.loads(response.read().decode('utf-8'))
    except urllib_error.HTTPError as exc:
        details = ''
        try:
            details = exc.read().decode('utf-8')
        except Exception:
            details = str(exc)
        return {
            'ok': False,
            'available': True,
            'message': f'Falha na sugestão automática: {details[:280]}',
            'suggestion': None,
        }
    except Exception as exc:
        return {
            'ok': False,
            'available': True,
            'message': f'Falha na sugestão automática: {exc}',
            'suggestion': None,
        }

    raw_text = _strip_json_fence(_extract_openai_text(payload_response))
    if not raw_text:
        return {
            'ok': False,
            'available': True,
            'message': 'A OpenAI não devolveu conteúdo utilizável para sugestão.',
            'suggestion': None,
        }

    try:
        suggestion = json.loads(raw_text)
    except Exception:
        return {
            'ok': False,
            'available': True,
            'message': 'A resposta da OpenAI não veio em JSON válido.',
            'suggestion': None,
            'raw_text': raw_text,
        }

    return {
        'ok': True,
        'available': True,
        'message': 'Sugestão automática gerada.',
        'suggestion': suggestion,
        'model': _document_ai_model(),
    }
