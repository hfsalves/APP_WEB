import unittest
from unittest.mock import patch

from services import document_ai_service


class ReconcileExtractedDocumentTests(unittest.TestCase):
    def test_replaces_llm_names_with_official_fe_and_fl_values(self):
        document = {
            'customer': {'name': 'Hsols France', 'tax_id': 'FR123456789'},
            'supplier': {'name': 'Vicat', 'tax_id': 'FR987654321'},
        }
        fe_match = {
            'feid': 7,
            'name': 'HSOLS FRANCE SAS',
            'tax_id': '123456789',
            'score': 0.99,
            'matched_by': 'tax_id',
        }
        supplier_match = {
            'no': 42,
            'name': 'VICAT SA',
            'tax_id': '987654321',
            'feid': 7,
            'score': 0.99,
            'matched_by': 'tax_id',
            'tax_field': 'nif',
        }

        with patch.object(document_ai_service, 'resolve_fe_entity', return_value=fe_match), patch.object(
            document_ai_service,
            'search_suppliers',
            return_value=[supplier_match],
        ) as search:
            result = document_ai_service.reconcile_extracted_document(document)

        self.assertEqual(result['document']['customer']['name'], 'HSOLS FRANCE SAS')
        self.assertEqual(result['document']['customer']['feid'], 7)
        self.assertEqual(result['document']['supplier']['name'], 'VICAT SA')
        self.assertEqual(result['document']['supplier']['supplier_no'], 42)
        self.assertTrue(result['matching']['supplier_matched'])
        self.assertTrue(all(call.kwargs['feid'] == 7 for call in search.call_args_list))

    def test_keeps_candidates_for_manual_choice_when_name_is_ambiguous(self):
        document = {
            'customer': {'name': 'Empresa Cliente'},
            'supplier': {'name': 'Alfa Construções'},
        }
        fe_match = {
            'feid': 3,
            'name': 'EMPRESA CLIENTE, LDA',
            'tax_id': '501000000',
            'score': 0.9,
            'matched_by': 'name',
        }
        candidates = [
            {'no': 10, 'name': 'ALFA CONSTRUÇÕES, LDA', 'tax_id': '', 'feid': 3, 'score': 0.69, 'matched_by': 'name'},
            {'no': 11, 'name': 'ALFA CONSTRUÇÃO SA', 'tax_id': '', 'feid': 3, 'score': 0.66, 'matched_by': 'name'},
        ]

        with patch.object(document_ai_service, 'resolve_fe_entity', return_value=fe_match), patch.object(
            document_ai_service,
            'search_suppliers',
            return_value=candidates,
        ):
            result = document_ai_service.reconcile_extracted_document(document)

        self.assertIsNone(result['document']['supplier']['supplier_no'])
        self.assertFalse(result['matching']['supplier_matched'])
        self.assertTrue(result['matching']['supplier_needs_selection'])
        self.assertEqual([item['no'] for item in result['matching']['supplier_candidates']], [10, 11])

    def test_rejects_weak_fe_name_match(self):
        weak_match = {
            'feid': 9,
            'name': 'OUTRA EMPRESA',
            'tax_id': '509000000',
            'score': 0.41,
            'matched_by': 'name',
        }
        document = {'customer': {'name': 'Nome pouco claro'}, 'supplier': {'name': 'Fornecedor'}}

        with patch.object(document_ai_service, 'resolve_fe_entity', return_value=weak_match), patch.object(
            document_ai_service,
            'search_suppliers',
        ) as search:
            result = document_ai_service.reconcile_extracted_document(document)

        self.assertFalse(result['matching']['customer_matched'])
        self.assertIsNone(result['matching']['supplier_query']['feid'])
        search.assert_not_called()

    def test_supplier_search_preserves_phc_ncont_source(self):
        suppliers = [{
            'NO': 88,
            'NOME': 'FOURNISSEUR EXEMPLE',
            'NIF': 'FR001122334',
            'FEID': 5,
            'TAX_FIELD': 'ncont',
            'SOURCE': 'phc',
        }]

        with patch.object(document_ai_service, '_load_suppliers', return_value=suppliers):
            result = document_ai_service.search_suppliers('001122334', feid=5)

        self.assertEqual(result[0]['no'], 88)
        self.assertEqual(result[0]['tax_field'], 'ncont')
        self.assertEqual(result[0]['source'], 'phc')


if __name__ == '__main__':
    unittest.main()
