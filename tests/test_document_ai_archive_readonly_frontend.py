import unittest
from pathlib import Path


class DocumentAiArchiveReadonlyFrontendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.source = (root / 'static/js/document_ai_extract.js').read_text(encoding='utf-8')
        cls.template = (root / 'templates/document_ai_extract.html').read_text(encoding='utf-8')

    def test_template_exposes_server_controlled_read_only_mode(self):
        self.assertIn('data-read-only="{{ \'1\' if document_ai_read_only else \'0\' }}"', self.template)

    def test_archive_loads_existing_result_without_triggering_ai(self):
        self.assertIn('setFile(file, { autoExtract: !state.readOnly })', self.source)
        self.assertIn('detail.result || cached.document || {}', self.source)

    def test_read_only_mode_never_autosaves_and_returns_to_archive(self):
        self.assertIn('if (state.readOnly) return Promise.resolve(true);', self.source)
        self.assertIn("if (state.readOnly) params.set('archived', '1')", self.source)

    def test_original_pdf_request_preserves_archive_scope(self):
        self.assertIn("state.readOnly ? '&archive=1' : ''", self.source)


if __name__ == '__main__':
    unittest.main()
