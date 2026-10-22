"""Planning-based AC, inferred weekends, boundary evidence and human edits."""
from copy import deepcopy
from datetime import date
from unittest.mock import patch
import unittest
import uuid

from modules.gr_travel_maps import allowances, config, engine, itinerary, planning, reconstruction, service, sources, store
from tests.test_gr_travel_calendar import graph_fixture, prepared_graph_steps
from tests.test_gr_travel_planning import plan_fixture
from tests.test_gr_travel_reconstruction import fixtures
from tests import test_gr_travel_planning as planning_tests
from tests import test_gr_travel_reconstruction as legacy


class AllowanceCalendarTests(unittest.TestCase):
    def setUp(self):
        self.payroll, self.batches, self.inputs = fixtures()
        self.payroll['map_period'] = config.map_period(2026, 9)
        self.payroll['employee']['phc']['km']['quantity'] = '0'
        self.graph, self.keys = graph_fixture()
        self.plan = plan_fixture({'2026-09-04': 'C', '2026-09-07': 'C'})

    def build(self):
        return itinerary.build(self.payroll, self.batches, self.inputs, self.graph, self.plan)

    def test_friday_monday_same_work_supports_inferred_weekend_and_preserves_sources(self):
        original = deepcopy(self.payroll), deepcopy(self.plan)
        doc = self.build()
        self.assertEqual([e['date'] for e in doc['entries']], [f'2026-09-{d:02}' for d in (4,5,6,7)])
        self.assertEqual(doc['reconciliation']['ac_estrangeiro']['map'], '4')
        for entry in doc['entries']:
            self.assertEqual(entry['evidence_type'], 'INFERIDO')
            if entry['date'] in ('2026-09-05', '2026-09-06'):
                self.assertEqual(entry['confidence']['level'], 'BAIXA')
                self.assertEqual(entry['provenance']['employee_assignment']['kind'], 'INFERIDO')
                self.assertEqual(entry['allowance_basis'], allowances.WEEKEND)
                evidence = entry['provenance']['allowance_calendar']
                self.assertEqual((evidence['friday'], evidence['monday']), ('2026-09-04', '2026-09-07'))
                self.assertEqual({r['date'] for r in evidence['references']}, {'2026-09-04','2026-09-07'})
        self.assertEqual((self.payroll, self.plan), original)
        engine.check_entries(doc, validating=True)

    def test_fifteen_days_use_thirteen_work_days_and_two_weekend_stays(self):
        self.payroll['employee']['phc']['ac_estrangeiro']['quantity'] = '15'
        self.plan = plan_fixture({f'2026-09-{d:02}': 'C' for d in (1,2,3,4,7,8,9,10,11,14,15,16,17)})
        doc = self.build()
        self.assertEqual(doc['reconciliation']['ac_estrangeiro']['map'], '15')
        self.assertEqual(sum(e['allowance_basis']==allowances.WEEKEND for e in doc['entries']), 2)
        self.assertEqual(sum(e['allowance_basis']=='TRABALHO_REGISTADO' for e in doc['entries']), 13)

    def test_shortfall_never_fills_unsupported_weekdays_or_changes_phc(self):
        self.payroll['employee']['phc']['ac_estrangeiro']['quantity'] = '15'
        doc = self.build()
        self.assertEqual(doc['reconciliation']['ac_estrangeiro']['map'], '4')
        self.assertEqual(doc['reconciliation']['ac_estrangeiro']['difference'], '-11')
        self.assertEqual(doc['payroll']['employee']['phc']['ac_estrangeiro']['quantity'], '15')

    def test_actual_work_days_have_priority_and_fractional_target_is_respected(self):
        self.payroll['employee']['phc']['ac_estrangeiro']['quantity'] = '2'
        self.assertEqual([e['date'] for e in self.build()['entries']], ['2026-09-04', '2026-09-07'])
        self.payroll['employee']['phc']['ac_estrangeiro']['quantity'] = '2.5'
        doc = self.build()
        self.assertEqual(doc['reconciliation']['ac_estrangeiro']['map'], '2.5')
        weekend = next(e for e in doc['entries'] if e['allowance_basis']==allowances.WEEKEND)
        self.assertEqual(weekend['quantity'], '0.5')

    def test_missing_different_or_ambiguous_anchors_do_not_create_stays(self):
        for schedule in ({'2026-09-04':'C'}, {'2026-09-07':'C'},
                         {'2026-09-04':'C','2026-09-07':'A'},
                         {'2026-09-04':'AC','2026-09-07':'C'},
                         {'2026-09-04':'C','2026-09-07':'AC'},
                         {'2026-09-04':'C','2026-09-05':'A','2026-09-07':'C'}):
            with self.subTest(schedule=schedule):
                self.plan = plan_fixture(schedule)
                self.assertEqual(self.build()['allowance_calendar']['weekend_days'], 0)

    def test_absences_and_manual_exclusions_override_weekend_continuity(self):
        for blocked in ('2026-09-04','2026-09-05','2026-09-06','2026-09-07'):
            for manual in (False, True):
                with self.subTest(blocked=blocked, manual=manual):
                    self.plan['blocked_dates'] = {} if manual else {blocked:'Ausência'}
                    self.inputs['blocked_dates'] = [blocked] if manual else []
                    doc = self.build()
                    self.assertEqual(doc['allowance_calendar']['weekend_days'], 0)
                    self.assertNotIn(blocked, [e['date'] for e in doc['entries']])

    def test_recorded_weekend_is_work_even_without_friday_and_monday(self):
        self.plan = plan_fixture({'2026-09-05':'C'})
        doc = self.build()
        self.assertEqual([e['date'] for e in doc['entries']], ['2026-09-05'])
        self.assertEqual(doc['entries'][0]['allowance_basis'], 'TRABALHO_REGISTADO')

    def test_direct_weekend_work_does_not_duplicate_inferred_ac(self):
        self.plan = plan_fixture({'2026-09-04':'C','2026-09-05':'C','2026-09-07':'C'})
        doc = self.build()
        self.assertEqual(len(doc['entries']), 4)
        self.assertEqual(doc['allowance_calendar']['weekend_days'], 1)

    def test_national_allowances_use_same_rule_without_granting_weekend_km(self):
        self.plan = plan_fixture({'2026-09-04':'A','2026-09-07':'A'})
        self.payroll['employee']['phc']['ac_estrangeiro']['quantity'] = '0'
        self.payroll['employee']['phc']['ac_nacional']['quantity'] = '4'
        self.inputs['rates']['ac_nacional'] = '50'
        self.payroll['employee']['phc']['km']['quantity'] = '140'
        self.inputs['return_policy'] = 'later'
        doc = self.build()
        self.assertEqual(doc['reconciliation']['km']['map'], '140')
        self.assertEqual(doc['reconciliation']['ac_nacional']['map'], '4')
        self.assertEqual({e['date'] for e in doc['entries'] if e['category']=='km'}, {'2026-09-04','2026-09-07'})
        weekend = [day for day in itinerary.calendar(doc) if day['date'] in ('2026-09-05','2026-09-06')]
        self.assertTrue(all(not d['available'] and d['allowance_available'] for d in weekend))
        engine.check_entries(doc, validating=True)

    def test_return_home_friday_and_departure_monday_prevent_weekend_stay(self):
        self.plan = plan_fixture({'2026-09-04':'A','2026-09-07':'A'})
        self.payroll['employee']['phc']['ac_estrangeiro']['quantity'] = '0'
        self.payroll['employee']['phc']['ac_nacional']['quantity'] = '4'
        self.payroll['employee']['phc']['km']['quantity'] = '280'
        self.inputs['return_policy'] = 'same_day'
        doc = self.build()
        self.assertEqual(doc['reconciliation']['km']['map'], '280')
        self.assertEqual(doc['reconciliation']['ac_nacional']['map'], '2')
        self.assertEqual(doc['allowance_calendar']['weekend_days'], 0)

    def test_human_date_edits_recheck_eligibility_and_preserve_audit(self):
        self.payroll['employee']['phc']['ac_estrangeiro']['quantity'] = '2'
        doc = self.build(); before = deepcopy(doc)
        entry = doc['entries'][0]
        with self.assertRaises(config.TravelMapsError):
            engine.edit(doc, [{'id':entry['id'],'date':'2026-09-08'}], 'user', 'Revisão')
        edited = engine.edit(doc, [{'id':entry['id'],'date':'2026-09-05'}], 'user', 'Revisão')
        changed = next(e for e in edited['entries'] if e['id']==entry['id'])
        self.assertEqual(changed['allowance_basis'], allowances.WEEKEND)
        self.assertEqual(changed['provenance']['date']['kind'], 'DECLARADO')
        self.assertEqual(changed['provenance']['human_changes'][0]['before'], '2026-09-04')
        restored = engine.edit(edited, [{'id':entry['id'],'date':'2026-09-04'}], 'user', 'Corrigir')
        restored_entry = next(e for e in restored['entries'] if e['id']==entry['id'])
        self.assertEqual(restored_entry['allowance_basis'], 'TRABALHO_REGISTADO')
        self.assertNotIn('Permanência', restored_entry['reason'])
        self.assertFalse(any('AC de fim de semana:' in w for w in restored['warnings']))
        self.assertEqual(doc, before)

    def test_validation_derives_rules_again_and_rejects_forged_provenance(self):
        doc = self.build()
        entry = next(e for e in doc['entries'] if e['allowance_basis']==allowances.WEEKEND)
        entry['date'] = '2026-09-08'
        with self.assertRaises(config.TravelMapsError):
            engine.check_entries(doc, validating=True)

    def test_review_preserves_human_reason_and_does_not_upgrade_inferred_evidence(self):
        doc = self.build()
        entry = next(e for e in doc['entries'] if e['allowance_basis']==allowances.WEEKEND)
        edited = engine.edit(doc, [{'id':entry['id'],'reason':'Permanência confirmada pelo colaborador'}], 'reviewer', 'Conferência')
        changed = next(e for e in edited['entries'] if e['id']==entry['id'])
        self.assertEqual(changed['reason'], 'Permanência confirmada pelo colaborador')
        self.assertEqual(changed['evidence_type'], 'INFERIDO')
        self.assertEqual(changed['provenance']['reason']['kind'], 'DECLARADO')
        self.assertEqual(changed['provenance']['allowance_calendar']['kind'], 'INFERIDO')

    def test_other_team_records_do_not_create_ac_dates(self):
        self.plan = plan_fixture({'2026-09-01':'C'})
        self.plan['extra_records'] = plan_fixture({'2026-09-04':'C','2026-09-07':'C'})['records']
        self.assertEqual([e['date'] for e in self.build()['entries']], ['2026-09-01'])

    def test_boundary_friday_is_evidence_only_and_context_absence_blocks_stay(self):
        self.plan = plan_fixture({'2026-08-24':'C'})
        self.plan['context_records'] = plan_fixture({'2026-08-21':'C'})['records']
        doc = self.build()
        self.assertEqual([e['date'] for e in doc['entries']], ['2026-08-22','2026-08-23','2026-08-24'])
        self.plan['context_blocked_dates'] = {'2026-08-21':'Ausência'}
        self.assertEqual([e['date'] for e in self.build()['entries']], ['2026-08-24'])

    def test_boundary_monday_is_evidence_only(self):
        self.payroll.update(year=2026,month=6,map_period=config.map_period(2026,6))
        self.plan = plan_fixture({'2026-06-19':'C'})
        self.plan['context_records'] = plan_fixture({'2026-06-22':'C'})['records']
        doc = self.build()
        self.assertEqual([e['date'] for e in doc['entries']], ['2026-06-19','2026-06-20','2026-06-21'])

    def test_legacy_policy_does_not_silently_enable_weekend_eligibility(self):
        doc = self.build()
        del doc['allowance_policy']
        self.assertEqual(set(allowances.eligible(doc)), {'2026-09-04','2026-09-07'})
        with self.assertRaises(config.TravelMapsError):
            engine.check_entries(doc, validating=True)


class WeekendSourceTests(unittest.TestCase):
    setUp = planning_tests.SourceAssemblyTests.setUp

    def build(self):
        return planning.assemble(self.payroll, self.batches, self.data, self.catalogs)

    def test_only_required_anchor_dates_extend_employee_queries(self):
        def rows(cursor, sql, params):
            if 'dbo.V_PE' in sql:
                return [{'BDADOS':self.payroll['company']['phc_db'], 'PESTAMP':self.payroll['employee']['pestamp']}]
            return []
        for month, start, end in ((9,date(2026,8,21),date(2026,9,22)),
                                  (6,date(2026,5,22),date(2026,6,23)),
                                  (3,date(2026,2,20),date(2026,3,24))):
            with self.subTest(month=month):
                self.payroll.update(month=month,map_period=config.map_period(2026,month))
                with patch.object(planning,'reader'), patch.object(sources,'rows',side_effect=rows) as read:
                    result = planning.read_rows(self.payroll,weekend_context=True)
                self.assertEqual(result['weekend_context'], {'start':start.isoformat(),'end_exclusive':end.isoformat()})
                calls = [call for call in read.call_args_list if 'dbo.V_PE' not in call.args[1]]
                self.assertEqual(len(calls), 4)
                for i, call in enumerate(calls):
                    bounds = config.map_bounds(self.payroll) if i == 2 else (start,end)
                    self.assertTrue(all(d in call.args[2] for d in bounds))

    def test_context_records_are_separate_and_source_changes_invalidate_validation(self):
        self.payroll['map_period'] = config.map_period(2026,9)
        self.data['weekend_context'] = {'start':'2026-08-21','end_exclusive':'2026-09-22'}
        self.data['assignments'][0]['DATA'] = date(2026,8,24)
        self.data['assignments'].append(dict(self.data['assignments'][0],DATA=date(2026,8,21),U_PLANOSTAMP='OUTSIDE'))
        first = self.build()
        self.assertEqual([r['date'] for r in first['records']], ['2026-08-24'])
        self.assertEqual([r['date'] for r in first['context_records']], ['2026-08-21'])
        self.assertEqual(first['days_with_assignments'], 1)
        self.data['absences'] = [{'U_AUSENCIASSTAMP':'ABS','DATAINI':date(2026,8,21),'DATAFIM':date(2026,8,21)}]
        changed = self.build()
        self.assertNotEqual(changed['fingerprint'], first['fingerprint'])
        self.assertEqual(changed['context_records'], [])
        self.assertIn('2026-08-21', changed['context_blocked_dates'])
        doc = {'payroll':self.payroll,'planning':first,'measurements':self.batches}
        with patch.object(reconstruction,'payroll_snapshot',return_value=self.payroll), \
             patch.object(planning,'snapshot',return_value=changed) as snapshot:
            with self.assertRaises(store.Conflict):
                reconstruction.ensure_sources_current(doc, object())
        self.assertTrue(snapshot.call_args.kwargs['weekend_context'])

    def test_absent_membership_blocks_weekend_without_a_planning_row(self):
        self.data['weekend_context'] = {'start':'2026-09-01','end_exclusive':'2026-10-01'}
        self.data['memberships'].append({'U_TEAMSTAMP':'ABSENT','AUSENTE':True,
                                       'DATAINI':date(2026,9,5),'DATAFIM':date(2026,9,6)})
        result = self.build()
        self.assertIn('2026-09-05', result['blocked_dates'])
        self.assertIn('2026-09-06', result['blocked_dates'])
        self.assertNotIn('2026-09-07', result['blocked_dates'])


class WeekendWorkflowTests(unittest.TestCase):
    setUp = legacy.WorkflowTests.setUp
    post = legacy.WorkflowTests.post

    def test_validation_keeps_weekend_evidence_and_immutable_initial_version(self):
        self.payroll['employee']['phc']['km']['quantity'] = '0'
        plan = plan_fixture({'2026-09-04':'C','2026-09-07':'C'})
        payload = {'mode':'AUTOMATIC','feid':2,'year':2026,'month':9,
                   'employee_key':self.payroll['employee']['key'],'measurement_companies':[1,2],
                   'inputs':self.inputs,'reason':'Reconstrução','expected_version':0,'request_id':str(uuid.uuid4())}
        with patch.object(planning,'snapshot',return_value=plan), \
             patch.object(reconstruction.distances,'prepare_steps',side_effect=prepared_graph_steps):
            response = self.post('propostas', payload)
            self.assertEqual(response.status_code, 200, response.json)
            created = response.json; map_id = created['header']['id']
            response = self.post(f'propostas/{map_id}/validar', {'expected_version':1,'request_id':str(uuid.uuid4()),
                                'reason':'Permanência confirmada','acknowledge_inference':True})
        self.assertEqual(response.status_code, 200, response.json)
        doc = response.json['current']['document']
        weekend = [e for e in doc['entries'] if e.get('allowance_basis')==allowances.WEEKEND]
        self.assertEqual(len(weekend), 2)
        self.assertTrue(all(e['evidence_type']=='INFERIDO' and e['validation_state']=='VALIDADO' for e in weekend))
        self.assertEqual(store.get(self.db_engine,map_id,1)['current']['document'], created['current']['document'])
        self.assertEqual(len(store.history(self.db_engine,map_id)), 2)


if __name__ == '__main__':
    unittest.main()
