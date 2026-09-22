import unittest
from pathlib import Path
import re


class DocumentAiReceptionFrontendTests(unittest.TestCase):
    def test_extract_modals_use_the_shared_sz_modal_structure(self):
        root = Path(__file__).resolve().parents[1]
        template = (root / 'templates/document_ai_extract.html').read_text(encoding='utf-8')
        styles = (root / 'static/css/sz_styles.css').read_text(encoding='utf-8')

        modal_panels = re.findall(
            r'<div id="docAi[^\"]*Modal" class="sz_modal[^\"]*"[^>]*>\s*'
            r'<div class="([^"]+)"',
            template,
        )
        self.assertGreaterEqual(len(modal_panels), 13)
        self.assertTrue(all('sz_panel' in classes.split() for classes in modal_panels))
        self.assertNotIn('sz_modal_dialog', template)
        self.assertNotIn('sz_icon_button', template)

        close_buttons = re.findall(
            r'id="docAi[^\"]*CloseTop"[^>]*class="([^"]+)"',
            template,
        )
        self.assertGreaterEqual(len(close_buttons), 10)
        self.assertTrue(all('sz_modal_close' in classes.split() for classes in close_buttons))
        self.assertIn('.sz_modal_close {', styles)

    def test_new_correspondence_is_persisted_so_reception_can_validate_it(self):
        root = Path(__file__).resolve().parents[1]
        blueprint = (root / 'blueprints/document_ai.py').read_text(encoding='utf-8')
        extract_route = blueprint.split('def api_document_ai_extract():', 1)[1].split("@bp.route('/api/document_ai/extract/split'", 1)[0]

        self.assertNotIn('not_saved_to_inbox', extract_route)
        self.assertNotIn('if is_mail and not requested_document_id', extract_route)
        self.assertIn('ensure_llm_inbox_document(file_name, file_bytes, _current_login())', extract_route)
        self.assertIn("payload['document_id'] = document_id", extract_route)

        persist_route = blueprint.split('def api_document_ai_extract_persist():', 1)[1].split("@bp.route('/api/document_ai/extract/split'", 1)[0]
        self.assertIn('ensure_llm_inbox_document(', persist_route)
        self.assertIn('save_llm_extraction(document_id, {', persist_route)
        self.assertNotIn('extract_document_full_visual', persist_route)

    def test_correspondence_header_has_no_secondary_document_field(self):
        source = (Path(__file__).resolve().parents[1] / 'static/js/document_ai_extract.js').read_text(encoding='utf-8')
        start = source.index('function renderDocumentCard()')
        end = source.index('async function saveHeaderField', start)
        render = source[start:end]

        self.assertIn("const isCorrespondence = ['mail', 'bank_statement'].includes(normalizedDocumentType);", render)
        self.assertIn("...(!isCorrespondence ? [editing === 'document_number'", render)
        self.assertNotIn('? documentData.mail_title', render)
        self.assertIn('...(isInvoice ? [editing === \'invoice_type\'', render)
        self.assertNotIn("isInvoice || editing === 'document_type'", render)

    def test_mail_ged_title_is_editable_and_limited_to_25_characters(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / 'static/js/document_ai_extract.js').read_text(encoding='utf-8')
        template = (root / 'templates/document_ai_extract.html').read_text(encoding='utf-8')

        self.assertIn('id="docAiExtractMailTitleEdit"', template)
        self.assertIn('id="docAiExtractMailTitleInput"', template)
        self.assertIn('maxlength="25"', template)
        self.assertIn("state.documentData.mail_title = value;", source)
        self.assertIn("'mail_title'", source)
        self.assertIn('renderGedDestination();', source)
        self.assertIn('scheduleAnalysisSave({ immediate: true })', source)

    def test_ged_file_name_never_contains_the_selected_cost_center(self):
        source = (Path(__file__).resolve().parents[1] / 'static/js/document_ai_extract.js').read_text(encoding='utf-8')
        start = source.index('function renderGedDestination()')
        end = source.index('function updateSubmitPhcButton()', start)
        render = source[start:end]

        self.assertNotIn("const project = gedSafePart(state.selectedProject?.ccusto", render)
        self.assertNotIn('fileParts.push(project)', render)
        self.assertIn("documentData.document_type === 'credit_note'", render)
        self.assertIn('`NC-${rawDocumentNumber.replace(', render)

    def test_correspondence_validation_is_not_blocked_by_hidden_lines_or_autosave(self):
        source = (Path(__file__).resolve().parents[1] / 'static/js/document_ai_extract.js').read_text(encoding='utf-8')
        start = source.index('function updateSubmitPhcButton()')
        end = source.index('function renderDocumentCard()', start)
        button_logic = source[start:end]

        self.assertIn('const hasBlockingDistribution = !isCorrespondence && incompleteDistribution;', button_logic)
        self.assertIn('|| hasBlockingDistribution', button_logic)
        self.assertNotIn('|| Boolean(state.draftTimer)', button_logic)
        self.assertNotIn('|| Boolean(state.draftRequest)', button_logic)
        self.assertIn('if (!await flushAnalysisSave()) return;', source)
        self.assertIn("fetchJson('/api/document_ai/extract/persist'", source)
        self.assertIn('if (!state.currentDocumentId && !await persistUnsavedAnalysis()) return false;', source)

    def test_workflow_validation_does_not_trigger_legacy_phc_flow(self):
        source = (Path(__file__).resolve().parents[1] / 'static/js/document_ai_extract.js').read_text(encoding='utf-8')
        start = source.index('async function validateWorkflowStage')
        end = source.index("els.backBtn?.addEventListener", start)
        workflow = source[start:end]
        self.assertNotIn('submitDocumentToPhc', workflow)
        self.assertNotIn('confirmDocumentControl', workflow)
        self.assertNotIn('saveWorkflowCorrections', workflow)
        self.assertIn('/workflow/preflight', workflow)
        self.assertIn('/workflow/validate', workflow)

    def test_correspondence_number_is_refreshed_after_manual_header_correction(self):
        source = (Path(__file__).resolve().parents[1] / 'static/js/document_ai_extract.js').read_text(encoding='utf-8')
        refresh = source.split('async function refreshHeaderDependencies()', 1)[1].split('async function loadCorrespondenceReference()', 1)[0]
        self.assertIn('loadCorrespondenceReference()', refresh)
        self.assertIn('/workflow/preflight', refresh)
        self.assertIn('state.duplicateMatches = duplicates', refresh)
        correspondence = source.split('async function loadCorrespondenceReference()', 1)[1].split('function cleanupPreview()', 1)[0]
        self.assertIn('/api/document_ai/correspondence/next-reference', correspondence)
        self.assertIn('const integration = state.integrationResult || {};', source)
        self.assertIn('Correspondência por criar', source)


if __name__ == '__main__':
    unittest.main()
