from __future__ import annotations

import json
import logging
import os
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from mcp import types
from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings


logger = logging.getLogger(__name__)
DEFAULT_API_BASE_URL = "http://127.0.0.1:8001/api/gr360/tickets"
DEFAULT_PUBLIC_HOST = "app.gr360flooringsystems.com"


def _authorization_header(ctx: Context | None) -> str:
    headers: Mapping[str, str] = (ctx.headers if ctx else None) or {}
    return str(headers.get("authorization") or headers.get("Authorization") or "").strip()


def _decode_response(raw: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ToolError("A API GR360 devolveu uma resposta inválida.") from exc
    if not isinstance(payload, dict):
        raise ToolError("A API GR360 devolveu uma resposta inválida.")
    return payload


def _api_request(
    ctx: Context | None,
    method: str,
    path: str = "",
    *,
    query: Mapping[str, Any] | None = None,
    body: Mapping[str, Any] | None = None,
    api_base_url: str = DEFAULT_API_BASE_URL,
) -> dict[str, Any]:
    authorization = _authorization_header(ctx)
    if not authorization:
        raise ToolError("Credencial Bearer em falta.")

    url = f"{api_base_url.rstrip('/')}/{path.lstrip('/')}" if path else api_base_url.rstrip("/")
    if query:
        url = f"{url}?{urlencode(query)}"

    data = None
    headers = {"Authorization": authorization, "Accept": "application/json"}
    if body is not None:
        data = json.dumps(dict(body), ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urlopen(request, timeout=30) as response:
            payload = _decode_response(response.read())
    except HTTPError as exc:
        try:
            payload = _decode_response(exc.read())
            message = str(payload.get("error") or "")
        except ToolError:
            message = ""
        raise ToolError(message or f"A API GR360 recusou o pedido ({exc.code}).") from exc
    except (URLError, TimeoutError) as exc:
        logger.exception("API GR360 indisponível para o serviço MCP.")
        raise ToolError("A API de tickets GR360 está temporariamente indisponível.") from exc

    if payload.get("ok") is False:
        raise ToolError(str(payload.get("error") or "Não foi possível processar o pedido."))
    return payload


def create_ticket_mcp_server(api_base_url: str | None = None) -> MCPServer:
    base_url = str(api_base_url or os.environ.get("GR360_TICKET_MCP_API_URL") or DEFAULT_API_BASE_URL).strip()
    server = MCPServer(
        name="gr360-tickets",
        title="GR360 Tickets",
        description="Consulta, criação e seguimento controlado de tickets da aplicação GR360.",
        instructions=(
            "Usa estas ferramentas apenas para tickets GR360. Antes de criar, pesquisa tickets "
            "semelhantes. Mantém o prompt_hugo completo e uma referência externa estável. "
            "As ferramentas de escrita exigem confirmação do utilizador."
        ),
        version="1.1.0",
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
        return _api_request(
            ctx,
            "GET",
            query={"status": estado, "limit": limite},
            api_base_url=base_url,
        )

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
        return _api_request(ctx, "GET", str(numero), api_base_url=base_url)

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
        return _api_request(
            ctx,
            "POST",
            body={
                "pedido": pedido,
                "prompt_hugo": prompt_hugo,
                "referencia_externa": referencia_externa,
                "descricao": descricao,
                "prioridade": prioridade,
                "utilizador": utilizador,
            },
            api_base_url=base_url,
        )

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
        return _api_request(
            ctx,
            "PATCH",
            f"{numero}/followup",
            body={"estado": estado, "seguimento": seguimento, "tratado": tratado},
            api_base_url=base_url,
        )

    return server


def run_ticket_mcp_server() -> None:
    listen_host = str(os.environ.get("GR360_TICKET_MCP_LISTEN_HOST") or "127.0.0.1").strip()
    listen_port = int(os.environ.get("GR360_TICKET_MCP_PORT") or 8002)
    public_host = str(os.environ.get("GR360_TICKET_MCP_PUBLIC_HOST") or DEFAULT_PUBLIC_HOST).strip()
    server = create_ticket_mcp_server()
    server.run(
        transport="streamable-http",
        host=listen_host,
        port=listen_port,
        streamable_http_path="/",
        json_response=True,
        stateless_http=True,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[
                public_host,
                f"{public_host}:*",
                "127.0.0.1",
                "127.0.0.1:*",
                "localhost",
                "localhost:*",
            ],
            allowed_origins=[f"https://{public_host}"],
        ),
    )
