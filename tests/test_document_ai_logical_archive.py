import unittest
from pathlib import Path

from services.document_ai_service import _document_inbox_scope_sql


ROOT = Path(__file__).resolve().parents[1]


class DocumentAiLogicalArchiveTests(unittest.TestCase):
    def test_inbox_excludes_latest_deleted_event_per_view(self):
        scope = _document_inbox_scope_sql('management', archived=False)
        self.assertIn("VIEW_CODE='management'", scope)
        self.assertIn("<> 'deleted'", scope)

    def test_archive_includes_deleted_and_validated_documents(self):
        scope = _document_inbox_scope_sql('accounting', archived=True)
        self.assertIn("VIEW_CODE='accounting'", scope)
        self.assertIn("= 'deleted'", scope)
        self.assertIn('ACCOUNTING_VALIDATED', scope)

    def test_delete_path_is_logical_and_has_no_confirmation(self):
        service = (ROOT / 'services/document_ai_service.py').read_text(encoding='utf-8')
        inbox = (ROOT / 'static/js/document_ai_inbox.js').read_text(encoding='utf-8')
        function_body = service.split('def delete_document_from_inbox', 1)[1].split('def recover_document_to_inbox', 1)[0]
        self.assertIn("'deleted'", function_body)
        self.assertNotIn('db.session.delete', function_body)
        self.assertNotIn('os.remove', function_body)
        self.assertNotIn('window.confirm', inbox)

    def test_recovery_is_available_only_for_deleted_archive_rows(self):
        inbox = (ROOT / 'static/js/document_ai_inbox.js').read_text(encoding='utf-8')
        self.assertIn("state.archived && item.business_state === 'Eliminado'", inbox)
        self.assertIn('fa-rotate-left', inbox)
        self.assertIn('Documento recuperado.', inbox)


if __name__ == '__main__':
    unittest.main()
