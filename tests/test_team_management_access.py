from datetime import date
from contextlib import contextmanager
import json
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from flask import Flask

from modules.gr_planning import service as planning_service
from modules.gr_planning.service import (
    _import_legacy_environment, get_api_access_scope, rewrite_team_management_body_html,
)


def team(code, group):
    return {"fref": code, "nmfref": f"Team {code}", "u_planning": group, "frefstamp": f"STAMP-{code}"}


TEAMS = [
    team("PT", "PORTUGAL"), team("FR", "FRANCE"), team("MA", "MAROC"),
    team("IA", "INTERSOL-ALSACE"), team("IL", "INTERSOL-LORRAINE"),
    team("IC", "INTERSOL-CHAMPAGNE"), team("SUB", "SOUS-TRAITANTS"),
    team("PUMP", "POMPES"), team("UNKNOWN", ""),
]
BY_CODE = {row["fref"]: row for row in TEAMS}


class TeamManagementAccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = _import_legacy_environment(("test-server", "test-db", "test-user", "test-password", ""))
        cls.env.app.config["TESTING"] = True

    def setUp(self):
        self.client = self.env.app.test_client()
        self.login(u_ia=True)

    def login(self, **flags):
        self.user = {"usercode": "test-user", "username": "Test user", "u_teams": True, **flags}
        with self.client.session_transaction() as session:
            session["user"] = self.user

    def page(self):
        members = [{"fref": row["fref"], "no": row["fref"], "nome": f"Member {row['fref']}",
                    "dataini": date(2026, 1, 1)} for row in TEAMS]
        with patch.object(self.env.database, "fetch_all_teams", return_value=TEAMS), \
             patch.object(self.env.database, "fetch_team_planning_groups", return_value=[row["u_planning"] for row in TEAMS if row["u_planning"]]), \
             patch.object(self.env.database, "fetch_team_members_for_date", return_value=members), \
             patch.object(self.env.database, "fetch_unassigned_employees", return_value=[]), \
             patch.object(self.env.app_module, "render_template", return_value="rendered") as render:
            response = self.client.get("/teams?date=2026-10-22")
        self.assertEqual(response.status_code, 200)
        return render.call_args.kwargs

    def test_page_cards_members_and_dropdown_follow_each_planning_market(self):
        for flag, expected in (("u_pt", "PT"), ("u_fr", "FR"), ("u_ma", "MA"),
                               ("u_ia", "IA"), ("u_il", "IL"), ("u_ic", "IC")):
            with self.subTest(flag=flag):
                self.login(**{flag: True})
                context = self.page()
                cards = [row for group in context["team_groups"] for row in group["teams"]]
                self.assertEqual({row["code"] for row in cards}, {expected, "SUB"})
                self.assertEqual({row["code"] for row in context["team_options"]}, {expected, "SUB"})
                self.assertEqual({member["name"] for row in cards for member in row["members"]},
                                 {f"Member {expected}", "Member SUB"})

    def test_admin_keeps_all_teams_including_unclassified_groups(self):
        self.login(u_admin=True)
        self.assertEqual({row["code"] for row in self.page()["team_options"]}, set(BY_CODE))

    def test_intersol_payroll_admin_does_not_bypass_market_access(self):
        self.login(u_adminis=True, u_ia=True)
        self.assertEqual({row["code"] for row in self.page()["team_options"]}, {"IA", "SUB"})

    def test_no_market_permissions_still_allows_subcontractors(self):
        self.login()
        self.assertEqual({row["code"] for row in self.page()["team_options"]}, {"SUB"})

    def test_combined_permissions_are_added_without_opening_other_regions(self):
        self.login(u_fr=True, u_ma=True, u_il=True)
        self.assertEqual({row["code"] for row in self.page()["team_options"]}, {"FR", "MA", "IL", "SUB"})

    def test_unlabelled_intersol_group_uses_any_authorized_intersol_region(self):
        self.assertTrue(self.env.app_module._can_manage_team(self.user, team("GENERIC", "INTERSOL")))
        self.login(u_fr=True)
        self.assertFalse(self.env.app_module._can_manage_team(self.user, team("GENERIC", "INTERSOL")))

    def test_string_false_flags_do_not_grant_admin_or_other_market_access(self):
        self.login(u_admin="0", u_ia=True, u_fr="false")
        self.assertEqual({row["code"] for row in self.page()["team_options"]}, {"IA", "SUB"})

    def membership_request(self, action, *, source=None, target=None):
        memberships = []
        if source:
            memberships = [{"u_teamstamp": "MEMBERSHIP", "fref": source, "frefstamp": f"STAMP-{source}",
                            "dataini": date(2026, 1, 1), "datafim": None,
                            "nome": "Worker", "origem": "INTERSOL"}]
        payload = {"action": action, "employee_number": "42", "employee_origin": "INTERSOL",
                   "reference_date": "2026-10-22", "target_team": target}
        with patch.object(self.env.database, "fetch_employee_memberships", return_value=memberships), \
             patch.object(self.env.database, "fetch_employee_details", return_value={"cval4": "Worker", "bdados": "INTERSOL"}), \
             patch.object(self.env.database, "fetch_team_by_code", side_effect=BY_CODE.get), \
             patch.object(self.env.database, "fetch_team_leads_for_period", return_value=[]), \
             patch.object(self.env.database, "apply_team_membership_operations") as apply:
            response = self.client.post("/api/team-memberships", json=payload)
        return response, apply

    def test_api_rejects_hidden_targets_even_with_a_manual_request(self):
        for action in ("assign", "lead"):
            with self.subTest(action=action):
                response, apply = self.membership_request(action, target="IL")
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.get_json()["error"], "team_access_denied")
                apply.assert_not_called()

    def test_api_rejects_removal_promotion_or_transfer_from_a_hidden_team(self):
        for action in ("remove", "lead", "transfer"):
            with self.subTest(action=action):
                response, apply = self.membership_request(action, source="FR", target="IA")
                self.assertEqual(response.status_code, 403)
                apply.assert_not_called()

    def test_api_rejects_transfer_from_visible_team_to_hidden_team(self):
        response, apply = self.membership_request("transfer", source="IA", target="IL")
        self.assertEqual(response.status_code, 403)
        apply.assert_not_called()

    def test_api_still_allows_authorized_teams_and_subcontractors(self):
        for target in ("IA", "SUB"):
            with self.subTest(target=target):
                response, apply = self.membership_request("assign", target=target)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(apply.call_args.args[0][0]["team_code"], target)

    def test_api_allows_transfer_between_visible_team_and_subcontractor(self):
        response, apply = self.membership_request("transfer", source="IA", target="SUB")
        self.assertEqual(response.status_code, 200)
        apply.assert_called_once()

    def test_admin_can_change_a_team_without_market_permissions(self):
        self.login(u_admin=True)
        response, apply = self.membership_request("assign", target="IL")
        self.assertEqual(response.status_code, 200)
        apply.assert_called_once()

    def test_api_requires_team_management_permission(self):
        self.login(u_teams=False, u_ia=True)
        response, apply = self.membership_request("assign", target="IA")
        self.assertEqual(response.status_code, 403)
        apply.assert_not_called()

    def test_api_requires_authentication(self):
        with self.client.session_transaction() as session:
            session.clear()
        response = self.client.post("/api/team-memberships", json={})
        self.assertEqual(response.status_code, 401)


class TeamCreationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = _import_legacy_environment(("test-server", "test-db", "test-user", "test-password", ""))
        cls.env.app.config["TESTING"] = True

    def setUp(self):
        self.client = self.env.app.test_client()
        self.user = {"usercode": "creator", "username": "Creator", "u_teams": True, "u_ia": True}
        self.login()
        self.payload = {"code": "NEW", "description": "Nova equipa", "planning": "INTERSOL-ALSACE"}
        self.groups = [row["u_planning"] for row in TEAMS if row["u_planning"]]

    def login(self, *, can_create_teams=True):
        with self.client.session_transaction() as session:
            session["user"] = self.user
            session["can_create_teams"] = can_create_teams

    def create(self, payload=None, *, error=None):
        with patch.object(self.env.database, "fetch_team_planning_groups", return_value=self.groups), \
             patch.object(self.env.database, "create_team", side_effect=error,
                          return_value={**self.payload, "stamp": "NEWSTAMP"}) as create:
            response = self.client.post("/api/teams", json=payload if payload is not None else self.payload)
        return response, create

    def test_creation_returns_saved_team_and_records_the_authenticated_user(self):
        response, create = self.create({"code": " NEW ", "description": " Nova equipa ", "planning": " intersol-alsace "})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["team"]["stamp"], "NEWSTAMP")
        create.assert_called_once_with("NEW", "Nova equipa", "INTERSOL-ALSACE", "creator")

    def test_creation_validates_required_fields_and_database_lengths(self):
        invalid = [({**self.payload, field: value}, f"missing_{field}")
                   for field in ("code", "description", "planning") for value in ("", "   ", None, {})]
        invalid += [({**self.payload, "code": "X" * 21}, "code_too_long"),
                    ({**self.payload, "description": "X" * 71}, "description_too_long")]
        for payload, error in invalid:
            with self.subTest(payload=payload):
                response, create = self.create(payload)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json()["error"], error)
                create.assert_not_called()

    def test_duplicate_code_returns_conflict(self):
        response, _ = self.create(error=ValueError("team_code_exists"))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["error"], "team_code_exists")

    def test_cannot_create_in_another_intersol_region(self):
        response, create = self.create({**self.payload, "planning": "INTERSOL-LORRAINE"})
        self.assertEqual(response.status_code, 403)
        create.assert_not_called()

    def test_arbitrary_planning_group_is_rejected_even_for_admin(self):
        self.user["u_admin"] = True
        self.login()
        response, create = self.create({**self.payload, "planning": "UNCONFIGURED"})
        self.assertEqual(response.status_code, 400)
        create.assert_not_called()

    def test_admin_can_create_in_any_configured_group(self):
        self.user["u_admin"] = True
        self.login()
        response, create = self.create({**self.payload, "planning": "POMPES"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(create.call_args.args[2], "POMPES")

    def test_subcontractors_are_available_without_market_permissions(self):
        self.user["u_ia"] = False
        self.login()
        response, create = self.create({**self.payload, "planning": "SOUS-TRAITANTS"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(create.call_args.args[2], "SOUS-TRAITANTS")

    def test_creation_requires_team_management_permission_and_authentication(self):
        self.user["u_teams"] = False
        self.login()
        response, create = self.create()
        self.assertEqual(response.status_code, 403)
        create.assert_not_called()
        with self.client.session_transaction() as session:
            session.clear()
        response, create = self.create()
        self.assertEqual(response.status_code, 401)
        create.assert_not_called()

    def test_legacy_admin_roles_do_not_grant_creation_permission(self):
        for roles in ({"u_admin": True}, {"u_adminis": True}, {"u_teams": True}):
            with self.subTest(roles=roles):
                self.user.update(roles)
                self.login(can_create_teams=False)
                response, create = self.create()
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.get_json()["error"], "admin_required")
                create.assert_not_called()

    def test_database_failure_does_not_report_a_created_team(self):
        with self.assertLogs(self.env.app.logger, level="ERROR"):
            response, _ = self.create(error=RuntimeError("private SQL diagnostics"))
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json(), {"error": "database_error"})

    def test_new_team_appears_in_page_and_accepts_an_existing_employee(self):
        teams = dict(BY_CODE)

        def insert(code, description, planning, user):
            row = team(code, planning)
            row["nmfref"] = description
            teams[code] = row
            return {"code": code, "description": description, "planning": planning, "stamp": row["frefstamp"]}

        with patch.object(self.env.database, "fetch_team_planning_groups", return_value=self.groups), \
             patch.object(self.env.database, "create_team", side_effect=insert), \
             patch.object(self.env.database, "fetch_all_teams", side_effect=lambda: list(teams.values())), \
             patch.object(self.env.database, "fetch_team_by_code", side_effect=teams.get), \
             patch.object(self.env.database, "fetch_team_members_for_date", return_value=[]), \
             patch.object(self.env.database, "fetch_unassigned_employees", return_value=[]), \
             patch.object(self.env.database, "fetch_employee_memberships", return_value=[]), \
             patch.object(self.env.database, "fetch_employee_details", return_value={"cval4": "Worker", "bdados": "INTERSOL"}), \
             patch.object(self.env.database, "apply_team_membership_operations") as apply:
            self.assertEqual(self.client.post("/api/teams", json=self.payload).status_code, 201)
            page = self.client.get("/teams?date=2026-10-22&lang=pt")
            self.assertEqual(page.status_code, 200)
            body, meta = rewrite_team_management_body_html(page.get_data(as_text=True))
            self.assertIn("Nova equipa", body)
            self.assertIn('id="team-create-modal"', body)
            self.assertIn('data-team-create-open', body)
            self.assertIn('INTERSOL-ALSACE', body)
            self.assertNotIn('<option value="INTERSOL-LORRAINE">', body)
            self.assertIn('NEW', meta["team_options"])
            response = self.client.post("/api/team-memberships", json={
                "action": "assign", "employee_number": "42", "employee_origin": "INTERSOL",
                "target_team": "NEW", "reference_date": "2026-10-22",
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(apply.call_args.args[0][0]["team_code"], "NEW")

    def test_new_endpoint_uses_team_management_permissions_in_the_host_proxy(self):
        self.assertEqual(get_api_access_scope("teams"), "team_management")


class TeamCreationDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = _import_legacy_environment(("test-server", "test-db", "test-user", "test-password", ""))

    def setUp(self):
        self.database = self.env.database_module.Database(SimpleNamespace())
        self.connection = MagicMock()
        self.cursor = self.connection.cursor.return_value

        @contextmanager
        def connect():
            yield self.connection

        self.database.connect = connect

    def test_duplicate_existing_code_rolls_back_without_inserting(self):
        self.cursor.fetchone.return_value = ("EXISTS",)
        with self.assertRaisesRegex(ValueError, "team_code_exists"):
            self.database.create_team("EXISTS", "Team", "PORTUGAL", "creator")
        self.connection.rollback.assert_called_once()
        self.connection.commit.assert_not_called()
        self.assertEqual(self.cursor.execute.call_count, 1)

    def test_unconfirmed_insert_is_rolled_back(self):
        self.cursor.fetchone.side_effect = [None, None]
        with self.assertRaisesRegex(RuntimeError, "team_creation_not_confirmed"):
            self.database.create_team("NEW", "Team", "PORTUGAL", "creator")
        self.connection.rollback.assert_called_once()
        self.connection.commit.assert_not_called()

    def test_sql_failure_is_rolled_back(self):
        self.cursor.fetchone.return_value = None
        self.cursor.execute.side_effect = [None, RuntimeError("SQL failure")]
        with self.assertRaisesRegex(RuntimeError, "SQL failure"):
            self.database.create_team("NEW", "Team", "PORTUGAL", "creator")
        self.connection.rollback.assert_called_once()
        self.connection.commit.assert_not_called()


class TeamCreationApplicationAdminTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = _import_legacy_environment(("test-server", "test-db", "test-user", "test-password", ""))
        cls.env.app.config["TESTING"] = True

    def setUp(self):
        self.host = Flask(__name__)
        self.legacy_user = {"usercode": "creator", "username": "Creator", "u_teams": True, "u_ia": True}
        self.payload = {"code": "NEW", "description": "Nova equipa", "planning": "INTERSOL-ALSACE"}

    def request(self, application_user, path, *, method="GET", payload=None):
        with self.host.test_request_context(path), \
             patch.object(planning_service, "current_user", application_user), \
             patch.object(planning_service, "get_legacy_environment", return_value=self.env), \
             patch.object(self.env.database, "fetch_team_planning_groups", return_value=["INTERSOL-ALSACE", "SOUS-TRAITANTS"]), \
             patch.object(self.env.database, "fetch_all_teams", return_value=TEAMS), \
             patch.object(self.env.database, "fetch_team_members_for_date", return_value=[]), \
             patch.object(self.env.database, "fetch_unassigned_employees", return_value=[]), \
             patch.object(self.env.database, "create_team", return_value={**self.payload, "stamp": "NEWSTAMP"}) as create:
            response = planning_service.open_legacy_request(
                path, login_value="creator", method=method, access_mode="team_management",
                data=json.dumps(payload or self.payload).encode() if method == "POST" else None,
                content_type="application/json" if method == "POST" else None,
                legacy_user=self.legacy_user,
            )
        return response, create

    def test_application_us_admin_one_can_see_the_button_and_create(self):
        user = SimpleNamespace(is_authenticated=True, ADMIN=1)
        response, _ = self.request(user, "/teams")
        self.assertIn("data-team-create-open", response.get_data(as_text=True))
        self.assertIn('id="team-create-modal"', response.get_data(as_text=True))
        response, create = self.request(user, "/api/teams", method="POST")
        self.assertEqual(response.status_code, 201)
        create.assert_called_once()

    def test_non_admin_cannot_see_the_button_or_call_the_api_even_as_phc_admin(self):
        self.legacy_user.update(u_admin=True, u_adminis=True)
        for user in (SimpleNamespace(is_authenticated=True, ADMIN=0),
                     SimpleNamespace(is_authenticated=True, DEV=1),
                     SimpleNamespace(is_authenticated=False, ADMIN=1)):
            with self.subTest(user=user):
                response, _ = self.request(user, "/teams")
                body = response.get_data(as_text=True)
                self.assertNotIn("data-team-create-open", body)
                self.assertNotIn('id="team-create-modal"', body)
                self.assertIn("Team IA", body)
                response, create = self.request(user, "/api/teams", method="POST")
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.get_json()["error"], "admin_required")
                create.assert_not_called()

    def test_client_payload_cannot_enable_the_admin_permission(self):
        payload = {**self.payload, "ADMIN": 1, "can_create_teams": True, "u_admin": True}
        response, create = self.request(SimpleNamespace(is_authenticated=True, ADMIN=0),
                                        "/api/teams", method="POST", payload=payload)
        self.assertEqual(response.status_code, 403)
        create.assert_not_called()


if __name__ == "__main__":
    unittest.main()
