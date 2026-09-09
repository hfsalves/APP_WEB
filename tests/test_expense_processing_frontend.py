import unittest
from pathlib import Path


class ExpenseProcessingFrontendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.template = (root / 'templates/colaborador_despesas_processamento.html').read_text(encoding='utf-8')
        cls.script = (root / 'static/js/expense_processing.js').read_text(encoding='utf-8')
        cls.styles = (root / 'static/css/expense_processing.css').read_text(encoding='utf-8')
        cls.service = (root / 'services/colaborador_despesas_service.py').read_text(encoding='utf-8')
        cls.app = (root / 'app.py').read_text(encoding='utf-8')

    def test_document_is_left_and_processing_is_right(self):
        self.assertLess(self.template.index('expense-document-panel'), self.template.index('expense-processing-panel'))
        self.assertIn('grid-template-columns:minmax(24rem,42%) minmax(38rem,58%)', self.styles)

    def test_header_and_document_actions_match_tp038(self):
        self.assertNotIn('sz_page_subtitle', self.template)
        self.assertIn("'Processamento' if archive_mode else 'Arquivo'", self.template)
        self.assertIn('title="Abrir PDF"', self.template)
        self.assertIn('title="Eliminar apenas o PDF"', self.template)
        self.assertIn('title="Analisar novamente com IA"', self.template)

    def test_multiple_accounting_lines_and_totals_are_present(self):
        self.assertIn('data-accounting-line', self.script)
        self.assertIn('data-add-line', self.script)
        self.assertIn('data-remove-line', self.script)
        self.assertIn('data-total-net', self.script)
        self.assertIn('data-difference', self.script)
        self.assertIn('COLAB_DESPESA_CONTAB_LINHA', self.service)

    def test_autosave_is_debounced_and_flushed_before_phc(self):
        self.assertIn('setTimeout(()=>save(card),450)', self.script)
        self.assertIn('async function flushPendingSaves(stamps)', self.script)
        self.assertLess(self.script.index('flushPendingSaves(stamps)'), self.script.index("fetch('/api/colaborador/despesas/processamento/lancar-phc'"))

    def test_optimistic_concurrency_and_exact_conflict_message(self):
        self.assertIn('VERSION = VERSION + 1', self.service)
        self.assertIn('Esta despesa foi alterada por outro utilizador. Atualiza antes de continuar.', self.service)
        self.assertIn("status = 409", self.app)

    def test_archive_and_three_deletion_paths_exist(self):
        self.assertIn("ESTADO = 'ELIMINADA'", self.service)
        self.assertIn("ESTADO = 'DEVOLVIDA'", self.service)
        self.assertIn('delete_expense_processing_pdf', self.service)
        self.assertIn('permanently_delete_archived_expense', self.service)

    def test_selection_is_limited_by_company_employee_and_currency(self):
        self.assertIn("base.feid, base.login", self.script)
        self.assertIn("Seleciona despesas da mesma empresa, colaborador e moeda.", self.script)

    def test_phc_endpoint_and_success_identifiers_are_preserved(self):
        self.assertIn("fetch('/api/colaborador/despesas/processamento/lancar-phc'", self.script)
        self.assertIn('result.nmdos', self.script)
        self.assertIn('result.obrano', self.script)

    def test_processing_permissions_are_separate(self):
        self.assertIn("tabela='PROC_DESP'", self.app)
        self.assertIn("_expense_processing_has_permission('consultar')", self.app)
        self.assertIn("_expense_processing_has_permission('inserir')", self.app)
        self.assertIn("_expense_processing_has_permission('editar')", self.app)
        self.assertIn("_expense_processing_has_permission('eliminar')", self.app)


if __name__ == '__main__':
    unittest.main()
