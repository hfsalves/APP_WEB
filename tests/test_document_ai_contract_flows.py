import unittest
from pathlib import Path

from modules.gr_subcontractor_measurements.service import _stable_operation_stamp


ROOT = Path(__file__).resolve().parents[1]


class DocumentAiContractFlowTests(unittest.TestCase):
    def test_stse_operation_stamp_is_stable_and_phc_sized(self):
        first = _stable_operation_stamp('DOC_AI:DOC1:STSE:CONTRACT1')
        self.assertEqual(first, _stable_operation_stamp('DOC_AI:DOC1:STSE:CONTRACT1'))
        self.assertEqual(len(first), 25)
        self.assertNotEqual(first, _stable_operation_stamp('DOC_AI:DOC2:STSE:CONTRACT1'))

    def test_contract_and_subcontract_actions_reuse_transactional_source_flow(self):
        script = (ROOT / 'static/js/document_ai_extract.js').read_text(encoding='utf-8')
        service = (ROOT / 'services/document_ai_purchase_order_service.py').read_text(encoding='utf-8')
        routes = (ROOT / 'blueprints/document_ai.py').read_text(encoding='utf-8')

        for action in ('create_contract', 'correct_contract', 'create_subcontract', 'correct_subcontract'):
            self.assertIn(f"registerDocumentAiOriginAction('{action}'", script)
        self.assertIn("'contract': {", service)
        self.assertIn("'subcontract': {", service)
        self.assertIn('sp_getapplock', service)
        self.assertIn("family not in {'contract', 'subcontract'}", routes)

    def test_stse_action_calls_existing_measurement_module_and_preserves_lineage(self):
        script = (ROOT / 'static/js/document_ai_extract.js').read_text(encoding='utf-8')
        service = (ROOT / 'services/document_ai_service.py').read_text(encoding='utf-8')
        module = (ROOT / 'modules/gr_subcontractor_measurements/service.py').read_text(encoding='utf-8')

        self.assertIn("registerDocumentAiOriginAction('create_work_situation'", script)
        self.assertIn('create_measurement_auto(payload, user)', service)
        self.assertIn("'origin_family': 'work_situation'", service)
        self.assertIn("'parent_bistamp': row['source_line_stamp']", service)
        self.assertIn('operation_key', module)
        self.assertIn('sp_getapplock', module)


if __name__ == '__main__':
    unittest.main()
