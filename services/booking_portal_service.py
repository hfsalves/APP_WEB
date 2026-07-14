from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from models import db


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


def get_noites_ocupadas(al_id, start=None, months=12) -> list[str]:
    al_id_clean = _clean(al_id)
    start_date = _to_date(start) or date.today()
    start_date = start_date.replace(day=1)
    end_date = _add_months(start_date, months)
    if not al_id_clean:
        return []

    row = db.session.execute(
        text(
            """
            SELECT TOP 1 LTRIM(RTRIM(ISNULL(AL.NOME, ''))) AS NOME
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
    if not alojamento_nome:
        return []

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
              AND CAST(RS.DATAIN AS date) < :end_date
              AND CAST(RS.DATAOUT AS date) > :start_date
            """
        ),
        {
            "alojamento": alojamento_nome,
            "start_date": start_date,
            "end_date": end_date,
        },
    ).mappings().all()

    occupied = set()
    for row in rows:
        data_in = _to_date(row.get("DATAIN"))
        data_out = _to_date(row.get("DATAOUT"))
        if not data_in or not data_out or data_out <= data_in:
            continue
        for day_value in _daterange(max(data_in, start_date), min(data_out, end_date)):
            occupied.add(day_value.isoformat())
    return sorted(occupied)


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
        "linhas": [
            {"label": f"Noites ({noites})", "value": _money(subtotal_noites)},
            {"label": f"Hospedes extra ({extra_guest_count} x {noites} noite{'s' if noites != 1 else ''})", "value": _money(extra_guest_total)} if extra_guest_total > 0 else None,
            {"label": "Taxa de limpeza", "value": _money(CLEANING_FEE)},
            {"label": f"Taxa turistica ({guest_count} hospede{'s' if guest_count != 1 else ''} x {tourist_days} dia{'s' if tourist_days != 1 else ''})", "value": _money(tourist_tax)},
        ],
    }
