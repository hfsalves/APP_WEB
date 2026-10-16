from __future__ import annotations

import calendar
import uuid
from datetime import date, datetime, time, timedelta
from typing import Any

from sqlalchemy import text

from models import db
from services.colaborador_despesas_service import get_colaborador_context


MONTH_NAMES_FR = (
    'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
    'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre',
)

WEEKDAY_NAMES_FR = (
    'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche',
)


def _truthy(value: Any) -> bool:
    return value is True or value == 1 or str(value or '').strip().lower() in {'1', 'true', 'yes'}


def ponto_user_allowed(user: Any) -> bool:
    """Only users enabled in US.PONTO and administrators can use time tracking."""
    return _truthy(getattr(user, 'ADMIN', False)) or _truthy(getattr(user, 'PONTO', False))


def _require_ponto_user(user: Any) -> None:
    if not ponto_user_allowed(user):
        raise ValueError('Votre compte n’est pas autorisé à utiliser le pointage.')


def _stamp() -> str:
    return uuid.uuid4().hex.upper()[:25]


def _day(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value or '').strip())
    except ValueError as exc:
        raise ValueError('Date de pointage invalide.') from exc


def _year(value: Any) -> int:
    try:
        selected = int(value or date.today().year)
    except (TypeError, ValueError) as exc:
        raise ValueError('Année invalide.') from exc
    if not 2000 <= selected <= 2100:
        raise ValueError('Année invalide.')
    return selected


def _month(value: Any) -> int:
    try:
        selected = int(value or date.today().month)
    except (TypeError, ValueError) as exc:
        raise ValueError('Mois invalide.') from exc
    if not 1 <= selected <= 12:
        raise ValueError('Mois invalide.')
    return selected


def _clock(value: Any, field_label: str) -> time:
    if isinstance(value, time):
        return value.replace(second=0, microsecond=0)
    raw = str(value or '').strip()
    try:
        return datetime.strptime(raw, '%H:%M').time()
    except ValueError as exc:
        raise ValueError(f'{field_label} est invalide.') from exc


def _clock_text(value: Any) -> str:
    if not value:
        return ''
    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds())
        return f'{(total_seconds // 3600) % 24:02d}:{(total_seconds // 60) % 60:02d}'
    if isinstance(value, time):
        return value.strftime('%H:%M')
    raw = str(value).strip()
    return raw[:5] if raw else ''


def _clock_minutes(value: time) -> int:
    return value.hour * 60 + value.minute


def _duration_text(minutes: int) -> str:
    safe_minutes = max(0, int(minutes or 0))
    hours, remainder = divmod(safe_minutes, 60)
    return f'{hours:02d}:{remainder:02d}'


def _is_editable_day(record_day: date, today: date | None = None) -> tuple[bool, str]:
    """Current month is open; preceding month remains editable through day 3."""
    current_day = today or date.today()
    if record_day > current_day:
        return False, 'Il n’est pas possible de saisir une date future.'
    if (record_day.year, record_day.month) == (current_day.year, current_day.month):
        return True, ''
    previous_month_end = current_day.replace(day=1) - timedelta(days=1)
    if (
        (record_day.year, record_day.month) == (previous_month_end.year, previous_month_end.month)
        and current_day.day <= 3
    ):
        return True, ''
    return False, 'Cette période est clôturée. Les pointages du mois précédent sont modifiables jusqu’au 3 du mois suivant.'


def ensure_ponto_schema() -> None:
    """Idempotent fallback for environments where the SQL migration was not run."""
    db.session.execute(text("""
        IF OBJECT_ID('dbo.COLAB_PONTO_REGISTO', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.COLAB_PONTO_REGISTO (
                PONTOSTAMP varchar(25) NOT NULL CONSTRAINT PK_COLAB_PONTO_REGISTO PRIMARY KEY,
                PENO int NOT NULL,
                PEFEID int NOT NULL CONSTRAINT DF_COLAB_PONTO_PEFEID DEFAULT 0,
                USSTAMP varchar(25) NOT NULL CONSTRAINT DF_COLAB_PONTO_USSTAMP DEFAULT '',
                LOGIN varchar(60) NOT NULL CONSTRAINT DF_COLAB_PONTO_LOGIN DEFAULT '',
                DATA_REGISTO date NOT NULL,
                HORA_ENTRADA time(0) NOT NULL,
                HORA_SAIDA time(0) NOT NULL,
                INTERVALO_ALMOCO_MIN smallint NOT NULL CONSTRAINT DF_COLAB_PONTO_INTERVALO DEFAULT 60,
                OBSERVACOES nvarchar(1000) NOT NULL CONSTRAINT DF_COLAB_PONTO_OBS DEFAULT N'',
                DTCRI datetime NOT NULL CONSTRAINT DF_COLAB_PONTO_DTCRI DEFAULT GETDATE(),
                DTALT datetime NULL,
                USERCRIACAO varchar(60) NOT NULL CONSTRAINT DF_COLAB_PONTO_USERCRI DEFAULT '',
                USERALTERACAO varchar(60) NOT NULL CONSTRAINT DF_COLAB_PONTO_USERALT DEFAULT '',
                VERSION int NOT NULL CONSTRAINT DF_COLAB_PONTO_VERSION DEFAULT 1,
                CONSTRAINT UQ_COLAB_PONTO_COLAB_DIA UNIQUE (PENO, PEFEID, DATA_REGISTO),
                CONSTRAINT CK_COLAB_PONTO_INTERVALO CHECK (INTERVALO_ALMOCO_MIN BETWEEN 0 AND 300),
                CONSTRAINT CK_COLAB_PONTO_HORAS CHECK (HORA_SAIDA > HORA_ENTRADA),
                CONSTRAINT CK_COLAB_PONTO_DURACAO CHECK (DATEDIFF(MINUTE, HORA_ENTRADA, HORA_SAIDA) > INTERVALO_ALMOCO_MIN)
            );
            CREATE INDEX IX_COLAB_PONTO_DIA ON dbo.COLAB_PONTO_REGISTO (PEFEID, DATA_REGISTO, PENO);
        END
    """))
    db.session.execute(text("""
        IF OBJECT_ID('dbo.COLAB_PONTO_HISTORICO', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.COLAB_PONTO_HISTORICO (
                HISTORICOSTAMP varchar(25) NOT NULL CONSTRAINT PK_COLAB_PONTO_HISTORICO PRIMARY KEY,
                PONTOSTAMP varchar(25) NOT NULL,
                PENO int NOT NULL,
                PEFEID int NOT NULL CONSTRAINT DF_COLAB_PONTO_HIST_PEFEID DEFAULT 0,
                USSTAMP varchar(25) NOT NULL CONSTRAINT DF_COLAB_PONTO_HIST_USSTAMP DEFAULT '',
                LOGIN varchar(60) NOT NULL CONSTRAINT DF_COLAB_PONTO_HIST_LOGIN DEFAULT '',
                DATA_REGISTO date NOT NULL,
                HORA_ENTRADA time(0) NOT NULL,
                HORA_SAIDA time(0) NOT NULL,
                INTERVALO_ALMOCO_MIN smallint NOT NULL,
                OBSERVACOES nvarchar(1000) NOT NULL CONSTRAINT DF_COLAB_PONTO_HIST_OBS DEFAULT N'',
                ACAO varchar(10) NOT NULL,
                VERSAO int NOT NULL,
                DATA_ACAO datetime NOT NULL CONSTRAINT DF_COLAB_PONTO_HIST_DATA DEFAULT GETDATE(),
                UTILIZADOR_ACAO varchar(60) NOT NULL CONSTRAINT DF_COLAB_PONTO_HIST_USER DEFAULT '',
                CONSTRAINT UQ_COLAB_PONTO_HIST_VERSAO UNIQUE (PONTOSTAMP, VERSAO),
                CONSTRAINT CK_COLAB_PONTO_HIST_ACAO CHECK (ACAO IN ('CREATE', 'UPDATE'))
            );
            CREATE INDEX IX_COLAB_PONTO_HIST_REGISTO
                ON dbo.COLAB_PONTO_HISTORICO (PENO, PEFEID, DATA_REGISTO, VERSAO);
        END
    """))
    db.session.commit()


def _employee(user: Any) -> dict[str, Any]:
    employee = get_colaborador_context(user)
    if not employee.get('peno') or not employee.get('pefeid'):
        raise ValueError('La fiche collaborateur est incomplète.')
    return employee


def get_daily_record(user: Any, value: Any = None) -> dict[str, Any]:
    _require_ponto_user(user)
    ensure_ponto_schema()
    employee = _employee(user)
    record_day = _day(value or date.today())
    row = db.session.execute(text("""
        SELECT HORA_ENTRADA, HORA_SAIDA, INTERVALO_ALMOCO_MIN, OBSERVACOES, VERSION
        FROM dbo.COLAB_PONTO_REGISTO
        WHERE PENO = :peno AND PEFEID = :pefeid AND DATA_REGISTO = :record_day
    """), {
        'peno': employee['peno'],
        'pefeid': employee['pefeid'],
        'record_day': record_day,
    }).mappings().first() or {}

    entry_text = _clock_text(row.get('HORA_ENTRADA'))
    exit_text = _clock_text(row.get('HORA_SAIDA'))
    lunch_minutes = int(row.get('INTERVALO_ALMOCO_MIN') or 0) if row else 60
    worked_minutes = 0
    if entry_text and exit_text:
        entry = _clock(entry_text, 'L’heure d’entrée')
        exit_time = _clock(exit_text, 'L’heure de sortie')
        worked_minutes = max(0, _clock_minutes(exit_time) - _clock_minutes(entry) - lunch_minutes)

    current_day = date.today()
    editable, lock_reason = _is_editable_day(record_day, current_day)
    first_current_month = current_day.replace(day=1)
    first_editable_day = (
        (first_current_month - timedelta(days=1)).replace(day=1)
        if current_day.day <= 3 else first_current_month
    )
    return {
        'ok': True,
        'date': record_day.isoformat(),
        'today': current_day.isoformat(),
        'min_editable_date': first_editable_day.isoformat(),
        'editable': editable,
        'lock_reason': lock_reason,
        'colaborador': employee,
        'record': {
            'entry_time': entry_text,
            'exit_time': exit_text,
            'lunch_minutes': lunch_minutes,
            'lunch_duration': _duration_text(lunch_minutes),
            'worked_minutes': worked_minutes,
            'worked_duration': _duration_text(worked_minutes),
            'observations': str(row.get('OBSERVACOES') or '').strip(),
            'version': int(row.get('VERSION') or 0),
        },
    }


def save_daily_record(user: Any, payload: dict[str, Any]) -> dict[str, Any]:
    _require_ponto_user(user)
    ensure_ponto_schema()
    employee = _employee(user)
    record_day = _day(payload.get('date'))
    editable, lock_reason = _is_editable_day(record_day)
    if not editable:
        raise ValueError(lock_reason)

    entry = _clock(payload.get('entry_time'), 'L’heure d’entrée')
    exit_time = _clock(payload.get('exit_time'), 'L’heure de sortie')
    try:
        lunch_minutes = int(payload.get('lunch_minutes'))
    except (TypeError, ValueError) as exc:
        raise ValueError('La durée de la pause déjeuner est invalide.') from exc
    if not 0 <= lunch_minutes <= 300:
        raise ValueError('La pause déjeuner doit être comprise entre 0 et 5 heures.')
    gross_minutes = _clock_minutes(exit_time) - _clock_minutes(entry)
    if gross_minutes <= 0:
        raise ValueError('L’heure de sortie doit être postérieure à l’heure d’entrée.')
    if gross_minutes <= lunch_minutes:
        raise ValueError('La pause déjeuner doit être inférieure à la durée de présence.')
    observations = str(payload.get('observations') or '').strip()
    if len(observations) > 1000:
        raise ValueError('Les observations ne peuvent pas dépasser 1 000 caractères.')

    login = str(getattr(user, 'LOGIN', '') or '').strip()
    saved = db.session.execute(text("""
        MERGE dbo.COLAB_PONTO_REGISTO AS target
        USING (SELECT :peno AS PENO, :pefeid AS PEFEID, :record_day AS DATA_REGISTO) AS source
        ON target.PENO = source.PENO
           AND target.PEFEID = source.PEFEID
           AND target.DATA_REGISTO = source.DATA_REGISTO
        WHEN MATCHED THEN UPDATE SET
            HORA_ENTRADA = :entry_time,
            HORA_SAIDA = :exit_time,
            INTERVALO_ALMOCO_MIN = :lunch_minutes,
            OBSERVACOES = :observations,
            DTALT = GETDATE(),
            USERALTERACAO = :user,
            VERSION = target.VERSION + 1
        WHEN NOT MATCHED THEN INSERT
            (PONTOSTAMP, PENO, PEFEID, USSTAMP, LOGIN, DATA_REGISTO,
             HORA_ENTRADA, HORA_SAIDA, INTERVALO_ALMOCO_MIN, OBSERVACOES,
             USERCRIACAO, USERALTERACAO)
        VALUES
            (:stamp, :peno, :pefeid, :userstamp, :login, :record_day,
             :entry_time, :exit_time, :lunch_minutes, :observations,
             :user, :user)
        OUTPUT inserted.PONTOSTAMP, inserted.VERSION,
               CASE WHEN deleted.PONTOSTAMP IS NULL THEN 'CREATE' ELSE 'UPDATE' END;
    """), {
        'stamp': _stamp(),
        'peno': employee['peno'],
        'pefeid': employee['pefeid'],
        'userstamp': employee['userstamp'],
        'login': login,
        'record_day': record_day,
        'entry_time': entry,
        'exit_time': exit_time,
        'lunch_minutes': lunch_minutes,
        'observations': observations,
        'user': login,
    }).first()
    if not saved:
        raise RuntimeError('Le pointage n’a pas été enregistré.')
    db.session.execute(text("""
        INSERT INTO dbo.COLAB_PONTO_HISTORICO
        (
            HISTORICOSTAMP, PONTOSTAMP, PENO, PEFEID, USSTAMP, LOGIN,
            DATA_REGISTO, HORA_ENTRADA, HORA_SAIDA, INTERVALO_ALMOCO_MIN,
            OBSERVACOES, ACAO, VERSAO, UTILIZADOR_ACAO
        )
        VALUES
        (
            :history_stamp, :ponto_stamp, :peno, :pefeid, :userstamp, :login,
            :record_day, :entry_time, :exit_time, :lunch_minutes,
            :observations, :action, :version, :user
        )
    """), {
        'history_stamp': _stamp(),
        'ponto_stamp': str(saved[0]),
        'peno': employee['peno'],
        'pefeid': employee['pefeid'],
        'userstamp': employee['userstamp'],
        'login': login,
        'record_day': record_day,
        'entry_time': entry,
        'exit_time': exit_time,
        'lunch_minutes': lunch_minutes,
        'observations': observations,
        'action': str(saved[2]),
        'version': int(saved[1]),
        'user': login,
    })
    db.session.commit()
    return get_daily_record(user, record_day)


def get_month_summary(user: Any, year: Any = None, month: Any = None) -> dict[str, Any]:
    _require_ponto_user(user)
    ensure_ponto_schema()
    employee = _employee(user)
    selected_year = _year(year)
    selected_month = _month(month)
    start_day = date(selected_year, selected_month, 1)
    end_day = (
        date(selected_year + 1, 1, 1)
        if selected_month == 12
        else date(selected_year, selected_month + 1, 1)
    )
    records = {
        _day(row.get('DATA_REGISTO')): row
        for row in db.session.execute(text("""
            SELECT DATA_REGISTO, HORA_ENTRADA, HORA_SAIDA,
                   INTERVALO_ALMOCO_MIN, OBSERVACOES
            FROM dbo.COLAB_PONTO_REGISTO
            WHERE PENO = :peno AND PEFEID = :pefeid
              AND DATA_REGISTO >= :start_day AND DATA_REGISTO < :end_day
            ORDER BY DATA_REGISTO
        """), {
            'peno': employee['peno'],
            'pefeid': employee['pefeid'],
            'start_day': start_day,
            'end_day': end_day,
        }).mappings().all()
    }

    rows: list[dict[str, Any]] = []
    recorded_days = 0
    worked_minutes_total = 0
    lunch_minutes_total = 0
    for day_number in range(1, calendar.monthrange(selected_year, selected_month)[1] + 1):
        record_day = date(selected_year, selected_month, day_number)
        record = records.get(record_day) or {}
        entry_text = _clock_text(record.get('HORA_ENTRADA'))
        exit_text = _clock_text(record.get('HORA_SAIDA'))
        lunch_minutes = int(record.get('INTERVALO_ALMOCO_MIN') or 0) if record else 0
        worked_minutes = 0
        if entry_text and exit_text:
            entry = _clock(entry_text, 'L’heure d’entrée')
            exit_time = _clock(exit_text, 'L’heure de sortie')
            worked_minutes = max(0, _clock_minutes(exit_time) - _clock_minutes(entry) - lunch_minutes)
            recorded_days += 1
            worked_minutes_total += worked_minutes
            lunch_minutes_total += lunch_minutes
        editable, _reason = _is_editable_day(record_day)
        rows.append({
            'date': record_day.isoformat(),
            'day_label': record_day.strftime('%d/%m'),
            'weekday': WEEKDAY_NAMES_FR[record_day.weekday()],
            'is_weekend': record_day.weekday() >= 5,
            'entry_time': entry_text,
            'exit_time': exit_text,
            'lunch_minutes': lunch_minutes if record else '',
            'lunch_duration': _duration_text(lunch_minutes) if record else '',
            'worked_minutes': worked_minutes if record else '',
            'worked_duration': _duration_text(worked_minutes) if record else '',
            'observations': str(record.get('OBSERVACOES') or '').strip(),
            'editable': editable,
        })

    return {
        'ok': True,
        'year': selected_year,
        'month': selected_month,
        'month_label': MONTH_NAMES_FR[selected_month - 1],
        'colaborador': employee,
        'rows': rows,
        'totals': {
            'recorded_days': recorded_days,
            'worked_minutes': worked_minutes_total,
            'worked_duration': _duration_text(worked_minutes_total),
            'lunch_minutes': lunch_minutes_total,
            'lunch_duration': _duration_text(lunch_minutes_total),
        },
    }
