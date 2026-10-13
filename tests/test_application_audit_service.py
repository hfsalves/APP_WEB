import unittest

from services.application_audit_service import turnover_time_action


class ApplicationAuditServiceTests(unittest.TestCase):
    def test_turnover_time_action_classifies_changes(self):
        self.assertEqual(turnover_time_action('', '15:00'), 'CRIAR')
        self.assertEqual(turnover_time_action('15:00', '16:00'), 'ALTERAR')
        self.assertEqual(turnover_time_action('15:00', ''), 'REMOVER')
        self.assertEqual(turnover_time_action('15:00', '15:00'), 'SEM_ALTERACAO')


if __name__ == '__main__':
    unittest.main()
