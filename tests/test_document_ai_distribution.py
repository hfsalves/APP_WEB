import unittest
from unittest.mock import patch

from services.document_ai_distribution_service import (
    _normalize_rule,
    assert_document_distribution_available,
    normalize_distribution_document_class,
)
from services.document_ai_service import validate_document_inbox_stage


class DocumentAiDistributionRuleTests(unittest.TestCase):
    def test_terminal_rule_has_no_destination_or_state(self):
        rule = _normalize_rule({
            'doc_class': 'mail', 'source': 'home',
            'destination': '', 'state': 'validated', 'terminal': True,
        })
        self.assertTrue(rule['terminal'])
        self.assertEqual(rule['destination'], '')
        self.assertEqual(rule['state'], 'none')

    def test_same_source_and_destination_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'não podem ser iguais'):
            _normalize_rule({
                'doc_class': 'invoice', 'source': 'home',
                'destination': 'home', 'state': 'pending',
            })

    def test_management_requires_automatic(self):
        with self.assertRaisesRegex(ValueError, 'Automático'):
            _normalize_rule({
                'doc_class': 'invoice', 'source': 'home',
                'destination': 'management', 'state': 'pending',
            })

    def test_invoice_accounting_accepts_pending_or_validated(self):
        for state in ('pending', 'validated'):
            rule = _normalize_rule({
                'doc_class': 'invoice', 'source': 'home',
                'destination': 'accounting', 'state': state,
            })
            self.assertEqual(rule['state'], state)

    def test_provisional_invoice_uses_invoice_distribution(self):
        self.assertEqual(normalize_distribution_document_class('provisional_invoice'), 'invoice')

    @patch('services.document_ai_distribution_service._distribution_rules', return_value=[])
    @patch('services.document_ai_distribution_service.ensure_document_ai_distribution_schema')
    def test_missing_distribution_fails_closed(self, _ensure, _rules):
        document = type('Document', (), {'doc_type_detected': 'delivery_note'})()
        with self.assertRaisesRegex(ValueError, 'Não existe distribuição'):
            assert_document_distribution_available(document, 'home')

    @patch('services.document_ai_distribution_service._distribution_rules', return_value=[])
    @patch('services.document_ai_distribution_service.ensure_document_ai_distribution_schema')
    def test_accounting_without_explicit_destination_is_terminal(self, _ensure, _rules):
        document = type('Document', (), {'doc_type_detected': 'invoice'})()
        rules = assert_document_distribution_available(document, 'accounting')
        self.assertEqual(len(rules), 1)
        self.assertTrue(rules[0]['terminal'])
        self.assertEqual(rules[0]['destination'], '')

    @patch('services.document_ai_service.db.session.get')
    def test_revalidating_completed_stage_is_idempotent(self, get_document):
        get_document.return_value = type('Document', (), {
            'docinstamp': 'DOC-1',
            'reception_validated': True,
            'management_validated': True,
            'accounting_validated': False,
        })()

        result = validate_document_inbox_stage('DOC-1', 'management', 'tester')

        self.assertTrue(result['ok'])
        self.assertTrue(result['already_validated'])
        self.assertTrue(result['distribution']['unchanged'])


if __name__ == '__main__':
    unittest.main()
