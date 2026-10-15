from copy import deepcopy
from datetime import date
from decimal import Decimal
import unittest
import uuid
from unittest.mock import patch

from modules.gr_travel_maps import engine, itinerary, planning, reconstruction, scheduled, store
from modules.gr_travel_maps.config import TravelMapsError
from tests.test_gr_travel_calendar import graph_fixture, prepared_graph_steps
from tests.test_gr_travel_reconstruction import fixtures
from tests import test_gr_travel_reconstruction as legacy


def plan_fixture(schedule):
    _, batches, _ = fixtures()
    works = engine.candidates(batches)
    keys = {w['work']: w['key'] for w in works}
    records = [{'date': day, 'team': 'EQ1', 'work_key': keys[work],
                'sources': [{'database': 'HSOLS_MASTER', 'table': 'U_PLANO', 'stamp': day+work},
                            {'database': 'HSOLS_MASTER', 'table': 'U_TEAM', 'stamp': 'TEAM1'}]}
               for day, codes in schedule.items() for work in codes]
    works = [dict(w, planning_refs=[r for r in records if r['work_key']==w['key']])
             for w in works if w['key'] in {r['work_key'] for r in records}]
    return {'works': works, 'records': records, 'blocked_dates': {}, 'warnings': [],
            'days_with_assignments': len(schedule), 'fingerprint': engine.digest(records)}


def extra_plan_fixture():
    plan = plan_fixture({f'2026-09-{day:02}': 'A' for day in (1, 2, 3, 4, 7, 8, 9, 10, 11)})
    other = plan_fixture({row['date']: 'B' for row in plan['records']})
    plan['extra_records'] = [dict(row, team='OUTRA', sources=[ref for ref in row['sources'] if ref['table']!='U_TEAM']) for row in other['records']]
    plan['extra_works'] = [dict(work, hypothetical=True, planning_refs=plan['extra_records']) for work in other['works']]
    return plan


class ScheduledTests(unittest.TestCase):
    def setUp(self):
        self.payroll, self.batches, self.inputs = fixtures()
        self.graph, self.keys = graph_fixture()

    def build(self, plan):
        keys = {'home', *(w['key'] for w in plan['works']+plan.get('extra_works', []))}
        graph = deepcopy(self.graph)
        graph['locations'] = {key: point for key, point in graph['locations'].items() if key in keys}
        return itinerary.build(self.payroll, self.batches, self.inputs, graph, plan)

    def test_only_recorded_work_dates_are_used_and_source_is_preserved(self):
        plan = plan_fixture({'2026-09-01': 'A', '2026-09-03': 'B', '2026-09-10': 'A'})
        doc = self.build(plan)
        daily = scheduled.assignments(plan)
        for entry in doc['entries']:
            self.assertIn(entry['work_key'], daily[entry['date']])
            self.assertEqual(entry['evidence_type'], 'INFERIDO')
            self.assertEqual(entry['provenance']['employee_assignment']['kind'], 'PLANEAMENTO')
        self.assertEqual(doc['planning'], plan)
        self.assertEqual(doc['payroll'], self.payroll)

    def test_missing_planning_does_not_fall_back_to_arbitrary_measured_works(self):
        doc = self.build(plan_fixture({}))
        self.assertEqual(doc['entries'], [])
        self.assertEqual(doc['reconciliation']['km']['map'], '0')
        self.assertEqual(doc['result']['status'], 'BLOCKED')

    def test_planned_weekend_is_a_real_candidate_without_enabling_invented_days(self):
        self.payroll['employee']['phc']['km']['quantity'] = '140'
        doc = self.build(plan_fixture({'2026-09-05': 'A'}))
        self.assertEqual({e['date'] for e in doc['entries']}, {'2026-09-05'})
        self.assertEqual(doc['reconciliation']['km']['map'], '140')

    def test_explicit_exclusions_and_planning_absences_override_assignments(self):
        plan = plan_fixture({'2026-09-01': 'A', '2026-09-02': 'A'})
        self.inputs['blocked_dates'] = ['2026-09-01']
        plan['blocked_dates'] = {'2026-09-02': 'Ausência'}
        self.assertEqual(self.build(plan)['entries'], [])

    def test_foreign_allowances_cannot_exceed_recorded_foreign_dates(self):
        plan = plan_fixture({'2026-09-01': 'A', '2026-09-02': 'C', '2026-09-03': 'C'})
        doc = self.build(plan)
        foreign = [e for e in doc['entries'] if e['category']=='ac_estrangeiro']
        self.assertEqual([e['date'] for e in foreign], ['2026-09-02', '2026-09-03'])
        self.assertEqual(doc['reconciliation']['ac_estrangeiro']['difference'], '-2')

    def test_local_transfer_follows_chronological_work_changes_and_delayed_return(self):
        self.payroll['employee']['phc']['km']['quantity'] = '8'
        doc = self.build(plan_fixture({'2026-09-01': 'A', '2026-09-02': 'B', '2026-09-03': 'A'}))
        legs = [e for e in doc['entries'] if e['category']=='km']
        self.assertEqual(doc['reconciliation']['km']['map'], '8')
        self.assertEqual([(e['from_label'], e['to_label'], e['date']) for e in legs],
                         [('A', 'B', '2026-09-02'), ('B', 'A', '2026-09-03')])

    def test_unknown_workday_gap_cannot_be_used_to_invent_a_local_start(self):
        self.payroll['employee']['phc']['km']['quantity'] = '8'
        doc = self.build(plan_fixture({'2026-09-01': 'A', '2026-09-10': 'B', '2026-09-11': 'A'}))
        self.assertEqual(doc['reconciliation']['km']['map'], '0')

    def test_return_cannot_bridge_another_work_or_an_absence(self):
        plan = plan_fixture({'2026-09-01': 'A', '2026-09-02': 'B', '2026-09-03': 'A'})
        path = ['home', self.keys['A'], 'home']
        self.assertFalse(scheduled.compatible(path, ['2026-09-01', '2026-09-03'], 1, plan, set()))
        plan = plan_fixture({'2026-09-01': 'A', '2026-09-02': 'A', '2026-09-03': 'A'})
        self.assertFalse(scheduled.compatible(path, ['2026-09-01', '2026-09-03'], 1, plan, {'2026-09-02'}))

    def test_human_date_edit_cannot_move_trip_to_another_work_day(self):
        self.payroll['employee']['phc']['km']['quantity'] = '140'
        doc = self.build(plan_fixture({'2026-09-01': 'A', '2026-09-02': 'B'}))
        changes = [{'id': e['id'], 'date': '2026-09-02'} for e in doc['entries'] if e['category']=='km']
        with self.assertRaises(TravelMapsError):
            engine.edit(doc, changes, 'reviewer', 'Alteração de data')

    def test_work_without_auto_remains_planned_and_is_not_labelled_production(self):
        plan = plan_fixture({'2026-09-01': 'A'})
        plan['works'][0]['evidence'] = []
        self.payroll['employee']['phc']['km']['quantity'] = '140'
        doc = self.build(plan)
        self.assertEqual(doc['reconciliation']['km']['map'], '140')
        self.assertEqual(doc['entries'][0]['provenance']['work']['kind'], 'PLANEAMENTO')

    def test_other_team_visits_are_hypotheses_with_original_own_team_unchanged(self):
        plan = extra_plan_fixture(); before = deepcopy(plan)
        self.payroll['employee']['phc']['km']['quantity'] = '16'
        doc = self.build(plan)
        self.assertEqual(doc['reconciliation']['km']['map'], '16')
        self.assertEqual(len(doc['journeys']), 2)
        self.assertEqual(plan, before)
        for entry in doc['entries']:
            self.assertTrue(entry['hypothesis'])
            self.assertEqual(entry['evidence_type'], 'INFERIDO')
            self.assertEqual(entry['confidence']['level'], 'BAIXA')
            provenance = entry['provenance']['employee_assignment']
            self.assertEqual(provenance['kind'], 'INFERIDO')
            self.assertEqual(provenance['own_team_references'][0]['team'], 'EQ1')
            self.assertEqual(provenance['other_team_references'][0]['team'], 'OUTRA')
            self.assertEqual(entry['quantity'], entry['provenance']['distance']['km'])
        dates = sorted({entry['date'] for entry in doc['entries']})
        self.assertGreater((date.fromisoformat(dates[1])-date.fromisoformat(dates[0])).days, 1)
        edited = engine.edit(doc, [{'id':doc['entries'][0]['id'],'reason':'Entrega de ferramentas confirmada'}], 'user', 'Revisão')
        self.assertEqual(next(e for e in edited['entries'] if e['id']==doc['entries'][0]['id'])['reason'], 'Entrega de ferramentas confirmada')

    def test_other_team_visits_require_same_day_assignment_and_return_to_own_work(self):
        plan = extra_plan_fixture()
        a, b = self.keys['A'], self.keys['B']
        self.assertTrue(scheduled.compatible([a,b,a], ['2026-09-01'], 2, plan, set()))
        self.assertFalse(scheduled.compatible([a,b,a], ['2026-09-01','2026-09-02'], 1, plan, set()))
        plan['extra_records'] = []
        self.assertFalse(scheduled.compatible([a,b,a], ['2026-09-01'], 2, plan, set()))

    def test_large_foreign_trip_is_split_across_consecutive_days_with_exact_km(self):
        self.payroll['employee']['phc']['km']['quantity'] = '3000'
        plan = plan_fixture({f'2026-09-{day:02}': 'C' for day in range(1, 11)})
        doc = self.build(plan)
        legs = [e for e in doc['entries'] if e['category']=='km']
        self.assertEqual(doc['reconciliation']['km']['map'], '3000')
        self.assertEqual(len(doc['journeys']), 1)
        self.assertEqual(len(legs), 2)
        self.assertEqual(doc['journeys'][0]['outbound_date'], '2026-09-01')
        self.assertEqual(doc['journeys'][0]['return_date'], '2026-09-10')
        self.assertTrue(all('2026-09-03'<=e['date']<='2026-09-08' for e in doc['entries'] if e['category']!='km'))
        for leg in legs:
            self.assertTrue(leg['hypothesis'])
            self.assertEqual(len(leg['driving_dates']), 3)
            self.assertEqual(sum(map(Decimal, leg['daily_km'].values())), Decimal(leg['quantity']))
            self.assertLessEqual(Decimal(leg['provenance']['distance']['seconds'])/len(leg['driving_dates']), 36000)
        self.assertEqual(sum(Decimal(day['km']) for day in itinerary.calendar(doc)), 3000)
        engine.check_entries(doc, validating=True)
        changed=engine.edit(doc, [{'id':legs[0]['id'], 'reason':'Viagem confirmada pelo trabalhador'}], 'user', 'Revisão')
        self.assertEqual(next(e for e in changed['entries'] if e['id']==legs[0]['id'])['start_date'], legs[0]['start_date'])
        with self.assertRaises(TravelMapsError):
            engine.edit(doc, [{'id':legs[0]['id'], 'date':'2026-09-01'}], 'user', 'Revisão')
        with self.assertRaises(TravelMapsError):
            engine.edit(doc, [{'id':legs[0]['id'], 'quantity':'1'}], 'user', 'Revisão')

    def test_long_trip_respects_unknown_days_absences_and_return_policy(self):
        self.payroll['employee']['phc']['km']['quantity'] = '3000'
        plan = plan_fixture({f'2026-09-{day:02}': 'C' for day in (1,2,3,4,7,8)})
        self.assertEqual(self.build(plan)['reconciliation']['km']['map'], '0')
        plan = plan_fixture({f'2026-09-{day:02}': 'C' for day in range(1,7)})
        plan['blocked_dates'] = {'2026-09-03':'Ausência'}
        self.assertEqual(self.build(plan)['reconciliation']['km']['map'], '0')
        plan['blocked_dates'] = {}; self.inputs['return_policy'] = 'same_day'
        self.assertEqual(self.build(plan)['reconciliation']['km']['map'], '0')

    def test_low_payroll_does_not_force_international_trip(self):
        self.payroll['employee']['phc']['km']['quantity'] = '446'
        plan = plan_fixture({f'2026-09-{day:02}': 'C' for day in range(1,11)})
        self.assertEqual(self.build(plan)['reconciliation']['km']['map'], '0')


class SourceAssemblyTests(unittest.TestCase):
    def setUp(self):
        self.payroll, self.batches, _ = fixtures()
        self.data = {'memberships': [{'U_TEAMSTAMP':'T1','ORIGEM':'HSOLS_PT','NO':'12','AUSENTE':False}],
                     'assignments': [{'DATA':date(2026,9,1),'FREF':'EQ1','U_TEAMSTAMP':'T1',
                        'U_PLANOSTAMP':'P1','OPCSTAMP':'SHARED','WORK_MATCHES':1,'PROCESSO':'HS1822'}],
                     'absences': [], 'absence_identity_unique': True}
        self.catalogs = [{'company':self.payroll['company'], 'rows':[{'OPCSTAMP':'SHARED','PROCESSO':'PT1822',
                         'NOME':'Cliente','MORADA':'Rua','LOCALIDADE':'Lyon'}]}]

    def build(self):
        return planning.assemble(self.payroll, self.batches, self.data, self.catalogs)

    def test_different_codes_join_by_stamp_without_fabricating_an_auto(self):
        result = self.build()
        self.assertEqual(result['works'][0]['work'], 'PT1822')
        self.assertEqual(result['works'][0]['planning_work'], 'HS1822')
        self.assertEqual(result['works'][0]['evidence'], [])
        self.assertTrue(any('sem auto positivo' in warning for warning in result['warnings']))

    def test_same_number_suffix_with_different_stamp_never_matches(self):
        self.catalogs[0]['rows'][0]['OPCSTAMP']='DIFFERENT'
        result=self.build()
        self.assertEqual(result['records'], [])
        self.assertIn('2026-09-01', result['blocked_dates'])

    def test_shared_stamp_copies_in_two_companies_create_one_work(self):
        other = deepcopy(self.catalogs[0]);other['company'] = {'feid':1,'name':'FR','phc_db':'HSOLS_FR'}
        other['rows'][0]['PROCESSO'] = 'HS1822'
        self.catalogs.append(other)
        self.assertEqual(len(self.build()['works']), 1)

    def test_ambiguous_team_memberships_are_excluded(self):
        self.data['memberships'].append({'U_TEAMSTAMP':'T2','AUSENTE':False})
        other = deepcopy(self.data['assignments'][0]);other.update(U_TEAMSTAMP='T2',FREF='EQ2')
        self.data['assignments'].append(other)
        self.assertEqual(self.build()['records'], [])

    def test_absence_and_absent_membership_exclude_the_day(self):
        self.data['absences']=[{'U_AUSENCIASSTAMP':'ABS1','DATAINI':date(2026,9,1),'DATAFIM':date(2026,9,1)}]
        self.assertEqual(self.build()['records'], [])
        self.data['absences']=[];self.data['memberships'][0]['AUSENTE']=True
        self.assertEqual(self.build()['records'], [])

    def test_source_changes_change_fingerprint_but_read_time_does_not(self):
        first=self.build()
        self.assertEqual(first['fingerprint'], self.build()['fingerprint'])
        self.data['assignments'][0]['DATA']=date(2026,9,2)
        self.assertNotEqual(first['fingerprint'], self.build()['fingerprint'])

    def test_other_team_candidates_only_on_own_dates_in_authorized_catalog(self):
        row = {'DATA':date(2026,9,1),'FREF':'EQ2','U_PLANOSTAMP':'P2','OPCSTAMP':'OTHER','WORK_MATCHES':1,'PROCESSO':'HS1970'}
        self.data['other_assignments'] = [row, dict(row, DATA=date(2026,9,2)), dict(row, OPCSTAMP='UNAUTHORIZED')]
        self.catalogs[0]['rows'].append({'OPCSTAMP':'OTHER','PROCESSO':'PT1970','NOME':'Outro','MORADA':'Rua','LOCALIDADE':'Lyon'})
        result = self.build()
        self.assertEqual(len(result['extra_records']), 1)
        self.assertEqual(result['extra_records'][0]['team'], 'EQ2')
        self.assertEqual(result['extra_records'][0]['date'], '2026-09-01')
        self.assertEqual(result['works'][0]['work'], 'PT1822')
        self.assertEqual(result['extra_works'][0]['work'], 'PT1970')
        self.assertTrue(result['extra_works'][0]['hypothetical'])


class PlanningWorkflowTests(unittest.TestCase):
    setUp=legacy.WorkflowTests.setUp
    post=legacy.WorkflowTests.post

    def test_hypotheses_need_confirmation_and_validation_keeps_inference_and_history(self):
        self.payroll['employee']['phc']['km']['quantity']='8'
        plan=extra_plan_fixture()
        payload={'mode':'AUTOMATIC','feid':2,'year':2026,'month':9,'employee_key':self.payroll['employee']['key'],
                 'measurement_companies':[1,2],'inputs':self.inputs,'reason':'Proposta','expected_version':0,'request_id':str(uuid.uuid4())}
        with patch.object(planning,'snapshot',return_value=plan), patch.object(reconstruction.distances,'prepare_steps',side_effect=prepared_graph_steps):
            created=self.post('propostas',payload).json
            map_id=created['header']['id']
            body={'expected_version':1,'request_id':str(uuid.uuid4()),'reason':'Confirmação humana','acknowledge_inference':True}
            rejected=self.post(f'propostas/{map_id}/validar',body)
            self.assertEqual(rejected.status_code,400,rejected.json)
            self.assertIn('hipóteses',rejected.json['error'])
            self.assertEqual(len(store.history(self.db_engine,map_id)),1)
            accepted=self.post(f'propostas/{map_id}/validar',{**body,'confirm_hypothetical_travel':True})
        self.assertEqual(accepted.status_code,200,accepted.json)
        doc=accepted.json['current']['document']
        self.assertTrue(doc['validation']['confirmed_hypothetical_entries'])
        self.assertTrue(all(e['evidence_type']=='INFERIDO' for e in doc['entries']))
        self.assertEqual(store.get(self.db_engine,map_id,1)['current']['document'],created['current']['document'])

    def test_server_planning_wins_over_client_and_changed_planning_blocks_validation(self):
        plan=plan_fixture({'2026-09-01':'A', '2026-09-02':'B'})
        payload={'mode':'AUTOMATIC','feid':2,'year':2026,'month':9,'employee_key':self.payroll['employee']['key'],
                 'measurement_companies':[1,2],'inputs':self.inputs,'reason':'Planeamento','expected_version':0,
                 'request_id':str(uuid.uuid4()), 'planning':{'records':[{'date':'2026-09-20'}]}}
        with patch.object(planning,'snapshot',return_value=plan), patch.object(reconstruction.distances,'prepare_steps',side_effect=prepared_graph_steps):
            response=self.post('propostas',payload)
        self.assertEqual(response.status_code,200,response.json)
        self.assertEqual(response.json['current']['document']['planning'],plan)
        changed=deepcopy(plan);changed['fingerprint']='changed'
        with patch.object(planning,'snapshot',return_value=changed):
            result=self.post(f"propostas/{response.json['header']['id']}/validar",{'expected_version':1,
                'request_id':str(uuid.uuid4()),'reason':'Revisão','acknowledge_inference':True})
        self.assertEqual(result.status_code,409,result.json)
        self.assertIn('planeamento mudaram',result.json['error'])
        self.assertEqual(len(store.history(self.db_engine,response.json['header']['id'])),1)


if __name__=='__main__':unittest.main()
