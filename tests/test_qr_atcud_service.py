import unittest

from services.qr_atcud_service import (
    build_atcud,
    build_fiscal_qr_payload,
    validate_atcud,
)


class QrAtcudServiceTests(unittest.TestCase):
    def _base_fe(self):
        return {"NIF": "505453770"}

    def _base_ft(self, tiposaft):
        return {
            "TIPOSAFT": tiposaft,
            "NMDOC": tiposaft,
            "SERIE": tiposaft,
            "FNO": 15,
            "FDATA": "2026-03-30",
            "NCONT": "123456789",
            "ANULADA": 0,
            "ASSINATURA": "ABCD1234SIGN",
            "ETTIVA": "23.00",
            "ETOTAL": "123.00",
            "EIVAIN1": "100.00",
            "EIVAV1": "23.00",
            "IVATX1": "23.00",
            "_QR_VERSION": "2",
        }

    def test_build_atcud_requires_min_validation_code(self):
        with self.assertRaisesRegex(ValueError, "pelo menos 8 caracteres"):
            build_atcud("FT123", 1)

    def test_build_atcud_requires_validation_code(self):
        with self.assertRaisesRegex(ValueError, "sem codigo de validacao"):
            build_atcud("", 1)

    def test_validate_atcud_rejects_prefixed_value(self):
        with self.assertRaisesRegex(ValueError, "nao pode incluir o prefixo"):
            validate_atcud("ATCUD:ABCD1234-15", 15)

    def test_build_qr_payload_ft_uses_real_atcud(self):
        payload = build_fiscal_qr_payload(
            self._base_ft("FT"),
            self._base_fe(),
            "ABCD1234-15",
            "12345",
            False,
        )
        self.assertIn("D:FT", payload)
        self.assertIn("F:20260330", payload)
        self.assertIn("G:FT FT/15", payload)
        self.assertIn("H:ABCD1234-15", payload)
        self.assertIn("I1:PT", payload)
        self.assertIn("I7:100.00", payload)
        self.assertIn("I8:23.00", payload)
        self.assertIn("R:12345", payload)
        self.assertNotIn("H:ATCUD:", payload)
        self.assertNotIn("V:", payload)

    def test_build_qr_payload_fs(self):
        payload = build_fiscal_qr_payload(
            self._base_ft("FS"),
            self._base_fe(),
            "ZXCV5678-15",
            "12345",
            False,
        )
        self.assertIn("D:FS", payload)
        self.assertIn("H:ZXCV5678-15", payload)

    def test_build_qr_payload_fr(self):
        payload = build_fiscal_qr_payload(
            self._base_ft("FR"),
            self._base_fe(),
            "QWER1234-15",
            "12345",
            False,
        )
        self.assertIn("D:FR", payload)

    def test_build_qr_payload_nc(self):
        payload = build_fiscal_qr_payload(
            self._base_ft("NC"),
            self._base_fe(),
            "NCAA1234-15",
            "12345",
            False,
        )
        self.assertIn("D:NC", payload)

    def test_build_qr_payload_gt(self):
        payload = build_fiscal_qr_payload(
            self._base_ft("GT"),
            self._base_fe(),
            "GTAA1234-15",
            "12345",
            False,
        )
        self.assertIn("D:GT", payload)

    def test_build_qr_payload_normalizes_certificate_number(self):
        payload = build_fiscal_qr_payload(
            self._base_ft("FT"),
            self._base_fe(),
            "ABCD1234-15",
            "9999.0000",
            False,
        )
        self.assertIn("R:9999", payload)
        self.assertNotIn("R:99990000", payload)

    def test_build_atcud_accepts_series_mapping(self):
        atcud = build_atcud({
            "SERIE": "FT",
            "CODIGO_VALIDACAO_AT": "AATEST01",
        }, 27)
        self.assertEqual(atcud, "AATEST01-27")


if __name__ == "__main__":
    unittest.main()
