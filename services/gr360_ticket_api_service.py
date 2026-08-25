from __future__ import annotations

import hashlib
import hmac
import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Mapping

from sqlalchemy import text


VALID_PRIORITIES = {"BAIXA": "Baixa", "NORMAL": "Normal", "ALTA": "Alta", "URGENTE": "Urgente"}
MAX_PROMPT_LENGTH = 100_000
MAX_FOLLOWUP_LENGTH = 100_000


class TicketApiError(RuntimeError):
    status_code = 400


class TicketApiUnauthorized(TicketApiError):
    status_code = 401


class TicketApiForbidden(TicketApiError):
    status_code = 403


class TicketApiNotFound(TicketApiError):
    status_code = 404


class TicketApiConfigurationError(TicketApiError):
    status_code = 503


@dataclass(frozen=True)
class TicketApiClient:
    client_id: str
    name: str
    can_create: bool
    can_read: bool
    can_read_all: bool
    can_update: bool = False


def clean_text(value: Any, max_length: int | None = None) -> str:
    result = str(value or "").strip()
    if max_length is not None:
        result = result[:max_length]
    return result


def normalize_spaces(value: Any) -> str:
    return re.sub(r"\s+", " ", clean_text(value)).strip()


def token_hash(token: str) -> str:
    return hashlib.sha256(clean_text(token).encode("utf-8")).hexdigest()


def extract_bearer_token(authorization: str | None) -> str:
    value = clean_text(authorization)
    if not value.lower().startswith("bearer "):
        return ""
    return value[7:].strip()


def normalize_priority(value: Any) -> str:
    key = clean_text(value or "Normal").upper()
    if key not in VALID_PRIORITIES:
        raise TicketApiError("Prioridade inválida. Usa Baixa, Normal, Alta ou Urgente.")
    return VALID_PRIORITIES[key]


def validate_create_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise TicketApiError("O corpo do pedido deve ser um objeto JSON.")

    pedido = normalize_spaces(payload.get("pedido"))[:100]
    prompt = clean_text(payload.get("prompt_hugo") or payload.get("prompt"))
    if not pedido:
        raise TicketApiError("O campo pedido é obrigatório.")
    if not prompt:
        raise TicketApiError("O campo prompt_hugo é obrigatório.")
    if len(prompt) > MAX_PROMPT_LENGTH:
        raise TicketApiError(f"O prompt excede o limite de {MAX_PROMPT_LENGTH} caracteres.")

    description = normalize_spaces(payload.get("descricao"))
    if not description:
        description = normalize_spaces(prompt)

    return {
        "pedido": pedido,
        "descricao": description[:250],
        "prompt_hugo": prompt,
        "prioridade": normalize_priority(payload.get("prioridade")),
        "utilizador": normalize_spaces(payload.get("utilizador"))[:50],
        "referencia_externa": clean_text(payload.get("referencia_externa"), 100) or None,
    }


def validate_followup_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise TicketApiError("O corpo do pedido deve ser um objeto JSON.")

    state = normalize_spaces(payload.get("estado"))[:30]
    followup = clean_text(payload.get("seguimento"))
    if not state:
        raise TicketApiError("O campo estado é obrigatório.")
    if not followup:
        raise TicketApiError("O campo seguimento é obrigatório.")
    if len(followup) > MAX_FOLLOWUP_LENGTH:
        raise TicketApiError(f"O seguimento excede o limite de {MAX_FOLLOWUP_LENGTH} caracteres.")

    treated = payload.get("tratado", False)
    if not isinstance(treated, bool):
        raise TicketApiError("O campo tratado deve ser true ou false.")
    return {"estado": state, "seguimento": followup, "tratado": treated}


def _new_stamp() -> str:
    return str(uuid.uuid4()).upper()[:25]


def _json_value(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def serialize_ticket(row: Mapping[str, Any], include_prompt: bool = True) -> dict[str, Any]:
    result = {
        "ticket": int(row.get("TICKET") or 0),
        "data": _json_value(row.get("DATA")),
        "utilizador": clean_text(row.get("UTILIZADOR")),
        "pedido": clean_text(row.get("PEDIDO")),
        "descricao": clean_text(row.get("DESCRICAO")),
        "prioridade": clean_text(row.get("PRIORIDADE")),
        "feid": row.get("FEID"),
        "tratado": bool(row.get("TRATADO")),
        "data_tratado": _json_value(row.get("DTTRATADO")),
        "seguimento_estado": clean_text(row.get("SEGUIMENTO_ESTADO")) or None,
        "seguimento_cliente": clean_text(row.get("SEGUIMENTO_CLIENTE")) or None,
        "seguimento_data": _json_value(row.get("SEGUIMENTO_DATA")),
        "seguimento_por": clean_text(row.get("SEGUIMENTO_POR")) or None,
        "origem_api": clean_text(row.get("ORIGEM_API")) or None,
        "referencia_externa": clean_text(row.get("REFERENCIA_EXTERNA")) or None,
    }
    if include_prompt:
        result["prompt_hugo"] = clean_text(row.get("PROMPT_HUGO"))
    return result


def ensure_gr360_database(connection, expected_database: str = "GR360_CORE") -> None:
    database_name = clean_text(connection.execute(text("SELECT DB_NAME() AS DB_NAME")).scalar()).upper()
    expected = clean_text(expected_database or "GR360_CORE").upper()
    if not expected or database_name != expected:
        raise TicketApiConfigurationError("API de tickets indisponível neste contexto de base de dados.")


def authenticate_client(engine, raw_token: str, expected_database: str = "GR360_CORE") -> TicketApiClient:
    token = clean_text(raw_token)
    if not token:
        raise TicketApiUnauthorized("Credencial Bearer em falta.")

    digest = token_hash(token)
    with engine.begin() as connection:
        ensure_gr360_database(connection, expected_database)
        rows = connection.execute(text("""
            SELECT CLIENT_ID, NOME, TOKEN_HASH, PODE_CRIAR, PODE_LER,
                   PODE_LER_TODOS, PODE_ATUALIZAR
            FROM dbo.GR_TICKET_API_CLIENT
            WHERE ATIVO = 1
        """)).mappings().all()
        matched = None
        for row in rows:
            if hmac.compare_digest(clean_text(row.get("TOKEN_HASH")).lower(), digest.lower()):
                matched = row
                break
        if not matched:
            raise TicketApiUnauthorized("Credencial inválida.")
        connection.execute(text("""
            UPDATE dbo.GR_TICKET_API_CLIENT
            SET ULTIMO_USO_UTC = SYSUTCDATETIME()
            WHERE CLIENT_ID = :client_id
        """), {"client_id": matched["CLIENT_ID"]})

    return TicketApiClient(
        client_id=clean_text(matched.get("CLIENT_ID"), 50),
        name=clean_text(matched.get("NOME"), 100),
        can_create=bool(matched.get("PODE_CRIAR")),
        can_read=bool(matched.get("PODE_LER")),
        can_read_all=bool(matched.get("PODE_LER_TODOS")),
        can_update=bool(matched.get("PODE_ATUALIZAR")),
    )


def create_ticket(
    engine,
    client: TicketApiClient,
    payload: Any,
    expected_database: str = "GR360_CORE",
    ticket_feid: int = 1,
) -> tuple[dict[str, Any], bool]:
    if not client.can_create:
        raise TicketApiForbidden("Esta credencial não pode criar tickets.")
    values = validate_create_payload(payload)
    reporter = values["utilizador"] or client.name or client.client_id
    try:
        fixed_feid = int(ticket_feid)
    except (TypeError, ValueError) as exc:
        raise TicketApiConfigurationError("FEID fixo da API de tickets inválido.") from exc
    if fixed_feid <= 0:
        raise TicketApiConfigurationError("FEID fixo da API de tickets inválido.")

    with engine.begin() as connection:
        ensure_gr360_database(connection, expected_database)
        if values["referencia_externa"]:
            existing = connection.execute(text("""
                SELECT TOP 1 *
                FROM dbo.TK
                WHERE ORIGEM_API = :client_id
                  AND REFERENCIA_EXTERNA = :external_reference
                ORDER BY TICKET DESC
            """), {
                "client_id": client.client_id,
                "external_reference": values["referencia_externa"],
            }).mappings().first()
            if existing:
                return serialize_ticket(existing), False

        stamp = _new_stamp()
        connection.execute(text("""
            INSERT INTO dbo.TK
            (
                TKSTAMP, DATA, UTILIZADOR, PEDIDO, DESCRICAO,
                TRATADO, DTTRATADO, NMTRATADO, PRIORIDADE, FEID,
                PROMPT_HUGO, SEGUIMENTO_CLIENTE, SEGUIMENTO_ESTADO,
                SEGUIMENTO_DATA, SEGUIMENTO_POR, ORIGEM_API, REFERENCIA_EXTERNA
            )
            VALUES
            (
                :stamp, CAST(SYSUTCDATETIME() AS date), :reporter, :pedido, :descricao,
                0, '19000101', '', :prioridade, :feid,
                :prompt_hugo, NULL, NULL,
                NULL, NULL, :client_id, :external_reference
            )
        """), {
            "stamp": stamp,
            "reporter": reporter,
            "pedido": values["pedido"],
            "descricao": values["descricao"],
            "prioridade": values["prioridade"],
            "feid": fixed_feid,
            "prompt_hugo": values["prompt_hugo"],
            "client_id": client.client_id,
            "external_reference": values["referencia_externa"],
        })
        row = connection.execute(text("SELECT TOP 1 * FROM dbo.TK WHERE TKSTAMP = :stamp"), {"stamp": stamp}).mappings().one()
    return serialize_ticket(row), True


def get_ticket(engine, client: TicketApiClient, ticket_no: int, expected_database: str = "GR360_CORE") -> dict[str, Any]:
    if not client.can_read:
        raise TicketApiForbidden("Esta credencial não pode consultar tickets.")
    with engine.connect() as connection:
        ensure_gr360_database(connection, expected_database)
        sql = "SELECT TOP 1 * FROM dbo.TK WHERE TICKET = :ticket"
        params: dict[str, Any] = {"ticket": ticket_no}
        if not client.can_read_all:
            sql += " AND ORIGEM_API = :client_id"
            params["client_id"] = client.client_id
        row = connection.execute(text(sql), params).mappings().first()
    if not row:
        raise TicketApiNotFound("Ticket não encontrado.")
    return serialize_ticket(row)


def list_tickets(
    engine,
    client: TicketApiClient,
    *,
    status: str = "all",
    limit: int = 50,
    expected_database: str = "GR360_CORE",
) -> list[dict[str, Any]]:
    if not client.can_read:
        raise TicketApiForbidden("Esta credencial não pode consultar tickets.")
    status_value = clean_text(status or "all").lower()
    if status_value not in {"all", "pending", "treated"}:
        raise TicketApiError("Estado inválido. Usa all, pending ou treated.")
    limit_value = max(1, min(int(limit or 50), 100))
    clauses = []
    params: dict[str, Any] = {"limit": limit_value}
    if not client.can_read_all:
        clauses.append("ORIGEM_API = :client_id")
        params["client_id"] = client.client_id
    if status_value == "pending":
        clauses.append("TRATADO = 0")
    elif status_value == "treated":
        clauses.append("TRATADO = 1")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with engine.connect() as connection:
        ensure_gr360_database(connection, expected_database)
        rows = connection.execute(text(f"""
            SELECT TOP (:limit) *
            FROM dbo.TK
            {where}
            ORDER BY TICKET DESC
        """), params).mappings().all()
    return [serialize_ticket(row, include_prompt=False) for row in rows]


def update_ticket_followup(
    engine,
    client: TicketApiClient,
    ticket_no: int,
    payload: Any,
    expected_database: str = "GR360_CORE",
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not client.can_update:
        raise TicketApiForbidden("Esta credencial não pode atualizar o seguimento de tickets.")
    values = validate_followup_payload(payload)

    with engine.begin() as connection:
        ensure_gr360_database(connection, expected_database)
        sql = "SELECT TOP 1 * FROM dbo.TK WITH (UPDLOCK, ROWLOCK) WHERE TICKET = :ticket"
        params: dict[str, Any] = {"ticket": int(ticket_no)}
        if not client.can_read_all:
            sql += " AND ORIGEM_API = :client_id"
            params["client_id"] = client.client_id
        before_row = connection.execute(text(sql), params).mappings().first()
        if not before_row:
            raise TicketApiNotFound("Ticket não encontrado.")

        treated_sql = """
            TRATADO = :treated,
            DTTRATADO = CASE WHEN :treated = 1 THEN CAST(SYSUTCDATETIME() AS date) ELSE '19000101' END,
            NMTRATADO = CASE WHEN :treated = 1 THEN :client_id ELSE '' END,
        """
        connection.execute(text(f"""
            UPDATE dbo.TK
            SET {treated_sql}
                SEGUIMENTO_CLIENTE = :followup,
                SEGUIMENTO_ESTADO = :state,
                SEGUIMENTO_DATA = SYSUTCDATETIME(),
                SEGUIMENTO_POR = :client_id
            WHERE TICKET = :ticket
        """), {
            "ticket": int(ticket_no),
            "treated": 1 if values["tratado"] else 0,
            "followup": values["seguimento"],
            "state": values["estado"],
            "client_id": client.client_id,
        })
        after_row = connection.execute(
            text("SELECT TOP 1 * FROM dbo.TK WHERE TICKET = :ticket"),
            {"ticket": int(ticket_no)},
        ).mappings().one()

    return serialize_ticket(before_row), serialize_ticket(after_row)
