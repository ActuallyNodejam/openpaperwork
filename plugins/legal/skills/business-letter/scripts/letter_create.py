#!/usr/bin/env python3
"""Write a business letter as Word or PDF from a JSON spec: on DIN 5008 Form B, or on the page and
envelope window of a Norwegian, Danish, Finnish, US, UK, Canadian, Australian, Belgian, Dutch, Austrian,
Irish, Spanish, Italian or Polish sender (window_letter.py).

Usage: letter_create.py spec.json OUTPUT.docx|OUTPUT.pdf

Spec (templates/letter.spec.json is a whole one):
{
  "language": "en",   # the recipient's language; leave out to use the sender's country
  "date": "2026-10-15",
  "sender": {"name": "...", "street": "...", "postcode": "...", "city": "...", "country": "SE",
             "email": "...", "phone": "...", "vat_id": "...",
             "registered_office": "...", "register": "...", "register_number": "...", "managing_directors": ["..."],
             "further": ["A particular the sender's letters carry that has no field here, one line each"]},
  "recipient": {"name": "...", "attention": "...", "street": "...", "postcode": "...", "city": "...", "country": "..."},
  "references": [{"label": "Your letter of", "value": "2026-10-02"}, {"label": "Our reference", "value": "KL-114"}],
  "contact": {"name": "...", "phone": "...", "email": "..."},
  "subject": "...",
  "salutation": "Dear Ms Berg,",
  "body": ["First paragraph.", "Second paragraph."],
  "closing": "Kind regards",
  "signatory": {"name": "...", "role": "..."},
  "enclosures": ["..."]
}

Where each part comes from:
- The page: DIN 5008:2020 Form B (skills/_shared/letter.py), the recipient in the window address
  field, written the way the recipient's post office reads it (letter.postal_lines, as every other
  letter and invoice), the references, contact and date in the information block, which ends on the
  text's right edge as an invoice's does, the text on one 25 mm edge.
- The parts of the letter: subject line without a label, salutation, body, closing, signatory and
  enclosures, in the order DIN 5008 sets out for a business letter.
- Dates: Unicode CLDR for the letter's language. Language: the recipient's when named, else the
  sender's country. Words for English, German, Swedish and Danish.
- Company details in the footer: Directive (EU) 2017/1132 Art. 26, GmbHG 35a for a GmbH,
  aktiebolagslagen 28 kap. 5 §. When a company's data lacks them the summary says so.
Every key the builder reads is in spec.fields.json beside SKILL.md. A key that is not there, or a value of
another shape (the body as one string, not a list of paragraphs), stops the build with the key's name
(skills/_shared/spec_guard.py): nothing given is left off the page.
Prints a JSON summary. Needs python-docx for Word; the PDF prints through Chromium.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
sys.path.insert(0, str(HERE))
import letter  # noqa: E402
import company  # noqa: E402
import spec_guard  # noqa: E402

FONT = "Arial"
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
WORDS = {
    "en-GB": {"date": "Date", "contact": "Contact", "phone": "Phone", "email": "Email", "enclosures": "Enclosures",
              "vat_id": "VAT ID", "yours": "Your reference", "ours": "Our reference"},
    "de-DE": {"date": "Datum", "contact": "Ansprechpartner", "phone": "Telefon", "email": "E-Mail", "enclosures": "Anlagen",
              "vat_id": "USt-IdNr.", "yours": "Ihr Zeichen", "ours": "Unser Zeichen"},
    "sv-SE": {"date": "Datum", "contact": "Kontaktperson", "phone": "Telefon", "email": "E-post", "enclosures": "Bilagor",
              "vat_id": "Momsreg.nr", "yours": "Er referens", "ours": "Vår referens"},
    "da-DK": {"date": "Dato", "contact": "Kontaktperson", "phone": "Telefon", "email": "E-mail", "enclosures": "Bilag",
              "vat_id": "Momsnr.", "yours": "Deres ref.", "ours": "Vores ref."},
}
REQUIRED = ("date", "sender", "recipient", "subject", "salutation", "body", "closing", "signatory")


class Letter:
    def __init__(self, spec):
        missing = [k for k in REQUIRED if not spec.get(k)]
        if missing:
            raise ValueError("the spec needs %s" % ", ".join(missing))
        self.spec = spec
        # letter.py speaks of a seller and a buyer; for a letter they are the sender and the recipient.
        self.locale, self.why = letter.language(dict(spec, seller=spec["sender"], buyer=spec["recipient"]))
        self.w = WORDS[self.locale]

    def date(self, value):
        return letter.date(value, self.locale) if ISO.match(str(value)) else str(value)

    def address(self):
        # The one rule for every letter and invoice: the address as the recipient's post office reads it,
        # the country in capitals on the last line when the letter goes abroad (UPU RL 123.3.3).
        return letter.postal_lines(self.spec["recipient"], self.spec["sender"].get("country"))

    def info_rows(self):
        s, w = self.spec, self.w
        rows = [(x.get("label") or w.get(x.get("kind"), ""), self.date(x["value"])) for x in s.get("references", [])]
        c = s.get("contact") or {}
        rows += [(w["contact"], c.get("name")), (w["phone"], c.get("phone")), (w["email"], c.get("email"))]
        rows.append((w["date"], self.date(s["date"])))
        return [(k, v) for k, v in rows if v]

    def return_line(self):
        s = self.spec["sender"]
        return " · ".join(x for x in (s["name"], s.get("street"), letter.town_line(s)) if x)

    def footer(self):
        # The first column is the company's own address, the one its invoice and its trade document print.
        s = self.spec["sender"]
        who = letter.own_address(s, (self.spec.get("recipient") or {}).get("country"))
        tax = (["%s %s" % (self.w["vat_id"], s["vat_id"])] if s.get("vat_id") else []) + letter.company_lines(s, self.locale)
        tax += letter.further_lines(s)
        reach = [s.get("email"), s.get("phone"), s.get("web")]
        return [[x for x in col if x] for col in (who, tax, reach)]

    def sign(self):
        g = self.spec["signatory"]
        return [g["name"]] + ([g["role"]] if g.get("role") else [])


def write_pdf(spec, out):
    lt = Letter(spec)
    esc = lambda s: str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    body = ["<h1>%s</h1>" % esc(spec["subject"]), "<p>%s</p>" % esc(spec["salutation"])]
    body += ['<p class="note">%s</p>' % esc(p) for p in spec["body"]]
    # The closing, the room to sign, the name and the enclosures stay on one page.
    end = ['<p class="note">%s</p>' % esc(spec["closing"]),
           '<p class="sign">%s</p>' % "<br>".join(esc(x) for x in lt.sign())]
    if spec.get("enclosures"):
        end.append('<p class="note"><b>%s</b><br>%s</p>' % (esc(lt.w["enclosures"]), "<br>".join(esc(x) for x in spec["enclosures"])))
    body.append('<div class="end">%s</div>' % "".join(end))
    html = letter.sheet_html(lt.locale, spec["subject"], "nodejam-letter-builder", spec["sender"]["name"], lt.return_line(),
                             "<br>".join(esc(x).replace("  ", "&nbsp; ") for x in lt.address()), lt.info_rows(),
                             "".join(body), lt.footer(), keep_tokens=True)
    # The information block ends on the text's right edge, as an invoice's does.
    html = html.replace("</style>", letter.info_css() + "</style>", 1)
    page = Path(out).with_suffix(".html")
    page.write_text(html)
    return letter.print_pdf(page, out)


def write_docx(spec, out):
    from docx import Document
    from docx.enum.table import WD_ROW_HEIGHT_RULE, WD_CELL_VERTICAL_ALIGNMENT
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Mm, Pt, RGBColor
    lt = Letter(spec)
    g = letter.GEOMETRY
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Mm(210), Mm(297)
    # DIN 5008 Form B: the letterhead takes the top 45 mm, the text runs from 25 mm to 20 mm short of the edge.
    sec.left_margin, sec.right_margin = Mm(g["left"]), Mm(g["right"])
    sec.top_margin, sec.bottom_margin = Mm(g["field_y"]), Mm(30)
    sec.header_distance, sec.footer_distance = Mm(g["head_top"]), Mm(8)
    for style in doc.styles:
        if style.type == 1 and style.font is not None:
            style.font.name = FONT
            rpr = style.element.get_or_add_rPr()
            fonts = rpr.find(qn("w:rFonts"))
            if fonts is None:
                fonts = OxmlElement("w:rFonts")
                rpr.append(fonts)
            for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
                fonts.set(qn(attr), FONT)
    doc.styles["Normal"].font.size = Pt(11)
    doc.styles["Normal"].paragraph_format.space_after = Pt(0)
    doc.core_properties.title = spec["subject"]
    doc.core_properties.language = lt.locale
    doc.core_properties.author = spec["signatory"]["name"]

    def run(p, text, bold=False, size=None, grey=False):
        r = p.add_run(text)
        r.bold = bold
        if size:
            r.font.size = Pt(size)
        if grey:
            r.font.color.rgb = RGBColor(0x6B, 0x62, 0x59)
        return r

    def no_borders(table):
        pr = table._tbl.tblPr
        borders = OxmlElement("w:tblBorders")
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
            e = OxmlElement("w:%s" % edge)
            e.set(qn("w:val"), "nil")
            borders.append(e)
        pr.append(borders)
        mar = OxmlElement("w:tblCellMar")
        for edge in ("left", "right"):
            e = OxmlElement("w:%s" % edge)
            e.set(qn("w:w"), "0")
            e.set(qn("w:type"), "dxa")
            mar.append(e)
        pr.append(mar)
        lay = OxmlElement("w:tblLayout")
        lay.set(qn("w:type"), "fixed")
        pr.append(lay)

    def para(text="", before=0, after=0):
        p = doc.add_paragraph()
        p.paragraph_format.space_before, p.paragraph_format.space_after = Mm(before), Mm(after)
        if text:
            run(p, text)
        return p

    run(sec.header.paragraphs[0], spec["sender"]["name"], bold=True, size=15)
    # Address field (80 mm of text from the 25 mm edge) and the information block from 125 mm.
    top = doc.add_table(rows=2, cols=3)
    no_borders(top)
    top.autofit = False
    def grid(table, widths_mm):
        """Column widths Word and LibreOffice both keep: the table grid and every cell."""
        table.autofit = False
        for i, wdt in enumerate(widths_mm):
            table.columns[i].width = Mm(wdt)
            for cell in table.columns[i].cells:
                cell.width = Mm(wdt)

    # The block runs from 125 mm to the text's right edge (65 mm), as on the PDF and on an invoice.
    info_w = letter.info_width()
    grid(top, (80, g["info_x"] - g["left"] - 80, info_w))
    top.rows[0].height, top.rows[0].height_rule = Mm(g["return_h"]), WD_ROW_HEIGHT_RULE.EXACTLY
    top.rows[1].height, top.rows[1].height_rule = Mm(g["address_h"]), WD_ROW_HEIGHT_RULE.AT_LEAST
    ret = top.cell(0, 0)
    ret.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.BOTTOM
    run(ret.paragraphs[0], lt.return_line(), size=7, grey=True)
    addr = top.cell(1, 0)
    for i, line in enumerate(lt.address()):
        p = addr.paragraphs[0] if i == 0 else addr.add_paragraph()
        p.paragraph_format.line_spacing = Mm(letter.ADDRESS_LINE)
        run(p, line, size=10)
    # The information block as on the PDF: labels in a grey column as wide as the longest label needs
    # (8.5 pt type), values beside them.
    info = top.cell(0, 2).merge(top.cell(1, 2))
    lead = info.paragraphs[0].paragraph_format
    lead.space_before, lead.line_spacing = Mm(g["info_y"] - g["field_y"]), Pt(1)
    rows = lt.info_rows()
    block = info.add_table(rows=len(rows), cols=2)
    no_borders(block)
    label_w = max(14, min(30, 1.45 * max([len(k) for k, _ in rows] or [0]) + 2))
    grid(block, (label_w, info_w - label_w))
    for i, (k, v) in enumerate(rows):
        run(block.cell(i, 0).paragraphs[0], k, size=8.5, grey=True)
        value = block.cell(i, 1)
        run(value.paragraphs[0], str(v), size=8.5)
        mar = OxmlElement("w:tcMar")
        left = OxmlElement("w:left")
        left.set(qn("w:w"), "85")
        left.set(qn("w:type"), "dxa")
        mar.append(left)
        value._tc.get_or_add_tcPr().append(mar)
    info.paragraphs[-1].paragraph_format.line_spacing = Pt(1)

    subject = para(before=g["subject_gap"], after=8)
    run(subject, spec["subject"], bold=True)
    para(spec["salutation"], after=4)
    for text in spec["body"]:
        para(text, after=4)
    para(spec["closing"], before=2, after=12)
    for line in lt.sign():
        para(line)
    if spec.get("enclosures"):
        p = para(before=8)
        run(p, lt.w["enclosures"], bold=True)
        for x in spec["enclosures"]:
            para(x)

    usable = 210 - g["left"] - g["right"]
    foot = sec.footer.add_table(rows=1, cols=3, width=Mm(usable))
    no_borders(foot)
    for i, col in enumerate(lt.footer()):
        cell = foot.cell(0, i)
        cell.width = Mm(usable / 3)
        for j, line in enumerate(col):
            run(cell.paragraphs[0] if j == 0 else cell.add_paragraph(), line, size=7, grey=True)
    doc.save(out)
    return "python-docx"


def main(argv):
    if len(argv) != 3:
        print(__doc__.split("\n\n")[1])
        return 2
    spec = json.loads(Path(argv[1]).read_text())
    out = Path(argv[2])
    # Nothing given is dropped: an unknown key or a value of the wrong shape stops the build here.
    spec_guard.guard(spec, HERE.parent / "spec.fields.json", "letter data file")
    spec_guard.output_guard(out, __file__, "letter")
    # The company's own particulars, written once in the person's folder: what the data file leaves out.
    company.apply(spec, argv[1], "business-letter")
    lid, layout = letter.letter_layout(spec)
    if layout:
        # Norway, Denmark, Finland, the United States, the United Kingdom, Canada, Australia, Belgium, the
        # Netherlands, Austria, Ireland, Spain, Italy and Poland.
        import window_letter as kind
    else:
        kind = sys.modules[__name__]
    writer = {".docx": kind.write_docx, ".pdf": kind.write_pdf}.get(out.suffix.lower())
    if not writer:
        raise SystemExit("output must end in .docx or .pdf")
    how = writer(spec, out)
    lt = kind.WindowLetter(spec) if layout else Letter(spec)
    summary = {"file": str(out), "language": lt.locale, "why": lt.why, "made_with": how,
               "page": layout["name"] if layout else "DIN 5008:2020 Form B"}
    if layout:
        summary["envelope"] = layout["envelope"]
        status, source = letter.WINDOW_SOURCES.get(layout["country"], ("", ""))
        if source:
            summary["window_source"] = "%s: %s" % (status, source)
    missing = letter.company_missing(spec["sender"])
    if missing:
        summary["company_details_missing"] = missing
        summary["say"] = "The sender is a company and the files do not give its %s; say so in your reply." % ", ".join(missing)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
