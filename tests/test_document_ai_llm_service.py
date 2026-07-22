import unittest
from unittest.mock import patch

from services import document_ai_llm_service as llm_service


class DocumentAiLlmServiceTests(unittest.TestCase):
    def test_full_extraction_schema_accepts_extended_document_types(self):
        schema = llm_service._document_full_extraction_schema()

        self.assertEqual(schema['properties']['document_type'], {'type': 'string'})
        self.assertIn('external_party_role', schema['required'])
        self.assertIn('mail_category', schema['required'])
        self.assertIn('mail_title', schema['required'])
        self.assertEqual(schema['properties']['mail_title']['maxLength'], 25)
        self.assertEqual(
            schema['properties']['external_party_role']['enum'],
            ['supplier', 'customer', 'unknown'],
        )
        self.assertEqual(schema['properties']['mail_category']['enum'], ['legal', 'general', 'unknown'])
        self.assertFalse(schema['properties']['lines']['items']['additionalProperties'])
        self.assertIn('origin_references', schema['required'])
        self.assertIn(
            'origin_delivery_note_number',
            schema['properties']['lines']['items']['required'],
        )
        self.assertEqual(
            schema['properties']['taxes']['items']['required'],
            ['tax_rate', 'taxable_base', 'tax_amount', 'gross_total'],
        )
        batch = schema['properties']['document_batch']
        self.assertIn('document_batch', schema['required'])
        self.assertFalse(batch['additionalProperties'])
        self.assertIn('start_page', batch['properties']['documents']['items']['required'])
        self.assertIn('end_page', batch['properties']['documents']['items']['required'])
        self.assertIn('supplier_name', batch['properties']['documents']['items']['required'])
        self.assertIn('supplier_tax_id', batch['properties']['documents']['items']['required'])

    def test_mail_title_is_normalized_to_25_characters(self):
        document = {
            'document_type': 'mail',
            'mail_title': '  Mise   en demeure avec pénalités supplémentaires  ',
            'lines': [],
        }

        normalized = llm_service._normalize_full_extraction_line_origins(document)

        self.assertEqual(normalized['mail_title'], 'Mise en demeure avec')
        self.assertLessEqual(len(normalized['mail_title']), 25)

    def test_full_visual_extraction_enables_full_mode(self):
        captured = {}

        def fake_classify(context):
            captured.update(context)
            return {
                'ok': True,
                'available': True,
                'classification': {'document_number': 'FT 1'},
                'model': 'test-model',
            }

        with patch.object(llm_service, '_pdf_page_count', return_value=3), patch.object(
            llm_service,
            'classify_document_visual',
            fake_classify,
        ):
            result = llm_service.extract_document_full_visual({
                'file_name': 'fatura.pdf',
                'file_bytes': b'%PDF-test',
            })

        self.assertTrue(captured['full_extraction'])
        self.assertEqual(captured['page_count'], 3)
        self.assertEqual(captured['file_name'], 'fatura.pdf')
        self.assertEqual(result['document']['document_number'], 'FT 1')
        self.assertEqual(result['document']['document_batch']['page_count'], 3)
        self.assertFalse(result['document']['document_batch']['contains_multiple_documents'])
        self.assertNotIn('classification', result)

    def test_normalizes_multiple_document_boundaries(self):
        document = {
            'document_type': 'delivery_note',
            'document_number': 'G1',
            'confidence': 0.9,
            'document_batch': {
                'page_count': 35,
                'contains_multiple_documents': True,
                'document_count': 3,
                'message': 'raw',
                'documents': [
                    {'start_page': 1, 'document_type': 'delivery_note', 'document_number': 'G1', 'confidence': 0.9},
                    {'start_page': 3, 'document_type': 'delivery_note', 'document_number': 'G2', 'confidence': 0.8},
                    {'start_page': 6, 'document_type': 'delivery_note', 'document_number': 'G3', 'confidence': 0.85},
                ],
            },
        }

        batch = llm_service._normalize_document_batch(document, 8)

        self.assertTrue(batch['contains_multiple_documents'])
        self.assertEqual(batch['document_count'], 3)
        self.assertEqual(
            [(item['start_page'], item['end_page']) for item in batch['documents']],
            [(1, 2), (3, 5), (6, 8)],
        )
        self.assertIn('1, 3, 6', batch['message'])

    def test_delivery_note_is_removed_from_article_reference(self):
        document = {
            'origin_references': [{
                'document_type': 'delivery_note',
                'document_number': '516006108',
            }],
            'lines': [{
                'ref': '516006108',
                'origin_delivery_note_number': '516006108',
                'description': 'Ciment CEM II',
            }],
        }

        normalized = llm_service._normalize_full_extraction_line_origins(document)

        self.assertEqual(normalized['lines'][0]['ref'], '')
        self.assertEqual(
            normalized['lines'][0]['origin_delivery_note_number'],
            '516006108',
        )

    def test_delivery_note_from_origins_is_moved_out_of_reference(self):
        document = {
            'origin_references': [{
                'document_type': 'delivery_note',
                'document_number': 'BL-516006110',
            }],
            'lines': [{
                'ref': 'BL 516006110',
                'origin_delivery_note_number': '',
                'description': 'Transport',
            }],
        }

        normalized = llm_service._normalize_full_extraction_line_origins(document)

        self.assertEqual(normalized['lines'][0]['ref'], '')
        self.assertEqual(
            normalized['lines'][0]['origin_delivery_note_number'],
            'BL 516006110',
        )

    def test_genuine_article_reference_is_preserved(self):
        document = {
            'origin_references': [{
                'document_type': 'delivery_note',
                'document_number': '516006108',
            }],
            'lines': [{
                'ref': 'ART-CEM-II',
                'origin_delivery_note_number': '516006108',
                'description': 'Ciment CEM II',
            }],
        }

        normalized = llm_service._normalize_full_extraction_line_origins(document)

        self.assertEqual(normalized['lines'][0]['ref'], 'ART-CEM-II')
        self.assertEqual(
            normalized['lines'][0]['origin_delivery_note_number'],
            '516006108',
        )

    def test_full_visual_extraction_preserves_error(self):
        failed_result = {
            'ok': False,
            'available': False,
            'message': 'Sem chave API.',
            'classification': None,
        }
        with patch.object(llm_service, 'classify_document_visual', return_value=failed_result):
            result = llm_service.extract_document_full_visual({'file_name': 'fatura.pdf'})

        self.assertFalse(result['ok'])
        self.assertIsNone(result['document'])
        self.assertEqual(result['message'], 'Sem chave API.')


if __name__ == '__main__':
    unittest.main()
