---
name: xlsx
description: "Excel .xlsx workbooks and CSVs: create, read, edit. For an invoice or a quote, order or delivery note load that pack first, even as Excel."
version: 1.1.0
license: MIT
platforms: [linux, macos, windows]
proven: "2026-10-03"
metadata:
  domain: formats
  version: "1.1.0"
---

# Xlsx Skill

## First: is there a pack for this kind of document?

This skill handles the workbook. It does not know what a kind of document must carry. If the ask is for one of these and that pack is installed, stop and load it first: the pack lays the file out and checks it.

- an invoice or a credit note: `e-invoice`
- a quotation, order confirmation, delivery note, pro forma or purchase order: `trade-documents`

Whatever language the ask is in. Come back here only for a file none of them names, or to read or change an existing one.

Work with Excel .xlsx workbooks using Python and openpyxl: build styled
multi-sheet workbooks with formulas and charts, inspect or dump existing
files, edit cells and structure, and convert to/from CSV. All helper
scripts are argparse CLIs that print JSON and use explicit UTF-8 I/O.

## Use project-specific guidance before drafting

## When to Use

- Creating .xlsx reports: multiple sheets, number formats, styling,
  merged cells, freeze panes, autofilter, conditional formatting,
  charts, data-validation dropdowns, native Excel tables, defined
  names, hyperlinks, cell notes, sheet protection.
- Reading a workbook: sheet inventory, dumping data as JSON or CSV,
  listing formulas vs cached values, notes, defined names, tables.
- Editing existing files: set cells, append rows, insert/delete
  rows/columns (reference-aware via `xlsx_restructure.py`),
  copy/rename sheets, tables, names, notes, protection.
- Recalculating formulas headlessly via LibreOffice
  (`xlsx_recalc.py`).
- CSV interop with type inference and non-UTF-8 encodings.
- Not for the legacy .xls binary format (use LibreOffice to convert
  first: `soffice --headless --convert-to xlsx old.xls`).

## Resolve the decision the workbook supports

When the workbook must compare costs with an approved budget, ask for the
missing ceiling or comparison basis before completing that comparison. Do not
infer a budget from spending or insert an unexplained target. A defined cost
overview for a budget meeting does not by itself request a budget comparison:
provide the requested totals, missing-price flags and notes without blocking
on a ceiling. Ask only when the missing decision changes the requested result.
Keep known costs distinct from a complete forecast while any prices are unknown.

For consolidated reports, inventory every source sheet and identify which
numbers are period activity, cumulative snapshots or a documented subset.
Open and closed counts from a photo appendix cannot be presented as the status
of every recorded issue. Reconcile only matching populations and periods; keep
unknown totals blank and state the missing source needed to complete them.
Never manufacture a total to satisfy a requested report heading.
For every requested indicator, provide its supported period summary or a precise
reason it cannot be aggregated. Attendance marks can support a count of recorded
attendance events; do not call that unique people or complete participation.
Read the meaning of each header even when column positions change across months.
Keep raw evidence and distinguish confirmed counts from unknown coverage.
When some periods are absent, show the supported recorded subtotal with its
coverage alongside the unknown complete-period total; do not discard recorded
activity merely because full coverage is unavailable. Keep that distinction
for each requested indicator and grouping (for example project), not only a
grand total. A person-level register does not replace a requested project
summary. Where a report asks for a prose summary, include that paragraph;
a detailed table can support it without replacing it.
Preserve missingness through formulas: a direct reference to an empty cell can
produce zero. Guard missing inputs explicitly, including end-of-period snapshot
references, and test a blank-input case after recalculation.

## Reconcile every grouped summary

Check each area, supplier or other group's known cost, row count and missing-value
count against the source rows. The groups together must reconcile to the overall
counts and costs. A correct grand total does not prove the group breakdown.
Keep rows whose grouping value is absent in an explicit unknown group, and retain
the original value separately. Use an explicit derived grouping label
for absent values, including empty cells and empty strings, rather than relying
on a blank conditional-count criterion. Recalculate and compare the resulting
counts with the source; formula presence alone does not prove correct grouping.

## Check measurement types before totals

Monthly counts, quantities and prices may be stored as text in a source
workbook. Excel SUM ignores text cells in a referenced range: 4, 4 and "4"
produce 8, not 12. In the generated measurement columns, deliberately convert
unambiguous numeric text to real numbers before aggregating. Preserve the
original files and source wording for traceability. Do not convert identifiers,
room numbers, dates or free text, and never turn missing values into zero.
Confirm the source locale before interpreting ambiguous decimal/thousands
separators; put unresolved values in the notes and leave the numeric input empty.

Before delivery, run `xlsx_read.py output.xlsx --check-numbers --sheet Data
--range C4:E29` on each declared numeric input range. It is read-only, reports
text and other non-numeric inputs, and exits nonzero for issues. Resolve or
explicitly account for every issue. Formula inputs require separate result
verification; this check does not calculate them. Independently reconcile each
requested total with its complete source inputs and periods, then compare it
with the saved workbook's actual formula result. A syntactically valid SUM or
a successful recalculation does not prove that all intended inputs contributed.

## Separate editable inputs from calculations

An operator changes numbers, not formulas. Keep source calculations as live
formulas connected to plainly labelled numeric input cells. If a source price
is a calculation such as a base price times a discount, expose the original
base price as an editable input and keep the discounted price as a formula
that references it. Carry the source discount rate and calculation unchanged;
do not invent a rate. Putting the original hard-coded expression in the same
cell the person must overwrite does not preserve their editing workflow.
All row costs and summaries must follow those inputs. Before delivery, change
one numeric input, verify the dependent discounted price and totals and that
the formulas remain intact, then restore the original input and save.

## Make the next action usable

When the person asks to compare this with the next quote or report, deliver
actual labelled empty input rows or columns for that next entry in the same
workbook. Keep existing source values and calculations, and connect the new
numeric inputs to the comparison and totals. A note telling them to copy a
sheet later does not deliver a ready comparison. Leave unknown suppliers,
prices and dates empty; never invent another quote. Check the saved native
workbook against each requested part and any later answers before delivery.
Do not add financial modules the person did not request.

## Every sheet prints one page wide, checked by rendering

Do this for any workbook with two or more sheets, whether or not a PDF or
printout was requested. The workbook may be printed or rendered by whoever
opens it, and supporting sheets (payments, rates, removed rows, unmatched
items, notes) are the ones left at defaults.

1. In the spec, give every sheet a `print` block: `paper` (A4 unless the
   source locale implies otherwise), `orientation` (landscape when a sheet has
   more than about five columns or any long text column), `fit_width: true`, and
   `repeat_rows` for the header row. Also set `column_widths` for every
   column, wide enough for the longest value, and wrap long note text rather
   than letting it run past the last column.
2. Before delivery, render: `soffice --headless --convert-to pdf out.xlsx
   --outdir /tmp/render`, count pages (`pdfinfo /tmp/render/out.pdf | grep
   Pages`) and read the per-page text. Every sheet must be one page wide: no
   page may hold only columns split off another page. A short sheet should
   fill one page; a long one may run down several. If columns spill, widen,
   wrap, switch to landscape or fix that sheet's print extent, and render again. Do not delete requested columns or rows to
   save pages.
3. Repeat steps 1-2 for every saved revision. A workbook rebuilt from a new
   spec must carry the `print` blocks again, and an added row or column can
   add a page. Report the final page count only if you rendered the file
   you are delivering.

## Every file

These hold for every workbook, whatever was asked.

- The workbook has a title. `xlsx_create.py` sets it from `"properties":
  {"title": ...}`, else from the first sheet name. After editing a workbook
  that has none, run `scripts/office_properties.py out.xlsx --title "..."`.
- Every sheet has a name that says what is on it, never `Sheet1`.
- Nothing is cut. A column is at least as wide as its longest text when the
  next cell is filled, and wide enough to show its numbers in their format.
  Wrapped text needs a row tall enough for its lines.
- Every formula has a saved result and none shows an error value. Recalculate
  before delivering.
- Coloured text keeps a contrast of 4.5:1 against the cell fill.
- No merged cells. A title runs on over the empty cells beside it instead.
- Nothing hidden: no hidden rows, columns or sheets, and no blank sheet.
- Every column of a table has one heading, used once.
- A column of numbers holds numbers, never a number typed as text or a dash,
  "..", "NA" in place of one; leave the cell blank and say why in a note.
- No links to other workbooks, and no OFFSET or INDIRECT.
- No number typed into a formula. A rate, a price or any other assumption sits
  in its own labelled cell and the formula refers to it; only units of time
  and scale (12 months, 24 hours, 100 per cent, 1000) may be written in.

The last five come from the UK Government Analysis Function's "Releasing
statistics in spreadsheets" (Open Government Licence v3.0) and the FAST
Standard 02c (FAST Standard Organisation, CC BY 4.0). The pack check reads them:
`python3 <skill folder>/../_checks/packcheck.py xlsx <your output>`.

## Preserve pictures when revising

After inserting images, a library save may renumber media parts. Do not
restore old ZIP media files by filename over the new package: a new picture
can reuse an old name and become a different product. If retaining original
parts, give added media unique names and update the drawing relationships
that reference them before combining packages. Keep content types valid.
Preservation means the picture bytes at each original sheet/anchor still
match, not merely that the original bytes exist somewhere in the ZIP.
Reopen the saved file and compare each added anchored image with its intended
source bytes or thumbnail. Check picture identity visually; a successful load,
correct image count and unchanged formulas do not prove the images are right.

## Prerequisites

- Python 3.10+ with `openpyxl` (`pip install openpyxl`). No other
  third-party packages are needed; everything else is stdlib.
- Optional: LibreOffice (`soffice`) for headless recalculation or
  format conversion.

## How to Run

Run the helper scripts with the `bash` tool from this skill's
`scripts/` directory (every script supports `--help`):

```bash
python scripts/xlsx_create.py spec.json report.xlsx   # build from JSON spec
python scripts/xlsx_read.py report.xlsx --sheets      # inventory
python scripts/xlsx_read.py report.xlsx --json --sheet Data
python scripts/xlsx_read.py report.xlsx --formulas
python scripts/xlsx_read.py report.xlsx --check-numbers --sheet Data --range C4:E29
python scripts/xlsx_edit.py report.xlsx --sheet Data --set B2=42 --recalc
python scripts/xlsx_restructure.py report.xlsx --sheet Data --insert-rows 3:2
python scripts/xlsx_recalc.py report.xlsx
python scripts/csv_to_xlsx.py data.csv out.xlsx --encoding utf-8
python scripts/xlsx_to_csv.py report.xlsx out.csv --sheet Data
```

Author the JSON spec with `write`, inspect script JSON output with
`read` or directly from stdout.

## Quick Reference

| Task | Command |
|---|---|
| Create workbook from spec | `xlsx_create.py spec.json out.xlsx` |
| Sheet names + dimensions | `xlsx_read.py f.xlsx --sheets` |
| Dump sheet as JSON | `xlsx_read.py f.xlsx --json --sheet S` |
| Dump sheet as CSV | `xlsx_read.py f.xlsx --csv --out d.csv` |
| List formulas + cached values | `xlsx_read.py f.xlsx --formulas` |
| Check numeric inputs (read-only) | `xlsx_read.py f.xlsx --check-numbers --sheet Data --range C4:E29` |
| Set a cell / formula | `xlsx_edit.py f.xlsx --set "A1==SUM(B:B)"` |
| Append a row | `xlsx_edit.py f.xlsx --append '[1,"x",true]'` |
| Insert 2 rows, refs NOT shifted | `xlsx_edit.py f.xlsx --insert-rows 3:2` |
| Insert 2 rows, refs shifted | `xlsx_restructure.py f.xlsx --insert-rows 3:2` |
| Delete a column, refs shifted | `xlsx_restructure.py f.xlsx --delete-cols B` |
| Create a native table | `xlsx_edit.py f.xlsx --add-table Sales:A1:C9` |
| Append inside a table | `--table-append 'Sales=["West",5]'` |
| List tables | `xlsx_edit.py f.xlsx --list-tables` |
| Defined names | `--define-name "Rates='Data'!$B$2:$B$9"` / `--delete-name Rates` / `xlsx_read.py f.xlsx --names` |
| Hyperlink | `--hyperlink "A1=https://example.com|Docs"` |
| Cell note | `--note "B2=Check this|Reviewer"`; read via `xlsx_read.py f.xlsx --notes` |
| Protect sheet (see Pitfalls) | `--protect your-password --unlock B2:B9` |
| Recalculate via LibreOffice | `xlsx_recalc.py f.xlsx` |
| Copy / rename sheet | `--copy-sheet Src:New --rename-sheet Old:New` |
| Force recalc on open | `xlsx_edit.py f.xlsx --recalc` |
| CSV -> styled xlsx | `csv_to_xlsx.py in.csv out.xlsx` |
| xlsx -> CSV | `xlsx_to_csv.py f.xlsx out.csv --encoding utf-8` |

## Procedure

1. **Create**: write a JSON spec (schema documented in
   `xlsx_create.py --help` and its docstring). Each sheet supports
   `rows` (scalars or styled cell objects), sparse `cells` overrides,
   `column_widths`, `row_heights`, `merges`, `freeze_panes`,
   `autofilter`, `conditional_formats` (cell_is rules and color
   scales), `charts` (bar/line/pie from cell ranges),
   `validations` (list dropdowns), `tables` (native Excel tables with
   a style name), and `protection`. Workbook-level `defined_names`
   maps names to refs. Cell objects also take `hyperlink` and `note`.
   Typed values: JSON numbers/bools
   pass through; dates use `{"value": "2026-01-31", "type": "date"}`.
   Number formats are Excel format strings: currency `"$#,##0.00"`,
   percent `"0.0%"`, date `"yyyy-mm-dd"`.
2. **Formulas**: set with `"formula": "SUM(B2:B9)"` in the spec or
   `--set "C1==SUM(A:A)"` in the editor. When writing formulas, add
   `"full_calc_on_load": true` (spec) or `--recalc` (editor); this sets
   the workbook's `fullCalcOnLoad` flag so Excel/LibreOffice recompute
   everything on open. openpyxl itself NEVER evaluates formulas.
3. **Read**: `--sheets` for inventory (names, dimensions, merged
   ranges, chart count, tables, protection, defined names),
   `--json`/`--csv` for data, `--formulas` to
   pair each formula string with its cached result, `--notes` for
   cell comments, `--names` for defined names. Cached results
   exist only if the file was last saved by a real spreadsheet app;
   files fresh from openpyxl return `null` there. To materialize
   results headlessly run `xlsx_recalc.py file.xlsx` (uses
   LibreOffice; prints `{"recalculated": false, ...}` and exits 0
   when `soffice` is absent), then reload with `--data-only`. If recalculation produces formula errors,
   the helper returns nonzero with sheet/cell details and leaves the input and
   destination unchanged. Repair those errors before claiming valid totals;
   `recalculated: true` alone is not a successful result.
4. **Edit**: `xlsx_edit.py` applies renames/copies first, then
   structural row/column changes, then `--set`/`--append`. It edits in
   place unless `--out` is given — copy the file first if you need the
   original.
5. **Restructure**: for insert/delete on sheets that have formulas,
   merges, tables, or filters, use `xlsx_restructure.py` instead of
   `xlsx_edit.py`. It rewrites formula references on ALL sheets
   (absolute `$` refs, ranges, cross-sheet refs), shifts merges,
   autofilter, freeze panes, validation and conditional-format
   ranges, table refs, defined names, and row/column dimensions, then
   prints a JSON report including a `not_shifted` list. Rules and
   limits: `references/restructuring.md`.
6. **CSV interop**: `csv_to_xlsx.py` infers int/float/bool/ISO-date
   per cell and styles the header row; `xlsx_to_csv.py` writes ISO
   dates and blank strings for empty cells. Both default to UTF-8 and
   accept `--encoding` (e.g. `utf-8-sig` for Excel-friendly BOM,
   `cp1252` for legacy Windows exports).

## Verify saved CSV files

Create CSV with Python's standard `csv.writer` and `newline=""`, rather than
assembling escaped row separators in a string. After saving, parse the actual
file again before delivery. Compare exact headers, field counts and expected
data-record count against the source; quoted commas and quoted multiline
cells are valid CSV and must remain intact.

Run `csv_verify.py purchases.csv --headers '["date","item","quantity","unit_price","currency"]' --rows 3`
with the columns and row count from the current request/source, not these
example values. The helper is read-only and exits nonzero on mismatched
headers, ragged records or missing rows. Fix the generated file and rerun
before saying it is ready. Verify source values, blank unknowns and unchanged
inputs separately; a shape pass does not establish factual accuracy. Never
globally replace literal backslash-n sequences in an existing CSV: they may
be legitimate cell content.

## Deliver readable views with compact sources

Separate the recipient's working tables from raw extraction or audit data.
Keep the requested rows, editable inputs and formulas complete in the native
workbook. Use a compact source table keyed to the relevant row or group, with
file/page or URL, retrieval date when applicable and a short factual note.
Keep necessary raw metadata in a supporting file rather than repeating long
JSON records throughout the reader's workbook. Preserve original evidence.

For a requested PDF, select the sheets and columns that answer its purpose.
Set and check the print layout for every intended printed sheet, including
source notes; the main sheet settings do not keep another sheet’s labels and
details together.
Do not blindly export every raw-data tab or shrink a wide workbook until its
text is unreadable. Use suitable page orientation, repeated headers and page
breaks, or a labelled summary view whose totals and missing-value counts
reconcile to the native rows. Retain access to requested detail. Inspect the
saved PDF at normal reading size and fix clipping, tiny text and blank pages
before delivery; a successful conversion proves none of those qualities.
For each populated cover or supporting sheet included in the render, explicitly
set paper size, orientation, fit-to-width and the intended print extent. Give
wrapped rows enough height after final text edits, and keep text readable rather
than forcing the whole sheet onto one page.
`xlsx_create.py` sheet specs take a `print` key (paper, orientation,
fit_width, repeat_rows, area) that sets this in the saved file.

After renaming outputs, check file references in sheets and accompanying notes
against the actual delivered filenames. Preserve source citations separately
from links to newly generated files, and use portable relative links where
supported. A reference to an old filename is not a working handoff.

## Converting to PDF

LibreOffice converts headlessly (also works for CSV export of a single
sheet):

```bash
soffice --headless --convert-to pdf report.xlsx --outdir out/
soffice --headless --convert-to csv report.xlsx --outdir out/  # 1st sheet only
```

Only the first sheet lands in a CSV; for other sheets use
`xlsx_to_csv.py --sheet NAME`. If `soffice` is missing, install
LibreOffice or hand the file to the user unconverted.

## Pitfalls

- **openpyxl does not calculate.** Formula results are available only
  via `load_workbook(path, data_only=True)` and only when the file was
  previously saved by Excel/LibreOffice. Otherwise you get `None`.
- **Read `"preserved"` in the JSON of `xlsx_edit.py` and
  `xlsx_restructure.py`.** `true`: every part the edit did not touch
  (charts, pictures, sparklines, pivots) was kept byte for byte, and
  row/column moves rewrote formulas, names, tables, chart ranges and
  anchors. `false` with `preserve_refused`: the edit could not be saved
  safely that way and ran on the stock path, which may drop what
  openpyxl does not model and whose `xlsx_edit.py` insert/delete does
  not shift references. Then name what may be lost in the hand-back,
  use `xlsx_restructure.py` for moves, and read its `not_shifted` list
  and `references/restructuring.md`.
- **Sheet protection is NOT security.** `--protect` sets the standard
  xlsx sheet-protection hash: it signals "don't edit this" to
  well-behaved apps and nothing more. Anyone can strip it by editing
  the zip's XML or unchecking it in LibreOffice. Never rely on it for
  confidentiality or integrity; it does not encrypt anything.
- **`data_only=True` then save** silently discards all formulas
  (cached values replace them). Never save a workbook loaded that way
  unless that is the goal.
- **Charts and pictures survive an edit only when `"preserved": true`.**
  On the stock path openpyxl rewrites charts and drops sparklines and
  newer conditional formats; check the saved file before handing it back.
- **CSV locale traps**: always pass explicit encodings (the scripts
  already do) and remember European CSVs often use `;` delimiters and
  decimal commas — use `--delimiter ';'` and expect strings like
  `"12,5"` to stay strings.
- **Dates are datetimes**: Excel stores dates as serial numbers;
  openpyxl returns `datetime`/`date` objects. Dumps here emit ISO
  strings.
- Sheet names are capped at 31 chars and reject `[ ] : * ? / \`.

## Verification

- After creating: `xlsx_read.py out.xlsx --sheets` and confirm sheet
  names, dimensions, merged ranges, and chart counts match intent.
- Dump data with `--json` and compare against the source values.
- After edits: re-dump the touched range; if formulas were written,
  confirm `--formulas` lists them and that `--recalc` was applied.
- After `xlsx_restructure.py`: read its JSON report, then re-run
  `--formulas` and `--sheets` to confirm references and ranges landed
  where expected.
- Before delivering any multi-sheet workbook: render to PDF and confirm every
  sheet is one page wide (see "Every sheet prints one page wide").
  Recalculation and a formula check do not establish this.
- For a full visual check, open in LibreOffice:
  `soffice --headless --convert-to pdf out.xlsx` and inspect the PDF.
