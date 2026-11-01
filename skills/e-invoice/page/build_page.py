#!/usr/bin/env python3
"""Emit the invoice page from the person's own source file, with the locale supplying the words.

    python3 build_page.py source.json invoice-page.html [--locale de-DE]

The model names the source and the locale and writes free text; it copies no number and no
identifier. Every amount, date, unit and the IBAN come straight out of the source, and the labels
come from the locale, so a German invoice reads Rechnungsnummer, Beschreibung, Stk, Von, An,
and its payment terms read 30 Tage netto where the source said 30 days net.
A label whose value is not in the source is not printed at all, and a required field that is
missing stops the build and says which one.
"""
import argparse
import inspect
import json
import re
import shutil
import sys
from html import unescape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
from format import money as _money, date as _date, number as _number  # noqa: E402
import letter  # noqa: E402
import page_look  # noqa: E402
import company  # noqa: E402
import doc_amounts  # noqa: E402
import spec_guard  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import einvoice_create  # noqa: E402
import facturx_pdf  # noqa: E402
import countries  # noqa: E402
import country_page  # noqa: E402
from decimal import Decimal, ROUND_HALF_UP  # noqa: E402

UNIT_WORDS = {"C62": {"de-DE": "Stk", "en-GB": "pcs", "sv-SE": "st", "da-DK": "stk", "fr-FR": "pce"},
              "HUR": {"de-DE": "Std", "en-GB": "h", "sv-SE": "tim", "da-DK": "timer", "fr-FR": "h"},
              "KGM": {"de-DE": "kg", "en-GB": "kg", "sv-SE": "kg", "da-DK": "kg", "fr-FR": "kg"},
              "MTR": {"de-DE": "m", "en-GB": "m", "sv-SE": "m", "da-DK": "m", "fr-FR": "m"},
              "LTR": {"de-DE": "l", "en-GB": "l", "sv-SE": "l", "da-DK": "l", "fr-FR": "l"},
              "DAY": {"de-DE": "Tag", "en-GB": "day", "sv-SE": "dag", "da-DK": "dag", "fr-FR": "jour"}}

WORDS = {
    "de-DE": {"order_reference": "Bestellnummer", "invoice": "Rechnung", "credit_note": "Gutschrift", "preceding": "Ursprungsrechnung", "number": "Rechnungsnummer", "issue": "Rechnungsdatum",
              "due": "Fällig am", "delivery": "Lieferdatum", "from": "Von", "to": "An",
              "description": "Beschreibung", "qty": "Menge", "unit": "Einheit",
              "unit_price": "Einzelpreis", "net": "Netto", "vat": "USt.", "total": "Gesamt",
              "rate": "Satz", "base": "Basis", "account": "Konto", "terms": "Zahlungsziel",
              "delivered": "Geliefert am", "currency": "Währung", "vat_id": "USt-IdNr."},
    "en-GB": {"order_reference": "Purchase order", "invoice": "Invoice", "credit_note": "Credit note", "preceding": "Original invoice", "number": "Invoice number", "issue": "Issue date",
              "due": "Due date", "delivery": "Delivery date", "from": "From", "to": "To",
              "description": "Description", "qty": "Qty", "unit": "Unit",
              "unit_price": "Unit price", "net": "Net", "vat": "VAT", "total": "Total",
              "rate": "Rate", "base": "Base", "account": "Account", "terms": "Payment terms",
              "delivered": "Delivered", "currency": "Currency", "vat_id": "VAT ID"},
    "sv-SE": {"order_reference": "Ert ordernummer", "invoice": "Faktura", "credit_note": "Kreditfaktura", "preceding": "Ursprunglig faktura", "number": "Fakturanummer", "issue": "Fakturadatum",
              "due": "Förfallodatum", "delivery": "Leveransdatum", "from": "Från", "to": "Till",
              "description": "Beskrivning", "qty": "Antal", "unit": "Enhet",
              "unit_price": "À-pris", "net": "Netto", "vat": "Moms", "total": "Att betala",
              "rate": "Sats", "base": "Underlag", "account": "Konto", "terms": "Betalningsvillkor",
              "delivered": "Levererat", "currency": "Valuta", "vat_id": "Momsreg.nr"},
    "da-DK": {"order_reference": "Jeres ordrenr.", "invoice": "Faktura", "credit_note": "Kreditnota", "preceding": "Oprindelig faktura", "number": "Fakturanummer", "issue": "Fakturadato",
              "due": "Forfaldsdato", "delivery": "Leveringsdato", "from": "Fra", "to": "Til",
              "description": "Beskrivelse", "qty": "Antal", "unit": "Enhed",
              "unit_price": "Enhedspris", "net": "Netto", "vat": "Moms", "total": "I alt",
              "rate": "Sats", "base": "Grundlag", "account": "Konto", "terms": "Betalingsbetingelser",
              "delivered": "Leveret", "currency": "Valuta", "vat_id": "Momsnr."},
    # French: the words of CGI annexe II art. 242 nonies A and of French invoices (HT, TTC).
    "fr-FR": {"order_reference": "Bon de commande", "invoice": "Facture", "credit_note": "Facture d'avoir", "preceding": "Facture d'origine", "number": "N° de facture",
              "issue": "Date de facture", "due": "Date d'échéance", "delivery": "Date de livraison", "from": "De", "to": "À",
              "description": "Désignation", "qty": "Qté", "unit": "Unité",
              "unit_price": "Prix unitaire HT", "net": "Montant HT", "vat": "TVA", "total": "Total TTC",
              "rate": "Taux", "base": "Base HT", "account": "Compte", "terms": "Conditions de paiement",
              "delivered": "Date de livraison", "currency": "Devise", "vat_id": "N° TVA intracom."},
}
# Words the German page needed beyond the table, now for every language the page writes.
EXTRA_WORDS = {
    "de-DE": {"customer_vat": "USt-IdNr. Kunde", "tax_number": "Steuernummer", "vat_in": "USt. in %s",
              "vat_on": "USt. %s %% auf %s", "preceding_date": "Ursprungsrechnung vom",
              "buyer_reference": "Käuferreferenz", "contact": "Ansprechpartner", "phone": "Telefon", "email": "E-Mail"},
    "en-GB": {"customer_vat": "Customer VAT ID", "tax_number": "Tax number", "vat_in": "VAT in %s",
              "vat_on": "VAT %s%% on %s", "preceding_date": "Original invoice date",
              "buyer_reference": "Buyer reference", "contact": "Contact", "phone": "Phone", "email": "Email"},
    "sv-SE": {"customer_vat": "Kundens momsreg.nr", "customer_org": "Kundens org.nr", "tax_number": "Org.nr", "vat_in": "Moms i %s",
              "vat_on": "Moms %s %% på %s", "preceding_date": "Ursprunglig fakturas datum",
              "buyer_reference": "Köparens referens", "contact": "Kontaktperson", "phone": "Telefon", "email": "E-post"},
    "da-DK": {"customer_vat": "Kundens momsnr.", "tax_number": "CVR-nr.", "vat_in": "Moms i %s",
              "vat_on": "Moms %s %% af %s", "preceding_date": "Oprindelig fakturas dato",
              "buyer_reference": "Købers reference", "contact": "Kontaktperson", "phone": "Telefon", "email": "E-mail"},
    "fr-FR": {"customer_vat": "N° TVA client", "tax_number": "N° fiscal", "vat_in": "TVA en %s",
              "vat_on": "TVA %s %% sur %s", "preceding_date": "Date facture d'origine",
              "buyer_reference": "Référence acheteur", "contact": "Contact", "phone": "Téléphone", "email": "E-mail",
              "customer_siren": "SIREN client", "net_total": "Total HT", "delivery_address": "Adresse de livraison",
              "operation": "Nature de l'opération"},
}
PAID_WORDS = doc_amounts.WORDS      # the words are shared with the trade documents (skills/_shared/doc_amounts.py)
# The mention a reverse-charge invoice must carry, VAT Directive 2006/112/EC Art. 226(11a), in the
# words each language version of the Directive and national law use; France says Autoliquidation
# (CGI annexe II art. 242 nonies A I 13°).
REVERSE_CHARGE = {"de-DE": "Steuerschuldnerschaft des Leistungsempfängers", "en-GB": "Reverse charge",
                  "sv-SE": "Omvänd betalningsskyldighet", "da-DK": "Omvendt betalingspligt", "fr-FR": "Autoliquidation"}
# France: the nature of the operation (242 nonies A I 8° bis), the date label that goes with it, and
# the option for VAT on debits (I 11° bis), in the words of the article.
FR_OPERATION = {"goods": "livraisons de biens", "services": "prestations de services",
                "both": "livraisons de biens et prestations de services"}
FR_DELIVERED = {"goods": "Date de livraison", "services": "Date de la prestation",
                "both": "Date de livraison ou de prestation"}
FR_DEBITS = "Option pour le paiement de la taxe d'après les débits"
# The national currency the VAT must also be stated in when the invoice is in another one,
# Art. 230: the euro area is EUR; these member states keep their own.
NATIONAL_CURRENCY = {"SE": "SEK", "DK": "DKK", "PL": "PLN", "CZ": "CZK", "HU": "HUF", "RO": "RON"}
CREDIT_WORDS = {
    "de-DE": {"number": "Gutschriftsnummer", "issue": "Gutschriftsdatum"},
    "en-GB": {"number": "Credit note number", "issue": "Credit note date"},
    "sv-SE": {"number": "Kreditfakturanummer", "issue": "Kreditfakturadatum"},
    "da-DK": {"number": "Kreditnotanummer", "issue": "Kreditnotadato"},
    "fr-FR": {"number": "N° d'avoir", "issue": "Date de l'avoir"},
}
# Norway, Finland, Australia, Canada (English and French) and the United States (page/country_page.py).
for _table, _more in ((WORDS, country_page.WORDS), (CREDIT_WORDS, country_page.CREDIT_WORDS)):
    for _tag, _words in _more.items():
        _table[_tag] = dict(_table.get(_tag) or {}, **_words)
for _tag, _words in country_page.EXTRA_WORDS.items():
    EXTRA_WORDS[_tag] = dict(EXTRA_WORDS.get(_tag) or EXTRA_WORDS["en-GB"], **_words)
for _code, _forms in country_page.UNITS.items():
    UNIT_WORDS[_code] = dict(UNIT_WORDS.get(_code) or {}, **_forms)
REVERSE_CHARGE.update(country_page.REVERSE_CHARGE)
NATIONAL_CURRENCY.update(countries.NATIONAL_CURRENCY)

# The order decides the language. A model that picks it can get it wrong, and did: a German order
# with --locale en-GB came out with Invoice and VAT ID on it.
COUNTRY_LOCALE = {
    "DE": "de-DE", "AT": "de-DE", "CH": "de-CH", "LI": "de-DE",
    "DK": "da-DK", "SE": "sv-SE", "NO": "nb-NO", "FI": "fi-FI", "IS": "is-IS",
    "NL": "nl-NL", "BE": "nl-BE", "FR": "fr-FR", "ES": "es-ES", "IT": "it-IT",
    "PT": "pt-PT", "PL": "pl-PL", "CZ": "cs-CZ", "IE": "en-GB", "GB": "en-GB", "US": "en-US",
    "AU": "en-AU", "CA": "en-CA",
}
# Wave 8: Austria writes Austrian German, Ireland Irish English; a Belgian seller writes the language of its
# region, read off its postcode (einvoice_ids.be_region_locale).
COUNTRY_LOCALE.update({"AT": "de-AT", "IE": "en-IE", "NL": "nl-NL"})
LANGUAGE_WORDS = {
    "de-DE": ("rechnung", "rechnungsnummer", "tage", "netto", "gesamt", "menge", "ust"),
    "en-GB": ("invoice", "days", "net", "total", "quantity", "vat"),
    "da-DK": ("faktura", "dage", "i alt", "moms"),
    "sv-SE": ("faktura", "dagar", "totalt", "moms"),
    "nl-NL": ("factuur", "dagen", "totaal", "btw"),
    "fr-FR": ("facture", "jours", "total", "tva"),
}


#: The customs code and origin of an export line, in the page's words.
CUSTOMS = {"de-DE": ("Zolltarifnummer", "Ursprung"), "en-GB": ("HS code", "Origin"),
           "sv-SE": ("Tulltaxenummer", "Ursprung"), "da-DK": ("Toldtarifnummer", "Oprindelse"),
           "fr-FR": ("Code SH", "Origine")}


def locale_of_order(src):
    """The page's language: the customer's language when the order names one (Stripe sets the
    invoice language per customer the same way), else the seller's country, whose rules govern
    the invoice (VAT Directive 2006/112/EC Art. 219a), else the buyer's, else the order's words."""
    named = str(src.get("language") or (src.get("buyer") or {}).get("language") or "").strip()
    if named and countries.ids.be_dutch_at_home(src.get("seller"), src.get("buyer"), named):
        # A firm in Flanders invoices a customer in Belgium in Dutch, whatever the order names (decree of
        # 19 July 1973 art. 5 § 1; § 2/1 opens a second language only for a customer abroad).
        return "nl-BE", "the seller's region in Belgium, Flanders, where an invoice to a customer in Belgium is in Dutch"
    if named:
        # The language in the region of the parties when there is one: French in Canada is fr-CA,
        # English in Australia en-AU; else the first table that speaks it.
        regions = [str(((src.get(p) or {}).get("country")) or "").upper() for p in ("seller", "buyer")]
        speak = [tag for tag in WORDS
                 if tag.lower() == named.lower() or tag.split("-")[0] == named.lower().split("-")[0]]
        for region in regions:
            for tag in speak:
                if tag.split("-")[1] == region:
                    return tag, "the customer's language %s" % named
        if speak:
            return speak[0], "the customer's language %s" % named
    for party in ("seller", "buyer"):
        country = str(((src.get(party) or {}).get("country")) or "").upper()
        if country == "BE":
            tag, region = countries.ids.be_region_locale((src.get(party) or {}).get("postcode"))
            return tag, "the %s's region in Belgium, %s" % (party, region)
        if country in COUNTRY_LOCALE:
            return COUNTRY_LOCALE[country], "the %s's country %s" % (party, country)
    text = json.dumps(src, ensure_ascii=False).lower()
    scored = {locale: sum(1 for word in words if word in text) for locale, words in LANGUAGE_WORDS.items()}
    best = max(scored, key=lambda locale: scored[locale])
    if scored[best]:
        return best, "the words the order is written in"
    return "en-GB", "no country and no words to go by"


REQUIRED = ("number", "issue_date", "currency", "seller", "buyer", "lines")

# Payment terms: the days come from the source, the words from the page's language.
TERMS = {
    "de-DE": {"days": "%d Tage", "net": "%d Tage netto"},
    "en-GB": {"days": "%d days", "net": "%d days net"},
    "sv-SE": {"days": "%d dagar", "net": "%d dagar netto"},
    "da-DK": {"days": "%d dage", "net": "%d dage netto"},
    "fr-FR": {"days": "%d jours", "net": "%d jours net"},
}
TERMS.update(country_page.TERMS)


def terms_word(value, locale):
    """30 days net is 30 Tage netto on a German page. A term with no number is left as written."""
    raw = str(value or "").strip()
    found = re.search(r"\d+", raw)
    # Only the English forms are translated (30 days, 30 days net, net 30); a term already written
    # in words of its own, such as Remboursement sous 14 jours, is kept as the source says it.
    if not found or not re.fullmatch(r"(?i)(net\s+)?\d+\s*(days?|d)?(\s+net)?", raw):
        return raw
    table = TERMS.get(locale) or TERMS["en-GB"]
    key = "net" if re.search(r"\bnet\b", raw, re.I) else "days"
    return table[key] % int(found.group(0))


def words(locale):
    return dict(WORDS.get(locale) or WORDS["en-GB"], **(EXTRA_WORDS.get(locale) or EXTRA_WORDS["en-GB"]))


def page_locale_for(locale):
    """A locale with no words in the table is written in English, numbers and all."""
    return locale if locale in WORDS else "en-GB"


def unit_word(code, locale):
    """The unit in the page's words. A line that names none is counted in ones, as the XML writes it (C62)."""
    code = code or "C62"
    return (UNIT_WORDS.get(str(code).upper()) or {}).get(locale, str(code))


def amount(value, locale, currency=None):
    if value is None:
        return None
    text = _money(value, locale)
    return text


def with_currency(text, currency, locale):
    """An amount with its currency as the page's language writes it: 2 970,00 € in French (CLDR
    fr: the symbol after a no-break space), 2.970,00 EUR on the other pages, as before."""
    if locale == "fr-FR" and currency == "EUR":
        return "%s €" % text
    return "%s %s" % (text, currency)


def spaced_siren(value):
    d = re.sub(r"\D", "", str(value or ""))
    return " ".join((d[:3], d[3:6], d[6:9])) if len(d) == 9 else str(value or "")


def spaced_siret(value):
    d = re.sub(r"\D", "", str(value or ""))
    return " ".join((d[:3], d[3:6], d[6:9], d[9:])) if len(d) == 14 else str(value or "")


def is_credit_note(src):
    """381 is a credit note in EN 16931 (BT-3). An order that names the invoice it corrects and
    gives no type code is one too: the eval's credit note came out headed Rechnung without this."""
    code = str(src.get("type_code") or "").strip()
    return code == "381" or (not code and bool(src.get("preceding_invoice")))


def build(src, locale):
    w = dict(words(locale))
    w.update(PAID_WORDS.get(locale) or PAID_WORDS["en-GB"])
    c = countries.seller_country(src)
    covered = country_page.covers(src)
    sales_tax = c in ("CA", "US")
    if c == "GB" and locale == "en-GB":
        # VAT Notice 700/21 4.1's words on a British seller's page.
        w.update(country_page.UK_WORDS)
    if is_credit_note(src):
        w["invoice"] = w["credit_note"]
        # A credit note numbers and dates itself: Gutschriftsnummer, not Rechnungsnummer.
        w.update(CREDIT_WORDS.get(locale, {}))
    missing = [k for k in REQUIRED if src.get(k) in (None, "", [], {})]
    if missing:
        raise SystemExit("required field(s) missing from the source: %s" % ", ".join(missing))

    cur = src.get("currency")
    seller, buyer = src.get("seller") or {}, src.get("buyer") or {}
    payment = src.get("payment") or {}
    lines = src.get("lines") or []
    if countries.credit_sign(src) < 0:
        # A Spanish rectifying invoice and a Polish correcting invoice state the correction itself, with its
        # sign (Real Decreto 1619/2012 art. 15.5; ustawa o VAT art. 106j ust. 2 pkt 5): minus the quantities
        # the order credits, so every amount that follows is minus too, as in the file beside the page.
        lines = [dict(l, quantity=-Decimal(str(l.get("quantity") or 0))) for l in lines]

    def net_of(line):
        """The line's net: the source's own quantity, price and discount, in the stated rule."""
        if line.get("net") not in (None, ""):
            return float(line["net"])
        return float(doc_amounts.line_amounts(line)["net"])

    # VAT once per category and rate, on the sum of that group's line nets, rounded half up: the
    # rule the XML follows (EN 16931), and a row per rate on the page (VAT Directive Art. 226(8)-(10)).
    exempt = ("AE", "E", "K", "G", "Z", "O")
    half = lambda d: d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if countries.credit_sign(src) < 0 and (src.get("allowances") or src.get("paid_amount")):
        raise SystemExit("a correcting invoice states its amounts with a minus sign; put a discount on the lines "
                         "and leave out allowances and paid_amount (a credit note owes nothing in advance)")
    if sales_tax:
        # Canada and the United States: no VAT groups; the sales taxes come after the lines.
        if src.get("allowances"):
            raise SystemExit("a document-level allowance is not built for a Canadian or US page; give the discount on the lines")
        breakdown = []
        net = float(sum((countries.line_net(l) for l in lines), Decimal(0)))
        vat_amount = float(country_page.sales_tax_total(src))
        paid = half(Decimal(str(src.get("paid_amount") or 0)))
        if paid < 0 or paid > half(Decimal(str(net + vat_amount))):
            raise SystemExit("paid_amount %s is not between 0 and the total: the amount due does not close" % paid)
        mn = dict(allowances=[], line_total=Decimal(str(net)), paid=paid, due=half(Decimal(str(net + vat_amount))) - paid)
    else:
        priced = []
        for i, l in enumerate(lines, 1):
            cat = str(l.get("vat_category") or "S").upper()
            rate = l.get("vat_rate")
            if rate in (None, ""):
                if cat not in exempt:
                    raise SystemExit("line %d has no vat_rate; the order must give it" % i)
                rate = 0
            priced.append(dict(cat=cat, rate=Decimal(str(rate)), net=Decimal(str(net_of(l)))))
        # The money once, for every syntax and the page (skills/_shared/doc_amounts.py): VAT once per category
        # and rate on the sum of that group's line nets less the document's allowances, rounded half up (EN 16931-1
        # BR-CO-13, BR-CO-15, BR-CO-16; VAT Directive Art. 226(8)-(10)).
        mn = doc_amounts.settle(src, priced)
        breakdown = [(cat, rate, half(base), mn["tax"][(cat, rate)]) for (cat, rate), base
                     in sorted(mn["groups"].items(), key=lambda kv: (-kv[0][1], kv[0][0]))]
        net = float(mn["basis"])
        vat_amount = float(mn["tax_total"])
    gross = round(net + vat_amount, 2)

    def rate_text(rate):
        return _number(rate, locale)

    def rate_cell(l):
        """The VAT (GST) rate of the line, or the tax a Canadian or US line carries."""
        if sales_tax:
            return country_page.line_tax_word(l, src, locale, w)
        cat = str(l.get("vat_category") or "S").upper()
        if c == "AU" and cat in ("Z", "E", "O", "G"):
            return w.get("gst_free", "GST-free")
        if cat in ("AE", "K", "G", "E", "O") and not l.get("vat_rate"):
            return "0%s" % country_page.pct_sep(locale)
        return "%s%s" % (rate_text(l.get("vat_rate") or 0), country_page.pct_sep(locale))

    rate_col = covered and (c in country_page.RATE_COLUMN or sales_tax)
    pct_sym = " %" if locale == "fr-FR" else "%"
    if covered:
        pct_sym = country_page.pct_sep(locale)
    ncols = 5 + (1 if rate_col else 0)

    def discount_row(l):
        """The discount under its item (EN 16931-1 BG-27: BT-138 the percentage, BT-136 the amount, BT-139 the
        reason), only when the line has one; a row of two cells, so a reader of the table of lines skips it."""
        if l.get("net") not in (None, ""):
            return ""
        a = doc_amounts.line_amounts(l)
        if not a["discount"]:
            return ""
        label = a["reason"] or w["discount"]
        if a["percent"] is not None:
            label += " %s%s" % (_number(float(a["percent"]), locale), pct_sym)
        return "<tr class='disc'><td class='d' colspan='%d'>%s</td><td class='n'>%s</td></tr>" % (
            ncols - 1, esc(label), amount(float(-a["discount"]), locale))

    def customs(l):
        """An export line's customs code and origin, under its name (EN 16931 BT-158, BT-159)."""
        hs, origin = str(l.get("hs_code") or "").strip(), str(l.get("origin") or "").strip().upper()
        digits = re.sub(r"[\s.]", "", hs)
        if digits.isdigit():  # the Combined Nomenclature writes 8204 11 00, never a decimal point
            hs = " ".join(x for x in (digits[:4], digits[4:6], digits[6:8], digits[8:]) if x)
        words = CUSTOMS.get(locale, CUSTOMS["en-GB"])
        bits = (["%s %s" % (words[0], esc(hs))] if hs else []) + (["%s %s" % (words[1], esc(origin))] if origin else [])
        return ("<br><small>%s</small>" % " · ".join(bits)) if bits else ""

    line_rows = "".join(
        "<tr><td class='d'>%s</td><td class='n'>%s</td><td>%s</td><td class='n'>%s</td>%s<td class='n'>%s</td></tr>%s"
        % (esc(country_page.described(l, locale) if covered else l.get("name", "")) + customs(l),
           esc(_number(l.get("quantity") or 0, locale) if covered else l.get("quantity", "")),
           esc(unit_word(l.get("unit"), locale)), amount(l.get("unit_price"), locale) or "",
           ("<td class='n'>%s</td>" % esc(rate_cell(l))) if rate_col else "", amount(net_of(l), locale) or "",
           discount_row(l))
        for l in lines)

    # The mentions the VAT Directive requires on the page (Art. 226(11) and (11a)).
    categories = {cat for cat, _, _, _ in breakdown}
    mentions = []
    if "AE" in categories:
        mentions.append(REVERSE_CHARGE.get(locale, REVERSE_CHARGE["en-GB"]))
    reasons = [r for r in dict.fromkeys([src.get("exemption_reason")] + [l.get("exemption_reason") for l in lines]) if r]
    mentions += [r for r in reasons if r not in mentions]
    # What the seller's own law adds: Poland's „mechanizm podzielonej płatności” and „metoda kasowa”, Italy's
    # split payment and stamp-duty annotation.
    mentions += [m for m in country_page.extra_mentions(src) if m not in mentions]
    # Art. 230: an invoice in a currency other than the seller's national one states the VAT in
    # the national currency too, at the rate the order gives.
    national = NATIONAL_CURRENCY.get(str(seller.get("country") or "").upper(), "EUR")
    if c in countries.PAGE_ONLY:
        national = cur
    if vat_amount and cur and cur != national:
        rate_x = src.get("exchange_rate")
        if not rate_x:
            raise SystemExit("the invoice is in %s and the seller's national currency is %s: the VAT must "
                             "also be stated in %s (VAT Directive Art. 230). Put the exchange rate the "
                             "order uses in the source as exchange_rate and build again."
                             % (cur, national, national))
        vat_in = w["vat_in"] % national if "%s" in w["vat_in"] else w["vat_in"]
        mentions.append("%s %s %s" % (vat_in, amount(round(vat_amount * float(rate_x), 2), locale), national))

    french = str(seller.get("country") or "").upper() == "FR"
    operation = einvoice_create.operation_of(src) if french else ""
    reform = []
    if french:
        # The reform's mentions (CGI annexe II art. 242 nonies A I 8° bis and 11° bis), as plain text.
        if operation:
            reform.append("%s : %s" % (w.get("operation", "Nature de l'opération"),
                                       FR_OPERATION[operation] if locale == "fr-FR" else operation))
        if src.get("vat_on_debits"):
            reform.append(FR_DEBITS)

    money_of = lambda v: with_currency(amount(v, locale), cur, locale)
    if covered:
        money_of = lambda v: country_page.money_text(amount(v, locale), cur, locale)
    # The percent sign: CLDR French puts a narrow no-break space before it (20 %), German and
    # Swedish a space; the English page writes it close up, as before.
    pct = " %" if locale == "fr-FR" else "%"
    if covered:
        pct = country_page.pct_sep(locale)
    sums, marks = [], {}
    if mn["allowances"]:
        # The sum of the lines, then each allowance on the whole document with its reason (BG-20, BT-97), then
        # the total without tax (BR-CO-13).
        marks[len(sums)] = "linesum"
        sums.append((w["lines_sum"], money_of(float(mn["line_total"]))))
        for al in mn["allowances"]:
            label = al["reason"] or al["code"]
            if al["percent"] is not None:
                label += " %s%s" % (_number(float(al["percent"]), locale), pct_sym)
            marks[len(sums)] = "allow"
            sums.append((label, money_of(float(-al["amount"]))))
    marks[len(sums)] = "net"
    sums.append((w.get("net_total", w["net"]), money_of(net)))
    shown = breakdown
    if c == "AU":
        # An Australian tax invoice states the GST payable; GST-free lines are marked in the table.
        shown = [b for b in breakdown if b[1]] or breakdown[:1]
    for cat, rate, base, vat in shown:
        label = ("%s %s%s" % (w["vat"], rate_text(rate), pct)) if len(shown) == 1 else w["vat_on"] % (rate_text(rate), amount(base, locale))
        sums.append((label, money_of(vat)))
    if sales_tax:
        sums += country_page.sales_tax_rows(src, locale, w, money_of, lambda v: amount(v, locale))
        gross = round(net + vat_amount, 2)
    if mn["paid"]:
        # An amount paid in advance (BT-113) comes off the total with tax; what is left is the amount due (BT-115).
        marks[len(sums)] = "total"
        sums.append((w["total_incl"], money_of(gross)))
        marks[len(sums)] = "paid"
        sums.append((w["paid"] + ((" " + _date(src["paid_date"], locale)) if src.get("paid_date") else ""),
                     money_of(float(-mn["paid"]))))
        marks[len(sums)] = "due"
        sums.append((w["due_pay"], money_of(float(mn["due"]))))
        if src.get("paid_note"):
            mentions.append(str(src["paid_note"]))
    else:
        marks[len(sums)] = "total"
        sums.append((w["total"], money_of(gross)))
        if c == "US" and not is_credit_note(src):
            marks[len(sums)] = "due"
            sums.append((w["balance"], money_of(gross)))

    body = ["<h1>%s %s</h1>" % (esc(w["invoice"]), esc(src.get("number", "")))]
    body.append("<table class='lines'><thead><tr><th class='d'>%s</th><th class='n'>%s</th><th>%s</th><th class='n'>%s</th>%s<th class='n'>%s</th>"
                "</tr></thead><tbody>%s</tbody></table>"
                % (w["description"], w["qty"], w["unit"], w["unit_price"],
                   ("<th class='n'>%s</th>" % esc(w["rate"])) if rate_col else "", w["net"], line_rows))
    body.append("<table class='sum'><tbody>%s</tbody></table>" % "".join(
        "<tr%s><td>%s</td><td class='n'>%s</td></tr>" % (
            (" class='%s'" % " ".join(x for x in (marks.get(i), "gross" if i == len(sums) - 1 else "") if x))
            if (marks.get(i) or i == len(sums) - 1) else "", esc(k), esc(v))
        for i, (k, v) in enumerate(sums)))
    body += ["<p class='note'>%s</p>" % esc(m) for m in mentions]
    if c in ("PL", "ES", "IT") and is_credit_note(src):
        # A Polish correcting invoice names the corrected invoice's KSeF number (art. 106j ust. 2 pkt 2a) and
        # may give the reason (ust. 2a); the Spanish and the Italian page give the reason the file carries
        # (Facturae AdditionalReasonDescription, FatturaPA Causale).
        if c == "PL" and src.get("preceding_ksef_number"):
            body.append("<p class='note'>%s: %s</p>" % (esc(w["ksef_number"]), esc(src["preceding_ksef_number"])))
        if src.get("note"):
            body.append("<p class='note'>%s: %s</p>" % (esc(w["reason"]), esc(src["note"])))
    if c == "IE" and is_credit_note(src) and src.get("note"):
        # An Irish credit note states the reason for the credit (VAT Regulations 2010 reg. 20(5)).
        body.append("<p class='note'>%s: %s</p>" % (esc(w.get("reason", "Reason for credit")), esc(src["note"])))
    elif src.get("note") and not (c in ("PL", "ES", "IT") and is_credit_note(src)):
        # The order's own note (EN 16931 BT-22), which the XML carries: on the page too, as written, so that
        # what the order gives is never on the file alone.
        body.append("<p class='note'>%s</p>" % esc(src["note"]))
    ship = src.get("delivery_address")
    if isinstance(ship, dict) and (ship.get("street") or ship.get("city")):
        # Where the goods go when it is not the buyer's address (BG-15; France 242 nonies A I 7° bis).
        place_to = " ".join(x for x in (ship.get("postcode"), ship.get("city")) if x)
        reform.insert(0, "%s%s%s" % (w.get("delivery_address", "Delivery address"), " : " if locale == "fr-FR" else ": ",
                      ", ".join(x for x in (ship.get("name"), ship.get("street"), place_to, ship.get("country")) if x)))
    if reform:
        body.append("<p class='note'>%s</p>" % "<br>".join(esc(x) for x in reform))
    if french:
        # The payment mentions of Code de commerce L441-9, L441-10 and D441-5, word for word the notes
        # the XML carries (PMD, PMT, AAB).
        legal = [text for code, text in einvoice_create.fr_notes(src) if code in ("PMD", "PMT", "AAB")]
        body.append("<div class='legal'>%s</div>" % "".join("<p>%s</p>" % esc(t) for t in legal))
    # The closing block, one grid of key and value (skills/_shared/page_look.py): the terms, and on an
    # invoice when it falls due and where to pay it, the country's own way first (a Norwegian account and
    # KID, a British sort code), then the IBAN and BIC the order gives. It stands at the foot of a page that
    # has room. A credit note asks for no payment and carries its terms alone.
    pay = []
    if src.get("payment_terms"):
        pay.append((w["terms"], terms_word(src["payment_terms"], locale)))
    credit = is_credit_note(src)
    if src.get("due_date") and not credit:
        pay.append((w["due"], _date(src["due_date"], locale)))
    if covered:
        pay += country_page.bank_rows(src, locale, w)
        if c == "FI" and not credit:
            code = country_page.ids.fi_virtual_barcode(payment.get("iban"), float(mn["due"]), payment.get("reference"),
                                                       src.get("due_date"))
            if code:
                # The bank barcode in its printed form (Finanssiala, Pankkiviivakoodi, version 4).
                pay.append((w["barcode"], code))
    if not credit:
        # A Swedish Bankgiro or PlusGiro number, written the way Bankgirot and PlusGiro print it.
        pay += [("Bankgiro", country_page.ids.se_bankgiro_text(payment["bankgiro"]) if payment.get("bankgiro") else None),
                ("PlusGiro", country_page.ids.se_plusgiro_text(payment["plusgiro"]) if payment.get("plusgiro") else None)]
        pay += [("IBAN", payment.get("iban")), ("BIC", payment.get("bic"))]
    body.append(page_look.closing(pay))

    delivered = w["delivered"]
    if french and locale == "fr-FR" and operation:
        delivered = FR_DELIVERED[operation]
    if covered and c == "NO" and not is_credit_note(src):
        # bokføringsforskriften § 5-1-1 nr. 4: the place of delivery beside its time.
        ship = src.get("delivery_address") if isinstance(src.get("delivery_address"), dict) else {}
        where = ship if (ship.get("street") or ship.get("city")) else buyer
        place = src.get("delivery_place") or ", ".join(x for x in (
            where.get("street"), country_page.place(dict(where, country=where.get("country") or buyer.get("country")))) if x)
        extra_info = [(w["delivery_place"], place)]
    else:
        extra_info = []
    info = [(w["number"], src.get("number")),
            # Spain: the series, where the invoice has one (Real Decreto 1619/2012 art. 6.1 a).
            (w.get("series", "Series"), src.get("series") if c == "ES" else None),
            (w["issue"], _date(src["issue_date"], locale) if src.get("issue_date") else None),
            (w["due"], _date(src["due_date"], locale) if src.get("due_date") else None),
            (delivered, _date(src["delivery_date"], locale) if src.get("delivery_date") else period_text(src, locale)),
            (w["currency"], cur), (w["preceding"], src.get("preceding_invoice")),
            # The date of the invoice a credit note amends (BT-26), so the reference is unambiguous (Art. 219).
            (w["preceding_date"], _date(src["preceding_invoice_date"], locale) if src.get("preceding_invoice_date") else None),
            (w["buyer_reference"], src.get("buyer_reference")),
            (w.get("order_reference", "Order"), src.get("order_reference")),
            # The buyer's SIREN, on French invoices from 1 September 2026 (242 nonies A I 1°).
            (w.get("customer_siren", "Customer SIREN"), spaced_siren(buyer.get("siren")) if french and buyer.get("siren") else None),
            # A Swedish customer's organisationsnummer, when the notes give it: the XML carries it as BT-47.
            (w.get("customer_org"), buyer.get("register_number") if c == "SE" and w.get("customer_org") else None),
            (w["customer_vat"], (country_page.customer_id(buyer, locale, w, c) if covered
                                 else buyer.get("vat_id") or buyer.get("vat"))),
            # Italy: the codice fiscale of a customer who gives one (DPR 633/1972 art. 21 comma 2 f).
            (w.get("customer_cf", "Tax code"), buyer.get("tax_code") if c == "IT" else None)]
    info[4:4] = extra_info
    if covered and c == "FI":
        info += [(w["late_interest"], src.get("late_interest")),
                 (w["complaint"], src.get("complaint_period"))]
    # The seller's contact (BG-6), the same one the XML carries.
    contact = seller.get("contact") if isinstance(seller.get("contact"), dict) else {}
    info += [(w["contact"], contact.get("name") or seller.get("contact_name")),
             (w["phone"], contact.get("phone") or seller.get("phone")),
             (w["email"], contact.get("email") or seller.get("email"))]
    # The town line and the footer's first column are the company's own address, the one its letter and its
    # trade document print (letter.town_line, letter.own_address).
    place = letter.town_line(seller)
    vat_id = seller.get("vat_id") or seller.get("vat")
    if french:
        # A French company's identity, as service-public.fr F31808 lists it: legal form and share
        # capital, SIREN with RCS and its city, SIRET, VAT number.
        siren = spaced_siren(seller.get("siren"))
        tax = einvoice_create.fr_company_line(dict(seller, rcs=None)) \
            + (["%s %s" % (seller["rcs"], siren)] if seller.get("rcs") else (["SIREN %s" % siren] if siren else [])) \
            + (["SIRET %s" % spaced_siret(seller["siret"])] if seller.get("siret") else []) \
            + (["%s %s" % (w["vat_id"], vat_id)] if vat_id else []) \
            + (["%s : %s" % ("Siège social", seller["registered_office"])] if seller.get("registered_office") else []) \
            + country_page.liquidation_line(seller, locale)
    elif covered:
        tax = country_page.footer_tax(seller, locale, w)
    else:
        tax = (["%s %s" % (w["vat_id"], vat_id)] if vat_id else []) \
            + (["%s %s" % (w["tax_number"], seller["tax_number"])] if seller.get("tax_number") else []) \
            + letter.company_lines(seller, locale) + country_page.liquidation_line(seller, locale)
    # The seller's further particulars: lines the order gives for a fact with no field of its own, as written.
    tax = list(tax) + letter.further_lines(seller)
    bank = [x for x in (payment.get("bank"),
                        ("Bankgiro %s" % country_page.ids.se_bankgiro_text(payment["bankgiro"])) if payment.get("bankgiro") else None,
                        ("PlusGiro %s" % country_page.ids.se_plusgiro_text(payment["plusgiro"])) if payment.get("plusgiro") else None,
                        ("IBAN %s" % payment["iban"]) if payment.get("iban") else None,
                        ("BIC %s" % payment["bic"]) if payment.get("bic") else None) if x]
    page = letter.sheet_html(
        locale, "%s %s" % (w["invoice"], src.get("number", "")), "nodejam-page-builder", seller.get("name", ""),
        " · ".join(x for x in (seller.get("name"), seller.get("street"), place) if x),
        "<br>".join(esc(x) for x in buyer_address(src)),
        info, "".join(body),
        [letter.own_address(seller, (src.get("buyer") or {}).get("country")), tax, bank],
        **({"paper": paper_of(locale)} if _SHEET_PAPER else {}))
    # An e-mail address too long for its column breaks where an address may: after its @, else before one of
    # its points, not inside a word (INFO_FIT keeps the domain whole wherever it fits).
    mail = esc(contact.get("email") or seller.get("email") or "")
    if "@" in mail:
        name, _, domain = mail.partition("@")
        page = page.replace("<dd>%s</dd>" % mail, "<dd>%s@<wbr>%s</dd>" % (name.replace(".", "<wbr>."),
                                                                        domain.replace(".", "<wbr>.")), 1)
    return grouped_info(page, {esc(w[k]) for k in ("contact", "phone", "email")})


# The two groups of the information block share one label column, so every value starts on one edge, as
# long as the seller's contact fits that way. A contact value that would take a second line (a long e-mail
# address) is dealt with in this order: up to 8 % too long, it is set that much smaller and nothing moves;
# longer, the contact group falls back to a label column as wide as its own longest label, which is usually
# the narrower one, and the address gets the room (again set up to 8 % smaller if that is all it lacks);
# longer still, it breaks after its @ and keeps its domain whole, and only a domain wider than the column
# breaks before a point. Run where the block stands, before the sheet's own script measures how far down
# the block reaches.
INFO_FIT = """<script>
(function(){const g=document.querySelectorAll('.info dl');if(g.length<2)return;
const col=d=>Math.max(...Array.from(d.querySelectorAll('dt'),e=>e.getBoundingClientRect().width));
const own=[col(g[0]),col(g[1])],both=Math.max(own[0],own[1]);
const set=(d,w)=>{d.style.gridTemplateColumns=w+'px minmax(0,1fr)'};
set(g[0],both);set(g[1],both);
const dd=Array.from(g[1].querySelectorAll('dd'));
const line=parseFloat(getComputedStyle(dd[0]).lineHeight)||17;
const wraps=e=>e.getBoundingClientRect().height>line*1.5;
const wide=(e,x)=>{const p=document.createElement('span');p.textContent=x;
p.style.cssText='position:absolute;visibility:hidden;white-space:nowrap';e.appendChild(p);
const w=p.getBoundingClientRect().width;p.remove();return w};
const over=e=>wide(e,e.textContent)/e.getBoundingClientRect().width;
const tighten=e=>{const k=over(e);e.textContent=e.textContent;e.style.whiteSpace='nowrap';
e.style.fontSize=(parseFloat(getComputedStyle(e).fontSize)/k*0.995)+'px'};
let long=dd.filter(wraps);if(!long.length)return;
if(long.every(e=>over(e)<=1.08)){long.forEach(tighten);return}
if(own[1]<both)set(g[1],own[1]);
for(const e of dd.filter(wraps)){const t=e.textContent,at=t.indexOf('@');
if(over(e)<=1.08){tighten(e)}
else if(at>0&&wide(e,t.slice(at+1))<=e.getBoundingClientRect().width){const d=document.createElement('span');
d.style.whiteSpace='nowrap';d.textContent=t.slice(at+1);e.textContent=t.slice(0,at+1);
e.appendChild(document.createElement('wbr'));e.appendChild(d)}}})();
</script>"""


def grouped_info(page, contact_labels):
    """The information block in two groups, the way a DIN 5008 block sets its lines of communication apart
    from its references: the document's data, then the seller's contact (name, telephone, e-mail). The
    groups share one label column while the contact fits (INFO_FIT); a contact value that would wrap gets
    the contact group a label column of its own, so a short "E-Mail" is not pushed out by a long
    "Ursprungsrechnung vom" and the address has the room the block can give it; a near miss is set a
    little smaller instead of broken."""
    found = re.search(r'<dl class="info">(.*?)</dl>', page, re.S)
    if not found:
        return page
    rows = re.findall(r"<div><dt>.*?</dt><dd>.*?</dd></div>", found.group(1), re.S)
    label = lambda row: re.match(r"<div><dt>(.*?)</dt>", row, re.S).group(1)
    groups = [[r for r in rows if label(r) not in contact_labels], [r for r in rows if label(r) in contact_labels]]
    return page[:found.start()] + '<div class="info">%s</div>' % "".join(
        "<dl>%s</dl>" % "".join(g) for g in groups if g) + (INFO_FIT if all(groups) else "") + page[found.end():]


def buyer_address(src):
    """The buyer's address as the letter to the same buyer writes it, one string per line: the lines the
    buyer's post office reads (skills/_shared/letter.py postal_lines: 9000 GENT, 8011 AA  ZWOLLE, LEEDS
    over LS1 1AA), ending with the country in capitals when the invoice goes abroad."""
    return letter.postal_lines(src.get("buyer") or {}, (src.get("seller") or {}).get("country"))


def esc(value):
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def period_text(src, locale):
    """A period of supply, 01.09.2026 – 30.09.2026, when the order gives one instead of a date."""
    per = src.get("delivery_period") if isinstance(src.get("delivery_period"), dict) else {}
    if per.get("from") and per.get("to"):
        return "%s – %s" % (_date(per["from"], locale), _date(per["to"], locale))
    return None


# ---- the country letter layouts --------------------------------------------------------------------
# An invoice is one of the seller's letters, so it sits where the seller's country puts a letter: the
# address in that country's envelope window and margins, from skills/_shared/letter.py (LAYOUTS, with the
# sources each rests on). A country with no layout there keeps DIN 5008:2020 Form B.

def layout_of(src):
    """(layout id, layout or None) for the seller's country; "layout" in the order picks one by name."""
    return letter.letter_layout({"sender": src.get("seller") or {}, "layout": src.get("layout")})


# The information block on every invoice page: one or two groups (grouped_info), each of two columns, the
# labels as wide as the group's longest label, so a label never wraps, and the values in what the block has
# left, wrapping inside their own column (an address too long for it breaks where it may, and only as a
# last resort where it must). The block's width is set where the page is laid out, so its right edge is the
# text's right edge, the one the table ends on, and nothing passes it.
INFO_GRID = (".info dl{display:grid;grid-template-columns:max-content minmax(0,1fr);column-gap:3mm}"
             ".info dl+dl{margin-top:1.6mm}"
             ".info div{display:contents}.info dt{width:auto;white-space:nowrap}"
             ".info dd{min-width:0;overflow-wrap:anywhere}")


def form_b_css(paper="A4"):
    """DIN 5008 Form B: the information block still starts 125 mm across; it ends on the text's right
    margin (20 mm), not 10 mm past it."""
    g = letter.GEOMETRY
    return "\n.info{width:%smm}%s\n" % (round(letter.PAPER_MM[paper][0] - g["right"] - g["info_x"], 2), INFO_GRID)


def layout_css(lay):
    """The Form B sheet moved onto a window layout: the shared letter's own arithmetic (skills/_shared/letter.py
    layout_css, which trade documents use too), with this page's grouped information block. Every number is
    the layout's own; none is restated here."""
    return letter.layout_css(lay, INFO_GRID)


def on_layout(html, src):
    lid, lay = layout_of(src)
    paper = "Letter" if "@page{size:Letter" in html else "A4"
    if not lay:
        html = html.replace("</style>", form_b_css(paper) + "</style>", 1)
        return page_look.dress(html, None, paper)
    # The sheet on the layout's window, margins and information block: the shared letter's own (on_layout).
    html = letter.on_layout(html, lay, INFO_GRID)
    # The look last: type, spacing and rules from the library's look file, the closing block at the foot.
    return page_look.dress(html, lay, paper)


# The paper of the page's language: US Letter in the United States and Canada (ANSI, and Canada's P4
# size, which Letter fits), A4 elsewhere (ISO 216). The shared letter sheet sets it when it knows the
# locale; the page builder makes sure of it for its own pages.
LETTER_LOCALES = ("en-US", "en-CA", "fr-CA")
# The shared sheet takes the paper (paper="Letter") where it knows it; an older one is made Letter here.
_SHEET_PAPER = "paper" in inspect.signature(letter.sheet_html).parameters
_PRINT_PAPER = "paper" in inspect.signature(letter.print_pdf).parameters


def paper_of(locale):
    return "Letter" if locale in LETTER_LOCALES else "A4"


def paper_for(html, locale):
    if locale in LETTER_LOCALES and "size:A4" in html:
        html = html.replace("@page{size:A4;margin:0}", "@page{size:Letter;margin:0}") \
                   .replace("html,body{width:210mm}", "html,body{width:215.9mm}") \
                   .replace("min-height:297mm", "min-height:279.4mm")
    return html


def print_pdf(html, pdf, paper="A4"):
    """Print the page with the app's own Chromium, or with Playwright outside the app, on the page's
    paper: the app's printer honours the CSS page size (preferCSSPageSize), Playwright is told it."""
    if _PRINT_PAPER:
        try:
            return letter.print_pdf(html, pdf, paper=paper)
        except RuntimeError as e:
            raise SystemExit(str(e))
    if paper == "Letter" and not shutil.which("nodejam-print"):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            sync_playwright = None
        if sync_playwright is not None:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(args=["--no-sandbox"])
                page = browser.new_page()
                page.goto(Path(html).resolve().as_uri())
                page.pdf(path=str(pdf), prefer_css_page_size=True, print_background=True)
                browser.close()
            return "playwright, Letter"
    try:
        return letter.print_pdf(html, pdf)
    except RuntimeError as e:
        raise SystemExit(str(e))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("out", help="the page: .html, or .pdf to build and print in one run")
    ap.add_argument("--locale", default=None)
    ap.add_argument("--no-facturx", action="store_true",
                    help="print the page alone, without the invoice XML inside it")
    a = ap.parse_args()
    src = json.loads(Path(a.source).read_text())
    out = Path(a.out)
    # Nothing given is dropped: an unknown key or a value of the wrong shape stops the build here.
    spec_guard.guard(src, Path(__file__).resolve().parents[1] / "spec.fields.json", "order's data file")
    spec_guard.output_guard(out, __file__, "invoice")
    # The company's own particulars, written once in the person's folder: what the data file leaves out.
    company.apply(src, a.source, "e-invoice")
    if countries.misplaced_numbers(src):
        raise SystemExit("; ".join(countries.misplaced_numbers(src)))
    xml = None
    syntax = "cii"
    if out.suffix.lower() == ".pdf" and not a.no_facturx:
        # The XML first, from the same source: what it refuses, the page is not printed for. Its syntax
        # is the seller country's: CII inside a Factur-X PDF, Peppol BIS UBL or Finvoice beside the page,
        # or none where EN 16931 does not apply (Australia, Canada, the United States).
        xml, summary, syntax = einvoice_create.document_xml(src)
        for warning in summary.get("warnings") or []:
            print("WARNING: %s" % warning)
    # The seller's own company particulars (register, seat, capital): what the order does not give, the
    # pack check fails; what it declares unknown, the page leaves out and the reply must say.
    for warning in countries.particulars.builder_warnings(src):
        print("WARNING: %s" % warning)
    derived, why = locale_of_order(src)
    locale = derived
    if a.locale and a.locale != derived:
        locale = a.locale
        print("WARNING: --locale %s disagrees with the order, which is %s (%s). The page carries the "
              "words of %s and the pack check fails that." % (a.locale, derived, why, a.locale))
    elif a.locale:
        locale = a.locale
    else:
        print("locale %s, from %s" % (derived, why))
    locale = page_locale_for(locale)
    html = out if out.suffix.lower() != ".pdf" else out.with_suffix(".html")
    html.write_text(on_layout(paper_for(build(src, locale), locale), src))
    how = ""
    if out.suffix.lower() == ".pdf":
        # A page that runs to a second page is printed once more with its running line (page_look).
        how = " printed by " + page_look.print_pages(html, out, paper_of(locale), print_pdf)
    print("%s -> %s%s (locale %s, %d line(s))"
          % (a.source, html, how, locale, len(src.get("lines") or [])))
    if xml is not None and syntax in countries.NATIONAL_NAMES:
        # Spain, Italy, Poland: the file the state takes, beside the page. None of them is sent, and the
        # Facturae is not signed.
        out.with_suffix(".xml").write_bytes(xml)
        print("%s: %s beside the page, %s; %s" % (
            out.with_suffix(".xml").name, countries.NATIONAL_NAMES[syntax],
            "a credit note" if is_credit_note(src) else "an invoice",
            {"facturae": "unsigned, so no public entry point takes it as it is",
             "fatturapa": "not sent to the Sistema di Interscambio", "ksef": "not sent to KSeF"}[syntax]))
    elif xml is not None and syntax in ("ubl", "si-ubl", "finvoice", "ebinterface"):
        # Peppol BIS Billing 3.0 (EHF in Norway), Finvoice or ebInterface travels as XML on its own; the page
        # is its readable copy, printed beside it.
        out.with_suffix(".xml").write_bytes(xml)
        print("%s: %s beside the page, %s" % (out.with_suffix(".xml").name,
                                              {"finvoice": "Finvoice 3.0", "ebinterface": "ebInterface 6.1",
                                               "si-ubl": "SI-UBL 2.0 (NLCIUS)"}.get(
                                                  syntax, "Peppol BIS Billing 3.0 (UBL)"),
                                              "a credit note" if is_credit_note(src) else "an invoice"))
    elif xml is not None:
        # One file for France and Germany: Factur-X / ZUGFeRD 2, the page as PDF/A-3 with the XML in it.
        # The same XML is written beside it for a buyer who takes the XML alone (XRechnung).
        out.with_suffix(".xml").write_bytes(xml)
        title = re.search(r"<title>(.*?)</title>", html.read_text())
        level, name = facturx_pdf.embed(out, xml, out, unescape(title.group(1)) if title else "", locale)
        print("%s: Factur-X / ZUGFeRD %s, %s inside (PDF/A-3); %s beside it"
              % (out.name, level, name, out.with_suffix(".xml").name))


if __name__ == "__main__":
    main()
