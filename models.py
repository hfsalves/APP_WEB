import uuid
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

# Instância do SQLAlchemy para ser usada em app e modelos
db = SQLAlchemy()

class Menu(db.Model):
    __tablename__ = 'MENU'
    menustamp = db.Column(db.String(25), primary_key=True, default=lambda: str(uuid.uuid4())[:25])
    ordem     = db.Column(db.Integer, nullable=False)
    nome      = db.Column(db.String(60), nullable=False)
    tabela    = db.Column(db.String(18), nullable=False)
    url       = db.Column(db.String(200), nullable=False)
    admin     = db.Column(db.Boolean, nullable=False, default=False)

class Campo(db.Model):
    __tablename__ = 'CAMPOS'
    camposstamp = db.Column(db.String(25), primary_key=True, default=lambda: str(uuid.uuid4())[:25])
    ordem       = db.Column(db.Integer, nullable=False)
    nmcampo     = db.Column(db.String(25), nullable=False)
    descricao   = db.Column(db.String(60), nullable=False)
    tipo        = db.Column(db.String(18), nullable=False)
    tabela      = db.Column(db.String(18), nullable=False)
    lista       = db.Column(db.Boolean, default=False, nullable=False)
    filtro      = db.Column(db.Boolean, default=False, nullable=False)
    admin       = db.Column(db.Boolean, default=False, nullable=False)
    ronly       = db.Column(db.Boolean, default=False, nullable=False)
    combo       = db.Column(db.String(200), nullable=True)

class US(UserMixin, db.Model):
    __tablename__ = 'US'
    USSTAMP  = db.Column(db.String(25), primary_key=True, default=lambda: str(uuid.uuid4())[:25])
    NOME     = db.Column(db.String(60), nullable=False)
    LOGIN    = db.Column(db.String(60), unique=True, nullable=False)
    PASSWORD = db.Column(db.String(128), nullable=False)
    EMAIL    = db.Column(db.String(120), unique=True, nullable=False)
    ADMIN    = db.Column(db.Boolean, default=False, nullable=False)
    EQUIPA   = db.Column(db.String(25), nullable=True)

    def check_password(self, plaintext):
        return self.PASSWORD == plaintext

    def get_id(self):
        return self.USSTAMP

# --------------------------------------------------
# Nova tabela de acessos (ACL)
# --------------------------------------------------
class Acessos(db.Model):
    __tablename__ = 'ACESSOS'

    acessosstamp = db.Column(db.String(25), primary_key=True, default=lambda: str(uuid.uuid4())[:25])
    utilizador   = db.Column(db.String(60), db.ForeignKey('US.LOGIN'), nullable=False)
    tabela       = db.Column(db.String(100), nullable=False)
    consultar    = db.Column(db.Boolean, default=False, nullable=False)
    inserir      = db.Column(db.Boolean, default=False, nullable=False)
    editar       = db.Column(db.Boolean, default=False, nullable=False)
    eliminar     = db.Column(db.Boolean, default=False, nullable=False)

    # Relacionamento opcional para aceder ao utilizador
    user = db.relationship('US', backref='acessos', primaryjoin="Acessos.utilizador==US.LOGIN")
