from __future__ import annotations

import re
import hashlib
from collections.abc import Mapping


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

PRIMARY_GUEST_REQUIRED_FIELDS = (
    "nome",
    "apelido",
    "dtnasc",
    "nacionalidade",
    "pais_residencia",
    "tipo_doc",
    "num_doc",
    "pais_emissor_doc",
)


def clean_guest_email(value: object, max_length: int = 255) -> str:
    return str(value or "").strip()[:max_length]


def clean_guest_phone(value: object, max_length: int = 50) -> str:
    return str(value or "").strip()[:max_length]


def valid_guest_email(value: object) -> bool:
    return bool(EMAIL_RE.fullmatch(clean_guest_email(value)))


def primary_guest_complete(guest: Mapping[str, object] | None) -> bool:
    source = guest or {}
    for field in PRIMARY_GUEST_REQUIRED_FIELDS:
        raw = str(source.get(field) or "").strip()
        if field == "dtnasc" and raw in {"1900-01-01", "0001-01-01"}:
            return False
        if not raw:
            return False
    return True


def clean_transfer_request_key(value: object, max_length: int = 64) -> str:
    """Return a browser-generated idempotency key safe for SQL storage."""
    cleaned = str(value or "").strip()[:max_length]
    return cleaned if re.fullmatch(r"[A-Za-z0-9_-]{8,64}", cleaned) else ""


def transfer_request_hash(
    *,
    rsstamp: object,
    route: object,
    service_date: object,
    service_time: object,
    flight: object = "",
) -> str:
    """Stable identity for one transfer movement, independent of UI retries."""
    canonical = "|".join((
        str(rsstamp or "").strip().upper(),
        str(route or "").strip().lower(),
        str(service_date or "").strip()[:10],
        str(service_time or "").strip()[:5],
        str(flight or "").strip().upper(),
    ))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest().upper()
