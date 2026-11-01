#!/usr/bin/env python3
"""Peppol BIS Billing 3.0 in UBL 2.1 from the same JSON spec: the invoice (Invoice) and the credit note
(CreditNote) Norway (EHF), Denmark (NemHandel), Finland and UK buyers on Peppol take.

    python3 ubl_create.py spec.json invoice.xml

The arithmetic is einvoice_create's: each line net is quantity x unit price less its discount, rounded to
two decimals; VAT once per category and rate on the sum of that group's nets. The elements follow the
UBL 2.1 schema's order (OASIS UBL 2.1, the Invoice and CreditNote documents) and the Peppol BIS Billing
3.0 syntax binding, which this file restates in its own code: OpenPeppol's terms do not allow its rules to
be copied, so none of them are; the official schematron runs untouched in the pack check (EINV-PEPPOL).

    BT-24  CustomizationID  urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0
    BT-23  ProfileID        urn:fdc:peppol.eu:2017:poacc:billing:01:1.0
    BT-34, BT-49  EndpointID with its EAS scheme (PEPPOL-EN16931-R010, R020): the spec's
                  electronic_address, else the business number under its country's scheme (0192 Norway,
                  0184 Denmark, 0216 Finland's OVT code, 9932 a UK VAT number), with a warning
    BT-30  PartyLegalEntity/CompanyID under its ICD (0192, 0184, 0212)
    Norway: PartyTaxScheme "Foretaksregisteret" under TaxScheme TAX for an AS, ASA or NUF (NO-R-002);
            the VAT number NO<org.nr.>MVA (NO-R-001); the KID as PaymentID (BT-83)
    Denmark: the CVR under 0184 (DK-R-002, DK-R-014); a bank transfer (42) with the registration number
            as FinancialInstitutionBranch (DK-R-006)
    Finland: the Y-tunnus under 0212, the viitenumero as PaymentID
    Belgium: the enterprise number under 0208 as Peppol address and legal ID (PEPPOL-COMMON-R043 checks its
            modulus 97), the structured communication's twelve digits as PaymentID
    Netherlands: the KvK number under 0106 (NL-R-003, NL-R-005), a payment means always (NL-R-007)
    Austria: the UID-Nummer under 9914, the Firmenbuchnummer as legal ID; Ireland: the VAT number under 9935

With "syntax": "si-ubl" a Dutch seller gets SI-UBL 2.0, the NLCIUS (CustomizationID
urn:cen.eu:en16931:2017#compliant#urn:fdc:nen.nl:nlcius:v1.0) the Dutch government takes. Its rules come
from the Nederlandse Peppol Autoriteit's validation artefacts (MIT, Stichting Simplerinvoicing), ported
with credit: BR-NL-1 and -10 the KvK under 0106, BR-NL-2 a buyer or order reference, BR-NL-3 and -4 street,
city and postcode, BR-NL-11 and -12 a payment means 30, 48, 49, 57, 58 or 59, and the fields BR-NL-26,
-30, -31 and -32 advise against (the legal form text, the account name, a bank branch for a SEPA transfer,
an allowance reason code) left out. The official si-ubl-2.0.xsl runs untouched in EINV-SI-UBL.

Standard library only. Prints a JSON summary with the totals.
"""
import argparse
import io
import json
import sys
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import einvoice_create as cii  # noqa: E402
import countries  # noqa: E402

INV = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
CN = "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"
CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
CUSTOMIZATION = "urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0"
PROFILE = "urn:fdc:peppol.eu:2017:poacc:billing:01:1.0"
NLCIUS = "urn:cen.eu:en16931:2017#compliant#urn:fdc:nen.nl:nlcius:v1.0"
EXEMPT = ("AE", "E", "K", "G", "O")


def cbc(parent, tag, text=None, **attrs):
    e = ET.SubElement(parent, "{%s}%s" % (CBC, tag), {k: str(v) for k, v in attrs.items()})
    if text is not None:
        e.text = str(text)
    return e


def cac(parent, tag):
    return ET.SubElement(parent, "{%s}%s" % (CAC, tag))


def amt(parent, tag, value, cur):
    return cbc(parent, tag, cii.r2(value), currencyID=cur)


def num(d):
    d = Decimal(str(d))
    return int(d) if d == d.to_integral_value() else d.normalize()


def address(parent, tag, p):
    a = cac(parent, tag)
    if p.get("street"):
        cbc(a, "StreetName", p["street"])
    if p.get("city"):
        cbc(a, "CityName", p["city"])
    if p.get("postcode"):
        cbc(a, "PostalZone", p["postcode"])
    cbc(cac(a, "Country"), "IdentificationCode", countries.country(p) or "")
    return a


def legal_info(p, c):
    """BT-33, the seller's additional legal information, in the seller's own words: its legal form and
    registered office, the way its letters state them (Directive (EU) 2017/1132 Art. 26)."""
    words = {"NO": "Hovedkontor", "DK": "Hjemsted", "FI": "Kotipaikka", "GB": "Registered office",
             "NL": "Statutaire zetel", "AT": "Sitz", "IE": "Registered office"}
    if c == "BE":
        words["BE"] = {"nl-BE": "Zetel", "fr-BE": "Siège", "de-BE": "Sitz"}[countries.ids.be_region_locale(p.get("postcode"))[0]]
    parts = [countries.legal_form(p)]
    if p.get("registered_office"):
        parts.append("%s: %s" % (words.get(c, "Registered office"), p["registered_office"]))
    if c == "GB" and p.get("register_number"):
        parts.append("Company number %s" % p["register_number"])
    if c == "BE" and p.get("register"):
        parts.append(str(p["register"]))
    if c == "AT" and p.get("register_number"):
        parts.append(", ".join(x for x in (countries.ids.at_fn_text(p["register_number"]), p.get("register")) if x))
    if c == "IE" and p.get("register_number"):
        parts.append("Registered in Ireland, company number %s" % p["register_number"])
    return "; ".join(x for x in parts if x)


def party(parent, tag, spec, role):
    p = spec.get(role) or {}
    c = countries.country(p)
    party_el = cac(cac(parent, tag), "Party")
    scheme, ident, _why = countries.endpoint(spec, role)
    if ident:
        cbc(party_el, "EndpointID", ident, schemeID=scheme)
    if p.get("trading_name"):
        cbc(cac(party_el, "PartyName"), "Name", p["trading_name"])
    address(party_el, "PostalAddress", p)
    v = countries.vat_id(p)
    if v:
        ts = cac(party_el, "PartyTaxScheme")
        cbc(ts, "CompanyID", v)
        cbc(cac(ts, "TaxScheme"), "ID", "VAT")
    if role == "seller" and c == "NO" and countries.legal_form(p).upper() in countries.NO_FORETAK:
        # NO-R-002: the word the Norwegian company register asks for (bokføringsforskriften § 5-1-2, which
        # still points at § 10-2 of the repealed 1985 act; foretaksregisterloven 2025 § 7-2 now asks for the register).
        ts = cac(party_el, "PartyTaxScheme")
        cbc(ts, "CompanyID", "Foretaksregisteret")
        cbc(cac(ts, "TaxScheme"), "ID", "TAX")
    le = cac(party_el, "PartyLegalEntity")
    cbc(le, "RegistrationName", p.get("name", ""))
    number = countries.org_number(p, c) or (p.get("register_number") if c in ("GB", "SE", "AT", "IE") else "")
    if c == "AT" and number:
        number = countries.ids.at_fn_text(number)
    if number:
        if c in countries.ICD:
            value = number if c == "FI" else (countries.ids.be_enterprise_digits(number) if c == "BE"
                                              else countries.ids.digits(number))
            cbc(le, "CompanyID", value, schemeID=countries.ICD[c])
        else:
            cbc(le, "CompanyID", number)
    if role == "seller":
        info = "" if spec.get("_nlcius") else legal_info(p, c)
        if info:
            cbc(le, "CompanyLegalForm", info)
        name, phone, email = cii.contact_of(p)
        if name or phone or email:
            ct = cac(party_el, "Contact")
            if name:
                cbc(ct, "Name", name)
            if phone:
                cbc(ct, "Telephone", phone)
            if email:
                cbc(ct, "ElectronicMail", email)
    elif p.get("contact_name"):
        cbc(cac(party_el, "Contact"), "Name", p["contact_name"])


def reason_for(cat, g, spec):
    c = countries.seller_country(spec)
    if cat == "AE":
        if c in ("BE", "NL", "AT", "IE") and not g["reason"]:
            lang = {"NL": "nl-NL", "AT": "de-AT", "IE": "en-IE"}.get(c) or countries.ids.be_region_locale(
                (spec.get("seller") or {}).get("postcode"))[0]
            return countries.REVERSE[lang]
        return g["reason"] or {"NO": countries.NO_REVERSE, "DK": "Omvendt betalingspligt",
                               "FI": "Käännetty verovelvollisuus"}.get(c, "Reverse charge")
    return g["reason"] or "Exempt"


def tax_category(parent, tag, cat, rate, reason=None, code=None):
    t = cac(parent, tag)
    cbc(t, "ID", cat)
    if cat != "O":
        cbc(t, "Percent", num(rate))
    if code:
        cbc(t, "TaxExemptionReasonCode", code)
    if reason:
        cbc(t, "TaxExemptionReason", reason)
    cbc(cac(t, "TaxScheme"), "ID", "VAT")


def payment(root, spec, credit):
    pay = spec.get("payment") or {}
    if not pay:
        return
    pm = cac(root, "PaymentMeans")
    code = str(pay.get("means_code") or ("58" if pay.get("iban") else "30"))
    cbc(pm, "PaymentMeansCode", code)
    if credit and spec.get("due_date"):
        cbc(pm, "PaymentDueDate", spec["due_date"])
    ref = pay.get("kid") or pay.get("reference")
    if ref and countries.seller_country(spec) == "BE" and countries.ids.be_ogm_ok(ref):
        # The structured communication travels as its twelve digits; the page prints it +++123/4567/89012+++.
        ref = countries.ids.digits(ref)
    if ref:
        cbc(pm, "PaymentID", str(ref).replace(" ", ""))
    account = (pay.get("iban") or "").replace(" ", "") or countries.ids.digits(pay.get("account"))
    if account:
        fa = cac(pm, "PayeeFinancialAccount")
        cbc(fa, "ID", account)
        if pay.get("account_name") and not spec.get("_nlcius"):
            cbc(fa, "Name", pay["account_name"])
        branch = pay.get("bic") or pay.get("bank_reg") or pay.get("sort_code")
        if branch and not (spec.get("_nlcius") and code in ("58", "59")):
            cbc(cac(fa, "FinancialInstitutionBranch"), "ID", str(branch).replace(" ", "").replace("-", ""))


def build(spec):
    warnings = cii.refuse(spec)
    missing, more = countries.refuse(spec)
    if missing:
        raise SystemExit("the spec lacks what this document needs; ask the person for it, never guess:\n  - "
                         + "\n  - ".join(missing))
    warnings += more
    lines, groups, money = cii.compute_full(spec)
    tax, net_total, tax_total, gross = money["tax"], money["basis"], money["tax_total"], money["grand"]
    credit = cii.type_code(spec) == "381"
    cur = spec.get("currency", "EUR")
    for prefix, ns in (("cac", CAC), ("cbc", CBC)):
        ET.register_namespace(prefix, ns)
    ET.register_namespace("", CN if credit else INV)
    root = ET.Element("{%s}%s" % (CN if credit else INV, "CreditNote" if credit else "Invoice"))
    cbc(root, "CustomizationID", NLCIUS if spec.get("_nlcius") else CUSTOMIZATION)
    cbc(root, "ProfileID", PROFILE)
    cbc(root, "ID", spec["number"])
    cbc(root, "IssueDate", spec["issue_date"])
    if credit:
        cbc(root, "CreditNoteTypeCode", "381")
    else:
        if spec.get("due_date"):
            cbc(root, "DueDate", spec["due_date"])
        cbc(root, "InvoiceTypeCode", cii.type_code(spec))
    if spec.get("note"):
        cbc(root, "Note", spec["note"])
    cbc(root, "DocumentCurrencyCode", cur)
    tax_cur = spec.get("tax_currency")
    national = countries.NATIONAL_CURRENCY.get(countries.seller_country(spec))
    if not tax_cur and national and national != cur:
        tax_cur = national
    if tax_cur and tax_cur != cur:
        cbc(root, "TaxCurrencyCode", tax_cur)
    if spec.get("buyer_reference"):
        cbc(root, "BuyerReference", spec["buyer_reference"])
    if spec.get("order_reference"):
        cbc(cac(root, "OrderReference"), "ID", spec["order_reference"])
    if spec.get("preceding_invoice"):
        ref = cac(cac(root, "BillingReference"), "InvoiceDocumentReference")
        cbc(ref, "ID", spec["preceding_invoice"])
        if spec.get("preceding_invoice_date"):
            cbc(ref, "IssueDate", spec["preceding_invoice_date"])
    party(root, "AccountingSupplierParty", spec, "seller")
    party(root, "AccountingCustomerParty", spec, "buyer")
    dlv = cac(root, "Delivery")
    cbc(dlv, "ActualDeliveryDate", spec.get("delivery_date") or spec["issue_date"])
    ship = spec.get("delivery_address")
    if isinstance(ship, dict) and (ship.get("street") or ship.get("city")):
        loc = cac(dlv, "DeliveryLocation")
        address(loc, "Address", dict(ship, country=ship.get("country") or countries.country(spec["buyer"])))
        if ship.get("name"):
            cbc(cac(cac(dlv, "DeliveryParty"), "PartyName"), "Name", ship["name"])
    payment(root, spec, credit)
    if spec.get("payment_terms"):
        cbc(cac(root, "PaymentTerms"), "Note", spec["payment_terms"])
    for a in money["allowances"]:
        # An allowance on the whole document (BG-20): amount BT-92, base BT-93, percentage BT-94, reason BT-97,
        # reason code BT-98 and the VAT category and rate it reduces (BT-95, BT-96).
        ac = cac(root, "AllowanceCharge")
        cbc(ac, "ChargeIndicator", "false")
        if a["code"] and not spec.get("_nlcius"):
            cbc(ac, "AllowanceChargeReasonCode", a["code"])
        if a["reason"]:
            cbc(ac, "AllowanceChargeReason", a["reason"])
        if a["percent"] is not None:
            cbc(ac, "MultiplierFactorNumeric", num(a["percent"]))
        amt(ac, "Amount", a["amount"], cur)
        if a["base"] is not None:
            amt(ac, "BaseAmount", a["base"], cur)
        tax_category(ac, "TaxCategory", a["cat"], a["rate"])
    tt = cac(root, "TaxTotal")
    amt(tt, "TaxAmount", tax_total, cur)
    for (cat, rate), g in sorted(groups.items(), key=lambda kv: (kv[0][0], -kv[0][1])):
        sub = cac(tt, "TaxSubtotal")
        amt(sub, "TaxableAmount", g["base"], cur)
        amt(sub, "TaxAmount", tax[(cat, rate)], cur)
        tax_category(sub, "TaxCategory", cat, rate, reason_for(cat, g, spec) if cat in EXEMPT else None, g.get("code"))
    if tax_cur and tax_cur != cur:
        if not spec.get("exchange_rate"):
            raise SystemExit("the VAT must also be stated in %s: give exchange_rate, the rate the order uses" % tax_cur)
        amt(cac(root, "TaxTotal"), "TaxAmount", tax_total * Decimal(str(spec["exchange_rate"])), tax_cur)
    tot = cac(root, "LegalMonetaryTotal")
    amt(tot, "LineExtensionAmount", money["line_total"], cur)
    amt(tot, "TaxExclusiveAmount", net_total, cur)
    amt(tot, "TaxInclusiveAmount", gross, cur)
    if money["allowances"]:
        amt(tot, "AllowanceTotalAmount", money["allowance_total"], cur)
    if money["paid"]:
        amt(tot, "PrepaidAmount", money["paid"], cur)
    amt(tot, "PayableAmount", money["due"], cur)
    for l, src in zip(lines, spec["lines"]):
        line = cac(root, "CreditNoteLine" if credit else "InvoiceLine")
        cbc(line, "ID", l["id"])
        cbc(line, "CreditedQuantity" if credit else "InvoicedQuantity", num(l["qty"]), unitCode=l["unit"])
        amt(line, "LineExtensionAmount", l["net"], cur)
        if l["disc"]:
            # A line discount as a line allowance (BG-27): the price stays the list price (BT-146) and the
            # line net is quantity x price less the allowance (PEPPOL-EN16931-R120). BT-138 the percentage
            # (when the order gave one), BT-136 the amount, BT-137 the amount it is taken off, BT-139 the
            # reason and BT-140 its UNCL 5189 code.
            ac = cac(line, "AllowanceCharge")
            cbc(ac, "ChargeIndicator", "false")
            if not spec.get("_nlcius"):
                cbc(ac, "AllowanceChargeReasonCode", l["disc_code"] or "95")
            cbc(ac, "AllowanceChargeReason", l["disc_reason"] or "Discount")
            if l["pct"]:
                cbc(ac, "MultiplierFactorNumeric", num(l["pct"]))
            amt(ac, "Amount", l["disc"], cur)
            if l["pct"]:
                amt(ac, "BaseAmount", l["base"], cur)       # BT-137 goes with BT-138 (PEPPOL-EN16931-R041, -R042)
        item = cac(line, "Item")
        if src.get("description"):
            cbc(item, "Description", src["description"])
        cbc(item, "Name", l["name"])
        if src.get("sku"):
            cbc(cac(item, "SellersItemIdentification"), "ID", src["sku"])
        if l.get("origin"):
            cbc(cac(item, "OriginCountry"), "IdentificationCode", l["origin"])          # BT-159
        if l.get("hs"):
            cbc(cac(item, "CommodityClassification"), "ItemClassificationCode", l["hs"], listID="HS")  # BT-158
        tax_category(item, "ClassifiedTaxCategory", l["cat"], l["rate"])
        price = cac(line, "Price")
        cbc(price, "PriceAmount", num(l["price"]), currencyID=cur)
    summary = dict(syntax="si-ubl" if spec.get("_nlcius") else "ubl",
                   profile="SI-UBL 2.0 (NLCIUS)" if spec.get("_nlcius") else "Peppol BIS Billing 3.0", type_code=cii.type_code(spec), lines=len(lines),
                   total_excluding_vat=str(cii.r2(net_total)), total_vat=str(cii.r2(tax_total)),
                   total_including_vat=str(cii.r2(gross)), **cii.money_summary(money),
                   vat=[dict(category=c, rate=str(r), taxable=str(cii.r2(g["base"])), vat=str(tax[(c, r)]))
                        for (c, r), g in groups.items()])
    if warnings:
        summary["warnings"] = warnings
    return root, summary


def xml_bytes(spec, nlcius=False):
    if nlcius:
        spec = dict(spec, _nlcius=True)
    root, summary = build(spec)
    ET.indent(root)
    out = io.BytesIO()
    ET.ElementTree(root).write(out, encoding="UTF-8", xml_declaration=True)
    return out.getvalue(), summary


def main(argv=None):
    ap = argparse.ArgumentParser(description="Create a Peppol BIS Billing 3.0 UBL invoice or credit note from a JSON spec.")
    ap.add_argument("spec")
    ap.add_argument("output")
    a = ap.parse_args(argv)
    spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    data, summary = xml_bytes(spec)
    Path(a.output).write_bytes(data)
    print(json.dumps(dict(ok=True, output=a.output, **summary), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
