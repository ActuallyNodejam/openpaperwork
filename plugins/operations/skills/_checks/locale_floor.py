#!/usr/bin/env python3
"""Locale floor read off a produced file: paper, dates, numbers, currency.

check(rule_id, path, case, stage) -> (passed, evidence). None means the file carries
nothing for that rule, so it is not scored. Sources for the table live beside it in
guidelines/openpaperwork/0.1.0/locales.json.
"""


import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

# The rule code lives in the skills tree, so a pack's check runs where the pack runs. When this file
# sits in a checkout it can also see the rest of the repository (the library's own check modules load
# these files from here); inside a sandbox only the skills tree is there, and the rules that need
# more say so instead of failing the file.
def _repo_root():
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "standards/checks").is_dir():
            return parent
    for parent in here.parents:
        if (parent / "skills").is_dir():
            return parent
    return here.parents[2]


ROOT = _repo_root()


_TABLE = next(
    (p for p in (Path(__file__).resolve().parent / "locales.json",
                 ROOT / "standards/guidelines/openpaperwork/0.1.0/locales.json")
     if p.is_file()),
    Path(__file__).resolve().parent / "locales.json",
)
LOCALES = json.loads(_TABLE.read_text())["locales"]

# The CLDR long date (9. oktober 2026, 9 October 2026, October 9, 2026, 9 octobre 2026) counts as the
# locale's date too. Its month names and order live with the letter (skills/_shared/letter.py, MONTH_NAMES
# and LONG_DATE), one table for the builders and this check; without letter.py the long form is not counted.
try:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))
    import letter as _letter
except Exception:                                    # a check copied without the shared folder
    _letter = None
LONG_DATE = getattr(_letter, "LONG_DATE", None) or {}
MONTH_NAMES = getattr(_letter, "MONTH_NAMES", None) or {}


def long_date_rx(locale):
    """The locale's CLDR long date as a pattern, or None when the locale has none."""
    pattern = LONG_DATE.get(locale)
    names = MONTH_NAMES.get(str(locale)) or MONTH_NAMES.get(str(locale).split("-")[0])   # de-AT has Jänner
    if not pattern or "{month}" not in pattern or not names:
        return None
    parts = {"d": r"(?:1er|\d{1,2})", "m": r"\d{1,2}", "y": r"\d{4}",
             "month": "(?:%s)" % "|".join(re.escape(n) for n in names.split())}
    out = "".join(parts.get(tok[1:-1], re.escape(tok)) if tok.startswith("{") else re.escape(tok)
                  for tok in re.findall(r"\{\w+\}|[^{]+", pattern))
    return re.compile(r"(?<!\d)%s(?!\d)" % out, re.I)

SHORT_EU = re.compile(r"\b\d{1,2}\.\d{1,2}\.\d{2,4}\b")
SHORT_US = re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b")
LONG_US = re.compile(r"\b(?:January|February|March|April|May|June|July|August|September|October|"
                     r"November|December)\s+\d{1,2},\s+\d{4}")
LONG_EU = re.compile(r"\b\d{1,2}\.\s?(?:Januar|Februar|M\u00e4rz|April|Mai|Juni|Juli|August|"
                     r"September|Oktober|November|Dezember)\s+\d{4}")


def _paper_pt(path):
    if path.suffix.lower() == ".pdf":
        out = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True).stdout
        m = re.search(r"Page size:\s*([0-9.]+) x ([0-9.]+) pts", out)
        return (float(m.group(1)), float(m.group(2))) if m else None
    if path.suffix.lower() == ".xlsx":
        # A workbook prints on the paper its first sheet's page setup names (ECMA-376 paperSize:
        # 1 Letter, 9 A4); a sheet that names none prints on the reader's default, so nothing to check.
        with zipfile.ZipFile(path) as z:
            sheets = sorted(n for n in z.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n))
            xml = z.read(sheets[0]).decode("utf-8", "ignore") if sheets else ""
        m = re.search(r'<pageSetup[^>]*\bpaperSize="(\d+)"', xml)
        return {"1": (612.0, 792.0), "9": (595.0, 842.0)}.get(m.group(1)) if m else None
    if path.suffix.lower() in (".docx", ".pptx"):
        with zipfile.ZipFile(path) as z:
            if path.suffix.lower() == ".docx":
                xml = z.read("word/document.xml").decode("utf-8", "ignore")
                m = re.search(r'<w:pgSz[^>]*w:w="(\d+)"[^>]*w:h="(\d+)"', xml)
                if m:
                    return (int(m.group(1)) / 20.0, int(m.group(2)) / 20.0)      # twips
            else:
                xml = z.read("ppt/presentation.xml").decode("utf-8", "ignore")
                m = re.search(r'<p:sldSz[^>]*cx="(\d+)"[^>]*cy="(\d+)"', xml)
                if m:
                    return (int(m.group(1)) / 12700.0, int(m.group(2)) / 12700.0)  # EMU to pt
    return None


def _text(path):
    if path.suffix.lower() == ".pdf":
        return subprocess.run(["pdftotext", "-layout", str(path), "-"],
                              capture_output=True, text=True).stdout
    if path.suffix.lower() in (".docx", ".pptx"):
        with zipfile.ZipFile(path) as z:
            # The document's own text only: docProps/core.xml carries the created and modified
            # timestamps (2026-10-09T08:00:00Z), which are not dates the reader sees.
            return " ".join(z.read(n).decode("utf-8", "ignore")
                            for n in z.namelist() if n.endswith(".xml") and not n.startswith("docProps/"))
    if path.suffix.lower() == ".xlsx":
        # A workbook's words: the strings its cells show, shared and inline. The file's packed bytes are not
        # text (read as text, a stray "0.41" in them failed a French quotation and a stray "6,63" passed a
        # Swedish one); a number cell is written out by the reader's own program in the workbook's language,
        # so it is not an amount to read here.
        with zipfile.ZipFile(path) as z:
            parts = [z.read(n).decode("utf-8", "ignore") for n in z.namelist()
                     if n == "xl/sharedStrings.xml" or re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n)]
        return "\n".join(t for x in parts for t in re.findall(r"<t(?:\s[^>]*)?>([^<]*)</t>", x))
    return path.read_text(errors="ignore")


def check(rule_id, path, case, stage):
    path = Path(path)
    if not case.get("locale") and case.get("locale_unread"):
        return None, ("the page's language is read from %s, the page this PDF was printed from, and it is not beside "
                      "the PDF: build again and keep it there" % case["locale_unread"])
    raw = case.get("locale") or "eu"
    loc = raw.lower()
    key = raw if raw in LOCALES else ("us" if loc in ("us", "en-us", "en_us") else "eu")
    spec = LOCALES[key]
    country = key not in ("eu", "us")

    if rule_id == "LOCALE-PAPER":
        got = _paper_pt(path)
        if not got:
            return None, "page size not readable from %s" % path.suffix
        want = spec["paper"]["pt"]
        ok = abs(got[0] - want[0]) <= 3 and abs(got[1] - want[1]) <= 3
        return (ok, "%s is %.0fx%.0f pt; %s wants %.0fx%.0f" % (
            path.name, got[0], got[1], spec["paper"]["name"], want[0], want[1]))

    if path.suffix.lower() == ".xml" and rule_id in ("LOCALE-DATE", "LOCALE-NUMBER", "LOCALE-CURRENCY"):
        return None, "machine format: the standard fixes this form, not the locale"
    text = _text(path)

    if rule_id == "LOCALE-DATE" and country:
        pat = spec["date"]["pattern"]
        # yyyy, dd and MM are fixed widths; a single d or M (Finnish d.M.yyyy) is one or two digits.
        widths = {"yyyy": r"\d{4}", "dd": r"\d{2}", "MM": r"\d{2}", "d": r"\d{1,2}", "M": r"\d{1,2}"}
        rx = "".join(widths.get(tok) or re.escape(tok) for tok in re.findall(r"yyyy|dd|MM|d|M|.", pat))
        got = len(re.findall(r"(?<!\d)%s(?!\d)" % rx, text))
        long_rx = long_date_rx(key)
        if long_rx is not None:
            got += len(long_rx.findall(text))        # a letter writes October 9, 2026 or 9. oktober 2026
        if got == 0 and not re.search(r"\d{1,4}[./-]\d{1,2}[./-]\d{1,4}", text):
            return None, "no date on the file, nothing to check"
        return (got > 0, "%d date(s) in the %s form (CLDR %s)" % (got, pat, key))

    if rule_id == "LOCALE-CURRENCY" and country:
        return None, "the order sets the currency; the locale does not"

    if rule_id == "LOCALE-DATE":
        eu = len(SHORT_EU.findall(text)) + len(LONG_EU.findall(text))
        us = len(SHORT_US.findall(text)) + len(LONG_US.findall(text))
        got, other = (eu, us) if key == "eu" else (us, eu)
        want = spec["date"]["pattern"] if key == "eu" else spec["date"]["pattern"] + " or Month D, YYYY"
        if got == 0 and other == 0:
            return None, "no date on the file, nothing to check"
        if got == 0:
            return False, "no date in the %s form; %d in the other" % (want, other)
        return (True, "%d date(s) in the %s form, %d in the other" % (got, want, other))

    if rule_id == "LOCALE-NUMBER":
        dec = spec["number"]["decimal"]
        if path.suffix.lower() == ".xlsx":
            # A workbook's amounts are number cells. A cell that holds a bare figure as text is a code (a
            # customs tariff number 8419.81, an article number), not an amount; an amount written inside a
            # sentence (a note, a term) is read like any other.
            text = "\n".join(x for x in text.split("\n") if not re.fullmatch(r"\s*\d[\d .,]*\s*", x))
        bare = SHORT_EU.sub(" ", text)          # dates and DOIs are not amounts
        bare = SHORT_US.sub(" ", bare)
        bare = LONG_EU.sub(" ", bare)
        bare = LONG_US.sub(" ", bare)
        good = re.findall(r"\d%s\d{2}(?!\d)" % re.escape(dec), bare)
        bad = re.findall(r"\d%s\d{2}(?!\d)" % re.escape("," if dec == "." else "."), bare)
        if not good and not bad:
            return None, "no amount on the file, nothing to check"
        ok = bool(good) and len(bad) <= max(1, len(good) // 4)
        return (ok, "%d amount(s) with %r as the decimal, %d with the other" % (len(good), dec, len(bad)))

    if rule_id == "LOCALE-CURRENCY":
        code = spec["currency"]["code"]
        other = "USD" if code == "EUR" else "EUR"
        hits, others = len(re.findall(code, text)), len(re.findall(other, text))
        if hits == 0 and others == 0:
            return None, "no amount on the file, nothing to check"
        return (hits > 0 and others == 0, "%d %s and %d %s" % (hits, code, others, other))

    return None, "unknown rule"


if __name__ == "__main__":
    loc = sys.argv[3] if len(sys.argv) > 3 else "eu"
    ok, why = check(sys.argv[1], sys.argv[2], {"locale": loc}, "first")
    print({"rule": sys.argv[1], "passed": ok, "evidence": why})
