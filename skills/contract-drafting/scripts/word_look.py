"""The look the contract pack's Word files share: A4, Arial, black on white, quiet tables.

Used by agreement_create.py and review_create.py. Needs python-docx.
"""
import datetime as dt
import re

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor

FONT = "Arial"
GREY = RGBColor(0x59, 0x59, 0x59)
RULE = "BFBFBF"
SHADE = "E8E8E8"          # a Variable: the word points at the Cover Page
TOKENS = re.compile(r"(\*\*|\{\{[^}]+\}\})")


# An agreement often takes effect when the last party signs; that is a date in words, not a calendar date.
LAST_SIGNATURE = ("last signature", "date of last signature", "the date of the last signature", "on signature",
                  "when the last party signs", "date of the last signature below")


def long_date(iso):
    if str(iso).strip().lower().rstrip(".") in LAST_SIGNATURE:
        return "the date of the last signature below"
    d = dt.date.fromisoformat(str(iso))
    return "%d %s %d" % (d.day, d.strftime("%B"), d.year)


def new_document(title, language="en-GB", subject=""):
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Mm(210), Mm(297)
    sec.left_margin = sec.right_margin = Mm(25)
    sec.top_margin, sec.bottom_margin = Mm(22), Mm(20)
    sec.footer_distance = Mm(10)
    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(10)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    pf = normal.paragraph_format
    pf.space_after = Pt(6)
    pf.line_spacing = 1.15
    for name, size in (("Title", 20), ("Heading 1", 14), ("Heading 2", 11), ("Heading 3", 10)):
        st = doc.styles[name]
        st.font.name = FONT
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.italic = False
        st.font.color.rgb = RGBColor(0, 0, 0)
        rpr = st.element.get_or_add_rPr()
        fonts = rpr.find(qn("w:rFonts"))
        if fonts is None:
            fonts = OxmlElement("w:rFonts")
            rpr.insert(0, fonts)
        for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            fonts.set(qn(attr), FONT)
        for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
            if fonts.get(qn(attr)) is not None:
                del fonts.attrib[qn(attr)]
        st.paragraph_format.space_before = Pt(14 if name != "Title" else 0)
        st.paragraph_format.space_after = Pt(6)
        st.paragraph_format.keep_with_next = True
    title_style = doc.styles["Title"]
    title_style.paragraph_format.space_after = Pt(4)
    # The Title style draws a blue rule under it in python-docx's template: take it off.
    ppr = title_style.element.find(qn("w:pPr"))
    if ppr is not None:
        for bdr in ppr.findall(qn("w:pBdr")):
            ppr.remove(bdr)
    doc.core_properties.title = title
    doc.core_properties.language = language
    if subject:
        doc.core_properties.subject = subject
    footer(doc, title)
    return doc


def field(paragraph, code):
    run = paragraph.add_run()
    for kind, text in (("begin", None), (None, code), ("separate", None), (None, "1"), ("end", None)):
        if kind:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
            run._r.append(el)
        elif text == code:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = " %s " % code
            run._r.append(el)
        else:
            el = OxmlElement("w:t")
            el.text = text
            run._r.append(el)
    return run


def footer(doc, title):
    doc.styles["Footer"].font.size = Pt(8)
    doc.styles["Footer"].font.color.rgb = GREY
    p = doc.sections[0].footer.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run(title + "    Page ")
    r.font.size = Pt(8)
    r.font.color.rgb = GREY
    f = field(p, "PAGE")
    f.font.size = Pt(8)
    f.font.color.rgb = GREY
    r = p.add_run(" of ")
    r.font.size = Pt(8)
    r.font.color.rgb = GREY
    f = field(p, "NUMPAGES")
    f.font.size = Pt(8)
    f.font.color.rgb = GREY


def shade(run, fill=SHADE):
    rpr = run._r.get_or_add_rPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    rpr.append(shd)


def rich(paragraph, text, bold=False, size=None, color=None, italic=False):
    """Write text with **bold** and {{Variable}} markup into a paragraph."""
    on = bold
    for part in TOKENS.split(text):
        if not part:
            continue
        if part == "**":
            on = not on
            continue
        variable = part.startswith("{{") and part.endswith("}}")
        run = paragraph.add_run(part[2:-2] if variable else part)
        run.bold = True if on else None
        run.italic = True if italic else None
        if size:
            run.font.size = Pt(size)
        if color is not None:
            run.font.color.rgb = color
        if variable:
            shade(run)
    return paragraph


def para(doc_or_cell, text="", bold=False, size=None, color=None, italic=False, left=0, hanging=0,
         after=None, before=None, keep=False, style=None):
    p = doc_or_cell.add_paragraph(style=style) if style else doc_or_cell.add_paragraph()
    pf = p.paragraph_format
    if left or hanging:
        pf.left_indent = Mm(left)
        pf.first_line_indent = Mm(-hanging) if hanging else None
    if after is not None or not style:
        pf.space_after = Pt(6 if after is None else after)
    if before is not None or not style:
        pf.space_before = Pt(before or 0)
    if keep:
        pf.keep_with_next = True
    if text:
        rich(p, text, bold=bold, size=size, color=color, italic=italic)
    return p


def cell_text(cell, text, bold=False, size=None, color=None, italic=False, after=0):
    """Fill a cell: its first paragraph, then one more per line."""
    lines = text if isinstance(text, list) else [text]
    first = cell.paragraphs[0]
    for i, line in enumerate(lines):
        p = first if i == 0 else cell.add_paragraph()
        p.paragraph_format.space_after = Pt(after if i == len(lines) - 1 else 2)
        rich(p, str(line), bold=bold, size=size, color=color, italic=italic)
    return cell


def borders(table, inside=True, color=RULE):
    tbl = table._tbl
    pr = tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement("w:%s" % edge)
        visible = edge in ("top", "bottom", "insideH") and (inside or edge != "insideH")
        el.set(qn("w:val"), "single" if visible else "nil")
        if visible:
            el.set(qn("w:sz"), "4")
            el.set(qn("w:space"), "0")
            el.set(qn("w:color"), color)
        b.append(el)
    for old in pr.findall(qn("w:tblBorders")):
        pr.remove(old)
    pr.append(b)
    margins = OxmlElement("w:tblCellMar")
    for edge, width in (("top", 60), ("bottom", 60), ("left", 80), ("right", 80)):
        el = OxmlElement("w:%s" % edge)
        el.set(qn("w:w"), str(width))
        el.set(qn("w:type"), "dxa")
        margins.append(el)
    pr.append(margins)


def table(doc, rows, widths, header=None, shade_header=True, size=9.5):
    """A quiet table: hairlines between rows, a grey header when there is one, rows kept whole."""
    t = doc.add_table(rows=0, cols=len(widths))
    t.alignment = WD_TABLE_ALIGNMENT.LEFT
    t.autofit = False
    borders(t)
    all_rows = ([header] if header else []) + rows
    for i, row in enumerate(all_rows):
        cells = t.add_row().cells
        tr = t.rows[-1]._tr
        trpr = tr.get_or_add_trPr()
        cant = OxmlElement("w:cantSplit")
        trpr.append(cant)
        if header and i == 0:
            th = OxmlElement("w:tblHeader")
            trpr.append(th)
        for j, value in enumerate(row):
            cells[j].width = Mm(widths[j])
            spec = value if isinstance(value, dict) else {"text": value}
            cell_text(cells[j], spec.get("text", ""), bold=spec.get("bold", header is not None and i == 0),
                      size=spec.get("size", size), color=spec.get("color"), italic=spec.get("italic", False))
            if spec.get("help"):
                hp = cells[j].add_paragraph()
                hp.paragraph_format.space_after = Pt(0)
                rich(hp, spec["help"], size=8, color=GREY)
            if header and i == 0 and shade_header:
                tcpr = cells[j]._tc.get_or_add_tcPr()
                shd = OxmlElement("w:shd")
                shd.set(qn("w:val"), "clear")
                shd.set(qn("w:color"), "auto")
                shd.set(qn("w:fill"), "F2F2F2")
                tcpr.append(shd)
            if spec.get("height"):
                trh = OxmlElement("w:trHeight")
                trh.set(qn("w:val"), str(int(spec["height"] * 56.7)))
                trh.set(qn("w:hRule"), "atLeast")
                trpr.append(trh)
    for j, w in enumerate(widths):
        t.columns[j].width = Mm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def page_break(doc):
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
