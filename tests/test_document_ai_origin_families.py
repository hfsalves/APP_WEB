import unittest
from pathlib import Path

from services.document_ai_service import (
    _phc_origin_family,
    _score_phc_origin_candidate,
    _validate_origin_allocation_balances,
    _validate_line_phc_origin_assignments,
    _validate_phc_origin_combination,
)


class DocumentAiOriginFamilyTests(unittest.TestCase):
    def test_family_normalizes_phc_document_types(self):
        self.assertEqual(_phc_origin_family({'ndos': 102}), 'bc')
        self.assertEqual(_phc_origin_family({'document_type': 'contract'}), 'contract')
        self.assertEqual(_phc_origin_family({'document_type': 'subcontract'}), 'subcontract')
        self.assertEqual(_phc_origin_family({'ndos': 129}), 'work_situation')

    def test_multiple_purchase_orders_are_allowed(self):
        _validate_phc_origin_combination([{'ndos': 102}], {'ndos': 102})

    def test_primary_families_can_be_mixed(self):
        _validate_phc_origin_combination([{'ndos': 102}], {'ndos': 119})
        _validate_phc_origin_combination([{'ndos': 102}, {'ndos': 119}], {'ndos': 128})

    def test_multiple_contracts_are_allowed(self):
        _validate_phc_origin_combination([{'ndos': 119}], {'ndos': 119})

    def test_delivery_note_requires_purchase_order_or_contract(self):
        with self.assertRaisesRegex(ValueError, 'Nota de Encomenda ou um Contrato'):
            _validate_phc_origin_combination([], {'ndos': 130})
        _validate_phc_origin_combination([{'ndos': 102}], {'ndos': 130})
        _validate_phc_origin_combination([{'ndos': 119}], {'ndos': 130})

    def test_contract_and_subcontract_can_coexist(self):
        _validate_phc_origin_combination([{'ndos': 119}], {'ndos': 128})

    def test_work_situation_requires_subcontract(self):
        with self.assertRaisesRegex(ValueError, r'Contrato Sub\.Emp\.'):
            _validate_phc_origin_combination([{'ndos': 119}], {'ndos': 129})

    def test_line_and_subline_must_reference_selected_origins(self):
        origins = [{'stamp': 'BO-NDE'}, {'stamp': 'BO-CONTRATO'}]
        _validate_line_phc_origin_assignments([
            {'phc_origin_stamp': 'BO-NDE'},
            {'sublines': [{'phc_origin_stamp': 'BO-CONTRATO'}]},
        ], origins)
        with self.assertRaisesRegex(ValueError, 'não está associada'):
            _validate_line_phc_origin_assignments([{'phc_origin_stamp': 'BO-OUTRA'}], origins)

    def test_frontend_does_not_lock_mixed_primary_families(self):
        script = (Path(__file__).resolve().parents[1] / 'static/js/document_ai_extract.js').read_text(encoding='utf-8')
        self.assertIn('function selectedPrimaryOriginFamilies()', script)
        self.assertNotIn('const contractLocked =', script)
        self.assertIn("primaryFamilies.has('bc') || primaryFamilies.has('contract')", script)

    def test_origin_search_does_not_require_a_cost_center(self):
        source = (Path(__file__).resolve().parents[1] / 'services/document_ai_service.py').read_text(encoding='utf-8')
        self.assertNotIn('Seleciona primeiro a obra para procurar origens elegíveis.', source)
        self.assertNotIn('project_filter_sql', source)
        self.assertIn("reasons.append('Mesma Obra')", source)
        self.assertIn("reasons.append('Outra Obra')", source)

    def test_origin_score_considers_intersol_agency_cost_center_and_articles(self):
        document = {
            'document_date': '2026-08-17',
            'customer': {'ged_folder': 'HSOLS_INTERSOL_LOR'},
            'origin_project': {'ccusto': 'IS0362'},
            'lines': [{'ref': 'ART-1', 'description': 'Location véhicule', 'qty': 1}],
            'totals': {'gross_total': 460.8},
        }
        candidate = {
            'document_type': 'purchase_order', 'ndos': 102, 'number': '1393',
            'date': '2026-08-01', 'ccusto': 'IS0362',
            'project_machine': 'INTERSOL-LORRAINE', 'project_location': 'METZ',
            'total': 460.8,
        }
        score, reasons = _score_phc_origin_candidate(candidate, document, [
            {'ref': 'ART-1', 'description': 'Location véhicule', 'pending_qty': 1},
        ])

        self.assertGreater(score, 0.8)
        self.assertIn('Mesma Obra', reasons)
        self.assertIn('Mesma agência INTERSOL', reasons)
        self.assertTrue(any('referências coincidem' in reason for reason in reasons))

    def test_manual_origin_allocations_cannot_exceed_phc_line_balance(self):
        origins = [{'stamp': 'BO-1393', 'lines': [
            {'line_stamp': 'BI-1', 'pending_qty': 3},
        ]}]
        _validate_origin_allocation_balances([
            {'bc_allocations': [{'origin_stamp': 'BO-1393', 'origin_line_stamp': 'BI-1', 'quantity': 3}]},
        ], origins)
        with self.assertRaisesRegex(ValueError, 'excede o saldo disponível'):
            _validate_origin_allocation_balances([
                {'bc_allocations': [{'origin_stamp': 'BO-1393', 'origin_line_stamp': 'BI-1', 'quantity': 2}]},
                {'bc_allocations': [{'origin_stamp': 'BO-1393', 'origin_line_stamp': 'BI-1', 'quantity': 2}]},
            ], origins)

    def test_origin_suggestions_never_write_lineage_automatically(self):
        script = (Path(__file__).resolve().parents[1] / 'static/js/document_ai_extract.js').read_text(encoding='utf-8')
        apply_source = script.split('function applyOriginLineReferences', 1)[1].split('function renderVirtualDeliveryNoteStage', 1)[0]
        self.assertIn('const selected = state.selectedOrigins;', apply_source)
        self.assertNotIn('target.phc_origin_links', apply_source)
        self.assertIn('confirma o dossier, a linha PHC e a quantidade', script)


if __name__ == '__main__':
    unittest.main()
