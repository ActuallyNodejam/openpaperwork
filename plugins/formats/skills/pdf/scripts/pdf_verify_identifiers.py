#!/usr/bin/env python3
"""Reconcile literal identifier sets against a PDF text layer, preserving gaps."""
import argparse
import json
import re
from pathlib import Path

from pypdf import PdfReader


def verify(source, pattern, identifiers=None, pages=None):
    reader = PdfReader(source)
    selected = list(range(1, len(reader.pages) + 1)) if pages is None else pages
    if not selected or any(type(page) is not int or not 1 <= page <= len(reader.pages) for page in selected):
        raise ValueError("pages must be nonempty 1-based page numbers within the PDF")
    # Match complete tokens, not 0101 inside 0101a or a dimension containing it.
    expression = re.compile(r"(?<![\w])(?:" + pattern + r")(?![\w])")
    if expression.match(""):
        raise ValueError("pattern must not match empty text")
    labels = {}
    empty = []
    for number in selected:
        text = reader.pages[number - 1].extract_text() or ""
        if not text.strip():
            empty.append(number)
        for match in expression.finditer(text):
            labels.setdefault(match.group(), set()).add(number)
    found = sorted(labels)
    result = {
        "source_count": len(found),
        "source_identifiers": found,
        "source_pages": {label: sorted(labels[label]) for label in found},
        "empty_text_pages": empty,
        "scope": "Literal text-layer set only. Review the pattern, dimensions, title blocks, image-only labels and spatial meaning separately. No inferred ranges.",
    }
    if identifiers is None:
        return {**result, "ok": bool(found) and not empty}
    if not isinstance(identifiers, list) or not identifiers or any(not isinstance(label, str) or not label for label in identifiers):
        raise ValueError("manifest must be a nonempty JSON list of literal identifier strings; preserve leading zeros")
    claimed = set(identifiers)
    extra = sorted(claimed - set(found))
    missing = sorted(set(found) - claimed)
    duplicates = sorted(label for label in claimed if identifiers.count(label) > 1)
    return {**result, "claimed_count": len(claimed), "extra": extra, "missing": missing,
            "duplicates": duplicates, "ok": bool(found) and not empty and not extra and not missing and not duplicates}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf")
    parser.add_argument("--pattern", required=True, help="Regex matching complete literal IDs for this drawing; exclude dimensions and drawing numbers")
    parser.add_argument("--manifest", help="JSON list of the actual literal IDs intended for the answer or exported from its file")
    parser.add_argument("--pages", type=int, nargs="+")
    args = parser.parse_args()
    try:
        identifiers = json.loads(Path(args.manifest).read_text()) if args.manifest else None
        result = verify(args.pdf, args.pattern, identifiers, args.pages)
    except (ValueError, OSError, re.error) as error:
        print(json.dumps({"ok": False, "error": str(error)}))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
