from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required

from models import db
from services.laundry_support_service import (
    LaundrySupportError,
    ensure_laundry_support_menu,
    laundry_plan,
    parse_period,
)


bp = Blueprint('laundry_support', __name__)


@bp.route('/apoio-lavandaria')
@login_required
def laundry_support_page():
    try:
        ensure_laundry_support_menu()
    except Exception:
        db.session.rollback()
    return render_template('laundry_support.html', page_title='Lavandaria')


@bp.route('/api/apoio-lavandaria')
@login_required
def api_laundry_support():
    try:
        data_ini, data_fim = parse_period(request.args.get('data_ini'), request.args.get('data_fim'))
        return jsonify({'ok': True, **laundry_plan(data_ini, data_fim)})
    except LaundrySupportError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(exc)}), 500
