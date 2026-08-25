import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from mcp.server.transport_security import TransportSecuritySettings
from starlette.testclient import TestClient

from services.gr360_ticket_mcp import _api_request, create_ticket_mcp_server


class _FakeHttpResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class Gr360TicketMcpTests(unittest.TestCase):
    def setUp(self):
        server = create_ticket_mcp_server("http://127.0.0.1:8001/api/gr360/tickets")
        asgi_app = server.streamable_http_app(
            streamable_http_path="/",
            json_response=True,
            stateless_http=True,
            transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
        )
        self.client_context = TestClient(asgi_app)
        self.client = self.client_context.__enter__()
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }

    def tearDown(self):
        self.client_context.__exit__(None, None, None)

    def post_rpc(self, method, params=None, request_id=1):
        return self.client.post(
            "/",
            headers=self.headers,
            json={"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}},
        )

    def test_mcp_initializes_and_exposes_expected_tools(self):
        response = self.post_rpc("initialize", {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "unit-test", "version": "1"},
        })
        self.assertEqual(response.status_code, 200)

        response = self.post_rpc("tools/list", request_id=2)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        tools = {item["name"]: item for item in payload["result"]["tools"]}
        self.assertEqual(
            set(tools),
            {"listar_tickets", "consultar_ticket", "criar_ticket", "atualizar_seguimento"},
        )
        self.assertTrue(tools["listar_tickets"]["annotations"]["readOnlyHint"])
        self.assertFalse(tools["criar_ticket"]["annotations"]["readOnlyHint"])

    @patch("services.gr360_ticket_mcp.urlopen")
    def test_adapter_forwards_bearer_token_to_ticket_api(self, mocked_urlopen):
        mocked_urlopen.return_value = _FakeHttpResponse({"ok": True, "count": 0, "items": []})
        ctx = SimpleNamespace(headers={"Authorization": "Bearer test-token"})

        result = _api_request(
            ctx,
            "GET",
            query={"status": "pending", "limit": 25},
        )

        self.assertTrue(result["ok"])
        request = mocked_urlopen.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer test-token")
        self.assertIn("status=pending", request.full_url)
        self.assertIn("limit=25", request.full_url)

    def test_main_application_does_not_import_mcp_service(self):
        source = Path("app.py").read_text(encoding="utf-8")
        self.assertNotIn("services.gr360_ticket_mcp", source)
        self.assertNotIn("GR360_TICKET_MCP_ENABLED", source)


if __name__ == "__main__":
    unittest.main()
