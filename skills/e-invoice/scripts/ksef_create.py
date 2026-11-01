#!/usr/bin/env python3
"""FA(3), the logical structure of the Polish structured invoice (Krajowy System e-Faktur), from the same JSON
spec: the faktura (RodzajFaktury VAT) and the faktura korygująca (KOR).

    python3 ksef_create.py spec.json invoice.xml

Polish taxpayers issue structured invoices in KSeF (ustawa o VAT art. 106ga) in the structure the Ministry of
Finance publishes as an electronic document template, FA(3) (crd.gov.pl/wzor/2025/06/25/13775/, kodSystemowy
"FA (3)", wersjaSchemy "1-0E"; the same files in github.com/CIRFMF/ksef-docs). A template of that kind is an
official document (prawo autorskie art. 4 pkt 2); still nothing of it is copied here: this file writes the
elements the structure defines, in its order, in our own code, and the Ministry's schema is fetched at pinned
SHA-256 sums and runs untouched in the pack check (EINV-KSEF).

THE FILE IS NOT SENT. This pack does not reach KSeF: the file has no KSeF number, and the page beside it
carries neither that number nor the code a structured invoice used outside KSeF must carry (art. 106gb ust. 5).

The arithmetic is einvoice_create's: line nets rounded to two decimals, the tax once per rate on the sum of
that rate's nets. A correcting invoice is written as the correction itself (art. 106j ust. 2 pkt 5): its
quantities and amounts are minus what the order credits. Standard library only. Prints a JSON summary.
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
NS = "http://crd.gov.pl/wzor/2025/06/25/13775/"
GENERATOR = "OpenPaperwork e-invoice"
EU = ("AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GR", "HR", "HU", "IE", "IT", "LT", "LU",
      "LV", "MT", "NL", "PT", "RO", "SE", "SI", "SK")
# The field of the summary each rate is added up in (P_13_n the net, P_14_n the tax): 23 and 22 percent in
# 1, 8 and 7 in 2, 5 in 3, 4 and 3 (taxi flat rate) in 4.
RATE_FIELD = {"23": "1", "22": "1", "8": "2", "7": "2", "5": "3", "4": "4", "3": "4"}
# UN/ECE Rec 20 units in the words a Polish invoice writes.
UNITS = {"C62": "szt.", "H87": "szt.", "HUR": "godz.", "DAY": "dni", "KGM": "kg", "MTR": "m", "LTR": "l", "MON": "mies."}
# EN 16931 payment means (UNCL 4461) to FormaPlatnosci: 1 cash, 2 card, 6 a transfer.
MEANS = {"30": "6", "58": "6", "42": "6", "10": "1", "48": "2", "54": "2", "55": "2"}


def sub(parent, tag, text=None, **attrs):
    e = ET.SubElement(parent, "{%s}%s" % (NS, tag), attrs)
    if text is not None:
        e.text = str(text)
    return e


def d2(x):
    return str(cii.r2(x))


def dn(x, places):
    text = format(Decimal(str(x)).quantize(Decimal(1).scaleb(-places)).normalize(), "f")
    return "0" if text in ("-0", "") else text


def untaxed(cat, buyer_country):
    """(P_12 word, summary field) of a line without tax. A reverse charge is "oo" when the buyer is in
    Poland; a supply outside Poland whose tax the buyer accounts for is "np II" for a buyer in another EU
    state (services under art. 100 ust. 1 pkt 4) and "np I" for one outside the EU."""
    if cat == "AE":
        if buyer_country in ("PL", ""):
            return "oo", "P_13_10"
        return ("np II", "P_13_9") if buyer_country in EU else ("np I", "P_13_8")
    return {"Z": ("0 KR", "P_13_6_1"), "K": ("0 WDT", "P_13_6_2"), "G": ("0 EX", "P_13_6_3"), "E": ("zw", "P_13_7"),
            "O": ("np I", "P_13_8")}[cat]


def address(parent, p):
    a = sub(parent, "Adres")
    sub(a, "KodKraju", countries.country(p))
    sub(a, "AdresL1", str(p.get("street") or p.get("city") or "")[:512])
    place = " ".join(x for x in (p.get("postcode"), p.get("city")) if x)
    if p.get("street") and place:
        sub(a, "AdresL2", place[:512])


def build(spec):
    warnings = cii.refuse(spec)
    missing, more = countries.refuse(spec)
    if missing:
        raise SystemExit("the spec lacks what this document needs; ask the person for it, never guess:\n  - "
                         + "\n  - ".join(missing))
    warnings += more
    lines, _groups, mny = cii.compute_full(spec)
    net_total = mny["basis"]
    cii.only_lines(mny, "KSeF FA(3)", paid_too=True)
    credit = countries.is_credit(spec)
    sgn = countries.credit_sign(spec)
    cur = str(spec.get("currency") or "PLN").upper()
    fx = Decimal(str(spec["exchange_rate"])) if cur != "PLN" and spec.get("exchange_rate") else None
    seller, buyer = spec.get("seller") or {}, spec.get("buyer") or {}
    bc = countries.country(buyer)
    ET.register_namespace("", NS)
    root = ET.Element("{%s}Faktura" % NS)
    head = sub(root, "Naglowek")
    sub(head, "KodFormularza", "FA", kodSystemowy="FA (3)", wersjaSchemy="1-0E")
    sub(head, "WariantFormularza", "3")
    sub(head, "DataWytworzeniaFa", spec.get("created_at") or "%sT00:00:00Z" % spec["issue_date"])
    sub(head, "SystemInfo", GENERATOR)
    p1 = sub(root, "Podmiot1")
    if bc in EU:
        sub(p1, "PrefiksPodatnika", "PL")             # art. 106e ust. 1 pkt 24 lit. a: PL before the NIP in EU trade
    d1 = sub(p1, "DaneIdentyfikacyjne")
    sub(d1, "NIP", ids.pl_nip(seller.get("vat_id")))
    sub(d1, "Nazwa", str(seller.get("name") or "")[:512])
    address(p1, seller)
    contact = seller.get("contact") if isinstance(seller.get("contact"), dict) else {}
    phone, mail = contact.get("phone") or seller.get("phone"), contact.get("email") or seller.get("email")
    if phone or mail:
        dk = sub(p1, "DaneKontaktowe")
        if mail:
            sub(dk, "Email", mail)
        if phone:
            sub(dk, "Telefon", re.sub(r"[^\d+]", "", str(phone))[:16])
    p2 = sub(root, "Podmiot2")
    d2_ = sub(p2, "DaneIdentyfikacyjne")
    raw = re.sub(r"[\s\-.]", "", str(buyer.get("vat_id") or "")).upper()
    if bc in ("PL", "") and ids.pl_nip_form(raw):
        sub(d2_, "NIP", ids.pl_nip(raw))
    elif bc in EU and raw:
        sub(d2_, "KodUE", "EL" if bc == "GR" else bc)
        sub(d2_, "NrVatUE", raw[2:] if raw[:2] in (bc, "EL") else raw)
    elif raw:
        if bc:
            sub(d2_, "KodKraju", bc)
        sub(d2_, "NrID", raw[:50])
    else:
        sub(d2_, "BrakID", "1")
    sub(d2_, "Nazwa", str(buyer.get("name") or "")[:512])
    address(p2, buyer)
    sub(p2, "JST", "2")                               # 2: the buyer is not a subordinate unit of local government
    sub(p2, "GV", "2")                                # 2: nor a member of a VAT group

    # Net and tax per summary field; a line knows its P_12 word.
    sums, order = {}, []
    for l in lines:
        if l["cat"] == "S" and l["rate"]:
            word = format(l["rate"].normalize(), "f")
            field = "P_13_" + RATE_FIELD[word]
        else:
            word, field = untaxed(l["cat"] if l["cat"] != "S" else "Z", bc)
        l["word"], l["field"] = word, field
        s = sums.setdefault(field, dict(base=Decimal(0), rate=l["rate"] if l["cat"] == "S" else Decimal(0)))
        s["base"] += l["net"]
    tax = {f: cii.r2(s["base"] * s["rate"] / 100) for f, s in sums.items()}
    tax_total = sum(tax.values(), Decimal(0))
    gross = net_total + tax_total

    fa = sub(root, "Fa")
    sub(fa, "KodWaluty", cur)
    sub(fa, "P_1", spec["issue_date"])
    sub(fa, "P_2", spec["number"])
    if spec.get("delivery_date") and not credit:
        sub(fa, "P_6", spec["delivery_date"])
    for n in ("1", "2", "3", "4"):
        f = "P_13_" + n
        if f in sums:
            sub(fa, f, d2(sgn * sums[f]["base"]))
            sub(fa, "P_14_" + n, d2(sgn * tax[f]))
            if fx:
                sub(fa, "P_14_%sW" % n, d2(sgn * tax[f] * fx))   # the tax in złoty when the invoice is in another currency
    for f in ("P_13_6_1", "P_13_6_2", "P_13_6_3", "P_13_7", "P_13_8", "P_13_9", "P_13_10"):
        if f in sums:
            sub(fa, f, d2(sgn * sums[f]["base"]))
    sub(fa, "P_15", d2(sgn * gross))
    cats = {l["cat"] for l in lines}
    an = sub(fa, "Adnotacje")
    sub(an, "P_16", "1" if spec.get("cash_method") else "2")          # „metoda kasowa”
    sub(an, "P_17", "2")                                              # „samofakturowanie”
    sub(an, "P_18", "1" if "AE" in cats else "2")                     # „odwrotne obciążenie”
    sub(an, "P_18A", "1" if spec.get("split_payment") else "2")       # „mechanizm podzielonej płatności”
    zw = sub(an, "Zwolnienie")
    exempt = [src for l, src in zip(lines, spec["lines"]) if l["cat"] == "E"]
    if exempt:
        basis = str(exempt[0].get("exemption_basis") or spec.get("exemption_basis") or "").lower()
        sub(zw, "P_19", "1")
        sub(zw, countries.PL_BASIS[basis], str(exempt[0].get("exemption_reason") or spec.get("exemption_reason"))[:256])
    else:
        sub(zw, "P_19N", "1")
    sub(sub(an, "NoweSrodkiTransportu"), "P_22N", "1")
    sub(an, "P_23", "2")
    sub(sub(an, "PMarzy"), "P_PMarzyN", "1")
    sub(fa, "RodzajFaktury", "KOR" if credit else "VAT")
    if credit:
        if spec.get("note"):
            sub(fa, "PrzyczynaKorekty", str(spec["note"])[:256])
        ref = sub(fa, "DaneFaKorygowanej")
        sub(ref, "DataWystFaKorygowanej", spec["preceding_invoice_date"])
        sub(ref, "NrFaKorygowanej", spec["preceding_invoice"])
        if spec.get("preceding_ksef_number"):
            sub(ref, "NrKSeF", "1")
            sub(ref, "NrKSeFFaKorygowanej", spec["preceding_ksef_number"])
        else:
            sub(ref, "NrKSeFN", "1")
    for l, src in zip(lines, spec["lines"]):
        w = sub(fa, "FaWiersz")
        sub(w, "NrWierszaFa", l["id"])
        sub(w, "P_7", str(l["name"])[:512])
        sub(w, "P_8A", UNITS.get(str(l["unit"]).upper(), str(l["unit"])))
        sub(w, "P_8B", dn(sgn * l["qty"], 6))
        sub(w, "P_9A", dn(l["price"], 8))
        cost = cii.r2(l["qty"] * l["price"])
        if cost != l["net"]:
            sub(w, "P_10", dn(sgn * (cost - l["net"]), 8))
        sub(w, "P_11", d2(sgn * l["net"]))
        sub(w, "P_12", l["word"])
        if fx:
            sub(w, "KursWaluty", dn(fx, 6))
    pay = spec.get("payment") or {}
    if not credit and (spec.get("due_date") or pay.get("iban") or pay.get("account")):
        pl = sub(fa, "Platnosc")
        if spec.get("due_date"):
            sub(sub(pl, "TerminPlatnosci"), "Termin", spec["due_date"])
        sub(pl, "FormaPlatnosci", MEANS.get(str(pay.get("means_code") or "58"), "6"))
        account = str(pay.get("iban") or pay.get("account") or "").replace(" ", "").upper()
        if account:
            rb = sub(pl, "RachunekBankowy")
            sub(rb, "NrRB", account)
            if pay.get("bic"):
                sub(rb, "SWIFT", str(pay["bic"]).replace(" ", "").upper())
            if pay.get("bank"):
                sub(rb, "NazwaBanku", str(pay["bank"])[:256])
    if seller.get("register_number") or seller.get("regon"):
        reg = sub(sub(root, "Stopka"), "Rejestry")
        if seller.get("register_number"):
            sub(reg, "KRS", re.sub(r"\D", "", str(seller["register_number"])))
        if seller.get("regon"):
            sub(reg, "REGON", re.sub(r"\D", "", str(seller["regon"])))
    summary = dict(syntax="ksef", profile="KSeF FA(3), not sent", type_code=cii.type_code(spec), lines=len(lines),
                   total_excluding_vat=str(cii.r2(sgn * net_total)), total_vat=str(cii.r2(sgn * tax_total)),
                   total_including_vat=str(cii.r2(sgn * gross)), sent=False)
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
    ap = argparse.ArgumentParser(description="Create a KSeF FA(3) invoice or correcting invoice from a JSON spec.")
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
