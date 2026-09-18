"""Map inventory tests without a live database, bookings, email or payments."""

import copy
from datetime import date, timedelta
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from services import booking_portal_map as maps
from services import booking_portal_service as portal


def property_row(identifier="one", **changes):
    return {
        "ID": identifier, "PUBLIC_NAME": "Jardim de São João",
        "LAT": "41.15798765", "LON": "-8.62912345",
        "INATIVO": False, "FECHADO": False,
        "ADULT_CAPACITY": 2, "TOTAL_CAPACITY": 3,
        "MIN_NIGHTS": 1, "QUERY_MATCH": 1,
        **changes,
    }


def params(**changes):
    return {
        "checkin": None, "checkout": None, "adultos": None,
        "criancas": 0, "bebes": 0, "hospedes": None,
        "query": "", "errors": [], "has_search": False,
        **changes,
    }


def stay(identifier, starts, ends, **changes):
    return {"ID": identifier, "DATAIN": date.fromisoformat(starts), "DATAOUT": date.fromisoformat(ends), **changes}


class Rows:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def all(self):
        return self.rows

    def first(self):
        return self.rows[0] if self.rows else None


class MapCatalogTests(unittest.TestCase):
    def setUp(self):
        self.inventory = [property_row()]
        self.bookings = []
        self.session = Mock()
        self.session.execute.side_effect = self.execute
        patcher = patch.object(maps, "db", SimpleNamespace(session=self.session))
        patcher.start()
        self.addCleanup(patcher.stop)

    def execute(self, statement, values=None):
        sql = str(statement)
        self.assertTrue(sql.strip().startswith("SELECT"))
        for forbidden in ("INSERT ", "UPDATE ", "DELETE ", "MERGE ", "OFFSET ", "FETCH ", "PHOTO_", "PBASE", "DESCRICAO", "CLIENTE"):
            self.assertNotIn(forbidden, sql.upper())
        return Rows(copy.deepcopy(self.bookings if "INNER JOIN dbo.RS" in sql else self.inventory))

    def result(self, **values):
        return maps.get_map_catalog(params(**values))

    def date_result(self, **values):
        return self.result(checkin=date(2030, 9, 10), checkout=date(2030, 9, 13), **values)

    def available(self, result):
        return {item["id"]: item["available"] for item in result["items"]}

    def test_no_filters_all_public_markers_blue_unpaginated(self):
        self.inventory = [property_row(str(i), PUBLIC_NAME=f"Stay {i}") for i in range(45)]
        result = self.result()
        self.assertEqual((result["total"], result["matched"], len(result["items"])), (45,45,45))
        self.assertEqual(result["missing_coordinates"], 0)
        self.assertFalse(result["has_search"])
        self.assertFalse(result["has_dates"])
        self.assertTrue(all(x["available"] for x in result["items"]))
        self.assertEqual(self.session.execute.call_count, 1)
        self.session.commit.assert_not_called()
        self.session.rollback.assert_not_called()

    def test_public_inventory_excludes_inactive_closed_empty_and_duplicate(self):
        self.inventory += [property_row("inactive",INATIVO=1),property_row("closed",FECHADO=True),property_row(""),property_row("blank",PUBLIC_NAME=" "),property_row("one")]
        result = self.result()
        self.assertEqual(result["total"],1)
        self.assertEqual([item["id"] for item in result["items"]],["one"])
        sql = str(self.session.execute.call_args.args[0])
        self.assertIn("ISNULL(AL.INATIVO, 0) = 0",sql)
        self.assertIn("ISNULL(AL.FECHADO, 0) = 0",sql)
        self.assertIn("LTRIM(RTRIM(ISNULL(AL.NOME, ''))) <> ''",sql)

    def test_only_public_projection_and_rounded_coordinates_leave_service(self):
        self.inventory[0].update({"NOME_INTERNO":"PRIVATE INTERNAL", "MORADA":"PRIVATE ADDRESS", "CLIENTE_EMAIL":"guest@example.com", "DESCRICAO":"PRIVATE DESCRIPTION"})
        item = self.result()["items"][0]
        self.assertEqual(set(item),{"id","name","lat","lon","available"})
        self.assertEqual((item["lat"],item["lon"]),(41.158,-8.629))
        self.assertEqual(item["name"],"Jardim de São João")
        for private in ("PRIVATE", "guest@example.com", "41.15798765", "-8.62912345"):
            self.assertNotIn(private,repr(item))

    def test_missing_nonfinite_out_of_range_or_zero_coordinates_are_counted(self):
        bad = [(None,-8),('',-8),('bad',-8),('nan',-8),('inf',-8),('-inf',-8),(91,-8),(-91,-8),(41,181),(41,-181),(0,-8),(41,0),(True,-8)]
        self.inventory += [property_row(f"bad{i}",LAT=lat,LON=lon) for i,(lat,lon) in enumerate(bad)]
        result = self.result()
        self.assertEqual(result["total"],len(bad)+1)
        self.assertEqual(result["missing_coordinates"],len(bad))
        self.assertEqual(result["matched"],1)
        self.assertEqual(len(result["items"]),1)

    def test_decimal_comma_and_valid_geographical_limits(self):
        self.inventory = [property_row("comma",LAT="41,123456",LON="-8,987654"),property_row("edge",LAT=-90,LON=180)]
        result = self.result()
        self.assertEqual(result["missing_coordinates"],0)
        self.assertEqual((result["items"][0]["lat"],result["items"][0]["lon"]),(41.123,-8.988))
        self.assertEqual((result["items"][1]["lat"],result["items"][1]["lon"]),(-90,180))

    def test_query_uses_database_accent_insensitive_collation_and_bound_parameter(self):
        # SQL is responsible for CI/AI matching (São João matches sao joao).
        self.inventory += [property_row("other", PUBLIC_NAME="Casa Lapa", QUERY_MATCH=0)]
        result = self.result(query="sao joao")
        self.assertEqual(self.available(result),{"one":True,"other":False})
        sql, values = self.session.execute.call_args.args
        self.assertEqual(values,{"query":"%sao joao%"})
        self.assertNotIn("sao joao",str(sql))
        for column in ("NOME","NMAIRBNB","NMPESQUISA","LOCAL","MORADA","ZONA"):
            self.assertIn(f"AL.{column}",str(sql))
        self.assertEqual(str(sql).count("LIKE :query COLLATE SQL_Latin1_General_CP1_CI_AI"),6)
        self.assertNotIn("AS MORADA",str(sql))
        self.assertEqual(result["matched"],1)
        self.assertEqual(result["total"],2)
        self.assertTrue(result["has_search"])

    def test_guest_filter_keeps_nonmatching_properties_as_grey(self):
        self.inventory += [property_row("big", ADULT_CAPACITY=4,TOTAL_CAPACITY=4)]
        result = self.result(adultos=3,hospedes=3)
        self.assertEqual(self.available(result),{"one":False,"big":True})
        self.assertEqual(result["total"],2)

    def test_children_share_total_capacity_without_separate_child_quota(self):
        self.assertTrue(self.result(adultos=2,criancas=1,hospedes=3)["items"][0]["available"])
        self.assertFalse(self.result(adultos=2,criancas=2,hospedes=4)["items"][0]["available"])

    def test_legacy_guest_filter_and_zero_unknown_capacity(self):
        self.assertTrue(self.result(hospedes=3)["items"][0]["available"])
        self.assertFalse(self.result(hospedes=4)["items"][0]["available"])
        self.inventory[0].update(ADULT_CAPACITY=0,TOTAL_CAPACITY=0)
        self.assertFalse(self.result(adultos=1)["items"][0]["available"])
        self.assertTrue(self.result()["items"][0]["available"])

    def test_capacity_sql_reuses_portal_typology_and_explicit_capacity_rules(self):
        self.result()
        sql = str(self.session.execute.call_args.args[0])
        self.assertIn(maps._alojamento_adult_capacity_sql(),sql)
        self.assertIn(maps._alojamento_capacity_sql(),sql)

    def test_babies_not_in_total_capacity_and_crib_is_not_a_block(self):
        self.inventory[0].update(TOTAL_CAPACITY=2,BERCO=False)
        for number in (1,2):
            self.assertTrue(self.result(adultos=2,bebes=number)["items"][0]["available"])
        self.assertFalse(self.result(adultos=2,bebes=3)["items"][0]["available"])

    def test_invalid_search_never_turns_missing_filters_into_all_blue(self):
        for change in ({"errors":["invalid_date"]},{"checkin":date(2030,9,10)}, {"checkin":date(2030,9,10),"checkout":date(2030,9,9)}, {"adultos":-1},{"adultos":"bad"},{"criancas":1},{"bebes":1}):
            with self.subTest(change=change):
                self.session.execute.reset_mock()
                result=self.result(**change)
                self.assertFalse(result["items"][0]["available"])
                self.assertTrue(result["has_search"])
                self.assertEqual(self.session.execute.call_count,1)

    def test_overlap_blocks_but_same_day_changeovers_do_not(self):
        self.inventory = [property_row("overlap"),property_row("leaves"),property_row("arrives"),property_row("cancelled")]
        self.bookings = [stay("overlap","2030-09-12","2030-09-15"),stay("leaves","2030-09-07","2030-09-10"),stay("arrives","2030-09-13","2030-09-15"),stay("cancelled","2030-09-10","2030-09-13",CANCELADA=1)]
        self.assertEqual(self.available(self.date_result()),{"overlap":False,"leaves":True,"arrives":True,"cancelled":True})
        self.assertEqual(self.session.execute.call_count,2)
        sql = str(self.session.execute.call_args.args[0])
        self.assertIn("ISNULL(RS.CANCELADA, 0) = 0",sql)
        self.assertIn("COLLATE SQL_Latin1_General_CP1_CI_AI",sql)
        self.assertNotIn("RS.CLIENTE",sql)

    def test_date_filters_still_return_all_markers_and_minimum_nights_applies(self):
        self.inventory = [property_row(str(i),MIN_NIGHTS=4 if i%2 else 3) for i in range(38)]
        result = self.date_result()
        self.assertEqual((result["total"],len(result["items"]),result["matched"]),(38,38,19))
        self.assertTrue(result["has_dates"])
        self.assertTrue(result["has_search"])
        self.assertEqual(self.session.execute.call_count,2)

    def test_seasonal_short_gaps_block_checkin_and_checkout(self):
        self.inventory = [property_row("previous",MIN_NIGHTS=3),property_row("next",MIN_NIGHTS=3),property_row("adjacent",MIN_NIGHTS=3)]
        self.bookings = [stay("previous","2030-09-05","2030-09-09"),stay("next","2030-09-14","2030-09-18"),stay("adjacent","2030-09-07","2030-09-10")]
        self.assertEqual(self.available(self.date_result()),{"previous":False,"next":False,"adjacent":True})

    def test_winter_short_gaps_allowed_and_cross_season_boundary_exact(self):
        self.inventory[0]["MIN_NIGHTS"]=3
        self.bookings=[stay("one","2030-02-05","2030-02-09")]
        self.assertTrue(self.result(checkin=date(2030,2,10),checkout=date(2030,2,13))["items"][0]["available"])
        self.bookings=[stay("one","2030-03-28","2030-03-31")]
        self.assertTrue(self.result(checkin=date(2030,4,1),checkout=date(2030,4,4))["items"][0]["available"])
        self.assertFalse(self.result(checkin=date(2030,4,2),checkout=date(2030,4,5))["items"][0]["available"])
        self.bookings=[stay("one","2030-10-28","2030-10-31")]
        self.assertFalse(self.result(checkin=date(2030,11,1),checkout=date(2030,11,4))["items"][0]["available"])

    def test_bad_reservation_intervals_are_ignored_and_names_never_join_in_python(self):
        self.bookings=[{"ID":"one","DATAIN":None,"DATAOUT":date(2030,9,12)},stay("one","2030-09-12","2030-09-12"),stay("one","2030-09-13","2030-09-10"),stay("different","2030-09-10","2030-09-13")]
        self.assertTrue(self.date_result()["items"][0]["available"])

    def test_empty_or_unmapped_inventory_does_not_query_reservations(self):
        for rows in ([],[property_row(LAT=None)]):
            self.inventory=rows
            self.session.execute.reset_mock()
            result=self.date_result()
            self.assertEqual(result["items"],[])
            self.assertEqual(self.session.execute.call_count,1)

    def test_each_get_reads_fresh_inventory_and_reservations(self):
        self.assertTrue(self.date_result()["items"][0]["available"])
        self.bookings=[stay("one","2030-09-10","2030-09-13")]
        self.assertFalse(self.date_result()["items"][0]["available"])
        self.assertEqual(self.session.execute.call_count,4)

    def test_errors_with_valid_dates_skip_reservation_query_and_preserve_date_flag(self):
        result=self.date_result(errors=["invalid_people"])
        self.assertTrue(result["has_dates"])
        self.assertFalse(result["items"][0]["available"])
        self.assertEqual(self.session.execute.call_count,1)

    def test_extreme_date_range_does_not_expand_a_multi_century_calendar(self):
        self.inventory[0]["MIN_NIGHTS"] = 3
        self.bookings = [stay("one","2030-09-10","2030-09-13")]
        with patch.object(maps,"_range_touches_medium_high_season",side_effect=AssertionError("No seasonal gap to expand")):
            result = self.result(checkin=date.min,checkout=date.max)
        self.assertTrue(result["has_dates"])
        self.assertFalse(result["items"][0]["available"])
        self.assertEqual(self.session.execute.call_count,2)
        bounds = self.session.execute.call_args.args[1]
        self.assertEqual(bounds,{"query_start":date.min,"query_end":date.max})

    def test_season_helper_is_reused_only_for_a_short_gap(self):
        self.inventory[0]["MIN_NIGHTS"] = 3
        self.bookings = [stay("one","2030-09-06","2030-09-09"),stay("one","2000-01-01","2000-01-05")]
        original = maps._range_touches_medium_high_season
        calls=[]
        def season(start,end):
            self.assertLessEqual((end-start).days,2)
            calls.append((start,end))
            return original(start,end)
        with patch.object(maps,"_range_touches_medium_high_season",side_effect=season):
            self.assertFalse(self.date_result()["items"][0]["available"])
        self.assertEqual(calls,[(date(2030,9,9),date(2030,9,10))])


class CalendarEquivalenceTests(unittest.TestCase):
    def test_interval_algorithm_matches_existing_calendar_policy(self):
        # Compare against the real existing date-policy implementation, not a
        # second reimplementation. The DB fixture obeys its SQL range bounds.
        for start in (date(2030,3,29),date(2030,4,1),date(2030,9,10),date(2030,10,30),date(2030,11,1),date(2030,12,10)):
            for minimum in (1,2,3,5):
                for delta in (-3,-1,0,1,3):
                    end=start+timedelta(days=3)
                    intervals=[(start+timedelta(days=delta-4),start+timedelta(days=delta)),(end+timedelta(days=2),end+timedelta(days=5))]
                    def execute(statement, values):
                        if "SELECT TOP 1" in str(statement):
                            return Rows([{"NOME":"Internal match only", "NOITES":minimum}])
                        return Rows([{"DATAIN":a,"DATAOUT":b} for a,b in intervals if a<values['query_end'] and b>values['query_start']])
                    with patch.object(portal,"db",SimpleNamespace(session=SimpleNamespace(execute=execute))):
                        allowed=portal.alojamento_datas_permitidas("fixture",start,end)['allowed']
                    expected=allowed and not any(a<end and b>start for a,b in intervals)
                    with self.subTest(start=start,minimum=minimum,delta=delta):
                        self.assertEqual(maps._date_match(start,end,minimum,intervals,maps._calendar_window(start,end)),expected)


if __name__ == '__main__':
    unittest.main()
