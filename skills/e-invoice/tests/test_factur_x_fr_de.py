"""Factur-X, the French invoice and the German XRechnung: each kind of mistake is built and seen caught.

    python3 -m unittest skills/e-invoice/tests/test_factur_x_fr_de.py

Needs pypdf and poppler (pdfdetach, pdfinfo) for the PDF tests; no browser, no validator, no network.
"""
import copy
import json
import shutil
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
import einvoice_create  # noqa: E402

TEMPLATES = PACK / "templates"


def spec(name):
    return json.loads((TEMPLATES / name).read_text())


def xml_root(s):
    data, summary = einvoice_create.xml_bytes(s)
    return ET.fromstring(data), summary


def find_all(root, tag):
    return root.findall(".//{*}" + tag)


class FrenchXml(unittest.TestCase):
    def test_reform_data_reaches_the_xml(self):
        root, summary = xml_root(spec("facture-spec.json"))
        process = root.find("{*}ExchangedDocumentContext/{*}BusinessProcessSpecifiedDocumentContextParameter/{*}ID")
        self.assertEqual(process.text, "S1")
        codes = [n.findtext("{*}SubjectCode") for n in find_all(root, "IncludedNote")]
        for code in ("PMD", "PMT", "AAB", "BAR"):
            self.assertEqual(codes.count(code), 1, code)
        sirens = [(e.text, e.get("schemeID")) for e in find_all(root, "SpecifiedLegalOrganization/{*}ID")]
        self.assertEqual(sirens, [("000000018", "0002"), ("000000026", "0002")])
        self.assertEqual(root.find(".//{*}SellerTradeParty/{*}GlobalID").get("schemeID"), "0009")
        self.assertEqual([e.get("schemeID") for e in find_all(root, "URIUniversalCommunication/{*}URIID")], ["0225", "0225"])
        self.assertEqual([e.text for e in find_all(root, "DueDateTypeCode")], ["5"])
        self.assertEqual(summary["total_including_vat"], "3564.00")

    def test_what_only_the_person_knows_stops_the_build(self):
        for field, path, said in (("buyer.siren", ("buyer", "siren"), "buyer.siren"),
                                  ("seller.siren", ("seller", "siren"), "seller.siren"),
                                  ("seller.share_capital", ("seller", "share_capital"), "share_capital"),
                                  ("operation", ("operation",), "operation")):
            s = spec("facture-spec.json")
            target = s
            for key in path[:-1]:
                target = target[key]
            del target[path[-1]]
            with self.assertRaises(SystemExit) as caught:
                einvoice_create.xml_bytes(s)
            self.assertIn(said, str(caught.exception), field)

    def test_defaults_are_said(self):
        s = spec("facture-spec.json")
        del s["late_penalty_rate"], s["early_payment_discount"], s["buyer"]["electronic_address"]
        root, summary = xml_root(s)
        text = " ".join(summary["warnings"])
        self.assertIn("late_penalty_rate", text)
        self.assertIn("early_payment_discount", text)
        self.assertIn("buyer.electronic_address", text)
        notes = {n.findtext("{*}SubjectCode"): n.findtext("{*}Content") for n in find_all(root, "IncludedNote")}
        self.assertIn("10 points", notes["PMD"])
        self.assertIn("néant", notes["AAB"])

    def test_reverse_charge_says_autoliquidation(self):
        s = spec("facture-spec.json")
        s["buyer"].update(country="DE", vat_id="DE000000000")
        del s["buyer"]["siren"], s["buyer"]["electronic_address"]
        for line in s["lines"]:
            line.update(vat_category="AE", vat_rate=0)
        root, _ = xml_root(s)
        self.assertEqual(root.find(".//{*}ApplicableHeaderTradeSettlement/{*}ApplicableTradeTax/{*}ExemptionReason").text,
                         "Autoliquidation")
        bar = [n.findtext("{*}Content") for n in find_all(root, "IncludedNote") if n.findtext("{*}SubjectCode") == "BAR"]
        self.assertEqual(bar, ["B2BINT"])

    def test_delivery_address_goes_in_bg15(self):
        s = spec("facture-spec.json")
        s["operation"] = "goods"
        s["delivery_address"] = {"street": "3 quai de l'Essai", "postcode": "13000", "city": "Marseille"}
        root, _ = xml_root(s)
        ship = root.find(".//{*}ShipToTradeParty/{*}PostalTradeAddress")
        self.assertEqual(ship.findtext("{*}CityName"), "Marseille")
        self.assertEqual(ship.findtext("{*}CountryID"), "FR")
        self.assertEqual(root.find(".//{*}BusinessProcessSpecifiedDocumentContextParameter/{*}ID").text, "B1")


class XRechnung(unittest.TestCase):
    def test_business_process_and_addresses(self):
        root, _ = xml_root(spec("xrechnung-credit-note-spec.json"))
        self.assertEqual(root.find(".//{*}BusinessProcessSpecifiedDocumentContextParameter/{*}ID").text,
                         einvoice_create.PEPPOL_BILLING)
        self.assertEqual([e.get("schemeID") for e in find_all(root, "URIUniversalCommunication/{*}URIID")], ["EM", "0204"])

    def test_addresses_default_from_the_order_and_say_so(self):
        s = spec("xrechnung-credit-note-spec.json")
        del s["seller"]["electronic_address"], s["buyer"]["electronic_address"]
        root, summary = xml_root(s)
        ids = [e.text for e in find_all(root, "URIUniversalCommunication/{*}URIID")]
        self.assertEqual(ids, [s["seller"]["contact"]["email"], s["buyer_reference"]])
        self.assertEqual(sum("electronic_address" in w for w in summary["warnings"]), 2)

    def test_an_address_with_no_scheme_stops(self):
        s = spec("xrechnung-credit-note-spec.json")
        s["buyer"]["electronic_address"] = "Lindental portal"
        with self.assertRaises(SystemExit) as caught:
            einvoice_create.xml_bytes(s)
        self.assertIn("BR-63", str(caught.exception))


def blank_pdf(path):
    from pypdf import PdfWriter
    w = PdfWriter()
    w.add_blank_page(595, 842)
    with open(path, "wb") as fh:
        w.write(fh)


@unittest.skipUnless(shutil.which("pdfdetach") and shutil.which("pdfinfo"), "poppler is not installed")
class FacturX(unittest.TestCase):
    def setUp(self):
        try:
            import pypdf  # noqa: F401
        except ImportError:
            self.skipTest("pypdf is not installed")
        import facturx_pdf
        import einvoice_external
        self.fx, self.ext = facturx_pdf, einvoice_external
        self.dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def make(self, name):
        data, _ = einvoice_create.xml_bytes(spec(name))
        pdf, xml = self.dir / "invoice.pdf", self.dir / "invoice.xml"
        blank_pdf(pdf)
        xml.write_bytes(data)
        return pdf, xml, data

    def test_en16931_and_xrechnung_profiles(self):
        for name, level, file_name in (("facture-spec.json", "EN 16931", "factur-x.xml"),
                                       ("xrechnung-credit-note-spec.json", "XRECHNUNG", "xrechnung.xml")):
            pdf, xml, data = self.make(name)
            self.assertEqual(self.fx.embed(pdf, data, pdf, "t", "fr-FR"), (level, file_name))
            ok, why = self.ext.check("EINV-FACTURX", pdf, {}, "first")
            self.assertTrue(ok, why)
            self.assertIn(level, why)

    def test_a_plain_page_fails(self):
        pdf, _xml, _data = self.make("facture-spec.json")
        ok, why = self.ext.check("EINV-FACTURX", pdf, {}, "first")
        self.assertFalse(ok)
        self.assertIn("no invoice XML inside", why)

    def test_the_xml_inside_must_be_the_one_beside(self):
        pdf, xml, data = self.make("facture-spec.json")
        self.fx.embed(pdf, data, pdf, "t", "fr-FR")
        xml.write_bytes(data.replace(b"FA-2026-0042", b"FA-2026-0043"))
        ok, why = self.ext.check("EINV-FACTURX", pdf, {}, "first")
        self.assertFalse(ok)
        self.assertIn("not the invoice.xml beside it", why)

    def test_validators_absent_say_could_not(self):
        pdf, _xml, data = self.make("facture-spec.json")
        import os
        saved = dict(os.environ)
        os.environ["FILETASK_EINVOICE_TOOLS"] = str(self.dir / "none")
        for key in ("FILETASK_KOSIT_JAR", "FILETASK_KOSIT_CONFIG", "FILETASK_FNFE_RFE", "FILETASK_VERAPDF",
                    "FILETASK_VERAPDF_IMAGE"):
            os.environ.pop(key, None)
        try:
            for rule in ("EINV-KOSIT", "EINV-FR-CTC"):
                ok, why = self.ext.check(rule, pdf, {}, "first")
                self.assertFalse(ok)
                self.assertTrue(why.startswith("could not run"), why)
        finally:
            os.environ.clear()
            os.environ.update(saved)


class FrenchChecks(unittest.TestCase):
    def setUp(self):
        import fr_invoice_check
        self.check = fr_invoice_check.check
        self.dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def write(self, s, mutate=None):
        data, _ = einvoice_create.xml_bytes(s)
        root = ET.fromstring(data)
        if mutate:
            mutate(root)
        (self.dir / "invoice.xml").write_bytes(ET.tostring(root))
        (self.dir / "order.json").write_text(json.dumps(s))
        return self.dir / "invoice.xml"

    def test_clean_xml_passes(self):
        path = self.write(spec("facture-spec.json"))
        for rule in ("FR-SELLER", "FR-BUYER", "FR-PAYMENT", "FR-MENTIONS"):
            ok, why = self.check(rule, path, {}, "first")
            self.assertTrue(ok, "%s: %s" % (rule, why))

    def test_missing_notes_are_caught(self):
        def drop_notes(root):
            doc = root.find("{*}ExchangedDocument")
            for n in doc.findall("{*}IncludedNote"):
                if n.findtext("{*}SubjectCode") in ("PMT", "AAB"):
                    doc.remove(n)
        ok, why = self.check("FR-PAYMENT", self.write(spec("facture-spec.json"), drop_notes), {}, "first")
        self.assertFalse(ok)
        self.assertIn("PMT", why)
        self.assertIn("AAB", why)

    def test_missing_billing_framework_is_caught(self):
        def drop_process(root):
            ctx = root.find("{*}ExchangedDocumentContext")
            ctx.remove(ctx.find("{*}BusinessProcessSpecifiedDocumentContextParameter"))
        ok, why = self.check("FR-MENTIONS", self.write(spec("facture-spec.json"), drop_process), {}, "first")
        self.assertFalse(ok)
        self.assertIn("BR-FR-08", why)

    def test_a_bad_siren_is_caught(self):
        def bad_siren(root):
            root.find(".//{*}SellerTradeParty/{*}SpecifiedLegalOrganization/{*}ID").text = "000000019"
        ok, why = self.check("FR-SELLER", self.write(spec("facture-spec.json"), bad_siren), {}, "first")
        self.assertFalse(ok)
        self.assertIn("check digit", why)

    def test_not_french_is_not_scored(self):
        ok, _why = self.check("FR-SELLER", self.write(spec("xrechnung-credit-note-spec.json")), {}, "first")
        self.assertIsNone(ok)


class PageWords(unittest.TestCase):
    def test_terms(self):
        import build_page
        self.assertEqual(build_page.terms_word("30 days net", "fr-FR"), "30 jours net")
        self.assertEqual(build_page.terms_word("30 days net", "de-DE"), "30 Tage netto")
        self.assertEqual(build_page.terms_word("Remboursement sous 14 jours", "fr-FR"), "Remboursement sous 14 jours")

    def test_french_figures(self):
        import build_page
        self.assertEqual(build_page.with_currency(build_page.amount(2970, "fr-FR"), "EUR", "fr-FR"), "2 970,00 €")
        self.assertEqual(build_page._date("2026-09-15", "fr-FR"), "15/09/2026")


if __name__ == "__main__":
    unittest.main()
