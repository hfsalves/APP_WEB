import unittest
from pathlib import Path


class DocumentAiExtractSummaryFrontendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.template = (root / 'templates/document_ai_extract.html').read_text(encoding='utf-8')
        cls.script = (root / 'static/js/document_ai_extract.js').read_text(encoding='utf-8')
        cls.css = (root / 'static/css/document_ai.css').read_text(encoding='utf-8')

    def test_summary_has_five_business_cards(self):
        for label in ('Entidade', 'Fornecedor', 'Classificação', 'Obra', 'Totais'):
            self.assertIn(f'>{label}<', self.template)
        self.assertNotIn('docAiExtractClassificationValue', self.template)
        self.assertNotIn('docAiExtractClassificationMeta', self.template)

    def test_ged_destination_is_inside_the_classification_card(self):
        card = self.template.split('id="docAiExtractModeCard"', 1)[1].split('</article>', 1)[0]
        self.assertIn('id="docAiExtractGedDestination"', card)
        self.assertIn('id="docAiExtractGedFileName"', card)
        self.assertIn('id="docAiExtractGedPath"', card)
        self.assertIn('id="docAiExtractGedFolderSelect"', card)
        self.assertIn('function renderClassificationCard()', self.script)

    def test_missing_project_and_totals_are_not_rendered_as_false_values(self):
        self.assertIn("els.projectName.textContent = selected ? project.ccusto : '-';", self.script)
        self.assertIn('formatOptionalMoney(totals.net_total, currency)', self.script)
        self.assertIn('formatOptionalMoney(totals.gross_total, currency)', self.script)

    def test_line_total_only_recalculates_after_quantity_or_price_edit(self):
        total_assignment = "line.net_amount = parseEditableNumber(input.value);"
        recalculation = "line.net_amount = Math.round((Number(line.qty || 0) * Number(line.unit_price || 0)"
        self.assertIn(total_assignment, self.script)
        self.assertIn(recalculation, self.script)
        self.assertLess(self.script.index(total_assignment), self.script.index(recalculation))

    def test_totals_modal_uses_standard_opaque_panel(self):
        self.assertIn('class="sz_panel docai-totals-modal"', self.template)
        self.assertIn('.docai-totals-modal .sz_modal_body', self.css)
        self.assertIn('background: var(--sz-color-surface);', self.css)

    def test_analysis_header_is_portuguese_and_has_only_workflow_actions(self):
        self.assertIn('{% block title %}Análise de Documentos{% endblock %}', self.template)
        header = self.template.split('<header', 1)[1].split('</header>', 1)[0]
        self.assertNotIn('docAiIntegrationAccessBtn', header)
        self.assertIn('Voltar ao inbox', header)
        self.assertNotIn('docAiExtractWorkflowValidateBtn', header)
        analysis_header = self.template.split('<section class="sz_panel docai-extract-result-panel">', 1)[1].split('<nav', 1)[0]
        self.assertIn('docAiExtractWorkflowValidateBtn', analysis_header)

    def test_validation_error_uses_a_single_message_channel(self):
        validation = self.script.split('async function validateWorkflowStage', 1)[1].split("els.backBtn?.addEventListener", 1)[0]
        self.assertNotIn("showMessage(message, 'error')", validation)

    def test_analysis_changes_are_debounced_and_saved_as_a_draft(self):
        self.assertIn('window.setTimeout(() => flushAnalysisSave(), 450)', self.script)
        self.assertIn("/draft`, {\n      method: 'PUT'", self.script)
        self.assertIn('fingerprint === state.draftLastFingerprint', self.script)
        self.assertIn('await flushAnalysisSave()', self.script)

    def test_autosave_failure_has_retry_and_conflict_recovery(self):
        self.assertIn('id="docAiExtractSaveRetryBtn"', self.template)
        self.assertIn('id="docAiConflictModal"', self.template)
        self.assertIn('Documento alterado por outro utilizador.', self.template)
        self.assertIn("error.payload?.code === 'document_version_conflict'", self.script)

    def test_forced_ai_read_preserves_manual_user_changes(self):
        self.assertIn('function captureManualOverrides(', self.script)
        self.assertIn('function applyManualOverrides(', self.script)
        self.assertIn('state.pendingManualOverrides = captureManualOverrides()', self.script)
        self.assertIn('markLineManualFields(line', self.script)

    def test_validation_focuses_the_first_missing_editable_control(self):
        self.assertIn("firstTarget?.querySelector('input, select, textarea, button, [tabindex]')", self.script)
        self.assertIn("focusTarget?.focus({ preventScroll: true })", self.script)


if __name__ == '__main__':
    unittest.main()
