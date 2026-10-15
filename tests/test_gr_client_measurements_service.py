from decimal import Decimal
import unittest
from unittest.mock import MagicMock, patch

from modules.gr_client_measurements.service import (
    ClientMeasurementsValidationError,
    PRODUCTION_ITEM_REF,
    _build_tax_totals,
    _budget_group_stamps,
    _budget_line_reference,
    _load_budget_group_headers,
    _market_process_code,
    _prepare_measurement_lines,
    _source_budget_stamp,
    list_budgets,
)


def _source_line(stamp: str, qty: str, value: str, price: str) -> dict:
    return {
        "BISTAMP": stamp,
        "QTT": Decimal(qty),
        "ETTDEB": Decimal(value),
        "EDEBITO": Decimal(price),
    }


class PrepareMeasurementLinesTests(unittest.TestCase):
    def test_uses_specific_structured_reference_or_default_production_article(self):
        self.assertEqual(PRODUCTION_ITEM_REF, _budget_line_reference({"REF": "DTE"}))
        self.assertEqual(PRODUCTION_ITEM_REF, _budget_line_reference({"REF": "DTI"}))
        self.assertEqual(
            "V.03.00.000.0001",
            _budget_line_reference({"REF": "V.03.00.000.0001"}),
        )
        self.assertEqual(
            "P.02.08.000.0021",
            _budget_line_reference({"REF": " p.02.08.000.0021 "}),
        )
        self.assertEqual(
            PRODUCTION_ITEM_REF,
            _budget_line_reference({"REF": "V.1.01.000.0021"}),
        )

    def test_keeps_unmeasured_budget_lines(self):
        sources = {
            "LINE1": _source_line("LINE1", "10", "100", "10"),
            "LINE2": _source_line("LINE2", "20", "100", "5"),
            "LINE3": _source_line("LINE3", "30", "300", "10"),
        }
        executed = {
            "LINE1": {"qty": Decimal("4"), "value": Decimal("40")},
            "LINE2": {"qty": Decimal("5"), "value": Decimal("25")},
        }

        prepared = _prepare_measurement_lines(
            sources,
            executed,
            [{"bistamp": "LINE2", "qty": "3"}],
        )

        self.assertEqual(
            [line["source_bistamp"] for line in prepared],
            ["LINE1", "LINE2", "LINE3"],
        )
        self.assertEqual(
            [line["qty"] for line in prepared],
            [Decimal("0.0000"), Decimal("3.0000"), Decimal("0.0000")],
        )
        self.assertEqual(prepared[0]["prior_qty"], Decimal("4"))
        self.assertEqual(prepared[0]["prior_qty"] + prepared[0]["qty"], Decimal("4.0000"))
        self.assertEqual(prepared[0]["cumulative_percent"], Decimal("40.00"))
        self.assertEqual(prepared[1]["prior_qty"], Decimal("5"))
        self.assertEqual(prepared[1]["prior_qty"] + prepared[1]["qty"], Decimal("8.0000"))
        self.assertEqual(prepared[1]["cumulative_percent"], Decimal("40.00"))
        self.assertEqual(prepared[2]["prior_qty"], Decimal("0"))
        self.assertEqual(prepared[2]["cumulative_percent"], Decimal("0.00"))

    def test_keeps_the_source_budget_for_lines_from_related_budgets(self):
        primary = _source_line("LINE1", "10", "100", "10")
        primary["BOSTAMP"] = "BUDGET1"
        additional = _source_line("LINE2", "5", "20", "4")
        additional["BOSTAMP"] = "BUDGET2"

        prepared = _prepare_measurement_lines(
            {"LINE1": primary, "LINE2": additional},
            {},
            [{"bistamp": "LINE2", "qty": "2"}],
        )

        self.assertEqual(_source_budget_stamp(prepared[0]["source"], "FALLBACK"), "BUDGET1")
        self.assertEqual(_source_budget_stamp(prepared[1]["source"], "FALLBACK"), "BUDGET2")

    def test_still_requires_a_nonzero_measurement(self):
        sources = {"LINE1": _source_line("LINE1", "10", "100", "10")}

        with self.assertRaises(ClientMeasurementsValidationError):
            _prepare_measurement_lines(
                sources,
                {},
                [{"bistamp": "LINE1", "qty": "0"}],
            )

    def test_preserves_a_negative_discount_line(self):
        discount = _source_line("DISCOUNT", "-1", "-10222.59", "10222.59")
        discount.update({"TABIVA": 2, "IVA": Decimal("20")})

        prepared = _prepare_measurement_lines(
            {"DISCOUNT": discount},
            {"DISCOUNT": {"qty": Decimal("-0.25"), "value": Decimal("-2555.65")}},
            [{"bistamp": "DISCOUNT", "qty": "-0.5", "value": "-5000"}],
        )

        line = prepared[0]
        self.assertEqual(line["qty"], Decimal("-0.5000"))
        self.assertEqual(line["amount"], Decimal("-5000.00"))
        self.assertEqual(line["prior_qty"], Decimal("-0.25"))
        self.assertEqual(line["prior_value"], Decimal("-2555.65"))
        self.assertEqual(line["remaining_qty"], Decimal("-0.75"))
        self.assertEqual(line["remaining_value"], Decimal("-7666.94"))
        self.assertEqual(line["current_percent"], Decimal("50.00"))
        self.assertEqual(line["cumulative_percent"], Decimal("75.00"))

    def test_rejects_a_discount_with_the_wrong_sign(self):
        discount = _source_line("DISCOUNT", "-1", "-10222.59", "10222.59")

        with self.assertRaisesRegex(ClientMeasurementsValidationError, "sinal invalido"):
            _prepare_measurement_lines(
                {"DISCOUNT": discount},
                {},
                [{"bistamp": "DISCOUNT", "qty": "0.5", "value": "5000"}],
            )

    def test_discount_reduces_the_taxable_base_and_vat(self):
        regular = _source_line("REGULAR", "10", "100", "10")
        regular.update({"TABIVA": 2, "IVA": Decimal("20")})
        discount = _source_line("DISCOUNT", "-1", "-10", "10")
        discount.update({"TABIVA": 2, "IVA": Decimal("20")})
        prepared = _prepare_measurement_lines(
            {"REGULAR": regular, "DISCOUNT": discount},
            {},
            [
                {"bistamp": "REGULAR", "qty": "10", "value": "100"},
                {"bistamp": "DISCOUNT", "qty": "-1", "value": "-10"},
            ],
        )

        totals = _build_tax_totals(prepared)

        self.assertEqual(totals[2]["base"], Decimal("90.00"))
        self.assertEqual(totals[2]["iva"], Decimal("18.00"))


class MarketProcessCodeTests(unittest.TestCase):
    def test_replaces_the_canonical_prefix_with_the_market_prefix(self):
        self.assertEqual(_market_process_code("INTERSOL", "HS1234"), "IS1234")
        self.assertEqual(_market_process_code("HSOLS_FR", "HS1234"), "FR1234")
        self.assertEqual(_market_process_code("HSOLS_PT", "HS1234"), "PT1234")
        self.assertEqual(_market_process_code("HSOLS_DE", "FR0123"), "DE0123")
        self.assertEqual(_market_process_code("HSOLS_ES", "HS1533"), "ES1533")
        self.assertEqual(_market_process_code("HSOLS_MA", "IS0001"), "MA0001")

    def test_keeps_non_work_codes_unchanged(self):
        self.assertEqual(_market_process_code("INTERSOL", "DGD"), "DGD")
        self.assertEqual(_market_process_code("OTHER", "HS1234"), "HS1234")


class BudgetGroupTests(unittest.TestCase):
    def test_budget_without_work_cannot_be_opened_for_measurement(self):
        with patch(
            "modules.gr_client_measurements.service._fetch_rows",
            return_value=[{"BOSTAMP": "BUDGET1", "PROCESSO": "", "CCUSTO": "", "ANULADO": 0}],
        ):
            with self.assertRaisesRegex(ClientMeasurementsValidationError, "obra definida"):
                _load_budget_group_headers(object(), 122, "BUDGET1")

    def test_preserves_order_and_removes_duplicate_stamps(self):
        self.assertEqual(
            _budget_group_stamps(
                [
                    {"BOSTAMP": "PRIMARY"},
                    {"BOSTAMP": "RELATED"},
                    {"BOSTAMP": " primary "},
                    {"BOSTAMP": ""},
                ]
            ),
            ["PRIMARY", "RELATED"],
        )

    def test_source_budget_stamp_falls_back_to_opened_budget(self):
        self.assertEqual(_source_budget_stamp({}, "PRIMARY"), "PRIMARY")


class BudgetListingTests(unittest.TestCase):
    def test_listing_excludes_budgets_without_a_work_code(self):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        fetch_rows = MagicMock(return_value=[])
        series = {
            "budget": {"NDOS": 122, "NMDOS": "Etude et Execution"},
            "auto": {"NDOS": 130, "NMDOS": "Situation de Travaux"},
        }

        with (
            patch(
                "modules.gr_client_measurements.service._company_for_user",
                return_value={"phc_db": "HSOLS_FR", "name": "HSOLS France"},
            ),
            patch("modules.gr_client_measurements.service._phc_conn_str", return_value="connection"),
            patch("modules.gr_client_measurements.service.pyodbc.connect", return_value=connection),
            patch("modules.gr_client_measurements.service._resolve_series", return_value=series),
            patch("modules.gr_client_measurements.service._fetch_rows", fetch_rows),
        ):
            result = list_budgets({"feid": 1}, object())

        listing_sql = fetch_rows.call_args.args[1]
        self.assertIn("NULLIF(C2.PROCESSO, '')", listing_sql)
        self.assertIn("NULLIF(C.CCUSTO, '')", listing_sql)
        self.assertEqual(result["rows"], [])


if __name__ == "__main__":
    unittest.main()
