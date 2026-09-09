import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from services.document_ai_service import (
    _has_complete_purchase_finalization,
    _integrate_accounting_purchase,
)


class DocumentAiPurchaseFinalizationTests(unittest.TestCase):
    @staticmethod
    def document(document_type='invoice'):
        meta = {
            'phc_operations': {
                'provisional_invoice': {
                    'status': 'confirmed',
                    'fostamp': 'FO-RECEPTION',
                    'phc_database': 'HSOLS_FR',
                },
            },
            'phc_origins': [
                {'stamp': 'BO-PROFORMA', 'ndos': 218, 'document_type': 'proforma_invoice'},
            ],
        }
        return SimpleNamespace(
            docinstamp='DOC-1',
            processing_meta_json=json.dumps(meta),
            processing_status='parsed_ok',
        ), {
            'document_type': document_type,
            'customer': {'feid': 1, 'phc_database': 'HSOLS_FR'},
        }

    def test_complete_finalization_requires_existing_fo_and_proforma_lines(self):
        self.assertTrue(_has_complete_purchase_finalization({
            'status': 'confirmed',
            'fostamp': 'FO-1',
            'phc_database': 'HSOLS_FR',
            'proforma_stamps': ['BO-1'],
            'final_line_count': 2,
        }))
        self.assertFalse(_has_complete_purchase_finalization({
            'status': 'confirmed',
            'fostamp': 'FO-1',
            'phc_database': 'HSOLS_FR',
            'proforma_stamps': [],
            'final_line_count': 0,
        }))

    def test_credit_note_is_left_for_its_dedicated_workflow(self):
        document, payload = self.document('credit_note')
        self.assertEqual(_integrate_accounting_purchase(document, payload, 'tester', {'invoice': True}), {})

    def test_invoice_permission_is_checked_on_the_server(self):
        document, payload = self.document()
        with self.assertRaisesRegex(PermissionError, 'Sem permissão'):
            _integrate_accounting_purchase(document, payload, 'tester', {'invoice': False})

    @patch('services.document_ai_service.finalize_purchase_on_existing_fo')
    @patch('services.document_ai_phc_operation_service.run_document_phc_operation')
    def test_reuses_reception_fo_and_selected_proforma(self, run_operation, finalize):
        document, payload = self.document()
        run_operation.return_value = {'status': 'confirmed', 'fostamp': 'FO-RECEPTION'}

        result = _integrate_accounting_purchase(document, payload, 'tester', {'invoice': True})

        self.assertEqual(result['fostamp'], 'FO-RECEPTION')
        kwargs = run_operation.call_args.kwargs
        self.assertEqual(kwargs['operation_type'], 'purchase_finalization')
        self.assertEqual(kwargs['legacy_meta_key'], 'phc_purchase_finalization')
        self.assertEqual(kwargs['operation_context']['action'], 'update_existing_fo')
        self.assertEqual(kwargs['operation_context']['fostamp'], 'FO-RECEPTION')
        kwargs['execute']()
        finalize.assert_called_once()
        call_args = finalize.call_args.args
        self.assertEqual(call_args[1]['fostamp'], 'FO-RECEPTION')
        self.assertEqual(call_args[2][0]['stamp'], 'BO-PROFORMA')

    def test_blueprint_passes_invoice_integration_permission(self):
        source = Path('blueprints/document_ai.py').read_text(encoding='utf-8')
        self.assertIn("'invoice': _document_ai_has_integration_access('invoice')", source)


if __name__ == '__main__':
    unittest.main()
