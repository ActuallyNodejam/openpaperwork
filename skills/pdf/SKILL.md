---
name: pdf
description: "PDF files: create, read, merge, fill, OCR, edit. For an invoice, letter, quote or deck load that pack first."
version: 1.1.0
license: MIT
platforms: [linux, macos, windows]
metadata:
  domain: formats
  version: "1.1.0"
---

# PDF Skill

## First: is there a pack for this kind of document?

This skill handles the PDF file. It does not know what a kind of document must carry. If the ask is for one of these and that pack is installed, stop and load it first: the pack lays the file out and checks it.

- an invoice or a credit note: `e-invoice`
- a letter: `business-letter`
- a quotation, order confirmation, delivery note, pro forma or purchase order: `trade-documents`
- a business deck (a board update, a proposal, a sales or investor deck): `business-deck`

Whatever language the ask is in. Come back here only for a file none of them names, or to read or change an existing one.

For an existing HTML file in the desktop app (`NODEJAM_PRINT` is set), export
with the bundled `nodejam-print "input.html" "output.pdf"`. It uses the app’s
own Chromium. Keep the existing HTML and pictures; a separate browser install
is unnecessary. Outside the desktop, use the existing headless browser path.

Create PDFs from structured specs, build and fill AcroForm forms (with layout linting and visual overlays), extract text/tables/metadata, merge/split/rotate/watermark/stamp pages, export page images, manage metadata and attachments, and encrypt/decrypt — using pypdf, reportlab, and pdfplumber. Two absorbed capabilities live in references/ (read the matching file before those tasks):

- **Scanned/image-only PDFs and OCR** (render pages with scripts/pdf_page_image.py and read the images; marker-pdf via scripts/extract_marker.py for bulk OCR): `references/ocr-extraction.md`
- **Editing text inside an existing PDF via natural-language prompts** (nano-pdf CLI): `references/nano-pdf-editing.md`

## When to Use

- Generate a report or another multi-page document as PDF (an invoice, a letter, a quotation and a deck have their own packs, above).
- Build a fillable AcroForm (text/checkbox/radio/dropdown) from a JSON spec, linting the layout first.
- Pull text, tables (JSON/CSV), metadata, or form-field values out of a PDF.
- Merge, split, rotate, extract page subsets, watermark, stamp text/images at coordinates, bookmark, or compress PDFs.
- Export pages as PNGs for visual review or for OCR hand-off; set/clear document metadata; add/extract file attachments.
- Fill or flatten AcroForm forms; encrypt or decrypt with passwords.
- NOT for scanned/image-only PDFs (use `references/ocr-extraction.md`) and for pixel-perfect HTML-to-PDF rendering use `nodejam-print` in the desktop or a headless browser elsewhere.

## Prerequisites

The desktop already bundles these dependencies. Use its Python; no package
setup is required there.

- Python 3.10+ with `pypdf`, `reportlab`, `pdfplumber`, `pypdfium2`:
  `python -m pip install pypdf reportlab pdfplumber pypdfium2`
- Optional, for page rasterization (`pdf_page_image.py`, overlay rendering): `python -m pip install pypdfium2`, or poppler's `pdftoppm` on PATH. Scripts fall back pypdfium2 → pdftoppm and report `{"rendered": false, "missing": [...]}` (exit 0) when neither exists.
- Each helper script checks imports lazily and prints an install hint if a dependency is missing.

## How to Run

All helpers live in `scripts/` and are argparse CLIs — run them with the `bash` tool; every one supports `--help`. They read/write JSON strictly as UTF-8, print JSON results to stdout, and exit non-zero on failure.

```bash
python scripts/pdf_create.py spec.json -o out.pdf         # build PDF from JSON spec
python scripts/pdf_make_form.py formspec.json -o form.pdf # build fillable AcroForm from JSON spec
python scripts/pdf_form_layout.py formspec.json           # lint form layout BEFORE building
python scripts/pdf_form_layout.py formspec.json --render-overlay boxes.png [--pdf form.pdf]
python scripts/pdf_read.py doc.pdf --text                 # per-page text (JSON)
python scripts/pdf_read.py doc.pdf --tables --csv-dir t/  # tables to JSON + CSV files
python scripts/pdf_read.py doc.pdf --meta                 # metadata, page sizes, encrypted/scanned flags
python scripts/pdf_read.py form.pdf --fields              # form fields: name, type, value
python scripts/pdf_merge.py a.pdf b.pdf -o merged.pdf [--bookmarks]
python scripts/pdf_split.py doc.pdf --pages 1-3,7 -o part.pdf [--rotate 90]
python scripts/pdf_fill_form.py form.pdf --fields-json values.json -o filled.pdf [--flatten]
python scripts/pdf_secure.py doc.pdf --encrypt -o enc.pdf --user-password your-password
python scripts/pdf_secure.py enc.pdf --decrypt -o dec.pdf --password your-password
python scripts/pdf_watermark.py doc.pdf --stamp mark.pdf -o stamped.pdf [--under]
python scripts/pdf_stamp.py doc.pdf -o out.pdf --text "DRAFT" --x 150 --y 400 \
    --font-size 60 --rotation 45 --opacity 0.3 --color "#cc0000" [--pages 1-3]
python scripts/pdf_stamp.py doc.pdf -o out.pdf --image sig.png --x 400 --y 60 --width 120
python scripts/pdf_page_image.py doc.pdf --pages 1-3 --dpi 150 --out-dir imgs/
python scripts/pdf_meta.py doc.pdf --set-meta --title "T" --author "A" -o out.pdf
python scripts/pdf_meta.py doc.pdf --attach data.csv -o out.pdf
python scripts/pdf_meta.py doc.pdf --list-attachments | --extract-attachments dir/
```

## Quick Reference

| Task | Tool | Command / API |
|---|---|---|
| Create doc (headings, tables, images) | reportlab platypus | `pdf_create.py spec.json -o out.pdf` |
| Build fillable form | reportlab acroForm | `pdf_make_form.py formspec.json -o form.pdf` |
| Lint form layout / overlay image | pure python + PIL | `pdf_form_layout.py formspec.json [--render-overlay o.png]` |
| Per-page text | pdfplumber | `pdf_read.py f.pdf --text` |
| Tables → JSON/CSV | pdfplumber | `pdf_read.py f.pdf --tables` |
| Metadata / sizes / encrypted / scanned | pypdf + pdfplumber | `pdf_read.py f.pdf --meta` |
| Merge (+ outline) | pypdf | `pdf_merge.py a.pdf b.pdf -o m.pdf` |
| Split / extract / rotate | pypdf | `pdf_split.py f.pdf --pages 2-5 --rotate 90` |
| List / fill / flatten form | pypdf | `pdf_read.py --fields`, `pdf_fill_form.py` |
| Encrypt / decrypt (AES-256) | pypdf | `pdf_secure.py --encrypt/--decrypt` |
| Watermark / stamp PDF page | pypdf | `pdf_watermark.py f.pdf --stamp w.pdf` |
| Stamp text/image at coordinates | reportlab + pypdf | `pdf_stamp.py f.pdf --text "Sign here" --x 400 --y 60` |
| Pages → PNG (review / OCR hand-off) | pypdfium2 or pdftoppm | `pdf_page_image.py f.pdf --pages 1-3 --out-dir imgs/` |
| Set/clear metadata, attachments | pypdf | `pdf_meta.py --set-meta / --attach / --extract-attachments` |
| Compress content streams | pypdf | `pdf_split.py f.pdf --pages 1-N --compress` |

## Procedure

1. **Inspect first.** Run `pdf_read.py file.pdf --meta`. Check `encrypted` (if true, decrypt first with `pdf_secure.py --decrypt`) and `likely_scanned_pages`. If pages are image-only, export them with `pdf_page_image.py --pages <scanned> --dpi 300 --out-dir imgs/` and hand the PNGs to the `references/ocr-extraction.md` skill — do not report empty text as "no content".
2. **Create.** Write a JSON spec with `write` (elements: `heading`, `paragraph`, `table`, `image`, `pagebreak`; optional `title`/`author` metadata; page numbers are added automatically), then run `pdf_create.py`. Verify visually with `vision_analyze` on a rendered page image if layout matters.
3. **Extract.** `--text` gives a JSON list of per-page strings; `--tables` gives row arrays per page and can also emit CSV files. Read results with `read`; never eyeball a binary PDF directly.
4. **Manipulate.** `pdf_merge.py` concatenates and can add one bookmark per source file; `pdf_split.py` handles page ranges (1-based, e.g. `1-3,5,9-`), rotation in 90° steps, and `--compress`. Watermark by preparing a single-page stamp PDF (e.g. via `pdf_create.py`) and overlaying it with `pdf_watermark.py`; for one-liner stamps ("sign here", diagonal DRAFT, corner labels) use `pdf_stamp.py` with text or an image at explicit coordinates.
5. **Build forms.** Write one form-spec JSON (fields with `label_box`/`entry_box` in PDF points — see `references/forms.md`), lint it with `pdf_form_layout.py` and fix every reported problem, optionally review the `--render-overlay` PNG with `vision_analyze`, then build with `pdf_make_form.py` and confirm with `pdf_read.py --fields`.
6. **Fill forms.** List fields (`--fields`) to learn exact names and types, write a UTF-8 JSON of `{"FieldName": "value"}` with `write` (checkboxes accept `true`/`false`; radio/choice values must match the field's export options), then `pdf_fill_form.py`. Re-read with `--fields` to confirm values landed.
7. **Metadata & attachments.** `pdf_meta.py --set-meta` writes Title/Author/Subject/Keywords (DocInfo); `--clear-meta` drops them; `--attach`/`--list-attachments`/`--extract-attachments` round-trip embedded files.
8. **Secure.** Encrypt with distinct user/owner passwords and AES-256. To remove a password you know, `--decrypt` writes an unencrypted copy.
9. **Verify** (see below) before reporting success.

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

## Verify literal source wording

When the deliverable promises the source's own words, export its actual quote
and citation fields to a JSON list of `{"id":"row-1","pages":[1],"quote":"..."}`
and run `python scripts/pdf_verify_quotes.py source.pdf quotes.json` before
calling those words verified. The helper checks normalized text containment,
not complete coverage or semantic correctness. Investigate every `needs_review`:
use the exact source wording, label a paraphrase as your summary, or visually
verify an image-only quote and retain that evidence. Never fabricate a caption
for an unnamed picture merely to obtain a match. Quotes spanning pages may be
split into separately cited literal fragments. Keep the original PDF unchanged.

## Pitfalls

- **Scanned PDFs**: empty `extract_text()` plus page images means there is no text layer. Route to `references/ocr-extraction.md`; do not fabricate text.
- **Flattening limits**: `pdf_fill_form.py --flatten` uses pypdf's flatten support, which converts widget appearances into page content. It is reliable for plain text fields and checkboxes but can drop or misrender exotic widgets (rich text, custom appearance streams, some radio groups). Verify the flattened output visually with `vision_analyze`; for bulletproof flattening use an external renderer (e.g. Ghostscript or `pdftoppm`+reassembly) as a fallback.
- **NeedAppearances**: after filling, viewers only render values if appearance streams exist. The fill script sets the AcroForm `NeedAppearances` flag so conforming viewers regenerate them; some minimal viewers ignore it — flatten if display fidelity matters.
- **Non-Latin form values**: values are stored correctly (UTF-16), but the field's default font may lack glyphs, so a viewer can show blanks even though the data round-trips. Verify with `--fields`, not just visually.
- **Compression expectations**: `--compress` only deflates content streams. Typical savings are 0–20%; it does nothing for PDFs dominated by images or already-compressed streams. It is not a substitute for image downsampling (Ghostscript territory).
- **Permission flags don't enforce**: owner-password permission bits (no-print, no-copy) are polite requests that viewers may honor; any library (including pypdf) can read and strip them. Only the user password actually gates content via encryption. Never present permission flags as security.
- **Table extraction is heuristic**: pdfplumber detects tables from ruling lines/word alignment; borderless or merged-cell tables may need `table_settings` tuning or manual cleanup.
- **Page indexing**: helper CLIs take 1-based pages; pypdf APIs are 0-based. The scripts convert — don't double-convert.
- **Rotated stamp text extraction**: pdfplumber's line grouping scrambles rotated glyphs (a 45° "DRAFT" extracts as stray letters); verify rotated stamps with `pypdf`'s `extract_text()` or a rendered image instead.
- **Radio groups**: reportlab needs ≥2 `radio()` widgets per group, fills need the slashed export value (`"/red"`), and flatten fidelity is worst for radios — see `references/forms.md`.
- **Metadata scope**: `pdf_meta.py` writes the classic DocInfo dictionary only; embedded XMP metadata (if any) is left untouched and may show different values in some viewers.
- **PDF/A is out of scope**: pypdf/reportlab cannot produce or validate conformant PDF/A. If archival conformance is required, run Ghostscript via the `bash` tool (e.g. `gs -dPDFA=2 -dPDFACompatibilityPolicy=1 -sColorConversionStrategy=UseDeviceIndependentColor -sDEVICE=pdfwrite -o out.pdf in.pdf` with a suitable ICC profile) and validate with veraPDF — both are external installs, and the result still needs validation, not assumption.
- Rotation must be a multiple of 90; encrypted inputs must be decrypted before any other operation.

## Verification

- After create/merge/split: `pdf_read.py out.pdf --meta` — confirm `page_count`, and per-page `rotation` when you rotated.
- After extraction: check the JSON is non-empty and spot-check a known string or cell.
- Form design loop: `pdf_form_layout.py spec.json` must exit 0; then `--render-overlay boxes.png --pdf form.pdf` and review the PNG with `vision_analyze` (red = entry boxes with field names, blue = label boxes) asking about overlaps, misalignment, and labels detached from their fields. Iterate spec → lint → overlay until clean.
- After building a form: `pdf_read.py form.pdf --fields` lists every spec field with the right type and options.
- After form fill: `pdf_read.py filled.pdf --fields` and compare values (exact match, including non-ASCII).
- After stamping: re-extract text (pypdf for rotated stamps) or render the page with `pdf_page_image.py` and inspect with `vision_analyze`.
- After metadata/attachment edits: `pdf_read.py --meta` / `pdf_meta.py --list-attachments`, and re-extract an attachment to byte-compare.
- After encrypt: `--meta` shows `"encrypted": true` and opening without a password fails; after decrypt, text extraction matches the original.
- For anything visual (watermarks, flattened forms), render and inspect with `vision_analyze`.
