import unittest
from pathlib import Path


class DocumentAiInboxFrontendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (Path(__file__).resolve().parents[1] / 'static/js/document_ai_inbox.js').read_text(encoding='utf-8')

    def test_total_uses_unfiltered_server_scope(self):
        self.assertIn('const scopeTotal = state.total;', self.source)
        self.assertIn('const visibleTotal = state.filteredItems.length;', self.source)
        self.assertNotIn('const total = state.allItems.filter((item) => matchesFilters(item)).length;', self.source)

    def test_total_card_has_the_required_two_line_order(self):
        card = self.source.split('class="docai-count-card docai-count-card-action docai-filtered-total"', 1)[1].split('</button>', 1)[0]
        self.assertLess(card.index('<span class="label">Total</span>'), card.index('<span class="count">${visibleTotal} de ${scopeTotal}</span>'))

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
        self.assertIn("const documentTypeGroup = counterGroup('Tipo de documento'", self.source)
        self.assertIn("const invoiceTypeGroup = state.view !== 'home'", self.source)
        self.assertNotIn("state.view !== 'management'", self.source)

    def test_invoice_type_counts_only_invoices_and_hides_empty_unknown(self):
        self.assertIn("filterName !== 'invoice_type' || String(item.document_type || 'unknown') === 'invoice'", self.source)
        self.assertIn('.filter(([, data]) => data.count > 0)', self.source)
        self.assertIn('const counts = new Map();', self.source)

    def test_each_view_has_the_expected_counter_groups(self):
        self.assertIn("const documentTypeGroup = counterGroup('Tipo de documento'", self.source)
        self.assertIn("const invoiceTypeGroup = state.view !== 'home'", self.source)

    def test_rows_open_analysis_and_restore_list_position(self):
        self.assertNotIn('data-action="extract"', self.source)
        self.assertIn('tabindex="0" role="button" aria-label="Analisar"', self.source)
        self.assertIn("if (!['Enter', ' '].includes(event.key)", self.source)
        self.assertIn('scrollTop: els.tableScroller?.scrollTop || 0', self.source)
        self.assertIn('scrollLeft: els.tableScroller?.scrollLeft || 0', self.source)

    def test_archive_rows_open_the_read_only_analysis_route(self):
        self.assertIn("if (state.archived) params.set('archive', '1')", self.source)
        self.assertIn("state.archived ? state.permissions.consult : state.permissions.analyze", self.source)

    def test_archive_hides_new_document_even_with_create_permission(self):
        self.assertIn('els.uploadBtn.hidden = state.archived || !state.permissions.create;', self.source)

    def test_each_filter_change_persists_the_same_visible_dataset(self):
        apply_filters = self.source.split('function applyFilters', 1)[1].split('function renderViewTabs', 1)[0]
        self.assertIn('renderTable();', apply_filters)
        self.assertIn('saveNavigationState(state.activeDocumentId);', apply_filters)

    def test_counter_selection_applies_immediately_and_exposes_active_state(self):
        listener = self.source.split("els.counts?.addEventListener('click'", 1)[1].split("els.refreshBtn?", 1)[0]
        self.assertIn('target.has(value) ? target.delete(value) : target.add(value);', listener)
        self.assertIn('applyFilters();', listener)
        self.assertIn("selected.has(value) ? 'is-active' : ''", self.source)
        self.assertIn("aria-pressed=\"${selected.has(value) ? 'true' : 'false'}\"", self.source)

    def test_document_type_scroller_does_not_capture_filter_button_clicks(self):
        scroller = self.source.split('function bindTypeCounterScroller()', 1)[1].split('function applyFilters', 1)[0]
        self.assertIn("event.target.closest('button, a, input, select')", scroller)
        self.assertLess(
            scroller.index("event.target.closest('button, a, input, select')"),
            scroller.index('scroller.setPointerCapture(pointerId)'),
        )

    def test_row_highlight_includes_the_sticky_action_cell(self):
        css = (Path(__file__).resolve().parents[1] / 'static/css/document_ai.css').read_text(encoding='utf-8')
        self.assertIn('.docai-inbox-row.is-interactive:hover > td:last-child,', css)
        self.assertIn('.docai-inbox-row.is-returned > td:last-child', css)


if __name__ == '__main__':
    unittest.main()
