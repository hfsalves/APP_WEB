from __future__ import annotations

import uuid
from typing import Any, Mapping

from sqlalchemy import text


def _new_stamp() -> str:
    return uuid.uuid4().hex.upper()[:25]


def ensure_application_audit_schema(db_session) -> None:
    """Create the application-session and turnover audit tables when missing."""
    db_session.execute(text("""
        IF OBJECT_ID('dbo.APP_SESSAO_LOG', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.APP_SESSAO_LOG (
                APPSESSAOSTAMP varchar(25) NOT NULL
                    CONSTRAINT PK_APP_SESSAO_LOG PRIMARY KEY,
                LOGIN_TENTADO varchar(100) NOT NULL
                    CONSTRAINT DF_APP_SESSAO_LOGIN DEFAULT '',
                USSTAMP varchar(25) NOT NULL
                    CONSTRAINT DF_APP_SESSAO_USSTAMP DEFAULT '',
                NOME nvarchar(120) NOT NULL
                    CONSTRAINT DF_APP_SESSAO_NOME DEFAULT '',
                FEID int NULL,
                SUCESSO bit NOT NULL
                    CONSTRAINT DF_APP_SESSAO_SUCESSO DEFAULT 0,
                MOTIVO varchar(60) NOT NULL
                    CONSTRAINT DF_APP_SESSAO_MOTIVO DEFAULT '',
                ENTRADA_UTC datetime2(3) NOT NULL
                    CONSTRAINT DF_APP_SESSAO_ENTRADA DEFAULT SYSUTCDATETIME(),
                ULTIMA_ATIVIDADE_UTC datetime2(3) NULL,
                SAIDA_UTC datetime2(3) NULL,
                SAIDA_TIPO varchar(30) NOT NULL
                    CONSTRAINT DF_APP_SESSAO_SAIDA_TIPO DEFAULT '',
                IP_ENTRADA varchar(64) NOT NULL
                    CONSTRAINT DF_APP_SESSAO_IP DEFAULT '',
                IP_ULTIMO varchar(64) NOT NULL
                    CONSTRAINT DF_APP_SESSAO_IP_ULTIMO DEFAULT '',
                USER_AGENT nvarchar(500) NOT NULL
                    CONSTRAINT DF_APP_SESSAO_USER_AGENT DEFAULT '',
                ROTA_ENTRADA nvarchar(500) NOT NULL
                    CONSTRAINT DF_APP_SESSAO_ROTA DEFAULT '',
                ULTIMA_ROTA nvarchar(500) NOT NULL
                    CONSTRAINT DF_APP_SESSAO_ULTIMA_ROTA DEFAULT ''
            );
        END;

        IF NOT EXISTS (
            SELECT 1 FROM sys.indexes
            WHERE object_id = OBJECT_ID('dbo.APP_SESSAO_LOG')
              AND name = 'IX_APP_SESSAO_LOGIN_ENTRADA'
        )
            CREATE INDEX IX_APP_SESSAO_LOGIN_ENTRADA
                ON dbo.APP_SESSAO_LOG (LOGIN_TENTADO, ENTRADA_UTC DESC);

        IF NOT EXISTS (
            SELECT 1 FROM sys.indexes
            WHERE object_id = OBJECT_ID('dbo.APP_SESSAO_LOG')
              AND name = 'IX_APP_SESSAO_ATIVAS'
        )
            CREATE INDEX IX_APP_SESSAO_ATIVAS
                ON dbo.APP_SESSAO_LOG (SUCESSO, SAIDA_UTC, ULTIMA_ATIVIDADE_UTC DESC);

        IF OBJECT_ID('dbo.TURNOVER_HORAS_LOG', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.TURNOVER_HORAS_LOG (
                TURNOVERLOGSTAMP varchar(25) NOT NULL
                    CONSTRAINT PK_TURNOVER_HORAS_LOG PRIMARY KEY,
                RSSTAMP varchar(25) NOT NULL
                    CONSTRAINT DF_TURNOVER_LOG_RSSTAMP DEFAULT '',
                RESERVA varchar(80) NOT NULL
                    CONSTRAINT DF_TURNOVER_LOG_RESERVA DEFAULT '',
                ALOJAMENTO nvarchar(120) NOT NULL
                    CONSTRAINT DF_TURNOVER_LOG_ALOJAMENTO DEFAULT '',
                TIPO varchar(10) NOT NULL,
                DATA_MOVIMENTO date NULL,
                HORA_ANTERIOR varchar(5) NOT NULL
                    CONSTRAINT DF_TURNOVER_LOG_HORA_ANT DEFAULT '',
                HORA_NOVA varchar(5) NOT NULL
                    CONSTRAINT DF_TURNOVER_LOG_HORA_NOVA DEFAULT '',
                ACAO varchar(20) NOT NULL
                    CONSTRAINT DF_TURNOVER_LOG_ACAO DEFAULT '',
                UTILIZADOR varchar(100) NOT NULL
                    CONSTRAINT DF_TURNOVER_LOG_UTILIZADOR DEFAULT '',
                USSTAMP varchar(25) NOT NULL
                    CONSTRAINT DF_TURNOVER_LOG_USSTAMP DEFAULT '',
                NOME nvarchar(120) NOT NULL
                    CONSTRAINT DF_TURNOVER_LOG_NOME DEFAULT '',
                FEID int NULL,
                IP varchar(64) NOT NULL
                    CONSTRAINT DF_TURNOVER_LOG_IP DEFAULT '',
                USER_AGENT nvarchar(500) NOT NULL
                    CONSTRAINT DF_TURNOVER_LOG_USER_AGENT DEFAULT '',
                REQUEST_PATH nvarchar(500) NOT NULL
                    CONSTRAINT DF_TURNOVER_LOG_PATH DEFAULT '',
                DTCRI_UTC datetime2(3) NOT NULL
                    CONSTRAINT DF_TURNOVER_LOG_DTCRI DEFAULT SYSUTCDATETIME(),
                CONSTRAINT CK_TURNOVER_LOG_TIPO CHECK (TIPO IN ('CHECKIN', 'CHECKOUT'))
            );
        END;

        IF NOT EXISTS (
            SELECT 1 FROM sys.indexes
            WHERE object_id = OBJECT_ID('dbo.TURNOVER_HORAS_LOG')
              AND name = 'IX_TURNOVER_LOG_RESERVA'
        )
            CREATE INDEX IX_TURNOVER_LOG_RESERVA
                ON dbo.TURNOVER_HORAS_LOG (RSSTAMP, DTCRI_UTC DESC);

        IF NOT EXISTS (
            SELECT 1 FROM sys.indexes
            WHERE object_id = OBJECT_ID('dbo.TURNOVER_HORAS_LOG')
              AND name = 'IX_TURNOVER_LOG_UTILIZADOR'
        )
            CREATE INDEX IX_TURNOVER_LOG_UTILIZADOR
                ON dbo.TURNOVER_HORAS_LOG (UTILIZADOR, DTCRI_UTC DESC);
    """))


def create_session_log(
    db_session,
    *,
    login_attempted: str,
    userstamp: str = '',
    name: str = '',
    feid: int | None = None,
    success: bool,
    reason: str = '',
    ip: str = '',
    user_agent: str = '',
    request_path: str = '',
) -> str:
    stamp = _new_stamp()
    db_session.execute(text("""
        INSERT INTO dbo.APP_SESSAO_LOG (
            APPSESSAOSTAMP, LOGIN_TENTADO, USSTAMP, NOME, FEID,
            SUCESSO, MOTIVO, ULTIMA_ATIVIDADE_UTC,
            IP_ENTRADA, IP_ULTIMO, USER_AGENT, ROTA_ENTRADA, ULTIMA_ROTA
        ) VALUES (
            :stamp, :login, :usstamp, :nome, :feid,
            :sucesso, :motivo,
            CASE WHEN :sucesso = 1 THEN SYSUTCDATETIME() ELSE NULL END,
            :ip, :ip, :user_agent, :request_path, :request_path
        )
    """), {
        'stamp': stamp,
        'login': str(login_attempted or '').strip()[:100],
        'usstamp': str(userstamp or '').strip()[:25],
        'nome': str(name or '').strip()[:120],
        'feid': int(feid) if feid not in (None, '') else None,
        'sucesso': 1 if success else 0,
        'motivo': str(reason or '').strip()[:60],
        'ip': str(ip or '').strip()[:64],
        'user_agent': str(user_agent or '').strip()[:500],
        'request_path': str(request_path or '').strip()[:500],
    })
    return stamp


def touch_session_log(db_session, session_stamp: str, *, ip: str = '', request_path: str = '') -> bool:
    result = db_session.execute(text("""
        UPDATE dbo.APP_SESSAO_LOG
           SET ULTIMA_ATIVIDADE_UTC = SYSUTCDATETIME(),
               IP_ULTIMO = :ip,
               ULTIMA_ROTA = :request_path
         WHERE APPSESSAOSTAMP = :stamp
           AND SUCESSO = 1
           AND SAIDA_UTC IS NULL
    """), {
        'stamp': str(session_stamp or '').strip()[:25],
        'ip': str(ip or '').strip()[:64],
        'request_path': str(request_path or '').strip()[:500],
    })
    return bool((result.rowcount or 0) > 0)


def close_session_log(
    db_session,
    session_stamp: str,
    *,
    exit_type: str = 'LOGOUT',
    ip: str = '',
    request_path: str = '',
) -> bool:
    result = db_session.execute(text("""
        UPDATE dbo.APP_SESSAO_LOG
           SET ULTIMA_ATIVIDADE_UTC = SYSUTCDATETIME(),
               SAIDA_UTC = SYSUTCDATETIME(),
               SAIDA_TIPO = :exit_type,
               IP_ULTIMO = :ip,
               ULTIMA_ROTA = :request_path
         WHERE APPSESSAOSTAMP = :stamp
           AND SUCESSO = 1
           AND SAIDA_UTC IS NULL
    """), {
        'stamp': str(session_stamp or '').strip()[:25],
        'exit_type': str(exit_type or 'LOGOUT').strip().upper()[:30],
        'ip': str(ip or '').strip()[:64],
        'request_path': str(request_path or '').strip()[:500],
    })
    return bool((result.rowcount or 0) > 0)


def turnover_time_action(previous: str, current: str) -> str:
    before = str(previous or '').strip()
    after = str(current or '').strip()
    if before == after:
        return 'SEM_ALTERACAO'
    if not before and after:
        return 'CRIAR'
    if before and not after:
        return 'REMOVER'
    return 'ALTERAR'


def create_turnover_time_log(
    db_session,
    *,
    reservation: Mapping[str, Any],
    time_type: str,
    previous_time: str,
    new_time: str,
    movement_date: Any = None,
    actor_login: str = '',
    actor_userstamp: str = '',
    actor_name: str = '',
    feid: int | None = None,
    ip: str = '',
    user_agent: str = '',
    request_path: str = '',
) -> str:
    stamp = _new_stamp()
    db_session.execute(text("""
        INSERT INTO dbo.TURNOVER_HORAS_LOG (
            TURNOVERLOGSTAMP, RSSTAMP, RESERVA, ALOJAMENTO, TIPO,
            DATA_MOVIMENTO, HORA_ANTERIOR, HORA_NOVA, ACAO,
            UTILIZADOR, USSTAMP, NOME, FEID, IP, USER_AGENT, REQUEST_PATH
        ) VALUES (
            :stamp, :rsstamp, :reserva, :alojamento, :tipo,
            :data_movimento, :hora_anterior, :hora_nova, :acao,
            :utilizador, :usstamp, :nome, :feid, :ip, :user_agent, :request_path
        )
    """), {
        'stamp': stamp,
        'rsstamp': str(reservation.get('RSSTAMP') or '').strip()[:25],
        'reserva': str(reservation.get('RESERVA') or '').strip()[:80],
        'alojamento': str(reservation.get('ALOJAMENTO') or '').strip()[:120],
        'tipo': str(time_type or '').strip().upper()[:10],
        'data_movimento': movement_date,
        'hora_anterior': str(previous_time or '').strip()[:5],
        'hora_nova': str(new_time or '').strip()[:5],
        'acao': turnover_time_action(previous_time, new_time),
        'utilizador': str(actor_login or '').strip()[:100],
        'usstamp': str(actor_userstamp or '').strip()[:25],
        'nome': str(actor_name or '').strip()[:120],
        'feid': int(feid) if feid not in (None, '') else None,
        'ip': str(ip or '').strip()[:64],
        'user_agent': str(user_agent or '').strip()[:500],
        'request_path': str(request_path or '').strip()[:500],
    })
    return stamp
