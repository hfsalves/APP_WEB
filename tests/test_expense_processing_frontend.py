import unittest
from pathlib import Path


class ExpenseProcessingFrontendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.source = (root / 'templates/colaborador_despesas_processamento.html').read_text(encoding='utf-8')
        cls.base = (root / 'templates/sz_base.html').read_text(encoding='utf-8')

    def test_validation_label_reflects_selection_count(self):
        self.assertIn("count === 1 ? 'Validar despesa'", self.source)
        self.assertIn('`Validar ${count', self.source)
        self.assertNotIn('<span>Lançar no PHC</span>', self.source)

    def test_final_action_waits_for_all_pending_autosaves(self):
        self.assertIn('async function flushPendingSaves(stamps)', self.source)
        self.assertIn('const saved = await flushPendingSaves(stamps);', self.source)
        self.assertLess(
            self.source.index('const saved = await flushPendingSaves(stamps);'),
            self.source.index("fetch('/api/colaborador/despesas/processamento/lancar-phc'"),
        )

    def test_autosave_is_serialized_and_retryable(self):
        self.assertIn('const saveStates = new Map();', self.source)
        self.assertIn('if (tracker.promise)', self.source)
        self.assertIn('Tentar gravar novamente', self.source)

    def test_first_invalid_field_is_focused(self):
        self.assertIn('function focusFirstLaunchIssue(stamps)', self.source)
        self.assertIn('rowEl.scrollIntoView', self.source)

    def test_phc_endpoint_is_preserved(self):
        self.assertIn("fetch('/api/colaborador/despesas/processamento/lancar-phc'", self.source)

    def test_generic_modal_exists_only_in_the_shared_base(self):
        self.assertNotIn('id="genericModal"', self.source)
        self.assertEqual(self.base.count('id="genericModal"'), 1)


if __name__ == '__main__':
    unittest.main()
