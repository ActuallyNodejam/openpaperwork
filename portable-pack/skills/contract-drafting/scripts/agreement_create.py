#!/usr/bin/env python3
"""Lay out an agreement as Word from a JSON spec.

Usage: agreement_create.py spec.json agreement.docx

Two kinds of spec:

1. A Common Paper standard agreement (the usual way). The clause text is Common Paper's Standard
   Terms, word for word (CC BY 4.0, standards/*.json); the parties fill in the Cover Page.
   {
     "standard": "common-paper-mutual-nda-1.0",   # or common-paper-dpa-1.1, common-paper-csa-2.1
     "kind": "nda",                               # nda, dpa or csa
     "effective_date": "2026-11-01",
     "parties": [{"name": "...", "registration": "556677-8899", "address": "...",
                  "notice_address": "legal@... (optional, else the address)", "role": "Provider",
                  "signatory": {"name": "...", "title": "..."}}],
     "terms": {"Purpose": "...", "MNDA Term": {"years": 2}, "Term of Confidentiality": {"years": 3}},
     "governing_law": "...",                      # the parties' choice: ask, never fill it in
     "courts": "...",
     "modifications": ["Changes the parties agreed to the Standard Terms, in their own words."]
   }
   `python3 agreement_create.py --fields <standard>` lists the Cover Page fields a standard needs.

2. A plain agreement in the parties' own words: "clauses" instead of "standard".
   {"kind": "agreement", "title": "...", "effective_date": "...", "parties": [...],
    "background": ["..."], "definitions": [{"term": "...", "means": "..."}],
    "clauses": [{"id": "fees", "heading": "Fees", "text": ["... as set out in {ref:term}."]}],
    "governing_law": "the laws of Sweden", "courts": "the general courts of Sweden"}
   A reference {ref:<clause id>} becomes the clause number, so it always resolves.

Every key the builder reads is in spec.fields.json beside SKILL.md. A key that is not there, a value of another
shape, or a term the chosen standard's Cover Page does not have stops the build with its name
(skills/_shared/spec_guard.py): nothing given is left off the page. What the parties agreed that the Cover Page
has no field for goes in "modifications", in their own words.

The script lays out structure only. It never judges whether a term is fair, usual or enforceable,
and its output is not legal advice. Prints a JSON summary. Needs python-docx.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "_shared"))
import company  # noqa: E402
import spec_guard  # noqa: E402
STANDARDS = HERE.parent / "standards"
REF = re.compile(r"\{ref:([\w-]+)\}")
PLACEHOLDER = re.compile(r"\[[^\]]*\]|\bTBD\b|\bTBC\b|_{3,}|<[^>]+>|\bXX+\b|\.\.\.|…")
LAW = "the governing law and the courts are the parties' choice: ask the person which law and which courts, and never fill them in yourself"
SAY = ("This lays out the agreement and checks its structure; it is not legal advice. Say so, and "
       "suggest a lawyer reads it before anyone signs.")


class SpecError(SystemExit):
    pass


def standard(name):
    path = STANDARDS / ("%s.json" % name)
    if not path.is_file():
        have = ", ".join(sorted(p.stem for p in STANDARDS.glob("*.json")))
        raise SpecError("no standard named %r; the pack has: %s" % (name, have))
    return json.loads(path.read_text())


def years(n):
    n = int(n)
    return "%d year%s" % (n, "" if n == 1 else "s")


def check_value(label, value):
    if isinstance(value, list):
        for v in value:
            check_value(label, v)
        return
    text = str(value)
    if PLACEHOLDER.search(text):
        raise SpecError("%s still holds a placeholder (%r): ask the person and write their own words"
                        % (label, PLACEHOLDER.search(text).group(0)))


def check_parties(spec, roles=None):
    parties = spec.get("parties") or []
    if len(parties) < 2:
        raise SpecError("an agreement needs at least two parties, each with name, registration and address")
    for p in parties:
        for key in ("name", "registration", "address"):
            if not str(p.get(key) or "").strip():
                raise SpecError("every party needs its %s (%s): ask the person" % (key, p.get("name", "a party")))
            check_value("%s's %s" % (p.get("name", "a party"), key), p[key])
    if roles:
        got = [p.get("role") for p in parties]
        if sorted(got) != sorted(roles):
            raise SpecError("this agreement has one %s: give each party its \"role\" (%s); got %s"
                            % (" and one ".join(roles), ", ".join(roles), got))


def field_value(f, spec):
    """The text a Cover Page field shows, or a SpecError saying what to ask."""
    name = f["name"]
    if f.get("spec"):
        value = spec.get(f["spec"])
        if not str(value or "").strip():
            if f.get("parties_choice"):
                # One the person did not give stays open on the Cover Page for the parties, never filled in, and the
                # reply names it (timed run c09, 2026-10-25: "a mutual NDA under English law" named no courts, and
                # the command asked and made no file).
                if f["spec"] in (spec.get("unknown") or []):
                    return ""
                raise SpecError("%s is empty: %s" % (name, LAW))
            raise SpecError("the spec needs %s (%s)" % (f["spec"], name))
        check_value(name, value)
        if f.get("format") == "date":
            import word_look
            shown = word_look.long_date(value)
            return shown[:1].upper() + shown[1:]
        return str(value).strip()
    terms = spec.get("terms") or {}
    value = terms.get(name)
    if f.get("options"):
        opts = f["options"]
        if isinstance(value, dict) and "years" in value and "years" in opts:
            return opts["years"].replace("{years}", years(value["years"]))
        if isinstance(value, (int, float)) and "years" in opts:
            return opts["years"].replace("{years}", years(value))
        if isinstance(value, str) and value.strip().lower() in opts:
            return opts[value.strip().lower()]
        choices = ['{"years": N}' if k == "years" else '"%s"' % k for k in opts]
        raise SpecError("%s: ask the person and write one of %s in \"terms\"" % (name, ", ".join(choices)))
    if value in (None, "", []):
        if f.get("required"):
            raise SpecError("the Cover Page needs %s%s: ask the person, never make it up"
                            % (name, " (%s)" % f["help"] if f.get("help") else ""))
        return None
    check_value(name, value)
    if f.get("list"):
        return [str(v) for v in (value if isinstance(value, list) else [value])]
    return str(value).strip()


def apply_changes(std):
    """Common Paper's text with the changes the standard file lists, each found exactly once."""
    sections = json.loads(json.dumps(std["sections"]))
    for ch in std.get("text_changes") or []:
        idx = int(ch["section"]) - 1
        blob = json.dumps(sections[idx], ensure_ascii=False)
        if blob.count(ch["from"]) != 1:
            raise SpecError("standard %s: the change in section %s no longer matches its text" % (std["id"], ch["section"]))
        sections[idx] = json.loads(blob.replace(ch["from"], ch["to"]))
    return sections


def roman(n):
    out = ""
    for v, s in ((10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")):
        while n >= v:
            out += s
            n -= v
    return out


def write_terms(doc, sections, nda_style):
    import word_look as w
    for i, sec in enumerate(sections, 1):
        if nda_style:     # the NDA's terms are one paragraph each: "1. Introduction. Text"
            w.para(doc, "%d.\t**%s**. %s" % (i, sec["heading"], sec.get("text", "")), left=7, hanging=7, after=6)
            continue
        w.para(doc, "%d.\t%s" % (i, sec["heading"]), bold=True, size=10.5, left=10, hanging=10,
               before=10, after=4, keep=True)
        if sec.get("text"):
            w.para(doc, sec["text"], left=10, after=4)
        for j, sub in enumerate(sec.get("items") or [], 1):
            head = "**%s.** " % sub["heading"] if sub.get("heading") else ""
            w.para(doc, "%d.%d\t%s%s" % (i, j, head, sub.get("text", "")), left=10, hanging=10, after=4)
            for k, item in enumerate(sub.get("items") or []):
                w.para(doc, "%s.\t%s" % (chr(97 + k), item.get("text", "")), left=16, hanging=6, after=3)
                for m, deep in enumerate(item.get("items") or [], 1):
                    w.para(doc, "%s.\t%s" % (roman(m), deep.get("text", "")), left=23, hanging=7, after=2)


OPEN = ("governing_law", "courts")


def build_standard(spec, out):
    import word_look as w
    for key in spec.get("unknown") or []:
        if key not in OPEN:
            raise SpecError("\"unknown\" takes %s, the parties' choices a Cover Page leaves open; got %r"
                            % (" and ".join('"%s"' % k for k in OPEN), key))
        if str(spec.get(key) or "").strip():
            raise SpecError("%s is given and also \"unknown\": keep one" % key)
    std = standard(spec["standard"])
    roles = std.get("roles")
    check_parties(spec, roles)
    cover = std["cover"]
    # A term the Cover Page of this standard has no field for would be left off the page: an error by name.
    known = [f["name"] for f in cover["fields"] if not f.get("spec")]
    extra = [k for k in (spec.get("terms") or {}) if k not in known and not str(k).startswith("_")]
    if extra:
        raise SpecError("%s has no Cover Page field named %s, so the builder would leave %s off the page. Its "
                        "fields are: %s. What the parties agreed beyond them goes in \"modifications\", in their "
                        "own words." % (std["id"], ", ".join('"%s"' % k for k in extra),
                                        "it" if len(extra) == 1 else "them", ", ".join(known)))
    values = [(f, field_value(f, spec)) for f in cover["fields"]]
    mods = spec.get("modifications") or []
    for m in mods:
        check_value("a modification", m)
    parties = spec["parties"]
    if roles:
        parties = sorted(parties, key=lambda p: roles.index(p["role"]))
    title = spec.get("title") or std["title"]
    doc = w.new_document(title, subject="%s; %s" % (std["source"]["work"], std["source"]["licence"]))

    doc.add_paragraph(title, style="Title")
    w.para(doc, "Cover Page", size=11, color=w.GREY, after=10)
    w.para(doc, cover["intro"], after=10)
    if roles:
        rows = [[{"text": "Name", "bold": True}] + [p["name"] for p in parties],
                [{"text": "Registration number", "bold": True}] + [p["registration"] for p in parties],
                [{"text": "Address", "bold": True}] + [p["address"] for p in parties]]
        w.para(doc, "Parties", style="Heading 2")
        w.table(doc, rows, [40, 60, 60], header=[""] + [p["role"] for p in parties])
    group = None
    rows = []

    def flush():
        if rows:
            w.table(doc, list(rows), [52, 108])
            rows.clear()

    for f, value in values:
        if value is None:
            continue
        if f.get("group") and f["group"] != group:
            flush()
            group = f["group"]
            w.para(doc, group, style="Heading 2")
        # The help says what a field is for while the parties review; the copy they sign shows their terms only.
        left = {"text": f["name"], "bold": True, "help": None if spec.get("copy") == "signing" else f.get("help")}
        rows.append([left, {"text": value if isinstance(value, list) else [value]}])
    flush()
    w.para(doc, cover["modifications"], style="Heading 2")
    if mods:
        for i, m in enumerate(mods, 1):
            w.para(doc, "%d.\t%s" % (i, m), left=7, hanging=7, after=3)
    else:
        w.para(doc, "None.")
    w.para(doc, cover["signing"], before=6, after=8, keep=True)
    labels = []
    for n, p in enumerate(parties, 1):
        labels.append(cover["party_label"].replace("{n}", str(n)).replace("{role}", p.get("role", "")).upper())
    sig = [[{"text": "Signature", "bold": True, "height": 16}] + ["" for _ in parties],
           [{"text": "Print Name", "bold": True}] + [(p.get("signatory") or {}).get("name", "") for p in parties],
           [{"text": "Title", "bold": True}] + [(p.get("signatory") or {}).get("title", "") for p in parties],
           [{"text": "Company", "bold": True}] + [p["name"] for p in parties],
           [{"text": "Registration number", "bold": True}] + [p["registration"] for p in parties],
           [{"text": "Address", "bold": True}] + [p["address"] for p in parties],
           [{"text": "Notice Address", "bold": True}] + [p.get("notice_address") or p["address"] for p in parties],
           [{"text": "Date", "bold": True, "height": 9}] + ["" for _ in parties]]
    width = 120 / len(parties)
    w.table(doc, sig, [40] + [width] * len(parties), header=[""] + labels)

    w.page_break(doc)
    w.para(doc, std["terms_heading"], style="Heading 1")
    write_terms(doc, apply_changes(std), nda_style=std["kind"] == "nda")

    src = std["source"]
    w.para(doc, "Source and licence", style="Heading 3")
    small = dict(size=8, color=w.GREY, after=2)
    w.para(doc, std["notice"], **small)
    w.para(doc, "%s by %s, %s. Licence: %s, %s." % (src["work"], src["publisher"], src["url"], src["licence"],
                                                   src["licence_url"]), **small)
    w.para(doc, "Changes made: " + " ".join(std["changes"]), **small)
    doc.save(out)
    return {"standard": std["id"], "kind": std["kind"], "sections": len(std["sections"]),
            "cover_fields": [f["name"] for f, v in values if v is not None]}


# The plain agreement, in the parties' own words.

def build_plain(spec):
    missing = [k for k in ("title", "effective_date", "parties", "clauses") if not spec.get(k)]
    if not str(spec.get("governing_law") or "").strip() or not str(spec.get("courts") or "").strip():
        raise SpecError(LAW)
    if missing:
        raise SpecError("the spec needs %s" % ", ".join(missing))
    check_parties(spec)
    check_value("the governing law", spec["governing_law"])
    check_value("the courts", spec["courts"])
    import word_look as w
    first = 2 if spec.get("definitions") else 1
    number = {c["id"]: first + i for i, c in enumerate(spec["clauses"])}
    law_no = first + len(spec["clauses"])

    def resolve(text):
        def one(m):
            if m.group(1) not in number:
                raise SpecError("the cross-reference {ref:%s} points at no clause" % m.group(1))
            return "clause %d" % number[m.group(1)]
        return REF.sub(one, text)

    out = [("title", spec["title"]),
           ("para", "This agreement is made on %s between:" % w.long_date(spec["effective_date"]))]
    for i, p in enumerate(spec["parties"], 1):
        short = ' ("%s")' % p["short"] if p.get("short") else ""
        out.append(("party", "(%d)\t%s, registration number %s, of %s%s%s" % (
            i, p["name"], p["registration"], p["address"], short, "; and" if i < len(spec["parties"]) else ".")))
    if spec.get("background"):
        out.append(("heading", "Background"))
        for i, b in enumerate(spec["background"]):
            out.append(("party", "(%s)\t%s" % (chr(65 + i), resolve(b))))
    if spec.get("definitions"):
        out.append(("heading", "1.\tDefinitions"))
        for d in spec["definitions"]:
            out.append(("para", "“%s” means %s" % (d["term"], resolve(d["means"]).rstrip(".") + ".")))
    for c in spec["clauses"]:
        n = number[c["id"]]
        out.append(("heading", "%d.\t%s" % (n, c["heading"])))
        texts = c["text"] if isinstance(c["text"], list) else [c["text"]]
        for j, t in enumerate(texts, 1):
            out.append(("clause", ("%d.%d\t%s" % (n, j, resolve(t))) if len(texts) > 1 else resolve(t)))
    out.append(("heading", "%d.\tGoverning law and disputes" % law_no))
    out.append(("clause", "%d.1\tThis agreement is governed by %s." % (law_no, spec["governing_law"].rstrip("."))))
    out.append(("clause", "%d.2\tAny dispute arising out of or in connection with this agreement shall be settled by %s."
                % (law_no, spec["courts"].rstrip("."))))
    return out


def write_plain(spec, out):
    import word_look as w
    parts = build_plain(spec)
    doc = w.new_document(spec["title"])
    for style, text in parts:
        if style == "title":
            doc.add_paragraph(text, style="Title")
        elif style == "heading":
            w.para(doc, text, bold=True, size=10.5, left=10, hanging=10, before=10, after=4, keep=True)
        elif style == "party":
            w.para(doc, text, left=10, hanging=10, after=4)
        elif style == "clause":
            w.para(doc, text, left=10, hanging=10 if re.match(r"^\d+\.\d+\t", text) else 0, after=4)
        else:
            w.para(doc, text, left=10 if not text.startswith("This agreement is made") else 0)
    w.para(doc, "Signatures", style="Heading 2")
    parties = spec["parties"]
    sig = [[{"text": "Signature", "bold": True, "height": 16}] + ["" for _ in parties],
           [{"text": "Name", "bold": True}] + [(p.get("signatory") or {}).get("name", "") for p in parties],
           [{"text": "Title", "bold": True}] + [(p.get("signatory") or {}).get("title", "") for p in parties],
           [{"text": "Date", "bold": True, "height": 9}] + ["" for _ in parties]]
    width = 120 / len(parties)
    w.table(doc, sig, [40] + [width] * len(parties),
            header=[""] + ["Signed for and on behalf of %s" % p["name"] for p in parties])
    doc.save(out)
    return {"kind": spec.get("kind", "agreement"), "clauses": len(spec["clauses"]) + 1}


def list_fields(name):
    std = standard(name)
    lines = ["%s (%s), Cover Page fields:" % (std["title"], std["id"])]
    if std.get("roles"):
        lines.append("  parties: one with \"role\": %s" % " and one with ".join('"%s"' % r for r in std["roles"]))
    for f in std["cover"]["fields"]:
        where = 'spec "%s"' % f["spec"] if f.get("spec") else 'terms "%s"' % f["name"]
        need = "the parties' choice, ask" if f.get("parties_choice") else (
            "one of: " + ", ".join('{"years": N}' if k == "years" else '"%s"' % k for k in f["options"])
            if f.get("options") else ("required" if f.get("required") or f.get("spec") else "optional"))
        lines.append("  %-50s %s; %s%s" % (f["name"], where, need, " (%s)" % f["help"] if f.get("help") else ""))
    return "\n".join(lines)


def main(argv):
    if len(argv) == 3 and argv[1] == "--fields":
        print(list_fields(argv[2]))
        return 0
    if len(argv) != 3:
        print(__doc__.split("\n\n")[1])
        return 2
    spec = json.loads(Path(argv[1]).read_text())
    out = Path(argv[2])
    if out.suffix.lower() != ".docx":
        raise SpecError("output must end in .docx")
    # Nothing given is dropped: an unknown key or a value of the wrong shape stops the build here.
    spec_guard.guard(spec, HERE.parent / "spec.fields.json", "agreement's data file")
    spec_guard.output_guard(out, __file__, "agreement")
    # The company's own particulars, written once in the person's folder: what the data file leaves out.
    company.apply(spec, argv[1], "contract-drafting")
    if spec.get("standard") and spec.get("clauses"):
        raise SpecError("the spec has both \"standard\" and \"clauses\": a standard agreement prints its own terms and "
                        "would leave the clauses off the page. Take one out; a change to a standard goes in "
                        "\"modifications\"")
    if spec.get("standard"):
        summary = build_standard(spec, out)
    elif spec.get("clauses"):
        summary = write_plain(spec, out)
    else:
        raise SpecError("the spec needs \"standard\" (a Common Paper agreement) or \"clauses\" (a plain agreement)")
    summary.update({"file": str(out), "say": SAY})
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
