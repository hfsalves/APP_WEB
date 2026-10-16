import unittest
from datetime import date

from services.transfer_email_service import build_transfer_confirmation_email


class TransferEmailServiceTests(unittest.TestCase):
    def test_builds_bilingual_commercial_email(self):
        result = build_transfer_confirmation_email({
            "reservation": "HMW4H2TD8D",
            "accommodation": "PARAÍSO H",
            "address": "Rua do Paraíso, 150, 4000-374 PORTO",
            "guest_name": "Kévin Decane",
            "people_count": 2,
            "guest_phone": "+351 900 000 000",
            "guest_email": "guest@example.com",
            "arrival_point_pt": "Aeroporto do Porto",
            "arrival_point_en": "Porto Airport",
            "arrival_date": date(2026, 10, 30),
            "arrival_time": "23:15",
            "flight": "FR6531",
            "transfer_id": "58A89738BAF14E2AB533A70CE",
            "driver_phone": "+351 929 009 157",
        })

        self.assertEqual(
            result["subject"],
            "Transfer confirmado / Transfer confirmed — HMW4H2TD8D",
        )
        self.assertIn("PEDIDO DE TRANSFER CONFIRMADO", result["body_text"])
        self.assertIn("TRANSFER REQUEST CONFIRMED", result["body_text"])
        self.assertIn("Kévin Decane", result["body_text"])
        self.assertIn("30/10/2026 às 23:15", result["body_text"])
        self.assertIn("EUR 30 per trip", result["body_text"])
        self.assertIn("Pedido de transfer confirmado", result["body_html"])
        self.assertIn("Transfer request confirmed", result["body_html"])


if __name__ == "__main__":
    unittest.main()
