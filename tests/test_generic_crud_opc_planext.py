import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app import app  # noqa: F401 - initializes the registered blueprints first
from blueprints.generic_crud import _sync_opc_external_planning_to_master


class GenericCrudOpcPlanextTests(unittest.TestCase):
    @staticmethod
    def _environment(cursor):
        connection = MagicMock()
        connection.cursor.return_value = cursor
        context = MagicMock()
        context.__enter__.return_value = connection
        context.__exit__.return_value = False
        database = MagicMock()
        database.connect.return_value = context
        return SimpleNamespace(database=database), connection

    def test_update_does_not_depend_on_trigger_rowcount(self):
        cursor = MagicMock()
        cursor.execute.return_value = cursor
        cursor.fetchone.side_effect = [(0,), (1,)]
        cursor.rowcount = -1
        environment, connection = self._environment(cursor)

        with patch(
            'modules.gr_planning.service.get_legacy_environment',
            return_value=environment,
        ):
            _sync_opc_external_planning_to_master('OPC-STAMP', True)

        self.assertEqual(cursor.execute.call_count, 3)
        connection.commit.assert_called_once_with()

    def test_missing_source_record_keeps_not_found_error(self):
        cursor = MagicMock()
        cursor.execute.return_value = cursor
        cursor.fetchone.return_value = None
        environment, connection = self._environment(cursor)

        with patch(
            'modules.gr_planning.service.get_legacy_environment',
            return_value=environment,
        ):
            with self.assertRaisesRegex(ValueError, 'Obra não encontrada'):
                _sync_opc_external_planning_to_master('MISSING-STAMP', True)

        self.assertEqual(cursor.execute.call_count, 1)
        connection.commit.assert_not_called()


if __name__ == '__main__':
    unittest.main()
