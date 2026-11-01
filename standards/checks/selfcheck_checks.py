#!/usr/bin/env python3
"""Self-test for the rules: they must pass good work and fail bad work.

After this many rule edits, the honest question is whether they still discriminate at all. For
each rule this runs the check against a known-good artifact and, where one exists, a known-bad
fixture, and prints pass/fail so a rule that stopped discriminating shows up.
"""
import json
import subprocess
import sys
from pathlib import Path

W = Path.home() / "nodejam-fork-wt"
EVAL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVAL / "checks"))
FIX = Path.home() / "Nodejam/output/gtm/op-core-20261005/part4-evals/fixtures"

GOOD = {
    "EINV-PAGE": (W / "core-invoice-20261005/tmp/part2-invoice-plain/invoice.pdf", "de-DE",
                  ["EINV-PAGE-COMPLETE", "EINV-PAGE-NO-EXTRA", "EINV-PAGE-TRACE"]),
    "DECK": (Path.home() / "Nodejam/output/gtm/op-core-20261005/house-layout/house-deck.html", "en-GB",
             ["DECK-PAGES", "DECK-TYPE", "DECK-ACCENT"]),
    "PAPER": (EVAL / "cases/54-professional-scientific-technical-services/15-1252-software-developers/paper-ieee-coldstart-001/build/paper.pdf",
              "en-US", ["PAPER-FONTS"]),
    "APA": (W / "core-academic-20261005/tmp/part3-apa/report.docx", "en-US",
            ["APA-NO-INTRO", "APA-REFS-NEW-PAGE"]),
}
BAD = [
    ("EINV-PAGE-COMPLETE", FIX / "wrong-amount/invoice-wrong-total.pdf", "de-DE", "page", "wrong total must fail"),
]

MODULES = {"EINV-PAGE": "einvoice_page", "DECK": "housedeck", "PAPER": "academic_style", "APA": "academic_style"}

# DECK-FILL reads the rendered page, so it is proven beside the house deck and the known-bad files
# instead of the markup groups above. Each entry is (path, must pass). The three "hole" files and the
# empty svg frame are real builder output from 2026-10-05 kept as known-bad.
DECK_OUT = Path.home() / "Nodejam/output/gtm/op-core-20261005"
FILL = [
    (DECK_OUT / "house-layout/house-deck.html", True),
    (EVAL / "checks/fixtures/deck/good.html", True),
    (EVAL / "checks/fixtures/deck/stripped.html", False),
    (EVAL / "checks/fixtures/deck/bad-cover-hole.html", False),
    (EVAL / "checks/fixtures/deck/bad-timeline-hole.html", False),
    (EVAL / "checks/fixtures/deck/bad-empty-svg.html", False),
] + [(DECK_OUT / ("part4-evals/deck-fill-run4/baseline/work/house-deck-001_rep%d/first/deck.html" % r), False)
     for r in range(3)]


# DECK-BOUNDS has its own known-bad files: a page that reached past the footer and a page whose
# content boxes collide.
BOUNDS = [
    (DECK_OUT / "house-layout/house-deck.html", True),
    (EVAL / "checks/fixtures/deck/good.html", True),
    (EVAL / "checks/fixtures/deck/bad-closing-footer.html", False),
    (EVAL / "checks/fixtures/deck/bad-overlap.html", False),
]


def bounds_results():
    """DECK-BOUNDS must pass the good files and fail the page that crossed the footer."""
    out = []
    for path, must_pass in BOUNDS:
        if not path.exists():
            continue
        try:
            ok, why = load("housedeck").check("DECK-BOUNDS", path, {}, "first")
        except Exception as exc:
            out.append(("DECK-BOUNDS", path.name, "error %s" % str(exc)[:40], "FAIL"))
            continue
        if not ok and "not measured" in str(why):
            out.append(("DECK-BOUNDS", path.name, str(why)[:46], "skip"))
            continue
        verdict = "PASS" if ok == must_pass else "FAIL"
        out.append(("DECK-BOUNDS", "%s must %s" % (path.name, "pass" if must_pass else "fail"),
                    str(why)[:46], verdict))
    return out


def fill_results():
    """DECK-FILL must pass the house deck and fail every known-bad page."""
    out = []
    for path, must_pass in FILL:
        if not path.exists():
            continue
        try:
            ok, why = load("housedeck").check("DECK-FILL", path, {}, "first")
        except Exception as exc:
            out.append(("DECK-FILL", "fill", "error %s" % str(exc)[:40], "FAIL"))
            continue
        if not ok and "fill not measured" in str(why):
            out.append(("DECK-FILL", path.name, str(why)[:46], "skip"))
            continue
        verdict = "PASS" if ok == must_pass else "FAIL"
        out.append(("DECK-FILL", "%s must %s" % (path.name, "pass" if must_pass else "fail"),
                    str(why)[:46], verdict))
    return out


def load(name):
    return __import__(name)


def main():
    results = []
    for group, (path, locale, rules) in GOOD.items():
        mod = load(MODULES[group])
        case = {"locale": locale, "truth": {"pages": 13, "values": [], "accents": ["#d9480f", "#ad3a0b", "#f08c4a", "#0f6e5c"]}}
        if path.suffix == ".pdf" and group == "EINV-PAGE":
            case = json.loads((EVAL / "cases/54-professional-scientific-technical-services/43-3021-billing-and-posting-clerks/eu-invoice-page-001/case.json").read_text())
        for rule in rules:
            if not path.exists():
                results.append((rule, "good", "no artifact", "skip"))
                continue
            try:
                ok, why = mod.check(rule, path, case, "first")
                results.append((rule, "good", str(why)[:44], "PASS" if ok else "FAIL"))
            except Exception as e:
                results.append((rule, "good", "error %s" % str(e)[:40], "FAIL"))
    for rule, path, locale, kind, why in BAD:
        mod = load("einvoice_page")
        case = json.loads((EVAL / "cases/54-professional-scientific-technical-services/43-3021-billing-and-posting-clerks/eu-invoice-page-001/case.json").read_text())
        try:
            ok, ev = mod.check(rule, path, case, "first")
            results.append((rule, "bad fixture", str(ev)[:44], "PASS" if ok is False else "FAIL"))
        except Exception as e:
            results.append((rule, "bad fixture", "error %s" % str(e)[:40], "FAIL"))

    results.extend(fill_results())
    results.extend(bounds_results())
    width = max(len(r[0]) for r in results)
    failures = 0
    for rule, kind, why, verdict in results:
        print("%-*s %-12s %-46s %s" % (width, rule, kind, why, verdict))
        if verdict == "FAIL":
            failures += 1
    print("rules run:", len(results), "| failures:", failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
