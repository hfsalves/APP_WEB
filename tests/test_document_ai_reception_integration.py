import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from services.document_ai_service import _integrate_reception_document


class DocumentAiReceptionIntegrationTests(unittest.TestCase):
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
                return_value={'crstamp': 'CR1', 'reference': 3042, 'year': 2026, 'phc_database': 'PHC'},
            ) as submit:
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
        existing = {'phc_integration': {'status': 'confirmed', 'crstamp': 'CR1', 'reference': 3042}}
        document = self._document('/missing.pdf', existing)
        with patch('services.document_ai_service.submit_correspondence_to_phc') as submit:
            integration = _integrate_reception_document(
                document, {'document_type': 'mail'}, 'tester', {'correspondence': True}
            )
        self.assertEqual(integration['reference'], 3042)
        submit.assert_not_called()

    def test_integration_permission_is_enforced(self):
        document = self._document('/missing.pdf')
        with self.assertRaises(PermissionError):
            _integrate_reception_document(
                document, {'document_type': 'mail'}, 'tester', {'correspondence': False}
            )


if __name__ == '__main__':
    unittest.main()
