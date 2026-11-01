#!/usr/bin/env python3
"""Build a diagram from its data: one self-contained HTML page with the drawing inline, and beside it the SVG,
a PNG and a PDF.

    python3 diagram.py <name>.diagram.json [--look look.json] [--no-print]

writes <name>.html (the master: the page with its title, the drawing, the legend and the source line), <name>.svg
(the drawing alone, for a document or a deck to place), <name>.png (the drawing at twice its size) and <name>.pdf
(the page, one sheet the size of the drawing). The PDF is what is handed back first.

The agent writes what the diagram says (the steps, the people, the dates, the items); this script owns every
coordinate. The grammar is diagram-design's (github.com/cathrynlavery/diagram-design, MIT, 2.6.74): the node box
(an opaque mask, then the box at rx 6, the name, a sublabel), arrows drawn before boxes, orthogonal connectors with
r 8 elbows, fanned attach points 12 px or more apart, arrow labels of 14 characters at most in capitals on an
opaque plate 8 px clear of their stroke, a legend as a strip under the drawing, the accessible SVG contract
(role img, a title and a desc named by aria-labelledby, ids prefixed by the file's slug), a 4 px grid, the
slide-16x9 width of 1280 with the presentation type ramp and a height fitted to the content. The layouts follow
its type references for flowchart, swimlane, org chart, timeline, gantt, quadrant and layer stack.

The look is the library's one look file, skills/business-deck/look.json (a company pack replaces it): its face,
its inks and its highlight. No web font and no remote reference: the page renders the same with no network.

Seven types; the data of each is in SKILL.md and an example of each is in ../templates/.
Standard library only, apart from printing: the app's own browser engine (nodejam-print), or Playwright outside
the app.
"""
import argparse
import datetime as dt
import html
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
LOOK = SKILL.parent / "business-deck" / "look.json"

TYPES = ("flowchart", "swimlane", "org-chart", "timeline", "gantt", "quadrant", "layers")
WIDTH = 1280                     # slide-16x9 (output-spec.md, Size)
MARGIN = 40                      # 'fit': 40 px outer margin on every side
# The presentation type ramp (output-spec.md, Type ramp per size class). Eyebrows, tags and legend keys take the
# top of the dense-annotation range (11) so a drawing placed in a deck or a document stays legible.
RAMP = {"name": 16, "sub": 12, "arrow": 12, "eyebrow": 11, "group": 14, "row": 11, "title": 40}
NODE_MIN_H = 64                  # presentation: node box min height 64
GAP = 40                         # presentation: min gap between nodes 40
WIDTHS = (160, 200, 240, 320)    # layout-budget.md node widths, the presentation-sized ones
SANS_EM, MONO_EM, WIDE_EM = 0.60, 0.62, 1.0   # style-guide.md, Width budget
ARROW_LABEL_MAX = 14

# Per-type limits (SKILL.md section 7 and layout-budget.md): the check holds the same numbers.
LIMITS = {"nodes": 9, "arrows": 12, "focal": 2, "lanes": 5, "org_nodes": 12, "org_depth": 4, "org_children": 5,
          "org_focal": 1, "tasks": 12, "items": 12, "layers": (4, 6)}


class DiagramError(ValueError):
    """The data cannot be drawn as it stands; the message says what to change."""


# ---- the look ---------------------------------------------------------------------------------------------------

def hexcol(value):
    value = str(value or "").strip().lstrip("#")
    if not re.fullmatch(r"[0-9A-Fa-f]{6}", value):
        raise DiagramError("the look has a colour that is not six hex digits: %r" % value)
    return "#" + value.upper()


def mix(fg, bg, alpha):
    """fg at alpha over bg, as one opaque colour (the source's tints, flattened so print and PNG agree)."""
    f = [int(fg[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(bg[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02X%02X%02X" % tuple(round(alpha * x + (1 - alpha) * y) for x, y in zip(f, b))


def load_look(path=None):
    look = json.loads(Path(path or LOOK).read_text(encoding="utf-8"))
    ink, face = look.get("ink") or {}, look.get("face") or {}
    marks = look.get("marks") or {}
    paper = hexcol(ink.get("ground", "FFFFFF"))
    t = {
        "name": look.get("name", "look"),
        "face": face.get("name") or "Arial",
        "weight": int(face.get("weight") or 400),
        "title_weight": int(face.get("title_weight") or face.get("weight") or 400),
        "paper": paper,
        "paper2": hexcol(ink.get("raised", "F2F2F2")),
        "ink": hexcol(ink.get("ink", "1A1C1F")),
        "muted": hexcol(ink.get("second", "6A6B6D")),
        "rule": hexcol(ink.get("hairline", "E3E3E4")),
        "accent": hexcol(marks.get("highlight") or ink.get("ink", "1A1C1F")),
        "corner": 6,
    }
    t["soft"] = t["muted"]
    t["accent_tint"] = mix(t["accent"], paper, 0.08)
    # Node treatments (style-guide.md, Node type -> treatment), flattened onto the paper.
    t["treat"] = {
        "focal": (t["accent_tint"], t["accent"], ""),
        "step": ("#FFFFFF" if paper == "#FFFFFF" else mix("#FFFFFF", paper, 0.7), t["ink"], ""),
        "store": (mix(t["ink"], paper, 0.05), t["muted"], ""),
        "external": (mix(t["ink"], paper, 0.03), mix(t["ink"], paper, 0.45), ""),
        "input": (mix(t["muted"], paper, 0.10), t["muted"], ""),
        "optional": (mix(t["ink"], paper, 0.02), mix(t["ink"], paper, 0.45), "4,3"),
        "approval": (mix(t["accent"], paper, 0.05), mix(t["accent"], paper, 0.6), "4,4"),
    }
    t["family"] = "'%s', 'Helvetica Neue', Helvetica, Arial, sans-serif" % t["face"].replace("'", "")
    return t


# ---- text ---------------------------------------------------------------------------------------------------------

def is_wide(ch):
    o = ord(ch)
    return (0x1100 <= o <= 0x115F or 0x2E80 <= o <= 0xA4CF or 0xAC00 <= o <= 0xD7A3 or 0xF900 <= o <= 0xFAFF
            or 0xFE30 <= o <= 0xFE4F or 0xFF00 <= o <= 0xFF60 or 0xFFE0 <= o <= 0xFFE6)


def text_width(text, size, em=SANS_EM, tracking=0.0):
    """The style guide's width budget: a wide character 1 em, every other its face's Latin advance."""
    return sum((WIDE_EM if is_wide(c) else em) * size + tracking * size for c in str(text))


def wrap(text, size, width, lines=2):
    """Words into at most `lines` lines no wider than width, balanced so no word is left alone on the last line;
    None when they do not fit."""
    out = greedy(text, size, width, lines)
    if not out or len(out) < 2:
        return out
    best, w = out, width
    while w > 0:
        w -= 4
        trial = greedy(text, size, w, lines)
        if not trial or len(trial) != len(out):
            break
        best = trial
    return best


def greedy(text, size, width, lines=2):
    words, out, line = str(text).split(), [], ""
    for w in words:
        trial = (line + " " + w).strip()
        if text_width(trial, size) <= width:
            line = trial
            continue
        if line:
            out.append(line)
        line = w
        if text_width(w, size) > width:
            return None
    if line:
        out.append(line)
    return out if len(out) <= lines else None


def esc(s):
    return html.escape(str(s), quote=True)


def g4(v):
    """Up to the next multiple of 4 (the grid)."""
    return int(math.ceil(v / 4.0) * 4)


# ---- the drawing --------------------------------------------------------------------------------------------------

class Canvas:
    """Arrows first, then labels, then nodes: the paint order every type reference assumes."""

    def __init__(self, t, slug):
        self.t, self.slug = t, slug
        self.zones, self.arrows, self.labels, self.nodes, self.top = [], [], [], [], []
        self.focal = 0
        self.used = set()
        self.boxes = []          # node rectangles (x0, y0, x1, y1): no label plate may sit on one
        self.rules = []          # lane rules (x0, y, x1): nor on one of these
        self.segs = []           # every connector leg, for crossings and for plates
        self.pending = []        # labels placed once every connector is drawn

    def text(self, x, y, s, size, fill=None, anchor="middle", weight=None, tracking=0.0, upper=False, klass=""):
        s = s.upper() if upper else s
        attrs = ' class="%s"' % klass if klass else ""
        track = ' letter-spacing="%gem"' % tracking if tracking else ""
        return ('<text x="%g" y="%g" fill="%s" font-size="%g" font-weight="%d" text-anchor="%s"%s%s>%s</text>'
                % (x, y, fill or self.t["ink"], size, weight or self.t["weight"], anchor, track, attrs, esc(s)))

    def node(self, x, y, w, h, name, sub="", kind="step", shape="rect", tag="", klass="node", data=""):
        fill, stroke, dash = self.t["treat"].get(kind, self.t["treat"]["step"])
        self.used.add(kind)
        if kind == "focal":
            self.focal += 1
        rx = {"rect": self.t["corner"], "oval": min(h / 2, 32)}.get(shape, self.t["corner"])
        d = ' stroke-dasharray="%s"' % dash if dash else ""
        cls = klass + (" focal" if kind == "focal" else "")
        self.boxes.append((x, y, x + w, y + h))
        parts = ['<g class="%s"%s>' % (cls, data)]
        if shape == "diamond":
            cx, cy = x + w / 2, y + h / 2
            pts = "%g,%g %g,%g %g,%g %g,%g" % (cx, y, x + w, cy, cx, y + h, x, cy)
            parts.append('<polygon points="%s" fill="%s"/>' % (pts, self.t["paper"]))
            parts.append('<polygon points="%s" fill="%s" stroke="%s" stroke-width="%g"%s/>'
                         % (pts, fill, stroke, 1.5 if kind == "focal" else 1, d))
            inner = w * 0.62
        else:
            parts.append('<rect x="%g" y="%g" width="%g" height="%g" rx="%g" fill="%s"/>'
                         % (x, y, w, h, rx, self.t["paper"]))
            parts.append('<rect x="%g" y="%g" width="%g" height="%g" rx="%g" fill="%s" stroke="%s" stroke-width="%g"%s/>'
                         % (x, y, w, h, rx, fill, stroke, 1.5 if kind == "focal" else 1, d))
            inner = w - 24
        size = RAMP["name"]
        name_lines = wrap(name, size, inner, 2)
        if name_lines is None:
            raise DiagramError("the name %r does not fit a box %d wide in two lines: shorten it" % (name, w))
        sub_lines = wrap(sub, RAMP["sub"], inner, 2) if sub else []
        if sub and sub_lines is None:
            raise DiagramError("the line under %r (%r) does not fit its box in two lines: shorten it" % (name, sub))
        block = len(name_lines) * (size + 4) + (len(sub_lines) * (RAMP["sub"] + 4) + 4 if sub_lines else 0)
        ty = y + (h - block) / 2 + size - 2
        name_fill = self.t["accent"] if kind == "focal" else self.t["ink"]
        for line in name_lines:
            parts.append(self.text(x + w / 2, ty, line, size, name_fill, weight=self.t["title_weight"]))
            ty += size + 4
        ty += 4
        for line in sub_lines:
            parts.append(self.text(x + w / 2, ty - 2, line, RAMP["sub"], self.t["muted"]))
            ty += RAMP["sub"] + 4
        if tag:
            tw = g4(text_width(tag, 9, tracking=0.08) + 12)
            parts.append('<rect x="%g" y="%g" width="%g" height="14" rx="2" fill="none" stroke="%s" stroke-width="0.8"/>'
                         % (x + 8, y + 6, tw, mix(stroke, self.t["paper"], 0.4)))
            parts.append(self.text(x + 8 + tw / 2, y + 16, tag, 9, self.t["muted"], tracking=0.08, upper=True))
        parts.append("</g>")
        self.nodes.append("".join(parts))

    def arrow(self, points, label="", accent=False, dashed=False, head=True):
        """An orthogonal connector through `points`, each bend a quarter arc of r 8 (smaller only where a leg is
        shorter), and its label on a plate beside its longest leg."""
        pts = [points[0]]
        for p in points[1:]:
            if p != pts[-1]:
                pts.append(p)
        i = 1
        while i < len(pts) - 1:                     # a point on a straight run is no bend
            (ax, ay), (bx, by), (cx, cy) = pts[i - 1], pts[i], pts[i + 1]
            if (ax == bx == cx) or (ay == by == cy):
                del pts[i]
            else:
                i += 1
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            if x1 != x2 and y1 != y2:
                raise AssertionError("diagonal leg %s -> %s" % ((x1, y1), (x2, y2)))
        d = "M%g,%g" % pts[0]
        for i in range(1, len(pts) - 1):
            (ax, ay), (bx, by), (cx, cy) = pts[i - 1], pts[i], pts[i + 1]
            l1, l2 = abs(bx - ax) + abs(by - ay), abs(cx - bx) + abs(cy - by)
            r = min(8, l1 / 2, l2 / 2)
            sx = bx - r * (1 if bx > ax else -1 if bx < ax else 0)
            sy = by - r * (1 if by > ay else -1 if by < ay else 0)
            ex = bx + r * (1 if cx > bx else -1 if cx < bx else 0)
            ey = by + r * (1 if cy > by else -1 if cy < by else 0)
            sweep = 1 if ((bx - ax) * (cy - by) - (by - ay) * (cx - bx)) > 0 else 0
            d += " L%g,%g A%g,%g 0 0 %d %g,%g" % (sx, sy, r, r, sweep, ex, ey)
        d += " L%g,%g" % pts[-1]
        colour = self.t["accent"] if accent else self.t["muted"]
        marker = ' marker-end="url(#%s-arrow%s)"' % (self.slug, "-accent" if accent else "") if head else ""
        dash = ' stroke-dasharray="5,4"' if dashed else ""
        self.arrows.append('<path class="connector%s" d="%s" fill="none" stroke="%s" stroke-width="%g"%s%s/>'
                           % (" focal" if accent else "", d, colour, 1.5 if accent else 1.2, dash, marker))
        if accent:
            self.focal += 1
        self.segs += [(a, b, len(self.arrows)) for a, b in zip(pts, pts[1:])]
        if label:
            self.pending.append((pts, label, len(self.arrows)))

    def finish(self):
        for pts, label, owner in self.pending:
            self.arrow_label(pts, label, owner)

    def free(self, box, owner):
        x0, y0, x1, y1 = box
        hit = lambda b, m=4: x0 < b[2] + m and b[0] - m < x1 and y0 < b[3] + m and b[1] - m < y1
        if any(hit(b) for b in self.boxes) or any(hit(b, 2) for b in getattr(self, "plates", [])):
            return False
        if any(x0 < r[2] and r[0] < x1 and y0 - 2 < r[1] < y1 + 2 for r in self.rules):
            return False
        for a, b, who in self.segs:                 # never over another connector (its own legs are 8 px off)
            sx0, sx1, sy0, sy1 = min(a[0], b[0]), max(a[0], b[0]), min(a[1], b[1]), max(a[1], b[1])
            if x0 - 2 < sx1 and sx0 < x1 + 2 and y0 - 2 < sy1 and sy0 < y1 + 2:
                return False
        return x0 >= 4 and y0 >= 4

    def arrow_label(self, pts, label, owner=None):
        label = label.strip().upper()
        if len(label) > ARROW_LABEL_MAX:
            raise DiagramError("the arrow label %r is longer than %d characters: say it in fewer words"
                               % (label, ARROW_LABEL_MAX))
        size = RAMP["arrow"]
        w = g4(text_width(label, size, tracking=0.06) + 12)
        h = 14                                 # the source's mask plate: 8 to 14 tall (verify-geometry.py)
        legs = sorted(((abs(b[0] - a[0]) + abs(b[1] - a[1]), a, b) for a, b in zip(pts, pts[1:])),
                      key=lambda l: -l[0])
        tries = []
        for length, a, b in legs:
            for f in (0.5, 0.33, 0.67, 0.2, 0.8):
                if a[1] == b[1] and length >= w + 16:      # horizontal leg: above, else below, 8 px clear
                    mx = a[0] + (b[0] - a[0]) * f
                    tries += [(mx - w / 2, a[1] - 8 - h), (mx - w / 2, a[1] + 8)]
                elif a[0] == b[0] and length >= h + 16:    # vertical leg: right, else left, 8 px clear
                    my = a[1] + (b[1] - a[1]) * f
                    tries += [(a[0] + 8, my - h / 2), (a[0] - 8 - w, my - h / 2)]
        if not tries:
            _, a, b = legs[0]
            tries = [((a[0] + b[0]) / 2 - w / 2, a[1] - 8 - h)] if a[1] == b[1] else [(a[0] + 8, (a[1] + b[1]) / 2 - h / 2)]
        segs = self.segs
        self.segs = [sg for sg in segs if sg[2] != owner]
        x, y = next((t_ for t_ in tries if self.free((t_[0], t_[1], t_[0] + w, t_[1] + h), owner)), tries[0])
        self.segs = segs
        self.plates = getattr(self, "plates", []) + [(x, y, x + w, y + h)]
        self.labels.append('<rect class="label-mask" x="%g" y="%g" width="%g" height="%g" rx="2" fill="%s"/>'
                           % (x, y, w, h, self.t["paper"]))
        self.labels.append(self.text(x + w / 2, y + h - 2.5, label, size, self.t["muted"], tracking=0.06,
                                     klass="arrow-label"))


def svg_document(c, width, height, title, desc, kind, legend, note):
    """The <svg>: title first, then defs, the paper, zones, arrows, labels, nodes; the legend strip under it."""
    t, slug = c.t, c.slug
    c.finish()
    legend_h = 0
    strip = []
    if legend:
        y = height + 12
        strip.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="0.8"/>'
                     % (MARGIN, y, width - MARGIN, y, t["rule"]))
        x = MARGIN
        for item in legend:
            fill, stroke, dash = t["treat"].get(item["kind"], t["treat"]["step"])
            d = ' stroke-dasharray="%s"' % dash if dash else ""
            strip.append('<rect x="%d" y="%d" width="16" height="12" rx="3" fill="%s" stroke="%s"%s/>'
                         % (x, y + 20, fill, stroke, d))
            strip.append(c.text(x + 24, y + 30, item["label"], RAMP["eyebrow"] + 1, t["muted"], anchor="start",
                                klass="legend"))
            x += g4(24 + text_width(item["label"], RAMP["eyebrow"] + 1) + 32)
        if x > width - MARGIN + 32:
            raise DiagramError("the legend is wider than the drawing: use fewer or shorter legend entries")
        legend_h = 48
    total_h = g4(height + legend_h + (MARGIN if legend else 0))
    out = ['<svg class="diagram" data-diagram-type="%s" viewBox="0 0 %d %d" width="%d" height="%d" '
           'xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="%s-title %s-desc" '
           'font-family="%s">' % (kind, width, total_h, width, total_h, slug, slug, esc(t["family"])),
           '<title id="%s-title">%s</title>' % (slug, esc(title)),
           '<desc id="%s-desc">%s</desc>' % (slug, esc(desc)),
           "<defs>",
           '<marker id="%s-arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">'
           '<polygon points="0 0, 8 3, 0 6" fill="%s"/></marker>' % (slug, t["muted"]),
           '<marker id="%s-arrow-accent" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">'
           '<polygon points="0 0, 8 3, 0 6" fill="%s"/></marker>' % (slug, t["accent"]),
           "</defs>",
           '<rect width="100%%" height="100%%" fill="%s"/>' % t["paper"]]
    out += c.zones + c.arrows + c.labels + c.nodes + c.top + strip
    out.append("</svg>")
    return "\n".join(out), total_h


# ---- layouts ------------------------------------------------------------------------------------------------------

def ids_of(items, what):
    seen = {}
    for i, item in enumerate(items):
        key = str(item.get("id") or item.get("name") or "").strip()
        if not key:
            raise DiagramError("%s %d has no name" % (what, i + 1))
        if key in seen:
            raise DiagramError("two %ss share the id %r: give each its own" % (what, key))
        seen[key] = item
    return seen


def kind_of(item, default="step"):
    if item.get("focal"):
        return "focal"
    k = str(item.get("kind") or default)
    return k if k in ("step", "store", "external", "input", "optional", "approval", "focal") else default


def box_width(items, sub_key="note", lines=2, limit=None):
    """The narrowest allowed width every name fits on one line (up to 240), else in two lines, and every note
    in two lines."""
    for w in WIDTHS[:3]:
        if all(wrap(i.get("name", ""), RAMP["name"], w - 24, 1) is not None and
               (not i.get(sub_key) or wrap(i[sub_key], RAMP["sub"], w - 24, 2) is not None) for i in items):
            return w
    fits = []
    for w in WIDTHS:
        names = [wrap(i.get("name", ""), RAMP["name"], w - 24, lines) for i in items]
        if all(n is not None for n in names) and \
                all(not i.get(sub_key) or wrap(i[sub_key], RAMP["sub"], w - 24, 2) is not None for i in items):
            fits.append((sum(len(n) for n in names), w))
    # The fewest wrapped names, then the narrowest, among the widths that keep the drawing 1280 wide (a figure in
    # a deck or a document is scaled to its page; a wider drawing takes its type ramp down with it).
    inside = [f for f in fits if limit is None or f[1] <= limit]
    if inside or fits:
        return min(inside or fits)[1]
    raise DiagramError("a name or note does not fit even a box %d wide: shorten it" % WIDTHS[-1])


def box_height(items, w, sub_key="note"):
    h = NODE_MIN_H
    for i in items:
        n = len(wrap(i.get("name", ""), RAMP["name"], w - 24, 2) or [1])
        s = len(wrap(i[sub_key], RAMP["sub"], w - 24, 2) or []) if i.get(sub_key) else 0
        h = max(h, g4(28 + n * (RAMP["name"] + 4) + (s * (RAMP["sub"] + 4) + 4 if s else 0)))
    return h


def fan(lo, hi, n):
    """Attach points k of n along an edge from lo to hi: L * k / (N + 1) (primitives-core.md, rule 4)."""
    return [lo + (hi - lo) * k / (n + 1) for k in range(1, n + 1)]


def grid_links(d, steps):
    links = []
    for i, link in enumerate(d.get("links") or []):
        a, b = str(link.get("from", "")).strip(), str(link.get("to", "")).strip()
        if a not in steps or b not in steps:
            raise DiagramError("link %d goes from %r to %r, and %s is not a step" %
                               (i + 1, a, b, a if a not in steps else b))
        links.append(link)
    return links


def layout_flow(d, c):
    """Flowchart (type-flowchart.md): top to bottom in ranks; a step's rank is one under the deepest step that
    links to it, unless the data gives "row". Decisions are diamonds, start and end ovals."""
    steps = ids_of(d.get("steps") or [], "step")
    if not steps:
        raise DiagramError("a flowchart needs steps")
    links = grid_links(d, steps)
    if any(str(st.get("group") or "").strip() for st in steps.values()):
        return layout_flow_groups(d, c, steps, links)
    order = list(steps)
    rank = {k: 0 for k in order}
    forward = [l for l in links if order.index(l["to"]) > order.index(l["from"])]
    for _ in range(len(order)):
        for l in forward:
            rank[l["to"]] = max(rank[l["to"]], rank[l["from"]] + 1)
    for k, s in steps.items():
        if s.get("row") is not None:
            rank[k] = int(s["row"]) - 1
    rows = {}
    for k in order:
        rows.setdefault(rank[k], []).append(k)
    widest = max(len(r) for r in rows.values())
    w = box_width(steps.values(), limit=(WIDTH - 2 * MARGIN - 64 - (widest - 1) * GAP) / widest)
    h = box_height(steps.values(), w)
    pos = {}
    width_needed = max(len(r) for r in rows.values()) * (w + GAP) - GAP
    # Room on the right for links that go back up or skip a rank.
    side = sum(1 for l in links if rank[l["to"]] <= rank[l["from"]] or rank[l["to"]] - rank[l["from"]] > 1)
    canvas_w = max(WIDTH, g4(width_needed + 2 * MARGIN + side * 16 + (32 if side else 0)))
    gaps = {r: 0 for r in rows}
    for l in links:
        if rank[l["to"]] - rank[l["from"]] == 1:
            gaps[rank[l["from"]]] = gaps.get(rank[l["from"]], 0) + 1
    y = MARGIN
    row_y = {}
    for r in sorted(rows):
        row_y[r] = y
        y += h + max(GAP + 16, 24 + 16 * gaps.get(r, 0) + 24)
    for r, keys in rows.items():
        span = len(keys) * (w + GAP) - GAP
        x0 = (canvas_w - side * 16 - (32 if side else 0)) / 2 - span / 2
        for i, k in enumerate(keys):
            pos[k] = (g4(x0 + i * (w + GAP)), row_y[r])
    for k, s in steps.items():
        shape = {"decision": "diamond", "start": "oval", "end": "oval"}.get(str(s.get("shape") or ""), "rect")
        x, y0 = pos[k]
        c.node(x, y0, w, h, s.get("name", k), s.get("note", ""), kind_of(s), shape, klass="node step",
               data=' data-id="%s"' % esc(k))
    route_links(c, links, pos, w, h, rank, canvas_w, vertical=True)
    return canvas_w, y - max(GAP + 16, 0) + 8


def layout_flow_groups(d, c, steps, links):
    """A flowchart in groups (a floor, a site, a department): each group a column left to right under its name
    and a hairline, its steps top to bottom in ranks; a link inside a group goes to its next rank, a link between
    groups leaves a step's right edge for the next group's left edge, each in its own channel."""
    names = []
    for k, st in steps.items():
        g = str(st.get("group") or "").strip()
        if not g:
            raise DiagramError("step %r has no group: give every step a group, or none of them" % k)
        if g not in names:
            names.append(g)
    gi = {k: names.index(str(st["group"]).strip()) for k, st in steps.items()}
    for k in steps:                                   # a group's steps stand together, in the order of the groups
        if any(gi[o] > gi[k] for o in list(steps)[:list(steps).index(k)]):
            raise DiagramError("step %r is in group %r after a step of a later group: list each group's steps "
                               "together, groups in the order they are passed" % (k, steps[k]["group"]))
    inner = [l for l in links if gi[l["from"]] == gi[l["to"]]]
    cross = [l for l in links if gi[l["from"]] != gi[l["to"]]]
    for l in cross:
        if gi[l["to"]] != gi[l["from"]] + 1:
            raise DiagramError("the link from %r to %r goes from group %r to %r: a link between groups goes to the "
                               "next group on the right; reorder the groups or pass through a step between" %
                               (l["from"], l["to"], names[gi[l["from"]]], names[gi[l["to"]]]))
    order = list(steps)
    rank = {k: 0 for k in order}
    fed = {l["to"] for l in inner}
    # Down its column: a step one row under the step that links to it, and a step nothing in its group links to
    # one row under the step listed before it, so zones with no route between them still read top to bottom.
    before = {}
    for k in order:
        same = [o for o in order[:order.index(k)] if gi[o] == gi[k]]
        if same and k not in fed:
            before[k] = same[-1]
    for _ in range(len(order) + 1):
        for l in inner:
            if order.index(l["to"]) > order.index(l["from"]):
                rank[l["to"]] = max(rank[l["to"]], rank[l["from"]] + 1)
        for k, b in before.items():
            rank[k] = max(rank[k], rank[b] + 1)
    for k, st in steps.items():
        if st.get("row") is not None:
            rank[k] = int(st["row"]) - 1
    for l in inner:
        if rank[l["to"]] - rank[l["from"]] != 1:
            raise DiagramError("inside group %r the link from %r to %r skips or goes back a row: a link inside a "
                               "group goes to the next row; pin rows with \"row\" or split the step" %
                               (names[gi[l["from"]]], l["from"], l["to"]))
    rows = [{} for _ in names]
    for k in order:
        rows[gi[k]].setdefault(rank[k], []).append(k)
    cols = [max(len(r) for r in g.values()) for g in rows]
    ncross = [sum(1 for l in cross if gi[l["from"]] == i) for i in range(len(names))]
    gaps = [max(64, 48 + 16 * ncross[i]) for i in range(len(names) - 1)]
    w = box_width(steps.values(), limit=(WIDTH - 2 * MARGIN - sum(gaps) - sum(n - 1 for n in cols) * GAP) / sum(cols))
    for name, n in zip(names, cols):
        if text_width(name.upper(), RAMP["eyebrow"], tracking=0.14) > n * (w + GAP) - GAP:
            raise DiagramError("the group name %r is wider than its column: shorten it" % name)
    h = box_height(steps.values(), w)
    spans = [n * (w + GAP) - GAP for n in cols]
    total = sum(spans) + sum(gaps)
    canvas_w = max(WIDTH, g4(total + 2 * MARGIN))
    gx, x = [], (canvas_w - total) / 2
    for i, sp in enumerate(spans):
        gx.append(g4(x))
        x += sp + (gaps[i] if i < len(gaps) else 0)
    down = {}
    for l in inner:
        down[rank[l["from"]]] = down.get(rank[l["from"]], 0) + 1
    top = MARGIN + 44
    row_y, y = {}, top
    step = h + max([GAP + 16] + [24 + 16 * n + 24 for n in down.values()])   # one even rhythm down every column
    for r in range(max(rank.values()) + 1):
        row_y[r] = y
        y += step
    pos = {}
    for i, g in enumerate(rows):
        for r, keys in g.items():
            span = len(keys) * (w + GAP) - GAP
            x0 = gx[i] + (spans[i] - span) / 2
            for j, k in enumerate(keys):
                pos[k] = (g4(x0 + j * (w + GAP)), row_y[r])
    for i, name in enumerate(names):
        x0, x1 = gx[i], gx[i] + spans[i]
        c.zones.append('<g class="group">%s</g>' % c.text((x0 + x1) / 2, MARGIN + 14, name, RAMP["eyebrow"],
                                                           c.t["muted"], tracking=0.14, upper=True))
        c.zones.append('<line class="group-rule" x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="1"/>'
                       % (x0, MARGIN + 24, x1, MARGIN + 24, c.t["rule"]))
        c.rules.append((x0, MARGIN + 24, x1))
    for k, st in steps.items():
        shape = {"decision": "diamond", "start": "oval", "end": "oval"}.get(str(st.get("shape") or ""), "rect")
        x, y0 = pos[k]
        c.node(x, y0, w, h, st.get("name", k), st.get("note", ""), kind_of(st), shape, klass="node step",
               data=' data-id="%s" data-group="%s"' % (esc(k), esc(names[gi[k]])))
    route_links(c, inner, pos, w, h, rank, canvas_w, vertical=True)
    outs, ins = {}, {}
    for l in cross:
        outs.setdefault(l["from"], []).append(l)
        ins.setdefault(l["to"], []).append(l)
    for k in outs:
        outs[k].sort(key=lambda l: pos[l["to"]][1])
    for k in ins:
        ins[k].sort(key=lambda l: pos[l["from"]][1])

    def make(l, n):
        (sx, sy), (tx, ty) = pos[l["from"]], pos[l["to"]]
        ya = fan(sy, sy + h, len(outs[l["from"]]))[outs[l["from"]].index(l)]
        yb = fan(ty, ty + h, len(ins[l["to"]]))[ins[l["to"]].index(l)]
        if abs(ya - yb) < 0.5:
            return [(sx + w, ya), (tx, yb)]
        mid = gx[gi[l["from"]]] + spans[gi[l["from"]]] + 24 + 16 * n
        return [(sx + w, ya), (mid, ya), (mid, yb), (tx, yb)]
    groups = {}
    for l in cross:
        groups.setdefault(gi[l["from"]], []).append(l)
    routes = assign_channels(groups, make)
    for l in cross:
        c.arrow(routes[id(l)], l.get("label", ""), accent=bool(l.get("focal")), dashed=bool(l.get("dashed")))
    return canvas_w, y - step + h + 8


def crossings(paths):
    """How often the legs of different routes cross or run on one another (primitives-core.md, rule 3)."""
    legs = [(i, a, b) for i, pts in enumerate(paths) for a, b in zip(pts, pts[1:])]
    n = 0
    for k, (i, a, b) in enumerate(legs):
        for j, c, d in legs[k + 1:]:
            if i == j:
                continue
            ah, ch = a[1] == b[1], c[1] == d[1]
            if ah != ch:
                h, v = ((a, b), (c, d)) if ah else ((c, d), (a, b))
                if min(h[0][0], h[1][0]) < v[0][0] < max(h[0][0], h[1][0]) and \
                        min(v[0][1], v[1][1]) < h[0][1] < max(v[0][1], v[1][1]):
                    n += 1
            elif ah and abs(a[1] - c[1]) < 12:
                if min(max(a[0], b[0]), max(c[0], d[0])) - max(min(a[0], b[0]), min(c[0], d[0])) > 1:
                    n += 3
            elif not ah and abs(a[0] - c[0]) < 12:
                if min(max(a[1], b[1]), max(c[1], d[1])) - max(min(a[1], b[1]), min(c[1], d[1])) > 1:
                    n += 3
    return n


def assign_channels(groups, make, drawn=()):
    """For each gap, the order of its routes' channels that crosses least, with the routes already chosen."""
    from itertools import permutations
    chosen, out = list(drawn), {}
    for key in sorted(groups):
        ls = groups[key]
        best, score = None, None
        orders = permutations(range(len(ls))) if len(ls) <= 6 else [tuple(range(len(ls)))]
        for order in orders:
            paths = [make(l, n) for l, n in zip(ls, order)]
            sc = crossings(paths + chosen)
            if score is None or sc < score:
                best, score = paths, sc
        for l, pts in zip(ls, best):
            out[id(l)] = pts
        chosen += best
    return out


def route_links(c, links, pos, w, h, rank, canvas_w, vertical):
    """Orthogonal routes: next rank through the gap between ranks, each link in its own channel 16 px apart;
    a link that stays in its rank, goes back or skips a rank takes a corridor beside the drawing."""
    out_edges, in_edges = {}, {}
    near = [l for l in links if rank[l["to"]] - rank[l["from"]] == 1]
    far = [l for l in links if l not in near]
    for l in near:
        out_edges.setdefault(l["from"], []).append(l)
        in_edges.setdefault(l["to"], []).append(l)
    port_out, port_in = {}, {}
    for k, ls in out_edges.items():
        ls.sort(key=lambda l: pos[l["to"]][0 if vertical else 1])
        x, y = pos[k]
        pts = fan(x, x + w, len(ls)) if vertical else fan(y, y + h, len(ls))
        for l, p in zip(ls, pts):
            port_out[id(l)] = p
    for k, ls in in_edges.items():
        ls.sort(key=lambda l: pos[l["from"]][0 if vertical else 1])
        x, y = pos[k]
        pts = fan(x, x + w, len(ls)) if vertical else fan(y, y + h, len(ls))
        for l, p in zip(ls, pts):
            port_in[id(l)] = p
    def make(l, n):
        (sx, sy), (tx, ty) = pos[l["from"]], pos[l["to"]]
        a, b = port_out[id(l)], port_in[id(l)]
        if vertical:
            y1, y2 = sy + h, ty
            mid = y1 + 24 + 16 * n
            return [(a, y1), (a, mid), (b, mid), (b, y2)] if abs(a - b) > 0.5 else [(a, y1), (a, y2)]
        x1, x2 = sx + w, tx
        mid = x1 + 20 + 16 * n
        return [(x1, a), (mid, a), (mid, b), (x2, b)] if abs(a - b) > 0.5 else [(x1, a), (x2, a)]
    groups = {}
    for l in near:
        groups.setdefault(rank[l["from"]], []).append(l)
    routes = assign_channels(groups, make)
    for l in near:
        c.arrow(routes[id(l)], l.get("label", ""), accent=bool(l.get("focal")), dashed=bool(l.get("dashed")))
    right = max(p[0] for p in pos.values()) + w
    bottom = max(p[1] for p in pos.values()) + h
    side_out, side_in = {}, {}
    for l in far:
        side_out.setdefault(l["from"], []).append(l)
        side_in.setdefault(l["to"], []).append(l)
    for i, l in enumerate(far):
        (sx, sy), (tx, ty) = pos[l["from"]], pos[l["to"]]
        if vertical:
            lane = right + 32 + 16 * i
            so = side_out[l["from"]]
            si = side_in[l["to"]]
            ya = fan(sy, sy + h, len(so))[so.index(l)]
            yb = fan(ty, ty + h, len(si))[si.index(l)]
            pts = [(sx + w, ya), (lane, ya), (lane, yb), (tx + w, yb)]
        else:
            lane = bottom + 24 + 16 * i
            so = side_out[l["from"]]
            si = side_in[l["to"]]
            xa = fan(sx, sx + w, len(so))[so.index(l)]
            xb = fan(tx, tx + w, len(si))[si.index(l)]
            pts = [(xa, sy + h), (xa, lane), (xb, lane), (xb, ty + h)]
        c.arrow(pts, l.get("label", ""), accent=bool(l.get("focal")), dashed=bool(l.get("dashed", True)))


def layout_swimlane(d, c):
    """Swimlane (type-swimlane.md): one lane per person or team, left to right; each step in its owner's lane,
    its column from "col" or one after the step that hands to it; handoffs are the links between lanes."""
    lanes = [str(l.get("name") if isinstance(l, dict) else l).strip() for l in d.get("lanes") or []]
    if not lanes:
        raise DiagramError("a swimlane needs lanes: one per person or team")
    steps = ids_of(d.get("steps") or [], "step")
    for k, s in steps.items():
        if str(s.get("lane", "")).strip() not in lanes:
            raise DiagramError("step %r is in lane %r, which is not one of the lanes %s" % (k, s.get("lane"), lanes))
    links = grid_links(d, steps)
    order = list(steps)
    col = {k: 0 for k in order}
    for _ in range(len(order)):
        for l in links:
            if order.index(l["to"]) > order.index(l["from"]):
                col[l["to"]] = max(col[l["to"]], col[l["from"]] + 1)
    for k, s in steps.items():
        if s.get("col") is not None:
            col[k] = int(s["col"]) - 1
    for k in order:                                   # one step per lane and column: push later ones right
        while any(o != k and col[o] == col[k] and steps[o]["lane"] == steps[k]["lane"] for o in order[:order.index(k)]):
            col[k] += 1
    label_w = g4(max(text_width(l, RAMP["eyebrow"], tracking=0.14) for l in lanes) + 32)
    label_w = max(label_w, 120)
    ncols = max(col.values()) + 1
    w = box_width(steps.values(), limit=(WIDTH - 2 * MARGIN - label_w - 24 - (ncols - 1) * 56) / ncols)
    h = box_height(steps.values(), w)
    hand = {}
    for l in links:
        hand[col[l["from"]]] = hand.get(col[l["from"]], 0) + 1
    xs, x = [], MARGIN + label_w + 24
    for i in range(ncols):
        xs.append(g4(x))
        x += w + max(GAP + 8, 20 + 16 * hand.get(i, 0) + 20)
    canvas_w = max(WIDTH, g4(x - GAP + MARGIN))
    lane_h = h + 48
    pos = {}
    for k, s in steps.items():
        li = lanes.index(s["lane"])
        pos[k] = (xs[col[k]], MARGIN + li * lane_h + 24)
    for i, name in enumerate(lanes):
        y0 = MARGIN + i * lane_h
        if i:
            c.rules.append((MARGIN, y0, canvas_w - MARGIN))
            c.zones.append('<line class="lane-rule" x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="1"/>'
                           % (MARGIN, y0, canvas_w - MARGIN, y0, c.t["rule"]))
        c.zones.append('<g class="lane">%s</g>' % c.text(MARGIN, y0 + lane_h / 2 + 4, name, RAMP["eyebrow"],
                                                           c.t["muted"], anchor="start", tracking=0.14, upper=True))
    for k, s in steps.items():
        x, y0 = pos[k]
        c.node(x, y0, w, h, s.get("name", k), s.get("note", ""), kind_of(s), klass="node step",
               data=' data-id="%s"' % esc(k))
    rank = {k: col[k] for k in order}
    route_lanes(c, links, pos, w, h, rank, steps)
    return canvas_w, MARGIN + len(lanes) * lane_h


def route_lanes(c, links, pos, w, h, col, steps):
    """A handoff leaves its step's right edge, turns in the gap after that column (its own channel) and enters
    the next step's left edge; within one lane and the next column it runs straight."""
    outs, ins = {}, {}
    for l in links:
        outs.setdefault(l["from"], []).append(l)
        ins.setdefault(l["to"], []).append(l)
    for k in outs:
        outs[k].sort(key=lambda l: pos[l["to"]][1])
    for k in ins:
        ins[k].sort(key=lambda l: pos[l["from"]][1])
    for l in links:
        if col[l["to"]] <= col[l["from"]]:
            raise DiagramError("the step %r hands back to %r in an earlier column: give the step it hands to a "
                               "later \"col\", so the flow reads left to right" % (l["from"], l["to"]))

    def make(l, n):
        (sx, sy), (tx, ty) = pos[l["from"]], pos[l["to"]]
        ya = fan(sy, sy + h, len(outs[l["from"]]))[outs[l["from"]].index(l)]
        yb = fan(ty, ty + h, len(ins[l["to"]]))[ins[l["to"]].index(l)]
        if abs(ya - yb) < 0.5 and col[l["to"]] - col[l["from"]] == 1:
            return [(sx + w, ya), (tx, yb)]
        mid = sx + w + 20 + 16 * n
        return [(sx + w, ya), (mid, ya), (mid, yb), (tx, yb)]
    groups = {}
    for l in links:
        groups.setdefault(col[l["from"]], []).append(l)
    routes = assign_channels(groups, make)
    for l in links:
        c.arrow(routes[id(l)], l.get("label", ""), accent=bool(l.get("focal")), dashed=bool(l.get("dashed")))

def layout_org(d, c):
    """Org chart (type-org-chart.md): the root at top centre, a vertical drop to a horizontal bus, drops to the
    children; leaves side by side, each parent centred over its children."""
    people = ids_of(d.get("people") or d.get("nodes") or [], "person")
    roots = [k for k, p in people.items() if not p.get("reports_to")]
    if len(roots) != 1:
        raise DiagramError("an org chart has one top: %d people report to nobody (%s)" %
                           (len(roots), ", ".join(roots) or "none"))
    kids = {k: [] for k in people}
    for k, p in people.items():
        boss = p.get("reports_to")
        if boss:
            if boss not in people:
                raise DiagramError("%r reports to %r, who is not in the chart" % (k, boss))
            kids[boss].append(k)
    depth = {}

    def walk(k, dpt, seen=()):
        if k in seen:
            raise DiagramError("%r reports to itself through %s" % (k, " -> ".join(seen)))
        depth[k] = dpt
        for ch in kids[k]:
            walk(ch, dpt + 1, seen + (k,))
    walk(roots[0], 0)
    leaves = sum(1 for k in people if not kids[k])
    w = box_width(people.values(), "role", limit=(WIDTH - 2 * MARGIN - (leaves - 1) * 24) / max(1, leaves))
    h = box_height(people.values(), w, "role")
    slot = w + 24
    xs = {}
    cursor = [MARGIN]

    def place(k):
        if not kids[k]:
            xs[k] = cursor[0]
            cursor[0] += slot
            return
        for ch in kids[k]:
            place(ch)
        xs[k] = (xs[kids[k][0]] + xs[kids[k][-1]]) / 2
    place(roots[0])
    span = cursor[0] - 24 - MARGIN
    canvas_w = max(WIDTH, g4(span + 2 * MARGIN))
    shift = (canvas_w - span) / 2 - MARGIN
    tier = h + 64
    pos = {k: (g4(xs[k] + shift) if not kids[k] else xs[k] + shift, MARGIN + depth[k] * tier) for k in people}
    def line(x1, y1, x2, y2, dash=False):
        c.arrows.append('<line class="reports" x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-width="1.2"%s/>'
                        % (x1, y1, x2, y2, c.t["muted"], ' stroke-dasharray="5,4"' if dash else ""))
    for k, ch in kids.items():
        if not ch:
            continue
        px, py = pos[k]
        mid, bus = px + w / 2, py + h + 32
        cy = pos[ch[0]][1]
        drops = sorted((pos[child][0] + w / 2, people[child].get("kind") == "optional") for child in ch)
        lo, hi = drops[0][0], drops[-1][0]
        if len(ch) == 1 and abs(lo - mid) < 0.5:
            line(mid, py + h, mid, cy, drops[0][1])
            continue
        # One trunk, one bus with rounded ends, a drop for each child between them (type-org-chart.md).
        line(mid, py + h, mid, bus)
        if len(ch) == 1:
            c.arrow([(mid, bus), (lo, bus), (lo, cy)], head=False, dashed=drops[0][1])
            continue
        c.arrows.append('<path class="reports" d="M%g,%g L%g,%g A8,8 0 0 1 %g,%g L%g,%g A8,8 0 0 1 %g,%g L%g,%g" '
                        'fill="none" stroke="%s" stroke-width="1.2"/>'
                        % (lo, cy, lo, bus + 8, lo + 8, bus, hi - 8, bus, hi, bus + 8, hi, cy, c.t["muted"]))
        for x, dash in drops[1:-1]:
            line(x, bus, x, cy, dash)
    for k, p in people.items():
        x, y0 = pos[k]
        c.node(x, y0, w, h, p.get("name", k), p.get("role", ""), kind_of(p), klass="node person",
               data=' data-id="%s" data-depth="%d" data-reports="%d"' % (esc(k), depth[k] + 1, len(kids[k])))
    return canvas_w, MARGIN + (max(depth.values()) + 1) * tier - 64 + 8


def parse_when(value, what):
    s = str(value or "").strip()
    for fmt, n in (("%Y-%m-%d", 10), ("%Y-%m", 7), ("%Y", 4)):
        try:
            return dt.datetime.strptime(s[:n], fmt).date() if len(s) >= n else None
        except ValueError:
            continue
    raise DiagramError("%s has the date %r: write it as 2026-11-03, 2026-11 or 2026" % (what, s))


def month_ticks(lo, hi):
    """Tick dates on Mondays for a span under ten weeks (step 0), else on month, quarter or year boundaries,
    whichever gives 4 to 14 ticks; the axis ends on the tick after the last date, so nothing sits on the edge."""
    if (hi - lo).days < 70:
        day = lo - dt.timedelta(days=lo.weekday())
        ticks = [day]
        while ticks[-1] <= hi:
            ticks.append(ticks[-1] + dt.timedelta(days=7))
        return ticks, 0
    months = (hi.year - lo.year) * 12 + hi.month - lo.month + 1
    step = 1 if months <= 14 else 3 if months <= 42 else 12
    y, m = lo.year, lo.month
    m = m - ((m - 1) % step)
    ticks = []
    while (y, m) <= (hi.year, hi.month):
        ticks.append(dt.date(y, m, 1))
        m += step
        while m > 12:
            m -= 12
            y += 1
    ticks.append(dt.date(y, m, 1))
    return ticks, step


MONTHS = {"en": "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec",
          "sv": "jan feb mar apr maj jun jul aug sep okt nov dec",
          "nb": "jan feb mar apr mai jun jul aug sep okt nov des",
          "da": "jan feb mar apr maj jun jul aug sep okt nov dec",
          "de": "Jan Feb Mär Apr Mai Jun Jul Aug Sep Okt Nov Dez",
          "fi": "tammi helmi maalis huhti touko kesä heinä elo syys loka marras joulu"}


def tick_label(day, step, lang, first=False):
    names = MONTHS.get(lang, MONTHS["en"]).split()
    if step == 0:                                    # weekly: the day and month, the year on the first tick
        return "%d %s%s" % (day.day, names[day.month - 1], " %d" % day.year if first or (day.month == 1 and
                                                                                         day.day <= 7) else "")
    if step == 12:
        return str(day.year)
    return "%s %d" % (names[day.month - 1], day.year) if day.month == 1 or first else names[day.month - 1]


def layout_timeline(d, c):
    """Timeline (type-timeline.md): a hairline baseline, ticks with dates under it, events as dots on an honest
    scale, labels alternating above and below on hairline drops; a milestone is the accent dot."""
    events = d.get("events") or []
    if not events:
        raise DiagramError("a timeline needs events, each with a date and a name")
    days = [parse_when(e.get("date"), "event %r" % e.get("name")) for e in events]
    lo, hi = min(days), max(days)
    ticks, step = month_ticks(lo, hi)
    t0, t1 = ticks[0], ticks[-1]
    x0, x1 = MARGIN + 24, WIDTH - MARGIN - 24
    scale = (x1 - x0) / max(1, (t1 - t0).days)
    xof = lambda day: x0 + (day - t0).days * scale
    lang = d.get("language", "en")
    placed = {1: [], -1: []}
    order = sorted(range(len(events)), key=lambda i: days[i])
    lw = 184
    plan = []
    for n, i in enumerate(order):
        e, x = events[i], xof(days[i])
        side = -1 if n % 2 == 0 else 1
        lines = wrap(e.get("name", ""), RAMP["sub"] + 2, lw - 8, 2)
        if lines is None:
            raise DiagramError("the event name %r does not fit two lines: shorten it" % e.get("name"))
        note = wrap(e.get("note", ""), RAMP["sub"], lw - 8, 2) if e.get("note") else []
        if e.get("note") and note is None:
            raise DiagramError("the note under %r does not fit two lines: shorten it" % e.get("name"))
        # Three tiers each side: an event whose label would touch the last one on its side steps out a tier.
        tier = 0
        while any(abs(x - px) < lw + 8 and pt == tier for px, pt in placed[side]) and tier < 2:
            tier += 1
        if any(abs(x - px) < lw + 8 and pt == tier for px, pt in placed[side]):
            raise DiagramError("too many events close together around %s: merge some, or split the timeline"
                               % e.get("date"))
        placed[side].append((x, tier))
        drop = 44 + tier * 52 if side < 0 else 52 + tier * 52
        plan.append((e, x, side, drop, lines, note or []))
    above = max([drop + (len(l) + len(nt) - 1) * 16 + 16 for _, _, sd, drop, l, nt in plan if sd < 0] or [24])
    below = max([drop + (len(l) + len(nt)) * 16 + 8 for _, _, sd, drop, l, nt in plan if sd > 0] or [40])
    base = g4(MARGIN + above)
    c.zones.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="1"/>'
                   % (x0, base, x1, base, c.t["ink"]))
    drops_below = [x for _, x, sd, _, _, _ in plan if sd > 0]
    for day in ticks:
        x = xof(day)
        c.zones.append('<line x1="%g" y1="%d" x2="%g" y2="%d" stroke="%s" stroke-width="1"/>'
                       % (x, base, x, base + 6, c.t["ink"]))
        label = tick_label(day, step, lang, day == ticks[0])
        half = text_width(label, RAMP["eyebrow"]) / 2 + 4
        if any(abs(x - dx) < half for dx in drops_below):
            continue                         # an event's drop runs through here: the tick keeps no label
        c.zones.append(c.text(x, base + 24, label, RAMP["eyebrow"], c.t["muted"], klass="tick"))
    for e, x, side, drop, lines, note in plan:
        focal = bool(e.get("focal") or e.get("milestone"))
        ly = base - drop if side < 0 else base + drop
        c.zones.append('<line x1="%g" y1="%d" x2="%g" y2="%g" stroke="%s" stroke-width="1"/>'
                       % (x, base, x, ly + (6 if side < 0 else -14), c.t["rule"] if not focal else c.t["accent"]))
        r = 6 if focal else 4
        c.nodes.append('<circle class="event%s" cx="%g" cy="%d" r="%d" fill="%s"/>'
                       % (" focal" if focal else "", x, base, r, c.t["accent"] if focal else c.t["ink"]))
        if focal:
            c.focal += 1
        anchor, tx = ("start", x - 4) if x < x0 + lw / 2 else ("end", x + 4) if x > x1 - lw / 2 else ("middle", x)
        ty = ly - (len(lines) + len(note) - 1) * 16 if side < 0 else ly + 4
        for line in lines:
            c.top.append(c.text(tx, ty, line, RAMP["sub"] + 2, c.t["accent"] if focal else c.t["ink"], anchor,
                                weight=c.t["title_weight"], klass="event-label"))
            ty += 16
        for line in note:
            c.top.append(c.text(tx, ty, line, RAMP["sub"], c.t["muted"], anchor, klass="event-note"))
            ty += 16
    return WIDTH, base + below + 8


def layout_gantt(d, c):
    """Gantt (type-gantt.md): a label column on the left, the time axis across the top, one row of 40 per task,
    each bar 24 high; phases as quiet zones with an eyebrow; one focal bar; a dashed marker for a milestone."""
    tasks = d.get("tasks") or []
    if not tasks:
        raise DiagramError("a gantt needs tasks, each with a name, a start and an end")
    spans = []
    for t_ in tasks:
        a = parse_when(t_.get("start"), "task %r" % t_.get("name"))
        b = parse_when(t_.get("end"), "task %r" % t_.get("name"))
        if len(str(t_.get("end", ""))) == 7:                       # 2026-11 ends at the month's end
            b = (dt.date(b.year + (b.month == 12), b.month % 12 + 1, 1) - dt.timedelta(days=1))
        if b < a:
            raise DiagramError("task %r ends (%s) before it starts (%s)" % (t_.get("name"), t_.get("end"), t_.get("start")))
        spans.append((a, b))
    markers = d.get("markers") or []
    mdays = [parse_when(m.get("date"), "marker %r" % m.get("name")) for m in markers]
    lo = min([a for a, _ in spans] + mdays)
    hi = max([b for _, b in spans] + mdays)
    ticks, step = month_ticks(lo, hi)
    label_w = 240
    for t_ in tasks:
        if wrap(t_.get("name", ""), RAMP["row"] + 2, label_w - 32, 1) is None:
            label_w = 320
    x0, x1 = MARGIN + label_w, WIDTH - MARGIN
    t0, t1 = ticks[0], ticks[-1]
    scale = (x1 - x0) / max(1, (t1 - t0).days)
    xof = lambda day: x0 + (day - t0).days * scale
    lang = d.get("language", "en")
    top = MARGIN + 40
    for day in ticks[:-1]:
        x = xof(day)
        c.zones.append(c.text(x + 4, top - 12, tick_label(day, step, lang, day == ticks[0]), RAMP["eyebrow"], c.t["muted"],
                              anchor="start", klass="tick"))
    for day in ticks:
        x = xof(day)
        c.zones.append('<line x1="%g" y1="%d" x2="%g" y2="%d" stroke="%s" stroke-width="0.8"/>'
                       % (x, top - 4, x, top + 8, c.t["rule"]))
    c.zones.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="1"/>'
                   % (MARGIN, top + 8, x1, top + 8, c.t["rule"]))
    y = top + 24
    phase_of = [str(t_.get("phase") or "").strip() for t_ in tasks]
    groups = []
    for i, p in enumerate(phase_of):
        if groups and groups[-1][0] == p:
            groups[-1][1].append(i)
        else:
            if p and any(g[0] == p for g in groups):
                raise DiagramError("the phase %r is split: put its tasks next to each other" % p)
            groups.append((p, [i]))
    if len(groups) > 1 and all(len(idx) == 1 for _, idx in groups):
        groups = [("", [i]) for _, [i] in groups]  # a phase per task only repeats the task: no phases drawn
    for p, idx in groups:
        if p:
            y += 24
            zh = 40 * len(idx) + 12
            c.zones.append('<rect class="phase" x="%d" y="%d" width="%d" height="%d" rx="6" fill="%s" stroke="%s" '
                           'stroke-width="0.8"/>' % (MARGIN - 8, y - 4, x1 - MARGIN + 16, zh,
                                                     mix(c.t["ink"], c.t["paper"], 0.02),
                                                     mix(c.t["ink"], c.t["paper"], 0.10)))
            c.zones.append(c.text(MARGIN, y - 10, p, RAMP["eyebrow"], c.t["muted"], anchor="start", tracking=0.14,
                                  upper=True, klass="phase-label"))
        for i in idx:
            t_, (a, b) = tasks[i], spans[i]
            focal = bool(t_.get("focal"))
            c.zones.append(c.text(MARGIN + 8, y + 25, t_.get("name", ""), RAMP["row"] + 2, c.t["ink"],
                                  anchor="start", weight=c.t["title_weight"], klass="task-label"))
            bx = xof(a)
            bw = max(8, xof(b + dt.timedelta(days=1)) - bx)
            fill = c.t["accent_tint"] if focal else mix(c.t["muted"], c.t["paper"], 0.15)
            stroke = c.t["accent"] if focal else c.t["muted"]
            c.nodes.append('<rect class="task%s" x="%g" y="%d" width="%g" height="24" rx="4" fill="%s" stroke="%s" '
                           'stroke-width="1"/>' % (" focal" if focal else "", bx, y + 8, bw, fill, stroke))
            if focal:
                c.focal += 1
            if t_.get("note"):
                nx = bx + bw + 8
                anchor = "start"
                if nx + text_width(t_["note"], RAMP["eyebrow"] + 1) > x1:
                    nx, anchor = bx - 8, "end"
                c.top.append(c.text(nx, y + 25, t_["note"], RAMP["eyebrow"] + 1, c.t["muted"], anchor,
                                    klass="task-note"))
            y += 40
        y += 12
    for m, day in zip(markers, mdays):
        x = xof(day)
        c.zones.append('<line class="marker" x1="%g" y1="%d" x2="%g" y2="%d" stroke="%s" stroke-width="1" '
                       'stroke-dasharray="5,4"/>' % (x, top + 8, x, y - 12, c.t["muted"]))
        c.top.append('<rect class="label-mask" x="%g" y="%d" width="%g" height="14" rx="2" fill="%s"/>'
                     % (x - g4(text_width(m.get("name", ""), RAMP["eyebrow"]) + 12) / 2, y - 8,
                        g4(text_width(m.get("name", ""), RAMP["eyebrow"]) + 12), c.t["paper"]))
        c.top.append(c.text(x, y + 3.5, m.get("name", ""), RAMP["eyebrow"], c.t["muted"], klass="marker-label"))
        y = y
    return WIDTH, y + 24


def layout_quadrant(d, c):
    """Quadrant (type-quadrant.md): a 2x2 with one word at each arrow tip, items as small labelled dots placed by
    their 0 to 1 scores, short tags in the corners; the accent on the one item to do first."""
    items = d.get("items") or []
    xa, ya = d.get("x") or {}, d.get("y") or {}
    if not items or not xa.get("name") or not ya.get("name"):
        raise DiagramError("a quadrant needs items and two axes, each with a name: \"x\": {\"name\": \"Effort\"}")
    for a in (xa, ya):
        if len(str(a["name"]).split()) > 1:
            raise DiagramError("an axis is named in one word (%r): the source's Jobs-minimal rule" % a["name"])
    size = 560
    x0 = (WIDTH - size) / 2
    y0 = MARGIN + 40
    cx, cy = x0 + size / 2, y0 + size / 2
    ink = c.t["ink"]
    c.zones.append('<rect x="%g" y="%g" width="%d" height="%d" fill="none" stroke="%s" stroke-width="0.8"/>'
                   % (x0, y0, size, size, c.t["rule"]))
    c.zones.append('<path d="M%g,%g L%g,%g" stroke="%s" stroke-width="1" marker-end="url(#%s-arrow)"/>'
                   % (x0, cy, x0 + size + 24, cy, ink, c.slug))
    c.zones.append('<path d="M%g,%g L%g,%g" stroke="%s" stroke-width="1" marker-end="url(#%s-arrow)"/>'
                   % (cx, y0 + size, cx, y0 - 24, ink, c.slug))
    c.zones.append(c.text(x0 + size + 36, cy + 4, xa["name"], RAMP["eyebrow"], ink, "start", tracking=0.18,
                          upper=True, klass="axis"))
    c.zones.append(c.text(cx, y0 - 36, ya["name"], RAMP["eyebrow"], ink, tracking=0.18, upper=True, klass="axis"))
    tags = d.get("quadrants") or {}
    for key, tx, ty, anchor in (("top_left", x0 + 12, y0 + 24, "start"), ("top_right", x0 + size - 12, y0 + 24, "end"),
                                ("bottom_left", x0 + 12, y0 + size - 14, "start"),
                                ("bottom_right", x0 + size - 12, y0 + size - 14, "end")):
        if tags.get(key):
            c.zones.append(c.text(tx, ty, tags[key], RAMP["eyebrow"], c.t["muted"], anchor, tracking=0.14,
                                  upper=True, klass="quadrant-tag"))
    boxes = []
    for it in items:
        try:
            sx, sy = float(it.get("x")), float(it.get("y"))
        except (TypeError, ValueError):
            raise DiagramError("item %r needs x and y between 0 and 1" % it.get("name"))
        if not (0 <= sx <= 1 and 0 <= sy <= 1) or sx == 0.5 or sy == 0.5:
            raise DiagramError("item %r sits at %s, %s: x and y are between 0 and 1 and never 0.5 (on an axis is "
                               "no quadrant)" % (it.get("name"), it.get("x"), it.get("y")))
        px = x0 + 24 + sx * (size - 48)
        py = y0 + size - 24 - sy * (size - 48)
        focal = bool(it.get("focal"))
        name = it.get("name", "")
        tw = text_width(name, RAMP["sub"] + 2)
        right = (px + 10, "start", px + 10, px + 10 + tw)
        left = (px - 10, "end", px - 10 - tw, px - 10)
        # A label stays in its item's quadrant: it never crosses an axis (type-quadrant.md) or another label.
        lo_x, hi_x = (x0 + 4, cx - 4) if px < cx else (cx + 4, x0 + size - 4)
        pick = None
        for cand in (right, left):
            box = (cand[2], py - 12, cand[3], py + 4)
            if box[0] < lo_x or box[2] > hi_x:
                continue
            if not any(box[0] < b[2] and b[0] < box[2] and box[1] < b[3] and b[1] < box[3] for b in boxes):
                pick = cand
                break
        if pick is None:
            raise DiagramError("the label %r has no room in its quadrant beside its dot: shorten it or move the "
                               "item further from the axis" % name)
        boxes.append((pick[2], py - 12, pick[3], py + 4))
        c.nodes.append('<circle class="item%s" cx="%g" cy="%g" r="%d" fill="%s"/>'
                       % (" focal" if focal else "", px, py, 6 if focal else 4, c.t["accent"] if focal else ink))
        if focal:
            c.focal += 1
        c.top.append(c.text(pick[0], py + 4, name, RAMP["sub"] + 2, c.t["accent"] if focal else ink, pick[1],
                            weight=c.t["title_weight"] if focal else None, klass="item-label"))
    return WIDTH, y0 + size + 32


def layout_layers(d, c):
    """Layer stack (type-layers.md): four to six full-width bands, an index tag on the left, the name, a note
    on the right, hairlines between; the accent on one focal layer; a direction label in the left margin."""
    layers = d.get("layers") or []
    lo, hi = LIMITS["layers"]
    if not lo <= len(layers) <= hi:
        raise DiagramError("a layer stack has %d to %d layers; this one has %d" % (lo, hi, len(layers)))
    x0, width = MARGIN + 160, WIDTH - 2 * MARGIN - 160
    h = 72
    y = MARGIN
    for i, layer in enumerate(layers):
        focal = bool(layer.get("focal"))
        fill = c.t["accent_tint"] if focal else (c.t["paper2"] if i % 2 else c.t["paper"])
        stroke = c.t["accent"] if focal else c.t["ink"]
        c.zones.append('<rect class="layer%s" x="%d" y="%d" width="%d" height="%d" fill="%s" stroke="%s" '
                       'stroke-width="%g"/>' % (" focal" if focal else "", x0, y, width, h, fill,
                                                c.t["rule"] if not focal else stroke, 1.5 if focal else 1))
        if focal:
            c.focal += 1
        tag = layer.get("tag") or "L%d" % (len(layers) - i)
        c.nodes.append(c.text(x0 + 20, y + h / 2 + 4, tag, RAMP["eyebrow"], c.t["muted"], "start", tracking=0.18,
                              upper=True, klass="layer-tag"))
        name = layer.get("name", "")
        if wrap(name, RAMP["name"] + 2, width * 0.45, 1) is None:
            raise DiagramError("the layer name %r is too long for one line: shorten it" % name)
        c.nodes.append(c.text(x0 + 96, y + h / 2 + 6, name, RAMP["name"] + 2, c.t["accent"] if focal else c.t["ink"],
                              "start", weight=c.t["title_weight"], klass="layer-name"))
        if layer.get("note"):
            note = wrap(layer["note"], RAMP["sub"], width * 0.42, 2)
            if note is None:
                raise DiagramError("the note on %r does not fit two lines: shorten it" % name)
            ny = y + h / 2 + 4 - (len(note) - 1) * 8
            for line in note:
                c.nodes.append(c.text(x0 + width - 20, ny, line, RAMP["sub"], c.t["muted"], "end", klass="layer-note"))
                ny += 16
        y += h
    c.zones.append('<rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="%s" stroke-width="1"/>'
                   % (x0, MARGIN, width, y - MARGIN, c.t["muted"]))
    if d.get("direction"):
        ax = x0 - 24
        flow = d.get("flow", "up")
        if flow not in ("up", "down"):
            raise DiagramError("flow is up (towards the top layer, the default) or down; this one is %r" % flow)
        ends = (y - 12, MARGIN + 12) if flow == "up" else (MARGIN + 12, y - 12)
        c.zones.append('<path d="M%d,%d L%d,%d" stroke="%s" stroke-width="1" marker-end="url(#%s-arrow)"/>'
                       % (ax, ends[0], ax, ends[1], c.t["muted"], c.slug))
        lines = wrap(d["direction"].upper(), RAMP["eyebrow"], x0 - 40 - MARGIN, 3)
        if lines is None:
            raise DiagramError("the direction %r is too long for the margin: two or three short words" % d["direction"])
        ty = (MARGIN + y) / 2 - (len(lines) - 1) * 8
        for line in lines:
            c.zones.append(c.text(x0 - 36, ty, line, RAMP["eyebrow"], c.t["muted"], "end",
                                  upper=True, klass="direction"))
            ty += 16
    return WIDTH, y + 8


LAYOUTS = {"flowchart": layout_flow, "swimlane": layout_swimlane, "org-chart": layout_org,
           "timeline": layout_timeline, "gantt": layout_gantt, "quadrant": layout_quadrant, "layers": layout_layers}


# ---- the page -----------------------------------------------------------------------------------------------------

def slug_of(path):
    s = re.sub(r"[^a-z0-9]+", "-", Path(path).stem.lower().replace(".diagram", "")).strip("-")
    return s or "diagram"


def page(d, svg, width, height, t, slug):
    """The master page: eyebrow, title, the drawing, a source line. Its @page is the drawing's frame, so the PDF is
    one sheet with nothing cut."""
    eyebrow = d.get("eyebrow", "")
    title = d["title"]
    source = d.get("source", "")
    head = 132 if eyebrow else 108
    foot = 48 if source else 16
    page_h = height + head + foot
    style = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root { --paper: %(paper)s; --ink: %(ink)s; --muted: %(muted)s; --rule: %(rule)s; --face: %(family)s; }
@page { size: %(w)dpx %(h)dpx; margin: 0; }
html, body { background: var(--paper); color: var(--ink); font-family: var(--face); font-weight: %(weight)d; }
.frame { width: %(w)dpx; padding: 0; }
.head { padding: 40px 40px 0 40px; height: %(head)dpx; }
.eyebrow { font-size: 11px; letter-spacing: 0.18em; text-transform: uppercase; color: var(--muted); margin-bottom: 12px; }
h1 { font-size: 40px; font-weight: %(tw)d; letter-spacing: -0.02em; line-height: 1.1; color: var(--ink); }
.diagram-container { width: 100%%; overflow-x: auto; }
.diagram-container svg { width: 100%%; min-width: %(w)dpx; display: block; }
.source { padding: 12px 40px 16px 40px; font-size: 12px; color: var(--muted); }
@media print { .diagram-container { overflow-x: visible; } .diagram-container svg { min-width: 0; } }
""" % dict(t, w=width, h=page_h, head=head, tw=t["title_weight"])
    return """<!DOCTYPE html>
<html lang="%s">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>%s</title>
<style>%s</style>
</head>
<body>
<div class="frame">
<div class="head">%s<h1>%s</h1></div>
<div class="diagram-container slide">
%s
</div>
%s
</div>
</body>
</html>
""" % (esc(d.get("language", "en")), esc(title), style,
       '<p class="eyebrow">%s</p>' % esc(eyebrow) if eyebrow else "", esc(title), svg,
       '<p class="source">%s</p>' % esc(source) if source else ""), page_h


def build(data_path, look_path=None):
    """The HTML master and the standalone SVG; returns (html path, svg path, width, page height, svg height)."""
    data_path = Path(data_path)
    d = json.loads(data_path.read_text(encoding="utf-8"))
    kind = str(d.get("type", "")).strip().lower().replace("_", "-").replace(" ", "-")
    kind = {"org": "org-chart", "orgchart": "org-chart", "layer-stack": "layers", "flow": "flowchart",
            "process": "flowchart", "matrix": "quadrant", "roadmap": "gantt"}.get(kind, kind)
    if kind not in TYPES:
        raise DiagramError("the type is %r; it is one of %s" % (d.get("type"), ", ".join(TYPES)))
    title = str(d.get("title") or "").strip()
    desc = str(d.get("description") or "").strip()
    if not title or len(title) > 60:
        raise DiagramError("the title is the subject's short name, 1 to 60 characters (it has %d)" % len(title))
    if not desc:
        raise DiagramError("the description is one sentence on what the diagram shows, for a reader who cannot "
                           "see it")
    d["title"] = title
    t = load_look(look_path)
    stem = data_path.name[:-len(".diagram.json")] if data_path.name.endswith(".diagram.json") else data_path.stem
    slug = slug_of(stem)
    c = Canvas(t, slug)
    width, height = LAYOUTS[kind](d, c)
    width, height = g4(width), g4(height)
    legend = []
    for item in d.get("legend") or []:
        k = "focal" if item.get("kind") == "focal" else kind_of(item)
        legend.append({"kind": k, "label": str(item.get("label", "")).strip()})
    svg, svg_h = svg_document(c, width, height, title, desc, kind, legend, d.get("source"))
    doc, page_h = page(d, svg, width, svg_h, t, slug)
    out_html = data_path.with_name(stem + ".html")
    out_svg = data_path.with_name(stem + ".svg")
    out_html.write_text(doc, encoding="utf-8")
    out_svg.write_text('<?xml version="1.0" encoding="UTF-8"?>\n' + svg + "\n", encoding="utf-8")
    return out_html, out_svg, width, page_h, svg_h


# ---- printing -----------------------------------------------------------------------------------------------------

PLAYWRIGHT = """
import sys
from playwright.sync_api import sync_playwright
src, pdf, png, w, h = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
with sync_playwright() as pw:
    b = pw.chromium.launch(args=["--no-sandbox"])
    p = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=2)
    p.goto("file://" + src)
    p.pdf(path=pdf, width="%dpx" % w, height="%dpx" % h, print_background=True, prefer_css_page_size=True)
    p.locator("svg.diagram").screenshot(path=png)
    b.close()
"""


def print_out(html_path, pdf, png, width, page_h):
    """The PDF and the PNG, by the app's own engine (nodejam-print) or Playwright outside the app."""
    tool = shutil.which("nodejam-print")
    why = "nodejam-print is not on PATH"
    if tool:
        # The app's printer never opens a window wider than the screen, so a 2x picture taken by zooming the
        # page came out cut at half width (2026-10-12). The PDF prints from the page; the PNG comes from a page
        # holding only the SVG at its own size, in a window that size, taken at --scale 2.
        shots = Path(tempfile.mkdtemp(prefix="diagram-shots-"))
        svg_text = Path(html_path).with_suffix(".svg").read_text(encoding="utf-8")
        vb = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg_text)
        w1, h1 = (float(vb.group(1)), float(vb.group(2))) if vb else (width, page_h)
        head = re.match(r"\s*(?:<\?xml[^>]*>\s*)?<svg\b[^>]*>", svg_text)
        tag_ = re.sub(r'\s(width|height)="[^"]*"', "", head.group(0))
        tag_ = re.sub(r"^\s*<\?xml[^>]*>\s*", "", tag_).replace("<svg", '<svg width="%g" height="%g"' % (w1, h1), 1)
        shot = shots / "shot.html"
        shot.write_text('<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;padding:0;'
                        'overflow:hidden}.slide{display:block;width:%gpx;height:%gpx}</style></head><body>'
                        '<div class="slide">%s%s</div></body></html>' % (w1, h1, tag_, svg_text[head.end():]),
                        encoding="utf-8")
        r = subprocess.run([tool, str(html_path), str(pdf), "--width", str(width), "--height", str(page_h)],
                           capture_output=True, text=True)
        if r.returncode == 0:
            r = subprocess.run([tool, str(shot), "--shots", str(shots), "--scale", "2", "--width", "%d" % math.ceil(w1),
                                "--height", "%d" % math.ceil(h1)], capture_output=True, text=True)
            if r.returncode != 0 and "--scale" in (r.stderr or ""):
                r.stderr = "this app's printer has no --scale for a sharp PNG: update the app"
        got = sorted(shots.glob("p-*.png"))
        size = struct.unpack(">II", got[0].read_bytes()[16:24]) if r.returncode == 0 and got else None
        if size and abs(size[0] - 2 * w1) <= 2 and abs(size[1] - 2 * h1) <= 2:
            shutil.move(str(got[0]), str(png))
            shutil.rmtree(shots, ignore_errors=True)
            return "nodejam-print"
        if size:
            r.returncode, r.stderr = 1, "the app's printer gave a %d x %d picture, not %d x %d" % (
                size[0], size[1], 2 * w1, 2 * h1)
        shutil.rmtree(shots, ignore_errors=True)
        why = ((r.stderr or r.stdout).strip().splitlines() or ["nodejam-print failed"])[-1]
    args = [str(Path(html_path).resolve()), str(Path(pdf).resolve()), str(Path(png).resolve()), str(width),
            str(page_h)]
    try:
        import playwright  # noqa: F401
        r = subprocess.run([sys.executable, "-c", PLAYWRIGHT] + args, capture_output=True, text=True)
        if r.returncode == 0:
            return "playwright (%s)" % why
        why = ((r.stderr or r.stdout).strip().splitlines() or [why])[-1]
    except ImportError:
        pass
    uv = shutil.which("uv") or os.path.expanduser("~/.local/bin/uv")
    if os.path.exists(uv):
        r = subprocess.run([uv, "run", "--no-project", "--with", "playwright", "python", "-c", PLAYWRIGHT] + args,
                           capture_output=True, text=True)
        if r.returncode == 0:
            return "playwright through uv (%s)" % why
        why = ((r.stderr or r.stdout).strip().splitlines() or [why])[-1]
    raise RuntimeError("could not print the diagram: %s; run this inside the app" % why)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("data", help="<name>.diagram.json")
    ap.add_argument("--look", help="a look file to use instead of the library's look.json")
    ap.add_argument("--no-print", action="store_true", help="write the HTML and the SVG only")
    a = ap.parse_args(argv)
    try:
        html_path, svg_path, width, page_h, _ = build(a.data, a.look)
    except DiagramError as exc:
        print("diagram: %s" % exc, file=sys.stderr)
        return 1
    print("wrote %s and %s" % (html_path.name, svg_path.name))
    if a.no_print:
        return 0
    pdf, png = html_path.with_suffix(".pdf"), html_path.with_suffix(".png")
    try:
        how = print_out(html_path, pdf, png, width, page_h)
    except RuntimeError as exc:
        print("diagram: %s" % exc, file=sys.stderr)
        return 2
    print("printed %s and %s with %s" % (pdf.name, png.name, how))
    return 0


if __name__ == "__main__":
    sys.exit(main())
