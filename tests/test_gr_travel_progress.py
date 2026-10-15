"""Incremental transport must report actual work and preserve the write contract."""
from copy import deepcopy
import json
import unittest
import uuid
from unittest.mock import patch

from modules.gr_travel_maps import distances, reconstruction, store
from modules.gr_travel_maps.config import TravelMapsError
from tests import test_gr_travel_reconstruction as legacy
from tests.test_gr_travel_calendar import graph_fixture, prepared_graph_steps


class ProgressWorkflowTests(unittest.TestCase):
    setUp = legacy.WorkflowTests.setUp

    def payload(self):
        return {'mode': 'AUTOMATIC', 'feid': 2, 'year': 2026, 'month': 9,
                'employee_key': self.payroll['employee']['key'], 'measurement_companies': [1, 2],
                'inputs': self.inputs, 'reason': 'Calendário automático', 'expected_version': 0,
                'request_id': str(uuid.uuid4())}

    def stream(self, path='propostas', payload=None, csrf=True):
        headers = {'Accept': 'application/x-ndjson'}
        if csrf:
            headers['X-Travel-CSRF'] = 'token'
        return self.client.post('/api/gr_mapas/' + path, json=payload or self.payload(),
                                headers=headers, buffered=False)

    def messages(self, response):
        try:
            return [json.loads(chunk) for chunk in response.response]
        finally:
            response.close()

    def test_progress_arrives_before_geocoding_and_before_persistence(self):
        graph, _ = graph_fixture()

        def locate(query, country, locality):
            work = next((w for w in graph['locations'].values() if w['address'] in query), graph['locations']['home'])
            return {**deepcopy(work), 'lat': 41, 'lon': -8}

        with patch.object(distances, 'locate_address', side_effect=locate) as geocode, \
                patch.object(distances, 'road_matrix', return_value=(graph['edges'], [])):
            response = self.stream()
            self.assertEqual(response.headers['X-Accel-Buffering'], 'no')
            self.assertIn('no-store', response.headers['Cache-Control'])
            self.assertEqual(response.mimetype, 'application/x-ndjson')
            events = []
            try:
                for chunk in response.response:
                    item = json.loads(chunk); events.append(item)
                    if item.get('phase') == 'locations' and item['completed'] == 0:
                        geocode.assert_not_called()
                        self.assertEqual(store.monthly(self.db_engine, 2, 2026, 9), [])
                    if item.get('phase') == 'saving':
                        self.assertEqual(store.monthly(self.db_engine, 2, 2026, 9), [])
            finally:
                response.close()
        locations = [e for e in events if e.get('phase') == 'locations']
        self.assertEqual(locations[-1]['completed'], 4)
        self.assertEqual(locations[-1]['resolved'], 4)
        self.assertEqual(locations[-1]['unresolved'], 0)
        self.assertEqual({e['current'] for e in locations}, {'Casa', 'A', 'B', 'C'})
        self.assertEqual([e['phase'] for e in events if e.get('phase') in ('routes', 'combinations', 'saving')],
                         ['routes', 'combinations', 'saving'])
        saved = events[-1]
        self.assertEqual(saved['type'], 'result')
        self.assertEqual(saved['current']['state'], 'POR_VALIDAR')
        self.assertTrue(all(e['evidence_type'] == 'INFERIDO' for e in saved['current']['document']['entries']))
        self.assertEqual(len(store.history(self.db_engine, saved['header']['id'])), 1)

    def test_preview_counts_unresolved_locations_and_does_not_save(self):
        with patch.object(distances, 'locate_address', side_effect=TravelMapsError('Por localizar')), \
                patch.object(distances, 'road_matrix', return_value=({}, [])):
            events = self.messages(self.stream('prever'))
        locations = [e for e in events if e.get('phase') == 'locations']
        self.assertEqual(locations[-1]['unresolved'], 4)
        self.assertEqual(locations[-1]['resolved'], 0)
        self.assertFalse(events[-1]['persisted'])
        self.assertEqual(events[-1]['document']['result']['status'], 'BLOCKED')
        self.assertEqual(store.monthly(self.db_engine, 2, 2026, 9), [])

    def test_csrf_and_write_permissions_still_reject_before_streaming(self):
        self.assertEqual(self.stream(csrf=False).status_code, 403)
        with patch('modules.gr_travel_maps.routes.can_change', return_value=False):
            self.assertEqual(self.stream().status_code, 403)

    def test_company_access_failure_never_emits_unauthorized_locations(self):
        self.allowed = {2}
        with patch.object(distances, 'prepare_steps') as prepare:
            events = self.messages(self.stream())
        prepare.assert_not_called()
        self.assertEqual(events[-1]['type'], 'error')
        self.assertEqual(events[-1]['status'], 403)
        self.assertFalse(any(e.get('phase') == 'locations' for e in events))

    def test_unexpected_error_is_terminal_and_does_not_expose_internal_details(self):
        with patch.object(reconstruction, 'payroll_snapshot', side_effect=RuntimeError('private connection details')):
            events = self.messages(self.stream())
        self.assertEqual(events[-1]['type'], 'error')
        self.assertNotIn('private connection', json.dumps(events))
        self.assertFalse(any(e['type'] == 'result' for e in events))

    def test_disconnect_before_save_does_not_continue_reconstruction(self):
        with patch.object(reconstruction, 'payroll_snapshot') as payroll:
            response = self.stream()
            self.assertEqual(json.loads(next(iter(response.response)))['phase'], 'payroll')
            response.close()
            payroll.assert_not_called()
        self.assertEqual(store.monthly(self.db_engine, 2, 2026, 9), [])

    def test_stream_retry_does_not_create_a_second_version(self):
        payload = self.payload()
        with patch.object(distances, 'prepare_steps', side_effect=prepared_graph_steps):
            first = self.messages(self.stream(payload=payload))[-1]
            retry = self.messages(self.stream(payload=payload))[-1]
        self.assertEqual(first['current'], retry['current'])
        self.assertEqual(len(store.history(self.db_engine, first['header']['id'])), 1)

    def test_conflict_is_reported_in_stream_without_false_success(self):
        with patch.object(distances, 'prepare_steps', side_effect=prepared_graph_steps):
            self.messages(self.stream())
            events = self.messages(self.stream())
        self.assertEqual(events[-1]['type'], 'error')
        self.assertEqual(events[-1]['status'], 409)
        self.assertFalse(any(e['type'] == 'result' for e in events))


if __name__ == '__main__':
    unittest.main()
