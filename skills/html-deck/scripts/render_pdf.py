#!/usr/bin/env python3
"""Renders an HTML deck (build_deck.py) to a PDF, one 1920x1080 page per
slide, and optionally one PNG per page to look at.

  uv run --with playwright python render_pdf.py <deck.html> <out.pdf> [--png <folder>]

Inside the Mac app `nodejam-print` is on PATH and prints with the app's own
Chromium, no Playwright needed. Elsewhere it uses headless Chromium through
Playwright; the browser lives in Playwright's own cache (~/.cache/ms-playwright),
never in a project folder; install it once with
`uv run --with playwright playwright install chromium`.
"""

import argparse
import os
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("deck")
    parser.add_argument("out")
    parser.add_argument("--png", help="also write one PNG per page into this folder")
    args = parser.parse_args()
    tool = shutil.which("nodejam-print")
    if tool:
        shots = ["--shots", os.path.abspath(args.png)] if args.png else []
        return subprocess.run([tool, os.path.abspath(args.deck), os.path.abspath(args.out)] + shots).returncode
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright is missing: run this with `uv run --with playwright python render_pdf.py ...`", file=sys.stderr)
        return 2
    url = "file://" + os.path.abspath(args.deck)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto(url, wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        broken = page.evaluate("""[...document.images].filter(i => i.getAttribute('src') && !(i.complete && i.naturalWidth))
                                  .map(i => i.getAttribute('src'))""")
        count = page.evaluate("document.querySelectorAll('section.slide').length")
        page.pdf(path=args.out, width="1920px", height="1080px", print_background=True, prefer_css_page_size=True)
        if args.png:
            os.makedirs(args.png, exist_ok=True)
            for index, slide in enumerate(page.query_selector_all("section.slide"), 1):
                slide.screenshot(path=os.path.join(args.png, "p-%02d.png" % index))
        browser.close()
    print("wrote %s (%d pages)" % (args.out, count))
    for src in broken:
        print("  picture did not load: %s" % src)
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
