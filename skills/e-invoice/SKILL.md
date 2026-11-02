---
name: e-invoice
description: "Any invoice or credit note (Rechnung, facture, faktura, factura) as PDF plus the XML its country takes: XRechnung, Factur-X, Peppol, FatturaPA, KSeF and more."
version: 0.6.0
license: Apache-2.0
platforms: [linux, macos, windows]
proven: "2026-10-03"
metadata:
  domain: finance
  version: "0.6.0"
workflows:
  - id: "invoice"
    arguments: "invoice"
    icon: "file-text"
    menu: "Faktura"
    menu_en: "Invoice"
    gives: "En faktura som PDF med den XML-fil kundens land tar"
    gives_en: "An invoice as PDF with the XML file the customer's country takes"
    takes: "Släpp beställningen eller dina anteckningar, eller skriv en rad: 12 timmar konsult för 85 euro i timmen till Exempel AB, Storgatan 12, 211 34 Malmö"
    takes_en: "Drop the order or your notes, or write one line: 12 hours of consulting at 85 euros an hour for Example Ltd, Storgatan 12, 211 34 Malmö"
  - id: "credit-note"
    arguments: "credit note"
    icon: "file-text"
    menu: "Kreditfaktura"
    menu_en: "Credit note"
    gives: "En kreditfaktura mot en faktura, som PDF med sin XML"
    gives_en: "A credit note against an invoice, as PDF with its XML"
    takes: "Släpp fakturan och skriv vad som krediteras"
    takes_en: "Drop the invoice and say what to credit"
---

# E-invoice Skill

Create an electronic invoice a customer's accounting system can read: the
European standard EN 16931, in the Cross Industry Invoice XML used by
Factur-X and ZUGFeRD. One script turns a short JSON spec into the XML, does
the arithmetic the standard requires and states every total, so the file
passes an EN 16931 validator without hand-written XML. The page builder prints
the readable invoice and puts the same XML inside it: one Factur-X / ZUGFeRD 2
PDF/A-3, the hybrid file France's reform and German buyers both take.

The library cites EN 16931-1:2017 with A1:2019. A revision, EN 16931-1:2026, was approved by
CEN's formal vote in March 2026 (https://ec.europa.eu/newsroom/digital/items/930407/en); the 2017
edition stays valid while it is brought in. The library moves to the 2026 edition only once Peppol
BIS Billing validates against it.

## When to Use

- A Norwegian, Danish, Finnish or British company invoices: a faktura, kreditnota, lasku, hyvityslasku,
  VAT invoice or credit note, as a page in its language and Peppol BIS Billing 3.0 XML (EHF in Norway).
- A Belgian factuur, facture or creditnota: Peppol between companies, mandatory since 1 January 2026.
- A Dutch factuur or creditnota (Peppol or SI-UBL 2.0; between companies an e-invoice is a choice there, not
  a duty: never tell the person it is required), an Austrian Rechnung or Rechnungskorrektur (Peppol or
  ebInterface), an Irish VAT invoice or credit note.
- A Spanish factura or factura rectificativa with its Facturae 3.2.2 file, an Italian fattura or nota di
  credito with its FatturaPA file, a Polish faktura or faktura korygująca with its KSeF FA(3) file. The pack
  writes these files and does not sign or send them: read "Spain, Italy, Poland" below before you answer.
- An Australian tax invoice or adjustment note, a Canadian invoice with GST/HST (and QST, in French for
  Quebec), a US invoice with sales tax.

- Someone asks for an e-invoice, an electronic invoice, EN 16931, Factur-X,
  ZUGFeRD, XRechnung or a "structured" invoice.
- A French company invoices: a facture, a facture d'avoir. From 1 September
  2026 every company in France must be able to receive e-invoices, and large
  and mid-size companies must issue them; small companies and
  micro-entreprises issue them from 1 September 2027 (impots.gouv.fr, "À
  partir de quand suis-je concerné", updated 16/01/2026).
- A German company invoices another business in Germany. The invoice must be an
  e-invoice, a structured file to EN 16931 (UStG § 14 Abs. 1 Satz 3 and 6, Abs. 2
  Satz 2 Nr. 1), and the buyer's consent is not needed to send one. Paper or another
  format is still allowed for a supply up to 31 December 2026, and for a supply in
  2027 only when the issuer's total turnover the year before was at most 800,000
  euros (an EDI invoice also stays allowed in 2027 with the buyer's consent); the transition ends on
  31 December 2027 (UStG § 27 Abs. 38, gesetze-im-internet.de, read 2026-11-02). This
  pack's CII file at the EN 16931 level is that format. Give no other date for it.
- A customer or a public body only accepts invoices as XML.
- A credit note (Gutschrift, kreditfaktura) against an invoice already sent,
  as XML and a page; XRechnung when a German public buyer asks for it.
- Not for a Word or Excel invoice. Use the docx or xlsx skill for that; this
  skill's PDF is the invoice and its XML in one file.

## How to Run

```bash
python3 <skill folder>/scripts/einvoice_create.py spec.json invoice.xml
```

Start from `templates/invoice-spec.json` (`templates/facture-spec.json` for a
French seller). The script prints the totals as JSON, and any warning about a
default it took; read them back to the person in plain words.

## The spec

- `number`, `issue_date`, `due_date`, `delivery_date` (YYYY-MM-DD), `currency`.
- `seller` and `buyer`: `name`, `street`, `postcode`, `city`, `country` (two
  letters), `vat_id`.
- `payment`: `means_code` (58 is a SEPA credit transfer, 30 a credit
  transfer) and `iban`. A Swedish seller paid to a Bankgiro or PlusGiro
  number gives `bankgiro` or `plusgiro` (means 30 unless set); the build
  checks its check digit and stops on a wrong one, so ask, never guess.
- `order_reference`: the buyer's order or PO number (BT-13), on the page and
  in the file; `buyer_reference` is their reference person or code (BT-10).
- `lines`: `name`, `quantity`, `unit` (C62 means "one"; HUR hour, DAY day,
  KGM kilogram), `unit_price`, `vat_rate`, `vat_category`.
- A discount on a line: `discount_percent` or `discount_amount` (both only when they agree), with
  `discount_reason` in the invoice's language ("Volymrabatt"). The page prints it under the line.
- A discount on the whole invoice: `allowances`, each `amount` or `percent`, a `reason`, and the `vat_rate`
  it comes off when the lines have more than one rate.
- An amount already paid: `paid_amount`, with `paid_date` and `paid_note` (one line for the page). The
  page then prints the total, the amount paid and what is left to pay.

Every one of these is a field because a note is not enough: a discount or a prepayment written only
in `note` leaves the totals wrong. The builder works the money out once for the page and the XML
(`_shared/doc_amounts.py`: EN 16931-1 BG-27, BG-20, BT-113, BT-115) and stops when a discount does
not close or more is paid than the total. The Polish KSeF file has no place for an amount paid or an
allowance on the whole invoice, FatturaPA and ebInterface none for the allowance: the builder says so
and stops; put the discount on the lines there. Facturae needs `paid_date` with `paid_amount`.
Starters: `templates/se-faktura-rabatt-forskott-spec.json`, `templates/no-faktura-rabatt-forskudd-spec.json`.

## Nothing given is left off

Both builders (`page/build_page.py` and `scripts/einvoice_create.py`) stop before anything is built
when the order holds a key they have no field for or a value of another shape (an amount as text, a
VAT rate written `0.2` where 20 percent is meant), and name the key. `spec.fields.json` beside this
file lists every key. A fact with no field of its own goes in `note` (one line, printed under the
totals and carried in the XML); a particular of the seller that has no field in `seller.further`,
one line each, printed in the footer with the register details. Write the invoice number exactly as
the person's files give it. Never leave a fact out to make the error go away: put it where the
message says, or say in your reply what the page does not carry.

The check reads the page as printed: each line's amount, the total without tax, the tax and the
amount due add up (EINV-SUMS), and every VAT rate is one the seller's country has, or the buyer's
for a sale taxed there (EINV-RATE, read from `_checks/tax_rates.json`, which names each country's
source and the day it was read). Write a rate as a percentage: `20`, never `0.2`. Take the rate from
the person's notes; never pick one.

Run the check with `--in` and the working folder. It then reads the person's own files there and
asks, once and never as a fail (NOTES-FLOOR): which e-mail addresses, numbers, dates and amounts the
notes hold and the page does not, which of them the page carries changed. Answer the question once:
put each on the page as the notes have it, or say in your reply why it does not belong there. Never
change one to shorten the list.

Work in the working folder, the folder the person is working in: write the data file there, run the
script from there by its full path (`<skill folder>` is the folder this file is in) and give the
output a path there. The builder refuses an output path inside the library's own folder, where the
person never looks; hand back the path in the working folder.

Look for `company.json` in the working folder first: it holds the company's own particulars, written
once (name, address, VAT and register numbers, registered office, share capital, bank account). The
builder fills from it what the data file leaves out of the sender, stops when the two disagree, and
the check fails a page whose sender disagrees with it (COMPANY-FILE). When the folder has none and
the person gives their company's particulars, write it once: `python3 <skill folder>/../_shared/company.py
make company.json name="..." country=.. street="..." postcode=.. city=.. vat_id=..
register_number=..`; it says which particulars that country's company law still wants. One the files
do not give is declared with `unknown=<key>`, never made up.

On an invoice of a German, Austrian, Polish or Finnish company, whose statutes name business letters
and order forms and not invoices, the same gap is a question and never a fail (LETTER-COMPANY prints
a WARN that says whose reading it is): put the register details on the invoice from the person's
files, or say in your reply that the files do not give them.

## Rules the standard sets

- Use only details the person gave. Never invent a VAT number, an address or
  a bank account; ask for a missing one.
- A number is never built from another one. A VAT number is not the
  organisation number with a prefix and "01" unless the person's files write
  it so: when they give only the organisation number, print that, list
  `vat_id` in that party's `unknown` and say so. The check asks about every
  tax or register number on the page that the notes and `company.json` do
  not hold (NOTES-FLOOR).
- A Swedish seller: "Godkänd för F-skatt" goes in the seller's `further` only
  when the person's files say it. When they do not, list `f_tax` in the
  seller's `unknown` and say in your reply that the invoice does not state
  it; the check asks once (a WARN, never a fail) and never wants it stated
  unasked.
- The seller's register particulars (register and number, seat, share capital)
  come from the person's files too. One their files do not give is listed in
  the seller's `unknown`, never made up: see "The company's own particulars".
- Each line net is quantity x unit price less its discount, rounded to two
  decimals. VAT is calculated once per category and rate on the sum of that
  group's line nets. The script does this; do not recompute totals by hand.
- `vat_category` is `S` for the standard rates, `Z` zero rated, `E` exempt,
  `AE` reverse charge, `K` a sale to a business in another EU country, `G`
  export. `AE`, `E`, `K` and `G` take rate 0 and need `exemption_reason`.
- An export's lines (a commercial invoice) carry `hs_code`, the customs tariff number, and `origin`,
  the ISO two-letter code of the country the goods come from; both go into the XML and stand
  under the line on the page.
- Reverse charge (`AE`) needs both VAT numbers: the seller's and the buyer's.
- The due date is the issue date plus the payment term. Work it out and put
  it in `due_date`.

## A French seller

A seller whose country is FR gets a French invoice: a page in French and an
XML that carries what the French reform reads. The build stops and names what
only the person can give. Start from `templates/facture-spec.json`, or
`templates/facture-avoir-spec.json` for a facture d'avoir.

- `seller`: `siren` (nine digits) and `siret`, `legal_form` (SAS, SARL, EI ...),
  `share_capital` and `rcs` ("RCS Lyon") for a company, `vat_id`.
- `buyer`: `siren` for a French buyer, on every invoice from 1 September 2026,
  and `vat_id`.
- `operation`: `goods`, `services` or `both`, the nature of what is invoiced.
- `delivery_address` when goods go somewhere other than the buyer's address.
- `vat_on_debits`: true when the seller opted to pay VAT on debits.
- `due_date`, `late_penalty_rate` (as the seller's terms say it) and
  `early_payment_discount` (`none` when there is none).
- `electronic_address` for each party, where it receives e-invoices. Without
  one, a French company is addressed at its SIREN in the French directory, and
  the build warns.

The page says Facture or Facture d'avoir, prints amounts as 2 970,00 € and dates
as 15/09/2026 (CLDR fr), and carries the mentions the law lists: the company's
legal form, capital, RCS and SIREN, the buyer's SIREN, the nature of the
operation, the option for VAT on debits, Autoliquidation for a reverse charge,
the late-payment penalties, the 40 € recovery indemnity and the discount or
its absence. The XML carries the same as the French rules code them: the
billing framework B1, S1 or M1 (BT-23), the SIRENs (scheme 0002), the notes
PMD, PMT and AAB, VAT on debits (BT-8 = 5).

Never choose a VAT rate, an exemption or a reverse charge for the person; take
them from their files. Without a penalty rate the invoice states the statutory
one (ECB rate plus 10 points), and without a discount it says "Escompte pour
paiement anticipé : néant"; say so in your reply.

## Credit notes

A credit note amends an invoice, and a document that amends an invoice and
refers to it specifically and unambiguously is treated as an invoice (VAT
Directive 2006/112/EC Art. 219), so it carries what Art. 226 lists. Start from
`templates/credit-note-spec.json`:

- `type_code` is `381`, a credit note (EN 16931 BT-3). Never a 380 invoice
  with minus amounts.
- `number` is the credit note's own number, never the invoice's.
- `preceding_invoice` and `preceding_invoice_date` name the invoice it amends
  (BT-25 and BT-26; BR-55). Take both from the person's files; when they are
  missing, ask. The script stops without the number and warns without the date.
- Quantities and prices are positive: the type code carries the sign.
- The lines are what is credited. VAT is broken down once per category and
  rate exactly as on an invoice; the script does it.
- The VAT treatment follows the invoice being amended: its rates, and any
  exemption or reverse charge it stated. Take them from that invoice; never
  choose one for the person.

The page is headed Credit note (Gutschrift, Kreditfaktura, Kreditnota) and
shows the original invoice's number and date beside its own.

## Which file each country gets

The seller's country decides; `"syntax"` overrides it (`cii`, `ubl`, `si-ubl`, `finvoice`, `ebinterface`, `facturae`,
`fatturapa`, `ksef`, `none`).

| Seller | XML beside the page | Page |
| --- | --- | --- |
| France, Germany, Sweden, others | EN 16931 CII inside a Factur-X / ZUGFeRD PDF/A-3 | its language |
| Norway, Denmark, Finland, UK | Peppol BIS Billing 3.0 in UBL 2.1 (`invoice.xml`, Invoice or CreditNote) | nb-NO, da-DK, fi-FI, en-GB |
| Finland with `"syntax": "finvoice"` | Finvoice 3.0 | fi-FI |
| Belgium, the Netherlands, Austria, Ireland | Peppol BIS Billing 3.0 in UBL 2.1 | nl-BE, fr-BE or de-BE by the seller's postcode region (`"language"` overrides, except that a seller in Flanders writes Dutch to a customer in Belgium), nl-NL, de-AT, en-IE |
| Netherlands with `"syntax": "si-ubl"` | SI-UBL 2.0, the NLCIUS the Dutch government takes | nl-NL |
| Austria with `"syntax": "ebinterface"` | ebInterface 6.1 | de-AT |
| Spain | Facturae 3.2.2, unsigned | es-ES |
| Italy | FatturaPA 1.2.3: FPR12, or FPA12 with `"public_buyer": true` | it-IT |
| Poland | the KSeF logical structure FA(3) | pl-PL |
| Australia, Canada, US | none: EN 16931 does not apply there | en-AU, en-CA or fr-CA (`"language": "fr"`), en-US; Letter paper in Canada and the US |

Peppol needs both parties' Peppol address (`electronic_address`, `"0192:999999999"`), else the build uses
the business number under its country's scheme and warns, and the buyer's reference (`buyer_reference`,
"Deres ref.") or order number (`order_reference`) (PEPPOL-EN16931-R003). Start from the country's
template in `templates/`: `no-faktura`, `no-kreditnota`, `dk-faktura`, `dk-kreditnota`, `fi-lasku`,
`fi-hyvityslasku`, `fi-finvoice`, `uk-vat-invoice`, `uk-credit-note`, `au-tax-invoice`,
`au-adjustment-note`, `ca-invoice`, `ca-facture`, `ca-credit-note`, `us-invoice`, `us-credit-memo`,
`be-factuur`, `be-facture`, `be-creditnota`, `nl-factuur`, `nl-creditnota`, `nl-si-ubl`, `at-rechnung`,
`at-rechnungskorrektur`, `at-ebinterface`, `ie-vat-invoice`, `ie-credit-note`, `es-factura`,
`es-factura-rectificativa`, `it-fattura`, `it-nota-di-credito`, `pl-faktura`, `pl-faktura-korygujaca`.

The page sits where the seller's country puts a letter: the address in that country's envelope window,
from the library's letter layouts (`skills/_shared/letter.py`), DIN 5008 Form B where none is set.

## What each country's invoice states

The build stops and names what only the person can give; never fill in an identifier.

- **Norway** (bokføringsforskriften §§ 5-1-1 to 5-1-5): `seller.org_number` (nine digits, modulus 11),
  `seller.vat_id` NO<org.nr.>MVA when it charges VAT, `legal_form` AS/ASA/NUF prints
  "Foretaksregisteret", `delivery_date` and the place (`delivery_address`, else the buyer's address, with
  a warning), `due_date`; the VAT also in NOK (`exchange_rate`) for another currency; payment
  `account` (11 digits) and `kid`. A reverse charge prints "Omvendt avgiftsplikt – Merverdiavgift ikke
  beregnet" and needs the buyer's `org_number`.
- **Denmark** (momsbekendtgørelsen § 58): `seller.cvr`, both parties' addresses, unit prices, rate and VAT.
  Pay by `means_code` 42 with `bank_reg` and `account` (Reg.nr. and Kontonr.), or 58 with an `iban`
  (DK-R-005, DK-R-006). OIOUBL 2.1 is not written; NemHandel takes Peppol BIS 3.
- **Finland** (arvonlisäverolaki 209 e §): `seller.business_id` (Y-tunnus 1234567-8, its check digit
  holds; the VAT identifier is FI and its digits), both addresses, `delivery_date`, `due_date`; payment
  `iban`, `bic` and the `reference` (viitenumero, 7-3-1 check digit). The page prints the bank barcode
  (version 4) and the `late_interest` and `complaint_period` the order gives.
- **UK** (VAT Notice 700/21 4.1): `seller.vat_id` GB and nine digits, each line's rate, the tax point
  (`delivery_date`) when it differs; the VAT in sterling for another currency; a company's
  `register_number`, `registered_in` and `registered_office`. Pay by `sort_code` and `account`, or IBAN.
- **Australia** (GST Act s 29-70, GST Regulations s 29-70.01): headed Tax invoice (Adjustment note for a
  credit), `seller.abn` (modulus 89), GST-free lines marked; from A$1,000 the buyer's name and its address
  or `abn`. Pay by `bsb` and `account`.
- **Canada** (SOR/91-45 s. 3): `taxes` lists each tax (`{"name": "HST (ON)", "rate": 13}`, or GST and
  QST); from $100 `seller.gst_number` (123456789 RT0001), QST needs `qst_number`; from $500 the buyer's
  name and `payment_terms`. A line with `"taxable": false` is marked exempt.
- **United States**: no federal invoice standard and no VAT. `taxes` names each jurisdiction's sales tax
  and rate; `"taxable": false` lines carry none. Never write VAT on a US invoice.

- **Belgium** (Royal Decree no. 1, art. 5 § 1 and art. 12; Code of companies and associations art. 2:20,
  which names invoices): `seller.register_number`, the enterprise number 0123.456.749 (modulus 97; the VAT
  number is BE and the same digits), `register` (RPR Antwerpen / RPM Liège with the court's division) and
  `registered_office`; a business buyer's enterprise number; the payment `reference` as a structured
  communication +++123/4567/89012+++, whose last two digits are the first ten modulo 97, 97 when that
  leaves nothing. A reverse charge prints the one mention art. 5 § 1 9°bis fixes per language, "Btw
  verlegd" or "Autoliquidation" ("Steuerschuldnerschaft des Leistungsempfängers" on a German page). A
  credit note names the invoice it corrects (art. 12 § 3). B2B invoices between Belgian businesses go as
  Peppol BIS UBL over Peppol since 1 January 2026 (art. 13ter, added in 2025; art. 5 was not renumbered);
  Peppol addresses are the enterprise number under 0208. The structured electronic invoice is the only
  legally required invoice; a PDF or paper copy may go with it but no longer counts as the invoice (FPS
  Finance, B2B FAQ questions 11 and 12). Both the supplier and the customer risk a fine (questions 7 and
  8); FPS Finance's tolerance period ended on 31 March 2026. The amounts are set by royal decree and are
  not proved here from the official text, so name none. https://einvoice.belgium.be/en/FAQ/general-questions-b2b A seller in Flanders writes Dutch to a customer
  in Belgium whatever `"language"` says (decree of 19 July 1973 art. 5 § 1); for a customer in another EU
  or EEA state the named language is a second valid version beside the Dutch invoice (§ 2/1, since 2017),
  so build both and say so.
- **Netherlands** (unproved: the article mapping below was not proved against the official text in the 2026-10-20 audit) (Wet OB 1968 art. 35a; Handelsregisterwet 2007 art. 27): `seller.vat_id` NL123456782B01,
  `seller.register_number` (KvK, eight digits) and a Dutch buyer's, a postcode for both, a payment means
  30, 48, 49, 57, 58 or 59 (NL-R-007, NL-R-008). A reverse charge prints the fixed mention "Btw verlegd"
  (art. 35a lid 1 m) with the buyer's btw-id; a credit note names its invoice (art. 34f).
- **Austria** (UStG 1994 § 11): `seller.vat_id` ATU and eight digits (the ministry's check digit),
  `delivery_date` or `delivery_period` (`{"from", "to"}`), the buyer's UID over 10 000 euros (Abs. 1 Z 3
  lit. b). A reverse charge names the buyer's UID and notes the Steuerschuldnerschaft des
  Leistungsempfängers; Abs. 1a fixes no wording, so any clear note passes the check. A credit note is a
  Rechnungskorrektur ("Gutschrift" is self-billing, § 11 Abs. 7). `register_number` FN 123456a,
  `register` (Handelsgericht Wien) and `managing_directors` print when given. The federal portal
  (e-Rechnungsverordnung, erechnung.gv.at) takes ebInterface and Peppol UBL, not CII; a federal buyer's
  order number goes in `order_reference`.
- **Ireland** (unproved: the article mapping below was not proved against the official text in the 2026-10-20 audit) (VAT Consolidation Act 2010 s. 66, VAT Regulations 2010 reg. 20; Revenue's two pages on what
  a VAT invoice and a credit note state): `seller.vat_id` IE1234567T, both addresses, `delivery_date` (the
  date of supply), each line's rate. A reverse charge names the buyer's VAT number and says that a reverse
  charge applies; the law fixes no words (reg. 20(2)(e)), so any clear note passes the check. A credit
  note's `note` states the reason, and it names the buyer's VAT number and the invoice (reg. 20(5)).
  Ireland's own e-invoicing duty is not in force: Revenue phases it in for domestic B2B sales from
  November 2028 (large corporates) and November 2029 (businesses that also trade within the EU).

Never choose a rate, an exemption or a tax for the person; take them from their files.

## The company's own particulars

Beside the tax rules, a company's own law puts its register particulars on its invoices. The pack check's
`EINV-PARTICULARS` fails a page that leaves one out and names the article.

| Seller | The page states | In `seller` | Statute |
| --- | --- | --- | --- |
| France (SARL, SAS, SA, SCA, SE, SNC, SCS) | SIREN, "RCS" and the registry's city, the seat, the name with the legal form, the share capital (not an SNC or SCS), liquidation | `siren`, `rcs`, `share_capital`, `registered_office` when it is not the address, `in_liquidation` | Code de commerce R123-237, R123-238 |
| Belgium (BV/SRL, NV/SA, CV/SC, VOF, CommV, VZW/ASBL) | name, legal form, seat, enterprise number, "RPR" or "RPM" with the court, e-mail and website when it has them, liquidation | `register_number`, `register` ("RPR Gent"), `in_liquidation` | Code des sociétés et des associations art. 2:20 |
| The Netherlands | the KvK number; a BV or NV also its full name and the seat in its articles | `register_number`, `registered_office` | Handelsregisterwet 2007 art. 27; Burgerlijk Wetboek 2:186, 2:75 |
| Spain (S.L., S.A.) | domicile, the Registro Mercantil and the entry (tomo, folio, hoja), legal form, liquidation; the paid-up capital beside any capital | `register`, `register_number`, `share_capital` with `paid_up_capital`, `in_liquidation` | Código de Comercio art. 24 |
| Italy (S.r.l., S.p.A., S.a.p.a., S.n.c., S.a.s.) | seat, the Registro delle Imprese office and the number, the capital as paid up (S.p.A., S.a.p.a., S.r.l.), a sole shareholder, liquidation, the directing company | `register`, `register_number`, `share_capital`, `sole_shareholder`, `in_liquidation`, `directed_by` | Codice civile art. 2250, art. 2497-bis |
| Sweden (AB) | name, the place of the board's seat (säte), organisationsnummer, liquidation | `register_number`, `registered_office`, `in_liquidation` | aktiebolagslagen 28 kap. 5 § |
| Norway (AS, ASA, NUF) | "Foretaksregisteret", the head office's address, winding up | `legal_form`, `registered_office` when it is not the address, `in_liquidation` | bokføringsforskriften § 5-1-2; foretaksregisterloven § 7-2 |
| Denmark (A/S, ApS, P/S) | name, the address it can be reached at, CVR-nummer | `cvr` | selskabsloven § 2, stk. 4 |
| Australia (Pty Ltd, Ltd) | name, with "ACN" and the number (or an ABN whose last nine digits are the ACN) | `acn` | Corporations Act 2001 s 153, s 88A |
| The UK, Ireland, Canada | the registered name | `name` | SI 2015/17 reg. 24; Companies Act 2014 s. 49; Canada Business Corporations Act s. 10(5) |

Germany, Austria, Poland and Finland ask for these on business letters and order forms, not on invoices
(GmbHG § 35a, AktG § 80, HGB § 37a; UGB § 14; Kodeks spółek handlowych art. 206 and 374; yritys- ja
yhteisötietolaki 15 §), as the UK and Ireland do for the registered number and office (reg. 25; s. 151),
and the US has no federal rule. There the page prints what the order gives and nothing fails for what
it does not.

- Read the person's files for these and put each in the seller. They are the seller's own, never the
  customer's.
- A required particular their files do not give is **never made up** and never silently left out. List it
  in the seller's `unknown`:

      "seller": {"name": "Esempio Stampa S.r.l.", "unknown": ["register", "register_number", "share_capital"]}

  The page prints nothing in its place, the check passes with a `WARN` line, and your reply says the
  invoice is not complete without it and asks the person for it.
- `unknown` is not a way round a fact the person gave. The check reads their own files (the folder named
  with `--in`, else the folder the page is in) and fails when they give a particular the page dropped,
  whatever the order declares.
- A number the tax rules ask for too (the SIREN, the Belgian enterprise number, the CVR, the Norwegian
  org.nr.) cannot be declared unknown: ask for it.
- A particular declared unknown no longer stops the build: the file is made, the warning names what is
  missing and your reply asks for it. This holds for the buyer too (an Austrian invoice over 10 000 € wants
  the buyer's UID: `"buyer": {"unknown": ["vat_id"]}`). Sums are never declarable: totals that do not close
  stop the build whatever `unknown` lists.
- Where the XML cannot be valid without the particular (a Dutch seller's Peppol file without the KvK number),
  the builder writes the page alone and its warning says "only the page is written": say so in your reply.

## Spain, Italy, Poland

Each of these states has its own e-invoice file, and a state system that takes it. The pack writes the file
and the page. It does not sign, send or register anything, and your reply says so every time.

- **Spain** (Real Decreto 1619/2012 art. 6 and 15): `seller.vat_id`, the NIF (`ESB12345674` or `B12345674`),
  and the recipient's for a supply in Spain, a reverse charge or an exempt intra-EU supply; `province` for
  both Spanish addresses; `series` where the seller uses one. A reverse charge prints «Inversión del sujeto
  pasivo» (art. 6.1 m); a line without tax needs `exemption_reason` (art. 6.1 j). A **factura
  rectificativa** has a `series` of its own (art. 6.1 a 2.º), names the invoice (`preceding_invoice`,
  `preceding_series`, `preceding_invoice_date`) and says what is rectified as Facturae codes it
  (`"correction": {"reason_code": "16", "period": {"from", "to"}}`: 01 number, 03 date, 10 the items, 11 the
  rate, 12 the tax, 16 the taxable base, 82 returned packaging, 83 discounts and rebates). Its page and file
  state the rectification itself, with minus amounts (art. 15.5); give the lines as positive quantities.
  - **The Facturae is not signed.** FACe and the other public entry points take a Facturae only with an
    XAdES signature made with the seller's certificate (Ley 25/2013 art. 5). The pack makes none: the
    seller signs the file with its own certificate and tools before sending.
  - **VERI\*FACTU.** Invoicing software must meet Real Decreto 1007/2023 before 1 January 2027 for
    companies that pay corporate tax and before 1 July 2027 for other businesses and professionals (the
    dates as moved by Real Decreto-ley 15/2025). The QR code and the words «VERI\*FACTU» belong on invoices
    issued by such a system (Real Decreto 1619/2012 art. 6.5); this pack is not one: it keeps no billing
    records, chains none and sends nothing to the tax agency, so its page carries neither. Say so when
    the seller asks whether the invoice is "VeriFactu".
- **Italy** (unproved: the article mapping below was not proved against the official text in the 2026-10-20 audit) (DPR 633/1972 art. 21; from 1 January 2027 the Testo unico IVA, D.Lgs. 10/2026, art. 72):
  `seller.vat_id`, the partita IVA (`IT01234567897`), and `seller.tax_regime` (RF01 the ordinary regime,
  RF19 the flat-rate one: ask, never choose); the customer's `vat_id` or, for a person who is not a
  business, `tax_code` (the codice fiscale); `province` (MI) and a five-digit `postcode`;
  `buyer.recipient_code` (the seven-character Codice Destinatario) or `buyer.pec`, else the file carries
  0000000 and the build warns; a public body has `"public_buyer": true` and its six-character office code.
  A line without IVA names its `nature` (N2.1, N3.1 to N3.6, N4, N6.1 to N6.9: ask) and its
  `exemption_reason`, the annotation art. 21 comma 6 puts in place of the tax; a reverse charge prints
  «Inversione contabile» (art. 17). `"split_payment": true` for a public buyer who pays the IVA itself
  (art. 17-ter), `"stamp_duty": true` or its amount when the imposta di bollo is due: the pack never
  decides that. A **nota di credito** is TD04 with positive amounts and names its invoice.
  - **The FatturaPA is not sent.** Invoices between parties in Italy are issued only through the Sistema
    di Interscambio (D.Lgs. 127/2015 art. 1 comma 3). The pack does not reach it; the seller sends the file
    through its own channel, and until then there is no invoice. The page is a courtesy copy.
- **Poland** (ustawa o VAT art. 106e and 106j): `seller.vat_id`, the NIP (`PL1234563218` or ten digits),
  and the buyer's; rates of 23, 22, 8, 7, 5, 4 or 3 percent, any other line by its category;
  `"split_payment": true` or `false` on an invoice over 15 000 zł (annex 15 decides; the pack cannot),
  `"cash_method": true` for „metoda kasowa”; an exempt line needs `exemption_reason` and
  `exemption_basis` (`act`, `directive` or `other`); an invoice in another currency needs
  `exchange_rate`, since the tax is stated in złoty (art. 106e ust. 11). A **faktura korygująca** names
  the invoice, its date and its KSeF number (`preceding_ksef_number`, or `"preceding_outside_ksef": true`);
  its page and file state the correction itself, with minus amounts. Give the lines as positive quantities.
  - **The FA(3) file is not sent.** Taxpayers issue structured invoices in the Krajowy System e-Faktur
    (art. 106ga): since 1 February 2026 the largest sellers, since 1 April 2026 the others, and until
    31 December 2026 a seller whose invoices in a month total no more than 10 000 zł may still issue outside
    it (art. 145l, 145m). The pack does not reach KSeF, so the file has no KSeF number and the page carries
    neither that number nor the code a structured invoice used outside KSeF must carry (art. 106gb ust. 5).
    The seller sends the file through its KSeF channel; the page is a picture of the same data.

A check character that does not hold (NIF, partita IVA, NIP) only warns, because none of the three formulas
was read from an official text: read the number again from the person's files and say what you found.

## XRechnung buyers

When the buyer asks for XRechnung (a German public buyer, which gives a
Leitweg-ID), add `"xrechnung": true` and:

- `buyer_reference`: the buyer reference, the Leitweg-ID (BT-10, BR-DE-15);
- `payment`: the payment instructions (BG-16, BR-DE-1), with the IBAN for a
  credit transfer (BR-DE-23-a);
- `seller.contact`: `name`, `phone` and `email` of the seller's contact (BG-6,
  BR-DE-2, BR-DE-5, BR-DE-6, BR-DE-7);
- the seller's and buyer's city and post code (BR-DE-3, -4, -8, -9);
- `electronic_address` for both parties (BT-34, BT-49). Without one, the buyer
  is addressed at its Leitweg-ID (scheme 0204) and the seller at its contact's
  email, and the build warns.

The script stops and names each missing field by its rule. These German rules
come from the KoSIT XRechnung schematron (Apache-2.0), restated in our own
code. Start from `templates/xrechnung-credit-note-spec.json`. A buyer that has
not asked for XRechnung gets plain EN 16931.

| Rule | What the pack check reads | Source |
| --- | --- | --- |
| `INV-CREDIT-TYPE` | type 381, its own number, a page that calls itself a credit note | EN 16931 BT-1, BT-3 |
| `INV-CREDIT-REF` | the amended invoice's number and date, in the XML and on the page | EN 16931 BT-25, BT-26, BR-55; Art. 219 |
| `INV-CREDIT-SIGN` | no negative amount or quantity | EN 16931 BT-3 (381) |
| `INV-CREDIT-VAT` | one VAT group per category and rate, each the sum of its lines, totals that add up | EN 16931 BR-CO-10, -13 to -18, BR-S-08 |
| `INV-XRECHNUNG` | the German rules above, for a buyer who asks for XRechnung | KoSIT XRechnung schematron 2.6.0 (XRechnung 3.0) |
| `EINV-FACTURX` | the PDF carries the XML as factur-x.xml (xrechnung.xml for XRechnung), with its AFRelationship and the Factur-X XMP, at the level the XML names, and it is the XML beside it | Factur-X 1.0 / ZUGFeRD 2.x, ISO 19005-3 |
| `EINV-PDFA` | veraPDF finds the PDF compliant with PDF/A-3B, where veraPDF is installed | ISO 19005-3 |
| `EINV-KOSIT` | the KoSIT validator accepts the XML: the XRechnung scenario, or EN 16931 (CII) | KoSIT validator 1.6.3, XRechnung 3.0.2 configuration |
| `EINV-FR-CTC` | for a French seller, the same validator with the French BR-FR rules accepts it | FNFE-MPE France_RFE, AFNOR XP Z12-012 |
| `EINV-PARTICULARS` | the company's own particulars by its country's statute (register and number, seat, legal form, share capital, liquidation): a missing one fails, one the order declares `unknown` warns, one the person's files give and the page drops fails | the statutes in "The company's own particulars" |
| `FR-SELLER` | SIREN, legal form, capital, RCS and VAT number | CGI annexe II art. 242 nonies A I; service-public.fr F31808 |
| `FR-BUYER` | name, address, a French buyer's SIREN, its VAT number | 242 nonies A I 1° (from 1 September 2026) |
| `FR-PAYMENT` | due date, penalty rate, 40 € indemnity, discount, on the page and as notes PMD, PMT, AAB | Code de commerce L441-9, L441-10, D441-5; BR-FR-05 |
| `FR-MENTIONS` | the nature of the operation and BT-23, VAT on debits, the delivery address, Autoliquidation, the exemption's reason | 242 nonies A I 7° bis, 8° bis, 11° bis, 12°, 13°; BR-FR-08 |
| `EINV-PEPPOL` | the official Peppol BIS Billing 3.0 rules (with the Norwegian, Danish and Dutch rules) accept the UBL, where installed | OpenPeppol Peppol BIS Billing 3.0.21, run untouched |
| `EINV-SI-UBL` | the official SI-UBL 2.0 rules accept a Dutch NLCIUS invoice, where installed | Nederlandse Peppol Autoriteit, SI-UBL 2.0.3.13 (MIT) |
| `EINV-EBINTERFACE` | the ebInterface 6.1 schema accepts an Austrian ebInterface invoice, where installed | AUSTRIAPRO ebInterface 6.1, run untouched |
| `BE-INVOICE` | enterprise number (modulus 97) and VAT number, both parties, the buyer's VAT number, prices, VAT per rate, the fixed reverse-charge mention, a credit note's invoice, the structured communication (modulo 97, 97 for 0); the enterprise number under 0208 in the UBL | Royal Decree no. 1 art. 5 § 1 (9°bis), art. 12 § 3; CSA art. 2:20 |
| `NL-INVOICE` | btw-id and KvK number, both parties, prices, VAT per rate, "btw verlegd" with the buyer's btw-id, a credit note's invoice; the KvK under 0106 in the UBL | Wet OB 1968 art. 34f, 35a; Handelsregisterwet 2007 art. 27; NL-R-003 |
| `AT-INVOICE` | UID-Nummer (the ministry's check digit), both parties, the date or period of supply, VAT per rate, the buyer's UID over 10 000 euros (lit. b), a reverse-charge note in any clear words, the Firmenbuchnummer when given | UStG 1994 § 11 Abs. 1 Z 3, Abs. 1a |
| `IE-VAT-INVOICE` | VAT number, both parties, the date of supply, each rate, VAT and total, the buyer's VAT number and any clear note that a reverse charge applies, a credit note's reason, buyer's VAT number and invoice | VAT Consolidation Act 2010 s. 66, 67; VAT Regulations 2010 reg. 20 |
| `EINV-FACTURAE` | the Facturae 3.2.2 schema accepts the Spanish file, where installed; it says the file is unsigned | Facturaev3_2_2.xml, facturae.gob.es |
| `EINV-FATTURAPA` | the FatturaPA schema 1.2.3 accepts the Italian file, where installed; it says the file is not sent | Schema_VFPR12_v1.2.3.xsd, fatturapa.gov.it |
| `EINV-KSEF` | the Ministry's logical structure FA(3) accepts the Polish file, where installed; it says the file is not sent | schemat.xsd, crd.gov.pl/wzor/2025/06/25/13775 |
| `ES-INVOICE` | NIF, both parties, the recipient's NIF, prices, rates, IVA per rate, the series, the exemption's reference, «inversión del sujeto pasivo», a rectifying invoice's own series and its invoice; class OR or OO in the Facturae | Real Decreto 1619/2012 art. 6.1, art. 15 |
| `IT-INVOICE` | partita IVA, both parties, the customer's partita IVA or codice fiscale, prices, rates, IVA per rate, the annotation in place of the tax, «inversione contabile», the split payment and stamp-duty annotations; TD01 or TD04 in the FatturaPA | DPR 633/1972 art. 21 comma 2 and 6, art. 17 (Testo unico IVA art. 72, 64 from 2027) |
| `PL-INVOICE` | NIP, both parties, the buyer's tax number, net prices, rates, tax per rate and in złoty, „odwrotne obciążenie”, „mechanizm podzielonej płatności”, „metoda kasowa”, a correcting invoice's invoice and KSeF number; VAT or KOR and the same annotations in the FA(3) | ustawa o VAT art. 106e ust. 1, art. 106j ust. 2 |
| `EINV-FINVOICE` | Finanssiala's Finvoice 3.0 schema accepts the Finvoice message, where installed | Finvoice3.0.xsd, 27.9.2023 |
| `NO-SELLER` | the org.nr. (check digit), MVA, Foretaksregisteret on the page and in the UBL | bokføringsforskriften § 5-1-2; NO-R-001, NO-R-002 |
| `NO-CONTENT` | number, date, buyer, delivery time and place, due date, VAT per rate and in NOK, the reverse-charge mark | § 5-1-1, § 5-1-5 |
| `DK-INVOICE` | CVR, both parties, unit prices, rate, VAT, the bank details; the CVR under 0184 in the UBL | momsbekendtgørelsen § 58; DK-R-002, DK-R-014 |
| `FI-INVOICE` | Y-tunnus, the VAT identifier, both parties, delivery date, VAT, the reverse-charge mark, the credited invoice | arvonlisäverolaki 209 e § |
| `FI-PAYMENT` | due date, IBAN, viitenumero check digit, a bank barcode that matches them | Finanssiala, Pankkiviivakoodi v4 |
| `UK-VAT-INVOICE` | the supplier's VAT number (check digits), both parties, tax point, unit prices, each line's rate, totals, VAT in sterling | VAT Notice 700/21 4.1 |
| `AU-TAX-INVOICE` | Tax invoice or Adjustment note, ABN (modulus 89), GST, GST-free lines marked, the buyer from A$1,000 | GST Act s 29-70, s 29-75; GST Regulations s 29-70.01 |
| `CA-GST-HST` | the total, the GST/HST number and each tax from $100, the buyer and terms from $500, exempt lines marked, the QST number | SOR/91-45 s. 3 |
| `US-SALES-TAX` | no VAT wording, each sales tax with its rate and amount, subtotal plus taxes is the total | (no federal standard) |

## Verification

- Read the printed totals against the source figures.
- Open the XML and confirm the seller, buyer and VAT numbers.
- The pack check runs the official validators when they are installed
  (`python3 scripts/fetch_validators.py` fetches the KoSIT validator, its
  XRechnung configuration, the FNFE-MPE French rules, the Peppol BIS 3.0.21 rules (compiled with SchXslt),
  the Finvoice 3.0 schema, the SI-UBL 2.0 rules, the ebInterface 6.1 schema, the Facturae 3.2.2 schema, the
  FatturaPA schema 1.2.3 and the KSeF structure FA(3) at pinned versions; veraPDF is installed apart).
  FA(3) counts up to 50 000 occurrences, which java takes about ten minutes to check, so the pack check
  loads a copy whose counts above 100 are unbounded; `FILETASK_KSEF_STRICT=1` checks the counts too. Where they are not, it prints SKIP for each and
  says so; say in your reply that the file was not run through them.

## The readable page

An invoice or credit note often has to be handed over as a readable page, not only as XML. Build it
with `page/build_page.py` (below), never by hand: the same data as the XML, printed to PDF, never a
figure the order does not carry. Each part of the page comes from a published source:

| Part | Source |
| --- | --- |
| What must be on it | VAT Directive 2006/112/EC Art. 226, and EN 16931 for the data |
| Where it sits | The seller country's letter layout, read from `skills/_shared/letter.py` wherever that module has one (Norway, Denmark, Finland, the UK, Australia, Canada, the US, and each country added there): the buyer alone in that country's envelope window, its margins, the invoice data beside the window, or at the top right above it on a US or Canadian Letter page, where a #10 window leaves no room beside it. Any other country keeps DIN 5008:2020 Form B, the library's letter sheet: the buyer in the window address field, the invoice data in the information block, one 25 mm left edge. The buyer's address is written as the letter to the same buyer writes it, the way its post office reads it (`9000 GENT`, `8011 AA  ZWOLLE`, `LEEDS` above `LS1 1AA`), with the country last when the invoice goes abroad. The invoice data never passes the text's right edge, the one the table ends on. The block is two groups, the document's data and the seller's contact, each with its labels in a column as wide as its own longest label: every label keeps to one line and a long value wraps inside its own column, an e-mail address after its @ or before a point. A page that runs long breaks clear of the footer. Company, tax and bank details are in the footer either way (`EINV-PAGE-DIN5008` measures both layouts and the right edge) |
| Numbers and dates | Unicode CLDR: 1.234,56 and 05.10.2026 in German and Danish, 1 234,56 and 2026-10-05 in Swedish, 1 234,56 € and 15/09/2026 in French, 1,234.56 and 05/10/2026 in English, 1 234,56 and 05.10.2026 in Norwegian, 1 234,56 € and 5.10.2026 in Finnish, 10/05/2026 in the US, 2026-10-05 in Canada; 1.234,56 and 5/10/2026 in Spanish, 1.234,56 and 05/10/2026 in Italian, 1 234,56 and 5.10.2026 in Polish (CLDR writes four digits ungrouped in these three; the library's pages group every thousand, as the locale table says) |
| Language | The customer's language when the order names one (`"language": "sv"`, the way Stripe sets it per customer), else the seller's country, whose rules govern the invoice (Art. 219a). German (Germany, Austria, Belgium), English (British, Irish, Australian, Canadian, American), Swedish, Danish, Norwegian, Finnish, French (France, Belgium, Canada), Dutch, Spanish, Italian and Polish have their words; any other language is written in English |
| French mentions | CGI annexe II art. 242 nonies A, Code de commerce L441-9, L441-10 and D441-5, service-public.fr F31808: see A French seller above (`FR-SELLER`, `FR-BUYER`, `FR-PAYMENT`, `FR-MENTIONS`) |
| The file | Factur-X 1.x / ZUGFeRD 2.x (FNFE-MPE and FeRD, 1.09.2 and 2.5.2 the release of 4 August 2026; the XMP namespace still reads 1p0): PDF/A-3B with the XML inside, sRGB output intent, XMP naming the profile (`EINV-FACTURX`, `EINV-PDFA`) |
| Mentions | A reverse-charge invoice says Reverse charge in the page's language (Art. 226(11a)); an exempt line prints its `exemption_reason` (Art. 226(11)) (`EINV-PAGE-MENTIONS`) |
| VAT per rate | One row per VAT rate with its taxable amount, VAT calculated once per rate on the sum of that rate's line nets (Art. 226(8)-(10), EN 16931); the same figures as the XML |
| Company details | A company's invoice is one of its letters: register, registration number, legal form and registered office, a GmbH's managing directors (Directive (EU) 2017/1132 Art. 26, GmbHG 35a). Put them in `seller` as `registered_office`, `register`, `register_number`, `managing_directors`; the page prints them in the footer and the XML carries them (BT-30, BT-33). When the files lack them, say so in your reply (`LETTER-COMPANY`) |
| Currency | An invoice in a currency other than the seller's national one (SEK for Sweden, DKK for Denmark) also states the VAT in the national currency (Art. 230). Put `tax_currency` and `exchange_rate`, the rate the order uses, in the source; if the order gives no rate, ask for it. The build stops without one |

## Figure forms

Every amount and date on the page goes through `page/format.py`, which reads the same CLDR table
the locale check reads:

```
python3 page/format.py --locale sv-SE --money 2150 --date 2026-10-01
2 150,00
2026-10-01
```

## The check is the finish line

Before you answer, run the pack check on what you produced:

    python3 <skill folder>/../_checks/packcheck.py e-invoice <your output>

Add `--in <folder>` when the person's files are in another folder than the page: the check reads them
for the seller's particulars. A `WARN` line on a clean run is something your reply must say.

It prints one FAIL line per rule with the evidence. Fix what it names and run it again, at most
three times. The turn does not end on a fail: if it still fails after three tries, say plainly
which rules fail and what you tried, and leave the file in place. A clean run prints
"pack check clean".

## The page is built, not hand written

One command builds the page from the person's source and prints it:

    python3 <skill folder>/page/build_page.py <source>.json invoice.pdf

It builds the XML from the same source first (what the XML refuses, the page is not printed for),
writes `invoice.html` beside the PDF, prints the PDF with the app's own Chromium, or with
Playwright outside the app, and makes it a Factur-X / ZUGFeRD PDF/A-3 with the XML inside; the same
XML is written beside it as `invoice.xml`, for a buyer who takes the XML alone, such as an XRechnung
portal. `--no-facturx` prints the page alone. Do not retype anything the source already carries: amounts, dates, the
unit and the IBAN come out of the source, the line nets and the totals are the source's own
quantities, prices and discounts combined by the rules it states, and the labels come from the
page's language, so a German invoice reads Rechnungsnummer, Beschreibung, Stk and
`Zahlungsziel: 30 Tage netto`, a Swedish one Fakturanummer, Beskrivning, st and
`Betalningsvillkor: 30 dagar netto`. Leave `--locale` off: the order decides the language. A label with no value in the source is not printed, and a required
field that is missing stops the build and names it.

The HTML the builder writes carries its mark. The pack check requires that HTML beside the PDF,
and a page without it fails and prints the command to run: there is no road where the page is
written by hand.

## Say what passed, not more

Tell the person which checks the file passed and against which source and version. Never call the
file certified, compliant or approved, and give no legal, tax or accounting advice.
