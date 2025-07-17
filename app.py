import os
import pyodbc
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for
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

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    # Importa e regista blueprint genérico
    from blueprints.generic_crud import bp as generic_bp
    app.register_blueprint(generic_bp)

    from blueprints.anexos import bp as anexos_bp
    app.register_blueprint(anexos_bp)

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

            # 4) Montar estrutura de dropdown: agrupadores são múltiplos de 100
            current_group = None
            for m in menu_items:
                if m.ordem % 100 == 0:
                    # cabeçalho de grupo (sem URL clicável)
                    current_group = {
                        'name'    : m.nome,
                        'icon'    : m.icone,
                        'children': []
                    }
                    menu_structure.append(current_group)
                else:
                    # item “filho” com url
                    child = {
                        'name': m.nome,
                        'url' : m.url,
                        'icon': m.icone
                    }
                    if current_group:
                        current_group['children'].append(child)
                    else:
                        # sem grupo definido, adiciona como item top-level
                        menu_structure.append({
                            'name'    : m.nome,
                            'icon'    : m.icone,
                            'url'     : m.url,
                            'children': []
                        })


                    print("🧪 current_user", current_user)
                    print("🧪 current_user.__dict__:", current_user.__dict__)
                    print("🧪 current_user.DEV =", getattr(current_user, 'DEV', 'NÃO DEFINIDO'))

        return {
            'menu_items'     : menu_items,
            'menu_structure' : menu_structure,
            'user_perms'     : perms,
            'page_name'      : page_name,
            'menu_botoes'    : menu_botoes,
            'is_dev'         : getattr(current_user, 'DEV', False) if current_user.is_authenticated else False
        }


    from sqlalchemy.sql import text

    @login_manager.user_loader
    def load_user(user_stamp):
        sql = text("""
            SELECT USSTAMP, LOGIN, NOME, EMAIL, PASSWORD, ADMIN, EQUIPA, DEV, HOME
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
                SELECT USSTAMP, LOGIN, NOME, EMAIL, PASSWORD, ADMIN, EQUIPA, DEV, HOME
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


    return app


app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
