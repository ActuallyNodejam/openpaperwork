#!/usr/bin/env python3
"""The business letter the library prints on, and where each part of it comes from.

    Geometry   DIN 5008:2020 Form B: A4, text on a 25 mm left edge and a 20 mm right margin,
               the address field 20 mm from the left and 45 mm from the top (85 x 45 mm: a 17.7 mm
               zone with the return line, then 27.3 mm for the address), the information block
               from 125 mm across and 50 mm down, the subject 8.46 mm below the lower of the two,
               fold marks at 105 and 210 mm and the hole mark at 148.5 mm.
    Numbers    Unicode CLDR, from skills/_checks/locales.json, the table the locale check reads.
    Language   The customer's language when the spec names one (Stripe sets the invoice language
               per customer the same way), else the seller's country, whose rules govern the
               document (VAT Directive 2006/112/EC Art. 219a). German, English, Swedish and Danish
               have their words; any other language is written in English.
    Company    Directive (EU) 2017/1132 Art. 26: letters and order forms state the register, the
               registration number, the legal form and the registered office. Germany adds the
               managing directors of a GmbH (GmbHG 35a), Sweden the organisation number and seat
               (aktiebolagslagen 28 kap. 5 §).

Standard library only. The PDF is printed with the app's own Chromium, or Playwright outside it.
"""
import datetime as dt
import json
import re
import shutil
import subprocess
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
_TABLE = json.loads((HERE.parent / "_checks" / "locales.json").read_text())["locales"]

LANGS = ("en-GB", "de-DE", "sv-SE", "da-DK")
COUNTRY_LOCALE = {"DE": "de-DE", "AT": "de-DE", "SE": "sv-SE", "DK": "da-DK", "GB": "en-GB", "IE": "en-GB"}
COUNTRY_NAMES = {"germany": "DE", "deutschland": "DE", "austria": "AT", "österreich": "AT", "sweden": "SE",
                 "sverige": "SE", "denmark": "DK", "danmark": "DK", "united kingdom": "GB", "uk": "GB",
                 "great britain": "GB", "england": "GB", "ireland": "IE", "france": "FR", "netherlands": "NL",
                 "norway": "NO", "finland": "FI", "italy": "IT", "spain": "ES", "poland": "PL",
                 "belgium": "BE", "belgië": "BE", "belgique": "BE", "belgien": "BE", "nederland": "NL",
                 "the netherlands": "NL", "niederlande": "NL", "éire": "IE"}

GEOMETRY = {"left": 25, "right": 20, "head_top": 15, "field_x": 20, "field_y": 45, "field_w": 85,
            "return_h": 17.7, "address_h": 27.3, "info_x": 125, "info_y": 50, "info_w": 75,
            "subject_gap": 8.46, "fold": (105, 210), "hole": 148.5, "footer_y": 270}


def country_code(value):
    s = str(value or "").strip()
    if len(s) == 2 and s.isalpha():
        return "GB" if s.upper() == "UK" else s.upper()   # ISO 3166 names the United Kingdom GB
    return COUNTRY_NAMES.get(s.lower(), "")


def language(spec):
    """(locale, why): the customer's language when named, else the seller's country, else English."""
    named = str(spec.get("language") or (spec.get("buyer") or {}).get("language") or "").strip().lower()
    if named:
        for tag in LANGS:
            if tag.lower() == named or tag.split("-")[0] == named.split("-")[0]:
                return tag, "the customer's language %s" % named
        return "en-GB", "the customer's language %s, which the library writes in English" % named
    for party in ("seller", "buyer"):
        code = country_code((spec.get(party) or {}).get("country"))
        if code:
            return COUNTRY_LOCALE.get(code, "en-GB"), "the %s's country %s" % (party, code)
    return "en-GB", "no language and no country given"


def _entry(locale):
    return _TABLE.get(locale) or (_TABLE["us"] if str(locale).lower() == "en-us" else _TABLE["eu"])


def money(value, locale, decimals=2):
    e = _entry(locale)["number"]
    text = ("%%.%df" % decimals) % float(Decimal(str(value)))
    whole, _, frac = text.partition(".")
    sign = "-" if whole.startswith("-") else ""
    whole = whole.lstrip("-")
    groups = []
    while len(whole) > 3:
        groups.insert(0, whole[-3:])
        whole = whole[:-3]
    groups.insert(0, whole)
    return sign + e["group"].join(groups) + (e["decimal"] + frac if decimals else "")


def number(value, locale):
    """A quantity or rate: whole numbers grouped, fractions with the locale's decimal sign."""
    d = Decimal(str(value))
    if d == d.to_integral_value():
        return money(d, locale, 0)
    text = str(d.normalize())
    return text.replace(".", _entry(locale)["number"]["decimal"])


def date(value, locale):
    """An ISO date in the locale's CLDR form; anything else is the person's own words, kept."""
    try:
        d = dt.date.fromisoformat(str(value).strip())
    except ValueError:
        return str(value)
    pattern = _entry(locale)["date"]["pattern"]
    # yyyy, dd and MM pad; a single d or M (Finnish d.M.yyyy) does not.
    parts = {"yyyy": "%04d" % d.year, "YYYY": "%04d" % d.year, "dd": "%02d" % d.day, "DD": "%02d" % d.day,
             "MM": "%02d" % d.month, "d": str(d.day), "M": str(d.month)}
    return "".join(parts.get(tok, tok) for tok in re.findall(r"yyyy|YYYY|dd|DD|MM|d|M|.", pattern))


# ---- company details, Directive (EU) 2017/1132 Art. 26 -------------------------------------

LEGAL_FORM = re.compile(r"\b(GmbH|AG|UG|KG|OHG|SE|AB|HB|KB|ApS|A/S|IVS|P/S|Ltd|Limited|PLC|LLP|Oyj|ASA|Inc|LLC|Corp|Ltée|"
                        r"S\.?A\.?|SARL|SAS|B\.?V\.?|N\.?V\.?|Oy|AS|S\.?r\.?l\.?|S\.?p\.?A\.?|sp\. z o\.o\.|"
                        r"SRL|SC|CommV|SComm|VOF|SNC|VZW|ASBL|OG|FlexCo|DAC|CLG|UC|"
                        # Wave 9: Spain (S.L., S.L.U., S.A.U.), Italy (S.a.p.a., S.n.c., S.a.s.), Poland (sp.k., sp.j., P.S.A.).
                        r"S\.?L\.?U\.?|S\.?L\.?|S\.?A\.?U\.?|S\.?a\.?p\.?a\.?|S\.?n\.?c\.?|S\.?a\.?s\.?|"
                        r"sp\. ?k\.|sp\. ?j\.|P\.?S\.?A\.?)\.?$")
COMPANY_WORDS = {
    "de-DE": {"office": "Sitz", "register": "", "number": "", "directors": "Geschäftsführer"},
    "en-GB": {"office": "Registered office", "register": "Registered in", "number": "Company number", "directors": "Directors"},
    "sv-SE": {"office": "Säte", "register": "", "number": "Org.nr", "directors": "VD"},
    "da-DK": {"office": "Hjemsted", "register": "", "number": "CVR-nr.", "directors": "Direktion"},
    "fr-FR": {"office": "Siège social", "register": "", "number": "SIREN", "directors": "Dirigeants"},
    "nb-NO": {"office": "Forretningskommune", "register": "", "number": "Org.nr.", "directors": "Daglig leder"},
    "fi-FI": {"office": "Kotipaikka", "register": "", "number": "Y-tunnus", "directors": "Toimitusjohtaja"},
    "en-US": {"office": "Principal office", "register": "", "number": "Registration number", "directors": "Officers"},
    "en-CA": {"office": "Registered office", "register": "", "number": "Business number", "directors": "Directors"},
    "fr-CA": {"office": "Siège social", "register": "", "number": "Numéro d'entreprise", "directors": "Administrateurs"},
    "en-AU": {"office": "Registered office", "register": "", "number": "ABN", "directors": "Directors"},
    # Wave 8. "number_first": the number leads and the register follows on its own line, as each country
    # writes it: KvK-nummer 12345678 (Handelsregisterwet 2007 art. 27); Ondernemingsnummer 0123.456.789 and
    # RPR Gent (Wetboek van vennootschappen en verenigingen art. 2:20); FN 123456 a and Handelsgericht Wien
    # (UGB § 14); Company number 654321 and Registered in Ireland (Companies Act 2014 s.151(2)).
    "nl-NL": {"office": "Statutaire zetel", "register": "", "number": "KvK-nummer", "directors": "Bestuurders",
              "order": "number_first"},
    "nl-BE": {"office": "Zetel", "register": "", "number": "Ondernemingsnummer", "directors": "Bestuurders",
              "order": "number_first"},
    "fr-BE": {"office": "Siège", "register": "", "number": "Numéro d'entreprise", "directors": "Administrateurs",
              "order": "number_first"},
    "de-AT": {"office": "Sitz", "register": "", "number": "", "directors": "Geschäftsführer", "order": "number_first"},
    "en-IE": {"office": "Registered office", "register": "Registered in", "number": "Company number",
              "directors": "Directors", "order": "number_first"},
    # Wave 9. "join" sets the register and the number in one line the way each country writes it: Registro
    # Mercantil de Madrid, tomo 00000, folio 000, hoja M-000000 (Código de Comercio art. 24); Registro delle
    # Imprese di Milano n. 01234560157 (Codice civile art. 2250). Poland leads with KRS 0000123456 and sets
    # the registry court on its own line (Kodeks spółek handlowych arts. 206 and 374). "capital", "paid_up", "sole", "liquidation", "directed"
    # and "group" are the further particulars those articles name.
    "es-ES": {"office": "Domicilio social", "register": "", "number": "", "directors": "Administradores",
              "join": "%s, %s", "capital": "Capital suscrito", "paid_up": "Capital desembolsado",
              "liquidation": "En liquidación"},
    "it-IT": {"office": "Sede legale", "register": "", "number": "", "directors": "Amministratori",
              "join": "%s n. %s", "capital": "Capitale sociale", "sole": "Società con unico socio",
              "liquidation": "In liquidazione",
              "directed": "Società soggetta all'attività di direzione e coordinamento di"},
    "pl-PL": {"office": "Siedziba", "register": "", "number": "KRS", "directors": "Zarząd",
              "order": "number_first", "capital": "Kapitał zakładowy", "paid_up": "Kapitał wpłacony",
              "group": "Grupa spółek"},
}
# Paper by locale: US Letter where the United States and Canada write on it, else A4 (ISO 216).
PAPER = {"en-US": "Letter", "en-CA": "Letter", "fr-CA": "Letter"}
PAPER_MM = {"A4": (210, 297), "Letter": (215.9, 279.4)}


def paper(locale):
    return PAPER.get(locale, "A4")
# French companies registered at the RCS state their legal form, share capital, SIREN and "RCS" with
# the register's city (service-public.fr F31808).
FR_COMPANY_FORMS = {"SA", "SAS", "SASU", "SARL", "EURL", "SNC", "SCA", "SCS", "SE", "SELARL", "SELAS"}


def legal_form(seller):
    found = LEGAL_FORM.search(str(seller.get("name") or "").strip())
    return seller.get("legal_form") or (found.group(1) if found else "")


def company_missing(seller):
    """What Art. 26 (and GmbHG 35a for a GmbH) asks for that the seller data does not give."""
    form = legal_form(seller)
    if not form:
        return []
    country = country_code(seller.get("country"))
    if country == "AU":
        # Corporations Act 2001 s 153: a company's public documents carry its name and its ABN or ACN.
        return [] if seller.get("register_number") or seller.get("abn") else ["register_number (ABN or ACN)"]
    if country in ("US", "CA"):
        return []                      # no Art. 26 duty outside the EEA; nothing the letter must add
    if country == "BE":
        # Code des sociétés et des associations / Wetboek van vennootschappen en verenigingen art. 2:20: the
        # seat, the enterprise number (KBO/BCE) and RPR or RPM with the court of the seat.
        missing = [k for k in ("registered_office", "register_number") if not seller.get(k)]
        if not re.search(r"\b(RPR|RPM)\b", str(seller.get("register") or "")):
            missing.append("register (RPR or RPM and the court of the seat)")
        return missing
    if country == "NL":
        # Handelsregisterwet 2007 art. 27: the KvK number; BW 2:186 and 2:75: the full name and the
        # statutory seat (woonplaats) of a BV or NV.
        return [k for k in ("register_number", "registered_office") if not seller.get(k)]
    if country == "IE":
        # Companies Act 2014 s.151(2): name and legal form, place of registration and number, registered
        # office; s.151(1): every director's name, and nationality if not Irish.
        missing = [k for k in ("registered_office", "register_number") if not seller.get(k)]
        if not seller.get("managing_directors"):
            missing.append("managing_directors (every director's name, and nationality if not Irish)")
        return missing
    bare = form.replace(".", "").replace(" ", "").upper()
    if country == "ES":
        # Código de Comercio art. 24.1: the registered office (domicilio), the particulars of the entry in
        # the Registro Mercantil and the legal form; a mention of the capital names the subscribed and the
        # paid-up capital.
        missing = [k for k in ("registered_office", "register", "register_number") if not seller.get(k)]
        if seller.get("share_capital") and not seller.get("paid_up_capital"):
            missing.append("paid_up_capital (art. 24: a mention of the capital names the subscribed and the paid-up capital)")
        return missing
    if country == "IT":
        # Codice civile art. 2250: the seat, the register office where the company is entered and the
        # number; an S.p.A., S.a.p.a. or S.r.l. the capital as paid up and shown in the last balance sheet.
        missing = [k for k in ("registered_office", "register", "register_number") if not seller.get(k)]
        if bare in ("SPA", "SAPA", "SRL", "SRLS") and seller.get("share_capital") in (None, ""):
            missing.append("share_capital (as paid up, art. 2250)")
        return missing
    if country == "PL" and bare in ("SPZOO", "SA"):
        # Kodeks spółek handlowych art. 206 § 1 (sp. z o.o.) and art. 374 § 1 (S.A.): the seat and address,
        # the registry court and the number in the register, the NIP, the share capital; an S.A. also the
        # paid-up capital.
        missing = [k for k in ("registered_office", "register", "register_number") if not seller.get(k)]
        if not seller.get("vat_id"):
            missing.append("vat_id (NIP)")
        if seller.get("share_capital") in (None, ""):
            missing.append("share_capital")
        if bare == "SA" and seller.get("paid_up_capital") in (None, ""):
            missing.append("paid_up_capital (art. 374 § 1 pkt 4)")
        return missing
    if country == "FR":
        missing = [] if seller.get("siren") else ["siren"]
        if form.upper() in FR_COMPANY_FORMS:
            missing += [k for k in ("share_capital", "rcs") if seller.get(k) in (None, "")]
        return missing
    missing = []
    if not seller.get("registered_office"):
        missing.append("registered_office")
    if not seller.get("register_number"):
        missing.append("register_number")
    if country_code(seller.get("country")) in ("DE", "AT") and not seller.get("register"):
        missing.append("register")
    # The Company, LLP and Business (Names and Trading Disclosures) Regulations 2015 (SI 2015/17) reg. 25: a UK
    # company's letters, order forms and websites give the part of the UK it is registered in, its number and
    # its registered office.
    if country == "GB" and not seller.get("register"):
        missing.append("register (the part of the UK the company is registered in, e.g. England and Wales)")
    # GmbHG 35a is German; Austria's UGB § 14 asks for no managing directors on a letter.
    if form in ("GmbH", "UG") and country != "AT" and not seller.get("managing_directors"):
        missing.append("managing_directors")
    return missing


def company_lines(seller, locale):
    w = COMPANY_WORDS.get(locale, COMPANY_WORDS["en-GB"])
    out = []
    # French sets a no-break space before the colon (Siège\u00a0: ...), as the rest of the French letter does.
    colon = "\u00a0: " if str(locale).startswith("fr") else ": "
    if seller.get("registered_office"):
        out.append("%s%s%s" % (w["office"], colon, seller["registered_office"]))
    reg, num = seller.get("register"), seller.get("register_number")
    if w.get("join") and reg and num:
        out.append(w["join"] % (reg, num))
    elif w.get("order") == "number_first" and num:
        out.append("%s %s" % (w["number"], num) if w["number"] else str(num))
        if reg:                        # its own line: a footer column wraps a long one
            out.append("%s %s" % (w["register"], reg) if w["register"] else str(reg))
    elif reg and num:
        out.append(("%s %s, %s" % (w["register"], reg, num)) if w["register"] else "%s, %s" % (reg, num))
    elif num:
        out.append("%s %s" % (w["number"], num) if w["number"] else num)
    directors = seller.get("managing_directors") or []
    if isinstance(directors, str):
        directors = [directors]
    if directors:
        out.append("%s%s%s" % (w["directors"], colon, ", ".join(directors)))
    if country_code(seller.get("country")) == "FR":
        out += french_lines(seller)
    out += capital_lines(seller, w, colon)
    # Runs of ordinary white space become one space; the French no-break space stays what it is.
    return [re.sub(r"[ \t\r\n]+", " ", x).strip(" \t\r\n") for x in out]


def french_lines(seller):
    """What a French company's letters and order forms say of it, as its invoice does (Code de commerce
    R123-237 and R123-238): the legal form with the share capital (SAS au capital de 10 000 €) and RCS with
    the register's town and the SIREN (RCS Lyon 000 000 018), or the SIREN alone when no RCS is given."""
    out = []
    form, capital = seller.get("legal_form") or legal_form(seller), seller.get("share_capital")
    if form and capital not in (None, ""):
        if isinstance(capital, (int, float)) and not isinstance(capital, bool):
            whole = float(capital) == int(capital)
            capital = "%s\u00a0€" % money(capital, "fr-FR", 0 if whole else 2)
        out.append("%s au capital de %s" % (form, capital))
    siren = re.sub(r"\D", "", str(seller.get("siren") or ""))
    spaced = " ".join((siren[:3], siren[3:6], siren[6:])).strip() if len(siren) == 9 else str(seller.get("siren") or "")
    if seller.get("rcs") and spaced:
        out.append("%s %s" % (seller["rcs"], spaced))
    elif spaced:
        out.append("SIREN %s" % spaced)
    return out


def further_lines(party):
    """A company's further particulars: the lines the data file gives in "further" for a fact that has no field
    of its own (a licence number, a trade body, a second register), printed as written under the company's
    register details, where each country's letter puts such lines. Nothing is added to them."""
    lines = party.get("further") or []
    if isinstance(lines, str):
        lines = [lines]
    return [re.sub(r"[ \t\r\n]+", " ", str(x)).strip() for x in lines if str(x).strip()]


def capital_lines(seller, w, colon=": "):
    """The particulars Spain, Italy and Poland add to the register line, when the seller data gives them:
    the capital (subscribed and paid up), a sole shareholder, liquidation, the directing company (Codice
    civile art. 2497-bis) and the group of companies (KSH art. 206 § 1 pkt 5)."""
    out = []
    if w.get("capital") and seller.get("share_capital") not in (None, ""):
        out.append("%s%s%s" % (w["capital"], colon, seller["share_capital"]))
    if w.get("paid_up") and seller.get("paid_up_capital") not in (None, ""):
        out.append("%s%s%s" % (w["paid_up"], colon, seller["paid_up_capital"]))
    if w.get("sole") and seller.get("sole_shareholder"):
        out.append(w["sole"])
    if w.get("liquidation") and seller.get("in_liquidation"):
        out.append(w["liquidation"])
    if w.get("directed") and seller.get("directed_by"):
        out.append("%s %s" % (w["directed"], seller["directed_by"]))
    if w.get("group") and seller.get("group"):
        out.append("%s%s%s" % (w["group"], colon, seller["group"]))
    return out


# ---- the sheet --------------------------------------------------------------------------------

# A page that runs long: mm kept clear at the top of a following page and above the foot of every page,
# the same two numbers the window letters keep (business-letter/scripts/window_letter.py).
PAGE_TOP, PAGE_FOOT = 25, 30


def sheet_css(paper="A4"):
    g = GEOMETRY
    w, h = PAPER_MM.get(paper, PAPER_MM["A4"])
    return ("""
@page{size:%s;margin:0}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:%smm}
body{position:relative;min-height:%smm;""" % (paper, w, h)) + """font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;color:#12100E;font-size:10pt;line-height:1.4}
.mark{position:absolute;left:0;width:5mm;border-top:0.2mm solid #9A9088}
.hole{width:7mm}
.head{position:absolute;left:%(left)smm;right:%(right)smm;top:%(head_top)smm}
.head .name{font-size:15pt;font-weight:700;letter-spacing:-.2px}
.field{position:absolute;left:%(field_x)smm;top:%(field_y)smm;width:%(field_w)smm;padding-left:5mm}
.return{height:%(return_h)smm;display:flex;align-items:flex-end;padding-bottom:1mm;font-size:7pt;color:#6B6259}
.return span{border-bottom:0.2mm solid #9A9088}
.address{height:%(address_h)smm;font-size:10pt;line-height:1.35}
.info{position:absolute;left:%(info_x)smm;top:%(info_y)smm;width:%(info_w)smm}
.info div{display:flex;gap:3mm;font-size:8.5pt;line-height:1.5}
.info dt{width:34mm;flex:none;color:#6B6259}
.info dd{font-variant-numeric:tabular-nums}
.body{padding:0 %(right)smm 0 %(left)smm}
h1{font-size:12pt;font-weight:700;margin-bottom:5mm}
table{width:100%%;border-collapse:collapse}
thead{display:table-header-group}
tr{break-inside:avoid}
.flow>tbody>tr{break-inside:auto}
.flow>*>tr>td{padding:0;border:0;font-size:inherit}
.flow .top{height:%(page_top)smm}
.flow .foot{height:%(page_foot)smm}
.end,.sum{break-inside:avoid}
th{font-size:8pt;color:#6B6259;font-weight:600;text-align:left;border-bottom:0.3mm solid #12100E;padding:1.5mm 0;vertical-align:bottom}
td{border-bottom:0.2mm solid #E3DCD3;padding:1.8mm 0;vertical-align:top;font-size:9pt}
th+th,td+td{padding-left:2.5mm}
.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.sum{margin-top:4mm;margin-left:auto;width:85mm}
.sum td{border:none;padding:0.8mm 0;font-size:9.5pt}
.sum td:first-child{color:#6B6259}
.sum .gross td{border-top:0.3mm solid #12100E;padding-top:2mm;font-weight:700;color:#12100E}
.terms{margin-top:6mm;font-size:9.5pt}
.terms p{margin-top:1.5mm}
.note{margin-top:4mm;font-size:9.5pt}
.sign{margin-top:14mm;font-size:9.5pt}
.extra{margin-bottom:5mm;font-size:9.5pt}
footer{position:fixed;left:%(left)smm;right:%(right)smm;bottom:8mm;border-top:0.2mm solid #E3DCD3;padding-top:2.5mm;
 display:grid;grid-template-columns:1.1fr 1.2fr 1.1fr;gap:5mm;font-size:7pt;line-height:1.45;color:#6B6259}
""" % dict({k: (v if not isinstance(v, tuple) else v[0]) for k, v in g.items()}, page_top=PAGE_TOP, page_foot=PAGE_FOOT)


# The information block ending on the text's right edge, the one rule for a DIN 5008 page since wave 9:
# it still starts 125 mm across (Form B) and ends 20 mm short of the paper's edge, where the text and an
# invoice's table end; the labels take a column as wide as the longest of them and a long value wraps in
# its own column. Invoices print this way since the wave 8 close-out, letters since wave 9.
INFO_GRID = (".info{display:grid;grid-template-columns:max-content minmax(0,1fr);column-gap:3mm}"
             ".info div{display:contents}.info dt{width:auto;white-space:nowrap}"
             ".info dd{min-width:0;overflow-wrap:anywhere}")
ADDRESS_LINE = 4.4      # mm: six address lines fill the 27.3 mm address zone


def info_width(paper="A4"):
    """mm from 125 mm across to the text's right edge (65 on A4)."""
    return round(PAPER_MM[paper][0] - GEOMETRY["right"] - GEOMETRY["info_x"], 2)


def info_css(paper="A4"):
    """CSS a DIN 5008 page adds after sheet_css: the block ends on the text's right edge, and the address
    keeps the line height that fits six lines in its zone."""
    return "\n.info{width:%smm}%s\n.address{line-height:%smm}\n" % (info_width(paper), INFO_GRID, ADDRESS_LINE)


def keep(text):
    """Escaped text in which a token with a hyphen stays on one line and an e-mail address breaks only
    after its @. A line that ends in a hyphen reads back from the PDF as a hyphenated word with the hyphen
    gone (hoja M-000000 as M000000), and an address broken inside its domain is hard to read."""
    out = []
    for tok in re.split(r"(\s+)", str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")):
        if "@" in tok:
            name, _, host = tok.partition("@")
            tok = '<span style="white-space:nowrap">%s@</span><wbr><span style="white-space:nowrap">%s</span>' % (name, host)
        elif "-" in tok:
            tok = '<span style="white-space:nowrap">%s</span>' % tok
        out.append(tok)
    return "".join(out)


def sheet_html(locale, title, generator, seller_name, return_line, address_html, info_rows, body_html, footer_cols,
               paper="A4", keep_tokens=False):
    """The whole page. info_rows: [(label, value)]; footer_cols: three lists of lines. paper: A4 or Letter; a
    Letter page keeps the Form B positions, which also put the address in a US No. 10 window. keep_tokens:
    values and footer lines through keep() (letters since wave 9; other documents as they were)."""
    g = GEOMETRY
    esc = lambda s: str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    val = keep if keep_tokens else esc
    info = "".join("<div><dt>%s</dt><dd>%s</dd></div>" % (esc(k), val(v)) for k, v in info_rows if v not in (None, ""))
    foot = "".join("<div>%s</div>" % "<br>".join(val(x) for x in col if x) for col in footer_cols)
    # The subject sits 8.46 mm below whichever ends lower, the address field or the information block.
    # The text runs in a table whose head and foot rows are empty and repeat on every printed page, so a
    # second page starts PAGE_TOP mm down and no page runs into the footer; the first page's head row is
    # taken off the padding again.
    script = """<script>
const info=document.querySelector('.info'),mm=96/25.4;
const low=Math.max(%(field_end)s*mm,(info.offsetTop+info.offsetHeight));
document.querySelector('.body').style.paddingTop=(low+%(gap)s*mm-%(page_top)s*mm)+'px';
</script>""" % {"field_end": g["field_y"] + g["return_h"] + g["address_h"], "gap": g["subject_gap"], "page_top": PAGE_TOP}
    return """<!doctype html><html lang="%(lang)s"><head><meta charset="utf-8">
<meta name="generator" content="%(gen)s">
<meta name="layout" content="DIN 5008:2020 Form B%(on)s">
<title>%(title)s</title><style>%(css)s</style></head><body>
<div class="mark" style="top:%(f1)smm"></div><div class="mark hole" style="top:%(hole)smm"></div><div class="mark" style="top:%(f2)smm"></div>
<div class="head"><div class="name">%(seller)s</div></div>
<div class="field"><div class="return"><span>%(ret)s</span></div><div class="address">%(addr)s</div></div>
<dl class="info">%(info)s</dl>
<section class="body"><table class="flow"><thead><tr><td><div class="top"></div></td></tr></thead>
<tfoot><tr><td><div class="foot"></div></td></tr></tfoot>
<tbody><tr><td>%(body)s</td></tr></tbody></table></section>
<footer>%(foot)s</footer>
%(script)s
</body></html>
""" % {"lang": locale, "gen": generator, "title": esc(title), "css": sheet_css(paper), "f1": g["fold"][0], "f2": g["fold"][1],
       "hole": g["hole"], "seller": esc(seller_name), "ret": esc(return_line), "addr": address_html, "info": info,
       "body": body_html, "foot": foot, "script": script,
       "on": "" if paper == "A4" else " geometry on %s" % paper}


def print_pdf(html, pdf, paper="A4"):
    """Print with the app's own Chromium, or with Playwright outside the app. The page's own @page size
    rules in the app; Playwright is told the paper too."""
    tool = shutil.which("nodejam-print")
    why = "nodejam-print is not on PATH"
    if tool:
        r = subprocess.run([tool, str(html), str(pdf)], capture_output=True, text=True)
        if r.returncode == 0:
            return "nodejam-print"
        why = ((r.stderr or r.stdout).strip().splitlines() or ["nodejam-print failed"])[-1]
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sync_playwright = None
    if sync_playwright is not None:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=["--no-sandbox"])
            page = browser.new_page()
            # The page measures itself as it will print (its tables give way by what they measure).
            page.emulate_media(media="print")
            page.goto(Path(html).resolve().as_uri())
            page.pdf(path=str(pdf), format=paper, print_background=True)
            browser.close()
        return "playwright (%s)" % why
    uv = shutil.which("uv")
    if uv:
        code = ("import sys;from playwright.sync_api import sync_playwright as s\n"
                "with s() as pw:\n b=pw.chromium.launch(args=['--no-sandbox']);p=b.new_page();p.emulate_media(media='print')\n"
                " p.goto('file://'+sys.argv[1]);p.pdf(path=sys.argv[2],format=sys.argv[3],print_background=True);b.close()")
        r = subprocess.run([uv, "run", "--with", "playwright", "python", "-c", code,
                            str(Path(html).resolve()), str(pdf), paper], capture_output=True, text=True)
        if r.returncode == 0:
            return "playwright through uv (%s)" % why
        why = ((r.stderr or r.stdout).strip().splitlines() or [why])[-1]
    raise RuntimeError("could not print the page: %s; run this inside the app" % why)


# ---- letters outside DIN 5008: the Nordics and the English-speaking markets (waves 6 and 7) ----------
#
# A letter is printed where it is sent from, so the sender's country picks the page and the envelope
# window; the address is written the way the recipient's post office reads it; the words and the date
# are the letter's language. Germany, Sweden and any country not named here keep DIN 5008 Form B above.
#
#   Window     Where the address must sit on the sheet, in mm from the sheet's top-left corner, with the
#              sheet at the top-left of its envelope. Checked against each operator's published
#              specification on 2026-10-09 (WINDOW_SOURCES below says, per country, what was read and
#              what it confirms). No operator publishes an exact window position: each publishes the
#              zone a window or an address must stay in, so every rectangle here is a common maker's
#              window placed inside that zone, and says so.
#   Address    UPU addressing sheets for each country and the operators' own guidance, cited, not
#              copied: USPS Publication 28 s.224 (CITY ST  ZIP+4, capitals, no punctuation), Canada Post
#              (MUNICIPALITY PROV  A1A 1A1), Australia Post (LOCALITY STATE  POSTCODE in capitals),
#              Royal Mail (POST TOWN in capitals, the postcode alone on the last line), Posten and Posti
#              (postcode, then the town in capitals), PostNord Danmark (postcode, then the town). Mail
#              to another country ends with the country in capitals (UPU Letter Post Regulations
#              RL 123.3.3). Wave 8: bpost (MassPost Gids section 1, January 2026: three to seven lines,
#              left-aligned, no blank lines, the postcode and the municipality last, the municipality
#              in capitals), PostNL (Vormgevingsvoorwaarden 2026, bijlage 1 and 3: 1234 AB, two spaces,
#              the town in capitals), Österreichische Post (Richtig adressieren: the postcode and the
#              town; abroad the town and the country in capitals) and An Post (Speed up your post: every
#              element on its own line, the county above the Eircode, the Eircode last, no punctuation).
#   Dates      Unicode CLDR long dates: 9. oktober 2026 (nb, da), October 9, 2026 (en-US, en-CA),
#              9 October 2026 (en-GB, en-AU; GOV.UK style guide, OGL v3), 9 octobre 2026 (fr; the
#              first of the month 1er), and 9.10.2026 in Finnish documents. Wave 8: 9 oktober 2026
#              (nl, nl-BE), 9 octobre 2026 (fr-BE), 9. Oktober 2026 and Jänner (de-AT), 9 October 2026
#              (en-IE), all CLDR 48 long dates.

INCH = 25.4
LONG_DATE = {"nb-NO": "{d}. {month} {y}", "da-DK": "{d}. {month} {y}", "de-DE": "{d}. {month} {y}",
             "sv-SE": "{d} {month} {y}", "en-GB": "{d} {month} {y}", "en-AU": "{d} {month} {y}",
             "en-US": "{month} {d}, {y}", "en-CA": "{month} {d}, {y}", "fr-CA": "{d} {month} {y}",
             "fr-FR": "{d} {month} {y}", "fi-FI": "{d}.{m}.{y}",
             # Wave 8 (CLDR long dates for nl, nl-BE, fr-BE, de-AT and en-IE).
             "nl-NL": "{d} {month} {y}", "nl-BE": "{d} {month} {y}", "fr-BE": "{d} {month} {y}",
             "de-AT": "{d}. {month} {y}", "en-IE": "{d} {month} {y}",
             # Wave 9 (CLDR 48 long dates: d 'de' MMMM 'de' y for es, d MMMM y for it and pl).
             "es-ES": "{d} de {month} de {y}", "it-IT": "{d} {month} {y}", "pl-PL": "{d} {month} {y}"}
MONTH_NAMES = {
    "nb": "januar februar mars april mai juni juli august september oktober november desember",
    "da": "januar februar marts april maj juni juli august september oktober november december",
    "de": "Januar Februar März April Mai Juni Juli August September Oktober November Dezember",
    "sv": "januari februari mars april maj juni juli augusti september oktober november december",
    "en": "January February March April May June July August September October November December",
    "fr": "janvier février mars avril mai juin juillet août septembre octobre novembre décembre",
    "fi": "tammikuuta helmikuuta maaliskuuta huhtikuuta toukokuuta kesäkuuta heinäkuuta elokuuta syyskuuta "
          "lokakuuta marraskuuta joulukuuta",
    "nl": "januari februari maart april mei juni juli augustus september oktober november december",
    "es": "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre",
    "it": "gennaio febbraio marzo aprile maggio giugno luglio agosto settembre ottobre novembre dicembre",
    # Polish dates take the month in the genitive (CLDR pl, months, format, wide).
    "pl": "stycznia lutego marca kwietnia maja czerwca lipca sierpnia września października listopada grudnia",
    # Austria writes Jänner (CLDR de-AT); a locale's own list wins over its language's.
    "de-AT": "Jänner Februar März April Mai Juni Juli August September Oktober November Dezember",
}


def month_names(locale):
    """The month names of a locale: its own list when it has one (de-AT), else its language's."""
    return MONTH_NAMES.get(str(locale)) or MONTH_NAMES.get(str(locale).split("-")[0])


def long_date(value, locale):
    """An ISO date written out the way a letter or minutes of that language write it (CLDR long)."""
    try:
        d = dt.date.fromisoformat(str(value).strip())
    except ValueError:
        return str(value)
    pattern = LONG_DATE.get(locale)
    if not pattern:
        return date(value, locale)
    day = "1er" if locale.startswith("fr") and d.day == 1 else str(d.day)
    month = month_names(locale).split()[d.month - 1]
    return pattern.format(d=day, m=d.month, y=d.year, month=month)


def _layout(name, country, paper, left, right, window, clear, address_at, info, body_y, date_at=None,
            text_x=None, envelope="", source="", inset=None, line=4.4):
    """window: (x, y, width, height) of the envelope window on the sheet. clear: how far the address stays
    inside every window edge; inset: (left, top, right, bottom) when the edges differ (An Post). line: the
    height of one address line in mm."""
    return {"name": name, "country": country, "paper": paper, "left": left, "right": right,
            "window": window, "clear": clear, "address_at": address_at, "info": info, "body_y": body_y,
            "date_at": date_at, "text_x": text_x or left, "envelope": envelope, "source": source,
            "inset": inset or (clear, clear, clear, clear), "line": line}


def window_box(layout):
    """(x0, y0, x1, y1): where the address text of a layout must stay, the window less its insets."""
    wx, wy, ww, wh = layout["window"]
    il, it, ir, ib = layout.get("inset") or (layout["clear"],) * 4
    return wx + il, wy + it, wx + ww - ir, wy + wh - ib


def info_box(layout):
    """(x, y, width): where a document on this layout puts its block of dates and numbers: right of a
    left-hand window from 125 mm, or left of a right-hand window (Belgium), level with the window."""
    wx, wy, ww, wh = layout["window"]
    page_w = PAPER_MM[layout["paper"]][0]
    if wx + ww / 2 > page_w / 2:
        return layout["left"], wy, max(40, wx - layout["left"] - 5)
    x = max(GEOMETRY["info_x"], wx + ww + 5)
    return x, wy, page_w - layout["right"] - x


_US_WINDOW = (7 / 8 * INCH, (4.125 - 0.5 - 1.125) * INCH, 4.5 * INCH, 1.125 * INCH)
LAYOUTS = {
    "us": _layout("United States: Letter, full block, #10 window envelope", "US", "Letter",
                  INCH, INCH, _US_WINDOW, INCH / 8, (INCH, _US_WINDOW[1] + INCH / 8 + 0.6), "above", 101,
                  date_at=44, envelope="#10 window envelope, window 4 1/2 x 1 1/8 in, 7/8 in from the left, 1/2 in from the bottom",
                  source="USPS Publication 28 s.224; USPS DMM 601 6.3 and Publication 25 (window clearance); full block"),
    "ca": _layout("Canada: Letter, full block, #10 window envelope", "CA", "Letter",
                  INCH, INCH, _US_WINDOW, INCH / 8, (INCH, _US_WINDOW[1] + INCH / 8 + 0.6), "above", 101,
                  date_at=44, envelope="#10 window envelope, window 4 1/2 x 1 1/8 in, 7/8 in from the left, 1/2 in from the bottom",
                  source="Canada Post addressing guidelines; OQLF, the parts of an administrative letter (fr-CA)"),
    "uk": _layout("United Kingdom: A4, blocked, DL window envelope", "GB", "A4", 25, 20,
                  (19, 57, 90, 35), 0, (25, 59), "right", 100,
                  envelope="DL window envelope, window 90 x 35 mm at 19 mm from the left and 18 mm from the bottom",
                  source="Royal Mail Mailmark letters specification (window limits); Royal Mail addressing; GOV.UK style guide for dates (OGL v3)"),
    "au": _layout("Australia: A4, blocked, DL window envelope", "AU", "A4", 25, 20,
                  (20, 57, 89, 35), 0, (25, 59), "right", 100,
                  envelope="DL window envelope, window 90 x 35 mm at 19 mm from the left and 18 mm from the bottom, or 90 x 45 mm at 20 and 15 mm",
                  source="Australia Post addressing; Australian Government Style Manual, emails and letters (cited)"),
    "no": _layout("Norway: A4, C5/E65 window envelope, reference line", "NO", "A4", 25, 20,
                  (20, 50, 90, 40), 0, (25, 54), "refline", 116,
                  envelope="C5/E65 window envelope, window 90 x 45 mm 20 mm from the left and 15 mm from the bottom (ISO 269, DIN 680); the address ends 20 mm above the bottom edge, which Bring keeps for barcodes",
                  source="Bring MV1 terms for machine-sorted mail; Posten addressing (UPU sheet NOR)"),
    "dk": _layout("Denmark: A4, C5/E65 window envelope", "DK", "A4", 25, 20,
                  (20, 50, 90, 45), 0, (25, 54), "right", 102,
                  envelope="C5/E65 window envelope, window 90 x 45 mm 20 mm from the left and 15 mm from the bottom (ISO 269, DIN 680)",
                  source="PostNord Danmark addressing (UPU sheet DNK)"),
    # Finland: the SFS 2487 field runs from 36 mm down; Posti's own window envelopes open 40 mm down, so
    # the address keeps to the part both show, 40 to 66 mm.
    "fi": _layout("Finland: A4 on SFS 2487, E window envelope", "FI", "A4", 20, 15,
                  (18, 40, 90, 26), 0, (20, 40.4), "fi", 90, text_x=43, line=4.2,
                  envelope="C65 or E65 window envelope: the part of the SFS 2487 address field (90 x 30 mm, 18 mm from the left, 36 mm from the top) that Posti's own window (18 mm from the left, 40 mm from the top) shows",
                  source="Posti's envelope range (window 18 mm from the left, 40 mm from the top); SFS 2487 (paid; numbers as koma-script-SFS carries them); Posti addressing (UPU sheet FIN)"),
    # ---- wave 8: Belgium, the Netherlands, Austria, Ireland ----------------------------------------
    # Belgium: bpost keeps an indexing zone 30 mm high and 140 mm long at the bottom right of the envelope,
    # which a left-hand DIN window enters, and puts an address without a window on the right. So the window
    # is on the right: 15 mm from the envelope's right edge, under the 40 mm franking zone, above the
    # indexing zone, the address 4 mm inside it.
    "be": _layout("Belgium: A4, window on the right (114 x 229 mm envelope)", "BE", "A4", 25, 20,
                  (104, 44, 106, 40), 4, (115, 48), "refline", 112,
                  envelope="114 x 229 mm window envelope with the window on the right: any opening inside 89-214 mm across and 40-84 mm down the envelope",
                  source="bpost MassPost Gids, sections 1 and 2, January 2026 (zones; no window position published)"),
    "nl": _layout("Netherlands: A4, EA5/6 or DL window envelope, reference line", "NL", "A4", 25, 20,
                  (20, 50, 90, 40), 0, (25, 54), "refline", 116,
                  envelope="EA5/6 or DL window envelope (110 x 220 mm), window on the left 90 x 45 mm 20 mm from the left and 15 mm from the bottom; its lowest 5 mm lie in PostNL's index zone and stay empty",
                  source="PostNL Vormgevingsvoorwaarden 2026, artikel 1 and bijlagen 1, 3 and 4 (zones; no window position published)"),
    # Austria: the DIN lang window (50-95 mm down) and the C6/5 window (54-99 mm down) share 54-95 mm; the
    # Post asks for 5 mm between the address and the window's edge.
    "at": _layout("Austria: A4, DIN lang or C6/5 window envelope", "AT", "A4", 25, 20,
                  (20, 54, 90, 41), 5, (25, 59), "right", 105,
                  envelope="DIN lang (110 x 220 mm) or C6/5 (114 x 229 mm) window envelope, window on the left 90 x 45 mm 20 mm from the left and 15 mm from the bottom",
                  source="Österreichische Post, Richtig adressieren (window at least 90 x 35 mm, 5 mm quiet zone; no window position published)"),
    # Ireland: An Post keeps text 15 mm from the window's left edge and 5 mm from its other edges.
    "ie": _layout("Ireland: A4, blocked, DL window envelope", "IE", "A4", 25, 20,
                  (19, 57, 90, 35), 5, (34, 62), "right", 100, inset=(15, 5, 5, 5), line=4.1,
                  envelope="DL window envelope (110 x 220 mm), window 90 x 35 mm at 19 mm from the left and 18 mm from the bottom",
                  source="An Post, Speed up your post (address block, clear zone and window insets; no window position published)"),
    # ---- wave 9: Spain, Italy, Poland ---------------------------------------------------------------
    # All three operators put the address at the bottom right of the envelope and publish the zone it must
    # stay in, not a window position. The window here is the DIN window mirrored to the right on a DL
    # envelope (90 x 45 mm, 20 mm from the right edge and 15 mm from the bottom), which lies inside each
    # zone; the insets keep the address where the operator's own clearances and the country's other usual
    # envelope still show it.
    # Spain: Correos' zone runs to 140 mm from the right edge, under the 40 mm franking zone and above the
    # 15 mm bar-code strip. No clearance inside a window is published; 10, 8, 5 and 5 mm are this layout's
    # own, so that the 115 x 225 mm envelope shows the address too.
    "es": _layout("Spain: A4, window on the right (DL 110 x 220 mm envelope)", "ES", "A4", 25, 20,
                  (110, 50, 90, 45), 5, (120, 58.4), "refline", 122, inset=(10, 8, 5, 5),
                  envelope="DL (110 x 220 mm) or 115 x 225 mm window envelope with the window on the right: 90 x 45 mm, 20 mm from the right edge and 15 mm from the bottom, or any opening inside Correos' address zone that shows 120-195 mm across and 58-90 mm down the sheet",
                  source="Correos, Dimensiones y pesos de los envíos, drawing of a normalised item (zones; no window position published)"),
    # Italy: Poste Italiane keeps 15 mm white left and right of the address block and 5 mm above and below,
    # and asks for a window at the bottom right, large enough for the whole block.
    "it": _layout("Italy: A4, window on the right (DL 110 x 220 mm or 110 x 230 mm envelope)", "IT", "A4", 25, 20,
                  (110, 50, 90, 45), 5, (125, 55.4), "refline", 122, inset=(15, 5, 5, 5),
                  envelope="DL (110 x 220 mm) or 110 x 230 mm window envelope with the window on the right: 90 x 45 mm, 20 mm from the right edge and 15 mm from the bottom, or any opening inside Poste Italiane's address area that shows 125-195 mm across and 55-90 mm down the sheet",
                  source="Poste Italiane, Caratteristiche standard degli invii, Posta indescritta, March 2026 (address area and zones of respect; no window position published)"),
    # Poland: Poczta Polska keeps 10 mm free around the address block inside a window, 5 mm on the right,
    # and a window at least 15 mm from the envelope's right edge.
    "pl": _layout("Poland: A4, window on the right (DL 110 x 220 mm envelope)", "PL", "A4", 25, 20,
                  (110, 50, 90, 45), 10, (120, 60.3), "refline", 122, inset=(10, 10, 5, 10), line=4.1,
                  envelope="DL (110 x 220 mm) window envelope with the window on the right: 90 x 45 mm, 20 mm from the right edge and 15 mm from the bottom, inside Poczta Polska's address field",
                  source="Poczta Polska, Zasady poprawnego adresowania i oznakowania przesyłek listowych (address field and window clearances; no window position published)"),
}

# What was read about each country's window, and what it confirms (2026-10-09). "zone" means the operator
# publishes the area a window or address must stay in, not a window position.
WINDOW_SOURCES = {
    "DE": ("zone", "Deutsche Post, Automationsfähige Briefsendungen, Leitfaden, January 2026, 3.1.2: a window at least 40 mm from "
                   "the top and 15 mm from the other edges, usually 90 x 45 mm; the DIN 680 position and the DIN 5008 field "
                   "are paid standards and were not read"),
    "SE": ("unconfirmed", "not confirmed against a PostNord document; the page is DIN 5008 Form B"),
    "DK": ("unconfirmed", "not confirmed against a PostNord document; the ISO 269 / DIN 680 window as for Norway"),
    "NO": ("zone", "Posten Bring, MV1 Plain envelopes, 2022-11-11, section 6: the address at least 40 mm from the top and "
                   "15 mm from the sides, the lowest 20 mm kept for barcodes; no window position published"),
    "FI": ("partly", "Posti, envelope range from 1.1.2019: C65 and C5 windows 95 x 35 mm, 18 mm from the left and 40 mm from "
                     "the top (E5: 90 x 30 mm); SFS 2487 is a paid standard and was not read"),
    "US": ("zone", "USPS DMM 601.6.3 (1/8 in clear inside the window) and 202.2.1 (the OCR read area); the #10 window "
                   "itself from a printer's listing, not a standard"),
    "CA": ("zone", "Canada Post, Machineable Mail Standard self-assessment tool, 2021-01-11: the address zone 35 mm from the "
                   "top and 10 mm from the other edges, windows inside it; the #10 window from a printer's listing"),
    "GB": ("confirmed", "Royal Mail, Mailmark Letters specification requirements, February 2020: windows at least 15 mm from "
                        "the top and sides and 18 mm from the bottom; the 90 x 35 mm DL window at 19 and 18 mm from a "
                        "reseller's listing"),
    "AU": ("zone", "Australia Post, Envelope zones and Correct addressing, 2023: 15 mm kept clear along the bottom and the "
                   "right edge; no window drawing, so the position is not confirmed"),
    "BE": ("zone", "bpost, MassPost Gids section 2, January 2026: the address on the right, a window never in the 30 x 140 mm "
                   "indexing zone, 15 mm from the side edges, 4 mm around the address; no window position published"),
    "NL": ("zone", "PostNL, Vormgevingsvoorwaarden 2026 (from 1 July 2026): the address zone 40 mm from the top and 15 mm "
                   "from the other sides, an index zone 20 mm high at the bottom right; no window position or side published"),
    "AT": ("zone", "Österreichische Post, Richtig adressieren, 2020 (file of 2024): a window at least 90 x 35 mm, 5 mm quiet "
                   "zone around the address; no window position published, ÖNORM A 1080 not read"),
    "IE": ("zone", "An Post, Speed up your post, 2019: the address block 20 mm in from both sides, 20 mm clear at the bottom, "
                   "text 15 mm from the window's left edge and 5 mm from the others; no window position published"),
    "ES": ("zone", "Correos, Dimensiones y pesos de los envíos, the drawing of a normalised item (read 2026-10-09): the address "
                   "block at most 140 mm from the right edge, under the 74 x 40 mm franking zone and above the 15 mm bar-code "
                   "strip, as far right as possible, about 8 mm at the right edge kept clear; zone published, exact window "
                   "position not published"),
    "IT": ("zone", "Poste Italiane, Caratteristiche standard degli invii, Posta indescritta, version 3 of 3 March 2026, 1.1.3, "
                   "4.1.6 and 4.2.7: the address block inside 140 x 140 mm from the bottom right corner and 15 mm from the "
                   "edges, the window at the bottom right, 15 mm kept white left and right of the block and 5 mm above and "
                   "below; zone published, exact window position not published"),
    "PL": ("zone", "Poczta Polska, Zasady poprawnego adresowania i oznakowania przesyłek listowych (file of September 2025): "
                   "the address field at the bottom right, at least 40 mm from the top and 15 mm from the right and bottom "
                   "edges, at most 140 mm from the right edge; a window at least 15 mm from the right edge, the address "
                   "10 mm inside it and 5 mm inside its right edge; zone published, exact window position not published"),
}
COUNTRY_LAYOUT = {"US": "us", "CA": "ca", "GB": "uk", "AU": "au", "NO": "no", "DK": "dk", "FI": "fi",
                  "BE": "be", "NL": "nl", "AT": "at", "IE": "ie", "ES": "es", "IT": "it", "PL": "pl"}
COUNTRY_NAMES.update({"united states": "US", "usa": "US", "united states of america": "US", "canada": "CA",
                      "australia": "AU", "norge": "NO", "suomi": "FI", "new zealand": "NZ",
                      "españa": "ES", "espana": "ES", "italia": "IT", "polska": "PL", "portugal": "PT",
                      "alemania": "DE", "germania": "DE", "niemcy": "DE", "francia": "FR", "francja": "FR"})
# English names of the countries for the last line of an address abroad (UPU RL 123.3.3: in capitals).
COUNTRY_EN = {"US": "UNITED STATES", "CA": "CANADA", "GB": "UNITED KINGDOM", "AU": "AUSTRALIA", "NO": "NORWAY",
              "DK": "DENMARK", "FI": "FINLAND", "SE": "SWEDEN", "DE": "GERMANY", "AT": "AUSTRIA", "IE": "IRELAND",
              "FR": "FRANCE", "NL": "NETHERLANDS", "NZ": "NEW ZEALAND", "BE": "BELGIUM", "LU": "LUXEMBOURG",
              "CH": "SWITZERLAND", "IT": "ITALY", "ES": "SPAIN", "PL": "POLAND"}
# An Austrian sender writes the country in German, as the Post's own examples do (DEUTSCHLAND).
COUNTRY_DE = {"DE": "DEUTSCHLAND", "CH": "SCHWEIZ", "IT": "ITALIEN", "FR": "FRANKREICH", "NL": "NIEDERLANDE",
              "BE": "BELGIEN", "LU": "LUXEMBURG", "GB": "VEREINIGTES KÖNIGREICH", "IE": "IRLAND", "ES": "SPANIEN",
              "PL": "POLEN", "SE": "SCHWEDEN", "DK": "DÄNEMARK", "NO": "NORWEGEN", "FI": "FINNLAND", "US": "USA"}
# A Spanish, Italian or Polish sender writes the country in its own language, as Poste Italiane's examples
# (GERMANIA) and Poczta Polska's rule (the country's name in Polish) have it.
COUNTRY_ES = {"DE": "ALEMANIA", "FR": "FRANCIA", "IT": "ITALIA", "PT": "PORTUGAL", "GB": "REINO UNIDO", "IE": "IRLANDA",
              "NL": "PAÍSES BAJOS", "BE": "BÉLGICA", "AT": "AUSTRIA", "CH": "SUIZA", "PL": "POLONIA", "SE": "SUECIA",
              "DK": "DINAMARCA", "NO": "NORUEGA", "FI": "FINLANDIA", "US": "ESTADOS UNIDOS", "LU": "LUXEMBURGO"}
COUNTRY_IT = {"DE": "GERMANIA", "FR": "FRANCIA", "ES": "SPAGNA", "PT": "PORTOGALLO", "GB": "REGNO UNITO", "IE": "IRLANDA",
              "NL": "PAESI BASSI", "BE": "BELGIO", "AT": "AUSTRIA", "CH": "SVIZZERA", "PL": "POLONIA", "SE": "SVEZIA",
              "DK": "DANIMARCA", "NO": "NORVEGIA", "FI": "FINLANDIA", "US": "STATI UNITI", "LU": "LUSSEMBURGO"}
COUNTRY_PL = {"DE": "NIEMCY", "FR": "FRANCJA", "ES": "HISZPANIA", "IT": "WŁOCHY", "PT": "PORTUGALIA",
              "GB": "WIELKA BRYTANIA", "IE": "IRLANDIA", "NL": "HOLANDIA", "BE": "BELGIA", "AT": "AUSTRIA",
              "CH": "SZWAJCARIA", "SE": "SZWECJA", "DK": "DANIA", "NO": "NORWEGIA", "FI": "FINLANDIA",
              "US": "STANY ZJEDNOCZONE", "LU": "LUKSEMBURG", "CZ": "CZECHY", "SK": "SŁOWACJA", "LT": "LITWA"}
COUNTRY_OWN = {"AT": COUNTRY_DE, "ES": COUNTRY_ES, "IT": COUNTRY_IT, "PL": COUNTRY_PL}
EN_MARKET = {"US": "en-US", "CA": "en-CA", "AU": "en-AU", "GB": "en-GB", "IE": "en-IE"}
NEW_LOCALE = {"NO": "nb-NO", "FI": "fi-FI", "DK": "da-DK", "US": "en-US", "CA": "en-CA", "AU": "en-AU", "GB": "en-GB",
              "BE": "nl-BE", "NL": "nl-NL", "AT": "de-AT", "IE": "en-IE", "ES": "es-ES", "IT": "it-IT", "PL": "pl-PL"}


def belgian_language(postcode):
    """nl-BE or fr-BE for a Belgian postcode: Wallonia (1300-1499, 4000-7999) writes French, Flanders
    Dutch; Brussels (1000-1299) is bilingual and falls to Dutch unless the spec names the language."""
    digits = re.sub(r"\D", "", str(postcode or ""))
    n = int(digits) if len(digits) == 4 else 0
    return "fr-BE" if 1300 <= n <= 1499 or 4000 <= n <= 7999 else "nl-BE"


def letter_layout(spec):
    """(layout id, layout or None): the spec's own "layout", else the sender's country; None is DIN 5008 Form B."""
    named = str(spec.get("layout") or "").lower()
    if named in LAYOUTS:
        return named, LAYOUTS[named]
    if named.startswith("din"):
        return "din5008-b", None
    code = country_code((spec.get("sender") or {}).get("country"))
    lid = COUNTRY_LAYOUT.get(code)
    return (lid, LAYOUTS[lid]) if lid else ("din5008-b", None)


def letter_locale(spec):
    """(locale, why) for a letter. Every letter DIN 5008 already wrote keeps language()'s answer; English
    takes the sender's or else the recipient's English-speaking country, French is Canadian when Canada
    is either side, and Norwegian, Finnish and the new senders' countries have words of their own."""
    s_cc = country_code((spec.get("sender") or {}).get("country"))
    r_cc = country_code((spec.get("recipient") or {}).get("country"))
    named = str(spec.get("language") or (spec.get("recipient") or {}).get("language") or "").strip().lower()
    base = {"no": "nb", "nn": "nb", "nob": "nb"}.get(named.split("-")[0], named.split("-")[0])
    old = dict(spec, seller=spec.get("sender") or {}, buyer=spec.get("recipient") or {})
    if named:
        if named in ("en-us", "en-ca", "en-au", "en-gb", "fr-ca", "en-ie", "nl-nl", "nl-be", "fr-be", "de-at",
                     "es-es", "it-it", "pl-pl"):
            return named[:3] + named[3:].upper(), "the language %s named in the spec" % named
        if base == "en":
            for cc in (s_cc, r_cc):
                if cc in EN_MARKET:
                    return EN_MARKET[cc], "English, as written in %s" % cc
            return language(old)
        if base == "fr":
            if "CA" in (s_cc, r_cc):
                return "fr-CA", "the customer's language %s" % named
            belgian = s_cc == "BE" or (r_cc == "BE" and s_cc != "FR")
            return ("fr-BE" if belgian else "fr-FR"), "the customer's language %s" % named
        if base == "nl":
            belgian = s_cc == "BE" or (r_cc == "BE" and s_cc != "NL")
            return ("nl-BE" if belgian else "nl-NL"), "the customer's language %s" % named
        if base == "de" and s_cc == "AT":
            return "de-AT", "the customer's language %s, as Austria writes it" % named
        if base in ("es", "it", "pl"):
            return {"es": "es-ES", "it": "it-IT", "pl": "pl-PL"}[base], "the customer's language %s" % named
        if base == "nb":
            return "nb-NO", "the customer's language %s" % named
        if base == "fi":
            return "fi-FI", "the customer's language %s" % named
        return language(old)
    if s_cc == "BE":
        loc = belgian_language((spec.get("sender") or {}).get("postcode"))
        return loc, "the sender's Belgian postcode (%s); name the language to write the other one" % (
            "Wallonia" if loc == "fr-BE" else "Flanders or Brussels")
    if s_cc in NEW_LOCALE:
        return NEW_LOCALE[s_cc], "the sender's country %s" % s_cc
    return language(old)


def paper_size(layout):
    """The sheet in mm for a layout, from PAPER_MM (A4 for DIN 5008)."""
    return tuple(PAPER_MM[layout["paper"]]) if layout else PAPER_MM["A4"]


# ---- the Form B sheet on a country layout -------------------------------------------------------------
# An invoice and a trade document are their sender's letters too, so each sits where the sender's country
# puts a letter: sheet_html()'s page moved onto the layout's margins and envelope window. The invoice page
# has done it since wave 8 (skills/e-invoice/page/build_page.py, layout_css and on_layout); the same
# arithmetic stands here so that every document printed on the sheet shares it and no builder restates a
# layout's numbers. A test in skills/trade-documents holds the two to the same CSS.

LAYOUT_GAP = 3      # mm between the information block and the window, beyond what the window keeps clear


def layout_info(layout):
    """(x, y, width, how): where a document on this layout puts its information block. how is "left" (left
    of a window on the right, level with the window's top: Belgium, Spain, Italy, Poland), "above" (at the
    top right, y being where the block ENDS, above the window: the United States and Canada, whose #10
    window leaves no room beside it) or "beside" (right of a window on the left, from 125 mm across, level
    with the window's top). The block ends on the text's right margin, or before the window."""
    g = GEOMETRY
    wx, wy, ww, _wh = layout["window"]
    clear = layout.get("clear") or 0
    page_w = PAPER_MM[layout["paper"]][0]
    if wx + ww / 2 > page_w / 2:
        return layout["left"], wy, wx - clear - LAYOUT_GAP - layout["left"], "left"
    if layout.get("info") == "above":
        return page_w - layout["right"] - g["info_w"], wy - clear - LAYOUT_GAP, g["info_w"], "above"
    x = max(g["info_x"], wx + ww + clear + LAYOUT_GAP)
    return x, wy, min(g["info_w"], page_w - layout["right"] - x), "beside"


def layout_address(layout):
    """(x, y, width, height, line): the address's first line inside the layout's window, the room it has
    there (to the edge of what the window keeps clear) and the height of one of its lines, all in mm."""
    wx, wy, _ww, _wh = layout["window"]
    clear = layout.get("clear") or 0
    ax, ay = layout.get("address_at") or (wx + clear, wy + clear)
    box = window_box(layout)
    return ax, ay, min(box[2], PAPER_MM[layout["paper"]][0] - 4) - ax, box[3] - ay, layout.get("line") or ADDRESS_LINE


def layout_css(layout, grid=INFO_GRID):
    """CSS that moves sheet_html()'s page onto a window layout: the layout's margins, the address at its
    first line inside the window in the layout's own line height and nothing else in the window (no return
    line), and the information block where layout_info() puts it. grid: the block's own column rules (an
    invoice page groups its block and brings its own). Every number is the layout's."""
    r = lambda v: round(v, 2)  # noqa: E731
    left, right = layout["left"], layout["right"]
    ax, ay, aw, ah, line = layout_address(layout)
    ix, iy, iw, how = layout_info(layout)
    extra = ""
    if how == "above":
        page_w = PAPER_MM[layout["paper"]][0]
        extra = ".info{transform:translateY(-100%%)}.head{right:%smm}" % round(page_w - ix + LAYOUT_GAP, 2)
    return ("\n/* layout: %s */\n.head{left:%smm;right:%smm}.body{padding-left:%smm;padding-right:%smm}"
            "footer{left:%smm;right:%smm}.field{left:%smm;top:%smm;width:%smm;padding-left:0}.return{display:none}"
            ".address{height:auto;max-height:%smm;overflow:hidden;line-height:%smm}.info{left:%smm;top:%smm;width:%smm}"
            "%s%s\n") % (
        layout["name"], r(left), r(right), r(left), r(right), r(left), r(right), r(ax), r(ay), r(aw),
        r(ah), line, r(ix), r(iy), r(iw), grid, extra)


def on_layout(html, layout, grid=INFO_GRID):
    """sheet_html()'s page on a window layout. The heading follows the lower of the window and the
    information block (the sheet's own script, told where this layout's window ends instead of Form B's
    address field); a block above the window does not push it down. The page names its layout."""
    html = html.replace("</style>", layout_css(layout, grid) + "</style>", 1)
    window_end = round(layout["window"][1] + layout["window"][3], 2)
    above = layout_info(layout)[3] == "above"
    html = re.sub(r"Math\.max\([\d.]+\*mm,\(info\.offsetTop\+info\.offsetHeight\)\)",
                  ("(%s*mm)" % window_end) if above else
                  "Math.max(%s*mm,(info.offsetTop+info.offsetHeight))" % window_end, html, 1)
    name = str(layout["name"]).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r'<meta name="layout" content="[^"]*">', '<meta name="layout" content="%s">' % name, html, 1)


def town_line(party):
    """The town line of an address in running print (a company's own address in a footer, a letterhead, a
    return line, a delivery line): one form per country, for every pack. The town, the state or province
    when the data gives one, then the postcode in the United States, Canada, Australia, the United Kingdom
    and Ireland, in the order their post offices write them (Portland OR 97204, Brisbane QLD 4000, Leeds
    LS1 4BR); the postcode first elsewhere (8000 Aarhus C), with Italy's province after the town in
    brackets (20121 Milano (MI)) and a Spanish province that is not the town's own name the same way
    (08201 Sabadell (Barcelona)). Ordinary case and one line: the capitals, the double spaces and the line
    breaks of postal_lines are for the address a post office's machines read, not for a company's imprint."""
    party = party or {}
    cc = country_code(party.get("country"))
    town, code = str(party.get("city") or "").strip(), str(party.get("postcode") or "").strip()
    region = str(party.get("state") or party.get("province") or "").strip()
    if cc in ("GB", "IE") and not region:
        region = str(party.get("county") or "").strip()
    if region and re.search(r"(^|[\s,(])%s\)?$" % re.escape(region), town, re.I):
        region = ""                    # the town already carries it (Austin, TX; Madrid in Madrid)
    if cc in ("US", "CA", "AU", "GB", "IE"):
        return " ".join(x for x in (town, region, code) if x)
    if cc in ("IT", "ES") and region:
        return " ".join(x for x in (code, town, "(%s)" % (region.upper() if cc == "IT" else region)) if x)
    return " ".join(x for x in (code, town) if x)


def country_line(party, other_country=None):
    """The country under an address: none at home; the country's name in capitals when the paper goes to
    another country (as the other side's post writes it where the tables have it, else in English); a
    country the tables do not know as it was written, in capitals."""
    party = party or {}
    cc, home = country_code(party.get("country")), country_code(other_country)
    if cc and home and cc != home:
        return COUNTRY_OWN.get(home, {}).get(cc) or COUNTRY_EN.get(cc, str(party.get("country") or "").upper())
    if not cc and party.get("country"):
        return str(party["country"]).upper()
    return None


def own_address(party, to_country=None):
    """A company's own address as the first column of its footer, the same on its letter, its invoice and
    its trade document: the name, the street (in Italy the building above it), a second line and a locality
    when the data gives them, town_line, and country_line when the paper goes abroad. One company, one
    footer: every builder that prints a sender calls this, none writes the lines itself."""
    p = party or {}
    if country_code(p.get("country")) == "IT":
        lines = [p.get("name"), p.get("building") or p.get("street2"), p.get("street")]
    else:
        lines = [p.get("name"), p.get("street"), p.get("street2")]
    lines += [p.get("locality"), town_line(p), country_line(p, to_country)]
    return [str(x) for x in lines if x]


def postal_lines(recipient, sender_country=None):
    """The address as the recipient's post office reads it, one string per line."""
    r = recipient
    cc = country_code(r.get("country"))
    home = country_code(sender_country)
    lines = [r.get("name")] + ([r["attention"]] if r.get("attention") else [])
    if cc == "IT":
        # Poste Italiane: the building (stair, floor, flat) on its own line above the street.
        lines += [r.get("building") or r.get("street2"), r.get("street")]
    else:
        lines += [r.get("street"), r.get("street2")]
    city, pc, region = (r.get("city") or "").strip(), (r.get("postcode") or "").strip(), (r.get("state") or r.get("province") or "").strip()
    if cc in ("US", "CA", "AU"):
        # USPS Pub. 28 s.224, Canada Post, Australia Post: town, state or province and postcode on the
        # last line, in capitals, two spaces before the postcode (and after the locality in Australia).
        gap = "  " if cc == "AU" else " "
        place = (city.upper() + (gap + region.upper() if region else "") + ("  " + pc.upper() if pc else "")).strip()
        lines.append(place)
    elif cc == "GB":
        # Royal Mail: the post town in capitals on its own line, the postcode alone on the last line.
        lines += [r.get("locality"), city.upper(), pc.upper()]
    elif cc == "IE":
        # An Post: every element on its own line, the post town, then the county (or the Dublin postal
        # district as the town), the Eircode alone on the last line.
        lines += [r.get("locality"), city, r.get("county"), pc.upper()]
    elif cc in ("NO", "FI", "BE"):
        # Posten, Posti, bpost: the postcode, then the town in capitals.
        lines.append(" ".join(x for x in (pc, city.upper()) if x))
    elif cc == "NL":
        # PostNL: 1234 AB, two spaces, the town in capitals.
        m = re.match(r"^(\d{4})\s*([A-Za-z]{2})$", pc)
        pc = "%s %s" % (m.group(1), m.group(2).upper()) if m else pc
        lines.append("  ".join(x for x in (pc, city.upper()) if x))
    elif cc == "ES":
        # Correos (UPU sheet ESP): the postcode left of the locality, the locality in capitals, the province
        # on a line of its own.
        lines.append(" ".join(x for x in (pc, city.upper()) if x))
        lines.append(region.upper())
    elif cc == "IT":
        # Poste Italiane: the CAP, the locality and the province's two letters on one line.
        lines.append(" ".join(x for x in (pc, city, region) if x))
    elif cc == "PL":
        # Poczta Polska: the postcode (XX-XXX) left of the locality, the locality in capitals.
        m = re.match(r"^(\d{2})[\s\-–]?(\d{3})$", pc)
        lines.append(" ".join(x for x in ("%s-%s" % m.groups() if m else pc, city.upper()) if x))
    elif home in ("AT", "NL", "IT", "PL") and cc and cc != home:
        # Österreichische Post, PostNL, Poste Italiane and Poczta Polska: abroad, the town in capitals
        # (PostNL: two spaces before it).
        lines.append(("  " if home == "NL" else " ").join(x for x in (pc, city.upper()) if x))
    else:
        lines.append(" ".join(x for x in (pc, city) if x))
    lines.append(country_line(r, sender_country))
    out = [x for x in lines if x]
    if cc == "US":
        # Publication 28: capitals and no punctuation on the lines the machines read.
        out = out[:1] + [re.sub(r"[.,]", "", x).upper() for x in out[1:]]
    if cc == "IE":
        # An Post: no punctuation, commas included, in the address (Co Mayo, not Co. Mayo).
        out = out[:1] + [re.sub(r"[.,]", "", x) for x in out[1:]]
    if "IT" in (cc, home) and len(out) > 2:
        # Poste Italiane, Standard di composizione degli indirizzi: the street and the locality lines in
        # capitals with no punctuation (three lines abroad, the foreign state last).
        n = 3 if cc != home and cc and home else 2
        out = out[:-n] + [re.sub(r"\s+", " ", re.sub(r"[.,;:()]", " ", x)).strip().upper() for x in out[-n:]]
    return out


def print_letter(html, pdf, paper):
    """Print a letter on its paper (A4 or Letter) through print_pdf."""
    return print_pdf(html, pdf, paper=paper)
