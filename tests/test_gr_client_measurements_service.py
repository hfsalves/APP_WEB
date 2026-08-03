from decimal import Decimal
import unittest

from modules.gr_client_measurements.service import (
    ClientMeasurementsValidationError,
    _market_process_code,
    _prepare_measurement_lines,
)


def _source_line(stamp: str, qty: str, value: str, price: str) -> dict:
    return {
        "BISTAMP": stamp,
        "QTT": Decimal(qty),
        "ETTDEB": Decimal(value),
        "EDEBITO": Decimal(price),
    }


class PrepareMeasurementLinesTests(unittest.TestCase):
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

    def test_still_requires_a_positive_measurement(self):
        sources = {"LINE1": _source_line("LINE1", "10", "100", "10")}

        with self.assertRaises(ClientMeasurementsValidationError):
            _prepare_measurement_lines(
                sources,
                {},
                [{"bistamp": "LINE1", "qty": "0"}],
            )


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


if __name__ == "__main__":
    unittest.main()
