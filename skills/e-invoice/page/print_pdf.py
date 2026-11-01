#!/usr/bin/env python3
"""Print one HTML page to an A4 PDF with Playwright.

The page builder calls this when nodejam-print is not there. Run it by hand the same way:

    uv run --with playwright python print_pdf.py page.html page.pdf
"""
import sys
from pathlib import Path


def main():
    src, out = sys.argv[1], sys.argv[2]
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page()
        page.goto(Path(src).resolve().as_uri())
        page.pdf(path=out, format="A4", print_background=True)
        browser.close()
    print("printed %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
