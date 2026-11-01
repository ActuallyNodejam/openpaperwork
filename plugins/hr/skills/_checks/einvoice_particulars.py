#!/usr/bin/env python3
"""EINV-PARTICULARS: what a company's own law makes it state on its invoice, beside what the tax rules ask.

The tax rules (VAT numbers, dates, rates) are the country rules' work. This rule reads the company-law
side: the register and number, the seat, the legal form, the share capital, liquidation. Each statute was
read in its official text on 2026-10-10 and is enforced on an invoice only where its words reach an invoice.

  Enforced, the statute names invoices or every document the company issues:
    FR  Code de commerce R123-237 (factures: the SIREN, "RCS" and the registry's city, the seat, liquidation)
        and R123-238 (lettres, factures: the name with the legal form, and the share capital of a SARL, SA,
        SAS, SCA or SE).
    BE  Code des sociétés et des associations art. 2:20 (facturen / factures: name, legal form, seat,
        enterprise number, "RPR" or "RPM" with the court of the seat, liquidation; e-mail and website when
        the legal person has them).
    NL  Handelsregisterwet 2007 art. 27 (brieven, orders, facturen, offertes: the KvK number); Burgerlijk
        Wetboek 2:186 and 2:75 (every document a BV or NV issues: its full name and its seat).
    ES  Código de Comercio art. 24.1 (documentación, correspondencia, notas de pedido y facturas: the
        domicile, the particulars of the entry in the Registro Mercantil, the legal form, liquidation; a
        mention of the capital names the subscribed and the paid-up capital).
    IT  Codice civile art. 2250 (atti e corrispondenza: the seat, the register office and the number; the
        capital as paid up for an S.p.A., S.a.p.a. or S.r.l.; liquidation; a sole shareholder) and art.
        2497-bis (the company that directs and coordinates it).
    SE  Aktiebolagslagen (2005:551) 28 kap. 5 § (brev, fakturor, orderblanketter: the name, the place of
        the board's seat, the organisationsnummer, liquidation).
    NO  Bokføringsforskriften § 5-1-2 (salgsdokument of an AS, ASA or branch: the word Foretaksregisteret,
        the head office's address, winding up); foretaksregisterloven (2025) § 7-2.
    DK  Selskabsloven § 2, stk. 4 (breve og andre forretningspapirer: name, hjemsted, which § 5 nr. 14
        defines as the address the company can be reached at, and CVR-nummer).
    AU  Corporations Act 2001 s 153 with s 88A(1)(c) (a public document, which an invoice is: the name and,
        with it, "ACN" and the number, or "ABN" and a number whose last nine digits are the ACN).
    GB  SI 2015/17 reg. 24(1)(e): the registered name on invoices. (Reg. 25, the number and the registered
        office, names business letters, order forms and websites only.)
    IE  Companies Act 2014 s. 49(1)(b)(iii): the name on invoices. (S. 151 names business letters and order
        forms only.)
    CA  Canada Business Corporations Act s. 10(5): the corporate name on invoices.

  Not enforced, the statute names business letters and order forms and not invoices:
    DE  GmbHG § 35a, AktG § 80, HGB § 37a (Geschäftsbriefe, Bestellscheine).
    AT  UGB § 14 (Geschäftsbriefe, Bestellscheine, Webseiten).
    PL  Kodeks spółek handlowych art. 206 § 1 and art. 374 § 1 (pisma i zamówienia handlowe); ustawa o
        Krajowym Rejestrze Sądowym art. 34 (written statements to named persons).
    FI  Yritys- ja yhteisötietolaki (244/2001) 15 § (kirjeet ja lomakkeet).
    US  No federal statute.

A particular the page does not state FAILS, with the article. There is one way out, because nobody may make
a register number up: the order lists the particular in the seller's "unknown" (or at the top of the order),
the builder prints nothing in its place, and the rule passes with a WARN line that says the invoice is not
complete without it. The way out closes when the person's own files give the particular: the folder the
check is told about with --in (or, without it, the folder the page is in) is read, and a particular found
there beside the seller's name and missing from the page is a FAIL whatever the order declares.

check(rule_id, path, case, stage) -> (passed, evidence). passed is None when no particular is owed on an
invoice; True with evidence starting "WARN " when a particular is declared unknown. A drafting check of what
the page says against published statutes; it never says an invoice is lawful. Standard library only;
pdftotext reads the page.
"""
import json
import os
import re
import subprocess
import sys
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import credit_note_check as cn  # noqa: E402

RULES = ("EINV-PARTICULARS",)

# The forms each statute names, read off the end of the seller's name or its "legal_form".
FORMS = {
    "FR": r"SARL|EURL|SELARL|SASU|SELAS|SAS|SA|SCA|SE|SNC|SCS",
    "BE": r"BVBA|BV|SPRL|SRL|NV|SA|CVBA|CV|SCRL|SC|VOF|SNC|CommV|SComm|IVZW|VZW|AISBL|ASBL",
    "NL": r"B\.?V\.?|N\.?V\.?",
    "ES": r"S\.?L\.?U\.?|S\.?L\.?L\.?|S\.?L\.?P\.?|S\.?L\.?|S\.?A\.?U\.?|S\.?A\.?",
    "IT": r"S\.?r\.?l\.?s\.?|S\.?r\.?l\.?|S\.?p\.?A\.?|S\.?a\.?p\.?a\.?|S\.?n\.?c\.?|S\.?a\.?s\.?",
    "SE": r"AB \(publ\)|AB|Aktiebolag",
    "NO": r"ASA|AS|NUF",
    "DK": r"A/S|ApS|P/S",
    "AU": r"Pty\.? Ltd\.?|Pty\.? Limited|Proprietary Limited|Ltd\.?|Limited|No Liability|N\.?L\.?",
    "GB": r"Ltd\.?|Limited|PLC|LLP|CIC|Cyf\.?|Cyfyngedig",
    "IE": r"Ltd\.?|Limited|DAC|PLC|CLG|ULC|UC|Teoranta|Teo\.?",
    "CA": r"Inc\.?|Incorporated|Incorporée|Ltd\.?|Limited|Ltée|Limitée|Corp\.?|Corporation",
}
# Why nothing is owed on an invoice where the statute stops at letters.
NOT_ON_INVOICES = {
    "DE": "GmbHG § 35a, AktG § 80 and HGB § 37a name business letters and order forms (Geschäftsbriefe, "
          "Bestellscheine), not invoices",
    "AT": "UGB § 14 names business letters, order forms and websites (Geschäftsbriefe, Bestellscheine, "
          "Webseiten), not invoices",
    "PL": "Kodeks spółek handlowych art. 206 § 1 and art. 374 § 1 name letters and commercial orders (pisma i "
          "zamówienia handlowe) and websites, not invoices",
    "FI": "yritys- ja yhteisötietolaki (244/2001) 15 § names letters and forms (kirjeet ja lomakkeet), not invoices",
    "US": "no federal statute sets a company's particulars on an invoice",
}
WHO = {"FR": "A French %s", "BE": "A Belgian %s", "NL": "A Dutch %s", "ES": "A Spanish %s", "IT": "An Italian %s",
       "SE": "A Swedish %s", "NO": "A Norwegian %s", "DK": "A Danish %s", "AU": "An Australian %s",
       "GB": "A UK %s", "IE": "An Irish %s", "CA": "A Canadian %s"}
NAMES = {"UK": "GB", "GREAT BRITAIN": "GB", "UNITED KINGDOM": "GB"}


def bare(form):
    return re.sub(r"[.\s]", "", str(form or "")).upper()


def country_of(seller):
    c = str((seller or {}).get("country") or "").strip().upper()
    return NAMES.get(c, c)


def form_of(seller, cc=None):
    """The seller's legal form when it is one the country's statute names, else ""."""
    cc = cc or country_of(seller)
    forms = FORMS.get(cc)
    if not forms:
        return ""
    given = str((seller or {}).get("legal_form") or "").strip()
    if given:
        return given if re.fullmatch(forms, given, re.I) else ""
    found = re.search(r"(?:^|[\s,])(%s)\s*$" % forms, str((seller or {}).get("name") or "").strip(), re.I)
    return found.group(1) if found else ""


def unknown_of(src):
    """The particulars the order declares unknown: "unknown": ["register_number"] in the seller, or at the
    top of the order."""
    out = set()
    for holder in (src or {}, (src or {}).get("seller") or {}):
        listed = holder.get("unknown") if isinstance(holder, dict) else None
        if isinstance(listed, str):
            listed = [listed]
        for key in listed or []:
            out.add(str(key).strip().split(".")[-1])
    return out


# ---- reading a page -------------------------------------------------------------------------------

def flat(text):
    return re.sub(r"[\s  ]+", " ", text or "").strip()


def squeezed(text):
    """The page with what a number is grouped by taken out: 556000-0000, 0123.456.749 and 10 000 read alike."""
    return re.sub(r"[\s  .\-']", "", text or "")


def plain(text):
    return re.sub(r"[.,;:]", "", flat(str(text))).casefold()


def digits_on(value, page):
    wanted = re.sub(r"[\s  .\-']", "", str(value or ""))
    return bool(wanted) and wanted.casefold() in squeezed(page).casefold()


def text_on(value, page):
    """The value is on the page. A footer column wraps a long value over two lines and a PDF's text may read
    another column between them, so its words are also looked for in order with a short run between two."""
    if not value:
        return False
    v, p = plain(value), plain(page)
    if v in p:
        return True
    words = [re.escape(w) for w in v.split(" ") if w]
    return len(words) > 1 and re.search(r"(?<!\w)" + r"(?:\s|\s.{0,120}?\s)".join(words) + r"(?!\w)", p) is not None


def word_on(value, page):
    return bool(value) and re.search(r"(?<!\w)%s(?!\w)" % re.escape(plain(value)), plain(page)) is not None


def whole_units(value):
    """10000 for 10000, "10.000,00 euro i.v.", "10 000 €" and "50 000,00 zł": the amount without its cents."""
    if isinstance(value, (int, float)):
        return str(int(value))
    m = re.search(r"\d[\d\s  .,']*", str(value or ""))
    if not m:
        return ""
    number = m.group(0).strip(" .,")
    cents = re.search(r"[.,]\d{1,2}$", number)
    if cents:
        number = number[:cents.start()]
    return re.sub(r"\D", "", number)


def capital_on(value, page, words):
    """The capital's own words on the page and, when its amount is known, the amount after them."""
    for m in re.finditer(words, page, re.I):
        after = squeezed(page[m.end():m.end() + 80])
        units = whole_units(value)
        if not units or units in re.sub(r"[,]", "", after):
            return True
    return False


def address_on(seller, page):
    """The seat as the page gives it: the registered office the order names, else the seller's own address."""
    office = seller.get("registered_office")
    if office:
        return text_on(office, page)
    return all(text_on(seller[k], page) for k in ("street", "city") if seller.get(k)) and bool(
        seller.get("street") or seller.get("city"))


def page_text(pdf):
    """The page read twice: in reading order, which keeps a footer column's lines together, and laid out as
    printed. A particular is on the page when either reading has it."""
    out = []
    for args in ((), ("-layout",)):
        run = subprocess.run(["pdftotext", *args, str(pdf), "-"], capture_output=True, text=True)
        out.append(run.stdout)
    return "\n\n".join(out)


# ---- the statutes ---------------------------------------------------------------------------------
#
# An item: key (the seller key that carries it, and the word the order lists under "unknown"), what (the
# words of the message), cite, on (page test), given (the value the order gives, "" when none), unknown
# (whether it may be declared unknown: never a number the tax rules ask for too, never a word the builder
# writes by itself), notes (how the person's own files would write it: a pattern whose first group is the
# value) and found (page test for a value read from the notes).

CAPITAL_WORDS = {"FR": r"capital(?:\s+social)?(?:\s+de)?", "IT": r"capitale\s+sociale|cap\.\s*soc\.",
                 "ES": r"capital\s+(?:social|suscrito)"}
LIQUIDATION = {"FR": r"en\s+liquidation", "BE": r"in\s+vereffening|en\s+liquidation|in\s+Liquidation",
               "ES": r"en\s+liquidaci[oó]n", "IT": r"in\s+liquidazione", "SE": r"i\s+likvidation",
               "NO": r"under\s+avvikling"}
NEGATED = re.compile(r"\b(non|not|no|pas|niet|geen|ej|inte|ikke|nicht|kein|sin|senza)\b[^.\n]{0,14}$", re.I)
IT_REGISTER = re.compile(
    r"Registro\s+(?:delle\s+)?Imprese(?:\s+di)?\s+([^\n,;:]{2,60}?)\s*[,;:]?\s*(?:al\s+)?(?:n\.|n°|nr\.?|numero)\s*"
    r"(?:d[i']\s*iscrizione\s*)?([A-Z]{0,2}[\- ]?\d[\d .\-]{4,14}\d)", re.I)
ES_REGISTER = re.compile(
    r"Registro\s+Mercantil(?:\s+de)?\s+([^\n,;:.]{2,50}?)\s*[,;:.]?\s*((?:tomo|t\.)\s*[\d.]+[^\n]{0,80}?"
    r"(?:hoja|h\.)\s*[A-Z]{1,2}\s*-?\s*[\d.]+)", re.I)
# Owed only when it is the case: nothing is missing when the order and the person's files are silent.
WHEN_SO = ("in_liquidation", "sole_shareholder", "email", "website", "directed_by")
MONEY = r"(\d[\d\s  .']*(?:,\d{2})?)"


def _item(key, what, cite, on, given="", unknown=True, notes=None, found=None, group=1):
    return {"key": key, "what": what, "cite": cite, "on": on, "given": given, "unknown": unknown,
            "notes": notes, "found": found, "group": group}


def _first(seller, *keys):
    for k in keys:
        if seller.get(k) not in (None, "", False):
            return seller[k]
    return ""


def _name(seller, cite, what="the company's name with its legal form"):
    def on(page):
        form = str(seller.get("legal_form") or "").strip()
        return text_on(seller.get("name"), page) and (
            not form or plain(form) in plain(seller.get("name")) or word_on(form, page))
    return _item("name", what, cite, on, given=seller.get("name") or "", unknown=False)


def _seat(seller, cite, what):
    """The seat is the registered office the order names, else the seller's own address. An order that
    names neither (a case's truth that lists only what it compares) leaves the address to the tax rules,
    which ask for it on every invoice."""
    named = _first(seller, "registered_office", "street", "city")
    return _item("registered_office", what, cite, lambda page: not named or address_on(seller, page),
                 given=named or "the seller's address", unknown=False)


def _liquidation(seller, cc, cite):
    words = LIQUIDATION[cc]
    rea = seller.get("rea") if isinstance(seller.get("rea"), dict) else {}
    return _item("in_liquidation", "that the company is in liquidation", cite,
                 lambda page: bool(re.search(words, page, re.I)),
                 given="yes" if seller.get("in_liquidation") or rea.get("in_liquidation") else "",
                 unknown=False, notes=re.compile("(%s)" % words, re.I),
                 found=lambda value, page: bool(re.search(words, page, re.I)))


def _capital(seller, cc, cite, what):
    words = CAPITAL_WORDS[cc]
    return _item("share_capital", what, cite, lambda page: capital_on(seller.get("share_capital"), page, words),
                 given=_first(seller, "share_capital"),
                 notes=re.compile(r"(?:%s)[^\n\d]{0,30}?%s" % (words, MONEY), re.I),
                 found=lambda value, page: capital_on(value, page, words))


def _fr(seller, form):
    b = bare(form)
    items = [
        _name(seller, "Code de commerce R123-238"),
        _item("siren", "the SIREN", "R123-237 1°", lambda page: digits_on(seller.get("siren"), page),
              given=_first(seller, "siren"), unknown=False),
        _item("rcs", "\"RCS\" and the city of its registry", "R123-237 2°",
              lambda page: bool(re.search(r"\bRCS\s+\S", page)) and (not seller.get("rcs") or text_on(seller["rcs"], page)),
              given=_first(seller, "rcs"),
              notes=re.compile(r"\b(R\.?C\.?S\.?\s+(?:de\s+)?[A-ZÀ-Ý][\w'’\-]+(?:[ \-][A-ZÀ-Ý][\w'’\-]+){0,3})"),
              found=lambda value, page: text_on(re.sub(r"R\.?C\.?S\.?\s+(?:de\s+)?", "RCS ", value), page)),
        _seat(seller, "R123-237 3°", "the place of its seat"),
    ]
    if b in ("SARL", "EURL", "SELARL", "SA", "SAS", "SASU", "SELAS", "SCA", "SE"):
        items.append(_capital(seller, "FR", "R123-238", "the amount of its share capital"))
    items.append(_liquidation(seller, "FR", "R123-237 4°"))
    return items


def _be(seller, form):
    number = _first(seller, "enterprise_number", "register_number") or re.sub(r"\D", "", str(seller.get("vat_id") or ""))
    court = re.compile(r"\b((?:RPR|RPM|RJP|rechtspersonenregister|registre des personnes morales)\s+[A-ZÀ-Ý][\w'’\-]+"
                       r"(?:,?\s+(?:afdeling|division)\s+[A-ZÀ-Ý][\w'’\-]+)?)", re.I)
    items = [
        _name(seller, "art. 2:20 1° and 2°"),
        _seat(seller, "art. 2:20 3°", "the seat"),
        _item("register_number", "the enterprise number", "art. 2:20 4°",
              lambda page: digits_on(str(number).lstrip("0"), page), given=number, unknown=False),
        _item("register", "\"RPR\" or \"RPM\" and the court of its seat", "art. 2:20 5°",
              lambda page: bool(re.search(r"\b(RPR|RPM|RJP|rechtspersonenregister|registre des personnes morales)\b",
                                          page, re.I)) and (not seller.get("register") or text_on(seller["register"], page)),
              given=_first(seller, "register"), notes=court, found=lambda value, page: text_on(value, page)),
    ]
    for key, what in (("email", "its e-mail address"), ("website", "its website")):
        if seller.get(key) or (isinstance(seller.get("contact"), dict) and seller["contact"].get(key)):
            value = seller.get(key) or seller["contact"][key]
            items.append(_item(key, what, "art. 2:20 6°",
                               lambda page, value=value: squeezed(value).casefold() in squeezed(page).casefold(),
                               given=value, unknown=False))
    items.append(_liquidation(seller, "BE", "art. 2:20 7°"))
    return items


def _nl(seller, form):
    kvk = _first(seller, "kvk", "register_number")
    items = [_item("register_number", "the KvK number", "Handelsregisterwet 2007 art. 27",
                   lambda page: digits_on(kvk, page), given=kvk,
                   notes=re.compile(r"\bK\.?v\.?K\.?(?:[\- ]?(?:nummer|nr\.?|number))?\s*:?\s*(\d{8})\b", re.I),
                   found=digits_on)]
    if form:
        book = "Burgerlijk Wetboek 2:%s" % ("75" if bare(form) == "NV" else "186")
        items.append(_name(seller, book, "the company's full name"))
        items.append(_item("registered_office", "the seat named in its articles (statutaire zetel)", book,
                           lambda page: text_on(seller.get("registered_office"), page),
                           given=_first(seller, "registered_office"),
                           notes=re.compile(r"statutair(?:e\s+zetel|\s+gevestigd)(?:\s+te|\s+in)?\s*:?\s*"
                                            r"([A-Z’'][\w'’\-]+(?:[ \-][A-Z][\w'’\-]+){0,2})", re.I),
                           found=lambda value, page: bool(re.search(r"zetel|statutair", page, re.I)) and text_on(value, page)))
    return items


def _es(seller, form):
    cite = "Código de Comercio art. 24"
    items = [
        _name(seller, cite),
        _seat(seller, cite, "its domicile"),
        _item("register", "the Registro Mercantil it is entered in", cite,
              lambda page: bool(re.search(r"Registro\s+Mercantil", page, re.I)) and text_on(seller.get("register"), page),
              given=_first(seller, "register"), notes=ES_REGISTER,
              found=lambda value, page: bool(re.search(r"Registro\s+Mercantil", page, re.I)) and text_on(value, page)),
        _item("register_number", "the particulars of its entry there (tomo, folio, hoja)", cite,
              lambda page: digits_on(seller.get("register_number"), page) or text_on(seller.get("register_number"), page),
              given=_first(seller, "register_number"), notes=ES_REGISTER, group=2,
              found=lambda value, page: digits_on(value, page) or text_on(value, page)),
    ]
    if seller.get("share_capital") not in (None, ""):
        items.append(_item("paid_up_capital", "the paid-up capital beside the subscribed capital the page mentions "
                           "(or leave the capital out)", cite,
                           lambda page: bool(re.search(r"desembolsado", page, re.I)),
                           given=_first(seller, "paid_up_capital"), unknown=False))
    items.append(_liquidation(seller, "ES", cite))
    return items


def _it(seller, form):
    cite = "Codice civile art. 2250"
    b = bare(form)
    rea = seller.get("rea") if isinstance(seller.get("rea"), dict) else {}
    words = r"Registro\s+(?:delle\s+)?Imprese"
    items = [
        _name(seller, cite, "the company's name"),
        _seat(seller, cite, "its seat"),
        _item("register", "the register office it is entered at (Registro delle Imprese di ...)", cite,
              lambda page: bool(re.search(words, page, re.I)) and text_on(seller.get("register"), page),
              given=_first(seller, "register"), notes=IT_REGISTER,
              found=lambda value, page: bool(re.search(words, page, re.I)) and text_on(value, page)),
        _item("register_number", "its number in that register", cite,
              lambda page: bool(re.search(words, page, re.I)) and digits_on(seller.get("register_number"), page),
              given=_first(seller, "register_number"), notes=IT_REGISTER, group=2,
              found=lambda value, page: bool(re.search(words, page, re.I)) and digits_on(value, page)),
    ]
    if b in ("SPA", "SAPA", "SRL", "SRLS"):
        items.append(_capital(seller, "IT", cite, "the share capital as paid up"))
    if b in ("SPA", "SRL", "SRLS"):
        sole = r"unico\s+socio|socio\s+unico"
        items.append(_item("sole_shareholder", "that the company has a sole shareholder", cite,
                           lambda page: bool(re.search(sole, page, re.I)),
                           given="yes" if seller.get("sole_shareholder") or rea.get("sole_shareholder") else "",
                           unknown=False, notes=re.compile("(%s)" % sole, re.I),
                           found=lambda value, page: bool(re.search(sole, page, re.I))))
    if seller.get("directed_by"):
        items.append(_item("directed_by", "the company that directs and coordinates it", "Codice civile art. 2497-bis",
                           lambda page: text_on(seller["directed_by"], page), given=seller["directed_by"], unknown=False))
    items.append(_liquidation(seller, "IT", cite))
    return items


def _se(seller, form):
    cite = "28 kap. 5 §"
    number = _first(seller, "org_number", "register_number")
    return [
        _name(seller, cite, "the company's name"),
        _item("register_number", "the organisationsnummer", cite, lambda page: digits_on(number, page), given=number,
              notes=re.compile(r"\borg(?:anisations)?\.?\s*-?\s*(?:nr|nummer)\.?\s*:?\s*(\d{6}\s*-?\s*\d{4})", re.I),
              found=digits_on),
        _item("registered_office", "the place where the board has its seat (säte)", cite,
              lambda page: text_on(seller.get("registered_office"), page) and bool(re.search(r"\bsäte\b", page, re.I)),
              given=_first(seller, "registered_office"),
              notes=re.compile(r"\bsäte(?:\s+i)?\s*:?\s*([A-ZÅÄÖ][\wåäöÅÄÖ\-]+(?: [A-ZÅÄÖ][\wåäö\-]+)?)"),
              found=lambda value, page: bool(re.search(r"\bsäte\b", page, re.I)) and text_on(value, page)),
        _liquidation(seller, "SE", cite),
    ]


def _no(seller, form):
    cite = "§ 5-1-2"
    return [
        _name(seller, "§ 7-2", "the company's name with its form"),
        _item("register", "the word Foretaksregisteret (the builder writes it for an AS, ASA or NUF)", cite,
              lambda page: "Foretaksregisteret" in page, given="Foretaksregisteret", unknown=False),
        _seat(seller, cite, "the head office's address"),
        _liquidation(seller, "NO", cite),
    ]


def _dk(seller, form):
    cite = "§ 2, stk. 4"
    cvr = _first(seller, "cvr") or re.sub(r"\D", "", str(seller.get("vat_id") or ""))
    return [
        _name(seller, cite, "the company's name"),
        _seat(seller, cite, "its hjemsted, the address it can be reached at (§ 5, nr. 14)"),
        _item("cvr", "the CVR-nummer", cite, lambda page: digits_on(cvr, page), given=cvr, unknown=False),
    ]


def _au(seller, form):
    acn = re.sub(r"\D", "", str(seller.get("acn") or ""))
    abn = re.sub(r"\D", "", str(seller.get("abn") or ""))

    def acn_on(page, number=None):
        number = number or acn
        if not number:
            return False
        spaced = r"\s*".join(number)
        if re.search(r"(?:A\.?C\.?N\.?|Australian Company Number)\s*:?\s*%s" % spaced, page, re.I):
            return True
        # s 153(2)(b): the ABN stands for the ACN when its last nine digits are the ACN.
        return len(abn) == 11 and abn.endswith(number) and bool(
            re.search(r"(?:A\.?B\.?N\.?|Australian Business Number)\s*:?\s*%s" % r"\s*".join(abn), page, re.I))

    return [
        _name(seller, "s 153(1)", "the company's name"),
        _item("acn", "\"ACN\" and its Australian Company Number with the name (or \"ABN\" and a number whose "
              "last nine digits are the ACN)", "s 153(2)", acn_on, given=acn,
              notes=re.compile(r"\b(?:A\.?C\.?N\.?|Australian Company Number)\s*:?\s*(\d{3}\s?\d{3}\s?\d{3})\b", re.I),
              found=lambda value, page: acn_on(page, re.sub(r"\D", "", value))),
    ]


def _name_only(cite):
    return lambda seller, form: [_name(seller, cite, "the company's registered name")]


LAW = {
    "FR": ("Code de commerce R123-237 and R123-238", _fr, True),
    "BE": ("Code des sociétés et des associations / Wetboek van vennootschappen en verenigingen art. 2:20", _be, True),
    "NL": ("Handelsregisterwet 2007 art. 27", _nl, False),      # art. 27 binds every registered business
    "ES": ("Código de Comercio art. 24.1", _es, True),
    "IT": ("Codice civile art. 2250", _it, True),
    "SE": ("aktiebolagslagen (2005:551) 28 kap. 5 §", _se, True),
    "NO": ("bokføringsforskriften § 5-1-2 and foretaksregisterloven § 7-2", _no, True),
    "DK": ("selskabsloven § 2, stk. 4", _dk, True),
    "AU": ("Corporations Act 2001 s 153; an invoice is a public document, s 88A", _au, True),
    "GB": ("SI 2015/17 reg. 24(1)(e)", _name_only("SI 2015/17 reg. 24(1)(e)"), True),
    "IE": ("Companies Act 2014 s. 49(1)(b)(iii)", _name_only("Companies Act 2014 s. 49(1)(b)(iii)"), True),
    "CA": ("Canada Business Corporations Act s. 10(5)", _name_only("Canada Business Corporations Act s. 10(5)"), True),
}


def owed(seller):
    """(statute, items, form) for the seller, or (why, None, form) when no particular is owed on an invoice."""
    cc = country_of(seller)
    if cc in NOT_ON_INVOICES:
        return NOT_ON_INVOICES[cc], None, ""
    if cc not in LAW:
        return "no company statute is read for a seller in %s" % (cc or "an unnamed country"), None, ""
    statute, fn, company_only = LAW[cc]
    form = form_of(seller, cc)
    if company_only and not form:
        return "the seller is not a company of a form %s names, or its form is not known" % statute, None, ""
    return statute, fn(seller or {}, form), form


# ---- the person's own files -----------------------------------------------------------------------

TEXT_FILES = (".txt", ".md", ".csv", ".tsv", ".eml", ".json", ".yaml", ".yml", ".rtf", ".html", ".htm")
MAX_FILES, MAX_BYTES, MAX_SECONDS = 60, 1_500_000, 20


def _read(path):
    kind = path.suffix.lower()
    try:
        if path.stat().st_size > MAX_BYTES:
            return ""
        if kind in TEXT_FILES:
            text = path.read_text(errors="ignore")
            if kind in (".html", ".htm"):
                if 'name="generator" content="nodejam-' in text:
                    return ""                                  # a page a builder wrote is an output, not a note
                text = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", text)
                text = re.sub(r"(?i)<(br|/p|/div|/li|/tr|/h\d)\b[^>]*>", "\n", text)
                text = re.sub(r"<[^>]+>", " ", text)
            if kind == ".json":
                try:
                    data = json.loads(text)
                except ValueError:
                    return text
                if path.name == "case.json" or (isinstance(data, dict) and data.get("lines") and "seller" in data):
                    return ""                                  # the order itself, and a case's own truth
            return text
        if kind == ".pdf":
            out = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True, timeout=20)
            return out.stdout
        if kind in (".docx", ".xlsx"):
            part = "word/document.xml" if kind == ".docx" else "xl/sharedStrings.xml"
            with zipfile.ZipFile(path) as z:
                xml = z.read(part).decode("utf-8", "ignore")
            return re.sub(r"<[^>]+>", " ", re.sub(r"</w:p>|</si>", "\n", xml))
    except (OSError, KeyError, ValueError, zipfile.BadZipFile, subprocess.SubprocessError):
        return ""
    return ""


def evidence_files(output, folder=""):
    """(name, text) of the person's own files: the folder the check was told about with --in, else the
    folder the page is in, two folders deep as the pack's own evidence is looked for. The page, the files
    of its name beside it, the order and any page a builder wrote are left out."""
    output = Path(output).resolve()
    root = Path(folder).resolve() if folder else output.parent
    if not root.is_dir():
        return []
    found, started = [], time.monotonic()
    for base, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d != "node_modules")
        if len(Path(base).relative_to(root).parts) >= 2:
            dirs[:] = []
        for name in sorted(names):
            path = Path(base) / name
            if name.startswith(".") or (path.parent == output.parent and path.stem == output.stem):
                continue
            if len(found) >= MAX_FILES or time.monotonic() - started > MAX_SECONDS:
                return found
            text = _read(path)
            if text.strip():
                found.append((str(path.relative_to(root)), text))
    return found


def _mentions(name, text):
    if not name or len(str(name).strip()) < 3:
        return None
    return re.search(r"\s+".join(re.escape(w) for w in str(name).split()), text, re.I)


def about_seller(text, seller, buyer):
    """The part of a file that speaks of the seller: all of a file that names the seller and not the buyer,
    else each paragraph that names the seller, cut where the buyer's name begins."""
    def seller_at(part):
        m = _mentions(seller.get("name"), part)
        if m:
            return m.start()
        for key in ("vat_id", "tax_code", "siren", "org_number", "cvr", "abn"):
            number = re.sub(r"\W", "", str(seller.get(key) or ""))
            if len(number) >= 8:
                m = re.search(r"[\s.\-]?".join(re.escape(c) for c in number), part, re.I)
                if m:
                    return m.start()
        return -1

    if seller_at(text) < 0:
        return ""
    if not _mentions(buyer.get("name"), text):
        return text
    parts = []
    for para in re.split(r"\n[ \t]*\n", text):
        at = seller_at(para)
        if at < 0:
            continue
        other = _mentions(buyer.get("name"), para)
        if not other:
            parts.append(para)
        elif other.start() > at:
            parts.append(para[:other.start()])
        else:
            parts.append(para[at:])
    return "\n\n".join(parts)


def in_notes(item, files, seller, buyer):
    """(file, quote, value) where the person's files give this particular for the seller, or None."""
    if not item.get("notes"):
        return None
    for name, text in files:
        part = about_seller(text, seller, buyer)
        if not part:
            continue
        for m in item["notes"].finditer(part):
            if NEGATED.search(part[max(0, m.start() - 30):m.start()]):
                continue
            value = m.group(item.get("group") or 1)
            if value:
                return name, flat(m.group(0))[:110], flat(value)
    return None


# ---- the rule -------------------------------------------------------------------------------------

# A particular the person does not have is declared unknown ("unknown": ["register_number"] in the seller, or at
# the top "unknown": ["buyer.vat_id"]): the page prints nothing in its place, a WARN names it, and the file is
# still handed back. These are the ones that may be declared; a total, a price or a number the VAT rules need to
# add up never is. XML_NEEDS are the ones the XML syntaxes cannot be valid without (the seller's VAT number for
# category S, a Dutch party's KvK number for its endpoint): with one of them unknown the page alone is written.
DECLARABLE = ("seller.register_number", "seller.vat_id", "seller.registered_office", "buyer.vat_id",
              "buyer.register_number", "delivery_date")
XML_NEEDS = ("seller.vat_id", "seller.register_number", "buyer.register_number")
REGISTER_KEYS = ("register_number", "org_number", "kvk", "enterprise_number", "business_id", "cvr")


def declared_unknown(src):
    """The qualified particulars the order declares unknown: seller.* from the seller's own list and the top,
    buyer.* from the buyer's own list or a "buyer.x" at the top, and top-level names such as delivery_date."""
    out = set()
    for holder, role in ((src or {}, ""), ((src or {}).get("seller") or {}, "seller"),
                         ((src or {}).get("buyer") or {}, "buyer")):
        listed = holder.get("unknown") if isinstance(holder, dict) else None
        if isinstance(listed, str):
            listed = [listed]
        for key in listed or []:
            key = str(key).strip()
            if "." in key:
                out.add(key)
            elif role:
                out.add("%s.%s" % (role, key))
            else:
                out.add(key if key == "delivery_date" else "seller." + key)
    return out


def blocked_keys(src):
    """The declared-unknown particulars that really are absent from the order and that the XML cannot go without."""
    seller, buyer = (src or {}).get("seller") or {}, (src or {}).get("buyer") or {}
    absent = {"seller.vat_id": not (seller.get("vat_id") or seller.get("vat")),
              "seller.register_number": not _first(seller, *REGISTER_KEYS),
              "buyer.register_number": not _first(buyer, *REGISTER_KEYS)}
    return [k for k in XML_NEEDS if k in declared_unknown(src) and absent[k]]


F_TAX = re.compile(r"F-?skatt", re.I)


def f_tax_warning(src, page, files=()):
    """A question about «Godkänd för F-skatt» for a Swedish seller, never a fail. Skatteverket's guidance on F-skatt
    and skatteförfarandelagen (2011:1244) 10 kap. (a payer withholds preliminary tax from a business that has no
    F-skatt) are why invoices state it; mervärdesskattelagen (2023:200) 17 kap. 24 § lists the 17 things a VAT
    invoice carries and does not name it (the 1994:200 law it replaced on 1 July 2023 did not either). It is a practice, not an invoice content rule: the basis could not be confirmed
    to an article in this library, so the check only asks. The person's own files and the company file decide."""
    seller = (src or {}).get("seller") or {}
    if country_of(seller) != "SE" or F_TAX.search(page or ""):
        return ""
    told = [name for name, text in files if F_TAX.search(text or "")]
    if told:
        return ("the person's file %s says the seller is approved for F-skatt and the page does not: put "
                "«Godkänd för F-skatt» in the seller's \"further\" (a practice under skatteförfarandelagen 10 kap. and "
                "Skatteverket's guidance, not a content rule of mervärdesskattelagen 17 kap. 24 §)" % told[0])
    unknown = unknown_of(src)
    if "f_tax" in unknown or "f-skatt" in unknown or "f_skatt" in unknown:
        return ("the seller's F-skatt status is declared unknown and the page does not say «Godkänd för F-skatt»: say so "
                "in the reply (a buyer pays a business without F-skatt less preliminary tax withheld, skatteförfarandelagen "
                "10 kap.; Skatteverket's guidance on invoices)")
    return ("a Swedish seller's invoice usually says «Godkänd för F-skatt» (Skatteverket's guidance; skatteförfarandelagen "
            "10 kap.; mervärdesskattelagen 17 kap. 24 § does not require it) and neither the order nor the page does: ask "
            "the person, or list \"f_tax\" in the seller's \"unknown\" and say so in the reply; never state it unasked")


def judge(src, page, files=()):
    """(passed, evidence): the particulars the company's law asks for, then the F-skatt question for a Swedish seller."""
    passed, why = _judge(src, page, files)
    warn = f_tax_warning(src, page, files) if passed is not False else ""
    if warn and passed is None:
        return True, "WARN " + warn
    if passed and warn:
        why = "WARN " + (why[5:] + "; " if why.startswith("WARN ") else "") + warn
    return passed, why


def _judge(src, page, files=()):
    """(passed, evidence) for an order, the text of its page and the person's files as (name, text)."""
    seller, buyer = (src or {}).get("seller") or {}, (src or {}).get("buyer") or {}
    statute, items, form = owed(seller)
    if items is None:
        return None, statute
    unknown = unknown_of(src)
    problems, declared, can_declare, dropped, quoted = [], [], [], False, set()

    def cited(item):
        return "" if item["cite"] in statute else " (%s)" % item["cite"]

    for item in items:
        if item["given"] not in (None, "", False):
            if not item["on"](page):
                problems.append("%s, which is not on the page%s" % (item["what"], cited(item)))
            continue
        noted = in_notes(item, files, seller, buyer)
        if noted and not item["found"](noted[2], page):
            dropped = True
            quote = "the same line" if noted[1] in quoted else "«%s»" % noted[1]
            quoted.add(noted[1])
            problems.append("%s, which the person's file %s gives (%s) and the page drops: seller.%s%s"
                            % (item["what"], noted[0], quote, item["key"], cited(item)))
            continue
        if item["key"] in WHEN_SO:
            continue                                           # owed only when it is the case
        if item["unknown"] and item["key"] in unknown:
            declared.append("%s%s" % (item["what"], cited(item)))
            continue
        problems.append("%s, which the order does not give: seller.%s%s" % (item["what"], item["key"], cited(item)))
        if item["unknown"]:
            can_declare.append(item["key"])
    who = (WHO[country_of(seller)] % form) if form else "A business in the trade register"
    if problems:
        way_out = ""
        if can_declare:
            way_out = (" If the person's files do not give %s, list it in the seller's \"unknown\" (\"unknown\": [%s]) "
                       "and say in the reply that the invoice is not complete without it; never make one up."
                       % ("it" if len(can_declare) == 1 else "one of them", ", ".join('"%s"' % k for k in can_declare)))
        elif dropped:
            way_out = " The person's own files give it, so it cannot be declared unknown."
        return False, ("%s states on its invoices what this page does not (%s): %s. Put what the person's files "
                       "give into the order's seller and build again.%s" % (who, statute, "; ".join(problems), way_out))
    if declared:
        return True, ("WARN declared unknown, and the invoice is not complete without it (%s): %s. The page prints "
                      "nothing in its place. Say so in the reply and ask the person for it."
                      % (statute, "; ".join(declared)))
    return True, "the company's particulars are on the page (%s)" % statute


def builder_warnings(src):
    """What the builder says of the same particulars before the check does."""
    seller = (src or {}).get("seller") or {}
    statute, items, form = owed(seller)
    if items is None:
        return []
    unknown = unknown_of(src)
    out = []
    for item in items:
        if item["given"] not in (None, "", False) or item["key"] in WHEN_SO:
            continue
        if item["unknown"] and item["key"] in unknown:
            out.append("seller.%s is declared unknown: the page does not state %s (%s) and the invoice is not "
                       "complete without it; say so in your reply" % (item["key"], item["what"], item["cite"]))
        elif item["unknown"]:
            out.append("seller.%s not given: %s (%s). The pack check fails the page without it. Take it from the "
                       "person's files; if they do not give it, add \"%s\" to the seller's \"unknown\" and say so in "
                       "your reply. Never make one up." % (item["key"], item["what"], item["cite"], item["key"]))
        else:
            out.append("seller.%s not given: %s (%s); the pack check fails the page without it"
                       % (item["key"], item["what"], item["cite"]))
    return out


def source(path, case, stage):
    """(order, made up): the seller the page is judged against, and what the order gives that it should not.

    The order beside the page is what the page was built from. A case's truth says what the file should be
    and may say less (a truth that lists only what it compares) or more (what the person's files give and a
    model left out), so the two are read together: the order's own values, and the truth's where the order
    has none. A particular the truth lists as unknown and the order gives was made up."""
    beside = cn.source_beside(path)
    wanted = cn.wanted(path, case, stage)
    if not (wanted or {}).get("seller"):
        return beside, []
    if not beside.get("seller") or beside == wanted:
        return wanted, []
    made_up = sorted(k for k in unknown_of(wanted) if beside["seller"].get(k) not in (None, "", [], {}))
    seller = dict(wanted["seller"])
    seller.update({k: v for k, v in beside["seller"].items() if v not in (None, "", [], {})})
    seller["unknown"] = sorted(unknown_of(wanted) | unknown_of(beside))
    return dict(wanted, seller=seller, buyer=wanted.get("buyer") or beside.get("buyer") or {}), made_up


def check(rule_id, path, case, stage):
    if rule_id not in RULES:
        return None, "unknown rule %s" % rule_id
    src, made_up = source(path, case, stage)
    if not src.get("seller"):
        return None, "no order beside the page names a seller"
    pdf = cn.page_for(path)
    if pdf is None:
        return None, "no printed page to read"
    if made_up:
        return False, ("the order gives %s and the person's files give none: a particular is never made up. Take it "
                       "out and list it in the seller's \"unknown\"" % ", ".join("seller.%s" % k for k in made_up))
    return judge(src, page_text(pdf), evidence_files(pdf, (case or {}).get("folder") or ""))


if __name__ == "__main__":
    ok, why = check("EINV-PARTICULARS", sys.argv[1], {"folder": sys.argv[2] if len(sys.argv) > 2 else ""}, "first")
    print(json.dumps({"rule": "EINV-PARTICULARS", "passed": ok, "evidence": why}, ensure_ascii=False))
