#!/usr/bin/env python3
"""Facturae 3.2.2, the Spanish state's e-invoice, from the same JSON spec: the factura and the factura
rectificativa.

    python3 facturae_create.py spec.json invoice.xml

Facturae is the structured format invoices to Spanish public bodies take (Ley 25/2013 art. 5 and disposición
adicional segunda); facturae.gob.es publishes the schema and lets its contents be reused under Ley 37/2007
with the source named (Origen de los datos: Ministerio de Hacienda y Administraciones Públicas - Ministerio de
Industria, Energía y Turismo). Nothing of the schema is copied here: this file writes the elements version
3.2.2 defines, in its order, in our own code, and the official Facturaev3_2_2.xml is fetched at a pinned
SHA-256 and runs untouched in the pack check (EINV-FACTURAE).

THE FILE IS NOT SIGNED. A public entry point such as FACe takes a Facturae only with an XAdES signature made
with the seller's certificate; this pack makes none and writes no ds:Signature element. The file is the data
to sign, never a stand-in for a signed invoice.

The arithmetic is einvoice_create's: line nets rounded to two decimals, IVA once per rate on the sum of that
rate's nets. A rectifying invoice (InvoiceClass OR, Real Decreto 1619/2012 art. 15) is written as the
difference itself, CorrectionMethod 02: its quantities and amounts are minus what the order credits, its
series is its own (art. 6.1 a 2.º) and its Corrective block names the invoice it rectifies (art. 15.4).
Standard library only. Prints a JSON summary with the totals.
"""
import argparse
import io
import json
import re
import sys
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import einvoice_create as cii  # noqa: E402
import countries  # noqa: E402

ids = countries.ids
NS = "http://www.facturae.gob.es/formato/Versiones/Facturaev3_2_2.xml"
# ISO 3166-1 alpha-3, which Facturae's CountryCode takes; a country that is not here is named by the order
# ("country_alpha3").
ALPHA3 = {"ES": "ESP", "PT": "PRT", "FR": "FRA", "DE": "DEU", "IT": "ITA", "GB": "GBR", "IE": "IRL", "NL": "NLD",
          "BE": "BEL", "LU": "LUX", "AT": "AUT", "CH": "CHE", "PL": "POL", "SE": "SWE", "DK": "DNK", "NO": "NOR",
          "FI": "FIN", "CZ": "CZE", "SK": "SVK", "HU": "HUN", "RO": "ROU", "BG": "BGR", "GR": "GRC", "HR": "HRV",
          "SI": "SVN", "EE": "EST", "LV": "LVA", "LT": "LTU", "CY": "CYP", "MT": "MLT", "AD": "AND", "US": "USA",
          "CA": "CAN", "MX": "MEX", "AU": "AUS", "MA": "MAR", "AR": "ARG", "CL": "CHL", "CO": "COL"}
EU = ("AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "FI", "FR", "GR", "HR", "HU", "IE", "IT", "LT", "LU", "LV",
      "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK")
# UN/ECE Rec 20 to Facturae's UnitOfMeasure: 01 units, 02 hours, 03 kilograms, 04 litres, 05 other.
UNITS = {"C62": "01", "H87": "01", "HUR": "02", "KGM": "03", "LTR": "04"}
# EN 16931 payment means (UNCL 4461) to Facturae's PaymentMeans: 04 a credit transfer, 02 a direct debit,
# 01 cash, 19 a card.
MEANS = {"30": "04", "58": "04", "42": "04", "49": "02", "59": "02", "10": "01", "48": "19", "54": "19", "55": "19"}


def sub(parent, tag, text=None):
    e = ET.SubElement(parent, tag)
    if text is not None:
        e.text = str(text)
    return e


def d2(x):
    return str(cii.r2(x))


def d8(x):
    text = format(Decimal(str(x)).quantize(Decimal("0.00000001")).normalize(), "f")
    return text if "." in text and len(text.split(".")[1]) >= 2 else d2(x)


def amount(parent, tag, value, rate=None):
    e = sub(parent, tag)
    sub(e, "TotalAmount", d2(value))
    if rate:
        sub(e, "EquivalentInEuros", d2(Decimal(str(value)) * Decimal(str(rate))))
    return e


def alpha3(p):
    code = str(p.get("country_alpha3") or ALPHA3.get(countries.country(p)) or "").upper()
    if not re.fullmatch(r"[A-Z]{3}", code):
        raise SystemExit("country %s: Facturae writes the country as three letters (ISO 3166-1 alpha-3); give it as "
                         "country_alpha3" % p.get("country"))
    return code


def party(parent, tag, p):
    el = sub(parent, tag)
    cc = countries.country(p)
    raw = str(p.get("vat_id") or "")
    number = ids.es_nif(raw) if cc == "ES" else re.sub(r"[\s.]", "", raw).upper()
    person = cc == "ES" and ids.es_nif_form(number) and ids.es_nif_person(number) or bool(p.get("person"))
    tax = sub(el, "TaxIdentification")
    sub(tax, "PersonTypeCode", "F" if person else "J")
    sub(tax, "ResidenceTypeCode", "R" if cc == "ES" else "U" if cc in EU else "E")
    sub(tax, "TaxIdentificationNumber", number)
    name = str(p.get("name") or "")
    if person:
        body = sub(el, "Individual")
        first = p.get("first_name") or name.split(" ")[0]
        sub(body, "Name", str(first)[:40])
        sub(body, "FirstSurname", str(p.get("surname") or name[len(str(first)):].strip() or first)[:40])
        if p.get("second_surname"):
            sub(body, "SecondSurname", str(p["second_surname"])[:40])
    else:
        body = sub(el, "LegalEntity")
        sub(body, "CorporateName", name[:80])
        if p.get("trade_name"):
            sub(body, "TradeName", str(p["trade_name"])[:40])
    if cc == "ES":
        a = sub(body, "AddressInSpain")
        sub(a, "Address", str(p.get("street") or "")[:80])
        sub(a, "PostCode", p.get("postcode") or "")
        sub(a, "Town", str(p.get("city") or "")[:50])
        sub(a, "Province", str(p.get("province") or "")[:20])
    else:
        a = sub(body, "OverseasAddress")
        sub(a, "Address", str(p.get("street") or "")[:80])
        sub(a, "PostCodeAndTown", " ".join(x for x in (p.get("postcode"), p.get("city")) if x)[:50])
        sub(a, "Province", str(p.get("province") or p.get("state") or p.get("city") or "")[:20])
    sub(a, "CountryCode", alpha3(p))
    contact = p.get("contact") if isinstance(p.get("contact"), dict) else {}
    phone, mail, who = contact.get("phone") or p.get("phone"), contact.get("email") or p.get("email"), contact.get("name")
    if tag == "SellerParty" and (phone or mail or who):
        c = sub(body, "ContactDetails")
        if phone:
            sub(c, "Telephone", re.sub(r"[^\d+]", "", str(phone))[:15])
        if mail:
            sub(c, "ElectronicMail", str(mail)[:60])
        if who:
            sub(c, "ContactPersons", str(who)[:40])
    return el


def tax(parent, rate, base, vat, fx):
    t = sub(parent, "Tax")
    sub(t, "TaxTypeCode", "01")                       # 01 is IVA
    sub(t, "TaxRate", d2(rate))
    amount(t, "TaxableBase", base, fx)
    amount(t, "TaxAmount", vat, fx)
    return t


def build(spec):
    warnings = cii.refuse(spec)
    missing, more = countries.refuse(spec)
    if missing:
        raise SystemExit("the spec lacks what this document needs; ask the person for it, never guess:\n  - "
                         + "\n  - ".join(missing))
    warnings += more
    lines, groups, mny = cii.compute_full(spec)
    vat, net_total, tax_total, gross = mny["tax"], mny["basis"], mny["tax_total"], mny["grand"]
    credit = countries.is_credit(spec)
    sgn = countries.credit_sign(spec)
    if sgn < 0 and (mny["allowances"] or mny["paid"]):
        raise SystemExit("a rectifying invoice states its amounts with a minus sign: put a discount on the lines; leave out allowances and paid_amount")
    cur = str(spec.get("currency") or "EUR").upper()
    fx = spec.get("exchange_rate") if cur != "EUR" else None
    seller, buyer = spec.get("seller") or {}, spec.get("buyer") or {}
    ET.register_namespace("fe", NS)
    root = ET.Element("{%s}Facturae" % NS)
    head = sub(root, "FileHeader")
    sub(head, "SchemaVersion", "3.2.2")
    sub(head, "Modality", "I")
    sub(head, "InvoiceIssuerType", "EM")
    batch = sub(head, "Batch")
    sub(batch, "BatchIdentifier", ("%s%s%s" % (ids.es_nif(seller.get("vat_id")), spec["number"], spec.get("series") or ""))[:70])
    sub(batch, "InvoicesCount", 1)
    for tag in ("TotalInvoicesAmount", "TotalOutstandingAmount", "TotalExecutableAmount"):
        amount(batch, tag, sgn * gross, fx)
    sub(batch, "InvoiceCurrencyCode", cur)
    parties = sub(root, "Parties")
    party(parties, "SellerParty", seller)
    party(parties, "BuyerParty", buyer)
    inv = sub(sub(root, "Invoices"), "Invoice")
    ih = sub(inv, "InvoiceHeader")
    sub(ih, "InvoiceNumber", spec["number"])
    if spec.get("series"):
        sub(ih, "InvoiceSeriesCode", str(spec["series"])[:20])
    sub(ih, "InvoiceDocumentType", "FC")
    sub(ih, "InvoiceClass", "OR" if credit else "OO")
    if credit:
        corr = spec.get("correction") if isinstance(spec.get("correction"), dict) else {}
        c = sub(ih, "Corrective")
        sub(c, "InvoiceNumber", str(spec["preceding_invoice"])[:20])
        if spec.get("preceding_series"):
            sub(c, "InvoiceSeriesCode", str(spec["preceding_series"])[:20])
        code = str(corr.get("reason_code"))
        sub(c, "ReasonCode", code)
        sub(c, "ReasonDescription", countries.FACTURAE_REASONS[code])
        period = corr.get("period") if isinstance(corr.get("period"), dict) else {}
        tp = sub(c, "TaxPeriod")
        sub(tp, "StartDate", period.get("from") or spec["preceding_invoice_date"])
        sub(tp, "EndDate", period.get("to") or spec["preceding_invoice_date"])
        sub(c, "CorrectionMethod", "02")
        sub(c, "CorrectionMethodDescription", "Rectificación por diferencias")
        if spec.get("note"):
            sub(c, "AdditionalReasonDescription", str(spec["note"])[:2500])
        if spec.get("preceding_invoice_date"):
            sub(c, "InvoiceIssueDate", spec["preceding_invoice_date"])
    issue = sub(inv, "InvoiceIssueData")
    sub(issue, "IssueDate", spec["issue_date"])
    if spec.get("delivery_date") and spec["delivery_date"] != spec["issue_date"]:
        sub(issue, "OperationDate", spec["delivery_date"])
    sub(issue, "InvoiceCurrencyCode", cur)
    if fx:
        x = sub(issue, "ExchangeRateDetails")
        sub(x, "ExchangeRate", d8(fx))
        sub(x, "ExchangeRateDate", spec.get("exchange_rate_date") or spec["issue_date"])
    sub(issue, "TaxCurrencyCode", "EUR")
    sub(issue, "LanguageName", "es")
    if spec.get("note") and not credit:
        sub(issue, "InvoiceDescription", str(spec["note"])[:2500])
    if spec.get("order_reference"):
        sub(issue, "ReceiverTransactionReference", str(spec["order_reference"])[:20])
    ordered = sorted(groups.items(), key=lambda kv: (-kv[0][1], kv[0][0]))
    taxes = sub(inv, "TaxesOutputs")
    for (cat, rate), g in ordered:
        tax(taxes, rate, sgn * g["base"], sgn * vat[(cat, rate)], fx)
    tot = sub(inv, "InvoiceTotals")
    sub(tot, "TotalGrossAmount", d2(sgn * mny["line_total"]))
    if mny["allowances"]:
        # Discounts on the whole document (EN 16931-1 BG-20): Facturae GeneralDiscounts, taken off the total gross amount.
        gd = sub(tot, "GeneralDiscounts")
        for al in mny["allowances"]:
            dd = sub(gd, "Discount")
            sub(dd, "DiscountReason", str(al["reason"] or al["code"])[:2500])
            if al["percent"] is not None:
                sub(dd, "DiscountRate", d8(al["percent"]))
            sub(dd, "DiscountAmount", d2(al["amount"]))
        sub(tot, "TotalGeneralDiscounts", d2(mny["allowance_total"]))
    sub(tot, "TotalGrossAmountBeforeTaxes", d2(sgn * net_total))
    sub(tot, "TotalTaxOutputs", d2(sgn * tax_total))
    sub(tot, "TotalTaxesWithheld", "0.00")
    sub(tot, "InvoiceTotal", d2(sgn * gross))
    if mny["paid"]:
        # An amount paid in advance (BT-113): PaymentsOnAccount, dated, taken off what is outstanding (BT-115).
        if not spec.get("paid_date"):
            raise SystemExit('Facturae dates every payment on account: add "paid_date" (the day the advance was paid), '
                             'or ask the person for it')
        pa = sub(sub(tot, "PaymentsOnAccount"), "PaymentOnAccount")
        sub(pa, "PaymentOnAccountDate", spec["paid_date"])
        sub(pa, "PaymentOnAccountAmount", d2(mny["paid"]))
    sub(tot, "TotalOutstandingAmount", d2(sgn * mny["due"]))
    if mny["paid"]:
        sub(tot, "TotalPaymentsOnAccount", d2(mny["paid"]))
    sub(tot, "TotalExecutableAmount", d2(sgn * mny["due"]))
    items = sub(inv, "Items")
    literals = []
    for l, src in zip(lines, spec["lines"]):
        li = sub(items, "InvoiceLine")
        sub(li, "SequenceNumber", l["id"])
        sub(li, "ItemDescription", str(l["name"])[:2500])
        sub(li, "Quantity", d8(sgn * l["qty"]))
        sub(li, "UnitOfMeasure", UNITS.get(str(l["unit"]).upper(), "05"))
        sub(li, "UnitPriceWithoutTax", d8(l["price"]))
        cost = cii.r2(l["qty"] * l["price"])
        sub(li, "TotalCost", d2(sgn * cost))
        if cost != l["net"]:
            d = sub(sub(li, "DiscountsAndRebates"), "Discount")
            sub(d, "DiscountReason", "Descuento")
            if src.get("discount_percent"):
                sub(d, "DiscountRate", d8(src["discount_percent"]))
            sub(d, "DiscountAmount", d2(sgn * (cost - l["net"])))
        sub(li, "GrossAmount", d2(sgn * l["net"]))
        tax(sub(li, "TaxesOutputs"), l["rate"], sgn * l["net"], sgn * cii.r2(l["net"] * l["rate"] / 100), fx)
        reason = src.get("exemption_reason") or spec.get("exemption_reason")
        if l["cat"] in countries.UNTAXED and reason:
            ev = sub(li, "SpecialTaxableEvent")
            sub(ev, "SpecialTaxableEventCode", "02" if l["cat"] == "O" else "01")
            sub(ev, "SpecialTaxableEventReason", str(reason)[:2500])
            literals.append(str(reason))
        if l["cat"] == "AE":
            literals.append(countries.REVERSE["es-ES"])
    pay = spec.get("payment") or {}
    if spec.get("due_date") and not credit and (pay.get("iban") or pay.get("means_code")):
        inst = sub(sub(inv, "PaymentDetails"), "Installment")
        sub(inst, "InstallmentDueDate", spec["due_date"])
        sub(inst, "InstallmentAmount", d2(mny["due"]))
        sub(inst, "PaymentMeans", MEANS.get(str(pay.get("means_code") or "58"), "04"))
        if pay.get("iban"):
            acc = sub(inst, "AccountToBeCredited")
            sub(acc, "IBAN", str(pay["iban"]).replace(" ", ""))
            if pay.get("bic"):
                sub(acc, "BIC", str(pay["bic"]).replace(" ", ""))
    literals = list(dict.fromkeys(literals))
    if literals:
        ll = sub(inv, "LegalLiterals")
        for text in literals:
            sub(ll, "LegalReference", text[:250])
    summary = dict(syntax="facturae", profile="Facturae 3.2.2, unsigned", type_code=cii.type_code(spec), lines=len(lines),
                   total_excluding_vat=str(cii.r2(sgn * net_total)), total_vat=str(cii.r2(sgn * tax_total)),
                   total_including_vat=str(cii.r2(sgn * gross)), signed=False, **cii.money_summary(mny))
    if warnings:
        summary["warnings"] = warnings
    return root, summary


def xml_bytes(spec):
    root, summary = build(spec)
    ET.indent(root)
    out = io.BytesIO()
    ET.ElementTree(root).write(out, encoding="UTF-8", xml_declaration=True)
    return out.getvalue(), summary


def main(argv=None):
    ap = argparse.ArgumentParser(description="Create an unsigned Facturae 3.2.2 invoice or rectifying invoice from a JSON spec.")
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
