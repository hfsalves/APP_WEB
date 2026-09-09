import copy
import json
import unittest
from contextlib import ExitStack
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch

from services import document_ai_preinvoice_service as pf
from services import document_ai_service as svc


def fixture():
    document = {'document_type': 'invoice', 'document_number': 'TEST-1',
                'document_date': '2026-09-09', 'currency': 'EUR',
                'customer': {'feid': 1}, 'supplier': {'supplier_no': 1},
                'lines': [{'article_ref': 'A', 'quantity': 2, 'net_amount': 20,
                           'cost_center': 'OBRA', 'tax_rate': 20}],
                'totals': {'net_total': 20, 'tax_total': 4, 'gross_total': 24}}
    header = {'bostamp': 'BO-SOURCE', 'ndos': 102, 'no': 1, 'estab': 0, 'moeda': 'EURO',
              'fechada': False, 'anulado': False}
    line = {'bistamp': 'BI-SOURCE', 'bostamp': 'BO-SOURCE', 'ref': 'A', 'qtt': 5,
            'qtt2': 0, 'reused_qty': 0, 'iva': 20, 'tabiva': 2, 'ivaincl': False,
            'edebito': 10, 'debito': 2004.82, 'ccusto': 'OBRA', 'fechada': False,
            'oobostamp': '', 'obistamp': ''}
    return document, header, line


class PreinvoicePlanningTests(unittest.TestCase):
    def plan(self, document, header, line):
        return pf.plan_preinvoice(document, [line], {header['bostamp']: header})

    def test_partial_purchase_order(self):
        document, header, line = fixture()
        result = self.plan(document, header, line)
        self.assertEqual(result[0]['quantity'], Decimal(2))
        self.assertEqual(result[0]['source']['bistamp'], 'BI-SOURCE')

    def test_subcontract_requires_situation(self):
        document, header, line = fixture()
        header['ndos'] = 128
        with self.assertRaisesRegex(ValueError, 'Situacao'):
            self.plan(document, header, line)

    def test_contract_and_situation_supported(self):
        for ndos in (119, 129):
            with self.subTest(ndos=ndos):
                document, header, line = fixture()
                header['ndos'] = ndos
                self.assertEqual(len(self.plan(document, header, line)), 1)

    def test_gr360_order_series_two_and_project_inheritance(self):
        document, header, line = fixture()
        header.update(ndos=2, nmdos='Bon Commande Fournisseur')
        del document['lines'][0]['cost_center']
        document['origin_project'] = {'ccusto': 'OBRA'}
        self.assertEqual(self.plan(document, header, line)[0]['ccusto'], 'OBRA')

    def test_immediate_delivery_note_supersedes_order(self):
        document, header, line = fixture()
        delivery = {**line, 'bistamp': 'BI-GDR', 'bostamp': 'BO-GDR', 'obistamp': 'BI-SOURCE'}
        result = pf.plan_preinvoice(document, [line, delivery], {
            'BO-SOURCE': header, 'BO-GDR': {**header, 'bostamp': 'BO-GDR', 'ndos': 130}})
        self.assertEqual(result[0]['source']['bistamp'], 'BI-GDR')

    def test_explicit_ancestor_is_rejected_when_delivery_selected(self):
        document, header, line = fixture()
        document['lines'][0]['bc_allocations'] = [{'origin_stamp': 'BO-SOURCE',
            'origin_line_stamp': 'BI-SOURCE', 'quantity': 2}]
        delivery = {**line, 'bistamp': 'BI-GDR', 'bostamp': 'BO-GDR', 'obistamp': 'BI-SOURCE'}
        with self.assertRaisesRegex(ValueError, 'GdR/Situacao'):
            pf.plan_preinvoice(document, [line, delivery], {'BO-SOURCE': header,
                'BO-GDR': {**header, 'bostamp': 'BO-GDR', 'ndos': 130}})

    def test_ambiguity_is_not_guessed(self):
        document, header, line = fixture()
        with self.assertRaisesRegex(ValueError, 'distribui'):
            pf.plan_preinvoice(document, [line, {**line, 'bistamp': 'OTHER'}], {'BO-SOURCE': header})

    def test_closed_or_consumed_source_rejected(self):
        for updates in ({'fechada': True}, {'qtt2': 4}, {'reused_qty': 4}):
            document, header, line = fixture()
            line.update(updates)
            with self.assertRaises(ValueError):
                self.plan(document, header, line)

    def test_shared_origin_cannot_overallocate_across_sublines(self):
        document, header, line = fixture()
        line['qtt'] = 3
        document['lines'] = [{'sublines': [document['lines'][0], copy.deepcopy(document['lines'][0])]}]
        with self.assertRaisesRegex(ValueError, 'quantidade disponivel'):
            self.plan(document, header, line)

    def test_multiple_origins_and_sublines(self):
        document, header, line = fixture()
        child = {**document['lines'][0], 'quantity': 1, 'net_amount': 10,
                 'phc_origin_line_stamp': 'BI-SOURCE'}
        second = {**child, 'phc_origin_line_stamp': 'BI-OTHER'}
        document['lines'] = [{'quantity': 99, 'net_amount': 999, 'sublines': [child, second]}]
        other = {**line, 'bistamp': 'BI-OTHER'}
        result = pf.plan_preinvoice(document, [line, other], {'BO-SOURCE': header})
        self.assertEqual(sum(p['net'] for p in result), Decimal(20))

    def test_rejects_mismatch_in_price_tax_worksite_and_totals(self):
        for key, value in [('net_amount', 21), ('tax_rate', 21), ('cost_center', 'OTHER'),
                           ('quantity', 'NaN'), ('article_ref', '')]:
            with self.subTest(field=key):
                document, header, line = fixture()
                document['lines'][0][key] = value
                with self.assertRaises(ValueError):
                    self.plan(document, header, line)


class PreinvoiceTransactionTests(unittest.TestCase):
    def run_case(self, *, existing=None, failure=None, missing_pdf=False):
        document, header, line = fixture()
        origins = [{'stamp': 'BO-SOURCE', 'phc_database': 'HSOLS_FR'}]
        connection = Mock()
        cursor = connection.cursor.return_value
        cursor.execute.return_value.fetchone.return_value = [1]
        supplier = {'no': 1, 'estab': 0, 'name': 'Test', 'tax_id': '', 'address': '',
                    'city': '', 'postal_code': ''}
        pdf_checks = Mock(return_value=not missing_pdf)
        inserts = []

        def rows(_cursor, sql, *params):
            if 'A.UNIQUEID' in sql:
                return [existing] if existing else []
            if 'FROM TS' in sql:
                return [{'ndos': 218, 'nmdos': 'Pre-Facture'}]
            if 'FROM FO' in sql:
                return [{'no': 1, 'estab': 0, 'moeda': 'EURO', 'adoc': 'TEST-1', 'doccode': 55}]
            if 'TOP 1 FULLNAME' in sql:
                return [{'fullname': r'\\server\ged\test.pdf'}]
            if 'B.*' in sql:
                return [header]
            if 'SELECT * FROM BI' in sql:
                return [line]
            if 'SELECT RECSTAMP' in sql:
                return []
            self.fail(sql)

        def insert(_cursor, table, values):
            inserts.append((table, dict(values)))
            if table == failure:
                raise RuntimeError('injected failure')

        with ExitStack() as stack:
            stack.enter_context(patch('pyodbc.connect', return_value=connection))
            stack.enter_context(patch('services.phc_user_import_service._phc_conn_str', return_value='test'))
            stack.enter_context(patch.object(pf, '_rows', side_effect=rows))
            for name, value in {
                '_phc_origin_source': {'kind': 'phc', 'phc_db': 'HSOLS_FR'},
                '_phc_provisional_supplier': supplier,
                '_phc_provisional_purchase_doc_config': {'doccode': 55, 'docname': 'V/Facture'},
                '_phc_tax_configuration': ({2: Decimal(20)}, {Decimal(20): 2}),
                '_phc_base_currency_per_euro': Decimal('200.482'),
                '_phc_provisional_effective_datetime': datetime(2026, 9, 9),
                '_phc_correspondence_user': {'initials': 'TST'},
                '_phc_table_columns': {'bostamp','ndos','obrano','bistamp','obistamp','oobistamp',
                                      'oobostamp','qtt','qtt2','uniqueid','recstamp','fullname','descricao'},
            }.items():
                stack.enter_context(patch.object(svc, name, return_value=value))
            stack.enter_context(patch.object(svc, '_document_ai_pdf_is_confirmed', pdf_checks))
            stack.enter_context(patch.object(svc, '_phc_insert_values', side_effect=insert))
            try:
                result = pf.create_preinvoice(document, origins, {'fostamp': 'FO-1',
                    'phc_database': 'HSOLS_FR'}, 'DOC-1', b'pdf', 'tester')
                return result, connection, inserts
            except Exception:
                connection.commit.assert_not_called()
                connection.rollback.assert_called_once()
                connection.close.assert_called_once()
                raise

    def test_creation_keeps_immediate_stamps_and_unsatisfied_new_lines(self):
        result, connection, inserts = self.run_case()
        self.assertTrue(result['ged_confirmed'])
        bi = next(values for table, values in inserts if table == 'BI')
        self.assertEqual(bi['obistamp'], 'BI-SOURCE')
        self.assertEqual(bi['oobistamp'], 'BI-SOURCE')
        self.assertEqual(bi['oobostamp'], '')
        self.assertEqual(bi['bostamp'], result['bostamp'])
        self.assertEqual(bi['qtt2'], 0)
        self.assertEqual(bi['ndoc'], 55)
        connection.commit.assert_called_once()
        self.assertEqual({table for table, _ in inserts}, {'BO','BO2','BO3','BI','BI2','BOT','ANEXOS'})

    def test_ged_or_sql_failure_rolls_back(self):
        with self.assertRaisesRegex(ValueError, 'PDF original'):
            self.run_case(missing_pdf=True)
        for table in ('BI', 'ANEXOS'):
            with self.subTest(table=table), self.assertRaisesRegex(RuntimeError, 'injected'):
                self.run_case(failure=table)

    def test_retry_recovers_same_preinvoice_without_writing(self):
        document, _, _ = fixture()
        existing = {'bostamp': 'RECOVERED', 'ndos': 218, 'nmdos': 'Pre-Facture',
                    'obrano': 123, 'boano': 2026, 'anexosstamp': 'A', 'fullname': 'test.pdf',
                    'descricao': pf.payload_fingerprint(document, [{'stamp': 'BO-SOURCE'}])}
        result, connection, inserts = self.run_case(existing=existing)
        self.assertTrue(result['duplicate'])
        self.assertEqual(result['bostamp'], 'RECOVERED')
        self.assertEqual(inserts, [])
        connection.commit.assert_not_called()

    def test_changed_retry_does_not_create_second_object(self):
        with self.assertRaisesRegex(ValueError, 'dados diferentes'):
            self.run_case(existing={'descricao': 'other'})


class PreinvoiceWorkflowTests(unittest.TestCase):
    def test_failure_does_not_validate_or_distribute_management(self):
        document, _, _ = fixture()
        record = SimpleNamespace(docinstamp='DOC-1', json_resultado=json.dumps(document),
            processing_meta_json='{}', doc_type_detected='invoice', invoice_type='unknown',
            extracted_text='', management_validated=False, reception_validated=True,
            accounting_validated=False)
        with ExitStack() as stack:
            for name in ('get', 'execute', 'refresh'):
                stack.enter_context(patch.object(svc.db.session, name, return_value=record if name == 'get' else Mock()))
            stack.enter_context(patch.object(svc, '_document_draft_version', return_value='1'))
            stack.enter_context(patch.object(svc, '_infer_invoice_type', return_value='materials'))
            stack.enter_context(patch.object(svc, 'preflight_document_inbox_stage', return_value={'ok': True}))
            stack.enter_context(patch.object(svc, '_integrate_management_preinvoice', side_effect=ValueError('no PDF')))
            distribution = stack.enter_context(patch('services.document_ai_distribution_service.apply_document_distribution'))
            with self.assertRaisesRegex(ValueError, 'no PDF'):
                svc.validate_document_inbox_stage('DOC-1', 'management', 'tester')
        self.assertFalse(record.management_validated)
        distribution.assert_not_called()

    def test_permission_is_required_before_any_connection(self):
        document, _, _ = fixture()
        with patch('pyodbc.connect') as connect, self.assertRaises(PermissionError):
            svc._integrate_management_preinvoice(SimpleNamespace(), document, 'tester', {})
        connect.assert_not_called()

    def test_credit_note_does_not_use_preinvoice_circuit(self):
        self.assertEqual(svc._integrate_management_preinvoice(None, {'document_type': 'credit_note'}, 'test'), {})

    def test_recovered_operation_restores_portal_origin_without_overwriting_reception(self):
        document, _, _ = fixture()
        meta = {'phc_integration': {'fostamp': 'FO-RECEPTION'}, 'phc_origins': []}
        record = SimpleNamespace(docinstamp='DOC-1', processing_meta_json=json.dumps(meta))
        confirmed = {'bostamp':'BO-PF','ndos':218,'document_name':'Pre-Facture',
                     'number':1,'year':2026,'phc_database':'HSOLS_FR'}
        with patch.object(svc, '_document_absolute_path', return_value=__file__), patch(
                'services.document_ai_phc_operation_service.run_document_phc_operation', return_value=confirmed):
            svc._integrate_management_preinvoice(record, document, 'test', {'proforma_invoice': True})
        saved = json.loads(record.processing_meta_json)
        self.assertEqual(saved['phc_integration']['fostamp'], 'FO-RECEPTION')
        self.assertEqual(saved['phc_origins'][0]['stamp'], 'BO-PF')


if __name__ == '__main__':
    unittest.main()
