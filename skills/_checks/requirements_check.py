#!/usr/bin/env python3
"""Checks for a requirements specification, from NASA's Systems Engineering Handbook (NASA/SP-2016-6105
Rev 2), Appendix C "How to Write a Good Requirement", a US Government work in the public domain; the
verbal forms of the ISO/IEC Directives, Part 2 (2021), clause 7, cited; and for values with units, the SI
Brochure, 9th edition (BIPM, version 4.01, June 2026, CC BY 4.0) section 5 and NIST SP 811 (2008 Edition),
public domain.

  REQ-ID        Every requirement has an id of its own (letters, a hyphen and a number, e.g. SLG-001), used
                once; a "shall" outside an identified requirement is a requirement with no id.
  REQ-VERB      "shall" marks a requirement, "will" a fact and "should" a goal: a requirement with no
                "shall", or one that says "must", is flagged (Swedish: ska, kommer att, bör, måste).
  REQ-ONE       One "shall" per requirement statement: two are two requirements.
  REQ-VAGUE     No ambiguous or unverifiable word in a requirement: as appropriate, etc., and/or, adequate,
                user-friendly, fast, easy, sufficient, minimize, maximize and the others Appendix C names.
  REQ-NEGATIVE  A warning: Appendix C (C.3) asks for a requirement stated positively, not with "shall not".
  REQ-TBD       Every TBD or TBR in a requirement is listed with who resolves it and by when.
  REQ-VERIFY    Every requirement names how it is verified: test, analysis, inspection or demonstration.
  UNITS-SPACE   A space between the number and the unit symbol, 20 °C and 5 % included; none before the
                plane-angle degree (30°).
  UNITS-SYMBOL  The unit's own symbol (kg, kN, MPa, s, h, min; never Kg, sec, hr, kgs), no full stop after a
                symbol inside a sentence, at most one solidus, no symbol mixed with a unit name.

A drafting check: it says which rules the text meets, never that the product or the document complies.
A requirement is a table row whose first cell is its id, under a heading row naming the statement column
(Requirement, Goal, Krav, Mål), or a paragraph that begins with its id. With a requirements spec beside the
file (skills/requirements-spec) REQ-ID and REQ-TBD also compare the file with it.
check(rule_id, path, case, stage) -> (passed, evidence); passed is None when the rule does not apply.
"""
import datetime as dt
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

ID = r"[A-Z][A-Z0-9]{0,7}(?:[-_.][A-Z0-9]{1,8})*[-_.][A-Z]{0,3}\d{1,5}[a-z]?"
ID_CELL = re.compile(r"^\[?(%s)\]?[.:]?$" % ID)
ID_LEAD = re.compile(r"^\[?(%s)\]?(?:\s*[:.)–—-]\s*|\s+)(\S.*)$" % ID)
ID_ANY = re.compile(r"\b%s\b" % ID)
MARKER = re.compile(r"\bTB[DR](?:[-_]?\d{1,3})?\b")
TBD_ID = re.compile(r"^TB[DRC](?:[-_.]|$)")

SHALL = re.compile(r"\b(?:shall|skall|ska)\b", re.I)
SHOULD = re.compile(r"\b(?:should|bör)\b", re.I)
WILL = re.compile(r"\b(?:will|kommer att)\b", re.I)
MUST = re.compile(r"\b(?:must|måste)\b", re.I)
NEGATIVE = re.compile(r"\b(?:shall\s+(?:not|never)|shan[’']t|skall?\s+(?:inte|icke|ej|aldrig)|får\s+(?:inte|icke|ej|aldrig))\b",
                      re.I)
QUOTED = re.compile(r"[“”\"„»«][^“”\"„»«]{1,24}[“”\"„»«]|‘[^‘’]{1,24}’")
METHOD = re.compile(r"\b(?:test(?:s|ed|ing)?|analys(?:is|es|ed|e)?|inspect(?:ion|ed)?|demonstrat(?:ion|ed)?|"
                    r"prov(?:ning|as)?|inspektion|granskning|demonstration)\b", re.I)

STMT_HEAD = re.compile(r"\b(?:requirements?|statement|goals?|krav|kravtext|mål)\b", re.I)
LOOSE_HEAD = re.compile(r"\b(?:description|text|beskrivning)\b", re.I)
GOAL_HEAD = re.compile(r"\b(?:goals?|mål)\b", re.I)
REQ_WORD = re.compile(r"\b(?:requirements?|krav)\b", re.I)
ID_HEAD = re.compile(r"\b(?:id|nr|no|number|nummer|ref)\b", re.I)
VERIFY_HEAD = re.compile(r"verif", re.I)
OWNER_HEAD = re.compile(r"\b(?:owner|responsible|ansvarig)\b", re.I)
DUE_HEAD = re.compile(r"\b(?:due|date|by when|deadline|datum|klart|senast)\b", re.I)
OWNER_INLINE = re.compile(r"\b(?:[Oo]wner|[Rr]esponsible|[Aa]nsvarig)\b\s*[:,]?\s*(?:is\s+|är\s+)?[A-ZÅÄÖÉ][\w'’-]+")
PLACEHOLDER = re.compile(r"^(?:tb[cdr]|-|–|—|\?|n/?a|none|ingen|okänd|unknown|x|\.+)?$", re.I)
# What requirements_create.py prints for an owner or a date the notes do not give, as the skill asks: still open, said
# so in the reply (WARN), never a fail the run can pass only by making a name or a date up (timed run c17, 2026-10-25).
TO_AGREE = re.compile(r"^(?:to be agreed|att bestämma)$", re.I)
MONTH = r"(?:jan|feb|mar|apr|may|maj|jun|jul|aug|sep|oct|okt|nov|dec)[a-zé]*\.?"
DATE = re.compile(r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}|(?:\d{1,2}\.? )?%s,? \d{4}|%s \d{1,2},? \d{4}|"
                  r"Q[1-4] \d{4}|(?:v\.|vecka|week|wk)\s?\d{1,2}\b)" % (MONTH, MONTH), re.I)
LABEL = re.compile(r"^(?:rationale|verification|verified by|method|motivering|verifiering|metod)\b", re.I)

# Appendix C, C.4 Clarity and Verifiability: the ambiguous and unverifiable terms it names, with the common
# "-ly" and "-ize" words it asks to avoid. The Swedish list is our own translation of the same terms.
VAGUE = {
    "en": [("as appropriate", r"\bas appropriate\b"), ("appropriate", r"\bappropriate(?:ly)?\b"),
           ("etc.", r"\betc\b\.?"), ("and/or", r"\band\s*/\s*or\b"), ("but not limited to", r"\bbut not limited to\b"),
           ("flexible", r"\bflexib(?:le|ly|ility)\b"), ("easy", r"\beas(?:y|ier|iest|ily)\b"),
           ("sufficient", r"\bsufficient(?:ly)?\b"), ("safe", r"(?<![-\w])safe(?:ly)?\b"), ("ad hoc", r"\bad[- ]hoc\b"),
           ("adequate", r"\badequate(?:ly)?\b"), ("accommodate", r"\baccommodat\w*"),
           ("user-friendly", r"\buser[- ]friendly\b"), ("usable", r"\busable\b"), ("when required", r"\bwhen required\b"),
           ("if required", r"\bif required\b"), ("fast", r"\bfast(?:er|est)?\b(?!-)"), ("portable", r"\bportable\b"),
           ("light-weight", r"\blight[- ]?weight\b"), ("small", r"\bsmall\b"), ("large", r"\blarge\b"),
           ("maximize", r"\bmaximi[sz]\w*"), ("minimize", r"\bminimi[sz]\w*"), ("robust", r"\brobust(?:ly|ness)?\b"),
           ("quickly", r"\bquick(?:ly)?\b(?!-)"), ("clearly", r"\bclearly\b"), ("approximately", r"\bapproximately\b"),
           ("reasonably", r"\breasonabl[ey]\b"), ("efficiently", r"\befficient(?:ly)?\b"),
           ("effectively", r"\beffective(?:ly)?\b"), ("optimize", r"\boptimi[sz]\w*|\boptimal(?:ly)?\b")],
    "sv": [("vid behov", r"\b(?:vid|efter) behov\b"), ("lämplig", r"\blämplig(?:t|a|en)?\b"), ("osv.", r"\bosv\b\.?"),
           ("etc.", r"\betc\b\.?"), ("m.m.", r"\bm\.\s?m\.|\bmed mera\b"), ("och/eller", r"\boch\s*/\s*eller\b"),
           ("men inte begränsat till", r"\bmen inte begränsa\w* till\b"), ("flexibel", r"\bflexib(?:el|elt|la)\b"),
           ("enkel", r"\benk(?:el|elt|la|lare)\b"), ("lätt", r"\blätt(?:a|are)?\b"),
           ("tillräcklig", r"\btillräcklig(?:t|a)?\b"), ("säker", r"(?<![-\w])säk(?:er|ert|ra)\b"),
           ("adekvat", r"\badekvat(?:a)?\b"), ("användarvänlig", r"\banvändarvänlig(?:t|a)?\b"),
           ("snabb", r"\bsnabb(?:t|a|are)?\b(?!-)"), ("bärbar", r"\bbärbar(?:t|a)?\b"), ("liten", r"\b(?:liten|litet|små)\b"),
           ("stor", r"\b(?:stor|stort|stora)\b"), ("maximera", r"\bmaximer\w*"), ("minimera", r"\bminimer\w*"),
           ("robust", r"\brobust(?:a)?\b"), ("tydlig", r"\btydlig(?:t|a)?\b"),
           ("när det krävs", r"\b(?:när|om) det (?:krävs|behövs)\b"), ("ungefär", r"\bungefär\b|\bcirka\b|\bca\b\.?"),
           ("effektiv", r"\beffektiv(?:t|a)?\b"), ("optimera", r"\boptimer\w*")],
}

# SI Brochure 5.2 and NIST SP 811 6.1: the symbols, with the wrong forms seen in the wild and their right ones.
NUM = r"(?<![\w.,/])[-+−]?\d+(?:[.,]\d+)*"
SYMBOLS = ["°C", "%", "‰", "kWh", "MWh", "GWh", "Wh", "kHz", "MHz", "GHz", "Hz", "kPa", "MPa", "GPa", "hPa", "Pa",
           "mbar", "bar", "kN", "MN", "N", "kJ", "MJ", "J", "mW", "kW", "MW", "GW", "W", "mV", "kV", "V", "mA", "kA",
           "µA", "μA", "kΩ", "MΩ", "Ω", "mm²", "cm²", "m²", "mm³", "cm³", "m³", "mm", "cm", "km", "µm", "μm", "nm", "m",
           "mg", "kg", "g", "t", "ms", "µs", "μs", "ns", "min", "s", "h", "mL", "ml", "L", "l", "dB", "lx", "lm", "mol"]
SYM = "|".join(re.escape(s) for s in sorted(SYMBOLS, key=len, reverse=True))
AFTER = r"(?![\wµμΩ²³°])"
VALUE = re.compile(r"%s\s?(?:%s)%s" % (NUM, SYM, AFTER))
NO_SPACE = re.compile(r"(%s)(%s)%s" % (NUM, SYM, AFTER))
DEG_SPLIT = re.compile(r"(%s)\s?°\s+C\b" % NUM)
ANGLE_SPACE = re.compile(r"(%s)\s+°(?!\s?[CF]\b)" % NUM)
HYPHEN = re.compile(r"(%s)-(%s)%s" % (NUM, SYM, AFTER))
BAD = {"Kg": "kg", "KG": "kg", "kgs": "kg", "Kgs": "kg", "KGS": "kg", "kilos": "kg", "kilo": "kg", "gm": "g",
       "gms": "g", "sec": "s", "secs": "s", "Sec": "s", "Secs": "s", "SEC": "s", "msec": "ms", "msecs": "ms",
       "usec": "µs", "sek": "s", "hr": "h", "hrs": "h", "Hr": "h", "Hrs": "h", "HR": "h", "HRS": "h", "tim": "h",
       "mins": "min", "Min": "min", "Mins": "min", "MIN": "min", "cms": "cm", "mms": "mm", "kms": "km", "Km": "km",
       "KM": "km", "CM": "cm", "Cm": "cm", "MM": "mm", "mtr": "m", "mtrs": "m", "Mtr": "m", "cc": "cm³", "mps": "m/s",
       "kph": "km/h", "Kph": "km/h", "KPH": "km/h", "kmph": "km/h", "kmh": "km/h", "km/hr": "km/h", "ltr": "L",
       "ltrs": "L", "Ltr": "L", "Ltrs": "L", "lit": "L", "amp": "A", "amps": "A", "Amp": "A", "Amps": "A", "Kw": "kW",
       "KW": "kW", "kw": "kW", "Kwh": "kWh", "KWh": "kWh", "kwh": "kWh", "KWH": "kWh", "Mpa": "MPa", "MPA": "MPa",
       "mpa": "MPa", "KPa": "kPa", "Kpa": "kPa", "kpa": "kPa", "KPA": "kPa", "KN": "kN", "Kn": "kN", "hz": "Hz",
       "HZ": "Hz", "Khz": "kHz", "KHz": "kHz", "khz": "kHz", "KHZ": "kHz", "Mhz": "MHz", "mhz": "MHz", "MHZ": "MHz",
       "Ghz": "GHz", "ghz": "GHz", "GHZ": "GHz", "KJ": "kJ", "Kj": "kJ", "KV": "kV", "Kv": "kV", "°c": "°C", "ºC": "°C",
       "degC": "°C", "deg C": "°C", "deg. C": "°C", "°K": "K", "sq m": "m²", "sq. m": "m²", "sqm": "m²", "sq.m": "m²",
       "sq mm": "mm²", "sq. mm": "mm²", "kvm": "m²", "cu m": "m³", "cu. m": "m³"}
WRONG = re.compile(r"(%s)\s?(%s)(?![\w²³])" % (NUM, "|".join(re.escape(k) for k in sorted(BAD, key=len, reverse=True))))
STOP = re.compile(r"(%s\s?(?:%s))\.(?=\s+[a-zåäöæø])" % (NUM, SYM))
SOLIDUS = re.compile(r"%s\s?[A-Za-zµμΩ°²³·]+\d?\s?/\s?[A-Za-zµμΩ²³·]+\d?\s?/\s?[A-Za-zµμΩ²³·]+" % NUM)
NAMES = (r"(?:seconds?|minutes?|hours?|days?|metres?|meters?|kilometres?|kilometers?|kilograms?|grams?|litres?|"
         r"liters?|newtons?|watts?|joules?|volts?|pascals?|sekund\w*|minut\w*|timm\w*|dygn|kilogram|liter)")
MIXED = re.compile(r"%s\s?(?:kg|km|cm|mm|m|g|s|h|N|W|J|L|l|kW|kN)\s+(?:per|i)\s+%s\b|\b%s\s?/\s?(?:s|h|min|km|m|kg|g|L|l)\b"
                   % (NUM, NAMES, NAMES))


def para_text(p):
    out = []
    for el in p.iter():
        if el.tag == W + "t":
            out.append(el.text or "")
        elif el.tag in (W + "tab", W + "br", W + "cr"):
            out.append(" ")
        elif el.tag == W + "noBreakHyphen":
            out.append("-")
    return re.sub(r"\s+", " ", "".join(out)).strip()


def blocks_of(path):
    """The body in order: ("p", style, text) for a paragraph and ("t", rows) for a table of cell texts."""
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    out = []

    def walk(node):
        for child in node:
            if child.tag == W + "p":
                style = child.find(W + "pPr/" + W + "pStyle")
                out.append(("p", style.get(W + "val", "") if style is not None else "", para_text(child)))
            elif child.tag == W + "tbl":
                rows = [[" ".join(para_text(p) for p in tc.iter(W + "p")).strip() for tc in tr.findall(W + "tc")]
                        for tr in child.findall(W + "tr")]
                out.append(("t", rows))
            elif child.tag in (W + "sdt", W + "sdtContent", W + "customXml"):
                walk(child)

    body = root.find(W + "body")
    walk(body if body is not None else root)
    return out


def language_of(path, spec, units):
    if spec and spec.get("language"):
        return "sv" if str(spec["language"]).lower().startswith("sv") else "en"
    try:
        with zipfile.ZipFile(path) as z:
            core = z.read("docProps/core.xml").decode("utf-8", "replace")
        lang = re.search(r"<dc:language>([^<]+)</dc:language>", core)
        if lang:
            return "sv" if lang.group(1).lower().startswith("sv") else "en"
    except (KeyError, zipfile.BadZipFile):
        pass
    text = " ".join(u["text"] for u in units)
    return "sv" if len(re.findall(r"\bskall?\b", text, re.I)) > len(re.findall(r"\bshall\b", text, re.I)) else "en"


def unquote(text):
    return QUOTED.sub(" ", text)


def heading(style):
    return bool(re.match(r"(?:heading|rubrik|title)", style or "", re.I))


def read(path):
    """Requirements and goals as units, the paragraphs and table rows outside them, and the TBD lists."""
    units, loose, tbd_rows, under_goal, last = [], [], [], False, None
    for block in blocks_of(path):
        if block[0] == "p":
            style, text = block[1], block[2]
            if not text:
                continue
            if heading(style):
                under_goal = bool(GOAL_HEAD.search(text)) and not REQ_WORD.search(text)
                last = None
                continue
            m = ID_LEAD.match(text)
            body = m.group(2) if m else ""
            if m and not TBD_ID.match(m.group(1)) and len(body.split()) >= 3 and (
                    SHALL.search(body) or SHOULD.search(body) or MUST.search(body) or WILL.search(body)):
                last = dict(id=m.group(1), text=body, kind="goal" if under_goal else "req", row=text, verify="")
                units.append(last)
            elif last is not None and LABEL.match(text):
                last["row"] += " " + text                     # its rationale or verification line below it
                last["verify"] += " " + text
                loose.append(text)
            else:
                last = None
                loose.append(text)
            continue
        last = None
        rows = [r for r in block[1] if any(c.strip() for c in r)]
        if not rows:
            continue
        head = [c.strip() for c in rows[0]]
        if ID_CELL.match(head[0]):
            idc, sc, vc, goal, strict, body = 0, 1, None, under_goal, True, rows
        else:
            idc = next((i for i, c in enumerate(head) if ID_HEAD.search(c) and len(c) < 25), 0)
            sc = next((i for i, c in enumerate(head) if i != idc and STMT_HEAD.search(c) and not ID_HEAD.search(c)), None)
            strict = sc is not None
            if sc is None:
                sc = next((i for i, c in enumerate(head) if i != idc and LOOSE_HEAD.search(c)), None)
            vc = next((i for i, c in enumerate(head) if VERIFY_HEAD.search(c)), None)
            named = head[sc] if sc is not None else ""
            goal = bool(GOAL_HEAD.search(named)) or (under_goal and not REQ_WORD.search(named))
            body = rows[1:]
            oc = next((i for i, c in enumerate(head) if OWNER_HEAD.search(c)), None)
            dc = next((i for i, c in enumerate(head) if i != oc and DUE_HEAD.search(c)), None)
            if oc is not None and dc is not None:
                for r in body:
                    tbd_rows.append(dict(row=" ".join(r), owner=r[oc] if oc < len(r) else "",
                                         due=r[dc] if dc < len(r) else ""))
        for r in body:
            cell = r[idc].strip() if idc < len(r) else ""
            m = ID_CELL.match(cell)
            stmt = r[sc].strip() if sc is not None and sc < len(r) else ""
            modal = SHALL.search(stmt) or SHOULD.search(stmt) or MUST.search(stmt) or WILL.search(stmt)
            if m and not TBD_ID.match(m.group(1)) and stmt and not ID_CELL.match(stmt) and len(stmt.split()) >= 3 \
                    and (strict or modal):
                rest = [c for i, c in enumerate(r) if i not in (idc, sc)]
                units.append(dict(id=m.group(1), text=stmt, kind="goal" if goal else "req", row=" ".join(r),
                                  verify=r[vc] if vc is not None and vc < len(r) else " ".join(rest)))
            else:
                loose.append(" ".join(r))
    return units, loose, tbd_rows


def spec_beside(path):
    for p in sorted(Path(path).parent.glob("*.json")):
        try:
            data = json.loads(p.read_text())
        except (ValueError, OSError):
            continue
        if isinstance(data, dict) and isinstance(data.get("requirements"), list) and data.get("product"):
            return data
    return None


def short(text, n=60):
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= n else text[:n - 1].rstrip() + "…"


def date_forms(value):
    try:
        d = dt.date.fromisoformat(str(value).strip())
    except ValueError:
        return {str(value).strip().lower()}
    return {d.isoformat(), d.strftime("%d/%m/%Y"), "%d/%d/%d" % (d.day, d.month, d.year),
            ("%d %s %d" % (d.day, d.strftime("%B"), d.year)).lower()}


def all_text(path):
    """Every paragraph and every table cell on its own, so a full stop never runs into the next cell."""
    out = []
    for block in blocks_of(path):
        if block[0] == "p":
            out.append(block[2])
        else:
            out.extend(c for r in block[1] for c in r)
    return out


def check_tbd(units, loose, tbd_rows, spec):
    bad, keys, n, agreed = [], set(), 0, []
    for t in tbd_rows:
        found = set(ID_ANY.findall(t["row"])) | set(MARKER.findall(t["row"]))
        if not found:
            continue
        n += 1
        name = sorted(found, key=lambda k: (not TBD_ID.match(k), k))[0]
        owner, due = t["owner"].strip(), t["due"].strip()
        problems = []
        if not TO_AGREE.match(owner) and (PLACEHOLDER.match(owner) or not re.search(r"[A-Za-zÅÄÖåäö]", owner)):
            problems.append("no owner")
        if not TO_AGREE.match(due) and not DATE.search(due):
            problems.append("no date")
        if problems:
            bad.append("%s has %s" % (name, " and ".join(problems)))
        else:
            keys |= found
            if TO_AGREE.match(owner) or TO_AGREE.match(due):
                agreed.append(name)
    for text in loose:                                        # a list kept as paragraphs
        if MARKER.search(text) and OWNER_INLINE.search(text) and DATE.search(text):
            keys |= set(ID_ANY.findall(text)) | set(MARKER.findall(text))
    for u in units:
        marks = MARKER.findall(u["row"])
        if not marks:
            continue
        n += 1
        numbered = [m for m in marks if re.search(r"\d", m)]
        if any(m in keys for m in numbered) or u["id"] in keys:
            continue
        if OWNER_INLINE.search(u["row"]) and DATE.search(u["row"]):
            continue
        bad.append("%s has %s with no owner and date: list it with who resolves it and by when" % (u["id"], marks[0]))
    if spec:
        flat = " ".join(t["row"] for t in tbd_rows) + " " + " ".join(loose) + " " + " ".join(u["row"] for u in units)
        flat = re.sub(r"\s+", " ", flat).lower()
        for t in spec.get("tbd") or []:
            n += 1
            if t.get("owner") and str(t["owner"]).lower() not in flat:
                bad.append("%s: the owner %s is not named" % (t.get("id", "a TBD"), t["owner"]))
            if t.get("due") and not any(f in flat for f in date_forms(t["due"])):
                bad.append("%s: the date %s is not given" % (t.get("id", "a TBD"), t["due"]))
    if not n:
        return None, "no TBD or TBR in the requirements"
    bad = list(dict.fromkeys(bad))
    if not bad and agreed:
        return True, ("WARN %s: who resolves it or by when is still to be agreed, since the notes do not say; name "
                      "it in the reply as open for the person" % ", ".join(agreed))
    return (not bad, "; ".join(bad[:4]) or "every TBD and TBR has an owner and a date (App. C, C.3)")


def check_units(rule_id, path):
    texts = all_text(path)
    values = sum(len(VALUE.findall(t)) for t in texts)
    bad = []
    for t in texts:
        if rule_id == "UNITS-SPACE":
            for m in NO_SPACE.finditer(t):
                num, sym = m.group(1), m.group(2)
                if sym == "s" and (re.fullmatch(r"(?:1[0-9]|20)\d0", num.lstrip("+-−"))
                                   or re.search(r"\bthe\s+$", t[:m.start()])):
                    continue                                  # the 1990s, the 60s: decades, not seconds
                bad.append("«%s» → %s %s" % (m.group(0), num, sym))
            for m in DEG_SPLIT.finditer(t):
                bad.append("«%s» → %s °C" % (m.group(0), m.group(1)))
            for m in ANGLE_SPACE.finditer(t):
                bad.append("«%s» → %s° (no space before the degree of angle)" % (m.group(0), m.group(1)))
            for m in HYPHEN.finditer(t):
                bad.append("«%s» → %s %s (a space, not a hyphen, even as an adjective)" % (m.group(0), m.group(1), m.group(2)))
        else:
            for m in WRONG.finditer(t):
                bad.append("«%s» → %s %s" % (m.group(0), m.group(1), BAD[m.group(2)]))
            for m in STOP.finditer(t):
                bad.append("«%s.» has a full stop inside a sentence" % m.group(1))
            for m in SOLIDUS.finditer(t):
                bad.append("«%s» uses the solidus twice: write it with one solidus and an exponent" % m.group(0))
            for m in MIXED.finditer(t):
                bad.append("«%s» mixes a unit symbol and a unit name" % m.group(0))
    bad = list(dict.fromkeys(bad))
    if not bad and not values:
        return None, "no value with a unit symbol"
    if rule_id == "UNITS-SPACE":
        why = "a space between number and unit symbol (SI Brochure 5.4.3, 5.4.7; NIST SP 811 7.2)"
    else:
        why = "the unit's own symbol, no full stop, one solidus (SI Brochure 5.2; NIST SP 811 6.1)"
    if bad:
        return False, "%s; %s" % ("; ".join(bad[:5]) + (" and %d more" % (len(bad) - 5) if len(bad) > 5 else ""), why)
    return True, "%d values with units, each with %s" % (values, why)


def check(rule_id, path, case, stage):
    path = Path(path)
    if path.suffix.lower() != ".docx":
        return None, "a requirements specification is checked as a Word file"
    if rule_id.startswith("UNITS-"):
        return check_units(rule_id, path)
    truth = (case or {}).get("truth") or {}
    spec = spec_beside(path) or (truth if truth.get("requirements") or truth.get("tbd") else None)
    units, loose, tbd_rows = read(path)
    reqs = [u for u in units if u["kind"] == "req"]
    if rule_id == "REQ-ID":
        ids = [u["id"] for u in units]
        bad = ["%s is used %d times" % (i, ids.count(i)) for i in dict.fromkeys(i for i in ids if ids.count(i) > 1)]
        stray = [t for t in loose if SHALL.search(unquote(t))]
        bad += ["a requirement with no id: «%s»" % short(t) for t in stray]
        if spec:
            want = [r.get("id") for r in list(spec.get("requirements") or []) + list(spec.get("goals") or [])]
            missing = [i for i in want if i and i not in ids]
            if missing:
                bad.append("in the spec but not in the file: %s" % ", ".join(missing[:6]))
        if not units and not stray:
            return False, "no requirement with an id was found: put the id (letters, a hyphen and a number, e.g. " \
                          "SLG-001) first in the row or paragraph, then the statement"
        return (not bad, "; ".join(bad[:4]) or "%d requirements and goals, each with an id of its own" % len(units))
    if rule_id == "REQ-TBD":
        return check_tbd(units, loose, tbd_rows, spec)
    if not units:
        return None, "no requirement with an id was found"
    lang = language_of(path, spec, units)
    if rule_id == "REQ-VERB":
        bad = []
        for u in units:
            s = unquote(u["text"])
            if u["kind"] == "goal":
                if SHALL.search(s):
                    bad.append("%s is a goal but says 'shall': a goal says 'should'" % u["id"])
                elif not SHOULD.search(s):
                    bad.append("%s is a goal with no 'should'" % u["id"])
                continue
            if MUST.search(s):
                bad.append("%s says '%s': write 'shall' (ISO/IEC Directives Part 2, 7.2; 'must' is for a constraint "
                           "from outside the document)" % (u["id"], MUST.search(s).group(0)))
            elif not SHALL.search(s):
                said = SHOULD.search(s) or WILL.search(s)
                bad.append("%s has no 'shall'%s" % (u["id"], " (it says '%s')" % said.group(0) if said else ""))
        why = "'shall' marks a requirement, 'will' a fact, 'should' a goal (NASA SE Handbook App. C, C.1)"
        word = "'ska' (shall)" if lang == "sv" else "'shall'"
        return (not bad, "%s; %s" % ("; ".join(bad[:4]), why) if bad else "%d requirements say %s" % (len(reqs), word))
    if not reqs:
        return None, "no requirement, only goals"
    if rule_id == "REQ-ONE":
        bad = ["%s has %d" % (u["id"], len(SHALL.findall(unquote(u["text"])))) for u in reqs
               if len(SHALL.findall(unquote(u["text"]))) > 1]
        return (not bad, "more than one 'shall': %s; one requirement per statement (App. C, C.4 Clarity)"
                % "; ".join(bad[:5]) if bad else "one 'shall' in each of %d requirements" % len(reqs))
    if rule_id == "REQ-VAGUE":
        bad = []
        for u in reqs:
            s = unquote(u["text"])
            found = [label for label, rx in VAGUE[lang] if re.search(rx, s, re.I)]
            if "as appropriate" in found and "appropriate" in found:
                found.remove("appropriate")
            if found:
                bad.append("%s: %s" % (u["id"], ", ".join("'%s'" % f for f in found)))
        return (not bad, "%s; give a value with its tolerance or a condition that can be verified (App. C, C.4)"
                % "; ".join(bad[:5]) if bad else "no ambiguous or unverifiable word in %d requirements" % len(reqs))
    if rule_id == "REQ-NEGATIVE":
        bad = ["%s says '%s'" % (u["id"], NEGATIVE.search(unquote(u["text"])).group(0)) for u in reqs
               if NEGATIVE.search(unquote(u["text"]))]
        return (not bad, "warning: %s; App. C, C.3 asks for a requirement stated positively: say what it shall do"
                % "; ".join(bad[:5]) if bad else "every requirement is stated positively")
    if rule_id == "REQ-VERIFY":
        bad = [u["id"] for u in reqs if not METHOD.search(u["verify"])]
        return (not bad, "no verification method for %s: name test, analysis, inspection or demonstration "
                "(App. C, C.4 Verifiability)" % ", ".join(bad[:8]) if bad
                else "each of %d requirements names how it is verified" % len(reqs))
    return None, "unknown rule"


RULES = ("REQ-ID", "REQ-VERB", "REQ-ONE", "REQ-VAGUE", "REQ-NEGATIVE", "REQ-TBD", "REQ-VERIFY", "UNITS-SPACE",
         "UNITS-SYMBOL")

if __name__ == "__main__":
    for rule in RULES:
        print(rule, check(rule, sys.argv[1], {}, "first"))
