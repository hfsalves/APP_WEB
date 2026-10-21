from datetime import date
from decimal import Decimal

import pytest

from services.transfer_management_service import TransferManagementError, normalize_transfer_edit


def _payload(**changes):
    payload = {
        "origin": "airport",
        "service_date": "2026-11-01",
        "service_time": "20:15",
        "flight": "FR2029",
        "guest_name": "Susana Avilés",
        "people": 3,
        "guest_phone": "+351 910 000 000",
        "guest_email": "susana@example.com",
        "driver_phone": "+351 929 009 157",
        "driver_email": "driver@example.com",
        "address": "Porto",
        "value": "30,00",
    }
    payload.update(changes)
    return payload


def test_normalize_arrival_transfer():
    result = normalize_transfer_edit(_payload())
    assert result["service_date"] == date(2026, 11, 1)
    assert result["service_time"] == "20:15"
    assert result["flight"] == "FR2029"
    assert result["has_departure"] is False
    assert result["value"] == Decimal("30.00")


def test_departure_route_uses_service_date_as_departure():
    result = normalize_transfer_edit(_payload(origin="to_campanha", flight="IGNORED"))
    assert result["flight"] == ""
    assert result["has_departure"] is True
    assert result["departure_date"] == date(2026, 11, 1)
    assert result["departure_time"] == "20:15"


def test_optional_return_requires_its_date_and_time():
    with pytest.raises(TransferManagementError):
        normalize_transfer_edit(_payload(has_departure=True))


def test_invalid_contacts_and_people_are_rejected():
    with pytest.raises(TransferManagementError):
        normalize_transfer_edit(_payload(guest_email="invalid"))
    with pytest.raises(TransferManagementError):
        normalize_transfer_edit(_payload(people=0))
