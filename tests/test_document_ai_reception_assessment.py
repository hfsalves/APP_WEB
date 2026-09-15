import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from services.document_ai_service import assess_document_reception, preflight_document_inbox_stage


class DocumentAiReceptionAssessmentTests(unittest.TestCase):
    def complete_invoice(self):
        return {
            'document_type': 'invoice',
            'invoice_type': 'material',
            'customer': {'feid': 1},
            'supplier': {'supplier_no': 10},
            'document_number': 'FAC-1',
            'document_date': '2026-08-28',
            'totals': {},
        }

    def test_complete_invoice_is_ok_without_project_or_totals(self):
        assessment = assess_document_reception(self.complete_invoice())
        self.assertEqual(assessment['state'], 'OK')
        self.assertEqual(assessment['missing'], [])

    def test_reception_does_not_require_document_number_or_date(self):
        document = self.complete_invoice()
        document.pop('document_number')
        document.pop('document_date')
        assessment = assess_document_reception(document)
        self.assertEqual(assessment['state'], 'OK')
        self.assertEqual(assessment['missing'], [])

    def test_management_invoice_type_does_not_block_reception(self):
        invoice = self.complete_invoice()
        invoice['invoice_type'] = 'unknown'
        self.assertEqual(assess_document_reception(invoice)['state'], 'OK')
        self.assertNotIn('invoice_type', assess_document_reception(invoice)['missing'])
        credit_note = dict(invoice, document_type='credit_note')
        self.assertEqual(assess_document_reception(credit_note)['state'], 'OK')

    def test_multiple_documents_are_always_blocked(self):
        document = self.complete_invoice()
        document['document_batch'] = {'contains_multiple_documents': True}
        assessment = assess_document_reception(document)
        self.assertEqual(assessment['state'], 'Bloqueio')
        self.assertIn('Vários documentos no PDF', assessment['reasons'])

    def test_advertising_allows_explicit_no_supplier(self):
        document = self.complete_invoice()
        document.update({'document_type': 'advertising', 'supplier': {}, 'supplier_explicitly_absent': True})
        document.pop('invoice_type')
        assessment = assess_document_reception(document)
        self.assertEqual(assessment['state'], 'OK')
        self.assertNotIn('supplier', assessment['missing'])

    def test_correspondence_allows_a_free_text_external_party(self):
        document = self.complete_invoice()
        document.update({
            'document_type': 'mail',
            'supplier': {'name': 'Remetente não registado'},
        })
        document.pop('invoice_type')

        assessment = assess_document_reception(document)

        self.assertEqual(assessment['state'], 'OK')
        self.assertNotIn('supplier', assessment['missing'])

    def test_missing_entity_and_supplier_have_separate_reasons(self):
        document = self.complete_invoice()
        document['customer'] = {}
        document['supplier'] = {}
        assessment = assess_document_reception(document)
        self.assertEqual(assessment['state'], 'Ação')
        self.assertIn('Falta Entidade', assessment['reasons'])
        self.assertIn('Falta Fornecedor', assessment['reasons'])

    def test_home_preflight_ignores_later_department_required_fields(self):
        document_data = self.complete_invoice()
        document_data['invoice_type'] = 'unknown'
        document_data.pop('totals')
        document = SimpleNamespace(
            docinstamp='DOC-1', json_resultado=json.dumps(document_data),
            feid=1, fornecedor_no=10, processing_status='parsed_ok',
            processing_meta_json='{}', doc_type_detected='invoice',
            invoice_type='unknown',
        )
        configured = [
            'entity', 'supplier', 'classification', 'project', 'article',
            'origin', 'gross_total', 'tax_total', 'net_total', 'vehicle',
        ]
        with patch('services.document_ai_service.db.session.get', return_value=document), patch(
            'services.document_ai_service._enrich_supplier_classification',
            side_effect=lambda value, _feid: value,
        ), patch(
            'services.document_ai_service._refresh_document_duplicate_state', return_value=[]
        ), patch(
            'services.document_ai_required_info_service.required_fields_for', return_value=configured
        ), patch(
            'services.document_ai_distribution_service.assert_document_distribution_available'
        ):
            result = preflight_document_inbox_stage('DOC-1', 'home')

        self.assertTrue(result['ok'])
        self.assertEqual(result['required_info']['required'], ['entity', 'supplier', 'classification'])


if __name__ == '__main__':
    unittest.main()
