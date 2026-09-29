import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from flask import Flask

from services.document_ai_service import (
    _attach_duplicate_pdf_to_existing_purchase,
    _duplicate_purchase_attachment_target,
    record_document_duplicate_decision,
)


class DocumentAiDuplicateAttachmentTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(
            PHC_GED_UNC_ROOT=r'\\10.0.1.11\ged',
            PHC_GED_WRITE_ROOT='/tmp/ged-test',
        )

    def test_additional_attachment_is_named_beside_the_existing_purchase_pdf(self):
        with self.app.app_context():
            target = _duplicate_purchase_attachment_target(
                r'\\10.0.1.11\ged\HSOLS_FR\FACTURATION_FOURNISSEURS\2026\9 SEPT 26\FAC-001.pdf',
                2,
                'abcdef123456',
            )
        self.assertEqual(target['file_name'], 'FAC-001-ANEXO-2-ABCDEF12.pdf')
        self.assertTrue(target['unc_path'].endswith(r'\FAC-001-ANEXO-2-ABCDEF12.pdf'))
        self.assertTrue(target['write_path'].endswith(os.path.join('HSOLS_FR', 'FACTURATION_FOURNISSEURS', '2026', '9 SEPT 26', target['file_name'])))

    def test_association_inserts_only_an_attachment_on_the_existing_fo(self):
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as handle:
            handle.write(b'%PDF-new-copy')
            pdf_path = handle.name
        source = SimpleNamespace(docinstamp='NEW', file_name='new.pdf')
        target_document = SimpleNamespace(
            docinstamp='OLD', feid=1,
            processing_meta_json=json.dumps({'phc_integration': {
                'status': 'confirmed', 'fostamp': 'FO-1', 'phc_database': 'HSOLS_FR',
                'ged_path': r'\\10.0.1.11\ged\HSOLS_FR\FACTURATION_FOURNISSEURS\2026\9 SEPT 26\FAC-001.pdf',
            }}),
        )
        cursor = MagicMock()

        def execute(sql, *params):
            result = MagicMock()
            normalized = ' '.join(str(sql).split()).upper()
            if 'SP_GETAPPLOCK' in normalized:
                result.fetchone.return_value = (0,)
            elif 'FROM DBO.FO' in normalized:
                result.fetchone.return_value = ('V/Facture', 'FAC-100')
            elif 'UNIQUEID = ?' in normalized:
                result.fetchone.return_value = None
            elif 'SELECT TOP 1 FULLNAME, RESUMO' in normalized:
                result.fetchone.return_value = (
                    r'\\10.0.1.11\ged\HSOLS_FR\FACTURATION_FOURNISSEURS\2026\9 SEPT 26\FAC-001.pdf',
                    'FAC',
                )
            elif 'COUNT_BIG' in normalized:
                result.fetchone.return_value = (1,)
            return result

        cursor.execute.side_effect = execute
        connection = MagicMock()
        connection.cursor.return_value = cursor
        inserted = MagicMock()
        try:
            with self.app.app_context(), \
                 patch('services.document_ai_service._document_absolute_path', return_value=pdf_path), \
                 patch('services.document_ai_service._fe_supplier_source', return_value={'phc_db': 'HSOLS_FR', 'phc_server': 'srv'}), \
                 patch('services.document_ai_service._phc_correspondence_user', return_value={'no': 1, 'name': 'Tester', 'initials': 'TST'}), \
                 patch('services.document_ai_service._phc_insert_values', inserted), \
                 patch('services.document_ai_service._write_document_ai_pdf', return_value=True), \
                 patch('services.document_ai_service._document_ai_pdf_is_confirmed', return_value=True), \
                 patch('services.phc_user_import_service._phc_conn_str', return_value='DRIVER=test'), \
                 patch('pyodbc.connect', return_value=connection):
                result = _attach_duplicate_pdf_to_existing_purchase(source, target_document, 'tester')
        finally:
            os.unlink(pdf_path)

        self.assertTrue(result['ok'])
        self.assertEqual(result['fostamp'], 'FO-1')
        inserted.assert_called_once()
        _cursor_arg, table_name, values = inserted.call_args.args
        self.assertEqual(table_name, 'ANEXOS')
        self.assertEqual(values['recstamp'], 'FO-1')
        self.assertEqual(values['oritable'], 'FO')
        self.assertEqual(values['origem'], 'Compras a Fornecedores\r')
        connection.commit.assert_called_once()

    def test_duplicate_decision_archives_new_record_only_after_attachment_succeeds(self):
        source = SimpleNamespace(
            docinstamp='NEW', processing_meta_json='{}', dtalt=None,
            useralteracao='', usercriacao='tester',
        )
        target = SimpleNamespace(
            docinstamp='OLD',
            processing_meta_json=json.dumps({'phc_integration': {'fostamp': 'FO1'}}),
            json_resultado=json.dumps({'document_type': 'invoice'}),
            doc_type_detected='invoice', dtalt=None,
            useralteracao='', usercriacao='tester',
        )
        fake_db = MagicMock()
        fake_db.session.get.side_effect = lambda _model, stamp: source if stamp == 'NEW' else target
        attachment = {
            'ok': True, 'anexosstamp': 'AN2', 'fostamp': 'FO1',
            'phc_database': 'HSOLS_FR', 'ged_path': r'\\ged\anexo-2.pdf',
            'ged_confirmed': True, 'message': 'Anexo acrescentado.',
        }
        with patch('services.document_ai_service.db', fake_db), \
             patch('services.document_ai_service._attach_duplicate_pdf_to_existing_purchase', return_value=attachment), \
             patch('services.document_ai_service._document_log'):
            result = record_document_duplicate_decision('NEW', 'OLD', 'associate', 'tester')

        self.assertEqual(result['attachment']['anexosstamp'], 'AN2')
        self.assertEqual(result['open_document_id'], 'OLD')
        saved_target = json.loads(target.processing_meta_json)
        self.assertEqual(saved_target['additional_purchase_attachments'][0]['anexosstamp'], 'AN2')
        executed_sql = ' '.join(str(call.args[0]) for call in fake_db.session.execute.call_args_list)
        self.assertIn("'duplicate_associated'", executed_sql)
        fake_db.session.commit.assert_called_once()

    def test_failed_attachment_does_not_archive_the_new_record(self):
        source = SimpleNamespace(docinstamp='NEW')
        target = SimpleNamespace(
            docinstamp='OLD',
            processing_meta_json=json.dumps({'phc_integration': {'fostamp': 'FO1'}}),
            json_resultado=json.dumps({'document_type': 'invoice'}),
            doc_type_detected='invoice',
        )
        fake_db = MagicMock()
        fake_db.session.get.side_effect = lambda _model, stamp: source if stamp == 'NEW' else target
        with patch('services.document_ai_service.db', fake_db), \
             patch('services.document_ai_service._attach_duplicate_pdf_to_existing_purchase', side_effect=RuntimeError('GED indisponível')):
            with self.assertRaisesRegex(RuntimeError, 'GED indisponível'):
                record_document_duplicate_decision('NEW', 'OLD', 'associate', 'tester')
        fake_db.session.execute.assert_not_called()
        fake_db.session.commit.assert_not_called()


if __name__ == '__main__':
    unittest.main()
