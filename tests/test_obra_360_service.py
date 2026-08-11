import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from flask import Flask

from services import obra_360_service as hub


class Obra360ServiceTests(unittest.TestCase):
    def test_context_only_enables_gr360_core_client_target(self):
        config = {
            "GR360_HUB_TARGET": "client",
            "GR360_HUB_EXPECTED_DATABASE": "GR360_CORE",
            "DB_CLIENT_NAME": "GR360_CORE",
        }
        self.assertTrue(hub.is_gr360_hub_context(config, current_target="client", require_request_context=False))
        self.assertFalse(hub.is_gr360_hub_context(config, current_target="prod", require_request_context=False))
        guest_config = {**config, "DB_CLIENT_NAME": "GUESTSPATUR"}
        self.assertFalse(hub.is_gr360_hub_context(guest_config, current_target="client", require_request_context=False))

    def test_overview_never_turns_missing_financial_data_into_zero(self):
        overview = hub.overview_for_work({"opcstamp": "OPC1", "codigo": "FR1787"})
        self.assertIsNone(overview["indicators"]["custo_real"]["value"])
        self.assertEqual(overview["indicators"]["custo_real"]["status"], "sem_dados")
        self.assertEqual(overview["indicators"]["custo_real"]["source"], "Ainda sem dados integrados")

    def test_only_supported_cards_are_marked_loading(self):
        self.assertEqual(hub._card_shell("orcamento")["state"], "loading")
        self.assertEqual(hub._card_shell("bl")["state"], "loading")
        self.assertEqual(hub._card_shell("custos")["state"], "loading")

    def test_cost_card_uses_management_map_groups(self):
        work = {"opcstamp": "OPC1", "codigo": "FR1787"}
        costs = {
            "total": 1250,
            "record_count": 4,
            "updated_at": "2026-08-10",
            "groups": [{"family": "2", "title": "2 · Mão de obra", "value": 1250, "record_count": 4}],
        }
        with patch.object(hub, "get_work_cost_groups", return_value=costs):
            with Flask(__name__).app_context():
                card = hub.card_data(work, "custos", "/generic/opc_projetos_form/OPC1")
        self.assertEqual(card["state"], "available")
        self.assertEqual(card["value"], 1250)
        self.assertEqual(card["groups"][0]["family"], "2")

    def test_production_card_uses_planning_assignments(self):
        work = {"opcstamp": "OPC1", "codigo": "HS2226", "origem": "HSOLS FRANCE"}
        assignments = [{
            "plan_stamp": "PLAN1",
            "date": "2026-07-21",
            "team": "IS ALSACE 02",
            "status": "concluida",
            "status_label": "Concluída",
            "intervention_count": 2,
            "updated_at": "2026-07-23",
        }]
        with patch.object(hub, "get_work_production_assignments", return_value=assignments):
            with Flask(__name__).app_context():
                card = hub.card_data(work, "producao", "/generic/opc_projetos_form/OPC1")
        self.assertEqual(card["state"], "available")
        self.assertEqual(card["record_count"], 1)
        self.assertEqual(card["assignments"][0]["team"], "IS ALSACE 02")

    def test_documents_card_lists_phc_opc_attachments(self):
        work = {"opcstamp": "OPC1"}
        attachments = {
            "source": {"name": "HSOLS France"},
            "attachments": [{"oristamp": "ANX1", "description": "Receção", "filename": "pvr.pdf"}],
        }
        with patch("services.opc_phc_info_service.get_opc_attachments", return_value=attachments):
            with Flask(__name__).app_context():
                card = hub.card_data(work, "anexos", "/generic/opc_projetos_form/OPC1")
        self.assertEqual(card["state"], "available")
        self.assertEqual(card["record_count"], 1)
        self.assertEqual(card["rows"][0]["filename"], "pvr.pdf")

    def test_opc_permission_is_required_for_non_admin_users(self):
        query = Mock()
        query.filter_by.return_value.first.return_value = SimpleNamespace(consultar=True)
        with patch.object(hub, "Acessos", SimpleNamespace(query=query)):
            self.assertTrue(hub.can_consult_opc(SimpleNamespace(ADMIN=False, DEV=False, LOGIN="reader")))
        self.assertFalse(hub.can_consult_opc(SimpleNamespace(ADMIN=False, DEV=False, LOGIN="")))

    def test_search_filters_out_origins_not_available_to_user(self):
        rows = [
            {"opcstamp": "1", "processo": "FR1787", "descricao": "Obra francesa", "cliente": "Cliente", "origem": "HSOLS FRANCE"},
            {"opcstamp": "2", "processo": "PT100", "descricao": "Obra PT", "cliente": "Cliente", "origem": "HSOLS PORTUGAL"},
        ]
        user = Mock(ADMIN=False, DEV=False)
        with patch.object(hub, "_search_rows", return_value=rows), patch.object(
            hub, "_allowed_sources", return_value=[{"NOME": "HSOLS France", "PHC_DB": "HSOLS_FR"}]
        ):
            works = hub.search_works("obra", user)
        self.assertEqual([work["codigo"] for work in works], ["FR1787"])

    def test_phc_card_failure_is_isolated_to_the_card(self):
        work = {"opcstamp": "OPC1"}
        with patch.object(hub, "_cached_phc_info", side_effect=RuntimeError("offline")):
            with Flask(__name__).app_context():
                card = hub.card_data(work, "orcamento", "/generic/opc_projetos_form/OPC1")
        self.assertEqual(card["state"], "error")
        self.assertIsNone(card["value"])

    def test_budget_rows_keep_their_phc_source_for_the_destination_link(self):
        work = {"opcstamp": "OPC1"}
        phc_info = {
            "fonte": {"feid": 12, "nome": "HSOLS France"},
            "orcamentos": [{"oristamp": "BO1", "total_iva": 100}],
            "autos": [],
        }
        with patch.object(hub, "_cached_phc_info", return_value=phc_info):
            with Flask(__name__).app_context():
                card = hub.card_data(work, "orcamento", "/generic/opc_projetos_form/OPC1")
        self.assertEqual(card["rows"][0]["source_feid"], 12)

    def test_customer_measurements_are_grouped_by_document_not_vat_rate(self):
        rows = hub._documents_by_stamp([
            {"oristamp": "AUTO1", "total_iva": 100, "iva": 10},
            {"oristamp": "AUTO1", "total_iva": 50, "iva": 5},
        ])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["total_iva"], 150)
        self.assertEqual(rows[0]["iva"], 15)

    def test_supplier_delivery_card_uses_only_delivery_documents(self):
        work = {"opcstamp": "OPC1"}
        phc_info = {
            "fonte": {"feid": 12, "nome": "HSOLS France"},
            "logistics": [
                {"kind": "bl", "oristamp": "BL1", "total": 100},
                {"kind": "bc", "oristamp": "BC1", "total": 250},
            ],
        }
        with patch.object(hub, "_cached_phc_info", return_value=phc_info):
            with Flask(__name__).app_context():
                card = hub.card_data(work, "bl", "/generic/opc_projetos_form/OPC1")
        self.assertEqual(card["record_count"], 1)
        self.assertEqual(card["value"], 100)
        self.assertEqual(card["rows"][0]["oristamp"], "BL1")

    def test_customer_invoice_card_uses_actual_ft_documents(self):
        work = {"opcstamp": "OPC1"}
        phc_info = {
            "fonte": {"feid": 12, "nome": "HSOLS France"},
            "faturas_cliente": [
                {"oristamp": "FT1", "total": 120},
                {"oristamp": "FT2", "total": -20},
            ],
        }
        with patch.object(hub, "_cached_phc_info", return_value=phc_info):
            with Flask(__name__).app_context():
                card = hub.card_data(work, "faturas_cliente", "/generic/opc_projetos_form/OPC1")
        self.assertEqual(card["record_count"], 2)
        self.assertEqual(card["value"], 100)
        self.assertEqual(card["rows"][0]["oristamp"], "FT1")


if __name__ == "__main__":
    unittest.main()
