import unittest
from datetime import datetime
from unittest.mock import MagicMock

from flask import Flask

from services.document_ai_distribution_service import normalize_distribution_document_class
from services.document_ai_required_info_service import evaluate_required_info
from services.document_ai_service import (
    _has_complete_reception_integration,
    _phc_provisional_effective_datetime,
    _provisional_invoice_ged_paths,
    normalize_document_type,
    normalize_unified_document_model,
)


class DocumentAiTp067OperationalDateTests(unittest.TestCase):
    received_at = datetime(2026, 9, 14, 11, 22, 33, 456789)

    @staticmethod
    def cursor_with(value):
        cursor = MagicMock()
        cursor.execute.return_value.fetchone.return_value = value
        return cursor

    def test_open_period_keeps_original_date(self):
        result = _phc_provisional_effective_datetime(
            self.cursor_with(('31.08.2026',)), 'HSOLS_FR',
            datetime(2026, 9, 10), self.received_at,
        )
        self.assertEqual(result, datetime(2026, 9, 10, 11, 22, 33, 456789))

    def test_closed_period_uses_first_day_of_following_open_month(self):
        result = _phc_provisional_effective_datetime(
            self.cursor_with(('17/08/2026',)), 'HSOLS_FR',
            datetime(2026, 7, 23), self.received_at,
        )
        self.assertEqual(result, datetime(2026, 9, 1, 11, 22, 33, 456789))

    def test_blank_close_date_means_original_period_is_open(self):
        result = _phc_provisional_effective_datetime(
            self.cursor_with(('',)), 'HSOLS_FR',
            datetime(2026, 7, 23), self.received_at,
        )
        self.assertEqual(result.date().isoformat(), '2026-07-23')

    def test_missing_invalid_and_failed_period_queries_do_not_fallback(self):
        with self.subTest(case='missing'), self.assertRaisesRegex(ValueError, 'GE_FECHO não está configurado'):
            _phc_provisional_effective_datetime(
                self.cursor_with(None), 'HSOLS_FR', datetime(2026, 7, 23), self.received_at,
            )
        with self.subTest(case='invalid'), self.assertRaisesRegex(ValueError, 'GE_FECHO.*inválida'):
            _phc_provisional_effective_datetime(
                self.cursor_with(('not-a-date',)), 'HSOLS_FR', datetime(2026, 7, 23), self.received_at,
            )
        broken = MagicMock()
        broken.execute.side_effect = RuntimeError('network')
        with self.subTest(case='query'), self.assertRaisesRegex(RuntimeError, 'consultar o período contabilístico'):
            _phc_provisional_effective_datetime(
                broken, 'HSOLS_FR', datetime(2026, 7, 23), self.received_at,
            )

    def test_operational_date_drives_both_ged_destinations(self):
        app = Flask(__name__)
        app.config['PHC_GED_UNC_ROOT'] = r'\\server\ged'
        with app.app_context():
            paths = _provisional_invoice_ged_paths(
                {'customer': {'ged_folder': 'HSOLS_FR'}, 'document_number': 'FAC/42'},
                {'phc_db': 'HSOLS_FR'}, {'no': 10, 'name': 'Fornecedor'}, 7,
                datetime(2026, 9, 1),
            )
        self.assertEqual(len(paths), 2)
        self.assertTrue(all('\\2026\\9 SEPT 26\\' in item['unc_path'] for item in paths))
        self.assertTrue(all('CCUSTO' not in item['file_name'] for item in paths))

    def test_invoice_integration_identity_requires_both_dates(self):
        payload = {
            'status': 'confirmed', 'reference': 7, 'year': 2026,
            'phc_database': 'HSOLS_FR', 'fostamp': 'FO1', 'crstamp': 'CR1',
            'anexosstamps': ['A1', 'A2'], 'ged_confirmed': True,
        }
        self.assertFalse(_has_complete_reception_integration(payload, 'invoice'))
        self.assertTrue(_has_complete_reception_integration({
            **payload, 'original_date': '2026-07-23', 'operational_date': '2026-09-01',
        }, 'invoice'))


class DocumentAiTp067MailTests(unittest.TestCase):
    def test_all_business_mail_labels_normalize_to_mail(self):
        for label in ('Lettre', 'Mahnung', 'carta', 'aviso', 'notificação'):
            with self.subTest(label=label):
                self.assertEqual(normalize_document_type(label), 'mail')
                self.assertEqual(normalize_distribution_document_class(label), 'mail')
                self.assertEqual(normalize_unified_document_model({'document_type': label})['document_type'], 'mail')

    def test_mail_reception_has_no_financial_requirements(self):
        result = evaluate_required_info(
            {
                'document_type': 'Lettre',
                'customer': {'feid': 1},
                'supplier': {'supplier_no': 2},
                'lines': [], 'totals': {},
            },
            'home',
            required_fields=['entity', 'supplier'],
        )
        self.assertTrue(result['ok'])
        self.assertNotIn('gross_total', result['required'])
        self.assertNotIn('tax_total', result['required'])
        self.assertNotIn('net_total', result['required'])


if __name__ == '__main__':
    unittest.main()
