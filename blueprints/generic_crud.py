from flask import Blueprint, render_template, request, jsonify, abort, current_app
from flask_login import login_required, current_user
from sqlalchemy import MetaData, Table, select, text
from app import db
from models import Campo, Menu, Acessos

bp = Blueprint('generic', __name__, url_prefix='/generic')

# ACL helper
def has_permission(table_name: str, action: str) -> bool:
    # super-admin do sistema vê tudo
    if getattr(current_user, 'ADMIN', False):
        return True
    # busca ACL específica para este utilizador e tabela
    acesso = (
        Acessos.query
               .filter_by(utilizador=current_user.LOGIN, tabela=table_name)
               .first()
    )
    if not acesso:
        return False
    return getattr(acesso, action, False)

# Helper: reflect a table by name
def get_table(table_name):
    meta = MetaData()
    try:
        return Table(
            table_name,
            meta,
            schema='dbo',
            autoload_with=db.engine
        )
    except Exception as e:
        current_app.logger.error(f"Erro ao refletir tabela {table_name}: {e}")
        abort(404, f"Tabela {table_name} não encontrada")

# View: listagem dinâmica
@bp.route('/view/<table_name>/', defaults={'record_stamp': None})
@bp.route('/view/<table_name>/<record_stamp>')
@login_required
def view_table(table_name, record_stamp):
    menu_item = Menu.query.filter_by(tabela=table_name).first()
    menu_label = menu_item.nome if menu_item else table_name.capitalize()
    return render_template(
        'dynamic_list.html',
        table_name=table_name,
        record_stamp=record_stamp,
        menu_label=menu_label
    )

# View: formulário de edição/introdução
@bp.route('/form/<table_name>/', defaults={'record_stamp': None})
@bp.route('/form/<table_name>/<record_stamp>')
@login_required
def edit_table(table_name, record_stamp):
    menu_item = Menu.query.filter_by(tabela=table_name).first()
    menu_label = menu_item.nome if menu_item else table_name.capitalize()
    return render_template(
        'dynamic_form.html',
        table_name=table_name,
        record_stamp=record_stamp,
        menu_label=menu_label
    )

# API: DESCRIBE colunas
@bp.route('/api/<table_name>', methods=['GET'])
@login_required
def list_or_describe(table_name):
    # DESCRIBE
    if request.args.get('action') == 'describe':
        campos = (
            Campo.query
            .filter_by(tabela=table_name)
            .order_by(Campo.ordem)
            .all()
        )
        pk_name = f"{table_name.upper()}STAMP"
        cols = []
        for c in campos:
            cols.append({
                'name':        c.nmcampo,
                'descricao':   c.descricao,
                'tipo':        c.tipo,
                'lista':       bool(c.lista),
                'filtro':      bool(c.filtro),
                'admin':       bool(c.admin),
                'primary_key': (c.nmcampo == pk_name),
                'readonly':    bool(c.ronly),
                'combo':       c.combo
            })
        return jsonify(cols)

    # LISTAGEM de registros (sem action)
    # valida permissão de consulta
    if not has_permission(table_name, 'consultar'):
        abort(403, 'Sem permissão para consultar')

    table = get_table(table_name)
    stmt = select(table)
    for key, value in request.args.items():
        if key == 'action':
            continue
        if hasattr(table.c, key):
            stmt = stmt.where(getattr(table.c, key) == value)
    try:
        rows = db.session.execute(stmt).fetchall()
        records = [dict(r._mapping) for r in rows]
        return jsonify(records)
    except Exception as e:
        current_app.logger.exception(f"Falha ao listar {table_name}")
        return jsonify({'error': str(e)}), 500

# API: opções para COMBO
@bp.route('/api/options', methods=['GET'])
@login_required
def combo_options():
    q = request.args.get('query')
    try:
        rows = db.session.execute(text(q)).fetchall()
    except Exception as e:
        current_app.logger.exception("Erro em combo_options")
        return jsonify({'error': str(e)}), 500

    results = []
    for r in rows:
        if len(r) == 1:
            results.append({'value': r[0], 'text': str(r[0])})
        else:
            results.append({'value': r[0], 'text': r[1]})
    return jsonify(results)

# API: Single record retrieval
@bp.route('/api/<table_name>/<record_stamp>', methods=['GET'])
@login_required
def get_record(table_name, record_stamp):
    # valida permissão de consulta
    if not has_permission(table_name, 'consultar'):
        abort(403, 'Sem permissão para consultar')

    table = get_table(table_name)
    pk = getattr(table.c, f"{table_name.upper()}STAMP")
    stmt = select(table).where(pk == record_stamp)
    row = db.session.execute(stmt).fetchone()
    if not row:
        abort(404, f"Registro não encontrado: {record_stamp}")
    return jsonify(dict(row._mapping))

# API: Create new record
@bp.route('/api/<table_name>', methods=['POST'])
@login_required
def create_record(table_name):
    # valida permissão de inserção
    if not has_permission(table_name, 'inserir'):
        abort(403, 'Sem permissão para inserir')

    table = get_table(table_name)
    data = request.get_json() or {}
    # permite usar DEFAULT do DB para PK vazio
    pk_name = f"{table_name.upper()}STAMP"
    if pk_name in data and not data[pk_name]:
        data.pop(pk_name, None)
    try:
        ins = table.insert().values(**data)
        db.session.execute(ins)
        db.session.commit()
        return jsonify({'success': True}), 201
    except Exception as e:
        current_app.logger.exception(f"Falha ao criar {table_name}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# API: Update record
@bp.route('/api/<table_name>/<record_stamp>', methods=['PUT'])
@login_required
def update_record(table_name, record_stamp):
    # valida permissão de edição
    if not has_permission(table_name, 'editar'):
        abort(403, 'Sem permissão para editar')

    table = get_table(table_name)
    data = request.get_json() or {}
    # mapeia colunas válidas (case-insensitive)
    col_map = {c.name.lower(): c.name for c in table.c}
    clean_data = {}
    for k, v in data.items():
        key_lower = k.lower()
        if key_lower in col_map:
            clean_data[col_map[key_lower]] = v
    data = clean_data

    pk = getattr(table.c, f"{table_name.upper()}STAMP")
    try:
        upd = table.update().where(pk == record_stamp).values(**data)
        result = db.session.execute(upd)
        if result.rowcount == 0:
            abort(404)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.exception(f"Falha ao atualizar {table_name}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# API: Delete record
@bp.route('/api/<table_name>/<record_stamp>', methods=['DELETE'])
@login_required
def delete_record(table_name, record_stamp):
    # valida permissão de eliminação
    if not has_permission(table_name, 'eliminar'):
        abort(403, 'Sem permissão para eliminar')

    table = get_table(table_name)
    pk = getattr(table.c, f"{table_name.upper()}STAMP")
    try:
        delete_stmt = table.delete().where(pk == record_stamp)
        result = db.session.execute(delete_stmt)
        if result.rowcount == 0:
            abort(404)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.exception(f"Falha ao eliminar {table_name}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
