#!/usr/bin/env python3
"""FatturaPA 1.2.3, the Italian e-invoice, from the same JSON spec: the fattura (TD01) and the nota di credito
(TD04), to a private party (FPR12) or to a public body (FPA12, "public_buyer": true).

    python3 fatturapa_create.py spec.json invoice.xml

Invoices between parties resident or established in Italy are issued only as e-invoices through the Sistema
di Interscambio in this format (D.Lgs. 127/2015 art. 1 comma 3; from 1 January 2027 art. 77 of the Testo unico
IVA, D.Lgs. 10/2026). The format is allegato A of DM 3 aprile 2013 n. 55, an official act (L. 633/1941 art. 5);
fatturapa.gov.it, which publishes the schema and the technical specifications, reserves every right in the
site's contents, so nothing of them is copied here. This file writes the elements schema 1.2.3 defines, in its
order, in our own code; the official schema is fetched at a pinned SHA-256 and runs untouched in the pack check
(EINV-FATTURAPA).

THE FILE IS NOT SENT. This pack does not reach the Sistema di Interscambio, signs nothing and names no file
for transmission; the page beside the file is a courtesy copy.

The arithmetic is einvoice_create's: line nets rounded to two decimals, IVA once per rate (and Natura) on the
sum of that group's nets. A credit note is TD04 with positive amounts, the document type carrying the sign,
and names the invoice it corrects in DatiFattureCollegate. Standard library only. Prints a JSON summary.
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
NS = "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"
# EN 16931 payment means (UNCL 4461) to FatturaPA's ModalitaPagamento: MP05 a credit transfer, MP01 cash,
# MP08 a payment card, MP19 a SEPA direct debit.
MEANS = {"30": "MP05", "58": "MP05", "42": "MP05", "10": "MP01", "48": "MP08", "54": "MP08", "55": "MP08", "59": "MP19"}
UNITS = {"C62": "pz", "H87": "pz", "HUR": "ore", "DAY": "giorni", "KGM": "kg", "MTR": "m", "LTR": "l", "MON": "mesi"}
# Characters outside Latin-1, which the schema's text types do not take, written the plain way.
PLAIN = {"–": "-", "—": "-", "’": "'", "‘": "'", "“": '"', "”": '"', "€": "EUR", "…": "...", " ": " ", " ": " "}


def latin(value, limit):
    text = "".join(PLAIN.get(ch, ch) for ch in str(value or ""))
    return text.encode("latin-1", "replace").decode("latin-1")[:limit]


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


def fiscal_id(parent, p):
    """IdFiscaleIVA: the country and the VAT number without it."""
    cc = countries.country(p)
    raw = re.sub(r"[\s.]", "", str(p.get("vat_id") or "")).upper()
    code = ids.it_piva(raw) if cc == "IT" else (raw[2:] if raw[:2] == cc else raw)
    el = sub(parent, "IdFiscaleIVA")
    sub(el, "IdPaese", cc)
    sub(el, "IdCodice", code[:28])


def address(parent, p):
    a = sub(parent, "Sede")
    italy = countries.country(p) == "IT"
    sub(a, "Indirizzo", latin(p.get("street"), 60))
    # The specification's filler for an address abroad: CAP 00000, no province.
    sub(a, "CAP", str(p.get("postcode") or "") if italy else "00000")
    sub(a, "Comune", latin(p.get("city"), 60))
    if italy and p.get("province"):
        sub(a, "Provincia", str(p["province"]).upper())
    sub(a, "Nazione", countries.country(p))


def name(parent, p):
    a = sub(parent, "Anagrafica")
    if p.get("first_name") and p.get("surname"):
        sub(a, "Nome", latin(p["first_name"], 60))
        sub(a, "Cognome", latin(p["surname"], 60))
    else:
        sub(a, "Denominazione", latin(p.get("name"), 80))


def build(spec):
    warnings = cii.refuse(spec)
    missing, more = countries.refuse(spec)
    if missing:
        raise SystemExit("the spec lacks what this document needs; ask the person for it, never guess:\n  - "
                         + "\n  - ".join(missing))
    warnings += more
    lines, _groups, mny = cii.compute_full(spec)
    net_total = mny["basis"]
    cii.only_lines(mny, "FatturaPA 1.2.3")
    credit = countries.is_credit(spec)
    seller, buyer = spec.get("seller") or {}, spec.get("buyer") or {}
    fmt = "FPA12" if spec.get("public_buyer") else "FPR12"
    ET.register_namespace("p", NS)
    root = ET.Element("{%s}FatturaElettronica" % NS, {"versione": fmt})
    head = sub(root, "FatturaElettronicaHeader")
    tx = sub(head, "DatiTrasmissione")
    sender = spec.get("transmitter") if isinstance(spec.get("transmitter"), dict) else {}
    idt = sub(tx, "IdTrasmittente")
    sub(idt, "IdPaese", str(sender.get("country") or "IT").upper())
    sub(idt, "IdCodice", str(sender.get("code") or seller.get("tax_code") or ids.it_piva(seller.get("vat_id"))))
    sub(tx, "ProgressivoInvio", (re.sub(r"[^A-Za-z0-9]", "", str(spec.get("transmission_number") or spec["number"])) or "1")[-10:])
    sub(tx, "FormatoTrasmissione", fmt)
    sub(tx, "CodiceDestinatario", countries.it_recipient_code(spec)[0])
    if buyer.get("pec") and fmt == "FPR12":
        sub(tx, "PECDestinatario", buyer["pec"])
    cp = sub(head, "CedentePrestatore")
    da = sub(cp, "DatiAnagrafici")
    fiscal_id(da, seller)
    if seller.get("tax_code"):
        sub(da, "CodiceFiscale", str(seller["tax_code"]).upper())
    name(da, seller)
    sub(da, "RegimeFiscale", seller["tax_regime"])
    address(cp, seller)
    rea = seller.get("rea") if isinstance(seller.get("rea"), dict) else None
    if rea and rea.get("office") and rea.get("number"):
        # The Registro delle imprese details a company states: office, REA number, capital, sole shareholder
        # (SU) or several (SM), in liquidation (LS) or not (LN).
        r = sub(cp, "IscrizioneREA")
        sub(r, "Ufficio", str(rea["office"]).upper())
        sub(r, "NumeroREA", str(rea["number"])[:20])
        if rea.get("share_capital") not in (None, ""):
            sub(r, "CapitaleSociale", d2(rea["share_capital"]))
        if rea.get("sole_shareholder") is not None:
            sub(r, "SocioUnico", "SU" if rea["sole_shareholder"] else "SM")
        sub(r, "StatoLiquidazione", "LS" if rea.get("in_liquidation") else "LN")
    contact = seller.get("contact") if isinstance(seller.get("contact"), dict) else {}
    phone, mail = contact.get("phone") or seller.get("phone"), contact.get("email") or seller.get("email")
    if phone or mail:
        c = sub(cp, "Contatti")
        if phone:
            sub(c, "Telefono", re.sub(r"[^\d+]", "", str(phone))[:12])
        if mail:
            sub(c, "Email", str(mail)[:256])
    cc = sub(head, "CessionarioCommittente")
    db = sub(cc, "DatiAnagrafici")
    if buyer.get("vat_id"):
        fiscal_id(db, buyer)
    if buyer.get("tax_code"):
        sub(db, "CodiceFiscale", str(buyer["tax_code"]).upper())
    name(db, buyer)
    address(cc, buyer)

    # IVA once per rate and Natura on the sum of that group's nets.
    groups = {}
    for l, src in zip(lines, spec["lines"]):
        nature = countries.nature_of(src, spec) if (l["cat"] != "S" or not l["rate"]) else ""
        reason = src.get("exemption_reason") or spec.get("exemption_reason") or (countries.REVERSE["it-IT"] if l["cat"] == "AE" else "")
        g = groups.setdefault((l["rate"], nature), dict(base=Decimal(0), reason=reason))
        g["base"] += l["net"]
        l["nature"] = nature
    tax = {k: cii.r2(g["base"] * k[0] / 100) for k, g in groups.items()}
    tax_total = sum(tax.values(), Decimal(0))
    gross = net_total + tax_total

    body = sub(root, "FatturaElettronicaBody")
    dg = sub(body, "DatiGenerali")
    doc = sub(dg, "DatiGeneraliDocumento")
    sub(doc, "TipoDocumento", "TD04" if credit else "TD01")
    sub(doc, "Divisa", str(spec.get("currency") or "EUR").upper())
    sub(doc, "Data", spec["issue_date"])
    sub(doc, "Numero", spec["number"])
    stamp = spec.get("stamp_duty")
    if stamp:
        b = sub(doc, "DatiBollo")
        sub(b, "BolloVirtuale", "SI")
        if not isinstance(stamp, bool):
            sub(b, "ImportoBollo", d2(stamp))
    sub(doc, "ImportoTotaleDocumento", d2(gross))
    notes = [spec.get("note")] + ([countries.IT_SPLIT] if spec.get("split_payment") else [])
    if mny["paid"]:
        # FatturaPA has no element for an amount paid in advance: the reason line says it and the payment below
        # is the amount still due.
        notes.append("Acconto versato: %s %s" % (d2(mny["paid"]), str(spec.get("currency") or "EUR").upper()))
    for text in [n for n in notes if n]:
        for i in range(0, len(str(text)), 200):
            sub(doc, "Causale", latin(str(text)[i:i + 200], 200))
    if spec.get("order_reference"):
        sub(sub(dg, "DatiOrdineAcquisto"), "IdDocumento", latin(spec["order_reference"], 20))
    if spec.get("preceding_invoice"):
        ref = sub(dg, "DatiFattureCollegate")
        sub(ref, "IdDocumento", latin(spec["preceding_invoice"], 20))
        if spec.get("preceding_invoice_date"):
            sub(ref, "Data", spec["preceding_invoice_date"])
    goods = sub(body, "DatiBeniServizi")
    for l, src in zip(lines, spec["lines"]):
        li = sub(goods, "DettaglioLinee")
        sub(li, "NumeroLinea", l["id"])
        sub(li, "Descrizione", latin(l["name"], 1000))
        sub(li, "Quantita", d8(l["qty"]))
        sub(li, "UnitaMisura", UNITS.get(str(l["unit"]).upper(), str(l["unit"]))[:10])
        sub(li, "PrezzoUnitario", d8(l["price"]))
        if l["disc"]:
            # A discount on the line (SC, sconto): its percentage when the order gave one, else its amount.
            sc = sub(li, "ScontoMaggiorazione")
            sub(sc, "Tipo", "SC")
            if l["pct"]:
                sub(sc, "Percentuale", d2(l["pct"]))
            else:
                sub(sc, "Importo", d2(l["disc"]))
        sub(li, "PrezzoTotale", d2(l["net"]))
        sub(li, "AliquotaIVA", d2(l["rate"]))
        if l["nature"]:
            sub(li, "Natura", l["nature"])
    for (rate, nature), g in sorted(groups.items(), key=lambda kv: (-kv[0][0], kv[0][1])):
        r = sub(goods, "DatiRiepilogo")
        sub(r, "AliquotaIVA", d2(rate))
        if nature:
            sub(r, "Natura", nature)
        sub(r, "ImponibileImporto", d2(g["base"]))
        sub(r, "Imposta", d2(tax[(rate, nature)]))
        if not nature:
            # S is the split payment (art. 17-ter: the public buyer pays the IVA to the treasury), I the
            # ordinary case.
            sub(r, "EsigibilitaIVA", "S" if spec.get("split_payment") else "I")
        elif g["reason"]:
            sub(r, "RiferimentoNormativo", latin(g["reason"], 100))
    pay = spec.get("payment") or {}
    if not credit and (pay.get("iban") or pay.get("means_code") or spec.get("due_date")):
        dp = sub(body, "DatiPagamento")
        sub(dp, "CondizioniPagamento", "TP02")        # TP02: paid in one amount
        det = sub(dp, "DettaglioPagamento")
        sub(det, "ModalitaPagamento", MEANS.get(str(pay.get("means_code") or "58"), "MP05"))
        if spec.get("due_date"):
            sub(det, "DataScadenzaPagamento", spec["due_date"])
        # Under the split payment the customer pays the seller the net alone.
        sub(det, "ImportoPagamento", d2((net_total if spec.get("split_payment") else gross) - mny["paid"]))
        if pay.get("iban"):
            sub(det, "IBAN", str(pay["iban"]).replace(" ", "").upper())
        if pay.get("bic"):
            sub(det, "BIC", str(pay["bic"]).replace(" ", "").upper())
    summary = dict(syntax="fatturapa", profile="FatturaPA 1.2.3 %s, not sent" % fmt, type_code=cii.type_code(spec),
                   lines=len(lines), total_excluding_vat=str(cii.r2(net_total)), total_vat=str(cii.r2(tax_total)),
                   total_including_vat=str(cii.r2(gross)), sent=False, **cii.money_summary(mny))
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
    ap = argparse.ArgumentParser(description="Create a FatturaPA 1.2.3 invoice or credit note from a JSON spec.")
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
