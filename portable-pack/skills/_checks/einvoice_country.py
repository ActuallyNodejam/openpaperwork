#!/usr/bin/env python3
"""What each country's law asks an invoice to state, read off the printed page against the order beside it,
and, where the pack writes Peppol UBL, off the XML: Norway, Denmark, Finland, the United Kingdom, Australia,
Canada and the United States.

  NO-SELLER     bokføringsforskriften § 5-1-2: the seller's name and organisasjonsnummer (nine digits whose
                modulus 11 check digit holds), followed by MVA when the seller charges VAT; "Foretaksregisteret"
                for an AS, ASA or NUF (and NO-R-002 in the UBL); the UBL VAT number NO<org.nr.>MVA (NO-R-001).
  NO-CONTENT    § 5-1-1: number and date, the buyer's name, the time and place of delivery, the due date, VAT
                stated in Norwegian kroner, one total per rate (§ 5-1-5), and "Omvendt avgiftsplikt –
                Merverdiavgift ikke beregnet" for a reverse charge (nr. 7).
  DK-INVOICE    momsbekendtgørelsen § 58, stk. 1 (fuld faktura): date, number, the seller's CVR-nummer, both
                parties' names and addresses, each line's quantity and unit price, the rate and the VAT
                amount; the registration and account number for a Danish bank transfer; the CVR under scheme
                0184 in the UBL (DK-R-002, DK-R-014).
  FI-INVOICE    arvonlisäverolaki 209 e §: date, number, the seller's VAT identifier (FI and its Y-tunnus,
                whose check digit holds), both parties' names and addresses, the delivery date, the rate and
                the VAT; "Käännetty verovelvollisuus" and the buyer's VAT identifier for a reverse charge.
  FI-PAYMENT    The Finnish payment lines: the due date (eräpäivä), the IBAN, a viitenumero whose 7-3-1 check
                digit holds, and a bank barcode (Finanssiala, version 4) that encodes that IBAN, total,
                reference and due date.
  UK-VAT-INVOICE  HMRC VAT Notice 700/21 4.1 (OGL v3.0): number, date, the supplier's name, address and VAT
                registration number (GB and nine digits whose check digits hold), the customer's name and
                address, the tax point when it differs from the date, each line's quantity, unit price and
                rate, the total excluding VAT, the total VAT, in sterling when the invoice is in another
                currency.
  AU-TAX-INVOICE  GST Act 1999 s 29-70 and GST Regulations 2019 s 29-70.01 (CC BY 4.0): headed Tax invoice
                (an adjustment note for a credit, s 29-75), the supplier's name and ABN (modulus 89), the
                date, the GST, each GST-free line marked when some are taxed; from A$1,000 the buyer's name
                and its address or ABN.
  CA-GST-HST    Input Tax Credit Information (GST/HST) Regulations SOR/91-45 s. 3: the supplier's name, the
                date and the total; from $100 the GST/HST registration number and each tax; from $500 the
                buyer's name and the terms of payment; a line that is not taxed is marked; the QST number
                when QST is charged.
  US-SALES-TAX  No federal invoice standard and no VAT: the page carries no VAT wording, each sales tax the
                order lists is on the page with its rate and amount, and subtotal plus taxes is the total.

Wave 8 (the texts, versions and licences are in the pack's guidelines):

  BE-INVOICE    Royal Decree no. 1 of 29 December 1992, art. 5 § 1 and art. 12 § 3; Code of companies and
                associations art. 2:20: number and date, the supplier's name,
                address, enterprise number (modulus 97) and VAT number BE and the same digits, the customer's
                name and address and, for a business customer, its VAT number, each line's unit price, the VAT
                per rate, the fixed reverse-charge mention of 9°bis ("Btw verlegd", "Autoliquidation", in
                German the Directive's "Steuerschuldnerschaft des Leistungsempfängers"), the invoice a
                credit note corrects; a structured communication whose check digits hold (the first ten
                digits modulo 97, 97 for a remainder of 0); in the UBL the enterprise number under 0208.
  NL-INVOICE    Wet op de omzetbelasting 1968 art. 34f, 35a and Handelsregisterwet 2007 art. 27: number and
                date, the supplier's btw-id and KvK number, both parties' names and
                addresses, each line's unit price, the VAT per rate, the fixed mention "btw verlegd" (lid 1
                m) and the customer's btw-id for a reverse charge, the credited invoice; in the UBL the KvK
                under 0106 (NL-R-003).
  AT-INVOICE    UStG 1994 § 11 Abs. 1 Z 3 lit. a to i and Abs. 1a: number and date, the supplier's UID-Nummer
                (the ministry's check digit, lit. i), both parties' names and addresses, the date or period
                of supply (lit. d), the VAT per rate, the recipient's UID-Nummer over 10 000 euros (lit. b),
                a note of the recipient's tax liability in any clear words (Abs. 1a fixes none), the
                Firmenbuchnummer when the order gives one, the corrected invoice.
  IE-VAT-INVOICE  VAT Consolidation Act 2010 s. 66, VAT Regulations 2010 reg. 20: number and date, the
                supplier's name, address and VAT number (its form), the customer's name and address, the
                date of supply, each line's unit price and rate, the VAT per rate in euro and the totals, the
                customer's VAT number and any clear indication that a reverse charge applies (reg.
                20(2)(e) fixes no words), a credit note's reason, the customer's registration number and
                the credited invoice (s. 67, reg. 20(5)(d), (f)).

Wave 9 (each country's national file sits beside the page; the texts are in the pack's guidelines):

  ES-INVOICE    Real Decreto 1619/2012 art. 6.1 and art. 15: number, series when there is one, date, the
                seller's NIF (nine characters in a published form), both parties' names and addresses, the
                recipient's NIF for a supply in Spain, a reverse charge or an exempt intra-EU supply, each
                line's unit price and rate, the tax per rate, the date of the supply when it differs, the
                exemption's reference, «inversión del sujeto pasivo» for a reverse charge; a rectifying invoice
                has a series of its own and names the invoice it rectifies; in the Facturae beside the page,
                class OR with its Corrective block for a rectifying invoice, OO otherwise, and no signature
                passed off as one.
  IT-INVOICE    DPR 633/1972 art. 21 comma 2 and 6, art. 17 (from 1 January 2027 the Testo unico IVA,
                D.Lgs. 10/2026, art. 72 and 64): number and date, the seller's partita IVA, both parties' names
                and addresses, the customer's partita IVA or codice fiscale, each line's unit price and rate,
                the tax per rate, the date of the supply when it differs, the annotation in place of the tax,
                «inversione contabile» for a reverse charge, «scissione dei pagamenti» and the stamp-duty
                annotation when the order asks for them; in the FatturaPA beside the page, TD04 with its
                DatiFattureCollegate for a credit note, TD01 otherwise.
  PL-INVOICE    Ustawa o VAT art. 106e ust. 1 and art. 106j ust. 2: number and date, the seller's NIP (ten
                digits in the form FA(3) takes), both parties' names and addresses, the buyer's tax number,
                each line's net unit price and rate, the tax per rate, the date of the supply when it
                differs, „odwrotne obciążenie”, „mechanizm podzielonej płatności” and „metoda kasowa” when the
                order carries them, the ground of an exemption, the tax in złoty, a correcting invoice's
                invoice and its KSeF number; in the FA(3) beside the page, KOR with DaneFaKorygowanej for a
                correcting invoice and the same annotations (P_16, P_18, P_18A).

check(rule_id, path, case, stage) -> (passed, evidence); passed is None when the seller is another
country's. A drafting check of what the file says against published rules; it never says an invoice is
lawful or a tax treatment right. Standard library only; pdftotext reads the page.
"""
import json
import re
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "_shared"))
import doc_amounts  # noqa: E402
import credit_note_check as cn  # noqa: E402
import einvoice_ids as ids  # noqa: E402
import einvoice_particulars as particulars  # noqa: E402

RULES = ("NO-SELLER", "NO-CONTENT", "DK-INVOICE", "FI-INVOICE", "FI-PAYMENT", "UK-VAT-INVOICE",
         "AU-TAX-INVOICE", "CA-GST-HST", "US-SALES-TAX", "BE-INVOICE", "NL-INVOICE", "AT-INVOICE", "IE-VAT-INVOICE",
         "ES-INVOICE", "IT-INVOICE", "PL-INVOICE")
COUNTRY = {"NO": "NO", "DK": "DK", "FI": "FI", "UK": "GB", "AU": "AU", "CA": "CA", "US": "US", "BE": "BE", "NL": "NL",
           "AT": "AT", "IE": "IE", "ES": "ES", "IT": "IT", "PL": "PL"}
# The reverse-charge mention, by the seller's country. Belgium and the Netherlands fix the words (Royal
# Decree no. 1 art. 5 § 1 9°bis, one mention per language; Wet OB 1968 art. 35a lid 1 m), with the
# Directive's English mention (Art. 226(11a)) for a page written in English. Austria and Ireland ask for a
# note and fix no words (UStG § 11 Abs. 1a; VAT Regulations 2010 reg. 20(2)(e)), so any clear note that the
# customer owes the tax passes.
W8_REVERSE = {
    "BE": re.compile(r"Autoliquidation|Btw verlegd|Steuerschuldnerschaft des Leistungsempfängers|Reverse charge", re.I),
    "NL": re.compile(r"Btw verlegd|Reverse charge|VAT reverse[- ]charged", re.I),
    "AT": re.compile(r"Steuerschuldnerschaft|Übergang der Steuerschuld|Steuerschuld\b.{0,60}\b(geht|übergeht|über)\b|"
                     r"Reverse[- ]Charge", re.I),
    "IE": re.compile(r"reverse[- ]charge|\b(customer|recipient|purchaser|buyer)\b.{0,60}\b(liable|accounts? for)\b.{0,40}\bVAT\b|"
                     r"\bVAT\b.{0,60}\b(accounted for|payable|due)\b.{0,30}\bby the (customer|recipient|purchaser|buyer)\b",
                     re.I),
    # Wave 9: all three laws fix the words (Real Decreto 1619/2012 art. 6.1 m; DPR 633/1972 art. 17 and art. 21
    # comma 6-bis; ustawa o VAT art. 106e ust. 1 pkt 18).
    "ES": re.compile(r"inversi[oó]n del sujeto pasivo", re.I),
    "IT": re.compile(r"inversione contabile", re.I),
    "PL": re.compile(r"odwrotne obciążenie", re.I),
}
NO_REVERSE = re.compile(r"Omvendt avgiftsplikt\s*[–-]\s*Merverdiavgift ikke beregnet")
NO_FORETAK = {"AS", "ASA", "NUF"}
CENT = Decimal("0.01")


def r2(x):
    return Decimal(str(x)).quantize(CENT, rounding=ROUND_HALF_UP)


def flat(text):
    return re.sub(r"[\s  ]+", " ", text or "").strip()


def nospace(text):
    return re.sub(r"[\s  ]+", "", text or "")


def amount_forms(value):
    """1234.5 -> 1234.50, 1,234.50, 1 234,50, 1.234,50, 1234,50: every way the page may print it."""
    v = r2(value)
    sign = "-" if v < 0 else ""
    whole, cents = str(abs(v)).split(".")
    groups = []
    w = whole
    while len(w) > 3:
        groups.insert(0, w[-3:])
        w = w[:-3]
    groups.insert(0, w)
    out = {whole + "." + cents, whole + "," + cents}
    for g, d in ((",", "."), (" ", ","), (".", ","), (" ", ".")):
        out.add(g.join(groups) + d + cents)
    return {sign + o for o in out}


def has_amount(text, value):
    t = flat(text)
    return any(f in t for f in amount_forms(value))


def legal_form(p):
    form = str((p or {}).get("legal_form") or "").strip()
    if form:
        return form
    m = re.search(r"\b(AS|ASA|NUF|A/S|ApS|Oy|Oyj|Ltd|Limited|PLC|LLP|Inc\.?|LLC)$", str((p or {}).get("name") or "").strip())
    return m.group(1) if m else ""


def credit(src):
    code = str(src.get("type_code") or "").strip()
    return code == "381" or (not code and bool(src.get("preceding_invoice")))


def line_net(l):
    return doc_amounts.line_amounts(l)["net"]


def settlement(src):
    """The document's money (skills/_shared/doc_amounts.py): lines, allowances, VAT, grand total, paid, due."""
    return doc_amounts.settle(src, [dict(cat=str(l.get("vat_category") or "S").upper(),
                                         rate=Decimal(str(l.get("vat_rate") or 0)), net=line_net(l))
                                    for l in src.get("lines") or []])


def groups_of(src):
    m = settlement(src)
    return {k: (r2(b), m["tax"][k]) for k, b in m["groups"].items()}


def totals(src):
    m = settlement(src)
    return r2(m["basis"]), r2(m["tax_total"]), r2(m["grand"])


def date_forms(iso):
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", str(iso or ""))
    if not m:
        return [str(iso)] if iso else []
    y, mo, d = m.groups()
    return [iso, "%s.%s.%s" % (d, mo, y), "%d.%d.%s" % (int(d), int(mo), y), "%s/%s/%s" % (d, mo, y),
            "%s/%s/%s" % (mo, d, y), "%s-%s-%s" % (d, mo, y), "%d/%s/%s" % (int(d), mo, y),
            # CLDR es writes d/M/y (30/9/2026) and CLDR pl d.MM.y (5.09.2026).
            "%d/%d/%s" % (int(d), int(mo), y), "%d.%s.%s" % (int(d), mo, y)]


def has_date(text, iso):
    t = flat(text)
    return any(f in t for f in date_forms(iso))


def has_name(text, value):
    return bool(value) and flat(str(value)) in flat(text)


def ubl_root(path):
    xml, inv, _why = cn.load(path)
    return inv.root if inv is not None and inv != "finvoice" and getattr(inv, "ubl", False) else None


def ubl_text(root, path):
    return cn.text(root, path) if root is not None else ""


def parties(src):
    return src.get("seller") or {}, src.get("buyer") or {}


def address_on(text, p):
    """The party's name, street and town are on the page. The buyer's address is written as its post office
    reads it (skills/_shared/letter.py postal_lines): the town in capitals in Belgium, the Netherlands,
    Norway, Finland and the English-speaking countries, no punctuation in an Irish or US address. GENT is
    the town Gent, so the street and the town are compared without case and without points and commas;
    the name is the party's own and is compared as written."""
    plain = lambda s: re.sub(r"[.,]", "", flat(str(s))).casefold()
    page = plain(text)
    return [k for k in ("name", "street", "city")
            if p.get(k) and not (has_name(text, p[k]) or (k != "name" and plain(p[k]) in page))]


# ---- Norway ------------------------------------------------------------------------------------

def no_seller(src, text, root):
    s, _b = parties(src)
    num = ids.digits(s.get("org_number"))
    problems = []
    if not ids.no_orgnr_ok(num):
        problems.append("the organisasjonsnummer %r is not nine digits whose modulus 11 check digit holds" % s.get("org_number"))
    elif num not in nospace(text):
        problems.append("the page does not give the seller's organisasjonsnummer %s (§ 5-1-2)" % ids.no_orgnr_text(num))
    elif s.get("vat_id") and not re.search(r"%s\s*MVA" % r"\s*".join(num), flat(text)):
        problems.append("the organisasjonsnummer is not followed by MVA on the page, and the seller charges VAT (§ 5-1-2)")
    if not has_name(text, s.get("name")):
        problems.append("the seller's name is not on the page")
    if legal_form(s).upper() in NO_FORETAK:
        if "Foretaksregisteret" not in text:
            problems.append("an %s writes Foretaksregisteret on its invoices (§ 5-1-2; foretaksregisterloven "
                            "2025 § 7-2, § 10-2 of the 1985 act until 2026)" % legal_form(s))
        if root is not None and not any(cn.text(ts, "CompanyID") == "Foretaksregisteret"
                                        for ts in root.iter() if ts.tag.endswith("}PartyTaxScheme")):
            problems.append("the UBL has no PartyTaxScheme Foretaksregisteret under TAX (NO-R-002)")
    if root is not None:
        vat = [cn.text(ts, "CompanyID") for ts in cn.find(root, "AccountingSupplierParty/Party").findall("{*}PartyTaxScheme")
               if cn.text(ts, "TaxScheme/ID") == "VAT"]
        if s.get("vat_id") and not any(re.fullmatch(r"NO%sMVA" % num, v) for v in vat):
            problems.append("the UBL seller VAT number is %s, NO-R-001 wants NO%sMVA" % (", ".join(vat) or "missing", num))
    return not problems, "; ".join(problems) or "Org.nr. %s%s%s" % (
        ids.no_orgnr_text(num), " MVA" if s.get("vat_id") else "",
        ", Foretaksregisteret" if legal_form(s).upper() in NO_FORETAK else "")


def no_content(src, text, root):
    s, b = parties(src)
    problems = []
    if src.get("number") and str(src["number"]) not in text:
        problems.append("the invoice number %s is not on the page" % src["number"])
    if not has_date(text, src.get("issue_date")):
        problems.append("the date %s is not on the page (§ 5-1-1 nr. 1)" % src.get("issue_date"))
    if not has_name(text, b.get("name")):
        problems.append("the buyer's name is not on the page (§ 5-1-2)")
    if not credit(src):
        if not src.get("delivery_date") or not has_date(text, src["delivery_date"]):
            problems.append("the time of delivery is not on the page (§ 5-1-1 nr. 4)")
        if "Leveringssted" not in text:
            problems.append("the place of delivery is not on the page (§ 5-1-1 nr. 4)")
        if not src.get("due_date") or not has_date(text, src["due_date"]):
            problems.append("the due date is not on the page (§ 5-1-1 nr. 5)")
    net, vat, gross = totals(src)
    cur = str(src.get("currency") or "NOK").upper()
    if vat and cur != "NOK":
        rate = src.get("exchange_rate")
        if not rate or "NOK" not in text or not has_amount(text, vat * Decimal(str(rate))):
            problems.append("the invoice is in %s and its VAT is not stated in NOK (§ 5-1-1 nr. 6)" % cur)
    groups = groups_of(src)
    missing_rate = [k for k, (_base, v) in groups.items() if k[0] == "S" and not has_amount(text, v)]
    if missing_rate:
        problems.append("the VAT at %s %% is not on the page as its own total (§ 5-1-5)" % ", ".join(str(k[1]) for k in missing_rate))
    if any(k[0] == "AE" for k in groups) and not NO_REVERSE.search(flat(text)):
        problems.append("a reverse charge without \"Omvendt avgiftsplikt – Merverdiavgift ikke beregnet\" (§ 5-1-1 nr. 7)")
    return not problems, "; ".join(problems) or "number, date, delivery time and place, due date and VAT per rate on the page"


# ---- Denmark -----------------------------------------------------------------------------------

def dk_invoice(src, text, root):
    s, b = parties(src)
    problems = []
    cvr = ids.digits(s.get("cvr") or s.get("vat_id"))
    if len(cvr) != 8:
        problems.append("no eight-digit CVR-nummer for the seller (§ 58, stk. 1, nr. 3)")
    elif cvr not in nospace(text):
        problems.append("the seller's CVR-nummer %s is not on the page (§ 58, stk. 1, nr. 3)" % cvr)
    for who, p, n in (("seller", s, 4), ("buyer", b, 5)):
        miss = address_on(text, p)
        if miss:
            problems.append("the %s's %s not on the page (§ 58, stk. 1, nr. %d)" % (who, ", ".join(miss), n))
    if src.get("number") and str(src["number"]) not in text:
        problems.append("the number %s is not on the page (nr. 2)" % src["number"])
    if not has_date(text, src.get("issue_date")):
        problems.append("the date is not on the page (nr. 1)")
    for l in src.get("lines") or []:
        if not has_amount(text, l.get("unit_price") or 0):
            problems.append("the unit price of %r is not on the page (nr. 8)" % l.get("name"))
    for (cat, rate), (_base, vat) in groups_of(src).items():
        if cat == "S" and not has_amount(text, vat):
            problems.append("the VAT at %s %% is not on the page (nr. 10)" % rate)
    pay = src.get("payment") or {}
    if str(pay.get("means_code")) in ("31", "42") and not (str(pay.get("bank_reg")) in text and str(pay.get("account")) in text):
        problems.append("the registration and account number for the bank transfer are not on the page")
    if root is not None:
        le = cn.find(root, "AccountingSupplierParty/Party/PartyLegalEntity/CompanyID")
        if le is None or (le.get("schemeID") != "0184"):
            problems.append("the UBL seller has no CVR under scheme 0184 (DK-R-002, DK-R-014)")
    return not problems, "; ".join(problems) or "CVR %s, both parties, prices, rate and VAT on the page" % cvr


# ---- Finland -----------------------------------------------------------------------------------

def fi_invoice(src, text, root):
    s, b = parties(src)
    problems = []
    yt = str(s.get("business_id") or "")
    if not ids.fi_ytunnus_ok(yt):
        problems.append("the Y-tunnus %r is not seven digits, a hyphen and a check digit that holds" % yt)
    vat = s.get("vat_id") or (ids.fi_vat_of(yt) if ids.fi_ytunnus_ok(yt) else "")
    if vat and vat.replace(" ", "") not in nospace(text):
        problems.append("the seller's VAT identifier %s is not on the page (AVL 209 e § 3)" % vat)
    for who, p in (("seller", s), ("buyer", b)):
        miss = address_on(text, p)
        if miss:
            problems.append("the %s's %s not on the page (209 e § 5)" % (who, ", ".join(miss)))
    if src.get("number") and str(src["number"]) not in text:
        problems.append("the number %s is not on the page (209 e § 2)" % src["number"])
    if not has_date(text, src.get("issue_date")):
        problems.append("the date is not on the page (209 e § 1)")
    if not credit(src) and (not src.get("delivery_date") or not has_date(text, src["delivery_date"])):
        problems.append("the delivery date is not on the page (209 e § 7)")
    groups = groups_of(src)
    for (cat, rate), (_base, v) in groups.items():
        if cat == "S" and not has_amount(text, v):
            problems.append("the VAT at %s %% is not on the page (209 e § 10)" % rate)
    if any(k[0] == "AE" for k in groups):
        if "Käännetty verovelvollisuus" not in text:
            problems.append("a reverse charge without \"Käännetty verovelvollisuus\" (209 e § 12)")
        if not b.get("vat_id") or b["vat_id"].replace(" ", "") not in nospace(text):
            problems.append("a reverse charge without the buyer's VAT identifier (209 e § 4)")
    if credit(src) and src.get("preceding_invoice") and str(src["preceding_invoice"]) not in text:
        problems.append("the credit note does not refer to invoice %s (209 e § 18)" % src["preceding_invoice"])
    return not problems, "; ".join(problems) or "Y-tunnus %s, VAT identifier, both parties, dates and VAT on the page" % yt


def fi_payment(src, text, root):
    if credit(src):
        return None, "a credit note asks for no payment"
    pay = src.get("payment") or {}
    problems = []
    if not src.get("due_date") or not has_date(text, src["due_date"]):
        problems.append("the eräpäivä is not on the page")
    iban = str(pay.get("iban") or "")
    if iban and not ids.iban_ok(iban):
        problems.append("the IBAN %s fails its check digits" % iban)
    elif iban and iban.replace(" ", "") not in nospace(text):
        problems.append("the IBAN is not on the page")
    ref = pay.get("reference")
    if ref:
        if not ids.fi_reference_ok(ref):
            problems.append("the viitenumero %s fails its check digit" % ref)
        elif ids.digits(ref) not in nospace(text) and str(ref).replace(" ", "") not in nospace(text):
            problems.append("the viitenumero %s is not on the page" % ref)
    m = re.search(r"(?<!\d)(4\d{53})(?!\d)", flat(text))
    if m:
        want = ids.fi_virtual_barcode(iban, settlement(src)["due"], ref, src.get("due_date"))
        if want and m.group(1) != want:
            problems.append("the bank barcode %s does not encode this IBAN, total, reference and due date (%s)" % (m.group(1), want))
    return not problems, "; ".join(problems) or "due date, IBAN%s%s on the page" % (
        ", viitenumero %s" % ids.fi_reference_text(ref) if ref else "", ", the bank barcode matches" if m else "")


# ---- United Kingdom ----------------------------------------------------------------------------

def uk_invoice(src, text, root):
    s, b = parties(src)
    problems = []
    vat = str(s.get("vat_id") or "")
    if not ids.gb_vat_ok(vat):
        problems.append("the supplier's VAT registration number %r is not GB and nine digits whose check digits hold" % vat)
    elif ids.digits(vat) not in nospace(text):
        problems.append("the supplier's VAT registration number is not on the page (4.1)")
    for who, p in (("supplier", s), ("customer", b)):
        miss = address_on(text, p)
        if miss:
            problems.append("the %s's %s not on the page (4.1)" % (who, ", ".join(miss)))
    if src.get("number") and str(src["number"]) not in text:
        problems.append("the sequential number %s is not on the page" % src["number"])
    if not has_date(text, src.get("issue_date")):
        problems.append("the date of issue is not on the page")
    if src.get("delivery_date") and src["delivery_date"] != src.get("issue_date") and not has_date(text, src["delivery_date"]):
        problems.append("the time of supply %s is not on the page (4.1)" % src["delivery_date"])
    for l in src.get("lines") or []:
        if not has_amount(text, l.get("unit_price") or 0):
            problems.append("the unit price of %r is not on the page (4.1)" % l.get("name"))
    rates = {format(Decimal(str(l.get("vat_rate") or 0)).normalize(), "f") for l in src.get("lines") or []}
    missing = [r for r in rates if not re.search(r"(?<![\d.])%s\s?%%" % re.escape(r), flat(text))]
    if missing:
        problems.append("the rate %s %% is not on the page beside its lines (4.1)" % ", ".join(sorted(missing)))
    net, vat_total, gross = totals(src)
    if not has_amount(text, net):
        problems.append("the total excluding VAT is not on the page")
    if not has_amount(text, vat_total):
        problems.append("the total VAT is not on the page")
    cur = str(src.get("currency") or "GBP").upper()
    if cur != "GBP" and vat_total:
        rate = src.get("exchange_rate")
        if not rate or "GBP" not in text or not has_amount(text, vat_total * Decimal(str(rate))):
            problems.append("the invoice is in %s and its total VAT is not stated in sterling (4.1)" % cur)
    return not problems, "; ".join(problems) or "VAT registration %s and every 4.1 detail on the page" % ids.gb_vat_text(vat)


# ---- Australia ---------------------------------------------------------------------------------

def au_invoice(src, text, root):
    s, b = parties(src)
    problems = []
    head = flat(text)[:600].lower()
    word = "adjustment note" if credit(src) else "tax invoice"
    if word not in head:
        problems.append("the page is not headed %s (GST Regulations s 29-70.01; s 29-75)" % word.capitalize())
    abn = ids.digits(s.get("abn"))
    if not ids.au_abn_ok(abn):
        problems.append("the supplier's ABN %r fails its modulus 89 check" % s.get("abn"))
    elif abn not in nospace(text):
        problems.append("the supplier's ABN is not on the page (GST Act s 29-70(1)(c))")
    if not has_name(text, s.get("name")):
        problems.append("the supplier's name is not on the page")
    if not has_date(text, src.get("issue_date")):
        problems.append("the date of issue is not on the page")
    net, gst, gross = totals(src)
    if gst and not (has_amount(text, gst) or "includes GST" in text):
        problems.append("the GST amount is not on the page")
    cats = {str(l.get("vat_category") or "S").upper() for l in src.get("lines") or []}
    if "S" in cats and cats - {"S"} and "GST-free" not in text:
        problems.append("some lines are GST-free and the page does not mark them (the extent each sale is taxable)")
    if gross >= 1000:
        ok = has_name(text, b.get("name")) and (has_name(text, b.get("street")) or
                                                 (b.get("abn") and ids.digits(b["abn"]) in nospace(text)))
        if not ok:
            problems.append("from A$1,000 the page states the buyer's name and its address or ABN (s 29-70.01)")
    return not problems, "; ".join(problems) or "%s, ABN %s, GST %s on the page" % (
        word.capitalize(), ids.au_abn_text(abn), gst)


# ---- Canada ------------------------------------------------------------------------------------

def taxable(l):
    v = l.get("taxable")
    return True if v is None else bool(v) and str(v).lower() not in ("false", "no", "0", "exempt")


def sales_taxes(src):
    base = sum((line_net(l) for l in src.get("lines") or [] if taxable(l)), Decimal(0))
    return [(str(t.get("name") or ""), Decimal(str(t.get("rate") or 0)), r2(base),
             r2(base * Decimal(str(t.get("rate") or 0)) / 100)) for t in src.get("taxes") or []]


def ca_invoice(src, text, root):
    s, b = parties(src)
    problems = []
    taxes = sales_taxes(src)
    net = r2(sum((line_net(l) for l in src.get("lines") or []), Decimal(0)))
    total = r2(net + sum((t[3] for t in taxes), Decimal(0)))
    if not has_name(text, s.get("name")):
        problems.append("the supplier's name is not on the page (SOR/91-45 s. 3(a)(i))")
    if not has_date(text, src.get("issue_date")):
        problems.append("the invoice date is not on the page (s. 3(a)(ii))")
    if not has_amount(text, total):
        problems.append("the total %s is not on the page (s. 3(a)(iii))" % total)
    names = " ".join(t[0] for t in taxes).upper()
    if total >= 100 and taxes and re.search(r"GST|HST|TPS|TVH", names):
        m = ids.CA_GST.match(str(s.get("gst_number") or ""))
        if not m:
            problems.append("from $100 the GST/HST registration number (123456789 RT0001) is required (s. 3(b)(i))")
        elif m.group(1) not in nospace(text) or ("RT" + m.group(2)) not in nospace(text):
            problems.append("the GST/HST registration number is not on the page (s. 3(b)(i))")
        for name, rate, _base, amount in taxes:
            if not has_amount(text, amount):
                problems.append("the %s amount %s is not on the page (s. 3(b)(ii))" % (name, amount))
    if re.search(r"QST|TVQ", names) and not (s.get("qst_number") and ids.digits(s["qst_number"])[:10] in nospace(text)):
        problems.append("QST is charged and the QST registration number is not on the page")
    if not all(taxable(l) for l in src.get("lines") or []) and not re.search(r"Exempt|Exonéré|Non-taxable", text):
        problems.append("some lines are not taxed and the page does not mark them (s. 3(b)(ii))")
    if total >= 500:
        if not has_name(text, b.get("name")):
            problems.append("from $500 the buyer's name is on the invoice (s. 3(c)(i))")
        if not src.get("payment_terms") or not re.search(r"Terms|Modalités", text):
            problems.append("from $500 the terms of payment are on the invoice (s. 3(c)(ii))")
    return not problems, "; ".join(problems) or "the SOR/91-45 details for a total of %s on the page" % total


# ---- United States -----------------------------------------------------------------------------

VAT_WORDS = re.compile(r"\bVAT\b|value[- ]added tax|\bGST\b|Mehrwertsteuer|\bMoms\b|\bMVA\b", re.I)


def us_invoice(src, text, root):
    problems = []
    if VAT_WORDS.search(text):
        problems.append("VAT wording on a US invoice: %r; the US has sales tax, no VAT" % VAT_WORDS.search(text).group(0))
    taxes = sales_taxes(src)
    for name, rate, _base, amount in taxes:
        if name and name not in flat(text):
            problems.append("the tax %r is not named on the page" % name)
        if not has_amount(text, amount):
            problems.append("the %s amount %s is not on the page" % (name, amount))
    net = r2(sum((line_net(l) for l in src.get("lines") or []), Decimal(0)))
    total = r2(net + sum((t[3] for t in taxes), Decimal(0)))
    if not has_amount(text, net):
        problems.append("the subtotal %s is not on the page" % net)
    if not has_amount(text, total):
        problems.append("the total %s (subtotal plus each tax) is not on the page" % total)
    return not problems, "; ".join(problems) or "%d sales tax line(s), subtotal %s, total %s, no VAT wording" % (len(taxes), net, total)


# ---- wave 8 ---------------------------------------------------------------------------------------

def _common(src, text, problems, rule, lines_price=True):
    """Number, date, unit prices and the VAT per standard rate on the page; the credited invoice."""
    if src.get("number") and str(src["number"]) not in text:
        problems.append("the number %s is not on the page (%s)" % (src["number"], rule))
    if not has_date(text, src.get("issue_date")):
        problems.append("the date of issue is not on the page (%s)" % rule)
    if lines_price:
        for l in src.get("lines") or []:
            if not has_amount(text, l.get("unit_price") or 0):
                problems.append("the unit price of %r is not on the page (%s)" % (l.get("name"), rule))
    for (cat, rate), (_base, vat) in groups_of(src).items():
        if cat == "S" and not has_amount(text, vat):
            problems.append("the VAT at %s %% is not on the page as its own amount (%s)" % (rate, rule))
    country = str((src.get("seller") or {}).get("country") or "").upper()
    if any(k[0] == "AE" for k in groups_of(src)) and not W8_REVERSE[country].search(flat(text)):
        problems.append("a reverse charge without its mention on the page (%s)" % {
            "BE": "art. 5 § 1 9°bis: Btw verlegd, Autoliquidation", "NL": "art. 35a lid 1 m: btw verlegd",
            "AT": "§ 11 Abs. 1a: a note of the Steuerschuldnerschaft des Leistungsempfängers, in any words",
            "IE": "reg. 20(2)(e): an indication that a reverse charge applies, in any words",
            "ES": "art. 6.1 m: «inversión del sujeto pasivo»",
            "IT": "art. 17 and art. 21 comma 6-bis: «inversione contabile»",
            "PL": "art. 106e ust. 1 pkt 18: „odwrotne obciążenie”"}[country])
    if credit(src) and src.get("preceding_invoice") and str(src["preceding_invoice"]) not in text:
        problems.append("the credit note does not name invoice %s" % src["preceding_invoice"])


def be_invoice(src, text, root):
    s, b = parties(src)
    problems = []
    raw = s.get("enterprise_number") or s.get("register_number")
    num = ids.be_enterprise_digits(raw)
    if not ids.be_enterprise_ok(num):
        problems.append("the enterprise number %r fails its modulus 97 check" % raw)
    elif num not in nospace(text).replace(".", ""):
        problems.append("the seller's enterprise number %s is not on the page (art. 2:20)" % ids.be_enterprise_text(num))
    elif not re.search(r"BE\s*" + r"[\s.]*".join(num), flat(text)):
        problems.append("the seller's VAT number BE %s is not on the page (art. 5)" % ids.be_enterprise_text(num))
    for who, p in (("supplier", s), ("customer", b)):
        miss = address_on(text, p)
        if miss:
            problems.append("the %s's %s not on the page (art. 5)" % (who, ", ".join(miss)))
    bnum = ids.be_enterprise_digits(b.get("enterprise_number") or b.get("register_number") or ids.digits(b.get("vat_id")))
    if str(b.get("country") or "").upper() == "BE" and not b.get("private"):
        if not bnum or bnum not in nospace(text).replace(".", ""):
            problems.append("the customer's VAT number is not on the page (art. 5)")
    _common(src, text, problems, "art. 5")
    ref = (src.get("payment") or {}).get("reference")
    if ref and "+" in str(ref):
        if not ids.be_ogm_ok(ref):
            problems.append("the structured communication %s fails its check digits" % ref)
        elif ids.be_ogm_text(ref) not in flat(text):
            problems.append("the structured communication %s is not on the page" % ids.be_ogm_text(ref))
    if root is not None:
        le = cn.find(root, "AccountingSupplierParty/Party/PartyLegalEntity/CompanyID")
        ep = cn.find(root, "AccountingSupplierParty/Party/EndpointID")
        if le is None or le.get("schemeID") != "0208":
            problems.append("the UBL seller has no enterprise number under scheme 0208")
        if ep is None or not ep.get("schemeID"):
            problems.append("the UBL seller has no Peppol address")
    return not problems, "; ".join(problems) or "enterprise number %s, VAT BE, both parties, prices and VAT per rate on the page" % (
        ids.be_enterprise_text(num))


def nl_invoice(src, text, root):
    s, b = parties(src)
    problems = []
    v = str(s.get("vat_id") or "").replace(" ", "").upper()
    if not re.fullmatch(r"NL\d{9}B\d{2}", v):
        problems.append("the supplier's btw-id %r is not NL, nine digits, B and two digits" % s.get("vat_id"))
    elif v not in nospace(text).upper():
        problems.append("the supplier's btw-id %s is not on the page (art. 35a)" % v)
    kvk = ids.digits(s.get("kvk") or s.get("register_number"))
    if not kvk and "register_number" in particulars.unknown_of(src):
        kvk = "declared unknown"            # EINV-PARTICULARS says the invoice is not complete without it
    elif len(kvk) != 8:
        problems.append("no eight-digit KvK number for the supplier")
    elif kvk not in nospace(text):
        problems.append("the supplier's KvK number %s is not on the page (Handelsregisterwet 2007 art. 27)" % kvk)
    for who, p in (("supplier", s), ("customer", b)):
        miss = address_on(text, p)
        if miss:
            problems.append("the %s's %s not on the page (art. 35a)" % (who, ", ".join(miss)))
    _common(src, text, problems, "art. 35a")
    if any(k[0] == "AE" for k in groups_of(src)):
        bv = str(b.get("vat_id") or "").replace(" ", "").upper()
        if not bv or bv not in nospace(text).upper():
            problems.append("a reverse charge without the customer's btw-id on the page (art. 35a)")
    if root is not None:
        le = cn.find(root, "AccountingSupplierParty/Party/PartyLegalEntity/CompanyID")
        if le is None or le.get("schemeID") not in ("0106", "0190"):
            problems.append("the UBL seller has no KvK or OIN under scheme 0106 or 0190 (NL-R-003)")
    return not problems, "; ".join(problems) or "btw-id %s, KvK %s, both parties, prices and VAT per rate on the page" % (v, kvk)


def at_invoice(src, text, root):
    s, b = parties(src)
    problems = []
    uid = str(s.get("vat_id") or "").replace(" ", "").upper()
    if not ids.at_uid_ok(uid):
        problems.append("the supplier's UID-Nummer %r fails its check digit" % s.get("vat_id"))
    elif uid not in nospace(text).upper():
        problems.append("the supplier's UID-Nummer %s is not on the page (§ 11 Abs. 1 Z 3)" % uid)
    for who, p in (("supplier", s), ("recipient", b)):
        miss = address_on(text, p)
        if miss:
            problems.append("the %s's %s not on the page (§ 11 Abs. 1 Z 3)" % (who, ", ".join(miss)))
    if not credit(src):
        per = src.get("delivery_period") if isinstance(src.get("delivery_period"), dict) else {}
        if not (has_date(text, src.get("delivery_date")) or (per.get("from") and has_date(text, per["from"])
                                                               and has_date(text, per.get("to")))):
            problems.append("the date or period of the supply is not on the page (§ 11 Abs. 1 Z 3)")
    _common(src, text, problems, "§ 11 Abs. 1 Z 3", lines_price=False)
    net, vat, gross = totals(src)
    if gross > 10000 and not b.get("private"):
        bu = str(b.get("vat_id") or "").replace(" ", "").upper()
        if not bu or bu not in nospace(text).upper():
            problems.append("over 10 000 euros without the recipient's UID-Nummer on the page (§ 11 Abs. 1 Z 3)")
    if legal_form(s) or s.get("register_number"):
        fn = ids.AT_FN.match(str(s.get("register_number") or ""))
        if s.get("register_number") and (not fn or (fn.group(1) + fn.group(2).lower()) not in nospace(text).lower()):
            problems.append("the Firmenbuchnummer %s is not on the page (UGB § 14)" % s.get("register_number"))
    return not problems, "; ".join(problems) or "UID %s, both parties, the supply date, VAT per rate on the page" % uid


def ie_invoice(src, text, root):
    s, b = parties(src)
    problems = []
    v = str(s.get("vat_id") or "").replace(" ", "").upper()
    if not ids.ie_vat_form(v):
        problems.append("the supplier's VAT number %r is not IE, seven digits and one or two letters" % s.get("vat_id"))
    elif v not in nospace(text).upper():
        problems.append("the supplier's VAT number %s is not on the page (reg. 20)" % v)
    for who, p in (("supplier", s), ("customer", b)):
        miss = address_on(text, p)
        if miss:
            problems.append("the %s's %s not on the page (reg. 20)" % (who, ", ".join(miss)))
    if not credit(src) and not has_date(text, src.get("delivery_date")):
        problems.append("the date of supply is not on the page (reg. 20)")
    _common(src, text, problems, "reg. 20")
    rates = {format(Decimal(str(l.get("vat_rate") or 0)).normalize(), "f") for l in src.get("lines") or []}
    missing = [r for r in rates if not re.search(r"(?<![\d.])%s\s?%%" % re.escape(r), flat(text))]
    if missing:
        problems.append("the rate %s %% is not on the page beside its lines (reg. 20)" % ", ".join(sorted(missing)))
    net, vat, gross = totals(src)
    if not has_amount(text, gross):
        problems.append("the total %s is not on the page" % gross)
    if any(k[0] in ("AE", "K") for k in groups_of(src)):
        bv = str(b.get("vat_id") or "").replace(" ", "").upper()
        if not bv or bv not in nospace(text).upper():
            problems.append("a reverse charge or an intra-EU supply without the customer's VAT number (reg. 20)")
    if credit(src) and (not src.get("note") or not has_name(text, src["note"])):
        problems.append("the credit note does not state the reason for the credit (reg. 20(5))")
    if credit(src) and not b.get("private"):
        bv = str(b.get("vat_id") or "").replace(" ", "").upper()
        if not bv or bv not in nospace(text).upper():
            problems.append("the credit note does not state the customer's registration number (reg. 20(5)(d))")
    cur = str(src.get("currency") or "EUR").upper()
    if cur != "EUR" and vat:
        rate = src.get("exchange_rate")
        if not rate or "EUR" not in text or not has_amount(text, vat * Decimal(str(rate))):
            problems.append("the invoice is in %s and its VAT is not stated in euro (s. 66)" % cur)
    return not problems, "; ".join(problems) or "VAT number %s, both parties, supply date, rates and VAT on the page" % v


# ---- wave 9: Spain, Italy, Poland ----------------------------------------------------------------

NATIONAL_ROOTS = ("{http://www.facturae.gob.es/formato/Versiones/Facturaev3_2_2.xml}Facturae",
                  "{http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2}FatturaElettronica",
                  "{http://crd.gov.pl/wzor/2025/06/25/13775/}Faktura")


def national_root(path):
    """The root of the Facturae, FatturaPA or FA(3) file beside the page, or None."""
    from xml.etree import ElementTree as ET
    xml = Path(path).with_suffix(".xml")
    if not xml.is_file():
        return None
    try:
        root = ET.parse(xml).getroot()
    except (ET.ParseError, OSError):
        return None
    return root if root.tag in NATIONAL_ROOTS else None


def first(root, name):
    """The text of the first element of that local name, whatever its namespace."""
    for el in root.iter():
        if el.tag.split("}")[-1] == name:
            return (el.text or "").strip()
    return None


def _rates_on(src, text, problems, rule):
    rates = {format(Decimal(str(l.get("vat_rate") or 0)).normalize(), "f") for l in src.get("lines") or []}
    missing = [r for r in rates if not re.search(r"(?<![\d.,])%s\s?%%" % re.escape(r).replace(r"\.", "[.,]"), flat(text))]
    if missing:
        problems.append("the rate %s %% is not on the page beside its lines (%s)" % (", ".join(sorted(missing)), rule))


def _supply_date(src, text, problems, rule):
    if not credit(src) and src.get("delivery_date") and src["delivery_date"] != src.get("issue_date") \
            and not has_date(text, src["delivery_date"]):
        problems.append("the date of the supply %s is not on the page (%s)" % (src["delivery_date"], rule))


def _reasons_on(src, text, problems, rule, cats=("E", "K", "G", "O", "Z")):
    for l in src.get("lines") or []:
        if str(l.get("vat_category") or "S").upper() in cats:
            reason = l.get("exemption_reason") or src.get("exemption_reason")
            if not reason or not has_name(text, reason):
                problems.append("%r carries no tax and the page does not say why (%s)" % (l.get("name"), rule))


def _tax_id_on(text, value):
    """A tax number is on the page, whatever points, spaces and hyphens the page prints it with."""
    want = re.sub(r"[\s.\-]", "", str(value or "")).upper()
    page = re.sub(r"[\s.\-]", "", nospace(text)).upper()
    return bool(want) and (want in page or (want[:2].isalpha() and want[2:] in page))


def es_invoice(src, text, root):
    s, b = parties(src)
    problems = []
    nif = ids.es_nif(s.get("vat_id"))
    if not ids.es_nif_form(nif):
        problems.append("the seller's NIF %r is not nine characters in a form Orden EHA/451/2008 art. 2 or Real Decreto "
                        "1065/2007 art. 19 and 20 give" % s.get("vat_id"))
    elif not _tax_id_on(text, nif):
        problems.append("the seller's NIF %s is not on the page (Real Decreto 1619/2012 art. 6.1 d)" % nif)
    for who, p in (("seller", s), ("recipient", b)):
        miss = address_on(text, p)
        if miss:
            problems.append("the %s's %s not on the page (art. 6.1 c, e)" % (who, ", ".join(miss)))
    cats = {k[0] for k in groups_of(src)}
    if (str(b.get("country") or "").upper() == "ES" and not b.get("private")) or cats & {"AE", "K"}:
        if not _tax_id_on(text, b.get("vat_id")):
            problems.append("the recipient's NIF is not on the page (art. 6.1 d)")
    _common(src, text, problems, "art. 6.1")
    _rates_on(src, text, problems, "art. 6.1 g")
    _supply_date(src, text, problems, "art. 6.1 i")
    _reasons_on(src, text, problems, "art. 6.1 j")
    if src.get("series") and not re.search(r"\bSeries?\b[\s:]*%s(?![\w-])" % re.escape(str(src["series"])), flat(text), re.I):
        problems.append("the series %s is not on the page beside its label (art. 6.1 a)" % src["series"])
    if credit(src) and not src.get("series"):
        problems.append("a rectifying invoice without a series of its own (art. 6.1 a 2.º)")
    if root is not None:
        want = "OR" if credit(src) else "OO"
        if first(root, "InvoiceClass") != want:
            problems.append("the Facturae's InvoiceClass is %s, not %s" % (first(root, "InvoiceClass"), want))
        if credit(src) and not any(el.tag.split("}")[-1] == "Corrective" for el in root.iter()):
            problems.append("the Facturae of a rectifying invoice has no Corrective block naming the invoice (art. 15.4)")
    return not problems, "; ".join(problems) or "NIF %s, both parties, prices, rates and IVA per rate on the page%s" % (
        nif, "; the Facturae beside it is unsigned" if root is not None else "")


def it_invoice(src, text, root):
    s, b = parties(src)
    problems = []
    piva = ids.it_piva(s.get("vat_id"))
    if not ids.it_piva_form(piva):
        problems.append("the seller's partita IVA %r is not IT and eleven digits" % s.get("vat_id"))
    elif not _tax_id_on(text, piva):
        problems.append("the seller's partita IVA %s is not on the page (DPR 633/1972 art. 21 comma 2 d)" % piva)
    for who, p in (("seller", s), ("customer", b)):
        miss = address_on(text, p)
        if miss:
            problems.append("the %s's %s not on the page (art. 21 comma 2 c, e)" % (who, ", ".join(miss)))
    if not b.get("private") and not (_tax_id_on(text, b.get("vat_id")) or _tax_id_on(text, b.get("tax_code"))):
        problems.append("neither the customer's partita IVA nor its codice fiscale is on the page (art. 21 comma 2 f)")
    _common(src, text, problems, "art. 21 comma 2")
    _rates_on(src, text, problems, "art. 21 comma 2 l")
    _supply_date(src, text, problems, "art. 21 comma 2 g-bis")
    _reasons_on(src, text, problems, "art. 21 comma 6")
    if src.get("split_payment") and not re.search(r"scissione dei pagamenti", flat(text), re.I):
        problems.append("a split payment without «scissione dei pagamenti» on the page (art. 17-ter)")
    if src.get("stamp_duty") and not re.search(r"bollo", flat(text), re.I):
        problems.append("stamp duty is owed and the page carries no annotation that it was paid (DM 17 giugno 2014 "
                        "art. 6 comma 2)")
    if root is not None:
        want = "TD04" if credit(src) else "TD01"
        if first(root, "TipoDocumento") != want:
            problems.append("the FatturaPA's TipoDocumento is %s, not %s" % (first(root, "TipoDocumento"), want))
        if credit(src) and not any(el.tag.split("}")[-1] == "DatiFattureCollegate" for el in root.iter()):
            problems.append("the FatturaPA of a credit note names no invoice (DatiFattureCollegate)")
        if src.get("split_payment") and first(root, "EsigibilitaIVA") != "S":
            problems.append("a split payment and the FatturaPA's EsigibilitaIVA is not S")
    return not problems, "; ".join(problems) or "partita IVA %s, both parties, prices, rates and IVA per rate on the page%s" % (
        piva, "; the FatturaPA beside it is not sent" if root is not None else "")


def pl_invoice(src, text, root):
    s, b = parties(src)
    problems = []
    nip = ids.pl_nip(s.get("vat_id"))
    if not ids.pl_nip_form(nip):
        problems.append("the seller's NIP %r is not ten digits in the form FA(3) takes" % s.get("vat_id"))
    elif not _tax_id_on(text, nip):
        problems.append("the seller's NIP %s is not on the page (ustawa o VAT art. 106e ust. 1 pkt 4)" % nip)
    for who, p in (("seller", s), ("buyer", b)):
        miss = address_on(text, p)
        if miss:
            problems.append("the %s's %s not on the page (art. 106e ust. 1 pkt 3)" % (who, ", ".join(miss)))
    if not b.get("private") and not _tax_id_on(text, b.get("vat_id")):
        problems.append("the buyer's tax number is not on the page (art. 106e ust. 1 pkt 5)")
    _common(src, text, problems, "art. 106e ust. 1")
    _rates_on(src, text, problems, "art. 106e ust. 1 pkt 12")
    _supply_date(src, text, problems, "art. 106e ust. 1 pkt 6")
    _reasons_on(src, text, problems, "art. 106e ust. 1 pkt 19", cats=("E",))
    page = flat(text).lower()
    if src.get("split_payment") and "mechanizm podzielonej płatności" not in page:
        problems.append("a split payment without „mechanizm podzielonej płatności” on the page (art. 106e ust. 1 pkt 18a)")
    if src.get("cash_method") and "metoda kasowa" not in page:
        problems.append("the cash method without „metoda kasowa” on the page (art. 106e ust. 1 pkt 16)")
    net, vat, gross = totals(src)
    cur = str(src.get("currency") or "PLN").upper()
    if cur != "PLN" and vat:
        rate = src.get("exchange_rate")
        if not rate or "PLN" not in text or not has_amount(text, vat * Decimal(str(rate))):
            problems.append("the invoice is in %s and its tax is not stated in złoty (art. 106e ust. 11)" % cur)
    if credit(src) and src.get("preceding_ksef_number") and str(src["preceding_ksef_number"]) not in nospace(text):
        problems.append("the KSeF number of the corrected invoice is not on the page (art. 106j ust. 2 pkt 2a)")
    if root is not None:
        want = "KOR" if credit(src) else "VAT"
        if first(root, "RodzajFaktury") != want:
            problems.append("the FA(3)'s RodzajFaktury is %s, not %s" % (first(root, "RodzajFaktury"), want))
        if credit(src) and first(root, "NrFaKorygowanej") != str(src.get("preceding_invoice")):
            problems.append("the FA(3) of a correcting invoice does not name invoice %s" % src.get("preceding_invoice"))
        for field, on, words in (("P_16", src.get("cash_method"), "metoda kasowa"),
                                 ("P_18", any(k[0] == "AE" for k in groups_of(src)), "odwrotne obciążenie"),
                                 ("P_18A", src.get("split_payment"), "mechanizm podzielonej płatności")):
            if first(root, field) != ("1" if on else "2"):
                problems.append("the FA(3)'s %s (%s) is %s and the order says %s" % (
                    field, words, first(root, field), "it applies" if on else "it does not"))
    return not problems, "; ".join(problems) or "NIP %s, both parties, prices, rates and tax per rate on the page%s" % (
        ids.pl_nip_text(nip), "; the FA(3) beside it is not sent" if root is not None else "")


RULE_FN = {"NO-SELLER": no_seller, "NO-CONTENT": no_content, "DK-INVOICE": dk_invoice, "FI-INVOICE": fi_invoice,
           "FI-PAYMENT": fi_payment, "UK-VAT-INVOICE": uk_invoice, "AU-TAX-INVOICE": au_invoice,
           "CA-GST-HST": ca_invoice, "US-SALES-TAX": us_invoice, "BE-INVOICE": be_invoice, "NL-INVOICE": nl_invoice,
           "AT-INVOICE": at_invoice, "IE-VAT-INVOICE": ie_invoice, "ES-INVOICE": es_invoice, "IT-INVOICE": it_invoice,
           "PL-INVOICE": pl_invoice}


def check(rule_id, path, case, stage):
    if rule_id not in RULE_FN:
        return None, "unknown rule %s" % rule_id
    src = cn.wanted(path, case, stage)
    if not src.get("seller"):
        src = cn.source_beside(path)
    country = str((src.get("seller") or {}).get("country") or "").upper()
    want = COUNTRY[rule_id.split("-")[0]]
    if country != want:
        return None, "the seller is not in %s" % want
    page = cn.page_for(path)
    if page is None:
        return None, "no printed page to read"
    text = cn.page_text(page)
    return RULE_FN[rule_id](src, text, national_root(path) if want in ("ES", "IT", "PL") else ubl_root(path))


if __name__ == "__main__":
    for rule in RULES:
        ok, why = check(rule, sys.argv[1], {}, "first")
        print(json.dumps({"rule": rule, "passed": ok, "evidence": why}, ensure_ascii=False))
