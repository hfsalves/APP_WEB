import unittest
from pathlib import Path


class DocumentAiReceptionFrontendTests(unittest.TestCase):
    def test_workflow_validation_does_not_trigger_legacy_phc_flow(self):
        source = (Path(__file__).resolve().parents[1] / 'static/js/document_ai_extract.js').read_text(encoding='utf-8')
        start = source.index('async function validateWorkflowStage')
        end = source.index("els.backBtn?.addEventListener", start)
        workflow = source[start:end]
        self.assertNotIn('submitDocumentToPhc', workflow)
        self.assertNotIn('confirmDocumentControl', workflow)
        self.assertNotIn('saveWorkflowCorrections', workflow)
        self.assertIn('/workflow/preflight', workflow)
        self.assertIn('/workflow/validate', workflow)


if __name__ == '__main__':
    unittest.main()
