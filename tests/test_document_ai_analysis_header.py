import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DocumentAiAnalysisHeaderTests(unittest.TestCase):
    def test_header_uses_confirmed_or_pending_correspondence(self):
        source = (ROOT / 'static/js/document_ai_extract.js').read_text(encoding='utf-8')
        self.assertIn('Correspondência n.º ${state.correspondenceReference} · ${state.correspondenceYear}', source)
        self.assertIn("els.correspondenceReference.textContent = 'Correspondência por criar'", source)

    def test_saved_reading_meta_is_compact(self):
        source = (ROOT / 'static/js/document_ai_extract.js').read_text(encoding='utf-8')
        self.assertIn('els.resultMeta.textContent = `Leitura guardada · ${language}`', source)
        self.assertNotIn('Leitura guardada · ${language}${batchSuffix}', source)

    def test_requested_technical_messages_are_hidden(self):
        source = (ROOT / 'static/js/document_ai_extract.js').read_text(encoding='utf-8')
        self.assertIn('Leitura guardada carregada do inbox', source)
        self.assertIn('Filtro de obra .* aplicado às origens', source)
        self.assertIn('els.status.hidden = !visibleMessage', source)

    def test_row_actions_have_stable_square_dimensions(self):
        css = (ROOT / 'static/css/document_ai.css').read_text(encoding='utf-8')
        self.assertIn('width: 2.25rem;', css)
        self.assertIn('height: 2.25rem;', css)
        self.assertIn('table-layout: fixed;', css)


if __name__ == '__main__':
    unittest.main()
