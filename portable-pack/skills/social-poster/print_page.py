#!/usr/bin/env python3
"""Print the poster page with Playwright's Chromium, for an agent with no app around it.

The same job and the same answer as the app's print command, so poster.py reads both alike:

    python3 print_page.py <in.html> [<out.pdf>] [--shots DIR] [--eval FILE.js] [--width W] [--height H] [--frames N]

Writes out.pdf (CSS @page wins, backgrounds on), p-01.png ... one per .slide into --shots, and prints the
--eval script's result as JSON. With --frames N the script is a function of the frame number that parks
the page on it, and f-00000.png onwards are taken in one page load.
"""
import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("pdf", nargs="?")
    parser.add_argument("--shots")
    parser.add_argument("--eval", dest="script")
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1350)
    parser.add_argument("--frames", type=int, default=0)
    args = parser.parse_args()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is not installed: pip install playwright, then playwright install chromium", file=sys.stderr)
        return 2
    page_url, _, suffix = args.input.partition("?")
    url = Path(page_url).resolve().as_uri() + (("?" + suffix) if suffix else "")
    script = Path(args.script).read_text(encoding="utf-8") if args.script else None
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--no-sandbox", "--allow-file-access-from-files", "--autoplay-policy=no-user-gesture-required"])
        page = browser.new_page(viewport={"width": args.width, "height": args.height})
        page.goto(url, wait_until="load")
        page.evaluate("document.fonts.ready.then(() => true)")
        shots = Path(args.shots) if args.shots else None
        if shots:
            shots.mkdir(parents=True, exist_ok=True)
        result = None
        if args.frames:
            for n in range(args.frames):
                page.evaluate(script, n)
                page.screenshot(path=str(shots / ("f-%05d.png" % n)))
        else:
            if script:
                result = page.evaluate(script)
            if shots:
                slides = page.query_selector_all(".slide") or [None]
                for i, slide in enumerate(slides, 1):
                    target = slide or page
                    target.screenshot(path=str(shots / ("p-%02d.png" % i)))
        if args.pdf:
            # no margins and backgrounds on, as the app prints
            page.pdf(path=args.pdf, print_background=True, prefer_css_page_size=True,
                     width="%dpx" % args.width, height="%dpx" % args.height,
                     margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
        browser.close()
    if result is not None:
        print(result if isinstance(result, str) else json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
