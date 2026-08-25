import json
import unittest

from flask import Flask

from services.gr360_ticket_mcp import mount_gr360_ticket_mcp


class Gr360TicketMcpTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(
            GR360_TICKET_MCP_ENABLED="1",
            GR360_TICKET_MCP_HOST="localhost",
        )
        mount_gr360_ticket_mcp(self.app)
        self.client = self.app.test_client()
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }

    def tearDown(self):
        self.app.extensions["gr360_ticket_mcp"]["mount"].close()

    def post_rpc(self, method, params=None, request_id=1):
        return self.client.post(
            "/mcp/gr360-tickets/",
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
        payload = json.loads(response.get_data(as_text=True))
        tools = {item["name"]: item for item in payload["result"]["tools"]}
        self.assertEqual(
            set(tools),
            {"listar_tickets", "consultar_ticket", "criar_ticket", "atualizar_seguimento"},
        )
        self.assertTrue(tools["listar_tickets"]["annotations"]["readOnlyHint"])
        self.assertFalse(tools["criar_ticket"]["annotations"]["readOnlyHint"])

    def test_mount_can_be_disabled(self):
        app = Flask("disabled-mcp")
        app.config["GR360_TICKET_MCP_ENABLED"] = "0"
        mount_gr360_ticket_mcp(app)
        self.assertNotIn("gr360_ticket_mcp", app.extensions)
