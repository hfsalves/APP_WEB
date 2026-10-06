from datetime import date


FATURA_TEXTO_MAX_LENGTH = 240
FATURA_TEXTO_LINE_MAX_LENGTH = 60


def current_fatura_date(today_value: date | None = None) -> date:
    """Use the current date for every reservation invoice issued to PHC."""
    return today_value or date.today()


def fatura_recipient_name(row: dict) -> str:
    """Prefer the billing name, falling back to the reservation guest name."""
    source = row or {}
    return (
        str(source.get('FTNOME') or '').strip()
        or str(source.get('NOME') or source.get('HOSPEDE') or '').strip()
        or 'Cliente Final'
    )


def normalize_fatura_texto(value) -> str:
    """Normalize and validate the free-text invoice lines stored on RS."""
    normalized = str(value or '').replace('\r\n', '\n').replace('\r', '\n')
    if len(normalized) > FATURA_TEXTO_MAX_LENGTH:
        raise ValueError(
            f'O texto da fatura não pode exceder {FATURA_TEXTO_MAX_LENGTH} caracteres.'
        )

    for number, line in enumerate(normalized.split('\n'), start=1):
        if len(line) > FATURA_TEXTO_LINE_MAX_LENGTH:
            raise ValueError(
                f'A linha {number} não pode exceder '
                f'{FATURA_TEXTO_LINE_MAX_LENGTH} caracteres.'
            )
    return normalized


def fatura_texto_lines(value) -> list[str]:
    """Return non-empty FI.DESIGN lines in their original order."""
    normalized = normalize_fatura_texto(value)
    return [line for line in normalized.split('\n') if line]


def append_fatura_texto_payload_lines(lines: list[dict], value) -> list[dict]:
    """Append zero-value PHC text rows after the billable invoice rows."""
    for design in fatura_texto_lines(value):
        lines.append({
            'ref': '',
            'design': design,
            'qtt': 0,
            'epv': 0,
            'tabiva': 4,
            'iva': 0,
        })
    return lines
