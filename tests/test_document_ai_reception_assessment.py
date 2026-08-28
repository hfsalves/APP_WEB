import unittest

from services.document_ai_service import assess_document_reception


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

    def test_invoice_type_is_required_only_for_invoice(self):
        invoice = self.complete_invoice()
        invoice['invoice_type'] = 'unknown'
        self.assertEqual(assess_document_reception(invoice)['state'], 'Ação')
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

    def test_missing_entity_and_supplier_have_separate_reasons(self):
        document = self.complete_invoice()
        document['customer'] = {}
        document['supplier'] = {}
        assessment = assess_document_reception(document)
        self.assertEqual(assessment['state'], 'Ação')
        self.assertIn('Falta Entidade', assessment['reasons'])
        self.assertIn('Falta Fornecedor', assessment['reasons'])


if __name__ == '__main__':
    unittest.main()
