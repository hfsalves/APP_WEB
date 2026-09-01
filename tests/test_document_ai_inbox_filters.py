import unittest
from pathlib import Path

from services.document_ai_service import normalize_document_type


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
        self.assertIn('const total = state.total;', source)
        self.assertIn('<strong>${count}</strong><span>${escapeHtml(value)}</span>', source)
        self.assertIn("<strong>${data.count}</strong><span>${escapeHtml(data.label || '-')}</span>", source)

    def test_counter_options_remain_visible_with_zero_counts(self):
        source = (ROOT / 'static/js/document_ai_inbox.js').read_text(encoding='utf-8')
        self.assertIn('options.map((option) => [String(option.value), { count: 0', source)
        self.assertNotIn('const hasUnknownType = state.allItems.some', source)

    def test_column_filter_click_does_not_immediately_close_the_redrawn_menu(self):
        source = (ROOT / 'static/js/document_ai_inbox.js').read_text(encoding='utf-8')
        listener = source[source.index("host.addEventListener('click'"):source.index("host.addEventListener('input'")]
        self.assertIn('event.stopPropagation();', listener)


if __name__ == '__main__':
    unittest.main()
