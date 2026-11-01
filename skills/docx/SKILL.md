---
name: docx
description: "Word .docx files: create, read, edit, fill a template. For an invoice, letter, minutes, quote, agreement or employment terms load that pack first."
version: 1.1.0
license: MIT
platforms: [linux, macos, windows]
proven: "2026-10-03"
metadata:
  domain: formats
  version: "1.1.0"
workflows:
  - id: "fill-template"
    arguments: "fill a template"
    icon: "file-text"
    menu: "Fyll i mall"
    menu_en: "Fill a template"
    gives: "Er egen Word-mall ifylld, med layouten kvar"
    gives_en: "Your own Word template filled in, its layout kept"
    takes: "Släpp mallen och det som ska in i den"
    takes_en: "Drop the template and what goes in it"
---

# Docx Skill

## First: is there a pack for this kind of document?

This skill handles the Word file. It does not know what a kind of document must carry. If the ask is for one of these and that pack is installed, stop and load it first: the pack lays the file out and checks it.

- an invoice or a credit note: `e-invoice`
- a letter: `business-letter`
- the minutes of a meeting: `meeting-minutes`
- a quotation, order confirmation, delivery note, pro forma or purchase order: `trade-documents`
- written terms of employment or an offer letter: `employment-statement`
- an NDA or another agreement, or a review of one: `contract-drafting`
- an annual report, a requirements specification, a research paper: `annual-accounts`, `requirements-spec`, `paper`

Whatever language the ask is in. Come back here only for a file none of them names, or to read or change an existing one.

Create, read, edit, and template Microsoft Word `.docx` files with
python-docx via small CLIs. It handles text, styles, lists, tables,
images, headers/footers, `{{token}}` templating, tracked changes
(list/accept/reject), comments (list/add/delete), TOC and page-number
fields, and package health checks. It does not render documents itself
(PDF needs LibreOffice — see Converting to PDF) or edit legacy `.doc`.

## Adapt a supplied checklist without adding policy

Keep the source requirements and their applicability thresholds word for word.
Blank tracking fields are useful, but do not add new approval conditions,
evidence requirements or rules about when a task may be marked complete unless
the source or user supplies them. Separate any requested suggestions from the
source checklist and label them as suggestions. Preserve the distinction between
not entered, not checked and failed; a blank field proves none of those states.

Choose the output for its intended use, not simply the input extension. A list
people will assign, filter and update usually suits a spreadsheet; a printable
form suits a document. Honor an explicit format. Keep owner, completion date
and comments as separate fields when providing progress tracking, so each can
be updated independently. Leave their values blank rather than assigning people
or deadlines. Reopen the result and compare every applicable source requirement.

## Fit and inspect the final document

Before creating a table, calculate the section's usable width from page width
minus left and right margins. Keep the total column widths within that width;
set the table grid and cell widths consistently. A landscape page still has
margins. Do not confuse centimetres, inches and twips. Keep headers readable,
repeat them on continued tables, and avoid splitting a requirement across pages
when the row fits on one page.

Run `scripts/docx_validate.py` on generated documents and inspect its issues,
including `table-width-overflow` warnings. The width check covers explicit
top-level tables with section dimensions; it does not simulate autofit, nested
tables or full pagination. Resolve unintended overflow before delivery.

For a generated document with tables or positioned content, render a temporary
PDF with an available Word-compatible renderer and inspect every page before
delivery. Check the right edge, clipped text, row breaks, headings separated
from their content and space for the requested tracking fields. Package health
and extracted text do not prove visual quality. If no renderer is available,
check explicit dimensions and disclose that visual layout remains unverified;
do not claim a visual check from XML inspection alone. Keep temporary renders
out of the user's final file list.

## Use source images at the delivered size

For a prominent image, prefer the original local source or cutout when it is
available. An image extracted from a workbook, preview or contact sheet may
be a small thumbnail, even when it depicts the right item. Compare the source
pixel dimensions with the size used on the page before enlarging it. Reuse a
thumbnail only at a size where it remains suitable; increasing its pixel
dimensions does not recover the source detail.

Keep the original aspect ratio and inspect the rendered page at a useful
reading size for pixelation, clipping and text/image balance. Use the same
adequate source in the editable file so a later export retains the quality.
If only a low-resolution reference exists, keep that limitation explicit;
do not invent product detail or substitute an unverified variant to conceal it.

## Check references between delivered files

When a document accompanies other outputs, check every reference to those
outputs against the final saved filenames after revisions or renaming. Read
body text, tables, headers, footers and any delivery note; replacing the title alone
does not update its references. Use portable relative links where supported.
Keep original source citations identifiable as sources, rather than making
an unavailable old output look like a file included in the delivery. Reopen
the final document to confirm the references match the files the reader gets.

## Grant proposals: Horizon Europe Part B

For a Horizon Europe research proposal (the technical description, Part B, of
the application form for RIA and IA actions), start from
`templates/horizon-europe-partb.spec.json`: copy it, replace the placeholder
lines and the participant rows, and build it with `docx_create.py`. Keep its
headings and their order; evaluators read by them.

The form's rules, version 5.1 of 22.01.2026:

- A4, every margin at least 15 mm.
- Body text at least 11 points, tables included. Times New Roman is the
  reference font. Line spacing at least single.
- The title, the list of participants and sections 1 to 3 together are at
  most 40 pages, or 45 for a lump-sum topic. Pages over the limit are not read.
- Sections: 1 Excellence (1.1 Objectives and ambition, 1.2 Methodology),
  2 Impact (2.1 pathways towards impact, 2.2 measures to maximise impact,
  2.3 Summary, optional), 3 Quality and efficiency of the implementation
  (3.1 Work plan and resources, 3.2 Capacity of participants and consortium).
- Remove section 2.3 when it is not used. Put only the applicant's own
  content under each heading; do not write new claims to fill a section.

## Every file

These hold for every document, whatever was asked.

- A new file is built with `scripts/docx_create.py`. It starts from
  `templates/standard.docx` (Arial) and draws tables in the house look: a bold
  header row with a rule under it, light rules between rows, no grid, numbers
  right-aligned. Never start from a bare `Document()`: its body text is
  Cambria and its tables a black grid. A script of your own opens
  `Document("<skills>/docx/templates/standard.docx")` and calls
  `house_table(table)` from `scripts/docx_create.py` on every table.
- Write in the language of the chat, the data too: in a Swedish chat the
  months are januari to december (juli, not July) and the file's
  `"properties": {"language": "sv-SE"}`.
- Run the pack check on the file. DOCX-FONT, DOCX-TABLE, DOCX-NUMBERS and
  DOCX-MONTHS fail the defaults above; fix and run it again.
- The file has a title. `docx_create.py` sets it from `"properties": {"title":
  ...}` or the first heading. After editing a file that has none, run
  `scripts/office_properties.py out.docx --title "..."`.
- Coloured text keeps a contrast of 4.5:1 against its background, or 3:1 at
  18 pt and above. Light grey on white fails.
- Every picture has alternative text.
- At most two font families. When a house style names one font, put
  `"font": "<name>"` in the spec: it names that font on every style, where the
  default file leaves headings and the title to the theme font.

## When to Use

- The user asks to generate a Word document (report, letter, contract).
- You need the text, outline, styles, or embedded images of a `.docx`.
- You must change an existing `.docx`: replace text, edit table cells,
  insert/delete paragraphs, apply styles, merge fragmented runs.
- You have a `.docx` template with `{{placeholders}}` to fill from data.
- The document has tracked changes to review, accept, or reject.
- You need to read reviewers' comments, or add/delete comments.
- A `.docx` won't open or behaves oddly and you need corruption triage.
- The document needs a table of contents or "Page X of Y" footers.
- Not for: `.doc` (legacy), `.odt`, or WYSIWYG layout work.

## Prerequisites

- Python 3.10+ with `python-docx` installed:
  `pip install python-docx` (import name is `docx`; lxml comes with it).
- Comments `add` uses the native API on python-docx >= 1.2 and an XML
  fallback on older versions — both are automatic.
- For image blocks: the image files must exist locally (PNG/JPEG).

## How to Run

All helpers live in `scripts/` next to this file. Run them with the
`bash` tool; each supports `--help` and prints JSON to stdout.

```bash
python scripts/docx_create.py spec.json out.docx
python scripts/docx_read.py out.docx --text
python scripts/docx_edit.py replace out.docx --find old --replace new
python scripts/docx_template.py tpl.docx values.json filled.docx
python scripts/docx_revisions.py list out.docx
python scripts/docx_comments.py list out.docx
python scripts/docx_validate.py out.docx
```

## Quick Reference

| Task | Command |
| --- | --- |
| Create from JSON spec | `docx_create.py spec.json out.docx` |
| Full text (body+tables+headers/footers) | `docx_read.py f.docx --text` |
| Heading outline + table shapes | `docx_read.py f.docx --structure` |
| Styles actually used | `docx_read.py f.docx --styles` |
| Extract embedded images | `docx_read.py f.docx --images outdir/` |
| Detect tracked changes/comments | `docx_read.py f.docx --revisions` |
| Find/replace (formatting kept) | `docx_edit.py replace f.docx --find A --replace B -o out.docx` |
| Set a table cell | `docx_edit.py set-cell f.docx --table 0 --row 1 --col 2 --text X` |
| Insert paragraph before index N | `docx_edit.py insert f.docx --index N --text X --style Normal` |
| Delete paragraph N | `docx_edit.py delete f.docx --index N` |
| Apply style to paragraph N | `docx_edit.py style f.docx --index N --style "Heading 1"` |
| Merge equal-format adjacent runs | `docx_edit.py normalize f.docx -o out.docx` |
| Insert TOC field before para N | `docx_edit.py toc f.docx --index N -o out.docx` |
| "Page X of Y" footer fields | `docx_edit.py page-numbers f.docx` |
| Fill `{{tokens}}` | `docx_template.py tpl.docx values.json out.docx --strict` |
| List revisions (id/author/date/text) | `docx_revisions.py list f.docx` |
| Accept / reject all revisions | `docx_revisions.py accept-all f.docx -o out.docx` (or `reject-all`) |
| Accept / reject one revision | `docx_revisions.py accept f.docx --id 3 -o out.docx` |
| List comments (+anchored text) | `docx_comments.py list f.docx` |
| Add comment anchored to text | `docx_comments.py add f.docx --target "phrase" --text "note" --author You` |
| Delete comment by id | `docx_comments.py delete f.docx --id 0` |
| Health-check the package | `docx_validate.py f.docx` (exit 1 on errors) |

## Procedure

1. **Create.** Write a JSON spec with `write`, then run
   `scripts/docx_create.py`. The spec supports: `page` (size + margins in
   mm), `header`/`footer` strings, `footer_page_numbers` (adds a
   "Page X of Y" field footer), `styles` (custom paragraph styles with
   font, size, bold/italic, hex `color`), and `blocks` — `heading`
   (level 1-9), `paragraph` (either `text` or a `runs` list where each run
   may set `bold`/`italic`/`underline`), `bullet_list`, `numbered_list`,
   `table` (`header` row rendered bold, `rows`, optional built-in table
   `style` such as `Table Grid`), `image` (`path`, optional `width_mm`),
   `toc` (Table of Contents field), and `page_break`. The full spec
   format is documented at the top of `scripts/docx_create.py`.
2. **Read.** Use `scripts/docx_read.py` with exactly one mode flag.
   `--text` returns body paragraphs, all table cell text, and
   header/footer text as JSON. `--structure` returns the heading outline
   plus paragraph/table/section counts. `--images DIR` copies every file
   under `word/media/` out of the package.
3. **Edit.** Use `scripts/docx_edit.py`. `replace` walks body, tables
   (nested included), headers and footers, and preserves run formatting;
   add `--body-only` to skip headers/footers. Pass `-o out.docx` to keep
   the original; omit it to edit in place. Paragraph indices for
   `insert`/`delete`/`style`/`toc` refer to `--structure`/`--text` body
   order. Run `normalize` first on documents that came out of heavy Word
   editing — it merges adjacent runs with identical formatting so later
   find-replace matches reliably.
4. **Review revisions.** `docx_revisions.py list` reports every `w:ins`
   and `w:del` (id, author, date, affected text) anywhere in body,
   tables, headers, or footers. `accept-all` / `reject-all` resolve them
   in bulk; `accept`/`reject --id N` handles a single revision. Accept
   keeps insertions and drops deleted text; reject does the reverse.
5. **Comments.** `docx_comments.py list` returns each comment's id,
   author, date, body text, and the document text it is anchored to.
   `add --target "some phrase"` anchors a new comment to the first
   occurrence of that phrase (runs are split as needed; formatting is
   preserved). `delete --id N` removes the comment and its markers
   without touching document text.
6. **Template.** Put `{{name}}`-style tokens in the document. Run
   `scripts/docx_template.py` with a JSON object of values. Use
   `--strict` to fail when tokens remain unfilled; the JSON output lists
   `filled` counts and `unfilled_tokens` either way.
7. **Verify** (always): re-read the output with `--text` or
   `--structure`, and run `docx_validate.py` on anything you produced
   via revision/comment surgery.

## Converting to PDF

No script needed. When LibreOffice is installed, convert headlessly:

```bash
soffice --headless --convert-to pdf --outdir outdir/ file.docx
```

Check availability first (`command -v soffice || command -v
libreoffice`). If neither exists, tell the user PDF conversion is
unavailable in this environment rather than improvising — python-docx
cannot render PDFs, and layout fidelity requires a real renderer.

## Pitfalls

- **Tokens split across runs.** Word often fragments text into several
  runs. The replace helpers collapse matched runs (replacement inherits
  the first run's formatting); running `docx_edit.py normalize` first
  reduces fragmentation for all later edits.
- **Revision coverage.** `docx_revisions.py` resolves run-level
  insertions and deletions (the overwhelming majority). Paragraph-mark
  and table-row revisions, format-change records, and moves are detected
  by `--revisions` but not auto-resolved — see
  `references/revisions-and-comments.md` and hand those to Word.
- **Comment threading.** Replies and "resolved" status live in
  `commentsExtended.xml`, which this skill ignores; comments it adds are
  plain top-level comments.
- **Field results are computed by Word.** `toc`, `page-numbers`, and the
  `toc`/`footer_page_numbers` spec options write *field codes*.
  Word/LibreOffice populates the actual entries and numbers when the
  file is opened (Word may prompt to update fields); python-docx never
  computes them, so placeholder text shows until then.
- **Validation is a health check, not schema validation.**
  `docx_validate.py` verifies the zip, required parts, relationship
  targets, image magic bytes, and referenced styles. It is NOT XSD
  validation — a file can pass and still contain XML Word dislikes.
- **Style names must exist.** Applying a style that isn't defined in the
  document raises `KeyError`. Built-ins like `Heading 1`, `List Bullet`,
  `List Number`, `Table Grid` exist in the default template; custom
  styles must be declared in the create spec first.
- **Numbered lists restart.** `List Number` relies on Word's default
  numbering; separate lists in one document may continue numbering
  instead of restarting. Warn users needing precise multi-list numbering.
- **Cell writes replace formatting.** `set-cell` uses `cell.text = ...`,
  which resets runs in that cell to plain formatting.
- **Encoding.** All JSON specs/values files are read as UTF-8 explicitly;
  never rely on locale defaults when writing your own glue code.
- **Don't unzip-and-sed the XML.** Edit through the scripts (or
  python-docx); raw text substitution in `document.xml` corrupts files
  easily. Use `edit`/`write` only for the JSON inputs, never on the
  `.docx` itself.

## Verification

- After create/edit/template, run `docx_read.py out.docx --text` and
  check the expected strings appear (and old strings are gone).
- After accept/reject, `docx_revisions.py list` should return `[]` (or
  only the ids you intentionally left); after comment surgery,
  `docx_comments.py list` should reflect the change and `--text` output
  must be unchanged.
- `docx_validate.py out.docx` exits 0 with `"ok": true` on a healthy
  package — run it after any revision/comment/field manipulation.
- For templates run with `--strict`, or check `unfilled_tokens == []`.
- Structure checks: `--structure` should show the expected heading
  outline and table shapes; `--styles` confirms custom styles applied.

## APA student paper

Build the file with `templates/apa-student-paper/build_apa.py`, which applies the format rules
the pack is graded on, so they do not depend on remembering them:

- the body opens with the paper title and there is **never** an Introduction heading;
- the reference list starts on a page of its own, always, with hanging indents;
- a reference may only be listed if the notes carried it, and every entry must be cited in the
  body. The builder refuses to write the file otherwise, rather than shipping an invented source;
- the ask is the person's own words: the skill saves the document under the name they asked for
  and hands back the file, without the request having to say so.

`python3 build_apa.py spec.json report.docx`, where the spec carries the title page fields, the
body as a list of headings and paragraphs, and the references.


## Check the list before handing it back

The pack ships the rules as a runnable check: standards/checks/academic_style.py. Run it
on the document before handing it back, with the rule id APA-REF-CITED, and fix what it names:

    python3 standards/checks/academic_style.py APA-REF-CITED report.docx

It fails when an entry is listed that the body never cites, and when the reference list does not
start on its own page. An entry with no source in the notes may not be listed at all.


## The file is the answer

Save the document before you write your reply, and save it again if the write fails. A run that
answers in prose without a file has not done the task: the person asked for a document, not a
description of one. After saving, one line saying what you made and where it is.

## The check is the finish line

Before you answer, run the pack check on what you produced:

    python3 <skill folder>/../_checks/packcheck.py docx <your output>

It prints one FAIL line per rule with the evidence. Fix what it names and run it again, at most
three times. The turn does not end on a fail: if it still fails after three tries, say plainly
which rules fail and what you tried, and leave the file in place. A clean run prints
"pack check clean".
