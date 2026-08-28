import hashlib
import io
import json

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from models import Acessos, db
from services.document_ai_service import (
    classify_document_with_llm,
    clear_document_phc_origin,
    delete_document_from_inbox,
    document_belongs_to_inbox_view,
    delete_document_source,
    document_ai_lookups,
    get_document_detail,
    get_document_group,
    get_document_phc_origins,
    get_phc_document_origin_detail,
    get_next_phc_correspondence_reference,
    get_cached_llm_extraction,
    get_document_original_file,
    get_document_preview_page,
    get_document_source,
    get_template_detail,
    get_document_integration_access,
    ingest_uploaded_document,
    ensure_llm_inbox_document,
    find_llm_inbox_document,
    list_document_sources,
    list_document_integration_access_users,
    list_documents,
    list_templates,
    mark_document_as_provisional_invoice,
    mark_document_control_ok,
    mark_document_validation_error,
    preflight_document_inbox_stage,
    reprocess_document,
    reconcile_extracted_document,
    reset_llm_extraction,
    require_document_control_ok,
    resolve_fe_entity,
    save_document_source,
    save_document_integration_access,
    save_document_review,
    save_document_phc_origin,
    save_document_adjusted_lines,
    save_llm_extraction,
    save_template,
    save_template_from_document,
    search_suppliers,
    search_fe_entities,
    search_customers,
    search_external_parties,
    search_phc_document_origins,
    search_phc_articles,
    search_phc_vehicles,
    search_phc_projects,
    split_extracted_pdf_into_inbox,
    submit_correspondence_to_phc,
    submit_provisional_invoice_to_phc,
    suggest_template,
    test_template,
    toggle_template_active,
    validate_document_inbox_stage,
)
from services.document_ai_inbox_access_service import (
    INBOX_VIEW_DEFINITIONS,
    allowed_inbox_views,
    is_inbox_view_allowed,
)
from services.document_ai_access_service import (
    allowed_views as access_allowed_views,
    can_access_document,
    has_permission as has_document_ai_permission,
    is_access_admin as is_document_ai_access_admin,
    list_access_configuration,
    permission_profile as document_ai_permission_profile,
    save_access_configuration,
    scope_filters_for,
)
from services.document_ai_distribution_service import (
    delete_distribution_rule,
    distribution_impact,
    list_distribution_configuration,
    save_distribution_rule,
)
from services.document_ai_required_info_service import (
    delete_required_info_rule,
    list_required_info_configuration,
    save_required_info_rule,
)
from services.document_ai_llm_service import extract_document_full_visual


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


def _document_ai_is_admin() -> bool:
    return is_document_ai_access_admin(_current_login())


def _allowed_current_inbox_views() -> list[dict[str, str]]:
    return access_allowed_views(_current_login())


def _current_inbox_view_is_allowed(view: str) -> bool:
    return has_document_ai_permission(_current_login(), view, 'consult')


def _current_document_ai_permission(view: str, permission: str) -> bool:
    return has_document_ai_permission(_current_login(), view, permission)


def _current_document_access(docinstamp: str, view: str, permission: str) -> bool:
    return can_access_document(_current_login(), view, permission, docinstamp)


def _current_document_ai_any_permission(permission: str) -> bool:
    return any(
        _current_document_ai_permission(item['value'], permission)
        for item in _allowed_current_inbox_views()
    )


def _first_document_permission_view(docinstamp: str, permission: str) -> str:
    for item in _allowed_current_inbox_views():
        view = item['value']
        if _current_document_access(docinstamp, view, permission):
            return view
    return ''


def _current_feid_is_allowed(view: str, feid: int) -> bool:
    profile = document_ai_permission_profile(_current_login(), view)
    if not profile['allowed']:
        return False
    return bool(profile['all_entities'] or int(feid or 0) in set(profile['entity_ids']))


def _requested_document_ai_view() -> str:
    body = request.get_json(silent=True) if request.is_json else {}
    return str(
        request.args.get('view')
        or request.form.get('view')
        or (body or {}).get('view')
        or ''
    ).strip().lower()


def _document_ai_has_integration_access(document_type: str) -> bool:
    if _document_ai_is_admin():
        return True
    return bool(get_document_integration_access(_current_login()).get(str(document_type or '').strip().lower()))


@bp.route('/document_ai/inbox')
@login_required
def document_ai_inbox_page():
    if not _document_ai_has_access('consultar'):
        return render_template('error.html', message='Sem permissão para consultar processamento documental.'), 403
    inbox_views = _allowed_current_inbox_views()
    if not inbox_views:
        return render_template('error.html', message='Sem acesso ao Inbox.'), 403
    return render_template(
        'document_ai_inbox.html',
        page_title='Processamento Documental',
        document_ai_inbox_views=inbox_views,
        document_ai_access_admin=_document_ai_is_admin(),
    )


@bp.route('/document_ai/extract')
@login_required
def document_ai_extract_page():
    if not _document_ai_has_access('consultar'):
        return render_template('error.html', message='Sem permissão para extrair documentos.'), 403
    inbox_views = _allowed_current_inbox_views()
    if not inbox_views:
        return render_template('error.html', message='Sem acesso ao Inbox.'), 403
    requested_view = str(request.args.get('view') or inbox_views[0]['value']).strip().lower()
    if not _current_document_ai_permission(requested_view, 'analyze'):
        return render_template('error.html', message='Sem acesso a esta etapa documental.'), 403
    requested_document_id = str(request.args.get('document_id') or '').strip()
    if requested_document_id and not _current_document_access(requested_document_id, requested_view, 'analyze'):
        return render_template('error.html', message='Sem acesso a este documento.'), 403
    profile = document_ai_permission_profile(_current_login(), requested_view)
    return render_template(
        'document_ai_extract.html',
        page_title='Análise de Documentos',
        document_ai_inbox_views=inbox_views,
        document_ai_current_view=requested_view,
        can_validate_document=bool(profile['permissions'].get('validate')),
        can_analyze_document=bool(profile['permissions'].get('analyze')),
        can_delete_document=bool(profile['permissions'].get('delete') and requested_view in {'home', 'management'}),
        can_use_document_ai=bool(profile['permissions'].get('ai')),
        can_associate_document=bool(profile['permissions'].get('associate')),
        can_submit_correspondence=_document_ai_has_integration_access('correspondence'),
        can_submit_provisional_invoice=_document_ai_has_integration_access('provisional_invoice'),
        document_ai_access_admin=_document_ai_is_admin(),
    )


@bp.route('/document_ai/review/<docinstamp>')
@login_required
def document_ai_review_page(docinstamp: str):
    if not _document_ai_has_access('consultar'):
        return render_template('error.html', message='Sem permissão para validar documentos.'), 403
    document_id = str(docinstamp or '').strip()
    for item in _allowed_current_inbox_views():
        view = item['value']
        if _current_document_access(document_id, view, 'analyze'):
            return redirect(url_for('document_ai.document_ai_extract_page', document_id=document_id, view=view))
    return render_template('error.html', message='Sem acesso a este documento.'), 403


@bp.route('/document_ai/templates')
@login_required
def document_ai_templates_page():
    if not _document_ai_has_access('consultar') or not _current_document_ai_any_permission('associate'):
        return render_template('error.html', message='Sem permissão para gerir templates documentais.'), 403
    return render_template('document_ai_templates.html', page_title='Modelos Documentais')


@bp.route('/document_ai/sources')
@login_required
def document_ai_sources_page():
    if not _document_ai_has_access('consultar') or not _document_ai_is_admin():
        return render_template('error.html', message='Sem permissão para gerir origens documentais.'), 403
    return render_template('document_ai_sources.html', page_title='Origens Documentais')


@bp.route('/api/document_ai/lookups', methods=['GET'])
@login_required
def api_document_ai_lookups():
    if not _document_ai_has_access('consultar'):
        return jsonify({'error': 'Sem permissão.'}), 403
    return jsonify(document_ai_lookups())


@bp.route('/api/document_ai/integration-access/users', methods=['GET'])
@login_required
def api_document_ai_integration_access_users():
    if not _document_ai_is_admin():
        return jsonify({'error': 'Apenas administradores podem gerir estes acessos.'}), 403
    try:
        return jsonify(list_document_integration_access_users(
            str(request.args.get('q') or ''),
            int(request.args.get('limit') or 30),
        ))
    except Exception as exc:
        current_app.logger.exception('Erro ao listar acessos de integração documental')
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/integration-access', methods=['PUT'])
@login_required
def api_document_ai_integration_access_save():
    if not _document_ai_is_admin():
        return jsonify({'error': 'Apenas administradores podem gerir estes acessos.'}), 403
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(save_document_integration_access(
            str(body.get('login') or ''),
            body.get('permissions') or {},
            _current_login(),
        ))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception('Erro ao guardar acessos de integração documental')
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/inbox', methods=['GET'])
@login_required
def api_document_ai_inbox():
    if not _document_ai_has_access('consultar'):
        return jsonify({'error': 'Sem permissão.'}), 403
    inbox_views = _allowed_current_inbox_views()
    if not inbox_views:
        return jsonify({'error': 'Sem acesso ao Inbox.'}), 403
    requested_view = str(request.args.get('view') or inbox_views[0]['value']).strip().lower()
    if not _current_inbox_view_is_allowed(requested_view):
        return jsonify({'error': 'Sem acesso a esta vista do Inbox.'}), 403
    filters = {
        'view': requested_view,
        'feid': request.args.get('feid', ''),
        'status': request.args.get('status', ''),
        'doc_type': request.args.get('doc_type', ''),
        'supplier': request.args.get('supplier', ''),
        'search': request.args.get('search', ''),
        'date_from': request.args.get('date_from', ''),
        'date_to': request.args.get('date_to', ''),
        'archived': request.args.get('archived', ''),
    }
    filters.update(scope_filters_for(_current_login(), requested_view))
    payload = list_documents(filters)
    payload['permissions'] = document_ai_permission_profile(_current_login(), requested_view)['permissions']
    return jsonify(payload)


@bp.route('/api/document_ai/access-configuration', methods=['GET'])
@login_required
def api_document_ai_access_configuration():
    if not _document_ai_is_admin():
        return jsonify({'error': 'Sem permissão para administrar acessos Document AI.'}), 403
    return jsonify(list_access_configuration(request.args.get('search', '')))


@bp.route('/api/document_ai/access-configuration', methods=['PUT'])
@login_required
def api_document_ai_access_configuration_save():
    if not _document_ai_is_admin():
        return jsonify({'error': 'Sem permissão para administrar acessos Document AI.'}), 403
    try:
        return jsonify(save_access_configuration(request.get_json(silent=True) or {}, _current_login()))
    except (ValueError, PermissionError) as exc:
        return jsonify({'error': str(exc)}), 400 if isinstance(exc, ValueError) else 403
    except Exception as exc:
        current_app.logger.exception('Erro ao guardar acessos Document AI')
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/distribution-configuration', methods=['GET'])
@login_required
def api_document_ai_distribution_configuration():
    if not _document_ai_is_admin():
        return jsonify({'error': 'Sem permissão para administrar distribuições Document AI.'}), 403
    return jsonify(list_distribution_configuration())


@bp.route('/api/document_ai/required-info', methods=['GET'])
@login_required
def api_document_ai_required_info():
    if not _document_ai_is_admin():
        return jsonify({'error': 'Sem permissão para administrar informações obrigatórias.'}), 403
    return jsonify(list_required_info_configuration())


@bp.route('/api/document_ai/required-info', methods=['POST', 'PUT'])
@login_required
def api_document_ai_required_info_save():
    if not _document_ai_is_admin():
        return jsonify({'error': 'Sem permissão para administrar informações obrigatórias.'}), 403
    try:
        return jsonify(save_required_info_rule(request.get_json(silent=True) or {}, _current_login()))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception('Erro ao guardar informação obrigatória Document AI')
        db.session.rollback()
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/required-info/<rule_id>', methods=['DELETE'])
@login_required
def api_document_ai_required_info_delete(rule_id: str):
    if not _document_ai_is_admin():
        return jsonify({'error': 'Sem permissão para administrar informações obrigatórias.'}), 403
    try:
        return jsonify(delete_required_info_rule(rule_id, _current_login()))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception('Erro ao eliminar informação obrigatória Document AI')
        db.session.rollback()
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/distribution-configuration', methods=['POST', 'PUT'])
@login_required
def api_document_ai_distribution_configuration_save():
    if not _document_ai_is_admin():
        return jsonify({'error': 'Sem permissão para administrar distribuições Document AI.'}), 403
    try:
        return jsonify(save_distribution_rule(request.get_json(silent=True) or {}, _current_login()))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception('Erro ao guardar distribuição Document AI')
        db.session.rollback()
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/distribution-configuration/impact', methods=['POST'])
@login_required
def api_document_ai_distribution_configuration_impact():
    if not _document_ai_is_admin():
        return jsonify({'error': 'Sem permissão para administrar distribuições Document AI.'}), 403
    try:
        return jsonify(distribution_impact(request.get_json(silent=True) or {}))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception('Erro ao calcular impacto da distribuição Document AI')
        db.session.rollback()
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/distribution-configuration/<rule_id>', methods=['DELETE'])
@login_required
def api_document_ai_distribution_configuration_delete(rule_id: str):
    if not _document_ai_is_admin():
        return jsonify({'error': 'Sem permissão para administrar distribuições Document AI.'}), 403
    try:
        return jsonify(delete_distribution_rule(rule_id, _current_login()))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception('Erro ao eliminar distribuição Document AI')
        db.session.rollback()
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/extract', methods=['POST'])
@login_required
def api_document_ai_extract():
    if not _document_ai_has_access('consultar'):
        return jsonify({'error': 'Sem permissão para extrair documentos.'}), 403

    requested_view = str(request.form.get('view') or '').strip().lower()
    if not _current_document_ai_permission(requested_view, 'ai'):
        return jsonify({'error': 'Sem permissão para usar iA nesta visualização.'}), 403
    uploaded_file = request.files.get('file')
    if not uploaded_file or not str(uploaded_file.filename or '').strip():
        return jsonify({'error': 'Seleciona um ficheiro PDF.'}), 400

    file_name = str(uploaded_file.filename or '').strip()
    if not file_name.lower().endswith('.pdf'):
        return jsonify({'error': 'Este ecrã aceita apenas ficheiros PDF.'}), 400

    max_file_size = 50 * 1024 * 1024
    file_bytes = uploaded_file.stream.read(max_file_size + 1)
    if not file_bytes:
        return jsonify({'error': 'O ficheiro está vazio.'}), 400
    if len(file_bytes) > max_file_size:
        return jsonify({'error': 'O PDF excede o limite de 50 MB.'}), 413

    try:
        requested_document_id = str(request.form.get('document_id') or '').strip()
        existing_document_id = requested_document_id or find_llm_inbox_document(file_bytes)
        document_id = existing_document_id
        if document_id and not _current_document_access(document_id, requested_view, 'ai'):
            return jsonify({'error': 'Sem acesso a este documento.'}), 403
        inbox = {
            'id': document_id,
            'created': False,
            'duplicate': bool(document_id and not requested_document_id),
        }
        force_read = str(request.form.get('force') or '').strip().lower() in {'1', 'true', 'yes'}
        if force_read and document_id:
            reset_llm_extraction(document_id, _current_login())
        cached = None if force_read or not document_id else get_cached_llm_extraction(document_id)
        if cached:
            is_mail = str((cached.get('document') or {}).get('document_type') or '').strip().lower() == 'mail'
            if is_mail and not requested_document_id:
                cached['document_id'] = ''
                cached['not_saved_to_inbox'] = True
            cached['inbox_created'] = bool(inbox.get('created'))
            cached['duplicate'] = bool(inbox.get('duplicate'))
            return jsonify(cached)

        payload = extract_document_full_visual({
            'file_name': file_name,
            'mime_type': 'application/pdf',
            'file_bytes': file_bytes,
        })
        if not payload.get('ok'):
            status_code = 503 if not payload.get('available', True) else 502
            return jsonify({'error': payload.get('message') or 'Não foi possível extrair o documento.'}), status_code
        reconciled = reconcile_extracted_document(payload.get('document') or {})
        payload['document'] = reconciled.get('document') or payload.get('document') or {}
        payload['matching'] = reconciled.get('matching') or {}
        is_mail = str(payload['document'].get('document_type') or '').strip().lower() == 'mail'
        if is_mail and not requested_document_id:
            payload['document_id'] = ''
            payload['cached'] = False
            payload['inbox_created'] = False
            payload['duplicate'] = bool(inbox.get('duplicate'))
            payload['not_saved_to_inbox'] = True
            return jsonify(payload)

        if not document_id:
            if not _document_ai_has_access('inserir'):
                return jsonify({'error': 'Sem permissão para adicionar o documento ao inbox.'}), 403
            inbox = ensure_llm_inbox_document(file_name, file_bytes, _current_login())
            document_id = str(inbox.get('id') or '').strip()
        save_llm_extraction(document_id, payload, _current_login())
        payload['document_id'] = document_id
        payload['cached'] = False
        payload['inbox_created'] = bool(inbox.get('created'))
        payload['duplicate'] = bool(inbox.get('duplicate'))
        return jsonify(payload)
    except Exception as exc:
        current_app.logger.exception('Erro na leitura integral de documento com LLM')
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/extract/split', methods=['POST'])
@login_required
def api_document_ai_extract_split():
    requested_view = _requested_document_ai_view()
    if not _current_document_ai_permission(requested_view, 'analyze'):
        return jsonify({'error': 'Sem permissão para analisar nesta visualização.'}), 403
    if not _document_ai_has_access('inserir'):
        return jsonify({'error': 'Sem permissão para criar documentos no inbox.'}), 403
    uploaded_file = request.files.get('file')
    if not uploaded_file or not str(uploaded_file.filename or '').strip():
        return jsonify({'error': 'PDF em falta.'}), 400
    if not str(uploaded_file.filename or '').lower().endswith('.pdf'):
        return jsonify({'error': 'A separação aceita apenas ficheiros PDF.'}), 400
    max_file_size = 50 * 1024 * 1024
    file_bytes = uploaded_file.stream.read(max_file_size + 1)
    if len(file_bytes) > max_file_size:
        return jsonify({'error': 'O PDF excede o limite de 50 MB.'}), 413
    try:
        document_batch = json.loads(request.form.get('document_batch') or '{}')
        document_data = json.loads(request.form.get('document_data') or '{}')
    except Exception:
        return jsonify({'error': 'Os dados de separação não são válidos.'}), 400
    try:
        payload = split_extracted_pdf_into_inbox(
            file_bytes=file_bytes,
            file_name=str(uploaded_file.filename or '').strip(),
            document_batch=document_batch,
            document_data=document_data,
            created_by=_current_login(),
            source_document_id=request.form.get('source_document_id', ''),
        )
        return jsonify(payload), 201
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception('Erro ao separar PDF e criar grupo no inbox')
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/origins/search', methods=['POST'])
@login_required
def api_document_ai_origins_search():
    requested_view = _requested_document_ai_view()
    if not _current_document_ai_permission(requested_view, 'associate'):
        return jsonify({'error': 'Sem permissão para associar nesta visualização.'}), 403
    if not _document_ai_has_access('consultar'):
        return jsonify({'error': 'Sem permissão.'}), 403
    body = request.get_json(silent=True) or {}
    try:
        payload = search_phc_document_origins(body.get('document') or {})
        document_id = str(body.get('document_id') or '').strip()
        payload['selected_origins'] = get_document_phc_origins(document_id) if document_id else []
        payload['selected_origin'] = payload['selected_origins'][0] if payload['selected_origins'] else None
        return jsonify(payload)
    except ValueError as exc:
        return jsonify({'available': False, 'message': str(exc), 'stages': []}), 200
    except Exception as exc:
        current_app.logger.exception('Erro ao pesquisar origens PHC do documento')
        return jsonify({'available': False, 'error': str(exc), 'stages': []}), 500


@bp.route('/api/document_ai/documents/<docinstamp>/origins/<originstamp>', methods=['GET'])
@login_required
def api_document_ai_origin_detail(docinstamp: str, originstamp: str):
    if not _document_ai_has_access('consultar'):
        return jsonify({'error': 'Sem permissão.'}), 403
    requested_view = _requested_document_ai_view()
    if not _current_document_access(docinstamp, requested_view, 'analyze'):
        return jsonify({'error': 'Sem acesso a este documento.'}), 403
    try:
        return jsonify(get_phc_document_origin_detail(docinstamp, originstamp))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception('Erro ao consultar detalhe da origem PHC')
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/projects/search', methods=['POST'])
@login_required
def api_document_ai_projects_search():
    requested_view = _requested_document_ai_view()
    if not _current_document_ai_permission(requested_view, 'associate'):
        return jsonify({'error': 'Sem permissão para associar nesta visualização.'}), 403
    if not _document_ai_has_access('consultar'):
        return jsonify({'error': 'Sem permissão.'}), 403
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(search_phc_projects(
            body.get('customer') or {},
            str(body.get('query') or ''),
            int(body.get('limit') or 20),
        ))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception('Erro ao pesquisar obras PHC')
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/articles/search', methods=['POST'])
@login_required
def api_document_ai_articles_search():
    requested_view = _requested_document_ai_view()
    if not _current_document_ai_permission(requested_view, 'associate'):
        return jsonify({'error': 'Sem permissão para associar nesta visualização.'}), 403
    if not _document_ai_has_access('consultar'):
        return jsonify({'error': 'Sem permissão.'}), 403
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(search_phc_articles(
            body.get('customer') or {},
            str(body.get('query') or ''),
            int(body.get('limit') or 20),
        ))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception('Erro ao pesquisar artigos PHC')
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/vehicles/search', methods=['POST'])
@login_required
def api_document_ai_vehicles_search():
    requested_view = _requested_document_ai_view()
    if not _current_document_ai_permission(requested_view, 'associate'):
        return jsonify({'error': 'Sem permissão para associar nesta visualização.'}), 403
    if not _document_ai_has_access('consultar'):
        return jsonify({'error': 'Sem permissão.'}), 403
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(search_phc_vehicles(
            body.get('customer') or {},
            str(body.get('query') or ''),
            int(body.get('limit') or 20),
        ))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception('Erro ao pesquisar viaturas PHC')
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/correspondence/next-reference', methods=['POST'])
@login_required
def api_document_ai_correspondence_next_reference():
    if not _document_ai_has_access('consultar'):
        return jsonify({'error': 'Sem permissão.'}), 403
    requested_view = _requested_document_ai_view()
    if not _current_document_ai_permission(requested_view, 'associate'):
        return jsonify({'error': 'Sem permissão para associar nesta visualização.'}), 403
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(get_next_phc_correspondence_reference(
            body.get('customer') or {},
            body.get('year'),
        ))
    except ValueError as exc:
        return jsonify({'available': False, 'error': str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception('Erro ao consultar a próxima referência de correspondência no PHC')
        return jsonify({'available': False, 'error': str(exc)}), 500


@bp.route('/api/document_ai/correspondence/submit', methods=['POST'])
@login_required
def api_document_ai_correspondence_submit():
    requested_view = _requested_document_ai_view()
    if not _current_document_ai_permission(requested_view, 'validate'):
        return jsonify({'error': 'Sem permissão para validar nesta visualização.'}), 403
    if not _document_ai_has_integration_access('correspondence'):
        return jsonify({'error': 'Não tens acesso para integrar correspondência no PHC.'}), 403
    uploaded_file = request.files.get('file')
    if not uploaded_file or not str(uploaded_file.filename or '').strip():
        return jsonify({'error': 'O PDF original é obrigatório.'}), 400
    if not str(uploaded_file.filename or '').lower().endswith('.pdf'):
        return jsonify({'error': 'A correspondência deve ser submetida em PDF.'}), 400
    max_file_size = 50 * 1024 * 1024
    file_bytes = uploaded_file.stream.read(max_file_size + 1)
    if not file_bytes:
        return jsonify({'error': 'O PDF está vazio.'}), 400
    if len(file_bytes) > max_file_size:
        return jsonify({'error': 'O PDF excede o limite de 50 MB.'}), 413
    try:
        document_data = json.loads(request.form.get('document_data') or '{}')
    except Exception:
        return jsonify({'error': 'Os dados da correspondência não são válidos.'}), 400
    document_id = str(request.form.get('document_id') or '').strip()
    if document_id and not _current_document_access(document_id, requested_view, 'validate'):
        return jsonify({'error': 'Sem acesso a este documento.'}), 403
    try:
        return jsonify(submit_correspondence_to_phc(
            document_data,
            file_bytes,
            str(uploaded_file.filename or '').strip(),
            _current_login(),
        )), 201
    except (ValueError, FileExistsError) as exc:
        return jsonify({'error': str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({'error': str(exc)}), 503
    except Exception as exc:
        current_app.logger.exception('Erro ao submeter correspondência no PHC')
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/provisional-invoice/submit', methods=['POST'])
@login_required
def api_document_ai_provisional_invoice_submit():
    requested_view = _requested_document_ai_view()
    if not _current_document_ai_permission(requested_view, 'validate'):
        return jsonify({'error': 'Sem permissão para validar nesta visualização.'}), 403
    if not _document_ai_has_integration_access('provisional_invoice'):
        return jsonify({'error': 'Não tens acesso para integrar Facture Provisoire no PHC.'}), 403
    uploaded_file = request.files.get('file')
    if not uploaded_file or not str(uploaded_file.filename or '').strip():
        return jsonify({'error': 'O PDF original é obrigatório.'}), 400
    if not str(uploaded_file.filename or '').lower().endswith('.pdf'):
        return jsonify({'error': 'A Facture Provisoire deve ser submetida em PDF.'}), 400
    max_file_size = 50 * 1024 * 1024
    file_bytes = uploaded_file.stream.read(max_file_size + 1)
    if not file_bytes:
        return jsonify({'error': 'O PDF está vazio.'}), 400
    if len(file_bytes) > max_file_size:
        return jsonify({'error': 'O PDF excede o limite de 50 MB.'}), 413
    try:
        document_data = json.loads(request.form.get('document_data') or '{}')
    except Exception:
        return jsonify({'error': 'Os dados da Facture Provisoire não são válidos.'}), 400
    document_id = str(request.form.get('document_id') or '').strip()
    if not document_id:
        return jsonify({'error': 'O documento tem de estar guardado no inbox antes da validação.'}), 400
    if not _current_document_access(document_id, requested_view, 'validate'):
        return jsonify({'error': 'Sem acesso a este documento.'}), 403
    try:
        require_document_control_ok(document_id)
        result = submit_provisional_invoice_to_phc(
            document_data,
            file_bytes,
            str(uploaded_file.filename or '').strip(),
            _current_login(),
        )
        mark_document_as_provisional_invoice(
            document_id,
            result,
            _current_login(),
            hashlib.sha256(file_bytes).hexdigest(),
        )
        return jsonify(result), 201
    except (ValueError, FileExistsError) as exc:
        mark_document_validation_error(document_id, str(exc), _current_login())
        return jsonify({'error': str(exc)}), 400
    except RuntimeError as exc:
        mark_document_validation_error(document_id, str(exc), _current_login())
        return jsonify({'error': str(exc)}), 503
    except Exception as exc:
        try:
            mark_document_validation_error(document_id, str(exc), _current_login())
        except Exception:
            current_app.logger.warning('Falhou registo do erro de validação Document AI.', exc_info=True)
        current_app.logger.exception('Erro ao submeter Facture Provisoire no PHC')
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/documents/<docinstamp>/control-ok', methods=['POST'])
@login_required
def api_document_ai_document_control_ok(docinstamp: str):
    requested_view = _requested_document_ai_view()
    if not _current_document_access(docinstamp, requested_view, 'analyze'):
        return jsonify({'error': 'Sem acesso a este documento.'}), 403
    if not _document_ai_has_access('editar'):
        return jsonify({'error': 'Sem permissão para concluir o controlo.'}), 403
    if not _document_ai_has_integration_access('provisional_invoice'):
        return jsonify({'error': 'Sem permissão para validar Facture Provisoire.'}), 403
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(mark_document_control_ok(docinstamp, _current_login(), body.get('document') or {}))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception('Erro ao concluir Controlo OK')
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/sources', methods=['GET'])
@login_required
def api_document_ai_sources():
    if not _document_ai_has_access('consultar') or not _document_ai_is_admin():
        return jsonify({'error': 'Sem permissão.'}), 403
    try:
        return jsonify(list_document_sources())
    except Exception as exc:
        current_app.logger.exception('Erro ao carregar origens documentais')
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/sources/<source_id>', methods=['GET'])
@login_required
def api_document_ai_source_detail(source_id: str):
    if not _document_ai_has_access('consultar') or not _document_ai_is_admin():
        return jsonify({'error': 'Sem permissão.'}), 403
    try:
        return jsonify(get_document_source(source_id))
    except Exception as exc:
        current_app.logger.exception('Erro ao carregar origem documental')
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/sources', methods=['POST'])
@login_required
def api_document_ai_source_create():
    if not _document_ai_has_access('inserir') or not _document_ai_is_admin():
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
    if not _document_ai_has_access('editar') or not _document_ai_is_admin():
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
    if not _document_ai_has_access('eliminar') or not _document_ai_is_admin():
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
    requested_view = str(request.form.get('view') or '').strip().lower()
    if not _current_document_ai_permission(requested_view, 'create'):
        return jsonify({'error': 'Sem permissão para criar documentos nesta visualização.'}), 403
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
    requested_view = str(request.args.get('view') or '').strip().lower()
    if not requested_view:
        requested_view = _first_document_permission_view(docinstamp, 'analyze')
    if not _current_document_access(docinstamp, requested_view, 'analyze'):
        return jsonify({'error': 'Sem acesso a este documento.'}), 403
    try:
        return jsonify(get_document_detail(docinstamp))
    except Exception as exc:
        current_app.logger.exception('Erro ao carregar detalhe documental')
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/documents/<docinstamp>/group', methods=['GET'])
@login_required
def api_document_ai_document_group(docinstamp: str):
    if not _document_ai_has_access('consultar'):
        return jsonify({'error': 'Sem permissão.'}), 403
    requested_view = str(request.args.get('view') or '').strip().lower()
    if not _current_document_access(docinstamp, requested_view, 'analyze'):
        return jsonify({'error': 'Sem acesso a este documento.'}), 403
    try:
        return jsonify(get_document_group(docinstamp))
    except Exception as exc:
        current_app.logger.exception('Erro ao carregar grupo documental')
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/documents/<docinstamp>/origin', methods=['POST'])
@login_required
def api_document_ai_document_origin_link(docinstamp: str):
    if not _document_ai_has_access('editar'):
        return jsonify({'error': 'Sem permissão para ligar a origem.'}), 403
    requested_view = _requested_document_ai_view()
    if not _current_document_access(docinstamp, requested_view, 'associate'):
        return jsonify({'error': 'Sem permissão para associar este documento.'}), 403
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(save_document_phc_origin(
            docinstamp,
            body.get('origin') or {},
            body.get('document') or {},
            _current_login(),
        ))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception('Erro ao ligar origem PHC ao documento')
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/documents/<docinstamp>/origin', methods=['DELETE'])
@login_required
def api_document_ai_document_origin_unlink(docinstamp: str):
    if not _document_ai_has_access('editar'):
        return jsonify({'error': 'Sem permissão para desmarcar a origem.'}), 403
    requested_view = _requested_document_ai_view()
    if not _current_document_access(docinstamp, requested_view, 'associate'):
        return jsonify({'error': 'Sem permissão para associar este documento.'}), 403
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(clear_document_phc_origin(
            docinstamp,
            _current_login(),
            str(body.get('stamp') or ''),
        ))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception('Erro ao desmarcar origem PHC do documento')
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/documents/<docinstamp>/lines', methods=['PATCH'])
@login_required
def api_document_ai_document_lines_update(docinstamp: str):
    if not _document_ai_has_access('editar'):
        return jsonify({'error': 'Sem permissão para ajustar as linhas.'}), 403
    requested_view = _requested_document_ai_view()
    if not _current_document_access(docinstamp, requested_view, 'associate'):
        return jsonify({'error': 'Sem permissão para associar este documento.'}), 403
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(save_document_adjusted_lines(
            docinstamp,
            body.get('lines') or [],
            _current_login(),
        ))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception('Erro ao guardar repartição das linhas do documento')
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/documents/<docinstamp>', methods=['DELETE'])
@login_required
def api_document_ai_document_delete(docinstamp: str):
    if not _document_ai_has_access('eliminar'):
        return jsonify({'error': 'Sem permissão para eliminar documentos.'}), 403
    body = request.get_json(silent=True) or {}
    requested_view = str(body.get('view') or '').strip().lower()
    if requested_view not in {'home', 'management'} or not _current_inbox_view_is_allowed(requested_view):
        return jsonify({'error': 'Sem permissão para eliminar documentos nesta vista.'}), 403
    if not _current_document_ai_permission(requested_view, 'delete'):
        return jsonify({'error': 'Sem permissão para eliminar documentos nesta vista.'}), 403
    if not _current_document_access(docinstamp, requested_view, 'delete'):
        return jsonify({'error': 'Sem acesso a este documento.'}), 403
    if not document_belongs_to_inbox_view(docinstamp, requested_view):
        return jsonify({'error': 'O documento não pertence a esta vista do Inbox.'}), 403
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
    requested_view = _requested_document_ai_view()
    if not _current_document_access(docinstamp, requested_view, 'analyze'):
        return jsonify({'error': 'Sem acesso a este documento.'}), 403
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
    requested_view = _requested_document_ai_view()
    if not _current_document_access(docinstamp, requested_view, 'analyze'):
        return jsonify({'error': 'Sem acesso a este documento.'}), 403
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
    requested_view = _requested_document_ai_view()
    if not _current_document_access(docinstamp, requested_view, 'ai'):
        return jsonify({'error': 'Sem permissão para usar iA neste documento.'}), 403
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
    requested_view = _requested_document_ai_view()
    if not _current_document_access(docinstamp, requested_view, 'ai'):
        return jsonify({'error': 'Sem permissão para usar iA neste documento.'}), 403
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
    requested_view = _requested_document_ai_view()
    if not _current_document_access(docinstamp, requested_view, 'analyze'):
        return jsonify({'error': 'Sem permissão para analisar este documento.'}), 403
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


@bp.route('/api/document_ai/documents/<docinstamp>/workflow/validate', methods=['POST'])
@login_required
def api_document_ai_document_workflow_validate(docinstamp: str):
    if not _document_ai_has_access('editar'):
        return jsonify({'error': 'Sem permissão para validar.'}), 403
    body = request.get_json(silent=True) or {}
    requested_view = _requested_document_ai_view()
    if not _current_document_access(docinstamp, requested_view, 'validate'):
        return jsonify({'error': 'Sem permissão para validar este documento.'}), 403
    view = str(body.get('view') or '').strip().lower()
    if not _current_inbox_view_is_allowed(view):
        return jsonify({'error': 'Sem acesso a esta etapa documental.'}), 403
    try:
        return jsonify(validate_document_inbox_stage(
            docinstamp,
            view,
            _current_login(),
            body.get('document') or None,
        ))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception('Erro ao validar etapa documental')
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/documents/<docinstamp>/workflow/preflight', methods=['POST'])
@login_required
def api_document_ai_document_workflow_preflight(docinstamp: str):
    if not _document_ai_has_access('editar'):
        return jsonify({'error': 'Sem permissão para validar.'}), 403
    body = request.get_json(silent=True) or {}
    requested_view = _requested_document_ai_view()
    if not _current_document_access(docinstamp, requested_view, 'validate'):
        return jsonify({'error': 'Sem permissão para validar este documento.'}), 403
    view = str(body.get('view') or '').strip().lower()
    if not _current_inbox_view_is_allowed(view):
        return jsonify({'error': 'Sem acesso a esta etapa documental.'}), 403
    try:
        return jsonify(preflight_document_inbox_stage(
            docinstamp,
            view,
            body.get('document') or None,
            requested_by=_current_login(),
            allow_duplicate_override=bool(body.get('confirm_duplicate')),
        ))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception('Erro ao pré-validar etapa documental')
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
    requested_view = _requested_document_ai_view()
    if not _current_document_access(docinstamp, requested_view, 'associate'):
        return jsonify({'error': 'Sem permissão para associar este documento.'}), 403
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
    if not _document_ai_has_access('consultar') or not _current_document_ai_any_permission('associate'):
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
    if not _document_ai_has_access('consultar') or not _current_document_ai_any_permission('associate'):
        return jsonify({'error': 'Sem permissão.'}), 403
    try:
        return jsonify(get_template_detail(template_id))
    except Exception as exc:
        current_app.logger.exception('Erro ao carregar template documental')
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/templates', methods=['POST'])
@login_required
def api_document_ai_template_create():
    if not _document_ai_has_access('editar') or not _current_document_ai_any_permission('associate'):
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
    if not _document_ai_has_access('editar') or not _current_document_ai_any_permission('associate'):
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
    if not _document_ai_has_access('editar') or not _current_document_ai_any_permission('associate'):
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
    if not _document_ai_has_access('consultar') or not _current_document_ai_any_permission('associate'):
        return jsonify({'error': 'Sem permissão.'}), 403
    body = request.get_json(silent=True) or {}
    document_id = str(body.get('document_id') or '').strip()
    if document_id and not _first_document_permission_view(document_id, 'analyze'):
        return jsonify({'error': 'Sem acesso a este documento.'}), 403
    try:
        return jsonify(test_template(template_id, document_id))
    except Exception as exc:
        current_app.logger.exception('Erro a testar template documental')
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/suggest', methods=['POST'])
@login_required
def api_document_ai_suggest():
    if not _document_ai_has_access('consultar'):
        return jsonify({'error': 'Sem permissão.'}), 403
    requested_view = _requested_document_ai_view()
    if not (
        _current_document_ai_permission(requested_view, 'ai')
        if requested_view else _current_document_ai_any_permission('ai')
    ):
        return jsonify({'error': 'Sem permissão para usar iA nesta visualização.'}), 403
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
    requested_view = _requested_document_ai_view()
    if not _current_document_ai_permission(requested_view, 'associate') or not _current_feid_is_allowed(requested_view, feid):
        return jsonify({'error': 'Sem acesso a esta entidade.'}), 403
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
        requested_view = _requested_document_ai_view()
        if not _current_document_ai_permission(requested_view, 'associate'):
            return jsonify({'error': 'Sem permissão para associar nesta visualização.'}), 403
        payload = resolve_fe_entity(term, mode)
        if payload and not _current_feid_is_allowed(requested_view, int(payload.get('feid') or 0)):
            return jsonify({})
        return jsonify(payload)
    except Exception as exc:
        current_app.logger.exception('Erro ao resolver entidade FE documental')
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/entities/search', methods=['GET'])
@login_required
def api_document_ai_entities_search():
    if not _document_ai_has_access('consultar'):
        return jsonify({'error': 'Sem permissão.'}), 403
    term = str(request.args.get('q', '') or '').strip()
    limit = min(max(int(request.args.get('limit', 20) or 20), 1), 50)
    try:
        requested_view = _requested_document_ai_view()
        profile = document_ai_permission_profile(_current_login(), requested_view)
        if not profile['allowed'] or not profile['permissions'].get('associate'):
            return jsonify({'error': 'Sem permissão para associar nesta visualização.'}), 403
        items = search_fe_entities(term, limit=limit)
        if not profile['all_entities']:
            allowed = set(profile['entity_ids'])
            items = [item for item in items if int(item.get('feid') or 0) in allowed]
        return jsonify(items)
    except Exception as exc:
        current_app.logger.exception('Erro ao pesquisar entidades FE documentais')
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/customers/search', methods=['GET'])
@login_required
def api_document_ai_customers_search():
    if not _document_ai_has_access('consultar'):
        return jsonify({'error': 'Sem permissão.'}), 403
    term = str(request.args.get('q', '') or '').strip()
    feid = int(request.args.get('feid', 0) or 0)
    limit = min(max(int(request.args.get('limit', 12) or 12), 1), 20)
    if len(term) < 2 or not feid:
        return jsonify([])
    requested_view = _requested_document_ai_view()
    if not _current_document_ai_permission(requested_view, 'associate') or not _current_feid_is_allowed(requested_view, feid):
        return jsonify({'error': 'Sem acesso a esta entidade.'}), 403
    try:
        return jsonify(search_customers(term, feid=feid, limit=limit))
    except Exception as exc:
        current_app.logger.exception('Erro ao pesquisar clientes Document AI')
        return jsonify({'error': str(exc)}), 500


@bp.route('/api/document_ai/external-parties/search', methods=['GET'])
@login_required
def api_document_ai_external_parties_search():
    if not _document_ai_has_access('consultar'):
        return jsonify({'error': 'Sem permissão.'}), 403
    term = str(request.args.get('q', '') or '').strip()
    feid = int(request.args.get('feid', 0) or 0)
    limit = min(max(int(request.args.get('limit', 12) or 12), 1), 20)
    if len(term) < 2 or not feid:
        return jsonify([])
    requested_view = _requested_document_ai_view()
    if not _current_document_ai_permission(requested_view, 'associate') or not _current_feid_is_allowed(requested_view, feid):
        return jsonify({'error': 'Sem acesso a esta entidade.'}), 403
    try:
        return jsonify(search_external_parties(term, feid=feid, limit=limit))
    except Exception as exc:
        current_app.logger.exception('Erro ao pesquisar clientes e fornecedores Document AI')
        return jsonify({'error': str(exc)}), 500
