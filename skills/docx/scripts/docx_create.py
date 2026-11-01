#!/usr/bin/env python3
# MIT License. Part of the Hermes docx skill.
"""Create a .docx document from a JSON spec.

Usage: docx_create.py spec.json output.docx
Run with --help for the spec format summary.

Spec (JSON object):
{
  "page": {"width_mm": 210, "height_mm": 297,
           "margins_mm": {"top": 25, "bottom": 25, "left": 20, "right": 20}},
  "header": "text shown in page header",
  "footer": "text shown in page footer",
  "styles": [{"name": "MyStyle", "base": "Normal", "font": "Arial",
              "size_pt": 12, "bold": true, "color": "1F4E79"}],
  "blocks": [
    {"type": "heading", "text": "Title", "level": 1},
    {"type": "paragraph", "style": "MyStyle", "runs": [
        {"text": "plain "}, {"text": "bold", "bold": true},
        {"text": " italic", "italic": true},
        {"text": " under", "underline": true}]},
    {"type": "paragraph", "text": "shortcut: single plain run"},
    {"type": "bullet_list", "items": ["a", "b"]},
    {"type": "numbered_list", "items": ["one", "two"]},
    {"type": "table", "header": ["Col1", "Col2"],
     "rows": [["1", "2"]], "style": "Light Grid Accent 1",
     "header_bold": true},
    {"type": "image", "path": "pic.png", "width_mm": 60},
    {"type": "page_break"},
    {"type": "toc"}
  ]
}

`"font": "Arial"` names one font family on every style, headings and title
included.
Every file: `"properties": {"title": "...", "language": "en-GB"}` sets the file's
title and language; without it the title is the first heading. `"template":
"standard"` starts from templates/standard.docx, whose styles name one font
family outright instead of leaving headings to the theme. It is the default: a new
file starts from it unless the spec says `"template": "blank"` or names its own
.docx. A table without a `style` gets the house look (house_table): a bold
header row with a rule under it, light rules between rows, no vertical lines,
numbers right-aligned. A python-docx script of your own calls
`house_table(table)` from this file on each table.

Extras: `"footer_page_numbers": true` at the top level adds a
"Page X of Y" footer built from PAGE/NUMPAGES fields, and a `toc` block
inserts a Table of Contents field. Field results are computed by
Word/LibreOffice when the file is opened, not by python-docx.
"""
from __future__ import annotations

import argparse
import json
import re
import sys

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_BREAK
from docx.shared import Mm, Pt, RGBColor


def apply_page(doc, page: dict) -> None:
    section = doc.sections[0]
    if "width_mm" in page:
        section.page_width = Mm(page["width_mm"])
    if "height_mm" in page:
        section.page_height = Mm(page["height_mm"])
    m = page.get("margins_mm", {})
    for side in ("top", "bottom", "left", "right"):
        if side in m:
            setattr(section, f"{side}_margin", Mm(m[side]))


def add_styles(doc, styles: list) -> None:
    for s in styles:
        style = doc.styles.add_style(s["name"], WD_STYLE_TYPE.PARAGRAPH)
        if s.get("base"):
            style.base_style = doc.styles[s["base"]]
        font = style.font
        if s.get("font"):
            font.name = s["font"]
        if s.get("size_pt"):
            font.size = Pt(s["size_pt"])
        if s.get("bold") is not None:
            font.bold = s["bold"]
        if s.get("italic") is not None:
            font.italic = s["italic"]
        if s.get("color"):
            font.color.rgb = RGBColor.from_string(s["color"])


def add_runs(para, block: dict) -> None:
    runs = block.get("runs")
    if runs is None:
        runs = [{"text": block.get("text", "")}]
    for r in runs:
        run = para.add_run(r.get("text", ""))
        if r.get("bold"):
            run.bold = True
        if r.get("italic"):
            run.italic = True
        if r.get("underline"):
            run.underline = True


NUMBER = re.compile(r"^[\u2212\-+]?\s?(?:\d{1,3}(?:[ \u00a0\u202f.,']\d{3})+|\d+)(?:[.,]\d+)?\s?"
                    r"(?:%|kr|sek|eur|\u20ac|\$|\u00a3|tkr|mkr)?$", re.IGNORECASE)


def _rule(name, size, color):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    el = OxmlElement(f"w:{name}")
    el.set(qn("w:val"), "single" if size else "nil")
    if size:
        el.set(qn("w:sz"), str(size))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
    return el


def house_table(table, header: bool = True) -> None:
    """The house table (Mac sweep 2026-10-12): a header row in bold with a dark rule under it, light rules
    between rows, no vertical lines, numbers and their headings right-aligned, the header repeated on a new
    page. Replaces python-docx's Table Grid, a black line round every cell."""
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    tbl_pr = table._tbl.tblPr
    for old in tbl_pr.findall(qn("w:tblStyle")) + tbl_pr.findall(qn("w:tblBorders")):
        tbl_pr.remove(old)
    borders = OxmlElement("w:tblBorders")
    for name, size, color in (("top", 0, ""), ("left", 0, ""), ("bottom", 4, "BFBFBF"), ("right", 0, ""),
                              ("insideH", 4, "D9D9D9"), ("insideV", 0, "")):
        borders.append(_rule(name, size, color))
    tbl_pr.append(borders)
    rows = table.rows
    numeric = set()
    for col in range(len(table.columns)):
        values = [r.cells[col].text.strip() for r in rows[1 if header else 0:] if col < len(r.cells)]
        values = [v for v in values if v]
        if values and sum(bool(NUMBER.match(v)) for v in values) * 2 > len(values):
            numeric.add(col)
    for i, row in enumerate(rows):
        for col, cell in enumerate(row.cells):
            for para in cell.paragraphs:
                if col in numeric:
                    para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                para.paragraph_format.space_before = Pt(3)
                para.paragraph_format.space_after = Pt(3)
                if header and i == 0:
                    for run in para.runs:
                        run.bold = True
        if header and i == 0:
            tr_pr = row._tr.get_or_add_trPr()
            tr_pr.append(OxmlElement("w:tblHeader"))
            for cell in row.cells:
                tc_pr = cell._tc.get_or_add_tcPr()
                tc_borders = OxmlElement("w:tcBorders")
                tc_borders.append(_rule("bottom", 8, "404040"))
                tc_pr.append(tc_borders)


def add_block(doc, block: dict) -> None:
    btype = block["type"]
    if btype == "heading":
        doc.add_heading(block.get("text", ""), level=block.get("level", 1))
    elif btype == "paragraph":
        para = doc.add_paragraph(style=block.get("style"))
        add_runs(para, block)
    elif btype == "bullet_list":
        for item in block.get("items", []):
            doc.add_paragraph(item, style="List Bullet")
    elif btype == "numbered_list":
        for item in block.get("items", []):
            doc.add_paragraph(item, style="List Number")
    elif btype == "table":
        header = block.get("header", [])
        rows = block.get("rows", [])
        ncols = len(header) if header else (len(rows[0]) if rows else 1)
        table = doc.add_table(rows=0, cols=ncols)
        if block.get("style"):
            table.style = block["style"]
        if header:
            cells = table.add_row().cells
            for i, text in enumerate(header):
                cells[i].text = str(text)
                if block.get("header_bold", True):
                    for para in cells[i].paragraphs:
                        for run in para.runs:
                            run.bold = True
        for row in rows:
            cells = table.add_row().cells
            for i, text in enumerate(row):
                cells[i].text = str(text)
        if not block.get("style"):
            house_table(table, header=bool(header))
    elif btype == "image":
        width = Mm(block["width_mm"]) if block.get("width_mm") else None
        doc.add_picture(block["path"], width=width)
    elif btype == "page_break":
        doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    elif btype == "toc":
        from docx_edit import _add_field
        para = doc.add_paragraph()
        _add_field(para, r' TOC \o "1-3" \h \z \u ',
                   "Table of contents - open in Word/LibreOffice and "
                   "update fields to populate.")
    else:
        raise ValueError(f"unknown block type: {btype}")


def plain_bullets(doc) -> None:
    """Swap the template's Symbol/Wingdings bullet glyphs (U+F0B7 and kin) for a plain
    bullet in the document's own font, so bullets render without Office fonts."""
    from docx.oxml.ns import qn
    try:
        numbering = doc.part.numbering_part.element
    except (KeyError, NotImplementedError):
        return
    for lvl in numbering.iter(qn("w:lvl")):
        fmt = lvl.find(qn("w:numFmt"))
        if fmt is None or fmt.get(qn("w:val")) != "bullet":
            continue
        text = lvl.find(qn("w:lvlText"))
        if text is not None:
            val = text.get(qn("w:val")) or ""
            text.set(qn("w:val"), "\u25e6" if val in ("o", "\uf06f") else
                     "\u25aa" if val == "\uf0a7" else "\u2022")
        rpr = lvl.find(qn("w:rPr"))
        if rpr is not None:
            for fonts in rpr.findall(qn("w:rFonts")):
                rpr.remove(fonts)


def one_font(doc, name: str) -> None:
    """Name one font family on every style and the document default, replacing theme references.

    The default file leaves headings and the title to the theme font, so a document meant to use
    one family ends up with two unless every style names it."""
    from docx.oxml.ns import qn
    for fonts in doc.styles.element.iter(qn("w:rFonts")):
        for attr in list(fonts.attrib):
            del fonts.attrib[attr]
        for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            fonts.set(qn(attr), name)
    for style in doc.styles:
        if style.name in ("Normal", "Title", "Subtitle") or style.name.startswith("Heading"):
            style.font.name = name


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Create a .docx from a JSON spec.",
        epilog="See the module docstring (top of this file) for the spec format.")
    ap.add_argument("spec", help="path to JSON spec file")
    ap.add_argument("output", help="path of .docx to write")
    args = ap.parse_args()

    with open(args.spec, encoding="utf-8") as f:
        spec = json.load(f)

    template = spec.get("template", "standard")
    if template == "blank":
        template = None
    if template == "standard":
        import os
        template = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates", "standard.docx")
    doc = Document(template) if template else Document()
    if spec.get("font"):
        one_font(doc, spec["font"])
    if spec.get("page"):
        apply_page(doc, spec["page"])
    if spec.get("styles"):
        add_styles(doc, spec["styles"])
    if spec.get("header"):
        doc.sections[0].header.paragraphs[0].text = spec["header"]
    if spec.get("footer"):
        doc.sections[0].footer.paragraphs[0].text = spec["footer"]
    for block in spec.get("blocks", []):
        add_block(doc, block)
    props = spec.get("properties") or {}
    from docx_edit import add_page_numbers, doc_language, set_default_language
    body = "\n".join(p.text for p in doc.paragraphs)
    if props.get("language"):
        doc.core_properties.language = props["language"]
    lang = doc_language(doc, body)
    if lang != "en":
        # A Swedish file opens as Swedish: no red marks on every word, and its footer reads "Sida 1 av 3".
        set_default_language(doc, props.get("language") or lang)
    if spec.get("footer_page_numbers"):
        add_page_numbers(doc, body)
    title = props.get("title") or next(
        (b.get("text") for b in spec.get("blocks", []) if b.get("type") == "heading" and b.get("text")), None)
    if title:
        doc.core_properties.title = title
    if props.get("language"):
        doc.core_properties.language = props["language"]
    plain_bullets(doc)
    doc.save(args.output)
    print(json.dumps({"ok": True, "output": args.output,
                      "blocks": len(spec.get("blocks", []))}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
