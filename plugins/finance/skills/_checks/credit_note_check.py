#!/usr/bin/env python3
"""Checks for a credit note in EN 16931 Cross Industry Invoice XML or in UBL 2.1 (Peppol BIS Billing 3.0), and
the German XRechnung rules for any invoice or credit note whose buyer asks for XRechnung.

  INV-CREDIT-TYPE  A credit note is invoice type 381 (EN 16931 BT-3), never 380, with a number of its own
                   (BT-1) that is not the number of the invoice it amends. The page beside it, when there is
                   one, calls itself a credit note.
  INV-CREDIT-REF   It names the invoice it amends: the preceding invoice number (BT-25, which BR-55 requires
                   in every preceding invoice reference) and its issue date (BT-26), in the XML and on the
                   page. VAT Directive 2006/112/EC Art. 219 treats a document that amends an invoice and
                   refers to it specifically and unambiguously as an invoice.
  INV-CREDIT-SIGN  Its amounts and quantities are positive: the type code 381 carries the sign, so a minus
                   on a credit note reverses it twice.
  INV-CREDIT-VAT   The VAT is broken down once per category and rate, as EN 16931 sets it out: each group's
                   taxable amount is the sum of its line nets (BR-S-08 and the other BR-x-08 rules), its VAT
                   is that amount times the rate, rounded to two decimals (BR-CO-17), there is at least one
                   group (BR-CO-18), and the totals add up (BR-CO-10, -13, -14, -15, -16). When the case
                   gives the lines, the groups match them too.
  INV-XRECHNUNG    For a buyer who asks for XRechnung, the German rules of the KoSIT XRechnung schematron
                   (Apache-2.0, ported and restated here): the XRechnung specification identifier (BR-DE-21),
                   a buyer reference (BT-10, BR-DE-15), payment instructions (BG-16, BR-DE-1) with the
                   account for a credit transfer (BR-DE-23-a), a seller contact (BG-6, BR-DE-2) with a name,
                   phone and email (BT-41 to BT-43, BR-DE-5, -6, -7), and the seller's and buyer's city
                   and post code (BR-DE-3, -4, -8, -9).

check(rule_id, path, case, stage) -> (passed, evidence); passed is None when the rule does not apply.
The path is the XML or the page printed beside it (invoice.pdf next to invoice.xml). Standard library
only; pdftotext reads the page.

This is a drafting check of the file's own data against published rules. It is not a validator, and
not tax or legal advice: it never decides whether a credit note, an exemption or a reverse charge is
right for the person, only that what the file says holds together.
"""
import json
import re
import subprocess
import sys
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from xml.etree import ElementTree as ET

RSM = "{urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100}"
XRECHNUNG_ID = "urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0"
CREDIT_WORDS = re.compile(r"gutschrift|rechnungskorrektur|credit note|kreditnota|kreditfaktura|"
                          r"creditnota|creditfactuur|avoir|nota di credito|nota de cr[eé]dito|"
                          r"faktura korygująca|hyvityslasku|factura rectificativa|korekta", re.I)
AMOUNTS = ("LineTotalAmount", "ChargeAmount", "BasisAmount", "CalculatedAmount", "TaxBasisTotalAmount",
           "TaxTotalAmount", "GrandTotalAmount", "DuePayableAmount", "BilledQuantity", "AllowanceTotalAmount",
           "ChargeTotalAmount", "TotalPrepaidAmount",
           # The same amounts in UBL 2.1 (Peppol BIS Billing 3.0).
           "LineExtensionAmount", "TaxExclusiveAmount", "TaxInclusiveAmount", "PayableAmount", "TaxableAmount",
           "TaxAmount", "PriceAmount", "CreditedQuantity", "InvoicedQuantity", "PrepaidAmount")
UBL_ROOTS = ("{urn:oasis:names:specification:ubl:schema:xsd:Invoice-2}Invoice",
             "{urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2}CreditNote")
CENT = Decimal("0.01")


def dec(text):
    try:
        return Decimal(str(text).strip())
    except (InvalidOperation, ValueError):
        return None


def r2(x):
    return Decimal(str(x)).quantize(CENT, rounding=ROUND_HALF_UP)


def same(a, b):
    return a is not None and b is not None and abs(Decimal(a) - Decimal(b)) < Decimal("0.005")


def find(node, path):
    """The first element under node along a path of local names, any namespace."""
    if node is None:
        return None
    return node.find("/".join("{*}" + p for p in path.split("/")))


def text(node, path):
    el = find(node, path)
    return (el.text or "").strip() if el is not None and el.text else ""


def iso(node):
    """A CII date (format 102, YYYYMMDD) as YYYY-MM-DD."""
    if node is None:
        return ""
    s = node.find("{*}DateTimeString")
    raw = (s.text or "").strip() if s is not None else ""
    return "%s-%s-%s" % (raw[:4], raw[4:6], raw[6:8]) if re.fullmatch(r"\d{8}", raw) else raw


# ---- where the data is -----------------------------------------------------------------------

def xml_for(path):
    """The CII XML the rules read: the file itself, the XML of the same name beside a page, or the one
    Cross Industry Invoice in the folder."""
    path = Path(path)
    if path.suffix.lower() == ".xml":
        return path if path.is_file() else None
    same_name = path.with_suffix(".xml")
    if same_name.is_file():
        return same_name
    found = []
    for p in sorted(path.parent.glob("*.xml")):
        try:
            if ET.parse(p).getroot().tag in (RSM + "CrossIndustryInvoice",) + UBL_ROOTS:
                found.append(p)
        except (ET.ParseError, OSError):
            continue
    return found[0] if len(found) == 1 else None


def page_for(path):
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        return path if path.is_file() else None
    pdf = path.with_suffix(".pdf")
    return pdf if pdf.is_file() else None


def page_text(pdf):
    if pdf is None:
        return ""
    out = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True)
    return re.sub(r"[ \t  ]+", " ", out.stdout)


def source_beside(path):
    """The order the file was built from: a JSON beside it (or one folder up) with lines and parties,
    and no trade-document type."""
    path = Path(path).resolve()
    for base in (path.parent, path.parent.parent):
        for p in sorted(base.glob("*.json")):
            try:
                data = json.loads(p.read_text())
            except (ValueError, OSError):
                continue
            if isinstance(data, dict) and data.get("lines") and isinstance(data.get("seller"), dict) \
                    and "type" not in data:
                return data
    return {}


def truth_for(case, stage):
    t = (case or {}).get("truth") or {}
    staged = t.get(stage or "first")
    return dict({k: v for k, v in t.items() if k not in ("first", "revision")},
                **(staged if isinstance(staged, dict) else {}))


def wanted(path, case, stage):
    """What the file should be: the case's truth when it describes the document, else the order beside."""
    t = truth_for(case, stage)
    keys = ("doc", "type_code", "preceding_invoice", "xrechnung", "lines")
    if any(k in t for k in keys):
        return t
    return source_beside(path)


def asks_credit(src):
    code = str(src.get("type_code") or "").strip()
    return src.get("doc") == "credit_note" or code == "381" or (not code and bool(src.get("preceding_invoice")))


class Invoice:
    def __init__(self, xml):
        self.root = ET.parse(xml).getroot()
        if self.root.tag != RSM + "CrossIndustryInvoice":
            raise ValueError("the root element is %s, not a Cross Industry Invoice" % self.root.tag.split("}")[-1])
        r = self.root
        self.doc = find(r, "ExchangedDocument")
        self.tx = find(r, "SupplyChainTradeTransaction")
        self.agr = find(self.tx, "ApplicableHeaderTradeAgreement")
        self.st = find(self.tx, "ApplicableHeaderTradeSettlement")
        self.number = text(self.doc, "ID")
        self.code = text(self.doc, "TypeCode")
        self.spec_id = text(r, "ExchangedDocumentContext/GuidelineSpecifiedDocumentContextParameter/ID")
        self.currency = text(self.st, "InvoiceCurrencyCode")

    def preceding(self):
        ref = find(self.st, "InvoiceReferencedDocument")
        if ref is None:
            return None
        return text(ref, "IssuerAssignedID"), iso(find(ref, "FormattedIssueDateTime"))

    def lines(self):
        out = []
        for item in self.tx.findall("{*}IncludedSupplyChainTradeLineItem"):
            s = find(item, "SpecifiedLineTradeSettlement")
            out.append(dict(name=text(item, "SpecifiedTradeProduct/Name"),
                            net=dec(text(s, "SpecifiedTradeSettlementLineMonetarySummation/LineTotalAmount")),
                            cat=text(s, "ApplicableTradeTax/CategoryCode") or "S",
                            rate=dec(text(s, "ApplicableTradeTax/RateApplicablePercent") or "0")))
        return out

    def breakdown(self):
        return [dict(cat=text(t, "CategoryCode"), rate=dec(text(t, "RateApplicablePercent") or "0"),
                     base=dec(text(t, "BasisAmount")), vat=dec(text(t, "CalculatedAmount")))
                for t in self.st.findall("{*}ApplicableTradeTax")]

    def totals(self):
        m = find(self.st, "SpecifiedTradeSettlementHeaderMonetarySummation")
        got = {}
        for el in (list(m) if m is not None else []):
            name = el.tag.split("}")[-1]
            # Two VAT totals when the VAT is also stated in the national currency (BT-110, BT-111): the
            # one in the invoice currency is the one the totals add up with.
            if name == "TaxTotalAmount" and el.get("currencyID") not in (None, "", self.currency):
                continue
            got[name] = dec(el.text)
        return got


class UblInvoice:
    """The same reading of a UBL 2.1 Invoice or CreditNote (Peppol BIS Billing 3.0): EN 16931's business
    terms where the UBL syntax binding puts them, under the names the rules above use."""
    TOTALS = {"LineExtensionAmount": "LineTotalAmount", "TaxExclusiveAmount": "TaxBasisTotalAmount",
              "TaxInclusiveAmount": "GrandTotalAmount", "PayableAmount": "DuePayableAmount",
              "AllowanceTotalAmount": "AllowanceTotalAmount", "ChargeTotalAmount": "ChargeTotalAmount",
              "PrepaidAmount": "TotalPrepaidAmount", "PayableRoundingAmount": "RoundingAmount"}

    def __init__(self, xml):
        self.root = ET.parse(xml).getroot()
        if self.root.tag not in UBL_ROOTS:
            raise ValueError("the root element is %s, not a UBL Invoice or CreditNote" % self.root.tag.split("}")[-1])
        r = self.root
        self.ubl = True
        self.agr = self.st = None
        self.number = text(r, "ID")
        self.code = text(r, "InvoiceTypeCode") or text(r, "CreditNoteTypeCode")
        self.spec_id = text(r, "CustomizationID")
        self.currency = text(r, "DocumentCurrencyCode")

    def preceding(self):
        ref = find(self.root, "BillingReference/InvoiceDocumentReference")
        if ref is None:
            return None
        return text(ref, "ID"), text(ref, "IssueDate")

    def lines(self):
        out = []
        for line in list(self.root.findall("{*}InvoiceLine")) + list(self.root.findall("{*}CreditNoteLine")):
            out.append(dict(name=text(line, "Item/Name"), net=dec(text(line, "LineExtensionAmount")),
                            cat=text(line, "Item/ClassifiedTaxCategory/ID") or "S",
                            rate=dec(text(line, "Item/ClassifiedTaxCategory/Percent") or "0")))
        return out

    def breakdown(self):
        rows = []
        for total in self.root.findall("{*}TaxTotal"):
            for sub in total.findall("{*}TaxSubtotal"):
                rows.append(dict(cat=text(sub, "TaxCategory/ID"), rate=dec(text(sub, "TaxCategory/Percent") or "0"),
                                 base=dec(text(sub, "TaxableAmount")), vat=dec(text(sub, "TaxAmount"))))
        return rows

    def totals(self):
        got = {}
        m = find(self.root, "LegalMonetaryTotal")
        for el in (list(m) if m is not None else []):
            name = self.TOTALS.get(el.tag.split("}")[-1])
            if name:
                got[name] = dec(el.text)
        for total in self.root.findall("{*}TaxTotal"):
            amount = total.find("{*}TaxAmount")
            if amount is not None and amount.get("currencyID") in (None, "", self.currency):
                got["TaxTotalAmount"] = dec(amount.text)
        return got


def load(path):
    xml = xml_for(path)
    if xml is None:
        return None, None, "no Cross Industry Invoice XML beside %s" % Path(path).name
    try:
        root_tag = ET.parse(xml).getroot().tag
    except (ET.ParseError, OSError) as e:
        return xml, None, "%s is not readable XML: %s" % (xml.name, e)
    if root_tag.endswith("}Invoice") and "ebinterface.at" in root_tag:
        return None, None, "%s is ebInterface 6.1 (DocumentType CreditMemo for a credit); EINV-EBINTERFACE " \
                           "validates it and the page carries the reference" % xml.name
    national = {"{http://www.facturae.gob.es/formato/Versiones/Facturaev3_2_2.xml}Facturae":
                    ("Facturae 3.2.2 (InvoiceClass OR for a rectifying invoice, written as the difference)", "EINV-FACTURAE"),
                "{http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2}FatturaElettronica":
                    ("FatturaPA 1.2.3 (TipoDocumento TD04 for a credit note)", "EINV-FATTURAPA"),
                "{http://crd.gov.pl/wzor/2025/06/25/13775/}Faktura":
                    ("KSeF FA(3) (RodzajFaktury KOR for a correcting invoice, written as the difference)", "EINV-KSEF")}
    if root_tag in national:
        return None, None, "%s is %s; %s validates it and the country's own rule reads the reference" % (
            xml.name, national[root_tag][0], national[root_tag][1])
    if root_tag == "Finvoice":
        return None, None, "%s is Finvoice 3.0, which states a credit note with minus signs; " \
                           "EINV-FINVOICE validates it and the page carries the reference" % xml.name
    if root_tag in UBL_ROOTS:
        try:
            return xml, UblInvoice(xml), ""
        except (ValueError, AttributeError) as e:
            return xml, None, "%s is not a readable UBL invoice: %s" % (xml.name, e)
    try:
        return xml, Invoice(xml), ""
    except (ET.ParseError, ValueError, AttributeError) as e:
        return xml, None, "%s is not a readable Cross Industry Invoice: %s" % (xml.name, e)


def date_forms(iso_date):
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", iso_date or "")
    if not m:
        return [iso_date] if iso_date else []
    y, mo, d = m.groups()
    return [iso_date, "%s.%s.%s" % (d, mo, y), "%s/%s/%s" % (d, mo, y), "%s-%s-%s" % (d, mo, y), y + mo + d,
            "%d.%d.%s" % (int(d), int(mo), y), "%s/%s/%s" % (mo, d, y),
            # CLDR es writes d/M/y (30/9/2026), CLDR pl d.MM.y (5.09.2026), CLDR nl-BE d/MM/y (5/09/2026).
            "%d/%d/%s" % (int(d), int(mo), y), "%d.%s.%s" % (int(d), mo, y), "%d/%s/%s" % (int(d), mo, y)]


# ---- the rules -------------------------------------------------------------------------------

def credit_type(inv, src, page):
    problems = []
    if asks_credit(src) and inv.code != "381":
        problems.append("the order is a credit note and the XML's invoice type code (BT-3) is %s; a credit note is 381"
                        % (inv.code or "missing"))
    if not inv.number:
        problems.append("the credit note has no number of its own (BT-1)")
    prev = inv.preceding()
    if prev and inv.number and prev[0] and inv.number == prev[0]:
        problems.append("the credit note reuses the number %s of the invoice it amends; it needs its own (BT-1)" % inv.number)
    if src.get("number") and inv.number and str(src["number"]) != inv.number:
        problems.append("the credit note number is %s and the order says %s" % (inv.number, src["number"]))
    if page is not None and not CREDIT_WORDS.search(page_text(page)):
        problems.append("the page %s never calls itself a credit note" % page.name)
    return (not problems, "; ".join(problems) or "type 381, number %s%s" % (
        inv.number, ", the page headed as a credit note" if page is not None else ""))


def credit_ref(inv, src, page):
    problems = []
    prev = inv.preceding()
    want_no, want_date = src.get("preceding_invoice"), src.get("preceding_invoice_date")
    if not prev or not prev[0]:
        if not want_no:
            return False, ("a credit note names the invoice it amends and neither the order nor the XML gives it; "
                           "ask for the original invoice number and date (BT-25, BT-26)")
        return False, "no preceding invoice reference in the XML (BG-3 with BT-25, BR-55); the order names %s" % want_no
    number, date = prev
    if want_no and str(want_no) != number:
        problems.append("the XML names invoice %s and the order %s" % (number, want_no))
    if not date:
        problems.append("the original invoice's date (BT-26) is not in the XML%s"
                        % ("; the order gives %s" % want_date if want_date else "; ask for it"))
    elif want_date and str(want_date) != date:
        problems.append("the original invoice's date is %s in the XML and %s in the order" % (date, want_date))
    if page is not None:
        flat = page_text(page)
        if number not in flat:
            problems.append("the page does not name the original invoice %s" % number)
        if date and not any(f in flat for f in date_forms(date)):
            problems.append("the page does not give the original invoice's date %s" % date)
    return (not problems, "; ".join(problems) or "amends invoice %s of %s%s" % (
        number, date, ", on the page as well" if page is not None else ""))


def credit_sign(inv):
    bad = []
    for el in inv.root.iter():
        name = el.tag.split("}")[-1]
        if name in AMOUNTS:
            v = dec(el.text)
            if v is not None and v < 0:
                bad.append("%s %s" % (name, el.text.strip()))
    return (not bad, "every amount and quantity is positive" if not bad else
            "negative on a credit note, where the type code 381 already carries the sign: %s" % ", ".join(bad[:5]))


def credit_vat(inv, src):
    problems = []
    lines = inv.lines()
    groups = {}
    for l in lines:
        if l["net"] is None:
            problems.append("line %r has no net amount (BT-131)" % l["name"])
            continue
        key = (l["cat"], (l["rate"] or Decimal(0)).normalize())
        groups[key] = groups.get(key, Decimal(0)) + l["net"]
    rows = inv.breakdown()
    if not rows:
        problems.append("no VAT breakdown (BG-23); an invoice has at least one (BR-CO-18)")
    seen = {}
    for row in rows:
        key = (row["cat"], (row["rate"] or Decimal(0)).normalize())
        if key in seen:
            problems.append("two VAT breakdowns for category %s at %s %%; one per category and rate" % key)
        seen[key] = row
        if key not in groups:
            problems.append("a VAT breakdown for category %s at %s %% that no line carries" % key)
            continue
        if not same(row["base"], groups[key]):
            problems.append("category %s at %s %%: taxable amount %s, the lines sum to %s (BR-%s-08)"
                            % (key[0], key[1], row["base"], r2(groups[key]), key[0]))
        if row["base"] is not None and not same(row["vat"], r2(row["base"] * key[1] / 100)):
            problems.append("category %s at %s %%: VAT %s, the rate gives %s (BR-CO-17)"
                            % (key[0], key[1], row["vat"], r2(row["base"] * key[1] / 100)))
    for key in groups:
        if key not in seen:
            problems.append("lines at category %s, %s %% have no VAT breakdown (BR-CO-18)" % key)
    tot = inv.totals()
    line_sum = sum((l["net"] for l in lines if l["net"] is not None), Decimal(0))
    if not same(tot.get("LineTotalAmount"), line_sum):
        problems.append("sum of line nets is %s, the total states %s (BR-CO-10)" % (r2(line_sum), tot.get("LineTotalAmount")))
    basis = (tot.get("LineTotalAmount") or Decimal(0)) - (tot.get("AllowanceTotalAmount") or 0) + (tot.get("ChargeTotalAmount") or 0)
    if not same(tot.get("TaxBasisTotalAmount"), basis):
        problems.append("total without VAT is %s, the lines less allowances plus charges give %s (BR-CO-13)"
                        % (tot.get("TaxBasisTotalAmount"), r2(basis)))
    vat_sum = sum((r["vat"] for r in rows if r["vat"] is not None), Decimal(0))
    if not same(tot.get("TaxTotalAmount"), vat_sum):
        problems.append("total VAT is %s, the breakdown sums to %s (BR-CO-14)" % (tot.get("TaxTotalAmount"), r2(vat_sum)))
    if tot.get("TaxBasisTotalAmount") is not None and not same(tot.get("GrandTotalAmount"),
                                                                tot["TaxBasisTotalAmount"] + (tot.get("TaxTotalAmount") or 0)):
        problems.append("total with VAT is %s, without VAT plus VAT gives %s (BR-CO-15)"
                        % (tot.get("GrandTotalAmount"), r2(tot["TaxBasisTotalAmount"] + (tot.get("TaxTotalAmount") or 0))))
    if tot.get("GrandTotalAmount") is not None:
        due = tot["GrandTotalAmount"] - (tot.get("TotalPrepaidAmount") or 0) + (tot.get("RoundingAmount") or 0)
        if not same(tot.get("DuePayableAmount"), due):
            problems.append("amount due is %s, the totals give %s (BR-CO-16)" % (tot.get("DuePayableAmount"), r2(due)))
    # The case's own lines, when it gives them: the groups the file states are the ones the order makes.
    want = {}
    for l in src.get("lines") or []:
        try:
            q, p = Decimal(str(l["quantity"])), Decimal(str(l["unit_price"]))
        except (KeyError, InvalidOperation):
            want = {}
            break
        d = Decimal(str(l.get("discount_percent") or 0))
        key = (str(l.get("vat_category") or "S").upper(), Decimal(str(l.get("vat_rate") or 0)).normalize())
        want[key] = want.get(key, Decimal(0)) + r2(q * p * (1 - d / 100))
    for key, base in want.items():
        row = seen.get(key)
        if row is None:
            problems.append("the order has lines at category %s, %s %% and the XML no VAT breakdown for them" % key)
        elif not same(row["base"], base):
            problems.append("category %s at %s %%: taxable amount %s, the order's lines give %s" % (key[0], key[1], row["base"], r2(base)))
    if want:
        problems += ["a VAT group for category %s at %s %% that the order's lines do not credit" % key
                     for key in seen if key not in want]
    return (not problems, "; ".join(problems[:6]) or "%d VAT group(s), each once per category and rate; totals add up"
            % len(rows))


def xrechnung(inv, src):
    asked = bool(src.get("xrechnung")) or "xrechnung" in inv.spec_id.lower()
    if not asked:
        return None, "the buyer does not ask for XRechnung"
    if getattr(inv, "ubl", False):
        return False, "the buyer asks for XRechnung and the XML is UBL; this pack writes XRechnung as CII (\"syntax\": \"cii\")"
    problems = []
    if inv.spec_id != XRECHNUNG_ID:
        problems.append("BR-DE-21 the specification identifier (BT-24) is %r, XRechnung 3.0 is %s"
                        % (inv.spec_id, XRECHNUNG_ID))
    ref = text(inv.agr, "BuyerReference")
    if not ref:
        problems.append("BR-DE-15 no buyer reference (BT-10; a public buyer's Leitweg-ID)")
    elif src.get("buyer_reference") and str(src["buyer_reference"]) != ref:
        problems.append("BR-DE-15 the buyer reference is %s and the order says %s" % (ref, src["buyer_reference"]))
    means = inv.st.findall("{*}SpecifiedTradeSettlementPaymentMeans")
    if not means:
        problems.append("BR-DE-1 no payment instructions (BG-16)")
    for m in means:
        if text(m, "TypeCode") in ("30", "58") and find(m, "PayeePartyCreditorFinancialAccount") is None:
            problems.append("BR-DE-23-a a credit transfer (code %s) without the account (BG-17)" % text(m, "TypeCode"))
    seller = find(inv.agr, "SellerTradeParty")
    contact = find(seller, "DefinedTradeContact")
    if contact is None:
        problems.append("BR-DE-2 no seller contact (BG-6)")
    else:
        if not (text(contact, "PersonName") or text(contact, "DepartmentName")):
            problems.append("BR-DE-5 no seller contact point (BT-41)")
        if not text(contact, "TelephoneUniversalCommunication/CompleteNumber"):
            problems.append("BR-DE-6 no seller contact phone (BT-42)")
        if not text(contact, "EmailURIUniversalCommunication/URIID"):
            problems.append("BR-DE-7 no seller contact email (BT-43)")
    for rule_city, rule_code, party in (("BR-DE-3", "BR-DE-4", "SellerTradeParty"), ("BR-DE-8", "BR-DE-9", "BuyerTradeParty")):
        address = find(inv.agr, party + "/PostalTradeAddress")
        who = "seller" if party.startswith("Seller") else "buyer"
        if not text(address, "CityName"):
            problems.append("%s no %s city" % (rule_city, who))
        if not text(address, "PostcodeCode"):
            problems.append("%s no %s post code" % (rule_code, who))
    return (not problems, "; ".join(problems) or "the XRechnung rules hold: buyer reference %s, payment "
            "instructions, seller contact with name, phone and email" % ref)


def check(rule_id, path, case, stage):
    if rule_id not in ("INV-CREDIT-TYPE", "INV-CREDIT-REF", "INV-CREDIT-SIGN", "INV-CREDIT-VAT", "INV-XRECHNUNG"):
        return None, "unknown rule %s" % rule_id
    src = wanted(path, case, stage)
    xml, inv, why = load(path)
    if inv == "finvoice":
        return None, why
    if inv is None:
        if xml is None and not (asks_credit(src) or src.get("xrechnung")):
            return None, why
        if xml is None:
            return None, why + "; the page alone carries no invoice data to check"
        return False, why
    if rule_id == "INV-XRECHNUNG":
        return xrechnung(inv, src)
    if not (asks_credit(src) or inv.code == "381"):
        return None, "an invoice (type %s), not a credit note" % (inv.code or "380")
    page = page_for(path)
    if rule_id == "INV-CREDIT-TYPE":
        return credit_type(inv, src, page)
    if rule_id == "INV-CREDIT-REF":
        return credit_ref(inv, src, page)
    if rule_id == "INV-CREDIT-SIGN":
        return credit_sign(inv)
    return credit_vat(inv, src)


if __name__ == "__main__":
    target = sys.argv[1]
    for rule in ("INV-CREDIT-TYPE", "INV-CREDIT-REF", "INV-CREDIT-SIGN", "INV-CREDIT-VAT", "INV-XRECHNUNG"):
        ok, why = check(rule, target, {}, "first")
        print(json.dumps({"rule": rule, "passed": ok, "evidence": why}, ensure_ascii=False))
