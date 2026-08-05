import unittest

from modules.gr_subcontractor_measurements.service import _contract_work_code


class ContractWorkCodeTests(unittest.TestCase):
    def test_cost_center_is_canonical_when_header_fields_differ(self):
        self.assertEqual(
            _contract_work_code({"CCUSTO": "IS2271", "PROCESSO": "IS1967"}),
            "IS2271",
        )

    def test_process_is_used_when_cost_center_is_empty(self):
        self.assertEqual(
            _contract_work_code({"CCUSTO": "", "PROCESSO": "IS2271"}),
            "IS2271",
        )


if __name__ == "__main__":
    unittest.main()
