import json
import os
import tempfile
import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch
from unittest.mock import MagicMock

from services.document_ai_service import (
    DOC_AI_PHC_PURCHASE_FLOW,
    clear_document_phc_origin,
    get_cached_llm_extraction,
    get_next_phc_correspondence_reference,
    submit_correspondence_to_phc,
    DOC_AI_PROVISIONAL_ARTICLE_REF,
    DOC_AI_PURCHASE_INVOICE_DOCCODE,
    DOC_AI_PURCHASE_INVOICE_CORRESPONDENCE_TYPE,
    reset_llm_extraction,
    resolve_fe_entity,
    save_llm_extraction,
    save_document_phc_origin,
    save_document_adjusted_lines,
    _score_phc_origin_candidate,
    _match_document_lines_to_origin,
    _phc_contract_flow_stages,
    _normalize_document_integration_access,
    _correspondence_file_name,
    _correspondence_company_folder,
    _ensure_phc_provisional_article,
    _is_provisional_purchase_source_type,
    _write_document_ai_pdf,
    _split_phc_line_design,
    _expand_phc_invoice_lines,
    _phc_base_currency_per_euro,
    _phc_local_amount,
    _phc_tax_configuration,
    _phc_tax_code,
)
from services import document_ai_service


class DocumentAiPhcOriginTests(unittest.TestCase):
    def test_provisional_invoice_permission_is_a_known_integration_type(self):
        permissions = _normalize_document_integration_access({'provisional_invoice': True})

        self.assertTrue(permissions['provisional_invoice'])

    def test_supplier_invoice_is_eligible_for_provisional_purchase_submission(self):
        self.assertTrue(_is_provisional_purchase_source_type('invoice'))
        self.assertTrue(_is_provisional_purchase_source_type('provisional_invoice'))
        self.assertFalse(_is_provisional_purchase_source_type('delivery_note'))
        self.assertEqual(DOC_AI_PURCHASE_INVOICE_DOCCODE, 55)
        self.assertEqual(DOC_AI_PURCHASE_INVOICE_CORRESPONDENCE_TYPE, 'FAC')

    def test_provisional_invoice_tax_rate_must_exist_in_phc_configuration(self):
        by_rate = {Decimal('0.00'): 5, Decimal('20.00'): 2}

        self.assertEqual(_phc_tax_code(Decimal('20'), by_rate), 2)
        with self.assertRaisesRegex(ValueError, '17.00%'):
            _phc_tax_code(Decimal('17'), by_rate)

    def test_duplicate_tax_rates_use_the_first_phc_table(self):
        cursor = MagicMock()
        cursor.execute.return_value.fetchall.return_value = [
            (1, Decimal('5.50')),
            (2, Decimal('20.00')),
            (6, Decimal('20.00')),
        ]

        by_code, by_rate = _phc_tax_configuration(cursor)

        self.assertEqual(by_code[6], Decimal('20.00'))
        self.assertEqual(by_rate[Decimal('20.00')], 2)

    def test_phc_currency_factor_uses_median_of_existing_documents(self):
        cursor = MagicMock()
        cursor.execute.return_value.fetchall.return_value = [
            (Decimal('200.482000'),),
            (Decimal('1.000000'),),
            (Decimal('200.482000'),),
        ]

        factor = _phc_base_currency_per_euro(cursor)

        self.assertEqual(factor, Decimal('200.482000'))
        self.assertEqual(_phc_local_amount(Decimal('375'), factor), Decimal('75180.75000'))
        self.assertEqual(_phc_local_amount(Decimal('375'), factor, whole=True), Decimal('75181'))

    def test_generic_provisional_article_is_reused_when_it_exists(self):
        cursor = MagicMock()
        cursor.execute.return_value.fetchone.return_value = (
            'ST-GENERIC', DOC_AI_PROVISIONAL_ARTICLE_REF, 'ARTIGO GENÉRICO - DOCUMENT AI',
        )

        with patch.object(document_ai_service, '_phc_insert_values') as insert:
            result = _ensure_phc_provisional_article(cursor, 'tester', document_ai_service._now())

        self.assertEqual(result['ref'], DOC_AI_PROVISIONAL_ARTICLE_REF)
        self.assertEqual(result['stamp'], 'ST-GENERIC')
        insert.assert_not_called()

    def test_pdf_is_written_directly_over_smb_without_local_mount(self):
        target = {
            'storage': 'smb',
            'unc_path': r'\\10.0.1.11\ged\HSOLS_FR\FACTURATION_FOURNISSEURS\invoice.pdf',
            'write_path': r'\\10.0.1.11\ged\HSOLS_FR\FACTURATION_FOURNISSEURS\invoice.pdf',
            'file_name': 'invoice.pdf',
        }
        handle = MagicMock()
        context = MagicMock()
        context.__enter__.return_value = handle
        context.__exit__.return_value = False

        with patch.object(document_ai_service, '_document_ai_smb_session') as session, patch(
            'smbclient.makedirs'
        ) as makedirs, patch('smbclient.path.exists', side_effect=[False, False]), patch(
            'smbclient.open_file', return_value=context
        ) as open_file, patch('smbclient.replace') as replace:
            created = _write_document_ai_pdf(target, b'%PDF-test')

        self.assertTrue(created)
        session.assert_called_once_with(target['unc_path'])
        makedirs.assert_called_once_with(
            r'\\10.0.1.11\ged\HSOLS_FR\FACTURATION_FOURNISSEURS', exist_ok=True,
        )
        open_file.assert_called_once()
        handle.write.assert_called_once_with(b'%PDF-test')
        replace.assert_called_once()

    def test_long_fn_design_is_split_on_words_and_ordered_by_lordem(self):
        description = (
            'Nos interventions en matière comptable relatives au suivi courant '
            'de votre dossier pendant le mois de mai'
        )

        chunks = _split_phc_line_design(description)
        expanded = _expand_phc_invoice_lines([{
            'description': description,
            'qty': Decimal('1.00'),
            'net': Decimal('375.00'),
        }])

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 60 for chunk in chunks))
        self.assertEqual(' '.join(chunks), description)
        self.assertEqual([row['lordem'] for row in expanded], [1000, 2000])
        self.assertFalse(expanded[0]['continuation'])
        self.assertTrue(expanded[1]['continuation'])

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

    def test_group_entity_resolution_uses_configured_phc_companies(self):
        configured = [{
            'FEID': 1,
            'NOME': 'HSOLS FRANCE',
            'NOMEFISCAL': 'HSOLS FRANCE SAS',
            'NIF': '46804213593',
            'PHC_DB': 'HSOLS_FR',
            'PHC_SERVER': '10.0.1.12',
        }]
        with patch.object(document_ai_service, '_configured_phc_sources', return_value=configured):
            result = resolve_fe_entity('HSOLS FRANCE')

        self.assertEqual(result['feid'], 1)
        self.assertEqual(result['name'], 'HSOLS FRANCE SAS')
        self.assertEqual(result['matched_by'], 'name')

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

    def test_correspondence_file_name_uses_role_number_title_and_date(self):
        result = _correspondence_file_name({
            'mail_category': 'legal',
            'external_party_role': 'customer',
            'mail_title': 'Mise en demeure',
            'document_date': '2026-07-10',
        }, 404, {
            'name': 'Caroline Pires',
            'customer_no': 1234,
        })

        self.assertEqual(result, 'JUR-404-1234-CAROLINE PIRES-MISE EN DEMEURE-2026-07-10.pdf')

    def test_correspondence_company_folder_supports_all_intersol_variants(self):
        self.assertEqual(
            _correspondence_company_folder({'name': 'INTERSOL ALSACE'}, {'phc_db': 'INTERSOL'}),
            'HSOLS_INTERSOL_AL',
        )
        self.assertEqual(
            _correspondence_company_folder({'name': 'INTERSOL LORRAINE'}, {'phc_db': 'INTERSOL'}),
            'HSOLS_INTERSOL_LOR',
        )

    def test_submit_correspondence_inserts_cr_and_linked_attachment(self):
        cursor = MagicMock()

        def execute(query, *params):
            cursor.fetchone.return_value = None
            if 'sp_getapplock' in query:
                cursor.fetchone.return_value = (0,)
            elif 'MAX(CAST' in query:
                cursor.fetchone.return_value = (2864,)
            return cursor

        cursor.execute.side_effect = execute
        connection = MagicMock()
        connection.cursor.return_value = cursor
        document = {
            'document_type': 'mail',
            'mail_category': 'general',
            'mail_title': 'Caution bancaire',
            'document_date': '2026-05-22',
            'external_party_role': 'supplier',
            'customer': {'feid': 1, 'name': 'HSOLS FRANCE'},
            'supplier': {'name': 'BTP BANQUE', 'supplier_no': 30779},
        }
        source = {'kind': 'phc', 'phc_db': 'HSOLS_FR', 'phc_server': '10.0.1.12'}
        inserted = []
        with tempfile.TemporaryDirectory() as directory:
            target = os.path.join(directory, 'COR-2865.pdf')
            ged = {
                'file_name': 'COR-2865-30779-BTP BANQUE-CAUTION BANCAIRE-2026-05-22.pdf',
                'unc_path': r'\\10.0.1.11\ged\HSOLS_FR\COURRIER\2026\COR-2865.pdf',
                'write_path': target,
            }
            with patch.object(document_ai_service, '_phc_origin_source', return_value=source), patch(
                'services.phc_user_import_service._phc_conn_str', return_value='PHC-CONNECTION'
            ), patch('pyodbc.connect', return_value=connection), patch.object(
                document_ai_service, '_phc_correspondence_party',
                return_value={'name': 'BTP BANQUE', 'no': 30779, 'estab': 0, 'origin': 'FL', 'role': 'supplier'},
            ), patch.object(
                document_ai_service, '_phc_correspondence_user',
                return_value={'no': 156, 'name': 'Utilizador', 'initials': 'UT', 'code': 'user'},
            ), patch.object(
                document_ai_service, '_correspondence_ged_paths', return_value=ged,
            ), patch.object(
                document_ai_service, '_phc_insert_values',
                side_effect=lambda _cursor, table, values: inserted.append((table, values)),
            ):
                result = submit_correspondence_to_phc(document, b'%PDF-test', 'mail.pdf', 'user')

            self.assertTrue(os.path.isfile(target))

        self.assertEqual(result['reference'], 2865)
        self.assertEqual([item[0] for item in inserted], ['CR', 'ANEXOS'])
        self.assertEqual(inserted[0][1]['origem'], 'FL')
        self.assertEqual(inserted[1][1]['oritable'], 'CR')
        self.assertEqual(inserted[1][1]['recstamp'], inserted[0][1]['crstamp'])
        self.assertTrue(inserted[1][1]['uniqueid'].startswith('DOC_AI:'))
        connection.commit.assert_called_once()

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
