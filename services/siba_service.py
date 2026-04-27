import base64
import re
import unicodedata
import xml.etree.ElementTree as ET
from datetime import date, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SIBA_BA_NS = "http://sef.pt/BAws"
SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
SIBA_METHOD_NS = "http://sef.pt/"
DEFAULT_SIBA_ENDPOINT = "https://siba.ssi.gov.pt/baws/boletinsalojamento.asmx"

ET.register_namespace("", SIBA_BA_NS)
ET.register_namespace("soap", SOAP_NS)


class SibaError(RuntimeError):
    pass


def _text(value: Any) -> str:
    return str(value or "").strip()


def _date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = _text(value)
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw[:10]).date()
    except Exception:
        return None


def _xml_date(value: Any) -> str:
    parsed = _date(value)
    return f"{parsed.isoformat()}T00:00:00" if parsed else ""


def _digits(value: Any, max_len: int = 0) -> str:
    out = re.sub(r"\D+", "", _text(value))
    return out[:max_len] if max_len else out


def _doc(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", _text(value).upper())[:16]


def _normalize_limited(value: Any, max_len: int, uppercase: bool = True) -> str:
    out = _text(value).replace("’", "'").replace("`", "'")
    out = re.sub(r"\s+", " ", out)
    if uppercase:
        out = out.upper()
    return out[:max_len]


def _name(value: Any, max_len: int = 40) -> str:
    out = _normalize_limited(value, max_len=max_len, uppercase=True)
    allowed = []
    for ch in out:
        if ch.isalpha() or ch in " ÇÃÁÀÉÊÍÕÔÓÚ'-":
            allowed.append(ch)
        else:
            normalized = unicodedata.normalize("NFD", ch)
            base = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
            if base and base[0].isalpha():
                allowed.append(base[0].upper())
            elif ch.isspace():
                allowed.append(" ")
    return re.sub(r"\s+", " ", "".join(allowed)).strip()[:max_len]


def _add(parent: ET.Element, tag: str, value: Any) -> ET.Element:
    el = ET.SubElement(parent, f"{{{SIBA_BA_NS}}}{tag}")
    el.text = _text(value)
    return el


def _parse_postal(value: Any) -> tuple[str, str]:
    digits = _digits(value)
    return digits[:4], digits[4:7]


def build_siba_xml(data: dict[str, Any]) -> str:
    reservation = data.get("reservation") or {}
    unit = data.get("unit") or {}
    guests = list(data.get("guests") or [])

    root = ET.Element(f"{{{SIBA_BA_NS}}}MovimentoBAL")

    codigo_postal, zona_postal = _parse_postal(unit.get("codpost"))
    unidade = ET.SubElement(root, f"{{{SIBA_BA_NS}}}Unidade_Hoteleira")
    _add(unidade, "Codigo_Unidade_Hoteleira", _digits(unit.get("codigo"), 9))
    _add(unidade, "Estabelecimento", _digits(unit.get("estabelecimento"), 2).zfill(2))
    _add(unidade, "Nome", _normalize_limited(unit.get("nome"), 40))
    _add(unidade, "Abreviatura", _normalize_limited(unit.get("abreviatura") or unit.get("nome"), 15))
    _add(unidade, "Morada", _normalize_limited(unit.get("morada"), 40))
    _add(unidade, "Localidade", _normalize_limited(unit.get("localidade"), 30))
    _add(unidade, "Codigo_Postal", codigo_postal)
    _add(unidade, "Zona_Postal", zona_postal)
    _add(unidade, "Telefone", _digits(unit.get("telefone"), 10))
    _add(unidade, "Fax", _digits(unit.get("fax"), 10))
    _add(unidade, "Nome_Contacto", _normalize_limited(unit.get("contacto_nome"), 40))
    _add(unidade, "Email_Contacto", _normalize_limited(unit.get("contacto_email"), 140, uppercase=False))

    for guest in guests:
        boletim = ET.SubElement(root, f"{{{SIBA_BA_NS}}}Boletim_Alojamento")
        _add(boletim, "Apelido", _name(guest.get("apelido"), 40))
        _add(boletim, "Nome", _name(guest.get("nome"), 40))
        _add(boletim, "Nacionalidade", _normalize_limited(guest.get("nacionalidade_icao"), 3))
        _add(boletim, "Data_Nascimento", _xml_date(guest.get("data_nascimento")))
        _add(boletim, "Local_Nascimento", _normalize_limited(guest.get("local_nascimento"), 30))
        _add(boletim, "Documento_Identificacao", _doc(guest.get("num_doc")))
        _add(boletim, "Pais_Emissor_Documento", _normalize_limited(guest.get("pais_emissor_doc_icao"), 3))
        _add(boletim, "Tipo_Documento", _normalize_limited(guest.get("tipo_doc_siba"), 3))
        _add(boletim, "Data_Entrada", _xml_date(reservation.get("datain")))
        if _date(reservation.get("dataout")):
            _add(boletim, "Data_Saida", _xml_date(reservation.get("dataout")))
        _add(boletim, "Pais_Residencia_Origem", _normalize_limited(guest.get("pais_residencia_icao"), 3))
        _add(boletim, "Local_Residencia_Origem", _normalize_limited(guest.get("local_residencia"), 30))

    envio = ET.SubElement(root, f"{{{SIBA_BA_NS}}}Envio")
    _add(envio, "Numero_Ficheiro", int(data.get("numero_ficheiro") or 1))
    _add(envio, "Data_Movimento", _xml_date(data.get("data_movimento") or date.today()))

    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")


def _soap_text(value: Any) -> str:
    return _text(value)


def _soap_envelope(unidade_hoteleira: str, estabelecimento: int, chave: str, boletins_b64: str) -> bytes:
    envelope = ET.Element(f"{{{SOAP_NS}}}Envelope")
    body = ET.SubElement(envelope, f"{{{SOAP_NS}}}Body")
    method = ET.SubElement(body, f"{{{SIBA_METHOD_NS}}}EntregaBoletinsAlojamento")
    ET.SubElement(method, f"{{{SIBA_METHOD_NS}}}UnidadeHoteleira").text = _soap_text(unidade_hoteleira)
    ET.SubElement(method, f"{{{SIBA_METHOD_NS}}}Estabelecimento").text = str(int(estabelecimento or 0))
    ET.SubElement(method, f"{{{SIBA_METHOD_NS}}}ChaveAcesso").text = _soap_text(chave)
    ET.SubElement(method, f"{{{SIBA_METHOD_NS}}}Boletins").text = boletins_b64
    return ET.tostring(envelope, encoding="utf-8", xml_declaration=True)


def parse_siba_error_xml(raw: str) -> dict[str, str]:
    text = _text(raw)
    if not text or text == "0":
        return {}
    try:
        root = ET.fromstring(text.encode("utf-8"))
    except Exception:
        return {"codigo": "", "descricao": text}

    def find_any(name: str) -> str:
        for el in root.iter():
            if el.tag.rsplit("}", 1)[-1].lower() == name.lower():
                return _text(el.text)
        return ""

    return {
        "codigo": find_any("Codigo_Retorno"),
        "descricao": find_any("Descricao") or text,
    }


def send_siba_boletins(data: dict[str, Any], endpoint: str = DEFAULT_SIBA_ENDPOINT, timeout: int = 45) -> dict[str, Any]:
    siba = data.get("siba") or {}
    xml_payload = build_siba_xml(data)
    boletins_b64 = base64.b64encode(xml_payload.encode("utf-8")).decode("ascii")
    body = _soap_envelope(
        unidade_hoteleira=_digits(siba.get("uh"), 9),
        estabelecimento=int(siba.get("estabelecimento") or 0),
        chave=_digits(siba.get("chave")),
        boletins_b64=boletins_b64,
    )
    request = Request(
        endpoint,
        data=body,
        headers={
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": '"http://sef.pt/EntregaBoletinsAlojamento"',
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            response_text = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SibaError(f"SIBA HTTP {exc.code}: {detail[:1000]}") from exc
    except URLError as exc:
        raise SibaError(f"Erro de ligacao ao SIBA: {exc.reason}") from exc

    try:
        root = ET.fromstring(response_text.encode("utf-8"))
    except Exception as exc:
        raise SibaError(f"Resposta SIBA invalida: {response_text[:1000]}") from exc

    result = ""
    for el in root.iter():
        if el.tag.rsplit("}", 1)[-1] == "EntregaBoletinsAlojamentoResult":
            result = _text(el.text)
            break
    if result == "0":
        return {"ok": True, "result": result, "xml": xml_payload}

    error = parse_siba_error_xml(result)
    description = error.get("descricao") or result or "Erro desconhecido no SIBA."
    code = error.get("codigo") or ""
    raise SibaError(f"SIBA {code}: {description}" if code else f"SIBA: {description}")
