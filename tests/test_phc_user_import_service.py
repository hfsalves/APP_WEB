import unittest
from unittest.mock import MagicMock, call, patch

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


class CollaboratorUserWizardTests(unittest.TestCase):
    def _payload(self):
        return {
            "nome": "Ana Silva",
            "login": "ana.silva",
            "password": "temporary-secret",
            "email": "ana.silva@example.test",
            "employer_feid": 2,
            "employee_no": 47,
            "feids": [2, 8],
            "principal_feid": 8,
        }

    def test_create_links_selected_employee_and_explicit_principal_company(self):
        fake_db = MagicMock()
        fake_db.session.begin_nested.return_value.__enter__.return_value = None
        company = {"FEID": 2, "NOME": "Empresa Empregadora", "PHC_DB": "PHC_EMPRESA"}
        employee = {"no": 47, "nome": "Ana Silva", "email": "ana.silva@example.test"}

        with (
            patch.object(phc_user_import_service, "db", fake_db),
            patch.object(phc_user_import_service, "collaborator_user_company_options", return_value=[
                {"feid": 2, "nome": "Empresa Empregadora", "phc_configured": True},
                {"feid": 8, "nome": "Empresa Acessível", "phc_configured": True},
            ]),
            patch.object(phc_user_import_service, "_find_local_user_by_login", return_value=None),
            patch.object(phc_user_import_service, "_email_conflict", return_value=None),
            patch.object(phc_user_import_service, "_collaborator_user_employee", return_value=(company, employee)),
            patch.object(phc_user_import_service, "_employee_link_conflict", return_value=None),
            patch.object(phc_user_import_service, "_insert_or_update_user", return_value=("USERSTAMP", True)) as insert_user,
            patch.object(phc_user_import_service, "_set_initial_password_hash") as set_hash,
            patch.object(phc_user_import_service, "_set_user_employee_link") as set_employee,
            patch.object(phc_user_import_service, "_ensure_user_company") as ensure_company,
            patch.object(phc_user_import_service, "_ensure_collaborator_accesses") as ensure_accesses,
        ):
            result = phc_user_import_service.create_collaborator_user(self._payload(), "admin")

        self.assertTrue(result["ok"])
        self.assertEqual(result["employee"]["pefeid"], 2)
        self.assertEqual(result["employee"]["peno"], 47)
        insert_user.assert_called_once_with({
            "nome": "Ana Silva",
            "login": "ana.silva",
            "password": "temporary-secret",
            "email": "ana.silva@example.test",
            "home": "dashboard",
            "vendedor": 0,
        })
        set_hash.assert_called_once_with("USERSTAMP", "temporary-secret")
        set_employee.assert_called_once_with("USERSTAMP", company, employee)
        ensure_company.assert_has_calls([
            call("USERSTAMP", 2, False, "admin"),
            call("USERSTAMP", 8, True, "admin"),
        ])
        ensure_accesses.assert_called_once_with("ana.silva", "USERSTAMP")
        fake_db.session.commit.assert_called_once()

    def test_employer_company_must_be_accessible(self):
        payload = self._payload()
        payload["feids"] = [8]

        with self.assertRaisesRegex(ValueError, "também deve estar nas empresas acessíveis"):
            phc_user_import_service.create_collaborator_user(payload, "admin")

    def test_existing_employee_link_is_rejected(self):
        fake_db = MagicMock()
        company = {"FEID": 2, "NOME": "Empresa Empregadora", "PHC_DB": "PHC_EMPRESA"}
        employee = {"no": 47, "nome": "Ana Silva"}

        with (
            patch.object(phc_user_import_service, "db", fake_db),
            patch.object(phc_user_import_service, "collaborator_user_company_options", return_value=[
                {"feid": 2, "nome": "Empresa Empregadora", "phc_configured": True},
                {"feid": 8, "nome": "Empresa Acessível", "phc_configured": True},
            ]),
            patch.object(phc_user_import_service, "_find_local_user_by_login", return_value=None),
            patch.object(phc_user_import_service, "_email_conflict", return_value=None),
            patch.object(phc_user_import_service, "_collaborator_user_employee", return_value=(company, employee)),
            patch.object(phc_user_import_service, "_employee_link_conflict", return_value={"LOGIN": "existing.user"}),
        ):
            with self.assertRaisesRegex(ValueError, "existing.user"):
                phc_user_import_service.create_collaborator_user(self._payload(), "admin")

    def test_employee_query_builds_valid_status_condition(self):
        cursor = MagicMock()
        cursor.fetchall.side_effect = [
            [("no",), ("nome",), ("status",)],
            [],
        ]
        connection = MagicMock()
        connection.cursor.return_value = cursor
        connection_context = MagicMock()
        connection_context.__enter__.return_value = connection

        with (
            patch.object(phc_user_import_service, "_phc_conn_str", return_value="connection-string"),
            patch.object(phc_user_import_service.pyodbc, "connect", return_value=connection_context),
        ):
            rows = phc_user_import_service._read_company_employees({
                "PHC_DB": "PHC_EMPRESA",
                "PHC_SERVER": "",
            })

        self.assertEqual(rows, [])
        employee_query = cursor.execute.call_args_list[1].args[0]
        self.assertIn("AND ISNULL(PE.STATUS, 1) <> 3", employee_query)
        self.assertNotIn("AND AND", employee_query)


if __name__ == "__main__":
    unittest.main()
