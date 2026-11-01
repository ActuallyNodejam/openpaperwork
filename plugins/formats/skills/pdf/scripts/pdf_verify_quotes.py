#!/usr/bin/env python3
"""Check literal quotes against cited PDF text layers; never proves completeness."""
import argparse
import json
import re
import unicodedata
from pathlib import Path
from pypdf import PdfReader


def normalized(value):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value)).casefold()


def verify(source, entries):
    pages = [page.extract_text() or "" for page in PdfReader(source).pages]
    if not isinstance(entries, list) or not entries:
        raise ValueError("manifest must be a nonempty list of quote records")
    results = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("each record must be an object")
        quote, cited = entry.get("quote"), entry.get("pages")
        if not isinstance(quote, str) or not normalized(quote):
            raise ValueError("quote must be nonempty text; do not invent quotes for uncaptained images")
        if not isinstance(cited, list) or not cited or any(type(n) is not int or not 1 <= n <= len(pages) for n in cited):
            raise ValueError("pages must be nonempty 1-based page numbers within the PDF")
        found = [n for n in cited if normalized(quote) in normalized(pages[n-1])]
        results.append({"id": entry.get("id"), "pages": cited, "matched_pages": found,
                        "status": "matched" if found else "needs_review",
                        "empty_text_pages": [n for n in cited if not pages[n-1].strip()]})
    return {"ok": all(r["status"] == "matched" for r in results), "checked": len(results),
            "results": results, "scope": "Whitespace/Unicode/case-normalized literal containment only; not visual verification, semantic support or complete coverage"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf")
    parser.add_argument("manifest", help='JSON list of {"id":..., "pages":[1], "quote":"literal words"}')
    args = parser.parse_args()
    try:
        result = verify(args.pdf, json.loads(Path(args.manifest).read_text(encoding="utf-8")))
    except (ValueError, OSError) as error:
        print(json.dumps({"ok": False, "error": str(error)}))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
