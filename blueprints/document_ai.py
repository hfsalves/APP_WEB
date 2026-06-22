import io

from flask import Blueprint, current_app, jsonify, render_template, request, send_file
from flask_login import current_user, login_required

from models import Acessos, db
from services.document_ai_service import (
    classify_document_with_llm,
    delete_document_from_inbox,
    delete_document_source,
    document_ai_lookups,
    get_document_detail,
    get_document_original_file,
    get_document_preview_page,
    get_document_source,
    get_template_detail,
    ingest_uploaded_document,
    list_document_sources,
    list_documents,
    list_templates,
    reprocess_document,
    resolve_fe_entity,
    save_document_source,
    save_document_review,
    save_template,
    save_template_from_document,
    search_suppliers,
    suggest_template,
    test_template,
    toggle_template_active,
)


bp = Blueprint('document_ai', __name__)


def _document_ai_has_access(action: str = 'consultar') -> bool:
    if bool(getattr(current_user, 'ADMIN', False) or getattr(current_user, 'DEV', False)):
        return True
    login = str(getattr(current_user, 'LOGIN', '') or '').strip()
    if not login:
        return False
    for table_name in ('DOC_AI', 'DOC_INTEL', 'FO'):
        acesso = Acessos.query.filter_by(utilizador=login, tabela=table_name).first()
        if acesso and bool(getattr(acesso, action, False)):
            return True
    return False


def _current_login() -> str:
    return str(getattr(current_user, 'LOGIN', '') or '').strip()


@bp.route('/document_ai/inbox')
@login_required
def document_ai_inbox_page():
    if not _document_ai_has_access('consultar'):
        return render_template('error.html', message='Sem permissão para consultar processamento documental.'), 403
    return render_template('document_ai_inbox.html', page_title='Processamento Documental')


@bp.route('/document_ai/review/<docinstamp>')
@login_required
def document_ai_review_page(docinstamp: str):
    if not _document_ai_has_access('consultar'):
        return render_template('error.html', message='Sem permissão para validar documentos.'), 403
    return render_template(
        'document_ai_review.html',
        page_title='Validação Documental',
        docinstamp=str(docinstamp or '').strip(),
    )


@bp.route('/document_ai/templates')
@login_required
def document_ai_templates_page():
    if not _document_ai_has_access('consultar'):
        return render_template('error.html', message='Sem permissão para gerir templates documentais.'), 403
    return render_template('document_ai_templates.html', page_title='Modelos Documentais')


@bp.route('/document_ai/sources')
@login_required
def document_ai_sources_page():
    if not _document_ai_has_access('consultar'):
        return render_template('error.html', message='Sem permissão para gerir origens documentais.'), 403
    return render_template('document_ai_sources.html', page_title='Origens Documentais')


@bp.route('/api/document_ai/lookups', methods=['GET'])
@login_required
def api_document_ai_lookups():
    if not _document_ai_has_access('consultar'):
        return jsonify({'error': 'Sem permissão.'}), 403
    return jsonify(document_ai_lookups())


@bp.route('/api/document_ai/inbox', methods=['GET'])
@login_required
def api_document_ai_inbox():
    if not _document_ai_has_access('consultar'):
        return jsonify({'error': 'Sem permissão.'}), 403
    filters = {
        'status': request.args.get('status', ''),
        'doc_type': request.args.get('doc_type', ''),
        'supplier': request.args.get('supplier', ''),
        'search': request.args.get('search', ''),
        'date_from': request.args.get('date_from', ''),
        'date_to': request.args.get('date_to', ''),
    }
    return jsonify(list_documents(filters))


@bp.route('/api/document_ai/sources', methods=['GET'])
@login_required
def api_document_ai_sources():
    if not _document_ai_has_access('consultar'):
        return jsonify({'error': 'Sem permissão.'}), 403
    try:
        return jsonify(list_document_sources())
    except Exception as exc:
        current_app.logger.exception('Erro ao carregar origens documentais')
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/sources/<source_id>', methods=['GET'])
@login_required
def api_document_ai_source_detail(source_id: str):
    if not _document_ai_has_access('consultar'):
        return jsonify({'error': 'Sem permissão.'}), 403
    try:
        return jsonify(get_document_source(source_id))
    except Exception as exc:
        current_app.logger.exception('Erro ao carregar origem documental')
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/sources', methods=['POST'])
@login_required
def api_document_ai_source_create():
    if not _document_ai_has_access('inserir'):
        return jsonify({'error': 'Sem permissão para criar origens.'}), 403
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(save_document_source(body, _current_login())), 201
    except Exception as exc:
        current_app.logger.exception('Erro ao criar origem documental')
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/sources/<source_id>', methods=['PUT'])
@login_required
def api_document_ai_source_update(source_id: str):
    if not _document_ai_has_access('editar'):
        return jsonify({'error': 'Sem permissão para editar origens.'}), 403
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(save_document_source(body, _current_login(), source_id))
    except Exception as exc:
        current_app.logger.exception('Erro ao atualizar origem documental')
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/sources/<source_id>', methods=['DELETE'])
@login_required
def api_document_ai_source_delete(source_id: str):
    if not _document_ai_has_access('eliminar'):
        return jsonify({'error': 'Sem permissão para remover origens.'}), 403
    try:
        return jsonify(delete_document_source(source_id))
    except Exception as exc:
        current_app.logger.exception('Erro ao remover origem documental')
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/documents/upload', methods=['POST'])
@login_required
def api_document_ai_upload():
    if not _document_ai_has_access('inserir'):
        return jsonify({'error': 'Sem permissão para importar documentos.'}), 403
    uploaded_file = request.files.get('file')
    if not uploaded_file:
        return jsonify({'error': 'Ficheiro em falta.'}), 400
    try:
        payload = ingest_uploaded_document(
            uploaded_file,
            created_by=_current_login(),
            source_table=request.form.get('source_table', ''),
            source_recstamp=request.form.get('source_recstamp', ''),
        )
        return jsonify(payload), 201
    except Exception as exc:
        current_app.logger.exception('Erro no upload documental')
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/documents/<docinstamp>', methods=['GET'])
@login_required
def api_document_ai_document_detail(docinstamp: str):
    if not _document_ai_has_access('consultar'):
        return jsonify({'error': 'Sem permissão.'}), 403
    try:
        return jsonify(get_document_detail(docinstamp))
    except Exception as exc:
        current_app.logger.exception('Erro ao carregar detalhe documental')
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/documents/<docinstamp>', methods=['DELETE'])
@login_required
def api_document_ai_document_delete(docinstamp: str):
    if not _document_ai_has_access('eliminar'):
        return jsonify({'error': 'Sem permissão para eliminar documentos.'}), 403
    try:
        return jsonify(delete_document_from_inbox(docinstamp, _current_login()))
    except Exception as exc:
        current_app.logger.exception('Erro ao eliminar documento do inbox')
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/documents/<docinstamp>/preview', methods=['GET'])
@login_required
def api_document_ai_document_preview(docinstamp: str):
    if not _document_ai_has_access('consultar'):
        return jsonify({'error': 'Sem permissão.'}), 403
    try:
        preview = get_document_preview_page(docinstamp, request.args.get('page', 1))
        if preview.get('kind') == 'bytes':
            return send_file(
                io.BytesIO(preview.get('data') or b''),
                mimetype=preview.get('mime_type') or 'image/png',
                download_name=preview.get('file_name') or 'preview.png',
            )
        return send_file(
            preview.get('path'),
            mimetype=preview.get('mime_type') or 'application/octet-stream',
            download_name=preview.get('file_name') or 'preview.bin',
        )
    except Exception as exc:
        current_app.logger.exception('Erro ao gerar preview documental')
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/documents/<docinstamp>/original', methods=['GET'])
@login_required
def api_document_ai_document_original(docinstamp: str):
    if not _document_ai_has_access('consultar'):
        return jsonify({'error': 'Sem permissão.'}), 403
    try:
        original = get_document_original_file(docinstamp)
        return send_file(
            original.get('path'),
            mimetype=original.get('mime_type') or 'application/octet-stream',
            download_name=original.get('file_name') or 'documento.pdf',
            as_attachment=False,
        )
    except Exception as exc:
        current_app.logger.exception('Erro ao abrir documento original')
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/documents/<docinstamp>/reprocess', methods=['POST'])
@login_required
def api_document_ai_document_reprocess(docinstamp: str):
    if not _document_ai_has_access('editar'):
        return jsonify({'error': 'Sem permissão para reprocessar.'}), 403
    body = request.get_json(silent=True) or {}
    try:
        payload = reprocess_document(
            docinstamp,
            requested_by=_current_login(),
            forced_template_stamp=body.get('template_id', ''),
            reprocess_mode=str(body.get('reprocess_mode') or 'auto').strip() or 'auto',
            manual_adjustments=body.get('manual_adjustments') or None,
            working_template_payload=body.get('current_template') or None,
        )
        return jsonify(payload)
    except Exception as exc:
        current_app.logger.exception('Erro ao reprocessar documento')
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/documents/<docinstamp>/classify_llm', methods=['POST'])
@login_required
def api_document_ai_document_classify_llm(docinstamp: str):
    if not _document_ai_has_access('consultar'):
        return jsonify({'error': 'Sem permissão.'}), 403
    try:
        return jsonify(classify_document_with_llm(docinstamp, _current_login()))
    except Exception as exc:
        current_app.logger.exception('Erro ao classificar documento com LLM')
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/documents/<docinstamp>/validate', methods=['POST'])
@login_required
def api_document_ai_document_validate(docinstamp: str):
    if not _document_ai_has_access('editar'):
        return jsonify({'error': 'Sem permissão para validar.'}), 403
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(save_document_review(docinstamp, body, _current_login()))
    except Exception as exc:
        current_app.logger.exception('Erro ao gravar validação documental')
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/documents/<docinstamp>/save_template', methods=['POST'])
@login_required
def api_document_ai_document_save_template(docinstamp: str):
    if not _document_ai_has_access('editar'):
        return jsonify({'error': 'Sem permissão para guardar templates.'}), 403
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(save_template_from_document(docinstamp, body, _current_login()))
    except Exception as exc:
        current_app.logger.exception('Erro ao guardar template a partir do documento')
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/templates', methods=['GET'])
@login_required
def api_document_ai_templates():
    if not _document_ai_has_access('consultar'):
        return jsonify({'error': 'Sem permissão.'}), 403
    filters = {
        'search': request.args.get('search', ''),
        'doc_type': request.args.get('doc_type', ''),
        'supplier': request.args.get('supplier', ''),
        'active': request.args.get('active', ''),
    }
    return jsonify(list_templates(filters))


@bp.route('/api/document_ai/templates/<template_id>', methods=['GET'])
@login_required
def api_document_ai_template_detail(template_id: str):
    if not _document_ai_has_access('consultar'):
        return jsonify({'error': 'Sem permissão.'}), 403
    try:
        return jsonify(get_template_detail(template_id))
    except Exception as exc:
        current_app.logger.exception('Erro ao carregar template documental')
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/templates', methods=['POST'])
@login_required
def api_document_ai_template_create():
    if not _document_ai_has_access('editar'):
        return jsonify({'error': 'Sem permissão para criar templates.'}), 403
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(save_template(body, _current_login())), 201
    except Exception as exc:
        current_app.logger.exception('Erro ao criar template documental')
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/templates/<template_id>', methods=['PUT'])
@login_required
def api_document_ai_template_update(template_id: str):
    if not _document_ai_has_access('editar'):
        return jsonify({'error': 'Sem permissão para editar templates.'}), 403
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(save_template(body, _current_login(), template_id))
    except Exception as exc:
        current_app.logger.exception('Erro ao atualizar template documental')
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/templates/<template_id>/toggle', methods=['POST'])
@login_required
def api_document_ai_template_toggle(template_id: str):
    if not _document_ai_has_access('editar'):
        return jsonify({'error': 'Sem permissão.'}), 403
    try:
        return jsonify(toggle_template_active(template_id, _current_login()))
    except Exception as exc:
        current_app.logger.exception('Erro ao alternar template documental')
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/templates/<template_id>/test', methods=['POST'])
@login_required
def api_document_ai_template_test(template_id: str):
    if not _document_ai_has_access('consultar'):
        return jsonify({'error': 'Sem permissão.'}), 403
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(test_template(template_id, body.get('document_id', '')))
    except Exception as exc:
        current_app.logger.exception('Erro a testar template documental')
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/suggest', methods=['POST'])
@login_required
def api_document_ai_suggest():
    if not _document_ai_has_access('consultar'):
        return jsonify({'error': 'Sem permissão.'}), 403
    body = request.get_json(silent=True) or {}
    return jsonify(suggest_template(body))


@bp.route('/api/document_ai/suppliers/search', methods=['GET'])
@login_required
def api_document_ai_suppliers_search():
    if not _document_ai_has_access('consultar'):
        return jsonify({'error': 'Sem permissão.'}), 403
    term = str(request.args.get('q', '') or '').strip()
    if len(term) < 2:
        return jsonify([])
    feid = request.args.get('feid', type=int)
    if not feid:
        return jsonify({'error': 'Identifica primeiro a Entidade FE do cliente.'}), 400
    limit = request.args.get('limit', default=8, type=int)
    try:
        return jsonify(search_suppliers(term, feid=feid, limit=limit))
    except Exception as exc:
        current_app.logger.exception('Erro ao pesquisar fornecedores Document AI')
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/entities/resolve', methods=['GET'])
@login_required
def api_document_ai_entities_resolve():
    if not _document_ai_has_access('consultar'):
        return jsonify({'error': 'Sem permissão.'}), 403
    term = str(request.args.get('q', '') or '').strip()
    mode = str(request.args.get('mode', 'auto') or 'auto').strip() or 'auto'
    if len(term) < 2:
        return jsonify({})
    try:
        return jsonify(resolve_fe_entity(term, mode))
    except Exception as exc:
        current_app.logger.exception('Erro ao resolver entidade FE documental')
        return jsonify({'error': str(exc)}), 500
