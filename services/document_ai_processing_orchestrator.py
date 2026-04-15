import os
from typing import Any

from flask import current_app

from services.document_ai_image_preprocessor import apply_manual_adjustments, default_preprocess_config, preprocess_document_image
from services.document_ai_ocr_service import extract_image_text_from_object, ocr_engine_available
from services.document_ai_quality_evaluator import evaluate_text_quality
from services.document_ai_text_extractor import (
    build_plain_text_payload,
    detect_source_kind,
    extract_pdf_direct_text,
    load_image_source,
    render_pdf_to_images,
)


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def _public_path_from_absolute(absolute_path: str) -> str:
    root = current_app.root_path
    relative = os.path.relpath(absolute_path, root)
    return '/' + relative.replace(os.sep, '/')


def _save_preprocessed_images(document_stamp: str, processed_pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not processed_pages:
        return []
    folder = os.path.join(current_app.root_path, 'static', 'images', 'document_ai_preprocessed')
    _ensure_dir(folder)
    saved = []
    for page in processed_pages:
        image = page.get('image')
        if image is None:
            continue
        file_name = f'{document_stamp or "doc"}-p{int(page.get("page") or 1)}.png'
        absolute_path = os.path.join(folder, file_name)
        image.save(absolute_path, format='PNG')
        saved.append({
            'page': int(page.get('page') or 1),
            'public_path': _public_path_from_absolute(absolute_path),
        })
    return saved


def _ocr_pages(pages: list[dict[str, Any]]) -> dict[str, Any]:
    warnings = []
    all_text = []
    all_blocks = []
    raw_pages = []
    engines = []
    for page in pages:
        payload = extract_image_text_from_object(
            page.get('image'),
            page_number=int(page.get('page') or 1),
            page_label=str(page.get('page') or ''),
        )
        warnings.extend(payload.get('warnings') or [])
        engine = str(payload.get('engine') or '').strip()
        if engine:
            engines.append(engine)
        if payload.get('text'):
            all_text.append(payload.get('text') or '')
        all_blocks.extend(payload.get('blocks') or [])
        raw_pages.append({
            'page': int(page.get('page') or 1),
            'raw_json': payload.get('raw_json') or {},
            'engine': engine,
        })
    engine_name = ''
    if engines:
        unique = list(dict.fromkeys(engines))
        engine_name = unique[0] if len(unique) == 1 else '+'.join(unique)
    return {
        'ok': bool('\n'.join(all_text).strip()),
        'engine': engine_name or (None if not ocr_engine_available() else ''),
        'text': '\n'.join(chunk for chunk in all_text if chunk).strip(),
        'blocks': all_blocks,
        'raw_json': {'pages': raw_pages},
        'warnings': warnings,
    }


def _choose_best_attempt(direct_attempt: dict[str, Any] | None, visual_attempt: dict[str, Any] | None) -> dict[str, Any]:
    if visual_attempt and visual_attempt.get('quality', {}).get('score', 0) >= (direct_attempt or {}).get('quality', {}).get('score', 0):
        return visual_attempt
    if direct_attempt:
        return direct_attempt
    if visual_attempt:
        return visual_attempt
    return {
        'ok': False,
        'method': 'failed',
        'engine': None,
        'text': '',
        'blocks': [],
        'raw_json': {},
        'quality': evaluate_text_quality('', []),
        'warnings': ['Nenhum pipeline conseguiu produzir texto utilizável.'],
        'notes': {'attempts': []},
        'preprocessed_image_path': '',
        'last_error': '',
        'fallback_used': False,
    }


def extract_document_with_cascade(
    file_path: str,
    file_ext: str = '',
    mime_type: str = '',
    document_stamp: str = '',
    force_mode: str = 'auto',
    manual_adjustments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not os.path.isfile(file_path):
        return {
            'ok': False,
            'method': 'failed',
            'engine': None,
            'text': '',
            'blocks': [],
            'raw_json': {},
            'quality': evaluate_text_quality('', []),
            'warnings': ['Ficheiro não encontrado no disco.'],
            'notes': {'attempts': [], 'source_kind': 'unknown'},
            'preprocessed_image_path': '',
            'last_error': 'file_not_found',
            'fallback_used': False,
        }

    source_kind = detect_source_kind(file_ext, mime_type)
    attempts = []
    direct_attempt = None
    visual_attempt = None

    if source_kind == 'pdf' and force_mode == 'auto':
        direct_payload = extract_pdf_direct_text(file_path)
        direct_quality = evaluate_text_quality(direct_payload.get('text') or '', direct_payload.get('blocks') or [])
        direct_attempt = {
            **direct_payload,
            'quality': direct_quality,
            'preprocessed_image_path': '',
            'fallback_used': False,
        }
        attempts.append({
            'method': 'direct_pdf_text',
            'engine': direct_payload.get('engine'),
            'score': direct_quality.get('score'),
            'usable': direct_quality.get('usable'),
            'warnings': direct_payload.get('warnings') or [],
        })
        if direct_payload.get('ok') and direct_quality.get('usable'):
            direct_payload['quality'] = direct_quality
            direct_payload['notes'] = {
                'attempts': attempts,
                'selected_method': 'direct_pdf_text',
                'source_kind': source_kind,
                'fallback_triggered': False,
            }
            direct_payload['preprocessed_image_path'] = ''
            direct_payload['last_error'] = ''
            direct_payload['fallback_used'] = False
            return direct_payload

    visual_warnings = []
    page_source = None
    preprocess_cfg = default_preprocess_config()
    if force_mode == 'ocr':
        preprocess_cfg.update({
            'grayscale': False,
            'denoise': False,
            'contrast': False,
            'threshold': False,
            'deskew': False,
            'normalize_resolution': False,
        })
    if source_kind == 'pdf':
        page_source = render_pdf_to_images(file_path)
    elif source_kind == 'image':
        page_source = load_image_source(file_path)
    else:
        plain_payload = build_plain_text_payload(file_path)
        plain_quality = evaluate_text_quality(plain_payload.get('text') or '', plain_payload.get('blocks') or [])
        plain_payload['quality'] = plain_quality
        plain_payload['notes'] = {
            'attempts': [{
                'method': 'plain_text',
                'engine': plain_payload.get('engine'),
                'score': plain_quality.get('score'),
                'usable': plain_quality.get('usable'),
            }],
            'selected_method': 'plain_text' if plain_payload.get('ok') else 'failed',
            'source_kind': source_kind,
            'fallback_triggered': False,
        }
        plain_payload['preprocessed_image_path'] = ''
        plain_payload['last_error'] = ''
        plain_payload['fallback_used'] = False
        return plain_payload

    if not page_source or not page_source.get('ok') or not page_source.get('pages'):
        visual_warnings.extend((page_source or {}).get('warnings') or [])
    else:
        processed_pages = []
        processing_notes = []
        for page in page_source.get('pages') or []:
            manual = apply_manual_adjustments(page.get('image'), manual_adjustments, page_number=page.get('page') or 1)
            processed = preprocess_document_image(manual.get('image'), preprocess_cfg)
            visual_warnings.extend(processed.get('warnings') or [])
            visual_warnings.extend(manual.get('warnings') or [])
            processing_notes.append({
                'page': int(page.get('page') or 1),
                'steps': processed.get('applied_steps') or [],
                'notes': (processed.get('notes') or []) + (manual.get('notes') or []),
                'geometry_changed': bool(processed.get('geometry_changed')),
            })
            processed_pages.append({
                'page': int(page.get('page') or 1),
                'image': processed.get('image') or page.get('image'),
            })
        saved_refs = _save_preprocessed_images(document_stamp, processed_pages) if processed_pages else []
        ocr_payload = _ocr_pages(processed_pages)
        visual_quality = evaluate_text_quality(ocr_payload.get('text') or '', ocr_payload.get('blocks') or [])
        visual_attempt = {
            **ocr_payload,
            'method': 'direct_image_ocr' if source_kind == 'image' else 'ocr_image_fallback',
            'quality': visual_quality,
            'preprocessed_image_path': (saved_refs[0]['public_path'] if saved_refs else ''),
            'fallback_used': source_kind == 'pdf',
            'notes': {
                'attempts': [],
                'preprocess': processing_notes,
                'preprocessed_images': saved_refs,
                'source_kind': source_kind,
            },
        }
        attempts.append({
            'method': visual_attempt.get('method'),
            'engine': visual_attempt.get('engine'),
            'score': visual_quality.get('score'),
            'usable': visual_quality.get('usable'),
            'warnings': visual_warnings + (ocr_payload.get('warnings') or []),
        })

    selected = _choose_best_attempt(direct_attempt, visual_attempt)
    selected['warnings'] = list(dict.fromkeys((selected.get('warnings') or []) + visual_warnings))
    selected['notes'] = {
        **(selected.get('notes') or {}),
        'attempts': attempts,
        'selected_method': selected.get('method') or 'failed',
        'source_kind': source_kind,
        'fallback_triggered': bool(visual_attempt and source_kind == 'pdf'),
        'manual_adjustments': manual_adjustments or {},
    }
    selected['last_error'] = '' if selected.get('ok') else 'no_usable_text'
    return selected
