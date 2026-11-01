#!/usr/bin/env python3
"""The house look of a Word file the docx skill makes from scratch (Mac sweep 2026-10-12).

A Swedish report came back as python-docx's blank document: Cambria body text, the Table Grid's black lines on
every cell, numbers left-aligned and the months in English. Nothing failed, because the Word skill's only rules
were the APA reference rules. These are the floor every new Word file stands on:

  DOCX-FONT     the body text is a sans family: the blank default's Cambria or any other serif fails (a paper with
                a reference list keeps the font its style guide names and is left alone).
  DOCX-TABLE    tables have no grid of black lines: a header row and light horizontal rules, as docx_create.py
                draws them by default.
  DOCX-NUMBERS  a number, an amount or a share in a table cell is right-aligned.
  DOCX-MONTHS   a document written in Swedish names its months in Swedish (juli, not July).

check(rule_id, path, case, stage) -> (passed, evidence). Standard library only.
"""
import re
import zipfile
from pathlib import Path

SERIF = ("cambria", "times", "georgia", "garamond", "book antiqua", "palatino", "constantia", "century",
         "baskerville", "minion", "liberation serif", "dejavu serif")
NUMBER = re.compile(r"^[−\-+]?\s?(?:\d{1,3}(?:[   .,']\d{3})+|\d+)(?:[.,]\d+)?\s?"
                    r"(?:%|kr|sek|eur|€|\$|£|tkr|mkr)?$", re.IGNORECASE)
EN_MONTHS = ("January", "February", "March", "May", "June", "July", "August", "October")
SV_WORDS = ("och", "för", "är", "med", "som", "på", "av", "till", "den", "det", "från", "per")
EN_WORDS = ("the", "and", "of", "with", "for", "is", "from", "to", "this", "that")


def _parts(path):
    with zipfile.ZipFile(path) as z:
        names = z.namelist()

        def read(name):
            return z.read(name).decode("utf-8", "ignore") if name in names else ""
        return read("word/document.xml"), read("word/styles.xml"), read("word/theme/theme1.xml")


def _text(xml):
    return re.sub(r"<[^>]+>", "", re.sub(r"</w:p>", "\n", xml))


def body_font(styles, theme):
    """The font the body text is set in: the Normal style, else the document defaults, else the theme's."""
    normal = re.search(r'<w:style [^>]*w:styleId="Normal".*?</w:style>', styles, re.S)
    for block in ((normal.group(0) if normal else ""), styles.split("</w:docDefaults>")[0]):
        fonts = re.search(r"<w:rFonts ([^>]*?)/?>", block)
        if not fonts:
            continue
        direct = re.search(r'w:ascii="([^"]+)"', fonts.group(1))
        if direct:
            return direct.group(1)
        themed = re.search(r'w:asciiTheme="(minor|major)', fonts.group(1))
        if themed:
            part = re.search(r'<a:%sFont>.*?<a:latin typeface="([^"]*)"' % themed.group(1), theme, re.S)
            return part.group(1) if part else ""
    return ""


def their_fonts(path, case=None):
    """The body fonts of the person's own Word files in the folder (their template, a letter of theirs): a file
    filled from one keeps its look. The fill-template run changed their template's font to Arial to pass DOCX-FONT
    (timed run c21, 2026-10-25)."""
    folder = Path((case or {}).get("folder") or path.parent)
    fonts = set()
    for other in folder.glob("*.docx"):
        if other.name.startswith("~$") or other.resolve() == path.resolve():
            continue
        try:
            _, styles, theme = _parts(other)
        except (OSError, zipfile.BadZipFile, KeyError):
            continue
        fonts.add(body_font(styles, theme))
    return fonts - {""}


def tables(document):
    return re.findall(r"<w:tbl>.*?</w:tbl>", document, re.S)


def academic(text):
    return bool(re.search(r"(?mi)^\s*(references|reference list|referenser|literaturverzeichnis)\s*$", text))


def check(rule_id, path, case=None, stage=None):
    path = Path(path)
    if path.suffix.lower() != ".docx":
        return None, "not a Word file"
    try:
        document, styles, theme = _parts(path)
    except (OSError, zipfile.BadZipFile, KeyError):
        return None, "could not read the Word file"
    text = _text(document)
    if rule_id == "DOCX-FONT":
        if academic(text):
            return None, "a paper with references keeps the font its style guide names"
        font = body_font(styles, theme)
        if font and font in their_fonts(path, case):
            return None, "the person's own Word file in the folder is set in %s, and the file keeps their look" % font
        if font and any(s in font.lower() for s in SERIF):
            return False, ("the body text is set in %s, a serif: the blank python-docx default. Build the file with "
                           "<skills>/docx/scripts/docx_create.py (it starts from templates/standard.docx, Arial), or "
                           "open that template in python-docx instead of Document()." % font)
        return True, "body text in %s" % (font or "the template's font")
    found = tables(document)
    if rule_id == "DOCX-TABLE":
        if not found:
            return None, "no tables"
        bad = [str(i + 1) for i, t in enumerate(found)
               if 'w:tblStyle w:val="TableGrid"' in t or re.search(r'<w:insideV w:val="(single|thick|double)"', t)]
        if bad:
            return False, ("table %s draws a black grid on every cell (Table Grid). Use docx_create.py's table block "
                           "without a style: a header row, a rule under it and light rules between rows, or call "
                           "docx_create.house_table(table) on a python-docx table." % ", ".join(bad))
        return True, "%d tables, no grid" % len(found)
    if rule_id == "DOCX-NUMBERS":
        if not found:
            return None, "no tables"
        left = []
        for t in found:
            for cell in re.findall(r"<w:tc>.*?</w:tc>", t, re.S):
                value = _text(cell).strip()
                if value and NUMBER.match(value) and not re.search(r'<w:jc w:val="(right|end|decimal)"', cell):
                    left.append(value)
        if left:
            return False, ("%d numbers in tables are not right-aligned (%s). Right-align every number, amount and "
                           "share, and its column's heading." % (len(left), ", ".join(left[:3])))
        return True, "numbers right-aligned"
    if rule_id == "DOCX-MONTHS":
        words = re.findall(r"[a-zåäö]+", text.lower())
        sv = sum(words.count(w) for w in SV_WORDS)
        en = sum(words.count(w) for w in EN_WORDS)
        if sv < 5 or sv <= en:
            return None, "not written in Swedish"
        english = sorted(m for m in EN_MONTHS if re.search(r"\b%s\b" % m, text))
        if english:
            return False, ("the document is in Swedish but names months in English: %s. Write januari, februari, "
                           "mars, maj, juni, juli, augusti, oktober, also where the source data says July."
                           % ", ".join(english))
        return True, "months in Swedish"
    return None, "not a rule of this module"
