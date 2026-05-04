import base64
import hashlib
import mimetypes
import os
import re
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from email.utils import getaddresses, formataddr
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app
from sqlalchemy import text

from models import db


EMAIL_STATES = {'PENDENTE', 'A_ENVIAR', 'ENVIADO', 'ERRO', 'CANCELADO'}
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


class EmailServiceError(RuntimeError):
    pass


def _now():
    return datetime.now()


def _clean(value, default='') -> str:
    if value is None:
        return default
    return str(value).strip()


def _encryptor():
    raw_key = (
        _clean(current_app.config.get('EMAIL_SERVICE_SECRET_KEY'))
        or _clean(os.environ.get('EMAIL_SERVICE_SECRET_KEY'))
        or _clean(current_app.config.get('SECRET_KEY'))
    )
    digest = hashlib.sha256(raw_key.encode('utf-8')).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str) -> str:
    value = _clean(value)
    if not value:
        return ''
    return _encryptor().encrypt(value.encode('utf-8')).decode('utf-8')


def decrypt_secret(value: str) -> str:
    value = _clean(value)
    if not value:
        return ''
    try:
        return _encryptor().decrypt(value.encode('utf-8')).decode('utf-8')
    except InvalidToken:
        raise EmailServiceError('Não foi possível desencriptar a password SMTP.')


def ensure_email_tables():
    db.session.execute(text("""
        IF OBJECT_ID('dbo.EMAIL_PROFILES', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.EMAIL_PROFILES
            (
                ID int IDENTITY(1,1) NOT NULL PRIMARY KEY,
                NOME_PERFIL varchar(100) NOT NULL UNIQUE,
                DESCRICAO varchar(255) NULL,
                EMAIL_FROM varchar(255) NOT NULL,
                NOME_FROM varchar(255) NULL,
                SMTP_HOST varchar(255) NOT NULL,
                SMTP_PORT int NOT NULL,
                SMTP_USER varchar(255) NULL,
                SMTP_PASSWORD_ENC varchar(max) NULL,
                USA_TLS bit NOT NULL CONSTRAINT DF_EMAIL_PROFILES_TLS DEFAULT 1,
                USA_SSL bit NOT NULL CONSTRAINT DF_EMAIL_PROFILES_SSL DEFAULT 0,
                ATIVO bit NOT NULL CONSTRAINT DF_EMAIL_PROFILES_ATIVO DEFAULT 1,
                DEFAULT_PROFILE bit NOT NULL CONSTRAINT DF_EMAIL_PROFILES_DEFAULT DEFAULT 0,
                DATA_CRIACAO datetime NOT NULL CONSTRAINT DF_EMAIL_PROFILES_DCRI DEFAULT GETDATE(),
                DATA_ALTERACAO datetime NULL
            );
        END

        IF OBJECT_ID('dbo.EMAIL_QUEUE', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.EMAIL_QUEUE
            (
                ID bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
                PROFILE_ID int NOT NULL,
                FROM_EMAIL varchar(255) NULL,
                FROM_NAME varchar(255) NULL,
                TO_EMAILS varchar(max) NOT NULL,
                CC_EMAILS varchar(max) NULL,
                BCC_EMAILS varchar(max) NULL,
                SUBJECT varchar(500) NOT NULL,
                BODY_HTML varchar(max) NULL,
                BODY_TEXT varchar(max) NULL,
                PRIORIDADE int NOT NULL CONSTRAINT DF_EMAIL_QUEUE_PRIORIDADE DEFAULT 5,
                ESTADO varchar(30) NOT NULL CONSTRAINT DF_EMAIL_QUEUE_ESTADO DEFAULT 'PENDENTE',
                TENTATIVAS int NOT NULL CONSTRAINT DF_EMAIL_QUEUE_TENTATIVAS DEFAULT 0,
                MAX_TENTATIVAS int NOT NULL CONSTRAINT DF_EMAIL_QUEUE_MAXTENT DEFAULT 3,
                ERRO_ULTIMA_TENTATIVA varchar(max) NULL,
                DATA_AGENDADA datetime NULL,
                DATA_CRIACAO datetime NOT NULL CONSTRAINT DF_EMAIL_QUEUE_DCRI DEFAULT GETDATE(),
                DATA_ULTIMA_TENTATIVA datetime NULL,
                DATA_ENVIO datetime NULL,
                CRIADO_POR varchar(100) NULL,
                CONTEXTO varchar(100) NULL,
                CONTEXTO_ID varchar(100) NULL,
                CONSTRAINT FK_EMAIL_QUEUE_PROFILE FOREIGN KEY (PROFILE_ID) REFERENCES dbo.EMAIL_PROFILES(ID),
                CONSTRAINT CK_EMAIL_QUEUE_ESTADO CHECK (ESTADO IN ('PENDENTE', 'A_ENVIAR', 'ENVIADO', 'ERRO', 'CANCELADO'))
            );
        END

        IF OBJECT_ID('dbo.EMAIL_ATTACHMENTS', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.EMAIL_ATTACHMENTS
            (
                ID bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
                EMAIL_ID bigint NOT NULL,
                FILE_NAME varchar(255) NOT NULL,
                FILE_PATH varchar(1000) NULL,
                FILE_CONTENT varbinary(max) NULL,
                MIME_TYPE varchar(255) NULL,
                TAMANHO_BYTES bigint NULL,
                DATA_CRIACAO datetime NOT NULL CONSTRAINT DF_EMAIL_ATTACHMENTS_DCRI DEFAULT GETDATE(),
                CONSTRAINT FK_EMAIL_ATTACHMENTS_EMAIL FOREIGN KEY (EMAIL_ID) REFERENCES dbo.EMAIL_QUEUE(ID) ON DELETE CASCADE
            );
        END

        IF OBJECT_ID('dbo.EMAIL_LOG', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.EMAIL_LOG
            (
                ID bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
                EMAIL_ID bigint NOT NULL,
                DATA_TENTATIVA datetime NOT NULL CONSTRAINT DF_EMAIL_LOG_DTENT DEFAULT GETDATE(),
                RESULTADO varchar(30) NOT NULL,
                MENSAGEM varchar(max) NULL,
                SMTP_RESPONSE varchar(max) NULL,
                CONSTRAINT FK_EMAIL_LOG_EMAIL FOREIGN KEY (EMAIL_ID) REFERENCES dbo.EMAIL_QUEUE(ID) ON DELETE CASCADE
            );
        END
    """))
    for name, sql in {
        'IX_EMAIL_QUEUE_PROCESS': "CREATE INDEX IX_EMAIL_QUEUE_PROCESS ON dbo.EMAIL_QUEUE (ESTADO, DATA_AGENDADA, PRIORIDADE, DATA_CRIACAO)",
        'IX_EMAIL_QUEUE_PROFILE': "CREATE INDEX IX_EMAIL_QUEUE_PROFILE ON dbo.EMAIL_QUEUE (PROFILE_ID)",
        'IX_EMAIL_ATTACHMENTS_EMAIL': "CREATE INDEX IX_EMAIL_ATTACHMENTS_EMAIL ON dbo.EMAIL_ATTACHMENTS (EMAIL_ID)",
        'IX_EMAIL_LOG_EMAIL': "CREATE INDEX IX_EMAIL_LOG_EMAIL ON dbo.EMAIL_LOG (EMAIL_ID)",
        'UX_EMAIL_PROFILES_DEFAULT': "CREATE UNIQUE INDEX UX_EMAIL_PROFILES_DEFAULT ON dbo.EMAIL_PROFILES (DEFAULT_PROFILE) WHERE DEFAULT_PROFILE = 1",
    }.items():
        db.session.execute(text(f"""
            IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = :name AND object_id IN (
                OBJECT_ID('dbo.EMAIL_QUEUE'), OBJECT_ID('dbo.EMAIL_ATTACHMENTS'), OBJECT_ID('dbo.EMAIL_LOG'), OBJECT_ID('dbo.EMAIL_PROFILES')
            ))
            BEGIN
                {sql}
            END
        """), {'name': name})
    db.session.commit()


def parse_email_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        raw = ','.join(_clean(item) for item in value)
    else:
        raw = _clean(value).replace(';', ',')
    addresses = []
    for _, addr in getaddresses([raw]):
        addr = _clean(addr).lower()
        if addr and EMAIL_RE.match(addr):
            addresses.append(addr)
    seen = set()
    result = []
    for addr in addresses:
        if addr not in seen:
            seen.add(addr)
            result.append(addr)
    return result


def format_email_list(value) -> str:
    return '; '.join(parse_email_list(value))


def _require_valid_recipients(to, cc=None, bcc=None):
    to_list = parse_email_list(to)
    cc_list = parse_email_list(cc)
    bcc_list = parse_email_list(bcc)
    if not to_list:
        raise EmailServiceError('Pelo menos um destinatário é obrigatório.')
    return to_list, cc_list, bcc_list


def get_email_profile(profile_id=None, profile_name=None, active_only=False):
    ensure_email_tables()
    where = []
    params = {}
    if profile_id:
        where.append('ID = :profile_id')
        params['profile_id'] = int(profile_id)
    if profile_name:
        where.append('UPPER(NOME_PERFIL) = :profile_name')
        params['profile_name'] = _clean(profile_name).upper()
    if active_only:
        where.append('ISNULL(ATIVO,0) = 1')
    sql = "SELECT TOP 1 * FROM dbo.EMAIL_PROFILES"
    if where:
        sql += " WHERE " + " AND ".join(where)
    if not where:
        sql += " WHERE ISNULL(DEFAULT_PROFILE,0)=1 AND ISNULL(ATIVO,0)=1"
    sql += " ORDER BY DEFAULT_PROFILE DESC, ID"
    row = db.session.execute(text(sql), params).mappings().first()
    return dict(row) if row else None


def list_profiles(include_inactive=True):
    ensure_email_tables()
    where = '' if include_inactive else 'WHERE ISNULL(ATIVO,0)=1'
    rows = db.session.execute(text(f"""
        SELECT *
        FROM dbo.EMAIL_PROFILES
        {where}
        ORDER BY DEFAULT_PROFILE DESC, ATIVO DESC, NOME_PERFIL
    """)).mappings().all()
    return [dict(r) for r in rows]


def save_profile(data: dict, profile_id=None):
    ensure_email_tables()
    name = _clean(data.get('NOME_PERFIL') or data.get('nome_perfil')).upper()
    if not name:
        raise EmailServiceError('Nome do perfil obrigatório.')
    email_from = _clean(data.get('EMAIL_FROM') or data.get('email_from')).lower()
    if not parse_email_list(email_from):
        raise EmailServiceError('Email remetente inválido.')
    smtp_host = _clean(data.get('SMTP_HOST') or data.get('smtp_host'))
    smtp_port = int(data.get('SMTP_PORT') or data.get('smtp_port') or 0)
    if not smtp_host or smtp_port <= 0:
        raise EmailServiceError('Host e porta SMTP são obrigatórios.')
    usa_tls = bool(data.get('USA_TLS') or data.get('usa_tls'))
    usa_ssl = bool(data.get('USA_SSL') or data.get('usa_ssl'))
    if usa_ssl and smtp_port != 465:
        # SQL Server Database Mail chama "SSL" ao STARTTLS usado normalmente na porta 587.
        usa_tls = True
        usa_ssl = False
    elif usa_ssl and smtp_port == 465:
        usa_tls = False
    is_default = bool(data.get('DEFAULT_PROFILE') or data.get('default_profile'))
    password = data.get('SMTP_PASSWORD') if 'SMTP_PASSWORD' in data else data.get('smtp_password')
    password_enc = encrypt_secret(password) if _clean(password) else None
    now = _now()

    duplicate = db.session.execute(text("""
        SELECT TOP 1 ID
        FROM dbo.EMAIL_PROFILES
        WHERE UPPER(NOME_PERFIL)=:name
          AND (:profile_id IS NULL OR ID <> :profile_id)
    """), {'name': name, 'profile_id': profile_id}).scalar()
    if duplicate:
        raise EmailServiceError('Já existe um perfil com esse nome.')

    if is_default:
        db.session.execute(text("""
            UPDATE dbo.EMAIL_PROFILES
            SET DEFAULT_PROFILE = 0, DATA_ALTERACAO = :now
            WHERE (:profile_id IS NULL OR ID <> :profile_id)
        """), {'now': now, 'profile_id': profile_id})

    params = {
        'name': name,
        'desc': _clean(data.get('DESCRICAO') or data.get('descricao')),
        'email_from': email_from,
        'name_from': _clean(data.get('NOME_FROM') or data.get('nome_from')),
        'smtp_host': smtp_host,
        'smtp_port': smtp_port,
        'smtp_user': _clean(data.get('SMTP_USER') or data.get('smtp_user')),
        'usa_tls': 1 if usa_tls else 0,
        'usa_ssl': 1 if usa_ssl else 0,
        'ativo': 1 if (data.get('ATIVO') is None or data.get('ATIVO') or data.get('ativo')) else 0,
        'default_profile': 1 if is_default else 0,
        'now': now,
        'profile_id': profile_id,
    }
    if profile_id:
        sql_password = ', SMTP_PASSWORD_ENC = :password_enc' if password_enc is not None else ''
        params['password_enc'] = password_enc
        db.session.execute(text(f"""
            UPDATE dbo.EMAIL_PROFILES
            SET NOME_PERFIL=:name, DESCRICAO=:desc, EMAIL_FROM=:email_from, NOME_FROM=:name_from,
                SMTP_HOST=:smtp_host, SMTP_PORT=:smtp_port, SMTP_USER=:smtp_user,
                USA_TLS=:usa_tls, USA_SSL=:usa_ssl, ATIVO=:ativo, DEFAULT_PROFILE=:default_profile,
                DATA_ALTERACAO=:now
                {sql_password}
            WHERE ID=:profile_id
        """), params)
    else:
        params['password_enc'] = password_enc or ''
        profile_id = db.session.execute(text("""
            INSERT INTO dbo.EMAIL_PROFILES
            (NOME_PERFIL, DESCRICAO, EMAIL_FROM, NOME_FROM, SMTP_HOST, SMTP_PORT, SMTP_USER,
             SMTP_PASSWORD_ENC, USA_TLS, USA_SSL, ATIVO, DEFAULT_PROFILE, DATA_CRIACAO)
            OUTPUT INSERTED.ID
            VALUES
            (:name, :desc, :email_from, :name_from, :smtp_host, :smtp_port, :smtp_user,
             :password_enc, :usa_tls, :usa_ssl, :ativo, :default_profile, :now)
        """), params).scalar()
    db.session.commit()
    return int(profile_id or 0)


def _queue_row(email_id: int):
    row = db.session.execute(text("""
        SELECT Q.*, P.NOME_PERFIL, P.EMAIL_FROM AS PROFILE_EMAIL_FROM, P.NOME_FROM AS PROFILE_NOME_FROM,
               P.SMTP_HOST, P.SMTP_PORT, P.SMTP_USER, P.SMTP_PASSWORD_ENC, P.USA_TLS, P.USA_SSL, P.ATIVO AS PROFILE_ATIVO
        FROM dbo.EMAIL_QUEUE Q
        INNER JOIN dbo.EMAIL_PROFILES P ON P.ID = Q.PROFILE_ID
        WHERE Q.ID = :email_id
    """), {'email_id': int(email_id)}).mappings().first()
    return dict(row) if row else None


def queue_email(profile_name='', profile_id=None, to=None, subject='', body_html='', body_text='',
                cc=None, bcc=None, attachments=None, priority=5, context='', context_id='',
                scheduled_at=None, created_by='', max_attempts=3, from_email='', from_name=''):
    ensure_email_tables()
    profile = get_email_profile(profile_id=profile_id, profile_name=profile_name, active_only=True)
    if not profile:
        raise EmailServiceError('Perfil de email ativo não encontrado.')
    to_list, cc_list, bcc_list = _require_valid_recipients(to, cc, bcc)
    subject = _clean(subject)
    if not subject:
        raise EmailServiceError('Assunto obrigatório.')
    if not _clean(body_html) and not _clean(body_text):
        raise EmailServiceError('Corpo HTML ou texto obrigatório.')
    email_id = int(db.session.execute(text("""
        INSERT INTO dbo.EMAIL_QUEUE
        (PROFILE_ID, FROM_EMAIL, FROM_NAME, TO_EMAILS, CC_EMAILS, BCC_EMAILS, SUBJECT, BODY_HTML, BODY_TEXT,
         PRIORIDADE, ESTADO, TENTATIVAS, MAX_TENTATIVAS, DATA_AGENDADA, DATA_CRIACAO, CRIADO_POR, CONTEXTO, CONTEXTO_ID)
        OUTPUT INSERTED.ID
        VALUES
        (:profile_id, :from_email, :from_name, :to_emails, :cc_emails, :bcc_emails, :subject, :body_html, :body_text,
         :priority, 'PENDENTE', 0, :max_attempts, :scheduled_at, :now, :created_by, :context, :context_id)
    """), {
        'profile_id': int(profile['ID']),
        'from_email': _clean(from_email),
        'from_name': _clean(from_name),
        'to_emails': '; '.join(to_list),
        'cc_emails': '; '.join(cc_list),
        'bcc_emails': '; '.join(bcc_list),
        'subject': subject[:500],
        'body_html': _clean(body_html),
        'body_text': _clean(body_text),
        'priority': int(priority or 5),
        'max_attempts': int(max_attempts or 3),
        'scheduled_at': scheduled_at,
        'now': _now(),
        'created_by': _clean(created_by),
        'context': _clean(context),
        'context_id': _clean(context_id),
    }).scalar() or 0)
    for attachment in attachments or []:
        add_attachment(email_id, **attachment)
    db.session.commit()
    return email_id


def _allowed_attachment_dirs() -> list[Path]:
    values = current_app.config.get('EMAIL_ATTACHMENT_DIRS') or []
    if isinstance(values, (str, os.PathLike)):
        values = [values]
    default_dir = Path(current_app.instance_path) / 'email_attachments'
    dirs = [default_dir]
    for value in values:
        if value:
            dirs.append(Path(value))
    return [path.resolve() for path in dirs]


def _validate_attachment_path(file_path: str) -> Path:
    raw = _clean(file_path)
    if not raw:
        raise EmailServiceError('Caminho do anexo em falta.')
    path = Path(raw).resolve()
    if not path.exists() or not path.is_file():
        raise EmailServiceError(f'Anexo não encontrado: {path.name}')
    allowed = _allowed_attachment_dirs()
    if not any(path == base or base in path.parents for base in allowed):
        raise EmailServiceError('Anexo fora das pastas permitidas.')
    return path


def add_attachment(email_id: int, file_name='', file_path='', file_content=None, mime_type=''):
    ensure_email_tables()
    data = file_content
    size = None
    path_value = _clean(file_path)
    name = _clean(file_name)
    if path_value:
        path = _validate_attachment_path(path_value)
        name = name or path.name
        size = path.stat().st_size
    elif data is not None:
        if isinstance(data, str):
            data = data.encode('utf-8')
        size = len(data)
    else:
        raise EmailServiceError('Anexo sem caminho ou conteúdo.')
    if not name:
        raise EmailServiceError('Nome do anexo obrigatório.')
    mime = _clean(mime_type) or mimetypes.guess_type(name)[0] or 'application/octet-stream'
    db.session.execute(text("""
        INSERT INTO dbo.EMAIL_ATTACHMENTS
        (EMAIL_ID, FILE_NAME, FILE_PATH, FILE_CONTENT, MIME_TYPE, TAMANHO_BYTES, DATA_CRIACAO)
        VALUES
        (:email_id, :file_name, :file_path, :file_content, :mime_type, :size, :now)
    """), {
        'email_id': int(email_id),
        'file_name': name[:255],
        'file_path': path_value,
        'file_content': data,
        'mime_type': mime[:255],
        'size': size,
        'now': _now(),
    })
    db.session.commit()


def _attachments(email_id: int):
    rows = db.session.execute(text("""
        SELECT *
        FROM dbo.EMAIL_ATTACHMENTS
        WHERE EMAIL_ID = :email_id
        ORDER BY ID
    """), {'email_id': int(email_id)}).mappings().all()
    return [dict(r) for r in rows]


def _logs(email_id: int):
    rows = db.session.execute(text("""
        SELECT *
        FROM dbo.EMAIL_LOG
        WHERE EMAIL_ID = :email_id
        ORDER BY DATA_TENTATIVA DESC, ID DESC
    """), {'email_id': int(email_id)}).mappings().all()
    return [dict(r) for r in rows]


def get_email_detail(email_id: int):
    ensure_email_tables()
    email_row = _queue_row(email_id)
    if not email_row:
        return None
    return {
        'email': email_row,
        'attachments': _attachments(email_id),
        'logs': _logs(email_id),
    }


def list_queue(filters=None, limit=200):
    ensure_email_tables()
    filters = filters or {}
    where = []
    params = {'limit': int(limit or 200)}
    if _clean(filters.get('estado')):
        where.append('Q.ESTADO = :estado')
        params['estado'] = _clean(filters.get('estado')).upper()
    if _clean(filters.get('profile_id')):
        where.append('Q.PROFILE_ID = :profile_id')
        params['profile_id'] = int(filters.get('profile_id'))
    if _clean(filters.get('search')):
        where.append('(Q.SUBJECT LIKE :search OR Q.TO_EMAILS LIKE :search OR Q.CONTEXTO LIKE :search OR Q.CONTEXTO_ID LIKE :search)')
        params['search'] = f"%{_clean(filters.get('search'))}%"
    if _clean(filters.get('date_from')):
        where.append('Q.DATA_CRIACAO >= :date_from')
        params['date_from'] = filters.get('date_from')
    if _clean(filters.get('date_to')):
        where.append('Q.DATA_CRIACAO < DATEADD(day, 1, :date_to)')
        params['date_to'] = filters.get('date_to')
    where_sql = 'WHERE ' + ' AND '.join(where) if where else ''
    rows = db.session.execute(text(f"""
        SELECT TOP (:limit)
            Q.ID, Q.PROFILE_ID, P.NOME_PERFIL, Q.TO_EMAILS, Q.SUBJECT, Q.ESTADO, Q.TENTATIVAS,
            Q.MAX_TENTATIVAS, Q.DATA_CRIACAO, Q.DATA_ENVIO, Q.DATA_AGENDADA,
            Q.ERRO_ULTIMA_TENTATIVA, Q.PRIORIDADE, Q.CONTEXTO, Q.CONTEXTO_ID
        FROM dbo.EMAIL_QUEUE Q
        INNER JOIN dbo.EMAIL_PROFILES P ON P.ID = Q.PROFILE_ID
        {where_sql}
        ORDER BY Q.DATA_CRIACAO DESC, Q.ID DESC
    """), params).mappings().all()
    return [dict(r) for r in rows]


def _log_attempt(email_id: int, result: str, message: str = '', smtp_response: str = ''):
    db.session.execute(text("""
        INSERT INTO dbo.EMAIL_LOG
        (EMAIL_ID, DATA_TENTATIVA, RESULTADO, MENSAGEM, SMTP_RESPONSE)
        VALUES
        (:email_id, :now, :result, :message, :smtp_response)
    """), {
        'email_id': int(email_id),
        'now': _now(),
        'result': _clean(result).upper()[:30],
        'message': _clean(message),
        'smtp_response': _clean(smtp_response),
    })


def mark_email_sent(email_id: int):
    db.session.execute(text("""
        UPDATE dbo.EMAIL_QUEUE
        SET ESTADO='ENVIADO', DATA_ENVIO=:now, DATA_ULTIMA_TENTATIVA=:now, ERRO_ULTIMA_TENTATIVA=NULL
        WHERE ID=:email_id
    """), {'email_id': int(email_id), 'now': _now()})
    _log_attempt(email_id, 'ENVIADO', 'Email enviado com sucesso.')
    db.session.commit()


def mark_email_error(email_id: int, error_message: str):
    row = db.session.execute(text("""
        SELECT TENTATIVAS, MAX_TENTATIVAS
        FROM dbo.EMAIL_QUEUE
        WHERE ID=:email_id
    """), {'email_id': int(email_id)}).mappings().first()
    attempts = int((row or {}).get('TENTATIVAS') or 0) + 1
    max_attempts = int((row or {}).get('MAX_TENTATIVAS') or 3)
    state = 'ERRO' if attempts >= max_attempts else 'PENDENTE'
    db.session.execute(text("""
        UPDATE dbo.EMAIL_QUEUE
        SET ESTADO=:state, TENTATIVAS=:attempts, DATA_ULTIMA_TENTATIVA=:now, ERRO_ULTIMA_TENTATIVA=:error
        WHERE ID=:email_id
    """), {
        'email_id': int(email_id),
        'state': state,
        'attempts': attempts,
        'now': _now(),
        'error': _clean(error_message),
    })
    _log_attempt(email_id, 'ERRO', _clean(error_message))
    db.session.commit()


def _build_message(row: dict, attachments: list[dict]) -> EmailMessage:
    to_list, cc_list, bcc_list = _require_valid_recipients(row.get('TO_EMAILS'), row.get('CC_EMAILS'), row.get('BCC_EMAILS'))
    from_email = _clean(row.get('FROM_EMAIL')) or _clean(row.get('PROFILE_EMAIL_FROM'))
    from_name = _clean(row.get('FROM_NAME')) or _clean(row.get('PROFILE_NOME_FROM'))
    msg = EmailMessage()
    msg['From'] = formataddr((from_name, from_email)) if from_name else from_email
    msg['To'] = ', '.join(to_list)
    if cc_list:
        msg['Cc'] = ', '.join(cc_list)
    msg['Subject'] = _clean(row.get('SUBJECT'))
    body_text = _clean(row.get('BODY_TEXT')) or ' '
    body_html = _clean(row.get('BODY_HTML'))
    msg.set_content(body_text)
    if body_html:
        msg.add_alternative(body_html, subtype='html')
    for item in attachments:
        name = _clean(item.get('FILE_NAME'))
        mime = _clean(item.get('MIME_TYPE')) or mimetypes.guess_type(name)[0] or 'application/octet-stream'
        maintype, subtype = mime.split('/', 1) if '/' in mime else ('application', 'octet-stream')
        if item.get('FILE_CONTENT') is not None:
            content = bytes(item.get('FILE_CONTENT'))
        else:
            path = _validate_attachment_path(item.get('FILE_PATH'))
            content = path.read_bytes()
        msg.add_attachment(content, maintype=maintype, subtype=subtype, filename=name)
    return msg


def _smtp_connection_mode(row: dict) -> str:
    port = int(row.get('SMTP_PORT') or 0)
    use_ssl = bool(row.get('USA_SSL'))
    use_tls = bool(row.get('USA_TLS'))
    if use_ssl and port == 465:
        return 'SSL'
    if use_tls or use_ssl:
        return 'STARTTLS'
    return 'PLAIN'


def send_email_now(email_id: int):
    ensure_email_tables()
    row = _queue_row(email_id)
    if not row:
        raise EmailServiceError('Email não encontrado.')
    if _clean(row.get('ESTADO')).upper() != 'PENDENTE':
        raise EmailServiceError('Só emails pendentes podem ser enviados.')
    if not bool(row.get('PROFILE_ATIVO')):
        raise EmailServiceError('Perfil de email inativo.')

    db.session.execute(text("""
        UPDATE dbo.EMAIL_QUEUE
        SET ESTADO='A_ENVIAR', DATA_ULTIMA_TENTATIVA=:now
        WHERE ID=:email_id AND ESTADO='PENDENTE'
    """), {'email_id': int(email_id), 'now': _now()})
    db.session.commit()

    password = ''
    try:
        attachments = _attachments(email_id)
        msg = _build_message(row, attachments)
        recipients = parse_email_list(row.get('TO_EMAILS')) + parse_email_list(row.get('CC_EMAILS')) + parse_email_list(row.get('BCC_EMAILS'))
        host = _clean(row.get('SMTP_HOST'))
        port = int(row.get('SMTP_PORT') or 0)
        username = _clean(row.get('SMTP_USER'))
        password = decrypt_secret(row.get('SMTP_PASSWORD_ENC')) if row.get('SMTP_PASSWORD_ENC') else ''
        smtp_mode = _smtp_connection_mode(row)
        if smtp_mode == 'SSL':
            smtp = smtplib.SMTP_SSL(host, port, timeout=30, context=ssl.create_default_context())
        else:
            smtp = smtplib.SMTP(host, port, timeout=30)
        with smtp:
            smtp.ehlo()
            if smtp_mode == 'STARTTLS':
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
            if username:
                smtp.login(username, password)
            response = smtp.send_message(msg, to_addrs=recipients)
        mark_email_sent(email_id)
        return {'ok': True, 'email_id': int(email_id), 'smtp_response': response}
    except Exception as exc:
        try:
            db.session.rollback()
        except Exception:
            pass
        safe_error = _clean(str(exc))
        if password:
            safe_error = safe_error.replace(password, '***')
        mark_email_error(email_id, safe_error)
        current_app.logger.exception('Erro ao enviar email %s', email_id)
        return {'ok': False, 'email_id': int(email_id), 'error': safe_error}


def process_email_queue(limit=20):
    ensure_email_tables()
    rows = db.session.execute(text("""
        SELECT TOP (:limit) ID
        FROM dbo.EMAIL_QUEUE WITH (READPAST)
        WHERE ESTADO='PENDENTE'
          AND (DATA_AGENDADA IS NULL OR DATA_AGENDADA <= GETDATE())
        ORDER BY PRIORIDADE ASC, DATA_CRIACAO ASC, ID ASC
    """), {'limit': int(limit or 20)}).mappings().all()
    results = []
    for row in rows:
        try:
            results.append(send_email_now(int(row.get('ID'))))
        except Exception as exc:
            current_app.logger.exception('Erro ao processar email em fila')
            results.append({'ok': False, 'email_id': int(row.get('ID')), 'error': str(exc)})
    return {'processed': len(results), 'results': results}


def test_email_profile(profile_id: int, test_recipient: str):
    profile = get_email_profile(profile_id=profile_id, active_only=True)
    if not profile:
        raise EmailServiceError('Perfil ativo não encontrado.')
    email_id = queue_email(
        profile_id=profile['ID'],
        to=[test_recipient],
        subject=f"Teste de email - {profile['NOME_PERFIL']}",
        body_text='Email de teste enviado pela aplicação.',
        body_html='<p>Email de teste enviado pela aplicação.</p>',
        priority=1,
        context='EMAIL_TEST',
        context_id=str(profile['ID']),
        created_by='system',
    )
    return send_email_now(email_id)


def update_queue_state(email_id: int, state: str):
    state = _clean(state).upper()
    if state not in EMAIL_STATES:
        raise EmailServiceError('Estado inválido.')
    db.session.execute(text("""
        UPDATE dbo.EMAIL_QUEUE
        SET ESTADO=:state
        WHERE ID=:email_id
    """), {'email_id': int(email_id), 'state': state})
    _log_attempt(email_id, state, f'Estado alterado para {state}.')
    db.session.commit()


def requeue_email(email_id: int):
    db.session.execute(text("""
        UPDATE dbo.EMAIL_QUEUE
        SET ESTADO='PENDENTE', TENTATIVAS=0, ERRO_ULTIMA_TENTATIVA=NULL, DATA_ENVIO=NULL
        WHERE ID=:email_id
    """), {'email_id': int(email_id)})
    _log_attempt(email_id, 'PENDENTE', 'Email reprocessado manualmente.')
    db.session.commit()


def duplicate_email(email_id: int, created_by=''):
    detail = get_email_detail(email_id)
    if not detail:
        raise EmailServiceError('Email não encontrado.')
    row = detail['email']
    new_id = queue_email(
        profile_id=row['PROFILE_ID'],
        to=row['TO_EMAILS'],
        cc=row.get('CC_EMAILS'),
        bcc=row.get('BCC_EMAILS'),
        subject=row['SUBJECT'],
        body_html=row.get('BODY_HTML'),
        body_text=row.get('BODY_TEXT'),
        priority=row.get('PRIORIDADE') or 5,
        context=row.get('CONTEXTO'),
        context_id=row.get('CONTEXTO_ID'),
        created_by=created_by,
        max_attempts=row.get('MAX_TENTATIVAS') or 3,
        from_email=row.get('FROM_EMAIL'),
        from_name=row.get('FROM_NAME'),
    )
    for att in detail['attachments']:
        add_attachment(
            new_id,
            file_name=att.get('FILE_NAME'),
            file_path=att.get('FILE_PATH'),
            file_content=att.get('FILE_CONTENT'),
            mime_type=att.get('MIME_TYPE'),
        )
    return new_id
