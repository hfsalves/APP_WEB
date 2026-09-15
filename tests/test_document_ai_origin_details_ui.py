import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class DocumentAiOriginDetailsUiTests(unittest.TestCase):
    def test_detail_table_has_fixed_principal_and_associated_origin_headers(self):
        template = (ROOT / 'templates' / 'document_ai_extract.html').read_text(encoding='utf-8')
        script = (ROOT / 'static' / 'js' / 'document_ai_extract.js').read_text(encoding='utf-8')

        self.assertIn('docAiExtractPrimaryOriginHead', template)
        self.assertIn('docAiExtractSecondaryOriginHead', template)
        self.assertIn('>Princ.</th>', template)
        self.assertIn('>Assoc.</th>', template)
        self.assertIn("primaryHead.textContent = 'Princ.'", script)
        self.assertIn("secondaryHead.textContent = 'Assoc.'", script)
        self.assertIn('colspan="2" scope="colgroup"', template)

    def test_analysis_only_shows_open_origins_without_card_annotations(self):
        service = (ROOT / 'services' / 'document_ai_service.py').read_text(encoding='utf-8')
        script = (ROOT / 'static' / 'js' / 'document_ai_extract.js').read_text(encoding='utf-8')
        self.assertIn("candidates = [item for item in candidates if not bool(item.get('closed'))]", service)
        candidate_card = script.split('class="docai-extract-origin-candidate', 1)[1].split('</article>', 1)[0]
        self.assertNotIn('<small', candidate_card)

    def test_info_is_outside_origin_and_vehicle_has_no_artificial_width(self):
        template = (ROOT / 'templates' / 'document_ai_extract.html').read_text(encoding='utf-8')
        css = (ROOT / 'static' / 'css' / 'document_ai.css').read_text(encoding='utf-8')
        header = template.split('class="docai-origin-subheads"', 1)[1].split('</tr>', 1)[0]
        self.assertLess(header.index('Princ.'), header.index('Assoc.'))
        self.assertLess(header.index('Assoc.'), header.index('Info'))
        self.assertLess(header.index('Info'), header.index('Matrícula'))
        self.assertIn('.docai-origin-subheads > th:nth-child(-n+2)', css)
        self.assertIn('.docai-extract-vehicle-cell {\n  width: auto;', css)

    def test_detail_origin_cells_are_compact_controls_only(self):
        template = (ROOT / 'templates' / 'document_ai_extract.html').read_text(encoding='utf-8')
        script = (ROOT / 'static' / 'js' / 'document_ai_extract.js').read_text(encoding='utf-8')
        css = (ROOT / 'static' / 'css' / 'document_ai.css').read_text(encoding='utf-8')

        self.assertIn('Associar dossier, linha e quantidade', template)
        self.assertIn('docai-origin-compact-control', script)
        self.assertIn('title="${escapeHtml(info.tooltip)}"', script)
        self.assertIn('width: 2.75rem', css)
        self.assertNotIn('Contrato de SubEmpreitada} N.º', script)

    def test_delivery_note_circles_only_exist_in_distribution_mode(self):
        script = (ROOT / 'static' / 'js' / 'document_ai_extract.js').read_text(encoding='utf-8')

        self.assertIn('state.deliveryNoteDistributionMode && hasDeliveryNoteColumn', script)
        self.assertIn('toggleDeliveryNoteDistribution', script)
        self.assertIn('Guardar distribuição GdR', script)

    def test_delivery_note_proposals_are_compact_and_selectable(self):
        script = (ROOT / 'static' / 'js' / 'document_ai_extract.js').read_text(encoding='utf-8')

        self.assertIn('docai-extract-origin-proposal', script)
        self.assertIn('data-virtual-bl', script)
        self.assertNotIn('Virtual — ainda não existe no PHC', script)
        self.assertNotIn('Sugestão · a criar', script)

    def test_origin_header_uses_one_contextual_action(self):
        template = (ROOT / 'templates' / 'document_ai_extract.html').read_text(encoding='utf-8')
        script = (ROOT / 'static' / 'js' / 'document_ai_extract.js').read_text(encoding='utf-8')

        self.assertIn('docAiExtractOriginAction', template)
        self.assertNotIn('docAiExtractOriginSource', template)
        self.assertIn('function originContextAction()', script)
        self.assertIn('registerDocumentAiOriginAction', script)
        self.assertIn('originActionHandlers.has(action.key)', script)
        for label in (
            'Criar Nota de Encomenda', 'Corrigir Nota de Encomenda', 'Criar Contrato',
            'Criar Contrato Sub.Emp.', 'Distribuir GdR', 'Criar GdR', 'Criar STSE',
        ):
            self.assertIn(label, script)

    def test_all_origin_modes_share_the_nine_column_sheet_and_footer_labels(self):
        template = (ROOT / 'templates' / 'document_ai_extract.html').read_text(encoding='utf-8')
        script = (ROOT / 'static' / 'js' / 'document_ai_extract.js').read_text(encoding='utf-8')
        common = '<th>Artigo</th><th>Designação</th><th>Quantidade</th><th title="Preço unitário">PU</th><th title="Preço total">PT</th><th>IVA</th><th title="Centro de Custo">CdC</th><th>Data</th><th>Matrícula</th>'

        self.assertGreaterEqual(script.count(common), 4)
        self.assertIn("els.originDetailClose.textContent = 'Fechar'", script)
        self.assertIn("els.originDetailClose.textContent = 'Cancelar'", script)
        self.assertIn('<span>Validar</span>', template)
        self.assertNotIn('Validar dados', template)


if __name__ == '__main__':
    unittest.main()
