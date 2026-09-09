import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from services.document_ai_service import (
    _has_complete_reception_integration,
    _integrate_reception_document,
)


class DocumentAiReceptionIntegrationTests(unittest.TestCase):
    def test_complete_correspondence_requires_attachment_and_confirmed_ged(self):
        base = {
            'status': 'confirmed',
            'reference': 42,
            'year': 2026,
            'phc_database': 'HSOLS_FR',
            'crstamp': 'CR-1',
        }

        self.assertFalse(_has_complete_reception_integration(base, 'mail'))
        self.assertFalse(_has_complete_reception_integration({
            **base,
            'anexosstamp': 'ANEXO-1',
            'ged_confirmed': False,
        }, 'mail'))
        self.assertTrue(_has_complete_reception_integration({
            **base,
            'anexosstamp': 'ANEXO-1',
            'ged_confirmed': True,
        }, 'mail'))

    def test_complete_invoice_requires_both_phc_attachments(self):
        base = {
            'status': 'confirmed',
            'reference': 42,
            'year': 2026,
            'phc_database': 'HSOLS_FR',
            'crstamp': 'CR-1',
            'fostamp': 'FO-1',
            'ged_confirmed': True,
        }

        self.assertFalse(_has_complete_reception_integration({
            **base,
            'anexosstamps': ['ANEXO-CR'],
        }, 'invoice'))
        self.assertTrue(_has_complete_reception_integration({
            **base,
            'anexosstamps': ['ANEXO-CR', 'ANEXO-FO'],
        }, 'invoice'))

    @staticmethod
    def _document(path, meta=None):
        return SimpleNamespace(
            file_path=path,
            file_name='documento.pdf',
            processing_meta_json=json.dumps(meta or {}),
            processing_status='parsed_ok',
            last_processing_error='',
            dtalt=None,
            useralteracao='',
        )

    def test_correspondence_is_integrated_and_identity_is_persisted(self):
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as handle:
            handle.write(b'%PDF-test')
            path = handle.name
        document = self._document(path)
        try:
            with patch('services.document_ai_service._document_absolute_path', return_value=path), patch(
                'services.document_ai_service.submit_correspondence_to_phc',
                return_value={
                    'crstamp': 'CR1', 'reference': 3042, 'year': 2026,
                    'phc_database': 'PHC', 'ged_path': r'\\ged\\COR-3042.pdf',
                    'anexosstamp': 'AN1', 'ged_confirmed': True,
                },
            ) as submit, patch('services.document_ai_service.db.session.commit'):
                integration = _integrate_reception_document(
                    document,
                    {'document_type': 'mail', 'customer': {'feid': 1}},
                    'tester',
                    {'correspondence': True},
                )
            self.assertEqual(integration['status'], 'confirmed')
            self.assertEqual(integration['crstamp'], 'CR1')
            self.assertEqual(integration['reference'], 3042)
            self.assertEqual(json.loads(document.processing_meta_json)['phc_integration']['crstamp'], 'CR1')
            submit.assert_called_once()
        finally:
            os.unlink(path)

    def test_confirmed_integration_is_reused_without_phc_call(self):
        existing = {
            'phc_integration': {
                'status': 'confirmed', 'crstamp': 'CR1', 'reference': 3042,
                'year': 2026, 'phc_database': 'PHC', 'ged_path': r'\\ged\\COR-3042.pdf',
                'anexosstamp': 'AN1', 'ged_confirmed': True,
            }
        }
        document = self._document('/missing.pdf', existing)
        with patch('services.document_ai_service.submit_correspondence_to_phc') as submit:
            integration = _integrate_reception_document(
                document, {'document_type': 'mail'}, 'tester', {'correspondence': True}
            )
        self.assertEqual(integration['reference'], 3042)
        submit.assert_not_called()

    def test_incomplete_confirmed_integration_is_not_reused(self):
        existing = {'phc_integration': {'status': 'confirmed', 'crstamp': 'CR1', 'reference': 3042}}
        document = self._document('/missing.pdf', existing)
        with patch('services.document_ai_service._document_absolute_path', return_value='/missing.pdf'):
            with self.assertRaises(FileNotFoundError):
                _integrate_reception_document(
                    document, {'document_type': 'mail'}, 'tester', {'correspondence': True}
                )

    def test_integration_permission_is_enforced(self):
        document = self._document('/missing.pdf')
        with self.assertRaises(PermissionError):
            _integrate_reception_document(
                document, {'document_type': 'mail'}, 'tester', {'correspondence': False}
            )

    def test_failed_integration_is_persisted_as_recoverable(self):
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as handle:
            handle.write(b'%PDF-test')
            path = handle.name
        document = self._document(path)
        try:
            with patch('services.document_ai_service._document_absolute_path', return_value=path), patch(
                'services.document_ai_service.submit_correspondence_to_phc',
                side_effect=RuntimeError('GED indisponível'),
            ), patch('services.document_ai_service.db.session.commit') as commit:
                with self.assertRaisesRegex(RuntimeError, 'GED indisponível'):
                    _integrate_reception_document(
                        document,
                        {'document_type': 'mail', 'customer': {'feid': 1}},
                        'tester',
                        {'correspondence': True},
                    )
            integration = json.loads(document.processing_meta_json)['phc_integration']
            self.assertEqual(integration['status'], 'failed_recoverable')
            self.assertEqual(document.processing_stage, 'integration_failed_recoverable')
            self.assertGreaterEqual(commit.call_count, 2)
        finally:
            os.unlink(path)


if __name__ == '__main__':
    unittest.main()
