import unittest

from app import app  # noqa: F401 - initializes the registered blueprints first
from blueprints.generic_crud import _json_safe_record


class GenericCrudJsonTests(unittest.TestCase):
    def test_binary_values_are_serialized_as_hex(self):
        record = {
            'TKSTAMP': 'TK-1',
            'TK_VERSION': b'\x00\x00\x00\x00\x00\x00\x00\x05',
        }

        serialized = _json_safe_record(record)

        self.assertEqual(serialized['TKSTAMP'], 'TK-1')
        self.assertEqual(serialized['TK_VERSION'], '0000000000000005')

    def test_bytearray_and_memoryview_are_serialized_as_hex(self):
        serialized = _json_safe_record({
            'BINARY': bytearray(b'\x01\x02'),
            'VERSION': memoryview(b'\x03\x04'),
        })

        self.assertEqual(serialized, {
            'BINARY': '0102',
            'VERSION': '0304',
        })


if __name__ == '__main__':
    unittest.main()
