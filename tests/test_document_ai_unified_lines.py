import unittest

from services.document_ai_line_distribution_service import (
    distribution_errors,
    normalize_line_structures,
    validate_group_pair,
)
from services.document_ai_service import (
    _assert_effective_portal_lines,
    _effective_portal_lines,
    _normalize_invoice_type,
    normalize_unified_document_model,
)


class UnifiedDocumentLinesTests(unittest.TestCase):
    def test_legacy_cp_is_migrated_to_services_without_losing_cost_detail(self):
        source = {
            'document_type': 'invoice',
            'invoice_type': 'fuel_tolls',
            'audit': {'created_by': 'msilva'},
            'lines': [{
                'line_id': 'L1', 'article_ref': 'A1', 'unit': 'UN',
                'accounting_consolidated': True, 'qty': 2,
                'unit_price': None, 'net_amount': 36,
                'sub_lines': [{
                    'subline_id': 'S1', 'description': 'Gasóleo', 'qty': 12,
                    'unit_price': 1.5, 'net_amount': 18, 'transaction_id': 'TX-1',
                }],
            }],
        }
        migrated = normalize_unified_document_model(source, 'DOC-1')
        self.assertEqual(migrated['invoice_type'], 'services')
        self.assertEqual(migrated['line_model_version'], 'TP065')
        self.assertEqual(migrated['audit'], source['audit'])
        line = migrated['lines'][0]
        self.assertEqual(line['line_id'], 'L1')
        self.assertEqual(line['line_model_version'], 'TP065')
        self.assertEqual(line['qty'], 1)
        self.assertEqual(line['unit_price'], 36)
        self.assertNotIn('sub_lines', line)
        self.assertEqual(line['detailed_costs'][0]['transaction_id'], 'TX-1')
        self.assertEqual(line['detailed_costs'][0]['subline_id'], 'S1')
        self.assertFalse(line['detailed_costs'][0]['accounting_effective'])

    def test_detailed_costs_never_create_phc_lines(self):
        line = {
            'line_id': 'L1', 'article_ref': 'A1', 'unit': 'UN', 'qty': 1,
            'unit_price': 36, 'net_amount': 36, 'tax_rate': 23,
            'detailed_costs': [
                {'cost_type': 'included', 'net_amount': 18},
                {'cost_type': 'additional', 'net_amount': 3},
            ],
        }
        effective = _effective_portal_lines(normalize_line_structures([line]))
        self.assertEqual(len(effective), 1)
        self.assertEqual(effective[0]['portal_line_id'], 'L1')

    def test_group_allows_different_pu_and_unit_but_not_common_fields(self):
        principal = {'article_ref': 'A1', 'unit_price': 10, 'unit': 'UN', 'tax_rate': 23}
        associated = {'article_ref': 'A1', 'unit_price': 20, 'unit': 'KG', 'tax_rate': 23}
        self.assertEqual(validate_group_pair(principal, associated), '')
        associated['tax_rate'] = 6
        self.assertEqual(validate_group_pair(principal, associated), 'Impossível agrupar: IVA diferente.')

    def test_distribution_requires_exact_100_percent_and_reconciled_values(self):
        line = {
            'qty': 10, 'unit_price': 5, 'net_amount': 50, 'tax_rate': 23,
            'sub_lines': [
                {'ccusto': 'A', 'qty': 4, 'unit_price': 5, 'net_amount': 20, 'percentage': 40},
                {'ccusto': 'B', 'qty': 6, 'unit_price': 5, 'net_amount': 30, 'percentage': 60},
            ],
        }
        self.assertEqual(distribution_errors(line), [])
        line['sub_lines'][1]['percentage'] = 59
        self.assertIn('A distribuição deve totalizar exatamente 100 %.', distribution_errors(line))

    def test_legacy_distribution_gets_idempotent_percentages(self):
        lines = normalize_line_structures([{
            'line_id': 'L1', 'qty': 3, 'net_amount': 30,
            'sub_lines': [
                {'subline_id': 'S1', 'ccusto': 'A', 'qty': 1, 'net_amount': 10},
                {'subline_id': 'S2', 'ccusto': 'B', 'qty': 2, 'net_amount': 20},
            ],
        }])
        self.assertAlmostEqual(lines[0]['sub_lines'][0]['percentage'], 33.333333)
        self.assertAlmostEqual(lines[0]['sub_lines'][1]['percentage'], 66.666667)
        self.assertEqual(normalize_line_structures(lines), lines)

    def test_all_cp_aliases_now_resolve_to_services(self):
        for value in ('C&P', 'fuel_tolls', 'cp', 'combustiveis_e_portagens'):
            self.assertEqual(_normalize_invoice_type(value), 'services')

    def test_generic_distribution_has_eight_visible_and_36_effective_lines(self):
        labels = (
            'Gazole Premier', 'Super 98 Sans Plomb', 'SP95 E10', 'AdBlue Bidon',
            'Accessoires', 'Télépéage Liber-t', 'Liber-T Abonnement', 'Frais de Gestion',
        )
        lines = [
            {'line_id': f'L{index}', 'description': label, 'qty': 1, 'unit_price': 1, 'net_amount': 1}
            for index, label in enumerate(labels)
        ]
        lines[0]['sub_lines'] = [
            {'subline_id': f'S{index}', 'qty': 1 / 29, 'net_amount': 1 / 29, 'percentage': 100 / 29}
            for index in range(29)
        ]
        self.assertEqual(len(lines), 8)
        self.assertEqual(len(_effective_portal_lines(lines)), 36)
        self.assertFalse(any(item.get('portal_line_id') == 'L0' for item in _effective_portal_lines(lines)))

    def test_demonstrated_line_rounding_accepts_one_cent_and_blocks_more(self):
        line = {
            'article_ref': 'BETON', 'unit': 'M3', 'ccusto': 'C1', 'tax_rate': 20,
            'qty': 18, 'unit_price': 4.65, 'net_amount': 83.71,
        }
        self.assertEqual(len(_assert_effective_portal_lines([line])), 1)
        with self.assertRaisesRegex(ValueError, 'Quantidade × PU'):
            _assert_effective_portal_lines([{**line, 'net_amount': 83.72}])

    def test_generic_detailed_costs_do_not_double_count(self):
        lines = [
            {'line_id': f'L{index}', 'description': f'Produto {index}', 'net_amount': 0}
            for index in range(13)
        ]
        lines[0]['net_amount'] = 533.11
        lines.append({'line_id': 'L13', 'description': 'Frais de gestion', 'net_amount': 6.25})
        lines[0]['detailed_costs'] = [{'cost_type': 'included', 'description': 'PMCB', 'net_amount': 0.20}]
        lines[1]['detailed_costs'] = [{'cost_type': 'included', 'description': 'PMCB', 'net_amount': 0.20}]
        normalized = normalize_line_structures(lines, 'GENERIC')
        self.assertEqual(len(normalized), 14)
        self.assertAlmostEqual(sum(float(line['net_amount']) for line in normalized), 539.36)
        self.assertAlmostEqual(sum(float(cost['net_amount']) for line in normalized for cost in line.get('detailed_costs', [])), 0.40)
        self.assertEqual(len(_effective_portal_lines(normalized)), 14)


if __name__ == '__main__':
    unittest.main()
