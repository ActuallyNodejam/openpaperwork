#!/usr/bin/env python3
"""A page that is well formed and says almost nothing does not pass.

House rules, each a plain defect check and none of them taken from a standard: a pass of the other rules
means the page has the right parts in the right places, and these say that the parts are not empty. They
never say a page is complete; they say what is missing.

  MINUTES-EMPTY   Every item of business has something recorded under it: what was reported or noted, a
                  motion, a decision, or in words that nothing was decided. A heading alone fails.
  LETTER-EMPTY    The letter has a body, and the address is one a postman can deliver to: the addressee,
                  the street and number (or a PO box), the town, and the postcode where the country has
                  postcodes. An address window holding a name and a town alone fails.
  TRADE-EMPTY     The same for a trade document's recipient and for the sender's own address in the
                  footer; every line says what it is.
  EMPLOY-EMPTY    Every heading of the statement has a line under it (the builder writes "Not applicable"
                  with the reason for an item that does not apply); a heading alone fails.
  LEGAL-EMPTY     Every heading of an agreement, a review or a redline has text under it.

check(rule_id, path, case, stage) -> (passed, evidence); passed is None when the rule does not apply.
Standard library only.
"""
import html
import json
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

HOUSE = "House rule (a defect check on the page, not a rule from a standard)."
# Countries whose post offices deliver by postcode: every country the library writes letters for, and their
# usual neighbours. Elsewhere the postcode is not asked for.
POSTCODE = {"DE", "AT", "CH", "FR", "BE", "NL", "LU", "SE", "NO", "DK", "FI", "GB", "US", "CA", "AU", "NZ",
            "ES", "IT", "PL", "PT", "CZ", "SK", "LT", "LV", "EE", "HU", "SI", "HR", "GR", "RO", "BG", "IS", "JP"}


# ---- reading a Word file ------------------------------------------------------------------------------

def _levels(z):
    """style id -> heading level (1 is the highest), from the file's own styles."""
    try:
        xml = z.read("word/styles.xml").decode("utf-8", "replace")
    except KeyError:
        return {}
    out = {}
    for sid, body in re.findall(r'<w:style\b[^>]*w:styleId="([^"]+)"[^>]*>(.*?)</w:style>', xml, re.S):
        name = re.search(r'<w:name w:val="([^"]+)"', body)
        lvl = re.search(r'<w:outlineLvl w:val="(\d)"', body)
        m = re.match(r"heading (\d)$", (name.group(1) if name else "").strip().lower())
        if m:
            out[sid] = int(m.group(1))
        elif lvl and int(lvl.group(1)) < 9:
            out[sid] = int(lvl.group(1)) + 1
    return out


def paragraphs(path):
    """[(heading level or 0, text)] for every paragraph of the document, tables included, in order."""
    with zipfile.ZipFile(path) as z:
        levels = _levels(z)
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    out = []
    for p in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S):
        style = re.search(r'<w:pStyle w:val="([^"]+)"', p)
        own = re.search(r'<w:outlineLvl w:val="(\d)"', p)
        level = levels.get(style.group(1), 0) if style else 0
        if own and int(own.group(1)) < 9:
            level = int(own.group(1)) + 1
        text = html.unescape(re.sub(r"<[^>]+>", "", p.replace("<w:br/>", " ").replace("<w:tab/>", " ")))
        out.append((level, re.sub(r"\s+", " ", text).strip()))
    return out


def says_something(text):
    """A line of words, not a rule of underscores or a bare number."""
    return len(re.findall(r"[^\W\d_]{2,}", text)) >= 1 and not re.fullmatch(r"[_\-–—.\s]*", text)


def lonely_headings(path):
    """The headings with nothing under them: the next line that says something is a heading of the same or
    a higher level, or there is none. A heading over deeper headings is their parent and is not alone."""
    paras = [(lvl, t) for lvl, t in paragraphs(path) if t]
    out = []
    for i, (level, text) in enumerate(paras):
        if not level:
            continue
        after = next(((l2, t2) for l2, t2 in paras[i + 1:] if l2 or says_something(t2)), None)
        if after is None or (after[0] and after[0] <= level):
            out.append(text)
    return out


def item_says(item):
    """An item of business in a minutes data file records something: what was noted, a motion, a decision, a
    dissent or a declared conflict."""
    if not isinstance(item, dict):
        return says_something(str(item))
    notes = item.get("notes") or []
    if any(says_something(str(t)) for t in ([notes] if isinstance(notes, str) else notes)):
        return True
    for key in ("motions", "decisions", "dissent", "conflict"):
        for entry in item.get(key) or []:
            text = entry.get("text") if isinstance(entry, dict) else entry
            if says_something(str(text or "")):
                return True
    return False


def spec_with(path, folder, test):
    """The data file a document was built from: a JSON object beside it (or in the folder the check was
    told about) that the test recognises."""
    roots = [Path(path).parent] + ([Path(folder)] if folder else [])
    for root in roots:
        for p in sorted(root.glob("*.json")):
            try:
                data = json.loads(p.read_text())
            except (ValueError, OSError):
                continue
            if isinstance(data, dict) and test(data):
                return data
    return None


def page_text(path):
    """Every word of the file as one lower-case string: a PDF through pdftotext, a Word file or a workbook
    from its parts."""
    path = Path(path)
    kind = path.suffix.lower()
    text = ""
    if kind == ".pdf" and shutil.which("pdftotext"):
        r = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True)
        text = r.stdout
    elif kind in (".docx", ".xlsx"):
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if re.match(r"(word/(document|header\d*|footer\d*)|xl/sharedStrings|xl/worksheets/sheet\d+)\.xml$", name):
                    xml = z.read(name).decode("utf-8", "replace")
                    text += " " + re.sub(r"<[^>]+>", " ", xml)
        text = html.unescape(text)          # a workbook's saved XML writes ö as &#246;
    return re.sub(r"\s+", " ", text).lower()


# ---- the address ---------------------------------------------------------------------------------------

def country_of(party, fallback=""):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "_shared"))
    import letter
    return letter.country_code((party or {}).get("country")) or fallback


def address_gaps(party, home=""):
    """What a postal address lacks: the addressee, the street and number or a PO box, the town, and the
    postcode where the country delivers by postcode."""
    party = party if isinstance(party, dict) else {}
    cc = country_of(party, home)
    gaps = []
    if not str(party.get("name") or "").strip():
        gaps.append("the addressee's name")
    if not any(str(party.get(k) or "").strip() for k in ("street", "street2", "building")):
        gaps.append("the street and number (or the PO box)")
    if not str(party.get("city") or "").strip():
        gaps.append("the town")
    if cc in POSTCODE and not str(party.get("postcode") or "").strip():
        gaps.append("the postcode")
    return gaps


def address_problem(party, what, key, home=""):
    gaps = address_gaps(party, home)
    if not gaps:
        return None
    party = party if isinstance(party, dict) else {}
    given = [str(party.get(k)).strip() for k in ("name", "attention", "street", "postcode", "city", "country")
             if str(party.get(k) or "").strip()]
    return ("%s holds only %s: a postal address also has %s. Take them from the person's notes and files and put "
            "them in \"%s\"; if the files do not give them, say so in your reply and ask. Never make an address up"
            % (what, ", ".join('"%s"' % g for g in given) or "nothing", " and ".join(gaps), key))


def not_on_page(party, text, keys=("street", "city")):
    """The parts of the address the data file gives that the page does not show."""
    out = []
    bare = lambda v: re.sub(r"[\s.,]", "", v)  # noqa: E731
    for k in keys:
        value = str((party or {}).get(k) or "").strip().lower()
        if value and bare(value) not in bare(text):
            out.append(str(party[k]))
    return out


# ---- the rules -----------------------------------------------------------------------------------------

def check(rule_id, path, case, stage):
    path = Path(path)
    folder = (case or {}).get("folder") or ""
    kind = path.suffix.lower()
    if rule_id == "MINUTES-EMPTY":
        if kind != ".docx":
            return None, "minutes are checked as Word files"
        spec = spec_with(path, folder, lambda d: isinstance(d.get("items"), list) and d.get("meeting"))
        empty = []
        if spec:
            # The data file beside the minutes: an item that gives no notes, motion, decision, dissent or
            # conflict prints as a heading alone (the last one too, where the closing lines follow it).
            empty = [str(i.get("title") if isinstance(i, dict) else i) for i in spec["items"] if not item_says(i)]
        low = [e.lower() for e in empty]
        empty += [h for h in lonely_headings(path) if not any(e and e in h.lower() for e in low)]
        if not empty:
            return True, "every item of business has something recorded under it"
        return False, ("nothing is recorded under %d heading%s: %s. Minutes record what was done under each item of "
                       "business: what was reported or noted, each motion with its result, each decision with its "
                       "vote. Put it in the item's \"notes\", \"motions\" and \"decisions\" from the person's notes; "
                       "where the meeting decided nothing, say so in words. %s"
                       % (len(empty), "" if len(empty) == 1 else "s", "; ".join('"%s"' % e[:60] for e in empty[:8]), HOUSE))
    if rule_id in ("EMPLOY-EMPTY", "LEGAL-EMPTY"):
        if kind != ".docx":
            return None, "checked as a Word file"
        lone = lonely_headings(path)
        if not lone:
            return True, "every heading has text under it"
        what = "statement" if rule_id == "EMPLOY-EMPTY" else "document"
        fix = ("Write the term under it, or \"Not applicable\" with the reason, as the builder does"
               if rule_id == "EMPLOY-EMPTY" else "Write the clause's text under it, or take the heading out")
        return False, ("%d heading%s of the %s %s nothing under %s: %s. %s. %s"
                       % (len(lone), "" if len(lone) == 1 else "s", what, "has" if len(lone) == 1 else "have",
                          "it" if len(lone) == 1 else "them", "; ".join('"%s"' % h[:60] for h in lone[:8]), fix, HOUSE))
    if rule_id == "LETTER-EMPTY":
        spec = spec_with(path, folder, lambda d: isinstance(d.get("recipient"), dict) and "body" in d)
        if not spec:
            return None, "no letter data file beside the letter to read the address and the body from"
        bad = []
        body = spec.get("body")
        paras_ = [body] if isinstance(body, str) else list(body or [])
        if not any(says_something(str(p)) for p in paras_):
            bad.append("the letter has no body: the paragraphs between the salutation and the closing are empty")
        home = country_of(spec.get("sender"))
        problem = address_problem(spec.get("recipient"), "the address", "recipient", home)
        if problem:
            bad.append(problem)
        else:
            text = page_text(path)
            lost = not_on_page(spec["recipient"], text) if text else []
            if lost:
                bad.append("the address on the page lacks %s, which the data file gives" % ", ".join('"%s"' % x for x in lost))
        if not bad:
            return True, "the letter has a body and an address a postman can deliver to"
        return False, "%s. %s" % ("; ".join(bad), HOUSE)
    if rule_id == "TRADE-EMPTY":
        spec = spec_with(path, folder, lambda d: d.get("type") and isinstance(d.get("lines"), list)
                         and isinstance(d.get("seller"), dict) and isinstance(d.get("buyer"), dict))
        if not spec:
            return None, "no trade document data file beside the file to read the addresses and the lines from"
        order = spec.get("type") == "purchase_order"
        to_key, from_key = ("seller", "buyer") if order else ("buyer", "seller")
        home = country_of(spec.get(from_key))
        bad = []
        problem = address_problem(spec.get(to_key), "the address", to_key, home)
        if problem:
            bad.append(problem)
        own = address_problem(spec.get(from_key), "the sender's own address in the footer", from_key, home)
        if own:
            bad.append(own)
        lines = [l for l in spec.get("lines") or [] if isinstance(l, dict)]
        blank = [i + 1 for i, l in enumerate(lines) if not says_something(str(l.get("description") or ""))]
        if not lines:
            bad.append("the document has no lines")
        elif blank:
            bad.append("line%s %s say%s nothing in \"description\"" % ("" if len(blank) == 1 else "s",
                       ", ".join(map(str, blank)), "s" if len(blank) == 1 else ""))
        if not problem:
            text = page_text(path)
            lost = not_on_page(spec[to_key], text) if text else []
            if lost:
                bad.append("the address on the page lacks %s, which the data file gives" % ", ".join('"%s"' % x for x in lost))
        if not bad:
            return True, "the addresses are whole and every line says what it is"
        return False, "%s. %s" % ("; ".join(bad), HOUSE)
    return None, "no such rule"
