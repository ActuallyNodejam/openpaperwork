#!/usr/bin/env python3
"""A drafting check for the annual report (årsredovisning) of a smaller Swedish limited company, as a Word
file in Swedish or English. It reads which parts and items are there and whether the numbers add up. It
never says whether the accounts are right, lawful or ready to file; that is for the board, the
accountant and, where there is one, the auditor. Its sources, restated in our own words:

  Årsredovisningslagen (1995:1554), 2 kap. 1 and 7 §§, 3 kap. 3-5 §§ with bilaga 1 and 2, 5 kap. 4, 8 and
  20 §§, 6 kap. 1 and 2 §§ (Swedish statute, outside copyright under upphovsrättslagen 9 §);
  Directive 2013/34/EU Art. 4(1), 9(5), 10, 13, 14 and 16(1) with Annexes III to V (EUR-Lex CELEX
  32013L0034, reused under Commission Decision 2011/833/EU);
  Bokföringsnämnden's general advice BFNAR 2016:10 (K2), chapters 3, 4, 5 and 18, cited only.

  ANNUAL-PARTS        The management report, income statement, balance sheet, notes and signatures, in
                      that order; the company's name and organisation number; the management report's
                      business, significant events, multi-year overview, changes in equity and the
                      proposed disposition of the result.
  ANNUAL-PAGES        Each part starts on a page of its own, as Swedish annual reports are set out.
  ANNUAL-AMOUNTS      The unit is stated (kronor or thousands), one unit throughout, whole numbers.
  ANNUAL-YEARS        The financial year is stated and both statements carry last year's figures
                      beside this year's, for every line.
  ANNUAL-SUMS         Every subtotal and result line is the sum of the lines it covers, both years.
  ANNUAL-BALANCE      Total assets equal total equity and liabilities, both years.
  ANNUAL-RESULT       The year's result is the same in the income statement, the balance sheet, the
                      changes in equity, the disposition and the multi-year overview.
  ANNUAL-EQUITY       The changes in equity run from last year's balance sheet to this year's.
  ANNUAL-DISPOSITION  The funds at the meeting's disposal are the unrestricted equity, and the proposal
                      disposes of exactly that sum.
  ANNUAL-NOTES        The accounting policies and average number of employees are there, notes are
                      numbered in order, every note a statement points to exists, every fixed asset
                      points to a note, and a note's carrying amount is the balance sheet's.
  ANNUAL-SIGNED       A signatures part with a date after the year end and the signatories' names.

With an annual-report spec beside the file (skills/annual-accounts) it also compares the company, the
year and the board's names with the spec. check(rule_id, path, case, stage) -> (passed, evidence);
passed is None when the rule does not apply.
"""
import datetime as dt
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from decimal import Decimal
from pathlib import Path

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

SECTIONS = [
    ("report", ("förvaltningsberättelse", "management report", "directors' report", "directors report",
                "administration report")),
    ("income", ("resultaträkning", "income statement", "profit and loss account", "profit and loss statement",
                "statement of profit or loss")),
    ("balance", ("balansräkning", "balance sheet", "statement of financial position")),
    ("notes", ("noter", "notes", "tilläggsupplysningar", "notes to the financial statements",
               "notes to the accounts")),
    ("sign", ("underskrifter", "signatures", "styrelsens underskrifter", "signing of the annual report",
              "underskrift", "signature")),
]
REF = {"report": "ÅRL 2 kap. 1 §, 6 kap. 1 §", "income": "ÅRL 2 kap. 1 §, 3 kap. 3 § bilaga 2",
       "balance": "ÅRL 2 kap. 1 §, 3 kap. 3 § bilaga 1", "notes": "ÅRL 2 kap. 1 §, 5 kap.",
       "sign": "ÅRL 2 kap. 7 §"}
NAMES = {"report": "the management report", "income": "the income statement", "balance": "the balance sheet",
         "notes": "the notes", "sign": "the signatures"}
SUBS = [
    ("business", ("verksamheten", "allmänt om verksamheten", "verksamhetens art och inriktning",
                  "information om verksamheten", "the business", "business", "operations",
                  "general information about the business", "nature of the business")),
    ("events", ("väsentliga händelser under räkenskapsåret", "väsentliga händelser under året",
                "väsentliga händelser", "significant events during the financial year",
                "significant events during the year", "significant events")),
    ("overview", ("flerårsöversikt", "multi-year overview", "multi-year summary", "five-year summary",
                  "five-year overview", "key figures")),
    ("changes", ("förändringar i eget kapital", "förändring av eget kapital", "förändring i eget kapital",
                 "changes in equity", "statement of changes in equity")),
    ("disposition", ("förslag till resultatdisposition", "förslag till vinstdisposition", "resultatdisposition",
                     "vinstdisposition", "förslag till disposition", "disposition av resultat",
                     "proposed appropriation of profit", "proposed appropriation of the result",
                     "proposed appropriation", "appropriation of profit", "appropriation of the result",
                     "proposed treatment of loss", "proposed disposition")),
]
SUB_NAMES = {"business": ("the business", "ÅRL 6 kap. 1 §"),
             "events": ("significant events during the year", "ÅRL 6 kap. 1 §"),
             "overview": ("the multi-year overview", "BFNAR 2016:10 kap. 5"),
             "changes": ("the changes in equity", "ÅRL 6 kap. 2 §"),
             "disposition": ("the proposed disposition of the result", "ÅRL 6 kap. 2 §")}
SUM_PREFIX = ("summa ", "total ", "totalt ", "sum ")
RESULTS = ("rörelseresultat", "resultat efter finansiella poster", "resultat före skatt", "årets resultat",
           "årets vinst", "årets förlust", "bruttoresultat", "bruttovinst", "operating profit", "operating loss",
           "operating result", "profit after financial items", "loss after financial items",
           "profit or loss after financial items", "result after financial items", "profit before tax",
           "loss before tax", "profit or loss before tax", "result before tax", "profit for the year",
           "loss for the year", "profit or loss for the year", "result for the year", "net profit",
           "net loss", "gross profit", "gross profit or loss")
YEAR_RESULT = ("årets resultat", "årets vinst", "årets förlust", "profit for the year", "loss for the year",
               "profit or loss for the year", "result for the year", "net profit for the year",
               "net loss for the year")
AFTER_FIN = ("resultat efter finansiella poster", "profit after financial items", "loss after financial items",
             "profit or loss after financial items", "result after financial items")
NET_SALES = ("nettoomsättning", "net sales", "net turnover", "revenue")
COSTISH = ("kostnad", "expense", "costs", "avskrivning", "depreciation", "råvaror", "handelsvaror",
           "raw materials", "goods for resale", "skatt på", "tax on")
TOTAL_ASSETS = ("summa tillgångar", "total assets")
TOTAL_EL = ("summa eget kapital och skulder", "summa eget kapital, avsättningar och skulder",
            "summa skulder och eget kapital", "total equity and liabilities", "total equity, provisions and "
            "liabilities", "total liabilities and equity")
FREE_SUM = ("summa fritt eget kapital", "total unrestricted equity", "total non-restricted equity")
FREE_HEAD = ("fritt eget kapital", "unrestricted equity", "non-restricted equity")
FREE_LINES = ("överkursfond", "balanserat resultat", "balanserad vinst", "balanserad förlust",
              "share premium", "retained earnings", "retained profit") + YEAR_RESULT
OPENING = ("belopp vid årets ingång", "ingående balans", "ingående", "opening balance", "balance at the beginning",
           "at the beginning", "opening")
CLOSING = ("belopp vid årets utgång", "utgående balans", "utgående", "closing balance", "balance at the end",
           "at the end", "closing")
CARRYING = ("utgående redovisat värde", "redovisat värde", "utgående bokfört värde", "bokfört värde",
            "closing carrying amount", "carrying amount", "closing book value", "book value")
PRINCIPLES = ("redovisningsprinciper", "värderingsprinciper", "redovisnings- och värderingsprinciper",
              "accounting policies", "accounting principles", "valuation principles")
EMPLOYEES = ("medelantal anställda", "medelantalet anställda", "anställda", "average number of employees",
             "employees")
DIVIDEND = ("utdelning", "dividend")
MONTHS = {"januari": 1, "january": 1, "februari": 2, "february": 2, "mars": 3, "march": 3, "april": 4,
          "maj": 5, "may": 5, "juni": 6, "june": 6, "juli": 7, "july": 7, "augusti": 8, "august": 8,
          "september": 9, "oktober": 10, "october": 10, "november": 11, "december": 12}
DATES = [
    (re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b"), "ymd"),
    (re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b"), "dmy"),
    (re.compile(r"\b(\d{1,2})(?:st|nd|rd|th|:e|:a)?\s+(%s)\s+(\d{4})\b" % "|".join(MONTHS), re.I), "dMy"),
    (re.compile(r"\b(%s)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b" % "|".join(MONTHS), re.I), "Mdy"),
]
YEARISH = re.compile(r"^(?:\d{4}(?:-\d{2}-\d{2})?(?:\s*[-–—]+\s*\d{4}(?:-\d{2}-\d{2})?)?|\d{4}/\d{2,4}|"
                     r"(?:\d{1,2}\s+\w+\s+)?\d{4}(?:\s*[-–—]\s*(?:\d{1,2}\s+\w+\s+)?\d{4})?)$")
NOTE_HEAD = re.compile(r"^(?:not|note)\s+(\d{1,3})\b[\s.:\-–—]*(.*)$", re.I)
UNIT_KR = re.compile(r"\b(?:belopp\w*|amounts?)\b[^.]{0,40}?\b(?:i|in)\s+(?:hela\s+|whole\s+)?(?:svenska\s+|swedish\s+)?"
                     r"(kr|kronor|sek)\b|\((kr|sek)\)", re.I)
UNIT_K = re.compile(r"\b(?:belopp\w*|amounts?)\b[^.]{0,40}?\b(?:i|in)\s+(tkr|ksek|tsek|tusentals kronor|thousands of "
                    r"(?:swedish )?kronor|thousands of sek)\b|\((tkr|ksek|tsek)\)", re.I)


def norm(s):
    s = str(s).replace(" ", " ").replace(" ", " ").replace(" ", " ")
    return re.sub(r"\s+", " ", s).strip().lower().rstrip(":.").strip()


# ---- reading the Word file -------------------------------------------------------------------------------
def _ptext(p):
    out = []
    for el in p.iter():
        if el.tag == W + "t" and el.text:
            out.append(el.text)
        elif el.tag in (W + "tab", W + "br", W + "cr"):
            out.append(" ")
    return re.sub(r"\s+", " ", "".join(out)).strip()


def _style(p):
    ps = p.find(W + "pPr/" + W + "pStyle")
    return ps.get(W + "val") if ps is not None else ""


def _breaks_styles(z):
    """Paragraph styles that start a new page themselves."""
    try:
        root = ET.fromstring(z.read("word/styles.xml"))
    except KeyError:
        return set()
    out = set()
    for st in root.findall(W + "style"):
        pb = st.find(W + "pPr/" + W + "pageBreakBefore")
        if pb is not None and pb.get(W + "val", "true") not in ("0", "false"):
            out.add(st.get(W + "styleId"))
    return out


def blocks(path):
    """('p', style, text, starts a new page) and ('t', rows of cell texts) in reading order."""
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
        paged = _breaks_styles(z)
    out = []
    pending = [False]

    def page_break(el):
        return el.tag == W + "br" and el.get(W + "type") == "page"

    def walk(parent):
        for el in parent:
            if el.tag == W + "p":
                text = _ptext(el)
                pb = el.find(W + "pPr/" + W + "pageBreakBefore")
                before = pending[0] or _style(el) in paged or (
                    pb is not None and pb.get(W + "val", "true") not in ("0", "false"))
                after, seen = el.find(W + "pPr/" + W + "sectPr") is not None, False
                for x in el.iter():
                    if x.tag == W + "t" and x.text and x.text.strip():
                        seen = True
                    elif page_break(x):
                        if seen:
                            after = True
                        else:
                            before = True
                if text:
                    out.append(("p", _style(el), text, before))
                    pending[0] = after
                else:
                    pending[0] = before or after
            elif el.tag == W + "tbl":
                rows = []
                for tr in el.findall(W + "tr"):
                    rows.append([" ".join(_ptext(p) for p in tc.iter(W + "p")).strip() for tc in tr.findall(W + "tc")])
                out.append(("t", rows))
                pending[0] = False
            elif el.tag in (W + "sdt", W + "sdtContent", W + "body"):
                walk(el)
    walk(root.find(W + "body"))
    return out


def headingish(style, text):
    return bool(re.match(r"(heading|rubrik|title|overskrift)", style or "", re.I)) or (
        len(text) <= 90 and not text.rstrip().endswith((".", ";", ",")))


def match_label(text, labels):
    t = re.sub(r"^(?:\d{1,2}(?:\.\d{1,2})*\.?|[ivx]+\.)\s+", "", norm(text))
    for lab in sorted(labels, key=len, reverse=True):
        if t == lab or (t.startswith(lab) and re.match(r"^\s*(\(|:|–|-|,|för |for |\d{4})", t[len(lab):])
                        and len(t) - len(lab) <= 30):
            return True
    return False


class Doc:
    def __init__(self, path):
        self.blocks = blocks(path)
        self.flat = " ".join(b[2] if b[0] == "p" else " ".join(" ".join(r) for r in b[1]) for b in self.blocks)
        self.section, self.sub, self.start = [], [], {}
        sec, sub = None, None
        subs_seen = {}
        for i, b in enumerate(self.blocks):
            if b[0] == "p" and headingish(b[1], b[2]):
                for key, labels in SECTIONS:
                    if key not in self.start and match_label(b[2], labels):
                        sec, sub = key, None
                        self.start[key] = i
                        break
                else:
                    for key, labels in SUBS:
                        if match_label(b[2], labels):
                            sub = key
                            subs_seen.setdefault(key, i)
                            break
            self.section.append(sec)
            self.sub.append(sub)
        self.subs = subs_seen

    def tables(self, section=None, sub=None):
        return [b[1] for i, b in enumerate(self.blocks) if b[0] == "t"
                and (section is None or self.section[i] == section) and (sub is None or self.sub[i] == sub)]

    def paras(self, section=None, sub=None):
        return [b[2] for i, b in enumerate(self.blocks) if b[0] == "p"
                and (section is None or self.section[i] == section) and (sub is None or self.sub[i] == sub)]


# ---- numbers -----------------------------------------------------------------------------------------------
def amount(s):
    """(value, has_fraction) of a printed amount, (Decimal 0, False) for a dash, None for anything else."""
    t = re.sub(r"[\s   ']", "", str(s)).replace("−", "-").replace("–", "-").replace("—", "-")
    t = re.sub(r"(?i)(kr|sek|tkr|ksek|%)$", "", t)
    if t in ("-", "--"):
        return Decimal(0), False
    m = re.fullmatch(r"(\()?(-)?(\d[\d.,]*)(\))?", t)
    if not m or (m.group(1) and not m.group(4)) or (m.group(4) and not m.group(1)):
        return None
    neg = bool(m.group(1)) or bool(m.group(2))
    d = m.group(3)
    frac = False
    if "," in d and "." in d:
        dec = "," if d.rfind(",") > d.rfind(".") else "."
        d = d.replace("." if dec == "," else ",", "").replace(dec, ".")
        frac = True
    elif "," in d or "." in d:
        sep = "," if "," in d else "."
        parts = d.split(sep)
        if all(len(p) == 3 for p in parts[1:]) and len(parts[0]) <= 3:
            d = "".join(parts)
        elif len(parts) == 2:
            d = parts[0] + "." + parts[1]
            frac = True
        else:
            return None
    v = Decimal(d)
    return (-v if neg else v), frac and v != v.to_integral_value()


def fmt(v):
    if v is None:
        return "none"
    s = "{:,}".format(int(v)) if v == v.to_integral_value() else "{:,}".format(v)
    return s.replace(",", " ")


class Row:
    def __init__(self, label, cur, prev, notes, raw):
        self.label, self.norm = label, norm(label)
        self.cur, self.prev, self.notes, self.raw = cur, prev, notes, raw
        self.kind = "line"

    def get(self, i):
        return self.cur if i == 0 else self.prev


def header_columns(row):
    """(note column, [year columns in order this year, last year], [year labels]) of a header row, or None."""
    cells = [norm(c) for c in row]
    if len(cells) < 2:
        return None
    note, years, labels = None, [], []
    for i, c in enumerate(cells[1:], 1):
        if not c:
            continue
        if c in ("not", "note", "noter", "notes", "not nr", "note no"):
            note = i
        elif YEARISH.match(c) or re.search(r"\b(19|20)\d{2}\b", c) and amount(c) is None:
            years.append(i)
            labels.append(row[i])
        elif amount(c) is not None or len(c) > 40:
            return None
    if not years:
        return None
    ends = [max([int(y) for y in re.findall(r"\b((?:19|20)\d{2})\b", norm(l))] or [0]) for l in labels]
    if len(years) >= 2 and ends[0] < ends[1]:
        years[0], years[1] = years[1], years[0]
        labels[0], labels[1] = labels[1], labels[0]
    return note, years, labels


def statement(tables, income):
    """Rows of a statement, with its year labels: (rows, labels, columns found)."""
    rows, labels, ncols = [], [], 0
    for t in tables:
        cols = None
        for n, cells in enumerate(t):
            if not cells or not any(c.strip() for c in cells):
                continue
            if n <= 1 and cols is None:
                h = header_columns(cells)
                if h:
                    cols = h
                    if not labels:
                        labels, ncols = h[2], len(h[1])
                    continue
            label = cells[0].strip()
            if cols:
                note_i, year_i, _ = cols
                vals = [amount(cells[i]) if i < len(cells) else None for i in year_i[:2]]
                note_txt = cells[note_i] if note_i is not None and note_i < len(cells) else ""
            else:
                found = [(i, amount(c)) for i, c in enumerate(cells[1:], 1) if c.strip()]
                nums = [(i, a) for i, a in found if a is not None]
                note_txt = ""
                if len(nums) >= 3 and nums[0][1][0] < 100 and len(cells) >= 4:
                    note_txt = cells[nums[0][0]]
                    nums = nums[1:]
                vals = [a for _, a in nums[-2:]]
                ncols = max(ncols, len(vals))
            vals = (vals + [None, None])[:2]
            notes = [int(x) for x in re.findall(r"\d+", note_txt)]
            r = Row(label, vals[0][0] if vals[0] else None, vals[1][0] if vals[1] else None, notes,
                    [v for v in vals if v])
            if not r.norm:
                continue
            if r.norm in ("summa", "total", "totalt") or r.norm.startswith(SUM_PREFIX):
                r.kind = "sum"
            elif income and r.norm.startswith(RESULTS) and (r.cur is not None or r.prev is not None):
                r.kind = "result"
            elif r.cur is None and r.prev is None:
                r.kind = "head"
            rows.append(r)
    return rows, labels, ncols


def lines(rows, a, b):
    return [r for r in rows[a:b] if r.kind == "line"]


def total(span, i):
    return sum((r.get(i) or 0) for r in span)


def sum_problems(rows, income, years):
    bad, checked = [], 0
    for i, row in enumerate(rows):
        if row.kind not in ("sum", "result"):
            continue
        if row.kind == "result":
            spans = [lines(rows, 0, i)]
        else:
            name = row.norm
            for p in SUM_PREFIX:
                if name.startswith(p):
                    name = name[len(p):].strip()
            head = next((j for j in range(i - 1, -1, -1) if rows[j].kind == "head" and rows[j].norm == name), None)
            last = next((j for j in range(i - 1, -1, -1) if rows[j].kind != "line"), -1)
            spans = [lines(rows, head + 1, i)] if head is not None else [lines(rows, last + 1, i), lines(rows, 0, i)]
        for y in range(years):
            got = row.get(y)
            if got is None:
                continue
            checked += 1
            wants = [total(s, y) for s in spans]
            if row.kind == "result":
                wants.append(sum((-abs(r.get(y) or 0) if any(w in r.norm for w in COSTISH) else (r.get(y) or 0))
                                 for r in spans[0]))
            if got not in wants:
                bad.append("%s %s is %s, the lines above it make %s" % (row.label, ("this year", "last year")[y],
                                                                      fmt(got), fmt(wants[0])))
    return bad, checked


def find(rows, labels, kind=None):
    for r in rows:
        if r.norm.startswith(labels) and (kind is None or r.kind == kind):
            return r
    return None


def dates_in(text):
    found = []
    for rx, kind in DATES:
        for m in rx.finditer(text):
            a, b, c = m.groups()
            try:
                d = (dt.date(int(a), int(b), int(c)) if kind == "ymd" else dt.date(int(c), int(b), int(a))
                     if kind == "dmy" else dt.date(int(c), MONTHS[b.lower()], int(a)) if kind == "dMy"
                     else dt.date(int(c), MONTHS[a.lower()], int(b)))
            except (ValueError, KeyError):
                continue
            found.append((m.start(), d))
    return [d for _, d in sorted(found)]


def spec_beside(path):
    for p in sorted(Path(path).parent.glob("*.json")):
        try:
            data = json.loads(p.read_text())
        except (ValueError, OSError):
            continue
        if isinstance(data, dict) and isinstance(data.get("company"), dict) and "balance" in data:
            return data
    return None


def notes_of(doc):
    """number -> (title, [tables]) from the note headings, in the notes part when there is one."""
    out, order, cur = {}, [], None
    for i, b in enumerate(doc.blocks):
        if "notes" in doc.start and doc.section[i] != "notes":
            continue
        if b[0] == "p" and headingish(b[1], b[2]):
            m = NOTE_HEAD.match(norm(b[2]))
            if m:
                cur = int(m.group(1))
                order.append(cur)
                out.setdefault(cur, [m.group(2).strip(), [], []])
                continue
        if cur is not None:
            if b[0] == "t":
                out[cur][1].append(b[1])
            else:
                out[cur][2].append(b[2])
    return out, order


def disposition_rows(doc):
    rows = []
    for i, b in enumerate(doc.blocks):
        if doc.sub[i] != "disposition" or doc.section[i] not in ("report", None):
            continue
        if b[0] == "t":
            for cells in b[1]:
                nums = [amount(c) for c in cells[1:] if c.strip()]
                nums = [a for a in nums if a is not None]
                if cells and cells[0].strip() and nums:
                    rows.append(Row(cells[0], nums[-1][0], None, [], [nums[-1]]))
        else:
            m = re.match(r"^(.*?[^\d\s-])\s*:?\s+(\(?[-−–]?\s?\d[\d\s  .,]*\)?)\s*(kr|sek|tkr)?\.?$", b[2], re.I)
            if m and len(m.group(1)) <= 80 and amount(m.group(2)) is not None:
                a = amount(m.group(2))
                rows.append(Row(m.group(1), a[0], None, [], [a]))
    for r in rows:
        if r.norm in ("summa", "total", "totalt") or r.norm.startswith(SUM_PREFIX):
            r.kind = "sum"
    return rows


def changes_table(doc):
    for i, b in enumerate(doc.blocks):
        if b[0] == "t" and doc.sub[i] == "changes" and len(b[1]) >= 3:
            return b[1]
    return None


def first_year(doc, spec):
    return bool(spec and spec.get("first_year")) or bool(re.search(
        r"första räkenskapsår|first financial year|bolagets första", doc.flat.lower()))


# ---- the rules ------------------------------------------------------------------------------------------------
def check(rule_id, path, case, stage):
    path = Path(path)
    if path.suffix.lower() != ".docx":
        return None, "an annual report is checked as a Word file"
    doc = Doc(path)
    truth = (case or {}).get("truth") or {}
    spec = spec_beside(path) or (truth if isinstance(truth.get("company"), dict) else None)
    inc, inc_years, inc_cols = statement(doc.tables("income"), True)
    bal, bal_years, bal_cols = statement(doc.tables("balance"), False)
    years = 1 if first_year(doc, spec) else 2
    flat = doc.flat.lower()
    # What the data file declares the company has not given yet (annual_create.py UNKNOWN): left empty, a question.
    unknown = set((spec or {}).get("unknown") or [])

    if rule_id == "ANNUAL-PARTS":
        bad = []
        missing = [k for k, _ in SECTIONS if k not in doc.start]
        if missing:
            bad.append("missing: %s" % "; ".join("%s [%s]" % (NAMES[k], REF[k]) for k in missing))
        order = [k for k, _ in SECTIONS if k in doc.start]
        if order != sorted(order, key=lambda k: doc.start[k]):
            bad.append("the parts run %s; K2 sets them out as management report, income statement, balance "
                       "sheet, notes, then signatures [BFNAR 2016:10 kap. 3]"
                       % ", ".join(NAMES[k] for k in sorted(order, key=lambda k: doc.start[k])))
        if not re.search(r"\b\d{6}-\d{4}\b", doc.flat):
            bad.append("no organisation number (NNNNNN-NNNN) names the company")
        if spec:
            co = spec["company"]
            if co.get("name") and norm(co["name"]) not in norm(doc.flat):
                bad.append("the company name %s from the spec is not in the report" % co["name"])
            if co.get("org_number") and co["org_number"] not in doc.flat:
                bad.append("the organisation number %s from the spec is not in the report" % co["org_number"])
        if "report" in doc.start:
            gone = [k for k, _ in SUBS if k not in doc.subs]
            if gone:
                bad.append("the management report has no %s" % "; no ".join(
                    "%s [%s]" % SUB_NAMES[k] for k in gone))
        if inc and not find(inc, YEAR_RESULT):
            bad.append("the income statement has no line for the year's result [ÅRL bilaga 2]")
        if bal and not (find(bal, TOTAL_ASSETS) and find(bal, TOTAL_EL)):
            bad.append("the balance sheet has no total of assets or of equity and liabilities [ÅRL bilaga 1]")
        if bad:
            return False, "; ".join(bad)
        return True, "the management report (business, events, overview, changes in equity, disposition), " \
                     "income statement, balance sheet, notes and signatures are there, in order"

    if rule_id == "ANNUAL-PAGES":
        if not doc.start:
            return None, "no parts to place (ANNUAL-PARTS names them)"
        bad = []
        for key, _ in SECTIONS:
            if key not in doc.start:
                continue
            i = doc.start[key]
            if doc.blocks[i][3]:
                continue
            if key == "report" and not any(b[0] == "p" and b[3] for b in doc.blocks[:i]):
                continue                                    # the management report may open page 1
            bad.append(NAMES[key])
        if bad:
            return False, "%s %s not start on a page of its own; a Swedish annual report opens each part on a " \
                          "new page (page break before the heading)" % (", ".join(bad), "does" if len(bad) == 1 else "do")
        return True, "each part starts on a page of its own"

    if rule_id == "ANNUAL-AMOUNTS":
        bad = []
        kr = UNIT_KR.search(doc.flat)
        k = UNIT_K.search(doc.flat)
        if not kr and not k:
            bad.append("the report never says what unit its amounts are in (kronor or thousands of kronor) "
                       "[BFNAR 2016:10 kap. 3]")
        elif kr and k:
            bad.append("the report states amounts both in kronor (%r) and in thousands (%r); keep one unit"
                       % (kr.group(0), k.group(0)))
        fractions = [r.label for r in inc + bal if any(f for _, f in r.raw)]
        if fractions:
            bad.append("amounts carry decimals where the statements round to whole kronor or thousands: %s"
                       % ", ".join(fractions[:6]))
        if bad:
            return False, "; ".join(bad)
        return True, "amounts are in %s throughout, as whole numbers" % ("thousands of kronor" if k else "kronor")

    if rule_id == "ANNUAL-YEARS":
        bad = []
        ds = set(dates_in(doc.flat))
        if spec and spec.get("year"):
            for key in ("start", "end"):
                try:
                    d = dt.date.fromisoformat(spec["year"][key])
                except (KeyError, ValueError):
                    continue
                if d not in ds:
                    bad.append("the financial year's %s %s is not stated" % (key, d))
        elif len(ds) < 2:
            bad.append("the financial year is not stated with its first and last day")
        if years == 1:
            if bad:
                return False, "; ".join(bad)
            return None, "the company's first financial year: there is no earlier year to compare"
        gaps, short = [], []
        for name, rows, labels, cols in (("income statement", inc, inc_years, inc_cols),
                                         ("balance sheet", bal, bal_years, bal_cols)):
            if not rows:
                continue
            if cols < 2:
                gaps.append("the %s has no column for last year [ÅRL 3 kap. 5 §; Directive 2013/34/EU Art. 9(5)]" % name)
                short.append(name)
                continue
            gap = [r.label for r in rows if r.kind in ("line", "sum", "result") and r.cur is not None and r.prev is None]
            if gap:
                gaps.append("the %s gives no figure for last year on %s [ÅRL 3 kap. 5 §]" % (name, ", ".join(gap[:6])))
                short.append(name)
        if gaps and not bad and "prior" in unknown:
            return True, ("WARN the data file declares last year's figures unknown, so the %s leave last year's "
                          "column empty [ÅRL 3 kap. 5 §]. The report is a draft until they are in: say so in your "
                          "reply and ask for last year's annual report" % " and the ".join(short))
        bad += gaps
        if bad:
            return False, "; ".join(bad)
        return True, "the financial year is stated, and both statements give last year's figure beside this year's"

    if rule_id == "ANNUAL-SUMS":
        if not inc and not bal:
            return False, "no income statement or balance sheet tables to add up"
        bad, checked = [], 0
        for name, rows in (("income statement", inc), ("balance sheet", bal)):
            b, c = sum_problems(rows, name == "income statement", years)
            bad += ["%s: %s" % (name, x) for x in b]
            checked += c
        if bad:
            return False, "; ".join(bad[:8])
        return True, "%d subtotals and result lines add up" % checked

    if rule_id == "ANNUAL-BALANCE":
        a, el = find(bal, TOTAL_ASSETS), find(bal, TOTAL_EL)
        if not (a and el):
            return False, "the balance sheet needs a line for total assets and one for total equity and liabilities"
        bad, shown = [], []
        for y in range(years):
            x, z = a.get(y), el.get(y)
            if x is None or z is None:
                continue
            shown.append(fmt(x))
            if x != z:
                bad.append("%s total assets are %s but equity and liabilities are %s, a gap of %s"
                           % (("this year", "last year")[y], fmt(x), fmt(z), fmt(x - z)))
        if bad:
            return False, "; ".join(bad)
        return True, "total assets equal total equity and liabilities: %s" % " and ".join(shown)

    if rule_id == "ANNUAL-RESULT":
        rr = find(inc, YEAR_RESULT, "result") or find(inc, YEAR_RESULT)
        if not rr:
            return False, "the income statement has no line for the year's result"
        bad, seen = [], ["the income statement"]
        br = find([r for r in bal if r.kind == "line"], YEAR_RESULT)
        if br is None:
            bad.append("the balance sheet's equity has no line for the year's result [ÅRL bilaga 1, A VI]")
        else:
            seen.append("the balance sheet")
            for y in range(years):
                if br.get(y) is not None and rr.get(y) is not None and br.get(y) != rr.get(y):
                    bad.append("the year's result %s is %s in the income statement but %s in the balance sheet"
                               % (("this year", "last year")[y], fmt(rr.get(y)), fmt(br.get(y))))
        t = changes_table(doc)
        if t:
            head = [norm(c) for c in t[0]]
            col = next((i for i, c in enumerate(head) if c.startswith(YEAR_RESULT)), None)
            close = next((r for r in t[1:] if norm(r[0]).startswith(CLOSING)), None)
            if col is not None and close and col < len(close) and amount(close[col]):
                seen.append("the changes in equity")
                v = amount(close[col])[0]
                if v != rr.cur:
                    bad.append("the changes in equity close the year's result at %s, the income statement has %s"
                               % (fmt(v), fmt(rr.cur)))
        disp = disposition_rows(doc)
        funds = []
        for r in disp:
            if r.kind == "sum":
                break
            funds.append(r)
        d = find(funds, YEAR_RESULT)
        if d:
            seen.append("the disposition")
            if d.cur != rr.cur:
                bad.append("the disposition gives the year's result as %s, the income statement %s"
                           % (fmt(d.cur), fmt(rr.cur)))
        for t in doc.tables(sub="overview"):
            h = header_columns(t[0]) if t else None
            if not h:
                continue
            ci = h[1][0]
            for cells in t[1:]:
                lab = norm(cells[0]) if cells else ""
                v = amount(cells[ci]) if ci < len(cells) else None
                if v is None:
                    continue
                if lab.startswith(NET_SALES):
                    ns = find(inc, NET_SALES)
                    if ns and ns.cur != v[0]:
                        bad.append("the multi-year overview gives net sales of %s, the income statement %s"
                                   % (fmt(v[0]), fmt(ns.cur)))
                    if "the multi-year overview" not in seen:
                        seen.append("the multi-year overview")
                elif lab.startswith(AFTER_FIN):
                    af = find(inc, AFTER_FIN)
                    if af and af.cur != v[0]:
                        bad.append("the multi-year overview gives the result after financial items as %s, the "
                                   "income statement %s" % (fmt(v[0]), fmt(af.cur)))
            break
        if bad:
            return False, "; ".join(bad)
        return True, "the year's result, %s, is the same in %s" % (fmt(rr.cur), ", ".join(seen))

    if rule_id == "ANNUAL-EQUITY":
        t = changes_table(doc)
        if not t:
            return None, "no table of changes in equity to read (ANNUAL-PARTS asks for one)"
        head = [c.strip() for c in t[0]]
        body = [r for r in t[1:] if r and r[0].strip()]
        open_i = next((i for i, r in enumerate(body) if norm(r[0]).startswith(OPENING)), None)
        close_i = next((i for i, r in enumerate(body) if norm(r[0]).startswith(CLOSING)), None)
        if close_i is None:
            return False, "the changes in equity have no closing row (belopp vid årets utgång)"
        start = open_i if open_i is not None else -1
        bad = []
        tot_col = next((i for i, c in enumerate(head) if norm(c) in ("totalt", "summa", "total", "summa eget kapital",
                                                                     "total equity")), None)
        for c in range(1, len(head)):
            val = lambda r: (amount(r[c]) or (Decimal(0), False))[0] if c < len(r) and r[c].strip() else Decimal(0)  # noqa: E731
            run = sum(val(r) for r in body[start if start >= 0 else 0:close_i]) if start >= 0 else \
                sum(val(r) for r in body[:close_i])
            if run != val(body[close_i]):
                bad.append("the %s column runs to %s but closes at %s" % (head[c] or "#%d" % c, fmt(run),
                                                                          fmt(val(body[close_i]))))
            match = next((r for r in bal if r.kind == "line" and r.norm == norm(head[c])), None)
            if match is not None and c != tot_col:
                if match.cur is not None and match.cur != val(body[close_i]):
                    bad.append("%s closes at %s in the changes in equity but is %s in the balance sheet"
                               % (head[c], fmt(val(body[close_i])), fmt(match.cur)))
                if open_i is not None and match.prev is not None and match.prev != val(body[open_i]):
                    bad.append("%s opens at %s in the changes in equity but was %s in last year's balance sheet"
                               % (head[c], fmt(val(body[open_i])), fmt(match.prev)))
        if tot_col is not None:
            for r in body:
                vals = [(amount(r[c]) or (Decimal(0), False))[0] if c < len(r) and r[c].strip() else Decimal(0)
                        for c in range(1, len(head))]
                tot = vals[tot_col - 1]
                if sum(vals) - tot != tot:
                    bad.append("the row %s totals %s, its columns make %s" % (r[0], fmt(tot), fmt(sum(vals) - tot)))
        if bad:
            return False, "; ".join(bad[:6]) + " [ÅRL 6 kap. 2 §]"
        return True, "each column of the changes in equity runs from last year's balance sheet to this year's"

    if rule_id == "ANNUAL-DISPOSITION":
        rows = disposition_rows(doc)
        if not rows:
            return False, "no amounts in the proposed disposition of the result [ÅRL 6 kap. 2 §]"
        groups, cur = [], []
        for r in rows:
            cur.append(r)
            if r.kind == "sum":
                groups.append(cur)
                cur = []
        if cur:
            groups.append(cur)
        bad = []
        funds = groups[0]
        fsum_row = funds[-1] if funds[-1].kind == "sum" else None
        flines = [r for r in funds if r.kind == "line"]
        fsum = fsum_row.cur if fsum_row else total(flines, 0)
        if fsum_row and total(flines, 0) != fsum_row.cur:
            bad.append("the funds add up to %s, not the %s stated" % (fmt(total(flines, 0)), fmt(fsum_row.cur)))
        fe = find(bal, FREE_SUM, "sum")
        free = fe.cur if fe else None
        if free is None:
            head = next((j for j, r in enumerate(bal) if r.kind == "head" and r.norm.startswith(FREE_HEAD)), None)
            if head is not None:
                end = next((j for j in range(head + 1, len(bal)) if bal[j].kind != "line"), len(bal))
                free = total(bal[head + 1:end], 0)
            else:
                span = [r for r in bal if r.kind == "line" and r.norm.startswith(FREE_LINES)]
                free = total(span, 0) if span else None
        if free is not None and free != fsum:
            bad.append("the funds at the meeting's disposal are %s but the balance sheet's unrestricted equity is %s"
                       % (fmt(fsum), fmt(free)))
        if len(groups) < 2 or not [r for r in groups[1] if r.kind == "line"]:
            bad.append("there is no proposal for how the funds are disposed of")
        else:
            prop = groups[1]
            plines = [r for r in prop if r.kind == "line"]
            psum = total(plines, 0)
            if prop[-1].kind == "sum" and prop[-1].cur != psum:
                bad.append("the proposal adds up to %s, not the %s stated" % (fmt(psum), fmt(prop[-1].cur)))
            if psum != fsum:
                bad.append("the proposal disposes of %s but %s is at the meeting's disposal" % (fmt(psum), fmt(fsum)))
            div = sum((r.cur or 0) for r in plines if r.norm.startswith(DIVIDEND))
            if div > 0 and div > fsum:
                bad.append("the proposed dividend of %s is larger than the %s at the meeting's disposal"
                           % (fmt(div), fmt(fsum)))
        if bad:
            return False, "; ".join(bad) + " [ÅRL 6 kap. 2 §]"
        return True, "the proposal disposes of the %s of unrestricted equity at the meeting's disposal" % fmt(fsum)

    if rule_id == "ANNUAL-NOTES":
        notes, order = notes_of(doc)
        bad = []
        if not notes:
            return False, "no numbered notes (Not 1, Not 2 ...) [ÅRL 5 kap.]"
        titles = {n: norm(v[0]) for n, v in notes.items()}
        if not any(any(w in t for w in PRINCIPLES) for t in titles.values()):
            bad.append("no note on the accounting policies [ÅRL 5 kap. 4 §; Directive 2013/34/EU Art. 16(1)(a)]")
        emp = [n for n, t in titles.items() if any(w in t for w in EMPLOYEES)]
        if not emp:
            bad.append("no note on the average number of employees [ÅRL 5 kap. 20 §; Art. 16(1)(h)]")
        elif not re.search(r"\d", " ".join(notes[emp[0]][2] + [" ".join(" ".join(r) for r in t) for t in notes[emp[0]][1]])):
            bad.append("the note on employees gives no number")
        if order != list(range(1, len(order) + 1)):
            bad.append("the notes are numbered %s, not 1 to %d in order" % (", ".join(map(str, order)), len(order)))
        refs = sorted({n for r in inc + bal for n in r.notes})
        dangling = [n for n in refs if n not in notes]
        if dangling:
            bad.append("the statements point to note %s, which is not there" % ", ".join(map(str, dangling)))
        fixed = False
        for r in bal:
            if r.kind == "head" and ("anläggningstillgångar" in r.norm or "fixed assets" in r.norm):
                fixed = True
            elif (r.kind == "head" and ("omsättningstillgångar" in r.norm or "current assets" in r.norm)) or \
                    (r.kind == "sum" and r.norm in ("summa anläggningstillgångar", "total fixed assets")):
                fixed = False
            elif fixed and r.kind == "line" and r.cur and not r.notes:
                bad.append("%s is a fixed asset with no note on its cost and depreciation [ÅRL 5 kap. 8 §]" % r.label)
        for r in bal:
            for n in r.notes:
                if n not in notes:
                    continue
                for t in notes[n][1]:
                    h = header_columns(t[0]) if t else None
                    carry = next((c for c in t if c and norm(c[0]).startswith(CARRYING)), None)
                    if not carry:
                        continue
                    idx = h[1] if h else [i for i, c in enumerate(carry) if i and amount(c) is not None]
                    vals = [amount(carry[i])[0] if i < len(carry) and amount(carry[i]) else None for i in idx[:2]]
                    for y, v in enumerate(vals[:years]):
                        if v is not None and r.get(y) is not None and v != r.get(y):
                            bad.append("note %d carries %s at %s %s, the balance sheet at %s"
                                       % (n, r.label, fmt(v), ("this year", "last year")[y], fmt(r.get(y))))
        if bad:
            return False, "; ".join(bad[:8])
        return True, "%d notes, numbered in order, with the accounting policies and employees; every note the " \
                     "statements point to is there" % len(notes)

    if rule_id == "ANNUAL-SIGNED":
        if "sign" not in doc.start:
            return False, "no signatures part: the board (and the managing director) sign and date the report [ÅRL 2 kap. 7 §]"
        texts = doc.paras("sign") + [" ".join(" ".join(r) for r in t) for t in doc.tables("sign")]
        text = " ".join(texts)
        bad = []
        end = None
        if spec and spec.get("year", {}).get("end"):
            try:
                end = dt.date.fromisoformat(spec["year"]["end"])
            except ValueError:
                end = None
        if end is None:
            ends = [d for lab in bal_years for d in dates_in(lab)]
            end = max(ends) if ends else None
        ds = dates_in(text)
        if not ds and "signing.date" not in unknown:
            bad.append("the signatures carry no date [ÅRL 2 kap. 7 §: the report states the day it was signed]")
        elif ds and end and ds[0] <= end:
            bad.append("the report is signed %s, not after the financial year ended %s" % (ds[0], end))
        if spec and (spec.get("signing") or {}).get("board"):
            for b in spec["signing"]["board"]:
                if norm(b.get("name", "")) not in norm(text):
                    bad.append("%s from the spec does not sign" % b.get("name"))
        elif not re.search(r"\b[A-ZÅÄÖÉ][a-zåäöéü]+(?:[- ][A-ZÅÄÖÉ][a-zåäöéü]+)+\b", " ".join(texts)):
            bad.append("no names under the signatures")
        if bad:
            return False, "; ".join(bad)
        if not ds:
            return True, ("WARN the data file declares the signing date unknown, so the signatures leave it on a "
                          "line to be dated when the board signs [ÅRL 2 kap. 7 §]: say so in your reply")
        return True, "signed %s%s" % (ds[0], ", after the year end %s" % end if end else "")

    return None, "unknown rule"


RULES = ["ANNUAL-PARTS", "ANNUAL-PAGES", "ANNUAL-AMOUNTS", "ANNUAL-YEARS", "ANNUAL-SUMS", "ANNUAL-BALANCE", "ANNUAL-RESULT",
         "ANNUAL-EQUITY", "ANNUAL-DISPOSITION", "ANNUAL-NOTES", "ANNUAL-SIGNED"]

if __name__ == "__main__":
    for rule in RULES:
        print(rule, check(rule, sys.argv[1], {}, "first"))
