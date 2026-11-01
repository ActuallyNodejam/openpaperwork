---
name: meeting-minutes
description: "Minutes of any meeting (Protokoll, protokoll, notulen, procès-verbal) as Word: board, general, club or association, with what the country's law asks to record."
version: 0.4.0
license: Apache-2.0
platforms: [linux, macos, windows]
metadata:
  domain: operations
  version: "0.4.0"
workflows:
  - id: "minutes"
    arguments: "minutes"
    icon: "file-text"
    menu: "Protokoll"
    menu_en: "Minutes"
    gives: "Ett protokoll i Word med det lagen kräver för mötet"
    gives_en: "Minutes in Word with what the law asks to record for the meeting"
    takes: "Släpp anteckningarna från mötet"
    takes_en: "Drop your notes from the meeting"
---

# Meeting minutes

Use this when someone asks for the minutes of a meeting from their notes. Minutes record what
was done, not what was said: who met, when and where, every motion or decision and how it ended,
and who signs. One script writes that, so your attention goes to getting the facts right. Minutes
are edited and signed, so they come back as Word.

## How to make them

1. Read the notes, the agenda and the list of who came. Ask nothing the notes already say.
2. Write a small spec file (JSON). Start from the template that fits:

| Meeting | Template |
| --- | --- |
| A club or association (Robert's Rules) | `templates/minutes.spec.json` |
| Sweden, board (styrelseprotokoll) | `templates/styrelseprotokoll.spec.json` |
| Norway, board (styreprotokoll) | `templates/styreprotokoll.spec.json` |
| Norway, general meeting (generalforsamling) | `templates/generalforsamlingsprotokoll.spec.json` |
| Denmark, board (bestyrelsesprotokol) | `templates/bestyrelsesprotokol.spec.json` |
| Denmark, general meeting | `templates/generalforsamling-dk.spec.json` |
| Finland, board (hallituksen pöytäkirja) | `templates/hallituksen-poytakirja.spec.json` |
| Finland, general meeting (yhtiökokous) | `templates/yhtiokokous.spec.json` |
| United Kingdom, board | `templates/board-minutes-uk.spec.json` |
| United States, board | `templates/board-minutes-us.spec.json` |
| Canada, board, English or French (procès-verbal) | `templates/board-minutes-ca.spec.json`, `templates/proces-verbal-ca.spec.json` |
| Australia, board | `templates/board-minutes-au.spec.json` |
| Belgium, board (raad van bestuur, conseil d'administration) | `templates/notulen-raad-van-bestuur-be.spec.json`, `templates/pv-conseil-administration-be.spec.json` |
| Belgium, general meeting | `templates/notulen-algemene-vergadering-be.spec.json`, `templates/pv-assemblee-generale-be.spec.json` |
| Netherlands, board and general meeting (notulen) | `templates/notulen-bestuursvergadering-nl.spec.json`, `templates/notulen-algemene-vergadering-nl.spec.json` |
| Austria, supervisory board (Niederschrift) | `templates/niederschrift-aufsichtsrat-at.spec.json` |
| Austria, a GmbH's general meeting | `templates/niederschrift-generalversammlung-at.spec.json` |
| Ireland, board and general meeting | `templates/board-minutes-ie.spec.json`, `templates/agm-minutes-ie.spec.json` |
| Spain, board (acta del consejo) and general meeting (junta general) | `templates/acta-consejo-es.spec.json`, `templates/acta-junta-general-es.spec.json` |
| Italy, an S.p.A.'s assembly (verbale di assemblea) and board | `templates/verbale-assemblea-it.spec.json`, `templates/verbale-consiglio-it.spec.json` |
| Poland, a sp. z o.o.'s shareholders' meeting and management board (protokół) | `templates/protokol-zgromadzenia-wspolnikow-pl.spec.json`, `templates/protokol-zarzadu-pl.spec.json` |

   `country` is the law the company is under; `language` is `en`, `sv`, `nb`, `da`, `fi`, `fr`,
   `nl`, `de`, `es`, `it` or `pl`. The company's name tells its form (BV, NV, SRL, SA, GmbH, AG,
   S.L., S.p.A., S.r.l., sp. z o.o.), and the form picks the article; say `legal_form` when the
   name does not end in it. In Spain, Italy and Poland a decision carries its count: `votes` with
   `for`, `against` and `abstained`, or `unanimous`, or the names of who voted which way.
   For a board, `present` lists the directors there and `in_attendance` everyone else (the CEO, the
   secretary when not a director). A decision may name who voted for and against.
3. Build the minutes:

```bash
python3 <skill folder>/scripts/minutes_create.py spec.json minutes.docx
```

4. Keep the spec beside the file and run the pack check; fix what it names:
   `python3 <skill folder>/../_checks/packcheck.py meeting-minutes <your output>`

## Nothing given is left off

`minutes_create.py` stops before anything is laid out when the spec holds a key it has no field for
(`description` or `resolution` on an item, `apologies`), a value of another shape, or a key these
minutes have no line for (Spain's `convened` in English minutes), and names the key.
`spec.fields.json` beside this file lists every key. What was reported under an item goes in the
item's `notes` (a string, or a list of paragraphs), what was decided in its `decisions`; a fact
about the meeting as a whole that has no field (that notice was given, what the quorum is) goes in
the top-level `notes`, one line each, printed before the first item. Who abstained is named when a
decision gives `abstained`; `previous_minutes` in your own words is printed as written. Never leave
a fact out to make the error go away: put it where the message says, or say in your reply what the
page does not carry.

The check fails minutes with a heading and nothing recorded under it (MINUTES-EMPTY, a house rule):
where the meeting decided nothing under an item, say so in the item's `notes`.

Run the check with `--in` and the working folder. It then reads the person's own files there and
asks, once and never as a fail (NOTES-FLOOR): which e-mail addresses, numbers, dates and amounts the
notes hold and the page does not, which of them the page carries changed, and which figures the
minutes state that the notes do not. Answer the question once: put each on the page as the notes
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

## What minutes record

From Robert's Rules of Order Revised (1915), section 60, which is in the public domain: the kind of
meeting, the body, the date and place, the chair and the secretary, whether the last minutes were
approved, every main motion that was not withdrawn with who moved it (not who seconded it) and
whether it was adopted or lost, the counted vote when there was one, the hours of opening and
adjournment, and the secretary's signature. Leave out speeches, praise and blame.
That printing is not the current edition: Robert's Rules of Order Newly Revised, 12th edition (2020),
is under copyright and is not used here. A club whose bylaws adopt it may differ in detail; say so
when the person's bylaws name it.

A company's law asks for more, and the script writes it:

| Country | Board | General meeting |
| --- | --- | --- |
| Sweden | aktiebolagslagen 8 kap. 24 och 26 §§: every decision, numbered minutes, the minute-taker signs, the chair and one more director check (justerar), a dissent (reservation) recorded | 7 kap. 48 § |
| Norway | aksjeloven § 6-29: time and place, the participants, how the board dealt with it (Behandlingsmåte), the decisions, who voted for and against a split decision, a view recorded on request; every director who took part signs (a board of five or more may pick two, `signers`) | § 5-16: the form of the meeting, each decision with its vote, the list of shareholders present; the chair and one person the meeting picks sign |
| Denmark | selskabsloven § 128: a protocol every director present signs; a director's view recorded on request | § 101: the dirigent leads and signs; available within two weeks |
| Finland | osakeyhtiölaki 6:6: the chair and at least one director the board picks sign, a dissent (eriävä mielipide) recorded, minutes numbered in sequence | 5:23: the voting list (ääniluettelo), the decisions and votes, the chair and one minutes checker sign; available within two weeks |
| United Kingdom | Companies Act 2006 s.248 (kept ten years), s.249 (signed by the chair as evidence); Model Articles art. 11 (quorum) | s.355 and s.356 |
| United States | Delaware General Corporation Law § 142(a) (an officer records the proceedings), § 141(b) (quorum), § 141(f) (written consent filed with the minutes) | |
| Canada | CBCA s.20 (minutes kept), s.114 (quorum), s.117 (a written resolution signed by every director, kept with the minutes) | |
| Australia | Corporations Act 2001 s.251A: recorded within one month, signed by the chair within a reasonable time | s.251A |
| Belgium | Companies and associations code (WVV, CSA) art. 5:75 (BV, SRL), 6:63 (CV, SC), 7:95 (NV, SA): the chair signs, and any director who asks; a director's conflict of interest and the reasons go in the minutes (art. 5:76, 6:64, 7:96; `conflict` on the item) | art. 5:90, 6:76, 7:138: an attendance list at every meeting; art. 5:93, 6:79, 7:141: the bureau signs (chair, secretary, vote counters in `checkers`); art. 5:89, 6:75, 7:137: technical problems that kept people from taking part online (`incidents`) |
| Netherlands | Boek 2 BW sets nothing for a board's minutes; the articles of association do | BW art. 2:230 lid 4 (BV), 2:120 lid 4 (NV): the board keeps a record of the resolutions adopted |
| Austria | The supervisory board (Aufsichtsrat): AktG § 92 (2), GmbHG § 30g (2): a Niederschrift signed by its chair or the deputy | A GmbH: GmbHG § 40: resolutions entered in a Niederschrift without delay, and the copy sent to every shareholder states the day they were entered (`recorded`). An AG: AktG § 120, a notary records the meeting, so the script's file is a working record only |
| Ireland | Companies Act 2014 s.166: the directors present and every resolution, signed by the chairperson as evidence; s.160(6) quorum; s.161 a written resolution signed by every director | s.199: the proceedings and the terms of every resolution, signed by the chairperson |
| Spain | Ley de Sociedades de Capital art. 250: the acta signed by the chair and the secretary. Reglamento del Registro Mercantil art. 97: the date and place, how and when the meeting was called (`convened`), the members there and those another member stood for (`represented`), a summary, each resolution and how many voted for it, an opposition recorded on request, the acta's approval (art. 99; `minutes_approved` when it was not at the meeting's end); the secretary signs with the chair's visto bueno | LSC art. 202: every resolution in an acta, approved by the junta at its end or within fifteen days by the chair and two members (`checkers`); art. 192: the list of those attending, inside the acta in an S.L.; RRM art. 97: how many came in person and by proxy and their share of the capital (`total_shares`), the votes on each resolution; a junta universal (`universal`) needs no call and every member signs; LSC art. 203: a notary called to the junta draws up the acta, so the script's file is a working record only |
| Italy | The Codice civile sets no contents for a board's verbale; arts. 2421 and 2478 ask that it be entered in the company's book | An S.p.A.: art. 2375: the date, who took part and the capital each stood for (in the verbale or attached), how the votes were cast (`voting`) and their result, who was for, abstained or dissented, signed by the chair and the secretary; art. 2371: the chair's findings on the constitution and on who was there. An S.r.l.: art. 2479-bis, the chair's findings and the votes. An extraordinary assembly's verbale is a notary's, so the script's file is a working record only |
| Poland | Kodeks spółek handlowych art. 208(1) (sp. z o.o.) and art. 376 (S.A.): the agenda, the members present, the votes on each resolution, a dissenting opinion with its reasons, signed at least by the member who chaired; the supervisory board the same (arts. 222 § 2 and 391 § 2; `organ`: `supervisory`) | A sp. z o.o.: art. 248: that the meeting was properly called and can resolve, the resolutions, the votes for each, the objections, the attendance list attached; signed by those present or at least the chair and the minute-taker. An S.A.: art. 421, a notary draws up the protocol, so the script's file is a working record only |

Nordic minutes open with the business their meetings record as items of their own (in Finland the
opening, the quorum and the choice of checker; at a Norwegian or Danish general meeting the choice
of who leads). Dates are written out (20. oktober 2026, 20 October 2026, October 20, 2026,
23.4.2026, 20 oktober 2026, 20. Jänner 2026 in Austria, 14 de octubre de 2026, 14 ottobre 2026,
14 października 2026); times are 16.00 in the Nordic languages, 2:00 p.m. in the US, 16 h 30 in
Canadian French, 9:05 in Spanish and 16:30 in Dutch, German, Belgian French, Italian and Polish.
Every label and signature role is in the minutes' language.

The Danish rules were read again on 2026-10-09 against the four acts that have amended
selskabsloven since its 2025 consolidation (lov nr. 710, 1648 and 1765 of 2025 and nr. 729 of
2026): none changes § 101 or § 128.

What the check cannot see: that the minutes were drawn up within a month, kept for ten years or
put before the shareholders within two weeks; that an Austrian GmbH sent every shareholder a copy
by registered letter; that a Belgian or Dutch company's articles ask for more; that the full text
of a Spanish meeting's call is the one sent, or that the acta was entered in the book; that an
Italian verbale was drawn up without delay; that a Polish attendance list carries its signatures.
The Spanish register rules bind only for entry in the Registro Mercantil (art. 97.3). Say so when
it matters.

The Spanish, Italian and Polish articles were read on 2026-10-09 and 2026-10-10 in the official
consolidated texts: the BOE (Ley de Sociedades de Capital, last updated 19 December 2025, arts. 192, 202, 203 and 250 unchanged when read again on 2026-10-20; Reglamento
del Registro Mercantil, 14 June 2023), Normattiva (Codice civile, text in force) and ISAP (Kodeks
spółek handlowych, unified text as of 3 June 2026).

## Say what passed, not more

Tell the person which checks the minutes passed and against which source. Never call the minutes
approved, certified or legally valid; they are approved when the people named sign them, and give
no legal advice.

## Sources

The official text of each law, as in force on 2026-10-20:

| Country | Law | Official text |
| --- | --- | --- |
| Club or association | Robert's Rules of Order Revised (1915), section 60 | https://www.gutenberg.org/ebooks/75990 |
| Sweden | Aktiebolagslag (2005:551) | https://www.riksdagen.se/sv/dokument-och-lagar/dokument/svensk-forfattningssamling/aktiebolagslag-2005551_sfs-2005-551/ |
| Norway | Aksjeloven (LOV-1997-06-13-44) | https://lovdata.no/lov/1997-06-13-44 |
| Denmark | Selskabsloven (LBK nr. 331 af 20/03/2025) | https://www.retsinformation.dk/eli/lta/2025/331 |
| Finland | Osakeyhtiölaki 624/2006 | https://www.finlex.fi/fi/lainsaadanto/2006/624 |
| United Kingdom | Companies Act 2006; Model Articles, SI 2008/3229 Sch. 1 | https://www.legislation.gov.uk/ukpga/2006/46, https://www.legislation.gov.uk/uksi/2008/3229/schedule/1 |
| United States | Delaware General Corporation Law, Title 8 | https://delcode.delaware.gov/title8/c001/sc04/index.html |
| Canada | Canada Business Corporations Act | https://laws-lois.justice.gc.ca/eng/acts/C-44/ |
| Australia | Corporations Act 2001 | https://www.legislation.gov.au/C2004A00818/latest/text |
| Belgium | Wetboek van vennootschappen en verenigingen / Code des sociétés et des associations | https://www.ejustice.just.fgov.be/eli/wet/2019/03/23/2019A40586/justel |
| Netherlands | Burgerlijk Wetboek Boek 2 | https://wetten.overheid.nl/BWBR0003045/ |
| Austria | GmbH-Gesetz; Aktiengesetz | https://www.ris.bka.gv.at/GeltendeFassung.wxe?Abfrage=Bundesnormen&Gesetzesnummer=10001720, https://www.ris.bka.gv.at/GeltendeFassung.wxe?Abfrage=Bundesnormen&Gesetzesnummer=10002070 |
| Ireland | Companies Act 2014 (revised) | https://revisedacts.lawreform.ie/eli/2014/act/38/revised/en/html |
| Spain | Ley de Sociedades de Capital; Reglamento del Registro Mercantil | https://www.boe.es/buscar/act.php?id=BOE-A-2010-10544, https://www.boe.es/buscar/act.php?id=BOE-A-1996-17533 |
| Italy | Codice civile | https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1942-03-16;262 |
| Poland | Kodeks spółek handlowych | https://isap.sejm.gov.pl/isap.nsf/DocDetails.xsp?id=WDU20000941037 |
