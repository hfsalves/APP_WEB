import unittest

from services import gr360_ticket_api_service as service


class Gr360TicketApiServiceTests(unittest.TestCase):
    def test_extracts_only_bearer_token(self):
        self.assertEqual(service.extract_bearer_token("Bearer abc-123"), "abc-123")
        self.assertEqual(service.extract_bearer_token("Basic abc-123"), "")
        self.assertEqual(service.extract_bearer_token(None), "")

    def test_token_hash_is_stable_and_does_not_return_plaintext(self):
        first = service.token_hash("secret-token")
        self.assertEqual(first, service.token_hash("secret-token"))
        self.assertEqual(len(first), 64)
        self.assertNotIn("secret-token", first)

    def test_validates_and_normalizes_ticket_payload(self):
        result = service.validate_create_payload({
            "pedido": "  Controlo   de gestão ",
            "prompt_hugo": "Analisar este comportamento.",
            "prioridade": "alta",
            "feid": "8",
            "utilizador": "Mickael",
            "referencia_externa": "cloud-gpt-123",
        })
        self.assertEqual(result["pedido"], "Controlo de gestão")
        self.assertEqual(result["prioridade"], "Alta")
        self.assertEqual(result["feid"], 8)
        self.assertEqual(result["referencia_externa"], "cloud-gpt-123")

    def test_requires_title_and_full_prompt(self):
        with self.assertRaises(service.TicketApiError):
            service.validate_create_payload({"prompt_hugo": "x"})
        with self.assertRaises(service.TicketApiError):
            service.validate_create_payload({"pedido": "x"})

    def test_rejects_invalid_priority_and_feid(self):
        with self.assertRaises(service.TicketApiError):
            service.validate_create_payload({"pedido": "x", "prompt_hugo": "y", "prioridade": "máxima"})
        with self.assertRaises(service.TicketApiError):
            service.validate_create_payload({"pedido": "x", "prompt_hugo": "y", "feid": "abc"})

    def test_serialization_omits_prompt_from_list_when_requested(self):
        row = {"TICKET": 27, "PEDIDO": "Teste", "TRATADO": 0, "PROMPT_HUGO": "conteúdo"}
        result = service.serialize_ticket(row, include_prompt=False)
        self.assertEqual(result["ticket"], 27)
        self.assertNotIn("prompt_hugo", result)

    def test_database_validation_fails_closed(self):
        class Result:
            @staticmethod
            def scalar():
                return "GESTAO"

        class Connection:
            @staticmethod
            def execute(_statement):
                return Result()

        with self.assertRaises(service.TicketApiConfigurationError):
            service.ensure_gr360_database(Connection(), "GR360_CORE")


if __name__ == "__main__":
    unittest.main()
