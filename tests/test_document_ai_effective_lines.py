import unittest

from services.document_ai_service import _effective_portal_lines


class DocumentAiEffectiveLinesTests(unittest.TestCase):
    def test_distributed_summary_is_not_sent_to_phc(self):
        lines = [{'id': 'L1', 'qty': 10, 'sublines': [
            {'id': 'S1', 'ccusto': 'CC1', 'qty': 4},
            {'id': 'S2', 'ccusto': 'CC2', 'qty': 6},
        ]}]
        result = _effective_portal_lines(lines)
        self.assertEqual([item['id'] for item in result], ['S1', 'S2'])
        self.assertEqual([item['parent_line_id'] for item in result], ['L1', 'L1'])
        self.assertEqual(result[0]['qty'], 4)

    def test_undistributed_line_remains_unchanged(self):
        line = {'id': 'L1', 'qty': 2, 'ref': 'A'}
        result = _effective_portal_lines([line])
        self.assertEqual({key: result[0][key] for key in line}, line)
        self.assertEqual(result[0]['portal_line_id'], 'L1')
        self.assertEqual(result[0]['portal_line_index'], 0)

    def test_distributed_child_does_not_inherit_parent_lineage(self):
        result = _effective_portal_lines([{
            'line_id': 'L1', 'article_ref': 'A', 'bostamp': 'BO-PARENT', 'bistamp': 'BI-PARENT',
            'sub_lines': [{'subline_id': 'S1', 'qty': 1}],
        }])
        self.assertEqual(result[0]['portal_line_id'], 'S1')
        self.assertNotIn('bostamp', result[0])
        self.assertNotIn('bistamp', result[0])

    def test_accepts_legacy_sub_lines_key(self):
        result = _effective_portal_lines([{'line_id': 'L1', 'sub_lines': [{'qty': 1}]}])
        self.assertEqual(result[0]['parent_line_id'], 'L1')


if __name__ == '__main__':
    unittest.main()
