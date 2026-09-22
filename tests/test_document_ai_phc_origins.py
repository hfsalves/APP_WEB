import json
import inspect
import os
import tempfile
import unittest
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch
from unittest.mock import MagicMock

from flask import Flask

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
    mark_document_as_provisional_invoice,
    mark_document_control_ok,
    mark_document_validation_error,
    require_document_control_ok,
    save_document_phc_origin,
    save_document_adjusted_lines,
    save_document_draft,
    DocumentDraftConflictError,
    _score_phc_origin_candidate,
    _match_document_lines_to_origin,
    _phc_contract_flow_stages,
    _normalize_document_integration_access,
    _correspondence_file_name,
    _correspondence_company_folder,
    _correspondence_ged_paths,
    _phc_correspondence_agency_origin,
    _phc_text_column_limit,
    _phc_provisional_purchase_doc_config,
    _phc_provisional_value,
    _provisional_invoice_ged_paths,
    _ensure_phc_provisional_article,
    _is_provisional_purchase_source_type,
    _write_document_ai_pdf,
    _write_confirmed_ged_targets,
    _split_phc_line_design,
    _expand_phc_invoice_lines,
    _phc_base_currency_per_euro,
    _phc_local_amount,
    _phc_provisional_effective_datetime,
    _phc_tax_configuration,
    _phc_tax_code,
    _doc_queryset_sql,
    _document_inbox_global_total,
    _normalize_document_inbox_view,
    _document_inbox_scope_sql,
    classify_document_type,
)
from services import document_ai_service


class DocumentAiPhcOriginTests(unittest.TestCase):
    def test_provisional_date_moves_to_first_day_after_the_company_close_date(self):
        cursor = MagicMock()
        cursor.execute.return_value.fetchone.return_value = ('17.08.2026',)

        effective_at = _phc_provisional_effective_datetime(
            cursor,
            'HSOLS_FR',
            datetime(2026, 8, 10, 0, 0, 0),
            datetime(2026, 9, 1, 14, 23, 45, 123456),
        )

        self.assertEqual(effective_at, datetime(2026, 8, 18, 14, 23, 45, 123456))

    def test_provisional_date_after_year_end_closing_uses_next_calendar_day(self):
        cursor = MagicMock()
        cursor.execute.return_value.fetchone.return_value = ('31.12.2026',)

        effective_at = _phc_provisional_effective_datetime(
            cursor,
            'HSOLS_FR',
            datetime(2026, 12, 15, 0, 0, 0),
            datetime(2027, 1, 3, 8, 5, 6),
        )

        self.assertEqual(effective_at, datetime(2027, 1, 1, 8, 5, 6))

    def test_document_draft_updates_persistent_result_and_cached_extraction(self):
        moment = datetime(2026, 9, 1, 10, 30, 0)
        cached = {'version': 4, 'document': {'document_number': 'OLD'}}
        document = SimpleNamespace(
            docinstamp='DOC-1', dtalt=moment, dtcri=moment,
            processing_meta_json=json.dumps({'llm_full_extraction': cached}),
            json_resultado='{}', feid=None, fornecedor_no=None,
            fornecedor_nome_detetado='', fornecedor_nif_detetado='',
            doc_type_detected='unknown', invoice_type='unknown', useralteracao='',
        )
        locked = MagicMock()
        locked.mappings.return_value.first.return_value = {'DTALT': moment, 'DTCRI': moment}
        draft = {
            'document_type': 'invoice', 'invoice_type': 'standard',
            'document_number': 'FAC-22', 'customer': {'feid': 8},
            'supplier': {'supplier_no': 42, 'name': 'Fornecedor', 'tax_id': '123'},
        }
        with patch.object(document_ai_service, '_ensure_document_ai_schema'), patch.object(
            document_ai_service.db.session, 'execute', return_value=locked
        ), patch.object(
            document_ai_service.db.session, 'get', return_value=document
        ), patch.object(
            document_ai_service.db.session, 'commit'
        ) as commit, patch.object(document_ai_service, '_now', return_value=moment), patch.object(
            document_ai_service, '_document_log'
        ):
            result = save_document_draft(
                'DOC-1',
                {'expected_version': moment.isoformat(timespec='microseconds'), 'view': 'home', 'document': draft},
                'tester',
            )

        persisted = json.loads(document.json_resultado)
        meta = json.loads(document.processing_meta_json)
        self.assertEqual(persisted['document_number'], 'FAC-22')
        self.assertEqual(meta['llm_full_extraction']['document']['document_number'], 'FAC-22')
        self.assertEqual(document.feid, 8)
        self.assertEqual(document.fornecedor_no, 42)
        self.assertEqual(result['version'], moment.isoformat(timespec='microseconds'))
        commit.assert_called_once()

    def test_management_draft_accepts_the_complete_review_snapshot(self):
        moment = datetime(2026, 9, 1, 10, 30, 0)
        previous = {
            'document_type': 'invoice',
            'invoice_type': 'services',
            'document_number': 'FAC-22',
            'customer': {'feid': 8, 'name': 'INTERSOL'},
            'supplier': {'supplier_no': 42, 'name': 'Fornecedor'},
            'lines': [{'description': 'Original', 'qty': 1}],
            'taxes': [],
        }
        reviewed = {
            **previous,
            'customer': {
                **previous['customer'],
                'phc_database': 'INTERSOL',
                'ged_folder': 'HSOLS_INTERSOL_LOR',
            },
            'lines': [{'description': 'Revista no CdG', 'qty': 1}],
            'taxes': [{'tax_rate': 20, 'tax_amount': 10}],
            'origin_project': {'ccusto': 'FR0001'},
        }
        document = SimpleNamespace(
            docinstamp='DOC-2', dtalt=moment, dtcri=moment,
            processing_meta_json=json.dumps({'llm_full_extraction': {
                'version': 4, 'document': previous,
            }}),
            json_resultado=json.dumps(previous), feid=8, fornecedor_no=42,
            fornecedor_nome_detetado='Fornecedor', fornecedor_nif_detetado='',
            doc_type_detected='invoice', invoice_type='services', useralteracao='',
            management_validated=False,
        )
        locked = MagicMock()
        locked.mappings.return_value.first.return_value = {'DTALT': moment, 'DTCRI': moment}
        with patch.object(document_ai_service, '_ensure_document_ai_schema'), patch.object(
            document_ai_service.db.session, 'execute', return_value=locked
        ), patch.object(
            document_ai_service.db.session, 'get', return_value=document
        ), patch.object(
            document_ai_service.db.session, 'commit'
        ), patch.object(document_ai_service, '_now', return_value=moment), patch.object(
            document_ai_service, '_document_log'
        ):
            save_document_draft(
                'DOC-2',
                {'expected_version': moment.isoformat(timespec='microseconds'), 'view': 'management', 'document': reviewed},
                'tester',
            )

        persisted = json.loads(document.json_resultado)
        self.assertEqual(persisted['customer']['ged_folder'], 'HSOLS_INTERSOL_LOR')
        self.assertEqual(persisted['lines'][0]['description'], 'Revista no CdG')
        self.assertEqual(persisted['origin_project']['ccusto'], 'FR0001')

    def test_cached_document_preserves_manually_selected_intersol_agency_across_views(self):
        moment = datetime(2026, 9, 1, 10, 30, 0)
        document = SimpleNamespace(
            docinstamp='DOC-3118', dtalt=moment, dtcri=moment,
            processing_meta_json=json.dumps({'llm_full_extraction': {
                'version': 4,
                'document': {'customer': {
                    'feid': 2, 'name': 'INTERSOL',
                    'ged_folder': 'HSOLS_INTERSOL_LOR',
                    'ged_folder_manually_selected': True,
                }},
            }}),
            processing_status='parsed_ok', reception_validated=True,
            management_validated=False, accounting_validated=False,
        )
        with patch.object(document_ai_service.db.session, 'get', return_value=document), patch.object(
            document_ai_service, '_fe_entity_by_id', return_value={
                'feid': 2, 'phc_database': 'INTERSOL', 'ged_folder': 'HSOLS_INTERSOL_AL',
            }
        ):
            cached = get_cached_llm_extraction('DOC-3118')

        self.assertEqual(cached['document']['customer']['ged_folder'], 'HSOLS_INTERSOL_LOR')
        self.assertEqual(cached['document']['customer']['phc_database'], 'INTERSOL')

    def test_cached_document_restores_the_stored_fe_entity_for_management(self):
        moment = datetime(2026, 9, 1, 10, 30, 0)
        document = SimpleNamespace(
            docinstamp='DOC-ENTITY', dtalt=moment, dtcri=moment, feid=7,
            processing_meta_json=json.dumps({'llm_full_extraction': {
                'version': 4,
                'document': {'customer': {}},
                'matching': {'customer_matched': False, 'supplier_query': {}},
            }}),
            processing_status='provisional_invoice', reception_validated=True,
            management_validated=False, accounting_validated=False,
        )
        with patch.object(document_ai_service.db.session, 'get', return_value=document), patch.object(
            document_ai_service, '_fe_entity_by_id', return_value={
                'feid': 7,
                'name': 'BETÃOCONCEPT',
                'tax_id': '507000000',
                'phc_database': 'HSOLS_PT',
                'ged_folder': 'HSOLS_PT',
            }
        ):
            cached = get_cached_llm_extraction('DOC-ENTITY')

        customer = cached['document']['customer']
        self.assertEqual(customer['feid'], 7)
        self.assertEqual(customer['name'], 'BETÃOCONCEPT')
        self.assertEqual(customer['tax_id'], '507000000')
        self.assertTrue(cached['matching']['customer_matched'])
        self.assertEqual(cached['matching']['supplier_query']['feid'], 7)

    def test_document_draft_detects_an_optimistic_lock_conflict(self):
        current = datetime(2026, 9, 1, 10, 31, 0)
        locked = MagicMock()
        locked.mappings.return_value.first.return_value = {'DTALT': current, 'DTCRI': current}
        with patch.object(document_ai_service, '_ensure_document_ai_schema'), patch.object(
            document_ai_service.db.session, 'execute', return_value=locked
        ), patch.object(document_ai_service.db.session, 'rollback') as rollback:
            with self.assertRaises(DocumentDraftConflictError):
                save_document_draft(
                    'DOC-1',
                    {'expected_version': '2026-09-01T10:00:00.000000', 'document': {}},
                    'tester',
                )

        rollback.assert_called_once()

    def test_accounting_cannot_persist_analysis_draft(self):
        moment = datetime(2026, 9, 1, 10, 31, 0)
        document = SimpleNamespace(dtalt=moment, dtcri=moment)
        locked = MagicMock()
        locked.mappings.return_value.first.return_value = {'DTALT': moment, 'DTCRI': moment}
        with patch.object(document_ai_service, '_ensure_document_ai_schema'), patch.object(
            document_ai_service.db.session, 'execute', return_value=locked
        ), patch.object(document_ai_service.db.session, 'get', return_value=document):
            with self.assertRaisesRegex(ValueError, 'apenas de consulta'):
                save_document_draft(
                    'DOC-1',
                    {'expected_version': moment.isoformat(timespec='microseconds'), 'view': 'accounting', 'document': {}},
                    'tester',
                )

    def test_inbox_query_filters_by_group_entity(self):
        where_sql, params = _doc_queryset_sql({'feid': '8'})

        self.assertIn('D.FEID', where_sql)
        self.assertEqual(params['feid'], 8)

    def test_inbox_global_total_does_not_depend_on_active_filters(self):
        query_result = MagicMock()
        query_result.scalar.return_value = 27
        with patch(
            'services.document_ai_distribution_service.ensure_document_ai_distribution_schema'
        ), patch.object(document_ai_service.db.session, 'execute', return_value=query_result) as execute:
            total = _document_inbox_global_total()

        self.assertEqual(total, 27)
        sql = str(execute.call_args.args[0])
        self.assertIn('COUNT_BIG(1)', sql)
        self.assertIn('split_output.batch_id', sql)

    def test_inbox_hides_a_source_only_after_it_was_split(self):
        scope_sql = _document_inbox_scope_sql('home')

        self.assertIn('ISJSON', scope_sql)
        self.assertIn('split_output.batch_id', scope_sql)
        self.assertIn('IS NULL', scope_sql)

    def test_inbox_view_fails_closed_to_home(self):
        self.assertEqual(_normalize_document_inbox_view('management'), 'management')
        self.assertEqual(_normalize_document_inbox_view('accounting'), 'accounting')
        self.assertEqual(_normalize_document_inbox_view('invalid-view'), 'home')
        self.assertEqual(_normalize_document_inbox_view(''), 'home')

    def test_marking_inbox_document_as_provisional_invoice_is_persistent(self):
        document = SimpleNamespace(
            docinstamp='DOC-1', file_hash='abc123', processing_meta_json='{}',
            processing_stage='parsed', processing_status='parsed_ok', dtalt=None,
            useralteracao='', doc_type_detected='invoice',
            reception_validated=False, reception_validated_at=None, reception_validated_by='',
            management_validated=False, management_validated_at=None, management_validated_by='',
            accounting_validated=False,
        )
        with patch.object(document_ai_service.db.session, 'get', return_value=document), patch.object(
            document_ai_service, 'get_phc_origins_from_meta', return_value=[{'stamp': 'FO-1'}]
        ), patch.object(
            document_ai_service.db.session, 'commit'
        ) as commit, patch(
            'services.document_ai_distribution_service.apply_document_distribution',
            return_value={'ok': True},
        ) as distribute:
            result = mark_document_as_provisional_invoice(
                'DOC-1',
                {'fostamp': 'FO-1', 'document_number': '159432', 'phc_database': 'HSOLS_FR'},
                'ldias',
                'abc123',
            )

        meta = json.loads(document.processing_meta_json)
        self.assertEqual(result['status'], 'provisional_invoice')
        self.assertEqual(document.processing_status, 'provisional_invoice')
        self.assertEqual(document.processing_stage, 'phc_integrated')
        self.assertEqual(meta['phc_integration']['type'], 'provisional_invoice')
        self.assertEqual(meta['phc_integration']['fostamp'], 'FO-1')
        self.assertEqual(meta['workflow']['validation_status'], 'management')
        self.assertEqual(meta['workflow']['distribution_status'], 'completed')
        self.assertTrue(document.reception_validated)
        self.assertFalse(document.management_validated)
        self.assertEqual([call.args[1] for call in distribute.call_args_list], ['home'])
        self.assertEqual(commit.call_count, 2)

    def test_control_ok_persists_reviewed_document_and_unlocks_validation(self):
        cached = {'version': 4, 'document': {}}
        document = SimpleNamespace(
            docinstamp='DOC-1', processing_meta_json=json.dumps({'llm_full_extraction': cached}),
            json_resultado='{}', feid=None, fornecedor_no=None,
            fornecedor_nome_detetado='', fornecedor_nif_detetado='', processing_stage='llm_extracted',
            processing_status='review_required', last_processing_error='', dtalt=None, useralteracao='',
        )
        reviewed = {
            'document_type': 'invoice', 'document_number': 'FAC-1',
            'customer': {'feid': 8},
            'supplier': {'supplier_no': 42, 'name': 'Fornecedor', 'tax_id': '123'},
            'lines': [{'description': 'Linha', 'qty': 1}],
        }
        with patch.object(document_ai_service.db.session, 'get', return_value=document), patch.object(
            document_ai_service, 'get_phc_origins_from_meta', return_value=[{'stamp': 'FO-1'}]
        ), patch.object(document_ai_service.db.session, 'commit') as commit:
            result = mark_document_control_ok('DOC-1', 'tester', reviewed)
            require_document_control_ok('DOC-1')

        meta = json.loads(document.processing_meta_json)
        self.assertTrue(result['workflow']['control_ok'])
        self.assertEqual(meta['llm_full_extraction']['document']['supplier']['supplier_no'], 42)
        self.assertEqual(document.processing_stage, 'controlled')
        commit.assert_called_once()

    def test_control_ok_rejects_an_incomplete_document(self):
        document = SimpleNamespace(
            docinstamp='DOC-1', processing_meta_json=json.dumps({'llm_full_extraction': {'version': 4, 'document': {}}}),
        )
        with patch.object(document_ai_service.db.session, 'get', return_value=document):
            with self.assertRaisesRegex(ValueError, 'sociedade'):
                mark_document_control_ok('DOC-1', 'tester', {'document_type': 'invoice'})

    def test_validation_error_keeps_document_recoverable(self):
        document = SimpleNamespace(
            docinstamp='DOC-1', processing_meta_json=json.dumps({'workflow': {'control_ok': True}}),
            last_processing_error='', processing_stage='controlled', dtalt=None, useralteracao='',
        )
        with patch.object(document_ai_service.db.session, 'get', return_value=document), patch.object(
            document_ai_service.db.session, 'commit'
        ):
            mark_document_validation_error('DOC-1', 'falha PHC', 'tester')

        meta = json.loads(document.processing_meta_json)
        self.assertTrue(meta['workflow']['control_ok'])
        self.assertEqual(meta['workflow']['validation_status'], 'error')
        self.assertEqual(document.processing_stage, 'validation_error')

    def test_repeating_completion_keeps_the_same_phc_reference(self):
        document = SimpleNamespace(
            docinstamp='DOC-1', file_hash='abc123', processing_meta_json=json.dumps({'workflow': {'control_ok': True}}),
            processing_stage='controlled', processing_status='parsed_ok', dtalt=None, useralteracao='',
            doc_type_detected='invoice',
            reception_validated=False, reception_validated_at=None, reception_validated_by='',
            management_validated=True, management_validated_at=None, management_validated_by='tester',
            accounting_validated=False,
        )
        result_data = {'fostamp': 'FO-1', 'document_number': '159432', 'phc_database': 'HSOLS_FR', 'duplicate': True}
        with patch.object(document_ai_service.db.session, 'get', return_value=document), patch.object(
            document_ai_service.db.session, 'commit'
        ), patch(
            'services.document_ai_distribution_service.apply_document_distribution',
            return_value={'ok': True},
        ):
            mark_document_as_provisional_invoice('DOC-1', result_data, 'tester', 'abc123')
            mark_document_as_provisional_invoice('DOC-1', result_data, 'tester', 'abc123')

        meta = json.loads(document.processing_meta_json)
        self.assertEqual(meta['phc_integration']['fostamp'], 'FO-1')
        self.assertTrue(meta['phc_integration']['duplicate'])

    def test_provisional_invoice_permission_is_a_known_integration_type(self):
        permissions = _normalize_document_integration_access({'provisional_invoice': True})

        self.assertTrue(permissions['provisional_invoice'])
        self.assertFalse(_normalize_document_integration_access({})['provisional_invoice'])

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

    def test_credit_note_provisional_values_are_always_positive(self):
        for value in ('-2.50', Decimal('-120.45'), -20):
            self.assertGreater(_phc_provisional_value(value, credit_note=True), 0)
        self.assertEqual(
            _phc_provisional_value(Decimal('-120.45'), credit_note=True),
            Decimal('120.45'),
        )
        self.assertEqual(
            _phc_provisional_value(Decimal('-120.45'), credit_note=False),
            Decimal('-120.45'),
        )

    def test_credit_note_uses_avoir_purchase_type_but_stays_in_fac_correspondence_circuit(self):
        cursor = MagicMock()
        cursor.execute.return_value.fetchone.return_value = None

        config = _phc_provisional_purchase_doc_config(cursor, 'HSOLS_FR', 'credit_note')

        self.assertTrue(config['is_credit_note'])
        self.assertEqual(config['doccode'], 3)
        self.assertEqual(config['docname'], 'V/Avoir')
        self.assertEqual(config['file_prefix'], 'FAC')
        self.assertEqual(config['correspondence_type'], 'FAC')

    def test_negative_invoice_values_do_not_classify_the_document_as_credit_note(self):
        result = classify_document_type(
            'FACTURE N° F-2026-15\nTotal HT -120,45 EUR\nTVA -24,09 EUR\nTotal TTC -144,54 EUR'
        )

        self.assertEqual(result['doc_type'], 'invoice')

    def test_provisional_purchase_copies_fl_country_to_fo(self):
        supplier_source = inspect.getsource(document_ai_service._phc_provisional_supplier)
        submission_source = inspect.getsource(document_ai_service.submit_provisional_invoice_to_phc)

        self.assertIn("ISNULL(PAIS, '')", supplier_source)
        self.assertIn("'currency', 'country'", supplier_source)
        self.assertIn("'pais': str(supplier.get('country') or '').strip()", submission_source)

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

    def test_ged_links_are_only_available_after_every_copy_is_confirmed(self):
        targets = [
            {'write_path': '/ged/correspondence.pdf'},
            {'write_path': '/ged/purchase.pdf'},
        ]
        with patch.object(document_ai_service, '_write_document_ai_pdf', side_effect=[True, False]), patch.object(
            document_ai_service, '_remove_document_ai_pdf',
        ) as remove:
            with self.assertRaisesRegex(RuntimeError, 'todos os destinos'):
                _write_confirmed_ged_targets(targets, b'%PDF')
        remove.assert_called_once_with(targets[0])

        with patch.object(document_ai_service, '_write_document_ai_pdf', return_value=True), patch.object(
            document_ai_service, '_document_ai_pdf_is_confirmed', return_value=True,
        ):
            self.assertEqual(
                _write_confirmed_ged_targets(targets, b'%PDF'),
                ['/ged/correspondence.pdf', '/ged/purchase.pdf'],
            )

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
        self.assertEqual(result['phc_database'], 'HSOLS_FR')
        self.assertEqual(result['ged_folder'], 'HSOLS_FR')
        self.assertEqual(result['matched_by'], 'name')

    def test_betaoconcept_ged_folder_comes_from_fe_phc_database(self):
        configured = [{
            'FEID': 2,
            'NOME': 'Betãoconcept',
            'NOMEFISCAL': 'Betãoconcept, Lda',
            'NIF': '510000000',
            'PHC_DB': 'HSOLS_PT',
            'PHC_SERVER': '10.0.1.12',
        }]
        with patch.object(document_ai_service, '_configured_phc_sources', return_value=configured):
            result = resolve_fe_entity('Betãoconcept')

        self.assertEqual(result['feid'], 2)
        self.assertEqual(result['phc_database'], 'HSOLS_PT')
        self.assertEqual(result['ged_folder'], 'HSOLS_PT')

    def test_contract_dossiers_are_discovered_from_each_phc_catalog(self):
        cursor = MagicMock()
        cursor.execute.return_value.fetchall.return_value = [
            (119, 'Contrat'),
            (128, 'Contrat Sous-Traitant'),
        ]

        stages = _phc_contract_flow_stages(cursor)

        self.assertEqual([stage['ndos'] for stage in stages], [119, 128])
        self.assertEqual([stage['document_type'] for stage in stages], ['contract', 'contract'])
        self.assertEqual(stages[0]['label'], 'Contrato')

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
            'estab': 1,
        })

        self.assertEqual(result, 'L-404-1234_1-CAROLINE PIRES-MISE EN DEMEURE-2026-07-10.pdf')

    def test_correspondence_company_folder_uses_fe_database_and_explicit_branch(self):
        self.assertEqual(
            _correspondence_company_folder({'name': 'INTERSOL SAS'}, {'phc_db': 'INTERSOL'}),
            'HSOLS_INTERSOL_AL',
        )
        self.assertEqual(
            _correspondence_company_folder(
                {'name': 'INTERSOL SAS', 'ged_folder': 'HSOLS_INTERSOL_LOR'},
                {'phc_db': 'INTERSOL'},
            ),
            'HSOLS_INTERSOL_LOR',
        )

    def test_intersol_correspondence_origin_follows_selected_ged_branch(self):
        source = {'phc_db': 'INTERSOL'}

        self.assertEqual(
            _phc_correspondence_agency_origin(
                {'ged_folder': 'HSOLS_INTERSOL_LOR'}, source,
            ),
            'INTERSOL-LORRAINE',
        )
        self.assertEqual(
            _phc_correspondence_agency_origin(
                {'ged_folder': 'HSOLS_INTERSOL_CH'}, source,
            ),
            'INTERSOL-CHAMPAGNE',
        )
        self.assertEqual(_phc_correspondence_agency_origin({}, {'phc_db': 'HSOLS_FR'}), '')

    def test_phc_text_column_limit_uses_real_schema_width(self):
        cursor = MagicMock()
        cursor.execute.return_value.fetchone.return_value = (4,)

        self.assertEqual(_phc_text_column_limit(cursor, 'FN', 'UNIDADE', 6), 4)

    def test_credit_note_ged_path_keeps_fac_prefix_and_marks_document_number_as_nc(self):
        application = Flask(__name__)
        with application.app_context():
            result = _provisional_invoice_ged_paths(
                {
                    'customer': {'ged_folder': 'HSOLS_FR'},
                    'document_type': 'credit_note',
                    'document_number': '50980',
                },
                {'phc_db': 'HSOLS_FR'},
                {'name': 'GM MECANIQUE', 'no': 31243, 'estab': 0},
                3268,
                datetime(2026, 7, 10, 12, 0),
                'FAC',
            )

        self.assertEqual(len(result), 2)
        self.assertTrue(all(item['file_name'].startswith('FAC-3268-') for item in result))
        self.assertTrue(all(item['file_name'].endswith('-NC-50980.pdf') for item in result))
        self.assertTrue(all('\\2026\\7 JUIL 26\\' in item['unc_path'] for item in result))

    def test_credit_note_ged_number_does_not_repeat_existing_nc_prefix(self):
        application = Flask(__name__)
        with application.app_context():
            result = _provisional_invoice_ged_paths(
                {
                    'customer': {'ged_folder': 'HSOLS_FR'},
                    'document_type': 'credit_note',
                    'document_number': 'NC-50980',
                },
                {'phc_db': 'HSOLS_FR'},
                {'name': 'GM MECANIQUE', 'no': 31243, 'estab': 0},
                3268,
                datetime(2026, 7, 10, 12, 0),
            )

        self.assertTrue(all(item['file_name'].endswith('-NC-50980.pdf') for item in result))

    def test_correspondence_ged_path_uses_received_mail_structure(self):
        application = Flask(__name__)
        with application.app_context():
            result = _correspondence_ged_paths({
                'customer': {'ged_folder': 'HSOLS_PT'},
                'mail_category': 'legal',
                'mail_title': 'Mise en demeure',
                'document_date': '2026-08-11',
            }, {'phc_db': 'HSOLS_PT'}, 15, {
                'name': 'Remetente',
            }, datetime(2026, 8, 11, 10, 30))

        self.assertEqual(result['category'], 'COURRIER_INTERNE_EXTERIEUR')
        self.assertEqual(result['inbox_folder'], 'Courriers Reçus')
        self.assertIn(
            r'\HSOLS_PT\COURRIER_INTERNE_EXTERIEUR\Courriers Reçus\2026\8 AOUT 26',
            result['unc_path'],
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
        self.assertEqual(inserted[0][1]['tipo'], 'L')
        self.assertEqual(inserted[0][1]['pasta'], 'LETTRE')
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
            document_ai_service, '_refresh_document_duplicate_state', return_value=[]
        ), patch.object(document_ai_service.db.session, 'commit'):
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

    def test_selected_project_prioritizes_without_rejecting_other_projects(self):
        document = {
            'document_date': '2026-04-30',
            'origin_project': {'ccusto': 'OBRA-A'},
            'lines': [],
            'totals': {},
        }
        matching = {
            'ndos': 102, 'document_type': 'purchase_order', 'date': '2026-04-30',
            'ccusto': 'OBRA-A',
        }
        other = {**matching, 'ccusto': 'OBRA-B'}

        matching_score, matching_reasons = _score_phc_origin_candidate(matching, document, [])
        other_score, other_reasons = _score_phc_origin_candidate(other, document, [])

        self.assertGreater(matching_score, other_score)
        self.assertIn('Mesma Obra', matching_reasons)
        self.assertIn('Outra Obra', other_reasons)

    def test_origin_search_does_not_filter_candidates_by_selected_project(self):
        source = inspect.getsource(document_ai_service.search_phc_document_origins)

        self.assertNotIn('project_filter_sql', source)
        self.assertNotIn('header_params.append(project_ccusto)', source)

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
