from decimal import Decimal
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from modules.gr_budgets.service import (
    _client_payload,
    _budget_is_in_preparation,
    _budget_visibility_predicate,
    _component_family_payload,
    _component_payload,
    _header_payload,
    _intersol_budget_visibility_predicate,
    _line_item_sort_key,
    _line_order_for_write,
    _line_payload,
    _oci_payload,
    _ouvrage_payload,
    _pick_default_series,
    _phc_currency,
    _plus_value_payload,
    _salesperson_payload,
    _totals_payload,
    _revision_token,
    _series_name_key,
    _series_rows,
    _write_money,
)


class BudgetPayloadTests(unittest.TestCase):
    def setUp(self):
        self.company = {
            "name": "H Solutions France",
            "phc_db": "HSOLS_FR",
            "country": "FR",
            "currency": "EUR",
        }

    def test_devis_is_the_default_series(self):
        rows = [
            {"ndos": 200, "name": "Budget"},
            {"ndos": 115, "name": "Devis"},
        ]

        self.assertEqual(_pick_default_series(rows), 115)

    def test_client_budget_series_name_filter_is_accent_insensitive(self):
        allowed = {"devis", "etude et execution", "devis perdu"}

        self.assertIn(_series_name_key("Devis"), allowed)
        self.assertIn(_series_name_key("Étude et Exécution"), allowed)
        self.assertIn(_series_name_key("Devis Perdu"), allowed)
        self.assertNotIn(_series_name_key("Contrat Sous-Traitant"), allowed)
        self.assertNotIn(_series_name_key("Devis de Maintenance"), allowed)
        self.assertNotIn(_series_name_key("Devis GE"), allowed)

    def test_series_rows_only_returns_client_budget_series_in_screen_order(self):
        source_rows = [
            {"NDOS": 128, "NMDOS": "Contrat Sous-Traitant"},
            {"NDOS": 115, "NMDOS": "Devis"},
            {"NDOS": 134, "NMDOS": "Devis de Maintenance"},
            {"NDOS": 215, "NMDOS": "Devis GE"},
            {"NDOS": 123, "NMDOS": "Devis Perdu"},
            {"NDOS": 122, "NMDOS": "Étude et Exécution"},
        ]

        with patch("modules.gr_budgets.service._fetch_rows", return_value=source_rows):
            rows = _series_rows(object())

        self.assertEqual(
            [(row["ndos"], row["name"]) for row in rows],
            [
                (115, "Devis"),
                (122, "Étude et Exécution"),
                (123, "Devis Perdu"),
            ],
        )

    def test_maps_phc_header_fields_to_budget_header(self):
        header = _header_payload(
            {
                "BOSTAMP": "SIB26071029653,295000001",
                "NMDOS": "Devis",
                "NDOS": 115,
                "OBRANO": 1612,
                "BOANO": 2026,
                "DATAOBRA": "2026-07-20",
                "NO": 20029,
                "NOME": "AWO GENAUX ARCHITECTES",
                "TRAB1": "SAS LES CHANCEAUX",
                "OBRANOME": "TINQUEUX",
                "VENDNM": "SAID ABDER",
                "MOEDA": "EURO",
                "ETOTALDEB": Decimal("522784.63"),
                "ECUSTO": Decimal("443839.607"),
                "APROVADO": True,
                "PROCESSO": "FR0001",
                "AREA": "Produção",
                "U_MARGEM": Decimal("15.10"),
                "U_EMARGEM": Decimal("78945.02"),
            },
            self.company,
        )

        self.assertEqual(header["series"], "Devis")
        self.assertEqual(header["number"], 1612)
        self.assertEqual(header["client_name"], "AWO GENAUX ARCHITECTES")
        self.assertEqual(header["work_name"], "SAS LES CHANCEAUX")
        self.assertEqual(header["locality"], "TINQUEUX")
        self.assertEqual(header["process"], "FR0001")
        self.assertEqual(header["currency"], "EUR")
        self.assertTrue(header["approved"])

    def test_calculates_line_cost_margin_and_profit(self):
        line = _line_payload(
            {
                "BOSTAMP": "BUDGET1",
                "BISTAMP": "LINE1",
                "LITEM": 1,
                "REF": "DTI",
                "DESIGN": "DALLAGE TRADITIONNEL INTÉRIEUR",
                "QTT": Decimal("12275"),
                "EDEBITO": Decimal("38.4"),
                "ETTDEB": Decimal("471360"),
                "EPCUSTO": Decimal("32.639"),
                "IVA": Decimal("20"),
                "TABIVA": 2,
                "U_ESPESS": Decimal("0.160"),
                "U_BLOQPV": True,
                "U_BOMBA": True,
                "TEMOCI": True,
                "U_MO": True,
            }
        )

        self.assertEqual(line["cost_total"], 400643.725)
        self.assertEqual(line["profit"], 70716.275)
        self.assertEqual(line["margin_percentage"], 15.0)
        self.assertEqual(line["budget_stamp"], "BUDGET1")
        self.assertEqual(line["item_label"], "1")
        self.assertTrue(line["has_technical_detail"])
        self.assertEqual(line["surface"], 12275.0)
        self.assertEqual(line["volume"], 1964.0)

    def test_orders_line_items_by_each_numeric_segment(self):
        lines = [
            {"item_label": "4"},
            {"item_label": "3.10"},
            {"item_label": "2"},
            {"item_label": "3.2"},
            {"item_label": "3"},
            {"item_label": "1"},
            {"item_label": "3.1"},
        ]

        ordered = sorted(lines, key=_line_item_sort_key)

        self.assertEqual([line["item_label"] for line in ordered], ["1", "2", "3", "3.1", "3.2", "3.10", "4"])

    def test_builds_phc_line_order_for_positions_and_subpositions(self):
        self.assertEqual(_line_order_for_write({"item_label": "3"}, 1), 30000)
        self.assertEqual(_line_order_for_write({"item_label": "3.1"}, 1), 30100)
        self.assertEqual(_line_order_for_write({"item_label": "3.10"}, 1), 31000)

    def test_normalises_euro_and_revision_for_phc_write(self):
        self.assertEqual(_phc_currency("EUR"), "EURO")
        self.assertEqual(_revision_token(__import__("datetime").date(2026, 8, 3), "15:25:10"), "2026-08-03|15:25:10")
        self.assertEqual(_write_money("4.105"), Decimal("4.11"))
        self.assertEqual(_write_money("4.104"), Decimal("4.10"))

    def test_only_preparation_budgets_can_be_changed(self):
        self.assertTrue(_budget_is_in_preparation({}))
        self.assertFalse(_budget_is_in_preparation({"APROVADO": True}))
        self.assertFalse(_budget_is_in_preparation({"ADJUDICADO": 1}))
        self.assertFalse(_budget_is_in_preparation({"ANULADO": "true"}))

    def test_intersol_salespeople_10_to_14_only_see_their_own_devis(self):
        sql, params = _intersol_budget_visibility_predicate(12)

        self.assertIn("B.NDOS NOT IN (?, ?)", sql)
        self.assertIn("B.VENDEDOR = ?", sql)
        self.assertEqual(params, (115, 122, 12))

    def test_intersol_agency_salespeople_are_filtered_by_machine(self):
        alsace_sql, alsace_params = _intersol_budget_visibility_predicate(20)
        regional_sql, regional_params = _intersol_budget_visibility_predicate(22)

        self.assertIn("B.MAQUINA IN (?)", alsace_sql)
        self.assertEqual(alsace_params, (115, 122, "INTERSOL-ALSACE"))
        self.assertIn("B.MAQUINA IN (?, ?)", regional_sql)
        self.assertEqual(
            regional_params,
            (115, 122, "INTERSOL-LORRAINE", "INTERSOL-CHAMPAGNE"),
        )

    def test_intersol_visibility_uses_the_gr360_user_salesperson(self):
        sql, params = _budget_visibility_predicate(
            {"phc_db": "INTERSOL"},
            SimpleNamespace(VENDEDOR=10),
        )
        unrestricted_sql, unrestricted_params = _budget_visibility_predicate(
            {"phc_db": "HSOLS_FR"},
            SimpleNamespace(VENDEDOR=10),
        )

        self.assertIn("B.VENDEDOR = ?", sql)
        self.assertEqual(params, (115, 122, 10))
        self.assertEqual((unrestricted_sql, unrestricted_params), ("1 = 1", ()))

    def test_users_without_a_restricted_salesperson_keep_full_visibility(self):
        self.assertEqual(_intersol_budget_visibility_predicate(0), ("1 = 1", ()))
        self.assertEqual(_intersol_budget_visibility_predicate(99), ("1 = 1", ()))

    def test_uses_u_alt_as_variant_in_hsols_fr(self):
        line = _line_payload({"QTT": 1, "U_ALT": True, "U_VARIANTE": False})

        self.assertTrue(line["variant"])

    def test_maps_ouvrage_article_and_oci_cost_row(self):
        ouvrage = _ouvrage_payload(
            {
                "STSTAMP": "ARTICLE1",
                "REF": "DTI",
                "DESIGN": "DALLAGE TRADITIONNEL INTÉRIEUR",
                "FAMILIA": "OUVRAGE",
                "UNIDADE": "m²",
            }
        )
        row = _oci_payload(
            {
                "OCISTAMP": "OCI1",
                "BISTAMP": "LINE1",
                "FAMILIA": "BETON",
                "REF": "C25/30",
                "DESIGN": "Béton",
                "QTT": Decimal("0.13"),
                "EPCUSTO": Decimal("115"),
                "QTTTOTAL": Decimal("18.85"),
                "U_AREA": Decimal("145"),
                "U_ESPESS": Decimal("0.13"),
                "U_VOLUME": Decimal("18.85"),
                "U_FORMULA": "PA x ÉPAISSEUR",
            }
        )

        self.assertEqual(ouvrage["reference"], "DTI")
        self.assertEqual(ouvrage["family"], "OUVRAGE")
        self.assertEqual(row["line_stamp"], "LINE1")
        self.assertEqual(row["formula"], "PA x ÉPAISSEUR")
        self.assertEqual(row["volume"], 18.85)

    def test_maps_component_family_and_article_for_oci_picker(self):
        family = _component_family_payload(
            {
                "STFAMISTAMP": "FAMILY1",
                "REF": "BANDE-DESOLID",
                "NOME": "BANDE DE DESOLIDARISATION",
                "TXTQLOOK": "01",
                "ARTICLE_COUNT": 3,
            }
        )
        component = _component_payload(
            {
                "STSTAMP": "ARTICLE1",
                "REF": "DESOLIDARISATION",
                "DESIGN": "Bande de désolidarisation périphérique",
                "FAMILIA": "BANDE-DESOLID",
                "EPCUSTO": Decimal("2"),
                "U_FORMULA": "PRIX FIXE",
                "U_FORFAIT": 0,
            }
        )

        self.assertEqual(family["lookup_order"], "01")
        self.assertEqual(family["article_count"], 3)
        self.assertEqual(component["purchase_price"], 2.0)
        self.assertEqual(component["formula"], "PRIX FIXE")

    def test_maps_plus_value_bi_as_technical_grid_row(self):
        row = _plus_value_payload(
            {
                "BISTAMP": "PLUS1",
                "BOSTAMP": "BUDGET1",
                "LITEM": "16.1",
                "REF": "PVL",
                "DGERAL": "Pompage du béton",
                "FAMILIA": "DIVERS",
                "EDEBITO": Decimal("2.83"),
                "UNIDADE": "M²",
                "U_FORMULA": "PRIX FIXE",
            }
        )

        self.assertTrue(row["is_plus_value"])
        self.assertEqual(row["reference"], "PVL")
        self.assertEqual(row["purchase_price"], 2.83)
        self.assertEqual(row["level_label"], "16.1")

    def test_header_totals_take_precedence_over_calculated_lines(self):
        totals = _totals_payload(
            {"total": 522784.63, "cost": 443839.61},
            [{"total": 471360, "cost_total": 400643.73}],
        )

        self.assertEqual(totals["total"], 522784.63)
        self.assertEqual(totals["cost"], 443839.61)
        self.assertEqual(totals["profit"], 78945.02)
        self.assertEqual(totals["margin_percentage"], 15.1)

    def test_maps_client_lookup_row(self):
        client = _client_payload(
            {
                "CLSTAMP": "CLIENT1",
                "NO": 10009,
                "ESTAB": 0,
                "NOME": "GSE",
                "NCONT": "FR123456",
                "LOCAL": "Saint Priest",
                "CONTACTO": "Sarah GIRARDI",
                "EMAIL": "facture@gsegroup.com",
                "TELEFONE": "04 90 23 74 00",
                "VENDEDOR": 6,
                "VENDNM": "ELSON IGREJA",
            }
        )

        self.assertEqual(client["number"], 10009)
        self.assertEqual(client["name"], "GSE")
        self.assertEqual(client["contact"], "Sarah GIRARDI")
        self.assertEqual(client["salesperson_number"], 6)

    def test_maps_cm3_salesperson_row(self):
        salesperson = _salesperson_payload(
            {
                "CM3STAMP": "CM3-6",
                "CM": 6,
                "CMDESC": "ELSON IGREJA",
                "INACTIVO": False,
            }
        )

        self.assertEqual(salesperson["number"], 6)
        self.assertEqual(salesperson["name"], "ELSON IGREJA")
        self.assertFalse(salesperson["inactive"])


if __name__ == "__main__":
    unittest.main()
