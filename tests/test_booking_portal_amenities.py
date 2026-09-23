from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services import booking_portal_service as portal


ROOT = Path(__file__).resolve().parents[1]


def test_public_amenities_use_selected_language_and_public_flags():
    session = MagicMock()
    session.execute.return_value.mappings.return_value.all.return_value = [
        {"CODIGO": "WIFI", "NOME": "Wi-Fi", "CATEGORIA": "TECNOLOGIA", "ICONE": "fa-wifi", "ORDEM": 10},
    ]
    with (
        patch.object(portal, "db", SimpleNamespace(session=session)),
        patch.object(portal, "_table_exists", return_value=True),
    ):
        result = portal.get_public_amenities("Alegria Studio", lang="fr")

    assert result == [{"codigo": "WIFI", "nome": "Wi-Fi", "categoria": "TECNOLOGIA", "icone": "fa-wifi"}]
    sql = " ".join(str(session.execute.call_args.args[0]).split()).upper()
    assert "C.NOME_FR" in sql
    assert "C.ATIVA=1" in sql
    assert "C.MOSTRA_PORTOBREAK=1" in sql
    assert session.execute.call_args.args[1] == {"alojamento": "Alegria Studio"}


def test_public_amenities_are_omitted_when_tables_or_property_are_missing():
    with patch.object(portal, "_table_exists", return_value=False):
        assert portal.get_public_amenities("Alegria Studio", lang="pt") == []
    assert portal.get_public_amenities("", lang="pt") == []


def test_detail_template_renders_only_real_assigned_amenities():
    template = (ROOT / "templates/booking_portal/detail.html").read_text(encoding="utf-8")
    assert "{% if alojamento.comodidades %}" in template
    assert "{% for comodidade in alojamento.comodidades %}" in template
    assert "booking-amenities-grid" in template
    assert "font-awesome/6.4.0/css/all.min.css" in template
    assert "comodidade.icone" in template
    assert "comodidade.nome" in template
