#!/usr/bin/env python3
"""Checks for any workbook, from two published sets of spreadsheet rules.

  SHEET-MERGED     No merged cells (UK Analysis Function, Releasing statistics in spreadsheets,
                   "Merged and split cells"; FAST Standard 02c 4.02-02).
  SHEET-HIDDEN     No hidden rows, columns or sheets (UK guidance, Formatting; FAST 2.01-08).
  SHEET-EMPTY      No blank sheet in a workbook of several (UK guidance, Blank worksheets).
  SHEET-HEADINGS   A table's header row gives every column a unique text heading (UK guidance,
                   Column headings).
  SHEET-NUMBERS    In a column of numbers, every value is stored as a number, not as text or a
                   dash, "..", "NA" (UK guidance, Signposting with note markers, Cells with no data).
  SHEET-LINKS      No links to other workbooks (FAST 1.03-01 and 1.03-02).
  SHEET-VOLATILE   No OFFSET or INDIRECT in a formula (FAST 4.01-03 and 4.01-04).
  SHEET-HARDCODED  No number typed into a formula, apart from units of time and scale; an
                   assumption sits in its own labelled cell (FAST 3.04-01).

A customer's own form wins. A builder that redraws a customer's form sets the workbook's custom
property "Customer form" to its own name, and SHEET-MERGED, SHEET-HEADINGS and SHEET-HARDCODED then
skip: the form's merged cells, headings and priced formulas are the customer's, not ours to change.

The UK guidance is Crown copyright under the Open Government Licence v3.0 and the FAST Standard
is CC BY 4.0 (FAST Standard Organisation); both are restated here in our own words.
check(rule_id, path, case, stage) -> (passed, evidence); passed is None when the rule does not apply.
Needs openpyxl.
"""
import re
import zipfile
from pathlib import Path

# Numbers a formula may carry without being an assumption: none, one, halves to quarters, a week,
# a year in months, days, hours, minutes and weeks, and per cent, per mille and thousands.
UNIVERSAL = {0, 1, 2, 3, 4, 7, 12, 24, 52, 60, 100, 365, 366, 1000}
PLACEHOLDERS = {"-", "--", "–", "—", "..", "...", "na", "n/a", "n.a.", "nil", "?"}
NUMBER_TEXT = re.compile(r"^\s*[-+]?(\d{1,3}([ ,.  ]\d{3})+|\d+)([.,]\d+)?\s*%?\s*$")
FORM = "Customer form"
FORM_RULES = {"SHEET-MERGED", "SHEET-HEADINGS", "SHEET-HARDCODED"}
REF = re.compile(r"(?:'[^']+'|[A-Za-z_][\w.]*)?!?\$?[A-Z]{1,3}\$?\d+(?::\$?[A-Z]{1,3}\$?\d+)?")


def head(bad, limit=3):
    return "; ".join(bad[:limit]) + (" (+%d more)" % (len(bad) - limit) if len(bad) > limit else "")


def book(path):
    import openpyxl
    return openpyxl.load_workbook(path)


def customer_form(path):
    """The builder named in the workbook's "Customer form" property, or "" when it has none."""
    import xml.etree.ElementTree as ET
    try:
        with zipfile.ZipFile(path) as z:
            data = z.read("docProps/custom.xml")
        for prop in ET.fromstring(data):
            if prop.get("name") == FORM:
                return "".join(prop.itertext()).strip() or "a builder"
    except (KeyError, OSError, zipfile.BadZipFile, ET.ParseError):
        pass
    return ""


def used(ws):
    """The rows of a sheet as lists of values, trailing empties kept to the used width."""
    return [list(row) for row in ws.iter_rows(values_only=True)]


def header_row(rows):
    """The first row with two or more values, all text, followed by a row holding a number."""
    for i, row in enumerate(rows[:-1]):
        filled = [v for v in row if v not in (None, "")]
        if len(filled) >= 2 and all(isinstance(v, str) for v in filled):
            if any(isinstance(v, (int, float)) and not isinstance(v, bool) for v in rows[i + 1]):
                return i
    return None


def numeric_columns(rows, top):
    """Columns under the header meant for numbers: at least one real number, and nearly every
    filled cell a number, a number written as text, or a placeholder for one."""
    out = []
    width = max(len(r) for r in rows)
    for c in range(width):
        cells = [r[c] for r in rows[top + 1:] if c < len(r) and r[c] not in (None, "")]
        nums = [v for v in cells if isinstance(v, (int, float)) and not isinstance(v, bool)]
        meant = nums + [v for v in cells if isinstance(v, str) and (NUMBER_TEXT.match(v) or v.strip().lower() in PLACEHOLDERS)]
        if len(cells) >= 3 and nums and len(meant) >= 0.8 * len(cells):
            out.append(c)
    return out


def column(c):
    s = ""
    c += 1
    while c:
        c, r = divmod(c - 1, 26)
        s = chr(65 + r) + s
    return s


def check(rule_id, path, case, stage):
    path = Path(path)
    if path.suffix.lower() != ".xlsx":
        return None, "not a workbook"
    if rule_id in FORM_RULES:
        form = customer_form(path)
        if form:
            return None, "the customer's own form, redrawn by %s: its layout is theirs" % form
    wb = book(path)
    sheets = wb.worksheets
    if rule_id == "SHEET-MERGED":
        bad = ["%s!%s" % (ws.title, r) for ws in sheets for r in ws.merged_cells.ranges]
        return (not bad, ("merged cells at " + head(bad)) if bad else "no merged cells")
    if rule_id == "SHEET-HIDDEN":
        bad = ["sheet %s" % ws.title for ws in sheets if ws.sheet_state != "visible"]
        for ws in sheets:
            bad += ["%s row %s" % (ws.title, k) for k, d in ws.row_dimensions.items() if d.hidden]
            bad += ["%s column %s" % (ws.title, k) for k, d in ws.column_dimensions.items() if d.hidden]
        return (not bad, ("hidden: " + head(bad)) if bad else "nothing hidden")
    if rule_id == "SHEET-EMPTY":
        if len(sheets) < 2:
            return None, "one sheet"
        bad = [ws.title for ws in sheets if not any(v not in (None, "") for row in used(ws) for v in row)]
        return (not bad, ("blank sheets: " + head(bad)) if bad else "every sheet holds something")
    if rule_id == "SHEET-HEADINGS":
        bad, seen = [], 0
        for ws in sheets:
            for table in ws.tables.values():
                seen += 1
                names = [c.name for c in table.tableColumns]
                if any(not n or re.fullmatch(r"Column\d+", n) for n in names):
                    bad.append("%s table %s has an unnamed column" % (ws.title, table.displayName))
                if len(set(n.lower() for n in names)) != len(names):
                    bad.append("%s table %s repeats a heading" % (ws.title, table.displayName))
            if ws.tables:
                continue
            rows = used(ws)
            top = header_row(rows) if rows else None
            if top is None:
                continue
            seen += 1
            width = max(len(r) for r in rows[top:])
            heads = [rows[top][c] if c < len(rows[top]) else None for c in range(width)]
            data_cols = [c for c in range(width) if any(c < len(r) and r[c] not in (None, "") for r in rows[top + 1:])]
            empty = [column(c) for c in data_cols if heads[c] in (None, "")]
            if empty:
                bad.append("%s row %d has no heading over column %s" % (ws.title, top + 1, ", ".join(empty)))
            named = [str(h).strip().lower() for h in heads if h not in (None, "")]
            if len(set(named)) != len(named):
                bad.append("%s row %d repeats a heading" % (ws.title, top + 1))
        if not seen:
            return None, "no table with a header row"
        return (not bad, head(bad) if bad else "every column has a unique heading")
    if rule_id == "SHEET-NUMBERS":
        bad, seen = [], 0
        for ws in sheets:
            rows = used(ws)
            top = header_row(rows) if rows else None
            if top is None:
                continue
            for c in numeric_columns(rows, top):
                seen += 1
                for i, r in enumerate(rows[top + 1:], start=top + 2):
                    v = r[c] if c < len(r) else None
                    if isinstance(v, str) and not v.startswith("="):
                        if NUMBER_TEXT.match(v):
                            bad.append("%s!%s%d holds the number %r as text" % (ws.title, column(c), i, v))
                        elif v.strip().lower() in PLACEHOLDERS:
                            bad.append("%s!%s%d holds %r in a column of numbers; leave it blank and say why in a note"
                                       % (ws.title, column(c), i, v))
        if not seen:
            return None, "no column of numbers under a header"
        return (not bad, head(bad) if bad else "every value in a column of numbers is a number")
    if rule_id == "SHEET-LINKS":
        with zipfile.ZipFile(path) as z:
            links = [n for n in z.namelist() if n.startswith("xl/externalLinks/")]
        return (not links, "links to %d other workbooks; bring the values in" % len(links) if links else "no links to other workbooks")
    if rule_id in ("SHEET-VOLATILE", "SHEET-HARDCODED"):
        bad, n = [], 0
        for ws in sheets:
            for row in ws.iter_rows():
                for cell in row:
                    f = cell.value
                    if not (isinstance(f, str) and f.startswith("=")):
                        continue
                    n += 1
                    where = "%s!%s" % (ws.title, cell.coordinate)
                    if rule_id == "SHEET-VOLATILE":
                        if re.search(r"\b(OFFSET|INDIRECT)\s*\(", f, re.I):
                            bad.append("%s uses %s" % (where, re.search(r"\b(OFFSET|INDIRECT)", f, re.I).group(1).upper()))
                        continue
                    bare = REF.sub(" ", re.sub(r'"[^"]*"', " ", f[1:]))
                    for lit in re.findall(r"(?<![\w.])(\d+(?:\.\d+)?)(?![\w.])", bare):
                        if float(lit) not in UNIVERSAL:
                            bad.append("%s types %s into %s; put it in its own labelled cell" % (where, lit, f))
                            break
        if not n:
            return None, "no formulas"
        if rule_id == "SHEET-VOLATILE":
            return (not bad, head(bad) if bad else "no OFFSET or INDIRECT in %d formulas" % n)
        return (not bad, head(bad) if bad else "no assumption typed into %d formulas" % n)
    return None, "unknown rule"
