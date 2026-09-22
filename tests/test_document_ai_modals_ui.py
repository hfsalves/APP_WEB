import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class DocumentAiModalsUiTests(unittest.TestCase):
    def test_tax_modal_uses_requested_title_and_total_row(self):
        template = (ROOT / 'templates' / 'document_ai_extract.html').read_text(encoding='utf-8')
        script = (ROOT / 'static' / 'js' / 'document_ai_extract.js').read_text(encoding='utf-8')
        css = (ROOT / 'static' / 'css' / 'document_ai.css').read_text(encoding='utf-8')

        self.assertIn('Detalhe IVA', template)
        self.assertNotIn('Detalhe dos totais', template)
        self.assertIn('docai-tax-total-row', script)
        self.assertIn(
            'id="docAiTotalsCloseTop" type="button" class="sz_button sz_button_ghost sz_modal_close"',
            template,
        )
        self.assertIn('.docai-totals-modal .sz_table_wrap', css)
        self.assertIn('overflow-x: visible;', css)

    def test_origin_detail_always_keeps_registration_column(self):
        script = (ROOT / 'static' / 'js' / 'document_ai_extract.js').read_text(encoding='utf-8')

        self.assertIn('<th>Data</th><th>Matrícula</th>', script)
        self.assertNotIn("showRegistration ? '<th>Matrícula</th>'", script)

    def test_origin_detail_has_two_fixed_header_lines_and_selected_proforma(self):
        template = (ROOT / 'templates' / 'document_ai_extract.html').read_text(encoding='utf-8')
        script = (ROOT / 'static' / 'js' / 'document_ai_extract.js').read_text(encoding='utf-8')

        self.assertIn('docAiOriginDetailSubtitle', template)
        self.assertIn('const selectedProformas = state.selectedOrigins.filter', script)
        self.assertIn("if (displayStage === 'proforma_invoice')", script)
        self.assertIn('Total s/IVA', script)
        self.assertIn('Total c/IVA', script)
        self.assertIn('Totais globais PHC (não reconciliados com estas linhas)', script)
        service = (ROOT / 'services' / 'document_ai_service.py').read_text(encoding='utf-8')
        self.assertIn("'totals_reconciled': totals_reconciled", service)
        self.assertNotIn('Não é possível associar o Contrato: os totais PHC', service)

    def test_origin_modal_keeps_only_its_sheet_scrollable(self):
        css = (ROOT / 'static' / 'css' / 'document_ai.css').read_text(encoding='utf-8')
        script = (ROOT / 'static' / 'js' / 'document_ai_extract.js').read_text(encoding='utf-8')

        self.assertIn('.docai-origin-detail-modal .sz_modal_body {\n  min-height: 0;\n  display: flex;\n  overflow: hidden;', css)
        self.assertIn('.docai-origin-detail-modal .sz_table_wrap {\n  max-height: 100%;\n  overflow: auto;', css)
        self.assertNotIn("candidate.number || '--'", script)
        self.assertIn('`Total s/IVA ${formatMoney', script)
        self.assertIn('`Total c/IVA ${formatMoney', script)
        self.assertIn(
            '.docai-origin-detail-heading p.is-warning {\n  color: var(--sz-color-text-muted);',
            css,
        )

    def test_origin_modal_maps_imported_lines_by_drag_and_drop(self):
        template = (ROOT / 'templates' / 'document_ai_extract.html').read_text(encoding='utf-8')
        script = (ROOT / 'static' / 'js' / 'document_ai_extract.js').read_text(encoding='utf-8')
        css = (ROOT / 'static' / 'css' / 'document_ai.css').read_text(encoding='utf-8')
        service = (ROOT / 'services' / 'document_ai_service.py').read_text(encoding='utf-8')

        self.assertIn('id="docAiOriginSourceLines"', template)
        self.assertIn('id="docAiOriginTargetLines"', template)
        self.assertIn('id="docAiOriginOverDeliver"', template)
        self.assertIn('id="docAiOriginSplitRemainder"', template)
        self.assertIn('id="docAiOriginPartialToggle"', template)
        self.assertIn('Satisfazer parcialmente', template)
        self.assertIn('id="docAiOriginPartialQuantity"', template)
        self.assertIn('id="docAiOriginCorrectQuantity"', template)
        self.assertIn('id="docAiOriginLineMapperSave"', template)
        self.assertIn("els.originMapperTargetLines?.addEventListener('dragstart'", script)
        self.assertIn("els.originMapperSourceLines?.addEventListener('drop'", script)
        self.assertIn('line.article_ref = sourceLine.article || sourceLine.ref', script)
        self.assertIn('applyBcAllocationLineage(line, line.bc_allocations, mapping.family)', script)
        self.assertIn('allow_over_delivery: mapping.overDeliveryTargets.has(targetIndex)', script)
        self.assertIn('function splitOriginMapperRemainder(requestedQuantity = null)', script)
        self.assertIn('function applyCustomOriginPartialQuantity()', script)
        self.assertIn('coveredQuantity > Number(warning.available || 0)', script)
        self.assertNotIn('até ao máximo disponível de', script)
        self.assertIn('async function correctOriginMapperQuantity()', script)
        self.assertIn('/origin-line/quantity', script)
        self.assertIn('function removeOriginMapperIndex(mapping, removedIndex)', script)
        self.assertIn('function legacyOriginSplitRemainderIndex(mapping, coveredIndex)', script)
        self.assertIn('function reconcileReleasedOriginSplits(mapping)', script)
        self.assertIn('reconcileReleasedOriginSplits(state.originDetailMapping)', script)
        self.assertIn("line.origin_quantity_split = { id: splitId, role: 'covered'", script)
        self.assertIn('Desfazer associação e recompor a linha original', script)
        self.assertIn('.docai-origin-line-mapper-columns', css)
        self.assertIn('ISNULL(BI.QTT2, 0)', service)
        self.assertIn('ISNULL(BI.TABIVA, 0)', service)
        self.assertIn("'tax_table': _safe_int(row[11], 0)", service)
        self.assertIn("'pending_quantity': (", service)
        self.assertIn('docai-origin-line-mapper-meta', script)
        self.assertIn('IVA Tabela', script)
        self.assertIn('PU ${escapeHtml(hasUnitPrice ? formatMoney', script)
        self.assertIn('const distributedCostCenters = [...new Set([', script)
        self.assertIn("directCostCenter || String(state.selectedProject?.ccusto || '').trim()", script)
        self.assertIn('matchingTaxTables', script)
        self.assertIn('.docai-origin-line-mapper-meta', css)
        self.assertIn("candidate.closed !== true", script)
        self.assertNotIn("candidate.available_balance !== false", script)
        self.assertIn("mapping.closed", script)
        self.assertIn('function openOriginArticleModal(sourceStamp)', script)
        self.assertIn('/origin-line/article', script)
        self.assertIn('updateLinkedOriginArticle', script)
        self.assertIn('is-reference-editable', script)
        self.assertIn('is-reference-editable', css)
        self.assertIn('def correct_document_phc_origin_line_article(', service)
        self.assertIn("'ststamp': str(article[0] or '').strip()", service)
        self.assertIn("allocation['article_ref'] = normalized_ref", service)
        self.assertNotIn('currencySuffix', script)
        self.assertNotIn('docai-extract-line-currency', script)

    def test_secondary_settings_modals_close_with_escape(self):
        required = (ROOT / 'static' / 'js' / 'document_ai_required_info.js').read_text(encoding='utf-8')
        distribution = (ROOT / 'static' / 'js' / 'document_ai_distribution.js').read_text(encoding='utf-8')

        self.assertIn("event.key === 'Escape'", required)
        self.assertIn("event.key === 'Escape'", distribution)


if __name__ == '__main__':
    unittest.main()
