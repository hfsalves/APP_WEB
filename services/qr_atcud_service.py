from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from sqlalchemy import text


def _to_decimal(value, default="0"):
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return Decimal(default)
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError):
        return Decimal(default)


def _fmt_decimal(value, places=2):
    quant = Decimal("1").scaleb(-int(places))
    val = _to_decimal(value, "0").quantize(quant, rounding=ROUND_HALF_UP)
    return format(val, "f")


def _digits_only(value):
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _param_value_from_row(row):
    tipo = str((row or {}).get("TIPO") or "").strip().upper()
    if tipo == "N":
        return str((row or {}).get("NVALOR") or 0)
    if tipo == "D":
        d = (row or {}).get("DVALOR")
        try:
            return d.strftime("%Y-%m-%d")
        except Exception:
            return str(d or "")
    if tipo == "L":
        return "1" if int((row or {}).get("LVALOR") or 0) == 1 else "0"
    return str((row or {}).get("CVALOR") or "")


def get_param(session, code: str, default=None):
    key = (code or "").strip()
    if not key:
        return default
    row = session.execute(text("""
        SELECT TOP 1 PARAMETRO, TIPO, CVALOR, DVALOR, NVALOR, LVALOR
        FROM dbo.PARA
        WHERE UPPER(LTRIM(RTRIM(PARAMETRO))) = UPPER(:p)
    """), {"p": key}).mappings().first()
    if not row:
        return default
    val = _param_value_from_row(dict(row))
    return val if str(val).strip() != "" else default


def get_serie_validation_code(session, ft: dict):
    festamp = (ft.get("FESTAMP") or "").strip()
    ndoc = int(float(str(ft.get("NDOC") or 0)))
    serie = (ft.get("SERIE") or "").strip()
    ano = int(float(str(ft.get("FTANO") or 0)))
    fts = session.execute(text("""
        SELECT TOP 1 FTSSTAMP
        FROM dbo.FTS
        WHERE FESTAMP=:festamp AND NDOC=:ndoc AND ISNULL(SERIE,'')=:serie AND ANO=:ano
    """), {"festamp": festamp, "ndoc": ndoc, "serie": serie, "ano": ano}).mappings().first()
    if not fts:
        return "", None
    ftsstamp = str(fts.get("FTSSTAMP") or "").strip()
    if not ftsstamp:
        return "", None
    try:
        sx = session.execute(text("""
            SELECT TOP 1 ISNULL(COD_VALIDACAO_SERIE,'') AS COD_VALIDACAO_SERIE
            FROM dbo.FTSX
            WHERE FTSSTAMP=:s
        """), {"s": ftsstamp}).mappings().first()
        return str((sx or {}).get("COD_VALIDACAO_SERIE") or "").strip(), ftsstamp
    except Exception:
        return "", ftsstamp


def validate_requirements(modo_teste: bool, cod_validacao: str, certificado: str, has_ftsx: bool):
    if modo_teste:
        return
    if not has_ftsx:
        raise ValueError("Série sem configuração FTSX.")
    if not (cod_validacao or "").strip():
        raise ValueError("COD_VALIDACAO_SERIE vazio para a série.")
    if not (certificado or "").strip():
        raise ValueError("Parâmetro AT_CERTIFICADO vazio.")


def build_atcud(cod_validacao: str, fno: int) -> str:
    return f"{(cod_validacao or '').strip()}-{int(fno or 0)}"


def map_doc_type(ft: dict) -> str:
    nmdoc = str(ft.get("NMDOC") or "").strip().upper()
    if nmdoc.startswith("FS"):
        return "FS"
    if nmdoc.startswith("FR"):
        return "FR"
    if nmdoc.startswith("ND"):
        return "ND"
    if nmdoc.startswith("NC"):
        return "NC"
    if "FATURA" in nmdoc or "FACTURA" in nmdoc or nmdoc.startswith("FT"):
        return "FT"
    return "FT"


def build_qr_payload(ft: dict, fe: dict, atcud: str, certificado: str, modo_teste: bool) -> str:
    fe_nif = _digits_only(fe.get("NIF"))
    b_nif = _digits_only(ft.get("NCONT"))
    if not b_nif and modo_teste:
        b_nif = "999999990"
    if not fe_nif:
        raise ValueError("NIF do emitente inválido.")
    if not b_nif and not modo_teste:
        raise ValueError("NIF do adquirente vazio.")

    estado = "A" if int(_to_decimal(ft.get("ANULADA"), "0")) == 1 else "N"
    fdata = str(ft.get("FDATA") or "").strip()
    ident = f"{str(ft.get('NMDOC') or '').strip()} {str(ft.get('SERIE') or '').strip()}/{int(_to_decimal(ft.get('FNO'), '0'))}"
    h4 = str(ft.get("HASH") or "")[:4]
    pais = "PT"
    qr_ver = str(ft.get("_QR_VERSION") or "").strip()

    parts = [
        f"A:{fe_nif}",
        f"B:{b_nif}",
        f"C:{pais}",
        f"D:{map_doc_type(ft)}",
        f"E:{estado}",
        f"F:{fdata}",
        f"G:{ident}",
        f"H:{atcud}",
    ]

    pos = 1
    for i in range(1, 10):
        base = _to_decimal(ft.get(f"EIVAIN{i}"), "0")
        iva = _to_decimal(ft.get(f"EIVAV{i}"), "0")
        tx = _to_decimal(ft.get(f"IVATX{i}"), "0")
        if base > 0 or tx > 0:
            parts.append(f"I{pos}:{_fmt_decimal(base, 2)}")
            parts.append(f"J{pos}:{_fmt_decimal(iva, 2)}")
            parts.append(f"K{pos}:{_fmt_decimal(tx, 2)}")
            pos += 1

    parts.extend([
        f"N:{_fmt_decimal(ft.get('ETTIVA'), 2)}",
        f"O:{_fmt_decimal(ft.get('ETOTAL'), 2)}",
        f"Q:{h4}",
        f"R:{str(certificado or '').strip()}",
    ])
    if qr_ver:
        parts.append(f"V:{qr_ver}")

    return "*".join(parts)

