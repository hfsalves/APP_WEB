import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from services.document_ai_phc_operation_service import run_document_phc_operation


class DocumentAiPhcOperationServiceTests(unittest.TestCase):
    @staticmethod
    def document(meta=None):
        return SimpleNamespace(
            docinstamp='DOC-1',
            processing_meta_json=json.dumps(meta or {}),
            processing_stage='parsed_ok',
            last_processing_error='',
            dtalt=None,
            useralteracao='',
        )

    @staticmethod
    def is_complete(payload):
        return payload.get('status') == 'confirmed' and bool(payload.get('fostamp'))

    def run_operation(self, document, execute, context=None):
        return run_document_phc_operation(
            document,
            operation_type='provisional_invoice',
            requested_by='tester',
            execute=execute,
            is_complete=self.is_complete,
            result_fields=('fostamp', 'phc_database', 'ged_confirmed'),
            operation_context=context or {'document_id': 'DOC-1'},
        )

    @patch('services.document_ai_phc_operation_service.db.session.commit')
    def test_persists_intent_and_confirmed_identity(self, commit):
        document = self.document()
        result = self.run_operation(document, lambda: {
            'fostamp': 'FO-1', 'phc_database': 'HSOLS_FR', 'ged_confirmed': True,
        })

        self.assertEqual(result['status'], 'confirmed')
        self.assertEqual(result['fostamp'], 'FO-1')
        meta = json.loads(document.processing_meta_json)
        self.assertEqual(meta['phc_integration']['fostamp'], 'FO-1')
        self.assertEqual(meta['phc_operations']['provisional_invoice']['fostamp'], 'FO-1')
        self.assertEqual(commit.call_count, 2)

    @patch('services.document_ai_phc_operation_service.db.session.commit')
    def test_reuses_completed_operation_after_lost_response(self, commit):
        existing = {
            'status': 'confirmed', 'fostamp': 'FO-1', 'phc_database': 'HSOLS_FR',
        }
        document = self.document({'phc_operations': {'provisional_invoice': existing}})
        execute = Mock()

        result = self.run_operation(document, execute)

        self.assertEqual(result['fostamp'], 'FO-1')
        execute.assert_not_called()
        commit.assert_not_called()

    @patch('services.document_ai_phc_operation_service.db.session.commit')
    def test_failure_is_recoverable_and_does_not_hide_original_error(self, commit):
        document = self.document()

        with self.assertRaisesRegex(RuntimeError, 'PHC indisponível'):
            self.run_operation(document, Mock(side_effect=RuntimeError('PHC indisponível')))

        operation = json.loads(document.processing_meta_json)['phc_operations']['provisional_invoice']
        self.assertEqual(operation['status'], 'failed_recoverable')
        self.assertEqual(document.processing_stage, 'integration_failed_recoverable')
        self.assertGreaterEqual(commit.call_count, 2)

    @patch('services.document_ai_phc_operation_service.db.session.commit')
    def test_incomplete_result_is_kept_for_reconciliation(self, commit):
        document = self.document()

        with self.assertRaisesRegex(RuntimeError, 'identificadores obrigatórios'):
            self.run_operation(document, lambda: {'phc_database': 'HSOLS_FR'})

        operation = json.loads(document.processing_meta_json)['phc_operations']['provisional_invoice']
        self.assertEqual(operation['status'], 'failed_recoverable')
        self.assertEqual(operation['phc_database'], 'HSOLS_FR')

    @patch('services.document_ai_phc_operation_service.db.session.commit')
    def test_sensitive_context_is_redacted(self, _commit):
        document = self.document()
        self.run_operation(document, lambda: {'fostamp': 'FO-1'}, {
            'document_id': 'DOC-1', 'api_token': 'secret', 'connection_string': 'server=x',
        })

        context = json.loads(document.processing_meta_json)['phc_integration']['context']
        self.assertEqual(context['api_token'], '***REDACTED***')
        self.assertEqual(context['connection_string'], '***REDACTED***')


if __name__ == '__main__':
    unittest.main()
