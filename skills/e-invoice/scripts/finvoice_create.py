#!/usr/bin/env python3
"""Finvoice 3.0, the Finnish banks' e-invoice, from the same JSON spec: the lasku and the hyvityslasku.

    python3 finvoice_create.py spec.json invoice.xml

Finanssiala ry publishes Finvoice 3.0 (the schema Finvoice3.0.xsd of 27.9.2023 and the implementation
guidelines) and says on its Finvoice page: "All materials on this page are freely usable." The element
order here follows that schema; the official schema runs untouched in the pack check (EINV-FINVOICE).
Amounts are written as Finvoice writes them, with a decimal comma (1234,56); dates as CCYYMMDD.

The arithmetic is einvoice_create's: line nets rounded to two decimals, VAT once per rate on the sum of
that rate's nets. Standard library only. Prints a JSON summary with the totals.
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

ids = countries.ids


def money(x):
    return str(cii.r2(x)).replace(".", ",")


# Finvoice states a credit note's amounts and quantities with a minus sign (Finvoice 3.0 implementation
# guidelines, InvoiceTypeCode INV02); the EN 16931 credit note keeps them positive under type 381.
sign = 1


def pct(x):
    d = Decimal(str(x)).normalize()
    text = format(d, "f")
    return text.replace(".", ",")


def sub(parent, tag, text=None, **attrs):
    e = ET.SubElement(parent, tag, {k: str(v) for k, v in attrs.items()})
    if text is not None:
        e.text = str(text)
    return e


def day(iso):
    return str(iso).replace("-", "")


def postal(parent, tag, prefix, p):
    a = sub(parent, tag)
    sub(a, prefix + "StreetName", p.get("street", ""))
    sub(a, prefix + "TownName", p.get("city", ""))
    sub(a, prefix + "PostCodeIdentifier", p.get("postcode", ""))
    sub(a, "CountryCode", countries.country(p))
    return a


def build(spec):
    warnings = cii.refuse(spec)
    missing, more = countries.refuse(dict(spec, syntax="finvoice"))
    if missing:
        raise SystemExit("the spec lacks what this document needs; ask the person for it, never guess:\n  - "
                         + "\n  - ".join(missing))
    warnings += more
    lines, groups, money_ = cii.compute_full(spec)
    tax, net_total, tax_total, gross = money_["tax"], money_["basis"], money_["tax_total"], money_["grand"]
    credit = cii.type_code(spec) == "381"
    if credit and (money_["allowances"] or money_["paid"]):
        raise SystemExit("a Finvoice credit note states its amounts with a minus sign: put a discount on the lines; a credit note owes nothing in advance")
    global sign
    sign = -1 if credit else 1
    cur = spec.get("currency", "EUR")
    seller, buyer = spec.get("seller") or {}, spec.get("buyer") or {}
    pay = spec.get("payment") or {}
    root = ET.Element("Finvoice", {"Version": "3.0"})

    sp = sub(root, "SellerPartyDetails")
    yt = countries.org_number(seller, "FI")
    if yt:
        sub(sp, "SellerPartyIdentifier", yt)
    sub(sp, "SellerOrganisationName", seller.get("name", ""))
    if countries.vat_id(seller):
        sub(sp, "SellerOrganisationTaxCode", countries.vat_id(seller))
    postal(sp, "SellerPostalAddressDetails", "Seller", seller)
    name, phone, email = cii.contact_of(seller)
    if name:
        sub(root, "SellerContactPersonName", name)
    if phone or email:
        com = sub(root, "SellerCommunicationDetails")
        if phone:
            sub(com, "SellerPhoneNumberIdentifier", phone)
        if email:
            sub(com, "SellerEmailaddressIdentifier", email)
    info = sub(root, "SellerInformationDetails")
    if seller.get("registered_office"):
        sub(info, "SellerHomeTownName", seller["registered_office"])
    if countries.vat_id(seller):
        sub(info, "SellerVatRegistrationText", "Alv.Rek")
    acc = sub(info, "SellerAccountDetails")
    sub(acc, "SellerAccountID", pay["iban"].replace(" ", ""), IdentificationSchemeName="IBAN")
    sub(acc, "SellerBic", pay["bic"].replace(" ", ""), IdentificationSchemeName="BIC")

    bp = sub(root, "BuyerPartyDetails")
    byt = countries.org_number(buyer, "FI") if countries.country(buyer) == "FI" else ""
    if byt:
        sub(bp, "BuyerPartyIdentifier", byt)
    sub(bp, "BuyerOrganisationName", buyer.get("name", ""))
    if countries.vat_id(buyer):
        sub(bp, "BuyerOrganisationTaxCode", countries.vat_id(buyer))
    postal(bp, "BuyerPostalAddressDetails", "Buyer", buyer)
    if buyer.get("contact_name"):
        sub(root, "BuyerContactPersonName", buyer["contact_name"])

    if spec.get("delivery_date"):
        sub(sub(root, "DeliveryDetails"), "DeliveryDate", day(spec["delivery_date"]), Format="CCYYMMDD")

    d = sub(root, "InvoiceDetails")
    sub(d, "InvoiceTypeCode", "INV02" if credit else "INV01", CodeListAgencyIdentifier="SPY")
    sub(d, "InvoiceTypeCodeUN", "381" if credit else "380")
    sub(d, "InvoiceTypeText", "HYVITYSLASKU" if credit else "LASKU")
    sub(d, "OriginCode", "Original")
    sub(d, "InvoiceNumber", spec["number"])
    sub(d, "InvoiceDate", day(spec["issue_date"]), Format="CCYYMMDD")
    if spec.get("preceding_invoice"):
        sub(d, "OriginalInvoiceNumber", spec["preceding_invoice"])
        if spec.get("preceding_invoice_date"):
            sub(d, "OriginalInvoiceDate", day(spec["preceding_invoice_date"]), Format="CCYYMMDD")
    if spec.get("order_reference"):
        sub(d, "OrderIdentifier", spec["order_reference"])
    if spec.get("buyer_reference"):
        sub(d, "BuyerReferenceIdentifier", spec["buyer_reference"])
    sub(d, "RowsTotalVatExcludedAmount", money(sign * (money_["line_total"])), AmountCurrencyIdentifier=cur)
    if money_["allowances"]:
        sub(d, "DiscountsTotalVatExcludedAmount", money(sign * money_["allowance_total"]), AmountCurrencyIdentifier=cur)
    sub(d, "InvoiceTotalVatExcludedAmount", money(sign * (net_total)), AmountCurrencyIdentifier=cur)
    sub(d, "InvoiceTotalVatAmount", money(sign * (tax_total)), AmountCurrencyIdentifier=cur)
    sub(d, "InvoiceTotalVatIncludedAmount", money(sign * (gross)), AmountCurrencyIdentifier=cur)
    if money_["paid"]:
        sub(d, "InvoicePaidAmount", money(money_["paid"]), AmountCurrencyIdentifier=cur)
    for (cat, rate), g in sorted(groups.items(), key=lambda kv: (-kv[0][1], kv[0][0])):
        v = sub(d, "VatSpecificationDetails")
        sub(v, "VatBaseAmount", money(sign * (g["base"])), AmountCurrencyIdentifier=cur)
        sub(v, "VatRatePercent", pct(rate))
        sub(v, "VatCode", cat)
        sub(v, "VatRateAmount", money(sign * (tax[(cat, rate)])), AmountCurrencyIdentifier=cur)
        if cat in ("AE", "E", "K", "G", "O"):
            sub(v, "VatFreeText", g["reason"] or ("Käännetty verovelvollisuus" if cat == "AE" else "Veroton"))
    if spec.get("note"):
        sub(d, "InvoiceFreeText", spec["note"])
    terms = sub(d, "PaymentTermsDetails")
    if spec.get("payment_terms"):
        sub(terms, "PaymentTermsFreeText", str(spec["payment_terms"])[:70])
    if spec.get("due_date"):
        sub(terms, "InvoiceDueDate", day(spec["due_date"]), Format="CCYYMMDD")
    if spec.get("late_interest_percent") not in (None, ""):
        fine = sub(terms, "PaymentOverDueFineDetails")
        sub(fine, "PaymentOverDueFinePercent", pct(spec["late_interest_percent"]))

    for al in money_["allowances"]:
        # An allowance on the whole document (EN 16931-1 BG-20) as DiscountDetails: reason BT-97, code BT-98, BT-94, BT-92, BT-93, BT-95, BT-96.
        dd = sub(d, "DiscountDetails")
        if al["reason"]:
            sub(dd, "FreeText", al["reason"][:70])
        if al["code"]:
            sub(dd, "ReasonCode", al["code"])
        if al["percent"] is not None:
            sub(dd, "Percent", pct(al["percent"]))
        sub(dd, "Amount", money(al["amount"]), AmountCurrencyIdentifier=cur)
        if al["base"] is not None:
            sub(dd, "BaseAmount", money(al["base"]), AmountCurrencyIdentifier=cur)
        sub(dd, "VatCategoryCode", al["cat"])
        sub(dd, "VatRatePercent", pct(al["rate"]))

    barcode = ids.fi_virtual_barcode(pay.get("iban"), money_["due"], pay.get("reference"), spec.get("due_date")) \
        if not credit else None
    if barcode:
        sub(root, "VirtualBankBarcode", barcode)

    for l, src in zip(lines, spec["lines"]):
        r = sub(root, "InvoiceRow")
        if src.get("sku"):
            sub(r, "ArticleIdentifier", src["sku"])
        sub(r, "ArticleName", l["name"][:100])
        sub(r, "InvoicedQuantity", pct(sign * l["qty"]), QuantityUnitCodeUN=l["unit"])
        sub(r, "UnitPriceAmount", money(l["price"]) if l["price"] == cii.r2(l["price"]) else pct(l["price"]),
            AmountCurrencyIdentifier=cur)
        if l["disc"]:
            # BG-27: BT-138 the percentage (when given), BT-136 the amount, BT-137 what it is taken off.
            if l["pct"]:
                sub(r, "RowDiscountPercent", pct(l["pct"]))
            sub(r, "RowDiscountAmount", money(sign * l["disc"]), AmountCurrencyIdentifier=cur)
            sub(r, "RowDiscountBaseAmount", money(sign * l["base"]), AmountCurrencyIdentifier=cur)
        sub(r, "RowVatRatePercent", pct(l["rate"]))
        sub(r, "RowVatCode", l["cat"])
        sub(r, "RowVatAmount", money(sign * (l["net"] * l["rate"] / 100)), AmountCurrencyIdentifier=cur)
        sub(r, "RowVatExcludedAmount", money(sign * (l["net"])), AmountCurrencyIdentifier=cur)
        sub(r, "RowAmount", money(sign * (l["net"] + cii.r2(l["net"] * l["rate"] / 100))), AmountCurrencyIdentifier=cur)

    epi = sub(root, "EpiDetails")
    ident = sub(epi, "EpiIdentificationDetails")
    sub(ident, "EpiDate", day(spec["issue_date"]), Format="CCYYMMDD")
    sub(ident, "EpiReference", "")
    parties = sub(epi, "EpiPartyDetails")
    sub(sub(parties, "EpiBfiPartyDetails"), "EpiBfiIdentifier", pay["bic"].replace(" ", ""), IdentificationSchemeName="BIC")
    ben = sub(parties, "EpiBeneficiaryPartyDetails")
    sub(ben, "EpiNameAddressDetails", seller.get("name", "")[:35])
    if yt:
        sub(ben, "EpiBei", ids.digits(yt))
    sub(ben, "EpiAccountID", pay["iban"].replace(" ", ""), IdentificationSchemeName="IBAN")
    instr = sub(epi, "EpiPaymentInstructionDetails")
    ref = str(pay.get("reference") or "").replace(" ", "")
    if ref:
        sub(instr, "EpiRemittanceInfoIdentifier", ref, IdentificationSchemeName="ISO" if ref.upper().startswith("RF") else "SPY")
    sub(instr, "EpiInstructedAmount", money(0 if credit else money_["due"]), AmountCurrencyIdentifier=cur)
    sub(instr, "EpiCharge", "SHA", ChargeOption="SHA")
    sub(instr, "EpiDateOptionDate", day(spec.get("due_date") or spec["issue_date"]), Format="CCYYMMDD")

    summary = dict(syntax="finvoice", profile="Finvoice 3.0", type_code=cii.type_code(spec), lines=len(lines),
                   total_excluding_vat=str(cii.r2(net_total)), total_vat=str(cii.r2(tax_total)),
                   total_including_vat=str(cii.r2(gross)), **cii.money_summary(money_))
    if barcode:
        summary["virtual_barcode"] = barcode
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
    ap = argparse.ArgumentParser(description="Create a Finvoice 3.0 invoice or credit note from a JSON spec.")
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
