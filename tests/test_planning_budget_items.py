import importlib.util
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch


def load_database_module():
    config = ModuleType("config")
    config.MSSQLConfig = SimpleNamespace
    config.get_mssql_config = lambda: SimpleNamespace()
    spec = importlib.util.spec_from_file_location(
        "planning_budget_items_database",
        Path(__file__).resolve().parents[1] / "planeamento" / "database.py",
    )
    module = importlib.util.module_from_spec(spec)
    with patch.dict("sys.modules", {"config": config}):
        spec.loader.exec_module(module)
    return module


class Cursor:
    def __init__(self, origin, master=(), source=(), error=None):
        self.origin, self.master, self.source, self.error = origin, master, source, error
        self.calls = []
        self.description = [(name,) for name in ("OBRAM", "LITEM", "DGERAL", "QTT", "UNIDADE", "QTT2", "BISTAMP")]

    def execute(self, query, params):
        self.calls.append((query, params))
        if "WITH BASE" in query and self.error:
            raise self.error

    def fetchall(self):
        return self.source if "WITH BASE" in self.calls[-1][0] else self.master

    def fetchone(self):
        return (self.origin,) if self.origin is not None else None


class PlanningBudgetItemsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_database_module()

    def database(self, cursor):
        database = self.module.Database(SimpleNamespace())

        @contextmanager
        def connect():
            yield SimpleNamespace(cursor=lambda: cursor)

        database.connect = connect
        return database

    def test_central_items_take_precedence_without_reading_source(self):
        cursor = Cursor("INTERSOL-ALSACE", master=[("IS2344", 1, "Work", Decimal("126"), "", 0, " A ")])
        result = self.database(cursor).fetch_project_budget_items("hs2344")
        self.assertEqual(result[0]["qtt"], 126.0)
        self.assertEqual(result[0]["bistamp"], "A")
        self.assertEqual(len(cursor.calls), 1)

    def test_missing_intersol_items_use_exact_entity_process(self):
        for origin in ("INTERSOL-ALSACE", "INTERSOL-LORRAINE", "INTERSOL-CHAMPAGNE"):
            with self.subTest(origin=origin):
                cursor = Cursor(origin, source=[("IS2412", 1, "Bât A", 289, "", 0, "BI1")])
                result = self.database(cursor).fetch_project_budget_items(" HS2412 ")
                self.assertEqual(result[0]["dgeral"], "Bât A")
                query, params = cursor.calls[-1]
                self.assertIn("FROM INTERSOL.dbo.BI", query)
                self.assertEqual(params, ("IS2412",))

    def test_hsols_france_items_do_not_require_intersol_origin(self):
        cursor = Cursor("HSOLS FRANCE", source=[("FR2357", 1, "Dallage", 55, "", 0, "BI2")])
        result = self.database(cursor).fetch_project_budget_items("HS2357")
        self.assertEqual(result[0]["qtt"], 55.0)
        query, params = cursor.calls[-1]
        self.assertIn("FROM HSOLS_FR.dbo.BI", query)
        self.assertNotIn("INTERSOL.dbo", query)
        self.assertEqual(params, ("FR2357",))

    def test_unknown_or_missing_origin_never_guesses_a_source(self):
        for origin in (None, "", "HSOLS PORTUGAL", "HSOLS FRANCE; DROP TABLE BI"):
            with self.subTest(origin=origin):
                cursor = Cursor(origin)
                self.assertEqual(self.database(cursor).fetch_project_budget_items("HS2357"), [])
                self.assertEqual(len(cursor.calls), 2)

    def test_source_failure_is_not_reported_as_no_work(self):
        cursor = Cursor("HSOLS FRANCE", error=RuntimeError("source offline"))
        with self.assertRaisesRegex(RuntimeError, "source offline"):
            self.database(cursor).fetch_project_budget_items("HS2357")

    def test_invalid_project_does_not_open_a_connection(self):
        cursor = Cursor("HSOLS FRANCE")
        for project in ("", "HS"):
            self.assertEqual(self.database(cursor).fetch_project_budget_items(project), [])
        self.assertEqual(cursor.calls, [])


if __name__ == "__main__":
    unittest.main()
