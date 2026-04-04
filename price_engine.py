import hmac
import json
import os
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

import click
from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import bindparam, text

from models import db
from services.qr_atcud_service import get_param as qr_get_param


DEFAULT_HORIZON_DAYS = 400
DEFAULT_UPDATE_THRESHOLD = Decimal("1.00")
DEFAULT_DAILY_VARIATION_LIMIT = Decimal("0.00")


pricing_bp = Blueprint("pricing", __name__, url_prefix="/pricing")

PRICING_SYNC_ROBOTS = (
    {"name": "R2-D2", "from": "A", "to": "ZZZ"},
)


def _pricing_robot_key():
    value = str(qr_get_param(db.session, "PRICING_ROBOT_KEY", "") or "").strip()
    if value:
        return value
    value = str(os.getenv("PRICING_ROBOT_KEY") or "").strip()
    if value:
        return value
    return str(os.getenv("STATIONZERO_ROBOT_KEY") or "").strip()


def _extract_robot_credential():
    direct = str(request.headers.get("X-StationZero-Key") or "").strip()
    if direct:
        return direct
    auth = str(request.headers.get("Authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return ""


def _authorize_pricing_robot_request():
    expected = _pricing_robot_key()
    if not expected:
        return "PRICING_ROBOT_KEY nao configurada.", 503
    received = _extract_robot_credential()
    if not received or not hmac.compare_digest(received, expected):
        return "Credencial invalida.", 401
    return None, 200


def _pricing_sync_robot_for_alojamento(alojamento):
    return PRICING_SYNC_ROBOTS[0]["name"]


def _add_months(day_value, months):
    month_index = (day_value.month - 1) + int(months)
    year = day_value.year + (month_index // 12)
    month = (month_index % 12) + 1
    return date(year, month, 1)


def _iso_or_empty(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return ""


def _quantize_money(value):
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _to_float(value):
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
        return float(value)
    try:
        number = float(value or 0)
    except Exception:
        return 0
    if number.is_integer():
        return int(number)
    return number


def _normalize_alojamento(value):
    return str(value or "").strip()


def _aloj_cache_key(value):
    return _normalize_alojamento(value).upper()


def _parse_date(value, field_name="data"):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip())
    except Exception as exc:
        raise ValueError(f"{field_name} invalida: {value}") from exc


def _iso_week_parts(day_value):
    iso_year, iso_week, _ = day_value.isocalendar()
    return iso_year, iso_week, f"{iso_year}-W{iso_week:02d}"


def _week_bounds(day_value):
    week_start = day_value - timedelta(days=day_value.isoweekday() - 1)
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def _month_bounds(day_value):
    month_start = day_value.replace(day=1)
    if month_start.month == 12:
        month_end = date(month_start.year + 1, 1, 1) - timedelta(days=1)
    else:
        month_end = date(month_start.year, month_start.month + 1, 1) - timedelta(days=1)
    return month_start, month_end


def _month_pickup_season(day_value):
    month = int(day_value.month)
    if month == 3:
        return "MID"
    if 4 <= month <= 10:
        return "ALTA"
    return "BAIXA"


def _clamp(value, min_value, max_value):
    return min(max(value, min_value), max_value)


def _safe_decimal(value, default="0"):
    if value is None or value == "":
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    text = str(value).strip().replace(" ", "")
    if text == "":
        return Decimal(default)
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Valor decimal invalido: {value}") from exc


def _round_price(value):
    return Decimal(str(value or 0)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def _as_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y", "on"}


def _normalize_mmdd(value, field_name):
    raw = str(value or "").strip()
    if len(raw) != 4 or not raw.isdigit():
        raise ValueError(f"{field_name} deve ter o formato MMDD.")
    month = int(raw[:2])
    day = int(raw[2:])
    try:
        date(2000, month, day)
    except Exception as exc:
        raise ValueError(f"{field_name} invalido: {raw}.") from exc
    return raw


def _interpolate_curve(points, lead_days):
    if not points:
        return Decimal("0")

    ordered = sorted(points, key=lambda item: item[0])
    if lead_days <= ordered[0][0]:
        return ordered[0][1]
    if lead_days > ordered[-1][0]:
        return Decimal("0")
    if lead_days == ordered[-1][0]:
        return ordered[-1][1]

    for idx in range(1, len(ordered)):
        x1, y1 = ordered[idx - 1]
        x2, y2 = ordered[idx]
        if x1 <= lead_days <= x2:
            if x1 == x2:
                return y2
            ratio = Decimal(str((lead_days - x1) / (x2 - x1)))
            return y1 + ((y2 - y1) * ratio)
    return ordered[-1][1]


def _mmdd_matches(mmdd_ini, mmdd_fim, day_value):
    mmdd = day_value.strftime("%m%d")
    start = str(mmdd_ini or "").strip()
    end = str(mmdd_fim or "").strip()
    if len(start) != 4 or len(end) != 4:
        return False
    if start <= end:
        return start <= mmdd <= end
    return mmdd >= start or mmdd <= end


def _daterange(start_date, end_date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def _load_existing_prices(session, start_date, end_date, alojamento=None):
    sql = """
        SELECT
            LTRIM(RTRIM(AL_NOME)) AS AL_NOME,
            CAST([DATA] AS date) AS DIA,
            PRECO_CALC,
            PRECO_FINAL,
            ISNULL([SYNC], 0) AS [SYNC],
            SYNCED_AT,
            FLAGS
        FROM dbo.PR_CALC_DAY
        WHERE CAST([DATA] AS date) BETWEEN :start_date AND :end_date
    """
    params = {"start_date": start_date, "end_date": end_date}
    if alojamento:
        sql += " AND LTRIM(RTRIM(AL_NOME)) = :alojamento"
        params["alojamento"] = alojamento

    rows = session.execute(text(sql), params).mappings().all()
    existing = {}
    for row in rows:
        existing[(_aloj_cache_key(row.get("AL_NOME")), row.get("DIA"))] = {
            "preco_calc": _quantize_money(row.get("PRECO_CALC") or 0),
            "preco_final": _quantize_money(row.get("PRECO_FINAL") or 0),
            "sync": bool(row.get("SYNC")),
            "synced_at": row.get("SYNCED_AT"),
            "flags": row.get("FLAGS") or "",
        }
    return existing


def _get_al_nome_sql_type(session):
    row = session.execute(
        text(
            """
            SELECT DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, COLLATION_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'dbo'
              AND TABLE_NAME = 'AL'
              AND COLUMN_NAME = 'NOME'
            """
        )
    ).mappings().first()
    if not row:
        raise ValueError("Nao foi possivel localizar dbo.AL.NOME.")

    data_type = str(row.get("DATA_TYPE") or "").upper()
    char_len = row.get("CHARACTER_MAXIMUM_LENGTH")
    if data_type in {"VARCHAR", "NVARCHAR", "CHAR", "NCHAR", "VARBINARY"}:
        if int(char_len or 0) == -1:
            sql_type = f"{data_type}(MAX)"
        else:
            sql_type = f"{data_type}({int(char_len or 0)})"
    else:
        sql_type = data_type

    collation = row.get("COLLATION_NAME")
    if collation and data_type in {"VARCHAR", "NVARCHAR", "CHAR", "NCHAR"}:
        sql_type = f"{sql_type} COLLATE {collation}"
    return sql_type


def validate_al_key(session):
    missing = session.execute(
        text(
            """
            SELECT COUNT(*) AS TOTAL
            FROM dbo.AL
            WHERE NOME IS NULL OR LTRIM(RTRIM(NOME)) = ''
            """
        )
    ).scalar_one()
    if int(missing or 0):
        raise ValueError("Existem registos em AL sem NOME. O Price Manager usa AL.NOME como chave.")

    duplicates = session.execute(
        text(
            """
            SELECT TOP 1 LTRIM(RTRIM(NOME)) AS NOME
            FROM dbo.AL
            GROUP BY LTRIM(RTRIM(NOME))
            HAVING COUNT(*) > 1
            ORDER BY NOME
            """
        )
    ).scalar()
    if duplicates:
        raise ValueError(
            f"AL.NOME nao e unico. Corrija duplicados antes de usar o Price Manager (ex.: '{duplicates}')."
        )


def ensure_pricing_schema(session):
    validate_al_key(session)
    al_name_sql_type = _get_al_nome_sql_type(session)

    ddl_statements = [
        """
        IF NOT EXISTS (
            SELECT 1
            FROM sys.indexes
            WHERE name = 'UX_AL_NOME_PRICE_MANAGER'
              AND object_id = OBJECT_ID('dbo.AL')
        )
        BEGIN
            CREATE UNIQUE NONCLUSTERED INDEX UX_AL_NOME_PRICE_MANAGER ON dbo.AL (NOME);
        END
        """,
        """
        IF OBJECT_ID('dbo.PR_PERFIL', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.PR_PERFIL (
                PERFIL_ID INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
                NOME NVARCHAR(120) NOT NULL,
                K_PICKUP DECIMAL(9,6) NOT NULL CONSTRAINT DF_PR_PERFIL_K_PICKUP DEFAULT (0.010000),
                LIM_AJUSTE_MIN DECIMAL(9,6) NOT NULL CONSTRAINT DF_PR_PERFIL_LIM_MIN DEFAULT (-0.200000),
                LIM_AJUSTE_MAX DECIMAL(9,6) NOT NULL CONSTRAINT DF_PR_PERFIL_LIM_MAX DEFAULT (0.200000)
            );
        END
        """,
        """
        IF OBJECT_ID('dbo.PR_SAZONAL_MES', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.PR_SAZONAL_MES (
                MES TINYINT NOT NULL PRIMARY KEY,
                INDICE DECIMAL(7,2) NOT NULL,
                NOTA NVARCHAR(200) NULL,
                CONSTRAINT CK_PR_SAZONAL_MES_RANGE CHECK (MES BETWEEN 1 AND 12)
            );
        END
        """,
        f"""
        IF OBJECT_ID('dbo.PR_ALOJAMENTO', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.PR_ALOJAMENTO (
                AL_NOME {al_name_sql_type} NOT NULL PRIMARY KEY,
                PERFIL_ID INT NOT NULL,
                REGIME NVARCHAR(20) NOT NULL CONSTRAINT DF_PR_ALOJAMENTO_REGIME DEFAULT ('GESTAO'),
                PRECO_MIN DECIMAL(10,2) NOT NULL,
                PRECO_BASE DECIMAL(10,2) NOT NULL,
                PRECO_MAX DECIMAL(10,2) NOT NULL,
                LAST_MIN_DISC DECIMAL(9,2) NOT NULL CONSTRAINT DF_PR_ALOJAMENTO_LAST_MIN_DISC DEFAULT (0),
                LAST_MIN_DAYS INT NOT NULL CONSTRAINT DF_PR_ALOJAMENTO_LAST_MIN_DAYS DEFAULT (0),
                SYNC BIT NOT NULL CONSTRAINT DF_PR_ALOJAMENTO_SYNC DEFAULT (0),
                ATIVO BIT NOT NULL CONSTRAINT DF_PR_ALOJAMENTO_ATIVO DEFAULT (1),
                CONSTRAINT FK_PR_ALOJAMENTO_AL FOREIGN KEY (AL_NOME) REFERENCES dbo.AL (NOME),
                CONSTRAINT FK_PR_ALOJAMENTO_PERFIL FOREIGN KEY (PERFIL_ID) REFERENCES dbo.PR_PERFIL (PERFIL_ID),
                CONSTRAINT CK_PR_ALOJAMENTO_PRECOS CHECK (PRECO_MIN <= PRECO_BASE AND PRECO_BASE <= PRECO_MAX)
            );
        END
        """,
    ]

    for statement in ddl_statements:
        session.execute(text(statement))

    ddl_tail = [
        """
        IF COL_LENGTH('dbo.PR_ALOJAMENTO', 'SYNC') IS NULL
        BEGIN
            ALTER TABLE dbo.PR_ALOJAMENTO
            ADD SYNC BIT NOT NULL CONSTRAINT DF_PR_ALOJAMENTO_SYNC DEFAULT (0);
        END
        """,
        """
        IF COL_LENGTH('dbo.PR_ALOJAMENTO', 'LAST_MIN_DISC') IS NULL
        BEGIN
            ALTER TABLE dbo.PR_ALOJAMENTO
            ADD LAST_MIN_DISC DECIMAL(9,2) NOT NULL CONSTRAINT DF_PR_ALOJAMENTO_LAST_MIN_DISC DEFAULT (0);
        END
        """,
        """
        IF COL_LENGTH('dbo.PR_ALOJAMENTO', 'LAST_MIN_DAYS') IS NULL
        BEGIN
            ALTER TABLE dbo.PR_ALOJAMENTO
            ADD LAST_MIN_DAYS INT NOT NULL CONSTRAINT DF_PR_ALOJAMENTO_LAST_MIN_DAYS DEFAULT (0);
        END
        """,
        """
        IF OBJECT_ID('dbo.PR_DIA_SEMANA_FATOR', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.PR_DIA_SEMANA_FATOR (
                PERFIL_ID INT NOT NULL,
                DOW TINYINT NOT NULL,
                FATOR DECIMAL(9,6) NOT NULL,
                CONSTRAINT PK_PR_DIA_SEMANA_FATOR PRIMARY KEY (PERFIL_ID, DOW),
                CONSTRAINT FK_PR_DIA_SEMANA_FATOR_PERFIL FOREIGN KEY (PERFIL_ID) REFERENCES dbo.PR_PERFIL (PERFIL_ID),
                CONSTRAINT CK_PR_DIA_SEMANA_FATOR_DOW CHECK (DOW BETWEEN 1 AND 7)
            );
        END
        """,
        """
        IF OBJECT_ID('dbo.PR_EVENTO', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.PR_EVENTO (
                EVENTO_ID INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
                NOME NVARCHAR(120) NOT NULL,
                MMDD_INI CHAR(4) NOT NULL,
                MMDD_FIM CHAR(4) NOT NULL,
                FATOR DECIMAL(9,6) NOT NULL,
                PRIORIDADE INT NOT NULL CONSTRAINT DF_PR_EVENTO_PRIORIDADE DEFAULT (0),
                ATIVO BIT NOT NULL CONSTRAINT DF_PR_EVENTO_ATIVO DEFAULT (1)
            );
        END
        """,
        """
        IF OBJECT_ID('dbo.PR_EVENTO_ANO', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.PR_EVENTO_ANO (
                EVENTO_ID INT NOT NULL,
                ANO INT NOT NULL,
                DATA_INI DATE NOT NULL,
                DATA_FIM DATE NOT NULL,
                FATOR_OVERRIDE DECIMAL(9,6) NULL,
                ATIVO BIT NOT NULL CONSTRAINT DF_PR_EVENTO_ANO_ATIVO DEFAULT (1),
                NOTA NVARCHAR(200) NULL,
                CONSTRAINT PK_PR_EVENTO_ANO PRIMARY KEY (EVENTO_ID, ANO),
                CONSTRAINT FK_PR_EVENTO_ANO_EVENTO FOREIGN KEY (EVENTO_ID) REFERENCES dbo.PR_EVENTO (EVENTO_ID)
            );
        END
        """,
        """
        IF OBJECT_ID('dbo.PR_PICKUP_CURVE', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.PR_PICKUP_CURVE (
                PERFIL_ID INT NOT NULL,
                LEAD_DAYS INT NOT NULL,
                OCUP_ALVO DECIMAL(7,2) NOT NULL,
                CONSTRAINT PK_PR_PICKUP_CURVE PRIMARY KEY (PERFIL_ID, LEAD_DAYS),
                CONSTRAINT FK_PR_PICKUP_CURVE_PERFIL FOREIGN KEY (PERFIL_ID) REFERENCES dbo.PR_PERFIL (PERFIL_ID)
            );
        END
        """,
        """
        IF OBJECT_ID('dbo.PR_PICKUP_CURVE_MENSAL', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.PR_PICKUP_CURVE_MENSAL (
                TEMPORADA NVARCHAR(20) NOT NULL,
                LEAD_DAYS INT NOT NULL,
                OCUP_ALVO DECIMAL(7,2) NOT NULL,
                CONSTRAINT PK_PR_PICKUP_CURVE_MENSAL PRIMARY KEY (TEMPORADA, LEAD_DAYS),
                CONSTRAINT CK_PR_PICKUP_CURVE_MENSAL_TEMPORADA CHECK (TEMPORADA IN ('ALTA', 'MID', 'BAIXA')),
                CONSTRAINT CK_PR_PICKUP_CURVE_MENSAL_OCUP CHECK (OCUP_ALVO BETWEEN 0 AND 100)
            );
        END
        """,
        """
        IF OBJECT_ID('dbo.PR_PROMO', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.PR_PROMO (
                PROMO_ID INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
                PERFIL_ID INT NOT NULL,
                DATA_INI DATE NOT NULL,
                DATA_FIM DATE NOT NULL,
                DESCONTO_PCT DECIMAL(9,2) NOT NULL,
                NOTA NVARCHAR(200) NULL,
                ATIVO BIT NOT NULL CONSTRAINT DF_PR_PROMO_ATIVO DEFAULT (1),
                CRIADO_EM DATETIME2(0) NOT NULL CONSTRAINT DF_PR_PROMO_CRIADO_EM DEFAULT (SYSUTCDATETIME()),
                CRIADO_POR NVARCHAR(60) NULL,
                CONSTRAINT FK_PR_PROMO_PERFIL FOREIGN KEY (PERFIL_ID) REFERENCES dbo.PR_PERFIL (PERFIL_ID),
                CONSTRAINT CK_PR_PROMO_INTERVALO CHECK (DATA_FIM >= DATA_INI),
                CONSTRAINT CK_PR_PROMO_PCT CHECK (DESCONTO_PCT >= 0 AND DESCONTO_PCT <= 100)
            );
        END
        """,
        f"""
        IF OBJECT_ID('dbo.PR_OVERRIDE', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.PR_OVERRIDE (
                OVR_ID INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
                AL_NOME {al_name_sql_type} NOT NULL,
                TIPO NVARCHAR(20) NOT NULL,
                DATA_INI DATE NOT NULL,
                DATA_FIM DATE NOT NULL,
                VALOR DECIMAL(10,2) NOT NULL,
                PERMITIR_ABAIXO_MIN BIT NOT NULL CONSTRAINT DF_PR_OVERRIDE_PERMITIR_ABAIXO_MIN DEFAULT (0),
                MOTIVO NVARCHAR(250) NULL,
                ATIVO BIT NOT NULL CONSTRAINT DF_PR_OVERRIDE_ATIVO DEFAULT (1),
                CRIADO_EM DATETIME2(0) NOT NULL CONSTRAINT DF_PR_OVERRIDE_CRIADO_EM DEFAULT (SYSUTCDATETIME()),
                CRIADO_POR NVARCHAR(60) NULL,
                CONSTRAINT FK_PR_OVERRIDE_AL FOREIGN KEY (AL_NOME) REFERENCES dbo.AL (NOME),
                CONSTRAINT CK_PR_OVERRIDE_TIPO CHECK (TIPO IN ('PRECO_FIXO', 'DESCONTO_PCT')),
                CONSTRAINT CK_PR_OVERRIDE_INTERVALO CHECK (DATA_FIM >= DATA_INI)
            );
        END
        """,
        f"""
        IF OBJECT_ID('dbo.PR_CALC_DAY', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.PR_CALC_DAY (
                AL_NOME {al_name_sql_type} NOT NULL,
                [DATA] DATE NOT NULL,
                ISO_WEEK CHAR(8) NOT NULL,
                PRECO_CALC DECIMAL(10,2) NOT NULL,
                PRECO_FINAL DECIMAL(10,2) NOT NULL,
                [SYNC] BIT NOT NULL CONSTRAINT DF_PR_CALC_DAY_SYNC DEFAULT (0),
                SYNCED_AT DATETIME2(0) NULL,
                FLAGS NVARCHAR(MAX) NULL,
                UPDATED_AT DATETIME2(0) NOT NULL,
                CONSTRAINT PK_PR_CALC_DAY PRIMARY KEY (AL_NOME, [DATA]),
                CONSTRAINT FK_PR_CALC_DAY_AL FOREIGN KEY (AL_NOME) REFERENCES dbo.AL (NOME)
            );
        END
        """,
        """
        IF NOT EXISTS (
            SELECT 1 FROM sys.indexes
            WHERE name = 'IX_PR_CALC_DAY_DATA'
              AND object_id = OBJECT_ID('dbo.PR_CALC_DAY')
        )
        BEGIN
            CREATE NONCLUSTERED INDEX IX_PR_CALC_DAY_DATA ON dbo.PR_CALC_DAY ([DATA]);
        END
        """,
        """
        IF COL_LENGTH('dbo.PR_CALC_DAY', 'SYNC') IS NULL
        BEGIN
            ALTER TABLE dbo.PR_CALC_DAY
            ADD [SYNC] BIT NOT NULL CONSTRAINT DF_PR_CALC_DAY_SYNC DEFAULT (0);
        END
        """,
        """
        IF COL_LENGTH('dbo.PR_CALC_DAY', 'SYNCED_AT') IS NULL
        BEGIN
            ALTER TABLE dbo.PR_CALC_DAY
            ADD SYNCED_AT DATETIME2(0) NULL;
        END
        """,
        """
        IF NOT EXISTS (
            SELECT 1 FROM sys.indexes
            WHERE name = 'IX_PR_CALC_DAY_AL_NOME_DATA'
              AND object_id = OBJECT_ID('dbo.PR_CALC_DAY')
        )
        BEGIN
            CREATE NONCLUSTERED INDEX IX_PR_CALC_DAY_AL_NOME_DATA ON dbo.PR_CALC_DAY (AL_NOME, [DATA]);
        END
        """,
        """
        IF NOT EXISTS (
            SELECT 1 FROM sys.indexes
            WHERE name = 'IX_PR_PROMO_PERFIL_DATA'
              AND object_id = OBJECT_ID('dbo.PR_PROMO')
        )
        BEGIN
            CREATE NONCLUSTERED INDEX IX_PR_PROMO_PERFIL_DATA ON dbo.PR_PROMO (PERFIL_ID, DATA_INI, DATA_FIM);
        END
        """,
        """
        IF NOT EXISTS (
            SELECT 1 FROM sys.indexes
            WHERE name = 'IX_PR_OVERRIDE_AL_NOME_DATA'
              AND object_id = OBJECT_ID('dbo.PR_OVERRIDE')
        )
        BEGIN
            CREATE NONCLUSTERED INDEX IX_PR_OVERRIDE_AL_NOME_DATA ON dbo.PR_OVERRIDE (AL_NOME, DATA_INI, DATA_FIM);
        END
        """,
        """
        IF NOT EXISTS (
            SELECT 1 FROM sys.indexes
            WHERE name = 'IX_PR_EVENTO_ANO_ANO'
              AND object_id = OBJECT_ID('dbo.PR_EVENTO_ANO')
        )
        BEGIN
            CREATE NONCLUSTERED INDEX IX_PR_EVENTO_ANO_ANO ON dbo.PR_EVENTO_ANO (ANO);
        END
        """,
    ]

    for statement in ddl_tail:
        session.execute(text(statement))

    if not session.execute(text("SELECT COUNT(*) FROM dbo.PR_PERFIL")).scalar_one():
        session.execute(
            text(
                """
                INSERT INTO dbo.PR_PERFIL (NOME, K_PICKUP, LIM_AJUSTE_MIN, LIM_AJUSTE_MAX)
                VALUES ('Base', 0.010000, -0.200000, 0.200000)
                """
            )
        )

    for month in range(1, 13):
        session.execute(
            text(
                """
                IF NOT EXISTS (SELECT 1 FROM dbo.PR_SAZONAL_MES WHERE MES = :mes)
                BEGIN
                    INSERT INTO dbo.PR_SAZONAL_MES (MES, INDICE, NOTA)
                    VALUES (:mes, 100.00, 'Default 100%')
                END
                """
            ),
            {"mes": month},
        )

    session.commit()


def _load_pricing_inputs(session, start_date, end_date, alojamento=None):
    aloj_sql = """
        SELECT
            LTRIM(RTRIM(pa.AL_NOME)) AS AL_NOME,
            pa.PERFIL_ID,
            LTRIM(RTRIM(ISNULL(pa.REGIME, 'GESTAO'))) AS REGIME,
            pa.PRECO_MIN,
            pa.PRECO_BASE,
            pa.PRECO_MAX,
            ISNULL(pa.LAST_MIN_DISC, 0) AS LAST_MIN_DISC,
            ISNULL(pa.LAST_MIN_DAYS, 0) AS LAST_MIN_DAYS
        FROM dbo.PR_ALOJAMENTO pa
        WHERE ISNULL(pa.ATIVO, 0) = 1
    """
    params = {}
    if alojamento:
        aloj_sql += " AND LTRIM(RTRIM(pa.AL_NOME)) = :alojamento"
        params["alojamento"] = alojamento
    aloj_sql += " ORDER BY pa.AL_NOME"

    aloj_rows = session.execute(text(aloj_sql), params).mappings().all()
    if not aloj_rows:
        return {
            "alojamentos": [],
            "profiles": {},
            "seasonality": {},
            "dow_factors": {},
            "events": [],
            "event_years": {},
            "pickup_curves": {},
            "monthly_pickup_curves": {},
            "promotions": {},
            "overrides": {},
            "reserved_days": {},
            "week_occupancy": {},
            "month_occupancy": {},
        }

    profile_ids = sorted({int(row["PERFIL_ID"]) for row in aloj_rows if row.get("PERFIL_ID") is not None})
    years = sorted({start_date.year, end_date.year, (start_date - timedelta(days=7)).year, (end_date + timedelta(days=7)).year})

    profiles = {}
    if profile_ids:
        placeholders = ", ".join(f":p{idx}" for idx in range(len(profile_ids)))
        profile_params = {f"p{idx}": profile_ids[idx] for idx in range(len(profile_ids))}
        rows = session.execute(
            text(
                f"""
                SELECT PERFIL_ID, NOME, K_PICKUP, LIM_AJUSTE_MIN, LIM_AJUSTE_MAX
                FROM dbo.PR_PERFIL
                WHERE PERFIL_ID IN ({placeholders})
                """
            ),
            profile_params,
        ).mappings().all()
        profiles = {
            int(row["PERFIL_ID"]): {
                "nome": row.get("NOME") or "",
                "k_pickup": _safe_decimal(row.get("K_PICKUP"), "0.01"),
                "lim_min": _safe_decimal(row.get("LIM_AJUSTE_MIN"), "-0.2"),
                "lim_max": _safe_decimal(row.get("LIM_AJUSTE_MAX"), "0.2"),
            }
            for row in rows
        }

    seasonality_rows = session.execute(text("SELECT MES, INDICE FROM dbo.PR_SAZONAL_MES")).mappings().all()
    seasonality = {int(row["MES"]): _safe_decimal(row.get("INDICE"), "100") for row in seasonality_rows}

    dow_factors = {}
    if profile_ids:
        placeholders = ", ".join(f":d{idx}" for idx in range(len(profile_ids)))
        dow_params = {f"d{idx}": profile_ids[idx] for idx in range(len(profile_ids))}
        rows = session.execute(
            text(
                f"""
                SELECT PERFIL_ID, DOW, FATOR
                FROM dbo.PR_DIA_SEMANA_FATOR
                WHERE PERFIL_ID IN ({placeholders})
                """
            ),
            dow_params,
        ).mappings().all()
        dow_factors = {
            (int(row["PERFIL_ID"]), int(row["DOW"])): _safe_decimal(row.get("FATOR"), "1")
            for row in rows
        }

    events = session.execute(
        text(
            """
            SELECT EVENTO_ID, NOME, MMDD_INI, MMDD_FIM, FATOR, PRIORIDADE
            FROM dbo.PR_EVENTO
            WHERE ISNULL(ATIVO, 0) = 1
            ORDER BY PRIORIDADE DESC, EVENTO_ID ASC
            """
        )
    ).mappings().all()

    event_years = {}
    if years:
        placeholders = ", ".join(f":y{idx}" for idx in range(len(years)))
        year_params = {f"y{idx}": years[idx] for idx in range(len(years))}
        rows = session.execute(
            text(
                f"""
                SELECT EVENTO_ID, ANO, DATA_INI, DATA_FIM, FATOR_OVERRIDE
                FROM dbo.PR_EVENTO_ANO
                WHERE ISNULL(ATIVO, 0) = 1
                  AND ANO IN ({placeholders})
                """
            ),
            year_params,
        ).mappings().all()
        event_years = {
            (int(row["EVENTO_ID"]), int(row["ANO"])): {
                "data_ini": row.get("DATA_INI"),
                "data_fim": row.get("DATA_FIM"),
                "fator_override": row.get("FATOR_OVERRIDE"),
            }
            for row in rows
        }

    pickup_curves = {}
    if profile_ids:
        placeholders = ", ".join(f":c{idx}" for idx in range(len(profile_ids)))
        curve_params = {f"c{idx}": profile_ids[idx] for idx in range(len(profile_ids))}
        rows = session.execute(
            text(
                f"""
                SELECT PERFIL_ID, LEAD_DAYS, OCUP_ALVO
                FROM dbo.PR_PICKUP_CURVE
                WHERE PERFIL_ID IN ({placeholders})
                ORDER BY PERFIL_ID ASC, LEAD_DAYS ASC
                """
            ),
            curve_params,
        ).mappings().all()
        for row in rows:
            pickup_curves.setdefault(int(row["PERFIL_ID"]), []).append(
                (int(row["LEAD_DAYS"]), _safe_decimal(row.get("OCUP_ALVO"), "0"))
            )

    monthly_pickup_curves = {}
    try:
        rows = session.execute(
            text(
                """
                SELECT TEMPORADA, LEAD_DAYS, OCUP_ALVO
                FROM dbo.PR_PICKUP_CURVE_MENSAL
                ORDER BY TEMPORADA ASC, LEAD_DAYS ASC
                """
            )
        ).mappings().all()
        for row in rows:
            season_code = str(row.get("TEMPORADA") or "").strip().upper()
            if not season_code:
                continue
            monthly_pickup_curves.setdefault(season_code, []).append(
                (int(row["LEAD_DAYS"]), _safe_decimal(row.get("OCUP_ALVO"), "0"))
            )
    except Exception:
        monthly_pickup_curves = {}

    promotions = {}
    if profile_ids:
        placeholders = ", ".join(f":pm{idx}" for idx in range(len(profile_ids)))
        promo_params = {
            "start_date": start_date,
            "end_date": end_date,
            **{f"pm{idx}": profile_ids[idx] for idx in range(len(profile_ids))},
        }
        promo_rows = session.execute(
            text(
                f"""
                SELECT
                    PROMO_ID,
                    PERFIL_ID,
                    DATA_INI,
                    DATA_FIM,
                    DESCONTO_PCT,
                    ISNULL(NOTA, '') AS NOTA,
                    CRIADO_EM,
                    ISNULL(CRIADO_POR, '') AS CRIADO_POR
                FROM dbo.PR_PROMO
                WHERE ISNULL(ATIVO, 0) = 1
                  AND DATA_INI <= :end_date
                  AND DATA_FIM >= :start_date
                  AND PERFIL_ID IN ({placeholders})
                ORDER BY PERFIL_ID ASC, CRIADO_EM DESC, PROMO_ID DESC
                """
            ),
            promo_params,
        ).mappings().all()
        for row in promo_rows:
            promotions.setdefault(int(row["PERFIL_ID"]), []).append(row)

    override_sql = """
        SELECT
            OVR_ID,
            LTRIM(RTRIM(AL_NOME)) AS AL_NOME,
            TIPO,
            DATA_INI,
            DATA_FIM,
            VALOR,
            ISNULL(PERMITIR_ABAIXO_MIN, 0) AS PERMITIR_ABAIXO_MIN,
            ISNULL(MOTIVO, '') AS MOTIVO,
            CRIADO_EM
        FROM dbo.PR_OVERRIDE
        WHERE ISNULL(ATIVO, 0) = 1
          AND DATA_INI <= :end_date
          AND DATA_FIM >= :start_date
    """
    override_params = {"start_date": start_date, "end_date": end_date}
    if alojamento:
        override_sql += " AND LTRIM(RTRIM(AL_NOME)) = :alojamento"
        override_params["alojamento"] = alojamento
    override_sql += " ORDER BY AL_NOME ASC, CRIADO_EM DESC, OVR_ID DESC"
    override_rows = session.execute(text(override_sql), override_params).mappings().all()
    overrides = {}
    for row in override_rows:
        overrides.setdefault(_aloj_cache_key(row.get("AL_NOME")), []).append(row)

    grid_start, _ = _week_bounds(start_date)
    _, grid_end = _week_bounds(end_date)
    reservation_sql = """
        SELECT
            LTRIM(RTRIM(ISNULL(RS.ALOJAMENTO, ''))) AS AL_NOME,
            CAST(RS.DATAIN AS date) AS DATA_INI,
            CAST(RS.DATAOUT AS date) AS DATA_FIM
        FROM dbo.RS
        WHERE RS.DATAIN IS NOT NULL
          AND RS.DATAOUT IS NOT NULL
          AND ISNULL(RS.CANCELADA, 0) = 0
          AND CAST(RS.DATAOUT AS date) > :grid_start
          AND CAST(RS.DATAIN AS date) <= :grid_end
    """
    reservation_params = {"grid_start": grid_start, "grid_end": grid_end}
    if alojamento:
        reservation_sql += " AND LTRIM(RTRIM(ISNULL(RS.ALOJAMENTO, ''))) = :alojamento"
        reservation_params["alojamento"] = alojamento

    reservation_rows = session.execute(text(reservation_sql), reservation_params).mappings().all()
    reserved_days = {}
    for row in reservation_rows:
        aloj_key = _aloj_cache_key(row.get("AL_NOME"))
        if not aloj_key:
            continue
        stay_start = max(row.get("DATA_INI"), grid_start)
        stay_end_exclusive = min(row.get("DATA_FIM"), grid_end + timedelta(days=1))
        if not stay_start or not stay_end_exclusive or stay_start >= stay_end_exclusive:
            continue
        reserved_set = reserved_days.setdefault(aloj_key, set())
        cursor = stay_start
        while cursor < stay_end_exclusive:
            reserved_set.add(cursor)
            cursor += timedelta(days=1)

    week_occupancy = {}
    for row in aloj_rows:
        aloj_key = _aloj_cache_key(row.get("AL_NOME"))
        reserved_set = reserved_days.get(aloj_key, set())
        week_cursor = grid_start
        while week_cursor <= grid_end:
            occupied_days = sum(1 for offset in range(7) if (week_cursor + timedelta(days=offset)) in reserved_set)
            week_occupancy[(aloj_key, week_cursor)] = (Decimal(occupied_days) / Decimal("7")) * Decimal("100")
            week_cursor += timedelta(days=7)

    month_occupancy = {}
    month_cursor = date(start_date.year, start_date.month, 1)
    last_month = date(end_date.year, end_date.month, 1)
    month_starts = []
    while month_cursor <= last_month:
        month_starts.append(month_cursor)
        if month_cursor.month == 12:
            month_cursor = date(month_cursor.year + 1, 1, 1)
        else:
            month_cursor = date(month_cursor.year, month_cursor.month + 1, 1)

    for row in aloj_rows:
        aloj_key = _aloj_cache_key(row.get("AL_NOME"))
        reserved_set = reserved_days.get(aloj_key, set())
        for month_start in month_starts:
            month_end = _month_bounds(month_start)[1]
            total_days = (month_end - month_start).days + 1
            occupied_days = sum(1 for offset in range(total_days) if (month_start + timedelta(days=offset)) in reserved_set)
            month_occupancy[(aloj_key, month_start)] = (Decimal(occupied_days) / Decimal(total_days)) * Decimal("100")

    return {
        "alojamentos": aloj_rows,
        "profiles": profiles,
        "seasonality": seasonality,
        "dow_factors": dow_factors,
        "events": events,
        "event_years": event_years,
        "pickup_curves": pickup_curves,
        "monthly_pickup_curves": monthly_pickup_curves,
        "promotions": promotions,
        "overrides": overrides,
        "reserved_days": reserved_days,
        "week_occupancy": week_occupancy,
        "month_occupancy": month_occupancy,
    }


def get_occupancy_week(alojamento, week_start, week_end, cached_week_occupancy=None):
    cache = cached_week_occupancy or {}
    return cache.get((_aloj_cache_key(alojamento), week_start), Decimal("0"))


def get_occupancy_month(alojamento, month_start, cached_month_occupancy=None):
    cache = cached_month_occupancy or {}
    return cache.get((_aloj_cache_key(alojamento), month_start), Decimal("0"))


def _resolve_event_factor(day_value, events, event_years):
    best = None
    for event in events:
        event_id = int(event["EVENTO_ID"])
        yearly = event_years.get((event_id, day_value.year))
        applies = False
        factor = _safe_decimal(event.get("FATOR"), "1")

        if yearly:
            start = yearly.get("data_ini")
            end = yearly.get("data_fim")
            if start and end and start <= day_value <= end:
                applies = True
                if yearly.get("fator_override") is not None:
                    factor = _safe_decimal(yearly.get("fator_override"), "1")
        else:
            applies = _mmdd_matches(event.get("MMDD_INI"), event.get("MMDD_FIM"), day_value)

        if applies:
            candidate = {
                "evento_id": event_id,
                "nome": event.get("NOME") or "",
                "prioridade": int(event.get("PRIORIDADE") or 0),
                "factor": factor,
            }
            if best is None or candidate["prioridade"] > best["prioridade"]:
                best = candidate

    if best is None:
        return Decimal("1"), None
    return best["factor"], best


def _match_override(overrides, day_value):
    for override in overrides or []:
        if override.get("DATA_INI") <= day_value <= override.get("DATA_FIM"):
            return override
    return None


def _match_promotion(promotions, day_value):
    for promo in promotions or []:
        if promo.get("DATA_INI") <= day_value <= promo.get("DATA_FIM"):
            return promo
    return None


def _build_flags(payload):
    return json.dumps(payload, ensure_ascii=False, default=str, separators=(",", ":"))


def recalculate_prices(days=DEFAULT_HORIZON_DAYS, alojamento=None, from_date=None, to_date=None):
    alojamento = _normalize_alojamento(alojamento)
    start_date = _parse_date(from_date, "from") or date.today()
    if to_date:
        end_date = _parse_date(to_date, "to")
    else:
        horizon = int(days or DEFAULT_HORIZON_DAYS)
        if horizon <= 0:
            raise ValueError("--days tem de ser maior que zero.")
        end_date = start_date + timedelta(days=horizon - 1)

    if end_date < start_date:
        raise ValueError("O intervalo de recalculo e invalido.")

    ensure_pricing_schema(db.session)

    inputs = _load_pricing_inputs(db.session, start_date, end_date, alojamento or None)
    if not inputs["alojamentos"]:
        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_rows": 0,
            "changed_rows": 0,
            "skipped_threshold": 0,
        }

    threshold = _safe_decimal(current_app.config.get("PRICING_UPDATE_THRESHOLD_EUR"), str(DEFAULT_UPDATE_THRESHOLD))
    daily_variation_limit = _safe_decimal(
        current_app.config.get("PRICING_DAILY_VARIATION_LIMIT_PCT"),
        str(DEFAULT_DAILY_VARIATION_LIMIT),
    )
    if daily_variation_limit > 1:
        daily_variation_limit = daily_variation_limit / Decimal("100")

    existing = _load_existing_prices(db.session, start_date, end_date, alojamento or None)

    rows_to_upsert = []
    skipped_threshold = 0
    total_rows = 0
    run_ts = datetime.utcnow().replace(microsecond=0)
    today = date.today()

    for aloj in inputs["alojamentos"]:
        aloj_name = _normalize_alojamento(aloj.get("AL_NOME"))
        aloj_cache_key = _aloj_cache_key(aloj_name)
        profile_id = int(aloj.get("PERFIL_ID"))
        profile = inputs["profiles"].get(profile_id)
        if not profile:
            raise ValueError(f"Perfil {profile_id} nao encontrado para o alojamento '{aloj_name}'.")

        regime = (aloj.get("REGIME") or "GESTAO").strip().upper()
        price_min_base = _round_price(aloj.get("PRECO_MIN"))
        price_base = _round_price(aloj.get("PRECO_BASE"))
        price_max = _round_price(aloj.get("PRECO_MAX"))
        last_min_disc = _safe_decimal(aloj.get("LAST_MIN_DISC"), "0")
        last_min_days = max(int(aloj.get("LAST_MIN_DAYS") or 0), 0)
        reserved = inputs["reserved_days"].get(aloj_cache_key, set())
        previous_calc = None

        for day_value in _daterange(start_date, end_date):
            total_rows += 1
            iso_year, iso_week_num, iso_week = _iso_week_parts(day_value)
            week_start, week_end = _week_bounds(day_value)
            month_start, month_end = _month_bounds(day_value)

            month_index = inputs["seasonality"].get(day_value.month, Decimal("100"))
            month_factor = month_index / Decimal("100")
            price_min = _round_price(price_min_base * month_factor)
            dow_factor = inputs["dow_factors"].get((profile_id, day_value.isoweekday()), Decimal("1"))
            event_factor, event_info = _resolve_event_factor(day_value, inputs["events"], inputs["event_years"])

            price_after_base = price_base
            price_after_month = price_after_base * month_factor
            price_after_dow = price_after_month * dow_factor
            price_after_event = price_after_dow * event_factor
            preco = price_after_event

            is_available = day_value not in reserved
            month_season = _month_pickup_season(day_value)
            month_curve = inputs["monthly_pickup_curves"].get(month_season, [])
            month_lead_days = (month_start - today).days
            month_target_occ = _interpolate_curve(month_curve, month_lead_days)
            month_real_occ = get_occupancy_month(aloj_name, month_start, inputs["month_occupancy"])
            month_deviation = month_real_occ - month_target_occ
            month_pickup_adjustment = month_deviation * profile["k_pickup"]
            month_pickup_adjustment = _clamp(month_pickup_adjustment, profile["lim_min"], profile["lim_max"])
            if is_available and month_curve:
                preco *= Decimal("1") + month_pickup_adjustment
            price_after_month_pickup = preco

            lead_days = (week_start - today).days
            target_occ = _interpolate_curve(inputs["pickup_curves"].get(profile_id, []), lead_days)
            real_occ = get_occupancy_week(aloj_name, week_start, week_end, inputs["week_occupancy"])
            deviation = real_occ - target_occ
            pickup_adjustment = deviation * profile["k_pickup"]
            pickup_adjustment = _clamp(pickup_adjustment, profile["lim_min"], profile["lim_max"])
            if is_available:
                preco *= Decimal("1") + pickup_adjustment
            price_after_pickup = preco

            stay_lead_days = (day_value - today).days
            last_min_info = {
                "configured_pct": _to_float(last_min_disc.quantize(Decimal("0.01"))),
                "window_days": last_min_days,
                "stay_lead_days": stay_lead_days,
                "applied": False,
                "discount_pct": 0.0,
            }
            if is_available and last_min_disc > 0 and last_min_days > 0 and 0 <= stay_lead_days <= last_min_days:
                step_discount = last_min_disc / Decimal(last_min_days)
                progress_step = (last_min_days - stay_lead_days) + 1
                applied_discount_pct = min(last_min_disc, step_discount * Decimal(progress_step))
                preco *= Decimal("1") - (applied_discount_pct / Decimal("100"))
                last_min_info.update(
                    {
                        "applied": True,
                        "discount_pct": _to_float(applied_discount_pct.quantize(Decimal("0.01"))),
                    }
                )
            price_after_last_min = preco

            promo_row = _match_promotion(inputs["promotions"].get(profile_id), day_value)
            promo_info = None
            if promo_row:
                promo_pct = _safe_decimal(promo_row.get("DESCONTO_PCT"), "0")
                preco *= Decimal("1") - (promo_pct / Decimal("100"))
                promo_info = {
                    "promo_id": int(promo_row.get("PROMO_ID")),
                    "perfil_id": profile_id,
                    "desconto_pct": _to_float(promo_pct.quantize(Decimal("0.01"))),
                    "nota": promo_row.get("NOTA") or "",
                    "criado_por": promo_row.get("CRIADO_POR") or "",
                }
            price_after_promo = preco

            preco = _clamp(preco, price_min, price_max)
            price_after_clamp = preco

            smooth_info = {"applied": False}
            if previous_calc is not None and daily_variation_limit > 0:
                lower_bound = previous_calc * (Decimal("1") - daily_variation_limit)
                upper_bound = previous_calc * (Decimal("1") + daily_variation_limit)
                smoothed = _clamp(preco, lower_bound, upper_bound)
                if smoothed != preco:
                    smooth_info = {
                        "applied": True,
                        "from": _to_float(_quantize_money(preco)),
                        "to": _to_float(_quantize_money(smoothed)),
                        "limit_pct": _to_float((daily_variation_limit * Decimal("100")).quantize(Decimal("0.01"))),
                    }
                preco = smoothed
                preco = _clamp(preco, price_min, price_max)
            price_after_smooth = preco

            preco_calc = _round_price(preco)
            preco_final = preco_calc

            override_row = _match_override(inputs["overrides"].get(aloj_cache_key), day_value)
            override_info = None
            if override_row:
                override_type = (override_row.get("TIPO") or "").strip().upper()
                override_value = _safe_decimal(override_row.get("VALOR"), "0")
                if override_type == "PRECO_FIXO":
                    preco_final = _round_price(override_value)
                elif override_type == "DESCONTO_PCT":
                    preco_final = _round_price(preco_calc * (Decimal("1") - (override_value / Decimal("100"))))

                clamped_by_regime = False
                if regime == "GESTAO" and not bool(override_row.get("PERMITIR_ABAIXO_MIN")) and preco_final < price_min:
                    preco_final = price_min
                    clamped_by_regime = True

                override_info = {
                    "ovr_id": int(override_row.get("OVR_ID")),
                    "tipo": override_type,
                    "valor": _to_float(override_value),
                    "motivo": override_row.get("MOTIVO") or "",
                    "permitir_abaixo_min": bool(override_row.get("PERMITIR_ABAIXO_MIN")),
                    "clamped_by_regime": clamped_by_regime,
                }

            flags = _build_flags(
                {
                    "base": _to_float(price_base),
                    "stages": {
                        "base": _to_float(_quantize_money(price_after_base)),
                        "after_month": _to_float(_quantize_money(price_after_month)),
                        "after_dow": _to_float(_quantize_money(price_after_dow)),
                        "after_event": _to_float(_quantize_money(price_after_event)),
                        "after_pickup_month": _to_float(_quantize_money(price_after_month_pickup)),
                        "after_pickup": _to_float(_quantize_money(price_after_pickup)),
                        "after_last_min": _to_float(_quantize_money(price_after_last_min)),
                        "after_promo": _to_float(_quantize_money(price_after_promo)),
                        "after_clamp": _to_float(_quantize_money(price_after_clamp)),
                        "after_smooth": _to_float(_quantize_money(price_after_smooth)),
                    },
                    "month": {
                        "mes": day_value.month,
                        "indice": _to_float(month_index),
                        "fator": _to_float(month_factor),
                        "min_base": _to_float(price_min_base),
                        "min_effective": _to_float(price_min),
                        "result": _to_float(_quantize_money(price_after_month)),
                    },
                    "dow": {
                        "dow": day_value.isoweekday(),
                        "fator": _to_float(dow_factor),
                        "result": _to_float(_quantize_money(price_after_dow)),
                    },
                    "event": (
                        {
                            **event_info,
                            "result": _to_float(_quantize_money(price_after_event)),
                        }
                        if event_info
                        else None
                    ),
                    "pickup_month": {
                        "applied": bool(is_available and month_curve),
                        "season": month_season,
                        "lead_days": month_lead_days,
                        "target_occ": _to_float(month_target_occ.quantize(Decimal("0.01"))),
                        "real_occ": _to_float(month_real_occ.quantize(Decimal("0.01"))),
                        "deviation": _to_float(month_deviation.quantize(Decimal("0.01"))),
                        "k": _to_float(profile["k_pickup"]),
                        "adjustment_pct": _to_float((month_pickup_adjustment * Decimal("100")).quantize(Decimal("0.01"))),
                        "month_start": month_start.isoformat(),
                        "month_end": month_end.isoformat(),
                        "result": _to_float(_quantize_money(price_after_month_pickup)),
                    },
                    "pickup": {
                        "applied": bool(is_available),
                        "lead_days": lead_days,
                        "target_occ": _to_float(target_occ.quantize(Decimal("0.01"))),
                        "real_occ": _to_float(real_occ.quantize(Decimal("0.01"))),
                        "deviation": _to_float(deviation.quantize(Decimal("0.01"))),
                        "k": _to_float(profile["k_pickup"]),
                        "adjustment_pct": _to_float((pickup_adjustment * Decimal("100")).quantize(Decimal("0.01"))),
                        "week_start": week_start.isoformat(),
                        "week_end": week_end.isoformat(),
                        "result": _to_float(_quantize_money(price_after_pickup)),
                    },
                    "last_min": {
                        **last_min_info,
                        "result": _to_float(_quantize_money(price_after_last_min)),
                    },
                    "availability": {"available": bool(is_available)},
                    "clamp": {
                        "min_base": _to_float(price_min_base),
                        "min": _to_float(price_min),
                        "max": _to_float(price_max),
                        "result": _to_float(_quantize_money(price_after_clamp)),
                    },
                    "smooth": {
                        **smooth_info,
                        "result": _to_float(_quantize_money(price_after_smooth)),
                    },
                    "promo": (
                        {
                            **promo_info,
                            "result": _to_float(_quantize_money(price_after_promo)),
                        }
                        if promo_info
                        else None
                    ),
                    "override": override_info,
                    "result": {
                        "preco_calc": _to_float(preco_calc),
                        "preco_final": _to_float(preco_final),
                        "iso_year": iso_year,
                        "iso_week": iso_week_num,
                    },
                }
            )

            existing_row = existing.get((aloj_cache_key, day_value))
            if existing_row:
                diff_calc = abs(preco_calc - existing_row["preco_calc"])
                diff_final = abs(preco_final - existing_row["preco_final"])
                flags_changed = flags != (existing_row.get("flags") or "")
                if diff_calc < threshold and diff_final < threshold and not flags_changed:
                    skipped_threshold += 1
                    previous_calc = existing_row["preco_calc"]
                    continue

            preserve_sync = bool(existing_row) and preco_final == existing_row["preco_final"]
            rows_to_upsert.append(
                {
                    "AL_NOME": aloj_name,
                    "DATA": day_value,
                    "ISO_WEEK": iso_week,
                    "PRECO_CALC": preco_calc,
                    "PRECO_FINAL": preco_final,
                    "SYNC": 1 if preserve_sync and existing_row.get("sync") else 0,
                    "SYNCED_AT": existing_row.get("synced_at") if preserve_sync and existing_row else None,
                    "FLAGS": flags,
                    "UPDATED_AT": run_ts,
                }
            )
            previous_calc = preco_calc

    if rows_to_upsert:
        merge_sql = text(
            """
            MERGE dbo.PR_CALC_DAY AS target
            USING (
                SELECT
                    :AL_NOME AS AL_NOME,
                    :DATA AS [DATA],
                    :ISO_WEEK AS ISO_WEEK,
                    :PRECO_CALC AS PRECO_CALC,
                    :PRECO_FINAL AS PRECO_FINAL,
                    :SYNC AS [SYNC],
                    :SYNCED_AT AS SYNCED_AT,
                    :FLAGS AS FLAGS,
                    :UPDATED_AT AS UPDATED_AT
            ) AS source
            ON target.AL_NOME = source.AL_NOME
               AND target.[DATA] = source.[DATA]
            WHEN MATCHED THEN
                UPDATE SET
                    ISO_WEEK = source.ISO_WEEK,
                    PRECO_CALC = source.PRECO_CALC,
                    PRECO_FINAL = source.PRECO_FINAL,
                    [SYNC] = source.[SYNC],
                    SYNCED_AT = source.SYNCED_AT,
                    FLAGS = source.FLAGS,
                    UPDATED_AT = source.UPDATED_AT
            WHEN NOT MATCHED THEN
                INSERT (AL_NOME, [DATA], ISO_WEEK, PRECO_CALC, PRECO_FINAL, [SYNC], SYNCED_AT, FLAGS, UPDATED_AT)
                VALUES (source.AL_NOME, source.[DATA], source.ISO_WEEK, source.PRECO_CALC, source.PRECO_FINAL, source.[SYNC], source.SYNCED_AT, source.FLAGS, source.UPDATED_AT);
            """
        )
        db.session.execute(merge_sql, rows_to_upsert)
        db.session.commit()

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_rows": total_rows,
        "changed_rows": len(rows_to_upsert),
        "skipped_threshold": skipped_threshold,
    }


def _load_ui_alojamentos():
    ensure_pricing_schema(db.session)
    rows = db.session.execute(
        text(
            """
            SELECT DISTINCT LTRIM(RTRIM(pa.AL_NOME)) AS AL_NOME
            FROM dbo.PR_ALOJAMENTO pa
            WHERE ISNULL(pa.ATIVO, 0) = 1
            ORDER BY AL_NOME
            """
        )
    ).fetchall()
    return [row[0] for row in rows]


def _ensure_pricing_alojamentos_registered(session):
    ensure_pricing_schema(session)

    default_profile_id = session.execute(
        text(
            """
            SELECT TOP 1 PERFIL_ID
            FROM dbo.PR_PERFIL
            ORDER BY CASE WHEN UPPER(LTRIM(RTRIM(ISNULL(NOME, '')))) = 'BASE' THEN 0 ELSE 1 END, PERFIL_ID ASC
            """
        )
    ).scalar()
    if not default_profile_id:
        raise ValueError("Nao existe PERFIL base em PR_PERFIL.")

    missing_rows = session.execute(
        text(
            """
            SELECT
                al.NOME AS AL_NOME_RAW,
                LTRIM(RTRIM(ISNULL(al.NOME, ''))) AS AL_NOME,
                UPPER(LTRIM(RTRIM(ISNULL(al.TIPO, 'GESTAO')))) AS REGIME_SUGERIDO
            FROM dbo.AL al
            LEFT JOIN dbo.PR_ALOJAMENTO pa
              ON pa.AL_NOME = al.NOME
            WHERE pa.AL_NOME IS NULL
              AND LTRIM(RTRIM(ISNULL(al.NOME, ''))) <> ''
              AND ISNULL(al.INATIVO, 0) = 0
            ORDER BY LTRIM(RTRIM(ISNULL(al.NOME, ''))) ASC
            """
        )
    ).mappings().all()

    created = []
    for row in missing_rows:
        raw_name = row.get("AL_NOME_RAW")
        normalized_name = _normalize_alojamento(row.get("AL_NOME"))
        if not raw_name or not normalized_name:
            continue
        regime = str(row.get("REGIME_SUGERIDO") or "GESTAO").strip().upper()
        if regime not in {"GESTAO", "EXPLORACAO"}:
            regime = "GESTAO"
        session.execute(
            text(
                """
                INSERT INTO dbo.PR_ALOJAMENTO
                (
                    AL_NOME, PERFIL_ID, REGIME, PRECO_MIN, PRECO_BASE, PRECO_MAX,
                    LAST_MIN_DISC, LAST_MIN_DAYS, SYNC, ATIVO
                )
                VALUES
                (
                    :alojamento, :perfil_id, :regime, 0, 0, 0,
                    0, 0, 0, 1
                )
                """
            ),
            {
                "alojamento": raw_name,
                "perfil_id": int(default_profile_id),
                "regime": regime,
            },
        )
        created.append(normalized_name)

    if created:
        session.commit()
    return created


def _load_alojamento_config(alojamento):
    ensure_pricing_schema(db.session)
    alojamento = _normalize_alojamento(alojamento)
    if not alojamento:
        raise ValueError("Alojamento em falta.")

    _ensure_pricing_alojamentos_registered(db.session)

    row = db.session.execute(
        text(
            """
            SELECT
                pa.AL_NOME,
                pa.PERFIL_ID,
                pa.REGIME,
                pa.PRECO_MIN,
                pa.PRECO_BASE,
                pa.PRECO_MAX,
                ISNULL(pa.LAST_MIN_DISC, 0) AS LAST_MIN_DISC,
                ISNULL(pa.LAST_MIN_DAYS, 0) AS LAST_MIN_DAYS,
                ISNULL(pa.SYNC, 0) AS SYNC,
                ISNULL(pa.ATIVO, 0) AS ATIVO,
                ISNULL(pp.NOME, '') AS PERFIL_NOME,
                ISNULL(al.TIPOLOGIA, '') AS TIPOLOGIA
            FROM dbo.PR_ALOJAMENTO pa
            LEFT JOIN dbo.PR_PERFIL pp ON pp.PERFIL_ID = pa.PERFIL_ID
            LEFT JOIN dbo.AL al ON al.NOME = pa.AL_NOME
            WHERE pa.AL_NOME = :alojamento
            """
        ),
        {"alojamento": alojamento},
    ).mappings().first()
    if not row:
        raise ValueError("PR_ALOJAMENTO nao encontrado para o alojamento selecionado.")

    profile_rows = db.session.execute(
        text(
            """
            SELECT PERFIL_ID, NOME
            FROM dbo.PR_PERFIL
            ORDER BY NOME ASC, PERFIL_ID ASC
            """
        )
    ).mappings().all()

    return {
        "alojamento": _normalize_alojamento(row.get("AL_NOME")),
        "perfil_id": int(row.get("PERFIL_ID")),
        "perfil_nome": row.get("PERFIL_NOME") or "",
        "regime": row.get("REGIME") or "GESTAO",
        "tipologia": row.get("TIPOLOGIA") or "",
        "preco_min": _to_float(row.get("PRECO_MIN")),
        "preco_base": _to_float(row.get("PRECO_BASE")),
        "preco_max": _to_float(row.get("PRECO_MAX")),
        "last_min_disc": _to_float(row.get("LAST_MIN_DISC")),
        "last_min_days": int(row.get("LAST_MIN_DAYS") or 0),
        "sync": bool(row.get("SYNC")),
        "ativo": bool(row.get("ATIVO")),
        "profiles": [
            {"perfil_id": int(item["PERFIL_ID"]), "nome": item.get("NOME") or ""}
            for item in profile_rows
        ],
    }


def _suggest_alojamento_base_price(alojamento):
    ensure_pricing_schema(db.session)
    alojamento = _normalize_alojamento(alojamento)
    if not alojamento:
        raise ValueError("Alojamento em falta.")

    exists = db.session.execute(
        text("SELECT COUNT(*) FROM dbo.PR_ALOJAMENTO WHERE AL_NOME = :alojamento"),
        {"alojamento": alojamento},
    ).scalar_one()
    if int(exists or 0) == 0:
        raise ValueError("PR_ALOJAMENTO nao encontrado para o alojamento selecionado.")

    seasonality_rows = db.session.execute(
        text("SELECT MES, INDICE FROM dbo.PR_SAZONAL_MES")
    ).mappings().all()
    seasonality = {
        int(row["MES"]): (_safe_decimal(row.get("INDICE"), "100") / Decimal("100"))
        for row in seasonality_rows
    }

    end_date = date.today()
    start_date = end_date - timedelta(days=365)
    rows = db.session.execute(
        text(
            """
            SELECT
                RS.DATAIN,
                RS.DATAOUT,
                RS.ESTADIA,
                RS.NOITES
            FROM dbo.RS RS
            WHERE RS.ALOJAMENTO = :alojamento
              AND RS.DATAIN IS NOT NULL
              AND RS.DATAOUT IS NOT NULL
              AND ISNULL(RS.CANCELADA, 0) = 0
              AND RS.NOITES IS NOT NULL
              AND RS.NOITES > 0
              AND RS.ESTADIA IS NOT NULL
              AND RS.DATAOUT > :start_date
              AND RS.DATAIN <= :end_date
            """
        ),
        {"alojamento": alojamento, "start_date": start_date, "end_date": end_date},
    ).mappings().all()

    normalized_sum = Decimal("0")
    normalized_nights = 0

    for row in rows:
        nightly_price = _safe_decimal(row.get("ESTADIA"), "0") / _safe_decimal(row.get("NOITES"), "1")
        stay_start = max(row.get("DATAIN"), start_date)
        stay_end_exclusive = min(row.get("DATAOUT"), end_date + timedelta(days=1))
        if not stay_start or not stay_end_exclusive or stay_start >= stay_end_exclusive:
            continue

        cursor = stay_start
        while cursor < stay_end_exclusive:
            month_factor = seasonality.get(cursor.month, Decimal("1"))
            if month_factor > 0:
                normalized_sum += nightly_price / month_factor
                normalized_nights += 1
            cursor += timedelta(days=1)

    suggested = (
        _round_price((normalized_sum / Decimal(normalized_nights)) * Decimal("1.20"))
        if normalized_nights
        else Decimal("0")
    )
    return {
        "alojamento": alojamento,
        "suggested_preco_base": _to_float(suggested),
        "source_nights": normalized_nights,
        "window_start": start_date.isoformat(),
        "window_end": end_date.isoformat(),
    }


def _load_pricing_settings_state():
    ensure_pricing_schema(db.session)

    profile_rows = db.session.execute(
        text(
            """
            SELECT
                p.PERFIL_ID,
                p.NOME,
                p.K_PICKUP,
                p.LIM_AJUSTE_MIN,
                p.LIM_AJUSTE_MAX,
                (
                    SELECT COUNT(*)
                    FROM dbo.PR_ALOJAMENTO pa
                    WHERE pa.PERFIL_ID = p.PERFIL_ID
                ) AS LINKED_ALOJAMENTOS
            FROM dbo.PR_PERFIL p
            ORDER BY p.NOME ASC, p.PERFIL_ID ASC
            """
        )
    ).mappings().all()

    seasonality_rows = db.session.execute(
        text(
            """
            SELECT MES, INDICE, ISNULL(NOTA, '') AS NOTA
            FROM dbo.PR_SAZONAL_MES
            ORDER BY MES ASC
            """
        )
    ).mappings().all()

    dow_rows = db.session.execute(
        text(
            """
            SELECT PERFIL_ID, DOW, FATOR
            FROM dbo.PR_DIA_SEMANA_FATOR
            ORDER BY DOW ASC, PERFIL_ID ASC
            """
        )
    ).mappings().all()

    profiles = [
        {
            "perfil_id": int(row["PERFIL_ID"]),
            "nome": row.get("NOME") or "",
            "k_pickup": _to_float(row.get("K_PICKUP")),
            "lim_ajuste_min": _to_float(row.get("LIM_AJUSTE_MIN")),
            "lim_ajuste_max": _to_float(row.get("LIM_AJUSTE_MAX")),
            "linked_alojamentos": int(row.get("LINKED_ALOJAMENTOS") or 0),
        }
        for row in profile_rows
    ]

    seasonality = [
        {
            "mes": int(row["MES"]),
            "indice": _to_float(row.get("INDICE")),
            "nota": row.get("NOTA") or "",
        }
        for row in seasonality_rows
    ]

    dow_lookup = {}
    for row in dow_rows:
        dow_lookup[(int(row["PERFIL_ID"]), int(row["DOW"]))] = _to_float(row.get("FATOR"))

    dow_matrix = []
    dow_labels = {
        1: "Seg",
        2: "Ter",
        3: "Qua",
        4: "Qui",
        5: "Sex",
        6: "Sab",
        7: "Dom",
    }
    for dow in range(1, 8):
        dow_matrix.append(
            {
                "dow": dow,
                "label": dow_labels[dow],
                "values": {
                    str(profile["perfil_id"]): dow_lookup.get((profile["perfil_id"], dow), 1.0)
                    for profile in profiles
                },
            }
        )

    return {
        "profiles": profiles,
        "seasonality": seasonality,
        "dow_matrix": dow_matrix,
    }


PICKUP_CURVE_SCOPE_OPTIONS = {
    "weekly": {"kind": "weekly", "label": "Semanal"},
    "monthly_high": {"kind": "monthly", "season": "ALTA", "label": "Mensal · High Season"},
    "monthly_mid": {"kind": "monthly", "season": "MID", "label": "Mensal · Mid Season"},
    "monthly_low": {"kind": "monthly", "season": "BAIXA", "label": "Mensal · Low Season"},
}
PICKUP_CURVE_HORIZON_OPTIONS = (60, 90, 120, 150, 180)
PICKUP_CURVE_EXPLORACAO_VALUE = "__EXPLORACAO__"
PICKUP_CURVE_EXPLORACAO_LABEL = "EXPLORACAO"


def _validate_pickup_curve_scope(scope):
    key = str(scope or "").strip().lower()
    config = PICKUP_CURVE_SCOPE_OPTIONS.get(key)
    if not config:
        raise ValueError("Scope de curva inválido.")
    return key, config


def _validate_pickup_curve_horizon(value):
    try:
        horizon_days = int(value)
    except Exception as exc:
        raise ValueError("Horizonte inválido.") from exc
    if horizon_days not in PICKUP_CURVE_HORIZON_OPTIONS:
        raise ValueError("Horizonte inválido.")
    return horizon_days


def _pickup_curve_alojamento_rows():
    ensure_pricing_schema(db.session)
    rows = db.session.execute(
        text(
            """
            SELECT DISTINCT
                LTRIM(RTRIM(ISNULL(pa.AL_NOME, ''))) AS AL_NOME,
                UPPER(LTRIM(RTRIM(ISNULL(al.TIPO, '')))) AS REGIME
            FROM dbo.PR_ALOJAMENTO pa
            LEFT JOIN dbo.AL al
              ON al.NOME = pa.AL_NOME
            WHERE ISNULL(pa.ATIVO, 0) = 1
              AND LTRIM(RTRIM(ISNULL(pa.AL_NOME, ''))) <> ''
            ORDER BY LTRIM(RTRIM(ISNULL(pa.AL_NOME, ''))) ASC
            """
        )
    ).mappings().all()
    return [
        {
            "alojamento": _normalize_alojamento(row.get("AL_NOME")),
            "regime": str(row.get("REGIME") or "").strip().upper(),
        }
        for row in rows
        if _normalize_alojamento(row.get("AL_NOME"))
    ]


def _pickup_curve_alojamento_options():
    rows = _pickup_curve_alojamento_rows()
    options = []
    if any(item["regime"] == "EXPLORACAO" for item in rows):
        options.append({"value": PICKUP_CURVE_EXPLORACAO_VALUE, "label": PICKUP_CURVE_EXPLORACAO_LABEL})
    options.extend({"value": item["alojamento"], "label": item["alojamento"]} for item in rows)
    return options


def _resolve_pickup_curve_target(alojamento):
    raw = str(alojamento or "").strip()
    rows = _pickup_curve_alojamento_rows()
    if raw == PICKUP_CURVE_EXPLORACAO_VALUE:
        items = [item["alojamento"] for item in rows if item["regime"] == "EXPLORACAO"]
        return {
            "value": PICKUP_CURVE_EXPLORACAO_VALUE,
            "label": PICKUP_CURVE_EXPLORACAO_LABEL,
            "items": items,
        }

    normalized = _normalize_alojamento(raw)
    return {
        "value": normalized,
        "label": normalized,
        "items": [normalized] if normalized else [],
    }


def _pickup_curve_grid(horizon_days):
    return list(range(horizon_days, -1, -5))


def _pickup_curve_source_points(scope, perfil_id=None):
    scope_key, scope_config = _validate_pickup_curve_scope(scope)
    if scope_config["kind"] == "weekly":
        if perfil_id is None:
            raise ValueError("O perfil é obrigatório para a curva semanal.")
        rows = db.session.execute(
            text(
                """
                SELECT LEAD_DAYS, OCUP_ALVO
                FROM dbo.PR_PICKUP_CURVE
                WHERE PERFIL_ID = :perfil_id
                ORDER BY LEAD_DAYS ASC
                """
            ),
            {"perfil_id": int(perfil_id)},
        ).mappings().all()
    else:
        rows = db.session.execute(
            text(
                """
                SELECT LEAD_DAYS, OCUP_ALVO
                FROM dbo.PR_PICKUP_CURVE_MENSAL
                WHERE TEMPORADA = :temporada
                ORDER BY LEAD_DAYS ASC
                """
            ),
            {"temporada": scope_config["season"]},
        ).mappings().all()

    return [(int(row["LEAD_DAYS"]), _safe_decimal(row.get("OCUP_ALVO"), "0")) for row in rows]


def _default_pickup_curve_horizon(scope, perfil_id=None):
    source_points = _pickup_curve_source_points(scope, perfil_id=perfil_id)
    if not source_points:
        return PICKUP_CURVE_HORIZON_OPTIONS[1]

    max_lead_days = max(lead_days for lead_days, _ in source_points)
    if max_lead_days in PICKUP_CURVE_HORIZON_OPTIONS:
        return max_lead_days

    for option in PICKUP_CURVE_HORIZON_OPTIONS:
        if option >= max_lead_days:
            return option
    return PICKUP_CURVE_HORIZON_OPTIONS[-1]


def _pickup_curve_period_options(scope, horizon_days, today_value=None):
    scope_key, scope_config = _validate_pickup_curve_scope(scope)
    horizon_days = _validate_pickup_curve_horizon(horizon_days)
    today_value = today_value or date.today()
    horizon_end = today_value + timedelta(days=horizon_days)

    if scope_config["kind"] == "weekly":
        week_start, _ = _week_bounds(today_value)
        last_week_start, _ = _week_bounds(horizon_end)
        options = []
        cursor = week_start
        while cursor <= last_week_start:
            iso_year, iso_week, _ = cursor.isocalendar()
            options.append(
                {
                    "value": f"{iso_year}-W{iso_week:02d}",
                    "label": f"Semana {iso_week:02d}",
                    "start_date": cursor.isoformat(),
                }
            )
            cursor += timedelta(days=7)
        return options

    month_names = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
        7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
    }
    cursor = today_value.replace(day=1)
    last_month = horizon_end.replace(day=1)
    options = []
    while cursor <= last_month:
        options.append(
            {
                "value": f"{cursor.year}-{cursor.month:02d}",
                "label": f"{month_names[cursor.month]} {cursor.year}",
                "start_date": cursor.isoformat(),
            }
        )
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)
    return options


def _parse_pickup_curve_period(scope, period_value):
    scope_key, scope_config = _validate_pickup_curve_scope(scope)
    raw = str(period_value or "").strip()
    if not raw:
        raise ValueError("Período em falta.")

    if scope_config["kind"] == "weekly":
        if "-W" not in raw:
            raise ValueError("Semana inválida.")
        year_raw, week_raw = raw.split("-W", 1)
        try:
            iso_year = int(year_raw)
            iso_week = int(week_raw)
            period_start = date.fromisocalendar(iso_year, iso_week, 1)
        except Exception as exc:
            raise ValueError("Semana inválida.") from exc
        period_end = period_start + timedelta(days=6)
        return {
            "value": raw,
            "label": f"Semana {iso_week:02d}",
            "start_date": period_start,
            "end_date": period_end,
            "kind": "weekly",
        }

    try:
        year_raw, month_raw = raw.split("-", 1)
        period_start = date(int(year_raw), int(month_raw), 1)
    except Exception as exc:
        raise ValueError("Mês inválido.") from exc
    period_end = _month_bounds(period_start)[1]
    return {
        "value": raw,
        "label": f"{period_start.month:02d}/{period_start.year}",
        "start_date": period_start,
        "end_date": period_end,
        "kind": "monthly",
    }


def _period_occupancy_pct(alojamento, start_date, end_date):
    target = _resolve_pickup_curve_target(alojamento)
    target_items = [item for item in target["items"] if item]
    if not target_items:
        return Decimal("0")

    rows = db.session.execute(
        text(
            """
            SELECT
                LTRIM(RTRIM(ISNULL(RS.ALOJAMENTO, ''))) AS ALOJAMENTO,
                CAST(RS.DATAIN AS date) AS DATA_INI,
                CAST(RS.DATAOUT AS date) AS DATA_FIM
            FROM dbo.RS
            WHERE LTRIM(RTRIM(ISNULL(RS.ALOJAMENTO, ''))) IN :alojamentos
              AND RS.DATAIN IS NOT NULL
              AND RS.DATAOUT IS NOT NULL
              AND ISNULL(RS.CANCELADA, 0) = 0
              AND CAST(RS.DATAOUT AS date) > :start_date
              AND CAST(RS.DATAIN AS date) <= :end_date
            """
        ).bindparams(bindparam("alojamentos", expanding=True)),
        {"alojamentos": target_items, "start_date": start_date, "end_date": end_date},
    ).mappings().all()

    occupied_slots = set()
    period_end_exclusive = end_date + timedelta(days=1)
    for row in rows:
        stay_start = max(row.get("DATA_INI"), start_date)
        stay_end_exclusive = min(row.get("DATA_FIM"), period_end_exclusive)
        if not stay_start or not stay_end_exclusive or stay_start >= stay_end_exclusive:
            continue
        aloj_key = _normalize_alojamento(row.get("ALOJAMENTO"))
        cursor = stay_start
        while cursor < stay_end_exclusive:
            occupied_slots.add((aloj_key, cursor))
            cursor += timedelta(days=1)

    total_days = (end_date - start_date).days + 1
    if total_days <= 0:
        return Decimal("0")
    total_slots = total_days * len(target_items)
    if total_slots <= 0:
        return Decimal("0")
    return (Decimal(len(occupied_slots)) / Decimal(total_slots)) * Decimal("100")


def _period_occupancy_pct_by_booking_date(alojamento, start_date, end_date, booked_until):
    target = _resolve_pickup_curve_target(alojamento)
    target_items = [item for item in target["items"] if item]
    if not target_items:
        return Decimal("0")

    rows = db.session.execute(
        text(
            """
            SELECT
                LTRIM(RTRIM(ISNULL(RS.ALOJAMENTO, ''))) AS ALOJAMENTO,
                CAST(RS.DATAIN AS date) AS DATA_INI,
                CAST(RS.DATAOUT AS date) AS DATA_FIM
            FROM dbo.RS
            WHERE LTRIM(RTRIM(ISNULL(RS.ALOJAMENTO, ''))) IN :alojamentos
              AND RS.DATAIN IS NOT NULL
              AND RS.DATAOUT IS NOT NULL
              AND RS.RDATA IS NOT NULL
              AND ISNULL(RS.CANCELADA, 0) = 0
              AND CAST(RS.RDATA AS date) <= :booked_until
              AND CAST(RS.DATAOUT AS date) > :start_date
              AND CAST(RS.DATAIN AS date) <= :end_date
            """
        ).bindparams(bindparam("alojamentos", expanding=True)),
        {
            "alojamentos": target_items,
            "booked_until": booked_until,
            "start_date": start_date,
            "end_date": end_date,
        },
    ).mappings().all()

    occupied_slots = set()
    period_end_exclusive = end_date + timedelta(days=1)
    for row in rows:
        stay_start = max(row.get("DATA_INI"), start_date)
        stay_end_exclusive = min(row.get("DATA_FIM"), period_end_exclusive)
        if not stay_start or not stay_end_exclusive or stay_start >= stay_end_exclusive:
            continue
        aloj_key = _normalize_alojamento(row.get("ALOJAMENTO"))
        cursor = stay_start
        while cursor < stay_end_exclusive:
            occupied_slots.add((aloj_key, cursor))
            cursor += timedelta(days=1)

    total_days = (end_date - start_date).days + 1
    if total_days <= 0:
        return Decimal("0")
    total_slots = total_days * len(target_items)
    if total_slots <= 0:
        return Decimal("0")
    return (Decimal(len(occupied_slots)) / Decimal(total_slots)) * Decimal("100")


def _load_pickup_curve_comparison(scope, horizon_days, alojamento=None, period_value=None, perfil_id=None):
    scope_key, scope_config = _validate_pickup_curve_scope(scope)
    horizon_days = _validate_pickup_curve_horizon(horizon_days)
    period = _parse_pickup_curve_period(scope_key, period_value)
    target = _resolve_pickup_curve_target(alojamento)
    source_points = _pickup_curve_source_points(scope_key, perfil_id=perfil_id)
    grid = _pickup_curve_grid(horizon_days)
    today_value = date.today()
    lead_days = (period["start_date"] - today_value).days
    target_occ = _interpolate_curve(source_points, lead_days) if source_points else Decimal("0")
    real_occ = _period_occupancy_pct_by_booking_date(alojamento, period["start_date"], period["end_date"], today_value)
    deviation = real_occ - target_occ
    nearest_lead_days = min(grid, key=lambda item: abs(item - lead_days)) if grid else 0
    actual_points = []
    for point_lead_days in grid:
        booked_until = period["start_date"] - timedelta(days=point_lead_days)
        known = booked_until <= today_value
        actual_pct = _period_occupancy_pct_by_booking_date(
            alojamento,
            period["start_date"],
            period["end_date"],
            booked_until,
        )
        actual_points.append(
            {
                "lead_days": int(point_lead_days),
                "booked_until": booked_until.isoformat(),
                "known": bool(known),
                "real_occ": _to_float(actual_pct.quantize(Decimal("0.01"))),
                "target_occ": _to_float(_interpolate_curve(source_points, point_lead_days).quantize(Decimal("0.01"))) if source_points else 0,
            }
        )

    return {
        "alojamento": target["label"],
        "period_value": period["value"],
        "period_label": period["label"],
        "period_start": period["start_date"].isoformat(),
        "period_end": period["end_date"].isoformat(),
        "lead_days": int(lead_days),
        "booked_until": today_value.isoformat(),
        "nearest_lead_days": int(nearest_lead_days),
        "target_occ": _to_float(target_occ.quantize(Decimal("0.01"))),
        "real_occ": _to_float(real_occ.quantize(Decimal("0.01"))),
        "deviation": _to_float(deviation.quantize(Decimal("0.01"))),
        "kind": scope_config["kind"],
        "actual_points": actual_points,
    }


def _pickup_curve_profiles():
    ensure_pricing_schema(db.session)
    rows = db.session.execute(
        text(
            """
            SELECT PERFIL_ID, NOME
            FROM dbo.PR_PERFIL
            ORDER BY NOME ASC, PERFIL_ID ASC
            """
        )
    ).mappings().all()
    return [{"perfil_id": int(row["PERFIL_ID"]), "nome": row.get("NOME") or ""} for row in rows]


def _load_pickup_curve_points(scope, horizon_days, perfil_id=None):
    ensure_pricing_schema(db.session)
    scope_key, scope_config = _validate_pickup_curve_scope(scope)
    if horizon_days in (None, ""):
        horizon_days = _default_pickup_curve_horizon(scope_key, perfil_id=perfil_id)
    else:
        horizon_days = _validate_pickup_curve_horizon(horizon_days)

    source_points = _pickup_curve_source_points(scope_key, perfil_id=perfil_id)

    points = []
    for lead_days in _pickup_curve_grid(horizon_days):
        value = _interpolate_curve(source_points, lead_days)
        if source_points and lead_days > source_points[-1][0]:
            value = source_points[-1][1]
        points.append({"lead_days": int(lead_days), "ocup_alvo": _to_float(value.quantize(Decimal("0.01")))})

    return {
        "scope": scope_key,
        "label": scope_config["label"],
        "kind": scope_config["kind"],
        "season": scope_config.get("season"),
        "perfil_id": int(perfil_id) if perfil_id is not None else None,
        "horizon_days": horizon_days,
        "points": points,
        "source_points": [
            {"lead_days": int(lead_days), "ocup_alvo": _to_float(value.quantize(Decimal("0.01")))}
            for lead_days, value in source_points
        ],
    }


def _save_pickup_curve_points(scope, horizon_days, points, perfil_id=None):
    ensure_pricing_schema(db.session)
    scope_key, scope_config = _validate_pickup_curve_scope(scope)
    horizon_days = _validate_pickup_curve_horizon(horizon_days)
    expected_days = _pickup_curve_grid(horizon_days)

    if scope_config["kind"] == "weekly":
        if perfil_id is None:
            raise ValueError("O perfil é obrigatório para a curva semanal.")
        perfil_id = int(perfil_id)
        exists = db.session.execute(
            text("SELECT COUNT(*) FROM dbo.PR_PERFIL WHERE PERFIL_ID = :perfil_id"),
            {"perfil_id": perfil_id},
        ).scalar_one()
        if int(exists or 0) == 0:
            raise ValueError("Perfil não encontrado.")

    if not isinstance(points, list):
        raise ValueError("Formato de pontos inválido.")

    normalized = {}
    for item in points:
        try:
            lead_days = int(item.get("lead_days"))
        except Exception as exc:
            raise ValueError("Lead day inválido.") from exc
        if lead_days not in expected_days:
            raise ValueError("Os pontos têm de respeitar a grelha de 5 em 5 dias.")
        ocup = _safe_decimal(item.get("ocup_alvo"), "0")
        if ocup < 0 or ocup > 100:
            raise ValueError("OCUP_ALVO tem de estar entre 0 e 100.")
        normalized[lead_days] = ocup.quantize(Decimal("0.01"))

    if sorted(normalized.keys(), reverse=True) != expected_days:
        raise ValueError("A curva tem de incluir todos os pontos do horizonte selecionado.")

    if scope_config["kind"] == "weekly":
        db.session.execute(
            text("DELETE FROM dbo.PR_PICKUP_CURVE WHERE PERFIL_ID = :perfil_id"),
            {"perfil_id": perfil_id},
        )
        for lead_days in expected_days:
            db.session.execute(
                text(
                    """
                    INSERT INTO dbo.PR_PICKUP_CURVE (PERFIL_ID, LEAD_DAYS, OCUP_ALVO)
                    VALUES (:perfil_id, :lead_days, :ocup_alvo)
                    """
                ),
                {"perfil_id": perfil_id, "lead_days": lead_days, "ocup_alvo": normalized[lead_days]},
            )
    else:
        db.session.execute(
            text("DELETE FROM dbo.PR_PICKUP_CURVE_MENSAL WHERE TEMPORADA = :temporada"),
            {"temporada": scope_config["season"]},
        )
        for lead_days in expected_days:
            db.session.execute(
                text(
                    """
                    INSERT INTO dbo.PR_PICKUP_CURVE_MENSAL (TEMPORADA, LEAD_DAYS, OCUP_ALVO)
                    VALUES (:temporada, :lead_days, :ocup_alvo)
                    """
                ),
                {"temporada": scope_config["season"], "lead_days": lead_days, "ocup_alvo": normalized[lead_days]},
            )

    db.session.commit()
    return _load_pickup_curve_points(scope_key, horizon_days, perfil_id=perfil_id)


def _load_pricing_events_state():
    ensure_pricing_schema(db.session)

    event_rows = db.session.execute(
        text(
            """
            SELECT
                EVENTO_ID,
                NOME,
                MMDD_INI,
                MMDD_FIM,
                FATOR,
                PRIORIDADE,
                ISNULL(ATIVO, 0) AS ATIVO
            FROM dbo.PR_EVENTO
            ORDER BY PRIORIDADE DESC, NOME ASC, EVENTO_ID ASC
            """
        )
    ).mappings().all()

    year_rows = db.session.execute(
        text(
            """
            SELECT
                EVENTO_ID,
                ANO,
                DATA_INI,
                DATA_FIM,
                FATOR_OVERRIDE,
                ISNULL(ATIVO, 0) AS ATIVO,
                ISNULL(NOTA, '') AS NOTA
            FROM dbo.PR_EVENTO_ANO
            ORDER BY ANO DESC, EVENTO_ID ASC
            """
        )
    ).mappings().all()

    by_event = {}
    for row in year_rows:
        by_event.setdefault(int(row["EVENTO_ID"]), []).append(
            {
                "evento_id": int(row["EVENTO_ID"]),
                "ano": int(row["ANO"]),
                "data_ini": row.get("DATA_INI").isoformat() if row.get("DATA_INI") else "",
                "data_fim": row.get("DATA_FIM").isoformat() if row.get("DATA_FIM") else "",
                "fator_override": _to_float(row.get("FATOR_OVERRIDE")) if row.get("FATOR_OVERRIDE") is not None else None,
                "ativo": bool(row.get("ATIVO")),
                "nota": row.get("NOTA") or "",
            }
        )

    events = []
    for row in event_rows:
        event_id = int(row["EVENTO_ID"])
        events.append(
            {
                "evento_id": event_id,
                "nome": row.get("NOME") or "",
                "mmdd_ini": row.get("MMDD_INI") or "",
                "mmdd_fim": row.get("MMDD_FIM") or "",
                "fator": _to_float(row.get("FATOR")),
                "prioridade": int(row.get("PRIORIDADE") or 0),
                "ativo": bool(row.get("ATIVO")),
                "anos": by_event.get(event_id, []),
            }
        )

    return {"events": events}


def _load_pricing_promotions_state():
    ensure_pricing_schema(db.session)

    profile_rows = db.session.execute(
        text(
            """
            SELECT PERFIL_ID, NOME
            FROM dbo.PR_PERFIL
            ORDER BY NOME ASC, PERFIL_ID ASC
            """
        )
    ).mappings().all()

    promo_rows = db.session.execute(
        text(
            """
            SELECT
                P.PROMO_ID,
                P.PERFIL_ID,
                PF.NOME AS PERFIL_NOME,
                P.DATA_INI,
                P.DATA_FIM,
                P.DESCONTO_PCT,
                ISNULL(P.NOTA, '') AS NOTA,
                ISNULL(P.ATIVO, 0) AS ATIVO,
                P.CRIADO_EM,
                ISNULL(P.CRIADO_POR, '') AS CRIADO_POR,
                (
                    SELECT COUNT(*)
                    FROM dbo.PR_ALOJAMENTO AS PA
                    WHERE PA.PERFIL_ID = P.PERFIL_ID
                      AND ISNULL(PA.ATIVO, 0) = 1
                ) AS ALOJAMENTOS_COUNT
            FROM dbo.PR_PROMO AS P
            INNER JOIN dbo.PR_PERFIL AS PF
              ON PF.PERFIL_ID = P.PERFIL_ID
            ORDER BY
                ISNULL(P.ATIVO, 0) DESC,
                P.DATA_INI DESC,
                P.PROMO_ID DESC
            """
        )
    ).mappings().all()

    return {
        "profiles": [
            {
                "perfil_id": int(row["PERFIL_ID"]),
                "nome": row.get("NOME") or "",
            }
            for row in profile_rows
        ],
        "promotions": [
            {
                "promo_id": int(row["PROMO_ID"]),
                "perfil_id": int(row["PERFIL_ID"]),
                "perfil_nome": row.get("PERFIL_NOME") or "",
                "data_ini": row.get("DATA_INI").isoformat() if row.get("DATA_INI") else "",
                "data_fim": row.get("DATA_FIM").isoformat() if row.get("DATA_FIM") else "",
                "desconto_pct": _to_float(row.get("DESCONTO_PCT")),
                "nota": row.get("NOTA") or "",
                "ativo": bool(row.get("ATIVO")),
                "criado_em": row.get("CRIADO_EM").isoformat() if row.get("CRIADO_EM") else "",
                "criado_por": row.get("CRIADO_POR") or "",
                "alojamentos_count": int(row.get("ALOJAMENTOS_COUNT") or 0),
            }
            for row in promo_rows
        ],
    }


def _recalc_promotions_for_profiles(profile_ids, start_date, end_date):
    ensure_pricing_schema(db.session)
    valid_profile_ids = sorted({int(item) for item in (profile_ids or []) if item is not None})
    if not valid_profile_ids or not start_date or not end_date:
        return {
            "profiles": [],
            "alojamentos": [],
            "changed_rows": 0,
            "total_rows": 0,
            "skipped_threshold": 0,
        }

    placeholders = ", ".join(f":pf{idx}" for idx in range(len(valid_profile_ids)))
    rows = db.session.execute(
        text(
            f"""
            SELECT LTRIM(RTRIM(AL_NOME)) AS AL_NOME
            FROM dbo.PR_ALOJAMENTO
            WHERE ISNULL(ATIVO, 0) = 1
              AND PERFIL_ID IN ({placeholders})
            ORDER BY AL_NOME ASC
            """
        ),
        {f"pf{idx}": valid_profile_ids[idx] for idx in range(len(valid_profile_ids))},
    ).mappings().all()

    alojamentos = [_normalize_alojamento(row.get("AL_NOME")) for row in rows if _normalize_alojamento(row.get("AL_NOME"))]
    totals = {
        "profiles": valid_profile_ids,
        "alojamentos": alojamentos,
        "changed_rows": 0,
        "total_rows": 0,
        "skipped_threshold": 0,
    }
    for alojamento in alojamentos:
        result = recalculate_prices(alojamento=alojamento, from_date=start_date, to_date=end_date)
        totals["changed_rows"] += int(result.get("changed_rows") or 0)
        totals["total_rows"] += int(result.get("total_rows") or 0)
        totals["skipped_threshold"] += int(result.get("skipped_threshold") or 0)
    return totals


def _load_pricing_sync_monitor_state():
    ensure_pricing_schema(db.session)

    rows = db.session.execute(
        text(
            """
            SELECT
                LTRIM(RTRIM(D.AL_NOME)) AS Alojamento,
                COUNT(*) AS RegistosPorSincronizar,
                MIN(CAST(D.[DATA] AS date)) AS PrimeiraData,
                MAX(CAST(D.[DATA] AS date)) AS UltimaData
            FROM dbo.PR_CALC_DAY AS D
            JOIN dbo.PR_ALOJAMENTO AS P
              ON P.AL_NOME = D.AL_NOME
            JOIN dbo.AL AS AL
              ON AL.NOME = D.AL_NOME
            WHERE
                P.SYNC = 1
                AND ISNULL(D.SYNC, 0) = 0
                AND D.[DATA] >= CAST(GETDATE() AS date)
                AND D.[DATA] < DATEADD(day, 375, CAST(GETDATE() AS date))
                AND NOT EXISTS (
                    SELECT 1
                    FROM dbo.RS
                    WHERE RS.ALOJAMENTO = D.AL_NOME
                      AND ISNULL(RS.CANCELADA, 0) = 0
                      AND CAST(RS.DATAIN AS date) <= D.[DATA]
                      AND CAST(RS.DATAOUT AS date) > D.[DATA]
                )
            GROUP BY
                LTRIM(RTRIM(D.AL_NOME))
            ORDER BY
                LTRIM(RTRIM(D.AL_NOME)) ASC
            """
        )
    ).mappings().all()

    items = []
    totals = {
        "total_alojamentos": 0,
        "total_registos": 0,
        "primeira_data": "",
        "ultima_data": "",
    }
    robots = {
        robot["name"]: {
            "robot": robot["name"],
            "range": f'{robot["from"]}–{robot["to"]}',
            "total_alojamentos": 0,
            "total_registos": 0,
            "primeira_data": "",
            "ultima_data": "",
        }
        for robot in PRICING_SYNC_ROBOTS
    }

    overall_first = None
    overall_last = None

    for row in rows:
        alojamento = _normalize_alojamento(row.get("Alojamento"))
        count = int(row.get("RegistosPorSincronizar") or 0)
        first_date = row.get("PrimeiraData")
        last_date = row.get("UltimaData")
        robot_name = _pricing_sync_robot_for_alojamento(alojamento)
        item = {
            "robot": robot_name,
            "alojamento": alojamento,
            "registos": count,
            "primeira_data": _iso_or_empty(first_date),
            "ultima_data": _iso_or_empty(last_date),
        }
        items.append(item)

        totals["total_alojamentos"] += 1
        totals["total_registos"] += count

        if first_date and (overall_first is None or first_date < overall_first):
            overall_first = first_date
        if last_date and (overall_last is None or last_date > overall_last):
            overall_last = last_date

        robot_bucket = robots[robot_name]
        robot_bucket["total_alojamentos"] += 1
        robot_bucket["total_registos"] += count

        current_first = robot_bucket.get("_first")
        current_last = robot_bucket.get("_last")
        if first_date and (current_first is None or first_date < current_first):
            robot_bucket["_first"] = first_date
        if last_date and (current_last is None or last_date > current_last):
            robot_bucket["_last"] = last_date

    totals["primeira_data"] = _iso_or_empty(overall_first)
    totals["ultima_data"] = _iso_or_empty(overall_last)

    robot_items = []
    for robot in PRICING_SYNC_ROBOTS:
        bucket = robots[robot["name"]]
        robot_items.append(
            {
                "robot": bucket["robot"],
                "range": bucket["range"],
                "total_alojamentos": bucket["total_alojamentos"],
                "total_registos": bucket["total_registos"],
                "primeira_data": _iso_or_empty(bucket.get("_first")),
                "ultima_data": _iso_or_empty(bucket.get("_last")),
            }
        )

    return {
        "generated_at": datetime.utcnow().replace(microsecond=0).isoformat(),
        "totals": totals,
        "robots": robot_items,
        "rows": items,
    }


def _load_pricing_sync_monitor_alojamento_detail(alojamento):
    ensure_pricing_schema(db.session)

    alojamento_norm = _normalize_alojamento(alojamento)
    if not alojamento_norm:
        raise ValueError("Alojamento em falta.")

    today_value = date.today()
    month_start = today_value.replace(day=1)
    last_month_start = _add_months(month_start, 11)
    last_month_end = _month_bounds(last_month_start)[1]
    max_sync_day = today_value + timedelta(days=374)
    range_end = min(last_month_end, max_sync_day)

    rows = db.session.execute(
        text(
            """
            SELECT CAST(D.[DATA] AS date) AS Dia
            FROM dbo.PR_CALC_DAY AS D
            JOIN dbo.PR_ALOJAMENTO AS P
              ON P.AL_NOME = D.AL_NOME
            JOIN dbo.AL AS AL
              ON AL.NOME = D.AL_NOME
            WHERE
                LTRIM(RTRIM(D.AL_NOME)) = :alojamento
                AND P.SYNC = 1
                AND ISNULL(D.SYNC, 0) = 0
                AND D.[DATA] >= :date_from
                AND D.[DATA] <= :date_to
                AND NOT EXISTS (
                    SELECT 1
                    FROM dbo.RS
                    WHERE RS.ALOJAMENTO = D.AL_NOME
                      AND ISNULL(RS.CANCELADA, 0) = 0
                      AND CAST(RS.DATAIN AS date) <= D.[DATA]
                      AND CAST(RS.DATAOUT AS date) > D.[DATA]
                )
            ORDER BY CAST(D.[DATA] AS date) ASC
            """
        ),
        {
            "alojamento": alojamento_norm,
            "date_from": today_value,
            "date_to": range_end,
        },
    ).mappings().all()

    unsynced_dates = {_iso_or_empty(row.get("Dia")) for row in rows if row.get("Dia")}
    occupied_rows = db.session.execute(
        text(
            """
            SELECT
                CAST(RS.DATAIN AS date) AS DataIn,
                CAST(RS.DATAOUT AS date) AS DataOut
            FROM dbo.RS
            WHERE
                LTRIM(RTRIM(RS.ALOJAMENTO)) = :alojamento
                AND ISNULL(RS.CANCELADA, 0) = 0
                AND CAST(RS.DATAOUT AS date) > :date_from
                AND CAST(RS.DATAIN AS date) <= :date_to
            """
        ),
        {
            "alojamento": alojamento_norm,
            "date_from": today_value,
            "date_to": range_end,
        },
    ).mappings().all()

    occupied_dates = set()
    for row in occupied_rows:
        data_in = row.get("DataIn")
        data_out = row.get("DataOut")
        if not data_in or not data_out:
            continue
        cursor_day = max(data_in, today_value)
        last_day = min(data_out - timedelta(days=1), range_end)
        while cursor_day <= last_day:
            occupied_dates.add(cursor_day.isoformat())
            cursor_day += timedelta(days=1)

    months = []
    cursor = month_start
    for _ in range(12):
        current_start, current_end = _month_bounds(cursor)
        cells = []
        for _pad in range(current_start.weekday()):
            cells.append({"kind": "pad"})
        total_days = (current_end - current_start).days + 1
        for offset in range(total_days):
            day_value = current_start + timedelta(days=offset)
            iso_day = day_value.isoformat()
            in_scope = today_value <= day_value <= range_end
            cells.append(
                {
                    "kind": "day",
                    "date": iso_day,
                    "active": bool(in_scope),
                    "occupied": bool(in_scope and iso_day in occupied_dates),
                    "unsynced": bool(in_scope and iso_day in unsynced_dates),
                }
            )
        months.append(
            {
                "month_start": current_start.isoformat(),
                "label": current_start.strftime("%b %Y"),
                "unsynced_count": sum(1 for item in cells if item.get("unsynced")),
                "occupied_count": sum(1 for item in cells if item.get("occupied")),
                "cells": cells,
            }
        )
        cursor = _add_months(cursor, 1)

    return {
        "generated_at": datetime.utcnow().replace(microsecond=0).isoformat(),
        "alojamento": alojamento_norm,
        "date_from": today_value.isoformat(),
        "date_to": range_end.isoformat(),
        "total_unsynced": len(unsynced_dates),
        "total_occupied": len(occupied_dates),
        "months": months,
    }


def _load_event_cache_for_range(start_date, end_date):
    years = sorted({start_date.year, end_date.year})
    events = db.session.execute(
        text(
            """
            SELECT EVENTO_ID, NOME, MMDD_INI, MMDD_FIM, FATOR, PRIORIDADE
            FROM dbo.PR_EVENTO
            WHERE ISNULL(ATIVO, 0) = 1
            ORDER BY PRIORIDADE DESC, EVENTO_ID ASC
            """
        )
    ).mappings().all()

    event_years = {}
    if years:
        placeholders = ", ".join(f":y{idx}" for idx in range(len(years)))
        params = {f"y{idx}": years[idx] for idx in range(len(years))}
        rows = db.session.execute(
            text(
                f"""
                SELECT EVENTO_ID, ANO, DATA_INI, DATA_FIM, FATOR_OVERRIDE
                FROM dbo.PR_EVENTO_ANO
                WHERE ISNULL(ATIVO, 0) = 1
                  AND ANO IN ({placeholders})
                """
            ),
            params,
        ).mappings().all()
        event_years = {
            (int(row["EVENTO_ID"]), int(row["ANO"])): {
                "data_ini": row.get("DATA_INI"),
                "data_fim": row.get("DATA_FIM"),
                "fator_override": row.get("FATOR_OVERRIDE"),
            }
            for row in rows
        }

    return events, event_years


@pricing_bp.route("/planner")
@login_required
def pricing_planner():
    auto_created_alojamentos = _ensure_pricing_alojamentos_registered(db.session)
    alojamentos = _load_ui_alojamentos()
    return render_template(
        "pricing_planner.html",
        alojamentos=alojamentos,
        page_title="Price Manager",
        auto_created_alojamentos=auto_created_alojamentos,
    )


@pricing_bp.route("/sync-monitor")
@login_required
def pricing_sync_monitor():
    initial_state = _load_pricing_sync_monitor_state()
    return render_template("pricing_sync_monitor.html", page_title="Monitor de Sync", initial_state=initial_state)


@pricing_bp.route("/pickup-curves")
@login_required
def pricing_pickup_curves():
    alojamentos = _pickup_curve_alojamento_options()
    profiles = _pickup_curve_profiles()
    initial_state = {
        "scopes": [
            {"value": key, "label": config["label"], "kind": config["kind"], "season": config.get("season")}
            for key, config in PICKUP_CURVE_SCOPE_OPTIONS.items()
        ],
        "horizons": list(PICKUP_CURVE_HORIZON_OPTIONS),
        "profiles": profiles,
        "alojamentos": alojamentos,
        "default_scope": "monthly_high",
        "today": {
            "date": date.today().isoformat(),
            "iso_week": int(date.today().isocalendar()[1]),
            "month": int(date.today().month),
        },
    }
    return render_template("pickup_curves.html", initial_state=initial_state, page_title="Pickup Curves")


@pricing_bp.route("/settings")
@login_required
def pricing_settings():
    state = _load_pricing_settings_state()
    return render_template("pricing_settings.html", initial_state=state, page_title="Price Manager Config")


@pricing_bp.route("/events")
@login_required
def pricing_events():
    state = _load_pricing_events_state()
    return render_template("pricing_events.html", initial_state=state, page_title="Price Manager Events")


@pricing_bp.route("/promotions")
@login_required
def pricing_promotions():
    state = _load_pricing_promotions_state()
    return render_template("pricing_promotions.html", initial_state=state, page_title="Price Manager Promocoes")


@pricing_bp.route("/api/settings/state")
@login_required
def pricing_api_settings_state():
    return jsonify(_load_pricing_settings_state())


@pricing_bp.route("/api/sync-monitor")
@login_required
def pricing_api_sync_monitor():
    return jsonify(_load_pricing_sync_monitor_state())


@pricing_bp.route("/api/sync-monitor/detail")
@login_required
def pricing_api_sync_monitor_detail():
    try:
        alojamento = request.args.get("alojamento")
        return jsonify(_load_pricing_sync_monitor_alojamento_detail(alojamento))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@pricing_bp.route("/api/pickup-curves/state")
@login_required
def pricing_api_pickup_curves_state():
    try:
        scope = request.args.get("scope") or "monthly_high"
        horizon_days = request.args.get("horizon_days")
        perfil_id_raw = request.args.get("perfil_id")
        perfil_id = int(perfil_id_raw) if str(perfil_id_raw or "").strip() else None
        alojamento = str(request.args.get("alojamento") or "").strip()
        if horizon_days in (None, ""):
            horizon_days = _default_pickup_curve_horizon(scope, perfil_id=perfil_id)
        else:
            horizon_days = _validate_pickup_curve_horizon(horizon_days)
        period_options = _pickup_curve_period_options(scope, horizon_days)
        period_value = request.args.get("period_value") or (period_options[0]["value"] if period_options else "")
        payload = {
            "scopes": [
                {"value": key, "label": config["label"], "kind": config["kind"], "season": config.get("season")}
                for key, config in PICKUP_CURVE_SCOPE_OPTIONS.items()
            ],
            "horizons": list(PICKUP_CURVE_HORIZON_OPTIONS),
            "profiles": _pickup_curve_profiles(),
            "alojamentos": _pickup_curve_alojamento_options(),
            "period_options": period_options,
            "selected_period_value": period_value,
            "curve": _load_pickup_curve_points(scope, horizon_days, perfil_id=perfil_id),
            "comparison": None,
        }
        valid_period_values = {item["value"] for item in period_options}
        if period_value not in valid_period_values and period_options:
            period_value = period_options[0]["value"]
            payload["selected_period_value"] = period_value
        if alojamento and period_value:
            payload["comparison"] = _load_pickup_curve_comparison(
                scope,
                horizon_days,
                alojamento=alojamento,
                period_value=period_value,
                perfil_id=perfil_id,
            )
        return jsonify(payload)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@pricing_bp.route("/api/pickup-curves", methods=["POST"])
@login_required
def pricing_api_pickup_curves_save():
    payload = request.get_json(silent=True) or {}
    try:
        scope = payload.get("scope")
        horizon_days = payload.get("horizon_days")
        perfil_id_raw = payload.get("perfil_id")
        perfil_id = int(perfil_id_raw) if str(perfil_id_raw or "").strip() else None
        points = payload.get("points") or []
        curve = _save_pickup_curve_points(scope, horizon_days, points, perfil_id=perfil_id)
        return jsonify({"ok": True, "curve": curve})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@pricing_bp.route("/api/events/state")
@login_required
def pricing_api_events_state():
    return jsonify(_load_pricing_events_state())


@pricing_bp.route("/api/promotions/state")
@login_required
def pricing_api_promotions_state():
    return jsonify(_load_pricing_promotions_state())


@pricing_bp.route("/api/alojamento-config")
@login_required
def pricing_api_alojamento_config():
    try:
        return jsonify(_load_alojamento_config(request.args.get("alojamento")))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@pricing_bp.route("/api/alojamento-config/suggested-base")
@login_required
def pricing_api_alojamento_config_suggested_base():
    try:
        return jsonify(_suggest_alojamento_base_price(request.args.get("alojamento")))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@pricing_bp.route("/api/alojamento-config", methods=["POST"])
@login_required
def pricing_api_alojamento_config_save():
    ensure_pricing_schema(db.session)
    payload = request.get_json(silent=True) or request.form

    alojamento = _normalize_alojamento(payload.get("alojamento"))
    if not alojamento:
        return jsonify({"error": "Alojamento em falta."}), 400

    try:
        perfil_id = int(payload.get("perfil_id"))
    except Exception:
        return jsonify({"error": "PERFIL_ID invalido."}), 400

    regime = str(payload.get("regime") or "GESTAO").strip().upper()
    if not regime:
        regime = "GESTAO"
    preco_min = _safe_decimal(payload.get("preco_min"), "0")
    preco_base = _safe_decimal(payload.get("preco_base"), "0")
    preco_max = _safe_decimal(payload.get("preco_max"), "0")
    last_min_disc = _safe_decimal(payload.get("last_min_disc"), "0")
    try:
        last_min_days = int(payload.get("last_min_days") or 0)
    except Exception:
        return jsonify({"error": "LAST_MIN_DAYS invalido."}), 400
    sync = 1 if _as_bool(payload.get("sync")) else 0
    ativo = 1 if _as_bool(payload.get("ativo")) else 0

    if preco_min > preco_base or preco_base > preco_max:
        return jsonify({"error": "A regra PRECO_MIN <= PRECO_BASE <= PRECO_MAX tem de ser respeitada."}), 400
    if last_min_disc < 0:
        return jsonify({"error": "LAST_MIN_DISC nao pode ser negativo."}), 400
    if last_min_days < 0:
        return jsonify({"error": "LAST_MIN_DAYS nao pode ser negativo."}), 400

    exists = db.session.execute(
        text("SELECT COUNT(*) FROM dbo.PR_ALOJAMENTO WHERE AL_NOME = :alojamento"),
        {"alojamento": alojamento},
    ).scalar_one()
    if int(exists or 0) == 0:
        return jsonify({"error": "PR_ALOJAMENTO nao encontrado para o alojamento selecionado."}), 404

    db.session.execute(
        text(
            """
            UPDATE dbo.PR_ALOJAMENTO
            SET PERFIL_ID = :perfil_id,
                REGIME = :regime,
                PRECO_MIN = :preco_min,
                PRECO_BASE = :preco_base,
                PRECO_MAX = :preco_max,
                LAST_MIN_DISC = :last_min_disc,
                LAST_MIN_DAYS = :last_min_days,
                SYNC = :sync,
                ATIVO = :ativo
            WHERE AL_NOME = :alojamento
            """
        ),
        {
            "alojamento": alojamento,
            "perfil_id": perfil_id,
            "regime": regime,
            "preco_min": preco_min,
            "preco_base": preco_base,
            "preco_max": preco_max,
            "last_min_disc": last_min_disc,
            "last_min_days": last_min_days,
            "sync": sync,
            "ativo": ativo,
        },
    )
    db.session.commit()

    return jsonify({"ok": True, "config": _load_alojamento_config(alojamento)})


@pricing_bp.route("/api/events/base", methods=["POST"])
@login_required
def pricing_api_events_base_save():
    ensure_pricing_schema(db.session)
    payload = request.get_json(silent=True) or request.form

    evento_id_raw = payload.get("evento_id")
    evento_id = int(evento_id_raw) if str(evento_id_raw or "").strip() else None
    nome = str(payload.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "O nome do evento e obrigatorio."}), 400

    try:
        mmdd_ini = _normalize_mmdd(payload.get("mmdd_ini"), "MMDD_INI")
        mmdd_fim = _normalize_mmdd(payload.get("mmdd_fim"), "MMDD_FIM")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    fator = _safe_decimal(payload.get("fator"), "1")
    prioridade = int(payload.get("prioridade") or 0)
    ativo = 1 if _as_bool(payload.get("ativo")) else 0

    if evento_id is None:
        new_id = db.session.execute(
            text(
                """
                INSERT INTO dbo.PR_EVENTO (NOME, MMDD_INI, MMDD_FIM, FATOR, PRIORIDADE, ATIVO)
                OUTPUT INSERTED.EVENTO_ID
                VALUES (:nome, :mmdd_ini, :mmdd_fim, :fator, :prioridade, :ativo)
                """
            ),
            {
                "nome": nome,
                "mmdd_ini": mmdd_ini,
                "mmdd_fim": mmdd_fim,
                "fator": fator,
                "prioridade": prioridade,
                "ativo": ativo,
            },
        ).scalar_one()
        db.session.commit()
        return jsonify({"ok": True, "evento_id": int(new_id)})

    exists = db.session.execute(
        text("SELECT EVENTO_ID FROM dbo.PR_EVENTO WHERE EVENTO_ID = :evento_id"),
        {"evento_id": evento_id},
    ).scalar()
    if not exists:
        return jsonify({"error": "Evento nao encontrado."}), 404

    db.session.execute(
        text(
            """
            UPDATE dbo.PR_EVENTO
            SET NOME = :nome,
                MMDD_INI = :mmdd_ini,
                MMDD_FIM = :mmdd_fim,
                FATOR = :fator,
                PRIORIDADE = :prioridade,
                ATIVO = :ativo
            WHERE EVENTO_ID = :evento_id
            """
        ),
        {
            "evento_id": evento_id,
            "nome": nome,
            "mmdd_ini": mmdd_ini,
            "mmdd_fim": mmdd_fim,
            "fator": fator,
            "prioridade": prioridade,
            "ativo": ativo,
        },
    )
    db.session.commit()
    return jsonify({"ok": True, "evento_id": evento_id})


@pricing_bp.route("/api/events/base/<int:evento_id>", methods=["DELETE"])
@login_required
def pricing_api_events_base_delete(evento_id):
    ensure_pricing_schema(db.session)

    exists = db.session.execute(
        text("SELECT COUNT(*) FROM dbo.PR_EVENTO WHERE EVENTO_ID = :evento_id"),
        {"evento_id": evento_id},
    ).scalar_one()
    if int(exists or 0) == 0:
        return jsonify({"error": "Evento nao encontrado."}), 404

    db.session.execute(text("DELETE FROM dbo.PR_EVENTO_ANO WHERE EVENTO_ID = :evento_id"), {"evento_id": evento_id})
    db.session.execute(text("DELETE FROM dbo.PR_EVENTO WHERE EVENTO_ID = :evento_id"), {"evento_id": evento_id})
    db.session.commit()
    return jsonify({"ok": True})


@pricing_bp.route("/api/events/year", methods=["POST"])
@login_required
def pricing_api_events_year_save():
    ensure_pricing_schema(db.session)
    payload = request.get_json(silent=True) or request.form

    try:
        evento_id = int(payload.get("evento_id"))
        ano = int(payload.get("ano"))
    except Exception:
        return jsonify({"error": "evento_id e ano sao obrigatorios."}), 400

    data_ini = _parse_date(payload.get("data_ini"), "data_ini")
    data_fim = _parse_date(payload.get("data_fim"), "data_fim")
    if not data_ini or not data_fim:
        return jsonify({"error": "DATA_INI e DATA_FIM sao obrigatorias."}), 400
    if data_fim < data_ini:
        return jsonify({"error": "DATA_FIM nao pode ser inferior a DATA_INI."}), 400
    if data_ini.year != ano or data_fim.year != ano:
        return jsonify({"error": "As datas do override anual devem pertencer ao ANO indicado."}), 400

    fator_override_raw = payload.get("fator_override")
    fator_override = None if str(fator_override_raw or "").strip() == "" else _safe_decimal(fator_override_raw, "1")
    ativo = 1 if _as_bool(payload.get("ativo")) else 0
    nota = str(payload.get("nota") or "").strip()

    exists = db.session.execute(
        text("SELECT COUNT(*) FROM dbo.PR_EVENTO WHERE EVENTO_ID = :evento_id"),
        {"evento_id": evento_id},
    ).scalar_one()
    if int(exists or 0) == 0:
        return jsonify({"error": "Evento nao encontrado."}), 404

    db.session.execute(
        text(
            """
            MERGE dbo.PR_EVENTO_ANO AS target
            USING (
                SELECT
                    :evento_id AS EVENTO_ID,
                    :ano AS ANO,
                    :data_ini AS DATA_INI,
                    :data_fim AS DATA_FIM,
                    :fator_override AS FATOR_OVERRIDE,
                    :ativo AS ATIVO,
                    :nota AS NOTA
            ) AS source
            ON target.EVENTO_ID = source.EVENTO_ID
               AND target.ANO = source.ANO
            WHEN MATCHED THEN
                UPDATE SET
                    DATA_INI = source.DATA_INI,
                    DATA_FIM = source.DATA_FIM,
                    FATOR_OVERRIDE = source.FATOR_OVERRIDE,
                    ATIVO = source.ATIVO,
                    NOTA = source.NOTA
            WHEN NOT MATCHED THEN
                INSERT (EVENTO_ID, ANO, DATA_INI, DATA_FIM, FATOR_OVERRIDE, ATIVO, NOTA)
                VALUES (source.EVENTO_ID, source.ANO, source.DATA_INI, source.DATA_FIM, source.FATOR_OVERRIDE, source.ATIVO, source.NOTA);
            """
        ),
        {
            "evento_id": evento_id,
            "ano": ano,
            "data_ini": data_ini,
            "data_fim": data_fim,
            "fator_override": fator_override,
            "ativo": ativo,
            "nota": nota,
        },
    )
    db.session.commit()
    return jsonify({"ok": True, "evento_id": evento_id, "ano": ano})


@pricing_bp.route("/api/events/year/<int:evento_id>/<int:ano>", methods=["DELETE"])
@login_required
def pricing_api_events_year_delete(evento_id, ano):
    ensure_pricing_schema(db.session)
    exists = db.session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM dbo.PR_EVENTO_ANO
            WHERE EVENTO_ID = :evento_id
              AND ANO = :ano
            """
        ),
        {"evento_id": evento_id, "ano": ano},
    ).scalar_one()
    if int(exists or 0) == 0:
        return jsonify({"error": "Override anual nao encontrado."}), 404

    db.session.execute(
        text(
            """
            DELETE FROM dbo.PR_EVENTO_ANO
            WHERE EVENTO_ID = :evento_id
              AND ANO = :ano
            """
        ),
        {"evento_id": evento_id, "ano": ano},
    )
    db.session.commit()
    return jsonify({"ok": True})


@pricing_bp.route("/api/promotions", methods=["POST"])
@login_required
def pricing_api_promotions_save():
    ensure_pricing_schema(db.session)
    payload = request.get_json(silent=True) or request.form

    promo_id_raw = payload.get("promo_id")
    promo_id = int(promo_id_raw) if str(promo_id_raw or "").strip() else None

    try:
        perfil_id = int(payload.get("perfil_id"))
    except Exception:
        return jsonify({"error": "PERFIL_ID invalido."}), 400

    data_ini = _parse_date(payload.get("data_ini"), "data_ini")
    data_fim = _parse_date(payload.get("data_fim"), "data_fim")
    if not data_ini or not data_fim:
        return jsonify({"error": "DATA_INI e DATA_FIM sao obrigatorias."}), 400
    if data_fim < data_ini:
        return jsonify({"error": "DATA_FIM nao pode ser inferior a DATA_INI."}), 400

    desconto_pct = _safe_decimal(payload.get("desconto_pct"), "0")
    if desconto_pct < 0 or desconto_pct > 100:
        return jsonify({"error": "DESCONTO_PCT tem de estar entre 0 e 100."}), 400

    nota = str(payload.get("nota") or "").strip()
    ativo = 1 if _as_bool(payload.get("ativo", True)) else 0

    perfil_exists = db.session.execute(
        text("SELECT COUNT(*) FROM dbo.PR_PERFIL WHERE PERFIL_ID = :perfil_id"),
        {"perfil_id": perfil_id},
    ).scalar_one()
    if int(perfil_exists or 0) == 0:
        return jsonify({"error": "Perfil nao encontrado."}), 404

    affected_profile_ids = {perfil_id}
    affected_start = data_ini
    affected_end = data_fim

    if promo_id is None:
        new_id = db.session.execute(
            text(
                """
                INSERT INTO dbo.PR_PROMO (
                    PERFIL_ID, DATA_INI, DATA_FIM, DESCONTO_PCT, NOTA, ATIVO, CRIADO_EM, CRIADO_POR
                )
                OUTPUT INSERTED.PROMO_ID
                VALUES (
                    :perfil_id, :data_ini, :data_fim, :desconto_pct, :nota, :ativo, SYSUTCDATETIME(), :criado_por
                )
                """
            ),
            {
                "perfil_id": perfil_id,
                "data_ini": data_ini,
                "data_fim": data_fim,
                "desconto_pct": desconto_pct,
                "nota": nota,
                "ativo": ativo,
                "criado_por": getattr(current_user, "LOGIN", "") or "",
            },
        ).scalar_one()
        db.session.commit()
        recalc = _recalc_promotions_for_profiles(affected_profile_ids, affected_start, affected_end)
        return jsonify({"ok": True, "promo_id": int(new_id), "recalc": recalc})

    current_row = db.session.execute(
        text(
            """
            SELECT PERFIL_ID, DATA_INI, DATA_FIM
            FROM dbo.PR_PROMO
            WHERE PROMO_ID = :promo_id
            """
        ),
        {"promo_id": promo_id},
    ).mappings().first()
    if not current_row:
        return jsonify({"error": "Promocao nao encontrada."}), 404

    affected_profile_ids.add(int(current_row["PERFIL_ID"]))
    affected_start = min(affected_start, current_row.get("DATA_INI") or affected_start)
    affected_end = max(affected_end, current_row.get("DATA_FIM") or affected_end)

    db.session.execute(
        text(
            """
            UPDATE dbo.PR_PROMO
            SET PERFIL_ID = :perfil_id,
                DATA_INI = :data_ini,
                DATA_FIM = :data_fim,
                DESCONTO_PCT = :desconto_pct,
                NOTA = :nota,
                ATIVO = :ativo
            WHERE PROMO_ID = :promo_id
            """
        ),
        {
            "promo_id": promo_id,
            "perfil_id": perfil_id,
            "data_ini": data_ini,
            "data_fim": data_fim,
            "desconto_pct": desconto_pct,
            "nota": nota,
            "ativo": ativo,
        },
    )
    db.session.commit()
    recalc = _recalc_promotions_for_profiles(affected_profile_ids, affected_start, affected_end)
    return jsonify({"ok": True, "promo_id": promo_id, "recalc": recalc})


@pricing_bp.route("/api/promotions/<int:promo_id>", methods=["DELETE"])
@login_required
def pricing_api_promotions_delete(promo_id):
    ensure_pricing_schema(db.session)

    row = db.session.execute(
        text(
            """
            SELECT PERFIL_ID, DATA_INI, DATA_FIM
            FROM dbo.PR_PROMO
            WHERE PROMO_ID = :promo_id
            """
        ),
        {"promo_id": promo_id},
    ).mappings().first()
    if not row:
        return jsonify({"error": "Promocao nao encontrada."}), 404

    db.session.execute(text("DELETE FROM dbo.PR_PROMO WHERE PROMO_ID = :promo_id"), {"promo_id": promo_id})
    db.session.commit()

    recalc = _recalc_promotions_for_profiles(
        [int(row["PERFIL_ID"])],
        row.get("DATA_INI"),
        row.get("DATA_FIM"),
    )
    return jsonify({"ok": True, "recalc": recalc})


@pricing_bp.route("/api/settings/profile", methods=["POST"])
@login_required
def pricing_api_settings_profile_save():
    ensure_pricing_schema(db.session)
    payload = request.get_json(silent=True) or request.form

    perfil_id_raw = payload.get("perfil_id")
    perfil_id = int(perfil_id_raw) if str(perfil_id_raw or "").strip() else None
    nome = str(payload.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "O nome do perfil e obrigatorio."}), 400

    k_pickup = _safe_decimal(payload.get("k_pickup"), "0.01")
    lim_min = _safe_decimal(payload.get("lim_ajuste_min"), "-0.20")
    lim_max = _safe_decimal(payload.get("lim_ajuste_max"), "0.20")
    if lim_min > lim_max:
        return jsonify({"error": "LIM_AJUSTE_MIN nao pode ser superior a LIM_AJUSTE_MAX."}), 400

    if perfil_id is None:
        new_id = db.session.execute(
            text(
                """
                INSERT INTO dbo.PR_PERFIL (NOME, K_PICKUP, LIM_AJUSTE_MIN, LIM_AJUSTE_MAX)
                OUTPUT INSERTED.PERFIL_ID
                VALUES (:nome, :k_pickup, :lim_min, :lim_max)
                """
            ),
            {
                "nome": nome,
                "k_pickup": k_pickup,
                "lim_min": lim_min,
                "lim_max": lim_max,
            },
        ).scalar_one()
        for dow in range(1, 8):
            db.session.execute(
                text(
                    """
                    INSERT INTO dbo.PR_DIA_SEMANA_FATOR (PERFIL_ID, DOW, FATOR)
                    VALUES (:perfil_id, :dow, 1.0)
                    """
                ),
                {"perfil_id": new_id, "dow": dow},
            )
        db.session.commit()
        return jsonify({"ok": True, "perfil_id": int(new_id)})

    existing = db.session.execute(
        text("SELECT PERFIL_ID FROM dbo.PR_PERFIL WHERE PERFIL_ID = :perfil_id"),
        {"perfil_id": perfil_id},
    ).scalar()
    if not existing:
        return jsonify({"error": "Perfil nao encontrado."}), 404

    db.session.execute(
        text(
            """
            UPDATE dbo.PR_PERFIL
            SET NOME = :nome,
                K_PICKUP = :k_pickup,
                LIM_AJUSTE_MIN = :lim_min,
                LIM_AJUSTE_MAX = :lim_max
            WHERE PERFIL_ID = :perfil_id
            """
        ),
        {
            "perfil_id": perfil_id,
            "nome": nome,
            "k_pickup": k_pickup,
            "lim_min": lim_min,
            "lim_max": lim_max,
        },
    )
    for dow in range(1, 8):
        db.session.execute(
            text(
                """
                IF NOT EXISTS (
                    SELECT 1
                    FROM dbo.PR_DIA_SEMANA_FATOR
                    WHERE PERFIL_ID = :perfil_id AND DOW = :dow
                )
                BEGIN
                    INSERT INTO dbo.PR_DIA_SEMANA_FATOR (PERFIL_ID, DOW, FATOR)
                    VALUES (:perfil_id, :dow, 1.0)
                END
                """
            ),
            {"perfil_id": perfil_id, "dow": dow},
        )
    db.session.commit()
    return jsonify({"ok": True, "perfil_id": perfil_id})


@pricing_bp.route("/api/settings/profile/<int:perfil_id>", methods=["DELETE"])
@login_required
def pricing_api_settings_profile_delete(perfil_id):
    ensure_pricing_schema(db.session)

    linked = db.session.execute(
        text("SELECT COUNT(*) FROM dbo.PR_ALOJAMENTO WHERE PERFIL_ID = :perfil_id"),
        {"perfil_id": perfil_id},
    ).scalar_one()
    if int(linked or 0) > 0:
        return jsonify({"error": "Nao pode remover um perfil associado a alojamentos."}), 400

    exists = db.session.execute(
        text("SELECT COUNT(*) FROM dbo.PR_PERFIL WHERE PERFIL_ID = :perfil_id"),
        {"perfil_id": perfil_id},
    ).scalar_one()
    if int(exists or 0) == 0:
        return jsonify({"error": "Perfil nao encontrado."}), 404

    db.session.execute(text("DELETE FROM dbo.PR_PICKUP_CURVE WHERE PERFIL_ID = :perfil_id"), {"perfil_id": perfil_id})
    db.session.execute(text("DELETE FROM dbo.PR_DIA_SEMANA_FATOR WHERE PERFIL_ID = :perfil_id"), {"perfil_id": perfil_id})
    db.session.execute(text("DELETE FROM dbo.PR_PERFIL WHERE PERFIL_ID = :perfil_id"), {"perfil_id": perfil_id})
    db.session.commit()
    return jsonify({"ok": True})


@pricing_bp.route("/api/settings/seasonality", methods=["POST"])
@login_required
def pricing_api_settings_seasonality_save():
    ensure_pricing_schema(db.session)
    payload = request.get_json(silent=True) or {}
    rows = payload.get("rows") or []
    if not isinstance(rows, list):
        return jsonify({"error": "Formato invalido para sazonalidade."}), 400

    for row in rows:
        mes = int(row.get("mes"))
        indice = _safe_decimal(row.get("indice"), "100")
        nota = str(row.get("nota") or "").strip()
        if mes < 1 or mes > 12:
            return jsonify({"error": f"Mes invalido: {mes}."}), 400
        db.session.execute(
            text(
                """
                MERGE dbo.PR_SAZONAL_MES AS target
                USING (SELECT :mes AS MES, :indice AS INDICE, :nota AS NOTA) AS source
                ON target.MES = source.MES
                WHEN MATCHED THEN
                    UPDATE SET INDICE = source.INDICE, NOTA = source.NOTA
                WHEN NOT MATCHED THEN
                    INSERT (MES, INDICE, NOTA)
                    VALUES (source.MES, source.INDICE, source.NOTA);
                """
            ),
            {"mes": mes, "indice": indice, "nota": nota},
        )

    db.session.commit()
    return jsonify({"ok": True})


@pricing_bp.route("/api/settings/dow", methods=["POST"])
@login_required
def pricing_api_settings_dow_save():
    ensure_pricing_schema(db.session)
    payload = request.get_json(silent=True) or {}
    rows = payload.get("rows") or []
    if not isinstance(rows, list):
        return jsonify({"error": "Formato invalido para fatores por dia."}), 400

    for row in rows:
        perfil_id = int(row.get("perfil_id"))
        dow = int(row.get("dow"))
        fator = _safe_decimal(row.get("fator"), "1")
        if dow < 1 or dow > 7:
            return jsonify({"error": f"DOW invalido: {dow}."}), 400
        db.session.execute(
            text(
                """
                MERGE dbo.PR_DIA_SEMANA_FATOR AS target
                USING (SELECT :perfil_id AS PERFIL_ID, :dow AS DOW, :fator AS FATOR) AS source
                ON target.PERFIL_ID = source.PERFIL_ID
                   AND target.DOW = source.DOW
                WHEN MATCHED THEN
                    UPDATE SET FATOR = source.FATOR
                WHEN NOT MATCHED THEN
                    INSERT (PERFIL_ID, DOW, FATOR)
                    VALUES (source.PERFIL_ID, source.DOW, source.FATOR);
                """
            ),
            {"perfil_id": perfil_id, "dow": dow, "fator": fator},
        )

    db.session.commit()
    return jsonify({"ok": True})


@pricing_bp.route("/api/planner")
@login_required
def pricing_api_planner():
    ensure_pricing_schema(db.session)
    alojamento = _normalize_alojamento(request.args.get("alojamento"))
    if not alojamento:
        return jsonify({"error": "Alojamento em falta."}), 400

    start_date = _parse_date(request.args.get("start"), "start")
    if not start_date:
        start_date = date.today().replace(day=1)

    horizon_end = start_date + timedelta(days=370)
    planner_events, planner_event_years = _load_event_cache_for_range(start_date, horizon_end)
    occupied_rows = db.session.execute(
        text(
            """
            SELECT
                RS.DATAIN AS DATA_INI,
                RS.DATAOUT AS DATA_FIM,
                RS.ESTADIA AS ESTADIA,
                RS.NOITES AS NOITES
            FROM dbo.RS
            WHERE RS.ALOJAMENTO = :alojamento
              AND RS.DATAIN IS NOT NULL
              AND RS.DATAOUT IS NOT NULL
              AND ISNULL(RS.CANCELADA, 0) = 0
              AND RS.DATAOUT > :start_date
              AND RS.DATAIN <= :end_date
            """
        ),
        {"alojamento": alojamento, "start_date": start_date, "end_date": horizon_end},
    ).mappings().all()
    occupied_days = set()
    occupied_prices = {}
    for item in occupied_rows:
        stay_start = max(item.get("DATA_INI"), start_date)
        stay_end_exclusive = min(item.get("DATA_FIM"), horizon_end + timedelta(days=1))
        if not stay_start or not stay_end_exclusive or stay_start >= stay_end_exclusive:
            continue
        nightly_price = None
        noites = _safe_decimal(item.get("NOITES"), "0")
        if noites > 0:
            nightly_price = _round_price(_safe_decimal(item.get("ESTADIA"), "0") / noites)
        cursor = stay_start
        while cursor < stay_end_exclusive:
            occupied_days.add(cursor)
            if nightly_price is not None:
                occupied_prices.setdefault(cursor, nightly_price)
            cursor += timedelta(days=1)

    rows = db.session.execute(
        text(
            """
            SELECT
                [DATA] AS DIA,
                ISO_WEEK,
                PRECO_FINAL,
                ISNULL([SYNC], 0) AS [SYNC],
                SYNCED_AT,
                UPDATED_AT
            FROM dbo.PR_CALC_DAY
            WHERE AL_NOME = :alojamento
              AND [DATA] BETWEEN :start_date AND :end_date
            ORDER BY [DATA] ASC
            """
        ),
        {"alojamento": alojamento, "start_date": start_date, "end_date": horizon_end},
    ).mappings().all()

    data = []
    for row in rows:
        _, planner_event = _resolve_event_factor(row["DIA"], planner_events, planner_event_years)
        data.append(
            {
                "date": row["DIA"].isoformat(),
                "iso_week": row.get("ISO_WEEK") or "",
                "preco_final": _to_float(row.get("PRECO_FINAL")),
                "occupied": row["DIA"] in occupied_days,
                "occupied_price": _to_float(occupied_prices.get(row["DIA"])) if row["DIA"] in occupied_prices else None,
                "synced": bool(row.get("SYNC")),
                "synced_at": row["SYNCED_AT"].isoformat() if row.get("SYNCED_AT") else "",
                "has_event": bool(planner_event),
                "event_name": (planner_event or {}).get("nome", ""),
                "updated_at": row["UPDATED_AT"].isoformat() if row.get("UPDATED_AT") else "",
            }
        )

    return jsonify({"alojamento": alojamento, "start": start_date.isoformat(), "days": data})


@pricing_bp.route("/api/planner-sync")
@login_required
def pricing_api_planner_sync():
    ensure_pricing_schema(db.session)
    alojamento = _normalize_alojamento(request.args.get("alojamento"))
    if not alojamento:
        return jsonify({"error": "Alojamento em falta."}), 400

    start_date = _parse_date(request.args.get("start"), "start")
    if not start_date:
        start_date = date.today().replace(day=1)

    horizon_end = start_date + timedelta(days=370)
    rows = db.session.execute(
        text(
            """
            SELECT
                [DATA] AS DIA,
                ISNULL([SYNC], 0) AS [SYNC],
                SYNCED_AT
            FROM dbo.PR_CALC_DAY
            WHERE AL_NOME = :alojamento
              AND [DATA] BETWEEN :start_date AND :end_date
            ORDER BY [DATA] ASC
            """
        ),
        {"alojamento": alojamento, "start_date": start_date, "end_date": horizon_end},
    ).mappings().all()

    return jsonify(
        {
            "alojamento": alojamento,
            "start": start_date.isoformat(),
            "days": [
                {
                    "date": row["DIA"].isoformat(),
                    "synced": bool(row.get("SYNC")),
                    "synced_at": row["SYNCED_AT"].isoformat() if row.get("SYNCED_AT") else "",
                }
                for row in rows
            ],
        }
    )


@pricing_bp.route("/api/day")
@login_required
def pricing_api_day():
    ensure_pricing_schema(db.session)
    alojamento = _normalize_alojamento(request.args.get("alojamento"))
    day_value = _parse_date(request.args.get("date"), "date")
    if not alojamento or not day_value:
        return jsonify({"error": "Alojamento e date sao obrigatorios."}), 400

    row = db.session.execute(
        text(
            """
            SELECT
                AL_NOME,
                [DATA] AS DIA,
                ISO_WEEK,
                PRECO_CALC,
                PRECO_FINAL,
                ISNULL([SYNC], 0) AS [SYNC],
                SYNCED_AT,
                FLAGS,
                UPDATED_AT
            FROM dbo.PR_CALC_DAY
            WHERE AL_NOME = :alojamento
              AND [DATA] = :day_value
            """
        ),
        {"alojamento": alojamento, "day_value": day_value},
    ).mappings().first()
    if not row:
        return jsonify({"error": "Dia nao materializado."}), 404

    profile_row = db.session.execute(
        text(
            """
            SELECT PERFIL_ID
            FROM dbo.PR_ALOJAMENTO
            WHERE AL_NOME = :alojamento
            """
        ),
        {"alojamento": alojamento},
    ).mappings().first()
    perfil_id = int(profile_row["PERFIL_ID"]) if profile_row and profile_row.get("PERFIL_ID") is not None else None

    promotions = []
    if perfil_id is not None:
        promotions = db.session.execute(
            text(
                """
                SELECT
                    P.PROMO_ID,
                    P.PERFIL_ID,
                    PF.NOME AS PERFIL_NOME,
                    P.DATA_INI,
                    P.DATA_FIM,
                    P.DESCONTO_PCT,
                    ISNULL(P.NOTA, '') AS NOTA,
                    ISNULL(P.ATIVO, 0) AS ATIVO,
                    P.CRIADO_EM,
                    ISNULL(P.CRIADO_POR, '') AS CRIADO_POR
                FROM dbo.PR_PROMO AS P
                INNER JOIN dbo.PR_PERFIL AS PF
                  ON PF.PERFIL_ID = P.PERFIL_ID
                WHERE P.PERFIL_ID = :perfil_id
                  AND ISNULL(P.ATIVO, 0) = 1
                  AND P.DATA_INI <= :day_value
                  AND P.DATA_FIM >= :day_value
                ORDER BY P.CRIADO_EM DESC, P.PROMO_ID DESC
                """
            ),
            {"perfil_id": perfil_id, "day_value": day_value},
        ).mappings().all()

    overrides = db.session.execute(
        text(
            """
            SELECT
                OVR_ID, TIPO, DATA_INI, DATA_FIM, VALOR, PERMITIR_ABAIXO_MIN,
                MOTIVO, ATIVO, CRIADO_EM, CRIADO_POR
            FROM dbo.PR_OVERRIDE
            WHERE AL_NOME = :alojamento
              AND ISNULL(ATIVO, 0) = 1
              AND DATA_INI <= :day_value
              AND DATA_FIM >= :day_value
            ORDER BY CRIADO_EM DESC, OVR_ID DESC
            """
        ),
        {"alojamento": alojamento, "day_value": day_value},
    ).mappings().all()

    try:
        flags = json.loads(row.get("FLAGS") or "{}")
    except Exception:
        flags = {"raw": row.get("FLAGS")}

    return jsonify(
        {
            "alojamento": _normalize_alojamento(row.get("AL_NOME")),
            "date": row.get("DIA").isoformat(),
            "iso_week": row.get("ISO_WEEK") or "",
            "preco_calc": _to_float(row.get("PRECO_CALC")),
            "preco_final": _to_float(row.get("PRECO_FINAL")),
            "synced": bool(row.get("SYNC")),
            "synced_at": row.get("SYNCED_AT").isoformat() if row.get("SYNCED_AT") else "",
            "flags": flags,
            "updated_at": row.get("UPDATED_AT").isoformat() if row.get("UPDATED_AT") else "",
            "promotions": [
                {
                    "promo_id": int(item["PROMO_ID"]),
                    "perfil_id": int(item["PERFIL_ID"]),
                    "perfil_nome": item.get("PERFIL_NOME") or "",
                    "data_ini": item.get("DATA_INI").isoformat() if item.get("DATA_INI") else "",
                    "data_fim": item.get("DATA_FIM").isoformat() if item.get("DATA_FIM") else "",
                    "desconto_pct": _to_float(item.get("DESCONTO_PCT")),
                    "nota": item.get("NOTA") or "",
                    "ativo": bool(item.get("ATIVO")),
                    "criado_em": item.get("CRIADO_EM").isoformat() if item.get("CRIADO_EM") else "",
                    "criado_por": item.get("CRIADO_POR") or "",
                }
                for item in promotions
            ],
            "overrides": [
                {
                    "ovr_id": int(item["OVR_ID"]),
                    "tipo": item.get("TIPO") or "",
                    "data_ini": item.get("DATA_INI").isoformat() if item.get("DATA_INI") else "",
                    "data_fim": item.get("DATA_FIM").isoformat() if item.get("DATA_FIM") else "",
                    "valor": _to_float(item.get("VALOR")),
                    "permitir_abaixo_min": bool(item.get("PERMITIR_ABAIXO_MIN")),
                    "motivo": item.get("MOTIVO") or "",
                    "ativo": bool(item.get("ATIVO")),
                    "criado_em": item.get("CRIADO_EM").isoformat() if item.get("CRIADO_EM") else "",
                    "criado_por": item.get("CRIADO_POR") or "",
                }
                for item in overrides
            ],
        }
    )


@pricing_bp.route("/api/override", methods=["POST"])
@login_required
def pricing_api_override():
    ensure_pricing_schema(db.session)
    payload = request.get_json(silent=True) or request.form

    try:
        alojamento = _normalize_alojamento(payload.get("alojamento"))
        tipo = str(payload.get("tipo") or "").strip().upper()
        data_ini = _parse_date(payload.get("data_ini"), "data_ini")
        data_fim = _parse_date(payload.get("data_fim"), "data_fim")
        valor = _safe_decimal(payload.get("valor"), "0")
        motivo = str(payload.get("motivo") or "").strip()
        permitir_abaixo_min = _as_bool(payload.get("permitir_abaixo_min"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if not alojamento or not data_ini or not data_fim:
        return jsonify({"error": "alojamento, data_ini e data_fim sao obrigatorios."}), 400
    if data_fim < data_ini:
        return jsonify({"error": "DATA_FIM nao pode ser inferior a DATA_INI."}), 400
    if tipo not in {"PRECO_FIXO", "DESCONTO_PCT"}:
        return jsonify({"error": "TIPO invalido."}), 400
    if tipo == "DESCONTO_PCT" and (valor < 0 or valor > 100):
        return jsonify({"error": "DESCONTO_PCT tem de estar entre 0 e 100."}), 400

    db.session.execute(
        text(
            """
            INSERT INTO dbo.PR_OVERRIDE (
                AL_NOME, TIPO, DATA_INI, DATA_FIM, VALOR, PERMITIR_ABAIXO_MIN,
                MOTIVO, ATIVO, CRIADO_EM, CRIADO_POR
            )
            VALUES (
                :alojamento, :tipo, :data_ini, :data_fim, :valor, :permitir_abaixo_min,
                :motivo, 1, SYSUTCDATETIME(), :criado_por
            )
            """
        ),
        {
            "alojamento": alojamento,
            "tipo": tipo,
            "data_ini": data_ini,
            "data_fim": data_fim,
            "valor": valor,
            "permitir_abaixo_min": 1 if permitir_abaixo_min else 0,
            "motivo": motivo,
            "criado_por": getattr(current_user, "LOGIN", "") or "",
        },
    )
    db.session.commit()

    result = recalculate_prices(alojamento=alojamento, from_date=data_ini, to_date=data_fim)
    return jsonify({"ok": True, "recalc": result})


@pricing_bp.route("/api/override/<int:ovr_id>", methods=["DELETE"])
@login_required
def pricing_api_override_delete(ovr_id):
    ensure_pricing_schema(db.session)

    row = db.session.execute(
        text(
            """
            SELECT
                AL_NOME,
                DATA_INI,
                DATA_FIM,
                ISNULL(ATIVO, 0) AS ATIVO
            FROM dbo.PR_OVERRIDE
            WHERE OVR_ID = :ovr_id
            """
        ),
        {"ovr_id": ovr_id},
    ).mappings().first()
    if not row:
        return jsonify({"error": "Override nao encontrado."}), 404
    if not bool(row.get("ATIVO")):
        return jsonify({"ok": True, "recalc": None})

    db.session.execute(
        text(
            """
            UPDATE dbo.PR_OVERRIDE
            SET ATIVO = 0
            WHERE OVR_ID = :ovr_id
            """
        ),
        {"ovr_id": ovr_id},
    )
    db.session.commit()

    result = recalculate_prices(
        alojamento=_normalize_alojamento(row.get("AL_NOME")),
        from_date=row.get("DATA_INI"),
        to_date=row.get("DATA_FIM"),
    )
    return jsonify({"ok": True, "recalc": result})


@pricing_bp.route("/api/recalc", methods=["POST"])
@login_required
def pricing_api_recalc():
    payload = request.get_json(silent=True) or request.form
    try:
        result = recalculate_prices(
            days=payload.get("days") or DEFAULT_HORIZON_DAYS,
            alojamento=payload.get("alojamento"),
            from_date=payload.get("from"),
            to_date=payload.get("to"),
        )
        return jsonify({"ok": True, "result": result})
    except Exception as exc:
        current_app.logger.exception("Erro no recalc manual de pricing")
        return jsonify({"error": str(exc)}), 500


@pricing_bp.route("/api/recalc-job", methods=["POST"])
def pricing_api_recalc_job():
    error, status = _authorize_pricing_robot_request()
    if error:
        return jsonify({"error": error}), status

    payload = request.get_json(silent=True) or request.form or {}
    try:
        result = recalculate_prices(
            days=payload.get("days") or DEFAULT_HORIZON_DAYS,
            alojamento=payload.get("alojamento"),
            from_date=payload.get("from"),
            to_date=payload.get("to"),
        )
        return jsonify({"ok": True, "result": result})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception("Erro no recalc tecnico de pricing")
        return jsonify({"error": str(exc)}), 500


def register_pricing(app):
    app.register_blueprint(pricing_bp)

    def _pricing_planner_legacy():
        return redirect(url_for("pricing.pricing_planner"))

    def _pricing_settings_legacy():
        return redirect(url_for("pricing.pricing_settings"))

    def _pricing_events_legacy():
        return redirect(url_for("pricing.pricing_events"))

    def _pricing_promotions_legacy():
        return redirect(url_for("pricing.pricing_promotions"))

    def _pricing_pickup_curves_legacy():
        return redirect(url_for("pricing.pricing_pickup_curves"))

    def _pricing_sync_monitor_legacy():
        return redirect(url_for("pricing.pricing_sync_monitor"))

    app.add_url_rule("/pricing_planner", endpoint="pricing_planner_legacy", view_func=_pricing_planner_legacy)
    app.add_url_rule("/pricing_planner/", endpoint="pricing_planner_legacy_slash", view_func=_pricing_planner_legacy)
    app.add_url_rule("/pricing_config", endpoint="pricing_settings_legacy", view_func=_pricing_settings_legacy)
    app.add_url_rule("/pricing_config/", endpoint="pricing_settings_legacy_slash", view_func=_pricing_settings_legacy)
    app.add_url_rule("/pricing_settings", endpoint="pricing_settings_legacy_alt", view_func=_pricing_settings_legacy)
    app.add_url_rule("/pricing_settings/", endpoint="pricing_settings_legacy_alt_slash", view_func=_pricing_settings_legacy)
    app.add_url_rule("/pricing_events", endpoint="pricing_events_legacy", view_func=_pricing_events_legacy)
    app.add_url_rule("/pricing_events/", endpoint="pricing_events_legacy_slash", view_func=_pricing_events_legacy)
    app.add_url_rule("/pricing_promotions", endpoint="pricing_promotions_legacy", view_func=_pricing_promotions_legacy)
    app.add_url_rule("/pricing_promotions/", endpoint="pricing_promotions_legacy_slash", view_func=_pricing_promotions_legacy)
    app.add_url_rule("/pickup_curves", endpoint="pricing_pickup_curves_legacy", view_func=_pricing_pickup_curves_legacy)
    app.add_url_rule("/pickup_curves/", endpoint="pricing_pickup_curves_legacy_slash", view_func=_pricing_pickup_curves_legacy)
    app.add_url_rule("/pickup-curves", endpoint="pricing_pickup_curves_legacy_alt", view_func=_pricing_pickup_curves_legacy)
    app.add_url_rule("/pickup-curves/", endpoint="pricing_pickup_curves_legacy_alt_slash", view_func=_pricing_pickup_curves_legacy)
    app.add_url_rule("/pricing_sync_monitor", endpoint="pricing_sync_monitor_legacy", view_func=_pricing_sync_monitor_legacy)
    app.add_url_rule("/pricing_sync_monitor/", endpoint="pricing_sync_monitor_legacy_slash", view_func=_pricing_sync_monitor_legacy)

    @app.cli.command("pricing:recalc")
    @click.option("--days", default=DEFAULT_HORIZON_DAYS, type=int, show_default=True)
    @click.option("--alojamento", default="", help="AL.NOME a recalcular.")
    @click.option("--from", "from_date", default=None, help="Data inicial (YYYY-MM-DD).")
    @click.option("--to", "to_date", default=None, help="Data final (YYYY-MM-DD).")
    def pricing_recalc_command(days, alojamento, from_date, to_date):
        """Materializa PR_CALC_DAY para o intervalo pedido."""
        with app.app_context():
            result = recalculate_prices(
                days=days,
                alojamento=alojamento,
                from_date=from_date,
                to_date=to_date,
            )
            click.echo(json.dumps(result, ensure_ascii=False))
