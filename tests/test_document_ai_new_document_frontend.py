from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DocumentAiNewDocumentFrontendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inbox_script = (ROOT / 'static/js/document_ai_inbox.js').read_text(encoding='utf-8')
        cls.extract_script = (ROOT / 'static/js/document_ai_extract.js').read_text(encoding='utf-8')
        cls.extract_template = (ROOT / 'templates/document_ai_extract.html').read_text(encoding='utf-8')

    def test_new_document_opens_empty_analysis_instead_of_file_picker(self):
        self.assertIn("window.location.href = analysisUrl('');", self.inbox_script)
        self.assertNotIn("els.uploadBtn?.addEventListener('click', () => els.uploadInput?.click())", self.inbox_script)

    def test_empty_analysis_only_processes_after_file_selection(self):
        self.assertIn("els.input?.addEventListener('change', (event) => setFile(event.target.files?.[0]))", self.extract_script)
        self.assertIn("window.setTimeout(() => extractDocument(), 0)", self.extract_script)
        self.assertIn("formData.append('document_id', state.currentDocumentId || '')", self.extract_script)

    def test_pending_correspondence_has_business_label(self):
        self.assertIn('Correspondência por criar', self.extract_template)
        self.assertNotIn('Correspondência por atribuir', self.extract_template)
        self.assertNotIn('Correspondência por atribuir', self.extract_script)


if __name__ == '__main__':
    unittest.main()
