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

    def test_document_and_invoice_type_are_independent_counter_filters(self):
        self.assertIn("counterGroup('Tipo de documento', 'document_type'", self.source)
        self.assertIn("counterGroup('Tipo de fatura', 'invoice_type'", self.source)
        self.assertIn("excludedField !== 'document_type'", self.source)
        self.assertIn("excludedField !== 'invoice_type'", self.source)

    def test_management_keeps_document_type_and_invoice_type_counters(self):
        self.assertIn("typeGroups.push(counterGroup('Tipo de documento'", self.source)
        self.assertNotIn("state.view !== 'management') typeGroups.push", self.source)

    def test_invoice_type_counts_only_invoices_and_hides_empty_unknown(self):
        self.assertIn("filterName !== 'invoice_type' || String(item.document_type || 'unknown') === 'invoice'", self.source)
        self.assertIn("value !== 'unknown' || data.count > 0", self.source)
        self.assertIn("options.map((option) => [String(option.value), { count: 0", self.source)

    def test_each_view_has_the_expected_counter_groups(self):
        self.assertIn("typeGroups.push(counterGroup('Tipo de documento'", self.source)
        self.assertIn("if (state.view !== 'home')", self.source)

    def test_rows_open_analysis_and_restore_list_position(self):
        self.assertNotIn('data-action="extract"', self.source)
        self.assertIn('tabindex="0" role="button" aria-label="Analisar"', self.source)
        self.assertIn("if (!['Enter', ' '].includes(event.key)", self.source)
        self.assertIn('scrollTop: els.tableScroller?.scrollTop || 0', self.source)
        self.assertIn('scrollLeft: els.tableScroller?.scrollLeft || 0', self.source)

    def test_archive_rows_open_the_read_only_analysis_route(self):
        self.assertIn("if (state.archived) params.set('archive', '1')", self.source)
        self.assertIn("state.archived ? state.permissions.consult : state.permissions.analyze", self.source)


if __name__ == '__main__':
    unittest.main()
