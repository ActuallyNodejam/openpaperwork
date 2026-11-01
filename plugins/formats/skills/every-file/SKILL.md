---
name: every-file
description: The floor every Word, Excel or PowerPoint file must pass before it is delivered, whatever the task. Use whenever you create or edit a .docx, .xlsx or .pptx.
license: Apache-2.0
metadata:
  domain: formats
  version: "0.1.0"
---

# Every file

These hold for every Office file you deliver, whatever was asked. Build the
file with python-docx, openpyxl or python-pptx as usual, then meet this list.

## Any file

- The file has a title in its properties. Set it when you build the file, or
  afterwards with `python3 scripts/office_properties.py FILE --title "..."`.
- At most two font families in the whole file, counting the theme fonts that
  headings and titles fall back to. When a house style names one font, set it
  on every style and run.
- Coloured text keeps a contrast of 4.5:1 against its background, or 3:1 at
  18 pt and above. Light grey on white fails. Dark text on a dark fill fails.
- Every picture and chart has alternative text.

## Documents

- The document declares a language. Set one with
  `scripts/office_properties.py FILE --language en-GB` when it has none.

## Workbooks

- Every sheet has a name that says what is on it, never `Sheet1`.
- Nothing is cut. A column is at least as wide as its longest text when the
  next cell is filled, and wide enough to show its numbers in their format.
  Wrapped text needs a row tall enough for its lines.
- Every formula has a saved result and none shows an error value. openpyxl
  writes formulas without results, so recalculate before delivering: convert
  the workbook with LibreOffice
  (`soffice --headless --convert-to xlsx --outdir out FILE`) and deliver the
  converted file.

## Decks

- Every slide has its title in the layout's title placeholder.
- Text fits its box. A line holds about (box width) / (0.55 x font size)
  characters and each line is 1.2 x the font size tall. Shorten the text or
  enlarge the box. Do not go below 18 pt.
- No text sits behind a picture or a filled shape. Give pictures their own
  area beside the text.

## Check before you deliver

Run the check on the finished file, with its absolute path:

```bash
python3 scripts/check_file.py /absolute/path/to/file
```

It prints each rule with pass or fail and what it found, and exits 1 when a
rule fails. Fix what fails and run it again until every rule passes. When the
`openpaperwork-checks` server is connected, its `check_file` tool runs the
same check.

Run the check again after every later edit of the file, a revision included.
