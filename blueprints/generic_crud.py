# blueprints/generic_crud.py

from flask import Blueprint, render_template, request, jsonify, abort, current_app
from flask_login import login_required, current_user
from sqlalchemy import MetaData, Table, select, text, String
from app import db
from models import Campo, Menu, Acessos, CamposModal, Linhas

bp = Blueprint('generic', __name__, url_prefix='/generic')

# --------------------------------------------------
# ACL helper
# --------------------------------------------------
def has_permission(table_name: str, action: str) -> bool:
    # super‐admin vê tudo
    if getattr(current_user, 'ADMIN', False):
        return True
    acesso = (
        Acessos.query
               .filter_by(utilizador=current_user.LOGIN, tabela=table_name)
               .first()
    )
    if not acesso:
        return False
    return getattr(acesso, action, False)

# --------------------------------------------------
# Helper: reflect a table by name
# --------------------------------------------------
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

# --------------------------------------------------
# Views para front-end
# --------------------------------------------------
@bp.route('/view/calendar/')
@login_required
def view_calendar():
    return render_template('calendar.html')

@bp.route('/view/<table_name>/', defaults={'record_stamp': None})
@bp.route('/view/<table_name>/<record_stamp>')
@login_required
def view_table(table_name, record_stamp):
    menu_item  = Menu.query.filter_by(tabela=table_name).first()
    menu_label = menu_item.nome if menu_item else table_name.capitalize()
    return render_template(
        'dynamic_list.html',
        table_name=table_name,
        record_stamp=record_stamp,
        menu_label=menu_label
    )

@bp.route('/form/<table_name>/', defaults={'record_stamp': None})
@bp.route('/form/<table_name>/<record_stamp>')
@login_required
def edit_table(table_name, record_stamp):
    from models import MenuBotoes
    menu_item  = Menu.query.filter_by(tabela=table_name).first()
    menu_label = menu_item.nome if menu_item else table_name.capitalize()

    botoes_query = MenuBotoes.query.filter_by(
        TABELA=table_name, ATIVO=True
    ).order_by(MenuBotoes.ORDEM)

    botoes = [{
        'NOME': b.NOME,
        'ICONE': b.ICONE,
        'TEXTO': b.TEXTO,
        'COR': b.COR,
        'TIPO': b.TIPO,
        'ACAO': b.ACAO,
        'CONDICAO': b.CONDICAO,
        'DESTINO': b.DESTINO
    } for b in botoes_query]

    return render_template(
        'dynamic_form.html',
        table_name=table_name,
        record_stamp=record_stamp,
        menu_label=menu_label,
        botoes=botoes
    )

# --------------------------------------------------
# API: DESCRIBE ou LISTAGEM
# --------------------------------------------------
@bp.route('/api/<table_name>', methods=['GET'])
@login_required
def list_or_describe(table_name):
    # 1) DESCRIBE
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

    # 2) LISTAGEM
    if not has_permission(table_name, 'consultar'):
        abort(403, 'Sem permissão para consultar')

    table = get_table(table_name)
    stmt  = select(table)

    # 3) FILTROS via query string
    for key, value in request.args.items():
        if key == 'action':
            continue

        # intervalo de datas: campo_from e campo_to
        if key.endswith('_from'):
            col_name = key[:-5]
            if hasattr(table.c, col_name):
                stmt = stmt.where(getattr(table.c, col_name) >= value)
            continue

        if key.endswith('_to'):
            col_name = key[:-3]
            if hasattr(table.c, col_name):
                stmt = stmt.where(getattr(table.c, col_name) <= value)
            continue

        # filtros normais
        if hasattr(table.c, key):
            col = getattr(table.c, key)
            # texto: contém via LIKE
            if isinstance(col.type, String):
                stmt = stmt.where(col.like(f"%{value}%"))
            else:
                stmt = stmt.where(col == value)

    # 4) ordenação automática por ORDEM → DATA → HORA
    order_cols = []
    for cn in ('ORDEM', 'DATA', 'HORA'):
        if hasattr(table.c, cn):
            order_cols.append(getattr(table.c, cn))
    if order_cols:
        stmt = stmt.order_by(*order_cols)

    # 5) executa e retorna JSON
    try:
        rows    = db.session.execute(stmt).fetchall()
        records = [dict(r._mapping) for r in rows]
        return jsonify(records)
    except Exception as e:
        current_app.logger.exception(f"Falha ao listar {table_name}")
        return jsonify({'error': str(e)}), 500

# --------------------------------------------------
# API: opções para COMBO
# --------------------------------------------------
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

# --------------------------------------------------
# API: registro único
# --------------------------------------------------
@bp.route('/api/<table_name>/<record_stamp>', methods=['GET'])
@login_required
def get_record(table_name, record_stamp):
    if not has_permission(table_name, 'consultar'):
        abort(403, 'Sem permissão para consultar')

    table = get_table(table_name)
    pk    = getattr(table.c, f"{table_name.upper()}STAMP")
    stmt  = select(table).where(pk == record_stamp)
    row   = db.session.execute(stmt).fetchone()
    if not row:
        abort(404, f"Registro não encontrado: {record_stamp}")
    return jsonify(dict(row._mapping))

# --------------------------------------------------
# API: inserir novo registro
# --------------------------------------------------
@bp.route('/api/<table_name>', methods=['POST'])
@login_required
def create_record(table_name):
    if not has_permission(table_name, 'inserir'):
        abort(403, 'Sem permissão para inserir')

    table = get_table(table_name)
    data  = request.get_json() or {}

    # Se vier chave vazia para o PK, removemos
    pk_name = f"{table_name.upper()}STAMP"
    if pk_name in data and not data[pk_name]:
        data.pop(pk_name)

    # — Filtra só colunas válidas —
    col_map = {c.name.lower(): c.name for c in table.c}
    clean   = {}
    for k, v in data.items():
        lk = k.lower()
        if lk in col_map:
            clean[col_map[lk]] = v
    # — end filtra —

    try:
        ins = table.insert().values(**clean)
        db.session.execute(ins)
        db.session.commit()
        return jsonify({'success': True}), 201
    except Exception as e:
        current_app.logger.exception(f"Falha ao criar {table_name}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# --------------------------------------------------
# API: atualizar registro
# --------------------------------------------------
@bp.route('/api/<table_name>/<record_stamp>', methods=['PUT'])
@login_required
def update_record(table_name, record_stamp):
    if not has_permission(table_name, 'editar'):
        abort(403, 'Sem permissão para editar')

    table = get_table(table_name)
    data  = request.get_json() or {}
    # filtra só colunas válidas
    col_map = {c.name.lower(): c.name for c in table.c}
    clean   = {}
    for k, v in data.items():
        lk = k.lower()
        if lk in col_map:
            clean[col_map[lk]] = v
    data = clean

    pk = getattr(table.c, f"{table_name.upper()}STAMP")
    try:
        upd = table.update().where(pk == record_stamp).values(**data)
        res = db.session.execute(upd)
        if res.rowcount == 0:
            abort(404)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.exception(f"Falha ao atualizar {table_name}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# --------------------------------------------------
# API: apagar registro
# --------------------------------------------------
@bp.route('/api/<table_name>/<record_stamp>', methods=['DELETE'])
@login_required
def delete_record(table_name, record_stamp):
    if not has_permission(table_name, 'eliminar'):
        abort(403, 'Sem permissão para eliminar')

    table = get_table(table_name)
    pk    = getattr(table.c, f"{table_name.upper()}STAMP")
    try:
        ddl = table.delete().where(pk == record_stamp)
        res = db.session.execute(ddl)
        if res.rowcount == 0:
            abort(404)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.exception(f"Falha ao eliminar {table_name}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# --------------------------------------------------
# API: linhas dinâmicas
# --------------------------------------------------
@bp.route('/api/linhas/<mae>', methods=['GET'])
@login_required
def api_linhas(mae):
    if not has_permission(mae, 'consultar'):
        abort(403, 'Sem permissão para consultar linhas deste registo')

    linhas = Linhas.query.filter_by(MAE=mae).all()
    resultado = []
    for l in linhas:
        resultado.append({
            'LINHASSTAMP': l.LINHASSTAMP,
            'TABELA':      l.TABELA,
            'LIGACAO':     l.LIGACAO,
            'LIGACAOMAE':  l.LIGACAOMAE
        })
    return jsonify(resultado)

# --------------------------------------------------
# API: detalhes dinâmicos
# --------------------------------------------------
@bp.route('/api/dynamic_details/<mae>/<record_stamp>', methods=['GET'])
@login_required
def api_dynamic_details(mae, record_stamp):
    if not has_permission(mae, 'consultar'):
        abort(403, 'Sem permissão para ver detalhes')

    detalhes = []
    for defn in Linhas.query.filter_by(MAE=mae):
        tabela     = defn.TABELA.strip()
        ligacao    = (defn.LIGACAO or '').strip()
        ligacaomae = defn.LIGACAOMAE.strip()

        if ligacao.upper().startswith('SELECT') or ' ' in ligacao:
            sql = ligacao.replace("{RECORD_STAMP}", ":record")
        elif ligacao:
            sql = f"SELECT * FROM {tabela} WHERE {ligacao} = :record"
        elif ligacaomae:
            sql = f"SELECT * FROM {tabela} WHERE {ligacaomae} = :record"
        else:
            abort(500, f"Definição inválida para detalhe {tabela}")

        rows = db.session.execute(text(sql), {"record": record_stamp}).mappings().all()

        cols = (
            Campo.query
                 .filter_by(tabela=tabela, lista=True)
                 .order_by(Campo.ordem)
                 .all()
        )
        campos = [{"CAMPO": c.nmcampo, "LABEL": c.descricao, "CAMPODESTINO": c.nmcampo} for c in cols]

        detalhes.append({
            "linhasstamp": defn.LINHASSTAMP,
            "tabela":      tabela,
            "campos":      campos,
            "rows":        [dict(r) for r in rows]
        })

    return jsonify(detalhes)

# --------------------------------------------------
# API: tarefas para calendar
# --------------------------------------------------
from datetime import datetime

@bp.route('/api/calendar_tasks', methods=['GET'])
@login_required
def api_calendar_tasks():
    start = request.args.get('start')
    end   = request.args.get('end')
    if not start or not end:
        abort(400, 'Precisamos de start e end em formato YYYY-MM-DD')
    try:
        datetime.strptime(start, '%Y-%m-%d')
        datetime.strptime(end,   '%Y-%m-%d')
    except ValueError:
        abort(400, 'Formato de data inválido')

    sql = text("""
    SELECT
      ta.TAREFASSTAMP,
      CONVERT(varchar(10), ta.DATA, 23) AS DATA,
      ta.HORA,
      ta.DURACAO,
      ta.TAREFA,
      ta.ALOJAMENTO,
      ta.UTILIZADOR,
      ta.ORIGEM,
      ta.ORISTAMP,
      ta.TRATADO,
      COALESCE(tc.COR, eq.COR, '#333333') AS COR
    FROM TAREFAS ta
    LEFT JOIN US    u  ON u.LOGIN    = ta.UTILIZADOR
    LEFT JOIN TEC   tc ON tc.NOME    = u.TECNICO
    LEFT JOIN EQ    eq ON eq.NOME    = u.EQUIPA
    WHERE ta.DATA BETWEEN :start AND :end
    ORDER BY ta.DATA, ta.HORA
    """)
    rows = db.session.execute(sql, {'start': start, 'end': end}).mappings().all()
    tarefas = [dict(r) for r in rows]
    return jsonify(tarefas)
