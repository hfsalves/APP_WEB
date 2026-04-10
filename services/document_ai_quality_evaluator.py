import re
from typing import Any


DOCUMENT_QUALITY_KEYWORDS = [
    'invoice',
    'total',
    'date',
    'vat',
    'facture',
    'rechnung',
    'credit note',
    'order',
    'fatura',
    'factura',
    'nota de credito',
    'nota de crédito',
    'guia',
    'subtotal',
    'iva',
]


def _normalize_text(value: Any) -> str:
    return str(value or '').strip().lower()


def evaluate_text_quality(text: str, blocks: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    source_text = str(text or '')
    lines = [line.strip() for line in source_text.splitlines() if line.strip()]
    collapsed = re.sub(r'\s+', ' ', source_text).strip()
    alnum_chars = sum(1 for char in collapsed if char.isalnum())
    printable_chars = sum(1 for char in collapsed if not char.isspace())
    alpha_ratio = (alnum_chars / printable_chars) if printable_chars else 0.0
    avg_line_length = (sum(len(line) for line in lines) / len(lines)) if lines else 0.0
    normalized = _normalize_text(source_text)
    keyword_hits = [keyword for keyword in DOCUMENT_QUALITY_KEYWORDS if keyword in normalized]

    char_count = len(collapsed)
    line_count = len(lines) if lines else len(blocks or [])

    score = 0.0
    score += min(char_count / 700.0, 1.0) * 0.28
    score += min(line_count / 18.0, 1.0) * 0.20
    score += min(max((alpha_ratio - 0.18) / 0.52, 0.0), 1.0) * 0.18
    score += min(len(keyword_hits) / 3.0, 1.0) * 0.24
    score += min(avg_line_length / 42.0, 1.0) * 0.10
    score = round(min(score, 0.99), 4)

    reasons = []
    if char_count < 80:
        reasons.append('text_too_short')
    if line_count < 4:
        reasons.append('too_few_lines')
    if alpha_ratio < 0.28:
        reasons.append('low_alphanumeric_ratio')
    if not keyword_hits:
        reasons.append('no_relevant_keywords')

    usable = (
        char_count >= 80
        and line_count >= 4
        and alpha_ratio >= 0.28
        and score >= 0.58
    )

    if usable:
        reasons.append('usable_text')

    return {
        'score': score,
        'usable': usable,
        'reasons': reasons,
        'metrics': {
            'char_count': char_count,
            'line_count': line_count,
            'alphanumeric_ratio': round(alpha_ratio, 4),
            'avg_line_length': round(avg_line_length, 2),
            'keyword_hits': keyword_hits,
            'keyword_hit_count': len(keyword_hits),
        },
    }
