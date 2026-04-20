from datetime import date, timedelta
from decimal import Decimal
import unittest

from intersol_monthly import (
    ROLE_AIDE,
    ROLE_CHEF,
    ROLE_POLISSEUR,
    ROLE_SCIEUR,
    Task,
    compute_monthly_sheet,
)


class IntersolMonthlyTests(unittest.TestCase):
    def _run_single_employee(self, tasks, roles, month_start, month_end, holidays=None):
        summary, _ = compute_monthly_sheet(
            tasks,
            month_start=month_start,
            month_end=month_end,
            roles_by_employee=roles,
            depot_manager_numbers=set(),
            holidays=holidays or [],
        )
        self.assertTrue(summary, "expected at least one summary row")
        return summary[0]

    def test_polisseur_finitions_plus_scie(self):
        month_start = date(2024, 1, 1)
        month_end = date(2024, 1, 31)
        tasks = [
            Task(
                date=date(2024, 1, 10),
                team_code="T1",
                team_name="Team 1",
                employee_number="1",
                employee_name="Polisseur",
                chantier="CH1",
                finish_type="lisse",
                sqm=Decimal("170"),
                sqm_total_chantier=Decimal("170"),
                sqm_scie=Decimal("60"),
                kg_steel=Decimal("0"),
                intervention_type="coulage",
            )
        ]
        res = self._run_single_employee(tasks, {"1": ROLE_POLISSEUR}, month_start, month_end)
        self.assertAlmostEqual(res.finitions_pay, 255.00, places=2)
        self.assertAlmostEqual(res.scie_pay, 10.80, places=2)
        self.assertAlmostEqual(res.total, 265.80, places=2)

    def test_aide_forfait_plus_scie(self):
        month_start = date(2024, 1, 1)
        month_end = date(2024, 1, 31)
        tasks = [
            Task(
                date=date(2024, 1, 11),
                team_code="T1",
                team_name="Team 1",
                employee_number="2",
                employee_name="Aide",
                chantier="CH2",
                finish_type="prepa",
                sqm=Decimal("0"),
                sqm_total_chantier=Decimal("0"),
                sqm_scie=Decimal("60"),
                kg_steel=Decimal("0"),
                intervention_type="coulage",
            )
        ]
        res = self._run_single_employee(tasks, {"2": ROLE_AIDE}, month_start, month_end)
        self.assertAlmostEqual(res.finitions_pay, 130.00, places=2)
        self.assertAlmostEqual(res.scie_pay, 10.80, places=2)
        self.assertAlmostEqual(res.total, 140.80, places=2)

    def test_scieur_threshold(self):
        month_start = date(2024, 1, 1)
        month_end = date(2024, 1, 31)
        tasks = [
            Task(
                date=date(2024, 1, 12),
                team_code="T2",
                team_name="Team 2",
                employee_number="3",
                employee_name="Scieur",
                chantier="CH3",
                finish_type="scie",
                sqm=Decimal("0"),
                sqm_total_chantier=Decimal("0"),
                sqm_scie=Decimal("900"),
                kg_steel=Decimal("0"),
                intervention_type="scie",
            )
        ]
        res = self._run_single_employee(tasks, {"3": ROLE_SCIEUR}, month_start, month_end)
        self.assertAlmostEqual(res.finitions_pay, 0.00, places=2)
        self.assertAlmostEqual(res.scie_pay, 162.00, places=2)
        self.assertAlmostEqual(res.total, 162.00, places=2)

    def test_treillis_threshold(self):
        month_start = date(2024, 1, 1)
        month_end = date(2024, 1, 31)
        tasks = [
            Task(
                date=date(2024, 1, 13),
                team_code="T3",
                team_name="Team 3",
                employee_number="4",
                employee_name="Steel",
                chantier="CH4",
                finish_type="prepa",
                sqm=Decimal("0"),
                sqm_total_chantier=Decimal("0"),
                sqm_scie=Decimal("0"),
                kg_steel=Decimal("3500"),
                intervention_type="coulage",
            )
        ]
        res = self._run_single_employee(tasks, {"4": ROLE_POLISSEUR}, month_start, month_end)
        self.assertAlmostEqual(res.kg_pay, 262.50, places=2)
        self.assertAlmostEqual(res.total, 412.50, places=2)

    def test_treillis_paid_below_threshold_when_coulage_present(self):
        month_start = date(2024, 2, 1)
        month_end = date(2024, 2, 29)
        tasks = [
            Task(
                date=date(2024, 2, 2),
                team_code="T5",
                team_name="Team 5",
                employee_number="6",
                employee_name="Treillis",
                chantier="CH6",
                finish_type="prepa",
                sqm=Decimal("0"),
                sqm_total_chantier=Decimal("0"),
                sqm_scie=Decimal("0"),
                kg_steel=Decimal("811.72"),
                intervention_type="coulage",
            )
        ]
        res = self._run_single_employee(tasks, {"6": ROLE_POLISSEUR}, month_start, month_end)
        self.assertAlmostEqual(res.finitions_pay, 150.00, places=2)
        self.assertAlmostEqual(res.kg_pay, 60.88, places=2)
        self.assertAlmostEqual(res.total, 210.88, places=2)

    def test_steel_only_day_without_coulage_does_not_add_forfait(self):
        month_start = date(2024, 2, 1)
        month_end = date(2024, 2, 29)
        tasks = [
            Task(
                date=date(2024, 2, 3),
                team_code="T5A",
                team_name="Team 5A",
                employee_number="6A",
                employee_name="Treillis only",
                chantier="CH6A",
                finish_type="prepa",
                sqm=Decimal("0"),
                sqm_total_chantier=Decimal("0"),
                sqm_scie=Decimal("0"),
                kg_steel=Decimal("5653.70"),
                intervention_type="prepa",
            )
        ]
        res = self._run_single_employee(tasks, {"6A": ROLE_POLISSEUR}, month_start, month_end)
        self.assertAlmostEqual(res.finitions_pay, 0.00, places=2)
        self.assertAlmostEqual(res.kg_pay, 424.03, places=2)
        self.assertAlmostEqual(res.total, 424.03, places=2)

    def test_prime_multiple_requires_two_distinct_coulage_chantiers(self):
        month_start = date(2024, 2, 1)
        month_end = date(2024, 2, 29)
        tasks = [
            Task(
                date=date(2024, 2, 5),
                team_code="T6",
                team_name="Team 6",
                employee_number="7",
                employee_name="Distinct",
                chantier="CH7",
                finish_type="desactive",
                sqm=Decimal("0"),
                sqm_total_chantier=Decimal("220"),
                sqm_scie=Decimal("0"),
                kg_steel=Decimal("0"),
                intervention_type="coulage",
            ),
            Task(
                date=date(2024, 2, 5),
                team_code="T6",
                team_name="Team 6",
                employee_number="7",
                employee_name="Distinct",
                chantier="CH7",
                finish_type="balaye",
                sqm=Decimal("104.80"),
                sqm_total_chantier=Decimal("220"),
                sqm_scie=Decimal("0"),
                kg_steel=Decimal("0"),
                intervention_type="coulage",
            ),
        ]
        res = self._run_single_employee(tasks, {"7": ROLE_POLISSEUR}, month_start, month_end)
        self.assertAlmostEqual(res.finitions_pay, 160.00, places=2)
        self.assertAlmostEqual(res.prime_multiple, 0.00, places=2)
        self.assertAlmostEqual(res.total, 160.00, places=2)

    def test_prime_multiple_uses_best_finish_once_per_day(self):
        month_start = date(2024, 2, 1)
        month_end = date(2024, 2, 29)
        tasks = [
            Task(
                date=date(2024, 2, 6),
                team_code="T7",
                team_name="Team 7",
                employee_number="8",
                employee_name="Best finish",
                chantier="CH8A",
                finish_type="desactive",
                sqm=Decimal("0"),
                sqm_total_chantier=Decimal("220"),
                sqm_scie=Decimal("0"),
                kg_steel=Decimal("0"),
                intervention_type="coulage",
            ),
            Task(
                date=date(2024, 2, 6),
                team_code="T7",
                team_name="Team 7",
                employee_number="8",
                employee_name="Best finish",
                chantier="CH8B",
                finish_type="desactive",
                sqm=Decimal("0"),
                sqm_total_chantier=Decimal("220"),
                sqm_scie=Decimal("0"),
                kg_steel=Decimal("0"),
                intervention_type="coulage",
            ),
        ]
        res = self._run_single_employee(tasks, {"8": ROLE_POLISSEUR}, month_start, month_end)
        self.assertAlmostEqual(res.finitions_pay, 160.00, places=2)
        self.assertAlmostEqual(res.prime_multiple, 40.00, places=2)
        self.assertAlmostEqual(res.total, 200.00, places=2)

    def test_lavage_does_not_create_second_coulage_prime(self):
        month_start = date(2024, 2, 1)
        month_end = date(2024, 2, 29)
        tasks = [
            Task(
                date=date(2024, 2, 6),
                team_code="T7A",
                team_name="Team 7A",
                employee_number="8AA",
                employee_name="Lavage",
                chantier="CH8A",
                finish_type="desactive",
                sqm=Decimal("0"),
                sqm_total_chantier=Decimal("378"),
                sqm_scie=Decimal("0"),
                kg_steel=Decimal("0"),
                intervention_type="coulage",
            ),
            Task(
                date=date(2024, 2, 6),
                team_code="T7A",
                team_name="Team 7A",
                employee_number="8AA",
                employee_name="Lavage",
                chantier="CH8B",
                finish_type="lavage",
                sqm=Decimal("0"),
                sqm_total_chantier=Decimal("0"),
                sqm_scie=Decimal("0"),
                kg_steel=Decimal("0"),
                intervention_type="lavage",
            ),
        ]
        res = self._run_single_employee(tasks, {"8AA": ROLE_POLISSEUR}, month_start, month_end)
        self.assertAlmostEqual(res.finitions_pay, 190.00, places=2)
        self.assertAlmostEqual(res.prime_multiple, 0.00, places=2)
        self.assertAlmostEqual(res.total, 190.00, places=2)

    def test_desactive_finish_code_uses_pdf_bracket_table(self):
        month_start = date(2024, 2, 1)
        month_end = date(2024, 2, 29)
        tasks = [
            Task(
                date=date(2024, 2, 7),
                team_code="T7",
                team_name="Team 7",
                employee_number="8A",
                employee_name="Desactive code",
                chantier="CH8C",
                finish_type="RP.DESACTIVE",
                sqm=Decimal("56"),
                sqm_total_chantier=Decimal("220"),
                sqm_scie=Decimal("0"),
                kg_steel=Decimal("0"),
                intervention_type="coulage",
            )
        ]
        res = self._run_single_employee(tasks, {"8A": ROLE_POLISSEUR}, month_start, month_end)
        self.assertAlmostEqual(res.finitions_pay, 160.00, places=2)
        self.assertAlmostEqual(res.total, 160.00, places=2)

    def test_lquartzo_finish_code_uses_150_per_sqm_rule(self):
        month_start = date(2024, 2, 1)
        month_end = date(2024, 2, 29)
        tasks = [
            Task(
                date=date(2024, 2, 8),
                team_code="T7",
                team_name="Team 7",
                employee_number="8B",
                employee_name="Quartz code",
                chantier="CH8D",
                finish_type="RP.LQUARTZO",
                sqm=Decimal("210.44"),
                sqm_total_chantier=Decimal("210.44"),
                sqm_scie=Decimal("0"),
                kg_steel=Decimal("0"),
                intervention_type="coulage",
            )
        ]
        res = self._run_single_employee(tasks, {"8B": ROLE_POLISSEUR}, month_start, month_end)
        self.assertAlmostEqual(res.finitions_pay, 315.66, places=2)
        self.assertAlmostEqual(res.total, 315.66, places=2)

    def test_effort_prime_only_hits_total_when_validated(self):
        month_start = date(2024, 2, 1)
        month_end = date(2024, 2, 29)
        tasks = [
            Task(
                date=date(2024, 2, 9),
                team_code="T8",
                team_name="Team 8",
                employee_number="9",
                employee_name="Prime effort",
                chantier="CH9A",
                finish_type="prepa",
                sqm=Decimal("0"),
                sqm_total_chantier=Decimal("0"),
                sqm_scie=Decimal("0"),
                kg_steel=Decimal("0"),
                intervention_type="coulage",
                effort_prime=Decimal("20"),
                effort_prime_validated=True,
            ),
            Task(
                date=date(2024, 2, 10),
                team_code="T8",
                team_name="Team 8",
                employee_number="9",
                employee_name="Prime effort",
                chantier="CH9B",
                finish_type="prepa",
                sqm=Decimal("0"),
                sqm_total_chantier=Decimal("0"),
                sqm_scie=Decimal("0"),
                kg_steel=Decimal("0"),
                intervention_type="coulage",
                effort_prime=Decimal("15"),
                effort_prime_validated=False,
            ),
        ]
        res = self._run_single_employee(tasks, {"9": ROLE_POLISSEUR}, month_start, month_end)
        self.assertAlmostEqual(res.finitions_pay, 300.00, places=2)
        self.assertAlmostEqual(res.prime_effort, 35.00, places=2)
        self.assertAlmostEqual(res.prime_effort_validated, 20.00, places=2)
        self.assertAlmostEqual(res.prime_effort_pending, 15.00, places=2)
        self.assertAlmostEqual(res.total, 320.00, places=2)

    def test_non_scieur_scie_only_adds_no_supplement_on_preparation_day(self):
        month_start = date(2024, 2, 1)
        month_end = date(2024, 2, 29)
        tasks = [
            Task(
                date=date(2024, 2, 10),
                team_code="T8A",
                team_name="Team 8A",
                employee_number="9A",
                employee_name="Prep plus scie",
                chantier="CH9C",
                finish_type="prepa",
                sqm=Decimal("0"),
                sqm_total_chantier=Decimal("0"),
                sqm_scie=Decimal("80"),
                kg_steel=Decimal("0"),
                intervention_type="prepa",
            )
        ]
        res = self._run_single_employee(tasks, {"9A": ROLE_POLISSEUR}, month_start, month_end)
        self.assertAlmostEqual(res.finitions_pay, 150.00, places=2)
        self.assertAlmostEqual(res.scie_pay, 0.00, places=2)
        self.assertAlmostEqual(res.total, 150.00, places=2)

    def test_lquartzoreg_combined_label_still_uses_150_per_sqm_rule(self):
        month_start = date(2024, 2, 1)
        month_end = date(2024, 2, 29)
        tasks = [
            Task(
                date=date(2024, 2, 8),
                team_code="T7",
                team_name="Team 7",
                employee_number="8C",
                employee_name="Quartz combined",
                chantier="CH8E",
                finish_type="RP.LQUARTZOREG, MANQUE.FINITION",
                sqm=Decimal("135.65"),
                sqm_total_chantier=Decimal("135.65"),
                sqm_scie=Decimal("0"),
                kg_steel=Decimal("0"),
                intervention_type="coulage",
            )
        ]
        res = self._run_single_employee(tasks, {"8C": ROLE_POLISSEUR}, month_start, month_end)
        self.assertAlmostEqual(res.finitions_pay, 203.48, places=2)
        self.assertAlmostEqual(res.total, 203.48, places=2)

    def test_scieur_uses_polisseur_finish_rules(self):
        month_start = date(2024, 2, 1)
        month_end = date(2024, 2, 29)
        tasks = [
            Task(
                date=date(2024, 2, 9),
                team_code="T8",
                team_name="Team 8",
                employee_number="9",
                employee_name="Scieur finish",
                chantier="CH9",
                finish_type="desactive",
                sqm=Decimal("0"),
                sqm_total_chantier=Decimal("220"),
                sqm_scie=Decimal("0"),
                kg_steel=Decimal("0"),
                intervention_type="coulage",
            )
        ]
        res = self._run_single_employee(tasks, {"9": ROLE_SCIEUR}, month_start, month_end)
        self.assertAlmostEqual(res.finitions_pay, 160.00, places=2)
        self.assertAlmostEqual(res.total, 160.00, places=2)

    def test_scieur_coulage_day_adds_scie_on_top_of_forfait(self):
        month_start = date(2024, 2, 1)
        month_end = date(2024, 2, 29)
        tasks = [
            Task(
                date=date(2024, 2, 12),
                team_code="T9A",
                team_name="Team 9A",
                employee_number="9A1",
                employee_name="Scieur mixte",
                chantier="CH9F",
                finish_type="prepa",
                sqm=Decimal("46"),
                sqm_total_chantier=Decimal("92"),
                sqm_scie=Decimal("0"),
                kg_steel=Decimal("0"),
                intervention_type="coulage",
            ),
            Task(
                date=date(2024, 2, 12),
                team_code="T9A",
                team_name="Team 9A",
                employee_number="9A1",
                employee_name="Scieur mixte",
                chantier="CH9G",
                finish_type="scie",
                sqm=Decimal("0"),
                sqm_total_chantier=Decimal("0"),
                sqm_scie=Decimal("383.33"),
                kg_steel=Decimal("0"),
                intervention_type="scie",
            ),
        ]
        res = self._run_single_employee(tasks, {"9A1": ROLE_SCIEUR}, month_start, month_end)
        self.assertAlmostEqual(res.finitions_pay, 150.00, places=2)
        self.assertAlmostEqual(res.scie_pay, 69.00, places=2)
        self.assertAlmostEqual(res.total, 219.00, places=2)

    def test_scieur_preparation_plus_scie_does_not_add_scie_supplement(self):
        month_start = date(2024, 2, 1)
        month_end = date(2024, 2, 29)
        tasks = [
            Task(
                date=date(2024, 2, 12),
                team_code="T9A",
                team_name="Team 9A",
                employee_number="9A1B",
                employee_name="Scieur preparation",
                chantier="CH9P",
                finish_type="prepa",
                sqm=Decimal("0"),
                sqm_total_chantier=Decimal("0"),
                sqm_scie=Decimal("0"),
                kg_steel=Decimal("0"),
                intervention_type="prepa",
            ),
            Task(
                date=date(2024, 2, 12),
                team_code="T9A",
                team_name="Team 9A",
                employee_number="9A1B",
                employee_name="Scieur preparation",
                chantier="CH9S",
                finish_type="scie",
                sqm=Decimal("0"),
                sqm_total_chantier=Decimal("0"),
                sqm_scie=Decimal("383.33"),
                kg_steel=Decimal("0"),
                intervention_type="scie",
            ),
        ]
        res = self._run_single_employee(tasks, {"9A1B": ROLE_SCIEUR}, month_start, month_end)
        self.assertAlmostEqual(res.finitions_pay, 150.00, places=2)
        self.assertAlmostEqual(res.scie_pay, 0.00, places=2)
        self.assertAlmostEqual(res.total, 150.00, places=2)

    def test_chef_desactive_uses_polisseur_scale_and_daily_prime_chef_prorata(self):
        month_start = date(2024, 2, 1)
        month_end = date(2024, 2, 29)
        tasks = [
            Task(
                date=date(2024, 2, 13),
                team_code="T9B",
                team_name="Team 9B",
                employee_number="9A2",
                employee_name="Chef partiel",
                chantier="CH9H",
                finish_type="RP.DESACTIVE",
                sqm=Decimal("76.30"),
                sqm_total_chantier=Decimal("378"),
                sqm_scie=Decimal("0"),
                kg_steel=Decimal("0"),
                intervention_type="coulage",
                is_chief=True,
            ),
            Task(
                date=date(2024, 2, 14),
                team_code="T9B",
                team_name="Team 9B",
                employee_number="9A2",
                employee_name="Chef partiel",
                chantier="CH9I",
                finish_type="prepa",
                sqm=Decimal("0"),
                sqm_total_chantier=Decimal("0"),
                sqm_scie=Decimal("0"),
                kg_steel=Decimal("0"),
                intervention_type="prepa",
                is_chief=False,
            ),
        ]
        res = self._run_single_employee(tasks, {"9A2": ROLE_POLISSEUR}, month_start, month_end)
        self.assertAlmostEqual(res.finitions_pay, 340.00, places=2)
        self.assertAlmostEqual(res.prime_chef, float((Decimal("400") / Decimal("21")).quantize(Decimal("0.01"))), places=2)

    def test_aide_finitions_threshold_uses_130_euro_breakpoint(self):
        month_start = date(2024, 2, 1)
        month_end = date(2024, 2, 29)
        tasks = [
            Task(
                date=date(2024, 2, 15),
                team_code="T9C",
                team_name="Team 9C",
                employee_number="9A3",
                employee_name="Aide seuil",
                chantier="CH9J",
                finish_type="RP.LQUARTZO",
                sqm=Decimal("90"),
                sqm_total_chantier=Decimal("90"),
                sqm_scie=Decimal("0"),
                kg_steel=Decimal("0"),
                intervention_type="coulage",
            )
        ]
        res = self._run_single_employee(tasks, {"9A3": ROLE_AIDE}, month_start, month_end)
        self.assertAlmostEqual(res.finitions_pay, 135.00, places=2)
        self.assertAlmostEqual(res.total, 135.00, places=2)

    def test_scieur_receives_intemperie_rate(self):
        month_start = date(2024, 2, 1)
        month_end = date(2024, 2, 29)
        tasks = [
            Task(
                date=date(2024, 2, 12),
                team_code="T9",
                team_name="Team 9",
                employee_number="10",
                employee_name="Scieur intemp",
                chantier="CH10",
                finish_type="lisse quartz",
                sqm=Decimal("0"),
                sqm_total_chantier=Decimal("0"),
                sqm_scie=Decimal("0"),
                kg_steel=Decimal("0"),
                intervention_type="intemperie",
                is_intemperie=True,
            )
        ]
        res = self._run_single_employee(tasks, {"10": ROLE_SCIEUR}, month_start, month_end)
        self.assertAlmostEqual(res.intemperies_total, 69.66, places=2)
        self.assertAlmostEqual(res.total, 69.66, places=2)

    def test_deplacement_type_uses_opc_tpdep_and_highest_daily_type(self):
        month_start = date(2024, 2, 1)
        month_end = date(2024, 2, 29)
        tasks = [
            Task(
                date=date(2024, 2, 13),
                team_code="T10",
                team_name="Team 10",
                employee_number="11",
                employee_name="Deplacement",
                chantier="CH11A",
                finish_type="prepa",
                sqm=Decimal("0"),
                sqm_total_chantier=Decimal("0"),
                sqm_scie=Decimal("0"),
                kg_steel=Decimal("0"),
                intervention_type="coulage",
                deplacement_type="Z2",
            ),
            Task(
                date=date(2024, 2, 13),
                team_code="T10",
                team_name="Team 10",
                employee_number="11",
                employee_name="Deplacement",
                chantier="CH11B",
                finish_type="prepa",
                sqm=Decimal("0"),
                sqm_total_chantier=Decimal("0"),
                sqm_scie=Decimal("0"),
                kg_steel=Decimal("0"),
                intervention_type="coulage",
                deplacement_type="GD",
            ),
            Task(
                date=date(2024, 2, 14),
                team_code="T10",
                team_name="Team 10",
                employee_number="11",
                employee_name="Deplacement",
                chantier="CH11C",
                finish_type="prepa",
                sqm=Decimal("0"),
                sqm_total_chantier=Decimal("0"),
                sqm_scie=Decimal("0"),
                kg_steel=Decimal("0"),
                intervention_type="coulage",
                deplacement_type="Z3",
            ),
        ]
        res = self._run_single_employee(tasks, {"11": ROLE_POLISSEUR}, month_start, month_end)
        self.assertEqual(res.grand_deplacement, 1)
        self.assertEqual(res.zone_counts["z2"], 0)
        self.assertEqual(res.zone_counts["z3"], 1)
        self.assertEqual(res.zone_counts["z4"], 0)
        self.assertEqual(res.panier_repas, 2)

    def test_panier_counts_worked_day_even_without_deplacement_type(self):
        month_start = date(2024, 2, 1)
        month_end = date(2024, 2, 29)
        tasks = [
            Task(
                date=date(2024, 2, 15),
                team_code="T11",
                team_name="Team 11",
                employee_number="12",
                employee_name="Sem Tpdep",
                chantier="CH12",
                finish_type="prepa",
                sqm=Decimal("0"),
                sqm_total_chantier=Decimal("0"),
                sqm_scie=Decimal("0"),
                kg_steel=Decimal("0"),
                intervention_type="coulage",
            )
        ]
        res = self._run_single_employee(tasks, {"12": ROLE_POLISSEUR}, month_start, month_end)
        self.assertEqual(res.worked_days, 1)
        self.assertEqual(res.panier_repas, 1)
        self.assertEqual(res.grand_deplacement, 0)
        self.assertEqual(sum(res.zone_counts.values()), 0)

    def test_minimum_guarantee(self):
        # 19 business days after removing 4 holidays; 17 worked days trigger complement.
        month_start = date(2024, 1, 1)
        month_end = date(2024, 1, 31)
        holidays = [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4), date(2024, 1, 5)]
        tasks = []
        current = date(2024, 1, 8)
        for i in range(17):
            tasks.append(
                Task(
                    date=current + timedelta(days=i),
                    team_code="T4",
                    team_name="Team 4",
                    employee_number="5",
                    employee_name="Polisseur",
                    chantier="CH5",
                    finish_type="prepa",
                    sqm=Decimal("0"),
                    sqm_total_chantier=Decimal("0"),
                    sqm_scie=Decimal("0"),
                    kg_steel=Decimal("0"),
                    intervention_type="coulage",
                )
            )
        res = self._run_single_employee(tasks, {"5": ROLE_POLISSEUR}, month_start, month_end, holidays=holidays)
        expected_minimum = (Decimal("3150") / Decimal("19") * Decimal("17")).quantize(Decimal("0.01"))
        monthly_without_intemp = Decimal(str(res.finitions_pay))
        complement = expected_minimum - monthly_without_intemp
        self.assertAlmostEqual(res.complement_minimum, float(complement), places=2)
        self.assertAlmostEqual(res.total, float(expected_minimum), places=2)


if __name__ == "__main__":
    unittest.main()
