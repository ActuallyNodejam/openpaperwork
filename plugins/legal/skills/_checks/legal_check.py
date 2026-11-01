#!/usr/bin/env python3
"""The agreement check, for Word files: an agreement we draft, a review of the other side's paper,
and a redline of it. It reads structure and evidence, never the merits. It never says whether a
term is fair, usual or enforceable, or whether anyone should sign; that is for the parties and their
lawyers.

Drafting (an agreement the pack laid out):
  LEGAL-PARTIES   Every party is named with its registration number and address (from the spec).
  LEGAL-DATE      The agreement states the date it takes effect.
  LEGAL-TERMS     Each defined term is defined once and used in the agreement.
  LEGAL-XREF      Every reference to one of the agreement's own clauses points at a clause that
                  exists; references to another instrument (a clause of the EEA SCCs, a section of
                  an Act) are left alone.
  LEGAL-LAW       A governing law clause names a law, with no placeholder left, and a Cover Page
                  row for the law or the courts is filled in; it is the parties' choice and the
                  library never fills it in.
  LEGAL-SIGN      A signature block for every party.
  LEGAL-NDA       A confidentiality agreement carries the elements of the NDA review in Open Legal
                  Products' mike-workflows (MIT): direction, the definition of Confidential
                  Information, the obligations, the four standard carve-outs, permitted disclosures,
                  term, return or destruction, remedies, governing law and courts.
  LEGAL-DPA       A data processing agreement carries what GDPR Article 28(3) requires.

Review (a report on the other side's paper, from review_create.py and its review JSON):
  LEGAL-VERDICT   Every item of the checklist has exactly one verdict, Finding, Acceptable, Not
                  applicable or Missing information (the coverage ledger of mike-workflows'
                  dpa-review, MIT), every Finding says whether it is a legal issue or a commercial
                  preference, and the report shows each item with its verdict.
  LEGAL-QUOTE     Every Finding quotes the reviewed document, and every quote is found in that
                  document's text (Word, PDF or plain text) and in the report.
  LEGAL-WORDING   The report, outside its quotes, gives no verdict on the agreement as a whole: not
                  compliant, lawful, valid, approved, nor safe or ready to sign.

Redline (the other side's Word file with our edits as tracked changes, from redline_create.py):
  LEGAL-REDLINE   The file carries tracked changes (w:ins, w:del), each with an author and a date,
                  and every edit in the redline JSON is there.
  LEGAL-ORIGINAL  With every change rejected the text is the original's, paragraph by paragraph,
                  and every other part of the file is the original's byte for byte.

check(rule_id, path, case, stage) -> (passed, evidence); passed is None when the rule does not apply.
"""
import html
import json
import re
import unicodedata
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHECKLISTS = HERE.parent / "contract-drafting" / "checklists"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

PLACEHOLDER = re.compile(r"\[(●|•|\.\.\.|insert[^\]]*|fill in[^\]]*|x+|tbd|tbc)\]|\bTBD\b|\bTBC\b|_{4,}|\bXX+\b|<[^>]+>", re.I)
TERM_DEF = re.compile(r"[\"“]([A-Z][\w'’ -]{1,60}?)[\"”]\s+(means|shall mean|has the meaning|avser|betyder)")
XREF = re.compile(r"\b(clause|section|paragraph|punkt|avsnitt)s?\s+(\d+(?:\.\d+)*)", re.I)
HEADING = re.compile(r"^(\d+(?:\.\d+)*)\.?\s+\S")
CHOICE_ROWS = ("governing law", "jurisdiction", "chosen courts", "governing member state", "tillämplig lag", "domstol")
NDA = [  # element, words that show it is there (English and Swedish)
    ("direction (mutual or one-way, with the disclosing and receiving party)", ("mutual", "each party", "disclosing party", "ömsesidig", "utlämnande part")),
    ("the definition of Confidential Information", ("confidential information\" means", "confidential information” means", "(“confidential information”)", "(\"confidential information\")", "konfidentiell information\" avser", "konfidentiell information” avser")),
    ("the receiving party's obligations", ("shall not disclose", "not disclose confidential information", "keep confidential", "use the confidential information only", "solely for the", "inte röja", "hålla konfidentiell")),
    ("carve-out: public", ("publicly available", "public domain", "publicly known", "allmänt känd", "offentligt tillgänglig")),
    ("carve-out: already known", ("already known", "already in its possession", "lawfully in its possession", "rightfully knew", "knew or possessed", "knew without", "redan känd")),
    ("carve-out: independently developed", ("independently developed", "självständigt utvecklad", "oberoende av")),
    ("carve-out: received from a third party", ("from a third party", "from someone else", "från tredje man")),
    ("permitted disclosures", ("employees", "advisers", "advisors", "professional advisers", "anställda", "rådgivare")),
    ("term and duration", ("years", "term of", "år ", "giltighetstid")),
    ("return or destruction", ("return or destroy", "return or destruction", "destroy", "återlämna", "förstöra")),
    ("remedies", ("injunct", "specific performance", "damages", "remed", "vite", "skadestånd")),
    ("governing law and courts", ("governed by", "courts", "tillämplig lag", "domstol", "skiljedom")),
]
DPA = [  # GDPR Article 28(3)
    ("the subject-matter and duration of the processing (28(3))", ("subject-matter", "subject matter", "duration")),
    ("the nature and purpose of the processing (28(3))", ("nature", "purpose")),
    ("the type of personal data (28(3))", ("types of personal data", "type of personal data", "categories of personal data")),
    ("the categories of data subjects (28(3))", ("categories of data subjects", "data subjects")),
    ("documented instructions (28(3)(a))", ("documented instructions", "processing instructions", "written instructions")),
    ("confidentiality of the persons authorised to process (28(3)(b))", None),
    ("security under Article 32 (28(3)(c))", ("article 32", "security of processing", "technical and organisational measures", "technical and organizational measures")),
    ("conditions for sub-processors (28(3)(d))", ("sub-processor", "subprocessor", "another processor")),
    ("assistance with data subjects' rights (28(3)(e))", ("data subject", "rights")),
    ("assistance with Articles 32 to 36 (28(3)(f))", ("articles 32 to 36", "article 33", "article 35", "breach")),
    ("deletion or return at the end (28(3)(g))", ("delete", "return")),
    ("information and audits (28(3)(h))", ("audit", "inspection")),
]
PEOPLE_BOUND = re.compile(r"(staff|personnel|employees|persons? authori[sz]ed|authori[sz]ed persons?|anställda|personal)"
                          r".{0,160}confidential|confidential.{0,160}(staff|personnel|employees|persons? authori[sz]ed|authori[sz]ed persons?)")
VERDICTS = {"finding": "Finding", "acceptable": "Acceptable", "not applicable": "Not applicable",
            "missing information": "Missing information"}
ISSUES = ("legal", "commercial")
# A verdict on the agreement as a whole: the review never gives one. Words inside a quote are the
# other side's and are left out first.
VERDICT_WORDS = [
    r"\b(non-)?compliant\b",
    r"\blawful\b(?!\s+(instructions?|basis|bases|purposes?|processing|grounds?))",
    r"\b(is|are|looks|seems|appears)\s+(fully\s+|legally\s+)?(valid|enforceable|binding)\b",
    r"\blegally\s+(valid|sound|watertight)\b",
    r"\b(safe|fine|ok|okay|good|ready|cleared|clear)\s+to\s+(sign|be signed)\b",
    r"\bready\s+for\s+signature\b",
    r"\b(can|may|could)\s+(safely\s+)?be\s+signed\b",
    r"\bsign\s+(it|this)\s+as\s+it\s+(is|stands)\b",
    r"\bapproved\b",
    r"\bno\s+(legal\s+)?(risks?|issues|concerns)\b",
    r"\brisk[- ]free\b",
    r"\b(kan|går att)\s+(skrivas under|undertecknas)\b",
    r"\bgodkän(d|t|da)\b",
    r"\blaglig(t|a)?\b",
]


# Reading Word files.

def _xml(path, part="word/document.xml"):
    with zipfile.ZipFile(path) as z:
        return z.read(part)


def paragraphs(path):
    xml = _xml(path).decode("utf-8", "replace")
    out = []
    for p in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S):
        p = re.sub(r"<w:delText[^>]*>.*?</w:delText>", "", p, flags=re.S)
        # Decoded, so a name like "Hughes & Patel" is read as written, not as "&amp;".
        text = html.unescape(re.sub(r"<[^>]+>", "", p.replace("<w:tab/>", " ").replace("<w:br/>", " ")))
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            out.append(text)
    return out


def table_rows(path):
    """Each table row as a list of cell texts."""
    xml = _xml(path).decode("utf-8", "replace")
    rows = []
    for tr in re.findall(r"<w:tr[ >].*?</w:tr>", xml, re.S):
        cells = []
        for tc in re.findall(r"<w:tc[ >].*?</w:tc>", tr, re.S):
            text = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<w:delText[^>]*>.*?</w:delText>", "", tc, flags=re.S)))
            cells.append(re.sub(r"\s+", " ", text).strip())
        rows.append(cells)
    return rows


def views(xml_bytes):
    """The document's paragraphs as text twice: with every change accepted and with every change
    rejected. A paragraph whose mark is inserted joins the next one when changes are rejected; one
    whose mark is deleted joins the next one when they are accepted."""
    from lxml import etree
    root = etree.fromstring(xml_bytes)
    accepted, rejected = [], []
    carry_a = carry_r = ""
    for p in root.iter(W + "p"):
        a = r = ""
        for el in p.iter(W + "t", W + "delText", W + "tab", W + "br", W + "cr"):
            owner = next(el.iterancestors(W + "p"))
            if owner is not p:
                continue
            tag = el.tag[len(W):]
            text = (el.text or "") if tag in ("t", "delText") else ("\t" if tag == "tab" else "\n")
            in_ins = any(True for _ in el.iterancestors(W + "ins"))
            if tag == "delText":
                r += text
            elif in_ins:
                a += text
            else:
                a += text
                r += text
        mark = p.find(W + "pPr/" + W + "rPr")
        mark_ins = mark is not None and mark.find(W + "ins") is not None
        mark_del = mark is not None and mark.find(W + "del") is not None
        if mark_del:
            carry_a += a
        else:
            accepted.append(carry_a + a)
            carry_a = ""
        if mark_ins:
            carry_r += r
        else:
            rejected.append(carry_r + r)
            carry_r = ""
    if carry_a:
        accepted.append(carry_a)
    if carry_r:
        rejected.append(carry_r)
    return accepted, rejected


def norm(text):
    text = unicodedata.normalize("NFKC", text)
    for a, b in (("‘’‚‛′`", "'"), ("“”„‟″", '"'), ("–—‑‒−", "-")):
        for ch in a:
            text = text.replace(ch, b)
    text = text.replace("­", "").replace("‎", "").replace("​", "")
    return re.sub(r"\s+", " ", text).strip().lower()


def document_text(path):
    """The reviewed document's text, or None when it cannot be read here."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".docx":
        accepted, _ = views(_xml(path))
        parts = [accepted]
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if re.match(r"word/(header|footer|footnotes|endnotes)\d*\.xml$", name):
                    parts.append(views(z.read(name))[0])
        return "\n".join("\n".join(p) for p in parts)
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
            return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
        except Exception:
            pass
        try:
            import pdfplumber
            with pdfplumber.open(str(path)) as pdf:
                return "\n".join(page.extract_text() or "" for page in pdf.pages)
        except Exception:
            pass
        import shutil
        import subprocess
        if shutil.which("pdftotext"):
            return subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True).stdout
        return None
    if suffix in (".txt", ".md"):
        return path.read_text(errors="replace")
    return None


def quote_found(quote, haystack):
    """A quote is found when each piece between ellipses appears, in order."""
    pos = 0
    pieces = [norm(p) for p in re.split(r"\.\.\.|…|\[\.\.\.\]", quote) if norm(p)]
    if not pieces:
        return False
    for piece in pieces:
        at = haystack.find(piece, pos)
        if at < 0:
            return False
        pos = at + len(piece)
    return True


# What sits beside the output.

def jsons_beside(path):
    for p in sorted(Path(path).parent.glob("*.json")):
        try:
            data = json.loads(p.read_text())
        except (ValueError, OSError):
            continue
        if isinstance(data, dict):
            yield p, data


def spec_beside(path):
    for _, data in jsons_beside(path):
        if isinstance(data.get("parties"), list) and (data.get("clauses") or data.get("standard")):
            return data
    return None


def review_beside(path):
    """(json path, review) for the report at path."""
    found = [(p, d) for p, d in jsons_beside(path) if "checklist" in d and isinstance(d.get("items"), list)]
    for p, d in found:
        if d.get("report") and Path(d["report"]).name == Path(path).name:
            return p, d
    return found[0] if len(found) == 1 else (None, None)


def redline_beside(path):
    found = [(p, d) for p, d in jsons_beside(path) if d.get("source") and isinstance(d.get("edits"), list)]
    for p, d in found:
        if d.get("output") and Path(d["output"]).name == Path(path).name:
            return p, d
    return found[0] if len(found) == 1 else (None, None)


def output_kind(path):
    try:
        core = _xml(path, "docProps/core.xml").decode("utf-8", "replace")
    except KeyError:
        core = ""
    if re.search(r"<cp:category>\s*contract review\s*</cp:category>", core, re.I):
        return "review"
    if re.search(rb"<w:(ins|del) ", _xml(path)):
        return "redline"
    p, d = redline_beside(path)
    if d and d.get("output") and Path(d["output"]).name == Path(path).name:
        return "redline"
    return "agreement"


def kind_of(spec, flat):
    if spec and spec.get("kind"):
        return spec["kind"]
    if spec and spec.get("standard"):
        for k in ("nda", "dpa", "csa"):
            if k in spec["standard"]:
                return k
    if "data processing" in flat or "personuppgiftsbiträdesavtal" in flat:
        return "dpa"
    if "confidential" in flat and ("non-disclosure" in flat or "confidentiality agreement" in flat) or "sekretessavtal" in flat:
        return "nda"
    return "agreement"


def missing(elements, flat):
    gone = []
    for name, words in elements:
        if words is None:
            if not PEOPLE_BOUND.search(flat):
                gone.append(name)
        elif not any(w in flat for w in words):
            gone.append(name)
    return gone


def load_checklist(name):
    path = CHECKLISTS / ("%s.json" % name)
    if not path.is_file():
        return None
    return json.loads(path.read_text())


def finding_quotes(item):
    q = item.get("quotes") if item.get("quotes") is not None else item.get("quote")
    if isinstance(q, str):
        q = [q]
    return [x for x in (q or []) if str(x).strip()]


# The rules.

def check_review(rule_id, path):
    jpath, review = review_beside(path)
    if not review:
        return False, "no review JSON beside the report; write one and build the report with review_create.py"
    checklist = load_checklist(review.get("checklist", ""))
    if checklist is None:
        return False, "the review names no checklist the pack has (%r); use nda or dpa" % review.get("checklist")
    items = {}
    dupes = []
    for it in review["items"]:
        if it.get("id") in items:
            dupes.append(it.get("id"))
        items[it.get("id")] = it
    report_paras = paragraphs(path)
    report_flat = norm("\n".join(report_paras))

    if rule_id == "LEGAL-VERDICT":
        bad = []
        wanted = [c["id"] for c in checklist["items"]]
        for c in checklist["items"]:
            it = items.get(c["id"])
            if not it:
                bad.append("%s has no verdict" % c["title"])
                continue
            v = VERDICTS.get(str(it.get("verdict", "")).strip().lower())
            if not v:
                bad.append("%s: %r is not one of Finding, Acceptable, Not applicable, Missing information"
                           % (c["title"], it.get("verdict")))
                continue
            if v == "Finding" and str(it.get("issue", "")).lower() not in ISSUES:
                bad.append("%s: say whether the finding is a legal issue or a commercial preference" % c["title"])
            if v in ("Not applicable", "Missing information") and not str(it.get("note", "")).strip():
                bad.append("%s: %s needs a note saying %s" % (c["title"], v,
                           "why" if v == "Not applicable" else "what to ask for"))
        bad += ["%s is not an item of the %s" % (i, checklist["title"]) for i in items if i not in wanted]
        bad += ["%s has more than one verdict" % d for d in dupes]
        rows = table_rows(path)
        for c in checklist["items"]:
            it = items.get(c["id"])
            v = VERDICTS.get(str((it or {}).get("verdict", "")).strip().lower())
            if v and not any(r and norm(r[0]) == norm(c["title"]) and any(norm(x) == norm(v) for x in r[1:])
                             for r in rows):
                bad.append("the report shows no row for %s with its verdict; rebuild it with review_create.py" % c["title"])
        if bad:
            return False, "; ".join(bad[:4]) + ("; and %d more" % (len(bad) - 4) if len(bad) > 4 else "")
        counts = {}
        for it in items.values():
            v = VERDICTS[str(it["verdict"]).strip().lower()]
            counts[v] = counts.get(v, 0) + 1
        return True, "all %d checklist items have one verdict (%s)" % (
            len(wanted), ", ".join("%d %s" % (n, v) for v, n in sorted(counts.items())))

    if rule_id == "LEGAL-QUOTE":
        doc = review.get("document")
        if not doc:
            return False, "the review JSON names no document; give the reviewed file as \"document\""
        dpath = (jpath.parent / doc) if not Path(doc).is_absolute() else Path(doc)
        if not dpath.is_file():
            return False, "the reviewed document %s is not beside the review; quotes are checked against it" % doc
        text = document_text(dpath)
        if text is None:
            return False, "could not read the text of %s to compare the quotes" % dpath.name
        hay = norm(text)
        bad, n = [], 0
        for it in review["items"]:
            v = VERDICTS.get(str(it.get("verdict", "")).strip().lower())
            quotes = finding_quotes(it)
            if v == "Finding" and not quotes:
                bad.append("the finding on %s quotes nothing from the document" % it.get("id"))
            for q in quotes:
                n += 1
                if not quote_found(q, hay):
                    bad.append("%s: %r is not in %s" % (it.get("id"), q[:70], dpath.name))
                elif not quote_found(q, report_flat):
                    bad.append("%s: the quote %r is not in the report" % (it.get("id"), q[:60]))
        if bad:
            return False, "; ".join(bad[:3]) + ("; and %d more" % (len(bad) - 3) if len(bad) > 3 else "")
        return True, "all %d quotes are found word for word in %s" % (n, dpath.name)

    if rule_id == "LEGAL-WORDING":
        text = report_flat
        for it in review["items"]:
            for q in finding_quotes(it):
                text = text.replace(norm(q), " ")
        hits = []
        for pat in VERDICT_WORDS:
            m = re.search(pat, text, re.I)
            if m:
                hits.append(m.group(0))
        if hits:
            return False, ("the report gives a verdict on the agreement (%s); say what was found against which "
                           "item, never that it is compliant, lawful or ready to sign" % ", ".join(repr(h) for h in hits[:4]))
        return True, "no verdict on the agreement as a whole; the report names findings only"
    return None, "unknown rule"


def check_redline(rule_id, path):
    from lxml import etree
    body = _xml(path)
    root = etree.fromstring(body)
    marks = list(root.iter(W + "ins", W + "del"))
    spath, spec = redline_beside(path)
    if rule_id == "LEGAL-REDLINE":
        if not marks:
            return False, "no tracked changes: the edits must be Word revisions (w:ins, w:del), not a rewritten copy; use redline_create.py"
        bad = []
        for m in marks:
            if not (m.get(W + "author") or "").strip():
                bad.append("a change has no author")
            if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?(Z|[+-]\d{2}:\d{2})?$", m.get(W + "date") or ""):
                bad.append("a change has no date")
        if spec:
            accepted, rejected = views(body)
            acc, rej = norm("\n".join(accepted)), norm("\n".join(rejected))
            ins_text = norm("".join("".join(t.text or "" for t in m.iter(W + "t")) for m in root.iter(W + "ins")))
            del_text = norm("".join("".join(t.text or "" for t in m.iter(W + "delText")) for m in root.iter(W + "del")))
            for e in spec["edits"]:
                new = e.get("replace", e.get("insert", e.get("paragraph", "")))
                old = e.get("find", "")
                if new and norm(new) not in ins_text:
                    bad.append("the edit %r is not shown as an insertion" % new[:50])
                if old and e.get("replace") is not None and norm(old) not in del_text:
                    bad.append("%r is not shown as a deletion" % old[:50])
                if new and norm(new) not in acc:
                    bad.append("accepting the changes does not give %r" % new[:50])
        if bad:
            return False, "; ".join(sorted(set(bad))[:4])
        authors = sorted({m.get(W + "author") for m in marks})
        return True, "%d tracked changes by %s" % (len(marks), ", ".join(authors))
    if rule_id == "LEGAL-ORIGINAL":
        if not spec:
            return None, "no redline JSON beside the file names the original"
        src = spath.parent / spec["source"]
        if not src.is_file():
            return False, "the original %s is not beside the redline" % spec["source"]
        if src.resolve() == Path(path).resolve():
            return False, "the redline overwrote the original; write it to a new file"
        _, rejected = views(body)
        original, _ = views(_xml(src))
        if rejected != original:
            for i, (a, b) in enumerate(zip(rejected, original)):
                if a != b:
                    at = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]), min(len(a), len(b)))
                    lo = max(0, at - 25)
                    return False, "outside the tracked changes paragraph %d differs from the original: %r, was %r" % (
                        i + 1, a[lo:at + 35], b[lo:at + 35])
            return False, "rejecting the changes gives %d paragraphs, the original has %d" % (len(rejected), len(original))
        allowed = {"word/document.xml", "word/comments.xml", "[Content_Types].xml", "word/_rels/document.xml.rels"}
        with zipfile.ZipFile(src) as a, zipfile.ZipFile(path) as b:
            before = {n: a.read(n) for n in a.namelist()}
            after = {n: b.read(n) for n in b.namelist()}
        changed = sorted(n for n in before if n not in allowed and before[n] != after.get(n))
        extra = sorted(n for n in after if n not in before and n not in allowed)
        if changed or extra:
            return False, "parts other than the text changed: %s" % ", ".join((changed + extra)[:4])
        return True, "with every change rejected the text is the original's (%d paragraphs), other parts untouched" % len(original)
    return None, "unknown rule"


def check(rule_id, path, case, stage):
    path = Path(path)
    if path.suffix.lower() != ".docx":
        return None, "agreements, reviews and redlines are checked as Word files"
    kind_out = output_kind(path)
    review_rules = ("LEGAL-VERDICT", "LEGAL-QUOTE", "LEGAL-WORDING")
    redline_rules = ("LEGAL-REDLINE", "LEGAL-ORIGINAL")
    if rule_id in review_rules:
        return check_review(rule_id, path) if kind_out == "review" else (None, "not a review report")
    if rule_id in redline_rules:
        return check_redline(rule_id, path) if kind_out == "redline" else (None, "not a redline")
    if kind_out != "agreement":
        return None, "a %s; the drafting rules read an agreement the pack drafts" % kind_out

    paras = paragraphs(path)
    text = "\n".join(paras)
    flat = re.sub(r"\s+", " ", text).lower()
    spec = spec_beside(path)
    kind = kind_of(spec, flat)
    if rule_id == "LEGAL-PARTIES":
        if not spec:
            return None, "no agreement spec beside the file names the parties"
        bad = []
        for p in spec["parties"]:
            for key in ("name", "registration", "address"):
                if p.get(key) and re.sub(r"\s+", " ", str(p[key])).lower() not in flat:
                    bad.append("%s's %s" % (p.get("name", "a party"), key))
                if not p.get(key):
                    bad.append("%s has no %s in the spec" % (p.get("name", "a party"), key))
        return (not bad, "every party is named with its number and address" if not bad else "missing: " + ", ".join(bad[:4]))
    if rule_id == "LEGAL-DATE":
        if spec and spec.get("effective_date"):
            return (spec["effective_date"] in text or "last signature" in text
                    or bool(re.search(r"\b\d{1,2} \w+ \d{4}\b", text)),
                    "the date it takes effect is stated")
        found = re.search(r"(effective|dated|made on|ingått den|gäller från)[^.]{0,40}(\d{4}|last signature)", flat)
        return (bool(found), "the date it takes effect is stated" if found else "no date the agreement takes effect")
    if rule_id == "LEGAL-TERMS":
        defs = TERM_DEF.findall(text)
        if not defs:
            return None, "no defined terms"
        names = [d[0].strip() for d in defs]
        bad = ["%r is defined %d times" % (n, names.count(n)) for n in sorted(set(names)) if names.count(n) > 1]
        for n in sorted(set(names)):
            stem = re.escape(n[:-1]) + "(?:y|ies)" if n.endswith("y") else re.escape(n) + "(?:s|es|’s|'s)?"
            if len(re.findall(r"\b%s\b" % stem, text)) < 2:
                bad.append("%r is defined but never used" % n)
        return (not bad, "; ".join(bad[:3]) or "%d defined terms, each defined once and used" % len(set(names)))
    if rule_id == "LEGAL-XREF":
        numbers = {m.group(1) for p in paras for m in [HEADING.match(p)] if m}
        refs = []
        for p in paras:
            for m in XREF.finditer(p):
                after = p[m.end():m.end() + 60]
                before = p[max(0, m.start() - 12):m.start()]
                if re.match(r"^[\w().‎-]*\s+of\s+(the\s+)?(?!this\b)[A-Z]", after):
                    continue          # Section 19 of the UK Addendum, Clause 8.5 of the EEA SCCs
                if re.search(r"\b[A-Z]{2,}\s*$", before):
                    continue          # FAR section 12.212
                refs.append((m.group(1).lower(), m.group(2)))
        if not refs:
            return None, "no cross-references"
        # The word the document uses for its own parts: from a reference to itself ("Section 3.2 of
        # this DPA", "this Section"), else the commonest word whose references resolve.
        selfref = re.search(r"\b(clause|section|paragraph|punkt|avsnitt)s?\s+[\d.]+\s+(?:\([^)]*\)\s+)?of\s+this\b"
                            r"|\bthis\s+(clause|section|paragraph|punkt|avsnitt)\b", text, re.I)
        own = {w for w, n in refs if n in numbers or n.split(".")[0] in numbers}
        if selfref:
            word = (selfref.group(1) or selfref.group(2)).lower()
        else:
            word = max(own, key=lambda w: sum(1 for x, _ in refs if x.rstrip("s") == w.rstrip("s"))) if own else None
        bad = sorted({n for w, n in refs if (word is None or w.rstrip("s") == word.rstrip("s"))
                      and n not in numbers and n.split(".")[0] not in numbers})
        return (not bad, "every cross-reference resolves" if not bad else "%s %s is referred to but does not exist"
                % ((word or "clause").rstrip("s"), ", ".join(bad)))
    if rule_id == "LEGAL-LAW":
        law = [p for p in paras if re.search(r"govern|applicable law|tillämplig lag|lag ska tillämpas", p, re.I)]
        if not law:
            return False, "no governing law clause; it is the parties' choice, ask the person"
        holes = [p for p in law if PLACEHOLDER.search(p)]
        if holes:
            return False, "the governing law clause still holds a placeholder: %r" % holes[0][:80]
        cover_law, left = [], []
        # A choice the spec declares unknown stays open for the parties, named in the reply (timed run c09,
        # 2026-10-25); one left empty without that is a fail.
        unknown = set((spec or {}).get("unknown") or [])
        for row in table_rows(path):
            if len(row) >= 2 and any(norm(row[0]).startswith(c) for c in CHOICE_ROWS):
                value = row[1].strip()
                key = "governing_law" if re.match(r"(governing law|tillämplig lag)", norm(row[0])) else "courts"
                if not value and key in unknown:
                    left.append(row[0].strip().split("\n")[0])
                    continue
                if not value or PLACEHOLDER.search(value):
                    return False, "the Cover Page row %r is empty or a placeholder; it is the parties' choice, ask the person" % row[0][:40]
                if re.match(r"(governing law|governing member state|tillämplig lag)", norm(row[0])):
                    cover_law.append(value)
        named = cover_law + [p for p in law if re.search(r"laws? of [A-Z]|svensk lag|[A-Z]\w+ law\b|lagen i|recht", p)]
        if left and (named or "governing_law" in unknown):
            return True, ("WARN the Cover Page leaves %s open for the parties to agree, as the person did not say; "
                          "name it in the reply as theirs to fill in before signing" % " and ".join(left))
        return (bool(named), "the governing law is named" if named else "the governing law clause names no law")
    if rule_id == "LEGAL-SIGN":
        names = [p["name"] for p in spec["parties"]] if spec else []
        marks = [i for i, p in enumerate(paras) if re.search(r"signature|signed|underskrift|namnteckning", p, re.I)]
        if not marks:
            return False, "no signature block"
        # A signature block: a mention of a signature with every party's name close after it.
        windows = ["\n".join(paras[max(0, i - 12):i + 60]).lower() for i in marks]
        window = next((w for w in windows if all(n.lower() in w for n in names)), windows[-1])
        bad = [n for n in names if n.lower() not in window]
        return (not bad, "a signature block for every party" if not bad else "no signature block for %s" % ", ".join(bad))
    if rule_id == "LEGAL-NDA":
        if kind != "nda":
            return None, "not a confidentiality agreement"
        gone = missing(NDA, flat)
        return (not gone, "the NDA elements are there" if not gone else "missing: " + "; ".join(gone))
    if rule_id == "LEGAL-DPA":
        if kind != "dpa":
            return None, "not a data processing agreement"
        gone = missing(DPA, flat)
        return (not gone, "everything GDPR Article 28(3) requires is there" if not gone else "missing: " + "; ".join(gone))
    return None, "unknown rule"
