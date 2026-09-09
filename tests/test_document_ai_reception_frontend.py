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

    def test_correspondence_number_is_refreshed_after_manual_header_correction(self):
        source = (Path(__file__).resolve().parents[1] / 'static/js/document_ai_extract.js').read_text(encoding='utf-8')
        refresh = source.split('async function refreshHeaderDependencies()', 1)[1].split('async function loadCorrespondenceReference()', 1)[0]
        self.assertIn('loadCorrespondenceReference()', refresh)
        self.assertIn('/workflow/preflight', refresh)
        self.assertIn('state.duplicateMatches = duplicates', refresh)
        correspondence = source.split('async function loadCorrespondenceReference()', 1)[1].split('function cleanupPreview()', 1)[0]
        self.assertIn('/api/document_ai/correspondence/next-reference', correspondence)
        self.assertIn('const integration = state.integrationResult || {};', source)
        self.assertIn('Correspondência por criar', source)


if __name__ == '__main__':
    unittest.main()
