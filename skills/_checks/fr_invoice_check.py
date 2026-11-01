#!/usr/bin/env python3
"""The mentions a French seller's invoice carries, read off the page and the XML beside it.

  FR-SELLER    The seller: name, SIREN (nine digits whose check digit holds; BT-30 under scheme 0002,
               BR-FR-10), legal form, and for a company registered at the RCS its share capital and
               "RCS" with the register's city; its VAT number on the page when the XML has one.
               CGI annexe II art. 242 nonies A I 1° and 2°; service-public.fr F31808.
  FR-BUYER     The buyer: name and address, and for a French buyer its SIREN (BT-47, scheme 0002), a
               mention every invoice carries from 1 September 2026 (242 nonies A I 1° as amended by
               décret n° 2022-1299; BR-FR-11); its VAT number on the page when the XML has one.
  FR-PAYMENT   The payment terms of Code de commerce L441-9: the due date (BT-9, on the page), the
               late-payment penalty rate, the 40 euro indemnity for recovery costs (L441-10, D441-5)
               and the early-payment discount or its absence; each on the page and once as a coded
               note in the XML (PMD, PMT, AAB; XP Z12-012 BR-FR-05, BR-FR-06). A credit note that
               settles nothing skips the due date.
  FR-MENTIONS  The reform's mentions and the VAT wording: the nature of the operation (goods,
               services or both; 242 nonies A I 8° bis) on the page and as the billing framework B1,
               S1 or M1 in BT-23 (BR-FR-08); "Option pour le paiement de la taxe d'après les débits"
               on the page when the XML says VAT falls due on debits (BT-8 = 5; I 11° bis); the
               delivery address on the page when the XML has one (BG-15; I 7° bis); "Autoliquidation"
               for a reverse charge (I 13°) and the exemption's reason for an exempt line (I 12°).

check(rule_id, path, case, stage) -> (passed, evidence); passed is None when the seller is not French.
Standard library only; pdftotext reads the page.

A drafting check of what the file says against published rules. It never says an invoice is
lawful, that a VAT treatment is right for the person, or that the platforms will accept it; the
French rules in full run in EINV-FR-CTC, the validator.
"""
import json
import re
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import credit_note_check as cn  # noqa: E402
import einvoice_particulars as particulars  # noqa: E402

RULES = ("FR-SELLER", "FR-BUYER", "FR-PAYMENT", "FR-MENTIONS")
COMPANY_FORMS = {"SA", "SAS", "SASU", "SARL", "EURL", "SNC", "SCA", "SCS", "SE", "SELARL", "SELAS"}
OPERATION_CODE = {"B": "goods", "S": "services", "M": "both"}
OPERATION_WORDS = {"goods": re.compile(r"livraisons? de biens", re.I),
                   "services": re.compile(r"prestations? de services", re.I),
                   "both": re.compile(r"livraisons? de biens et (?:de )?prestations? de services", re.I)}


def digits(value):
    return re.sub(r"\D", "", str(value or ""))


def luhn(number):
    total = 0
    for i, c in enumerate(reversed(number)):
        d = int(c) * (2 if i % 2 else 1)
        total += d - 9 if d > 9 else d
    return total % 10 == 0


def flat(text):
    return re.sub(r"\s+", " ", text or "").strip()


def page_text(pdf):
    if pdf is None:
        return ""
    return flat(subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True).stdout)


def on_page(value, text):
    """A value on the page, in any spacing: 000 000 018, 000000018 and 10 000 € alike."""
    if not value:
        return True
    bare = re.sub(r"\s+", "", text)
    return flat(str(value)) in text or re.sub(r"\s+", "", str(value)) in bare


class Doc:
    def __init__(self, path, case=None, stage="first"):
        self.xml_path, self.inv, self.why = cn.load(path)
        self.pdf = cn.page_for(path)
        self.page = page_text(self.pdf)
        # The order beside the file, else the case's own truth when it describes the parties.
        self.src = cn.source_beside(path) or cn.truth_for(case, stage)

    def party(self, tag):
        return cn.find(self.inv.agr, tag)

    def seller_country(self):
        return cn.text(self.party("SellerTradeParty"), "PostalTradeAddress/CountryID").upper()


def legal_id(party):
    """(id, scheme) of a party's legal registration identifier (BT-30, BT-47)."""
    node = cn.find(party, "SpecifiedLegalOrganization/ID")
    if node is None:
        return "", ""
    return (node.text or "").strip(), node.get("schemeID") or ""


def seller_rule(d):
    seller = d.party("SellerTradeParty")
    src = d.src.get("seller") or {}
    problems = []
    name = cn.text(seller, "Name")
    siren, scheme = legal_id(seller)
    if not re.fullmatch(r"\d{9}", siren):
        problems.append("no nine-digit SIREN for the seller in the XML (BT-30; BR-FR-10)")
    else:
        if scheme != "0002":
            problems.append("the seller's SIREN %s has scheme %r; a SIREN is scheme 0002" % (siren, scheme))
        if not luhn(siren):
            problems.append("the seller's SIREN %s fails its check digit" % siren)
        if d.pdf is not None and not on_page(siren, d.page):
            problems.append("the seller's SIREN %s is not on the page" % siren)
    if d.pdf is not None:
        if name and name not in d.page:
            problems.append("the seller %s is not named on the page" % name)
        form = str(src.get("legal_form") or "").strip()
        if not form:
            problems.append("the order gives no legal form for the seller (F31808); ask for it")
        elif form not in d.page:
            problems.append("the legal form %s is not on the page" % form)
        if form.upper() in COMPANY_FORMS:
            # A particular the order declares unknown is EINV-PARTICULARS' to warn about; Code de commerce
            # R123-238 asks no capital of an SNC or an SCS.
            unknown = particulars.unknown_of(d.src)
            if form.upper() in ("SNC", "SCS") or "share_capital" in unknown:
                pass
            elif src.get("share_capital") in (None, ""):
                problems.append("a %s states its share capital (Code de commerce R123-238; F31808); the order gives none" % form)
            elif not re.search(r"capital de [\d\s  .,]+", d.page):
                problems.append("the share capital is not on the page")
            if "rcs" not in unknown and not re.search(r"\bRCS\s+\w+", d.page):
                problems.append("no \"RCS\" with the register's city on the page (Code de commerce R123-237; F31808)")
        vat = cn.text(seller, "SpecifiedTaxRegistration/ID")
        if vat and vat not in d.page:
            problems.append("the seller's VAT number %s is not on the page (242 nonies A I 2°)" % vat)
    return (not problems, "; ".join(problems) or "seller %s, SIREN %s%s" % (
        name, siren, ", legal form, capital and RCS on the page" if d.pdf is not None else ""))


def buyer_rule(d):
    buyer = d.party("BuyerTradeParty")
    problems = []
    name = cn.text(buyer, "Name")
    french = cn.text(buyer, "PostalTradeAddress/CountryID").upper() == "FR"
    siren, scheme = legal_id(buyer)
    if french:
        if not re.fullmatch(r"\d{9}", siren):
            problems.append("a French buyer and no nine-digit SIREN for it in the XML (BT-47; 242 nonies A I 1° "
                            "from 1 September 2026; BR-FR-11)")
        else:
            if scheme != "0002":
                problems.append("the buyer's SIREN %s has scheme %r; a SIREN is scheme 0002" % (siren, scheme))
            if not luhn(siren):
                problems.append("the buyer's SIREN %s fails its check digit" % siren)
            if d.pdf is not None and not on_page(siren, d.page):
                problems.append("the buyer's SIREN %s is not on the page" % siren)
    if d.pdf is not None:
        if name and name not in d.page:
            problems.append("the buyer %s is not named on the page" % name)
        for part in ("PostalTradeAddress/LineOne", "PostalTradeAddress/CityName"):
            value = cn.text(buyer, part)
            if value and value not in d.page:
                problems.append("the buyer's address (%s) is not on the page" % value)
        vat = cn.text(buyer, "SpecifiedTaxRegistration/ID")
        if vat and vat not in d.page:
            problems.append("the buyer's VAT number %s is not on the page (242 nonies A I 2° and 4°)" % vat)
    return (not problems, "; ".join(problems) or "buyer %s%s" % (name, ", SIREN %s" % siren if siren else ""))


def notes(inv):
    out = []
    for n in inv.doc.findall("{*}IncludedNote"):
        out.append((cn.text(n, "SubjectCode"), cn.text(n, "Content")))
    return out


def payment_rule(d):
    problems = []
    coded = notes(d.inv)
    for code, what in (("PMD", "the late-payment penalties"), ("PMT", "the 40 euro recovery indemnity"),
                       ("AAB", "the early-payment discount or its absence")):
        found = [text for c, text in coded if c == code]
        if not found:
            problems.append("no note %s in the XML for %s (BR-FR-05)" % (code, what))
        elif len(found) > 1:
            problems.append("the note %s appears %d times; once (BR-FR-06)" % (code, len(found)))
    if d.pdf is not None:
        if not re.search(r"p[ée]nalit[ée]s? de retard", d.page, re.I):
            problems.append("no late-payment penalty rate on the page (Code de commerce L441-9)")
        if not re.search(r"indemnit[ée] forfaitaire pour frais de recouvrement[^.]*?40", d.page, re.I):
            problems.append("no 40 euro indemnity for recovery costs on the page (L441-10, D441-5)")
        if not re.search(r"escompte", d.page, re.I):
            problems.append("no early-payment discount, or its absence, on the page (L441-9)")
        due = cn.iso(cn.find(d.inv.st, "SpecifiedTradePaymentTerms/DueDateDateTime"))
        if d.inv.code == "380":
            if not due:
                problems.append("no due date in the XML (BT-9; L441-9: the date payment is due)")
            elif not any(f in d.page for f in cn.date_forms(due)):
                problems.append("the due date %s is not on the page" % due)
    return (not problems, "; ".join(problems) or "penalties, 40 euro indemnity and discount on the page and "
            "as the notes PMD, PMT and AAB%s" % (", due date on the page" if d.inv.code == "380" else ""))


def mentions_rule(d):
    problems = []
    root = d.inv.root
    process = cn.text(root, "ExchangedDocumentContext/BusinessProcessSpecifiedDocumentContextParameter/ID")
    if not re.fullmatch(r"[BSM][1-9]", process or ""):
        problems.append("BT-23 is %r; a French invoice states its billing framework, B1, S1 or M1 by the nature "
                        "of the operation (BR-FR-08)" % (process or "missing"))
        operation = ""
    else:
        operation = OPERATION_CODE[process[0]]
    want = str(d.src.get("operation") or "").strip().lower()
    want = {"biens": "goods", "mixte": "both", "mixed": "both", "les deux": "both"}.get(want, want)
    if operation and want in OPERATION_WORDS and want != operation:
        problems.append("the order says %s and BT-23 %s says %s" % (want, process, operation))
    if d.pdf is not None:
        if operation and not OPERATION_WORDS[operation].search(d.page):
            problems.append("the nature of the operation (%s) is not on the page (242 nonies A I 8° bis)" % operation)
        debits = [t for t in d.inv.st.findall("{*}ApplicableTradeTax") if cn.text(t, "DueDateTypeCode") == "5"]
        if (debits or d.src.get("vat_on_debits")) and not re.search(
                r"option pour le paiement de la taxe d.apr[eè]s les d[ée]bits", d.page, re.I):
            problems.append("VAT on debits and no \"Option pour le paiement de la taxe d'après les débits\" on the "
                            "page (I 11° bis)")
        if d.src.get("vat_on_debits") and not debits:
            problems.append("the order opts for VAT on debits and the XML's BT-8 is not 5 (BR-FR-MAP-03)")
        ship = cn.find(d.inv.tx, "ApplicableHeaderTradeDelivery/ShipToTradeParty/PostalTradeAddress")
        if ship is not None:
            for part in ("LineOne", "CityName"):
                value = cn.text(ship, part)
                if value and value not in d.page:
                    problems.append("the delivery address (%s) is not on the page (I 7° bis)" % value)
        cats = {cn.text(t, "CategoryCode") for t in d.inv.st.findall("{*}ApplicableTradeTax")}
        if "AE" in cats and not re.search(r"auto-?liquidation", d.page, re.I):
            problems.append("a reverse charge and no \"Autoliquidation\" on the page (I 13°)")
        for t in d.inv.st.findall("{*}ApplicableTradeTax"):
            reason = cn.text(t, "ExemptionReason")
            if cn.text(t, "CategoryCode") in ("E", "K", "G") and reason and flat(reason) not in d.page:
                problems.append("the exemption's reason %r is not on the page (I 12°)" % reason)
    return (not problems, "; ".join(problems) or "billing framework %s (%s)%s" % (
        process, operation, ", the mentions on the page" if d.pdf is not None else ""))


def check(rule_id, path, case, stage):
    if rule_id not in RULES:
        return None, "unknown rule %s" % rule_id
    d = Doc(path, case, stage)
    if d.inv is None:
        if (d.src.get("seller") or {}).get("country", "").upper() == "FR":
            return False, d.why or "no invoice XML to read"
        return None, d.why or "no invoice XML to read"
    if d.seller_country() != "FR":
        return None, "the seller is not French; the French mentions do not apply"
    return {"FR-SELLER": seller_rule, "FR-BUYER": buyer_rule, "FR-PAYMENT": payment_rule,
            "FR-MENTIONS": mentions_rule}[rule_id](d)


if __name__ == "__main__":
    for rule in RULES:
        ok, why = check(rule, sys.argv[1], {}, "first")
        print(json.dumps({"rule": rule, "passed": ok, "evidence": why}, ensure_ascii=False))
