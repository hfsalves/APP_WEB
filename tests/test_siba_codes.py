import unittest

from services.siba_codes import country_to_icao


class SibaCodesTests(unittest.TestCase):
    def test_germany_uses_siba_code(self):
        for value in ("Alemanha", "Germany", "Deutschland", "DE", "DEU"):
            with self.subTest(value=value):
                self.assertEqual(country_to_icao(value), "D")


if __name__ == "__main__":
    unittest.main()
