#!/usr/bin/env python3
"""A page's sender is the company the person's folder describes.

  COMPANY-FILE   When the folder holds a company.json (skills/_shared/company.py: the company's own particulars,
                 written once) and the page is that company's, the data file the page was built from says
                 nothing else about the company than the file does, and the page carries the company's name and
                 its numbers (the VAT number and the register number, where that kind of document prints them)
                 as the file gives them. A particular the file declares unknown is not asked for. The rule does
                 not apply when the folder has no company file or the page is another company's.

A house rule (one record of the company, every page in step with it), not a rule from a standard: the shape of
the file is EN 16931-1's seller party, cited. check(rule_id, path, case, stage) -> (passed, evidence).
"""
import copy
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "_shared"))

RULES = ("COMPANY-FILE",)
# The numbers each kind of document prints of its sender.
PRINTS = {"business-letter": ("vat_id", "register_number"), "trade-documents": ("vat_id", "register_number"),
          "e-invoice": ("vat_id",), "meeting-minutes": ("register_number",),
          "employment-statement": ("register_number",), "contract-drafting": ("register_number",)}
WORDS = {"vat_id": "VAT number", "register_number": "register number", "name": "name"}


def _squeeze(text):
    return re.sub(r"[\s  .\-/,]", "", str(text or "")).casefold()


def check(rule_id, path, case, stage):
    if rule_id != "COMPANY-FILE":
        return None, "no such rule"
    import company
    import notes_floor
    path = Path(path)
    folder = (case or {}).get("folder") or ""
    # The output first: a file that cannot be read is "could not check", whatever the folder holds, so that a
    # file no rule can read is never called checked.
    page = notes_floor.page_text(path)
    if not page.strip():
        return None, "could not read the output as text"
    found = company.find(Path(folder) if folder else path.parent)
    if not found:
        return None, "no company.json in the folder"
    try:
        comp = company.load(found)
    except SystemExit as exc:
        return False, "the company file cannot be read as one: %s" % str(exc)[:300]
    _notes, data = notes_floor.read_folder(path, folder)
    bad, pack, ours = [], None, None
    for name, kind, content in data:
        where, party = company.sender_of(content, kind)
        if where is None or not party or company._empty(party.get("name")):
            continue
        if not company.is_ours(party, comp):
            ours = False if ours is None else ours
            continue
        ours, pack = True, kind
        root = Path(folder).resolve() if folder else path.resolve().parent
        try:
            company.apply(copy.deepcopy(content), root / name, kind, say=False)
        except SystemExit as exc:
            lines = [l.strip(" -") for l in str(exc).splitlines() if l.strip().startswith("-")]
            bad += lines or [str(exc)[:300]]
    if ours is None:
        ours = bool(comp.get("name")) and _squeeze(comp["name"]) in _squeeze(page)
    if not ours:
        return None, "the page's sender is not the company of %s" % found.name
    unknown = company.unknown_of(comp)
    flat = _squeeze(page)
    for key in ("name",) + PRINTS.get(pack, ()):
        value = comp.get(key)
        if company._empty(value) or key in unknown:
            continue
        if _squeeze(value) not in flat:
            bad.append("the company's %s is %s in the company file and the page does not carry it" % (WORDS[key], value))
    if not bad:
        return True, "the sender is the company of %s, particular for particular" % found.name
    return False, ("%s. The company file (%s) is the company's own record, written once: build the page from it, and "
                   "correct whichever is wrong from the person's files. Never change a particular to make the two "
                   "agree" % ("; ".join(bad[:6]), found))
