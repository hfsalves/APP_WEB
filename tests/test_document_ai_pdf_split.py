import io
import unittest

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


if __name__ == '__main__':
    unittest.main()
