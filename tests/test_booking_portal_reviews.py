import json
from pathlib import Path

from services.booking_portal_reviews import (
    build_rating_summary,
    format_rating,
    parse_reviews,
)
from services.booking_portal_service import _alojamento_base_select, _alojamento_paged_select


ROOT = Path(__file__).resolve().parents[1]


def test_rating_uses_the_local_decimal_separator_and_two_decimals_at_most():
    assert format_rating("4.88", "pt") == "4,88"
    assert format_rating("4.88", "en") == "4.88"
    assert format_rating("5.00", "fr") == "5"
    assert build_rating_summary("4.63", 350, "es") == {"label": "4,63", "count": 350}


def test_invalid_or_zero_rating_is_omitted_while_a_valid_rating_can_have_no_count():
    assert build_rating_summary(0, 120, "pt") is None
    assert build_rating_summary(6, 120, "pt") is None
    assert build_rating_summary("invalid", 120, "pt") is None
    assert build_rating_summary("4.7", None, "en") == {"label": "4.7", "count": 0}


def test_reviews_follow_the_real_versioned_payload_and_keep_original_text():
    original = "Primeira linha.\nSegunda linha exatamente como foi escrita."
    payload = json.dumps({
        "schema_version": 1,
        "source": "external-source",
        "reviews": [{
            "author": "Joana",
            "profile": "Lisboa, Portugal",
            "rating": 4.94,
            "date_label": "março de 2026",
            "stay_label": "Estadia de algumas noites",
            "text": original,
        }],
    })
    reviews = parse_reviews(payload, "pt")
    assert reviews == [{
        "author": "Joana",
        "author_initial": "J",
        "profile": "Lisboa, Portugal",
        "rating_label": "4,94",
        "date_label": "março de 2026",
        "stay_label": "Estadia de algumas noites",
        "text": original,
        "expandable": False,
    }]


def test_parser_handles_any_valid_count_and_malformed_content_without_failure():
    for count in (1, 5, 6, 8):
        payload = json.dumps({"reviews": [{"author": str(i), "text": "Real"} for i in range(count)]})
        assert len(parse_reviews(payload, "en")) == count
    for malformed in (None, "", "not json", "[]", '{"reviews": {}}'):
        assert parse_reviews(malformed, "pt") == []


def test_platform_tenure_profile_is_not_presented_as_property_review_metadata():
    payload = json.dumps({"reviews": [{
        "author": "Ana", "profile": "Está na Airbnb há 2 anos", "text": "Ótimo."
    }]})
    assert parse_reviews(payload, "pt")[0]["profile"] == ""


def test_catalog_query_does_not_select_the_reviews_payload_but_detail_query_does():
    catalog_sql = _alojamento_paged_select("1 = 1", lang="pt").upper()
    detail_sql = _alojamento_base_select("1 = 1", lang="pt", include_reviews=True).upper()
    assert "AL.AVALIACAO" in catalog_sql
    assert "AL.NRAVALIACOES" in catalog_sql
    assert "AL.AVALIACOES" not in catalog_sql
    assert "AL.AVALIACOES" in detail_sql


def test_templates_share_the_rating_component_and_detail_reviews_component():
    index = (ROOT / "templates/booking_portal/index.html").read_text()
    detail = (ROOT / "templates/booking_portal/detail.html").read_text()
    component = (ROOT / "templates/booking_portal/_reviews.html").read_text()
    assert 'from "booking_portal/_reviews.html" import rating_summary' in index
    assert 'from "booking_portal/_reviews.html" import rating_summary, reviews_section' in detail
    assert "alojamento.reviews" in component
    assert 'id="avaliacoes"' in component
