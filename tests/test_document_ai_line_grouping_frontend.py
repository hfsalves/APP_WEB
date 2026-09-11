import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DocumentAiLineGroupingFrontendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = (ROOT / 'static/js/document_ai_extract.js').read_text(encoding='utf-8')
        cls.template = (ROOT / 'templates/document_ai_extract.html').read_text(encoding='utf-8')
        cls.css = (ROOT / 'static/css/document_ai.css').read_text(encoding='utf-8')

    def test_first_column_is_only_the_group_handle(self):
        self.assertIn('data-line-group-handle=', self.script)
        self.assertIn('title="Agrupar linha" aria-label="Agrupar linha"', self.script)
        self.assertNotIn('docai-extract-line-group-input', self.script)
        self.assertNotIn('P = Principal', self.script)

    def test_drag_and_keyboard_grouping_are_supported(self):
        self.assertIn("addEventListener('dragstart'", self.script)
        self.assertIn("addEventListener('drop'", self.script)
        self.assertIn("['Delete', 'Backspace']", self.script)
        self.assertIn('keyboardGroupLineId', self.script)
        self.assertIn('Desagrupar linha', self.template)

    def test_conflict_messages_are_exact(self):
        self.assertIn('Impossível agrupar: ${label} diferente.', self.script)
        for label in ('Artigo', 'Centro de Custo', 'Origem', 'Data', 'IVA', 'Matrícula'):
            self.assertIn(label, self.script)
        self.assertNotIn("['PU', principal.unit_price", self.script)
        self.assertNotIn("['Unidade', principal.unit", self.script)

    def test_group_visual_states_use_system_warning_colour(self):
        self.assertIn('.docai-line-group-principal > td', self.css)
        self.assertIn('.docai-line-group-associated > td', self.css)
        self.assertIn('var(--sz-color-warning)', self.css)
        self.assertIn('.docai-line-group-handle', self.css)
        self.assertIn('background: transparent', self.css)
        self.assertIn('border: 0', self.css)

    def test_only_group_metadata_is_shared(self):
        self.assertIn("markLineManualFields(line, 'group_id', 'group_role')", self.script)
        self.assertIn('inheritPrincipalFields(target, line)', self.script)
        self.assertNotIn("member.description = line.description", self.script)
        self.assertNotIn("member.qty = line.qty", self.script)

    def test_single_adaptive_distribution_modal(self):
        self.assertEqual(self.template.count('id="docAiLineDistributionModal"'), 1)
        self.assertIn('Distribuir por CdC', self.template)
        self.assertIn('Distribuir por Matrículas', self.script)
        self.assertIn("mode === 'vehicle'", self.script)
        self.assertIn("['registration', 'Matrícula'], ['ccusto', 'Centro de Custo']", self.script)
        self.assertIn("['ccusto', 'Centro de Custo'], ['registration', 'Matrícula']", self.script)
        self.assertIn('docAiLineDistributionSearchPane', self.template)
        self.assertIn("els.lineDistributionMain.hidden = true", self.script)
        self.assertIn("els.lineDistributionSearchPane.hidden = false", self.script)

    def test_distribution_calculation_and_balances(self):
        self.assertIn("['percentage', 'qty', 'net_amount'].includes(field)", self.script)
        self.assertIn('<th>%</th><th>Quantidade</th><th>PU</th><th>PT</th>', self.script)
        self.assertIn('last.percentage = distributionRound(100 -', self.script)
        self.assertIn('readonly tabindex="-1"', self.script)
        self.assertIn('aria-label="por distribuir"', self.script)
        self.assertIn('PU igual a zero: corrige explicitamente a linha antes de validar.', self.script)
        self.assertIn('|| incompleteDistribution', self.script)
        self.assertIn('Completa a distribuição das linhas antes de validar.', self.script)

    def test_group_distribution_is_automatic_and_proportional(self):
        self.assertNotIn('Criar sublinhas às linhas associadas', self.template)
        self.assertIn("if (line.group_role === 'principal')", self.script)
        self.assertIn('function applyPrincipalDistribution(principal, member)', self.script)
        self.assertIn('memberQuantity * Number(row.percentage || 0) / 100', self.script)
        self.assertIn('memberTotal * Number(row.percentage || 0) / 100', self.script)

    def test_principal_removal_breaks_group_without_promotion(self):
        self.assertIn("line.group_role === 'principal'", self.script)
        self.assertNotIn("remaining[0].group_role = 'principal'", self.script)

    def test_existing_groups_are_not_merged(self):
        self.assertIn('Impossível fundir dois grupos existentes.', self.script)

    def test_associated_common_edit_detaches_first(self):
        self.assertIn('function detachAssociatedLine(line)', self.script)
        self.assertIn('Linha desagrupada devido à alteração de um campo comum obrigatório.', self.script)

    def test_vehicle_without_project_and_percentage_tax_are_explicit(self):
        self.assertIn('Matrícula s/Centro de Custo', self.script)
        self.assertIn("row.ccusto = item.ccusto", self.script)
        self.assertIn('docai-line-distribution-percent', self.script)
        self.assertNotIn('Montante IVA', self.template)


if __name__ == '__main__':
    unittest.main()
