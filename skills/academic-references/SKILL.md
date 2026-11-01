---
name: academic-references
description: "Citations and reference lists in APA 7 (default), IEEE or Vancouver: write, fix or convert them in a paper, thesis, report or literature review."
version: 0.2.0
license: Apache-2.0
platforms: [linux, macos, windows]
metadata:
  domain: academic
  version: "0.2.0"
workflows:
  - id: "references"
    arguments: "references"
    icon: "bullet-list"
    menu: "Referenslista"
    menu_en: "References"
    gives: "En referenslista som Word-fil i APA 7, IEEE eller Vancouver, varje post kontrollerad"
    gives_en: "A reference list as a Word file in APA 7, IEEE or Vancouver, every entry checked"
    takes: "Släpp dokumentet eller listan och skriv vilken stil"
    takes_en: "Drop the document or the list and say which style"
---

# Academic references

Every rule here comes from the style's own publisher:

| Style | Source |
| --- | --- |
| APA 7 | Publication Manual of the American Psychological Association, 7th edition (2020): §2.11, §2.12, §2.19, §2.27, §8.4, §9.8, §9.44 for the rules below; `apa.csl` from the Citation Style Language project for the forms |
| IEEE | IEEE Reference Guide, version 3.28.2025 (IEEE Author Center); `ieee.csl` for the forms |
| Vancouver | Citing Medicine, 2nd edition (National Library of Medicine, Patrias and Wendling, 2007-, NCBI Bookshelf NBK7256), public domain: chapter 1 journals (1B on the Internet), chapter 2 books; NLM's Samples of Formatted References for Authors of Journal Articles; ICMJE Recommendations (updated January 2026) IV.A.3.g References, cited and restated, never quoted. The CSL `vancouver.csl` was read to learn the forms; no part of it is copied |

The rules and their sections are in `standards/guidelines/apa/7`, `ieee/2025-03-28` and
`nlm-citing-medicine/2`.
The shape (a few rules, then forms, then a check) follows the research-agent skill pattern
described by alphaXiv OpenResearch. Use the docx skill for the file mechanics.

## Rules

1. Keep every source the document already cites unless the user asks to
   remove one; converting a style never removes or merges sources.
2. Never fabricate a citation. Cite only sources the user supplied or the
   document already cites. A detail the source does not give (editor, city,
   issue, DOI, first name) stays out. A source the user says they have not
   read is not cited.
3. Cite a source only for what it reports, and keep its limits: correlational
   stays correlational, self-reported stays self-reported, a subgroup effect
   is not an overall effect.
4. Use the style the user, journal or university template names. A supplied
   template or style file wins over these notes. A medical, nursing or health
   sciences journal or course that asks for Vancouver, ICMJE or NLM style gets
   Vancouver. With none, use APA 7.
5. On a revision, change every place the changed value appears (text,
   citations, list, order) and nothing else. When a source is replaced,
   rewrite the sentence so it reads as one claim with one citation; never
   cite the same work twice in a sentence as if it were two studies.
6. Before saving, run the checks at the end. Do not hand back a list that
   fails them.

## APA 7 in-text citations

- Parenthetical: (Surname, 2021); (Surname & Other, 2021); (Surname et al., 2021).
- Narrative: Surname (2021); Surname and Other (2021); Surname et al. (2021).
- Three or more authors: first author plus et al. from the first citation.
- Group author: (Name of Group, 2024) or Name of Group (2024).
- Several works: (Adams, 2019; Baker & Cole, 2022), alphabetical, separated by semicolons.
- A number used as a noun ("As [3] showed") becomes a narrative citation.

## APA 7 reference forms

Authors: Surname, I. I., up to 20, comma separated, & before the last. With 21 or more:
the first 19, then ". . ." and the last author, no ampersand (§9.8).
Year in parentheses then a period. Titles of works in sentence case (first
word, first word after a colon, proper nouns). DOI as https://doi.org/...
with no label. Page ranges with an en dash (–), never a hyphen.

| Type | Form (italic part in *stars*) |
| --- | --- |
| Article | Surname, A. B., & Other, C. (2021). Title of article. *Journal Name, 12*(3), 45–67. https://doi.org/10.xxxx/yyy |
| Book | Surname, A. (2019). *Title of book: Subtitle*. Publisher. |
| Chapter | Surname, A. (2019). Title of chapter. In E. Editor & F. Editor (Eds.), *Title of book* (pp. 201–219). Publisher. |
| Chapter, editors unknown | Surname, A. (2019). Title of chapter. In *Title of book* (pp. 201–219). Publisher. |
| Report | Name of Group. (2024). *Title of report* (Report No. 7). Publisher. |
| Preprint | Surname, A., & Other, B. (2023). *Title of preprint* [Preprint]. Archive Name. https://doi.org/10.xxxx/yyy |

APA prefers the published version of a work over its preprint. When a draft
cites both, keep both, since the author may cite the preprint for its date,
and tell the user in your reply that APA would cite the published version.
Drop the preprint only when the user asks.

## APA 7 page format in a .docx

- One font: Times New Roman 12, Calibri 11, Arial 11 or Georgia 11.
- Double spacing everywhere, references included; 0 pt before and after.
- Body paragraphs: first-line indent 0.5 in. References: hanging indent
  0.5 in (left indent 0.5 in, first line -0.5 in).
- Level 1 heading and the References label: centered, bold.
- Italics are runs: split each entry into runs so only the journal name and
  volume, or the book, report or preprint title, are italic.

```python
from docx.shared import Inches, Pt
p = doc.add_paragraph()
f = p.paragraph_format
f.left_indent, f.first_line_indent = Inches(0.5), Inches(-0.5)
f.line_spacing, f.space_before, f.space_after = 2.0, Pt(0), Pt(0)
p.add_run('Surname, A. (2021). Title of article. ')
p.add_run('Journal Name, 12').italic = True
p.add_run('(3), 45–67. https://doi.org/10.xxxx/yyy')
```

## IEEE

Numbers in square brackets, on the line and inside the punctuation, in order of
first citation. Ranges are written out: [1], [2], [3], [4], not [1]–[4] (Reference
Guide 3.28.2025). A paper built on IEEE's own LaTeX template keeps the template's
form. The list is numbered in citation order, not alphabetical. Authors initials
first, all of them up to six, more than six as the first author and et al.; in the
text, three or more names are the first author and et al. Article titles in
quotation marks; journal abbreviated and italic; vol., no., pp., abbreviated month
and year; doi: 10.xxxx; every reference ends with a period.

## Vancouver

Numbered citations in the order the text first cites each source, the style the ICMJE
Recommendations ask of medical journals. Each rule has an id the check names when it fails.

| Rule | What it asks | Source |
| --- | --- | --- |
| VANC-ORDER | Number sources 1, 2, 3 in the order the text first cites them; a number in a table or figure legend counts where the table is first cited | ICMJE IV.A.3.g.ii; Citing Medicine, introduction (citation-sequence) |
| VANC-MARKS | One in-text form throughout: [1], (1) or superscript¹. Ranges as 1-3, lists as 1,4 | ICMJE IV.A.3.g.ii (numerals in parentheses); a journal's own form wins |
| VANC-LIST | The list runs in number order, one entry per number, no gaps | Citing Medicine, citation-sequence |
| VANC-CITED | Every entry is cited and every cited number has an entry | Citing Medicine, citation-sequence (the list holds the works the text cites) |
| VANC-ONCE | A source cited again keeps its first number; never list it twice | Citing Medicine, citation-sequence |
| VANC-AUTHORS | Surname then initials, no full stops or spaces in the initials (Halpern SD); the first six authors, then et al. | Citing Medicine 1A (author); NLM sample references, item 1 |
| VANC-JOURNAL | Journal titles abbreviated NLM style, without full stops (N Engl J Med). The check reads the full stops only; it does not know whether an abbreviation is right | ICMJE IV.A.3.g.ii; Citing Medicine 1A (title of journal) |
| VANC-DATE | Journal entries read year;volume(issue):pages, e.g. 2021;12(3):45-57, with no vol., no., pp. or (year) | Citing Medicine 1A; NLM sample references, item 1 |
| VANC-ONLINE | A source read online carries [Internet] after the title or journal, a date of citation [cited 2026 Oct 9] and "Available from:" with its URL; a DOI goes after the pages as doi:10.xxxx | Citing Medicine 1B and 2B |

| Type | Form |
| --- | --- |
| Article | Okafor-Lindqvist PA, Brennan-Toft J, Halloway R. Title of article. J Abbrev Title. 2021;12(3):45-57. doi:10.xxxx/yyy |
| Seven or more authors | First six, then et al.: Brennan-Toft J, Asterly M, Pell D, Quorrin S, Venn T, Yarrow K, et al. Title. ... |
| Group author | Name of Organisation. Title of report. City: Publisher; 2024. Report No.: 7. |
| Book | Mistral A, Fenwick-Oyelaran B. Title of book. 2nd ed. City: Publisher; 2022. |
| Article read online | Surname A. Title. J Abbrev Title [Internet]. 2025 Mar [cited 2026 Oct 9];8(2):101-9. Available from: https://... |
| Web page | Title of page [Internet]. City: Publisher; 2025 [updated 2025 Jun 3; cited 2026 Oct 9]. Available from: https://... |

A detail the source does not give stays out; never invent an issue, a page range or a DOI (rule 2).
Converting to Vancouver from APA renumbers every citation in order of first mention.

### Build it

Write a spec and build the document; the builder numbers the sources from the text, so the order,
the list and the cross-check cannot drift:

    python3 <skill folder>/scripts/vancouver_create.py spec.json report.docx

Start from `templates/vancouver.spec.json` (a short invented ward audit). A citation in the text
is `[@key]` or `[@key1; @key2]`; `"marks"` is `brackets`, `superscript` or `parentheses`. The
builder refuses a key the spec does not list and a listed source the text never cites, writes the
author, journal, date and online forms above, and runs the VANC rules on what it wrote.

### Check it

    python3 <skill folder>/../_checks/packcheck.py academic-references report.docx

It prints one `FAIL <rule id> <evidence>` line per rule that fails; fix those and run it again. The
check reads the list's form, never the science: a clean run does not mean the paper is right or
ready to submit, and the reply never says so. On a numbered list the APA rules stand aside, and on
an author-date list the VANC rules do. `scripts/repair_refs.py` reports an uncited numbered entry
but never edits a numbered list; rebuild through the spec instead, which numbers the rest again.

## Check before saving

Reopen the saved file and confirm:

1. Every in-text citation has a list entry with the same first author and
   year, and every entry is cited (§8.4). A personal communication is cited
   in the text only and never listed.
2. The list is alphabetical (APA) or numbered in citation order (IEEE, Vancouver).
3. No bracketed numbers remain after an APA conversion; no (Author, year) after a Vancouver one.
4. No hyphen in a page range, no "doi:" or dx.doi.org, no ALL CAPS titles.
5. Every number in the text matches the user's notes or draft.
6. After a revision: the old value appears nowhere, and every sentence still
   reads as one claim per citation.

## The list page

A reference list starts on a page of its own (§2.12), with the heading centred bold and hanging
indents on every entry, and only sources the notes actually carry may appear in it. When you
repair an existing document, move the list onto its own page rather than leaving it under the
body text.


## Check the list before handing it back

The pack ships the rules as a runnable check: <skill folder>/../_checks/academic_style.py. Run it
on the document before handing it back, with the rule id APA-REF-CITED, and fix what it names:

    python3 <skill folder>/../_checks/academic_style.py APA-REF-CITED report.docx

It fails when an entry is listed that the body never cites, and when the reference list does not
start on its own page. An entry with no source in the notes may not be listed at all.

A list the person asked for on its own (their sources, tidied into the style) is handed back as
the list alone: the heading References and the entries, nothing above them. Never write body text,
or a line telling them to write it, to give the entries something to cite; with no text above the
list the check reads its form and leaves citing to the paper it goes into. Give the file a title in
its properties (the heading will do) and a name that says what it is, such as `references.docx`.


## Take an uncited entry out of the list

A repair on a file that already exists needs the removal, not just a report. The pack ships it:

    python3 <skill folder>/scripts/repair_refs.py report.docx            # report, exit 2 when there are any
    python3 <skill folder>/scripts/repair_refs.py report.docx --remove   # take them out, then report

It runs the same rule as the check (`APA-REF-CITED`), so the file and the pack check cannot
disagree. Run it after the list is written.

## Repair through the builder

When a repair rewrites the reference list, build the document with the docx skill's APA builder rather than
hand editing the file:

    python3 <skill folder>/../docx/templates/apa-student-paper/build_apa.py spec.json report.docx

It refuses to write a file that lists an entry the body never cites, or an entry with no source
in the notes, so the rule is enforced by the tool rather than remembered.

## Say what passed, not more

Tell the person which checks the file passed and against which source and version. Never call the
file certified, compliant or approved, and give no legal, tax or accounting advice.
