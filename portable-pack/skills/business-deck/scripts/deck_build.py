#!/usr/bin/env python3
"""Build a business deck from its data: a PDF, and an editable PowerPoint file when one is asked for.

    python3 deck_build.py <deck>.deck.json <out>.pdf [--editable] [--density sparse|standard|full] [--look look.json]
    python3 deck_build.py <deck>.deck.json <out>.pptx [--no-pdf]

The agent writes the data (what each page says); this script lays the pages out, once, and writes
them two ways from the same positions:

  the PDF     what is handed back. The pages are written as one HTML file (deck_html.py: real text,
              real tables, charts as drawings of the same data) and printed by the app's own browser
              engine, or by a headless one outside the app. Nothing else has to be installed.
  the .pptx   the editable file, written when the person asks for one to edit (--editable, an out
              path ending in .pptx, "editable": true in the data, or a look that asks for it). A
              real PowerPoint deck: one slide master with a layout per page type, text in the
              layouts' placeholders, charts and tables native, so a colleague opens it in
              PowerPoint, Keynote, LibreOffice or Google Slides and edits a number or a word.

Two layers:
  structure   the page types, the grid and the rules of density.json: the same for every deck
  look        look.json: inks, face, type scale, letter spacing, margins, logo, running line. A
              company pack replaces it and nothing else. Both outputs read the same file.

The builder never writes a label of its own into a chart or a table: every word on a page comes
from the data.

The master-and-layout construction and the glyph-width text fit follow the approach of Nodejam's
own deck builder; python-pptx (MIT) writes the file.
"""
import argparse
import copy
import itertools
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(os.path.dirname(PACK), "_checks"))

NEEDS = ("deck_build.py needs %s, and this Python does not have it (%s).\n"
         "With uv installed the script fetches it itself. Without it, install the packages once:\n"
         "  python3 -m pip install python-pptx pillow pypdfium2 pypdf\n"
         "then run the same command again: python3 %s")
PACKAGES = ("python-pptx", "pillow", "pypdfium2", "pypdf")
import deck_text as T  # noqa: E402

# python-pptx writes the editable file and nothing else: the PDF is built without it.
NO_PPTX = None
try:
    from lxml import etree  # noqa: E402
    from pptx import Presentation  # noqa: E402
    from pptx.chart.data import CategoryChartData  # noqa: E402
    from pptx.dml.color import RGBColor  # noqa: E402
    from pptx.enum.dml import MSO_THEME_COLOR  # noqa: E402
    from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_TICK_LABEL_POSITION, XL_TICK_MARK  # noqa: E402
    from pptx.enum.shapes import PP_PLACEHOLDER  # noqa: E402
    from pptx.enum.text import MSO_ANCHOR, PP_ALIGN  # noqa: E402
    from pptx.opc.constants import RELATIONSHIP_TYPE as RT  # noqa: E402
    from pptx.opc.packuri import PackURI  # noqa: E402
    from pptx.parts.slide import SlideLayoutPart  # noqa: E402
    from pptx.util import Emu, Pt  # noqa: E402
except ImportError as missing:
    NO_PPTX = missing


def through_uv(what, missing):
    """A package this run needs is not in this Python. With uv installed the same command runs again through
    it: uv fetches the packages into its own cache and touches nothing of the system's Python. Once only: the
    second time round the error is the real answer."""
    import shlex
    if shutil.which("uv") and not os.environ.get("BDECK_UV"):
        os.environ["BDECK_UV"] = "1"
        sys.stdout.flush()
        os.execvp("uv", ["uv", "run", "--quiet", "--no-project"] + [x for p in PACKAGES for x in ("--with", p)]
                  + ["python3", os.path.abspath(__file__)] + sys.argv[1:])
    raise SystemExit(NEEDS % (what, missing, shlex.join(sys.argv)))


VERSION = "0.3.0"
MARK = "business-deck/%s" % VERSION
NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
}
DECL = " ".join('xmlns:%s="%s"' % (k, v) for k, v in NS.items() if k != "c")
PT = 12700
NO_TABLE_STYLE = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"

LAYOUTS = ["Cover", "Summary", "Agenda", "Section", "Chart", "Figures", "Comparison", "Table", "Process",
           "Timeline", "Text", "Matrix", "Figure", "Quote", "Next steps", "Closing", "Appendix"]
DARK = {"Cover", "Closing"}
# page type -> layout
TYPES = {"cover": "Cover", "summary": "Summary", "agenda": "Agenda", "section": "Section", "chart": "Chart",
         "figures": "Figures", "comparison": "Comparison", "table": "Table", "process": "Process",
         "timeline": "Timeline", "text": "Text", "matrix": "Matrix", "figure": "Figure", "quote": "Quote",
         "next-steps": "Next steps", "closing": "Closing", "appendix": "Appendix"}
KEYS = {
    "cover": {"title", "subtitle", "meta"},
    "summary": {"title", "blocks", "source"},
    "agenda": {"title", "items"},
    "section": {"title"},
    "chart": {"title", "kind", "measure", "unit", "period", "categories", "series", "bars", "highlight", "decimals",
              "axis_min", "alt", "takeaway", "points", "source"},
    "figures": {"title", "figures", "takeaway", "source"},
    "comparison": {"title", "options", "rows", "highlight", "source"},
    "table": {"title", "head", "columns", "rows", "highlight", "takeaway", "points", "source"},
    "process": {"title", "steps", "takeaway", "source"},
    "timeline": {"title", "steps", "source"},
    "text": {"title", "statement", "points", "source"},
    "matrix": {"title", "x", "y", "quadrants", "items", "highlight", "takeaway", "points", "source"},
    "figure": {"title", "image", "caption", "alt", "takeaway", "points", "source"},
    "quote": {"title", "quote", "name", "role", "source"},
    "next-steps": {"title", "columns", "steps", "source"},
    "closing": {"title", "contact", "small"},
    "appendix": {"title", "mark"},
}
# What may stand behind the appendix divider as a backup page: evidence, not the storyline's own pages.
BACKUP = ("chart", "figures", "comparison", "table", "process", "timeline", "text", "matrix", "figure", "quote")
QUADRANTS = ("top_left", "top_right", "bottom_left", "bottom_right")
PICTURES = ("PNG", "JPEG", "GIF")
EVERY = {"type", "section", "notes"}
# What a key holds. A line of text given a list (or a list given text) is refused by name: left alone it would be
# printed on the page as it stands.
TEXT = {"title", "subtitle", "head", "takeaway", "statement", "source", "caption", "alt", "quote", "name", "role", "image",
        "measure", "unit", "period", "kind", "small", "mark", "section", "notes", "highlight"}
LISTS = {"points", "rows", "columns", "categories", "series", "steps", "figures", "blocks", "items", "options", "meta"}
HINT = {"head": "it says in a line what the table shows; the column headings go in \"columns\"",
        "columns": "one heading a column", "source": "one line: \"Source: ...\"", "takeaway": "one sentence",
        "title": "the page's message as one sentence"}
CHART_KINDS = ("column", "bar", "line", "stacked")
CHARTS = {} if NO_PPTX else {"column": XL_CHART_TYPE.COLUMN_CLUSTERED, "bar": XL_CHART_TYPE.BAR_CLUSTERED,
                             "line": XL_CHART_TYPE.LINE, "stacked": XL_CHART_TYPE.COLUMN_STACKED}

IDX_SECTION, IDX_SOURCE, IDX_FOOTER, IDX_NUMBER = 10, 11, 12, 13
IDX_HEAD, IDX_EXHIBIT, IDX_TAKEAWAY, IDX_LEAD, IDX_SMALL, IDX_TRACK, IDX_NUM = 20, 21, 22, 23, 24, 25, 26
IDX_NAME, IDX_ROLE = 27, 28
GROUP_A, GROUP_B, GROUP_C = 30, 40, 50
IDX_AXIS = 60        # the six words of a matrix's two axes: 60 to 65
GROUP = 6
LISTED = 10          # the backup pages an appendix divider lists


class Refused(SystemExit):
    def __init__(self, message):
        super().__init__("refused: %s" % message)


def emu(points):
    return int(round(points * PT))


def esc(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def rgb(hexcode):
    return RGBColor.from_string(hexcode.upper())


# The look's colours have a place each in the file's theme (set in _theme): the ink is the theme's first text
# colour, the ground its first background, and so on. A colour that is one of them is written as that place,
# not as a fixed value, so changing the theme's colours in PowerPoint (Design, Variants, Colours) restyles every
# page, chart and table at once. Filled by the kit for the look in use; a colour with no place stays as it is.
SLOTS = {}
THEME_COLOR = {} if NO_PPTX else {
    "tx1": MSO_THEME_COLOR.TEXT_1, "bg1": MSO_THEME_COLOR.BACKGROUND_1, "tx2": MSO_THEME_COLOR.TEXT_2,
    "bg2": MSO_THEME_COLOR.BACKGROUND_2, "accent1": MSO_THEME_COLOR.ACCENT_1, "accent2": MSO_THEME_COLOR.ACCENT_2,
    "accent3": MSO_THEME_COLOR.ACCENT_3, "accent4": MSO_THEME_COLOR.ACCENT_4, "accent5": MSO_THEME_COLOR.ACCENT_5,
    "accent6": MSO_THEME_COLOR.ACCENT_6}


def clr(hexcode):
    """The colour as DrawingML: its place in the theme when it is one of the look's tokens, else its value."""
    slot = SLOTS.get(str(hexcode).upper())
    return '<a:schemeClr val="%s"/>' % slot if slot else '<a:srgbClr val="%s"/>' % str(hexcode).upper()


def paint(colour, hexcode):
    """The same for a colour set through python-pptx (a chart's marks, a table's text, a picture's outline)."""
    slot = SLOTS.get(str(hexcode).upper())
    if slot:
        colour.theme_color = THEME_COLOR[slot]
    else:
        colour.rgb = rgb(hexcode)


# ---------------------------------------------------------------- the kit: look, scale and grid


class Kit:
    """The look's tokens and the preset's numbers, turned into the positions a page is laid on."""

    def __init__(self, look, density, name, language):
        if name not in look["scale"]:
            raise Refused("the look has no type scale for the %s preset; it carries %s"
                          % (name, ", ".join(k for k in look["scale"] if k != "about")))
        self.look, self.name, self.language = look, name, language
        self.number = None      # a backup page's number in the appendix's count; None for a page of the storyline
        self.d = density["presets"][name]
        self.build = self.d["build"]
        sc = self.sc = look["scale"][name]
        self.W, self.H = look["page"]["width"], look["page"]["height"]
        self.M, self.G = sc["margin"], sc["gutter"]
        self.face = look["face"]["name"]
        self.advance = float(look["face"].get("advance") or T.advance_of(self.face))
        self.ink, self.dark, self.marks = look["ink"], look["dark"], look["marks"]
        # Which of the theme's colours each token is; where two tokens share a value the first named here has it.
        series = list(self.marks.get("series") or [])
        SLOTS.clear()
        for slot, value in (("tx1", self.ink["ink"]), ("bg1", self.ink["ground"]), ("tx2", self.dark["ground"]),
                            ("bg2", self.ink["raised"]), ("accent4", self.ink["second"]), ("accent5", self.dark["ink"]),
                            ("accent6", self.ink["hairline"]), ("accent1", self.marks["highlight"]),
                            ("accent2", self.marks["neutral"]), ("accent3", (series + [self.ink["second"]] * 3)[1])):
            SLOTS.setdefault(str(value).upper(), slot)
        cols = look["grid"]["columns"]
        page_col = (self.W - 2 * self.M - (cols - 1) * self.G) / float(cols)
        self.page_col = page_col
        self.c0 = max(0, int(look["grid"].get("content_from", 1)) - 1)
        self.X0 = self.M + self.c0 * (page_col + self.G)
        self.X1 = self.W - self.M
        self.CW = self.X1 - self.X0
        self.col = (self.CW - 11 * self.G) / 12.0
        self.small_line = sc["small"][1]
        self.body_line = sc["body"][1]
        top = look["running"].get("place", "top") == "top"
        self.running_y = sc["top"] if top else self.H - sc["bottom"] - self.small_line
        self.title_y = sc["top"] + self.small_line + 10 if top else sc["top"]
        self.title_h = 2 * sc["title"][1]
        self.body_top = self.title_y + self.title_h + sc["gap"]
        self.source_y = (self.H - sc["bottom"] - self.small_line) if top else self.running_y - 8 - self.small_line
        self.body_bottom = self.source_y - 10
        self.pad = round(self.body_line * 0.55)
        # A point is body text with its detail under it; where the preset sends the detail to the notes the
        # point stands alone and takes the lead size, the statement's.
        self.point_style = "lead" if self.build.get("detail") == "notes" else "body"
        ink, second = self.ink["ink"], self.ink["second"]
        dink, dsecond = self.dark["ink"], self.dark["second"]
        t = lambda key: (sc[key][0], sc[key][1])  # noqa: E731
        chart = (sc["chart"], round(sc["chart"] * 1.3))
        # style -> ((size, pitch), colour, space after)
        self.styles = {
            "display-dark": (t("display"), dink, 0),
            "headline": (t("headline"), ink, 0), "headline-dark": (t("headline"), dink, 0),
            "number": (t("headline"), second, 0),
            "title": (t("title"), ink, 0),
            "lead": (t("lead"), ink, round(sc["lead"][1] * 0.4)),
            "lead-second": (t("lead"), second, 0), "lead-dark": (t("lead"), dsecond, 0),
            "body": (t("body"), ink, round(sc["body"][1] * 0.3)),
            "body-second": (t("body"), second, round(sc["body"][1] * 0.3)),
            "body-dark": (t("body"), dink, 0),
            "small": (t("small"), second, 0), "small-ink": (t("small"), ink, 0),
            "small-dark": (t("small"), dsecond, 0), "small-dark-ink": (t("small"), dink, 0),
            "figure": (t("figure"), ink, 0), "figure-second": (t("figure"), second, 0),
            "head": (chart, ink, 0), "head-second": (chart, second, 0),
        }

    def part(self, first, count):
        """x and width of `count` of the content area's twelve columns, starting at column `first`."""
        return self.X0 + first * (self.col + self.G), count * self.col + (count - 1) * self.G

    def page_span(self, first, count):
        return self.M + first * (self.page_col + self.G), count * self.page_col + (count - 1) * self.G

    def spacing(self, style):
        """Letter spacing in points for a style: the look's tracking on large type, nothing on the rest."""
        tr = self.look.get("tracking") or {}
        size = self.styles[style][0][0]
        base = style.split("-")[0]
        if base in (tr.get("styles") or []) and size >= float(tr.get("from_pt", 14)):
            return float(tr.get("em", 0)) * size
        return 0.0

    def lines(self, text, style, width):
        size = self.styles[style][0][0]
        return T.wrap(text, size, width, self.advance, self.spacing(style))

    def width(self, text, style):
        return T.measure(text, self.styles[style][0][0], self.advance, self.spacing(style))

    def text_h(self, paras, width, indent=0.0):
        """Height of paragraphs given as (text, style): wrapped lines at the style's pitch plus its space after."""
        total, after = 0.0, 0.0
        for text, style in paras:
            (size, pitch), _, after = self.styles[style]
            total += len(self.lines(text, style, width - indent)) * pitch + after
        return total - after if paras else 0.0


def load_look(path):
    with open(path, encoding="utf-8") as handle:
        look = json.load(handle)
    look["_folder"] = os.path.dirname(os.path.abspath(path))
    return look


def load_density():
    with open(os.path.join(PACK, "density.json"), encoding="utf-8") as handle:
        return json.load(handle)


# ---------------------------------------------------------------- XML pieces


def _rpr(kit, style, tag="a:defRPr", colour=None, bold=None):
    (size, _), col, _ = kit.styles[style]
    weight = kit.look["face"].get("title_weight" if style.split("-")[0] in ("title", "headline") else "weight", 400)
    bold = (int(weight) >= 600) if bold is None else bold
    spc = int(round(kit.spacing(style) * 100))
    return ('<%s lang="%s" sz="%d" b="%d" i="0" spc="%d" dirty="0"><a:solidFill>%s</a:solidFill>'
            '<a:latin typeface="+mn-lt"/><a:cs typeface="+mn-lt"/></%s>'
            % (tag, kit.language, int(round(size * 100)), 1 if bold else 0, spc, clr(colour or col), tag))


def _lvl(kit, n, style, bullet, align):
    (size, pitch), colour, after = kit.styles[style]
    hang = emu(round(size * 0.95))
    mar = ' marL="%d" indent="%d"' % (hang, -hang) if bullet else ' marL="0" indent="0"'
    bu = ('<a:buClr>%s</a:buClr><a:buSzPct val="100000"/><a:buFontTx/><a:buChar char="%s"/>'
          % (clr(colour), bullet)) if bullet else "<a:buNone/>"
    return ('<a:lvl%dpPr%s algn="%s"><a:lnSpc><a:spcPts val="%d"/></a:lnSpc><a:spcBef><a:spcPts val="0"/></a:spcBef>'
            '<a:spcAft><a:spcPts val="%d"/></a:spcAft>%s%s</a:lvl%dpPr>'
            % (n, mar, align, int(pitch * 100), int(after * 100), bu, _rpr(kit, style), n))


def lst_style(kit, levels, align="l"):
    """The text styles of a placeholder, one per paragraph level; `levels` is [(style, bullet or None)]."""
    levels = list(levels) + [levels[-1]] * (3 - len(levels))
    return "<a:lstStyle>%s</a:lstStyle>" % "".join(_lvl(kit, n + 1, s, b, align) for n, (s, b) in enumerate(levels[:3]))


def _ph_tag(kind, idx):
    if kind == "title":
        return '<p:ph type="title"/>'
    return '<p:ph type="%s" sz="quarter" idx="%d"/>' % (kind, idx)


def placeholder(kit, sid, name, kind, idx, x, y, w, h, anchor, levels, align="l"):
    field = kind == "sldNum"
    run = ('<a:fld id="{B6F15528-21DE-4FAA-801E-634DDDAF4B2B}" type="slidenum"><a:rPr lang="%s"/><a:t>‹#›</a:t></a:fld>'
           % kit.language if field else '<a:r><a:rPr lang="%s" dirty="0"/><a:t>%s</a:t></a:r>' % (kit.language, esc(name)))
    xml = ('<p:sp %s><p:nvSpPr><p:cNvPr id="%d" name="%s"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>'
           "<p:nvPr>%s</p:nvPr></p:nvSpPr>"
           '<p:spPr><a:xfrm><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></a:xfrm></p:spPr>'
           '<p:txBody><a:bodyPr vert="horz" wrap="square" lIns="0" tIns="0" rIns="0" bIns="0" anchor="%s" anchorCtr="0" '
           'rtlCol="0"><a:noAutofit/></a:bodyPr>%s<a:p>%s</a:p></p:txBody></p:sp>'
           % (DECL, sid, esc(name), _ph_tag(kind, idx), emu(x), emu(y), emu(w), emu(h), anchor,
              lst_style(kit, levels, align), run))
    return etree.fromstring(xml)


def textbox(kit, sid, name, x, y, w, h, text, style, anchor="t", align="l", colour=None, user_drawn=True):
    """A text box that belongs to no placeholder: its size, pitch and colour are written on it."""
    (size, pitch), _, _ = kit.styles[style]
    xml = ('<p:sp %s><p:nvSpPr><p:cNvPr id="%d" name="%s"/><p:cNvSpPr txBox="1"/><p:nvPr%s/></p:nvSpPr>'
           '<p:spPr><a:xfrm><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/>'
           '</a:prstGeom><a:noFill/></p:spPr>'
           '<p:txBody><a:bodyPr wrap="square" lIns="0" tIns="0" rIns="0" bIns="0" anchor="%s"><a:noAutofit/></a:bodyPr>'
           '<a:lstStyle/><a:p><a:pPr algn="%s"><a:lnSpc><a:spcPts val="%d"/></a:lnSpc></a:pPr><a:r>%s<a:t>%s</a:t></a:r>'
           "</a:p></p:txBody></p:sp>"
           % (DECL, sid, esc(name), ' userDrawn="1"' if user_drawn else "", emu(x), emu(y), emu(w), emu(h), anchor,
              align, int(pitch * 100), _rpr(kit, style, "a:rPr", colour), esc(text)))
    return etree.fromstring(xml)


def rule(sid, x, y, w, colour, name="Rule", weight=0.75):
    xml = ('<p:cxnSp %s><p:nvCxnSpPr><p:cNvPr id="%d" name="%s"/><p:cNvCxnSpPr/><p:nvPr/></p:nvCxnSpPr>'
           '<p:spPr><a:xfrm><a:off x="%d" y="%d"/><a:ext cx="%d" cy="0"/></a:xfrm><a:prstGeom prst="line"><a:avLst/>'
           '</a:prstGeom><a:ln w="%d"><a:solidFill>%s</a:solidFill></a:ln></p:spPr></p:cxnSp>'
           % (DECL, sid, name, emu(x), emu(y), emu(w), emu(weight), clr(colour)))
    return etree.fromstring(xml)


def vrule(sid, x, y, h, colour, name="Rule", weight=0.75):
    xml = ('<p:cxnSp %s><p:nvCxnSpPr><p:cNvPr id="%d" name="%s"/><p:cNvCxnSpPr/><p:nvPr/></p:nvCxnSpPr>'
           '<p:spPr><a:xfrm><a:off x="%d" y="%d"/><a:ext cx="0" cy="%d"/></a:xfrm><a:prstGeom prst="line"><a:avLst/>'
           '</a:prstGeom><a:ln w="%d"><a:solidFill>%s</a:solidFill></a:ln></p:spPr></p:cxnSp>'
           % (DECL, sid, name, emu(x), emu(y), emu(h), emu(weight), clr(colour)))
    return etree.fromstring(xml)


def panel(sid, x, y, w, h, fill, name="Panel"):
    """A filled rectangle with no outline and no text: the ground under one part of an exhibit."""
    xml = ('<p:sp %s><p:nvSpPr><p:cNvPr id="%d" name="%s"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
           '<p:spPr><a:xfrm><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/>'
           '</a:prstGeom><a:solidFill>%s</a:solidFill><a:ln><a:noFill/></a:ln></p:spPr></p:sp>'
           % (DECL, sid, name, emu(x), emu(y), emu(w), emu(h), clr(fill)))
    return etree.fromstring(xml)


def dot(sid, x, y, size, fill, name="Mark"):
    xml = ('<p:sp %s><p:nvSpPr><p:cNvPr id="%d" name="%s"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
           '<p:spPr><a:xfrm><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></a:xfrm><a:prstGeom prst="ellipse"><a:avLst/>'
           '</a:prstGeom><a:solidFill>%s</a:solidFill><a:ln><a:noFill/></a:ln></p:spPr></p:sp>'
           % (DECL, sid, name, emu(x), emu(y), emu(size), emu(size), clr(fill)))
    return etree.fromstring(xml)


def picture(sid, name, rid, x, y, w, h, descr):
    xml = ('<p:pic %s><p:nvPicPr><p:cNvPr id="%d" name="%s" descr="%s"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/>'
           '</p:cNvPicPr><p:nvPr userDrawn="1"/></p:nvPicPr><p:blipFill><a:blip r:embed="%s"/><a:stretch><a:fillRect/>'
           '</a:stretch></p:blipFill><p:spPr><a:xfrm><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
           '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>'
           % (DECL, sid, esc(name), esc(descr), rid, emu(x), emu(y), emu(w), emu(h)))
    return etree.fromstring(xml)


# ---------------------------------------------------------------- the master and its layouts


def _theme(prs, kit):
    part = prs.slide_master.part.part_related_by(RT.THEME)
    root = etree.fromstring(part.blob)
    look = kit.look
    root.set("name", look.get("name") or "Deck")
    scheme = root.find(".//a:clrScheme", NS)
    scheme.set("name", look.get("name") or "Deck")
    series = list(kit.marks.get("series") or [])
    colours = {"dk1": kit.ink["ink"], "lt1": kit.ink["ground"], "dk2": kit.dark["ground"], "lt2": kit.ink["raised"],
               "accent1": kit.marks["highlight"], "accent2": kit.marks["neutral"],
               "accent3": (series + [kit.ink["second"]] * 3)[1], "accent4": kit.ink["second"],
               "accent5": kit.dark["ink"], "accent6": kit.ink["hairline"],
               "hlink": kit.ink["ink"], "folHlink": kit.ink["second"]}
    for child in scheme:
        tag = etree.QName(child).localname
        if tag in colours:
            for old in list(child):
                child.remove(old)
            etree.SubElement(child, "{%s}srgbClr" % NS["a"]).set("val", colours[tag])
    fonts = root.find(".//a:fontScheme", NS)
    fonts.set("name", look.get("name") or "Deck")
    for group in ("a:majorFont", "a:minorFont"):
        node = fonts.find(group, NS)
        for old in list(node):
            node.remove(old)
        etree.SubElement(node, "{%s}latin" % NS["a"]).set("typeface", kit.face)
        etree.SubElement(node, "{%s}ea" % NS["a"]).set("typeface", "")
        etree.SubElement(node, "{%s}cs" % NS["a"]).set("typeface", "")
    part._blob = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def _clear(tree):
    for child in list(tree):
        if etree.QName(child).localname not in ("nvGrpSpPr", "grpSpPr"):
            tree.remove(child)


def _background(c_sld, colour):
    old = c_sld.find("p:bg", NS)
    if old is not None:
        c_sld.remove(old)
    c_sld.insert(0, etree.fromstring(
        '<p:bg %s><p:bgPr><a:solidFill>%s</a:solidFill><a:effectLst/></p:bgPr></p:bg>'
        % (DECL, clr(colour))))


def _add_layout(prs):
    """One more layout on the master: the default template carries eleven and a deck has a layout a page type."""
    master = prs.slide_master
    source = prs.slide_layouts[0].part
    package = prs.part.package
    partname = package.next_partname("/ppt/slideLayouts/slideLayout%d.xml")
    part = SlideLayoutPart.load(PackURI(str(partname)), source.content_type, package, source.blob)
    part.relate_to(master.part, RT.SLIDE_MASTER)
    rid = master.part.relate_to(part, RT.SLIDE_LAYOUT)
    lst = master._element.find("p:sldLayoutIdLst", NS)
    ids = [int(el.get("id")) for el in lst] + [2147483648]
    el = etree.SubElement(lst, "{%s}sldLayoutId" % NS["p"])
    el.set("id", str(max(ids) + 1))
    el.set("{%s}id" % NS["r"], rid)


def layout_boxes(kit):
    """Every layout's placeholders: (idx, name, kind, x, y, w, h, anchor, levels, align). The positions of
    the grouped boxes (rows and columns) are the layout's own; a slide moves them to fit what it holds."""
    k = kit
    X, CW, bt, bb = k.X0, k.CW, k.body_top, k.body_bottom
    bh = bb - bt
    part = k.part
    title = ("title", "Title", "title", X, k.title_y, CW, k.title_h, "t", [("title", None)], "l")
    source = (IDX_SOURCE, "Source", "body", X, k.source_y, CW, k.small_line, "b", [("small", None)], "l")
    hl = k.sc["headline"][1]
    lead, body, small = k.sc["lead"][1], k.sc["body"][1], k.small_line
    tx, tw = part(8, 4)
    tx, tw = tx + k.G, tw - k.G
    ex, ew = part(0, 8)
    head_h = k.styles["head"][0][1]
    take = [("lead", None), ("body-second", "•")]
    out = {}

    cover_top = k.H * 0.13
    cover_end = k.H * 0.66
    cw3 = part(0, 3)[1]
    out["Cover"] = [
        ("title", "Title", "title", X, cover_top, part(0, 11)[1], cover_end - cover_top, "b", [("display-dark", None)], "l"),
        (IDX_LEAD, "Subtitle", "body", X, cover_end + lead * 0.6, part(0, 9)[1], 2 * lead, "t", [("lead-dark", None)], "l"),
    ] + [(GROUP_C + i, "Fact %d" % (i + 1), "body", part(3 * i, 3)[0], k.H - k.sc["bottom"] - 2 * small, cw3, 2 * small, "b",
          [("small-dark", None), ("small-dark-ink", None)], "l") for i in range(3)]

    rows = []
    for i in range(5):
        y = bt + i * bh / 5.0 + k.pad
        rows.append((GROUP_A + i, "Block %d label" % (i + 1), "body", part(0, 3)[0], y, part(0, 3)[1], bh / 5.0 - k.pad, "t",
                     [("body-second", None)], "l"))
        rows.append((GROUP_B + i, "Block %d" % (i + 1), "body", part(3, 9)[0], y, part(3, 9)[1], bh / 5.0 - k.pad, "t",
                     [("lead", None), ("body-second", "•")], "l"))
    out["Summary"] = [title] + rows + [source]

    rows = []
    for i in range(GROUP):
        y = bt + i * bh / 6.0 + k.pad
        rows.append((GROUP_A + i, "Item %d number" % (i + 1), "body", part(0, 1)[0], y, part(0, 1)[1], lead, "t",
                     [("lead-second", None)], "l"))
        rows.append((GROUP_B + i, "Item %d" % (i + 1), "body", part(1, 9)[0], y, part(1, 9)[1], bh / 6.0 - k.pad, "t",
                     [("lead", None), ("body-second", None)], "l"))
    out["Agenda"] = [title] + rows

    out["Section"] = [
        ("title", "Title", "title", part(2, 6)[0], bb - 3 * hl, part(2, 6)[1], 3 * hl, "b", [("headline", None)], "l"),
        (IDX_NUM, "Section number", "body", X, bb - hl, part(0, 2)[1], hl, "b", [("number", None)], "l"),
        (IDX_TRACK, "Sections", "body", part(9, 3)[0], bb - 8 * body, part(9, 3)[1], 8 * body, "b",
         [("body-second", None), ("body", None)], "l"),
    ]

    out["Chart"] = [
        title,
        (IDX_HEAD, "Chart head", "body", ex, bt + k.pad, ew, head_h, "t", [("head", None)], "l"),
        (IDX_EXHIBIT, "Chart", "chart", ex, bt + k.pad + head_h + 6, ew, bb - bt - k.pad - head_h - 6, "t",
         [("body", None)], "l"),
        (IDX_TAKEAWAY, "Takeaway", "body", tx, bt + k.pad, tw, bh - k.pad, "t", take, "l"),
        source,
    ]

    cols = []
    cw4 = (CW - 3 * 2 * k.G) / 4.0
    fig = k.sc["figure"][1]
    for i in range(4):
        x = X + i * (cw4 + 2 * k.G)
        cols.append((GROUP_A + i, "Figure %d name" % (i + 1), "body", x, bt + k.pad, cw4, body, "t", [("body-second", None)], "l"))
        cols.append((GROUP_B + i, "Figure %d" % (i + 1), "body", x, bt + k.pad + body, cw4, fig, "t", [("figure", None)], "l"))
        cols.append((GROUP_C + i, "Figure %d text" % (i + 1), "body", x, bt + k.pad + body + fig + 4, cw4, 6 * body, "t",
                     [("body", None), ("body-second", None)], "l"))
    under = (IDX_TAKEAWAY, "Takeaway", "body", X, bb - 3 * lead, part(0, 9)[1], 3 * lead, "t", [("lead", None)], "l")
    out["Figures"] = [title] + cols + [under, source]

    table = (IDX_EXHIBIT, "Table", "tbl", X, bt, CW, bh, "t", [("body", None)], "l")
    out["Comparison"] = [title, table, source]
    out["Table"] = [
        title,
        (IDX_HEAD, "Table head", "body", ex, bt + k.pad, ew, head_h, "t", [("head", None)], "l"),
        (IDX_EXHIBIT, "Table", "tbl", ex, bt + k.pad + head_h + 6, ew, bh - k.pad - head_h - 6, "t", [("body", None)], "l"),
        (IDX_TAKEAWAY, "Takeaway", "body", tx, bt + k.pad, tw, bh - k.pad, "t", take, "l"),
        source,
    ]

    cols = []
    cw6 = (CW - 5 * 2 * k.G) / 6.0
    for i in range(GROUP):
        x = X + i * (cw6 + 2 * k.G)
        cols.append((GROUP_A + i, "Step %d number" % (i + 1), "body", x, bt + k.pad, cw6, fig, "t", [("figure-second", None)], "l"))
        cols.append((GROUP_C + i, "Step %d" % (i + 1), "body", x, bt + k.pad + fig + 6, cw6, 8 * body, "t",
                     [("lead", None), ("body-second", None)], "l"))
    out["Process"] = [title] + cols + [under, source]

    cols = []
    axis = bt + bh / 2.0
    for i in range(GROUP):
        x = X + i * CW / 6.0
        above = i % 2 == 0
        cols.append((GROUP_C + i, "Milestone %d" % (i + 1), "body", x, bt if above else axis + 14, CW / 3.0 - k.G,
                     axis - 14 - bt if above else bb - axis - 14, "b" if above else "t",
                     [("body-second", None), ("lead", None), ("body-second", None)], "l"))
    out["Timeline"] = [title] + cols + [source]

    rows = [(IDX_LEAD, "Statement", "body", part(0, 5)[0], bt + k.pad, part(0, 5)[1], bh - k.pad, "t", [("lead", None)], "l")]
    for i in range(GROUP):
        y = bt + i * bh / 6.0 + k.pad
        rows.append((GROUP_B + i, "Point %d" % (i + 1), "body", part(6, 6)[0], y, part(6, 6)[1], bh / 6.0 - k.pad, "t",
                     [(k.point_style, None), ("body-second", None)], "l"))
    out["Text"] = [title] + rows + [source]

    # A 2x2 matrix: the four quadrants' names (the highlighted one takes the second level, full ink), the six
    # words of the two axes, and the takeaway. The page moves them onto the matrix it draws.
    gut = part(0, 1)[1] + k.G
    mx, mw, my, mh = ex + gut, ew - gut, bt + k.pad, bh - k.pad - head_h - 6
    quads = []
    for i, name in enumerate(("top left", "top right", "bottom left", "bottom right")):
        quads.append((GROUP_A + i, "Quadrant %s" % name, "body", mx + (i % 2) * mw / 2.0 + k.pad, my + (i // 2) * mh / 2.0 + k.pad,
                      mw / 2.0 - 2 * k.pad, body, "t", [("body-second", None), ("body", None)], "l"))
    axes = [
        (IDX_AXIS, "X axis", "body", mx + mw / 3.0, my + mh + 6, mw / 3.0, head_h, "t", [("head", None)], "ctr"),
        (IDX_AXIS + 1, "X low", "body", mx, my + mh + 6, mw / 3.0, head_h, "t", [("head-second", None)], "l"),
        (IDX_AXIS + 2, "X high", "body", mx + 2 * mw / 3.0, my + mh + 6, mw / 3.0, head_h, "t", [("head-second", None)], "r"),
        (IDX_AXIS + 3, "Y axis", "body", ex, my + head_h, gut - k.G, mh - 2 * head_h, "ctr", [("head", None)], "l"),
        (IDX_AXIS + 4, "Y low", "body", ex, my + mh - head_h, gut - k.G, head_h, "b", [("head-second", None)], "l"),
        (IDX_AXIS + 5, "Y high", "body", ex, my, gut - k.G, head_h, "t", [("head-second", None)], "l"),
    ]
    out["Matrix"] = [title] + quads + axes + [(IDX_TAKEAWAY, "Takeaway", "body", tx, bt + k.pad, tw, bh - k.pad, "t", take, "l"),
                                               source]

    out["Figure"] = [
        title,
        (IDX_HEAD, "Caption", "body", ex, bt + k.pad, ew, head_h, "t", [("head", None)], "l"),
        (IDX_EXHIBIT, "Picture", "pic", ex, bt + k.pad + head_h + 6, ew, bh - k.pad - head_h - 6, "t", [("body", None)], "l"),
        (IDX_TAKEAWAY, "Takeaway", "body", tx, bt + k.pad, tw, bh - k.pad, "t", take, "l"),
        source,
    ]

    qx, qw = part(0, 10)
    out["Quote"] = [
        title,
        (IDX_LEAD, "Quote", "body", qx, bt + bh * 0.18, qw, 3 * hl, "t", [("headline", None)], "l"),
        (IDX_NAME, "Quote name", "body", qx, bt + bh * 0.18 + 3 * hl + 2 * k.pad, qw, lead, "t", [("lead", None)], "l"),
        (IDX_ROLE, "Quote role", "body", qx, bt + bh * 0.18 + 3 * hl + 2 * k.pad + lead, qw, body, "t", [("body-second", None)], "l"),
        source,
    ]

    out["Next steps"] = [title, table, source]

    rows = []
    for i in range(LISTED):
        y = bt + i * bh / float(LISTED)
        rows.append((GROUP_A + i, "Backup %d number" % (i + 1), "body", part(5, 1)[0], y, part(5, 1)[1], body, "t",
                     [("body-second", None)], "l"))
        rows.append((GROUP_B + i, "Backup %d" % (i + 1), "body", part(6, 6)[0], y, part(6, 6)[1], bh / float(LISTED), "t",
                     [("body", None)], "l"))
    out["Appendix"] = [("title", "Title", "title", X, bb - 3 * hl, part(0, 4)[1], 3 * hl, "b", [("headline", None)], "l")] + rows

    close_end = k.H * 0.6
    out["Closing"] = [
        ("title", "Title", "title", X, k.H * 0.13, part(0, 11)[1], close_end - k.H * 0.13, "b", [("display-dark", None)], "l"),
        (IDX_LEAD, "Contact", "body", X, close_end + body, part(0, 8)[1], 4 * body, "t", [("body-dark", None)], "l"),
        (IDX_SMALL, "Small print", "body", X, k.H - k.sc["bottom"] - 2 * small, part(0, 9)[1], 2 * small, "b",
         [("small-dark", None)], "l"),
    ]
    return out


def _running(kit, tree, part, name, organisation, ids):
    """The running line of a layout: the organisation (logo or name), the deck title, the section and the
    page number, each in a box of one height on one line, so all four stand on one baseline."""
    dark = name in DARK
    y, h = kit.running_y, kit.small_line
    second = "small-dark" if dark else "small"
    logo = kit.look.get("logo") or {}
    file = logo.get("dark_file" if dark else "file") or ""
    ox, ow = kit.page_span(0, 4)
    if file:
        path = file if os.path.isabs(file) else os.path.join(kit.look["_folder"], file)
        if not os.path.isfile(path):
            raise Refused("the look names the logo %s, which is not there" % file)
        from PIL import Image
        with Image.open(path) as im:
            ratio = im.size[0] / float(im.size[1])
        height = float(logo.get("height", 12))
        size = kit.styles[second][0][0]
        baseline = y + h - (kit.small_line - size) / 2.0 - size * 0.22
        _, rid = part.get_or_add_image_part(path)
        tree.append(picture(next(ids), "Logo", rid, kit.M, baseline - height * (1 - float(logo.get("below_baseline", 0))),
                            height * ratio, height, logo.get("alt") or organisation))
    elif organisation:
        tree.append(textbox(kit, next(ids), "Organisation", ox, y, ow, h, organisation, second, anchor="b"))
    if name == "Cover":
        return
    if name != "Closing":
        fx, fw = kit.page_span(4, 4)
        tree.append(placeholder(kit, next(ids), "Deck title", "ftr", IDX_FOOTER, fx, y, fw, h, "b", [(second, None)]))
        if name not in ("Section", "Appendix"):
            if kit.c0:
                sx, sw = kit.page_span(0, kit.c0)
                tree.append(placeholder(kit, next(ids), "Section", "body", IDX_SECTION, sx, kit.title_y + 4, sw - kit.G,
                                        3 * h, "t", [(second, None)]))
            else:
                sx, sw = kit.page_span(8, 3)
                tree.append(placeholder(kit, next(ids), "Section", "body", IDX_SECTION, sx, y, sw, h, "b", [(second, None)]))
    nx, nw = kit.page_span(11, 1)
    tree.append(placeholder(kit, next(ids), "Page number", "sldNum", IDX_NUMBER, nx, y, nw, h, "b", [(second, None)], "r"))


def bare(kit, organisation):
    """A presentation holding one master and a layout per page type, and no slide."""
    prs = Presentation()
    prs.slide_width, prs.slide_height = Emu(emu(kit.W)), Emu(emu(kit.H))
    _theme(prs, kit)
    master = prs.slide_master
    m = master._element
    _background(m.cSld, kit.ink["ground"])
    tree = m.cSld.spTree
    _clear(tree)
    ids = itertools.count(2)
    tree.append(placeholder(kit, next(ids), "Title", "title", 0, kit.X0, kit.title_y, kit.CW, kit.title_h, "t", [("title", None)]))
    tree.append(placeholder(kit, next(ids), "Text", "body", 1, kit.X0, kit.body_top, kit.CW, kit.body_bottom - kit.body_top,
                            "t", [("body", None), ("body-second", "•")]))
    fx, fw = kit.page_span(4, 4)
    nx, nw = kit.page_span(11, 1)
    tree.append(placeholder(kit, next(ids), "Deck title", "ftr", IDX_FOOTER, fx, kit.running_y, fw, kit.small_line, "b", [("small", None)]))
    tree.append(placeholder(kit, next(ids), "Page number", "sldNum", IDX_NUMBER, nx, kit.running_y, nw, kit.small_line, "b",
                            [("small", None)], "r"))
    # The master's own text styles: one face, the look's weight, exact line pitch, no bullet at level one.
    styles = m.find("p:txStyles", NS)
    for child in list(styles):
        styles.remove(child)
    for tag, first, rest in (("titleStyle", ("title", None), ("title", None)),
                             ("bodyStyle", ("body", None), ("body-second", "•")),
                             ("otherStyle", ("body", None), ("body", None))):
        node = etree.SubElement(styles, "{%s}%s" % (NS["p"], tag))
        for n in range(1, 10):
            style, bullet = first if n == 1 else rest
            node.append(etree.fromstring("<x %s>%s</x>" % (DECL, _lvl(kit, 1, style, bullet, "l")))[0])
            node[-1].tag = "{%s}lvl%dpPr" % (NS["a"], n)

    while len(prs.slide_layouts) < len(LAYOUTS):
        _add_layout(prs)
    for layout in list(prs.slide_layouts)[len(LAYOUTS):]:
        prs.slide_layouts.remove(layout)
    boxes = layout_boxes(kit)
    for layout, name in zip(prs.slide_layouts, LAYOUTS):
        el = layout._element
        el.cSld.set("name", name)
        el.set("showMasterSp", "0")
        el.set("preserve", "1")
        el.set("userDrawn", "1")
        if el.get("type"):
            del el.attrib["type"]
        _background(el.cSld, kit.dark["ground"] if name in DARK else kit.ink["ground"])
        tree = el.cSld.spTree
        _clear(tree)
        ids = itertools.count(2)
        specs = boxes[name]
        for idx, label, kind, x, y, w, h, anchor, levels, align in specs[:1]:
            tree.append(placeholder(kit, next(ids), label, kind, 0 if idx == "title" else idx, x, y, w, h, anchor, levels, align))
        for idx, label, kind, x, y, w, h, anchor, levels, align in specs[1:]:
            tree.append(placeholder(kit, next(ids), label, kind, idx, x, y, w, h, anchor, levels, align))
        _running(kit, tree, layout.part, name, organisation, ids)
    return prs


# ---------------------------------------------------------------- slides


def Page(prs, kit, layout_name, kind, deck_title, section):
    """A page of the output being written: a slide of the PowerPoint file, or a page of the HTML the PDF is
    printed from (deck_html.py). The page types below lay a page out through this one set of calls (put,
    place, drop, rule, dot, panel, label, chart, table, picture), so both outputs stand on the same positions."""
    make = getattr(prs, "page", None)
    if make is not None:
        return make(kit, layout_name, kind, deck_title, section)
    return Slide(prs, kit, layout_name, kind, deck_title, section)


class Slide:
    """One slide being filled: its placeholders by idx, and the helpers that fill, move and drop them."""

    def __init__(self, prs, kit, layout_name, kind, deck_title, section):
        layout = next((la for la in prs.slide_layouts if la.name == layout_name), None)
        if layout is None:
            raise Refused("the master has no layout %s" % layout_name)
        self.kit, self.slide, self.layout = kit, prs.slides.add_slide(layout), layout
        self.slide._element.cSld.set("name", kind)
        names = {p.placeholder_format.idx: p.name for p in layout.placeholders}
        self.ph = {}
        for shape in self.slide.placeholders:
            idx = shape.placeholder_format.idx
            shape.name = names.get(idx, shape.name)
            self.ph[idx] = shape
        self.tree = self.slide.shapes._spTree
        self._ids = itertools.count(max([int(s.shape_id) for s in self.slide.shapes] + [1]) + 100)
        self.notes = []
        # The running line: PowerPoint shows a layout's footer and page number only on a slide that carries them.
        for base in layout.placeholders:
            kind_ = base.placeholder_format.type
            if kind_ == PP_PLACEHOLDER.FOOTER and deck_title:
                self.tree.append(self._field(base, "ftr", deck_title))
            elif kind_ == PP_PLACEHOLDER.SLIDE_NUMBER:
                # A backup page is numbered in the appendix's own count (A1, A2), a page of the storyline by its place.
                self.tree.append(self._field(base, "sldNum", getattr(kit, "number", None)))
        if IDX_SECTION in self.ph:
            self.put(IDX_SECTION, [section] if section else [])

    def sid(self):
        return next(self._ids)

    def _field(self, base, kind, text):
        idx = base.placeholder_format.idx
        run = ('<a:fld id="{B6F15528-21DE-4FAA-801E-634DDDAF4B2B}" type="slidenum"><a:rPr lang="%s"/><a:t>‹#›</a:t></a:fld>'
               % self.kit.language if text is None else '<a:r><a:rPr lang="%s"/><a:t>%s</a:t></a:r>' % (self.kit.language, esc(text)))
        return etree.fromstring(
            '<p:sp %s><p:nvSpPr><p:cNvPr id="%d" name="%s"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr>'
            '<p:ph type="%s" sz="quarter" idx="%d"/></p:nvPr></p:nvSpPr><p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/>'
            "<a:p>%s</a:p></p:txBody></p:sp>" % (DECL, self.sid(), esc(base.name), kind, idx, run))

    def put(self, idx, paras):
        """Fill a placeholder with paragraphs given as text or (text, level); an empty list removes it.
        Only words and levels are written: size, face, colour, spacing and bullets come from the layout."""
        shape = self.ph.get(idx)
        if shape is None:
            return None
        paras = [p for p in paras if (p[0] if isinstance(p, tuple) else p)]
        if not paras:
            self.drop(idx)
            return None
        frame = shape.text_frame
        for n, item in enumerate(paras):
            text, level = item if isinstance(item, tuple) else (item, 0)
            para = frame.paragraphs[0] if n == 0 else frame.add_paragraph()
            para.text = str(text)
            if level:
                para.level = level
        return shape

    def drop(self, idx):
        shape = self.ph.pop(idx, None)
        if shape is not None:
            shape._element.getparent().remove(shape._element)

    def place(self, idx, x, y, w, h):
        shape = self.ph.get(idx)
        if shape is not None:
            shape.left, shape.top, shape.width, shape.height = Emu(emu(x)), Emu(emu(y)), Emu(emu(w)), Emu(emu(h))

    def rule(self, x, y, w, strong=False, name="Rule"):
        colour = self.kit.ink["rule"] if strong else self.kit.ink["hairline"]
        self.tree.append(rule(self.sid(), x, y, w, colour, name=name))

    def vrule(self, x, y, h, strong=False, name="Rule"):
        colour = self.kit.ink["rule"] if strong else self.kit.ink["hairline"]
        self.tree.append(vrule(self.sid(), x, y, h, colour, name=name))

    def title(self, text, part=None):
        if part and part[1] > 1:
            text = "%s (%d/%d)" % (text, part[0], part[1])
        self.put(0, [text])

    def finish(self, page):
        self.put(IDX_SOURCE, [page.get("source") or ""])
        notes = [page.get("notes") or ""] + self.notes
        notes = [n for n in notes if n]
        if notes:
            self.slide.notes_slide.notes_text_frame.text = "\n".join(notes)

    # -- what a page draws besides its placeholders

    def dot(self, x, y, size, fill, name="Mark"):
        self.tree.append(dot(self.sid(), x, y, size, fill, name=name))

    def panel(self, x, y, w, h, fill, name="Panel"):
        """A ground under part of an exhibit: it lies under everything else on the slide."""
        self.tree.insert(2, panel(self.sid(), x, y, w, h, fill, name=name))

    def label(self, name, x, y, w, h, text, style, align="l", colour=None):
        """Words that belong to an exhibit and to no placeholder: a series' name, an item's name."""
        self.tree.append(textbox(self.kit, self.sid(), name, x, y, w, h, text, style, align=align, colour=colour,
                                 user_drawn=False))

    def chart(self, kind, cats, series, page, x, y, w, h, alt):
        data = CategoryChartData(number_format=number_format(page.get("decimals", 0)))
        data.categories = cats
        for s in series:
            data.add_series(str(s.get("name") or ""), [None if v is None else float(v) for v in s["values"]])
        holder = self.ph.pop(IDX_EXHIBIT)
        frame = holder.insert_chart(CHARTS[kind], data)
        frame.left, frame.top, frame.width, frame.height = Emu(emu(x)), Emu(emu(y)), Emu(emu(w)), Emu(emu(h))
        frame.name = "Chart"
        frame._element.xpath("./p:nvGraphicFramePr/p:cNvPr")[0].set("descr", alt)
        style_chart(self.kit, self, frame, kind, cats, series, page, x, y, w, h)
        return frame

    def table(self, plan, x, y, highlight_row=None, highlight_col=None, label_col=False):
        return write_table(self.kit, self, plan, x, y, highlight_row, highlight_col, label_col)

    def settle(self, frame, top):
        frame.top = Emu(emu(top))

    def picture(self, path, x, y, w, h, alt, pixels=None):
        holder = self.ph.pop(IDX_EXHIBIT)
        pic = holder.insert_picture(path)
        pic.left, pic.top, pic.width, pic.height = Emu(emu(x)), Emu(emu(y)), Emu(emu(w)), Emu(emu(h))
        pic.crop_left = pic.crop_right = pic.crop_top = pic.crop_bottom = 0
        pic.name = "Figure"
        pic._element.xpath("./p:nvPicPr/p:cNvPr")[0].set("descr", alt)
        paint(pic.line.color, self.kit.ink["hairline"])
        pic.line.width = Pt(0.75)
        return pic


def detail(kit, page, items):
    """A piece's supporting detail goes on the page, or into the speaker notes when the preset keeps pages lean."""
    items = [str(i) for i in items if i]
    if kit.build.get("detail") == "notes":
        page.notes.extend(items)
        return []
    return items


def spread(kit, heights, top, bottom, slack=3.0):
    """Tops and heights for rows of the given text heights between top and bottom. Every row gets the same
    pitch, that of the tallest plus at most `slack` body lines of clear space, so one long row does not break
    the rhythm; and when the rows do not fill the body the block sits on its middle, not under the title."""
    n = len(heights)
    room = bottom - top
    pitch = min(room / float(n), max(heights) + kit.pad + slack * kit.body_line)
    start = top + max(0.0, (room - n * pitch) / 2.0)
    return [start + i * pitch for i in range(n)], [pitch] * n


def rows_bottom(kit, page):
    """Where a page of rows may end: the body's foot, or the source line's when the page has no source."""
    return kit.body_bottom if page.get("source") else kit.source_y + kit.small_line


def page_cover(prs, kit, deck, page):
    pg = Page(prs, kit, "Cover", "cover", "", "")
    pg.title(page["title"])
    pg.put(IDX_LEAD, [page.get("subtitle") or ""])
    meta = list(page.get("meta") or [])[:3]
    for i in range(3):
        if i < len(meta):
            fact = meta[i]
            if isinstance(fact, dict):
                pg.put(GROUP_C + i, [(fact.get("key") or "", 0), (fact.get("value") or "", 1)])
            else:
                pg.put(GROUP_C + i, [(str(fact), 1)])
        else:
            pg.drop(GROUP_C + i)
    return pg


def page_summary(prs, kit, deck, page):
    pg = Page(prs, kit, "Summary", "summary", deck["title"], page.get("section") or "")
    pg.title(page["title"], page.get("_part"))
    blocks = page.get("blocks") or []
    if not 1 <= len(blocks) <= 5:
        raise Refused("a summary page holds one to five blocks, one per section; this one has %d" % len(blocks))
    lx, lw = kit.part(0, 3)
    tx, tw = kit.part(3, 9)
    filled, heights = [], []
    for block in blocks:
        points = detail(kit, pg, block.get("points") or [])
        paras = [(block.get("lead") or "", 0)] + [(p, 1) for p in points]
        indent = kit.styles["body-second"][0][0] * 0.95
        h = kit.text_h([(block.get("lead") or "", "lead")], tw) + (kit.styles["lead"][2] if points else 0) \
            + kit.text_h([(p, "body-second") for p in points], tw, indent)
        filled.append(paras)
        heights.append(h)
    tops, rows = spread(kit, heights, kit.body_top, rows_bottom(kit, page))
    for i in range(5):
        if i >= len(blocks):
            pg.drop(GROUP_A + i)
            pg.drop(GROUP_B + i)
            continue
        y = tops[i]
        pg.rule(kit.X0, y, kit.CW)
        pg.put(GROUP_A + i, [blocks[i].get("section") or ""])
        pg.place(GROUP_A + i, lx, y + kit.pad, lw, rows[i] - kit.pad - 1)
        pg.put(GROUP_B + i, filled[i])
        pg.place(GROUP_B + i, tx, y + kit.pad, tw, rows[i] - kit.pad - 1)
    return pg


def page_agenda(prs, kit, deck, page):
    pg = Page(prs, kit, "Agenda", "agenda", deck["title"], "")
    pg.title(page["title"])
    items = page.get("items") or []
    if not 2 <= len(items) <= GROUP:
        raise Refused("an agenda lists two to six sections; this one has %d" % len(items))
    nx, nw = kit.part(0, 1)
    tx, tw = kit.part(1, 9)
    heights = [kit.text_h([(it.get("name") or "", "lead")] + ([(it["text"], "body-second")] if it.get("text") else []), tw)
               + (kit.styles["lead"][2] if it.get("text") else 0) for it in items]
    tops, rows = spread(kit, heights, kit.body_top, rows_bottom(kit, page))
    for i in range(GROUP):
        if i >= len(items):
            pg.drop(GROUP_A + i)
            pg.drop(GROUP_B + i)
            continue
        y = tops[i]
        pg.rule(kit.X0, y, kit.CW)
        pg.put(GROUP_A + i, ["%02d" % (i + 1)])
        pg.place(GROUP_A + i, nx, y + kit.pad, nw, kit.sc["lead"][1])
        pg.put(GROUP_B + i, [(items[i].get("name") or "", 0), (items[i].get("text") or "", 1)])
        pg.place(GROUP_B + i, tx, y + kit.pad, tw, rows[i] - kit.pad - 1)
    return pg


def page_section(prs, kit, deck, page):
    pg = Page(prs, kit, "Section", "section", deck["title"], "")
    pg.title(page["title"])
    names = deck["_sections"]
    number = names.index(page["title"]) + 1 if page["title"] in names else 0
    pg.put(IDX_NUM, ["%02d" % number] if number else [])
    pg.put(IDX_TRACK, [(name, 1 if name == page["title"] else 0) for name in names] if len(names) > 1 else [])
    return pg


def exhibit_frame(kit, with_takeaway):
    if with_takeaway:
        ex, ew = kit.part(0, 8)
        tx, tw = kit.part(8, 4)
        return ex, ew, tx + kit.G, tw - kit.G
    return kit.X0, kit.CW, None, None


def takeaway(kit, pg, page, tx, tw, top):
    points = detail(kit, pg, page.get("points") or [])
    if not page.get("takeaway"):
        pg.drop(IDX_TAKEAWAY)
        return
    pg.rule(tx, top, tw)
    pg.put(IDX_TAKEAWAY, [(page["takeaway"], 0)] + [(p, 1) for p in points])
    pg.place(IDX_TAKEAWAY, tx, top + kit.pad, tw, kit.body_bottom - top - kit.pad)


def number_format(decimals):
    return "#,##0" + ("." + "0" * int(decimals) if decimals else "")


def chart_data_of(page):
    if page.get("bars"):
        cats = [str(b.get("label", "")) for b in page["bars"]]
        series = [{"name": page.get("measure") or "", "values": [b.get("value") for b in page["bars"]]}]
    else:
        cats = [str(c) for c in page.get("categories") or []]
        series = page.get("series") or []
    if not cats or not series:
        raise Refused("a chart page needs its data: categories and series (name, values), or bars (label, value)")
    for s in series:
        if len(s.get("values") or []) != len(cats):
            raise Refused("the series %r has %d values for %d categories" % (s.get("name"), len(s.get("values") or []), len(cats)))
    return cats, series


def page_chart(prs, kit, deck, page):
    pg = Page(prs, kit, "Chart", "chart", deck["title"], page.get("section") or "")
    pg.title(page["title"], page.get("_part"))
    kind = page.get("kind") or "column"
    if kind not in CHART_KINDS:
        raise Refused("the chart kind %r is not one of %s" % (kind, ", ".join(sorted(CHART_KINDS))))
    cats, series = chart_data_of(page)
    # The takeaway stands beside the chart, in a column wide enough for a sentence, or under it, as under a table.
    words = page.get("takeaway") or ""
    below = kit.build.get("takeaway.chart") == "below"
    if words and not below:
        cols = int(kit.build.get("chart.takeaway_columns", 4))
        ex, ew = kit.part(0, 12 - cols)
        tx, tw = kit.part(12 - cols, cols)
        tx, tw = tx + kit.G, tw - kit.G
    else:
        ex, ew, tx, tw = kit.X0, kit.CW, None, None
    top = kit.body_top
    head = ", ".join(str(page[k]) for k in ("measure", "unit", "period") if page.get(k))
    head_h = kit.styles["head"][0][1]
    pg.rule(ex, top, ew)
    pg.put(IDX_HEAD, [head])
    pg.place(IDX_HEAD, ex, top + kit.pad, ew, head_h)
    cy = top + kit.pad + (head_h + 8 if head else 0)
    under, under_w = [], kit.CW
    if words and below:
        under = [(words, 0)] + [(p, 1) for p in detail(kit, pg, page.get("points") or [])]
        room = kit.text_h([(t, "lead" if lv == 0 else "body-second") for t, lv in under], under_w) + 1.5 * kit.pad
    else:
        room = 0.0
    ch = kit.body_bottom - cy - room
    alt = page.get("alt") or ". ".join(x.rstrip(".") for x in (head, page.get("takeaway") or page["title"]) if x) + "."
    pg.chart(kind, cats, series, page, ex, cy, ew, ch, alt[:kit.d.get("alt.max_chars", 250)])
    if under:
        ty = cy + ch + 1.5 * kit.pad
        pg.put(IDX_TAKEAWAY, under)
        pg.place(IDX_TAKEAWAY, ex, ty, under_w, kit.body_bottom - ty)
    else:
        takeaway(kit, pg, page, tx, tw, top)
    return pg


def _c(tag):
    return "{%s}%s" % (NS["c"], tag)


def chart_scale(kind, cats, series, floor=None):
    """The value scale of a chart, (lowest, highest). Bars start at zero because a bar's length is its value. A
    line shows change, and one that runs along the top of an empty plot shows none: its scale starts a little
    under its lowest value, unless the data comes near zero anyway."""
    values = [float(v) for s in series for v in s["values"] if v is not None]
    stacked = kind == "stacked"
    top = max([sum(float(s["values"][i] or 0) for s in series) for i in range(len(cats))]) if stacked else max(values + [0.0])
    low = min(values + [0.0])
    lowest = float(floor) if floor is not None else (min(0.0, low * 1.15))
    if floor is None and low < 0 and kind in ("bar", "column"):
        # a mark below zero carries its value beyond its end: the scale leaves that value room before the names
        lowest = low - 0.12 * (max(top, 0.0) - low)
    highest = top * (1.06 if stacked else 1.16) if top > 0 else 1.0
    if kind == "line" and floor is None and values:
        least = min(values)
        span = (top - least) or abs(top) or 1.0
        if least - 0.35 * span > 0.25 * top:
            lowest, highest = least - 0.35 * span, top + 0.25 * span
    return lowest, highest


def chart_colours(kit, kind, series, highlight):
    """The colour of each series: the look's highlight on the one the page names, neutral tones on the rest. In a
    chart of one series the highlight is a category, and the series itself stays neutral."""
    marks = kit.marks
    multi = len(series) > 1
    tones = [marks["neutral"]] + list(marks.get("series") or [])
    colours = []
    spare = iter(tones)
    for s in series:
        name = str(s.get("name") or "")
        if multi and highlight is not None and name == highlight:
            colours.append(marks["highlight"])
        elif multi:
            colours.append(next(spare, tones[-1]))
        else:
            colours.append(marks["neutral"] if highlight is not None and kind != "line" else marks["highlight"])
    return colours


def style_chart(kit, pg, frame, kind, cats, series, page, fx, fy, fw, fh):
    """Dress a native chart: no title, no legend up to the preset's direct-label limit, values on the marks,
    one highlight in the look's ink and every other mark neutral, horizontal text, a zero baseline."""
    chart = frame.chart
    marks, size = kit.marks, kit.sc["chart"]
    ink, second = kit.ink["ink"], kit.ink["second"]
    highlight = page.get("highlight")
    names = [str(s.get("name") or "") for s in series]
    multi = len(series) > 1
    chart.has_title = False
    chart.font.size = Pt(size)
    chart.font.name = "+mn-lt"          # the theme's face, as every other text: a change of the theme's fonts reaches the charts
    paint(chart.font.color, second)
    chart.has_legend = len(series) > kit.d["legend.direct_max"]
    if chart.has_legend:
        from pptx.enum.chart import XL_LEGEND_POSITION
        chart.legend.position = XL_LEGEND_POSITION.TOP
        chart.legend.include_in_layout = False
    cat = chart.category_axis
    cat.has_major_gridlines = False
    cat.major_tick_mark = XL_TICK_MARK.NONE
    paint(cat.format.line.color, kit.ink["rule"])
    cat.format.line.width = Pt(0.75)
    cat.tick_labels.font.size = Pt(size)
    paint(cat.tick_labels.font.color, second)
    body = cat._element.find(_c("txPr")).find("{%s}bodyPr" % NS["a"])
    body.set("rot", "0")
    body.set("vert", "horz")
    val = chart.value_axis
    val.visible = False
    val.has_major_gridlines = False
    val.has_minor_gridlines = False
    stacked = kind == "stacked"
    # The value axis is not drawn and both ends of every line carry their values.
    val.minimum_scale, val.maximum_scale = chart_scale(kind, cats, series, page.get("axis_min"))
    plot = chart.plots[0]
    plot.vary_by_categories = False
    if kind in ("column", "bar", "stacked"):
        plot.gap_width = int(marks.get("gap_width", 50))
    if kind == "stacked":
        plot.overlap = 100
    if kind == "bar":
        cat.reverse_order = True
    # A mark below zero grows across the baseline, where its category's name would stand on it: the names move to
    # the low end of the value axis, clear of every mark.
    if kind != "line" and any((v or 0) < 0 for one in series for v in one.get("values") or []):
        cat.tick_label_position = XL_TICK_LABEL_POSITION.LOW

    # Which marks carry the look's highlight: a category of a single series, or one series of several.
    colours = chart_colours(kit, kind, series, highlight)
    fmt = number_format(page.get("decimals", 0))
    for n, s in enumerate(chart.series):
        colour = colours[n]
        hollow = colour.upper() == kit.ink["ground"].upper()
        if kind == "line":
            s.smooth = False
            paint(s.format.line.color, marks["outline"] if hollow else colour)
            s.format.line.width = Pt(marks.get("line_width", 2.25) if colour == marks["highlight"] else
                                    marks.get("neutral_line_width", 1.5))
            from pptx.enum.chart import XL_MARKER_STYLE
            s.marker.style = XL_MARKER_STYLE.NONE
        else:
            s.invert_if_negative = False
            s.format.fill.solid()
            paint(s.format.fill.fore_color, colour)
            if hollow:
                paint(s.format.line.color, marks["outline"])
                s.format.line.width = Pt(0.75)
            elif stacked:
                paint(s.format.line.color, kit.ink["ground"])
                s.format.line.width = Pt(0.75)
            if not multi and highlight is not None:
                for i, c in enumerate(cats):
                    if c == str(highlight):
                        point = s.points[i]
                        point.format.fill.solid()
                        paint(point.format.fill.fore_color, marks["highlight"])
    if kind == "line":
        _line_labels(kit, chart, cats, series, colours, fmt)
        last = len(cats) - 1
        places = int(page.get("decimals", 0))
        widest = max(T.measure(format(float(s["values"][last] or 0), ".%df" % places), size, kit.advance) for s in series)
        named = max([T.measure(n, size, kit.advance) for n in names] + [0.0]) if multi else 0.0
        px, py, ph = 0.07, 0.08, 0.78
        pw = max(0.5, 1.0 - px - (widest + 14 + named + 10) / float(fw))
        _manual_layout(chart, px, py, pw, ph)
        between = val._element.find(_c("crossBetween"))
        if between is not None:
            between.set("val", "midCat")
        if multi:
            # Each line is named beside its right end, after its last value; names keep a line's distance.
            line = kit.styles["head"][0][1]
            scale = (val.maximum_scale - val.minimum_scale) or 1.0
            x = fx + fw * (px + pw) + widest + 14
            spots = []
            for n, s in enumerate(series):
                v = float(s["values"][last] or 0)
                spots.append([fy + fh * (py + ph * (1 - (v - val.minimum_scale) / scale)) - line / 2.0, n])
            spots.sort()
            for i in range(1, len(spots)):
                spots[i][0] = max(spots[i][0], spots[i - 1][0] + line)
            for y, n in spots:
                pg.tree.append(textbox(kit, pg.sid(), "Series label", x, y, max(20.0, fx + fw - x), line, names[n], "head",
                                       colour=ink if colours[n] == marks["highlight"] else second, user_drawn=False))
    else:
        plot.has_data_labels = True
        labels = plot.data_labels
        labels.number_format = fmt
        labels.number_format_is_linked = False
        labels.font.size = Pt(size)
        paint(labels.font.color, ink)
        labels.show_value = True
        if stacked:
            fmt = "%s;-%s;" % (fmt, fmt)      # a part that is nothing prints nothing
            labels.number_format = fmt
            labels.position = XL_LABEL_POSITION.CENTER
            for n, s in enumerate(chart.series):
                dark = T_luminance(colours[n]) < 0.3
                s.data_labels.font.size = Pt(size)
                paint(s.data_labels.font.color, marks.get("on_dark", "FFFFFF") if dark else ink)
                s.data_labels.number_format = fmt
                s.data_labels.number_format_is_linked = False
                s.data_labels.show_value = True
                s.data_labels.position = XL_LABEL_POSITION.CENTER
            # The series are named beside the last stack, in the order they are stacked.
            px, py, pw, ph = 0.0, 0.05, 0.8, 0.82
            _manual_layout(chart, px, py, pw, ph)
            run, last = 0.0, len(cats) - 1
            scale = val.maximum_scale - val.minimum_scale
            line = kit.styles["head"][0][1]
            for n, s in enumerate(series):
                v = float(s["values"][last] or 0)
                mid = run + v / 2.0
                run += v
                y = fy + fh * (py + ph * (1 - (mid - val.minimum_scale) / scale)) - line / 2.0
                x = fx + fw * (px + pw) + 8
                pg.tree.append(textbox(kit, pg.sid(), "Series label", x, y, fx + fw - x, line, names[n], "head",
                                       colour=ink if colours[n] == marks["highlight"] else second, user_drawn=False))
        else:
            labels.position = XL_LABEL_POSITION.OUTSIDE_END
            if multi:
                # Each series is named once, on its first mark, above the value.
                for n, s in enumerate(chart.series):
                    _point_label(s, 0, True, True, fmt, size, ink, None)


def T_luminance(hexcode):
    h = hexcode.lstrip("#")
    ch = []
    for i in (0, 2, 4):
        v = int(h[i:i + 2], 16) / 255.0
        ch.append(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]


def _point_label(series, index, name, value, fmt, size, colour, position):
    """A data label on one point that prints the series name, its value, or both: native, so it follows the data."""
    label = series.points[index].data_label
    label.font.size = Pt(size)
    paint(label.font.color, colour)
    if position is not None:
        label.position = position
    el = label._get_or_add_dLbl()
    for tag, on in (("showVal", value), ("showSerName", name), ("showCatName", False), ("showLegendKey", False),
                    ("showPercent", False), ("showBubbleSize", False)):
        node = el.find(_c(tag))
        if node is None:
            node = etree.SubElement(el, _c(tag))
        node.set("val", "1" if on else "0")
    order = ["idx", "delete", "layout", "tx", "numFmt", "spPr", "txPr", "dLblPos", "showLegendKey", "showVal", "showCatName",
             "showSerName", "showPercent", "showBubbleSize", "separator", "extLst"]
    if el.find(_c("numFmt")) is None:
        num = etree.SubElement(el, _c("numFmt"))
        num.set("formatCode", fmt)
        num.set("sourceLinked", "0")
    if name and value and el.find(_c("separator")) is None:
        etree.SubElement(el, _c("separator")).text = "\n"
    el[:] = sorted(el, key=lambda child: order.index(etree.QName(child).localname)
                   if etree.QName(child).localname in order else len(order))


def _line_labels(kit, chart, cats, series, colours, fmt):
    """A line is named and valued at its right end and valued at its left: no legend, no value axis."""
    size, ink, second = kit.sc["chart"], kit.ink["ink"], kit.ink["second"]
    last = len(cats) - 1
    for n, s in enumerate(chart.series):
        strong = colours[n] == kit.marks["highlight"]
        colour = ink if strong or len(series) == 1 else second
        _point_label(s, last, False, True, fmt, size, colour, XL_LABEL_POSITION.RIGHT)
        _point_label(s, 0, False, True, fmt, size, colour, XL_LABEL_POSITION.LEFT)
        # Only the two ends are labelled: the series' own switch stays off.
        lbls = s._element.find(_c("dLbls"))
        for tag in ("showVal", "showSerName", "showCatName", "showLegendKey", "showPercent", "showBubbleSize"):
            node = lbls.find(_c(tag))
            if node is not None:
                node.set("val", "0")


def _manual_layout(chart, x, y, w, h):
    """Fix the plot's place inside the chart frame, so labels beside it have room and a known position."""
    area = chart._chartSpace.find(".//" + _c("plotArea"))
    old = area.find(_c("layout"))
    if old is not None:
        area.remove(old)
    area.insert(0, etree.fromstring(
        '<c:layout xmlns:c="%s"><c:manualLayout><c:layoutTarget val="inner"/><c:xMode val="edge"/><c:yMode val="edge"/>'
        '<c:x val="%s"/><c:y val="%s"/><c:w val="%s"/><c:h val="%s"/></c:manualLayout></c:layout>' % (NS["c"], x, y, w, h)))


NUMBER = re.compile(r"[+\-−–]?\(?[\d][\d.,''\u00a0\u202f ]*\)?\s?%?")


def is_number(text):
    return bool(NUMBER.fullmatch(str(text).strip()))


def make_table(kit, pg, x, y, w, avail, columns, rows, highlight_row=None, highlight_col=None, label_col=False):
    """A table as tall as its rows: a line under the header, hairlines between rows, numbers and their headings
    right-aligned, one row or column on the look's raised ground. Returns what the page drew and its height."""
    plan = table_plan(kit, w, avail, columns, rows, label_col)
    frame = pg.table(plan, x, y, highlight_row, highlight_col, label_col)
    return frame, sum(plan["heights"])


def table_plan(kit, w, avail, columns, rows, label_col=False):
    """The widths of a table's columns and the heights of its rows, the same for both outputs."""
    # A cell is its text, or (text, detail): the detail is a second line in the second ink.
    rows = [[c if isinstance(c, (list, tuple)) else (c, "") for c in r] for r in rows]
    main = lambda cell: str(cell[0])  # noqa: E731
    n_rows, n_cols = len(rows) + 1, len(columns)
    for r in rows:
        if len(r) != n_cols:
            raise Refused("a table row has %d cells for %d columns: %r" % (len(r), n_cols, r))
    (size, line), ink, _ = kit.styles["body"]
    gap = kit.G
    numeric = []
    for c in range(n_cols):
        cells = [main(r[c]).strip() for r in rows if main(r[c]).strip() not in ("", "–", "-", "—")]
        numeric.append(bool(cells) and all(is_number(v) for v in cells))
    natural = []
    for c in range(n_cols):
        texts = [str(columns[c])] + [main(r[c]) for r in rows] + [str(r[c][1]) for r in rows if r[c][1]]
        natural.append(max(T.measure(t, size, kit.advance) for t in texts) + gap * 1.5)
    fixed = sum(natural[c] for c in range(n_cols) if numeric[c])
    loose = [c for c in range(n_cols) if not numeric[c]]
    widths = list(natural)
    room = w - fixed
    if loose:
        want = sum(natural[c] for c in loose)
        if want > room or label_col:
            # Text columns share what the number columns leave; in a comparison the options are equal.
            if label_col and len(loose) > 1:
                first = min(natural[loose[0]], room * 0.26)
                widths[loose[0]] = first
                for c in loose[1:]:
                    widths[c] = (room - first) / float(len(loose) - 1)
            else:
                for c in loose:
                    widths[c] = room * natural[c] / want
        else:
            # Room to spare goes to the first text column; a table of numbers only keeps its natural width.
            widths[loose[0]] += room - want
    total = sum(widths)
    row_text = []
    for r in [[(c, "") for c in columns]] + list(rows):
        tallest = 1
        for c in range(n_cols):
            inner = widths[c] - gap * (0 if c == 0 else 1)
            count = len(T.wrap(main(r[c]), size, max(20.0, inner), kit.advance))
            if r[c][1]:
                count += len(T.wrap(str(r[c][1]), size, max(20.0, inner), kit.advance))
            tallest = max(tallest, count)
        row_text.append(tallest * line)
    pitch = float(kit.d["table.row_pitch"])
    least = float(kit.build.get("row.min_pitch", 1.4)) - 1.0
    padding = (avail - sum(row_text)) / float(n_rows)
    if padding < least * line:
        # The rows do not fit at the preset's least pitch and the table was not continued (a second page would
        # hold too few rows): the rows close up, down to the preset's floor, before anything leaves the page.
        least = max(float(kit.build.get("row.floor_pitch", 1.2)) - 1.0, padding / line)
    padding = max(least * line, min((pitch - 1.0) * line, padding))
    heights = [h + padding for h in row_text]
    return {"columns": [str(c) for c in columns], "rows": rows, "numeric": numeric, "widths": widths, "heights": heights,
            "total": total}


def write_table(kit, pg, plan, x, y, highlight_row=None, highlight_col=None, label_col=False):
    """The planned table as a native PowerPoint table with no table style."""
    columns, rows, numeric, widths, heights, total = (plan[k] for k in ("columns", "rows", "numeric", "widths", "heights", "total"))
    main = lambda cell: str(cell[0])  # noqa: E731
    n_rows, n_cols = len(rows) + 1, len(columns)
    holder = pg.ph.pop(IDX_EXHIBIT)
    frame = holder.insert_table(n_rows, n_cols)
    frame.name = "Table"
    table = frame.table
    pr = frame._element.graphic.graphicData.tbl.tblPr
    pr.set("firstRow", "1")
    pr.set("bandRow", "0")
    style_id = pr.find("{%s}tableStyleId" % NS["a"])
    if style_id is None:
        style_id = etree.SubElement(pr, "{%s}tableStyleId" % NS["a"])
    style_id.text = NO_TABLE_STYLE
    (size, line), ink, _ = kit.styles["body"]
    second = kit.ink["second"]
    gap = kit.G
    frame.left, frame.top = Emu(emu(x)), Emu(emu(y))
    frame.width, frame.height = Emu(emu(total)), Emu(emu(sum(heights)))
    for c in range(n_cols):
        table.columns[c].width = Emu(emu(widths[c]))
    for r in range(n_rows):
        table.rows[r].height = Emu(emu(heights[r]))
    a = NS["a"]
    for r in range(n_rows):
        for c in range(n_cols):
            cell = table.cell(r, c)
            text, more = (str(columns[c]), "") if r == 0 else (main(rows[r - 1][c]), str(rows[r - 1][c][1] or ""))
            right = numeric[c]
            cell.margin_top = cell.margin_bottom = 0
            cell.margin_left = 0 if (right or c == 0) else Emu(emu(gap))
            cell.margin_right = Emu(emu(gap)) if (right and c < n_cols - 1) else 0
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            para = cell.text_frame.paragraphs[0]
            para.alignment = PP_ALIGN.RIGHT if right else PP_ALIGN.LEFT
            para.line_spacing = Pt(line)
            run = para.add_run()
            run.text = text
            run.font.size = Pt(size)
            dim = (r == 0 and not label_col) or (label_col and c == 0)
            paint(run.font.color, second if dim else ink)
            if more:
                extra = cell.text_frame.add_paragraph()
                extra.alignment = para.alignment
                extra.line_spacing = Pt(line)
                run = extra.add_run()
                run.text = more
                run.font.size = Pt(size)
                paint(run.font.color, second)
            tc_pr = cell._tc.get_or_add_tcPr()
            strong = r == 0
            border = etree.fromstring(
                '<a:lnB xmlns:a="%s" w="%d" cap="flat" cmpd="sng" algn="ctr"><a:solidFill>%s</a:solidFill>'
                '<a:prstDash val="solid"/></a:lnB>' % (a, emu(0.75), clr(kit.ink["rule"] if strong else kit.ink["hairline"])))
            tc_pr.insert(0, border)
            marked = (highlight_row is not None and r == highlight_row + 1) or (highlight_col is not None and c == highlight_col)
            if marked:
                cell.fill.solid()
                paint(cell.fill.fore_color, kit.ink["raised"])
    return frame


def page_table(prs, kit, deck, page):
    pg = Page(prs, kit, "Table", "table", deck["title"], page.get("section") or "")
    pg.title(page["title"], page.get("_part"))
    columns, rows = page.get("columns") or [], page.get("rows") or []
    if not columns or not rows:
        raise Refused("a table page needs columns and rows")
    below = kit.build.get("takeaway.table") == "below"
    ex, ew, tx, tw = exhibit_frame(kit, bool(page.get("takeaway")) and not below)
    top = kit.body_top
    head = page.get("head") or ""
    head_h = kit.styles["head"][0][1]
    y = top
    if head:
        pg.rule(ex, top, ew)
        pg.put(IDX_HEAD, [head])
        pg.place(IDX_HEAD, ex, top + kit.pad, ew, head_h)
        y = top + kit.pad + head_h + 6
    else:
        pg.drop(IDX_HEAD)
    mark = None
    if page.get("highlight") is not None:
        mark = next((i for i, r in enumerate(rows) if str(r[0]) == str(page["highlight"])), None)
    part = page.get("_part")
    last = not part or part[0] == part[1]
    words = page.get("takeaway") if (last or not below) else ""
    room = kit.text_h([(words, "lead")], kit.CW) + 1.5 * kit.pad if (below and words) else 0
    _, used = make_table(kit, pg, ex, y, ew, kit.body_bottom - y - room, columns, rows, highlight_row=mark)
    if below:
        detail(kit, pg, page.get("points") or [])
        if words:
            ty = y + used + 1.5 * kit.pad
            pg.put(IDX_TAKEAWAY, [(words, 0)])
            pg.place(IDX_TAKEAWAY, ex, ty, kit.CW, kit.body_bottom - ty)
        else:
            pg.drop(IDX_TAKEAWAY)
    else:
        takeaway(kit, pg, page, tx, tw, top)
    return pg


def settle(kit, pg, frame, used):
    """A table that is the page's whole body and shorter than it sits on the middle of the body, as a page of
    rows does, so four actions or five rows of a comparison do not hang from the title over an empty half."""
    room = kit.body_bottom - kit.body_top
    if used < room:
        pg.settle(frame, kit.body_top + (room - used) / 2.0)


def page_comparison(prs, kit, deck, page):
    pg = Page(prs, kit, "Comparison", "comparison", deck["title"], page.get("section") or "")
    pg.title(page["title"], page.get("_part"))
    options, rows = page.get("options") or [], page.get("rows") or []
    if not 2 <= len(options) <= 3:
        raise Refused("a comparison sets two or three options side by side; this one has %d" % len(options))
    if not rows:
        raise Refused("a comparison needs its rows: a label and one value an option")
    for r in rows:
        if len(r.get("values") or []) != len(options):
            raise Refused("the comparison row %r has %d values for %d options" % (r.get("label"), len(r.get("values") or []), len(options)))
    mark = options.index(page["highlight"]) + 1 if page.get("highlight") in options else None
    frame, used = make_table(kit, pg, kit.X0, kit.body_top, kit.CW, kit.body_bottom - kit.body_top, [""] + list(options),
                             [[r.get("label") or ""] + list(r["values"]) for r in rows], highlight_col=mark, label_col=True)
    settle(kit, pg, frame, used)
    return pg


def page_next_steps(prs, kit, deck, page):
    pg = Page(prs, kit, "Next steps", "next-steps", deck["title"], page.get("section") or "")
    pg.title(page["title"], page.get("_part"))
    columns, steps = page.get("columns") or [], page.get("steps") or []
    if len(columns) != 3:
        raise Refused("a next-steps page needs its three column headings in the deck's own language, for the action, "
                      "its owner and its date: \"columns\": [\"Action\", \"Owner\", \"By\"]")
    if not steps:
        raise Refused("a next-steps page needs its steps: action, owner, date")
    rows = []
    for s in steps:
        more = detail(kit, pg, [s.get("detail") or ""])
        rows.append([(s.get("action") or "", more[0] if more else ""), s.get("owner") or "", s.get("date") or ""])
    frame, used = make_table(kit, pg, kit.X0, kit.body_top, kit.CW, kit.body_bottom - kit.body_top, columns, rows)
    settle(kit, pg, frame, used)
    return pg


def columns_of(kit, n, wide=1.0):
    gap = 2 * kit.G
    w = (kit.CW - (n - 1) * gap) / float(n)
    return [(kit.X0 + i * (w + gap), w) for i in range(n)]


def under_block(kit, pg, page, block):
    """Where a row of columns starts so that it, and the takeaway under it when the page has one, sit a little
    above the middle of the body. Fills the takeaway."""
    words = page.get("takeaway") or ""
    part = page.get("_part")
    if part and part[0] != part[1]:
        words = ""
    width = kit.part(0, 9)[1]
    gap = 2.5 * kit.pad
    extra = gap + kit.pad + kit.text_h([(words, "lead")], width) if words else 0.0
    top = kit.body_top + max(0.0, (kit.body_bottom - kit.body_top - block - extra) * 0.5)
    if words:
        y = top + block + gap
        pg.rule(kit.X0, y, kit.CW)
        pg.put(IDX_TAKEAWAY, [words])
        pg.place(IDX_TAKEAWAY, kit.X0, y + kit.pad, width, kit.body_bottom - y - kit.pad)
    else:
        pg.drop(IDX_TAKEAWAY)
    return top


def page_figures(prs, kit, deck, page):
    pg = Page(prs, kit, "Figures", "figures", deck["title"], page.get("section") or "")
    pg.title(page["title"], page.get("_part"))
    figures = page.get("figures") or []
    if not 2 <= len(figures) <= 4:
        raise Refused("a key-figures page holds two to four figures; this one has %d" % len(figures))
    cols = columns_of(kit, len(figures))
    w = cols[0][1]
    body = kit.body_line
    fig = kit.sc["figure"][1]
    name_h = max(len(kit.lines(f.get("label") or "", "body-second", w)) for f in figures) * body
    texts = []
    for f in figures:
        facts = ", ".join(str(f[k]) for k in ("unit", "period") if f.get(k) and str(f[k]).strip() != "%")
        note = detail(kit, pg, [f.get("note") or ""])
        texts.append(([(facts, 0)] if facts else []) + [(n, 1) for n in note])
    text_h = max([kit.text_h([(t, "body" if lv == 0 else "body-second") for t, lv in paras], w) for paras in texts] + [0])
    block = kit.pad + name_h + 4 + fig + 6 + text_h
    top = under_block(kit, pg, page, block)
    for i in range(4):
        if i >= len(figures):
            for group in (GROUP_A, GROUP_B, GROUP_C):
                pg.drop(group + i)
            continue
        x = cols[i][0]
        f = figures[i]
        pg.rule(x, top, w)
        pg.put(GROUP_A + i, [f.get("label") or ""])
        pg.place(GROUP_A + i, x, top + kit.pad, w, name_h)
        value = str(f.get("value", "")).strip()
        pg.put(GROUP_B + i, [value + "%" if str(f.get("unit") or "").strip() == "%" and "%" not in value else value])
        pg.place(GROUP_B + i, x, top + kit.pad + name_h + 4, w, fig)
        pg.put(GROUP_C + i, texts[i])
        pg.place(GROUP_C + i, x, top + kit.pad + name_h + 4 + fig + 6, w, max(text_h, body))
    return pg


def page_process(prs, kit, deck, page):
    pg = Page(prs, kit, "Process", "process", deck["title"], page.get("section") or "")
    pg.title(page["title"], page.get("_part"))
    steps = page.get("steps") or []
    if not 2 <= len(steps) <= GROUP:
        raise Refused("a process page holds three to six steps; this one has %d" % len(steps))
    cols = columns_of(kit, len(steps))
    w = cols[0][1]
    lead = kit.sc["figure"][1]
    filled = []
    for s in steps:
        more = detail(kit, pg, [s.get("detail") or ""])
        filled.append([(s.get("name") or "", 0)] + [(m, 1) for m in more])
    text_h = max(kit.text_h([(t, "lead" if lv == 0 else "body-second") for t, lv in paras], w) for paras in filled)
    block = kit.pad + lead + 6 + text_h
    first = int(page.get("_first", 0))
    top = under_block(kit, pg, page, block)
    for i in range(GROUP):
        if i >= len(steps):
            pg.drop(GROUP_A + i)
            pg.drop(GROUP_C + i)
            continue
        x = cols[i][0]
        pg.rule(x, top, w)
        pg.put(GROUP_A + i, ["%02d" % (first + i + 1)])
        pg.place(GROUP_A + i, x, top + kit.pad, w, lead)
        pg.put(GROUP_C + i, filled[i])
        pg.place(GROUP_C + i, x, top + kit.pad + lead + 6, w, text_h)
    return pg


def page_timeline(prs, kit, deck, page):
    pg = Page(prs, kit, "Timeline", "timeline", deck["title"], page.get("section") or "")
    pg.title(page["title"], page.get("_part"))
    steps = page.get("steps") or []
    if not 2 <= len(steps) <= GROUP:
        raise Refused("a timeline holds three to six dated steps; this one has %d" % len(steps))
    n = len(steps)
    step = kit.CW / float(n)
    filled = []
    for s in steps:
        more = detail(kit, pg, [s.get("detail") or ""])
        filled.append([(s.get("when") or "", 0), (s.get("what") or "", 1)] + [(m, 2) for m in more])
    w = min(2 * step - 2 * kit.G, kit.CW * 0.42)
    styles = {0: "body-second", 1: "lead", 2: "body-second"}
    widths = [min(w, kit.X1 - (kit.X0 + i * step)) for i in range(n)]
    heights = [kit.text_h([(t, styles[lv]) for t, lv in paras if t], widths[i]) for i, paras in enumerate(filled)]
    up = max([h for i, h in enumerate(heights) if i % 2 == 0] + [0])
    down = max([h for i, h in enumerate(heights) if i % 2 == 1] + [0])
    gap = 16
    room = kit.body_bottom - kit.body_top
    axis = kit.body_top + max(up + gap, min(room - down - gap, room / 2.0))
    pg.rule(kit.X0, axis, kit.CW, strong=True, name="Axis")
    size = 8
    for i in range(GROUP):
        if i >= n:
            pg.drop(GROUP_C + i)
            continue
        x = kit.X0 + i * step
        pg.dot(x, axis - size / 2.0, size, kit.ink["ink"])
        width = widths[i]
        pg.put(GROUP_C + i, filled[i])
        if i % 2 == 0:
            pg.place(GROUP_C + i, x, axis - gap - up, width, up)
        else:
            pg.place(GROUP_C + i, x, axis + gap, width, max(down, kit.body_line))
    return pg


def page_text(prs, kit, deck, page):
    pg = Page(prs, kit, "Text", "text", deck["title"], page.get("section") or "")
    pg.title(page["title"], page.get("_part"))
    points = page.get("points") or []
    if len(points) > GROUP:
        raise Refused("a text page holds at most six points; this one has %d" % len(points))
    sx, sw = kit.part(0, 5)
    px, pw = kit.part(6, 6)
    top = kit.body_top
    if page.get("statement"):
        pg.rule(sx, top, sw)
        pg.put(IDX_LEAD, [page["statement"]])
    else:
        pg.drop(IDX_LEAD)
        px, pw = kit.part(0, 9)
    filled, heights = [], []
    for p in points:
        if isinstance(p, dict):
            more = detail(kit, pg, [p.get("detail") or ""])
            paras = [(p.get("point") or "", 0)] + [(m, 1) for m in more]
        else:
            paras = [(str(p), 0)]
        filled.append(paras)
        heights.append(kit.text_h([(t, kit.point_style if lv == 0 else "body-second") for t, lv in paras], pw))
    if points:
        tops, rows = spread(kit, heights, top, rows_bottom(kit, page))
    for i in range(GROUP):
        if i >= len(points):
            pg.drop(GROUP_B + i)
            continue
        pg.rule(px, tops[i], pw)
        pg.put(GROUP_B + i, filled[i])
        pg.place(GROUP_B + i, px, tops[i] + kit.pad, pw, rows[i] - kit.pad - 1)
    return pg


def page_closing(prs, kit, deck, page):
    pg = Page(prs, kit, "Closing", "closing", "", "")
    pg.title(page["title"])
    contact = page.get("contact") or []
    contact = [contact] if isinstance(contact, str) else list(contact)
    pg.put(IDX_LEAD, ["\n".join(str(c) for c in contact)] if contact else [])
    pg.put(IDX_SMALL, [page.get("small") or ""])
    return pg


def page_matrix(prs, kit, deck, page):
    """A 2x2 matrix: two named axes with both ends named, four named quadrants, the items placed on it, and one
    quadrant on the look's raised ground with its name and items in full ink: the page's message."""
    pg = Page(prs, kit, "Matrix", "matrix", deck["title"], page.get("section") or "")
    pg.title(page["title"], page.get("_part"))
    xa, ya = page.get("x"), page.get("y")
    for axis, letter in ((xa, "x"), (ya, "y")):
        if not isinstance(axis, dict) or set(axis) - {"name", "low", "high"} \
                or not all(str(axis.get(key) or "").strip() for key in ("name", "low", "high")):
            raise Refused('a matrix names both axes and both ends of each: "%s": {"name": what it measures, '
                          '"low": the word at its low end, "high": the word at its high end}' % letter)
    quads = page.get("quadrants")
    if not isinstance(quads, dict) or set(quads) != set(QUADRANTS) or not all(str(v or "").strip() for v in quads.values()):
        raise Refused('a matrix names its four quadrants: "quadrants": {"top_left": ..., "top_right": ..., '
                      '"bottom_left": ..., "bottom_right": ...}')
    items = page.get("items") or []
    spots = []
    for it in items:
        try:
            x, y = float(it["x"]), float(it["y"])
            name = str(it["name"]).strip()
        except (KeyError, TypeError, ValueError):
            x = y = -1.0
            name = ""
        if not name or not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0) or set(it) - {"name", "x", "y"}:
            raise Refused('a matrix places each item by its name and its place along both axes, 0 at the low end and '
                          '1 at the high end: {"name": ..., "x": 0.2, "y": 0.8}; got %r' % (it,))
        spots.append((name, x, y))
    if not spots:
        raise Refused('a matrix places its items: "items": [{"name": ..., "x": 0.2, "y": 0.8}]')
    mark = page.get("highlight")
    lit = None
    if mark is not None:
        lit = mark if mark in QUADRANTS else next((q for q in QUADRANTS if str(quads[q]).strip() == str(mark).strip()), None)
        if lit is None:
            raise Refused("the matrix highlights %r, which is none of its quadrants (%s)"
                          % (mark, ", ".join(str(quads[q]) for q in QUADRANTS)))
    top = kit.body_top
    line = kit.styles["head"][0][1]
    # The vertical axis's words stand in a gutter left of the matrix, the horizontal axis's in a line under it.
    gutter = min(kit.part(0, 2)[1], max(kit.width(str(ya[key]), "head") for key in ("name", "low", "high")) + 2) + kit.G
    my = top + kit.pad
    words = page.get("takeaway") or ""
    points = detail(kit, pg, page.get("points") or [])
    under = [(words, 0)] + [(p, 1) for p in points]
    room = kit.text_h([(t, "lead" if lv == 0 else "body-second") for t, lv in under], kit.CW) + 1.5 * kit.pad
    # The preset's pattern for evidence pages puts the takeaway under the exhibit or beside it. A matrix laid
    # out flat stops reading as one, so where the full width would make it flatter than the preset's limit the
    # takeaway moves beside it.
    below = bool(words) and kit.build.get("takeaway.chart") == "below"
    if below and (kit.CW - gutter) / (kit.body_bottom - room - my - line - 6) > float(kit.build.get("matrix.max_aspect", 2.2)):
        below = False
    if words and not below:
        cols = int(kit.build.get("matrix.takeaway_columns", kit.build.get("chart.takeaway_columns", 4)))
        ex, ew = kit.part(0, 12 - cols)
        tx, tw = kit.part(12 - cols, cols)
        tx, tw = tx + kit.G, tw - kit.G
        bottom = kit.body_bottom
    else:
        ex, ew, tx, tw = kit.X0, kit.CW, None, None
        bottom = kit.body_bottom - (room if words else 0.0)
    pg.rule(ex, top, ew)
    mx, mw, mh = ex + gutter, ew - gutter, bottom - my - line - 6
    qw, qh = mw / 2.0, mh / 2.0
    corner = {"top_left": (0, 0), "top_right": (1, 0), "bottom_left": (0, 1), "bottom_right": (1, 1)}
    if lit:
        col, row = corner[lit]
        pg.panel(mx + col * qw, my + row * qh, qw, qh, kit.ink["raised"], name="Quadrant highlight")
    pg.rule(mx, my, mw, name="Matrix line")
    pg.vrule(mx + mw, my, mh, name="Matrix line")
    pg.rule(mx, my + qh, mw, name="Matrix line")
    pg.vrule(mx + qw, my, mh, name="Matrix line")
    pg.vrule(mx, my, mh, strong=True, name="Matrix axis")
    pg.rule(mx, my + mh, mw, strong=True, name="Matrix axis")
    for i, quad in enumerate(QUADRANTS):
        col, row = corner[quad]
        pg.put(GROUP_A + i, [(str(quads[quad]), 1 if quad == lit else 0)])
        pg.place(GROUP_A + i, mx + col * qw + kit.pad, my + row * qh + kit.pad, qw - 2 * kit.pad, kit.body_line)
    third = mw / 3.0
    for n, (text, x, y, w, h) in enumerate((
            (xa["name"], mx + third, my + mh + 6, third, line), (xa["low"], mx, my + mh + 6, third, line),
            (xa["high"], mx + 2 * third, my + mh + 6, third, line),
            (ya["name"], ex, my + line, gutter - kit.G, mh - 2 * line), (ya["low"], ex, my + mh - line, gutter - kit.G, line),
            (ya["high"], ex, my, gutter - kit.G, line))):
        pg.put(IDX_AXIS + n, [str(text)])
        pg.place(IDX_AXIS + n, x, y, w, h)
    # An item is a dot with its name beside it, kept clear of the quadrant's name and of the lines.
    size, gap = 8.0, 5.0
    band = kit.pad + kit.body_line + size
    inset = kit.pad + size / 2.0
    set_names = []
    for name, x, y in spots:
        col, row = (1 if x >= 0.5 else 0), (0 if y >= 0.5 else 1)
        fx, fy = (x - 0.5 * col) / 0.5, (y - 0.5 * (1 - row)) / 0.5
        left, upper = mx + col * qw, my + row * qh
        wide = kit.width(name, "head") + 2
        if wide + gap + size + 2 * inset > qw:
            raise Refused("the matrix item %r is too long for its quadrant; shorten the name" % name)
        cx = left + inset + fx * (qw - 2 * inset)
        cy = upper + qh - inset - fy * (qh - inset - band)
        strong = (col, row) == corner.get(lit)
        pg.dot(cx - size / 2.0, cy - size / 2.0, size, kit.ink["ink"] if strong else kit.marks["neutral"], name="Item mark")
        # The dot stands where the data puts it. Its name goes to its right, else to its left, else under or over
        # it: the first of these that stays inside the quadrant and clear of the names already set.
        mid = min(max(cx - wide / 2.0, left + inset), left + qw - inset - wide)
        spots_for = [(cx + size / 2.0 + gap, cy - line / 2.0, "l"), (cx - size / 2.0 - gap - wide, cy - line / 2.0, "r"),
                     (mid, cy + size / 2.0 + 2, "ctr"), (mid, cy - size / 2.0 - 2 - line, "ctr")]
        inside = [(lx, ly, al) for lx, ly, al in spots_for
                  if lx >= left + inset - 0.5 and lx + wide <= left + qw - inset + 0.5 and ly >= upper + band - size - line
                  and ly + line <= upper + qh - 1]
        clear = [(lx, ly, al) for lx, ly, al in inside
                 if not any(lx < ox + ow and ox < lx + wide and ly < oy + line and oy < ly + line for ox, oy, ow in set_names)]
        lx, ly, align = (clear or inside or spots_for[2:3])[0]
        set_names.append((lx, ly, wide))
        pg.label("Item label", lx, ly, wide, line, name, "head", align=align,
                 colour=kit.ink["ink"] if strong else kit.ink["second"])
    if not words:
        pg.drop(IDX_TAKEAWAY)
    elif below:
        ty = bottom + 1.5 * kit.pad
        pg.put(IDX_TAKEAWAY, under)
        pg.place(IDX_TAKEAWAY, ex, ty, kit.CW, kit.body_bottom - ty)
    else:
        pg.rule(tx, top, tw)
        pg.put(IDX_TAKEAWAY, under)
        pg.place(IDX_TAKEAWAY, tx, top + kit.pad, tw, kit.body_bottom - top - kit.pad)
    return pg


def picture_of(deck, file):
    """The path and pixel size of a figure's picture, read beside the deck's data."""
    path = file if os.path.isabs(file) else os.path.join(deck.get("_folder") or os.getcwd(), file)
    if not os.path.isfile(path):
        raise Refused("the figure's picture %s is not there; it is read beside the deck's data, in %s"
                      % (file, os.path.dirname(os.path.abspath(path))))
    from PIL import Image
    try:
        with Image.open(path) as im:
            kind, (wide, high) = im.format, im.size
    except Exception:
        kind, wide, high = None, 0, 0
    if kind not in PICTURES or not wide or not high:
        raise Refused("the figure's picture %s is not a PNG, JPEG or GIF file; save the page or screen as a PNG" % file)
    return path, wide, high


def page_figure(prs, kit, deck, page):
    """A figure: one picture, or one rendered page of a real file, shown whole at its own proportions, with a
    caption above it, its source under it and the takeaway beside or under it."""
    pg = Page(prs, kit, "Figure", "figure", deck["title"], page.get("section") or "")
    pg.title(page["title"], page.get("_part"))
    file = str(page.get("image") or "").strip()
    if not file:
        raise Refused('a figure page shows one picture: "image": a PNG or JPEG file beside the deck\'s data')
    path, wide, high = picture_of(deck, file)
    ratio = wide / float(high)
    caption = str(page.get("caption") or "").strip()
    words = page.get("takeaway") or ""
    points = detail(kit, pg, page.get("points") or [])
    top = kit.body_top
    line = kit.styles["head"][0][1]

    def fit(w, h):
        return (w, w / ratio) if w / ratio <= h else (h * ratio, h)

    def laid(mode, lines):
        """The picture's size and the takeaway's place when it stands beside ('side'), under ('below') or is not there."""
        room = kit.body_bottom - top - kit.pad - ((lines * line + 8) if caption else 0)
        if mode == "below":
            under = [(words, 0)] + [(p, 1) for p in points]
            need = kit.text_h([(t, "lead" if lv == 0 else "body-second") for t, lv in under], kit.CW) + 1.5 * kit.pad
            return fit(kit.CW, room - need) + (under,)
        if mode == "side":
            cols = int(kit.build.get("chart.takeaway_columns", 4))
            return fit(kit.part(0, 12 - cols)[1], room) + ([],)
        return fit(kit.CW, room) + ([],)

    mode = "none"
    if words:
        # The preset's pattern for evidence pages, unless the other way shows the picture much larger.
        first = "below" if kit.build.get("takeaway.chart") == "below" else "side"
        other = "side" if first == "below" else "below"
        a, b = laid(first, 1), laid(other, 1)
        mode = other if b[0] * b[1] > 1.4 * a[0] * a[1] else first
    pw, ph, under = laid(mode, 1)
    lines = len(kit.lines(caption, "head", pw)) if caption else 0
    if lines > 1:
        pw, ph, under = laid(mode, lines)
    pg.rule(kit.X0, top, pw)
    pg.put(IDX_HEAD, [caption])
    pg.place(IDX_HEAD, kit.X0, top + kit.pad, pw, max(1, lines) * line)
    py = top + kit.pad + ((lines * line + 8) if caption else 0)
    alt = str(page.get("alt") or caption or page["title"])
    pg.picture(path, kit.X0, py, pw, ph, alt[:kit.d.get("alt.max_chars", 250)], (wide, high))
    if mode == "below":
        ty = py + ph + 1.5 * kit.pad
        pg.put(IDX_TAKEAWAY, under)
        pg.place(IDX_TAKEAWAY, kit.X0, ty, kit.CW, kit.body_bottom - ty)
    elif mode == "side":
        tx = kit.X0 + pw + 2 * kit.G
        pg.rule(tx, top, kit.X1 - tx)
        pg.put(IDX_TAKEAWAY, [(words, 0)] + [(p, 1) for p in points])
        pg.place(IDX_TAKEAWAY, tx, top + kit.pad, kit.X1 - tx, kit.body_bottom - top - kit.pad)
    else:
        pg.drop(IDX_TAKEAWAY)
    return pg


def page_quote(prs, kit, deck, page):
    """A quote: one sentence somebody said, set large on the middle of the body, with who said it and their
    role under it. The builder adds nothing: no ornament, no quotation marks the data does not carry."""
    pg = Page(prs, kit, "Quote", "quote", deck["title"], page.get("section") or "")
    pg.title(page["title"], page.get("_part"))
    words, name, role = (str(page.get(key) or "").strip() for key in ("quote", "name", "role"))
    if not words:
        raise Refused('a quote page holds one sentence somebody said: "quote"')
    if not name or not role:
        raise Refused('a quote names who said it and their role: "name" and "role"')
    x, w = kit.part(0, 10)
    lead, body = kit.sc["lead"][1], kit.body_line
    said = kit.text_h([(words, "headline")], w)
    gap = 2 * kit.pad
    bottom = rows_bottom(kit, page)
    top = kit.body_top + max(0.0, (bottom - kit.body_top - (said + gap + lead + body)) / 2.0)
    pg.put(IDX_LEAD, [words])
    pg.place(IDX_LEAD, x, top, w, said)
    pg.put(IDX_NAME, [name])
    pg.place(IDX_NAME, x, top + said + gap, w, lead)
    pg.put(IDX_ROLE, [role])
    pg.place(IDX_ROLE, x, top + said + gap + lead, w, body)
    return pg


def page_appendix(prs, kit, deck, page):
    """The appendix divider: its name, and the backup pages behind it listed by their numbers."""
    pg = Page(prs, kit, "Appendix", "appendix", deck["title"], "")
    pg.title(page["title"])
    listed = page.get("_backup") or []
    nx, nw = kit.part(5, 1)
    tx, tw = kit.part(6, 6)
    heights = [kit.text_h([(title, "body")], tw) for _, title in listed]
    room = kit.body_bottom - kit.body_top
    rows = [h + 2 * kit.pad for h in heights]
    show = 0 < len(listed) <= LISTED and sum(rows) <= room
    tops = [kit.body_bottom - sum(rows[i:]) + kit.pad for i in range(len(rows))]
    for i in range(LISTED):
        if not show or i >= len(listed):
            pg.drop(GROUP_A + i)
            pg.drop(GROUP_B + i)
            continue
        number, title = listed[i]
        pg.rule(nx, tops[i], kit.X1 - nx)
        pg.put(GROUP_A + i, [number])
        pg.place(GROUP_A + i, nx, tops[i] + kit.pad, nw, kit.body_line)
        pg.put(GROUP_B + i, [title])
        pg.place(GROUP_B + i, tx, tops[i] + kit.pad, tw, heights[i])
    return pg


BUILDERS = {"cover": page_cover, "summary": page_summary, "agenda": page_agenda, "section": page_section,
            "chart": page_chart, "figures": page_figures, "comparison": page_comparison, "table": page_table,
            "process": page_process, "timeline": page_timeline, "text": page_text, "matrix": page_matrix,
            "figure": page_figure, "quote": page_quote, "next-steps": page_next_steps, "closing": page_closing,
            "appendix": page_appendix}
# The list a page may be split over when the preset keeps fewer rows a page, and the preset's limit for it.
SPLIT = {"table": ("rows", "rows.max"), "comparison": ("rows", "rows.max"), "next-steps": ("steps", "rows.max"),
         "summary": ("blocks", "blocks.max"), "text": ("points", "bullets.max"), "process": ("steps", "columns.max"),
         "timeline": ("steps", "columns.max"), "figures": ("figures", "figures.max")}


def rows_that_fit(kit, page):
    """The rows a table page holds at the preset's type size: what the body leaves after the table's head and a
    takeaway set under it, in rows of the preset's least pitch."""
    line = kit.body_line
    room = kit.body_bottom - kit.body_top
    lines = 1
    if page["type"] == "table":
        if page.get("head"):
            room -= kit.pad + kit.styles["head"][0][1] + 6
        if page.get("takeaway") and kit.build.get("takeaway.table") == "below":
            room -= kit.text_h([(page["takeaway"], "lead")], kit.CW) + 1.5 * kit.pad
    elif page["type"] == "next-steps":
        if kit.build.get("detail") != "notes" and any(s.get("detail") for s in page.get("steps") or []):
            lines = 2
    pitch = float(kit.build.get("row.min_pitch", 1.4))
    return max(1, int((room - line * pitch) // (line * (lines + pitch - 1.0))))


def expand(pages, kit):
    """A list longer than a page holds continues on the next, in equal parts, the title counting them (1/2),
    (2/2). A table continues only when its rows do not fit the body at the preset's type size, and never so
    that a page is left with fewer rows than the preset's least."""
    out = []
    for page in pages:
        key, knob = SPLIT.get(page["type"], (None, None))
        items = page.get(key) if key else None
        limit = (kit.build.get(knob) or kit.d.get(knob) or 0) if knob else 0
        if knob == "rows.max" and limit:
            limit = min(limit, rows_that_fit(kit, page))
        if not items or not limit or len(items) <= limit:
            out.append(page)
            continue
        parts = int(math.ceil(len(items) / float(limit)))
        if knob == "rows.max":
            least = int(kit.build.get("rows.min_page", 4))
            while parts > 1 and len(items) // parts < least:
                parts -= 1
        per = int(math.ceil(len(items) / float(parts)))
        for i in range(parts):
            piece = dict(page)
            piece[key] = items[i * per:(i + 1) * per]
            piece["_part"] = (i + 1, parts)
            piece["_first"] = i * per
            out.append(piece)
    return out


# A title that ends on one of these keeps its stop: the stop belongs to the word.
SHORT_FORMS = {"ltd", "inc", "co", "corp", "plc", "etc", "approx", "no", "nr", "st", "jr", "sr", "vs", "ca", "cf", "est",
               "dept", "min", "max", "avg", "bros", "mr", "mrs", "ms", "dr", "prof", "ab", "oy", "as", "bv", "nv", "sa"}


def shown_title(text, kind, sentence_words):
    """A page's title as it is set. One closing full stop comes off: a title is a headline, and a deck where
    some titles end on a stop and others do not reads as two decks. It stays where it belongs to the words: on
    a cover or closing statement that is a full sentence, after a short form ("Ltd.", "a.m.") and in an
    ellipsis. A question mark or an exclamation mark is never touched."""
    text = str(text).rstrip()
    if not text.endswith(".") or text.endswith(".."):
        return text
    stem = text[:-1].rstrip()
    last = (stem.split() or [""])[-1].strip("()[]\"'“”‘'")
    if "." in last or last.lower() in SHORT_FORMS:
        return text
    if kind in ("cover", "closing") and len(stem.split()) >= sentence_words:
        return text
    return stem


def validate(deck):
    if not isinstance(deck.get("pages"), list) or not deck["pages"]:
        raise Refused("the deck has no pages")
    extra = set(deck) - {"title", "organisation", "language", "density", "editable", "pages"}
    if extra:
        raise Refused("unknown key(s) at the top: %s (known: title, organisation, language, density, editable, pages)"
                      % ", ".join(sorted(extra)))
    if deck.get("editable") is not None and not isinstance(deck["editable"], bool):
        raise Refused('"editable" is true or false: true writes the PowerPoint file beside the PDF')
    if not str(deck.get("title") or "").strip():
        raise Refused("the deck needs a title: it names the file and runs along every page")
    for n, page in enumerate(deck["pages"], 1):
        kind = page.get("type")
        if kind not in TYPES:
            raise Refused("page %d has the type %r; the page types are %s" % (n, kind, ", ".join(TYPES)))
        extra = set(page) - KEYS[kind] - EVERY
        if extra:
            raise Refused("page %d (%s) has unknown key(s): %s (known: %s)"
                          % (n, kind, ", ".join(sorted(extra)), ", ".join(sorted(KEYS[kind] | EVERY))))
        for key, value in page.items():
            shape = "a list" if isinstance(value, list) else "a group of keys" if isinstance(value, dict) else "text"
            if value is not None and key in TEXT and isinstance(value, (list, dict)):
                raise Refused('page %d (%s): "%s" is one line of text and was given %s%s'
                              % (n, kind, key, shape, "; " + HINT[key] if key in HINT else ""))
            if value is not None and key in LISTS and not isinstance(value, list):
                raise Refused('page %d (%s): "%s" is a list and was given %s%s'
                              % (n, kind, key, shape, "; " + HINT[key] if key in HINT else ""))
        if not str(page.get("title") or "").strip():
            raise Refused("page %d (%s) has no title" % (n, kind))
    # The appendix is the deck's last part: one divider, and behind it only backup pages.
    kinds = [page["type"] for page in deck["pages"]]
    if kinds.count("appendix") > 1:
        raise Refused("the deck has %d appendix pages; one divider opens the appendix" % kinds.count("appendix"))
    if "appendix" in kinds:
        at = kinds.index("appendix")
        if at == len(kinds) - 1:
            raise Refused("the appendix has no backup page behind it; put the backup pages after the appendix page, or drop it")
        for n, kind in enumerate(kinds[at + 1:], at + 2):
            if kind not in BACKUP:
                raise Refused("page %d (%s) stands behind the appendix page; everything after it is a backup page (%s), "
                              "so the appendix comes last, after the closing page" % (n, kind, ", ".join(BACKUP)))


def prepare(deck, density_name=None, look_path=None, folder=None):
    """Everything both outputs share before a page is drawn: the data checked, the look and the preset read,
    lists split over pages, the appendix numbered. Returns (kit, deck, pages, preset name)."""
    validate(deck)
    look = load_look(look_path or os.path.join(PACK, "look.json"))
    density = load_density()
    name = (density_name or deck.get("density") or look.get("density") or density.get("default") or "standard").lower()
    if name not in density["presets"]:
        raise Refused("no density preset %r; the presets are %s" % (name, ", ".join(density["presets"])))
    language = deck.get("language") or "en-GB"
    kit = Kit(look, density, name, language)
    organisation = deck.get("organisation") or ""
    for what, text, room in [("the deck's title", deck["title"], kit.page_span(4, 4)[1]),
                             ("the organisation's name", organisation, kit.page_span(0, 4)[1])] + \
            [("page %d's section name" % n, str(p.get("section") or ""), (kit.page_span(0, kit.c0)[1] - kit.G) if kit.c0 else kit.page_span(8, 3)[1])
             for n, p in enumerate(deck["pages"], 1)]:
        wide = kit.width(text, "small")
        if wide > room and not (what.endswith("section name") and kit.c0):
            raise Refused("%s, %r, runs along the top of every page in one line of small print and is too long for it: "
                          "keep it to about %d characters%s" % (what, text, int(len(text) * room / wide),
                                                               "; the cover's title and subtitle say the rest" if what == "the deck's title" else ""))
    deck = dict(deck)
    deck["_folder"] = folder or os.getcwd()
    deck["organisation"], deck["language"] = organisation, language
    pages = copy.deepcopy(deck["pages"])
    for page in pages:
        page["title"] = shown_title(page["title"], page["type"], int(kit.d.get("title.min_words", 6)))
    deck["_sections"] = [p["title"] for p in pages if p["type"] == "section"]
    pages = expand(pages, kit)
    # Behind the appendix divider every page is a backup page: numbered in the appendix's own count, under the
    # letter its name starts with (or the data's "mark"), and carrying the appendix's name in its running line.
    appendix, count = None, 0
    for page in pages:
        if page["type"] == "appendix":
            appendix = page
            appendix["_mark"] = str(page.get("mark") or page["title"].strip()[:1]).strip().upper()
            if not re.fullmatch(r"[^\W\d_]{1,3}", appendix["_mark"]):
                raise Refused('the appendix numbers its pages under a letter, the first of its name unless you give one: "mark": "A"')
            appendix["_backup"] = []
        elif appendix is not None:
            count += 1
            page["_number"] = "%s%d" % (appendix["_mark"], count)
            page["section"] = appendix["title"]
            part = page.get("_part")
            if not part or part[0] == 1:
                appendix["_backup"].append((page["_number"], page["title"]))
    return kit, deck, pages, name


def draw(book, kit, deck, pages):
    """Lay every page out on `book`: a presentation with its master, or the HTML the PDF is printed from."""
    for page in pages:
        kit.number = page.get("_number")
        pg = BUILDERS[page["type"]](book, kit, deck, page)
        pg.finish(page)
    kit.number = None


def editable(deck, look_path=None):
    """Does the deck's own data, or the look in use, ask for the PowerPoint file beside the PDF?"""
    if isinstance(deck.get("editable"), bool):
        return deck["editable"]
    look = load_look(look_path or os.path.join(PACK, "look.json"))
    return bool((look.get("output") or {}).get("editable"))


def build(deck, out, density_name=None, look_path=None, folder=None):
    """Write the deck to `out` as a PowerPoint file and return the preset's name and the number of pages.
    `folder` is where a figure's picture is read from: the folder of the deck's data."""
    if NO_PPTX is not None:
        raise ImportError("no python-pptx in this Python (%s)" % NO_PPTX)
    kit, deck, pages, name = prepare(deck, density_name, look_path, folder)
    organisation, language = deck["organisation"], deck["language"]
    prs = bare(kit, organisation)
    draw(prs, kit, deck, pages)
    props = prs.core_properties
    props.title = deck["title"]
    props.author = organisation
    props.last_modified_by = organisation
    props.language = language
    props.identifier = "%s density=%s" % (MARK, name)
    props.subject = ""
    props.keywords = ""
    props.comments = ""
    props.category = ""
    props.revision = 1
    prs.save(out)
    return name, len(pages)


def soffice():
    found = shutil.which("soffice") or shutil.which("libreoffice")
    if found:
        return found
    for path in ("/Applications/LibreOffice.app/Contents/MacOS/soffice",
                 r"C:\Program Files\LibreOffice\program\soffice.exe"):
        if os.path.isfile(path):
            return path
    return None


def write_pdf(pptx, folder=None):
    """The PowerPoint file drawn as a PDF by LibreOffice, where it is installed: what the check measures an
    editable file's pages on. Written beside the file, or into `folder`. Returns the path, or None. This is
    not the PDF that is handed back; deck_html.py writes that one."""
    tool = soffice()
    if not tool:
        return None
    folder = folder or os.path.dirname(os.path.abspath(pptx))
    with tempfile.TemporaryDirectory(prefix="deck-office-") as profile:
        run = subprocess.run([tool, "-env:UserInstallation=file://%s" % profile, "--headless", "--convert-to", "pdf",
                              "--outdir", folder, os.path.abspath(pptx)], capture_output=True, text=True, timeout=300)
    pdf = os.path.join(folder, os.path.splitext(os.path.basename(pptx))[0] + ".pdf")
    if run.returncode != 0 or not os.path.isfile(pdf):
        return None
    return pdf


def own_company(deck, data_file):
    """The organisation a deck leaves out is the company of the folder's company.json (skills/_shared/company.py:
    its trading name, else its name). One the deck does give stands as written: a deck may be another body's."""
    if deck.get("organisation"):
        return None
    shared = os.path.join(os.path.dirname(PACK), "_shared")
    if shared not in sys.path:
        sys.path.insert(0, shared)
    try:
        import company
    except ImportError:
        return None
    path = company.find(data_file)
    if not path:
        return None
    facts = company.load(path)
    name = facts.get("trading_name") or facts.get("name")
    if not name:
        return None
    deck["organisation"] = name
    print("company file %s: filled organisation" % path, file=sys.stderr)
    return name


def need_notes(deck):
    """The editable file is presented from: every slide carries what its speaker says, in the notes under it."""
    bare = ["%d (%s)" % (n, page.get("type")) for n, page in enumerate(deck.get("pages") or [], 1)
            if isinstance(page, dict) and not str(page.get("notes") or "").strip()]
    if bare:
        raise Refused("the editable file needs speaker notes on every page, and page%s %s ha%s none: give each a \"notes\" key, "
                      "two or three sentences the presenter says aloud on that page, in the deck's language, saying "
                      "nothing the page and the person's notes do not carry"
                      % ("s" if len(bare) > 1 else "", ", ".join(bare), "ve" if len(bare) > 1 else "s"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("deck", help="the deck's data, a JSON file")
    ap.add_argument("out", help="the file to write: <name>.pdf, the deck that is handed back; or <name>.pptx, "
                                "the editable file, with the PDF beside it")
    ap.add_argument("--density", help="sparse, standard or full; default the deck's own, then the look's")
    ap.add_argument("--look", help="a look file to use instead of the pack's look.json")
    ap.add_argument("--editable", action="store_true", help="also write the PowerPoint file beside the PDF")
    ap.add_argument("--no-pdf", action="store_true", help="with an out path ending in .pptx: write the PowerPoint file alone")
    ap.add_argument("--html", action="store_true", help="keep the page the PDF is printed from, as <name>.html")
    a = ap.parse_args(argv)
    with open(a.deck, encoding="utf-8") as handle:
        deck = json.load(handle)
    if not isinstance(deck, dict):
        raise Refused("the deck's data is a group of keys: title, organisation, language, density, pages")
    stem, kind = os.path.splitext(os.path.abspath(a.out))
    if kind.lower() not in (".pdf", ".pptx"):
        raise Refused("the deck is written as a PDF (%s.pdf) or as an editable PowerPoint file (%s.pptx); got %s"
                      % (os.path.basename(stem), os.path.basename(stem), os.path.basename(a.out)))
    try:
        inside = os.path.commonpath([PACK, os.path.dirname(stem)]) == PACK
    except ValueError:
        inside = False
    if inside:
        raise Refused("%s is inside the skill's own folder; write the deck into the person's folder, beside its data"
                      % os.path.basename(a.out))
    folder = os.path.dirname(os.path.abspath(a.deck))
    own_company(deck, a.deck)
    want_pdf = not (kind.lower() == ".pptx" and a.no_pdf)
    want_pptx = kind.lower() == ".pptx" or a.editable or editable(deck, a.look)
    if want_pptx:
        validate(deck)
        need_notes(deck)
    if want_pptx and NO_PPTX is not None:
        through_uv("python-pptx to write the editable file", NO_PPTX)
    name = count = None
    if want_pdf:
        import deck_html
        try:
            name, count, how, notes = deck_html.build_pdf(deck, stem + ".pdf", a.density, a.look, folder, keep_html=a.html)
        except deck_html.Missing as missing:
            through_uv(missing.what, missing)
        print("%s -> %s (%d pages, %s preset, printed by %s)" % (a.deck, stem + ".pdf", count, name, how))
        if notes:
            print("%d pieces of detail are not on the pages: the %s preset keeps them for the speaker's notes, which a PDF "
                  "does not carry; they are in the editable file (--editable)" % (notes, name))
    if want_pptx:
        name, count = build(deck, stem + ".pptx", a.density, a.look, folder)
        print("%s -> %s (%d pages, %s preset, editable)" % (a.deck, stem + ".pptx", count, name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
