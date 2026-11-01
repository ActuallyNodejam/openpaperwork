---
name: annual-accounts
description: "Annual report (årsredovisning) of a smaller Swedish company under K2, as Word: management report, income statement, balance sheet and notes, added up and checked."
version: 0.1.0
license: Apache-2.0
platforms: [linux, macos, windows]
metadata:
  domain: finance
  version: "0.1.0"
workflows:
  - id: "annual-report"
    arguments: "annual report"
    icon: "file-text"
    menu: "Årsredovisning"
    menu_en: "Annual report"
    gives: "En årsredovisning enligt K2 i Word, summerad och kontrollerad"
    gives_en: "A K2 annual report in Word, added up and checked"
    takes: "Släpp saldobalansen eller fjolårets årsredovisning"
    takes_en: "Drop the trial balance or last year's annual report"
---

# Annual accounts

Use this when someone asks for the annual report of a smaller Swedish aktiebolag: an årsredovisning
under årsredovisningslagen (1995:1554) that follows Bokföringsnämndens K2 rules (BFNAR 2016:10). The
figures come from the company's own books, a trial balance (saldobalans) or last year's report. The
report sets them out; it never makes them up.

A drafting check, not accounting advice: it reads which parts are there and whether the numbers add up,
never whether a valuation, a tax figure or a dividend is right. The board signs the report and answers
for it (ÅRL 2 kap. 7 §; Directive 2013/34/EU Art. 33).

A smaller company is one whose shares or other securities are not traded on a regulated market and
that does not pass more than one of these in each of the last two years: 50 employees on average,
40 million kronor in total assets, 80 million kronor in net sales (ÅRL 1 kap. 3 § första stycket 4,
as in force on 2026-10-20; Sweden kept these figures when Delegated Directive (EU) 2023/2775 raised
the Directive's limits). A larger company, or a smaller one that has chosen K3 (BFNAR 2012:1), needs more
than this pack writes: say so and stop.

## How to make one

1. Read what the person gave you: the trial balance, last year's report, their notes. Ask nothing they
   already say.
2. Write a small spec file (JSON). Start from `templates/arsredovisning-konsult.spec.json` (Swedish, a
   two-person consultancy with a profit and a dividend) or `templates/annual-report-cleaning.spec.json`
   (English, a cleaning company with a loss and a shareholder contribution). `"language": "sv"` or `"en"`.
3. Put every account into the line it belongs to (the keys are listed in the script). Income is
   positive and costs negative, as they print. Give this year and last year as `[this, last]`.
4. Ask only for what the report cannot be laid out without, when the notes leave it out: the board
   and the managing director who sign, the dividend the board proposes and the average number of
   employees. Never fill one in yourself.
   The rest can wait for the person, so build the draft without it: last year's figures, net sales,
   result after financial items and equity ratio for the two years before last year
   (`report.earlier_years`, for the multi-year overview), what happened during the year
   (`report.events`) and the date the board signs (`signing.date`). Declare each one the notes leave
   out in `"unknown"`: `["prior", "report.earlier_years", "report.events", "signing.date"]`. The page
   leaves it empty, the script's warnings name it, and your reply names it as still open. With
   `"prior"` unknown, give this year's figures only (`[this, null]`, this year's retained earnings
   from the trial balance) and the last year's dates in `prior`. Put what you do have for last year,
   such as its net sales and result after financial items, in `report.earlier_years`.
5. Build the report:

```bash
python3 <skill folder>/scripts/annual_create.py spec.json arsredovisning.docx
```

   The script adds up every subtotal and result, works out this year's equity from last year's and the
   changes (`"retained": [null, last year]`), and prints warnings where the figures you gave disagree.
   A warning is a question for the person, never something to smooth over.
6. Run the pack check and fix what it names:
   `python3 <skill folder>/../_checks/packcheck.py annual-accounts <your output>`

## Nothing given is left off

`annual_create.py` stops before anything is laid out when the spec holds a key it has no field for,
a value of another shape, or a line the income statement or balance sheet does not have, and names
it (`spec.fields.json` beside this file lists every key; the lines are INCOME, ASSETS and
LIABILITIES in the script). What the report must say that has no field goes in `notes`, each with a
title and a text. Never leave a fact out to make the error go away: put it where the message says,
or say in your reply what the page does not carry.

Run the check with `--in` and the working folder. It then reads the person's own files there and
asks, once and never as a fail (NOTES-FLOOR): which e-mail addresses, numbers, dates and amounts the
notes hold and the page does not, which of them the page carries changed. Answer the question once:
put each on the page as the notes have it, or say in your reply why it does not belong there. Never
change one to shorten the list.

Work in the working folder, the folder the person is working in: write the data file there, run the
script from there by its full path (`<skill folder>` is the folder this file is in) and give the
output a path there. The builder refuses an output path inside the library's own folder, where the
person never looks; hand back the path in the working folder.

## What the report holds, in this order

| Part | What it carries | Source |
| --- | --- | --- |
| Front | The company's name and organisation number, the financial year, the unit (whole kronor) | ÅRL 2 kap. 5 §; BFNAR 2016:10 kap. 3 |
| Förvaltningsberättelse | The business and its seat; significant events during the year; a multi-year overview of net sales, result after financial items and equity ratio for the year and the three before it, with a comment when net sales vary by more than 30 percent between the years; the changes in equity; the proposed disposition of the result | ÅRL 6 kap. 1 and 2 §§; BFNAR 2016:10 kap. 5, punkt 5.5 |
| Resultaträkning | By nature of expense, last year beside this year, subtotals down to the year's result | ÅRL 3 kap. 3 and 5 §§, bilaga 2; Directive 2013/34/EU Art. 9(5), 13, Annex V |
| Balansräkning | Assets, then equity (restricted and unrestricted), untaxed reserves, provisions and liabilities, last year beside this year | ÅRL 3 kap. 3-5 §§, bilaga 1; Directive Art. 10, 14, Annex III |
| Noter | Accounting policies; the average number of employees; each fixed asset's cost and depreciation; pledged assets and contingent liabilities ("Inga" when there are none); significant events after the year end, when there are any | ÅRL 5 kap. 4, 8, 14, 15, 20 and 22 §§; Directive Art. 16(1); BFNAR 2016:10 kap. 18 |
| Underskrifter | Place and date, then every board member and the managing director by name; the auditor's line when the company has one | ÅRL 2 kap. 7 § |

The page follows the shape of the published Swedish examples (the K2 general advice's own examples
and the reports companies file): the first page names the company, its organisation number and the
year, then the management report; the income statement, the balance sheet (assets on one page, equity
and liabilities on the next), the notes and the signatures each start a new page; every later page
carries the company, its organisation number and "2 (6)" in its header. Amounts sit right-aligned in
the same columns throughout, with a space between thousands and a true minus sign in Swedish and a
comma in English; only subtotals and totals are bold, under a thin rule.

A smaller company may merge the balance sheet items preceded by arabic numerals (ÅRL 3 kap. 4 §;
Directive Art. 14), and the first items of the income statement into one gross profit line
(ÅRL 3 kap. 11 §). The script writes the lines that carry a figure in either year and leaves out the
rest.

The builder warns when the multi-year overview has fewer than four years or when net sales move by
more than 30 percent between two of them (BFNAR 2016:10 punkt 5.5). A younger company has fewer
years; say so. For the swing, ask the company what happened and put it in `report.events`.

## Who may not use K2

K2 (BFNAR 2016:10) is only for a smaller company (ÅRL 1 kap. 3 § första stycket 5), and BFN's own
scope rules (punkter 1.1A to 1.1C, as amended by BFNAR 2025:2) leave these out. Ask before you write
a K2 report when any may apply, and write none when one does:

- a public company (publikt aktiebolag);
- a parent company of a larger group, or of a smaller group that prepares consolidated accounts;
- a natural person or an estate (dödsbo);
- a bostadsrättsförening or bostadsförening;
- a company that has, or had during the year, a branch abroad;
- a company that acquired goods or services against share-based payment during the year;
- a company that has, or had during the year, convertible debt it issued or similar compound
  financial instruments;
- a company that holds, or held during the year, crypto-assets (one that only now and then took or
  used them as payment is not left out);
- a company with a material deferred tax liability, or with one or more buildings that bring at
  least 75 percent of its net sales (punkt 1.1B), unless it meets at most one of: more than 3
  employees, more than SEK 1.5 million in total assets, more than SEK 3 million in net sales, in each
  of the last two years, or it used K2 the year before and is normally outside 1.1B (punkt 1.1C).

Source: Bokföringsnämnden, BFNAR 2016:10 kapitel 1,
https://www.bfn.se/wp-content/uploads/vl16-10-k2ar-kons2025.pdf

## Never work these out

The tax on the year's result, a depreciation period, a valuation, the size of a periodiseringsfond and
whether a dividend can be paid are the company's and its accountant's calls. Write what they give you.
A proposed dividend needs the board's own statement on it (aktiebolagslagen 18 kap. 4 §, with the
prudence rule in 17 kap. 3 §): ask the board for it, put it under the disposition, never write it
yourself. When there is reason to believe equity is below half the registered share capital, tell the person
what aktiebolagslagen 25 kap. 13 § says: the board must at once draw up a kontrollbalansräkning and
have the company's auditor review it. The same applies when an enforcement under utsökningsbalken
shows the company cannot pay the debt in full. Say no more than the law says; what follows is the
board's and its advisers' work.

Rounding: give whole kronor and let the script add. A report in thousands (tkr) rounds each line and
then adjusts one line so the sums still add; say which line, never leave a total that does not add.

## What the check reads

| Rule | What it reads |
| --- | --- |
| ANNUAL-PARTS | The five parts in K2's order; the name and organisation number; the business, the significant events, the multi-year overview, the changes in equity and the disposition in the management report |
| ANNUAL-PAGES | Each part starts on a page of its own |
| ANNUAL-AMOUNTS | One unit, stated, and whole numbers throughout |
| ANNUAL-YEARS | The financial year is stated; both statements give last year's figure on every line (not for a company's first year) |
| ANNUAL-SUMS | Every subtotal and result line is the sum of the lines it covers, both years |
| ANNUAL-BALANCE | Total assets equal total equity and liabilities, both years |
| ANNUAL-RESULT | The year's result is the same in the income statement, the balance sheet, the changes in equity, the disposition and the multi-year overview |
| ANNUAL-EQUITY | The changes in equity run from last year's balance sheet to this year's, column by column |
| ANNUAL-DISPOSITION | The funds at the meeting's disposal are the unrestricted equity, and the proposal disposes of exactly that sum |
| ANNUAL-NOTES | Accounting policies and employees are there; notes run 1, 2, 3; every note a statement points to exists; every fixed asset points to a note, and its carrying amount is the balance sheet's |
| ANNUAL-SIGNED | A signatures part, dated after the year end, with the signatories' names |

## Say what passed, not more

Tell the person which checks the report passed: which items are there and that the numbers add up.
Never call it correct, compliant, lawful, approved or ready to file; the board adopts and signs it, the
annual general meeting adopts the statements, and a board member or the managing director files a
certified copy with Bolagsverket (ÅRL 8 kap. 3 §). Suggest they check anything the check flags with
their accountant.

## Sources

Each read in its official text as in force on 2026-10-20.

- Årsredovisningslag (1995:1554), Sveriges riksdag:
  https://www.riksdagen.se/sv/dokument-och-lagar/dokument/svensk-forfattningssamling/arsredovisningslag-19951554_sfs-1995-1554/
- Aktiebolagslag (2005:551), Sveriges riksdag:
  https://www.riksdagen.se/sv/dokument-och-lagar/dokument/svensk-forfattningssamling/aktiebolagslag-2005551_sfs-2005-551/
- BFNAR 2016:10, Årsredovisning i mindre företag (K2), Bokföringsnämnden, consolidated with BFNAR 2024:4
  and 2025:2: https://www.bfn.se/wp-content/uploads/vl16-10-k2ar-kons2025.pdf
- Directive 2013/34/EU (the Accounting Directive): https://eur-lex.europa.eu/eli/dir/2013/34/oj, and
  Delegated Directive (EU) 2023/2775, which raised its size limits: https://eur-lex.europa.eu/eli/dir_del/2023/2775/oj
