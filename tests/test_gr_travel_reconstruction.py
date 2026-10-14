from copy import deepcopy
from datetime import date
from decimal import Decimal
from itertools import product
from types import SimpleNamespace
from unittest.mock import patch
import tempfile
import unittest
import uuid

from flask import Flask
from flask_login import LoginManager
from jinja2 import DictLoader
from sqlalchemy import create_engine, select, update

from modules.gr_travel_maps import config, engine, reconstruction, service, store
from modules.gr_travel_maps.routes import bp
from tests.test_gr_travel_maps import COMPANY, START, END, salary_line


def fixtures():
    app = Flask(__name__)
    with app.app_context():
        rule = config.payroll_rule('HSOLS_PT', START, END)
        employee = service.aggregate_payroll([
            salary_line(), salary_line(PRRESTAMP='LINE2', CR=40, RQTT=Decimal('4'), ERVU=Decimal('80'), ERE=Decimal('320')),
        ], COMPANY, START, END, rule)['rows'][0]
    payroll = {'company': service.public_company(COMPANY), 'year': 2026, 'month': 9,
               'read_at': '2026-10-14T00:00:00Z', 'mapping': rule, 'period_basis': 'PR.DATA',
               'employee': employee, 'warnings': []}
    batches = []
    for feid, database, works in [(2, 'HSOLS_PT', [('A', 'Braga'), ('B', 'Guimarães')]), (1, 'HSOLS_FR', [('C', 'Lyon')])]:
        records = [{'bostamp': f'{database}-{work}', 'number': '1', 'series': 'Auto de Medição', 'ndos': 201,
            'date': START.isoformat(), 'work': work, 'cost_center': '', 'description': work, 'client': 'Cliente',
            'client_number': '1', 'address': f'Rua {work}', 'locality': city, 'country': None,
            'work_matches': 1, 'has_positive_measurement': True, 'employee_assignment': None,
            'source': {'database': database, 'table': 'BO', 'stamp': f'{database}-{work}'}} for work, city in works]
        batches.append({'company': {'feid': feid, 'phc_db': database, 'name': database}, 'rows': records,
                        'source_state': 'AVAILABLE', 'read_at': '2026-10-14T00:00:00Z', 'warnings': []})
    works = engine.candidates(batches)
    inputs = {'origin': 'Base de teste', 'origin_country': 'PT', 'note': 'Percursos indicados pelo revisor, a confirmar.',
              'vehicle': 'AA-00-BB', 'owner': 'Trabalhador de teste', 'blocked_dates': [], 'rates': {},
              'works': [{'key': w['key'], 'country': 'FR' if w['work']=='C' else 'PT', 'city': w['locality'],
                         'outward_km': {'A': '70', 'B': '99', 'C': None}[w['work']], 'return_km': None,
                         'max_trips': 3, 'distance_source': 'Percurso rodoviário declarado'} for w in works]}
    return payroll, batches, inputs


def profile_fixture():
    return {'origin': 'Rua da casa 1, Braga', 'vehicle': 'AA-00-BB', 'warnings': [],
            'provenance': {field: {'kind': 'PHC', 'temporal_scope': 'CURRENT_EMPLOYEE_RECORD',
                'references': [{'database': 'HSOLS_PT', 'table': table, 'stamp': 'PE12', 'fields': fields}]}
                for field, table, fields in [('origin', 'PE', ['MORADA', 'CODPOST', 'LOCAL']), ('vehicle', 'PE2', ['MATRICULA'])]}}


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.payroll, self.batches, self.inputs = fixtures()

    def build(self):
        return engine.build(self.payroll, self.batches, self.inputs)

    def test_reconciles_without_changing_phc_or_confusing_confidence(self):
        before = deepcopy(self.payroll)
        document = self.build()
        self.assertEqual(document['reconciliation']['km']['map'], '676')
        self.assertEqual(document['reconciliation']['km']['difference'], '-8')
        self.assertEqual(document['reconciliation']['km']['percent'], '98.83')
        self.assertEqual(document['reconciliation']['ac_estrangeiro']['map'], '4')
        self.assertEqual(self.payroll, before)
        self.assertTrue(all(e['evidence_type']=='INFERIDO' and e['confidence']['level']=='BAIXA' and e['validation_state']=='POR_VALIDAR' for e in document['entries']))
        self.assertTrue(all(e['provenance']['work']['references'] for e in document['entries']))
        self.assertEqual(len({e['date'] for e in document['entries']}), len(document['entries']))

    def test_missing_distances_are_not_invented(self):
        for work in self.inputs['works']: work['outward_km'] = None
        document = self.build()
        self.assertEqual(document['reconciliation']['km']['map'], '0')
        self.assertEqual(document['reconciliation']['km']['difference'], '-684')
        self.assertTrue(any('Sem percursos' in warning for warning in document['warnings']))

    def test_no_inferred_country_from_company_or_city(self):
        for work in self.inputs['works']: work['country'] = ''
        document = self.build()
        self.assertEqual(document['reconciliation']['ac_estrangeiro']['map'], '0')
        self.assertTrue(all(w['country'] is None for b in document['measurements'] for w in b['rows']))

    def test_calendar_exclusions_and_fractional_allowances(self):
        self.payroll['employee']['phc']['ac_estrangeiro']['quantity'] = '2.5'
        self.inputs['blocked_dates'] = ['2026-09-01','2026-09-02']
        document = self.build()
        allowances = [e for e in document['entries'] if e['category']=='ac_estrangeiro']
        self.assertEqual([e['quantity'] for e in allowances], ['1','1','0.5'])
        self.assertEqual(allowances[0]['date'], '2026-09-03')
        self.assertTrue(all(date.fromisoformat(e['date']).weekday()<5 and e['date'] not in self.inputs['blocked_dates'] for e in document['entries']))

    def test_calendar_shortage_keeps_difference(self):
        self.inputs['blocked_dates'] = [day for day in engine.calendar_days(START,END,[]) if day!='2026-09-30']
        document = self.build()
        self.assertEqual(document['reconciliation']['ac_estrangeiro']['map'], '1')
        self.assertEqual(document['reconciliation']['km']['map'], '0')

    def test_weekends_require_explicit_option_and_respect_exclusions(self):
        self.inputs['include_weekends']=True
        self.inputs['blocked_dates']=['2026-09-01','2026-09-02','2026-09-03','2026-09-04']
        document=self.build()
        self.assertEqual(document['entries'][0]['date'],'2026-09-05')
        engine.check_entries(document,validating=True)

    def test_allowance_country_is_not_the_temporary_departure_country(self):
        self.inputs['origin_country']='FR'
        self.inputs['allowance_country']='PT'
        document=self.build()
        self.assertEqual(document['reconciliation']['ac_estrangeiro']['map'],'4')
        self.assertTrue(all(e['country']=='FR' for e in document['entries'] if e['category']=='ac_estrangeiro'))

    def test_joint_calendar_allows_km_and_allowance_only_at_same_work(self):
        self.payroll['employee']['phc']['km']['quantity']='140'
        self.payroll['employee']['phc']['ac_estrangeiro']['quantity']='1'
        self.inputs['blocked_dates']=[day for day in engine.calendar_days(START,END,[]) if day!='2026-09-30']
        foreign=next(w for w in self.inputs['works'] if w['country']=='FR')
        foreign['outward_km']='70'
        document=self.build()
        self.assertEqual(document['reconciliation']['km']['map'],'140')
        self.assertEqual(len(document['entries']),2)
        self.assertEqual(len({e['work_key'] for e in document['entries']}),1)
        self.assertEqual(len({e['date'] for e in document['entries']}),1)

    def test_subday_precision_is_preserved_through_edits(self):
        self.payroll['employee']['phc']['ac_estrangeiro']['quantity']='0.125'
        document=self.build();entry=next(e for e in document['entries'] if e['category']=='ac_estrangeiro')
        result=engine.edit(document,[{'id':entry['id'],'quantity':'0.375'}],'reviewer','Correção de fração')
        self.assertEqual(result['reconciliation']['ac_estrangeiro']['map'],'0.375')

    def test_multiple_autos_do_not_multiply_candidate_trips(self):
        record=deepcopy(self.batches[0]['rows'][0]);record['bostamp']='extra';record['source']['stamp']='extra'
        self.batches[0]['rows'].append(record)
        self.assertEqual(len(engine.candidates(self.batches)),3)
        self.assertEqual(self.build()['reconciliation']['km']['map'],'676')

    def test_default_trip_limit_uses_calendar_instead_of_arbitrary_ten(self):
        self.inputs['works'] = [next(w for w in self.inputs['works'] if w['outward_km'] == '70')]
        self.inputs['works'][0].pop('max_trips')
        self.payroll['employee']['phc']['km']['quantity'] = '1680'
        document = self.build()
        self.assertEqual(document['inputs']['works'][0]['max_trips'], 22)
        self.assertEqual(document['inputs']['works'][0]['max_trips_source'], 'CALENDARIO')
        self.assertEqual(len(document['entries']), 12)
        self.assertEqual(document['reconciliation']['km']['map'], '1680')
        self.inputs['blocked_dates'] = engine.calendar_days(START, END, [])[:-2]
        self.inputs['works'][0]['max_trips'] = None
        document = self.build()
        self.assertEqual(document['inputs']['works'][0]['max_trips'], 2)
        self.assertEqual(len(document['entries']), 2)

    def test_explicit_trip_limit_is_a_declared_restriction(self):
        document = self.build()
        self.assertTrue(all(w['max_trips'] == 3 and w['max_trips_source'] == 'DECLARADO' for w in document['inputs']['works']))

    def test_nonpositive_autos_and_unknown_works_cannot_be_selected(self):
        self.batches[0]['rows'][0]['has_positive_measurement']=False
        with self.assertRaises(config.TravelMapsError):self.build()

    def test_unknown_zero_and_negative_targets(self):
        self.payroll['employee']['phc']['km']['quantity']='-5'
        document=self.build()
        self.assertEqual(document['reconciliation']['km']['map'],'0')
        self.assertIsNone(document['reconciliation']['ac_nacional']['percent'])
        self.assertEqual(engine.reconciliation('0',Decimal('0'))['percent'],'100.00')
        self.assertEqual(engine.reconciliation('0',Decimal('1'))['percent'],'0.00')
        self.assertEqual(engine.reconciliation('4',Decimal('5'))['percent'],'75.00')

    def test_exact_solver_matches_exhaustive_small_problems(self):
        routes=[{'round_trip':'14.25','max_trips':3},{'round_trip':'19.80','max_trips':2},{'round_trip':'30','max_trips':2}]
        for target in ('0','14.26','29','53.31','68.40','110','250'):
            chosen,truncated=engine.km_combination(target,routes,5)
            total=sum((Decimal(w['round_trip'])*n for w,n in chosen),Decimal(0))
            possible=[(sum(Decimal(w['round_trip'])*n for w,n in zip(routes,counts)),sum(counts)) for counts in product(range(4),range(3),range(3)) if sum(counts)<=5]
            expected=min(possible,key=lambda x:(abs(x[0]-Decimal(target)),x[0]>Decimal(target),x[1],x[0]))
            self.assertEqual(total,expected[0]);self.assertFalse(truncated)

    def test_bounded_search_discloses_pruning(self):
        routes=[{'round_trip':str(17+i*3),'max_trips':5} for i in range(10)]
        _,truncated=engine.km_combination('684',routes,20,max_states=12)
        self.assertTrue(truncated)

    def test_nonfinite_or_negative_manual_data_rejected(self):
        for bad in ('NaN','Infinity','-1','12.123'):
            with self.subTest(value=bad):
                self.inputs['works'][0]['outward_km']=bad
                with self.assertRaises(config.TravelMapsError):self.build()

    def test_distance_requires_origin_and_reference(self):
        next(work for work in self.inputs['works'] if work['outward_km'] is not None)['distance_source']=''
        with self.assertRaises(config.TravelMapsError):self.build()

    def test_mixed_phc_rates_are_not_averaged(self):
        employee=self.payroll['employee'];line=deepcopy(employee['lines'][0]);line['original']['ERVU']='0.35';employee['lines'].append(line)
        document=self.build()
        self.assertTrue(all(e['rate'] is None for e in document['entries'] if e['category']=='km'))

    def test_human_edit_creates_new_document_and_retains_inference(self):
        document=self.build();original=deepcopy(document)
        entry=next(e for e in document['entries'] if e['category']=='km')
        result=engine.edit(document,[{'id':entry['id'],'quantity':'141','rate':'0.5'}],'reviewer','Percurso corrigido')
        changed=next(e for e in result['entries'] if e['id']==entry['id'])
        self.assertEqual(changed['amount'],'70.50')
        self.assertEqual(changed['evidence_type'],'INFERIDO')
        self.assertEqual(changed['provenance']['human_changes'][0]['actor'],'reviewer')
        self.assertEqual(changed['provenance']['quantity']['kind'],'DECLARADO')
        self.assertEqual(changed['provenance']['rate']['previous_source']['kind'],'PHC')
        self.assertEqual(document,original)

    def test_invalid_date_overlap_or_protected_fields_fail(self):
        document=self.build();km=next(e for e in document['entries'] if e['category']=='km');ac=document['entries'][0]
        for patch in ({'date':'2026-08-31'},{'date':'2026-09-06'},{'date':ac['date']},{'evidence_type':'COMPROVADO'},{'quantity':'0'}):
            with self.subTest(change=patch),self.assertRaises(config.TravelMapsError):
                engine.edit(document,[{'id':km['id'],**patch}],'user','Teste')

    def test_validation_checks_missing_vehicle_and_rates(self):
        document=self.build();engine.check_entries(document,validating=True)
        next(e for e in document['entries'] if e['category']=='km')['vehicle']=''
        with self.assertRaises(config.TravelMapsError):engine.check_entries(document,validating=True)

    def test_employee_home_defaults_are_snapshotted_and_remain_inferred_trips(self):
        self.payroll['employee_profile'] = profile_fixture()
        del self.inputs['origin']; del self.inputs['vehicle']
        document = self.build()
        for entry in document['entries']:
            self.assertEqual(entry['origin'], 'Rua da casa 1, Braga')
            self.assertEqual(entry['vehicle'], 'AA-00-BB')
            self.assertEqual(entry['provenance']['origin']['kind'], 'PHC')
            self.assertEqual(entry['provenance']['vehicle']['kind'], 'PHC')
            self.assertEqual(entry['provenance']['owner']['kind'], 'DECLARADO')
            self.assertEqual(entry['evidence_type'], 'INFERIDO')
        self.payroll['employee_profile']['origin'] = 'Outra morada'
        self.assertEqual(document['payroll']['employee_profile']['origin'], 'Rua da casa 1, Braga')

    def test_override_of_employee_home_cannot_forge_phc_provenance(self):
        self.payroll['employee_profile'] = profile_fixture()
        self.inputs['provenance'] = {'origin': {'kind': 'PHC', 'table': 'FORGED'}}
        document = self.build()
        for entry in document['entries']:
            self.assertEqual(entry['origin'], 'Base de teste')
            self.assertEqual(entry['provenance']['origin']['kind'], 'DECLARADO')
            self.assertEqual(entry['provenance']['origin']['previous_source']['references'][0]['table'], 'PE')

    def test_edit_vehicle_preserves_original_phc_source_and_value(self):
        self.payroll['employee_profile'] = profile_fixture()
        document = self.build(); entry = document['entries'][0]
        changed = engine.edit(document, [{'id': entry['id'], 'vehicle': 'CC-11-DD'}], 'reviewer', 'Outra viatura')
        updated = next(e for e in changed['entries'] if e['id'] == entry['id'])
        self.assertEqual(updated['provenance']['vehicle']['previous_source']['kind'], 'PHC')
        self.assertEqual(document['entries'][0]['vehicle'], 'AA-00-BB')


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.engine=create_engine('sqlite:///:memory:');store.metadata.create_all(self.engine)
        self.addCleanup(self.engine.dispose)
        self.document=engine.build(*fixtures())

    def append(self,expected=0,request=None,action='GENERATE',state='POR_VALIDAR',document=None):
        return store.append(self.engine,document or self.document,action=action,state=state,actor='reviewer',user_stamp='US1',reason='Revisão de teste',expected_version=expected,request_id=request or str(uuid.uuid4()),request_hash='a'*64)

    def test_versions_survive_changes(self):
        first=self.append();map_id=first['header']['id']
        revised=deepcopy(self.document);revised['warnings'].append('Alteração humana')
        self.append(1,action='EDIT',document=revised)
        self.assertEqual(store.get(self.engine,map_id,1)['current']['document'],self.document)
        self.assertEqual(store.get(self.engine,map_id)['current']['version'],2)
        self.assertEqual(len(store.history(self.engine,map_id)),2)
        self.assertEqual(store.get(self.engine,map_id)['current']['previous_hash'],first['current']['content_hash'])

    def test_versions_survive_reopening_the_database(self):
        with tempfile.TemporaryDirectory() as folder:
            url=f'sqlite:///{folder}/maps.db';first_engine=create_engine(url);store.metadata.create_all(first_engine)
            result=store.append(first_engine,self.document,action='GENERATE',state='POR_VALIDAR',actor='user',user_stamp='U',reason='test',
                                expected_version=0,request_id=str(uuid.uuid4()),request_hash='x')
            first_engine.dispose()
            second_engine=create_engine(url)
            self.assertEqual(store.get(second_engine,result['header']['id'])['current']['document'],self.document)
            second_engine.dispose()

    def test_stale_version_cannot_overwrite(self):
        first=self.append()
        with self.assertRaises(store.Conflict):self.append(0)
        self.assertEqual(store.get(self.engine,first['header']['id'])['header']['version'],1)
        self.assertEqual(len(store.history(self.engine,first['header']['id'])),1)

    def test_identical_request_is_idempotent(self):
        request=str(uuid.uuid4());first=self.append(request=request);second=self.append(request=request)
        self.assertEqual(first['current'],second['current'])
        self.assertEqual(len(store.history(self.engine,first['header']['id'])),1)

    def test_history_tampering_detected(self):
        first=self.append()
        with self.engine.begin() as conn:conn.execute(update(store.versions).values(reason='Tampered'))
        with self.assertRaises(store.StorageUnavailable):store.history(self.engine,first['header']['id'])

    def test_reused_request_cannot_change_scope(self):
        request=str(uuid.uuid4());self.append(request=request)
        other=deepcopy(self.document);other['payroll']['company']['feid']=3
        with self.assertRaises(store.Conflict):self.append(request=request,document=other)

    def test_failed_version_insert_rolls_back_header_change(self):
        first=self.append();map_id=first['header']['id']
        from sqlalchemy import event
        def fail(conn,cursor,statement,parameters,context,executemany):
            if statement.startswith('INSERT INTO "GR_TRAVEL_MAP_VERSION"'):raise RuntimeError('Simulated failure')
        event.listen(self.engine,'before_cursor_execute',fail)
        try:
            with self.assertRaises(RuntimeError):self.append(1)
        finally:event.remove(self.engine,'before_cursor_execute',fail)
        self.assertEqual(store.get(self.engine,map_id)['header']['version'],1)
        self.assertEqual(len(store.history(self.engine,map_id)),1)

    def test_missing_schema_is_explicit_and_not_created(self):
        fresh=create_engine('sqlite:///:memory:');self.addCleanup(fresh.dispose)
        with self.assertRaises(store.StorageUnavailable):store.require_schema(fresh)
        self.assertFalse(store.ready(fresh))

    def test_two_companies_never_share_a_map(self):
        first=self.append();other=deepcopy(self.document);other['payroll']['company']['feid']=3
        second=self.append(document=other)
        self.assertNotEqual(first['header']['id'],second['header']['id'])
        self.assertEqual(len(store.monthly(self.engine,2,2026,9)),1)

    def test_concurrent_initial_generation_keeps_one_head(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        with tempfile.TemporaryDirectory() as folder:
            db_engine=create_engine(f'sqlite:///{folder}/maps.db');store.metadata.create_all(db_engine)
            barrier=Barrier(2)
            def worker():
                barrier.wait()
                try:
                    return store.append(db_engine,self.document,action='GENERATE',state='POR_VALIDAR',actor='user',user_stamp='U',reason='test',expected_version=0,request_id=str(uuid.uuid4()),request_hash='x')
                except store.Conflict:return None
            with ThreadPoolExecutor(2) as pool:results=list(pool.map(lambda _:worker(),range(2)))
            self.assertEqual(sum(result is not None for result in results),1)
            self.assertEqual(len(store.monthly(db_engine,2,2026,9)),1)
            db_engine.dispose()


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.db_engine=create_engine('sqlite:///:memory:');store.metadata.create_all(self.db_engine)
        self.addCleanup(self.db_engine.dispose)
        self.payroll,self.batches,self.inputs=fixtures()
        self.user=SimpleNamespace(is_authenticated=True,ADMIN=True,DEV=False,LOGIN='reviewer',USSTAMP='US1')
        self.app=Flask(__name__);self.app.config.update(TESTING=True,SECRET_KEY='test',DB_CLIENT_NAME='GR360_CORE',DB_CURRENT_TARGET_RESOLVER=lambda:'client')
        self.app.register_blueprint(bp)
        self.app.jinja_loader=DictLoader({'base.html':'{% block content %}{% endblock %}'})
        manager=LoginManager(self.app);manager.request_loader(lambda request:self.user)
        self.client=self.app.test_client()
        self.allowed={1,2}
        def company(feid,user):
            if int(feid) not in self.allowed:
                error=config.TravelMapsError('Sem acesso');error.status_code=403;raise error
            return {'feid':int(feid),'phc_db':'HSOLS_PT' if int(feid)==2 else 'HSOLS_FR','name':'Empresa'}
        patches=[patch.object(reconstruction.db.session,'get_bind',return_value=self.db_engine),
            patch.object(reconstruction,'payroll_snapshot',side_effect=lambda *args:deepcopy(self.payroll)),
            patch.object(service,'company_for_user',side_effect=company),
            patch.object(service,'monthly_measurements',side_effect=lambda feid,*args:deepcopy(next(batch for batch in self.batches if batch['company']['feid']==int(feid))))]
        for item in patches:item.start();self.addCleanup(item.stop)
        with self.client.session_transaction() as session:session['travel_maps_csrf']='token'

    def post(self,path,body,csrf=True):
        return self.client.post('/api/gr_mapas/'+path,json=body,headers={'X-Travel-CSRF':'token'} if csrf else {})

    def generate(self):
        payload={'feid':2,'year':2026,'month':9,'employee_key':self.payroll['employee']['key'],'measurement_companies':[1,2],
                 'inputs':self.inputs,'reason':'Primeira proposta','expected_version':0,'request_id':str(uuid.uuid4())}
        response=self.post('propostas',payload)
        self.assertEqual(response.status_code,200,response.json)
        return response.json

    def test_human_validation_and_retry_preserve_inferred_evidence(self):
        created=self.generate();map_id=created['header']['id']
        body={'expected_version':1,'request_id':str(uuid.uuid4()),'reason':'Conferido; diferença de 8 km aceite.','acknowledge_inference':True}
        result=self.post(f'propostas/{map_id}/validar',body)
        self.assertEqual(result.status_code,200,result.json)
        self.assertEqual(result.json['current']['state'],'VALIDADO')
        self.assertEqual(result.json['current']['document']['validation']['actor'],'reviewer')
        self.assertTrue(all(e['evidence_type']=='INFERIDO' for e in result.json['current']['document']['entries']))
        retry=self.post(f'propostas/{map_id}/validar',body)
        self.assertEqual(retry.status_code,200,retry.json);self.assertEqual(retry.json['current']['version'],2)
        self.assertEqual(len(store.history(self.db_engine,map_id)),2)

    def test_validation_requires_explicit_review(self):
        created=self.generate()
        response=self.post(f"propostas/{created['header']['id']}/validar",{'expected_version':1,'request_id':str(uuid.uuid4()),'reason':'Test'})
        self.assertEqual(response.status_code,400)
        self.assertEqual(len(store.history(self.db_engine,created['header']['id'])),1)

    def test_phc_change_blocks_validation_without_rewriting_snapshot(self):
        created=self.generate();self.payroll['employee']['phc']['km']['quantity']='700'
        response=self.post(f"propostas/{created['header']['id']}/validar",{'expected_version':1,'request_id':str(uuid.uuid4()),'reason':'Test','acknowledge_inference':True})
        self.assertEqual(response.status_code,409)
        self.assertEqual(store.get(self.db_engine,created['header']['id'])['current']['document']['payroll']['employee']['phc']['km']['quantity'],'684')

    def test_changed_employee_home_blocks_validation_and_keeps_saved_address(self):
        self.payroll['employee_profile'] = profile_fixture()
        self.inputs['origin'] = self.payroll['employee_profile']['origin']
        created = self.generate()
        self.payroll['employee_profile']['origin'] = 'Nova casa'
        response = self.post(f"propostas/{created['header']['id']}/validar", {'expected_version': 1, 'request_id': str(uuid.uuid4()), 'reason': 'Revisão', 'acknowledge_inference': True})
        self.assertEqual(response.status_code, 409, response.json)
        self.assertIn('morada ou matrícula', response.json['error'])
        context = self.client.get('/api/gr_mapas/contexto?feid=2&ano=2026&mes=9&employee_key=' + self.payroll['employee']['key']).json
        self.assertEqual(context['payroll']['employee_profile']['origin'], 'Nova casa')
        self.assertEqual(context['saved']['current']['document']['inputs']['origin'], 'Rua da casa 1, Braga')
        self.assertEqual(context['saved']['header']['version'], 1)

    def test_profile_read_timestamp_does_not_invalidate_unchanged_data(self):
        self.payroll['employee_profile'] = profile_fixture()
        self.inputs['origin'] = self.payroll['employee_profile']['origin']
        created = self.generate()
        self.payroll['employee_profile']['read_at'] = '2026-10-15T00:00:00Z'
        response = self.post(f"propostas/{created['header']['id']}/validar", {'expected_version': 1, 'request_id': str(uuid.uuid4()), 'reason': 'Conferido', 'acknowledge_inference': True})
        self.assertEqual(response.status_code, 200, response.json)

    def test_changed_auto_blocks_validation(self):
        created=self.generate();self.batches[0]['rows'][0]['has_positive_measurement']=False
        response=self.post(f"propostas/{created['header']['id']}/validar",{'expected_version':1,'request_id':str(uuid.uuid4()),'reason':'Test','acknowledge_inference':True})
        self.assertEqual(response.status_code,409)

    def test_read_only_user_and_csrf_cannot_generate(self):
        self.assertEqual(self.post('propostas',{},csrf=False).status_code,403)
        with patch('modules.gr_travel_maps.routes.can_change',return_value=False):
            self.assertEqual(self.post('propostas',{}).status_code,403)

    def test_revoked_evidence_company_blocks_reads_and_mutations(self):
        created=self.generate();self.allowed={2}
        response=self.client.get(f"/api/gr_mapas/propostas/{created['header']['id']}")
        self.assertEqual(response.status_code,403)
        monthly=self.client.get('/api/gr_mapas/propostas?feid=2&ano=2026&mes=9')
        self.assertEqual(monthly.status_code,200,monthly.json)
        self.assertEqual(monthly.json['rows'],[{'employee_key':self.payroll['employee']['key'],'restricted':True}])
        response=self.post(f"propostas/{created['header']['id']}/rejeitar",{'expected_version':1,'request_id':str(uuid.uuid4()),'reason':'Test'})
        self.assertEqual(response.status_code,403)

    def test_rejection_then_edit_keeps_every_version(self):
        created=self.generate();map_id=created['header']['id'];entry=created['current']['document']['entries'][0]
        rejected=self.post(f'propostas/{map_id}/rejeitar',{'expected_version':1,'request_id':str(uuid.uuid4()),'reason':'Datas por rever'})
        self.assertEqual(rejected.status_code,200,rejected.json)
        edited=self.post(f'propostas/{map_id}/editar',{'expected_version':2,'request_id':str(uuid.uuid4()),'reason':'Retirada uma linha','changes':[{'id':entry['id'],'included':False}]})
        self.assertEqual(edited.status_code,200,edited.json)
        self.assertEqual(edited.json['current']['state'],'POR_VALIDAR')
        self.assertEqual(len(store.history(self.db_engine,map_id)),3)
        self.assertTrue(store.get(self.db_engine,map_id,1)['current']['document']['entries'][0]['included'])

    def test_historical_version_and_context_reopen(self):
        created=self.generate()
        response=self.client.get('/api/gr_mapas/contexto?feid=2&ano=2026&mes=9&employee_key='+self.payroll['employee']['key'])
        self.assertEqual(response.status_code,200,response.json)
        self.assertEqual(response.json['measurement_companies'],[1,2])
        self.assertEqual(len(response.json['history']),1)
        detail=self.client.get(f"/api/gr_mapas/propostas/{created['header']['id']}?version=1")
        self.assertEqual(detail.status_code,200)

    def test_history_does_not_disclose_a_revoked_evidence_company(self):
        created=self.generate();map_id=created['header']['id']
        inputs=deepcopy(self.inputs);inputs['works']=[w for w in inputs['works'] if w['country']=='PT']
        response=self.post('propostas',{'feid':2,'year':2026,'month':9,'employee_key':self.payroll['employee']['key'],
            'measurement_companies':[2],'inputs':inputs,'reason':'Só obras PT','expected_version':1,'request_id':str(uuid.uuid4())})
        self.assertEqual(response.status_code,200,response.json)
        self.allowed={2}
        detail=self.client.get(f'/api/gr_mapas/propostas/{map_id}')
        self.assertEqual(detail.status_code,200,detail.json)
        self.assertEqual([v['version'] for v in detail.json['history']],[2])
        self.assertEqual(self.client.get(f'/api/gr_mapas/propostas/{map_id}?version=1').status_code,403)

    def test_client_phc_override_is_ignored(self):
        payload={'feid':2,'year':2026,'month':9,'employee_key':self.payroll['employee']['key'],'measurement_companies':[1,2],
                 'inputs':self.inputs,'reason':'Test','expected_version':0,'request_id':str(uuid.uuid4()),
                 'phc':{'km':'676'},'state':'VALIDADO','confidence':'ALTA'}
        response=self.post('propostas',payload)
        self.assertEqual(response.status_code,200,response.json)
        self.assertEqual(response.json['current']['state'],'POR_VALIDAR')
        self.assertEqual(response.json['current']['document']['payroll']['employee']['phc']['km']['quantity'],'684')

    def test_saved_history_remains_available_when_receipt_disappears(self):
        created=self.generate()
        with patch.object(reconstruction,'payroll_snapshot',side_effect=store.NotFound('Recibo não encontrado.')):
            response=self.client.get('/api/gr_mapas/contexto?feid=2&ano=2026&mes=9&employee_key='+self.payroll['employee']['key'])
        self.assertEqual(response.status_code,200,response.json)
        self.assertFalse(response.json['sources_current'])
        self.assertEqual(response.json['saved']['header']['id'],created['header']['id'])
        self.assertEqual(response.json['payroll']['employee']['phc']['km']['quantity'],'684')
        self.assertTrue(response.json['source_warnings'])

    def test_saved_history_remains_available_when_autos_are_offline(self):
        self.generate()
        with patch.object(service,'monthly_measurements',side_effect=config.SourceUnavailable('Offline')):
            response=self.client.get('/api/gr_mapas/contexto?feid=2&ano=2026&mes=9&employee_key='+self.payroll['employee']['key'])
        self.assertEqual(response.status_code,200,response.json)
        self.assertFalse(response.json['sources_current'])
        self.assertEqual(len(response.json['works']),3)


if __name__=='__main__':unittest.main()
