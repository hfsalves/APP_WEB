import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from unittest.mock import MagicMock

from services.document_ai_service import (
    DOC_AI_PHC_PURCHASE_FLOW,
    clear_document_phc_origin,
    get_cached_llm_extraction,
    get_next_phc_correspondence_reference,
    reset_llm_extraction,
    save_llm_extraction,
    save_document_phc_origin,
    save_document_adjusted_lines,
    _score_phc_origin_candidate,
    _match_document_lines_to_origin,
    _phc_contract_flow_stages,
    _normalize_document_integration_access,
)
from services import document_ai_service


class DocumentAiPhcOriginTests(unittest.TestCase):
    def test_document_integration_access_normalizes_only_known_types(self):
        permissions = _normalize_document_integration_access({
            'purchase_order': True,
            'delivery_note': '1',
            'invoice': False,
            'unknown_type': True,
        })

        self.assertTrue(permissions['purchase_order'])
        self.assertTrue(permissions['delivery_note'])
        self.assertFalse(permissions['invoice'])
        self.assertNotIn('unknown_type', permissions)

    def test_contract_dossiers_are_discovered_from_each_phc_catalog(self):
        cursor = MagicMock()
        cursor.execute.return_value.fetchall.return_value = [
            (119, 'Contrat'),
            (128, 'Contrat Sous-Traitant'),
        ]

        stages = _phc_contract_flow_stages(cursor)

        self.assertEqual([stage['ndos'] for stage in stages], [119, 128])
        self.assertEqual([stage['document_type'] for stage in stages], ['contract', 'contract'])
        self.assertEqual(stages[0]['label'], 'Contrat')

    def test_next_correspondence_reference_uses_company_and_year(self):
        cursor = MagicMock()
        cursor.execute.return_value.fetchone.return_value = (2864,)
        connection = MagicMock()
        connection.__enter__.return_value.cursor.return_value = cursor
        source = {
            'kind': 'phc', 'feid': 1, 'phc_db': 'HSOLS_FR',
            'phc_server': '10.0.1.12', 'company_name': 'HSOLS FRANCE SAS',
        }

        with patch.object(document_ai_service, '_phc_origin_source', return_value=source), patch(
            'services.phc_user_import_service._phc_conn_str', return_value='PHC-CONNECTION'
        ), patch('pyodbc.connect', return_value=connection) as connect:
            result = get_next_phc_correspondence_reference(
                {'feid': 1, 'name': 'HSOLS France'}, 2026,
            )

        self.assertEqual(result['reference'], 2865)
        self.assertEqual(result['last_reference'], 2864)
        self.assertEqual(result['year'], 2026)
        self.assertEqual(result['phc_database'], 'HSOLS_FR')
        self.assertTrue(result['provisional'])
        connect.assert_called_once_with('PHC-CONNECTION', timeout=10)
        query_args = cursor.execute.call_args.args
        self.assertIn('dbo.CR', query_args[0])
        self.assertIn('ANO', query_args[0])
        self.assertEqual(query_args[1], 2026)

    def test_correspondence_reference_restarts_when_year_has_no_rows(self):
        cursor = MagicMock()
        cursor.execute.return_value.fetchone.return_value = (0,)
        connection = MagicMock()
        connection.__enter__.return_value.cursor.return_value = cursor
        source = {'kind': 'phc', 'feid': 8, 'phc_db': 'INTERSOL', 'phc_server': '10.0.1.12'}

        with patch.object(document_ai_service, '_phc_origin_source', return_value=source), patch(
            'services.phc_user_import_service._phc_conn_str', return_value='PHC-CONNECTION'
        ), patch('pyodbc.connect', return_value=connection):
            result = get_next_phc_correspondence_reference({'feid': 8}, 2027)

        self.assertEqual(result['reference'], 1)
        self.assertEqual(result['year'], 2027)

    def test_purchase_flow_uses_the_configured_phc_stages(self):
        self.assertEqual(
            [item['key'] for item in DOC_AI_PHC_PURCHASE_FLOW],
            ['purchase_order', 'delivery_note', 'proforma_invoice', 'invoice'],
        )
        self.assertEqual(
            [item.get('ndos') for item in DOC_AI_PHC_PURCHASE_FLOW[:3]],
            [102, 130, 218],
        )

    def test_candidate_score_rewards_date_and_line_matches(self):
        document = {
            'document_date': '2026-06-30',
            'lines': [{'ref': 'ABC-123', 'description': 'Betão estrutural para fundação'}],
            'totals': {'gross_total': 1230},
        }
        candidate = {'ndos': 218, 'date': '2026-06-29', 'total': 1225}
        lines = [{'ref': 'ABC-123', 'description': 'Betão estrutural para fundação'}]

        score, reasons = _score_phc_origin_candidate(candidate, document, lines)

        self.assertGreater(score, 0.85)
        self.assertIn('Mesmo fornecedor', reasons)
        self.assertTrue(any('referências coincidem' in reason for reason in reasons))
        self.assertIn('Valor total próximo', reasons)

    def test_candidate_without_line_match_remains_possible(self):
        document = {
            'document_date': '2026-06-30',
            'lines': [{'ref': 'CURRENT', 'description': 'Material atual'}],
            'totals': {'gross_total': 5000},
        }
        candidate = {'ndos': 102, 'date': '2026-06-20', 'total': 100}

        score, reasons = _score_phc_origin_candidate(
            candidate,
            document,
            [{'ref': 'OLDER', 'description': 'Outro material'}],
        )

        self.assertGreater(score, 0.2)
        self.assertIn('Mesmo fornecedor', reasons)

    def test_cached_llm_extraction_is_reused(self):
        stored = SimpleNamespace(
            docinstamp='DOC-1',
            processing_meta_json='{"llm_full_extraction":{"version":4,"model":"gpt-test","document":{"document_number":"F1"},"matching":{},"saved_at":"2026-07-22"}}',
        )
        with patch.object(document_ai_service.db.session, 'get', return_value=stored):
            result = get_cached_llm_extraction('DOC-1')

        self.assertTrue(result['cached'])
        self.assertEqual(result['document']['document_number'], 'F1')
        self.assertEqual(result['model'], 'gpt-test')

    def test_saving_llm_extraction_updates_inbox_fields(self):
        stored = SimpleNamespace(
            docinstamp='DOC-2', processing_meta_json='{}', json_resultado='{}', feid=None,
            fornecedor_no=None, fornecedor_nome_detetado='', fornecedor_nif_detetado='',
            doc_type_detected='unknown', confidence_score=0, extraction_method='failed',
            extraction_quality_score=0, processing_stage='new', processing_status='new',
            last_processing_error='', dtproc=None, dtalt=None, useralteracao='',
        )
        payload = {
            'model': 'gpt-test',
            'matching': {'supplier_matched': True},
            'document': {
                'document_type': 'invoice', 'confidence': 0.9,
                'customer': {'feid': 7},
                'supplier': {'supplier_no': 42, 'name': 'Fornecedor', 'tax_id': '123'},
            },
        }
        with patch.object(document_ai_service.db.session, 'get', return_value=stored), patch.object(
            document_ai_service.db.session, 'commit'
        ):
            result = save_llm_extraction('DOC-2', payload, 'tester')

        self.assertTrue(result['cached'])
        self.assertEqual(stored.feid, 7)
        self.assertEqual(stored.fornecedor_no, 42)
        self.assertEqual(stored.doc_type_detected, 'invoice')
        self.assertEqual(stored.processing_status, 'parsed_ok')

    def test_explicit_pdf_origin_has_priority(self):
        document = {
            'document_date': '2026-04-30',
            'origin_references': [{
                'document_type': 'purchase_order',
                'document_number': '397',
                'visible_text': 'Votre commande 397',
                'page': 1,
            }],
            'lines': [],
            'totals': {},
        }
        candidate = {
            'ndos': 102,
            'document_type': 'purchase_order',
            'number': '397',
            'date': '2026-03-23',
            'total': 0,
        }

        score, reasons = _score_phc_origin_candidate(candidate, document, [])

        self.assertGreater(score, 0.8)
        self.assertTrue(reasons[0].startswith('Referência explícita no PDF'))

    def test_customer_reference_in_line_is_purchase_order_candidate(self):
        origins = document_ai_service._explicit_document_origins({
            'origin_references': [],
            'lines': [
                {'description': 'INTERSOL Réf. Client: 498'},
                {'description': 'Réf. Client: 498'},
            ],
        })

        self.assertEqual(len(origins), 1)
        self.assertEqual(origins[0]['document_type'], 'purchase_order')
        self.assertEqual(origins[0]['document_number'], '498')

    def test_pending_quantity_match_rewards_purchase_order(self):
        document = {
            'document_date': '2026-04-30',
            'lines': [
                {'qty': 7.5, 'origin_delivery_note_number': f'BL-{index}'}
                for index in range(6)
            ] + [{'qty': 45, 'description': 'Taxa ambiental'}],
            'totals': {},
        }
        candidate = {
            'ndos': 102,
            'document_type': 'purchase_order',
            'number': '498',
            'date': '2026-04-02',
        }
        candidate_lines = [{'pending_qty': 45, 'description': 'Betão'}]

        score, reasons = _score_phc_origin_candidate(candidate, document, candidate_lines)

        self.assertGreater(score, 0.65)
        self.assertIn('Quantidade pendente coincide (45)', reasons)

    def test_maps_many_invoice_deliveries_to_single_purchase_order_line(self):
        document_lines = [
            {
                'description': 'Betão C25/30',
                'qty': 7.5,
                'origin_delivery_note_number': f'BL-{index}',
            }
            for index in range(6)
        ] + [{'description': 'Taxa ambiental', 'qty': 45}]
        origin_lines = [
            {'ref': 'CBA', 'description': 'Betão para 45 m3', 'qty': 45, 'pending_qty': 45},
            {'ref': 'ECO', 'description': 'Taxa', 'qty': 0, 'pending_qty': 0},
        ]

        matches = _match_document_lines_to_origin(document_lines, origin_lines)

        self.assertEqual(len(matches), 6)
        self.assertTrue(all(item['origin_ref'] == 'CBA' for item in matches))
        self.assertTrue(all('Quantidade agregada coincide' in item['reasons'] for item in matches))

    def test_maps_multiple_lines_by_quantity_and_description_without_reuse(self):
        document_lines = [
            {'description': 'Cimento cinzento', 'qty': 10},
            {'description': 'Areia lavada', 'qty': 5},
        ]
        origin_lines = [
            {'ref': 'AREIA', 'description': 'Areia lavada', 'qty': 5, 'pending_qty': 5},
            {'ref': 'CIM', 'description': 'Cimento cinzento', 'qty': 10, 'pending_qty': 10},
        ]

        matches = _match_document_lines_to_origin(document_lines, origin_lines)

        self.assertEqual(
            [(item['document_line_index'], item['origin_ref']) for item in matches],
            [(0, 'CIM'), (1, 'AREIA')],
        )

    def test_forced_llm_read_resets_cached_extraction(self):
        stored = SimpleNamespace(
            docinstamp='DOC-3',
            processing_meta_json='{"llm_full_extraction":{"version":4,"document":{}},"phc_origin":{"stamp":"BO1"},"phc_origins":[{"stamp":"BO2"}]}',
            json_resultado='{"document_number":"OLD"}', fornecedor_no=42,
            fornecedor_nome_detetado='Old supplier', fornecedor_nif_detetado='123',
            doc_type_detected='invoice', confidence_score=0.9, extraction_method='llm_visual',
            extraction_quality_score=0.9, processing_stage='llm_extracted',
            processing_status='parsed_ok', last_processing_error='', dtproc='old', dtalt=None,
            useralteracao='',
        )
        with patch.object(document_ai_service.db.session, 'get', return_value=stored), patch.object(
            document_ai_service.db.session, 'commit'
        ):
            reset_llm_extraction('DOC-3', 'tester')

        self.assertNotIn('llm_full_extraction', stored.processing_meta_json)
        self.assertNotIn('phc_origin', stored.processing_meta_json)
        self.assertNotIn('phc_origins', stored.processing_meta_json)
        self.assertIsNone(stored.fornecedor_no)
        self.assertEqual(stored.processing_status, 'new')

    def test_clearing_origin_preserves_llm_cache(self):
        stored = SimpleNamespace(
            docinstamp='DOC-4',
            processing_meta_json='{"llm_full_extraction":{"version":4,"document":{"document_number":"F1"}},"phc_origin":{"stamp":"BO498"}}',
            dtalt=None,
            useralteracao='',
        )
        with patch.object(document_ai_service.db.session, 'get', return_value=stored), patch.object(
            document_ai_service.db.session, 'commit'
        ):
            result = clear_document_phc_origin('DOC-4', 'tester')

        self.assertTrue(result['removed'])
        self.assertNotIn('phc_origin', stored.processing_meta_json)
        self.assertIn('llm_full_extraction', stored.processing_meta_json)
        self.assertEqual(stored.useralteracao, 'tester')

    def test_multiple_purchase_orders_can_be_selected_and_one_removed(self):
        stored = SimpleNamespace(
            docinstamp='DOC-MULTI',
            processing_meta_json='{"llm_full_extraction":{"version":4,"document":{}}}',
            dtalt=None,
            useralteracao='',
        )
        candidates = [{
            'stamp': 'BO498', 'table': 'BO', 'number': '498', 'document_type': 'purchase_order',
            'ccusto': 'OBRA-A', 'line_matches': [],
        }, {
            'stamp': 'BO499', 'table': 'BO', 'number': '499', 'document_type': 'purchase_order',
            'ccusto': 'OBRA-B', 'line_matches': [],
        }]
        search_payload = {
            'phc_database': 'PHC',
            'stages': [{'candidates': candidates}],
        }
        with patch.object(document_ai_service.db.session, 'get', return_value=stored), patch.object(
            document_ai_service.db.session, 'commit'
        ), patch.object(document_ai_service, 'search_phc_document_origins', return_value=search_payload):
            first = save_document_phc_origin('DOC-MULTI', candidates[0], {}, 'tester')
            second = save_document_phc_origin('DOC-MULTI', candidates[1], {}, 'tester')
            removed = clear_document_phc_origin('DOC-MULTI', 'tester', 'BO498')

        self.assertEqual([item['stamp'] for item in first['origins']], ['BO498'])
        self.assertEqual([item['stamp'] for item in second['origins']], ['BO498', 'BO499'])
        self.assertEqual([item['stamp'] for item in removed['origins']], ['BO499'])
        self.assertEqual(
            [item['stamp'] for item in json.loads(stored.processing_meta_json)['phc_origins']],
            ['BO499'],
        )

    def test_saving_adjusted_lines_preserves_cached_extraction(self):
        stored = SimpleNamespace(
            docinstamp='DOC-5',
            processing_meta_json='{"llm_full_extraction":{"version":4,"document":{"document_number":"F1","lines":[{"qty":12}]}}}',
            json_resultado='{}',
            dtalt=None,
            useralteracao='',
        )
        adjusted_lines = [{
            'qty': 4,
            'origin_delivery_note_number': 'BL1',
            '_virtual_split_allocation': True,
        }, {
            'qty': 8,
            'origin_delivery_note_number': 'BL2',
            '_virtual_split_allocation': True,
        }]
        with patch.object(document_ai_service.db.session, 'get', return_value=stored), patch.object(
            document_ai_service.db.session, 'commit'
        ):
            result = save_document_adjusted_lines('DOC-5', adjusted_lines, 'tester')

        self.assertEqual(result['line_count'], 2)
        saved_meta = json.loads(stored.processing_meta_json)
        saved_result = json.loads(stored.json_resultado)
        self.assertEqual(saved_meta['llm_full_extraction']['document']['document_number'], 'F1')
        self.assertTrue(saved_meta['llm_full_extraction']['document']['lines'][0]['_virtual_split_allocation'])
        self.assertEqual(saved_result['lines'][1]['origin_delivery_note_number'], 'BL2')


if __name__ == '__main__':
    unittest.main()
