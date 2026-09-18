"""Booking photos use the session cover without changing photographic records."""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services import booking_portal_service as portal


class BookingPortalPhotoTests(unittest.TestCase):
    def setUp(self):
        self.session = MagicMock()
        self.db_patch = patch.object(portal, "db", SimpleNamespace(session=self.session))
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        self.table_patch = patch.object(portal, "_table_exists", return_value=True)
        self.table_patch.start()
        self.addCleanup(self.table_patch.stop)

    def session_results(self, rows, session_id="session-newest"):
        session_result = MagicMock()
        session_result.mappings.return_value.first.return_value = {"ID": session_id}
        photos_result = MagicMock()
        photos_result.mappings.return_value.all.return_value = rows
        self.session.execute.side_effect = [session_result, photos_result]

    def test_configured_session_cover_precedes_other_ready_photos(self):
        self.session_results([
            {"IS_COVER": 1, "ENHANCED_PATH": "/static/session/cover.jpg", "STATUS": "melhorada"},
            {"IS_COVER": 0, "ENHANCED_PATH": "/static/session/other.jpg", "STATUS": "melhorada"},
        ])

        photos = portal.get_fotos_melhoradas_alojamento("property-1")

        self.assertEqual(photos[0]["url"], "https://szeroapp.com/static/session/cover.jpg")
        self.assertTrue(photos[0]["capa"])
        self.assertFalse(photos[1]["capa"])
        selection_sql = str(self.session.execute.call_args_list[0].args[0])
        files_sql = str(self.session.execute.call_args_list[1].args[0])
        self.assertIn("ORDER BY COALESCE(S.UPDATED_AT, S.CREATED_AT) DESC", selection_sql)
        self.assertIn("ORDER BY CASE WHEN ISNULL(F.IS_COVER, 0) = 1 THEN 0 ELSE 1 END", files_sql)
        self.assertEqual(self.session.execute.call_args_list[1].args[1], {"session_id": "session-newest"})
        self.session.commit.assert_not_called()

    def test_unprocessed_configured_cover_uses_original_not_legacy_cover(self):
        self.session_results([
            {"IS_COVER": 1, "ORIGINAL_PATH": "/static/session/original.jpg", "STATUS": "carregada"},
        ])

        self.assertEqual(
            portal.get_foto_principal("property-1"),
            "https://szeroapp.com/static/session/original.jpg",
        )
        self.assertEqual(self.session.execute.call_count, 2)

    def test_unready_enhancement_does_not_replace_selected_original(self):
        self.session_results([
            {
                "IS_COVER": 1,
                "ORIGINAL_PATH": "/static/session/original.jpg",
                "ENHANCED_PATH": "/static/session/unfinished.jpg",
                "STATUS": "processando",
            },
            {"IS_COVER": 0, "ORIGINAL_PATH": "/static/session/private-original.jpg", "STATUS": "carregada"},
        ])

        photos = portal.get_fotos_melhoradas_alojamento("property-1")

        self.assertEqual(len(photos), 1)
        self.assertTrue(photos[0]["url"].endswith("/original.jpg"))

    def test_heic_heif_and_other_unrenderable_cover_originals_use_existing_jpeg_preview(self):
        for extension in ("HEIC", "heif", "raw"):
            with self.subTest(extension=extension):
                self.session_results([
                    {
                        "IS_COVER": 1,
                        "ORIGINAL_PATH": f"/static/session/original.{extension}",
                        "THUMB_PATH": "/static/session/thumbs/cover.jpg",
                        "STATUS": "carregada",
                    },
                ])

                self.assertEqual(
                    portal.get_foto_principal("property-1"),
                    "https://szeroapp.com/static/session/thumbs/cover.jpg",
                )

    def test_unrenderable_original_without_preview_is_not_exposed(self):
        self.session_results([
            {"IS_COVER": 1, "ORIGINAL_PATH": "/static/session/original.heic", "STATUS": "carregada"},
        ])

        self.assertEqual(portal.get_fotos_melhoradas_alojamento("property-1"), [])

    def test_session_without_explicit_cover_uses_first_ready_photo(self):
        self.session_results([
            {"IS_COVER": 0, "ENHANCED_PATH": "/static/session/first.jpg", "STATUS": "melhorada"},
        ])

        self.assertEqual(
            portal.get_foto_principal("property-1"),
            "https://szeroapp.com/static/session/first.jpg",
        )
        self.assertEqual(self.session.execute.call_count, 2)

    def test_legacy_cover_is_used_only_without_usable_session_photos(self):
        self.session.execute.return_value.mappings.return_value.first.return_value = {
            "CAMINHO": "/static/property/legacy.jpg"
        }
        with patch.object(portal, "get_fotos_melhoradas_alojamento", return_value=[]):
            cover = portal.get_foto_principal("property-1")

        self.assertEqual(cover, "https://szeroapp.com/static/property/legacy.jpg")
        query = str(self.session.execute.call_args.args[0])
        self.assertIn("ISNULL(CHECKIN, 0) = 0", query)
        self.assertIn("ISNULL(ATIVO, 1) = 1", query)
        self.assertIn("ISNULL(CAPA, 0) = 1", query)
        self.assertIn("LTRIM(RTRIM(ISNULL(CAMINHO, ''))) <> ''", query)

    def test_missing_session_tables_and_blank_ids_do_not_query_photos(self):
        with patch.object(portal, "_table_exists", return_value=False):
            self.assertEqual(portal.get_fotos_melhoradas_alojamento("property-1"), [])
        self.assertEqual(portal.get_fotos_melhoradas_alojamento("  "), [])
        self.session.execute.assert_not_called()

    def test_detail_gallery_starts_with_same_session_cover_and_has_no_legacy(self):
        cover = {"url": "https://photos.test/cover.jpg", "thumb_url": "https://photos.test/thumb.jpg", "capa": True}
        other = {"url": "https://photos.test/other.jpg", "capa": False}
        with (
            patch.object(portal, "get_fotos_melhoradas_alojamento", return_value=[cover, other, cover]),
            patch.object(portal, "get_fotos_alojamento") as legacy,
        ):
            details = portal._decorate_alojamento({"ALSTAMP": "property-1", "NOME": "Property"}, include_gallery=True)

        self.assertEqual(details["foto_principal"], cover["url"])
        self.assertEqual([photo["url"] for photo in details["fotos"]], [cover["url"], other["url"]])
        self.assertEqual(details["fotos"][0]["thumb_url"], cover["thumb_url"])
        legacy.assert_not_called()

    def test_detail_without_session_keeps_legacy_cover_fallback(self):
        with (
            patch.object(portal, "get_fotos_melhoradas_alojamento", return_value=[]),
            patch.object(portal, "get_fotos_alojamento", return_value=[{"url": "https://photos.test/legacy.jpg"}]),
        ):
            details = portal._decorate_alojamento({"ALSTAMP": "property-1"}, include_gallery=True)

        self.assertEqual(details["foto_principal"], "https://photos.test/legacy.jpg")
        self.assertEqual(details["fotos"][0]["url"], details["foto_principal"])
        self.assertTrue(details["fotos"][0]["capa"])

    def test_detail_without_any_photos_uses_empty_placeholder(self):
        with (
            patch.object(portal, "get_fotos_melhoradas_alojamento", return_value=[]),
            patch.object(portal, "get_fotos_alojamento", return_value=[]),
        ):
            details = portal._decorate_alojamento({"ALSTAMP": "property-1"}, include_gallery=True)

        self.assertEqual(details["foto_principal"], portal.PLACEHOLDER_IMAGE)
        self.assertEqual(details["fotos"], [])

    def test_catalog_uses_the_same_session_cover_selector(self):
        with patch.object(portal, "get_fotos_melhoradas_alojamento", return_value=[{"url": "https://photos.test/cover.jpg"}]):
            card = portal._decorate_alojamento({"ALSTAMP": "property-1"})

        self.assertEqual(card["foto_principal"], "https://photos.test/cover.jpg")
        self.assertEqual(card["fotos"], [])
        self.session.execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
