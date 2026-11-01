#!/usr/bin/env python3
"""What an invoice needs in Norway, Denmark, Finland, the United Kingdom, Australia, Canada and the United
States, from each country's own published rules, and which file each one gets.

    NO  bokføringsforskriften (FOR-2004-12-01-1558) §§ 5-1-1 to 5-1-5: number and date, the parties
        (seller's name and organisasjonsnummer followed by MVA when VAT-registered, "Foretaksregisteret"
        for an AS, ASA or a branch of a foreign company, § 5-1-2), what is supplied, the time and place of
        delivery, the price and the due date, VAT stated in Norwegian kroner, "Omvendt avgiftsplikt –
        Merverdiavgift ikke beregnet" for a reverse charge (§ 5-1-1 nr. 7). EHF, Peppol BIS Billing 3.0
        with the Norwegian rules NO-R-001 and NO-R-002. Norwegian law is free of copyright
        (åndsverkloven § 14).
    DK  momsbekendtgørelsen § 58, stk. 1 (fuld faktura): date, number, the seller's VAT number (CVR or
        SE), the parties' names and addresses, quantity and kind, the delivery date when it differs, the
        taxable amount and unit price without VAT, the rate, the VAT; § 58, stk. 2 a credit note that
        refers to the invoice. Peppol BIS 3.0 with the Danish rules DK-R-*, which NemHandel receives
        beside OIOUBL 2.1 (OIOUBL 3.0 was dropped in 2026 for one Peppol-based "Nemhandel BIS 4" from
        2028-2029, Erhvervsstyrelsen's strategy of 5 March 2026). Danish law is free of copyright
        (ophavsretsloven § 9).
    FI  arvonlisäverolaki (1501/1993) 209 e §: date, a running number, the seller's VAT identifier,
        the buyer's in a reverse charge, the parties' names and addresses, quantity and kind, the
        delivery date, the taxable amount per rate, the unit price, the rate, the VAT, the exemption's
        ground, "Käännetty verovelvollisuus", a reference to the original in a credit note; the VAT in
        euros. Peppol BIS 3.0, or Finvoice 3.0 (Finanssiala: "All materials on this page are freely
        usable"). Finnish law is free of copyright (tekijänoikeuslaki 9 §).
    GB  HMRC VAT Notice 700/21 section 4.1 (Open Government Licence v3.0): a sequential number, the
        time of supply, the date of issue, the supplier's name, address and VAT registration number,
        the customer's name and address, a description, and for each description the quantity, the
        unit price, the rate and the amount excluding VAT, the total excluding VAT, the rate of any cash
        discount, the total VAT in sterling. Peppol BIS 3.0 where the buyer takes it.
    AU  A New Tax System (Goods and Services Tax) Act 1999 s 29-70 and the GST Regulations 2019
        s 29-70.01 (legislation.gov.au, CC BY 4.0): a document intended to be a tax invoice, the
        supplier's identity and ABN, the date, what is sold, the GST (or that the price includes it) and
        the extent each sale is taxable; from A$1,000 the buyer's identity or ABN. A credit is an
        adjustment note (s 29-75). Page only: Peppol PINT A-NZ is not built here.
    CA  Input Tax Credit Information (GST/HST) Regulations, SOR/91-45, s. 3 (Justice Laws; reproduced
        under the Reproduction of Federal Law Order): the supplier's name and the date, the total;
        from $100 the GST/HST registration number and the tax; from $500 the buyer's name, the terms
        of payment and a description of each supply. Page only.
    US  No federal invoice standard and no VAT. Sales tax is a state and local tax; the page states
        each jurisdiction's tax on its own line. Page only; nothing here is a "US standard".

Wave 8, Belgium, the Netherlands, Austria and Ireland (the legal texts, their versions and licences are in
the pack's guidelines; each one is restated here, never copied):

    BE  Royal Decree no. 1 of 29 December 1992 (VAT), art. 5 § 1: date and number (1°), the supplier's
        and the customer's names, addresses and VAT numbers (2°, 3°), the date of supply (5°), what is
        supplied (6°), the taxable amount per rate, the unit price and discounts (8°), the rate and the VAT
        (9°), one fixed mention for a reverse charge in place of the rates and the VAT, "Autoliquidation"
        in the French text and "Btw verlegd" in the Dutch (9°bis), the exemption's ground (10°); a
        correcting document, the credit note, refers to the invoice it corrects (art. 12 § 3). The Code
        of companies and associations art. 2:20 adds, on invoices too, the legal form, the seat, the
        enterprise number and RPM/RPR with the court of the seat; the enterprise number is ten digits
        (Royal Decree of 24 June 2003 art. 3) whose last two are 97 less the first eight modulo 97 (the
        check PEPPOL-COMMON-R043 runs). Structured B2B e-invoices are mandatory from 1 January 2026 (Law
        of 6 February 2024, VAT Code art. 53 § 2bis); the Royal Decree of 8 July 2025 added the rule as
        art. 13ter (EN 16931 in Peppol BIS UBL, over the Peppol network) and left the particulars of
        art. 5 where they were. The enterprise number goes under scheme 0208. The page is in the
        language of the seller's region (be_region_locale). In Flanders that is Dutch: the decree of
        19 July 1973 art. 5 § 1 makes Dutch the language of a firm's legally required documents, and
        § 2/1 (in force 11 August 2017) lets an invoice to a customer in another EU or EEA state carry a
        second valid version in an official language of the EU or EEA that all parties understand, so a
        customer in Belgium gets Dutch whatever the order names and a customer abroad gets the named
        language beside the Dutch invoice. French in Wallonia and Brussels unless the order names Dutch,
        German in the German-speaking Community. Justel carries no German text of 9°bis, so a German
        page writes the mention of VAT Directive Art. 226(11a) in German, "Steuerschuldnerschaft des
        Leistungsempfängers", the words FPS Finance's German pages use.
    NL  Wet op de omzetbelasting 1968 art. 35a: date, number, the supplier's btw-id, the customer's for a
        reverse charge ("btw verlegd") or an intra-EU supply, both parties' names and addresses, quantity
        and kind, the date of supply, the taxable amount per rate, the unit price, the rate, the VAT in
        euro (lid 4); a document that changes an invoice refers to it specifically and unambiguously
        (art. 34f); the KvK number on outgoing letters, orders, invoices and offers (Handelsregisterwet
        2007 art. 27 lid 1). Peppol BIS 3.0 with the Dutch rules NL-R-001 to NL-R-009 (KvK
        under 0106), or SI-UBL 2.0, the NLCIUS, with "syntax": "si-ubl".
    AT  UStG 1994 § 11 Abs. 1 Z 3 lit. a to i: the supplier's and the recipient's names and addresses
        (lit. a, b; the recipient's UID-Nummer when the total exceeds 10 000 euros, lit. b), quantity and
        kind (c), the date or period of supply (d), the price per rate (e), the VAT, in euro too when the
        invoice is in another currency (f), the date (g), a running number (h), the supplier's
        UID-Nummer (i); for a reverse charge the recipient's UID and a note of the recipient's tax
        liability, in no prescribed words (Abs. 1a: "auf die Steuerschuldnerschaft des
        Leistungsempfängers hinzuweisen"; the page writes those words); up to 400 euros a small invoice
        (Abs. 6); "Gutschrift" is self-billing (Abs. 7, 8), so a correcting credit note is a
        Rechnungskorrektur. UGB § 14's Firmenbuch details are for letters and order forms; invoices are
        not named, so they print when given. The federal e-invoicing decree is the e-Rechnungsverordnung
        (BGBl. II Nr. 505/2012): § 5 has invoices come in the formats the ministry sets, which on
        erechnung.gv.at are ebInterface and UBL (Peppol BIS), not CII, through the USP or the Peppol
        network, and § 4 asks for the order reference. So: Peppol BIS 3.0, or ebInterface 6.1
        (AUSTRIAPRO) with "syntax": "ebinterface".
    IE  Value-Added Tax Consolidation Act 2010 s. 66 and the Value-Added Tax Regulations 2010 (S.I. 639
        of 2010) reg. 20(2): date and number, the supplier's name, address and VAT number, the customer's
        name and address, quantity and kind, the date of supply, the unit price and the amount per rate,
        the rate and the VAT; for a reverse charge the customer's VAT number and "an indication that a
        reverse charge applies" (reg. 20(2)(e): the law fixes no words, so any clear note passes), for
        goods to another member state the customer's VAT number and an indication of an intra-Community
        supply (reg. 20(2)(f)); a credit note states both parties' registration numbers, its reason and
        the invoice it refers to (s. 67, reg. 20(5)(d), (f)). Revenue has no invoice manual: its guidance
        is two pages, "What information is required on a VAT invoice?" and "What information is
        required on a VAT credit note?". Revenue publishes no check-letter rule for the VAT number, so a
        mismatch warns. Peppol BIS 3.0, which Irish public buyers take (EN 16931 since 2019). Revenue's
        roadmap brings in structured e-invoices for domestic B2B sales in phases: large corporates in
        November 2028, then in November 2029 the same domestic rule for every VAT-registered business
        that also trades with other EU states (not cross-border e-invoicing, which comes with the EU's
        ViDA rules in July 2030).

Wave 9, Spain, Italy and Poland: each has a national e-invoice file, written beside the page (the texts,
their versions and licences are in the pack's guidelines; each is restated here, never copied):

    ES  Reglamento por el que se regulan las obligaciones de facturación (Real Decreto 1619/2012) art. 6.1:
        number and, where there is one, series (a), the date (b), both parties' full names (c), the seller's
        NIF and the recipient's when the supply is made in Spain by a seller established there, in a
        reverse charge and in an exempt intra-EU supply (d), both addresses (e), what is supplied with the
        unit price without tax and any discount (f), the rate (g), the tax, stated apart (h), the date of the
        supply when it differs (i), a reference to the exemption (j), and for a reverse charge the mention
        «inversión del sujeto pasivo» (m). A rectifying invoice (art. 15) has a series of its own (art. 6.1 a
        2.º), names the invoice it rectifies (15.4) and states the rectification itself, whatever its sign
        (15.5): the page and the file write a credit as minus amounts. Facturae 3.2.2 is the state's XML;
        invoices to public bodies go through a general entry point such as FACe in that format with an
        advanced electronic signature (Ley 25/2013 art. 4, 5 and disposición adicional segunda). This pack
        writes the unsigned file and never signs it. Invoicing software must meet Real Decreto 1007/2023
        (VERI*FACTU) before 1 January 2027 for corporate-tax payers and before 1 July 2027 for the other
        obligors (disposición final cuarta, as amended by Real Decreto-ley 15/2025); the QR code and the
        words «VERI*FACTU» are for invoices issued by such a system (Real Decreto 1619/2012 art. 6.5). This
        pack keeps no billing records, chains none and sends nothing to the tax agency.
    IT  DPR 633/1972 art. 21 comma 2 (until 31 December 2026; from 1 January 2027 the Testo unico IVA,
        D.Lgs. 19 gennaio 2026 n. 10, art. 72): the date (a), a number (b), both parties' names and
        addresses (c, e), the seller's partita IVA (d), the customer's partita IVA or, for a resident who
        does not act as a business, the codice fiscale (f), what is supplied (g), the date of the supply
        when it differs (g-bis), the amounts (h), the rate, the tax and the taxable amount (l); in place of
        the tax «inversione contabile» for a reverse charge (art. 17, art. 21 comma 6-bis; art. 64 and 72 of
        the Testo unico), «operazione non imponibile», «operazione esente» and the like (comma 6). A credit
        note is a variation under art. 26 (art. 92). Invoices between parties resident or established in
        Italy are issued only as e-invoices through the Sistema di Interscambio in the FatturaPA format
        (D.Lgs. 127/2015 art. 1 comma 3; art. 77): FPR12 to a private party, FPA12 to a public body, TD01 an
        invoice, TD04 a credit note. An e-invoice that owes stamp duty says it was paid under the decree
        of 17 June 2014 (art. 6 comma 2). This pack writes the file and sends nothing; the page is a
        courtesy copy.
    PL  Ustawa o podatku od towarów i usług art. 106e ust. 1: the date (1), a number (2), both parties'
        names and addresses (3), the seller's and the buyer's tax numbers (4, 5), the date of the supply
        when it differs (6), what is supplied, its measure and quantity (7, 8), the net unit price (9),
        discounts (10), the net value (11), the rate (12), net value and tax per rate (13, 14), the total
        (15), „metoda kasowa” (16), „odwrotne obciążenie” (18), „mechanizm podzielonej płatności” on an
        invoice over 15 000 zł for goods or services of annex 15 supplied to a taxpayer (18a), the ground
        of an exemption (19). A correcting invoice (art. 106j ust. 2) carries its own number and date, the
        KSeF number of the invoice it corrects where one was given, that invoice's data of pkt 1-5 and the
        correction per rate; the words „FAKTURA KORYGUJĄCA” and the reason are optional (ust. 2a).
        Taxpayers issue structured invoices in the Krajowy System e-Faktur (art. 106ga) in the logical
        structure FA(3): from 1 February 2026 those whose 2024 sales passed 200 000 000 zł, from 1 April
        2026 the others (art. 145l), and until 31 December 2026 a seller whose invoices in a month total
        no more than 10 000 zł may still issue outside it (art. 145m). A structured invoice used outside
        KSeF carries the code that gives access to it there (art. 106gb ust. 5). This pack writes the
        FA(3) file and the page; it sends nothing to KSeF, so the page has no KSeF number and no code.

Standard library only.
"""
import re
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_checks"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
import doc_amounts  # noqa: E402
import einvoice_ids as ids  # noqa: E402
import einvoice_particulars as particulars  # noqa: E402

# The file each seller country gets when the spec names none: Peppol BIS Billing 3.0 in UBL for the
# Nordic and British sellers whose buyers take it, the readable page alone where EN 16931 does not apply.
UBL = ("NO", "DK", "FI", "GB", "BE", "NL", "AT", "IE")
PAGE_ONLY = ("AU", "CA", "US", "NZ")
# Wave 9: the national e-invoice file each of these sellers gets beside the page.
NATIONAL = {"ES": "facturae", "IT": "fatturapa", "PL": "ksef"}
NATIONAL_NAMES = {"facturae": "Facturae 3.2.2", "fatturapa": "FatturaPA 1.2.3", "ksef": "KSeF FA(3)"}
# The currency the VAT must be stated in: NOK in Norway (§ 5-1-1 nr. 6), sterling in the UK (Notice
# 700/21 4.1), euros in Finland; the EU members outside the euro (VAT Directive Art. 230) as before.
NATIONAL_CURRENCY = {"SE": "SEK", "DK": "DKK", "PL": "PLN", "CZ": "CZK", "HU": "HUF", "RO": "RON",
                     "NO": "NOK", "GB": "GBP"}
# The Peppol electronic address scheme (EAS) each country's business number is read under.
EAS = {"NO": "0192", "DK": "0184", "FI": "0216", "GB": "9932", "SE": "0007", "AU": "0151", "BE": "0208",
       "NL": "0106", "AT": "9914", "IE": "9935", "ES": "9920", "IT": "0211", "PL": "9945"}
# The legal registration scheme (ICD) of the seller's and buyer's company number (BT-30, BT-47).
ICD = {"NO": "0192", "DK": "0184", "FI": "0212", "BE": "0208", "NL": "0106"}
NO_FORETAK = {"AS", "ASA", "NUF"}
# The words of the Norwegian reverse-charge mark, bokføringsforskriften § 5-1-1 nr. 7.
NO_REVERSE = "Omvendt avgiftsplikt – Merverdiavgift ikke beregnet"
DK_PAYMENT_CODES = ("1", "10", "31", "42", "48", "49", "50", "58", "59", "93", "97")
AU_BUYER_THRESHOLD = Decimal("1000")
CA_REGISTRATION_THRESHOLD = Decimal("100")
CA_BUYER_THRESHOLD = Decimal("500")
# Austria: the recipient's UID-Nummer from a total over 10 000 euros (UStG § 11 Abs. 1 Z 3 lit. b).
AT_BUYER_UID_THRESHOLD = Decimal("10000")
# The reverse-charge mention each page writes. Belgium fixes one mention per language (Royal Decree no. 1
# art. 5 § 1 9°bis: "Btw verlegd", "Autoliquidation"; in German the mention of VAT Directive Art. 226(11a))
# and the Netherlands fixes "btw verlegd" (art. 35a lid 1 m). Austria and Ireland ask for a note and fix no
# words: the page writes the statute's own (UStG § 11 Abs. 1a; VAT Regulations 2010 reg. 20(2)(e)).
REVERSE = {"nl-BE": "Btw verlegd", "fr-BE": "Autoliquidation", "de-BE": "Steuerschuldnerschaft des Leistungsempfängers",
           "nl-NL": "Btw verlegd", "de-AT": "Steuerschuldnerschaft des Leistungsempfängers",
           "en-IE": "Reverse charge applies",
           # Wave 9: the words each law fixes (Real Decreto 1619/2012 art. 6.1 m; DPR 633/1972 art. 17 and
           # art. 21 comma 6-bis; ustawa o VAT art. 106e ust. 1 pkt 18).
           "es-ES": "Inversión del sujeto pasivo", "it-IT": "Inversione contabile", "pl-PL": "Odwrotne obciążenie"}
# Poland: the invoice total over which art. 106e ust. 1 pkt 18a may ask for „mechanizm podzielonej płatności”.
PL_SPLIT_THRESHOLD = Decimal("15000")
PL_SPLIT = "Mechanizm podzielonej płatności"
PL_CASH = "Metoda kasowa"
IT_SPLIT = "Scissione dei pagamenti"
IT_STAMP = "Imposta di bollo assolta in modo virtuale ai sensi del decreto MEF 17 giugno 2014"
# Company forms of the four countries, read off the end of a name when the order gives no legal_form.
W8_FORMS = re.compile(r"\b(B\.?V\.?|N\.?V\.?|SRL|SA|SPRL|BVBA|CommV|VOF|GmbH|GesmbH|AG|KG|OG|DAC|CLG|UC|PLC|Ltd|Limited)\.?$")
# Payment means a Dutch seller may name for a Dutch buyer (Peppol NL-R-008, cited).
NL_PAYMENT_CODES = ("30", "48", "49", "57", "58", "59")


def country(p):
    return str((p or {}).get("country") or "").strip().upper()


def seller_country(spec):
    return country(spec.get("seller"))


def syntax_of(spec):
    """cii (EN 16931 CII, Factur-X), ubl (Peppol BIS Billing 3.0), finvoice (Finvoice 3.0) or none."""
    named = str(spec.get("syntax") or "").strip().lower()
    if named in ("cii", "ubl", "finvoice", "ebinterface", "none", "facturae", "fatturapa", "ksef"):
        return named
    if named in ("facturae 3.2.2", "face"):
        return "facturae"
    if named in ("fpr12", "fpa12", "fattura", "sdi", "fatturapa 1.2.3"):
        return "fatturapa"
    if named in ("fa3", "fa(3)", "fa (3)", "fa", "ksef fa(3)"):
        return "ksef"
    if named in ("ebi", "ebinterface 6.1"):
        return "ebinterface"
    if named in ("si-ubl", "siubl", "nlcius", "si-ubl 2.0"):
        return "si-ubl"
    if named in ("peppol", "ehf", "peppol-bis"):
        return "ubl"
    if spec.get("xrechnung"):
        return "cii"
    c = seller_country(spec)
    if c in UBL:
        return "ubl"
    if c in PAGE_ONLY:
        return "none"
    return NATIONAL.get(c, "cii")


def legal_form(p):
    form = str((p or {}).get("legal_form") or "").strip()
    if form:
        return form
    m = re.search(r"\b(AS|ASA|NUF|A/S|ApS|IVS|Oy|Oyj|Ltd|Limited|PLC|LLP|Pty Ltd|Inc\.?|LLC|Corp\.?)$",
                  str((p or {}).get("name") or "").strip())
    return m.group(1) if m else ""


def org_number(p, c=None):
    """The party's own business number in its country: organisasjonsnummer, CVR, Y-tunnus, ABN."""
    p = p or {}
    c = c or country(p)
    raw = {"NO": p.get("org_number"), "DK": p.get("cvr"), "FI": p.get("business_id"),
           "AU": p.get("abn"), "BE": p.get("enterprise_number") or p.get("register_number"),
           "NL": p.get("kvk") or p.get("register_number")}.get(c)
    return str(raw).strip() if raw not in (None, "") else ""



# Each country's own business-number field, as org_number() reads it. Another country's party never has it read:
# a Swedish buyer's org.nr written as "org_number", Norway's organisasjonsnummer, printed on no page and in no XML,
# and the reply said the page had no place for it (timed command run c01, 2026-10-25).
OWN_NUMBER = {"org_number": "NO", "cvr": "DK", "business_id": "FI", "abn": "AU", "kvk": "NL", "enterprise_number": "BE"}


def misplaced_numbers(spec):
    """Why a party's business number stands in another country's field, one line each: the build stops on them."""
    found = []
    for role in ("seller", "buyer", "payee", "tax_representative"):
        p = (spec or {}).get(role)
        c = country(p) if isinstance(p, dict) else ""
        if not c:
            continue
        for key, home in OWN_NUMBER.items():
            if c != home and p.get(key) not in (None, ""):
                found.append('%s.%s is %s\'s own number field, and a %s party\'s page and XML never read it: put the '
                             'number in %s.register_number' % (role, key, home, c, role))
    return found

def vat_id(p):
    """The VAT identifier as EN 16931 carries it (BT-31, BT-48): what the spec gives, else the one a
    Finnish or Danish business number makes by definition (FI + the Y-tunnus digits; DK + the CVR)."""
    p = p or {}
    if p.get("vat_id"):
        return str(p["vat_id"]).replace(" ", "").upper()
    c = country(p)
    if c == "FI" and ids.fi_ytunnus_ok(p.get("business_id")):
        return ids.fi_vat_of(p["business_id"])
    if c == "DK" and ids.dk_cvr_ok(p.get("cvr")):
        return "DK" + ids.digits(p["cvr"])
    if c == "BE" and ids.be_enterprise_ok(org_number(p, "BE")):
        return "BE" + ids.be_enterprise_digits(org_number(p, "BE"))
    return ""


def endpoint(spec, role):
    """(scheme, id, why) of a party's Peppol address (BT-34, BT-49): what the spec gives, else its
    business number under its country's scheme. why is None when the spec gave it."""
    p = spec.get(role) or {}
    raw = p.get("electronic_address")
    if isinstance(raw, dict) and raw.get("id"):
        return str(raw.get("scheme") or ("EM" if "@" in str(raw["id"]) else "")), str(raw["id"]), None
    if isinstance(raw, str) and raw.strip():
        m = re.fullmatch(r"(\d{4}):(\S+)", raw.strip())
        if m:
            return m.group(1), m.group(2), None
        if "@" in raw:
            return "EM", raw.strip(), None
        return "", raw.strip(), None
    c = country(p)
    num = ids.digits(org_number(p, c))
    if c == "NO" and len(num) == 9:
        return "0192", num, "its organisasjonsnummer under scheme 0192"
    if c == "DK" and len(num) == 8:
        return "0184", num, "its CVR-nummer under scheme 0184"
    if c == "FI" and len(num) == 8:
        return "0216", "0037" + num, "its OVT code 0037%s under scheme 0216" % num
    if c == "GB" and vat_id(p):
        return "9932", vat_id(p), "its VAT registration number under scheme 9932"
    if c == "SE" and p.get("register_number"):
        return "0007", ids.digits(p["register_number"]), "its organisationsnummer under scheme 0007"
    if c == "BE" and ids.be_enterprise_ok(org_number(p, "BE")):
        return "0208", ids.be_enterprise_digits(org_number(p, "BE")), "its enterprise number under scheme 0208"
    if c == "NL" and ids.nl_kvk_ok(org_number(p, "NL")):
        return "0106", ids.digits(org_number(p, "NL")), "its KvK number under scheme 0106"
    if c == "AT" and vat_id(p):
        return "9914", vat_id(p), "its UID-Nummer under scheme 9914"
    if c == "IE" and vat_id(p):
        return "9935", vat_id(p), "its VAT number under scheme 9935"
    if c == "ES" and ids.es_nif_form(p.get("vat_id")):
        return "9920", "ES" + ids.es_nif(p["vat_id"]), "its NIF under scheme 9920"
    if c == "IT" and ids.it_piva_form(p.get("vat_id")):
        return "0211", "IT" + ids.it_piva(p["vat_id"]), "its partita IVA under scheme 0211"
    if c == "PL" and ids.pl_nip_form(p.get("vat_id")):
        return "9945", "PL" + ids.pl_nip(p["vat_id"]), "its NIP under scheme 9945"
    return None, None, None


def r2(x):
    return Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def line_net(l):
    return doc_amounts.line_amounts(l)["net"]


def taxable(l):
    """A line under a sales-tax list (Canada, the United States) is taxable unless it says otherwise."""
    v = l.get("taxable")
    return True if v is None else bool(v) and str(v).lower() not in ("false", "no", "0", "exempt")


def sales_taxes(spec):
    """[(name, rate, base, amount)] for the taxes a Canadian or US invoice lists: each tax once, on the
    sum of the taxable lines' nets, rounded half up."""
    base = sum((line_net(l) for l in spec.get("lines") or [] if taxable(l)), Decimal(0))
    out = []
    for t in spec.get("taxes") or []:
        rate = Decimal(str(t.get("rate") or 0))
        own = t.get("lines")
        b = base if not own else sum((line_net(l) for i, l in enumerate(spec.get("lines") or [], 1)
                                      if i in own), Decimal(0))
        out.append((str(t.get("name") or ""), rate, r2(b), r2(b * rate / 100)))
    return out


def gross_estimate(spec):
    """The invoice total with tax, as the page states it: the threshold rules read this."""
    lines = spec.get("lines") or []
    net = sum((line_net(l) for l in lines), Decimal(0))
    c = seller_country(spec)
    if c in ("CA", "US"):
        return net + sum((t[3] for t in sales_taxes(spec)), Decimal(0))
    if c not in PAGE_ONLY and not any(l.get("vat_rate") not in (None, "") for l in lines):
        return net
    return doc_amounts.settle(spec, [dict(cat=str(l.get("vat_category") or "S").upper(),
                                          rate=Decimal(str(l.get("vat_rate") or 0)), net=line_net(l)) for l in lines])["grand"]


def has_category(spec, cat):
    return any(str(l.get("vat_category") or "S").upper() == cat for l in spec.get("lines") or [])


def is_credit(spec):
    code = str(spec.get("type_code") or "").strip()
    return code == "381" or (not code and bool(spec.get("preceding_invoice")))


def refuse(spec):
    """(missing, warnings). A particular the order declares unknown (einvoice_particulars.DECLARABLE) is no longer
    a stop: it becomes a warning naming it, what asks for it and what to tell the person. A total that does not
    close and anything invented still stop."""
    missing, warnings = _refuse_all(spec)
    declared = particulars.declared_unknown(spec)
    kept = []
    for m in missing:
        key = re.match(r"[a-z_.]+", m).group(0).rstrip(".:") if re.match(r"[a-z_.]+", m) else ""
        if key in particulars.DECLARABLE and key in declared:
            warnings.append("%s is declared unknown, and the invoice is not complete without it; the page prints nothing "
                            "in its place%s. Say in your reply what is missing and why it matters: %s"
                            % (key, " and no XML file is written (that syntax is not valid without it)"
                               if key in particulars.XML_NEEDS else "", m.split(" (")[0]))
        else:
            kept.append(m)
    return kept, warnings


def xml_blocked(spec):
    """The declared-unknown particulars the XML cannot be valid without: then only the page is written."""
    return particulars.blocked_keys(spec)


def _refuse_all(spec):
    """(missing, warnings) for the seller's country. Nothing here is filled in by guess."""
    c = seller_country(spec)
    fn = {"NO": _no, "DK": _dk, "FI": _fi, "GB": _gb, "AU": _au, "CA": _ca, "US": _us,
          "BE": _be, "NL": _nl, "AT": _at, "IE": _ie, "ES": _es, "IT": _it, "PL": _pl}.get(c)
    missing, warnings = fn(spec) if fn else ([], [])
    if syntax_of(spec) in ("ubl", "si-ubl"):
        m2, w2 = _peppol(spec)
        missing += m2
        warnings += w2
    if syntax_of(spec) == "finvoice":
        m2, w2 = _finvoice(spec)
        missing += m2
        warnings += w2
    if syntax_of(spec) == "ebinterface":
        m2, w2 = _ebinterface(spec)
        missing += m2
        warnings += w2
    extra = {"facturae": _facturae, "fatturapa": _fatturapa, "ksef": _ksef}.get(syntax_of(spec))
    if extra:
        m2, w2 = extra(spec)
        missing += m2
        warnings += w2
    return missing, warnings


def _national_currency(spec, missing, rule):
    c = seller_country(spec)
    national = NATIONAL_CURRENCY.get(c, "EUR" if c in ("FI", "BE", "NL", "AT", "IE", "ES", "IT") else None)
    cur = str(spec.get("currency") or "").upper()
    if national and cur and cur != national and not spec.get("exchange_rate"):
        missing.append("exchange_rate: the invoice is in %s and the VAT must also be stated in %s (%s); give "
                       "the rate the order uses" % (cur, national, rule))


def _no(spec):
    missing, warnings = [], []
    s, b = spec.get("seller") or {}, spec.get("buyer") or {}
    num = org_number(s, "NO")
    if not num:
        missing.append("seller.org_number: the seller's organisasjonsnummer (bokføringsforskriften § 5-1-2)")
    elif not ids.no_orgnr_ok(num):
        missing.append("seller.org_number %s fails its modulus 11 check digit; read it again from the "
                       "person's files (NO-R-001)" % num)
    v = vat_id(s)
    if v and not re.fullmatch(r"NO\d{9}MVA", v):
        missing.append("seller.vat_id %s: a Norwegian VAT number is NO, the organisasjonsnummer and MVA "
                       "(NO-R-001; § 5-1-2)" % v)
    if v and num and ids.digits(v) != ids.digits(num):
        missing.append("seller.vat_id %s does not carry the organisasjonsnummer %s" % (v, num))
    if not v and any(str(l.get("vat_category") or "S").upper() == "S" for l in spec.get("lines") or []):
        missing.append("seller.vat_id: a seller that charges merverdiavgift is in Merverdiavgiftsregisteret "
                       "and writes NO<org.nr.>MVA (§ 5-1-2)")
    if legal_form(s).upper() in NO_FORETAK and not s.get("registered_office"):
        warnings.append("seller.registered_office not given: an %s states its head office's address "
                        "(§ 5-1-2); the page prints the seller's address as it" % legal_form(s))
    if not b.get("name") or not (b.get("street") or org_number(b, "NO")):
        missing.append("buyer: the buyer's name and its address or organisasjonsnummer (§ 5-1-2)")
    if has_category(spec, "AE") and not org_number(b, "NO"):
        missing.append("buyer.org_number: a reverse-charge sale names the buyer's organisasjonsnummer "
                       "(§ 5-1-2, § 5-1-1 nr. 7)")
    if not is_credit(spec):
        if not spec.get("delivery_date"):
            missing.append("delivery_date: the time of delivery (§ 5-1-1 nr. 4)")
        if not spec.get("due_date"):
            missing.append("due_date: the payment due date (§ 5-1-1 nr. 5)")
        if not spec.get("delivery_address") and not spec.get("delivery_place"):
            warnings.append("no delivery_address: the page states the buyer's address as the place of "
                            "delivery (§ 5-1-1 nr. 4); say so in your reply")
    pay = spec.get("payment") or {}
    if pay.get("account") and not ids.no_account_ok(pay["account"]):
        missing.append("payment.account %s fails its modulus 11 check digit" % pay["account"])
    if pay.get("kid") and not ids.no_kid_ok(pay["kid"]):
        missing.append("payment.kid %s fails its check digit (modulus 10 or 11)" % pay["kid"])
    _national_currency(spec, missing, "bokføringsforskriften § 5-1-1 nr. 6")
    return missing, warnings


def _dk(spec):
    missing, warnings = [], []
    s, b = spec.get("seller") or {}, spec.get("buyer") or {}
    cvr = org_number(s, "DK")
    if not cvr:
        missing.append("seller.cvr: the seller's CVR-nummer, its VAT number (momsbekendtgørelsen § 58, stk. 1, "
                       "nr. 3; DK-R-002)")
    elif not ids.dk_cvr_ok(cvr):
        missing.append("seller.cvr %s: a CVR-nummer is eight digits" % cvr)
    elif not ids.dk_cvr_mod11(cvr):
        warnings.append("seller.cvr %s does not pass the old modulus 11 check; read it again from the files" % cvr)
    for role, p in (("seller", s), ("buyer", b)):
        if not p.get("name") or not p.get("street") or not p.get("city"):
            missing.append("%s: name and address (§ 58, stk. 1, nr. %d)" % (role, 4 if role == "seller" else 5))
    if has_category(spec, "AE") and not vat_id(b):
        missing.append("buyer.vat_id: a reverse-charge invoice names the buyer's VAT number (Art. 226(4))")
    pay = spec.get("payment") or {}
    code = str(pay.get("means_code") or "58")
    if pay and code not in DK_PAYMENT_CODES:
        missing.append("payment.means_code %s: a Danish seller pays by 1, 10, 31, 42, 48, 49, 50, 58, 59, 93 "
                       "or 97 (DK-R-005); 42 a Danish account, 58 a SEPA transfer to an IBAN" % code)
    if code in ("31", "42") and not (pay.get("account") and pay.get("bank_reg")):
        missing.append("payment.bank_reg and payment.account: the registration number and account for a "
                       "bank transfer (DK-R-006)")
    if code == "58" and pay and not pay.get("iban"):
        missing.append("payment.iban: the IBAN for a SEPA transfer (BR-61)")
    if not is_credit(spec) and not spec.get("due_date"):
        warnings.append("no due_date: a Danish invoice states when it falls due; ask for the payment term")
    return missing, warnings


def _fi(spec):
    missing, warnings = [], []
    s, b = spec.get("seller") or {}, spec.get("buyer") or {}
    yt = org_number(s, "FI")
    if not yt:
        missing.append("seller.business_id: the seller's Y-tunnus, 1234567-8 (AVL 209 e § 3; the VAT "
                       "identifier is FI and its digits)")
    elif not ids.fi_ytunnus_ok(yt):
        missing.append("seller.business_id %s fails its check digit; read it again from the files" % yt)
    if not s.get("vat_id") and yt and ids.fi_ytunnus_ok(yt):
        warnings.append("seller.vat_id not given: the page and the XML state %s, FI and the Y-tunnus "
                        "(AVL 209 e §)" % ids.fi_vat_of(yt))
    for role, p in (("seller", s), ("buyer", b)):
        if not p.get("name") or not p.get("street") or not p.get("city"):
            missing.append("%s: name and address (AVL 209 e § 5)" % role)
    if has_category(spec, "AE") and not vat_id(b):
        missing.append("buyer.vat_id: a reverse charge names the buyer's VAT identifier (AVL 209 e § 4)")
    if not is_credit(spec):
        if not spec.get("delivery_date"):
            missing.append("delivery_date: the date the goods were delivered or the service done "
                           "(AVL 209 e § 7)")
        if not spec.get("due_date"):
            missing.append("due_date: the eräpäivä the invoice is paid by")
    pay = spec.get("payment") or {}
    if pay.get("iban") and not ids.iban_ok(pay["iban"]):
        missing.append("payment.iban %s fails its check digits (ISO 13616)" % pay["iban"])
    ref = pay.get("reference")
    if ref and not ids.fi_reference_ok(ref):
        missing.append("payment.reference %s fails its check digit (viitenumero 7-3-1, or RF ISO 11649)" % ref)
    if not ref and not is_credit(spec):
        warnings.append("no payment.reference: a Finnish invoice usually carries a viitenumero; give the "
                        "seller's if it uses one")
    _national_currency(spec, missing, "the VAT in euros")
    return missing, warnings


def _gb(spec):
    missing, warnings = [], []
    s, b = spec.get("seller") or {}, spec.get("buyer") or {}
    v = vat_id(s)
    if not v:
        missing.append("seller.vat_id: the supplier's VAT registration number (VAT Notice 700/21 4.1)")
    elif not ids.gb_vat_ok(v):
        missing.append("seller.vat_id %s is not a UK VAT registration number (GB and nine digits whose "
                       "check digits hold)" % v)
    for role, p in (("seller", s), ("buyer", b)):
        if not p.get("name") or not p.get("street"):
            missing.append("%s: name and address (VAT Notice 700/21 4.1)" % role)
    for i, l in enumerate(spec.get("lines") or [], 1):
        if l.get("vat_rate") in (None, "") and str(l.get("vat_category") or "S").upper() == "S":
            missing.append("line %d vat_rate: each description states its rate (4.1)" % i)
    _national_currency(spec, missing, "VAT Notice 700/21 4.1, the total VAT in sterling")
    if legal_form(s) in ("Ltd", "Limited", "PLC", "LLP") and not (s.get("register_number") and s.get("registered_office")):
        warnings.append("seller.register_number and registered_office not given: a UK company's business "
                        "letters, order forms and websites state its registered number, the part of the UK it "
                        "is registered in and its registered office (SI 2015/17 reg 25); an invoice needs its "
                        "registered name (reg 24), so nothing is missing from the page; say so")
    return missing, warnings


def _au(spec):
    missing, warnings = [], []
    s, b = spec.get("seller") or {}, spec.get("buyer") or {}
    abn = org_number(s, "AU")
    if not abn:
        missing.append("seller.abn: the supplier's ABN (GST Act s 29-70(1)(c))")
    elif not ids.au_abn_ok(abn):
        missing.append("seller.abn %s fails its modulus 89 check; read it again from the files" % abn)
    if not s.get("name"):
        missing.append("seller.name: the supplier's identity (GST Regulations s 29-70.01)")
    if gross_estimate(spec) >= AU_BUYER_THRESHOLD and not (b.get("name") and (b.get("street") or b.get("abn"))):
        missing.append("buyer: from A$1,000 a tax invoice states the buyer's identity and its address or ABN "
                       "(GST Regulations s 29-70.01)")
    if b.get("abn") and not ids.au_abn_ok(b["abn"]):
        missing.append("buyer.abn %s fails its modulus 89 check" % b["abn"])
    if str(spec.get("currency") or "AUD").upper() != "AUD":
        warnings.append("the invoice is not in AUD; state the GST in Australian dollars as well if the "
                        "buyer claims it")
    return missing, warnings


def _ca(spec):
    missing, warnings = [], []
    s, b = spec.get("seller") or {}, spec.get("buyer") or {}
    taxes = sales_taxes(spec)
    total = gross_estimate(spec)
    names = " ".join(t[0] for t in taxes).upper()
    if taxes and any(w in names for w in ("GST", "HST", "TPS", "TVH")) and total >= CA_REGISTRATION_THRESHOLD:
        if not s.get("gst_number"):
            missing.append("seller.gst_number: the GST/HST registration number, 123456789 RT0001 (SOR/91-45 "
                           "s. 3(b)(i), from $100)")
        elif not ids.ca_gst_ok(s["gst_number"]):
            missing.append("seller.gst_number %s: nine digits, RT and four digits" % s["gst_number"])
    if ("QST" in names or "TVQ" in names) and not ids.ca_qst_ok(s.get("qst_number")):
        missing.append("seller.qst_number: a Quebec registrant charging QST states its QST number, "
                       "1234567890 TQ0001")
    if total >= CA_BUYER_THRESHOLD:
        if not b.get("name"):
            missing.append("buyer.name: from $500 the buyer's name (SOR/91-45 s. 3(c)(i))")
        if not spec.get("payment_terms"):
            missing.append("payment_terms: from $500 the terms of payment (SOR/91-45 s. 3(c)(ii))")
    for t in spec.get("taxes") or []:
        if not t.get("name") or t.get("rate") in (None, ""):
            missing.append("taxes: each tax has a name (GST, HST, QST, PST) and a rate")
    if not taxes and any(taxable(l) for l in spec.get("lines") or []):
        warnings.append("no taxes listed: the page charges no GST/HST; say so if the seller is not registered")
    return missing, warnings


def _us(spec):
    missing, warnings = [], []
    for t in spec.get("taxes") or []:
        if not t.get("name") or t.get("rate") in (None, ""):
            missing.append("taxes: each sales tax names its jurisdiction (\"Texas state sales tax\", "
                           "\"City of Austin\") and its rate")
    if any(str(l.get("vat_category") or "").upper() in ("AE", "K") for l in spec.get("lines") or []):
        missing.append("lines: a US invoice carries no VAT category; use taxable: true or false per line")
    if not spec.get("taxes"):
        warnings.append("no taxes listed: the page charges no sales tax; say why if the buyer is exempt "
                        "(a resale or exemption certificate) or the seller does not collect it there")
    return missing, warnings


def _peppol(spec):
    """What Peppol BIS Billing 3.0 needs that the plain EN 16931 spec might not give (restated here; the
    official rules run untouched in EINV-PEPPOL)."""
    missing, warnings = [], []
    if not spec.get("buyer_reference") and not spec.get("order_reference"):
        missing.append("buyer_reference or order_reference: the buyer's reference (their contact or "
                       "reference, \"Deres ref.\") or their order number (PEPPOL-EN16931-R003); ask for it")
    for role, rule in (("seller", "PEPPOL-EN16931-R020"), ("buyer", "PEPPOL-EN16931-R010")):
        scheme, ident, why = endpoint(spec, role)
        if not ident:
            missing.append("%s.electronic_address: its Peppol address, {\"scheme\": \"0192\", \"id\": ...} or "
                           "\"0192:999999999\" (%s)" % (role, rule))
        elif why:
            warnings.append("%s.electronic_address not given: the Peppol address is %s; use the one it gave "
                            "if it has one" % (role, why))
        elif not scheme:
            missing.append("%s.electronic_address %s: name its scheme" % (role, ident))
    pay = spec.get("payment") or {}
    if pay and str(pay.get("means_code") or "58") in ("30", "58") and not (pay.get("iban") or pay.get("account")):
        missing.append("payment.iban or payment.account: the account for a credit transfer (BR-61)")
    return missing, warnings


def _finvoice(spec):
    missing, warnings = [], []
    pay = spec.get("payment") or {}
    if not pay.get("iban"):
        missing.append("payment.iban: Finvoice carries the seller's account as an IBAN (EpiAccountID)")
    if not pay.get("bic"):
        missing.append("payment.bic: Finvoice carries the seller's bank as a BIC (EpiBfiIdentifier)")
    if not spec.get("due_date") and not is_credit(spec):
        missing.append("due_date: Finvoice's payment date (EpiDateOptionDate)")
    return missing, warnings


# ---- wave 8: Belgium, the Netherlands, Austria, Ireland ----------------------------------------

def _parties_named(spec, rule, missing, need_street=True):
    for role in ("seller", "buyer"):
        p = spec.get(role) or {}
        if not p.get("name") or not p.get("city") or (need_street and not p.get("street")):
            missing.append("%s: name and address (%s)" % (role, rule))


def _no_delivery(spec, rule, warnings):
    if not is_credit(spec) and not spec.get("delivery_date"):
        warnings.append("no delivery_date: the page states the date of supply as the invoice date (%s); say "
                        "so in your reply if they differ" % rule)


def _company(p, words, rule, warnings, need=("registered_office", "register_number")):
    form = legal_form(p) or W8_FORMS.search(str((p or {}).get("name") or "").strip())
    if form and any(not p.get(k) for k in need):
        warnings.append("seller %s not given: a company's invoices and letters state %s (%s); say so in your reply"
                        % (" and ".join(k for k in need if not p.get(k)), words, rule))


def _be(spec):
    missing, warnings = [], []
    s, b = spec.get("seller") or {}, spec.get("buyer") or {}
    num = org_number(s, "BE")
    if not num:
        missing.append("seller.register_number: the seller's enterprise number, 0123.456.749, whose VAT number is BE "
                       "and the same ten digits (Royal Decree no. 1, art. 5 § 1 2°; Code of companies and associations "
                       "art. 2:20)")
    elif not ids.be_enterprise_ok(num):
        missing.append("seller.register_number %s: the enterprise number fails its modulus 97 check; read it again from the person's "
                       "files (PEPPOL-COMMON-R043)" % num)
    v = str(s.get("vat_id") or "").replace(" ", "").replace(".", "").upper()
    if v and num and ids.be_enterprise_ok(num) and v != "BE" + ids.be_enterprise_digits(num):
        missing.append("seller.vat_id %s is not BE and the enterprise number %s" % (s["vat_id"], num))
    _parties_named(spec, "Royal Decree no. 1, art. 5", missing)
    if country(b) == "BE" and not (org_number(b, "BE") or b.get("vat_id")) and not b.get("private"):
        missing.append("buyer.register_number: a Belgian business customer's VAT number (art. 5) and its Peppol "
                       "address under 0208 (the 2026 mandate); for a consumer say \"private\": true")
    if org_number(b, "BE") and not ids.be_enterprise_ok(org_number(b, "BE")):
        missing.append("buyer.register_number %s: the enterprise number fails its modulus 97 check" % org_number(b, "BE"))
    if has_category(spec, "AE") and not (vat_id(b) or b.get("vat_id")):
        missing.append("buyer.vat_id: a reverse-charge invoice names the customer's VAT number (art. 5)")
    ref = (spec.get("payment") or {}).get("reference")
    if ref and "+" in str(ref) and not ids.be_ogm_ok(ref):
        missing.append("payment.reference %s: a structured communication is twelve digits whose last two are the "
                       "first ten modulo 97, 97 when that leaves nothing" % ref)
    named = str(spec.get("language") or b.get("language") or "").strip().lower()
    if named and named.split("-")[0] != "nl" and ids.be_region_locale(s.get("postcode"))[1] == "Flanders":
        if ids.be_dutch_at_home(s, b, named):
            warnings.append("language %s: a firm in Flanders writes an invoice to a customer in Belgium in Dutch "
                            "(decree of 19 July 1973 art. 5 § 1), so the page stays Dutch; say so in your reply" % named)
        else:
            warnings.append("language %s: for a customer in another EU or EEA state the decree of 19 July 1973 art. 5 "
                            "§ 2/1 allows this page as a second valid version; the Dutch invoice stands beside it, so "
                            "build the same order without \"language\" too" % named)
    if not is_credit(spec) and not spec.get("due_date"):
        warnings.append("no due_date: a Belgian invoice usually states when it is due; ask for the payment term")
    _no_delivery(spec, "art. 5 § 1 5°", warnings)
    # The company's own particulars (art. 2:20, which names invoices) are the page builder's to warn about
    # and EINV-PARTICULARS' to check: skills/_checks/einvoice_particulars.py.
    _national_currency(spec, missing, "the VAT in euro")
    return missing, warnings


def _nl(spec):
    missing, warnings = [], []
    s, b = spec.get("seller") or {}, spec.get("buyer") or {}
    v = s.get("vat_id")
    if not v:
        missing.append("seller.vat_id: the seller's btw-identificatienummer, NL123456782B01 (Wet OB 1968 art. 35a)")
    elif not re.fullmatch(r"NL\d{9}B\d{2}", str(v).replace(" ", "").upper()):
        missing.append("seller.vat_id %s is not a Dutch btw-id: NL, nine digits, B, two digits" % v)
    elif not ids.nl_vat_ok(v):
        warnings.append("seller.vat_id %s passes neither the eleven test nor modulus 97; read it again from the "
                        "person's files" % v)
    if not org_number(s, "NL"):
        missing.append("seller.register_number: the seller's KvK number, eight digits (Handelsregisterwet 2007 art. 27; "
                       "NL-R-003 under scheme 0106). The Peppol file cannot be written without it. If the person's "
                       "files do not give it, never make one up: add \"register_number\" to the seller's \"unknown\"; "
                       "the page is written without it, the XML is not, and the reply says so")
    elif not ids.nl_kvk_ok(org_number(s, "NL")):
        missing.append("seller.register_number %s: a KvK number is eight digits" % org_number(s, "NL"))
    _parties_named(spec, "art. 35a", missing)
    for role in ("seller", "buyer"):
        p = spec.get(role) or {}
        if country(p) == "NL" and not p.get("postcode"):
            missing.append("%s.postcode: a Dutch address carries its postcode (NL-R-002, NL-R-004)" % role)
    if country(b) == "NL" and not b.get("private"):
        if not org_number(b, "NL"):
            missing.append("buyer.register_number: a Dutch business customer's KvK number (NL-R-005, scheme 0106)")
        elif not ids.nl_kvk_ok(org_number(b, "NL")):
            missing.append("buyer.register_number %s: a KvK number is eight digits" % org_number(b, "NL"))
    if has_category(spec, "AE") and not b.get("vat_id"):
        missing.append("buyer.vat_id: a reverse-charge invoice (btw verlegd) names the customer's btw-id (art. 35a)")
    pay = spec.get("payment") or {}
    if not is_credit(spec) and not pay:
        missing.append("payment: how the customer pays, a means_code and the IBAN (NL-R-007)")
    if pay and country(b) == "NL" and str(pay.get("means_code") or "58") not in NL_PAYMENT_CODES:
        missing.append("payment.means_code %s: a Dutch seller and buyer use 30, 48, 49, 57, 58 or 59 (NL-R-008)"
                       % pay.get("means_code"))
    if spec.get("lines") and any(l.get("order_line") for l in spec["lines"]) and not spec.get("order_reference"):
        missing.append("order_reference: order line references need the order number (NL-R-009)")
    _no_delivery(spec, "art. 35a", warnings)
    _national_currency(spec, missing, "the VAT in euro")
    return missing, warnings


def _at(spec):
    missing, warnings = [], []
    s, b = spec.get("seller") or {}, spec.get("buyer") or {}
    v = vat_id(s)
    if not v:
        missing.append("seller.vat_id: the seller's UID-Nummer, ATU and eight digits (UStG § 11 Abs. 1 Z 3 lit. i)")
    elif not ids.at_uid_ok(v):
        missing.append("seller.vat_id %s fails its check digit (ATU and eight digits); read it again" % v)
    _parties_named(spec, "§ 11 Abs. 1 Z 3 lit. a, b", missing)
    total = gross_estimate(spec)
    if total > AT_BUYER_UID_THRESHOLD and not b.get("vat_id") and not b.get("private"):
        missing.append("buyer.vat_id: over 10 000 euros the invoice states the recipient's UID-Nummer "
                       "(§ 11 Abs. 1 Z 3 lit. b)")
    if b.get("vat_id") and country(b) == "AT" and not ids.at_uid_ok(b["vat_id"]):
        missing.append("buyer.vat_id %s fails its check digit" % b["vat_id"])
    if has_category(spec, "AE") and not b.get("vat_id"):
        missing.append("buyer.vat_id: a reverse charge names the recipient's UID-Nummer (§ 11 Abs. 1a)")
    if not is_credit(spec) and not spec.get("delivery_date") and not spec.get("delivery_period"):
        missing.append("delivery_date: the date or period of the supply (§ 11 Abs. 1 Z 3 lit. d)")
    if s.get("register_number") and not ids.at_fn_ok(s["register_number"]):
        missing.append("seller.register_number %s: a Firmenbuchnummer is FN, up to six digits and a letter" % s["register_number"])
    _company(s, "the Firmenbuchnummer, the Firmenbuchgericht and the seat on its letters and order forms (UGB "
             "§ 14; invoices are not named there, so the page prints them when given)", "UGB § 14", warnings,
             ("register_number", "register", "registered_office"))
    _national_currency(spec, missing, "the VAT in euro")
    return missing, warnings


def _ie(spec):
    missing, warnings = [], []
    s, b = spec.get("seller") or {}, spec.get("buyer") or {}
    v = s.get("vat_id")
    if not v:
        missing.append("seller.vat_id: the supplier's VAT registration number, IE1234567T (VAT Regulations 2010 reg. 20)")
    elif not ids.ie_vat_form(v):
        missing.append("seller.vat_id %s is not an Irish VAT number: IE, seven digits and one or two letters" % v)
    elif not ids.ie_vat_ok(v):
        warnings.append("seller.vat_id %s fails the usual check letter (Revenue publishes none); read it again" % v)
    _parties_named(spec, "reg. 20", missing, need_street=True)
    if (has_category(spec, "AE") or has_category(spec, "K")) and not b.get("vat_id"):
        missing.append("buyer.vat_id: a reverse charge or a supply to another EU business names the customer's VAT "
                       "number (reg. 20)")
    if not is_credit(spec) and not spec.get("delivery_date"):
        missing.append("delivery_date: the date the goods or services were supplied (reg. 20)")
    if is_credit(spec) and not spec.get("note"):
        missing.append("note: the reason for the credit note, in a few words (VAT Regulations 2010 reg. 20(5))")
    if is_credit(spec) and not b.get("vat_id") and not b.get("private"):
        missing.append("buyer.vat_id: a credit note states the registration number of the person it is issued to "
                       "(VAT Regulations 2010 reg. 20(5)(d)); for a consumer say \"private\": true")
    for i, l in enumerate(spec.get("lines") or [], 1):
        if l.get("vat_rate") in (None, "") and str(l.get("vat_category") or "S").upper() == "S":
            missing.append("line %d vat_rate: each rate and the amount at it (reg. 20)" % i)
    _company(s, "its registered number and registered office on its letters and order forms (Companies Act 2014 "
             "s. 151; invoices are not named there, so the page prints them when given)", "Companies Act 2014",
             warnings, ("register_number", "registered_office"))
    _national_currency(spec, missing, "the VAT in euro (s. 66)")
    return missing, warnings


def _ebinterface(spec):
    """What ebInterface 6.1 itself needs: a town and postcode for both parties, the biller's UID, and the
    order reference a federal buyer gives (the Auftragsreferenz)."""
    missing, warnings = [], []
    for role in ("seller", "buyer"):
        p = spec.get(role) or {}
        if not p.get("postcode") or not p.get("city"):
            missing.append("%s.postcode and city: ebInterface's Address needs ZIP and Town" % role)
    if not spec.get("order_reference") and not spec.get("buyer_reference"):
        warnings.append("no order_reference: a public buyer on erechnung.gv.at gives an Auftragsreferenz, its order "
                        "number; ask for it when the buyer is one")
    return missing, warnings


# ---- wave 9: Spain, Italy, Poland ---------------------------------------------------------------

# Facturae's reasons for a rectifying invoice (ReasonCodeType, with the Spanish words the schema pairs them
# with) and the ways to rectify (CorrectionMethodType). The pack writes the difference, method 02.
FACTURAE_REASONS = {
    "01": "Número de la factura", "02": "Serie de la factura", "03": "Fecha expedición",
    "04": "Nombre y apellidos/Razón Social-Emisor", "05": "Nombre y apellidos/Razón Social-Receptor",
    "06": "Identificación fiscal Emisor/obligado", "07": "Identificación fiscal Receptor",
    "08": "Domicilio Emisor/Obligado", "09": "Domicilio Receptor", "10": "Detalle Operación",
    "11": "Porcentaje impositivo a aplicar", "12": "Cuota tributaria a aplicar", "13": "Fecha/Periodo a aplicar",
    "14": "Clase de factura", "15": "Literales legales", "16": "Base imponible",
    "80": "Cálculo de cuotas repercutidas", "81": "Cálculo de cuotas retenidas",
    "82": "Base imponible modificada por devolución de envases / embalajes",
    "83": "Base imponible modificada por descuentos y bonificaciones",
    "84": "Base imponible modificada por resolución firme, judicial o administrativa",
    "85": "Base imponible modificada cuotas repercutidas no satisfechas. Auto de declaración de concurso"}
# FatturaPA 1.2.3: the regime fiscale and the Natura of a line without IVA.
IT_REGIME = re.compile(r"RF(0[1-9]|1[0-9]|20)")
IT_NATURE = re.compile(r"N1|N2\.[12]|N3\.[1-6]|N4|N5|N6\.[1-9]|N7")
# FA(3): the rates P_12 takes as numbers; every other line names its category.
PL_RATES = ("23", "22", "8", "7", "5", "4", "3")
PL_BASIS = {"act": "P_19A", "ustawa": "P_19A", "directive": "P_19B", "dyrektywa": "P_19B", "other": "P_19C",
            "inna": "P_19C"}
UNTAXED = ("E", "K", "G", "O", "Z")


def credit_sign(spec):
    """-1 where a credit is written as the difference itself, with minus amounts: a Spanish rectifying
    invoice (Real Decreto 1619/2012 art. 15.5) and a Polish correcting invoice (ustawa o VAT art. 106j ust. 2
    pkt 5). Everywhere else the document type carries the sign and the amounts stay positive."""
    return -1 if is_credit(spec) and seller_country(spec) in ("ES", "PL") else 1


def nature_of(line, spec):
    return str((line or {}).get("nature") or spec.get("nature") or "").strip().upper()


def rate_of(line):
    return Decimal(str((line or {}).get("vat_rate") or 0))


def category(line):
    return str((line or {}).get("vat_category") or "S").upper()


def _reasons(spec, rule, missing, cats=UNTAXED):
    for i, l in enumerate(spec.get("lines") or [], 1):
        if category(l) in cats and not (l.get("exemption_reason") or spec.get("exemption_reason")):
            missing.append("line %d exemption_reason: why no tax is charged, in the words the invoice is to carry (%s)" % (i, rule))


def _es(spec):
    missing, warnings = [], []
    s, b = spec.get("seller") or {}, spec.get("buyer") or {}
    v = s.get("vat_id")
    if not v:
        missing.append("seller.vat_id: the seller's NIF, such as B12345674, with ES before it as a VAT number (Real Decreto "
                       "1619/2012 art. 6.1 d)")
    elif not ids.es_nif_form(v):
        missing.append("seller.vat_id %s is not a NIF: nine characters, a DNI or NIE with its letter, or a letter, seven "
                       "digits and a control character (Orden EHA/451/2008 art. 2)" % v)
    elif not ids.es_nif_ok(v):
        warnings.append("seller.vat_id %s: the usual check character does not hold; read it again from the person's files" % v)
    _parties_named(spec, "Real Decreto 1619/2012 art. 6.1 c, e", missing)
    if not b.get("vat_id") and not b.get("private"):
        if country(b) == "ES":
            missing.append("buyer.vat_id: the recipient's NIF, which the invoice states for a supply made in Spain by a "
                           "seller established there (art. 6.1 d 3.º); for a consumer say \"private\": true")
        elif has_category(spec, "AE") or has_category(spec, "K"):
            missing.append("buyer.vat_id: a reverse charge or an exempt supply to another EU state names the recipient's "
                           "tax number (art. 6.1 d 1.º, 2.º)")
    if b.get("vat_id") and country(b) == "ES":
        if not ids.es_nif_form(b["vat_id"]):
            missing.append("buyer.vat_id %s is not a NIF: nine characters (Orden EHA/451/2008 art. 2)" % b["vat_id"])
        elif not ids.es_nif_ok(b["vat_id"]):
            warnings.append("buyer.vat_id %s: the usual check character does not hold; read it again" % b["vat_id"])
    _reasons(spec, "art. 6.1 j: a reference to the provision that exempts the supply, or that it is exempt", missing)
    for i, l in enumerate(spec.get("lines") or [], 1):
        if l.get("vat_rate") in (None, "") and category(l) == "S":
            missing.append("line %d vat_rate: the rate applied (art. 6.1 g)" % i)
    if is_credit(spec) and not spec.get("series"):
        missing.append("series: a rectifying invoice is numbered in a series of its own (art. 6.1 a 2.º), such as \"R\"")
    _no_delivery(spec, "art. 6.1 i", warnings)
    _national_currency(spec, missing, "the tax in euro")
    return missing, warnings


def _facturae(spec):
    """What Facturae 3.2.2 itself needs (restated; the official schema runs untouched in EINV-FACTURAE)."""
    missing, warnings = [], []
    for role in ("seller", "buyer"):
        p = spec.get(role) or {}
        if country(p) == "ES":
            if not re.fullmatch(r"\d{5}", str(p.get("postcode") or "")):
                missing.append("%s.postcode: five digits (Facturae AddressInSpain)" % role)
            if not p.get("province"):
                missing.append("%s.province: the province of the address, which Facturae's AddressInSpain carries" % role)
        if role == "buyer" and not p.get("vat_id"):
            missing.append("buyer.vat_id: Facturae identifies both parties by a tax number (TaxIdentificationNumber)")
    if len(str(spec.get("number") or "")) > 20:
        missing.append("number %s: Facturae takes at most 20 characters" % spec.get("number"))
    if is_credit(spec):
        corr = spec.get("correction") if isinstance(spec.get("correction"), dict) else {}
        if str(corr.get("reason_code") or "") not in FACTURAE_REASONS:
            missing.append("correction.reason_code: what is rectified, as Facturae codes it: 01 number, 03 date, 10 the "
                           "items, 11 the rate, 12 the tax, 16 the taxable base, 82 returned packaging, 83 discounts and "
                           "rebates, 84 a firm ruling, 85 unpaid tax in insolvency (01 to 16, 80 to 85)")
        if not (isinstance(corr.get("period"), dict) and corr["period"].get("from") and corr["period"].get("to")):
            if not spec.get("preceding_invoice_date"):
                missing.append("preceding_invoice_date or correction.period: Facturae states the tax period of the "
                               "rectified invoice (TaxPeriod)")
            else:
                warnings.append("no correction.period: the file states the rectified invoice's own date as its tax "
                                "period; give {\"from\", \"to\"} when the seller knows the period it was declared in")
    warnings.append("the Facturae file is not signed: FACe and the other public entry points take a Facturae only with "
                    "an XAdES signature made with the seller's certificate (Ley 25/2013 art. 5); this pack does not sign. "
                    "Say so in your reply")
    return missing, warnings


def _it(spec):
    missing, warnings = [], []
    s, b = spec.get("seller") or {}, spec.get("buyer") or {}
    v = s.get("vat_id")
    if not v:
        missing.append("seller.vat_id: the seller's partita IVA, IT and eleven digits (DPR 633/1972 art. 21 comma 2 d)")
    elif not ids.it_piva_form(v):
        missing.append("seller.vat_id %s is not a partita IVA: IT and eleven digits" % v)
    elif not ids.it_piva_ok(v):
        warnings.append("seller.vat_id %s: the usual check digit does not hold; read it again from the person's files" % v)
    _parties_named(spec, "DPR 633/1972 art. 21 comma 2 c, e", missing)
    if not b.get("private") and not (b.get("vat_id") or b.get("tax_code")):
        missing.append("buyer.vat_id or buyer.tax_code: the customer's partita IVA, its VAT number in another EU state "
                       "or, for a resident who does not act as a business, the codice fiscale (art. 21 comma 2 f)")
    if b.get("vat_id") and country(b) == "IT":
        if not ids.it_piva_form(b["vat_id"]):
            missing.append("buyer.vat_id %s is not a partita IVA: IT and eleven digits" % b["vat_id"])
        elif not ids.it_piva_ok(b["vat_id"]):
            warnings.append("buyer.vat_id %s: the usual check digit does not hold; read it again" % b["vat_id"])
    if b.get("tax_code") and not ids.it_cf_form(b["tax_code"]):
        missing.append("buyer.tax_code %s is not a codice fiscale: sixteen characters, or eleven digits" % b["tax_code"])
    for i, l in enumerate(spec.get("lines") or [], 1):
        if l.get("vat_rate") in (None, "") and category(l) == "S":
            missing.append("line %d vat_rate: the rate (art. 21 comma 2 l)" % i)
    _reasons(spec, "art. 21 comma 6: the annotation that stands in place of the tax, such as «operazione non "
                   "imponibile» or «operazione esente», with its provision", missing)
    lines = spec.get("lines") or []
    if lines and not any(category(l) == "S" and rate_of(l) for l in lines) and "stamp_duty" not in spec:
        warnings.append("no IVA is charged on this invoice: say whether the imposta di bollo is due (\"stamp_duty\": true "
                        "or false); an e-invoice that owes it carries the annotation of the decree of 17 June 2014 "
                        "(art. 6 comma 2)")
    _no_delivery(spec, "art. 21 comma 2 g-bis", warnings)
    _national_currency(spec, missing, "the tax in euro")
    return missing, warnings


def it_recipient_code(spec):
    """(code, why): the CodiceDestinatario of the file. What the order gives; else 0000000 for a customer in
    Italy and XXXXXXX for one abroad, the two fillers the FatturaPA specification names."""
    b = spec.get("buyer") or {}
    code = str(b.get("recipient_code") or "").strip().upper()
    if code:
        return code, None
    if country(b) not in ("IT", ""):
        return "XXXXXXX", "XXXXXXX, the filler for a customer outside Italy"
    return "0000000", ("0000000 with the customer's PEC" if b.get("pec") else
                       "0000000: the Sistema di Interscambio then leaves the invoice in the customer's reserved area")


def _fatturapa(spec):
    """What FatturaPA 1.2.3 itself needs (restated; the official schema runs untouched in EINV-FATTURAPA)."""
    missing, warnings = [], []
    s, b = spec.get("seller") or {}, spec.get("buyer") or {}
    if not IT_REGIME.fullmatch(str(s.get("tax_regime") or "")):
        missing.append("seller.tax_regime: the seller's regime fiscale as FatturaPA codes it, RF01 the ordinary regime, "
                       "RF19 the flat-rate regime (RF01 to RF20); ask, never choose one")
    for role in ("seller", "buyer"):
        p = spec.get(role) or {}
        if country(p) == "IT" and not re.fullmatch(r"\d{5}", str(p.get("postcode") or "")):
            missing.append("%s.postcode: the CAP, five digits" % role)
        if p.get("province") and not re.fullmatch(r"[A-Za-z]{2}", str(p["province"])):
            missing.append("%s.province %s: the two letters of the province, such as MI" % (role, p["province"]))
    code, why = it_recipient_code(spec)
    if spec.get("public_buyer"):
        if not re.fullmatch(r"[A-Z0-9]{6}", code):
            missing.append("buyer.recipient_code: a public body's Codice Univoco Ufficio, six characters (FPA12)")
    elif not re.fullmatch(r"[A-Z0-9]{7}", code):
        missing.append("buyer.recipient_code %s: a Codice Destinatario is seven letters and digits (FPR12)" % code)
    elif why and country(b) in ("IT", "") and not b.get("pec"):
        warnings.append("buyer.recipient_code and buyer.pec not given: the file carries %s; ask the customer for its "
                        "Codice Destinatario or PEC" % why)
    for i, l in enumerate(spec.get("lines") or [], 1):
        if (category(l) != "S" or not rate_of(l)) and not IT_NATURE.fullmatch(nature_of(l, spec)):
            missing.append("line %d nature: a line without IVA names its Natura as FatturaPA codes it: N2.1 or N2.2 not "
                           "subject, N3.1 to N3.6 not taxable, N4 exempt, N6.1 to N6.9 reverse charge; ask, never "
                           "choose one" % i)
    if len(str(spec.get("number") or "")) > 20:
        missing.append("number %s: FatturaPA takes at most 20 characters" % spec.get("number"))
    warnings.append("the FatturaPA file is not sent: an invoice between parties in Italy is issued only through the "
                    "Sistema di Interscambio (D.Lgs. 127/2015 art. 1 comma 3), which this pack does not reach; the page is "
                    "a courtesy copy. Say so in your reply")
    return missing, warnings


def pln_total(spec):
    """The invoice total in złoty, at the order's rate when it is in another currency; None without one."""
    total = gross_estimate(spec)
    if str(spec.get("currency") or "PLN").upper() == "PLN":
        return total
    return total * Decimal(str(spec["exchange_rate"])) if spec.get("exchange_rate") else None


def _pl(spec):
    missing, warnings = [], []
    s, b = spec.get("seller") or {}, spec.get("buyer") or {}
    v = s.get("vat_id")
    if not v:
        missing.append("seller.vat_id: the seller's NIP, ten digits, with PL before it in EU trade (ustawa o VAT art. 106e "
                       "ust. 1 pkt 4)")
    elif not ids.pl_nip_form(v):
        missing.append("seller.vat_id %s is not a NIP: ten digits" % v)
    elif not ids.pl_nip_ok(v):
        warnings.append("seller.vat_id %s: the usual check digit does not hold; read it again from the person's files" % v)
    _parties_named(spec, "art. 106e ust. 1 pkt 3", missing)
    if not b.get("vat_id") and not b.get("private"):
        missing.append("buyer.vat_id: the buyer's NIP, or its VAT number in another EU state (art. 106e ust. 1 pkt 5); for "
                       "a consumer say \"private\": true")
    if b.get("vat_id") and country(b) == "PL":
        if not ids.pl_nip_form(b["vat_id"]):
            missing.append("buyer.vat_id %s is not a NIP: ten digits" % b["vat_id"])
        elif not ids.pl_nip_ok(b["vat_id"]):
            warnings.append("buyer.vat_id %s: the usual check digit does not hold; read it again" % b["vat_id"])
    _reasons(spec, "art. 106e ust. 1 pkt 19: the provision that exempts the supply", missing, cats=("E",))
    for i, l in enumerate(spec.get("lines") or [], 1):
        if l.get("vat_rate") in (None, "") and category(l) == "S":
            missing.append("line %d vat_rate: the rate (art. 106e ust. 1 pkt 12)" % i)
    total = pln_total(spec)
    if total is not None and total > PL_SPLIT_THRESHOLD and "split_payment" not in spec \
            and country(b) == "PL" and not b.get("private") and not is_credit(spec):
        warnings.append("the total passes 15 000 zł: an invoice for goods or services of annex 15 supplied to a taxpayer "
                        "states „mechanizm podzielonej płatności” (art. 106e ust. 1 pkt 18a); say \"split_payment\": true "
                        "or false")
    _no_delivery(spec, "art. 106e ust. 1 pkt 6", warnings)
    _national_currency(spec, missing, "the tax in złoty")
    return missing, warnings


def _ksef(spec):
    """What the logical structure FA(3) itself needs (restated; the Ministry's schema runs untouched in
    EINV-KSEF)."""
    missing, warnings = [], []
    b = spec.get("buyer") or {}
    for i, l in enumerate(spec.get("lines") or [], 1):
        cat = category(l)
        if cat == "S" and format(rate_of(l).normalize(), "f") not in PL_RATES:
            missing.append("line %d vat_rate %s: FA(3) takes 23, 22, 8, 7, 5, 4 or 3 percent; a line without tax names "
                           "its category instead (Z, K, G, E, AE, O)" % (i, l.get("vat_rate")))
        if cat == "E" and str(l.get("exemption_basis") or spec.get("exemption_basis") or "").lower() not in PL_BASIS:
            missing.append("line %d exemption_basis: where the ground of the exemption stands, \"act\" (a provision of "
                           "the VAT act, P_19A), \"directive\" (P_19B) or \"other\" (P_19C)" % i)
    if is_credit(spec):
        if not spec.get("preceding_invoice_date"):
            missing.append("preceding_invoice_date: the date of the invoice being corrected (art. 106j ust. 2 pkt 3; "
                           "FA(3) DataWystFaKorygowanej)")
        if not spec.get("preceding_ksef_number") and not spec.get("preceding_outside_ksef"):
            missing.append("preceding_ksef_number: the KSeF number of the invoice being corrected (art. 106j ust. 2 "
                           "pkt 2a), or \"preceding_outside_ksef\": true when it was issued outside KSeF")
    if not b.get("private") and not b.get("vat_id"):
        missing.append("buyer.vat_id: FA(3) identifies the buyer by NIP, by an EU VAT number or by another tax number")
    if len(spec.get("lines") or []) > 10000:
        missing.append("lines: FA(3) takes at most 10 000 lines (FaWiersz)")
    warnings.append("the FA(3) file is not sent: a structured invoice is issued through the Krajowy System e-Faktur "
                    "(art. 106ga), which this pack does not reach; the page is a picture of the same data and carries "
                    "neither a KSeF number nor the code of art. 106gb ust. 5. Say so in your reply")
    return missing, warnings
