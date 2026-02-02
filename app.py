import os
import tempfile
import subprocess
import shutil
import pyodbc
import json
import time
import uuid
from decimal import Decimal
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import text

# Importa a instÃ¢ncia db e modelos
from models import db, US, Menu, Acessos, Widget, UsWidget, MenuBotoes, Linhas
from models import Modais, CamposModal
#from your_app_folder import db  # ou ajusta conforme a tua estrutura

login_manager = LoginManager()

def new_stamp() -> str:
    return uuid.uuid4().hex.upper()[:25]

def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    # Cache-busting para assets estÃ¡ticos (evita o browser usar JS antigo)
    app.config['STATIC_VERSION'] = int(time.time())
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        "mssql+pyodbc://sa:enterprise@hfsalves.mooo.com,50002/GESTAO"
        "?driver=ODBC+Driver+17+for+SQL+Server"
        "&TrustServerCertificate=Yes&protocol=TCP&application_name=SZERO"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    radar_conn_str = os.environ.get('RADAR_CONN_STR') or (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=hfsalves.mooo.com,50002;"
        "DATABASE=GESTAO;"
        "UID=sa;"
        "PWD=enterprise;"
        "TrustServerCertificate=Yes;"
        "Application Name=SZERO"
    )

    # Garantir JSON e respostas com UTF-8 para evitar problemas de acentuaÃ§Ã£o
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
                # acrescenta charset se nÃ£o existir
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

    # Importa e regista blueprint genÃ©rico
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
        menu_forms = {}

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

            # 2) PermissÃµes de acesso por tabela
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

            # VerificaÃ§Ã£o direta de acesso Ã  MN conforme pedido
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

            # 3) Determinar page_name e menu_botoes (igual lÃ³gica atual)
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

            # 4) Montar estrutura do menu com permissÃµes
            menu_structure = []
            user_is_admin = getattr(current_user, 'ADMIN', False)

            # Lista de widgets do user (para o dashboard)
            user_widgets = set()
            if not user_is_admin:
                user_widgets = {uw.WIDGET for uw in UsWidget.query.filter_by(UTILIZADOR=current_user.LOGIN, VISIVEL=True)}

            current_group = None
            for m in menu_items:
                mostrar = False

                # Dashboard sÃ³ para quem tem widgets
                if m.tabela == "dashboard" and not user_is_admin:
                    mostrar = bool(user_widgets)
                # Monitor de Trabalho sempre visÃ­vel
                elif m.tabela == "monitor":
                    mostrar = True
                # Agrupadores (ordem % 100 == 0)
                elif m.ordem % 100 == 0:
                    mostrar = False  # SÃ³ serÃ¡ True se algum filho for permitido (mais abaixo)
                # Todos os outros: sÃ³ se tem acesso
                else:
                    mostrar = user_is_admin or perms.get(m.tabela, {}).get('consultar', False)

                # CriaÃ§Ã£o do grupo ou item
                if m.ordem % 100 == 0:
                    current_group = {
                        'name': m.nome,
                        'icon': m.icone,
                        'children': [],
                        'mostrar': False,  # SÃ³ serÃ¡ True se algum filho for mostrado
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
                        # Se nÃ£o estÃ¡ num grupo, mete top-level
                        menu_structure.append(child)

            # Depois de montar, remove grupos sem filhos visÃ­veis
            menu_structure = [
                g for g in menu_structure
                if not isinstance(g, dict) or g.get('mostrar', True) or (g.get('children') and len(g['children']) > 0)
            ]

            menu_forms = { m.tabela: getattr(m, 'form', None) for m in menu_items }

        return {
            'menu_items'     : menu_items,
            'menu_structure' : menu_structure,
            'user_perms'     : perms,
            'page_name'      : page_name,
            'menu_botoes'    : menu_botoes,
            'menu_forms'     : menu_forms,
            'is_dev'         : getattr(current_user, 'DEV', False) if current_user.is_authenticated else False,
            'can_open_mn'    : can_open_mn if current_user.is_authenticated else False,
            'can_open_fs'    : can_open_fs if current_user.is_authenticated else False,
            'static_version' : app.config.get('STATIC_VERSION', 1)
        }

    from sqlalchemy.sql import text

    @login_manager.user_loader
    def load_user(user_stamp):
        sql = text("""
            SELECT USSTAMP, LOGIN, NOME, EMAIL, COR, PASSWORD, ADMIN, EQUIPA, DEV, HOME, MNADMIN, LPADMIN, LSADMIN, FOTO
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


    # Rotas de autenticaÃ§Ã£o
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            login_ = request.form['login']
            pwd = request.form['password']

            sql = text("""
                SELECT USSTAMP, LOGIN, NOME, EMAIL, COR, PASSWORD, ADMIN, EQUIPA, DEV, HOME, MNADMIN, LPADMIN, LSADMIN, FOTO
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

            return render_template('login.html', error='Credenciais invÃ¡lidas')
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
                'filtros': getattr(widg, 'FILTROS', '') or '',
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
            return jsonify({'error': 'Widget nÃ£o encontrado'}), 404

        # 2. LÃª a query do CONFIG
        try:
            config = json.loads(widget.CONFIG)
            query = config.get('query')
            if not query:
                return jsonify({'error': 'Query nÃ£o definida no config'}), 400
        except Exception as e:
            return jsonify({'error': f'Config invÃ¡lido: {e}'}), 400

        # 3. Executa a query via SQLAlchemy
        try:
            result = db.session.execute(text(query))
        except Exception as e:
            return jsonify({'error': f'Erro ao executar query: {e}'}), 500

        # 4. ConstrÃ³i as linhas usando .mappings() para ter dicts
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

    @app.route('/api/widgets/<widget_id>/filters/options', methods=['POST'])
    @login_required
    def widget_filter_options(widget_id):
        data = request.get_json(silent=True) or {}
        options_query = (data.get('options_query') or '').strip()
        if not options_query:
            return jsonify({'error': 'options_query em falta'}), 400

        widget = Widget.query.filter((Widget.NOME == widget_id) | (Widget.WIDGETSSTAMP == widget_id)).first()
        if not widget or not widget.ATIVO:
            return jsonify({'error': 'Widget não encontrado'}), 404

        try:
            result = db.session.execute(text(options_query))
            options = []
            for row in result:
                if hasattr(row, '_mapping'):
                    m = row._mapping
                    val = m.get('value', list(m.values())[0])
                    lab = m.get('label', val)
                else:
                    val = row[0]
                    lab = row[1] if len(row) > 1 else val
                options.append({'value': val, 'label': lab})
            return jsonify({'options': options})
        except Exception as e:
            current_app.logger.exception('Erro em widget_filter_options')
            return jsonify({'error': str(e)}), 500

    @app.route('/api/widgets/<widget_id>/run', methods=['POST'])
    @login_required
    def widget_run(widget_id):
        payload = request.get_json(silent=True) or {}
        filters = payload.get('filters') or {}

        widget = Widget.query.filter((Widget.NOME == widget_id) | (Widget.WIDGETSSTAMP == widget_id)).first()
        if not widget or not widget.ATIVO:
            return jsonify({'error': 'Widget não encontrado'}), 404

        try:
            config = json.loads(widget.CONFIG or '{}')
            query = config.get('query')
            if not query:
                return jsonify({'error': 'Query não definida no config'}), 400
        except Exception as e:
            return jsonify({'error': f'Config inválido: {e}'}), 400

        # Prepara bind params apenas para as keys presentes na query (simples heurística por prefixo :)
        bind_params = {}
        for key, val in (filters.items() if isinstance(filters, dict) else []):
            bind_params[key] = val

        try:
            result = db.session.execute(text(query), bind_params)
            mappings = result.mappings().all()
            rows = []
            for rd in mappings:
                clean = {}
                for col, val in rd.items():
                    if isinstance(val, (date, datetime)):
                        clean[col] = val.strftime('%Y-%m-%d')
                    else:
                        clean[col] = val
                rows.append(clean)
            return jsonify({'columns': list(result.keys()), 'rows': rows})
        except Exception as e:
            current_app.logger.exception('Erro ao executar widget_run')
            return jsonify({'error': f'Erro ao executar query: {e}'}), 500

    @app.route('/modals/<acao>')
    @login_required
    def modal_generico(acao):
    # Exemplo de configuraÃ§Ã£o por acao
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
            return jsonify({'success': False, 'message': 'Modal nÃ£o encontrado'}), 404

        campos = CamposModal.query.filter_by(MODAISSTAMP=modal.MODAISSTAMP).order_by(CamposModal.ORDEM).all()

        resultado = []
        for campo in campos:
            opcoes = []
            if campo.TIPO == 'COMBO' and campo.COMBO:
                try:
                    # âš ï¸ use text() aqui
                    res = db.session.execute(text(campo.COMBO))
                    for r in res.fetchall():
                        # adapte se o SELECT tiver sÃ³ uma coluna
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

        print(f"\nðŸ“¥ [MODAL] A gravar modal: {nome_modal}")
        print(f"ðŸ“¦ Dados recebidos: {dados}")

        modal = Modais.query.filter_by(NOME=nome_modal, ATIVO=True).first()
        if not modal:
            print(f"âŒ Modal '{nome_modal}' nÃ£o encontrado ou inativo.")
            return jsonify(success=False, error="Modal nÃ£o encontrado")

        try:
            campos = CamposModal.query.filter_by(MODAISSTAMP=modal.MODAISSTAMP).all()
            mapa = {
                c.CAMPO.upper(): (c.CAMPODESTINO or c.CAMPO)
                for c in campos
            }

            print(f"ðŸ” Mapeamento CAMPO â†’ CAMPODESTINO: {mapa}")

            dados_filtrados = {
                mapa[k.upper()]: v for k, v in dados.items() if k.upper() in mapa
            }

            print(f"âœ… Dados finais para INSERT na tabela {modal.TABELA}: {dados_filtrados}")

            if not dados_filtrados:
                print("âš ï¸ Nenhum campo corresponde ao mapping â€” abortado.")
                return jsonify(success=False, error="Nenhum dado vÃ¡lido para inserir")

            colunas = ', '.join(dados_filtrados.keys())
            marcadores = ', '.join([f':{k}' for k in dados_filtrados.keys()])
            sql = f"INSERT INTO {modal.TABELA} ({colunas}) VALUES ({marcadores})"

            print(f"ðŸ“ SQL gerado:\n{sql}")

            db.session.execute(text(sql), dados_filtrados)
            db.session.commit()
            print("âœ… InserÃ§Ã£o concluÃ­da com sucesso.")
            return jsonify(success=True)

        except Exception as e:
            db.session.rollback()
            print(f"âŒ ERRO durante gravaÃ§Ã£o:\n{e}")
            return jsonify(success=False, error=str(e)), 500
        

    from datetime import datetime
    from flask_login import current_user
    import uuid

    def resolver_macros(valor):
        def resolver_macros(valor):
            print(f"ðŸ§© A resolver macro: {valor}")

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
            print(f"âž¡ï¸  Substituir {macro} por {real}")
            valor = valor.replace(macro, real)

        print(f"âœ… Resultado final: {valor}")
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
            'COR': getattr(current_user, 'COR', None),
            'ADMIN': getattr(current_user, 'ADMIN', None),
            'DEV': getattr(current_user, 'DEV', None),
            'MNADMIN': getattr(current_user, 'MNADMIN', None),
            'LSADMIN': getattr(current_user, 'LSADMIN', None),
            'LPADMIN': getattr(current_user, 'LPADMIN', None),
            'EQUIPA': getattr(current_user, 'EQUIPA', None),
            'FOTO': getattr(current_user, 'FOTO', None)
        }

        return jsonify(user_data)


    @app.route('/analise/<usqlstamp>')
    @login_required
    def pagina_analise(usqlstamp):
        from models import Usql
        entry = Usql.query.filter_by(usqlstamp=usqlstamp).first()
        if not entry:
            return render_template('error.html', message='AnÃ¡lise nÃ£o encontrada'), 404
        return render_template('analise.html', usqlstamp=usqlstamp, titulo=entry.descricao)

    @app.route('/api/analise/<usqlstamp>')
    @login_required
    def api_analise(usqlstamp):
        from models import Usql
        entry = Usql.query.filter_by(usqlstamp=usqlstamp).first()
        if not entry:
            return jsonify({'error': 'AnÃ¡lise nÃ£o encontrada'}), 404

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

    @app.route('/posicoes_pesquisas')
    @login_required
    def posicoes_pesquisas_alias():
        return redirect(url_for('pesquisas_posicoes_page'))

    @app.route('/pesquisas/posicoes')
    @login_required
    def pesquisas_posicoes_page():
        return render_template('posicoes_pesquisas.html', page_title='Posições de Pesquisas')

    @app.route('/api/pesquisas/posicoes')
    @login_required
    def api_pesquisas_posicoes():
        sql_blocos = """
DECLARE @Hoje date = CAST(GETDATE() AS date);
DECLARE @DataInicio date = @Hoje;
DECLARE @DataFim    date = DATEADD(day, 30, @Hoje);

;WITH
Aloj AS (
    SELECT
        al.nome as CCUSTO,
        al.TIPO,
        al.NMAIRBNB
    FROM dbo.AL al
    WHERE 1=1
      AND ISNULL(al.FECHADO, 0) = 0
),
Cal AS (
    SELECT @DataInicio AS [DATA]
    UNION ALL
    SELECT DATEADD(day, 1, [DATA])
    FROM Cal
    WHERE [DATA] < @DataFim
),
Occ AS (
    SELECT DISTINCT
        v.CCUSTO,
        CAST(v.[DATA] AS date) AS [DATA]
    FROM dbo.v_diario_all v
    WHERE v.[DATA] BETWEEN @DataInicio AND @DataFim
      AND ISNULL(v.VALOR, 0) <> 0  -- ignorar check-out (VALOR=0)
),
Livres AS (
    SELECT
        a.CCUSTO,
        a.TIPO,
        a.NMAIRBNB,
        c.[DATA]
    FROM Aloj a
    CROSS JOIN Cal c
    LEFT JOIN Occ o
      ON o.CCUSTO = a.CCUSTO
     AND o.[DATA] = c.[DATA]
    WHERE o.CCUSTO IS NULL
),
LivresComGrupo AS (
    SELECT
        CCUSTO,
        TIPO,
        NMAIRBNB,
        [DATA],
        DATEADD(day, -ROW_NUMBER() OVER (PARTITION BY CCUSTO ORDER BY [DATA]), [DATA]) AS grp
    FROM Livres
),
LivresValidas AS (
    SELECT
        l.CCUSTO,
        l.TIPO,
        l.NMAIRBNB,
        l.[DATA],
        l.grp
    FROM LivresComGrupo l
    JOIN (
        SELECT CCUSTO, grp
        FROM LivresComGrupo
        GROUP BY CCUSTO, grp
        HAVING COUNT(*) >= 2
    ) g
      ON g.CCUSTO = l.CCUSTO
     AND g.grp    = l.grp
    WHERE
        DATEDIFF(day, @Hoje, l.[DATA]) BETWEEN 0 AND 30
),
Blocos AS (
    SELECT
        CCUSTO,
        TIPO,
        NMAIRBNB,
        MIN([DATA]) AS DataInicio,
        MAX([DATA]) AS DataFim,
        COUNT(*) AS Noites
    FROM LivresValidas
    GROUP BY CCUSTO, TIPO, NMAIRBNB, grp
)
SELECT
    b.CCUSTO,
    b.TIPO,
    b.NMAIRBNB,
    b.DataInicio,
    b.DataFim,
    b.Noites
FROM Blocos b
ORDER BY b.CCUSTO, b.DataInicio
OPTION (MAXRECURSION 32767);
        """

        sql_pesquisas = """
DECLARE @Hoje date = CAST(GETDATE() AS date);
DECLARE @DataInicio date = @Hoje;
DECLARE @DataFim    date = DATEADD(day, 30, @Hoje);

SELECT
    PESQUISASSTAMP,
    CCUSTO,
    DATA,
    NOITES,
    HOSPEDES,
    DTPESQUISA,
    PAGINA,
    POSICAO
FROM PESQUISAS
WHERE DATA BETWEEN @DataInicio AND @DataFim
ORDER BY CCUSTO, DATA, DTPESQUISA DESC;
        """

        blocos = []
        pesquisas = []
        try:
            with pyodbc.connect(radar_conn_str) as conn:
                cur = conn.cursor()
                cur.execute(sql_blocos)
                cols = [c[0] for c in cur.description]
                for raw in cur.fetchall():
                    entry = {}
                    for col_name, val in zip(cols, raw):
                        if isinstance(val, (datetime, date)):
                            entry[col_name] = val.isoformat()
                        else:
                            entry[col_name] = val
                    blocos.append(entry)

                cur.execute(sql_pesquisas)
                cols2 = [c[0] for c in cur.description]
                for raw in cur.fetchall():
                    entry = {}
                    for col_name, val in zip(cols2, raw):
                        if isinstance(val, (datetime, date)):
                            entry[col_name] = val.isoformat()
                        else:
                            entry[col_name] = val
                    pesquisas.append(entry)
        except Exception:
            try:
                app.logger.exception("Erro ao carregar posições de pesquisas")
            except Exception:
                pass
            return jsonify({"error": "Não foi possível carregar os dados"}), 500

        return jsonify({"blocks": blocos, "pesquisas": pesquisas})

    @app.route('/api/pesquisas/posicoes/<stamp>', methods=['DELETE'])
    @login_required
    def api_pesquisas_posicoes_delete(stamp):
        if not stamp:
            return jsonify({"error": "stamp obrigatório"}), 400
        try:
            with pyodbc.connect(radar_conn_str) as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM PESQUISAS WHERE PESQUISASSTAMP = ?", stamp)
                conn.commit()
        except Exception:
            try:
                app.logger.exception("Erro ao eliminar pesquisa")
            except Exception:
                pass
            return jsonify({"error": "Não foi possível eliminar"}), 500
        return jsonify({"ok": True})

    @app.route('/api/pesquisas/posicoes/<stamp>/relaunch', methods=['POST'])
    @login_required
    def api_pesquisas_posicoes_relaunch(stamp):
        if not stamp:
            return jsonify({"error": "stamp obrigatório"}), 400
        try:
            with pyodbc.connect(radar_conn_str) as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT CCUSTO, DATA, NOITES, HOSPEDES, NMAIRBNB
                    FROM PESQUISAS
                    WHERE PESQUISASSTAMP = ?
                """, stamp)
                row = cur.fetchone()
                if not row:
                    return jsonify({"error": "Pesquisa não encontrada"}), 404
                ccusto, data_val, noites_val, hosp_val, nmairbnb = row
                novo_stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")[:25]
                cur.execute("""
                    INSERT INTO PESQUISAS
                        (PESQUISASSTAMP, CCUSTO, DATA, DTPESQUISA, NOITES, HOSPEDES, PAGINA, POSICAO, NMAIRBNB)
                    VALUES
                        (?, ?, ?, CAST(GETDATE() AS date), ?, ?, 0, 0, ?)
                """, novo_stamp, ccusto, data_val, noites_val, hosp_val, nmairbnb)
                conn.commit()
        except Exception:
            try:
                app.logger.exception("Erro ao relançar pesquisa")
            except Exception:
                pass
            return jsonify({"error": "Não foi possível relançar"}), 500
        return jsonify({"ok": True, "stamp": novo_stamp})

    @app.route('/api/pesquisas/posicoes', methods=['POST'])
    @login_required
    def api_pesquisas_posicoes_insert():
        payload = request.get_json(silent=True) or {}
        ccusto = (payload.get('ccusto') or '').strip()
        data_inicio = payload.get('data')
        noites = payload.get('noites')
        hospedes = payload.get('hospedes')
        nmairbnb = (payload.get('nmairbnb') or '').strip()

        if not ccusto or not data_inicio or not noites:
            return jsonify({"error": "ccusto, data e noites são obrigatórios"}), 400

        try:
            noites_int = int(noites)
            if noites_int < 1:
                noites_int = 1
        except Exception:
            noites_int = 1

        try:
            hospedes_int = int(hospedes or 2)
            if hospedes_int < 1:
                hospedes_int = 2
        except Exception:
            hospedes_int = 2

        try:
            data_obj = datetime.fromisoformat(data_inicio).date()
        except Exception:
            return jsonify({"error": "Data inválida"}), 400

        stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")[:25]
        insert_sql = """
INSERT INTO PESQUISAS
    (PESQUISASSTAMP, CCUSTO, DATA, DTPESQUISA, NOITES, HOSPEDES, PAGINA, POSICAO, NMAIRBNB)
VALUES
    (?, ?, ?, CAST(GETDATE() AS date), ?, ?, 0, 0, ?);
        """

        try:
            with pyodbc.connect(radar_conn_str) as conn:
                cur = conn.cursor()
                cur.execute(insert_sql, stamp, ccusto, data_obj, str(noites_int), hospedes_int, nmairbnb)
                conn.commit()
        except Exception:
            try:
                app.logger.exception("Erro ao inserir pesquisa para posição")
            except Exception:
                pass
            return jsonify({"error": "Não foi possível registar a pesquisa"}), 500

        return jsonify({"ok": True, "stamp": stamp})

    @app.route('/radar')
    @login_required
    def radar_page():
        radar_rows = []
        radar_error = None
        radar_sql = """
/*  RADAR (1 linha por alojamento)
    - HOJE+1 até HOJE+30
    - Noites livres = noites que NÃO existem em v_diario_all (por CCUSTO, DATA)
    - Só conta livres vendáveis: blocos consecutivos com >= 2 noites
    - Métricas por alojamento:
        Livres_D7, Livres_D14, Livres_D30
        Pressao_D7, Pressao_D14, Pressao_D30
        ADR_60d (média VALOR>0 últimos 60 dias; fallback = média global 60d)
        Sugestão de Ação (prioriza risco D7)
*/

DECLARE @Hoje date = CAST(GETDATE() AS date);
DECLARE @DataInicio date = DATEADD(day, 1, @Hoje);
DECLARE @DataFim    date = DATEADD(day, 30, @Hoje);

;WITH
Aloj AS (
    SELECT
        al.nome as CCUSTO,
        al.TIPO
    FROM dbo.AL al
    WHERE 1=1
      -- aplica aqui os teus filtros (fechados/inativos)
      AND ISNULL(al.FECHADO, 0) = 0
      -- AND ISNULL(al.ATIVO, 1) = 1
),
Cal AS (
    SELECT @DataInicio AS [DATA]
    UNION ALL
    SELECT DATEADD(day, 1, [DATA])
    FROM Cal
    WHERE [DATA] < @DataFim
),
Occ AS (
    -- ocupadas = existem na view
    SELECT DISTINCT
        v.CCUSTO,
        CAST(v.[DATA] AS date) AS [DATA]
    FROM dbo.v_diario_all v
    WHERE v.[DATA] BETWEEN @DataInicio AND @DataFim
),
Livres AS (
    -- livres = (alojamento x calendário) sem registo em Occ
    SELECT
        a.CCUSTO,
        a.TIPO,
        c.[DATA]
    FROM Aloj a
    CROSS JOIN Cal c
    LEFT JOIN Occ o
      ON o.CCUSTO = a.CCUSTO
     AND o.[DATA] = c.[DATA]
    WHERE o.CCUSTO IS NULL
),
LivresComGrupo AS (
    -- ilhas de livres consecutivas
    SELECT
        CCUSTO,
        TIPO,
        [DATA],
        DATEADD(day, -ROW_NUMBER() OVER (PARTITION BY CCUSTO ORDER BY [DATA]), [DATA]) AS grp
    FROM Livres
),
LivresValidas AS (
    -- só blocos com >= 2 noites; e já com bucket temporal
    SELECT
        l.CCUSTO,
        l.TIPO,
        l.[DATA],
        DATEDIFF(day, @Hoje, l.[DATA]) AS Dias_Ate,
        CASE
            WHEN DATEDIFF(day, @Hoje, l.[DATA]) BETWEEN 1 AND 7  THEN 'D7'
            WHEN DATEDIFF(day, @Hoje, l.[DATA]) BETWEEN 8 AND 14 THEN 'D14'
            WHEN DATEDIFF(day, @Hoje, l.[DATA]) BETWEEN 15 AND 30 THEN 'D30'
        END AS Janela
    FROM LivresComGrupo l
    JOIN (
        SELECT CCUSTO, grp
        FROM LivresComGrupo
        GROUP BY CCUSTO, grp
        HAVING COUNT(*) >= 2
    ) g
      ON g.CCUSTO = l.CCUSTO
     AND g.grp    = l.grp
    WHERE
        DATEDIFF(day, @Hoje, l.[DATA]) BETWEEN 1 AND 30
),
LivresAgg AS (
    SELECT
        CCUSTO,
        TIPO,
        SUM(CASE WHEN Janela = 'D7'  THEN 1 ELSE 0 END)  AS Livres_D7,
        SUM(CASE WHEN Janela = 'D14' THEN 1 ELSE 0 END)  AS Livres_D14,
        SUM(CASE WHEN Janela = 'D30' THEN 1 ELSE 0 END)  AS Livres_D30
    FROM LivresValidas
    GROUP BY CCUSTO, TIPO
),
ADR_Aloj_60d AS (
    SELECT
        v.CCUSTO,
        AVG(CAST(v.VALOR AS decimal(18,6))) AS ADR_60d
    FROM dbo.v_diario_all v
    WHERE v.[DATA] >= DATEADD(day, -60, @Hoje)
      AND v.[DATA] <  @Hoje
      AND v.VALOR IS NOT NULL
      AND v.VALOR > 0
    GROUP BY v.CCUSTO
),
ADR_Portfolio_60d AS (
    SELECT
        AVG(CAST(v.VALOR AS decimal(18,6))) AS ADR_Portfolio_60d
    FROM dbo.v_diario_all v
    WHERE v.[DATA] >= DATEADD(day, -60, @Hoje)
      AND v.[DATA] <  @Hoje
      AND v.VALOR IS NOT NULL
      AND v.VALOR > 0
),
Base AS (
    SELECT
        a.CCUSTO AS Alojamento,
        a.TIPO,
        ISNULL(l.Livres_D7,  0) AS Livres_D7,
        ISNULL(l.Livres_D14, 0) AS Livres_D14,
        ISNULL(l.Livres_D30, 0) AS Livres_D30,
        CAST(1.0 * ISNULL(l.Livres_D7,  0) / 7.0  AS decimal(10,4)) AS Pressao_D7,
        CAST(1.0 * ISNULL(l.Livres_D14, 0) / 7.0  AS decimal(10,4)) AS Pressao_D14,
        CAST(1.0 * ISNULL(l.Livres_D30, 0) / 16.0 AS decimal(10,4)) AS Pressao_D30,
        COALESCE(adr.ADR_60d, p.ADR_Portfolio_60d) AS ADR_Usado_60d,
        p.ADR_Portfolio_60d
    FROM Aloj a
    LEFT JOIN LivresAgg l
      ON l.CCUSTO = a.CCUSTO
    LEFT JOIN ADR_Aloj_60d adr
      ON adr.CCUSTO = a.CCUSTO
    CROSS JOIN ADR_Portfolio_60d p
)
SELECT
    Alojamento,
    TIPO,
    Livres_D7,
    Livres_D14,
    Livres_D30,
    Pressao_D7,
    Pressao_D14,
    Pressao_D30,
    ADR_Usado_60d,
    ADR_Portfolio_60d,
    CAST((ADR_Usado_60d / NULLIF(ADR_Portfolio_60d,0)) - 1 AS decimal(10,4)) AS Desvio_ADR,
    CASE
        WHEN Pressao_D7 >= 0.40 AND ADR_Usado_60d >= ADR_Portfolio_60d
            THEN 'Urgente: baixar preco / abrir regras (D7)'
        WHEN Pressao_D7 >= 0.40
            THEN 'Urgente: mexer em regras/anuncio (D7)'
        WHEN Pressao_D14 >= 0.50 AND ADR_Usado_60d >= ADR_Portfolio_60d
            THEN 'Ajuste: preco ligeiro / min nights (D14)'
        WHEN Pressao_D14 >= 0.50
            THEN 'Ajuste: monitorizar + regras (D14)'
        WHEN Pressao_D30 >= 0.60
            THEN 'Atencao: comecar a trabalhar D30'
        ELSE 'OK'
    END AS Acao
FROM Base
ORDER BY
    CASE
        WHEN Pressao_D7  >= 0.40 THEN 1
        WHEN Pressao_D14 >= 0.50 THEN 2
        WHEN Pressao_D30 >= 0.60 THEN 3
        ELSE 4
    END,
    Pressao_D7 DESC,
    Pressao_D14 DESC,
    Pressao_D30 DESC,
    Alojamento
OPTION (MAXRECURSION 32767);
        """

        try:
            with pyodbc.connect(radar_conn_str) as conn:
                cur = conn.cursor()
                cur.execute(radar_sql)
                cols = [c[0] for c in cur.description]
                for raw in cur.fetchall():
                    row = {}
                    for col_name, val in zip(cols, raw):
                        if isinstance(val, Decimal):
                            row[col_name] = float(val)
                        elif isinstance(val, (datetime, date)):
                            row[col_name] = val.isoformat()
                        else:
                            row[col_name] = val
                    radar_rows.append(row)
        except Exception:
            radar_error = "Não foi possível carregar o radar neste momento. Tenta novamente em breve."
            try:
                app.logger.exception("Erro ao obter dados do Radar de Atenção")
            except Exception:
                pass

        status_code = 500 if radar_error else 200
        return render_template(
            'radar.html',
            page_title='Radar de Atenção',
            radar_rows=radar_rows,
            radar_error=radar_error
        ), status_code

    @app.route('/mapa-gestao')
    @login_required
    def mapa_gestao_page():
        return render_template('mapa_gestao.html', page_title='Mapa de Gestao', ano_atual=date.today().year)

    @app.route('/mapa-controlo')
    @login_required
    def mapa_controlo_page():
        hoje = date.today()
        return render_template(
            'mapa_controlo.html',
            page_title='Mapa de Controlo',
            ano_atual=hoje.year,
            mes_atual=hoje.month
        )

    @app.route('/orcamento')
    @login_required
    def orcamento_page():
        return render_template('orcamento.html', page_title='Orçamento', ano_atual=date.today().year)

    @app.route('/api/orcamento')
    @login_required
    def api_orcamento_get():
        try:
            ano = request.args.get('ano', type=int) or date.today().year
        except Exception:
            ano = date.today().year

        try:
            fam_rows = db.session.execute(text("SELECT ref, nome FROM v_stfami ORDER BY ref")).fetchall()
        except Exception as e:
            return jsonify({'error': f'Erro ao obter familias: {e}'}), 500

        def level_from_ref(ref: str) -> int:
            try:
                return ref.count('.') + 1
            except Exception:
                return 1

        def sort_key(ref: str):
            parts = []
            for p in str(ref or '').split('.'):
                try:
                    parts.append(int(p))
                except Exception:
                    parts.append(p)
            return parts

        def is_prov_ref(rf: str) -> bool:
            try:
                return str(rf or '').strip().startswith('9')
            except Exception:
                return False

        familias_map = {}
        for r in fam_rows:
            ref = str(r[0]).strip() if r and r[0] is not None else ''
            if not ref:
                continue
            if is_prov_ref(ref):
                continue  # orçamento só de custos
            nome = r[1] if len(r) > 1 else ''
            nivel = level_from_ref(ref)
            familias_map[ref] = {
                'ref': ref,
                'nome': nome,
                'nivel': nivel,
                'editable': False,
                'meses': [0.0] * 12
            }

        # Apenas famílias de movimento (folhas) são editáveis:
        # - se existir 3 níveis num ramo => nível 3 (folha)
        # - se existir 2 níveis num ramo => nível 2 (folha)
        # - se existir 1 nível => nível 1 (folha)
        parents = set()
        for ref in familias_map.keys():
            parts = ref.split('.')
            if len(parts) <= 1:
                continue
            # marca todos os prefixos como pais
            for i in range(1, len(parts)):
                parents.add('.'.join(parts[:i]))
        for ref, f in familias_map.items():
            f['editable'] = (ref not in parents)

        # carregar valores existentes
        try:
            oc_rows = db.session.execute(
                text("SELECT FAMILIA, MES, VALOR FROM OC WHERE ANO = :ano"),
                {'ano': ano}
            ).fetchall()
        except Exception as e:
            return jsonify({'error': f'Erro ao obter orçamento (OC): {e}'}), 500

        for r in oc_rows:
            fam = str(r[0]).strip() if r[0] is not None else ''
            try:
                mes = int(r[1])
            except Exception:
                mes = 0
            val = float(r[2] or 0)
            if not fam or mes < 1 or mes > 12:
                continue
            node = familias_map.get(fam)
            if node is None:
                # se existir orçamento para família não mapeada, ignora
                continue
            node['meses'][mes - 1] = round(val, 2)

        # agrega para pais (mostrar totais por nível, mas só folhas editáveis gravam)
        # regra: pais = soma dos filhos diretos (bottom-up)
        refs_sorted = sorted(familias_map.keys(), key=lambda x: (familias_map[x]['nivel'], sort_key(x)), reverse=True)
        for ref in refs_sorted:
            node = familias_map[ref]
            if node.get('editable'):
                continue
            prefix = ref + '.'
            children = [c for c in familias_map.keys() if c.startswith(prefix) and familias_map[c]['nivel'] == node['nivel'] + 1]
            if not children:
                continue
            for m in range(12):
                node['meses'][m] = round(sum(float(familias_map[c]['meses'][m] or 0) for c in children), 2)

        familias_lista = []
        for ref in sorted(familias_map.keys(), key=sort_key):
            f = familias_map[ref]
            meses = [round(float(v or 0), 2) for v in f['meses']]
            familias_lista.append({
                'ref': f['ref'],
                'nome': f.get('nome', ''),
                'nivel': int(f.get('nivel') or 1),
                'editable': bool(f.get('editable')),
                'meses': meses
            })

        return jsonify({'ano': ano, 'editable_rule': 'leaf', 'familias': familias_lista})

    @app.route('/api/orcamento/batch', methods=['POST'])
    @login_required
    def api_orcamento_batch():
        try:
            body = request.get_json(silent=True) or {}
            try:
                ano = int(body.get('ano') or date.today().year)
            except Exception:
                ano = date.today().year
            updates = body.get('updates') or []
            if not isinstance(updates, list) or not updates:
                return jsonify({'ok': True, 'updated': 0})

            updated = 0
            for u in updates[:500]:
                fam = str(u.get('familia') or '').strip()
                try:
                    mes = int(u.get('mes') or 0)
                except Exception:
                    mes = 0
                try:
                    valor = float(u.get('valor') or 0)
                except Exception:
                    valor = 0.0
                if not fam or mes < 1 or mes > 12:
                    continue

                # find existing
                row = db.session.execute(
                    text("SELECT TOP 1 OCSTAMP FROM OC WHERE ANO=:ano AND MES=:mes AND FAMILIA=:fam"),
                    {'ano': ano, 'mes': mes, 'fam': fam}
                ).fetchone()
                if row and row[0]:
                    db.session.execute(
                        text("UPDATE OC SET VALOR=:valor WHERE OCSTAMP=:id"),
                        {'valor': valor, 'id': row[0]}
                    )
                else:
                    new_id_row = db.session.execute(text("SELECT LEFT(CONVERT(varchar(36), NEWID()), 25)")).fetchone()
                    oc_id = new_id_row[0]
                    db.session.execute(
                        text("INSERT INTO OC (OCSTAMP, ANO, MES, FAMILIA, VALOR) VALUES (:id,:ano,:mes,:fam,:valor)"),
                        {'id': oc_id, 'ano': ano, 'mes': mes, 'fam': fam, 'valor': valor}
                    )
                updated += 1
            db.session.commit()
            return jsonify({'ok': True, 'updated': updated})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    @app.route('/api/mapa_controlo')
    @login_required
    def api_mapa_controlo():
        try:
            ano = request.args.get('ano', type=int) or date.today().year
        except Exception:
            ano = date.today().year
        try:
            mes = request.args.get('mes', type=int) or date.today().month
        except Exception:
            mes = date.today().month
        if mes < 1 or mes > 12:
            mes = date.today().month

        sql = text("""
            SELECT
                LTRIM(RTRIM(C.CCUSTO)) AS CCUSTO,
                SUM(CASE WHEN LEFT(LTRIM(RTRIM(C.FAMILIA)), 1) = '9' THEN ISNULL(C.TOTAL,0) ELSE 0 END) AS PROVEITO,
                SUM(CASE WHEN LEFT(LTRIM(RTRIM(C.FAMILIA)), 1) <> '9' AND LTRIM(RTRIM(C.REF)) = 'RENDA' THEN ISNULL(C.TOTAL,0) ELSE 0 END) AS RENDAS,
                SUM(CASE WHEN LEFT(LTRIM(RTRIM(C.FAMILIA)), 1) <> '9' AND LTRIM(RTRIM(C.REF)) IN ('LUZ-6','LUZ-23') THEN ISNULL(C.TOTAL,0) ELSE 0 END) AS LUZ,
                SUM(CASE WHEN LEFT(LTRIM(RTRIM(C.FAMILIA)), 1) <> '9' AND LTRIM(RTRIM(C.REF)) IN ('AGUA','SANEAMENTO') THEN ISNULL(C.TOTAL,0) ELSE 0 END) AS AGUA,
                SUM(CASE WHEN LEFT(LTRIM(RTRIM(C.FAMILIA)), 1) <> '9' AND LTRIM(RTRIM(C.REF)) = 'COMUNICACOES' THEN ISNULL(C.TOTAL,0) ELSE 0 END) AS COMUNICACOES,
                SUM(CASE
                      WHEN LEFT(LTRIM(RTRIM(C.FAMILIA)), 1) <> '9'
                       AND NOT (
                          LTRIM(RTRIM(C.REF)) = 'RENDA'
                          OR LTRIM(RTRIM(C.REF)) IN ('LUZ-6','LUZ-23')
                          OR LTRIM(RTRIM(C.REF)) IN ('AGUA','SANEAMENTO')
                          OR LTRIM(RTRIM(C.REF)) = 'COMUNICACOES'
                       )
                      THEN ISNULL(C.TOTAL,0)
                      ELSE 0
                END) AS OUTROS
            FROM v_custo C
            INNER JOIN AL a
              ON LTRIM(RTRIM(a.CCUSTO)) COLLATE SQL_Latin1_General_CP1_CI_AI
               = LTRIM(RTRIM(C.CCUSTO)) COLLATE SQL_Latin1_General_CP1_CI_AI
            WHERE YEAR(C.DATA) = :ano
              AND MONTH(C.DATA) = :mes
              AND UPPER(LTRIM(RTRIM(ISNULL(a.TIPO,'')))) = 'EXPLORACAO'
            GROUP BY LTRIM(RTRIM(C.CCUSTO))
            ORDER BY LTRIM(RTRIM(C.CCUSTO))
        """)
        try:
            rows = db.session.execute(sql, {'ano': ano, 'mes': mes}).mappings().all()
        except Exception as e:
            return jsonify({'error': f'Erro ao obter mapa controlo: {e}'}), 500

        out_rows = []
        totals = {
            'ccusto': 'TOTAL',
            'proveito': 0.0,
            'rendas': 0.0,
            'luz': 0.0,
            'agua': 0.0,
            'comunicacoes': 0.0,
            'outros': 0.0,
            'total_custos': 0.0,
            'saldo': 0.0
        }
        for r in rows:
            ccusto = (r.get('CCUSTO') or '').strip()
            proveito = float(r.get('PROVEITO') or 0)
            rendas = float(r.get('RENDAS') or 0)
            luz = float(r.get('LUZ') or 0)
            agua = float(r.get('AGUA') or 0)
            comunic = float(r.get('COMUNICACOES') or 0)
            outros = float(r.get('OUTROS') or 0)
            total_custos = rendas + luz + agua + comunic + outros
            saldo = proveito - total_custos
            out_rows.append({
                'ccusto': ccusto,
                'proveito': round(proveito, 2),
                'rendas': round(rendas, 2),
                'luz': round(luz, 2),
                'agua': round(agua, 2),
                'comunicacoes': round(comunic, 2),
                'outros': round(outros, 2),
                'total_custos': round(total_custos, 2),
                'saldo': round(saldo, 2)
            })
            totals['proveito'] += proveito
            totals['rendas'] += rendas
            totals['luz'] += luz
            totals['agua'] += agua
            totals['comunicacoes'] += comunic
            totals['outros'] += outros

        totals['total_custos'] = totals['rendas'] + totals['luz'] + totals['agua'] + totals['comunicacoes'] + totals['outros']
        totals['saldo'] = totals['proveito'] - totals['total_custos']
        for k in ('proveito','rendas','luz','agua','comunicacoes','outros','total_custos','saldo'):
            totals[k] = round(float(totals[k] or 0), 2)

        return jsonify({
            'ano': ano,
            'mes': mes,
            'rows': out_rows,
            'totals': totals
        })

    @app.route('/api/mapa_gestao/ccustos')
    @login_required
    def api_mapa_gestao_ccustos():
        try:
            rows = db.session.execute(text("""
                SELECT c.CCUSTO, ISNULL(a.TIPO,'') AS TIPO
                FROM v_cct c
                LEFT JOIN AL a
                  ON LTRIM(RTRIM(a.CCUSTO)) COLLATE SQL_Latin1_General_CP1_CI_AI
                   = LTRIM(RTRIM(c.CCUSTO)) COLLATE SQL_Latin1_General_CP1_CI_AI
                ORDER BY ISNULL(a.TIPO,''), c.CCUSTO
            """)).fetchall()
            opts = []
            for r in rows:
                cc = r[0] if len(r) > 0 else None
                tipo = r[1] if len(r) > 1 else ''
                if cc is None:
                    continue
                opts.append({'ccusto': cc, 'tipo': tipo})
            return jsonify({'options': opts})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/mapa_gestao')
    @login_required
    def api_mapa_gestao():
        try:
            ano = request.args.get('ano', type=int) or date.today().year
        except Exception:
            ano = date.today().year

        ccustos_raw = (request.args.get('ccustos') or '').strip()
        ccustos = [c.strip() for c in ccustos_raw.split(',') if c.strip()]

        try:
            fam_rows = db.session.execute(text("SELECT ref, nome FROM v_stfami ORDER BY ref")).fetchall()
        except Exception as e:
            return jsonify({'error': f'Erro ao obter familias: {e}'}), 500

        def level_from_ref(ref: str) -> int:
            try:
                return ref.count('.') + 1
            except Exception:
                return 1

        familias_map = {}
        for r in fam_rows:
            ref = str(r[0]).strip() if r and r[0] is not None else ''
            if not ref:
                continue
            nome = r[1] if len(r) > 1 else ''
            familias_map[ref] = {
                'ref': ref,
                'nome': nome,
                'nivel': level_from_ref(ref),
                'meses': [0.0] * 12,
                'total': 0.0,
                'orc_meses': [0.0] * 12,
                'orc_total': 0.0,
            }

        def ensure_node(ref: str):
            if ref not in familias_map:
                familias_map[ref] = {
                    'ref': ref,
                    'nome': ref,
                    'nivel': level_from_ref(ref),
                    'meses': [0.0] * 12,
                    'total': 0.0,
                    'orc_meses': [0.0] * 12,
                    'orc_total': 0.0,
                }

        def is_prov_ref(rf: str) -> bool:
            try:
                return str(rf or '').strip().startswith('9')
            except Exception:
                return False

        # Custos por familia/mes
        where_parts = ["YEAR(DATA) = :ano"]
        params = {'ano': ano}
        if ccustos:
            keys = []
            for idx, cc in enumerate(ccustos):
                k = f"c{idx}"
                params[k] = cc
                keys.append(f":{k}")
            where_parts.append("CCUSTO IN (" + ",".join(keys) + ")")

        where_sql = " AND ".join(where_parts)
        custos_sql = f"""
            SELECT FAMILIA, MONTH(DATA) AS MES, SUM(TOTAL) AS TOTAL
            FROM v_custo
            WHERE {where_sql}
            GROUP BY FAMILIA, MONTH(DATA)
        """

        try:
            custo_rows = db.session.execute(text(custos_sql), params).fetchall()
        except Exception as e:
            return jsonify({'error': f'Erro ao obter custos: {e}'}), 500

        for row in custo_rows:
            familia = str(row[0]).strip() if row[0] is not None else ''
            mes = int(row[1]) if row[1] is not None else None
            valor = float(row[2] or 0)
            if not familia or mes is None or mes < 1 or mes > 12:
                continue

            # acumula na familia e respetivos pais
            partes = familia.split('.')
            while partes:
                ref_atual = '.'.join(partes)
                ensure_node(ref_atual)
                node = familias_map[ref_atual]
                node['meses'][mes - 1] += valor
                node['total'] += valor
                partes = partes[:-1]

        # Orçamento (OC) por familia/mes (custos)
        try:
            oc_rows = db.session.execute(
                text("SELECT FAMILIA, MES, VALOR FROM OC WHERE ANO = :ano"),
                {'ano': ano}
            ).fetchall()
        except Exception as e:
            return jsonify({'error': f'Erro ao obter orçamento (OC): {e}'}), 500

        for row in oc_rows:
            familia = str(row[0]).strip() if row[0] is not None else ''
            try:
                mes = int(row[1]) if row[1] is not None else None
            except Exception:
                mes = None
            valor = float(row[2] or 0)
            if not familia or mes is None or mes < 1 or mes > 12:
                continue
            if is_prov_ref(familia):
                continue
            # acumula no nó e respetivos pais (para permitir evidenciar também níveis superiores)
            partes = familia.split('.')
            while partes:
                ref_atual = '.'.join(partes)
                ensure_node(ref_atual)
                node = familias_map[ref_atual]
                node['orc_meses'][mes - 1] += valor
                node['orc_total'] += valor
                partes = partes[:-1]

        # Objetivos de venda (OV) para proveitos:
        # - 9.1 => EXPLORACAO
        # - 9.2 => GESTAO
        try:
            where_ov = ["ov.ANO = :ano"]
            params_ov = {'ano': ano}
            if ccustos:
                keys = []
                for idx, cc in enumerate(ccustos):
                    k = f"cc{idx}"
                    params_ov[k] = cc
                    keys.append(f":{k}")
                where_ov.append("ov.CCUSTO IN (" + ",".join(keys) + ")")
            sql_ov = f"""
                SELECT
                    ov.CCUSTO,
                    UPPER(LTRIM(RTRIM(ISNULL(a.TIPO,'')))) AS TIPO,
                    ISNULL(ov.JANEIRO,0)   AS JANEIRO,
                    ISNULL(ov.FEVEREIRO,0) AS FEVEREIRO,
                    ISNULL(ov.MARCO,0)     AS MARCO,
                    ISNULL(ov.ABRIL,0)     AS ABRIL,
                    ISNULL(ov.MAIO,0)      AS MAIO,
                    ISNULL(ov.JUNHO,0)     AS JUNHO,
                    ISNULL(ov.JULHO,0)     AS JULHO,
                    ISNULL(ov.AGOSTO,0)    AS AGOSTO,
                    ISNULL(ov.SETEMBRO,0)  AS SETEMBRO,
                    ISNULL(ov.OUTUBRO,0)   AS OUTUBRO,
                    ISNULL(ov.NOVEMBRO,0)  AS NOVEMBRO,
                    ISNULL(ov.DEZEMBRO,0)  AS DEZEMBRO
                FROM OV ov
                LEFT JOIN AL a
                  ON LTRIM(RTRIM(a.CCUSTO)) COLLATE SQL_Latin1_General_CP1_CI_AI
                   = LTRIM(RTRIM(ov.CCUSTO)) COLLATE SQL_Latin1_General_CP1_CI_AI
                WHERE {" AND ".join(where_ov)}
            """
            ov_rows = db.session.execute(text(sql_ov), params_ov).mappings().all()
        except Exception as e:
            return jsonify({'error': f'Erro ao obter objetivos (OV): {e}'}), 500

        expl = [0.0] * 12
        gest = [0.0] * 12
        for r in ov_rows:
            tipo = (r.get('TIPO') or '').strip().upper()
            months = [
                float(r.get('JANEIRO') or 0),
                float(r.get('FEVEREIRO') or 0),
                float(r.get('MARCO') or 0),
                float(r.get('ABRIL') or 0),
                float(r.get('MAIO') or 0),
                float(r.get('JUNHO') or 0),
                float(r.get('JULHO') or 0),
                float(r.get('AGOSTO') or 0),
                float(r.get('SETEMBRO') or 0),
                float(r.get('OUTUBRO') or 0),
                float(r.get('NOVEMBRO') or 0),
                float(r.get('DEZEMBRO') or 0),
            ]
            if tipo == 'EXPLORACAO':
                for i in range(12):
                    expl[i] += months[i]
            elif tipo == 'GESTAO':
                for i in range(12):
                    gest[i] += months[i]

        ensure_node('9')
        ensure_node('9.1')
        ensure_node('9.2')
        for i in range(12):
            familias_map['9.1']['orc_meses'][i] += expl[i]
            familias_map['9.1']['orc_total'] += expl[i]
            familias_map['9.2']['orc_meses'][i] += gest[i]
            familias_map['9.2']['orc_total'] += gest[i]
            familias_map['9']['orc_meses'][i] += (expl[i] + gest[i])
            familias_map['9']['orc_total'] += (expl[i] + gest[i])

        def sort_key(ref: str):
            parts = []
            for p in ref.split('.'):
                try:
                    parts.append(int(p))
                except Exception:
                    parts.append(p)
            return parts

        total_base = sum(
            v['total']
            for v in familias_map.values()
            if v.get('nivel') == 1 and not is_prov_ref(v.get('ref'))
        )
        familias_lista = []
        for f in sorted(familias_map.values(), key=lambda x: sort_key(x['ref'])):
            total_fam = float(f['total'] or 0)
            meses_fmt = [round(float(v or 0), 2) for v in f['meses']]
            is_proveito = is_prov_ref(f.get('ref'))
            orc_meses_fmt = [round(float(v or 0), 2) for v in (f.get('orc_meses') or [0.0] * 12)]
            orc_total = round(float(f.get('orc_total') or 0), 2)
            familias_lista.append({
                'ref': f['ref'],
                'nome': f.get('nome', ''),
                'nivel': f.get('nivel', 1),
                'meses': meses_fmt,
                'total': round(total_fam, 2),
                'percent': (None if is_proveito else round((total_fam / total_base * 100) if total_base else 0, 2)),
                'orc_meses': orc_meses_fmt,
                'orc_total': orc_total,
            })

        return jsonify({
            'ano': ano,
            'ccustos': ccustos,
            'total_geral': round(float(total_base or 0), 2),
            'familias': familias_lista
        })

    @app.route('/api/mapa_gestao/detalhe')
    @login_required
    def api_mapa_gestao_detalhe():
        try:
            ano = request.args.get('ano', type=int) or date.today().year
        except Exception:
            ano = date.today().year
        familia = (request.args.get('familia') or '').strip()
        if not familia:
            return jsonify({'error': 'familia obrigatoria'}), 400
        mes = request.args.get('mes', type=int)
        include_children = request.args.get('include_children') in ('1', 'true', 'True')
        ccustos_raw = (request.args.get('ccustos') or '').strip()
        ccustos = [c.strip() for c in ccustos_raw.split(',') if c.strip()]

        where_parts = ["YEAR(data) = :ano"]
        params = {'ano': ano, 'familia': familia}
        if include_children:
            where_parts.append("(FAMILIA = :familia OR FAMILIA LIKE :familia_like)")
            params['familia_like'] = familia + ".%"
        else:
            where_parts.append("FAMILIA = :familia")
        if mes and 1 <= mes <= 12:
            where_parts.append("MONTH(data) = :mes")
            params['mes'] = mes
        if ccustos:
            keys = []
            for idx, cc in enumerate(ccustos):
                k = f"c{idx}"
                params[k] = cc
                keys.append(f":{k}")
            where_parts.append("ccusto IN (" + ",".join(keys) + ")")

        where_sql = " AND ".join(where_parts)
        sql = f"""
            SELECT
                nmdoc AS documento,
                nrdoc AS numero,
                data  AS data,
                nome  AS nome,
                ccusto AS ccusto,
                ref    AS referencia,
                design AS designacao,
                qtt    AS quantidade,
                epv    AS preco,
                total  AS total,
                CABSTAMP AS cabstamp
            FROM v_custo
            WHERE {where_sql}
            ORDER BY data, nmdoc, nrdoc
        """
        try:
            rows = db.session.execute(text(sql), params).mappings().all()
        except Exception as e:
            return jsonify({'error': f'Erro ao obter detalhe: {e}'}), 500

        # Orçamento/Objetivo:
        # - Custos => OC (por família/mês)
        # - Proveitos (famílias 9.1/9.2) => OV (por CCUSTO, mapeado via AL.TIPO)
        orc_total = 0.0
        familia_is_prov = str(familia or '').strip().startswith('9')
        if familia_is_prov:
            try:
                where_ov = ["ov.ANO = :ano"]
                params_ov = {'ano': ano}
                if ccustos:
                    keys = []
                    for idx, cc in enumerate(ccustos):
                        k = f"cc{idx}"
                        params_ov[k] = cc
                        keys.append(f":{k}")
                    where_ov.append("ov.CCUSTO IN (" + ",".join(keys) + ")")
                sql_ov = f"""
                    SELECT
                        UPPER(LTRIM(RTRIM(ISNULL(a.TIPO,'')))) AS TIPO,
                        SUM(ISNULL(ov.JANEIRO,0))   AS JANEIRO,
                        SUM(ISNULL(ov.FEVEREIRO,0)) AS FEVEREIRO,
                        SUM(ISNULL(ov.MARCO,0))     AS MARCO,
                        SUM(ISNULL(ov.ABRIL,0))     AS ABRIL,
                        SUM(ISNULL(ov.MAIO,0))      AS MAIO,
                        SUM(ISNULL(ov.JUNHO,0))     AS JUNHO,
                        SUM(ISNULL(ov.JULHO,0))     AS JULHO,
                        SUM(ISNULL(ov.AGOSTO,0))    AS AGOSTO,
                        SUM(ISNULL(ov.SETEMBRO,0))  AS SETEMBRO,
                        SUM(ISNULL(ov.OUTUBRO,0))   AS OUTUBRO,
                        SUM(ISNULL(ov.NOVEMBRO,0))  AS NOVEMBRO,
                        SUM(ISNULL(ov.DEZEMBRO,0))  AS DEZEMBRO
                    FROM OV ov
                    LEFT JOIN AL a
                      ON LTRIM(RTRIM(a.CCUSTO)) COLLATE SQL_Latin1_General_CP1_CI_AI
                       = LTRIM(RTRIM(ov.CCUSTO)) COLLATE SQL_Latin1_General_CP1_CI_AI
                    WHERE {" AND ".join(where_ov)}
                    GROUP BY UPPER(LTRIM(RTRIM(ISNULL(a.TIPO,''))))
                """
                ov_rows = db.session.execute(text(sql_ov), params_ov).mappings().all()
                by_tipo = { (r.get('TIPO') or '').strip().upper(): r for r in ov_rows }
                exp = by_tipo.get('EXPLORACAO', {}) or {}
                ges = by_tipo.get('GESTAO', {}) or {}
                month_cols = ['JANEIRO','FEVEREIRO','MARCO','ABRIL','MAIO','JUNHO','JULHO','AGOSTO','SETEMBRO','OUTUBRO','NOVEMBRO','DEZEMBRO']
                if mes and 1 <= mes <= 12:
                    col = month_cols[mes - 1]
                    val_exp = float(exp.get(col) or 0)
                    val_ges = float(ges.get(col) or 0)
                    fam = str(familia or '').strip()
                    if fam.startswith('9.1'):
                        orc_total = val_exp
                    elif fam.startswith('9.2'):
                        orc_total = val_ges
                    else:
                        # 9 (ou outras) -> soma
                        orc_total = val_exp + val_ges
                else:
                    val_exp = sum(float(exp.get(c) or 0) for c in month_cols)
                    val_ges = sum(float(ges.get(c) or 0) for c in month_cols)
                    fam = str(familia or '').strip()
                    if fam.startswith('9.1'):
                        orc_total = val_exp
                    elif fam.startswith('9.2'):
                        orc_total = val_ges
                    else:
                        orc_total = val_exp + val_ges
            except Exception as e:
                return jsonify({'error': f'Erro ao obter objetivos (OV): {e}'}), 500
        else:
            try:
                oc_where = ["ANO = :ano"]
                oc_params = {'ano': ano, 'familia': familia}
                if include_children:
                    oc_where.append("(FAMILIA = :familia OR FAMILIA LIKE :familia_like)")
                    oc_params['familia_like'] = familia + ".%"
                else:
                    oc_where.append("FAMILIA = :familia")
                if mes and 1 <= mes <= 12:
                    oc_where.append("MES = :mes")
                    oc_params['mes'] = mes
                oc_sql = "SELECT SUM(ISNULL(VALOR,0)) AS ORCAMENTO FROM OC WHERE " + " AND ".join(oc_where)
                oc_row = db.session.execute(text(oc_sql), oc_params).mappings().first() or {}
                orc_total = float(oc_row.get('ORCAMENTO') or 0)
            except Exception as e:
                return jsonify({'error': f'Erro ao obter orçamento (OC): {e}'}), 500

        out = []
        total_sum = 0.0
        cabstamps = []
        for r in rows:
            val = float(r.get('total') or 0)
            total_sum += val
            data_val = r.get('data')
            if isinstance(data_val, (datetime, date)):
                data_val = data_val.strftime('%Y-%m-%d')
            cabstamp = r.get('cabstamp')
            if cabstamp:
                cabstamps.append(str(cabstamp))
            out.append({
                'documento': r.get('documento'),
                'numero': r.get('numero'),
                'data': data_val,
                'nome': r.get('nome'),
                'ccusto': r.get('ccusto'),
                'referencia': r.get('referencia'),
                'designacao': r.get('designacao'),
                'quantidade': r.get('quantidade'),
                'preco': r.get('preco'),
                'total': round(val, 2),
                'cabstamp': cabstamp
            })

        anexo_map = {}
        if cabstamps:
            placeholders = []
            params_anx = {}
            for idx, cab in enumerate(cabstamps):
                key = f"c{idx}"
                params_anx[key] = cab
                placeholders.append(f":{key}")
            sql_anx = f"""
                SELECT RECSTAMP, CAMINHO, FICHEIRO
                FROM ANEXOS
                WHERE RECSTAMP IN ({",".join(placeholders)})
                ORDER BY RECSTAMP
            """
            try:
                rows_anx = db.session.execute(text(sql_anx), params_anx).fetchall()
                for ra in rows_anx:
                    rec = str(ra[0])
                    if rec and rec not in anexo_map:
                        caminho = ra[1] if len(ra) > 1 else None
                        ficheiro = ra[2] if len(ra) > 2 else None
                        anexo_map[rec] = caminho or ficheiro or None
            except Exception:
                anexo_map = {}

        for item in out:
            cab = item.get('cabstamp')
            url = anexo_map.get(str(cab)) if cab else None
            item['anexo_url'] = url

        desvio = total_sum - orc_total
        desvio_pct = None
        if orc_total:
            try:
                desvio_pct = (desvio / orc_total) * 100
            except Exception:
                desvio_pct = None

        return jsonify({
            'rows': out,
            'total': round(total_sum, 2),
            'orc_total': round(float(orc_total or 0), 2),
            'desvio': round(float(desvio or 0), 2),
            'desvio_pct': (None if desvio_pct is None else round(float(desvio_pct), 2))
        })

    @app.route('/turnover')
    @login_required
    def turnover_page():
        return render_template('turnover.html', page_title='Turnover Diário', today=date.today().isoformat())

    @app.route('/api/turnover')
    @login_required
    def api_turnover():
        try:
            data_str = (request.args.get('data') or '').strip()
            dia = datetime.strptime(data_str, '%Y-%m-%d').date() if data_str else date.today()
            dia_iso = dia.isoformat()

            reservas_out = db.session.execute(text("""
                SELECT LTRIM(RTRIM(ALOJAMENTO)) AS ALOJAMENTO, ISNULL(HORAOUT,'') AS HORAOUT, NOITES,
                       ISNULL(ADULTOS,0) AS ADULTOS, ISNULL(CRIANCAS,0) AS CRIANCAS,
                       ISNULL(BERCO,0) AS BERCO, ISNULL(SOFACAMA,0) AS SOFACAMA
                FROM RS
                WHERE CAST(DATAOUT AS date) = :dia
                  AND ISNULL(CANCELADA,0) = 0
            """), {'dia': dia_iso}).mappings().all()

            reservas_in = db.session.execute(text("""
                SELECT LTRIM(RTRIM(RS.ALOJAMENTO)) AS ALOJAMENTO, ISNULL(RS.HORAIN,'') AS HORAIN, RS.NOITES,
                       ISNULL(RS.ADULTOS,0) AS ADULTOS, ISNULL(RS.CRIANCAS,0) AS CRIANCAS,
                       ISNULL(RS.BERCO,0) AS BERCO, ISNULL(RS.SOFACAMA,0) AS SOFACAMA,
                       ISNULL(RS.SEF,0) AS SEF, ISNULL(RS.USRSEF,'') AS USRSEF,
                       ISNULL(RS.INSTR,0) AS INSTR, ISNULL(RS.USRINSTR,'') AS USRINSTR,
                       ISNULL(RS.PRESENCIAL,0) AS PRESENCIAL,
                       ISNULL(RS.ENTROU,0) AS ENTROU,
                       ISNULL(RS.USRCHECKIN,'') AS USRCHECKIN,
                       ISNULL(uc.NOME, RS.USRCHECKIN) AS USRCHECKIN_NOME
                FROM RS
                LEFT JOIN US uc ON uc.LOGIN = RS.USRCHECKIN
                WHERE CAST(RS.DATAIN AS date) = :dia
                  AND ISNULL(RS.CANCELADA,0) = 0
            """), {'dia': dia_iso}).mappings().all()

            tarefas = db.session.execute(text("""
                SELECT LTRIM(RTRIM(t.ALOJAMENTO)) AS ALOJAMENTO,
                       t.UTILIZADOR,
                       ISNULL(t.TRATADO,0) AS TRATADO,
                       ISNULL(t.TAREFA,'') AS OBS,
                       ISNULL(u.NOME, t.UTILIZADOR) AS NOME,
                       ISNULL(t.HORA,'') AS HORA,
                       ISNULL(al.TIPOLOGIA,'') AS TIPOLOGIA
                FROM TAREFAS t
                LEFT JOIN US u ON u.LOGIN = t.UTILIZADOR
                LEFT JOIN AL al ON LTRIM(RTRIM(al.NOME)) = LTRIM(RTRIM(t.ALOJAMENTO))
                WHERE LTRIM(RTRIM(ISNULL(t.ORIGEM,''))) = 'LP'
                  AND CAST(t.DATA AS date) = :dia
            """), {'dia': dia_iso}).mappings().all()

            ultimas_limpezas = db.session.execute(text("""
                WITH cte AS (
                    SELECT LTRIM(RTRIM(t.ALOJAMENTO)) AS ALOJAMENTO,
                           CAST(t.DATA AS date) AS DIA,
                           ISNULL(t.HORA,'') AS HORA,
                           ISNULL(u.NOME, t.UTILIZADOR) AS NOME,
                           ROW_NUMBER() OVER (
                               PARTITION BY LTRIM(RTRIM(t.ALOJAMENTO))
                               ORDER BY CAST(t.DATA AS date) DESC, ISNULL(t.HORA,'') DESC
                           ) AS rn
                    FROM TAREFAS t
                    LEFT JOIN US u ON u.LOGIN = t.UTILIZADOR
                    WHERE LTRIM(RTRIM(ISNULL(t.ORIGEM,''))) = 'LP'
                      AND ISNULL(t.TRATADO,0) = 1
                      AND CAST(t.DATA AS date) <= :dia
                )
                SELECT ALOJAMENTO, DIA, HORA, NOME FROM cte WHERE rn = 1
            """), {'dia': dia_iso}).mappings().all()

            def norm_aloj(v: str) -> str:
                try:
                    return (v or '').strip().upper()
                except Exception:
                    return ''

            map_out, map_in, map_tasks, map_last = {}, {}, {}, {}
            for r in reservas_out:
                aloj = norm_aloj(r.get('ALOJAMENTO'))
                if aloj:
                    map_out.setdefault(aloj, []).append(r)
            for r in reservas_in:
                aloj = norm_aloj(r.get('ALOJAMENTO'))
                if aloj:
                    map_in.setdefault(aloj, []).append(r)
            for r in tarefas:
                aloj = norm_aloj(r.get('ALOJAMENTO'))
                if aloj:
                    map_tasks.setdefault(aloj, []).append(r)
            for r in ultimas_limpezas:
                aloj = norm_aloj(r.get('ALOJAMENTO'))
                if aloj and aloj not in map_last:
                    map_last[aloj] = r

            now_dt = datetime.now()
            all_aloj = set(map_out.keys()) | set(map_in.keys()) | set(map_tasks.keys())

            # Helpers to cache last checkout and next checkin dates
            cache_last_out = {}
            cache_next_in = {}
            cache_future_clean = {}

            def get_last_out(aloj):
                if aloj in cache_last_out:
                    return cache_last_out[aloj]
                try:
                    row = db.session.execute(text("""
                        SELECT TOP 1 CAST(DATAOUT AS date) AS DIA
                        FROM RS
                        WHERE CAST(DATAOUT AS date) < :dia
                          AND LTRIM(RTRIM(ALOJAMENTO)) = LTRIM(RTRIM(:aloj))
                          AND ISNULL(CANCELADA,0) = 0
                        ORDER BY DATAOUT DESC
                    """), {'dia': dia_iso, 'aloj': aloj}).first()
                    cache_last_out[aloj] = row[0] if row else None
                except Exception:
                    cache_last_out[aloj] = None
                return cache_last_out[aloj]

            def get_next_in(aloj):
                if aloj in cache_next_in:
                    return cache_next_in[aloj]
                try:
                    row = db.session.execute(text("""
                        SELECT TOP 1 CAST(DATAIN AS date) AS DIA
                        FROM RS
                        WHERE CAST(DATAIN AS date) > :dia
                          AND LTRIM(RTRIM(ALOJAMENTO)) = LTRIM(RTRIM(:aloj))
                          AND ISNULL(CANCELADA,0) = 0
                        ORDER BY DATAIN ASC
                    """), {'dia': dia_iso, 'aloj': aloj}).first()
                    cache_next_in[aloj] = row[0] if row else None
                except Exception:
                    cache_next_in[aloj] = None
                return cache_next_in[aloj]

            def get_future_clean(aloj, limite):
                if aloj in cache_future_clean:
                    return cache_future_clean[aloj]
                try:
                    params = {'dia': dia_iso, 'aloj': aloj}
                    sql = """
                        SELECT TOP 1 CAST(t.DATA AS date) AS DIA,
                               ISNULL(u.NOME, t.UTILIZADOR) AS NOME
                        FROM TAREFAS t
                        LEFT JOIN US u ON u.LOGIN = t.UTILIZADOR
                        WHERE LTRIM(RTRIM(t.ALOJAMENTO)) = LTRIM(RTRIM(:aloj))
                          AND LTRIM(RTRIM(ISNULL(t.ORIGEM,''))) = 'LP'
                          AND CAST(t.DATA AS date) > :dia
                          AND ISNULL(t.TRATADO,0) = 0
                    """
                    if limite:
                        sql += " AND CAST(t.DATA AS date) <= :limite"
                        params['limite'] = limite
                    sql += " ORDER BY t.DATA ASC"
                    row = db.session.execute(text(sql), params).first()
                    if row:
                        cache_future_clean[aloj] = {'dia': row[0], 'nome': row[1]}
                    else:
                        cache_future_clean[aloj] = None
                except Exception:
                    cache_future_clean[aloj] = None
                return cache_future_clean[aloj]

            dow_pt = ['SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SAB', 'DOM']

            def fmt_date_parts(dval):
                try:
                    if isinstance(dval, datetime):
                        d = dval.date()
                    else:
                        d = dval
                    dow = dow_pt[d.weekday()]
                    dat = d.strftime('%d/%m')
                    return {'dow': dow, 'date': dat}
                except Exception:
                    return None

            cards = []
            for aloj in sorted(all_aloj):
                out_list = map_out.get(aloj, [])
                in_list = map_in.get(aloj, [])
                task_list = map_tasks.get(aloj, [])

                aloj_display = ''
                for src in (out_list, in_list, task_list):
                    if src:
                        aloj_display = src[0].get('ALOJAMENTO') or ''
                        break

                def first_val(lst, key):
                    try:
                        return lst[0].get(key) if lst else ''
                    except Exception:
                        return ''

                chk_out = first_val(out_list, 'HORAOUT') or ''
                chk_in = first_val(in_list, 'HORAIN') or ''
                noites = first_val(in_list, 'NOITES') or 0
                try:
                    hospedes = int(first_val(in_list, 'ADULTOS') or 0) + int(first_val(in_list, 'CRIANÇAS') or first_val(in_list, 'CRIANCAS') or 0)
                except Exception:
                    hospedes = 0
                berco = bool(first_val(in_list, 'BERCO'))
                sof = bool(first_val(in_list, 'SOFACAMA'))

                status = 'Já limpo'
                tem_planeada = False
                tem_concluida = False
                if task_list:
                    tem_planeada = any(int(t.get('TRATADO') or 0) == 0 for t in task_list)
                    tem_concluida = any(int(t.get('TRATADO') or 0) == 1 for t in task_list)
                    if tem_planeada:
                        status = 'Planeada'
                    elif tem_concluida:
                        status = 'Concluída'
                equipa = first_val(task_list, 'NOME') or ''
                hora_lp = first_val(task_list, 'HORA') or ''
                tipologia = (first_val(task_list, 'TIPOLOGIA') or '').strip().upper()
                dur_map = {'T0': 60, 'T1': 60, 'T2': 90, 'T3': 120, 'T4': 150}
                dur_min = dur_map.get(tipologia)
                hora_fim = ''
                try:
                    if hora_lp and dur_min:
                        s = str(hora_lp).strip()
                        hh = mm = 0
                        if ':' in s:
                            parts = s.split(':')
                            hh = int(parts[0])
                            mm = int(parts[1] if len(parts) > 1 else 0)
                        else:
                            digits = ''.join(ch for ch in s if ch.isdigit())
                            if len(digits) >= 3:
                                mm = int(digits[-2:])
                                hh = int(digits[:-2])
                            elif digits:
                                hh = int(digits)
                        total = hh * 60 + mm + dur_min
                        hora_fim = f"{(total // 60) % 24:02d}:{total % 60:02d}"
                except Exception:
                    hora_fim = ''
                atrasada = False
                if tem_planeada and not tem_concluida:
                    if dia < now_dt.date():
                        atrasada = True
                    elif dia == now_dt.date():
                        try:
                            if hora_fim:
                                h_end = datetime.strptime(hora_fim, '%H:%M').time()
                                if now_dt.time() > h_end:
                                    atrasada = True
                        except Exception:
                            pass
                if atrasada:
                    status = 'Atrasada'
                if out_list and not task_list:
                    status = 'Por atribuir'
                last_info = False
                if not task_list:
                    last = map_last.get(aloj)
                    if last:
                        try:
                            dia_last = last.get('DIA')
                            dia_str = ''
                            if dia_last:
                                try:
                                    dia_str = dia_last.strftime('%d/%m/%Y')
                                except Exception:
                                    dia_str = str(dia_last)[:10]
                            nome_last = last.get('NOME') or ''
                            if nome_last or dia_str:
                                equipa = f"{nome_last} ({dia_str})".strip()
                            last_info = True
                        except Exception:
                            pass
                extras_obs = []
                if berco:
                    extras_obs.append('Berço')
                if sof:
                    extras_obs.append('Sofá-cama')
                obs = ' • '.join(extras_obs)
                fallback_out = None
                if not out_list:
                    d_last = get_last_out(aloj)
                    if d_last:
                        fmt = fmt_date_parts(d_last)
                        if fmt:
                            fallback_out = fmt
                fallback_in = None
                if not in_list:
                    d_next = get_next_in(aloj)
                    if d_next:
                        fmt = fmt_date_parts(d_next)
                        if fmt:
                            fallback_in = fmt
                    else:
                        fallback_in = {'text': 'Sem Reservas'}
                # Se existe checkout e nÇõo hÇ  limpeza hoje, verificar limpeza planeada antes/prÇüx checkin
                if out_list and not task_list:
                    limite = get_next_in(aloj) or (dia + timedelta(days=14))
                    prox_limpeza = get_future_clean(aloj, limite)
                    if prox_limpeza:
                        dia_fut = prox_limpeza.get('dia')
                        nome_fut = prox_limpeza.get('nome') or ''
                        try:
                            data_fmt = dia_fut.strftime('%d/%m') if dia_fut else ''
                            status = f"Planeada {data_fmt}" if data_fmt else 'Planeada'
                        except Exception:
                            status = 'Planeada'
                        try:
                            if dia_fut:
                                data_lbl = dia_fut.strftime('%d/%m')
                            else:
                                data_lbl = ''
                            if nome_fut or data_lbl:
                                equipa = f"{nome_fut} ({data_lbl})".strip()
                                last_info = True
                        except Exception:
                            pass

                cards.append({
                    'alojamento': aloj_display or aloj,
                    'status': status,
                    'check_out': chk_out,
                    'has_check_out': bool(out_list),
                    'check_in': chk_in,
                    'has_check_in': bool(in_list),
                    'entrou': bool(first_val(in_list, 'ENTROU') or 0),
                    'equipa': equipa,
                    'last_info': last_info,
                    'hora_lp': hora_lp,
                    'hora_fim': hora_fim,
                    'noites': noites,
                    'hospedes': hospedes,
                    'berco': berco,
                    'sofacama': sof,
                    'obs': obs,
                    'sef': bool(first_val(in_list, 'SEF') or 0),
                    'instr': bool(first_val(in_list, 'INSTR') or 0),
                    'presencial': bool(first_val(in_list, 'PRESENCIAL') or 0),
                    'usrcheckin': first_val(in_list, 'USRCHECKIN') or '',
                    'usrcheckin_nome': first_val(in_list, 'USRCHECKIN_NOME') or '',
                    'fallback_out': fallback_out,
                    'fallback_in': fallback_in
                })

            return jsonify({'data': dia_iso, 'cards': cards})
        except Exception as e:
            try:
                app.logger.exception('Erro em api_turnover')
            except Exception:
                pass
            return jsonify({'error': str(e)}), 500

    @app.route('/api/turnover/checkin', methods=['GET', 'POST'])
    @login_required
    def api_turnover_checkin():
        try:
            if request.method == 'GET':
                data_str = (request.args.get('data') or '').strip()
                aloj = (request.args.get('alojamento') or '').strip()
                if not data_str or not aloj:
                    return jsonify({'error': 'Parâmetros em falta'}), 400
                try:
                    dia = datetime.strptime(data_str, '%Y-%m-%d').date()
                except Exception:
                    return jsonify({'error': 'Data inválida'}), 400

                users_rows = db.session.execute(text(
                    "SELECT LOGIN, NOME FROM US WHERE ISNULL(INATIVO,0)=0 ORDER BY NOME"
                )).fetchall()
                users = [{'value': r[0], 'label': r[1] or r[0]} for r in users_rows]

                row = db.session.execute(text("""
                    SELECT TOP 1 ISNULL(PRESENCIAL,0) AS PRESENCIAL,
                           ISNULL(ENTROU,0) AS ENTROU,
                           ISNULL(USRCHECKIN,'') AS USRCHECKIN,
                           ISNULL(SEF,0) AS SEF,
                           ISNULL(USRSEF,'') AS USRSEF,
                           ISNULL(INSTR,0) AS INSTR,
                           ISNULL(USRINSTR,'') AS USRINSTR
                    FROM RS
                    WHERE CAST(DATAIN AS date) = :dia
                      AND LTRIM(RTRIM(ALOJAMENTO)) = LTRIM(RTRIM(:aloj))
                      AND ISNULL(CANCELADA,0) = 0
                    ORDER BY DATAIN DESC
                """), {'dia': dia, 'aloj': aloj}).mappings().first()
                if not row:
                    return jsonify({'error': 'Reserva não encontrada'}), 404

                data = {
                    'presencial': bool(row.get('PRESENCIAL') or 0),
                    'entrou': bool(row.get('ENTROU') or 0),
                    'usrcheckin': row.get('USRCHECKIN') or '',
                    'sef': bool(row.get('SEF') or 0),
                    'usrsef': row.get('USRSEF') or '',
                    'instr': bool(row.get('INSTR') or 0),
                    'usrinstr': row.get('USRINSTR') or ''
                }
                return jsonify({'data': data, 'users': users, 'alojamento': aloj})

            # POST
            body = request.get_json(silent=True) or {}
            data_str = (body.get('data') or '').strip()
            aloj = (body.get('alojamento') or '').strip()
            if not data_str or not aloj:
                return jsonify({'error': 'Parâmetros em falta'}), 400
            try:
                dia = datetime.strptime(data_str, '%Y-%m-%d').date()
            except Exception:
                return jsonify({'error': 'Data inválida'}), 400
            sef = 1 if body.get('sef') else 0
            instr = 1 if body.get('instr') else 0
            presencial = 1 if body.get('presencial') else 0
            entrou = 1 if body.get('entrou') else 0
            usrcheckin = (body.get('usrcheckin') or '').strip()
            usrsef = getattr(current_user, 'LOGIN', '')
            usrinstr = getattr(current_user, 'LOGIN', '')

            upd = text("""
                UPDATE RS
                   SET PRESENCIAL = :p,
                       ENTROU = :e,
                       USRCHECKIN = :u,
                       SEF = :sef,
                       USRSEF = CASE WHEN :sef = 1 THEN :usrsef ELSE USRSEF END,
                       INSTR = :instr,
                       USRINSTR = CASE WHEN :instr = 1 THEN :usrinstr ELSE USRINSTR END
                 WHERE CAST(DATAIN AS date) = :dia
                   AND LTRIM(RTRIM(ALOJAMENTO)) = LTRIM(RTRIM(:aloj))
                   AND ISNULL(CANCELADA,0) = 0
            """)
            res = db.session.execute(upd, {
                'p': presencial,
                'e': entrou,
                'u': usrcheckin,
                'sef': sef,
                'usrsef': usrsef,
                'instr': instr,
                'usrinstr': usrinstr,
                'dia': dia,
                'aloj': aloj
            })
            db.session.commit()
            return jsonify({'ok': True, 'updated': res.rowcount})
        except Exception as e:
            db.session.rollback()
            try:
                app.logger.exception('Erro em api_turnover_checkin')
            except Exception:
                pass
            return jsonify({'error': str(e)}), 500


    # Performance dashboard page
    @app.route('/performance')
    @login_required
    def performance_page():
        return render_template('performance.html', page_title='Performance')

    # API: Alojamentos performance aggregation
    @app.route('/api/performance')
    @login_required
    def api_performance():
        try:
            # Parse dates or default to current month
            qs_ini = (request.args.get('data_inicio') or '').strip()
            qs_fim = (request.args.get('data_fim') or '').strip()

            today = date.today()
            first_day = date(today.year, today.month, 1)
            # Compute last day of month
            if today.month == 12:
                next_month_first = date(today.year + 1, 1, 1)
            else:
                next_month_first = date(today.year, today.month + 1, 1)
            from datetime import timedelta
            last_day = next_month_first - timedelta(days=1)

            def parse_d(dstr, fallback):
                try:
                    return datetime.strptime(dstr, '%Y-%m-%d').date()
                except Exception:
                    return fallback

            data_inicio = parse_d(qs_ini, first_day)
            data_fim = parse_d(qs_fim, last_day)

            # Nights total in the period (1 per day, inclusive)
            noites_totais = (data_fim - data_inicio).days + 1
            if noites_totais < 0:
                return jsonify({'error': 'Intervalo de datas inválido'}), 400

            # Future window: from max(today, start) to end (inclusive)
            future_start = first_day if data_inicio < first_day else data_inicio
            if today > future_start:
                future_start = today
            noites_futuras_totais = (data_fim - future_start).days + 1 if data_fim >= future_start else 0

            # Next 2/4/7 nights windows for alert (from today, capped to selected period)
            next_start = today if today > data_inicio else data_inicio
            next2_end_raw = today + timedelta(days=1)
            next4_end_raw = today + timedelta(days=3)
            next7_end_raw = today + timedelta(days=6)
            next2_end = next2_end_raw if next2_end_raw < data_fim else data_fim
            next4_end = next4_end_raw if next4_end_raw < data_fim else data_fim
            next7_end = next7_end_raw if next7_end_raw < data_fim else data_fim
            total_next2_days = (next2_end - next_start).days + 1 if next2_end >= next_start else 0
            total_next4_days = (next4_end - next_start).days + 1 if next4_end >= next_start else 0
            total_next7_days = (next7_end - next_start).days + 1 if next7_end >= next_start else 0

            # SQL Server aggregation with LEFT JOIN and filters in ON to preserve AL rows
            sql = text(
                """
                SELECT
                    A.NOME AS nome,
                    A.TIPOLOGIA AS tipologia,
                    A.TIPO AS tipo,
                    COUNT(DISTINCT V.data) AS noites_ocupadas,
                    SUM(ISNULL(V.valor, 0)) AS total_liquido,
                    CASE WHEN COUNT(DISTINCT V.data) > 0
                         THEN SUM(ISNULL(V.valor,0)) / NULLIF(COUNT(DISTINCT V.data), 0)
                         ELSE 0 END AS preco_medio_noite,
                    COUNT(DISTINCT CASE WHEN V.data >= :hoje THEN V.data END) AS noites_futuras_ocupadas,
                    COUNT(DISTINCT CASE WHEN V.data BETWEEN :next_start AND :next2_end THEN V.data END) AS next2_ocupadas,
                    COUNT(DISTINCT CASE WHEN V.data BETWEEN :next_start AND :next4_end THEN V.data END) AS next4_ocupadas,
                    COUNT(DISTINCT CASE WHEN V.data BETWEEN :next_start AND :next7_end THEN V.data END) AS next7_ocupadas
                FROM AL AS A
                LEFT JOIN v_diario_all AS V
                  ON V.CCUSTO = A.NOME
                 AND ISNULL(V.valor, 0) <> 0
                 AND V.data BETWEEN :data_inicio AND :data_fim
                WHERE ISNULL(A.INATIVO, 0) = 0
                GROUP BY A.NOME, A.TIPOLOGIA, A.TIPO
                ORDER BY A.NOME
                """
            )

            rows = db.session.execute(sql, {
                'data_inicio': data_inicio,
                'data_fim': data_fim,
                'hoje': today,
                'next_start': next_start,
                'next2_end': next2_end,
                'next4_end': next4_end,
                'next7_end': next7_end
            }).mappings().all()
            # Build occupancy map for next 7-day horizon to detect 2+ night gaps
            from datetime import datetime as _dt
            sql_occ = text(
                """
                SELECT V.CCUSTO AS nome, CAST(V.data AS date) AS dia
                FROM v_diario_all V
                JOIN AL A ON V.CCUSTO = A.NOME AND ISNULL(A.INATIVO,0)=0
                WHERE ISNULL(V.valor,0) <> 0
                  AND V.data BETWEEN :start AND :end
                """
            )
            occ_rows = db.session.execute(sql_occ, {
                'start': next_start,
                'end': next7_end
            }).fetchall()
            occ_map = {}
            for nome, dia in occ_rows:
                # Ensure date object
                if isinstance(dia, _dt):
                    dkey = dia.date()
                else:
                    dkey = dia
                occ_map.setdefault(nome, set()).add(dkey)

            result = []
            for r in rows:
                nome = r.get('nome')
                tipologia = r.get('tipologia')
                tipo = r.get('tipo')
                noites_ocupadas = float(r.get('noites_ocupadas') or 0)
                total_liquido = float(r.get('total_liquido') or 0)
                preco_medio_noite = float(r.get('preco_medio_noite') or 0)
                noites_futuras_ocupadas = int(r.get('noites_futuras_ocupadas') or 0)
                # Occupancy map for this lodging in next horizon
                occ_set = occ_map.get(nome, set())
                # Helper to detect if there exists a run of >=2 empty nights within first L days
                def has_two_plus_gap(L):
                    if L is None or L < 2:
                        return False
                    run = 0
                    for i in range(L):
                        d = next_start + timedelta(days=i)
                        if d in occ_set:
                            run = 0
                        else:
                            run += 1
                            if run >= 2:
                                return True
                    return False
                noites_disponiveis = max(0, noites_futuras_totais - noites_futuras_ocupadas)
                taxa = (noites_ocupadas / noites_totais * 100.0) if noites_totais > 0 else 0.0
                # Determine alert level based on first window that contains a 2+ empty-night run
                alert_level = ''
                if has_two_plus_gap(total_next2_days):
                    alert_level = 'red'
                elif has_two_plus_gap(total_next4_days):
                    alert_level = 'orange'
                elif has_two_plus_gap(total_next7_days):
                    alert_level = 'yellow'

                result.append({
                    'nome': nome,
                    'tipologia': tipologia,
                    'tipo': tipo,
                    'noites_ocupadas': round(noites_ocupadas, 2),
                    'noites_totais': noites_totais,
                    'taxa_ocupacao': round(taxa, 2),
                    'total_liquido': round(total_liquido, 2),
                    'preco_medio_noite': round(preco_medio_noite, 2),
                    'noites_futuras_ocupadas': noites_futuras_ocupadas,
                    'noites_futuras_totais': noites_futuras_totais,
                    'noites_disponiveis': noites_disponiveis,
                    'alert_level': alert_level
                })

            return jsonify({
                'rows': result,
                'data_inicio': data_inicio.strftime('%Y-%m-%d'),
                'data_fim': data_fim.strftime('%Y-%m-%d')
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # -----------------------------
    # Não disponibilidades (ND)
    # -----------------------------
    @app.route('/nd')
    @login_required
    def nd_page():
        return render_template('nd.html', page_title='Não disponibilidades')

    @app.route('/api/nd', methods=['GET', 'POST'])
    @login_required
    def api_nd():
        try:
            if request.method == 'GET':
                qs_ini = (request.args.get('data_inicio') or '').strip()
                qs_fim = (request.args.get('data_fim') or '').strip()
                def parse_d(dstr):
                    try:
                        return datetime.strptime(dstr, '%Y-%m-%d').date()
                    except Exception:
                        return None
                di = parse_d(qs_ini)
                df = parse_d(qs_fim)
                if not di or not df:
                    return jsonify({'error': 'Parâmetros de datas inválidos'}), 400
                sql = text(
                    """
                    SELECT N.NDSTAMP, N.DATA, N.TIPO, N.UTILIZADOR, U.NOME, U.COR
                    FROM ND AS N
                    INNER JOIN US AS U ON U.LOGIN = N.UTILIZADOR
                    WHERE N.DATA BETWEEN :di AND :df
                    ORDER BY N.DATA, U.NOME
                    """
                )
                rows = db.session.execute(sql, {'di': di, 'df': df}).fetchall()
                items = [
                    {
                        'id': r[0],
                        'data': r[1].isoformat(),
                        'tipo': r[2],
                        'login': r[3],
                        'nome': r[4],
                        'cor': r[5] or '#94a3b8'
                    }
                    for r in rows
                ]
                return jsonify({'rows': items})
            # POST: inserir ND (FOLGA)
            body = request.get_json(silent=True) or {}
            data_str = (body.get('data') or '').strip()
            utilizador = (body.get('utilizador') or '').strip()
            try:
                d = datetime.strptime(data_str, '%Y-%m-%d').date()
            except Exception:
                return jsonify({'error': 'Data inválida'}), 400
            if not utilizador:
                return jsonify({'error': 'Utilizador obrigatório'}), 400
            ins = text(
                """
                INSERT INTO ND (NDSTAMP, EQUIPA, DATA, TIPO, UTILIZADOR)
                SELECT LEFT(CONVERT(varchar(36), NEWID()), 25), '', :data, 'FOLGA', :util
                """
            )
            db.session.execute(ins, {'data': d, 'util': utilizador})
            db.session.commit()
            return jsonify({'ok': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    @app.route('/api/nd/move', methods=['POST'])
    @login_required
    def api_nd_move():
        try:
            body = request.get_json(silent=True) or {}
            nd_id = (body.get('id') or '').strip()
            data_str = (body.get('data') or '').strip()
            if not nd_id:
                return jsonify({'error': 'ID em falta'}), 400
            try:
                new_date = datetime.strptime(data_str, '%Y-%m-%d').date()
            except Exception:
                return jsonify({'error': 'Data inválida'}), 400
            upd = text("UPDATE ND SET DATA = :d WHERE NDSTAMP = :id")
            res = db.session.execute(upd, {'d': new_date, 'id': nd_id})
            db.session.commit()
            return jsonify({'ok': True, 'updated': res.rowcount})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    @app.route('/api/nd/delete', methods=['POST'])
    @login_required
    def api_nd_delete():
        try:
            body = request.get_json(silent=True) or {}
            nd_id = (body.get('id') or '').strip()
            if not nd_id:
                return jsonify({'error': 'ID em falta'}), 400
            del_sql = text("DELETE FROM ND WHERE NDSTAMP = :id")
            res = db.session.execute(del_sql, {'id': nd_id})
            db.session.commit()
            return jsonify({'ok': True, 'deleted': res.rowcount})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    @app.route('/api/nd/ferias', methods=['POST'])
    @login_required
    def api_nd_ferias():
        try:
            body = request.get_json(silent=True) or {}
            utilizador = (body.get('utilizador') or '').strip()
            di_str = (body.get('data_inicio') or '').strip()
            df_str = (body.get('data_fim') or '').strip()
            ano_str = (body.get('ano') or '').strip()
            if not utilizador:
                return jsonify({'error': 'Utilizador obrigatório'}), 400
            try:
                di = datetime.strptime(di_str, '%Y-%m-%d').date()
                df = datetime.strptime(df_str, '%Y-%m-%d').date()
            except Exception:
                return jsonify({'error': 'Datas inválidas'}), 400
            if df < di:
                return jsonify({'error': 'Data fim anterior à data início'}), 400
            # Determina ano
            try:
                ano = int(ano_str) if ano_str else di.year
            except Exception:
                ano = di.year
            # Nota: o ano (FA/ND.ANO) representa o direito adquirido; as datas podem ser gozadas noutro ano.
            from datetime import timedelta
            # Validação: dias disponíveis em FA vs usados em ND
            q_fa = db.session.execute(text(
                "SELECT ISNULL(DIAS,0) FROM FA WHERE UTILIZADOR = :u AND ANO = :a"
            ), { 'u': utilizador, 'a': ano }).fetchone()
            total_fa = int(q_fa[0]) if q_fa is not None else 0
            q_used = db.session.execute(text(
                "SELECT COUNT(*) FROM ND WHERE UTILIZADOR = :u AND TIPO = 'FERIAS' AND ANO = :a"
            ), { 'u': utilizador, 'a': ano }).fetchone()
            usados = int(q_used[0]) if q_used is not None else 0
            # calcula dias solicitados
            solicitados = (df - di).days + 1
            if total_fa <= 0:
                return jsonify({'error': 'Não existem dias de férias anuais configurados (FA) para este utilizador/ano'}), 400
            if usados + solicitados > total_fa:
                disponiveis = max(0, total_fa - usados)
                return jsonify({'error': f'Sem dias suficientes. Disponíveis: {disponiveis}'}), 400
            ins = text("""
                INSERT INTO ND (NDSTAMP, EQUIPA, DATA, TIPO, UTILIZADOR, ANO)
                SELECT LEFT(CONVERT(varchar(36), NEWID()), 25), '', :data, 'FERIAS', :util, :ano
            """)
            d = di
            total = 0
            while d <= df:
                db.session.execute(ins, {'data': d, 'util': utilizador, 'ano': ano})
                total += 1
                d += timedelta(days=1)
            db.session.commit()
            return jsonify({'ok': True, 'count': total})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    @app.route('/api/nd/users')
    @login_required
    def api_nd_users():
        try:
            # Apenas utilizadores ativos (INATIVO = 0)
            sql = text("SELECT LOGIN, NOME, ISNULL(COR,'') AS COR FROM US WHERE ISNULL(INATIVO,0)=0 ORDER BY NOME")
            rows = db.session.execute(sql).fetchall()
            items = [
                {
                    'login': r[0],
                    'nome': r[1],
                    'cor': r[2] or '#94a3b8'
                }
                for r in rows
            ]
            return jsonify({'users': items})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # Tesouraria
    @app.route('/tesouraria')
    @login_required
    def tesouraria_page():
        return render_template('tesouraria.html', page_title='Tesouraria')

    @app.route('/generic/api/tesouraria/contas')
    @login_required
    def api_tesouraria_contas():
        try:
            sql = text("""
                SELECT BANCO, CONTA, ORDEM, NOCONTA
                FROM V_BL
                ORDER BY ORDEM, BANCO, CONTA
            """)
            rows = db.session.execute(sql).mappings().all()
            return jsonify([dict(r) for r in rows])
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/generic/api/tesouraria')
    @login_required
    def api_tesouraria():
        try:
            start = request.args.get('start')
            end = request.args.get('end')
            account = (request.args.get('account') or '').strip()
            if not start or not end:
                return jsonify({'error': 'Parâmetros start/end obrigatórios'}), 400
            base_sql = """
                SELECT DATAENTRADA AS DATA, TIPOLINHA AS TIPO, SUM(VALOR) AS VALOR, ISNULL(NoConta, 1) AS NOCONTA
                FROM DBO.V_ENTRADAS_TESOURARIA
                WHERE DATAENTRADA BETWEEN :start AND :end
            """
            params = {'start': start, 'end': end}
            if account:
                # As previsões podem vir sem NoConta; por defeito, assumimos que pertencem à conta 1.
                base_sql += " AND ISNULL(NoConta, 1) = :account"
                params['account'] = account
            base_sql += " GROUP BY DATAENTRADA, TIPOLINHA, ISNULL(NoConta, 1) ORDER BY DATAENTRADA, TIPOLINHA"
            sql = text(base_sql)
            rows = db.session.execute(sql, params).mappings().all()
            return jsonify([dict(r) for r in rows])
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/generic/api/tesouraria/ba')
    @login_required
    def api_tesouraria_ba():
        """
        Movimentos reais de tesouraria (BA) por dia:
        - Entradas: soma EENTRADA
        - Saídas: soma ESAIDA
        Fonte: dbo.V_BA (na BD GESTAO)
        """
        try:
            start = request.args.get('start')
            end = request.args.get('end')
            account = (request.args.get('account') or '').strip()
            if not start or not end:
                return jsonify({'error': 'Parâmetros start/end obrigatórios'}), 400

            where_account = ""
            params = {'start': start, 'end': end}
            if account:
                where_account = " AND BA.NOCONTA = :account"
                params['account'] = account

            sql = text(f"""
                SELECT
                    CAST(BA.DATA AS date) AS DATA,
                    SUM(ISNULL(BA.EENTRADA, 0)) AS EENTRADA,
                    SUM(ISNULL(BA.ESAIDA, 0)) AS ESAIDA
                FROM dbo.V_BA AS BA
                WHERE CAST(BA.DATA AS date) BETWEEN :start AND :end
                  AND (ISNULL(BA.EENTRADA, 0) <> 0 OR ISNULL(BA.ESAIDA, 0) <> 0)
                  {where_account}
                GROUP BY CAST(BA.DATA AS date)
                ORDER BY CAST(BA.DATA AS date)
            """)
            rows = db.session.execute(sql, params).mappings().all()
            out = []
            for r in rows:
                d = r.get('DATA')
                if isinstance(d, (datetime, date)):
                    d = d.strftime('%Y-%m-%d')
                else:
                    d = str(d) if d is not None else ''
                out.append({
                    'DATA': d,
                    'EENTRADA': float(r.get('EENTRADA') or 0),
                    'ESAIDA': float(r.get('ESAIDA') or 0)
                })
            return jsonify(out)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/generic/api/tesouraria/ba/saldo_base')
    @login_required
    def api_tesouraria_ba_saldo_base():
        """
        Saldo base (acumulado) antes de uma data (exclusive).
        Query: ?before=YYYY-MM-DD
        Retorna: { "base": <float> }
        """
        try:
            before = (request.args.get('before') or '').strip()
            account = (request.args.get('account') or '').strip()
            if not before:
                return jsonify({'error': 'Parâmetro before obrigatório'}), 400

            where_account = ""
            params = {'before': before}
            if account:
                where_account = " AND BA.NOCONTA = :account"
                params['account'] = account

            sql = text(f"""
                SELECT
                    SUM(ISNULL(BA.EENTRADA, 0) - ISNULL(BA.ESAIDA, 0)) AS BASE
                FROM dbo.V_BA AS BA
                WHERE CAST(BA.DATA AS date) < :before
                  AND (ISNULL(BA.EENTRADA, 0) <> 0 OR ISNULL(BA.ESAIDA, 0) <> 0)
                  {where_account}
            """)
            row = db.session.execute(sql, params).mappings().first() or {}
            base = float(row.get('BASE') or 0)
            return jsonify({'base': base})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/generic/api/tesouraria/ba/detalhe')
    @login_required
    def api_tesouraria_ba_detalhe():
        """
        Detalhe de movimentos reais (V_BA) num dia.
        Query: ?date=YYYY-MM-DD&kind=in|out
        """
        try:
            d = (request.args.get('date') or '').strip()
            kind = (request.args.get('kind') or '').strip().lower()
            account = (request.args.get('account') or '').strip()
            if not d:
                return jsonify({'error': 'Parâmetro date obrigatório'}), 400
            if kind not in ('in', 'out'):
                return jsonify({'error': 'Parâmetro kind inválido (in|out)'}), 400

            if kind == 'in':
                where_kind = "ISNULL(BA.EENTRADA,0) <> 0"
                value_col = "ISNULL(BA.EENTRADA,0)"
            else:
                where_kind = "ISNULL(BA.ESAIDA,0) <> 0"
                value_col = "ISNULL(BA.ESAIDA,0)"

            where_account = ""
            params = {'d': d}
            if account:
                where_account = " AND BA.NOCONTA = :account"
                params['account'] = account

            sql = text(f"""
                SELECT
                    CAST(BA.DATA AS date) AS DATA,
                    ISNULL(BA.BASTAMP,'') AS BASTAMP,
                    ISNULL(BA.DOCUMENTO,'') AS DOCUMENTO,
                    ISNULL(BA.DESCRICAO,'') AS DESCRICAO,
                    {value_col} AS VALOR
                FROM dbo.V_BA AS BA
                WHERE CAST(BA.DATA AS date) = :d
                  AND {where_kind}
                  {where_account}
                ORDER BY ISNULL(BA.DOCUMENTO,''), ISNULL(BA.DESCRICAO,'')
            """)
            rows = db.session.execute(sql, params).mappings().all()
            out = []
            total = 0.0
            for r in rows:
                val = float(r.get('VALOR') or 0)
                total += val
                data_val = r.get('DATA')
                if isinstance(data_val, (datetime, date)):
                    data_str = data_val.strftime('%Y-%m-%d')
                else:
                    data_str = str(data_val) if data_val is not None else ''
                out.append({
                    'data': data_str,
                    'bastamp': r.get('BASTAMP') or '',
                    'documento': r.get('DOCUMENTO') or '',
                    'descricao': r.get('DESCRICAO') or '',
                    'valor': round(val, 2)
                })

            return jsonify({'date': d, 'kind': kind, 'rows': out, 'total': round(total, 2)})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/generic/api/tesouraria/ba/extrato')
    @login_required
    def api_tesouraria_ba_extrato():
        """
        Extrato de movimentos reais (V_BA) num intervalo.
        Query: ?start=YYYY-MM-DD&end=YYYY-MM-DD
        Retorna linhas normalizadas:
          { DATA, KIND: in|out, DOCUMENTO, DESCRICAO, VALOR }
        """
        try:
            start = (request.args.get('start') or '').strip()
            end = (request.args.get('end') or '').strip()
            account = (request.args.get('account') or '').strip()
            if not start or not end:
                return jsonify({'error': 'Parâmetros start/end obrigatórios'}), 400

            where_account = ""
            params = {'start': start, 'end': end}
            if account:
                where_account = " AND BA.NOCONTA = :account"
                params['account'] = account

            sql = text("""
                SELECT
                    CAST(BA.DATA AS date) AS DATA,
                    'in' AS KIND,
                    ISNULL(BA.DOCUMENTO,'') AS DOCUMENTO,
                    ISNULL(BA.DESCRICAO,'') AS DESCRICAO,
                    ISNULL(BA.EENTRADA,0) AS VALOR
                FROM dbo.V_BA AS BA
                WHERE CAST(BA.DATA AS date) BETWEEN :start AND :end
                  AND ISNULL(BA.EENTRADA,0) <> 0
            """ + where_account + """

                UNION ALL

                SELECT
                    CAST(BA.DATA AS date) AS DATA,
                    'out' AS KIND,
                    ISNULL(BA.DOCUMENTO,'') AS DOCUMENTO,
                    ISNULL(BA.DESCRICAO,'') AS DESCRICAO,
                    ISNULL(BA.ESAIDA,0) AS VALOR
                FROM dbo.V_BA AS BA
                WHERE CAST(BA.DATA AS date) BETWEEN :start AND :end
                  AND ISNULL(BA.ESAIDA,0) <> 0
            """ + where_account + """

                ORDER BY DATA, KIND, DOCUMENTO, DESCRICAO
            """)
            rows = db.session.execute(sql, params).mappings().all()
            out = []
            for r in rows:
                d = r.get('DATA')
                if isinstance(d, (datetime, date)):
                    d = d.strftime('%Y-%m-%d')
                else:
                    d = str(d) if d is not None else ''
                out.append({
                    'DATA': d,
                    'KIND': (r.get('KIND') or '').strip(),
                    'DOCUMENTO': r.get('DOCUMENTO') or '',
                    'DESCRICAO': r.get('DESCRICAO') or '',
                    'VALOR': round(float(r.get('VALOR') or 0), 2)
                })
            return jsonify(out)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # -----------------------------
    # Contas Correntes - Fornecedores
    # -----------------------------
    @app.route('/cc_fornecedores')
    @app.route('/contas-correntes-fornecedores')
    @login_required
    def cc_fornecedores_page():
        return render_template('cc_fornecedores.html', page_title='Contas Correntes - Fornecedores')

    # Alias para abrir FO sem o prefixo /generic (usado em links do ecrã de CC)
    @app.route('/fo_compras_form/', defaults={'record_stamp': None})
    @app.route('/fo_compras_form/<record_stamp>')
    @login_required
    def fo_compras_form_alias(record_stamp):
        if record_stamp:
            return redirect(url_for('generic.fo_compras_form', record_stamp=record_stamp))
        return redirect(url_for('generic.fo_compras_form'))

    @app.route('/api/cc_fornecedores/resumo')
    @login_required
    def api_cc_fornecedores_resumo():
        """
        Resumo por fornecedor (saldo em aberto).
        Query:
          - q (opcional): pesquisa por NO/NOME
          - pendentes=1: apenas fornecedores com saldo em aberto != 0
        """
        try:
            q = (request.args.get('q') or '').strip()
            pendentes = (request.args.get('pendentes') or '').strip() in ('1', 'true', 'True')

            # Fonte: dbo.V_FC (BD GESTAO).
            # Fornecedores: a dÃ­vida em aberto deve ficar positiva (normalmente vem do lado do crÃ©dito).
            #   (ECRED - ECREDF) - (EDEB - EDEBF)
            open_expr = "(ISNULL(ECRED,0) - ISNULL(ECREDF,0)) - (ISNULL(EDEB,0) - ISNULL(EDEBF,0))"

            where = []
            params = {}
            if q:
                where.append("(CAST(NO AS varchar(50)) LIKE :q OR NOME LIKE :q)")
                params['q'] = f"%{q}%"

            where_sql = ("WHERE " + " AND ".join(where)) if where else ""
            having_sql = f"HAVING ABS(SUM({open_expr})) > 0.005" if pendentes else ""

            sql = text(f"""
                SELECT
                    NO,
                    MAX(NOME) AS NOME,
                    SUM({open_expr}) AS SALDO_ABERTO
                FROM dbo.V_FC
                {where_sql}
                GROUP BY NO
                {having_sql}
                ORDER BY SUM({open_expr}) DESC, MAX(NOME)
            """)
            rows = db.session.execute(sql, params).mappings().all()

            items = []
            total_divida = 0.0
            total_saldo = 0.0
            for r in rows:
                no = r.get('NO')
                nome = str(r.get('NOME') or '').strip()
                saldo = float(r.get('SALDO_ABERTO') or 0)
                total_saldo += saldo
                divida = saldo if saldo > 0 else 0.0
                total_divida += divida
                items.append({
                    'NO': int(no) if str(no).isdigit() else no,
                    'NOME': nome,
                    'SALDO_ABERTO': round(saldo, 2),
                    'DIVIDA': round(divida, 2)
                })

            return jsonify({
                'total_divida': round(total_divida, 2),
                'total_saldo': round(total_saldo, 2),
                'count_fornecedores': len(items),
                'items': items
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/cc_fornecedores/detalhe')
    @login_required
    def api_cc_fornecedores_detalhe():
        """
        Movimentos de conta corrente por fornecedor.
        Query:
          - no (obrigatório): fornecedor
          - pendentes=1: apenas linhas com aberto != 0
        """
        try:
            no = request.args.get('no', type=int)
            if not no:
                return jsonify({'error': 'Parâmetro no obrigatório'}), 400
            pendentes = (request.args.get('pendentes') or '').strip() in ('1', 'true', 'True')

            open_expr = "(ISNULL(ECRED,0) - ISNULL(ECREDF,0)) - (ISNULL(EDEB,0) - ISNULL(EDEBF,0))"

            where_pend = f"AND ABS({open_expr}) > 0.005" if pendentes else ""
            sql = text(f"""
                SELECT
                    FCSTAMP,
                    CAST(DATALC AS date) AS DATALC,
                    CAST(DATAVEN AS date) AS DATAVEN,
                    ISNULL(CMDESC,'') AS CMDESC,
                    ISNULL(ADOC,'') AS ADOC,
                    ISNULL(EDEB,0) AS EDEB,
                    ISNULL(ECRED,0) AS ECRED,
                    ISNULL(EDEBF,0) AS EDEBF,
                    ISNULL(ECREDF,0) AS ECREDF,
                    ISNULL(MOEDA,'') AS MOEDA,
                    ISNULL(CCUSTO,'') AS CCUSTO,
                    ISNULL(FOSTAMP,'') AS FOSTAMP,
                    {open_expr} AS ABERTO
                FROM dbo.V_FC
                WHERE NO = :no
                {where_pend}
                ORDER BY CAST(DATALC AS date), FCSTAMP
            """)
            rows = db.session.execute(sql, {'no': no}).mappings().all()

            out = []
            total_aberto = 0.0
            for r in rows:
                aberto = float(r.get('ABERTO') or 0)
                total_aberto += aberto
                dlc = r.get('DATALC')
                dven = r.get('DATAVEN')
                out.append({
                    'FCSTAMP': r.get('FCSTAMP') or '',
                    'DATALC': dlc.strftime('%Y-%m-%d') if isinstance(dlc, (datetime, date)) else (str(dlc) if dlc is not None else ''),
                    'DATAVEN': dven.strftime('%Y-%m-%d') if isinstance(dven, (datetime, date)) else (str(dven) if dven is not None else ''),
                    'CMDESC': r.get('CMDESC') or '',
                    'ADOC': r.get('ADOC') or '',
                    'EDEB': round(float(r.get('EDEB') or 0), 2),
                    'ECRED': round(float(r.get('ECRED') or 0), 2),
                    'EDEBF': round(float(r.get('EDEBF') or 0), 2),
                    'ECREDF': round(float(r.get('ECREDF') or 0), 2),
                    'ABERTO': round(aberto, 2),
                    'MOEDA': r.get('MOEDA') or '',
                    'CCUSTO': r.get('CCUSTO') or '',
                    'FOSTAMP': r.get('FOSTAMP') or ''
                })

            return jsonify({'no': no, 'rows': out, 'total_aberto': round(total_aberto, 2)})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/cc_fornecedores/pendentes')
    @login_required
    def api_cc_fornecedores_pendentes():
        """
        Lista movimentos pendentes (em aberto) para assistente de pagamentos.
        Query:
          - q (opcional): pesquisa por NO/NOME/ADOC/CMDESC

        Nota: considera pendente apenas ABERTO > 0 (dívida) para pagamento.
        """
        try:
            q = (request.args.get('q') or '').strip()

            open_expr = "(ISNULL(ECRED,0) - ISNULL(ECREDF,0)) - (ISNULL(EDEB,0) - ISNULL(EDEBF,0))"
            where = [f"({open_expr}) > 0.005"]
            params = {}
            if q:
                where.append("(CAST(NO AS varchar(50)) LIKE :q OR NOME LIKE :q OR ADOC LIKE :q OR CMDESC LIKE :q)")
                params['q'] = f"%{q}%"

            where_sql = "WHERE " + " AND ".join(where)

            def run_query(include_cm: bool):
                cm_sel = "ISNULL(CM,0) AS CM," if include_cm else "CAST(0 AS int) AS CM,"
                sql = text(f"""
                    SELECT
                        FCSTAMP,
                        CAST(DATALC AS date) AS DATALC,
                        CAST(DATAVEN AS date) AS DATAVEN,
                        ISNULL(CMDESC,'') AS CMDESC,
                        ISNULL(ADOC,'') AS ADOC,
                        {cm_sel}
                        ISNULL(NO,0) AS NO,
                        ISNULL(NOME,'') AS NOME,
                        ISNULL(MOEDA,'') AS MOEDA,
                        ISNULL(CCUSTO,'') AS CCUSTO,
                        ISNULL(FOSTAMP,'') AS FOSTAMP,
                        {open_expr} AS ABERTO
                    FROM dbo.V_FC
                    {where_sql}
                    ORDER BY ISNULL(NOME,''), CAST(DATAVEN AS date), CAST(DATALC AS date), FCSTAMP
                """)
                return db.session.execute(sql, params).mappings().all()

            try:
                rows = run_query(include_cm=True)
            except Exception as e:
                # compat: a view V_FC pode nÃ£o ter a coluna CM ainda
                msg = str(e)
                if "Invalid column name 'CM'" in msg or "Invalid column name \"CM\"" in msg:
                    rows = run_query(include_cm=False)
                else:
                    raise

            out = []
            total = 0.0
            for r in rows:
                dlc = r.get('DATALC')
                dven = r.get('DATAVEN')
                aberto = float(r.get('ABERTO') or 0)
                total += aberto
                out.append({
                    'FCSTAMP': (r.get('FCSTAMP') or '').strip(),
                    'DATALC': dlc.strftime('%Y-%m-%d') if isinstance(dlc, (datetime, date)) else (str(dlc) if dlc is not None else ''),
                    'DATAVEN': dven.strftime('%Y-%m-%d') if isinstance(dven, (datetime, date)) else (str(dven) if dven is not None else ''),
                    'CMDESC': r.get('CMDESC') or '',
                    'ADOC': r.get('ADOC') or '',
                    'CM': int(r.get('CM') or 0),
                    'NO': int(r.get('NO') or 0),
                    'NOME': r.get('NOME') or '',
                    'MOEDA': r.get('MOEDA') or '',
                    'CCUSTO': r.get('CCUSTO') or '',
                    'FOSTAMP': r.get('FOSTAMP') or '',
                    'ABERTO': round(aberto, 2)
                })

            return jsonify({'rows': out, 'total': round(total, 2), 'count': len(out)})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # -----------------------------
    # Contas Correntes - Clientes
    # -----------------------------
    @app.route('/cc_clientes')
    @app.route('/contas-correntes-clientes')
    @login_required
    def cc_clientes_page():
        return render_template('cc_clientes.html', page_title='Contas Correntes - Clientes')

    @app.route('/api/cc_clientes/resumo')
    @login_required
    def api_cc_clientes_resumo():
        """
        Resumo por cliente (saldo em aberto).
        Query:
          - q (opcional): pesquisa por NO/NOME
          - pendentes=1: apenas clientes com saldo em aberto != 0
        """
        try:
            q = (request.args.get('q') or '').strip()
            pendentes = (request.args.get('pendentes') or '').strip() in ('1', 'true', 'True')

            # Fonte: dbo.V_CC (BD GESTAO).
            # Clientes: o valor em aberto deve ficar positivo quando o cliente nos deve (normalmente vem do lado do débito).
            #   (EDEB - EDEBF) - (ECRED - ECREDF)
            open_expr = "(ISNULL(EDEB,0) - ISNULL(EDEBF,0)) - (ISNULL(ECRED,0) - ISNULL(ECREDF,0))"

            where = []
            params = {}
            if q:
                where.append("(CAST(NO AS varchar(50)) LIKE :q OR NOME LIKE :q)")
                params['q'] = f"%{q}%"

            where_sql = ("WHERE " + " AND ".join(where)) if where else ""
            having_sql = f"HAVING ABS(SUM({open_expr})) > 0.005" if pendentes else ""

            sql = text(f"""
                SELECT
                    NO,
                    MAX(NOME) AS NOME,
                    SUM({open_expr}) AS SALDO_ABERTO
                FROM dbo.V_CC
                {where_sql}
                GROUP BY NO
                {having_sql}
                ORDER BY SUM({open_expr}) DESC, MAX(NOME)
            """)
            rows = db.session.execute(sql, params).mappings().all()

            items = []
            total_aberto = 0.0
            total_saldo = 0.0
            for r in rows:
                no = r.get('NO')
                nome = str(r.get('NOME') or '').strip()
                saldo = float(r.get('SALDO_ABERTO') or 0)
                total_saldo += saldo
                aberto = saldo if saldo > 0 else 0.0
                total_aberto += aberto
                items.append({
                    'NO': int(no) if str(no).isdigit() else no,
                    'NOME': nome,
                    'SALDO_ABERTO': round(saldo, 2),
                    'ABERTO': round(aberto, 2)
                })

            return jsonify({
                'total_aberto': round(total_aberto, 2),
                'total_saldo': round(total_saldo, 2),
                'count_clientes': len(items),
                'items': items
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/cc_clientes/detalhe')
    @login_required
    def api_cc_clientes_detalhe():
        """
        Movimentos de conta corrente por cliente.
        Query:
          - no (obrigatório): cliente
          - pendentes=1: apenas linhas com aberto != 0
        """
        try:
            no = request.args.get('no', type=int)
            if not no:
                return jsonify({'error': 'Parâmetro no obrigatório'}), 400
            pendentes = (request.args.get('pendentes') or '').strip() in ('1', 'true', 'True')

            open_expr = "(ISNULL(EDEB,0) - ISNULL(EDEBF,0)) - (ISNULL(ECRED,0) - ISNULL(ECREDF,0))"
            where_pend = f"AND ABS({open_expr}) > 0.005" if pendentes else ""

            sql = text(f"""
                SELECT
                    CCSTAMP,
                    CAST(DATALC AS date) AS DATALC,
                    CAST(DATAVEN AS date) AS DATAVEN,
                    ISNULL(CMDESC,'') AS CMDESC,
                    ISNULL(NRDOC,'') AS NRDOC,
                    ISNULL(EDEB,0) AS EDEB,
                    ISNULL(ECRED,0) AS ECRED,
                    ISNULL(EDEBF,0) AS EDEBF,
                    ISNULL(ECREDF,0) AS ECREDF,
                    ISNULL(MOEDA,'') AS MOEDA,
                    ISNULL(CCUSTO,'') AS CCUSTO,
                    ISNULL(FTSTAMP,'') AS FTSTAMP,
                    ISNULL(CM,0) AS CM,
                    {open_expr} AS ABERTO
                FROM dbo.V_CC
                WHERE NO = :no
                {where_pend}
                ORDER BY CAST(DATALC AS date), CCSTAMP
            """)
            rows = db.session.execute(sql, {'no': no}).mappings().all()

            out = []
            total_aberto = 0.0
            for r in rows:
                aberto = float(r.get('ABERTO') or 0)
                total_aberto += aberto
                dlc = r.get('DATALC')
                dven = r.get('DATAVEN')
                out.append({
                    'CCSTAMP': r.get('CCSTAMP') or '',
                    'DATALC': dlc.strftime('%Y-%m-%d') if isinstance(dlc, (datetime, date)) else (str(dlc) if dlc is not None else ''),
                    'DATAVEN': dven.strftime('%Y-%m-%d') if isinstance(dven, (datetime, date)) else (str(dven) if dven is not None else ''),
                    'CMDESC': r.get('CMDESC') or '',
                    'NRDOC': r.get('NRDOC') or '',
                    'EDEB': round(float(r.get('EDEB') or 0), 2),
                    'ECRED': round(float(r.get('ECRED') or 0), 2),
                    'EDEBF': round(float(r.get('EDEBF') or 0), 2),
                    'ECREDF': round(float(r.get('ECREDF') or 0), 2),
                    'ABERTO': round(aberto, 2),
                    'MOEDA': r.get('MOEDA') or '',
                    'CCUSTO': r.get('CCUSTO') or '',
                    'FTSTAMP': r.get('FTSTAMP') or '',
                    'CM': int(r.get('CM') or 0),
                })

            return jsonify({'no': no, 'rows': out, 'total_aberto': round(total_aberto, 2)})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/cc_clientes/pendentes')
    @login_required
    def api_cc_clientes_pendentes():
        """
        Lista movimentos pendentes (em aberto) para assistente de recebimentos.
        Query:
          - q (opcional): pesquisa por NO/NOME/NRDOC/CMDESC

        Nota: considera pendente quando ABS(ABERTO) > 0 (a receber / a crédito).
        """
        try:
            q = (request.args.get('q') or '').strip()

            open_expr = "(ISNULL(EDEB,0) - ISNULL(EDEBF,0)) - (ISNULL(ECRED,0) - ISNULL(ECREDF,0))"
            where = [f"ABS(({open_expr})) > 0.005"]
            params = {}
            if q:
                where.append("(CAST(NO AS varchar(50)) LIKE :q OR NOME LIKE :q OR CAST(NRDOC AS varchar(50)) LIKE :q OR CMDESC LIKE :q)")
                params['q'] = f"%{q}%"

            where_sql = "WHERE " + " AND ".join(where)

            sql = text(f"""
                SELECT
                    CCSTAMP,
                    CAST(DATALC AS date) AS DATALC,
                    CAST(DATAVEN AS date) AS DATAVEN,
                    ISNULL(CMDESC,'') AS CMDESC,
                    ISNULL(NRDOC,0) AS NRDOC,
                    ISNULL(CM,0) AS CM,
                    ISNULL(NO,0) AS NO,
                    ISNULL(NOME,'') AS NOME,
                    ISNULL(MOEDA,'') AS MOEDA,
                    ISNULL(CCUSTO,'') AS CCUSTO,
                    ISNULL(FTSTAMP,'') AS FTSTAMP,
                    {open_expr} AS ABERTO
                FROM dbo.V_CC
                {where_sql}
                ORDER BY ISNULL(NOME,''), CAST(DATAVEN AS date), CAST(DATALC AS date), CCSTAMP
            """)
            rows = db.session.execute(sql, params).mappings().all()

            out = []
            total = 0.0
            for r in rows:
                dlc = r.get('DATALC')
                dven = r.get('DATAVEN')
                aberto = float(r.get('ABERTO') or 0)
                total += aberto
                out.append({
                    'CCSTAMP': (r.get('CCSTAMP') or '').strip(),
                    'DATALC': dlc.strftime('%Y-%m-%d') if isinstance(dlc, (datetime, date)) else (str(dlc) if dlc is not None else ''),
                    'DATAVEN': dven.strftime('%Y-%m-%d') if isinstance(dven, (datetime, date)) else (str(dven) if dven is not None else ''),
                    'CMDESC': r.get('CMDESC') or '',
                    'NRDOC': int(r.get('NRDOC') or 0),
                    'CM': int(r.get('CM') or 0),
                    'NO': int(r.get('NO') or 0),
                    'NOME': r.get('NOME') or '',
                    'MOEDA': r.get('MOEDA') or '',
                    'CCUSTO': r.get('CCUSTO') or '',
                    'FTSTAMP': r.get('FTSTAMP') or '',
                    'ABERTO': round(aberto, 2)
                })

            return jsonify({'rows': out, 'total': round(total, 2), 'count': len(out)})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/cc_clientes/recebimentos/criar', methods=['POST'])
    @login_required
    def api_cc_clientes_recebimentos_criar():
        """
        Cria registos RE/RL a partir de movimentos pendentes selecionados.
        Body:
          { "rec_date": "YYYY-MM-DD", "items": [ { CCSTAMP, NO, NOME, CMDESC, NRDOC, DATALC, DATAVEN, ABERTO, PAYVAL, MOEDA } ... ] }
        Cria 1 RE por cliente e 1 RL por movimento.
        """
        try:
            body = request.get_json(silent=True) or {}
            rec_date = str(body.get('rec_date') or '').strip()
            items = body.get('items') or []
            if not rec_date:
                return jsonify({'error': 'rec_date obrigatório (YYYY-MM-DD)'}), 400
            if not isinstance(items, list) or not items:
                return jsonify({'error': 'items obrigatório'}), 400

            try:
                d = date.fromisoformat(rec_date)
            except Exception:
                return jsonify({'error': 'rec_date inválido (YYYY-MM-DD)'}), 400
            base_dt = datetime.combine(d, datetime.min.time())
            ano = d.year

            # agrupar por cliente
            by_no = {}
            for it in items:
                no = int(it.get('NO') or 0)
                if not no:
                    continue
                nome = str(it.get('NOME') or '').strip()
                ccstamp = str(it.get('CCSTAMP') or '').strip()
                if not ccstamp:
                    continue
                aberto = float(it.get('ABERTO') or 0)
                payval = it.get('PAYVAL', None)
                pay = float(payval) if payval is not None else aberto

                # Permitir também créditos (ABERTO < 0): aceita valores positivos e negativos,
                # mas força o sinal e limita à faixa válida do "aberto".
                if not (abs(aberto) > 0.005):
                    continue
                if aberto > 0:
                    # entre 0 e aberto
                    if pay < 0:
                        pay = 0.0
                    if pay > aberto:
                        pay = aberto
                else:
                    # aberto < 0: entre aberto e 0 (valores negativos)
                    if pay > 0:
                        pay = 0.0
                    if pay < aberto:
                        pay = aberto
                if abs(pay) <= 0.00001:
                    continue
                if no not in by_no:
                    by_no[no] = {'NO': no, 'NOME': nome, 'items': []}
                by_no[no]['items'].append({**it, 'PAYVAL': pay})

            if not by_no:
                return jsonify({'error': 'Nenhum movimento válido selecionado.'}), 400

            created = []
            for grp in by_no.values():
                no = grp['NO']
                nome = grp['NOME'] or ''
                movs = grp['items']
                total = sum(float(x.get('PAYVAL') or 0) for x in movs)

                # Colunas disponíveis (para compatibilidade entre bases)
                re_cols = set(
                    r['COLUMN_NAME'].upper()
                    for r in (
                        db.session.execute(
                            text("""
                                SELECT COLUMN_NAME
                                FROM INFORMATION_SCHEMA.COLUMNS
                                WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'RE'
                            """)
                        ).mappings().all()
                        or []
                    )
                )
                rl_cols = set(
                    r['COLUMN_NAME'].upper()
                    for r in (
                        db.session.execute(
                            text("""
                                SELECT COLUMN_NAME
                                FROM INFORMATION_SCHEMA.COLUMNS
                                WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'RL'
                            """)
                        ).mappings().all()
                        or []
                    )
                )

                # RNO sequencial simples
                rno_row = db.session.execute(text("SELECT ISNULL(MAX(RNO),0) + 1 AS N FROM dbo.RE")).mappings().first() or {}
                rno = int(rno_row.get('N') or 1)

                restamp = new_stamp()
                moeda = (movs[0].get('MOEDA') or 'EUR').strip()[:11]

                re_cols_sql = [
                    'RESTAMP', 'NMDOC', 'RNO', 'RDATA', 'NOME', 'TOTAL', 'ETOTAL',
                    'NO', 'REANO',
                    'OLCODIGO', 'TELOCAL', 'MOEDA', 'CONTADO', 'PROCESS', 'PROCDATA', 'OLLOCAL', 'PLANO', 'TIPO', 'PAIS', 'SYNC'
                ]
                re_vals_sql = [
                    ':RESTAMP', ':NMDOC', ':RNO', ':RDATA', ':NOME', ':TOTAL', ':ETOTAL',
                    ':NO', ':REANO',
                    ':OLCODIGO', ':TELOCAL', ':MOEDA', ':CONTADO', ':PROCESS', ':PROCDATA', ':OLLOCAL', ':PLANO', ':TIPO', ':PAIS', ':SYNC'
                ]
                # Algumas bases usam NDOC, outras NDOS.
                if 'NDOC' in re_cols:
                    re_cols_sql.insert(7, 'NDOC')
                    re_vals_sql.insert(7, ':NDOC')
                if 'NDOS' in re_cols:
                    re_cols_sql.insert(7, 'NDOS')
                    re_vals_sql.insert(7, ':NDOS')

                ins_re = text(f"""
                    INSERT INTO dbo.RE
                    ({", ".join(re_cols_sql)})
                    VALUES
                    ({", ".join(re_vals_sql)})
                """)
                re_params = {
                    'RESTAMP': restamp,
                    'NMDOC': 'Normal',
                    'RNO': rno,
                    'RDATA': base_dt,
                    'NOME': nome[:55],
                    'TOTAL': total,
                    'ETOTAL': total,
                    'NO': no,
                    'REANO': ano,
                    'OLCODIGO': 'R10001',
                    'TELOCAL': 'B',
                    'MOEDA': moeda,
                    'CONTADO': 1,
                    'PROCESS': 1,
                    'PROCDATA': base_dt,
                    'OLLOCAL': 'Santander  DO',
                    'PLANO': 0,
                    'TIPO': '',
                    'PAIS': 1,
                    'SYNC': 0
                }
                if 'NDOC' in re_cols:
                    re_params['NDOC'] = 1
                if 'NDOS' in re_cols:
                    re_params['NDOS'] = 1
                db.session.execute(ins_re, re_params)

                # RL: algumas bases podem ter VAL (em vez de EVAL). Queremos:
                #   - VAL/EVAL = valor pendente (ABERTO)
                #   - EREC = valor recebido (PAYVAL)
                rl_value_col = 'EVAL' if 'EVAL' in rl_cols else ('VAL' if 'VAL' in rl_cols else 'EVAL')
                ins_rl = text(f"""
                    INSERT INTO dbo.RL
                    (RLSTAMP, NDOC, RNO, CDESC, NRDOC, DATALC, DATAVEN, RESTAMP, CCSTAMP, CM, {rl_value_col}, EREC, PROCESS, MOEDA, RDATA)
                    VALUES
                    (:RLSTAMP, :NDOC, :RNO, :CDESC, :NRDOC, :DATALC, :DATAVEN, :RESTAMP, :CCSTAMP, :CM, :VALPEND, :EREC, :PROCESS, :MOEDA, :RDATA)
                """)
                for m in movs:
                    rlstamp = new_stamp()
                    dlc = str(m.get('DATALC') or '').strip()
                    dven = str(m.get('DATAVEN') or '').strip()
                    try:
                        dlc_dt = datetime.combine(date.fromisoformat(dlc), datetime.min.time()) if dlc else base_dt
                    except Exception:
                        dlc_dt = base_dt
                    try:
                        dven_dt = datetime.combine(date.fromisoformat(dven), datetime.min.time()) if dven else base_dt
                    except Exception:
                        dven_dt = base_dt

                    aberto0 = float(m.get('ABERTO') or 0)
                    recebido = float(m.get('PAYVAL') or 0)

                    db.session.execute(ins_rl, {
                        'RLSTAMP': rlstamp,
                        'NDOC': 1,
                        'RNO': rno,
                        'CDESC': (str(m.get('CMDESC') or '')[:20]),
                        'NRDOC': int(m.get('NRDOC') or 0),
                        'DATALC': dlc_dt,
                        'DATAVEN': dven_dt,
                        'RESTAMP': restamp,
                        'CCSTAMP': (str(m.get('CCSTAMP') or '')[:25]),
                        'CM': int(m.get('CM') or 0),
                        'VALPEND': aberto0,
                        'EREC': recebido,
                        'PROCESS': 1,
                        'MOEDA': (str(m.get('MOEDA') or moeda)[:11]),
                        'RDATA': base_dt
                    })

                created.append({'RESTAMP': restamp, 'RNO': rno, 'NO': no, 'TOTAL': round(total, 2)})

            db.session.commit()
            return jsonify({'ok': True, 'created': created})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    @app.route('/api/cc_fornecedores/pagamentos/criar', methods=['POST'])
    @login_required
    def api_cc_fornecedores_pagamentos_criar():
        """
        Cria registos PO/PL a partir de movimentos pendentes selecionados.
        Body:
          { "items": [ { FCSTAMP, NO, NOME, CMDESC, ADOC, DATALC, DATAVEN, ABERTO, MOEDA, CCUSTO } ... ] }
        Cria 1 PO por fornecedor e 1 PL por movimento.
        """
        try:
            body = request.get_json(silent=True) or {}
            pay_date_str = str(body.get('pay_date') or '').strip()
            items = body.get('items') or []
            if not isinstance(items, list) or not items:
                return jsonify({'error': 'Sem movimentos selecionados.'}), 400

            # normalizar e validar
            cleaned = []
            for it in items:
                if not isinstance(it, dict):
                    continue
                no = int(it.get('NO') or 0)
                fcstamp = str(it.get('FCSTAMP') or '').strip()
                nome = str(it.get('NOME') or '').strip()
                if not no or not fcstamp:
                    continue
                try:
                    aberto = float(it.get('ABERTO') or 0)
                except Exception:
                    aberto = 0.0
                if aberto <= 0:
                    continue
                try:
                    payval = float(it.get('PAYVAL') if it.get('PAYVAL') is not None else it.get('EVAL') or aberto)
                except Exception:
                    payval = aberto
                if payval <= 0:
                    continue
                if payval > aberto:
                    payval = aberto
                cleaned.append({
                    'NO': no,
                    'NOME': nome,
                    'FCSTAMP': fcstamp[:25],
                    'CMDESC': str(it.get('CMDESC') or '').strip()[:20],
                    'ADOC': str(it.get('ADOC') or '').strip()[:50],
                    'DATALC': str(it.get('DATALC') or '').strip(),
                    'DATAVEN': str(it.get('DATAVEN') or '').strip(),
                    'CM': int(it.get('CM') or 0),
                    'EVAL': payval,
                    'ABERTO': aberto,
                    'MOEDA': str(it.get('MOEDA') or '').strip()[:11],
                    'CCUSTO': str(it.get('CCUSTO') or '').strip()[:20],
                })
                if len(cleaned) >= 2000:
                    break
            if not cleaned:
                return jsonify({'error': 'Sem movimentos válidos.'}), 400

            # agrupar por fornecedor
            by_no = {}
            for it in cleaned:
                by_no.setdefault(it['NO'], {'NO': it['NO'], 'NOME': it['NOME'], 'items': []})
                by_no[it['NO']]['items'].append(it)

            def new_stamp():
                import uuid
                return uuid.uuid4().hex.upper()[:25]

            # Data do pagamento (sem hora)
            try:
                base_date = date.fromisoformat(pay_date_str) if pay_date_str else date.today()
            except Exception:
                base_date = date.today()
            base_dt = datetime.combine(base_date, datetime.min.time())
            ano = int(base_date.strftime('%Y'))

            # Lote sequencial (1 por execução do assistente)
            lote_row = db.session.execute(text("SELECT ISNULL(MAX(LOTE),0) + 1 AS N FROM dbo.PO")).mappings().first() or {}
            lote = int(lote_row.get('N') or 1)

            created = []
            # Algumas BD usam DVALOR, outras DTVALOR (ou ambas). Detecta e usa as que existirem.
            po_cols = set(
                r['COLUMN_NAME'].upper()
                for r in (
                    db.session.execute(
                        text("""
                            SELECT COLUMN_NAME
                            FROM INFORMATION_SCHEMA.COLUMNS
                            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'PO'
                        """)
                    ).mappings().all()
                    or []
                )
            )
            has_dvalor = 'DVALOR' in po_cols
            has_dtvalor = 'DTVALOR' in po_cols

            for grp in by_no.values():
                no = grp['NO']
                nome = grp['NOME'] or ''
                movs = grp['items']
                total = sum(float(x['EVAL'] or 0) for x in movs)

                # RNO sequencial simples
                rno_row = db.session.execute(text("SELECT ISNULL(MAX(RNO),0) + 1 AS N FROM dbo.PO")).mappings().first() or {}
                rno = int(rno_row.get('N') or 1)

                postamp = new_stamp()
                moeda = (movs[0].get('MOEDA') or 'EUR').strip()[:11]
                ccusto = (movs[0].get('CCUSTO') or '').strip()[:20]
                fcstamp_head = (movs[0].get('FCSTAMP') or '').strip()[:25]
                cmdesc_head = (movs[0].get('CMDESC') or 'PAGAMENTO').strip()[:20]
                adoc_head = (movs[0].get('ADOC') or '').strip()[:50]

                po_cols_sql = [
                    'POSTAMP', 'RNO', 'RDATA', 'NOME', 'TOTAL', 'ETOTAL', 'PAIS', 'NO', 'POANO',
                    'OLCODIGO', 'TELOCAL', 'MOEDA', 'CONTADO',
                    'PROCESS', 'PROCDATA', 'OLLOCAL', 'CCUSTO', 'PLANO', 'OLSTAMP', 'FCSTAMP', 'CM', 'CMDESC', 'ADOC', 'LOTE'
                ]
                po_vals_sql = [
                    ':POSTAMP', ':RNO', ':RDATA', ':NOME', ':TOTAL', ':ETOTAL', ':PAIS', ':NO', ':POANO',
                    ':OLCODIGO', ':TELOCAL', ':MOEDA', ':CONTADO',
                    ':PROCESS', ':PROCDATA', ':OLLOCAL', ':CCUSTO', ':PLANO', ':OLSTAMP', ':FCSTAMP', ':CM', ':CMDESC', ':ADOC', ':LOTE'
                ]
                if has_dvalor:
                    po_cols_sql.insert(9, 'DVALOR')
                    po_vals_sql.insert(9, ':DVALOR')
                if has_dtvalor:
                    po_cols_sql.insert(9, 'DTVALOR')
                    po_vals_sql.insert(9, ':DTVALOR')

                ins_po = text(f"""
                    INSERT INTO dbo.PO
                    ({", ".join(po_cols_sql)})
                    VALUES
                    ({", ".join(po_vals_sql)})
                """)

                po_params = {
                    'POSTAMP': postamp,
                    'RNO': rno,
                    'RDATA': base_dt,
                    'NOME': nome[:55],
                    'TOTAL': total,
                    'ETOTAL': total,
                    'PAIS': 0,
                    'NO': no,
                    'POANO': ano,
                    'OLCODIGO': 'P10001',
                    'TELOCAL': 'B',
                    'MOEDA': moeda,
                    'CONTADO': 1,
                    'PROCESS': 1,
                    'PROCDATA': base_dt,
                    'OLLOCAL': 'Santander  DO',
                    'CCUSTO': ccusto,
                    'PLANO': 0,
                    'OLSTAMP': '',
                    'FCSTAMP': fcstamp_head,
                    'CM': 104,
                    'CMDESC': 'N/Trfa.',
                    'ADOC': str(rno),
                    'LOTE': lote
                }
                if has_dvalor:
                    po_params['DVALOR'] = base_dt
                if has_dtvalor:
                    po_params['DTVALOR'] = base_dt

                db.session.execute(ins_po, po_params)

                ins_pl = text("""
                    INSERT INTO dbo.PL
                    (POSTAMP, PLSTAMP, RNO, CDESC, ADOC, DATALC, DATAVEN, FCSTAMP, CM, EVAL, EREC, PROCESS, MOEDA, RDATA)
                    VALUES
                    (:POSTAMP, :PLSTAMP, :RNO, :CDESC, :ADOC, :DATALC, :DATAVEN, :FCSTAMP, :CM, :EVAL, :EREC, :PROCESS, :MOEDA, :RDATA)
                """)
                for m in movs:
                    plstamp = new_stamp()
                    # datas como datetime (YYYY-MM-DD)
                    try:
                        dlc_dt = datetime.fromisoformat(m['DATALC'])
                    except Exception:
                        dlc_dt = base_dt
                    try:
                        dven_dt = datetime.fromisoformat(m['DATAVEN'])
                    except Exception:
                        dven_dt = dlc_dt

                    dlc = datetime.combine(dlc_dt.date(), datetime.min.time())
                    dven = datetime.combine(dven_dt.date(), datetime.min.time())
                    cm_line = int(m.get('CM') or 0)

                    db.session.execute(ins_pl, {
                        'POSTAMP': postamp,
                        'PLSTAMP': plstamp,
                        'RNO': rno,
                        'CDESC': (m.get('CMDESC') or '')[:20],
                        'ADOC': (m.get('ADOC') or '')[:50],
                        'DATALC': dlc,
                        'DATAVEN': dven,
                        'FCSTAMP': (m.get('FCSTAMP') or '')[:25],
                        'CM': cm_line,
                        'EVAL': float(m.get('EVAL') or 0),
                        'EREC': float(m.get('EVAL') or 0),
                        'PROCESS': 1,
                        'MOEDA': (m.get('MOEDA') or moeda)[:11],
                        'RDATA': base_dt
                    })

                created.append({'NO': no, 'NOME': nome, 'POSTAMP': postamp, 'RNO': rno, 'TOTAL': round(total, 2), 'COUNT': len(movs), 'LOTE': lote})

            db.session.commit()
            return jsonify({'ok': True, 'lote': lote, 'created': created})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    # -----------------------------
    # Pagamentos (PO)
    # -----------------------------
    @app.route('/pagamentos')
    @login_required
    def pagamentos_page():
        return render_template('pagamentos.html', page_title='Pagamentos')

    @app.route('/api/pagamentos')
    @login_required
    def api_pagamentos_list():
        """
        Lista pagamentos (PO) com filtros simples.
        Query:
          - de=YYYY-MM-DD
          - ate=YYYY-MM-DD
          - lote=int
          - q=texto (NO, NOME, ADOC, CMDESC, OLCODIGO, OLLOCAL)
        """
        try:
            de = (request.args.get('de') or '').strip()
            ate = (request.args.get('ate') or '').strip()
            q = (request.args.get('q') or '').strip()
            try:
                lote = int(request.args.get('lote')) if request.args.get('lote') not in (None, '') else None
            except Exception:
                lote = None

            where = []
            params = {}
            if de:
                where.append("CAST(PO.RDATA AS date) >= :de")
                params['de'] = de
            if ate:
                where.append("CAST(PO.RDATA AS date) <= :ate")
                params['ate'] = ate
            if lote is not None:
                where.append("PO.LOTE = :lote")
                params['lote'] = lote
            if q:
                where.append("""(
                    CAST(PO.NO AS varchar(50)) LIKE :q OR
                    PO.NOME LIKE :q OR
                    PO.ADOC LIKE :q OR
                    PO.CMDESC LIKE :q OR
                    PO.OLCODIGO LIKE :q OR
                    PO.OLLOCAL LIKE :q
                )""")
                params['q'] = f"%{q}%"

            where_sql = ("WHERE " + " AND ".join(where)) if where else ""

            sql = text(f"""
                SELECT TOP 2000
                    PO.POSTAMP,
                    PO.RNO,
                    CAST(PO.RDATA AS date) AS RDATA,
                    ISNULL(PO.LOTE,0) AS LOTE,
                    ISNULL(PO.NO,0) AS NO,
                    ISNULL(PO.NOME,'') AS NOME,
                    ISNULL(PO.MOEDA,'') AS MOEDA,
                    ISNULL(PO.ETOTAL,0) AS ETOTAL,
                    ISNULL(PO.OLLOCAL,'') AS OLLOCAL,
                    ISNULL(PO.OLCODIGO,'') AS OLCODIGO,
                    ISNULL(PO.TELOCAL,'') AS TELOCAL,
                    ISNULL(PO.CMDESC,'') AS CMDESC,
                    ISNULL(PO.ADOC,'') AS ADOC
                FROM dbo.PO AS PO
                {where_sql}
                ORDER BY CAST(PO.RDATA AS date) DESC, ISNULL(PO.LOTE,0) DESC, PO.RNO DESC
            """)
            rows = db.session.execute(sql, params).mappings().all()

            out = []
            total = 0.0
            for r in rows:
                d = r.get('RDATA')
                if isinstance(d, (datetime, date)):
                    d = d.strftime('%Y-%m-%d')
                else:
                    d = str(d) if d is not None else ''
                et = float(r.get('ETOTAL') or 0)
                total += et
                out.append({
                    'POSTAMP': r.get('POSTAMP') or '',
                    'RNO': int(r.get('RNO') or 0),
                    'RDATA': d,
                    'LOTE': int(r.get('LOTE') or 0),
                    'NO': int(r.get('NO') or 0),
                    'NOME': r.get('NOME') or '',
                    'MOEDA': r.get('MOEDA') or '',
                    'ETOTAL': round(et, 2),
                    'OLLOCAL': r.get('OLLOCAL') or '',
                    'OLCODIGO': r.get('OLCODIGO') or '',
                    'TELOCAL': r.get('TELOCAL') or '',
                    'CMDESC': r.get('CMDESC') or '',
                    'ADOC': r.get('ADOC') or ''
                })

            return jsonify({'rows': out, 'count': len(out), 'total': round(total, 2)})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/pagamentos/<postamp>')
    @login_required
    def api_pagamentos_detail(postamp):
        """
        Detalhe de um pagamento:
          - Cabeçalho: PO
          - Linhas: PL
        """
        try:
            postamp = (postamp or '').strip()
            if not postamp:
                return jsonify({'error': 'POSTAMP obrigatório'}), 400

            head_sql = text("""
                SELECT
                    PO.POSTAMP,
                    PO.RNO,
                    CAST(PO.RDATA AS date) AS RDATA,
                    ISNULL(PO.LOTE,0) AS LOTE,
                    ISNULL(PO.NO,0) AS NO,
                    ISNULL(PO.NOME,'') AS NOME,
                    ISNULL(PO.ETOTAL,0) AS ETOTAL,
                    ISNULL(PO.MOEDA,'') AS MOEDA,
                    ISNULL(PO.OLCODIGO,'') AS OLCODIGO,
                    ISNULL(PO.OLLOCAL,'') AS OLLOCAL,
                    ISNULL(PO.TELOCAL,'') AS TELOCAL,
                    ISNULL(PO.CM,0) AS CM,
                    ISNULL(PO.CMDESC,'') AS CMDESC,
                    ISNULL(PO.ADOC,'') AS ADOC,
                    ISNULL(PO.PROCESS,0) AS PROCESS
                FROM dbo.PO AS PO
                WHERE PO.POSTAMP = :postamp
            """)
            head = db.session.execute(head_sql, {'postamp': postamp}).mappings().first()
            if not head:
                return jsonify({'error': 'Pagamento não encontrado.'}), 404

            d = head.get('RDATA')
            if isinstance(d, (datetime, date)):
                d = d.strftime('%Y-%m-%d')
            else:
                d = str(d) if d is not None else ''

            header = {
                'POSTAMP': head.get('POSTAMP') or '',
                'RNO': int(head.get('RNO') or 0),
                'RDATA': d,
                'LOTE': int(head.get('LOTE') or 0),
                'NO': int(head.get('NO') or 0),
                'NOME': head.get('NOME') or '',
                'ETOTAL': round(float(head.get('ETOTAL') or 0), 2),
                'MOEDA': head.get('MOEDA') or '',
                'OLCODIGO': head.get('OLCODIGO') or '',
                'OLLOCAL': head.get('OLLOCAL') or '',
                'TELOCAL': head.get('TELOCAL') or '',
                'CM': int(head.get('CM') or 0),
                'CMDESC': head.get('CMDESC') or '',
                'ADOC': head.get('ADOC') or '',
                'PROCESS': int(head.get('PROCESS') or 0),
            }

            lines_sql = text("""
                SELECT
                    PL.PLSTAMP,
                    PL.RNO,
                    CAST(PL.RDATA AS date) AS RDATA,
                    ISNULL(PL.CDESC,'') AS CDESC,
                    ISNULL(PL.ADOC,'') AS ADOC,
                    CAST(PL.DATALC AS date) AS DATALC,
                    CAST(PL.DATAVEN AS date) AS DATAVEN,
                    ISNULL(PL.FCSTAMP,'') AS FCSTAMP,
                    ISNULL(PL.CM,0) AS CM,
                    ISNULL(PL.EVAL,0) AS EVAL,
                    ISNULL(PL.EREC,0) AS EREC,
                    ISNULL(PL.PROCESS,0) AS PROCESS,
                    ISNULL(PL.MOEDA,'') AS MOEDA
                FROM dbo.PL AS PL
                WHERE PL.POSTAMP = :postamp
                ORDER BY CAST(PL.DATAVEN AS date), CAST(PL.DATALC AS date), PL.PLSTAMP
            """)
            rows = db.session.execute(lines_sql, {'postamp': postamp}).mappings().all()

            lines = []
            for r in rows:
                dlc = r.get('DATALC')
                dven = r.get('DATAVEN')
                lines.append({
                    'PLSTAMP': r.get('PLSTAMP') or '',
                    'RNO': int(r.get('RNO') or 0),
                    'RDATA': (r.get('RDATA').strftime('%Y-%m-%d') if isinstance(r.get('RDATA'), (datetime, date)) else str(r.get('RDATA') or '')),
                    'CDESC': r.get('CDESC') or '',
                    'ADOC': r.get('ADOC') or '',
                    'DATALC': dlc.strftime('%Y-%m-%d') if isinstance(dlc, (datetime, date)) else (str(dlc) if dlc is not None else ''),
                    'DATAVEN': dven.strftime('%Y-%m-%d') if isinstance(dven, (datetime, date)) else (str(dven) if dven is not None else ''),
                    'FCSTAMP': r.get('FCSTAMP') or '',
                    'CM': int(r.get('CM') or 0),
                    'EVAL': round(float(r.get('EVAL') or 0), 2),
                    'EREC': round(float(r.get('EREC') or 0), 2),
                    'PROCESS': int(r.get('PROCESS') or 0),
                    'MOEDA': r.get('MOEDA') or ''
                })

            return jsonify({'header': header, 'lines': lines})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/pagamentos/<postamp>', methods=['PUT'])
    @login_required
    def api_pagamentos_update(postamp):
        """
        Atualiza campos do pagamento (PO). Por agora:
          - RDATA/(DVALOR|DTVALOR)/PROCDATA (data sem hora)
          - PL.RDATA (para manter consistência)
        Body: { "RDATA": "YYYY-MM-DD" }
        """
        try:
            postamp = (postamp or '').strip()
            if not postamp:
                return jsonify({'error': 'POSTAMP obrigatório'}), 400
            body = request.get_json(silent=True) or {}
            rdata = str(body.get('RDATA') or '').strip()
            if not rdata:
                return jsonify({'error': 'RDATA obrigatória'}), 400

            try:
                d = date.fromisoformat(rdata)
            except Exception:
                return jsonify({'error': 'RDATA inválida (YYYY-MM-DD)'}), 400

            dt0 = datetime.combine(d, datetime.min.time())

            # garantir que existe
            exists = db.session.execute(
                text("SELECT 1 AS X FROM dbo.PO WHERE POSTAMP = :p"),
                {'p': postamp}
            ).mappings().first()
            if not exists:
                return jsonify({'error': 'Pagamento não encontrado.'}), 404

            po_cols = set(
                r['COLUMN_NAME'].upper()
                for r in (
                    db.session.execute(
                        text("""
                            SELECT COLUMN_NAME
                            FROM INFORMATION_SCHEMA.COLUMNS
                            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'PO'
                        """)
                    ).mappings().all()
                    or []
                )
            )

            set_parts = ["RDATA = :d", "PROCDATA = :d"]
            if 'DVALOR' in po_cols:
                set_parts.append("DVALOR = :d")
            if 'DTVALOR' in po_cols:
                set_parts.append("DTVALOR = :d")

            db.session.execute(
                text(f"""
                    UPDATE dbo.PO
                    SET {", ".join(set_parts)}
                    WHERE POSTAMP = :p
                """),
                {'d': dt0, 'p': postamp}
            )
            db.session.execute(
                text("""
                    UPDATE dbo.PL
                    SET RDATA = :d
                    WHERE POSTAMP = :p
                """),
                {'d': dt0, 'p': postamp}
            )
            db.session.commit()
            return jsonify({'ok': True, 'POSTAMP': postamp, 'RDATA': rdata})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    @app.route('/api/pagamentos/<postamp>', methods=['DELETE'])
    @login_required
    def api_pagamentos_delete(postamp):
        """
        Elimina um pagamento (PO) e as suas linhas (PL).
        """
        try:
            postamp = (postamp or '').strip()
            if not postamp:
                return jsonify({'error': 'POSTAMP obrigatório'}), 400

            # delete linhas primeiro
            db.session.execute(text("DELETE FROM dbo.PL WHERE POSTAMP = :p"), {'p': postamp})
            res = db.session.execute(text("DELETE FROM dbo.PO WHERE POSTAMP = :p"), {'p': postamp})
            # SQLAlchemy 2: rowcount disponível
            if getattr(res, 'rowcount', 0) == 0:
                db.session.rollback()
                return jsonify({'error': 'Pagamento não encontrado.'}), 404
            db.session.commit()
            return jsonify({'ok': True, 'POSTAMP': postamp})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    # -----------------------------
    # Recebimentos (RE)
    # -----------------------------
    @app.route('/recebimentos')
    @login_required
    def recebimentos_page():
        return render_template('recebimentos.html', page_title='Recebimentos')

    @app.route('/api/recebimentos')
    @login_required
    def api_recebimentos_list():
        """
        Lista recebimentos (RE) com filtros simples.
        Query:
          - de=YYYY-MM-DD
          - ate=YYYY-MM-DD
          - q=texto (NO, NOME, NRDOC, CDESC, NMDOC, OLCODIGO, OLLOCAL)
        """
        try:
            de = (request.args.get('de') or '').strip()
            ate = (request.args.get('ate') or '').strip()
            q = (request.args.get('q') or '').strip()

            where = []
            params = {}
            if de:
                where.append("CAST(RE.RDATA AS date) >= :de")
                params['de'] = de
            if ate:
                where.append("CAST(RE.RDATA AS date) <= :ate")
                params['ate'] = ate
            if q:
                where.append("""(
                    CAST(RE.NO AS varchar(50)) LIKE :q OR
                    RE.NOME LIKE :q OR
                    RE.NMDOC LIKE :q OR
                    RE.OLCODIGO LIKE :q OR
                    RE.OLLOCAL LIKE :q OR
                    EXISTS (
                        SELECT 1 FROM dbo.RL AS RL
                        WHERE RL.RESTAMP = RE.RESTAMP
                          AND (
                            CAST(ISNULL(RL.NRDOC,0) AS varchar(50)) LIKE :q OR
                            RL.CDESC LIKE :q
                          )
                    )
                )""")
                params['q'] = f"%{q}%"

            where_sql = ("WHERE " + " AND ".join(where)) if where else ""

            sql = text(f"""
                SELECT TOP 2000
                    RE.RESTAMP,
                    RE.RNO,
                    CAST(RE.RDATA AS date) AS RDATA,
                    ISNULL(RE.NO,0) AS NO,
                    ISNULL(RE.NOME,'') AS NOME,
                    ISNULL(RE.MOEDA,'') AS MOEDA,
                    ISNULL(RE.ETOTAL,0) AS ETOTAL,
                    ISNULL(RE.OLLOCAL,'') AS OLLOCAL,
                    ISNULL(RE.OLCODIGO,'') AS OLCODIGO,
                    ISNULL(RE.TELOCAL,'') AS TELOCAL,
                    ISNULL(RE.NMDOC,'') AS NMDOC
                FROM dbo.RE AS RE
                {where_sql}
                ORDER BY CAST(RE.RDATA AS date) DESC, RE.RNO DESC
            """)
            rows = db.session.execute(sql, params).mappings().all()

            out = []
            total = 0.0
            for r in rows:
                d = r.get('RDATA')
                if isinstance(d, (datetime, date)):
                    d = d.strftime('%Y-%m-%d')
                else:
                    d = str(d) if d is not None else ''
                et = float(r.get('ETOTAL') or 0)
                total += et
                out.append({
                    'RESTAMP': r.get('RESTAMP') or '',
                    'RNO': int(r.get('RNO') or 0),
                    'RDATA': d,
                    'NO': int(r.get('NO') or 0),
                    'NOME': r.get('NOME') or '',
                    'MOEDA': r.get('MOEDA') or '',
                    'ETOTAL': round(et, 2),
                    'OLLOCAL': r.get('OLLOCAL') or '',
                    'OLCODIGO': r.get('OLCODIGO') or '',
                    'TELOCAL': r.get('TELOCAL') or '',
                    'NMDOC': r.get('NMDOC') or ''
                })

            return jsonify({'rows': out, 'total': round(total, 2), 'count': len(out)})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/recebimentos/<restamp>')
    @login_required
    def api_recebimentos_detail(restamp):
        """
        Detalhe de recebimento: cabeçalho (RE) + linhas (RL).
        """
        try:
            restamp = (restamp or '').strip()
            if not restamp:
                return jsonify({'error': 'RESTAMP obrigatório'}), 400

            head_sql = text("""
                SELECT TOP 1
                    RE.RESTAMP,
                    RE.RNO,
                    CAST(RE.RDATA AS date) AS RDATA,
                    ISNULL(RE.NO,0) AS NO,
                    ISNULL(RE.NOME,'') AS NOME,
                    ISNULL(RE.MOEDA,'') AS MOEDA,
                    ISNULL(RE.ETOTAL,0) AS ETOTAL,
                    ISNULL(RE.OLLOCAL,'') AS OLLOCAL,
                    ISNULL(RE.OLCODIGO,'') AS OLCODIGO,
                    ISNULL(RE.TELOCAL,'') AS TELOCAL,
                    ISNULL(RE.NMDOC,'') AS NMDOC,
                    ISNULL(RE.PROCESS,0) AS PROCESS
                FROM dbo.RE AS RE
                WHERE RE.RESTAMP = :s
            """)
            head = db.session.execute(head_sql, {'s': restamp}).mappings().first()
            if not head:
                return jsonify({'error': 'Recebimento não encontrado.'}), 404

            rdata = head.get('RDATA')
            rdata_str = rdata.strftime('%Y-%m-%d') if isinstance(rdata, (datetime, date)) else (str(rdata) if rdata is not None else '')
            header = {
                'RESTAMP': head.get('RESTAMP') or '',
                'RNO': int(head.get('RNO') or 0),
                'RDATA': rdata_str,
                'NO': int(head.get('NO') or 0),
                'NOME': head.get('NOME') or '',
                'MOEDA': head.get('MOEDA') or '',
                'ETOTAL': round(float(head.get('ETOTAL') or 0), 2),
                'OLLOCAL': head.get('OLLOCAL') or '',
                'OLCODIGO': head.get('OLCODIGO') or '',
                'TELOCAL': head.get('TELOCAL') or '',
                'NMDOC': head.get('NMDOC') or '',
                'PROCESS': int(head.get('PROCESS') or 0),
            }

            rl_cols = set(
                r['COLUMN_NAME'].upper()
                for r in (
                    db.session.execute(
                        text("""
                            SELECT COLUMN_NAME
                            FROM INFORMATION_SCHEMA.COLUMNS
                            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'RL'
                        """)
                    ).mappings().all()
                    or []
                )
            )
            value_col = 'EVAL' if 'EVAL' in rl_cols else ('VAL' if 'VAL' in rl_cols else 'EVAL')

            lines_sql = text(f"""
                SELECT
                    RL.RLSTAMP,
                    RL.RNO,
                    CAST(RL.RDATA AS date) AS RDATA,
                    ISNULL(RL.CDESC,'') AS CDESC,
                    ISNULL(RL.NRDOC,0) AS NRDOC,
                    CAST(RL.DATALC AS date) AS DATALC,
                    CAST(RL.DATAVEN AS date) AS DATAVEN,
                    ISNULL(RL.CCSTAMP,'') AS CCSTAMP,
                    ISNULL(RL.CM,0) AS CM,
                    ISNULL(RL.{value_col},0) AS EVAL,
                    ISNULL(RL.EREC,0) AS EREC,
                    ISNULL(RL.PROCESS,0) AS PROCESS,
                    ISNULL(RL.MOEDA,'') AS MOEDA
                FROM dbo.RL AS RL
                WHERE RL.RESTAMP = :s
                ORDER BY CAST(RL.DATAVEN AS date), CAST(RL.DATALC AS date), RL.RLSTAMP
            """)
            rows = db.session.execute(lines_sql, {'s': restamp}).mappings().all()

            lines = []
            for r in rows:
                dlc = r.get('DATALC')
                dven = r.get('DATAVEN')
                lines.append({
                    'RLSTAMP': r.get('RLSTAMP') or '',
                    'RNO': int(r.get('RNO') or 0),
                    'RDATA': (r.get('RDATA').strftime('%Y-%m-%d') if isinstance(r.get('RDATA'), (datetime, date)) else str(r.get('RDATA') or '')),
                    'CDESC': r.get('CDESC') or '',
                    'NRDOC': int(r.get('NRDOC') or 0),
                    'DATALC': dlc.strftime('%Y-%m-%d') if isinstance(dlc, (datetime, date)) else (str(dlc) if dlc is not None else ''),
                    'DATAVEN': dven.strftime('%Y-%m-%d') if isinstance(dven, (datetime, date)) else (str(dven) if dven is not None else ''),
                    'CCSTAMP': r.get('CCSTAMP') or '',
                    'CM': int(r.get('CM') or 0),
                    'EVAL': round(float(r.get('EVAL') or 0), 2),
                    'EREC': round(float(r.get('EREC') or 0), 2),
                    'PROCESS': int(r.get('PROCESS') or 0),
                    'MOEDA': r.get('MOEDA') or ''
                })

            return jsonify({'header': header, 'lines': lines})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/recebimentos/<restamp>', methods=['PUT'])
    @login_required
    def api_recebimentos_update(restamp):
        """
        Atualiza campos do recebimento (RE):
          - RDATA/PROCDATA (data sem hora)
          - RL.RDATA (consistência)
        Body: { "RDATA": "YYYY-MM-DD" }
        """
        try:
            restamp = (restamp or '').strip()
            if not restamp:
                return jsonify({'error': 'RESTAMP obrigatório'}), 400
            body = request.get_json(silent=True) or {}
            rdata = str(body.get('RDATA') or '').strip()
            if not rdata:
                return jsonify({'error': 'RDATA obrigatória'}), 400

            try:
                d = date.fromisoformat(rdata)
            except Exception:
                return jsonify({'error': 'RDATA inválida (YYYY-MM-DD)'}), 400

            dt0 = datetime.combine(d, datetime.min.time())

            exists = db.session.execute(
                text("SELECT 1 AS X FROM dbo.RE WHERE RESTAMP = :s"),
                {'s': restamp}
            ).mappings().first()
            if not exists:
                return jsonify({'error': 'Recebimento não encontrado.'}), 404

            db.session.execute(
                text("""
                    UPDATE dbo.RE
                    SET RDATA = :d, PROCDATA = :d
                    WHERE RESTAMP = :s
                """),
                {'d': dt0, 's': restamp}
            )
            db.session.execute(
                text("""
                    UPDATE dbo.RL
                    SET RDATA = :d
                    WHERE RESTAMP = :s
                """),
                {'d': dt0, 's': restamp}
            )
            db.session.commit()
            return jsonify({'ok': True, 'RESTAMP': restamp, 'RDATA': rdata})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    @app.route('/api/recebimentos/<restamp>', methods=['DELETE'])
    @login_required
    def api_recebimentos_delete(restamp):
        """
        Elimina um recebimento (RE) e as suas linhas (RL).
        """
        try:
            restamp = (restamp or '').strip()
            if not restamp:
                return jsonify({'error': 'RESTAMP obrigatório'}), 400

            exists = db.session.execute(
                text("SELECT 1 AS X FROM dbo.RE WHERE RESTAMP = :s"),
                {'s': restamp}
            ).mappings().first()
            if not exists:
                return jsonify({'error': 'Recebimento não encontrado.'}), 404

            db.session.execute(text("DELETE FROM dbo.RL WHERE RESTAMP = :s"), {'s': restamp})
            db.session.execute(text("DELETE FROM dbo.RE WHERE RESTAMP = :s"), {'s': restamp})
            db.session.commit()
            return jsonify({'ok': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    # -----------------------------
    # Configuração de Escalas (ES/ESL)
    # -----------------------------
    @app.route('/escalas')
    @login_required
    def escalas_page():
        return render_template('escalas.html', page_title='Configuração de Escalas')

    @app.route('/api/escalas', methods=['GET', 'POST'])
    @login_required
    def api_escalas():
        try:
            if request.method == 'GET':
                sql = text(
                    """
                    SELECT E.ESSTAMP, E.ESCALA, ISNULL(L.DIA, 0) AS DIA, ISNULL(L.FOLGA,0) AS FOLGA
                    FROM ES AS E
                    LEFT JOIN ESL AS L ON L.ESSTAMP = E.ESSTAMP
                    ORDER BY E.ESCALA, E.ESSTAMP, ISNULL(L.DIA, 0)
                    """
                )
                rows = db.session.execute(sql).fetchall()
                escalas = {}
                for r in rows:
                    es_id, nome, dia, folga = r[0], r[1], int(r[2] or 0), int(r[3] or 0)
                    if es_id not in escalas:
                        escalas[es_id] = { 'id': es_id, 'escala': nome, 'dias': {}, 'max_dia': 0 }
                    if dia:
                        escalas[es_id]['dias'][dia] = folga
                        if dia > escalas[es_id]['max_dia']:
                            escalas[es_id]['max_dia'] = dia
                items = []
                max_dias = 0
                for es in escalas.values():
                    max_dias = max(max_dias, es['max_dia'])
                    items.append({ 'id': es['id'], 'escala': es['escala'], 'dias': es['dias'], 'total_dias': es['max_dia'] })
                return jsonify({ 'rows': items, 'max_dias': max_dias })

            # POST (create): { escala, dias }
            body = request.get_json(silent=True) or {}
            nome = (body.get('escala') or '').strip()
            try:
                dias = int(body.get('dias') or 0)
            except Exception:
                dias = 0
            if not nome:
                return jsonify({ 'error': 'Nome da escala obrigatório' }), 400
            if dias <= 0 or dias > 366:
                return jsonify({ 'error': 'Número de dias inválido' }), 400
            new_id_row = db.session.execute(text("SELECT LEFT(CONVERT(varchar(36), NEWID()), 25)")).fetchone()
            es_id = new_id_row[0]
            db.session.execute(text("INSERT INTO ES (ESSTAMP, ESCALA) VALUES (:id, :nome)"), { 'id': es_id, 'nome': nome })
            # Preenche dias com FOLGA=0
            ins = text("INSERT INTO ESL (ESLSTAMP, ESSTAMP, DIA, FOLGA) VALUES (LEFT(CONVERT(varchar(36), NEWID()), 25), :es, :dia, 0)")
            for d in range(1, dias+1):
                db.session.execute(ins, { 'es': es_id, 'dia': d })
            db.session.commit()
            return jsonify({ 'ok': True, 'id': es_id })
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    @app.route('/api/escalas/<es_id>', methods=['DELETE'])
    @login_required
    def api_escalas_delete(es_id):
        try:
            db.session.execute(text("DELETE FROM ESL WHERE ESSTAMP = :id"), { 'id': es_id })
            res = db.session.execute(text("DELETE FROM ES WHERE ESSTAMP = :id"), { 'id': es_id })
            db.session.commit()
            return jsonify({ 'ok': True, 'deleted': res.rowcount })
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    @app.route('/api/escalas/<es_id>/toggle', methods=['POST'])
    @login_required
    def api_escalas_toggle(es_id):
        try:
            body = request.get_json(silent=True) or {}
            try:
                dia = int(body.get('dia') or 0)
            except Exception:
                dia = 0
            if dia <= 0:
                return jsonify({ 'error': 'Dia inválido' }), 400
            # Tenta atualizar; se não existir, cria com FOLGA=1
            upd = text("UPDATE ESL SET FOLGA = CASE WHEN ISNULL(FOLGA,0)=1 THEN 0 ELSE 1 END WHERE ESSTAMP = :es AND DIA = :dia")
            res = db.session.execute(upd, { 'es': es_id, 'dia': dia })
            if res.rowcount == 0:
                db.session.execute(text("INSERT INTO ESL (ESLSTAMP, ESSTAMP, DIA, FOLGA) VALUES (LEFT(CONVERT(varchar(36), NEWID()), 25), :es, :dia, 1)"), { 'es': es_id, 'dia': dia })
                new_val = 1
            else:
                # fetch new value
                cur = db.session.execute(text("SELECT ISNULL(FOLGA,0) FROM ESL WHERE ESSTAMP=:es AND DIA=:dia"), { 'es': es_id, 'dia': dia }).fetchone()
                new_val = int(cur[0]) if cur else 0
            db.session.commit()
            return jsonify({ 'ok': True, 'folga': new_val })
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    # API: Detalhe de faturação por reserva para um alojamento
    @app.route('/api/performance/detalhe')
    @login_required
    def api_performance_detalhe():
        try:
            alojamento = (request.args.get('alojamento') or '').strip()
            data_inicio = (request.args.get('data_inicio') or '').strip()
            data_fim = (request.args.get('data_fim') or '').strip()
            if not alojamento or not data_inicio or not data_fim:
                return jsonify({'error': 'Parâmetros em falta'}), 400

            # Query: agrupa por reserva, soma valor, mostra uma linha por reserva
            sql = text(
                """
                SELECT
                    CAST(MIN(V.data) AS date) AS data_reserva,
                    MAX(ISNULL(V.nome, ''))    AS hospede,
                    ISNULL(V.reserva, '')      AS reserva,
                    SUM(ISNULL(V.valor, 0))    AS total
                FROM v_diario_all AS V
                WHERE V.CCUSTO = :aloj
                  AND ISNULL(V.valor, 0) <> 0
                  AND V.data BETWEEN :data_inicio AND :data_fim
                GROUP BY ISNULL(V.reserva, '')
                ORDER BY data_reserva, reserva
                """
            )

            rows = db.session.execute(sql, {
                'aloj': alojamento,
                'data_inicio': data_inicio,
                'data_fim': data_fim
            }).mappings().all()

            out = []
            total_sum = 0.0
            for r in rows:
                data_res = r.get('data_reserva')
                if isinstance(data_res, (datetime, date)):
                    data_str = data_res.strftime('%Y-%m-%d')
                else:
                    data_str = str(data_res) if data_res is not None else ''
                val = float(r.get('total') or 0)
                total_sum += val
                out.append({
                    'data_reserva': data_str,
                    'hospede': r.get('hospede') or '',
                    'reserva': r.get('reserva') or '',
                    'valor': round(val, 2)
                })

            # Custos: agrupar por referência (REF), somando o valor no período
            sql_c = text(
                """
                SELECT ISNULL(C.ref,'') AS ref, SUM(ISNULL(C.valor,0)) AS valor
                FROM v_custo AS C
                WHERE C.ccusto = :aloj
                  AND C.data BETWEEN :data_inicio AND :data_fim
                GROUP BY ISNULL(C.ref,'')
                ORDER BY ISNULL(C.ref,'')
                """
            )
            c_rows_db = db.session.execute(sql_c, {
                'aloj': alojamento,
                'data_inicio': data_inicio,
                'data_fim': data_fim
            }).mappings().all()

            custos_rows = []
            custos_total = 0.0
            for r in c_rows_db:
                v = float(r.get('valor') or 0)
                custos_total += v
                custos_rows.append({
                    'ref': r.get('ref') or '',
                    'valor': round(v, 2)
                })

            return jsonify({
                'rows': out,
                'total': round(total_sum, 2),
                'custos': custos_rows,
                'total_custos': round(custos_total, 2),
                'resultado': round(total_sum - custos_total, 2)
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # API: Ocupação por dia (datas e totais) para um alojamento num período
    @app.route('/api/performance/ocupacao')
    @login_required
    def api_performance_ocupacao():
        try:
            alojamento = (request.args.get('alojamento') or '').strip()
            data_inicio = (request.args.get('data_inicio') or '').strip()
            data_fim = (request.args.get('data_fim') or '').strip()
            if not alojamento or not data_inicio or not data_fim:
                return jsonify({'error': 'Parâmetros em falta'}), 400

            sql = text(
                """
                SELECT CAST(V.data AS date) AS dia, SUM(ISNULL(V.valor,0)) AS total
                FROM v_diario_all V
                WHERE V.CCUSTO = :aloj
                  AND ISNULL(V.valor,0) <> 0
                  AND V.data BETWEEN :data_inicio AND :data_fim
                GROUP BY CAST(V.data AS date)
                ORDER BY dia
                """
            )
            rows = db.session.execute(sql, {
                'aloj': alojamento,
                'data_inicio': data_inicio,
                'data_fim': data_fim
            }).fetchall()
            dias = []
            mapa = {}
            for r in rows:
                d = r[0]
                tot = float(r[1] or 0)
                if isinstance(d, (date, datetime)):
                    key = d.strftime('%Y-%m-%d')
                else:
                    key = str(d)
                dias.append(key)
                mapa[key] = round(tot, 2)
            return jsonify({'dias': dias, 'mapa': mapa})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    from sqlalchemy import text

    from flask_login import current_user

    @app.route('/newmn')
    @login_required
    def newmn():
        alojamentos = [row[0] for row in db.session.execute(text("SELECT NOME FROM AL ORDER BY 1")).fetchall()]
        users = [row[0] for row in db.session.execute(text("SELECT LOGIN FROM US ORDER BY 1")).fetchall()]
        utilizador = current_user.LOGIN
        return render_template('newmn.html', alojamentos=alojamentos, users=users, utilizador=utilizador, page_title='ManutenÃ§Ã£o')
    
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
            abort(400, "Faltam parÃ¢metros")
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
            # sÃ³ insere se nÃ£o existir ainda
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
        return render_template('profile.html', user=current_user, page_title='Perfil')


    @app.route('/api/profile/change_password', methods=['POST'])
    @login_required
    def change_password():
        data = request.json
        new_pwd = data.get('password', '').strip()
        if not new_pwd or len(new_pwd) < 4:
            return {'error': 'Password demasiado curta'}, 400

        from app import db  # ou usa db conforme jÃ¡ tens no teu projeto
        user = db.session.query(US).get(current_user.USSTAMP)
        if not user:
            return {'error': 'Utilizador nÃ£o encontrado'}, 404
        user.PASSWORD = new_pwd
        db.session.commit()
        return {'success': True}

    @app.route('/api/profile/save', methods=['POST'])
    @login_required
    def save_profile():
        try:
            data = request.get_json(force=True) or {}
            # Campos permitidos a serem atualizados no perfil
            allowed_fields = {'EMAIL', 'COR'}

            user = db.session.query(US).get(current_user.USSTAMP)
            if not user:
                return {'error': 'Utilizador nÃ£o encontrado'}, 404

            updated = {}
            for field in allowed_fields:
                if field in data:
                    setattr(user, field, data[field])
                    updated[field] = data[field]

            if not updated:
                return {'error': 'Sem alteraÃ§Ãµes vÃ¡lidas'}, 400

            db.session.commit()
            return jsonify({'success': True, 'updated': updated})
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

    @app.route('/api/profile/upload_photo', methods=['POST'])
    @login_required
    def upload_photo():
        try:
            from werkzeug.utils import secure_filename
            import uuid as _uuid
            photo = request.files.get('photo')
            if not photo or photo.filename == '':
                return {'error': 'Ficheiro em falta'}, 400
            fname = secure_filename(photo.filename)
            ext = os.path.splitext(fname)[1].lower()
            if ext not in ('.jpg', '.jpeg', '.png', '.gif', '.webp'):
                return {'error': 'Formato invÃ¡lido'}, 400

            target_dir = os.path.join(app.static_folder, 'images', 'profile')
            os.makedirs(target_dir, exist_ok=True)
            new_name = f"{_uuid.uuid4().hex}{ext}"
            save_path = os.path.join(target_dir, new_name)
            photo.save(save_path)

            # Atualiza caminho relativo sob /static
            rel_path = f"images/profile/{new_name}"
            user = db.session.query(US).get(current_user.USSTAMP)
            if not user:
                return {'error': 'Utilizador nÃ£o encontrado'}, 404
            user.FOTO = rel_path
            db.session.commit()

            return jsonify({'success': True, 'path': rel_path})
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

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
            # aceita tambÃ©m CSV alternativo (users, aloj, origins)
            utilizadores = params.getlist('UTILIZADOR') or ([] if params.get('UTILIZADOR') is None else [params.get('UTILIZADOR')])
            if not utilizadores and params.get('users'):
                utilizadores = [u.strip() for u in params.get('users').split(',') if u.strip() != '']
            alojamentos = params.getlist('ALOJAMENTO') or ([] if params.get('ALOJAMENTO') is None else [params.get('ALOJAMENTO')])
            if not alojamentos and params.get('aloj'):
                alojamentos = [a.strip() for a in params.get('aloj').split(',')]
            origens = params.getlist('ORIGEM') or ([] if params.get('ORIGEM') is None else [params.get('ORIGEM')])
            if not origens and params.get('origins'):
                origens = [o.strip() for o in params.get('origins').split(',')]
            # Regra: LPADMIN vê sempre FS. Não remove filtros existentes; apenas acrescenta FS.
            try:
                is_lp_admin = bool(getattr(current_user, 'LPADMIN', 0))
            except Exception:
                is_lp_admin = False
            if is_lp_admin and origens:
                if 'FS' not in {str(o).upper() for o in origens}:
                    origens.append('FS')

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

            # LPADMIN: garantir FS visível, ignorando only_mine
            try:
                _lpadmin_flag = bool(getattr(current_user, 'LPADMIN', 0))
            except Exception:
                _lpadmin_flag = False
            if _lpadmin_flag:
                try:
                    _only_backup = only_mine
                except Exception:
                    _only_backup = False
                try:
                    only_mine = False
                    if exists_table('FS'):
                        s2, b2 = build_select('FS', 'FS')
                        if s2:
                            # Renomear binds para evitar colisões
                            selects.append(s2)
                            binds_union.update({ f"fsall_{k}": v for k, v in b2.items() })
                            for k in list(b2.keys()):
                                s2 = s2.replace(f":{k}", f":fsall_{k}")
                            selects[-1] = s2
                    elif exists_table('TAREFAS') and 'ORIGEM' in get_columns('TAREFAS'):
                        cols = get_columns('TAREFAS')
                        data_col = 'DATA' if 'DATA' in cols else None
                        hora_col = 'HORA' if 'HORA' in cols else None
                        aloj_col = 'ALOJAMENTO' if 'ALOJAMENTO' in cols else None
                        user_col = 'UTILIZADOR' if 'UTILIZADOR' in cols else None
                        tarefa_col = next((c for c in ('TAREFA','TITULO','ASSUNTO','DESCRICAO','DESCR') if c in cols), None)
                        tratado_col = 'TRATADO' if 'TRATADO' in cols else None
                        if data_col:
                            sel = [
                                "NULL AS TAREFASSTAMP",
                                f"CAST({data_col} AS date) AS DATA",
                                (f"CAST({hora_col} AS varchar(8)) AS HORA" if hora_col else "'' AS HORA"),
                                (f"ISNULL({aloj_col}, '') AS ALOJAMENTO" if aloj_col else "'' AS ALOJAMENTO"),
                                "'FS' AS ORIGEM",
                                (f"{tarefa_col} AS TAREFA" if tarefa_col else "'Tarefa' AS TAREFA"),
                                (f"ISNULL({tratado_col}, 0) AS TRATADO" if tratado_col else "0 AS TRATADO"),
                                (f"ISNULL({user_col}, '') AS UTILIZADOR" if user_col else "'' AS UTILIZADOR"),
                            ]
                            sel_sql = ",\n                    ".join(sel)
                            fs_sql = f"SELECT\n                    {sel_sql}\n                FROM TAREFAS\n                WHERE {data_col} BETWEEN :fs_start AND :fs_end AND ISNULL(ORIGEM,'') = 'FS'"
                            selects.append(fs_sql)
                            binds_union.update({ 'fs_start': start, 'fs_end': end })
                finally:
                    only_mine = _only_backup

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

            # 3) juntar e eliminar duplicados por chave lÃ³gica
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


    # Report per client/month (HTML)
    @app.route('/report/<cliente_id>/<int:ano>/<int:mes>')
    @login_required
    def report_cliente_mes(cliente_id, ano, mes):
        # Resolve month range
        try:
            start = date(ano, mes, 1)
            if mes == 12:
                end = date(ano + 1, 1, 1)
            else:
                end = date(ano, mes + 1, 1)
            end = end.replace(day=1)
            # last day of month
            from datetime import timedelta
            end = end - timedelta(days=1)
        except Exception:
            # fallback: current month
            today = date.today()
            start = date(today.year, today.month, 1)
            if today.month == 12:
                end = date(today.year + 1, 1, 1) - timedelta(days=1)
            else:
                end = date(today.year, today.month + 1, 1) - timedelta(days=1)

        # Fetch client's alojamentos; prefer CLIENTID when numeric
        alojamentos = []
        monthly_map = {}
        try:
            is_num = False
            try:
                _cid_int = int(cliente_id)
                is_num = True
            except Exception:
                is_num = False

            if is_num:
                rows = db.session.execute(text("""
                    SELECT NOME, TIPOLOGIA, EMPRESA, PROPRIETARIO, CCUSTO, TIPO
                    FROM AL
                    WHERE ISNULL(INATIVO,0)=0 AND CLIENTID = :cid
                    ORDER BY NOME
                """), { 'cid': _cid_int }).mappings().all()
            else:
                rows = db.session.execute(text("""
                    SELECT NOME, TIPOLOGIA, EMPRESA, PROPRIETARIO, CCUSTO, TIPO
                    FROM AL
                    WHERE ISNULL(INATIVO,0)=0 AND (PROPRIETARIO = :cid OR EMPRESA = :cid)
                    ORDER BY NOME
                """), { 'cid': cliente_id }).mappings().all()
            alojamentos = [ dict(r) for r in rows ]

            if is_num:
                sql_aggr = text("""
                    SELECT A.NOME AS ALOJ, MONTH(RS.DATAOUT) AS MES,
                           SUM(ISNULL(RS.ESTADIA,0)+ISNULL(RS.LIMPEZA,0)) AS VENDAS,
                           SUM(ISNULL(RS.COMISSAO,0)) AS COM_CANAL
                    FROM AL A
                    LEFT JOIN RS ON ISNULL(RS.ALOJAMENTO, RS.CCUSTO) = A.NOME AND YEAR(RS.DATAOUT) = :ano
                    WHERE ISNULL(A.INATIVO,0)=0 AND A.CLIENTID = :cid
                    GROUP BY A.NOME, MONTH(RS.DATAOUT)
                    ORDER BY A.NOME, MES
                """)
                ag = db.session.execute(sql_aggr, { 'cid': _cid_int, 'ano': ano }).all()
                for aloj, mesn, vendas, com_canal in ag:
                    monthly_map.setdefault(aloj, {})[int(mesn or 0)] = {
                        'vendas': float(vendas or 0),
                        'com_canal': float(com_canal or 0)
                    }
        except Exception:
            alojamentos = []
            monthly_map = {}

        # Render standalone printable HTML
        return render_template('report.html', cliente_id=cliente_id, ano=ano, mes=mes, inicio=start, fim=end, alojamentos=alojamentos, monthly_map=monthly_map)# Report per client/month (PDF)
    @app.route('/report/<cliente_id>/<int:ano>/<int:mes>/pdf')
    @login_required
    def report_cliente_mes_pdf(cliente_id, ano, mes):
        # Reuse same data gathering as HTML
        try:
            start = date(ano, mes, 1)
            if mes == 12:
                next_month_first = date(ano + 1, 1, 1)
            else:
                next_month_first = date(ano, mes + 1, 1)
            from datetime import timedelta
            end = next_month_first - timedelta(days=1)
        except Exception:
            today = date.today()
            start = date(today.year, today.month, 1)
            if today.month == 12:
                end = date(today.year + 1, 1, 1) - timedelta(days=1)
            else:
                end = date(today.year, today.month + 1, 1) - timedelta(days=1)

        alojamentos = []
        try:
            query = text(
                """
                SELECT NOME, TIPOLOGIA, EMPRESA, PROPRIETARIO, CCUSTO, TIPO
                FROM AL
                WHERE ISNULL(INATIVO,0)=0
                  AND (
                        PROPRIETARIO = :cid
                     OR EMPRESA = :cid
                     OR (CASE WHEN TRY_CAST(:cid AS int) IS NOT NULL THEN IDPLABS ELSE NULL END) = TRY_CAST(:cid AS int)
                  )
                ORDER BY NOME
                """
            )
            rows = db.session.execute(query, { 'cid': cliente_id }).mappings().all()
            alojamentos = [ dict(r) for r in rows ]
        except Exception:
            alojamentos = []

        # Render HTML
        from flask import render_template_string, current_app, Response
        html = render_template('report.html', cliente_id=cliente_id, ano=ano, mes=mes, inicio=start, fim=end, alojamentos=alojamentos, monthly_map={})

        # Try WeasyPrint / wkhtmltopdf / Headless Chrome
        pdf_bytes = None
        try:
            from weasyprint import HTML
            pdf_bytes = HTML(string=html, base_url=current_app.root_path).write_pdf()
        except Exception:
            try:
                import pdfkit  # requires wkhtmltopdf installed
                pdf_bytes = pdfkit.from_string(html, False)
            except Exception:
                # Try Headless Chrome/Edge as a last resort
                try:
                    chrome_paths = [
                        os.environ.get('CHROME_PATH') or '',
                        shutil.which('chrome') or '',
                        shutil.which('google-chrome') or '',
                        shutil.which('msedge') or '',
                        r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                        r"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
                        r"C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
                        r"/usr/bin/google-chrome",
                        r"/usr/bin/chromium",
                    ]
                    chrome = next((p for p in chrome_paths if p and os.path.exists(p)), None)
                    if chrome:
                        with tempfile.TemporaryDirectory() as td:
                            html_path = os.path.join(td, 'report.html')
                            pdf_path = os.path.join(td, 'report.pdf')
                            with open(html_path, 'w', encoding='utf-8') as f:
                                f.write(html)
                            uri = 'file:///' + html_path.replace('\\', '/')
                            cmd = [
                                chrome,
                                '--headless=new',
                                '--disable-gpu',
                                f'--print-to-pdf={pdf_path}',
                                '--no-sandbox',
                                uri
                            ]
                            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                            with open(pdf_path, 'rb') as pf:
                                pdf_bytes = pf.read()
                except Exception:
                    pdf_bytes = None

        if not pdf_bytes:
            # Fallback: return HTML with hint
            return html + "<!-- PDF generator not available. Install WeasyPrint (pip install weasyprint + deps), wkhtmltopdf/pdfkit, or set CHROME_PATH to a Chrome/Edge binary for headless printing. -->"

        headers = {
            'Content-Type': 'application/pdf',
            'Content-Disposition': f'inline; filename="report_{cliente_id}_{ano:04d}-{mes:02d}.pdf"'
        }
        return Response(pdf_bytes, headers=headers)


    return app


app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
