import json
import hashlib
import unittest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from services import document_ai_delivery_note_service as service
from services import document_ai_service as document_service


def source_line(**updates):
    line = {
        'bistamp': 'BI-CONTRACT-1', 'bostamp': 'BO-CONTRACT',
        'ref': 'BETON', 'design': 'Béton', 'unidade': 'M3',
        'ccusto': 'FR001', 'qtt': Decimal('10'), 'qtt2': Decimal('2'),
        'iva': Decimal('20'), 'tabiva': 2,
        'edebito': Decimal('50'), 'debito': Decimal('50'),
        'ettdeb': Decimal('500'), 'ttdeb': Decimal('500'),
    }
    line.update(updates)
    return line


def controlled_line(**updates):
    line = {
        'portal_line_index': 0, 'portal_subline_index': None, 'portal_line_id': 'LINE-1',
        'line_id': 'LINE-1', 'origin_delivery_note_number': 'BL-77',
        'phc_origin_stamp': 'BO-CONTRACT', 'phc_origin_line_stamp': 'BI-CONTRACT-1',
        'article_ref': 'BETON', 'description': 'Béton', 'unit': 'M3',
        'qty': 3, 'unit_price': 50, 'net_amount': 150, 'tax_rate': 20,
        'ccusto': 'FR001',
    }
    line.update(updates)
    return line


def plan_for_creation():
    source = source_line()
    return {
        'delivery_number': 'BL-77',
        'series': {
            'contract': {'ndos': 119, 'name': 'Contrat'},
            'delivery_note': {'ndos': 130, 'name': 'Bon Livraison Fourn.'},
        },
        'contract': {
            'bostamp': 'BO-CONTRACT', 'ndos': 119, 'obrano': 9, 'boano': 2026,
            'no': 12, 'estab': 0, 'nome': 'Supplier', 'ccusto': 'FR001', 'moeda': 'EURO',
        },
        'contract_stamp': 'BO-CONTRACT',
        'supplier': {'no': 12, 'estab': 0, 'name': 'Supplier'},
        'lines': [{
            'portal_line_index': 0, 'portal_subline_index': None,
            'portal_line_id': 'LINE-1', 'source': source,
            'quantity': Decimal('3'), 'ccusto': 'FR001',
            'foreign_net': Decimal('150'), 'local_net': Decimal('150'),
            'tax_rate': Decimal('20'), 'tax_code': 2,
        }],
        'source_lines': [source],
        'requested_by_source': {'BI-CONTRACT-1': Decimal('3')},
    }


class DocumentAiDeliveryNotePlanningTests(unittest.TestCase):
    def test_intersol_series_requires_demonstrated_119_and_130(self):
        with patch.object(service, '_rows', return_value=[
            {'ndos': 119, 'nmdos': 'Contrat'},
            {'ndos': 130, 'nmdos': 'Bon Livraison Fourn.'},
        ]):
            result = service._intersol_series(MagicMock())

        self.assertEqual(result['contract']['ndos'], 119)
        self.assertEqual(result['delivery_note']['ndos'], 130)

    def test_other_databases_are_explicitly_blocked(self):
        with patch('services.document_ai_service._phc_origin_source', return_value={
            'kind': 'phc', 'phc_db': 'HSOLS_FR',
        }):
            with self.assertRaisesRegex(ValueError, 'apenas em INTERSOL'):
                service._source_and_document({'customer': {'feid': 1}})

    def test_plan_aggregates_partial_sublines_against_contract_balance(self):
        lines = [
            controlled_line(portal_line_id='SUB-1', qty=3),
            controlled_line(portal_line_index=1, portal_line_id='SUB-2', qty=4),
        ]
        document = {'lines': lines, 'supplier': {'supplier_no': 12}}
        source = source_line()
        contract = {'bostamp': 'BO-CONTRACT', 'ndos': 119, 'no': 12, 'estab': 0, 'anulado': 0}
        with patch('services.document_ai_service._assert_effective_portal_lines', return_value=lines), patch(
            'services.document_ai_service._phc_provisional_supplier', return_value={
                'no': 12, 'estab': 0, 'name': 'Supplier',
            }
        ), patch.object(service, '_intersol_series', return_value={
            'contract': {'ndos': 119, 'name': 'Contrat'},
            'delivery_note': {'ndos': 130, 'name': 'Bon Livraison Fourn.'},
        }), patch.object(service, '_load_contract', return_value=(contract, [source])):
            result = service._plan(MagicMock(), document, 'BL-77', for_update=True)

        self.assertEqual(result['requested_by_source']['BI-CONTRACT-1'], Decimal('7'))
        self.assertEqual(len(result['lines']), 2)
        self.assertEqual(sum(row['foreign_net'] for row in result['lines']), Decimal('350.00'))

    def test_plan_blocks_quantity_above_remaining_contract_balance(self):
        line = controlled_line(qty=9)
        document = {'lines': [line], 'supplier': {'supplier_no': 12}}
        contract = {'bostamp': 'BO-CONTRACT', 'ndos': 119, 'no': 12, 'estab': 0, 'anulado': 0}
        with patch('services.document_ai_service._assert_effective_portal_lines', return_value=[line]), patch(
            'services.document_ai_service._phc_provisional_supplier', return_value={
                'no': 12, 'estab': 0, 'name': 'Supplier',
            }
        ), patch.object(service, '_intersol_series', return_value={
            'contract': {'ndos': 119, 'name': 'Contrat'},
            'delivery_note': {'ndos': 130, 'name': 'Bon Livraison Fourn.'},
        }), patch.object(service, '_load_contract', return_value=(contract, [source_line()])):
            with self.assertRaisesRegex(ValueError, 'excede o saldo'):
                service._plan(MagicMock(), document, 'BL-77', for_update=True)

    def test_plan_blocks_closed_contract_for_a_new_delivery(self):
        line = controlled_line(qty=1)
        document = {'lines': [line], 'supplier': {'supplier_no': 12}}
        contract = {
            'bostamp': 'BO-CONTRACT', 'ndos': 119, 'no': 12, 'estab': 0,
            'anulado': 0, 'fechada': 1,
        }
        with patch('services.document_ai_service._assert_effective_portal_lines', return_value=[line]), patch(
            'services.document_ai_service._phc_provisional_supplier', return_value={
                'no': 12, 'estab': 0, 'name': 'Supplier',
            }
        ), patch.object(service, '_intersol_series', return_value={
            'contract': {'ndos': 119, 'name': 'Contrat'},
            'delivery_note': {'ndos': 130, 'name': 'Bon Livraison Fourn.'},
        }), patch.object(service, '_load_contract', return_value=(contract, [source_line()])):
            with self.assertRaisesRegex(ValueError, 'Contrato selecionado está fechado'):
                service._plan(MagicMock(), document, 'BL-77', for_update=True)

    def test_stamps_are_stable_per_document_delivery_and_portal_line(self):
        header = service._header_stamp('DOC-1', 'BL-77', 'BO-CONTRACT')
        line = service._line_stamp('DOC-1', 'BL-77', 'LINE-1', 1)

        self.assertEqual(header, service._header_stamp('DOC-1', 'BL-77', 'BO-CONTRACT'))
        self.assertEqual(line, service._line_stamp('DOC-1', 'BL-77', 'LINE-1', 8))
        self.assertEqual(len(header), 25)
        self.assertEqual(len(line), 25)

    def test_delivery_number_is_found_on_distributed_sublines(self):
        document = {'lines': [{
            'line_id': 'PARENT',
            'sub_lines': [controlled_line(origin_delivery_note_number='BL-SUB')],
        }]}

        self.assertEqual(service._delivery_number(document, 'BL-SUB'), 'BL-SUB')


class FakeCursor:
    def __init__(self, lock=0):
        self.lock = lock
        self.rowcount = 1
        self.statements = []

    def execute(self, sql, *params):
        self.statements.append((sql, params))
        self._last_sql = sql
        return self

    def fetchone(self):
        if 'sp_getapplock' in self._last_sql:
            return (self.lock,)
        if 'MAX(OBRANO)' in self._last_sql:
            return (42,)
        return (1,)


class DocumentAiDeliveryNoteTransactionTests(unittest.TestCase):
    def _connection(self, cursor):
        connection = MagicMock()
        connection.cursor.return_value = cursor
        return connection

    def _patches(self, connection, plan, row_sets):
        return (
            patch.object(service, '_source_and_document', return_value=(
                {'kind': 'phc', 'phc_db': 'INTERSOL', 'phc_server': 'server'},
                {
                    'document_date': '2026-09-10',
                    'lines': [controlled_line()],
                    'customer': {'feid': 8}, 'supplier': {'supplier_no': 12},
                },
            )),
            patch('services.document_ai_service._effective_portal_lines', return_value=[controlled_line()]),
            patch.object(service, '_plan', return_value=plan),
            patch.object(service, '_rows', side_effect=row_sets),
            patch('services.phc_user_import_service._phc_conn_str', return_value='PHC-CONNECTION'),
            patch('pyodbc.connect', return_value=connection),
            patch('services.document_ai_service._phc_correspondence_user', return_value={'initials': 'TST'}),
        )

    def test_creation_is_atomic_and_preserves_contract_lineage(self):
        cursor = FakeCursor()
        connection = self._connection(cursor)
        inserted = []
        patches = self._patches(connection, plan_for_creation(), [[]])
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patch(
            'services.document_ai_service._phc_insert_values',
            side_effect=lambda _cursor, table, values: inserted.append((table, values)),
        ):
            result = service.create_delivery_note(
                {'lines': [controlled_line()]}, 'DOC-1', 'BL-77', 'tester',
                {'path': '/ged/bl77.pdf', 'name': 'bl77.pdf', 'bytes': b'%PDF'},
            )

        bi = next(values for table, values in inserted if table == 'BI')
        self.assertEqual((bi['obistamp'], bi['oobistamp']), ('BI-CONTRACT-1', 'BI-CONTRACT-1'))
        self.assertEqual((bi['qtt'], bi['qtt2'], bi['fechada']), (Decimal('3'), Decimal('3'), 1))
        self.assertEqual((bi['ettdeb'], bi['ttdeb']), (Decimal('150'), Decimal('150')))
        self.assertTrue(any(table == 'ANEXOS' for table, _values in inserted))
        self.assertTrue(any(table == 'BOT' for table, _values in inserted))
        self.assertEqual(result['ndos'], 130)
        self.assertEqual(result['line_stamps'][0]['origin_line_stamp'], 'BI-CONTRACT-1')
        connection.commit.assert_called_once()
        connection.rollback.assert_not_called()

    def test_repeat_after_lost_response_returns_existing_document(self):
        cursor = FakeCursor()
        connection = self._connection(cursor)
        plan = plan_for_creation()
        expected_line = service._line_stamp('DOC-1', 'BL-77', 'LINE-1', 1)
        existing = [{
            'bostamp': service._header_stamp('DOC-1', 'BL-77', 'BO-CONTRACT'),
            'ndos': 130, 'nmdos': 'Bon Livraison Fourn.', 'obrano': 41,
            'boano': 2026, 'dataobra': datetime(2026, 9, 10), 'anulado': 0,
        }]
        current = [{
            'bistamp': expected_line, 'obistamp': 'BI-CONTRACT-1',
            'oobistamp': 'BI-CONTRACT-1', 'qtt': Decimal('3'),
        }]
        patches = self._patches(connection, plan, [existing, current])
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patch(
            'services.document_ai_service._phc_insert_values'
        ) as insert:
            result = service.create_delivery_note(
                {'lines': [controlled_line()]}, 'DOC-1', 'BL-77', 'tester',
            )

        self.assertTrue(result['duplicate'])
        self.assertEqual(result['line_stamps'][0]['line_stamp'], expected_line)
        connection.rollback.assert_called_once()
        connection.commit.assert_not_called()
        insert.assert_not_called()

    def test_concurrent_lock_refusal_rolls_back_without_writes(self):
        cursor = FakeCursor(lock=-1)
        connection = self._connection(cursor)
        patches = self._patches(connection, plan_for_creation(), [])
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patch(
            'services.document_ai_service._phc_insert_values'
        ) as insert:
            with self.assertRaisesRegex(ValueError, 'Outra operação'):
                service.create_delivery_note(
                    {'lines': [controlled_line()]}, 'DOC-1', 'BL-77', 'tester',
                )

        connection.rollback.assert_called_once()
        connection.commit.assert_not_called()
        insert.assert_not_called()

    def test_partial_write_error_rolls_back(self):
        cursor = FakeCursor()
        connection = self._connection(cursor)
        patches = self._patches(connection, plan_for_creation(), [[]])
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patch(
            'services.document_ai_service._phc_insert_values', side_effect=RuntimeError('write failed')
        ):
            with self.assertRaisesRegex(RuntimeError, 'write failed'):
                service.create_delivery_note(
                    {'lines': [controlled_line()]}, 'DOC-1', 'BL-77', 'tester',
                )

        connection.rollback.assert_called_once()
        connection.commit.assert_not_called()


class DocumentAiDeliveryNoteFrontendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open('static/js/document_ai_extract.js', encoding='utf-8') as handle:
            cls.script = handle.read()
        with open('blueprints/document_ai.py', encoding='utf-8') as handle:
            cls.blueprint = handle.read()

    def test_create_and_distribute_actions_are_wired(self):
        self.assertIn("registerDocumentAiOriginAction('create_delivery_note'", self.script)
        self.assertIn("registerDocumentAiOriginAction('distribute_delivery_note'", self.script)
        self.assertIn('/delivery-note/preview', self.script)
        self.assertIn('/delivery-note/validate', self.script)
        self.assertIn("'Criada no PHC'", self.script)
        self.assertIn("filter((group) => !group.created)", self.script)

    def test_delivery_endpoints_are_management_only(self):
        self.assertIn("requested_view != 'management'", self.blueprint)
        self.assertIn("_document_ai_has_integration_access('delivery_note')", self.blueprint)
        self.assertIn('api_document_ai_delivery_note_preview', self.blueprint)
        self.assertIn('api_document_ai_delivery_note_validate', self.blueprint)


class DocumentAiDeliveryNoteLineageTests(unittest.TestCase):
    def test_confirmed_gdr_becomes_immediate_origin_and_preserves_contract_link(self):
        line = controlled_line()
        document = {
            'document_date': '2026-09-10', 'lines': [line],
            'customer': {'feid': 8}, 'supplier': {'supplier_no': 12},
        }
        record = type('Document', (), {})()
        record.docinstamp = 'DOC-1'
        record.file_name = 'invoice.pdf'
        record.processing_stage = 'management'
        record.last_processing_error = ''
        record.json_resultado = '{}'
        record.processing_meta_json = json.dumps({
            'llm_full_extraction': {'version': 4, 'document': document},
            'phc_origins': [{
                'stamp': 'BO-CONTRACT', 'document_type': 'contract',
                'origin_family': 'contract',
            }],
        })
        confirmed = {
            'status': 'confirmed', 'bostamp': 'BO-GDR', 'ndos': 130,
            'document_name': 'Bon Livraison Fourn.', 'number': 77,
            'year': 2026, 'date': '2026-09-10', 'phc_database': 'INTERSOL',
            'delivery_note_number': 'BL-77', 'contract_stamp': 'BO-CONTRACT',
            'line_stamps': [{
                'portal_line_index': 0, 'portal_subline_index': None,
                'portal_line_id': 'LINE-1', 'line_stamp': 'BI-GDR',
                'origin_line_stamp': 'BI-CONTRACT-1', 'quantity': 3,
            }],
        }

        def run(_document, **kwargs):
            kwargs['on_confirmed'](confirmed)
            return confirmed

        with patch.object(document_service.db.session, 'get', return_value=record), patch.object(
            document_service, 'get_cached_llm_extraction', return_value={'document': document}
        ), patch.object(document_service, 'preview_document_delivery_note', return_value={
            'delivery_note_number': 'BL-77',
            'contract': {'stamp': 'BO-CONTRACT'}, 'lines': [{}],
        }), patch.object(document_service, 'get_document_original_file', return_value={
            'path': __file__, 'file_name': 'source.txt', 'mime_type': 'text/plain',
        }), patch(
            'services.document_ai_phc_operation_service.run_document_phc_operation', side_effect=run
        ), patch.object(document_service, 'get_document_phc_origins', return_value=[]), patch.object(
            document_service, '_document_draft_version', return_value='V1'
        ):
            result = document_service.validate_document_delivery_note(
                'DOC-1', 'tester', delivery_number='BL-77',
            )

        saved = json.loads(record.processing_meta_json)
        saved_line = saved['llm_full_extraction']['document']['lines'][0]
        self.assertEqual(
            (saved_line['phc_origin_stamp'], saved_line['phc_origin_line_stamp']),
            ('BO-GDR', 'BI-GDR'),
        )
        families = {link['origin_family'] for link in saved_line['phc_origin_links']}
        self.assertEqual(families, {'contract', 'delivery_note'})
        self.assertEqual(saved_line['bc_allocations'][0]['origin_line_stamp'], 'BI-GDR')
        gdr = next(item for item in saved['phc_origins'] if item['stamp'] == 'BO-GDR')
        self.assertEqual(gdr['lines'][0]['obistamp'], 'BI-CONTRACT-1')
        self.assertTrue(result['ok'])

    def test_second_click_reuses_confirmed_portal_operation_without_repreview_or_phc_write(self):
        line = controlled_line(
            phc_origin_stamp='BO-GDR', phc_origin_line_stamp='BI-GDR',
            bostamp='BO-GDR', bistamp='BI-GDR',
        )
        document = {'lines': [line], 'customer': {'feid': 8}, 'supplier': {'supplier_no': 12}}
        operation_type = f"delivery_note_{hashlib.sha1(b'BL-77').hexdigest()[:12]}"
        confirmed = {
            'status': 'confirmed', 'bostamp': 'BO-GDR', 'ndos': 130,
            'phc_database': 'INTERSOL', 'delivery_note_number': 'BL-77',
            'line_stamps': [{'portal_line_id': 'LINE-1', 'line_stamp': 'BI-GDR'}],
            'message': 'GdR já criada.',
        }
        record = type('Document', (), {})()
        record.processing_stage = 'management'
        record.processing_meta_json = json.dumps({
            'phc_operations': {operation_type: confirmed},
            'llm_full_extraction': {'version': 4, 'document': document},
        })
        record.file_name = 'source.txt'
        record.last_processing_error = ''
        with patch.object(document_service.db.session, 'get', return_value=record), patch.object(
            document_service, 'get_cached_llm_extraction', return_value={'document': document}
        ), patch.object(document_service, 'get_document_original_file', return_value={
            'path': __file__, 'file_name': 'source.txt', 'mime_type': 'text/plain',
        }), patch.object(
            document_service, 'get_document_phc_origins', return_value=[]
        ), patch.object(document_service, '_document_draft_version', return_value='V2'), patch.object(
            service, 'create_delivery_note'
        ) as create:
            result = document_service.validate_document_delivery_note(
                'DOC-1', 'tester', delivery_number='BL-77',
            )

        create.assert_not_called()
        self.assertEqual(result['bostamp'], 'BO-GDR')


if __name__ == '__main__':
    unittest.main()
