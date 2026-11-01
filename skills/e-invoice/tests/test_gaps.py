#!/usr/bin/env python3
"""A line discount, an allowance on the whole document, an amount paid in advance, an identifier never made up and
a particular declared unknown (EN 16931-1 BG-27, BG-20, BT-113, BT-115, BR-CO-13, BR-CO-16): the arithmetic once
(skills/_shared/doc_amounts.py), each XML syntax, the page, the sums rule and the notes floor. Seeded faults fail or
warn as designed."""
import copy
import json
import re
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent
PACK = HERE.parent
SKILLS = PACK.parent
for sub in ("scripts", "page"):
    sys.path.insert(0, str(PACK / sub))
sys.path.insert(0, str(SKILLS / "_shared"))
sys.path.insert(0, str(SKILLS / "_checks"))
import doc_amounts  # noqa: E402
import einvoice_create as cii  # noqa: E402
import countries  # noqa: E402
import money_check  # noqa: E402
import notes_floor  # noqa: E402
import einvoice_particulars as part  # noqa: E402

BUILDER = PACK / "page" / "build_page.py"


def starter(name):
    return json.loads((PACK / "templates" / name).read_text())


def se():
    return starter("se-faktura-rabatt-forskott-spec.json")


def tags(root):
    return [e.tag.split("}")[-1] for e in root.iter()]


def texts(root, tag):
    return [e.text for e in root.iter() if e.tag.split("}")[-1] == tag]


def builder_of(syntax):
    import importlib
    return importlib.import_module(syntax + "_create")


class Arithmetic(unittest.TestCase):
    def test_a_line_closes_with_a_percentage_or_an_amount(self):
        a = doc_amounts.line_amounts({"quantity": 18, "unit_price": 640, "discount_percent": 10})
        self.assertEqual((a["base"], a["discount"], a["net"]), (Decimal("11520.00"), Decimal("1152.00"), Decimal("10368.00")))
        b = doc_amounts.line_amounts({"quantity": 8, "unit_price": 320, "discount_amount": 60})
        self.assertEqual((b["discount"], b["net"], b["percent"]), (Decimal("60.00"), Decimal("2500.00"), None))

    def test_a_discount_that_does_not_close_stops(self):
        with self.assertRaises(SystemExit) as why:
            doc_amounts.line_amounts({"quantity": 10, "unit_price": 100, "discount_percent": 10, "discount_amount": 50})
        self.assertIn("does not close", str(why.exception))
        with self.assertRaises(SystemExit):
            doc_amounts.line_amounts({"quantity": 1, "unit_price": 100, "discount_amount": 150})
        both = doc_amounts.line_amounts({"quantity": 10, "unit_price": 100, "discount_percent": 10, "discount_amount": 100})
        self.assertEqual(both["net"], Decimal("900.00"))

    def settle(self, **extra):
        spec = dict(extra)
        lines = [dict(cat="S", rate=Decimal(25), net=Decimal("1000.00")), dict(cat="S", rate=Decimal(12), net=Decimal("500.00"))]
        return doc_amounts.settle(spec, lines)

    def test_an_allowance_comes_off_its_rate_and_the_amount_due_closes(self):
        m = self.settle(allowances=[{"amount": 100, "reason": "Rebate", "vat_rate": 25}], paid_amount=300)
        self.assertEqual(m["basis"], Decimal("1400.00"))
        self.assertEqual(m["tax"][("S", Decimal(25))], Decimal("225.00"))
        self.assertEqual(m["grand"], Decimal("1400.00") + Decimal("225.00") + Decimal("60.00"))
        self.assertEqual(m["due"], m["grand"] - 300)

    def test_an_allowance_must_name_its_rate_when_the_lines_have_several(self):
        with self.assertRaises(SystemExit) as why:
            self.settle(allowances=[{"amount": 100, "reason": "Rebate"}])
        self.assertIn("vat_rate", str(why.exception))

    def test_a_paid_amount_above_the_total_stops(self):
        with self.assertRaises(SystemExit) as why:
            self.settle(paid_amount=5000)
        self.assertIn("BR-CO-16", str(why.exception))

    def test_a_percentage_allowance_carries_its_base_and_an_amount_one_does_not(self):
        m = self.settle(allowances=[{"percent": 10, "reason": "Rebate", "vat_rate": 25},
                                    {"amount": 20, "base": 500, "reason": "Other", "vat_rate": 12}])
        self.assertEqual([a["base"] for a in m["allowances"]], [Decimal("1000.00"), None])      # PEPPOL-EN16931-R041, -R042
        self.assertEqual(m["allowance_total"], Decimal("120.00"))


class Syntaxes(unittest.TestCase):
    def test_cii_carries_the_discounts_and_the_prepayment(self):
        root, summary = cii.build(dict(se(), allowances=[{"amount": 100, "reason": "Rebate", "vat_rate": 25}]))
        self.assertEqual(texts(root, "ActualAmount"), ["1160.00", "60.00", "100.00"])
        self.assertEqual(texts(root, "CalculationPercent"), ["10"])
        grand = Decimal(texts(root, "GrandTotalAmount")[0])
        self.assertEqual(Decimal(texts(root, "TotalPrepaidAmount")[0]), Decimal("2000.00"))
        self.assertEqual(Decimal(texts(root, "DuePayableAmount")[0]), grand - 2000)
        lines = sum(Decimal(x) for x in texts(root, "LineTotalAmount")[:-1])
        self.assertEqual(lines, Decimal(texts(root, "LineTotalAmount")[-1]))
        self.assertEqual(lines - 100, Decimal(texts(root, "TaxBasisTotalAmount")[0]))
        self.assertEqual(summary["amount_due"], texts(root, "DuePayableAmount")[0])

    def test_ubl_carries_them_and_never_a_base_without_a_percentage(self):
        s = starter("no-faktura-rabatt-forskudd-spec.json")
        root, _ = builder_of("ubl").build(s)
        names = tags(root)
        self.assertEqual(names.count("AllowanceCharge"), 3)      # two lines and the document
        self.assertIn("AllowanceTotalAmount", names)
        self.assertEqual(Decimal(texts(root, "PrepaidAmount")[0]), Decimal("1500.00"))
        due = Decimal(texts(root, "TaxInclusiveAmount")[0]) - Decimal("1500.00")
        self.assertEqual(Decimal(texts(root, "PayableAmount")[0]), due)
        for ac in root.iter("{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}AllowanceCharge"):
            kids = [k.tag.split("}")[-1] for k in ac]
            self.assertEqual("BaseAmount" in kids, "MultiplierFactorNumeric" in kids, kids)

    def test_finvoice_carries_them(self):
        s = starter("fi-finvoice-spec.json")
        s["lines"][0].update(discount_percent=10)
        s["allowances"] = [{"amount": 10, "reason": "Alennus", "vat_rate": s["lines"][0]["vat_rate"]}]
        s["paid_amount"] = 20
        root, summary = builder_of("finvoice").build(s)
        names = tags(root)
        for need in ("RowDiscountPercent", "RowDiscountAmount", "RowDiscountBaseAmount", "DiscountDetails", "InvoicePaidAmount",
                     "DiscountsTotalVatExcludedAmount"):
            self.assertIn(need, names)
        self.assertEqual(texts(root, "EpiInstructedAmount")[0].replace(",", "."), summary["amount_due"])

    def test_facturae_dates_a_payment_on_account(self):
        s = starter("es-factura-spec.json")
        s["paid_amount"] = 50
        with self.assertRaises(SystemExit) as why:
            builder_of("facturae").build(s)
        self.assertIn("paid_date", str(why.exception))
        s["paid_date"] = "2026-09-01"
        s["allowances"] = [{"amount": 10, "reason": "Descuento", "vat_rate": s["lines"][0]["vat_rate"]}]
        root, summary = builder_of("facturae").build(s)
        for need in ("GeneralDiscounts", "TotalGeneralDiscounts", "PaymentsOnAccount", "TotalPaymentsOnAccount"):
            self.assertIn(need, tags(root))
        outstanding = [t for t in texts(root, "TotalOutstandingAmount") if t and t.strip()]
        self.assertEqual(Decimal(outstanding[-1]), Decimal(texts(root, "InvoiceTotal")[-1]) - 50)

    def test_ebinterface_carries_the_prepayment_and_refuses_a_document_allowance(self):
        s = starter("at-ebinterface-spec.json")
        s["paid_amount"] = 30
        root, _ = builder_of("ebinterface").build(s)
        self.assertEqual(Decimal(texts(root, "PayableAmount")[0]), Decimal(texts(root, "TotalGrossAmount")[0]) - 30)
        self.assertEqual(texts(root, "PrepaidAmount"), ["30.00"])
        s["allowances"] = [{"amount": 10, "reason": "Rabatt", "vat_rate": s["lines"][0]["vat_rate"]}]
        with self.assertRaises(SystemExit) as why:
            builder_of("ebinterface").build(s)
        self.assertIn("BG-20", str(why.exception))

    def test_fatturapa_states_an_amount_discount_and_the_payment_left(self):
        s = starter("it-fattura-spec.json")
        s["lines"][0].pop("discount_percent", None)
        s["lines"][0]["discount_amount"] = 12
        s["paid_amount"] = 40
        root, summary = builder_of("fatturapa").build(s)
        self.assertEqual(texts(root, "Importo"), ["12.00"])
        self.assertEqual(Decimal(texts(root, "ImportoPagamento")[0]), Decimal(summary["total_including_vat"]) - 40)
        s["allowances"] = [{"amount": 10, "reason": "Sconto", "vat_rate": s["lines"][0]["vat_rate"]}]
        with self.assertRaises(SystemExit):
            builder_of("fatturapa").build(s)

    def test_ksef_refuses_what_its_structure_has_no_place_for(self):
        s = starter("pl-faktura-spec.json")
        s["paid_amount"] = 10
        with self.assertRaises(SystemExit) as why:
            builder_of("ksef").build(s)
        self.assertIn("BT-113", str(why.exception))


def build_html(order, tmp, name="faktura"):
    src = Path(tmp) / (name + ".json")
    src.write_text(json.dumps(order))
    r = subprocess.run([sys.executable, str(BUILDER), str(src), str(Path(tmp) / (name + ".html"))], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr, Path(tmp) / (name + ".html")


class Page(unittest.TestCase):
    def test_the_page_states_the_discount_the_prepayment_and_what_is_left_to_pay(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, said, page = build_html(dict(se(), allowances=[{"amount": 100, "reason": "Rabatt på ordern", "vat_rate": 25}]), tmp)
            self.assertEqual(rc, 0, said)
            text = page.read_text()
            for word in ("Volymrabatt 10%", "Kampanjrabatt", "Summa rader", "Rabatt på ordern", "Totalt", "Förskottsbetalt",
                         "Att betala", "Godkänd för F-skatt"):
                self.assertIn(word, text)
            self.assertEqual(money_check.page_sums(page, json.loads((Path(tmp) / "faktura.json").read_text())), [])
            # 'Totalt' and not 'Att betala' labels the total with VAT once an amount is paid in advance
            self.assertLess(text.index("Totalt"), text.index("Förskottsbetalt"))

    def test_a_page_that_does_not_close_fails_the_sums_rule(self):
        with tempfile.TemporaryDirectory() as tmp:
            order = dict(se(), allowances=[{"amount": 100, "reason": "Rabatt på ordern", "vat_rate": 25}])
            rc, said, page = build_html(order, tmp)
            html = page.read_text()
            due = re.findall(r"<tr class='total due gross'|<tr class='due gross'><td>Att betala</td><td class='n'>([^<]+)</td>", html)
            m = re.search(r"(<tr class='due gross'><td>Att betala</td><td class='n'>)([^<]+)(</td>)", html)
            self.assertTrue(m, html[-900:])
            page.write_text(html.replace(m.group(0), m.group(1) + "15 000,00 kr" + m.group(3)))
            bad = money_check.page_sums(page, order)
            self.assertTrue(any("amount due" in b for b in bad), bad)
            # a sum of lines that does not match the allowance
            page.write_text(html.replace("Rabatt på ordern", "Rabatt på ordern").replace("-100,00", "-90,00"))
            self.assertTrue(any("BR-CO-13" in b for b in money_check.page_sums(page, order)))

    def test_a_discount_or_a_paid_amount_that_does_not_close_stops_the_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            order = se()
            order["lines"][0]["discount_amount"] = 50            # 10 percent of 11 600 is 1 160
            rc, said, _ = build_html(order, tmp)
            self.assertNotEqual(rc, 0)
            self.assertIn("does not close", said)
            order = se()
            order["paid_amount"] = 99999
            self.assertNotEqual(build_html(order, tmp)[0], 0)


class Identifiers(unittest.TestCase):
    NOTES = ("Vi: Exempel AB, org.nr 556000-2106. Momsreg.nr SE556000210601. Kund: Exempel Industri AB, Org.nr 556000-3104. "
             "KvK 87654321. Norska: NO999000118MVA.")

    def test_an_identifier_the_notes_do_not_give_is_asked_about(self):
        page = "Momsreg.nr: SE556000210601   Kundens momsreg.nr: SE556000310401   Org.nr 556000-2106"
        self.assertEqual(notes_floor.identifiers_not_in_notes(page, self.NOTES), ["SE556000310401"])

    def test_the_same_identifier_in_another_grouping_is_not(self):
        page = "Org.nr. 999 000 118 MVA   KvK: 8765 4321   Momsreg.nr SE 5560-0021-0601   VAT NO999000118MVA"
        self.assertEqual(notes_floor.identifiers_not_in_notes(page, self.NOTES), [])

    def test_a_vat_number_built_from_an_organisation_number_is_the_case_that_was_found(self):
        notes = "Kund: Exempel Industri AB, Org.nr 556000-3104."
        self.assertEqual(notes_floor.identifiers_not_in_notes("Kundens momsreg.nr SE556000310401", notes), ["SE556000310401"])

    def test_an_incoterms_rule_the_notes_do_not_name_is_asked_about(self):
        page = "Leveransvillkor DAP Sosnowiec, Polska, Incoterms 2020"
        self.assertEqual(notes_floor.incoterms_not_in_notes(page, "Dostawa do naszego magazynu"), ["DAP"])
        self.assertEqual(notes_floor.incoterms_not_in_notes(page, "Leverans enligt DAP"), [])

    def test_the_floor_says_so_in_its_question(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "notes.txt").write_text("Kund: Exempel Industri AB, Org.nr 556000-3104. Pris 100,00 kr.")
            page = Path(tmp, "out.html")
            page.write_text("<html><body>Kundens momsreg.nr SE556000310401 Org.nr 556000-3104 100,00 kr</body></html>")
            question, _ = notes_floor.judge(page, tmp)
            self.assertIn("SE556000310401", question)
            self.assertIn("never built from another", question)


class Unknown(unittest.TestCase):
    def test_an_austrian_buyers_missing_uid_over_10000_no_longer_stops_when_declared_unknown(self):
        s = starter("at-rechnung-spec.json")
        s["lines"][0]["quantity"] = 400
        s["buyer"].pop("vat_id", None)
        missing = countries.refuse(s)[0]
        self.assertTrue(any(m.startswith("buyer.vat_id") for m in missing), missing)
        s["buyer"]["unknown"] = ["vat_id"]
        missing, warnings = countries.refuse(s)
        self.assertEqual([m for m in missing if m.startswith("buyer.vat_id")], [])
        self.assertTrue(any("buyer.vat_id is declared unknown" in w and "UID" in w for w in warnings), warnings)
        self.assertEqual(countries.xml_blocked(s), [])                 # the XML is valid without it
        self.assertIsNotNone(cii.document_xml(s)[0])

    def test_a_totals_that_do_not_close_are_never_declarable(self):
        s = se()
        s["unknown"] = ["paid_amount", "lines", "seller.name"]
        s["paid_amount"] = 99999
        with self.assertRaises(SystemExit):
            cii.document_xml(s)

    def test_an_xml_that_cannot_be_valid_without_it_is_not_written(self):
        s = starter("nl-factuur-spec.json")
        s["seller"].pop("register_number", None)
        s["seller"].pop("kvk", None)
        s["seller"]["unknown"] = ["register_number"]
        data, summary, syntax = cii.document_xml(s)
        self.assertIsNone(data)
        self.assertEqual(syntax, "none")
        self.assertIn("only the page is written", " ".join(summary["warnings"]))

    def test_a_swedish_seller_is_asked_about_f_skatt_and_only_asked(self):
        s = starter("invoice-spec.json")
        s["seller"].pop("unknown", None)
        passed, why = part.judge(s, "Faktura 1", [])
        self.assertTrue(passed and why.startswith("WARN") and "F-skatt" in why, why)
        passed, why = part.judge(s, "Faktura 1", [("notes.txt", "Godkänd för F-skatt.")])
        self.assertIn("notes.txt", why)
        passed, why = part.judge(s, "Faktura 1 Godkänd för F-skatt", [("notes.txt", "Godkänd för F-skatt.")])
        self.assertFalse(str(why).startswith("WARN") and "F-skatt" in str(why), why)


class SwedishGiro(unittest.TestCase):
    """A Swedish seller paid to a Bankgiro or PlusGiro number, and the buyer's order number (BT-13): both in the
    file and on the page, and a number whose check digit fails stops the build."""

    def order(self, **pay):
        return dict(se(), payment=pay, order_reference="PO-2026-311")

    def test_the_file_carries_the_bankgiro_number_and_the_order_number(self):
        root, _ = cii.build(self.order(bankgiro="123-4566"))
        self.assertEqual(root.find(".//{*}SpecifiedTradeSettlementPaymentMeans/{*}TypeCode").text, "30")
        self.assertEqual(texts(root, "ProprietaryID"), ["1234566"])
        self.assertEqual(texts(root, "IBANID"), [])
        self.assertEqual(root.find(".//{*}BuyerOrderReferencedDocument/{*}IssuerAssignedID").text, "PO-2026-311")

    def test_an_iban_stays_the_account_and_a_plusgiro_number_is_carried_alone(self):
        root, _ = cii.build(self.order(means_code="58", iban="SE35 5000 0000 0549 1000 0003", bankgiro="123-4566"))
        self.assertEqual(texts(root, "IBANID"), ["SE3550000000054910000003"])
        self.assertEqual(texts(root, "ProprietaryID"), [])
        root, _ = cii.build(self.order(plusgiro="1234-4"))
        self.assertEqual(texts(root, "ProprietaryID"), ["12344"])

    def test_a_number_whose_check_digit_fails_stops_the_build(self):
        for pay in ({"bankgiro": "123-4567"}, {"bankgiro": "12-345"}, {"plusgiro": "1234-6"}):
            with self.assertRaises(SystemExit) as why:
                cii.build(self.order(**pay))
            self.assertIn("check digit", str(why.exception))

    def test_the_page_prints_the_bankgiro_number_and_the_order_number(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, said, page = build_html(self.order(bankgiro="1234566"), tmp)
            self.assertEqual(rc, 0, said)
            text = page.read_text()
            for word in ("Bankgiro", "123-4566", "Ert ordernummer", "PO-2026-311"):
                self.assertIn(word, text)
            self.assertNotIn("IBAN", text)


class SwedishCustomer(unittest.TestCase):
    """A Swedish customer's organisationsnummer the notes give: in the file as the buyer's legal registration
    identifier (BT-47) and on the page. A timed run (c01, 2026-10-25) put it in the spec and both left it out."""

    def order(self):
        return dict(se(), buyer=dict(se()["buyer"], register_number="556000-3104"))

    def test_the_file_carries_it(self):
        root, _ = cii.build(self.order())
        self.assertEqual(root.find(".//{*}BuyerTradeParty/{*}SpecifiedLegalOrganization/{*}ID").text, "556000-3104")

    def test_the_page_prints_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, said, page = build_html(self.order(), tmp)
            self.assertEqual(rc, 0, said)
            text = page.read_text()
            for word in ("Kundens org.nr", "556000-3104"):
                self.assertIn(word, text)


class IntraCommunity(unittest.TestCase):
    def test_an_intra_community_supply_asks_where_the_goods_went(self):
        order = dict(se(), buyer=dict(se()["buyer"], country="DE", vat_id="DE123456789"))
        for line in order["lines"]:
            line.update(vat_rate=0, vat_category="K", exemption_reason="Gemenskapsintern leverans")
        with self.assertRaises(SystemExit) as why:
            cii.build(order)
        self.assertIn("BR-IC-12", str(why.exception))
        root, _ = cii.build(dict(order, delivery_address={"city": "Berlin", "country": "DE"}))
        self.assertEqual(root.find(".//{*}ShipToTradeParty/{*}PostalTradeAddress/{*}CountryID").text, "DE")


if __name__ == "__main__":
    unittest.main()
