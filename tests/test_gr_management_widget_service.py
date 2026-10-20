from datetime import date, datetime
from decimal import Decimal
import unittest
from unittest.mock import MagicMock, patch

from services.gr_management_widget_service import execute_read_query


class GrManagementWidgetServiceTest(unittest.TestCase):
    def test_execute_read_query_uses_non_blocking_bounded_session(self):
        cursor = MagicMock()
        cursor.description = [("AMOUNT",), ("DAY",), ("CREATED",)]
        cursor.fetchall.return_value = [
            (Decimal("12.50"), date(2026, 10, 19), datetime(2026, 10, 19, 8, 30)),
        ]
        connection = MagicMock()
        connection.cursor.return_value = cursor
        context = MagicMock()
        context.__enter__.return_value = connection

        with patch("services.gr_management_widget_service.pyodbc.connect", return_value=context) as connect:
            rows = execute_read_query("dsn", "SELECT ?", [7])

        connect.assert_called_once_with("dsn", timeout=10, autocommit=True)
        self.assertEqual(connection.timeout, 25)
        self.assertEqual(
            cursor.execute.call_args_list[0].args,
            ("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED",),
        )
        self.assertEqual(cursor.execute.call_args_list[1].args, ("SET LOCK_TIMEOUT 10000",))
        self.assertEqual(cursor.execute.call_args_list[2].args, ("SELECT ?", 7))
        self.assertEqual(
            rows,
            [{"AMOUNT": 12.5, "DAY": "2026-10-19", "CREATED": "2026-10-19"}],
        )


if __name__ == "__main__":
    unittest.main()
