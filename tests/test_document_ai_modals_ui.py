import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class DocumentAiModalsUiTests(unittest.TestCase):
    def test_tax_modal_uses_requested_title_and_total_row(self):
        template = (ROOT / 'templates' / 'document_ai_extract.html').read_text(encoding='utf-8')
        script = (ROOT / 'static' / 'js' / 'document_ai_extract.js').read_text(encoding='utf-8')

        self.assertIn('Detalhe IVA', template)
        self.assertNotIn('Detalhe dos totais', template)
        self.assertIn('docai-tax-total-row', script)

    def test_origin_detail_always_keeps_registration_column(self):
        script = (ROOT / 'static' / 'js' / 'document_ai_extract.js').read_text(encoding='utf-8')

        self.assertIn('<th>Matrícula</th><th>Data</th>', script)
        self.assertNotIn("showRegistration ? '<th>Matrícula</th>'", script)

    def test_secondary_settings_modals_close_with_escape(self):
        required = (ROOT / 'static' / 'js' / 'document_ai_required_info.js').read_text(encoding='utf-8')
        distribution = (ROOT / 'static' / 'js' / 'document_ai_distribution.js').read_text(encoding='utf-8')

        self.assertIn("event.key === 'Escape'", required)
        self.assertIn("event.key === 'Escape'", distribution)


if __name__ == '__main__':
    unittest.main()
