"""Indicative prices use the first available future window, without database access."""

from datetime import date, timedelta
from decimal import Decimal
import re
import unittest
from unittest.mock import Mock, patch

from services.booking_portal_pricing import get_from_prices, select_from_prices


TODAY = date(2030, 9, 18)


def row(al_id, offset, price):
    return {"al_id": al_id, "day": TODAY + timedelta(days=offset), "price": price}


def parameter_values(params):
    values = []
    for value in params.values():
        if isinstance(value, (tuple, list, set)):
            values.extend(value)
        else:
            values.append(value)
    return values


class SelectFromPricesTests(unittest.TestCase):
    def test_first_thirty_days_take_precedence_over_cheaper_later_prices(self):
        rows = [row("one", 60, "2"), row("one", 29, "85.50"), row("one", 30, "1")]
        rows += [row("one", 0, "120.00"), row("one", 14, "90")]
        self.assertEqual(select_from_prices(rows, TODAY), {"one": Decimal("85.50")})

    def test_falls_back_to_sixty_days_only_when_first_window_has_no_prices(self):
        rows = [row("one", 30, "90"), row("one", 59, "80"), row("one", 60, "1")]
        self.assertEqual(select_from_prices(rows, TODAY), {"one": Decimal("80")})

    def test_falls_back_to_ninety_days_only_when_first_two_windows_are_empty(self):
        rows = [row("one", 60, "95"), row("one", 89, "75"), row("one", 90, "1")]
        self.assertEqual(select_from_prices(rows, TODAY), {"one": Decimal("75")})

    def test_final_fallback_has_no_artificial_one_year_limit(self):
        rows = [row("one", 90, "99"), row("one", 500, "45"), row("two", 730, "65")]
        self.assertEqual(select_from_prices(rows, TODAY), {
            "one": Decimal("45"), "two": Decimal("65"),
        })

    def test_exact_window_boundaries(self):
        for earlier, later in ((0, 30), (29, 30), (30, 60), (59, 60), (60, 90), (89, 90)):
            with self.subTest(earlier=earlier, later=later):
                rows = [row("one", later, "1"), row("one", earlier, "100")]
                self.assertEqual(select_from_prices(rows, TODAY), {"one": Decimal("100")})

    def test_each_property_chooses_its_own_first_available_window(self):
        rows = [
            row("early", 4, "100"), row("early", 32, "5"),
            row("middle", 32, "80"), row("middle", 64, "5"),
            row("late", 64, "60"), row("late", 94, "5"),
            row("future", 400, "40"), row("future", 800, "30"),
        ]
        expected = {
            "early": Decimal("100"), "middle": Decimal("80"),
            "late": Decimal("60"), "future": Decimal("30"),
        }
        self.assertEqual(select_from_prices(rows, TODAY), expected)
        self.assertEqual(select_from_prices(list(reversed(rows)), TODAY), expected)

    def test_invalid_rows_and_past_or_non_positive_prices_are_discarded(self):
        rows = [row("one", -1, "1"), row("one", -800, "0.01")]
        rows += [row("one", 0, price) for price in (
            None, "", "not-a-price", "0", "-1", Decimal("NaN"), Decimal("Infinity"),
        )]
        rows += [
            {"al_id": "one", "day": None, "price": "1"},
            {"al_id": "one", "day": "not-a-date", "price": "1"},
            row("", 0, "1"), row(None, 0, "1"), {},
            row("one", 30, "80.25"),
        ]
        self.assertEqual(select_from_prices(rows, TODAY), {"one": Decimal("80.25")})

    def test_no_eligible_prices_produces_no_misleading_starting_price(self):
        self.assertEqual(select_from_prices([], TODAY), {})
        self.assertEqual(select_from_prices([row("one", -1, "5"), row("two", 1, "0")], TODAY), {})


class GetFromPricesTests(unittest.TestCase):
    def setUp(self):
        self.db = Mock()
        self.db.session.execute.return_value.mappings.return_value.all.return_value = []
        patcher = patch("services.booking_portal_pricing.db", self.db)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_empty_or_blank_ids_do_not_query_the_database(self):
        for ids in (None, [], (), ["", " ", None]):
            with self.subTest(ids=ids):
                self.assertEqual(get_from_prices(ids, today=TODAY), {})
        self.db.session.execute.assert_not_called()

    def test_ids_and_date_are_bound_parameters_and_rows_use_the_selector(self):
        self.db.session.execute.return_value.mappings.return_value.all.return_value = [
            row("one", 0, "105"), row("one", 30, "1"), row("two", 45, "75"),
        ]
        self.assertEqual(get_from_prices(["one", "two"], today=TODAY), {
            "one": Decimal("105"), "two": Decimal("75"),
        })
        self.db.session.execute.assert_called_once()
        statement, params = self.db.session.execute.call_args.args
        self.assertNotIn("'one'", str(statement))
        self.assertNotIn("'two'", str(statement))
        values = parameter_values(params)
        self.assertIn(TODAY, values)
        self.assertIn("one", values)
        self.assertIn("two", values)
        self.db.session.execute.return_value.mappings.return_value.all.assert_called_once()

    def test_property_ids_are_deduplicated_and_queried_in_batches_of_500(self):
        ids = [f"stay-{index}" for index in range(1001)]
        self.assertEqual(get_from_prices(ids + ids[:10], today=TODAY), {})
        self.assertEqual(self.db.session.execute.call_count, 3)
        batches = []
        for call in self.db.session.execute.call_args_list:
            params = call.args[1]
            batches.append([value for value in parameter_values(params) if value in ids])
        self.assertEqual([len(batch) for batch in batches], [500, 500, 1])
        self.assertEqual({value for batch in batches for value in batch}, set(ids))

    def test_query_excludes_closed_properties_unpriced_nights_and_occupied_nights(self):
        get_from_prices(["one"], today=TODAY)
        sql = re.sub(r"\s+", " ", str(self.db.session.execute.call_args.args[0])).upper()
        self.assertIn("PR_CALC_DAY", sql)
        self.assertIn("NOT EXISTS", sql)
        self.assertIn("RS.DATAIN IS NOT NULL", sql)
        self.assertIn("RS.DATAOUT IS NOT NULL", sql)
        self.assertRegex(sql, r"ISNULL\(RS\.CANCELADA,\s*0\)\s*=\s*0")
        self.assertRegex(sql, r"ISNULL\(AL\.INATIVO,\s*0\)\s*=\s*0")
        self.assertRegex(sql, r"ISNULL\(AL\.FECHADO,\s*0\)\s*=\s*0")
        self.assertRegex(sql, r"(?:PRECO_FINAL[^;]*?)>\s*0")
        day_expression = r"(?:CAST\(D\.\[DATA\] AS DATE\)|D\.\[DATA\])"
        self.assertRegex(sql, r"CAST\(RS\.DATAIN AS DATE\)\s*<=\s*" + day_expression)
        self.assertRegex(sql, r"CAST\(RS\.DATAOUT AS DATE\)\s*>\s*" + day_expression)


if __name__ == "__main__":
    unittest.main()
