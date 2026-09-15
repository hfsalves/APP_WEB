from __future__ import annotations

import uuid
import calendar
import base64
import binascii
from io import BytesIO
from datetime import date, datetime, timedelta
from typing import Any

import pyodbc
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image as PdfImage, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import text

from models import db
from services.colaborador_despesas_service import _phc_conn_str, get_colaborador_context


ABSENCE_TYPES = {
    'WEEKLY_REST',
    'PAID_LEAVE',
    'CONVENTIONAL_LEAVE',
    'SICK_LEAVE',
    'PUBLIC_HOLIDAY',
    'UNEXCUSED_ABSENCE',
}

MONTH_NAMES_FR = (
    'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
    'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre',
)

DETAIL_COLUMNS = (
    ('work_fraction', 'Journée ou demi-journée travaillée'),
    ('WEEKLY_REST', 'Repos hebdomadaire'),
    ('PAID_LEAVE', 'Congés payés'),
    ('CONVENTIONAL_LEAVE', 'Congés conventionnels'),
    ('SICK_LEAVE', 'Absence pour maladie'),
    ('PUBLIC_HOLIDAY', 'Jours fériés chômés'),
    ('UNEXCUSED_ABSENCE', 'Absences non justifiées'),
)


def forfait_user_allowed(user: Any) -> bool:
    """Forfait users and administrators can use this module."""
    admin = getattr(user, 'ADMIN', False)
    if admin is True or admin == 1 or str(admin or '').strip().lower() in {'1', 'true', 'yes'}:
        return True
    value = getattr(user, 'FORFAIT', False)
    return value is True or value == 1 or str(value or '').strip().lower() in {'1', 'true', 'yes'}


def _require_forfait_user(user: Any) -> None:
    if not forfait_user_allowed(user):
        raise ValueError('Votre compte n’est pas autorisé à utiliser le suivi forfait-jours.')


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
        raise ValueError('Date de saisie invalide.') from exc


def _year(value: Any) -> int:
    try:
        selected = int(value or date.today().year)
    except (TypeError, ValueError):
        selected = date.today().year
    if not 2000 <= selected <= 2100:
        raise ValueError('Année invalide.')
    return selected


def _is_editable_day(record_day: date, today: date | None = None) -> tuple[bool, str]:
    """Current month is open; the preceding month remains editable through day 3."""
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
    return False, 'Cette période est clôturée. Les saisies du mois précédent sont modifiables jusqu’au 3 du mois suivant.'


def _previous_period(value: date) -> tuple[int, int]:
    previous = value.replace(day=1) - timedelta(days=1)
    return previous.year, previous.month


def required_signature_period(employee: dict[str, Any], today: date | None = None) -> tuple[int, int] | None:
    current_day = today or date.today()
    if current_day.day < 4 or not employee.get('peno') or not employee.get('pefeid'):
        return None
    year, month = _previous_period(current_day)
    signed = db.session.execute(text("""
        SELECT 1 FROM dbo.COLAB_FORFAIT_JOURS_ASSINATURA
        WHERE PENO = :peno AND PEFEID = :pefeid AND ANO = :year AND MES = :month
    """), {'peno': employee['peno'], 'pefeid': employee['pefeid'], 'year': year, 'month': month}).scalar()
    return None if signed else (year, month)


def ensure_forfait_jours_schema() -> None:
    """Idempotent fallback for environments where the SQL migration was not yet run."""
    db.session.execute(text("""
        IF OBJECT_ID('dbo.COLAB_FORFAIT_JOURS_REGISTO', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.COLAB_FORFAIT_JOURS_REGISTO (
                REGISTOSTAMP varchar(25) NOT NULL CONSTRAINT PK_COLAB_FORFAIT_JOURS_REGISTO PRIMARY KEY,
                PENO int NOT NULL,
                PEFEID int NOT NULL CONSTRAINT DF_COLAB_FORFAIT_JOURS_PEFEID DEFAULT 0,
                USSTAMP varchar(25) NOT NULL CONSTRAINT DF_COLAB_FORFAIT_JOURS_USSTAMP DEFAULT '',
                LOGIN varchar(60) NOT NULL CONSTRAINT DF_COLAB_FORFAIT_JOURS_LOGIN DEFAULT '',
                DATA_REGISTO date NOT NULL,
                FRACAO_TRABALHADA decimal(2,1) NOT NULL CONSTRAINT DF_COLAB_FORFAIT_JOURS_FRACAO DEFAULT 0,
                TIPO_AUSENCIA varchar(30) NOT NULL CONSTRAINT DF_COLAB_FORFAIT_JOURS_AUSENCIA DEFAULT '',
                OBSERVACOES nvarchar(1000) NOT NULL CONSTRAINT DF_COLAB_FORFAIT_JOURS_OBS DEFAULT N'',
                DTCRI datetime NOT NULL CONSTRAINT DF_COLAB_FORFAIT_JOURS_DTCRI DEFAULT GETDATE(),
                DTALT datetime NULL,
                USERCRIACAO varchar(60) NOT NULL CONSTRAINT DF_COLAB_FORFAIT_JOURS_USERCRI DEFAULT '',
                USERALTERACAO varchar(60) NOT NULL CONSTRAINT DF_COLAB_FORFAIT_JOURS_USERALT DEFAULT '',
                VERSION int NOT NULL CONSTRAINT DF_COLAB_FORFAIT_JOURS_VERSION DEFAULT 1,
                CONSTRAINT UQ_COLAB_FORFAIT_JOURS_COLAB_DIA UNIQUE (PENO, PEFEID, DATA_REGISTO),
                CONSTRAINT CK_COLAB_FORFAIT_JOURS_FRACAO CHECK (FRACAO_TRABALHADA IN (0, 0.5, 1)),
                CONSTRAINT CK_COLAB_FORFAIT_JOURS_TIPO CHECK (TIPO_AUSENCIA IN ('', 'WEEKLY_REST', 'PAID_LEAVE', 'CONVENTIONAL_LEAVE', 'SICK_LEAVE', 'PUBLIC_HOLIDAY', 'UNEXCUSED_ABSENCE')),
                CONSTRAINT CK_COLAB_FORFAIT_JOURS_DIA CHECK ((FRACAO_TRABALHADA IN (0.5, 1) AND TIPO_AUSENCIA = '') OR (FRACAO_TRABALHADA = 0 AND TIPO_AUSENCIA <> ''))
            );
            CREATE INDEX IX_COLAB_FORFAIT_JOURS_DIA ON dbo.COLAB_FORFAIT_JOURS_REGISTO (PEFEID, DATA_REGISTO, PENO);
        END
    """))
    db.session.execute(text("""
        IF OBJECT_ID('dbo.COLAB_FORFAIT_JOURS_ASSINATURA', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.COLAB_FORFAIT_JOURS_ASSINATURA (
                ASSINATURASTAMP varchar(25) NOT NULL CONSTRAINT PK_COLAB_FORFAIT_JOURS_ASSINATURA PRIMARY KEY,
                PENO int NOT NULL, PEFEID int NOT NULL CONSTRAINT DF_COLAB_FORFAIT_ASSINATURA_PEFEID DEFAULT 0,
                USSTAMP varchar(25) NOT NULL CONSTRAINT DF_COLAB_FORFAIT_ASSINATURA_USSTAMP DEFAULT '', LOGIN varchar(60) NOT NULL CONSTRAINT DF_COLAB_FORFAIT_ASSINATURA_LOGIN DEFAULT '',
                ANO smallint NOT NULL, MES tinyint NOT NULL, ASSINATURA_PNG varbinary(max) NOT NULL, PDF_ASSINADO varbinary(max) NOT NULL,
                NOME_FICHEIRO varchar(160) NOT NULL CONSTRAINT DF_COLAB_FORFAIT_ASSINATURA_FICHEIRO DEFAULT '', DTASSINATURA datetime NOT NULL CONSTRAINT DF_COLAB_FORFAIT_ASSINATURA_DATA DEFAULT GETDATE(),
                CONSTRAINT UQ_COLAB_FORFAIT_ASSINATURA_PERIODO UNIQUE (PENO, PEFEID, ANO, MES), CONSTRAINT CK_COLAB_FORFAIT_ASSINATURA_MES CHECK (MES BETWEEN 1 AND 12)
            );
            CREATE INDEX IX_COLAB_FORFAIT_JOURS_ASSINATURA_COLAB ON dbo.COLAB_FORFAIT_JOURS_ASSINATURA (PENO, PEFEID, ANO DESC, MES DESC);
        END
    """))
    db.session.commit()


def get_daily_record(user: Any, value: Any = None) -> dict[str, Any]:
    _require_forfait_user(user)
    ensure_forfait_jours_schema()
    employee = get_colaborador_context(user)
    record_day = _day(value or date.today())
    record = {'work_fraction': None, 'absence_type': '', 'observations': '', 'version': 0}
    if employee['peno']:
        row = db.session.execute(text("""
            SELECT FRACAO_TRABALHADA, TIPO_AUSENCIA, OBSERVACOES, VERSION
            FROM dbo.COLAB_FORFAIT_JOURS_REGISTO
            WHERE PENO = :peno AND PEFEID = :pefeid AND DATA_REGISTO = :record_day
        """), {'peno': employee['peno'], 'pefeid': employee['pefeid'], 'record_day': record_day}).mappings().first()
        if row:
            record = {
                'work_fraction': float(row.get('FRACAO_TRABALHADA') or 0) or None,
                'absence_type': str(row.get('TIPO_AUSENCIA') or ''),
                'observations': str(row.get('OBSERVACOES') or ''),
                'version': int(row.get('VERSION') or 1),
            }
    current_day = date.today()
    editable, lock_reason = _is_editable_day(record_day, current_day)
    first_current_month = current_day.replace(day=1)
    first_editable_day = (
        (first_current_month - timedelta(days=1)).replace(day=1)
        if current_day.day <= 3 else first_current_month
    )
    return {
        'ok': True, 'date': record_day.isoformat(), 'today': current_day.isoformat(),
        'min_editable_date': first_editable_day.isoformat(),
        'editable': editable, 'lock_reason': lock_reason, 'colaborador': employee, 'record': record,
        'signature_required': required_signature_period(employee, current_day),
    }


def save_daily_record(user: Any, payload: dict[str, Any]) -> dict[str, Any]:
    _require_forfait_user(user)
    ensure_forfait_jours_schema()
    employee = get_colaborador_context(user)
    if not employee.get('peno') or not employee.get('pefeid'):
        raise ValueError('La fiche collaborateur est incomplète.')
    record_day = _day(payload.get('date'))
    editable, lock_reason = _is_editable_day(record_day)
    if not editable:
        raise ValueError(lock_reason)
    signature_period = required_signature_period(employee)
    current_day = date.today()
    if signature_period and (record_day.year, record_day.month) == (current_day.year, current_day.month):
        raise ValueError('Vous devez signer le document du mois précédent avant de saisir le mois en cours.')
    work_fraction = payload.get('work_fraction')
    try:
        work_fraction = float(work_fraction) if work_fraction not in (None, '') else 0
    except (TypeError, ValueError) as exc:
        raise ValueError('Sélectionnez une journée ou une demi-journée travaillée.') from exc
    absence_type = str(payload.get('absence_type') or '').strip().upper()
    observations = str(payload.get('observations') or '').strip()
    if len(observations) > 1000:
        raise ValueError('Les observations ne peuvent pas dépasser 1 000 caractères.')
    if work_fraction not in (0, 0.5, 1):
        raise ValueError('Sélectionnez une journée ou une demi-journée travaillée.')
    if work_fraction and absence_type:
        raise ValueError('Une journée travaillée ne peut pas avoir de motif d’absence.')
    if not work_fraction and absence_type not in ABSENCE_TYPES:
        raise ValueError('Sélectionnez le motif de la journée non travaillée.')
    login = str(getattr(user, 'LOGIN', '') or '').strip()
    params = {
        'stamp': _stamp(), 'peno': employee['peno'], 'pefeid': employee['pefeid'],
        'userstamp': employee['userstamp'], 'login': login, 'record_day': record_day,
        'work_fraction': work_fraction, 'absence_type': absence_type,
        'observations': observations, 'user': login,
    }
    db.session.execute(text("""
        MERGE dbo.COLAB_FORFAIT_JOURS_REGISTO AS target
        USING (SELECT :peno AS PENO, :pefeid AS PEFEID, :record_day AS DATA_REGISTO) AS source
        ON target.PENO = source.PENO AND target.PEFEID = source.PEFEID AND target.DATA_REGISTO = source.DATA_REGISTO
        WHEN MATCHED THEN UPDATE SET FRACAO_TRABALHADA = :work_fraction, TIPO_AUSENCIA = :absence_type,
          OBSERVACOES = :observations, DTALT = GETDATE(), USERALTERACAO = :user, VERSION = target.VERSION + 1
        WHEN NOT MATCHED THEN INSERT (REGISTOSTAMP, PENO, PEFEID, USSTAMP, LOGIN, DATA_REGISTO, FRACAO_TRABALHADA, TIPO_AUSENCIA, OBSERVACOES, USERCRIACAO, USERALTERACAO)
          VALUES (:stamp, :peno, :pefeid, :userstamp, :login, :record_day, :work_fraction, :absence_type, :observations, :user, :user);
    """), params)
    db.session.commit()
    return get_daily_record(user, record_day)


def _year_rows(employee: dict[str, Any], selected_year: int) -> list[dict[str, Any]]:
    if not employee.get('peno') or not employee.get('pefeid'):
        return []
    return db.session.execute(text("""
        SELECT DATA_REGISTO, FRACAO_TRABALHADA, TIPO_AUSENCIA, OBSERVACOES
        FROM dbo.COLAB_FORFAIT_JOURS_REGISTO
        WHERE PENO = :peno AND PEFEID = :pefeid
          AND DATA_REGISTO >= :start_day AND DATA_REGISTO < :end_day
        ORDER BY DATA_REGISTO
    """), {
        'peno': employee['peno'], 'pefeid': employee['pefeid'],
        'start_day': date(selected_year, 1, 1), 'end_day': date(selected_year + 1, 1, 1),
    }).mappings().all()


def get_annual_summary(user: Any, year: Any = None) -> dict[str, Any]:
    _require_forfait_user(user)
    ensure_forfait_jours_schema()
    selected_year = _year(year)
    employee = get_colaborador_context(user)
    monthly = [{'month': index, 'label': label, 'worked_days': 0.0, 'absence_days': 0} for index, label in enumerate(MONTH_NAMES_FR, 1)]
    signed_months = {
        int(row.get('MES') or 0)
        for row in db.session.execute(text("""
            SELECT MES FROM dbo.COLAB_FORFAIT_JOURS_ASSINATURA
            WHERE PENO = :peno AND PEFEID = :pefeid AND ANO = :year
        """), {'peno': employee.get('peno') or 0, 'pefeid': employee.get('pefeid') or 0, 'year': selected_year}).mappings().all()
    }
    for row in _year_rows(employee, selected_year):
        record_day = _day(row.get('DATA_REGISTO'))
        item = monthly[record_day.month - 1]
        item['worked_days'] += float(row.get('FRACAO_TRABALHADA') or 0)
        if str(row.get('TIPO_AUSENCIA') or '').strip():
            item['absence_days'] += 1
    for item in monthly:
        item['worked_days'] = round(item['worked_days'], 1)
        item['signed'] = item['month'] in signed_months
    return {
        'ok': True, 'year': selected_year, 'colaborador': employee, 'months': monthly,
        'totals': {
            'worked_days': round(sum(item['worked_days'] for item in monthly), 1),
            'absence_days': sum(item['absence_days'] for item in monthly),
        },
    }


def get_month_detail(user: Any, year: Any, month: Any) -> dict[str, Any]:
    _require_forfait_user(user)
    ensure_forfait_jours_schema()
    selected_year = _year(year)
    try:
        selected_month = int(month)
    except (TypeError, ValueError) as exc:
        raise ValueError('Mois invalide.') from exc
    if not 1 <= selected_month <= 12:
        raise ValueError('Mois invalide.')
    employee = get_colaborador_context(user)
    signed = bool(db.session.execute(text("""
        SELECT 1 FROM dbo.COLAB_FORFAIT_JOURS_ASSINATURA
        WHERE PENO = :peno AND PEFEID = :pefeid AND ANO = :year AND MES = :month
    """), {'peno': employee.get('peno') or 0, 'pefeid': employee.get('pefeid') or 0, 'year': selected_year, 'month': selected_month}).scalar())
    entries = {
        _day(row.get('DATA_REGISTO')): row
        for row in _year_rows(employee, selected_year)
        if _day(row.get('DATA_REGISTO')).month == selected_month
    }
    rows: list[dict[str, Any]] = []
    worked_days = 0.0
    absence_days = 0
    for day_num in range(1, calendar.monthrange(selected_year, selected_month)[1] + 1):
        record_day = date(selected_year, selected_month, day_num)
        entry = entries.get(record_day) or {}
        fraction = float(entry.get('FRACAO_TRABALHADA') or 0)
        absence_type = str(entry.get('TIPO_AUSENCIA') or '').strip()
        worked_days += fraction
        absence_days += int(bool(absence_type))
        rows.append({
            'date': record_day.isoformat(), 'day_label': record_day.strftime('%d/%m'),
            'work_fraction': fraction or '', 'absence_type': absence_type,
            'observations': str(entry.get('OBSERVACOES') or '').strip(),
        })
    return {
        'ok': True, 'year': selected_year, 'month': selected_month,
        'month_label': MONTH_NAMES_FR[selected_month - 1], 'columns': DETAIL_COLUMNS,
        'rows': rows, 'signed': signed, 'totals': {'worked_days': round(worked_days, 1), 'absence_days': absence_days},
    }


def _employee_pdf_profile(employee: dict[str, Any]) -> dict[str, str]:
    peno = int(employee.get('peno') or 0)
    phc_db = str(employee.get('phc_db') or '').strip()
    if not peno or not phc_db:
        raise ValueError('La fiche collaborateur est incomplète.')
    try:
        with pyodbc.connect(_phc_conn_str(phc_db, str(employee.get('phc_server') or '').strip()), timeout=15) as conn:
            row = conn.cursor().execute("""
                SELECT TOP 1
                    LTRIM(RTRIM(ISNULL(NOME, ''))) AS NOME,
                    LTRIM(RTRIM(ISNULL(CCPROFISS, ''))) AS FONCTION,
                    LTRIM(RTRIM(ISNULL(CCATEGORIA, ''))) AS CLASSIFICATION
                FROM dbo.PE
                WHERE NO = ?
            """, peno).fetchone()
    except pyodbc.Error as exc:
        raise ValueError('Impossible de lire les données du collaborateur dans le PHC.') from exc
    if not row:
        raise ValueError('Collaborateur introuvable dans la table PE du PHC.')
    return {
        'name': str(row.NOME or employee.get('penome') or '').strip(),
        'function': str(row.FONCTION or '').strip(),
        'classification': str(row.CLASSIFICATION or '').strip(),
    }


def _company_pdf_profile(employee: dict[str, Any]) -> dict[str, str]:
    row = db.session.execute(text("""
        SELECT TOP 1
            LTRIM(RTRIM(ISNULL(NOME, ''))) AS NOME,
            LTRIM(RTRIM(ISNULL(NOMEFISCAL, ''))) AS NOMEFISCAL,
            LTRIM(RTRIM(ISNULL(NIF, ''))) AS NIF,
            LTRIM(RTRIM(ISNULL(MORADA, ''))) AS MORADA,
            LTRIM(RTRIM(ISNULL(CODPOST, ''))) AS CODPOST,
            LTRIM(RTRIM(ISNULL(LOCAL, ''))) AS LOCAL
        FROM dbo.FE WHERE FEID = :feid
    """), {'feid': int(employee.get('feid') or employee.get('pefeid') or 0)}).mappings().first() or {}
    address = ' '.join(part for part in (str(row.get('MORADA') or '').strip(), str(row.get('CODPOST') or '').strip(), str(row.get('LOCAL') or '').strip()) if part)
    return {
        'name': str(row.get('NOMEFISCAL') or row.get('NOME') or employee.get('empresa') or '').strip(),
        'nif': str(row.get('NIF') or '').strip(), 'address': address,
    }


def build_month_pdf(user: Any, year: Any, month: Any, signature_png: bytes | None = None) -> tuple[bytes, str]:
    """Create the monthly forfait-jours control document in the format of the supplied sheet."""
    detail = get_month_detail(user, year, month)
    employee = get_colaborador_context(user)
    profile = _employee_pdf_profile(employee)
    company = _company_pdf_profile(employee)
    stream = BytesIO()
    document = SimpleDocTemplate(
        stream, pagesize=A4, leftMargin=8 * mm, rightMargin=8 * mm,
        topMargin=7 * mm, bottomMargin=10 * mm, title='Suivi mensuel forfait-jours',
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('ForfaitTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=10, leading=12, alignment=1, textColor=colors.HexColor('#162233'), spaceAfter=3)
    normal_style = ParagraphStyle('ForfaitNormal', parent=styles['BodyText'], fontName='Helvetica', fontSize=6.1, leading=7.1, textColor=colors.HexColor('#162233'))
    small_style = ParagraphStyle('ForfaitSmall', parent=normal_style, fontSize=5.2, leading=5.8, alignment=1)
    header_style = ParagraphStyle('ForfaitHeader', parent=small_style, fontName='Helvetica-Bold', textColor=colors.HexColor('#162233'))
    story = [Paragraph('DOCUMENT INDIVIDUEL DE SUIVI MENSUEL DE FORFAIT-JOURS', title_style)]
    company_line = company['name'] or '-'
    if company['nif']:
        company_line += f" - NIF {company['nif']}"
    story.append(Paragraph(f"<b>{company_line}</b>{('<br/>' + company['address']) if company['address'] else ''}", normal_style))
    story.append(Spacer(1, 2 * mm))
    info = [
        [Paragraph('<b>Salarié</b>', normal_style), Paragraph(profile['name'] or '-', normal_style), Paragraph('<b>Période</b>', normal_style), Paragraph(f"{detail['month_label']} {detail['year']}", normal_style)],
        [Paragraph('<b>Fonction</b>', normal_style), Paragraph(profile['function'] or '-', normal_style), Paragraph('<b>Total travaillé</b>', normal_style), Paragraph(f"{detail['totals']['worked_days']:.1f} jour(s)", normal_style)],
        [Paragraph('<b>Classification</b>', normal_style), Paragraph(profile['classification'] or '-', normal_style), Paragraph('<b>Absences</b>', normal_style), Paragraph(str(detail['totals']['absence_days']), normal_style)],
    ]
    info_table = Table(info, colWidths=[27 * mm, 73 * mm, 28 * mm, 55 * mm])
    info_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), .4, colors.HexColor('#D8E0EC')), ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F8FBFF')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#F8FBFF')), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3), ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.extend([info_table, Spacer(1, 2 * mm)])
    headings = ['Jour', 'Travail', 'Repos', 'CP', 'Conv.', 'Maladie', 'Férié', 'Non just.', 'Observations']
    table_data: list[list[Any]] = [[Paragraph(value, header_style) for value in headings]]
    for row in detail['rows']:
        cells: list[Any] = [Paragraph(row['day_label'], normal_style)]
        for key, _label in detail['columns']:
            mark = f"{float(row['work_fraction']):.1f}" if key == 'work_fraction' and row['work_fraction'] else ('X' if row['absence_type'] == key else '')
            cells.append(Paragraph(mark, small_style))
        observation = str(row['observations'] or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        cells.append(Paragraph((observation[:34] + ('...' if len(observation) > 34 else '')) or '', small_style))
        table_data.append(cells)
    # Keep the printable sheet balanced across short and long months, while
    # reserving enough room for *both* signature rows on the same A4 page.
    daily_row_height = 600 / len(detail['rows'])
    month_table = Table(
        table_data,
        colWidths=[13 * mm, 27 * mm, 17 * mm, 17 * mm, 19 * mm, 17 * mm, 17 * mm, 20 * mm, 47 * mm],
        rowHeights=[16] + [daily_row_height] * len(detail['rows']), repeatRows=1,
    )
    month_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), .35, colors.HexColor('#D8E0EC')), ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F8FBFF')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('ALIGN', (0, 1), (7, -1), 'CENTER'), ('LEFTPADDING', (0, 0), (-1, -1), 1.5), ('RIGHTPADDING', (0, 0), (-1, -1), 1.5), ('TOPPADDING', (0, 0), (-1, -1), 1.2), ('BOTTOMPADDING', (0, 0), (-1, -1), 1.2),
    ]))
    story.append(month_table)
    if signature_png:
        try:
            signature = PdfImage(BytesIO(signature_png), width=48 * mm, height=18 * mm, kind='proportional')
        except Exception as exc:
            raise ValueError('La signature fournie est invalide.') from exc
        signature_cell: Any = signature
        signature_date = f"Signé le {date.today().strftime('%d/%m/%Y')}"
    else:
        signature_cell = Paragraph('', normal_style)
        signature_date = 'Signature à compléter'
    signature_table = Table([
            [Paragraph('<b>Signature du salarié</b>', normal_style), signature_cell],
            [Paragraph(signature_date, normal_style), Paragraph(profile['name'] or '-', normal_style)],
        ], colWidths=[55 * mm, 139 * mm], rowHeights=[49, 12])
    signature_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), .4, colors.HexColor('#D8E0EC')), ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F8FBFF')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3), ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.extend([Spacer(1, 3 * mm), signature_table])
    def draw_footer(pdf_canvas, _document):
        pdf_canvas.saveState()
        pdf_canvas.setStrokeColor(colors.HexColor('#D8E0EC'))
        pdf_canvas.line(document.leftMargin, 7 * mm, A4[0] - document.rightMargin, 7 * mm)
        pdf_canvas.setFont('Helvetica', 5.5)
        pdf_canvas.setFillColor(colors.HexColor('#6C7A92'))
        pdf_canvas.drawString(document.leftMargin, 4 * mm, f"Forfait-jours - {detail['month_label']} {detail['year']}")
        pdf_canvas.drawRightString(A4[0] - document.rightMargin, 4 * mm, f"Page {pdf_canvas.getPageNumber()}")
        pdf_canvas.restoreState()
    document.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    filename = f"forfait-jours_{detail['year']}-{detail['month']:02d}_{int(employee.get('peno') or 0)}.pdf"
    return stream.getvalue(), filename


def signature_page_context(user: Any) -> dict[str, Any]:
    _require_forfait_user(user)
    ensure_forfait_jours_schema()
    employee = get_colaborador_context(user)
    period = required_signature_period(employee)
    if not period:
        return {'ok': True, 'required': False, 'colaborador': employee}
    year, month = period
    detail = get_month_detail(user, year, month)
    return {'ok': True, 'required': True, 'year': year, 'month': month, 'month_label': detail['month_label'], 'totals': detail['totals'], 'colaborador': employee}


def _decode_signature(value: Any) -> bytes:
    raw = str(value or '').strip()
    prefix = 'data:image/png;base64,'
    if not raw.startswith(prefix):
        raise ValueError('Veuillez signer dans le cadre prévu.')
    try:
        image = base64.b64decode(raw[len(prefix):], validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError('La signature est invalide.') from exc
    if not 200 <= len(image) <= 1_500_000 or not image.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('La signature est invalide.')
    return image


def sign_previous_month(user: Any, payload: dict[str, Any]) -> dict[str, Any]:
    _require_forfait_user(user)
    ensure_forfait_jours_schema()
    employee = get_colaborador_context(user)
    period = required_signature_period(employee)
    if not period:
        raise ValueError('Aucun document mensuel ne requiert actuellement votre signature.')
    year, month = period
    try:
        requested_year, requested_month = int(payload.get('year')), int(payload.get('month'))
    except (TypeError, ValueError) as exc:
        raise ValueError('Période de signature invalide.') from exc
    if (requested_year, requested_month) != period:
        raise ValueError('Cette période ne peut pas être signée.')
    signature_png = _decode_signature(payload.get('signature'))
    already_signed = db.session.execute(text("""
        SELECT 1 FROM dbo.COLAB_FORFAIT_JOURS_ASSINATURA
        WHERE PENO = :peno AND PEFEID = :pefeid AND ANO = :year AND MES = :month
    """), {'peno': employee['peno'], 'pefeid': employee['pefeid'], 'year': year, 'month': month}).scalar()
    if already_signed:
        raise ValueError('Ce document a déjà été signé.')
    pdf_content, filename = build_month_pdf(user, year, month, signature_png)
    login = str(getattr(user, 'LOGIN', '') or '').strip()
    db.session.execute(text("""
        INSERT INTO dbo.COLAB_FORFAIT_JOURS_ASSINATURA
          (ASSINATURASTAMP, PENO, PEFEID, USSTAMP, LOGIN, ANO, MES, ASSINATURA_PNG, PDF_ASSINADO, NOME_FICHEIRO)
        VALUES (:stamp, :peno, :pefeid, :userstamp, :login, :year, :month, :signature, :pdf, :filename)
    """), {'stamp': _stamp(), 'peno': employee['peno'], 'pefeid': employee['pefeid'], 'userstamp': employee['userstamp'], 'login': login, 'year': year, 'month': month, 'signature': signature_png, 'pdf': pdf_content, 'filename': filename})
    db.session.commit()
    return {'ok': True, 'year': year, 'month': month, 'filename': filename}


def signed_month_pdf(user: Any, year: Any, month: Any) -> tuple[bytes, str]:
    _require_forfait_user(user)
    ensure_forfait_jours_schema()
    employee = get_colaborador_context(user)
    selected_year, selected_month = _year(year), int(month)
    row = db.session.execute(text("""
        SELECT PDF_ASSINADO, NOME_FICHEIRO
        FROM dbo.COLAB_FORFAIT_JOURS_ASSINATURA
        WHERE PENO = :peno AND PEFEID = :pefeid AND ANO = :year AND MES = :month
    """), {'peno': employee['peno'], 'pefeid': employee['pefeid'], 'year': selected_year, 'month': selected_month}).mappings().first()
    if not row:
        raise ValueError('Le PDF signé est introuvable.')
    return bytes(row.get('PDF_ASSINADO') or b''), str(row.get('NOME_FICHEIRO') or 'forfait-jours-signe.pdf')
