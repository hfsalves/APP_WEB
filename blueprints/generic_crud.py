# blueprints/generic_crud.py

from flask import Blueprint, render_template, request, jsonify, abort, current_app
from flask_login import login_required, current_user
from sqlalchemy import MetaData, Table, select, text, String, or_
from app import db
from models import Campo, Menu, Acessos, CamposModal, Linhas
import uuid

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
    
    linhas_exist = Linhas.query.filter_by(MAE=table_name).count() > 0


    return render_template(
        'dynamic_form.html',
        table_name=table_name,
        record_stamp=record_stamp,
        menu_label=menu_label,
        botoes=botoes,
        linhas_exist=linhas_exist  # <-- adiciona aqui
    )

# --------------------------------------------------
# API: DESCRIBE ou LISTAGEM
# --------------------------------------------------
@bp.route('/api/<table_name>', methods=['GET'])
@login_required
def list_or_describe(table_name):
    if request.args.get('action') == 'describe':
        campos = Campo.query.filter_by(tabela=table_name).order_by(Campo.ordem).all()
        pk_name = f"{table_name.upper()}STAMP"
        cols = []
        for c in campos:
            cols.append({
                'name':             c.nmcampo,
                'descricao':        c.descricao,
                'tipo':             c.tipo,
                'lista':            bool(c.lista),
                'filtro':           bool(c.filtro) if c.tipo != 'VIRTUAL' else False,
                'admin':            bool(c.admin),
                'primary_key':      (c.nmcampo == pk_name),
                'readonly':         True if c.tipo == 'VIRTUAL' else bool(c.ronly),
                'combo':            c.combo,
                'virtual':          c.virtual if c.tipo == 'VIRTUAL' else None,
                'ordem':            c.ordem,
                'tam':              c.tam,
                'ordem_mobile':     c.ordem_mobile,
                'tam_mobile':       c.tam_mobile,
                'condicao_visivel': c.condicao_visivel,
                'obrigatorio':      c.obrigatorio
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
        # 1. Recolhe os campos VIRTUAL para esta tabela
        virtual_fields = (
            Campo.query
                .filter_by(tabela=table_name, tipo='VIRTUAL')
                .all()
        )

        # 2. Identifica o nome do PK
        pk_name = f"{table_name.upper()}STAMP"

        # 3. Para cada campo virtual e registo, executa a subquery
        for campo in virtual_fields:
            sql = text(campo.virtual)  # exemplo: SELECT TOP 1 VALOR ... WHERE CLIENTE = :pk
            for rec in records:
                pk_value = rec.get(pk_name)
                if not pk_value:
                    continue
                try:
                    val = db.session.execute(sql, {'pk': pk_value}).scalar()
                except Exception as e:
                    val = None  # ou logar erro
                rec[campo.nmcampo] = val
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
# API: marcar MN como tratada
# --------------------------------------------------
@bp.route('/api/mn/tratar', methods=['POST'])
@login_required
def mn_tratar():
    data = request.get_json(silent=True) or {}
    mnstamp = data.get('MNSTAMP') or data.get('mnstamp')
    if not mnstamp:
        return jsonify({'ok': False, 'error': 'MNSTAMP em falta'}), 400

    # Permissão: MN admin ou permissão de editar tabela MN (se existir ACL)
    allowed = getattr(current_user, 'MNADMIN', False) or has_permission('MN', 'editar')
    if not allowed:
        return jsonify({'ok': False, 'error': 'Sem permissão'}), 403

    try:
        sql = text("""
            UPDATE MN
            SET TRATADO = 1,
                NMTRATADO = :user,
                DTTRATADO = CAST(GETDATE() AS date)
            WHERE MNSTAMP = :stamp
        """)
        db.session.execute(sql, {'user': current_user.LOGIN, 'stamp': mnstamp})
        db.session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Erro ao marcar MN como tratada')
        return jsonify({'ok': False, 'error': str(e)}), 500

# --------------------------------------------------
# API: tarefas do monitor com filtro por utilizador/origem
# --------------------------------------------------
@bp.route('/api/monitor_tasks_filtered', methods=['GET'])
@login_required
def monitor_tasks_filtered():
    only_mine = request.args.get('only_mine', '1') in ('1', 'true', 'True')

    is_mn_admin = bool(getattr(current_user, 'MNADMIN', False))
    is_lp_admin = bool(getattr(current_user, 'LPADMIN', False))

    where = []
    params = {'user': current_user.LOGIN}

    if only_mine:
        where.append("UTILIZADOR = :user")
    else:
        origins = []
        if is_mn_admin:
            origins.append("'MN'")
        if is_lp_admin:
            origins.extend(["'LP'", "'FS'"])
        if origins:
            where.append(f"ORIGEM IN ({', '.join(origins)})")
        else:
            # fallback para apenas as do próprio
            where.append("UTILIZADOR = :user")

    # Regras de data: todas as atrasadas, e tratadas apenas últimos 7 dias
    # Implementamos como (TRATADO=0) OR (TRATADO=1 AND DATA >= hoje-7)
    where.append("(TRATADO = 0 OR DATA >= DATEADD(day, -7, CAST(GETDATE() AS date)))")

    where_sql = (" WHERE " + " AND ".join(where)) if where else ""

    sql = text(f"""
        SELECT 
            T.TAREFASSTAMP,
            CONVERT(varchar(10), T.DATA, 23)       AS DATA,        -- YYYY-MM-DD
            LEFT(CONVERT(varchar(8), T.HORA, 108), 5) AS HORA,     -- HH:MM
            T.TAREFA,
            T.ALOJAMENTO,
            T.TRATADO,
            T.ORIGEM,
            T.UTILIZADOR,
            U.NOME AS UTILIZADOR_NOME,
            U.COR  AS UTILIZADOR_COR
        FROM TAREFAS T
        LEFT JOIN US U ON U.LOGIN = T.UTILIZADOR
        {where_sql}
        ORDER BY T.DATA, T.HORA
    """)
    try:
        rows = db.session.execute(sql, params).fetchall()
        return jsonify([dict(r._mapping) for r in rows])
    except Exception as e:
        current_app.logger.exception('Erro em monitor_tasks_filtered')
        return jsonify({'error': str(e)}), 500

# --------------------------------------------------
# API: Tarefas tratar/reabrir
# --------------------------------------------------
@bp.route('/api/tarefas/tratar', methods=['POST'])
@login_required
def tarefa_tratar():
    data = request.get_json(silent=True) or {}
    tid = data.get('id')
    if not tid:
        return jsonify({'ok': False, 'error': 'ID em falta'}), 400
    try:
        sql = text("""
            UPDATE TAREFAS
            SET TRATADO = 1,
                NMTRATADO = :user,
                DTTRATADO = CAST(GETDATE() AS date)
            WHERE TAREFASSTAMP = :id
        """)
        db.session.execute(sql, {'user': current_user.LOGIN, 'id': tid})
        db.session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Erro ao tratar tarefa')
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/api/tarefas/reabrir', methods=['POST'])
@login_required
def tarefa_reabrir():
    data = request.get_json(silent=True) or {}
    tid = data.get('id')
    if not tid:
        return jsonify({'ok': False, 'error': 'ID em falta'}), 400
    try:
        sql = text("""
            UPDATE TAREFAS
            SET TRATADO = 0,
                NMTRATADO = NULL,
                DTTRATADO = NULL
            WHERE TAREFASSTAMP = :id
        """)
        db.session.execute(sql, {'id': tid})
        db.session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Erro ao reabrir tarefa')
        return jsonify({'ok': False, 'error': str(e)}), 500

# --------------------------------------------------
# API: RS search and update OBS
# --------------------------------------------------
@bp.route('/api/rs/search')
@login_required
def rs_search():
    date_in   = request.args.get('date')
    reserva   = request.args.get('reserva')
    if not date_in and not reserva:
        return jsonify({'error': 'Indica data ou reserva'}), 400

    try:
        if date_in:
            sql = text("""
                SELECT RESERVA, ALOJAMENTO, CONVERT(varchar(10), DATAIN, 23) AS DATAIN,
                       NOITES, ADULTOS, CRIANCAS, OBS, NOME
                FROM RS
                WHERE DATAIN = :date AND (CANCELADA = 0 OR CANCELADA IS NULL)
                ORDER BY ALOJAMENTO
            """)
            rows = db.session.execute(sql, {'date': date_in}).fetchall()
        else:
            sql = text("""
                SELECT RESERVA, ALOJAMENTO, CONVERT(varchar(10), DATAIN, 23) AS DATAIN,
                       NOITES, ADULTOS, CRIANCAS, OBS, NOME
                FROM RS
                WHERE RESERVA = :reserva AND (CANCELADA = 0 OR CANCELADA IS NULL)
            """)
            rows = db.session.execute(sql, {'reserva': reserva}).fetchall()
        return jsonify([dict(r._mapping) for r in rows])
    except Exception as e:
        current_app.logger.exception('Erro em rs_search')
        return jsonify({'error': str(e)}), 500

@bp.route('/api/rs/obs', methods=['POST'])
@login_required
def rs_update_obs():
    data = request.get_json(silent=True) or {}
    reserva = data.get('reserva')
    obs     = data.get('obs', '')
    if not reserva:
        return jsonify({'ok': False, 'error': 'Reserva em falta'}), 400
    try:
        sql = text("""
            UPDATE RS SET OBS = :obs WHERE RESERVA = :reserva
        """)
        db.session.execute(sql, {'obs': obs, 'reserva': reserva})
        db.session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Erro em rs_update_obs')
        return jsonify({'ok': False, 'error': str(e)}), 500

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

    # Base: dados reais
    rec = dict(row._mapping)

    # 🔁 Adiciona campos virtuais
    virtual_fields = (
        Campo.query
             .filter_by(tabela=table_name, tipo='VIRTUAL')
             .all()
    )
    pk_value = rec.get(f"{table_name.upper()}STAMP")

    for campo in virtual_fields:
        try:
            val = db.session.execute(text(campo.virtual), {'pk': pk_value}).scalar()
        except Exception as e:
            val = None
        rec[campo.nmcampo] = val

    return jsonify(rec)


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
    # ... ACL ...
    pk_name = f"{table_name.upper()}STAMP"
    sql = f"DELETE FROM {table_name} WHERE {pk_name} = :id"
    result = db.session.execute(text(sql), {"id": record_stamp})
    db.session.commit()

    if result.rowcount == 0:
        abort(404, "Registo não encontrado")

    return jsonify(success=True)

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
            'LIGACAOMAE':  l.LIGACAOMAE,
            'CAMPOSCAB':   l.LIGACAO,
            'CAMPOSLIN':   l.LIGACAOMAE
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

        # --- monta o SQL dinamicamente ---
        if ligacao.upper().startswith('SELECT') or ' ' in ligacao:
            sql = ligacao.replace("{RECORD_STAMP}", ":record")
        elif ligacao:
            sql = f"SELECT * FROM {tabela} WHERE {ligacao} = :record"
        elif ligacaomae:
            sql = f"SELECT * FROM {tabela} WHERE {ligacaomae} = :record"
        else:
            abort(500, f"Definição inválida para detalhe {tabela}")

        # <<< AQUI: executa e define `rows` >>>
        rows = db.session.execute(text(sql), {"record": record_stamp}).mappings().all()

        # metadados de colunas para a lista
        pk_name = f"{tabela.upper()}STAMP"

        # buscar os campos visíveis na lista
        cols = list(
            Campo.query
                .filter_by(tabela=tabela, lista=True)
                .order_by(Campo.ordem)
                .all()
        )

        # garantir que a PK está incluída (mesmo que lista=False)
        pk_name = f"{tabela.upper()}STAMP"
        if not any(c.nmcampo.upper() == pk_name for c in cols):
            # cria um campo fake, não vem da tabela Campo
            from types import SimpleNamespace
            cols.insert(0, SimpleNamespace(nmcampo=pk_name, descricao='ID', ordem=0))

        campos = [
            {
                "CAMPO": c.nmcampo,
                "LABEL": c.descricao,
                "CAMPODESTINO": c.nmcampo,
                "VISIVEL": c.nmcampo.upper() != pk_name
            }
            for c in cols
        ]

        # mapeia camposcab / camposlin
        camposcab = [c.strip() for c in (defn.CAMPOSCAB or '').split(',') if c.strip()]
        camposlin = [c.strip() for c in (defn.CAMPOSLIN or '').split(',') if c.strip()]

        # <<< e só aqui é que usas `rows` >>>
        detalhes.append({
            "linhasstamp": defn.LINHASSTAMP,
            "tabela":      tabela,
            "campos":      campos,
            "rows":        [dict(r) for r in rows],
            "camposcab":   camposcab,
            "camposlin":   camposlin
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
      COALESCE(u.COR, tc.COR, eq.COR, '#333333') AS COR
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


# In generic_crud.py (add within the existing Blueprint `bp`)

from datetime import date, datetime

@bp.route('/planner/', defaults={'planner_date': None})
@bp.route('/planner/<planner_date>')
@login_required
def view_planner(planner_date):
    try:
        if planner_date:
            datetime.strptime(planner_date, '%Y-%m-%d')  # valida formato
        else:
            planner_date = date.today().isoformat()
    except ValueError:
        return "Formato de data inválido (usa YYYY-MM-DD)", 400

    return render_template('planner.html', planner_date=planner_date)



@bp.route('/api/cleaning_plan')
def api_cleaning_plan():
    """
    Return JSON payload with lodging cleaning plan for a given date.
    Query params:
      - date: 'YYYY-MM-DD'
    """
    date = request.args.get('date')
    sql = text("""
        SELECT
        al.NOME           AS lodging,
        al.TIPOLOGIA      AS typology,
        al.ZONA           AS zone,
        -- Última equipa que limpou
        lc.last_team      AS last_team,
        -- Check-out do dia
        co.HORAOUT        AS checkout_time,
        co.RESERVA        AS checkout_reservation,
        co.ADULTOS + co.CRIANCAS  AS checkout_people,
        co.NOITES         AS checkout_nights,
        -- Check-in do dia
        ci.HORAIN         AS checkin_time,
        ci.RESERVA        AS checkin_reservation,
        ci.ADULTOS + ci.CRIANCAS  AS checkin_people,
        ci.NOITES         AS checkin_nights,
        -- Limpezas já agendadas no dia
        pl.LPSTAMP        AS cleaning_id,
        pl.HORA           AS cleaning_time,
        pl.EQUIPA         AS cleaning_team,
        pl.TERMINADA      AS cleaning_done,
        pl.HOSPEDES       AS cleaning_guests,
        pl.NOITES         AS cleaning_nights,
        pl.OBS            AS cleaning_notes,
        -- O estado (1:checkout, 2:checkin, 3:ocupado, 4:vazio)
        CASE
            WHEN co.RSSTAMP IS NOT NULL THEN 1
            WHEN ci.RSSTAMP IS NOT NULL THEN 2
            WHEN oc.RSSTAMP IS NOT NULL THEN 3
            ELSE 4
        END AS planner_status,
        0                  AS cost
        FROM AL al
        LEFT JOIN (
            SELECT ALOJAMENTO, MAX(DATA) AS last_date, MAX(HORA) AS last_hour, MAX(EQUIPA) AS last_team
            FROM LP
            WHERE DATA < :date
            GROUP BY ALOJAMENTO
        ) lc ON lc.ALOJAMENTO = al.NOME
        -- Apenas reservas NÃO canceladas
        LEFT JOIN RS co ON co.ALOJAMENTO = al.NOME AND co.DATAOUT = :date AND co.CANCELADA = 0
        LEFT JOIN RS ci ON ci.ALOJAMENTO = al.NOME AND ci.DATAIN = :date AND ci.CANCELADA = 0
        LEFT JOIN (
            SELECT RSSTAMP, ALOJAMENTO
            FROM RS
            WHERE CANCELADA = 0
            AND DATAIN < :date AND DATAOUT > :date
        ) oc ON oc.ALOJAMENTO = al.NOME
        LEFT JOIN LP pl ON pl.ALOJAMENTO = al.NOME AND pl.DATA = :date
        ORDER BY planner_status, al.ZONA, al.NOME
    """,
    )
    # Execute and fetch mappings
    rows = db.session.execute(sql, {'date': date}).mappings().all()

    # Convert RowMapping to plain dicts for JSON serialization
    result = [dict(row) for row in rows]
    return jsonify(result)

@bp.route("/api/LP/gravar", methods=["POST"])
def api_gravar_limpezas():
    limpezas = request.get_json()
    if not limpezas:
        return jsonify(success=False, message="Nenhum dado recebido"), 400
    for lp in limpezas:
        # Verifica se já existe (mesmo ALOJAMENTO, DATA, HORA, EQUIPA)
        reg = db.session.execute(
            text("""
            SELECT LPSTAMP FROM LP WHERE
              ALOJAMENTO = :alojamento
              AND DATA = :data
              AND HORA = :hora
              AND EQUIPA = :equipa
            """), dict(
                alojamento=lp["ALOJAMENTO"],
                data=lp["DATA"],
                hora=lp["HORA"],
                equipa=lp["EQUIPA"]
            )
        ).fetchone()
        if reg:
            continue  # já existe, não grava de novo
        # Senão, cria
        db.session.execute(
            text("""
            INSERT INTO LP (LPSTAMP, ALOJAMENTO, DATA, HORA, EQUIPA, TERMINADA, CUSTO, HOSPEDES, NOITES, OBS)
            VALUES (:lpstamp, :alojamento, :data, :hora, :equipe, 0, 0, 0, 0, '')
            """),
            dict(
                lpstamp=uuid.uuid4().hex[:25],
                alojamento=lp["ALOJAMENTO"],
                data=lp["DATA"],
                hora=lp["HORA"],
                equipe=lp["EQUIPA"]
            )
        )
    db.session.commit()
    return jsonify(success=True)

@bp.route('/api/update_campo', methods=['POST'])
@login_required
def update_campo():
    if not getattr(current_user, 'DEV', False):
        return jsonify(success=False, error="Acesso negado")

    data = request.get_json()
    tabela = data.get('tabela')
    campo  = data.get('campo')

    if not tabela or not campo:
        return jsonify(success=False, error="Tabela ou campo em falta")

    # Verifica que tipo de update vamos fazer
    updates = []
    params = {}

    if 'ordem' in data:
        updates.append("ORDEM = :ordem")
        params["ordem"] = data.get("ordem")

    if 'tam' in data:
        updates.append("TAM = :tam")
        params["tam"] = data.get("tam")

    if 'ordem_mobile' in data:
        updates.append("ORDEM_MOBILE = :ordem_mobile")
        params["ordem_mobile"] = data.get("ordem_mobile")

    if 'tam_mobile' in data:
        updates.append("TAM_MOBILE = :tam_mobile")
        params["tam_mobile"] = data.get("tam_mobile")

    if not updates:
        return jsonify(success=False, error="Nenhum campo para atualizar")

    sql = f"""
        UPDATE CAMPOS
        SET {', '.join(updates)}
        WHERE TABELA = :tabela AND NMCAMPO = :campo
    """

    params["tabela"] = tabela
    params["campo"] = campo

    try:
        db.session.execute(text(sql), params)
        db.session.commit()
        return jsonify(success=True)
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, error=str(e))


@bp.route('/api/tarefas/tratar', methods=['POST'])
@login_required
def tratar_tarefa():
    data = request.get_json()
    tarefa_id = data.get('id')

    if not tarefa_id:
        return jsonify({'error': 'Falta o ID da tarefa'}), 400

    try:
        sql = text("UPDATE TAREFAS SET TRATADO = 1 WHERE TAREFASSTAMP = :id")
        db.session.execute(sql, {'id': tarefa_id})
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/tarefas/reabrir', methods=['POST'])
@login_required
def reabrir_tarefa():
    data = request.get_json()
    tarefa_id = data.get('id')

    if not tarefa_id:
        return jsonify({'error': 'Falta o ID da tarefa'}), 400

    try:
        sql = text("UPDATE TAREFAS SET TRATADO = 0 WHERE TAREFASSTAMP = :id")
        db.session.execute(sql, {'id': tarefa_id})
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

from flask import request, jsonify, abort
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import text

@bp.route('/api/monitor_tasks', methods=['GET'])
@login_required
def api_monitor_tasks():
    hoje = datetime.today().date()
    start = hoje - timedelta(days=7)
    end = hoje + timedelta(days=7)

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
      COALESCE(u.COR, tc.COR, eq.COR, '#333333') AS COR
    FROM TAREFAS ta
    LEFT JOIN US    u  ON u.LOGIN    = ta.UTILIZADOR
    LEFT JOIN TEC   tc ON tc.NOME    = u.TECNICO
    LEFT JOIN EQ    eq ON eq.NOME    = u.EQUIPA
    WHERE ta.DATA BETWEEN :start AND :end
      AND UPPER(ta.UTILIZADOR) = UPPER(:user)
    ORDER BY ta.DATA, ta.HORA
    """)

    rows = db.session.execute(sql, {
        'start': start.isoformat(),
        'end': end.isoformat(),
        'user': current_user.LOGIN
    }).mappings().all()

    tarefas = [dict(r) for r in rows]
    return jsonify(tarefas)


@bp.route('/api/mn_incidente', methods=['POST'])
@login_required
def criar_mn_incidente():
    """
    Endpoint dedicado para criar uma nova incidência na tabela MN
    Garante que o campo TRATADO é sempre booleano.
    """
    from sqlalchemy import text
    import uuid
    data = request.get_json() or {}

    # Campos obrigatórios
    obrigatorios = ['ALOJAMENTO', 'DATA', 'NOME', 'INCIDENCIA']
    for campo in obrigatorios:
        if not data.get(campo):
            return jsonify({'error': f'Campo obrigatório em falta: {campo}'}), 400

    # Campos automáticos/defaults
    mnstamp = uuid.uuid4().hex[:25].upper()
    tratado = str(data.get('TRATADO', '0')).lower() in ['1', 'true', 'on']
    dttratado = data.get('DTTRATADO', None) or None
    nmtratado = data.get('NMTRATADO', '')
    dttratado = data.get('DTTRATADO') or '1900-01-01'


    sql = text("""
        INSERT INTO MN (MNSTAMP, ALOJAMENTO, DATA, NOME, INCIDENCIA, TRATADO, DTTRATADO, NMTRATADO)
        VALUES (:mnstamp, :alojamento, :data, :nome, :incidencia, :tratado, :dttratado, :nmtratado)
    """)
    try:
        db.session.execute(sql, {
            'mnstamp': mnstamp,
            'alojamento': data['ALOJAMENTO'],
            'data': data['DATA'],
            'nome': data['NOME'],
            'incidencia': data['INCIDENCIA'],
            'tratado': tratado,
            'dttratado': dttratado,
            'nmtratado': nmtratado
        })
        db.session.commit()
        return jsonify({'success': True, 'MNSTAMP': mnstamp}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/fs_falta', methods=['POST'])
@login_required
def api_fs_falta():
    from sqlalchemy import text
    import uuid

    data = request.get_json() or {}
    obrig = ['ALOJAMENTO', 'DATA', 'USERNAME', 'ITEM']
    for c in obrig:
        if not data.get(c):
            return jsonify({'error': f'Campo obrigatório em falta: {c}'}), 400

    fsstamp = uuid.uuid4().hex[:25].upper()

    urgente    = str(data.get('URGENTE', '0')).lower() in ('1','true','on')
    tratado    = str(data.get('TRATADO', '0')).lower() in ('1','true','on')
    tratadopor = data.get('TRATADOPOR') or ''
    dttratado  = data.get('DTTRATADO') or '1900-01-01'  # mantém alinhado com o teu default

    sql = text("""
        INSERT INTO FS (FSSTAMP, ALOJAMENTO, DATA, USERNAME, ITEM, URGENTE, TRATADO, TRATADOPOR, DTTRATADO)
        VALUES (:FSSTAMP, :ALOJAMENTO, :DATA, :USERNAME, :ITEM, :URGENTE, :TRATADO, :TRATADOPOR, :DTTRATADO)
    """)

    try:
        db.session.execute(sql, {
            'FSSTAMP': fsstamp,
            'ALOJAMENTO': data['ALOJAMENTO'],
            'DATA': data['DATA'],
            'USERNAME': data['USERNAME'],
            'ITEM': data['ITEM'],
            'URGENTE': 1 if urgente else 0,
            'TRATADO': 1 if tratado else 0,
            'TRATADOPOR': tratadopor,
            'DTTRATADO': dttratado
        })
        db.session.commit()
        return jsonify({'success': True, 'FSSTAMP': fsstamp}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500



@bp.route('/api/profile/fields', methods=['GET'])
@login_required
def api_profile_fields():
    """
    Devolve os campos configurados para o formulário de perfil:
      - Só campos da tabela US
      - Só tipo ADMIN=1 na CAMPOS
      - Lista o nome, tipo, descrição
    """
    from app import db
    try:
        rows = db.session.execute(
            text("""
                SELECT nmcampo, tipo, descricao
                FROM CAMPOS
                WHERE tabela = 'US' AND admin = 1
                ORDER BY ordem
            """)
        ).fetchall()
        fields = [
            dict(zip(['nmcampo', 'tipo', 'descricao'], row))
            for row in rows
        ]
    except Exception as e:
        return {'error': str(e)}, 500

    return {'fields': fields}

from sqlalchemy import text

@bp.route("/api/tarefa_info/<stamp>")
@login_required
def tarefa_info(stamp):
    result = db.session.execute(
        db.text("SELECT dbo.info_tarefa(:stamp) AS info"),
        {"stamp": stamp}
    ).fetchone()
    
    return jsonify({"info": result.info if result else ""})

# === Monitor: Manutenções não agendadas + Agendamento em TAREFAS =================
from sqlalchemy import text

@bp.route('/api/monitor/mn-nao-agendadas', methods=['GET'])
@login_required
def api_mn_nao_agendadas():
    """Lista MN por agendar (sem entrada em TAREFAS). Só para MNADMIN."""
    if not getattr(current_user, 'MNADMIN', 0):
        abort(403, 'Sem permissão de manutenção')

    sql = text("""
        SELECT 
          MNSTAMP,
          NOME,
          ALOJAMENTO,
          INCIDENCIA,
          CONVERT(varchar(10), DATA, 23) AS DATA
        FROM MN
        WHERE TRATADO = 0
          AND MNSTAMP NOT IN (SELECT ORISTAMP FROM TAREFAS)
        ORDER BY DATA DESC, MNSTAMP
    """)
    rows = db.session.execute(sql).mappings().all()
    return jsonify({'rows': [dict(r) for r in rows]})


@bp.route('/api/tarefas/from-mn', methods=['POST'])
@login_required
def api_criar_tarefa_from_mn():
    """Cria uma TAREFA a partir de uma MN não agendada."""
    if not getattr(current_user, 'MNADMIN', 0):
        abort(403, 'Sem permissão de manutenção')

    data = request.get_json() or {}
    mnstamp = data.get('MNSTAMP')
    data_str = data.get('DATA')   # YYYY-MM-DD
    hora_str = data.get('HORA')   # HH:MM

    if not mnstamp or not data_str or not hora_str:
        return jsonify({'ok': False, 'error': 'Parâmetros obrigatórios: MNSTAMP, DATA, HORA'}), 400

    # Buscar incidência e alojamento da MN
    mn = db.session.execute(
        text("""
            SELECT 
              INCIDENCIA,
              ALOJAMENTO
            FROM MN
            WHERE MNSTAMP = :mnstamp
        """),
        {'mnstamp': mnstamp}
    ).fetchone()

    if not mn:
        return jsonify({'ok': False, 'error': 'MN não encontrada'}), 404

    # Inserir na TAREFAS
    # Nota: a coluna chama-se DURACAO (conforme queries acima neste ficheiro)
    ins = text("""
        INSERT INTO TAREFAS (
            TAREFASSTAMP, ORIGEM, ORISTAMP, UTILIZADOR,
            DATA, HORA, DURACAO, TAREFA, ALOJAMENTO, TRATADO
        )
        VALUES (
            LEFT(NEWID(), 25), 'MN', :oristamp, :utilizador,
            :data, :hora, :duracao, :tarefa, :alojamento, 0
        )
    """)
    try:
        db.session.execute(ins, {
            'oristamp':   mnstamp,
            'utilizador': getattr(current_user, 'LOGIN', None),
            'data':       data_str,
            'hora':       hora_str,
            'duracao':    60,
            'tarefa':     mn.INCIDENCIA,
            'alojamento': mn.ALOJAMENTO
        })
        db.session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500
