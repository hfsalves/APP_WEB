from copy import deepcopy
from decimal import Decimal
from datetime import date
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest
import uuid

from flask import Flask

from modules.gr_travel_maps import engine, itinerary, distances, service, sources, config, reconstruction
from tests.test_gr_travel_reconstruction import fixtures, profile_fixture
from tests import test_gr_travel_reconstruction as legacy
from tests.test_gr_travel_maps import COMPANY


def graph_fixture(local=True):
    payroll, batches, inputs = fixtures()
    works = engine.candidates(batches)
    points = {'home': {'key': 'home', 'label': 'Casa', 'address': inputs['origin'], 'country': 'PT', 'city': 'Braga',
                       'source': {'kind': 'GEOCODIFICADO'}, 'precision': 'MORADA'}}
    for work in works:
        points[work['key']] = {'key': work['key'], 'label': work['work'], 'address': work['address'],
                              'country': 'FR' if work['work']=='C' else 'PT', 'city': work['locality'],
                              'source': {'kind': 'GEOCODIFICADO'}, 'precision': 'MORADA'}
    ids = {point['label']: key for key, point in points.items()}
    edges = {}
    routes = [('Casa','A',70),('A','Casa',70),('Casa','B',99),('B','Casa',99),('Casa','C',1500),('C','Casa',1500)]
    if local: routes += [('A','B',4),('B','A',4)]
    for a,b,km in routes:
        first,last = ids[a],ids[b]
        edges[f'{first}>{last}'] = {'from':first,'to':last,'km':str(km),'meters':str(km*1000),'seconds':str(km*50),
                                  'source':{'kind':'CALCULADO','provider':'OSRM'}}
    return {'locations':points,'edges':edges,'warnings':[],'unresolved':[]}, ids


def prepared_graph_steps(*args):
    yield from ()
    return graph_fixture()[0]


class CalendarTests(unittest.TestCase):
    def setUp(self):
        self.payroll,self.batches,self.inputs=fixtures()
        self.graph,self.ids=graph_fixture()

    def build(self):return itinerary.build(self.payroll,self.batches,self.inputs,self.graph)

    def test_residual_uses_real_work_to_work_detour_and_keeps_phc(self):
        original=deepcopy(self.payroll)
        doc=self.build()
        self.assertEqual(doc['reconciliation']['km']['map'],'684')
        self.assertEqual(doc['reconciliation']['ac_estrangeiro']['map'],'4')
        self.assertTrue(any(e['travel_type']=='ENTRE_OBRAS' for e in doc['entries']))
        self.assertEqual(self.payroll,original)
        for e in doc['entries']:
            self.assertEqual(e['evidence_type'],'INFERIDO')
            if e['category']=='km':self.assertEqual(e['quantity'],e['provenance']['distance']['km'])
        self.assertEqual(len(itinerary.calendar(doc)),30)
        self.assertGreater(min(e['date'] for e in doc['entries'] if e['category']=='km'),'2026-09-01')
        self.assertGreater(max(e['date'] for e in doc['entries'] if e['category']=='km'),'2026-09-20')
        engine.check_entries(doc,True)

    def test_without_local_route_difference_is_not_fabricated(self):
        self.graph,_=graph_fixture(False)
        self.assertEqual(self.build()['reconciliation']['km']['map'],'676')

    def test_foreign_allowances_form_one_block_without_domestic_trips(self):
        doc=self.build()
        foreign=[e for e in doc['entries'] if e['category']=='ac_estrangeiro']
        self.assertEqual([e['date'] for e in foreign],['2026-09-25','2026-09-28','2026-09-29','2026-09-30'])
        self.assertTrue(all(e['date']<'2026-09-25' for e in doc['entries'] if e['category']=='km'))
        self.assertTrue(any('permanência e deslocação' in w for w in doc['warnings']))

    def test_unknown_and_negative_phc_warnings_survive_calendar_generation(self):
        self.payroll['employee']['phc']['ac_nacional']['quantity']=None
        self.payroll['employee']['phc']['ac_estrangeiro']['quantity']='-1'
        warnings=self.build()['warnings']
        self.assertTrue(any('ac_nacional: total PHC desconhecido' in w for w in warnings))
        self.assertTrue(any('ac_estrangeiro: total PHC negativo' in w for w in warnings))

    def test_low_target_uses_one_inferred_work_base_and_linked_return(self):
        self.payroll['employee']['phc']['km']['quantity']='8'
        doc=self.build();km=[e for e in doc['entries'] if e['category']=='km']
        self.assertEqual(doc['reconciliation']['km']['map'],'8')
        self.assertEqual(len(km),2)
        self.assertTrue(all(e['travel_type']=='ENTRE_OBRAS' for e in km))
        self.assertEqual(km[0]['journey_id'],km[1]['journey_id'])
        self.assertLess(km[0]['date'],km[1]['date'])
        self.assertEqual(km[0]['from_key'],km[1]['to_key'])
        self.assertTrue(any('Presença inicial' in w for w in doc['warnings']))

    def test_same_day_and_later_policy_are_respected(self):
        for policy in ('same_day','later'):
            self.inputs['return_policy']=policy
            doc=self.build()
            for journey in doc['journeys']:
                self.assertEqual(journey['outbound_date']==journey['return_date'],policy=='same_day')

    def test_exclusions_are_respected_and_no_invented_workday_presence(self):
        self.inputs['blocked_dates']=['2026-09-03','2026-09-04','2026-09-24']
        doc=self.build()
        self.assertTrue(all(e['date'] not in self.inputs['blocked_dates'] and date.fromisoformat(e['date']).weekday()<5 for e in doc['entries']))
        self.assertTrue(any('atividade em cada dia' in w for w in doc['warnings']))

    def test_return_before_departure_and_partial_journey_are_rejected(self):
        doc=self.build();journey=doc['journeys'][0];legs=sorted([e for e in doc['entries'] if e.get('journey_id')==journey['id']],key=lambda e:e['leg_index'])
        for change in ({'id':legs[-1]['id'],'date':'2026-09-01'},{'id':legs[0]['id'],'included':False}):
            with self.assertRaises(config.TravelMapsError):engine.edit(doc,[change],'reviewer','Correção')
        edited=engine.edit(doc,[{'id':e['id'],'included':False} for e in legs],'reviewer','Excluir viagem')
        self.assertLess(Decimal(edited['reconciliation']['km']['map']),Decimal(doc['reconciliation']['km']['map']))
        self.assertTrue(all(e['included'] for e in legs))

    def test_delayed_return_is_editable_with_history_and_dates_updated(self):
        self.payroll['employee']['phc']['ac_estrangeiro']['quantity']='0'
        doc=self.build();journey=doc['journeys'][-1]
        legs=[e for e in doc['entries'] if e.get('journey_id')==journey['id'] and e['date']==journey['return_date']]
        edited=engine.edit(doc,[{'id':e['id'],'date':'2026-09-30'} for e in legs],'reviewer','Regresso mais tarde')
        self.assertEqual(edited['journeys'][-1]['return_date'],'2026-09-30')
        self.assertNotEqual(doc['journeys'][-1]['return_date'],'2026-09-30')
        self.assertEqual(edited['reconciliation']['km'],doc['reconciliation']['km'])

    def test_calendar_conflict_with_another_journey_is_rejected(self):
        doc=self.build();first,second=doc['journeys'][:2]
        legs=[e for e in doc['entries'] if e.get('journey_id')==first['id'] and e['date']==first['return_date']]
        with self.assertRaises(config.TravelMapsError):engine.edit(doc,[{'id':e['id'],'date':second['outbound_date']} for e in legs],'user','Overlap')

    def test_unresolved_locations_never_become_zero_distance_routes(self):
        self.graph['edges']={}
        doc=self.build()
        self.assertEqual(doc['reconciliation']['km']['map'],'0')
        self.assertTrue(any('Sem combinação' in w for w in doc['warnings']))

    def test_home_override_does_not_claim_phc_address_provenance(self):
        self.payroll['employee_profile']=profile_fixture()
        self.inputs['origin']=self.payroll['employee_profile']['origin']
        self.graph['locations']['home']['address']='Outra partida declarada'
        doc=self.build()
        self.assertEqual(doc['inputs']['origin'],'Outra partida declarada')
        self.assertTrue(all(e['provenance']['origin']['kind']=='DECLARADO' for e in doc['entries'] if e.get('from_key')=='home'))

    def test_ac_between_split_legs_requires_the_actual_inferred_stay_work(self):
        self.payroll['employee']['phc']['ac_estrangeiro']['quantity']='0'
        doc=self.build();journey=doc['journeys'][-1]
        legs=sorted([e for e in doc['entries'] if e.get('journey_id')==journey['id']],key=lambda e:e['leg_index'])
        ret=[e for e in legs if e['date']==journey['return_date']]
        edited=engine.edit(doc,[{'id':e['id'],'date':'2026-09-30'} for e in ret],'user','Stay')
        actual=itinerary.presence(sorted([e for e in edited['entries'] if e.get('journey_id')==journey['id']],key=lambda e:e['leg_index']),['2026-09-28'])
        before=[e for e in legs if e['date']==journey['outbound_date']][-1]
        self.assertEqual(actual['2026-09-28'],{before['to_key']}-{'home'})

    def test_solver_matches_bruteforce_without_pruning(self):
        from itertools import product
        options=[{'km':'14.25','days':1,'local_legs':0},{'km':'19.80','days':2,'local_legs':2}]
        for target in ('14','28.50','34','68.40'):
            chosen,truncated=itinerary.search(options,Decimal(target),4)
            total=sum((Decimal(o['km']) for o in chosen),Decimal(0))
            possible=[(Decimal('14.25')*a+Decimal('19.80')*b,b*2,a+b) for a,b in product(range(5),range(3)) if a+2*b<=4]
            expected=min(possible,key=lambda v:(abs(v[0]-Decimal(target)),v[0]>Decimal(target),v[1],v[2]))
            self.assertEqual(total,expected[0]);self.assertFalse(truncated)


class DistanceTests(unittest.TestCase):
    def setUp(self):
        self.folder=TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.app=Flask(__name__,instance_path=self.folder.name)
        self.ctx=self.app.app_context();self.ctx.push();self.addCleanup(self.ctx.pop)

    def feature(self,lon=-8.42,lat=41.55,name='Braga'):
        return {'geometry':{'coordinates':[lon,lat]},'properties':{'name':name,'countrycode':'PT','osm_value':'city','osm_type':'R','osm_id':123}}

    def test_geocoder_does_not_accept_unrelated_or_ambiguous_results(self):
        self.assertEqual(distances.select_match([self.feature()],'Braga','PT')['precision'],'LOCALIDADE')
        for query,features in [('Lisboa',[self.feature()]),('Braga',[self.feature(),self.feature(-9,40)]),('Braga',[self.feature(lat=999)])]:
            with self.assertRaises(config.TravelMapsError):distances.select_match(features,query,'PT')

    def test_geocode_is_cached_and_queries_no_payroll_identity(self):
        with patch.object(distances,'fetch',return_value={'features':[self.feature()]}) as fetch:
            first=distances.geocode('Braga','PT');second=distances.geocode('Braga','PT')
        self.assertEqual(first,second);self.assertEqual(fetch.call_count,1)
        self.assertEqual(fetch.call_args.args[1],{'q':'Braga','limit':4,'countrycode':'PT'})

    def test_locality_fallback_is_explicit_and_preserves_unresolved_address(self):
        located={'precision':'RUA','country':'PT','source':{'kind':'GEOCODIFICADO','query':'Braga'}}
        with patch.object(distances,'geocode',side_effect=[config.TravelMapsError('Morada não localizada'),located]) as geocode:
            result=distances.locate_address('Rua X, Braga','PT','Braga')
        self.assertEqual(geocode.call_count,2)
        self.assertEqual(result['precision'],'LOCALIDADE')
        self.assertEqual(result['source']['address_not_resolved'],'Rua X, Braga')
        self.assertEqual(result['source']['query'],'Braga')

    def test_modified_home_never_falls_back_to_old_phc_locality(self):
        payroll,batches,inputs=fixtures();payroll['employee_profile']=profile_fixture()
        payroll['employee_profile']['original']={'pe':{'LOCAL':'Braga'}}
        inputs['origin']='Casa nova, Faro'
        with patch.object(distances,'locate_address',side_effect=config.TravelMapsError('Por localizar')) as locate:
            result=distances.prepare(payroll,batches,inputs)
        self.assertEqual(locate.call_args_list[0].args,('Casa nova, Faro','PT',''))
        self.assertEqual(result['edges'],{})

    def test_provider_failure_circuit_avoids_one_timeout_per_employee_work(self):
        import requests
        with patch.object(distances,'_UNAVAILABLE',{}),patch.object(distances.requests,'get',side_effect=requests.Timeout) as get:
            for unused in range(3):
                with self.assertRaises(config.TravelMapsError):distances.fetch('https://example.invalid/api',{'q':'Braga'})
        self.assertEqual(get.call_count,1)

    def test_directed_matrix_preserves_asymmetry_and_unroutable_cells(self):
        points={'a':{'lat':41,'lon':-8},'b':{'lat':42,'lon':-8},'c':{'lat':43,'lon':-8}}
        response={'code':'Ok','distances':[[0,7000,None],[7500,0,None],[None,None,0]],'durations':[[0,420,None],[450,0,None],[None,None,0]]}
        with patch.object(distances,'fetch',return_value=response):edges,_=distances.road_matrix(points)
        self.assertEqual(edges['a>b']['km'],'7.00');self.assertEqual(edges['b>a']['km'],'7.50')
        self.assertNotIn('a>c',edges)

    def test_matrix_rejects_air_distance_fallback_and_invalid_numbers(self):
        points={'a':{'lat':41,'lon':-8},'b':{'lat':42,'lon':-8}}
        for response in [{'code':'Ok','fallback_speed_cells':[[0,1]]},{'code':'Ok','distances':[[0,-1],[2,0]],'durations':[[0,1],[2,0]]}]:
            with patch.object(distances,'cache_read',return_value=None),patch.object(distances,'fetch',return_value=response):
                with self.assertRaises(config.TravelMapsError):distances.road_matrix(points)

    def test_private_vehicle_field_has_priority_and_exact_provenance(self):
        details={'pe':{'PESTAMP':'PE1','MORADA':'Rua X','U_MATPRO':'39-OF-04'},'pe2':{'PE2STAMP':'PE1','MATRICULA':'ZZ-00-AA'},
                 'fields':{'PE':['PESTAMP','MORADA','U_MATPRO'],'PE2':['PE2STAMP','MATRICULA']}}
        with patch.object(service,'company_for_user',return_value=COMPANY),patch.object(sources,'employee_details',return_value=details):
            result=service.employee_profile(2,{'pestamp':'PE1','identity_resolved':True},object())
        self.assertEqual(result['vehicle'],'39-OF-04')
        self.assertEqual(result['provenance']['vehicle']['references'][0]['fields'],['U_MATPRO'])
        self.assertTrue(any('diferem' in w for w in result['warnings']))


class AutomaticWorkflowTests(unittest.TestCase):
    setUp=legacy.WorkflowTests.setUp
    post=legacy.WorkflowTests.post

    def test_automatic_generation_versions_and_validation(self):
        graph,_=graph_fixture()
        payload={'mode':'AUTOMATIC','feid':2,'year':2026,'month':9,'employee_key':self.payroll['employee']['key'],
                 'measurement_companies':[1,2],'inputs':self.inputs,'reason':'Calendário automático','expected_version':0,'request_id':str(uuid.uuid4())}
        with patch.object(reconstruction.distances,'prepare_steps',side_effect=prepared_graph_steps):response=self.post('propostas',payload)
        self.assertEqual(response.status_code,200,response.json)
        self.assertEqual(response.json['current']['document']['mode'],'AUTOMATIC')
        self.assertEqual(response.json['current']['document']['reconciliation']['km']['map'],'684')
        result=self.post(f"propostas/{response.json['header']['id']}/validar",{'expected_version':1,'request_id':str(uuid.uuid4()),'reason':'Revisto','acknowledge_inference':True})
        self.assertEqual(result.status_code,200,result.json)
        self.assertTrue(all(e['evidence_type']=='INFERIDO' for e in result.json['current']['document']['entries']))

    def test_preview_does_not_write_and_cannot_forge_phc(self):
        graph,_=graph_fixture()
        payload={'feid':2,'year':2026,'month':9,'employee_key':self.payroll['employee']['key'],'measurement_companies':[1,2],
                 'inputs':self.inputs,'phc':{'km':'999'}}
        with patch.object(reconstruction.distances,'prepare_steps',side_effect=prepared_graph_steps),patch.object(reconstruction.store,'append') as append:
            response=self.post('prever',payload)
        self.assertEqual(response.status_code,200,response.json);append.assert_not_called()
        self.assertFalse(response.json['persisted'])
        self.assertEqual(response.json['document']['payroll']['employee']['phc']['km']['quantity'],'684')


