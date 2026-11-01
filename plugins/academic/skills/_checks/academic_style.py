#!/usr/bin/env python3
"""Academic style rules read off the rendered file, not off prose.

check(rule_id, path, case, stage) -> (passed, evidence). Standard library only,
pdffonts from poppler for the PDF rule.

Rules:
  PAPER-FONTS        the PDF embeds the template's Times family for text, no
                     Computer Modern or Latin Modern text faces
  PAPER-CITE-COVER   every \\bibitem key in the .tex is cited by a \\cite
  PAPER-REF-RECORD   every published paper in the list carries a DOI, arXiv id or URL, and when the
                     registries answer, every surname it lists is among its record's authors
  PAPER-CLAIM-CITE   a sentence claiming something of the field or of others' work cites a source in it
  APA-NO-INTRO       the paper has no heading or paragraph named Introduction
  APA-REFS-NEW-PAGE  the reference list starts on a page of its own
  APA-REF-CITED      every listed reference is cited in the text and every
                     in-text citation has an entry

A reference list handed back on its own (above it a title at most, no text) has nothing to cite it:
APA-REF-CITED, VANC-ORDER, VANC-MARKS and VANC-CITED are not measured on it, and it may start on the
first page. The list's own form is still read.

Vancouver (numbered citations, medicine and health sciences; measured only on a numbered list
in Vancouver form, and the APA rules stand aside on one):
  VANC-ORDER         sources are numbered in the order the text first cites them
  VANC-MARKS         one form of in-text number throughout: [1], (1) or superscript
  VANC-LIST          the list runs 1, 2, 3 in number order, one entry per number
  VANC-CITED         every entry is cited and every cited number has an entry
  VANC-ONCE          a source cited again keeps its first number; it is never listed twice
  VANC-AUTHORS       Surname and initials without full stops, six authors at most then et al.
  VANC-JOURNAL       no full stops inside an abbreviated journal title
  VANC-DATE          a journal entry reads year;volume(issue):pages, no vol., no pp., no (year)
  VANC-ONLINE        an online source gives Available from: its URL and [cited date]
"""


import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

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


W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
CM_FACES = ("CMR", "CMMI", "CMSY", "CMEX", "LMRoman", "LMSans", "LMMono", "Computer Modern")


def _docx_text(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml")
    root = ET.fromstring(xml)
    paras = []
    for p in root.iter(W + "p"):
        texts = [t.text or "" for t in p.iter(W + "t")]
        breaks = p.findall(".//" + W + "br")
        page_break = any(b.get(W + "type") == "page" for b in breaks)
        ppr = p.find(W + "pPr")
        if ppr is not None and ppr.find(W + "pageBreakBefore") is not None:
            page_break = True
        style = ""
        if ppr is not None:
            ps = ppr.find(W + "pStyle")
            if ps is not None:
                style = ps.get(W + "val") or ""
        bold = any(r.find(W + "rPr") is not None and r.find(W + "rPr").find(W + "b") is not None
                   for r in p.iter(W + "r"))
        paras.append({"text": "".join(texts).strip(), "page_break": page_break, "style": style, "bold": bold})
    return paras


def _pdf_fonts(path):
    out = subprocess.run(["pdffonts", str(path)], capture_output=True, text=True).stdout
    return [line.split()[0] for line in out.splitlines()[2:] if line.strip()]


def reference_entries(path):
    """The body text and the reference list, split the way every reference rule reads them."""
    paras = _docx_text(path)
    idx = next((i for i, p in enumerate(paras) if p["text"].lower().startswith("references")), None)
    if idx is None:
        return None, None
    body = " ".join(p["text"] for p in paras[:idx])
    refs = [p["text"] for p in paras[idx + 1:] if p["text"]]
    # A note about the list is not an entry. When the notes carry no source, the honest answer is a
    # list that says so, and the rules are about entries.
    refs = [r for r in refs if not (r.startswith("[") and r.rstrip().endswith("]"))]
    return body, refs


# What a list on its own is measured as: no text cites it, so no rule about citing it applies.
ON_ITS_OWN = "not measured: a reference list on its own, with no text above it to cite it"


def on_its_own(path):
    """A reference list handed back as the whole document: a title at most above it, no citation."""
    if Path(path).suffix.lower() != ".docx":
        return False
    body, refs = reference_entries(path)
    return bool(refs) and len(re.findall(r"[^\W\d_]{2,}", body)) <= 12 and not CITATION.search(body) \
        and not re.search(r"\[\d+(?:[,\u2013-]\d+)*\]", body)


def uncited_entries(path):
    """The listed entries nothing in the text cites. repair_refs.py removes exactly these; on a list on its own
    there is no text, so none."""
    body, refs = reference_entries(path)
    if refs is None or on_its_own(path):
        return []
    body = body.replace("et al.", "et al")     # "(Devlin et al., 2019)": the full stop is not the end of a cite
    out = []
    for ref in refs:
        m = re.match(r"([A-Z][A-Za-z'\-]+)", ref)
        y = re.search(r"\((\d{4})\)", ref)
        if not m or not y or not re.search(r"%s[^.]{0,40}%s" % (re.escape(m.group(1)), y.group(1)), body):
            out.append(ref)
    return out


CITATION = re.compile(r"\([A-Z][A-Za-z'\-]+(?: (?:&|and|et al\.)[^,()]*)?, \d{4}[a-z]?\)")


def is_academic(paras):
    """An APA report has a reference list or (Author, year) citations. A Word file with neither, an
    invoice or a letter made with the docx skill, is not one, and its rules are not measured on it."""
    if any(p["text"].lower().startswith("references") for p in paras):
        return True
    return any(CITATION.search(p["text"]) for p in paras)


# ---------------------------------------------------------------------------------------------------
# Vancouver: numbered citations for medicine and health sciences.
#
# Sources, restated in our own words: Citing Medicine, 2nd edition (National Library of Medicine,
# Patrias and Wendling, 2007-, NCBI Bookshelf NBK7256), a work of the US Government in the public
# domain: chapter 1 (journals; 1B for articles on the Internet) and chapter 2 (books); NLM's
# "Samples of Formatted References for Authors of Journal Articles" (the six-author limit, the
# year;volume(issue):pages form); the ICMJE Recommendations (updated January 2026) section IV.A.3.g
# (number in order of first mention, abbreviate journal titles, follow Citing Medicine), cited only.
# The CSL vancouver.csl style was read to learn the forms; nothing of it is copied here.
#
# The rules say which rule a list breaks. They never say a paper is correct or ready to submit.
# ---------------------------------------------------------------------------------------------------

REF_HEADINGS = ("references", "reference list", "bibliography", "literature cited")
LEAD_NUMBER = re.compile(r"^\s*(?:\[(\d{1,3})\]|(\d{1,3})[.)]|(\d{1,3})(?=\s+[A-Z]))\s*")
NUM_GROUP = r"\d{1,3}(?:\s*[-–—,]\s*\d{1,3})*"
BRACKET_MARK = re.compile(r"\[(%s)\]" % NUM_GROUP)
PAREN_MARK = re.compile(r"(?<![\w(])\((%s)\)" % NUM_GROUP)
SUP_MARK = re.compile(r"⟨(%s)⟩" % NUM_GROUP)      # superscript runs, marked by the reader below
MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
YEAR_SEMI = re.compile(r"(?<!updated )(?<!cited )\b(\d{4})(?: %s(?:-%s)?(?: \d{1,2})?)?(?: \[(?:cited|updated)[^\]]*\])?;" % (MONTH, MONTH))
PARTICLE = r"(?:(?:van|von|de|der|den|du|da|di|del|della|le|la|ten|ter|St)\s)"
SURNAME = r"%s*[A-ZÀ-Þ][\wÀ-ɏ'’\-]*(?:\s%s*[A-ZÀ-Þ][\wÀ-ɏ'’\-]*[a-zß-ÿ][\wÀ-ɏ'’\-]*)*" % (PARTICLE, PARTICLE)
INITIALS = r"[A-Z](?:\.?\s?[A-Z]){0,3}\.?"
NAME = re.compile(r"(%s)\s(%s)(?=,\s|\.\s|\.$|;\s|\s[A-Z][a-z])" % (SURNAME, INITIALS))
APA_NAME = re.compile(r"^[A-Z][\w'’\-]+,\s(?:[A-Z]\.\s?){1,3}(?:,|\s&|\s\()")
IEEE_ENTRY = re.compile(r"^(?:[A-Z]\.\s?(?:-?[A-Z]\.\s?)*\s?[A-Z][\w'\-]+(?:,|\sand\s|\s?et al))|[\"“][^\"”]{8,}[,.][\"”]")
STOP_ABBREV = re.compile(r"((?:\b[A-Z][a-z]{0,7}\.\s){2,})(?:\[Internet\]\.\s)?\d{4}")
URL = re.compile(r"(?:https?://|www\.)\S+")
DOI_URL = re.compile(r"https?://(?:dx\.)?doi\.org/\S+")


def _vanc_paras(path):
    """Paragraphs as the Vancouver rules read them: superscript digits wrapped in angle marks, and
    whether Word numbers the paragraph itself (a numbered list carries no number in its text)."""
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
        try:
            styles = ET.fromstring(z.read("word/styles.xml"))
        except KeyError:
            styles = None
    # A list style (List Number and the like) numbers its paragraphs without a numPr of their own.
    numbered_styles = set()
    if styles is not None:
        for st in styles.iter(W + "style"):
            ppr = st.find(W + "pPr")
            if ppr is not None and ppr.find(W + "numPr") is not None:
                numbered_styles.add(st.get(W + "styleId"))
    out = []
    for p in root.iter(W + "p"):
        parts = []
        for r in p.iter(W + "r"):
            text = "".join(t.text or "" for t in r.iter(W + "t"))
            rpr = r.find(W + "rPr")
            va = rpr.find(W + "vertAlign") if rpr is not None else None
            if va is not None and va.get(W + "val") == "superscript" and re.fullmatch(r"\s*%s\s*" % NUM_GROUP, text):
                parts.append("⟨%s⟩" % text.strip())
            else:
                parts.append(text)
        ppr = p.find(W + "pPr")
        numbered = ppr is not None and ppr.find(W + "numPr") is not None
        if not numbered and ppr is not None and ppr.find(W + "pStyle") is not None:
            numbered = ppr.find(W + "pStyle").get(W + "val") in numbered_styles
        out.append({"text": "".join(parts).strip(), "numbered": numbered})
    # Two superscript runs side by side are one mark.
    for para in out:
        para["text"] = para["text"].replace("⟩⟨", ",")
    return out


def _expand(group):
    nums = []
    for piece in re.split(r"\s*,\s*", group):
        bounds = re.split(r"\s*[-–—]\s*", piece)
        if len(bounds) == 2 and bounds[0].isdigit() and bounds[1].isdigit() and int(bounds[0]) <= int(bounds[1]):
            nums.extend(range(int(bounds[0]), int(bounds[1]) + 1))
        elif bounds[0].isdigit():
            nums.append(int(bounds[0]))
    return nums


def vancouver_parts(path):
    """(body marks, entries) or None when the file has no numbered reference list.

    marks: [(form, [numbers])] in reading order, form one of brackets, parentheses, superscript.
    entries: [(number or None, text)] in list order; Word's own numbering stands in for a missing number.
    """
    paras = _vanc_paras(path)
    idx = next((i for i, p in enumerate(paras)
                if p["text"].lower().rstrip(":") in REF_HEADINGS), None)
    if idx is None:
        return None
    entries = []
    auto = 0
    for p in paras[idx + 1:]:
        text = p["text"].replace("⟨", "").replace("⟩", "")
        if not text:
            continue
        m = LEAD_NUMBER.match(text)
        if m:
            entries.append((int(next(g for g in m.groups() if g)), text[m.end():].strip()))
        elif p["numbered"]:
            auto += 1
            entries.append((auto, text))
        else:
            entries.append((None, text))
    # Paragraphs after the list (an appendix heading, a table) are not entries: stop at the first
    # unnumbered paragraph once numbered ones began.
    trimmed = []
    for number, text in entries:
        if number is None and trimmed:
            break
        if number is not None:
            trimmed.append((number, text))
    if not trimmed:
        return None
    marks = []
    for p in paras[:idx]:
        text = p["text"]
        found = []
        for form, rx in (("brackets", BRACKET_MARK), ("parentheses", PAREN_MARK), ("superscript", SUP_MARK)):
            for m in rx.finditer(text):
                nums = _expand(m.group(1))
                # A bracketed or parenthesised number past the list's end is a count or a year, not a citation.
                if form != "superscript" and any(n > max(n2 for n2, _ in trimmed) + 20 for n in nums):
                    continue
                found.append((m.start(), form, nums))
        marks.extend((form, nums) for _, form, nums in sorted(found))
    return marks, trimmed


def is_vancouver(path):
    """A numbered reference list in Vancouver form, not IEEE (initials first, titles in quotation marks)."""
    parts = vancouver_parts(path)
    if not parts:
        return False
    entries = parts[1]
    ieee = sum(1 for _, text in entries if IEEE_ENTRY.search(text))
    # And a positive sign of Vancouver on at least half the entries: Surname AB authors or a
    # year;volume date. A numbered draft in another form (an APA conversion not yet done) stays
    # with the APA rules, which fail it.
    signs = sum(1 for _, text in entries
                if (NAME.match(text) and not APA_NAME.match(text)) or YEAR_SEMI.search(text))
    return ieee * 2 < len(entries) and signs * 2 >= len(entries)


def _authors(text):
    """The author block of one entry: (names, et_al, problems). names is None for a group or no author."""
    problems = []
    if APA_NAME.match(text):
        return [], False, ["'%s' is written Surname, A. (APA); Vancouver writes Surname A" % text[:30]]
    names, pos, et_al = [], 0, False
    while True:
        rest = text[pos:]
        if rest.startswith("et al"):
            et_al = True
            break
        m = NAME.match(rest)
        if not m:
            break
        surname, initials = m.group(1), m.group(2)
        pos += m.end()
        sep = text[pos:pos + 2]
        # The full stop that ends the author block is not part of the last name's initials.
        shown = initials
        if initials.endswith(".") and sep != ", " and not text[pos:pos + 1] == ",":
            initials = initials[:-1]
        if "." in initials:
            problems.append("'%s %s' has full stops in the initials; write %s %s"
                            % (surname, shown.strip(), surname, initials.replace(".", "").replace(" ", "")))
        elif " " in initials.strip():
            problems.append("'%s %s' has spaces between the initials" % (surname, initials.strip()))
        names.append(surname)
        if sep == ", ":
            pos += 2
            continue
        break
    if not names:
        return None, et_al, problems
    return names, et_al, problems


def _some(problems, n=4):
    more = len(problems) - n
    return "; ".join(problems[:n]) + ("; and %d more" % more if more > 0 else "")


def _vanc_rule(rule_id, path):
    parts = vancouver_parts(path)
    if not parts or not is_vancouver(path):
        return False, "not measured: no numbered reference list in Vancouver form"
    marks, entries = parts
    listed = [n for n, _ in entries]

    if rule_id == "VANC-ORDER":
        if not marks:
            return False, "no numbered citation in the text"
        first = []
        for _, nums in marks:
            for n in nums:
                if n not in first:
                    first.append(n)
        due = list(range(1, len(first) + 1))
        if first == due:
            return True, "numbers are cited in order of first mention"
        at = next(i for i, (a, b) in enumerate(zip(first, due)) if a != b)
        return False, ("first citations run %s; [%d] comes where [%d] is due: number the sources in the "
                       "order the text first cites them" % (", ".join(map(str, first[:10])), first[at], due[at]))

    if rule_id == "VANC-MARKS":
        forms = {}
        for form, _ in marks:
            forms[form] = forms.get(form, 0) + 1
        if not forms:
            return False, "no numbered citation in the text"
        if len(forms) > 1:
            return False, ("in-text numbers mix forms (%s): use one form throughout"
                           % ", ".join("%s %d" % kv for kv in sorted(forms.items())))
        return True, "every in-text number uses %s" % next(iter(forms))

    if rule_id == "VANC-LIST":
        problems = []
        dupes = sorted({n for n in listed if listed.count(n) > 1})
        if dupes:
            problems.append("number %s heads more than one entry" % ", ".join(map(str, dupes)))
        if listed != sorted(listed):
            problems.append("the list is not in number order (%s)" % ", ".join(map(str, listed[:8])))
        gaps = sorted(set(range(1, max(listed) + 1)) - set(listed))
        if gaps:
            problems.append("no entry numbered %s" % ", ".join(map(str, gaps[:6])))
        return (not problems, "one entry per number, 1 to %d in order" % len(listed) if not problems
                else "; ".join(problems))

    if rule_id == "VANC-CITED":
        cited = {n for _, nums in marks for n in nums}
        uncited = [n for n in listed if n not in cited]
        unlisted = sorted(n for n in cited if n not in listed)
        problems = []
        if uncited:
            problems.append("listed but never cited: %s" % ", ".join("[%d]" % n for n in uncited[:6]))
        if unlisted:
            problems.append("cited but not in the list: %s" % ", ".join("[%d]" % n for n in unlisted[:6]))
        return (not problems, "every entry is cited and every cited number is listed" if not problems
                else "; ".join(problems))

    if rule_id == "VANC-ONCE":
        def key(text):
            head = re.split(r"\.\s(?=[A-Z0-9])", text, maxsplit=2)
            return re.sub(r"\W+", " ", " ".join(head[:2]).lower()).strip()
        seen, problems = {}, []
        for n, text in entries:
            k = key(text)
            if k in seen and len(k) > 12:
                problems.append("[%d] and [%d] are the same source" % (seen[k], n))
            seen.setdefault(k, n)
        return (not problems, "each source has one number" if not problems
                else _some(problems) + ": a source cited again keeps its first number")

    if rule_id == "VANC-AUTHORS":
        problems = []
        for n, text in entries:
            names, et_al, issues = _authors(text)
            problems.extend("[%d] %s" % (n, i) for i in issues)
            if names is None:
                continue
            if len(names) > 6:
                problems.append("[%d] names %d authors: list the first six, then et al." % (n, len(names)))
            elif et_al and len(names) < 6:
                problems.append("[%d] has et al. after %d author%s: list every author up to six"
                                % (n, len(names), "" if len(names) == 1 else "s"))
        return (not problems, "authors are Surname and initials, at most six then et al." if not problems
                else _some(problems))

    if rule_id == "VANC-JOURNAL":
        problems = []
        for n, text in entries:
            m = STOP_ABBREV.search(text)
            if m and YEAR_SEMI.search(text):
                problems.append("[%d] '%s' has full stops in the abbreviated journal title" % (n, m.group(1).strip()))
        return (not problems, "no full stops inside an abbreviated journal title" if not problems
                else _some(problems) + " (NLM abbreviations carry none: N Engl J Med)")

    if rule_id == "VANC-DATE":
        problems = []
        for n, text in entries:
            if re.search(r"\(\d{4}[a-z]?\)", text):
                problems.append("[%d] has the year in parentheses (APA form)" % n)
                continue
            if re.search(r"\b(?:vol|pp|no)\.\s?\d", text, re.I):
                problems.append("[%d] uses vol., no. or pp.; write year;volume(issue):pages" % n)
                continue
            m = YEAR_SEMI.search(text)
            if not m:
                continue
            after = text[m.end():]
            if not re.match(r"(?:\d+[A-Za-z]?(?:\s(?:Suppl|Pt)\s?\d+)?(?:\([^)\s][^)]*\))?|\([^)\s][^)]*\)):"
                            r"(?:\[?[A-Za-z]{0,2}\d+[A-Za-z]?(?:-[A-Za-z]{0,2}\d+[A-Za-z]?)?\]?|\[about [^\]]+\])",
                            after):
                problems.append("[%d] '%s' is not year;volume(issue):pages" % (n, (text[m.start():m.end()] + after)[:28]))
        return (not problems, "journal entries read year;volume(issue):pages" if not problems
                else _some(problems))

    if rule_id == "VANC-ONLINE":
        problems = []
        for n, text in entries:
            urls = [u for u in URL.findall(text) if not DOI_URL.match(u)]
            internet = "[Internet]" in text
            cited = re.search(r"(?:\[|;\s)(?:cited|accessed)\s[^\]]*\d{4}[^\]]*\]", text, re.I)
            if urls and not cited:
                problems.append("[%d] has a URL but no date of citation [cited YYYY Mon DD]" % n)
            if urls and "Available from:" not in text:
                problems.append("[%d] gives its URL without 'Available from:'" % n)
            if (internet or cited) and not urls and "doi" not in text.lower():
                problems.append("[%d] is an Internet source with no URL or DOI" % n)
        return (not problems, "every online source has its URL and date of citation" if not problems
                else _some(problems))

    return None, "unknown rule"


VANC_RULES = ["VANC-ORDER", "VANC-MARKS", "VANC-LIST", "VANC-CITED", "VANC-ONCE", "VANC-AUTHORS",
              "VANC-JOURNAL", "VANC-DATE", "VANC-ONLINE"]


def uncited_numbers(path):
    """The numbered entries nothing in the text cites, as (number, text)."""
    parts = vancouver_parts(path)
    if not parts:
        return []
    cited = {n for _, nums in parts[0] for n in nums}
    return [(n, t) for n, t in parts[1] if n not in cited]


PAPER_KIND = re.compile(r"\b(Proc\.|Proceedings|Conference|Conf\.|Journal|Trans\.|Transactions|Lett\.|vol\.|"
                        r"NeurIPS|ICLR|ICML|CVPR|ACL|EMNLP|AAAI|IJCAI|arXiv)", re.I)
REF_ID = re.compile(r"(10\.\d{4,9}/[^\s}\\,;]+|arXiv:\s*\d{4}\.\d{4,5}|arxiv\.org/(?:abs|pdf)/\d{4}\.\d{4,5}|"
                    r"\\url\{[^}]+\}|https?://\S+)", re.I)


def _bib_entries(tex):
    if "\\begin{thebibliography}" not in tex:
        return []
    body = tex.split("\\begin{thebibliography}", 1)[1].split("\\end{thebibliography}")[0]
    parts = re.split(r"\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}", body)
    return [(parts[i], re.sub(r"\s+", " ", parts[i + 1]).strip()) for i in range(1, len(parts) - 1, 2)]


def _fold(name):
    import unicodedata
    name = re.sub(r"\\[`'^\"~=.uvHckrb]\s*", "", name).replace("{", "").replace("}", "")
    return "".join(c for c in unicodedata.normalize("NFKD", name) if not unicodedata.combining(c)).lower()


def _ref_surnames(entry):
    """The surnames an IEEE or ACM entry lists before its title."""
    head = re.split(r"``|“|\"|\\textit|\\emph|\\textsl", entry, 1)[0]
    head = re.sub(r"\\(?:and|&)\b", ",", head)
    head = re.sub(r"\\[a-zA-Z]+\*?", " ", head).replace("~", " ")
    names = re.split(r",|\band\b|&", head)
    out = []
    for n in names:
        n = n.strip(" .:")
        if not n or re.search(r"et\.? al", n):
            continue
        words = [w for w in n.split() if not re.fullmatch(r"(?:[A-Z]\.-?)+|[A-Z]|Jr\.?|II|III", w.strip("{}"))]
        if words:
            out.append(words[-1].strip("{}."))
    return out


def _registries_answer():
    import urllib.request
    try:
        urllib.request.urlopen("https://api.crossref.org/works?rows=0", timeout=6).close()
        return True
    except Exception:
        return False


def _record(ident):
    """The registry's record for a DOI or arXiv id as {found, authors}; None when it cannot be asked."""
    here = Path(__file__).resolve().parent.parent / "literature-search"
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))
    try:
        import papers
    except ImportError:
        return None
    try:
        aid = re.search(r"\d{4}\.\d{4,5}", ident) if "arxiv" in ident.lower() else None
        if aid:
            rows = papers.arxiv_query({"id_list": aid.group(0)})
            return {"found": bool(rows), "authors": [a.split()[-1] for a in rows[0]["authors"]] if rows else []}
        return papers.verify(papers.trim_doi(ident))
    except (ConnectionError, OSError, ValueError):
        return None


#: Words that make a sentence a claim about the field or about others' work, which a reader checks against a source.
_FIELD = re.compile(
    r"\b(?:studies|research(?:ers)?|prior work|previous work|recent work|the literature|it is (?:well[- ])?known|"
    r"(?:has|have) been (?:shown|reported|observed|demonstrated)|are known to|widely|commonly|often|frequently|"
    r"typically|usually|most (?:models|systems|methods|approaches|work)|models (?:like|such as)|state[- ]of[- ]the[- ]art)\b",
    re.I)


def paper_claim_cite(path):
    """Every sentence that claims something of the field or of others' work cites a source in it."""
    tex = Path(path).read_text(errors="ignore")
    body = tex.split("\\begin{document}", 1)[-1].split("\\begin{thebibliography}", 1)[0]
    body = re.sub(r"\\begin\{abstract\}.*?\\end\{abstract\}", " ", body, flags=re.S)
    body = re.sub(r"(?<!\\)%.*", "", body)
    body = re.sub(r"\\(?:section|subsection|subsubsection|title|author|caption|label|keywords)\*?\{[^{}]*\}", " ", body)
    body = re.sub(r"\\begin\{(IEEEkeywords|keywords|table|figure|equation|align)(\*?)\}.*?\\end\{\1\2\}", " ", body,
                  flags=re.S)
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z\\])", re.sub(r"\s+", " ", body))
    bare = []
    for n, s in enumerate(sentences):
        # a topic sentence whose next sentence names the source counts as cited
        if "\\cite" in s or "\\cite" in "".join(sentences[n + 1:n + 2]) or not _FIELD.search(s) or re.search(r"\b(?:we|our|us)\b|future work|further (?:research|work|study)", s, re.I):
            continue
        bare.append(re.sub(r"\\[a-zA-Z]+\*?(?:\{([^{}]*)\})?", r"\1", s).strip()[:90])
    if bare:
        return False, ("a claim about the field with no source; cite one in the sentence or keep it to the notes: "
                       + " | ".join(bare[:3]))
    return True, "every claim about the field cites a source"


def paper_ref_record(path):
    entries = _bib_entries(Path(path).read_text(errors="ignore"))
    if not entries:
        return True, "no reference list"
    bare, wrong, looked = [], [], 0
    online = os.environ.get("PAPER_LOOKUP", "1") != "0" and _registries_answer()
    for key, text in entries:
        ids = REF_ID.findall(text)
        if not ids:
            if PAPER_KIND.search(text):
                bare.append(key)
            continue
        ident = next((i for i in ids if i.lower().startswith("10.") or "arxiv" in i.lower()), None)
        if not online or ident is None:
            continue
        rec = _record(ident)
        if rec is None:
            online = False
            continue
        looked += 1
        if not rec.get("found"):
            wrong.append("%s: %s is in no registry" % (key, ident))
            continue
        have = {_fold(a) for a in rec.get("authors") or [] if a}
        # A surname with a particle is the same author with it or without it: an entry's "R. {de Koster}" reads
        # as Koster, the record's de Koster (a real paper run, 2026-10-25).
        have |= {h.split()[-1] for h in have if h.split()}
        extra = [s for s in _ref_surnames(text) if _fold(s) not in have]
        if have and extra:
            wrong.append("%s: %s not among the record's authors (%s)"
                         % (key, ", ".join(extra), ", ".join((rec.get("authors") or [])[:7])))
    problems = []
    if bare:
        problems.append("a published paper with no DOI, arXiv id or URL: %s. Find each with literature-search "
                        "and copy its record, authors and identifier, into the entry; a paper you cannot find is "
                        "left out and named in the reply" % ", ".join(bare))
    problems += wrong
    if problems:
        return False, "; ".join(problems)
    return True, ("%d references, %d looked up, every listed author is in its record" % (len(entries), looked)
                  if online else "%d references carry their identifiers; not looked up (no answer from the registries)"
                  % len(entries))


def check(rule_id, path, case, stage):
    path = Path(path)
    if rule_id in ("APA-REF-CITED", "VANC-ORDER", "VANC-MARKS", "VANC-CITED") and on_its_own(path):
        return False, ON_ITS_OWN
    if rule_id.startswith("VANC-"):
        return _vanc_rule(rule_id, path)
    if rule_id.startswith("APA-") and path.suffix.lower() == ".docx" and is_vancouver(path):
        return False, "not measured: a numbered Vancouver list; the APA rules read an author-date list"
    if rule_id.startswith("APA-") and not is_academic(_docx_text(path)):
        return False, "not measured: no reference list and no (Author, year) citation, so not an APA report"
    if rule_id == "PAPER-FONTS":
        fonts = _pdf_fonts(path)
        if not fonts:
            return None, "pdffonts returned nothing"
        bad = [f for f in fonts if any(f.split("+")[-1].startswith(c) for c in CM_FACES)]
        text_bad = [f for f in bad if not any(f.split("+")[-1].startswith(m)
                                             for m in ("CMMI", "CMSY", "CMEX", "CMMIB", "CMBSY"))]
        times = [f for f in fonts if "Nimbus" in f or "Times" in f or "ntx" in f.lower()]
        if text_bad:
            return False, "Computer Modern or Latin Modern text faces embedded: %s" % ", ".join(text_bad[:3])
        if bad:
            return False, ("the text is the template family but the math is not: %s"
                           % ", ".join(sorted(set(bad))[:3]))
        if not times:
            return False, "no Times family font embedded: %s" % ", ".join(fonts[:3])
        return True, "Times family embedded (%s), no CM or LM text faces" % ", ".join(sorted(set(times))[:2])

    if rule_id in ("PAPER-REF-RECORD", "PAPER-CITE-COVER", "PAPER-CLAIM-CITE") and path.suffix.lower() == ".pdf":
        # packcheck hands over the PDF; these two read the source it was built from, beside it
        if not path.with_suffix(".tex").is_file():
            return False, "no %s beside %s: hand back the source with the PDF" % (path.with_suffix(".tex").name, path.name)
        path = path.with_suffix(".tex")

    if rule_id == "PAPER-REF-RECORD":
        return paper_ref_record(path)

    if rule_id == "PAPER-CLAIM-CITE":
        return paper_claim_cite(path)

    if rule_id == "PAPER-CITE-COVER":
        tex = path.read_text(errors="ignore")
        items = re.findall(r"\\bibitem\{([^}]+)\}", tex)
        cites = set()
        for group in re.findall(r"\\cite\{([^}]+)\}", tex):
            cites.update(k.strip() for k in group.split(","))
        missing = [i for i in items if i not in cites]
        return (not missing, "every reference is cited" if not missing
                else "listed but never cited: %s" % ", ".join(missing))

    if rule_id == "APA-NO-INTRO":
        paras = _docx_text(path)
        bad = [p for p in paras if p["text"].lower() == "introduction"]
        return (not bad, "no Introduction heading" if not bad
                else "the paper opens with an Introduction heading, which APA 7 does not use")

    if rule_id == "APA-REFS-NEW-PAGE":
        paras = _docx_text(path)
        idx = next((i for i, p in enumerate(paras) if p["text"].lower().startswith("references")), None)
        if idx is None:
            return False, "no reference list found"
        if paras[idx]["page_break"]:
            return True, "the reference list starts on a new page"
        if on_its_own(path):
            return True, "the reference list is the whole document, from its first page"
        prev = paras[idx - 1] if idx else None
        if prev and prev["page_break"]:
            return True, "the reference list starts on a new page"
        return False, "the reference list continues on the page before it"

    if rule_id == "APA-REF-CITED":
        body, refs = reference_entries(path)
        if refs is None:
            return False, "no reference list found"
        uncited = [ref[:40] if not (re.match(r"([A-Z][A-Za-z'\-]+)", ref)
                                    and re.search(r"\((\d{4})\)", ref))
                   else "%s %s" % (re.match(r"([A-Z][A-Za-z'\-]+)", ref).group(1),
                                   re.search(r"\((\d{4})\)", ref).group(1))
                   for ref in uncited_entries(path)]
        cites = set(re.findall(r"\(([A-Z][A-Za-z'\-]+)(?: & [A-Z][A-Za-z'\-]+)?, (\d{4})\)", body))
        listed = set()
        for ref in refs:
            m = re.match(r"([A-Z][A-Za-z'\-]+)", ref)
            y = re.search(r"\((\d{4})\)", ref)
            if m and y:
                listed.add((m.group(1), y.group(1)))
        unlisted = ["%s %s" % c for c in cites if c not in listed]
        problems = []
        if uncited:
            problems.append("listed but not cited: %s" % ", ".join(uncited[:3]))
        if unlisted:
            problems.append("cited but not listed: %s" % ", ".join(unlisted[:3]))
        return (not problems, "; ".join(problems) if problems
                else "every reference is cited and every citation is listed")
    return None, "unknown rule"


if __name__ == "__main__":
    rid, path = sys.argv[1], sys.argv[2]
    case = {}
    ok, why = check(rid, path, case, "first")
    print({"rule": rid, "passed": ok, "evidence": why})
    sys.exit(0 if ok else 1)
