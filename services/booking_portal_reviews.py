from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


_RATING_STEP = Decimal("0.01")
_DECIMAL_COMMA_LANGS = {"pt", "es", "fr"}


def _text(value) -> str:
    return str(value or "").strip()


def _rating_value(value) -> Decimal | None:
    try:
        rating = Decimal(str(value).strip())
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not rating.is_finite() or rating <= 0 or rating > 5:
        return None
    return rating.quantize(_RATING_STEP, rounding=ROUND_HALF_UP)


def format_rating(value, lang: str = "pt") -> str:
    """Format a valid 0–5 rating with at most two decimal places."""
    rating = _rating_value(value)
    if rating is None:
        return ""
    label = f"{rating:.2f}".rstrip("0").rstrip(".")
    return label.replace(".", ",") if lang in _DECIMAL_COMMA_LANGS else label


def build_rating_summary(value, count, lang: str = "pt") -> dict | None:
    label = format_rating(value, lang)
    if not label:
        return None
    try:
        review_count = max(0, int(count or 0))
    except (TypeError, ValueError):
        review_count = 0
    return {"label": label, "count": review_count}


def parse_reviews(raw_value, lang: str = "pt") -> list[dict]:
    """Parse the versioned AL.AVALIACOES payload without changing review text.

    Unknown or malformed payloads are deliberately ignored. Platform-tenure
    profile labels are not public accommodation metadata, so they are omitted;
    geographic profile labels remain available exactly as stored.
    """
    if not isinstance(raw_value, str) or not raw_value.strip():
        return []
    try:
        payload = json.loads(raw_value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(payload, dict) or not isinstance(payload.get("reviews"), list):
        return []

    parsed = []
    for entry in payload["reviews"]:
        if not isinstance(entry, dict):
            continue
        author = _text(entry.get("author"))
        profile = _text(entry.get("profile"))
        rating_label = format_rating(entry.get("rating"), lang)
        date_label = _text(entry.get("date_label"))
        stay_label = _text(entry.get("stay_label"))
        raw_text = entry.get("text")
        review_text = raw_text if isinstance(raw_text, str) else _text(raw_text)
        if not any((author, profile, rating_label, date_label, stay_label, review_text.strip())):
            continue
        parsed.append({
            "author": author,
            "author_initial": author[:1].upper(),
            "profile": "" if "airbnb" in profile.casefold() else profile,
            "rating_label": rating_label,
            "date_label": date_label,
            "stay_label": stay_label,
            "text": review_text,
            "expandable": len(review_text) > 420,
        })
    return parsed
