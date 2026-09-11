import unittest
from pathlib import Path

from services.document_ai_service import (
    _document_inbox_scope_sql,
    _infer_invoice_type,
    _missing_intersol_agency,
    _normalize_invoice_type,
    _score_phc_article_candidate,
    validate_document_financial_consistency,
)
from services.document_ai_required_info_service import evaluate_required_info


class DocumentAiInboxWorkflowTests(unittest.TestCase):
    def test_each_view_uses_its_persistent_stage(self):
        self.assertIn('RECEPTION_VALIDATED, 0) = 0', _document_inbox_scope_sql('home'))
        self.assertIn('MANAGEMENT_VALIDATED, 0) = 0', _document_inbox_scope_sql('management'))
        self.assertIn('ACCOUNTING_VALIDATED, 0) = 0', _document_inbox_scope_sql('accounting'))

    def test_unknown_view_fails_to_home_scope(self):
        scope = _document_inbox_scope_sql('anything')
        self.assertIn('RECEPTION_VALIDATED, 0) = 0', scope)
        self.assertNotIn('ACCOUNTING_VALIDATED, 0) = 0', scope)

    def test_archive_uses_completed_stage(self):
        self.assertIn('RECEPTION_VALIDATED, 0) = 1', _document_inbox_scope_sql('home', True))
        self.assertIn('MANAGEMENT_VALIDATED, 0) = 1', _document_inbox_scope_sql('management', True))
        self.assertIn('ACCOUNTING_VALIDATED, 0) = 1', _document_inbox_scope_sql('accounting', True))

    def test_invoice_type_aliases_are_normalized(self):
        self.assertEqual(_normalize_invoice_type('Betão'), 'concrete')
        self.assertEqual(_normalize_invoice_type('Materiais'), 'material')
        self.assertEqual(_normalize_invoice_type('Serviços'), 'services')
        self.assertEqual(_normalize_invoice_type('C&P'), 'services')
        self.assertEqual(_normalize_invoice_type(''), 'unknown')

    def test_invoice_type_can_be_inferred_from_document_lines(self):
        self.assertEqual(
            _infer_invoice_type({'lines': [{'description': 'Béton prêt à emploi'}]}),
            'concrete',
        )
        self.assertEqual(
            _infer_invoice_type({'lines': [{'description': 'Gasoil et péages autoroute'}]}),
            'services',
        )

    def test_management_state_uses_the_same_business_requirements_as_validation(self):
        result = evaluate_required_info(
            {
                'document_type': 'invoice',
                'invoice_type': 'services',
                'customer': {'feid': 1},
                'supplier': {'supplier_no': 10},
                'lines': [{'description': 'Serviço', 'qty': 1, 'unit_price': 10, 'net_amount': 10}],
                'totals': {'net_total': 10, 'tax_total': 2.3, 'gross_total': 12.3},
            },
            'management',
            processing_meta={'phc_origins': [{'stamp': 'BC-1'}]},
            required_fields=['entity', 'supplier', 'article'],
        )
        self.assertFalse(result['ok'])
        self.assertIn('Falta o artigo.', result['messages'])
        self.assertEqual(
            _infer_invoice_type({'lines': [{'description': 'Honoraires de conseil'}]}),
            'services',
        )
        self.assertEqual(
            _infer_invoice_type({'lines': [{'description': 'Treillis soudé'}]}),
            'material',
        )

    def test_intersol_agency_is_required_and_must_be_known(self):
        self.assertTrue(_missing_intersol_agency({'phc_database': 'INTERSOL', 'ged_folder': ''}))
        self.assertTrue(_missing_intersol_agency({'phc_database': 'INTERSOL', 'ged_folder': 'OTHER'}))
        self.assertFalse(_missing_intersol_agency({
            'phc_database': 'INTERSOL', 'ged_folder': 'HSOLS_INTERSOL_LOR',
        }))
        self.assertFalse(_missing_intersol_agency({'phc_database': 'HSOLS_FR', 'ged_folder': 'HSOLS_FR'}))

    def test_financial_detail_must_reconcile_with_document_totals(self):
        result = validate_document_financial_consistency({
            'totals': {'net_total': 100, 'tax_total': 20, 'gross_total': 120},
            'taxes': [{'tax_rate': 20, 'taxable_base': 100, 'tax_amount': 20, 'gross_total': 120}],
        })
        self.assertTrue(result['ok'])

    def test_financial_detail_rejects_inconsistent_iva(self):
        result = validate_document_financial_consistency({
            'totals': {'net_total': 100, 'tax_total': 20, 'gross_total': 120},
            'taxes': [{'tax_rate': 20, 'taxable_base': 100, 'tax_amount': 18, 'gross_total': 118}],
        })
        self.assertFalse(result['ok'])
        self.assertTrue(any('taxa indicada' in message for message in result['errors']))

    def test_financial_consistency_detects_a2c_missing_tax_base(self):
        result = validate_document_financial_consistency({
            'totals': {'net_total': 144921.42, 'tax_total': 29435.91, 'gross_total': 176615.49},
            'taxes': [
                {'tax_rate': 20, 'taxable_base': 144921.42, 'tax_amount': 28984.28, 'gross_total': 173905.70},
                {'tax_rate': 20, 'taxable_base': 2258.16, 'tax_amount': 451.63, 'gross_total': 2709.79},
            ],
        })
        self.assertFalse(result['ok'])
        self.assertIn('bases de IVA', ' '.join(result['errors']))
        self.assertEqual(result['tooltips'], ['Valor não Conforme'])

    def test_financial_consistency_detects_vdb_tax_difference(self):
        result = validate_document_financial_consistency({
            'totals': {'net_total': 11437, 'tax_total': 2356.99, 'gross_total': 13793.99},
            'taxes': [
                {'tax_rate': 20, 'taxable_base': 11437, 'tax_amount': 2294.74, 'gross_total': 13731.74},
            ],
        })
        self.assertFalse(result['ok'])
        self.assertIn('taxa indicada', ' '.join(result['errors']))

    def test_financial_consistency_uses_effective_sublines_and_line_rounding(self):
        result = validate_document_financial_consistency({
            'totals': {'net_total': 30, 'tax_total': 6, 'gross_total': 36},
            'taxes': [{'tax_rate': 20, 'taxable_base': 30, 'tax_amount': 6, 'gross_total': 36}],
            'lines': [{
                'net_amount': 999,
                'tax_rate': 20,
                'sub_lines': [
                    {'net_amount': 10, 'tax_rate': 20},
                    {'net_amount': 20, 'tax_rate': 20},
                ],
            }],
        })
        self.assertTrue(result['ok'])

    def test_inbox_column_filters_use_a_viewport_menu_to_escape_the_table_scroll_area(self):
        inbox_script = Path('static/js/document_ai_inbox.js').read_text()
        inbox_css = Path('static/css/document_ai.css').read_text()
        self.assertIn('function positionColumnFilterMenu(host)', inbox_script)
        self.assertIn("position: fixed;", inbox_css)

    def test_main_details_sheet_places_editable_iva_after_total(self):
        template = Path('templates/document_ai_extract.html').read_text()
        extract_script = Path('static/js/document_ai_extract.js').read_text()
        self.assertIn('<th rowspan="2">PT</th>\n                        <th rowspan="2">IVA</th>', template)
        self.assertIn('data-line-tax-rate=', extract_script)
        self.assertIn("markLineManualFields(line, 'tax_rate')", extract_script)

    def test_validation_highlights_are_shown_only_with_a_tooltip(self):
        extract_script = Path('static/js/document_ai_extract.js').read_text()
        extract_css = Path('static/css/document_ai.css').read_text()
        self.assertIn("target.dataset.docaiValidationTitle = 'true'", extract_script)
        self.assertIn('target.dataset.docaiPreviousTitle', extract_script)
        self.assertIn("replace(/[.]+$/, '')", extract_script)
        self.assertIn('validationTooltipByTarget[targetId] || codeTooltip || tooltips[index] || tooltips[0]', extract_script)
        self.assertIn('background: color-mix(in srgb, var(--sz-color-danger) 8%', extract_css)

    def test_tp058_validation_is_deferred_and_distinguishes_line_hierarchy(self):
        extract_script = Path('static/js/document_ai_extract.js').read_text()
        extract_css = Path('static/css/document_ai.css').read_text()
        self.assertIn('validationVisible: false', extract_script)
        self.assertIn("state.validationVisible = true", extract_script)
        self.assertIn('docai-validation-primary-line-error', extract_script)
        self.assertIn('docai-validation-subline-error', extract_script)
        self.assertIn('docai-validation-field-error', extract_script)
        self.assertIn('.docai-validation-line-error.docai-validation-primary-line-error', extract_css)
        self.assertIn('.docai-validation-line-error.docai-validation-subline-error', extract_css)

    def test_tp058_uses_canonical_tooltips_without_final_periods(self):
        extract_script = Path('static/js/document_ai_extract.js').read_text()
        expected = (
            'Falta Matrícula', 'Falta Centro de Custo', 'Falta Categoria ADM/LOG',
            'Falta Distribuição', 'Artigo não Conforme', 'Valor não Conforme',
            'Movimento Duplicado', 'Matrícula não Conforme', 'Linha Ignorada',
            'Veículo a associar', 'Veículo associado',
        )
        for tooltip in expected:
            self.assertIn(tooltip, extract_script)
            self.assertNotIn(f"{tooltip}.", extract_script)

    def test_tax_detail_is_visually_consolidated_without_mutating_source(self):
        extract_script = Path('static/js/document_ai_extract.js').read_text()
        self.assertIn('const sourceItems = Array.isArray(taxes) ? taxes : [];', extract_script)
        self.assertIn('const grouped = new Map();', extract_script)
        self.assertIn('tax?.exemption_reason', extract_script)

    def test_totals_card_uses_net_tax_gross_order(self):
        template = Path('templates/document_ai_extract.html').read_text()
        net = template.index('id="docAiExtractNetTotal"')
        tax = template.index('id="docAiExtractTaxTotal"')
        gross = template.index('id="docAiExtractGrossTotal"')
        self.assertLess(net, tax)
        self.assertLess(tax, gross)

    def test_origin_references_use_the_canonical_number_year_separator(self):
        extract_script = Path('static/js/document_ai_extract.js').read_text()
        self.assertIn("candidate.year ? ` · ${escapeHtml(candidate.year)}`", extract_script)
        self.assertNotIn("candidate.year ? ` / ${escapeHtml(candidate.year)}`", extract_script)

    def test_lines_are_grouped_visually_by_cost_center_and_registration(self):
        extract_script = Path('static/js/document_ai_extract.js').read_text()
        extract_css = Path('static/css/document_ai.css').read_text()
        self.assertIn('const mappedItems = items.map((line, lineIndex)', extract_script)
        self.assertIn("`${costCenter}\\u0000${registration}`", extract_script)
        self.assertIn("items.some((line) => String(line.group_id || ''))", extract_script)
        self.assertIn('docai-extract-line-group-start', extract_script)
        self.assertIn('.docai-extract-line-group-start td', extract_css)

    def test_article_match_prefers_exact_source_reference(self):
        exact_score, exact_reasons = _score_phc_article_candidate(
            {'ref': 'MAT-100', 'design': 'Betão', 'unit': 'M3'},
            line={'ref': 'MAT-100', 'description': 'Betão', 'unit': 'M3'},
        )
        other_score, _ = _score_phc_article_candidate(
            {'ref': 'MAT-200', 'design': 'Areia', 'unit': 'KG'},
            line={'ref': 'MAT-100', 'description': 'Betão', 'unit': 'M3'},
        )
        self.assertGreater(exact_score, other_score)
        self.assertIn('Referência lida coincide', exact_reasons)

    def test_article_history_strengthens_same_supplier_mapping(self):
        score, reasons = _score_phc_article_candidate(
            {'ref': 'PHC-1', 'design': 'Granulat fin', 'unit': 'T'},
            line={'description': 'Granulat fin livraison', 'unit': 'T'},
            history=[{'article_ref': 'PHC-1', 'description': 'Granulat fin livraison'}],
        )
        self.assertGreaterEqual(score, 0.8)
        self.assertIn('Associação anterior do fornecedor', reasons)

    def test_purchase_order_article_strengthens_the_proposal_without_selecting_it(self):
        score, reasons = _score_phc_article_candidate(
            {'ref': 'PHC-BC', 'design': 'Material', 'unit': 'UN'},
            line={'description': 'Texto da fatura', 'origin_article_refs': ['PHC-BC']},
        )
        self.assertGreaterEqual(score, 0.94)
        self.assertIn('Artigo da origem coincide', reasons)

    def test_article_selection_preserves_invoice_reference(self):
        extract_script = Path('static/js/document_ai_extract.js').read_text()
        selection = extract_script[
            extract_script.index('async function selectArticle(index)'):
            extract_script.index('function closeVehicleModal()')
        ]
        self.assertIn("candidate.source_ref = candidate.extracted_ref || candidate.ref || '';", selection)
        self.assertIn("candidate.article_ref = article.ref || '';", selection)
        self.assertNotIn("candidate.ref = article.ref || '';", selection)
        self.assertIn("line.article_ref || line.article || 'Associar'", extract_script)

    def test_article_search_is_scoped_and_reports_invalid_selection(self):
        extract_script = Path('static/js/document_ai_extract.js').read_text()
        self.assertIn('supplier_no: state.documentData.supplier?.supplier_no', extract_script)
        self.assertIn('selected_article_ref: line.article_ref', extract_script)
        self.assertIn("showMessage('Artigo não encontrado.', 'error');", extract_script)


if __name__ == '__main__':
    unittest.main()
