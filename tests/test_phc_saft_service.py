import unittest
from collections import OrderedDict
from datetime import date, datetime
from decimal import Decimal
from xml.etree import ElementTree as ET

from services.phc_saft_service import SAFT_NS, _allocate_line_amounts, _build_xml


class PhcSaftServiceTests(unittest.TestCase):
    def test_allocates_invoice_net_total_like_phc_export(self):
        document = {"NET_TOTAL": Decimal("674.53")}
        lines = [
            {"LINE_WEIGHT": Decimal("675"), "QUANTITY": Decimal("1")},
            {"LINE_WEIGHT": Decimal("40"), "QUANTITY": Decimal("1")},
        ]

        _allocate_line_amounts(document, lines)

        self.assertEqual(lines[0]["SAFT_AMOUNT"], Decimal("636.794056"))
        self.assertEqual(lines[1]["SAFT_AMOUNT"], Decimal("37.735944"))
        self.assertEqual(sum(line["SAFT_AMOUNT"] for line in lines), Decimal("674.530000"))

    def test_builds_phc_shaped_windows_1252_xml(self):
        document = {
            "INVOICE_NO": "FR 2026A3/1",
            "ATCUD": "J6SVFK9W-1",
            "ANULADO": 0,
            "CREATED_DATE": datetime(2026, 7, 21),
            "CREATED_TIME": "09:53:06",
            "CREATED_BY": "Administrador de Sistema",
            "DOCUMENT_HASH": "signed-hash",
            "HASH_CONTROL": "1",
            "FDATA": datetime(2026, 7, 20),
            "INVOICE_TYPE": "FR",
            "CUSTOMER_ID": "CUSTOMER-1",
            "TAX_POINT_DATE": datetime(2026, 7, 21),
            "TAX_TOTAL": Decimal("40.47"),
            "NET_TOTAL": Decimal("674.53"),
            "GROSS_TOTAL": Decimal("715.00"),
            "LINES": [
                {
                    "PRODUCT_CODE": "ESTADIA",
                    "PRODUCT_DESCRIPTION": "ESTADIA",
                    "DESCRIPTION": "Estadia de 25.06.2026 a 04.07.2026 -(HMRKZ8RP9C)",
                    "QUANTITY": Decimal("1"),
                    "UNIT_OF_MEASURE": "",
                    "SAFT_UNIT_PRICE": Decimal("636.794056"),
                    "SAFT_AMOUNT": Decimal("636.794056"),
                    "TAX_PERCENTAGE": Decimal("6"),
                },
                {
                    "PRODUCT_CODE": "LIMPEZA",
                    "PRODUCT_DESCRIPTION": "TAXA DE LIMPEZA",
                    "DESCRIPTION": "Taxa de Limpeza",
                    "QUANTITY": Decimal("1"),
                    "UNIT_OF_MEASURE": "",
                    "SAFT_UNIT_PRICE": Decimal("37.735944"),
                    "SAFT_AMOUNT": Decimal("37.735944"),
                    "TAX_PERCENTAGE": Decimal("6"),
                },
            ],
        }
        dataset = {
            "company": {
                "TAX_ID": "167508032",
                "COMPANY_NAME": "CARLA CAPELAS",
                "ADDRESS_DETAIL": "Praça Coronel Pacheco, 77 - 4º Traseiras",
                "CITY": "Porto",
                "POSTAL_CODE": "4050-453",
                "COUNTRY": "PT",
                "EAC_CODE": "55201",
            },
            "documents": [document],
            "customers": OrderedDict({
                "CUSTOMER-1": {
                    "CustomerID": "CUSTOMER-1",
                    "AccountID": "Desconhecido",
                    "CustomerTaxID": "999999990",
                    "CompanyName": "Consumidor Final",
                    "AddressDetail": "Desconhecido",
                    "City": "Desconhecido",
                    "PostalCode": "0000-000",
                    "Country": "PT",
                }
            }),
            "start_date": date(2026, 7, 1),
            "end_date": date(2026, 7, 31),
            "created_on": date(2026, 7, 31),
            "total_debit": Decimal("0"),
            "total_credit": Decimal("674.53"),
        }

        xml_bytes = _build_xml(dataset)
        self.assertTrue(xml_bytes.startswith(b'<?xml version="1.0" encoding="Windows-1252" standalone="yes"?>'))
        root = ET.fromstring(xml_bytes)
        ns = {"s": SAFT_NS}
        self.assertEqual(root.findtext("s:Header/s:ProductID", namespaces=ns), "CS Advanced 202601/PHC")
        self.assertEqual(root.findtext(".//s:Invoice/s:InvoiceNo", namespaces=ns), "FR 2026A3/1")
        self.assertEqual(root.findtext(".//s:Invoice/s:ATCUD", namespaces=ns), "J6SVFK9W-1")
        self.assertEqual(root.findtext(".//s:Line/s:UnitPrice", namespaces=ns), "636.794056")
        self.assertEqual(root.findtext(".//s:WorkingDocuments/s:NumberOfEntries", namespaces=ns), "0")


if __name__ == "__main__":
    unittest.main()
