import unittest
from datetime import date, time
from types import SimpleNamespace

from services import ponto_service as ponto


class PontoServiceTests(unittest.TestCase):
    def test_access_is_limited_to_enabled_users_and_admins(self):
        self.assertTrue(ponto.ponto_user_allowed(SimpleNamespace(ADMIN=True, PONTO=False)))
        self.assertTrue(ponto.ponto_user_allowed(SimpleNamespace(ADMIN=False, PONTO=True)))
        self.assertFalse(ponto.ponto_user_allowed(SimpleNamespace(ADMIN=False, PONTO=False)))

    def test_current_month_accepts_only_dates_up_to_today(self):
        today = date(2026, 10, 16)
        self.assertTrue(ponto._is_editable_day(date(2026, 10, 1), today)[0])
        self.assertFalse(ponto._is_editable_day(date(2026, 10, 17), today)[0])

    def test_previous_month_closes_after_third_day(self):
        previous = date(2026, 9, 30)
        self.assertTrue(ponto._is_editable_day(previous, date(2026, 10, 3))[0])
        self.assertFalse(ponto._is_editable_day(previous, date(2026, 10, 4))[0])

    def test_time_and_duration_helpers_use_minutes(self):
        self.assertEqual(ponto._clock('08:45', 'Entrée'), time(8, 45))
        self.assertEqual(ponto._duration_text(510), '08:30')

    def test_invalid_clock_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'invalide'):
            ponto._clock('25:00', 'L’heure')


if __name__ == '__main__':
    unittest.main()
