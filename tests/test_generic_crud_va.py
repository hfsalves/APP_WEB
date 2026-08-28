import unittest

from sqlalchemy import Column, Date, DateTime, MetaData, String, Table

from app import app  # noqa: F401 - initializes the registered blueprints first
from blueprints.generic_crud import _normalise_write_values


class GenericCrudVaTests(unittest.TestCase):
    def setUp(self):
        metadata = MetaData()
        self.table = Table(
            'VA',
            metadata,
            Column('VASTAMP', String(25), primary_key=True),
            Column('DATAMAT', DateTime, nullable=False),
            Column('DTMATRICULA', Date, nullable=True),
        )

    def test_missing_datamat_uses_legacy_empty_date(self):
        values = _normalise_write_values(self.table, 'VA', {})

        self.assertEqual(values['DATAMAT'], '1900-01-01')

    def test_registration_date_is_used_for_missing_datamat(self):
        values = _normalise_write_values(
            self.table,
            'VA',
            {'DTMATRICULA': '2026-01-06'},
        )

        self.assertEqual(values['DATAMAT'], '2026-01-06')

    def test_explicit_datamat_is_preserved(self):
        values = _normalise_write_values(
            self.table,
            'VA',
            {'DATAMAT': '2025-12-31', 'DTMATRICULA': '2026-01-06'},
        )

        self.assertEqual(values['DATAMAT'], '2025-12-31')


if __name__ == '__main__':
    unittest.main()
