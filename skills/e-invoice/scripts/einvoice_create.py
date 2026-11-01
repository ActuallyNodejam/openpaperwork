#!/usr/bin/env python3
"""Create an EN 16931 e-invoice (UN/CEFACT Cross Industry Invoice XML, the Factur-X syntax) from a JSON spec.

Usage: einvoice_create.py spec.json invoice.xml

Spec:
{
  "number": "2026-0412", "issue_date": "2026-10-05", "due_date": "2026-11-04",
  "delivery_date": "2026-10-05", "currency": "EUR", "note": "optional free text",
  "seller": {"name": "...", "street": "...", "postcode": "...", "city": "...", "country": "SE", "vat_id": "SE..."},
  "buyer":  {"name": "...", "street": "...", "postcode": "...", "city": "...", "country": "SE", "vat_id": "SE..."},
  "payment": {"means_code": "58", "iban": "SE35 5000 0000 0549 1000 0003"},
  "order_reference": "PO-2026-311",
  "lines": [{"name": "Design workshop", "quantity": 2, "unit": "C62", "unit_price": 4500.00,
             "discount_percent": 0, "vat_rate": 25, "vat_category": "S"}]
}

A Swedish seller paid to a Bankgiro or PlusGiro number gives "payment": {"bankgiro": "123-4566"} (or
"plusgiro") in place of the IBAN; the means code is then 30 unless the spec says otherwise, and the file
carries the number as the payment account (BT-84). The build stops on a number whose check digit fails.
The buyer's order number is "order_reference" (BT-13), beside their reference "buyer_reference" (BT-10).

Amounts follow EN 16931: each line net is quantity x unit price less the discount, rounded to two
decimals; VAT is calculated once per category and rate on the sum of its line nets. The file states
every total, so a validator can check the arithmetic. vat_category is S (standard), Z (zero rated),
E (exempt), AE (reverse charge), K (intra-community supply) or G (export); AE, E, K and G need
"exemption_reason" on the line or at the top level. unit is a UN/ECE Rec 20 code (C62 is "one").
An invoice in a currency other than the seller's national one adds "tax_currency" (SEK, DKK, ...)
and "exchange_rate", so the VAT is stated in both (VAT Directive Art. 230, EN 16931 BT-6, BT-111).

A credit note is type 381 (BT-3): "type_code": "381", its own "number", and the invoice it amends as
"preceding_invoice" and "preceding_invoice_date" (BT-25, BT-26; BR-55; VAT Directive Art. 219). Its
amounts are positive: the type code carries the sign. A spec that names a preceding invoice and no type
code is a credit note, the same way the page builder reads it.

A buyer who asks for XRechnung (a German public buyer, or any buyer who says so) adds "xrechnung": true,
"buyer_reference" (BT-10, the Leitweg-ID of a public buyer) and the seller's contact as
"seller": {"contact": {"name": "...", "phone": "...", "email": "..."}} (BG-6). The build stops and
names what is missing under the German rules of the KoSIT XRechnung schematron (BR-DE-1, -2, -3, -4,
-5, -6, -7, -8, -9, -15, -23-a). The specification identifier (BT-24) then names XRechnung 3.0, the
business process (BT-23) the Peppol billing process, and both parties need an electronic address
("electronic_address", BT-34 and BT-49), which XRechnung 3.0 requires (PEPPOL-EN16931-R010, -R020).

A French seller (seller country FR) writes the invoice the French reform reads (CGI annexe II
art. 242 nonies A; Code de commerce L441-9, L441-10, D441-5; the FNFE-MPE France_RFE rules, Apache-2.0,
for AFNOR XP Z12-012): "siren" (and "siret") for the seller and a French buyer (BT-30, BT-47, scheme
0002; BT-29, BT-46, scheme 0009), "legal_form", "share_capital" and "rcs" for a company, "operation"
(goods, services or both: the nature of the operation, BT-23 B1, S1 or M1), "delivery_address" when the
goods go elsewhere (BG-15), "vat_on_debits": true when the seller opted to pay VAT on debits (BT-8 = 5),
"late_penalty_rate" and "early_payment_discount" (the notes PMD and AAB; the 40 euro recovery
indemnity is the note PMT). The build stops on what only the person can give and names it.

A Norwegian, Danish, Finnish, British, Belgian, Dutch, Austrian or Irish seller gets Peppol BIS Billing 3.0 in
UBL instead (scripts/ubl_create.py), a Finnish spec with "syntax": "finvoice" gets Finvoice 3.0
(scripts/finvoice_create.py), an Austrian one with "syntax": "ebinterface" ebInterface 6.1
(scripts/ebinterface_create.py), and "syntax": "cii"
keeps this file's CII; scripts/countries.py holds each country's rules. A Spanish seller gets Facturae 3.2.2,
unsigned (scripts/facturae_create.py), an Italian one FatturaPA 1.2.3 (scripts/fatturapa_create.py) and a
Polish one the KSeF structure FA(3) (scripts/ksef_create.py): the files their states take, none of them sent.

Prints a JSON summary with the totals. Standard library only.
"""
import re
import argparse
import json
import sys
from decimal import Decimal, ROUND_HALF_UP
from xml.etree import ElementTree as ET
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '_shared'))
import doc_amounts  # noqa: E402

RSM = 'urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100'
RAM = 'urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100'
UDT = 'urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100'
QDT = 'urn:un:unece:uncefact:data:standard:QualifiedDataType:100'
PROFILE = 'urn:cen.eu:en16931:2017'
# The specification identifier (BT-24) of XRechnung 3.0, as the KoSIT schematron expects it (BR-DE-21).
# It is an identifier the buyer's system routes on, not a statement about the file.
XRECHNUNG = 'urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0'
# The business process (BT-23) XRechnung 3.0 asks for (PEPPOL-EN16931-R001): Peppol BIS billing.
PEPPOL_BILLING = 'urn:fdc:peppol.eu:2017:poacc:billing:01:1.0'
# France: the nature of the operation (CGI annexe II art. 242 nonies A I 8° bis) carried as the
# billing framework (cadre de facturation, BT-23) of XP Z12-012, rule BR-FR-08: B1 goods, S1 services,
# M1 both, for an invoice submitted in the ordinary way.
OPERATION = {'goods': 'B1', 'services': 'S1', 'both': 'M1'}
OPERATION_WORDS = {'goods': 'goods', 'biens': 'goods', 'livraison de biens': 'goods', 'livraisons de biens': 'goods',
                   'services': 'services', 'prestations de services': 'services', 'prestation de services': 'services',
                   'both': 'both', 'mixed': 'both', 'mixte': 'both', 'les deux': 'both', 'goods and services': 'both',
                   'biens et services': 'both'}
# The VAT rates the French rules accept (BR-FR-16), in percent.
FR_RATES = {'0', '10', '13', '20', '8.5', '19.6', '2.1', '5.5', '7', '20.6', '1.05', '0.9', '1.75', '9.2', '9.6'}
# The legal forms of companies registered at the trade and companies register (RCS), whose invoices
# state their legal form, share capital and the RCS with its city (service-public.fr F31808).
FR_COMPANY_FORMS = {'SA', 'SAS', 'SASU', 'SARL', 'EURL', 'SNC', 'SCA', 'SCS', 'SE', 'SELARL', 'SELAS'}
# The statutory late-payment rate when the terms give none: the ECB's most recent refinancing rate
# plus 10 percentage points (Code de commerce L441-10 II).
FR_DEFAULT_PENALTY = ("taux d'intérêt appliqué par la Banque centrale européenne à son opération de "
                      "refinancement la plus récente majoré de 10 points de pourcentage")
# service-public.fr F31808 gives this wording for an invoice that grants no early-payment discount.
FR_NO_DISCOUNT = "Escompte pour paiement anticipé : néant"


def r2(x):
    return Decimal(str(x)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def el(parent, ns, tag, text=None, **attrs):
    e = ET.SubElement(parent, '{%s}%s' % (ns, tag), attrs)
    if text is not None:
        e.text = str(text)
    return e


def date(parent, tag, iso):
    d = el(parent, RAM, tag)
    el(d, UDT, 'DateTimeString', iso.replace('-', ''), format='102')


def contact_of(p):
    """(name, phone, email) of a party's contact: its "contact" block, else its own phone and email."""
    c = p.get('contact') if isinstance(p.get('contact'), dict) else {}
    return c.get('name') or p.get('contact_name'), c.get('phone') or p.get('phone'), c.get('email') or p.get('email')


def type_code(spec):
    """381 is a credit note (BT-3). A spec that names the invoice it amends and gives no code is one."""
    return str(spec.get('type_code') or ('381' if spec.get('preceding_invoice') else '380'))


def country(p):
    return str((p or {}).get('country') or '').strip().upper()


def is_french(spec):
    """A French seller's invoice follows the French rules, whatever the buyer's country."""
    return country(spec.get('seller')) == 'FR'


def digits(value):
    return re.sub(r'\D', '', str(value or ''))


def luhn(number):
    """The check digit SIREN and SIRET numbers carry (the Luhn algorithm INSEE uses)."""
    total = 0
    for i, c in enumerate(reversed(number)):
        d = int(c) * (2 if i % 2 else 1)
        total += d - 9 if d > 9 else d
    return total % 10 == 0


def operation_of(spec):
    """goods, services or both, from the spec's "operation" in English or French; '' when not given."""
    raw = str(spec.get('operation') or '').strip().lower()
    return OPERATION_WORDS.get(raw, raw if raw in OPERATION else '')


def electronic_address(p):
    """(scheme, id) of the electronic address a party gives (BT-34, BT-49). A string with @ is an email
    (EM), nine digits (with a _suffix) a French directory address (0225); {"scheme": ..., "id": ...}
    names its scheme."""
    raw = (p or {}).get('electronic_address')
    if isinstance(raw, dict) and raw.get('id'):
        return str(raw.get('scheme') or ('EM' if '@' in str(raw['id']) else '')), str(raw['id'])
    if isinstance(raw, str) and raw.strip():
        raw = raw.strip()
        # "0192:999999999": a Peppol participant identifier, the EAS scheme and the id.
        scheme_id = re.fullmatch(r'(\d{4}):(\S+)', raw)
        if scheme_id:
            return scheme_id.group(1), scheme_id.group(2)
        if '@' in raw:
            return 'EM', raw
        if re.fullmatch(r'\d{9}(_[A-Za-z0-9._-]+)?', raw):
            return '0225', raw
        return '', raw
    return None


def address_for(spec, role):
    """(address, why) for a party: the one the spec gives; else, for a French party, its SIREN in the
    French directory (scheme 0225); for an XRechnung, the public buyer's Leitweg-ID (scheme 0204) and
    the seller contact's email (EM). why says which default was taken, None when the spec gave it."""
    p = spec.get(role) or {}
    given = electronic_address(p)
    if given:
        return given, None
    if is_french(spec) and len(digits(p.get('siren'))) == 9:
        return ('0225', digits(p['siren'])), 'its SIREN in the French directory (scheme 0225)'
    if spec.get('xrechnung'):
        if role == 'buyer' and spec.get('buyer_reference'):
            return ('0204', str(spec['buyer_reference'])), 'its Leitweg-ID %s (scheme 0204)' % spec['buyer_reference']
        email = contact_of(p)[2]
        if role == 'seller' and email:
            return ('EM', email), 'the seller contact\'s email %s' % email
    return None, None


def treatment(spec):
    """The French treatment note (BAR, BR-FR-20): B2B for a French buyer, which puts the invoice in
    the e-invoicing scope, B2BINT for a business buyer abroad."""
    if not is_french(spec):
        return None
    return spec.get('fr_treatment') or ('B2B' if country(spec.get('buyer')) == 'FR' else 'B2BINT')


def capital_text(value):
    """10000 -> 10 000 €: the share capital as a French page writes it."""
    if isinstance(value, (int, float)) or re.fullmatch(r'[\d.]+', str(value or '')):
        whole = '{:,}'.format(int(Decimal(str(value)))).replace(',', ' ')
        return '%s €' % whole
    return str(value)


def fr_company_line(p):
    """SAS au capital de 10 000 € · RCS Lyon 000 000 018: what a French company's invoice says of it."""
    parts = []
    if p.get('legal_form'):
        parts.append(('%s au capital de %s' % (p['legal_form'], capital_text(p['share_capital'])))
                     if p.get('share_capital') not in (None, '') else str(p['legal_form']))
    siren = digits(p.get('siren'))
    if p.get('rcs') and siren:
        parts.append('%s %s' % (p['rcs'], ' '.join((siren[:3], siren[3:6], siren[6:]))))
    return parts


def fr_notes(spec):
    """The notes French invoices carry (XP Z12-012 BR-FR-05): PMD the late-payment penalties, PMT the
    40 euro recovery indemnity, AAB the early-payment discount or its absence (Code de commerce L441-9,
    L441-10, D441-5); and BAR the treatment. Returns [(subject code, text)]."""
    if not is_french(spec):
        return []
    rate = spec.get('late_penalty_rate')
    if isinstance(rate, (int, float)) or re.fullmatch(r'[\d.,]+', str(rate or '')):
        rate = '%s %% par an' % str(rate).replace('.', ',')
    discount = str(spec.get('early_payment_discount') or '').strip()
    if discount.lower() in ('', 'none', 'no', 'néant', 'neant', 'aucun', 'aucune'):
        discount = FR_NO_DISCOUNT
    elif not discount.lower().startswith('escompte'):
        discount = 'Escompte pour paiement anticipé : %s' % discount
    notes = [('PMD', 'Pénalités de retard exigibles le jour suivant la date de règlement : %s' % (rate or FR_DEFAULT_PENALTY)),
             ('PMT', 'Indemnité forfaitaire pour frais de recouvrement en cas de retard de paiement : 40 €'),
             ('AAB', discount)]
    bar = treatment(spec)
    if bar:
        notes.append(('BAR', bar))
    return notes


def refuse_french(spec):
    """What a French seller's invoice needs (CGI annexe II art. 242 nonies A; Code de commerce L441-9;
    service-public.fr F31808; XP Z12-012 BR-FR rules) that the spec does not give. Returns (missing, warnings)."""
    missing, warnings = [], []
    seller, buyer = spec.get('seller') or {}, spec.get('buyer') or {}
    siren = digits(seller.get('siren'))
    if len(siren) != 9:
        missing.append('seller.siren: the seller\'s nine-digit SIREN (242 nonies A I 1°; BR-FR-10, BT-30)')
    elif not luhn(siren):
        warnings.append('seller.siren %s fails its check digit; read it again from the person\'s files' % siren)
    if seller.get('siret') and not digits(seller['siret']).startswith(siren):
        missing.append('seller.siret %s does not start with the SIREN %s (BR-FR-09)' % (seller['siret'], siren))
    form = str(seller.get('legal_form') or '').strip()
    if not form:
        missing.append('seller.legal_form: SAS, SARL, SA, EI ... (service-public.fr F31808)')
    elif form.upper() in FR_COMPANY_FORMS:
        # Nobody may make one of these up: the order may declare it unknown, the page then prints nothing in
        # its place and the pack check warns (EINV-PARTICULARS). An SNC or SCS states no capital (R123-238).
        import countries                       # lazily, as document_xml does
        unknown = countries.particulars.unknown_of(spec)
        way_out = ('; if the person\'s files do not give it, add "%s" to the seller\'s "unknown" and say so in '
                   'the reply, never make one up')
        if seller.get('share_capital') in (None, '') and 'share_capital' not in unknown \
                and form.upper() not in ('SNC', 'SCS'):
            missing.append('seller.share_capital: a %s states its share capital on its invoices (Code de '
                           'commerce R123-238; F31808)' % form + way_out % 'share_capital')
        if not seller.get('rcs') and 'rcs' not in unknown:
            missing.append('seller.rcs: "RCS" and the city of its register, as "RCS Lyon" (Code de commerce '
                           'R123-237; F31808)' + way_out % 'rcs')
    if country(buyer) == 'FR':
        bsiren = digits(buyer.get('siren'))
        if len(bsiren) != 9:
            missing.append('buyer.siren: a French buyer\'s SIREN, on every invoice from 1 September 2026 '
                           '(242 nonies A I 1°; BR-FR-11, BT-47)')
        elif not luhn(bsiren):
            warnings.append('buyer.siren %s fails its check digit; read it again from the person\'s files' % bsiren)
    if not operation_of(spec):
        missing.append('operation: goods, services or both, the nature of what is invoiced (242 nonies A I 8° bis; '
                       'BT-23, BR-FR-08)')
    if type_code(spec) == '380' and not spec.get('due_date'):
        missing.append('due_date: the date payment is due (Code de commerce L441-9)')
    if not spec.get('late_penalty_rate'):
        warnings.append('no late_penalty_rate: the invoice states the statutory rate, the ECB rate plus 10 points '
                        '(Code de commerce L441-10 II); say so in your reply')
    if not spec.get('early_payment_discount'):
        warnings.append('no early_payment_discount: the invoice says "%s"; say so in your reply' % FR_NO_DISCOUNT)
    for role in ('seller', 'buyer'):
        address, why = address_for(spec, role)
        if why:
            warnings.append('%s.electronic_address not given: the %s is addressed at %s; use the address it '
                            'gave if it has one' % (role, role, why))
    rates = {format(Decimal(str(l.get('vat_rate', 0))).normalize(), 'f') for l in spec.get('lines', [])}
    odd = sorted(r for r in rates if r not in FR_RATES)
    if odd:
        warnings.append('VAT rate(s) %s %% are not French rates (BR-FR-16); check them' % ', '.join(odd))
    return missing, warnings


def refuse(spec):
    """What a credit note or an XRechnung buyer needs that the spec does not give, by rule. The build
    stops on any of it: nothing here is filled in by guess. Returns the warnings that do not stop it."""
    missing, warnings = [], []
    if type_code(spec) == '381':
        if not spec.get('preceding_invoice'):
            missing.append('preceding_invoice: the number of the invoice this credit note amends (BT-25, BR-55; VAT Directive Art. 219)')
        elif not spec.get('preceding_invoice_date'):
            # EN 16931 asks for the number (BR-55); the date makes the reference unambiguous (BT-26) and the
            # pack check asks for it, so the reply must say it is missing.
            warnings.append('no preceding_invoice_date: give the issue date of invoice %s (BT-26) or say in your reply '
                            'that the files do not have it' % spec['preceding_invoice'])
        if spec.get('preceding_invoice') and str(spec.get('number')) == str(spec['preceding_invoice']):
            missing.append('number: a credit note has its own number, not the invoice\'s %s (BT-1)' % spec['number'])
        negative = [l.get('name', '?') for l in spec.get('lines', [])
                    if Decimal(str(l.get('quantity', 0))) < 0 or Decimal(str(l.get('unit_price', 0))) < 0]
        if negative:
            missing.append('positive quantity and unit_price on %s: the type code 381 carries the sign' % ', '.join(negative))
    # A Swedish seller is paid to its Bankgiro or PlusGiro number; one with a wrong check digit sends the
    # money nowhere, so the build stops and asks rather than print it.
    giro = spec.get('payment') or {}
    for key, size in (('bankgiro', (7, 8)), ('plusgiro', tuple(range(2, 9)))):
        if giro.get(key) and not (len(digits(giro[key])) in size and luhn(digits(giro[key]))):
            missing.append('payment.%s %s: a %s number has %s digits and ends in a modulus 10 check digit; '
                           'ask for it' % (key, giro[key], 'Bankgiro' if key == 'bankgiro' else 'PlusGiro',
                                           'seven or eight' if key == 'bankgiro' else 'two to eight'))
    # An intra-community supply names the country the goods went to (BT-80, BR-IC-12); the validator rejects
    # the file without it, so the build asks first. The buyer's address does not stand in: goods can go elsewhere.
    ship = spec.get('delivery_address') if isinstance(spec.get('delivery_address'), dict) else {}
    if any(l.get('vat_category') == 'K' for l in spec.get('lines', [])) and not (ship.get('street') or ship.get('city')):
        missing.append('delivery_address: where the goods were delivered, at least a city and its country, for an '
                       'intra-community supply (BT-80, BR-IC-12)')
    if spec.get('xrechnung'):
        # The German rules, from the KoSIT XRechnung schematron (Apache-2.0), restated.
        if not spec.get('buyer_reference'):
            missing.append('buyer_reference: the buyer reference, a public buyer\'s Leitweg-ID (BT-10, BR-DE-15)')
        pay = spec.get('payment') or {}
        if not pay:
            missing.append('payment: the payment instructions (BG-16, BR-DE-1)')
        elif str(pay.get('means_code', '58')) in ('30', '58') and not pay.get('iban'):
            missing.append('payment.iban: the account for a credit transfer (BG-17, BR-DE-23-a)')
        name, phone, email = contact_of(spec.get('seller') or {})
        for value, field, rule in ((name, 'name', 'BT-41, BR-DE-5'), (phone, 'phone', 'BT-42, BR-DE-6'),
                                   (email, 'email', 'BT-43, BR-DE-7')):
            if not value:
                missing.append('seller.contact.%s: the seller contact (BG-6, BR-DE-2; %s)' % (field, rule))
        for role, rules in (('seller', ('BR-DE-3', 'BR-DE-4')), ('buyer', ('BR-DE-8', 'BR-DE-9'))):
            p = spec.get(role) or {}
            if not p.get('city'):
                missing.append('%s.city (%s)' % (role, rules[0]))
            if not p.get('postcode'):
                missing.append('%s.postcode (%s)' % (role, rules[1]))
        # XRechnung 3.0 takes the Peppol rules for the parties' electronic addresses; the KoSIT
        # validator rejects an XRechnung without them. A public buyer's is often its Leitweg-ID.
        for role, rule, bt in (('seller', 'PEPPOL-EN16931-R020', 'BT-34'), ('buyer', 'PEPPOL-EN16931-R010', 'BT-49')):
            address, why = address_for(spec, role)
            if not address:
                missing.append('%s.electronic_address: where the %s receives e-invoices, an email or '
                               '{"scheme": ..., "id": ...} (%s, %s)' % (role, role, bt, rule))
            elif why:
                warnings.append('%s.electronic_address not given: the XRechnung uses %s (%s); say so in your reply'
                                % (role, why, bt))
    for role in ('seller', 'buyer'):
        address = electronic_address(spec.get(role))
        if address and not address[0]:
            missing.append('%s.electronic_address %s: name its scheme, {"scheme": "EM" or an ISO 6523 / EAS code, '
                           '"id": ...} (EN 16931 BR-62, BR-63)' % (role, address[1]))
    if is_french(spec):
        missing_fr, warn_fr = refuse_french(spec)
        missing += missing_fr
        warnings += warn_fr
    if missing:
        raise SystemExit('the spec lacks what this document needs; ask the person for it, never guess:\n  - '
                         + '\n  - '.join(missing))
    return warnings


def party(parent, tag, p, french=False, address=None):
    e = el(parent, RAM, tag)
    siren, siret = digits(p.get('siren')), digits(p.get('siret'))
    # A French establishment's SIRET is its global identifier (BT-29, BT-46; scheme 0009, BR-FR-09).
    if french and len(siret) == 14:
        el(e, RAM, 'GlobalID', siret, schemeID='0009')
    el(e, RAM, 'Name', p['name'])
    if tag == 'SellerTradeParty':
        # The details EU company law asks for on a company's letters (Directive (EU) 2017/1132
        # Art. 26): additional legal information (BT-33) and the registration number (BT-30).
        legal = [('Sitz/Registered office: %s' % p['registered_office']) if p.get('registered_office') else None,
                 ', '.join(x for x in (p.get('register'), p.get('register_number')) if x) or None,
                 ', '.join(p['managing_directors']) if isinstance(p.get('managing_directors'), list) else p.get('managing_directors')]
        if french:
            legal = fr_company_line(p) + legal[:1]
        legal = [x for x in legal if x]
        if legal:
            el(e, RAM, 'Description', '; '.join(legal))
    # The legal registration identifier (BT-30, BT-47): a French SIREN under scheme 0002, else the
    # register number the seller or the buyer gives, such as a Swedish customer's organisationsnummer.
    if french and len(siren) == 9:
        el(el(e, RAM, 'SpecifiedLegalOrganization'), RAM, 'ID', siren, schemeID='0002')
    elif p.get('register_number'):
        el(el(e, RAM, 'SpecifiedLegalOrganization'), RAM, 'ID', p['register_number'])
    if tag == 'SellerTradeParty':
        # The seller contact (BG-6): contact point, phone and email (BT-41, BT-42, BT-43).
        name, phone, email = contact_of(p)
        if name or phone or email:
            c = el(e, RAM, 'DefinedTradeContact')
            if name:
                el(c, RAM, 'PersonName', name)
            if phone:
                el(el(c, RAM, 'TelephoneUniversalCommunication'), RAM, 'CompleteNumber', phone)
            if email:
                el(el(c, RAM, 'EmailURIUniversalCommunication'), RAM, 'URIID', email)
    a = el(e, RAM, 'PostalTradeAddress')
    if p.get('postcode'):
        el(a, RAM, 'PostcodeCode', p['postcode'])
    if p.get('street'):
        el(a, RAM, 'LineOne', p['street'])
    if p.get('city'):
        el(a, RAM, 'CityName', p['city'])
    el(a, RAM, 'CountryID', p['country'])
    # The party's electronic address (BT-34, BT-49), where e-invoices reach it.
    if address:
        el(el(e, RAM, 'URIUniversalCommunication'), RAM, 'URIID', address[1], **({'schemeID': address[0]} if address[0] else {}))
    if p.get('vat_id'):
        t = el(e, RAM, 'SpecifiedTaxRegistration')
        el(t, RAM, 'ID', p['vat_id'], schemeID='VA')


def compute_full(spec):
    """(lines, groups, settlement): the lines with their discount (EN 16931-1 BG-27), the VAT groups with their
    taxable amount after the document's allowances (BG-20), and the money of the document (doc_amounts.settle:
    line total, allowances, total without VAT, VAT, grand total, paid amount, amount due)."""
    lines, groups = [], {}
    for i, l in enumerate(spec['lines'], 1):
        qty, price = Decimal(str(l['quantity'])), Decimal(str(l['unit_price']))
        a = doc_amounts.line_amounts(l, i)
        cat, rate = l.get('vat_category', 'S'), Decimal(str(l.get('vat_rate', 0)))
        reason = l.get('exemption_reason') or spec.get('exemption_reason')
        # BT-158 and BT-159: an export line's customs code and the country its goods come from.
        hs, origin = str(l.get('hs_code') or '').strip(), str(l.get('origin') or '').strip().upper()
        hs = re.sub(r'[\s.]', '', hs) if re.fullmatch(r'[\d\s.]+', hs) else hs  # the code's digits: 8204.11 -> 820411
        if origin and not re.fullmatch(r'[A-Z]{2}', origin):
            raise SystemExit('line %d: "origin" is the ISO 3166 two-letter code of the country the goods come '
                             'from (SE, DE, CN), not %r' % (i, l.get('origin')))
        lines.append(dict(id=i, name=l['name'], qty=qty, unit=l.get('unit', 'C62'), price=price, net_price=price,
                          net=a['net'], base=a['base'], disc=a['discount'], pct=a['percent'], disc_reason=a['reason'],
                          disc_code=str(l.get('discount_reason_code') or ''), cat=cat, rate=rate, hs=hs, origin=origin))
        groups.setdefault((cat, rate), dict(base=Decimal(0), reason=reason,
                                            code=l.get('exemption_code') or spec.get('exemption_code')))
    money = doc_amounts.settle(spec, lines)
    for k, g in groups.items():
        g['base'] = money['groups'][k]
    return lines, groups, money


def compute(spec):
    """The tuple every syntax builder reads: lines, VAT groups, VAT per group, total without VAT (after the
    document's allowances), total VAT, total with VAT."""
    lines, groups, money = compute_full(spec)
    return lines, groups, money['tax'], money['basis'], money['tax_total'], money['grand']


def indicator(parent, value=False):
    el(el(parent, RAM, 'ChargeIndicator'), UDT, 'Indicator', 'true' if value else 'false')


def line_allowance(settle, l):
    """A line discount as a line allowance (BG-27): BT-138 the percentage, BT-137 the amount it is worked out
    from, BT-136 the amount, BT-139/BT-140 the reason and its UNCL 5189 code (95, discount, unless the order
    names one). Written only when the line has a discount."""
    if not l['disc']:
        return
    ac = el(settle, RAM, 'SpecifiedTradeAllowanceCharge')
    indicator(ac)
    if l['pct']:
        el(ac, RAM, 'CalculationPercent', l['pct'].normalize() if l['pct'] != l['pct'].to_integral() else int(l['pct']))
    if l['pct']:
        el(ac, RAM, 'BasisAmount', l['base'])          # BT-137 goes with BT-138
    el(ac, RAM, 'ActualAmount', l['disc'])
    el(ac, RAM, 'ReasonCode', l['disc_code'] or '95')
    el(ac, RAM, 'Reason', l['disc_reason'] or 'Discount')


def document_allowance(settle, a):
    """An allowance on the whole document (BG-20): BT-94, BT-93, BT-92, BT-98, BT-97 and its VAT category and
    rate (BT-95, BT-96)."""
    ac = el(settle, RAM, 'SpecifiedTradeAllowanceCharge')
    indicator(ac)
    if a['percent'] is not None:
        el(ac, RAM, 'CalculationPercent', a['percent'].normalize() if a['percent'] != a['percent'].to_integral() else int(a['percent']))
    if a['base'] is not None:
        el(ac, RAM, 'BasisAmount', a['base'])
    el(ac, RAM, 'ActualAmount', a['amount'])
    if a['code']:
        el(ac, RAM, 'ReasonCode', a['code'])
    if a['reason']:
        el(ac, RAM, 'Reason', a['reason'])
    t = el(ac, RAM, 'CategoryTradeTax')
    el(t, RAM, 'TypeCode', 'VAT')
    el(t, RAM, 'CategoryCode', a['cat'])
    el(t, RAM, 'RateApplicablePercent', a['rate'].normalize() if a['rate'] != a['rate'].to_integral() else int(a['rate']))


def build(spec):
    warnings = refuse(spec)
    lines, groups, money = compute_full(spec)
    tax, net_total, tax_total, gross = money['tax'], money['basis'], money['tax_total'], money['grand']
    cur = spec.get('currency', 'EUR')
    ET.register_namespace('rsm', RSM); ET.register_namespace('ram', RAM); ET.register_namespace('udt', UDT)
    ET.register_namespace('qdt', QDT)
    root = ET.Element('{%s}CrossIndustryInvoice' % RSM)
    french = is_french(spec)
    ctx = el(root, RSM, 'ExchangedDocumentContext')
    # The business process (BT-23): Peppol billing for XRechnung, the French billing framework (B1, S1,
    # M1 from the nature of the operation) for a French seller, or what the spec names.
    process = spec.get('business_process') or (PEPPOL_BILLING if spec.get('xrechnung') else
                                               OPERATION.get(operation_of(spec)) if french else None)
    if process:
        el(el(ctx, RAM, 'BusinessProcessSpecifiedDocumentContextParameter'), RAM, 'ID', process)
    el(el(ctx, RAM, 'GuidelineSpecifiedDocumentContextParameter'), RAM, 'ID', XRECHNUNG if spec.get('xrechnung') else PROFILE)
    doc = el(root, RSM, 'ExchangedDocument')
    el(doc, RAM, 'ID', spec['number'])
    el(doc, RAM, 'TypeCode', type_code(spec))
    date(doc, 'IssueDateTime', spec['issue_date'])
    if spec.get('note'):
        el(el(doc, RAM, 'IncludedNote'), RAM, 'Content', spec['note'])
    # The French mentions as coded notes (BG-1: BT-22 the text, BT-21 its subject code).
    for subject, content in fr_notes(spec):
        n = el(doc, RAM, 'IncludedNote')
        el(n, RAM, 'Content', content)
        el(n, RAM, 'SubjectCode', subject)
    tx = el(root, RSM, 'SupplyChainTradeTransaction')
    for l in lines:
        item = el(tx, RAM, 'IncludedSupplyChainTradeLineItem')
        el(el(item, RAM, 'AssociatedDocumentLineDocument'), RAM, 'LineID', l['id'])
        product = el(item, RAM, 'SpecifiedTradeProduct')
        el(product, RAM, 'Name', l['name'])
        if l.get('hs'):
            el(el(product, RAM, 'DesignatedProductClassification'), RAM, 'ClassCode', l['hs'], listID='HS')
        if l.get('origin'):
            el(el(product, RAM, 'OriginTradeCountry'), RAM, 'ID', l['origin'])
        agr = el(item, RAM, 'SpecifiedLineTradeAgreement')
        el(el(agr, RAM, 'NetPriceProductTradePrice'), RAM, 'ChargeAmount', l['net_price'].normalize() if l['net_price'] != l['net_price'].to_integral() else r2(l['net_price']))
        el(el(item, RAM, 'SpecifiedLineTradeDelivery'), RAM, 'BilledQuantity', l['qty'].normalize() if l['qty'] != l['qty'].to_integral() else int(l['qty']), unitCode=l['unit'])
        st = el(item, RAM, 'SpecifiedLineTradeSettlement')
        t = el(st, RAM, 'ApplicableTradeTax')
        el(t, RAM, 'TypeCode', 'VAT')
        el(t, RAM, 'CategoryCode', l['cat'])
        el(t, RAM, 'RateApplicablePercent', l['rate'].normalize() if l['rate'] != l['rate'].to_integral() else int(l['rate']))
        line_allowance(st, l)
        el(el(st, RAM, 'SpecifiedTradeSettlementLineMonetarySummation'), RAM, 'LineTotalAmount', l['net'])
    agr = el(tx, RAM, 'ApplicableHeaderTradeAgreement')
    if spec.get('buyer_reference'):
        el(agr, RAM, 'BuyerReference', spec['buyer_reference'])
    party(agr, 'SellerTradeParty', spec['seller'], french, address_for(spec, 'seller')[0])
    party(agr, 'BuyerTradeParty', spec['buyer'], french, address_for(spec, 'buyer')[0])
    # The buyer's order number (BT-13), beside their reference (BT-10).
    if spec.get('order_reference'):
        el(el(agr, RAM, 'BuyerOrderReferencedDocument'), RAM, 'IssuerAssignedID', spec['order_reference'])
    dlv = el(tx, RAM, 'ApplicableHeaderTradeDelivery')
    # Where the goods go when it is not the buyer's address (BG-13, BG-15; for France 242 nonies A I 7° bis).
    ship = spec.get('delivery_address')
    if isinstance(ship, dict) and (ship.get('street') or ship.get('city')):
        to = el(dlv, RAM, 'ShipToTradeParty')
        if ship.get('name'):
            el(to, RAM, 'Name', ship['name'])
        a = el(to, RAM, 'PostalTradeAddress')
        for key, tag in (('postcode', 'PostcodeCode'), ('street', 'LineOne'), ('city', 'CityName')):
            if ship.get(key):
                el(a, RAM, tag, ship[key])
        el(a, RAM, 'CountryID', ship.get('country') or spec['buyer']['country'])
    ev = el(dlv, RAM, 'ActualDeliverySupplyChainEvent')
    date(ev, 'OccurrenceDateTime', spec.get('delivery_date', spec['issue_date']))
    st = el(tx, RAM, 'ApplicableHeaderTradeSettlement')
    # VAT Directive Art. 230: an invoice in another currency states the VAT in the seller's
    # national one too. EN 16931 carries it as the VAT accounting currency (BT-6) and the VAT
    # total in it (BT-111).
    tax_cur = spec.get('tax_currency')
    if tax_cur and tax_cur != cur:
        el(st, RAM, 'TaxCurrencyCode', tax_cur)
    el(st, RAM, 'InvoiceCurrencyCode', cur)
    pay = spec.get('payment') or {}
    if pay:
        giro = pay.get('bankgiro') or pay.get('plusgiro')
        pm = el(st, RAM, 'SpecifiedTradeSettlementPaymentMeans')
        el(pm, RAM, 'TypeCode', pay.get('means_code', '30' if giro and not pay.get('iban') else '58'))
        if pay.get('iban'):
            el(el(pm, RAM, 'PayeePartyCreditorFinancialAccount'), RAM, 'IBANID', pay['iban'].replace(' ', ''))
        elif giro or pay.get('account'):
            # A Swedish Bankgiro or PlusGiro number, or another account without an IBAN (BT-84).
            el(el(pm, RAM, 'PayeePartyCreditorFinancialAccount'), RAM, 'ProprietaryID', digits(giro or pay['account']))
    for (cat, rate), g in sorted(groups.items(), key=lambda kv: (kv[0][0], -kv[0][1])):
        t = el(st, RAM, 'ApplicableTradeTax')
        el(t, RAM, 'CalculatedAmount', tax[(cat, rate)])
        el(t, RAM, 'TypeCode', 'VAT')
        if cat in ('AE', 'E', 'K', 'G', 'O'):
            # A French reverse charge says Autoliquidation (242 nonies A I 13°).
            default = {'AE': 'Autoliquidation' if french else 'Reverse charge'}.get(cat, 'Exempt')
            el(t, RAM, 'ExemptionReason', g['reason'] or default)
        el(t, RAM, 'BasisAmount', r2(g['base']))
        el(t, RAM, 'CategoryCode', cat)
        if g.get('code'):
            el(t, RAM, 'ExemptionReasonCode', g['code'])
        # VAT due on debits (BT-8 = 5, the invoice date): the French option for paying VAT on debits
        # (242 nonies A I 11° bis; XP Z12-012 BR-FR-MAP-03), on the taxed groups.
        if spec.get('vat_on_debits') and cat == 'S':
            el(t, RAM, 'DueDateTypeCode', '5')
        el(t, RAM, 'RateApplicablePercent', rate.normalize() if rate != rate.to_integral() else int(rate))
    for a in money['allowances']:
        document_allowance(st, a)
    terms = el(st, RAM, 'SpecifiedTradePaymentTerms')
    if spec.get('payment_terms'):
        el(terms, RAM, 'Description', spec['payment_terms'])
    if spec.get('due_date'):
        date(terms, 'DueDateDateTime', spec['due_date'])
    tot = el(st, RAM, 'SpecifiedTradeSettlementHeaderMonetarySummation')
    el(tot, RAM, 'LineTotalAmount', r2(money['line_total']))
    if money['allowances']:
        el(tot, RAM, 'AllowanceTotalAmount', r2(money['allowance_total']))
    el(tot, RAM, 'TaxBasisTotalAmount', r2(net_total))
    el(tot, RAM, 'TaxTotalAmount', r2(tax_total), currencyID=cur)
    if tax_cur and tax_cur != cur:
        if not spec.get('exchange_rate'):
            raise SystemExit('tax_currency %s needs exchange_rate, the rate the order uses' % tax_cur)
        el(tot, RAM, 'TaxTotalAmount', r2(tax_total * Decimal(str(spec['exchange_rate']))), currencyID=tax_cur)
    el(tot, RAM, 'GrandTotalAmount', r2(gross))
    if money['paid']:
        el(tot, RAM, 'TotalPrepaidAmount', r2(money['paid']))
    el(tot, RAM, 'DuePayableAmount', r2(money['due']))
    # The invoice a credit note amends (BG-3): its number (BT-25) and issue date (BT-26).
    if spec.get('preceding_invoice'):
        ref = el(st, RAM, 'InvoiceReferencedDocument')
        el(ref, RAM, 'IssuerAssignedID', spec['preceding_invoice'])
        if spec.get('preceding_invoice_date'):
            when = el(ref, RAM, 'FormattedIssueDateTime')
            el(when, QDT, 'DateTimeString', spec['preceding_invoice_date'].replace('-', ''), format='102')
    summary = dict(type_code=type_code(spec), lines=len(lines), total_excluding_vat=str(r2(net_total)), total_vat=str(r2(tax_total)), total_including_vat=str(r2(gross)),
                   **money_summary(money),
                   vat=[dict(category=c, rate=str(r), taxable=str(r2(g['base'])), vat=str(tax[(c, r)])) for (c, r), g in groups.items()])
    if warnings:
        summary['warnings'] = warnings
    return root, summary


def only_lines(money, syntax, paid_too=False):
    """A national file that carries a discount on a line but no allowance on the whole document stops here and
    says what to do; nothing is dropped silently."""
    if money['allowances']:
        raise SystemExit('%s carries a discount on each line, not an allowance on the whole document (EN 16931-1 BG-20, '
                         'which the CII and UBL files and the page carry): put the discount on the lines '
                         '(discount_percent or discount_amount) and build again' % syntax)
    if paid_too and money['paid']:
        raise SystemExit('%s has no element for an amount paid in advance (EN 16931-1 BT-113): the page states it; '
                         'leave paid_amount out of the file\'s data and say so in your reply' % syntax)


def money_summary(money):
    """What the summary adds when the document has an allowance or an amount paid in advance."""
    out = {}
    if money['allowances']:
        out['allowances_total'] = str(r2(money['allowance_total']))
    if money['paid']:
        out['paid'] = str(r2(money['paid']))
        out['amount_due'] = str(r2(money['due']))
    return out


def xml_bytes(spec):
    """The XML as bytes and the summary: what the page builder embeds in the Factur-X PDF."""
    import io
    root, summary = build(spec)
    ET.indent(root)
    out = io.BytesIO()
    ET.ElementTree(root).write(out, encoding='UTF-8', xml_declaration=True)
    return out.getvalue(), summary


def document_xml(spec):
    """(xml bytes, summary, syntax) in the syntax the seller's country takes (countries.syntax_of): the CII
    of Factur-X and XRechnung, Peppol BIS Billing 3.0 in UBL (Norway, Denmark, Finland, the UK), Finvoice
    3.0 when a Finnish spec asks for it, ebInterface 6.1 when an Austrian one does, or (None, summary, 'none') for a page-only country (Australia,
    Canada, the United States), whose rules the countries module still holds the spec to."""
    import countries
    syntax = countries.syntax_of(spec)
    blocked = countries.xml_blocked(spec)
    if blocked:
        return None, dict(syntax='none', warnings=['%s is declared unknown, and that syntax is not valid without it: only the page is written, no XML. Say so in your reply and ask the person for it' % ', '.join(blocked)]), 'none'
    if syntax in ('ubl', 'si-ubl'):
        import ubl_create
        data, summary = ubl_create.xml_bytes(spec, nlcius=syntax == 'si-ubl')
    elif syntax == 'finvoice':
        import finvoice_create
        data, summary = finvoice_create.xml_bytes(spec)
    elif syntax == 'ebinterface':
        import ebinterface_create
        data, summary = ebinterface_create.xml_bytes(spec)
    elif syntax in countries.NATIONAL_NAMES:
        # Spain, Italy, Poland: the national file (Facturae, FatturaPA, KSeF FA(3)), each from its own script.
        import importlib
        data, summary = importlib.import_module(syntax + '_create').xml_bytes(spec)
    elif syntax == 'none':
        missing, warnings = countries.refuse(spec)
        if missing:
            raise SystemExit('the spec lacks what this document needs; ask the person for it, never guess:\n  - '
                             + '\n  - '.join(missing))
        return None, dict(syntax='none', warnings=warnings) if warnings else dict(syntax='none'), 'none'
    else:
        data, summary = xml_bytes(spec)
    return data, summary, syntax


def main(argv=None):
    ap = argparse.ArgumentParser(description='Create an EN 16931 e-invoice XML from a JSON spec.')
    ap.add_argument('spec'); ap.add_argument('output')
    ap.add_argument('--syntax', choices=('cii', 'ubl', 'si-ubl', 'finvoice', 'ebinterface', 'facturae', 'fatturapa', 'ksef'),
                    help='the XML syntax; by default the seller country\'s (CII, or Peppol UBL in the Nordics, the UK, Belgium, the Netherlands, Austria and Ireland)')
    args = ap.parse_args(argv)
    with open(args.spec, encoding='utf-8') as fh:
        spec = json.load(fh)
    # Nothing given is dropped: an unknown key or a value of the wrong shape stops the build here
    # (skills/_shared/spec_guard.py, the fields in spec.fields.json beside SKILL.md).
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.join(here, '..', '..', '_shared'))
    import spec_guard
    spec_guard.guard(spec, os.path.join(here, '..', 'spec.fields.json'), "order's data file")
    spec_guard.output_guard(args.output, __file__, 'invoice file')
    import company
    company.apply(spec, args.spec, 'e-invoice')
    import countries
    if countries.misplaced_numbers(spec):
        raise SystemExit('; '.join(countries.misplaced_numbers(spec)))
    if args.syntax:
        spec['syntax'] = args.syntax
    data, summary, syntax = document_xml(spec)
    if data is None:
        raise SystemExit('a %s seller\'s invoice is a page only (no XML is written for it: %s); build it with '
                         'page/build_page.py' % (spec['seller'].get('country'), '; '.join(summary.get('warnings') or ['no EN 16931 XML applies there'])))
    with open(args.output, 'wb') as fh:
        fh.write(data)
    print(json.dumps(dict(ok=True, output=args.output, **summary), ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
