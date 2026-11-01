---
name: powerpoint
description: "Read or change an existing .pptx, or fill a company's own .pptx template. To make a new business deck load business-deck."
version: 1.1.0
license: MIT
platforms: [linux, macos, windows]
proven: "2026-10-03"
metadata:
  domain: formats
  version: "1.1.0"
---

# Powerpoint Skill

## First: is there a pack for this kind of document?

This skill handles the .pptx file. It does not know what a kind of document must carry. If the ask is for one of these and that pack is installed, stop and load it first: the pack lays the file out and checks it.

- a business deck (a board update, a proposal, a sales or investor deck): `business-deck`

Whatever language the ask is in. Come back here only for a file none of them names, or to read or change an existing one.

Create, inspect, and edit PowerPoint (.pptx) presentations using the
python-pptx library. Five helper scripts cover deck creation from a JSON
spec, structured read-back, in-place edits, template-driven brand decks,
and slide rendering — all offline, no PowerPoint installation required.

## When to Use

- The user asks for slides from a company's own .pptx template, or a quick deck no pack names (any business deck is `business-deck`, above: it hands back a PDF, and the editable .pptx when asked).
- You need to extract text, notes, tables, chart data, or images from a
  .pptx someone shared.
- You need to update an existing deck: replace text, refresh or patch
  chart data, swap a logo, duplicate/remove/reorder slides, set
  backgrounds, footers, hyperlinks, or speaker notes.
- You must produce an on-brand deck from a company .pptx template.
- Do NOT use this for .ppt (legacy binary) files — convert them first with
  `soffice --convert-to pptx old.ppt` if LibreOffice is available.

## Build from a brand kit

When the person gives a brand kit (fonts, a palette, limits, a footer), or a
kit file such as `kit.json`, build the deck with `pptx_from_kit.py`. The kit
owns the look, so you write only the words and the chart data.

```bash
python scripts/pptx_from_kit.py kit.json slides.json out.pptx
```

`slides.json` is `{"properties": {"title": ...}, "slides": [...]}`. Each
slide has a `role` (`title`, `content`, `chart` or `picture`), a `title`, and
`bullets`, a `subtitle`, a `chart` with `categories`, `series` and `alt`, or a
`picture` with `path` and `alt`. Run the script with `--help` for the full
shapes.

- The script sets every font, colour, size and the footer from the kit, puts
  the title in the title placeholder, gives charts alternative text and
  palette colours, and names the deck. Do not restyle its output by hand.
- Put screenshots and photos in a `picture` slide. The script keeps the
  picture in its own area at its true proportions, beside the text. Never add
  a picture to the built file with your own code: it lands on top of the text.
- Body text is one size on every slide, set by the fullest slide. If it comes
  out small, shorten the longest slide and build again.
- Nothing decorative is drawn: no rule under the title, no shadow, no shape
  that carries no information, and titles in the regular weight. A kit may
  name a `logo` file, and ask for `"style": {"title_rule": true}` or
  `"bold_titles": true` when the company's own look has them.
- It stops with a list of slides to shorten when a slide is over the kit's
  word or paragraph limit or its text cannot fit at the minimum size. Rewrite
  those slides shorter, keeping every figure and date, and run it again.
- When the kit changes (a new accent colour, a removed slide), change the kit
  file or the slide list and rebuild. Do not patch colours in the old file.

## Every file

These hold for every deck, whatever was asked.

- The deck has a title, and every slide has one in its title placeholder.
  `pptx_create.py` sets the deck title from `"properties": {"title": ...}` or
  the first slide. After editing a deck that has none, run
  `scripts/office_properties.py out.pptx --title "..."`.
- Charts and pictures carry alternative text. A chart takes it from `"alt"`,
  else from its title, so give every chart one of the two.
- Text fits its box. A line holds about (box width) / (0.55 x font size)
  characters and each line is 1.2 x the font size tall. Shorten the text or
  enlarge the box; do not go below 18 pt.
- Coloured text keeps a contrast of 4.5:1 against the fill behind it, or 3:1
  at 18 pt and above. Dark text on a dark fill disappears when projected.
- At most two font families.

## Prerequisites

- Python 3.10+ with `python-pptx` installed
  (`pip install python-pptx`).
- Optional: LibreOffice (`soffice`) plus poppler (`pdftoppm` or
  `pdftocairo`) for rendering slides to PNGs and for PDF export.
  `pptx_render.py` detects both with `shutil.which` and degrades
  gracefully (reports `{"rendered": false, "missing": [...]}`, exit 0)
  when absent — all create/read/edit operations work without them.
- Check availability via the `bash` tool:
  `python -c "import pptx; print(pptx.__version__)"` and `which soffice pdftoppm`.

## How to Run

All scripts live in `scripts/`, take `--help`, print JSON to stdout, and
exit non-zero on failure. Run them with the `bash` tool:

```bash
python scripts/pptx_create.py deck.json out.pptx
python scripts/pptx_read.py deck.pptx --outline      # full JSON outline
python scripts/pptx_read.py deck.pptx --notes        # speaker notes
python scripts/pptx_read.py deck.pptx --images ./img # export pictures
python scripts/pptx_edit.py deck.pptx --replace-text "Old Corp" "New Corp"
python scripts/pptx_edit.py deck.pptx --chart-data update.json
python scripts/pptx_edit.py deck.pptx --duplicate-slide 2
python scripts/pptx_edit.py deck.pptx --remove-slide 3 --move-slide 2 0
python scripts/pptx_from_template.py brand.pptx out.pptx --values vals.json
python scripts/pptx_render.py deck.pptx --outdir ./render  # slide PNGs
```

Author JSON specs with `write`; inspect script output and generated
JSON with `read`.

## Quick Reference

| Task | Command |
|---|---|
| New deck from spec | `pptx_create.py spec.json out.pptx` |
| 16:9 vs 4:3 | `"slide_size": "16:9"` or `"4:3"` in the spec |
| Outline as JSON | `pptx_read.py deck.pptx --outline` |
| Export images | `pptx_read.py deck.pptx --images DIR` |
| Replace text | `pptx_edit.py deck.pptx --replace-text OLD NEW` |
| Replace chart data | `pptx_edit.py deck.pptx --chart-data spec.json` |
| Patch one series | same flag, spec with `"ops"` (see below) |
| Swap picture | `pptx_edit.py deck.pptx --swap-image N NAME new.png` |
| Duplicate slide | `pptx_edit.py deck.pptx --duplicate-slide N` |
| Remove slide | `pptx_edit.py deck.pptx --remove-slide N` |
| Reorder slide | `pptx_edit.py deck.pptx --move-slide FROM TO` |
| Slide background | `pptx_edit.py deck.pptx --set-background N RRGGBB` |
| Hyperlink runs | `pptx_edit.py deck.pptx --hyperlink N TEXT URL` |
| Slide number on | `pptx_edit.py deck.pptx --enable-slide-number N` |
| Footer text | `pptx_edit.py deck.pptx --set-footer N TEXT` |
| Set notes | `pptx_edit.py deck.pptx --set-notes N TEXT` |
| Append notes | `pptx_edit.py deck.pptx --append-notes N TEXT` |
| Fill template | `pptx_from_template.py tpl.pptx out.pptx --values v.json` |
| Build from a brand kit | `pptx_from_kit.py kit.json slides.json out.pptx` |
| Render slide PNGs | `pptx_render.py deck.pptx --outdir DIR` |

## Procedure

### 1. Create a deck

Write a JSON spec (see `pptx_create.py --help` for the full format), then
run `pptx_create.py`. Per slide you can set: `layout` (title,
title_content, section, two_content, title_only, blank), `title`,
`subtitle`, `bullets` (strings, or dicts with `level` 0-4, `size` pt,
`bold`, `italic`, `font`, `color` hex, `link` URL for a hyperlink),
`background` (solid hex), `footer` (text; enables the layout's footer
placeholder), `slide_number` (true; enables the layout's slide-number
placeholder), `images` (path + left/top/width/height in inches), `tables`
(`rows` as list-of-lists), `shapes` (rectangle, rounded_rectangle, oval,
diamond, right_arrow, chevron, with `fill` hex + optional `text`),
`charts` (bar, bar_h, line, pie with `categories` + `series`), and
`notes` (speaker notes).

### 2. Read a deck

`pptx_read.py deck.pptx --outline` returns slide size, layout inventory,
and per slide: layout name, all shape texts, table cells, image inventory
(filename/ext/bytes), chart categories/series/values, and speaker notes.
Use `--images DIR` to dump embedded pictures to files, then
`vision_analyze` on any exported image if you need to see its content.

### 3. Edit a deck

`pptx_edit.py` combines operations in one pass; use `--output` to keep the
original. Text replacement scans slide shapes, table cells, and notes.
Image swap retargets the picture's relationship id so position and size
are preserved. Slide removal drops the relationship and the `<p:sldId>`
entry; reorder moves the `<p:sldId>` element within `<p:sldIdLst>`
(python-pptx has no public API for either — the script does the XML-level
work). `--duplicate-slide N` appends an independent deep copy of slide N:
shape XML plus image/media/hyperlink relationships are cloned and rIds
remapped, so editing the copy never touches the original. Chart slides
are refused (see Pitfalls). `--set-notes`/`--append-notes` edit speaker
notes; `--set-background`, `--hyperlink`, `--enable-slide-number`, and
`--set-footer` handle deck polish.

Chart updates take a JSON spec via `--chart-data`. Full replace:
`{"slide": 0, "chart": 0, "categories": [...], "series": {...}}`. For
surgical edits, pass `"ops"` instead — a list of
`{"op": "update_series", "name": ..., "values": [...]}`,
`add_series`, `remove_series`, `rename_category` (`from`/`to` or
`index`), and `set_title`. python-pptx can only swap a chart's entire
dataset (`replace_data`), so ops are implemented as read-existing →
modify → replace; the per-part UX is a wrapper, and any chart data not
expressible as categories + numeric series will be normalized by the
round-trip.

### 4. Build from a template

`pptx_from_template.py` opens a brand .pptx, replaces every
`{{token}}` from a values JSON across slides/tables/notes, and can append
new slides that use the template's own layouts (by layout name or index)
so they inherit the master's fonts and colors. Tip: to start from a
template with zero slides, delete existing ones afterward with
`pptx_edit.py --remove-slide`.

### 5. Visual verification

`pptx_render.py deck.pptx --outdir ./render` converts the deck to PDF
with `soffice --headless` and splits it into one PNG per slide with
`pdftoppm` (or `pdftocairo`). Output JSON lists the PNG paths — review
each with `vision_analyze`. When either tool is missing the script exits
0 with `{"rendered": false, "missing": [...]}` and guidance; fall back to
the JSON outline from `pptx_read.py`, which verifies content and
structure, just not visuals.

## Converting to PDF

If LibreOffice is installed, export the finished deck to PDF directly:

```bash
soffice --headless --convert-to pdf --outdir ./out deck.pptx
```

The output lands at `./out/deck.pdf`. Fonts not installed on the host are
substituted, so render-verify (Procedure step 5) before shipping the PDF.
There is no offline pure-Python .pptx→PDF path; if `soffice` is absent,
say so rather than approximating.

## Pitfalls

- **Run splitting**: PowerPoint fragments paragraph text into runs at
  spell-check and edit boundaries. `--replace-text` first merges adjacent
  runs whose formatting is identical, so matches split across such runs
  are replaced with formatting fully preserved. Only when a match spans
  *genuinely differently-formatted* runs is the paragraph rewritten with
  the first run's formatting — verify those slides after replacement.
- **Chart slides duplicate with their own data**: each chart embeds a
  separate XLSX workbook part, and `--duplicate-slide` gives the copy its
  own, so editing one chart leaves the other alone. A chart slide it
  cannot copy safely (OLE objects, SmartArt, comments) is refused with
  nothing changed; rebuild that slide on a new one instead.
  External-hyperlink and image/media rels are carried over; layout and
  notes rels are recreated fresh.
- **Chart ops are a wrapper**: python-pptx replaces the whole dataset;
  `"ops"` round-trips existing plot data through `replace_data`, and
  changing chart *type* is not possible.
- **Reordering is XML-level**: python-pptx has no supported reorder API.
  `--move-slide` manipulates `<p:sldIdLst>` directly; safe for ordinary
  decks but re-read the deck afterward to confirm.
- **Copying slides between decks is unsupported** — duplication works
  only within one deck, where layouts and masters are shared.
- Footer/slide-number enablement copies the placeholder from the slide's
  layout; on layouts without those placeholders, `--set-footer` fails
  with a clear message (add a textbox instead).
- Hyperlinks apply to whole runs; `--hyperlink` links every run
  containing the given text on that slide.
- The default python-pptx template is 4:3; the create script sets 16:9
  unless the spec says otherwise. Custom templates keep their own size.
- Layout indexes vary by template. For brand templates, list layout names
  first: `pptx_read.py template.pptx --outline` (`layouts_available`).
- `slide.shapes.title` is None on blank layouts — the create script
  handles this, but remember it when writing ad-hoc python-pptx code.
- Always pass `encoding="utf-8"` when writing spec files; tokens like
  `{{city}}` may be filled with non-ASCII values.

## Verification

1. After any create/edit, run `pptx_read.py OUT.pptx --outline` and check
   slide count, texts, tables, notes, and chart values match intent.
2. `--images DIR` then file-size check confirms pictures embedded.
3. Render every slide with `pptx_render.py deck.pptx --outdir ./render`
   and review each PNG with `vision_analyze` — this catches overlapping
   shapes, truncated text, and color problems the outline cannot. If the
   render tools are missing, the script says so; rely on the outline.
4. The bundled test suite is the full contract:
   `python -m pytest tests/ -q` (requires python-pptx + pytest).
