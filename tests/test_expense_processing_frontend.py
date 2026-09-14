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

    def test_tp072_card_hierarchy_and_read_only_comment(self):
        for label in ('Nome do colaborador', 'Tipo de despesa', 'Data da despesa', 'Total c/IVA', 'Empresa'):
            self.assertIn(label, self.script)
        self.assertIn('Comentário do colaborador', self.script)
        self.assertNotIn('data-expense-field="obs"', self.script)
        self.assertNotIn("obs:card.querySelector", self.script)
        self.assertIn("comment = str(current.get('OBS')", self.service)

    def test_accounting_line_is_two_rows_without_horizontal_scroll(self):
        self.assertIn('expense-line-main', self.script)
        self.assertIn('expense-line-values', self.script)
        self.assertNotIn('overflow-x:auto}.expense-line', self.styles)
        self.assertIn('expense-line-actions', self.script)
        self.assertLess(self.script.index('data-add-line'), self.script.index('data-remove-line'))
        self.assertIn('grid-template-columns:repeat(3,minmax(6rem,1fr))', self.styles)
        self.assertIn('.expense-rows,.expense-columns{overflow-x:hidden}', self.styles)

    def test_phc_values_use_server_validated_search_selectors(self):
        self.assertIn('id="expLookupModal"', self.template)
        self.assertIn('data-lookup="article"', self.script)
        self.assertIn('data-lookup="ccusto"', self.script)
        self.assertIn('data-lookup="vehicle"', self.script)
        self.assertNotIn('datalist', self.script)
        for message in ('Artigo não encontrado.', 'Centro de Custo não encontrado.', 'Matrícula não encontrada.'):
            self.assertIn(message, self.service)
        self.assertIn("'ccusto': str(row.get('CCUSTO')", self.service)
        self.assertIn("'design': str(row.get('DESCRICAO')", self.service)
        self.assertIn("('INATIVO' if _column_exists('ST', 'INATIVO')", self.service)

    def test_save_state_buttons_and_totals_match_tp072(self):
        for text in ('A guardar...', 'Guardado', 'Erro ao guardar'):
            self.assertIn(text, self.script)
        self.assertIn('title="Devolver" aria-label="Devolver"', self.script)
        self.assertIn('title="Eliminar" aria-label="Eliminar"', self.script)
        self.assertIn('.expense-return:hover:not(:disabled)', self.styles)
        self.assertIn('.expense-delete:hover:not(:disabled)', self.styles)
        self.assertIn('.expense-difference.is-zero', self.styles)
        self.assertIn("raise ValueError('Totais incoerentes.')", self.service)

    def test_company_change_preserves_and_flags_manual_values(self):
        self.assertIn("button.classList.add('is-unverified')", self.script)
        self.assertNotIn("querySelectorAll('[data-field=\"ccusto\"],[data-field=\"matricula\"]')", self.script)

    def test_document_identity_includes_required_expense_fields(self):
        self.assertIn("item.tipo||''", self.script)
        self.assertIn('money(item.valor,item.moeda)', self.script)


if __name__ == '__main__':
    unittest.main()
