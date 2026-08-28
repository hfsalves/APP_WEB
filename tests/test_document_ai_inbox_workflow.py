import unittest

from services.document_ai_service import (
    _document_inbox_scope_sql,
    _infer_invoice_type,
    _normalize_invoice_type,
)
from services.document_ai_required_info_service import evaluate_required_info


class DocumentAiInboxWorkflowTests(unittest.TestCase):
    def test_each_view_uses_its_persistent_stage(self):
        self.assertIn('RECEPTION_VALIDATED, 0) = 0', _document_inbox_scope_sql('home'))
        self.assertIn('MANAGEMENT_VALIDATED, 0) = 0', _document_inbox_scope_sql('management'))
        self.assertIn('ACCOUNTING_VALIDATED, 0) = 0', _document_inbox_scope_sql('accounting'))

    def test_unknown_view_fails_to_home_scope(self):
        scope = _document_inbox_scope_sql('anything')
        self.assertIn('RECEPTION_VALIDATED, 0) = 0', scope)
        self.assertNotIn('ACCOUNTING_VALIDATED, 0) = 0', scope)

    def test_archive_uses_completed_stage(self):
        self.assertIn('RECEPTION_VALIDATED, 0) = 1', _document_inbox_scope_sql('home', True))
        self.assertIn('MANAGEMENT_VALIDATED, 0) = 1', _document_inbox_scope_sql('management', True))
        self.assertIn('ACCOUNTING_VALIDATED, 0) = 1', _document_inbox_scope_sql('accounting', True))

    def test_invoice_type_aliases_are_normalized(self):
        self.assertEqual(_normalize_invoice_type('Betão'), 'concrete')
        self.assertEqual(_normalize_invoice_type('Materiais'), 'material')
        self.assertEqual(_normalize_invoice_type('Serviços'), 'services')
        self.assertEqual(_normalize_invoice_type(''), 'unknown')

    def test_invoice_type_can_be_inferred_from_document_lines(self):
        self.assertEqual(
            _infer_invoice_type({'lines': [{'description': 'Béton prêt à emploi'}]}),
            'concrete',
        )

    def test_management_state_uses_the_same_business_requirements_as_validation(self):
        result = evaluate_required_info(
            {
                'document_type': 'invoice',
                'invoice_type': 'services',
                'customer': {'feid': 1},
                'supplier': {'supplier_no': 10},
                'lines': [{'description': 'Serviço', 'qty': 1, 'unit_price': 10, 'net_amount': 10}],
                'totals': {'net_total': 10, 'tax_total': 2.3, 'gross_total': 12.3},
            },
            'management',
            processing_meta={'phc_origins': [{'stamp': 'BC-1'}]},
            required_fields=['entity', 'supplier', 'article'],
        )
        self.assertFalse(result['ok'])
        self.assertIn('Falta o artigo.', result['messages'])
        self.assertEqual(
            _infer_invoice_type({'lines': [{'description': 'Honoraires de conseil'}]}),
            'services',
        )
        self.assertEqual(
            _infer_invoice_type({'lines': [{'description': 'Treillis soudé'}]}),
            'material',
        )


if __name__ == '__main__':
    unittest.main()
