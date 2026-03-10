import json
import os
import uuid
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib import error as urllib_error
from urllib import request as urllib_request

from flask import current_app
from sqlalchemy import text
from werkzeug.utils import secure_filename

from models import db


_DEC2 = Decimal("0.01")
_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
_IMAGE_FOLDER = os.path.join("static", "images", "shop")
_TRANSLATABLE_FIELDS = (
    ("NOME", 150),
    ("TITULO", 200),
    ("SUBTITULO", 200),
    ("DESCRICAO_CURTA", 500),
    ("DESCRICAO", None),
)
_TRANSLATION_LANGS = ("EN", "ES", "FR")
_TRANSLATION_COLUMNS = tuple(
    (f"{field}_{lang}", max_len)
    for field, max_len in _TRANSLATABLE_FIELDS
    for lang in _TRANSLATION_LANGS
)


class ShopServiceError(Exception):
    pass


class ShopValidationError(ShopServiceError):
    pass


class ShopNotFoundError(ShopServiceError):
    pass


def _table_exists(table_name):
    sql = text(
        """
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = 'dbo'
          AND TABLE_NAME = :table_name
        """
    )
    return bool(db.session.execute(sql, {"table_name": table_name}).scalar() or 0)


def _require_tables(*table_names):
    missing = [name for name in table_names if not _table_exists(name)]
    if missing:
        raise ShopServiceError(
            "Estrutura SHOP indisponivel. Tabelas em falta: " + ", ".join(missing)
        )


def _text_value(value, max_len=None):
    raw = "" if value is None else str(value).strip()
    if max_len:
        raw = raw[:max_len]
    return raw


def _nullable_text(value, max_len=None):
    raw = _text_value(value, max_len=max_len)
    return raw or None


def _bool_value(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _int_value(value, default=0, minimum=None):
    try:
        number = int(value)
    except Exception:
        number = default
    if minimum is not None and number < minimum:
        number = minimum
    return number


def _decimal_value(value, default="0.00", minimum=None):
    try:
        number = Decimal(str(value if value not in (None, "") else default))
    except (InvalidOperation, ValueError, TypeError):
        number = Decimal(str(default))
    if minimum is not None and number < minimum:
        number = minimum
    return number.quantize(_DEC2, rounding=ROUND_HALF_UP)


def _money_float(value):
    return float(_decimal_value(value))


def _normalize_code(value, prefix):
    raw = _text_value(value, 50).upper()
    return raw or f"{prefix}_{uuid.uuid4().hex[:10].upper()}"


def _format_dt(value):
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _translation_select_sql(alias="p"):
    return ",\n                ".join(f"{alias}.{column}" for column, _ in _TRANSLATION_COLUMNS)


def _translation_insert_sql():
    return ", ".join(column for column, _ in _TRANSLATION_COLUMNS)


def _translation_values_sql():
    return ", ".join(f":{column}" for column, _ in _TRANSLATION_COLUMNS)


def _translation_update_sql():
    return ",\n                    ".join(f"{column} = :{column}" for column, _ in _TRANSLATION_COLUMNS)


def _translation_payload(payload):
    params = {}
    for column, max_len in _TRANSLATION_COLUMNS:
        params[column] = _nullable_text(payload.get(column), max_len=max_len)
    return params


def _product_translation_map(row):
    return {
        "pt": {
            "name": _text_value(row.get("NOME"), 150),
            "title": _text_value(row.get("TITULO"), 200),
            "subtitle": _nullable_text(row.get("SUBTITULO"), 200) or "",
            "description_short": _nullable_text(row.get("DESCRICAO_CURTA"), 500) or "",
            "description": _nullable_text(row.get("DESCRICAO")) or "",
        },
        "en": {
            "name": _nullable_text(row.get("NOME_EN"), 150) or "",
            "title": _nullable_text(row.get("TITULO_EN"), 200) or "",
            "subtitle": _nullable_text(row.get("SUBTITULO_EN"), 200) or "",
            "description_short": _nullable_text(row.get("DESCRICAO_CURTA_EN"), 500) or "",
            "description": _nullable_text(row.get("DESCRICAO_EN")) or "",
        },
        "es": {
            "name": _nullable_text(row.get("NOME_ES"), 150) or "",
            "title": _nullable_text(row.get("TITULO_ES"), 200) or "",
            "subtitle": _nullable_text(row.get("SUBTITULO_ES"), 200) or "",
            "description_short": _nullable_text(row.get("DESCRICAO_CURTA_ES"), 500) or "",
            "description": _nullable_text(row.get("DESCRICAO_ES")) or "",
        },
        "fr": {
            "name": _nullable_text(row.get("NOME_FR"), 150) or "",
            "title": _nullable_text(row.get("TITULO_FR"), 200) or "",
            "subtitle": _nullable_text(row.get("SUBTITULO_FR"), 200) or "",
            "description_short": _nullable_text(row.get("DESCRICAO_CURTA_FR"), 500) or "",
            "description": _nullable_text(row.get("DESCRICAO_FR")) or "",
        },
    }


def _param_value_from_row(row):
    tipo = _text_value((row or {}).get("TIPO"), 1).upper()
    if tipo == "N":
        try:
            return str((row or {}).get("NVALOR") or "")
        except Exception:
            return ""
    if tipo == "D":
        value = (row or {}).get("DVALOR")
        try:
            return value.strftime("%Y-%m-%d")
        except Exception:
            return str(value or "")
    if tipo == "L":
        return "1" if int((row or {}).get("LVALOR") or 0) == 1 else "0"
    return str((row or {}).get("CVALOR") or "")


def _get_para_value(code, default=None):
    key = _text_value(code, 100)
    if not key or not _table_exists("PARA"):
        return default
    row = db.session.execute(
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


def _translation_api_key():
    return (
        _get_para_value("SHOP_TRANSLATE_OPENAI_API_KEY")
        or _get_para_value("OPENAI_API_KEY")
        or os.getenv("SHOP_TRANSLATE_OPENAI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or ""
    ).strip()


def _translation_model():
    return (
        _get_para_value("SHOP_TRANSLATE_MODEL")
        or _get_para_value("OPENAI_TRANSLATE_MODEL")
        or os.getenv("SHOP_TRANSLATE_MODEL")
        or os.getenv("OPENAI_TRANSLATE_MODEL")
        or "gpt-4o-mini"
    ).strip()


def _extract_openai_text(payload):
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


def _strip_json_fence(raw_text):
    text_value = str(raw_text or "").strip()
    if text_value.startswith("```"):
        lines = text_value.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return text_value


def _payload_summary(raw_payload):
    text_payload = _text_value(raw_payload)
    if not text_payload:
        return ""
    try:
        payload = json.loads(text_payload)
    except Exception:
        return text_payload[:280] + ("..." if len(text_payload) > 280 else "")

    if isinstance(payload, dict):
        parts = []
        for key in ("id", "type", "object", "status", "message", "code"):
            value = payload.get(key)
            if value not in (None, ""):
                parts.append(f"{key}: {value}")
        data_obj = payload.get("data")
        if isinstance(data_obj, dict) and isinstance(data_obj.get("object"), dict):
            inner = data_obj["object"]
            for key in ("id", "object", "status"):
                value = inner.get(key)
                if value not in (None, ""):
                    parts.append(f"data.{key}: {value}")
        if parts:
            summary = " | ".join(parts)
            return summary[:280] + ("..." if len(summary) > 280 else "")

    pretty = json.dumps(payload, ensure_ascii=False)
    return pretty[:280] + ("..." if len(pretty) > 280 else "")


def _stock_expr():
    return """
        COALESCE((
            SELECT SUM(
                CASE
                    WHEN sm.TIPO_MOVIMENTO IN ('ENTRADA', 'AJUSTE_ENTRADA') THEN sm.QUANTIDADE
                    WHEN sm.TIPO_MOVIMENTO IN ('SAIDA', 'AJUSTE_SAIDA') THEN -sm.QUANTIDADE
                    ELSE 0
                END
            )
            FROM dbo.SHOP_STOCK_MOVIMENTOS sm
            WHERE sm.PRODUTO_ID = p.PRODUTO_ID
        ), 0)
    """


def get_shop_meta():
    families = []
    states = []
    if _table_exists("SHOP_FAMILIAS"):
        families = db.session.execute(
            text(
                """
                SELECT FAMILIA_ID, CODIGO, NOME, TITULO, ORDEM, ATIVO
                FROM dbo.SHOP_FAMILIAS
                ORDER BY ORDEM, NOME
                """
            )
        ).mappings().all()
    if _table_exists("SHOP_ENCOMENDA_ESTADOS"):
        states = db.session.execute(
            text(
                """
                SELECT ENCOMENDA_ESTADO_ID, CODIGO, NOME, ORDEM, ATIVO
                FROM dbo.SHOP_ENCOMENDA_ESTADOS
                ORDER BY ORDEM, NOME
                """
            )
        ).mappings().all()
    return {
        "families": [dict(row) for row in families],
        "order_states": [dict(row) for row in states],
        "payment_states": [
            {"code": "PENDENTE", "name": "Pendente"},
            {"code": "AUTORIZADO", "name": "Autorizado"},
            {"code": "PAGO", "name": "Pago"},
            {"code": "FALHADO", "name": "Falhado"},
            {"code": "CANCELADO", "name": "Cancelado"},
            {"code": "PARCIALMENTE_REEMBOLSADO", "name": "Parcialmente reembolsado"},
            {"code": "REEMBOLSADO", "name": "Reembolsado"},
        ],
        "variant_types": [
            {"code": "TAMANHO", "name": "Tamanho"},
            {"code": "CAPACIDADE", "name": "Capacidade"},
            {"code": "FORMATO", "name": "Formato"},
            {"code": "UNIDADE", "name": "Unidade"},
            {"code": "OUTRO", "name": "Outro"},
        ],
    }


def list_families():
    _require_tables("SHOP_FAMILIAS")
    rows = db.session.execute(
        text(
            """
            SELECT
                FAMILIA_ID, CODIGO, NOME, TITULO, DESCRICAO,
                ORDEM, ATIVO, CRIADO_EM, ALTERADO_EM
            FROM dbo.SHOP_FAMILIAS
            ORDER BY ORDEM, NOME
            """
        )
    ).mappings().all()
    items = []
    for row in rows:
        item = dict(row)
        item["CRIADO_EM"] = _format_dt(item.get("CRIADO_EM"))
        item["ALTERADO_EM"] = _format_dt(item.get("ALTERADO_EM"))
        items.append(item)
    return items


def get_family_detail(family_id):
    _require_tables("SHOP_FAMILIAS")
    row = db.session.execute(
        text(
            """
            SELECT
                FAMILIA_ID, CODIGO, NOME, TITULO, DESCRICAO,
                ORDEM, ATIVO, CRIADO_EM, ALTERADO_EM
            FROM dbo.SHOP_FAMILIAS
            WHERE FAMILIA_ID = :family_id
            """
        ),
        {"family_id": int(family_id)},
    ).mappings().first()
    if not row:
        raise ShopNotFoundError("Familia nao encontrada.")
    item = dict(row)
    item["CRIADO_EM"] = _format_dt(item.get("CRIADO_EM"))
    item["ALTERADO_EM"] = _format_dt(item.get("ALTERADO_EM"))
    return item


def save_family(payload, family_id=None):
    _require_tables("SHOP_FAMILIAS")
    nome = _text_value(payload.get("NOME"), 100)
    if not nome:
        raise ShopValidationError("O nome da familia e obrigatorio.")
    params = {
        "CODIGO": _normalize_code(payload.get("CODIGO"), "FAM"),
        "NOME": nome,
        "TITULO": _nullable_text(payload.get("TITULO"), 150) or nome,
        "DESCRICAO": _nullable_text(payload.get("DESCRICAO"), 500),
        "ORDEM": _int_value(payload.get("ORDEM"), default=0, minimum=0),
        "ATIVO": 1 if _bool_value(payload.get("ATIVO", True)) else 0,
    }
    if family_id is None:
        row = db.session.execute(
            text(
                """
                INSERT INTO dbo.SHOP_FAMILIAS
                    (CODIGO, NOME, TITULO, DESCRICAO, ORDEM, ATIVO, CRIADO_EM, ALTERADO_EM)
                OUTPUT INSERTED.FAMILIA_ID
                VALUES
                    (:CODIGO, :NOME, :TITULO, :DESCRICAO, :ORDEM, :ATIVO, SYSUTCDATETIME(), SYSUTCDATETIME())
                """
            ),
            params,
        ).mappings().first()
        db.session.commit()
        return get_family_detail(row["FAMILIA_ID"])

    params["FAMILIA_ID"] = int(family_id)
    result = db.session.execute(
        text(
            """
            UPDATE dbo.SHOP_FAMILIAS
            SET
                CODIGO = :CODIGO,
                NOME = :NOME,
                TITULO = :TITULO,
                DESCRICAO = :DESCRICAO,
                ORDEM = :ORDEM,
                ATIVO = :ATIVO,
                ALTERADO_EM = SYSUTCDATETIME()
            WHERE FAMILIA_ID = :FAMILIA_ID
            """
        ),
        params,
    )
    if not result.rowcount:
        db.session.rollback()
        raise ShopNotFoundError("Familia nao encontrada.")
    db.session.commit()
    return get_family_detail(family_id)


def list_products(filters=None):
    _require_tables(
        "SHOP_PRODUTOS",
        "SHOP_FAMILIAS",
        "SHOP_PRODUTO_IMAGENS",
        "SHOP_PRODUTO_VARIANTES",
        "SHOP_STOCK_MOVIMENTOS",
    )
    filters = filters or {}
    q_value = _text_value(filters.get("q"), 120)
    active_raw = _text_value(filters.get("active"), 8).lower()
    sort_map = {
        "nome": "p.NOME ASC, p.PRODUTO_ID DESC",
        "familia": "f.NOME ASC, p.ORDEM ASC, p.NOME ASC",
        "preco": "p.PRECO DESC, p.NOME ASC",
        "ordem": "p.ORDEM ASC, p.NOME ASC",
        "criado": "p.CRIADO_EM DESC, p.PRODUTO_ID DESC",
        "alterado": "p.ALTERADO_EM DESC, p.PRODUTO_ID DESC",
    }
    params = {
        "q": f"%{q_value}%",
        "has_q": 1 if q_value else 0,
        "family_id": _int_value(filters.get("family_id"), default=0, minimum=0),
        "active_all": 1 if active_raw not in {"0", "1"} else 0,
        "active_value": 1 if active_raw == "1" else 0,
    }
    order_clause = sort_map.get(_text_value(filters.get("sort"), 20).lower(), sort_map["alterado"])
    rows = db.session.execute(
        text(
            f"""
            SELECT
                p.PRODUTO_ID,
                p.CODIGO,
                p.NOME,
                p.TITULO,
                p.SUBTITULO,
                p.DESCRICAO_CURTA,
                p.NOME_EN,
                p.NOME_ES,
                p.NOME_FR,
                p.PRECO,
                p.MOEDA,
                p.ORDEM,
                p.ATIVO,
                p.CRIADO_EM,
                p.ALTERADO_EM,
                p.FAMILIA_ID,
                f.NOME AS FAMILIA_NOME,
                f.CODIGO AS FAMILIA_CODIGO,
                {_stock_expr()} AS STOCK_ATUAL,
                (
                    SELECT TOP 1 pi.URL
                    FROM dbo.SHOP_PRODUTO_IMAGENS pi
                    WHERE pi.PRODUTO_ID = p.PRODUTO_ID
                      AND pi.ATIVO = 1
                    ORDER BY pi.E_PRINCIPAL DESC, pi.ORDEM ASC, pi.PRODUTO_IMAGEM_ID ASC
                ) AS IMAGEM_URL,
                (
                    SELECT COUNT(*)
                    FROM dbo.SHOP_PRODUTO_VARIANTES pv
                    WHERE pv.PRODUTO_ID = p.PRODUTO_ID
                ) AS VARIANTES_COUNT
            FROM dbo.SHOP_PRODUTOS p
            INNER JOIN dbo.SHOP_FAMILIAS f
                ON f.FAMILIA_ID = p.FAMILIA_ID
            WHERE
                (:has_q = 0 OR (
                    p.CODIGO LIKE :q
                    OR p.NOME LIKE :q
                    OR ISNULL(p.SUBTITULO, '') LIKE :q
                    OR ISNULL(p.DESCRICAO_CURTA, '') LIKE :q
                    OR f.NOME LIKE :q
                ))
                AND (:family_id = 0 OR p.FAMILIA_ID = :family_id)
                AND (:active_all = 1 OR p.ATIVO = :active_value)
            ORDER BY {order_clause}
            """
        ),
        params,
    ).mappings().all()
    items = []
    for row in rows:
        item = dict(row)
        item["PRECO"] = _money_float(item.get("PRECO"))
        item["STOCK_ATUAL"] = float(item.get("STOCK_ATUAL") or 0)
        item["CRIADO_EM"] = _format_dt(item.get("CRIADO_EM"))
        item["ALTERADO_EM"] = _format_dt(item.get("ALTERADO_EM"))
        items.append(item)
    return {
        "items": items,
        "count": len(items),
        "summary": {
            "active_count": sum(1 for item in items if item.get("ATIVO")),
            "inactive_count": sum(1 for item in items if not item.get("ATIVO")),
            "families_count": len({item.get("FAMILIA_ID") for item in items}),
        },
    }


def _product_variants(product_id):
    rows = db.session.execute(
        text(
            """
            SELECT
                PRODUTO_VARIANTE_ID, PRODUTO_ID, CODIGO, TIPO_VARIANTE,
                NOME, VALOR, DESCRICAO_CURTA, PRECO, ORDEM,
                PADRAO, ATIVO, CRIADO_EM, ALTERADO_EM
            FROM dbo.SHOP_PRODUTO_VARIANTES
            WHERE PRODUTO_ID = :product_id
            ORDER BY ORDEM ASC, PRODUTO_VARIANTE_ID ASC
            """
        ),
        {"product_id": int(product_id)},
    ).mappings().all()
    items = []
    for row in rows:
        item = dict(row)
        item["PRECO"] = None if item.get("PRECO") is None else _money_float(item.get("PRECO"))
        item["CRIADO_EM"] = _format_dt(item.get("CRIADO_EM"))
        item["ALTERADO_EM"] = _format_dt(item.get("ALTERADO_EM"))
        items.append(item)
    return items


def _product_images(product_id):
    rows = db.session.execute(
        text(
            """
            SELECT
                PRODUTO_IMAGEM_ID, PRODUTO_ID, URL, ALT_TEXT, ORDEM,
                E_PRINCIPAL, ATIVO, CRIADO_EM, ALTERADO_EM
            FROM dbo.SHOP_PRODUTO_IMAGENS
            WHERE PRODUTO_ID = :product_id
            ORDER BY E_PRINCIPAL DESC, ORDEM ASC, PRODUTO_IMAGEM_ID ASC
            """
        ),
        {"product_id": int(product_id)},
    ).mappings().all()
    items = []
    for row in rows:
        item = dict(row)
        item["CRIADO_EM"] = _format_dt(item.get("CRIADO_EM"))
        item["ALTERADO_EM"] = _format_dt(item.get("ALTERADO_EM"))
        items.append(item)
    return items


def get_product_detail(product_id):
    _require_tables("SHOP_PRODUTOS", "SHOP_FAMILIAS", "SHOP_PRODUTO_IMAGENS", "SHOP_PRODUTO_VARIANTES")
    row = db.session.execute(
        text(
            f"""
            SELECT
                p.PRODUTO_ID, p.FAMILIA_ID, p.CODIGO, p.NOME, p.TITULO,
                p.SUBTITULO, p.DESCRICAO_CURTA, p.DESCRICAO,
                {_translation_select_sql('p')},
                p.PRECO,
                p.MOEDA, p.ORDEM, p.ATIVO, p.CRIADO_EM, p.ALTERADO_EM,
                f.NOME AS FAMILIA_NOME, f.CODIGO AS FAMILIA_CODIGO,
                {_stock_expr()} AS STOCK_ATUAL
            FROM dbo.SHOP_PRODUTOS p
            INNER JOIN dbo.SHOP_FAMILIAS f
                ON f.FAMILIA_ID = p.FAMILIA_ID
            WHERE p.PRODUTO_ID = :product_id
            """
        ),
        {"product_id": int(product_id)},
    ).mappings().first()
    if not row:
        raise ShopNotFoundError("Artigo nao encontrado.")
    product = dict(row)
    product["PRECO"] = _money_float(product.get("PRECO"))
    product["STOCK_ATUAL"] = float(product.get("STOCK_ATUAL") or 0)
    product["CRIADO_EM"] = _format_dt(product.get("CRIADO_EM"))
    product["ALTERADO_EM"] = _format_dt(product.get("ALTERADO_EM"))
    product["TRADUCOES"] = _product_translation_map(product)
    return {
        "product": product,
        "variants": _product_variants(product_id),
        "images": _product_images(product_id),
    }


def auto_translate_product(payload):
    source = {
        "NOME": _text_value(payload.get("NOME"), 150),
        "TITULO": _nullable_text(payload.get("TITULO"), 200) or "",
        "SUBTITULO": _nullable_text(payload.get("SUBTITULO"), 200) or "",
        "DESCRICAO_CURTA": _nullable_text(payload.get("DESCRICAO_CURTA"), 500) or "",
        "DESCRICAO": _nullable_text(payload.get("DESCRICAO")) or "",
    }
    if not source["NOME"]:
        raise ShopValidationError("Preenche pelo menos o nome em PT antes de traduzir.")

    api_key = _translation_api_key()
    if not api_key:
        raise ShopValidationError("Traducao automatica indisponivel. Configura OPENAI_API_KEY ou SHOP_TRANSLATE_OPENAI_API_KEY.")

    prompt = {
        "task": "translate_shop_product_fields",
        "source_language": "pt",
        "target_languages": ["en", "es", "fr"],
        "rules": [
            "Translate product copy for an online guest shop.",
            "Keep the tone short, commercial and natural.",
            "Return JSON only.",
            "Preserve empty strings when the Portuguese source field is empty.",
            "Do not invent extra facts.",
        ],
        "source_fields": source,
        "expected_json_keys": [column for column, _ in _TRANSLATION_COLUMNS],
    }
    request_body = {
        "model": _translation_model(),
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": "You translate ecommerce product fields from Portuguese into English, Spanish and French. Return valid JSON only."
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
                "name": "shop_product_translations",
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        column: {"type": "string"} for column, _ in _TRANSLATION_COLUMNS
                    },
                    "required": [column for column, _ in _TRANSLATION_COLUMNS],
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
        with urllib_request.urlopen(req, timeout=35) as response:
            payload_response = json.loads(response.read().decode("utf-8"))
    except urllib_error.HTTPError as exc:
        details = ""
        try:
            details = exc.read().decode("utf-8")
        except Exception:
            details = str(exc)
        raise ShopServiceError(f"Falha na traducao automatica: {details[:280]}") from exc
    except Exception as exc:
        raise ShopServiceError(f"Falha na traducao automatica: {exc}") from exc

    raw_text = _strip_json_fence(_extract_openai_text(payload_response))
    if not raw_text:
        raise ShopServiceError("A API de traducao nao devolveu conteudo utilizavel.")

    try:
        parsed = json.loads(raw_text)
    except Exception as exc:
        raise ShopServiceError("A resposta da traducao automatica nao veio em JSON valido.") from exc

    normalized = {}
    for column, max_len in _TRANSLATION_COLUMNS:
        normalized[column] = _nullable_text(parsed.get(column), max_len=max_len) or ""
    return normalized


def _replace_variants(product_id, variants):
    db.session.execute(
        text("DELETE FROM dbo.SHOP_PRODUTO_VARIANTES WHERE PRODUTO_ID = :product_id"),
        {"product_id": int(product_id)},
    )
    default_used = False
    for raw in variants:
        name = _text_value(raw.get("NOME"), 100)
        value = _text_value(raw.get("VALOR"), 100)
        if not name or not value:
            continue
        is_default = bool(raw.get("PADRAO")) and not default_used
        if is_default:
            default_used = True
        db.session.execute(
            text(
                """
                INSERT INTO dbo.SHOP_PRODUTO_VARIANTES
                    (PRODUTO_ID, CODIGO, TIPO_VARIANTE, NOME, VALOR, DESCRICAO_CURTA, PRECO, ORDEM, PADRAO, ATIVO, CRIADO_EM, ALTERADO_EM)
                VALUES
                    (:PRODUTO_ID, :CODIGO, :TIPO_VARIANTE, :NOME, :VALOR, :DESCRICAO_CURTA, :PRECO, :ORDEM, :PADRAO, :ATIVO, SYSUTCDATETIME(), SYSUTCDATETIME())
                """
            ),
            {
                "PRODUTO_ID": int(product_id),
                "CODIGO": _nullable_text(raw.get("CODIGO"), 50),
                "TIPO_VARIANTE": _text_value(raw.get("TIPO_VARIANTE"), 30).upper() or "OUTRO",
                "NOME": name,
                "VALOR": value,
                "DESCRICAO_CURTA": _nullable_text(raw.get("DESCRICAO_CURTA"), 300),
                "PRECO": _decimal_value(raw.get("PRECO"), default="0.00", minimum=Decimal("0.00"))
                if raw.get("PRECO") not in (None, "")
                else None,
                "ORDEM": _int_value(raw.get("ORDEM"), default=0, minimum=0),
                "PADRAO": 1 if is_default else 0,
                "ATIVO": 1 if _bool_value(raw.get("ATIVO", True)) else 0,
            },
        )


def save_product(payload, product_id=None):
    _require_tables("SHOP_PRODUTOS", "SHOP_FAMILIAS", "SHOP_PRODUTO_VARIANTES")
    family_id = _int_value(payload.get("FAMILIA_ID"), default=0, minimum=0)
    if family_id <= 0:
        raise ShopValidationError("Seleciona uma familia.")
    nome = _text_value(payload.get("NOME"), 150)
    if not nome:
        raise ShopValidationError("O nome do artigo e obrigatorio.")
    params = {
        "FAMILIA_ID": family_id,
        "CODIGO": _normalize_code(payload.get("CODIGO"), "PRD"),
        "NOME": nome,
        "TITULO": _nullable_text(payload.get("TITULO"), 200) or nome,
        "SUBTITULO": _nullable_text(payload.get("SUBTITULO"), 200),
        "DESCRICAO_CURTA": _nullable_text(payload.get("DESCRICAO_CURTA"), 500),
        "DESCRICAO": _nullable_text(payload.get("DESCRICAO")),
        "PRECO": _decimal_value(payload.get("PRECO"), default="0.00", minimum=Decimal("0.00")),
        "MOEDA": _text_value(payload.get("MOEDA") or "EUR", 3).upper() or "EUR",
        "ORDEM": _int_value(payload.get("ORDEM"), default=0, minimum=0),
        "ATIVO": 1 if _bool_value(payload.get("ATIVO", True)) else 0,
    }
    params.update(_translation_payload(payload))
    if product_id is None:
        row = db.session.execute(
            text(
                """
                INSERT INTO dbo.SHOP_PRODUTOS
                    (FAMILIA_ID, CODIGO, NOME, TITULO, SUBTITULO, DESCRICAO_CURTA, DESCRICAO, """ + _translation_insert_sql() + """, PRECO, MOEDA, ORDEM, ATIVO, CRIADO_EM, ALTERADO_EM)
                OUTPUT INSERTED.PRODUTO_ID
                VALUES
                    (:FAMILIA_ID, :CODIGO, :NOME, :TITULO, :SUBTITULO, :DESCRICAO_CURTA, :DESCRICAO, """ + _translation_values_sql() + """, :PRECO, :MOEDA, :ORDEM, :ATIVO, SYSUTCDATETIME(), SYSUTCDATETIME())
                """
            ),
            params,
        ).mappings().first()
        product_id = int(row["PRODUTO_ID"])
    else:
        params["PRODUTO_ID"] = int(product_id)
        result = db.session.execute(
            text(
                """
                UPDATE dbo.SHOP_PRODUTOS
                SET
                    FAMILIA_ID = :FAMILIA_ID,
                    CODIGO = :CODIGO,
                    NOME = :NOME,
                    TITULO = :TITULO,
                    SUBTITULO = :SUBTITULO,
                    DESCRICAO_CURTA = :DESCRICAO_CURTA,
                    DESCRICAO = :DESCRICAO,
                    """ + _translation_update_sql() + """,
                    PRECO = :PRECO,
                    MOEDA = :MOEDA,
                    ORDEM = :ORDEM,
                    ATIVO = :ATIVO,
                    ALTERADO_EM = SYSUTCDATETIME()
                WHERE PRODUTO_ID = :PRODUTO_ID
                """
            ),
            params,
        )
        if not result.rowcount:
            db.session.rollback()
            raise ShopNotFoundError("Artigo nao encontrado.")
    _replace_variants(product_id, payload.get("VARIANTES") or payload.get("variants") or [])
    db.session.commit()
    return get_product_detail(product_id)


def upload_product_image(product_id, file_storage, alt_text=None):
    _require_tables("SHOP_PRODUTOS", "SHOP_PRODUTO_IMAGENS")
    if not file_storage or not getattr(file_storage, "filename", ""):
        raise ShopValidationError("Seleciona uma imagem para carregar.")
    filename = secure_filename(file_storage.filename or "")
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in _IMAGE_EXTENSIONS:
        raise ShopValidationError(f"Extensao .{extension} nao suportada.")
    product_exists = db.session.execute(
        text("SELECT TOP 1 1 FROM dbo.SHOP_PRODUTOS WHERE PRODUTO_ID = :product_id"),
        {"product_id": int(product_id)},
    ).first()
    if not product_exists:
        raise ShopNotFoundError("Artigo nao encontrado.")

    image_name = f"{uuid.uuid4().hex[:25]}.{extension}"
    target_dir = os.path.join(current_app.root_path, _IMAGE_FOLDER)
    os.makedirs(target_dir, exist_ok=True)
    file_storage.save(os.path.join(target_dir, image_name))
    public_path = f"/{_IMAGE_FOLDER.replace(os.sep, '/')}/{image_name}"

    next_order = db.session.execute(
        text(
            """
            SELECT COALESCE(MAX(ORDEM), 0) + 10
            FROM dbo.SHOP_PRODUTO_IMAGENS
            WHERE PRODUTO_ID = :product_id
            """
        ),
        {"product_id": int(product_id)},
    ).scalar() or 10
    has_images = db.session.execute(
        text(
            """
            SELECT TOP 1 1
            FROM dbo.SHOP_PRODUTO_IMAGENS
            WHERE PRODUTO_ID = :product_id
            """
        ),
        {"product_id": int(product_id)},
    ).first()
    db.session.execute(
        text(
            """
            INSERT INTO dbo.SHOP_PRODUTO_IMAGENS
                (PRODUTO_ID, URL, ALT_TEXT, ORDEM, E_PRINCIPAL, ATIVO, CRIADO_EM, ALTERADO_EM)
            VALUES
                (:product_id, :url, :alt_text, :ordem, :is_main, 1, SYSUTCDATETIME(), SYSUTCDATETIME())
            """
        ),
        {
            "product_id": int(product_id),
            "url": public_path,
            "alt_text": _nullable_text(alt_text, 200) or filename,
            "ordem": int(next_order),
            "is_main": 0 if has_images else 1,
        },
    )
    db.session.commit()
    return get_product_detail(product_id)


def update_product_image(product_id, image_id, payload):
    _require_tables("SHOP_PRODUTO_IMAGENS")
    exists = db.session.execute(
        text(
            """
            SELECT TOP 1 1
            FROM dbo.SHOP_PRODUTO_IMAGENS
            WHERE PRODUTO_IMAGEM_ID = :image_id
              AND PRODUTO_ID = :product_id
            """
        ),
        {"image_id": int(image_id), "product_id": int(product_id)},
    ).first()
    if not exists:
        raise ShopNotFoundError("Imagem nao encontrada.")
    if _bool_value(payload.get("E_PRINCIPAL", False)):
        db.session.execute(
            text(
                """
                UPDATE dbo.SHOP_PRODUTO_IMAGENS
                SET E_PRINCIPAL = 0, ALTERADO_EM = SYSUTCDATETIME()
                WHERE PRODUTO_ID = :product_id
                """
            ),
            {"product_id": int(product_id)},
        )
    db.session.execute(
        text(
            """
            UPDATE dbo.SHOP_PRODUTO_IMAGENS
            SET
                ALT_TEXT = :ALT_TEXT,
                ORDEM = :ORDEM,
                ATIVO = :ATIVO,
                E_PRINCIPAL = :E_PRINCIPAL,
                ALTERADO_EM = SYSUTCDATETIME()
            WHERE PRODUTO_IMAGEM_ID = :image_id
              AND PRODUTO_ID = :product_id
            """
        ),
        {
            "ALT_TEXT": _nullable_text(payload.get("ALT_TEXT"), 200),
            "ORDEM": _int_value(payload.get("ORDEM"), default=0, minimum=0),
            "ATIVO": 1 if _bool_value(payload.get("ATIVO", True)) else 0,
            "E_PRINCIPAL": 1 if _bool_value(payload.get("E_PRINCIPAL", False)) else 0,
            "image_id": int(image_id),
            "product_id": int(product_id),
        },
    )
    db.session.commit()
    return get_product_detail(product_id)


def delete_product_image(product_id, image_id):
    _require_tables("SHOP_PRODUTO_IMAGENS")
    row = db.session.execute(
        text(
            """
            SELECT URL, E_PRINCIPAL
            FROM dbo.SHOP_PRODUTO_IMAGENS
            WHERE PRODUTO_IMAGEM_ID = :image_id
              AND PRODUTO_ID = :product_id
            """
        ),
        {"image_id": int(image_id), "product_id": int(product_id)},
    ).mappings().first()
    if not row:
        raise ShopNotFoundError("Imagem nao encontrada.")
    db.session.execute(
        text(
            """
            DELETE FROM dbo.SHOP_PRODUTO_IMAGENS
            WHERE PRODUTO_IMAGEM_ID = :image_id
              AND PRODUTO_ID = :product_id
            """
        ),
        {"image_id": int(image_id), "product_id": int(product_id)},
    )
    if row.get("E_PRINCIPAL"):
        db.session.execute(
            text(
                """
                WITH first_image AS (
                    SELECT TOP 1 PRODUTO_IMAGEM_ID
                    FROM dbo.SHOP_PRODUTO_IMAGENS
                    WHERE PRODUTO_ID = :product_id
                    ORDER BY ORDEM ASC, PRODUTO_IMAGEM_ID ASC
                )
                UPDATE dbo.SHOP_PRODUTO_IMAGENS
                SET
                    E_PRINCIPAL = CASE WHEN PRODUTO_IMAGEM_ID IN (SELECT PRODUTO_IMAGEM_ID FROM first_image) THEN 1 ELSE 0 END,
                    ALTERADO_EM = SYSUTCDATETIME()
                WHERE PRODUTO_ID = :product_id
                """
            ),
            {"product_id": int(product_id)},
        )
    db.session.commit()

    image_url = _text_value(row.get("URL"))
    try:
        if image_url.startswith("/"):
            rel_path = image_url.lstrip("/").replace("/", os.sep)
            full_path = os.path.join(current_app.root_path, rel_path)
            safe_root = os.path.abspath(os.path.join(current_app.root_path, _IMAGE_FOLDER))
            if os.path.abspath(full_path).startswith(safe_root) and os.path.isfile(full_path):
                os.remove(full_path)
    except Exception:
        pass

    return get_product_detail(product_id)


def list_orders(filters=None):
    _require_tables("SHOP_ENCOMENDAS", "SHOP_ENCOMENDA_ESTADOS", "SHOP_PAGAMENTOS", "SHOP_TRANSACOES_STRIPE")
    filters = filters or {}
    q_value = _text_value(filters.get("q"), 120)
    params = {
        "q": f"%{q_value}%",
        "has_q": 1 if q_value else 0,
        "estado_id": _int_value(filters.get("estado_id"), default=0, minimum=0),
        "payment_state": _text_value(filters.get("payment_state"), 40).upper(),
        "date_from": _nullable_text(filters.get("date_from"), 20),
        "date_to": _nullable_text(filters.get("date_to"), 20),
    }
    rows = db.session.execute(
        text(
            """
            SELECT
                e.ENCOMENDA_ID,
                e.NUMERO,
                e.RESERVA,
                e.CRIADO_EM,
                e.PAGA_EM,
                e.TOTAL,
                e.SUBTOTAL,
                e.MOEDA,
                e.TOTAL_PAGO,
                e.TOTAL_REEMBOLSADO,
                est.CODIGO AS ESTADO_CODIGO,
                est.NOME AS ESTADO_NOME,
                pay.PAGAMENTO_ID,
                pay.ESTADO AS PAGAMENTO_ESTADO,
                pay.REFERENCIA_EXTERNA,
                stripe.CHECKOUT_SESSION_ID,
                stripe.PAYMENT_INTENT_ID,
                stripe.CHARGE_ID,
                stripe.EXTERNAL_STATUS AS STRIPE_STATUS,
                CASE WHEN stripe.TRANSACAO_STRIPE_ID IS NULL THEN 0 ELSE 1 END AS TEM_STRIPE
            FROM dbo.SHOP_ENCOMENDAS e
            INNER JOIN dbo.SHOP_ENCOMENDA_ESTADOS est
                ON est.ENCOMENDA_ESTADO_ID = e.ENCOMENDA_ESTADO_ID
            OUTER APPLY (
                SELECT TOP 1 PAGAMENTO_ID, ESTADO, REFERENCIA_EXTERNA
                FROM dbo.SHOP_PAGAMENTOS p
                WHERE p.ENCOMENDA_ID = e.ENCOMENDA_ID
                ORDER BY p.CRIADO_EM DESC, p.PAGAMENTO_ID DESC
            ) pay
            OUTER APPLY (
                SELECT TOP 1
                    ts.TRANSACAO_STRIPE_ID,
                    ts.CHECKOUT_SESSION_ID,
                    ts.PAYMENT_INTENT_ID,
                    ts.CHARGE_ID,
                    ts.EXTERNAL_STATUS
                FROM dbo.SHOP_TRANSACOES_STRIPE ts
                WHERE ts.PAGAMENTO_ID = pay.PAGAMENTO_ID
                ORDER BY ts.CRIADO_EM DESC, ts.TRANSACAO_STRIPE_ID DESC
            ) stripe
            WHERE
                (:has_q = 0 OR (
                    e.RESERVA LIKE :q
                    OR ISNULL(e.NUMERO, '') LIKE :q
                    OR CAST(e.ENCOMENDA_ID AS NVARCHAR(40)) LIKE :q
                ))
                AND (:estado_id = 0 OR e.ENCOMENDA_ESTADO_ID = :estado_id)
                AND (:payment_state = '' OR ISNULL(pay.ESTADO, '') = :payment_state)
                AND (:date_from IS NULL OR CAST(e.CRIADO_EM AS date) >= CAST(:date_from AS date))
                AND (:date_to IS NULL OR CAST(e.CRIADO_EM AS date) <= CAST(:date_to AS date))
            ORDER BY e.CRIADO_EM DESC, e.ENCOMENDA_ID DESC
            """
        ),
        params,
    ).mappings().all()
    items = []
    for row in rows:
        item = dict(row)
        for field in ("TOTAL", "SUBTOTAL", "TOTAL_PAGO", "TOTAL_REEMBOLSADO"):
            item[field] = _money_float(item.get(field))
        item["CRIADO_EM"] = _format_dt(item.get("CRIADO_EM"))
        item["PAGA_EM"] = _format_dt(item.get("PAGA_EM"))
        items.append(item)
    return {
        "items": items,
        "count": len(items),
        "summary": {
            "total_value": round(sum(item.get("TOTAL") or 0 for item in items), 2),
            "paid_count": sum(1 for item in items if item.get("PAGAMENTO_ESTADO") == "PAGO"),
            "stripe_count": sum(1 for item in items if item.get("TEM_STRIPE")),
        },
    }


def get_order_detail(order_id):
    _require_tables(
        "SHOP_ENCOMENDAS",
        "SHOP_ENCOMENDA_ESTADOS",
        "SHOP_ENCOMENDA_LINHAS",
        "SHOP_PAGAMENTOS",
        "SHOP_TRANSACOES_STRIPE",
        "SHOP_REEMBOLSOS",
        "SHOP_LOGS",
    )
    header = db.session.execute(
        text(
            """
            SELECT
                e.ENCOMENDA_ID, e.CARRINHO_ID, e.NUMERO, e.RESERVA, e.MOEDA,
                e.SUBTOTAL, e.TOTAL, e.TOTAL_PAGO, e.TOTAL_REEMBOLSADO,
                e.PAGA_EM, e.CANCELADA_EM, e.CRIADO_EM, e.ALTERADO_EM,
                est.CODIGO AS ESTADO_CODIGO, est.NOME AS ESTADO_NOME
            FROM dbo.SHOP_ENCOMENDAS e
            INNER JOIN dbo.SHOP_ENCOMENDA_ESTADOS est
                ON est.ENCOMENDA_ESTADO_ID = e.ENCOMENDA_ESTADO_ID
            WHERE e.ENCOMENDA_ID = :order_id
            """
        ),
        {"order_id": int(order_id)},
    ).mappings().first()
    if not header:
        raise ShopNotFoundError("Encomenda nao encontrada.")

    lines = db.session.execute(
        text(
            """
            SELECT
                ENCOMENDA_LINHA_ID, NUMERO_LINHA, PRODUTO_ID, PRODUTO_VARIANTE_ID,
                PRODUTO_NOME, VARIANTE_NOME, QUANTIDADE, PRECO_UNITARIO,
                SUBTOTAL, TOTAL, CRIADO_EM
            FROM dbo.SHOP_ENCOMENDA_LINHAS
            WHERE ENCOMENDA_ID = :order_id
            ORDER BY NUMERO_LINHA ASC, ENCOMENDA_LINHA_ID ASC
            """
        ),
        {"order_id": int(order_id)},
    ).mappings().all()
    payments = db.session.execute(
        text(
            """
            SELECT
                PAGAMENTO_ID, PROVEDOR, ESTADO, MOEDA, VALOR,
                VALOR_AUTORIZADO, VALOR_CAPTURADO, VALOR_REEMBOLSADO,
                REFERENCIA_EXTERNA, PAGO_EM, CRIADO_EM, ALTERADO_EM
            FROM dbo.SHOP_PAGAMENTOS
            WHERE ENCOMENDA_ID = :order_id
            ORDER BY CRIADO_EM DESC, PAGAMENTO_ID DESC
            """
        ),
        {"order_id": int(order_id)},
    ).mappings().all()
    transactions = db.session.execute(
        text(
            """
            SELECT
                ts.TRANSACAO_STRIPE_ID, ts.PAGAMENTO_ID, ts.TIPO_TRANSACAO,
                ts.EVENT_ID, ts.EVENT_TYPE, ts.IDEMPOTENCY_KEY, ts.PAYMENT_INTENT_ID,
                ts.CHECKOUT_SESSION_ID, ts.CHARGE_ID, ts.REFUND_ID,
                ts.EXTERNAL_STATUS, ts.MOEDA, ts.VALOR, ts.PAYLOAD, ts.CRIADO_EM
            FROM dbo.SHOP_TRANSACOES_STRIPE ts
            INNER JOIN dbo.SHOP_PAGAMENTOS p
                ON p.PAGAMENTO_ID = ts.PAGAMENTO_ID
            WHERE p.ENCOMENDA_ID = :order_id
            ORDER BY ts.CRIADO_EM DESC, ts.TRANSACAO_STRIPE_ID DESC
            """
        ),
        {"order_id": int(order_id)},
    ).mappings().all()
    refunds = db.session.execute(
        text(
            """
            SELECT
                r.REEMBOLSO_ID, r.PAGAMENTO_ID, r.ESTADO, r.MOEDA, r.VALOR,
                r.MOTIVO, r.REFUND_ID_EXTERNO, r.PROCESSADO_EM, r.CRIADO_EM, r.ALTERADO_EM
            FROM dbo.SHOP_REEMBOLSOS r
            INNER JOIN dbo.SHOP_PAGAMENTOS p
                ON p.PAGAMENTO_ID = r.PAGAMENTO_ID
            WHERE p.ENCOMENDA_ID = :order_id
            ORDER BY r.CRIADO_EM DESC, r.REEMBOLSO_ID DESC
            """
        ),
        {"order_id": int(order_id)},
    ).mappings().all()
    logs = db.session.execute(
        text(
            """
            SELECT TOP 50
                LOG_ID, NIVEL, CATEGORIA, EVENTO, ENTIDADE, ENTIDADE_ID, RESERVA,
                ENCOMENDA_ID, PAGAMENTO_ID, TRANSACAO_STRIPE_ID, MENSAGEM, DETALHE, CRIADO_EM
            FROM dbo.SHOP_LOGS
            WHERE ENCOMENDA_ID = :order_id
            ORDER BY CRIADO_EM DESC, LOG_ID DESC
            """
        ),
        {"order_id": int(order_id)},
    ).mappings().all()

    header_item = dict(header)
    for field in ("SUBTOTAL", "TOTAL", "TOTAL_PAGO", "TOTAL_REEMBOLSADO"):
        header_item[field] = _money_float(header_item.get(field))
    for field in ("PAGA_EM", "CANCELADA_EM", "CRIADO_EM", "ALTERADO_EM"):
        header_item[field] = _format_dt(header_item.get(field))

    line_items = []
    for row in lines:
        item = dict(row)
        for field in ("PRECO_UNITARIO", "SUBTOTAL", "TOTAL"):
            item[field] = _money_float(item.get(field))
        item["CRIADO_EM"] = _format_dt(item.get("CRIADO_EM"))
        line_items.append(item)

    payment_items = []
    for row in payments:
        item = dict(row)
        for field in ("VALOR", "VALOR_AUTORIZADO", "VALOR_CAPTURADO", "VALOR_REEMBOLSADO"):
            item[field] = _money_float(item.get(field))
        for field in ("PAGO_EM", "CRIADO_EM", "ALTERADO_EM"):
            item[field] = _format_dt(item.get(field))
        payment_items.append(item)

    transaction_items = []
    for row in transactions:
        item = dict(row)
        item["VALOR"] = None if item.get("VALOR") is None else _money_float(item.get("VALOR"))
        item["CRIADO_EM"] = _format_dt(item.get("CRIADO_EM"))
        item["PAYLOAD_SUMMARY"] = _payload_summary(item.get("PAYLOAD"))
        transaction_items.append(item)

    refund_items = []
    for row in refunds:
        item = dict(row)
        item["VALOR"] = _money_float(item.get("VALOR"))
        for field in ("PROCESSADO_EM", "CRIADO_EM", "ALTERADO_EM"):
            item[field] = _format_dt(item.get(field))
        refund_items.append(item)

    log_items = []
    for row in logs:
        item = dict(row)
        item["CRIADO_EM"] = _format_dt(item.get("CRIADO_EM"))
        item["DETALHE_RESUMO"] = _payload_summary(item.get("DETALHE"))
        log_items.append(item)

    return {
        "header": header_item,
        "lines": line_items,
        "payments": payment_items,
        "transactions": transaction_items,
        "refunds": refund_items,
        "logs": log_items,
    }
