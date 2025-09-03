import os
import pyodbc
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, date
from sqlalchemy import text

# Importa a instância db e modelos
from models import db, US, Menu, Acessos, Widget, UsWidget, MenuBotoes, Linhas
from models import Modais, CamposModal
#from your_app_folder import db  # ou ajusta conforme a tua estrutura

login_manager = LoginManager()

def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        "mssql+pyodbc://sa:enterprise@hfsalves.mooo.com,50002/GESTAO"
        "?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=Yes&protocol=TCP"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Garantir JSON e respostas com UTF-8 para evitar problemas de acentuação
    try:
        # Flask 2.x/3.x JSON provider
        app.json.ensure_ascii = False
    except Exception:
        app.config['JSON_AS_ASCII'] = False

    @app.after_request
    def _force_utf8(resp):
        try:
            mt = resp.mimetype or ''
            if mt.startswith('text/'):
                # acrescenta charset se não existir
                if 'charset=' not in (resp.headers.get('Content-Type') or ''):
                    resp.headers['Content-Type'] = f"{mt}; charset=utf-8"
            elif mt == 'application/json':
                # alguns navegadores assumem latin-1 sem charset
                resp.headers['Content-Type'] = 'application/json; charset=utf-8'
        except Exception:
            pass
        return resp

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    # Importa e regista blueprint genérico
    from blueprints.generic_crud import bp as generic_bp
    app.register_blueprint(generic_bp)

    from blueprints.anexos import bp as anexos_bp
    app.register_blueprint(anexos_bp)

    # Favicon at root path
    @app.route('/favicon.ico')
    def favicon():
        try:
            return send_from_directory(
                os.path.join(app.root_path, 'static', 'images'),
                'favicon.ico',
                mimetype='image/x-icon'
            )
        except Exception:
            # As fallback, try /static/images/favicon.ico redirect
            return redirect(url_for('static', filename='images/favicon.ico'))

    @app.context_processor
    def inject_menu_and_access():
        page_name = None
        menu_items = []
        menu_structure = []
        perms = {}
        menu_botoes = {}

        if current_user.is_authenticated:
            # 1) Carrega todos os menus (filtra admin se for caso)
            if getattr(current_user, 'ADMIN', False):
                menu_items = Menu.query.order_by(Menu.ordem).all()
            else:
                menu_items = (
                    Menu.query
                        .filter_by(admin=False)
                        .order_by(Menu.ordem)
                        .all()
                )

            # 2) Permissões de acesso por tabela
            rows = Acessos.query.filter_by(utilizador=current_user.LOGIN).all()
            perms = {
                a.tabela: {
                    'consultar': bool(a.consultar),
                    'inserir' : bool(a.inserir),
                    'editar'  : bool(a.editar),
                    'eliminar': bool(a.eliminar),
                }
                for a in rows
            }

            # Verificação direta de acesso à MN conforme pedido
            try:
                q_mn = db.session.execute(text(
                    "SELECT CONSULTAR FROM ACESSOS WHERE TABELA = 'MN' AND UTILIZADOR = :u"
                ), { 'u': current_user.LOGIN }).fetchone()
                can_open_mn = bool(getattr(current_user, 'ADMIN', False)) or (bool(q_mn[0]) if q_mn is not None else False)
            except Exception:
                can_open_mn = False

            try:
                q_fs = db.session.execute(text(
                    "SELECT CONSULTAR FROM ACESSOS WHERE TABELA = 'FS' AND UTILIZADOR = :u"
                ), { 'u': current_user.LOGIN }).fetchone()
                can_open_fs = bool(getattr(current_user, 'ADMIN', False)) or (bool(q_fs[0]) if q_fs is not None else False)
            except Exception:
                can_open_fs = False

            # 3) Determinar page_name e menu_botoes (igual lógica atual)
            parts = request.path.strip('/').split('/')
            if len(parts) >= 3 and parts[0] == 'generic' and parts[1] in ('view', 'form'):
                tabela_arg = parts[2]
                for m in menu_items:
                    if m.tabela == tabela_arg:
                        page_name = m.nome
                        botoes = (
                            MenuBotoes.query
                                .filter_by(TABELA=m.tabela, ATIVO=True)
                                .order_by(MenuBotoes.ORDEM)
                                .all()
                        )
                        menu_botoes = {
                            b.NOME: {
                                'icone'    : b.ICONE,
                                'texto'    : b.TEXTO,
                                'cor'      : b.COR,
                                'tipo'     : b.TIPO,
                                'acao'     : b.ACAO,
                                'condicao' : b.CONDICAO,
                                'destino'  : b.DESTINO,
                            }
                            for b in botoes
                        }
                        break

            if not page_name:
                for m in menu_items:
                    if request.path.startswith(m.url):
                        page_name = m.nome
                        break

            # 4) Montar estrutura do menu com permissões
            menu_structure = []
            user_is_admin = getattr(current_user, 'ADMIN', False)

            # Lista de widgets do user (para o dashboard)
            user_widgets = set()
            if not user_is_admin:
                user_widgets = {uw.WIDGET for uw in UsWidget.query.filter_by(UTILIZADOR=current_user.LOGIN, VISIVEL=True)}

            current_group = None
            for m in menu_items:
                mostrar = False

                # Dashboard só para quem tem widgets
                if m.tabela == "dashboard" and not user_is_admin:
                    mostrar = bool(user_widgets)
                # Monitor de Trabalho sempre visível
                elif m.tabela == "monitor":
                    mostrar = True
                # Agrupadores (ordem % 100 == 0)
                elif m.ordem % 100 == 0:
                    mostrar = False  # Só será True se algum filho for permitido (mais abaixo)
                # Todos os outros: só se tem acesso
                else:
                    mostrar = user_is_admin or perms.get(m.tabela, {}).get('consultar', False)

                # Criação do grupo ou item
                if m.ordem % 100 == 0:
                    current_group = {
                        'name': m.nome,
                        'icon': m.icone,
                        'children': [],
                        'mostrar': False,  # Só será True se algum filho for mostrado
                    }
                    menu_structure.append(current_group)
                else:
                    child = {
                        'name': m.nome,
                        'url': m.url,
                        'icon': m.icone
                    }
                    if current_group:
                        if mostrar:
                            current_group['mostrar'] = True
                            current_group['children'].append(child)
                    elif mostrar:
                        # Se não está num grupo, mete top-level
                        menu_structure.append(child)

            # Depois de montar, remove grupos sem filhos visíveis
            menu_structure = [
                g for g in menu_structure
                if not isinstance(g, dict) or g.get('mostrar', True) or (g.get('children') and len(g['children']) > 0)
            ]

        return {
            'menu_items'     : menu_items,
            'menu_structure' : menu_structure,
            'user_perms'     : perms,
            'page_name'      : page_name,
            'menu_botoes'    : menu_botoes,
            'is_dev'         : getattr(current_user, 'DEV', False) if current_user.is_authenticated else False,
            'can_open_mn'    : can_open_mn if current_user.is_authenticated else False,
            'can_open_fs'    : can_open_fs if current_user.is_authenticated else False
        }

    from sqlalchemy.sql import text

    @login_manager.user_loader
    def load_user(user_stamp):
        sql = text("""
            SELECT USSTAMP, LOGIN, NOME, EMAIL, PASSWORD, ADMIN, EQUIPA, DEV, HOME, MNADMIN, LPADMIN
            FROM US
            WHERE USSTAMP = :stamp
        """)
        row = db.session.execute(sql, {'stamp': user_stamp}).mappings().first()
        if not row:
            return None

        user = US()
        for k, v in row.items():
            setattr(user, k, v)
        return user


    # Rotas de autenticação
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            login_ = request.form['login']
            pwd = request.form['password']

            sql = text("""
                SELECT USSTAMP, LOGIN, NOME, EMAIL, PASSWORD, ADMIN, EQUIPA, DEV, HOME, MNADMIN, LPADMIN
                FROM US
                WHERE LOGIN = :login
            """)
            row = db.session.execute(sql, {'login': login_}).mappings().first()
            if row and row['PASSWORD'] == pwd:
                user = US()
                for k, v in row.items():
                    setattr(user, k, v)
                login_user(user)
                return redirect(request.args.get('next') or url_for('home_page'))

            return render_template('login.html', error='Credenciais inválidas')
        return render_template('login.html')



    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('login'))
   

    @app.route('/')
    @login_required
    def home_page():
        home = getattr(current_user, 'HOME', '').lower().strip().lstrip('/')
        print(f"HOME do utilizador: {home}")

        if home == 'dashboard':
            return redirect(url_for('dashboard_page'))
        elif home == 'monitor' or not home:
            return redirect(url_for('monitor_page'))

        return redirect(url_for('dashboard_page'))


    @app.route('/plan')
    @login_required
    def plan_page():
        return render_template('plan.html', today=date.today().isoformat())

    @app.route('/cleanings')
    @login_required
    def cleanings_page():
        return render_template('cleanings.html')

    @app.route('/cleanings/edit/<string:lpstamp>')
    @login_required
    def cleaning_edit_page(lpstamp):
        return render_template('cleaning_edit.html', lpstamp=lpstamp)

    @app.route('/dashboard')
    @login_required
    def dashboard_page():
        return render_template('dashboard.html')

    @app.route('/api/dashboard')
    @login_required
    def api_dashboard_widgets():
        user_login = current_user.LOGIN
        query = (
            db.session.query(UsWidget, Widget)
            .join(Widget, UsWidget.WIDGET == Widget.NOME)
            .filter(
                UsWidget.UTILIZADOR == user_login,
                UsWidget.VISIVEL == True,
                Widget.ATIVO == True
            )
            .order_by(UsWidget.COLUNA, UsWidget.ORDEM)
            .all()
        )
        dashboard = {1: [], 2: [], 3: []}
        for usw, widg in query:
            dashboard[usw.COLUNA].append({
                'nome': widg.NOME,
                'titulo': widg.TITULO,
                'tipo': widg.TIPO,
                'fonte': widg.FONTE,
                'config': widg.CONFIG,
                'coluna': usw.COLUNA,
                'ordem': usw.ORDEM,
                'maxheight': usw.MAXHEIGHT
            })
        return jsonify(dashboard)

    @app.route('/api/widget/analise/<nome>')
    @login_required
    def widget_analise(nome):
        # 1. Carrega o widget
        widget = Widget.query.filter_by(NOME=nome, ATIVO=True).first()
        if not widget:
            return jsonify({'error': 'Widget não encontrado'}), 404

        # 2. Lê a query do CONFIG
        try:
            config = json.loads(widget.CONFIG)
            query = config.get('query')
            if not query:
                return jsonify({'error': 'Query não definida no config'}), 400
        except Exception as e:
            return jsonify({'error': f'Config inválido: {e}'}), 400

        # 3. Executa a query via SQLAlchemy
        try:
            result = db.session.execute(text(query))
        except Exception as e:
            return jsonify({'error': f'Erro ao executar query: {e}'}), 500

        # 4. Constrói as linhas usando .mappings() para ter dicts
        mappings = result.mappings().all()
        rows = []
        for rd in mappings:
            clean = {}
            for col, val in rd.items():
                # Se for date ou datetime, passa para ISO string
                if isinstance(val, (date, datetime)):
                    clean[col] = val.strftime('%Y-%m-%d')
                else:
                    clean[col] = val
            rows.append(clean)

        # 5. Devolve colunas e linhas
        return jsonify({
            'columns': list(result.keys()),
            'rows': rows
        })

    @app.route('/modals/<acao>')
    @login_required
    def modal_generico(acao):
    # Exemplo de configuração por acao
        if acao == 'agendar_tarefa':
            campos = [
            {'nome': 'PESSOA', 'label': 'Pessoa', 'tipo': 'text'},
            {'nome': 'DATA', 'label': 'Data', 'tipo': 'date'},
            {'nome': 'HORA', 'label': 'Hora', 'tipo': 'time'},
        ]
        return render_template('dynamic_modal.html', titulo="Agendar Tarefa", campos=campos, acao="gravarTarefa()")
    

    @app.route('/generic/api/modal/<modal_nome>', methods=['GET'])
    @login_required
    def api_modal_fields(modal_nome):
        from models import Modais, CamposModal
        modal = Modais.query.filter_by(NOME=modal_nome, ATIVO=True).first()
        if not modal:
            return jsonify({'success': False, 'message': 'Modal não encontrado'}), 404

        campos = CamposModal.query.filter_by(MODAISSTAMP=modal.MODAISSTAMP).order_by(CamposModal.ORDEM).all()

        resultado = []
        for campo in campos:
            opcoes = []
            if campo.TIPO == 'COMBO' and campo.COMBO:
                try:
                    # ⚠️ use text() aqui
                    res = db.session.execute(text(campo.COMBO))
                    for r in res.fetchall():
                        # adapte se o SELECT tiver só uma coluna
                        opcoes.append([str(r[0]), str(r[1] if len(r)>1 else r[0])])
                except Exception as e:
                    print('Erro na query da combo:', e)

            resultado.append({
                'CAMPO': campo.CAMPO,
                'LABEL': campo.LABEL,
                'TIPO': campo.TIPO,
                'ORDEM': campo.ORDEM,
                'OPCOES': opcoes,
                'VALORDEFAULT': resolver_macros(campo.VALORDEFAULT)
            })

        return jsonify({'success': True, 'campos': resultado})

    @app.route('/generic/api/modal/gravar', methods=['POST'])
    @login_required
    def gravar_modal():
        dados = request.json
        nome_modal = dados.pop('__modal__', None)

        print(f"\n📥 [MODAL] A gravar modal: {nome_modal}")
        print(f"📦 Dados recebidos: {dados}")

        modal = Modais.query.filter_by(NOME=nome_modal, ATIVO=True).first()
        if not modal:
            print(f"❌ Modal '{nome_modal}' não encontrado ou inativo.")
            return jsonify(success=False, error="Modal não encontrado")

        try:
            campos = CamposModal.query.filter_by(MODAISSTAMP=modal.MODAISSTAMP).all()
            mapa = {
                c.CAMPO.upper(): (c.CAMPODESTINO or c.CAMPO)
                for c in campos
            }

            print(f"🔁 Mapeamento CAMPO → CAMPODESTINO: {mapa}")

            dados_filtrados = {
                mapa[k.upper()]: v for k, v in dados.items() if k.upper() in mapa
            }

            print(f"✅ Dados finais para INSERT na tabela {modal.TABELA}: {dados_filtrados}")

            if not dados_filtrados:
                print("⚠️ Nenhum campo corresponde ao mapping — abortado.")
                return jsonify(success=False, error="Nenhum dado válido para inserir")

            colunas = ', '.join(dados_filtrados.keys())
            marcadores = ', '.join([f':{k}' for k in dados_filtrados.keys()])
            sql = f"INSERT INTO {modal.TABELA} ({colunas}) VALUES ({marcadores})"

            print(f"📝 SQL gerado:\n{sql}")

            db.session.execute(text(sql), dados_filtrados)
            db.session.commit()
            print("✅ Inserção concluída com sucesso.")
            return jsonify(success=True)

        except Exception as e:
            db.session.rollback()
            print(f"❌ ERRO durante gravação:\n{e}")
            return jsonify(success=False, error=str(e)), 500
        

    from datetime import datetime
    from flask_login import current_user
    import uuid

    def resolver_macros(valor):
        def resolver_macros(valor):
            print(f"🧩 A resolver macro: {valor}")

        if not isinstance(valor, str):
            return valor

        hoje = datetime.today().date()
        agora = datetime.now()

        macros = {
            '{TODAY}': hoje.strftime('%d.%m.%Y'),
            '{NOW}': agora.strftime('%H:%M'),
            '{USER}': current_user.LOGIN if current_user.is_authenticated else '',
            '{USERSTAMP}': current_user.get_id() if current_user.is_authenticated else '',
            '{UUID}': str(uuid.uuid4()),
        }

        for macro, real in macros.items():
            print(f"➡️  Substituir {macro} por {real}")
            valor = valor.replace(macro, real)

        print(f"✅ Resultado final: {valor}")
        return valor


    @app.route('/api/whoami')
    @login_required
    def whoami():
        from flask import jsonify

        user_data = {
            'USSTAMP': current_user.USSTAMP,
            'LOGIN': current_user.LOGIN,
            'NOME': current_user.NOME,
            'EMAIL': current_user.EMAIL,
            'ADMIN': getattr(current_user, 'ADMIN', None),
            'DEV': getattr(current_user, 'DEV', None),
            'MNADMIN': getattr(current_user, 'MNADMIN', None),
            'LPADMIN': getattr(current_user, 'LPADMIN', None),
            'EQUIPA': getattr(current_user, 'EQUIPA', None)
        }

        return jsonify(user_data)


    @app.route('/analise/<usqlstamp>')
    @login_required
    def pagina_analise(usqlstamp):
        from models import Usql
        entry = Usql.query.filter_by(usqlstamp=usqlstamp).first()
        if not entry:
            return render_template('error.html', message='Análise não encontrada'), 404
        return render_template('analise.html', usqlstamp=usqlstamp, titulo=entry.descricao)

    @app.route('/api/analise/<usqlstamp>')
    @login_required
    def api_analise(usqlstamp):
        from models import Usql
        entry = Usql.query.filter_by(usqlstamp=usqlstamp).first()
        if not entry:
            return jsonify({'error': 'Análise não encontrada'}), 404

        try:
            result = db.session.execute(text(entry.sqlexpr))
            mappings = result.mappings().all()
            rows = []
            for rd in mappings:
                clean = {}
                for col, val in rd.items():
                    if isinstance(val, (datetime, date)):
                        clean[col] = val.strftime('%Y-%m-%d')
                    else:
                        clean[col] = val
                rows.append(clean)

            return jsonify({
                'columns': list(result.keys()),
                'rows': rows,
                'decimais': float(entry.decimais or 2),
                'totais': bool(entry.totais)
            })

        except Exception as e:
            return jsonify({'error': str(e)}), 500


    @app.route('/monitor')
    @login_required
    def monitor_page():
        return render_template('monitor.html')
    
    from sqlalchemy import text

    from flask_login import current_user

    @app.route('/newmn')
    @login_required
    def newmn():
        alojamentos = [row[0] for row in db.session.execute(text("SELECT NOME FROM AL ORDER BY 1")).fetchall()]
        users = [row[0] for row in db.session.execute(text("SELECT LOGIN FROM US ORDER BY 1")).fetchall()]
        utilizador = current_user.LOGIN
        return render_template('newmn.html', alojamentos=alojamentos, users=users, utilizador=utilizador, page_title='Manutenção')
    
    from sqlalchemy import text

    @app.route('/newfs')
    @login_required
    def newfs():
        # Ajusta os SELECTs para as tuas tabelas reais de alojamentos e utilizadores
        alojamentos = [row[0] for row in db.session.execute(text("SELECT NOME FROM AL ORDER BY 1")).fetchall()]
        users = [row[0] for row in db.session.execute(text("SELECT LOGIN FROM US ORDER BY 1")).fetchall()]
        utilizador = getattr(current_user, 'LOGIN', '')  # default seguro
        return render_template('newfs.html',
                            alojamentos=alojamentos,
                            users=users,
                            utilizador=utilizador,
                            page_title='Faltas')

    
    @app.route('/newanexo')
    @login_required
    def newanexo():
        table = request.args.get('table')
        rec = request.args.get('rec')
        if not table or not rec:
            abort(400, "Faltam parâmetros")
        return render_template('newanexo.html', table=table, rec=rec, page_title='Anexos')

    from sqlalchemy import text

    @app.route('/planner/api/imprimir_etiquetas', methods=['POST'])
    @login_required
    def imprimir_etiquetas():
        data = request.args.get('date')
        if not data:
            return jsonify({'error': 'Data em falta'}), 400

        # Inserir todos os LP com DATA = data na tabela ET
        sql = text("""
            INSERT INTO ET (LPSTAMP, TRATADO)
            SELECT LPSTAMP, 0 FROM LP WHERE DATA = :data
        """)
        try:
            db.session.execute(sql, {'data': data})
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500


    @app.route('/api/etiqueta_rapida', methods=['POST'])
    @login_required
    def criar_etiqueta_rapida():
        lpstamp = request.json.get('lpstamp')
        if not lpstamp:
            return jsonify({'error': 'LPSTAMP em falta'}), 400
        try:
            # só insere se não existir ainda
            sql = text('INSERT INTO ET (LPSTAMP, TRATADO) VALUES (:lpstamp, 0)')
            db.session.execute(sql, {'lpstamp': lpstamp})
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500


    from flask import render_template, redirect, url_for

    @app.route('/profile')
    @login_required
    def profile():
        return render_template('profile.html', user=current_user)


    @app.route('/api/profile/change_password', methods=['POST'])
    @login_required
    def change_password():
        data = request.json
        new_pwd = data.get('password', '').strip()
        if not new_pwd or len(new_pwd) < 4:
            return {'error': 'Password demasiado curta'}, 400

        from app import db  # ou usa db conforme já tens no teu projeto
        user = db.session.query(US).get(current_user.USSTAMP)
        if not user:
            return {'error': 'Utilizador não encontrado'}, 404
        user.PASSWORD = new_pwd
        db.session.commit()
        return {'success': True}

    # Monitor: lista de tarefas unificada com filtros simples
    @app.route('/generic/api/monitor_tasks')
    @app.route('/generic/api/monitor_tasks_filtered')
    @login_required
    def api_monitor_tasks():
        try:
            params = request.args or {}
            only_mine = params.get('only_mine') in ('1', 'true', 'True')
            start = params.get('start')
            end = params.get('end')
            # aceita também CSV alternativo (users, aloj, origins)
            utilizadores = params.getlist('UTILIZADOR') or ([] if params.get('UTILIZADOR') is None else [params.get('UTILIZADOR')])
            if not utilizadores and params.get('users'):
                utilizadores = [u.strip() for u in params.get('users').split(',') if u.strip() != '']
            alojamentos = params.getlist('ALOJAMENTO') or ([] if params.get('ALOJAMENTO') is None else [params.get('ALOJAMENTO')])
            if not alojamentos and params.get('aloj'):
                alojamentos = [a.strip() for a in params.get('aloj').split(',')]
            origens = params.getlist('ORIGEM') or ([] if params.get('ORIGEM') is None else [params.get('ORIGEM')])
            if not origens and params.get('origins'):
                origens = [o.strip() for o in params.get('origins').split(',')]

            # Defaults date window
            if not start:
                start = (date.today()).toordinal() - 30
                start = date.fromordinal(start).isoformat()
            if not end:
                end = (date.today()).toordinal() + 60
                end = date.fromordinal(end).isoformat()

            # Helper to get columns present in a table
            def get_columns(table_name: str):
                try:
                    rows = db.session.execute(text(
                        "SELECT UPPER(COLUMN_NAME) AS CN FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = :t"
                    ), { 't': table_name }).fetchall()
                    return { r[0] for r in rows }
                except Exception:
                    return set()

            def exists_table(table_name: str) -> bool:
                try:
                    r = db.session.execute(text(
                        "SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = :t"
                    ), { 't': table_name }).fetchone()
                    return r is not None
                except Exception:
                    return False

            # Build dynamic SELECT for each table, normalizing fields
            def build_select(table: str, origem_code: str):
                cols = get_columns(table)
                if not cols:
                    return None, {}
                # Choose STAMP
                stamp_col = next((c for c in cols if c.endswith('STAMP')), None)
                data_col = 'DATA' if 'DATA' in cols else None
                hora_col = 'HORA' if 'HORA' in cols else None
                aloj_col = 'ALOJAMENTO' if 'ALOJAMENTO' in cols else None
                user_col = 'UTILIZADOR' if 'UTILIZADOR' in cols else None
                tarefa_col = next((c for c in ('TAREFA','TITULO','ASSUNTO','DESCRICAO','DESCR') if c in cols), None)
                tratado_col = 'TRATADO' if 'TRATADO' in cols else None

                # SELECT list
                sel = [
                    f"CAST({stamp_col} AS varchar(50)) AS TAREFASSTAMP" if stamp_col else "NULL AS TAREFASSTAMP",
                    f"CAST({data_col} AS date) AS DATA" if data_col else "CAST(NULL AS date) AS DATA",
                    (f"CAST({hora_col} AS varchar(8)) AS HORA" if hora_col else "'' AS HORA"),
                    (f"ISNULL({aloj_col}, '') AS ALOJAMENTO" if aloj_col else "'' AS ALOJAMENTO"),
                    ("ISNULL(T.ORIGEM,'') AS ORIGEM" if table == 'TAREFAS' and 'ORIGEM' in cols else f"'{origem_code}' AS ORIGEM"),
                    (f"{tarefa_col} AS TAREFA" if tarefa_col else f"'{origem_code if origem_code else 'Tarefa'}' AS TAREFA"),
                    (f"ISNULL({tratado_col}, 0) AS TRATADO" if tratado_col else "0 AS TRATADO"),
                    (f"ISNULL({user_col}, '') AS UTILIZADOR" if user_col else "'' AS UTILIZADOR")
                ]
                sel_sql = ",\n                    ".join(sel)
                base = f"SELECT\n                    {sel_sql}\n                FROM {table}"
                binds = {}
                where = []
                if data_col:
                    where.append(f"{data_col} BETWEEN :start AND :end")
                    binds.update({ 'start': start, 'end': end })
                if only_mine and getattr(current_user, 'LOGIN', None) and user_col:
                    where.append(f"{user_col} = :onlymine")
                    binds['onlymine'] = current_user.LOGIN
                if where:
                    base += "\nWHERE " + " AND ".join(where)
                return base, binds

            selects = []
            binds_union = {}
            # Always try TAREFAS
            if exists_table('TAREFAS'):
                s, b = build_select('TAREFAS', '')
                if s:
                    selects.append(s)
                    binds_union.update({ f"t_{k}": v for k, v in b.items() })
                    # rename binds in SQL to unique names
                    for k in list(b.keys()):
                        s = s.replace(f":{k}", f":t_{k}")
                    selects[-1] = s
            # Optional MN/LP/FS
            for tab, code, prefix in (( 'MN','MN','m'), ('LP','LP','l'), ('FS','FS','f')):
                if exists_table(tab):
                    s, b = build_select(tab, code)
                    if s:
                        selects.append(s)
                        binds_union.update({ f"{prefix}_{k}": v for k, v in b.items() })
                        for k in list(b.keys()):
                            s = s.replace(f":{k}", f":{prefix}_{k}")
                        selects[-1] = s

            if not selects:
                return jsonify([])

            union_sql = "\nUNION ALL\n".join(selects)
            outer = f"SELECT X.*, ISNULL(U.NOME, X.UTILIZADOR) AS UTILIZADOR_NOME, '#6c757d' AS UTILIZADOR_COR\nFROM (\n{union_sql}\n) X\nLEFT JOIN US U ON U.LOGIN = X.UTILIZADOR\n"

            # Outer filters (IN lists)
            where_outer = []
            outer_bind = dict(binds_union)
            if utilizadores:
                keys = []
                for i, u in enumerate(utilizadores):
                    k = f"ou{i}"
                    outer_bind[k] = u
                    keys.append(f":{k}")
                where_outer.append("X.UTILIZADOR IN (" + ",".join(keys) + ")")
            if alojamentos:
                keys = []
                for i, a in enumerate(alojamentos):
                    k = f"oa{i}"
                    outer_bind[k] = a
                    keys.append(f":{k}")
                where_outer.append("X.ALOJAMENTO IN (" + ",".join(keys) + ")")
            if origens:
                keys = []
                for i, o in enumerate(origens):
                    k = f"oo{i}"
                    outer_bind[k] = o
                    keys.append(f":{k}")
                where_outer.append("X.ORIGEM IN (" + ",".join(keys) + ")")
            if where_outer:
                outer += "WHERE " + " AND ".join(where_outer) + "\n"
            outer += "ORDER BY X.DATA, X.HORA\n"

            base_rows = [ dict(r) for r in db.session.execute(text(outer), outer_bind).mappings().all() ]

            # Regra adicional: Se o utilizador tiver LP num alojamento num dia,
            # deve ver MN/FS desse alojamento nesse dia, mesmo de outros utilizadores.
            # 1) recolher pares (DATA, ALOJAMENTO) de LP para utilizadores selecionados (ou only_mine)
            lp_pairs = set()
            target_users = set(utilizadores)
            if only_mine and getattr(current_user, 'LOGIN', None):
                target_users.add(current_user.LOGIN)

            def add_lp_pairs_from_table(tab: str):
                cols = get_columns(tab)
                if not cols or 'DATA' not in cols or 'ALOJAMENTO' not in cols:
                    return
                where = ["DATA BETWEEN :lp_start AND :lp_end"]
                bind = { 'lp_start': start, 'lp_end': end }
                if target_users and 'UTILIZADOR' in cols:
                    ukeys = []
                    for i, u in enumerate(target_users):
                        k = f"lpu{i}"
                        bind[k] = u
                        ukeys.append(f":{k}")
                    where.append("UTILIZADOR IN (" + ",".join(ukeys) + ")")
                if alojamentos:
                    akeys = []
                    for i, a in enumerate(alojamentos):
                        k = f"lpa{i}"
                        bind[k] = a
                        akeys.append(f":{k}")
                    where.append("ISNULL(ALOJAMENTO,'') IN (" + ",".join(akeys) + ")")
                sql_lp = text(f"SELECT CAST(DATA AS date) AS DATA, ISNULL(ALOJAMENTO,'') AS ALOJAMENTO FROM {tab} WHERE " + " AND ".join(where))
                for r in db.session.execute(sql_lp, bind).fetchall():
                    lp_pairs.add((r[0].isoformat() if hasattr(r[0], 'isoformat') else str(r[0]), r[1]))

            # Prefer LP table if exists, else TAREFAS where ORIGEM='LP'
            if exists_table('LP'):
                add_lp_pairs_from_table('LP')
            elif exists_table('TAREFAS') and 'ORIGEM' in get_columns('TAREFAS'):
                # Fallback via TAREFAS
                cols = get_columns('TAREFAS')
                if 'DATA' in cols and 'ALOJAMENTO' in cols:
                    where = ["DATA BETWEEN :lp_start AND :lp_end", "ISNULL(ORIGEM,'') = 'LP'"]
                    bind = { 'lp_start': start, 'lp_end': end }
                    if target_users and 'UTILIZADOR' in cols:
                        ukeys = []
                        for i, u in enumerate(target_users):
                            k = f"lptu{i}"
                            bind[k] = u
                            ukeys.append(f":{k}")
                        where.append("UTILIZADOR IN (" + ",".join(ukeys) + ")")
                    if alojamentos:
                        akeys = []
                        for i, a in enumerate(alojamentos):
                            k = f"lpta{i}"
                            bind[k] = a
                            akeys.append(f":{k}")
                        where.append("ISNULL(ALOJAMENTO,'') IN (" + ",".join(akeys) + ")")
                    sql_lp = text("SELECT CAST(DATA AS date) AS DATA, ISNULL(ALOJAMENTO,'') AS ALOJAMENTO FROM TAREFAS WHERE " + " AND ".join(where))
                    for r in db.session.execute(sql_lp, bind).fetchall():
                        lp_pairs.add((r[0].isoformat() if hasattr(r[0], 'isoformat') else str(r[0]), r[1]))

            # 2) se houver pares LP, buscar MN e FS para esses pares (independente de utilizador)
            extra_rows = []
            if lp_pairs:
                # limita por origens selecionadas, se fornecidas; caso vazio, considera MN e FS
                target_origens = set([o for o in origens if o in ('MN','FS')]) if origens else {'MN','FS'}

                def fetch_extra_from_table(tab: str, origem_code: str):
                    if origem_code not in target_origens:
                        return
                    cols = get_columns(tab)
                    if not cols:
                        return
                    stamp_col = next((c for c in cols if c.endswith('STAMP')), None)
                    data_col = 'DATA' if 'DATA' in cols else None
                    hora_col = 'HORA' if 'HORA' in cols else None
                    aloj_col = 'ALOJAMENTO' if 'ALOJAMENTO' in cols else None
                    user_col = 'UTILIZADOR' if 'UTILIZADOR' in cols else None
                    tarefa_col = next((c for c in ('TAREFA','TITULO','ASSUNTO','DESCRICAO','DESCR') if c in cols), None)
                    if not data_col or not aloj_col:
                        return
                    pair_conditions = []
                    bind = { 'ex_start': start, 'ex_end': end }
                    idx = 0
                    for (d,a) in lp_pairs:
                        kd = f"d{idx}"; ka = f"a{idx}"; idx += 1
                        bind[kd] = d; bind[ka] = a
                        pair_conditions.append(f"({data_col} = :{kd} AND ISNULL({aloj_col},'') = :{ka})")
                    if not pair_conditions:
                        return
                    where = [f"{data_col} BETWEEN :ex_start AND :ex_end", "(" + " OR ".join(pair_conditions) + ")"]
                    sql = f"SELECT {stamp_col or 'NULL'} AS STAMP, CAST({data_col} AS date) AS DATA, " \
                          f"{('CAST('+hora_col+' AS varchar(8))' if hora_col else "''")} AS HORA, " \
                          f"ISNULL({aloj_col}, '') AS ALOJAMENTO, '{origem_code}' AS ORIGEM, " \
                          f"{(tarefa_col or "''")} AS TAREFA, {('ISNULL('+user_col+', \'\')' if user_col else "''")} AS UTILIZADOR " \
                          f"FROM {tab} WHERE " + " AND ".join(where)
                    for r in db.session.execute(text(sql), bind).mappings().all():
                        extra_rows.append({
                            'TAREFASSTAMP': r.get('STAMP'),
                            'DATA': r.get('DATA'),
                            'HORA': r.get('HORA') or '',
                            'ALOJAMENTO': r.get('ALOJAMENTO') or '',
                            'ORIGEM': origem_code,
                            'TAREFA': r.get('TAREFA') or (origem_code or 'Tarefa'),
                            'TRATADO': 0,
                            'UTILIZADOR': r.get('UTILIZADOR') or ''
                        })

                # Prefer MN/FS tables
                if exists_table('MN'):
                    fetch_extra_from_table('MN', 'MN')
                if exists_table('FS'):
                    fetch_extra_from_table('FS', 'FS')
                # Fallback: TAREFAS com ORIGEM MN/FS
                if exists_table('TAREFAS') and 'ORIGEM' in get_columns('TAREFAS'):
                    cols = get_columns('TAREFAS')
                    data_col = 'DATA' if 'DATA' in cols else None
                    hora_col = 'HORA' if 'HORA' in cols else None
                    aloj_col = 'ALOJAMENTO' if 'ALOJAMENTO' in cols else None
                    user_col = 'UTILIZADOR' if 'UTILIZADOR' in cols else None
                    tarefa_col = next((c for c in ('TAREFA','TITULO','ASSUNTO','DESCRICAO','DESCR') if c in cols), None)
                    if data_col and aloj_col:
                        pair_conditions = []
                        bind = { 'ex_start': start, 'ex_end': end }
                        idx = 0
                        for (d,a) in lp_pairs:
                            kd = f"td{idx}"; ka = f"ta{idx}"; idx += 1
                            bind[kd] = d; bind[ka] = a
                            pair_conditions.append(f"({data_col} = :{kd} AND ISNULL({aloj_col},'') = :{ka})")
                        if pair_conditions:
                            org_filter = "('MN','FS')" if not origens else "(" + ",".join([f"'{o}'" for o in target_origens]) + ")"
                            sql = f"SELECT CAST({data_col} AS date) AS DATA, {('CAST('+hora_col+' AS varchar(8))' if hora_col else "''")} AS HORA, " \
                                  f"ISNULL({aloj_col}, '') AS ALOJAMENTO, ISNULL(ORIGEM,'') AS ORIGEM, " \
                                  f"{(tarefa_col or "''")} AS TAREFA, {('ISNULL('+user_col+', \'\')' if user_col else "''")} AS UTILIZADOR " \
                                  f"FROM TAREFAS WHERE {data_col} BETWEEN :ex_start AND :ex_end AND ISNULL(ORIGEM,'') IN {org_filter} " \
                                  f"AND (" + " OR ".join(pair_conditions) + ")"
                            for r in db.session.execute(text(sql), bind).mappings().all():
                                extra_rows.append({
                                    'TAREFASSTAMP': None,
                                    'DATA': r.get('DATA'),
                                    'HORA': r.get('HORA') or '',
                                    'ALOJAMENTO': r.get('ALOJAMENTO') or '',
                                    'ORIGEM': r.get('ORIGEM') or '',
                                    'TAREFA': r.get('TAREFA') or 'Tarefa',
                                    'TRATADO': 0,
                                    'UTILIZADOR': r.get('UTILIZADOR') or ''
                                })

            # 3) juntar e eliminar duplicados por chave lógica
            seen = set()
            out = []
            def key_of(x):
                return f"{x.get('ORIGEM','')}|{x.get('DATA','')}|{x.get('HORA','')}|{x.get('ALOJAMENTO','')}|{x.get('TAREFA','')}|{x.get('UTILIZADOR','')}"
            for r in base_rows + extra_rows:
                k = key_of(r)
                if k in seen:
                    continue
                seen.add(k)
                out.append(r)
            # ordenar por data/hora
            out.sort(key=lambda r: (str(r.get('DATA') or ''), str(r.get('HORA') or '')))
            return jsonify(out)
        except Exception as e:
            return jsonify({ 'error': str(e), 'rows': [] })

    @app.route("/api/tarefa_info/<stamp>")
    @login_required
    def tarefa_info(stamp):
        result = db.session.execute(
            db.text("SELECT dbo.info_tarefa(:stamp) AS info"),
            {"stamp": stamp}
        ).fetchone()
        
        return jsonify({"info": result.info if result else ""})

    @app.route('/api/alojamentos')
    @login_required
    def api_alojamentos():
        try:
            # lightweight mode: just names, no extra queries
            basic_param = (request.args.get('basic') or '').strip().lower()
            basic = basic_param in ('1', 'true', 'yes', 'y')

            can_open = False
            try:
                q = db.session.execute(text("""
                    SELECT CONSULTAR FROM ACESSOS
                    WHERE UTILIZADOR = :u AND TABELA = 'AL'
                """), { 'u': current_user.LOGIN }).fetchone()
                can_open = bool(q[0]) if q is not None else False
            except Exception:
                can_open = False

            if basic:
                rows = db.session.execute(text(
                    """
                    SELECT NOME
                    FROM AL
                    WHERE ISNULL(INATIVO,0) = 0
                    ORDER BY NOME
                    """
                )).fetchall()
                nomes = [r[0] for r in rows if r and r[0]]
                return jsonify({ 'rows': [ { 'NOME': n } for n in nomes ], 'can_open': can_open })

            rows = db.session.execute(text(
                """
                SELECT ALSTAMP, NOME, MORADA, CODPOST, LOCAL, TIPOLOGIA, LOTACAO
                FROM AL
                WHERE ISNULL(INATIVO,0) = 0
                ORDER BY NOME
                """
            )).mappings().all()

            result = []
            for r in rows:
                d = dict(r)
                # carregar codigos (ALC) por alojamento
                try:
                    cods = db.session.execute(text(
                        """
                        SELECT CARACTERISTICA, VALOR
                        FROM ALC
                        WHERE ALOJAMENTO = :nome AND GRUPO = 'CODIGOS'
                        ORDER BY CARACTERISTICA
                        """
                    ), { 'nome': r['NOME'] }).mappings().all()
                    d['CODIGOS'] = [ dict(c) for c in cods ]
                except Exception:
                    d['CODIGOS'] = []
                result.append(d)

            return jsonify({ 'rows': result, 'can_open': can_open })
        except Exception as e:
            return jsonify({ 'error': str(e) }), 500


    return app


app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
