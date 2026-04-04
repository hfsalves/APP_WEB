import logging
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from sqlalchemy import text


logger = logging.getLogger(__name__)


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


def _fts_has_codigo_validacao_at(session) -> bool:
    try:
        row = session.execute(text("""
            SELECT TOP 1 1
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA='dbo'
              AND TABLE_NAME='FTS'
              AND COLUMN_NAME='CODIGO_VALIDACAO_AT'
        """)).first()
        return bool(row)
    except Exception:
        return False


def get_serie_validation_code(session, ft: dict):
    festamp = (ft.get("FESTAMP") or "").strip()
    ndoc = int(float(str(ft.get("NDOC") or 0)))
    serie = (ft.get("SERIE") or "").strip()
    ano = int(float(str(ft.get("FTANO") or 0)))
    has_series_code = _fts_has_codigo_validacao_at(session)
    select_code = ", ISNULL(CODIGO_VALIDACAO_AT,'') AS CODIGO_VALIDACAO_AT" if has_series_code else ""
    fts = session.execute(text(f"""
        SELECT TOP 1 FTSSTAMP{select_code}
        FROM dbo.FTS
        WHERE FESTAMP=:festamp AND NDOC=:ndoc AND ISNULL(SERIE,'')=:serie AND ANO=:ano
    """), {"festamp": festamp, "ndoc": ndoc, "serie": serie, "ano": ano}).mappings().first()
    if not fts:
        return "", None
    ftsstamp = str(fts.get("FTSSTAMP") or "").strip()
    if not ftsstamp:
        return "", None
    if has_series_code:
        return str((fts or {}).get("CODIGO_VALIDACAO_AT") or "").strip(), ftsstamp
    try:
        sx = session.execute(text("""
            SELECT TOP 1 ISNULL(COD_VALIDACAO_SERIE,'') AS COD_VALIDACAO_SERIE
            FROM dbo.FTSX
            WHERE FTSSTAMP=:s
        """), {"s": ftsstamp}).mappings().first()
        return str((sx or {}).get("COD_VALIDACAO_SERIE") or "").strip(), ftsstamp
    except Exception:
        return "", ftsstamp


def validate_validation_code(cod_validacao: str) -> str:
    code = str(cod_validacao or "").strip().upper()
    if not code:
        raise ValueError("Serie nao comunicada a AT ou sem codigo de validacao")
    if len(code) < 8:
        raise ValueError("ATCUD invalido - serie nao certificada. O codigo de validacao tem de ter pelo menos 8 caracteres.")
    return code


def validate_atcud(atcud: str, sequential_number) -> str:
    value = str(atcud or "").strip()
    seq = int(_to_decimal(sequential_number, "0"))
    if seq <= 0:
        raise ValueError("Numero sequencial invalido para ATCUD.")
    if not value:
        raise ValueError("ATCUD vazio.")
    if value.upper().startswith("ATCUD:"):
        raise ValueError("ATCUD invalido. O valor interno nao pode incluir o prefixo 'ATCUD:'.")
    if "-" not in value:
        raise ValueError("ATCUD invalido. Formato esperado: CODIGO_VALIDACAO_SERIE-NUMERO.")
    code, number = value.rsplit("-", 1)
    code = validate_validation_code(code)
    if not number.isdigit():
        raise ValueError("ATCUD invalido. O numero sequencial tem de ser numerico.")
    if int(number) != seq:
        raise ValueError("ATCUD invalido. O numero sequencial nao coincide com o documento.")
    return f"{code}-{int(number)}"


def validate_requirements(modo_teste: bool, cod_validacao: str, certificado: str, has_ftsx: bool):
    if not has_ftsx:
        raise ValueError("Serie sem configuracao base.")
    validate_validation_code(cod_validacao)
    if not (certificado or "").strip() and not modo_teste:
        raise ValueError("Parametro AT_CERTIFICADO vazio.")


def _extract_validation_code_and_label(serie) -> tuple[str, str]:
    if isinstance(serie, Mapping):
        code = (
            serie.get("CODIGO_VALIDACAO_AT")
            or serie.get("COD_VALIDACAO_SERIE")
            or serie.get("COD_VALIDACAO_SERIE_AT")
            or ""
        )
        label = (
            serie.get("SERIE")
            or serie.get("DESCR")
            or serie.get("FTSSTAMP")
            or ""
        )
        return str(code or "").strip(), str(label or "").strip()
    return str(serie or "").strip(), ""


def build_atcud(serie, fno: int) -> str:
    raw_code, serie_label = _extract_validation_code_and_label(serie)
    code = validate_validation_code(raw_code)
    seq = int(_to_decimal(fno, "0"))
    if seq <= 0:
        raise ValueError("Numero sequencial invalido para gerar ATCUD.")
    atcud = f"{code}-{seq}"
    logger.info(
        "ATCUD built | serie=%s | numero=%s | codigo_validacao=%s | atcud=%s",
        serie_label or "",
        seq,
        code,
        atcud,
    )
    return atcud


def map_doc_type(ft: dict) -> str:
    tiposaft = str(ft.get("TIPOSAFT") or "").strip().upper()
    if tiposaft:
        return tiposaft
    nmdoc = str(ft.get("NMDOC") or "").strip().upper()
    if nmdoc.startswith("GT") or "GUIA DE TRANSPORTE" in nmdoc:
        return "GT"
    if nmdoc.startswith("FS"):
        return "FS"
    if nmdoc.startswith("FR"):
        return "FR"
    if nmdoc.startswith("ND"):
        return "ND"
    if nmdoc.startswith("NC"):
        return "NC"
    if nmdoc.startswith("PF"):
        return "PF"
    if "FATURA" in nmdoc or "FACTURA" in nmdoc or nmdoc.startswith("FT"):
        return "FT"
    return "FT"


def _fmt_qr_doc_date(value) -> str:
    digits = _digits_only(value)
    if len(digits) >= 8:
        return digits[:8]
    raise ValueError("Data do documento invalida para QR fiscal.")


def _document_identifier(ft: dict, doc_type: str, fno: int) -> str:
    serie = str(ft.get("SERIE") or "").strip()
    if serie:
        return f"{doc_type} {serie}/{fno}"
    return f"{doc_type} {fno}"


def _certificate_number(value) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    normalized = raw.replace(",", ".")
    try:
        dec = Decimal(normalized)
        if dec == dec.to_integral_value():
            return str(int(dec))
    except Exception:
        pass
    return _digits_only(raw)


def _tax_region_code(ft: dict) -> str:
    country = _digits_only(ft.get("PAIS"))
    if country and country != "0":
        return country
    return "PT"


def _tax_summary_fields(ft: dict) -> list[str]:
    exempt_base = Decimal("0")
    reduced_base = Decimal("0")
    reduced_vat = Decimal("0")
    intermediate_base = Decimal("0")
    intermediate_vat = Decimal("0")
    normal_base = Decimal("0")
    normal_vat = Decimal("0")

    for i in range(1, 10):
        base = _to_decimal(ft.get(f"EIVAIN{i}"), "0")
        vat = _to_decimal(ft.get(f"EIVAV{i}"), "0")
        rate = _to_decimal(ft.get(f"IVATX{i}"), "0")
        if base == 0 and vat == 0 and rate == 0:
            continue
        if rate == 0:
            exempt_base += base
        elif rate <= Decimal("6.00"):
            reduced_base += base
            reduced_vat += vat
        elif rate <= Decimal("13.00"):
            intermediate_base += base
            intermediate_vat += vat
        else:
            normal_base += base
            normal_vat += vat

    total_base = exempt_base + reduced_base + intermediate_base + normal_base
    if total_base <= 0:
        return ["I1:0"]

    fields = ["I1:PT"]
    if exempt_base > 0:
        fields.append(f"I2:{_fmt_decimal(exempt_base, 2)}")
    if reduced_base > 0 or reduced_vat > 0:
        fields.append(f"I3:{_fmt_decimal(reduced_base, 2)}")
        fields.append(f"I4:{_fmt_decimal(reduced_vat, 2)}")
    if intermediate_base > 0 or intermediate_vat > 0:
        fields.append(f"I5:{_fmt_decimal(intermediate_base, 2)}")
        fields.append(f"I6:{_fmt_decimal(intermediate_vat, 2)}")
    if normal_base > 0 or normal_vat > 0:
        fields.append(f"I7:{_fmt_decimal(normal_base, 2)}")
        fields.append(f"I8:{_fmt_decimal(normal_vat, 2)}")
    return fields


def build_fiscal_qr_payload(ft: dict, fe: dict, atcud: str, certificado: str, modo_teste: bool) -> str:
    fe_nif = _digits_only(fe.get("NIF"))
    b_nif = _digits_only(ft.get("NCONT"))
    if not b_nif and modo_teste:
        b_nif = "999999990"
    if not fe_nif:
        raise ValueError("NIF do emitente invalido.")
    if not b_nif and not modo_teste:
        raise ValueError("NIF do adquirente vazio.")

    fno = int(_to_decimal(ft.get("FNO"), "0"))
    if fno <= 0:
        raise ValueError("Numero sequencial invalido para QR fiscal.")

    doc_type = map_doc_type(ft)
    atcud_value = validate_atcud(atcud, fno)
    estado = "A" if int(_to_decimal(ft.get("ANULADA"), "0")) == 1 else "N"
    fdata = _fmt_qr_doc_date(ft.get("FDATA"))
    ident = _document_identifier(ft, doc_type, fno)
    h4 = str(ft.get("ASSINATURA") or ft.get("HASH") or "")[:4]
    pais = _tax_region_code(ft)
    certificado_num = _certificate_number(certificado)

    parts = [
        f"A:{fe_nif}",
        f"B:{b_nif}",
        f"C:{pais}",
        f"D:{doc_type}",
        f"E:{estado}",
        f"F:{fdata}",
        f"G:{ident}",
        f"H:{atcud_value}",
    ]
    parts.extend(_tax_summary_fields(ft))
    parts.extend([
        f"N:{_fmt_decimal(ft.get('ETTIVA'), 2)}",
        f"O:{_fmt_decimal(ft.get('ETOTAL'), 2)}",
        f"Q:{h4}",
        f"R:{certificado_num}",
    ])

    payload = "*".join(parts)
    logger.debug(
        "QR payload encoded for %s %s/%s: %s",
        doc_type,
        str(ft.get("SERIE") or "").strip(),
        fno,
        payload,
    )
    return payload


def build_qr_payload(ft: dict, fe: dict, atcud: str, certificado: str, modo_teste: bool) -> str:
    return build_fiscal_qr_payload(ft, fe, atcud, certificado, modo_teste)
