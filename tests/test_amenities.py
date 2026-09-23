from pathlib import Path

import pytest

from services.amenities_service import (
    CATEGORIES,
    ICON_OPTIONS,
    INITIAL_AMENITIES,
    normalize_amenity_payload,
)


ROOT = Path(__file__).resolve().parents[1]


def _payload(**overrides):
    data = {
        "codigo": "TESTE_FISICO",
        "nome_pt": "Teste",
        "nome_en": "Test",
        "nome_es": "Prueba",
        "nome_fr": "Test",
        "categoria": "OUTROS",
        "icone": "fa-house",
        "ordem": 10,
        "ativa": True,
        "mostra_portobreak": True,
        "filtro_portobreak": False,
    }
    data.update(overrides)
    return data


def test_initial_catalog_has_exact_requested_physical_amenities_and_translations():
    assert len(INITIAL_AMENITIES) == 41
    codes = [item[0] for item in INITIAL_AMENITIES]
    assert len(codes) == len(set(codes))
    assert {"AR_CONDICIONADO", "WIFI", "ELEVADOR", "BERCO", "COFRE"}.issubset(codes)
    assert not {"ANIMAIS", "FUMADORES", "VISTA_RIO", "VISTA_MAR", "LAREIRA"}.intersection(codes)
    for code, pt, en, es, fr, category, icon, order, show, filtering in INITIAL_AMENITIES:
        assert code and pt and en and es and fr
        assert category in CATEGORIES
        assert icon in ICON_OPTIONS
        assert isinstance(order, int)
        assert filtering in (0, 1) and show in (0, 1)
        assert not filtering or show


def test_payload_normalizes_code_and_filter_dependency():
    clean = normalize_amenity_payload(_payload(
        codigo=" ar condicionado especial ",
        ativa=False,
        mostra_portobreak=False,
        filtro_portobreak=True,
    ), creating=True)
    assert clean["codigo"] == "AR_CONDICIONADO_ESPECIAL"
    assert clean["ativa"] is True
    assert clean["mostra_portobreak"] is True
    assert clean["filtro_portobreak"] is True


@pytest.mark.parametrize("field,value", [
    ("nome_pt", ""), ("nome_en", ""), ("nome_es", ""), ("nome_fr", ""),
    ("categoria", "INVENTADA"), ("icone", "<script>"), ("ordem", "x"),
    ("ativa", "false"), ("mostra_portobreak", None), ("filtro_portobreak", "yes"),
])
def test_payload_rejects_invalid_catalog_values(field, value):
    with pytest.raises(ValueError):
        normalize_amenity_payload(_payload(**{field: value}), creating=True)


def test_migration_uses_al_name_and_enforces_catalog_and_relation_constraints():
    sql = (ROOT / "migrations/al_comodidades.sql").read_text(encoding="utf-8").upper()
    assert "ALOJAMENTO VARCHAR(60)" in sql
    assert "PRIMARY KEY CLUSTERED (ALOJAMENTO, COMODIDADE_ID)" in sql
    assert "UNIQUE (CODIGO)" in sql
    assert "FK_AL_COMODIDADES_COMODIDADES" in sql
    assert "FILTRO_PORTOBREAK = 0 OR (ATIVA = 1 AND MOSTRA_PORTOBREAK = 1)" in sql


def test_public_portobreak_templates_do_not_reference_amenities_module():
    for relative in ("templates/booking_portal/index.html", "templates/booking_portal/detail.html"):
        assert "comodidade" not in (ROOT / relative).read_text(encoding="utf-8").lower()


def test_backoffice_matrix_is_dynamic_and_uses_immediate_api_saves():
    template = (ROOT / "templates/amenities.html").read_text(encoding="utf-8")
    script = (ROOT / "static/js/amenities.js").read_text(encoding="utf-8")
    assert 'id="amenitiesMatrix"' in template
    assert 'id="amenitiesDialog"' in template
    assert "data-bulk" in script
    assert "root.dataset.relationUrl" in script
    assert "alojamento:input.dataset.property" in script
    assert "window.confirm" in script
