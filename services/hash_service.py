import hashlib
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


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


def _fmt_date(value) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    raw = _norm_text(value)
    return raw[:10] if raw else ""


def _fmt_datetime(value) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%S")
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time()).strftime("%Y-%m-%dT%H:%M:%S")
    raw = _norm_text(value).replace(" ", "T")
    if not raw:
        return ""
    if len(raw) == 10:
        return f"{raw}T00:00:00"
    if len(raw) == 16:
        return f"{raw}:00"
    return raw[:19]


def _doc_type_code(ft: dict) -> str:
    tipo_saft = _norm_text(ft.get("TIPOSAFT")).upper()
    if tipo_saft:
        return tipo_saft
    nmdoc = _norm_text(ft.get("NMDOC")).upper()
    if "SIMPLIFICADA" in nmdoc or nmdoc.startswith("FS"):
        return "FS"
    if "RECIBO" in nmdoc:
        return "FR"
    if "CRÉDITO" in nmdoc or "CREDITO" in nmdoc or nmdoc.startswith("NC"):
        return "NC"
    if "ORÇAMENTO" in nmdoc or "ORCAMENTO" in nmdoc or nmdoc.startswith("OR"):
        return "OR"
    if "PRO-FORMA" in nmdoc or "PRO FORMA" in nmdoc or nmdoc.startswith("PF"):
        return "PF"
    return "FT"


def ft_invoice_no(ft: dict) -> str:
    doc_type = _doc_type_code(ft)
    serie = _norm_text(ft.get("SERIE"))
    try:
        fno = int(_to_decimal(ft.get("FNO"), "0"))
    except Exception:
        fno = 0
    if serie:
        return f"{doc_type} {serie}/{fno}"
    return f"{doc_type} {fno}"


def ft_system_entry_datetime(ft: dict) -> str:
    return _fmt_datetime(ft.get("DTAlteracao") or ft.get("DTCriacao"))


def ft_signature_gross_total(ft: dict) -> str:
    etotal = ft.get("ETTOTAL")
    if etotal is None:
        etotal = ft.get("ETOTAL")
    if etotal is None:
        etotal = _to_decimal(ft.get("ETTILIQ"), "0") + _to_decimal(ft.get("ETTIVA"), "0")
    return fmt_decimal(etotal, 2)


def build_ft_hash_message(ft: dict, fi_rows: list[dict], hash_ant: str) -> str:
    return ";".join([
        _fmt_date(ft.get("FDATA")),
        ft_system_entry_datetime(ft),
        ft_invoice_no(ft),
        ft_signature_gross_total(ft),
        _norm_text(hash_ant),
    ])


def sha1_hex(message: str) -> tuple[bytes, str]:
    payload = (message or "").encode("utf-8")
    digest = hashlib.sha1(payload).digest()
    return digest, hashlib.sha1(payload).hexdigest()
