import os
import pyodbc
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, date

# Importa a instância db e modelos
from models import db, US, Menu, Acessos, Widget, UsWidget

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
        """
        Injeta menu_items, user_perms e page_name baseado na rota:
        - para genérico: /generic/view/<tabela> e /generic/form/<tabela>/<id>
        - para estáticas: request.path.startswith(m.url)
        """
        page_name = None
        menu_items = []
        perms = {}

        if current_user.is_authenticated:
            # Carrega menus conforme perfil de admin
            if getattr(current_user, 'ADMIN', False):
                menu_items = Menu.query.order_by(Menu.ordem).all()
            else:
                menu_items = Menu.query.filter_by(admin=False).order_by(Menu.ordem).all()

            # Carrega permissões de acesso
            rows = Acessos.query.filter_by(utilizador=current_user.LOGIN).all()
            perms = {
                a.tabela: {
                    'consultar': bool(a.consultar),
                    'inserir':   bool(a.inserir),
                    'editar':    bool(a.editar),
                    'eliminar':  bool(a.eliminar),
                }
                for a in rows
            }

            # Detecta genérico (list e form)
            parts = request.path.strip('/').split('/')
            if len(parts) >= 3 and parts[0] == 'generic' and parts[1] in ('view', 'form'):
                tabela_arg = parts[2]
                for m in menu_items:
                    if m.tabela == tabela_arg:
                        page_name = m.nome
                        break

            # Fallback para rotas estáticas
            if not page_name:
                for m in menu_items:
                    if request.path.startswith(m.url):
                        page_name = m.nome
                        break

        return dict(menu_items=menu_items, user_perms=perms, page_name=page_name)

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

    # Rotas de páginas estáticas
    @app.route('/')
    @login_required
    def home_page():
        return redirect(url_for('dashboard_page'))

    @app.route('/plan')
    @login_required
    def plan_page():
        return render_template(
            'plan.html',
            today=date.today().isoformat()
        )

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

    # Endpoints de API
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

    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
