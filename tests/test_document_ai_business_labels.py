import unittest
from pathlib import Path

from services.document_ai_service import DOC_AI_DOC_TYPES, DOC_AI_INTEGRATION_ACCESS_TYPES


ROOT = Path(__file__).resolve().parents[1]


class DocumentAiBusinessLabelsTests(unittest.TestCase):
    def test_document_type_labels_use_business_nomenclature(self):
        labels = {item['value']: item['label'] for item in DOC_AI_DOC_TYPES}
        self.assertEqual(labels['purchase_order'], 'Nota de Encomenda')
        self.assertEqual(labels['delivery_note'], 'Guia de Remessa')
        self.assertEqual(labels['subcontract'], 'Contrato de SubEmpreitada')
        self.assertEqual(labels['provisional_invoice'], 'Fatura Provisória')

    def test_integration_settings_use_business_labels(self):
        labels = {key: label for key, label, _column in DOC_AI_INTEGRATION_ACCESS_TYPES}
        self.assertEqual(labels['purchase_order'], 'Nota de Encomenda')
        self.assertEqual(labels['delivery_note'], 'Guia de Remessa')
        self.assertEqual(labels['proforma_invoice'], 'Pré-Fatura')

    def test_compact_table_headers_use_defined_abbreviations(self):
        template = (ROOT / 'templates/document_ai_extract.html').read_text(encoding='utf-8')
        script = (ROOT / 'static/js/document_ai_extract.js').read_text(encoding='utf-8')
        self.assertIn('>NdE</th>', template)
        self.assertIn('>GdR</th>', template)
        self.assertIn("'C Sub.Emp.'", script)
        self.assertIn("'SdT Sub.Emp.'", script)

    def test_ged_prefixes_remain_unchanged(self):
        script = (ROOT / 'static/js/document_ai_extract.js').read_text(encoding='utf-8')
        self.assertIn("prefix = 'BL';", script)
        self.assertIn("prefix = 'BC';", script)


if __name__ == '__main__':
    unittest.main()
