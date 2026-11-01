#!/usr/bin/env python3
"""Report or remove a listed reference that nothing in the text cites.

    python3 repair_refs.py report.docx            report them; exit 2 when there are any
    python3 repair_refs.py report.docx --remove   take them out of the list; exit 0 when it is clean

The rule is the pack's own, skills/_checks/academic_style.py, which is the same code the grader
runs for APA-REF-CITED: one source of truth for what counts as an uncited entry. The model runs
this instead of reading the list by eye.

A numbered (Vancouver) list is reported the same way, by number, but never edited here: taking an
entry out of a numbered list leaves a gap and every later number in the text wrong. Rebuild it with
scripts/vancouver_create.py, which numbers the sources again from the text.
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE / "_checks"))

import academic_style  # noqa: E402  (the loader finds the rule in the repo checks dir)


def remove_entries(path, entries):
    """Take the uncited entries out of the reference list and save the file."""
    from docx import Document

    wanted = [e.strip() for e in entries]
    document = Document(str(path))
    removed = 0
    for paragraph in list(document.paragraphs):
        text = paragraph.text.strip()
        if text and text in wanted:
            paragraph._element.getparent().remove(paragraph._element)
            removed += 1
    document.save(str(path))
    return removed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--remove", action="store_true",
                    help="take the uncited entries out of the list instead of only reporting them")
    a = ap.parse_args()

    path = Path(a.file)
    if not path.is_file():
        print("no %s" % path)
        return 1
    if academic_style.is_vancouver(path):
        numbered = academic_style.uncited_numbers(path)
        if not numbered:
            print("every listed reference is cited")
            return 0
        for number, text in numbered:
            print("listed but not cited: [%d] %s" % (number, text))
        print("a numbered list is not edited in place: take the source out of the spec and rebuild with "
              "scripts/vancouver_create.py, which numbers the rest again")
        return 2
    entries = academic_style.uncited_entries(path)
    if not entries:
        print("every listed reference is cited")
        return 0
    for entry in entries:
        print("listed but not cited: %s" % entry)
    if not a.remove:
        print("%d entr%s: run again with --remove to take them out of the list"
              % (len(entries), "y" if len(entries) == 1 else "ies"))
        return 2
    removed = remove_entries(path, entries)
    print("removed %d of %d from %s" % (removed, len(entries), path.name))
    left = academic_style.uncited_entries(path)
    if left:
        for entry in left:
            print("still listed but not cited: %s" % entry)
        return 2
    print("every listed reference is cited")
    return 0


if __name__ == "__main__":
    sys.exit(main())
