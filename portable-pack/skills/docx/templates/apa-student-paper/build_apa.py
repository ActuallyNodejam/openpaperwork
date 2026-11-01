#!/usr/bin/env python3
"""Build an APA 7 student paper. The format rules live here, not in the model's memory.

    python3 build_apa.py spec.json report.docx

The spec carries the content; this builder applies the rules the pack is graded on:

  * the title page: title in bold in the upper half, then author, affiliation, course,
    instructor and date, each centred, with the page number top right;
  * the body opens with the paper title, and there is never an Introduction heading;
  * Level 1 headings centred bold, Level 2 flush left bold, double spacing, one inch margins,
    first-line indents, hanging indents on the reference list;
  * the reference list starts on a page of its own;
  * a reference may only be listed if the notes carried it: every entry needs a source, and
    every entry must be cited in the body.

Spec:
{
  "title": "...", "author": "...", "affiliation": "...", "course": "...",
  "instructor": "...", "date": "October 20, 2026",
  "body": [{"level": 1|2, "text": "..."} | {"paragraph": "..."}],
  "references": ["Example, A. (2025). Title. Journal, 12(3), 210-219. https://doi.org/..."]
}
"""
import json
import re
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt


def page_numbers(doc):
    for section in doc.sections:
        p = section.header.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        run = p.add_run()
        fld = OxmlElement("w:fldSimple")
        fld.set(qn("w:instr"), "PAGE")
        run._r.addnext(fld)


def para(doc, text, *, align=None, bold=False, indent=None, hanging=False, italic_spans=()):
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 2.0
    p.paragraph_format.space_after = Pt(0)
    if align:
        p.alignment = align
    if indent:
        p.paragraph_format.first_line_indent = Inches(0.5)
    if hanging:
        p.paragraph_format.left_indent = Inches(0.5)
        p.paragraph_format.first_line_indent = Inches(-0.5)
    if italic_spans:
        rest = text
        for span in italic_spans:
            before, rest = rest.split(span, 1)
            p.add_run(before)
            r = p.add_run(span)
            r.italic = True
        p.add_run(rest)
    else:
        r = p.add_run(text)
        r.bold = bold
    return p


def cite_key(entry):
    m = re.match(r"([A-Z][A-Za-z'\-]+)", entry)
    y = re.search(r"\((\d{4}|n\.d\.)\)", entry)
    return (m.group(1), y.group(1)) if m and y else None


def build(spec, out):
    body_text = " ".join(p.get("text") or p.get("paragraph", "") for p in spec["body"])
    unsourced = [e for e in spec.get("references", []) if not re.search(r"https?://|doi\.org|Press|Journal|Proceedings|Retrieved", e)]
    if unsourced:
        raise SystemExit("a reference carries no source, so it cannot be listed: %s" % unsourced[0][:60])
    uncited = []
    for e in spec.get("references", []):
        k = cite_key(e)
        if not k:
            continue
        surname, year = k
        if not re.search(r"%s[^.]{0,60}%s" % (re.escape(surname), re.escape(year)), body_text):
            uncited.append("%s %s" % (surname, year))
    if uncited:
        raise SystemExit("listed but never cited in the body: %s" % ", ".join(uncited))

    doc = Document()
    doc.core_properties.title = spec["title"]
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(12)
    for s in doc.sections:
        s.top_margin = s.bottom_margin = s.left_margin = s.right_margin = Inches(1)
    page_numbers(doc)

    for _ in range(3):
        para(doc, "")
    para(doc, spec["title"], align=WD_ALIGN_PARAGRAPH.CENTER, bold=True)
    para(doc, "")
    for line in (spec.get("author"), spec.get("affiliation"), spec.get("course"),
                 spec.get("instructor"), spec.get("date")):
        if line:
            para(doc, line, align=WD_ALIGN_PARAGRAPH.CENTER)

    doc.add_page_break()
    para(doc, spec["title"], align=WD_ALIGN_PARAGRAPH.CENTER, bold=True)
    for item in spec["body"]:
        if "level" in item:
            para(doc, item["text"], bold=True,
                 align=WD_ALIGN_PARAGRAPH.CENTER if item["level"] == 1 else None)
        else:
            para(doc, item["paragraph"], indent=True)

    if spec.get("references"):
        doc.add_page_break()                      # the list starts on its own page, always
        para(doc, "References", align=WD_ALIGN_PARAGRAPH.CENTER, bold=True)
        for entry in spec["references"]:
            italics = re.findall(r"\|([^|]+)\|", entry)
            clean = re.sub(r"\|([^|]+)\|", r"\1", entry)
            para(doc, clean, hanging=True, italic_spans=italics)
    doc.save(out)
    return out


if __name__ == "__main__":
    spec = json.loads(open(sys.argv[1]).read())
    print(build(spec, sys.argv[2]))
