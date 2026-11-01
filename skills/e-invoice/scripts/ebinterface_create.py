#!/usr/bin/env python3
"""ebInterface 6.1, the Austrian e-invoice, from the same JSON spec: the Rechnung and the Rechnungskorrektur.

    python3 ebinterface_create.py spec.json invoice.xml

AUSTRIAPRO (Wirtschaftskammer Österreich) publishes ebInterface and makes it available free of charge
for implementation; its schema repository (github.com/austriapro/ebinterface-standards) states no
licence, so nothing of it is copied here. This file writes the elements the 6.1 schema defines, in its
order, in our own code; the official Invoice.xsd is fetched at a pinned commit and runs untouched in
the pack check (EINV-EBINTERFACE). The Austrian federal portal (erechnung.gv.at) takes ebInterface and
Peppol BIS Billing 3.0 alike; a public buyer's order number goes in order_reference (OrderID).

The arithmetic is einvoice_create's: line nets rounded to two decimals, VAT once per category and rate
on the sum of that group's nets. A credit note is DocumentType CreditMemo with positive amounts and the
invoice it corrects as a RelatedDocument. Standard library only. Prints a JSON summary with the totals.
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

NS = "http://www.ebinterface.at/schema/6p1/"
GENERATOR = "OpenPaperwork e-invoice"
# ebInterface's own word for a party without a VAT number (the 6.1 documentation, VATIdentificationNumber).
NO_UID = "00000000"


def sub(parent, tag, text=None, **attrs):
    e = ET.SubElement(parent, "{%s}%s" % (NS, tag), {k: str(v) for k, v in attrs.items()})
    if text is not None:
        e.text = str(text)
    return e


def d2(x):
    return str(cii.r2(x))


def d4(x):
    return format(Decimal(str(x)).quantize(Decimal("0.0001")).normalize(), "f")


def pct(x):
    return format(Decimal(str(x)).quantize(Decimal("0.01")).normalize(), "f")


def address(parent, p, contact=None):
    a = sub(parent, "Address")
    sub(a, "Name", p.get("name", ""))
    if p.get("street"):
        sub(a, "Street", p["street"])
    sub(a, "Town", p.get("city", ""))
    sub(a, "ZIP", p.get("postcode", ""))
    cc = countries.country(p)
    sub(a, "Country", p.get("country_name") or cc, CountryCode=cc)
    if contact and contact.get("phone"):
        sub(a, "Phone", contact["phone"])
    if contact and contact.get("email"):
        sub(a, "Email", contact["email"])


def party(parent, tag, spec, role):
    p = spec.get(role) or {}
    el = sub(parent, tag)
    sub(el, "VATIdentificationNumber", countries.vat_id(p) or NO_UID)
    if role == "seller" and p.get("register_number"):
        # The Firmenbuch details a company's business documents state (UGB § 14), as ebInterface's further
        # identifications FN (Firmenbuchnummer) and FBG (Firmenbuchgericht).
        sub(el, "FurtherIdentification", countries.ids.at_fn_text(p["register_number"]).replace("FN ", ""),
            IdentificationType="FN")
        if p.get("register"):
            sub(el, "FurtherIdentification", p["register"], IdentificationType="FBG")
    if role == "buyer" and (spec.get("order_reference") or spec.get("buyer_reference")):
        ref = sub(el, "OrderReference")
        sub(ref, "OrderID", spec.get("order_reference") or spec.get("buyer_reference"))
        if spec.get("order_date"):
            sub(ref, "ReferenceDate", spec["order_date"])
    contact = p.get("contact") if isinstance(p.get("contact"), dict) else {}
    address(el, p, contact)
    name = contact.get("name") or p.get("contact_name")
    if name:
        sub(sub(el, "Contact"), "Name", name)
    return el


def build(spec):
    warnings = cii.refuse(spec)
    missing, more = countries.refuse(spec)
    if missing:
        raise SystemExit("the spec lacks what this document needs; ask the person for it, never guess:\n  - "
                         + "\n  - ".join(missing))
    warnings += more
    lines, groups, mny = cii.compute_full(spec)
    tax, net_total, tax_total, gross = mny["tax"], mny["basis"], mny["tax_total"], mny["grand"]
    cii.only_lines(mny, "ebInterface 6.1")
    credit = cii.type_code(spec) == "381"
    cur = spec.get("currency", "EUR")
    ET.register_namespace("", NS)
    root = ET.Element("{%s}Invoice" % NS, {"GeneratingSystem": GENERATOR,
                                          "DocumentType": "CreditMemo" if credit else "Invoice",
                                          "InvoiceCurrency": cur, "Language": "de"})
    sub(root, "InvoiceNumber", spec["number"])
    sub(root, "InvoiceDate", spec["issue_date"])
    if spec.get("preceding_invoice"):
        rel = sub(root, "RelatedDocument")
        sub(rel, "InvoiceNumber", spec["preceding_invoice"])
        if spec.get("preceding_invoice_date"):
            sub(rel, "InvoiceDate", spec["preceding_invoice_date"])
        sub(rel, "DocumentType", "Invoice")
    period = spec.get("delivery_period") if isinstance(spec.get("delivery_period"), dict) else None
    if spec.get("delivery_date") or period:
        dlv = sub(root, "Delivery")
        if period and period.get("from") and period.get("to"):
            pe = sub(dlv, "Period")
            sub(pe, "FromDate", period["from"])
            sub(pe, "ToDate", period["to"])
        else:
            sub(dlv, "Date", spec["delivery_date"])
    party(root, "Biller", spec, "seller")
    party(root, "InvoiceRecipient", spec, "buyer")
    details = sub(root, "Details")
    items = sub(details, "ItemList")
    for l, src in zip(lines, spec["lines"]):
        li = sub(items, "ListLineItem")
        sub(li, "PositionNumber", l["id"])
        sub(li, "Description", l["name"])
        sub(li, "Quantity", d4(l["qty"]), Unit=l["unit"])
        sub(li, "UnitPrice", d4(l["price"]))
        gross_line = cii.r2(l["qty"] * l["price"])
        if gross_line != l["net"]:
            red = sub(sub(li, "ReductionAndSurchargeListLineItemDetails"), "ReductionListLineItem")
            sub(red, "BaseAmount", d2(gross_line))
            if src.get("discount_percent"):
                sub(red, "Percentage", pct(src["discount_percent"]))
            sub(red, "Amount", d2(gross_line - l["net"]))
        ti = sub(li, "TaxItem")
        sub(ti, "TaxableAmount", d2(l["net"]))
        sub(ti, "TaxPercent", pct(l["rate"]), TaxCategoryCode=l["cat"])
        sub(li, "LineItemAmount", d2(l["net"]))
    taxes = sub(root, "Tax")
    for (cat, rate), g in sorted(groups.items(), key=lambda kv: (kv[0][0], -kv[0][1])):
        ti = sub(taxes, "TaxItem")
        sub(ti, "TaxableAmount", d2(g["base"]))
        sub(ti, "TaxPercent", pct(rate), TaxCategoryCode=cat)
        sub(ti, "TaxAmount", d2(tax[(cat, rate)]))
        if cat == "AE":
            sub(ti, "Comment", g["reason"] or countries.REVERSE["de-AT"])
        elif cat in ("E", "K", "G", "O") and g["reason"]:
            sub(ti, "Comment", g["reason"])
    sub(root, "TotalGrossAmount", d2(gross))
    if mny["paid"]:
        sub(root, "PrepaidAmount", d2(mny["paid"]))        # BT-113
    sub(root, "PayableAmount", d2(mny["due"]))         # BT-115
    pay = spec.get("payment") or {}
    if pay.get("iban"):
        pm = sub(root, "PaymentMethod")
        ubt = sub(pm, "UniversalBankTransaction")
        acc = sub(ubt, "BeneficiaryAccount")
        if pay.get("bic"):
            sub(acc, "BIC", pay["bic"].replace(" ", ""))
        sub(acc, "IBAN", pay["iban"].replace(" ", ""))
        sub(acc, "BankAccountOwner", (pay.get("account_name") or (spec.get("seller") or {}).get("name", ""))[:70])
        if pay.get("reference"):
            sub(ubt, "PaymentReference", str(pay["reference"])[:35])
    if spec.get("due_date") or spec.get("payment_terms"):
        pc = sub(root, "PaymentConditions")
        if spec.get("due_date"):
            sub(pc, "DueDate", spec["due_date"])
        if spec.get("payment_terms"):
            sub(pc, "Comment", spec["payment_terms"])
    notes = [spec.get("note")] + ([countries.REVERSE["de-AT"]] if "AE" in {k[0] for k in groups} else [])
    notes = [n for n in notes if n]
    if notes:
        sub(root, "Comment", " ".join(notes))
    summary = dict(syntax="ebinterface", profile="ebInterface 6.1", type_code=cii.type_code(spec), lines=len(lines),
                   total_excluding_vat=str(cii.r2(net_total)), total_vat=str(cii.r2(tax_total)),
                   total_including_vat=str(cii.r2(gross)), **cii.money_summary(mny))
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
    ap = argparse.ArgumentParser(description="Create an ebInterface 6.1 invoice or credit memo from a JSON spec.")
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
