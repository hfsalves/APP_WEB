from datetime import date
import unittest

from services.phc_close_dates_service import _format_close_date, _parse_close_date, update_all_close_dates


class PhcCloseDateParsingTests(unittest.TestCase):
    def test_parse_supported_phc_date_formats(self):
        expected = date(2026, 7, 31)
        self.assertEqual(_parse_close_date('31.07.2026'), expected)
        self.assertEqual(_parse_close_date('31/07/2026'), expected)
        self.assertEqual(_parse_close_date('2026-07-31'), expected)

    def test_reject_invalid_value(self):
        self.assertIsNone(_parse_close_date('2026-31-07'))

    def test_phc_format_is_day_month_year(self):
        self.assertEqual(_format_close_date(date(2026, 7, 31)), '31.07.2026')

    def test_bulk_update_requires_iso_date(self):
        with self.assertRaises(Exception):
            update_all_close_dates('31/07/2026')
