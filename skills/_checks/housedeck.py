#!/usr/bin/env python3
"""House-deck rules read off the produced HTML, for grade.py.

check(rule_id, path, case, stage) -> (passed, evidence). Standard library only.

Rules:
  DECK-PAGES   the deck has the number of pages the request asks for, each in the
               house page container
  DECK-TYPE    no text is set below the house floor of 18px, and body copy is 22px
               or more
  DECK-ACCENT  one accent hue at most beyond the neutral ground and ink, taken from
               the case data
  DECK-TRACE   every number printed on the pages appears in the case data
"""
import colorsys
import itertools
import re
import sys
from pathlib import Path
import os
import subprocess
import tempfile
import shutil


import json

# The rule code lives in the skills tree, so a pack's check runs where the pack runs. When this file
# sits in a checkout it can also see the rest of the repository (the library's own check modules load
# these files from here); inside a sandbox only the skills tree is there, and the rules that need
# more say so instead of failing the file.
def _repo_root():
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "standards/checks").is_dir():
            return parent
    for parent in here.parents:
        if (parent / "skills").is_dir():
            return parent
    return here.parents[2]


ROOT = _repo_root()

def _helper(name, nested=None):
    """A script the rule runs: beside the rule, or wherever this checkout keeps the checks."""
    here = Path(__file__).resolve().parent
    candidates = [here / name]
    if nested:
        candidates.append(here.parent / nested)
        candidates.append(ROOT / "skills" / nested)
    candidates.append(ROOT / "standards/checks" / name)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]



def _hsv(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return colorsys.rgb_to_hsv(r, g, b)


def _same_family(colour, accent, hue_tol=0.035):
    """Tints and shades of the accent keep its hue; foreign colours do not."""
    h1, s1, _ = _hsv(colour)
    h2, s2, _ = _hsv(accent)
    if s1 < 0.15:
        return True
    dh = min(abs(h1 - h2), 1 - abs(h1 - h2))
    return dh <= hue_tol


NEUTRAL = ("#ffffff", "#fff", "#000000", "#000", "#f2f2f2", "#f4f0eb", "#e3dcd3",
           "#12100e", "#6b6259", "#f7f5f2", "#eae6e1", "transparent", "none",
           "currentcolor", "inherit")
FLOOR = 18
BODY = 22


def _strip_assets(html):
    """Inline images and fonts carry numbers by accident; they are not page text."""
    html = re.sub(r"&#?[0-9A-Za-z]+;", " ", html)   # an arrow is not a figure
    html = re.sub(r"data:[a-z/+.-]+;base64,[A-Za-z0-9+/=]+", " ", html)
    html = re.sub(r"[A-Za-z0-9+/]{40,}={0,2}", " ", html)
    return html


def _derived_flat(values):
    """What a summary may legitimately print: the data, its differences and its sums."""
    nums = []
    for v in values:
        try:
            nums.append(float(str(v).replace(".", "").replace(",", ".")))
        except ValueError:
            pass
    out = set()
    for a, b in itertools.permutations(nums, 2):
        for n in (a - b, a + b):
            if n >= 0:
                out.add("%.2f" % n)
                out.add(str(int(n)) if float(n).is_integer() else ("%.2f" % n).replace(".", ","))
        if b:
            share = a / b * 100.0
            if 0 <= share <= 100.0001:
                out.add("%.1f" % share)
                out.add("%.0f" % share)
                out.add(("%.1f" % share).replace(".", ","))
    for n in nums:
        out.add(str(int(n)) if float(n).is_integer() else "%.2f" % n)
    return out


PAGE_TOKENS = ("page", "slide", "sheet", "deck-page")


def _pages(html):
    """Every element whose class names one of the house page words."""
    out = []
    pattern = re.compile(r"<(section|div|article)[^>]*class=\"([^\"]*)\"[^>]*>(.*?)</\1>", re.S | re.I)
    for m in pattern.finditer(html):
        if set(m.group(2).lower().split()) & set(PAGE_TOKENS):
            out.append(m.group(3))
    return out


def _sizes(html):
    """The sizes the page actually uses, with var() resolved through the token table."""
    tokens = {}
    for m in re.finditer(r"(--[a-z0-9-]+)\s*:\s*([0-9.]+)\s*(px|pt)", html, re.I):
        v = float(m.group(2)) * (1.333 if m.group(3).lower() == "pt" else 1.0)
        tokens[m.group(1).lower()] = v

    def resolve(value):
        value = value.strip()
        var = re.match(r"var\(\s*(--[a-z0-9-]+)\s*(?:,\s*([0-9.]+)\s*(px|pt))?\s*\)", value, re.I)
        if var:
            if var.group(1).lower() in tokens:
                return tokens[var.group(1).lower()]
            if var.group(2):
                return float(var.group(2)) * (1.333 if var.group(3).lower() == "pt" else 1.0)
            return None
        lit = re.match(r"([0-9.]+)\s*(px|pt)", value, re.I)
        if lit:
            return float(lit.group(1)) * (1.333 if lit.group(2).lower() == "pt" else 1.0)
        return None

    out = []
    for m in re.finditer(r"font-size\s*:\s*([^;\}\n]+)", html, re.I):
        v = resolve(m.group(1))
        if v is not None and v >= 8:      # below 8 is a hairline or an icon, not text
            out.append(v)
    return out


def _build_from_json(path):
    """A deck may be handed over as the JSON the builder takes; build it, then judge the HTML."""
    import json as _json
    import subprocess as _sp
    import sys as _sys
    import tempfile
    builder = _helper("build_deck.py", "html-deck/scripts/build_deck.py")
    if not builder.is_file():
        return None, "builder missing: %s" % builder
    out = Path(tempfile.mkdtemp()) / "deck.html"
    r = _sp.run([_sys.executable, str(builder), str(path), str(out)], capture_output=True, text=True)
    if r.returncode != 0:
        return None, "builder failed: %s" % (r.stderr or r.stdout).strip()[:120]
    return out, "built from deck.json"


FILL_MINIMUM = {
    "cover": {"big": 1, "sub": 1},
    "numbers": {"stat": 2, "chart": 1},
    "chart-bullets": {"bar": 2, "bullet": 2},
    "table": {"row": 3},
    "timeline": {"step": 3},
    "closing": {"big": 1, "sub": 1},
}


def _page_type(tag):
    """cover from class="slide cover", or the data-type when the builder wrote one."""
    m = re.search(r'data-type="([^"]+)"', tag)
    if m:
        return m.group(1)
    m = re.search(r'class="([^"]*)"', tag)
    if not m:
        return ""
    for token in m.group(1).split():
        if token != "slide":
            return token
    return ""



def _fill_counts(html):
    pages = []
    for m in re.finditer(r'<section class="slide[^"]*"(?: data-type="([^"]*)")?(.*?)</section>',
                         html, re.S):
        dtype, body = _page_type(m.group(0)), m.group(2)
        pages.append((dtype, {
            "big": len(re.findall(r'class="big"', body)),
            "sub": len(re.findall(r'class="sub"', body)),
            "stat": len(re.findall(r'class="stat"', body)),
            "chart": len(re.findall(r"<svg", body)),
            "bar": len(re.findall(r"<rect", body)),
            "bullet": len(re.findall(r"<li", body)),
            "row": len(re.findall(r"<tr", (re.search(r"<tbody>(.*?)</tbody>", body, re.S)
                                             or re.match("", "")).group(0) if "<tbody>" in body else body)),
            "step": len(re.findall(r'class="step"', body)),
        }))
    return pages


def check_parts(html):
    """The per-type part counts, kept as their own rule."""
    pages = _fill_counts(html)
    if not pages:
        return False, "no house pages found"
    short = []
    for i, (dtype, counts) in enumerate(pages, 1):
        need = FILL_MINIMUM.get(dtype)
        if need is None:
            short.append("page %d: unknown type %s" % (i, dtype or "none"))
            continue
        missing = [k for k, n in need.items() if counts.get(k, 0) < n]
        if missing:
            short.append("page %d (%s) missing %s" % (i, dtype, ", ".join(missing)))
    if short:
        return False, "; ".join(short[:4])
    return True, "every page carries what its type calls for"



FILL_MIN_SHARE = 0.12          # house pages measure 0.19 to 0.85; run4 pages 0.00 to 0.33
FILL_MIN_LOWER = 0.10          # house pages 0.18 to 0.85; run4 pages 0.00 on every page
FILL_JS = _helper("fill-eval.js")
FILL_VENV = "/tmp/fillvenv/bin/python"     # the grader fallback, installed on the box


def _fill_cmd(cmd, env=None):
    """Run a measurement command and report exactly why it failed, instead of nothing."""
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT), env=env)
    return r


def _fill_via_app(path):
    """The app's own Chromium through nodejam-print: the in-turn route."""
    where = os.environ.get("NODEJAM_PRINT")
    if not where or not os.path.exists(where):
        found = list((Path.home() / ".config").glob("*/profile/desktop/print.json"))
        where = str(found[0]) if found else None
    printer = shutil.which("nodejam-print")
    if not (where and os.path.exists(where) and printer and FILL_JS.is_file()):
        return None, "app route unavailable"
    r = _fill_cmd([printer, str(path), "--eval", str(FILL_JS), "--width", "1920", "--height", "1080"],
                  env={**os.environ, "NODEJAM_PRINT": where})
    if r.returncode != 0 or not r.stdout.strip():
        return None, "nodejam-print rc %d: %s" % (r.returncode, (r.stderr or r.stdout).strip()[-120:])
    try:
        return json.loads(json.loads(r.stdout.strip().splitlines()[-1])), "app"
    except Exception as exc:
        return None, "app output unreadable: %s" % exc


def _fill_via_playwright(path):
    """The grader fallback at FILL_VENV, when the app is not running."""
    runner = Path(FILL_VENV)
    measurer = _helper("measure_fill.py")
    if not runner.exists():
        return None, "no fallback interpreter at %s" % FILL_VENV
    if not measurer.is_file():
        return None, "no measurement script at %s" % measurer
    out = Path(tempfile.mkdtemp()) / "fill.json"
    r = _fill_cmd([str(runner), str(measurer), str(path), "--json", str(out)])
    if not out.is_file():
        return None, "fallback rc %d: %s" % (r.returncode, (r.stderr or r.stdout).strip()[-160:])
    try:
        return json.loads(out.read_text()), "fallback"
    except Exception as exc:
        return None, "fallback output unreadable: %s" % exc


def check_fill(path):
    """The rendered page: content that covers too little of the body fails, page by page."""
    pages, why = _fill_via_app(path)
    if pages is None:
        pages, why2 = _fill_via_playwright(path)
        why = "%s; %s" % (why, why2)
    if pages is None:
        return False, "fill not measured: %s" % why
    short = []
    for p in pages:
        why = []
        if p.get("share", 0) < FILL_MIN_SHARE:
            why.append("content covers %.2f of the body" % p.get("share", 0))
        if p.get("lower", 0) < FILL_MIN_LOWER:
            why.append("lower half empty")
        if why:
            short.append("page %d: %s" % (p.get("page"), " and ".join(why)))
    if short:
        return False, "; ".join(short[:4])
    return True, "%d pages carry content across the body" % len(pages)

def check_bounds(path):
    """DECK-BOUNDS: nothing crosses the footer rule and nothing overlaps."""
    pages, why = _fill_via_app(path)
    if pages is None:
        pages, why2 = _fill_via_playwright(path)
        why = "%s; %s" % (why, why2)
    if pages is None:
        return False, "bounds not measured: %s" % why
    bad = []
    for p in pages:
        if p.get("crosses"):
            bad.append("page %d: %d box(es) reach past the footer line" % (p.get("page"),
                                                                          p.get("crosses")))
        if p.get("overlaps"):
            bad.append("page %d: %d overlapping box pair(s)" % (p.get("page"), p.get("overlaps")))
    if bad:
        return False, "; ".join(bad[:4])
    return True, "%d pages hold inside the body and nothing overlaps" % len(pages)


def check(rule_id, path, case, stage):
    path = Path(path)
    if path.suffix.lower() == ".json":
        built, why = _build_from_json(path)
        if built is None:
            return False, why
        path = built
    html = path.read_text(errors="ignore")
    truth = case.get("truth") or {}
    pages = _pages(html) or re.findall(r'class="[^"]*\bslide\b[^"]*"', html, re.I)
    body = " ".join(pages) if pages else html

    if rule_id == "DECK-PAGES":
        want = int(truth.get("pages") or 0)
        got = len(pages)
        if not want:
            return (got > 0, "%d pages" % got)
        return (got == want, "%d of %d pages" % (got, want))

    if rule_id == "DECK-TYPE":
        sizes = _sizes(html)
        if not sizes:
            return False, "no font sizes found in the file"
        small = [s for s in sizes if s < FLOOR]
        if small:
            return False, "text below the %dpx floor: %s" % (FLOOR, ", ".join("%.0fpx" % s for s in sorted(set(small))[:4]))
        body_sizes = [s for s in sizes if s >= BODY]
        return (bool(body_sizes), "floor held; largest sizes %s" % ", ".join("%.0fpx" % s for s in sorted(set(sizes))[-3:]))

    if rule_id == "DECK-ACCENT":
        hexes = set(h.lower() for h in re.findall(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b", html))

        def low_chroma(h):
            """A ground or an ink is a low-chroma grey; an accent carries the hue."""
            h = h.lstrip("#")
            if len(h) == 3:
                h = "".join(c * 2 for c in h)
            r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
            hi, lo = max(r, g, b), min(r, g, b)
            return (hi - lo) <= 60 or hi == 0   # grounds, inks and blue-greys stay neutral

        accents = sorted(h for h in hexes if h not in NEUTRAL and not low_chroma(h))
        allowed = [a.lower() for a in (truth.get("accents") or [])]
        extra = [a for a in accents
                 if allowed and not any(a == x or _same_family(a, x) for x in allowed)]
        if not allowed:
            return (len(accents) <= 1, "accents used: %s" % (", ".join(accents) or "none"))
        return (not extra, "accent %s only" % ", ".join(allowed) if not extra
                else "colours outside the brand kit: %s" % ", ".join(extra[:4]))

    if rule_id == "DECK-FILL":
        return check_fill(path)

    if rule_id == "DECK-BOUNDS":
        return check_bounds(path)

    if rule_id == "DECK-PARTS":
        return check_parts(html)

    if rule_id == "DECK-TRACE":
        allowed = set()
        for v in (truth.get("values") or []):
            allowed |= set(re.findall(r"\d[\d.,]*\d|\d", str(v)))
        zones = re.findall(r'class="[^"]*\bnum\b[^"]*"[^>]*>(.*?)<', body, re.S)
        scanned = (" ".join(zones) if zones
                   else _strip_assets(re.sub(r"<[^>]+>", " ", body)))
        tokens = set(re.findall(r"\d[\d.,]*\d|\d", scanned))
        pages = int(truth.get("pages") or 0)
        structural = set()
        for n in range(1, pages + 1):          # page labels are the deck's own furniture
            structural |= {str(n), "%02d" % n, "%d/%d" % (n, pages)}
        structural |= {str(v) for v in (truth.get("axis") or [])}
        structural |= _derived(truth.get("values") or [], _data_file(case, path))
        def tick(t):
            try:
                v = float(t.replace(",", "."))
            except ValueError:
                return False
            return v <= 5.0 or (v <= 70 and abs(v % 10) < 1e-9)   # the two axes the case declares
        extra = sorted(t for t in tokens if t not in allowed and t not in structural
                       and not tick(t) and t.rstrip(".,") not in allowed)
        return (not extra, "every number on the pages traces to the case data" if not extra
                else "not in the data: %s" % ", ".join(extra[:6]))

    return None, "unknown rule"


if __name__ == "__main__":
    ok, why = check(sys.argv[1], sys.argv[2], {}, "first")
    print({"rule": sys.argv[1], "passed": ok, "evidence": why})
    sys.exit(0 if ok else 1)


def _derived_from_data(data):
    """Sums, differences and percentage changes the data table itself declares."""
    out = set()

    def add(v):
        if v is None:
            return
        if abs(v - round(v)) < 1e-9:
            out.add(str(int(round(v))))
        out.add("%.1f" % v)
        out.add(("%.1f" % v).replace(".", ","))
        out.add("%.2f" % v)

    def pairs(node):
        if not isinstance(node, dict):
            return
        nums = {k: v for k, v in node.items() if isinstance(v, (int, float))}
        for a, b in itertools.combinations(sorted(nums), 2):
            add(nums[a] - nums[b])
            add(nums[b] - nums[a])
            if nums[a]:
                add(100.0 * (nums[b] - nums[a]) / nums[a])
        kids = {k: v for k, v in node.items() if isinstance(v, dict)}
        for x, y in itertools.combinations(sorted(kids), 2):
            for k in sorted(set(kids[x]) & set(kids[y])):
                if isinstance(kids[x][k], (int, float)) and isinstance(kids[y][k], (int, float)):
                    add(kids[y][k] - kids[x][k])
        for v in kids.values():
            pairs(v)

    def sums(node):
        if not isinstance(node, dict):
            return
        vals = [v for v in node.values() if isinstance(v, (int, float))]
        if 2 <= len(vals) <= 5:
            for r in range(2, len(vals) + 1):
                for combo in itertools.combinations(vals, r):
                    add(sum(combo))
        for v in node.values():
            sums(v)

    pairs(data)
    sums(data)
    return out


def _data_file(case, path):
    for cand in (Path(path).parent / "deck-data.json", Path(path).parent / "data.json"):
        if cand.is_file():
            return cand
    return None


def _derived(values, data_source=None):
    """The declared derived numbers when a data table is known, else the plain value list."""
    if data_source:
        try:
            structured = _derived_from_data(json.loads(Path(data_source).read_text()))
            if structured:
                return structured
        except Exception:
            pass
    return _derived_flat(values)
