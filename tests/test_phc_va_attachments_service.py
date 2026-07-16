import unittest
from unittest.mock import patch

from services.phc_va_attachments_service import (
    _deterministic_local_stamp,
    _normalise_fullname,
    resolve_attachment_path,
)


class PhcVaAttachmentsServiceTests(unittest.TestCase):
    def test_normalise_fullname_replaces_legacy_ged_alias(self):
        self.assertEqual(
            _normalise_fullname(r"\\servidor\ged\HSOLS_PT\file.pdf"),
            r"\\10.0.1.11\ged\HSOLS_PT\file.pdf",
        )

    def test_deterministic_stamp_is_stable_and_25_characters(self):
        first = _deterministic_local_stamp("HSOLS_PT", "ABC")
        second = _deterministic_local_stamp("HSOLS_PT", "ABC")
        self.assertEqual(first, second)
        self.assertEqual(len(first), 25)

    def test_resolver_prefers_existing_original_path(self):
        row = {
            "FULLNAME": r"\\10.0.1.11\ged\HSOLS_PT\car\document.pdf",
            "FNAME": "document",
            "FEXT": "pdf",
            "MATRICULA": "AA-00-AA",
        }
        with patch("services.phc_va_attachments_service.os.path.isfile", return_value=True), patch(
            "services.phc_va_attachments_service._filename_index"
        ) as filename_index:
            resolved = resolve_attachment_path("HSOLS_PT", row)
        self.assertEqual(resolved, row["FULLNAME"])
        filename_index.assert_not_called()

    def test_resolver_uses_plate_to_disambiguate_relocated_file(self):
        row = {
            "FULLNAME": r"\\servidor\ged\HSOLS_FR\old\controle.pdf",
            "FNAME": "controle",
            "FEXT": "pdf",
            "MATRICULA": "DR-353-KH",
        }
        index = {
            "controle.pdf": (
                r"\\10.0.1.11\ged\HSOLS_FR\AA-111-AA\controle.pdf",
                r"\\10.0.1.11\ged\HSOLS_FR\DR-353-KH\controle.pdf",
            )
        }

        def is_file(path):
            return "\\old\\" not in path

        with patch("services.phc_va_attachments_service.os.path.isfile", side_effect=is_file), patch(
            "services.phc_va_attachments_service._filename_index", return_value=index
        ):
            resolved = resolve_attachment_path("HSOLS_FR", row)
        self.assertIn("DR-353-KH", resolved)

    def test_resolver_rejects_ambiguous_relocated_file(self):
        row = {
            "FULLNAME": r"\\servidor\ged\HSOLS_FR\old\controle.pdf",
            "FNAME": "controle",
            "FEXT": "pdf",
            "MATRICULA": "",
        }
        index = {
            "controle.pdf": (
                r"\\10.0.1.11\ged\HSOLS_FR\one\controle.pdf",
                r"\\10.0.1.11\ged\HSOLS_FR\two\controle.pdf",
            )
        }

        def is_file(path):
            return "\\old\\" not in path

        with patch("services.phc_va_attachments_service.os.path.isfile", side_effect=is_file), patch(
            "services.phc_va_attachments_service._filename_index", return_value=index
        ):
            self.assertIsNone(resolve_attachment_path("HSOLS_FR", row))


if __name__ == "__main__":
    unittest.main()
