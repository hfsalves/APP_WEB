import unittest

from services.opc_phc_info_service import (
    AUTOS_SQL,
    FT_STANDALONE_SQL,
    _origin_phc_process_prefix,
    _phc_process_code,
)


class OpcPhcInfoProcessCodeTests(unittest.TestCase):
    def test_intersol_origin_uses_is_prefix(self):
        self.assertEqual(
            _origin_phc_process_prefix("INTERSOL-ALSACE", "INTERSOL"),
            "IS",
        )
        self.assertEqual(
            _phc_process_code("HS1849", "INTERSOL-ALSACE", "INTERSOL"),
            "IS1849",
        )

    def test_france_origin_keeps_fr_prefix(self):
        self.assertEqual(
            _phc_process_code("HS1849", "HSOLS FRANCE", "HSOLS_FR"),
            "FR1849",
        )

    def test_customer_advance_reduces_vat_base(self):
        self.assertIn(
            "((C.PROD - C.AJUST) + C.ACOMPTE - C.RG",
            AUTOS_SQL,
        )
        self.assertIn(
            "F.BASE_NET - F.ACOMPTE + ROUND(F.BASE_NET",
            AUTOS_SQL,
        )
        self.assertIn(
            "((PROD - AJUST) + ACOMPTE - RG",
            FT_STANDALONE_SQL,
        )
        self.assertIn(
            "((PROD - AJUST) - RG - RFT - AUTRET - PRORATA) + ROUND(((PROD - AJUST) + ACOMPTE",
            FT_STANDALONE_SQL,
        )


if __name__ == "__main__":
    unittest.main()
