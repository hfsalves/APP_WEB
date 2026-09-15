import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from services import colaborador_despesas_service as service


class ExpenseProcessingServiceTests(unittest.TestCase):
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
