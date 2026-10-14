from datetime import date
from decimal import Decimal
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from flask import Flask
from flask_login import LoginManager
from jinja2 import DictLoader

from modules.gr_travel_maps import access, config, service, sources
from modules.gr_travel_maps.routes import bp


COMPANY = {"feid": 2, "name": "Empresa PT", "phc_db": "HSOLS_PT", "phc_server": "private-host"}
START, END = date(2026, 9, 1), date(2026, 10, 1)


def salary_line(**overrides):
    return {
        "NO": 12, "PESTAMP": "PE12", "NOME": "Trabalhador de teste", "IDENTITIES": 1,
        "PRSTAMP": "PR1", "RECIBO": 1, "DATA": START, "ANO": 2026, "MESREF": "setembro", "STATUS": 1,
        "PRRESTAMP": "LINE1", "CR": 60, "REM": "Kms em Viatura Própria", "RQTT": Decimal("684"),
        "ERVU": Decimal("0.40"), "ERE": Decimal("273.60"), "DTREF": START, "ORIPRRESTAMP": "",
        **overrides,
    }


class TravelMapServiceTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.addCleanup(self.ctx.pop)
        self.rule = config.payroll_rule("HSOLS_PT", START, END)

    def aggregate(self, rows):
        return service.aggregate_payroll(rows, COMPANY, START, END, self.rule)

    def test_all_receipts_and_signed_adjustments_are_preserved(self):
        result = self.aggregate([
            salary_line(),
            salary_line(PRSTAMP="PR2", PRRESTAMP="LINE2", RECIBO=2, RQTT=Decimal("-8"), ERE=Decimal("-3.20")),
            salary_line(PRRESTAMP="LINE3", CR=40, RQTT=Decimal("4"), ERVU=Decimal("80"), ERE=Decimal("320")),
        ])
        row = result["rows"][0]
        self.assertEqual(result["receipt_count"], 2)
        self.assertEqual(result["line_count"], 3)
        self.assertEqual(row["phc"]["km"], {"quantity": "676", "amount": "270.40"})
        self.assertEqual(row["phc"]["ac_estrangeiro"]["quantity"], "4")
        self.assertEqual(len(row["receipts"]), 2)
        self.assertIn("Regularização", row["warnings"][0])
        self.assertIsNone(row["map"]["km"])
        self.assertIsNone(row["difference"]["km"])
        self.assertIsNone(row["reconciliation"]["km"])

    def test_unknown_national_category_is_not_zero(self):
        result = self.aggregate([salary_line()])
        self.assertEqual(result["totals"]["ac_nacional"], {"quantity": None, "amount": None})
        self.assertEqual(result["totals"]["ac_estrangeiro"]["quantity"], "0")

    def test_employees_without_relevant_lines_remain_visible(self):
        result = self.aggregate([salary_line(PRRESTAMP=None)])
        self.assertEqual(result["employee_count"], 1)
        self.assertEqual(result["line_count"], 0)
        self.assertEqual(result["rows"][0]["phc"]["km"]["quantity"], "0")

    def test_amount_mismatch_is_reported_without_rewriting_phc(self):
        result = self.aggregate([salary_line(ERE=Decimal("273.63"))])
        row = result["rows"][0]
        self.assertEqual(row["phc"]["km"]["amount"], "273.63")
        self.assertEqual(row["lines"][0]["original"]["ERE"], "273.63")
        self.assertIn("valor original", row["warnings"][0])

    def test_decimal_arithmetic_and_fractional_days(self):
        result = self.aggregate([
            salary_line(CR=40, RQTT=Decimal("0.1"), ERVU=Decimal("1"), ERE=Decimal("0.1")),
            salary_line(PRRESTAMP="LINE2", CR=40, RQTT=Decimal("0.2"), ERVU=Decimal("1"), ERE=Decimal("0.2")),
        ])
        self.assertEqual(result["totals"]["ac_estrangeiro"]["quantity"], "0.3")
        self.assertEqual(result["totals"]["ac_estrangeiro"]["amount"], "0.3")

    def test_duplicate_source_lines_fail_instead_of_inflating_totals(self):
        with self.assertRaises(config.SourceUnavailable):
            self.aggregate([salary_line(), salary_line()])

    def test_missing_or_nonfinite_quantity_does_not_become_zero(self):
        for value in (None, "NaN", "Infinity", "abc"):
            with self.subTest(value=value), self.assertRaises(config.SourceUnavailable):
                self.aggregate([salary_line(RQTT=value)])

    def test_reference_outside_month_is_visible_and_retained(self):
        result = self.aggregate([salary_line(DTREF=date(2026, 8, 1))])
        self.assertEqual(result["totals"]["km"]["quantity"], "684")
        self.assertIn("fora do mês", result["rows"][0]["warnings"][0])

    def test_company_is_part_of_employee_key(self):
        first = self.aggregate([salary_line()])["rows"][0]
        second = service.aggregate_payroll([salary_line()], {**COMPANY, "feid": 8, "phc_db": "INTERSOL"}, START, END, self.rule)["rows"][0]
        self.assertNotEqual(first["key"], second["key"])

    def test_missing_employee_identity_is_flagged(self):
        result = self.aggregate([salary_line(PESTAMP=None, IDENTITIES=2)])
        self.assertFalse(result["rows"][0]["identity_resolved"])
        self.assertIn("Identidade PHC por resolver.", result["rows"][0]["warnings"])

    def test_unknown_company_and_year_have_no_implicit_mapping(self):
        self.assertIsNone(config.payroll_rule("HSOLS_FR", START, END))
        self.assertIsNone(config.payroll_rule("HSOLS_PT", date(2025, 9, 1), date(2025, 10, 1)))

    def test_invalid_or_ambiguous_mapping_fails(self):
        invalid_rules = [
            [{**self.rule, "codes": {"km": [60], "ac_nacional": [60]}}],
            [self.rule, self.rule],
            [{**self.rule, "valid_from": "2026-09-15"}],
            [{**self.rule, "currency": "MAD"}],
        ]
        for rules in invalid_rules:
            with self.subTest(rules=rules):
                self.app.config["GR_TRAVEL_MAPS_CONFIG"] = {"HSOLS_PT": rules}
                with self.assertRaises(config.TravelMapsError):
                    config.payroll_rule("HSOLS_PT", START, END)

    def test_valid_period_and_year_rollover(self):
        self.assertEqual(config.period_bounds("2026", "12"), (date(2026, 12, 1), date(2027, 1, 1)))
        for year, month in ((None, 9), (2026, 13), (1999, 1), (2026, "9; DROP TABLE PR")):
            with self.subTest(year=year, month=month), self.assertRaises(config.TravelMapsError):
                config.period_bounds(year, month)

    def test_unauthorized_company_is_rejected_before_phc_access(self):
        with patch.object(service, "list_companies_for_user", return_value=[COMPANY]), patch.object(sources, "payroll_rows") as read:
            with self.assertRaises(config.TravelMapsError) as error:
                service.monthly_panel(8, 2026, 9, object())
        self.assertEqual(error.exception.status_code, 403)
        read.assert_not_called()

    def test_source_failure_never_returns_empty_success(self):
        with patch.object(service, "company_for_user", return_value=COMPANY), patch.object(sources, "payroll_rows", side_effect=config.SourceUnavailable("Offline")):
            with self.assertRaises(config.SourceUnavailable):
                service.monthly_panel(2, 2026, 9, object())

    def test_measurements_do_not_assign_workers_or_infer_country(self):
        record = {"BOSTAMP": "BO1", "OBRANO": 1, "NMDOS": "Auto de Medição", "NDOS": 201,
                  "DATAOBRA": START, "CLIENT_NAME": "Cliente", "CLIENT_NO": 1, "PROCESSO": "PT001", "POSITIVE_LINES": 1}
        with patch.object(service, "company_for_user", return_value=COMPANY), patch.object(sources, "measurement_rows", return_value=([record], [{"NDOS": 201, "NMDOS": "Auto de Medição"}])):
            result = service.monthly_measurements(2, 2026, 9, object())
        self.assertEqual(result["work_count"], 1)
        self.assertIsNone(result["rows"][0]["employee_assignment"])
        self.assertIsNone(result["rows"][0]["country"])
        self.assertIn("data do documento", result["warnings"][0])

    def test_missing_series_differs_from_empty_month(self):
        with patch.object(service, "company_for_user", return_value=COMPANY), patch.object(sources, "measurement_rows", return_value=([], [])):
            self.assertEqual(service.monthly_measurements(2, 2026, 9, object())["source_state"], "UNCONFIGURED")

    def test_reader_uses_read_only_and_rolls_back_and_closes(self):
        connection = MagicMock()
        with patch.object(sources, "_phc_conn_str", return_value="private-connection"), patch.object(sources.pyodbc, "connect", return_value=connection) as connect:
            with sources.reader(COMPANY):
                pass
        self.assertEqual(connect.call_args.kwargs["attrs_before"], {101: 1})
        self.assertFalse(connect.call_args.kwargs["autocommit"])
        connection.rollback.assert_called_once()
        connection.close.assert_called_once()
        connection.commit.assert_not_called()

    def test_reader_closes_on_domain_failure(self):
        connection = MagicMock()
        with patch.object(sources, "_phc_conn_str", return_value="private"), patch.object(sources.pyodbc, "connect", return_value=connection):
            with self.assertRaises(config.SourceUnavailable):
                with sources.reader(COMPANY):
                    raise config.SourceUnavailable("Schema incompatible")
        connection.rollback.assert_called_once()
        connection.close.assert_called_once()

    def test_row_limit_does_not_publish_partial_totals(self):
        cursor = MagicMock()
        cursor.fetchmany.return_value = [()] * (sources.MAX_ROWS + 1)
        with self.assertRaises(config.SourceUnavailable):
            sources.rows(cursor, "SELECT 1")


class EmployeeProfileTests(unittest.TestCase):
    def setUp(self):
        self.employee = {'pestamp': 'PE12', 'identity_resolved': True}
        self.details = {'pe': {'PESTAMP': 'PE12', 'MORADA': ' Rua de teste 1 ', 'CODPOST': '4700-001', 'LOCAL': 'Braga'},
                        'pe2': {'PE2STAMP': 'PE12', 'MATRICULA': ' AA-00-BB '},
                        'fields': {'PE': ['PESTAMP', 'MORADA', 'CODPOST', 'LOCAL'], 'PE2': ['PE2STAMP', 'MATRICULA']}}

    def profile(self):
        with patch.object(service, 'company_for_user', return_value=COMPANY), patch.object(sources, 'employee_details', return_value=self.details):
            return service.employee_profile(2, self.employee, object())

    def test_address_and_plate_have_exact_phc_sources_without_assuming_owner(self):
        profile = self.profile()
        self.assertEqual(profile['origin'], 'Rua de teste 1, 4700-001 Braga')
        self.assertEqual(profile['vehicle'], 'AA-00-BB')
        self.assertEqual(profile['provenance']['origin']['references'][0]['fields'], ['MORADA', 'CODPOST', 'LOCAL'])
        self.assertEqual(profile['provenance']['vehicle']['references'][0]['table'], 'PE2')
        self.assertEqual(profile['original'], self.details)
        self.assertNotIn('owner', profile)

    def test_postal_code_with_locality_does_not_duplicate_it(self):
        self.details['pe']['CODPOST'] = '4700-001 BRAGA'
        self.assertEqual(self.profile()['origin'], 'Rua de teste 1, 4700-001 BRAGA')

    def test_missing_address_or_plate_remains_unknown(self):
        self.details['pe']['MORADA'] = ' '
        self.details['pe2']['MATRICULA'] = ''
        profile = self.profile()
        self.assertEqual(profile['origin'], '')
        self.assertEqual(profile['vehicle'], '')
        self.assertEqual(profile['provenance'], {})
        self.assertIn('Morada em falta', profile['warnings'][0])

    def test_unauthorized_or_unresolved_employee_is_not_read(self):
        with patch.object(service, 'company_for_user', side_effect=config.TravelMapsError('Sem acesso')), patch.object(sources, 'employee_details') as read:
            with self.assertRaises(config.TravelMapsError): service.employee_profile(2, self.employee, object())
        read.assert_not_called()
        self.employee['identity_resolved'] = False
        with patch.object(service, 'company_for_user', return_value=COMPANY), patch.object(sources, 'employee_details') as read:
            self.assertEqual(service.employee_profile(2, self.employee, object())['origin'], '')
        read.assert_not_called()

    def test_selected_employee_queries_use_stamp_parameters(self):
        with patch.object(sources, 'reader'), patch.object(sources, 'columns', side_effect=[set(self.details['fields']['PE']), set(self.details['fields']['PE2'])]), patch.object(sources, 'rows', side_effect=[[self.details['pe']], [self.details['pe2']]]) as read:
            self.assertEqual(sources.employee_details(COMPANY, 'PE12'), self.details)
        self.assertIn('WHERE PESTAMP = ?', read.call_args_list[0].args[1])
        self.assertIn('WHERE PE2STAMP = ?', read.call_args_list[1].args[1])
        self.assertTrue(all(call.args[2] == ('PE12',) for call in read.call_args_list))

    def test_optional_pe2_and_ambiguous_identity(self):
        with patch.object(sources, 'reader'), patch.object(sources, 'columns', side_effect=[{'PESTAMP'}, set()]), patch.object(sources, 'rows', return_value=[{'PESTAMP': 'PE12'}]) as read:
            self.assertIsNone(sources.employee_details(COMPANY, 'PE12')['pe2'])
            self.assertEqual(read.call_count, 1)
        for records in ([], [{'PESTAMP': 'PE12'}, {'PESTAMP': 'PE12'}]):
            with patch.object(sources, 'reader'), patch.object(sources, 'columns', side_effect=[{'PESTAMP'}, set()]), patch.object(sources, 'rows', return_value=records):
                with self.assertRaises(config.SourceUnavailable): sources.employee_details(COMPANY, 'PE12')
        with patch.object(sources, 'reader'), patch.object(sources, 'columns', side_effect=[{'PESTAMP'}, {'PE2STAMP', 'MATRICULA'}]), patch.object(sources, 'rows', side_effect=[[self.details['pe']], [self.details['pe2'], self.details['pe2']]]):
            with self.assertRaises(config.SourceUnavailable): sources.employee_details(COMPANY, 'PE12')


class TravelMapRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SECRET_KEY="test", DB_CLIENT_NAME="GR360_CORE",
                               DB_CURRENT_TARGET_RESOLVER=lambda: "client")
        self.app.register_blueprint(bp)
        self.app.jinja_loader = DictLoader({"base.html": "<html>{% block extra_head %}{% endblock %}<body>{% block content %}{% endblock %}{% block scripts %}{% endblock %}</body></html>"})
        manager = LoginManager(self.app)
        self.user = SimpleNamespace(is_authenticated=True, ADMIN=True, DEV=False, LOGIN="admin", USSTAMP="USER1")
        manager.request_loader(lambda request: self.user)
        self.client = self.app.test_client()

    def test_page_renders_controls_with_no_database_reads(self):
        with patch.object(service, "list_companies_for_user") as read:
            response = self.client.get("/mapas-deslocacoes")
        self.assertEqual(response.status_code, 200)
        self.assertIn('id="travelWorksCompany"', response.get_data(as_text=True))
        self.assertIn('id="travelDetail"', response.get_data(as_text=True))
        self.assertIn("no-store", response.headers["Cache-Control"])
        read.assert_not_called()

    def test_non_gr360_context_is_rejected_before_reads(self):
        self.app.config["DB_CURRENT_TARGET_RESOLVER"] = lambda: "prod"
        with patch.object(service, "monthly_panel") as read:
            self.assertEqual(self.client.get("/api/gr_mapas/mensal?feid=2&ano=2026&mes=9").status_code, 404)
        read.assert_not_called()

    def test_salary_acl_is_required_even_for_a_company_member(self):
        self.user.ADMIN = False
        with patch.object(access, "db") as db, patch.object(service, "list_companies_for_user") as read:
            db.session.execute.return_value.first.return_value = None
            response = self.client.get("/api/gr_mapas/empresas")
        self.assertEqual(response.status_code, 403)
        read.assert_not_called()

    def test_anonymous_user_cannot_read(self):
        self.user = None
        with patch.object(service, "monthly_panel") as read:
            self.assertEqual(self.client.get("/api/gr_mapas/mensal").status_code, 401)
        read.assert_not_called()

    def test_public_company_list_does_not_expose_server(self):
        with patch.object(service, "list_companies_for_user", return_value=[COMPANY]):
            response = self.client.get("/api/gr_mapas/empresas")
        self.assertNotIn("private-host", response.get_data(as_text=True))
        self.assertEqual(response.json["rows"][0]["feid"], 2)

    def test_failure_does_not_leak_connection_details(self):
        with patch.object(service, "monthly_panel", side_effect=RuntimeError("PWD=secret; SERVER=private")):
            response = self.client.get("/api/gr_mapas/mensal")
        self.assertEqual(response.status_code, 502)
        self.assertFalse(response.json["ok"])
        self.assertNotIn("secret", response.get_data(as_text=True))
        self.assertNotIn("rows", response.json)

    def test_missing_period_returns_400(self):
        response = self.client.get("/api/gr_mapas/mensal?feid=2")
        self.assertEqual(response.status_code, 400)

    def test_no_write_endpoints(self):
        for path in ("/api/gr_mapas/mensal", "/api/gr_mapas/autos"):
            self.assertEqual(self.client.post(path, json={}).status_code, 405)


if __name__ == "__main__":
    unittest.main()
