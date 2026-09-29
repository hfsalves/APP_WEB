import io
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pypdf import PdfWriter

from services.document_ai_service import (
    _classify_pdf_from_embedded_invoice_xml,
    _classify_structured_invoice_xml,
    classify_document_with_llm,
)


UBL_INVOICE = b'''<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
 xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
 xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:CustomizationID>urn:cen.eu:en16931:2017</cbc:CustomizationID>
  <cbc:ID>FAC-100</cbc:ID><cbc:IssueDate>2026-09-29</cbc:IssueDate>
  <cbc:DueDate>2026-10-29</cbc:DueDate><cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>
  <cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>
  <cac:AccountingSupplierParty><cac:Party>
    <cac:PartyName><cbc:Name>Fornecedor SA</cbc:Name></cac:PartyName>
    <cac:PartyTaxScheme><cbc:CompanyID>FR12345678901</cbc:CompanyID><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:PartyTaxScheme>
  </cac:Party></cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty><cac:Party>
    <cac:PartyLegalEntity><cbc:RegistrationName>HSOLS FRANCE</cbc:RegistrationName></cac:PartyLegalEntity>
    <cac:PartyTaxScheme><cbc:CompanyID>FR46804213593</cbc:CompanyID><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:PartyTaxScheme>
  </cac:Party></cac:AccountingCustomerParty>
  <cac:TaxTotal><cbc:TaxAmount currencyID="EUR">20.00</cbc:TaxAmount>
    <cac:TaxSubtotal><cbc:TaxableAmount currencyID="EUR">100.00</cbc:TaxableAmount><cbc:TaxAmount currencyID="EUR">20.00</cbc:TaxAmount>
      <cac:TaxCategory><cbc:Percent>20</cbc:Percent></cac:TaxCategory>
    </cac:TaxSubtotal>
  </cac:TaxTotal>
  <cac:LegalMonetaryTotal><cbc:LineExtensionAmount currencyID="EUR">100.00</cbc:LineExtensionAmount>
    <cbc:TaxExclusiveAmount currencyID="EUR">100.00</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount currencyID="EUR">120.00</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount currencyID="EUR">120.00</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
  <cac:InvoiceLine><cbc:ID>1</cbc:ID><cbc:InvoicedQuantity unitCode="EA">2</cbc:InvoicedQuantity>
    <cbc:LineExtensionAmount currencyID="EUR">100.00</cbc:LineExtensionAmount>
    <cac:Item><cbc:Name>Servico</cbc:Name><cac:SellersItemIdentification><cbc:ID>ART-1</cbc:ID></cac:SellersItemIdentification>
      <cac:ClassifiedTaxCategory><cbc:Percent>20</cbc:Percent></cac:ClassifiedTaxCategory>
    </cac:Item><cac:Price><cbc:PriceAmount currencyID="EUR">50.00</cbc:PriceAmount></cac:Price>
  </cac:InvoiceLine>
</Invoice>'''


CII_INVOICE = b'''<?xml version="1.0" encoding="UTF-8"?>
<rsm:CrossIndustryInvoice xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
 xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
 xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
 <rsm:ExchangedDocument><ram:ID>CII-1</ram:ID><ram:TypeCode>380</ram:TypeCode>
  <ram:IssueDateTime><udt:DateTimeString format="102">20260929</udt:DateTimeString></ram:IssueDateTime>
 </rsm:ExchangedDocument>
 <rsm:SupplyChainTradeTransaction>
  <ram:IncludedSupplyChainTradeLineItem>
   <ram:SpecifiedTradeProduct><ram:SellerAssignedID>REF-1</ram:SellerAssignedID><ram:Name>Material</ram:Name></ram:SpecifiedTradeProduct>
   <ram:SpecifiedLineTradeAgreement><ram:NetPriceProductTradePrice><ram:ChargeAmount>10.00</ram:ChargeAmount></ram:NetPriceProductTradePrice></ram:SpecifiedLineTradeAgreement>
   <ram:SpecifiedLineTradeDelivery><ram:BilledQuantity unitCode="C62">10</ram:BilledQuantity></ram:SpecifiedLineTradeDelivery>
   <ram:SpecifiedLineTradeSettlement><ram:ApplicableTradeTax><ram:RateApplicablePercent>20</ram:RateApplicablePercent></ram:ApplicableTradeTax>
    <ram:SpecifiedTradeSettlementLineMonetarySummation><ram:LineTotalAmount>100.00</ram:LineTotalAmount></ram:SpecifiedTradeSettlementLineMonetarySummation>
   </ram:SpecifiedLineTradeSettlement>
  </ram:IncludedSupplyChainTradeLineItem>
  <ram:ApplicableHeaderTradeAgreement>
   <ram:SellerTradeParty><ram:Name>Fornecedor CII</ram:Name><ram:SpecifiedTaxRegistration><ram:ID schemeID="VA">FR123</ram:ID></ram:SpecifiedTaxRegistration></ram:SellerTradeParty>
   <ram:BuyerTradeParty><ram:Name>HSOLS France</ram:Name><ram:SpecifiedTaxRegistration><ram:ID schemeID="VA">FR456</ram:ID></ram:SpecifiedTaxRegistration></ram:BuyerTradeParty>
  </ram:ApplicableHeaderTradeAgreement>
  <ram:ApplicableHeaderTradeSettlement><ram:InvoiceCurrencyCode>EUR</ram:InvoiceCurrencyCode>
   <ram:ApplicableTradeTax><ram:CalculatedAmount>20.00</ram:CalculatedAmount><ram:BasisAmount>100.00</ram:BasisAmount><ram:RateApplicablePercent>20</ram:RateApplicablePercent></ram:ApplicableTradeTax>
   <ram:SpecifiedTradeSettlementHeaderMonetarySummation><ram:LineTotalAmount>100.00</ram:LineTotalAmount><ram:TaxBasisTotalAmount>100.00</ram:TaxBasisTotalAmount><ram:TaxTotalAmount>20.00</ram:TaxTotalAmount><ram:GrandTotalAmount>120.00</ram:GrandTotalAmount><ram:DuePayableAmount>120.00</ram:DuePayableAmount></ram:SpecifiedTradeSettlementHeaderMonetarySummation>
  </ram:ApplicableHeaderTradeSettlement>
 </rsm:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoice>'''


def pdf_with_attachment(name, content):
    stream = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.add_attachment(name, content)
    writer.write(stream)
    return stream.getvalue()


class DocumentAiStructuredXmlTests(unittest.TestCase):
    def test_reads_valid_ubl_attachment(self):
        payload = _classify_pdf_from_embedded_invoice_xml(pdf_with_attachment('factur-x.xml', UBL_INVOICE))
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['mode'], 'embedded_xml')
        self.assertEqual(payload['structured_xml']['format'], 'UBL')
        classification = payload['classification']
        self.assertEqual(classification['document_number'], 'FAC-100')
        self.assertEqual(classification['supplier']['tax_id'], 'FR12345678901')
        self.assertEqual(classification['totals']['gross_total'], 120.0)
        self.assertEqual(classification['lines'][0]['source_ref'], 'ART-1')

    def test_reads_factur_x_cii_attachment(self):
        payload = _classify_structured_invoice_xml(CII_INVOICE, 'factur-x.xml')
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['structured_xml']['format'], 'Factur-X/CII')
        self.assertEqual(payload['classification']['document_date'], '2026-09-29')
        self.assertEqual(payload['classification']['lines'][0]['qty'], 10.0)

    def test_rejects_inconsistent_xml_so_caller_can_fall_back_to_llm(self):
        inconsistent = UBL_INVOICE.replace(b'<cbc:TaxInclusiveAmount currencyID="EUR">120.00', b'<cbc:TaxInclusiveAmount currencyID="EUR">130.00')
        self.assertIsNone(_classify_structured_invoice_xml(inconsistent, 'factur-x.xml'))

    def test_rejects_unrelated_or_unsafe_xml(self):
        self.assertIsNone(_classify_structured_invoice_xml(b'<root><value>1</value></root>', 'data.xml'))
        self.assertIsNone(_classify_structured_invoice_xml(b'<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><Invoice>&xxe;</Invoice>', 'data.xml'))

    def test_valid_xml_bypasses_visual_llm_in_reception_flow(self):
        pdf_bytes = pdf_with_attachment('factur-x.xml', UBL_INVOICE)
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as handle:
            handle.write(pdf_bytes)
            path = handle.name
        document = SimpleNamespace(
            docinstamp='DOC-1', file_name='invoice.pdf', file_ext='.pdf', mime_type='application/pdf',
            extracted_text='', feid=1, fornecedor_no=None, doc_type_detected='', dtalt=None,
            useralteracao='', usercriacao='tester', processing_meta_json='{}',
        )
        fake_db = MagicMock()
        fake_db.session.get.return_value = document
        try:
            with patch('services.document_ai_service._ensure_document_ai_schema'), \
                 patch('services.document_ai_service._document_absolute_path', return_value=path), \
                 patch('services.document_ai_service._supplier_candidates_for_llm', return_value=[]), \
                 patch('services.document_ai_service.classify_document_visual') as visual_llm, \
                 patch('services.document_ai_service.resolve_fe_entity', return_value={}), \
                 patch('services.document_ai_service.search_suppliers', return_value=[]), \
                 patch('services.document_ai_service._document_log'), \
                 patch('services.document_ai_service.db', fake_db):
                payload = classify_document_with_llm('DOC-1', 'tester')
            self.assertEqual(payload['mode'], 'embedded_xml')
            visual_llm.assert_not_called()
            self.assertIn('structured_xml_classification', document.processing_meta_json)
            fake_db.session.commit.assert_called_once()
        finally:
            os.unlink(path)

    def test_invalid_structured_xml_keeps_visual_llm_fallback(self):
        inconsistent = UBL_INVOICE.replace(b'<cbc:TaxInclusiveAmount currencyID="EUR">120.00', b'<cbc:TaxInclusiveAmount currencyID="EUR">130.00')
        pdf_bytes = pdf_with_attachment('factur-x.xml', inconsistent)
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as handle:
            handle.write(pdf_bytes)
            path = handle.name
        document = SimpleNamespace(
            docinstamp='DOC-2', file_name='invoice.pdf', file_ext='.pdf', mime_type='application/pdf',
            extracted_text='', feid=1, fornecedor_no=None, doc_type_detected='', dtalt=None,
            useralteracao='', usercriacao='tester', processing_meta_json='{}',
        )
        fake_db = MagicMock()
        fake_db.session.get.return_value = document
        llm_payload = {'ok': False, 'mode': 'visual', 'model': 'test-model'}
        try:
            with patch('services.document_ai_service._ensure_document_ai_schema'), \
                 patch('services.document_ai_service._document_absolute_path', return_value=path), \
                 patch('services.document_ai_service._supplier_candidates_for_llm', return_value=[]), \
                 patch('services.document_ai_service._document_first_page_image_bytes', return_value=(b'image', 'image/png')), \
                 patch('services.document_ai_service.classify_document_visual', return_value=llm_payload) as visual_llm, \
                 patch('services.document_ai_service.db', fake_db):
                payload = classify_document_with_llm('DOC-2', 'tester')
            self.assertIs(payload, llm_payload)
            visual_llm.assert_called_once()
            self.assertEqual(visual_llm.call_args.args[0]['image_bytes'], b'image')
        finally:
            os.unlink(path)


if __name__ == '__main__':
    unittest.main()
