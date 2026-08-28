import unittest
from unittest.mock import patch

from services.document_ai_required_info_service import _normalize, evaluate_required_info


def _document(**overrides):
    value = {
        'document_type': 'invoice',
        'document_date': '2026-08-28',
        'customer': {'feid': 1},
        'supplier': {'supplier_no': 25},
        'totals': {'gross_total': 123, 'tax_total': 23, 'net_total': 100},
        'lines': [{
            'article_ref': 'MAT001', 'description': 'Material', 'qty': 2,
            'unit_price': 50, 'net_amount': 100, 'ccusto': 'OBRA01',
        }],
    }
    value.update(overrides)
    return value


class RequiredInfoTests(unittest.TestCase):
    def test_supplier_resolved_is_only_valid_for_advertising(self):
        with self.assertRaisesRegex(ValueError, 'Publicidade'):
            _normalize({'doc_class': 'invoice', 'view': 'home', 'field': 'supplier_resolved'})
        self.assertEqual(
            _normalize({'doc_class': 'advertising', 'view': 'home', 'field': 'supplier_resolved'})['field'],
            'supplier_resolved',
        )

    def test_rejects_field_in_incompatible_view(self):
        with self.assertRaisesRegex(ValueError, 'compatível'):
            _normalize({'doc_class': 'invoice', 'view': 'home', 'field': 'article'})

    @patch('services.document_ai_required_info_service.required_fields_for', return_value=['entity', 'supplier'])
    def test_home_invoice_accepts_identified_entity_and_supplier(self, _required):
        result = evaluate_required_info(_document(), 'home')
        self.assertTrue(result['ok'])
        self.assertEqual(result['missing'], [])

    @patch('services.document_ai_required_info_service.required_fields_for', return_value=['supplier'])
    def test_home_invoice_reports_missing_supplier(self, _required):
        document = _document(supplier={'supplier_no': 'not-a-number'})
        result = evaluate_required_info(document, 'home')
        self.assertFalse(result['ok'])
        self.assertEqual(result['missing'], ['supplier'])
        self.assertEqual(result['targets'], ['docAiExtractSupplierCard'])

    @patch('services.document_ai_required_info_service.required_fields_for', return_value=['supplier_resolved'])
    def test_advertising_accepts_explicit_absence_of_supplier(self, _required):
        document = _document(
            document_type='advertising', supplier={}, supplier_explicitly_absent=True,
        )
        self.assertTrue(evaluate_required_info(document, 'home')['ok'])

    @patch('services.document_ai_required_info_service.required_fields_for', return_value=['description'])
    def test_informative_line_only_requires_a_description(self, _required):
        document = _document(lines=[{'description': 'Informação livre', 'informative': True}])
        self.assertTrue(evaluate_required_info(document, 'management')['ok'])

    @patch('services.document_ai_required_info_service.required_fields_for', return_value=[])
    def test_management_rejects_incoherent_line_total(self, _required):
        document = _document(lines=[{
            'article_ref': 'MAT001', 'description': 'Material', 'qty': 2,
            'unit_price': 50, 'net_amount': 80,
        }])
        result = evaluate_required_info(document, 'management')
        self.assertFalse(result['ok'])
        self.assertIn('Quantidade x PU', result['messages'][0])

    @patch('services.document_ai_required_info_service.required_fields_for', return_value=[])
    def test_management_rejects_incoherent_document_totals(self, _required):
        document = _document(totals={'gross_total': 130, 'tax_total': 23, 'net_total': 100})
        result = evaluate_required_info(document, 'management')
        self.assertFalse(result['ok'])
        self.assertIn('não são coerentes', result['messages'][0])

    @patch('services.document_ai_required_info_service.required_fields_for', return_value=[])
    def test_management_rejects_associate_without_principal(self, _required):
        document = _document(lines=[{
            'article_ref': 'MAT001', 'description': 'Material', 'qty': 1,
            'unit_price': 100, 'net_amount': 100, 'article_group_code': 'A1',
        }])
        result = evaluate_required_info(document, 'management')
        self.assertFalse(result['ok'])
        self.assertIn('grupos de artigos', result['messages'][0])


if __name__ == '__main__':
    unittest.main()
