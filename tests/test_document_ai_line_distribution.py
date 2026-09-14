import unittest

from services.document_ai_line_distribution_service import (
    distribution_errors,
    line_workflow_errors,
    normalize_line_structures,
    validate_group_pair,
)


class DocumentAiLineDistributionTests(unittest.TestCase):
    def test_stable_ids_and_legacy_group_migration(self):
        source = [{'article_group_code': 'P1', 'description': 'A'}, {'article_group_code': 'A1', 'description': 'B'}]
        first = normalize_line_structures(source, 'DOC-1')
        second = normalize_line_structures(source, 'DOC-1')
        self.assertEqual(first[0]['line_id'], second[0]['line_id'])
        self.assertEqual(first[0]['group_role'], 'principal')
        self.assertEqual(first[1]['group_role'], 'associated')
        self.assertNotIn('article_group_code', first[0])

    def test_subline_inherits_shared_line_fields_without_overwrite(self):
        line = {
            'article_ref': 'A', 'unit_price': 5, 'unit': 'UN', 'date': '2026-09-10', 'tax_rate': 23,
            'sub_lines': [{'ccusto': 'C1', 'unit': 'KG'}],
        }
        child = normalize_line_structures([line], 'DOC-1')[0]['sub_lines'][0]
        self.assertEqual(child['article_ref'], 'A')
        self.assertEqual(child['unit_price'], 5)
        self.assertEqual(child['unit'], 'KG')
        self.assertEqual(child['tax_rate'], 23)

    def test_group_conflicts_use_exact_messages(self):
        base = {'article_ref': 'A', 'unit_price': 10, 'ccusto': 'C1', 'registration': 'AA', 'date': '2026-01-01', 'tax_rate': 20, 'unit': 'UN'}
        variants = {
            'Artigo': {'article_ref': 'B'},
            'Centro de Custo': {'ccusto': 'C2'}, 'Data': {'date': '2026-01-02'},
            'IVA': {'tax_rate': 21}, 'Matrícula': {'registration': 'BB'},
        }
        for label, change in variants.items():
            with self.subTest(label=label):
                self.assertEqual(validate_group_pair(base, {**base, **change}), f'Impossível agrupar: {label} diferente.')
        self.assertEqual(validate_group_pair(base, {**base, 'unit_price': 11, 'unit': 'KG'}), '')

    def test_multiple_destinations_must_match_as_a_common_configuration(self):
        principal = {'ccusto': 'C1', 'sub_lines': [{'ccusto': 'C1'}, {'ccusto': 'C2'}]}
        associated = {'sub_lines': [{'ccusto': 'C2'}, {'ccusto': 'C1'}]}
        self.assertEqual(validate_group_pair(principal, associated), '')
        self.assertEqual(
            validate_group_pair(principal, {'ccusto': 'C3'}),
            'Impossível agrupar: Centro de Custo diferente.',
        )

    def test_complete_distribution_is_valid(self):
        line = {'qty': 10, 'unit_price': 5, 'net_amount': 50, 'sub_lines': [
            {'ccusto': 'C1', 'qty': 4, 'net_amount': 20, 'percentage': 40, 'tax_rate': 23},
            {'ccusto': 'C2', 'qty': 6, 'net_amount': 30, 'percentage': 60, 'tax_rate': 23},
        ]}
        self.assertEqual(distribution_errors(line), [])

    def test_distribution_rejects_duplicate_overflow_and_missing_values(self):
        line = {'qty': 10, 'unit_price': 5, 'net_amount': 50, 'sub_lines': [
            {'ccusto': 'C1', 'qty': 8, 'net_amount': 40},
            {'ccusto': 'C1', 'qty': 4, 'net_amount': 20},
        ]}
        errors = distribution_errors(line)
        self.assertTrue(any('duplicada' in value for value in errors))
        self.assertTrue(any('excede' in value for value in errors))

    def test_vehicle_without_cost_center_and_zero_price_are_explicit(self):
        line = {'qty': 1, 'unit_price': 0, 'net_amount': 0, 'sub_lines': [
            {'registration': 'AA-00-AA', 'qty': 1, 'net_amount': 0, 'tax_rate': 23},
        ]}
        errors = distribution_errors(line)
        self.assertIn('Matrícula s/Centro de Custo', errors)
        self.assertIn('PU igual a zero: corrige explicitamente a linha antes de validar.', errors)

    def test_distribution_requires_percentage_tax_and_non_negative_values(self):
        line = {'qty': -1, 'unit_price': 5, 'net_amount': -5, 'sub_lines': [
            {'ccusto': 'C1', 'qty': -1, 'net_amount': -5, 'tax_rate': ''},
        ]}
        errors = distribution_errors(line)
        self.assertIn('Falta IVA numa sublinha.', errors)
        self.assertIn('Quantidade e PT não podem ser negativos.', errors)

    def test_group_and_distribution_errors_are_combined(self):
        lines = [
            {'group_id': 'G', 'group_role': 'principal', 'article_ref': 'A'},
            {'group_id': 'G', 'group_role': 'associated', 'article_ref': 'B'},
        ]
        self.assertIn('Impossível agrupar: Artigo diferente.', line_workflow_errors(lines))

    def test_group_requires_every_common_mandatory_field(self):
        complete = {
            'article_ref': 'A', 'tax_rate': 23, 'phc_origin_stamp': 'BO1', 'phc_origin_line_stamp': 'BI1',
            'ccusto': 'C1', 'date': '2026-09-14', 'registration': 'AA-00-AA',
        }
        lines = [
            {**complete, 'group_id': 'G', 'group_role': 'principal'},
            {**complete, 'group_id': 'G', 'group_role': 'associated'},
        ]
        self.assertEqual(line_workflow_errors(lines), [])
        for field, label in (
            ('article_ref', 'Artigo'), ('tax_rate', 'IVA'), ('phc_origin_stamp', 'Origem'),
            ('ccusto', 'Centro de Custo'), ('date', 'Data'), ('registration', 'Matrícula'),
        ):
            with self.subTest(field=field):
                incomplete = [dict(item) for item in lines]
                incomplete[0][field] = ''
                incomplete[1][field] = ''
                self.assertTrue(any(label in error for error in line_workflow_errors(incomplete)))


if __name__ == '__main__':
    unittest.main()
