#!/usr/bin/env python3
# MIT License. Part of the Hermes docx skill.
"""Edit an existing .docx in place (or to a new file).

Subcommands:
  replace   find-and-replace text, preserving run formatting
  set-cell  set the text of a table cell
  insert    insert a paragraph before a given body paragraph index
  delete    delete a body paragraph by index
  style     apply a paragraph style to a body paragraph by index
  normalize merge adjacent runs with identical formatting
  toc       insert a Table of Contents field at a body paragraph index
  page-numbers  add "Page X of Y" (PAGE/NUMPAGES fields) to the footer

Examples:
  docx_edit.py replace in.docx --find old --replace new -o out.docx
  docx_edit.py set-cell in.docx --table 0 --row 1 --col 2 --text "42"
  docx_edit.py insert in.docx --index 3 --text "New para" --style Normal
  docx_edit.py delete in.docx --index 3
  docx_edit.py style in.docx --index 0 --style "Heading 1"
  docx_edit.py normalize in.docx -o out.docx
  docx_edit.py toc in.docx --index 1 -o out.docx
  docx_edit.py page-numbers in.docx -o out.docx

Field results (TOC entries, page numbers) are computed by Word or
LibreOffice when the document is opened, not by python-docx; until then
the fields show placeholder text.
"""
from __future__ import annotations

import argparse
import json
import re
import sys

from docx import Document

from docx_common import iter_all_paragraphs, replace_in_paragraph

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _q(tag: str) -> str:
    return f"{{{W}}}{tag}"


def cmd_replace(doc, args) -> dict:
    n = 0
    for para in iter_all_paragraphs(doc):
        n += replace_in_paragraph(para, args.find, args.replace)
    return {"replacements": n}


def cmd_set_cell(doc, args) -> dict:
    cell = doc.tables[args.table].cell(args.row, args.col)
    cell.text = args.text
    return {"table": args.table, "row": args.row, "col": args.col}


def cmd_insert(doc, args) -> dict:
    paras = doc.paragraphs
    if args.index < len(paras):
        anchor = paras[args.index]
        new_para = anchor.insert_paragraph_before(args.text, style=args.style)
    else:
        new_para = doc.add_paragraph(args.text, style=args.style)
    return {"inserted_at": args.index, "text": new_para.text}


def cmd_delete(doc, args) -> dict:
    para = doc.paragraphs[args.index]
    el = para._element
    el.getparent().remove(el)
    return {"deleted_index": args.index}


def cmd_style(doc, args) -> dict:
    doc.paragraphs[args.index].style = doc.styles[args.style]
    return {"index": args.index, "style": args.style}


def _run_format_key(r_el) -> str:
    """Canonical string for a run's w:rPr (None when absent)."""
    from lxml import etree
    rpr = r_el.find(_q("rPr"))
    return "" if rpr is None else etree.tostring(rpr).decode("utf-8")


def cmd_normalize(doc) -> dict:
    """Merge adjacent sibling runs with identical formatting."""
    merged = 0
    for para in iter_all_paragraphs(doc):
        prev = None
        for r_el in list(para._p):
            if r_el.tag != _q("r"):
                prev = None
                continue
            # only merge plain-text runs (no breaks, tabs, drawings...)
            kids = {c.tag for c in r_el} - {_q("rPr"), _q("t")}
            if kids:
                prev = None
                continue
            if (prev is not None
                    and _run_format_key(prev) == _run_format_key(r_el)):
                pt = prev.find(_q("t"))
                ct = r_el.find(_q("t"))
                if pt is None:
                    pt = prev.makeelement(_q("t"), {})
                    prev.append(pt)
                pt.text = (pt.text or "") + ((ct.text or "")
                                             if ct is not None else "")
                pt.set("{http://www.w3.org/XML/1998/namespace}space",
                       "preserve")
                r_el.getparent().remove(r_el)
                merged += 1
            else:
                prev = r_el
    return {"runs_merged": merged}


def _add_field(para, instr: str, placeholder: str) -> None:
    """Append a complex field (begin/instrText/separate/result/end)."""
    p = para._p
    for ftype, extra in (("begin", None), (None, instr),
                         ("separate", None), (None, placeholder),
                         ("end", None)):
        r = p.makeelement(_q("r"), {})
        p.append(r)
        if ftype is not None:
            fld = r.makeelement(_q("fldChar"), {_q("fldCharType"): ftype})
            r.append(fld)
        elif extra is instr:
            it = r.makeelement(_q("instrText"), {})
            it.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            it.text = instr
            r.append(it)
        else:
            t = r.makeelement(_q("t"), {})
            t.text = extra
            r.append(t)


def cmd_toc(doc, args) -> dict:
    paras = doc.paragraphs
    if args.index < len(paras):
        para = paras[args.index].insert_paragraph_before("")
    else:
        para = doc.add_paragraph("")
    _add_field(para, r' TOC \o "1-3" \h \z \u ',
               "Table of contents - open in Word/LibreOffice and update "
               "fields to populate.")
    return {"toc_inserted_at": args.index}


_PAGE_WORDS = {
    "sv": ("Sida ", " av "), "da": ("Side ", " af "), "nb": ("Side ", " av "),
    "no": ("Side ", " av "), "nn": ("Side ", " av "), "de": ("Seite ", " von "),
    "fr": ("Page ", " sur "), "es": ("Página ", " de "), "fi": ("Sivu ", " / "),
    "nl": ("Pagina ", " van "), "it": ("Pagina ", " di "), "pt": ("Página ", " de "),
}
_SV_WORDS = re.compile(r"\b(och|att|som|för|med|är|ett|det|den|av|på|inte|vi|ni|har)\b", re.I)


def guess_language(text: str) -> str | None:
    """"sv" when the text is plainly Swedish (common words and å ä ö), else None."""
    words = re.findall(r"\w+", text)
    if len(words) < 20:
        return None
    hits = len(_SV_WORDS.findall(text))
    return "sv" if hits * 10 >= len(words) and re.search("[åäöÅÄÖ]", text) else None


def doc_language(doc, text: str = "") -> str:
    """The file's language code: its declared language, else its default style, else the text itself."""
    declared = (doc.core_properties.language or "").strip()
    if declared:
        return declared.split("-")[0].lower()
    lang = doc.styles.element.find(".//" + _q("docDefaults") + "//" + _q("lang"))
    val = lang.get(_q("val")) if lang is not None else ""
    guess = guess_language(text or "\n".join(p.text for p in doc.paragraphs))
    if guess and (not val or val.lower().startswith("en")):
        return guess
    return (val or "en").split("-")[0].lower()


def set_default_language(doc, code: str) -> None:
    """Make the text's language the file's default, so Word does not mark every word as a mistake."""
    defaults = doc.styles.element.find(_q("docDefaults"))
    if defaults is None:
        return
    rpr = defaults.find(".//" + _q("rPr"))
    if rpr is None:
        return
    lang = rpr.find(_q("lang"))
    if lang is None:
        lang = rpr.makeelement(_q("lang"), {})
        rpr.append(lang)
    region = {"sv": "SE", "da": "DK", "nb": "NO", "de": "DE", "fi": "FI"}.get(code)
    lang.set(_q("val"), code + ("-" + region if region else ""))


def add_page_numbers(doc, text: str = "") -> None:
    """Footer "Page X of Y" from fields, in the file's own language, set apart from any footer text."""
    code = doc_language(doc, text)
    page, of = _PAGE_WORDS.get(code, ("Page ", " of "))
    footer = doc.sections[0].footer
    para = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    if para.text.strip():
        para.add_run("  \u00b7  ")
    para.add_run(page)
    _add_field(para, " PAGE ", "1")
    para.add_run(of)
    _add_field(para, " NUMPAGES ", "1")


def cmd_page_numbers(doc, args) -> dict:
    add_page_numbers(doc)
    return {"footer_fields": ["PAGE", "NUMPAGES"]}


def main() -> int:
    ap = argparse.ArgumentParser(description="Edit a .docx file.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("path", help="input .docx")
        p.add_argument("-o", "--output",
                       help="output path (default: overwrite input)")

    p = sub.add_parser("replace", help="find-and-replace text")
    common(p)
    p.add_argument("--find", required=True)
    p.add_argument("--replace", required=True)
    p.add_argument("--body-only", action="store_true",
                   help="skip headers/footers")

    p = sub.add_parser("set-cell", help="set table cell text")
    common(p)
    p.add_argument("--table", type=int, required=True, help="table index")
    p.add_argument("--row", type=int, required=True)
    p.add_argument("--col", type=int, required=True)
    p.add_argument("--text", required=True)

    p = sub.add_parser("insert", help="insert paragraph at body index")
    common(p)
    p.add_argument("--index", type=int, required=True)
    p.add_argument("--text", required=True)
    p.add_argument("--style", default=None)

    p = sub.add_parser("delete", help="delete body paragraph by index")
    common(p)
    p.add_argument("--index", type=int, required=True)

    p = sub.add_parser("style", help="apply style to body paragraph")
    common(p)
    p.add_argument("--index", type=int, required=True)
    p.add_argument("--style", required=True)

    p = sub.add_parser("normalize",
                       help="merge adjacent runs with identical formatting")
    common(p)

    p = sub.add_parser("toc", help="insert a TOC field (Word computes it)")
    common(p)
    p.add_argument("--index", type=int, default=0,
                   help="body paragraph index to insert before (default 0)")

    p = sub.add_parser("page-numbers",
                       help="add PAGE/NUMPAGES fields to the footer")
    common(p)

    args = ap.parse_args()
    doc = Document(args.path)

    if args.cmd == "replace":
        if args.body_only:
            n = 0
            for para in iter_all_paragraphs(doc, include_headers_footers=False):
                n += replace_in_paragraph(para, args.find, args.replace)
            result = {"replacements": n}
        else:
            result = cmd_replace(doc, args)
    elif args.cmd == "set-cell":
        result = cmd_set_cell(doc, args)
    elif args.cmd == "insert":
        result = cmd_insert(doc, args)
    elif args.cmd == "delete":
        result = cmd_delete(doc, args)
    elif args.cmd == "normalize":
        result = cmd_normalize(doc)
    elif args.cmd == "toc":
        result = cmd_toc(doc, args)
    elif args.cmd == "page-numbers":
        result = cmd_page_numbers(doc, args)
    else:
        result = cmd_style(doc, args)

    out = args.output or args.path
    doc.save(out)
    result.update({"ok": True, "output": out})
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
