import unittest
from unittest.mock import MagicMock, patch

from services import document_ai_service


def _rows(items):
    result = MagicMock()
    result.mappings.return_value.all.return_value = items
    return result


class DocumentAiArchiveRegularizationTests(unittest.TestCase):
    def test_dry_run_reports_only_explicit_validation_evidence(self):
        ambiguous = MagicMock()
        ambiguous.scalar.return_value = 1
        results = [
            _rows([{'DOCINSTAMP': 'A', 'LATEST_EVENT': ''}, {'DOCINSTAMP': 'B', 'LATEST_EVENT': 'deleted'}]),
            _rows([{'DOCINSTAMP': 'C', 'LATEST_EVENT': ''}]),
            _rows([]),
            ambiguous,
        ]
        with patch.object(document_ai_service, '_ensure_document_ai_schema'), patch.object(
            document_ai_service.db.session, 'execute', side_effect=results,
        ), patch.object(document_ai_service.db.session, 'commit') as commit:
            report = document_ai_service.regularize_document_archives('tester', dry_run=True)

        self.assertEqual(report['examined'], 3)
        self.assertEqual(report['corrected'], 2)
        self.assertEqual(report['unchanged'], 1)
        self.assertEqual(report['ambiguous_unchanged'], 1)
        commit.assert_not_called()

    def test_apply_only_adds_history_events_and_commits_once(self):
        ambiguous = MagicMock()
        ambiguous.scalar.return_value = 0
        insertion = MagicMock()
        results = [
            _rows([{'DOCINSTAMP': 'A', 'LATEST_EVENT': ''}]),
            _rows([]),
            _rows([]),
            ambiguous,
            insertion,
        ]
        with patch.object(document_ai_service, '_ensure_document_ai_schema'), patch.object(
            document_ai_service.db.session, 'execute', side_effect=results,
        ) as execute, patch.object(document_ai_service.db.session, 'commit') as commit:
            report = document_ai_service.regularize_document_archives('tester', dry_run=False)

        self.assertEqual(report['corrected'], 1)
        self.assertIn('DOC_AI_VIEW_EVENT', str(execute.call_args_list[-1].args[0]))
        commit.assert_called_once()


if __name__ == '__main__':
    unittest.main()
