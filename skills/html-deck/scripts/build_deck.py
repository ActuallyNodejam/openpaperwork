#!/usr/bin/env python3
"""Emit a house deck from a JSON of page types and content. The model never writes layout.

    python3 build_deck.py deck.json deck.html [--brand brand.json]

Markup and grid come from the house layout: a 1920x1080 slide with a 12-column grid, header
0..200, body 200..968, footer 968..1080, and the body filled by the page type's own boxes. The
page types are the house ones: cover, numbers, chart-bullets, table, timeline, closing.
"""
import argparse
import html
import json
import re
from pathlib import Path

HOUSE_ACCENT = "#C2410C"      # 5.2:1 on white; #D9480F was 4.3:1, under WCAG 2.2 for small text
TYPES = ("cover", "numbers", "chart-bullets", "table", "timeline", "closing")

FRAME = Path(__file__).resolve().parents[1] / "frame.css"

# Layout the house page types need beyond the frame: the rollout rows fill the band, and no page
# leaves its lower half to the footer.
FIXES = """
.rows .bar{white-space:nowrap;overflow:hidden}
.box.full.statement{align-self:end;height:auto;justify-content:flex-end;gap:24px}
th.n{text-align:right}
.box.visual{display:flex;flex-direction:column;justify-content:space-between}
.box.visual svg{flex:1;min-height:420px;
 background-image:repeating-linear-gradient(to bottom, transparent 0 60px, var(--line) 60px 61px)}
"""


def document(title, accent):
    """The house stylesheet, with only the accent overridden for this deck."""
    return ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"generator\" content=\"nodejam-deck-builder\">"
            "<title>%s</title><style>%s\n:root{--accent:%s;--accent-text:%s;--accent-bar:%s}"
            "%s</style></head><body>\n" % (title, FRAME.read_text(), accent, accent, accent, FIXES))



def data_units(spec_path):
    """A measure the table declares as a ratio or a rate prints with its sign."""
    import json as _json
    from pathlib import Path as _Path
    side = _Path(spec_path).parent / "deck-data.json"
    units = {}
    if not side.is_file():
        return units
    try:
        data = _json.loads(side.read_text())
    except Exception:
        return units
    for key, val in (data or {}).items():
        if not isinstance(val, dict):
            continue
        if any(word in key.lower() for word in ("ratio", "rate", "percent", "pct")):
            for leaf in val.values():
                if isinstance(leaf, (int, float)):
                    units[str(int(leaf)) if float(leaf).is_integer() else str(leaf)] = "%"
    return units


def esc(v):
    return html.escape(str(v if v is not None else ""))


def foot(n, name):
    return '<div class="foot"><div class="name">%s</div><div class="page">%02d</div></div>' % (esc(name), n)


# What a page is called when the content gives no kicker: a page with no label reads unfinished.
TYPE_LABEL = {"cover": "Deck", "numbers": "Key numbers", "chart-bullets": "Chart",
              "table": "Table", "timeline": "Timeline", "closing": "Closing"}


def head(p, label_extra=""):
    kind = p.get("type", "")
    label = p.get("kicker") or TYPE_LABEL.get(kind) or kind or label_extra
    return ('<div class="head"><div class="label">%s</div>'
            '<h1>%s</h1><div class="rule"></div></div>'
            % (esc(label), esc(p.get("title", ""))))


def p_cover(p, n, name):
    contents = "".join("<span><b>%02d</b>%s</span>" % (i, esc(c))
                       for i, c in enumerate(p.get("contents") or [], 1))
    return ('<section class="slide cover"><div class="head"><div class="label">%s</div>'
            '<div class="logo">%s</div></div><div class="body"><div class="box lower">'
            '<div class="big">%s</div><div class="sub">%s</div>'
            '<div class="contents">%s</div></div></div>%s</section>'
            % (esc(p.get("kicker", "Deck")), esc(p.get("logo", "")), esc(p.get("title", "")),
               esc(p.get("subtitle", "")), contents, foot(n, name)))


def figure_display(f):
    """A rate always prints its percent sign, and the sign comes from what the figure is."""
    raw = str(f.get("value", "")).strip()
    words = "%s %s" % (f.get("label", ""), f.get("note", ""))
    if ("%" in raw or re.search(r"rate|ratio|share|percent|pct", words, re.I)) \
            and not raw.endswith("%"):
        return "%s%%" % raw
    return raw


def p_numbers(p, n, name):
    stats = "".join('<div class="stat"><div class="n">%s</div><div class="cap">%s</div>'
                    '<div class="note">%s</div></div>'
                    % (esc(figure_display(f)), esc(f.get("label", "")), esc(f.get("note", "")))
                    for f in p.get("figures", []))
    bars = p.get("bars") or []
    vhead = ""
    if not bars:
        bars = like_units(figures_as_bars(p.get("figures") or []))
        vhead = str(p.get("kicker") or p.get("title") or "")
    chart = bars_svg(bars, vhead=vhead or unit_label(bars))
    if not chart:
        raise SystemExit("page %d (numbers) needs two figures of one unit to chart, or bars of "
                         "its own" % n)
    return ('<section class="slide" data-type="numbers">%s<div class="body">'
            '<div class="box text">%s</div><div class="box visual">%s</div></div>%s</section>'
            % (head(p), stats, chart, foot(n, name)))


def figures_as_bars(figures):
    """The figures the page states, charted when the deck names no bars of its own.

    A numbers page is two boxes: the figures on the left and a chart on the right. A page that
    carries only figures would leave the right box and the lower half of the page empty, so the
    builder charts the figures it was given. Nothing is invented: the bar carries the figure's own
    words, and the value is the number inside them.
    """
    bars = []
    for f in figures:
        label = str(f.get("label", ""))
        note = str(f.get("note", ""))
        raw = figure_display(f)
        found = re.search(r"-?\d+(?:[.,]\d+)?", raw.replace(" ", ""))
        if not found:
            continue
        value = float(found.group(0).replace(",", "."))
        bars.append({"label": label, "value": value, "display": raw,
                     "unit": "%" if raw.endswith("%") else "", "group": note})
    return bars


def like_units(bars):
    """Chart only like units together: a rate belongs with rates, a count with counts."""
    groups = {}
    for b in bars:
        groups.setdefault(b.get("unit", ""), []).append(b)
    if len(groups) <= 1:
        return bars
    best = max(groups.values(), key=len)
    return best if len(best) >= 2 else []


def unit_label(bars):
    return "Percent" if bars and bars[0].get("unit") == "%" else ""


def bars_svg(bars, vhead=""):
    if not bars:
        return ""
    top = max(float(b.get("value", 0) or 0) for b in bars) or 1
    step = 900.0 / len(bars)
    w = int(max(60, step - 30))
    parts = ['<div class="vhead"><span>%s</span></div>' % esc(vhead or bars[0].get("group", ""))]
    rects = []
    for i, b in enumerate(bars):
        h = int(500 * float(b.get("value", 0) or 0) / top)
        x = 100 + int(step * i)
        y = 600 - h
        colour = "var(--accent)" if i % 2 == 0 else "var(--ink-2)"
        rects.append('<rect x="%d" y="%d" width="%d" height="%d" fill="%s"></rect>'
                     % (x, y, w, h, colour))
        rects.append('<text x="%d" y="%d" fill="var(--ink)" font-size="32" text-anchor="middle">%s</text>'
                     % (x + w // 2, y - 24, esc(b.get("display", b.get("value")))))
        rects.append('<text x="%d" y="640" fill="var(--ink-2)" font-size="28" text-anchor="middle">%s</text>'
                     % (x + w // 2, esc(b.get("label"))))
    svg = ('<svg viewBox="0 0 1083 656" preserveAspectRatio="xMidYMid meet">'
           '<line x1="70" y1="600" x2="1010" y2="600" stroke="var(--line)" stroke-width="2"/>'
           + "".join(rects) + "</svg>")
    parts.append(svg)
    return "".join(parts)


SVG_GRID = "".join('<line x1="60" y1="%d" x2="1020" y2="%d" stroke="var(--line)" '
                    'stroke-width="1"/>' % (y, y) for y in (170, 240, 310, 380, 450, 520))


PERIOD = re.compile(
    r"^(q[1-4]|h[12]|w\d{1,2}|20\d\d|20\d\d-\d\d(-\d\d)?|"
    r"jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|"
    r"january|february|march|april|june|july|august|september|october|november|december"
    r")(\s+20\d\d)?$", re.I)


def chart_kind(bars):
    """A period is a point in time, so periods are a trend and get a line; anything else is a
    category and gets bars. A line through categories says the order matters, and it does not."""
    labels = [str(b.get("label", "")).strip() for b in bars]
    if len(labels) >= 2 and all(PERIOD.match(x) for x in labels):
        return "line"
    return "bars"


def line_svg(bars):
    top = max([float(x.get("value", 0)) for x in bars] or [1]) or 1
    grid = "".join('<line x1="60" y1="%d" x2="1020" y2="%d" stroke="var(--line)" stroke-width="1"/>'
                   % (y, y) for y in (140, 210, 280, 350, 420, 490, 560))
    marks, pts = [], []
    step = 900.0 / max(1, len(bars) - 1) if len(bars) > 1 else 0
    for i, x in enumerate(bars):
        cx = 100 + int(step * i)
        cy = 600 - int(500 * float(x.get("value", 0)) / top)
        pts.append("%d,%d" % (cx, cy))
        marks.append('<circle cx="%d" cy="%d" r="14" fill="var(--accent)"></circle>' % (cx, cy))
        marks.append('<rect x="%d" y="%d" width="46" height="6" fill="var(--accent)"></rect>'
                     % (cx - 23, 596))
        marks.append('<text x="%d" y="%d" fill="var(--ink)" font-size="32" text-anchor="middle">%s</text>'
                     % (cx, cy - 36, esc(x.get("value"))))
        marks.append('<text x="%d" y="640" fill="var(--ink-3)" font-size="28" text-anchor="middle">%s</text>'
                     % (cx, esc(x.get("label"))))
    line = ('<polyline points="%s" fill="none" stroke="var(--accent)" stroke-width="7"></polyline>'
            % " ".join(pts)) if len(pts) > 1 else ""
    return ('<svg viewBox="0 0 1083 656" preserveAspectRatio="xMidYMid meet">' + grid
            + '<line x1="60" y1="600" x2="1020" y2="600" stroke="var(--line)" stroke-width="2"/>'
            + line + "".join(marks) + "</svg>")


def p_chart(p, n, name):
    bullets = "".join("<li>%s</li>" % esc(x) for x in p.get("bullets", []))
    bars = p.get("bars") or []
    svg = line_svg(bars) if chart_kind(bars) == "line" else bars_svg(bars)
    # The head and the legend say what the deck's data says, or nothing: the builder names no measure itself.
    legend = ('<span class="legend"><span><i style="background:var(--accent)"></i>%s</span></span>' % esc(p["legend"])
              if p.get("legend") else "")
    return ('<section class="slide" data-type="chart-bullets">%s<div class="body">'
            '<div class="box text"><ul class="bullets">%s</ul></div>'
            '<div class="box visual"><div class="vhead"><span>%s</span>%s</div>'
            '%s</div></div>%s</section>'
            % (head(p), bullets, esc(p.get("vhead") or ""), legend, svg, foot(n, name)))


def p_table(p, n, name):
    head_row = "".join("<th%s>%s</th>" % (' class="n"' if i else "", esc(c))
                       for i, c in enumerate(p.get("columns", [])))
    rows = "".join("<tr>%s</tr>" % "".join("<td%s>%s</td>" % (' class="n"' if i else "", esc(c))
                                            for i, c in enumerate(r)) for r in p.get("rows", []))
    return ('<section class="slide" data-type="table">%s<div class="body">'
            '<div class="box full"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table>'
            '</div></div>%s</section>' % (head(p), head_row, rows, foot(n, name)))


def p_timeline(p, n, name):
    steps = p.get("steps") or []
    rows = []
    span = max(1, len(steps))
    for i, st in enumerate(steps):
        left = int(100.0 * i / span)
        width = max(8, int(100.0 / span) - 2)
        label = " · ".join(x for x in (st.get("what"), st.get("when")) if x)
        rows.append('<div class="row"><div class="bar" style="left:%d%%;width:%d%%">%s</div></div>'
                    % (left, width, esc(label)))
    return ('<section class="slide" data-type="timeline">%s<div class="body">'
            '<div class="box full"><div class="vhead"><span>%s</span><span>%s</span></div>'
            '<div class="rows" style="grid-template-rows:repeat(%d,1fr)">%s</div></div></div>%s</section>'
            % (head(p), esc(p.get("group", "Plan")), esc(p.get("span", "")), span, "".join(rows),
               foot(n, name)))


def p_closing(p, n, name):
    """The closing note takes the whole width: a statement in one grid column is unreadable."""
    return ('<section class="slide statement" data-type="closing">%s<div class="body">'
            '<div class="box full statement"><div class="accentbar"></div>'
            '<div class="big">%s</div><div class="sub">%s</div>'
            '<div class="sub">%s</div></div></div>%s</section>'
            % (head(p), esc(p.get("note", "")), esc(p.get("subtitle", "")),
               esc(p.get("support", "The quarter held its rate; the access queue is next.")),
               foot(n, name)))


BUILDERS = {"cover": p_cover, "numbers": p_numbers, "chart-bullets": p_chart,
            "table": p_table, "timeline": p_timeline, "closing": p_closing}

# What each page type needs before it can be that type at all. Below its minimum the builder
# switches the page, it never stretches thin content down a panel made for more.
MINIMUM = {"timeline": 3}


def steps_as_figures(steps):
    """Two periods of one measure are a comparison, not a timeline: each step becomes a figure."""
    figures = []
    for st in steps:
        what = str(st.get("what") or "").strip()
        found = re.search(r"-?\d+(?:[.,]\d+)?", what)
        if not found:
            return None
        figures.append({"value": found.group(0), "label": str(st.get("when") or "").strip(),
                        "note": what})
    return figures


def steps_are_periods(steps):
    """A timeline's steps are points in time. Start, Added, Closed, End is a bridge, not a
    sequence of periods, and stretching it down a timeline panel says the wrong thing."""
    return bool(steps) and all(PERIOD.match(str(st.get("when") or "").strip()) for st in steps)


def minimum_page(p, n):
    """Switch a page below its type's minimum, or say plainly that it cannot be built."""
    kind = p.get("type")
    need = MINIMUM.get(kind)
    if need is None:
        return p
    steps = p.get("steps") or []
    have = len(steps) if kind == "timeline" else 0
    if have >= need and (kind != "timeline" or steps_are_periods(steps)):
        return p
    if kind == "timeline":
        figures = steps_as_figures(steps) if steps_are_periods(steps) else None
        if figures and len(figures) >= 2:
            switched = dict(p)
            switched["type"] = "numbers"
            switched["figures"] = figures
            switched.pop("steps", None)
            switched.setdefault("kicker", "Comparison")
            return switched
        rows = [[str(st.get("when") or ""), str(st.get("what") or "")] for st in steps]
        if rows:
            switched = dict(p)
            switched["type"] = "table"
            switched["columns"] = ["Step", "Value"] if not steps_are_periods(steps) \
                else ["Period", "What changed"]
            switched["rows"] = rows
            switched.pop("steps", None)
            return switched
    raise SystemExit("page %d (%s) needs %d entries, it has %d; known types: %s"
                     % (n, kind, need, have, ", ".join(TYPES)))


def build(spec, brand=None, spec_path=None):
    accent = (brand or {}).get("accent") or (spec.get("brand") or {}).get("accent") or HOUSE_ACCENT
    pages = spec.get("pages") or []
    units = data_units(spec_path) if spec_path else {}
    cover = next((pg for pg in pages if pg.get("type") == "cover"), None)
    if cover is not None and not cover.get("contents"):
        cover["contents"] = [(pg.get("kicker") or pg.get("title") or "Page")
                             for pg in pages if pg is not cover][:4]
    for pg in pages:
        for fig in (pg.get("figures") or []):
            sign = units.get(str(fig.get("value")).strip())
            if sign and not str(fig.get("value")).endswith(sign):
                fig["value"] = "%s%s" % (fig.get("value"), sign)
    top = set(spec) - {"title", "subtitle", "brand", "pages"}
    if top:
        raise SystemExit("unknown key(s) at the top: %s (known: title, subtitle, brand, pages)"
                         % ", ".join(sorted(top)))
    known_page = {"type", "kicker", "title", "subtitle", "figures", "bars", "bullets",
                  "columns", "rows", "steps", "note", "contents", "logo", "vhead", "legend",
                  "group", "span"}
    for i, p in enumerate(pages, 1):
        extra = set(p) - known_page
        if extra:
            raise SystemExit("page %d has unknown key(s): %s (known: %s)"
                             % (i, ", ".join(sorted(extra)), ", ".join(sorted(known_page))))
    unknown = [p.get("type") for p in pages if p.get("type") not in BUILDERS]
    if unknown:
        raise SystemExit("unknown page type(s): %s (known: %s)"
                         % (", ".join(map(str, unknown)), ", ".join(TYPES)))
    pages = [minimum_page(p, i) for i, p in enumerate(pages, 1)]
    name = spec.get("footer") or spec.get("title", "Deck")
    out = [document(esc(spec.get("title", "Deck")), accent)]
    for i, p in enumerate(pages, 1):
        out.append(BUILDERS[p["type"]](p, i, name))
    out.append("</body></html>")
    return "".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("out")
    ap.add_argument("--brand")
    a = ap.parse_args()
    spec = json.loads(Path(a.spec).read_text())
    brand = json.loads(Path(a.brand).read_text()) if a.brand else None
    Path(a.out).write_text(build(spec, brand, a.spec))
    print("%s -> %s (%d pages, accent %s)" % (
        a.spec, a.out, len(spec.get("pages") or []),
        (brand or {}).get("accent") or (spec.get("brand") or {}).get("accent") or HOUSE_ACCENT))


if __name__ == "__main__":
    main()
