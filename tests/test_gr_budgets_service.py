from decimal import Decimal
import unittest

from modules.gr_budgets.service import (
    _header_payload,
    _line_payload,
    _pick_default_series,
    _totals_payload,
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
        self.assertTrue(line["has_technical_detail"])

    def test_header_totals_take_precedence_over_calculated_lines(self):
        totals = _totals_payload(
            {"total": 522784.63, "cost": 443839.61},
            [{"total": 471360, "cost_total": 400643.73}],
        )

        self.assertEqual(totals["total"], 522784.63)
        self.assertEqual(totals["cost"], 443839.61)
        self.assertEqual(totals["profit"], 78945.02)
        self.assertEqual(totals["margin_percentage"], 15.1)


if __name__ == "__main__":
    unittest.main()
