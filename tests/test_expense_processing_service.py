import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services import colaborador_despesas_service as service


class ExpenseProcessingServiceTests(unittest.TestCase):
    def test_new_expense_without_accounting_lines_can_be_listed(self):
        session = MagicMock()
        session.execute.return_value.mappings.return_value.all.return_value = []
        item = {
            'stamp': 'NEW_EXPENSE', 'valor': 10.20, 'ccusto': 'PT001',
            'taxaiva': 0, 'tabiva': '', 'obs': 'Comentario do colaborador',
        }
        with patch.object(service, 'db', SimpleNamespace(session=session)):
            service._attach_processing_details([item])

        self.assertEqual(10.20, item['linhas_total_com_iva'])
        self.assertEqual(10.20, item['linhas_total_sem_iva'])
        self.assertEqual(0.0, item['linhas_total_iva'])
        self.assertEqual(0.0, item['diferenca'])
        line = item['accounting_lines'][0]
        self.assertEqual('', line['stamp'])
        self.assertEqual('', line['artigo_ref'])
        self.assertEqual('', line['tabiva'])
        self.assertEqual('PT001', line['ccusto'])
        self.assertEqual('Comentario do colaborador', item['obs'])
        session.commit.assert_not_called()
        self.assertEqual(1, session.execute.call_count)

    def test_new_expense_does_not_break_other_users_or_change_saved_splits(self):
        session = MagicMock()
        session.execute.return_value.mappings.return_value.all.return_value = [
            {'DESPLINHASTAMP': 'CLASSIFIED', 'DESPCONTABSTAMP': 'C1',
             'TOTAL_SEM_IVA': Decimal('6.00'), 'VALOR_IVA': Decimal('1.38'),
             'TOTAL_COM_IVA': Decimal('7.38'), 'ARTIGO_REF': 'ART1'},
            {'DESPLINHASTAMP': 'CLASSIFIED', 'DESPCONTABSTAMP': 'C2',
             'TOTAL_SEM_IVA': Decimal('4.00'), 'VALOR_IVA': Decimal('0.92'),
             'TOTAL_COM_IVA': Decimal('4.92'), 'ARTIGO_REF': 'ART2'},
        ]
        items = [
            {'stamp': 'CLASSIFIED', 'valor': 13.30},
            {'stamp': 'NEW_EXPENSE', 'valor': 10.20, 'taxaiva': 23, 'tabiva': '2'},
        ]
        with patch.object(service, 'db', SimpleNamespace(session=session)):
            service._attach_processing_details(items)

        self.assertEqual(['C1', 'C2'], [line['stamp'] for line in items[0]['accounting_lines']])
        self.assertEqual(12.30, items[0]['linhas_total_com_iva'])
        self.assertEqual(1.0, items[0]['diferenca'])
        self.assertEqual(8.29, items[1]['linhas_total_sem_iva'])
        self.assertEqual(1.91, items[1]['linhas_total_iva'])
        self.assertEqual(10.20, items[1]['linhas_total_com_iva'])

    def test_expense_created_after_first_listing_needs_no_schema_backfill(self):
        session = MagicMock()
        result = session.execute.return_value.mappings.return_value
        result.all.side_effect = [[], []]
        with patch.object(service, 'db', SimpleNamespace(session=session)):
            service._attach_processing_details([{'stamp': 'FIRST', 'valor': 10.20}])
            new_item = {'stamp': 'SECOND', 'valor': 5.54}
            service._attach_processing_details([new_item])
        self.assertEqual(5.54, new_item['linhas_total_com_iva'])
        self.assertEqual(0, new_item['diferenca'])
        session.commit.assert_not_called()

    def test_phc_target_is_resolved_only_from_expense_feid(self):
        company = {'feid': 7, 'nome': 'HSOLS MAROC', 'phc_db': 'HSOLS_MA', 'phc_server': 'sql-ma'}
        with patch.object(service, '_expense_company_by_feid', return_value=company) as find_company, \
             patch.object(service, '_phc_conn_str', return_value='safe-target') as build_connection:
            resolved, connection = service._expense_phc_target(7)
        self.assertEqual(company, resolved)
        self.assertEqual('safe-target', connection)
        find_company.assert_called_once_with(7)
        build_connection.assert_called_once_with('HSOLS_MA', 'sql-ma')

    def test_missing_phc_company_configuration_is_not_an_empty_result(self):
        with patch.object(service, '_expense_company_by_feid', return_value={'feid': 9, 'phc_db': ''}):
            with self.assertRaisesRegex(service.ExpensePhcConfigurationError, 'Empresa sem configuração PHC'):
                service._expense_phc_target(9)

    def test_cost_center_validation_uses_exact_phc_lookup_without_list_limit(self):
        class FakeRow:
            CCUSTO = 'FR1888'

        class FakeCursor:
            def __init__(self):
                self.executions = []

            def execute(self, sql, *params):
                self.executions.append((sql, params))
                return self

            def fetchall(self):
                return [('CCUSTO',), ('INACTIVO',)]

            def fetchone(self):
                return FakeRow()

        class FakeConnection:
            def __init__(self):
                self.cursor_instance = FakeCursor()

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def cursor(self):
                return self.cursor_instance

        connection = FakeConnection()
        with patch.object(service, '_expense_phc_target', return_value=({}, 'safe-target')), \
             patch.object(service.pyodbc, 'connect', return_value=connection):
            result = service._expense_cost_center_by_code(1, ' fr1888 ')

        self.assertEqual('FR1888', result)
        exact_sql, exact_params = connection.cursor_instance.executions[-1]
        self.assertIn('UPPER(?)', exact_sql)
        self.assertIn('INACTIVO', exact_sql)
        self.assertEqual(('fr1888',), exact_params)

    def test_preflight_aggregates_all_local_anomalies_before_phc(self):
        lines = [{
            'DESPLINHASTAMP': 'EXP1', 'DATA_DESPESA': '2026-09-15', 'VALOR': None,
            'CAMINHO': '', 'MOEDA': 'EURO', 'PENO': 0, 'ACCOUNTING_LINES': [{
                'artigo_ref': '', 'ccusto': '', 'tabiva': '', 'taxaiva': '23',
                'total_sem_iva': '8.00', 'valor_iva': '1.00', 'total_com_iva': '-10.00',
            }],
        }]
        errors = service._expense_launch_preflight(lines, {'phc_db': 'HSOLS_PT', 'phc_server': 'sql'})
        expected = ('Moeda ISO inválida', 'total em falta', 'justificativo em falta', 'Artigo em falta',
                    'Centro de Custo em falta', 'IVA em falta', 'valor negativo', 'Totais incoerentes')
        for message in expected:
            self.assertTrue(any(message in error for error in errors), message)

    def test_money_rounding_is_decimal_and_per_line(self):
        net_a, vat_a = service._vat_amounts_from_gross('0.10', '23')
        net_b, vat_b = service._vat_amounts_from_gross('0.20', '23')
        self.assertEqual(Decimal('0.30'), (net_a + vat_a + net_b + vat_b).quantize(Decimal('0.01')))

    def test_reference_migration_preserves_useful_text_in_history(self):
        migration = (Path(__file__).resolve().parents[1] / 'migrations' / 'tp073_expense_processing_post_receipt.sql').read_text(encoding='utf-8')
        self.assertIn("'MIGRACAO_TP073'", migration)
        self.assertIn('STRING_ESCAPE', migration)
        self.assertIn("UPDATE dbo.COLAB_DESPESA_CONTAB_LINHA SET REFERENCIA = N''", migration)


if __name__ == '__main__':
    unittest.main()
