import unittest
from pathlib import Path


class DocumentAiDeliveryNoteFrontendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.template = (root / 'templates/document_ai_extract.html').read_text(encoding='utf-8')
        cls.script = (root / 'static/js/document_ai_extract.js').read_text(encoding='utf-8')

    def test_only_distribution_action_is_exposed(self):
        self.assertNotIn('docAiExtractSuggestBlsBtn', self.template)
        self.assertNotIn('Sugerir BL', self.template)
        self.assertIn('docAiExtractSplitLineBtn', self.template)
        self.assertIn('Distribuir Guia de Remessa', self.template)

    def test_delivery_note_suggestions_are_activated_automatically(self):
        self.assertIn(
            'state.virtualDeliveryNotesActive = state.deliveryNoteGroups.length > 0;',
            self.script,
        )
        self.assertNotIn('function suggestVirtualDeliveryNotes()', self.script)

    def test_distribution_label_counts_delivery_note_groups(self):
        self.assertIn('proportionalGroups.length === 1', self.script)
        self.assertIn('`Distribuir ${proportionalGroups.length} Guias de Remessa`', self.script)


if __name__ == '__main__':
    unittest.main()
