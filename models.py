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
    icone     = db.Column(db.String(100), nullable=False)

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

# Adiciona isto ao teu models.py
class Widget(db.Model):
    __tablename__ = 'WIDGETS'
    WIDGETSSTAMP = db.Column(db.String(25), primary_key=True)
    NOME         = db.Column(db.String(50), unique=True, nullable=False)
    TITULO       = db.Column(db.String(80), nullable=False, default='')
    TIPO         = db.Column(db.String(20), nullable=False, default='GRAFICO')
    FONTE        = db.Column(db.String(200), nullable=False, default='')
    CONFIG       = db.Column(db.Text, nullable=False, default='{}')
    ATIVO        = db.Column(db.Boolean, nullable=False, default=True)

class UsWidget(db.Model):
    __tablename__ = 'USWIDGETS'
    USWIDGETSSTAMP = db.Column(db.String(25), primary_key=True)
    UTILIZADOR     = db.Column(db.String(50), nullable=False)
    WIDGET         = db.Column(db.String(50), nullable=False)  # liga a WIDGETS.NOME
    COLUNA         = db.Column(db.Integer, nullable=False, default=1)
    ORDEM          = db.Column(db.Integer, nullable=False, default=1)
    VISIVEL        = db.Column(db.Boolean, nullable=False, default=True)
    MAXHEIGHT      = db.Column(db.Integer, nullable=False, default=1)

class MenuBotoes(db.Model):
    __tablename__ = 'MENUBOTOES'

    MENUBOTOESSTAMP = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4())[:25])
    TABELA          = db.Column(db.String(50), nullable=False, default='')
    NOME            = db.Column(db.String(100), nullable=False, default='')
    ICONE           = db.Column(db.String(50), nullable=False, default='')
    TEXTO           = db.Column(db.String(100), nullable=False, default='')
    COR             = db.Column(db.String(20), nullable=False, default='')
    ORDEM           = db.Column(db.Integer, default=0)
    TIPO            = db.Column(db.String(20), nullable=False, default='')
    ACAO            = db.Column(db.String(200), nullable=False, default='')
    CONDICAO        = db.Column(db.Text, nullable=False, default='')
    DESTINO         = db.Column(db.String(100), nullable=False, default='')
    ATIVO           = db.Column(db.Boolean, nullable=False, default=False)

class Modais(db.Model):
    __tablename__ = 'MODAIS'

    MODAISSTAMP = db.Column(db.String(50), primary_key=True)
    NOME        = db.Column(db.String(100), nullable=False, default='')
    TITULO      = db.Column(db.String(100), nullable=False, default='')
    ACAO        = db.Column(db.String(100), nullable=False, default='')
    ATIVO       = db.Column(db.Boolean, default=True)
    TABELA      = db.Column(db.String(100), nullable=False, default='')


class CamposModal(db.Model):
    __tablename__ = 'CAMPOSMODAL'

    CAMPOSMODALSTAMP = db.Column(db.String(50), primary_key=True)
    MODAISSTAMP      = db.Column(db.String(50), nullable=False)
    CAMPO            = db.Column(db.String(100), nullable=False, default='')
    LABEL            = db.Column(db.String(100), nullable=False, default='')
    TIPO             = db.Column(db.String(20), nullable=False, default='')
    VALORDEFAULT     = db.Column(db.String(100), default='')
    COMBO            = db.Column(db.Text, default='')
    ORDEM            = db.Column(db.Integer, default=0)
    OBRIGATORIO      = db.Column(db.Boolean, default=True)
    CAMPODESTINO     = db.Column(db.String(100), nullable=False, default='')

class Linhas(db.Model):
    __tablename__ = 'LINHAS'

    LINHASSTAMP  = db.Column(db.String(25), primary_key=True)
    MAE          = db.Column(db.String(50), nullable=False, default='')
    TABELA       = db.Column(db.String(50), nullable=False, default='')
    LIGACAO      = db.Column(db.String(200), nullable=False, default='')
    LIGACAOMAE   = db.Column(db.String(100), nullable=False, default='')
