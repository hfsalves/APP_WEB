from datetime import date
from decimal import Decimal
import unittest

from scripts.import_bmso_hsols_fr import BL_NDOS, PF_NDOS, header_values


class BmsoDeliveryNoteMappingTests(unittest.TestCase):
    def setUp(self):
        self.source_header = {
            'NOME': 'SAS BMSO',
            'NO': 31106,
            'NCONT': 'FR00000000000',
            'MORADA': '',
            'LOCAL': '',
            'CODPOST': '',
            'ESTAB': 0,
            'MOEDA': 'EURO',
            'CCUSTO': 'FR1739',
        }

    def test_delivery_note_number_is_stored_in_bo_maquina(self):
        values = header_values(
            'BLSTAMP', BL_NDOS, 'Bon Livraison Fourn.', 8505,
            date(2026, 7, 23), self.source_header, 'B4-016031',
            Decimal('100'), Decimal('20'), True,
        )

        self.assertEqual(values['maquina'], 'B4-016031')
        self.assertEqual(values['fref'], '')

    def test_preinvoice_number_remains_in_bo_fref(self):
        values = header_values(
            'PFSTAMP', PF_NDOS, 'Pré-Facture', 8506,
            date(2026, 7, 23), self.source_header, '9001234567',
            Decimal('100'), Decimal('20'), False,
        )

        self.assertEqual(values['fref'], '9001234567')
        self.assertEqual(values['maquina'], '')


if __name__ == '__main__':
    unittest.main()
