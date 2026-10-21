from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from services.guest_transfer_service import valid_guest_email


VALID_TRANSFER_ROUTES = frozenset({"airport", "campanha", "to_airport", "to_campanha"})
AIRPORT_ROUTES = frozenset({"airport", "to_airport"})
DEPARTURE_ROUTES = frozenset({"to_airport", "to_campanha"})
TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


class TransferManagementError(ValueError):
    pass


def _clean(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _date(value: Any, label: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value or "").strip()[:10])
    except ValueError as exc:
        raise TransferManagementError(f"Indique uma {label} válida.") from exc


def _time(value: Any, label: str) -> str:
    result = _clean(value, 5)
    if not TIME_RE.fullmatch(result):
        raise TransferManagementError(f"Indique uma {label} válida.")
    return result


def _boolean(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _positive_int(value: Any, label: str) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise TransferManagementError(f"Indique um valor válido para {label}.") from exc
    if result <= 0:
        raise TransferManagementError(f"{label.capitalize()} tem de ser superior a zero.")
    return result


def _money(value: Any) -> Decimal:
    raw = str(value or "0").strip().replace(" ", "").replace(",", ".")
    try:
        result = Decimal(raw).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as exc:
        raise TransferManagementError("Indique um valor válido para o transfer.") from exc
    if result < 0:
        raise TransferManagementError("O valor do transfer não pode ser negativo.")
    return result


def normalize_transfer_edit(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    source = payload or {}
    route = _clean(source.get("origin") or source.get("route"), 20).lower()
    if route not in VALID_TRANSFER_ROUTES:
        raise TransferManagementError("Selecione um percurso válido.")

    service_date = _date(source.get("service_date") or source.get("arrival_date"), "data do transfer")
    service_time = _time(source.get("service_time") or source.get("arrival_time"), "hora do transfer")
    departure_route = route in DEPARTURE_ROUTES
    has_return = _boolean(source.get("has_departure")) and not departure_route
    departure_date = None
    departure_time = ""
    if departure_route:
        departure_date, departure_time = service_date, service_time
    elif has_return:
        departure_date = _date(source.get("departure_date"), "data de regresso")
        departure_time = _time(source.get("departure_time"), "hora de regresso")

    guest_name = _clean(source.get("guest_name"), 200)
    if not guest_name:
        raise TransferManagementError("Indique o nome do hóspede.")
    people = _positive_int(source.get("people"), "número de pessoas")
    guest_email = _clean(source.get("guest_email"), 255)
    if guest_email and not valid_guest_email(guest_email):
        raise TransferManagementError("Indique um email válido para o hóspede.")
    driver_email = _clean(source.get("driver_email"), 255)
    if driver_email and not valid_guest_email(driver_email):
        raise TransferManagementError("Indique um email válido para o motorista.")

    return {
        "origin": route,
        "service_date": service_date,
        "service_time": service_time,
        "flight": _clean(source.get("flight"), 20) if route in AIRPORT_ROUTES else "",
        "has_departure": departure_route or has_return,
        "departure_date": departure_date,
        "departure_time": departure_time or None,
        "address": _clean(source.get("address"), 300),
        "guest_name": guest_name,
        "people": people,
        "guest_phone": _clean(source.get("guest_phone"), 50),
        "guest_email": guest_email,
        "driver_phone": _clean(source.get("driver_phone"), 50),
        "driver_email": driver_email,
        "value": _money(source.get("value")),
    }
