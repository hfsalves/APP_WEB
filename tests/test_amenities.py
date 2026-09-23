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
    assert len(INITIAL_AMENITIES) == 44
    codes = [item[0] for item in INITIAL_AMENITIES]
    assert len(codes) == len(set(codes))
    assert {"AR_CONDICIONADO", "WIFI", "ELEVADOR", "BERCO", "COFRE", "GEL_DUCHE", "SHAMPOO", "SABONETE_LIQUIDO"}.issubset(codes)
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


def test_public_catalog_does_not_load_amenities_and_detail_does():
    catalog = (ROOT / "templates/booking_portal/index.html").read_text(encoding="utf-8").lower()
    detail = (ROOT / "templates/booking_portal/detail.html").read_text(encoding="utf-8").lower()
    assert "comodidade" not in catalog
    assert "alojamento.comodidades" in detail


def test_backoffice_matrix_is_dynamic_and_uses_immediate_api_saves():
    template = (ROOT / "templates/amenities.html").read_text(encoding="utf-8")
    script = (ROOT / "static/js/amenities.js").read_text(encoding="utf-8")
    styles = (ROOT / "static/css/amenities.css").read_text(encoding="utf-8")
    assert 'id="amenitiesMatrix"' in template
    assert 'id="amenitiesDialog"' in template
    assert 'class="modal fade amenities-modal"' in template
    assert "modal-dialog-centered" in template
    assert "bootstrap?.Modal" in script
    assert "var(--sz-color-surface)" in styles
    assert "var(--sz-color-text)" in styles
    assert "overflow-x: scroll" in styles
    assert "data-bulk" in script
    assert "root.dataset.relationUrl" in script
    assert "alojamento:input.dataset.property" in script
    assert "window.confirm" in script
    assert 'data-delete=' in script
    assert "method:'DELETE'" in script
    assert 'data-column-index=' in script
    assert "is-hover-column" in script
    assert "is-hover-row" in script
    assert "amenities-value-cell" in script
    assert "input.click()" in script
    assert "scrollWidth > label.clientWidth" in script
    assert "data-full-label" in script
    assert "label.removeAttribute('title')" in script


def test_deleted_initial_amenities_are_not_reseeded_on_restart():
    service = (ROOT / "services/amenities_service.py").read_text(encoding="utf-8")
    assert "SELECT TOP 1 1 FROM dbo.COMODIDADES" in service
    assert "IF NOT EXISTS (SELECT 1 FROM dbo.COMODIDADES WHERE CODIGO" not in service


def test_delete_removes_relations_before_catalogue_record():
    service = (ROOT / "services/amenities_service.py").read_text(encoding="utf-8")
    relation_delete = service.index("DELETE FROM dbo.AL_COMODIDADES WHERE COMODIDADE_ID=:id")
    catalogue_delete = service.index("DELETE FROM dbo.COMODIDADES WHERE ID=:id")
    assert relation_delete < catalogue_delete
