import os

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from services.email_service import (
    EmailServiceError,
    duplicate_email,
    ensure_email_tables,
    get_email_detail,
    get_email_profile,
    list_profiles,
    list_queue,
    process_email_queue,
    requeue_email,
    save_profile,
    send_email_now,
    test_email_profile,
    update_queue_state,
)


bp = Blueprint('email_service', __name__)


def _is_admin() -> bool:
    return bool(getattr(current_user, 'ADMIN', False) or getattr(current_user, 'DEV', False))


def _require_admin():
    if not _is_admin():
        return render_template('error.html', message='Sem permissão para gerir o serviço de email.'), 403
    return None


def _login() -> str:
    return str(getattr(current_user, 'LOGIN', '') or '').strip()


def _bool_form(name: str) -> bool:
    return str(request.form.get(name) or '').strip().lower() in {'1', 'true', 'on', 'yes', 'sim'}


def _profile_form_payload() -> dict:
    return {
        'NOME_PERFIL': request.form.get('nome_perfil'),
        'DESCRICAO': request.form.get('descricao'),
        'EMAIL_FROM': request.form.get('email_from'),
        'NOME_FROM': request.form.get('nome_from'),
        'SMTP_HOST': request.form.get('smtp_host'),
        'SMTP_PORT': request.form.get('smtp_port'),
        'SMTP_USER': request.form.get('smtp_user'),
        'SMTP_PASSWORD': request.form.get('smtp_password'),
        'USA_TLS': _bool_form('usa_tls'),
        'USA_SSL': _bool_form('usa_ssl'),
        'ATIVO': _bool_form('ativo'),
        'DEFAULT_PROFILE': _bool_form('default_profile'),
    }


@bp.route('/email/profiles')
@login_required
def email_profiles():
    denied = _require_admin()
    if denied:
        return denied
    ensure_email_tables()
    return render_template(
        'email_profiles.html',
        page_title='Perfis de Email',
        profiles=list_profiles(include_inactive=True),
        message=request.args.get('message', ''),
        error=request.args.get('error', ''),
    )


@bp.route('/email/profiles/new', methods=['GET', 'POST'])
@login_required
def email_profile_new():
    denied = _require_admin()
    if denied:
        return denied
    ensure_email_tables()
    if request.method == 'POST':
        try:
            profile_id = save_profile(_profile_form_payload())
            return redirect(url_for('email_service.email_profile_edit', profile_id=profile_id, message='Perfil criado.'))
        except Exception as exc:
            current_app.logger.exception('Erro ao criar perfil de email')
            return render_template('email_profile_form.html', profile=None, error=str(exc), page_title='Novo Perfil de Email')
    return render_template('email_profile_form.html', profile=None, error='', page_title='Novo Perfil de Email')


@bp.route('/email/profiles/<int:profile_id>/edit', methods=['GET', 'POST'])
@login_required
def email_profile_edit(profile_id):
    denied = _require_admin()
    if denied:
        return denied
    ensure_email_tables()
    profile = get_email_profile(profile_id=profile_id)
    if not profile:
        return render_template('error.html', message='Perfil não encontrado.'), 404
    if request.method == 'POST':
        try:
            save_profile(_profile_form_payload(), profile_id=profile_id)
            return redirect(url_for('email_service.email_profile_edit', profile_id=profile_id, message='Perfil gravado.'))
        except Exception as exc:
            current_app.logger.exception('Erro ao gravar perfil de email')
            profile.update(_profile_form_payload())
            return render_template('email_profile_form.html', profile=profile, error=str(exc), page_title='Editar Perfil de Email')
    return render_template(
        'email_profile_form.html',
        profile=profile,
        error=request.args.get('error', ''),
        message=request.args.get('message', ''),
        page_title='Editar Perfil de Email',
    )


@bp.post('/email/profiles/<int:profile_id>/test')
@login_required
def email_profile_test(profile_id):
    denied = _require_admin()
    if denied:
        return denied
    recipient = request.form.get('test_recipient') or ''
    try:
        result = test_email_profile(profile_id, recipient)
        if result.get('ok'):
            return redirect(url_for('email_service.email_profile_edit', profile_id=profile_id, message='Teste enviado.'))
        return redirect(url_for('email_service.email_profile_edit', profile_id=profile_id, error=f"Teste falhou: {result.get('error')}"))
    except Exception as exc:
        return redirect(url_for('email_service.email_profile_edit', profile_id=profile_id, error=str(exc)))


@bp.route('/email/test', methods=['GET', 'POST'])
@login_required
def email_test():
    denied = _require_admin()
    if denied:
        return denied
    ensure_email_tables()
    profiles = list_profiles(include_inactive=False)
    message = ''
    error = ''
    if request.method == 'POST':
        try:
            result = test_email_profile(int(request.form.get('profile_id') or 0), request.form.get('recipient') or '')
            message = 'Teste enviado.' if result.get('ok') else ''
            error = '' if result.get('ok') else result.get('error') or 'Erro no envio.'
        except Exception as exc:
            error = str(exc)
    return render_template('email_test.html', profiles=profiles, message=message, error=error, page_title='Teste de Email')


@bp.route('/email/queue')
@login_required
def email_queue():
    denied = _require_admin()
    if denied:
        return denied
    ensure_email_tables()
    filters = {
        'estado': request.args.get('estado', ''),
        'profile_id': request.args.get('profile_id', ''),
        'search': request.args.get('search', ''),
        'date_from': request.args.get('date_from', ''),
        'date_to': request.args.get('date_to', ''),
    }
    return render_template(
        'email_queue.html',
        page_title='Fila de Emails',
        emails=list_queue(filters),
        profiles=list_profiles(include_inactive=True),
        filters=filters,
        states=['', 'PENDENTE', 'A_ENVIAR', 'ENVIADO', 'ERRO', 'CANCELADO'],
        message=request.args.get('message', ''),
        error=request.args.get('error', ''),
    )


@bp.route('/email/queue/<int:email_id>')
@login_required
def email_queue_detail(email_id):
    denied = _require_admin()
    if denied:
        return denied
    detail = get_email_detail(email_id)
    if not detail:
        return render_template('error.html', message='Email não encontrado.'), 404
    return render_template(
        'email_queue_detail.html',
        page_title=f'Email #{email_id}',
        detail=detail,
        message=request.args.get('message', ''),
        error=request.args.get('error', ''),
    )


@bp.post('/email/queue/<int:email_id>/send-now')
@login_required
def email_queue_send_now(email_id):
    denied = _require_admin()
    if denied:
        return denied
    result = send_email_now(email_id)
    if result.get('ok'):
        return redirect(url_for('email_service.email_queue_detail', email_id=email_id, message='Email enviado.'))
    return redirect(url_for('email_service.email_queue_detail', email_id=email_id, error=result.get('error') or 'Erro no envio.'))


@bp.post('/email/queue/<int:email_id>/requeue')
@login_required
def email_queue_requeue(email_id):
    denied = _require_admin()
    if denied:
        return denied
    try:
        requeue_email(email_id)
        return redirect(url_for('email_service.email_queue_detail', email_id=email_id, message='Email reprocessado.'))
    except Exception as exc:
        return redirect(url_for('email_service.email_queue_detail', email_id=email_id, error=str(exc)))


@bp.post('/email/queue/<int:email_id>/cancel')
@login_required
def email_queue_cancel(email_id):
    denied = _require_admin()
    if denied:
        return denied
    try:
        update_queue_state(email_id, 'CANCELADO')
        return redirect(url_for('email_service.email_queue_detail', email_id=email_id, message='Email cancelado.'))
    except Exception as exc:
        return redirect(url_for('email_service.email_queue_detail', email_id=email_id, error=str(exc)))


@bp.post('/email/queue/<int:email_id>/duplicate')
@login_required
def email_queue_duplicate(email_id):
    denied = _require_admin()
    if denied:
        return denied
    try:
        new_id = duplicate_email(email_id, created_by=_login())
        return redirect(url_for('email_service.email_queue_detail', email_id=new_id, message='Email duplicado.'))
    except Exception as exc:
        return redirect(url_for('email_service.email_queue_detail', email_id=email_id, error=str(exc)))


@bp.post('/email/queue/process')
@login_required
def email_queue_process():
    denied = _require_admin()
    if denied:
        return denied
    result = process_email_queue(limit=int(request.form.get('limit') or 20))
    return redirect(url_for('email_service.email_queue', message=f"{result.get('processed', 0)} emails processados."))


@bp.post('/internal/email/process-queue')
def internal_email_process_queue():
    token = str(current_app.config.get('EMAIL_INTERNAL_TOKEN') or os.environ.get('EMAIL_INTERNAL_TOKEN') or '').strip()
    if token:
        received = str(request.headers.get('X-Internal-Token') or request.args.get('token') or '').strip()
        if received != token:
            return jsonify({'error': 'Unauthorized'}), 401
    elif not (current_user.is_authenticated and _is_admin()):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        return jsonify(process_email_queue(limit=int(request.args.get('limit') or request.form.get('limit') or 20)))
    except Exception as exc:
        current_app.logger.exception('Erro ao processar fila de emails')
        return jsonify({'error': str(exc)}), 500
