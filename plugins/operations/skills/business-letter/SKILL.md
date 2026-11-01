---
name: business-letter
description: "Any business letter (Brief, brev, lettre, carta) as PDF or Word, laid out for the sender's country (DIN 5008 and more), the address the way the post reads it."
version: 0.4.0
license: Apache-2.0
platforms: [linux, macos, windows]
metadata:
  domain: operations
  version: "0.4.0"
workflows:
  - id: "letter"
    arguments: "letter"
    icon: "file-text"
    menu: "Brev"
    menu_en: "Letter"
    gives: "Ett affärsbrev som PDF eller Word, uppställt för avsändarens land"
    gives_en: "A business letter as PDF or Word, laid out for the sender's country"
    takes: "Skriv vad brevet ska säga och till vem, eller släpp ditt utkast, eller skriv en rad: ett tackbrev till Exempel AB, Storgatan 12, 211 34 Malmö"
    takes_en: "Say what the letter says and to whom, or drop your draft, or write one line: a thank-you letter to Example Ltd, Storgatan 12, 211 34 Malmö"
---

# Business letter

Use this for a letter that goes on paper or as a PDF attachment: to a customer, a supplier, a
landlord, a bank or an authority. A quotation, order confirmation, delivery note or pro forma has
its own skill (`trade-documents`); a memo inside the company is a plain document.

A business letter has a settled page and settled parts. One script owns the page, so your
attention goes to what the letter says and to whom. A letter is sent, so hand back the PDF unless
the person asks for Word; the Word file has the same page.

## How to make one

1. Read what the person gave you: the letter they are answering, their notes, and the company's
   own details (address, register number, contact).
2. Write a small spec file (JSON) with the facts. Start from the template for the sender's country:

| Sender in | Template | Page |
| --- | --- | --- |
| Germany, Sweden, elsewhere | `templates/letter.spec.json` | DIN 5008 Form B, A4 (for Sweden: house style, no Swedish standard read) |
| Norway | `templates/letter-no.spec.json` | A4, C5/E65 window, reference line under the address |
| Denmark | `templates/letter-dk.spec.json` | A4, C5/E65 window, references beside the address |
| Finland | `templates/letter-fi.spec.json` | A4 on SFS 2487's columns, E window, date and page number in the head |
| United States | `templates/letter-us.spec.json` | US Letter, full block, #10 window |
| United Kingdom | `templates/letter-uk.spec.json` | A4, blocked, DL window |
| Canada | `templates/letter-ca.spec.json`, `templates/lettre-ca.spec.json` (French) | US Letter, full block, #10 window |
| Australia | `templates/letter-au.spec.json` | A4, blocked, DL window |
| Belgium | `templates/brief-be.spec.json` (Dutch), `templates/lettre-be.spec.json` (French) | A4, the address on the right, reference line under it |
| Netherlands | `templates/brief-nl.spec.json` | A4, window on the left, reference line under the address |
| Austria | `templates/brief-at.spec.json` | A4, DIN lang or C6/5 window, references beside the address |
| Ireland | `templates/letter-ie.spec.json` | A4, blocked, DL window, the address 15 mm inside it |
| Spain | `templates/carta-es.spec.json` | A4, the address on the right, reference line under it |
| Italy | `templates/lettera-it.spec.json` | A4, the address on the right in capitals, reference line under it |
| Poland | `templates/pismo-pl.spec.json` | A4, the address on the right, 10 mm inside the window, reference line under it |

   The sender's `country` picks the page; `"layout": "din5008"` (or `"us"`, `"uk"`, `"no"`, `"be"`
   and so on) overrides it. Put a US, Canadian or Australian recipient's state or province in
   `state` and an Irish recipient's county in `county`; a Spanish recipient's province and the two
   letters of an Italian recipient's province go in `province`, an Italian stair, floor or flat in
   `building`. A Belgian sender writes Dutch or French:
   name the `language`, or the sender's postcode picks it (Wallonia French, Flanders and Brussels
   Dutch).
3. Build the letter, PDF first:

```bash
python3 <skill folder>/scripts/letter_create.py spec.json letter.pdf
python3 <skill folder>/scripts/letter_create.py spec.json letter.docx
```

4. Read the JSON it prints. When it says company details are missing, say so in your reply.
5. Keep the spec beside the letter and run the pack check; fix what it names:
   `python3 <skill folder>/../_checks/packcheck.py business-letter <your output>`

## Nothing given is left off

`letter_create.py` stops before anything is laid out when the spec holds a key it has no field for,
or a value of another shape (the body as one string instead of a list of paragraphs), and names the
key. `spec.fields.json` beside this file lists every key. What the letter says goes in `body`; a
particular of the sender that has no field of its own (a licence, a trade body, a second register)
goes in `sender.further`, one line each, printed in the footer under the register details. Never
leave a fact out to make the error go away: put it where the message says, or say in your reply what
the page does not carry.

The check fails a letter with no body, or with an address a postman cannot deliver to: the
addressee, the street and number or a PO box, the town and the postcode all come from the person's
files (LETTER-EMPTY, a house rule).

Run the check with `--in` and the working folder. It then reads the person's own files there and
asks, once and never as a fail (NOTES-FLOOR): which e-mail addresses, numbers, dates and amounts the
notes hold and the page does not, which of them the page carries changed, and which figures the
letter states that the notes do not. Answer the question once: put each on the page as the notes
have it, or say in your reply why it does not belong there. Never change one to shorten the list.

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

## The parts, in order

| Part | What goes in it |
| --- | --- |
| Letterhead | The sender's name, and its address and phone in small type under it |
| Address | In the envelope window: the recipient, an attention line, street, then the town line as the recipient's post office wants it; the country in capitals on the last line when it goes abroad |
| References and date | Their reference, ours, the contact person and the date: beside the address (Denmark, UK, Ireland, Australia, Austria, DIN 5008), in a line under it (Norway, the Netherlands, Belgium, Spain, Italy, Poland), above it (US, Canada), or the date in the head (Finland). On DIN 5008 the block ends on the text's right edge, as an invoice's does |
| Subject | One line in bold with no label; in French after "Objet :", in the Netherlands after "Betreft:", in Spanish after "Asunto:", in Italian after "Oggetto:", in Polish after "Dotyczy:"; in the UK, Ireland and Australia under the salutation |
| Salutation | "Dear Ms. Berg:" in the US, "Dear Ms Berg" in the UK, Ireland and Australia, "Madame," in French, "Geachte heer Jansen," in Dutch, "Sehr geehrte Frau Mag. Huber," in Austria, "Estimada señora Ferrer:" with a colon in Spanish, "Gentile dottoressa Bellini," in Italian, "Szanowna Pani," in Polish; Norwegian, Danish and Finnish letters may go without one |
| Body | Short paragraphs; the request or decision first, the reasons after |
| Closing and signatory | The closing, space to sign, the name and the role |
| Enclosures | What is attached, one per line |
| Footer | The company's address, VAT or tax number, registered office and register number |

## Language, dates and closings

`language` is the language the recipient wrote to you in; leave it out and the sender's country
decides. English takes the sender's English-speaking country (else the recipient's), French is
Canadian when either side is in Canada. The script writes the date from the spec's year-month-day:

| Variant | Date | Closing the script writes when the spec has none |
| --- | --- | --- |
| nb | 9. oktober 2026 | Med vennlig hilsen |
| da | 9. oktober 2026 | Med venlig hilsen |
| fi | 9.10.2026 | Ystävällisin terveisin |
| en-US, en-CA | October 9, 2026 | Sincerely, |
| en-GB, en-AU | 9 October 2026 | Yours sincerely, or Yours faithfully after "Dear Sir or Madam" |
| fr-CA, fr-BE | Montréal, le 9 octobre 2026 | Veuillez agréer, Madame, mes salutations distinguées. |
| nl-NL | 9 oktober 2026 | Met vriendelijke groet, |
| nl-BE | 9 oktober 2026 | Met vriendelijke groeten, with the comma only when the salutation has one |
| de-AT | 9. Oktober 2026, and Jänner for January | Mit freundlichen Grüßen, with no mark after it |
| en-IE | 9 October 2026 | Yours sincerely, or Yours faithfully after "Dear Sir or Madam" |
| es-ES | Madrid, 9 de octubre de 2026 | Atentamente, |
| it-IT | Milano, 9 ottobre 2026 | Distinti saluti |
| pl-PL | Warszawa, 9 października 2026 | Z poważaniem, with no mark after it |

German, Swedish and Danish letters from a German or Swedish sender stay on DIN 5008 with its
numeric date; their address is written the way the recipient's post office reads it, like every
other letter's (EDINBURGH, then the postcode, then UNITED KINGDOM). A Spanish, Italian or Polish
letter writes the sender's town before the date. In French the script turns "straight quotes" into « guillemets ». A letter that
runs to a second page keeps clear of the footer, on DIN 5008 as on the window layouts, with the
closing and the signature on one page; a Finnish letter numbers its pages in the head, the page
count in brackets: 1 (2).

## Where it comes from, and what is not checked

- The page: DIN 5008:2020 Form B for Germany, and as house style for Sweden (no SIS or PostNord letter
  standard was read). Its millimetre values are not proved: DIN 5008 is paid and was not bought. Belgium's NBN Z 01-002, the Dutch NEN
  1026, Austria's ÖNORM A 1080, SFS 2487, ISO 269 and DIN 680 are paid standards and were not
  read; what the letters take from them comes from free descriptions and is named below.
- The address: USPS Publication 28, Canada Post, Australia Post, Royal Mail, Posten, Posti and
  PostNord addressing guidance and the UPU's country sheets; bpost (MassPost Gids section 1,
  January 2026), PostNL (Vormgevingsvoorwaarden 2026, bijlagen 1 and 3), Österreichische Post
  (Richtig adressieren) and An Post (Speed up your post); Correos (the UPU sheet for Spain: the
  postcode and the locality in capitals, the province on its own line), Poste Italiane (Standard di
  composizione degli indirizzi, August 2023: three to six lines, the building above the street, CAP,
  locality and province, the last lines in capitals with no punctuation) and Poczta Polska (Zasady
  poprawnego adresowania i oznakowania przesyłek listowych: the postcode left of the locality, the
  locality in capitals, the country's name in Polish abroad). All cited, none copied.
- Dates: Unicode CLDR; the GOV.UK style guide (OGL v3) for 9 October 2026.
- Salutations and closings: the US Navy Correspondence Manual (SECNAV M-5216.5) for the US colon
  and comma, the Australian Government Style Manual for sincerely and faithfully, the OQLF for the
  French letter, Taaladvies.net (Taalunie) for the Dutch and the Belgian letter; all cited, none
  copied. For German the Amtliches Regelwerk der deutschen Rechtschreibung 2024, § 72 (CC BY 4.0).
  No Belgian authority's rule for the French letter and no Irish one for the English letter was
  found: they follow the French and the British letter the pack already writes. For Spanish the Real
  Academia Española (Puntuación de saludos y despedidas en cartas y correos electrónicos; the
  Diccionario panhispánico de dudas on the comma between place and date): a colon after the
  salutation, never a comma, and a comma or a full stop after a closing with no verb. rae.es refused a
  direct fetch on 2026-10-10, so these were read through a search tool's reading of its pages. For
  Polish the Poradnia Językowa PWN (Interpunkcja zwrotów adresatywnych oraz pożegnalnych, 2021): a
  comma, or an exclamation mark, after the salutation and no mark after the closing. No Italian
  authority's rule was found, so the check scripts none for Italian and says so.
- The Finnish page number: Kielitoimiston ohjepankki, Sivunumerointi, which cites SFS 2487 (the
  page count in brackets after the page number, 4 (7)). Cited, not copied.
- Company details: Directive (EU) 2017/1132 Art. 26, GmbHG 35a (AktG § 80 for an AG; HGB § 37a asks the
  same of a German sole trader or partnership registered as a Kaufmann: the firm, the legal form, the
  seat, the register court and number), aktiebolagslagen 28 kap. 5 §; for a UK company the Companies
  Act 2006 s.82 and SI 2015/17 reg. 25 (the part of the UK it is registered in, its number and its
  registered office, in `register`, `register_number` and `registered_office`); the
  Corporations Act 2001 s 153 for an Australian company's ABN or ACN; the Belgian companies code
  art. 2:20, Handelsregisterwet 2007 art. 27 and BW 2:186, Unternehmensgesetzbuch § 14 and the
  Irish Companies Act 2014 s.151. Spain: Código de Comercio art. 24 (the registered office, the entry
  in the Registro Mercantil and the legal form; a company that names its capital names the subscribed
  and the paid-up capital; `share_capital`, `paid_up_capital`). Italy: Codice civile art. 2250 (the
  seat, the register office and number, the capital as paid up for an S.p.A., S.a.p.a. or S.r.l., a
  sole shareholder, liquidation; `sole_shareholder`, `in_liquidation`) and art. 2497-bis (the company
  that directs it, `directed_by`). Poland: Kodeks spółek handlowych art. 206 (sp. z o.o.) and art. 374
  (S.A.): the seat and address, the registry court and the KRS number, the NIP, the share capital,
  an S.A.'s paid-up capital, the group of companies (`group`). Each was read in the official
  consolidated text (BOE, Normattiva, ISAP).

### The envelope window, country by country

No postal operator publishes the exact position of a window. Each publishes the zone a window or
an address must stay in, so every window here is a common maker's window placed inside that zone.
Checked on 2026-10-09; `skills/_shared/letter.py` (WINDOW_SOURCES) carries the same table.

| Sender in | What was read | What it confirms |
| --- | --- | --- |
| Germany | Deutsche Post, Automationsfähige Briefsendungen, Leitfaden, January 2026, 3.1.2 | Zone: a window at least 40 mm from the top and 15 mm from the other edges, usually 90 x 45 mm. The DIN 680 position and the DIN 5008 field are not confirmed (paid standards) |
| Sweden | nothing | Not confirmed against a PostNord document. The page is DIN 5008 Form B as house style |
| Denmark | nothing | Not confirmed against a PostNord document. The ISO 269 / DIN 680 window, as for Norway |
| Norway | Posten Bring, MV1 Plain envelopes, 2022-11-11, section 6 | Zone: the address at least 40 mm from the top and 15 mm from the sides, the lowest 20 mm kept for barcodes. No window position published |
| Finland | Posti's own envelope range (from 1.1.2019) | Partly: the window is 18 mm from the left and 40 mm from the top, so the address keeps out of 36 to 40 mm, where the SFS 2487 field begins |
| United States | USPS DMM 601.6.3 and 202.2.1 | Zone: 1/8 inch clear inside the window, the OCR read area. The #10 window itself comes from a printer's listing, not a standard |
| Canada | Canada Post, Machineable Mail Standard self-assessment tool, 2021 | Zone: the address 35 mm from the top and 10 mm from the other edges, windows inside it. The #10 window from a printer's listing |
| United Kingdom | Royal Mail, Mailmark Letters specification requirements, February 2020 | Confirmed for the 90 x 35 mm window 19 mm from the left and 18 mm from the bottom (a reseller's listing inside Royal Mail's limits). A 90 x 45 mm window 15 mm from the bottom breaks the 18 mm limit and is no longer used |
| Australia | Australia Post, Envelope zones and Correct addressing, 2023 | Zone: 15 mm kept clear along the bottom and the right edge. No window drawing, so the position is not confirmed |
| Belgium | bpost, MassPost Gids section 2, January 2026 | Zone: the address on the right, a window never in the 30 x 140 mm indexing zone at the bottom right, 15 mm from the side edges, 4 mm around the address. So the window is on the right; its rectangle is worked out from the zones, not from a maker's drawing |
| Netherlands | PostNL, Vormgevingsvoorwaarden 2026 (from 1 July 2026) | Zone: the address 40 mm from the top and 15 mm from the other sides, an index zone 20 mm high at the bottom right. No window position or side published |
| Austria | Österreichische Post, Richtig adressieren (2020, file of 2024) | Zone: a window of at least 90 x 35 mm, 5 mm quiet zone around the address. No window position published |
| Ireland | An Post, Speed up your post, 2019 | Zone: the address block 20 mm in from both sides, 20 mm clear at the bottom, text 15 mm from the window's left edge and 5 mm from the others. No window position published |
| Spain | Correos, Dimensiones y pesos de los envíos, the drawing of a normalised item (read 2026-10-09) | Zone published, exact position not published: the address block at most 140 mm from the right edge, under the 74 x 40 mm franking zone and above the 15 mm bar-code strip, as far right as possible, about 8 mm kept clear at the right edge (the drawing's own figure is partly hidden). So the window is on the right |
| Italy | Poste Italiane, Caratteristiche standard degli invii, Posta indescritta, version 3 of 3 March 2026, 1.1.3, 4.1.6 and 4.2.7 | Zone published, exact position not published: the address block inside 140 x 140 mm from the bottom right corner and 15 mm from the edges, the window at the bottom right, 15 mm kept white left and right of the block and 5 mm above and below |
| Poland | Poczta Polska, Zasady poprawnego adresowania i oznakowania przesyłek listowych (file of September 2025) | Zone published, exact position not published: the address field at the bottom right, at least 40 mm from the top and 15 mm from the right and bottom edges, at most 140 mm from the right edge; a window at least 15 mm from the right edge, the address 10 mm inside it and 5 mm inside its right edge |

For Spain, Italy and Poland the window is the DIN window mirrored to the right on a DL envelope
(90 x 45 mm, 20 mm from the right edge and 15 mm from the bottom): it lies inside all three zones,
but no operator's or maker's document gives that position. The address keeps to the part of it
that each operator's own clearances leave (Poland 10 mm, Italy 5 mm above and below) and that the
country's other usual envelope (115 x 225 mm in Spain, 110 x 230 mm in Italy) still shows; the
side margins in Spain and Italy are this pack's own, not published numbers.

The check reads the page (paper, window, the address lines), the parts, the date, the salutation
and closing for the variant, a Finnish letter's page numbers, and that every label is in the
letter's language. It does not judge the tone or whether the letter says the right thing, and it
cannot see the envelope: try one letter in the envelope you use before a mailing.

### Official texts

Where each named source is published (read 2026-10-09 to 2026-10-20; DIN 5008, NBN Z 01-002, NEN 1026,
ÖNORM A 1080, SFS 2487 and ISO 269 are sold, not published):

- DIN 5008:2020-03, DIN Media: https://www.dinmedia.de/de/norm/din-5008/318422674
- Directive (EU) 2017/1132 Art. 26: https://eur-lex.europa.eu/eli/dir/2017/1132/oj
- Germany: GmbHG § 35a https://www.gesetze-im-internet.de/gmbhg/__35a.html, AktG § 80
  https://www.gesetze-im-internet.de/aktg/__80.html, HGB § 37a https://www.gesetze-im-internet.de/hgb/__37a.html
- Sweden: aktiebolagslag (2005:551) 28 kap. 5 §:
  https://www.riksdagen.se/sv/dokument-och-lagar/dokument/svensk-forfattningssamling/aktiebolagslag-2005551_sfs-2005-551/
- United Kingdom: Companies Act 2006 s.82 https://www.legislation.gov.uk/ukpga/2006/46/section/82 and
  SI 2015/17 reg. 25 https://www.legislation.gov.uk/uksi/2015/17/regulation/25
- Ireland: Companies Act 2014 s.151 https://www.irishstatutebook.ie/eli/2014/act/38/section/151/enacted/en/html
- Belgium: Wetboek van vennootschappen en verenigingen art. 2:20
  https://www.ejustice.just.fgov.be/eli/wet/2019/03/23/2019A40586/justel
- Netherlands: Handelsregisterwet 2007 art. 27 https://wetten.overheid.nl/BWBR0021777 and BW Boek 2
  https://wetten.overheid.nl/BWBR0003045/
- Austria: UGB § 14 https://www.ris.bka.gv.at/NormDokument.wxe?Abfrage=Bundesnormen&Gesetzesnummer=10001702&Paragraf=14
- Spain: Código de Comercio art. 24 https://www.boe.es/buscar/act.php?id=BOE-A-1885-6627
- Italy: Codice civile arts. 2250 and 2497-bis https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1942-03-16;262
- Poland: Kodeks spółek handlowych arts. 206 and 374 https://isap.sejm.gov.pl/isap.nsf/DocDetails.xsp?id=WDU20000941037
- Australia: Corporations Act 2001 s 153 https://www.legislation.gov.au/C2004A00818/latest/text
- USPS Publication 28 https://pe.usps.com/text/pub28/28c2_009.htm; GOV.UK style guide
  https://guidance.publishing.service.gov.uk/writing-to-gov-uk-standards/style-guides/a-to-z-style-guide/;
  Australian Government Style Manual https://www.stylemanual.gov.au/content-types/emails-and-letters; OQLF
  https://vitrinelinguistique.oqlf.gouv.qc.ca/23309/la-redaction-et-la-communication/redaction-administrative-et-commerciale/correspondance/lettre/synthese-des-elements-de-la-lettre-administrative;
  Taaladvies.net https://taaladvies.net/opmaak-van-een-zakelijke-brief-in-nederland-algemeen/; Amtliches Regelwerk
  2024 https://www.rechtschreibrat.com/DOX/RfdR_Amtliches-Regelwerk_2024.pdf; Kielitoimiston ohjepankki
  https://kielitoimistonohjepankki.fi/ohje/sivunumerointi/; Unicode CLDR https://cldr.unicode.org/

## Say what passed, not more

Tell the person which checks the letter passed and against which source and version. Never call
the letter certified, compliant or approved, and give no legal, tax or accounting advice.
