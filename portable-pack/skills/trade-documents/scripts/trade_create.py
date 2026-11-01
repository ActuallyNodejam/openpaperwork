#!/usr/bin/env python3
"""Create a quotation, order confirmation, delivery note, pro forma invoice or purchase order from a JSON spec.

Usage: trade_create.py spec.json OUTPUT.docx|OUTPUT.xlsx|OUTPUT.pdf

Spec (see templates/ for one example per document):
{
  "type": "quotation" | "order_confirmation" | "delivery_note" | "proforma_invoice" | "purchase_order",
  "language": "en",   # the customer's language: the one they wrote to you in; leave out to use the seller's country
  "number": "Q-2026-0187", "issue_date": "2026-10-15", "currency": "SEK",
  "seller": {"name": "...", "street": "...", "postcode": "...", "city": "...", "country": "SE", "vat_id": "SE...",
             "email": "...", "phone": "...",
             "registered_office": "Gothenburg", "register": "Amtsgericht ...", "register_number": "556123-4567",
             "managing_directors": ["..."],
             "further": ["A particular the company's papers carry that has no field here, one line each"]},
  "buyer":  {"name": "...", "street": "...", "postcode": "...", "city": "...", "country": "...", "vat_id": "..."},
  "deliver_to": {"name": "...", "street": "...", "postcode": "...", "city": "...", "country": "..."},
  "references": [{"label": "Your enquiry", "value": "12 October 2026"}],
  "dates": [{"label": "Valid until", "value": "2026-11-14"}],
  "delivery_terms": {"rule": "DAP", "place": "Malmö, Sweden"}, "transport": "road" | "sea" | "air" | "rail",
  "payment_terms": "30 days net from invoice date",
  "bank": {"bank": "...", "iban": "...", "bic": "..."},   # or "account" where no IBAN exists
  "lines": [{"code": "KG-200", "description": "...", "quantity": 12, "unit": "pcs", "unit_price": 1890.00,
             "discount_percent": 0, "vat_rate": 25, "delivered": 12, "hs_code": "8419.81", "origin": "Italy"}],
  "packages": 3, "gross_weight_kg": 148.5, "notes": ["..."],
  "quotation": "Q-2026-0187", "requested_delivery_date": "2026-11-02",   # a purchase order
  "tax_name": "QST",   # optional: the tax's own name when it is not the market's usual one
  "layout": "din5008"  # optional: DIN 5008 Form B, or a letter layout by name (uk, nl, es), instead of the sender's country's
}

A purchase order is the buyer's letter to its supplier, with the fields of OASIS UBL 2.1 Order: the buyer
(BuyerCustomerParty) issues it and the seller (SellerSupplierParty) receives it, so the buyer heads the page
and signs the footer and the seller sits in the address field. It names the supplier's quotation it
answers (QuotationDocumentReference), the requested delivery date (Delivery/RequestedDeliveryPeriod) and
the delivery address (Delivery/DeliveryAddress; the buyer's own address when "deliver_to" is not given), and
an Incoterms 2020 term when the goods cross a border. Its language is the one the spec names, else the
buyer's country.

Where each part comes from:
- The page: the letter of the country the document is sent from, the sheet its invoice and its letter sit
  on (skills/_shared/letter.py, LAYOUTS and letter_layout): the address inside that country's envelope
  window, on the left in the Nordics, the Netherlands, Austria, the United Kingdom, Ireland and Australia,
  on the right in Belgium, Spain, Italy and Poland, in a No. 10 window on US Letter in the United States
  and Canada, with that layout's margins; the document's own data in the information block beside the
  window (left of a window on the right, above a No. 10 window). Germany, Sweden, France and any country
  with no layout there keep DIN 5008:2020 Form B: the window address field on the left with its return
  line, the block from 125 mm, the text on one 25 mm edge. A layout is used on its own paper; a document
  whose language asks for the other paper keeps Form B. "layout" in the spec picks a layout by name.
  Word and Excel follow the PDF: the same margins, window and block in Word, the same side for the
  address in a workbook. The two rules an invoice page follows hold here too: the address is
  written as the recipient's post office reads it (letter.postal_lines: LEEDS over LS1 1AA, 9000 GENT,
  28001 MADRID, the country last and in capitals when the document goes abroad), and the information
  block ends on the text's right edge, where the table ends, or before the window, its labels on one
  line each. The sender's own address in the footer is the company's imprint, not an address for the
  post: ordinary case, the same on its letter and its invoice (letter.own_address: 28001 Madrid, 40121
  Bologna (BO), the country last when the document goes abroad); the return line, the delivery line and a
  workbook's footer row are one line each with the same town line (place_line, letter.town_line).
- Numbers and dates: Unicode CLDR for the document's language. Language: the customer's when the
  spec names one, else the seller's country (in Belgium the region its postcode lies in). Words
  (skills/_checks/trade_words.json) for British, Irish, American, Canadian and Australian English,
  Canadian and Belgian French and the French of France, German and Austrian German, Dutch and Belgian Dutch, Swedish, Danish,
  Norwegian (bokmål), Finnish, Spanish, Italian and Polish; the tax is named as each market names it
  (VAT, moms, MVA, ALV, btw, TVA, USt., IVA, sales tax, GST/HST, TPS/TVH, GST), or as "tax_name" in the
  spec says.
- Paper: A4 (ISO 216), or US Letter for the United States and Canada, by the document's language.
- Company details in the footer: Directive (EU) 2017/1132 Art. 26 (register, number, legal form,
  registered office), GmbHG 35a for a German GmbH's managing directors, aktiebolagslagen 28 kap. 5 §;
  Belgium's enterprise number with RPR or RPM and the court (art. 2:20), the Dutch KvK number
  (Handelsregisterwet 2007 art. 27), Austria's FN and Firmenbuch court (UGB § 14), Ireland's number,
  place of registration and every director (Companies Act 2014 s.151); Spain's registered office and
  Registro Mercantil entry, and the paid-up capital beside the subscribed when the capital is named
  (Código de Comercio art. 24); Italy's seat, register office and number, the capital paid up and a
  sole shareholder (Codice civile art. 2250); Poland's seat and address, registry court and KRS number,
  NIP and share capital, and an S.A.'s paid-up capital (Kodeks spółek handlowych art. 206 § 1, art. 374 § 1).
  When a company's seller data lacks them the summary warns, and the reply must say so.
- The delivery term: Incoterms 2020, a rule, a named place and the words "Incoterms 2020"; the script
  refuses a rule that does not exist or a sea-only rule for goods that do not travel by sea.
- The arithmetic: each line net is quantity x unit price less the discount, rounded half-up to two
  decimals; VAT is calculated once per rate on the sum of that rate's line nets; the totals follow.
Every key the builder reads is in spec.fields.json beside SKILL.md. A key that is not there, a value of another
shape (notes as one string, an amount as text, a VAT rate written 0.2 for 20 percent) or a key this kind of document
has no place for (a bank account on a purchase order, the recipient's e-mail address) stops the build with the
key's name (skills/_shared/spec_guard.py): nothing given is left off the page.
A workbook gets live formulas with their results saved. A delivery note shows quantities ordered,
delivered and outstanding and never a price. Prints a JSON summary with the totals. Needs
python-docx or openpyxl for Word and Excel; the PDF prints through Chromium.
"""
import json
import re
import sys
import zipfile
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
import letter  # noqa: E402
import page_look  # noqa: E402
import company  # noqa: E402
import doc_amounts  # noqa: E402
import spec_guard  # noqa: E402

FIELDS = Path(__file__).resolve().parents[1] / "spec.fields.json"

INCOTERMS = {'EXW': 'any', 'FCA': 'any', 'CPT': 'any', 'CIP': 'any', 'DAP': 'any', 'DPU': 'any', 'DDP': 'any',
             'FAS': 'sea', 'FOB': 'sea', 'CFR': 'sea', 'CIF': 'sea'}
TYPES = ('quotation', 'order_confirmation', 'delivery_note', 'proforma_invoice', 'purchase_order')
FONT = 'Arial'

# The words per locale and the labels a spec's own references and dates use most live in one table the
# TRADE-LANG check reads too (skills/_checks/trade_words.json), so the builder and the check never drift.
_TABLE = json.loads((Path(__file__).resolve().parents[2] / "_checks" / "trade_words.json").read_text())
WORDS = _TABLE["words"]
UNIT_ALIASES = ('pcs', 'pc', 'pce', 'piece', 'pieces', 'st', 'stk', 'stck')

# A label written in one language prints in the document's; a label not in the table prints as written.
LABELS = _TABLE["labels"]
LABEL_INDEX = {v.casefold(): row for row in LABELS for v in row.values()}


def r2(x):
    return Decimal(str(x)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def qty(x):
    d = Decimal(str(x))
    return str(d.quantize(Decimal(1))) if d == d.to_integral_value() else str(d.normalize())


def delivery_term(spec):
    t = spec.get('delivery_terms')
    if not t:
        return None
    rule, place = t.get('rule', '').upper().strip(), (t.get('place') or '').strip()
    if rule not in INCOTERMS:
        raise ValueError('delivery_terms.rule %r is not an Incoterms 2020 rule; use one of %s' % (rule, ', '.join(INCOTERMS)))
    if not place:
        raise ValueError('delivery_terms.place is needed: an Incoterms rule is always followed by a named place')
    if INCOTERMS[rule] == 'sea' and spec.get('transport', 'sea') not in ('sea', 'inland waterway'):
        raise ValueError('%s is for sea and inland waterway transport only; for %s use FCA, CPT, CIP, DAP, DPU or DDP' % (rule, spec.get('transport')))
    return '%s %s, Incoterms® 2020' % (rule, place)   # ICC's own form of the name, with its mark


def is_order(spec):
    return spec.get('type') == 'purchase_order'


def sender(spec):
    """Whose letter it is: the seller's, or for a purchase order the buyer's."""
    return spec['buyer'] if is_order(spec) else spec['seller']


def recipient(spec):
    return spec['seller'] if is_order(spec) else spec['buyer']


def delivery_address(spec):
    """Where the goods go: deliver_to, or for a purchase order the buyer's own address."""
    if spec.get('deliver_to'):
        return spec['deliver_to']
    return spec['buyer'] if is_order(spec) else None


def crosses_border(spec):
    """The goods leave the seller's country: the case where a purchase order owes an Incoterms term."""
    origin = country(spec['seller'].get('country'))
    dest = country((delivery_address(spec) or spec['buyer']).get('country'))
    return bool(origin and dest and origin != dest)


# The countries whose words the table has, and the English or French of each market.
COUNTRY_LOCALE = dict(letter.COUNTRY_LOCALE, NO='nb-NO', FI='fi-FI', US='en-US', CA='en-CA', AU='en-AU',
                      NL='nl-NL', AT='de-AT', IE='en-IE', ES='es-ES', IT='it-IT', PL='pl-PL', FR='fr-FR')
COUNTRY_NAMES = {'norway': 'NO', 'norge': 'NO', 'finland': 'FI', 'suomi': 'FI', 'united states': 'US', 'usa': 'US',
                 'united states of america': 'US', 'canada': 'CA', 'australia': 'AU', 'españa': 'ES', 'espana': 'ES',
                 'italia': 'IT', 'polska': 'PL'}
EN_MARKET = {'US': 'en-US', 'CA': 'en-CA', 'AU': 'en-AU', 'GB': 'en-GB', 'IE': 'en-IE'}
# Dutch, French and German written for a market of their own: Belgian Dutch and French, Austrian German.
MARKET = {('nl', 'NL'): 'nl-NL', ('nl', 'BE'): 'nl-BE', ('fr', 'BE'): 'fr-BE', ('fr', 'CA'): 'fr-CA',
          ('fr', 'FR'): 'fr-FR',
          ('de', 'AT'): 'de-AT', ('de', 'DE'): 'de-DE', ('es', 'ES'): 'es-ES', ('it', 'IT'): 'it-IT',
          ('pl', 'PL'): 'pl-PL'}


def belgian_locale(p):
    """Belgium writes in the language of the region its business sits in (the Flemish decree of 19 July 1973,
    the French Community decree of 30 June 1982): bpost postcodes 1500-3999 and 8000-9999 are Flanders, 1300-1499
    and 4000-7999 Wallonia, 1000-1299 Brussels-Capital, which writes either (French here unless the spec names
    Dutch). The German-speaking municipalities (4700-4791) are written in French here; name the language."""
    code = re.sub(r'\D', '', str(p.get('postcode') or ''))[:4]
    n = int(code) if len(code) == 4 else 0
    return 'nl-BE' if 1500 <= n <= 3999 or 8000 <= n <= 9999 else 'fr-BE'


def country(value):
    return letter.country_code(value) or COUNTRY_NAMES.get(str(value or '').strip().lower(), '')


def named_locale(named, spec):
    """The table's locale for a language the spec names: an exact tag first (en-US), then the language,
    English and French taken in the parties' own market."""
    tag = named.strip().replace('_', '-')
    for loc in WORDS:
        if loc.lower() == tag.lower():
            return loc
    base = {'no': 'nb', 'nn': 'nb', 'nob': 'nb'}.get(tag.split('-')[0].lower(), tag.split('-')[0].lower())
    codes = [country((spec.get(r) or {}).get('country')) for r in ('seller', 'buyer')]
    if base == 'en':
        return next((EN_MARKET[c] for c in codes if c in EN_MARKET), 'en-GB')
    marked = next((MARKET[(base, c)] for c in codes if (base, c) in MARKET), None)
    if marked:
        return marked
    if base == 'fr':
        return 'fr-FR'                 # French with no Belgian or Canadian party: France's own words
    return next((loc for loc in WORDS if loc.split('-')[0] == base), None)


def language(spec):
    """The seller's letters are in the customer's language, else the seller's country's. A purchase order
    is the buyer's letter: the language the spec names, else the buyer's country."""
    order = is_order(spec)
    named = str(spec.get('language') or (spec['seller'] if order else spec.get('buyer') or {}).get('language') or '').strip()
    if named:
        loc = named_locale(named, spec)
        if loc:
            return loc, ('the language the order names, %s' if order else "the customer's language %s") % named
        return 'en-GB', "the customer's language %s, which the library writes in English" % named
    for role in (('buyer', 'seller') if order else ('seller', 'buyer')):
        code = country((spec.get(role) or {}).get('country'))
        if code == 'BE':
            loc = belgian_locale(spec[role])
            return loc, "the %s's region in Belgium (postcode %s)" % (role, spec[role].get('postcode'))
        if code:
            return COUNTRY_LOCALE.get(code, 'en-GB'), "the %s's country %s" % (role, code)
    return 'en-GB', 'no language and no country given'


# What a country's own law asks a company to print on a quotation or an order, beside Art. 26 of the Directive.
COMPANY_LAW = {'BE': 'Code des sociétés et des associations art. 2:20',
               'NL': 'Handelsregisterwet 2007 art. 27, Burgerlijk Wetboek 2:186',
               'AT': 'Unternehmensgesetzbuch § 14', 'IE': 'Companies Act 2014 s.151(2)',
               # Wave 9: "toda su documentación, correspondencia, notas de pedido y facturas" (art. 24.1);
               # "negli atti e nella corrispondenza" (art. 2250); "pisma i zamówienia handlowe" (art. 206 § 1,
               # and art. 374 § 1 for a spółka akcyjna).
               'ES': 'Código de Comercio art. 24', 'IT': 'Codice civile art. 2250',
               'PL': 'Kodeks spółek handlowych art. 206 § 1'}


def company_law(who, code):
    """The country's own rule for this company: a Polish spółka akcyjna reads art. 374 § 1, not art. 206."""
    form = letter.legal_form(who).replace('.', '').replace(' ', '').upper()
    if code == 'PL' and form == 'SA':
        return 'Kodeks spółek handlowych art. 374 § 1'
    return COMPANY_LAW.get(code)


# What the person's files do not give stays off the page and is said in the reply, the invoice rule's way: the
# document's own number before it is given one, and the bank. A marker in its place is no fact: a timed pro forma
# printed "TBC" as its number and its bank (c07, 2026-10-25), because the builder took no number as unknown.
OPEN = ('number', 'bank')
MARKER = re.compile(r"\s*(?:\[[^\]]*\]|tbc|tbd|tba|n/?a|\?+|x{3,}|-+|to be (?:confirmed|added|assigned|advised|agreed))\s*",
                    re.I)


def open_keys(spec):
    """The top-level keys the data file declares unknown; a marker standing in for one stops the build."""
    listed = spec.get('unknown') or []
    unknown = [listed] if isinstance(listed, str) else list(listed)
    wrong = [k for k in unknown if k not in OPEN]
    if wrong:
        raise ValueError('"unknown" holds %s; at the top it takes %s, and a party\'s particulars go in that '
                         'party\'s own "unknown"' % (', '.join(map(repr, wrong)), ' and '.join(OPEN)))
    values = [('number', spec.get('number'))] + [('bank.' + k, v) for k, v in (spec.get('bank') or {}).items()]
    for key, value in values:
        if isinstance(value, str) and value.strip() and MARKER.fullmatch(value):
            raise ValueError('%s is %r, a marker and no fact: leave it out, list %r in "unknown" (printed as '
                             'nothing) and say in your reply that the person fills it in' % (key, value, key.split('.')[0]))
    return set(unknown)


def company_warning(spec):
    """The register details a company's quotation or order must carry that the files do not give, or None.
    The script says what is missing; it never fills a number in."""
    who = sender(spec)
    code = country(who.get('country'))
    missing = letter.company_missing(who)
    if code == 'IE':
        # Companies Act 2014 s.151(1) names every director on a business letter; a quotation, an order form
        # or a delivery note falls under s.151(2): name and legal form, place and number, registered office.
        missing = [m for m in missing if not m.startswith('managing_directors')]
    if not missing:
        return None
    law = 'Directive (EU) 2017/1132 Art. 26' + ('; %s' % company_law(who, code) if code in COMPANY_LAW else '')
    return ('the %s is a company and its letters must state %s (%s); they are not in the files: say so in your reply'
            % ('buyer' if is_order(spec) else 'seller', ', '.join(missing), law))


def layout_of(spec, paper=None):
    """(layout id, layout or None): the letter layout of the country the document is sent from, the call an
    invoice makes for its seller (letter.letter_layout); "layout" in the spec picks one by name. None is DIN
    5008:2020 Form B. A layout is used on its own paper: a document whose language asks for the other paper (a
    US seller writing Spanish on A4, a British one writing en-US on Letter) keeps the Form B positions."""
    lid, lay = letter.letter_layout({'sender': sender(spec), 'layout': spec.get('layout')})
    if lay and paper and lay['paper'] != paper:
        return 'din5008-b', None
    return lid, lay


def own(p):
    """A party with its country as a code, so the shared letter reads a country written out (Norge, Suomi)."""
    return dict(p, country=country(p.get('country')) or p.get('country'))


def place_line(p):
    """Town and postcode on one line, for an address in running print: the return line of a Form B page, the
    delivery line, a workbook's footer row and the footer's first column. One form for every pack
    (letter.town_line): the postcode after the town in the United States, Canada, Australia, the United
    Kingdom and Ireland (Manchester M17 1AA), before it elsewhere, Italy's province after the town (40121
    Bologna (BO)). The address field alone is written as the post office reads it (letter.postal_lines)."""
    return letter.town_line(own(p))


class Data(tuple):
    """(lines, vat, net, tax, gross) as before, with .money: the whole settlement (skills/_shared/doc_amounts.py)
    for the sum of lines, the allowances on the document and the amount paid in advance."""


def compute(spec):
    """Line nets, VAT per rate and totals, as the EN 16931 invoice rules do it: a line is quantity x price less
    its discount (BG-27), the document's allowances (BG-20) come off the taxable amounts, VAT is worked out once
    per rate, and an amount paid in advance (BT-113) comes off the total to leave the amount due (BT-115)."""
    lines = []
    for i, l in enumerate(spec['lines'], 1):
        a = doc_amounts.line_amounts(dict(l, unit_price=l.get('unit_price', 0)), i)
        lines.append(dict(l, net=a['net'], disc=a['discount'], base=a['base'], pct=a['percent'], disc_reason=a['reason'],
                          rate=Decimal(str(l.get('vat_rate', 0)))))
    if spec.get('paid_amount') and spec.get('type') not in ('order_confirmation', 'proforma_invoice'):
        raise ValueError('an amount paid in advance (paid_amount) belongs on an order confirmation or a pro forma '
                         'invoice; a %s asks for no payment' % str(spec.get('type')).replace('_', ' '))
    try:
        money = doc_amounts.settle(spec, [dict(cat='S', rate=l['rate'], net=l['net']) for l in lines])
    except SystemExit as exc:
        raise ValueError(str(exc))
    vat = [(rate, money['groups'][('S', rate)], money['tax'][('S', rate)])
           for rate in sorted({l['rate'] for l in lines}, reverse=True)]
    data = Data((lines, vat, money['basis'], money['tax_total'], money['grand']))
    data.money = money
    return data


class Page:
    """The document's language and the forms and words that follow from it."""

    def __init__(self, spec):
        self.locale, self.why = language(spec)
        self.w = dict(WORDS[self.locale], **doc_amounts.WORDS.get(self.locale, doc_amounts.WORDS['en-GB']))
        self.w['cols'] = dict(self.w['cols'], Discount=self.w['discount'])
        self.spec = spec
        self.paper = letter.paper(self.locale)
        # The sender's country's letter layout, or None for DIN 5008 Form B; how: where the information block
        # goes on it ("beside" the window on Form B and on a layout with its window on the left).
        self.lid, self.lay = layout_of(spec, self.paper)
        self.how = letter.layout_info(self.lay)[3] if self.lay else 'beside'
        named = str(spec.get('tax_name') or '').strip()
        if named and named != self.w.get('tax'):
            # A tax with another name (QST, HST alone, a US state's use tax) replaces the locale's in every label.
            self.w = json.loads(json.dumps(self.w).replace(self.w['tax'], named))

    def money(self, x):
        return letter.money(x, self.locale)

    def num(self, x):
        return letter.number(x, self.locale)

    def date(self, x):
        return letter.date(x, self.locale)

    def unit(self, u):
        return self.w['pcs'] if str(u or 'pcs').lower() in UNIT_ALIASES else str(u)

    def title(self):
        return self.w['title'][self.spec['type']]

    def label(self, text):
        """A spec's own label in the document's language when the table knows it, else as written."""
        row = LABEL_INDEX.get(str(text).strip().casefold())
        return row.get(self.locale, text) if row else text

    def address(self):
        """The recipient in the address field, as the letter and the invoice to the same recipient write it:
        the lines the recipient's post office reads (skills/_shared/letter.py postal_lines), the country last
        and in capitals when the document goes abroad."""
        return letter.postal_lines(recipient(self.spec), sender(self.spec).get('country'))

    def party(self, p, with_vat=True):
        out = [p['name']]
        out += [x for x in (p.get('street'), place_line(p), p.get('country')) if x]
        if with_vat and p.get('vat_id'):
            out.append('%s %s' % (self.w['vat_id'], p['vat_id']))
        return out

    def info_rows(self):
        s, w = self.spec, self.w
        rows = [(w['number'][s['type']], s['number']), (w['issue'], self.date(s['issue_date']))]
        if is_order(s) and s.get('quotation'):
            rows.append((w['your_quotation'], s['quotation']))
        rows += [(self.label(r['label']), self.date(r['value'])) for r in s.get('references', [])]
        if is_order(s) and s.get('requested_delivery_date'):
            rows.append((w['requested'], self.date(s['requested_delivery_date'])))
        rows += [(self.label(d['label']), self.date(d['value'])) for d in s.get('dates', [])]
        if s['type'] != 'delivery_note':
            rows.append((w['currency'], s['currency']))
        if recipient(s).get('vat_id'):
            rows.append((w['supplier_vat'] if is_order(s) else w['customer_vat'], recipient(s)['vat_id']))
        if s['type'] == 'delivery_note':
            if s.get('packages') is not None:
                rows.append((w['packages'], self.num(s['packages'])))
            if s.get('gross_weight_kg') is not None:
                rows.append((w['weight'], '%s kg' % self.num(s['gross_weight_kg'])))
        return rows

    def term_rows(self):
        s, w = self.spec, self.w
        rows = []
        term = delivery_term(s)
        if term:
            rows.append((w['delivery_terms'], term))
        if s.get('payment_terms') and s['type'] != 'delivery_note':
            rows.append((w['payment_terms'], s['payment_terms']))
        return rows

    def has_discount(self):
        if self.spec['type'] == 'delivery_note':
            return False
        return any(doc_amounts.line_amounts(dict(l, unit_price=l.get('unit_price', 0)))['discount'] for l in self.spec['lines'])

    def no_codes(self, editable=False):
        """No line carries an article code: the page and the Word file leave the Item column off, so the
        description keeps the text's left edge; the spreadsheet keeps it, a cell the person can fill in."""
        return not editable and not any(str(l.get('code') or '').strip() for l in self.spec['lines'])

    def columns(self, editable=False):
        if self.spec['type'] == 'delivery_note':
            cols = ['Item', 'Description', 'Unit', 'Ordered', 'Delivered', 'Outstanding']
            return cols[1:] if self.no_codes(editable) else cols
        cols = ['Item', 'Description', 'Quantity', 'Unit', 'Unit price', 'Discount %', 'VAT %', 'Net amount']
        if self.has_discount():
            # The discount in money (EN 16931-1 BT-136), beside its percentage, only on a document that gives one.
            cols.insert(6, 'Discount')
        elif not editable:
            # No line has a discount: the page leaves the column out rather than print a row of zeros. The
            # spreadsheet keeps it, a cell the person can fill in that its formulas read.
            cols.remove('Discount %')
        if self.spec['type'] == 'proforma_invoice':
            cols[2:2] = ['HS code', 'Origin']
        return cols[1:] if self.no_codes(editable) else cols

    def cells(self, l, editable=False):
        if self.spec['type'] == 'delivery_note':
            done = Decimal(str(l.get('delivered', l['quantity'])))
            row = [l.get('code', ''), l['description'], self.unit(l.get('unit')), self.num(l['quantity']), self.num(done),
                   self.num(Decimal(str(l['quantity'])) - done)]
            return row[1:] if self.no_codes(editable) else row
        percent = '' if (l.get('disc') and not l.get('pct')) else self.num(l.get('discount_percent', 0))
        row = [l.get('code', ''), l['description'], self.num(l['quantity']), self.unit(l.get('unit')), self.money(l['unit_price']),
               percent] + ([self.money(l['disc']) if l.get('disc') else ''] if self.has_discount() else []) + [
               self.num(l['rate']), self.money(l['net'])]
        if 'Discount %' not in self.columns(editable):
            del row[5]
        if self.spec['type'] == 'proforma_invoice':
            row[2:2] = [l.get('hs_code', ''), l.get('origin', '')]
        return row[1:] if self.no_codes(editable) else row

    def totals(self, data):
        _, vat, net, tax, gross = data
        m, cur, w = data.money, self.spec['currency'], self.w
        rows = []
        if m['allowances']:
            # The sum of the lines, each allowance on the whole document with its reason (EN 16931-1 BG-20,
            # BT-97) and then the total without VAT (BR-CO-13).
            rows.append((w['lines_sum'], '%s %s' % (self.money(m['line_total']), cur)))
            for al in m['allowances']:
                label = al['reason'] or al['code']
                if al['percent'] is not None:
                    label += ' %s %%' % self.num(al['percent'])
                rows.append((label, '-%s %s' % (self.money(al['amount']), cur)))
        rows.append((w['net_total'], '%s %s' % (self.money(net), cur)))
        rows += [(w['vat_on'] % (self.num(rate), self.money(base)), '%s %s' % (self.money(v), cur)) for rate, base, v in vat]
        if len(vat) != 1:
            # The VAT total, when more than one rate makes it a sum; with one rate the row above already says it.
            rows.append((w['vat_total'], '%s %s' % (self.money(tax), cur)))
        rows.append((w['gross_total'], '%s %s' % (self.money(gross), cur)))
        if m['paid']:
            # An amount paid in advance (BT-113) and what is left to pay (BT-115).
            rows += [(w['paid'] + (' ' + self.date(self.spec['paid_date']) if self.spec.get('paid_date') else ''), '-%s %s' % (self.money(m['paid']), cur)), (w['due_pay'], '%s %s' % (self.money(m['due']), cur))]
        return rows

    def bank_rows(self):
        """Where to pay, for the closing block of a document that asks for payment: the bank (and, where there is
        no IBAN, the account as the spec writes it), the IBAN and the BIC, the facts the footer's last column
        carries."""
        s, b = self.spec, self.spec.get('bank') or {}
        if not b or s['type'] in ('delivery_note', 'purchase_order'):
            return []
        return [(self.w['bank'], [b.get('bank'), None if b.get('iban') else b.get('account')]),
                ('IBAN', b.get('iban')), ('BIC', b.get('bic'))]

    def notes(self):
        notes = list(self.spec.get('notes', []))
        if self.spec['type'] == 'proforma_invoice':
            notes.insert(0, self.w['proforma'])
        return notes

    def layout_name(self):
        return self.lay['name'] if self.lay else 'DIN 5008:2020 Form B'

    def footer(self, block=True):
        """Three columns: who the sender is, its tax and company details, how to pay or reach it. The first is
        the company's own address as its letter and its invoice print it (letter.own_address): ordinary case,
        its country's town line, and the country last when the document goes abroad, none at home. The post
        office's capitals belong to the address field, which a machine reads; a footer is an imprint.
        block=False: the same address for one line (a workbook's footer row)."""
        s, seller = self.spec, sender(self.spec)
        if block:
            who = letter.own_address(own(seller), recipient(s).get('country'))
        else:
            who = [seller['name'], seller.get('street'), place_line(seller), seller.get('country')]
        tax = (['%s %s' % (self.w['vat_id'], seller['vat_id'])] if seller.get('vat_id') else []) + letter.company_lines(seller, self.locale)
        tax += letter.further_lines(seller)
        b = s.get('bank') or {}
        pay = []
        if b and s['type'] not in ('delivery_note', 'purchase_order'):
            pay = [b.get('bank'), ('IBAN %s' % b['iban']) if b.get('iban') else b.get('account'),
                   ('BIC %s' % b['bic']) if b.get('bic') else None]
        pay += [seller.get('email'), seller.get('phone')]
        return [[x for x in who if x], tax, [x for x in pay if x]]

    def sign_line(self, room=92, gap='    '):
        """The received-by line of a delivery note on one row: the blanks shrink as the words grow, so a long
        label (French, German) never pushes the date's blank onto a row of its own. room: about how many
        characters the row holds."""
        a, b = self.w['received'], self.w['sign_date']
        spare = max(18, room - len(a) - len(b) - len(gap) - 2)
        name = min(30, spare * 2 // 3)
        return '%s %s%s%s %s' % (a, '_' * name, gap, b, '_' * max(8, min(14, spare - name)))

    def return_line(self):
        seller = sender(self.spec)
        place = place_line(seller)
        return ' · '.join(x for x in (seller['name'], seller.get('street'), place) if x)


THIN, BROAD = set(" .,:;'|!()[]/-·ijlIftr"), set("mwMW%@")


def text_mm(text, size, bold=False):
    """About how wide a line of Arial or Helvetica is, from each character's class in the fonts' published
    widths: points and thin letters under a third of an em, digits and most letters a little over half,
    capitals near three quarters, m, w and the percent sign more; bold a tenth wider. On the generous side,
    so a header or a figure never wraps where the estimate says it fits."""
    em = sum(0.3 if ch in THIN else 0.9 if ch in BROAD else 0.56 if ch.isdigit() else 0.73 if ch.isupper() else 0.56
             for ch in str(text))
    return em * size * 0.3528 * (1.1 if bold else 1.0)


def info_mm(paper='A4', lay=None):
    """How wide the information block is. On DIN 5008 Form B: from 125 mm across to the text's right edge, 20 mm
    short of the paper's, where the table ends (65 mm on A4; invoices end it there since the wave 8 close-out).
    On a country layout: the width that layout gives the block (letter.layout_info), which ends on the text's
    right edge or before a window on the right."""
    if lay:
        return round(letter.layout_info(lay)[2], 2)
    return letter.info_width(paper)


def label_mm(rows, base=34.0, paper='A4', lay=None):
    """How wide the information block's label column is in Word: the usual 34 mm, and wider when a label is
    longer (Numéro du bon de livraison, Potwierdzony termin dostawy), so a label always keeps to one line;
    a value too long for what is left wraps in its own column."""
    need = max(text_mm(k, 8.5) for k, _ in rows) + 1.5
    return round(min(max(base, need), info_mm(paper, lay) - 15), 1)


def info_css(paper='A4'):
    """The CSS that ends a Form B page's block on the text's right edge, in two columns: the labels as wide as
    the longest of them and never wrapped, the values in what the block has left (the shared letter's rule)."""
    return letter.info_css(paper)


# Word only: on a country layout the letterhead sits in the page header above this line (mm from the top of the
# sheet) and the first table starts on it. Every layout's window and information block start below it.
WORD_TOP = 25
WORD_ROW = 4.1      # mm one row of the information block takes in Word (a line of the 10 pt body style)
WORD_LEAD = 0.42    # mm of line one point of type needs


# ---------- PDF: the letter sheet, printed by Chromium ----------

def page_html(spec, data):
    """The page a PDF is printed from: the shared letter sheet, on the layout of the country it is sent from."""
    pg = Page(spec)
    esc = lambda s: str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    cols = pg.columns()
    numeric = {'Quantity', 'Unit price', 'Discount %', 'Discount', 'VAT %', 'Net amount', 'Ordered', 'Delivered', 'Outstanding'}
    # The description is the column that wraps and takes the spare width (class d); an article code or a unit
    # stays on one row.
    kind = lambda c: ' class="n"' if c in numeric else ' class="d"' if c == 'Description' else ''  # noqa: E731
    # A column head never breaks before its percent sign (Disc. %).
    head = ''.join('<th%s>%s</th>' % (kind(c), esc(pg.w['cols'][c]).replace(' %', '&nbsp;%')) for c in cols)
    whole = {'Item', 'Unit', 'HS code'}
    rows = ''.join('<tr>%s</tr>' % ''.join('<td%s>%s</td>' % (kind(cols[i]) or (' style="white-space:nowrap"' if cols[i] in whole else ''),
                                                              esc(v))
                                           for i, v in enumerate(pg.cells(l))) for l in data[0])
    body = ['<h1>%s %s</h1>' % (esc(pg.title()), esc(spec['number']))]
    if delivery_address(spec):
        body.append('<p class="extra"><span class="k">%s:</span> %s</p>' % (esc(pg.w['deliver_to']), esc(', '.join(pg.party(delivery_address(spec), False)))))
    body.append('<table class="lines"><thead><tr>%s</tr></thead><tbody>%s</tbody></table>' % (head, rows))
    if spec['type'] != 'delivery_note':
        tot = pg.totals(data)
        body.append('<table class="sum"><tbody>%s</tbody></table>' % ''.join(
            '<tr%s><td>%s</td><td class="n">%s</td></tr>' % (' class="gross"' if i == len(tot) - 1 else '', esc(a), esc(b))
            for i, (a, b) in enumerate(tot)))
    body += ['<p class="note">%s</p>' % esc(n) for n in pg.notes()]
    # The closing block (skills/_shared/page_look.py): the delivery and payment terms and where to pay as rows
    # of key and value on one grid, then a delivery note's signature line. It stands at the foot of a page that
    # has room, after the notes on a full one.
    sign = ''
    if spec['type'] == 'delivery_note':
        sign = '<p class="sign" style="white-space:nowrap">%s</p>' % esc(pg.sign_line(88, '   ')).replace('   ', '&nbsp;&nbsp;&nbsp;')
    body.append(page_look.closing(pg.term_rows() + pg.bank_rows(), sign, letter.keep))
    # A token with a hyphen stays on one line and an e-mail address breaks after its @ (hoja M-123456 in a
    # footer column reads back whole).
    html = letter.sheet_html(pg.locale, '%s %s' % (pg.title(), spec['number']), 'nodejam-trade-builder', sender(spec)['name'],
                             pg.return_line(), '<br>'.join(esc(x) for x in pg.address()), pg.info_rows(), ''.join(body),
                             pg.footer(), paper=pg.paper, keep_tokens=True)
    if pg.lay:
        # The sheet on the sender's country's letter layout, the way its invoice sits on it: the layout's margins,
        # the address in its envelope window, the block beside, left of or above the window. Every number is the
        # layout's own (skills/_shared/letter.py).
        html = letter.on_layout(html, pg.lay)
    else:
        html = html.replace('</style>', info_css(pg.paper) + '</style>', 1)
    # The look last: type, spacing and rules from the library's look file, the closing block at the foot.
    return page_look.dress(html, pg.lay, pg.paper)


def write_pdf(spec, out, data):
    page = Path(out).with_suffix('.html')
    page.write_text(page_html(spec, data))
    # A document that runs to a second page is printed once more with its running line (page_look).
    return page_look.print_pages(page, out, Page(spec).paper, lambda h, p, paper: letter.print_pdf(h, p, paper=paper))


# ---------- Word: the same sheet, in Word's own terms ----------

def write_docx(spec, out, data):
    from docx import Document
    from docx.enum.table import WD_ROW_HEIGHT_RULE, WD_CELL_VERTICAL_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Mm, Pt, RGBColor
    pg = Page(spec)
    g = letter.GEOMETRY
    lay = pg.lay
    lines = data[0]
    # The look the PDF takes (skills/_shared/page_look.py, from the library's look file): its inks, its face,
    # one weight unless the file asks for bold titles, and its sizes: the sender's name, the document's name
    # and number, the total, rows and notes, and one size of small print.
    look = page_look.load()
    inks, text, trade = look['ink'], look['text'], look['trade']
    face = look['face']['name']
    strong = int(look['face'].get('title_weight') or 400) >= 600
    body_pt, small_pt = trade['body'][0], trade['small'][0]
    second = RGBColor.from_string(str(inks['second']).upper())
    hairline, rule = str(inks['hairline']).upper(), str(inks['rule']).upper()
    rule_w, hair_w = int(round(trade['rule'] * 8)), int(round(trade['hairline'] * 8))    # eighths of a point
    air = trade['row_air'] * 0.3528                                                     # mm over and under a row
    doc = Document()
    sec = doc.sections[0]
    page_w, page_h = letter.PAPER_MM[pg.paper]
    sec.page_width, sec.page_height = Mm(page_w), Mm(page_h)
    # DIN 5008 Form B: the letterhead takes the top 45 mm, the text runs from 25 mm to 20 mm short of the edge.
    # A country layout: its own margins, the letterhead above WORD_TOP.
    left, right = (lay['left'], lay['right']) if lay else (g['left'], g['right'])
    top_mm = WORD_TOP if lay else g['field_y']
    sec.left_margin, sec.right_margin = Mm(left), Mm(right)
    sec.top_margin, sec.bottom_margin = Mm(top_mm), Mm(30)
    sec.header_distance, sec.footer_distance = Mm(g['head_top']), Mm(8)
    for style in doc.styles:
        if style.type == 1 and style.font is not None:
            style.font.name = face
            rpr = style.element.get_or_add_rPr()
            fonts = rpr.find(qn('w:rFonts'))
            if fonts is None:
                fonts = OxmlElement('w:rFonts')
                rpr.append(fonts)
            for attr in ('w:ascii', 'w:hAnsi', 'w:eastAsia', 'w:cs'):
                fonts.set(qn(attr), face)
    doc.styles['Normal'].font.size = Pt(body_pt)
    doc.styles['Normal'].font.color.rgb = RGBColor.from_string(str(inks['ink']).upper())
    doc.styles['Normal'].paragraph_format.space_after = Pt(0)
    doc.core_properties.title = '%s %s' % (pg.title(), spec['number'])
    doc.core_properties.language = pg.locale

    def run(p, text, bold=False, size=None, grey=False):
        r = p.add_run(text)
        r.bold = bold
        if size:
            r.font.size = Pt(size)
        if grey:
            r.font.color.rgb = second
        return r

    def no_borders(table):
        tbl = table._tbl
        pr = tbl.tblPr
        borders = OxmlElement('w:tblBorders')
        for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
            e = OxmlElement('w:%s' % edge)
            e.set(qn('w:val'), 'nil')
            borders.append(e)
        pr.append(borders)
        mar = OxmlElement('w:tblCellMar')
        for edge in ('left', 'right'):
            e = OxmlElement('w:%s' % edge)
            e.set(qn('w:w'), '0')
            e.set(qn('w:type'), 'dxa')
            mar.append(e)
        pr.append(mar)
        fixed(table)

    def fixed(table):
        lay = OxmlElement('w:tblLayout')
        lay.set(qn('w:type'), 'fixed')
        table._tbl.tblPr.append(lay)

    def grid(table, widths_mm):
        """Column widths Word and LibreOffice both keep: the table grid and every cell, on a fixed layout."""
        table.autofit = False
        for i, wdt in enumerate(widths_mm):
            table.columns[i].width = Mm(wdt)
            for cell in table.columns[i].cells:
                cell.width = Mm(wdt)

    def edge(cell, side, size=hair_w, color=hairline):
        """One rule on one side of a cell; size in eighths of a point."""
        pr = cell._tc.get_or_add_tcPr()
        borders = pr.find(qn('w:tcBorders'))
        if borders is None:
            borders = OxmlElement('w:tcBorders')
            pr.append(borders)
        e = OxmlElement('w:%s' % side)
        e.set(qn('w:val'), 'single')
        e.set(qn('w:sz'), str(size))
        e.set(qn('w:space'), '0')
        e.set(qn('w:color'), color)
        borders.append(e)

    def pad(cell, left=0, top=None, bottom=None):
        pr = cell._tc.get_or_add_tcPr()
        mar = OxmlElement('w:tcMar')
        for side, mm in (('top', top), ('left', left), ('bottom', bottom)):
            if mm is not None:
                e = OxmlElement('w:%s' % side)
                e.set(qn('w:w'), str(int(round(mm * 56.7))))
                e.set(qn('w:type'), 'dxa')
                mar.append(e)
        pr.append(mar)

    def keep_row(row, header=False):
        trpr = row._tr.get_or_add_trPr()
        trpr.append(OxmlElement('w:cantSplit'))
        if header:
            rep = OxmlElement('w:tblHeader')
            rep.set(qn('w:val'), 'true')
            trpr.append(rep)

    head = sec.header.paragraphs[0]
    run(head, sender(spec)['name'], bold=strong, size=text['h2'][0])

    rows = pg.info_rows()
    block_w = info_mm(pg.paper, lay)
    usable = page_w - left - right
    block_pt, block_line = small_pt, None
    if lay:
        # The sender's country's letter layout, as on the PDF: a first row as tall as the space above the
        # address, then the address at its first line inside the envelope window, in the layout's own line
        # height and with no return line; the information block where the layout puts it (letter.layout_info):
        # right of a window on the left, left of a window on the right, or above a No. 10 window.
        ax, ay, aw, _ah, line_mm = letter.layout_address(lay)
        ix, iy, _iw, how = letter.layout_info(lay)
        _wx, wy, _ww, wh = lay['window']
        lead_mm = ax - left
        if how == 'left':
            widths, at, bi = [block_w, lead_mm - block_w, min(aw, usable - lead_mm)], 2, 0
        elif how == 'above':
            widths, at, bi = [ix - left, block_w], 0, 1
        else:
            widths = ([lead_mm] if lead_mm > 0.5 else []) + [aw, ix - ax - aw, block_w]
            at, bi = len(widths) - 3, len(widths) - 1
        # Fixed rows down to the address's first line: one, or for a block above the window two (the block's
        # row, on whose foot it stands, and the space between it and the address).
        above = [iy - top_mm, ay - iy] if how == 'above' else [ay - top_mm]
        top = doc.add_table(rows=len(above) + 1, cols=len(widths))
        no_borders(top)
        top.autofit = False
        grid(top, widths)
        for i, height in enumerate(above):
            top.rows[i].height, top.rows[i].height_rule = Mm(height), WD_ROW_HEIGHT_RULE.EXACTLY
        top.rows[-1].height, top.rows[-1].height_rule = Mm(wy + wh - ay), WD_ROW_HEIGHT_RULE.AT_LEAST
        addr = top.cell(len(above), at)
        if how == 'above':
            addr = addr.merge(top.cell(len(above), bi))   # nothing stands beside a No. 10 window: the address has the row
        for i, line in enumerate(pg.address()):
            p = addr.paragraphs[0] if i == 0 else addr.add_paragraph()
            p.paragraph_format.line_spacing = Mm(line_mm)
            run(p, line)
        if how == 'above':
            info = top.cell(0, bi)
            info.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.BOTTOM
            info.paragraphs[0].paragraph_format.line_spacing = Pt(1)
            if len(rows) * WORD_ROW > above[0]:
                # More rows than the room above the window holds: closer lines and smaller type, never a cut row.
                block_line = above[0] / len(rows)
                block_pt = min(block_pt, round(block_line / WORD_LEAD, 1))
        else:
            info = top.cell(0, bi).merge(top.cell(1, bi))
            lead = info.paragraphs[0].paragraph_format
            lead.space_before, lead.line_spacing = Mm(iy - top_mm), Pt(1)
    else:
        # Address field (80 mm of text from the 25 mm edge) and the information block from 125 mm.
        top = doc.add_table(rows=2, cols=3)
        no_borders(top)
        top.autofit = False
        # The block runs from 125 mm to the text's right margin, as on the PDF: the table ends where the text does.
        grid(top, (80, g['info_x'] - g['left'] - 80, block_w))
        top.rows[0].height, top.rows[0].height_rule = Mm(g['return_h']), WD_ROW_HEIGHT_RULE.EXACTLY
        top.rows[1].height, top.rows[1].height_rule = Mm(g['address_h']), WD_ROW_HEIGHT_RULE.AT_LEAST
        ret = top.cell(0, 0)
        ret.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.BOTTOM
        run(ret.paragraphs[0], pg.return_line(), size=7, grey=True)
        addr = top.cell(1, 0)
        for i, line in enumerate(pg.address()):
            p = addr.paragraphs[0] if i == 0 else addr.add_paragraph()
            run(p, line)
        info = top.cell(0, 2).merge(top.cell(1, 2))
        lead = info.paragraphs[0].paragraph_format
        lead.space_before, lead.line_spacing = Mm(g['info_y'] - g['field_y']), Pt(1)
    # The information block as on the PDF: labels in a grey column of their own, values beside them.
    block = info.add_table(rows=len(rows), cols=2)
    no_borders(block)
    label_w = label_mm(rows, 33.0, pg.paper, lay)
    grid(block, (label_w, block_w - label_w))
    for i, (k, v) in enumerate(rows):
        label, value = block.cell(i, 0), block.cell(i, 1)
        run(label.paragraphs[0], k, size=block_pt, grey=True)
        run(value.paragraphs[0], str(v), size=block_pt)
        pad(value, left=1.5)
        if block_line:
            label.paragraphs[0].paragraph_format.line_spacing = Mm(block_line)
            value.paragraphs[0].paragraph_format.line_spacing = Mm(block_line)
    info.paragraphs[-1].paragraph_format.line_spacing = Pt(1)

    subject = doc.add_paragraph()
    subject.paragraph_format.space_before = Mm(g['subject_gap'])
    subject.paragraph_format.space_after = Pt(trade['title_gap'])
    run(subject, '%s %s' % (pg.title(), spec['number']), bold=strong, size=text['h1'][0])
    if delivery_address(spec):
        p = doc.add_paragraph()
        run(p, '%s: ' % pg.w['deliver_to'], grey=True)
        run(p, ', '.join(pg.party(delivery_address(spec), False)))
        p.paragraph_format.space_after = Pt(text['heading_gap'][0] / 2.0)

    # The lines as on the PDF: no grid, an ink rule under the header, hairlines between rows, numbers
    # flush right, each column as wide as its header and figures need and the description the rest. Rows are
    # set at the look's body size where that leaves the description its share of the table, as the PDF keeps
    # its columns on one line each; a table of more columns is set one or two points smaller, as before.
    cols = pg.columns()
    numeric = {'Quantity', 'Unit price', 'Discount %', 'Discount', 'VAT %', 'Net amount', 'Ordered', 'Delivered', 'Outstanding'}
    gap = 2.5
    body = [pg.cells(l) for l in lines]
    d = cols.index('Description')

    def needs(size, head_pt):
        head = [text_mm(pg.w['cols'][c], head_pt, True) + 1 + (gap if i else 0) for i, c in enumerate(cols)]
        return head, [max([head[i]] + [text_mm(r[i], size) + 1 + (gap if i else 0) for r in body]) for i in range(len(cols))]

    size = body_pt
    head, widths = needs(size, small_pt)
    if usable - (sum(widths) - widths[d]) < usable * page_look.DESCRIPTION_SHARE:
        size = min(body_pt, 8 if len(cols) > 8 else 9)
        head, widths = needs(size, min(small_pt, size - 1))
    head_pt = small_pt if size == body_pt else min(small_pt, size - 1)
    widths[d] = 0
    # The description takes what is left, and never less than its longest word needs: a long compound
    # (Noodverlichtingsarmatuur) is not cut one letter before its end.
    word = max([text_mm(x, size) for r in body for x in str(r[d]).split()] or [0]) + 1.5
    widths[d] = max(30, word, usable - sum(widths))
    spare = sum(widths) - usable
    for i in sorted(range(len(cols)), key=lambda i: head[i] - widths[i]):
        # Too wide: a long code or place wraps before any header does.
        if i != d and spare > 0:
            cut = min(spare, max(0, widths[i] - head[i]))
            widths[i] -= cut
            spare -= cut
    if spare > 0:
        # Still too wide: each header gives up most of the millimetre the generous estimate leaves it,
        # and only then does the description wrap inside a word.
        others = [i for i in range(len(cols)) if i != d]
        cut = min(0.8, spare / len(others))
        for i in others:
            widths[i] -= cut
        spare -= cut * len(others)
        widths[d] -= max(0, spare)
    table = doc.add_table(rows=1 + len(lines), cols=len(cols))
    no_borders(table)
    grid(table, widths)
    keep_row(table.rows[0], header=True)
    for r, values in enumerate([[pg.w['cols'][c] for c in cols]] + body):
        row = table.rows[r]
        if r:
            keep_row(row)
        for i, v in enumerate(values):
            cell = row.cells[i]
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.BOTTOM if r == 0 else WD_CELL_VERTICAL_ALIGNMENT.TOP
            run(cell.paragraphs[0], v, size=head_pt if r == 0 else size, grey=r == 0)
            pad(cell, left=gap if i else 0, top=1.5 if r == 0 else air, bottom=1.5 if r == 0 else air)
            edge(cell, 'bottom', rule_w, rule) if r == 0 else edge(cell, 'bottom')
            if cols[i] in numeric:
                cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    if spec['type'] != 'delivery_note':
        # The totals flush right as on the PDF, on the right half of the text's width or as wide as the total
        # needs: figures ending under the amount column, the labels in the second ink, the total larger, in
        # ink, with an ink rule over it.
        gap_p = doc.add_paragraph()  # two tables back to back would run together into one
        gap_p.paragraph_format.line_spacing = Pt(1)
        tot = doc.add_table(rows=0, cols=3)
        no_borders(tot)
        rows = pg.totals(data)
        for i, (label, value) in enumerate(rows):
            tot.add_row()
        total_pt = text['lead'][0]
        label_w = max([text_mm(a, body_pt) for a, _ in rows[:-1]] + [text_mm(rows[-1][0], total_pt, strong)]) + 4
        value_w = max([text_mm(b, body_pt) for _, b in rows[:-1]] + [text_mm(rows[-1][1], total_pt, strong)]) + 2
        block = min(usable, max(usable / 2.0 - trade['gutter'] / 2.0, label_w + value_w))
        grid(tot, (usable - block, block - value_w, value_w))
        for i, (label, value) in enumerate(rows):
            c = tot.rows[i].cells
            last = i == len(rows) - 1
            run(c[1].paragraphs[0], label, bold=last and strong, size=total_pt if last else body_pt, grey=not last)
            run(c[2].paragraphs[0], value, bold=last and strong, size=total_pt if last else body_pt)
            c[2].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
            for cell in c[1:]:
                pad(cell, top=4 if i == 0 else (air if last else 0.4), bottom=air if i == len(rows) - 2 else 0.4)
                if last:
                    edge(cell, 'top', rule_w, rule)
    for n in pg.notes():
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Mm(3)
        run(p, n)
    # The closing block as on the PDF: the terms and where to pay as rows of key and value under a hairline,
    # the keys in the second ink on the column the footer's second block starts on. Word lets a page run on,
    # so the block follows the notes instead of standing at the foot.
    closing = [(k, [x for x in (v if isinstance(v, list) else [v]) if x]) for k, v in pg.term_rows() + pg.bank_rows()]
    closing = [(k, v) for k, v in closing if v]
    if closing:
        gap_p = doc.add_paragraph()
        gap_p.paragraph_format.space_before = Pt(text['heading_gap'][0] / 2.0)
        gap_p.paragraph_format.line_spacing = Pt(1)
        key_w = max([usable * trade['key_columns'] / 12.0 + trade['gutter'] * trade['key_columns'] / 12.0]
                    + [text_mm(k, body_pt) + 3 for k, _ in closing])
        pay = doc.add_table(rows=len(closing), cols=2)
        no_borders(pay)
        grid(pay, (key_w, usable - key_w))
        for i, (k, v) in enumerate(closing):
            keep_row(pay.rows[i])
            key, value = pay.cell(i, 0), pay.cell(i, 1)
            run(key.paragraphs[0], k, grey=True)
            for j, line in enumerate(v):
                run(value.paragraphs[0] if j == 0 else value.add_paragraph(), str(line))
            if i == 0:
                for cell in (key, value):
                    edge(cell, 'top')
                    pad(cell, top=air)
    if spec['type'] == 'delivery_note':
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Mm(12)
        run(p, pg.sign_line(88))

    foot = sec.footer.add_table(rows=1, cols=3, width=Mm(usable))
    no_borders(foot)
    # The footer's three blocks on the grid's columns, as on the PDF, each after the first with the gutter
    # before it: a line that fills its column (Domicilio social: ..., Registro delle Imprese di ...) never runs
    # into the next column's text.
    gutter, parts = trade['gutter'], trade['footer_columns']
    column = (usable - 11 * gutter) / 12.0
    grid(foot, [k * column + (k - 1) * gutter + (gutter if i else 0) for i, k in enumerate(parts)])
    for i, col in enumerate(pg.footer()):
        cell = foot.cell(0, i)
        edge(cell, 'top')
        pad(cell, left=gutter if i else 0, top=air)
        for j, line in enumerate(col):
            p = cell.paragraphs[0] if j == 0 else cell.add_paragraph()
            run(p, line, size=small_pt, grey=True)
    doc.save(out)


# ---------- Excel: a working sheet, in the document's language and forms ----------

def write_xlsx(spec, out, data):
    import textwrap
    from openpyxl import Workbook
    from openpyxl.cell.rich_text import CellRichText, TextBlock
    from openpyxl.cell.text import InlineFont
    from openpyxl.styles import Alignment, Border, Font, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.page import PageMargins
    pg = Page(spec)
    w = pg.w
    lines, vat, net, tax, gross = data
    wb = Workbook()
    ws = wb.active
    ws.title = pg.title()[:31]
    wb.properties.title = '%s %s' % (pg.title(), spec['number'])
    wb.properties.language = pg.locale
    # The look's inks (skills/_shared/page_look.py); a working sheet keeps its own sizes and its bold headings.
    inks = page_look.load()['ink']
    ink, grey_ink, rule_ink = str(inks['ink']).upper(), str(inks['second']).upper(), str(inks['hairline']).upper()
    base, bold = Font(name=FONT, size=10, color=ink), Font(name=FONT, size=10, bold=True, color=ink)
    grey, small = Font(name=FONT, size=10, color=grey_ink), Font(name=FONT, size=8, color=grey_ink)
    dark, light = Side(style='medium', color=ink), Side(style='thin', color=rule_ink)
    cached = {}
    cols = pg.columns(editable=True)
    numeric = {'Quantity', 'Unit price', 'Discount %', 'Discount', 'VAT %', 'Net amount', 'Ordered', 'Delivered', 'Outstanding'}
    # The workbook shows its figures in the document's language: Excel takes the separators from the
    # reader's own settings, LibreOffice from the locale tag in front of the format.
    tag = _TABLE['xlsx_tag'].get(pg.locale, '')
    amount_fmt = tag + '#,##0.00'
    total_fmt = tag + '#,##0.00 "%s"' % spec.get('currency', '')
    count_fmt = tag + '#,##0.###'

    # Each column as wide as its header and its figures need, the description the widest.
    widths = {'Item': 9, 'Description': 28, 'Quantity': 7, 'Unit': 6, 'Unit price': 11, 'Discount %': 8, 'Discount': 10, 'VAT %': 7,
              'Net amount': 14, 'HS code': 10, 'Origin': 10, 'Ordered': 9, 'Delivered': 9, 'Outstanding': 10}
    width = [max(widths[c], len(w['cols'][c]) + 2) for c in cols]
    for i, c in enumerate(cols):
        if c in ('Item', 'HS code', 'Origin'):
            width[i] = max([width[i]] + [len(str(pg.cells(l, editable=True)[i])) + 2 for l in lines])
    if len(cols) > 8:
        width[cols.index('Description')] = 22    # a pro forma's ten columns: keep the page readable at A4 width
    letter_of = {c: get_column_letter(i) for i, c in enumerate(cols, 1)}
    last_col = get_column_letter(len(cols))
    span = sum(width)

    # No merged cells (UK Analysis Function spreadsheet guidance, FAST 4.02-02): a label or an address
    # line runs on over the empty cells beside it instead, and only table cells wrap.
    def put(ref, value, font=base, fmt=None, align=None, result=None, wrap=False, valign='top', indent=0):
        c = ws[ref]
        c.value, c.font = value, font
        c.alignment = Alignment(wrap_text=wrap, vertical=valign, horizontal=align, indent=indent)
        if fmt:
            c.number_format = fmt
        if result is not None:
            cached[ref] = result
        return c

    def labelled(label, value):
        """'Label: value' in one cell, the label in bold, as the PDF prints its terms."""
        return CellRichText(TextBlock(InlineFont(rFont=FONT, sz=10, b=True, color=ink), '%s: ' % label),
                            TextBlock(InlineFont(rFont=FONT, sz=10, color=ink), str(value)))

    # The letterhead, then the recipient and the information block on the sides the PDF has them: the address on
    # the left and the block right of it (Form B, and a layout with its window on the left), the address on the
    # right and the block left of it (a window on the right: Belgium, Spain, Italy, Poland), or the block at the
    # top right and the address under it on the left (a No. 10 window: the United States, Canada). A Form B page
    # carries its return line under the letterhead; a country layout has none, as on the PDF.
    put('A1', sender(spec)['name'], Font(name=FONT, size=14, bold=True, color=ink))
    ws.row_dimensions[1].height = 22
    if pg.lay:
        r = 3
    else:
        put('A2', pg.return_line(), small)
        r = 4
    address = pg.address()
    info = pg.info_rows()
    long_label = max(len(k) for k, _ in info) + 2
    long_value = max(len(str(v)) for _, v in info) + 1
    long_line = max(len(x) for x in address)
    n = len(cols)
    place = None            # (address column, label column, value column), counted from 0
    if pg.how == 'left':
        # The labels on the left edge, the values in the first column clear of them, and the address as far
        # right as its longest line still fits inside the table's width, clear of the values.
        vc = next((i for i in range(1, n) if sum(width[:i]) >= long_label), None)
        ac = next((i for i in range(n - 1, 0, -1) if sum(width[i:]) >= long_line + 1), None)
        if vc is not None and ac is not None and sum(width[vc:ac]) >= long_value + 2:
            place = (ac, 0, vc)
    elif pg.how == 'above':
        # The block as far right as its values and labels fit; the address starts under it.
        vc = next((i for i in range(n - 1, 1, -1) if sum(width[i:]) >= long_value), None)
        lc = next((i for i in range(vc - 1, 0, -1) if sum(width[i:vc]) >= long_label), None) if vc is not None else None
        if lc is not None:
            place = (0, lc, vc)
    else:
        # The block starts in the first column clear of the address, as the PDF's starts at 125 mm.
        lc = next((i for i in range(2, n) if sum(width[:i]) >= long_line + 3), None)
        if lc is not None:
            vc = next((i for i in range(lc + 1, n) if sum(width[lc:i]) >= long_label), None)
            if vc is not None and sum(width[vc:]) >= long_value:
                place = (0, lc, vc)
    if place:
        ac, lc, vc = place
        first = r + (len(info) + 1 if pg.how == 'above' else 0)
        for i, line in enumerate(address):
            put('%s%d' % (get_column_letter(ac + 1), first + i), line)
        for i, (k, v) in enumerate(info):
            put('%s%d' % (get_column_letter(lc + 1), r + i), k, grey)
            put('%s%d' % (get_column_letter(vc + 1), r + i), str(v))
        r = max(first + len(address), r + len(info)) + 1
    else:
        for i, line in enumerate(address):
            put('A%d' % (r + i), line)
        r += len(address) + 1
        for k, v in info:
            put('A%d' % r, k, grey)
            put('C%d' % r, str(v))
            r += 1
        r += 1
    put('A%d' % r, '%s %s' % (pg.title(), spec['number']), Font(name=FONT, size=12, bold=True, color=ink))
    ws.row_dimensions[r].height = 20
    r += 1
    def labelled_rows(label, value):
        """A labelled line, wrapped to the table's width: nothing merges, so a line longer than the columns
        would run off the printed page."""
        nonlocal r
        parts = textwrap.wrap('%s: %s' % (label, value), int(span * 1.05)) or ['%s:' % label]
        put('A%d' % r, labelled(label, parts[0][len(label) + 2:]))
        for part in parts[1:]:
            r += 1
            put('A%d' % r, part)
        r += 1

    if delivery_address(spec):
        labelled_rows(w['deliver_to'], ', '.join(pg.party(delivery_address(spec), False)))
    r += 1

    # The lines: a bold header with a rule under it, hairlines between rows, figures flush right.
    head = r
    for i, c in enumerate(cols, 1):
        cell = put('%s%d' % (get_column_letter(i), r), w['cols'][c], Font(name=FONT, size=9, bold=True, color=grey_ink),
                   align='right' if c in numeric else 'left', valign='bottom', indent=1 if c == 'Unit' else 0)
        cell.border = Border(bottom=dark)
    ws.row_dimensions[r].height = 18
    first = r + 1
    desc_chars = width[cols.index('Description')] - 1
    for l in lines:
        r += 1
        if spec['type'] == 'delivery_note':
            done = Decimal(str(l.get('delivered', l['quantity'])))
            values = dict(zip(cols, [l.get('code', ''), l['description'], pg.unit(l.get('unit')), float(l['quantity']), float(done), None]))
        else:
            values = {'Item': l.get('code', ''), 'Description': l['description'], 'Quantity': float(l['quantity']), 'Unit': pg.unit(l.get('unit')),
                      'Unit price': float(l['unit_price']), 'Discount %': float(l.get('discount_percent', 0)), 'VAT %': float(l['rate']),
                      'Discount': float(l['disc']),
                      'HS code': l.get('hs_code', ''), 'Origin': l.get('origin', ''), 'Net amount': None}
        for c in cols:
            ref = '%s%d' % (letter_of[c], r)
            align = 'right' if c in numeric else 'left'
            if c == 'Net amount' and 'Discount' in cols:
                put(ref, '=ROUND(%s%d*%s%d,2)-%s%d' % (letter_of['Quantity'], r, letter_of['Unit price'], r, letter_of['Discount'], r),
                    fmt=amount_fmt, result=l['net'], align=align)
            elif c == 'Discount':
                # A percentage is worked out from its cell; an amount stays the number the order gave (BT-136).
                if l.get('pct') or not l['disc']:
                    put(ref, '=ROUND(%s%d*%s%d,2)-ROUND(%s%d*%s%d*(1-%s%d/100),2)' % (
                        letter_of['Quantity'], r, letter_of['Unit price'], r, letter_of['Quantity'], r,
                        letter_of['Unit price'], r, letter_of['Discount %'], r), fmt=amount_fmt, result=l['disc'], align=align)
                else:
                    put(ref, float(l['disc']), fmt=amount_fmt, align=align)
            elif c == 'Net amount':
                put(ref, '=ROUND(%s%d*%s%d*(1-%s%d/100),2)' % (letter_of['Quantity'], r, letter_of['Unit price'], r, letter_of['Discount %'], r),
                    fmt=amount_fmt, result=l['net'], align=align)
            elif c == 'Outstanding':
                put(ref, '=%s%d-%s%d' % (letter_of['Ordered'], r, letter_of['Delivered'], r), fmt=count_fmt, align=align,
                    result=Decimal(str(l['quantity'])) - Decimal(str(l.get('delivered', l['quantity']))))
            else:
                fmt = amount_fmt if c == 'Unit price' else (count_fmt if c in numeric else None)
                put(ref, values[c], fmt=fmt, align=align, wrap=c == 'Description', indent=1 if c == 'Unit' else 0)
            ws[ref].border = Border(bottom=light)
        ws.row_dimensions[r].height = 18 * max(1, -(-len(str(l['description'])) // desc_chars))
    last = r
    r += 2

    # The totals under the amount column, the labels in one column to their left, as on the PDF.
    if spec['type'] != 'delivery_note':
        n, v = letter_of['Net amount'], letter_of['VAT %']
        nc = len(cols)
        label_col, base_col = get_column_letter(nc - 4), get_column_letter(nc - 2)

        def total(label, formula, result, strong=False):
            nonlocal r
            put('%s%d' % (label_col, r), label, bold if strong else grey)
            put('%s%d' % (n, r), formula, bold if strong else base, fmt=total_fmt, result=result, align='right')
            if strong:
                for i in range(nc - 4, nc + 1):
                    ws['%s%d' % (get_column_letter(i), r)].border = Border(top=dark)
                ws.row_dimensions[r].height = 20
            r += 1
            return '%s%d' % (n, r - 1)
        m = data.money
        net_ref = total(w['net_total'] if not m['allowances'] else w['lines_sum'], '=SUM(%s%d:%s%d)' % (n, first, n, last),
                        m['line_total'] if m['allowances'] else net)
        if m['allowances']:
            refs = [net_ref]
            for al in m['allowances']:
                label = al['reason'] or al['code']
                refs.append(total(label, '=-%s' % al['amount'], -al['amount']))
            net_ref = total(w['net_total'], '=' + '+'.join(refs), net)
        vat_refs = []
        for rate, basev, amount in vat:
            share = 'SUMIF(%s%d:%s%d,%s,%s%d:%s%d)' % (v, first, v, last, rate, n, first, n, last)
            cuts = ''.join('-%s' % al['amount'] for al in m['allowances'] if al['rate'] == rate)
            if cuts:
                share = '(%s%s)' % (share, cuts)
            put('%s%d' % (label_col, r), (w['vat_on'] % (pg.num(rate), '')).strip(), grey)
            put('%s%d' % (base_col, r), '=' + share, grey, fmt=amount_fmt, result=basev, align='right')
            put('%s%d' % (n, r), '=ROUND(%s*%s/100,2)' % (share, rate), fmt=total_fmt, result=amount, align='right')
            vat_refs.append('%s%d' % (n, r))
            r += 1
        tax_ref = total(w['vat_total'], '=' + ('+'.join(vat_refs) if vat_refs else '0'), tax)
        gross_ref = total(w['gross_total'], '=%s+%s' % (net_ref, tax_ref), gross, strong=not m['paid'])
        if m['paid']:
            paid_ref = total(w['paid'], '=-%s' % m['paid'], -m['paid'])
            total(w['due_pay'], '=%s+%s' % (gross_ref, paid_ref), m['due'], strong=True)
        r += 1

    # Terms, notes and the signature line on the left edge, each wrapped to the table's width.
    for k, value in pg.term_rows():
        labelled_rows(k, value)
    if pg.term_rows():
        r += 1
    for note in pg.notes():
        for part in textwrap.wrap(note, int(span * 0.95)):
            put('A%d' % r, part)
            r += 1
        r += 1
    if spec['type'] == 'delivery_note':
        r += 1
        put('A%d' % r, pg.sign_line(int(span * 1.05), '   '))
        r += 2

    # The company details the PDF prints in its footer, under a hairline.
    r += 1
    for i in range(1, len(cols) + 1):
        ws['%s%d' % (get_column_letter(i), r)].border = Border(top=light)
    for col in pg.footer(block=False):
        # One line per column, wrapped to the table's width in the footer's smaller type: nothing merges, so a
        # longer line (a registry court, every director) would run off the printed page.
        for part in textwrap.wrap(' · '.join(col), int(span * 1.5)):
            put('A%d' % r, part, small)
            r += 1

    for c, wdt in zip(cols, width):
        ws.column_dimensions[letter_of[c]].width = wdt
    ws.sheet_view.showGridLines = False
    ws.page_setup.paperSize = ws.PAPERSIZE_LETTER if pg.paper == 'Letter' else ws.PAPERSIZE_A4
    ws.page_setup.orientation = 'portrait'
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_margins = PageMargins(left=18 / 25.4, right=15 / 25.4, top=18 / 25.4, bottom=18 / 25.4, header=0.3, footer=0.3)
    ws.print_options.horizontalCentered = False
    ws.print_area = 'A1:%s%d' % (last_col, r)
    ws.print_title_rows = '%d:%d' % (head, head)
    wb.save(out)
    save_results(out, cached)


def save_results(path, cached):
    """openpyxl writes formulas without results. Store each result so the workbook shows figures before any recalculation."""
    with zipfile.ZipFile(path) as z:
        parts = {n: z.read(n) for n in z.namelist()}
    name = 'xl/worksheets/sheet1.xml'
    xml = parts[name].decode('utf-8')
    for ref, value in cached.items():
        pat = re.compile(r'(<c r="%s"[^>]*>)(<f>.*?</f>)<v\s*/>|(<c r="%s"[^>]*>)(<f>.*?</f>)<v></v>' % (ref, ref))
        xml, n = pat.subn(lambda m: '%s%s<v>%s</v>' % (m.group(1) or m.group(3), m.group(2) or m.group(4), value), xml, count=1)
        if not n:
            raise RuntimeError('could not store the result of %s' % ref)
    parts[name] = xml.encode('utf-8')
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        for n, data in parts.items():
            z.writestr(n, data)


# What the recipient's part of the page shows: its postal address, and its VAT number in the information block.
RECIPIENT_PRINTS = ('name', 'attention', 'street', 'street2', 'building', 'locality', 'postcode', 'city', 'county',
                    'province', 'state', 'country', 'language', 'vat_id')


def not_printed(spec):
    """Keys the data file gives that this kind of document has no place for. Each is an error with the place
    such a fact can go, never a silent drop."""
    kind = spec.get('type')
    out = []
    only = {'packages': ('delivery_note',), 'gross_weight_kg': ('delivery_note',),
            'quotation': ('purchase_order',), 'requested_delivery_date': ('purchase_order',)}
    for key, kinds in only.items():
        if spec.get(key) not in (None, '', [], {}) and kind not in kinds:
            where = '"references" as {"label": ..., "value": ...}' if key == 'quotation' else \
                '"dates" as {"label": ..., "value": ...}' if key == 'requested_delivery_date' else '"notes"'
            out.append('"%s" is printed on a %s only; on a %s put it in %s'
                       % (key, ' or '.join(kinds).replace('_', ' '), str(kind).replace('_', ' '), where))
    if spec.get('bank') and kind in ('delivery_note', 'purchase_order'):
        out.append('"bank" is not printed on a %s; take it out, or write the account in "notes" if the page must '
                   'carry it' % kind.replace('_', ' '))
    if spec.get('payment_terms') and kind == 'delivery_note':
        out.append('"payment_terms" is not printed on a delivery note, which never shows a price; take it out, or '
                   'write the terms in "notes"')
    for i, l in enumerate(spec.get('lines') or []):
        if not isinstance(l, dict):
            continue
        if kind != 'proforma_invoice':
            out += ['"lines[%d].%s" is printed on a pro forma invoice only; on a %s write it into the line\'s '
                    '"description"' % (i, k, str(kind).replace('_', ' ')) for k in ('hs_code', 'origin') if l.get(k)]
        if kind != 'delivery_note' and l.get('delivered') is not None:
            out.append('"lines[%d].delivered" is printed on a delivery note only' % i)
    role = 'seller' if is_order(spec) else 'buyer'
    them = spec.get(role) if isinstance(spec.get(role), dict) else {}
    lost = sorted(k for k, v in them.items() if k not in RECIPIENT_PRINTS and not k.startswith('_')
                  and v not in (None, '', [], {}, False))
    if lost:
        out.append('"%s" is the recipient here and the page shows its postal address and VAT number only; %s not '
                   'printed. Take %s out, or write what the page must carry in "notes" or as a line of "references"'
                   % (role, ', '.join('"%s.%s"' % (role, k) for k in lost) + (' is' if len(lost) == 1 else ' are'),
                      'it' if len(lost) == 1 else 'them'))
    return out


def main(argv):
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        spec = json.loads(Path(argv[0]).read_text())
        # Nothing given is dropped: an unknown key, a value of the wrong shape or a key this kind of document
        # has no place for stops the build here, before anything is laid out.
        found = spec_guard.problems(spec, spec_guard.load_fields(FIELDS))
        if not found and spec.get('type') in TYPES:
            found = not_printed(spec)
        if found:
            raise ValueError(spec_guard.message(found, 'data file'))
        beside_the_pack = spec_guard.output_problem(argv[1], __file__, 'document')
        if beside_the_pack:
            raise ValueError(beside_the_pack)
        try:
            # The company's own particulars, written once in the person's folder: what the data file leaves out.
            company.apply(spec, argv[0], 'trade-documents')
        except SystemExit as stop:
            raise ValueError(str(stop))
        if spec.get('type') not in TYPES:
            raise ValueError('type must be one of %s' % ', '.join(TYPES))
        unknown = open_keys(spec)
        for key in ('number', 'issue_date', 'seller', 'buyer', 'lines'):
            if not spec.get(key) and not (key == 'number' and 'number' in unknown):
                raise ValueError('the spec needs %r' % key)
        spec.setdefault('number', '')
        if spec['type'] != 'delivery_note' and not spec.get('currency'):
            raise ValueError("the spec needs 'currency'")
        data = compute(spec)
        term = delivery_term(spec)
        out = Path(argv[1])
        writer = {'.docx': write_docx, '.xlsx': write_xlsx, '.pdf': write_pdf}.get(out.suffix.lower())
        if not writer:
            raise ValueError('output must end in .docx, .xlsx or .pdf')
        warnings = []
        if spec['type'] == 'proforma_invoice':
            warnings += ['line %d has no hs_code or origin' % (i + 1) for i, l in enumerate(spec['lines']) if not (l.get('hs_code') and l.get('origin'))]
        if spec['type'] == 'quotation' and not spec.get('dates'):
            warnings.append('a quotation should say until when it is valid: add a "Valid until" date')
        if spec['type'] != 'delivery_note' and not spec.get('payment_terms'):
            warnings.append('no payment_terms given')
        if not term:
            warnings.append('no delivery_terms given')
        if is_order(spec):
            if not spec.get('requested_delivery_date'):
                warnings.append('a purchase order states the requested delivery date: add requested_delivery_date, '
                                'or say in your reply that the files do not give it')
            if not spec.get('deliver_to'):
                warnings.append("no deliver_to: the buyer's own address is printed as the delivery address")
            if crosses_border(spec) and not term:
                warnings.append('the goods cross a border and no delivery_terms is given: a purchase order names the '
                                'Incoterms 2020 rule and place agreed with the supplier; ask, never pick one')
        if 'number' in unknown:
            warnings.append('the document has no number yet and prints none: say in your reply that the person '
                            'numbers it before sending')
        if spec['type'] == 'proforma_invoice' and not spec.get('bank'):
            warnings.append('no bank details: a pro forma is paid before dispatch, so the buyer needs them; say in '
                            'your reply that the person adds them' if 'bank' in unknown else
                            'a pro forma is paid before dispatch and the buyer needs the bank details: take them from '
                            'the files, or list "bank" in "unknown" and say so in your reply')
        warning = company_warning(spec)
        if warning:
            warnings.append(warning)
        writer(spec, out, data)
    except (ValueError, KeyError, json.JSONDecodeError, OSError, RuntimeError) as e:
        print(json.dumps(dict(ok=False, error=str(e))))
        return 1
    lines, vat, net, tax, gross = data
    locale, why = language(spec)
    summary = dict(ok=True, file=str(out), type=spec['type'], language=locale, language_from=why, paper=letter.paper(locale),
                   layout=Page(spec).layout_name(), delivery_terms=term, warnings=warnings)
    if spec['type'] != 'delivery_note':
        summary.update(total_excluding_vat=str(net), vat=[dict(rate=str(r), taxable=str(b), vat=str(v)) for r, b, v in vat],
                       total_vat=str(tax), total_including_vat=str(gross))
        if data.money['allowances']:
            summary['allowances_total'] = str(data.money['allowance_total'])
        if data.money['paid']:
            summary.update(paid=str(data.money['paid']), amount_due=str(data.money['due']))
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
