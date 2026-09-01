import unittest

from services.document_ai_service import (
    document_duplicate_identities_match,
    normalize_document_duplicate_identity,
)
from services.document_duplicate_service import evaluate_duplicate_match


class DocumentAiDuplicateTests(unittest.TestCase):
    def identity(self, **overrides):
        document = {
            'document_type': 'invoice',
            'customer': {'feid': 8},
            'supplier': {'supplier_no': 50007, 'tax_id': 'FR 43.752.341.00025'},
            'document_number': 'FAC / 2026-001',
            'document_date': '28/08/2026',
            'currency': 'eur',
            'totals': {'gross_total': '1 234,50 EUR'},
        }
        document.update(overrides)
        return normalize_document_duplicate_identity(document, file_hash='ABCDEF')

    def test_identity_is_normalized(self):
        identity = self.identity()
        self.assertEqual(identity['doc_class'], 'invoice')
        self.assertEqual(identity['document_number'], 'FAC2026001')
        self.assertEqual(identity['document_year'], 2026)
        self.assertEqual(identity['gross_total'], 1234.50)
        self.assertEqual(identity['currency'], 'EUR')
        self.assertEqual(identity['file_hash'], 'abcdef')

    def test_provisional_and_final_invoice_share_business_class(self):
        left = self.identity(document_type='provisional_invoice')
        right = self.identity(document_type='invoice')
        left['file_hash'] = 'left'
        right['file_hash'] = 'right'
        self.assertEqual(document_duplicate_identities_match(left, right), 'business')

    def test_exact_hash_matches_any_document_class(self):
        left = self.identity(document_type='mail')
        right = self.identity(document_type='advertising')
        self.assertEqual(document_duplicate_identities_match(left, right), 'exact')

    def test_all_document_types_match_by_complete_business_key(self):
        left = self.identity(document_type='mail')
        right = self.identity(document_type='mail')
        left['file_hash'] = 'left'
        right['file_hash'] = 'right'
        self.assertEqual(document_duplicate_identities_match(left, right), 'business')

    def test_amount_is_not_part_of_the_complete_business_key(self):
        left = self.identity()
        right = self.identity(totals={'gross_total': '1234,51'})
        left['file_hash'] = 'left'
        right['file_hash'] = 'right'
        self.assertEqual(document_duplicate_identities_match(left, right), 'business')

    def test_incomplete_high_score_is_possible_duplicate(self):
        left = self.identity()
        right = self.identity()
        left['file_hash'] = 'left'
        right['file_hash'] = 'right'
        right['document_date'] = None
        right['document_year'] = None
        assessment = evaluate_duplicate_match(left, right)
        self.assertEqual(assessment['classification'], 'possible')
        self.assertEqual(assessment['match_type'], 'possible')
        self.assertGreaterEqual(assessment['score'], 85)
        self.assertIn('document_date', assessment['missing_fields'])

    def test_conflicting_business_field_is_new_document(self):
        left = self.identity()
        right = self.identity()
        left['file_hash'] = 'left'
        right['file_hash'] = 'right'
        right['document_number'] = 'OUTRO2026'
        assessment = evaluate_duplicate_match(left, right)
        self.assertEqual(assessment['classification'], 'new')
        self.assertIn('document_number', assessment['conflicting_fields'])


if __name__ == '__main__':
    unittest.main()
