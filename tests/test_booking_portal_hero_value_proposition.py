from pathlib import Path

from blueprints.booking_portal import SUPPORTED_LANGS, TRANSLATIONS


ROOT = Path(__file__).resolve().parents[1]


def test_hero_value_proposition_exists_in_every_supported_language():
    required = {
        "local_stay",
        "hero_title",
        "hero_lead",
        "hero_trust_label",
        "hero_direct_rates",
        "hero_secure_payment",
        "hero_local_support",
    }
    assert set(SUPPORTED_LANGS) == {"pt", "en", "es", "fr"}
    for lang in SUPPORTED_LANGS:
        assert required.issubset(TRANSLATIONS[lang])
        assert all(str(TRANSLATIONS[lang][key]).strip() for key in required)


def test_hero_uses_direct_rate_claim_without_absolute_price_promises():
    forbidden = ("best price", "cheapest", "lowest price", "melhor preço garantido", "preço mais baixo")
    for lang in SUPPORTED_LANGS:
        copy = " ".join(str(TRANSLATIONS[lang][key]) for key in (
            "hero_title", "hero_lead", "hero_direct_rates", "hero_secure_payment", "hero_local_support",
        )).casefold()
        assert not any(claim in copy for claim in forbidden)

    assert TRANSLATIONS["en"]["hero_title"] == "Stay in Porto. Book direct."
    assert TRANSLATIONS["en"]["hero_direct_rates"] == "Direct rates"
    assert TRANSLATIONS["pt"]["hero_title"] == "Fica no Porto. Reserva diretamente."
    assert TRANSLATIONS["pt"]["hero_direct_rates"] == "Tarifas diretas"


def test_hero_trust_points_reuse_i18n_and_have_responsive_styles():
    template = (ROOT / "templates" / "booking_portal" / "index.html").read_text()
    stylesheet = (ROOT / "static" / "css" / "booking_portal.css").read_text()

    assert 'class="booking-hero-trust"' in template
    assert "{{ t.hero_direct_rates }}" in template
    assert "{{ t.hero_secure_payment }}" in template
    assert "{{ t.hero_local_support }}" in template
    assert ".booking-hero-trust" in stylesheet
    assert "@media (max-width: 720px)" in stylesheet
