import unittest
from unittest.mock import patch

from services import phc_user_import_service


class PhcUserImportSalespersonTests(unittest.TestCase):
    def test_intersol_salesperson_takes_priority_over_other_phc_companies(self):
        sources = [
            {"FEID": 1, "NOME": "Outra", "PHC_DB": "OUTRA", "PHC_SERVER": ""},
            {"FEID": 8, "NOME": "Intersol", "PHC_DB": "INTERSOL", "PHC_SERVER": ""},
        ]

        def source_users(source):
            salesperson = 99 if source["PHC_DB"] == "OUTRA" else 12
            return ([{
                "nome": "Utilizador",
                "login": "utilizador",
                "email": "utilizador@example.test",
                "password": "secret",
                "vendedor": salesperson,
            }], "")

        with (
            patch.object(phc_user_import_service, "_active_fe_sources", return_value=sources),
            patch.object(phc_user_import_service, "_read_source_users", side_effect=source_users),
            patch.object(phc_user_import_service, "_local_users_by_login", return_value={}),
            patch.object(phc_user_import_service, "_local_users_by_email", return_value={}),
        ):
            rows, warnings, returned_sources = phc_user_import_service._aggregate_source_users()

        self.assertEqual(warnings, [])
        self.assertEqual(returned_sources, sources)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["vendedor"], 12)
        self.assertTrue(rows[0]["vendedor_intersol"])

    def test_first_nonzero_salesperson_is_used_when_user_is_not_in_intersol(self):
        sources = [
            {"FEID": 1, "NOME": "Primeira", "PHC_DB": "PRIMEIRA", "PHC_SERVER": ""},
            {"FEID": 2, "NOME": "Segunda", "PHC_DB": "SEGUNDA", "PHC_SERVER": ""},
        ]

        def source_users(source):
            salesperson = 7 if source["PHC_DB"] == "PRIMEIRA" else 8
            return ([{
                "nome": "Utilizador",
                "login": "utilizador",
                "email": "utilizador@example.test",
                "password": "secret",
                "vendedor": salesperson,
            }], "")

        with (
            patch.object(phc_user_import_service, "_active_fe_sources", return_value=sources),
            patch.object(phc_user_import_service, "_read_source_users", side_effect=source_users),
            patch.object(phc_user_import_service, "_local_users_by_login", return_value={}),
            patch.object(phc_user_import_service, "_local_users_by_email", return_value={}),
        ):
            rows, _, _ = phc_user_import_service._aggregate_source_users()

        self.assertEqual(rows[0]["vendedor"], 7)
        self.assertFalse(rows[0]["vendedor_intersol"])


if __name__ == "__main__":
    unittest.main()
