import json
import os
import socket
import base64
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


def _document_ai_timeout() -> int:
    raw_value = (
        _para_value('DOC_AI_OPENAI_TIMEOUT')
        or os.getenv('DOC_AI_OPENAI_TIMEOUT')
        or '180'
    )
    try:
        return max(30, min(600, int(float(raw_value))))
    except Exception:
        return 180


def _document_ai_text_sample_limit() -> int:
    raw_value = (
        _para_value('DOC_AI_OPENAI_TEXT_LIMIT')
        or os.getenv('DOC_AI_OPENAI_TEXT_LIMIT')
        or '24000'
    )
    try:
        return max(4000, min(120000, int(float(raw_value))))
    except Exception:
        return 24000


def _document_ai_max_output_tokens() -> int:
    raw_value = (
        _para_value('DOC_AI_OPENAI_MAX_OUTPUT_TOKENS')
        or os.getenv('DOC_AI_OPENAI_MAX_OUTPUT_TOKENS')
        or '6000'
    )
    try:
        return max(1200, min(16000, int(float(raw_value))))
    except Exception:
        return 6000


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


def _document_classification_schema() -> dict[str, Any]:
    return {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'document_type': {
                'type': 'string',
                'enum': ['invoice', 'credit_note', 'purchase_order', 'delivery_note', 'unknown'],
            },
            'confidence': {'type': 'number'},
            'reason': {'type': 'string'},
            'document_number': {'type': 'string'},
            'document_date': {'type': 'string'},
            'due_date': {'type': 'string'},
            'currency': {'type': 'string'},
            'supplier': {
                'type': 'object',
                'additionalProperties': False,
                'properties': {
                    'tax_id': {'type': 'string'},
                    'name': {'type': 'string'},
                },
                'required': ['tax_id', 'name'],
            },
            'customer': {
                'type': 'object',
                'additionalProperties': False,
                'properties': {
                    'tax_id': {'type': 'string'},
                    'name': {'type': 'string'},
                },
                'required': ['tax_id', 'name'],
            },
            'totals': {
                'type': 'object',
                'additionalProperties': False,
                'properties': {
                    'net_total': {'type': 'number'},
                    'tax_total': {'type': 'number'},
                    'gross_total': {'type': 'number'},
                },
                'required': ['net_total', 'tax_total', 'gross_total'],
            },
            'taxes': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'additionalProperties': False,
                    'properties': {
                        'tax_rate': {'type': 'number'},
                        'taxable_base': {'type': 'number'},
                        'tax_amount': {'type': 'number'},
                        'gross_total': {'type': 'number'},
                    },
                    'required': ['tax_rate', 'taxable_base', 'tax_amount', 'gross_total'],
                },
            },
            'visible_language': {'type': 'string'},
            'notes': {'type': 'array', 'items': {'type': 'string'}},
        },
        'required': [
            'document_type',
            'confidence',
            'reason',
            'document_number',
            'document_date',
            'due_date',
            'currency',
            'supplier',
            'customer',
            'totals',
            'taxes',
            'visible_language',
            'notes',
        ],
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
    text_limit = _document_ai_text_sample_limit()
    extracted_text = str(source_context.get('extracted_text') or '')
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
            'extracted_text_sample': extracted_text[:text_limit],
            'extracted_text_truncated': len(extracted_text) > text_limit,
            'extracted_text_original_chars': len(extracted_text),
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
        'max_output_tokens': _document_ai_max_output_tokens(),
    }

    try:
        body_bytes = json.dumps(body).encode('utf-8')
        timeout_seconds = _document_ai_timeout()
        current_app.logger.info(
            'Document AI OpenAI suggestion: model=%s timeout=%ss input_bytes=%s text_chars=%s truncated=%s',
            _document_ai_model(),
            timeout_seconds,
            len(body_bytes),
            len(extracted_text),
            len(extracted_text) > text_limit,
        )
        req = urllib_request.Request(
            'https://api.openai.com/v1/responses',
            data=body_bytes,
            headers={
                'Authorization': f'Bearer {_document_ai_api_key()}',
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        with urllib_request.urlopen(req, timeout=timeout_seconds) as response:
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
    except (TimeoutError, socket.timeout) as exc:
        return {
            'ok': False,
            'available': True,
            'message': (
                'Falha na sugestão automática: a OpenAI demorou mais do que '
                f'{_document_ai_timeout()}s a responder. Pode aumentar DOC_AI_OPENAI_TIMEOUT na PARA.'
            ),
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


def classify_document_visual(context: dict[str, Any]) -> dict[str, Any]:
    if not llm_suggestions_available():
        return {
            'ok': False,
            'available': False,
            'message': 'Integração LLM indisponível. Configura DOC_AI_OPENAI_API_KEY na tabela PARA.',
            'classification': None,
        }

    source_context = context or {}
    file_name = str(source_context.get('file_name') or 'documento').strip() or 'documento'
    mime_type = str(source_context.get('mime_type') or 'application/pdf').strip() or 'application/pdf'
    file_bytes = source_context.get('file_bytes') or b''
    image_bytes = source_context.get('image_bytes') or b''
    image_mime_type = str(source_context.get('image_mime_type') or 'image/png').strip() or 'image/png'
    extracted_text = str(source_context.get('extracted_text') or '')

    if not file_bytes and not image_bytes:
        return {
            'ok': False,
            'available': True,
            'message': 'Não há ficheiro ou imagem disponível para enviar ao LLM.',
            'classification': None,
        }

    base_prompt = {
        'task': 'document_visual_classification',
        'goal': 'Classify the visible business document and extract the accounting header values needed for purchase validation.',
        'allowed_document_types': {
            'invoice': 'Invoice / Fatura / Facture',
            'credit_note': 'Credit note / Nota de crédito / Avoir',
            'purchase_order': 'Purchase order / Nota de encomenda / Bon de commande',
            'delivery_note': 'Delivery note / Guia / Bon de livraison / Bon d’enlèvement',
            'unknown': 'Use this when the document is not one of the above.',
        },
        'rules': [
            'Return JSON only.',
            'Do not infer values that are not visible.',
            'Prefer visual evidence from the PDF/image over OCR text when they conflict.',
            'Dates must be ISO yyyy-mm-dd when visible; otherwise empty string.',
            'Amounts must be numeric values without currency symbols.',
            'Extract supplier name and tax/VAT id from the issuer/seller section.',
            'Extract customer name and tax/VAT id from the buyer/delivery/customer section.',
            'Extract document number, document date, due date if visible, currency, net total without VAT, VAT total and gross total with VAT.',
            'Extract VAT/tax breakdown rows by rate when visible. Use taxes=[] when no VAT breakdown is visible.',
            'For delivery notes without prices, keep totals as 0 and explain that values are not visible in notes.',
            'Use unknown when the visible document type is uncertain.',
        ],
        'file_name': file_name,
        'ocr_text_sample': extracted_text[:_document_ai_text_sample_limit()],
    }

    def call_openai(content: list[dict[str, Any]], mode: str) -> dict[str, Any]:
        body = {
            'model': _document_ai_model(),
            'input': [
                {
                    'role': 'system',
                    'content': [
                        {
                            'type': 'input_text',
                            'text': (
                                'You classify and extract purchase-side business documents from visual evidence. '
                                'Return valid JSON only, following the required schema.'
                            ),
                        }
                    ],
                },
                {
                    'role': 'user',
                    'content': content,
                },
            ],
            'text': {
                'format': {
                    'type': 'json_schema',
                    'name': 'document_ai_visual_classification',
                    'schema': _document_classification_schema(),
                }
            },
            'max_output_tokens': min(_document_ai_max_output_tokens(), 3000),
        }
        body_bytes = json.dumps(body).encode('utf-8')
        current_app.logger.info(
            'Document AI OpenAI visual classification: model=%s mode=%s timeout=%ss input_bytes=%s',
            _document_ai_model(),
            mode,
            _document_ai_timeout(),
            len(body_bytes),
        )
        req = urllib_request.Request(
            'https://api.openai.com/v1/responses',
            data=body_bytes,
            headers={
                'Authorization': f'Bearer {_document_ai_api_key()}',
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        with urllib_request.urlopen(req, timeout=_document_ai_timeout()) as response:
            return json.loads(response.read().decode('utf-8'))

    attempts: list[tuple[str, list[dict[str, Any]]]] = []
    if file_bytes and mime_type == 'application/pdf':
        attempts.append((
            'pdf',
            [
                {'type': 'input_text', 'text': json.dumps(base_prompt, ensure_ascii=False)},
                {
                    'type': 'input_file',
                    'filename': file_name if file_name.lower().endswith('.pdf') else f'{file_name}.pdf',
                    'file_data': f'data:{mime_type};base64,{base64.b64encode(file_bytes).decode("ascii")}',
                },
            ],
        ))
    if image_bytes:
        attempts.append((
            'image',
            [
                {'type': 'input_text', 'text': json.dumps(base_prompt, ensure_ascii=False)},
                {
                    'type': 'input_image',
                    'image_url': f'data:{image_mime_type};base64,{base64.b64encode(image_bytes).decode("ascii")}',
                },
            ],
        ))

    last_message = ''
    for mode, content in attempts:
        try:
            payload_response = call_openai(content, mode)
        except urllib_error.HTTPError as exc:
            try:
                details = exc.read().decode('utf-8')
            except Exception:
                details = str(exc)
            last_message = details[:500]
            current_app.logger.info('Document AI visual classification failed with %s: %s', mode, last_message)
            continue
        except (TimeoutError, socket.timeout):
            last_message = f'A OpenAI demorou mais do que {_document_ai_timeout()}s a responder.'
            continue
        except Exception as exc:
            last_message = str(exc)
            continue

        raw_text = _strip_json_fence(_extract_openai_text(payload_response))
        if not raw_text:
            last_message = 'A OpenAI não devolveu conteúdo utilizável.'
            continue
        try:
            classification = json.loads(raw_text)
        except Exception:
            last_message = 'A resposta da OpenAI não veio em JSON válido.'
            continue
        return {
            'ok': True,
            'available': True,
            'message': f'Classificação LLM gerada por {mode}.',
            'classification': classification,
            'mode': mode,
            'model': _document_ai_model(),
        }

    return {
        'ok': False,
        'available': True,
        'message': f'Falha na classificação visual: {last_message or "sem resposta utilizável"}',
        'classification': None,
    }
