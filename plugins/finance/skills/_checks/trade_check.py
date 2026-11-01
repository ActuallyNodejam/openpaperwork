#!/usr/bin/env python3
"""TRADE-LANG: a trade document's labels are all in the document's own language. TRADE-BLOCK: its
information block keeps to the text's right edge and to one line per label. TRADE-WINDOW: it sits on the
letter layout of the country it is sent from, its address inside that country's envelope window.

A quotation, order confirmation, delivery note, pro forma or purchase order prints its labels (the
document's name, the information block, the column heads, the totals, the delivery and payment terms)
in one language. The words come from trade_words.json beside this file, the table the builder in
skills/trade-documents prints from, in each language's published business usage. The check reads the
finished PDF, Word or Excel file, takes out every label of the document's own locale, and reports any
label left over that belongs to another locale only: an English "Delivery terms" on a Norwegian tilbud,
"VAT" on a US quotation that writes sales tax, "Moms" on a Norwegian one that writes MVA.

A label one locale shares with the document's (Bank, Description) never counts, nor a word that is part
of one of the document's own labels (Total inside Total VAT). Text the customer wrote (descriptions,
notes, places) can hold a foreign word; the rule names what it found so a person can judge.

TRADE-BLOCK reads a printed PDF the way EINV-PAGE-DIN5008 reads an invoice page: the information block
starts 125 mm across (DIN 5008 Form B) and nothing in it passes the text's right margin, 20 mm from the
paper's edge, where the table below ends; and each label of the block (read from the page the builder
wrote beside the PDF) sits on one line. On a country layout the block stands where that layout puts it
(skills/_shared/letter.py layout_info): right of a window on the left, left of a window on the right, where
it ends before the window, or above a No. 10 window. Word and Excel files are not measured.

TRADE-WINDOW holds a trade document to the sheet its sender's letter and invoice sit on (letter.LAYOUTS,
by the sender's country: the seller's, or the buyer's on a purchase order). A PDF: every address line
inside the envelope window less what the operator keeps clear, nothing else in the window, the heading on
the layout's left margin, the table ending on its right margin and nothing past it. A Word file: the
layout's paper and margins, and a fixed first row and the cells before the address that put its first
line inside the window. A document from a country with no layout there (Germany, Sweden, France), or one
on the other paper, is on DIN 5008 Form B, which LETTER-DIN5008 measures; a workbook is not a letter.

check(rule_id, path, case, stage) -> (passed, evidence); passed is None when the rule does not apply.
"""
import html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import letter_check  # noqa: E402

TABLE = json.loads((HERE / "trade_words.json").read_text())


def phrases(locale):
    """Every label the locale prints, without its %s slots and trailing colons."""
    w = TABLE["words"].get(locale)
    if not w:
        return set()
    out = set()

    def add(text):
        text = str(text)
        for part in re.split(r"%[sd%]|%%", text):
            part = part.strip(" :").strip()
            if len(part) >= 3 and not part.replace(" ", "").isdigit():
                out.add(part)

    for key, value in w.items():
        if key in ("proforma",):          # a sentence, not a label
            continue
        if isinstance(value, dict):
            for v in value.values():
                add(v)
        else:
            add(value)
    for row in TABLE["labels"]:
        if row.get(locale):
            add(row[locale])
    return out


def _flat(text):
    return re.sub(r"\s+", " ", text.replace(" ", " ").replace(" ", " "))


def foreign_labels(text, locale):
    """[(label, locales)] of labels in the text that belong to other locales only."""
    own = phrases(locale)
    own_cf = {p.casefold() for p in own}
    rest = _flat(text)
    # Take out the document's own labels first, the longest first, so their words do not count.
    for p in sorted(own, key=len, reverse=True):
        rest = re.sub(r"(?<!\w)%s(?!\w)" % re.escape(p), " ", rest, flags=re.I)
    found = {}
    for other in TABLE["words"]:
        if other == locale:
            continue
        for p in phrases(other):
            cf = p.casefold()
            if cf in own_cf or any(re.search(r"(?<!\w)%s(?!\w)" % re.escape(cf), o) for o in own_cf):
                continue
            # One word is a label only as the label writes it (Article, MVA); a customer's sentence writes it
            # in lower case. A phrase of several words counts in any case.
            single = " " not in p
            rx = r"(?<!\w)%s(?!\w)" % re.escape(p)
            if re.search(rx, rest, flags=0 if single else re.I):
                found.setdefault(p, []).append(other)
    return sorted(found.items(), key=lambda kv: -len(kv[0]))


def customer_text(spec):
    """The words the spec carries that are not labels: names, addresses, descriptions, notes, terms, the
    values of its references and dates. They are the customer's, in whatever language they are written."""
    out = []

    def walk(v, key=""):
        if isinstance(v, dict):
            for k, x in v.items():
                if k not in ("label", "type", "language", "rule", "transport"):
                    walk(x, k)
        elif isinstance(v, list):
            for x in v:
                walk(x, key)
        elif isinstance(v, str) and len(v) >= 3:
            out.append(v)
    walk(spec or {})
    return sorted(set(out), key=len, reverse=True)


def _letter():
    sys.path.insert(0, str(HERE.parent / "_shared"))
    import letter
    return letter


TYPES = ("quotation", "order_confirmation", "delivery_note", "proforma_invoice", "purchase_order")


def spec_of(path, case, stage):
    """What the document was built from: the spec beside the file, else what a case's truth says of it (its
    "doc" names the type). {} when neither describes a trade document."""
    spec = letter_check.spec_beside(path)
    if not spec:
        truth = (case or {}).get("truth") or {}
        staged = truth.get(stage or "first") if isinstance(truth.get(stage or "first"), dict) else {}
        spec = dict(truth, **staged)
    if spec.get("type") not in TYPES and spec.get("doc") in TYPES:
        spec = dict(spec, type=spec["doc"])
    return spec if spec.get("type") in TYPES else {}


def parties(spec):
    """(sender, recipient) of a trade document: a purchase order is the buyer's letter to its supplier."""
    spec = spec or {}
    if spec.get("type") == "purchase_order":
        return spec.get("buyer") or {}, spec.get("seller") or {}
    return spec.get("seller") or {}, spec.get("buyer") or {}


def layout_for(spec, page_w=None):
    """The letter layout a trade document sits on: its sender's country's (skills/_shared/letter.py LAYOUTS,
    the call an invoice makes for its seller), when the file is on that layout's own paper; None for DIN 5008
    Form B. page_w: the file's page width in mm, when known."""
    letter = _letter()
    _lid, lay = letter.letter_layout({"sender": parties(spec)[0], "layout": (spec or {}).get("layout")})
    if lay and page_w and abs(letter.PAPER_MM[lay["paper"]][0] - page_w) > 1.5:
        return None
    return lay


def block_problems(pdf, lay=None):
    """What is wrong with the information block of a printed trade document: a list, empty when nothing is.
    lay: the country layout the page sits on; None measures DIN 5008 Form B."""
    import einvoice_page
    letter = _letter()
    g = letter.GEOMETRY
    words = einvoice_page.page_words(pdf)
    if not words:
        return ["no text on the page"]
    page_w = einvoice_page.page_width(pdf)
    if lay:
        ix, iy, _iw, how = letter.layout_info(lay)
        wx, wy, ww, wh = lay["window"]
        page_w = letter.PAPER_MM[lay["paper"]][0]         # the layout's own sheet; the PDF reports a fraction more
        head = first_heading(words, lay["left"], wy + wh, iy)
        if how == "left":
            # Left of a window on the right: from the left margin, level with the window, ending before it.
            edge = wx - (lay.get("clear") or 0)
            block = [w for w in words if lay["left"] - 1 <= w[0] < wx and iy - 2 <= w[1] < head]
            ends, where = "before the window, at %.0f mm" % edge, "left of the window"
        elif how == "above":
            # At the top right, ending above a No. 10 window.
            edge = page_w - lay["right"]
            block = [w for w in words if w[0] >= ix - 1 and w[3] <= iy + 1.5]
            # What stands right of the window and lower than the block may end is the block running down.
            low = [w for w in words if w[0] > max(ix - 1, wx + ww) and iy + 1.5 < w[3] <= wy + wh and w[1] < head]
            ends, where = "on the text's right edge at %.0f mm, where the table ends" % edge, "above the window"
            if low:
                return ["the information block runs below %.0f mm (%s); it ends above the window" % (iy, low[0][4])]
        else:
            edge = page_w - lay["right"]
            block = [w for w in words if w[0] >= ix - 1 and iy - 2 <= w[1] <= max(wy + wh, iy + 60) and w[1] < head]
            ends, where = "on the text's right edge at %.0f mm, where the table ends" % edge, "beside the window"
        missing = "no information block %s of the %s layout" % (where, lay["name"].split(":")[0])
    else:
        edge = page_w - g["right"]
        low = g["field_y"] + g["return_h"] + g["address_h"]
        block = [w for w in words if w[0] >= g["info_x"] - 1 and g["info_y"] - 2 <= w[1] <= max(low, g["info_y"] + 60)
                 and w[1] < first_heading(words, g["left"], low)]
        ends = "on the text's right edge at %.0f mm, where the table ends" % edge
        missing = "no information block from %s mm across beside the address field" % g["info_x"]
    problems = []
    if not block:
        return [missing]
    far = max(block, key=lambda w: w[2])
    if far[2] > edge + 0.5:
        problems.append("the information block runs to %.1f mm across (%s); it ends %s" % (far[2], far[4], ends))
    page = Path(pdf).with_suffix(".html")
    if page.is_file():
        for label in re.findall(r"<dt>(.*?)</dt>", page.read_text(errors="ignore")):
            toks = html.unescape(label).split()
            if len(toks) < 2:
                continue
            firsts = [w for w in block if w[4] == toks[0]]
            if firsts and not any(any(o[4] == toks[-1] and abs(o[1] - f[1]) < 1 and o[0] > f[0] for o in block)
                                  for f in firsts):
                problems.append("the label %r wraps over two lines" % html.unescape(label))
    return problems


HEADING_MM = 4.5    # a word of the 12 pt heading is this tall or taller on the page; the block's 8.5 pt and the text's 10 pt are not


def heading_word(words, top):
    """The first word of the document's heading: the first large type below `top` (the letterhead's name is
    above it), wherever on the line it starts; None when the page has none."""
    big = [w for w in words if w[1] > top and w[3] - w[1] >= HEADING_MM]
    return min(big, key=lambda w: (round(w[1]), w[0])) if big else None


def first_heading(words, left, low, top=None):
    """How far down the document's heading starts. top: on a country layout, where to look for it from, so
    it is told by its larger type from an information block that stands on the left edge itself (a window on
    the right); else the first text on the left edge below the address field or window (low)."""
    if top is not None:
        word = heading_word(words, top)
        if word:
            return word[1]
    below = [w[1] for w in words if abs(w[0] - left) <= 1.5 and w[1] > low]
    return min(below) if below else 10 ** 6


class _Addressed:
    """What letter_check.window_problems reads of a letter: its layout and its address lines."""

    def __init__(self, lay, lines):
        self.lay, self._lines = lay, lines

    def address(self):
        return self._lines


def pdf_window_problems(pdf, spec, lay):
    """A printed trade document against its layout: the address in the window and nothing else there, the
    heading on the left margin, the table ending on the right margin, nothing past it."""
    import einvoice_page
    letter = _letter()
    sender, recipient = parties(spec)
    lines = letter.postal_lines(recipient, sender.get("country"))
    problems = letter_check.window_problems(pdf, _Addressed(lay, lines))
    words = einvoice_page.page_words(pdf)
    left, edge = lay["left"], letter.PAPER_MM[lay["paper"]][0] - lay["right"]
    past = [w for w in words if w[2] > edge + 0.5]
    if past:
        far = max(past, key=lambda w: w[2])
        problems.append("%r runs to %.1f mm across, past the layout's right margin at %.1f mm" % (far[4], far[2], edge))
    head = heading_word(words, lay["window"][1])
    if not head:
        problems.append("no heading under the window")
    else:
        if abs(head[0] - left) > 1.5:
            problems.append("the text starts %.1f mm across; the layout's left margin is %.1f mm" % (head[0], left))
        end = max(w[2] for w in words if head[1] <= w[1] <= 262)
        if end < edge - 1.5:
            problems.append("the table ends %.1f mm across; the layout's right margin puts it at %.1f mm" % (end, edge))
    return problems


def docx_sheet(path):
    """A Word file's page (width, height), its margins and the rows of its first table, each (its exact height
    or None, [(cell width, cell text)]), all in mm: where the builder puts the address."""
    import zipfile
    from xml.etree import ElementTree as ET
    w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    mm = 25.4 / 1440
    with zipfile.ZipFile(path) as z:
        body = ET.fromstring(z.read("word/document.xml")).find(w + "body")
    sect = body.find(w + "sectPr")
    size = sect.find(w + "pgSz") if sect is not None else None
    mar = sect.find(w + "pgMar") if sect is not None else None
    out = {"size": (int(size.get(w + "w")) * mm, int(size.get(w + "h")) * mm) if size is not None else None,
           "margins": {k.replace(w, ""): int(v) * mm for k, v in mar.attrib.items() if v.lstrip("-").isdigit()} if mar is not None else {},
           "rows": []}
    table = body.find(w + "tbl")
    for row in table.findall(w + "tr") if table is not None else []:
        height = row.find("%strPr/%strHeight" % (w, w))
        exact = int(height.get(w + "val")) * mm if height is not None and height.get(w + "hRule") == "exact" else None
        cells = []
        for cell in row.findall(w + "tc"):
            width = cell.find("%stcPr/%stcW" % (w, w))
            # The cell's own paragraphs, one line each; a table nested in it (the information block) is not its text.
            text = "\n".join("".join(t.text or "" for t in p.iter(w + "t")) for p in cell.findall(w + "p"))
            cells.append((int(width.get(w + "w")) * mm if width is not None else 0.0, text))
        out["rows"].append((exact, cells))
    return out


def docx_window_problems(path, spec, lay):
    """A Word trade document against its layout: the paper, the margins, and the first row and the cells before
    the address that put its first line inside the window."""
    letter = _letter()
    sender, recipient = parties(spec)
    lines = [letter_check.norm(x) for x in letter.postal_lines(recipient, sender.get("country"))]
    d = docx_sheet(path)
    W, H = letter.paper_size(lay)
    bad = []
    if not d["size"] or abs(d["size"][0] - W) > 1 or abs(d["size"][1] - H) > 1:
        bad.append("the page is not %s (%.0f x %.0f mm)" % (lay["paper"], W, H))
    m = d["margins"]
    for side in ("left", "right"):
        if abs(m.get(side, 0) - lay[side]) > 1:
            bad.append("%s margin %.1f mm, the layout wants %.1f" % (side, m.get(side, 0), lay[side]))
    x0, y0, x1, y1 = letter.window_box(lay)
    found = next(((r, i) for r, (_h, cells) in enumerate(d["rows"]) for i, (_w, text) in enumerate(cells)
                  if letter_check.norm(text.split("\n")[0]) == lines[0]), None)
    over = [h for h, _cells in d["rows"][:found[0]]] if found else []
    if not found or not over or None in over:
        bad.append("no fixed rows with the address under them put the address in the window; build it with trade_create.py")
        return bad
    cells, at = d["rows"][found[0]][1], found[1]
    top = m.get("top", 0) + sum(over)
    if not (y0 - 0.5 <= top <= y1 - 15):
        bad.append("the address starts %.1f mm down; inside the window it may start %.0f-%.0f mm down" % (top, y0, y1 - 15))
    across = m.get("left", 0) + sum(width for width, _text in cells[:at])
    if not (x0 - 0.5 <= across <= x0 + 10):
        bad.append("the address starts %.1f mm across; inside the window it starts at %.0f mm" % (across, x0))
    held = [letter_check.norm(x) for x in cells[at][1].split("\n") if x.strip()]
    if held[:len(lines)] != lines:
        bad.append("the address cell does not hold the address as the post office reads it")
    return bad


def check(rule_id, path, case, stage):
    if rule_id == "TRADE-BLOCK":
        if Path(path).suffix.lower() != ".pdf":
            return None, "only a printed PDF is measured"
        spec = spec_of(path, case, stage)
        if not spec:
            return None, "no trade document spec beside the file"
        import einvoice_page
        lay = layout_for(spec, einvoice_page.page_width(path))
        problems = block_problems(path, lay)
        if problems:
            return False, "; ".join(problems)
        if lay and _letter().layout_info(lay)[3] == "left":
            return True, "the information block ends before the window and every label keeps to one line"
        return True, "the information block ends on the text's right edge and every label keeps to one line"
    if rule_id == "TRADE-WINDOW":
        kind = Path(path).suffix.lower()
        if kind not in (".pdf", ".docx"):
            return None, "a %s is not a letter; no window to measure" % kind
        spec = spec_of(path, case, stage)
        if not spec:
            return None, "no trade document spec beside the file"
        if kind == ".pdf":
            import einvoice_page
            lay = layout_for(spec, einvoice_page.page_width(path))
        else:
            size = docx_sheet(path)["size"]
            lay = layout_for(spec, size[0] if size else None)
        if not lay:
            return None, "on DIN 5008 Form B; LETTER-DIN5008 measures it"
        problems = pdf_window_problems(path, spec, lay) if kind == ".pdf" else docx_window_problems(path, spec, lay)
        if problems:
            # The sheet and what it rests on, so the reader knows which window is meant and where it comes from.
            return False, "%s; the sheet is %s (%s)" % ("; ".join(problems), lay["name"], lay["source"])
        return True, "the address sits in the window of the %s" % lay["envelope"]
    if rule_id != "TRADE-LANG":
        return None, "unknown rule %s" % rule_id
    locale = case.get("locale")
    if locale not in TABLE["words"]:
        return None, "the document names no language the trade table has (%s)" % (locale or "none")
    text = _flat(letter_check.text_of(path))
    for own in customer_text(letter_check.spec_beside(path)):
        text = text.replace(_flat(own), " ")
    if not text.strip():
        return None, "no text read from %s" % Path(path).name
    hits = foreign_labels(text, locale)
    if hits:
        return False, "labels in another language than the document's %s: %s; print them in %s" % (
            locale, "; ".join("%r (%s)" % (p, ", ".join(sorted(set(ls))[:3])) for p, ls in hits[:6]), locale)
    return True, "every label is in %s" % locale


if __name__ == "__main__":
    print(check("TRADE-LANG", sys.argv[1], {"locale": sys.argv[2]}, "first"))
    print(check("TRADE-BLOCK", sys.argv[1], {}, "first"))
    print(check("TRADE-WINDOW", sys.argv[1], {}, "first"))
