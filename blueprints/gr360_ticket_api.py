from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from models import db
from services.gr360_audit_service import audit_table_write
from services.gr360_ticket_api_service import (
    TicketApiConfigurationError,
    TicketApiError,
    authenticate_client,
    create_ticket,
    extract_bearer_token,
    get_ticket,
    list_tickets,
)


bp = Blueprint("gr360_ticket_api", __name__, url_prefix="/api/gr360/tickets")


def _enabled() -> bool:
    return str(current_app.config.get("GR360_TICKET_API_ENABLED", "1") or "").strip().lower() in {
        "1", "true", "yes", "on", "sim"
    }


def _engine():
    if not _enabled():
        raise TicketApiConfigurationError("API de tickets desativada.")
    engine = db.engines.get("client")
    if engine is None:
        raise TicketApiConfigurationError("Ligação GR360 indisponível.")
    return engine


def _expected_database() -> str:
    return str(current_app.config.get("GR360_TICKET_API_EXPECTED_DATABASE") or "GR360_CORE").strip()


def _client():
    return authenticate_client(
        _engine(),
        extract_bearer_token(request.headers.get("Authorization")),
        _expected_database(),
    )


@bp.errorhandler(TicketApiError)
def _ticket_api_error(exc):
    return jsonify({"ok": False, "error": str(exc)}), getattr(exc, "status_code", 400)


@bp.errorhandler(SQLAlchemyError)
def _ticket_api_database_error(exc):
    current_app.logger.exception("Falha de base de dados na API de tickets GR360.")
    return jsonify({"ok": False, "error": "Não foi possível processar o ticket neste momento."}), 503


@bp.get("")
def api_list_tickets():
    client = _client()
    try:
        limit = int(request.args.get("limit", 50))
    except (TypeError, ValueError):
        limit = 50
    items = list_tickets(
        _engine(),
        client,
        status=request.args.get("status", "all"),
        limit=limit,
        expected_database=_expected_database(),
    )
    return jsonify({"ok": True, "count": len(items), "items": items})


@bp.get("/<int:ticket_no>")
def api_get_ticket(ticket_no: int):
    item = get_ticket(_engine(), _client(), ticket_no, _expected_database())
    return jsonify({"ok": True, "item": item})


@bp.post("")
def api_create_ticket():
    client = _client()
    item, created = create_ticket(
        _engine(),
        client,
        request.get_json(silent=True),
        _expected_database(),
    )
    if created:
        audit_table_write(
            table_name="TK",
            action="INSERT",
            record_key={"TICKET": item["ticket"]},
            after_data=item,
            metadata={"source": "gr360_ticket_api", "api_client": client.client_id},
            database_name="GR360_CORE",
        )
    return jsonify({"ok": True, "created": created, "item": item}), (201 if created else 200)
