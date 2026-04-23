from __future__ import annotations

import json
import logging
import os
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

from flask import current_app, has_app_context
from sqlalchemy import text

from i18n import (
    BASE_LANGUAGE,
    LANGUAGE_LABELS,
    SUPPORTED_LANGUAGES,
    i18n_enabled,
    normalize_language,
)

logger = logging.getLogger("stationzero.db_i18n")

DB_TRANSLATION_TABLE = "I18N_TRADUCOES"
DB_TRANSLATION_MAX_LEN = 255
DB_TRANSLATION_BATCH_SIZE = 20
TRANSLATABLE_ORIGINS = {
    "MENU": {
        "table": "MENU",
        "stamp_column": "MENUSTAMP",
        "text_column": "NOME",
    },
    "CAMPOS": {
        "table": "CAMPOS",
        "stamp_column": "CAMPOSSTAMP",
        "text_column": "DESCRICAO",
    },
}

_DB_TRANSLATIONS_CACHE: dict[str, dict[str, dict[str, str]]] = {}
_DB_TRANSLATIONS_CACHE_LOADED = False


class DbI18nServiceError(Exception):
    pass


class DbI18nValidationError(DbI18nServiceError):
    pass


def clear_db_translations_cache() -> None:
    global _DB_TRANSLATIONS_CACHE_LOADED
    _DB_TRANSLATIONS_CACHE.clear()
    _DB_TRANSLATIONS_CACHE_LOADED = False


def _trimmed_text(value: Any, limit: int = DB_TRANSLATION_MAX_LEN) -> str:
    text_value = str(value or "").strip()
    return text_value[:limit]


def _normalize_origin(value: Any) -> str:
    origin = str(value or "").strip().upper()
    return origin if origin in TRANSLATABLE_ORIGINS else ""


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return int(value) == 1
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "sim", "s", "on"}


def _param_value_from_row(row: dict[str, Any] | None) -> str:
    data = dict(row or {})
    tipo = str(data.get("TIPO") or "").strip().upper()
    if tipo == "N":
        try:
            return str(data.get("NVALOR") or "")
        except Exception:
            return ""
    if tipo == "D":
        value = data.get("DVALOR")
        try:
            return value.strftime("%Y-%m-%d")
        except Exception:
            return str(value or "")
    if tipo == "L":
        return "1" if bool(data.get("LVALOR") or 0) else "0"
    return str(data.get("CVALOR") or "").strip()


def _para_value(session, code: str, default: str = "") -> str:
    key = str(code or "").strip()
    if not key:
        return default

    if has_app_context():
        try:
            para_map = current_app.config.get("PARA_VALUES") or {}
            value = para_map.get(key)
            if value in (None, ""):
                value = para_map.get(key.upper())
            if value not in (None, ""):
                return str(value).strip()
        except Exception:
            pass

    try:
        row = session.execute(
            text(
                """
                SELECT TOP 1 PARAMETRO, TIPO, CVALOR, DVALOR, NVALOR, LVALOR
                FROM dbo.PARA
                WHERE UPPER(LTRIM(RTRIM(PARAMETRO))) = UPPER(LTRIM(RTRIM(:code)))
                """
            ),
            {"code": key},
        ).mappings().first()
        if not row:
            return default
        value = _param_value_from_row(dict(row))
        return value if str(value).strip() != "" else default
    except Exception:
        return default


def _translation_api_key(session) -> str:
    return (
        _para_value(session, "SHOP_TRANSLATE_OPENAI_API_KEY")
        or _para_value(session, "OPENAI_API_KEY")
        or os.getenv("SHOP_TRANSLATE_OPENAI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or ""
    ).strip()


def _translation_model(session) -> str:
    return (
        _para_value(session, "SHOP_TRANSLATE_MODEL")
        or _para_value(session, "OPENAI_TRANSLATE_MODEL")
        or _para_value(session, "OPENAI_MODEL")
        or os.getenv("SHOP_TRANSLATE_MODEL")
        or os.getenv("OPENAI_TRANSLATE_MODEL")
        or os.getenv("OPENAI_MODEL")
        or "gpt-4o-mini"
    ).strip()


def _extract_openai_text(payload: dict[str, Any]) -> str:
    direct = str(payload.get("output_text") or "").strip()
    if direct:
        return direct
    for output in payload.get("output") or []:
        for content in output.get("content") or []:
            if content.get("type") == "output_text":
                text_value = str(content.get("text") or "").strip()
                if text_value:
                    return text_value
    return ""


def _strip_json_fence(raw_text: str) -> str:
    text_value = str(raw_text or "").strip()
    if not text_value.startswith("```"):
        return text_value
    lines = text_value.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _language_display_name(language: Any) -> str:
    language_key = normalize_language(language) or BASE_LANGUAGE
    return LANGUAGE_LABELS.get(language_key, language_key)


def get_db_translation_runtime_meta(session) -> dict[str, Any]:
    api_key = _translation_api_key(session)
    return {
        "auto_translate_available": bool(api_key),
        "translation_model": (_translation_model(session) if api_key else ""),
    }


def db_translation_table_exists(session) -> bool:
    exists = session.execute(
        text("SELECT OBJECT_ID('dbo.I18N_TRADUCOES', 'U')")
    ).scalar()
    return exists is not None


def ensure_db_translation_table(session) -> bool:
    if db_translation_table_exists(session):
        return False

    try:
        session.execute(
            text(
                """
                IF OBJECT_ID('dbo.I18N_TRADUCOES', 'U') IS NULL
                BEGIN
                    CREATE TABLE dbo.I18N_TRADUCOES
                    (
                        ORIGEM   varchar(20)   NOT NULL,
                        ORISTAMP varchar(25)   NOT NULL,
                        IDIOMA   varchar(10)   NOT NULL,
                        TRADUCAO nvarchar(255) NOT NULL
                            CONSTRAINT DF_I18N_TRADUCOES_TRADUCAO DEFAULT N'',
                        CONSTRAINT PK_I18N_TRADUCOES PRIMARY KEY (ORIGEM, ORISTAMP, IDIOMA),
                        CONSTRAINT CK_I18N_TRADUCOES_ORIGEM CHECK (ORIGEM IN ('MENU', 'CAMPOS'))
                    )
                END
                """
            )
        )
        session.commit()
        logger.info("Tabela dbo.I18N_TRADUCOES criada automaticamente")
        return True
    except Exception:
        session.rollback()
        raise


def _load_source_rows(session) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for origin, cfg in TRANSLATABLE_ORIGINS.items():
        source_rows = session.execute(
            text(
                f"""
                SELECT
                    '{origin}' AS ORIGEM,
                    LTRIM(RTRIM(ISNULL({cfg['stamp_column']}, ''))) AS ORISTAMP,
                    LTRIM(RTRIM(ISNULL({cfg['text_column']}, ''))) AS TEXTO
                FROM dbo.{cfg['table']}
                WHERE LTRIM(RTRIM(ISNULL({cfg['stamp_column']}, ''))) <> ''
                """
            )
        ).mappings().all()
        rows.extend(
            {
                "ORIGEM": origin,
                "ORISTAMP": str(row.get("ORISTAMP") or "").strip(),
                "TEXTO": _trimmed_text(row.get("TEXTO")),
            }
            for row in source_rows
            if str(row.get("ORISTAMP") or "").strip()
        )
    return rows


def reload_db_translations(session) -> dict[str, dict[str, dict[str, str]]]:
    global _DB_TRANSLATIONS_CACHE_LOADED
    if not i18n_enabled():
        clear_db_translations_cache()
        return {}
    if not db_translation_table_exists(session):
        clear_db_translations_cache()
        return {}

    rows = session.execute(
        text(
            """
            SELECT ORIGEM, ORISTAMP, IDIOMA, TRADUCAO
            FROM dbo.I18N_TRADUCOES
            """
        )
    ).mappings().all()

    cache: dict[str, dict[str, dict[str, str]]] = {}
    for row in rows:
        language = normalize_language(row.get("IDIOMA")) or BASE_LANGUAGE
        origin = str(row.get("ORIGEM") or "").strip().upper()
        stamp = str(row.get("ORISTAMP") or "").strip()
        if not origin or not stamp:
            continue
        cache.setdefault(language, {}).setdefault(origin, {})[stamp] = _trimmed_text(row.get("TRADUCAO"))

    _DB_TRANSLATIONS_CACHE.clear()
    _DB_TRANSLATIONS_CACHE.update(cache)
    _DB_TRANSLATIONS_CACHE_LOADED = True
    return cache


def ensure_db_translations_cache(session, force: bool = False) -> bool:
    if not i18n_enabled():
        clear_db_translations_cache()
        return False
    if force or not _DB_TRANSLATIONS_CACHE_LOADED:
        reload_db_translations(session)
    return _DB_TRANSLATIONS_CACHE_LOADED


def sync_db_translations(session) -> dict[str, int]:
    if not i18n_enabled():
        clear_db_translations_cache()
        return {"sources": 0, "inserted": 0, "updated": 0}

    ensure_db_translation_table(session)
    source_rows = _load_source_rows(session)
    existing_rows = session.execute(
        text(
            """
            SELECT ORIGEM, ORISTAMP, IDIOMA, TRADUCAO
            FROM dbo.I18N_TRADUCOES
            """
        )
    ).mappings().all()

    existing_map = {
        (
            str(row.get("ORIGEM") or "").strip().upper(),
            str(row.get("ORISTAMP") or "").strip(),
            normalize_language(row.get("IDIOMA")) or BASE_LANGUAGE,
        ): _trimmed_text(row.get("TRADUCAO"))
        for row in existing_rows
        if str(row.get("ORIGEM") or "").strip() and str(row.get("ORISTAMP") or "").strip()
    }

    insert_params: list[dict[str, str]] = []
    update_params: list[dict[str, str]] = []
    for row in source_rows:
        origin = row["ORIGEM"]
        stamp = row["ORISTAMP"]
        base_text = row["TEXTO"]
        for language in SUPPORTED_LANGUAGES:
            key = (origin, stamp, language)
            current_text = existing_map.get(key)
            if current_text is None:
                insert_params.append(
                    {
                        "ORIGEM": origin,
                        "ORISTAMP": stamp,
                        "IDIOMA": language,
                        "TRADUCAO": base_text,
                    }
                )
                continue
            if language == BASE_LANGUAGE and current_text != base_text:
                update_params.append(
                    {
                        "ORIGEM": origin,
                        "ORISTAMP": stamp,
                        "IDIOMA": language,
                        "TRADUCAO": base_text,
                    }
                )
                continue
            if language != BASE_LANGUAGE and not current_text:
                update_params.append(
                    {
                        "ORIGEM": origin,
                        "ORISTAMP": stamp,
                        "IDIOMA": language,
                        "TRADUCAO": base_text,
                    }
                )

    try:
        if insert_params:
            session.execute(
                text(
                    """
                    INSERT INTO dbo.I18N_TRADUCOES (ORIGEM, ORISTAMP, IDIOMA, TRADUCAO)
                    VALUES (:ORIGEM, :ORISTAMP, :IDIOMA, :TRADUCAO)
                    """
                ),
                insert_params,
            )
        if update_params:
            session.execute(
                text(
                    """
                    UPDATE dbo.I18N_TRADUCOES
                    SET TRADUCAO = :TRADUCAO
                    WHERE ORIGEM = :ORIGEM
                      AND ORISTAMP = :ORISTAMP
                      AND IDIOMA = :IDIOMA
                    """
                ),
                update_params,
            )
        session.commit()
    except Exception:
        session.rollback()
        raise

    reload_db_translations(session)
    return {
        "sources": len(source_rows),
        "inserted": len(insert_params),
        "updated": len(update_params),
    }


def translate_db_record(origin: str, oristamp: str, fallback_text: str = "", language: Any = None) -> str:
    fallback_value = str(fallback_text or "")
    if not i18n_enabled():
        return fallback_value

    origin_key = str(origin or "").strip().upper()
    stamp_key = str(oristamp or "").strip()
    if not origin_key or not stamp_key:
        return fallback_value

    language_key = normalize_language(language) or BASE_LANGUAGE
    translated = (
        _DB_TRANSLATIONS_CACHE.get(language_key, {})
        .get(origin_key, {})
        .get(stamp_key)
    )
    if translated:
        return translated

    base_translated = (
        _DB_TRANSLATIONS_CACHE.get(BASE_LANGUAGE, {})
        .get(origin_key, {})
        .get(stamp_key)
    )
    if base_translated:
        return base_translated

    return fallback_value


def bulk_translate_db_records(origin: str, items: list[tuple[str, str]], language: Any = None) -> dict[str, str]:
    return {
        str(stamp or "").strip(): translate_db_record(origin, stamp, fallback_text=fallback, language=language)
        for stamp, fallback in items
        if str(stamp or "").strip()
    }


def _translation_rows_query() -> str:
    return """
        SELECT
            X.ORIGEM,
            X.ORISTAMP,
            X.TEXTO_BASE,
            X.TRADUCAO,
            X.CONTEXTO,
            X.CONTEXTO_EXTRA
        FROM
        (
            SELECT
                'MENU' AS ORIGEM,
                LTRIM(RTRIM(ISNULL(M.MENUSTAMP, ''))) AS ORISTAMP,
                LTRIM(RTRIM(ISNULL(M.NOME, ''))) AS TEXTO_BASE,
                LTRIM(RTRIM(ISNULL(T.TRADUCAO, ''))) AS TRADUCAO,
                LTRIM(RTRIM(ISNULL(M.TABELA, ''))) AS CONTEXTO,
                LTRIM(RTRIM(ISNULL(M.URL, ''))) AS CONTEXTO_EXTRA,
                CAST(1 AS int) AS ORDEM_GRUPO,
                UPPER(LTRIM(RTRIM(ISNULL(M.TABELA, '')))) AS CONTEXTO_SORT,
                CAST(ISNULL(M.ORDEM, 0) AS int) AS ORDEM_NUM
            FROM dbo.MENU M
            LEFT JOIN dbo.I18N_TRADUCOES T
                ON T.ORIGEM = 'MENU'
               AND T.ORISTAMP = LTRIM(RTRIM(ISNULL(M.MENUSTAMP, '')))
               AND T.IDIOMA = :language
            WHERE LTRIM(RTRIM(ISNULL(M.MENUSTAMP, ''))) <> ''

            UNION ALL

            SELECT
                'CAMPOS' AS ORIGEM,
                LTRIM(RTRIM(ISNULL(C.CAMPOSSTAMP, ''))) AS ORISTAMP,
                LTRIM(RTRIM(ISNULL(C.DESCRICAO, ''))) AS TEXTO_BASE,
                LTRIM(RTRIM(ISNULL(T.TRADUCAO, ''))) AS TRADUCAO,
                LTRIM(RTRIM(ISNULL(C.TABELA, ''))) AS CONTEXTO,
                LTRIM(RTRIM(ISNULL(C.NMCAMPO, ''))) AS CONTEXTO_EXTRA,
                CAST(2 AS int) AS ORDEM_GRUPO,
                UPPER(LTRIM(RTRIM(ISNULL(C.TABELA, '')))) AS CONTEXTO_SORT,
                CAST(ISNULL(C.ORDEM, 0) AS int) AS ORDEM_NUM
            FROM dbo.CAMPOS C
            LEFT JOIN dbo.I18N_TRADUCOES T
                ON T.ORIGEM = 'CAMPOS'
               AND T.ORISTAMP = LTRIM(RTRIM(ISNULL(C.CAMPOSSTAMP, '')))
               AND T.IDIOMA = :language
            WHERE LTRIM(RTRIM(ISNULL(C.CAMPOSSTAMP, ''))) <> ''
        ) X
        WHERE (:origin = '' OR X.ORIGEM = :origin)
          AND (
                :search = ''
                OR UPPER(X.ORISTAMP) LIKE :search_like
                OR UPPER(X.TEXTO_BASE) LIKE :search_like
                OR UPPER(X.TRADUCAO) LIKE :search_like
                OR UPPER(X.CONTEXTO) LIKE :search_like
                OR UPPER(X.CONTEXTO_EXTRA) LIKE :search_like
          )
        ORDER BY
            X.ORDEM_GRUPO,
            X.CONTEXTO_SORT,
            X.ORDEM_NUM,
            UPPER(X.TEXTO_BASE),
            UPPER(X.CONTEXTO_EXTRA),
            UPPER(X.ORISTAMP)
    """


def get_db_translation_dataset(session, language: Any, origin: Any = "", search: Any = "") -> dict[str, Any]:
    language_key = normalize_language(language) or BASE_LANGUAGE
    origin_key = _normalize_origin(origin)
    search_text = str(search or "").strip()

    if not i18n_enabled():
        return {
            "language": language_key,
            "origin": origin_key,
            "search": search_text,
            "rows": [],
            "summary": {"total": 0, "base": 0, "pending": 0, "translated": 0},
        }

    ensure_db_translation_table(session)
    raw_rows = session.execute(
        text(_translation_rows_query()),
        {
            "language": language_key,
            "origin": origin_key,
            "search": search_text,
            "search_like": f"%{search_text.upper()}%",
        },
    ).mappings().all()

    rows: list[dict[str, Any]] = []
    summary = {"total": 0, "base": 0, "pending": 0, "translated": 0}

    for row in raw_rows:
        row_origin = _normalize_origin(row.get("ORIGEM"))
        row_stamp = str(row.get("ORISTAMP") or "").strip()
        if not row_origin or not row_stamp:
            continue

        source_text = _trimmed_text(row.get("TEXTO_BASE"))
        translation_text = _trimmed_text(row.get("TRADUCAO"))
        context = str(row.get("CONTEXTO") or "").strip()
        context_extra = str(row.get("CONTEXTO_EXTRA") or "").strip()
        context_display = " - ".join(part for part in (context, context_extra) if part)

        status = "base"
        if language_key != BASE_LANGUAGE:
            status = "translated" if translation_text and translation_text != source_text else "pending"

        rows.append(
            {
                "origin": row_origin,
                "oristamp": row_stamp,
                "language": language_key,
                "source_text": source_text,
                "translation": translation_text,
                "context": context,
                "context_extra": context_extra,
                "context_display": context_display,
                "status": status,
                "is_base_language": language_key == BASE_LANGUAGE,
            }
        )
        summary["total"] += 1
        summary[status] += 1

    return {
        "language": language_key,
        "origin": origin_key,
        "search": search_text,
        "rows": rows,
        "summary": summary,
    }


def save_db_translation_rows(session, language: Any, rows: Any) -> dict[str, Any]:
    if not i18n_enabled():
        raise DbI18nValidationError("Multiidioma inativo.")

    language_key = normalize_language(language)
    if not language_key:
        raise DbI18nValidationError("Idioma invalido.")
    if language_key == BASE_LANGUAGE:
        raise DbI18nValidationError("O idioma base pt-PT e gerido automaticamente.")

    sync_db_translations(session)

    payloads: list[dict[str, str]] = []
    for row in rows or []:
        origin_key = _normalize_origin((row or {}).get("origin") or (row or {}).get("ORIGEM"))
        stamp_key = str((row or {}).get("oristamp") or (row or {}).get("ORISTAMP") or "").strip()
        if not origin_key or not stamp_key:
            continue
        payloads.append(
            {
                "ORIGEM": origin_key,
                "ORISTAMP": stamp_key,
                "IDIOMA": language_key,
                "TRADUCAO": _trimmed_text((row or {}).get("translation") or (row or {}).get("TRADUCAO")),
            }
        )

    if not payloads:
        return {"language": language_key, "updated": 0}

    try:
        session.execute(
            text(
                """
                UPDATE dbo.I18N_TRADUCOES
                SET TRADUCAO = :TRADUCAO
                WHERE ORIGEM = :ORIGEM
                  AND ORISTAMP = :ORISTAMP
                  AND IDIOMA = :IDIOMA
                """
            ),
            payloads,
        )
        session.execute(
            text(
                """
                INSERT INTO dbo.I18N_TRADUCOES (ORIGEM, ORISTAMP, IDIOMA, TRADUCAO)
                SELECT :ORIGEM, :ORISTAMP, :IDIOMA, :TRADUCAO
                WHERE NOT EXISTS
                (
                    SELECT 1
                    FROM dbo.I18N_TRADUCOES
                    WHERE ORIGEM = :ORIGEM
                      AND ORISTAMP = :ORISTAMP
                      AND IDIOMA = :IDIOMA
                )
                """
            ),
            payloads,
        )
        session.commit()
    except Exception:
        session.rollback()
        raise

    reload_db_translations(session)
    return {"language": language_key, "updated": len(payloads)}


def _chunk_rows(rows: list[dict[str, Any]], size: int = DB_TRANSLATION_BATCH_SIZE) -> list[list[dict[str, Any]]]:
    return [rows[index:index + size] for index in range(0, len(rows), size)]


def _translate_batch_with_openai(session, language: str, rows: list[dict[str, Any]]) -> dict[str, str]:
    api_key = _translation_api_key(session)
    if not api_key:
        raise DbI18nValidationError(
            "Traducao automatica indisponivel. Configura SHOP_TRANSLATE_OPENAI_API_KEY na tabela PARA."
        )

    model = _translation_model(session)
    prompt = {
        "task": "translate_stationzero_db_labels",
        "source_language": "pt-PT",
        "target_language": language,
        "target_language_label": _language_display_name(language),
        "rules": [
            "Translate short UI labels used in business software.",
            "Keep the text concise and natural.",
            "Preserve placeholders such as {count}, {name} and punctuation.",
            "Preserve acronyms, codes, table names and field names when they appear as technical identifiers.",
            "Do not add explanations or extra fields.",
            "Return JSON only.",
        ],
        "items": [
            {
                "id": str(row.get("id") or "").strip(),
                "origin": str(row.get("origin") or "").strip(),
                "context": str(row.get("context") or "").strip(),
                "context_extra": str(row.get("context_extra") or "").strip(),
                "source_text": str(row.get("source_text") or "").strip(),
            }
            for row in rows
            if str(row.get("id") or "").strip()
        ],
    }
    request_body = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "You translate short interface labels from Portuguese into the requested language. "
                            "Return valid JSON only."
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": json.dumps(prompt, ensure_ascii=False),
                    }
                ],
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "db_i18n_translations",
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "translations": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "id": {"type": "string"},
                                    "text": {"type": "string"},
                                },
                                "required": ["id", "text"],
                            },
                        }
                    },
                    "required": ["translations"],
                },
            }
        },
    }

    req = urllib_request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=60) as response:
            payload_response = json.loads(response.read().decode("utf-8"))
    except urllib_error.HTTPError as exc:
        details = ""
        try:
            details = exc.read().decode("utf-8")
        except Exception:
            details = str(exc)
        raise DbI18nServiceError(f"Falha na traducao automatica: {details[:280]}") from exc
    except Exception as exc:
        raise DbI18nServiceError(f"Falha na traducao automatica: {exc}") from exc

    raw_text = _strip_json_fence(_extract_openai_text(payload_response))
    if not raw_text:
        raise DbI18nServiceError("A API de traducao nao devolveu conteudo utilizavel.")

    try:
        parsed = json.loads(raw_text)
    except Exception as exc:
        raise DbI18nServiceError("A resposta da traducao automatica nao veio em JSON valido.") from exc

    translations: dict[str, str] = {}
    for item in parsed.get("translations") or []:
        item_id = str((item or {}).get("id") or "").strip()
        if not item_id:
            continue
        translations[item_id] = _trimmed_text((item or {}).get("text"))
    return translations


def auto_translate_db_rows(session, language: Any, origin: Any = "", overwrite: Any = False) -> dict[str, Any]:
    if not i18n_enabled():
        raise DbI18nValidationError("Multiidioma inativo.")

    language_key = normalize_language(language)
    if not language_key:
        raise DbI18nValidationError("Idioma invalido.")
    if language_key == BASE_LANGUAGE:
        raise DbI18nValidationError("O idioma base pt-PT e gerido automaticamente.")

    sync_db_translations(session)
    dataset = get_db_translation_dataset(session, language_key, origin=origin, search="")
    rows = dataset.get("rows") or []
    overwrite_existing = _coerce_bool(overwrite)

    candidates: list[dict[str, Any]] = []
    skipped_existing = 0
    for row in rows:
        source_text = str(row.get("source_text") or "").strip()
        current_text = str(row.get("translation") or "").strip()
        if not source_text:
            continue
        if not overwrite_existing and current_text and current_text != source_text:
            skipped_existing += 1
            continue
        candidates.append(
            {
                "id": f"{row.get('origin')}::{row.get('oristamp')}",
                "origin": str(row.get("origin") or "").strip(),
                "oristamp": str(row.get("oristamp") or "").strip(),
                "context": str(row.get("context") or "").strip(),
                "context_extra": str(row.get("context_extra") or "").strip(),
                "source_text": source_text,
            }
        )

    if not candidates:
        return {
            "language": language_key,
            "updated": 0,
            "processed": 0,
            "skipped_existing": skipped_existing,
            "model": "",
            "overwrite": overwrite_existing,
        }

    translated_map: dict[str, str] = {}
    for batch in _chunk_rows(candidates):
        translated_map.update(_translate_batch_with_openai(session, language_key, batch))

    update_params: list[dict[str, str]] = []
    for item in candidates:
        translated_text = _trimmed_text(translated_map.get(item["id"]) or item["source_text"])
        update_params.append(
            {
                "ORIGEM": item["origin"],
                "ORISTAMP": item["oristamp"],
                "IDIOMA": language_key,
                "TRADUCAO": translated_text,
            }
        )

    try:
        session.execute(
            text(
                """
                UPDATE dbo.I18N_TRADUCOES
                SET TRADUCAO = :TRADUCAO
                WHERE ORIGEM = :ORIGEM
                  AND ORISTAMP = :ORISTAMP
                  AND IDIOMA = :IDIOMA
                """
            ),
            update_params,
        )
        session.commit()
    except Exception:
        session.rollback()
        raise

    reload_db_translations(session)
    return {
        "language": language_key,
        "updated": len(update_params),
        "processed": len(candidates),
        "skipped_existing": skipped_existing,
        "model": _translation_model(session),
        "overwrite": overwrite_existing,
    }
