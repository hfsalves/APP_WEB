import unittest
from pathlib import Path


class DocumentAiInboxFrontendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (Path(__file__).resolve().parents[1] / 'static/js/document_ai_inbox.js').read_text(encoding='utf-8')

    def test_total_uses_unfiltered_server_scope(self):
        self.assertIn('const total = state.total;', self.source)
        self.assertNotIn('const total = state.allItems.filter((item) => matchesFilters(item)).length;', self.source)

    def test_currency_uses_accounting_number_and_real_code(self):
        self.assertIn("return code ? `${formatted} ${code}` : formatted;", self.source)

    def test_filtering_does_not_reset_scroll_by_default(self):
        self.assertIn('function applyFilters({ resetScroll = false } = {})', self.source)
        self.assertIn('if (resetScroll && els.tableScroller)', self.source)


if __name__ == '__main__':
    unittest.main()
