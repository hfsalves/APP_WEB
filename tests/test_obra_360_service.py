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
        self.assertEqual(hub._card_shell("custos")["state"], "preparation")

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


if __name__ == "__main__":
    unittest.main()
