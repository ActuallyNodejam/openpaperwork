"""The diagram pack's rules: the drawing on disk, judged by code. Standard library only.

check(rule_id, path, case, stage) -> (passed, evidence)

The file handed back is the PDF, the SVG or the PNG; every rule reads the master beside it, <name>.html (or, for a
drawing made by hand with no page, <name>.svg). The rules are diagram-design's (github.com/cathrynlavery/diagram-
design, MIT, 2.6.74): its own scripts where it has one, ported unchanged, and its written limits and contracts
held by code here, since no model judges the file.

DIAG-CONTRACT  The accessible SVG contract and single-file safety (its self_check.py, ported unchanged as
               diagram_contract.py, run offline): role img, a title first and a desc, ids prefixed by the
               diagram's slug, aria-labelledby naming both, no script or executable attribute, no remote
               reference; and the title is the subject's short name, 60 characters at most (SKILL.md section 12).
DIAG-OFFLINE   No web address anywhere in the master or the SVG, Google Fonts included: the file renders the
               same with no network (stricter than the source, which allows its font stylesheet).
DIAG-GEOMETRY  Its verify-geometry.py, ported unchanged as diagram_geometry.py: no label mask under a node drawn
               after it; connectors orthogonal, off node borders and corners, fanned 12 px apart on a shared
               edge, never stacked on one another.
DIAG-BOUNDS    Nothing drawn past the edge of the viewBox: the clipping its lint-render.py finds in a browser,
               found here from the coordinates, text measured on the style guide's width budget.
DIAG-FIT       Every line of text inside the box it stands in, on the same budget (style-guide.md, Width budget).
DIAG-OVERLAP   No two node boxes on one another and no two pieces of text on one another.
DIAG-CONTRAST  Text at 4.5:1 against what it stands on (3:1 from 18 px, or 14 px at 600 and heavier), lines
               and arrows at 3:1 (the style guide's contrast contract, its verify-contrast.py's thresholds,
               WCAG 2.2 1.4.3 and 1.4.11).
DIAG-BUDGET    The complexity budget (SKILL.md section 7, layout-budget.md): 9 nodes and 12 arrows, 2 accent
               elements; a swimlane 5 lanes; an org chart 12 people, 4 tiers, 5 reports a parent, 1 accent; a
               gantt 12 tasks; a quadrant 12 items; a layer stack 4 to 6 layers.
DIAG-LABEL     Every arrow label 14 characters at most (primitives-core.md, Arrow labels).
DIAG-EXPORT    The PDF, the SVG and the PNG stand beside the master and were made from this version of it.
DIAG-PNG       The PNG is the whole drawing at twice its size: twice the viewBox wide and high, its ink reaching
               twice the rightmost and lowest shape of the SVG, and no ink on its right or bottom edge (a capture
               cut short, at half width say, leaves the rest of the picture blank or slices it at the edge).
"""
import re
import struct
import sys
import zlib
from pathlib import Path
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import diagram_contract  # noqa: E402  (plain imports: the plugin build finds a check's modules by its import lines)
import diagram_geometry  # noqa: E402

SVG_NS = "{http://www.w3.org/2000/svg}"
SANS_EM, WIDE_EM = 0.60, 1.0
LIMITS = {
    "flowchart": {"nodes": 9, "arrows": 12, "focal": 2},
    "swimlane": {"nodes": 9, "arrows": 12, "focal": 2, "lanes": 5},
    "org-chart": {"nodes": 12, "depth": 4, "reports": 5, "focal": 1},
    "timeline": {"focal": 2},
    "gantt": {"tasks": 12, "focal": 2},
    "quadrant": {"items": 12, "focal": 2},
    "layers": {"layers": (4, 6), "focal": 2},
    None: {"nodes": 9, "arrows": 12, "focal": 2},
}


# ---- reading the drawing ------------------------------------------------------------------------------------------

def master_of(path):
    path = Path(path)
    for cand in (path.with_suffix(".html"), path.with_suffix(".svg")):
        if cand.is_file():
            return cand
    return None


def svg_source(master):
    text = master.read_text(encoding="utf-8")
    m = re.search(r"<svg\b.*?</svg>", text, re.S)
    if not m:
        raise ValueError("no <svg> in %s" % master.name)
    return m.group(0)


def svg_tree(master):
    src = svg_source(master)
    if "xmlns=" not in src[:400]:
        src = src.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"', 1)
    return ET.fromstring(src)


def tag(el):
    return el.tag.replace(SVG_NS, "")


def num(el, name, default=0.0):
    try:
        return float(re.sub(r"px$", "", str(el.get(name, default))))
    except ValueError:
        return default


def viewbox(root):
    vb = [float(v) for v in re.split(r"[\s,]+", (root.get("viewBox") or "0 0 0 0").strip())]
    return vb if len(vb) == 4 else [0, 0, 0, 0]


def walk(el, inherited=None, offset=(0.0, 0.0)):
    """Every element with the attributes it inherits from its groups (fill, font-size, font-weight, anchor) and
    the translate() offset of its groups."""
    inherited = dict(inherited or {})
    for key in ("fill", "font-size", "font-weight", "text-anchor", "letter-spacing", "class"):
        if el.get(key) is not None:
            inherited[key] = el.get(key)
    m = re.search(r"translate\(\s*([-\d.]+)[\s,]*([-\d.]*)\s*\)", el.get("transform") or "")
    if m:
        offset = (offset[0] + float(m.group(1)), offset[1] + float(m.group(2) or 0))
    yield el, inherited, offset
    for child in el:
        yield from walk(child, inherited, offset)


def is_wide(ch):
    o = ord(ch)
    return (0x1100 <= o <= 0x115F or 0x2E80 <= o <= 0xA4CF or 0xAC00 <= o <= 0xD7A3 or 0xF900 <= o <= 0xFAFF
            or 0xFE30 <= o <= 0xFE4F or 0xFF00 <= o <= 0xFF60 or 0xFFE0 <= o <= 0xFFE6)


def texts(root):
    """(content, x0, y0, x1, y1, size, weight, fill) for every <text>, measured on the width budget."""
    out = []
    for el, inh, (ox, oy) in walk(root):
        if tag(el) != "text":
            continue
        s = "".join(el.itertext()).strip()
        if not s:
            continue
        size = float(re.sub(r"px$", "", str(inh.get("font-size", 16))) or 16)
        track = inh.get("letter-spacing") or "0"
        tr = float(track[:-2]) if track.endswith("em") else float(re.sub(r"px$", "", track) or 0) / size
        width = sum((WIDE_EM if is_wide(c) else SANS_EM) * size + tr * size for c in s)
        x, y = num(el, "x") + ox, num(el, "y") + oy
        anchor = inh.get("text-anchor", "start")
        x0 = x - width / 2 if anchor == "middle" else x - width if anchor == "end" else x
        weight = str(inh.get("font-weight", "400"))
        weight = 700 if weight == "bold" else int(weight) if weight.isdigit() else 400
        out.append((s, x0, y - 0.78 * size, x0 + width, y + 0.22 * size, size, weight, inh.get("fill")))
    return out


def rects(root, stroked_only=False):
    out = []
    for el, inh, (ox, oy) in walk(root):
        if tag(el) != "rect" or el.get("width", "").endswith("%"):
            continue
        stroke = el.get("stroke")
        if stroked_only and (not stroke or stroke == "none"):
            continue
        x, y = num(el, "x") + ox, num(el, "y") + oy
        out.append((x, y, x + num(el, "width"), y + num(el, "height"), el.get("fill"), stroke, el))
    return out


def nodes(root):
    """Stroked boxes at least 60 x 40 (verify-geometry.py's notion of a node), less zones that hold others."""
    boxes = [r for r in rects(root, True) if r[2] - r[0] >= 60 and r[3] - r[1] >= 40]
    inside = lambda a, b: a is not b and b[0] <= a[0] and b[1] <= a[1] and a[2] <= b[2] and a[3] <= b[3]
    return [b for b in boxes if not any(inside(o, b) for o in boxes)]


def paper(root):
    for el in root:
        if tag(el) == "rect" and el.get("width") == "100%":
            return el.get("fill") or "#FFFFFF"
    return "#FFFFFF"


# ---- colour ---------------------------------------------------------------------------------------------------------

def rgb(value):
    v = str(value or "").strip()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", v):
        return tuple(int(v[i:i + 2], 16) for i in (1, 3, 5))
    if re.fullmatch(r"#[0-9a-fA-F]{3}", v):
        return tuple(int(c * 2, 16) for c in v[1:])
    m = re.fullmatch(r"rgba?\(([^)]*)\)", v)
    if m:
        parts = [p.strip() for p in m.group(1).split(",")]
        return tuple(int(float(p)) for p in parts[:3])
    named = {"white": (255, 255, 255), "black": (0, 0, 0)}
    return named.get(v.lower())


def luminance(c):
    def ch(v):
        v /= 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(x) for x in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# ---- the rules ------------------------------------------------------------------------------------------------------

def rule_contract(master):
    if master.suffix.lower() == ".svg":
        src = master.read_text(encoding="utf-8")
        tmp = master.with_name("." + master.stem + ".contract.html")
        tmp.write_text("<!DOCTYPE html><html><body>%s</body></html>" % src.split("?>", 1)[-1], encoding="utf-8")
        try:
            errors = diagram_contract.verify(tmp, offline=True)
        finally:
            tmp.unlink()
    else:
        errors = diagram_contract.verify(master, offline=True)
    title = svg_tree(master).find(SVG_NS + "title")
    if title is not None and len("".join(title.itertext()).strip()) > 60:
        errors.append("the title is %d characters; it is the subject's short name, 60 at most"
                      % len("".join(title.itertext()).strip()))
    if errors:
        return False, "%s: %s" % (master.name, "; ".join(errors[:4]))
    return True, ""


def rule_offline(master):
    found = []
    for f in (master, master.with_suffix(".svg")):
        if f.is_file():
            for m in re.finditer(r"(?:https?:)?//[A-Za-z0-9.-]+\.[A-Za-z]{2,}[^\s\"')<]*", f.read_text(encoding="utf-8")):
                if not m.group(0).lstrip("htps:/").startswith("www.w3.org"):
                    found.append("%s: %s" % (f.name, m.group(0)[:60]))
    if found:
        return False, "a web address in the drawing (%s): a diagram carries everything it shows, and the look's " \
                      "face, never a web font" % "; ".join(found[:3])
    return True, ""


def rule_geometry(master):
    findings = diagram_geometry.check(master)
    if findings:
        return False, "%d connector or label finding%s: %s" % (len(findings), "" if len(findings) == 1 else "s",
                                                            " | ".join(f.split(": ", 1)[-1] for f in findings[:3]))
    return True, ""


def rule_bounds(master):
    root = svg_tree(master)
    _, _, w, h = viewbox(root)
    out = []
    for s, x0, y0, x1, y1, *_ in texts(root):
        if x0 < -1 or y0 < -1 or x1 > w + 1 or y1 > h + 1:
            out.append("the text %r runs past the edge (%d..%d of %d wide)" % (s[:30], x0, x1, w))
    for x0, y0, x1, y1, *_ in rects(root):
        if x0 < -1 or y0 < -1 or x1 > w + 1 or y1 > h + 1:
            out.append("a box at %d,%d runs past the edge" % (x0, y0))
    for el, _, (ox, oy) in walk(root):
        if tag(el) == "circle":
            cx, cy, r = num(el, "cx") + ox, num(el, "cy") + oy, num(el, "r")
            if cx - r < -1 or cy - r < -1 or cx + r > w + 1 or cy + r > h + 1:
                out.append("a dot at %d,%d is cut by the edge" % (cx, cy))
    if out:
        return False, "%s: %s. The drawing is cut there in the PDF and the PNG." % (master.name, "; ".join(out[:3]))
    return True, ""


def rule_fit(master):
    root = svg_tree(master)
    boxes = nodes(root)
    out = []
    for s, x0, y0, x1, y1, *_ in texts(root):
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        home = [b for b in boxes if b[0] <= cx <= b[2] and b[1] <= cy <= b[3]]
        if not home:
            continue
        b = min(home, key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))
        if x0 < b[0] + 2 or x1 > b[2] - 2 or y0 < b[1] or y1 > b[3]:
            out.append("%r (%d wide) is wider or taller than its box (%d wide)" % (s[:30], x1 - x0, b[2] - b[0]))
    if out:
        return False, "%s: %s" % (master.name, "; ".join(out[:3]))
    return True, ""


def rule_overlap(master):
    root = svg_tree(master)
    out = []
    boxes = nodes(root)
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            if a[0] < b[2] - 1 and b[0] < a[2] - 1 and a[1] < b[3] - 1 and b[1] < a[3] - 1:
                out.append("two boxes at %d,%d and %d,%d lie on one another" % (a[0], a[1], b[0], b[1]))
    ts = texts(root)
    for i, a in enumerate(ts):
        for b in ts[i + 1:]:
            if a[1] < b[3] - 1 and b[1] < a[3] - 1 and a[2] < b[4] - 1 and b[2] < a[4] - 1:
                out.append("%r and %r are written on one another" % (a[0][:24], b[0][:24]))
    if out:
        return False, "%s: %s" % (master.name, "; ".join(out[:3]))
    return True, ""


def rule_contrast(master):
    root = svg_tree(master)
    ground = rgb(paper(root)) or (255, 255, 255)
    filled = [r for r in rects(root) if rgb(r[4])]
    out = []
    for s, x0, y0, x1, y1, size, weight, fill in texts(root):
        fg = rgb(fill or "#000000")
        if fg is None:
            continue
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        under = [r for r in filled if r[0] <= cx <= r[2] and r[1] <= cy <= r[3]]
        bg = rgb(under[-1][4]) if under else ground
        need = 3.0 if size >= 18 or (size >= 14 and weight >= 600) else 4.5
        if ratio(fg, bg) < need - 0.005:
            out.append("%r at %.2f:1 (needs %.1f:1)" % (s[:24], ratio(fg, bg), need))
    for el, _, _ in walk(root):
        if tag(el) in ("path", "line") and el.get("marker-end"):
            fg = rgb(el.get("stroke"))
            if fg and ratio(fg, ground) < 2.995:
                out.append("an arrow at %.2f:1 against the paper (needs 3:1)" % ratio(fg, ground))
    if out:
        return False, "%s: %s" % (master.name, "; ".join(out[:3]))
    return True, ""


def rule_budget(master):
    root = svg_tree(master)
    kind = root.get("data-diagram-type")
    lim = LIMITS.get(kind, LIMITS[None])
    klass = lambda el: (el.get("class") or "").split()
    out = []
    count = lambda pred: sum(1 for el, _, _ in walk(root) if pred(el))
    n_nodes = count(lambda el: tag(el) == "g" and "node" in klass(el)) if kind else len(nodes(root))
    if "nodes" in lim and n_nodes > lim["nodes"]:
        out.append("%d %s (at most %d: above that it is two diagrams, an overview and a detail)"
                   % (n_nodes, "people" if kind == "org-chart" else "boxes", lim["nodes"]))
    arrows = count(lambda el: tag(el) in ("path", "line") and el.get("marker-end") and "connector" in klass(el)) \
        if kind else count(lambda el: tag(el) in ("path", "line") and el.get("marker-end"))
    if "arrows" in lim and arrows > lim["arrows"]:
        out.append("%d arrows (at most %d)" % (arrows, lim["arrows"]))
    focal = count(lambda el: "focal" in klass(el) and tag(el) != "text")
    if kind and focal > lim["focal"]:
        out.append("%d accented elements (at most %d: the accent is editorial, not a flag)" % (focal, lim["focal"]))
    if "lanes" in lim:
        lanes = count(lambda el: "lane" in klass(el))
        if lanes > lim["lanes"]:
            out.append("%d lanes (at most %d)" % (lanes, lim["lanes"]))
    if "depth" in lim:
        depth = max([int(el.get("data-depth") or 0) for el, _, _ in walk(root)] or [0])
        reports = max([int(el.get("data-reports") or 0) for el, _, _ in walk(root)] or [0])
        if depth > lim["depth"]:
            out.append("%d tiers (at most %d)" % (depth, lim["depth"]))
        if reports > lim["reports"]:
            out.append("%d reports under one person (at most %d: group them under a team)" % (reports, lim["reports"]))
    for key, cls in (("tasks", "task"), ("items", "item")):
        if key in lim:
            n = count(lambda el: cls in klass(el) and tag(el) != "text")
            if n > lim[key]:
                out.append("%d %s (at most %d)" % (n, key, lim[key]))
    if "layers" in lim:
        n = count(lambda el: "layer" in klass(el) and tag(el) == "rect")
        lo, hi = lim["layers"]
        if not lo <= n <= hi:
            out.append("%d layers (%d to %d)" % (n, lo, hi))
    if out:
        return False, "%s is over its budget: %s. Split it or merge what always travels together." % (
            master.name, "; ".join(out))
    return True, ""


def rule_label(master):
    root = svg_tree(master)
    masks = [r for r in rects(root) if 20 <= r[2] - r[0] <= 200 and 8 <= r[3] - r[1] <= 14]
    long = []
    for s, x0, y0, x1, y1, *_ in texts(root):
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if any(m[0] <= cx <= m[2] and m[1] <= cy <= m[3] for m in masks) and len(s) > 14:
            long.append(s)
    if long:
        return False, "arrow label%s over 14 characters: %s. Say it in fewer words; detail goes in the box." % (
            "" if len(long) == 1 else "s", ", ".join(repr(s) for s in long[:4]))
    return True, ""


def png_size(path):
    data = path.read_bytes()[:32]
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return None
    return struct.unpack(">II", data[16:24])


def rule_export(master, path):
    stem = master.with_suffix("")
    if master.suffix.lower() != ".html":
        return False, "no %s.html beside %s: build the diagram with the skill's diagram.py, which writes the page " \
                      "and the PDF, SVG and PNG from it" % (stem.name, Path(path).name)
    missing, old = [], []
    made = master.stat().st_mtime
    for ext in (".pdf", ".svg", ".png"):
        f = stem.with_suffix(ext)
        if not f.is_file():
            missing.append(f.name)
        elif f.stat().st_mtime < made - 2:
            old.append(f.name)
    if missing or old:
        return False, "%s%s: run diagram.py on the data again so all four are made from one version" % (
            "missing %s" % ", ".join(missing) if missing else "",
            ("; " if missing else "") + "older than the page: %s" % ", ".join(old) if old else "")
    if not stem.with_suffix(".pdf").read_bytes()[:5] == b"%PDF-":
        return False, "%s is not a PDF inside" % stem.with_suffix(".pdf").name
    return True, ""


def shapes_extent(root):
    """The rightmost and lowest point a shape of the drawing reaches that shows clearly on the paper (text left
    out: its width is an estimate; a near-white hairline left out: a capture shows it under the ink threshold)."""
    xs, ys = [0.0], [0.0]
    ground = rgb(paper(root)) or (255, 255, 255)
    for el, inh, (ox, oy) in walk(root):
        t = tag(el)
        stroke = el.get("stroke") if el.get("stroke") not in (None, "none") else None
        colour = rgb(stroke or (el.get("fill") if el.get("fill") not in (None, "none") else inh.get("fill")))
        if colour is None or max(abs(a - b) for a, b in zip(colour, ground)) <= 48:
            continue
        if t == "rect" and not el.get("width", "").endswith("%"):
            xs.append(num(el, "x") + num(el, "width") + ox)
            ys.append(num(el, "y") + num(el, "height") + oy)
        elif t == "line":
            xs += [num(el, "x1") + ox, num(el, "x2") + ox]
            ys += [num(el, "y1") + oy, num(el, "y2") + oy]
        elif t in ("circle", "ellipse"):
            r = num(el, "r") or num(el, "rx")
            xs.append(num(el, "cx") + r + ox)
            ys.append(num(el, "cy") + (num(el, "r") or num(el, "ry")) + oy)
        elif t in ("polyline", "polygon"):
            nums = [float(v) for v in re.findall(r"-?[\d.]+", el.get("points") or "")]
            xs += [v + ox for v in nums[0::2]]
            ys += [v + oy for v in nums[1::2]]
        elif t == "path":
            for x, y in path_points(el.get("d") or ""):
                xs.append(x + ox)
                ys.append(y + oy)
    return max(xs), max(ys)


def path_points(d):
    """The end points of an absolute path's commands (M, L, H, V, A, C, Q, S, T), each as (x, y)."""
    out, x, y = [], 0.0, 0.0
    size = {"M": 2, "L": 2, "T": 2, "H": 1, "V": 1, "A": 7, "C": 6, "Q": 4, "S": 4, "Z": 0}
    for cmd, args in re.findall(r"([MLHVACQSTZmlhvacqstz])([^MLHVACQSTZmlhvacqstz]*)", d):
        nums, n = [float(v) for v in re.findall(r"-?\d*\.?\d+(?:e-?\d+)?", args)], size.get(cmd.upper(), 2)
        rel = cmd.islower()
        for i in range(0, len(nums) - n + 1, n) if n else []:
            chunk = nums[i:i + n]
            if cmd.upper() == "H":
                x = chunk[0] + (x if rel else 0)
            elif cmd.upper() == "V":
                y = chunk[0] + (y if rel else 0)
            else:
                x, y = chunk[-2] + (x if rel else 0), chunk[-1] + (y if rel else 0)
            out.append((x, y))
    return out


def ink_box(path, threshold=24):
    """(width, height, box): box is (x0, y0, x1, y1), x1 and y1 one past the last pixel that differs from the
    top-left pixel by more than threshold in a channel; None when the picture is one colour. Pillow when the
    Python has it (the app's does), else a small PNG reader for 8-bit pictures."""
    try:
        from PIL import Image, ImageChops
    except ImportError:
        Image = None
    if Image is not None:
        with Image.open(path) as im:
            im = im.convert("RGB")
            bg = Image.new("RGB", im.size, im.getpixel((0, 0)))
            r, g, b = ImageChops.difference(im, bg).split()
            mask = ImageChops.lighter(ImageChops.lighter(r, g), b).point(lambda v: 255 if v > threshold else 0)
            return im.size[0], im.size[1], mask.getbbox()
    data = Path(path).read_bytes()
    width, height, depth, colour, _, _, interlace = struct.unpack(">IIBBBBB", data[16:29])
    chans = {0: 1, 2: 3, 4: 2, 6: 4}.get(colour)
    if depth != 8 or not chans or interlace:
        raise ValueError("%s is a %d-bit PNG of colour type %d; the check reads 8-bit grey or RGB" % (
            Path(path).name, depth, colour))
    idat, at = [], 8
    while at + 8 <= len(data):
        size, name = struct.unpack(">I4s", data[at:at + 8])
        if name == b"IDAT":
            idat.append(data[at + 8:at + 8 + size])
        if name == b"IEND":
            break
        at += 12 + size
    raw = zlib.decompress(b"".join(idat))
    stride = width * chans
    prev, bg, box = bytearray(stride), None, None
    for row in range(height):
        start = row * (stride + 1)
        kind, line = raw[start], bytearray(raw[start + 1:start + 1 + stride])
        if kind:
            for i in range(stride):
                a = line[i - chans] if i >= chans else 0
                b, c = prev[i], (prev[i - chans] if i >= chans else 0)
                if kind == 1:
                    line[i] = (line[i] + a) & 255
                elif kind == 2:
                    line[i] = (line[i] + b) & 255
                elif kind == 3:
                    line[i] = (line[i] + (a + b) // 2) & 255
                elif kind == 4:
                    p = a + b - c
                    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                    line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        if bg is None:
            bg = bytes(line[:chans])
        prev = line
        if bytes(line) == bg * width:
            continue
        cols = [x for x in range(width)
                if max(abs(line[x * chans + k] - bg[k]) for k in range(min(chans, 3))) > threshold]
        if cols:
            box = (min(cols), row, max(cols) + 1, row + 1) if box is None else (
                min(box[0], cols[0]), box[1], max(box[2], cols[-1] + 1), row + 1)
    return width, height, box


def rule_png(master):
    png = master.with_suffix(".png")
    if not png.is_file():
        return False, "no %s beside %s: build the diagram with diagram.py" % (png.name, master.name)
    root = svg_tree(master)
    _, _, w, h = viewbox(root)
    pw, ph, box = ink_box(png)
    if abs(pw - 2 * w) > 2 or abs(ph - 2 * h) > 2:
        return False, "%s is %d x %d, not twice the drawing (%d x %d): build it again with diagram.py" % (
            png.name, pw, ph, 2 * w, 2 * h)
    if box is None:
        return False, "%s is one flat colour: the drawing was not captured" % png.name
    xmax, ymax = shapes_extent(root)
    out = []
    if box[2] < 2 * xmax - 12:
        out.append("its ink stops %d px from the left, and the drawing reaches %d: the right part is missing" % (
            box[2], 2 * xmax))
    if box[3] < 2 * ymax - 12:
        out.append("its ink stops %d px from the top, and the drawing reaches %d: the bottom is missing" % (
            box[3], 2 * ymax))
    if box[2] >= pw and xmax < w - 1:
        out.append("ink runs into its right edge: the picture is cut there")
    if box[3] >= ph and ymax < h - 1:
        out.append("ink runs into its bottom edge: the picture is cut there")
    if out:
        return False, "%s is not the whole drawing: %s. Build it again with diagram.py, inside the app or with " \
                      "Playwright, and look at the PNG" % (png.name, "; ".join(out))
    return True, ""


RULES = {"DIAG-CONTRACT": rule_contract, "DIAG-OFFLINE": rule_offline, "DIAG-GEOMETRY": rule_geometry,
         "DIAG-BOUNDS": rule_bounds, "DIAG-FIT": rule_fit, "DIAG-OVERLAP": rule_overlap,
         "DIAG-CONTRAST": rule_contrast, "DIAG-BUDGET": rule_budget, "DIAG-LABEL": rule_label,
         "DIAG-PNG": rule_png}


def check(rule_id, path, case=None, stage="first"):
    path = Path(path)
    master = master_of(path)
    if rule_id == "DIAG-EXPORT":
        if master is None:
            return False, "no %s.html beside %s: build the diagram with the skill's diagram.py" % (
                path.stem, path.name)
        return rule_export(master, path)
    if master is None:
        return False, "could not check: no %s.html or %s.svg beside %s" % (path.stem, path.stem, path.name)
    try:
        return RULES[rule_id](master)
    except (ET.ParseError, ValueError) as exc:
        return False, "could not check: %s does not read as SVG (%s)" % (master.name, str(exc)[:70])
