from __future__ import annotations

import atexit
import asyncio
import logging
import threading
from contextlib import contextmanager
from typing import Any, Mapping

from a2wsgi import ASGIMiddleware
from flask import Flask
from mcp import types
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.mcpserver import Context
from mcp.server.transport_security import TransportSecuritySettings
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.middleware.dispatcher import DispatcherMiddleware

from models import db
from services.gr360_audit_service import audit_table_write
from services.gr360_ticket_api_service import (
    TicketApiClient,
    TicketApiError,
    authenticate_client,
    create_ticket,
    extract_bearer_token,
    get_ticket,
    list_tickets,
    update_ticket_followup,
)


logger = logging.getLogger(__name__)
MCP_MOUNT_PATH = "/mcp/gr360-tickets"


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "sim"}


def _authorization_header(ctx: Context) -> str:
    headers: Mapping[str, str] = ctx.headers or {}
    return str(headers.get("authorization") or headers.get("Authorization") or "")


@contextmanager
def _flask_operation_context(app: Flask, ctx: Context):
    headers = {"Authorization": _authorization_header(ctx)}
    with app.test_request_context(MCP_MOUNT_PATH, method="POST", headers=headers):
        yield


def _engine(app: Flask):
    if not _truthy(app.config.get("GR360_TICKET_API_ENABLED", "1")):
        raise RuntimeError("API de tickets GR360 desativada.")
    engine = db.engines.get("client")
    if engine is None:
        raise RuntimeError("Ligação GR360 indisponível.")
    return engine


def _expected_database(app: Flask) -> str:
    return str(app.config.get("GR360_TICKET_API_EXPECTED_DATABASE") or "GR360_CORE").strip()


def _ticket_feid(app: Flask) -> int:
    return int(app.config.get("GR360_TICKET_API_FEID") or 1)


def _client(app: Flask, ctx: Context) -> TicketApiClient:
    return authenticate_client(
        _engine(app),
        extract_bearer_token(_authorization_header(ctx)),
        _expected_database(app),
    )


def _run_tool(app: Flask, ctx: Context, operation):
    try:
        with _flask_operation_context(app, ctx):
            return operation()
    except TicketApiError as exc:
        raise ToolError(str(exc)) from exc
    except SQLAlchemyError as exc:
        app.logger.exception("Falha de base de dados no MCP de tickets GR360.")
        raise ToolError("Não foi possível aceder aos tickets neste momento.") from exc


def create_ticket_mcp_server(app: Flask) -> MCPServer:
    server = MCPServer(
        name="gr360-tickets",
        title="GR360 Tickets",
        description="Consulta, criação e seguimento controlado de tickets da aplicação GR360.",
        instructions=(
            "Usa estas ferramentas apenas para tickets GR360. Antes de criar, pesquisa tickets "
            "semelhantes. Mantém o prompt_hugo completo e uma referência externa estável. "
            "As ferramentas de escrita exigem confirmação do utilizador."
        ),
        version="1.0.0",
    )

    @server.tool(
        name="listar_tickets",
        title="Listar tickets GR360",
        description="Lista tickets GR360. Estado: all, pending ou treated; máximo 100 registos.",
        annotations=types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
        structured_output=True,
    )
    def listar_tickets_tool(estado: str = "all", limite: int = 50, ctx: Context = None) -> dict[str, Any]:
        def operation():
            client = _client(app, ctx)
            items = list_tickets(
                _engine(app),
                client,
                status=estado,
                limit=limite,
                expected_database=_expected_database(app),
            )
            return {"count": len(items), "items": items}

        return _run_tool(app, ctx, operation)

    @server.tool(
        name="consultar_ticket",
        title="Consultar ticket GR360",
        description="Consulta o conteúdo completo e o seguimento de um ticket GR360.",
        annotations=types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
        structured_output=True,
    )
    def consultar_ticket_tool(numero: int, ctx: Context = None) -> dict[str, Any]:
        return _run_tool(
            app,
            ctx,
            lambda: {"item": get_ticket(_engine(app), _client(app, ctx), numero, _expected_database(app))},
        )

    @server.tool(
        name="criar_ticket",
        title="Criar ticket GR360",
        description=(
            "Cria um ticket GR360 de forma idempotente. Requer título, prompt técnico completo "
            "e uma referência externa estável."
        ),
        annotations=types.ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
        structured_output=True,
    )
    def criar_ticket_tool(
        pedido: str,
        prompt_hugo: str,
        referencia_externa: str,
        descricao: str = "",
        prioridade: str = "Normal",
        utilizador: str = "",
        ctx: Context = None,
    ) -> dict[str, Any]:
        def operation():
            client = _client(app, ctx)
            item, created = create_ticket(
                _engine(app),
                client,
                {
                    "pedido": pedido,
                    "prompt_hugo": prompt_hugo,
                    "referencia_externa": referencia_externa,
                    "descricao": descricao,
                    "prioridade": prioridade,
                    "utilizador": utilizador,
                },
                _expected_database(app),
                _ticket_feid(app),
            )
            if created:
                audit_table_write(
                    table_name="TK",
                    action="INSERT",
                    record_key={"TICKET": item["ticket"]},
                    after_data=item,
                    metadata={"source": "gr360_ticket_mcp", "api_client": client.client_id},
                    database_name="GR360_CORE",
                )
            return {"created": created, "item": item}

        return _run_tool(app, ctx, operation)

    @server.tool(
        name="atualizar_seguimento",
        title="Atualizar seguimento de ticket GR360",
        description=(
            "Regista a validação ou seguimento do cliente num ticket. Não altera o pedido nem o "
            "prompt original. Só marca tratado quando tratado=true."
        ),
        annotations=types.ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
        structured_output=True,
    )
    def atualizar_seguimento_tool(
        numero: int,
        estado: str,
        seguimento: str,
        tratado: bool = False,
        ctx: Context = None,
    ) -> dict[str, Any]:
        def operation():
            client = _client(app, ctx)
            before, item = update_ticket_followup(
                _engine(app),
                client,
                numero,
                {"estado": estado, "seguimento": seguimento, "tratado": tratado},
                _expected_database(app),
            )
            audit_table_write(
                table_name="TK",
                action="UPDATE",
                record_key={"TICKET": item["ticket"]},
                before_data=before,
                after_data=item,
                metadata={"source": "gr360_ticket_mcp", "api_client": client.client_id},
                database_name="GR360_CORE",
            )
            return {"item": item}

        return _run_tool(app, ctx, operation)

    return server


class _McpWsgiMount:
    def __init__(self, asgi_app):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, name="gr360-ticket-mcp", daemon=True)
        self.thread.start()
        self.lifespan = asgi_app.router.lifespan_context(asgi_app)
        self.ready = threading.Event()
        self.stop_event = None
        self.lifespan_future = asyncio.run_coroutine_threadsafe(self._run_lifespan(), self.loop)
        if not self.ready.wait(timeout=15):
            raise RuntimeError("O MCP de tickets GR360 não iniciou dentro do tempo esperado.")
        if self.lifespan_future.done():
            self.lifespan_future.result()
        self.wsgi_app = ASGIMiddleware(asgi_app, loop=self.loop, wait_time=30)
        self.closed = False

    async def _run_lifespan(self):
        self.stop_event = asyncio.Event()
        async with self.lifespan:
            self.ready.set()
            await self.stop_event.wait()

    async def _cancel_pending_tasks(self):
        current = asyncio.current_task()
        pending = [task for task in asyncio.all_tasks() if task is not current and not task.done()]
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            self.loop.call_soon_threadsafe(self.stop_event.set)
            self.lifespan_future.result(timeout=15)
            asyncio.run_coroutine_threadsafe(self._cancel_pending_tasks(), self.loop).result(timeout=15)
        except Exception:
            logger.exception("Falha ao terminar o MCP de tickets GR360.")
        finally:
            self.loop.call_soon_threadsafe(self.loop.stop)


def mount_gr360_ticket_mcp(app: Flask) -> None:
    if not _truthy(app.config.get("GR360_TICKET_MCP_ENABLED", "1")):
        return
    if "gr360_ticket_mcp" in app.extensions:
        return

    server = create_ticket_mcp_server(app)
    host = str(app.config.get("GR360_TICKET_MCP_HOST") or "app.gr360flooringsystems.com").strip()
    asgi_app = server.streamable_http_app(
        streamable_http_path="/",
        json_response=True,
        stateless_http=True,
        host=host,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[
                host,
                f"{host}:*",
                "app.gr360flooringsystems.com",
                "app.gr360flooringsystems.com:*",
                "127.0.0.1",
                "127.0.0.1:*",
                "localhost",
                "localhost:*",
            ],
            allowed_origins=[
                "https://app.gr360flooringsystems.com",
                "http://127.0.0.1:*",
                "http://localhost:*",
            ],
        ),
    )
    mount = _McpWsgiMount(asgi_app)
    app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {MCP_MOUNT_PATH: mount.wsgi_app})
    app.extensions["gr360_ticket_mcp"] = {"server": server, "mount": mount}
    atexit.register(mount.close)
