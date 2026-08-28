import unittest
from unittest.mock import MagicMock, patch

from services import document_ai_access_service as service


class DocumentAiAccessServiceTests(unittest.TestCase):
    def setUp(self):
        self.schema_patch = patch.object(service, 'ensure_document_ai_access_schema')
        self.schema_patch.start()

    def tearDown(self):
        self.schema_patch.stop()

    def test_unknown_view_fails_closed_without_querying_access(self):
        with patch.object(service.db, 'session') as session:
            profile = service.permission_profile('user', 'unknown')
        self.assertFalse(profile['allowed'])
        self.assertFalse(any(profile['permissions'].values()))
        session.execute.assert_not_called()

    def test_missing_assignment_fails_closed(self):
        result = MagicMock()
        result.mappings.return_value.first.return_value = None
        with patch.object(service.db.session, 'execute', return_value=result):
            profile = service.permission_profile('user', 'home')
        self.assertFalse(profile['allowed'])
        self.assertFalse(profile['permissions']['consult'])

    def test_restricted_profile_requires_an_assigned_entity(self):
        access = MagicMock()
        access.mappings.return_value.first.return_value = {
            'DOC_AI_ACCESS_STAMP': 'access-1',
            'ALL_ENTITIES': 0,
            'CAN_CONSULT': 1,
            'CAN_CREATE': 0,
            'CAN_ANALYZE': 1,
            'CAN_DELETE': 0,
            'CAN_AI': 0,
            'CAN_ASSOCIATE': 0,
            'CAN_VALIDATE': 0,
        }
        entities = MagicMock()
        entities.scalars.return_value.all.return_value = [8]
        with patch.object(service.db.session, 'execute', side_effect=[access, entities]):
            profile = service.permission_profile('user', 'management')
        self.assertTrue(profile['allowed'])
        self.assertEqual(profile['entity_ids'], [8])
        self.assertTrue(profile['permissions']['analyze'])
        self.assertFalse(profile['permissions']['create'])

    def test_all_entities_profile_does_not_query_document_scope(self):
        profile = {
            'allowed': True,
            'all_entities': True,
            'entity_ids': [],
            'permissions': {'analyze': True},
        }
        with patch.object(service, 'permission_profile', return_value=profile), patch.object(service.db, 'session') as session:
            allowed = service.can_access_document('user', 'home', 'analyze', 'doc-1')
        self.assertTrue(allowed)
        session.execute.assert_not_called()

    def test_configuration_rejects_removing_every_admin(self):
        with patch.object(service, 'is_access_admin', return_value=True):
            with self.assertRaisesRegex(ValueError, 'pelo menos um administrador'):
                service.save_access_configuration({'assignments': [], 'admin_logins': []}, 'admin')


if __name__ == '__main__':
    unittest.main()
