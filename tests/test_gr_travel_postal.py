import io
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import time
import unittest
from unittest.mock import patch, MagicMock
import zipfile

from flask import Flask

from modules.gr_travel_maps import postal, distances, itinerary, config
from tests.test_gr_travel_calendar import graph_fixture
from tests.test_gr_travel_reconstruction import fixtures


def line(iso='PT',code='3105-089',place='Guia',lat='39.9493',lon='-8.7838'):
    return '\t'.join((iso,code,place,'Region','','County','','Area','',lat,lon,'4'))


def archive(iso='PT',body=None):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr(iso+'.txt',body or line(iso))
    return stream.getvalue()


class PostalTests(unittest.TestCase):
    def setUp(self):
        self.directory=TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.app=Flask(__name__,instance_path=self.directory.name)
        self.app.config['GR_TRAVEL_POSTAL_COUNTRIES']='PT,FR'
        self.ctx=self.app.app_context();self.ctx.push();self.addCleanup(self.ctx.pop)
        self.memory=patch.object(postal,'_INDEX',{});self.memory.start();self.addCleanup(self.memory.stop)
        self.index={'PT':postal.parse(line(),'PT'),'FR':postal.parse(line('FR','38070','Saint-Quentin-Fallavier','45.6434','5.1127'),'FR')}
        for value in self.index.values():value['source']={'dataset':'test public dataset','sha256':'test','cache_stale':False}

    def test_exact_postal_is_approximate_and_retains_source_not_home_precision(self):
        with patch.object(postal,'dataset',side_effect=lambda iso:self.index[iso]):
            result=postal.lookup('Morada privada, 3105-089 GUIA PBL','PT','GUIA PBL')
        self.assertEqual(result['precision'],'CODIGO_POSTAL')
        self.assertEqual(result['country'],'PT')
        self.assertEqual(result['source']['postal_code'],'3105-089')
        self.assertEqual(result['source']['license'],'CC BY 4.0')
        self.assertIn('Morada privada',result['source']['address_not_resolved'])

    def test_truncated_locality_requires_matching_postal_and_country_is_not_employer(self):
        with patch.object(postal,'dataset',side_effect=lambda iso:self.index[iso]):
            result=postal.lookup('Rua X, 38070 ST QUENTIN FALL','','38070 ST QUENTIN FALL')
        self.assertEqual(result['country'],'FR')
        self.assertEqual(result['source']['countries_considered'],['PT','FR'])

    def test_ambiguous_places_and_conflicting_postal_are_rejected(self):
        self.index['PT']=postal.parse(line()+'\n'+line(lat='41.5'),'PT');self.index['PT']['source']={}
        with patch.object(postal,'dataset',side_effect=lambda iso:self.index[iso]):
            for query,locality in [('3105-089 Guia','Guia'),('3105-089 Faro','Faro')]:
                with self.assertRaises(config.TravelMapsError):postal.lookup(query,'PT',locality)

    def test_no_city_inference_from_street_names(self):
        with patch.object(postal,'dataset') as load:
            with self.assertRaises(config.TravelMapsError):postal.lookup('Rua de Braga 73','PT','')
        load.assert_not_called()

    def test_explicit_locality_without_postal_and_country_filter(self):
        with patch.object(postal,'dataset',side_effect=lambda iso:self.index[iso]):
            result=postal.lookup('Morada na Guia','PT','Guia')
            with self.assertRaises(config.TravelMapsError):postal.lookup('38070 Saint-Quentin-Fallavier','PT','Saint-Quentin-Fallavier')
        self.assertEqual(result['precision'],'LOCALIDADE')

    def test_same_postal_and_place_in_two_countries_is_ambiguous(self):
        for iso in ('PT','FR'):
            self.index[iso]=postal.parse(line(iso,'35000','Rennes'),iso);self.index[iso]['source']={}
        with patch.object(postal,'dataset',side_effect=lambda iso:self.index[iso]):
            with self.assertRaises(config.TravelMapsError):postal.lookup('35000 Rennes','','Rennes')

    def test_corrupt_disk_cache_is_repaired_and_used_offline_next_time(self):
        path=Path(self.app.instance_path)/'gr_travel_geo'/'postal'/'PT.zip';path.parent.mkdir(parents=True)
        path.write_bytes(b'not a zip')
        with patch.object(postal,'download',return_value=archive()) as download:
            result=postal.dataset('PT');postal._INDEX.clear();again=postal.dataset('PT')
        self.assertEqual(download.call_count,1)
        self.assertEqual(result['source']['sha256'],again['source']['sha256'])
        self.assertIn('3105-089',again['postal'])

    def test_stale_dataset_remains_available_with_explicit_provenance(self):
        path=Path(self.app.instance_path)/'gr_travel_geo'/'postal'/'PT.zip';path.parent.mkdir(parents=True)
        path.write_bytes(archive());old=time.time()-postal.TTL-100;os.utime(path,(old,old))
        with patch.object(postal,'download',side_effect=config.TravelMapsError('Offline')):
            result=postal.dataset('PT')
        self.assertTrue(result['source']['cache_stale'])

    def test_cache_write_failure_does_not_lose_successful_download(self):
        with patch.object(postal,'download',return_value=archive()),patch.object(postal.os,'replace',side_effect=OSError):
            result=postal.dataset('PT')
        self.assertIn('3105-089',result['postal'])

    def test_only_static_country_file_is_downloaded_never_address_query(self):
        response=MagicMock();response.__enter__.return_value=response
        response.iter_content.return_value=[archive()]
        with patch.object(postal.requests,'get',return_value=response) as get:
            result=postal.lookup('Morada privada, 3105-089','PT','')
        self.assertEqual(get.call_args.args,(postal.BASE_URL+'PT.zip',))
        self.assertNotIn('params',get.call_args.kwargs)
        self.assertEqual(result['precision'],'CODIGO_POSTAL')

    def test_independent_fallback_after_photon_outage(self):
        with patch.object(distances,'geocode',side_effect=config.TravelMapsError('Offline')),patch.object(postal,'dataset',side_effect=lambda iso:self.index[iso]):
            result=distances.locate_address('3105-089 Guia','PT','Guia')
        self.assertEqual(result['source']['provider'],'GeoNames')

    def test_geographic_label_does_not_replace_home_or_work_identity(self):
        payroll,batches,inputs=fixtures()
        point={'lat':39.9,'lon':-8.7,'label':'3105-089 Guia, PT','city':'Guia','country':'PT',
               'precision':'CODIGO_POSTAL','source':{'kind':'GEOCODIFICADO','provider':'GeoNames'}}
        with patch.object(distances,'locate_address',return_value=point),patch.object(distances,'road_matrix',return_value=({},[])):
            graph=distances.prepare(payroll,batches,inputs)
        self.assertEqual(graph['locations']['home']['label'],'Casa')
        self.assertEqual({p['label'] for key,p in graph['locations'].items() if key!='home'},{'A','B','C'})
        self.assertTrue(all(p['matched_label']=='3105-089 Guia, PT' for p in graph['locations'].values()))


class ResultDiagnosticsTests(unittest.TestCase):
    def test_empty_preview_explains_block_instead_of_claiming_success(self):
        payroll,batches,inputs=fixtures()
        graph={'locations':{},'edges':{},'warnings':['Pesquisa indisponível'],'unresolved':[{'key':'home','reason':'Sem localização'}]}
        document=itinerary.build(payroll,batches,inputs,graph)
        self.assertEqual(document['result']['status'],'BLOCKED')
        self.assertEqual(document['result']['entries'],0)
        self.assertIn('Nenhum local',document['result']['message'])
        self.assertEqual(document['reconciliation']['km']['phc'],'684')

    def test_road_failure_does_not_block_allowances_with_known_country(self):
        payroll,batches,inputs=fixtures();graph,_=graph_fixture();graph['edges']={}
        document=itinerary.build(payroll,batches,inputs,graph)
        self.assertEqual(document['reconciliation']['ac_estrangeiro']['map'],'4')
        self.assertEqual(document['reconciliation']['km']['map'],'0')
        self.assertEqual(document['result']['status'],'PARTIAL')

    def test_approximate_locations_mark_every_affected_leg(self):
        payroll,batches,inputs=fixtures();graph,_=graph_fixture()
        for point in graph['locations'].values():point['precision']='CODIGO_POSTAL'
        document=itinerary.build(payroll,batches,inputs,graph)
        self.assertTrue(all(e['approximate_distance'] for e in document['entries'] if e['category']=='km'))
        self.assertEqual(document['result']['status'],'PARTIAL')
        self.assertEqual(document['result']['approximate_locations'],len(graph['locations']))
