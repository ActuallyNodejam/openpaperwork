#!/usr/bin/env python3
# MIT License. Part of the Hermes docx skill.
"""Health-check a .docx package and report issues as JSON.

Usage: docx_validate.py file.docx

Checks (health-check tier, NOT full XSD schema validation):
  - the file is a readable zip and python-docx can open it
  - required package parts exist ([Content_Types].xml, document.xml)
  - every relationship in every .rels file resolves to a part in the
    package (dangling image/hyperlink/etc. rels are reported; external
    targets such as hyperlinks are skipped)
  - r:embed / r:id references in document.xml resolve to relationships
  - embedded images are non-empty and start with known magic bytes
    (PNG/JPEG/GIF/BMP/TIFF/EMF/WMF/SVG); no PIL required
  - paragraph and run style ids referenced by the document exist in
    styles.xml
  - explicit top-level table widths are compared with their section margins
    (warning only; autofit, nested tables and visual layout still need review)

Output: {"ok": bool, "issues": [{"severity": "error"|"warning", ...}]}
Exit code 1 when any error-severity issue is found (warnings exit 0).
"""
from __future__ import annotations

import argparse
import json
import posixpath
import sys
import zipfile

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PR = "http://schemas.openxmlformats.org/package/2006/relationships"

IMAGE_MAGIC = (
    b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff", b"GIF87a", b"GIF89a",
    b"BM", b"II*\x00", b"MM\x00*",
    b"\x01\x00\x00\x00",              # EMF
    b"\xd7\xcd\xc6\x9a", b"\x01\x00\x09\x00",  # WMF variants
    b"<?xml", b"<svg",
)


def _issue(issues, severity, code, detail):
    issues.append({"severity": severity, "code": code, "detail": detail})


def _rel_target(base_part: str, target: str) -> str:
    base_dir = posixpath.dirname(base_part)
    return posixpath.normpath(posixpath.join(base_dir, target)).lstrip("/")


def check_table_widths(doc_root, issues):
    """Flag explicit top-level table widths; this does not simulate Word layout."""
    body = doc_root.find(f"{{{W}}}body")
    if body is None:
        return
    blocks = list(body)
    indices = {block: i + 1 for i, block in enumerate(b for b in blocks if b.tag == f"{{{W}}}tbl")}
    usable = None
    # Section properties terminate their section, so inspect blocks backwards.
    for block in reversed(blocks):
        section = block if block.tag == f"{{{W}}}sectPr" else block.find(f"{{{W}}}pPr/{{{W}}}sectPr")
        if section is not None:
            size = section.find(f"{{{W}}}pgSz")
            margins = section.find(f"{{{W}}}pgMar")
            values = [size.get(f"{{{W}}}w") if size is not None else None]
            values += [margins.get(f"{{{W}}}{side}") if margins is not None else None for side in ("left", "right")]
            usable = int(values[0]) - int(values[1]) - int(values[2]) if all(v is not None for v in values) else None
        if block.tag != f"{{{W}}}tbl" or usable is None:
            continue
        widths = [sum(int(col.get(f"{{{W}}}w", "0")) for col in block.findall(f"{{{W}}}tblGrid/{{{W}}}gridCol"))]
        declared = block.find(f"{{{W}}}tblPr/{{{W}}}tblW")
        if declared is not None and declared.get(f"{{{W}}}type") == "dxa":
            widths.append(int(declared.get(f"{{{W}}}w", "0")))
        for row in block.findall(f"{{{W}}}tr"):
            cells = row.findall(f"{{{W}}}tc/{{{W}}}tcPr/{{{W}}}tcW")
            if cells and all(c.get(f"{{{W}}}type") == "dxa" for c in cells):
                widths.append(sum(int(c.get(f"{{{W}}}w", "0")) for c in cells))
        if max(widths) > usable + 20:  # one-point rounding allowance
            _issue(issues, "warning", "table-width-overflow",
                   f"Table {indices[block]} declares {max(widths)} twips across a {usable}-twip usable page. "
                   "Fit grid and cell widths to the section or inspect an intentional overflow in a renderer.")


def validate(path: str) -> dict:
    issues: list[dict] = []

    try:
        zf = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as exc:
        _issue(issues, "error", "not-a-zip", str(exc))
        return {"ok": False, "issues": issues}

    names = set(zf.namelist())
    bad = zf.testzip()
    if bad is not None:
        _issue(issues, "error", "corrupt-member", f"CRC check failed: {bad}")

    for required in ("[Content_Types].xml", "word/document.xml"):
        if required not in names:
            _issue(issues, "error", "missing-part",
                   f"required part absent: {required}")
    if issues and any(i["severity"] == "error" for i in issues):
        return {"ok": False, "issues": issues}

    # --- relationships resolve ------------------------------------------
    # Keyed by the part a .rels file belongs to: the document's and a header's
    # share the word/ folder but not their ids.
    rel_ids_by_source: dict[str, dict] = {}
    for rels_name in sorted(n for n in names if n.endswith(".rels")):
        try:
            root = etree.fromstring(zf.read(rels_name))
        except etree.XMLSyntaxError as exc:
            _issue(issues, "error", "bad-rels-xml", f"{rels_name}: {exc}")
            continue
        source_part = posixpath.normpath(
            posixpath.join(posixpath.dirname(rels_name), ".."))
        source_part = "" if source_part == "." else source_part
        ids = {}
        for rel in root.iter(f"{{{PR}}}Relationship"):
            rid, target = rel.get("Id"), rel.get("Target", "")
            mode = rel.get("TargetMode", "Internal")
            ids[rid] = target
            if mode == "External":
                continue
            resolved = _rel_target(source_part + "/x" if source_part
                                   else "x", target)
            if resolved not in names:
                _issue(issues, "error", "dangling-rel",
                       f"{rels_name}: {rid} -> {target} (missing part)")
        owner = posixpath.join(source_part, posixpath.basename(rels_name)[:-len(".rels")])
        rel_ids_by_source[owner or "_package"] = ids

    # --- r:id / r:embed references in document.xml -----------------------
    doc_root = etree.fromstring(zf.read("word/document.xml"))
    doc_rels = rel_ids_by_source.get("word/document.xml", {})
    for el in doc_root.iter():
        for attr in (f"{{{R}}}id", f"{{{R}}}embed", f"{{{R}}}link"):
            rid = el.get(attr)
            if rid and rid not in doc_rels:
                _issue(issues, "error", "unresolved-reference",
                       f"document.xml references {rid} with no relationship")

    # --- embedded images decode ------------------------------------------
    for name in [n for n in names if n.startswith("word/media/")]:
        data = zf.read(name)
        if not data:
            _issue(issues, "error", "empty-image", name)
        elif not any(data.startswith(m) for m in IMAGE_MAGIC):
            _issue(issues, "warning", "unknown-image-format",
                   f"{name}: unrecognized magic bytes")

    # --- styles referenced exist ------------------------------------------
    defined = set()
    if "word/styles.xml" in names:
        styles_root = etree.fromstring(zf.read("word/styles.xml"))
        defined = {s.get(f"{{{W}}}styleId")
                   for s in styles_root.iter(f"{{{W}}}style")}
    for tag, attr in ((f"{{{W}}}pStyle", f"{{{W}}}val"),
                      (f"{{{W}}}rStyle", f"{{{W}}}val"),
                      (f"{{{W}}}tblStyle", f"{{{W}}}val")):
        for el in doc_root.iter(tag):
            sid = el.get(attr)
            if sid and sid not in defined:
                _issue(issues, "error", "missing-style",
                       f"style id referenced but not defined: {sid}")

    check_table_widths(doc_root, issues)

    # --- python-docx can open it ------------------------------------------
    try:
        from docx import Document
        Document(path)
    except Exception as exc:  # noqa: BLE001 - triage tool, report anything
        _issue(issues, "error", "python-docx-open-failed", str(exc))

    ok = not any(i["severity"] == "error" for i in issues)
    return {"ok": ok, "issues": issues}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Health-check a .docx (not XSD schema validation).")
    ap.add_argument("path", help="the .docx file to check")
    args = ap.parse_args()
    report = validate(args.path)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
