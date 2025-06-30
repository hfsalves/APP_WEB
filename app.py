import os
import pyodbc
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, date
from sqlalchemy import text

# Importa a instância db e modelos
from models import db, US, Menu, Acessos, Widget, UsWidget, MenuBotoes
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

    @app.context_processor
    def inject_menu_and_access():
        page_name = None
        menu_items = []
        perms = {}
        menu_botoes = {}

        if current_user.is_authenticated:
            if getattr(current_user, 'ADMIN', False):
                menu_items = Menu.query.order_by(Menu.ordem).all()
            else:
                menu_items = Menu.query.filter_by(admin=False).order_by(Menu.ordem).all()

            rows = Acessos.query.filter_by(utilizador=current_user.LOGIN).all()
            perms = {
                a.tabela: {
                    'consultar': bool(a.consultar),
                    'inserir': bool(a.inserir),
                    'editar': bool(a.editar),
                    'eliminar': bool(a.eliminar),
                }
                for a in rows
            }

            parts = request.path.strip('/').split('/')
            if len(parts) >= 3 and parts[0] == 'generic' and parts[1] in ('view', 'form'):
                tabela_arg = parts[2]
                for m in menu_items:
                    if m.tabela == tabela_arg:
                        page_name = m.nome
                        botoes = MenuBotoes.query.filter_by(TABELA=m.tabela, ATIVO=True).order_by(MenuBotoes.ORDEM).all()
                        menu_botoes = {
                            b.NOME: {
                                'icone': b.ICONE,
                                'texto': b.TEXTO,
                                'cor': b.COR,
                                'tipo': b.TIPO,
                                'acao': b.ACAO,
                                'condicao': b.CONDICAO,
                                'destino': b.DESTINO,
                            } for b in botoes
                        }
                        break

            if not page_name:
                for m in menu_items:
                    if request.path.startswith(m.url):
                        page_name = m.nome
                        break

        return dict(menu_items=menu_items, user_perms=perms, page_name=page_name, menu_botoes=menu_botoes)

    @login_manager.user_loader
    def load_user(user_stamp):
        return US.query.get(user_stamp)

    # Rotas de autenticação
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            login_ = request.form['login']
            pwd = request.form['password']
            user = US.query.filter_by(LOGIN=login_).first()
            if user and user.check_password(pwd):
                login_user(user)
                return redirect(request.args.get('next') or url_for('dashboard_page'))
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
        widget = Widget.query.filter_by(NOME=nome, ATIVO=True).first()
        if not widget:
            return jsonify({'error': 'Widget não encontrado'}), 404

        try:
            config = json.loads(widget.CONFIG)
            query = config.get('query')
            if not query:
                return jsonify({'error': 'Query não definida no config'}), 400

            CONN_STR = (
                'DRIVER={ODBC Driver 17 for SQL Server};'
                'SERVER=hfsalves.mooo.com,50002;'
                'DATABASE=GESTAO;'
                'UID=sa;PWD=enterprise;'
                'TrustServerCertificate=Yes;'
            )
            with pyodbc.connect(CONN_STR) as conn:
                cur = conn.cursor()
                cur.execute(query)
                col_names = [desc[0] for desc in cur.description]
                rows = [dict(zip(col_names, row)) for row in cur.fetchall()]
        except Exception as e:
            return jsonify({'error': str(e)}), 500

        return jsonify({'columns': col_names, 'rows': rows})

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
                    res = db.session.execute(campo.COMBO)
                    opcoes = [[str(r[0]), str(r[1])] for r in res.fetchall()]
                except Exception as e:
                    print('Erro na query da combo:', e)

            resultado.append({
                'CAMPO': campo.CAMPO,
                'LABEL': campo.LABEL,
                'TIPO': campo.TIPO,
                'ORDEM': campo.ORDEM,
                'OPCOES': opcoes,
                'VALORDEFAULT': campo.VALORDEFAULT  # ← AQUI ESTAVA A FALTAR
            })

        return jsonify({'success': True, 'campos': resultado, 'titulo': modal.TITULO})    

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

    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
