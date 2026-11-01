#!/usr/bin/env python3
"""DECK-FILL, measured on the rendered page.

Renders the deck in Chromium at 1920x1080 one page at a time, rasteres the body zone (y 200 to 968)
into a 12x16 grid, and reports per page the share of that zone covered by visible content and
whether the lower half (y 584 to 968) is empty. Boxes are elements that carry their own text or
draw something; an svg frame with nothing drawn in it is not content. Thresholds come from house-deck.html,
which must pass every page. It does not care which builder made the deck.

    python3 measure_fill.py <deck.html> [--shots <dir>]
"""
import argparse
import json
import sys
from pathlib import Path

BODY_TOP, BODY_BOTTOM = 200, 968
MID = (BODY_TOP + BODY_BOTTOM) // 2


def _contains(a, b, slack=2.0):
    """A nested box is inside its parent, which is not a collision."""
    return (a["t"] <= b["t"] + slack and a["b"] >= b["b"] - slack
            and a["l"] <= b["l"] + slack and a["r"] >= b["r"] - slack)


def _bounds(rows, slack=2.0):
    """(boxes reaching past the footer line, overlapping pairs that are not nested)."""
    crosses = sum(1 for b in rows if b["b"] > BODY_BOTTOM + 1)
    overlaps = 0
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            a, b = rows[i], rows[j]
            if _contains(a, b, slack) or _contains(b, a, slack):
                continue
            w = min(a["r"], b["r"]) - max(a["l"], b["l"])
            h = min(a["b"], b["b"]) - max(a["t"], b["t"])
            if w > 2 and h > 2:
                overlaps += 1
    return crosses, overlaps


def measure(path, shots=None):
    from playwright.sync_api import sync_playwright

    pages = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto(Path(path).resolve().as_uri())
        slides = page.query_selector_all("section.slide") or page.query_selector_all("section.page")
        if shots:
            Path(shots).mkdir(parents=True, exist_ok=True)
        for i, slide in enumerate(slides, 1):
            if shots:
                slide.screenshot(path=str(Path(shots) / ("p%02d.png" % i)))
            boxes = page.evaluate(
                """(el) => {
                    const out = [];
                    const walk = (node) => {
                        for (const c of node.children) {
                            const s = getComputedStyle(c);
                            if (s.display === 'none' || s.visibility === 'hidden' || parseFloat(s.opacity) === 0) continue;
                            const r = c.getBoundingClientRect();
                            const hasText = Array.from(c.childNodes).some(n => n.nodeType === 3 && n.textContent.trim());
                            const graphic = ['IMG','SVG','RECT','TEXT','CANVAS'].includes(c.tagName.toUpperCase());
                            const drawn = c.tagName.toUpperCase() !== 'SVG' ||
                                !!c.querySelector('rect,circle,ellipse,line,path,polyline,polygon,text,image,use');
                            if ((hasText || graphic) && drawn && r.width > 0 && r.height > 0) {
                                const host = el.getBoundingClientRect();
                                out.push({t: r.top - host.top, b: r.bottom - host.top, l: r.left - host.left, r: r.right - host.left});
                            }
                            walk(c);
                        }
                    };
                    walk(el);
                    return out;
                }""", slide)
            rows = [b for b in boxes if b["b"] > BODY_TOP and b["t"] < BODY_BOTTOM]
            crosses, overlaps = _bounds(rows)
            if not rows:
                pages.append({"page": i, "share": 0.0, "lower": 0.0, "bottom": 0,
                              "crosses": 0, "overlaps": 0})
                continue
            # area, not span: raster the band and count the cells any box touches
            COLS, ROWS = 12, 16
            cw = 1920.0 / COLS
            ch = (BODY_BOTTOM - BODY_TOP) / float(ROWS)
            cells = set()
            lower_cells = set()
            for b in rows:
                t = max(b["t"], BODY_TOP); bo = min(b["b"], BODY_BOTTOM)
                l = max(b["l"], 0.0); r = min(b["r"], 1920.0)
                if bo <= t or r <= l:
                    continue
                for cy in range(int((t - BODY_TOP) // ch), int((bo - BODY_TOP - 1e-6) // ch) + 1):
                    for cx in range(int(l // cw), int((r - 1e-6) // cw) + 1):
                        cells.add((cx, cy))
                        if (BODY_TOP + (cy + 0.5) * ch) > MID:
                            lower_cells.add((cx, cy))
            bottom = min(BODY_BOTTOM, max(b["b"] for b in rows))
            lower_total = ROWS - sum(1 for cy in range(ROWS) if (BODY_TOP + (cy + 0.5) * ch) > MID)
            pages.append({"page": i,
                          "share": round(len(cells) / float(COLS * ROWS), 3),
                          "lower": round(len(lower_cells) / float(COLS * lower_total), 3),
                          "bottom": int(bottom), "crosses": crosses, "overlaps": overlaps})
        browser.close()
    return pages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("deck")
    ap.add_argument("--shots")
    ap.add_argument("--json")
    a = ap.parse_args()
    pages = measure(a.deck, a.shots)
    for p in pages:
        print("page %d  share %.2f  lower half %.2f  content bottom %d" % (p["page"], p["share"], p["lower"], p["bottom"]))
    if a.json:
        Path(a.json).write_text(json.dumps(pages))
    return 0


if __name__ == "__main__":
    sys.exit(main())
