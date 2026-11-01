#!/usr/bin/env python3
"""The business deck as a PDF: the pages written as one HTML file and printed.

deck_build.py lays every page out through one set of calls; this module answers those calls with
HTML instead of PowerPoint shapes, on the same positions, from the same look.json and density
preset. Text is real text, a table is a real table, a chart is a drawing (inline SVG) of the same
data, scale and colours the native chart gets. No number of the look is typed into the CSS: sizes,
inks, margins and letter spacing are read from the kit, as the PowerPoint layouts are.

The page is printed the way the library's other printed pages are (skills/_shared/letter.py and
html-deck's render_pdf.py): inside the app by `nodejam-print`, which uses the app's own Chromium;
outside it by a headless Chromium through Playwright, fetched through uv when this Python has none.

After printing, the PDF gets what a browser's print does not write: its title, author and language,
bookmarks (the sections with their pages, in the deck's own words), page labels (a backup page
is A1, A2 as on its running line) and, in the document's private data (PDF 1.7, 14.5, page-piece
dictionaries), a description of every page: which box holds which words, each chart's data, each
table's cells. The pack check reads that description and measures it against the printed pages.
Speaker notes are never written into the PDF.

    python3 deck_html.py --print <page>.html <out>.pdf      print one built page (what uv is asked to run)
"""
import base64
import datetime
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

PIECE = "/BusinessDeck"       # the key of the deck's description in the PDF's page-piece dictionary
FALLBACK = '"Liberation Sans", Arimo, Helvetica, sans-serif'    # faces that set on the same widths as Arial


class Missing(Exception):
    """A package this output needs is not in this Python."""

    def __init__(self, what, detail):
        super().__init__(str(detail))
        self.what = what


def esc(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def pt(value):
    """A length in points as CSS writes it."""
    return ("%.2f" % float(value)).rstrip("0").rstrip(".") + "pt" if value else "0"


def num(value):
    return ("%.2f" % float(value)).rstrip("0").rstrip(".") or "0"


def hexc(colour):
    return "#" + str(colour).lstrip("#").upper()


def number_text(value, places, figures=(",", ".")):
    return format(float(value), ",.%df" % int(places or 0)).translate(str.maketrans({",": figures[0], ".": figures[1]}))


# Languages that group thousands with a space or a point when the deck's words show neither.
SPACED = ("sv", "fi", "fr", "nb", "nn", "no", "pl", "cs")
POINTED = ("de", "da", "nl", "es", "it", "pt")


def number_figures(deck):
    """The thousands and decimal marks the deck's own words write ("793 400 kr" or "793,400"), so the values on a
    chart read as the sentences beside them do (the 10-12 web test: 53,200 on the bar, 53 200 kr in the title).
    With no grouped number in the words, the deck's language decides; English keeps 1,234.5."""
    words = json.dumps(deck["pages"], ensure_ascii=False)
    spaced = len(re.findall(r"\d[ \u00a0\u202f]\d{3}(?!\d)", words))
    commas = len(re.findall(r"\d,\d{3}(?!\d)", words))
    language = str(deck.get("language") or "").split("-")[0].lower()
    if spaced > commas or (not commas and language in SPACED):
        return "\u00a0", ","
    if not spaced and not commas and language in POINTED:
        return ".", ","
    return ",", "."


# ---------------------------------------------------------------- one page


class HtmlPage:
    """One page being filled. The same calls as deck_build.Slide: its placeholders by idx, and what it draws."""

    def __init__(self, book, layout_name, kind, deck_title, section):
        import deck_build as B
        self.B, self.book, self.kit = B, book, book.kit
        self.layout, self.kind = layout_name, kind
        self.n = len(book.pages) + 1
        self.dark = layout_name in B.DARK
        self.ground = self.kit.dark["ground"] if self.dark else self.kit.ink["ground"]
        self.notes = []
        self.slots, self.filled, self.order = {}, {}, []
        for idx, name, ph_kind, x, y, w, h, anchor, levels, align in book.boxes[layout_name]:
            idx = 0 if idx == "title" else idx
            levels = list(levels) + [levels[-1]] * (3 - len(levels))
            self.slots[idx] = {"name": name, "kind": "title" if ph_kind == "title" else "body", "box": [x, y, w, h],
                               "anchor": anchor, "levels": levels, "align": align}
            self.order.append(idx)
        self.under, self.drawn, self.running = [], [], []
        self._running_line(deck_title, section)

    # -- text

    def _para(self, text, style, bullet=None, level=0, colour=None):
        (size, pitch), ink, after = self.kit.styles[style]
        weight = self.kit.look["face"].get("title_weight" if style.split("-")[0] in ("title", "headline") else "weight", 400)
        return {"text": str(text), "size": size, "pitch": pitch, "after": after, "indent": round(size * 0.95) if bullet else 0,
                "spacing": round(self.kit.spacing(style), 3), "colour": str(colour or ink).upper(), "bold": int(weight) >= 600,
                "level": level, "bullet": bullet or ""}

    def _item(self, name, kind, x, y, w, h, paras, anchor="t", align="l"):
        return {"t": "text", "name": name, "kind": kind, "x": x, "y": y, "w": w, "h": h, "anchor": anchor, "align": align,
                "paras": paras}

    def _running_line(self, deck_title, section):
        """The organisation (its logo, or its name), the deck title, the section and the page number, each in a
        box of one height on one line, so all four stand on one baseline: deck_build._running, as HTML."""
        kit, name = self.kit, self.layout
        y, h = kit.running_y, kit.small_line
        second = "small-dark" if self.dark else "small"
        logo = kit.look.get("logo") or {}
        file = logo.get("dark_file" if self.dark else "file") or ""
        organisation = self.book.organisation
        ox, ow = kit.page_span(0, 4)
        if file:
            path = file if os.path.isabs(file) else os.path.join(kit.look["_folder"], file)
            if not os.path.isfile(path):
                raise self.B.Refused("the look names the logo %s, which is not there" % file)
            uri, (wide, high) = self.book.picture(path)
            height = float(logo.get("height", 12))
            size = kit.styles[second][0][0]
            baseline = y + h - (kit.small_line - size) / 2.0 - size * 0.22
            self.running.append({"t": "logo", "name": "Logo", "x": kit.M, "y": baseline - height * (1 - float(logo.get("below_baseline", 0))),
                                 "w": height * wide / float(high), "h": height, "alt": logo.get("alt") or organisation, "src": uri})
        elif organisation:
            self.running.append(self._item("Organisation", "box", ox, y, ow, h, [self._para(organisation, second)], anchor="b"))
        if name == "Cover":
            return
        if name != "Closing":
            fx, fw = kit.page_span(4, 4)
            if deck_title:
                self.running.append(self._item("Deck title", "footer", fx, y, fw, h, [self._para(deck_title, second)], anchor="b"))
            if name not in ("Section", "Appendix") and section:
                if kit.c0:
                    sx, sw = kit.page_span(0, kit.c0)
                    self.running.append(self._item("Section", "body", sx, kit.title_y + 4, sw - kit.G, 3 * h,
                                                   [self._para(section, second)], anchor="t"))
                else:
                    sx, sw = kit.page_span(8, 3)
                    self.running.append(self._item("Section", "body", sx, y, sw, h, [self._para(section, second)], anchor="b"))
        nx, nw = kit.page_span(11, 1)
        # A backup page is numbered in the appendix's own count (A1, A2), a page of the storyline by its place.
        number = getattr(kit, "number", None) or str(self.n)
        self.running.append(self._item("Page number", "number", nx, y, nw, h, [self._para(number, second)], anchor="b", align="r"))

    def put(self, idx, paras):
        """Fill a placeholder with paragraphs given as text or (text, level); an empty list removes it."""
        if idx not in self.slots:
            return None
        paras = [p for p in paras if (p[0] if isinstance(p, tuple) else p)]
        if not paras:
            self.drop(idx)
            return None
        self.filled[idx] = [p if isinstance(p, tuple) else (p, 0) for p in paras]
        return self.slots[idx]

    def drop(self, idx):
        self.slots.pop(idx, None)
        self.filled.pop(idx, None)

    def place(self, idx, x, y, w, h):
        if idx in self.slots:
            self.slots[idx]["box"] = [x, y, w, h]

    def title(self, text, part=None):
        if part and part[1] > 1:
            text = "%s (%d/%d)" % (text, part[0], part[1])
        self.put(0, [text])

    def finish(self, page):
        self.put(self.B.IDX_SOURCE, [page.get("source") or ""])
        self.notes = [n for n in [page.get("notes") or ""] + self.notes if n]

    # -- what a page draws besides its placeholders

    def rule(self, x, y, w, strong=False, name="Rule"):
        colour = self.kit.ink["rule"] if strong else self.kit.ink["hairline"]
        self.drawn.append({"t": "mark", "kind": "line", "name": name, "x": x, "y": y, "w": w, "h": 0, "colour": colour.upper()})

    def vrule(self, x, y, h, strong=False, name="Rule"):
        colour = self.kit.ink["rule"] if strong else self.kit.ink["hairline"]
        self.drawn.append({"t": "mark", "kind": "line", "name": name, "x": x, "y": y, "w": 0, "h": h, "colour": colour.upper()})

    def dot(self, x, y, size, fill, name="Mark"):
        self.drawn.append({"t": "mark", "kind": "dot", "name": name, "x": x, "y": y, "w": size, "h": size, "colour": fill.upper()})

    def panel(self, x, y, w, h, fill, name="Panel"):
        self.under.append({"t": "mark", "kind": "box", "name": name, "x": x, "y": y, "w": w, "h": h, "colour": fill.upper()})

    def label(self, name, x, y, w, h, text, style, align="l", colour=None):
        self.drawn.append(self._item(name, "box", x, y, w, h, [self._para(text, style, colour=colour)], align=align))

    def chart(self, kind, cats, series, page, x, y, w, h, alt):
        svg, record = chart_svg(self, kind, cats, series, page, x, y, w, h, alt)
        record["svg"] = svg
        self.drawn.insert(self._first_label(), record)
        return record

    def _first_label(self):
        """A chart stands before the series names drawn for it, as the native chart stands before its text boxes."""
        for i, item in enumerate(self.drawn):
            if item["t"] == "text" and item["name"] == "Series label":
                return i
        return len(self.drawn)

    def table(self, plan, x, y, highlight_row=None, highlight_col=None, label_col=False):
        frame = {"t": "table", "x": x, "y": y, "plan": plan, "row": highlight_row, "col": highlight_col, "label_col": label_col}
        self.drawn.append(frame)
        return frame

    def settle(self, frame, top):
        frame["y"] = top

    def picture(self, path, x, y, w, h, alt, pixels=None):
        uri, size = self.book.picture(path)
        self.drawn.append({"t": "picture", "name": "Figure", "x": x, "y": y, "w": w, "h": h, "alt": alt, "px": list(pixels or size),
                           "src": uri})

    # -- out

    def items(self):
        """Everything on the page in the order it is written and read: the grounds, the title, the placeholders
        in the layout's order, what the page drew, the running line."""
        out = list(self.under)
        for idx in self.order:
            if idx not in self.filled:
                continue
            slot = self.slots[idx]
            paras = []
            for text, level in self.filled[idx]:
                style, bullet = slot["levels"][min(level, 2)]
                paras.append(self._para(text, style, bullet, level))
            x, y, w, h = slot["box"]
            out.append(self._item(slot["name"], slot["kind"], x, y, w, h, paras, slot["anchor"], slot["align"]))
        for item in self.drawn:
            out.append(table_item(self, item) if item["t"] == "table" else item)
        return out + self.running

    def html(self, items):
        parts = ['<section class="slide%s" data-kind="%s" style="background:%s">' % (" dark" if self.dark else "", esc(self.kind), hexc(self.ground))]
        for item in items:
            parts.append(RENDER[item["t"]](self, item))
        parts.append("</section>")
        return "\n".join(parts)


def box_style(item, extra=""):
    return "left:%s;top:%s;width:%s;height:%s%s" % (pt(item["x"]), pt(item["y"]), pt(item["w"]), pt(item["h"]), extra)


def para_style(p, last=True):
    out = ["font-size:%s" % pt(p["size"]), "line-height:%s" % pt(p["pitch"]), "color:%s" % hexc(p["colour"])]
    if p["spacing"]:
        out.append("letter-spacing:%s" % pt(p["spacing"]))
    if p["bold"]:
        out.append("font-weight:700")
    if p["after"] and not last:
        out.append("margin-bottom:%s" % pt(p["after"]))
    if p["bullet"]:
        out.append("padding-left:%s;text-indent:-%s" % (pt(p["indent"]), pt(p["indent"])))
    return ";".join(out)


def text_html(page, item):
    tag = "h1" if item["kind"] == "title" else "p"
    paras = []
    for n, p in enumerate(item["paras"]):
        words = esc(p["text"]).replace("\n", "<br>")
        if p["bullet"]:
            words = '<span class="bu" style="width:%s">%s</span>%s' % (pt(p["indent"]), esc(p["bullet"]), words)
        paras.append('<%s style="%s">%s</%s>' % (tag, para_style(p, n == len(item["paras"]) - 1), words, tag))
    cls = "b" + {"b": " ab", "ctr": " ac"}.get(item["anchor"], "") + {"r": " tr", "ctr": " tc"}.get(item["align"], "")
    return '<div class="%s" data-name="%s" style="%s">%s</div>' % (cls, esc(item["name"]), box_style(item), "".join(paras))


def mark_html(page, item):
    colour = hexc(item["colour"])
    if item["kind"] == "line":
        # a line of 0.75 pt, centred on its position as a drawn line is
        if item["h"]:
            return '<i class="ln" style="left:%s;top:%s;width:0.75pt;height:%s;background:%s"></i>' % (
                pt(item["x"] - 0.375), pt(item["y"]), pt(item["h"]), colour)
        return '<i class="ln" style="left:%s;top:%s;width:%s;height:0.75pt;background:%s"></i>' % (
            pt(item["x"]), pt(item["y"] - 0.375), pt(item["w"]), colour)
    radius = ";border-radius:50%" if item["kind"] == "dot" else ""
    return '<i class="ln" style="%s"></i>' % box_style(item, ";background:%s%s" % (colour, radius))


def picture_html(page, item):
    edge = ";outline:0.75pt solid %s;outline-offset:-0.375pt" % hexc(page.kit.ink["hairline"]) if item["t"] == "picture" else ""
    return '<img class="pic" src="%s" alt="%s" style="%s">' % (item["src"], esc(item["alt"]), box_style(item, edge))


def chart_html(page, item):
    return item["svg"]


def table_item(page, frame):
    """The planned table with every cell's place and words, as the page writes it and the check reads it."""
    kit, plan = page.kit, frame["plan"]
    columns, rows, numeric, widths, heights = (plan[k] for k in ("columns", "rows", "numeric", "widths", "heights"))
    (size, line), ink, _ = kit.styles["body"]
    second, gap = kit.ink["second"], kit.G
    n_cols = len(columns)
    out, y = [], frame["y"]
    for r in range(len(rows) + 1):
        cells, x = [], frame["x"]
        for c in range(n_cols):
            text, more = (columns[c], "") if r == 0 else (str(rows[r - 1][c][0]), str(rows[r - 1][c][1] or ""))
            right = numeric[c]
            dim = (r == 0 and not frame["label_col"]) or (frame["label_col"] and c == 0)
            marked = (frame["row"] is not None and r == frame["row"] + 1) or (frame["col"] is not None and c == frame["col"])
            paras = []
            if str(text).strip():
                paras.append({"text": str(text), "size": size, "pitch": line, "after": 0, "indent": 0, "spacing": 0,
                              "colour": (second if dim else ink).upper(), "bold": False, "level": 0, "bullet": ""})
            if more.strip():
                paras.append({"text": more, "size": size, "pitch": line, "after": 0, "indent": 0, "spacing": 0,
                              "colour": second.upper(), "bold": False, "level": 0, "bullet": ""})
            cells.append({"paras": paras, "x": x, "y": y, "w": widths[c], "h": heights[r], "align": "r" if right else "l",
                          "insets": [0 if (right or c == 0) else gap, 0, gap if (right and c < n_cols - 1) else 0, 0],
                          "fill": kit.ink["raised"].upper() if marked else None,
                          "under": (kit.ink["rule"] if r == 0 else kit.ink["hairline"]).upper()})
            x += widths[c]
        out.append(cells)
        y += heights[r]
    return {"t": "table", "x": frame["x"], "y": frame["y"], "w": plan["total"], "h": sum(heights), "widths": widths,
            "heights": heights, "header": True, "rows": out}


def table_html(page, item):
    parts = ['<table class="tb" style="left:%s;top:%s;width:%s">' % (pt(item["x"]), pt(item["y"]), pt(item["w"])),
             "<colgroup>%s</colgroup>" % "".join('<col style="width:%s">' % pt(w) for w in item["widths"])]
    for r, row in enumerate(item["rows"]):
        parts.append("<thead>" if r == 0 else "<tbody>" if r == 1 else "")
        cells = []
        for cell in row:
            style = ["height:%s" % pt(cell["h"]), "background-image:linear-gradient(%s,%s)" % (hexc(cell["under"]), hexc(cell["under"]))]
            if cell["fill"]:
                style.append("background-color:%s" % hexc(cell["fill"]))
            if cell["align"] == "r":
                style.append("text-align:right")
            if cell["insets"][0]:
                style.append("padding-left:%s" % pt(cell["insets"][0]))
            if cell["insets"][2]:
                style.append("padding-right:%s" % pt(cell["insets"][2]))
            words = "".join('<div style="%s">%s</div>' % (para_style(p), esc(p["text"]).replace("\n", "<br>")) for p in cell["paras"])
            tag = 'th scope="col"' if r == 0 else "td"
            cells.append("<%s style=\"%s\">%s</%s>" % (tag, ";".join(style), words, tag.split()[0]))
        parts.append("<tr>%s</tr>" % "".join(cells))
        parts.append("</thead>" if r == 0 else "")
    parts.append("</tbody></table>" if len(item["rows"]) > 1 else "</table>")
    return "".join(parts)


RENDER = {"text": text_html, "mark": mark_html, "picture": picture_html, "logo": picture_html, "chart": chart_html,
          "table": table_html}


# ---------------------------------------------------------------- charts


def luminance(hexcode):
    h = str(hexcode).lstrip("#")
    ch = []
    for i in (0, 2, 4):
        v = int(h[i:i + 2], 16) / 255.0
        ch.append(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]


def chart_svg(page, kind, cats, series, data, fx, fy, fw, fh, alt):
    """One chart as a drawing: the data, the scale and the colours the native chart gets (deck_build.chart_scale
    and chart_colours), dressed the same way: no title, no value axis, values on the marks, the categories
    under them, series named on or beside their marks, one highlight, every word horizontal.
    Returns the SVG and what the check reads of a chart."""
    import deck_text as T
    B, kit = page.B, page.kit
    marks, size = kit.marks, float(kit.sc["chart"])
    line = kit.styles["head"][0][1]
    ink, second, ground = kit.ink["ink"], kit.ink["second"], kit.ink["ground"]
    axis = kit.ink["rule"]
    highlight = data.get("highlight")
    places = int(data.get("decimals", 0) or 0)
    figures = page.book.figures
    names = [str(s.get("name") or "") for s in series]
    multi = len(series) > 1
    stacked = kind == "stacked"
    colours = B.chart_colours(kit, kind, series, highlight)
    low, high = B.chart_scale(kind, cats, series, data.get("axis_min"))
    span = (high - low) or 1.0
    count = len(cats)
    gap = float(marks.get("gap_width", 50)) / 100.0
    wide = lambda text: T.measure(str(text), size, kit.advance)  # noqa: E731
    value = lambda s, i: 0.0 if s["values"][i] is None else float(s["values"][i])  # noqa: E731
    out = []

    def text(x, y, words, anchor="middle", fill=second):
        out.append('<text x="%s" y="%s" text-anchor="%s" fill="%s">%s</text>' % (num(x), num(y), anchor, hexc(fill), esc(words)))

    def rect(x, y, w, h, fill, stroke=None):
        edge = ' stroke="%s" stroke-width="0.75"' % hexc(stroke) if stroke else ""
        out.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s"%s/>' % (num(x), num(y), num(max(w, 0)), num(max(h, 0)), hexc(fill), edge))

    def stroke_of(colour):
        hollow = colour.upper() == ground.upper()
        return marks["outline"] if hollow else (ground if stacked else None)

    legend = len(series) > kit.d["legend.direct_max"]
    head = 0.0
    if legend:
        # more series than are named on their marks: one line of keys over the plot
        x = 0.0
        for n, name in enumerate(names):
            rect(x, 2, size * 0.7, size * 0.7, colours[n], stroke_of(colours[n]))
            text(x + size, 2 + size * 0.7, name, "start")
            x += size + wide(name) + 16
        head = line + 4
    base = min(max(0.0, low), high)
    points = {}
    if kind in ("column", "stacked"):
        if stacked:
            x0, y0, pw, ph = 0.0, head + 0.05 * fh, 0.8 * fw, 0.82 * fh - head
        else:
            step = fw / float(count)
            cat_lines = max(len(T.wrap(c, size, max(20.0, step - 6), kit.advance)) for c in cats)
            over = (2 if multi and not legend else 1) * line + 4
            x0, y0, pw = 0.0, head + over, fw
            ph = fh - y0 - (cat_lines * line + 8)
        step = pw / float(count)
        group = step / (1.0 + gap)
        bar = group if stacked else group / len(series)
        Y = lambda v: y0 + ph * (1 - (v - low) / span)  # noqa: E731
        for i in range(count):
            gx = x0 + i * step + (step - group) / 2.0
            run = 0.0
            for n, s in enumerate(series):
                v = value(s, i)
                colour = colours[n]
                if not multi and highlight is not None and cats[i] == str(highlight):
                    colour = marks["highlight"]
                    points[i] = colour
                if stacked:
                    a, b, bx = Y(run), Y(run + v), gx
                    run += v
                else:
                    a, b, bx = Y(base), Y(max(low, min(high, v))), gx + n * bar
                rect(bx, min(a, b), bar, abs(a - b), colour, stroke_of(colour))
                if stacked:
                    if v:          # a part that is nothing prints nothing
                        text(bx + bar / 2.0, (a + b) / 2.0 + 0.36 * size, number_text(v, places, figures),
                             fill=marks.get("on_dark", "FFFFFF") if luminance(colour) < 0.3 else ink)
                else:
                    ly = b - 5 if v >= 0 else b + size + 3
                    text(bx + bar / 2.0, ly, number_text(v, places, figures), fill=ink)
                    if multi and i == 0 and not legend:    # each series is named once, on its first mark, above the value
                        text(bx + bar / 2.0, ly - line, names[n], fill=ink)
            for k, part in enumerate(T.wrap(cats[i], size, max(20.0, step - 6), kit.advance)):
                text(x0 + i * step + step / 2.0, y0 + ph + (k + 1) * line + 1, part)
        out.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="0.75"/>' % (num(x0), num(Y(base)), num(x0 + pw), num(Y(base)), hexc(axis)))
        if stacked and not legend:
            # the series are named beside the last stack, in the order they are stacked
            run, last = 0.0, count - 1
            for n, s in enumerate(series):
                v = value(s, last)
                mid = run + v / 2.0
                run += v
                x = fx + x0 + pw + 8
                page.label("Series label", x, fy + Y(mid) - line / 2.0, fx + fw - x, line, names[n], "head",
                           colour=ink if colours[n] == marks["highlight"] else second)
    elif kind == "bar":
        labels = min(0.4 * fw, max(wide(c) for c in cats) + 10)
        ends = max(wide(number_text(value(s, i), places, figures)) for s in series for i in range(count)) + 10
        named = (max(wide(n) for n in names) + 8) if multi and not legend else 0.0
        x0, y0, pw, ph = labels, head, max(40.0, fw - labels - ends - named), fh - head
        step = ph / float(count)
        group = step / (1.0 + gap)
        bar = group / len(series)
        X = lambda v: x0 + pw * (v - low) / span  # noqa: E731
        for i in range(count):
            gy = y0 + i * step + (step - group) / 2.0
            for n, s in enumerate(series):
                v = value(s, i)
                colour = colours[n]
                if not multi and highlight is not None and cats[i] == str(highlight):
                    colour = marks["highlight"]
                    points[i] = colour
                a, b, by = X(base), X(max(low, min(high, v))), gy + n * bar
                rect(min(a, b), by, abs(a - b), bar, colour, stroke_of(colour))
                shown = number_text(v, places, figures)
                text(max(a, b) + 5, by + bar / 2.0 + 0.36 * size, shown, "start", ink)
                if multi and i == 0 and not legend:
                    text(max(a, b) + 5 + wide(shown) + 8, by + bar / 2.0 + 0.36 * size, names[n], "start", second)
            text(x0 - 8, gy + group / 2.0 + 0.36 * size, cats[i], "end")
        out.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="0.75"/>' % (num(X(base)), num(y0), num(X(base)), num(y0 + ph), hexc(axis)))
    else:
        # A line is valued at both its ends and named beside its right end: no legend, no value axis.
        last = count - 1
        widest = max(T.measure(format(value(s, last), ".%df" % places), size, kit.advance) for s in series)
        named = max([wide(n) for n in names] + [0.0]) if multi else 0.0
        px, py, ph_share = 0.07, 0.08, 0.78
        pw_share = max(0.5, 1.0 - px - (widest + 14 + named + 10) / float(fw))
        x0, y0, pw, ph = px * fw, head + py * fh, pw_share * fw, ph_share * fh - head
        X = lambda i: x0 + pw * i / float(max(1, count - 1))  # noqa: E731
        Y = lambda v: y0 + ph * (1 - (v - low) / span)  # noqa: E731
        out.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="0.75"/>' % (num(x0), num(y0 + ph), num(x0 + pw), num(y0 + ph), hexc(axis)))
        for n, s in enumerate(series):
            colour = colours[n]
            strong = colour == marks["highlight"]
            drawn = marks["outline"] if colour.upper() == ground.upper() else colour
            width = marks.get("line_width", 2.25) if strong else marks.get("neutral_line_width", 1.5)
            path = " ".join("%s,%s" % (num(X(i)), num(Y(float(v)))) for i, v in enumerate(s["values"]) if v is not None)
            out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linejoin="round" stroke-linecap="round"/>'
                       % (path, hexc(drawn), num(width)))
            shade = ink if strong or not multi else second
            text(X(last) + 6, Y(value(s, last)) + 0.36 * size, number_text(value(s, last), places, figures), "start", shade)
            text(X(0) - 6, Y(value(s, 0)) + 0.36 * size, number_text(value(s, 0), places, figures), "end", shade)
        for i in range(count):
            text(X(i), y0 + ph + line + 1, cats[i])
        if multi and not legend:
            # each line is named beside its right end, after its last value; names keep a line's distance
            x = fx + x0 + pw + widest + 14
            spots = sorted([fy + Y(value(s, last)) - line / 2.0, n] for n, s in enumerate(series))
            for i in range(1, len(spots)):
                spots[i][0] = max(spots[i][0], spots[i - 1][0] + line)
            for y, n in spots:
                page.label("Series label", x, y, max(20.0, fx + fw - x), line, names[n], "head",
                           colour=ink if colours[n] == marks["highlight"] else second)
    svg = ('<svg class="ch" role="img" aria-label="%s" style="left:%s;top:%s" width="%s" height="%s" viewBox="0 0 %s %s" '
           'font-size="%s"><title>%s</title>%s</svg>'
           % (esc(alt), pt(fx), pt(fy), pt(fw), pt(fh), num(fw), num(fh), num(size), esc(alt), "".join(out)))
    record = {"t": "chart", "x": fx, "y": fy, "w": fw, "h": fh, "alt": alt, "kinds": [kind], "categories": list(cats),
              "legend": legend, "axis_min": low, "axis_max": high, "sizes": [size], "gap": gap * 100.0,
              "plot": [x0 / fw, y0 / fh, pw / fw, ph / fh],
              "series": [{"name": names[n], "kind": kind, "values": [float(v) for v in s["values"] if v is not None],
                          "colour": colours[n].upper(), "outline": (stroke_of(colours[n]) or "").upper() or None,
                          "points": {str(i): c.upper() for i, c in points.items()} if not multi else {},
                          "valued": True, "named": bool(multi and kind in ("column", "bar") and not legend)}
                         for n, s in enumerate(series)]}
    return svg, record


# ---------------------------------------------------------------- the deck


class Book:
    """The deck being written as HTML: what deck_build.draw fills in place of a presentation."""

    def __init__(self, kit, deck):
        import deck_build as B
        self.kit, self.deck, self.pages = kit, deck, []
        self.boxes = B.layout_boxes(kit)
        self.organisation = deck.get("organisation") or ""
        self.figures = number_figures(deck)
        self._pictures = {}

    def page(self, kit, layout_name, kind, deck_title, section):
        pg = HtmlPage(self, layout_name, kind, deck_title, section)
        self.pages.append(pg)
        return pg

    def picture(self, path):
        """A picture as the page carries it (inside the page, so the page is one file) and its size in pixels."""
        path = os.path.abspath(path)
        if path not in self._pictures:
            try:
                from PIL import Image
            except ImportError as missing:
                raise Missing("Pillow to read a picture", missing)
            with Image.open(path) as im:
                kind, size = (im.format or "PNG").lower(), im.size
            with open(path, "rb") as handle:
                self._pictures[path] = ("data:image/%s;base64,%s" % (kind, base64.b64encode(handle.read()).decode("ascii")), size)
        return self._pictures[path]

    def css(self):
        kit = self.kit
        face = kit.look["face"]
        return "\n".join([
            "@page{size:%s %s;margin:0}" % (pt(kit.W), pt(kit.H)),
            "*{box-sizing:border-box}",
            "html,body{margin:0;padding:0}",
            "body{font-family:\"%s\",%s;font-weight:%d;font-variant-ligatures:none;hyphens:manual;"
            "-webkit-print-color-adjust:exact;print-color-adjust:exact}" % (face["name"], FALLBACK, int(face.get("weight", 400))),
            ".slide{position:relative;width:%s;height:%s;overflow:hidden;break-after:page;page-break-after:always}" % (pt(kit.W), pt(kit.H)),
            ".slide:last-child{break-after:auto;page-break-after:auto}",
            ".b{position:absolute;display:flex;flex-direction:column;justify-content:flex-start}",
            ".b.ab{justify-content:flex-end}.b.ac{justify-content:center}.b.tr{text-align:right}.b.tc{text-align:center}",
            ".b p,.b h1{margin:0;font-weight:inherit;font-size:inherit}",
            ".bu{display:inline-block;text-indent:0}",
            ".ln,.pic,.ch,.tb{position:absolute;display:block}",
            ".ch text{font-family:inherit}",
            ".tb{border-collapse:collapse;border-spacing:0;table-layout:fixed}",
            ".tb th,.tb td{padding:0;vertical-align:middle;text-align:left;font-weight:inherit;"
            "background-repeat:no-repeat;background-position:left bottom;background-size:100% 0.75pt}",
        ])

    def html(self, items, mark):
        deck = self.deck
        head = ['<!doctype html>', '<html lang="%s"><head><meta charset="utf-8">' % esc(deck["language"]),
                "<title>%s</title>" % esc(deck["title"]),
                '<meta name="generator" content="%s">' % esc(mark),
                '<meta name="author" content="%s">' % esc(self.organisation),
                "<style>%s</style></head><body>" % self.css()]
        return "\n".join(head + [page.html(page_items) for page, page_items in zip(self.pages, items)] + ["</body></html>"])

    def describe(self, items, mark, preset):
        """What the check reads: every page's boxes, words, charts and tables as they were set. No notes."""
        kit = self.kit
        slides = []
        for page, page_items in zip(self.pages, items):
            kept = []
            for item in page_items:
                item = {k: v for k, v in item.items() if k not in ("svg", "src")}
                kept.append(item)
            slides.append({"n": page.n, "kind": page.kind, "layout": page.layout, "ground": page.ground.upper(), "items": kept})
        return {"mark": mark, "density": preset, "page": [kit.W, kit.H], "face": kit.face, "advance": kit.advance,
                "title": self.deck["title"], "language": self.deck["language"],
                "theme": {"accent1": kit.marks["highlight"].upper(), "dk1": kit.ink["ink"].upper()}, "slides": slides}

    def outline(self):
        """The bookmarks, in the deck's own words: a page's title, under its section's name where it has one."""
        out, open_section = [], None
        for page in self.pages:
            title = " ".join(text for text, _ in page.filled.get(0, []))
            section = next((p["paras"][0]["text"] for p in page.running if p["t"] == "text" and p["name"] == "Section"), "")
            if section:
                if open_section is None or open_section[0] != section:
                    open_section = [section, page.n - 1, []]
                    out.append(open_section)
                open_section[2].append((title, page.n - 1))
            else:
                open_section = None
                out.append([title, page.n - 1, []])
        return out

    def labels(self):
        """Page labels as the running line numbers the pages: 1, 2, 3 and, behind the appendix, A1, A2."""
        runs = []
        for page in self.pages:
            number = next((p["paras"][0]["text"] for p in page.running if p["t"] == "text" and p["name"] == "Page number"), str(page.n))
            prefix = number.rstrip("0123456789")
            if not runs or runs[-1][2] != prefix:
                runs.append([page.n - 1, page.n - 1, prefix, int(number[len(prefix):] or page.n)])
            else:
                runs[-1][1] = page.n - 1
        return runs


# ---------------------------------------------------------------- printing


def _playwright(page, pdf):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--no-sandbox"])
        tab = browser.new_page()
        tab.goto(pathlib.Path(page).resolve().as_uri())
        tab.evaluate("document.fonts.ready")
        tab.pdf(path=str(pdf), prefer_css_page_size=True, print_background=True)
        browser.close()


def print_pdf(page, pdf, width, height):
    """Print the page with the app's own Chromium, or with a headless one through Playwright outside the app: the
    way the library's other printed pages go. The page's own @page size rules in both. Returns who printed."""
    tool = shutil.which("nodejam-print")
    why = "nodejam-print is not on PATH"
    if tool:
        r = subprocess.run([tool, os.path.abspath(page), os.path.abspath(pdf), "--width", str(int(round(width * 96 / 72.0))),
                            "--height", str(int(round(height * 96 / 72.0)))], capture_output=True, text=True)
        if r.returncode == 0 and os.path.isfile(pdf):
            return "the app"
        why = ((r.stderr or r.stdout).strip().splitlines() or ["nodejam-print failed"])[-1]
    try:
        import playwright  # noqa: F401
        have = True
    except ImportError:
        have = False
    if have:
        try:
            _playwright(page, pdf)
            return "a headless browser"
        except Exception as error:
            why = (str(error).strip().splitlines() or [why])[0]
    uv = shutil.which("uv")
    if uv and not have:
        r = subprocess.run([uv, "run", "--quiet", "--no-project", "--with", "playwright", "python3", os.path.abspath(__file__),
                            "--print", os.path.abspath(page), os.path.abspath(pdf)], capture_output=True, text=True)
        if r.returncode == 0 and os.path.isfile(pdf):
            return "a headless browser, through uv"
        why = ((r.stderr or r.stdout).strip().splitlines() or [why])[-1]
    raise SystemExit("could not print the deck's pages: %s. Inside the app this needs nothing. Outside it the pages are printed by a "
                     "headless browser: install uv, and the browser once with `uv run --with playwright playwright install chromium`; "
                     "then run the same command again" % why)


def finish_pdf(raw, out, book, description):
    """What a browser's print leaves out: the title, the author and the language, bookmarks, page labels and the
    deck's own description of its pages."""
    try:
        from pypdf import PdfReader, PdfWriter
        from pypdf.generic import (BooleanObject, DecodedStreamObject, DictionaryObject, NameObject, TextStringObject)
    except ImportError as missing:
        raise Missing("pypdf to finish the PDF", missing)
    reader = PdfReader(raw)
    if len(reader.pages) != len(book.pages):
        raise SystemExit("the deck has %d pages and the print came out with %d: something on a page is larger than the page"
                         % (len(book.pages), len(reader.pages)))
    writer = PdfWriter(clone_from=reader)
    deck = book.deck
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("D:%Y%m%d%H%M%S+00'00'")
    writer.add_metadata({"/Title": deck["title"], "/Author": book.organisation, "/Creator": description["mark"]})
    root = writer._root_object
    root[NameObject("/Lang")] = TextStringObject(deck["language"])
    root[NameObject("/ViewerPreferences")] = DictionaryObject({NameObject("/DisplayDocTitle"): BooleanObject(True)})
    for title, index, children in book.outline():
        parent = writer.add_outline_item(title, index)
        for child, at in children:
            writer.add_outline_item(child, at, parent=parent)
    for first, last, prefix, start in book.labels():
        writer.set_page_label(first, last, style="/D", prefix=prefix or None, start=start)
    stream = DecodedStreamObject()
    stream.set_data(json.dumps(description, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    private = writer._add_object(stream.flate_encode())
    root[NameObject("/PieceInfo")] = DictionaryObject({NameObject(PIECE): DictionaryObject({
        NameObject("/LastModified"): TextStringObject(stamp), NameObject("/Private"): private})})
    with open(out, "wb") as handle:
        writer.write(handle)


def build_pdf(deck, out, density_name=None, look_path=None, folder=None, keep_html=False):
    """Write the deck to `out` as a PDF. Returns the preset's name, the number of pages, who printed them and
    how many pieces of detail the preset kept off the pages for the speaker's notes."""
    import deck_build as B
    try:
        import pypdf  # noqa: F401
    except ImportError as missing:
        raise Missing("pypdf to finish the PDF", missing)
    kit, deck, pages, name = B.prepare(deck, density_name, look_path, folder)
    book = Book(kit, deck)
    B.draw(book, kit, deck, pages)
    mark = "%s density=%s" % (B.MARK, name)
    items = [page.items() for page in book.pages]
    page = book.html(items, mark)
    with tempfile.TemporaryDirectory(prefix="deck-pdf-") as tmp:
        source, raw = os.path.join(tmp, "deck.html"), os.path.join(tmp, "deck.pdf")
        with open(source, "w", encoding="utf-8") as handle:
            handle.write(page)
        how = print_pdf(source, raw, kit.W, kit.H)
        finish_pdf(raw, out, book, book.describe(items, mark, name))
    if keep_html:
        with open(os.path.splitext(out)[0] + ".html", "w", encoding="utf-8") as handle:
            handle.write(page)
    kept = sum(len(p.notes) for p in book.pages) - sum(1 for p, src in zip(book.pages, pages) if src.get("notes"))
    return name, len(book.pages), how, max(0, kept) if kit.build.get("detail") == "notes" else 0


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--print":
        _playwright(sys.argv[2], sys.argv[3])
        sys.exit(0)
    sys.exit("deck_html.py is run by deck_build.py: python3 deck_build.py <deck>.deck.json <out>.pdf")
