import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from services import document_ai_service as svc
from services.document_ai_service import (
    _accounting_persisted_document,
    _assert_document_draft_mutable,
    _assert_exact_purchase_attachment,
    _assert_final_purchase_content,
    _assert_final_purchase_lineage,
    _effective_portal_lines,
    _has_complete_purchase_finalization,
    _integrate_accounting_purchase,
    validate_document_inbox_stage,
)
from services.document_ai_preinvoice_service import payload_fingerprint


class DocumentAiPurchaseFinalizationTests(unittest.TestCase):
    @staticmethod
    def document(document_type='invoice'):
        payload = {
            'document_type': document_type,
            'currency': 'EUR',
            'customer': {'feid': 1, 'phc_database': 'HSOLS_FR'},
            'supplier': {'supplier_no': 7, 'estab': 2},
            'lines': [],
            'totals': {},
        }
        origins = [
            {'stamp': 'BO-PROFORMA', 'ndos': 218, 'document_type': 'proforma_invoice'},
        ]
        meta = {
            'phc_operations': {
                'provisional_invoice': {
                    'status': 'confirmed',
                    'fostamp': 'FO-RECEPTION',
                    'phc_database': 'HSOLS_FR',
                },
                'preinvoice': {
                    'status': 'confirmed', 'bostamp': 'BO-PROFORMA',
                    'phc_database': 'HSOLS_FR', 'anexosstamp': 'AN-PF',
                    'ged_confirmed': True, 'approved': True, 'validated': True,
                    'team': '', 'effective_date': '2026-09-11',
                    'payload_fingerprint': payload_fingerprint(payload, origins),
                },
            },
            'phc_origins': origins,
        }
        return SimpleNamespace(
            docinstamp='DOC-1',
            processing_meta_json=json.dumps(meta),
            processing_status='parsed_ok',
            file_hash='FILE-HASH',
        ), payload

    def test_complete_finalization_requires_existing_fo_and_proforma_lines(self):
        self.assertTrue(_has_complete_purchase_finalization({
            'status': 'confirmed',
            'fostamp': 'FO-1',
            'phc_database': 'HSOLS_FR',
            'proforma_stamps': ['BO-1'],
            'final_line_count': 2,
        }))
        self.assertFalse(_has_complete_purchase_finalization({
            'status': 'confirmed',
            'fostamp': 'FO-1',
            'phc_database': 'HSOLS_FR',
            'proforma_stamps': [],
            'final_line_count': 0,
        }))

    def test_finalization_requires_one_distinct_preinvoice_line_per_effective_child(self):
        effective = _effective_portal_lines([{
            'line_id': 'SUMMARY', 'qty': 2, 'sub_lines': [
                {'subline_id': 'S1', 'qty': 1, 'phc_origin_links': [
                    {'origin_family': 'proforma_invoice', 'bistamp': 'BI-PF-1'}]},
                {'subline_id': 'S2', 'qty': 1, 'phc_origin_links': [
                    {'origin_family': 'proforma_invoice', 'bistamp': 'BI-PF-2'}]},
            ],
        }])
        _assert_final_purchase_lineage(effective, ['BI-PF-1', 'BI-PF-2'])
        with self.assertRaisesRegex(ValueError, 'exatamente uma linha PHC'):
            _assert_final_purchase_lineage(effective, ['BI-PF-1'])
        with self.assertRaisesRegex(ValueError, 'não coincide'):
            _assert_final_purchase_lineage(effective, ['BI-PF-1', 'BI-OTHER'])

    def test_credit_note_is_left_for_its_dedicated_workflow(self):
        document, payload = self.document('credit_note')
        self.assertEqual(_integrate_accounting_purchase(document, payload, 'tester', {'invoice': True}), {})

    def test_invoice_permission_is_checked_on_the_server(self):
        document, payload = self.document()
        with self.assertRaisesRegex(PermissionError, 'Sem permissão'):
            _integrate_accounting_purchase(document, payload, 'tester', {'invoice': False})

    def test_accounting_rejects_mutable_payload_and_returns_persisted_snapshot(self):
        persisted = {'document_type': 'invoice', 'lines': [{'line_id': 'L1', 'qty': 1}]}
        self.assertEqual(
            _accounting_persisted_document(persisted, dict(persisted), 'DOC-1')['lines'][0]['qty'],
            1,
        )
        changed = {'document_type': 'invoice', 'lines': [{'line_id': 'L1', 'qty': 2}]}
        with self.assertRaisesRegex(ValueError, 'nenhuma alteração foi guardada.*Responsável'):
            _accounting_persisted_document(persisted, changed, 'DOC-1')

    def test_accounting_validation_rejects_changed_document_before_preflight_or_commit(self):
        persisted = {'document_type': 'invoice', 'lines': [{'line_id': 'L1', 'qty': 1}]}
        record = SimpleNamespace(
            docinstamp='DOC-1', json_resultado=json.dumps(persisted),
            processing_meta_json='{}', invoice_type='services', doc_type_detected='invoice',
            reception_validated=True, management_validated=True, accounting_validated=False,
        )
        lock_result = Mock()
        lock_result.scalar_one.return_value = 'DOC-1'
        with patch.object(svc.db.session, 'get', return_value=record), \
                patch.object(svc.db.session, 'execute', return_value=lock_result), \
                patch.object(svc.db.session, 'refresh'), \
                patch.object(svc.db.session, 'commit') as commit, \
                patch('services.document_ai_service._document_draft_version', return_value='v1'), \
                patch('services.document_ai_service.preflight_document_inbox_stage') as preflight:
            with self.assertRaisesRegex(ValueError, 'nenhuma alteração foi guardada'):
                validate_document_inbox_stage(
                    'DOC-1', 'accounting', 'tester',
                    reviewed_document={'document_type': 'invoice', 'lines': [{'line_id': 'L1', 'qty': 99}]},
                    expected_version='v1',
                )
        preflight.assert_not_called()
        commit.assert_not_called()

    def test_no_draft_is_mutable_after_management_validation(self):
        with self.assertRaisesRegex(ValueError, 'rascunho está imutável'):
            _assert_document_draft_mutable(SimpleNamespace(management_validated=True), 'management')
        with self.assertRaisesRegex(ValueError, 'apenas de consulta'):
            _assert_document_draft_mutable(SimpleNamespace(management_validated=False), 'accounting')

    def test_purchase_attachment_must_match_portal_hash_and_stamp(self):
        _assert_exact_purchase_attachment(
            ('AN-FO', 'DOC_AI:abc123:FO'), 'ABC123', 'AN-FO',
        )
        with self.assertRaisesRegex(ValueError, 'hash do anexo.*Responsável: Receção'):
            _assert_exact_purchase_attachment(
                ('AN-FO', 'DOC_AI:other:FO'), 'ABC123', 'AN-FO',
            )
        with self.assertRaisesRegex(ValueError, 'ANEXOSSTAMP.*Responsável: Receção'):
            _assert_exact_purchase_attachment(
                ('AN-OTHER', 'DOC_AI:abc123:FO'), 'ABC123', 'AN-FO',
            )

    @staticmethod
    def _content_fixture():
        portal = [{
            'line_id': 'L1', 'portal_line_id': 'L1',
            'article_ref': 'ART', 'unit': 'UN', 'ccusto': 'C1',
            'qty': 2, 'unit_price': 5, 'net_amount': 10, 'tax_rate': 23,
            'phc_origin_links': [{'origin_family': 'proforma_invoice', 'bistamp': 'BI-PF'}],
        }]
        row = [None] * 24
        for index, value in {
            0: 'BI-PF', 1: 'BO-PF', 2: 'ART', 3: 'Artigo', 4: 2,
            9: 10, 10: 23, 14: 'UN', 15: 'C1',
        }.items():
            row[index] = value
        preinvoice = ['BO-PF', 218, 7, 1, 0, 2, 'EURO', 10, 12.3, 1]
        purchase = [
            'FO-1', 3, 'Compra', 'F1', 7, 2, None, 'EURO', 'Leitura inteligente',
            10, 12.3, None,
        ]
        document = {
            'currency': 'EUR', 'supplier': {'supplier_no': 7, 'estab': 2},
            'totals': {'net_total': 10, 'gross_total': 12.3},
        }
        return document, portal, [row], preinvoice, purchase

    def test_final_content_is_compared_before_accounting(self):
        _assert_final_purchase_content(*self._content_fixture())
        document, portal, rows, preinvoice, purchase = self._content_fixture()
        rows[0][9] = 9
        with self.assertRaisesRegex(ValueError, 'PT diverge.*Responsável'):
            _assert_final_purchase_content(document, portal, rows, preinvoice, purchase)

    def test_changed_management_fingerprint_blocks_accounting_before_phc_operation(self):
        document, payload = self.document()
        payload['totals'] = {'net_total': 1}
        with patch('services.document_ai_phc_operation_service.run_document_phc_operation') as operation:
            with self.assertRaisesRegex(ValueError, 'estado validado no CdG'):
                _integrate_accounting_purchase(document, payload, 'tester', {'invoice': True})
        operation.assert_not_called()

    @patch('services.document_ai_service.finalize_purchase_on_existing_fo')
    @patch('services.document_ai_phc_operation_service.run_document_phc_operation')
    def test_reuses_reception_fo_and_selected_proforma(self, run_operation, finalize):
        document, payload = self.document()
        run_operation.return_value = {'status': 'confirmed', 'fostamp': 'FO-RECEPTION'}

        result = _integrate_accounting_purchase(document, payload, 'tester', {'invoice': True})

        self.assertEqual(result['fostamp'], 'FO-RECEPTION')
        kwargs = run_operation.call_args.kwargs
        self.assertEqual(kwargs['operation_type'], 'purchase_finalization')
        self.assertEqual(kwargs['legacy_meta_key'], 'phc_purchase_finalization')
        self.assertEqual(kwargs['operation_context']['action'], 'update_existing_fo')
        self.assertEqual(kwargs['operation_context']['fostamp'], 'FO-RECEPTION')
        kwargs['execute']()
        finalize.assert_called_once()
        call_args = finalize.call_args.args
        self.assertEqual(call_args[1]['fostamp'], 'FO-RECEPTION')
        self.assertEqual(call_args[2][0]['stamp'], 'BO-PROFORMA')
        self.assertEqual(finalize.call_args.kwargs['expected_file_hash'], 'FILE-HASH')

    def test_blueprint_passes_invoice_integration_permission(self):
        source = Path('blueprints/document_ai.py').read_text(encoding='utf-8')
        self.assertIn("'invoice': _document_ai_has_integration_access('invoice')", source)


if __name__ == '__main__':
    unittest.main()
