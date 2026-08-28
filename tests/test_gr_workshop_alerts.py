import unittest
from datetime import date

from modules.gr_workshop.service import _preventive_alert


class WorkshopPreventiveAlertTests(unittest.TestCase):
    def test_alerts_when_date_is_due(self):
        result = _preventive_alert("2026-08-28", 0, 0, today=date(2026, 8, 28))
        self.assertTrue(result["active"])
        self.assertIn("2026-08-28", result["reason"])

    def test_alerts_when_mileage_is_due(self):
        result = _preventive_alert(None, 10000, 10001, today=date(2026, 8, 28))
        self.assertTrue(result["active"])
        self.assertIn("10,000 km", result["reason"])

    def test_does_not_alert_before_threshold(self):
        result = _preventive_alert("2026-09-10", 10000, 9000, today=date(2026, 8, 28))
        self.assertFalse(result["active"])


if __name__ == "__main__":
    unittest.main()
