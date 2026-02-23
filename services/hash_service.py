import hashlib
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


"""
Hash message builder V1 interna.
Esta composição é determinística e isolada para futura substituição
pela composição final de certificação fiscal.
"""


def _to_decimal(value, default="0"):
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return Decimal(default)
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError):
        return Decimal(default)


def fmt_decimal(value, places=2) -> str:
    quant = Decimal("1").scaleb(-int(places))
    val = _to_decimal(value, "0").quantize(quant, rounding=ROUND_HALF_UP)
    return format(val, "f")


def _norm_text(value) -> str:
    return str(value or "").strip()


def build_ft_hash_message(ft: dict, fi_rows: list[dict], hash_ant: str) -> str:
    header_parts = [
        _norm_text(ft.get("FDATA")),
        _norm_text(ft.get("NMDOC")),
        _norm_text(ft.get("SERIE")),
        _norm_text(ft.get("FNO")),
    ]
    etotal = ft.get("ETTOTAL")
    if etotal is None:
        etotal = _to_decimal(ft.get("ETTILIQ"), "0") + _to_decimal(ft.get("ETTIVA"), "0")
    header_parts.append(fmt_decimal(etotal, 6))
    header_parts.append(_norm_text(hash_ant))

    ordered_rows = sorted(fi_rows or [], key=lambda r: int(_to_decimal((r or {}).get("LORDEM"), "0")))
    line_parts = []
    for row in ordered_rows:
        line_parts.extend([
            _norm_text((row or {}).get("REF")),
            _norm_text((row or {}).get("DESIGN")),
            fmt_decimal((row or {}).get("QTT"), 3),
            fmt_decimal((row or {}).get("EPV"), 6),
            fmt_decimal((row or {}).get("IVA"), 2),
            "1" if int(_to_decimal((row or {}).get("IVAINCL"), "0")) == 1 else "0",
            str(int(_to_decimal((row or {}).get("TABIVA"), "0"))),
        ])

    return ";".join(header_parts + line_parts)


def sha1_hex(message: str) -> tuple[bytes, str]:
    payload = (message or "").encode("utf-8")
    digest = hashlib.sha1(payload).digest()
    return digest, hashlib.sha1(payload).hexdigest()

