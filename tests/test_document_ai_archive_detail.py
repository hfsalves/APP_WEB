import json
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services import document_ai_service


def _rows(items):
    result = MagicMock()
    result.mappings.return_value.all.return_value = items
    return result


class DocumentAiArchiveDetailTests(unittest.TestCase):
    def _document(self):
        moment = datetime(2026, 9, 15, 9, 30)
        return SimpleNamespace(
            docinstamp='DOC-1', file_name='invoice.pdf', file_ext='.pdf',
            mime_type='application/pdf', file_size=123,
            json_resultado=json.dumps({
                'document_type': 'invoice', 'document_number': 'F-1',
                'lines': [{'description': 'Persistida', 'sub_lines': [{'ccusto': 'OBRA-1'}]}],
                'totals': {'net_total': 10, 'tax_total': 2, 'gross_total': 12},
            }),
            processing_meta_json=json.dumps({
                'phc_origins': [{'stamp': 'BO-1', 'document_type': 'purchase_order'}],
                'phc_integration': {'fostamp': 'FO-1', 'ged_path': 'GED/file.pdf'},
                'phc_operations': {'preinvoice': {'status': 'confirmed'}},
            }),
            processing_status='validated', reception_validated=True,
            reception_validated_at=moment, reception_validated_by='tester',
            management_validated=False, management_validated_at=None,
            management_validated_by='', accounting_validated=False,
            accounting_validated_at=None, accounting_validated_by='',
            dtcri=moment, dtalt=moment, usercriacao='creator', useralteracao='tester',
        )

    def test_returns_exact_persisted_document_and_relationships(self):
        event = _rows([{
            'EVENT_CODE': 'validated', 'PREVIOUS_STATE': 'OK',
            'USUARIO': 'tester', 'DTCRI': datetime(2026, 9, 15, 9, 30),
        }])
        assignments = _rows([])
        logs = _rows([])
        with patch.object(document_ai_service.db.session, 'get', return_value=self._document()), patch.object(
            document_ai_service.db.session, 'execute', side_effect=[event, assignments, logs],
        ), patch.object(document_ai_service.db.session, 'commit') as commit:
            payload = document_ai_service.get_document_archive_detail('DOC-1', 'home')

        self.assertEqual(payload['result']['lines'][0]['description'], 'Persistida')
        self.assertEqual(payload['archive_snapshot']['origins'][0]['stamp'], 'BO-1')
        self.assertEqual(payload['archive_snapshot']['phc_operations']['preinvoice']['status'], 'confirmed')
        self.assertEqual(payload['archive_snapshot']['latest_event']['actor'], 'tester')
        commit.assert_not_called()

    def test_does_not_prepare_schema_or_recalculate_document(self):
        empty = _rows([])
        with patch.object(document_ai_service.db.session, 'get', return_value=self._document()), patch.object(
            document_ai_service.db.session, 'execute', side_effect=[empty, empty, empty],
        ), patch.object(document_ai_service, '_ensure_document_ai_schema') as ensure, patch.object(
            document_ai_service, 'normalize_unified_document_model', side_effect=AssertionError('must not normalize'),
        ):
            payload = document_ai_service.get_document_archive_detail('DOC-1', 'management')

        ensure.assert_not_called()
        self.assertEqual(payload['result']['document_number'], 'F-1')


if __name__ == '__main__':
    unittest.main()
