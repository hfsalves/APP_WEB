import unittest
from datetime import date

from app import (
    INTERSOL_DETAIL_PREPAID,
    ROLE_CHEF,
    ROLE_POLISSEUR,
    ROLE_AIDE,
    _apply_intersol_role_hints,
    _build_intersol_tasks,
    _compute_intersol_panier_repas,
    _infer_intervention_type,
    _intersol_detail_paid_value,
    _is_intemperie_row,
    _planning_group_visible_for_selected_markets,
    _project_visible_for_selected_markets,
    _resolve_intersol_period,
    _serialize_intersol_detail_rows,
    _serialize_intersol_regularization_rows,
)


class IntersolClassificationTests(unittest.TestCase):
    def test_litem_codes_drive_intervention_type(self):
        self.assertEqual(_infer_intervention_type({"litem": "999", "acabamento": "lisse quartz"}), "prepa")
        self.assertEqual(_infer_intervention_type({"litem": "997", "acabamento": "lisse quartz"}), "reparation")
        self.assertEqual(_infer_intervention_type({"litem": "980", "acabamento": "lisse quartz"}), "intemperie")
        self.assertEqual(_infer_intervention_type({"litem": "994", "acabamento": "lisse quartz"}), "lavage")
        self.assertEqual(_infer_intervention_type({"litem": "995", "acabamento": "lisse quartz"}), "other")

    def test_item_980_forces_intemperie_even_when_finish_is_wrong(self):
        self.assertTrue(_is_intemperie_row({"litem": "980", "acabamento": "lisse quartz"}))

    def test_item_995_is_not_intemperie(self):
        self.assertFalse(_is_intemperie_row({"litem": "995", "acabamento": "lisse quartz"}))

    def test_chef_hint_overrides_existing_role(self):
        roles_by_employee = {"100": ROLE_POLISSEUR}
        _apply_intersol_role_hints(roles_by_employee, {"100": ROLE_CHEF, "200": ROLE_POLISSEUR})
        self.assertEqual(roles_by_employee["100"], ROLE_CHEF)
        self.assertEqual(roles_by_employee["200"], ROLE_POLISSEUR)

    def test_resolve_intersol_period_uses_22_to_21_window(self):
        month_value, selected_month_start, period_start, period_end, month_label, period_label = _resolve_intersol_period(
            "2026-03",
            today=date(2026, 3, 20),
        )
        self.assertEqual(month_value, "2026-03")
        self.assertEqual(selected_month_start, date(2026, 3, 1))
        self.assertEqual(period_start, date(2026, 2, 22))
        self.assertEqual(period_end, date(2026, 3, 21))
        self.assertEqual(month_label, "03/2026")
        self.assertEqual(period_label, "Período: 22/02/2026 a 21/03/2026")

    def test_detail_paid_value_applies_only_to_previous_month_rows(self):
        selected_month_start = date(2026, 3, 1)
        self.assertEqual(_intersol_detail_paid_value(date(2026, 2, 23), selected_month_start), INTERSOL_DETAIL_PREPAID)
        self.assertEqual(_intersol_detail_paid_value(date(2026, 2, 27), selected_month_start), INTERSOL_DETAIL_PREPAID)
        self.assertEqual(_intersol_detail_paid_value(date(2026, 3, 1), selected_month_start), 0)
        self.assertEqual(_intersol_detail_paid_value(date(2026, 3, 21), selected_month_start), 0)
        self.assertEqual(_intersol_detail_paid_value(date(2026, 3, 23), selected_month_start), 0)
        self.assertEqual(_intersol_detail_paid_value(date(2026, 2, 22), date(2026, 2, 1)), 0)

    def test_detail_paid_value_is_zero_on_weekends(self):
        selected_month_start = date(2026, 3, 1)
        self.assertEqual(_intersol_detail_paid_value(date(2026, 2, 22), selected_month_start), 0)
        self.assertEqual(_intersol_detail_paid_value(date(2026, 3, 22), selected_month_start), 0)

    def test_detail_paid_value_uses_aide_daily_rate(self):
        selected_month_start = date(2026, 3, 1)
        self.assertEqual(_intersol_detail_paid_value(date(2026, 2, 23), selected_month_start, ROLE_AIDE), 130)

    def test_detail_rows_add_business_day_estimates_after_day_21(self):
        rows, paid_total, display_total_sum = _serialize_intersol_detail_rows([], date(2026, 3, 1))
        estimate_rows = [row for row in rows if row.get("is_estimate")]
        not_worked_rows = [row for row in rows if row.get("chantier") == "Não trabalhou"]
        self.assertEqual(len(estimate_rows), 7)
        self.assertEqual(len(not_worked_rows), 5)
        self.assertEqual(estimate_rows[0]["date"], "2026-03-23")
        self.assertEqual(estimate_rows[-1]["date"], "2026-03-31")
        self.assertTrue(all(row["chantier"] == "Estimativa" for row in estimate_rows))
        self.assertTrue(all(row["paid_value"] == 0.0 for row in estimate_rows))
        self.assertTrue(all(row["display_total"] == 150.0 for row in estimate_rows))
        self.assertTrue(all(row["is_pending_period"] for row in estimate_rows))
        self.assertTrue(all(row["paid_value"] == 150.0 for row in not_worked_rows))
        self.assertTrue(all(row["display_total"] == -150.0 for row in not_worked_rows))
        self.assertEqual(paid_total, INTERSOL_DETAIL_PREPAID * 5)
        self.assertEqual(display_total_sum, INTERSOL_DETAIL_PREPAID * 2)

    def test_detail_rows_skip_not_worked_and_estimate_days_inside_absence_periods(self):
        rows, paid_total, display_total_sum = _serialize_intersol_detail_rows(
            [],
            date(2026, 3, 1),
            [(date(2026, 2, 23), date(2026, 2, 24)), (date(2026, 3, 23), date(2026, 3, 24))],
        )
        row_dates = {row["date"] for row in rows}
        self.assertNotIn("2026-02-23", row_dates)
        self.assertNotIn("2026-02-24", row_dates)
        self.assertNotIn("2026-03-23", row_dates)
        self.assertNotIn("2026-03-24", row_dates)
        self.assertEqual(paid_total, INTERSOL_DETAIL_PREPAID * 3)
        self.assertEqual(display_total_sum, INTERSOL_DETAIL_PREPAID * 2)

    def test_panier_repas_counts_month_days_with_estimates_after_day_21(self):
        rows, _, _ = _serialize_intersol_detail_rows([], date(2026, 3, 1))
        self.assertEqual(_compute_intersol_panier_repas(rows, date(2026, 3, 1)), 7)

    def test_panier_repas_ignores_intemperie_and_previous_month_rows(self):
        detail_rows = [
            {"date": "2026-02-24", "finish_type": "", "is_not_worked": True, "is_estimate": False},
            {"date": "2026-03-02", "finish_type": "RP.LQUARTZO", "is_not_worked": False, "is_estimate": False},
            {"date": "2026-03-03", "finish_type": "INTEMPERIE", "is_not_worked": False, "is_estimate": False},
            {"date": "2026-03-23", "finish_type": "", "is_not_worked": False, "is_estimate": True},
            {"date": "2026-03-24", "finish_type": "", "is_not_worked": False, "is_estimate": True},
            {"date": "03/2026", "finish_type": "Mutuelle", "is_regularization": True},
        ]
        self.assertEqual(_compute_intersol_panier_repas(detail_rows, date(2026, 3, 1)), 3)

    def test_regularization_rows_are_serialized_for_selected_month(self):
        rows, total = _serialize_intersol_regularization_rows(
            [{"obs": "Mutuelle février", "valor": "-6.50"}],
            date(2026, 3, 1),
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["date"], "03/2026")
        self.assertEqual(rows[0]["chantier"], "Regularização")
        self.assertEqual(rows[0]["finish_type"], "Mutuelle février")
        self.assertEqual(rows[0]["display_total"], -6.5)
        self.assertTrue(rows[0]["is_regularization"])
        self.assertEqual(total, -6.5)

    def test_build_intersol_tasks_aggregates_chantier_total_across_am_stamps(self):
        rows = [
            {
                "u_amstamp": "AM1",
                "fref": "IS ALSACE 01",
                "fref_name": "Equipe",
                "processo": "HS1984",
                "data": date(2026, 3, 10),
                "no": "100",
                "nome": "Teste",
                "acabamento": "RP.DESACTIVE",
                "aml_qtt": 76.3,
                "am_qtt": 228.9,
                "aml_m2serragem": 0,
                "aml_kgferro": 0,
                "litem": "1",
            },
            {
                "u_amstamp": "AM2",
                "fref": "IS ALSACE 02",
                "fref_name": "Equipe 2",
                "processo": "HS1984",
                "data": date(2026, 3, 10),
                "no": "101",
                "nome": "Outro",
                "acabamento": "RP.DESACTIVE",
                "aml_qtt": 49.7,
                "am_qtt": 149.1,
                "aml_m2serragem": 0,
                "aml_kgferro": 0,
                "litem": "1",
            },
        ]
        tasks, role_hints = _build_intersol_tasks(rows, ["IS ALSACE 01"])
        self.assertFalse(role_hints)
        self.assertEqual(len(tasks), 1)
        self.assertAlmostEqual(float(tasks[0].sqm_total_chantier), 378.0, places=2)

    def test_planext_project_visibility_excludes_maroc_only_selection(self):
        self.assertTrue(_project_visible_for_selected_markets("FR", True, ["IA"]))
        self.assertTrue(_project_visible_for_selected_markets("FR", True, ["FR"]))
        self.assertFalse(_project_visible_for_selected_markets("FR", True, ["MA"]))
        self.assertFalse(_project_visible_for_selected_markets("FR", False, ["IA"]))

    def test_planning_group_visibility_follows_selected_market(self):
        self.assertTrue(_planning_group_visible_for_selected_markets("INTERSOL", ["IA"]))
        self.assertTrue(_planning_group_visible_for_selected_markets("SOUS-TRAITANTS", ["IA"]))
        self.assertFalse(_planning_group_visible_for_selected_markets("FRANCE", ["IA"]))
        self.assertTrue(_planning_group_visible_for_selected_markets("FRANCE", ["FR"]))


if __name__ == "__main__":
    unittest.main()
