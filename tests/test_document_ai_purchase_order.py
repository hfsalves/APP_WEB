import unittest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from services import document_ai_purchase_order_service as service


class DocumentAiPurchaseOrderTests(unittest.TestCase):
    def test_series_is_discovered_by_name_instead_of_hardcoded_number(self):
        with patch.object(service, '_rows', return_value=[
            {'ndos': 2, 'nmdos': 'Bon Commande Fournisseur'},
            {'ndos': 99, 'nmdos': 'Outra série'},
        ]):
            series = service._purchase_order_series(MagicMock())

        self.assertEqual(series, {'ndos': 2, 'name': 'Bon Commande Fournisseur'})

    def test_series_rejects_ambiguous_configuration(self):
        with patch.object(service, '_rows', return_value=[
            {'ndos': 2, 'nmdos': 'Bon Commande Fournisseur'},
            {'ndos': 102, 'nmdos': 'Bon Commande Fournisseur'},
        ]):
            with self.assertRaisesRegex(ValueError, 'única série'):
                service._purchase_order_series(MagicMock())

    def test_contract_series_are_discovered_without_hardcoded_numbers(self):
        with patch.object(service, '_rows', return_value=[
            {'ndos': 119, 'nmdos': 'Contrat'},
            {'ndos': 128, 'nmdos': 'Contrat Sous-Traitant'},
        ]):
            contract = service._purchase_order_series(MagicMock(), 'contract')
            subcontract = service._purchase_order_series(MagicMock(), 'subcontract')

        self.assertEqual(contract, {'ndos': 119, 'name': 'Contrat'})
        self.assertEqual(subcontract, {'ndos': 128, 'name': 'Contrat Sous-Traitant'})

    def test_stable_creation_stamp_is_repeatable_and_phc_sized(self):
        first = service._stable_stamp('DOCNDE', 'DOC-123')
        second = service._stable_stamp('DOCNDE', 'DOC-123')

        self.assertEqual(first, second)
        self.assertEqual(len(first), 25)
        self.assertNotEqual(first, service._stable_stamp('DOCNDE', 'DOC-124'))

    def test_new_line_stamp_follows_portal_identity_not_position(self):
        row = {'portal_line_id': 'SUBLINE-STABLE'}
        first = service._planned_line_stamp('DOC-123', row, 1)
        reordered = service._planned_line_stamp('DOC-123', row, 7)

        self.assertEqual(first, reordered)
        self.assertEqual(len(first), 25)

    def test_plan_uses_only_controlled_line_values_and_dynamic_series(self):
        cursor = MagicMock()
        cursor.execute.return_value.fetchone.return_value = (1,)
        document = {
            'document_date': '2026-09-09',
            'currency': 'EUR',
            'supplier': {'supplier_no': 30489},
            'origin_project': {'ccusto': 'FR0002'},
            'lines': [{
                'article_ref': 'BETON-1', 'description': 'Béton contrôlé',
                'qty': 2, 'unit': 'M2', 'unit_price': 15,
                'net_amount': 30, 'tax_rate': 20,
            }],
        }
        supplier = {
            'no': 30489, 'estab': 0, 'name': 'SAS FORCH', 'tax_id': 'FR1',
            'address': '', 'city': '', 'postal_code': '', 'currency': 'EURO',
        }
        article = {'ref': 'BETON-1', 'design': 'Master', 'unidade': 'M2', 'familia': 'BETON', 'tabiva': 2}
        with patch('services.document_ai_service._phc_provisional_supplier', return_value=supplier), patch(
            'services.document_ai_service._effective_portal_lines', return_value=document['lines']
        ), patch('services.document_ai_service._phc_tax_configuration', return_value=(
            {2: Decimal('20.00')}, {Decimal('20.00'): 2},
        )), patch('services.document_ai_service._phc_tax_code', return_value=2), patch.object(
            service, '_purchase_order_series', return_value={'ndos': 102, 'name': 'Bon Commande Fournisseur'}
        ), patch.object(service, '_rows', return_value=[article]):
            plan = service._normalize_plan(cursor, document)

        self.assertEqual(plan['series']['ndos'], 102)
        self.assertEqual(plan['project'], 'FR0002')
        self.assertEqual(plan['lines'][0]['design'], 'Béton contrôlé')
        self.assertEqual(plan['lines'][0]['quantity'], Decimal('2'))
        self.assertEqual(plan['gross'], Decimal('36.00'))

    def test_plan_blocks_missing_controlled_unit(self):
        cursor = MagicMock()
        cursor.execute.return_value.fetchone.return_value = (1,)
        line = {'article_ref': 'A', 'description': 'Linha', 'qty': 1,
                'unit_price': 10, 'net_amount': 10, 'tax_rate': 20}
        document = {'document_date': '2026-09-09', 'currency': 'EUR',
                    'supplier': {'supplier_no': 1}, 'origin_project': {'ccusto': 'FR1'}, 'lines': [line]}
        with patch('services.document_ai_service._phc_provisional_supplier', return_value={
            'no': 1, 'estab': 0, 'name': 'F', 'currency': 'EURO',
        }), patch('services.document_ai_service._effective_portal_lines', return_value=[line]), patch(
            'services.document_ai_service._phc_tax_configuration', return_value=({}, {})
        ), patch.object(service, '_purchase_order_series', return_value={'ndos': 2, 'name': 'Bon Commande Fournisseur'}), patch.object(
            service, '_rows', return_value=[{'ref': 'A'}]
        ):
            with self.assertRaisesRegex(ValueError, 'confirma a unidade'):
                service._normalize_plan(cursor, document)

    def test_snapshot_detects_phc_concurrent_changes(self):
        header = {'bostamp': 'BO1', 'ndos': 102, 'obrano': 7, 'boano': 2026, 'fechada': 0}
        line = {'bistamp': 'BI1', 'ref': 'A', 'qtt': Decimal('1'), 'qtt2': Decimal('0')}

        before = service._snapshot(header, [line])
        after = service._snapshot(header, [{**line, 'qtt': Decimal('2')}])

        self.assertNotEqual(before, after)


class DocumentAiPurchaseOrderFrontendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open('static/js/document_ai_extract.js', encoding='utf-8') as handle:
            cls.script = handle.read()
        with open('templates/document_ai_extract.html', encoding='utf-8') as handle:
            cls.template = handle.read()

    def test_context_actions_are_implemented_and_management_only(self):
        self.assertIn("registerDocumentAiOriginAction('create_purchase_order'", self.script)
        self.assertIn("registerDocumentAiOriginAction('correct_purchase_order'", self.script)
        self.assertIn("registerDocumentAiOriginAction('create_contract'", self.script)
        self.assertIn("registerDocumentAiOriginAction('correct_contract'", self.script)
        self.assertIn("registerDocumentAiOriginAction('create_subcontract'", self.script)
        self.assertIn("registerDocumentAiOriginAction('correct_subcontract'", self.script)
        self.assertIn("'phc-source/preview'", self.script)
        self.assertIn("'phc-source/validate'", self.script)
        self.assertIn("state.view === 'management'", self.script)

    def test_modal_requires_explicit_validation(self):
        self.assertIn('docAiOriginDetailValidate', self.template)
        self.assertIn('<i class="fa-solid fa-check"></i><span>Validar</span>', self.template)
        self.assertIn("'purchase-order/preview'", self.script)
        self.assertIn("'purchase-order/validate'", self.script)


if __name__ == '__main__':
    unittest.main()
