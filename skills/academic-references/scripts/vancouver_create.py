#!/usr/bin/env python3
"""Write a paper or report with Vancouver references as Word from a JSON spec.

Usage: vancouver_create.py spec.json report.docx

Spec (templates/vancouver.spec.json is a short clinical audit to start from):
{
  "title": "...", "byline": "optional line under the title", "language": "en-GB",
  "marks": "brackets",            # or "superscript" or "parentheses": one form for the whole paper
  "sections": [{"heading": "Background", "paragraphs": ["A sentence that cites [@key].", "..."]}],
  "references": {
    "key": {"type": "article", "authors": ["Surname AB", "Other C"], "title": "...",
            "journal": "Abbrev J Title", "year": 2021, "month": "Mar", "volume": "12", "issue": "3",
            "pages": "45-67", "doi": "10.xxxx/yyy"},
    "key2": {"type": "article", ..., "url": "https://...", "cited": "2026 Oct 9"},    # read online
    "key3": {"type": "book", "authors": [...], "title": "...", "edition": "2nd", "place": "City",
             "publisher": "...", "year": 2019},
    "key4": {"type": "report", "group": "Name of Organisation", "title": "...", "place": "City",
             "publisher": "...", "year": 2024, "number": "Report No.: 7"},
    "key5": {"type": "web", "title": "...", "place": "City", "publisher": "...", "year": 2025,
             "updated": "2025 Jun 3", "cited": "2026 Oct 9", "url": "https://..."}
  }
}

A citation in a paragraph is [@key] or [@key1; @key2]. Sources are numbered in the order the text
first cites them, and a source cited again keeps its first number (ICMJE Recommendations IV.A.3.g;
Citing Medicine, 2nd ed.). Runs of three or more numbers are written as a range, 1-3.

The forms are restated from Citing Medicine, 2nd edition (NLM, public domain): chapter 1 journals
(1B on the Internet: [Internet], [cited date], Available from:), chapter 2 books; and NLM's sample
references: Surname and initials without full stops, the first six authors then et al., journal
abbreviated without full stops, year;volume(issue):pages.

The script refuses a citation of a key the spec does not list and a listed source the text never
cites. It never invents a detail: a field the spec leaves out stays out. It runs the pack's VANC
rules on what it wrote and prints a JSON summary; exit 1 when a rule fails. Needs python-docx.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_checks"))

FONT = "Times New Roman"
CITE = re.compile(r"\[@([^\]]+)\]")


def initials_of(name):
    """'Okafor-Lindqvist P.A.' -> 'Okafor-Lindqvist PA'; a dict {surname, initials} the same."""
    if isinstance(name, dict):
        surname, initials = name["surname"], name.get("initials", "")
    else:
        bits = name.strip().rsplit(" ", 1)
        if len(bits) == 2 and re.fullmatch(r"(?:[A-Z]\.?\s?){1,4}", bits[1]):
            surname, initials = bits
        else:
            m = re.fullmatch(r"(.+?)\s((?:[A-Z]\.\s?){1,4})", name.strip())
            surname, initials = (m.group(1), m.group(2)) if m else (name.strip(), "")
    initials = re.sub(r"[.\s]", "", initials)
    return ("%s %s" % (surname.strip(), initials)).strip()


def author_block(ref):
    people = [initials_of(a) for a in ref.get("authors") or []]
    group = ref.get("group")
    if len(people) > 6:
        people = people[:6] + ["et al"]
    names = ", ".join(people)
    if group:
        names = "%s; %s" % (names, group) if names else group
    return names


def journal_of(name):
    return re.sub(r"\.(?=\s|$)", "", name).strip()


def sentence(text):
    text = text.strip()
    return text if text.endswith((".", "?", "!")) else text + "."


def date_part(ref, internet):
    date = str(ref["year"])
    if ref.get("month"):
        date += " " + ref["month"]
        if ref.get("day"):
            date += " %s" % ref["day"]
    brackets = []
    if ref.get("updated"):
        brackets.append("updated " + ref["updated"])
    if internet and ref.get("cited"):
        brackets.append("cited " + ref["cited"])
    if brackets:
        date += " [%s]" % "; ".join(brackets)
    return date


def entry(ref):
    kind = ref.get("type", "article")
    internet = bool(ref.get("url"))
    if internet and not ref.get("cited"):
        raise SystemExit("a source read online needs \"cited\": the date it was read (Citing Medicine 1B): %s"
                         % ref.get("title", "")[:50])
    who = author_block(ref)
    head = sentence(who) + " " if who else ""
    tail = ""
    if ref.get("doi"):
        tail += " doi:%s" % ref["doi"].replace("https://doi.org/", "")
    if internet:
        tail += " Available from: %s" % ref["url"]
    if kind == "article":
        journal = journal_of(ref["journal"]) + (" [Internet]" if internet else "")
        where = "%s;%s" % (date_part(ref, internet), ref.get("volume", ""))
        if ref.get("issue"):
            where += "(%s)" % ref["issue"]
        if ref.get("pages"):
            where += ":%s" % ref["pages"]
        body = "%s%s %s. %s." % (head, sentence(ref["title"]), journal, where)
    elif kind in ("book", "report"):
        title = ref["title"] + (" [Internet]" if internet else "")
        body = head + sentence(title) + " "
        if ref.get("edition"):
            body += "%s ed. " % ref["edition"]
        body += "%s: %s; %s." % (ref["place"], ref["publisher"], date_part(ref, internet))
        if ref.get("number"):
            body += " " + sentence(ref["number"])
    elif kind == "web":
        body = "%s%s [Internet]. %s: %s; %s." % (head, ref["title"], ref["place"], ref["publisher"],
                                                 date_part(ref, True))
    else:
        raise SystemExit("unknown reference type %r: article, book, report or web" % kind)
    return body + tail


def collapse(nums):
    nums = sorted(set(nums))
    out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        if j - i >= 2:
            out.append("%d–%d" % (nums[i], nums[j]))
        else:
            out.extend(str(n) for n in nums[i:j + 1])
        i = j + 1
    return ",".join(out)


def number_sources(spec):
    order, missing = {}, []
    for section in spec["sections"]:
        for para in section.get("paragraphs", []):
            for group in CITE.findall(para):
                for key in re.split(r"[;,]\s*", group):
                    key = key.strip().lstrip("@")
                    if key not in spec["references"]:
                        missing.append(key)
                    elif key not in order:
                        order[key] = len(order) + 1
    uncited = [k for k in spec["references"] if k not in order]
    return order, missing, uncited


def build(spec, out):
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.shared import Inches, Pt, RGBColor

    order, missing, uncited = number_sources(spec)
    if missing:
        raise SystemExit("cited but not in the spec's references: %s" % ", ".join(sorted(set(missing))))
    if uncited:
        raise SystemExit("listed but never cited, take them out or cite them: %s" % ", ".join(uncited))
    marks = spec.get("marks", "brackets")
    if marks not in ("brackets", "superscript", "parentheses"):
        raise SystemExit("marks is brackets, superscript or parentheses")

    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name, normal.font.size = FONT, Pt(12)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    pf = normal.paragraph_format
    pf.line_spacing, pf.space_before, pf.space_after = 2.0, Pt(0), Pt(0)
    for name in ("Title", "Heading 1"):
        st = doc.styles[name]
        st.font.name, st.font.bold, st.font.color.rgb = FONT, True, RGBColor(0, 0, 0)
        st.font.size = Pt(14 if name == "Title" else 12)
        fonts = st.element.rPr.rFonts
        for theme in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
            fonts.attrib.pop(qn(theme), None)
        st.paragraph_format.space_before, st.paragraph_format.space_after = Pt(12), Pt(0)

    t = doc.add_paragraph(spec["title"], style="Title")
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if spec.get("byline"):
        b = doc.add_paragraph(spec["byline"])
        b.alignment = WD_ALIGN_PARAGRAPH.CENTER

    for section in spec["sections"]:
        if section.get("heading"):
            doc.add_heading(section["heading"], level=1)
        for para in section.get("paragraphs", []):
            p = doc.add_paragraph()
            p.paragraph_format.first_line_indent = Inches(0.5)
            pos = 0
            for m in CITE.finditer(para):
                before = para[pos:m.start()]
                if marks == "superscript":
                    before = before.rstrip()
                p.add_run(before)
                nums = [order[k.strip().lstrip("@")] for k in re.split(r"[;,]\s*", m.group(1))]
                text = collapse(nums)
                if marks == "superscript":
                    p.add_run(text).font.superscript = True
                else:
                    p.add_run("[%s]" % text if marks == "brackets" else "(%s)" % text)
                pos = m.end()
            p.add_run(para[pos:])

    doc.add_heading("References", level=1)
    for key, n in sorted(order.items(), key=lambda kv: kv[1]):
        p = doc.add_paragraph("%d. %s" % (n, entry(spec["references"][key])))
        f = p.paragraph_format
        f.left_indent, f.first_line_indent = Inches(0.4), Inches(-0.4)

    doc.core_properties.title = spec["title"]
    doc.core_properties.language = spec.get("language", "en-GB")
    doc.save(str(out))
    return order


def main():
    if len(sys.argv) != 3:
        print(__doc__.split("\n\n")[0])
        return 2
    spec = json.loads(Path(sys.argv[1]).read_text())
    out = Path(sys.argv[2])
    order = build(spec, out)
    import academic_style
    fails = {}
    for rule in academic_style.VANC_RULES:
        ok, why = academic_style.check(rule, out, {}, "first")
        if ok is False:
            fails[rule] = why
    print(json.dumps({"file": str(out), "references": len(order), "marks": spec.get("marks", "brackets"),
                      "failing_rules": fails}, ensure_ascii=False))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
