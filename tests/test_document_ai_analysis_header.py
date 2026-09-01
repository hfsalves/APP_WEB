import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DocumentAiAnalysisHeaderTests(unittest.TestCase):
    def test_header_uses_confirmed_or_pending_correspondence(self):
        source = (ROOT / 'static/js/document_ai_extract.js').read_text(encoding='utf-8')
        self.assertIn('Correspondência n.º ${state.correspondenceReference} · ${state.correspondenceYear}', source)
        self.assertIn("els.correspondenceReference.textContent = 'Correspondência por criar'", source)

    def test_saved_reading_meta_is_not_rendered_in_header(self):
        source = (ROOT / 'static/js/document_ai_extract.js').read_text(encoding='utf-8')
        self.assertNotIn('els.resultMeta.textContent = `Leitura guardada', source)
        self.assertIn("els.resultMeta.textContent = '';", source)
        self.assertIn('els.resultMeta.hidden = true;', source)

    def test_workflow_validation_is_in_analysis_header_and_uses_view_label(self):
        template = (ROOT / 'templates/document_ai_extract.html').read_text(encoding='utf-8')
        source = (ROOT / 'static/js/document_ai_extract.js').read_text(encoding='utf-8')
        header_start = template.index('<section class="sz_panel docai-extract-result-panel">')
        header_end = template.index('<nav id="docAiExtractGroupNavigator"', header_start)
        self.assertIn('id="docAiExtractWorkflowValidateBtn"', template[header_start:header_end])
        self.assertIn("home: 'Receção'", source)
        self.assertIn("management: 'Controlo'", source)
        self.assertIn("accounting: 'Contabilidade'", source)
        self.assertIn('`Validar ${viewLabel}`', source)

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
