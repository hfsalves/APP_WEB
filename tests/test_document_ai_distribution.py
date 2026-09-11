import json
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services.document_ai_distribution_service import (
    _normalize_rule,
    assert_document_distribution_available,
    normalize_distribution_document_class,
)
from services.document_ai_service import DocumentDraftConflictError, validate_document_inbox_stage


class DocumentAiDistributionRuleTests(unittest.TestCase):
    def test_terminal_rule_has_no_destination_or_state(self):
        rule = _normalize_rule({
            'doc_class': 'mail', 'source': 'home',
            'destination': '', 'state': 'validated', 'terminal': True,
        })
        self.assertTrue(rule['terminal'])
        self.assertEqual(rule['destination'], '')
        self.assertEqual(rule['state'], 'none')

    def test_mail_without_destination_is_reception_terminal(self):
        service = __import__('services.document_ai_distribution_service', fromlist=['x'])
        self.assertIn("('mail', 'home', None, 'none', True)", Path(service.__file__).read_text(encoding='utf-8'))
        workflow_source = Path(__import__('services.document_ai_service', fromlist=['x']).__file__).read_text(encoding='utf-8')
        self.assertIn("destination = ','.join(routed_destinations) if routed_destinations else 'archive'", workflow_source)

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

    @patch('services.document_ai_distribution_service.ensure_document_ai_distribution_schema')
    def test_bank_invoice_goes_directly_to_accounting(self, _ensure):
        document = SimpleNamespace(
            doc_type_detected='invoice', fornecedor_no=10231, feid=1,
            json_resultado=json.dumps({'supplier': {'supplier_type': 'Banque'}}),
        )

        rules = assert_document_distribution_available(document, 'home')

        self.assertEqual(rules, [{
            'id': 'bank-direct', 'doc_class': 'invoice', 'source': 'home',
            'destination': 'accounting', 'state': 'none', 'terminal': False,
        }])

    @patch('services.document_ai_distribution_service._distribution_rules')
    @patch('services.document_ai_distribution_service.ensure_document_ai_distribution_schema')
    def test_bank_name_without_phc_type_uses_normal_rules(self, _ensure, distribution_rules):
        configured = [{
            'id': 'normal', 'doc_class': 'invoice', 'source': 'home',
            'destination': 'management', 'state': 'automatic', 'terminal': False,
        }]
        distribution_rules.return_value = configured
        document = SimpleNamespace(
            doc_type_detected='invoice', fornecedor_no=1, feid=1,
            json_resultado=json.dumps({'supplier': {'name': 'Banque sans classement'}}),
        )

        self.assertEqual(assert_document_distribution_available(document, 'home'), configured)

    @patch('services.document_ai_distribution_service.ensure_document_ai_distribution_schema')
    def test_bank_credit_note_uses_same_direct_route(self, _ensure):
        document = SimpleNamespace(
            doc_type_detected='credit_note', fornecedor_no=52603, feid=2,
            json_resultado=json.dumps({'supplier': {'supplier_type': 'Banco'}}),
        )

        rules = assert_document_distribution_available(document, 'home')

        self.assertEqual(rules[0]['destination'], 'accounting')
        self.assertEqual(rules[0]['state'], 'none')

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

    @patch('services.document_ai_service.db.session.rollback')
    @patch('services.document_ai_service.db.session.refresh')
    @patch('services.document_ai_service.db.session.execute')
    @patch('services.document_ai_service.db.session.get')
    def test_transition_rejects_a_stale_saved_version(self, get_document, execute, _refresh, rollback):
        current = datetime(2026, 9, 9, 12, 30, 0)
        get_document.return_value = SimpleNamespace(
            docinstamp='DOC-1', dtalt=current, dtcri=current,
            reception_validated=False, management_validated=False,
            accounting_validated=False,
        )
        execute.return_value = MagicMock(scalar_one=MagicMock(return_value='DOC-1'))

        with self.assertRaises(DocumentDraftConflictError):
            validate_document_inbox_stage(
                'DOC-1', 'management', 'tester', expected_version='2026-09-09T12:00:00.000000'
            )

        rollback.assert_called_once()


if __name__ == '__main__':
    unittest.main()
