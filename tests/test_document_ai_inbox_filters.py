import unittest
from pathlib import Path

from services.document_ai_service import (
    DOC_AI_INBOX_DOC_TYPES,
    _normalize_inbox_document_type,
    normalize_document_type,
)


ROOT = Path(__file__).resolve().parents[1]


class DocumentAiInboxFiltersTests(unittest.TestCase):
    def test_document_type_aliases_are_canonical(self):
        self.assertEqual(normalize_document_type('contract'), 'contract')
        self.assertEqual(normalize_document_type('Contrat'), 'contract')
        self.assertEqual(normalize_document_type('contrat sous-traitant'), 'subcontract')
        self.assertEqual(normalize_document_type('bon de livraison'), 'delivery_note')
        self.assertEqual(normalize_document_type('nota de crédito'), 'credit_note')

    def test_empty_filter_state_has_clear_action(self):
        source = (ROOT / 'static/js/document_ai_inbox.js').read_text(encoding='utf-8')
        self.assertIn('Sem documentos para os filtros selecionados.', source)
        self.assertIn('data-action="reset-filters"', source)

    def test_counts_keep_total_and_render_number_first(self):
        source = (ROOT / 'static/js/document_ai_inbox.js').read_text(encoding='utf-8')
        self.assertIn('const scopeTotal = state.total;', source)
        self.assertIn('const visibleTotal = state.filteredItems.length;', source)
        self.assertIn('${visibleTotal} de ${scopeTotal}', source)
        self.assertIn('<strong>${count}</strong><span>${escapeHtml(value)}</span>', source)
        self.assertIn("<strong>${data.count}</strong><span>${escapeHtml(data.label || '-')}</span>", source)

    def test_document_type_counters_hide_zero_counts(self):
        source = (ROOT / 'static/js/document_ai_inbox.js').read_text(encoding='utf-8')
        self.assertIn('const counts = new Map();', source)
        self.assertIn('.filter(([, data]) => data.count > 0)', source)
        self.assertNotIn('options.map((option) => [String(option.value), { count: 0', source)

    def test_tp068_has_only_date_until_and_no_value_range(self):
        template = (ROOT / 'templates/document_ai_inbox.html').read_text(encoding='utf-8')
        source = (ROOT / 'static/js/document_ai_inbox.js').read_text(encoding='utf-8')
        self.assertIn('id="docAiDocumentDateTo"', template)
        for obsolete in ('docAiDocumentDateFrom', 'docAiValueMin', 'docAiValueMax'):
            self.assertNotIn(obsolete, template)
            self.assertNotIn(obsolete, source)

    def test_tp068_uses_singular_state_and_simple_state_tooltips(self):
        source = (ROOT / 'static/js/document_ai_inbox.js').read_text(encoding='utf-8')
        self.assertIn('<span class="docai-business-count-title">Estado</span>', source)
        self.assertNotIn('<span class="docai-business-count-title">Estados</span>', source)
        self.assertIn('title="${escapeHtml(value)}" aria-label="${escapeHtml(value)}"', source)

    def test_tp068_filters_never_expose_legacy_or_technical_types(self):
        visible_values = {item['value'] for item in DOC_AI_INBOX_DOC_TYPES}
        self.assertTrue({'invoice', 'credit_note', 'mail'}.issubset(visible_values))
        self.assertTrue({'provisional_invoice', 'proforma_invoice', 'other', 'debit_note'}.isdisjoint(visible_values))
        self.assertEqual(_normalize_inbox_document_type('provisional_invoice'), 'invoice')
        self.assertEqual(_normalize_inbox_document_type('proforma_invoice'), 'invoice')
        self.assertEqual(_normalize_inbox_document_type('debit_note'), 'unknown')
        self.assertEqual(_normalize_inbox_document_type('other'), 'unknown')

    def test_column_filter_click_does_not_immediately_close_the_redrawn_menu(self):
        source = (ROOT / 'static/js/document_ai_inbox.js').read_text(encoding='utf-8')
        listener = source[source.index("host.addEventListener('click'"):source.index("host.addEventListener('input'")]
        self.assertIn('event.stopPropagation();', listener)

    def test_column_filter_search_updates_only_options_and_keeps_input_node(self):
        source = (ROOT / 'static/js/document_ai_inbox.js').read_text(encoding='utf-8')
        listener = source[source.index("host.addEventListener('input'"):source.index("document.addEventListener('click'")]
        self.assertIn('renderColumnFilterOptions(host.dataset.filter);', listener)
        self.assertNotIn('renderColumnFilter(host.dataset.filter)', listener)

    def test_only_document_types_are_horizontally_scrollable(self):
        source = (ROOT / 'static/js/document_ai_inbox.js').read_text(encoding='utf-8')
        css = (ROOT / 'static/css/document_ai.css').read_text(encoding='utf-8')
        self.assertIn('docai-business-count-states', source)
        self.assertIn('class="docai-counts-types" tabindex="0"', source)
        self.assertIn('${documentTypeGroup}', source)
        self.assertIn('class="docai-counts-invoice"', source)
        self.assertNotIn("typeGroups.join('')", source)
        self.assertIn('bindTypeCounterScroller();', source)
        self.assertIn("scroller.addEventListener('pointermove'", source)
        self.assertIn("scroller.addEventListener('wheel'", source)
        self.assertIn("scroller.addEventListener('keydown'", source)
        self.assertIn('.docai-counts-types::-webkit-scrollbar', css)
        self.assertIn('.docai-counts.has-invoice-type', css)
        self.assertNotIn('.docai-counts {\n    grid-template-columns: max-content minmax(12rem, 1fr) 7.5rem;\n    overflow-x: auto;', css)

    def test_counter_titles_are_horizontal_and_table_has_no_global_horizontal_scroll(self):
        source = (ROOT / 'static/js/document_ai_inbox.js').read_text(encoding='utf-8')
        css = (ROOT / 'static/css/document_ai.css').read_text(encoding='utf-8')
        self.assertNotIn('writing-mode: vertical-rl', css)
        self.assertNotIn('min-width: 78rem', css)
        self.assertIn('overflow-x: hidden', css)
        self.assertIn('flex: 0 0 auto', css)
        self.assertIn('flex: 1 1 auto', css)
        self.assertIn('class="docai-cell-ellipsis"', source)
        self.assertIn('title="${escapeHtml(text)}"', source)
        self.assertIn('aria-label="${escapeHtml(text)}"', source)

    def test_action_column_is_accessible_and_sticky_on_the_right(self):
        template = (ROOT / 'templates/document_ai_inbox.html').read_text(encoding='utf-8')
        css = (ROOT / 'static/css/document_ai.css').read_text(encoding='utf-8')
        self.assertIn('title="Ação" aria-label="Ação"', template)
        action_rules = css.split('.docai-inbox-table-panel .sz_table th:last-child,', 1)[1].split('@media', 1)[0]
        self.assertIn('position: sticky;', action_rules)
        self.assertIn('right: 0;', action_rules)

    def test_total_card_width_and_result_line_are_fixed_at_all_resolutions(self):
        css = (ROOT / 'static/css/document_ai.css').read_text(encoding='utf-8')
        self.assertIn('.docai-filtered-total .count {\n  white-space: nowrap;', css)
        self.assertGreaterEqual(css.count('min-width: 7.5rem;'), 2)
        self.assertNotIn('.docai-filtered-total {\n    width: 100%;', css)
        self.assertNotIn('minmax(10.75rem, 1fr) 5.125rem', css)

    def test_required_groups_and_entity_scope_match_tp051(self):
        required = (ROOT / 'static/js/document_ai_required_info.js').read_text(encoding='utf-8')
        access = (ROOT / 'static/js/document_ai_access.js').read_text(encoding='utf-8')
        template = (ROOT / 'templates/document_ai_inbox.html').read_text(encoding='utf-8')
        self.assertIn('data-toggle-required=', required)
        self.assertIn("fa-${open ? 'minus' : 'plus'}", required)
        self.assertIn('${rules.length}', required)
        self.assertIn('id="docAiAccessAllEntities" type="radio"', template)
        self.assertIn('id="docAiAccessSpecificEntities" type="radio"', template)
        self.assertIn('els.specificEntityPanel.hidden = entityDraft.all_entities;', access)
        self.assertIn('const permissionsByView = {', access)


if __name__ == '__main__':
    unittest.main()
