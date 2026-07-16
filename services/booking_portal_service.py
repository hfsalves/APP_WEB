from __future__ import annotations

import hashlib
import re
import secrets
import uuid
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import current_app
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from models import db
from services.auth_service import hash_password, verify_password_hash


TIPOLOGIA_CAPACIDADE = {
    "T0": 2,
    "T1": 3,
    "T2": 4,
    "T3": 6,
    "T4": 8,
}

PLACEHOLDER_IMAGE = ""
PUBLIC_STATIC_BASE_URL = "https://szeroapp.com/static/"
_DEC2 = Decimal("0.01")
CLEANING_FEE = Decimal("30.00")
TOURIST_TAX_PER_GUEST_NIGHT = Decimal("3.00")
TOURIST_TAX_MAX_DAYS = 7
_TABLE_EXISTS_CACHE = {}


class PortalPaymentError(RuntimeError):
    """A user-facing failure while preparing a Porto Break test payment."""


class PortalPaymentConfigurationError(PortalPaymentError):
    """Raised when test payments are not explicitly configured."""


def _new_stamp() -> str:
    return str(uuid.uuid4()).upper()


def _clean(value) -> str:
    return str(value or "").strip()


def _to_date(value):
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return date.fromisoformat(str(value or "").strip()[:10])
    except Exception:
        return None


def _to_int(value, default=None):
    try:
        number = int(str(value or "").strip())
        return number if number > 0 else default
    except Exception:
        return default


def _to_count(value, default=None):
    if value is None:
        return default
    text_value = str(value).strip()
    if text_value == "":
        return default
    try:
        number = int(text_value)
        return number if number >= 0 else default
    except Exception:
        return default


def _to_decimal(value):
    try:
        return Decimal(str(value or "0")).quantize(_DEC2, rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal("0.00")


def _to_float(value):
    try:
        text_value = str(value or "").strip().replace(",", ".")
        if not text_value:
            return None
        number = float(text_value)
        if abs(number) < 0.000001:
            return None
        return number
    except Exception:
        return None


def _money(value):
    amount = _to_decimal(value)
    if amount <= 0:
        return ""
    return f"{amount:.2f} EUR"


def _daterange(start_date: date, end_date: date):
    cursor = start_date
    while cursor < end_date:
        yield cursor
        cursor = date.fromordinal(cursor.toordinal() + 1)


def _add_months(value: date, months: int) -> date:
    month_index = (value.month - 1) + int(months or 0)
    year = value.year + (month_index // 12)
    month = (month_index % 12) + 1
    return date(year, month, 1)


def _in_medium_high_season(day_value: date) -> bool:
    return 4 <= day_value.month <= 10


def _range_touches_medium_high_season(start_date: date, end_date: date) -> bool:
    return any(_in_medium_high_season(day_value) for day_value in _daterange(start_date, end_date))


def capacidade_por_tipologia(tipologia) -> int:
    value = _clean(tipologia).upper().replace(" ", "")
    match = re.search(r"T[0-4]", value)
    if not match:
        return 0
    return TIPOLOGIA_CAPACIDADE.get(match.group(0), 0)


def _public_image_url(path) -> str:
    value = _clean(path).replace("\\", "/")
    if not value:
        return PLACEHOLDER_IMAGE
    if value.startswith(("http://", "https://")):
        return value
    clean = value.lstrip("/")
    static_relative = clean[7:] if clean.startswith("static/") else clean
    return f"{PUBLIC_STATIC_BASE_URL}{static_relative}"


def _row_dict(row) -> dict:
    return dict(row or {})


def _table_exists(table_name: str) -> bool:
    name = _clean(table_name).upper()
    if not name:
        return False
    if name in _TABLE_EXISTS_CACHE:
        return _TABLE_EXISTS_CACHE[name]
    try:
        exists = bool(
            db.session.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM INFORMATION_SCHEMA.TABLES
                    WHERE TABLE_SCHEMA = 'dbo'
                      AND TABLE_NAME = :table_name
                    """
                ),
                {"table_name": name},
            ).scalar()
            or 0
        )
    except SQLAlchemyError:
        db.session.rollback()
        return False
    _TABLE_EXISTS_CACHE[name] = exists
    return exists


def alojamento_disponivel(al_id, checkin, checkout) -> bool:
    checkin_date = _to_date(checkin)
    checkout_date = _to_date(checkout)
    if not checkin_date or not checkout_date or checkout_date <= checkin_date:
        return False

    row = db.session.execute(
        text(
            """
            SELECT TOP 1 AL.NOME
            FROM dbo.AL AS AL
            WHERE AL.ALSTAMP = :al_id
              AND LTRIM(RTRIM(ISNULL(AL.NOME, ''))) <> ''
              AND ISNULL(AL.INATIVO, 0) = 0
              AND ISNULL(AL.FECHADO, 0) = 0
            """
        ),
        {"al_id": _clean(al_id)},
    ).mappings().first()
    if not row:
        return False

    conflicts = db.session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM dbo.RS AS RS
            WHERE LTRIM(RTRIM(ISNULL(RS.ALOJAMENTO, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI
                = LTRIM(RTRIM(:alojamento)) COLLATE SQL_Latin1_General_CP1_CI_AI
              AND RS.DATAIN IS NOT NULL
              AND RS.DATAOUT IS NOT NULL
              AND ISNULL(RS.CANCELADA, 0) = 0
              AND CAST(RS.DATAIN AS date) < :checkout
              AND CAST(RS.DATAOUT AS date) > :checkin
            """
        ),
        {
            "alojamento": _clean(row.get("NOME")),
            "checkin": checkin_date,
            "checkout": checkout_date,
        },
    ).scalar()
    return not bool(conflicts or 0)


def _descricao_alojamento_sql(lang=None) -> str:
    lang_key = _clean(lang).lower()
    translated_column = {
        "en": "DESCRICAOEN",
        "fr": "DESCRICAOFR",
        "es": "DESCRICAOES",
    }.get(lang_key)
    base = "LTRIM(RTRIM(CAST(ISNULL(AL.DESCRICAO, '') AS varchar(max))))"
    if not translated_column:
        return base
    translated = f"LTRIM(RTRIM(CAST(ISNULL(AL.{translated_column}, '') AS varchar(max))))"
    return f"COALESCE(NULLIF({translated}, ''), {base})"


def _alojamento_base_select(where_sql: str, lang=None) -> str:
    return f"""
        SELECT
            AL.ALSTAMP,
            LTRIM(RTRIM(ISNULL(AL.NOME, ''))) AS NOME_INTERNO,
            COALESCE(
                NULLIF(LTRIM(RTRIM(ISNULL(AL.NMAIRBNB, ''))), ''),
                LTRIM(RTRIM(ISNULL(AL.NOME, '')))
            ) AS NOME,
            LTRIM(RTRIM(ISNULL(AL.TIPOLOGIA, ''))) AS TIPOLOGIA,
            LTRIM(RTRIM(ISNULL(AL.MORADA, ''))) AS MORADA,
            LTRIM(RTRIM(ISNULL(AL.LOCAL, ''))) AS LOCAL,
            LTRIM(RTRIM(ISNULL(AL.CODPOST, ''))) AS CODPOST,
            LTRIM(RTRIM(ISNULL(AL.ZONA, ''))) AS ZONA,
            LTRIM(RTRIM(ISNULL(AL.LAT, ''))) AS LAT,
            LTRIM(RTRIM(ISNULL(AL.LON, ''))) AS LON,
            LTRIM(RTRIM(ISNULL(AL.NMPESQUISA, ''))) AS NMPESQUISA,
            CAST(ISNULL(AL.LOTADULTOS, 0) AS int) AS LOTADULTOS,
            CAST(ISNULL(AL.LOTCRIANCAS, 0) AS int) AS LOTCRIANCAS,
            CAST(ISNULL(AL.BERCO, 0) AS bit) AS BERCO,
            CAST(ISNULL(AL.NOITES, 1) AS int) AS NOITES,
            CAST(ISNULL(AL.VALOREXTRA, 0) AS decimal(12, 2)) AS VALOREXTRA,
            CAST(ISNULL(AL.EXTRAMAISQUE, 0) AS int) AS EXTRAMAISQUE,
            CAST(ISNULL(AL.PBASE, 0) AS decimal(12, 2)) AS PBASE,
            CAST(COALESCE(PA.PRECO_BASE, AL.PBASE, 0) AS decimal(12, 2)) AS PRECO_DESDE,
            {_descricao_alojamento_sql(lang)} AS DESCRICAO
        FROM dbo.AL AS AL
        OUTER APPLY (
            SELECT TOP 1 PA.PRECO_BASE
            FROM dbo.PR_ALOJAMENTO AS PA
            WHERE LTRIM(RTRIM(ISNULL(PA.AL_NOME, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI
                = LTRIM(RTRIM(ISNULL(AL.NOME, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI
              AND ISNULL(PA.ATIVO, 1) = 1
        ) AS PA
        WHERE {where_sql}
        ORDER BY COALESCE(
            NULLIF(LTRIM(RTRIM(ISNULL(AL.NMAIRBNB, ''))), ''),
            LTRIM(RTRIM(ISNULL(AL.NOME, '')))
        )
    """


def _alojamento_count_select(where_sql: str) -> str:
    return f"""
        SELECT COUNT(*)
        FROM dbo.AL AS AL
        WHERE {where_sql}
    """


def _alojamento_capacity_sql() -> str:
    normalized = "REPLACE(UPPER(LTRIM(RTRIM(ISNULL(AL.TIPOLOGIA, '')))), ' ', '')"
    typology_capacity = f"""
        CASE
            WHEN {normalized} LIKE '%T4%' THEN 8
            WHEN {normalized} LIKE '%T3%' THEN 6
            WHEN {normalized} LIKE '%T2%' THEN 4
            WHEN {normalized} LIKE '%T1%' THEN 3
            WHEN {normalized} LIKE '%T0%' THEN 2
            ELSE 0
        END
    """
    return f"""
        CASE
            WHEN ISNULL(AL.LOTADULTOS, 0) > 0 OR ISNULL(AL.LOTCRIANCAS, 0) > 0
                THEN ISNULL(AL.LOTADULTOS, 0) + ISNULL(AL.LOTCRIANCAS, 0)
            ELSE {typology_capacity}
        END
    """


def _alojamento_adult_capacity_sql() -> str:
    normalized = "REPLACE(UPPER(LTRIM(RTRIM(ISNULL(AL.TIPOLOGIA, '')))), ' ', '')"
    typology_capacity = f"""
        CASE
            WHEN {normalized} LIKE '%T4%' THEN 8
            WHEN {normalized} LIKE '%T3%' THEN 6
            WHEN {normalized} LIKE '%T2%' THEN 4
            WHEN {normalized} LIKE '%T1%' THEN 3
            WHEN {normalized} LIKE '%T0%' THEN 2
            ELSE 0
        END
    """
    return f"""
        CASE
            WHEN ISNULL(AL.LOTADULTOS, 0) > 0 THEN ISNULL(AL.LOTADULTOS, 0)
            ELSE {typology_capacity}
        END
    """


def _alojamento_paged_select(where_sql: str, lang=None) -> str:
    base_sql = _alojamento_base_select(where_sql, lang=lang).rstrip()
    return f"""
        {base_sql}
        OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
    """


def _decorate_alojamento(row: dict, include_gallery: bool = False) -> dict:
    item = _row_dict(row)
    tipologia = _clean(item.get("TIPOLOGIA"))
    capacidade_tipologia = capacidade_por_tipologia(tipologia)
    lot_adultos_raw = _to_count(item.get("LOTADULTOS"), default=0) or 0
    lot_criancas_raw = _to_count(item.get("LOTCRIANCAS"), default=0) or 0
    has_lotacao_detalhada = lot_adultos_raw > 0 or lot_criancas_raw > 0
    lot_adultos = lot_adultos_raw if lot_adultos_raw > 0 else capacidade_tipologia
    lot_criancas = lot_criancas_raw if has_lotacao_detalhada else 0
    capacidade = (lot_adultos + lot_criancas) if has_lotacao_detalhada else capacidade_tipologia
    alstamp = item.get("ALSTAMP")
    fotos_al = get_fotos_alojamento(alstamp) if include_gallery else []
    foto_principal = fotos_al[0]["url"] if fotos_al else get_foto_principal(alstamp)
    fotos = []
    seen_urls = set()
    if include_gallery and foto_principal:
        fotos.append({
            "url": foto_principal,
            "thumb_url": foto_principal,
            "alt": _clean(item.get("NOME")) or "Alojamento",
            "capa": True,
            "source": "cover",
        })
        seen_urls.add(foto_principal)
    if include_gallery:
        for photo in get_fotos_melhoradas_alojamento(alstamp):
            url = _clean(photo.get("url"))
            if not url or url in seen_urls:
                continue
            fotos.append(photo)
            seen_urls.add(url)
    descricao = _clean(item.get("DESCRICAO"))
    lat = _to_float(item.get("LAT"))
    lon = _to_float(item.get("LON"))
    return {
        "id": _clean(item.get("ALSTAMP")),
        "nome": _clean(item.get("NOME")),
        "nome_interno": _clean(item.get("NOME_INTERNO")),
        "tipologia": tipologia,
        "capacidade": capacidade,
        "lot_adultos": lot_adultos,
        "lot_criancas": lot_criancas,
        "berco": bool(item.get("BERCO")),
        "noites_minimas": max(1, _to_count(item.get("NOITES"), default=1) or 1),
        "valor_extra": _to_decimal(item.get("VALOREXTRA")),
        "extra_mais_que": _to_count(item.get("EXTRAMAISQUE"), default=0) or 0,
        "morada": _clean(item.get("MORADA")),
        "local": _clean(item.get("LOCAL")),
        "codpost": _clean(item.get("CODPOST")),
        "zona": _clean(item.get("ZONA")),
        "lat": lat,
        "lon": lon,
        "tem_mapa": lat is not None and lon is not None,
        "localizacao": ", ".join(part for part in [_clean(item.get("LOCAL")), _clean(item.get("ZONA"))] if part),
        "descricao": descricao,
        "descricao_curta": descricao[:180] + ("..." if len(descricao) > 180 else ""),
        "pbase": _to_decimal(item.get("PBASE")),
        "preco_desde": _money(item.get("PRECO_DESDE")),
        "foto_principal": foto_principal,
        "fotos": fotos,
    }


def get_foto_principal(al_id) -> str:
    if not _clean(al_id) or not _table_exists("AL_FOTOS"):
        return PLACEHOLDER_IMAGE
    row = db.session.execute(
        text(
            """
            SELECT TOP 1 ISNULL(CAMINHO, '') AS CAMINHO
            FROM dbo.AL_FOTOS
            WHERE ALSTAMP = :al_id
              AND ISNULL(ATIVO, 1) = 1
              AND ISNULL(CHECKIN, 0) = 0
            ORDER BY
              CASE WHEN ISNULL(CAPA, 0) = 1 THEN 0 ELSE 1 END,
              ISNULL(ORDEM, 999999),
              DTCRI
            """
        ),
        {"al_id": _clean(al_id)},
    ).mappings().first()
    return _public_image_url((row or {}).get("CAMINHO"))


def get_fotos_alojamento(al_id) -> list[dict]:
    if not _clean(al_id) or not _table_exists("AL_FOTOS"):
        return []
    rows = db.session.execute(
        text(
            """
            SELECT
                ISNULL(FICHEIRO, '') AS FICHEIRO,
                ISNULL(CAMINHO, '') AS CAMINHO,
                ISNULL(ALT_TEXT, '') AS ALT_TEXT,
                ISNULL(CAPA, 0) AS CAPA
            FROM dbo.AL_FOTOS
            WHERE ALSTAMP = :al_id
              AND ISNULL(ATIVO, 1) = 1
              AND ISNULL(CHECKIN, 0) = 0
            ORDER BY
              CASE WHEN ISNULL(CAPA, 0) = 1 THEN 0 ELSE 1 END,
              ISNULL(ORDEM, 999999),
              DTCRI
            """
        ),
        {"al_id": _clean(al_id)},
    ).mappings().all()
    return [
        {
            "url": _public_image_url(row.get("CAMINHO")),
            "alt": _clean(row.get("ALT_TEXT")) or _clean(row.get("FICHEIRO")) or "Alojamento",
            "capa": bool(row.get("CAPA")),
        }
        for row in rows
        if _clean(row.get("CAMINHO"))
    ]


def get_fotos_melhoradas_alojamento(al_id) -> list[dict]:
    al_id_clean = _clean(al_id)
    if not al_id_clean or not _table_exists("PHOTO_ENHANCER_SESSION") or not _table_exists("PHOTO_ENHANCER_FILE"):
        return []

    session_row = db.session.execute(
        text(
            """
            SELECT TOP 1 S.ID
            FROM dbo.PHOTO_ENHANCER_SESSION AS S
            WHERE LTRIM(RTRIM(ISNULL(S.ALOJAMENTO_ID, ''))) = :al_id
              AND EXISTS (
                  SELECT 1
                  FROM dbo.PHOTO_ENHANCER_FILE AS F
                  WHERE F.SESSION_ID = S.ID
                    AND LTRIM(RTRIM(ISNULL(F.ENHANCED_PATH, ''))) <> ''
                    AND LTRIM(RTRIM(ISNULL(F.STATUS, ''))) = 'melhorada'
              )
            ORDER BY COALESCE(S.UPDATED_AT, S.CREATED_AT) DESC, S.CREATED_AT DESC, S.ID DESC
            """
        ),
        {"al_id": al_id_clean},
    ).mappings().first()
    session_id = _clean((session_row or {}).get("ID"))
    if not session_id:
        return []

    rows = db.session.execute(
        text(
            """
            SELECT
                ISNULL(F.ORIGINAL_FILENAME, '') AS ORIGINAL_FILENAME,
                ISNULL(F.ENHANCED_PATH, '') AS ENHANCED_PATH,
                ISNULL(F.THUMB_PATH, '') AS THUMB_PATH
            FROM dbo.PHOTO_ENHANCER_FILE AS F
            WHERE F.SESSION_ID = :session_id
              AND LTRIM(RTRIM(ISNULL(F.ENHANCED_PATH, ''))) <> ''
              AND LTRIM(RTRIM(ISNULL(F.STATUS, ''))) = 'melhorada'
            ORDER BY F.CREATED_AT, F.ID
            """
        ),
        {"session_id": session_id},
    ).mappings().all()
    return [
        {
            "url": _public_image_url(row.get("ENHANCED_PATH")),
            "thumb_url": _public_image_url(row.get("THUMB_PATH")) if _clean(row.get("THUMB_PATH")) else _public_image_url(row.get("ENHANCED_PATH")),
            "alt": _clean(row.get("ORIGINAL_FILENAME")) or "Alojamento",
            "capa": False,
            "source": "photo_enhancer",
        }
        for row in rows
        if _clean(row.get("ENHANCED_PATH"))
    ]


def get_alojamento(al_id, lang=None) -> dict | None:
    al_id_clean = _clean(al_id)
    if not al_id_clean:
        return None
    row = db.session.execute(
        text(
            _alojamento_base_select(
                """
                AL.ALSTAMP = :al_id
                AND LTRIM(RTRIM(ISNULL(AL.NOME, ''))) <> ''
                AND ISNULL(AL.INATIVO, 0) = 0
                AND ISNULL(AL.FECHADO, 0) = 0
                """,
                lang=lang,
            )
        ),
        {"al_id": al_id_clean},
    ).mappings().first()
    if not row:
        return None
    return _decorate_alojamento(row, include_gallery=True)


def get_calendario_ocupacao(al_id, start=None, months=12) -> dict:
    al_id_clean = _clean(al_id)
    start_date = _to_date(start) or date.today()
    start_date = start_date.replace(day=1)
    end_date = _add_months(start_date, months)
    if not al_id_clean:
        return {"occupied": [], "blocked_checkin": [], "blocked_checkout": [], "min_nights": 1}

    row = db.session.execute(
        text(
            """
            SELECT TOP 1
                LTRIM(RTRIM(ISNULL(AL.NOME, ''))) AS NOME,
                CAST(ISNULL(AL.NOITES, 1) AS int) AS NOITES
            FROM dbo.AL AS AL
            WHERE AL.ALSTAMP = :al_id
              AND LTRIM(RTRIM(ISNULL(AL.NOME, ''))) <> ''
              AND ISNULL(AL.INATIVO, 0) = 0
              AND ISNULL(AL.FECHADO, 0) = 0
            """
        ),
        {"al_id": al_id_clean},
    ).mappings().first()
    alojamento_nome = _clean((row or {}).get("NOME"))
    min_nights = max(1, _to_count((row or {}).get("NOITES"), default=1) or 1)
    if not alojamento_nome:
        return {"occupied": [], "blocked_checkin": [], "blocked_checkout": [], "min_nights": min_nights}

    gap_days = max(0, min_nights - 1)
    query_start = date.fromordinal(start_date.toordinal() - gap_days)
    query_end = date.fromordinal(end_date.toordinal() + gap_days)

    rows = db.session.execute(
        text(
            """
            SELECT
                CAST(RS.DATAIN AS date) AS DATAIN,
                CAST(RS.DATAOUT AS date) AS DATAOUT
            FROM dbo.RS AS RS
            WHERE LTRIM(RTRIM(ISNULL(RS.ALOJAMENTO, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI
                = LTRIM(RTRIM(:alojamento)) COLLATE SQL_Latin1_General_CP1_CI_AI
              AND RS.DATAIN IS NOT NULL
              AND RS.DATAOUT IS NOT NULL
              AND ISNULL(RS.CANCELADA, 0) = 0
              AND CAST(RS.DATAIN AS date) < :query_end
              AND CAST(RS.DATAOUT AS date) > :query_start
            """
        ),
        {
            "alojamento": alojamento_nome,
            "query_start": query_start,
            "query_end": query_end,
        },
    ).mappings().all()

    occupied = set()
    blocked_checkin = set()
    blocked_checkout = set()
    for row in rows:
        data_in = _to_date(row.get("DATAIN"))
        data_out = _to_date(row.get("DATAOUT"))
        if not data_in or not data_out or data_out <= data_in:
            continue
        for day_value in _daterange(max(data_in, start_date), min(data_out, end_date)):
            occupied.add(day_value.isoformat())
        for offset in range(1, gap_days + 1):
            checkout_candidate = date.fromordinal(data_in.toordinal() - offset)
            gap_start = checkout_candidate
            gap_end = data_in
            if start_date <= checkout_candidate < end_date and _range_touches_medium_high_season(gap_start, gap_end):
                blocked_checkout.add(checkout_candidate.isoformat())

            checkin_candidate = date.fromordinal(data_out.toordinal() + offset)
            gap_start = data_out
            gap_end = checkin_candidate
            if start_date <= checkin_candidate < end_date and _range_touches_medium_high_season(gap_start, gap_end):
                blocked_checkin.add(checkin_candidate.isoformat())
    return {
        "occupied": sorted(occupied),
        "blocked_checkin": sorted(blocked_checkin),
        "blocked_checkout": sorted(blocked_checkout),
        "min_nights": min_nights,
    }


def get_noites_ocupadas(al_id, start=None, months=12) -> list[str]:
    return get_calendario_ocupacao(al_id, start=start, months=months).get("occupied", [])


def alojamento_datas_permitidas(al_id, checkin, checkout) -> dict:
    checkin_date = _to_date(checkin)
    checkout_date = _to_date(checkout)
    if not checkin_date or not checkout_date or checkout_date <= checkin_date:
        return {"allowed": False, "errors": ["invalid_dates"], "min_nights": 1}

    start_date = min(checkin_date, checkout_date).replace(day=1)
    months = max(2, ((checkout_date.year - start_date.year) * 12) + checkout_date.month - start_date.month + 2)
    calendario = get_calendario_ocupacao(al_id, start=start_date, months=months)
    min_nights = int(calendario.get("min_nights") or 1)
    errors = []
    if (checkout_date - checkin_date).days < min_nights:
        errors.append("min_nights")
    if checkin_date.isoformat() in set(calendario.get("blocked_checkin") or []):
        errors.append("blocked_checkin")
    if checkout_date.isoformat() in set(calendario.get("blocked_checkout") or []):
        errors.append("blocked_checkout")
    return {"allowed": not errors, "errors": errors, "min_nights": min_nights}


def get_alojamentos_disponiveis_page(checkin=None, checkout=None, hospedes=None, query=None, page=1, per_page=18, lang=None, adultos=None, criancas=None, bebes=None) -> dict:
    checkin_date = _to_date(checkin)
    checkout_date = _to_date(checkout)
    guest_count = _to_int(hospedes)
    adult_count = _to_count(adultos)
    child_count = _to_count(criancas, default=0) or 0
    query_clean = _clean(query)
    try:
        page_number = max(1, int(page or 1))
    except Exception:
        page_number = 1
    try:
        page_size = min(10000, max(1, int(per_page or 30)))
    except Exception:
        page_size = 30

    where = [
        "LTRIM(RTRIM(ISNULL(AL.NOME, ''))) <> ''",
        "ISNULL(AL.INATIVO, 0) = 0",
        "ISNULL(AL.FECHADO, 0) = 0",
    ]
    params = {}

    if query_clean:
        where.append(
            """
            (
                LTRIM(RTRIM(ISNULL(AL.NOME, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI LIKE :query COLLATE SQL_Latin1_General_CP1_CI_AI
                OR LTRIM(RTRIM(ISNULL(AL.NMAIRBNB, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI LIKE :query COLLATE SQL_Latin1_General_CP1_CI_AI
                OR LTRIM(RTRIM(ISNULL(AL.NMPESQUISA, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI LIKE :query COLLATE SQL_Latin1_General_CP1_CI_AI
                OR LTRIM(RTRIM(ISNULL(AL.LOCAL, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI LIKE :query COLLATE SQL_Latin1_General_CP1_CI_AI
                OR LTRIM(RTRIM(ISNULL(AL.MORADA, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI LIKE :query COLLATE SQL_Latin1_General_CP1_CI_AI
                OR LTRIM(RTRIM(ISNULL(AL.ZONA, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI LIKE :query COLLATE SQL_Latin1_General_CP1_CI_AI
            )
            """
        )
        params["query"] = f"%{query_clean}%"

    if checkin_date and checkout_date and checkout_date > checkin_date:
        where.append(
            """
            NOT EXISTS (
                SELECT 1
                FROM dbo.RS AS RS
                WHERE LTRIM(RTRIM(ISNULL(RS.ALOJAMENTO, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI
                    = LTRIM(RTRIM(ISNULL(AL.NOME, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI
                  AND RS.DATAIN IS NOT NULL
                  AND RS.DATAOUT IS NOT NULL
                  AND ISNULL(RS.CANCELADA, 0) = 0
                  AND CAST(RS.DATAIN AS date) < :checkout
                  AND CAST(RS.DATAOUT AS date) > :checkin
            )
            """
        )
        params["checkin"] = checkin_date
        params["checkout"] = checkout_date

    if adult_count:
        where.append(f"({_alojamento_adult_capacity_sql()}) >= :adult_count")
        params["adult_count"] = adult_count
        where.append(f"({_alojamento_capacity_sql()}) >= :guest_count")
        params["guest_count"] = adult_count + child_count
    elif child_count:
        where.append(f"({_alojamento_capacity_sql()}) >= :guest_count")
        params["guest_count"] = child_count
    elif guest_count:
        where.append(f"({_alojamento_capacity_sql()}) >= :guest_count")
        params["guest_count"] = guest_count

    where_sql = " AND ".join(where)
    total = int(db.session.execute(text(_alojamento_count_select(where_sql)), params).scalar() or 0)
    total_pages = max(1, ((total + page_size - 1) // page_size))
    page_number = min(page_number, total_pages)
    start = (page_number - 1) * page_size
    page_params = {**params, "offset": start, "limit": page_size}
    rows = db.session.execute(text(_alojamento_paged_select(where_sql, lang=lang)), page_params).mappings().all()
    alojamentos = [_decorate_alojamento(row) for row in rows]
    return {
        "items": alojamentos,
        "total": total,
        "page": page_number,
        "per_page": page_size,
        "pages": total_pages,
        "has_prev": page_number > 1,
        "has_next": page_number < total_pages,
        "prev_page": page_number - 1 if page_number > 1 else None,
        "next_page": page_number + 1 if page_number < total_pages else None,
    }


def get_alojamentos_disponiveis(checkin=None, checkout=None, hospedes=None, query=None, lang=None, adultos=None, criancas=None, bebes=None) -> list[dict]:
    return get_alojamentos_disponiveis_page(
        checkin=checkin,
        checkout=checkout,
        hospedes=hospedes,
        query=query,
        lang=lang,
        adultos=adultos,
        criancas=criancas,
        bebes=bebes,
        page=1,
        per_page=10000,
    )["items"]


def _price_manager_base_price(alojamento_nome) -> Decimal:
    row = db.session.execute(
        text(
            """
            SELECT TOP 1 PA.PRECO_BASE
            FROM dbo.PR_ALOJAMENTO AS PA
            WHERE LTRIM(RTRIM(ISNULL(PA.AL_NOME, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI
                = LTRIM(RTRIM(:alojamento)) COLLATE SQL_Latin1_General_CP1_CI_AI
              AND ISNULL(PA.ATIVO, 1) = 1
            """
        ),
        {"alojamento": _clean(alojamento_nome)},
    ).mappings().first()
    return _to_decimal((row or {}).get("PRECO_BASE"))


def _price_manager_nightly_prices(alojamento_nome, checkin, checkout) -> list[dict]:
    checkin_date = _to_date(checkin)
    checkout_date = _to_date(checkout)
    if not checkin_date or not checkout_date or checkout_date <= checkin_date:
        return []

    rows = db.session.execute(
        text(
            """
            SELECT
                CAST(D.[DATA] AS date) AS DIA,
                CAST(D.PRECO_FINAL AS decimal(12, 2)) AS PRECO_FINAL
            FROM dbo.PR_CALC_DAY AS D
            WHERE LTRIM(RTRIM(ISNULL(D.AL_NOME, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI
                = LTRIM(RTRIM(:alojamento)) COLLATE SQL_Latin1_General_CP1_CI_AI
              AND CAST(D.[DATA] AS date) >= :checkin
              AND CAST(D.[DATA] AS date) < :checkout
            ORDER BY CAST(D.[DATA] AS date)
            """
        ),
        {
            "alojamento": _clean(alojamento_nome),
            "checkin": checkin_date,
            "checkout": checkout_date,
        },
    ).mappings().all()

    prices_by_day = {row.get("DIA"): _to_decimal(row.get("PRECO_FINAL")) for row in rows}
    fallback_price = _price_manager_base_price(alojamento_nome)
    nightly = []
    for day_value in _daterange(checkin_date, checkout_date):
        price = prices_by_day.get(day_value) or fallback_price
        nightly.append({
            "data": day_value.isoformat(),
            "valor": price,
            "label": _money(price) or "0.00 EUR",
            "fallback": day_value not in prices_by_day,
        })
    return nightly


def calcular_preco(al_id, checkin=None, checkout=None, hospedes=None):
    alojamento = get_alojamento(al_id)
    if not alojamento:
        return {"valor": None, "label": "Preco sob consulta", "noites": 0, "linhas": []}

    checkin_date = _to_date(checkin)
    checkout_date = _to_date(checkout)
    if not checkin_date or not checkout_date or checkout_date <= checkin_date:
        return {
            "valor": None,
            "label": alojamento.get("preco_desde") or "Preco sob consulta",
            "noites": 0,
            "linhas": [],
        }

    noites = (checkout_date - checkin_date).days
    guest_count = _to_int(hospedes, default=1) or 1
    nightly_prices = _price_manager_nightly_prices(alojamento.get("nome_interno"), checkin_date, checkout_date)
    subtotal_noites = sum((_to_decimal(item.get("valor")) for item in nightly_prices), Decimal("0.00")).quantize(_DEC2)
    if subtotal_noites <= 0:
        return {"valor": None, "label": "Preco sob consulta", "noites": noites, "linhas": []}

    tourist_days = min(noites, TOURIST_TAX_MAX_DAYS)
    tourist_tax = (TOURIST_TAX_PER_GUEST_NIGHT * Decimal(guest_count) * Decimal(tourist_days)).quantize(_DEC2)
    extra_rate = _to_decimal(alojamento.get("valor_extra"))
    extra_threshold = _to_count(alojamento.get("extra_mais_que"), default=0) or 0
    extra_guest_count = max(0, guest_count - extra_threshold) if extra_rate > 0 and extra_threshold > 0 else 0
    extra_guest_total = (extra_rate * Decimal(extra_guest_count) * Decimal(noites)).quantize(_DEC2)
    total = (subtotal_noites + extra_guest_total + CLEANING_FEE + tourist_tax).quantize(_DEC2)
    linhas = [
        {"label": f"Noites ({noites})", "value": _money(subtotal_noites)},
    ]
    if extra_guest_total > 0:
        linhas.append({
            "label": f"Hospedes extra ({extra_guest_count} x {noites} noite{'s' if noites != 1 else ''})",
            "value": _money(extra_guest_total),
        })
    linhas.extend([
        {"label": "Taxa de limpeza", "value": _money(CLEANING_FEE)},
        {"label": f"Taxa turistica ({guest_count} hospede{'s' if guest_count != 1 else ''} x {tourist_days} dia{'s' if tourist_days != 1 else ''})", "value": _money(tourist_tax)},
    ])

    return {
        "valor": total,
        "label": _money(total),
        "noites": noites,
        "hospedes": guest_count,
        "precos_noite": nightly_prices,
        "preco_noites": subtotal_noites,
        "preco_noites_label": _money(subtotal_noites),
        "hospedes_extra": extra_guest_count,
        "hospedes_extra_valor_noite": extra_rate,
        "hospedes_extra_valor_noite_label": _money(extra_rate),
        "hospedes_extra_total": extra_guest_total,
        "hospedes_extra_total_label": _money(extra_guest_total),
        "hospedes_extra_limite": extra_threshold,
        "limpeza": CLEANING_FEE,
        "limpeza_label": _money(CLEANING_FEE),
        "taxa_turistica": tourist_tax,
        "taxa_turistica_label": _money(tourist_tax),
        "taxa_turistica_dias": tourist_days,
        "linhas": linhas,
    }


def _normalize_email(value) -> str:
    return _clean(value).lower()


def portal_user_exists(email) -> bool:
    email_normalizado = _normalize_email(email)
    if not email_normalizado:
        return False
    return bool(db.session.execute(
        text(
            """
            SELECT TOP 1 1
            FROM dbo.PB_USERS
            WHERE EMAIL_NORMALIZADO = :email
            """
        ),
        {"email": email_normalizado},
    ).scalar())


def get_portal_user(pbuserstamp: str) -> dict | None:
    user_id = _clean(pbuserstamp)
    if not user_id:
        return None
    row = db.session.execute(
        text(
            """
            SELECT PBUSERSTAMP, NOME, EMAIL, TELEFONE, MORADA, PAIS, NIF,
                   EMAIL_CONFIRMADO, ATIVO
            FROM dbo.PB_USERS
            WHERE PBUSERSTAMP = :user_id
              AND ISNULL(ATIVO, 0) = 1
            """
        ),
        {"user_id": user_id},
    ).mappings().first()
    return dict(row) if row else None


def get_unverified_portal_user_by_email(email: str) -> dict | None:
    email_normalizado = _normalize_email(email)
    if not email_normalizado:
        return None
    row = db.session.execute(
        text(
            """
            SELECT PBUSERSTAMP, NOME, EMAIL
            FROM dbo.PB_USERS
            WHERE EMAIL_NORMALIZADO = :email
              AND ISNULL(ATIVO, 0) = 1
              AND ISNULL(EMAIL_CONFIRMADO, 0) = 0
            """
        ),
        {"email": email_normalizado},
    ).mappings().first()
    return dict(row) if row else None


def autenticar_portal_user(email: str, password: str) -> tuple[dict | None, str]:
    email_normalizado = _normalize_email(email)
    if not email_normalizado or not password:
        return None, "invalid_credentials"
    row = db.session.execute(
        text(
            """
            SELECT PBUSERSTAMP, NOME, EMAIL, PASSWORD_HASH, PASSWORD_ALGO,
                   EMAIL_CONFIRMADO, ATIVO
            FROM dbo.PB_USERS
            WHERE EMAIL_NORMALIZADO = :email
            """
        ),
        {"email": email_normalizado},
    ).mappings().first()
    if not row or not bool(row.get("ATIVO")):
        return None, "invalid_credentials"
    user = dict(row)
    if not verify_password_hash(user, password):
        return None, "invalid_credentials"
    if not bool(user.get("EMAIL_CONFIRMADO")):
        return None, "email_unverified"
    return {
        "id": _clean(user.get("PBUSERSTAMP")),
        "nome": _clean(user.get("NOME")),
        "email": _clean(user.get("EMAIL")),
    }, "ok"


def _create_email_verification_record(pbuserstamp: str) -> dict:
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    verification_id = _new_stamp()
    db.session.execute(
        text(
            """
            INSERT INTO dbo.PB_EMAIL_VERIFICATIONS (
                PBEMAILVERSTAMP, PBUSERSTAMP, TOKEN_HASH, EXPIRA_EM
            )
            VALUES (
                :verification_id, :user_id, :token_hash, DATEADD(hour, 48, SYSUTCDATETIME())
            )
            """
        ),
        {
            "verification_id": verification_id,
            "user_id": _clean(pbuserstamp),
            "token_hash": token_hash,
        },
    )
    return {"id": verification_id, "token": token}


def criar_verificacao_email_portal(pbuserstamp: str) -> dict | None:
    user_id = _clean(pbuserstamp)
    user = db.session.execute(
        text(
            """
            SELECT PBUSERSTAMP, NOME, EMAIL, EMAIL_CONFIRMADO
            FROM dbo.PB_USERS
            WHERE PBUSERSTAMP = :user_id
            """
        ),
        {"user_id": user_id},
    ).mappings().first()
    if not user or bool(user.get("EMAIL_CONFIRMADO")):
        return None
    verification = _create_email_verification_record(user_id)
    db.session.commit()
    return {**verification, "user_id": user_id, "nome": _clean(user.get("NOME")), "email": _clean(user.get("EMAIL"))}


def confirmar_email_portal(token: str) -> str:
    token_value = _clean(token)
    if len(token_value) < 20:
        return "invalid"
    token_hash = hashlib.sha256(token_value.encode("utf-8")).hexdigest()
    row = db.session.execute(
        text(
            """
            SELECT TOP 1
                V.PBEMAILVERSTAMP,
                V.PBUSERSTAMP,
                V.EXPIRA_EM,
                V.USADO_EM,
                U.EMAIL_CONFIRMADO
            FROM dbo.PB_EMAIL_VERIFICATIONS AS V
            INNER JOIN dbo.PB_USERS AS U ON U.PBUSERSTAMP = V.PBUSERSTAMP
            WHERE V.TOKEN_HASH = :token_hash
            """
        ),
        {"token_hash": token_hash},
    ).mappings().first()
    if not row:
        return "invalid"
    if bool(row.get("EMAIL_CONFIRMADO")):
        return "already_confirmed"
    if row.get("USADO_EM") is not None:
        return "used"
    if row.get("EXPIRA_EM") is None or row["EXPIRA_EM"] <= datetime.utcnow():
        return "expired"

    now = datetime.utcnow()
    db.session.execute(
        text(
            """
            UPDATE dbo.PB_USERS
            SET EMAIL_CONFIRMADO = 1,
                EMAIL_CONFIRMADO_EM = :now,
                DTALT = :now
            WHERE PBUSERSTAMP = :user_id
            """
        ),
        {"now": now, "user_id": row["PBUSERSTAMP"]},
    )
    db.session.execute(
        text(
            """
            UPDATE dbo.PB_EMAIL_VERIFICATIONS
            SET USADO_EM = :now
            WHERE PBEMAILVERSTAMP = :verification_id
              AND USADO_EM IS NULL
            """
        ),
        {"now": now, "verification_id": row["PBEMAILVERSTAMP"]},
    )
    db.session.commit()
    return "confirmed"


def _create_password_reset_record(pbuserstamp: str) -> dict:
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    reset_id = _new_stamp()
    db.session.execute(
        text(
            """
            UPDATE dbo.PB_PASSWORD_RESETS
            SET USADO_EM = SYSUTCDATETIME()
            WHERE PBUSERSTAMP = :user_id
              AND USADO_EM IS NULL
            """
        ),
        {"user_id": _clean(pbuserstamp)},
    )
    db.session.execute(
        text(
            """
            INSERT INTO dbo.PB_PASSWORD_RESETS (
                PBPASSWORDRESETSTAMP, PBUSERSTAMP, TOKEN_HASH, EXPIRA_EM
            )
            VALUES (
                :reset_id, :user_id, :token_hash, DATEADD(hour, 1, SYSUTCDATETIME())
            )
            """
        ),
        {
            "reset_id": reset_id,
            "user_id": _clean(pbuserstamp),
            "token_hash": token_hash,
        },
    )
    return {"id": reset_id, "token": token}


def criar_password_reset_portal(email: str) -> dict | None:
    email_normalizado = _normalize_email(email)
    if not email_normalizado:
        return None
    user = db.session.execute(
        text(
            """
            SELECT PBUSERSTAMP, NOME, EMAIL
            FROM dbo.PB_USERS
            WHERE EMAIL_NORMALIZADO = :email
              AND ISNULL(ATIVO, 0) = 1
              AND ISNULL(EMAIL_CONFIRMADO, 0) = 1
            """
        ),
        {"email": email_normalizado},
    ).mappings().first()
    if not user:
        return None
    reset = _create_password_reset_record(user["PBUSERSTAMP"])
    db.session.commit()
    return {
        **reset,
        "user_id": _clean(user.get("PBUSERSTAMP")),
        "nome": _clean(user.get("NOME")),
        "email": _clean(user.get("EMAIL")),
    }


def redefinir_password_portal(token: str, password: str) -> str:
    token_value = _clean(token)
    if len(token_value) < 20 or len(password or "") < 8:
        return "invalid"
    token_hash = hashlib.sha256(token_value.encode("utf-8")).hexdigest()
    row = db.session.execute(
        text(
            """
            SELECT TOP 1 R.PBPASSWORDRESETSTAMP, R.PBUSERSTAMP, R.EXPIRA_EM, R.USADO_EM
            FROM dbo.PB_PASSWORD_RESETS AS R
            INNER JOIN dbo.PB_USERS AS U ON U.PBUSERSTAMP = R.PBUSERSTAMP
            WHERE R.TOKEN_HASH = :token_hash
              AND ISNULL(U.ATIVO, 0) = 1
              AND ISNULL(U.EMAIL_CONFIRMADO, 0) = 1
            """
        ),
        {"token_hash": token_hash},
    ).mappings().first()
    if not row:
        return "invalid"
    if row.get("USADO_EM") is not None:
        return "used"
    if row.get("EXPIRA_EM") is None or row["EXPIRA_EM"] <= datetime.utcnow():
        return "expired"

    password_hash, password_algo = hash_password(password)
    now = datetime.utcnow()
    db.session.execute(
        text(
            """
            UPDATE dbo.PB_USERS
            SET PASSWORD_HASH = :password_hash,
                PASSWORD_ALGO = :password_algo,
                DTALT = :now
            WHERE PBUSERSTAMP = :user_id
            """
        ),
        {
            "password_hash": password_hash,
            "password_algo": password_algo,
            "now": now,
            "user_id": row["PBUSERSTAMP"],
        },
    )
    db.session.execute(
        text(
            """
            UPDATE dbo.PB_PASSWORD_RESETS
            SET USADO_EM = :now
            WHERE PBUSERSTAMP = :user_id
              AND USADO_EM IS NULL
            """
        ),
        {"now": now, "user_id": row["PBUSERSTAMP"]},
    )
    db.session.commit()
    return "updated"


def criar_pedido_reserva(
    al_id,
    params: dict,
    customer: dict,
    *,
    create_account=False,
    password=None,
    authenticated_user_id=None,
    ip="",
    user_agent="",
) -> dict:
    alojamento = get_alojamento(al_id)
    if not alojamento:
        raise ValueError("alojamento_inexistente")

    checkin_date = _to_date(params.get("checkin"))
    checkout_date = _to_date(params.get("checkout"))
    if not checkin_date or not checkout_date or checkout_date <= checkin_date:
        raise ValueError("datas_invalidas")

    if not alojamento_disponivel(al_id, checkin_date, checkout_date):
        raise ValueError("indisponivel")
    date_policy = alojamento_datas_permitidas(al_id, checkin_date, checkout_date)
    if not date_policy.get("allowed"):
        raise ValueError("datas_nao_permitidas")

    adultos = _to_count(params.get("adultos"), default=0) or 0
    criancas = _to_count(params.get("criancas"), default=0) or 0
    bebes = _to_count(params.get("bebes"), default=0) or 0
    hospedes = adultos + criancas
    preco = calcular_preco(al_id, checkin_date, checkout_date, hospedes)
    noites = (checkout_date - checkin_date).days

    pbuserstamp = None
    email_verification = None
    email_normalizado = _normalize_email(customer.get("email"))
    if authenticated_user_id:
        authenticated_user = get_portal_user(authenticated_user_id)
        if not authenticated_user or not bool(authenticated_user.get("EMAIL_CONFIRMADO")):
            raise ValueError("conta_invalida")
        pbuserstamp = _clean(authenticated_user.get("PBUSERSTAMP"))
    elif create_account:
        if portal_user_exists(email_normalizado):
            raise ValueError("email_ja_registado")
        password_hash, password_algo = hash_password(password or "")
        pbuserstamp = _new_stamp()
        db.session.execute(
            text(
                """
                INSERT INTO dbo.PB_USERS (
                    PBUSERSTAMP, NOME, EMAIL, EMAIL_NORMALIZADO, TELEFONE, MORADA, PAIS, NIF,
                    PASSWORD_HASH, PASSWORD_ALGO
                )
                VALUES (
                    :stamp, :nome, :email, :email_normalizado, :telefone, :morada, :pais, :nif,
                    :password_hash, :password_algo
                )
                """
            ),
            {
                "stamp": pbuserstamp,
                "nome": _clean(customer.get("nome")),
                "email": _clean(customer.get("email")),
                "email_normalizado": email_normalizado,
                "telefone": _clean(customer.get("telefone")),
                "morada": _clean(customer.get("morada")),
                "pais": _clean(customer.get("pais")),
                "nif": _clean(customer.get("nif")),
                "password_hash": password_hash,
                "password_algo": password_algo,
            },
        )
        email_verification = _create_email_verification_record(pbuserstamp)

    request_stamp = _new_stamp()
    dados = {
        "alojamento": {"id": alojamento.get("id"), "nome": alojamento.get("nome"), "nome_interno": alojamento.get("nome_interno")},
        "datas": {"checkin": checkin_date.isoformat(), "checkout": checkout_date.isoformat(), "noites": noites},
        "hospedes": {"adultos": adultos, "criancas": criancas, "bebes": bebes},
        "preco": {
            "valor": str(preco.get("valor") or ""),
            "label": preco.get("label") or "",
            "linhas": preco.get("linhas") or [],
        },
    }
    db.session.execute(
        text(
            """
            INSERT INTO dbo.PB_BOOKING_REQUESTS (
                PBBKSTAMP, PBUSERSTAMP, ALSTAMP, AL_NOME, CHECKIN, CHECKOUT, NOITES,
                ADULTOS, CRIANCAS, BEBES,
                CLIENTE_NOME, CLIENTE_EMAIL, CLIENTE_TELEFONE, CLIENTE_MORADA, CLIENTE_PAIS, CLIENTE_NIF,
                CRIOU_CONTA, PRECO_ESTIMADO, PRECO_LABEL, OBSERVACOES, DADOS_JSON, IP_CLIENTE, USER_AGENT
            )
            VALUES (
                :stamp, :user_stamp, :alstamp, :al_nome, :checkin, :checkout, :noites,
                :adultos, :criancas, :bebes,
                :nome, :email, :telefone, :morada, :pais, :nif,
                :criou_conta, :preco_estimado, :preco_label, :observacoes, :dados_json, :ip, :user_agent
            )
            """
        ),
        {
            "stamp": request_stamp,
            "user_stamp": pbuserstamp,
            "alstamp": alojamento.get("id"),
            "al_nome": alojamento.get("nome"),
            "checkin": checkin_date,
            "checkout": checkout_date,
            "noites": noites,
            "adultos": adultos,
            "criancas": criancas,
            "bebes": bebes,
            "nome": _clean(customer.get("nome")),
            "email": _clean(customer.get("email")),
            "telefone": _clean(customer.get("telefone")),
            "morada": _clean(customer.get("morada")),
            "pais": _clean(customer.get("pais")),
            "nif": _clean(customer.get("nif")),
            "criou_conta": 1 if create_account else 0,
            "preco_estimado": preco.get("valor"),
            "preco_label": preco.get("label") or "",
            "observacoes": _clean(customer.get("observacoes")),
            "dados_json": json.dumps(dados, ensure_ascii=False),
            "ip": _clean(ip)[:80],
            "user_agent": _clean(user_agent)[:500],
        },
    )
    db.session.commit()
    return {
        "id": request_stamp,
        "user_id": pbuserstamp,
        "created_account": bool(create_account),
        "preco": preco,
        "alojamento": alojamento,
        "checkin": checkin_date,
        "checkout": checkout_date,
        "noites": noites,
        "email_verification": email_verification,
    }


def _portal_payment_table_exists(table_name: str) -> bool:
    key = f"portal-payment:{table_name}"
    if key in _TABLE_EXISTS_CACHE:
        return _TABLE_EXISTS_CACHE[key]
    exists = bool(db.session.execute(
        text(
            """
            SELECT TOP 1 1
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = :table_name
            """
        ),
        {"table_name": table_name},
    ).scalar())
    _TABLE_EXISTS_CACHE[key] = exists
    return exists


def _portal_payment_require_table() -> None:
    if not _portal_payment_table_exists("PB_STRIPE_TEST_PAYMENTS"):
        raise PortalPaymentConfigurationError(
            "O pagamento de teste ainda nao esta configurado. Aplique a migracao do portal."
        )


def _portal_para_text(code: str) -> str:
    key = _clean(code)
    if not key:
        return ""
    try:
        row = db.session.execute(
            text(
                """
                SELECT TOP 1 CVALOR
                FROM dbo.PARA
                WHERE UPPER(LTRIM(RTRIM(PARAMETRO))) = UPPER(LTRIM(RTRIM(:code)))
                """
            ),
            {"code": key},
        ).mappings().first()
        if row:
            value = _clean(row.get("CVALOR"))
            if value:
                return value
    except Exception:
        current_app.logger.exception("Erro ao ler parametro Stripe de teste do portal.")
    try:
        return _clean((current_app.config.get("PARA_VALUES") or {}).get(key))
    except Exception:
        return ""


def _portal_stripe_test_secret_key() -> str:
    secret_key = _portal_para_text("SHOP_STRIPE_SECRET_KEY")
    if secret_key.startswith("sk_test_"):
        return secret_key
    if secret_key:
        raise PortalPaymentConfigurationError(
            "A configuracao Stripe ainda nao esta preparada para este ambiente."
        )
    raise PortalPaymentConfigurationError("A configuracao Stripe esta em falta.")


def _portal_stripe_test_request(method: str, path: str, data=None, *, idempotency_key: str = "") -> dict:
    secret_key = _portal_stripe_test_secret_key()
    method = _clean(method).upper() or "GET"
    resource = _clean(path)
    if not resource.startswith("/"):
        resource = f"/{resource}"
    payload = None
    if data:
        encoded = urlencode(data, doseq=True)
        if method == "GET":
            resource = f"{resource}{'&' if '?' in resource else '?'}{encoded}"
        else:
            payload = encoded.encode("utf-8")
    request_obj = Request(
        f"https://api.stripe.com{resource}",
        data=payload,
        method=method,
        headers={"Authorization": f"Bearer {secret_key}"},
    )
    if payload is not None:
        request_obj.add_header("Content-Type", "application/x-www-form-urlencoded")
    if idempotency_key:
        request_obj.add_header("Idempotency-Key", idempotency_key)
    try:
        with urlopen(request_obj, timeout=35) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            message = json.loads(body).get("error", {}).get("message") or body
        except Exception:
            message = body
        raise PortalPaymentError(f"Stripe: {message}") from exc
    except URLError as exc:
        raise PortalPaymentError("A Stripe esta indisponivel. Tente novamente daqui a instantes.") from exc
    try:
        return json.loads(raw)
    except Exception as exc:
        raise PortalPaymentError("A Stripe devolveu uma resposta invalida.") from exc


def _portal_test_payment_booking(request_id: str, user_id: str | None = None) -> dict | None:
    owner_filter = "AND PBUSERSTAMP = :user_id" if _clean(user_id) else ""
    return db.session.execute(
        text(
            f"""
            SELECT TOP 1 PBBKSTAMP, PBUSERSTAMP, AL_NOME, CHECKIN, CHECKOUT,
                   CLIENTE_EMAIL, PRECO_ESTIMADO, PRECO_LABEL, ESTADO
            FROM dbo.PB_BOOKING_REQUESTS
            WHERE PBBKSTAMP = :request_id
              {owner_filter}
            """
        ),
        {"request_id": _clean(request_id), "user_id": _clean(user_id)},
    ).mappings().first()


def criar_checkout_teste_portal(
    request_id: str,
    user_id: str | None = None,
    *,
    success_url: str,
    cancel_url: str,
    lang: str = "pt",
) -> dict:
    _portal_payment_require_table()
    _portal_stripe_test_secret_key()
    booking = _portal_test_payment_booking(request_id, user_id)
    if not booking or _clean(booking.get("ESTADO")).upper() != "PENDENTE":
        raise PortalPaymentError("O pedido de reserva nao esta disponivel para pagamento de teste.")
    amount = _to_decimal(booking.get("PRECO_ESTIMADO"))
    if amount <= 0:
        raise PortalPaymentError("O pedido de reserva nao tem um valor valido para testar o pagamento.")

    payment_id = _new_stamp()
    idempotency_key = f"portobreak-test-{payment_id.replace('-', '')[:24]}"
    db.session.execute(
        text(
            """
            INSERT INTO dbo.PB_STRIPE_TEST_PAYMENTS
            (
                PBPAYSTAMP, PBBKSTAMP, PBUSERSTAMP, ESTADO, MOEDA, VALOR,
                IDEMPOTENCY_KEY, DTCRI, DTALT
            )
            VALUES
            (
                :payment_id, :request_id, :user_id, 'CRIADO', 'EUR', :amount,
                :idempotency_key, SYSUTCDATETIME(), SYSUTCDATETIME()
            )
            """
        ),
        {
            "payment_id": payment_id,
            "request_id": booking["PBBKSTAMP"],
            "user_id": _clean(booking.get("PBUSERSTAMP")) or None,
            "amount": amount,
            "idempotency_key": idempotency_key,
        },
    )
    db.session.commit()
    try:
        stripe_session = _portal_stripe_test_request(
            "POST",
            "/v1/checkout/sessions",
            {
                "mode": "payment",
                "success_url": success_url,
                "cancel_url": cancel_url,
                "locale": lang if lang in {"pt", "en", "es", "fr"} else "auto",
                "client_reference_id": payment_id,
                "payment_method_types[0]": "card",
                "metadata[pb_payment_id]": payment_id,
                "metadata[pb_booking_request_id]": booking["PBBKSTAMP"],
                "metadata[environment]": "test",
                "line_items[0][quantity]": "1",
                "line_items[0][price_data][currency]": "eur",
                "line_items[0][price_data][unit_amount]": str(int(amount * 100)),
                "line_items[0][price_data][product_data][name]": "Pedido de reserva Porto Break",
                "line_items[0][price_data][product_data][description]": (
                    f"{_clean(booking.get('AL_NOME'))[:120]} · "
                    f"{_to_date(booking.get('CHECKIN')).isoformat()} a {_to_date(booking.get('CHECKOUT')).isoformat()}"
                )[:250],
            },
            idempotency_key=idempotency_key,
        )
        checkout_session_id = _clean(stripe_session.get("id"))
        checkout_url = _clean(stripe_session.get("url"))
        if not checkout_session_id or not checkout_url:
            raise PortalPaymentError("Nao foi possivel criar a sessao de checkout Stripe.")
        db.session.execute(
            text(
                """
                UPDATE dbo.PB_STRIPE_TEST_PAYMENTS
                SET CHECKOUT_SESSION_ID = :session_id,
                    PAYMENT_INTENT_ID = :payment_intent_id,
                    STRIPE_STATUS = :stripe_status,
                    DTALT = SYSUTCDATETIME()
                WHERE PBPAYSTAMP = :payment_id
                """
            ),
            {
                "payment_id": payment_id,
                "session_id": checkout_session_id,
                "payment_intent_id": _clean(stripe_session.get("payment_intent")) or None,
                "stripe_status": _clean(stripe_session.get("status")) or None,
            },
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        try:
            db.session.execute(
                text(
                    """
                    UPDATE dbo.PB_STRIPE_TEST_PAYMENTS
                    SET ESTADO = 'FALHADO', DTALT = SYSUTCDATETIME()
                    WHERE PBPAYSTAMP = :payment_id
                    """
                ),
                {"payment_id": payment_id},
            )
            db.session.commit()
        except Exception:
            db.session.rollback()
        raise
    return {
        "id": payment_id,
        "checkout_url": checkout_url,
        "session_id": checkout_session_id,
    }


def sincronizar_checkout_teste_portal(session_id: str, user_id: str | None = None) -> dict | None:
    _portal_payment_require_table()
    owner_filter = "AND PBUSERSTAMP = :user_id" if _clean(user_id) else ""
    payment = db.session.execute(
        text(
            f"""
            SELECT TOP 1 PBPAYSTAMP, PBBKSTAMP, ESTADO, VALOR, MOEDA, CHECKOUT_SESSION_ID
            FROM dbo.PB_STRIPE_TEST_PAYMENTS
            WHERE CHECKOUT_SESSION_ID = :session_id
              {owner_filter}
            """
        ),
        {"session_id": _clean(session_id), "user_id": _clean(user_id)},
    ).mappings().first()
    if not payment:
        return None
    stripe_session = _portal_stripe_test_request(
        "GET", f"/v1/checkout/sessions/{_clean(session_id)}"
    )
    paid = (
        _clean(stripe_session.get("status")) == "complete"
        and _clean(stripe_session.get("payment_status")) == "paid"
    )
    if paid:
        state = "PAGO_TESTE"
    elif _clean(stripe_session.get("status")) == "expired":
        state = "EXPIRADO"
    else:
        state = "CRIADO"
    db.session.execute(
        text(
            """
            UPDATE dbo.PB_STRIPE_TEST_PAYMENTS
            SET ESTADO = :state,
                PAYMENT_INTENT_ID = :payment_intent_id,
                STRIPE_STATUS = :stripe_status,
                DTALT = SYSUTCDATETIME()
            WHERE PBPAYSTAMP = :payment_id
            """
        ),
        {
            "payment_id": payment["PBPAYSTAMP"],
            "state": state,
            "payment_intent_id": _clean(stripe_session.get("payment_intent")) or None,
            "stripe_status": _clean(stripe_session.get("payment_status") or stripe_session.get("status")) or None,
        },
    )
    db.session.commit()
    reservation = registar_reserva_portal_pagamento(payment["PBPAYSTAMP"]) if paid else None
    return {
        "id": payment["PBPAYSTAMP"],
        "booking_id": payment["PBBKSTAMP"],
        "paid": paid,
        "state": state,
        "amount": _to_decimal(payment.get("VALOR")),
        "currency": _clean(payment.get("MOEDA")) or "EUR",
        "reservation_code": (reservation or {}).get("reserva"),
        "rsstamp": (reservation or {}).get("rsstamp"),
    }


def registar_reserva_portal_pagamento(payment_id: str) -> dict | None:
    """Create the operational RS reservation exactly once after a successful Stripe payment."""
    _portal_payment_require_table()
    payment = db.session.execute(
        text(
            """
            SELECT TOP 1
                P.PBPAYSTAMP, P.PBBKSTAMP, P.RSSTAMP, P.ESTADO AS PAGAMENTO_ESTADO,
                B.ALSTAMP, B.CHECKIN, B.CHECKOUT, B.NOITES, B.ADULTOS, B.CRIANCAS, B.BEBES,
                B.CLIENTE_NOME, B.CLIENTE_EMAIL, B.CLIENTE_TELEFONE, B.CLIENTE_MORADA,
                B.CLIENTE_PAIS, B.CLIENTE_NIF, B.PRECO_ESTIMADO, B.OBSERVACOES,
                LTRIM(RTRIM(ISNULL(AL.NOME, ''))) AS ALOJAMENTO_INTERNO
            FROM dbo.PB_STRIPE_TEST_PAYMENTS AS P
            INNER JOIN dbo.PB_BOOKING_REQUESTS AS B ON B.PBBKSTAMP = P.PBBKSTAMP
            INNER JOIN dbo.AL AS AL ON AL.ALSTAMP = B.ALSTAMP
            WHERE P.PBPAYSTAMP = :payment_id
            """
        ),
        {"payment_id": _clean(payment_id)},
    ).mappings().first()
    if not payment or _clean(payment.get("PAGAMENTO_ESTADO")) != "PAGO_TESTE":
        return None

    existing_stamp = _clean(payment.get("RSSTAMP"))
    if existing_stamp:
        existing = db.session.execute(
            text("SELECT TOP 1 RSSTAMP, RESERVA FROM dbo.RS WHERE RSSTAMP = :rsstamp"),
            {"rsstamp": existing_stamp},
        ).mappings().first()
        if existing:
            return {"rsstamp": existing["RSSTAMP"], "reserva": existing["RESERVA"]}

    alojamento = _clean(payment.get("ALOJAMENTO_INTERNO"))
    checkin = _to_date(payment.get("CHECKIN"))
    checkout = _to_date(payment.get("CHECKOUT"))
    if not alojamento or not checkin or not checkout or checkout <= checkin:
        raise PortalPaymentError("Nao foi possivel registar a reserva paga.")

    conflict = db.session.execute(
        text(
            """
            SELECT TOP 1 RSSTAMP
            FROM dbo.RS WITH (UPDLOCK, HOLDLOCK)
            WHERE LTRIM(RTRIM(ISNULL(ALOJAMENTO, ''))) COLLATE SQL_Latin1_General_CP1_CI_AI
                    = LTRIM(RTRIM(:alojamento)) COLLATE SQL_Latin1_General_CP1_CI_AI
              AND ISNULL(CANCELADA, 0) = 0
              AND CAST(DATAIN AS date) < :checkout
              AND CAST(DATAOUT AS date) > :checkin
            """
        ),
        {"alojamento": alojamento, "checkin": checkin, "checkout": checkout},
    ).scalar()
    if conflict:
        raise PortalPaymentError("As datas deixaram de estar disponiveis antes de a reserva ser registada.")

    rsstamp = _new_stamp().replace("-", "")[:25].upper()
    reservation_code = f"PB{payment['PBPAYSTAMP'].replace('-', '')[:12].upper()}"
    total = _to_decimal(payment.get("PRECO_ESTIMADO"))
    cleaning = CLEANING_FEE if total >= CLEANING_FEE else Decimal("0.00")
    stay_value = (total - cleaning).quantize(_DEC2)
    obs = f"PortoBreak online | Stripe {payment['PBPAYSTAMP']}"
    extra_obs = _clean(payment.get("OBSERVACOES"))
    if extra_obs:
        obs = f"{obs} | {extra_obs}"

    db.session.execute(
        text(
            """
            INSERT INTO dbo.RS
            (
                RSSTAMP, ALOJAMENTO, RDATA, ORIGEM, RESERVA,
                DATAIN, DATAOUT, HORAIN, HORAOUT, NOITES,
                NOME, PAIS, ADULTOS, CRIANCAS, BEBES,
                ESTADIA, LIMPEZA, COMISSAO, OBS,
                FTNOME, FTMORADA, FTLOCAL, FTNCONT, FTEMAIL
            )
            VALUES
            (
                :rsstamp, :alojamento, CAST(GETDATE() AS date), 'PORTOBREAK', :reserva,
                :checkin, :checkout, '15:00', '11:00', :noites,
                :nome, :pais, :adultos, :criancas, :bebes,
                :estadia, :limpeza, 0, :obs,
                :ftnome, :ftmorada, :ftlocal, :ftncont, :ftemail
            )
            """
        ),
        {
            "rsstamp": rsstamp,
            "alojamento": alojamento[:60],
            "reserva": reservation_code[:25],
            "checkin": checkin,
            "checkout": checkout,
            "noites": _to_count(payment.get("NOITES"), default=0) or 0,
            "nome": _clean(payment.get("CLIENTE_NOME"))[:60],
            "pais": _clean(payment.get("CLIENTE_PAIS"))[:60],
            "adultos": _to_count(payment.get("ADULTOS"), default=0) or 0,
            "criancas": _to_count(payment.get("CRIANCAS"), default=0) or 0,
            "bebes": _to_count(payment.get("BEBES"), default=0) or 0,
            "estadia": stay_value,
            "limpeza": cleaning,
            "obs": obs[:250],
            "ftnome": _clean(payment.get("CLIENTE_NOME"))[:55],
            "ftmorada": _clean(payment.get("CLIENTE_MORADA"))[:55],
            "ftlocal": _clean(payment.get("CLIENTE_PAIS"))[:43],
            "ftncont": _clean(payment.get("CLIENTE_NIF"))[:20],
            "ftemail": _clean(payment.get("CLIENTE_EMAIL"))[:200],
        },
    )
    db.session.execute(
        text(
            """
            UPDATE dbo.PB_STRIPE_TEST_PAYMENTS
            SET RSSTAMP = :rsstamp, DTALT = SYSUTCDATETIME()
            WHERE PBPAYSTAMP = :payment_id
            """
        ),
        {"rsstamp": rsstamp, "payment_id": payment["PBPAYSTAMP"]},
    )
    db.session.execute(
        text(
            """
            UPDATE dbo.PB_BOOKING_REQUESTS
            SET ESTADO = 'CONFIRMADO', DTALT = SYSUTCDATETIME()
            WHERE PBBKSTAMP = :booking_id
            """
        ),
        {"booking_id": payment["PBBKSTAMP"]},
    )
    db.session.commit()
    return {"rsstamp": rsstamp, "reserva": reservation_code[:25]}
