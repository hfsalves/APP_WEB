from services.guest_transfer_service import (
    clean_guest_email,
    clean_guest_phone,
    clean_transfer_request_key,
    primary_guest_complete,
    transfer_request_hash,
    valid_guest_email,
)


def complete_guest():
    return {
        "nome": "Ana",
        "apelido": "Silva",
        "dtnasc": "1990-05-12",
        "nacionalidade": "Portugal",
        "pais_residencia": "Portugal",
        "tipo_doc": "PASSAPORTE",
        "num_doc": "AA123456",
        "pais_emissor_doc": "Portugal",
    }


def test_primary_guest_completion_does_not_require_optional_contacts():
    assert primary_guest_complete(complete_guest()) is True


def test_primary_guest_completion_rejects_missing_identity_data():
    guest = complete_guest()
    guest["num_doc"] = ""
    assert primary_guest_complete(guest) is False


def test_transfer_contact_normalization_and_email_validation():
    assert clean_guest_email("  guest@example.com  ") == "guest@example.com"
    assert clean_guest_phone("  +351 912 345 678  ") == "+351 912 345 678"
    assert valid_guest_email("guest@example.com") is True
    assert valid_guest_email("guest@example") is False


def test_transfer_request_identity_is_stable_and_route_sensitive():
    first = transfer_request_hash(
        rsstamp=" RS-1 ", route="AIRPORT", service_date="2026-11-01",
        service_time="20:15", flight=" fr2029 ",
    )
    retry = transfer_request_hash(
        rsstamp="rs-1", route="airport", service_date="2026-11-01",
        service_time="20:15", flight="FR2029",
    )
    departure = transfer_request_hash(
        rsstamp="rs-1", route="to_airport", service_date="2026-11-01",
        service_time="20:15", flight="FR2029",
    )
    assert first == retry
    assert first != departure
    assert len(first) == 64


def test_transfer_request_key_only_accepts_safe_values():
    assert clean_transfer_request_key("abcDEF_123-456") == "abcDEF_123-456"
    assert clean_transfer_request_key("short") == ""
    assert clean_transfer_request_key("not safe !") == ""
