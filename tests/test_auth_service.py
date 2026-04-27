import unittest

from services import auth_service


class _FakeScalarResult:
    def __init__(self, values):
        self._values = list(values)

    def scalars(self):
        return self

    def all(self):
        return list(self._values)


class _FakeSession:
    def __init__(self, columns):
        self._columns = list(columns)
        self._engine = object()

    def get_bind(self):
        return self._engine

    def execute(self, statement, params):
        self.last_statement = statement
        self.last_params = params
        return _FakeScalarResult(self._columns)


class AuthServiceTests(unittest.TestCase):
    def setUp(self):
        auth_service.clear_table_columns_cache()

    def tearDown(self):
        auth_service.clear_table_columns_cache()

    def test_selectable_user_columns_cache_isolated_by_bind(self):
        client_session = _FakeSession(auth_service.BASE_USER_COLUMNS + ["LANGUAGE"])
        prod_session = _FakeSession(auth_service.BASE_USER_COLUMNS)

        client_selectable = auth_service._selectable_user_columns(client_session)
        prod_selectable = auth_service._selectable_user_columns(prod_session)

        self.assertIn("LANGUAGE", client_selectable)
        self.assertNotIn("LANGUAGE", prod_selectable)

    def test_clear_table_columns_cache_removes_all_bind_variants_for_table(self):
        client_session = _FakeSession(auth_service.BASE_USER_COLUMNS + ["LANGUAGE"])
        prod_session = _FakeSession(auth_service.BASE_USER_COLUMNS)

        auth_service.get_table_columns(client_session, "US")
        auth_service.get_table_columns(prod_session, "US")
        self.assertTrue(auth_service._TABLE_COLUMNS_CACHE)

        auth_service.clear_table_columns_cache("US")

        self.assertEqual(auth_service._TABLE_COLUMNS_CACHE, {})


if __name__ == "__main__":
    unittest.main()
