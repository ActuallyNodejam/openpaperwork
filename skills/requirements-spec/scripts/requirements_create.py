#!/usr/bin/env python3
"""Write a requirements specification as Word from a JSON spec, in English or Swedish.

Usage: requirements_create.py spec.json requirements.docx

Spec (templates/ has one in English and one in Swedish):
{
  "language": "en",                          # "sv" for Swedish
  "product": "PS-30 bench power supply",     # what the requirements are for
  "organisation": "Larkfield Instruments Ltd", "document": "LFI-RS-007", "version": "0.2",
  "date": "2026-10-20", "status": "Draft for review", "author": "Nadia Okafor", "approver": "Tom Ashby",
  "purpose": "Why the document exists, in one or two sentences.",
  "scope": "What it covers and what it leaves out.",
  "definitions": [{"term": "Ripple", "meaning": "..."}],
  "facts": ["The supply will be used on lab benches at 0 °C to 40 °C."],     # context and assumptions: "will"
  "requirements": [{"id": "PS-001", "section": "Output",
                    "text": "The supply shall deliver an output voltage adjustable from 0 V to 30 V.",
                    "rationale": "Why it is needed.", "verification": "test"}],  # test, analysis, inspection, demonstration
  "goals": [{"id": "PS-G01", "text": "The supply should run without a fan up to 50 W.", "rationale": "..."}],
  "tbd": [{"id": "TBR-1", "requirement": "PS-006", "estimate": "85 %", "closes": "What settles it",
           "owner": "Nadia Okafor", "due": "2026-11-30"}],
  "history": [{"version": "0.1", "date": "2026-10-06", "change": "First draft", "author": "Nadia Okafor"}]
}

Where each part comes from:
- NASA Systems Engineering Handbook, NASA/SP-2016-6105 Rev 2, Appendix C "How to Write a Good Requirement",
  public domain: "shall" for a requirement, "will" for a fact, "should" for a goal (C.1); every requirement
  with its rationale and assumptions (C.3) and its own number (C.4 Traceability); TBD and TBR kept in one list
  with who resolves each and by when (C.3, C.4 Completeness); each verified by test, analysis, inspection or
  demonstration (C.4 Verifiability).
- ISO/IEC Directives, Part 2 (2021), clause 7, cited: shall, should, may and can, and "must" kept for a
  constraint from outside the document. In Swedish: ska, bör, får, kan.
- SI Brochure, 9th edition (BIPM, version 4.01, CC BY 4.0), 5.4.3 and 5.4.7, and NIST SP 811 (2008) 7.2: a
  space between the number and the unit symbol, written here as a no-break space so a value never splits.
- Dates: Unicode CLDR for the language (skills/_shared/letter.py).
Prints a JSON summary. Needs python-docx.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import letter  # noqa: E402
import spec_guard  # noqa: E402

FONT = "Arial"
WORDS = {
    "en-GB": {
        "title": "Requirements specification: %s",
        "facts": [("organisation", "Organisation"), ("document", "Document"), ("version", "Version"),
                  ("date", "Date"), ("status", "Status"), ("author", "Author"), ("approver", "Approved by")],
        "purpose": "Purpose and scope", "conventions": "Conventions", "definitions": "Definitions",
        "context": "Context and assumptions", "requirements": "Requirements", "goals": "Goals",
        "tbd": "TBD and TBR items", "history": "Change history",
        "convention": "In this document “shall” marks a requirement, “will” a statement of fact and "
                      "“should” a goal. Every requirement has an identifier of its own, a rationale and the "
                      "way it is verified: test, analysis, inspection or demonstration. A value not yet decided is "
                      "marked TBD (to be determined) and a best estimate still to be confirmed TBR (to be resolved)%s "
                      "Quantities are given in SI units, with a space between the number and the unit symbol.",
        "tbd_where": "; section %d lists each one with who resolves it and by when.",
        "tbd_none": "; none is open in this version.",
        "due_open": "to be agreed",
        "head_req": ["ID", "Requirement", "Rationale", "Verification"],
        "head_goal": ["ID", "Goal", "Rationale"],
        "head_tbd": ["ID", "Requirement", "Best estimate", "To close it", "Owner", "Due"],
        "head_def": ["Term", "Meaning"],
        "head_hist": ["Version", "Date", "Change", "Author"],
        "methods": {"test": "Test", "analysis": "Analysis", "inspection": "Inspection", "demonstration": "Demonstration"},
    },
    "sv-SE": {
        "title": "Kravspecifikation: %s",
        "facts": [("organisation", "Organisation"), ("document", "Dokument"), ("version", "Version"),
                  ("date", "Datum"), ("status", "Status"), ("author", "Författare"), ("approver", "Godkänd av")],
        "purpose": "Syfte och omfattning", "conventions": "Konventioner", "definitions": "Definitioner",
        "context": "Förutsättningar och antaganden", "requirements": "Krav", "goals": "Mål",
        "tbd": "TBD- och TBR-punkter", "history": "Ändringshistorik",
        "convention": "I detta dokument anger ”ska” ett krav, ”kommer att” ett faktum och ”bör” "
                      "ett mål. Varje krav har en egen identitet, en motivering och ett sätt att verifiera det: "
                      "provning, analys, inspektion eller demonstration. Ett värde som ännu inte är bestämt markeras "
                      "TBD (to be determined) och en bästa uppskattning som återstår att bekräfta markeras TBR "
                      "(to be resolved)%s Storheter anges i SI-enheter, med mellanslag mellan tal och enhetssymbol.",
        "tbd_where": "; avsnitt %d listar var och en med vem som löser den och när.",
        "tbd_none": "; ingen är öppen i denna version.",
        "head_req": ["ID", "Krav", "Motivering", "Verifiering"],
        "head_goal": ["ID", "Mål", "Motivering"],
        "due_open": "att bestämma",
        "head_tbd": ["ID", "Krav", "Bästa uppskattning", "För att stänga", "Ansvarig", "Klart senast"],
        "head_def": ["Term", "Betydelse"],
        "head_hist": ["Version", "Datum", "Ändring", "Författare"],
        "methods": {"test": "Provning", "analysis": "Analys", "inspection": "Inspektion", "demonstration": "Demonstration",
                    "provning": "Provning", "analys": "Analys", "inspektion": "Inspektion"},
    },
}
# Shares of the 160 mm text width: the identifier narrow, the statement widest, then its rationale.
WIDTHS = {"head_req": [12, 40, 30, 18], "head_goal": [12, 52, 36], "head_tbd": [11, 12, 17, 30, 16, 14],
          "head_def": [26, 74], "head_hist": [12, 17, 51, 20]}
TEXT_MM = 160
INK, GREY, RULE, SHADE = "12100E", "6B6259", "D9D4CC", "F2F0ED"
REQUIRED = ("product", "requirements")
UNIT = (r"(?:°C|%|‰|m²|m³|mm²|cm²|mm³|cm³|[kMGmµμcnh]?(?:m|g|s|Hz|N|Pa|W|Wh|V|A|J|L|l|Ω|bar)|min|h|t|dB|lx|lm|mol)")


def locale_of(spec):
    return "sv-SE" if str(spec.get("language") or "en").lower().startswith("sv") else "en-GB"


def nbsp(text):
    """A no-break space between a number and its unit symbol (SI Brochure 5.4.3), so 20 °C stays on one line."""
    return re.sub(r"(?<=\d) (?=%s(?![A-Za-z]))" % UNIT, " ", str(text))


def sections(spec):
    order = []
    for r in spec["requirements"]:
        name = r.get("section") or ""
        if name not in order:
            order.append(name)
    return order


def write_docx(spec, out):
    from docx import Document
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Mm, Pt, RGBColor
    missing = [k for k in REQUIRED if not spec.get(k)]
    if missing:
        raise SystemExit("the spec needs %s" % ", ".join(missing))
    bad = [r for r in spec["requirements"] if not r.get("id") or not r.get("text")]
    if bad:
        raise SystemExit("every requirement needs an id and a text")
    loc = locale_of(spec)
    w = WORDS[loc]
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Mm(210), Mm(297)
    sec.left_margin = sec.right_margin = Mm(25)
    sec.top_margin = sec.bottom_margin = Mm(20)
    for style in doc.styles:
        if style.type == 1 and style.font is not None:
            style.font.name = FONT
            rpr = style.element.get_or_add_rPr()
            fonts = rpr.find(qn("w:rFonts"))
            if fonts is not None:
                for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
                    fonts.set(qn(attr), FONT)
    doc.styles["Normal"].font.size = Pt(11)
    title = spec.get("title") or w["title"] % spec["product"]
    doc.core_properties.title = title
    doc.core_properties.language = loc
    doc.core_properties.author = spec.get("author") or ""
    doc.core_properties.subject = spec["product"]

    def borders(table, inside_h):
        """No grid: hairlines between rows only, no verticals, no frame."""
        pr = table._tbl.tblPr
        b = OxmlElement("w:tblBorders")
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
            e = OxmlElement("w:%s" % edge)
            if inside_h and edge in ("insideH", "bottom"):
                e.set(qn("w:val"), "single")
                e.set(qn("w:sz"), "4")
                e.set(qn("w:space"), "0")
                e.set(qn("w:color"), RULE)
            else:
                e.set(qn("w:val"), "nil")
            b.append(e)
        pr.append(b)
        lay = OxmlElement("w:tblLayout")
        lay.set(qn("w:type"), "fixed")
        pr.append(lay)

    def margins(table, top, side):
        mar = OxmlElement("w:tblCellMar")
        for edge, v in (("top", top), ("left", side), ("bottom", top), ("right", side)):
            e = OxmlElement("w:%s" % edge)
            e.set(qn("w:w"), str(v))
            e.set(qn("w:type"), "dxa")
            mar.append(e)
        table._tbl.tblPr.append(mar)

    def widths(table, mm):
        table.autofit = False
        for i, wdt in enumerate(mm):
            table.columns[i].width = Mm(wdt)
            for cell in table.columns[i].cells:
                cell.width = Mm(wdt)

    def row_props(row, header=False):
        pr = row._tr.get_or_add_trPr()
        pr.append(OxmlElement("w:cantSplit"))       # a requirement never breaks across two pages
        if header:
            rep = OxmlElement("w:tblHeader")         # and the header row repeats on every page
            rep.set(qn("w:val"), "true")
            pr.append(rep)

    def shade_and_rule(cell):
        pr = cell._tc.get_or_add_tcPr()
        b = OxmlElement("w:tcBorders")
        e = OxmlElement("w:bottom")
        for k, v in (("w:val", "single"), ("w:sz", "8"), ("w:space", "0"), ("w:color", INK)):
            e.set(qn(k), v)
        b.append(e)
        pr.append(b)
        shd = OxmlElement("w:shd")
        for k, v in (("w:val", "clear"), ("w:color", "auto"), ("w:fill", SHADE)):
            shd.set(qn(k), v)
        pr.append(shd)

    def write(cell, text, bold=False, size=9.5):
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.1
        r = p.add_run(text)
        r.bold, r.font.size = bold, Pt(size)
        return r

    def table(key, rows):
        head = w[key]
        t = doc.add_table(rows=1 + len(rows), cols=len(head))
        borders(t, True)
        margins(t, 70, 100)
        widths(t, [TEXT_MM * share / 100 for share in WIDTHS[key]])
        row_props(t.rows[0], header=True)
        for i, h in enumerate(head):
            cell = t.rows[0].cells[i]
            write(cell, h, bold=True, size=9)
            shade_and_rule(cell)
        for n, r in enumerate(rows, 1):
            row_props(t.rows[n])
            for i, v in enumerate(r):
                write(t.rows[n].cells[i], nbsp(v), bold=i == 0 and key != "head_hist")
        doc.add_paragraph().paragraph_format.space_after = Pt(4)

    def facts(pairs):
        """The document's own data as a label and value block, not running text."""
        t = doc.add_table(rows=len(pairs), cols=2)
        borders(t, False)
        margins(t, 20, 0)
        widths(t, (32, TEXT_MM - 32))
        for n, (label, value) in enumerate(pairs):
            r = write(t.rows[n].cells[0], label, size=10)
            r.font.color.rgb = RGBColor.from_string(GREY)
            write(t.rows[n].cells[1], str(value), size=10)
        doc.add_paragraph().paragraph_format.space_after = Pt(2)

    doc.add_heading(title, level=1)
    facts([(label, letter.date(spec[key], loc) if key == "date" else spec[key]) for key, label in w["facts"] if spec.get(key)])
    n = 0

    def section(name):
        nonlocal n
        n += 1
        doc.add_heading("%d  %s" % (n, name), level=2)
        return n

    section(w["purpose"])
    for key in ("purpose", "scope"):
        if spec.get(key):
            doc.add_paragraph(nbsp(spec[key]))
    section(w["conventions"])
    later = bool(spec.get("definitions")) + bool(spec.get("facts")) + 1 + bool(spec.get("goals")) + 1
    where = w["tbd_where"] % (n + later) if spec.get("tbd") else w["tbd_none"]
    doc.add_paragraph(w["convention"] % where)
    if spec.get("definitions"):
        section(w["definitions"])
        table("head_def", [(d.get("term", ""), d.get("meaning", "")) for d in spec["definitions"]])
    if spec.get("facts"):
        section(w["context"])
        for fact in spec["facts"]:
            doc.add_paragraph(nbsp(fact), style="List Bullet")
    top = section(w["requirements"])
    names = sections(spec)
    for k, name in enumerate(names, 1):
        if name:
            doc.add_heading("%d.%d  %s" % (top, k, name), level=3)
        rows = []
        for r in spec["requirements"]:
            if (r.get("section") or "") != name:
                continue
            method = str(r.get("verification") or "")
            rows.append((r["id"], r["text"], r.get("rationale", ""), w["methods"].get(method.lower(), method)))
        table("head_req", rows)
    if spec.get("goals"):
        section(w["goals"])
        table("head_goal", [(g["id"], g["text"], g.get("rationale", "")) for g in spec["goals"]])
    if spec.get("tbd"):
        section(w["tbd"])
        table("head_tbd", [(t.get("id", ""), t.get("requirement", ""), t.get("estimate", ""), t.get("closes", ""),
                            t.get("owner", "") or w["due_open"],
                            letter.date(t["due"], loc) if t.get("due") else w["due_open"]) for t in spec["tbd"]])
    if spec.get("history"):
        section(w["history"])
        table("head_hist", [(h.get("version", ""), letter.date(h.get("date", ""), loc), h.get("change", ""),
                             h.get("author", "")) for h in spec["history"]])
    doc.save(out)


def main(argv):
    if len(argv) != 3:
        print(__doc__.split("\n\n")[1])
        return 2
    spec = json.loads(Path(argv[1]).read_text())
    out = Path(argv[2])
    if out.suffix.lower() != ".docx":
        raise SystemExit("output must end in .docx")
    # Nothing given is dropped: an unknown key or a value of the wrong shape stops the build here.
    spec_guard.guard(spec, HERE.parent / "spec.fields.json", "specification's data file")
    spec_guard.output_guard(out, __file__, "specification")
    write_docx(spec, out)
    print(json.dumps({"file": str(out), "language": locale_of(spec), "requirements": len(spec["requirements"]),
                      "goals": len(spec.get("goals") or []), "tbd": len(spec.get("tbd") or [])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
