import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class DocumentAiOriginDetailsUiTests(unittest.TestCase):
    def test_detail_table_has_dynamic_origin_headers(self):
        template = (ROOT / 'templates' / 'document_ai_extract.html').read_text(encoding='utf-8')
        script = (ROOT / 'static' / 'js' / 'document_ai_extract.js').read_text(encoding='utf-8')

        self.assertIn('docAiExtractPrimaryOriginHead', template)
        self.assertIn('docAiExtractSecondaryOriginHead', template)
        self.assertIn("'Contrato ST'", script)
        self.assertIn("'Situação de Trabalho'", script)

    def test_delivery_note_proposals_are_compact_and_selectable(self):
        script = (ROOT / 'static' / 'js' / 'document_ai_extract.js').read_text(encoding='utf-8')

        self.assertIn('docai-extract-origin-proposal', script)
        self.assertIn('data-virtual-bl', script)
        self.assertNotIn('Virtual — ainda não existe no PHC', script)
        self.assertNotIn('Sugestão · a criar', script)


if __name__ == '__main__':
    unittest.main()
