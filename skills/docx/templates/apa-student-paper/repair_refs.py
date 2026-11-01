#!/usr/bin/env python3
"""Repair an APA reference list through the builder, so the rule is enforced by the tool.

    python3 repair_refs.py draft.docx spec.json

Reads the draft, pulls the body and the reference list out of it, and writes the spec the APA
builder takes. Correct the reference list in the spec, then run build_apa.py: it refuses to write a
paper that lists an entry with no source, or an entry the body never cites, so the repair cannot
end with a list the body does not support.

The draft is read with the app's own Python, which is the one that carries python-docx.
"""
import json
import re
import sys
from pathlib import Path

from docx import Document  # noqa: E402

HEADINGS = ("references", "reference list", "works cited")


def read_draft(path):
    doc = Document(str(path))
    paras = [p.text.strip() for p in doc.paragraphs]
    ref_at = None
    for i, text in enumerate(paras):
        if text.lower().strip(": ") in HEADINGS:
            ref_at = i
            break
    if ref_at is None:
        body, refs = paras, []
    else:
        body, refs = paras[:ref_at], [p for p in paras[ref_at + 1:] if p]
    title = next((p for p in body if p), "")
    body = [p for p in body if p and p != title]
    return title, body, refs


def cite_key(entry):
    entry = re.sub(r"^\s*[\[\d\]\.\)\s]+", "", entry.strip())   # drop a numbering marker
    surname = re.match(r"^([A-Z][A-Za-z'\-]+)", entry)
    year = re.search(r"\((\d{4})\)", entry)
    return (surname.group(1) if surname else "", year.group(1) if year else "")


def main():
    if len(sys.argv) < 3:
        raise SystemExit("usage: repair_refs.py draft.docx spec.json")
    draft, out = Path(sys.argv[1]), Path(sys.argv[2])
    title, body, refs = read_draft(draft)
    spec = {
        "title": title or "Report",
        "author": "", "affiliation": "", "course": "", "instructor": "", "date": "",
        "body": [{"paragraph": p} for p in body],
        "references": refs,
    }
    out.write_text(json.dumps(spec, indent=1))
    print("%s -> %s (%d body paragraphs, %d references)" % (draft, out, len(body), len(refs)))
    for r in refs:
        surname, year = cite_key(r)
        cited = any(surname and surname in p and (not year or year in p) for p in body)
        print("  %-8s %s %s" % ("cited" if cited else "UNCITED", surname or "?", r[:60]))


if __name__ == "__main__":
    main()
