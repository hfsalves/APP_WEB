import unittest
from unittest.mock import patch

from flask import Flask

from services import gr360_audit_service as audit


class Gr360AuditServiceTests(unittest.TestCase):
    def test_detects_gr360_context_only_when_explicit(self):
        config = {
            "GR360_AUDIT_ENABLED": "1",
            "GR360_AUDIT_TARGET": "client",
            "GR360_AUDIT_EXPECTED_DATABASE": "GR360_CORE",
            "GR360_AUDIT_SOURCE_DATABASE": "GR360_CORE",
        }

        self.assertTrue(audit.is_gr360_audit_context(config, current_target="client"))
        self.assertFalse(audit.is_gr360_audit_context(config, current_target="prod"))

    def test_guestspatur_context_returns_without_writing(self):
        app = Flask(__name__)
        app.config.update(
            GR360_AUDIT_ENABLED="1",
            GR360_AUDIT_TARGET="client",
            GR360_AUDIT_EXPECTED_DATABASE="GR360_CORE",
            GR360_AUDIT_SOURCE_DATABASE="GR360_CORE",
            GR360_AUDIT_TABLES="CL,OPC,VA,FL,ST",
            DB_CURRENT_TARGET_RESOLVER=lambda: "prod",
        )

        with app.test_request_context("/generic/api/CL", method="POST"):
            with patch("services.gr360_audit_service.write_logapp_entry") as writer:
                self.assertFalse(
                    audit.audit_table_write(
                        table_name="CL",
                        action="INSERT",
                        record_key={"CLSTAMP": "1"},
                        after_data={"NOME": "Guest"},
                    )
                )
                writer.assert_not_called()

    def test_unknown_context_disables_audit(self):
        config = {
            "GR360_AUDIT_ENABLED": "1",
            "GR360_AUDIT_TARGET": "client",
            "GR360_AUDIT_EXPECTED_DATABASE": "GR360_CORE",
            "GR360_AUDIT_SOURCE_DATABASE": "",
            "CURRENT_DB_TARGET": "",
        }

        self.assertFalse(audit.should_audit_table("CL", config))

    def test_wildcard_tables_cover_any_dynamic_form_table(self):
        config = {
            "GR360_AUDIT_ENABLED": "1",
            "GR360_AUDIT_TARGET": "client",
            "GR360_AUDIT_EXPECTED_DATABASE": "GR360_CORE",
            "GR360_AUDIT_SOURCE_DATABASE": "GR360_CORE",
            "GR360_AUDIT_TABLES": "*",
            "CURRENT_DB_TARGET": "client",
        }

        self.assertTrue(audit.should_audit_table("OPC", config))
        self.assertTrue(audit.should_audit_table("QUALQUER_TABELA_DO_DYNAMIC_FORM", config))

    def test_redacts_sensitive_fields_recursively(self):
        data = audit.redact_data(
            {
                "LOGIN": "admin",
                "PASSWORD": "enterprise",
                "PASSWORD_HASH": "abc",
                "nested": {"api_key": "secret", "nome": "Alice"},
                "rows": [{"reset_token": "token", "valor": 10}],
            }
        )

        self.assertEqual(data["LOGIN"], "admin")
        self.assertEqual(data["PASSWORD"], audit.REDACTED_VALUE)
        self.assertEqual(data["PASSWORD_HASH"], audit.REDACTED_VALUE)
        self.assertEqual(data["nested"]["api_key"], audit.REDACTED_VALUE)
        self.assertEqual(data["nested"]["nome"], "Alice")
        self.assertEqual(data["rows"][0]["reset_token"], audit.REDACTED_VALUE)

    def test_calculates_changed_data_only_for_changed_fields(self):
        changed = audit.calculate_changed_data(
            {"NOME": "Antes", "VALOR": 10, "PASSWORD": "old"},
            {"NOME": "Depois", "VALOR": 10, "PASSWORD": "new", "NOVO": "x"},
        )

        self.assertEqual(set(changed), {"NOME", "NOVO"})
        self.assertEqual(changed["NOME"], {"before": "Antes", "after": "Depois"})
        self.assertEqual(changed["NOVO"], {"before": None, "after": "x"})
        self.assertNotIn("PASSWORD", changed)

    def test_log_connection_failure_does_not_raise(self):
        config = {"GR360_AUDIT_LOG_CONN_STR": "SERVER=example;DATABASE=GR360_LOG;UID=u;PWD=p"}
        payload = {
            "TABLE_NAME": "CL",
            "ACTION": "INSERT",
            "DATABASE_NAME": "GR360_CORE",
            "SCHEMA_NAME": "dbo",
            "RECORD_KEY": "{}",
            "STATUS": "success",
        }

        def failing_factory(_conn_str):
            raise RuntimeError("offline")

        with patch.object(audit.logger, "exception") as log_exception:
            self.assertFalse(audit.write_logapp_entry(payload, config=config, connection_factory=failing_factory))
            log_exception.assert_called_once()


if __name__ == "__main__":
    unittest.main()
