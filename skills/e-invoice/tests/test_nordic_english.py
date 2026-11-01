"""Norway, Denmark, Finland, the UK, Australia, Canada and the US: each kind of mistake is built and seen caught.

    python3 -m unittest skills/e-invoice/tests/test_nordic_english.py

Standard library only: no browser, no validator, no network. The page rules are fed the page's text as
the builder would print it, then the same text with one thing taken out.
"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent
PACK = HERE.parent
sys.path.insert(0, str(PACK / "scripts"))
sys.path.insert(0, str(PACK / "page"))
sys.path.insert(0, str(PACK.parent / "_checks"))
import countries  # noqa: E402
import einvoice_create  # noqa: E402
import finvoice_create  # noqa: E402
import ubl_create  # noqa: E402
import einvoice_ids as ids  # noqa: E402
import einvoice_country as ec  # noqa: E402
import credit_note_check as cn  # noqa: E402

TEMPLATES = PACK / "templates"


def spec(name):
    return json.loads((TEMPLATES / name).read_text())


def ubl(s):
    data, summary = ubl_create.xml_bytes(s)
    return ET.fromstring(data), summary, data


def refused(test, s, words, build=None):
    with test.assertRaises(SystemExit) as caught:
        (build or einvoice_create.document_xml)(s)
    test.assertIn(words, str(caught.exception))


class Identifiers(unittest.TestCase):
    def test_check_digits(self):
        self.assertTrue(ids.no_orgnr_ok("999 999 999"))
        self.assertFalse(ids.no_orgnr_ok("999 999 998"))
        self.assertTrue(ids.no_account_ok("8601.11.17947"))
        self.assertTrue(ids.fi_ytunnus_ok("1234567-1"))
        self.assertFalse(ids.fi_ytunnus_ok("1234567-2"))
        self.assertTrue(ids.fi_reference_ok("202604123"))
        self.assertFalse(ids.fi_reference_ok("202604124"))
        self.assertTrue(ids.gb_vat_ok("GB123456727"))
        self.assertFalse(ids.gb_vat_ok("GB123456728"))
        self.assertTrue(ids.au_abn_ok("12 345 678 012"))
        self.assertFalse(ids.au_abn_ok("12 345 678 013"))
        self.assertTrue(ids.iban_ok("FI21 1234 5600 0007 85"))
        self.assertTrue(ids.ca_gst_ok("123456782 RT0001"))
        self.assertFalse(ids.ca_gst_ok("123456782"))

    def test_bank_barcode_version_4(self):
        code = ids.fi_virtual_barcode("FI21 1234 5600 0007 85", 3112.40, "202604123", "2026-10-19")
        self.assertEqual(len(code), 54)
        self.assertEqual(code, "4" + "2112345600000785" + "003112" + "40" + "000" + "202604123".rjust(20, "0") + "261019")


class Syntax(unittest.TestCase):
    def test_each_country_gets_its_file(self):
        self.assertEqual(countries.syntax_of(spec("no-faktura-spec.json")), "ubl")
        self.assertEqual(countries.syntax_of(spec("uk-vat-invoice-spec.json")), "ubl")
        self.assertEqual(countries.syntax_of(spec("fi-finvoice-spec.json")), "finvoice")
        self.assertEqual(countries.syntax_of(spec("us-invoice-spec.json")), "none")
        self.assertEqual(countries.syntax_of(spec("facture-spec.json")), "cii")
        self.assertEqual(countries.syntax_of(spec("invoice-spec.json")), "cii")
        data, summary, syntax = einvoice_create.document_xml(spec("au-tax-invoice-spec.json"))
        self.assertIsNone(data)
        self.assertEqual(syntax, "none")


class PeppolUbl(unittest.TestCase):
    def test_norwegian_invoice(self):
        root, summary, _ = ubl(spec("no-faktura-spec.json"))
        self.assertTrue(root.tag.endswith("}Invoice"))
        self.assertEqual(root.find("{*}CustomizationID").text, ubl_create.CUSTOMIZATION)
        self.assertEqual(root.find("{*}ProfileID").text, ubl_create.PROFILE)
        seller = root.find("{*}AccountingSupplierParty/{*}Party")
        self.assertEqual(seller.find("{*}EndpointID").get("schemeID"), "0192")
        ids_ = {ts.find("{*}TaxScheme/{*}ID").text: ts.find("{*}CompanyID").text for ts in seller.findall("{*}PartyTaxScheme")}
        self.assertEqual(ids_, {"VAT": "NO999999999MVA", "TAX": "Foretaksregisteret"})
        self.assertEqual(root.find("{*}PaymentMeans/{*}PaymentID").text, "20260410")
        # The discounted line: list price, an allowance, and the net (PEPPOL-EN16931-R120).
        line = root.findall("{*}InvoiceLine")[1]
        self.assertEqual(line.find("{*}LineExtensionAmount").text, "3402.00")
        self.assertEqual(line.find("{*}AllowanceCharge/{*}Amount").text, "378.00")

    def test_credit_note_is_a_creditnote_document(self):
        root, _summary, _ = ubl(spec("dk-kreditnota-spec.json"))
        self.assertTrue(root.tag.endswith("}CreditNote"))
        self.assertEqual(root.find("{*}CreditNoteTypeCode").text, "381")
        self.assertEqual(root.find("{*}BillingReference/{*}InvoiceDocumentReference/{*}ID").text, "F-2026-118")
        legal = root.find("{*}AccountingSupplierParty/{*}Party/{*}PartyLegalEntity/{*}CompanyID")
        self.assertEqual((legal.text, legal.get("schemeID")), ("12345674", "0184"))
        self.assertIsNotNone(root.find("{*}CreditNoteLine/{*}CreditedQuantity"))

    def test_vat_also_in_nok(self):
        s = spec("no-faktura-spec.json")
        s["currency"] = "EUR"
        refused(self, copy.deepcopy(s), "exchange_rate")
        s["exchange_rate"] = 11.7
        root, _summary, _ = ubl(s)
        self.assertEqual(root.find("{*}TaxCurrencyCode").text, "NOK")
        self.assertEqual(len(root.findall("{*}TaxTotal")), 2)

    def test_peppol_needs_a_reference_and_addresses(self):
        s = spec("uk-vat-invoice-spec.json")
        s.pop("buyer_reference")
        refused(self, s, "PEPPOL-EN16931-R003")
        s = spec("dk-faktura-spec.json")
        s["buyer"].pop("electronic_address")
        s["buyer"].pop("cvr")
        refused(self, s, "PEPPOL-EN16931-R010")

    def test_the_credit_note_check_reads_ubl(self):
        with tempfile.TemporaryDirectory() as d:
            s = spec("no-kreditnota-spec.json")
            (Path(d) / "spec.json").write_text(json.dumps(s))
            _root, _summary, data = ubl(s)
            xml = Path(d) / "invoice.xml"
            xml.write_bytes(data)
            for rule in ("INV-CREDIT-TYPE", "INV-CREDIT-SIGN", "INV-CREDIT-VAT", "INV-CREDIT-REF"):
                self.assertTrue(cn.check(rule, xml, {}, "first")[0], rule)
            xml.write_bytes(data.replace(b"<cbc:TaxAmount currencyID=\"NOK\">85.05", b"<cbc:TaxAmount currencyID=\"NOK\">-85.05"))
            ok, why = cn.check("INV-CREDIT-SIGN", xml, {}, "first")
            self.assertFalse(ok)
            self.assertIn("negative", why)


class CountryRefusals(unittest.TestCase):
    def test_norway(self):
        s = spec("no-faktura-spec.json")
        s["seller"]["org_number"] = "999 999 998"
        refused(self, s, "modulus 11")
        s = spec("no-faktura-spec.json")
        s.pop("delivery_date")
        refused(self, s, "§ 5-1-1 nr. 4")
        s = spec("no-faktura-spec.json")
        s["seller"]["vat_id"] = "NO999999999"
        refused(self, s, "MVA")

    def test_denmark(self):
        s = spec("dk-faktura-spec.json")
        s["payment"] = {"means_code": "30", "account": "1"}
        refused(self, s, "DK-R-005")
        s = spec("dk-faktura-spec.json")
        s["payment"].pop("bank_reg")
        refused(self, s, "DK-R-006")

    def test_finland(self):
        s = spec("fi-lasku-spec.json")
        s["seller"]["business_id"] = "1234567-9"
        refused(self, s, "check digit")
        s = spec("fi-lasku-spec.json")
        s["payment"]["reference"] = "202604124"
        refused(self, s, "viitenumero")

    def test_uk(self):
        s = spec("uk-vat-invoice-spec.json")
        s["seller"]["vat_id"] = "GB123456728"
        refused(self, s, "VAT registration number")
        s = spec("uk-vat-invoice-spec.json")
        s["currency"] = "EUR"
        refused(self, s, "sterling")

    def test_australia_buyer_from_a_thousand_dollars(self):
        s = spec("au-tax-invoice-spec.json")
        s["buyer"] = {"name": "Example Office Cleaning Pty Ltd", "country": "AU"}
        refused(self, s, "A$1,000")
        s["lines"] = s["lines"][2:]
        self.assertEqual(einvoice_create.document_xml(s)[2], "none")

    def test_canada_thresholds(self):
        s = spec("ca-invoice-spec.json")
        s.pop("payment_terms")
        refused(self, s, "s. 3(c)(ii)")
        s["lines"] = [{"name": "Cable", "quantity": 1, "unit": "C62", "unit_price": 80}]
        self.assertEqual(einvoice_create.document_xml(s)[2], "none")
        s = spec("ca-facture-spec.json")
        s["seller"].pop("qst_number")
        refused(self, s, "QST")


class Finvoice(unittest.TestCase):
    def test_invoice_and_credit_note(self):
        data, summary = finvoice_create.xml_bytes(spec("fi-finvoice-spec.json"))
        root = ET.fromstring(data)
        self.assertEqual(root.get("Version"), "3.0")
        self.assertEqual(root.find("InvoiceDetails/InvoiceTypeCode").text, "INV01")
        self.assertEqual(root.find("InvoiceDetails/InvoiceTotalVatIncludedAmount").text, "3112,40")
        self.assertEqual(root.find("VirtualBankBarcode").text, summary["virtual_barcode"])
        s = spec("fi-hyvityslasku-spec.json")
        root = ET.fromstring(finvoice_create.xml_bytes(s)[0])
        self.assertEqual(root.find("InvoiceDetails/InvoiceTypeCode").text, "INV02")
        self.assertTrue(root.find("InvoiceDetails/InvoiceTotalVatIncludedAmount").text.startswith("-"))
        self.assertEqual(root.find("InvoiceDetails/OriginalInvoiceNumber").text, "10458")


class PageRules(unittest.TestCase):
    """The rules read the page: the right text passes, the same text with one part missing fails."""

    def test_norway(self):
        s = spec("no-faktura-spec.json")
        text = ("Fjordlys Rådgivning AS Org.nr. 999 999 999 MVA Foretaksregisteret Faktura 2026-0412 Fakturadato "
                "05.10.2026 Forfallsdato 19.10.2026 Leveringsdato 02.10.2026 Leveringssted Prøvevegen 8 "
                "Nordkapp Verksted AS MVA 25 % 5 200,50 NOK")
        self.assertTrue(ec.no_seller(s, text, None)[0])
        self.assertTrue(ec.no_content(s, text, None)[0])
        ok, why = ec.no_seller(s, text.replace("Foretaksregisteret", ""), None)
        self.assertFalse(ok)
        self.assertIn("Foretaksregisteret", why)
        self.assertFalse(ec.no_seller(s, text.replace("999 999 999 MVA", "999 999 999"), None)[0])
        self.assertFalse(ec.no_content(s, text.replace("Leveringssted", ""), None)[0])

    def test_uk_rate_beside_lines(self):
        s = spec("uk-vat-invoice-spec.json")
        text = ("Example Studio Ltd 1 Example Street Manchester VAT registration no. GB 123 4567 27 Sample Trading plc "
                "2 Sample Road Leeds INV-2026-0207 05/10/2026 Tax point 30/09/2026 650.00 20% 18.00 20% 400.00 0% "
                "£4,480.00 £816.00")
        self.assertTrue(ec.uk_invoice(s, text, None)[0])
        ok, why = ec.uk_invoice(s, text.replace(" 0% ", " "), None)
        self.assertFalse(ok)
        self.assertIn("rate 0", why)

    def test_australia_heading_and_gst_free(self):
        s = spec("au-tax-invoice-spec.json")
        text = ("Example Plumbing Supplies Pty Ltd Tax invoice INV-1043 05/10/2026 ABN 12 345 678 012 GST-free "
                "Example Office Cleaning Pty Ltd 2 Example Road $364.00")
        self.assertTrue(ec.au_invoice(s, text, None)[0])
        self.assertFalse(ec.au_invoice(s, text.replace("Tax invoice", "Invoice"), None)[0])
        self.assertFalse(ec.au_invoice(s, text.replace("GST-free", ""), None)[0])

    def test_us_has_no_vat(self):
        s = spec("us-invoice-spec.json")
        text = ("Invoice 1087 Subtotal $2,979.00 Texas state sales tax 6.25% $168.38 City of Austin 1% $26.94 "
                "Austin MTA 1% $26.94 Total $3,201.26")
        self.assertTrue(ec.us_invoice(s, text, None)[0])
        ok, why = ec.us_invoice(s, text + " VAT 20%", None)
        self.assertFalse(ok)
        self.assertIn("VAT", why)

    def test_finnish_barcode_must_match(self):
        s = spec("fi-lasku-spec.json")
        code = ids.fi_virtual_barcode("FI21 1234 5600 0007 85", 3112.40, "202604123", "2026-10-19")
        text = "Eräpäivä 19.10.2026 FI21 1234 5600 0007 85 Viitenumero 2026 04123 Virtuaaliviivakoodi " + code
        self.assertTrue(ec.fi_payment(s, text, None)[0])
        ok, why = ec.fi_payment(s, text.replace(code, code[:-6] + "261020"), None)
        self.assertFalse(ok)
        self.assertIn("barcode", why)


if __name__ == "__main__":
    unittest.main()
