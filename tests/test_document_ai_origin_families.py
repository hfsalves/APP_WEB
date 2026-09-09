import unittest

from services.document_ai_service import (
    _phc_origin_family,
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

    def test_delivery_note_requires_purchase_order(self):
        with self.assertRaisesRegex(ValueError, 'primeiro uma Nota de Encomenda'):
            _validate_phc_origin_combination([], {'ndos': 130})

    def test_work_situation_requires_subcontract(self):
        with self.assertRaisesRegex(ValueError, 'Sout-Traitant'):
            _validate_phc_origin_combination([{'ndos': 119}], {'ndos': 129})

    def test_line_and_subline_must_reference_selected_origins(self):
        origins = [{'stamp': 'BO-NDE'}, {'stamp': 'BO-CONTRATO'}]
        _validate_line_phc_origin_assignments([
            {'phc_origin_stamp': 'BO-NDE'},
            {'sublines': [{'phc_origin_stamp': 'BO-CONTRATO'}]},
        ], origins)
        with self.assertRaisesRegex(ValueError, 'não está associada'):
            _validate_line_phc_origin_assignments([{'phc_origin_stamp': 'BO-OUTRA'}], origins)


if __name__ == '__main__':
    unittest.main()
