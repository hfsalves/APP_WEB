import unittest

from services.document_ai_line_distribution_service import (
    normalize_line_structures,
    origin_lineage_errors,
)
from services.document_ai_service import (
    _line_phc_origin_stamps,
    _match_document_lines_to_origin,
)


class DocumentAiOriginLineageTests(unittest.TestCase):
    def test_same_article_uses_distinct_exact_bistamps(self):
        document_lines = [
            {'line_id': 'L1', 'article_ref': 'A', 'qty': 2, 'description': 'Primeira'},
            {'line_id': 'L2', 'article_ref': 'A', 'qty': 3, 'description': 'Segunda'},
        ]
        origin_lines = [
            {'line_stamp': 'BI-ONE', 'ref': 'A', 'qty': 2, 'pending_qty': 2, 'description': 'Primeira'},
            {'line_stamp': 'BI-TWO', 'ref': 'A', 'qty': 3, 'pending_qty': 3, 'description': 'Segunda'},
        ]
        matches = _match_document_lines_to_origin(document_lines, origin_lines)
        self.assertEqual([item['origin_line_stamp'] for item in matches], ['BI-ONE', 'BI-TWO'])
        self.assertEqual([item['document_line_id'] for item in matches], ['L1', 'L2'])

    def test_distributed_line_matches_each_subline_independently(self):
        document_lines = [{
            'line_id': 'L1', 'article_ref': 'A', 'qty': 5,
            'sub_lines': [
                {'subline_id': 'S1', 'article_ref': 'A', 'qty': 2, 'description': 'Primeira'},
                {'subline_id': 'S2', 'article_ref': 'A', 'qty': 3, 'description': 'Segunda'},
            ],
        }]
        origin_lines = [
            {'line_stamp': 'BI-ONE', 'ref': 'A', 'qty': 2, 'pending_qty': 2, 'description': 'Primeira'},
            {'line_stamp': 'BI-TWO', 'ref': 'A', 'qty': 3, 'pending_qty': 3, 'description': 'Segunda'},
        ]
        matches = _match_document_lines_to_origin(document_lines, origin_lines)
        self.assertEqual([item['document_subline_id'] for item in matches], ['S1', 'S2'])
        self.assertEqual([item['origin_line_stamp'] for item in matches], ['BI-ONE', 'BI-TWO'])

    def test_lineage_aliases_are_normalized_but_not_copied_to_group(self):
        lines = normalize_line_structures([
            {'line_id': 'L1', 'group_id': 'G', 'group_role': 'principal', 'bostamp': 'BO1', 'bistamp': 'BI1'},
            {'line_id': 'L2', 'group_id': 'G', 'group_role': 'associated'},
        ])
        self.assertEqual(lines[0]['phc_origin_stamp'], 'BO1')
        self.assertEqual(lines[0]['phc_origin_line_stamp'], 'BI1')
        self.assertNotIn('phc_origin_stamp', lines[1])

    def test_lineage_requires_complete_bostamp_bistamp_pair(self):
        self.assertEqual(origin_lineage_errors([{'bostamp': 'BO1'}]), [
            'A filiação PHC da linha está incompleta: confirma BOSTAMP e BISTAMP.'
        ])
        self.assertEqual(origin_lineage_errors([{'bostamp': 'BO1', 'bistamp': 'BI1'}]), [])

    def test_origin_stamp_scan_includes_exact_links_and_sublines(self):
        lines = [{'sub_lines': [{'phc_origin_links': [{'bostamp': 'BO2', 'bistamp': 'BI2'}]}]}]
        self.assertEqual(_line_phc_origin_stamps(lines), {'BO2'})


if __name__ == '__main__':
    unittest.main()
