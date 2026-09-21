"""Versioned, translated public documents; company facts have one source."""

import json
from pathlib import Path


LEGAL_VERSION = "2026-09-21.1"
LEGAL_UPDATED = "2026-09-21"
LEGAL_CONTENT_DIR = Path(__file__).resolve().parent.parent / "content" / "booking_portal" / "legal"
LEGAL_ENDPOINTS = {
    "terms": "booking_portal.terms",
    "privacy": "booking_portal.privacy",
    "cookies": "booking_portal.cookies",
    "legal": "booking_portal.legal",
}
COMPANY_DEFAULTS = {
    "company_name": "GuestSpaTur Habitação e Turismo, Lda.",
    "tax_id": "518401057",
    "address": "Rua Régulo Magauanha, 102, 4000-413 Porto, Portugal",
    "contact_email": "helpdesk@guestspa.pt",
    "complaints_url": "https://www.livroreclamacoes.pt/",
}
LICENSE_LABELS = {"pt": "Registo AL", "en": "AL registration", "es": "Registro AL", "fr": "Enregistrement AL"}
COMPLAINTS_LABELS = {
    "pt": "Livro de Reclamações",
    "en": "Complaints Book",
    "es": "Libro de Reclamaciones",
    "fr": "Livre des Réclamations",
}


def get_legal_content(lang):
    language = lang if lang in {"pt", "en", "es", "fr"} else "pt"
    return json.loads((LEGAL_CONTENT_DIR / f"{language}.json").read_text(encoding="utf-8"))


def get_legal_company(config):
    configured = config.get("PORTOBREAK_LEGAL_COMPANY") or {}
    return {key: str(configured.get(key) or value) for key, value in COMPANY_DEFAULTS.items()}


def format_legal_content(value, replacements):
    """Interpolate plain text only; the presentation keeps Jinja autoescaping."""
    if isinstance(value, str):
        return value.format_map(replacements)
    if isinstance(value, list):
        return [format_legal_content(item, replacements) for item in value]
    if isinstance(value, dict):
        return {key: format_legal_content(item, replacements) for key, item in value.items()}
    return value
