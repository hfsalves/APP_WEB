from datetime import date, datetime
from decimal import Decimal
from io import BytesIO

from openpyxl import load_workbook

from services.employee_insurance_service import (
    build_employee_insurance_workbook,
    calculate_meal_allowance,
    classify_changes,
    filter_and_sort,
)


def employee(stamp, name, profession="9112.0", description="Trabalhador de limpeza"):
    return {
        "pestamp": stamp, "numero": 1, "nome": name, "nacionalidade": "PORTUGUESA",
        "nif": "123456789", "niss": "12345678901", "nascimento": date(1990, 1, 2),
        "admissao": date(2026, 1, 1), "salario_base": Decimal("920.00"),
        "subsidio_refeicao": Decimal("132.00"), "profissao_codigo": profession,
        "profissao_descricao": description, "profissao": f"{profession} — {description}",
        "incompleto": False,
    }


def test_meal_allowance_uses_22_days():
    assert calculate_meal_allowance("6") == Decimal("132.00")


def test_first_issue_does_not_mark_every_employee_as_new():
    current, departures = classify_changes([employee("A", "Ana")], [])
    assert current[0]["novo"] is False
    assert departures == []


def test_entries_and_departures_are_compared_by_pestamp():
    current, departures = classify_changes(
        [employee("A", "Ana"), employee("B", "Bruna")],
        [employee("A", "Ana"), employee("C", "Carla")],
    )
    assert [row["nome"] for row in current if row["novo"]] == ["Bruna"]
    assert [row["nome"] for row in departures] == ["Carla"]


def test_search_filter_and_sort_cover_profession_and_nif():
    rows = [employee("B", "Bruna"), employee("A", "Ana", "8157.0", "Operador de máquinas de lavandaria")]
    result = filter_and_sort(rows, {"q": "lavandaria", "ordenar": "nome", "direcao": "desc"})
    assert [row["nome"] for row in result] == ["Ana"]
    assert filter_and_sort(rows, {"q": "123456789"}) == sorted(rows, key=lambda row: row["nome"])


def test_workbook_has_typed_values_and_separate_departures():
    ana = employee("A", "ANA PAULA MAGALHÃES SOARES", "8157.0", "Operador de máquinas de lavandaria")
    ana["novo"] = True
    departed = employee("C", "Carla")
    report = {"gerado_em": datetime(2026, 10, 20, 12, 0), "ambito": "todos"}
    workbook = load_workbook(BytesIO(build_employee_insurance_workbook(report, [ana], [departed])))
    sheet = workbook["Mapa seguradora"]
    assert sheet["B2"].value == "GuestSpaTur"
    assert sheet["G8"].value == 132
    assert "Operador de máquinas de lavandaria" in sheet["H8"].value
    assert sheet["A10"].value == "SAÍDAS DESDE A ÚLTIMA EMISSÃO"
