"""22–21 operational cycles, monthly PHC totals, and immutable old versions."""
from copy import deepcopy
from datetime import date
from unittest.mock import MagicMock, patch
import unittest
import uuid

from flask import Flask

from modules.gr_travel_maps import config, engine, itinerary, planning, reconstruction, service, sources, store
from tests.test_gr_travel_calendar import graph_fixture
from tests.test_gr_travel_planning import plan_fixture
from tests.test_gr_travel_reconstruction import fixtures
from tests import test_gr_travel_reconstruction as legacy
from tests.test_gr_travel_maps import COMPANY, salary_line


class PeriodTests(unittest.TestCase):
    def setUp(self):
        self.payroll, self.batches, self.inputs = fixtures()
        self.payroll['map_period'] = config.map_period(2026, 9)

    def test_inclusive_cycle_and_payroll_month_are_distinct(self):
        self.assertEqual(config.map_period(2026, 9), {'basis':'22_21','start':'2026-08-22','end':'2026-09-21'})
        self.assertEqual(config.map_bounds(self.payroll), (date(2026,8,22), date(2026,9,22)))
        self.assertEqual(config.period_bounds(2026,9), (date(2026,9,1),date(2026,10,1)))

    def test_january_and_leap_year_calendars(self):
        for year, month, first, last, count in [(2026,1,'2025-12-22','2026-01-21',31),
                (2024,3,'2024-02-22','2024-03-21',29), (2026,3,'2026-02-22','2026-03-21',28)]:
            with self.subTest(year=year,month=month):
                self.payroll.update(year=year,month=month,map_period=config.map_period(year,month))
                doc=itinerary.build(self.payroll,self.batches,self.inputs,graph_fixture()[0])
                days=itinerary.calendar(doc)
                self.assertEqual((days[0]['date'],days[-1]['date'],len(days)),(first,last,count))
                self.assertEqual(doc['payroll']['employee']['phc'],self.payroll['employee']['phc'])

    def test_planning_and_allowances_use_both_months_but_not_the_next_cycle(self):
        self.payroll['employee']['phc']['km']['quantity']='0'
        plan=plan_fixture({'2026-08-21':'C','2026-08-22':'C','2026-08-31':'C',
                           '2026-09-01':'C','2026-09-21':'C','2026-09-22':'C'})
        doc=itinerary.build(self.payroll,self.batches,self.inputs,graph_fixture()[0],plan)
        self.assertEqual([e['date'] for e in doc['entries']],['2026-08-22','2026-08-31','2026-09-01','2026-09-21'])
        days=itinerary.calendar(doc)
        self.assertEqual((days[0]['date'],days[-1]['date'],len(days)),('2026-08-22','2026-09-21',31))
        self.assertEqual(doc['reconciliation']['ac_estrangeiro']['map'],'4')

    def test_km_can_fall_on_august_22_and_september_21(self):
        self.payroll['employee']['phc']['km']['quantity']='280'
        self.payroll['employee']['phc']['ac_estrangeiro']['quantity']='0'
        plan=plan_fixture({'2026-08-22':'A','2026-09-21':'A','2026-09-22':'A'})
        doc=itinerary.build(self.payroll,self.batches,self.inputs,graph_fixture()[0],plan)
        self.assertEqual({e['date'] for e in doc['entries']},{'2026-08-22','2026-09-21'})
        self.assertEqual(doc['reconciliation']['km']['map'],'280')
        engine.check_entries(doc,validating=True)
        with self.assertRaises(config.TravelMapsError):
            engine.edit(doc,[{'id':e['id'],'date':'2026-09-22'} for e in doc['entries']],'user','Alteração')

    def test_exclusions_and_absences_cover_previous_month(self):
        self.payroll['employee']['phc']['km']['quantity']='0'
        plan=plan_fixture({'2026-08-24':'C','2026-08-25':'C','2026-09-21':'C'})
        self.inputs['blocked_dates']=['2026-08-24']
        plan['blocked_dates']={'2026-08-25':'Ausência'}
        doc=itinerary.build(self.payroll,self.batches,self.inputs,graph_fixture()[0],plan)
        self.assertEqual([e['date'] for e in doc['entries']],['2026-09-21'])
        self.inputs['blocked_dates']=['2026-09-22']
        with self.assertRaises(config.TravelMapsError):
            itinerary.build(self.payroll,self.batches,self.inputs,graph_fixture()[0],plan)

    def test_old_documents_keep_calendar_month(self):
        del self.payroll['map_period']
        doc=itinerary.build(self.payroll,self.batches,self.inputs,graph_fixture()[0])
        days=itinerary.calendar(doc)
        self.assertEqual((days[0]['date'],days[-1]['date'],len(days)),('2026-09-01','2026-09-30',30))
        self.assertNotIn('map_period',doc['payroll'])

    def test_source_queries_use_cycle_for_autos_but_salary_month_for_phc(self):
        with Flask(__name__).app_context(), patch.object(service,'company_for_user',return_value=COMPANY), \
             patch.object(sources,'payroll_rows',return_value=[salary_line()]) as salary, \
             patch.object(sources,'measurement_rows',return_value=([],[])) as autos:
            panel=service.monthly_panel(2,2026,9,object())
            service.monthly_measurements(2,2026,9,object())
        self.assertEqual(salary.call_args.args[1:3],(date(2026,9,1),date(2026,10,1)))
        self.assertEqual(autos.call_args.args[1:3],(date(2026,8,22),date(2026,9,22)))
        self.assertEqual((panel['year'],panel['month']), (2026,9))
        self.assertEqual(panel['map_period'], self.payroll['map_period'])
        self.assertEqual(panel['totals']['km']['quantity'],'684')

    def test_all_planning_queries_use_cycle_bounds_including_absences(self):
        def rows(cursor,sql,params):
            if 'dbo.V_PE' in sql:
                return [{'BDADOS':self.payroll['company']['phc_db'],'PESTAMP':self.payroll['employee']['pestamp']}]
            return []
        with patch.object(planning,'reader') as reader, patch.object(sources,'rows',side_effect=rows) as read:
            reader.return_value.__enter__.return_value=MagicMock()
            planning.read_rows(self.payroll)
        dated=[call for call in read.call_args_list if 'dbo.V_PE' not in call.args[1]]
        self.assertEqual(len(dated),4)
        for call in dated:
            sql,params=call.args[1:]
            self.assertIn(date(2026,8,22),params)
            self.assertIn(date(2026,9,22),params)
            self.assertNotIn(date(2026,10,1),params)


class PeriodWorkflowTests(unittest.TestCase):
    setUp=legacy.WorkflowTests.setUp
    post=legacy.WorkflowTests.post

    def test_regeneration_adds_cycle_without_rewriting_old_version_or_month_identity(self):
        old=engine.build(self.payroll,self.batches,self.inputs)
        first=store.append(self.db_engine,old,action='GENERATE',state='POR_VALIDAR',actor='reviewer',user_stamp='US1',
                           reason='Versão anterior',expected_version=0,request_id=str(uuid.uuid4()),request_hash='a'*64)
        payload={'feid':2,'year':2026,'month':9,'employee_key':self.payroll['employee']['key'],
                 'measurement_companies':[1,2],'inputs':self.inputs,'expected_version':1,
                 'reason':'Ciclo 22–21','request_id':str(uuid.uuid4()),
                 'map_period':{'start':'2026-09-01','end':'2026-09-30'}}
        response=self.post('propostas',payload)
        self.assertEqual(response.status_code,200,response.json)
        saved=response.json; doc=saved['current']['document']
        self.assertEqual(saved['header']['id'],first['header']['id'])
        self.assertEqual((saved['header']['year'],saved['header']['month']),(2026,9))
        self.assertEqual(doc['payroll']['map_period'],config.map_period(2026,9))
        self.assertTrue(all('2026-08-22'<=entry['date']<='2026-09-21' for entry in doc['entries']))
        self.assertEqual(store.get(self.db_engine,first['header']['id'],1)['current']['document'],old)
        monthly=self.client.get('/api/gr_mapas/propostas?feid=2&ano=2026&mes=9').json
        self.assertEqual(monthly['rows'][0]['map_period'],config.map_period(2026,9))

    def test_validation_rereads_the_version_period_and_keeps_phc_fingerprint(self):
        for modern in (False,True):
            with self.subTest(modern=modern):
                payroll=deepcopy(self.payroll)
                if modern:payroll['map_period']=config.map_period(2026,9)
                plan=plan_fixture({'2026-09-01':'A'})
                doc=itinerary.build(payroll,self.batches,self.inputs,graph_fixture()[0],plan)
                current={**deepcopy(self.payroll),'map_period':config.map_period(2026,9)}
                with patch.object(reconstruction,'payroll_snapshot',return_value=current), \
                     patch.object(planning,'snapshot',return_value=plan) as read_plan, \
                     patch.object(service,'monthly_measurements',side_effect=lambda feid,*args:deepcopy(next(b for b in self.batches if b['company']['feid']==feid))) as read_autos:
                    reconstruction.ensure_sources_current(doc,self.user)
                expected=(date(2026,8,22),date(2026,9,22)) if modern else (date(2026,9,1),date(2026,10,1))
                self.assertEqual(config.map_bounds(read_plan.call_args.args[0]),expected)
                self.assertTrue(all(call.args[4]==expected for call in read_autos.call_args_list))
                self.assertEqual(reconstruction.payroll_fingerprint(payroll),reconstruction.payroll_fingerprint(current))


if __name__=='__main__':unittest.main()
