import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class DocumentAiOriginDetailsUiTests(unittest.TestCase):
    def test_detail_table_has_dynamic_origin_headers(self):
        template = (ROOT / 'templates' / 'document_ai_extract.html').read_text(encoding='utf-8')
        script = (ROOT / 'static' / 'js' / 'document_ai_extract.js').read_text(encoding='utf-8')

        self.assertIn('docAiExtractPrimaryOriginHead', template)
        self.assertIn('docAiExtractSecondaryOriginHead', template)
        self.assertIn("'C Sub.Emp.'", script)
        self.assertIn("'SdT Sub.Emp.'", script)

    def test_delivery_note_proposals_are_compact_and_selectable(self):
        script = (ROOT / 'static' / 'js' / 'document_ai_extract.js').read_text(encoding='utf-8')

        self.assertIn('docai-extract-origin-proposal', script)
        self.assertIn('data-virtual-bl', script)
        self.assertNotIn('Virtual — ainda não existe no PHC', script)
        self.assertNotIn('Sugestão · a criar', script)

    def test_origin_header_uses_one_contextual_action(self):
        template = (ROOT / 'templates' / 'document_ai_extract.html').read_text(encoding='utf-8')
        script = (ROOT / 'static' / 'js' / 'document_ai_extract.js').read_text(encoding='utf-8')

        self.assertIn('docAiExtractOriginAction', template)
        self.assertNotIn('docAiExtractOriginSource', template)
        self.assertIn('function originContextAction()', script)
        self.assertIn('registerDocumentAiOriginAction', script)
        self.assertIn('originActionHandlers.has(action.key)', script)
        for label in (
            'Criar Nota de Encomenda', 'Corrigir Nota de Encomenda', 'Criar Contrato',
            'Criar Contrato Sub.Emp.', 'Distribuir GdR', 'Criar GdR', 'Criar STSE',
        ):
            self.assertIn(label, script)


if __name__ == '__main__':
    unittest.main()
