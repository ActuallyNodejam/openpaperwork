"""The business deck's structure rules, read off the deck itself: the PDF that is handed back, or the
editable PowerPoint file.

    check(rule_id, path, case, stage) -> (passed, evidence)

Every rule runs on the deck alone: no case file, no data file. The rules are the same whatever the
deck looks like; every bound that says how much a page may carry comes from the density preset the
deck was built in (skills/business-deck/density.json; the builder writes the preset's name into the
file's properties, and a deck without it is held to the default preset).

A PDF is read two ways at once. What the builder set (which box holds which words, each chart's
data, each table's cells) is in the file's own private data, written there by deck_build.py. What
the pages show is read off the pages: every letter's place, size and colour, and the pages drawn
as pictures. So on a PDF the page rules (fit, fill, grid, type, contrast) are measured on the real
pages, never estimated. A PowerPoint file is read from its XML; its pages are measured on a drawing
of them where LibreOffice is installed, and estimated from the file where it is not.

Where the rules come from, named again in each message:

  AF charts   UK Government Analysis Function, "Data visualisation: charts" (OGL v3.0)
  AF tables   UK Government Analysis Function, "Data visualisation: tables" (OGL v3.0)
  Urban       Urban Institute, Data Visualization Style Guide (Apache-2.0)
  PL          US federal plain language guidelines, "Add useful headings" (public domain, CC0)
  508         US Section508.gov, "How to author PowerPoint for accessibility" (US federal work)
  CFPB        CFPB design system, data visualization guidelines (CC0)
  WCAG        W3C, Web Content Accessibility Guidelines 2.2, criteria 1.1.1, 1.4.1, 1.4.3, 1.4.11
  open-design nexu-io/open-design, deck checklists and the simple-deck layouts (Apache-2.0)
  measured    this pack's measurements of published consulting decks (facts, in the guideline)

A PDF needs pypdf and PDFium (pypdfium2); a PowerPoint file needs python-pptx, and PDFium or poppler's
pdftoppm for the rendered-page measures.
"""
import colorsys
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:          # loaded by path from standards/checks: the text measure sits beside this file
    sys.path.insert(0, str(HERE))
import deck_text as T  # noqa: E402
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
C = "{http://schemas.openxmlformats.org/drawingml/2006/chart}"
EMU = 12700.0

RULES = ("BDECK-TITLE", "BDECK-ONE-IDEA", "BDECK-STORYLINE", "BDECK-NEXT-STEPS", "BDECK-SOURCE",
         "BDECK-PLACEHOLDER", "BDECK-CHART-HEAD", "BDECK-CHART-LABELS", "BDECK-CHART-HONEST",
         "BDECK-CHART-EARNS", "BDECK-HIGHLIGHT", "BDECK-TABLE", "BDECK-FIT", "BDECK-FILL", "BDECK-WORDS",
         "BDECK-TYPE", "BDECK-CONTRAST", "BDECK-GRID", "BDECK-FILE", "BDECK-MATRIX", "BDECK-FIGURE", "BDECK-QUOTE",
         "BDECK-APPENDIX")
SOURCE = {
    "BDECK-TITLE": "plain language guidelines, Add useful headings: a statement heading; Analysis Function charts: the title states the main message",
    "BDECK-ONE-IDEA": "one message a page, as the measured consulting decks keep it",
    "BDECK-STORYLINE": "answer first, then a visible storyline, as the measured consulting decks keep it",
    "BDECK-NEXT-STEPS": "open-design deck checklist: the close asks for something",
    "BDECK-SOURCE": "Analysis Function charts and tables: name the source under the chart or table; Urban Institute style guide: source line",
    "BDECK-PLACEHOLDER": "open-design deck checklist: no placeholder text",
    "BDECK-CHART-HEAD": "Analysis Function charts: a statistical subtitle with the data, the unit and the period; Urban Institute: name the unit once",
    "BDECK-CHART-LABELS": "Analysis Function charts: label lines and bars directly, keep text horizontal; Urban Institute: direct labels",
    "BDECK-CHART-HONEST": "Analysis Function charts: never break a bar axis, no 3D, a pie only with few parts; Urban Institute: bars start at zero, one axis; CFPB: at most five series",
    "BDECK-CHART-EARNS": "a chart shows a pattern figures cannot; open-design deck checklist: one number on a figure page",
    "BDECK-HIGHLIGHT": "one highlight on what the title is about, as the measured consulting decks keep it; WCAG 2.2, 1.4.1",
    "BDECK-TABLE": "Analysis Function tables: right-align numbers and their headings, one precision a column, units in the heading, no merged cells or blank rows; Section 508: a header row",
    "BDECK-FIT": "text stays inside its box (Section 508, readable text)",
    "BDECK-FILL": "the density preset; published consulting decks fill about four fifths of the body",
    "BDECK-WORDS": "the density preset; published consulting decks carry 80 to 170 words a page",
    "BDECK-TYPE": "the density preset; WCAG 2.2 large-text sizes",
    "BDECK-CONTRAST": "WCAG 2.2, 1.4.3 (text 4.5:1, large text 3:1) and 1.4.11 (graphics 3:1)",
    "BDECK-GRID": "the title and the running line at one position on every page, as the measured consulting decks keep them",
    "BDECK-FILE": "Section 508, How to author PowerPoint for accessibility; CFPB: alternative text of at most 250 characters; WCAG 2.2, 1.1.1 and 2.4.2",
    "BDECK-MATRIX": "Analysis Function charts: when labelling axes always use horizontal text, and label the marks directly; one highlight on what the title is about; WCAG 2.2, 1.4.1: the highlight is named, not only shaded",
    "BDECK-FIGURE": "Urban Institute style guide: a figure carries its title, its source and its notes; Section 508 and WCAG 2.2, 1.1.1: alternative text that says what the picture shows; the density preset for its size",
    "BDECK-QUOTE": "open-design simple-deck checklist: one quote per deck, and its quote layout: one quote, one attribution; the density preset for its length",
    "BDECK-APPENDIX": "backup pages stand behind the close, in an appendix of their own count, as the measured consulting decks keep them; Section 508: every slide keeps its title and its place in the reading order",
}

KINDS = ("cover", "summary", "agenda", "section", "chart", "figures", "comparison", "table", "process", "timeline",
         "text", "matrix", "figure", "quote", "next-steps", "closing", "appendix")
CONTENT = ("summary", "chart", "figures", "comparison", "table", "process", "timeline", "text", "matrix", "figure", "quote",
           "next-steps", "content")
RUNNING = ("deck title", "page number", "section", "organisation", "logo", "footer", "slide number", "date")
AXES = ("x axis", "x low", "x high", "y axis", "y low", "y high")
QUADRANTS = ("quadrant top left", "quadrant top right", "quadrant bottom left", "quadrant bottom right")
# Words set at an exhibit's own size, as a chart's labels are: they are held to the type floor, not to the body's size.
SMALL_PRINT = RUNNING + ("source", "chart head", "table head", "series label", "caption", "item label") + AXES
QUOTE_MARKS = "\"'“”„‟‘’‚«»‹›「」❝❞"
PICTURE_FILE = re.compile(r"\.(png|jpe?g|gif|bmp|tiff?|svg|webp|pdf|pptx|docx|xlsx)$", re.I)
# A title that is only one of these says what kind of page it is, not what the page says.
PAGE_WORDS = {"agenda", "summary", "executive summary", "overview", "introduction", "background", "contents",
              "key figures", "key numbers", "figures", "figure", "chart", "table", "comparison", "process", "timeline",
              "matrix", "quote", "backup",
              "roadmap", "next steps", "conclusion", "conclusions", "appendix", "results", "findings",
              "recommendation", "recommendations", "discussion", "questions", "thank you", "update", "status"}
FILLER = re.compile(
    r"^(text|title|subtitle|label|heading|caption|click to (add|edit) .*|your (text|title|name) here|insert .*|"
    r"placeholder|lorem ipsum.*|todo.*|tbd|tba|xxx+|source:?|source: ?(tbd|tba|xxx+|todo.*)?)$", re.I)
# The labels a charting tool writes when nobody named the thing.
CHART_FILLER = re.compile(r"^(value|values|measure|series ?\d+|category ?\d+|data|name|label ?\d*)$", re.I)
INSERT = re.compile(r"\[[^\]]{0,40}\]|\{\{.*?\}\}|<[a-z][a-z _-]{1,30}>|lorem ipsum|\bxxx+\b|\btodo\b|\[\s*['\"].*['\"]\s*\]|\{\s*['\"].*\}", re.I)
DULL_NAMES = re.compile(r"^(deck|presentation|slides?|untitled|output|document|file|new|test|draft|final|copy)[ _-]?\d*$", re.I)
STOP = {"the", "and", "for", "with", "from", "that", "this", "its", "per", "all", "are", "was", "has", "not", "but"}
NUMBER = re.compile(r"[+\-−–]?\(?\d[\d.,'’   ]*\)?\s?%?")

NEEDS = ("nothing was checked: this Python lacks a package the check reads the deck with (%s) and uv is not installed to "
         "fetch it. Install them once, python3 -m pip install python-pptx pillow pypdfium2 pypdf, and run the same check again")
PIECE = "/BusinessDeck"         # where deck_build.py keeps a PDF's description of its pages (the page-piece dictionary)


def _through_uv():
    """Without python-pptx no rule can read a deck. When the pack check itself is what is running and uv is
    installed, the whole check runs again through uv, which fetches the packages into its own cache: the agent,
    and the plugin's Stop hook with the system's Python, get a real verdict instead of a check that read
    nothing. Returns only when that cannot be done."""
    if os.path.basename(sys.argv[0] if sys.argv else "") != "packcheck.py" or os.environ.get("BDECK_UV") or not shutil.which("uv"):
        return
    os.environ["BDECK_UV"] = "1"
    sys.stdout.flush()
    os.execvp("uv", ["uv", "run", "--quiet", "--no-project", "--with", "python-pptx", "--with", "pillow", "--with", "pypdfium2",
                     "--with", "pypdf", "python3"] + sys.argv)
_CACHE = {}


def _density():
    for folder in (HERE.parent / "business-deck", HERE / "business-deck"):
        path = folder / "density.json"
        if path.is_file():
            return json.loads(path.read_text())
    raise RuntimeError("could not find the pack's density.json beside the check")


# ---------------------------------------------------------------- colour


def _rgb(hexcode):
    h = (hexcode or "").strip().lstrip("#")
    if len(h) == 8:
        h = h[2:]
    if not re.fullmatch(r"[0-9A-Fa-f]{6}", h):
        return None
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _lum(c):
    ch = []
    for v in c:
        v = v / 255.0
        ch.append(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]


def contrast(fg, bg):
    a, b = _lum(fg), _lum(bg)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def _chroma(c):
    return colorsys.rgb_to_hsv(*(v / 255.0 for v in c))[1]


# ---------------------------------------------------------------- reading the file


class Para:
    __slots__ = ("text", "size", "pitch", "after", "indent", "spacing", "colour", "bold", "italic", "level", "bullet")


class Text:
    """One text shape (or table cell) with everything its text inherits resolved."""

    def __init__(self):
        self.name = self.text = ""
        self.paras = []
        self.x = self.y = self.w = self.h = None
        self.anchor = "t"
        self.insets = (0.0, 0.0, 0.0, 0.0)
        self.kind = ""          # title, footer, number, body, box, cell
        self.fill = None        # the shape's own solid fill
        self.line = False       # a visible outline
        self.autofit = False
        self.turned = False     # set at an angle, or top to bottom

    @property
    def key(self):
        return self.name.strip().lower()

    def inner_w(self):
        return max(1.0, (self.w or 0) - self.insets[0] - self.insets[2])

    def inner_h(self):
        return max(1.0, (self.h or 0) - self.insets[1] - self.insets[3])

    def lines(self, advance):
        return [T.wrap(p.text, p.size, max(1.0, self.inner_w() - p.indent), advance, p.spacing) for p in self.paras]

    def needed(self, advance):
        return T.height([(p.text, p.size, p.pitch, p.after, p.indent, p.spacing) for p in self.paras], self.inner_w(), advance)

    def extent(self, advance):
        """The rectangle the text itself covers inside its box: (x, y, w, h)."""
        lines = [(ln, p) for p, ls in zip(self.paras, self.lines(advance)) for ln in ls]
        width = max([T.measure(ln, p.size, advance, p.spacing) + p.indent for ln, p in lines] + [0.0])
        height = min(self.needed(advance), self.inner_h() if self.h else 1e9)
        top = self.y + self.insets[1]
        if self.anchor == "b":
            top = self.y + self.h - self.insets[3] - height
        elif self.anchor == "ctr":
            top = self.y + (self.h - height) / 2.0
        return self.x + self.insets[0], top, min(width, self.inner_w()), height


class Chart:
    def __init__(self):
        self.x = self.y = self.w = self.h = 0.0
        self.alt = ""
        self.kinds, self.series, self.categories = [], [], []
        self.legend = self.three_d = False
        self.value_axes = 0
        self.axis_min = None
        self.cat_labels = self.val_labels = self.value_axis_shown = False
        self.rotated = False
        self.sizes = []
        self.gridlines = None
        self.title = ""
        self.plot = (0.04, 0.07, 0.92, 0.78)   # the plot inside the frame, as shares of it
        self.axis_max = None
        self.gap = 150.0


class Table:
    def __init__(self):
        self.x = self.y = self.w = self.h = 0.0
        self.rows = []          # [[Text, ...], ...] with .align and .cell_fill set on each
        self.heights = []
        self.header = False
        self.merged = False


class Picture:
    """A picture on a slide: where it stands, its alternative text, the pixels it is made of and what is cut off it."""

    def __init__(self):
        self.name = self.alt = ""
        self.x = self.y = self.w = self.h = 0.0
        self.px = (0, 0)
        self.crop = (0.0, 0.0, 0.0, 0.0)       # left, top, right, bottom, as shares
        self.ink = 0.5                          # the share of it that stands out from the page's ground

    def __iter__(self):                         # (name, alt), as the file rule reads it
        return iter((self.name, self.alt))


class Mark:
    """A drawn shape without words: a line, a dot or a filled box, by its name."""

    def __init__(self, name, kind, x, y, w, h, colour):
        self.name, self.kind, self.colour = name, kind, colour
        self.x, self.y, self.w, self.h = x, y, w, h

    @property
    def key(self):
        return self.name.strip().lower()

    @property
    def middle(self):
        return self.x + self.w / 2.0, self.y + self.h / 2.0


class Slide:
    def __init__(self):
        self.n = 0
        self.kind = "content"
        self.layout = ""
        self.ground = (255, 255, 255)
        self.title = None
        self.backup = False      # a page behind the appendix divider
        self.texts, self.charts, self.tables, self.pictures = [], [], [], []
        self.rules = []          # drawn lines that stand out from the ground: (x, y, w, h)
        self.marks = []          # every drawn line, dot and filled box, whether it stands out or not
        self.order = []          # the shapes that carry text or an exhibit, in reading order

    def named(self, prefix):
        return [t for t in self.texts if t.key.startswith(prefix)]

    def one(self, name):
        return next((t for t in self.texts if t.key == name), None)

    def content(self):
        return self.kind in CONTENT


def _lst(el):
    if el is None:
        return None
    body = el.find(P + "txBody")
    return body.find(A + "lstStyle") if body is not None else None


def _body_pr(el):
    if el is None:
        return None
    body = el.find(P + "txBody")
    return body.find(A + "bodyPr") if body is not None else None


class Deck:
    printed = False

    def __init__(self, path):
        from pptx import Presentation
        self.path = Path(path)
        self.prs = Presentation(str(path))
        self.author = self.prs.core_properties.author or ""
        self.W, self.H = self.prs.slide_width / EMU, self.prs.slide_height / EMU
        density = _density()
        self.measure = density["measure"]
        ident = self.prs.core_properties.identifier or ""
        found = re.search(r"density=([a-z]+)", ident)
        self.preset = found.group(1) if found and found.group(1) in density["presets"] else density["default"]
        self.named_preset = bool(found)
        self.d = density["presets"][self.preset]
        self._theme()
        self.advance = T.advance_of(self.face)
        master = self.prs.slide_master._element
        tx = master.find(P + "txStyles")
        self.tx = {k: (tx.find(P + k + "Style") if tx is not None else None) for k in ("title", "body", "other")}
        slides = list(self.prs.slides)
        self.slides = [self._slide(s, i, len(slides)) for i, s in enumerate(slides)]
        behind = False
        for s in self.slides:
            s.backup = behind and s.kind != "appendix"
            behind = behind or s.kind == "appendix"

    def _theme(self):
        from pptx.opc.constants import RELATIONSHIP_TYPE as RT
        from lxml import etree
        self.face, self.theme = "Arial", {}
        try:
            root = etree.fromstring(self.prs.slide_master.part.part_related_by(RT.THEME).blob)
        except Exception:
            return
        latin = root.find(".//" + A + "minorFont/" + A + "latin")
        if latin is not None and latin.get("typeface"):
            self.face = latin.get("typeface")
        scheme = root.find(".//" + A + "clrScheme")
        for child in (scheme if scheme is not None else []):
            tag = child.tag.split("}")[1]
            srgb, sys_ = child.find(A + "srgbClr"), child.find(A + "sysClr")
            value = srgb.get("val") if srgb is not None else (sys_.get("lastClr") if sys_ is not None else None)
            if value:
                self.theme[tag] = value
        for alias, real in (("tx1", "dk1"), ("bg1", "lt1"), ("tx2", "dk2"), ("bg2", "lt2")):
            if real in self.theme:
                self.theme[alias] = self.theme[real]

    def colour(self, fill):
        """The RGB of a solidFill element, through the theme where it names a theme colour."""
        if fill is None:
            return None
        srgb = fill.find(A + "srgbClr")
        if srgb is not None:
            return _rgb(srgb.get("val"))
        scheme = fill.find(A + "schemeClr")
        if scheme is not None:
            return _rgb(self.theme.get(scheme.get("val"), ""))
        return None

    def _ground(self, slide):
        for el in (slide._element, slide.slide_layout._element, slide.slide_layout.slide_master._element):
            fill = el.find(P + "cSld/" + P + "bg/" + P + "bgPr/" + A + "solidFill")
            c = self.colour(fill)
            if c is not None:
                return c
        return (255, 255, 255)

    # -- text

    def _chains(self, shape):
        """(the list styles a shape's text inherits from, nearest first; its bodyPr elements likewise)."""
        lists, bodies, kind = [_lst(shape._element)], [_body_pr(shape._element)], "other"
        if getattr(shape, "is_placeholder", False):
            t = str(shape.placeholder_format.type or "")
            if "TITLE" in t and "SUB" not in t:
                kind = "title"
            elif any(k in t for k in ("BODY", "SUBTITLE", "OBJECT")):
                kind = "body"
            base = shape
            for _ in range(2):
                try:
                    base = base._base_placeholder
                except Exception:
                    base = None
                if base is None:
                    break
                lists.append(_lst(base._element))
                bodies.append(_body_pr(base._element))
        lists.append(self.tx.get(kind))
        return [x for x in lists if x is not None], [b for b in bodies if b is not None]

    def _paras(self, tx_body, lists, default_size=18.0, default_colour=None):
        out = []
        dark = _rgb(self.theme.get("dk1", "000000")) or (0, 0, 0)
        for p in tx_body.findall(A + "p"):
            ppr = p.find(A + "pPr")
            level = int(ppr.get("lvl", "0")) if ppr is not None else 0
            sources = ([ppr] if ppr is not None else []) + \
                [x for x in (lst.find(A + "lvl%dpPr" % (level + 1)) for lst in lists) if x is not None]

            def first(fn):
                for src in sources:
                    value = fn(src)
                    if value is not None:
                        return value
                return None

            text, sizes, colours, bolds, spacings, italics = "", [], [], [], [], []
            for node in p:
                tag = node.tag.split("}")[1]
                if tag == "br":
                    text += "\n"
                elif tag in ("r", "fld"):
                    t = node.find(A + "t")
                    text += (t.text or "") if t is not None else ""
                    rpr = node.find(A + "rPr")
                    if rpr is not None and (t is not None and (t.text or "").strip()):
                        if rpr.get("sz"):
                            sizes.append(int(rpr.get("sz")) / 100.0)
                        c = self.colour(rpr.find(A + "solidFill"))
                        if c is not None:
                            colours.append(c)
                        if rpr.get("b") is not None:
                            bolds.append(rpr.get("b") in ("1", "true"))
                        if rpr.get("i") is not None:
                            italics.append(rpr.get("i") in ("1", "true"))
                        if rpr.get("spc") is not None:
                            spacings.append(int(rpr.get("spc")) / 100.0)
            if not text.strip():
                continue
            para = Para()
            para.text, para.level = text, level
            def_rpr = lambda src: src.find(A + "defRPr")  # noqa: E731
            size = first(lambda s: int(def_rpr(s).get("sz")) / 100.0 if def_rpr(s) is not None and def_rpr(s).get("sz") else None)
            para.size = max(sizes) if sizes else (size or default_size)
            pts = first(lambda s: s.find(A + "lnSpc/" + A + "spcPts"))
            pct = first(lambda s: s.find(A + "lnSpc/" + A + "spcPct"))
            para.pitch = int(pts.get("val")) / 100.0 if pts is not None else \
                para.size * 1.2 * (int(pct.get("val")) / 100000.0 if pct is not None else 1.0)
            aft = first(lambda s: s.find(A + "spcAft/" + A + "spcPts"))
            para.after = int(aft.get("val")) / 100.0 if aft is not None else 0.0
            mar = first(lambda s: s.get("marL"))
            para.indent = int(mar) / EMU if mar is not None else 0.0
            bullet = first(lambda s: True if (s.find(A + "buChar") is not None or s.find(A + "buAutoNum") is not None)
                           else (False if s.find(A + "buNone") is not None else None))
            para.bullet = bool(bullet)
            colour = first(lambda s: self.colour(def_rpr(s).find(A + "solidFill")) if def_rpr(s) is not None else None)
            para.colour = colours[0] if colours else (colour or default_colour or dark)
            bold = first(lambda s: (def_rpr(s).get("b") in ("1", "true")) if def_rpr(s) is not None and def_rpr(s).get("b") is not None else None)
            para.bold = bolds[0] if bolds else bool(bold)
            slant = first(lambda s: (def_rpr(s).get("i") in ("1", "true")) if def_rpr(s) is not None and def_rpr(s).get("i") is not None else None)
            para.italic = any(italics) if italics else bool(slant)
            spc = first(lambda s: int(def_rpr(s).get("spc")) / 100.0 if def_rpr(s) is not None and def_rpr(s).get("spc") else None)
            para.spacing = spacings[0] if spacings else (spc or 0.0)
            out.append(para)
        return out

    def _text(self, shape):
        el = shape._element
        body = el.find(P + "txBody")
        if body is None:
            return None
        lists, bodies = self._chains(shape)
        item = Text()
        item.name = shape.name or ""
        item.paras = self._paras(body, lists)
        if not item.paras:
            return None
        item.text = "\n".join(p.text for p in item.paras)
        if None in (shape.left, shape.top, shape.width, shape.height):
            return None
        item.x, item.y, item.w, item.h = (v / EMU for v in (shape.left, shape.top, shape.width, shape.height))

        def attr(name, default):
            for b in bodies:
                if b.get(name) is not None:
                    return b.get(name)
            return default
        item.insets = tuple(int(attr(k, d)) / EMU for k, d in (("lIns", 91440), ("tIns", 45720), ("rIns", 91440), ("bIns", 45720)))
        item.anchor = attr("anchor", "t")
        item.autofit = any(b.find(A + "normAutofit") is not None or b.find(A + "spAutoFit") is not None for b in bodies[:1])
        sp = el.find(P + "spPr")
        frame = sp.find(A + "xfrm") if sp is not None else None
        item.turned = attr("vert", "horz") != "horz" or attr("rot", "0") != "0" or \
            (frame is not None and frame.get("rot") not in (None, "0"))
        if sp is not None:
            item.fill = self.colour(sp.find(A + "solidFill"))
            ln = sp.find(A + "ln")
            item.line = ln is not None and ln.find(A + "solidFill") is not None
        if getattr(shape, "is_placeholder", False):
            t = str(shape.placeholder_format.type or "")
            item.kind = "title" if ("TITLE" in t and "SUB" not in t) else "footer" if "FOOTER" in t else \
                "number" if "SLIDE_NUMBER" in t else "date" if "DATE" in t else "body"
        else:
            item.kind = "box"
        return item

    # -- charts and tables

    def _chart(self, shape):
        info = Chart()
        info.x, info.y, info.w, info.h = (v / EMU for v in (shape.left, shape.top, shape.width, shape.height))
        props = shape._element.find(P + "nvGraphicFramePr/" + P + "cNvPr")
        info.alt = (props.get("descr") or "").strip() if props is not None else ""
        space = shape.chart._chartSpace
        area = space.find(".//" + C + "plotArea")
        info.three_d = space.find(".//" + C + "view3D") is not None
        info.legend = space.find(".//" + C + "legend") is not None
        title = space.find(C + "chart/" + C + "title")
        if title is not None:
            info.title = "".join(t.text or "" for t in title.iter(A + "t")).strip()
        for node in space.iter(A + "bodyPr"):
            if node.get("rot") not in (None, "0") or node.get("vert") not in (None, "horz"):
                info.rotated = True
        info.sizes = [int(n.get("sz")) / 100.0 for n in space.iter() if n.get("sz") and n.tag.endswith("RPr")]
        manual = area.find(C + "layout/" + C + "manualLayout")
        if manual is not None:
            try:
                info.plot = tuple(float(manual.find(C + k).get("val")) for k in ("x", "y", "w", "h"))
            except (AttributeError, TypeError, ValueError):
                pass
        gap = area.find(".//" + C + "gapWidth")
        if gap is not None and gap.get("val"):
            info.gap = float(gap.get("val"))
        shown_axis = False
        for ax in area.findall(C + "valAx"):
            high = ax.find(C + "scaling/" + C + "max")
            if high is not None and info.axis_max is None:
                info.axis_max = float(high.get("val"))
            info.value_axes += 1
            low = ax.find(C + "scaling/" + C + "min")
            if low is not None and info.axis_min is None:
                info.axis_min = float(low.get("val"))
            deleted = ax.find(C + "delete")
            if deleted is None or deleted.get("val") in ("0", "false"):
                pos = ax.find(C + "tickLblPos")
                if pos is None or pos.get("val") != "none":
                    shown_axis = True
            if ax.find(C + "majorGridlines") is not None:
                unit, high = ax.find(C + "majorUnit"), ax.find(C + "scaling/" + C + "max")
                if unit is not None and high is not None and float(unit.get("val")) > 0:
                    info.gridlines = int((float(high.get("val")) - (info.axis_min or 0.0)) / float(unit.get("val"))) + 1
        info.value_axis_shown = shown_axis
        for ax in area.findall(C + "catAx") + area.findall(C + "dateAx"):
            deleted = ax.find(C + "delete")
            pos = ax.find(C + "tickLblPos")
            if (deleted is None or deleted.get("val") in ("0", "false")) and (pos is None or pos.get("val") != "none"):
                info.cat_labels = True
        for plot in area:
            tag = plot.tag.split("}")[1]
            if not tag.endswith("Chart"):
                continue
            if "3D" in tag:
                info.three_d = True
            kind = tag[:-5].replace("3D", "")
            if kind == "bar":
                direction = plot.find(C + "barDir")
                kind = "bar" if direction is not None and direction.get("val") == "bar" else "column"
                grouping = plot.find(C + "grouping")
                if grouping is not None and "tacked" in (grouping.get("val") or ""):
                    kind = "stacked"
            info.kinds.append(kind)
            plot_val = _flag(plot.find(C + "dLbls"), "showVal")
            for ser in plot.findall(C + "ser"):
                s = {"name": "".join(v.text or "" for v in ser.findall(C + "tx//" + C + "v")).strip(), "kind": kind}
                cats = [v.text or "" for v in ser.findall(C + "cat//" + C + "pt/" + C + "v")]
                if cats and not info.categories:
                    info.categories = cats
                values = []
                for pt in ser.findall(C + "val//" + C + "pt"):
                    v = pt.find(C + "v")
                    try:
                        values.append(float(v.text))
                    except (TypeError, ValueError, AttributeError):
                        pass
                s["values"] = values
                sp = ser.find(C + "spPr")
                fill = self.colour(sp.find(A + "solidFill")) if sp is not None else None
                line = self.colour(sp.find(A + "ln/" + A + "solidFill")) if sp is not None else None
                s["colour"] = (line if kind in ("line", "scatter", "radar") else fill) or fill or line
                s["outline"] = line
                s["points"] = {}
                for dpt in ser.findall(C + "dPt"):
                    idx = dpt.find(C + "idx")
                    c = self.colour(dpt.find(C + "spPr/" + A + "solidFill"))
                    if idx is not None and c is not None:
                        s["points"][int(idx.get("val"))] = c
                lbls = ser.find(C + "dLbls")
                ser_val = _flag(lbls, "showVal")
                point_val = any(_flag(d, "showVal") for d in (lbls.findall(C + "dLbl") if lbls is not None else []))
                s["valued"] = bool(ser_val or point_val or (plot_val and ser_val is not False))
                s["named"] = bool(_flag(lbls, "showSerName") or any(
                    _flag(d, "showSerName") for d in (lbls.findall(C + "dLbl") if lbls is not None else [])))
                info.series.append(s)
        info.val_labels = bool(info.series) and all(s["valued"] for s in info.series)
        return info

    def _table(self, shape, ground):
        info = Table()
        info.x, info.y, info.w, info.h = (v / EMU for v in (shape.left, shape.top, shape.width, shape.height))
        table = shape.table
        info.header = bool(table.first_row)
        widths = [c.width / EMU for c in table.columns]
        info.heights = [r.height / EMU for r in table.rows]
        y = info.y
        for r, row in enumerate(table.rows):
            cells, x = [], info.x
            for c, cell in enumerate(row.cells):
                tc = cell._tc
                if tc.get("gridSpan") not in (None, "1") or tc.get("rowSpan") not in (None, "1") \
                        or tc.get("hMerge") or tc.get("vMerge"):
                    info.merged = True
                item = Text()
                item.name, item.kind = "table cell", "cell"
                body = tc.find(A + "txBody")
                item.paras = self._paras(body, [], default_size=18.0) if body is not None else []
                item.text = "\n".join(p.text for p in item.paras)
                pr = tc.find(A + "tcPr")
                get = lambda k, d: int(pr.get(k)) / EMU if pr is not None and pr.get(k) is not None else d  # noqa: E731
                item.insets = (get("marL", 7.2), get("marT", 3.6), get("marR", 7.2), get("marB", 3.6))
                item.x, item.y, item.w, item.h = x, y, widths[c], info.heights[r]
                item.anchor = (pr.get("anchor") if pr is not None else None) or "t"
                item.fill = self.colour(pr.find(A + "solidFill")) if pr is not None else None
                under = self.colour(pr.find(A + "lnB/" + A + "solidFill")) if pr is not None else None
                item.ruled = under is not None and contrast(under, ground) >= 3.0
                first = body.find(A + "p/" + A + "pPr") if body is not None else None
                item.align = (first.get("algn") if first is not None else None) or "l"
                cells.append(item)
                x += widths[c]
            info.rows.append(cells)
            y += info.heights[r]
        return info

    def _picture(self, shape, ground):
        pic = Picture()
        pic.name = shape.name or ""
        props = shape._element.find(P + "nvPicPr/" + P + "cNvPr")
        pic.alt = (props.get("descr") or "").strip() if props is not None else ""
        if None not in (shape.left, shape.top, shape.width, shape.height):
            pic.x, pic.y, pic.w, pic.h = (v / EMU for v in (shape.left, shape.top, shape.width, shape.height))
        rect = shape._element.find(P + "blipFill/" + A + "srcRect")
        if rect is not None:
            pic.crop = tuple(int(rect.get(k, "0")) / 100000.0 for k in ("l", "t", "r", "b"))
        try:
            import io
            from PIL import Image
            with Image.open(io.BytesIO(shape.image.blob)) as im:
                pic.px = im.size
                small = im.convert("RGB").resize((48, max(1, int(48 * im.size[1] / float(im.size[0])))))
            raw = small.tobytes()
            dots = [raw[i:i + 3] for i in range(0, len(raw), 3)]
            pic.ink = sum(1 for p in dots if max(abs(p[i] - ground[i]) for i in range(3)) > 40) / float(len(dots) or 1)
        except Exception:
            try:
                pic.px = tuple(shape.image.size)
            except Exception:
                pass
        return pic

    def _slide(self, slide, index, total):
        out = Slide()
        out.n = index + 1
        out.layout = slide.slide_layout.name or ""
        out.ground = self._ground(slide)
        for shape in slide.shapes:
            if getattr(shape, "has_chart", False):
                chart = self._chart(shape)
                out.charts.append(chart)
                out.order.append(("chart", chart))
                continue
            if getattr(shape, "has_table", False):
                table = self._table(shape, out.ground)
                out.tables.append(table)
                out.order.append(("table", table))
                continue
            if shape._element.tag == P + "cxnSp" and None not in (shape.left, shape.top, shape.width, shape.height):
                c = self.colour(shape._element.find(P + "spPr/" + A + "ln/" + A + "solidFill"))
                box = tuple(v / EMU for v in (shape.left, shape.top, shape.width, shape.height))
                out.marks.append(Mark(shape.name or "", "line", *box, c))
                if c is not None and contrast(c, out.ground) >= 3.0:
                    out.rules.append(box)
                continue
            if shape._element.tag == P + "pic":
                out.pictures.append(self._picture(shape, out.ground))
                continue
            item = self._text(shape) if shape.has_text_frame else None
            if item is None:
                sp = shape._element.find(P + "spPr")
                fill = self.colour(sp.find(A + "solidFill")) if sp is not None else None
                if shape._element.tag == P + "sp" and fill is not None and None not in (shape.left, shape.top, shape.width, shape.height):
                    geom = sp.find(A + "prstGeom")
                    kind = "dot" if geom is not None and geom.get("prst") == "ellipse" else "box"
                    out.marks.append(Mark(shape.name or "", kind, *(v / EMU for v in (shape.left, shape.top, shape.width, shape.height)), fill))
                continue
            out.texts.append(item)
            out.order.append(("text", item))
            if item.kind == "title" and out.title is None:
                out.title = item
        name = (slide._element.find(P + "cSld").get("name") or "").strip().lower()
        layout = out.layout.strip().lower().replace(" ", "-")
        if name in KINDS:
            out.kind = name
        elif layout in KINDS:
            out.kind = layout
        elif index == 0:
            out.kind = "cover"
        elif index == total - 1 and not out.charts and not out.tables:
            out.kind = "closing"
        else:
            out.kind = "chart" if out.charts else "table" if out.tables else "content"
        return out


def _flag(parent, tag):
    """True or False when the element switches a data-label part on or off, None when it does not say."""
    if parent is None:
        return None
    node = parent.find(C + tag)
    if node is None:
        return None
    return node.get("val") in ("1", "true")


# ---------------------------------------------------------------- the deck as a PDF


class NotADeck(Exception):
    """A PDF that deck_build.py did not write: it carries no description of its pages."""


class PageText(Text):
    """A text on a printed page: its box and its styles as the builder set them; its lines, its size and its
    colour as the page shows them."""

    def __init__(self):
        super().__init__()
        self.real = None        # one entry a paragraph: the lines it takes on the page, None when its words are not there
        self.ink = None         # the rectangle its letters cover on the page: (x0, y0, x1, y1)
        self.align = "l"

    def lines(self, advance):
        planned = super().lines(advance)
        if not self.real:
            return planned
        out = []
        for p, plan, real in zip(self.paras, planned, self.real):
            out.append(plan if real is None or real == len(plan) else [p.text] + [""] * (real - 1))
        return out

    def needed(self, advance):
        if not self.real or any(r is None for r in self.real):
            return super().needed(advance)
        total, after = 0.0, 0.0
        for p, real in zip(self.paras, self.real):
            total += real * p.pitch + p.after
            after = p.after
        return total - after


def _letters(text):
    """A text as the page's letters spell it: no spaces, no line ends, no bullet and no hyphen. A word broken at
    its hyphen at a line's end is read back with a mark in the hyphen's place (PDFium's U+0002), so hyphens are
    left out on both sides: "two-shift" set over two lines is the same words."""
    return re.sub(r"[\s\u0000-\u001f\u00a0\u00ad\u200b\u2022\u2010\u2011\uFFFE\uFFFF-]+", "", text or "")


def _most(values):
    return max(set(values), key=values.count) if values else None


class PrintedDeck:
    """A deck as a PDF: the description deck_build.py wrote into the file, held against the pages as printed."""
    printed = True

    def __init__(self, path):
        self.path = Path(path)
        data = self._description()
        density = _density()
        self.measure = density["measure"]
        self.W, self.H = (float(v) for v in data["page"])
        found = re.search(r"density=([a-z]+)", str(data.get("mark") or ""))
        self.preset = found.group(1) if found and found.group(1) in density["presets"] else density["default"]
        self.named_preset = bool(found)
        self.d = density["presets"][self.preset]
        self.face = data.get("face") or "Arial"
        self.theme = dict(data.get("theme") or {})
        self.advance = float(data.get("advance") or T.advance_of(self.face))
        self.slides = [self._slide(raw) for raw in data.get("slides") or []]
        behind = False
        for s in self.slides:
            s.backup = behind and s.kind != "appendix"
            behind = behind or s.kind == "appendix"
        self._read_pages()

    def _description(self):
        from pypdf import PdfReader
        try:
            reader = PdfReader(str(self.path))
            root = reader.trailer["/Root"]
            piece = root.get("/PieceInfo")
            own = piece.get_object().get(PIECE) if piece is not None else None
            data = json.loads(own.get_object()["/Private"].get_object().get_data().decode("utf-8")) if own is not None else None
            info = reader.metadata
            self.file_title = (info.title if info else "") or ""
            self.author = (info.author if info else "") or ""
            self.file_language = str(root.get("/Lang") or "")
            self._marked = bool(reader.outline) or "/PageLabels" in root
        except Exception as error:
            raise NotADeck("%s could not be read as a PDF (%s)" % (self.path.name, str(error)[:80]))
        if not isinstance(data, dict) or not isinstance(data.get("slides"), list) or not data.get("page"):
            raise NotADeck("%s was not written by this pack's builder: it carries no description of its pages, so no rule can "
                           "read it. Write the deck as data and build it: python3 <skill folder>/scripts/deck_build.py "
                           "\"<name>.deck.json\" \"%s\"" % (self.path.name, self.path.name))
        return data

    # -- what the builder set

    def _text(self, raw, cell=False):
        item = PageText()
        item.name, item.kind = ("table cell", "cell") if cell else (raw.get("name") or "", raw.get("kind") or "box")
        item.x, item.y, item.w, item.h = (float(raw[k]) for k in ("x", "y", "w", "h"))
        item.anchor, item.align = ("ctr" if cell else raw.get("anchor") or "t"), raw.get("align") or "l"
        item.insets = tuple(float(v) for v in raw.get("insets") or (0, 0, 0, 0))
        for p in raw.get("paras") or []:
            if not str(p.get("text") or "").strip():
                continue
            para = Para()
            para.text, para.level = str(p["text"]), int(p.get("level") or 0)
            para.size, para.pitch, para.after = float(p["size"]), float(p["pitch"]), float(p.get("after") or 0)
            para.indent, para.spacing = float(p.get("indent") or 0), float(p.get("spacing") or 0)
            para.colour = _rgb(p.get("colour")) or (0, 0, 0)
            para.bold, para.italic, para.bullet = bool(p.get("bold")), False, bool(p.get("bullet"))
            item.paras.append(para)
        item.text = "\n".join(p.text for p in item.paras)
        return item

    def _slide(self, raw):
        out = Slide()
        out.n, out.layout = int(raw["n"]), raw.get("layout") or ""
        out.kind = raw.get("kind") if raw.get("kind") in KINDS else "content"
        out.ground = _rgb(raw.get("ground")) or (255, 255, 255)
        for it in raw.get("items") or []:
            kind = it.get("t")
            if kind == "text":
                item = self._text(it)
                if not item.paras:
                    continue
                out.texts.append(item)
                out.order.append(("text", item))
                if item.kind == "title" and out.title is None:
                    out.title = item
            elif kind == "chart":
                chart = Chart()
                chart.x, chart.y, chart.w, chart.h = (float(it[k]) for k in ("x", "y", "w", "h"))
                chart.alt = (it.get("alt") or "").strip()
                chart.kinds, chart.categories = list(it.get("kinds") or []), [str(c) for c in it.get("categories") or []]
                chart.legend, chart.value_axes = bool(it.get("legend")), 1
                chart.axis_min, chart.axis_max = it.get("axis_min"), it.get("axis_max")
                chart.cat_labels, chart.sizes = True, [float(z) for z in it.get("sizes") or []]
                chart.plot, chart.gap = tuple(it.get("plot") or chart.plot), float(it.get("gap") or chart.gap)
                for s in it.get("series") or []:
                    chart.series.append({"name": str(s.get("name") or ""), "kind": s.get("kind"), "values": [float(v) for v in s.get("values") or []],
                                         "colour": _rgb(s.get("colour")), "outline": _rgb(s.get("outline")),
                                         "points": {int(k): _rgb(v) for k, v in (s.get("points") or {}).items()},
                                         "valued": bool(s.get("valued")), "named": bool(s.get("named"))})
                chart.val_labels = bool(chart.series) and all(s["valued"] for s in chart.series)
                out.charts.append(chart)
                out.order.append(("chart", chart))
            elif kind == "table":
                table = Table()
                table.x, table.y, table.w, table.h = (float(it[k]) for k in ("x", "y", "w", "h"))
                table.heights, table.header = [float(h) for h in it.get("heights") or []], bool(it.get("header"))
                for row in it.get("rows") or []:
                    cells = []
                    for raw_cell in row:
                        cell = self._text(raw_cell, cell=True)
                        cell.fill = _rgb(raw_cell.get("fill"))
                        under = _rgb(raw_cell.get("under"))
                        cell.ruled = under is not None and contrast(under, out.ground) >= 3.0
                        cells.append(cell)
                    table.rows.append(cells)
                out.tables.append(table)
                out.order.append(("table", table))
            elif kind == "picture":
                pic = Picture()
                pic.name, pic.alt = it.get("name") or "", (it.get("alt") or "").strip()
                pic.x, pic.y, pic.w, pic.h = (float(it[k]) for k in ("x", "y", "w", "h"))
                pic.px = tuple(it.get("px") or (0, 0))
                out.pictures.append(pic)
            elif kind == "mark":
                colour = _rgb(it.get("colour"))
                box = tuple(float(it[k]) for k in ("x", "y", "w", "h"))
                out.marks.append(Mark(it.get("name") or "", it.get("kind") or "box", *box, colour))
                if it.get("kind") == "line" and colour is not None and contrast(colour, out.ground) >= 3.0:
                    out.rules.append(box)
        return out

    # -- what the pages show

    def _read_pages(self):
        """Every page drawn as a picture, every letter on it with its place and size, and every run of text in
        the order the page was written, with its place, size and colour. Then each paragraph of the description
        is found among the page's runs: its lines, size and colour become the page's own, and words that are not
        on the page are known to be missing."""
        import ctypes
        import pypdfium2 as pdfium
        import pypdfium2.raw as raw
        width = int(self.measure.get("render_width", 480))
        self.file_problems, pages = [], []
        doc = pdfium.PdfDocument(str(self.path))
        x, y = ctypes.c_double(), ctypes.c_double()
        l, r, b, t = (ctypes.c_double() for _ in range(4))
        red, green, blue, alpha = (ctypes.c_uint() for _ in range(4))
        matrix = raw.FS_MATRIX()
        for page in doc:
            pw, ph = page.get_width(), page.get_height()
            k = self.W / float(pw)
            image = page.render(scale=width / float(pw)).to_pil().convert("RGB")
            tp = page.get_textpage()
            glyphs = []
            for i in range(tp.count_chars()):
                code = raw.FPDFText_GetUnicode(tp.raw, i)
                if code <= 32 or code in (0xA0, 0xAD, 0x2022, 0xFFFE, 0xFFFF) or raw.FPDFText_IsGenerated(tp.raw, i) == 1:
                    continue
                if not raw.FPDFText_GetCharOrigin(tp.raw, i, ctypes.byref(x), ctypes.byref(y)):
                    continue
                raw.FPDFText_GetCharBox(tp.raw, i, ctypes.byref(l), ctypes.byref(r), ctypes.byref(b), ctypes.byref(t))
                size = raw.FPDFText_GetFontSize(tp.raw, i)
                if raw.FPDFText_GetMatrix(tp.raw, i, ctypes.byref(matrix)):
                    size *= abs(matrix.a * matrix.d - matrix.b * matrix.c) ** 0.5
                raw.FPDFText_GetFillColor(tp.raw, i, ctypes.byref(red), ctypes.byref(green), ctypes.byref(blue), ctypes.byref(alpha))
                glyphs.append((chr(code), l.value * k, (ph - t.value) * k, r.value * k, (ph - b.value) * k, x.value * k,
                               (ph - y.value) * k, round(size * k, 1), (red.value, green.value, blue.value)))
            # The runs of text as the page's own content lists them: the order they were written in, which a
            # reader's sorting of the letters into lines does not keep where a large figure stands over small print.
            runs, buffer = [], ctypes.create_string_buffer(4096)
            for obj in page.get_objects(filter=(raw.FPDF_PAGEOBJ_TEXT,), max_depth=6):
                count = raw.FPDFTextObj_GetText(obj.raw, tp.raw, ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ushort)), 4096)
                words = _letters(buffer.raw[:max(0, min(count, 4096) - 2)].decode("utf-16-le", "ignore")) if count else ""
                if not words:
                    continue
                size = ctypes.c_float()
                raw.FPDFTextObj_GetFontSize(obj.raw, ctypes.byref(size))
                scale = 1.0
                if raw.FPDFPageObj_GetMatrix(obj.raw, ctypes.byref(matrix)):
                    scale = abs(matrix.a * matrix.d - matrix.b * matrix.c) ** 0.5
                raw.FPDFPageObj_GetFillColor(obj.raw, ctypes.byref(red), ctypes.byref(green), ctypes.byref(blue), ctypes.byref(alpha))
                left, bottom, right, top = obj.get_bounds()
                runs.append((words, left * k, (ph - top) * k, right * k, (ph - bottom) * k, (ph - matrix.f) * k,
                             round(size.value * scale * k, 1), (red.value, green.value, blue.value)))
            pages.append({"image": image, "chars": [(g[5], g[6], g[7]) for g in glyphs], "glyphs": glyphs, "runs": runs})
            tp.close()
            page.close()
        doc.close()
        if len(pages) != len(self.slides):
            self.file_problems.append("the PDF has %d pages and describes %d; build it again from its data" % (len(pages), len(self.slides)))
            self._rendered = None
            return
        self._rendered = pages
        for slide, page in zip(self.slides, pages):
            if not page["glyphs"]:
                self.file_problems.append("slide %d carries no text that can be read, searched or copied" % slide.n)
            _hold(slide, page["runs"])
        if not self._marked:
            self.file_problems.append("the PDF has neither bookmarks nor page labels to find a section by")

    def every_text(self, slide):
        return list(slide.texts) + [cell for table in slide.tables for row in table.rows for cell in row if cell.paras]

    def smallest(self, slide):
        """The smallest letter on a page, whoever set it: a chart's labels too."""
        sizes = [g[7] for g in self._rendered[slide.n - 1]["glyphs"]] if self._rendered else []
        return min(sizes) if sizes else None

    def fit_problems(self):
        """Words that are not on the page, words that leave their box sideways, and letters that leave the page."""
        bad = []
        if not self._rendered:
            return bad
        for s in self.slides:
            for item in self.every_text(s):
                gone = [p.text for p, real in zip(item.paras, item.real or []) if real is None]
                if gone:
                    bad.append("slide %d, %r: the words %r are not on the printed page; nothing may be cut off or left out"
                               % (s.n, item.name, gone[0][:40]))
                elif item.ink is not None and (item.ink[0] < item.x - 2.5 or item.ink[2] > item.x + item.w + 2.5):
                    over = max(item.x - item.ink[0], item.ink[2] - item.x - item.w)
                    bad.append("slide %d, %r runs %.0f pt past the side of its box: a word is wider than its column; shorten it"
                               % (s.n, item.name, over))
            off = [g for g in self._rendered[s.n - 1]["glyphs"] if g[1] < -1 or g[2] < -1 or g[3] > self.W + 1 or g[4] > self.H + 1]
            if off:
                bad.append("slide %d prints %d letters past the edge of the page; cut words or split the page" % (s.n, len(off)))
        return bad


def _hold(slide, runs):
    """Find each paragraph of a slide's texts and cells among the page's runs of text, nearest its own box first.
    A run is (letters, x0, y0, x1, y1, baseline, size, colour)."""
    stream = "".join(r[0] for r in runs)
    owner = [n for n, r in enumerate(runs) for _ in r[0]]
    taken = bytearray(len(stream))
    items = list(slide.texts) + [cell for table in slide.tables for row in table.rows for cell in row]
    for item in items:
        item.real, boxes = [], []
        for p in item.paras:
            needle = _letters(p.text)
            best, start = None, 0
            while needle:
                at = stream.find(needle, start)
                if at < 0:
                    break
                if not any(taken[at:at + len(needle)]):
                    first = runs[owner[at]]
                    gx, gy = first[1], first[5]
                    far = max(item.x - gx, 0.0, gx - item.x - item.w) + max(item.y - gy, 0.0, gy - item.y - item.h)
                    if best is None or far < best[0]:
                        best = (far, at)
                    if far == 0:
                        break
                start = at + 1
            if best is None:
                item.real.append(None if needle else 1)
                continue
            taken[best[1]:best[1] + len(needle)] = b"\x01" * len(needle)
            found = [runs[n] for n in sorted(set(owner[best[1]:best[1] + len(needle)]))]
            size = _most([r[6] for r in found for _ in r[0]]) or p.size
            bases = sorted({round(r[5]) for r in found})
            count = 1
            for a, b in zip(bases, bases[1:]):
                if b - a > 0.4 * size:
                    count += 1
            item.real.append(count)
            p.size, p.colour = size, _most([r[7] for r in found for _ in r[0]]) or p.colour
            boxes += found
        if boxes:
            item.ink = (min(r[1] for r in boxes), min(r[2] for r in boxes), max(r[3] for r in boxes), max(r[4] for r in boxes))


def deck_of(path):
    path = Path(path)
    key = (str(path.resolve()), path.stat().st_mtime_ns)
    if key not in _CACHE:
        _CACHE.clear()
        _CACHE[key] = PrintedDeck(path) if path.suffix.lower() == ".pdf" else Deck(path)
    return _CACHE[key]


# ---------------------------------------------------------------- the rendered pages


def _pdf_beside(deck):
    """A drawing of the PowerPoint file's own pages beside it. The PDF the builder hands back is not one: it is
    laid out by a browser, not by the program that opens the file."""
    pdf = deck.path.with_suffix(".pdf")
    if pdf.is_file() and pdf.stat().st_mtime >= deck.path.stat().st_mtime - 2:
        try:
            import pypdfium2 as pdfium
            doc = pdfium.PdfDocument(str(pdf))
            own = (doc.get_metadata_value("Creator") or "").startswith("business-deck/")
            doc.close()
        except Exception:
            own = False
        if not own:
            return pdf
    return None


def _drawn_by_office(deck):
    """The PowerPoint file drawn as a PDF by LibreOffice, where it is installed, into a folder of the check's own."""
    tool = shutil.which("soffice") or shutil.which("libreoffice")
    if not tool:
        return None
    folder = tempfile.mkdtemp(prefix="bdeck-pages-")
    import atexit
    atexit.register(shutil.rmtree, folder, True)
    try:
        subprocess.run([tool, "-env:UserInstallation=file://%s/profile" % folder, "--headless", "--convert-to", "pdf", "--outdir",
                        folder, str(deck.path.resolve())], capture_output=True, text=True, timeout=300)
    except Exception:
        return None
    pdf = Path(folder) / (deck.path.stem + ".pdf")
    return pdf if pdf.is_file() else None


def _pages(deck):
    """What the rendered pages show, one entry a page: {"image": PIL image, "chars": [(x, baseline, size)]}.
    None when there is no fresh PDF beside the deck or nothing here can draw it."""
    if hasattr(deck, "_rendered"):
        return deck._rendered
    deck._rendered = None
    if os.environ.get("BDECK_NO_RENDER"):
        return None
    pdf = _pdf_beside(deck) or _drawn_by_office(deck)
    if pdf is None:
        return None
    width = int(deck.measure.get("render_width", 480))
    pages = []
    try:
        import ctypes
        import pypdfium2 as pdfium
        import pypdfium2.raw as raw
        doc = pdfium.PdfDocument(str(pdf))
        for page in doc:
            pw, ph = page.get_width(), page.get_height()
            image = page.render(scale=width / float(pw)).to_pil().convert("RGB")
            chars = []
            tp = page.get_textpage()
            x, y = ctypes.c_double(), ctypes.c_double()
            for i in range(tp.count_chars()):
                if not raw.FPDFText_GetCharOrigin(tp.raw, i, ctypes.byref(x), ctypes.byref(y)):
                    continue
                code = raw.FPDFText_GetUnicode(tp.raw, i)
                if code in (0, 32, 10, 13, 0xA0):
                    continue
                scale = deck.W / float(pw)
                chars.append((x.value * scale, (ph - y.value) * scale, raw.FPDFText_GetFontSize(tp.raw, i) * scale))
            pages.append({"image": image, "chars": chars})
            tp.close()
            page.close()
        doc.close()
    except Exception:
        pages = []
        tool = shutil.which("pdftoppm")
        if not tool:
            return None
        try:
            from PIL import Image
            with tempfile.TemporaryDirectory(prefix="bdeck-") as tmp:
                subprocess.run([tool, "-png", "-scale-to-x", str(width), "-scale-to-y", "-1", str(pdf), os.path.join(tmp, "p")],
                               check=True, capture_output=True, timeout=180)
                for name in sorted(os.listdir(tmp)):
                    pages.append({"image": Image.open(os.path.join(tmp, name)).convert("RGB").copy(), "chars": None})
        except Exception:
            return None
    if len(pages) != len(deck.slides):
        return None
    deck._rendered = pages
    return pages


def _ink(deck, image, ground):
    """(share of the body band's grid cells that carry ink, the same for the lower half, the ink's bounding box
    in page points or None)."""
    m = deck.measure
    w, h = image.size
    step, cell_ink = int(m["ink_step"]), float(m["cell_ink"])
    cols, rows = m["grid"]["columns"], m["grid"]["rows"]
    left, right = m["band"]["left"] * w, m["band"]["right"] * w
    top, bottom = m["band"]["top"] * h, m["band"]["bottom"] * h
    counts = [[0] * cols for _ in range(rows)]
    totals = [[0] * cols for _ in range(rows)]
    cw, ch = (right - left) / cols, (bottom - top) / rows
    data = image.load()
    gr, gg, gb = ground
    x0 = y0 = 1e9
    x1 = y1 = -1.0
    for y in range(h):
        row = int((y + 0.5 - top) // ch) if top <= y + 0.5 < bottom else -1
        for x in range(w):
            r, g, b = data[x, y]
            inked = abs(r - gr) > step or abs(g - gg) > step or abs(b - gb) > step
            if inked:
                x0, x1, y0, y1 = min(x0, x), max(x1, x + 1), min(y0, y), max(y1, y + 1)
            if row < 0 or not left <= x + 0.5 < right:
                continue
            col = int((x + 0.5 - left) // cw)
            if 0 <= col < cols and 0 <= row < rows:
                totals[row][col] += 1
                counts[row][col] += 1 if inked else 0
    full = [[totals[r][c] and counts[r][c] / float(totals[r][c]) > cell_ink for c in range(cols)] for r in range(rows)]
    share = sum(sum(1 for v in row if v) for row in full) / float(cols * rows)
    low = full[rows // 2:]
    lower = sum(sum(1 for v in row if v) for row in low) / float(cols * len(low))
    k = deck.W / float(w)
    box = (x0 * k, y0 * k, x1 * k, y1 * k) if x1 >= 0 else None
    return share, lower, box


def _text_bands(item, advance):
    """Where a text shape's ink sits: one band a line, as tall as the letters and as wide as the line."""
    out = []
    x, top, w, h = item.extent(advance)
    y = top
    align = getattr(item, "align", "l")
    for p, lines in zip(item.paras, item.lines(advance)):
        for line in lines:
            width = min(T.measure(line, p.size, advance, p.spacing), item.inner_w())
            left = item.x + item.insets[0] + p.indent
            if align == "r":
                left = item.x + item.w - item.insets[2] - width
            elif align == "ctr":
                left = item.x + (item.w - width) / 2.0
            y0 = y + (p.pitch - p.size) / 2.0 + 0.22 * p.size
            if width > 0:
                out.append((left, y0, left + width, y0 + 0.6 * p.size, TEXT_INK))
            y += p.pitch
        y += p.after
    return out


TEXT_INK = 0.45     # the share of a line's letter band that is ink, as a render at this size counts it
RULE_INK = 2.0      # points of height a drawn line is counted at: a thin line still darkens a row of pixels
LINE_INK = 2.0      # points of width a chart line is counted at


def _chart_ink(chart):
    """A chart's marks as rectangles: bars as they stand on the axis, lines as a string of small squares,
    and the band of category labels under the plot. An estimate, for when no rendered page is there."""
    out = []
    px, py, pw, ph = chart.plot
    x0, y0, w, h = chart.x + px * chart.w, chart.y + py * chart.h, pw * chart.w, ph * chart.h
    count = max([len(s["values"]) for s in chart.series] + [len(chart.categories)] + [1])
    values = [v for s in chart.series for v in s["values"]]
    stacked = "stacked" in chart.kinds
    totals = [sum((s["values"][i] if i < len(s["values"]) else 0) for s in chart.series) for i in range(count)]
    low = chart.axis_min if chart.axis_min is not None else min(values + [0.0])
    high = chart.axis_max if chart.axis_max is not None else (max(totals if stacked else values + [1.0]) * 1.1)
    span = (high - low) or 1.0
    kind = chart.kinds[0] if chart.kinds else "column"
    if kind in ("column", "stacked", "bar"):
        groups = 1 if stacked else max(1, len(chart.series))
        step = (h if kind == "bar" else w) / float(count)
        bar = step / (1.0 + chart.gap / 100.0) / groups
        for i in range(count):
            for g in range(groups):
                v = totals[i] if stacked else (chart.series[g]["values"][i] if i < len(chart.series[g]["values"]) else 0)
                size = max(0.0, (v - low) / span)
                start = i * step + (step - bar * groups) / 2.0 + g * bar
                if kind == "bar":
                    out.append((x0, y0 + start, x0 + w * size, y0 + start + bar, 1.0))
                else:
                    out.append((x0 + start, y0 + h * (1 - size), x0 + start + bar, y0 + h, 1.0))
    elif kind in ("line", "area", "scatter", "radar"):
        for s in chart.series:
            pts = [(x0 + (w * i / float(max(1, len(s["values"]) - 1))), y0 + h * (1 - (v - low) / span)) for i, v in enumerate(s["values"])]
            for (ax, ay), (bx, by) in zip(pts, pts[1:]):
                steps = max(1, int(((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5 / LINE_INK))
                for k in range(steps):
                    cx, cy = ax + (bx - ax) * k / float(steps), ay + (by - ay) * k / float(steps)
                    out.append((cx, cy - LINE_INK / 2.0, cx + LINE_INK, cy + LINE_INK / 2.0, 1.0))
    else:
        side = min(w, h)
        out.append((x0 + (w - side) / 2.0, y0 + (h - side) / 2.0, x0 + (w + side) / 2.0, y0 + (h + side) / 2.0, 0.8))
    size = min(chart.sizes) if chart.sizes else 11.0
    if chart.cat_labels and kind != "bar":
        out.append((x0, y0 + h - RULE_INK / 2.0, x0 + w, y0 + h + RULE_INK / 2.0, 1.0))
        out.append((x0, y0 + h + 0.5 * size, x0 + w, y0 + h + 1.1 * size, TEXT_INK * 0.6))
    return out


def _boxes(deck, slide):
    """The rectangles a slide's ink covers, estimated from the file, each with the share of it that is ink:
    text as bands of letters, table cells likewise, charts as their marks."""
    out = []
    for item in slide.texts:
        out += _text_bands(item, deck.advance)
    for table in slide.tables:
        for row in table.rows:
            for cell in row:
                if cell.paras:
                    out += _text_bands(cell, deck.advance)
                if getattr(cell, "ruled", False):
                    out.append((cell.x, cell.y + cell.h - RULE_INK / 2.0, cell.x + cell.w, cell.y + cell.h + RULE_INK / 2.0, 1.0))
    for chart in slide.charts:
        out += _chart_ink(chart)
    for pic in slide.pictures:
        if pic.w and pic.h:
            # a picture's ink is spread over it: a page of text darkens every cell it covers a little
            out.append((pic.x, pic.y, pic.x + pic.w, pic.y + pic.h, max(pic.ink, 0.06)))
    for mark in slide.marks:
        if mark.kind == "dot" and mark.colour is not None and contrast(mark.colour, slide.ground) >= 3.0:
            out.append((mark.x, mark.y, mark.x + mark.w, mark.y + mark.h, 0.8))
    for x, y, w, h in slide.rules:
        out.append((x, y - RULE_INK / 2.0, x + max(w, RULE_INK), y + max(h, RULE_INK / 2.0) + RULE_INK / 2.0, 1.0))
    return out


def _estimate(deck, slide):
    m = deck.measure
    cols, rows = m["grid"]["columns"], m["grid"]["rows"]
    left, right = m["band"]["left"] * deck.W, m["band"]["right"] * deck.W
    top, bottom = m["band"]["top"] * deck.H, m["band"]["bottom"] * deck.H
    cw, ch = (right - left) / cols, (bottom - top) / rows
    boxes = _boxes(deck, slide)
    ink = [[0.0] * cols for _ in range(rows)]
    for x0, y0, x1, y1, density in boxes:
        for r in range(max(0, int((y0 - top) // ch)), min(rows - 1, int((y1 - top) // ch)) + 1):
            for c in range(max(0, int((x0 - left) // cw)), min(cols - 1, int((x1 - left) // cw)) + 1):
                iw = min(x1, left + (c + 1) * cw) - max(x0, left + c * cw)
                ih = min(y1, top + (r + 1) * ch) - max(y0, top + r * ch)
                if iw > 0 and ih > 0:
                    ink[r][c] += iw * ih * density
    full = [[ink[r][c] / (cw * ch) > float(m["cell_ink"]) for c in range(cols)] for r in range(rows)]
    share = sum(sum(1 for v in row if v) for row in full) / float(cols * rows)
    low = full[rows // 2:]
    lower = sum(sum(1 for v in row if v) for row in low) / float(cols * len(low))
    box = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)) if boxes else None
    return share, lower, box


def fill_of(deck):
    """Per slide (share, lower, ink box), and how it was measured."""
    if hasattr(deck, "_fill"):
        return deck._fill
    pages = _pages(deck)
    if pages:
        deck._fill = ([_ink(deck, p["image"], s.ground) for p, s in zip(pages, deck.slides)], "measured on the rendered pages")
    else:
        deck._fill = ([_estimate(deck, s) for s in deck.slides], "estimated from the file, no rendered pages beside it")
    return deck._fill


# ---------------------------------------------------------------- helpers


def words(text):
    return [w for w in re.findall(r"[^\s/|·,;:()\[\]“”\"]+", text or "") if re.search(r"[^\W\d_]", w)]


def is_number(text):
    return bool(NUMBER.fullmatch((text or "").strip()))


THOUSANDS = re.compile(r"[1-9]\d{0,2}(?:[.,'’\u00a0\u202f ]\d{3})+")


def decimals(text, grouped=False):
    """The decimal places a printed number shows. With `grouped`, digits in threes after a separator are read
    as thousands (1,900 has none), which is how a column that also holds 850 means them."""
    core = re.sub(r"[^\d.,'’\u00a0\u202f ]", "", text or "").strip()
    if grouped:
        whole = THOUSANDS.match(core)
        if whole and whole.end() == len(core):
            return 0
        if whole and re.fullmatch(r"[.,]\d+", core[whole.end():]):
            return len(core) - whole.end() - 1
    return len(re.split(r"[.,]", re.sub(r"[^\d.,]", "", core))[-1]) if re.search(r"[.,]\d+$", core) else 0


def clean_title(text):
    return re.sub(r"\s*\(\d+\s*/\s*\d+\)\s*$", "", (text or "").replace("\n", " ")).strip()


def title_case(text):
    """True when most of a title's longer words are capitalised, as in a Headline Set Like This."""
    found = re.findall(r"[^\W\d_][\w'’-]*", text)
    longer = [w for w in found[1:] if len(w) >= 4 and not w.isupper()]
    return len(longer) >= 3 and sum(1 for w in longer if w[0].isupper()) / float(len(longer)) > 0.6


def names_it(title, label, others=()):
    """Does the title name what the label names? A word that sets the label apart from its neighbours (the
    other categories, series or rows) must be in the title; a label with no word of its own must be there whole."""
    def tokens(text):
        return {t for t in re.findall(r"[^\W_]+", (text or "").lower()) if (len(t) >= 3 or re.search(r"\d", t)) and t not in STOP}
    have = tokens(title)

    def named(token):
        return token in have or any(len(token) >= 5 and h.startswith(token[:5]) for h in have)
    mine = tokens(label)
    shared = set()
    for other in others:
        if other != label:
            shared |= tokens(other)
    own = mine - shared
    if own:
        return any(named(t) for t in own)
    return bool(mine) and all(named(t) for t in mine)


def two(value, bound):
    """A measure and its bound as text: two decimals, or three where two would print them the same."""
    return ("%.2f" % value, "%.2f" % bound) if "%.2f" % value != "%.2f" % bound else ("%.3f" % value, "%.3f" % bound)


def head(problems, limit=4):
    return "; ".join(problems[:limit]) + (" (and %d more)" % (len(problems) - limit) if len(problems) > limit else "")


def result(rule, problems, ok):
    if problems:
        return False, "%s [%s]" % (head(problems), SOURCE[rule])
    return True, ok


def all_text(deck, slide):
    """Every string a slide shows: text shapes, table cells, chart series and categories."""
    out = [(t.name, p.text) for t in slide.texts for p in t.paras]
    for table in slide.tables:
        out += [("table", cell.text) for row in table.rows for cell in row if cell.text.strip()]
    for chart in slide.charts:
        out += [("chart series", s["name"]) for s in chart.series]
        out += [("chart category", c) for c in chart.categories]
        if chart.title:
            out.append(("chart title", chart.title))
    return out


def body_texts(slide):
    return [t for t in slide.texts if t.kind not in ("title", "footer", "number", "date") and t.key not in RUNNING]


# ---------------------------------------------------------------- the rules


def rule_title(deck):
    d, bad = deck.d, []
    sizes = set()
    for s in deck.slides:
        if not s.content():
            continue
        if s.title is None:
            bad.append("slide %d has no title" % s.n)
            continue
        text = clean_title(s.title.text)
        count = len(text.split())
        low, high = d["title.min_words"], d["title.max_words"]
        if text.lower().rstrip(".:") in PAGE_WORDS:
            bad.append("slide %d is titled %r, which names the kind of page; write the page's message as a sentence" % (s.n, text))
        elif count < low:
            bad.append("slide %d's title %r is a topic label of %d words; state the page's message in %d to %d words"
                       % (s.n, text[:50], count, low, high))
        elif count > high:
            bad.append("slide %d's title runs to %d words; the %s preset holds %d" % (s.n, count, deck.preset, high))
        if text.endswith(":"):
            bad.append("slide %d's title ends in a colon; finish the sentence" % s.n)
        if title_case(text):
            bad.append("slide %d's title %r is in Title Case; write it in sentence case" % (s.n, text[:50]))
        lines = sum(len(ls) for ls in s.title.lines(deck.advance))
        if lines > d["title.max_lines"]:
            bad.append("slide %d's title takes %d lines; the preset holds %d, cut about %d characters"
                       % (s.n, lines, d["title.max_lines"], int(len(text) * (1 - d["title.max_lines"] / float(lines))) + 1))
        sizes.add(round(s.title.paras[0].size, 1))
    return result("BDECK-TITLE", bad, "every content page is titled with its message, in the %s preset's range" % deck.preset)


def rule_one_idea(deck):
    bad, seen = [], {}
    for s in deck.slides:
        if s.title is not None:
            key = re.sub(r"\W+", " ", s.title.text.lower()).strip()
            if key in seen:
                bad.append("slides %d and %d share the title %r; one message a page, each its own" % (seen[key], s.n, s.title.text[:50]))
            seen.setdefault(key, s.n)
        exhibits = len(s.charts) + len(s.tables) + len(s.pictures) + (1 if s.kind == "matrix" else 0)
        row = len({round(c.y) for c in s.charts}) <= 1 and not s.tables and not s.pictures and s.kind != "matrix"
        if exhibits > 1 and not row:
            bad.append("slide %d holds %d exhibits (charts, tables, pictures); one exhibit a page, or one row of small charts on one scale" % (s.n, exhibits))
    return result("BDECK-ONE-IDEA", bad, "one message and one exhibit a page")


def _sections(deck):
    names = [clean_title(s.title.text) for s in deck.slides if s.kind == "section" and s.title is not None]
    for s in deck.slides:
        if s.kind == "agenda":
            names += [t.paras[0].text for t in s.named("item ") if not t.key.endswith("number")]
    return {n.strip().lower() for n in names if n.strip()}


def page_count(deck):
    """The deck's pages as its author wrote them: a page continued as (2/3) is the same page still."""
    story = [s for s in deck.slides if not s.backup and s.kind != "appendix"]
    more = [s for s in story if s.title is not None and re.search(r"\(([2-9]|\d\d)\s*/\s*\d+\)\s*$", s.title.text)]
    return len(story) - len(more)


def rule_storyline(deck):
    d, bad = deck.d, []
    pages = page_count(deck)
    if pages < d["story.min_pages"]:
        return True, "a deck of %d pages needs no storyline pages (from %d on)" % (pages, d["story.min_pages"])
    kinds = [s.kind for s in deck.slides]
    summaries = [s for s in deck.slides if s.kind == "summary"]
    if not summaries:
        bad.append("a deck of %d pages opens with the answer: add an executive summary page after the cover" % pages)
    if "agenda" not in kinds:
        bad.append("a deck of %d pages shows its storyline: add an agenda page that lists the sections" % pages)
    sections = _sections(deck)
    blocks = [t for s in summaries for t in s.named("block ") if t.key.endswith("label")]
    if summaries and blocks:
        if not 3 <= len(blocks) <= 5:
            bad.append("the executive summary has %d blocks; give it three to five, one a section" % len(blocks))
        unknown = [b.text.strip() for b in blocks if sections and b.text.strip().lower() not in sections]
        if unknown:
            bad.append("the executive summary names %s, which is no section of the deck" % ", ".join(repr(u) for u in unknown[:3]))
    content = [s for s in deck.slides if s.content() and s.kind != "summary" and not s.backup]
    unmarked = [s.n for s in content if not (s.one("section") and s.one("section").text.strip())]
    listed = [t.paras[0].text.strip() for s in deck.slides if s.kind == "agenda" for t in s.named("item ") if not t.key.endswith("number")]
    carried = {}
    for s in content:
        label = s.one("section").text.strip() if s.one("section") else ""
        if label:
            carried.setdefault(label.lower(), (label, s.n))
    if listed and carried:
        empty = [name for name in listed if name.lower() not in carried]
        if empty:
            bad.append("the agenda lists %s, and no page carries that as its section; name the pages' sections as the agenda does"
                       % ", ".join(repr(e) for e in empty[:3]))
        stray = [(label, n) for key, (label, n) in carried.items() if key not in {name.lower() for name in listed}]
        if stray:
            bad.append("slide %d carries the section %r, which the agenda does not list; a page's section is one of the agenda's"
                       % (stray[0][1], stray[0][0]))
    if unmarked and "section" not in kinds:
        bad.append("slides %s carry no section label and no section opens with a divider; mark the storyline on the pages"
                   % ", ".join(str(n) for n in unmarked[:6]))
    # In a short deck the section's name in the running line is mark enough; a long one opens each section on a page of its own.
    if pages >= d["story.divider_pages"]:
        opened = {clean_title(s.title.text).strip().lower() for s in deck.slides if s.kind == "section" and s.title is not None}
        named = []
        for s in content:
            label = s.one("section").text.strip() if s.one("section") else ""
            if label and label.lower() not in opened and label not in named:
                named.append(label)
        if named:
            bad.append("a deck of %d pages opens each section with a divider page; %s has none (from %d pages on)"
                       % (pages, ", ".join(repr(n) for n in named[:4]), d["story.divider_pages"]))
    return result("BDECK-STORYLINE", bad, "the answer comes first and the storyline shows: summary, agenda, sections")


def rule_next_steps(deck):
    d, bad = deck.d, []
    steps = [s for s in deck.slides if s.kind == "next-steps"]
    body = [s for s in deck.slides if s.kind not in ("closing", "cover", "appendix") and not s.backup]
    if page_count(deck) >= d["story.min_pages"]:
        if not steps:
            bad.append("the deck ends without next steps; close on a page of actions, each with its owner and date")
        elif body and body[-1].kind != "next-steps":
            bad.append("slide %d follows the next steps; they are the last page before the closing" % body[-1].n)
    for s in steps:
        if not s.tables:
            bad.append("slide %d lists next steps without a table of action, owner and date" % s.n)
            continue
        for r, row in enumerate(s.tables[0].rows[1:], start=1):
            cells = [c.paras[0].text.strip() if c.paras else "" for c in row]
            if len(cells) < 3 or not all(cells[:3]):
                bad.append("slide %d, step %d has no %s; every action has an owner and a date"
                           % (s.n, r, "owner" if len(cells) > 1 and not cells[1] else "date" if len(cells) > 2 and not cells[2] else "action"))
            elif not re.search(r"\d", cells[2]):
                bad.append("slide %d, step %d is due %r; give a date" % (s.n, r, cells[2]))
    return result("BDECK-NEXT-STEPS", bad, "the deck closes on actions with owners and dates" if steps else "no next-steps page to check")


def rule_source(deck):
    bad = []
    for s in deck.slides:
        if s.kind == "next-steps" or not (s.charts or s.tables or s.kind == "figure"):
            continue
        source = s.one("source") or next((t for t in s.texts if re.match(
            r"(sources?|källa|quelle|fuente|fonte|bron|kilde|lähde|źródło)\b", t.text.strip(), re.I)), None)
        what = "chart" if s.charts else "table" if s.tables else "figure"
        if source is None or not source.text.strip():
            bad.append("slide %d shows a %s with no source line under it" % (s.n, what))
        elif FILLER.match(source.text.strip()) or INSERT.search(source.text):
            bad.append("slide %d's source line reads %r; name where the figures come from" % (s.n, source.text.strip()[:40]))
    return result("BDECK-SOURCE", bad, "every chart, table and figure names its source")


def rule_placeholder(deck):
    bad = []
    for s in deck.slides:
        for where, text in all_text(deck, s):
            t = text.strip()
            if not t:
                if where == "chart series" and len([x for c in s.charts for x in c.series]) > 1:
                    bad.append("slide %d has a chart series with no name" % s.n)
                continue
            dull = FILLER.match(t) or (where.startswith("chart") and CHART_FILLER.match(t)) \
                or (where.strip().lower() == "chart head" and CHART_FILLER.match(t))
            if dull and where.strip().lower() not in ("source",):
                bad.append("slide %d, %s reads %r, a placeholder; write the real words or remove it" % (s.n, where, t[:30]))
            elif INSERT.search(t):
                bad.append("slide %d, %s still holds filler text: %r" % (s.n, where, INSERT.search(t).group(0)[:30]))
    return result("BDECK-PLACEHOLDER", bad, "no placeholder or filler text on any page")


def _chart_head(slide, chart):
    named = slide.one("chart head")
    if named is not None:
        return named.text.strip()
    if chart.title:
        return chart.title
    above = [t for t in slide.texts if t.kind != "title" and t.key not in RUNNING and t.y is not None
             and chart.y - 40 <= t.y + t.h <= chart.y + 4 and t.x < chart.x + chart.w and t.x + t.w > chart.x]
    return above[-1].text.strip() if above else ""


def rule_chart_head(deck):
    bad = []
    for s in deck.slides:
        for chart in s.charts:
            text = _chart_head(s, chart)
            parts = [p for p in re.split(r"\s*[,;·|]\s*|\s+[–—-]\s+", text) if p.strip()]
            if not text:
                bad.append("slide %d's chart has no head; above it, name the measure, its unit and the period" % s.n)
            elif len(parts) < 3:
                bad.append("slide %d's chart head reads %r; name the measure, its unit and the period, with commas between" % (s.n, text[:50]))
    return result("BDECK-CHART-HEAD", bad, "every chart names its measure, unit and period once")


def rule_chart_labels(deck):
    d, bad = deck.d, []
    for s in deck.slides:
        texts = {t.text.strip().lower() for t in s.texts}
        for chart in s.charts:
            pie = "pie" in chart.kinds or "doughnut" in chart.kinds
            if not chart.cat_labels and not pie:
                bad.append("slide %d's chart does not label its categories" % s.n)
            if not chart.val_labels and not chart.value_axis_shown:
                bad.append("slide %d's chart shows no values: label the marks or show the value axis" % s.n)
            count = len(chart.series)
            if 1 < count <= d["legend.direct_max"]:
                if chart.legend:
                    bad.append("slide %d's chart has a legend for %d series; up to %d are named on the marks, with no legend"
                               % (s.n, count, d["legend.direct_max"]))
                unnamed = [x["name"] for x in chart.series if not x["named"] and x["name"].strip().lower() not in texts]
                if unnamed and not chart.legend:
                    bad.append("slide %d's chart does not name the series %s on or beside its marks" % (s.n, ", ".join(repr(u) for u in unnamed[:3])))
            elif count > d["legend.direct_max"] and not chart.legend:
                unnamed = [x["name"] for x in chart.series if not x["named"] and x["name"].strip().lower() not in texts]
                if unnamed:
                    bad.append("slide %d's chart has %d series and neither labels nor a legend name them" % (s.n, count))
            if chart.rotated:
                bad.append("slide %d's chart sets text at an angle; keep every label horizontal" % s.n)
    return result("BDECK-CHART-LABELS", bad, "categories, values and series are labelled on the charts, horizontally")


def rule_chart_honest(deck):
    d, bad = deck.d, []
    for s in deck.slides:
        for chart in s.charts:
            if chart.three_d:
                bad.append("slide %d's chart is drawn in 3D; draw it flat" % s.n)
            if any(k in ("bar", "column", "stacked", "area") for k in chart.kinds) and chart.axis_min is not None and chart.axis_min > 0:
                bad.append("slide %d's bars start at %g; a bar's length is its value, start the axis at zero" % (s.n, chart.axis_min))
            if chart.value_axes > 1 and "scatter" not in chart.kinds:
                bad.append("slide %d's chart has two value axes; use one scale, or two charts" % s.n)
            if "pie" in chart.kinds or "doughnut" in chart.kinds:
                parts = max([len(x["values"]) for x in chart.series] + [0])
                if parts > d["pie.max_parts"]:
                    bad.append("slide %d's pie has %d parts; a pie reads up to %d, use bars" % (s.n, parts, d["pie.max_parts"]))
            if len(chart.series) > d["series.max"]:
                bad.append("slide %d's chart has %d series; the %s preset holds %d" % (s.n, len(chart.series), deck.preset, d["series.max"]))
            if chart.gridlines is not None and chart.gridlines > d["gridlines.max"]:
                bad.append("slide %d's chart draws %d gridlines; keep to %d light ones or none" % (s.n, chart.gridlines, d["gridlines.max"]))
    return result("BDECK-CHART-HONEST", bad, "bars start at zero, one scale, no 3D, no crowded pie")


def rule_chart_earns(deck):
    d, bad = deck.d, []
    for s in deck.slides:
        beside = " ".join(p.text for t in s.texts if t.kind != "title" for p in t.paras)
        printed = set(re.findall(r"\d+(?:[.,]\d+)?", beside))
        for chart in s.charts:
            values = [v for x in chart.series for v in x["values"]]
            if len(values) < d["chart.min_points"]:
                bad.append("slide %d's chart plots %d values; fewer than %d are key figures, not a chart"
                           % (s.n, len(values), d["chart.min_points"]))
                continue
            shown = {("%g" % v) for v in values} | {("%.1f" % v) for v in values}
            if values and len(values) <= 4 and all(("%g" % v) in printed or ("%.1f" % v) in printed for v in values):
                bad.append("slide %d's chart only repeats the figures printed beside it (%s); keep the figures or chart something more"
                           % (s.n, ", ".join(sorted(shown & printed))[:40]))
    return result("BDECK-CHART-EARNS", bad, "every chart shows more than the figures beside it")


def _highlights(deck, slide, chart):
    """The labels of the marks a chart singles out, and the colours that compete with them."""
    # The highlight is the theme's accent, or its ink where the look highlights in full ink against greys.
    strong = {c for c in (_rgb(deck.theme.get("accent1", "")), _rgb(deck.theme.get("dk1", ""))) if c is not None}
    marks, loud = [], []
    if len(chart.series) == 1:
        s = chart.series[0]
        count = len(s["values"])
        colours = [s["points"].get(i, s["colour"]) for i in range(count)]
        known = [c for c in colours if c is not None]
        if known:
            common = max(set(known), key=known.count)
            marks = [chart.categories[i] if i < len(chart.categories) else "mark %d" % (i + 1)
                     for i, c in enumerate(colours) if c is not None and c != common]
    else:
        for s in chart.series:
            c = s["colour"]
            if c is None:
                continue
            if c in strong:
                marks.append(s["name"])
            elif _chroma(c) > 0.25:
                loud.append(s["name"])
    return marks, loud


def rule_highlight(deck):
    bad = []
    for s in deck.slides:
        title = s.title.text if s.title is not None else ""
        for chart in s.charts:
            marks, loud = _highlights(deck, s, chart)
            if len(marks) > 1:
                bad.append("slide %d's chart highlights %d marks (%s); highlight the one the title is about"
                           % (s.n, len(marks), ", ".join(marks[:3])))
            elif marks and not names_it(title, marks[0], chart.categories if len(chart.series) == 1 else [x["name"] for x in chart.series]):
                bad.append("slide %d's chart highlights %r, which the title does not name; highlight what the title says, or say it"
                           % (s.n, marks[0]))
            if loud:
                bad.append("slide %d's chart colours %s as well; every mark but the highlight is a neutral grey" % (s.n, ", ".join(loud[:3])))
        for table in s.tables:
            body = table.rows[1:]
            if not body:
                continue
            rows = [r for r in body if r and all(c.fill is not None and c.fill != s.ground for c in r)]
            cols = [c for c in range(len(body[0])) if all(len(r) > c and r[c].fill is not None and r[c].fill != s.ground for r in body)]
            if rows and len(rows) == len(body):
                rows = []
            marked = [r[0].text.strip() for r in rows] if rows else \
                [table.rows[0][c].text.strip() for c in cols if c < len(table.rows[0])]
            others = [r[0].text.strip() for r in body] if rows else [c.text.strip() for c in table.rows[0]]
            if len(marked) > 1:
                bad.append("slide %d's table marks %d rows or columns; mark the one the title is about" % (s.n, len(marked)))
            elif marked and not names_it(title, marked[0], others):
                bad.append("slide %d's table marks %r, which the title does not name" % (s.n, marked[0][:40]))
    return result("BDECK-HIGHLIGHT", bad, "at most one highlight a chart or table, on what the title names")


def rule_table(deck):
    d, bad = deck.d, []
    for s in deck.slides:
        for table in s.tables:
            body = table.rows[1:]
            if table.merged:
                bad.append("slide %d's table has merged cells; keep every cell its own" % s.n)
            if not table.header:
                bad.append("slide %d's table has no header row marked; switch on its header row" % s.n)
            if s.kind not in ("next-steps", "comparison") and len(body) < d["table.min_rows"]:
                bad.append("slide %d's table has %d rows; under %d, state the figures as key figures" % (s.n, len(body), d["table.min_rows"]))
            if any(not any(c.text.strip() for c in row) for row in body):
                bad.append("slide %d's table has a blank row; no spacer rows" % s.n)
            unnamed = [c + 1 for c, cell in enumerate(table.rows[0] if table.rows else []) if not cell.text.strip()
                       and not (c == 0 and s.kind == "comparison")]
            if unnamed:
                bad.append("slide %d's table has no heading over column %s; name every column" % (s.n, ", ".join(str(c) for c in unnamed)))
            for c in range(len(table.rows[0]) if table.rows else 0):
                cells = [row[c] for row in body if len(row) > c and row[c].paras]
                firsts = [cell.paras[0].text.strip() for cell in cells]
                numbers = [t for t in firsts if is_number(t)]
                if not firsts or len(numbers) < max(1, len([t for t in firsts if t not in ("–", "-", "—")])):
                    # a column of words; a figure with its unit written into every cell belongs in a number column
                    united = [t for t in firsts if re.fullmatch(r"[^\d]{0,6}\d[\d.,' ]*\s?[^\d\s]{1,12}", t) and not is_number(t)]
                    if len(united) >= 2 and len(united) == len(firsts):
                        bad.append("slide %d's table writes the unit in every cell of column %d (%s); put the unit in the heading"
                                   % (s.n, c + 1, united[0]))
                    continue
                name = table.rows[0][c].text.strip() or "column %d" % (c + 1)
                if any(cell.align != "r" for cell in cells) or (table.rows[0][c].paras and table.rows[0][c].align != "r"):
                    bad.append("slide %d's table sets the numbers of %r left or centred; right-align numbers and their heading" % (s.n, name))
                places = {decimals(t) for t in numbers}
                grouped = {decimals(t, grouped=True) for t in numbers}
                if len(places) > 1 and len(grouped) > 1:
                    bad.append("slide %d's table mixes %s decimal places in %r; one precision down a column"
                               % (s.n, " and ".join(str(p) for p in sorted(places)), name))
                if any(re.search(r"\d{5,}", t) for t in numbers):
                    bad.append("slide %d's table prints a long number in %r without thousands separators" % (s.n, name))
                if sum(1 for t in numbers if t.endswith("%")) >= 2:
                    bad.append("slide %d's table repeats %% in the cells of %r; put the unit in the heading" % (s.n, name))
            pitch = float(d["table.row_pitch"])
            for r, row in enumerate(table.rows):
                need = max([cell.needed(deck.advance) for cell in row if cell.paras] + [0.0])
                line = max([p.pitch for cell in row for p in cell.paras] + [0.0])
                if need and table.heights[r] > need + (pitch - 1.0) * line + 1.5:
                    bad.append("slide %d's table row %d is %.0f pt tall for %.0f pt of text; a table is as tall as its rows, at most %.1f lines a row"
                               % (s.n, r + 1, table.heights[r], need, pitch))
                    break
    return result("BDECK-TABLE", bad, "tables are as tall as their rows, numbers right-aligned, one precision a column")


def rule_fit(deck):
    bad = []
    for s in deck.slides:
        for item in s.texts:
            if item.autofit or not item.h:
                continue
            need = item.needed(deck.advance)
            if need > item.inner_h() + 2.0:
                bad.append("slide %d, %r needs %.0f pt of height and its box has %.0f; cut about %d characters or split the page"
                           % (s.n, item.name, need, item.inner_h(), int(len(item.text) * (1 - item.inner_h() / need)) + 1))
            else:
                wide = max([T.widest_word(p.text, p.size, deck.advance, p.spacing) + p.indent for p in item.paras] + [0.0])
                if wide > item.inner_w() + 1.0:
                    bad.append("slide %d, %r holds a word wider than its box" % (s.n, item.name))
        for table in s.tables:
            for r, row in enumerate(table.rows):
                for cell in row:
                    if cell.paras and cell.needed(deck.advance) > table.heights[r] + 1.5:
                        bad.append("slide %d's table row %d needs %.0f pt and is %.0f pt tall; shorten the cell %r"
                                   % (s.n, r + 1, cell.needed(deck.advance), table.heights[r], cell.text[:30]))
                        break
            if table.y + sum(table.heights) > deck.H - deck.d["margin.min"] * deck.H + 1:
                bad.append("slide %d's table runs past the bottom margin; move rows to a second page" % s.n)
        for ex in s.charts:
            if ex.x < -1 or ex.y < -1 or ex.x + ex.w > deck.W + 1 or ex.y + ex.h > deck.H + 1:
                bad.append("slide %d's chart leaves the page" % s.n)
    if deck.printed:
        bad += deck.fit_problems()
        return result("BDECK-FIT", bad, "all text fits its box, measured on the printed pages")
    return result("BDECK-FIT", bad, "all text fits its box")


def rule_fill(deck):
    d, bad = deck.d, []
    fills, how = fill_of(deck)
    # An estimate from the file counts a little less than a render does, so it is given that much.
    slack = 0.0 if how.startswith("measured") else float(deck.measure.get("estimate_slack", 0.0))
    seen = []
    for s, (share, lower, _) in zip(deck.slides, fills):
        if s.kind == "closing" and share + slack < d["fill.closing_min"]:
            bad.append("slide %d, the closing page, fills %.2f of the body; the %s preset asks for %.2f: say what is asked and whom to reach, not one line"
                       % (s.n, share, deck.preset, d["fill.closing_min"]))
        if not s.content():
            continue
        seen.append(share)
        if s.kind == "quote":
            # one sentence and who said it: a quote page is held to its own floor, as the closing page is
            if share + slack < d["fill.quote_min"]:
                bad.append("slide %d, the quote page, fills %.2f of the body; the %s preset asks for %.2f: quote a whole sentence"
                           % (s.n, share, deck.preset, d["fill.quote_min"]))
        elif share + slack < d["fill.min"]:
            bad.append("slide %d fills %s of the body; the %s preset asks for %s: add what the person's material gives in support of the title, "
                       "or use a page type that holds less; never pad" % (s.n, two(share, d["fill.min"])[0], deck.preset, two(share, d["fill.min"])[1]))
        elif share > d["fill.max"]:
            bad.append("slide %d fills %.2f of the body; the %s preset holds %.2f: cut, or split the page" % (s.n, share, deck.preset, d["fill.max"]))
        if lower + slack < d["lower.min"]:
            bad.append("slide %d's lower half is %s full; the %s preset asks for %s: the page stops half way down"
                       % (s.n, two(lower, d["lower.min"])[0], deck.preset, two(lower, d["lower.min"])[1]))
        for item in s.texts:
            if (item.fill is not None and item.fill != s.ground or item.line) and item.h:
                used = item.needed(deck.advance) / item.inner_h()
                if used < d["panel.min_fill"]:
                    bad.append("slide %d, the panel %r is %.2f full; a drawn panel is at least %.2f full, make it as small as its text"
                               % (s.n, item.name, used, d["panel.min_fill"]))
    if not seen:
        return True, "no content pages to measure"
    return result("BDECK-FILL", bad, "%d content pages fill %.2f to %.2f of the body, %s (%s preset)"
                  % (len(seen), min(seen), max(seen), how, deck.preset))


def rule_words(deck):
    d, bad = deck.d, []
    counts = []
    for s in deck.slides:
        if not s.content():
            continue
        text = " ".join(t for where, t in all_text(deck, s) if where.strip().lower() not in RUNNING + ("source",))
        count = len(words(text))
        counts.append(count)
        if count < d["words.min"]:
            bad.append("slide %d carries %d words; the %s preset asks for at least %d: say what supports the title" % (s.n, count, deck.preset, d["words.min"]))
        elif count > d["words.max"]:
            bad.append("slide %d carries %d words; the %s preset holds %d: cut, or split the page" % (s.n, count, deck.preset, d["words.max"]))
        for item in s.named("takeaway"):
            lines = item.lines(deck.advance)
            if item.paras and lines and len(lines[0]) > d["takeaway.max_lines"]:
                bad.append("slide %d's takeaway runs to %d lines; it is one sentence of at most %d lines: cut it, or give its column more room"
                           % (s.n, len(lines[0]), d["takeaway.max_lines"]))
        points = s.named("point ")
        if len(points) > d["bullets.max"]:
            bad.append("slide %d lists %d points; the %s preset holds %d" % (s.n, len(points), deck.preset, d["bullets.max"]))
        for item in body_texts(s):
            bullets = [p for p in item.paras if p.bullet]
            if len(bullets) > d["bullets.max"]:
                bad.append("slide %d, %r lists %d points; the %s preset holds %d" % (s.n, item.name, len(bullets), deck.preset, d["bullets.max"]))
            if len({p.level for p in bullets}) > 1:
                bad.append("slide %d, %r nests its points; keep them on one level" % (s.n, item.name))
            for p, lines in zip(item.paras, item.lines(deck.advance)):
                if p.bullet and len(lines) > 2:
                    bad.append("slide %d, the point %r runs to %d lines; a point is at most two" % (s.n, p.text[:30], len(lines)))
                    break
    if not counts:
        return True, "no content pages to count"
    asked = label_case(deck)
    if asked and not bad:
        return True, "WARN " + head(asked)
    return result("BDECK-WORDS", bad, "content pages carry %d to %d words (%s preset)" % (min(counts), max(counts), deck.preset))


def label_case(deck):
    """Section names and the deck's running title that are set in Title Case, each as a question for the writer:
    the look is sentence case, and a deck whose labels read "The Problem" beside titles in sentence case reads as
    two hands. A label is asked about only when it has two words or more, every word starts with a capital, and at
    least two of them are neither all capitals (Q3, VAT) nor one of the deck's own names (the organisation, the
    person it quotes, whom to reach): so a name or a short form never trips it alone. One such word is enough when
    it is not the label's first word and the deck itself writes it without the capital somewhere ("Q3 Performance"
    beside "performance"): the deck has then said it is no name. The builder never rewrites a label."""
    names = set(re.findall(r"[^\W\d_]+", (getattr(deck, "author", "") or "").lower()))
    labels = {}
    for s in deck.slides:
        for t in s.texts:
            if t.key in ("organisation", "quote name", "contact"):
                names |= set(re.findall(r"[^\W\d_]+", t.text.lower()))
            running = t.key in ("section", "deck title") or t.kind == "footer"
            listed = (s.kind == "agenda" and t.key.startswith("item ") and not t.key.endswith("number")) \
                or (s.kind == "summary" and t.key.startswith("block ") and t.key.endswith("label"))
            if (running or listed) and t.paras:
                labels.setdefault(t.paras[0].text.strip(), (s.n, "running title" if t.key == "deck title" or t.kind == "footer" else "section label"))
    names -= STOP | {"a", "an", "of", "to", "in", "on", "at", "by", "our", "we", "you", "your"}
    small = {w for s in deck.slides for t in s.texts for w in re.findall(r"[^\W\d_][\w'’-]*", t.text) if w[0].islower()}
    out = []
    for text, (n, what) in labels.items():
        found = re.findall(r"[^\W\d_][\w'’-]*", text)
        if len(found) < 2 or not all(w[0].isupper() for w in found):
            continue
        own = [w for w in found if not w.isupper() and w.lower() not in names]
        if len(own) < 2:
            own = [w for w in own if w != found[0] and w[0].lower() + w[1:] in small]
            if not own:
                continue
        plain = text
        for w in own[1:] if found[0] == own[0] else own:
            plain = re.sub(r"\b%s\b" % re.escape(w), w[0].lower() + w[1:], plain, count=1)
        out.append("the %s %r (slide %d) is in Title Case; labels are set in sentence case, as the titles are: %r, "
                   "unless it is a name" % (what, text, n, plain))
    return out


def rule_type(deck):
    d, bad = deck.d, []
    titles = {}
    for s in deck.slides:
        small = []
        for item in s.texts:
            small += [(p.size, item.name) for p in item.paras if p.size < d["type.floor"] - 0.01]
        for table in s.tables:
            small += [(p.size, "the table") for row in table.rows for cell in row for p in cell.paras if p.size < d["type.floor"] - 0.01]
        for chart in s.charts:
            small += [(z, "the chart") for z in chart.sizes if z < d["type.floor"] - 0.01]
        if deck.printed and not small:
            least = deck.smallest(s)
            if least is not None and least < d["type.floor"] - 0.06:
                small.append((least, "some of its text"))
        if small:
            size, where = min(small)
            bad.append("slide %d sets %s at %g pt; nothing is set under %g pt in the %s preset" % (s.n, where, size, d["type.floor"], deck.preset))
        if not s.content():
            continue
        if s.title is not None:
            titles.setdefault(round(s.title.paras[0].size, 1), s.n)
        weight = {}
        for item in body_texts(s):
            if item.key in SMALL_PRINT:
                continue
            for p in item.paras:
                weight[p.size] = weight.get(p.size, 0) + len(p.text)
        for table in s.tables:
            for row in table.rows:
                for cell in row:
                    for p in cell.paras:
                        weight[p.size] = weight.get(p.size, 0) + len(p.text)
        if weight:
            most = max(weight, key=weight.get)
            if most < d["type.body_min"] - 0.01:
                bad.append("slide %d sets most of its text at %g pt; body text is at least %g pt in the %s preset"
                           % (s.n, most, d["type.body_min"], deck.preset))
    if len(titles) > 1:
        bad.append("content titles are set in %s pt (slides %s); one title size on every content page"
                   % (" and ".join("%g" % k for k in sorted(titles)), ", ".join(str(titles[k]) for k in sorted(titles))))
    return result("BDECK-TYPE", bad, "nothing under %g pt, body at %g pt or more, one title size" % (d["type.floor"], d["type.body_min"]))


def rule_contrast(deck):
    bad = []

    def judge(n, where, p, ground):
        need = 3.0 if p.size >= 18 or (p.size >= 14 and p.bold) else 4.5
        got = contrast(p.colour, ground)
        if got < need - 0.005:
            bad.append("slide %d, %s: %r is %.2f:1 against its ground; it needs %.1f:1 at %g pt" % (n, where, p.text[:24], got, need, p.size))

    for s in deck.slides:
        for item in s.texts:
            ground = item.fill or s.ground
            for p in item.paras:
                judge(s.n, repr(item.name), p, ground)
        for table in s.tables:
            for row in table.rows:
                for cell in row:
                    for p in cell.paras:
                        judge(s.n, "the table", p, cell.fill or s.ground)
        for chart in s.charts:
            for x in chart.series:
                colours = [c for c in [x["colour"]] + list(x["points"].values()) if c is not None]
                for c in colours:
                    seen = max(contrast(c, s.ground), contrast(x["outline"], s.ground) if x["outline"] else 0)
                    if seen < 3.0 - 0.005:
                        bad.append("slide %d's chart draws %r at %.2f:1 against the page; a mark needs 3:1, or an outline that has it"
                                   % (s.n, x["name"] or "a series", seen))
                        break
    return result("BDECK-CONTRAST", bad, "text and chart marks have the contrast WCAG 2.2 asks for")


def rule_grid(deck):
    d, m, bad = deck.d, deck.measure, []
    tol = float(m.get("position_tolerance", 1.0))
    margin_x, margin_y = d["margin.min"] * deck.W, d["margin.min"] * deck.H
    fills, how = fill_of(deck)
    pages = _pages(deck)
    for s, (_, _, box) in zip(deck.slides, fills):
        if box is None or s.kind in ("cover", "closing"):
            continue
        if box[0] < margin_x - 1.5 or box[2] > deck.W - margin_x + 1.5:
            bad.append("slide %d runs to %.0f pt from a side edge; the %s preset keeps %.0f pt clear"
                       % (s.n, min(box[0], deck.W - box[2]), deck.preset, margin_x))
        if box[1] < margin_y - 1.5 or box[3] > deck.H - margin_y + 1.5:
            bad.append("slide %d runs to %.0f pt from the top or bottom edge; the %s preset keeps %.0f pt clear"
                       % (s.n, min(box[1], deck.H - box[3]), deck.preset, margin_y))
    content = [s for s in deck.slides if s.content() and s.title is not None]
    spots = {}
    for s in content:
        spots.setdefault((round(s.title.x / tol), round(s.title.y / tol)), []).append(s.n)
    if len(spots) > 1:
        odd = sorted(spots.values(), key=len)[0]
        bad.append("the title sits at another position on slide %s; keep its top and left edge the same on every content page"
                   % ", ".join(str(n) for n in odd[:4]))
    # The running line: its parts at one height on every page, and on one baseline.
    heights = {}
    for s in deck.slides:
        parts = [t for t in s.texts if t.kind in ("footer", "number") or t.key in ("section", "deck title", "page number")]
        parts = [t for t in parts if t.h and t.h < 40]
        if s.kind != "cover" and not any(t.kind == "number" or t.key == "page number" for t in s.texts):
            bad.append("slide %d carries no page number; every page but the cover has one" % s.n)
        if not parts:
            continue
        bottoms = {round((t.y + t.h) / tol) for t in parts}
        sizes = {round(t.paras[0].size, 1) for t in parts}
        if len(bottoms) > 1 or (len(sizes) > 1 and {t.anchor for t in parts} != {"b"}):
            bad.append("slide %d's running line stands on more than one baseline; the name, the deck title, the section and the page number share one" % s.n)
        heights.setdefault(round(min(t.y for t in parts) / tol), []).append(s.n)
        if pages and pages[s.n - 1]["chars"] is not None:
            y0, y1 = min(t.y for t in parts) - 3, max(t.y + t.h for t in parts) + 3
            lines = sorted({round(base, 1) for x, base, size in pages[s.n - 1]["chars"] if y0 <= base <= y1})
            if lines and lines[-1] - lines[0] > float(m.get("baseline_tolerance", 0.6)):
                bad.append("slide %d's running line is drawn on baselines %.1f pt apart; its parts share one baseline"
                           % (s.n, lines[-1] - lines[0]))
    if len(heights) > 1:
        odd = sorted(heights.values(), key=len)[0]
        bad.append("the running line sits at another height on slide %s; keep it at one position on every page" % ", ".join(str(n) for n in odd[:4]))
    if pages and all(p["chars"] is not None for p in pages):
        firsts = {}
        for s in content:
            y0, y1 = s.title.y, s.title.y + s.title.h + 2
            inside = [base for x, base, size in pages[s.n - 1]["chars"] if y0 <= base <= y1 and s.title.x - 2 <= x <= s.title.x + s.title.w + 2]
            if inside:
                firsts.setdefault(round(min(inside) / tol), []).append(s.n)
        if len(firsts) > 1:
            odd = sorted(firsts.values(), key=len)[0]
            bad.append("the title's first line is drawn at another height on slide %s" % ", ".join(str(n) for n in odd[:4]))
    cover = next((s for s in deck.slides if s.kind == "cover"), None)
    if cover is not None and not any(re.search(r"\b(19|20)\d\d\b", t.text) for t in cover.texts):
        bad.append("the cover carries no date; say when the deck is from")
    return result("BDECK-GRID", bad, "margins held, the title and the running line at one position, on one baseline (%s)" % how)


def rule_file(deck):
    d, bad = deck.d, []
    if deck.printed:
        title, lang = deck.file_title, deck.file_language
        bad += deck.file_problems
    else:
        props = deck.prs.core_properties
        title, lang = props.title, (props.language or "").strip()
        if not lang:
            xml = deck.prs.slide_master._element
            lang = next((n.get("lang") for n in xml.iter() if n.tag.endswith("RPr") and n.get("lang")), "")
    if not (title or "").strip():
        bad.append("the file has no title in its properties")
    if DULL_NAMES.match(deck.path.stem.strip()):
        bad.append("the file is named %r; name it after the deck" % deck.path.name)
    if not lang:
        bad.append("the file names no language for its text")
    for s in deck.slides:
        if s.title is None or not s.title.text.strip():
            bad.append("slide %d has no title in its title placeholder" % s.n)
        else:
            first = next((item for kind, item in s.order if kind == "text" and item.key not in RUNNING), None)
            if first is not None and first is not s.title:
                bad.append("slide %d is read from %r before its title; put the title first in the reading order" % (s.n, first.name))
        for chart in s.charts:
            if not chart.alt:
                bad.append("slide %d's chart has no alternative text; say the kind of chart, the data and the takeaway" % s.n)
            elif len(chart.alt) > d["alt.max_chars"]:
                bad.append("slide %d's chart has %d characters of alternative text; keep it to %d" % (s.n, len(chart.alt), d["alt.max_chars"]))
        for name, alt in s.pictures:
            if not alt:
                bad.append("slide %d's picture %r has no alternative text" % (s.n, name))
            elif len(alt) > d["alt.max_chars"]:
                bad.append("slide %d's picture has %d characters of alternative text; keep it to %d" % (s.n, len(alt), d["alt.max_chars"]))
    return result("BDECK-FILE", bad, "titles, reading order, alternative text, language and file name are in place")


def _matrix(slide):
    """A matrix page as the check reads it: the box its two axes span, the four quadrants' names, the six words
    of the axes, the highlighted quadrants and the items with the quadrant each stands in."""
    axes = [m for m in slide.marks if m.kind == "line" and m.key == "matrix axis"]
    lines = axes or [m for m in slide.marks if m.kind == "line" and m.key.startswith("matrix")]
    if not lines:
        return None
    x0, y0 = min(m.x for m in lines), min(m.y for m in lines)
    x1, y1 = max(m.x + m.w for m in lines), max(m.y + m.h for m in lines)
    if x1 - x0 < 20 or y1 - y0 < 20:
        return None

    def quadrant(px, py):
        return "quadrant %s %s" % ("top" if py < (y0 + y1) / 2.0 else "bottom", "left" if px < (x0 + x1) / 2.0 else "right")
    names = {key: (slide.one(key).text.strip() if slide.one(key) else "") for key in QUADRANTS}
    words = {key: (slide.one(key).text.strip() if slide.one(key) else "") for key in AXES}
    lit = [quadrant(*m.middle) for m in slide.marks if m.kind == "box" and m.key == "quadrant highlight"]
    dots = [m for m in slide.marks if m.kind == "dot" and m.key == "item mark"]
    items = []
    for label in slide.named("item label"):
        mid = (label.x + label.w / 2.0, label.y + label.h / 2.0)
        near = min(dots, key=lambda m: abs(m.middle[0] - mid[0]) + 4 * abs(m.middle[1] - mid[1])) if dots else None
        at = near.middle if near is not None else mid
        items.append({"name": label.text.strip(), "at": at, "quadrant": quadrant(*at), "label": label,
                      "inside": x0 - 1 <= at[0] <= x1 + 1 and y0 - 1 <= at[1] <= y1 + 1})
    return {"box": (x0, y0, x1, y1), "names": names, "axes": words, "lit": lit, "items": items}


def rule_matrix(deck):
    d, bad = deck.d, []
    pages = [s for s in deck.slides if s.kind == "matrix"]
    for s in pages:
        m = _matrix(s)
        if m is None:
            bad.append("slide %d is a matrix page with no matrix drawn on it" % s.n)
            continue
        title = clean_title(s.title.text) if s.title is not None else ""
        said = {"x axis": "what its horizontal axis measures", "x low": "the low end of its horizontal axis",
                "x high": "the high end of its horizontal axis", "y axis": "what its vertical axis measures",
                "y low": "the low end of its vertical axis", "y high": "the high end of its vertical axis"}
        missing = [said[key] for key in AXES if not m["axes"][key] or FILLER.match(m["axes"][key])]
        if missing:
            bad.append("slide %d's matrix does not name %s; a matrix has two named axes, each with both ends named" % (s.n, ", ".join(missing[:3])))
        for letter in ("x", "y"):
            low, high = m["axes"]["%s low" % letter], m["axes"]["%s high" % letter]
            if low and low.lower() == high.lower():
                bad.append("slide %d's matrix calls both ends of an axis %r; name the low end and the high end" % (s.n, low))
        named = [v for v in m["names"].values() if v and not FILLER.match(v)]
        if len(named) < 4:
            bad.append("slide %d's matrix names %d of its four quadrants; name all four" % (s.n, len(named)))
        elif len({v.lower() for v in named}) < 4:
            bad.append("slide %d's matrix gives two quadrants the same name" % s.n)
        items = m["items"]
        if len(items) < d["matrix.min_items"]:
            bad.append("slide %d's matrix places %d items; it takes at least %d to compare" % (s.n, len(items), d["matrix.min_items"]))
        elif len(items) > d["matrix.max_items"]:
            bad.append("slide %d's matrix places %d items; the %s preset holds %d" % (s.n, len(items), deck.preset, d["matrix.max_items"]))
        outside = [i["name"] for i in items if not i["inside"]]
        if outside:
            bad.append("slide %d's matrix places %s outside its axes" % (s.n, ", ".join(repr(o) for o in outside[:3])))
        for a, b in ((a, b) for n, a in enumerate(items) for b in items[n + 1:]):
            la, lb = a["label"], b["label"]
            if la.x < lb.x + lb.w and lb.x < la.x + la.w and la.y < lb.y + lb.h and lb.y < la.y + la.h:
                bad.append("slide %d's matrix sets the names %r and %r on top of each other; move one item" % (s.n, a["name"], b["name"]))
                break
        if any(t.turned for t in s.texts):
            bad.append("slide %d's matrix sets text at an angle; keep every word horizontal" % s.n)
        if not m["lit"]:
            bad.append("slide %d's matrix highlights no quadrant; highlight the one the page's message is about" % s.n)
        elif len(m["lit"]) > 1:
            bad.append("slide %d's matrix highlights %d quadrants; highlight the one the title is about" % (s.n, len(m["lit"])))
        else:
            key = m["lit"][0]
            name = m["names"].get(key, "")
            inside = [i["name"] for i in items if i["quadrant"] == key]
            others = [v for k, v in m["names"].items() if k != key]
            if not (names_it(title, name, others) or any(names_it(title, i, [o["name"] for o in items]) for i in inside)):
                bad.append("slide %d's matrix highlights %r, and the title names neither it nor an item in it; highlight what the title says, or say it"
                           % (s.n, name or key))
    return result("BDECK-MATRIX", bad, "every matrix names its axes and quadrants and highlights what its title says"
                  if pages else "no matrix page to check")


def rule_figure(deck):
    d, m, bad = deck.d, deck.measure, []
    pages = [s for s in deck.slides if s.kind == "figure"]
    body = (m["band"]["right"] - m["band"]["left"]) * deck.W * (m["band"]["bottom"] - m["band"]["top"]) * deck.H
    for s in pages:
        if len(s.pictures) != 1:
            bad.append("slide %d is a figure page with %s; it shows one picture as its exhibit"
                       % (s.n, "no picture" if not s.pictures else "%d pictures" % len(s.pictures)))
            continue
        pic = s.pictures[0]
        caption = s.one("caption")
        title = clean_title(s.title.text).lower() if s.title is not None else ""
        if caption is None or not caption.text.strip() or FILLER.match(caption.text.strip()) or INSERT.search(caption.text):
            bad.append("slide %d's figure has no caption; say in a line what the picture is" % s.n)
        else:
            if caption.text.strip().lower() == title:
                bad.append("slide %d's caption repeats the title; the title is the message, the caption says what the picture is" % s.n)
            lines = sum(len(ls) for ls in caption.lines(deck.advance))
            if lines > d["caption.max_lines"]:
                bad.append("slide %d's caption takes %d lines; a caption is at most %d" % (s.n, lines, d["caption.max_lines"]))
        if pic.alt and (PICTURE_FILE.search(pic.alt) or pic.alt.strip().lower() in (pic.name.strip().lower(), "figure", "picture", "image")):
            bad.append("slide %d's picture has %r as its alternative text; say what the picture shows" % (s.n, pic.alt[:40]))
        wide, high = pic.px[0] * (1 - pic.crop[0] - pic.crop[2]), pic.px[1] * (1 - pic.crop[1] - pic.crop[3])
        if wide > 0 and high > 0 and pic.w and pic.h:
            if abs((pic.w / pic.h) / (wide / high) - 1.0) > 0.02:
                bad.append("slide %d's picture is stretched: it is drawn %.2f to 1 and the file is %.2f to 1; keep its proportions"
                           % (s.n, pic.w / pic.h, wide / high))
            sharp = wide / (pic.w / 72.0)
            if sharp < d["figure.min_ppi"]:
                bad.append("slide %d's picture is %d pixels wide and shown %.1f inches wide, %d pixels an inch; under %d it blurs: use a larger file or show it smaller"
                           % (s.n, wide, pic.w / 72.0, sharp, d["figure.min_ppi"]))
        share = pic.w * pic.h / body
        if share < d["figure.min_share"]:
            bad.append("slide %d's picture covers %.2f of the body; the %s preset asks for %.2f: the picture is the page's exhibit, show it larger"
                       % (s.n, share, deck.preset, d["figure.min_share"]))
        edge_x, edge_y = d["margin.min"] * deck.W, d["margin.min"] * deck.H
        if pic.x < edge_x - 1.5 or pic.x + pic.w > deck.W - edge_x + 1.5 or pic.y < edge_y - 1.5 or pic.y + pic.h > deck.H - edge_y + 1.5:
            bad.append("slide %d's picture runs into the page's margin" % s.n)
    return result("BDECK-FIGURE", bad, "every figure is one picture at its own proportions, with a caption and words for those who cannot see it"
                  if pages else "no figure page to check")


def sentences(text):
    """How many sentences a quotation holds, its own quotation marks set aside."""
    core = (text or "").strip().strip(QUOTE_MARKS + " ")
    parts = re.split(r"(?<=[.!?…])[%s]?\s+(?=[%s]?[^\W\d_a-zà-ÿ])" % (re.escape(QUOTE_MARKS), re.escape(QUOTE_MARKS)), core)
    return len([p for p in parts if p.strip()])


def rule_quote(deck):
    d, bad = deck.d, []
    pages = [s for s in deck.slides if s.kind == "quote"]
    if len(pages) > d["quotes.max"]:
        bad.append("the deck has %d quote pages (slides %s); the %s preset holds %d: a quote is the one voice the deck lets in"
                   % (len(pages), ", ".join(str(s.n) for s in pages), deck.preset, d["quotes.max"]))
    for s in pages:
        said, name, role = s.one("quote"), s.one("quote name"), s.one("quote role")
        if said is None or not said.text.strip():
            bad.append("slide %d is a quote page with no quote on it" % s.n)
            continue
        text = said.text.strip()
        count = len(words(text))
        if FILLER.match(text.strip(QUOTE_MARKS + " ")) or INSERT.search(text):
            bad.append("slide %d's quote is filler text; quote what was said" % s.n)
        elif count < d["quote.min_words"]:
            bad.append("slide %d's quote is %d words; under %d it is a slogan, not something somebody said" % (s.n, count, d["quote.min_words"]))
        elif count > d["quote.max_words"]:
            bad.append("slide %d's quote runs to %d words; the %s preset holds %d: quote the one sentence that matters" % (s.n, count, deck.preset, d["quote.max_words"]))
        if sentences(text) > 1:
            bad.append("slide %d quotes %d sentences; quote one" % (s.n, sentences(text)))
        who = name.text.strip() if name is not None else ""
        what = role.text.strip() if role is not None else ""
        if not who or FILLER.match(who):
            bad.append("slide %d's quote does not say who said it" % s.n)
        if not what or FILLER.match(what) or what.lower() == who.lower():
            bad.append("slide %d's quote gives no role for %s; say what they are to the reader (a role, an organisation)" % (s.n, who or "its speaker"))
        dressed = []
        if s.pictures:
            dressed.append("a picture")
        if any(m.kind == "box" for m in s.marks) or any((t.fill is not None and t.fill != s.ground) or t.line for t in (said, name, role) if t is not None):
            dressed.append("a panel")
        if any(p.italic for p in said.paras):
            dressed.append("italics")
        if text.strip(QUOTE_MARKS + " ").isupper():
            dressed.append("capitals")
        if any(t.text.strip() and not t.text.strip().strip(QUOTE_MARKS) for t in s.texts):
            dressed.append("a quotation mark as an ornament")
        if dressed:
            bad.append("slide %d dresses its quote with %s; the sentence and who said it are enough" % (s.n, " and ".join(dressed)))
        low = max(t.y + t.h for t in (said, name, role) if t is not None)
        if low > deck.H - d["margin.min"] * deck.H + 1:
            bad.append("slide %d's quote runs past the foot of the page; cut it" % s.n)
    return result("BDECK-QUOTE", bad, "the quote is one sentence, with who said it and their role, and nothing else"
                  if pages else "no quote page to check")


def rule_appendix(deck):
    bad = []
    dividers = [s for s in deck.slides if s.kind == "appendix"]
    if not dividers:
        return True, "no appendix to check"
    if len(dividers) > 1:
        bad.append("the deck has %d appendix dividers (slides %s); one opens the appendix" % (len(dividers), ", ".join(str(s.n) for s in dividers)))
    first = dividers[0]
    behind = [s for s in deck.slides if s.backup]
    name = clean_title(first.title.text).strip() if first.title is not None else ""
    if not behind:
        bad.append("slide %d opens an appendix with no backup page behind it" % first.n)
    late = [s for s in behind if not s.content() or s.kind in ("summary", "next-steps")]
    if late:
        bad.append("slide %d (%s) stands behind the appendix divider; the appendix comes last, after the closing page, and holds only backup pages"
                   % (late[0].n, late[0].kind))
    closing = [s for s in deck.slides if s.kind == "closing"]
    if page_count(deck) >= deck.d["story.min_pages"] and not [s for s in closing if s.n < first.n]:
        bad.append("the appendix on slide %d opens before the deck has closed; the storyline ends on its closing page first" % first.n)
    marks, count = set(), 0
    for s in behind:
        if s in late:
            continue
        count += 1
        number = next((t.text.strip() for t in s.texts if t.kind == "number" or t.key == "page number"), "")
        found = re.fullmatch(r"([^\W\d_]{1,3})[ .-]?(\d+)", number)
        if not found:
            bad.append("slide %d is a backup page numbered %s; number backup pages in the appendix's own count, a letter and a number (A1, A2)"
                       % (s.n, "as a page of the storyline" if not number or "#" in number or number.isdigit() else repr(number)))
            continue
        marks.add(found.group(1).upper())
        if int(found.group(2)) != count:
            bad.append("slide %d is numbered %s where the appendix's count is at %d" % (s.n, number, count))
        label = s.one("section").text.strip() if s.one("section") else ""
        if name and label.lower() != name.lower():
            bad.append("slide %d's running line reads %r; a backup page carries the appendix's name, %r" % (s.n, label, name))
    if len(marks) > 1:
        bad.append("the backup pages are numbered under %s; one letter for the whole appendix" % " and ".join(sorted(marks)))
    return result("BDECK-APPENDIX", bad, "the appendix stands behind the close and its %d backup pages keep their own count" % len(behind))


RULE = {
    "BDECK-TITLE": rule_title, "BDECK-ONE-IDEA": rule_one_idea, "BDECK-STORYLINE": rule_storyline,
    "BDECK-NEXT-STEPS": rule_next_steps, "BDECK-SOURCE": rule_source, "BDECK-PLACEHOLDER": rule_placeholder,
    "BDECK-CHART-HEAD": rule_chart_head, "BDECK-CHART-LABELS": rule_chart_labels, "BDECK-CHART-HONEST": rule_chart_honest,
    "BDECK-CHART-EARNS": rule_chart_earns, "BDECK-HIGHLIGHT": rule_highlight, "BDECK-TABLE": rule_table,
    "BDECK-FIT": rule_fit, "BDECK-FILL": rule_fill, "BDECK-WORDS": rule_words, "BDECK-TYPE": rule_type,
    "BDECK-CONTRAST": rule_contrast, "BDECK-GRID": rule_grid, "BDECK-FILE": rule_file,
    "BDECK-MATRIX": rule_matrix, "BDECK-FIGURE": rule_figure, "BDECK-QUOTE": rule_quote, "BDECK-APPENDIX": rule_appendix,
}


def check(rule_id, path, case, stage):
    path = Path(path)
    if path.suffix.lower() not in (".pdf", ".pptx"):
        return False, "could not check %s: the business deck is a PDF, or an editable PowerPoint file (.pptx)" % path.name
    if rule_id not in RULE:
        return None, "unknown rule"
    try:
        deck = deck_of(path)
    except NotADeck as why:
        # A PDF the builder did not write has no page the rules can read. One rule says so, with what to do; the
        # others stand down, so the answer is one line and never a clean check of nothing.
        if rule_id == "BDECK-FILE":
            return False, str(why)
        return False, "could not check: the PDF was not written by the deck's builder"
    except ImportError as missing:
        _through_uv()
        # Still here: no python-pptx and no uv. Run by hand, one rule fails and says what to install, so a check
        # that read nothing is never taken for a clean one; the others say they did not run. Run by the plugin's
        # Stop hook (--if-claimed), every rule stands down: there is nothing the agent can fix in the file.
        if rule_id == RULES[0] and "--if-claimed" not in sys.argv:
            return False, NEEDS % missing
        return False, "could not check: this Python lacks %s" % missing
    return RULE[rule_id](deck)


def report(path):
    """Every rule's verdict and the page-by-page measures: what the pack's tuning reads."""
    deck = deck_of(path)
    fills, how = fill_of(deck)
    lines = ["%s: %d slides, %s preset, %s" % (Path(path).name, len(deck.slides), deck.preset, how)]
    for s, (share, lower, box) in zip(deck.slides, fills):
        text = " ".join(t for where, t in all_text(deck, s) if where.strip().lower() not in RUNNING + ("source",))
        lines.append("  %2d %-11s fill %.2f lower %.2f words %3d  %s" % (s.n, s.kind, share, lower, len(words(text)),
                                                                 (s.title.text[:48] if s.title else "")))
    for rule in RULES:
        ok, why = RULE[rule](deck)
        lines.append("%s %-18s %s" % ("ok  " if ok else "FAIL", rule, why))
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    print(report(sys.argv[1]))
