#!/usr/bin/env python3
"""What a client's own example files do, read by code and compared by code.

A spreadsheet or a deck the client made is the standard for the next one: the columns and their order, the
title and section rows, the number formats, the total row; the page rhythm, the fonts, the ink and the
colours of the pages. This reads those into a fingerprint, writes the name pattern of the example files, and
compares a new file with the fingerprint, naming the field it gets wrong. No model judges; nothing here
knows a client. Word and PDF documents stay at the depth the onboarding reading has (fonts, colours, headers).

    examples.py fingerprint <file> [--company-words Acme Berg ...]
    examples.py check <new file> --examples <fingerprint.json>
    examples.py check <new file> --installed      (the company pack's examples in .nodejam/examples)

check prints one line for each field that is not the same: `FAIL <field>: ...` where the new file lacks or
changes what the examples have, `WARN <field>: ...` where it is close, and ends with
`examples check: N fields same, M close, K off`. Exit code 1 when any line is FAIL, 3 when the file could not
be read (the last line then begins "pack check not checked:"), else 0.
"""
from __future__ import annotations

import argparse
import colorsys
import csv
import importlib.util
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import unicodedata
import zipfile
from collections import Counter
from pathlib import Path

# The app's openpyxl is paper-xlsx, which loads in preserve mode and refuses
# edits it cannot splice back (moved pictures, sheets redrawn whole). This
# script keeps the stock round trip it was written against; preserve mode is
# for edits to a person's own workbook (skills/xlsx/scripts/xlsx_keep.py).
try:
    STOCK_LOAD = ({"preserve": False}
                  if importlib.util.find_spec("openpyxl.preserve") else {})
except ModuleNotFoundError:
    STOCK_LOAD = {}

SHEETS = {".xlsx", ".xlsm", ".xltx", ".xltm", ".csv"}
DECKS = {".pptx", ".pdf"}
DEFAULT_SHEET = re.compile(r"^(sheet|blad|tabelle|feuil|ark|hoja|foglio|blatt|tabel)\s*\d*$", re.I)
SLIDE_ASPECTS = (4 / 3, 16 / 10, 16 / 9)
CAP_PAGES = 100


def norm(value) -> str:
    """Lowercase, no diacritics, words separated by one space: how two headers are told equal."""
    text = unicodedata.normalize("NFKD", str(value or "")).lower()
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9ß]+", " ", text).strip()


# ----------------------------------------------------------------------------- meaning of a header

# meaning -> words (normalised: no diacritics) in Swedish, English, German, Norwegian and Danish. The first
# meaning whose words match wins, so the specific ones (code, sum) stand before the general ones.
LEXICON = [
    ("code", r"art ?nr|artnr|artikelnr|artikelnummer|nummer|number|sku|kod|code|referens|reference|ref|id|nr|no|numero"),
    ("sum", r"summa|total|totalt|totalsumma|sum|belopp|gesamt|betrag|subtotal|totaal"),
    ("price", r"pris|a pris|styckpris|price|preis|kostnad|cost|prijs|kosten"),
    ("picture", r"bild|bilder|foto|image|picture|photo|bilde|billede|abbildung|pic"),
    ("count", r"antal|qty|quantity|anzahl|menge|antall|mengde|st|stk|pcs|aantal|count"),
    ("supplier", r"leverantor|supplier|vendor|lieferant|leverandor|fabrikat|tillverkare|manufacturer|hersteller|producent"),
    ("lead time", r"ledtid|leveranstid|lead ?time|delivery time|lieferzeit|leveringstid|levtid|leveransvecka"),
    ("size", r"matt|dimension|dimensioner|size|storlek|große|grosse|masse|maße|storrelse|størrelse"),
    ("unit", r"enhet|unit|einheit|enhed|eenheid"),
    ("link", r"lank|link|url|webb|web|hemsida"),
    ("date", r"datum|date|dato|deadline|leveransdatum|frist"),
    ("note", r"anmarkning|kommentar|kommentarer|note|notes|notering|comment|bemerkung|anmerkung|merknad|remark|ovrigt"),
    ("room", r"rum|yta|area|room|zone|raum|bereich|rom|omrade|plats|location|etage|vaning"),
    ("article", r"artikel|utforande|beskrivning|description|spec|specification|beschreibung|beskrivelse|modell|model|variant|finish|material"),
    ("name", r"benamning|namn|name|navn|bezeichnung|produkt|product|item|titel|title|post"),
]


def header_meaning(header) -> str | None:
    words = norm(header)
    for meaning, pattern in LEXICON:
        if re.search(r"(?:^|\s)(?:%s)(?:\s|$)" % pattern, words):
            return meaning
    return None


# ----------------------------------------------------------------------------- colours

def _rgb(hexs: str):
    h = hexs.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _lab(hexs: str):
    def lin(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(v) for v in _rgb(hexs))
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883

    def f(t):
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    return 116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))


def delta_e(a: str, b: str) -> float:
    """CIE76 distance between two #rrggbb colours: under 6 is the same colour to the eye, 6 to 18 is near."""
    la, lb = _lab(a), _lab(b)
    return math.dist(la, lb)


def hex_of(rgb) -> str:
    return "#%02x%02x%02x" % tuple(int(v) for v in rgb)


# ----------------------------------------------------------------------------- name patterns

CONNECTORS = {"for", "i", "in", "of", "av", "till", "to", "pa", "at", "fur", "von", "de", "du", "pour", "och", "and", "und", "&"}
DATE = re.compile(r"\d{4}-\d{2}-\d{2}|\d{1,2}[./]\d{1,2}[./]\d{2,4}|(?<!\d)(?:19|20)\d{6}(?!\d)")
VERSION = re.compile(r"^v\d+(?:\.\d+)*$", re.I)


def _kind_of_token(token: str) -> str | None:
    if token == "{date}":
        return "date"
    if VERSION.match(token):
        return "version"
    if re.fullmatch(r"(?:19|20)\d{2}", token):
        return "year"
    if re.fullmatch(r"\d+", token):
        return "number"
    return None


def _tokens(text: str) -> list[str]:
    text = DATE.sub(" {date} ", text)
    return [t for t in re.findall(r"\{date\}|[^\s_\-–—,;:()\[\]]+", text) if t]


def name_pattern(names, company_words=()) -> dict:
    """The fixed and the variable words of one or more file names (or titles).

    With several examples a word is fixed when every example has it. With one, the first word is the kind and
    stays fixed (with the connecting words after it and any word of the company); a word written in lower case
    throughout (a file named like a web address) stays fixed; the rest, and every number, date, year and
    version, is variable."""
    if isinstance(names, str):
        names = [names]
    stems = [Path(n).stem if re.search(r"\.\w{2,5}$", n) else n for n in names]
    stems = [s for s in stems if s.strip()]
    if not stems:
        return {"pattern": "", "tokens": [], "separator": " ", "examples": []}
    company = {norm(w) for w in company_words if w}
    rows = [_tokens(s) for s in stems]
    seps = Counter(re.findall(r"[ _-]", " ".join(stems)))
    separator = seps.most_common(1)[0][0] if seps else " "
    tokens: list[dict] = []
    if len(rows) > 1:
        common = set.intersection(*({norm(t) for t in row} for row in rows))
        for token in rows[0]:
            fixed = norm(token) in common and _kind_of_token(token) is None
            tokens.append({"text": token, "fixed": fixed})
    else:
        row = rows[0]
        lower = row and row[0][:1].islower()
        after_kind = True
        for index, token in enumerate(row):
            kind = _kind_of_token(token)
            fixed = kind is None and (
                index == 0
                or norm(token) in company
                or (after_kind and norm(token) in CONNECTORS)
                or (lower and token[:1].islower())
            )
            if not fixed:
                after_kind = False
            tokens.append({"text": token, "fixed": fixed})
    out: list[dict] = []
    for token in tokens:
        if token["fixed"]:
            out.append({"text": token["text"], "fixed": True})
            continue
        kind = _kind_of_token(token["text"]) or "name"
        if out and not out[-1]["fixed"] and out[-1]["type"] == kind == "name":
            continue
        out.append({"text": "{%s}" % kind, "fixed": False, "type": kind})
    # A connecting word with no variable after it belongs to the name itself.
    return {"pattern": " ".join(t["text"] for t in out), "tokens": out, "separator": separator, "examples": stems}


def name_matches(pattern: dict, text: str, share: float = 1.0) -> bool:
    """Whether a name (a file name without its extension, or a title) follows a pattern: it starts with the
    pattern's first fixed word and carries at least `share` of the fixed words."""
    fixed = [norm(t["text"]) for t in pattern.get("tokens", []) if t["fixed"]]
    fixed = [f for f in fixed if f]
    if not fixed:
        return False
    words = norm(re.sub(r"\.\w{2,5}$", "", text)).split()
    if not words:
        return False
    if pattern["tokens"] and pattern["tokens"][0]["fixed"] and words[0] != fixed[0].split()[0]:
        return False
    have = sum(1 for f in fixed if f in " ".join(words) or f.split()[0] in words)
    return have / len(fixed) >= share


# ----------------------------------------------------------------------------- spreadsheets

MONEY = re.compile(r"kr\b|sek|eur|usd|€|\$|£|¥|\[\$|rp\b|nok|dkk|chf|gbp", re.I)
TOTAL = re.compile(r"^(summa|total|totalt|sum|gesamt|totaal|subtotal|delsumma|totalsumma|att betala|grand total|belopp)\b")
SECTION = re.compile(r"^\s*([^:\d][^:]{0,28}?)\s*:\s*(\S.*)$")
FORMULA_FN = re.compile(r"^=\s*([A-Za-z.]+)\(")


def format_class(fmt: str | None) -> str:
    """A number format by what it shows: money, percent, date, decimal, integer or general."""
    if not fmt or fmt == "General":
        return "general"
    if MONEY.search(fmt):
        return "money"
    if "%" in fmt:
        return "percent"
    if not re.search(r"[0#]", fmt) and re.search(r"[dmyhs]", fmt, re.I):
        return "date"
    if re.search(r"0\.0|#,##0\.0|0,0", fmt):
        return "decimal"
    if re.search(r"0|#", fmt):
        return "integer"
    return "general"


def _col_letter(index: int) -> str:
    out = ""
    index += 1
    while index:
        index, rest = divmod(index - 1, 26)
        out = chr(65 + rest) + out
    return out


def _letter_index(letters: str) -> int:
    n = 0
    for c in letters:
        n = n * 26 + ord(c) - 64
    return n - 1


def _picture_cells(path: Path) -> dict[str, Counter]:
    """Per sheet name, the columns holding pictures: those placed in a cell (the vm mark of a rich value) and
    those anchored by a drawing. Read from the XML only; no picture is decoded."""
    found: dict[str, Counter] = {}
    try:
        z = zipfile.ZipFile(path)
    except zipfile.BadZipFile:
        return found
    with z:
        names = set(z.namelist())
        if "xl/workbook.xml" not in names:
            return found
        book = z.read("xl/workbook.xml").decode("utf-8", "replace")
        rels = z.read("xl/_rels/workbook.xml.rels").decode("utf-8", "replace") if "xl/_rels/workbook.xml.rels" in names else ""
        targets = {}
        for m in re.finditer(r"<Relationship\b[^>]*>", rels):
            tag = m.group(0)
            rid, target = re.search(r'\bId="([^"]+)"', tag), re.search(r'\bTarget="([^"]+)"', tag)
            if rid and target:
                targets[rid.group(1)] = target.group(1)
        for m in re.finditer(r"<sheet\b[^>]*>", book):
            tag = m.group(0)
            name, rid = re.search(r'\bname="([^"]*)"', tag), re.search(r'\br:id="([^"]+)"', tag)
            if not name or not rid or rid.group(1) not in targets:
                continue
            target = targets[rid.group(1)].lstrip("/")
            sheet_path = target if target.startswith("xl/") else "xl/" + target
            if sheet_path not in names:
                continue
            title = name.group(1).replace("&amp;", "&").replace("&apos;", "'").replace("&quot;", '"')
            counts: Counter = Counter()
            xml = z.read(sheet_path).decode("utf-8", "replace")
            for cell in re.finditer(r'<c r="([A-Z]+)\d+"[^>]*\bvm="', xml):
                counts[cell.group(1)] += 1
            rel_path = sheet_path.replace("worksheets/", "worksheets/_rels/") + ".rels"
            if rel_path in names:
                sheet_rels = z.read(rel_path).decode("utf-8", "replace")
                for d in re.finditer(r'Target="([^"]*drawings/[^"]+\.xml)"', sheet_rels):
                    drawing = os.path.normpath(os.path.join("xl/worksheets", d.group(1))).replace("\\", "/")
                    if drawing in names:
                        dxml = z.read(drawing).decode("utf-8", "replace")
                        for a in re.finditer(r"<(?:xdr:)?from>\s*<(?:xdr:)?col>(\d+)</", dxml):
                            counts[_col_letter(int(a.group(1)))] += 1
            if counts:
                found[title] = counts
    return found


def _cell_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _sheet_fingerprint(ws, pictures: Counter, rows: list[list], csv_mode: bool = False) -> dict:
    """One sheet's fingerprint from its cells. `rows` are the values (formulas as text) of the first rows."""
    width = max((len(r) for r in rows), default=0)

    def filled(r):
        return [i for i, v in enumerate(r) if _cell_text(v)]

    def textual(r):
        idx = filled(r)
        return idx and all(isinstance(r[i], str) for i in idx)

    counts = [len(filled(r)) for r in rows[:20]]
    header_at = None
    for i, r in enumerate(rows[:20]):
        if counts[i] >= 3 and textual(r):
            header_at = i
            break
    if header_at is None:
        best = max(counts, default=0)
        header_at = counts.index(best) if best >= 2 else 0
    header = rows[header_at] if rows else []
    head_idx = filled(header)
    keys = [norm(header[i]) for i in head_idx]

    def single(r):
        idx = filled(r)
        return idx[0] if len(idx) == 1 else None

    # Rows with one filled cell: a title, or a section marker ("Label: value") that comes back.
    candidates = []
    for i, r in enumerate(rows):
        if i == header_at or single(r) is None:
            continue
        text = _cell_text(r[single(r)])
        m = SECTION.match(text)
        candidates.append((i, text, m.group(1).strip() if m else None, single(r)))
    labels = Counter(label for _, _, label, _ in candidates if label)
    section_label = next((l for l, n in labels.most_common() if n >= 2), None)
    section_rows = [(i, t, c) for i, t, l, c in candidates if section_label and l == section_label]
    bold_sections = []
    if section_label is None and ws is not None and not csv_mode:
        for i, t, l, c in candidates:
            if i > header_at and getattr(ws.cell(i + 1, c + 1).font, "b", False) and not TOTAL.match(norm(t)):
                bold_sections.append((i, t, c))
        if len(bold_sections) < 2:
            bold_sections = []
    sections = None
    marker_rows = {i for i, _, _ in section_rows} | {i for i, _, _ in bold_sections}
    if section_rows or bold_sections:
        used = section_rows or bold_sections
        repeats = 0
        for i, _, _ in used:
            for j in range(i + 1, min(i + 3, len(rows))):
                key = [norm(rows[j][k]) for k in head_idx if k < len(rows[j])]
                if key and sum(a == b for a, b in zip(key, keys)) >= max(2, int(0.7 * len(keys))):
                    repeats += 1
                    break
        if section_rows:
            meaning = header_meaning(section_label)
            sample = section_rows[0][1].split(":", 1)[1].strip()
            sections = {"label": section_label, "pattern": "%s: {%s}" % (section_label, meaning if meaning == "room" else "name"),
                        "count": len(section_rows), "example": sample, "column": _col_letter(section_rows[0][2]), "bold": True}
        else:
            sections = {"label": None, "pattern": "{name}", "count": len(bold_sections), "example": bold_sections[0][1],
                        "column": _col_letter(bold_sections[0][2]), "bold": True}
        sections["repeats_header"] = repeats >= max(1, len(used) // 2)
        if ws is not None and not csv_mode:
            sections["bold"] = bool(getattr(ws.cell(used[0][0] + 1, used[0][2] + 1).font, "b", False))
    title_rows = [t for i, t, l, c in candidates if i < header_at and i not in marker_rows]
    title = None
    if title_rows:
        title = {"rows": title_rows, "patterns": [name_pattern(t) for t in title_rows]}
        title["pattern"] = title["patterns"][0]["pattern"]
    # Total rows: a label that says total and a formula, or a sum formula beside nothing.
    totals = []
    data_rows = []
    repeat_rows = []
    for i in range(header_at + 1, len(rows)):
        r = rows[i]
        if i in marker_rows or not filled(r):
            continue
        key = [norm(r[k]) for k in head_idx if k < len(r)]
        if sum(a == b for a, b in zip(key, keys)) >= max(2, int(0.7 * len(keys))):
            repeat_rows.append(i + 1)
            continue
        label = next((_cell_text(v) for v in r if isinstance(v, str) and not v.startswith("=") and TOTAL.match(norm(v))), None)
        formulas = [(k, v) for k, v in enumerate(r) if isinstance(v, str) and v.startswith("=")]
        summing = [(k, v) for k, v in formulas if re.match(r"=\s*(SUM|SUMMA|SUBTOTAL|DELSUMMA)\(", v, re.I)]
        if (label and formulas) or summing and not any(isinstance(v, (int, float)) for v in r):
            fn = FORMULA_FN.match((summing or formulas)[0][1])
            totals.append({"label": label or "", "column": _col_letter((summing or formulas)[0][0]),
                           "function": fn.group(1).upper() if fn else "", "row": i + 1})
            continue
        data_rows.append(i)
    widths = {}
    if ws is not None and not csv_mode:
        for letter, dim in ws.column_dimensions.items():
            lo = dim.min or _letter_index(letter) + 1
            hi = dim.max or lo
            if dim.width and hi - lo < 60:
                for k in range(lo, hi + 1):
                    widths[_col_letter(k - 1)] = round(float(dim.width), 1)
    columns = []
    sample_rows = data_rows[:60]
    for k in head_idx:
        letter = _col_letter(k)
        text = _cell_text(header[k])
        kinds: Counter = Counter()
        fmts: Counter = Counter()
        formulas = 0
        links = 0
        full = figured = 0
        for i in sample_rows:
            v = rows[i][k] if k < len(rows[i]) else None
            if v is None or v == "" or (isinstance(v, (int, float)) and not isinstance(v, bool) and v == 0):
                continue
            full += 1
            figured += (isinstance(v, (int, float)) and not isinstance(v, bool)) or (isinstance(v, str) and bool(re.search(r"\d", v)))
            if isinstance(v, str) and v.startswith("="):
                formulas += bool(re.search(r"\$?[A-Z]{1,3}\$?\d+", v))  # a sum of typed numbers is not a calculation
                kinds["number"] += 1
            elif isinstance(v, bool):
                kinds["text"] += 1
            elif isinstance(v, int) or (isinstance(v, float) and v.is_integer()):
                kinds["integer"] += 1
            elif isinstance(v, float):
                kinds["number"] += 1
            elif hasattr(v, "year"):
                kinds["date"] += 1
            elif isinstance(v, str) and re.match(r"https?://|www\.", v):
                links += 1
                kinds["link"] += 1
            else:
                kinds["text"] += 1
        if ws is not None and not csv_mode:
            for i in list(sample_rows) + list(range(header_at + 1, min(header_at + 40, len(rows)))):
                cell = ws.cell(i + 1, k + 1)
                if cell.number_format and cell.number_format != "General":
                    fmts[cell.number_format] += 1
                if cell.hyperlink is not None and i in sample_rows:
                    links += 1
        fmt = fmts.most_common(1)[0][0] if fmts else None
        pics = pictures.get(letter, 0)
        data_kind = None
        if pics:
            data_kind = "picture"
        elif links and links >= max(1, sum(kinds.values()) // 2):
            data_kind = "link"
        elif kinds:
            data_kind = kinds.most_common(1)[0][0]
        meaning = header_meaning(text)
        if meaning is None:
            cls = format_class(fmt)
            if data_kind == "picture":
                meaning = "picture"
            elif data_kind == "link":
                meaning = "link"
            elif data_kind == "date" or cls == "date":
                meaning = "date"
            elif cls == "money":
                meaning = "price"
            elif data_kind == "integer":
                meaning = "count"
        columns.append({
            "index": len(columns) + 1, "letter": letter, "header": text, "key": norm(text), "meaning": meaning or "text",
            "data": data_kind, "format": fmt, "format_class": format_class(fmt), "width": widths.get(letter),
            "formulas": formulas, "numbers": sum(n for k, n in kinds.items() if k in ("number", "integer")), "pictures": pics,
            # The share of data rows this column fills (a zero counts as empty; a picture column counts its pictures).
            "filled": round(min(1.0, (pics if pics else full) / len(sample_rows)), 2) if sample_rows else None,
            # The share it fills with a figure (a count, a measure, a price): "Saknas" in a price column is no price.
            "figured": round(figured / len(sample_rows), 2) if sample_rows else None,
        })
    return {
        "name": ws.title if ws is not None else "csv",
        "default_name": bool(ws is not None and DEFAULT_SHEET.match(ws.title)) or csv_mode,
        "header_row": header_at + 1,
        "title": title,
        "sections": sections,
        "columns": columns,
        "totals": totals,
        "data_rows": len(data_rows),
        "frozen": str(ws.freeze_panes) if ws is not None and not csv_mode and ws.freeze_panes else None,
        "amounts_are_formulas": any(c["formulas"] and c["formulas"] * 2 >= c["numbers"] for c in columns if c["meaning"] in ("sum", "price")) or bool(totals),
        "picture_columns": [c["letter"] for c in columns if c["pictures"]],
        # 1-based rows the starter keeps: section markers, repeated headers, total rows.
        "layout_rows": {"sections": sorted(i + 1 for i in marker_rows), "headers": repeat_rows, "totals": [t["row"] for t in totals]},
    }


def sheet_fingerprint(path: Path, company_words=()) -> dict:
    path = Path(path)
    out = {"kind": "sheet", "file": path.name, "name_pattern": name_pattern(path.name, company_words), "sheets": []}
    if path.suffix.lower() == ".csv":
        raw = path.read_text(encoding="utf-8-sig", errors="replace")
        dialect = csv.Sniffer().sniff(raw[:4000], delimiters=",;\t|") if raw.strip() else csv.excel
        rows = [r for _, r in zip(range(3000), csv.reader(raw.splitlines(), dialect))]
        out["sheets"].append(_sheet_fingerprint(None, Counter(), rows, csv_mode=True))
        return out
    try:
        from openpyxl import load_workbook
    except ImportError as error:
        raise RuntimeError("reading a spreadsheet needs openpyxl, which this machine lacks (%s)" % error)
    book = load_workbook(str(path), data_only=False, **STOCK_LOAD)
    pictures = _picture_cells(path)
    for ws in book.worksheets[:8]:
        rows = []
        for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row, 3000), max_col=min(ws.max_column, 40), values_only=True):
            rows.append(list(row))
        while rows and not any(_cell_text(v) for v in rows[-1]):
            rows.pop()
        if not rows:
            continue
        out["sheets"].append(_sheet_fingerprint(ws, pictures.get(ws.title, Counter()), rows))
    return out


# ----------------------------------------------------------------------------- decks

def _pack_draft():
    path = Path(__file__).resolve().parents[1] / "concept-deck" / "scripts" / "pack_draft.py"
    spec = importlib.util.spec_from_file_location("pack_draft", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _ship(pd, family: str) -> str:
    return next((f for pattern, f in pd.FONT_MAP if re.search(pattern, family, re.I)), "Inter")


def _clean_family(name: str) -> str:
    name = re.sub(r"^[A-Z]{6}\+", "", name or "")
    return re.sub(r"[-,](Bold|Italic|BoldItalic|Book|Light|Regular|Medium|Semi|Demi|Extra|Heavy|Black|Roman|Thin|Oblique).*$", "", name)


def _shares(pairs: Counter, total: float, n: int = 6) -> list[dict]:
    """Colours merged when within a few units, with their share of `total`, largest first."""
    merged: list[list] = []
    for colour, weight in pairs.most_common():
        for entry in merged:
            if delta_e(entry[0], colour) < 6:
                entry[1] += weight
                break
        else:
            merged.append([colour, weight])
    merged.sort(key=lambda e: -e[1])
    return [{"hex": c, "share": round(100 * w / total, 1)} for c, w in merged[:n] if total]


PHOTO_KINDS = {"picture wall", "board or collage", "picture spread with words"}


def _summary(kinds: list[str], infos: list[dict], words: list[int], pd) -> dict:
    n = len(kinds)
    shares = {k: round(100 * c / n, 1) for k, c in Counter(kinds).most_common()}
    roles = pd.roles(infos)
    return {
        "pages": n,
        "types": kinds,
        "shares": shares,
        "opening": kinds[:3],
        "closing": kinds[-1] if kinds else None,
        "roles": pd.program(roles),
        "words_median": int(statistics.median(words)) if words else 0,
    }


def _pdf_tools() -> bool:
    try:
        subprocess.run(["pdfinfo", "-v"], capture_output=True, timeout=10)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def pdf_is_deck(path: Path) -> tuple[bool, dict]:
    """A PDF is a deck when its pages are landscape slides (4:3, 16:10 or 16:9) and there are at least three;
    a portrait document, a drawing on A3 or A4 landscape and a one-page sheet are not."""
    size, pages = None, 0
    if _pdf_tools():
        info = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True, timeout=60).stdout
        m = re.search(r"Pages:\s+(\d+)", info)
        s = re.search(r"Page size:\s+([\d.]+) x ([\d.]+)", info)
        pages = int(m.group(1)) if m else 0
        size = (float(s.group(1)), float(s.group(2))) if s else None
    else:
        import pypdfium2
        pdf = pypdfium2.PdfDocument(str(path))
        pages = len(pdf)
        size = tuple(pdf[0].get_size()) if pages else None
    if not size or not pages:
        return False, {"pages": pages}
    aspect = size[0] / size[1]
    ok = pages >= 3 and any(abs(aspect - a) < 0.03 for a in SLIDE_ASPECTS)
    return ok, {"pages": pages, "size": size, "aspect": round(aspect, 3)}


def _pdf_material(path: Path, pages: int, folder: str):
    """The text of each page, one thumbnail per page and the fonts, by poppler where the machine has it and
    by pypdfium2 and pdfplumber (bundled in the app) where it does not."""
    last = min(pages, CAP_PAGES)
    # pdfinfo alone may be the app's stand-in (Resources/bin/pdfinfo), with no pdftoppm beside it.
    if _pdf_tools() and shutil.which("pdftoppm") and subprocess.run(["pdftoppm", "-v"], capture_output=True).returncode in (0, 99):
        # Side by side in a few chunks: rendering 66 slides one after the other takes six seconds.
        chunk = max(8, -(-last // min(4, os.cpu_count() or 1)))
        jobs = [subprocess.Popen(["pdftoppm", "-r", "24", "-png", "-f", str(first), "-l", str(min(last, first + chunk - 1)),
                                  str(path), os.path.join(folder, "c%03d" % first)])
                for first in range(1, last + 1, chunk)]
        for job in jobs:
            if job.wait(timeout=300):
                raise RuntimeError("pdftoppm could not render %s" % path.name)
        texts = subprocess.run(["pdftotext", "-layout", "-f", "1", "-l", str(last), str(path), "-"], capture_output=True,
                               text=True, timeout=300).stdout.split("\f")
        thumbs = sorted((os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".png")),
                        key=lambda f: [int(n) for n in re.findall(r"\d+", os.path.basename(f))])
        return texts, thumbs, None
    import pypdfium2
    pdf = pypdfium2.PdfDocument(str(path))
    texts, thumbs = [], []
    for i in range(last):
        page = pdf[i]
        file = os.path.join(folder, "p-%03d.png" % (i + 1))
        page.render(scale=24 / 72).to_pil().convert("RGB").save(file)
        thumbs.append(file)
        texts.append(page.get_textpage().get_text_range())
    return texts, thumbs, True


def _pdf_fonts(pd, path: Path, pdfium: bool) -> list[dict]:
    if not pdfium:
        return pd.fonts(str(path))
    import pdfplumber
    seen: Counter = Counter()
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages[:6]:
            for ch in page.chars[:3000]:
                seen[_clean_family(ch.get("fontname", ""))] += 1
    return [{"font": f, "uses": n, "ship": _ship(pd, f)} for f, n in seen.most_common() if f]


def _pdf_colours(arrays, infos) -> dict:
    """Grounds, ink and accents from the page thumbnails. Photo pages say nothing about the house colours."""
    import numpy as np
    grounds: Counter = Counter(i["ground"].lower() for i in infos)
    ink: Counter = Counter()
    accent: Counter = Counter()
    plain = 0
    for a, info in zip(arrays, infos):
        if info["kind"] in PHOTO_KINDS:
            continue
        plain += 1
        px = a.reshape(-1, 3).astype(int)
        q = (px >> 4 << 4) + 8
        codes, counts = np.unique(q[:, 0] * 65536 + q[:, 1] * 256 + q[:, 2], return_counts=True)
        total = counts.sum()
        ground = np.array(_rgb(info["ground"]))
        lum_g = 0.299 * ground[0] + 0.587 * ground[1] + 0.114 * ground[2]
        best, best_gap, seen_accent = None, 0, set()
        for code, count in zip(codes, counts):
            if count / total < 0.002:
                continue
            rgb = np.array([code >> 16, (code >> 8) & 255, code & 255])
            if np.abs(rgb - ground).sum() < 60:
                continue
            gap = abs(0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2] - lum_g)
            if gap > best_gap:
                best, best_gap = rgb, gap
            h, s, v = colorsys.rgb_to_hsv(*(rgb / 255))
            if s > 0.4 and v > 0.3 and count / total >= 0.004:
                seen_accent.add(hex_of(rgb))
        if best is not None:
            ink[hex_of(best)] += 1
        for c in seen_accent:
            accent[c] += 1
    return {
        "grounds": _shares(grounds, len(infos), 5),
        "ink": (_shares(ink, plain, 1) or [None])[0],
        "accents": _shares(accent, plain, 4),
    }


SPEC_LINE = re.compile(r"^\s*([^\W\d_]{3,12}):\s+\S", re.M)
SPACED = re.compile(r"(?<!\S)(?:[^\W\d_] ){4,}[^\W\d_](?!\S)")


def page_layouts(texts) -> dict:
    """How many pages read as a spec grid (pieces each with the same labelled lines: "Plats: ...", "Produkt: ...")
    and as a story page (a named piece with a letter-spaced subtitle and a short caption), from their words."""
    spec = story = 0
    for text in texts:
        labels = Counter(m.lower() for m in SPEC_LINE.findall(text or ""))
        words = len((text or "").split())
        if len(labels) >= 2 and max(labels.values()) >= 2:
            spec += 1
        elif 15 <= words <= 80 and SPACED.search(text or ""):
            story += 1
    return {"specgrid": spec, "feature": story}


def pdf_deck_fingerprint(path: Path, meta: dict) -> dict:
    try:
        import numpy as np
        from PIL import Image
    except ImportError as error:
        raise RuntimeError("reading a deck needs Pillow and numpy, which this machine lacks (%s)" % error)
    pd = _pack_draft()
    with tempfile.TemporaryDirectory() as folder:
        texts, thumbs, pdfium = _pdf_material(path, meta["pages"], folder)
        infos = [pd.kind_of(p, texts[i] if i < len(texts) else "") for i, p in enumerate(thumbs)]
        arrays = [np.asarray(Image.open(p).convert("RGB")) for p in thumbs]
        colours = _pdf_colours(arrays, infos)
        fonts = _pdf_fonts(pd, path, pdfium)
    kinds = [i["kind"] for i in infos]
    words = [i["words"] for i in infos]
    out = {"kind": "deck", "source": "pdf", "file": path.name, "size": {"w": meta["size"][0], "h": meta["size"][1], "unit": "pt",
                                                                       "aspect": meta["aspect"]},
           "total_pages": meta["pages"], "sampled": meta["pages"] > CAP_PAGES}
    out.update(_summary(kinds, infos, words, pd))
    out.update({"fonts": fonts[:6], "picture_share": round(100 * sum(k in PHOTO_KINDS for k in kinds) / max(1, len(kinds)), 1)})
    out["layouts_seen"] = page_layouts(texts)
    out.update(colours)
    return out


THEME_COLOUR = re.compile(r"<a:(dk1|lt1|accent\d)>\s*<a:(?:srgbClr val|sysClr val=\"\w+\" lastClr)=\"([0-9A-Fa-f]{6})\"")


def pptx_deck_fingerprint(path: Path) -> dict:
    try:
        from pptx import Presentation
        from pptx.enum.dml import MSO_FILL
        from pptx.enum.shapes import MSO_SHAPE_TYPE
    except ImportError as error:
        raise RuntimeError("reading a deck needs python-pptx, which this machine lacks (%s)" % error)
    pd = _pack_draft()
    prs = Presentation(str(path))
    width, height = prs.slide_width or 1, prs.slide_height or 1
    theme = {}
    fonts_theme = []
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if re.match(r"ppt/theme/theme\d+\.xml", name):
                xml = z.read(name).decode("utf-8", "replace")
                theme = {k: "#" + v.lower() for k, v in THEME_COLOUR.findall(xml)}
                fonts_theme = re.findall(r'<a:latin typeface="([^"]+)"', xml)[:2]
                break
    fonts: Counter = Counter()
    ink: Counter = Counter()
    grounds: Counter = Counter()
    accents: Counter = Counter()
    layouts: Counter = Counter()
    kinds, infos, words = [], [], []

    def rgb_of(color):
        try:
            return "#" + str(color.rgb).lower() if color is not None and color.type is not None and color.rgb else None
        except (AttributeError, TypeError, ValueError):
            return None

    def walk(shapes):
        for shape in shapes:
            if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                yield from walk(shape.shapes)
            else:
                yield shape

    for slide in prs.slides:
        layouts[slide.slide_layout.name] += 1
        n_words, n_pics, pic_area, ground = 0, 0, 0.0, None
        for shape in walk(slide.shapes):
            area = ((shape.width or 0) * (shape.height or 0)) / (width * height)
            is_pic = shape.shape_type == MSO_SHAPE_TYPE.PICTURE or hasattr(shape, "image") and shape.shape_type != MSO_SHAPE_TYPE.TEXT_BOX
            try:
                if is_pic and shape.image is not None:
                    n_pics += 1
                    pic_area += area
            except (AttributeError, ValueError, KeyError):
                pass
            try:
                if shape.fill.type == MSO_FILL.SOLID:
                    colour = rgb_of(shape.fill.fore_color)
                    if colour:
                        if area >= 0.85:
                            ground = colour
                        elif area >= 0.01:
                            accents[colour] += area
            except (AttributeError, TypeError, NotImplementedError):
                pass
            if shape.has_text_frame:
                for p in shape.text_frame.paragraphs:
                    for run in p.runs:
                        count = len(run.text)
                        n_words += len(run.text.split())
                        fonts[_clean_family(run.font.name) if run.font.name else (fonts_theme[-1] if fonts_theme else "")] += count
                        colour = rgb_of(run.font.color) or theme.get("dk1")
                        if colour and count:
                            ink[colour] += count
        if ground is None:
            try:
                if not slide.follow_master_background and slide.background.fill.type == MSO_FILL.SOLID:
                    ground = rgb_of(slide.background.fill.fore_color)
            except (AttributeError, TypeError, NotImplementedError):
                pass
        grounds[ground or theme.get("lt1") or "#ffffff"] += 1
        if n_words <= 6 and n_pics == 0:
            kind = "divider"
        elif n_words <= 6:
            kind = "picture wall" if n_pics >= 4 else "board or collage"
        elif n_words > 140:
            kind = "text page"
        elif n_pics >= 1:
            kind = "picture spread with words"
        else:
            kind = "page with a few words"
        kinds.append(kind)
        infos.append({"kind": kind, "words": n_words, "flat": 1.0 if n_pics == 0 else 0.0})
        words.append(n_words)
    pages = len(kinds)
    families = [(f, n) for f, n in fonts.most_common() if f]
    out = {"kind": "deck", "source": "pptx", "file": Path(path).name,
           "size": {"w": round(width / 914400, 2), "h": round(height / 914400, 2), "unit": "in", "aspect": round(width / height, 3)},
           "total_pages": pages, "sampled": False}
    if pages:
        out.update(_summary(kinds, infos, words, pd))
    else:
        out.update({"pages": 0, "types": [], "shares": {}, "opening": [], "closing": None, "roles": [], "words_median": 0})
    out["fonts"] = [{"font": f, "uses": n, "ship": _ship(pd, f)} for f, n in families[:6]]
    out["picture_share"] = round(100 * sum(k in PHOTO_KINDS for k in kinds) / max(1, pages), 1)
    out["grounds"] = _shares(grounds, max(1, pages), 5)
    out["ink"] = (_shares(ink, sum(ink.values()) or 1, 1) or [None])[0]
    out["accents"] = _shares(accents, sum(accents.values()) or 1, 4)
    out["layouts"] = [l for l, _ in layouts.most_common(8)]
    return out


def deck_fingerprint(path: Path, company_words=()) -> dict:
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        ok, meta = pdf_is_deck(path)
        if not ok:
            return {"kind": "document", "file": path.name, "note": "not a deck: its pages are not landscape slides", **meta}
        out = pdf_deck_fingerprint(path, meta)
    else:
        out = pptx_deck_fingerprint(path)
    out["name_pattern"] = name_pattern(path.name, company_words)
    return out


def fingerprint(path, company_words=()) -> dict:
    """A spreadsheet's or a deck's fingerprint. Anything else (a Word file, a portrait PDF) has none and
    answers {"kind": "document"}."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in SHEETS:
        return sheet_fingerprint(path, company_words)
    if suffix in DECKS:
        return deck_fingerprint(path, company_words)
    return {"kind": "document", "file": path.name, "note": "no layout fingerprint for this kind of file"}


def merge(fingerprints: list[dict]) -> dict:
    """What several examples of one form share: the columns every sheet has (in the first one's order), the
    title and section patterns they agree on, the fonts and colours all decks use, the pages' shares averaged."""
    fps = [f for f in fingerprints if f and f.get("kind") in ("sheet", "deck")]
    if not fps:
        return {}
    first = json.loads(json.dumps(fps[0]))
    if len(fps) == 1:
        return first
    first["name_pattern"] = name_pattern([f["file"] for f in fps], [])
    first["sources"] = [f["file"] for f in fps]
    if first["kind"] == "sheet":
        for sheet in first["sheets"]:
            others = [next((s for s in f["sheets"] if s["name"] == sheet["name"]), f["sheets"][0]) for f in fps[1:] if f["sheets"]]
            for other in others:
                keys = {c["key"] for c in other["columns"]}
                sheet["columns"] = [c for c in sheet["columns"] if c["key"] in keys]
                if (sheet["title"] or {}).get("pattern") != (other["title"] or {}).get("pattern"):
                    sheet["title"] = None
                if (sheet["sections"] or {}).get("pattern") != (other["sections"] or {}).get("pattern"):
                    sheet["sections"] = None
                if not other["totals"]:
                    sheet["totals"] = []
    else:
        for other in fps[1:]:
            have = {norm(f["font"]) for f in other["fonts"]}
            first["fonts"] = [f for f in first["fonts"] if norm(f["font"]) in have]
            for part in ("grounds", "accents"):
                first[part] = [c for c in first[part] if any(delta_e(c["hex"], o["hex"]) < 12 for o in other[part])]
            if first["ink"] and (not other["ink"] or delta_e(first["ink"]["hex"], other["ink"]["hex"]) > 18):
                first["ink"] = None
            first["shares"] = {k: round((first["shares"].get(k, 0) + other["shares"].get(k, 0)) / 2, 1)
                               for k in set(first["shares"]) | set(other["shares"])}
            n = 0
            while n < min(len(first["opening"]), len(other["opening"])) and first["opening"][n] == other["opening"][n]:
                n += 1
            first["opening"] = first["opening"][:n]
            if first["closing"] != other["closing"]:
                first["closing"] = None
    return first


# ----------------------------------------------------------------------------- compare

def finding(field, verdict, expected, actual, note):
    return {"field": field, "verdict": verdict, "expected": expected, "actual": actual, "note": note}


def _list(items, limit=9):
    items = [str(i) for i in items]
    return ", ".join(items[:limit]) + (" ..." if len(items) > limit else "")


def _match_columns(expected: list[dict], actual: list[dict]):
    """Pair each expected column with an actual one: the same header first, then the same meaning."""
    pairs: dict[int, tuple[dict, str]] = {}
    used: set[int] = set()
    for i, e in enumerate(expected):
        for j, a in enumerate(actual):
            if j not in used and a["key"] == e["key"]:
                pairs[i] = (a, "same")
                used.add(j)
                break
    for i, e in enumerate(expected):
        if i in pairs or e["meaning"] in (None, "text"):
            continue
        for j, a in enumerate(actual):
            if j not in used and a["meaning"] == e["meaning"]:
                pairs[i] = (a, "close")
                used.add(j)
                break
    return pairs, used


def compare_sheet(e: dict, a: dict, label: str = "") -> list[dict]:
    tag = (" on sheet '%s'" % label) if label else ""
    out = []
    if not e["default_name"]:
        same = norm(e["name"]) == norm(a["name"])
        out.append(finding("sheet name", "same" if same else "different", e["name"], a["name"],
                           "the sheet is called '%s'; the examples call it '%s'." % (a["name"], e["name"])))
    if e["title"]:
        if not a["title"]:
            out.append(finding("title" + tag, "missing", e["title"]["pattern"], None,
                               "there is no title above the table; the examples start with '%s'." % e["title"]["pattern"]))
        else:
            ok = name_matches(e["title"]["patterns"][0], a["title"]["rows"][0])
            out.append(finding("title" + tag, "same" if ok else "different", e["title"]["pattern"], a["title"]["rows"][0],
                               "the title reads '%s'; the examples write it '%s'." % (a["title"]["rows"][0], e["title"]["pattern"])))
    if e["sections"]:
        s, t = e["sections"], a["sections"]
        if not t:
            out.append(finding("sections" + tag, "missing", s["pattern"], None,
                               "there are no section rows; the examples put a row '%s' before each block." % s["pattern"]))
        else:
            ok = (s["label"] is None) or norm(s["label"]) == norm(t["label"] or "")
            out.append(finding("sections" + tag, "same" if ok else "different", s["pattern"], t["pattern"],
                               "the section rows read '%s'; the examples write '%s'." % (t["pattern"], s["pattern"])))
            if s.get("repeats_header") != t.get("repeats_header"):
                out.append(finding("section header" + tag, "different", s["repeats_header"], t["repeats_header"],
                                   "the column header %s after each section row; the examples %s it."
                                   % ("is not repeated" if s["repeats_header"] else "is repeated",
                                      "repeat" if s["repeats_header"] else "do not repeat")))
    if e["header_row"] != a["header_row"]:
        out.append(finding("header row" + tag, "close", e["header_row"], a["header_row"],
                           "the column header is on row %d; in the examples it is on row %d." % (a["header_row"], e["header_row"])))
    pairs, used = _match_columns(e["columns"], a["columns"])
    names = _list(c["header"] for c in e["columns"])
    for i, col in enumerate(e["columns"]):
        if i not in pairs:
            out.append(finding("column '%s'" % col["header"], "missing", col["header"], None,
                               "the column '%s' (%s) is missing; the examples have %s in this order." % (col["header"], col["meaning"], names)))
        elif pairs[i][1] == "close":
            out.append(finding("column '%s'" % col["header"], "close", col["header"], pairs[i][0]["header"],
                               "the column '%s' has the meaning of '%s' (%s); write the header as the examples do." % (pairs[i][0]["header"], col["header"], col["meaning"])))
        else:
            out.append(finding("column '%s'" % col["header"], "same", col["header"], pairs[i][0]["header"], ""))
    extra = [c["header"] for j, c in enumerate(a["columns"]) if j not in used]
    if extra:
        out.append(finding("extra columns" + tag, "close", None, extra,
                           "the columns %s are not in the examples (%s)." % (_list(extra), names)))
    order = [a["columns"].index(pairs[i][0]) for i in sorted(pairs)]
    if order == sorted(order):
        if pairs:
            out.append(finding("column order" + tag, "same", None, None, ""))
    else:
        bad = next(k for k in range(1, len(order)) if order[k] < order[k - 1])
        names_by = [e["columns"][i]["header"] for i in sorted(pairs)]
        out.append(finding("column order" + tag, "different", names_by, None,
                           "'%s' stands before '%s'; in the examples it comes after (%s)." % (names_by[bad], names_by[bad - 1], names)))
    for i, (act, how) in pairs.items():
        col = e["columns"][i]
        field = "format of '%s'" % col["header"]
        if col["format"] and col["format_class"] != "general":
            if act["format"] == col["format"]:
                out.append(finding(field, "same", col["format"], act["format"], ""))
            elif act["format_class"] == col["format_class"]:
                out.append(finding(field, "close", col["format"], act["format"],
                                   "'%s' is shown as %s; the examples use %s." % (col["header"], act["format"], col["format"])))
            else:
                out.append(finding(field, "different", col["format"], act["format"],
                                   "'%s' is shown as %s; the examples show it as %s (%s)." % (col["header"], act["format"] or "plain numbers", col["format"], col["format_class"])))
        if col["width"] and act["width"] and abs(act["width"] / col["width"] - 1) > 0.35:
            out.append(finding("width of '%s'" % col["header"], "close", col["width"], act["width"],
                               "'%s' is %s wide; the examples make it %s." % (col["header"], act["width"], col["width"])))
    for i, (act, how) in pairs.items():
        col = e["columns"][i]
        want, got = col.get("filled"), act.get("filled")
        if want is None or got is None or col["pictures"] or want < 0.4:
            continue
        figures = col.get("figured") is not None and act.get("figured") is not None and col["figured"] >= 0.8 * want
        if figures:
            want, got = col["figured"], act["figured"]
        verdict = "different" if got < want / 2 else "close" if got < want - 0.25 else "same"
        out.append(finding("fill of '%s'" % col["header"], verdict, want, got,
                           "" if verdict == "same" else ("'%s' has a figure in %d%% of the rows; in the examples %d%%." if figures
                                                         else "'%s' is filled in %d%% of the rows; in the examples %d%%.")
                           % (col["header"], round(got * 100), round(want * 100))))
    if e["picture_columns"] and not a["picture_columns"]:
        letters = _list(e["picture_columns"])
        out.append(finding("pictures" + tag, "close", letters, None,
                           "the examples hold pictures in column %s; none are placed in this file." % letters))
    if e["totals"]:
        want = e["totals"][0]
        got = next((t for t in a["totals"] if not want["label"] or norm(t["label"]) == norm(want["label"])), None)
        if got is None:
            has_label = want["label"] and any(TOTAL.match(norm(t["label"])) for t in a["totals"])
            out.append(finding("total row" + tag, "missing", want["label"] or want["function"], None,
                               "there is no total row%s; the examples end with '%s' and a %s formula." % (
                                   "" if not has_label else " with that label", want["label"] or "a total", want["function"] or "sum")))
        else:
            out.append(finding("total row" + tag, "same", want["label"], got["label"], ""))
    if e["amounts_are_formulas"] and not a["amounts_are_formulas"]:
        out.append(finding("formulas" + tag, "different", True, False,
                           "the amounts are typed numbers; in the examples sums and totals are formulas."))
    if e["frozen"] and not a["frozen"]:
        out.append(finding("frozen panes" + tag, "close", e["frozen"], None,
                           "the header is not frozen; the examples freeze at %s." % e["frozen"]))
    return out


def compare_deck(e: dict, a: dict) -> list[dict]:
    out = []
    cross = e.get("source") != a.get("source")
    soft = (lambda v: "close" if v == "different" else v) if cross else (lambda v: v)
    where = " (compared across a %s and a %s, so approximate)" % (e.get("source"), a.get("source")) if cross else ""
    ea, aa = e["size"]["aspect"], a["size"]["aspect"]
    out.append(finding("page size", "same" if abs(ea - aa) / ea < 0.03 else "different", ea, aa,
                       "the pages are %.2f:1; the examples are %.2f:1." % (aa, ea)))
    efonts = [f for f in e["fonts"] if f["font"]][:3]
    afonts = {norm(f["font"]): f for f in a["fonts"]}
    aship = {f["ship"] for f in a["fonts"][:3]}
    for f in efonts[:2]:
        key = norm(f["font"])
        if key in afonts:
            out.append(finding("font " + f["font"], "same", f["font"], f["font"], ""))
        elif f["ship"] in aship and f["ship"] != "Inter":
            out.append(finding("font " + f["font"], "close", f["font"], f["ship"],
                               "the deck uses %s; the examples use %s (the free look-alike %s)." % (_list(x["font"] for x in a["fonts"][:3]), f["font"], f["ship"])))
        else:
            out.append(finding("font " + f["font"], "different", f["font"], _list(x["font"] for x in a["fonts"][:3]),
                               "the examples set text in %s; the deck uses %s." % (f["font"], _list(x["font"] for x in a["fonts"][:3]) or "no font I can read")))

    def colour(field, want, pool, plain):
        if not want:
            return
        if not pool:
            out.append(finding(field, "missing", want["hex"], None, "the deck shows no %s; the examples have %s." % (plain, want["hex"])))
            return
        best = min(pool, key=lambda c: delta_e(want["hex"], c["hex"]))
        d = delta_e(want["hex"], best["hex"])
        verdict = "same" if d <= 6 else "close" if d <= 18 else "different"
        out.append(finding(field, verdict, want["hex"], best["hex"],
                           "the %s is %s; the examples have %s." % (plain, best["hex"], want["hex"])))

    if e.get("ink") and a.get("ink"):
        colour("ink", e["ink"], [a["ink"]], "text colour")
    for k, g in enumerate(e["grounds"][:2]):
        colour("page colour %s" % g["hex"], g, a["grounds"], "page colour")
    for g in e["accents"][:2]:
        colour("accent %s" % g["hex"], g, a["accents"], "accent colour")
    if e["opening"]:
        n = min(len(e["opening"]), len(a["opening"]))
        verdict = "same" if e["opening"][:n] == a["opening"][:n] else "close" if e["opening"][:1] == a["opening"][:1] else "different"
        out.append(finding("opening pages", soft(verdict), e["opening"], a["opening"],
                           "the deck opens with %s; the examples open with %s%s." % (_list(a["opening"]), _list(e["opening"]), where)))
    if e["closing"]:
        out.append(finding("closing page", soft("same" if e["closing"] == a["closing"] else "different"), e["closing"], a["closing"],
                           "the deck ends on a %s; the examples end on a %s%s." % (a["closing"], e["closing"], where)))
    for kind, share in e["shares"].items():
        if share < 10:
            continue
        got = a["shares"].get(kind, 0)
        gap = abs(got - share)
        verdict = "same" if gap <= 5 else "close" if gap <= 10 else "different"
        if got == 0:
            verdict = "missing"
        out.append(finding("page type '%s'" % kind, soft(verdict) if verdict != "missing" else "close" if cross else "missing", share, got,
                           "%s are %.0f%% of the pages; in the examples %.0f%%%s." % (kind, got, share, where)))
    if e["words_median"]:
        ratio = a["words_median"] / e["words_median"] if e["words_median"] else 1
        verdict = "same" if abs(ratio - 1) <= 0.35 else "close" if abs(ratio - 1) <= 0.7 else "different"
        out.append(finding("words per page", soft(verdict), e["words_median"], a["words_median"],
                           "a page holds %d words (median); the examples hold %d%s." % (a["words_median"], e["words_median"], where)))
    gap = abs(a["picture_share"] - e["picture_share"])
    out.append(finding("pictures per page", soft("same" if gap <= 10 else "close" if gap <= 25 else "different"),
                       e["picture_share"], a["picture_share"],
                       "%.0f%% of the pages carry pictures; in the examples %.0f%%%s." % (a["picture_share"], e["picture_share"], where)))
    return out


def compare(expected: dict, actual: dict) -> list[dict]:
    """Findings of a new file against the examples' fingerprint: {field, verdict, expected, actual, note}, verdict
    same, close, missing or different."""
    if expected.get("kind") != actual.get("kind"):
        return [finding("kind of file", "different", expected.get("kind"), actual.get("kind"),
                        "the examples are a %s; this file is a %s." % (expected.get("kind"), actual.get("kind")))]
    if expected["kind"] == "deck":
        return compare_deck(expected, actual)
    out = []
    used: set[int] = set()
    for index, sheet in enumerate(expected["sheets"]):
        match = next((i for i, s in enumerate(actual["sheets"]) if i not in used and not sheet["default_name"] and norm(s["name"]) == norm(sheet["name"])), None)
        if match is None and index < len(actual["sheets"]) and index not in used:
            match = index
        if match is None:
            out.append(finding("sheet '%s'" % sheet["name"], "missing", sheet["name"], None, "the sheet '%s' is missing." % sheet["name"]))
            continue
        used.add(match)
        out.extend(compare_sheet(sheet, actual["sheets"][match], actual["sheets"][match]["name"] if len(expected["sheets"]) > 1 else ""))
    return out


def lines(findings: list[dict], suffix: str = "") -> tuple[list[str], dict]:
    count = Counter()
    out = []
    for f in findings:
        count["off" if f["verdict"] in ("missing", "different") else f["verdict"]] += 1
        if f["verdict"] == "same":
            continue
        word = "WARN" if f["verdict"] == "close" else "FAIL"
        note = f["note"][0].upper() + f["note"][1:] if f["note"] else ""
        out.append("%s %s: %s%s" % (word, f["field"], note, suffix))
    return out, count


# ----------------------------------------------------------------------------- command line

def load_examples(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else [data]
    return [i for i in items if isinstance(i, dict)]


def installed_examples(file: Path) -> list[tuple[str, dict]]:
    """The examples of the company packs installed above a file: .nodejam/examples/*.json in its folder or a
    folder above it, else those of the pack the app installed for the organization (NODEJAM_COMPANY_PACK)."""
    here = file.resolve().parent
    for _ in range(8):
        folder = here / ".nodejam" / "examples"
        if folder.is_dir():
            return [(p.stem, e) for p in sorted(folder.glob("*.json")) for e in load_examples(p)]
        if here.parent == here:
            break
        here = here.parent
    company = os.environ.get("NODEJAM_COMPANY_PACK")
    folder = Path(company) / "examples" if company else None
    if folder and folder.is_dir():
        return [(p.stem, e) for p in sorted(folder.glob("*.json")) for e in load_examples(p)]
    return []


def chain_findings(path: Path) -> list[str]:
    """FAIL lines for a property file that skipped the chain's own scripts (a customer r19, 2026-10-18: the company's
    list skill came first, the model filled the starter by hand with the plan's 34 rooms and a ceiling row in each,
    redrew it from the deck when the turn's end check asked, rebuilt the budget and handed back the tidplan laid
    from the first list). An article list beside a concept deck made here is drawn from that deck; a tidplan laid
    from a list is laid again when the list changes after it."""
    import os
    try:
        import openpyxl
        book = openpyxl.load_workbook(path, read_only=False, **STOCK_LOAD)
    except Exception:
        return []
    out = []
    skills = os.environ.get("NODEJAM_SKILLS") or str(Path(__file__).resolve().parents[1])
    if (book.properties.identifier or "") == "tidplan/1.0" and len(book.worksheets) >= 4:
        for row in book.worksheets[3].iter_rows(min_row=2, values_only=True):
            source = row[2] if len(row) > 2 else None
            if row[0] in ("Block", "Blocks") and isinstance(source, str) and source.endswith(".xlsx"):
                listed = path.parent / source
                if listed.is_file() and listed.stat().st_mtime > path.stat().st_mtime + 1:
                    out.append("FAIL chain: %s changed after this tidplan was laid from it; lay it again: python3 "
                               "\"%s/property/tidplan/scripts/from_list.py\" \"%s\" --out \"%s\" --opening <the same date>"
                               % (source, skills, source, path.name))
                break
        return out
    # A tidplan the chat wrote itself beside a list drawn here (a customer r21, 2026-10-18: build_tidplan.py, six rooms
    # stepped a week apart, no order from the list). The customer's own tidplan was saved by a person, not openpyxl.
    titled = path.name.lower().startswith("tidplan") or any(ws.title.lower().startswith("tidplan") for ws in book.worksheets)
    if titled and (book.properties.creator or "") == "openpyxl":
        lists = [p for p in sorted(path.parent.glob("*.xlsx")) if p != path and p.name.lower().startswith("artikellista")]
        source = lists[0].name if lists else "<artikellista.xlsx>"
        out.append("FAIL chain: this tidplan was not laid by the tidplan script; lay it from the article list: python3 "
                   "\"%s/property/tidplan/scripts/from_list.py\" \"%s\" --out \"%s\" --opening <the opening date>"
                   % (skills, source, path.name))
        return out
    sheet = book.worksheets[0]
    is_list = any(isinstance(v, str) and v.startswith("Yta:") for row in sheet.iter_rows(max_row=12, max_col=1, values_only=True)
                  for v in row) and any(v == "Benämning" for row in sheet.iter_rows(max_row=12, values_only=True) for v in row)
    drawn = [prop.value for prop in book.custom_doc_props.props if prop.name == "Customer form"]
    if is_list and "vaxjo_sheet.py" not in drawn:
        area = os.environ.get("NODEJAM_WORK_AREA") or ""
        decks = sorted(Path(area).glob("koncept/*/roster.json")) if area else []
        if decks:
            deck = decks[-1].parent
            out.append("FAIL chain: a concept deck made here is in %s; draw the list from it, not by hand: python3 "
                       "\"%s/property/artikellista/scripts/vaxjo_sheet.py\" skeleton \"%s\" --deck \"%s\" --title \"<title>\" "
                       "(the company's form stays: its columns and rows are the same)" % (deck.name, skills, path.name, deck))
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    fp = sub.add_parser("fingerprint")
    fp.add_argument("file")
    fp.add_argument("--company-words", nargs="*", default=[])
    ck = sub.add_parser("check")
    ck.add_argument("file")
    ck.add_argument("--examples", default=None)
    ck.add_argument("--installed", action="store_true")
    for ignored in ("--if-claimed", "--since", "--in", "--stage"):
        ck.add_argument(ignored, nargs="?", const="", default=None)
    args = parser.parse_args(argv)
    if args.cmd == "fingerprint":
        try:
            result = fingerprint(args.file, args.company_words)
        except Exception as error:
            print("pack check not checked: %s" % error, file=sys.stderr)
            return 3
        json.dump(result, sys.stdout, ensure_ascii=False, indent=1)
        print()
        return 0
    path = Path(args.file)
    if not path.is_file():
        print("pack check not checked: %s is not there" % path.name)
        return 3
    if path.suffix.lower() not in SHEETS | DECKS:
        return 0
    chain = chain_findings(path) if path.suffix.lower() == ".xlsx" else []
    for line in chain:
        print(line)
    if args.examples:
        pool = [(Path(args.examples).stem, e) for e in load_examples(Path(args.examples))]
    elif args.installed:
        pool = installed_examples(path)
    else:
        parser.error("check needs --examples <fingerprint.json> or --installed")
    wanted = []
    for form, wrapper in pool:
        expected = wrapper.get("fingerprint", wrapper)
        if expected.get("kind") not in ("sheet", "deck"):
            continue
        if args.installed:
            pattern = wrapper.get("name") or expected.get("name_pattern")
            if not pattern or not name_matches(pattern, path.name, 0.6):
                continue
            if (expected["kind"] == "sheet") != (path.suffix.lower() in SHEETS):
                continue
        wanted.append((form, expected))
    if not wanted:
        return 1 if chain else 0
    try:
        actual = fingerprint(path)
    except Exception as error:
        print("pack check not checked: examples check could not read %s (%s)" % (path.name, str(error)[:120]))
        return 3
    if actual.get("kind") == "document":
        return 0
    failed = False
    total = Counter()
    for form, expected in wanted:
        text, count = lines(compare(expected, actual), " (examples: %s)" % form if len(wanted) > 1 else "")
        total.update(count)
        for line in text:
            print(line)
            failed = failed or line.startswith("FAIL")
    print("examples check: %d fields same, %d close, %d off" % (total["same"], total["close"], total["off"]))
    return 1 if failed or chain else 0


if __name__ == "__main__":
    sys.exit(main())
