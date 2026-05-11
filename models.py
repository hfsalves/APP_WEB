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
    form      = db.Column(db.String(200), nullable=True)  # rota de form específico (opcional)
    orderby   = db.Column('ORDERBY', db.String(200), nullable=True)

    novo      = db.Column(db.Boolean, nullable=False, default=False)
    inativo   = db.Column('INATIVO', db.Boolean, nullable=False, default=False)

class Campo(db.Model):
    __tablename__ = 'CAMPOS'
    camposstamp       = db.Column(db.String(25), primary_key=True, default=lambda: str(uuid.uuid4())[:25])
    ordem             = db.Column(db.Integer, nullable=False)
    nmcampo           = db.Column(db.String(25), nullable=False)
    descricao         = db.Column(db.String(60), nullable=False)
    tipo              = db.Column(db.String(18), nullable=False)
    tabela            = db.Column(db.String(18), nullable=False)
    lista             = db.Column(db.Boolean, default=False, nullable=False)
    filtro            = db.Column(db.Boolean, default=False, nullable=False)
    filtrodefault     = db.Column('FILTRODEFAULT', db.String(100), nullable=True)
    admin             = db.Column(db.Boolean, default=False, nullable=False)
    ronly             = db.Column(db.Boolean, default=False, nullable=False)
    combo             = db.Column(db.String(200), nullable=True)
    virtual           = db.Column(db.String(200), nullable=True)
    tam               = db.Column(db.Integer, nullable=False)
    ordem_mobile      = db.Column(db.Integer, nullable=False)
    tam_mobile        = db.Column(db.Integer, nullable=False)
    condicao_visivel  = db.Column(db.String(200), nullable=True)
    obrigatorio       = db.Column(db.Boolean, default=False, nullable=False)

class MenuObjeto(db.Model):
    __tablename__ = 'MENU_OBJETOS'
    menuobjstamp      = db.Column(db.String(25), primary_key=True, default=lambda: str(uuid.uuid4())[:25])
    menustamp         = db.Column(db.String(25), nullable=False)
    nmcampo           = db.Column(db.String(50), nullable=False)
    descricao         = db.Column(db.String(100), nullable=False, default='')
    tipo              = db.Column(db.String(20), nullable=False)
    ordem             = db.Column(db.Integer, nullable=False, default=0)
    tam               = db.Column(db.Integer, nullable=False, default=5)
    ordem_mobile      = db.Column(db.Integer, nullable=False, default=0)
    tam_mobile        = db.Column(db.Integer, nullable=False, default=5)
    visivel           = db.Column(db.Boolean, nullable=False, default=True)
    ronly             = db.Column(db.Boolean, nullable=False, default=False)
    obrigatorio       = db.Column(db.Boolean, nullable=False, default=False)
    condicao_visivel  = db.Column(db.String(200), nullable=False, default='')
    combo             = db.Column(db.Text, nullable=False, default='')
    decimais          = db.Column(db.Integer, nullable=False, default=0)
    minimo            = db.Column(db.Numeric(18, 6), nullable=True)
    maximo            = db.Column(db.Numeric(18, 6), nullable=True)
    propriedades      = db.Column(db.Text, nullable=False, default='{}')
    ativo             = db.Column(db.Boolean, nullable=False, default=True)
    dtcri             = db.Column('DTCRI', db.DateTime, nullable=False)
    dtalt             = db.Column('DTALT', db.DateTime, nullable=True)
    usercriacao       = db.Column(db.String(50), nullable=False, default='')
    useralteracao     = db.Column(db.String(50), nullable=False, default='')

class MenuVariavel(db.Model):
    __tablename__ = 'MENU_VARIAVEIS'
    menuvarstamp      = db.Column(db.String(25), primary_key=True, default=lambda: str(uuid.uuid4())[:25])
    menustamp         = db.Column(db.String(25), nullable=False)
    nome              = db.Column(db.String(60), nullable=False)
    descricao         = db.Column(db.String(100), nullable=False, default='')
    tipo              = db.Column(db.String(20), nullable=False, default='TEXT')
    valor_default     = db.Column(db.Text, nullable=False, default='')
    ordem             = db.Column(db.Integer, nullable=False, default=0)
    propriedades      = db.Column(db.Text, nullable=False, default='{}')
    ativo             = db.Column(db.Boolean, nullable=False, default=True)
    dtcri             = db.Column('DTCRI', db.DateTime, nullable=False)
    dtalt             = db.Column('DTALT', db.DateTime, nullable=True)
    usercriacao       = db.Column(db.String(50), nullable=False, default='')
    useralteracao     = db.Column(db.String(50), nullable=False, default='')

class MenuEvento(db.Model):
    __tablename__ = 'MENU_EVENTOS'
    menueventostamp   = db.Column(db.String(25), primary_key=True, default=lambda: str(uuid.uuid4())[:25])
    menustamp         = db.Column(db.String(25), nullable=False)
    evento            = db.Column(db.String(40), nullable=False)
    fluxo             = db.Column(db.Text, nullable=False, default='{}')
    ativo             = db.Column(db.Boolean, nullable=False, default=True)
    dtcri             = db.Column('DTCRI', db.DateTime, nullable=False)
    dtalt             = db.Column('DTALT', db.DateTime, nullable=True)
    usercriacao       = db.Column(db.String(50), nullable=False, default='')
    useralteracao     = db.Column(db.String(50), nullable=False, default='')


class DocParser(db.Model):
    __tablename__ = 'DOC_PARSER'

    docparserstamp    = db.Column(db.String(25), primary_key=True, default=lambda: str(uuid.uuid4())[:25])
    codigo            = db.Column(db.String(60), nullable=False, unique=True)
    nome              = db.Column(db.String(100), nullable=False)
    descricao         = db.Column(db.Text, nullable=False, default='')
    familia           = db.Column(db.String(40), nullable=False, default='text_rules')
    versao            = db.Column(db.String(20), nullable=False, default='1.0')
    schema_output_json = db.Column(db.Text, nullable=False, default='{}')
    ativo             = db.Column(db.Boolean, nullable=False, default=True)
    dtcri             = db.Column('DTCRI', db.DateTime, nullable=False)
    dtalt             = db.Column('DTALT', db.DateTime, nullable=True)
    usercriacao       = db.Column(db.String(50), nullable=False, default='')
    useralteracao     = db.Column(db.String(50), nullable=False, default='')


class DocTemplate(db.Model):
    __tablename__ = 'DOC_TEMPLATE'

    doctemplatestamp  = db.Column(db.String(25), primary_key=True, default=lambda: str(uuid.uuid4())[:25])
    nome              = db.Column(db.String(120), nullable=False)
    descricao         = db.Column(db.Text, nullable=False, default='')
    fornecedor_no     = db.Column(db.Integer, nullable=True)
    doc_type          = db.Column(db.String(30), nullable=False, default='unknown')
    idioma            = db.Column(db.String(20), nullable=True)
    fingerprint       = db.Column(db.String(255), nullable=True)
    score_minimo_match = db.Column(db.Numeric(8, 4), nullable=False, default=0.55)
    regras_identificacao_json = db.Column(db.Text, nullable=False, default='{}')
    definition_json   = db.Column(db.Text, nullable=False, default='{}')
    docparserstamp    = db.Column(db.String(25), nullable=True)
    parser_version    = db.Column(db.String(20), nullable=True)
    ativo             = db.Column(db.Boolean, nullable=False, default=True)
    dtcri             = db.Column('DTCRI', db.DateTime, nullable=False)
    dtalt             = db.Column('DTALT', db.DateTime, nullable=True)
    usercriacao       = db.Column(db.String(50), nullable=False, default='')
    useralteracao     = db.Column(db.String(50), nullable=False, default='')


class DocTemplateField(db.Model):
    __tablename__ = 'DOC_TEMPLATE_FIELD'

    doctemplatefieldstamp = db.Column(db.String(25), primary_key=True, default=lambda: str(uuid.uuid4())[:25])
    doctemplatestamp  = db.Column(db.String(25), nullable=False)
    field_key         = db.Column(db.String(60), nullable=False)
    label             = db.Column(db.String(100), nullable=False, default='')
    ordem             = db.Column(db.Integer, nullable=False, default=0)
    required          = db.Column(db.Boolean, nullable=False, default=False)
    match_mode        = db.Column(db.String(30), nullable=False, default='anchor_regex')
    anchors_json      = db.Column(db.Text, nullable=False, default='[]')
    regex_pattern     = db.Column(db.Text, nullable=True)
    aliases_json      = db.Column(db.Text, nullable=False, default='[]')
    postprocess       = db.Column(db.String(40), nullable=True)
    config_json       = db.Column(db.Text, nullable=False, default='{}')
    ativo             = db.Column(db.Boolean, nullable=False, default=True)
    dtcri             = db.Column('DTCRI', db.DateTime, nullable=False)
    dtalt             = db.Column('DTALT', db.DateTime, nullable=True)
    usercriacao       = db.Column(db.String(50), nullable=False, default='')
    useralteracao     = db.Column(db.String(50), nullable=False, default='')


class DocInbox(db.Model):
    __tablename__ = 'DOC_INBOX'

    docinstamp        = db.Column(db.String(25), primary_key=True, default=lambda: str(uuid.uuid4())[:25])
    feid              = db.Column(db.Integer, nullable=True)
    anexosstamp       = db.Column(db.String(25), nullable=True)
    source_table      = db.Column(db.String(50), nullable=True)
    source_recstamp   = db.Column(db.String(50), nullable=True)
    file_name         = db.Column(db.String(260), nullable=False, default='')
    file_path         = db.Column(db.String(400), nullable=False, default='')
    file_ext          = db.Column(db.String(20), nullable=False, default='')
    mime_type         = db.Column(db.String(100), nullable=False, default='')
    file_hash         = db.Column(db.String(128), nullable=True)
    file_size         = db.Column(db.BigInteger, nullable=False, default=0)
    extracted_text    = db.Column(db.Text, nullable=False, default='')
    extraction_method = db.Column(db.String(40), nullable=False, default='failed')
    extraction_quality_score = db.Column(db.Numeric(8, 4), nullable=False, default=0)
    extraction_notes_json = db.Column(db.Text, nullable=False, default='{}')
    preprocessed_image_path = db.Column(db.String(400), nullable=True)
    ocr_raw_json      = db.Column(db.Text, nullable=False, default='{}')
    text_blocks_json  = db.Column(db.Text, nullable=False, default='[]')
    processing_stage  = db.Column(db.String(40), nullable=False, default='new')
    last_processing_error = db.Column(db.Text, nullable=False, default='')
    doc_type_detected = db.Column(db.String(30), nullable=False, default='unknown')
    fornecedor_no     = db.Column(db.Integer, nullable=True)
    fornecedor_nif_detetado = db.Column(db.String(40), nullable=True)
    fornecedor_nome_detetado = db.Column(db.String(120), nullable=True)
    doctemplatestamp  = db.Column(db.String(25), nullable=True)
    docparserstamp    = db.Column(db.String(25), nullable=True)
    parser_version    = db.Column(db.String(20), nullable=True)
    confidence_score  = db.Column(db.Numeric(8, 4), nullable=False, default=0)
    processing_status = db.Column(db.String(30), nullable=False, default='new')
    json_resultado    = db.Column(db.Text, nullable=False, default='{}')
    warnings_json     = db.Column(db.Text, nullable=False, default='[]')
    errors_json       = db.Column(db.Text, nullable=False, default='[]')
    processing_meta_json = db.Column(db.Text, nullable=False, default='{}')
    dtproc            = db.Column('DTPROC', db.DateTime, nullable=True)
    dtcri             = db.Column('DTCRI', db.DateTime, nullable=False)
    dtalt             = db.Column('DTALT', db.DateTime, nullable=True)
    usercriacao       = db.Column(db.String(50), nullable=False, default='')
    useralteracao     = db.Column(db.String(50), nullable=False, default='')


class DocProcessLog(db.Model):
    __tablename__ = 'DOC_PROCESS_LOG'

    docprocesslogstamp = db.Column(db.String(25), primary_key=True, default=lambda: str(uuid.uuid4())[:25])
    docinstamp        = db.Column(db.String(25), nullable=False)
    fase              = db.Column(db.String(40), nullable=False)
    status            = db.Column(db.String(20), nullable=False, default='info')
    mensagem          = db.Column(db.String(255), nullable=False, default='')
    detalhe_json      = db.Column(db.Text, nullable=False, default='{}')
    dtcri             = db.Column('DTCRI', db.DateTime, nullable=False)

class US(UserMixin, db.Model):
    __tablename__ = 'US'
    USSTAMP  = db.Column(db.String(25), primary_key=True, default=lambda: str(uuid.uuid4())[:25])
    NOME     = db.Column(db.String(60), nullable=False)
    LOGIN    = db.Column(db.String(60), unique=True, nullable=False)
    PASSWORD = db.Column(db.String(128), nullable=False)
    EMAIL    = db.Column(db.String(120), unique=True, nullable=False)
    COR      = db.Column(db.String(20), nullable=True)
    ADMIN    = db.Column(db.Boolean, default=False, nullable=False)
    EQUIPA   = db.Column(db.String(25), nullable=True)
    DEV      = db.Column(db.Boolean, default=False, nullable=False)
    MNADMIN  = db.Column(db.Boolean, default=False, nullable=False)
    LSADMIN  = db.Column(db.Boolean, default=False, nullable=False)
    FOTO     = db.Column(db.String(255), nullable=True)  # caminho relativo sob /static
    LPADMIN  = db.Column(db.Boolean, default=False, nullable=False)
    HOME     = db.Column(db.String(200), unique=True, nullable=False)
    VIEWMODE = db.Column(db.String(20), nullable=False, default='LIGHT MODE')
    CLNO     = db.Column(db.Integer, nullable=True)
    CLNOME   = db.Column(db.String(120), nullable=True)

    def check_password(self, plaintext):
        from services.auth_service import verify_password_hash

        password_hash = getattr(self, 'PASSWORD_HASH', None)
        if password_hash:
            row = {
                'PASSWORD_HASH': password_hash,
                'PASSWORD_ALGO': getattr(self, 'PASSWORD_ALGO', None),
            }
            return verify_password_hash(row, plaintext)
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
    usstamp      = db.Column(db.String(100), nullable=False)


class FeClusterEntidade(db.Model):
    __tablename__ = 'FE_CLUSTER_ENTIDADES'

    FECLUSTERENTSTAMP = db.Column(db.String(25), primary_key=True, default=lambda: uuid.uuid4().hex.upper()[:25])
    FESTAMP_CLUSTER = db.Column(db.String(25), nullable=False)
    FESTAMP_ENTIDADE = db.Column(db.String(25), nullable=False)
    DTCRI = db.Column(db.DateTime, nullable=False)
    DTALT = db.Column(db.DateTime, nullable=True)
    USERCRIACAO = db.Column(db.String(50), nullable=False, default='')
    USERALTERACAO = db.Column(db.String(50), nullable=False, default='')

# Adiciona isto ao teu models.py
class Widget(db.Model):
    __tablename__ = 'WIDGETS'
    WIDGETSSTAMP = db.Column(db.String(25), primary_key=True)
    NOME         = db.Column(db.String(50), unique=True, nullable=False)
    TITULO       = db.Column(db.String(80), nullable=False, default='')
    TIPO         = db.Column(db.String(20), nullable=False, default='GRAFICO')
    FONTE        = db.Column(db.String(200), nullable=False, default='')
    CONFIG       = db.Column(db.Text, nullable=False, default='{}')
    FILTROS      = db.Column(db.Text, nullable=False, default='{}')
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
    CAMPOSCAB    = db.Column(db.String(200), nullable=False, default='')    
    CAMPOSLIN    = db.Column(db.String(200), nullable=False, default='')

class Usql(db.Model):
    __tablename__ = 'USQL'
    usqlstamp = db.Column(db.String(25), primary_key=True)
    descricao = db.Column(db.String(80), nullable=False)
    sqlexpr   = db.Column(db.Text, nullable=False)
    grupo     = db.Column(db.String(100), nullable=True)
    decimais  = db.Column(db.Numeric(5,2), nullable=False, default=2)
    totais    = db.Column(db.Boolean, nullable=False, default=False)
    temgraf   = db.Column(db.Boolean, nullable=False, default=False)
    tipograf  = db.Column(db.String(100), nullable=True)


class EmailProfile(db.Model):
    __tablename__ = 'EMAIL_PROFILES'

    ID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    NOME_PERFIL = db.Column(db.String(100), nullable=False, unique=True)
    DESCRICAO = db.Column(db.String(255), nullable=True)
    EMAIL_FROM = db.Column(db.String(255), nullable=False)
    NOME_FROM = db.Column(db.String(255), nullable=True)
    SMTP_HOST = db.Column(db.String(255), nullable=False)
    SMTP_PORT = db.Column(db.Integer, nullable=False)
    SMTP_USER = db.Column(db.String(255), nullable=True)
    SMTP_PASSWORD_ENC = db.Column(db.Text, nullable=True)
    USA_TLS = db.Column(db.Boolean, nullable=False, default=True)
    USA_SSL = db.Column(db.Boolean, nullable=False, default=False)
    ATIVO = db.Column(db.Boolean, nullable=False, default=True)
    DEFAULT_PROFILE = db.Column(db.Boolean, nullable=False, default=False)
    DATA_CRIACAO = db.Column(db.DateTime, nullable=False)
    DATA_ALTERACAO = db.Column(db.DateTime, nullable=True)


class EmailQueue(db.Model):
    __tablename__ = 'EMAIL_QUEUE'

    ID = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    PROFILE_ID = db.Column(db.Integer, db.ForeignKey('EMAIL_PROFILES.ID'), nullable=False)
    FROM_EMAIL = db.Column(db.String(255), nullable=True)
    FROM_NAME = db.Column(db.String(255), nullable=True)
    TO_EMAILS = db.Column(db.Text, nullable=False)
    CC_EMAILS = db.Column(db.Text, nullable=True)
    BCC_EMAILS = db.Column(db.Text, nullable=True)
    SUBJECT = db.Column(db.String(500), nullable=False)
    BODY_HTML = db.Column(db.Text, nullable=True)
    BODY_TEXT = db.Column(db.Text, nullable=True)
    PRIORIDADE = db.Column(db.Integer, nullable=False, default=5)
    ESTADO = db.Column(db.String(30), nullable=False, default='PENDENTE')
    TENTATIVAS = db.Column(db.Integer, nullable=False, default=0)
    MAX_TENTATIVAS = db.Column(db.Integer, nullable=False, default=3)
    ERRO_ULTIMA_TENTATIVA = db.Column(db.Text, nullable=True)
    DATA_AGENDADA = db.Column(db.DateTime, nullable=True)
    DATA_CRIACAO = db.Column(db.DateTime, nullable=False)
    DATA_ULTIMA_TENTATIVA = db.Column(db.DateTime, nullable=True)
    DATA_ENVIO = db.Column(db.DateTime, nullable=True)
    CRIADO_POR = db.Column(db.String(100), nullable=True)
    CONTEXTO = db.Column(db.String(100), nullable=True)
    CONTEXTO_ID = db.Column(db.String(100), nullable=True)


class EmailAttachment(db.Model):
    __tablename__ = 'EMAIL_ATTACHMENTS'

    ID = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    EMAIL_ID = db.Column(db.BigInteger, db.ForeignKey('EMAIL_QUEUE.ID'), nullable=False)
    FILE_NAME = db.Column(db.String(255), nullable=False)
    FILE_PATH = db.Column(db.String(1000), nullable=True)
    FILE_CONTENT = db.Column(db.LargeBinary, nullable=True)
    MIME_TYPE = db.Column(db.String(255), nullable=True)
    TAMANHO_BYTES = db.Column(db.BigInteger, nullable=True)
    DATA_CRIACAO = db.Column(db.DateTime, nullable=False)


class EmailLog(db.Model):
    __tablename__ = 'EMAIL_LOG'

    ID = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    EMAIL_ID = db.Column(db.BigInteger, db.ForeignKey('EMAIL_QUEUE.ID'), nullable=False)
    DATA_TENTATIVA = db.Column(db.DateTime, nullable=False)
    RESULTADO = db.Column(db.String(30), nullable=False)
    MENSAGEM = db.Column(db.Text, nullable=True)
    SMTP_RESPONSE = db.Column(db.Text, nullable=True)
