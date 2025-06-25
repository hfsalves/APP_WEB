import os
import pyodbc
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, date

# Importa a instância db e modelos
from models import db, US, Menu, Acessos

# Inicializa extensões
login_manager = LoginManager()

def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        "mssql+pyodbc://sa:enterprise@hfsalves.mooo.com,50002/GESTAO"
        "?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=Yes&protocol=TCP"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Inicializa DB e Login
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    # Importa e regista blueprint genérico
    from blueprints.generic_crud import bp as generic_bp
    app.register_blueprint(generic_bp)

    from sqlalchemy import false

    @app.context_processor
    def inject_menu_and_access():
        # 1) Se não está logado, devolve menus vazios e sem perms
        if not current_user.is_authenticated:
            return dict(menu_items=[], user_perms={})

        # 2) Monta menu (sistema-wide admin vs não-admin system)
        if getattr(current_user, 'ADMIN', False):
            menus = Menu.query.order_by(Menu.ordem).all()
        else:
            menus = Menu.query.filter_by(admin=False).order_by(Menu.ordem).all()

        # 3) Carrega ACL específicas do utilizador (por LOGIN)
        rows = Acessos.query.filter_by(utilizador=current_user.LOGIN).all()
        perms = {}
        for a in rows:
            perms[a.tabela] = {
                'consultar': bool(a.consultar),
                'inserir':   bool(a.inserir),
                'editar':    bool(a.editar),
                'eliminar':  bool(a.eliminar),
            }

        # 4) Disponibiliza ambos no template
        return dict(menu_items=menus, user_perms=perms)

    # Carregamento de utilizador
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
                return redirect(request.args.get('next') or url_for('home_page'))
            return render_template('login.html', error='Credenciais inválidas')
        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('login'))

    # Páginas
    @app.route('/')
    @login_required
    def home_page():
        return render_template('home.html')

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

    # API Plan
    CONN_STR = (
        'DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.1.50,1433;DATABASE=GESTAO;UID=sa;PWD=enterprise;TrustServerCertificate=Yes'
        'SERVER=127.0.0.1,1433;DATABASE=GESTAO;UID=sa;PWD=enterprise;TrustServerCertificate=Yes'
    )

    @app.route('/api/plan')
    @login_required
    def get_plan():
        date_str = request.args.get('date')
        if not date_str:
            return jsonify({'error': 'date=YYYY-MM-DD obrigatório'}), 400
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Formato inválido'}), 400

        try:
            with pyodbc.connect(CONN_STR) as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT Data, Alojamento, ... FROM v_plan WHERE Data = ?", dt
                )
                plan = [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]
        except Exception as e:
            return jsonify({'error': str(e)}), 500

        return jsonify(plan=plan)

    # API Cleanings placeholder
    @app.route('/api/cleanings', methods=['GET', 'POST'])
    @login_required
    def api_cleanings():
        if request.method == 'GET':
            date_str = request.args.get('date')
            return jsonify([])
        return '', 204

    return app

# Criação da app
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
