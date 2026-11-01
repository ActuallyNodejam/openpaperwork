#!/usr/bin/env python3
"""Show or set the title and language of a .docx, .pptx or .xlsx file, in place.

Usage:
  office_properties.py FILE                      print the current properties as JSON
  office_properties.py FILE --title "Q3 review"  set the title
  office_properties.py FILE --language en-GB     set the language

Every delivered file needs a title: a screen reader announces it, and an exported PDF takes its
document title from it. Use this after editing a file whose create step you did not run.
"""
import argparse
import json
import sys


def main(argv=None):
    ap = argparse.ArgumentParser(description="Show or set Office file title and language.")
    ap.add_argument("file")
    ap.add_argument("--title")
    ap.add_argument("--language")
    args = ap.parse_args(argv)
    ext = args.file.lower().rsplit(".", 1)[-1]
    if ext == "docx":
        from docx import Document
        doc = Document(args.file)
        props, save = doc.core_properties, doc.save
    elif ext == "pptx":
        from pptx import Presentation
        doc = Presentation(args.file)
        props, save = doc.core_properties, doc.save
    elif ext == "xlsx":
        from openpyxl import load_workbook
        doc = load_workbook(args.file)
        props, save = doc.properties, doc.save
    else:
        print(json.dumps({"ok": False, "error": "unsupported file type"}))
        return 1
    if args.title is not None:
        props.title = args.title
    if args.language is not None:
        props.language = args.language
    if args.title is not None or args.language is not None:
        save(args.file)
    print(json.dumps({"ok": True, "file": args.file, "title": props.title, "language": props.language}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
