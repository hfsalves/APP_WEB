from __future__ import annotations

import os
from collections import OrderedDict, defaultdict
from datetime import date, datetime, time
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from typing import Any
from xml.etree import ElementTree as ET


SAFT_NS = "urn:OECD:StandardAuditFile-Tax:PT_1.04_01"
SAFT_VERSION = "1.04_01"
MONEY_2 = Decimal("0.01")
MONEY_6 = Decimal("0.000001")


class PhcSaftError(ValueError):
    pass


def _text(value: Any, fallback: str = "") -> str:
    clean = str(value or "").strip()
    return clean or fallback


def _decimal(value: Any, fallback: str = "0") -> Decimal:
    try:
        return Decimal(str(value if value not in (None, "") else fallback))
    except Exception:
        return Decimal(fallback)


def _date_value(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = _text(value)
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw).date()
    except Exception:
        return None


def _real_date(value: Any) -> date | None:
    parsed = _date_value(value)
    return parsed if parsed and parsed.year > 1900 else None


def _date_iso(value: Any) -> str:
    parsed = _real_date(value)
    return parsed.isoformat() if parsed else ""


def _datetime_iso(date_value: Any, hour_value: Any = "") -> str:
    parsed_date = _real_date(date_value)
    if not parsed_date:
        return ""
    raw_hour = _text(hour_value).replace(".", ":")
    parsed_time = time(0, 0, 0)
    for fmt in ("%H:%M:%S", "%H:%M", "%H%M%S", "%H%M"):
        try:
            parsed_time = datetime.strptime(raw_hour, fmt).time()
            break
        except Exception:
            pass
    return datetime.combine(parsed_date, parsed_time).isoformat(timespec="seconds")


def _money_2(value: Any) -> str:
    return format(abs(_decimal(value)).quantize(MONEY_2, rounding=ROUND_HALF_UP), ".2f")


def _money_6(value: Any) -> str:
    return format(abs(_decimal(value)).quantize(MONEY_6, rounding=ROUND_HALF_UP), ".6f")


def _quantity(value: Any) -> str:
    return format(abs(_decimal(value)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP), ".3f")


def _row_dicts(cursor) -> list[dict[str, Any]]:
    columns = [str(item[0] or "").upper() for item in cursor.description or []]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _fetch_all(connection, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    cursor = connection.cursor()
    cursor.execute(sql, params)
    return _row_dicts(cursor)


def _fetch_one(connection, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any]:
    rows = _fetch_all(connection, sql, params)
    return rows[0] if rows else {}


def _load_company(connection) -> dict[str, Any]:
    row = _fetch_one(connection, """
        SELECT TOP 1
            LTRIM(RTRIM(ISNULL(E1.NOMECOMP, ''))) AS COMPANY_NAME,
            LTRIM(RTRIM(ISNULL(E1.MORADA, ''))) AS ADDRESS_DETAIL,
            LTRIM(RTRIM(ISNULL(E1.LOCAL, ''))) AS CITY,
            LTRIM(RTRIM(ISNULL(E1.CODPOST, ''))) AS POSTAL_CODE,
            LTRIM(RTRIM(ISNULL(E1.CODPAIS, ''))) AS COUNTRY,
            LTRIM(RTRIM(ISNULL(E1.NCONT, ''))) AS TAX_ID,
            LTRIM(RTRIM(ISNULL(E1.CAE, ''))) AS EAC_CODE
        FROM dbo.E1 AS E1
        ORDER BY ISNULL(E1.ESTAB, 0), E1.E1STAMP
    """)
    if not row:
        raise PhcSaftError("A base PHC não tem ficha da empresa em E1.")
    if not _text(row.get("COMPANY_NAME")):
        raise PhcSaftError("A ficha E1 não tem o nome da empresa definido.")
    tax_id = "".join(char for char in _text(row.get("TAX_ID")) if char.isdigit())
    if len(tax_id) != 9:
        raise PhcSaftError("A ficha E1 não tem um NIF português válido.")
    row["TAX_ID"] = tax_id
    return row


def _load_documents(connection, start_date: date, end_date: date) -> list[dict[str, Any]]:
    return _fetch_all(connection, """
        SELECT
            LTRIM(RTRIM(FT.FTSTAMP)) AS FTSTAMP,
            LTRIM(RTRIM(ISNULL(FT.NMDOC, ''))) AS NMDOC,
            ISNULL(FT.FNO, 0) AS FNO,
            ISNULL(FT.NDOC, 0) AS NDOC,
            ISNULL(FT.FTANO, 0) AS FTANO,
            FT.FDATA,
            ISNULL(FT.NO, 0) AS NO,
            ISNULL(FT.ESTAB, 0) AS ESTAB,
            ISNULL(FT.ANULADO, 0) AS ANULADO,
            ISNULL(FT.ETTILIQ, 0) AS NET_TOTAL,
            ISNULL(FT.ETTIVA, 0) AS TAX_TOTAL,
            ISNULL(FT.ETOTAL, 0) AS GROSS_TOTAL,
            LTRIM(RTRIM(ISNULL(FT.OUSRINIS, ''))) AS CREATED_BY,
            FT.OUSRDATA AS CREATED_DATE,
            LTRIM(RTRIM(ISNULL(FT.OUSRHORA, ''))) AS CREATED_TIME,
            LTRIM(RTRIM(ISNULL(FT2.TIPOSAFT, ''))) AS INVOICE_TYPE,
            LTRIM(RTRIM(ISNULL(FT2.ASSINATURA, ''))) AS DOCUMENT_HASH,
            LTRIM(RTRIM(ISNULL(FT2.VERSAOCHAVE, ''))) AS HASH_CONTROL,
            LTRIM(RTRIM(ISNULL(FT3.ATCUD, ''))) AS ATCUD,
            FT3.TAXPOINTDT AS TAX_POINT_DATE,
            LTRIM(RTRIM(ISNULL(FT3.MOTANUL, ''))) AS CANCEL_REASON,
            LTRIM(RTRIM(ISNULL(FT3.ANULINIS, ''))) AS CANCELLED_BY,
            FT3.ANULDATA AS CANCELLED_DATE,
            LTRIM(RTRIM(ISNULL(FT3.ANULHORA, ''))) AS CANCELLED_TIME,
            LTRIM(RTRIM(ISNULL(CL.CLSTAMP, ''))) AS CUSTOMER_ID,
            LTRIM(RTRIM(ISNULL(CL.NOME, ''))) AS CUSTOMER_NAME,
            LTRIM(RTRIM(ISNULL(CL.NCONT, ''))) AS CUSTOMER_TAX_ID,
            LTRIM(RTRIM(ISNULL(CL.MORADA, ''))) AS CUSTOMER_ADDRESS,
            LTRIM(RTRIM(ISNULL(CL.LOCAL, ''))) AS CUSTOMER_CITY,
            LTRIM(RTRIM(ISNULL(CL.CODPOST, ''))) AS CUSTOMER_POSTAL_CODE,
            LTRIM(RTRIM(ISNULL(FT3.CODPAIS, ''))) AS CUSTOMER_COUNTRY,
            LTRIM(RTRIM(ISNULL(SERIE.IDSERIEPHC, ''))) AS INVOICE_SERIES,
            LTRIM(RTRIM(ISNULL(SERIE.CODSERIEAT, ''))) AS SERIES_AT_CODE
        FROM dbo.FT AS FT
        INNER JOIN dbo.FT2 AS FT2
          ON FT2.FT2STAMP = FT.FTSTAMP
        LEFT JOIN dbo.FT3 AS FT3
          ON FT3.FT3STAMP = FT.FTSTAMP
        LEFT JOIN dbo.CL AS CL
          ON CL.NO = FT.NO
         AND ISNULL(CL.ESTAB, 0) = ISNULL(FT.ESTAB, 0)
        OUTER APPLY (
            SELECT TOP 1 S.IDSERIEPHC, S.CODSERIEAT
            FROM dbo.SERIEAT AS S
            WHERE UPPER(LTRIM(RTRIM(ISNULL(S.ORIGEM, '')))) = 'FT'
              AND ISNULL(S.ANO, 0) = ISNULL(FT.FTANO, 0)
              AND ISNULL(S.NUMERO, 0) = ISNULL(FT.NDOC, 0)
            ORDER BY ISNULL(S.VALIDADAPORWS, 0) DESC, S.DATAINICIO DESC, S.SERIEATSTAMP DESC
        ) AS SERIE
        WHERE CAST(FT.FDATA AS date) BETWEEN ? AND ?
          AND ISNULL(FT.FNO, 0) > 0
          AND UPPER(LTRIM(RTRIM(ISNULL(FT2.TIPOSAFT, '')))) IN ('FT', 'FS', 'FR', 'NC')
        ORDER BY CAST(FT.FDATA AS date), ISNULL(FT.NDOC, 0), ISNULL(FT.FNO, 0), FT.FTSTAMP
    """, (start_date, end_date))


def _load_lines(connection, start_date: date, end_date: date) -> dict[str, list[dict[str, Any]]]:
    rows = _fetch_all(connection, """
        SELECT
            LTRIM(RTRIM(FI.FTSTAMP)) AS FTSTAMP,
            LTRIM(RTRIM(FI.FISTAMP)) AS FISTAMP,
            ISNULL(FI.LORDEM, 0) AS LINE_ORDER,
            LTRIM(RTRIM(ISNULL(FI.REF, ''))) AS PRODUCT_CODE,
            LTRIM(RTRIM(ISNULL(ST.DESIGN, ISNULL(FI.REF, '')))) AS PRODUCT_DESCRIPTION,
            LTRIM(RTRIM(ISNULL(FI.DESIGN, ''))) AS DESCRIPTION,
            ISNULL(FI.QTT, 0) AS QUANTITY,
            LTRIM(RTRIM(ISNULL(FI.UNIDADE, ''))) AS UNIT_OF_MEASURE,
            ISNULL(FI.IVA, 0) AS TAX_PERCENTAGE,
            ISNULL(FI.IVAINCL, 0) AS VAT_INCLUDED,
            ISNULL(FI.EPV, 0) AS UNIT_GROSS,
            ISNULL(FI.ETILIQUIDO, 0) AS LINE_WEIGHT,
            LTRIM(RTRIM(ISNULL(FI.CODMOTISEIMP, ''))) AS EXEMPTION_CODE_FI,
            LTRIM(RTRIM(ISNULL(FI.MOTISEIMP, ''))) AS EXEMPTION_REASON_FI,
            LTRIM(RTRIM(ISNULL(FI2.CODISP, ''))) AS EXEMPTION_CODE_FI2,
            LTRIM(RTRIM(ISNULL(FI2.DESIGNISP, ''))) AS EXEMPTION_REASON_FI2,
            LTRIM(RTRIM(ISNULL(FI2.ORIGINATINGON, ''))) AS ORIGINATING_ON,
            FI2.ORDERDATE AS ORDER_DATE,
            LTRIM(RTRIM(ISNULL(FI2.REFRETIF, ''))) AS REFERENCE,
            LTRIM(RTRIM(ISNULL(FI2.MOTRETIF, ''))) AS REFERENCE_REASON
        FROM dbo.FI AS FI
        INNER JOIN dbo.FT AS FT
          ON FT.FTSTAMP = FI.FTSTAMP
        LEFT JOIN dbo.FI2 AS FI2
          ON FI2.FI2STAMP = FI.FISTAMP
        LEFT JOIN dbo.ST AS ST
          ON LTRIM(RTRIM(ISNULL(ST.REF, ''))) = LTRIM(RTRIM(ISNULL(FI.REF, '')))
        WHERE CAST(FT.FDATA AS date) BETWEEN ? AND ?
          AND ISNULL(FT.FNO, 0) > 0
        ORDER BY CAST(FT.FDATA AS date), ISNULL(FT.FNO, 0), ISNULL(FI.LORDEM, 0), FI.FISTAMP
    """, (start_date, end_date))
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[_text(row.get("FTSTAMP"))].append(row)
    return grouped


def _load_tax_totals(connection, start_date: date, end_date: date) -> dict[str, list[dict[str, Any]]]:
    rows = _fetch_all(connection, """
        SELECT
            LTRIM(RTRIM(FTT.FTSTAMP)) AS FTSTAMP,
            ISNULL(FTT.TAXA, 0) AS TAX_PERCENTAGE,
            ISNULL(FTT.EBASEINC, 0) AS TAX_BASE,
            ISNULL(FTT.EVALOR, 0) AS TAX_VALUE
        FROM dbo.FTT AS FTT
        INNER JOIN dbo.FT AS FT
          ON FT.FTSTAMP = FTT.FTSTAMP
        WHERE CAST(FT.FDATA AS date) BETWEEN ? AND ?
          AND ISNULL(FT.FNO, 0) > 0
        ORDER BY FT.FTSTAMP, FTT.CODIGO
    """, (start_date, end_date))
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[_text(row.get("FTSTAMP"))].append(row)
    return grouped


def _tax_code(percentage: Decimal) -> str:
    rate = percentage.quantize(MONEY_2, rounding=ROUND_HALF_UP)
    if rate == Decimal("23.00"):
        return "NOR"
    if rate == Decimal("13.00"):
        return "INT"
    if rate == Decimal("6.00"):
        return "RED"
    if rate == Decimal("0.00"):
        return "ISE"
    return "OUT"


def _allocate_line_amounts(document: dict[str, Any], lines: list[dict[str, Any]]) -> None:
    total_net = abs(_decimal(document.get("NET_TOTAL"))).quantize(MONEY_6, rounding=ROUND_HALF_UP)
    weights: list[Decimal] = []
    for line in lines:
        weight = abs(_decimal(line.get("LINE_WEIGHT")))
        if weight == 0:
            weight = abs(_decimal(line.get("QUANTITY")) * _decimal(line.get("UNIT_GROSS")))
        weights.append(weight)
    weight_total = sum(weights, Decimal("0"))
    allocated = Decimal("0")
    for index, line in enumerate(lines):
        if index == len(lines) - 1:
            line_net = total_net - allocated
        elif weight_total:
            line_net = (total_net * weights[index] / weight_total).quantize(MONEY_6, rounding=ROUND_HALF_UP)
            allocated += line_net
        else:
            line_net = Decimal("0")
        quantity = abs(_decimal(line.get("QUANTITY")))
        line["SAFT_AMOUNT"] = line_net
        line["SAFT_UNIT_PRICE"] = (
            (line_net / quantity).quantize(MONEY_6, rounding=ROUND_HALF_UP)
            if quantity else Decimal("0")
        )


def _validate_document(document: dict[str, Any], lines: list[dict[str, Any]], taxes: list[dict[str, Any]]) -> None:
    label = f"{_text(document.get('NMDOC'), 'Documento')} {int(_decimal(document.get('FNO')))}"
    required = {
        "INVOICE_TYPE": "tipo SAF-T",
        "INVOICE_SERIES": "série AT",
        "ATCUD": "ATCUD",
        "DOCUMENT_HASH": "assinatura",
        "HASH_CONTROL": "versão da chave",
        "CUSTOMER_ID": "cliente",
    }
    missing = [description for field, description in required.items() if not _text(document.get(field))]
    if missing:
        raise PhcSaftError(f"{label}: faltam {', '.join(missing)} no PHC.")
    if not lines:
        raise PhcSaftError(f"{label}: documento sem linhas em FI.")
    if taxes:
        ftt_tax = sum((abs(_decimal(row.get("TAX_VALUE"))) for row in taxes), Decimal("0")).quantize(MONEY_2, rounding=ROUND_HALF_UP)
        ft_tax = abs(_decimal(document.get("TAX_TOTAL"))).quantize(MONEY_2, rounding=ROUND_HALF_UP)
        if ftt_tax != ft_tax:
            raise PhcSaftError(f"{label}: o IVA de FT ({ft_tax}) não coincide com FTT ({ftt_tax}).")
    for line in lines:
        if not _text(line.get("PRODUCT_CODE")):
            raise PhcSaftError(f"{label}: existe uma linha FI sem referência.")
        if _decimal(line.get("TAX_PERCENTAGE")) == 0:
            code = _text(line.get("EXEMPTION_CODE_FI2") or line.get("EXEMPTION_CODE_FI"))
            reason = _text(line.get("EXEMPTION_REASON_FI2") or line.get("EXEMPTION_REASON_FI"))
            if not code or not reason:
                raise PhcSaftError(f"{label}: linha isenta sem código e motivo de isenção.")


def _prepare_dataset(connection, start_date: date, end_date: date, created_on: date) -> dict[str, Any]:
    if start_date.year != end_date.year or start_date > end_date:
        raise PhcSaftError("O período SAF-T tem de pertencer a um único ano fiscal.")
    company = _load_company(connection)
    documents = _load_documents(connection, start_date, end_date)
    lines_by_document = _load_lines(connection, start_date, end_date)
    taxes_by_document = _load_tax_totals(connection, start_date, end_date)
    customers: OrderedDict[str, dict[str, Any]] = OrderedDict()
    total_debit = Decimal("0")
    total_credit = Decimal("0")

    for document in documents:
        stamp = _text(document.get("FTSTAMP"))
        lines = lines_by_document.get(stamp, [])
        _validate_document(document, lines, taxes_by_document.get(stamp, []))
        _allocate_line_amounts(document, lines)
        document["LINES"] = lines
        document["INVOICE_NO"] = f"{_text(document.get('INVOICE_SERIES'))}/{int(_decimal(document.get('FNO')))}"
        doc_net = sum((_decimal(line.get("SAFT_AMOUNT")) for line in lines), Decimal("0"))
        if _text(document.get("INVOICE_TYPE")).upper() == "NC":
            total_debit += doc_net
        else:
            total_credit += doc_net

        customer_id = _text(document.get("CUSTOMER_ID"))
        if customer_id not in customers:
            customer_tax_id = _text(document.get("CUSTOMER_TAX_ID"), "999999990")
            generic_customer = "".join(char for char in customer_tax_id if char.isdigit()) == "999999990"
            customers[customer_id] = {
                "CustomerID": customer_id,
                "AccountID": "Desconhecido",
                "CustomerTaxID": customer_tax_id,
                "CompanyName": "Consumidor Final" if generic_customer else _text(document.get("CUSTOMER_NAME"), "Desconhecido"),
                "AddressDetail": _text(document.get("CUSTOMER_ADDRESS"), "Desconhecido"),
                "City": _text(document.get("CUSTOMER_CITY"), "Desconhecido"),
                "PostalCode": _text(document.get("CUSTOMER_POSTAL_CODE"), "0000-000"),
                "Country": _text(document.get("CUSTOMER_COUNTRY"), "PT").upper()[:2],
            }

    return {
        "company": company,
        "documents": documents,
        "customers": customers,
        "start_date": start_date,
        "end_date": end_date,
        "created_on": created_on,
        "total_debit": total_debit.quantize(MONEY_6, rounding=ROUND_HALF_UP),
        "total_credit": total_credit.quantize(MONEY_6, rounding=ROUND_HALF_UP),
    }


def _ns(tag: str) -> str:
    return f"{{{SAFT_NS}}}{tag}"


def _append(parent: ET.Element, tag: str, value: Any) -> ET.Element:
    text_value = _text(value)
    if not text_value:
        raise PhcSaftError(f"O campo SAF-T {tag} ficou vazio.")
    element = ET.SubElement(parent, _ns(tag))
    element.text = text_value
    return element


def _append_zero_summary(parent: ET.Element) -> None:
    _append(parent, "NumberOfEntries", "0")
    _append(parent, "TotalDebit", "0.000000")
    _append(parent, "TotalCredit", "0.000000")


def _build_xml(dataset: dict[str, Any]) -> bytes:
    ET.register_namespace("", SAFT_NS)
    root = ET.Element(_ns("AuditFile"))
    company = dataset["company"]

    header = ET.SubElement(root, _ns("Header"))
    _append(header, "AuditFileVersion", SAFT_VERSION)
    _append(header, "CompanyID", company["TAX_ID"])
    _append(header, "TaxRegistrationNumber", company["TAX_ID"])
    _append(header, "TaxAccountingBasis", "P")
    _append(header, "CompanyName", company["COMPANY_NAME"])
    _append(header, "BusinessName", company["COMPANY_NAME"])
    address = ET.SubElement(header, _ns("CompanyAddress"))
    _append(address, "AddressDetail", _text(company.get("ADDRESS_DETAIL"), "Desconhecido"))
    _append(address, "City", _text(company.get("CITY"), "Desconhecido"))
    _append(address, "PostalCode", _text(company.get("POSTAL_CODE"), "0000-000"))
    _append(address, "Country", _text(company.get("COUNTRY"), "PT").upper()[:2])
    _append(header, "FiscalYear", str(dataset["start_date"].year))
    _append(header, "StartDate", dataset["start_date"].isoformat())
    _append(header, "EndDate", dataset["end_date"].isoformat())
    _append(header, "CurrencyCode", "EUR")
    _append(header, "DateCreated", dataset["created_on"].isoformat())
    _append(header, "TaxEntity", "Global")
    _append(header, "ProductCompanyTaxID", os.environ.get("PHC_SAFT_PRODUCT_COMPANY_TAX_ID", "502199326"))
    _append(header, "SoftwareCertificateNumber", os.environ.get("PHC_SAFT_SOFTWARE_CERTIFICATE", "6"))
    _append(header, "ProductID", os.environ.get("PHC_SAFT_PRODUCT_ID", "CS Advanced 202601/PHC"))
    _append(header, "ProductVersion", os.environ.get("PHC_SAFT_PRODUCT_VERSION", "2026.01.00.122"))

    master_files = ET.SubElement(root, _ns("MasterFiles"))
    for customer in dataset["customers"].values():
        customer_el = ET.SubElement(master_files, _ns("Customer"))
        _append(customer_el, "CustomerID", customer["CustomerID"])
        _append(customer_el, "AccountID", customer["AccountID"])
        _append(customer_el, "CustomerTaxID", customer["CustomerTaxID"])
        _append(customer_el, "CompanyName", customer["CompanyName"])
        billing_address = ET.SubElement(customer_el, _ns("BillingAddress"))
        _append(billing_address, "AddressDetail", customer["AddressDetail"])
        _append(billing_address, "City", customer["City"])
        _append(billing_address, "PostalCode", customer["PostalCode"])
        _append(billing_address, "Country", customer["Country"])
        _append(customer_el, "SelfBillingIndicator", "0")

    source_documents = ET.SubElement(root, _ns("SourceDocuments"))
    sales_invoices = ET.SubElement(source_documents, _ns("SalesInvoices"))
    _append(sales_invoices, "NumberOfEntries", str(len(dataset["documents"])))
    _append(sales_invoices, "TotalDebit", _money_6(dataset["total_debit"]))
    _append(sales_invoices, "TotalCredit", _money_6(dataset["total_credit"]))

    for document in dataset["documents"]:
        invoice = ET.SubElement(sales_invoices, _ns("Invoice"))
        _append(invoice, "InvoiceNo", document["INVOICE_NO"])
        _append(invoice, "ATCUD", document["ATCUD"])

        cancelled = bool(document.get("ANULADO"))
        status = ET.SubElement(invoice, _ns("DocumentStatus"))
        _append(status, "InvoiceStatus", "A" if cancelled else "N")
        status_date = (
            _datetime_iso(document.get("CANCELLED_DATE"), document.get("CANCELLED_TIME"))
            if cancelled else _datetime_iso(document.get("CREATED_DATE"), document.get("CREATED_TIME"))
        )
        _append(status, "InvoiceStatusDate", status_date)
        if cancelled and _text(document.get("CANCEL_REASON")):
            _append(status, "Reason", document["CANCEL_REASON"])
        status_user = document.get("CANCELLED_BY") if cancelled else document.get("CREATED_BY")
        _append(status, "SourceID", _text(status_user, "Administrador de Sistema"))
        _append(status, "SourceBilling", "P")

        _append(invoice, "Hash", document["DOCUMENT_HASH"])
        _append(invoice, "HashControl", document["HASH_CONTROL"])
        _append(invoice, "InvoiceDate", _date_iso(document["FDATA"]))
        invoice_type = _text(document["INVOICE_TYPE"]).upper()
        _append(invoice, "InvoiceType", invoice_type)
        regimes = ET.SubElement(invoice, _ns("SpecialRegimes"))
        _append(regimes, "SelfBillingIndicator", "0")
        _append(regimes, "CashVATSchemeIndicator", "0")
        _append(regimes, "ThirdPartiesBillingIndicator", "0")
        _append(invoice, "SourceID", _text(document.get("CREATED_BY"), "Administrador de Sistema"))
        if _text(company.get("EAC_CODE")):
            _append(invoice, "EACCode", company["EAC_CODE"])
        _append(invoice, "SystemEntryDate", _datetime_iso(document.get("CREATED_DATE"), document.get("CREATED_TIME")))
        _append(invoice, "CustomerID", document["CUSTOMER_ID"])

        for index, line in enumerate(document["LINES"], start=1):
            line_el = ET.SubElement(invoice, _ns("Line"))
            _append(line_el, "LineNumber", str(index))
            if _text(line.get("ORIGINATING_ON")) or _real_date(line.get("ORDER_DATE")):
                order_refs = ET.SubElement(line_el, _ns("OrderReferences"))
                if _text(line.get("ORIGINATING_ON")):
                    _append(order_refs, "OriginatingON", line["ORIGINATING_ON"])
                if _real_date(line.get("ORDER_DATE")):
                    _append(order_refs, "OrderDate", _date_iso(line["ORDER_DATE"]))
            _append(line_el, "ProductCode", line["PRODUCT_CODE"])
            _append(line_el, "ProductDescription", _text(line.get("PRODUCT_DESCRIPTION"), line["PRODUCT_CODE"]))
            _append(line_el, "Quantity", _quantity(line["QUANTITY"]))
            _append(line_el, "UnitOfMeasure", _text(line.get("UNIT_OF_MEASURE"), "Unidade"))
            _append(line_el, "UnitPrice", _money_6(line["SAFT_UNIT_PRICE"]))
            tax_point = _date_iso(document.get("TAX_POINT_DATE")) or _date_iso(document.get("FDATA"))
            _append(line_el, "TaxPointDate", tax_point)
            if _text(line.get("REFERENCE")) or _text(line.get("REFERENCE_REASON")):
                references = ET.SubElement(line_el, _ns("References"))
                if _text(line.get("REFERENCE")):
                    _append(references, "Reference", line["REFERENCE"])
                if _text(line.get("REFERENCE_REASON")):
                    _append(references, "Reason", line["REFERENCE_REASON"])
            _append(line_el, "Description", _text(line.get("DESCRIPTION"), line["PRODUCT_CODE"]))
            amount_tag = "DebitAmount" if invoice_type == "NC" else "CreditAmount"
            _append(line_el, amount_tag, _money_6(line["SAFT_AMOUNT"]))
            tax_percentage = _decimal(line.get("TAX_PERCENTAGE"))
            tax = ET.SubElement(line_el, _ns("Tax"))
            _append(tax, "TaxType", "IVA")
            _append(tax, "TaxCountryRegion", "PT")
            _append(tax, "TaxCode", _tax_code(tax_percentage))
            _append(tax, "TaxPercentage", _money_6(tax_percentage))
            if tax_percentage == 0:
                exemption_reason = _text(line.get("EXEMPTION_REASON_FI2") or line.get("EXEMPTION_REASON_FI"))
                exemption_code = _text(line.get("EXEMPTION_CODE_FI2") or line.get("EXEMPTION_CODE_FI"))
                _append(line_el, "TaxExemptionReason", exemption_reason)
                _append(line_el, "TaxExemptionCode", exemption_code)

        totals = ET.SubElement(invoice, _ns("DocumentTotals"))
        _append(totals, "TaxPayable", _money_6(document["TAX_TOTAL"]))
        _append(totals, "NetTotal", _money_6(document["NET_TOTAL"]))
        _append(totals, "GrossTotal", _money_2(document["GROSS_TOTAL"]))

    working_documents = ET.SubElement(source_documents, _ns("WorkingDocuments"))
    _append_zero_summary(working_documents)

    tree = ET.ElementTree(root)
    try:
        ET.indent(tree, space="  ")
    except AttributeError:
        pass
    buffer = BytesIO()
    tree.write(buffer, encoding="windows-1252", xml_declaration=False, short_empty_elements=True)
    declaration = b'<?xml version="1.0" encoding="Windows-1252" standalone="yes"?>\r\n'
    return declaration + buffer.getvalue().replace(b"\n", b"\r\n")


def generate_phc_monthly_saft(
    connection,
    start_date: date,
    end_date: date,
    *,
    created_on: date | None = None,
) -> tuple[str, bytes, dict[str, Any]]:
    created_date = created_on or date.today()
    dataset = _prepare_dataset(connection, start_date, end_date, created_date)
    xml_bytes = _build_xml(dataset)
    now = datetime.now()
    filename = f"{dataset['company']['TAX_ID']}{now:%Y%m%d%H%M}.xml"
    return filename, xml_bytes, {
        "documents": len(dataset["documents"]),
        "customers": len(dataset["customers"]),
        "total_debit": _money_6(dataset["total_debit"]),
        "total_credit": _money_6(dataset["total_credit"]),
        "company": dataset["company"]["COMPANY_NAME"],
        "tax_id": dataset["company"]["TAX_ID"],
    }
