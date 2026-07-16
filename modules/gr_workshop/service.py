from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any
import json
import os
import uuid
from urllib import error as urllib_error
from urllib import request as urllib_request

from flask import current_app
from sqlalchemy import text

from models import db
from services.multiempresa_service import get_current_feid


WORKSHOP_STATES = [
    {"code": "ABERTA", "label": "Aberta", "tone": "secondary"},
    {"code": "EXECUCAO", "label": "Em execução", "tone": "primary"},
    {"code": "CONCLUIDA", "label": "Concluída", "tone": "success"},
    {"code": "ANULADA", "label": "Anulada", "tone": "danger"},
]
WORKSHOP_STATE_CODES = {item["code"] for item in WORKSHOP_STATES}
PLANNING_DAY_START_MINUTES = 8 * 60
PLANNING_DAY_END_MINUTES = 20 * 60
PLANNING_SLOT_MINUTES = 15


class WorkshopError(Exception):
    status_code = 500


class WorkshopValidationError(WorkshopError):
    status_code = 400


class WorkshopNotFoundError(WorkshopError):
    status_code = 404


def _new_stamp() -> str:
    return uuid.uuid4().hex.upper()[:25]


def _para_value(code: str, default: str = "") -> str:
    key = _text(code)
    if not key:
        return default

    try:
        configured = current_app.config.get("PARA_VALUES") or {}
        value = configured.get(key)
        if value in (None, ""):
            value = configured.get(key.upper())
        if value not in (None, ""):
            return str(value).strip()
    except Exception:
        pass

    row = db.session.execute(
        text(
            """
            SELECT TOP 1 TIPO, CVALOR, DVALOR, NVALOR, LVALOR
            FROM dbo.PARA
            WHERE UPPER(LTRIM(RTRIM(PARAMETRO))) = UPPER(LTRIM(RTRIM(:code)))
            """
        ),
        {"code": key},
    ).mappings().first()
    if not row:
        return default

    value_type = _text(row.get("TIPO")).upper()
    if value_type == "N":
        return str(row.get("NVALOR") or "")
    if value_type == "D":
        return str(row.get("DVALOR") or "")
    if value_type == "L":
        return "1" if bool(row.get("LVALOR") or 0) else "0"
    return _text(row.get("CVALOR")) or default


def _workshop_ai_api_key() -> str:
    return (
        _para_value("WORKSHOP_OPENAI_API_KEY")
        or _para_value("SHOP_TRANSLATE_OPENAI_API_KEY")
        or _para_value("OPENAI_API_KEY")
        or os.getenv("WORKSHOP_OPENAI_API_KEY")
        or os.getenv("SHOP_TRANSLATE_OPENAI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or ""
    ).strip()


def _workshop_ai_model() -> str:
    return (
        _para_value("WORKSHOP_OPENAI_MODEL")
        or _para_value("OPENAI_MODEL")
        or os.getenv("WORKSHOP_OPENAI_MODEL")
        or os.getenv("OPENAI_MODEL")
        or "gpt-5"
    ).strip()


def workshop_ai_available() -> bool:
    return bool(_workshop_ai_api_key())


def _extract_openai_text(payload: dict[str, Any]) -> str:
    direct = _text(payload.get("output_text"))
    if direct:
        return direct
    for output in payload.get("output") or []:
        for content in output.get("content") or []:
            if content.get("type") == "output_text":
                value = _text(content.get("text"))
                if value:
                    return value
    return ""


def _parse_openai_json(raw: str) -> dict[str, Any]:
    value = _text(raw)
    if value.startswith("```"):
        lines = value.splitlines()
        value = "\n".join(lines[1:-1] if len(lines) > 2 else [])
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError) as exc:
        raise WorkshopError("A AI não devolveu uma sugestão válida.") from exc
    if not isinstance(parsed, dict):
        raise WorkshopError("A AI não devolveu uma sugestão válida.")
    return parsed


def _text(value: Any, limit: int = 0) -> str:
    cleaned = str(value or "").strip()
    if limit and len(cleaned) > limit:
        return cleaned[:limit]
    return cleaned


def _decimal(value: Any, default: str = "0") -> Decimal:
    raw = str(value if value is not None else "").strip().replace(",", ".")
    if not raw:
        raw = default
    try:
        return Decimal(raw)
    except (InvalidOperation, ValueError) as exc:
        raise WorkshopValidationError("Valor numérico inválido.") from exc


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def _qty(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def _int_value(value: Any, *, default: int = 0, minimum: int | None = None, label: str = "Valor") -> int:
    raw = str(value if value is not None else "").strip()
    if raw == "":
        parsed = default
    else:
        try:
            parsed = int(float(raw.replace(",", ".")))
        except (TypeError, ValueError) as exc:
            raise WorkshopValidationError(f"{label} inválido.") from exc
    if minimum is not None and parsed < minimum:
        raise WorkshopValidationError(f"{label} inválido.")
    return parsed


def _date_value(value: Any, *, required: bool = False, label: str = "Data") -> date | None:
    raw = str(value or "").strip()
    if not raw:
        if required:
            raise WorkshopValidationError(f"{label} obrigatória.")
        return None
    for candidate in (raw, raw[:10]):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(candidate, fmt).date()
            except ValueError:
                continue
    try:
        return datetime.fromisoformat(raw).date()
    except ValueError as exc:
        raise WorkshopValidationError(f"{label} inválida.") from exc


def _time_value(value: Any, *, required: bool = False, label: str = "Hora") -> str:
    raw = str(value or "").strip()
    if not raw:
        if required:
            raise WorkshopValidationError(f"{label} obrigatória.")
        return ""
    if len(raw) >= 5:
        raw = raw[:5]
    try:
        parsed = datetime.strptime(raw, "%H:%M").time()
    except ValueError as exc:
        raise WorkshopValidationError(f"{label} inválida. Usa HH:MM.") from exc
    return parsed.strftime("%H:%M")


def _legacy_dt(day: date | None, hour: str) -> datetime | None:
    if not day or not hour:
        return None
    parsed_hour = datetime.strptime(hour, "%H:%M").time()
    return datetime.combine(day, parsed_hour)


def _table_exists(table_name: str) -> bool:
    return db.session.execute(
        text(
            """
            SELECT 1
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = :table_name
            """
        ),
        {"table_name": table_name},
    ).first() is not None


def _table_column_exists(table_name: str, column_name: str) -> bool:
    return db.session.execute(
        text(
            """
            SELECT 1
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'dbo'
              AND TABLE_NAME = :table_name
              AND COLUMN_NAME = :column_name
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    ).first() is not None


def ensure_schema_available() -> None:
    missing = [
        name
        for name in ("OFICINA_TRAB", "OFICINA_MEC", "OFICINA_FOLHA", "OFICINA_LINHA", "VA", "ST")
        if not _table_exists(name)
    ]
    if missing:
        raise WorkshopValidationError(
            "Tabelas em falta: " + ", ".join(missing) + ". Executa migrations/gr_oficina_schema.sql."
        )


def _current_feid() -> int:
    try:
        return int(get_current_feid() or 0)
    except Exception as exc:
        raise WorkshopValidationError("Empresa ativa não definida.") from exc


def _state_meta(code: str) -> dict[str, str]:
    normalized = _text(code).upper()
    return next((item for item in WORKSHOP_STATES if item["code"] == normalized), WORKSHOP_STATES[0])


def _date_only_iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return ""


def _datetime_local_iso(day: str, hour: str) -> str:
    if not day or not hour:
        return ""
    return f"{day}T{hour}"


def _minutes_from_time(value: str) -> int:
    hour = _time_value(value, required=True)
    parts = hour.split(":")
    return int(parts[0]) * 60 + int(parts[1])


def _time_from_minutes(value: int) -> str:
    safe = max(0, min(23 * 60 + 59, int(value or 0)))
    return f"{safe // 60:02d}:{safe % 60:02d}"


def _week_start(value: Any = None) -> date:
    parsed = _date_value(value) if value else date.today()
    if not parsed:
        parsed = date.today()
    return parsed - timedelta(days=parsed.weekday())


def _next_no(feid: int) -> int:
    value = db.session.execute(
        text(
            """
            SELECT ISNULL(MAX(NO), 0) + 1 AS NEXT_NO
            FROM dbo.OFICINA_FOLHA WITH (UPDLOCK, HOLDLOCK)
            WHERE FEID = :feid
            """
        ),
        {"feid": feid},
    ).scalar()
    try:
        return max(1, int(value or 1))
    except Exception:
        return 1


def list_mechanics() -> list[dict[str, Any]]:
    rows = db.session.execute(
        text(
            """
            SELECT
                LTRIM(RTRIM(ISNULL(OFICINA_MECSTAMP, ''))) AS OFICINA_MECSTAMP,
                LTRIM(RTRIM(ISNULL(NOME, ''))) AS NOME,
                LTRIM(RTRIM(ISNULL(COR, ''))) AS COR
            FROM dbo.OFICINA_MEC
            WHERE LTRIM(RTRIM(ISNULL(NOME, ''))) <> ''
            ORDER BY NOME
            """
        )
    ).mappings().all()
    return [
        {
            "OFICINA_MECSTAMP": _text(row["OFICINA_MECSTAMP"], 25),
            "NOME": _text(row["NOME"], 60),
            "COR": _text(row["COR"], 18) or "#60A5FA",
        }
        for row in rows
    ]


def _mechanic_stamp(value: Any, *, allow_empty: bool = True) -> str | None:
    stamp = _text(value, 25)
    if not stamp:
        if allow_empty:
            return None
        raise WorkshopValidationError("Mecânico obrigatório.")
    row = db.session.execute(
        text(
            """
            SELECT TOP 1 OFICINA_MECSTAMP
            FROM dbo.OFICINA_MEC
            WHERE OFICINA_MECSTAMP = :stamp
            """
        ),
        {"stamp": stamp},
    ).first()
    if not row:
        raise WorkshopValidationError("Mecânico inválido.")
    return stamp


def list_vehicles(term: str = "", limit: int = 40) -> list[dict[str, Any]]:
    query = f"%{_text(term)}%"
    safe_limit = max(1, min(int(limit or 40), 100))
    rows = db.session.execute(
        text(
            f"""
            SELECT TOP ({safe_limit})
                LTRIM(RTRIM(ISNULL(VASTAMP, ''))) AS VASTAMP,
                LTRIM(RTRIM(ISNULL(MATRICULA, ''))) AS MATRICULA,
                LTRIM(RTRIM(ISNULL(MARCA, ''))) AS MARCA,
                LTRIM(RTRIM(ISNULL(MODELO, ''))) AS MODELO,
                LTRIM(RTRIM(ISNULL(NOFROTA, ''))) AS NOFROTA
            FROM dbo.VA
            WHERE ISNULL(INATIVO, 0) = 0
              AND LTRIM(RTRIM(ISNULL(MATRICULA, ''))) <> ''
              AND (
                    :query = '%%'
                 OR MATRICULA LIKE :query
                 OR MARCA LIKE :query
                 OR MODELO LIKE :query
                 OR NOFROTA LIKE :query
              )
            ORDER BY LTRIM(RTRIM(ISNULL(MATRICULA, '')))
            """
        ),
        {"query": query},
    ).mappings().all()
    return [
        {
            "VASTAMP": row["VASTAMP"],
            "MATRICULA": row["MATRICULA"],
            "MARCA": row["MARCA"],
            "MODELO": row["MODELO"],
            "NOFROTA": row["NOFROTA"],
            "value": row["MATRICULA"],
            "display": [
                row["MATRICULA"],
                " ".join(part for part in (row["MARCA"], row["MODELO"]) if part),
                row["NOFROTA"],
            ],
            "row": {
                "VASTAMP": row["VASTAMP"],
                "MATRICULA": row["MATRICULA"],
                "MARCA": row["MARCA"],
                "MODELO": row["MODELO"],
                "NOFROTA": row["NOFROTA"],
            },
            "LABEL": " ".join(
                part for part in (row["MATRICULA"], row["MARCA"], row["MODELO"], row["NOFROTA"]) if part
            ),
        }
        for row in rows
    ]


def _vehicle_by_stamp_or_plate(vastamp: str = "", matricula: str = "") -> dict[str, Any]:
    stamp = _text(vastamp, 25)
    plate = _text(matricula, 12)
    if not stamp and not plate:
        raise WorkshopValidationError("Viatura obrigatória.")
    row = db.session.execute(
        text(
            """
            SELECT TOP 1 VA.*
            FROM dbo.VA VA
            WHERE ISNULL(VA.INATIVO, 0) = 0
              AND (
                    (:vastamp <> '' AND VA.VASTAMP = :vastamp)
                 OR (:matricula <> '' AND VA.MATRICULA = :matricula)
              )
            """
        ),
        {"vastamp": stamp, "matricula": plate},
    ).mappings().first()
    if not row:
        raise WorkshopValidationError("Viatura inválida ou inativa.")
    return dict(row)


def list_articles(term: str = "", limit: int = 40) -> list[dict[str, Any]]:
    feid = _current_feid()
    query = f"%{_text(term)}%"
    safe_limit = max(1, min(int(limit or 40), 100))
    rows = db.session.execute(
        text(
            f"""
            SELECT TOP ({safe_limit})
                LTRIM(RTRIM(ISNULL(STSTAMP, ''))) AS STSTAMP,
                LTRIM(RTRIM(ISNULL(REF, ''))) AS REF,
                LTRIM(RTRIM(ISNULL(DESIGN, ''))) AS DESIGN,
                LTRIM(RTRIM(ISNULL(UNIDADE, ''))) AS UNIDADE,
                ISNULL(EPV, 0) AS EPV,
                LTRIM(RTRIM(ISNULL(FAMILIA, ''))) AS FAMILIA,
                LTRIM(RTRIM(ISNULL(FAMINOME, ''))) AS FAMINOME
            FROM dbo.ST
            WHERE ISNULL(FEID, 0) = :feid
              AND ISNULL(INATIVO, 0) = 0
              AND LTRIM(RTRIM(ISNULL(REF, ''))) <> ''
              AND (
                    :query = '%%'
                 OR REF LIKE :query
                 OR DESIGN LIKE :query
                 OR FAMILIA LIKE :query
                 OR FAMINOME LIKE :query
              )
            ORDER BY LTRIM(RTRIM(ISNULL(REF, '')))
            """
        ),
        {"feid": feid, "query": query},
    ).mappings().all()
    return [
        {
            "STSTAMP": row["STSTAMP"],
            "REF": row["REF"],
            "DESIGN": row["DESIGN"],
            "UNIDADE": row["UNIDADE"],
            "PUNIT": float(row["EPV"] or 0),
            "FAMILIA": row["FAMILIA"],
            "FAMINOME": row["FAMINOME"],
        }
        for row in rows
    ]


def list_work_types(term: str = "", include_inactive: bool = False, limit: int = 100) -> list[dict[str, Any]]:
    feid = _current_feid()
    query = f"%{_text(term)}%"
    safe_limit = max(1, min(int(limit or 100), 300))
    active_sql = "" if include_inactive else "AND ISNULL(ATIVO, 0) = 1"
    rows = db.session.execute(
        text(
            f"""
            SELECT TOP ({safe_limit})
                OFICINA_TRABSTAMP,
                CODIGO,
                DESCRICAO,
                ISNULL(ATIVO, 0) AS ATIVO,
                ISNULL(ORDEM, 0) AS ORDEM
            FROM dbo.OFICINA_TRAB
            WHERE FEID = :feid
              {active_sql}
              AND (
                    :query = '%%'
                 OR CODIGO LIKE :query
                 OR DESCRICAO LIKE :query
              )
            ORDER BY ISNULL(ORDEM, 0), DESCRICAO, CODIGO
            """
        ),
        {"feid": feid, "query": query},
    ).mappings().all()
    return [
        {
            "OFICINA_TRABSTAMP": _text(row["OFICINA_TRABSTAMP"]),
            "CODIGO": _text(row["CODIGO"]),
            "DESCRICAO": _text(row["DESCRICAO"]),
            "ATIVO": bool(row["ATIVO"]),
            "ORDEM": int(row["ORDEM"] or 0),
        }
        for row in rows
    ]


def save_work_type(payload: dict[str, Any], user_login: str = "", stamp: str = "") -> dict[str, Any]:
    feid = _current_feid()
    target_stamp = _text(stamp or payload.get("OFICINA_TRABSTAMP"), 25)
    codigo = _text(payload.get("CODIGO"), 20).upper()
    descricao = _text(payload.get("DESCRICAO"), 255)
    ativo = 1 if bool(payload.get("ATIVO", True)) else 0
    try:
        ordem = int(payload.get("ORDEM") or 0)
    except Exception:
        ordem = 0
    if not codigo:
        raise WorkshopValidationError("Código do trabalho obrigatório.")
    if not descricao:
        raise WorkshopValidationError("Descrição do trabalho obrigatória.")

    params = {
        "stamp": target_stamp or _new_stamp(),
        "feid": feid,
        "codigo": codigo,
        "descricao": descricao,
        "ativo": ativo,
        "ordem": ordem,
        "user": _text(user_login, 60),
    }
    if target_stamp:
        result = db.session.execute(
            text(
                """
                UPDATE dbo.OFICINA_TRAB
                   SET CODIGO = :codigo,
                       DESCRICAO = :descricao,
                       ATIVO = :ativo,
                       ORDEM = :ordem,
                       DTALT = SYSDATETIME(),
                       USERALTERACAO = :user
                 WHERE OFICINA_TRABSTAMP = :stamp
                   AND FEID = :feid
                """
            ),
            params,
        )
        if result.rowcount == 0:
            raise WorkshopNotFoundError("Trabalho não encontrado.")
    else:
        db.session.execute(
            text(
                """
                INSERT INTO dbo.OFICINA_TRAB
                    (OFICINA_TRABSTAMP, FEID, CODIGO, DESCRICAO, ATIVO, ORDEM, USERCRIACAO, USERALTERACAO)
                VALUES
                    (:stamp, :feid, :codigo, :descricao, :ativo, :ordem, :user, :user)
                """
            ),
            params,
        )
    db.session.commit()
    return {"work": get_work_type(params["stamp"])}


def get_work_type(stamp: str) -> dict[str, Any]:
    feid = _current_feid()
    row = db.session.execute(
        text(
            """
            SELECT OFICINA_TRABSTAMP, CODIGO, DESCRICAO, ISNULL(ATIVO, 0) AS ATIVO, ISNULL(ORDEM, 0) AS ORDEM
            FROM dbo.OFICINA_TRAB
            WHERE OFICINA_TRABSTAMP = :stamp
              AND FEID = :feid
            """
        ),
        {"stamp": _text(stamp, 25), "feid": feid},
    ).mappings().first()
    if not row:
        raise WorkshopNotFoundError("Trabalho não encontrado.")
    return {
        "OFICINA_TRABSTAMP": _text(row["OFICINA_TRABSTAMP"]),
        "CODIGO": _text(row["CODIGO"]),
        "DESCRICAO": _text(row["DESCRICAO"]),
        "ATIVO": bool(row["ATIVO"]),
        "ORDEM": int(row["ORDEM"] or 0),
    }


def _vehicle_ai_context(vehicle: dict[str, Any]) -> dict[str, Any]:
    """Expose all filled operational VA fields, while omitting internal audit data."""
    excluded = {
        "VASTAMP",
        "FEID",
        "INATIVO",
        "DTCRI",
        "DTALT",
        "USERCRIACAO",
        "USERALTERACAO",
    }
    context: dict[str, Any] = {}
    for raw_key, raw_value in vehicle.items():
        key = _text(raw_key).upper()
        if not key or key in excluded or isinstance(raw_value, (bytes, bytearray, memoryview)):
            continue
        if raw_value is None or (isinstance(raw_value, str) and not raw_value.strip()):
            continue
        if isinstance(raw_value, datetime):
            context[key] = raw_value.isoformat(sep=" ", timespec="minutes")
        elif isinstance(raw_value, date):
            context[key] = raw_value.isoformat()
        elif isinstance(raw_value, Decimal):
            context[key] = float(raw_value)
        elif isinstance(raw_value, (bool, int, float)):
            context[key] = raw_value
        else:
            context[key] = _text(raw_value, 500)
    return context


def _suggestion_parts(value: Any, limit: int = 8) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        description = _text(item.get("description"), 140)
        if not description:
            continue
        row = {
            "description": description,
            "supplier_reference": _text(item.get("supplier_reference"), 80),
            "quantity": _text(item.get("quantity"), 30),
            "note": _text(item.get("note"), 120),
            "source_url": _text(item.get("source_url"), 300),
        }
        if row not in rows:
            rows.append(row)
        if len(rows) >= limit:
            break
    return rows


def _suggestion_list(value: Any, limit: int = 8) -> list[str]:
    if not isinstance(value, list):
        return []
    rows: list[str] = []
    for item in value:
        cleaned = _text(item, 180)
        if cleaned and cleaned not in rows:
            rows.append(cleaned)
        if len(rows) >= limit:
            break
    return rows


def _format_ai_observations(procedure: str, parts: list[dict[str, str]], tools: list[str]) -> str:
    sections = [procedure]
    if parts:
        part_lines = []
        for part in parts:
            line = part["description"]
            if part["supplier_reference"]:
                line += f" | Ref. fornecedor/OEM (confirmar): {part['supplier_reference']}"
            if part["quantity"]:
                line += f" | Qtd.: {part['quantity']}"
            if part["note"]:
                line += f" | {part['note']}"
            if part["source_url"]:
                line += f" | Fonte: {part['source_url']}"
            part_lines.append(f"- {line}")
        sections.append("PEÇAS A PREPARAR/CONFIRMAR:\n" + "\n".join(part_lines))
    if tools:
        sections.append("FERRAMENTAS/EQUIPAMENTO:\n" + "\n".join(f"- {tool}" for tool in tools))
    return _text("\n\n".join(sections), 4000)


def suggest_workshop_job(payload: dict[str, Any]) -> dict[str, Any]:
    """Return an AI estimate without changing the work order itself."""
    ensure_schema_available()
    api_key = _workshop_ai_api_key()
    if not api_key:
        raise WorkshopValidationError(
            "Integração AI indisponível. Configura WORKSHOP_OPENAI_API_KEY ou OPENAI_API_KEY na tabela PARA."
        )

    vehicle = _vehicle_by_stamp_or_plate(
        _text(payload.get("VASTAMP"), 25),
        _text(payload.get("MATRICULA"), 12),
    )
    work_type = get_work_type(_text(payload.get("OFICINA_TRABSTAMP"), 25))
    if not work_type["ATIVO"]:
        raise WorkshopValidationError("O trabalho pré-definido selecionado está inativo.")

    vehicle_context = _vehicle_ai_context(vehicle)
    request_context = {
        "dados_da_ficha_da_viatura": vehicle_context,
        "trabalho_pre_definido": {
            "codigo": work_type["CODIGO"],
            "descricao": work_type["DESCRICAO"],
        },
    }
    request_body = {
        "model": _workshop_ai_model(),
        "reasoning": {"effort": "low"},
        "tools": [{"type": "web_search", "search_context_size": "medium"}],
        "tool_choice": "required",
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "És um assistente de planeamento para uma oficina de automóveis de ligeiros e pesados. "
                            "Estima o tempo de mão de obra habitualmente necessário e cria instruções práticas para o mecânico. "
                            "Usa todos os dados preenchidos da ficha da viatura para adequar a sugestão. "
                            "Tens de pesquisar na internet antes de responder, procurando catálogos OEM, fabricantes e fornecedores. "
                            "Não inventes dados específicos do manual ou do veículo. Quando a informação for insuficiente, "
                            "assinala verificações a confirmar. Não incluas preços, nem texto em Markdown."
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": json.dumps(
                            {
                                "pedido": "Estimar duração e instruções de trabalho.",
                                "regras": [
                                    "estimated_minutes deve ser um número inteiro entre 5 e 1440, arredondado a 5 minutos.",
                                    "Antes de responder, pesquisa pelo VIN/chassis exato, pelo motor exato e por marca/modelo/ano. Faz pesquisa específica apenas para as três peças principais.",
                                    "instructions deve ser um procedimento conciso em português, até 1200 caracteres.",
                                    "parts deve listar as peças ou consumíveis a preparar/confirmar, incluindo quantidades apenas quando seguras.",
                                    "Para cada peça, supplier_reference deve conter a referência OEM ou do fornecedor para encomenda, nunca uma referência interna de stock.",
                                    "source_url deve conter o URL da página de catálogo/fabricante/fornecedor onde a referência foi encontrada.",
                                    "tools deve listar ferramentas e equipamento necessários.",
                                    "Só devolve supplier_reference e source_url quando a pesquisa os confirmar explicitamente; caso contrário devolve strings vazias.",
                                    "Nunca inventes uma referência OEM/fornecedor e indica sempre confirmar compatibilidade quando aplicável.",
                                    "Inclui preparação, verificações de segurança e testes finais relevantes.",
                                ],
                                "contexto": request_context,
                            },
                            ensure_ascii=False,
                        ),
                    }
                ],
            },
        ],
        # A pesquisa web e o raciocínio do GPT-5 também consomem o orçamento.
        # Com 1.000 tokens a resposta podia ficar incompleta antes do JSON final.
        "max_output_tokens": 3000,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "workshop_job_suggestion",
                "strict": True,
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "estimated_minutes": {"type": "integer"},
                        "instructions": {"type": "string"},
                        "parts": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "description": {"type": "string"},
                                    "supplier_reference": {"type": "string"},
                                    "quantity": {"type": "string"},
                                    "note": {"type": "string"},
                                    "source_url": {"type": "string"},
                                },
                                "required": ["description", "supplier_reference", "quantity", "note", "source_url"],
                            },
                        },
                        "tools": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["estimated_minutes", "instructions", "parts", "tools"],
                },
            }
        },
    }
    req = urllib_request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(request_body).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    result: dict[str, Any] | None = None
    last_http_error: urllib_error.HTTPError | None = None
    try:
        # A chamada ocorre dentro de uma interação do utilizador. Nunca deve
        # prender o modal por vários minutos quando a pesquisa externa atrasa.
        with urllib_request.urlopen(req, timeout=50) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib_error.HTTPError as exc:
        last_http_error = exc
    except Exception as exc:
        raise WorkshopError(
            "A pesquisa AI demorou demasiado a responder. Tenta novamente dentro de instantes."
        ) from exc

    if last_http_error:
        if last_http_error.code in {401, 403}:
            raise WorkshopError("A chave da integração AI foi recusada pela OpenAI.") from last_http_error
        if last_http_error.code == 429:
            raise WorkshopError("A integração AI atingiu temporariamente o limite de utilização.") from last_http_error
        if last_http_error.code >= 500:
            raise WorkshopError(
                "A pesquisa web da OpenAI está temporariamente indisponível. Tenta novamente dentro de instantes."
            ) from last_http_error
        raise WorkshopError(f"A integração AI rejeitou o pedido (HTTP {last_http_error.code}).") from last_http_error
    if not isinstance(result, dict):
        raise WorkshopError("A integração AI não devolveu uma resposta utilizável.")
    if result.get("status") == "incomplete":
        detail = result.get("incomplete_details") or {}
        if detail.get("reason") == "max_output_tokens":
            raise WorkshopError(
                "A AI demorou demasiado na pesquisa das referências e não concluiu a sugestão. Tenta novamente."
            )
        raise WorkshopError("A AI não concluiu a sugestão. Tenta novamente.")

    suggestion = _parse_openai_json(_extract_openai_text(result))
    try:
        estimated_minutes = int(suggestion.get("estimated_minutes"))
    except (TypeError, ValueError) as exc:
        raise WorkshopError("A AI não devolveu um tempo de trabalho válido.") from exc
    estimated_minutes = max(5, min(1440, int(round(estimated_minutes / 5.0) * 5)))
    procedure = _text(suggestion.get("instructions"), 1200)
    if not procedure:
        raise WorkshopError("A AI não devolveu instruções de trabalho válidas.")
    parts = _suggestion_parts(suggestion.get("parts"))
    tools = _suggestion_list(suggestion.get("tools"))
    instructions = _format_ai_observations(procedure, parts, tools)

    return {
        "estimated_minutes": estimated_minutes,
        "instructions": instructions,
        "procedure": procedure,
        "parts": parts,
        "tools": tools,
        "vehicle": vehicle_context,
        "work_type": request_context["trabalho_pre_definido"],
        "model": _workshop_ai_model(),
    }


def list_sheets(args: dict[str, Any]) -> dict[str, Any]:
    feid = _current_feid()
    term = _text(args.get("q") or args.get("search"))
    estado = _text(args.get("estado")).upper()
    if estado and estado not in WORKSHOP_STATE_CODES:
        estado = ""
    params: dict[str, Any] = {"feid": feid, "term": f"%{term}%", "estado": estado}
    where = ["F.FEID = :feid"]
    if term:
        where.append(
            """
            (
                CAST(F.NO AS varchar(20)) LIKE :term
             OR F.MATRICULA LIKE :term
             OR F.TRABALHO LIKE :term
             OR ISNULL(T.DESCRICAO, '') LIKE :term
             OR ISNULL(M.NOME, '') LIKE :term
            )
            """
        )
    if estado:
        where.append("F.ESTADO = :estado")

    rows = db.session.execute(
        text(
            f"""
            SELECT TOP 300
                F.OFICINA_FOLHASTAMP,
                F.NO,
                F.VASTAMP,
                F.MATRICULA,
                F.OFICINA_TRABSTAMP,
                ISNULL(T.CODIGO, '') AS TRAB_CODIGO,
                ISNULL(T.DESCRICAO, '') AS TRAB_DESCRICAO,
                F.TRABALHO,
                F.DATA,
                F.HORAINI,
                F.HORAFIM,
                F.TEMPO,
                F.OFICINA_MECSTAMP,
                ISNULL(M.NOME, '') AS MECANICO,
                ISNULL(M.COR, '') AS MECANICO_COR,
                F.PLAN_DATA,
                F.PLAN_HORAINI,
                F.PLAN_HORAFIM,
                F.ESTADO,
                F.TOTAL,
                ISNULL(V.MARCA, '') AS MARCA,
                ISNULL(V.MODELO, '') AS MODELO,
                ISNULL(V.NOFROTA, '') AS NOFROTA
            FROM dbo.OFICINA_FOLHA F
            LEFT JOIN dbo.OFICINA_TRAB T
              ON T.OFICINA_TRABSTAMP = F.OFICINA_TRABSTAMP
            LEFT JOIN dbo.OFICINA_MEC M
              ON M.OFICINA_MECSTAMP = F.OFICINA_MECSTAMP
            LEFT JOIN dbo.VA V
              ON V.VASTAMP = F.VASTAMP
            WHERE {" AND ".join(where)}
            ORDER BY F.DATA DESC, F.HORAINI DESC, F.NO DESC
            """
        ),
        params,
    ).mappings().all()
    items = [_sheet_row(row) for row in rows]
    return {
        "items": items,
        "summary": {
            "total": len(items),
            "open": sum(1 for item in items if item["ESTADO"] in {"ABERTA", "EXECUCAO"}),
            "done": sum(1 for item in items if item["ESTADO"] == "CONCLUIDA"),
            "void": sum(1 for item in items if item["ESTADO"] == "ANULADA"),
        },
    }


def _sheet_row(row: Any) -> dict[str, Any]:
    state = _state_meta(row["ESTADO"])
    vehicle = " ".join(
        part
        for part in (
            _text(row["MATRICULA"]),
            _text(row.get("MARCA") if hasattr(row, "get") else row["MARCA"]),
            _text(row.get("MODELO") if hasattr(row, "get") else row["MODELO"]),
            _text(row.get("NOFROTA") if hasattr(row, "get") else row["NOFROTA"]),
        )
        if part
    )
    item = {
        "OFICINA_FOLHASTAMP": _text(row["OFICINA_FOLHASTAMP"]),
        "NO": int(row["NO"] or 0),
        "VASTAMP": _text(row["VASTAMP"]),
        "MATRICULA": _text(row["MATRICULA"]),
        "VEICULO_LABEL": vehicle,
        "OFICINA_TRABSTAMP": _text(row["OFICINA_TRABSTAMP"]),
        "TRAB_CODIGO": _text(row["TRAB_CODIGO"]),
        "TRAB_DESCRICAO": _text(row["TRAB_DESCRICAO"]),
        "TRABALHO": _text(row["TRABALHO"]),
        "DATA": _date_only_iso(row["DATA"]),
        "HORAINI": _text(row["HORAINI"], 5),
        "HORAFIM": _text(row["HORAFIM"], 5),
        "TEMPO": int(row["TEMPO"] or 0),
        "OFICINA_MECSTAMP": _text(row.get("OFICINA_MECSTAMP") if hasattr(row, "get") else row["OFICINA_MECSTAMP"], 25),
        "MECANICO": _text(row.get("MECANICO") if hasattr(row, "get") else row["MECANICO"], 60),
        "MECANICO_COR": _text(row.get("MECANICO_COR") if hasattr(row, "get") else row["MECANICO_COR"], 18),
        "PLAN_DATA": _date_only_iso(row["PLAN_DATA"]),
        "PLAN_HORAINI": _text(row["PLAN_HORAINI"], 5),
        "PLAN_HORAFIM": _text(row["PLAN_HORAFIM"], 5),
        "ESTADO": state["code"],
        "ESTADO_LABEL": state["label"],
        "ESTADO_TONE": state["tone"],
        "TOTAL": float(row["TOTAL"] or 0),
    }
    item["DTINICIO"] = _datetime_local_iso(item["DATA"], item["HORAINI"])
    item["DTFIM"] = _datetime_local_iso(item["DATA"], item["HORAFIM"])
    return item


def get_sheet(stamp: str) -> dict[str, Any]:
    feid = _current_feid()
    row = db.session.execute(
        text(
            """
            SELECT
                F.OFICINA_FOLHASTAMP,
                F.NO,
                F.VASTAMP,
                F.MATRICULA,
                F.OFICINA_TRABSTAMP,
                ISNULL(T.CODIGO, '') AS TRAB_CODIGO,
                ISNULL(T.DESCRICAO, '') AS TRAB_DESCRICAO,
                F.TRABALHO,
                F.DATA,
                F.HORAINI,
                F.HORAFIM,
                F.TEMPO,
                F.OFICINA_MECSTAMP,
                ISNULL(M.NOME, '') AS MECANICO,
                ISNULL(M.COR, '') AS MECANICO_COR,
                F.PLAN_DATA,
                F.PLAN_HORAINI,
                F.PLAN_HORAFIM,
                F.ESTADO,
                F.OBS,
                F.TOTAL,
                ISNULL(V.MARCA, '') AS MARCA,
                ISNULL(V.MODELO, '') AS MODELO,
                ISNULL(V.NOFROTA, '') AS NOFROTA
            FROM dbo.OFICINA_FOLHA F
            LEFT JOIN dbo.OFICINA_TRAB T
              ON T.OFICINA_TRABSTAMP = F.OFICINA_TRABSTAMP
            LEFT JOIN dbo.OFICINA_MEC M
              ON M.OFICINA_MECSTAMP = F.OFICINA_MECSTAMP
            LEFT JOIN dbo.VA V
              ON V.VASTAMP = F.VASTAMP
            WHERE F.OFICINA_FOLHASTAMP = :stamp
              AND F.FEID = :feid
            """
        ),
        {"stamp": _text(stamp, 25), "feid": feid},
    ).mappings().first()
    if not row:
        raise WorkshopNotFoundError("Folha de obra não encontrada.")
    sheet = _sheet_row(row)
    sheet["OBS"] = _text(row["OBS"])
    sheet["lines"] = _sheet_lines(sheet["OFICINA_FOLHASTAMP"])
    return {"sheet": sheet}


def list_planning_week(args: dict[str, Any]) -> dict[str, Any]:
    ensure_schema_available()
    feid = _current_feid()
    start = _week_start(args.get("week") or args.get("date"))
    end = start + timedelta(days=6)
    mechanic_stamp = _mechanic_stamp(args.get("mecanico") or args.get("mechanic"), allow_empty=True)
    params = {"feid": feid, "week_start": start, "week_end": end, "mechanic": mechanic_stamp}
    mechanic_planned_filter = "AND (:mechanic IS NULL OR F.OFICINA_MECSTAMP = :mechanic)"
    mechanic_unplanned_filter = "AND (:mechanic IS NULL OR F.OFICINA_MECSTAMP IS NULL OR F.OFICINA_MECSTAMP = :mechanic)"

    select_sql = """
        F.OFICINA_FOLHASTAMP,
        F.NO,
        F.VASTAMP,
        F.MATRICULA,
        F.OFICINA_TRABSTAMP,
        ISNULL(T.CODIGO, '') AS TRAB_CODIGO,
        ISNULL(T.DESCRICAO, '') AS TRAB_DESCRICAO,
        F.TRABALHO,
        F.DATA,
        F.HORAINI,
        F.HORAFIM,
        F.TEMPO,
        F.OFICINA_MECSTAMP,
        ISNULL(M.NOME, '') AS MECANICO,
        ISNULL(M.COR, '') AS MECANICO_COR,
        F.PLAN_DATA,
        F.PLAN_HORAINI,
        F.PLAN_HORAFIM,
        F.ESTADO,
        F.TOTAL,
        ISNULL(V.MARCA, '') AS MARCA,
        ISNULL(V.MODELO, '') AS MODELO,
        ISNULL(V.NOFROTA, '') AS NOFROTA
    """
    from_sql = """
        FROM dbo.OFICINA_FOLHA F
        LEFT JOIN dbo.OFICINA_TRAB T
          ON T.OFICINA_TRABSTAMP = F.OFICINA_TRABSTAMP
        LEFT JOIN dbo.OFICINA_MEC M
          ON M.OFICINA_MECSTAMP = F.OFICINA_MECSTAMP
        LEFT JOIN dbo.VA V
          ON V.VASTAMP = F.VASTAMP
    """
    planned_rows = db.session.execute(
        text(
            f"""
            SELECT TOP 500 {select_sql}
            {from_sql}
            WHERE F.FEID = :feid
              AND F.ESTADO <> 'ANULADA'
              AND F.PLAN_DATA >= :week_start
              AND F.PLAN_DATA <= :week_end
              AND LTRIM(RTRIM(ISNULL(F.PLAN_HORAINI, ''))) <> ''
              {mechanic_planned_filter}
            ORDER BY F.PLAN_DATA, F.PLAN_HORAINI, F.NO
            """
        ),
        params,
    ).mappings().all()
    unplanned_rows = db.session.execute(
        text(
            f"""
            SELECT TOP 500 {select_sql}
            {from_sql}
            WHERE F.FEID = :feid
              AND F.ESTADO <> 'ANULADA'
              AND (F.PLAN_DATA IS NULL OR LTRIM(RTRIM(ISNULL(F.PLAN_HORAINI, ''))) = '')
              {mechanic_unplanned_filter}
            ORDER BY F.NO DESC
            """
        ),
        params,
    ).mappings().all()
    days = []
    for offset in range(7):
        current = start + timedelta(days=offset)
        days.append(
            {
                "date": current.isoformat(),
                "label": current.strftime("%d/%m"),
                "weekday": ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"][offset],
                "weekend": offset >= 5,
            }
        )
    return {
        "week": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "previous": (start - timedelta(days=7)).isoformat(),
            "next": (start + timedelta(days=7)).isoformat(),
        },
        "days": days,
        "dayStart": "08:00",
        "dayEnd": "20:00",
        "slotMinutes": PLANNING_SLOT_MINUTES,
        "mechanic": mechanic_stamp or "",
        "mechanics": list_mechanics(),
        "unplanned": [_planning_row(row) for row in unplanned_rows],
        "planned": [_planning_row(row) for row in planned_rows],
    }


def _planning_row(row: Any) -> dict[str, Any]:
    item = _sheet_row(row)
    planned_start = item["PLAN_HORAINI"]
    planned_end = item["PLAN_HORAFIM"]
    tempo = max(0, int(item.get("TEMPO") or 0))
    if planned_start and not planned_end and tempo > 0:
        planned_end = _time_from_minutes(_minutes_from_time(planned_start) + tempo)
        item["PLAN_HORAFIM"] = planned_end
    item["PLANNED_START_MINUTES"] = _minutes_from_time(planned_start) if planned_start else None
    item["PLANNED_END_MINUTES"] = _minutes_from_time(planned_end) if planned_end else None
    return item


def _next_free_mechanic_start(
    *,
    feid: int,
    stamp: str,
    mechanic_stamp: str | None,
    plan_data: date,
    start_minutes: int,
    duration_minutes: int,
) -> int:
    if not mechanic_stamp:
        return start_minutes
    rows = db.session.execute(
        text(
            """
            SELECT
                PLAN_HORAINI,
                PLAN_HORAFIM,
                ISNULL(TEMPO, 0) AS TEMPO
            FROM dbo.OFICINA_FOLHA
            WHERE FEID = :feid
              AND OFICINA_FOLHASTAMP <> :stamp
              AND ESTADO <> 'ANULADA'
              AND OFICINA_MECSTAMP = :mechanic
              AND PLAN_DATA = :plan_data
              AND LTRIM(RTRIM(ISNULL(PLAN_HORAINI, ''))) <> ''
            ORDER BY PLAN_HORAINI
            """
        ),
        {
            "feid": feid,
            "stamp": _text(stamp, 25),
            "mechanic": mechanic_stamp,
            "plan_data": plan_data,
        },
    ).mappings().all()
    intervals: list[tuple[int, int]] = []
    for row in rows:
        other_start = _minutes_from_time(_text(row["PLAN_HORAINI"], 5))
        other_end_text = _text(row["PLAN_HORAFIM"], 5)
        other_end = _minutes_from_time(other_end_text) if other_end_text else other_start + int(row["TEMPO"] or 0)
        if other_end > other_start:
            intervals.append((other_start, other_end))

    candidate = start_minutes
    while True:
        candidate_end = candidate + duration_minutes
        moved = False
        for other_start, other_end in intervals:
            if candidate < other_end and candidate_end > other_start:
                candidate = other_end
                moved = True
                break
        if not moved:
            return candidate


def plan_sheet(stamp: str, payload: dict[str, Any], user_login: str = "") -> dict[str, Any]:
    ensure_schema_available()
    feid = _current_feid()
    plan_data = _date_value(payload.get("PLAN_DATA"), required=True, label="Data planeada")
    plan_horaini = _time_value(payload.get("PLAN_HORAINI"), required=True, label="Hora planeada de início")
    start_minutes = _minutes_from_time(plan_horaini)
    if start_minutes < PLANNING_DAY_START_MINUTES or start_minutes >= PLANNING_DAY_END_MINUTES:
        raise WorkshopValidationError("Hora planeada fora do horário 08:00-20:00.")

    row = db.session.execute(
        text(
            """
            SELECT TOP 1
                ISNULL(TEMPO, 0) AS TEMPO,
                OFICINA_MECSTAMP
            FROM dbo.OFICINA_FOLHA
            WHERE OFICINA_FOLHASTAMP = :stamp
              AND FEID = :feid
              AND ESTADO <> 'ANULADA'
            """
        ),
        {"stamp": _text(stamp, 25), "feid": feid},
    ).mappings().first()
    if not row:
        raise WorkshopNotFoundError("Folha de obra não encontrada.")
    tempo = int(row["TEMPO"] or 0)
    if tempo <= 0:
        raise WorkshopValidationError("Define o TEMPO em minutos antes de planear.")
    mechanic_supplied = "OFICINA_MECSTAMP" in payload or "MECANICO" in payload
    mechanic_stamp = (
        _mechanic_stamp(payload.get("OFICINA_MECSTAMP") or payload.get("MECANICO"), allow_empty=True)
        if mechanic_supplied
        else _text(row["OFICINA_MECSTAMP"], 25) or None
    )
    start_minutes = _next_free_mechanic_start(
        feid=feid,
        stamp=stamp,
        mechanic_stamp=mechanic_stamp,
        plan_data=plan_data,
        start_minutes=start_minutes,
        duration_minutes=tempo,
    )
    end_minutes = start_minutes + tempo
    if end_minutes > PLANNING_DAY_END_MINUTES:
        raise WorkshopValidationError("O trabalho ultrapassa as 20:00 no próximo espaço livre do mecânico.")
    plan_horaini = _time_from_minutes(start_minutes)
    plan_horafim = _time_from_minutes(end_minutes)
    mechanic_set_sql = "OFICINA_MECSTAMP = :mechanic," if mechanic_supplied else ""
    result = db.session.execute(
        text(
            f"""
            UPDATE dbo.OFICINA_FOLHA
               SET PLAN_DATA = :plan_data,
                   PLAN_HORAINI = :plan_horaini,
                   PLAN_HORAFIM = :plan_horafim,
                   {mechanic_set_sql}
                   DTALT = SYSDATETIME(),
                   USERALTERACAO = :user
             WHERE OFICINA_FOLHASTAMP = :stamp
               AND FEID = :feid
               AND ESTADO <> 'ANULADA'
            """
        ),
        {
            "stamp": _text(stamp, 25),
            "feid": feid,
            "plan_data": plan_data,
            "plan_horaini": plan_horaini,
            "plan_horafim": plan_horafim,
            "mechanic": mechanic_stamp,
            "user": _text(user_login, 60),
        },
    )
    if result.rowcount == 0:
        raise WorkshopNotFoundError("Folha de obra não encontrada.")
    db.session.commit()
    return get_sheet(stamp)


def assign_sheet_mechanic(stamp: str, payload: dict[str, Any], user_login: str = "") -> dict[str, Any]:
    ensure_schema_available()
    feid = _current_feid()
    mechanic_stamp = _mechanic_stamp(payload.get("OFICINA_MECSTAMP") or payload.get("MECANICO"), allow_empty=True)
    current = db.session.execute(
        text(
            """
            SELECT TOP 1
                PLAN_DATA,
                PLAN_HORAINI,
                ISNULL(TEMPO, 0) AS TEMPO
            FROM dbo.OFICINA_FOLHA
            WHERE OFICINA_FOLHASTAMP = :stamp
              AND FEID = :feid
              AND ESTADO <> 'ANULADA'
            """
        ),
        {"stamp": _text(stamp, 25), "feid": feid},
    ).mappings().first()
    if not current:
        raise WorkshopNotFoundError("Folha de obra não encontrada.")

    plan_set_sql = ""
    params: dict[str, Any] = {
        "stamp": _text(stamp, 25),
        "feid": feid,
        "mechanic": mechanic_stamp,
        "user": _text(user_login, 60),
    }
    if mechanic_stamp and current["PLAN_DATA"] and _text(current["PLAN_HORAINI"]):
        tempo = int(current["TEMPO"] or 0)
        if tempo > 0:
            start_minutes = _next_free_mechanic_start(
                feid=feid,
                stamp=stamp,
                mechanic_stamp=mechanic_stamp,
                plan_data=current["PLAN_DATA"],
                start_minutes=_minutes_from_time(_text(current["PLAN_HORAINI"], 5)),
                duration_minutes=tempo,
            )
            end_minutes = start_minutes + tempo
            if end_minutes > PLANNING_DAY_END_MINUTES:
                raise WorkshopValidationError("O trabalho ultrapassa as 20:00 no próximo espaço livre do mecânico.")
            plan_set_sql = """
                   PLAN_HORAINI = :plan_horaini,
                   PLAN_HORAFIM = :plan_horafim,"""
            params["plan_horaini"] = _time_from_minutes(start_minutes)
            params["plan_horafim"] = _time_from_minutes(end_minutes)

    result = db.session.execute(
        text(
            f"""
            UPDATE dbo.OFICINA_FOLHA
               SET OFICINA_MECSTAMP = :mechanic,
                   {plan_set_sql}
                   DTALT = SYSDATETIME(),
                   USERALTERACAO = :user
             WHERE OFICINA_FOLHASTAMP = :stamp
               AND FEID = :feid
               AND ESTADO <> 'ANULADA'
            """
        ),
        params,
    )
    if result.rowcount == 0:
        raise WorkshopNotFoundError("Folha de obra não encontrada.")
    db.session.commit()
    return get_sheet(stamp)


def unplan_sheet(stamp: str, user_login: str = "") -> dict[str, Any]:
    ensure_schema_available()
    feid = _current_feid()
    result = db.session.execute(
        text(
            """
            UPDATE dbo.OFICINA_FOLHA
               SET PLAN_DATA = NULL,
                   PLAN_HORAINI = '',
                   PLAN_HORAFIM = '',
                   DTALT = SYSDATETIME(),
                   USERALTERACAO = :user
             WHERE OFICINA_FOLHASTAMP = :stamp
               AND FEID = :feid
               AND ESTADO <> 'ANULADA'
            """
        ),
        {
            "stamp": _text(stamp, 25),
            "feid": feid,
            "user": _text(user_login, 60),
        },
    )
    if result.rowcount == 0:
        raise WorkshopNotFoundError("Folha de obra não encontrada.")
    db.session.commit()
    return get_sheet(stamp)


def _sheet_lines(sheet_stamp: str) -> list[dict[str, Any]]:
    rows = db.session.execute(
        text(
            """
            SELECT
                OFICINA_LINHASTAMP,
                OFICINA_FOLHASTAMP,
                ISNULL(ORDEM, 0) AS ORDEM,
                LTRIM(RTRIM(ISNULL(STSTAMP, ''))) AS STSTAMP,
                LTRIM(RTRIM(ISNULL(REF, ''))) AS REF,
                LTRIM(RTRIM(ISNULL(DESIGN, ''))) AS DESIGN,
                LTRIM(RTRIM(ISNULL(UNIDADE, ''))) AS UNIDADE,
                QTT,
                PUNIT,
                TOTAL,
                OBS
            FROM dbo.OFICINA_LINHA
            WHERE OFICINA_FOLHASTAMP = :sheet_stamp
            ORDER BY ISNULL(ORDEM, 0), OFICINA_LINHASTAMP
            """
        ),
        {"sheet_stamp": sheet_stamp},
    ).mappings().all()
    return [
        {
            "OFICINA_LINHASTAMP": _text(row["OFICINA_LINHASTAMP"]),
            "OFICINA_FOLHASTAMP": _text(row["OFICINA_FOLHASTAMP"]),
            "ORDEM": int(row["ORDEM"] or 0),
            "STSTAMP": _text(row["STSTAMP"]),
            "REF": _text(row["REF"]),
            "DESIGN": _text(row["DESIGN"]),
            "UNIDADE": _text(row["UNIDADE"]),
            "QTT": float(row["QTT"] or 0),
            "PUNIT": float(row["PUNIT"] or 0),
            "TOTAL": float(row["TOTAL"] or 0),
            "OBS": _text(row["OBS"]),
        }
        for row in rows
    ]


def save_sheet(payload: dict[str, Any], user_login: str = "", stamp: str = "") -> dict[str, Any]:
    ensure_schema_available()
    feid = _current_feid()
    target_stamp = _text(stamp or payload.get("OFICINA_FOLHASTAMP"), 25)
    vehicle = _vehicle_by_stamp_or_plate(payload.get("VASTAMP"), payload.get("MATRICULA"))
    work_stamp = _text(payload.get("OFICINA_TRABSTAMP"), 25)
    trabalho = _text(payload.get("TRABALHO"), 1000)
    if work_stamp:
        work = get_work_type(work_stamp)
        if not trabalho:
            trabalho = work["DESCRICAO"]
    if not trabalho:
        raise WorkshopValidationError("Trabalho a executar obrigatório.")

    legacy_start = _text(payload.get("DTINICIO"))
    legacy_end = _text(payload.get("DTFIM"))
    data_value = _date_value(payload.get("DATA") or legacy_start[:10], required=True)
    horaini = _time_value(
        payload.get("HORAINI") or (legacy_start[11:16] if len(legacy_start) >= 16 else ""),
        label="Hora de início",
    )
    horafim = _time_value(
        payload.get("HORAFIM") or (legacy_end[11:16] if len(legacy_end) >= 16 else ""),
        label="Hora de fim",
    )
    if horafim and not horaini:
        raise WorkshopValidationError("Hora de início obrigatória quando existe hora de fim.")
    if horafim and horafim < horaini:
        raise WorkshopValidationError("Hora de fim não pode ser anterior à hora de início.")
    tempo = _int_value(payload.get("TEMPO"), default=0, minimum=0, label="Tempo")
    plan_data = _date_value(payload.get("PLAN_DATA"), label="Data planeada")
    plan_horaini = _time_value(payload.get("PLAN_HORAINI"), label="Hora planeada de início")
    plan_horafim = _time_value(payload.get("PLAN_HORAFIM"), label="Hora planeada de fim")
    if plan_horafim and not plan_horaini:
        raise WorkshopValidationError("Hora planeada de início obrigatória quando existe hora planeada de fim.")
    if plan_horafim and plan_horaini and plan_horafim < plan_horaini:
        raise WorkshopValidationError("Hora planeada de fim não pode ser anterior ao início.")
    mechanic_stamp = _mechanic_stamp(payload.get("OFICINA_MECSTAMP") or payload.get("MECANICO"), allow_empty=True)

    estado = _text(payload.get("ESTADO") or "ABERTA").upper()
    if estado not in WORKSHOP_STATE_CODES:
        raise WorkshopValidationError("Estado da folha inválido.")

    lines, total = _normalize_lines(payload.get("lines") or payload.get("LINHAS") or [])
    user = _text(user_login, 60)
    params = {
        "stamp": target_stamp or _new_stamp(),
        "feid": feid,
        "vastamp": vehicle["VASTAMP"],
        "matricula": vehicle["MATRICULA"],
        "work_stamp": work_stamp or None,
        "trabalho": trabalho,
        "data": data_value,
        "horaini": horaini,
        "horafim": horafim,
        "tempo": tempo,
        "mechanic": mechanic_stamp,
        "plan_data": plan_data,
        "plan_horaini": plan_horaini,
        "plan_horafim": plan_horafim,
        "dtinicio": _legacy_dt(data_value, horaini),
        "dtfim": _legacy_dt(data_value, horafim),
        "estado": estado,
        "obs": _text(payload.get("OBS"), 4000),
        "total": total,
        "user": user,
    }
    has_legacy_dates = _table_column_exists("OFICINA_FOLHA", "DTINICIO") and _table_column_exists(
        "OFICINA_FOLHA", "DTFIM"
    )

    if target_stamp:
        legacy_set = ""
        if has_legacy_dates:
            legacy_set = """
                       DTINICIO = :dtinicio,
                       DTFIM = :dtfim,"""
        result = db.session.execute(
            text(
                f"""
                UPDATE dbo.OFICINA_FOLHA
                   SET VASTAMP = :vastamp,
                       MATRICULA = :matricula,
                       OFICINA_TRABSTAMP = :work_stamp,
                       TRABALHO = :trabalho,
                       DATA = :data,
                       HORAINI = :horaini,
                       HORAFIM = :horafim,{legacy_set}
                       TEMPO = :tempo,
                       OFICINA_MECSTAMP = :mechanic,
                       PLAN_DATA = :plan_data,
                       PLAN_HORAINI = :plan_horaini,
                       PLAN_HORAFIM = :plan_horafim,
                       ESTADO = :estado,
                       OBS = :obs,
                       TOTAL = :total,
                       DTALT = SYSDATETIME(),
                       USERALTERACAO = :user
                 WHERE OFICINA_FOLHASTAMP = :stamp
                   AND FEID = :feid
                """
            ),
            params,
        )
        if result.rowcount == 0:
            raise WorkshopNotFoundError("Folha de obra não encontrada.")
        db.session.execute(
            text("DELETE FROM dbo.OFICINA_LINHA WHERE OFICINA_FOLHASTAMP = :stamp"),
            {"stamp": params["stamp"]},
        )
    else:
        params["no"] = _next_no(feid)
        legacy_columns = ", DTINICIO, DTFIM" if has_legacy_dates else ""
        legacy_values = ", :dtinicio, :dtfim" if has_legacy_dates else ""
        db.session.execute(
            text(
                f"""
                INSERT INTO dbo.OFICINA_FOLHA
                    (OFICINA_FOLHASTAMP, FEID, NO, VASTAMP, MATRICULA, OFICINA_TRABSTAMP,
                     TRABALHO, DATA, HORAINI, HORAFIM, TEMPO, OFICINA_MECSTAMP, PLAN_DATA, PLAN_HORAINI, PLAN_HORAFIM{legacy_columns},
                     ESTADO, OBS, TOTAL, USERCRIACAO, USERALTERACAO)
                VALUES
                    (:stamp, :feid, :no, :vastamp, :matricula, :work_stamp,
                     :trabalho, :data, :horaini, :horafim, :tempo, :mechanic, :plan_data, :plan_horaini, :plan_horafim{legacy_values},
                     :estado, :obs, :total, :user, :user)
                """
            ),
            params,
        )

    _insert_lines(params["stamp"], lines)
    db.session.commit()
    return get_sheet(params["stamp"])


def _normalize_lines(raw_lines: Any) -> tuple[list[dict[str, Any]], Decimal]:
    if not isinstance(raw_lines, list):
        raise WorkshopValidationError("Linhas inválidas.")
    lines: list[dict[str, Any]] = []
    total = Decimal("0")
    for idx, raw in enumerate(raw_lines, start=1):
        if not isinstance(raw, dict):
            continue
        ref = _text(raw.get("REF"), 18)
        design = _text(raw.get("DESIGN"), 120)
        ststamp = _text(raw.get("STSTAMP"), 25)
        if not ref and not design and not ststamp:
            continue
        qtt = _qty(_decimal(raw.get("QTT")))
        punit = _money(_decimal(raw.get("PUNIT")))
        if qtt <= 0:
            raise WorkshopValidationError(f"Quantidade inválida na linha {idx}.")
        if punit < 0:
            raise WorkshopValidationError(f"Preço unitário inválido na linha {idx}.")
        if not ref:
            raise WorkshopValidationError(f"Referência obrigatória na linha {idx}.")
        if not design:
            raise WorkshopValidationError(f"Descrição obrigatória na linha {idx}.")
        line_total = _money(qtt * punit)
        total += line_total
        lines.append(
            {
                "stamp": _new_stamp(),
                "ordem": idx,
                "ststamp": ststamp or None,
                "ref": ref,
                "design": design,
                "unidade": _text(raw.get("UNIDADE"), 10),
                "qtt": qtt,
                "punit": punit,
                "total": line_total,
                "obs": _text(raw.get("OBS"), 500),
            }
        )
    return lines, _money(total)


def _insert_lines(sheet_stamp: str, lines: list[dict[str, Any]]) -> None:
    if not lines:
        return
    db.session.execute(
        text(
            """
            INSERT INTO dbo.OFICINA_LINHA
                (OFICINA_LINHASTAMP, OFICINA_FOLHASTAMP, ORDEM, STSTAMP, REF, DESIGN,
                 UNIDADE, QTT, PUNIT, TOTAL, OBS)
            VALUES
                (:stamp, :sheet_stamp, :ordem, :ststamp, :ref, :design,
                 :unidade, :qtt, :punit, :total, :obs)
            """
        ),
        [{**line, "sheet_stamp": sheet_stamp} for line in lines],
    )


def annul_sheet(stamp: str, user_login: str = "") -> dict[str, Any]:
    feid = _current_feid()
    result = db.session.execute(
        text(
            """
            UPDATE dbo.OFICINA_FOLHA
               SET ESTADO = 'ANULADA',
                   DTALT = SYSDATETIME(),
                   USERALTERACAO = :user
             WHERE OFICINA_FOLHASTAMP = :stamp
               AND FEID = :feid
            """
        ),
        {"stamp": _text(stamp, 25), "feid": feid, "user": _text(user_login, 60)},
    )
    if result.rowcount == 0:
        raise WorkshopNotFoundError("Folha de obra não encontrada.")
    db.session.commit()
    return get_sheet(stamp)
