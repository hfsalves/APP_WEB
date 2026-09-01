from decimal import Decimal
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from services.phc_approval_limits_service import (
    PhcApprovalLimitsError,
    _parse_limit,
    _user_row,
    create_approval_limit,
    delete_approval_limit,
)


class PhcApprovalLimitsServiceTests(unittest.TestCase):
    def test_limit_accepts_comma_and_rounds_to_two_decimals(self):
        self.assertEqual(_parse_limit("1250,555"), Decimal("1250.56"))

    def test_limit_rejects_negative_values(self):
        with self.assertRaisesRegex(PhcApprovalLimitsError, "não pode ser negativo"):
            _parse_limit("-0.01")

    def test_user_is_selected_from_gr360_core(self):
        with patch(
            "services.phc_approval_limits_service._app_users",
            return_value=[
                {
                    "usercode": "doussama",
                    "username": "Diraa Oussama",
                    "inactive": False,
                }
            ],
        ):
            result = _user_row(MagicMock(), "DOUSSAMA")

        self.assertEqual(
            result,
            {"usercode": "doussama", "username": "Diraa Oussama"},
        )

    def test_create_uses_phc_user_and_writes_audit_fields(self):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        cursor = connection.cursor.return_value
        cursor.execute.return_value.fetchone.return_value = None
        created = {
            "stamp": "NEW-STAMP",
            "usercode": "acruz",
            "username": "António Cruz",
            "plafond": "1000.00",
        }

        with (
            patch("services.phc_approval_limits_service._ensure_context"),
            patch("services.phc_approval_limits_service._connection", return_value=connection),
            patch(
                "services.phc_approval_limits_service._user_row",
                return_value={"usercode": "acruz", "username": "António Cruz"},
            ),
            patch("services.phc_approval_limits_service._actor_initials", return_value="AC"),
            patch("services.phc_approval_limits_service._stamp", return_value="NEW-STAMP"),
            patch("services.phc_approval_limits_service.get_approval_limit", return_value=created),
        ):
            result = create_approval_limit(
                {"usercode": "acruz", "plafond": "1000"},
                SimpleNamespace(LOGIN="acruz"),
            )

        insert_call = cursor.execute.call_args_list[-1]
        self.assertIn("INSERT INTO dbo.U_APROPLAF", insert_call.args[0])
        self.assertEqual(insert_call.args[1], "NEW-STAMP")
        self.assertEqual(insert_call.args[2], "acruz")
        self.assertEqual(insert_call.args[3], "António Cruz")
        self.assertEqual(insert_call.args[4], Decimal("1000.00"))
        connection.commit.assert_called_once_with()
        self.assertEqual(result, created)

    def test_delete_requires_one_existing_row(self):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        cursor = connection.cursor.return_value
        cursor.rowcount = 1

        with (
            patch("services.phc_approval_limits_service._ensure_context"),
            patch("services.phc_approval_limits_service._connection", return_value=connection),
        ):
            delete_approval_limit("STAMP-1")

        self.assertIn("DELETE FROM dbo.U_APROPLAF", cursor.execute.call_args.args[0])
        connection.commit.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
