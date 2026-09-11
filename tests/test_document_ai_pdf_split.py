import io
import unittest
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from services.document_ai_service import (
    _safe_split_file_part,
    _split_document_prefix,
    _split_pdf_parts,
)


def _blank_pdf(page_count: int) -> bytes:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=595, height=842)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


class DocumentAiPdfSplitTests(unittest.TestCase):
    def test_splits_using_llm_start_pages_and_recomputes_end_pages(self):
        source = _blank_pdf(8)
        batch = {
            'documents': [
                {'start_page': 1, 'end_page': 1, 'document_type': 'delivery_note', 'document_number': 'G1'},
                {'start_page': 3, 'end_page': 3, 'document_type': 'delivery_note', 'document_number': 'G2'},
                {'start_page': 6, 'end_page': 6, 'document_type': 'invoice', 'document_number': 'F3'},
            ],
        }

        parts = _split_pdf_parts(source, batch)

        self.assertEqual([(item['start_page'], item['end_page']) for item in parts], [(1, 2), (3, 5), (6, 8)])
        self.assertEqual([len(PdfReader(io.BytesIO(item['pdf_bytes'])).pages) for item in parts], [2, 3, 3])

    def test_rejects_boundaries_without_page_one(self):
        with self.assertRaisesRegex(ValueError, 'fronteiras'):
            _split_pdf_parts(_blank_pdf(4), {'documents': [{'start_page': 2}, {'start_page': 3}]})

    def test_builds_requested_prefixes_and_safe_name_parts(self):
        self.assertEqual(_split_document_prefix('delivery_note'), 'BL')
        self.assertEqual(_split_document_prefix('invoice'), 'FAC')
        self.assertEqual(_safe_split_file_part('Vicat S.A. / France', 'FORNECEDOR'), 'Vicat_S_A_France')

    def test_children_keep_real_pdf_hash_and_batch_is_audit_only(self):
        service = Path('services/document_ai_service.py').read_text(encoding='utf-8')
        split_block = service.split('def split_extracted_pdf_into_inbox(', 1)[1].split(
            'def _create_inbox_document_from_stored_file(', 1
        )[0]

        self.assertIn('file_hash=content_hash', split_block)
        self.assertNotIn('unique_hash', split_block)
        self.assertIn("'batch_audit': group", split_block)
        self.assertIn("'audit_only': True", service)

    def test_frontend_has_no_batch_document_navigator(self):
        template = Path('templates/document_ai_extract.html').read_text(encoding='utf-8')
        script = Path('static/js/document_ai_extract.js').read_text(encoding='utf-8')

        self.assertNotIn('docAiExtractGroupNavigator', template)
        self.assertNotIn('Documento 1 de 1', template)
        self.assertNotIn('renderGroupNavigator', script)
        self.assertNotIn('/group`', script)
        self.assertIn('payload.batch_audit?.documents', script)


if __name__ == '__main__':
    unittest.main()
