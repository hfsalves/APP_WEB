import os
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO
from typing import Any
from xml.etree import ElementTree as ET

from sqlalchemy import text

from services.qr_atcud_service import get_param as qr_get_param


SAFT_NS = "urn:OECD:StandardAuditFile-Tax:PT_1.04_01"
SAFT_VERSION = "1.04_01"
ALLOWED_DOC_TYPES = {"FT", "FR", "NC"}


class SaftValidationError(ValueError):
    pass


def _to_decimal(value: Any, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    raw = str(value).strip()
    if not raw:
        return Decimal(default)
    try:
        return Decimal(raw.replace(",", "."))
    except (InvalidOperation, ValueError):
        return Decimal(default)


def _money(value: Any) -> str:
    quantized = _to_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return format(quantized, "f")


def _decimal_6(value: Any) -> str:
    quantized = _to_decimal(value).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    return format(quantized, "f")


def _fmt_date(value: Any) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    raw = str(value or "").strip()
    return raw[:10] if raw else ""


def _fmt_datetime(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%S")
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time()).strftime("%Y-%m-%dT%H:%M:%S")
    raw = str(value or "").strip()
    if not raw:
        return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    clean = raw.replace(" ", "T")
    if len(clean) == 10:
        return f"{clean}T00:00:00"
    if len(clean) == 16:
        return f"{clean}:00"
    return clean[:19]


def _safe_text(value: Any, fallback: str = "") -> str:
    raw = str(value or "").strip()
    return raw or fallback


def _digits_only(value: Any) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _country_code(value: Any) -> str:
    raw = _safe_text(value).upper()
    if len(raw) == 2 and raw.isalpha():
        return raw
    return "PT"


def _normalize_filters(filters: dict[str, Any] | None) -> dict[str, Any]:
    payload = dict(filters or {})
    dt_ini_raw = _safe_text(payload.get("dt_ini"))
    dt_fim_raw = _safe_text(payload.get("dt_fim"))
    if not dt_ini_raw or not dt_fim_raw:
        raise SaftValidationError("Preenche a data inicial e a data final.")
    try:
        dt_ini = datetime.strptime(dt_ini_raw[:10], "%Y-%m-%d").date()
        dt_fim = datetime.strptime(dt_fim_raw[:10], "%Y-%m-%d").date()
    except ValueError as exc:
        raise SaftValidationError("Datas inválidas para emissão SAF-T.") from exc
    if dt_ini > dt_fim:
        raise SaftValidationError("A data inicial não pode ser superior à data final.")
    if dt_ini.year != dt_fim.year:
        raise SaftValidationError("A exportação SAF-T deve respeitar um único ano fiscal.")

    serie = _safe_text(payload.get("serie"))
    tipo_doc = _safe_text(payload.get("tipo_doc")).upper()
    if tipo_doc and tipo_doc not in ALLOWED_DOC_TYPES:
        raise SaftValidationError("Tipo de documento inválido.")

    incluir_emitidos = bool(payload.get("emitidos_only", True))
    return {
        "dt_ini": dt_ini,
        "dt_fim": dt_fim,
        "serie": serie,
        "tipo_doc": tipo_doc,
        "emitidos_only": incluir_emitidos,
    }


def _ns(tag: str) -> str:
    return f"{{{SAFT_NS}}}{tag}"


def get_saft_filter_options(session) -> dict[str, Any]:
    series = session.execute(text("""
        SELECT DISTINCT LTRIM(RTRIM(ISNULL(SERIE,''))) AS SERIE
        FROM dbo.FT
        WHERE LTRIM(RTRIM(ISNULL(SERIE,''))) <> ''
        ORDER BY SERIE
    """)).mappings().all()
    return {
        "series": [str(row.get("SERIE") or "").strip() for row in series if str(row.get("SERIE") or "").strip()],
        "doc_types": ["FT", "FR", "NC"],
    }


def _table_columns(session, table_name: str) -> set[str]:
    try:
        rows = session.execute(text("""
            SELECT UPPER(COLUMN_NAME) AS CN
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = :table_name
        """), {"table_name": table_name}).mappings().all()
    except Exception:
        return set()
    return {str(row.get("CN") or "").upper() for row in rows}


def _doc_where_sql(filters: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    clauses = [
        "CAST(FT.FDATA AS date) BETWEEN :dt_ini AND :dt_fim",
        "ISNULL(FT.FNO,0) > 0",
        "UPPER(LTRIM(RTRIM(ISNULL(FTS.TIPOSAFT,'')))) IN ('FT','FR','NC')",
    ]
    params: dict[str, Any] = {
        "dt_ini": filters["dt_ini"].isoformat(),
        "dt_fim": filters["dt_fim"].isoformat(),
    }
    if filters.get("emitidos_only", True):
        clauses.append("ISNULL(FT.BLOQUEADO,0) = 1")
    if filters.get("serie"):
        clauses.append("LTRIM(RTRIM(ISNULL(FT.SERIE,''))) = :serie")
        params["serie"] = filters["serie"]
    if filters.get("tipo_doc"):
        clauses.append("UPPER(LTRIM(RTRIM(ISNULL(FTS.TIPOSAFT,'')))) = :tipo_doc")
        params["tipo_doc"] = filters["tipo_doc"]
    return " AND ".join(clauses), params


def _load_headers(session, filters: dict[str, Any]) -> list[dict[str, Any]]:
    where_sql, params = _doc_where_sql(filters)
    rows = session.execute(text(f"""
        SELECT
            FT.*,
            ISNULL(FTS.TIPOSAFT, '') AS TIPOSAFT,
            ISNULL(FTS.DESCR, '') AS SERIE_DESCR,
            ISNULL(FTSX.HASHVER, '') AS SERIE_HASHVER,
            ISNULL(FTSX.COD_VALIDACAO_SERIE, '') AS COD_VALIDACAO_SERIE
        FROM dbo.FT AS FT
        INNER JOIN dbo.FTS AS FTS
          ON FTS.FESTAMP = FT.FESTAMP
         AND FTS.NDOC = FT.NDOC
         AND LTRIM(RTRIM(ISNULL(FTS.SERIE,''))) = LTRIM(RTRIM(ISNULL(FT.SERIE,'')))
         AND ISNULL(FTS.ANO,0) = ISNULL(FT.FTANO,0)
        LEFT JOIN dbo.FTSX AS FTSX
          ON FTSX.FTSSTAMP = FTS.FTSSTAMP
        WHERE {where_sql}
        ORDER BY CAST(FT.FDATA AS date), LTRIM(RTRIM(ISNULL(FT.SERIE,''))), ISNULL(FT.FNO,0)
    """), params).mappings().all()
    return [dict(row) for row in rows]


def _load_lines(session, filters: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    where_sql, params = _doc_where_sql(filters)
    rows = session.execute(text(f"""
        SELECT
            FI.*,
            ISNULL(FTS.TIPOSAFT, '') AS TIPOSAFT,
            FT.NMDOC AS FT_NMDOC,
            FT.SERIE AS FT_SERIE,
            FT.FNO AS FT_FNO,
            FT.FDATA AS FT_FDATA
        FROM dbo.FI AS FI
        INNER JOIN dbo.FT AS FT
          ON FT.FTSTAMP = FI.FTSTAMP
        INNER JOIN dbo.FTS AS FTS
          ON FTS.FESTAMP = FT.FESTAMP
         AND FTS.NDOC = FT.NDOC
         AND LTRIM(RTRIM(ISNULL(FTS.SERIE,''))) = LTRIM(RTRIM(ISNULL(FT.SERIE,'')))
         AND ISNULL(FTS.ANO,0) = ISNULL(FT.FTANO,0)
        WHERE {where_sql}
        ORDER BY CAST(FT.FDATA AS date), LTRIM(RTRIM(ISNULL(FT.SERIE,''))), ISNULL(FT.FNO,0), ISNULL(FI.LORDEM,0), FI.FISTAMP
    """), params).mappings().all()
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        item = dict(row)
        unit_price = _line_unit_price(item)
        item["UNITPRICE_FISCAL"] = format(unit_price, "f") if unit_price is not None else None
        grouped[str(item.get("FTSTAMP") or "").strip()].append(item)
    return grouped


def _pick_first(row: dict[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        if key in row:
            value = _safe_text(row.get(key))
            if value:
                return value
    return default


def _load_emitter(session, festamp: str) -> dict[str, Any]:
    fe_cols = _table_columns(session, "FE")
    name_expr = "ISNULL(NOME,'')" if "NOME" in fe_cols else "''"
    nome_com_expr = "ISNULL(NOMECOM,'')" if "NOMECOM" in fe_cols else "''"
    morada_expr = "ISNULL(MORADA,'')" if "MORADA" in fe_cols else "''"
    local_expr = "ISNULL(LOCAL,'')" if "LOCAL" in fe_cols else "''"
    codpost_expr = "ISNULL(CODPOST,'')" if "CODPOST" in fe_cols else "''"
    pais_expr = "CONVERT(varchar(30), ISNULL(PAIS,''))" if "PAIS" in fe_cols else "''"
    row = session.execute(text(f"""
        SELECT TOP 1
            FE.*,
            {name_expr} AS FE_NOME,
            {nome_com_expr} AS FE_NOMECOM,
            {morada_expr} AS FE_MORADA,
            {local_expr} AS FE_LOCAL,
            {codpost_expr} AS FE_CODPOST,
            {pais_expr} AS FE_PAIS
        FROM dbo.FE AS FE
        WHERE FESTAMP = :f
    """), {"f": festamp}).mappings().first()
    if not row:
        raise SaftValidationError("Emitente não encontrado para os documentos selecionados.")
    return dict(row)


def _load_app_params(session) -> dict[str, str]:
    rows = session.execute(text("""
        SELECT PARAMETRO, TIPO, CVALOR, DVALOR, NVALOR, LVALOR
        FROM dbo.PARA
    """)).mappings().all()
    out: dict[str, str] = {}
    for row in rows:
        code = _safe_text(row.get("PARAMETRO")).upper()
        if not code:
            continue
        tipo = _safe_text(row.get("TIPO")).upper()
        if tipo == "N":
            value = str(row.get("NVALOR") or "")
        elif tipo == "D":
            value = _fmt_date(row.get("DVALOR"))
        elif tipo == "L":
            value = "1" if bool(row.get("LVALOR")) else "0"
        else:
            value = _safe_text(row.get("CVALOR"))
        out[code] = value
    return out


def _tax_code_from_percentage(percentage: Decimal) -> str:
    pct = percentage.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if pct == Decimal("23.00"):
        return "NOR"
    if pct == Decimal("13.00"):
        return "INT"
    if pct == Decimal("6.00"):
        return "RED"
    if pct == Decimal("0.00"):
        return "ISE"
    return "OUT"


def _customer_id_from_doc(doc: dict[str, Any]) -> str:
    no = int(_to_decimal(doc.get("NO"), "0"))
    if no > 0:
        return f"C{no}"
    nif = _digits_only(doc.get("NCONT"))
    if nif:
        return f"N{nif}"
    return "CONSUMIDOR_FINAL"


def _customer_tax_id(doc: dict[str, Any], warnings: list[str], warned: set[str]) -> str:
    raw_nif = _digits_only(doc.get("NCONT"))
    if len(raw_nif) == 9:
        return raw_nif
    cid = _customer_id_from_doc(doc)
    if cid not in warned:
        warnings.append(f"Cliente {cid} sem NIF português válido. Foi usado 999999990 no SAF-T.")
        warned.add(cid)
    return "999999990"


def _product_code(line: dict[str, Any], warnings: list[str], warned: set[str]) -> str:
    ref = _safe_text(line.get("REF"))
    if ref:
        return ref[:60]
    key = str(line.get("FISTAMP") or line.get("LORDEM") or "0")
    if key not in warned:
        warnings.append(f"Linha {key} sem REF. Foi gerado código técnico de produto.")
        warned.add(key)
    return f"GEN-{key}"[:60]


def _product_code_no_warning(line: dict[str, Any]) -> str:
    ref = _safe_text(line.get("REF"))
    if ref:
        return ref[:60]
    key = str(line.get("FISTAMP") or line.get("LORDEM") or "0")
    return f"GEN-{key}"[:60]


def _line_unit_price(line: dict[str, Any]) -> Decimal | None:
    quantity = _to_decimal(line.get("QTT"), "0").quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    if quantity == Decimal("0.000000"):
        return None
    provided = line.get("UNITPRICE_FISCAL")
    if provided not in (None, ""):
        return _to_decimal(provided, "0").quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    net_amount = _to_decimal(line.get("ETILIQUIDO"), "0").quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    return (net_amount / quantity).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def _build_dataset(session, filters: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_filters(filters)
    headers = _load_headers(session, normalized)
    if not headers:
        raise SaftValidationError("Não existem documentos válidos para o período selecionado.")

    festamps = {str(row.get("FESTAMP") or "").strip() for row in headers if str(row.get("FESTAMP") or "").strip()}
    if not festamps:
        raise SaftValidationError("Os documentos selecionados não têm emitente definido.")
    if len(festamps) > 1:
        raise SaftValidationError("A geração SAF-T suporta apenas um emitente por ficheiro.")

    emitter = _load_emitter(session, next(iter(festamps)))
    app_params = _load_app_params(session)
    certificado = _safe_text(qr_get_param(session, "AT_CERTIFICADO", "") or "")
    if not certificado:
        raise SaftValidationError("Parâmetro AT_CERTIFICADO não definido.")

    emit_nif = _digits_only(emitter.get("NIF"))
    if len(emit_nif) != 9:
        raise SaftValidationError("O emitente não tem NIF válido em FE.")

    lines_by_doc = _load_lines(session, normalized)
    warnings: list[str] = []

    valid_headers: list[dict[str, Any]] = []
    for header in headers:
        ftstamp = _safe_text(header.get("FTSTAMP"))
        if not lines_by_doc.get(ftstamp):
            warnings.append(f"Documento {header.get('NMDOC')} {header.get('SERIE')}/{header.get('FNO')} ignorado por não ter linhas.")
            continue
        valid_headers.append(header)

    if not valid_headers:
        raise SaftValidationError("Não existem documentos exportáveis com linhas válidas.")

    totals = {
        "documents": len(valid_headers),
        "customers": 0,
        "net_total": Decimal("0.00"),
        "tax_total": Decimal("0.00"),
        "gross_total": Decimal("0.00"),
    }

    customer_warning_keys: set[str] = set()
    product_warning_keys: set[str] = set()
    customers: dict[str, dict[str, Any]] = {}
    products: dict[str, dict[str, Any]] = {}
    tax_table: dict[str, dict[str, Any]] = {}

    for header in valid_headers:
        totals["net_total"] += _to_decimal(header.get("ETTILIQ"), "0")
        totals["tax_total"] += _to_decimal(header.get("ETTIVA"), "0")
        totals["gross_total"] += _to_decimal(header.get("ETOTAL"), "0")

        customer_id = _customer_id_from_doc(header)
        if customer_id not in customers:
            customers[customer_id] = {
                "CustomerID": customer_id,
                "AccountID": customer_id,
                "CustomerTaxID": _customer_tax_id(header, warnings, customer_warning_keys),
                "CompanyName": _pick_first(header, "NOME", default="Consumidor final"),
                "AddressDetail": _pick_first(header, "MORADA", default=""),
                "City": _pick_first(header, "LOCAL", default=""),
                "PostalCode": _pick_first(header, "CODPOST", default=""),
                "Country": _country_code(_pick_first(header, "PAIS", default="PT")),
            }

        for line in lines_by_doc.get(_safe_text(header.get("FTSTAMP")), []):
            product_code = _product_code(line, warnings, product_warning_keys)
            if product_code not in products:
                products[product_code] = {
                    "ProductType": "P",
                    "ProductCode": product_code,
                    "ProductGroup": _safe_text(line.get("FAMILIA"))[:50],
                    "Description": _safe_text(line.get("DESIGN"), "Linha faturação")[:200],
                    "ProductNumberCode": product_code,
                }
            percentage = _to_decimal(line.get("IVA"), "0").quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            tax_key = f"PT|IVA|{percentage}"
            if tax_key not in tax_table:
                tax_table[tax_key] = {
                    "TaxType": "IVA",
                    "TaxCountryRegion": "PT",
                    "TaxCode": _tax_code_from_percentage(percentage),
                    "Description": f"IVA {_money(percentage)}%",
                    "TaxPercentage": percentage,
                }

    totals["customers"] = len(customers)

    company_name = _pick_first(
        emitter,
        "FE_NOMECOM",
        "FE_NOME",
        "NOMECOM",
        "NOME",
        default=_safe_text(app_params.get("EMP_NOME_COM") or app_params.get("EMP_NOME") or "StationZero"),
    )
    business_name = _pick_first(
        emitter,
        "FE_NOME",
        "FE_NOMECOM",
        "NOME",
        "NOMECOM",
        default=_safe_text(app_params.get("EMP_NOME") or company_name),
    )

    header_data = {
        "AuditFileVersion": SAFT_VERSION,
        "CompanyID": emit_nif,
        "TaxRegistrationNumber": emit_nif,
        "TaxAccountingBasis": "F",
        "CompanyName": company_name,
        "BusinessName": business_name,
        "CompanyAddress": {
            "AddressDetail": _pick_first(emitter, "FE_MORADA", "MORADA", default=_safe_text(app_params.get("EMP_MORADA"))),
            "City": _pick_first(emitter, "FE_LOCAL", "LOCAL", default=_safe_text(app_params.get("EMP_LOCAL"))),
            "PostalCode": _pick_first(emitter, "FE_CODPOST", "CODPOST", default=_safe_text(app_params.get("EMP_CODPOST"))),
            "Country": _country_code(_pick_first(emitter, "FE_PAIS", "PAIS", default=_safe_text(app_params.get("EMP_PAIS") or "PT"))),
        },
        "FiscalYear": normalized["dt_ini"].year,
        "StartDate": normalized["dt_ini"].isoformat(),
        "EndDate": normalized["dt_fim"].isoformat(),
        "CurrencyCode": "EUR",
        "DateCreated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "TaxEntity": "PT",
        "ProductCompanyTaxID": emit_nif,
        "SoftwareCertificateNumber": certificado,
        "ProductID": "StationZero",
        "ProductVersion": os.environ.get("APP_VERSION", "dev"),
    }

    return {
        "filters": normalized,
        "header": header_data,
        "documents": valid_headers,
        "lines_by_doc": lines_by_doc,
        "customers": customers,
        "products": products,
        "tax_table": tax_table,
        "summary": {
            "documents": totals["documents"],
            "customers": totals["customers"],
            "net_total": _money(totals["net_total"]),
            "tax_total": _money(totals["tax_total"]),
            "gross_total": _money(totals["gross_total"]),
        },
        "warnings": warnings,
    }


def preview_saft_sales(session, filters: dict[str, Any] | None) -> dict[str, Any]:
    dataset = _build_dataset(session, filters or {})
    return {
        "filters": {
            "dt_ini": dataset["filters"]["dt_ini"].isoformat(),
            "dt_fim": dataset["filters"]["dt_fim"].isoformat(),
            "serie": dataset["filters"]["serie"],
            "tipo_doc": dataset["filters"]["tipo_doc"],
            "emitidos_only": dataset["filters"]["emitidos_only"],
        },
        "summary": dataset["summary"],
        "warnings": dataset["warnings"],
    }


def _append_text(parent: ET.Element, tag: str, value: Any) -> ET.Element:
    el = ET.SubElement(parent, _ns(tag))
    el.text = _safe_text(value)
    return el


def _build_xml_tree(dataset: dict[str, Any]) -> ET.Element:
    ET.register_namespace("", SAFT_NS)
    root = ET.Element(_ns("AuditFile"))

    header = ET.SubElement(root, _ns("Header"))
    hdr = dataset["header"]
    for field in (
        "AuditFileVersion",
        "CompanyID",
        "TaxRegistrationNumber",
        "TaxAccountingBasis",
        "CompanyName",
        "BusinessName",
        "FiscalYear",
        "StartDate",
        "EndDate",
        "CurrencyCode",
        "DateCreated",
        "TaxEntity",
        "ProductCompanyTaxID",
        "SoftwareCertificateNumber",
        "ProductID",
        "ProductVersion",
    ):
        _append_text(header, field, hdr.get(field))

    company_address = ET.SubElement(header, _ns("CompanyAddress"))
    for field in ("AddressDetail", "City", "PostalCode", "Country"):
        _append_text(company_address, field, hdr["CompanyAddress"].get(field))

    master_files = ET.SubElement(root, _ns("MasterFiles"))
    for customer in dataset["customers"].values():
        customer_el = ET.SubElement(master_files, _ns("Customer"))
        _append_text(customer_el, "CustomerID", customer["CustomerID"])
        _append_text(customer_el, "AccountID", customer["AccountID"])
        _append_text(customer_el, "CustomerTaxID", customer["CustomerTaxID"])
        _append_text(customer_el, "CompanyName", customer["CompanyName"])
        billing_address = ET.SubElement(customer_el, _ns("BillingAddress"))
        for field in ("AddressDetail", "City", "PostalCode", "Country"):
            _append_text(billing_address, field, customer.get(field))

    for product in dataset["products"].values():
        product_el = ET.SubElement(master_files, _ns("Product"))
        for field in ("ProductType", "ProductCode", "ProductGroup", "Description", "ProductNumberCode"):
            _append_text(product_el, field, product.get(field))

    tax_table_el = ET.SubElement(master_files, _ns("TaxTable"))
    for tax in dataset["tax_table"].values():
        tax_entry = ET.SubElement(tax_table_el, _ns("TaxTableEntry"))
        _append_text(tax_entry, "TaxType", tax["TaxType"])
        _append_text(tax_entry, "TaxCountryRegion", tax["TaxCountryRegion"])
        _append_text(tax_entry, "TaxCode", tax["TaxCode"])
        _append_text(tax_entry, "Description", tax["Description"])
        _append_text(tax_entry, "TaxPercentage", _money(tax["TaxPercentage"]))

    source_documents = ET.SubElement(root, _ns("SourceDocuments"))
    sales_invoices = ET.SubElement(source_documents, _ns("SalesInvoices"))
    _append_text(sales_invoices, "NumberOfEntries", str(dataset["summary"]["documents"]))

    total_debit = Decimal("0.00")
    total_credit = Decimal("0.00")

    for header_row in dataset["documents"]:
        gross_total = _to_decimal(header_row.get("ETOTAL"), "0")
        doc_type = _safe_text(header_row.get("TIPOSAFT") or header_row.get("NMDOC")).upper() or "FT"
        if doc_type == "NC":
            total_credit += gross_total.copy_abs()
        else:
            total_debit += gross_total.copy_abs()

    _append_text(sales_invoices, "TotalDebit", _money(total_debit))
    _append_text(sales_invoices, "TotalCredit", _money(total_credit))

    for header_row in dataset["documents"]:
        invoice_el = ET.SubElement(sales_invoices, _ns("Invoice"))
        doc_type = _safe_text(header_row.get("TIPOSAFT") or header_row.get("NMDOC")).upper() or "FT"
        serie = _safe_text(header_row.get("SERIE"))
        fno = int(_to_decimal(header_row.get("FNO"), "0"))
        invoice_no = f"{doc_type} {serie}/{fno}" if serie else f"{doc_type} {fno}"
        customer_id = _customer_id_from_doc(header_row)

        _append_text(invoice_el, "InvoiceNo", invoice_no)
        _append_text(invoice_el, "ATCUD", header_row.get("ATCUD"))

        document_status = ET.SubElement(invoice_el, _ns("DocumentStatus"))
        _append_text(document_status, "InvoiceStatus", "A" if int(_to_decimal(header_row.get("ANULADA"), "0")) == 1 else "N")
        _append_text(document_status, "InvoiceStatusDate", _fmt_datetime(header_row.get("ANULDATA") or header_row.get("DTAlteracao") or header_row.get("DTCriacao")))
        _append_text(document_status, "SourceID", _safe_text(header_row.get("USERALTERACAO") or header_row.get("USERCRIACAO") or "SYSTEM"))
        _append_text(document_status, "SourceBilling", "P")

        _append_text(invoice_el, "Hash", header_row.get("HASH"))
        _append_text(invoice_el, "HashControl", _safe_text(header_row.get("HASHVER") or header_row.get("KEYID") or "1"))
        _append_text(invoice_el, "Period", f"{int(_fmt_date(header_row.get('FDATA'))[5:7] or '0')}")
        _append_text(invoice_el, "InvoiceDate", _fmt_date(header_row.get("FDATA")))
        _append_text(invoice_el, "InvoiceType", doc_type)

        special_regimes = ET.SubElement(invoice_el, _ns("SpecialRegimes"))
        _append_text(special_regimes, "SelfBillingIndicator", "0")
        _append_text(special_regimes, "CashVATSchemeIndicator", "0")
        _append_text(special_regimes, "ThirdPartiesBillingIndicator", "0")

        _append_text(invoice_el, "SourceID", _safe_text(header_row.get("USERCRIACAO") or "SYSTEM"))
        _append_text(invoice_el, "SystemEntryDate", _fmt_datetime(header_row.get("DTCriacao") or header_row.get("DTAlteracao")))
        _append_text(invoice_el, "CustomerID", customer_id)

        line_number = 0
        for line in dataset["lines_by_doc"].get(_safe_text(header_row.get("FTSTAMP")), []):
            line_number += 1
            line_el = ET.SubElement(invoice_el, _ns("Line"))
            product_code = _product_code_no_warning(line)
            quantity = _to_decimal(line.get("QTT"), "0").copy_abs()
            unit_price = _line_unit_price(line)
            net_amount = _to_decimal(line.get("ETILIQUIDO"), "0").copy_abs()
            tax_percentage = _to_decimal(line.get("IVA"), "0").quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            _append_text(line_el, "LineNumber", str(line_number))
            _append_text(line_el, "ProductCode", product_code)
            _append_text(line_el, "ProductDescription", _safe_text(line.get("DESIGN"), "Linha faturação"))
            _append_text(line_el, "Quantity", format(quantity, "f"))
            _append_text(line_el, "UnitOfMeasure", _safe_text(line.get("UNIDADE"), "UN"))
            _append_text(line_el, "UnitPrice", _decimal_6((unit_price or Decimal("0.000000")).copy_abs()))
            _append_text(line_el, "TaxPointDate", _fmt_date(header_row.get("FDATA")))
            _append_text(line_el, "Description", _safe_text(line.get("DESIGN"), "Linha faturação"))
            if doc_type == "NC":
                _append_text(line_el, "CreditAmount", _money(net_amount))
            else:
                _append_text(line_el, "DebitAmount", _money(net_amount))

            tax_el = ET.SubElement(line_el, _ns("Tax"))
            _append_text(tax_el, "TaxType", "IVA")
            _append_text(tax_el, "TaxCountryRegion", "PT")
            _append_text(tax_el, "TaxCode", _tax_code_from_percentage(tax_percentage))
            _append_text(tax_el, "TaxPercentage", _money(tax_percentage))

        totals_el = ET.SubElement(invoice_el, _ns("DocumentTotals"))
        _append_text(totals_el, "TaxPayable", _money(header_row.get("ETTIVA")))
        _append_text(totals_el, "NetTotal", _money(header_row.get("ETTILIQ")))
        _append_text(totals_el, "GrossTotal", _money(header_row.get("ETOTAL")))

    return root


def generate_saft_sales_xml(session, filters: dict[str, Any] | None) -> tuple[str, bytes, dict[str, Any]]:
    dataset = _build_dataset(session, filters or {})
    root = _build_xml_tree(dataset)
    tree = ET.ElementTree(root)
    try:
        ET.indent(tree, space="  ")
    except AttributeError:
        pass
    buffer = BytesIO()
    tree.write(buffer, encoding="utf-8", xml_declaration=True)
    filename = f"SAFT_VENDAS_{dataset['filters']['dt_ini'].isoformat()}_{dataset['filters']['dt_fim'].isoformat()}.xml"
    return filename, buffer.getvalue(), {
        "summary": dataset["summary"],
        "warnings": dataset["warnings"],
    }
