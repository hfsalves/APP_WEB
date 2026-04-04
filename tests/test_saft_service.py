import unittest
from decimal import Decimal

from services.saft_service import _prepare_doc_for_saft, SaftValidationError


class SaftServiceTests(unittest.TestCase):
    def _header(self, desconto=0):
        return {
            'FTSTAMP': 'FT1',
            'NMDOC': 'Fatura',
            'SERIE': 'FT',
            'FNO': 1,
            'MOEDA': 'EUR',
            'DESCONTO': desconto,
        }

    def _line(self, *, qtt=1, epv=100, desconto=0, iva=23, miseimp=''):
        return {
            'FISTAMP': 'FI1',
            'REF': 'ART1',
            'DESIGN': 'Artigo teste',
            'QTT': qtt,
            'EPV': epv,
            'DESCONTO': desconto,
            'IVA': iva,
            'UNIDADE': 'UN',
            'MISEIMP': miseimp,
        }

    def test_without_global_discount_has_no_settlement(self):
        header, lines = _prepare_doc_for_saft(self._header(0), [self._line(qtt=2, epv=50)], {})
        self.assertEqual(header['_SAFT_NET_TOTAL'], Decimal('100.00'))
        self.assertEqual(header['_SAFT_SETTLEMENT_TOTAL'], Decimal('0.00'))
        self.assertEqual(header['_SAFT_TAX_TOTAL'], Decimal('23.00'))
        self.assertEqual(header['_SAFT_GROSS_TOTAL'], Decimal('123.00'))
        self.assertEqual(lines[0]['_SAFT_NET_AMOUNT'], Decimal('100.000000'))

    def test_global_discount_only_sets_settlement_amount(self):
        header, lines = _prepare_doc_for_saft(self._header(10), [self._line(qtt=2, epv=50)], {})
        self.assertEqual(header['_SAFT_NET_TOTAL'], Decimal('100.00'))
        self.assertEqual(header['_SAFT_SETTLEMENT_TOTAL'], Decimal('10.00'))
        self.assertEqual(header['_SAFT_TAX_TOTAL'], Decimal('20.70'))
        self.assertEqual(header['_SAFT_GROSS_TOTAL'], Decimal('110.70'))
        self.assertEqual(lines[0]['_SAFT_NET_AMOUNT'], Decimal('100.000000'))
        self.assertEqual(lines[0]['_SAFT_HEADER_SETTLEMENT'], Decimal('10.000000'))

    def test_line_discount_only_stays_in_line(self):
        header, lines = _prepare_doc_for_saft(self._header(0), [self._line(qtt=2, epv=50, desconto=10)], {})
        self.assertEqual(header['_SAFT_NET_TOTAL'], Decimal('90.00'))
        self.assertEqual(header['_SAFT_SETTLEMENT_TOTAL'], Decimal('0.00'))
        self.assertEqual(header['_SAFT_TAX_TOTAL'], Decimal('20.70'))
        self.assertEqual(lines[0]['_SAFT_UNIT_PRICE'], Decimal('45.000000'))

    def test_line_and_global_discount_both_apply_without_duplication(self):
        header, lines = _prepare_doc_for_saft(self._header(5), [self._line(qtt=100, epv='0.55', desconto='8.8')], {})
        self.assertEqual(header['_SAFT_NET_TOTAL'], Decimal('50.16'))
        self.assertEqual(header['_SAFT_SETTLEMENT_TOTAL'], Decimal('2.51'))
        self.assertEqual(header['_SAFT_TAX_TOTAL'], Decimal('10.96'))
        self.assertEqual(header['_SAFT_GROSS_TOTAL'], Decimal('58.61'))
        self.assertEqual(lines[0]['_SAFT_NET_AMOUNT'], Decimal('50.160000'))
        self.assertEqual(lines[0]['_SAFT_HEADER_SETTLEMENT'], Decimal('2.508000'))

    def test_zero_vat_uses_exact_miseimp_description(self):
        header, lines = _prepare_doc_for_saft(
            self._header(0),
            [self._line(qtt=1, epv=100, iva=0, miseimp='M05')],
            {'M05': 'Isento artigo 14.º do CIVA'},
        )
        self.assertEqual(header['_SAFT_SETTLEMENT_TOTAL'], Decimal('0.00'))
        self.assertEqual(lines[0]['MISEIMP'], 'M05')
        self.assertEqual(lines[0]['MISEIMP_DESCRICAO'], 'Isento artigo 14.º do CIVA')

    def test_zero_vat_without_code_blocks_export(self):
        with self.assertRaises(SaftValidationError):
            _prepare_doc_for_saft(self._header(0), [self._line(qtt=1, epv=100, iva=0, miseimp='')], {'M05': 'X'})

    def test_zero_vat_with_unknown_code_blocks_export(self):
        with self.assertRaises(SaftValidationError):
            _prepare_doc_for_saft(self._header(0), [self._line(qtt=1, epv=100, iva=0, miseimp='M07')], {'M05': 'X'})


if __name__ == '__main__':
    unittest.main()
