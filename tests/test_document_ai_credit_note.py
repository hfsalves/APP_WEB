import json
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from services import document_ai_credit_note_service as credit
from services.document_ai_service import (
    _has_complete_credit_note_finalization,
    _integrate_accounting_credit_note,
)


def controlled_line(line_id='L1', fnstamp='FN-ORIGINAL-1'):
    return {
        'line_id': line_id, 'portal_line_id': line_id, 'description': 'Material',
        'qty': 2, 'net_amount': 20,
        'credit_origin_fostamp': 'FO-ORIGINAL',
        'credit_origin_fnstamp': fnstamp,
        'credit_origin_confirmed': True,
    }


class CreditNoteRulesTests(unittest.TestCase):
    def test_mapping_requires_manual_confirmation_on_every_effective_line(self):
        with self.assertRaisesRegex(ValueError, 'manualmente'):
            credit._mapping([{'line_id': 'L1'}])

    def test_mapping_preserves_line_and_subline_identity(self):
        original_fo, rows = credit._mapping([
            controlled_line('L1', 'FN1'), controlled_line('SUB1', 'FN2'),
        ])
        self.assertEqual(original_fo, 'FO-ORIGINAL')
        self.assertEqual([row['portal_line_id'] for row in rows], ['L1', 'SUB1'])

    def test_one_original_fn_cannot_be_reused_for_two_credit_lines(self):
        with self.assertRaisesRegex(ValueError, 'distinta'):
            credit._mapping([controlled_line('L1', 'FN1'), controlled_line('L2', 'FN1')])

    def test_total_and_partial_credit_fit_original_balance(self):
        origin = {'qtt': Decimal('10'), 'etiliquido': Decimal('100')}
        credit._validate_capacity(origin, {}, Decimal('10'), Decimal('100'))
        credit._validate_capacity(origin, {'used_qtt': 3, 'used_value': 30}, Decimal('7'), Decimal('70'))

    def test_excess_and_concurrent_credit_are_blocked(self):
        origin = {'qtt': Decimal('10'), 'etiliquido': Decimal('100')}
        with self.assertRaisesRegex(ValueError, 'quantidade'):
            credit._validate_capacity(origin, {'used_qtt': 4}, Decimal('7'), Decimal('50'))
        with self.assertRaisesRegex(ValueError, 'valor'):
            credit._validate_capacity(origin, {'used_value': 80}, Decimal('1'), Decimal('25'))

    def test_historical_positive_and_recent_negative_series_keep_their_sign(self):
        self.assertEqual(credit._credit_sign([{'etiliquido': 10}]), Decimal('1'))
        self.assertEqual(credit._credit_sign([{'etiliquido': -10}]), Decimal('-1'))

    def test_hsols_fr_and_intersol_are_supported_but_gr360_is_blocked(self):
        for database in ('HSOLS_FR', 'INTERSOL'):
            with patch('services.document_ai_service._phc_origin_source', return_value={
                'kind': 'phc', 'phc_db': database, 'phc_server': 'server',
            }):
                _, selected, fostamp = credit._source(
                    {'customer': {'feid': 1}}, {'phc_database': database, 'fostamp': 'FO-NC'},
                )
                self.assertEqual((selected, fostamp), (database, 'FO-NC'))
        with patch('services.document_ai_service._phc_origin_source', return_value={
            'kind': 'phc', 'phc_db': 'GR360', 'phc_server': 'server',
        }):
            with self.assertRaisesRegex(ValueError, 'GR360 está bloqueada'):
                credit._source({'customer': {}}, {'phc_database': 'GR360', 'fostamp': 'FO-NC'})

    def test_finalization_completion_requires_original_fo_and_fn(self):
        self.assertTrue(_has_complete_credit_note_finalization({
            'status': 'confirmed', 'fostamp': 'FO-NC', 'original_fostamp': 'FO-ORIGINAL',
            'original_fnstamps': ['FN1'], 'final_line_count': 1,
        }))
        self.assertFalse(_has_complete_credit_note_finalization({
            'status': 'confirmed', 'fostamp': 'FO-NC', 'original_fnstamps': [],
        }))

    @patch('services.document_ai_phc_operation_service.run_document_phc_operation')
    def test_accounting_reuses_reception_fo_and_runs_dedicated_operation(self, run_operation):
        run_operation.return_value = {'status': 'confirmed', 'fostamp': 'FO-NC'}
        payload = {'document_type': 'credit_note', 'lines': [controlled_line()], 'customer': {}}
        fingerprint = credit.mapping_fingerprint(payload)
        document = SimpleNamespace(
            docinstamp='DOC-1', processing_status='provisional_invoice',
            processing_meta_json=json.dumps({
                'phc_operations': {'provisional_invoice': {
                    'status': 'confirmed', 'fostamp': 'FO-NC', 'phc_database': 'HSOLS_FR',
                }},
                'credit_note_mapping': {'fingerprint': fingerprint},
            }),
        )
        _integrate_accounting_credit_note(document, payload, 'tester', {'invoice': True})
        kwargs = run_operation.call_args.kwargs
        self.assertEqual(kwargs['operation_type'], 'credit_note_finalization')
        self.assertEqual(kwargs['operation_context']['fostamp'], 'FO-NC')
        self.assertEqual(kwargs['operation_context']['action'], 'update_existing_fo')

    def test_source_contains_demonstrated_lineage_and_concurrency_guards(self):
        source = Path('services/document_ai_credit_note_service.py').read_text(encoding='utf-8')
        self.assertIn("'ofnstamp': item['fnstamp']", source)
        self.assertIn("'bistamp': ''", source)
        self.assertIn('sp_getapplock', source)
        self.assertIn('UPDLOCK,HOLDLOCK', source)
        self.assertNotIn("'dostamp'", source.lower())


if __name__ == '__main__':
    unittest.main()
