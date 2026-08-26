import unittest

from services.document_ai_inbox_access_service import allowed_inbox_views, is_inbox_view_allowed


class DocumentAiInboxAccessServiceTests(unittest.TestCase):
    def test_default_mapping_is_explicit(self):
        self.assertEqual([item["value"] for item in allowed_inbox_views("ldias")], ["home"])
        self.assertEqual([item["value"] for item in allowed_inbox_views("msilva")], ["management"])
        self.assertEqual([item["value"] for item in allowed_inbox_views("arocha")], ["management"])

    def test_unknown_user_fails_closed(self):
        self.assertEqual(allowed_inbox_views("admin"), [])
        self.assertEqual(allowed_inbox_views(""), [])

    def test_multiple_views_are_supported_in_defined_order(self):
        config = {"DOC_AI_INBOX_VIEW_ACCESS": {"user": ["accounting", "home"]}}
        self.assertEqual(
            [item["value"] for item in allowed_inbox_views("USER", config)],
            ["home", "accounting"],
        )

    def test_invalid_json_configuration_fails_closed(self):
        self.assertEqual(allowed_inbox_views("ldias", {"DOC_AI_INBOX_VIEW_ACCESS": "{"}), [])

    def test_view_check_rejects_non_authorized_view(self):
        self.assertTrue(is_inbox_view_allowed("msilva", "management"))
        self.assertFalse(is_inbox_view_allowed("msilva", "home"))


if __name__ == "__main__":
    unittest.main()
