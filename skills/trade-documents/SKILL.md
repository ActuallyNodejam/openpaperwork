---
name: trade-documents
description: "Quote, offer, order confirmation, delivery note, pro forma or purchase order (Angebot, offert, devis, presupuesto) as Word, Excel or PDF, sums done by script."
version: 0.5.0
license: Apache-2.0
platforms: [linux, macos, windows]
metadata:
  domain: sales
  version: "0.5.0"
workflows:
  - id: "quotation"
    arguments: "quotation"
    icon: "file-text"
    menu: "Offert"
    menu_en: "Quotation"
    gives: "En offert i Word eller PDF, summorna räknade med skript"
    gives_en: "A quotation in Word or PDF, the sums done by script"
    takes: "Släpp förfrågan eller prislistan, eller skriv en rad: 40 stolar för 289 kr styck till Exempel AB, Storgatan 12, 211 34 Malmö"
    takes_en: "Drop the request or your price list, or write one line: 40 chairs at 289 kr a chair for Example Ltd, Storgatan 12, 211 34 Malmö"
  - id: "order-confirmation"
    arguments: "order confirmation"
    icon: "file-text"
    menu: "Orderbekräftelse"
    menu_en: "Order confirmation"
    gives: "En orderbekräftelse i Word eller PDF med det ni har lovat"
    gives_en: "An order confirmation in Word or PDF with what you have agreed"
    takes: "Släpp beställningen eller offerten"
    takes_en: "Drop the order or the quotation"
  - id: "delivery-note"
    arguments: "delivery note"
    icon: "file-text"
    menu: "Följesedel"
    menu_en: "Delivery note"
    gives: "En följesedel att lägga i paketet"
    gives_en: "A delivery note to put in the parcel"
    takes: "Släpp ordern och skriv vad som skickas"
    takes_en: "Drop the order and say what ships"
  - id: "proforma-invoice"
    arguments: "pro forma invoice"
    icon: "file-text"
    menu: "Proformafaktura"
    menu_en: "Pro forma invoice"
    gives: "En proformafaktura för förskott eller tull"
    gives_en: "A pro forma invoice for prepayment or customs"
    takes: "Släpp offerten eller ordern"
    takes_en: "Drop the quotation or the order"
  - id: "purchase-order"
    arguments: "purchase order"
    icon: "file-text"
    menu: "Inköpsorder"
    menu_en: "Purchase order"
    gives: "En inköpsorder till leverantören"
    gives_en: "A purchase order to your supplier"
    takes: "Släpp leverantörens offert, eller skriv en rad: 200 kartonger för 1 150 kr styck från Exempel AB, Storgatan 12, 211 34 Malmö"
    takes_en: "Drop the supplier's quote, or write one line: 200 boxes at 1,150 kr a box from Example Ltd, Storgatan 12, 211 34 Malmö"
---

# Trade documents

Use this before the spreadsheet, document or PDF skill when someone asks for a quotation (quote, offer), an order confirmation,
a delivery note (despatch note, packing slip, packing list), a pro forma invoice or a
purchase order (an order to a supplier, Bestellung, inköpsorder, pedido, ordine d'acquisto, zamówienie). For a
tax invoice use the spreadsheet or document skill, and `e-invoice` for the
electronic one and for a credit note.

These five documents have a settled layout and settled arithmetic. One script
owns both, so your attention goes to the content: who, what, how many, at
what price, on what terms, and what the customer must be told.


A commercial invoice for an export is the real invoice: make it with the `e-invoice` skill (no VAT
charged on an export: `vat_category` `G` with its `exemption_reason`, and each line's `hs_code` and
`origin`, the ISO two-letter code). Its packing list is this skill's
delivery note. Read the shipment's details from the folder's files before asking for any.

## How to make one

1. Read everything the person gave you: the customer's message, the price
   list, the stock or packing list, and the company's own notes on terms.
2. Write a small spec file (JSON) with the facts. Start from the example for
   that document in `templates/` beside this file.
3. Run the script. It lays out the file, does the sums and saves it.

```sh
python3 <skill folder>/scripts/trade_create.py spec.json quotation.docx
python3 <skill folder>/scripts/trade_create.py spec.json order-confirmation.xlsx
python3 <skill folder>/scripts/trade_create.py spec.json delivery-note.pdf
```

The ending of the output name picks Word, Excel or PDF. The script prints the
totals and any warnings; read them. An Excel file has live formulas with
their results saved. Use the format the person asked for; when they did not
say, a quotation or pro forma is a PDF or Word file, an order confirmation
either, and a delivery note a PDF.

4. Open the result and read it once as the customer would.
5. Run the pack check and fix what it names:
   `python3 <skill folder>/../_checks/packcheck.py trade-documents <your output>`

## Nothing given is left off

`trade_create.py` stops before anything is laid out when the spec holds a key it has no field for, a
value of another shape (`notes` as one string, an amount as text, a VAT rate written `0.2` where 20
percent is meant) or a key this kind of document has no place for (a bank account on a purchase
order, the recipient's e-mail address), and names the key. `spec.fields.json` beside this file lists
every key. A fact with no field of its own goes in `notes` (lines under the totals) or as a line of
`references` (a label and a value in the information block: a contact person, who raised the order);
a particular of the company itself in `seller.further` or `buyer.further`, printed in the sender's
footer. Never leave a fact out to make the error go away: put it where the message says, or say in
your reply what the page does not carry. A Swedish seller whose files say it is approved for F-skatt
has "Godkänd för F-skatt" in `seller.further` on a quotation, order confirmation and pro forma; the
check fails one that leaves it off (LETTER-COMPANY), and never wants it stated unasked. A number
or bank details the files do not give are listed in the top-level `"unknown": ["number", "bank"]`,
printed as nothing and named in your reply; the builder stops on a marker such as "TBC" in their place.

The check fails a document whose recipient's address, or the sender's own in the footer, lacks the
street, the town or the postcode, and a line that does not say what it is (TRADE-EMPTY, a house
rule).

The check recomputes the money: every line amount is quantity times price less the discount, the
totals add up and VAT is worked out once per rate (TRADE-SUMS; a purchase order's TRADE-PO-LINES and
TRADE-PO-TOTAL), and every VAT rate is one the seller's country has (TRADE-RATE, read from
`_checks/tax_rates.json`, which names each country's source and the day it was read). Write a rate
as a percentage: `20`, never `0.2`. Take the rate from the person's notes; never pick one.

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

When the sender is a company, its own company law asks its letters and order forms to state its
particulars (the register and its number, the registered office, and by country the court, the
directors, the share capital), and the check fails a page without one of them (LETTER-COMPANY,
citing the article). Take each from the person's files or from `company.json`. One the files do not
give is declared in the sender with `"unknown": ["register_number"]`: it is printed as nothing, the
check then only warns, and your reply says the page is not complete without it. Never make one up.

## Where the page comes from

| Part | Source |
| --- | --- |
| Where things sit | The letter of the country the document is sent from, the sheet that country's invoice and letter sit on (`skills/_shared/letter.py`): the address in that country's envelope window and its margins. The window is on the left in Norway, Denmark, Finland, the Netherlands, Austria, the United Kingdom, Ireland and Australia, on the right in Belgium, Spain, Italy and Poland, and a No. 10 window on US Letter in the United States and Canada (`TRADE-WINDOW` measures a PDF and a Word file). Germany, Sweden, France and any other country keep DIN 5008:2020 Form B: the window address field with its return line and one 25 mm left edge (`LETTER-DIN5008`). The sender is the seller, or the buyer on a purchase order. The document's data stands in the information block: right of a window on the left, left of a window on the right, above a No. 10 window. It ends on the text's right edge, where the table ends, or before the window, with each label on one line and a long value wrapping in its own column, as on an invoice page (`TRADE-BLOCK` measures a PDF). Word follows the PDF, and an Excel file keeps the address on the same side. Leave `layout` out; `"layout": "din5008"` asks for Form B and a layout's name (`uk`, `nl`, `es`) for that one |
| The address | Written as the recipient's post office reads it, the way the letter and the invoice to the same recipient write it (`skills/_shared/letter.py`): LEEDS over LS1 1AA, 9000 GENT, 3818 LE  AMERSFOORT, 28001 MADRID with the province below, 10121 TORINO TO, 30-001 KRAKÓW; no country line at home, the country last and in capitals abroad. Give `province` (Spain: the name; Italy: the two letters) when the files have it. The sender's own address in the footer is the company's imprint, not an address for the post: ordinary case, the same lines its letter and its invoice print (28001 Madrid, 40121 Bologna (BO), Leeds LS1 4BR), the country last when the document goes abroad; the return line of a Form B page, the delivery line and an Excel file's footer row are one line each with the same town line |
| Paper | A4 (ISO 216); US Letter in the United States and Canada, for PDF, Word and Excel alike (`LOCALE-PAPER`). The document's language picks the paper, and a layout is used on its own paper: a US seller writing Spanish prints on A4 and keeps the Form B positions |
| Numbers and dates | Unicode CLDR for the document's locale: 12.10.2026 in Norway, 9.10.2026 in Finland (no leading zero), 10/12/2026 in the US, 2026-10-12 in Canada, 12/10/2026 in Australia, 12-10-2026 in the Netherlands, 12/10/2026 in Belgium, Ireland, Spain and Italy, 12.10.2026 in Austria and Poland; 1.234,56 in Spain and Italy, 1 234,56 in Poland |
| Language | `language` in the spec: the language the customer wrote to you in, as a tag when the market matters (`en-US`, `en-CA`, `fr-CA`, `en-AU`, `en-IE`, `nl-NL`, `nl-BE`, `fr-BE`, `fr-FR`, `de-AT`, `es-ES`, `it-IT`, `pl-PL`). Leave it out and the seller's country decides; in Belgium the region its postcode lies in (Dutch in Flanders, French in Wallonia and, unless the spec names Dutch, in Brussels). The words exist for British, Irish, American, Canadian and Australian English, Canadian and Belgian French and the French of France (a French seller, or French named with no Belgian or Canadian party: devis, bon de commande, bon de livraison, facture pro forma, HT and TTC), German and Austrian German, Dutch and Belgian Dutch, Swedish, Danish, Norwegian (bokmål), Finnish, Spanish, Italian and Polish; others are written in British English. Write your own `references` and `dates` labels in the same language; the common ones (Your enquiry, Valid until, Delivery time, Our quotation, Your purchase order, Confirmed delivery date and the like) are printed in the document's language whichever of these you write them in. `TRADE-LANG` fails a document with a label in another language |
| The tax | Named as the market names it: VAT, moms, MVA, ALV, btw (the Netherlands and Flanders), TVA (French-speaking Belgium), USt. (Germany and Austria, whose VAT number is the UID-Nr.), IVA (Spain, with the NIF-IVA, and Italy, with the partita IVA), VAT in Poland (with the NIP), sales tax (US), GST/HST or TPS/TVH (Canada), GST (Australia). Set `tax_name` (QST, TVQ, HST) when the tax has another name; the rate per line is the one the files give, never one you pick |
| Company details in the footer | Directive (EU) 2017/1132 Art. 26: register, registration number, legal form, registered office; a Norwegian AS or ASA its organisation number and the word Foretaksregisteret (bokføringsforskriften § 5-1-2, foretaksregisterloven 2025 § 7-2); a UK company its registered name, the part of the UK it is registered in, its number and its registered office, which an order form must give (Companies Act 2006 s.82, SI 2015/17 regs. 24 and 25: `register` "England and Wales"); a GmbH also its managing directors (GmbHG 35a); a Swedish AB its org number and seat (aktiebolagslagen 28 kap. 5 §). A Belgian company prints its seat, its enterprise number and RPR or RPM with the court of its seat (Code des sociétés et des associations art. 2:20: `register` is "RPR Gent, afdeling Gent" or "RPM Liège, division Liège"); a Dutch one its KvK number and statutory seat (Handelsregisterwet 2007 art. 27, BW 2:186); an Austrian one its Firmenbuch number and court and its seat (UGB § 14: `register_number` "FN 123456 a", `register` the court), with no managing directors asked; an Irish one its number, "Registered in Ireland" and its registered office (Companies Act 2014 s.151(2)), and on a business letter every director with a nationality other than Irish (s.151(1)). A Spanish company prints its registered office and its Registro Mercantil entry (Código de Comercio art. 24: `register` "Registro Mercantil de Madrid", `register_number` the tomo, folio and hoja), and when it names its capital the paid-up capital beside the subscribed (`share_capital`, `paid_up_capital`); an Italian one its seat, the register office with its number and, for an S.p.A., S.a.p.a. or S.r.l., the capital as paid up, and that it has a sole shareholder when it has (Codice civile art. 2250: `share_capital`, `sole_shareholder`); a French one its legal form with the share capital and RCS with the register's town and the SIREN, as its invoice prints them (Code de commerce R123-237: `legal_form`, `share_capital`, `rcs` "RCS Lyon", `siren`); a Polish sp. z o.o. or S.A. its seat and address, the registry court, the KRS number, the NIP and the share capital, an S.A. also the paid-up capital (Kodeks spółek handlowych art. 206 § 1 and art. 374 § 1, which name commercial orders: `register` the court, `register_number` the KRS number). An Australian company prints its ABN or ACN (Corporations Act 2001 s 153) as `register_number`. Put them in `seller` as `registered_office`, `register`, `register_number`, `managing_directors` when the files give them; when they do not, the script warns, naming the country's rule, and your reply says what is missing (`LETTER-COMPANY`); never make up a register number. A US or Canadian seller has no such list; give its GST/HST number in `vat_id` in Canada |
| Delivery term | Incoterms 2020 (ICC, in force since 1 January 2020 and still the current edition on 2026-10-20), written as ICC writes it: the rule, the named place, Incoterms® 2020 |
| A purchase order's fields | OASIS UBL 2.1 Order: number, issue date, buyer, seller, currency, lines with quantity and price, the quotation it answers, the requested delivery date and address, the delivery term |

## What each document must say

| Document | Besides parties, number, date and lines |
| --- | --- |
| Quotation | the customer's reference, until when it is valid, delivery term, payment terms |
| Order confirmation | the customer's order number and your quotation number, the confirmed delivery or collection date, delivery term, payment terms; anything not delivered in full, said in plain words with its date |
| Delivery note | the customer's order number and your order number, the delivery address, quantities ordered, delivered and outstanding, number of packages, gross weight, a place to sign; never a price |
| Pro forma invoice | the customer's order number, until when it is valid, payment in advance with bank details, delivery term, customs code and country of origin on every goods line, currency; it is not a tax invoice, and for an export it says no VAT is charged |
| Purchase order | the supplier's quotation number when it answers one, the requested delivery date, the delivery address, payment terms, and when the goods cross a border the Incoterms 2020 rule and named place agreed with the supplier; prices, discounts and VAT as the quotation gives them |

Templates per market: `quotation-nb`, `delivery-note-nb` (Norway, MVA), `order-confirmation-fi`,
`purchase-order-fi` (Finland, ALV), `quotation-us` (sales tax, Letter), `proforma-invoice-ca` (an
export from Canada, zero-rated, Letter), `order-confirmation-fr-ca` (New Brunswick, TPS/TVH, Letter)
and `quotation-au` (GST, ABN); `quotation-nl` (the Netherlands, btw, KvK), `order-confirmation-be-nl`
(Flanders, RPR), `delivery-note-be-fr` (Wallonia, RPM), `purchase-order-at` (Austria, USt., Firmenbuch)
and `proforma-invoice-ie` (an export from Ireland); `quotation-es` (Spain, a presupuesto, IVA, Registro
Mercantil), `order-confirmation-it` (Italy, a conferma d'ordine, registro delle imprese and capital) and
`purchase-order-pl` (Poland, a zamówienie, KRS, NIP and capital). An Italian delivery note is titled
documento di trasporto; what D.P.R. 472/1996 asks of one is not checked here. A US or Canadian bank
without an IBAN goes in `bank.account`.

Put things the table has no field for in `notes`: a part delivery and when
the rest comes, why VAT is 0, what happens next.

## Rules

1. Facts come from the person's files. Never invent a price, a discount, a
   delivery date, a freight charge, a warranty or a term. If something
   needed is missing, leave it out and say so in your reply. A number is
   never built from another one: a VAT number is not the organisation number
   with a prefix unless the files write it so.
2. Apply the company's own rules exactly: its validity period, payment terms,
   VAT rates and volume discounts. A discount applies only to the line it is
   stated for and only when its condition is met.
3. Delivery term: only when the person's files name one or say plainly what
   was agreed. When they do not, leave `delivery_terms` out and say in your
   reply that the files give none; a starter's term is an example, never a
   default, and the check asks about a rule the notes do not name
   (NOTES-FLOOR). When they do: an Incoterms 2020 rule, a named place, and
   the words Incoterms 2020, the rule read from what was agreed:
   - the customer collects at your premises and you load: FCA your town
   - you deliver to their address, they unload: DAP their town
   - you arrange and pay carriage: CPT their town; with insurance too: CIP
   - FAS, FOB, CFR and CIF are for sea transport only; never use them for a
     truck or a parcel
   When charges for freight or insurance are added, the rule must change to
   one that includes them.
4. Dates as year-month-day in the spec; the script writes them in the document's language. Work out a validity
   date from the company's rule and the issue date.
5. A revision changes every place the changed fact appears and nothing else:
   quantities, amounts, dates, the delivery term, notes that mentioned the
   old value. Rebuild the file from an edited spec rather than patching the
   old file, keep the same number and mark it "Revision 1" in `references`
   when asked.

## A purchase order is the buyer's letter

When the person orders from a supplier, they are the buyer: `buyer` is their
company, which heads the page and fills the footer, and `seller` is the
supplier, in the address field; the page is the buyer's country's letter. Put the supplier's quotation number in
`quotation`, the date the goods are wanted in `requested_delivery_date` and
the goods reception in `deliver_to` (without it the buyer's own address is
printed as the delivery address). When the supplier's country differs from
where the goods go, the order needs the Incoterms 2020 rule and place agreed
with the supplier; if the files do not say, never pick one: build the order
without `delivery_terms`, and say in your reply that it states none (the
check prints a WARN, not a fail). Start from
`templates/purchase-order.spec.json`. The pack check reads the order against
its spec: `TRADE-PO-HEAD` (named a purchase order, number, date, both parties,
currency), `TRADE-PO-LINES` (each line's quantity times price), `TRADE-PO-TOTAL`
(the total is the sum of the lines), `TRADE-PO-DELIVERY` (date and address),
`TRADE-PO-INCOTERMS` (across a border) and `TRADE-PO-QUOTE` (the quotation it
answers). Every other trade document with a `delivery_terms` is held to
`TRADE-INCOTERMS`: the rule, its named place and Incoterms 2020 on the page.

## The spec

`type` is `quotation`, `order_confirmation`, `delivery_note`,
`proforma_invoice` or `purchase_order`. `references` and `dates` are lists of label and value
that appear in the header block, in order. Each line has `code`,
`description`, `quantity`, `unit`, and for priced documents `unit_price`,
`discount_percent` or `discount_amount` (with `discount_reason`) and
`vat_rate`; a delivery note line has `delivered`; a pro
forma line has `hs_code` and `origin`. A charge such as freight is a line
without a code. A discount on the whole document is `allowances` (each
`amount` or `percent`, a `reason`, and the `vat_rate` it comes off when the
lines have several); an amount already paid is `paid_amount` with
`paid_date`, on an order confirmation or a pro forma invoice only, and the
page then prints what is left to pay. Put these in their fields, never only
in `notes`: the totals are worked out from them. `delivery_terms` is `{"rule": "DAP", "place": "Malmö,
Sweden"}` and `transport` is `road`, `sea`, `air` or `rail`. `deliver_to` is
a second address block. `packages` and `gross_weight_kg` belong to a delivery
note; `quotation` and `requested_delivery_date` to a purchase order. See
the header of `scripts/trade_create.py` for every field.

## Sources

- Incoterms® 2020, International Chamber of Commerce: https://iccwbo.org/business-solutions/incoterms-rules/incoterms-2020/
  (the rules are ICC's and sold; only how a term is written is used here)
- OASIS Universal Business Language 2.1 (OASIS Standard, 4 November 2013), the Quotation, OrderResponse,
  DespatchAdvice, Invoice and Order documents: https://docs.oasis-open.org/ubl/os-UBL-2.1/UBL-2.1.html. UBL 2.1
  is the version Peppol BIS uses; OASIS has published later versions.
- The company details: as in the business letter's sources (Directive (EU) 2017/1132 Art. 26
  https://eur-lex.europa.eu/eli/dir/2017/1132/oj and each country's statute named above).
- The page: DIN 5008:2020-03 https://www.dinmedia.de/de/norm/din-5008/318422674, ISO 216 (A4), and the
  envelope windows of the business letter.
- Numbers and dates: Unicode CLDR https://cldr.unicode.org/

## Say what passed, not more

Tell the person which checks the file passed and against which source and version. Never call the
file certified, compliant or approved, and give no legal, tax or accounting advice.
