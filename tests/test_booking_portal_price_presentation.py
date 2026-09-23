"""Commercial price hierarchy on the stay detail and booking summary."""

from decimal import Decimal
from pathlib import Path
import unittest
from unittest.mock import patch

from flask import Flask

from blueprints.booking_portal import bp


ROOT = Path(__file__).resolve().parents[1]
PROPERTY = {
    "id": "stay-one",
    "nome": "Estúdio do Porto",
    "nome_interno": "ESTUDIO PORTO",
    "descricao": "Um estúdio confortável.",
    "descricao_curta": "Um estúdio confortável.",
    "localizacao": "Porto",
    "capacidade": 2,
    "lot_adultos": 2,
    "lot_criancas": 0,
    "berco": False,
    "noites_minimas": 1,
    "valor_extra": Decimal("0.00"),
    "extra_mais_que": 0,
    "tipologia": "T0",
    "foto_principal": "/static/stay.jpg",
    "fotos": [{"url": "/static/stay.jpg", "alt": "Estúdio"}],
    "tem_mapa": False,
    "preco_desde": "44.00 EUR",
    "airbnb_room_id": "21329922",
}
QUOTE = {
    "valor": Decimal("128.00"),
    "label": "128.00 EUR",
    "noites": 2,
    "hospedes": 1,
    "preco_noites": Decimal("92.00"),
    "preco_noites_label": "92.00 EUR",
    "preco_noites_airbnb": Decimal("96.00"),
    "preco_noites_airbnb_label": "96.00 EUR",
    "preco_total_airbnb": Decimal("132.00"),
    "preco_total_airbnb_label": "132.00 EUR",
    "preco_total_portobreak": Decimal("128.00"),
    "preco_total_portobreak_label": "128.00 EUR",
    "poupanca_noites": Decimal("4.00"),
    "poupanca_noites_label": "4.00 EUR",
    "hospedes_extra": 0,
    "limpeza": Decimal("30.00"),
    "limpeza_label": "30.00 EUR",
    "taxa_turistica": Decimal("6.00"),
    "taxa_turistica_label": "6.00 EUR",
    "taxa_turistica_dias": 2,
    "linhas": [
        {"label": "Noites (2)", "value": "92.00 EUR"},
        {"label": "Taxa de limpeza", "value": "30.00 EUR"},
        {"label": "Taxa turistica (1 hospede x 2 dias)", "value": "6.00 EUR"},
    ],
}


class BookingPortalPricePresentationTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(
            __name__, template_folder=str(ROOT / "templates"), static_folder=str(ROOT / "static")
        )
        self.app.config.update(TESTING=True, SECRET_KEY="price-presentation-tests")
        self.app.register_blueprint(bp)
        self.client = self.app.test_client()
        fixtures = {
            "_portal_current_user": {"return_value": None},
            "get_alojamento": {"return_value": PROPERTY},
            "get_calendario_ocupacao": {"return_value": {
                "occupied": [], "blocked_checkin": [], "blocked_checkout": [], "min_nights": 1,
            }},
            "alojamento_disponivel": {"return_value": True},
            "alojamento_datas_permitidas": {"return_value": {"allowed": True, "errors": []}},
            "calcular_preco": {"return_value": QUOTE},
        }
        for name, options in fixtures.items():
            patcher = patch("blueprints.booking_portal." + name, **options)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_detail_and_booking_summary_show_the_same_comparison_and_total(self):
        query = "?lang=pt&checkin=2030-10-14&checkout=2030-10-16&adultos=1"
        for path in ("/reservas/stay-one", "/reservas/stay-one/reservar"):
            with self.subTest(path=path):
                response = self.client.get(path + query)
                self.assertEqual(response.status_code, 200)
                markup = response.get_data(as_text=True)
                self.assertIn("Preço Airbnb", markup)
                self.assertIn('class="booking-airbnb-badge"', markup)
                self.assertIn('href="https://www.airbnb.pt/rooms/21329922?adults=1&amp;check_in=2030-10-14&amp;check_out=2030-10-16"', markup)
                self.assertIn('<span class="booking-airbnb-price">132.00 EUR</span>', markup)
                self.assertNotIn("<del>132.00 EUR</del>", markup)
                self.assertIn("Reserva direta", markup)
                self.assertIn("<strong>128.00 EUR</strong>", markup)
                self.assertIn("Poupa 4.00 EUR", markup)
                self.assertIn("Noites (2)", markup)
                self.assertIn("Taxa de limpeza", markup)
                self.assertIn("30.00 EUR", markup)
                self.assertIn("Taxa turistica", markup)
                self.assertIn("6.00 EUR", markup)
                self.assertIn('class="booking-price-total"', markup)
                self.assertIn("128.00 EUR", markup)

    def test_saving_explanation_is_available_in_every_supported_language(self):
        expected = {
            "pt": ("Porque poupa na reserva direta", "Somos proprietários ou coanfitriões"),
            "en": ("Why you save by booking direct", "We are the owners or co-hosts"),
            "es": ("Por qué ahorras al reservar directamente", "Somos propietarios o coanfitriones"),
            "fr": ("Pourquoi vous économisez en réservant directement", "Nous sommes propriétaires ou co-hôtes"),
        }
        for lang, copy in expected.items():
            with self.subTest(lang=lang):
                response = self.client.get(
                    "/reservas/stay-one",
                    query_string={
                        "lang": lang, "checkin": "2030-10-14",
                        "checkout": "2030-10-16", "adultos": 1,
                    },
                )
                markup = response.get_data(as_text=True)
                self.assertIn('data-price-info-open', markup)
                self.assertIn('id="bookingPriceInfoDialog"', markup)
                self.assertIn('aria-controls="bookingPriceInfoDialog"', markup)
                self.assertIn(copy[0], markup)
                self.assertIn(copy[1], markup)


if __name__ == "__main__":
    unittest.main()
