#!/usr/bin/env python3
"""What the notes held and the page does not; what the page says and the notes do not.

  NOTES-FLOOR   A question, never a fail. The check reads the person's own files in the folder it was told
                about with --in (else the folder the page is in): text files, mail, spreadsheets, PDFs, Word
                files; never the page itself, never the data file a builder was given, never a page a builder
                wrote. It pulls the hard tokens out of them (e-mail addresses, IBANs, phone numbers, tax and
                register numbers, document numbers, dates, amounts) and lists those the notes hold and the page
                does not. A token the page carries in a form a few characters off (an e-mail address with
                another domain, a number with a digit changed) is named as changed, with both forms.
                The other way, for the documents whose numbers the model writes itself (a deck, a letter,
                minutes): a figure in the text of the data file that is nowhere in the notes and is not a sum,
                a difference, a product or a share of figures that are is listed too. A figure a builder
                works out (a total, a tax) is never read: only the words and values the data file gives.

The rule passes with a WARN line and the Stop hook and the app's pack check send it back ONCE as a question:
"the notes hold these and the page does not: ... Put them on the page or say why not", "these figures are on the
page and not in your notes: ... Say where each comes from or take it out". It is never a FAIL: notes hold
things that do not belong on the page, and a model told to fix what is not broken makes the page worse. It does
not run when the folder holds no notes.

A house rule (a floor under every pack), not a rule from a standard. It reads tokens, never meaning: a fact
written in words ("the board sits in Gothenburg") is not seen, and a pass says nothing about them.

check(rule_id, path, case, stage) -> (passed, evidence). Standard library only; pdftotext reads a PDF.
"""
import datetime as dt
import difflib
import html as _html
import json
import os
import re
import subprocess
import sys
import time
import zipfile
from decimal import Decimal, InvalidOperation
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "_shared"))

RULES = ("NOTES-FLOOR",)
TEXT_FILES = (".txt", ".md", ".csv", ".tsv", ".eml", ".json", ".yaml", ".yml", ".rtf", ".html", ".htm")
MAX_FILES, MAX_BYTES, MAX_SECONDS, MAX_LISTED = 60, 1_500_000, 20, 12
# The packs whose numbers the model writes itself: the figures in their data files are held against the notes.
WRITES_FIGURES = ("business-deck", "html-deck", "business-letter", "meeting-minutes")


# ---- the person's files, the page and the data file -----------------------------------------------------

def _recognisers():
    """What each pack's own data file looks like (pack.json "recognises"), so a builder's data file is never
    read as a note: [(pack, file ending, keys it has, keys it has not)]."""
    out = []
    for pack in sorted(HERE.parent.glob("*/pack.json")):
        try:
            rule = json.loads(pack.read_text()).get("recognises") or {}
        except (ValueError, OSError):
            continue
        if rule.get("has"):
            out.append((pack.parent.name, str(rule.get("file") or "*").replace("*", "").lower(),
                        list(rule["has"]), list(rule.get("without") or [])))
    return out


def data_file_of(data, name, known=None):
    """The pack whose builder this JSON is the data file of, or ""."""
    if not isinstance(data, dict):
        return ""
    for pack, ending, has, without in (known if known is not None else _recognisers()):
        if name.lower().endswith(ending) and all(k in data for k in has) and not any(k in data for k in without):
            return pack
    return ""


# A builder signs what it writes: "business-deck/0.3.0 ..." in an office file's dc:identifier or a PDF's Creator.
# Such a file is an output (a deck made earlier in the chat, its printed PDF), never the person's notes: read as
# notes, its cover date and its table style's GUID came back as "the notes hold these" (Mac sweep 2026-10-12).
BUILDER = re.compile(r"^\s*([a-z][a-z0-9-]*)/\d+\.\d+")
GUID = re.compile(r"\{?[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\}?")


def _builder_wrote(mark):
    found = BUILDER.match(mark or "")
    if not found:
        return False
    # A pack sits at skills/<name> or one group down (skills/property/<name>).
    name = found.group(1)
    return any((HERE.parent / name / f).is_file() or any(HERE.parent.glob("*/%s/%s" % (name, f))) for f in ("pack.json", "SKILL.md"))


def _signed(path):
    """True when a pack's builder wrote this office file or PDF."""
    kind = path.suffix.lower()
    if kind == ".pdf":
        out = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True, timeout=20).stdout
        creator = next((line.split(":", 1)[1] for line in out.splitlines() if line.startswith("Creator:")), "")
        return _builder_wrote(creator)
    with zipfile.ZipFile(path) as z:
        # The article list's builder marks its own workbook (vaxjo_sheet.py, "Customer form"); read as notes, an
        # earlier chain's list and budget came back on a painting quote as "the figures in the other Östersund files"
        # (2026-10-15).
        if "docProps/custom.xml" in z.namelist() and b"vaxjo_sheet.py" in z.read("docProps/custom.xml"):
            return True
        if "docProps/core.xml" not in z.namelist():
            return False
        core = z.read("docProps/core.xml").decode("utf-8", "ignore")
    found = re.search(r"<dc:identifier>([^<]*)</dc:identifier>", core)
    return bool(found) and _builder_wrote(_html.unescape(found.group(1)))


def _read(path, known):
    """(text, data file's pack and content or None) of one file in the person's folder."""
    kind = path.suffix.lower()
    try:
        if path.stat().st_size > MAX_BYTES:
            return "", None
        if kind in TEXT_FILES:
            text = path.read_text(errors="ignore")
            if kind in (".html", ".htm"):
                if 'name="generator" content="nodejam-' in text:
                    return "", None                            # a page a builder wrote is an output, not a note
                text = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", text)
                text = re.sub(r"(?i)<(br|/p|/div|/li|/tr|/h\d)\b[^>]*>", "\n", text)
                text = _html.unescape(re.sub(r"<[^>]+>", " ", text))
            if kind == ".json":
                try:
                    data = json.loads(text)
                except ValueError:
                    return text, None
                if path.name in ("case.json", "company.json"):
                    return "", None                            # a case's own truth; the company file has its own rule
                if path.name.lower().endswith("look.json"):
                    return "", None                            # a builder's look file: drawing settings, not notes
                pack = data_file_of(data, path.name, known)
                if pack:
                    return "", (pack, data)                    # a builder's data file: what the model wrote
            return text, None
        if kind in (".pdf", ".docx", ".xlsx", ".pptx") and _signed(path):
            return "", None                                    # a builder's own output, not a note
        if kind == ".pdf":
            out = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True, timeout=20)
            return out.stdout, None
        if kind in (".docx", ".xlsx", ".pptx"):
            return _office_text(path), None
    except (OSError, KeyError, ValueError, zipfile.BadZipFile, subprocess.SubprocessError):
        return "", None
    return "", None


def _office_text(path):
    kind = path.suffix.lower()
    part = {".docx": r"word/(document|header\d*|footer\d*)\.xml$",
            ".xlsx": r"xl/(sharedStrings|worksheets/sheet\d+)\.xml$",
            ".pptx": r"ppt/(slides/slide\d+|notesSlides/notesSlide\d+)\.xml$"}[kind]
    out = []
    with zipfile.ZipFile(path) as z:
        for name in sorted(z.namelist()):
            if re.match(part, name):
                xml = z.read(name).decode("utf-8", "ignore")
                # A table style or other part id is markup, not words on the page.
                xml = GUID.sub(" ", re.sub(r"(?s)<a:tableStyleId>.*?</a:tableStyleId>", " ", xml))
                xml = re.sub(r"</w:p>|</si>|</a:p>|</row>|<w:br/>|<w:tab/>|</c>", "\n", xml)
                out.append(_html.unescape(re.sub(r"<[^>]+>", " ", xml)))
    return "\n".join(out)


def page_text(path):
    """Every word of the output: a PDF read twice (in reading order and laid out), an office file from its
    parts, a page as text."""
    path = Path(path)
    kind = path.suffix.lower()
    try:
        if kind == ".pdf":
            out = []
            for args in ((), ("-layout",)):
                out.append(subprocess.run(["pdftotext", *args, str(path), "-"], capture_output=True, text=True,
                                          timeout=60).stdout)
            return "\n\n".join(out)
        if kind in (".docx", ".xlsx", ".pptx"):
            return _office_text(path)
        if kind in (".html", ".htm"):
            text = path.read_text(errors="ignore")
            text = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", text)
            return _html.unescape(re.sub(r"<[^>]+>", " ", text))
        return path.read_text(errors="ignore")
    except (OSError, KeyError, ValueError, zipfile.BadZipFile, subprocess.SubprocessError):
        return ""


def read_folder(output, folder=""):
    """(notes, data files): the person's own files as [(name, text)], and the builders' data files in the
    folder as [(name, pack, data)]. The output, the files of its name beside it and builder pages are left
    out; hidden folders and anything deeper than two folders are not read."""
    output = Path(output).resolve()
    root = Path(folder).resolve() if folder else output.parent
    if not root.is_dir():
        return [], []
    known = _recognisers()
    notes, data, started = [], [], time.monotonic()
    for base, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d != "node_modules")
        if len(Path(base).relative_to(root).parts) >= 2:
            dirs[:] = []
        for name in sorted(names):
            path = Path(base) / name
            if name.startswith(".") or (path.parent == output.parent and path.stem == output.stem):
                continue
            if len(notes) >= MAX_FILES or time.monotonic() - started > MAX_SECONDS:
                return notes, data
            text, found = _read(path, known)
            if found:
                data.append((str(path.relative_to(root)), found[0], found[1]))
            elif text.strip():
                notes.append((str(path.relative_to(root)), text))
    return notes, data


# ---- hard tokens ----------------------------------------------------------------------------------------

EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+")
IBAN = re.compile(r"\b[A-Z]{2}\d{2}(?:[  ]?[A-Z0-9]{4}){2,7}(?:[  ]?[A-Z0-9]{1,4})?\b")
# A document number: letters, a separator and digits (PO-2026-0642, Q-20931, HM/2026/114), a year with a series
# (2026-A-0158, 2026/0312) or letters run into digits (ABC1234).
DOCNO = re.compile(r"\b[A-Z]{1,6}[-/]\d{2,}(?:[-/][A-Z0-9]+)*\b|\b\d{4}[-/][A-Z0-9]{1,4}[-/]\d{2,}\b"
                   r"|\b\d{4}/\d{3,}\b|\b\d{1,4}/\d{4}\b|\b[A-Z]{2,5}\d{4,}\b")
# A run of digits in groups (556012-3456, GB 123 4567 82, 031-000 00 00, 01234567897): five digits or more.
RUN = re.compile(r"(?<![\w.,])(?:\+|[A-Z]{1,3}[ \-]?)?\d+(?:(?:[ \u00a0\-/]|\.(?=\d))\d+)*(?![\w])")
PERCENT = re.compile(r"(?<![\w.,])(\d{1,3}(?:[.,]\d{1,2})?)\s?%")
AMOUNT = re.compile(r"(?<![\w.,])\d{1,3}(?:[   .,']\d{3})*[.,]\d{2}(?!\d)|(?<![\w.,])\d{1,3}(?:[   .,']\d{3})+(?![\d])")


def _months():
    import letter
    names = {}
    for key, line in letter.MONTH_NAMES.items():
        for i, word in enumerate(line.split(), 1):
            names[word.lower()] = i
    extra = ("jan feb mar apr may jun jul aug sep oct nov dec", "sept", "jänner",
             "styczeń luty marzec kwiecień maj czerwiec lipiec sierpień wrzesień październik listopad grudzień",
             "tammikuu helmikuu maaliskuu huhtikuu toukokuu kesäkuu heinäkuu elokuu syyskuu lokakuu marraskuu joulukuu",
             "janv févr mars avr mai juin juil août sept oct nov déc")
    for line in extra:
        words = line.split()
        if len(words) == 12:
            for i, word in enumerate(words, 1):
                names.setdefault(word, i)
    names.setdefault("sept", 9)
    names.setdefault("jänner", 1)
    return names


MONTHS = _months()
_MONTH = "|".join(sorted((re.escape(m) for m in MONTHS), key=len, reverse=True))
DATE_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
DATE_NUM = re.compile(r"(?<![\d.])(\d{1,2})[./](\d{1,2})[./](\d{4})\b")
DATE_DMY = re.compile(r"(?<![\w])(\d{1,2})(?:er|st|nd|rd|th|\.|:e|\.º|º)?\s+(?:de\s+|of\s+|den\s+)?(%s)\.?(?:\s+de)?,?\s+(\d{4})\b" % _MONTH, re.I)
DATE_MDY = re.compile(r"(?<![\w])(%s)\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b" % _MONTH, re.I)


def _iso(y, m, d):
    try:
        return dt.date(int(y), int(m), int(d)).isoformat()
    except ValueError:
        return None


def dates(text):
    """{iso date: as written} for every date with its year in the text; a numeric date reads both ways round
    where both are dates (3/4/2026)."""
    out = {}
    for m in DATE_ISO.finditer(text):
        out.setdefault(_iso(*m.groups()), m.group(0))
    for m in DATE_NUM.finditer(text):
        a, b, y = m.groups()
        out.setdefault(_iso(y, b, a), m.group(0))
        out.setdefault(_iso(y, a, b), m.group(0))
    for m in DATE_DMY.finditer(text):
        out.setdefault(_iso(m.group(3), MONTHS[m.group(2).lower()], m.group(1)), m.group(0))
    for m in DATE_MDY.finditer(text):
        out.setdefault(_iso(m.group(3), MONTHS[m.group(1).lower()], m.group(2)), m.group(0))
    out.pop(None, None)
    return out


def _without(text, *patterns):
    for p in patterns:
        text = p.sub(lambda m: " " * len(m.group(0)), text)
    return text


def squeeze(text):
    """A text with what a number is grouped by taken out, in capitals: 556012-3456 and 556012 3456 read alike."""
    return re.sub(r"[\s  .\-/()']", "", str(text or "")).upper()


def _readings(token):
    """Every amount a written number can be: 1.234,50 and 1,234.50 both give 1234.50."""
    import purchase_order_check as po
    return po.numbers(token)


def tokens(text):
    """The hard tokens of a text by kind: {"email": {normalised: as written}, "iban": ..., "date": ...,
    "docno": ..., "run": ..., "amount": {as written: readings}, "percent": {as written: readings}}."""
    out = {"email": {}, "iban": {}, "date": {}, "docno": {}, "run": {}, "amount": {}, "percent": {}}
    for m in EMAIL.finditer(text):
        out["email"].setdefault(m.group(0).rstrip(".").lower(), m.group(0).rstrip("."))
    rest = _without(text, EMAIL)
    for m in IBAN.finditer(rest):
        if len(squeeze(m.group(0))) >= 15:
            out["iban"].setdefault(squeeze(m.group(0)), m.group(0).strip())
    rest = _without(rest, IBAN)
    out["date"] = dates(rest)
    rest = _without(rest, DATE_ISO, DATE_NUM, DATE_DMY, DATE_MDY)
    for m in DOCNO.finditer(rest):
        out["docno"].setdefault(squeeze(m.group(0)), m.group(0))
    rest = _without(rest, DOCNO, CLOCK)
    for m in PERCENT.finditer(rest):
        out["percent"].setdefault(m.group(0), _readings(m.group(1)))
    rest = _without(rest, PERCENT)
    for m in AMOUNT.finditer(rest):
        out["amount"].setdefault(m.group(0).strip(), _readings(m.group(0)))
    rest = _without(rest, AMOUNT)
    for m in RUN.finditer(rest):
        raw = m.group(0).strip(" .-/(")
        if len(re.sub(r"\D", "", raw)) < 5:
            continue
        if raw.count(".") == 1 and re.search(r"\.\d{1,2}$", raw):
            continue                       # a figure with decimals beside another number, not a number of its own
        out["run"].setdefault(squeeze(raw), raw)
    return out


def _near(a, b, kind):
    """Two tokens of one kind a few characters apart: the same thing, changed."""
    if kind == "email":
        la, _, da = a.partition("@")
        lb, _, db = b.partition("@")
        return la == lb or da == db or difflib.SequenceMatcher(None, a, b).ratio() >= 0.75
    if abs(len(a) - len(b)) > 2:
        return False
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.8


def held_back(notes_text, page):
    """(missing, changed): what the notes hold and the page does not, as written in the notes; and the pairs
    (as the notes write it, as the page writes it) where the page carries it a few characters off."""
    have, want = tokens(page), tokens(notes_text)
    flat = squeeze(page)
    digits = re.sub(r"\D", "", page)
    import purchase_order_check as po
    page_numbers = po.numbers(page)
    missing, changed = [], []
    for kind in ("email", "iban", "docno", "run"):
        spare = {k: v for k, v in have[kind].items() if k not in squeeze(notes_text) and k not in want[kind]}
        if kind == "email":
            spare = {k: v for k, v in have[kind].items() if k not in want[kind]}
        for key, written in want[kind].items():
            if kind == "email":
                on = key in page.lower()
            else:
                on = key in flat
                if not on and kind == "run" and key.isdigit() and len(key) >= 8:
                    on = key[-8:] in digits            # a phone number with or without its country code
            if on:
                continue
            twin = next((v for k, v in spare.items() if _near(key, k, kind)), None)
            if twin:
                changed.append((written, twin))
            else:
                missing.append(written)
    for iso, written in want["date"].items():
        if iso not in have["date"]:
            missing.append(written)
    for kind in ("amount", "percent"):
        for written, readings in want[kind].items():
            if readings and not any(po.has(page_numbers, r) for r in readings):
                missing.append(written)
    return list(dict.fromkeys(missing)), list(dict.fromkeys(changed))


# ---- identifiers the model made up ---------------------------------------------------------------------

# A tax or register number on a page is a fact the person's files give. A VAT number worked out from an
# organisation number (Sweden: SE, the ten digits and 01) is not one, even when the form is right: the page then
# states a number nobody gave. The labels below are the words invoices, letters and orders put before such a
# number, and the shapes are the forms EU VAT numbers take (the VIES country list: the prefix and the digits).
ID_LABEL = re.compile(
    r"(?<![\w])(?:VAT(?:\s?(?:ID|No\.?|number|reg\w*))?|MVA|moms\w*|USt\.?-?\s?Id\w*|UID(?:-?Nr\.?)?|BTW(?:-?(?:nr|id)\.?)?|TVA|"
    r"(?:P\.?\s?)?IVA|NIF|CIF|NIP|REGON|KRS|IČO|IČ\s?DPH|DIČ|CVR|KvK|Org\.?\s?-?(?:nr|nummer)\.?|organisations?nummer|"
    r"Y-tunnus|SIREN|SIRET|RCS|HRB|FN|ABN|ACN|EIN|Company\s(?:No|number)\.?|Steuernummer|Ondernemingsn\w*|"
    r"Handelsregister\w*)(?![a-zA-Z])[\s.:#]*(?:nr\.?|no\.?|number)?[\s.:#]*"
    r"((?:[A-Z]{1,3}\s?)?\d+(?:[ .\-/]\d+)*(?:[A-Z]\d{1,2}|[A-Z]{1,2})?)", re.I)
VAT_SHAPE = re.compile(
    r"(?<![\w])((?:ATU|BE|BG|CY|CZ|DE|DK|EE|EL|ES|FI|FR|HR|HU|IE|IT|LT|LU|LV|MT|NL|PL|PT|RO|SE|SI|SK|GB|XI|NO|CHE)"
    r"\s?[0-9A-Z]\d*(?:[ .\-]\d+)*(?:[A-Z]\d{1,2})?)(?![\w])")
ID_SUFFIX = re.compile(r"(MVA|MWST|IVA|TVA|BTW)$")


def _core(raw):
    """An identifier with spaces, dots, dashes and slashes set aside, the country prefix and a tail like MVA off."""
    norm = re.sub(r"[^0-9A-Za-z]", "", raw).upper()
    norm = re.sub(r"^[A-Z]{2,3}(?=\d)", "", norm)
    return ID_SUFFIX.sub("", norm)


def identifiers_not_in_notes(page, notes_text):
    """The tax and register numbers the page prints that the notes do not hold in any grouping: the page's words
    as written, once each. A number the notes hold with other spaces, dots, dashes or a country prefix is held."""
    held = re.sub(r"[^0-9A-Za-z]", "", notes_text).upper()
    out = []
    for rx in (ID_LABEL, VAT_SHAPE):
        for m in rx.finditer(page):
            raw = m.group(1).strip(" .-/")
            if len(re.sub(r"\D", "", raw)) < 6 or re.search(r"[a-z]{3,}", raw):
                continue
            if rx is VAT_SHAPE and len(re.sub(r"\D", "", raw)) < 8:
                continue
            core = _core(raw)
            if len(core) < 6 or core in held:
                continue
            shown = re.sub(r"\s+", " ", raw)
            if not any(_core(x) == core for x in out):
                out.append(shown)
    return out


def company_text(output, folder=""):
    """The text of company.json in the folder, else beside the output: the company's own particulars, written
    once, give its tax and register numbers as the notes do (COMPANY-FILE reads the page against it)."""
    for root in ([Path(folder)] if folder else []) + [Path(output).resolve().parent]:
        try:
            return (root / "company.json").read_text(errors="ignore")
        except OSError:
            continue
    return ""


INCOTERM = re.compile(r"\b(EXW|FCA|FAS|FOB|CFR|CIF|CPT|CIP|DAP|DPU|DDP)\b[^\n]{0,80}?Incoterms|Incoterms[^\n]{0,40}?\b(EXW|FCA|FAS|FOB|CFR|CIF|CPT|CIP|DAP|DPU|DDP)\b")


def incoterms_not_in_notes(page, notes_text):
    """The Incoterms 2020 rules the page names (a rule beside the word Incoterms) that the notes do not name."""
    out = []
    for m in INCOTERM.finditer(page):
        rule = m.group(1) or m.group(2)
        if rule not in out and not re.search(r"\b%s\b" % rule, notes_text, re.I):
            out.append(rule)
    return out


# ---- figures the model wrote ----------------------------------------------------------------------------

FIGURE = re.compile(r"(?<![\w.,/\-])\d[\d   .,']*\d(?![\w/\-])|(?<![\w.,/\-])\d(?![\w/\-.,]*\d)")
TIME = re.compile(r"\b([01]?\d|2[0-3])[:.][0-5]\d\b(?!\s?%)")
# A time of day the notes say is one ("closed 11.15", "at 10.30", "11.15am", "14.00 Uhr"): a time, never an
# amount, whichever separator the page then writes it with (a real run, 2026-10-13: "11.15" asked about against
# "11:15"). A bare 11.15 may be money and stays a figure.
CLOCK = re.compile(r"(?i)\b(?:at|closed|opened|started|ended|from|until|till|by|kl\.?|klockan|um|à|alle|om)\s+"
                   r"(?:[01]?\d|2[0-3])[.:][0-5]\d\b|\b(?:[01]?\d|2[0-3])[.:][0-5]\d\s?(?:am|pm|a\.m\.|p\.m\.|h|uhr)\b")
ORDINAL = re.compile(r"(?m)^\s*\d{1,2}[.)]\s|§\s*\d+|\b(?:Q[1-4]|H[12])\b")
YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
DAY_MONTH = re.compile(r"(?<![\w])\d{1,2}(?:er|st|nd|rd|th|\.)?\s+(?:de\s+|of\s+)?(?:%s)\b|\b(?:%s)\.?\s+\d{1,2}(?:st|nd|rd|th)?\b" % (_MONTH, _MONTH), re.I)


def prose(value, out, numbers=False):
    """Every string a data file gives that reads as written text (and, for a deck, its numbers): what the
    model wrote. Keys that hold a date, an address, a phone number or a name are not prose."""
    skip = {"date", "start", "end", "issue_date", "due_date", "given", "street", "postcode", "city", "country",
            "phone", "email", "iban", "bic", "vat_id", "register_number", "number", "company_number", "language",
            "when", "period", "decimals", "density", "type", "kind", "layout", "highlight", "place", "address",
            "registered_office", "notice_address", "register", "registration", "share_capital", "paid_up_capital"}
    if isinstance(value, dict):
        for k, v in value.items():
            if str(k).startswith("_") or k in skip:
                continue
            prose(v, out, numbers)
    elif isinstance(value, list):
        for v in value:
            prose(v, out, numbers)
    elif isinstance(value, str):
        out.append(value)
    elif numbers and isinstance(value, (int, float)) and not isinstance(value, bool):
        out.append(format(Decimal(str(value)).normalize(), "f"))
    return out


def figures(text):
    """{as written: Decimal} for the figures of a text: no dates, times, years, e-mail addresses, IBANs,
    document numbers, list numbers or whole numbers under 4."""
    rest = _without(text, EMAIL, IBAN, DATE_ISO, DATE_NUM, DATE_DMY, DATE_MDY, DAY_MONTH, DOCNO, TIME, ORDINAL, YEAR)
    out = {}
    for m in FIGURE.finditer(rest):
        raw = m.group(0).strip("   .,'")
        if not raw:
            continue
        readings = _readings(raw)
        if not readings:
            continue
        value = min(readings) if len(readings) > 1 and re.fullmatch(r"\d{1,3}[.,]\d{3}", raw) else max(readings)
        if value == value.to_integral_value() and abs(value) < 4:
            continue
        out.setdefault(raw, value)
    return out


def _all_numbers(text):
    """Every number of the notes, in every reading, dates' own numbers left out."""
    import purchase_order_check as po
    rest = _without(text, EMAIL, IBAN, DATE_ISO, DATE_NUM)
    return po.numbers(rest)


def _places(d):
    return max(0, -d.as_tuple().exponent)


def _operands(line):
    """The numbers of one line of the notes that a figure may be worked out from: no dates, times or years."""
    import purchase_order_check as po
    rest = _without(line, EMAIL, IBAN, DATE_ISO, DATE_NUM, DATE_DMY, DATE_MDY, DAY_MONTH, DOCNO, TIME, ORDINAL, YEAR)
    out = []
    for m in FIGURE.finditer(rest):
        readings = po.numbers(m.group(0))
        if readings:
            out.append(max(readings))
    return out[:16]


SHARE = re.compile(r"(?<![\w.,])(\d[\d.,]*)\s+(?:of|out of|von|av|af|van|de|di|sur|z|su)\s+(?:the\s+|los\s+|las\s+|les\s+)?(\d[\d.,]*)", re.I)


def derived(value, notes_text):
    """A figure that follows plainly from figures standing on one line of the notes: the sum or the difference
    of two of them, their product (a quantity times a price), the sum of the line or of a run in it, the count
    of the figures the line lists, or the share the notes give in words ("41 of 58" is 71 percent). Nothing
    looser: any small number can be made from some two of forty, so figures far apart are never combined and
    no ratio is tried that the notes do not state."""
    import purchase_order_check as po
    q = Decimal(1).scaleb(-_places(value))
    exact = lambda x: x == value or -x == value  # noqa: E731
    near = lambda x: x.quantize(q) == value  # noqa: E731
    for m in SHARE.finditer(notes_text):
        a, b = (max(po.numbers(g) or [Decimal(0)]) for g in m.groups())
        if b and (near(a / b * 100) or near((b - a) / b * 100)):
            return True
    for line in notes_text.splitlines():
        pool = _operands(line)
        if len(pool) < 2:
            continue
        if value == len(pool) and value <= 31:
            return True
        for x, a in enumerate(pool):
            total = Decimal(0)
            for y in range(x, len(pool)):
                total += pool[y]
                if y > x and exact(total):
                    return True
            for y, b in enumerate(pool):
                if x != y and (exact(a - b) or (a * b).quantize(Decimal("0.01")) == value.quantize(Decimal("0.01"))):
                    return True
    return False


def not_in_notes(data, notes_text, pack):
    """The figures the data file's own text carries that are nowhere in the notes and do not follow from
    figures that stand together there."""
    known = _all_numbers(notes_text)
    import purchase_order_check as po
    out = []
    text = "\n".join(prose(data, [], numbers=pack in ("business-deck", "html-deck")))
    for raw, value in figures(text).items():
        if po.has(known, value) or po.has(known, abs(value)):
            continue
        if derived(value, notes_text):
            continue
        at = text.find(raw)
        tail = text[at + len(raw):at + len(raw) + 14]
        unit = re.match(r"\s?(%|percent|per cent|weeks?|days?|months?|years?|hours?|k\b|m\b|bn\b)", tail, re.I)
        shown = raw + (unit.group(0) if unit else "")
        if shown not in out:
            out.append(shown)
    return out


# ---- the rule -------------------------------------------------------------------------------------------

def _listed(items):
    shown = ", ".join("«%s»" % str(x)[:60] for x in items[:MAX_LISTED])
    return shown + (" and %d more" % (len(items) - MAX_LISTED) if len(items) > MAX_LISTED else "")


def judge(output, folder=""):
    """(question or "", why): the one question the notes floor has about this output."""
    # The output first: a file that cannot be read is "could not check", whatever the folder holds, so that a
    # file no rule can read is never called checked.
    page = page_text(output)
    if not page.strip():
        return "", "the output could not be read as text"
    notes, data = read_folder(output, folder)
    if not notes:
        return "", "the folder holds no notes of the person's to read the page against"
    notes_text = "\n\n".join(text for _, text in notes)
    missing, changed = held_back(notes_text, page)
    parts = []
    if changed:
        parts.append("the page changes what the notes give: %s. Write each as the notes have it; never change a "
                     "name, an address or a number" % ", ".join("«%s» is «%s» on the page" % (a[:50], b[:50]) for a, b in changed[:6]))
    if missing:
        parts.append("the notes hold these and the page does not: %s. Put them on the page or say why not"
                     % _listed(missing))
    made_up = identifiers_not_in_notes(page, notes_text + "\n" + company_text(output, folder))
    if made_up:
        parts.append("these tax or register numbers are on the page and not in your notes: %s. Take each out, or say "
                     "where the notes give it; a number is never built from another one (a VAT number from an "
                     "organisation number), and a number the person does not have is declared unknown, not guessed"
                     % _listed(made_up))
    terms = incoterms_not_in_notes(page, notes_text)
    if terms:
        parts.append("the page names the Incoterms 2020 rule %s and your notes name none: a delivery term is the "
                     "person's agreement, never a default. Take it out and say the notes do not give one, or ask"
                     % _listed(terms))
    extra = []
    for _name, pack, content in data:
        if pack in WRITES_FIGURES:
            extra += [x for x in not_in_notes(content, notes_text, pack) if x not in extra]
    if extra:
        parts.append("these figures are on the page and not in your notes: %s. Say where each comes from or take "
                     "it out" % _listed(extra))
    names = ", ".join(n for n, _ in notes[:4]) + (" and %d more" % (len(notes) - 4) if len(notes) > 4 else "")
    if not parts:
        return "", "every hard token of the person's files (%s) is on the page" % names
    return "%s (read from %s). A question, not a fault: answer it once, in the file or in your reply" % ("; ".join(parts), names), ""


def check(rule_id, path, case, stage):
    if rule_id != "NOTES-FLOOR":
        return None, "no such rule"
    question, why = judge(Path(path), (case or {}).get("folder") or "")
    if question:
        return True, "WARN " + question
    if why.startswith("the folder holds no notes") or why.startswith("the output could not"):
        return None, why
    return True, why


def main(argv):
    if len(argv) < 2:
        print("usage: notes_floor.py <output file> [folder]")
        return 2
    question, why = judge(Path(argv[1]), argv[2] if len(argv) > 2 else "")
    print("WARN NOTES-FLOOR  " + question if question else "notes floor: " + why)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
