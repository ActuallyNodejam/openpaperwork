#!/usr/bin/env python3
"""Write a review of the other side's agreement as a Word memo, from a review JSON.

Usage: review_create.py review.json review.docx

The method is the coverage ledger of Open Legal Products' mike-workflows (MIT): every item of the
checklist (checklists/nda.json or checklists/dpa.json) gets exactly one verdict, Finding,
Acceptable, Not applicable or Missing information; each Finding quotes the document word for word
and says whether it is a legal issue or a commercial preference, and the two are kept apart.

{
  "document": "their-nda.docx",            # the file under review, beside this JSON (Word, PDF or text)
  "title": "Confidentiality Agreement",    # what the document calls itself
  "checklist": "nda",                      # nda or dpa
  "for": "Exempel Tryck AB",              # the party the review is written for
  "side": "Receiving Party",               # nda: Disclosing Party, Receiving Party or both; dpa: Provider or Customer
  "other_party": "Halvard Data AS",
  "date": "2026-11-03",
  "prepared_by": "Karin Lind",
  "assumptions": ["The parties will share prices and customer lists, nothing technical."],
  "items": [
    {"id": "term", "verdict": "Finding", "issue": "commercial", "clause": "7",
     "quote": "shall survive for a period of ten (10) years",
     "note": "Ten years is long for price lists that change every year.",
     "proposed_change": "Three years after the agreement ends, trade secrets for as long as they stay secret."},
    {"id": "residuals", "verdict": "Acceptable", "note": "No residuals clause; nothing is lost for us."},
    {"id": "non-solicit", "verdict": "Not applicable", "note": "The agreement has no such restriction."},
    {"id": "law", "verdict": "Missing information", "note": "Schedule 2 with the chosen courts is referred to but not attached; ask for it."}
  ]
}

"quote" may be a list ("quotes"); a quote may skip text with "..." between pieces, each found in
order. The script refuses a quote it cannot find in the document. It never says whether the
agreement is fine to sign, and the memo says that a lawyer should read the agreement before anyone
signs. Prints a JSON summary. Needs python-docx.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "_checks"))
import legal_check as lc  # noqa: E402
sys.path.insert(0, str(HERE.parent.parent / "_shared"))
import spec_guard  # noqa: E402

ORDER = ["Finding", "Acceptable", "Not applicable", "Missing information"]
ABOUT = ("This memo reads the {title} against the {checklist}, item by item. Each item has one verdict: "
         "Finding, Acceptable, Not applicable or Missing information. A finding quotes the document word "
         "for word and is marked as a legal issue or a commercial preference; the two are listed apart. "
         "The review is written for {party}{side}. It is not legal advice and it does not say whether "
         "to sign; a lawyer should read the agreement before anyone signs.")


def fail(msg):
    raise SystemExit(msg)


def load(spec_path):
    spec = json.loads(Path(spec_path).read_text())
    # Nothing given is dropped: an unknown key or a value of the wrong shape stops the build here.
    spec_guard.guard(spec, HERE.parent / "review.fields.json", "review's data file")
    for key in ("document", "checklist", "for", "items"):
        if not spec.get(key):
            fail("the review needs \"%s\"" % key)
    checklist = lc.load_checklist(spec["checklist"])
    if not checklist:
        fail("no checklist named %r: use nda or dpa" % spec["checklist"])
    side = spec.get("side")
    sides = checklist.get("sides") or []
    if side and side != "both" and side not in sides:
        fail("\"side\" must be one of %s%s" % (", ".join(sides), " or both" if spec["checklist"] == "nda" else ""))
    doc = Path(spec_path).parent / spec["document"]
    if not doc.is_file():
        fail("the reviewed document %s is not beside the review JSON" % spec["document"])
    text = lc.document_text(doc)
    if text is None:
        fail("could not read the text of %s; save it as Word or PDF with text" % doc.name)
    hay = lc.norm(text)
    by_id = {}
    problems = []
    wanted = [c["id"] for c in checklist["items"]]
    for it in spec["items"]:
        if it.get("id") not in wanted:
            problems.append("%r is not an item of the %s (%s)" % (it.get("id"), checklist["title"], ", ".join(wanted)))
            continue
        if it["id"] in by_id:
            problems.append("%s has two verdicts; give it one" % it["id"])
        v = lc.VERDICTS.get(str(it.get("verdict", "")).strip().lower())
        if not v:
            problems.append("%s: the verdict must be one of %s" % (it["id"], ", ".join(ORDER)))
            continue
        it["verdict"] = v
        if v == "Finding":
            if str(it.get("issue", "")).lower() not in lc.ISSUES:
                problems.append("%s: say \"issue\": \"legal\" or \"commercial\"" % it["id"])
            if not lc.finding_quotes(it):
                problems.append("%s: a finding quotes the document word for word" % it["id"])
        if v in ("Not applicable", "Missing information") and not str(it.get("note", "")).strip():
            problems.append("%s: %s needs a note" % (it["id"], v))
        for q in lc.finding_quotes(it):
            if not lc.quote_found(q, hay):
                problems.append("%s: %r is not in %s; copy the words exactly" % (it["id"], q[:70], doc.name))
        by_id[it["id"]] = it
    for c in checklist["items"]:
        if c["id"] not in by_id:
            problems.append("%s (%s) has no verdict" % (c["title"], c["id"]))
    if problems:
        fail("the review is not complete:\n  " + "\n  ".join(problems))
    return spec, checklist, by_id


def write(spec, checklist, by_id, out):
    import word_look as w
    title = spec.get("title") or Path(spec["document"]).stem
    heading = "Review of the %s" % title
    doc = w.new_document(heading, subject="contract review: %s" % checklist["title"])
    doc.core_properties.category = "contract review"
    doc.add_paragraph(heading, style="Title")
    w.para(doc, "%s, from %s" % (spec["document"], spec.get("other_party") or "the other party"),
           size=11, color=w.GREY, after=10)
    meta = [["Reviewed for", spec["for"] + (" (%s)" % spec["side"] if spec.get("side") and spec["side"] != "both" else "")],
            ["Other party", spec.get("other_party", "")],
            ["Document", spec["document"]],
            ["Checklist", "%s, from %s" % (checklist["title"], checklist["source"]["work"])],
            ["Date", w.long_date(spec["date"]) if spec.get("date") else ""],
            ["Prepared by", spec.get("prepared_by", "")]]
    w.table(doc, [[{"text": k, "bold": True}, v] for k, v in meta if v], [40, 120])
    side = " as the %s" % spec["side"] if spec.get("side") and spec["side"] != "both" else ""
    w.para(doc, ABOUT.format(title=title, checklist=checklist["title"], party=spec["for"], side=side), after=8)

    items = [(c, by_id[c["id"]]) for c in checklist["items"]]
    legal = [(c, it) for c, it in items if it["verdict"] == "Finding" and it["issue"].lower() == "legal"]
    commercial = [(c, it) for c, it in items if it["verdict"] == "Finding" and it["issue"].lower() == "commercial"]
    missing = [(c, it) for c, it in items if it["verdict"] == "Missing information"]
    count = {v: sum(1 for _, it in items if it["verdict"] == v) for v in ORDER}
    w.para(doc, "Summary", style="Heading 1")
    w.table(doc, [["Findings: legal issues", str(len(legal))],
                  ["Findings: commercial preferences", str(len(commercial))],
                  ["Acceptable", str(count["Acceptable"])],
                  ["Not applicable", str(count["Not applicable"])],
                  ["Missing information", str(count["Missing information"])],
                  [{"text": "Checklist items", "bold": True}, {"text": str(len(items)), "bold": True}]],
            [90, 30], header=["Verdict", "Items"])
    if spec.get("assumptions"):
        w.para(doc, "Assumptions", style="Heading 2")
        for a in spec["assumptions"]:
            w.para(doc, "–\t" + a, left=6, hanging=6, after=3)

    def findings(label, rows, prefix):
        w.para(doc, label, style="Heading 1")
        if not rows:
            w.para(doc, "None found against the checklist.")
            return
        for n, (c, it) in enumerate(rows, 1):
            where = " (clause %s)" % it["clause"] if it.get("clause") else ""
            w.para(doc, "%s%d. %s%s" % (prefix, n, c["title"], where), style="Heading 2")
            for q in it_quotes(it):
                p = w.para(doc, "“%s”" % q, italic=True, left=8, after=4)
                p.paragraph_format.right_indent = w.Mm(8)
            if it.get("note"):
                w.para(doc, "**What it means.** " + it["note"], after=4)
            if it.get("proposed_change"):
                w.para(doc, "**Proposed change.** " + it["proposed_change"], after=8)

    def it_quotes(it):
        return lc.finding_quotes(it)

    findings("Legal issues", legal, "L")
    findings("Commercial preferences", commercial, "C")
    w.para(doc, "Missing information", style="Heading 1")
    if missing:
        for c, it in missing:
            w.para(doc, "**%s.** %s" % (c["title"], it["note"]), after=4)
    else:
        w.para(doc, "Nothing the review needed was missing.")

    w.para(doc, "Coverage", style="Heading 1")
    rows = []
    for c, it in items:
        kind = it["issue"].capitalize() if it["verdict"] == "Finding" else ""
        if it["verdict"] == "Finding":
            n = "See %s above." % ("Legal issues" if it["issue"].lower() == "legal" else "Commercial preferences")
            note = [n]
        else:
            note = ["“%s”" % q for q in lc.finding_quotes(it)] + ([it["note"]] if it.get("note") else [])
        rows.append([{"text": c["title"], "bold": True}, it["verdict"], kind, it.get("clause", ""), {"text": note}])
    w.table(doc, rows, [38, 24, 20, 19, 59], header=["Item", "Verdict", "Type", "Clause", "Note"], size=8.5)
    src = checklist["source"]
    w.para(doc, "Checklist: %s, %s, %s; %s. %s" % (src["work"], src["repository"], src["commit"][:12], src["licence"],
                                                   checklist["changes"]), size=8, color=w.GREY, after=2)
    doc.save(out)
    return {"items": len(items), "legal": len(legal), "commercial": len(commercial),
            "acceptable": count["Acceptable"], "not_applicable": count["Not applicable"],
            "missing_information": count["Missing information"]}


def main(argv):
    if len(argv) != 3:
        print(__doc__.split("\n\n")[1])
        return 2
    out = Path(argv[2])
    if out.suffix.lower() != ".docx":
        fail("output must end in .docx")
    spec_guard.output_guard(out, __file__, "review")
    spec, checklist, by_id = load(argv[1])
    summary = write(spec, checklist, by_id, out)
    summary.update({"file": str(out), "say": "Say what the review found item by item and that it is not legal "
                    "advice; never say the agreement is fine, compliant or ready to sign."})
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
