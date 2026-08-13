from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required

from models import db
from services.predefined_messages_service import (
    PredefinedMessagesError,
    delete_message,
    ensure_predefined_messages_schema,
    ensure_predefined_messages_menu,
    get_message,
    list_messages,
    render_message,
    save_message,
    search_reservations,
)


bp = Blueprint('predefined_messages', __name__)


@bp.route('/mensagens-predefinidas')
@login_required
def predefined_messages_page():
    try:
        ensure_predefined_messages_schema()
        ensure_predefined_messages_menu()
    except Exception:
        db.session.rollback()
    return render_template('predefined_messages.html', page_title='Mensagens pré-definidas')


@bp.route('/api/mensagens-predefinidas')
@login_required
def api_predefined_messages_list():
    try:
        ensure_predefined_messages_schema()
        return jsonify({'ok': True, 'items': list_messages()})
    except Exception as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(exc)}), 500


@bp.route('/api/mensagens-predefinidas', methods=['POST'])
@login_required
def api_predefined_messages_create():
    try:
        ensure_predefined_messages_schema()
        return jsonify({'ok': True, 'item': save_message(None, request.get_json(silent=True) or {})})
    except PredefinedMessagesError as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(exc)}), 500


@bp.route('/api/mensagens-predefinidas/<message_id>', methods=['PUT'])
@login_required
def api_predefined_messages_update(message_id):
    try:
        ensure_predefined_messages_schema()
        return jsonify({'ok': True, 'item': save_message(message_id, request.get_json(silent=True) or {})})
    except PredefinedMessagesError as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(exc)}), 500


@bp.route('/api/mensagens-predefinidas/<message_id>', methods=['DELETE'])
@login_required
def api_predefined_messages_delete(message_id):
    try:
        ensure_predefined_messages_schema()
        delete_message(message_id)
        return jsonify({'ok': True})
    except PredefinedMessagesError as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(exc)}), 500


@bp.route('/api/mensagens-predefinidas/reservas')
@login_required
def api_predefined_messages_reservations():
    try:
        return jsonify({'ok': True, 'items': search_reservations(request.args.get('q', ''))})
    except PredefinedMessagesError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(exc)}), 500


@bp.route('/api/mensagens-predefinidas/<message_id>/render', methods=['POST'])
@login_required
def api_predefined_messages_render(message_id):
    try:
        ensure_predefined_messages_schema()
        message = get_message(message_id, include_inactive=False)
        if not message:
            return jsonify({'ok': False, 'error': 'Mensagem não encontrada.'}), 404
        payload = request.get_json(silent=True) or {}
        return jsonify({'ok': True, 'message': render_message(message['mensagem'], payload.get('reserva') or {})})
    except Exception as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(exc)}), 500
