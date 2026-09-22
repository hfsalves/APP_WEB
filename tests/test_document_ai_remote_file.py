import io
import json
import os
import sys
import tempfile
import types
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from flask import Flask

from services.document_ai_service import (
    _document_absolute_path,
    _document_ged_path_candidates,
    _document_ged_unc_path,
)


class DocumentAiRemoteFileTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = Flask(__name__)
        self.app.config.update(
            DOCUMENT_AI_STORAGE_ROOT=self.temp_dir.name,
            PHC_GED_UNC_ROOT=r'\\10.0.1.11\ged',
        )
        self.context = self.app.app_context()
        self.context.push()

    def tearDown(self):
        self.context.pop()
        self.temp_dir.cleanup()

    @staticmethod
    def document(meta=None):
        return SimpleNamespace(
            docinstamp='DOC-REMOTE-1',
            file_name='invoice.pdf',
            file_path='/static/images/document_ai/invoice.pdf',
            file_ext='.pdf',
            processing_meta_json=json.dumps(meta or {}),
        )

    def test_collects_paths_from_reception_identity_and_operations(self):
        document = self.document({
            'phc_integration': {
                'ged_path': r'\\10.0.1.11\ged\HSOLS_FR\FACTURATION_FOURNISSEURS\invoice.pdf',
                'ged_paths': [
                    {'path': r'\\10.0.1.11\ged\HSOLS_FR\COURRIER_INTERNE_EXTERIEUR\invoice.pdf'},
                ],
            },
            'phc_operations': {
                'provisional_invoice': {
                    'ged_path': r'\\10.0.1.11\ged\HSOLS_FR\FACTURATION_FOURNISSEURS\invoice.pdf',
                },
            },
        })

        paths = _document_ged_path_candidates(document)

        self.assertEqual(len(paths), 2)
        self.assertIn('FACTURATION_FOURNISSEURS', paths[0])
        self.assertIn('COURRIER_INTERNE_EXTERIEUR', paths[1])

    def test_rejects_an_unc_path_outside_the_configured_ged(self):
        self.assertEqual(_document_ged_unc_path(r'\\other-server\share\invoice.pdf'), '')
        self.assertEqual(
            _document_ged_unc_path(r'\\10.0.1.11\ged\HSOLS_FR\invoice.pdf'),
            r'\\10.0.1.11\ged\HSOLS_FR\invoice.pdf',
        )

    def test_missing_local_file_is_read_from_ged_and_cached(self):
        content = b'%PDF-1.7\nremote document'
        unc_path = r'\\10.0.1.11\ged\HSOLS_FR\FACTURATION_FOURNISSEURS\invoice.pdf'
        document = self.document({'phc_integration': {'ged_path': unc_path}})
        fake_smbclient = types.SimpleNamespace(
            path=types.SimpleNamespace(isfile=lambda path: path == unc_path),
            open_file=lambda _path, mode='rb': io.BytesIO(content),
        )

        with patch.dict(sys.modules, {'smbclient': fake_smbclient}), patch(
            'services.document_ai_service._document_ai_smb_session'
        ) as session:
            resolved = _document_absolute_path(document)

        self.assertTrue(os.path.isfile(resolved))
        with open(resolved, 'rb') as handle:
            self.assertEqual(handle.read(), content)
        self.assertIn('.document_ai_cache', resolved)
        session.assert_called_once_with(unc_path)

        # The second preview uses the local cache and does not reconnect to SMB.
        with patch('services.document_ai_service._document_ai_smb_session') as second_session:
            self.assertEqual(_document_absolute_path(document), resolved)
        second_session.assert_not_called()


if __name__ == '__main__':
    unittest.main()
