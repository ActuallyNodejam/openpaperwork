#!/usr/bin/env python3
"""Pack consistency check: every core case is complete and its criteria resolve.

Catches the half-formed case shapes this whole stretch kept tripping over: a missing output name,
criteria that name a rule no guideline defines, a criterion naming a check script that is not in
checks/, a case without a revision, sector or occupation as objects, or inputs that are absent.
"""
import json
from pathlib import Path

EVAL = Path(__file__).resolve().parents[1]
BASE = EVAL / "cases/54-professional-scientific-technical-services"
CASES = [
    "43-3021-billing-and-posting-clerks/eu-invoice-plain-001",
    "43-3021-billing-and-posting-clerks/eu-invoice-page-001",
    "43-3021-billing-and-posting-clerks/eu-invoice-reverse-charge-001",
    "43-3021-billing-and-posting-clerks/eu-invoice-credit-note-001",
    "15-1252-software-developers/paper-ieee-coldstart-001",
    "15-1252-software-developers/paper-apa-report-001",
    "23-2011-paralegals-and-legal-assistants/refs-repair-apa-001",
    "15-1252-software-developers/house-deck-001",
]

problems = 0
for rel in CASES:
    d = BASE / rel
    case = json.loads((d / "case.json").read_text())
    bad = []
    for key in ("id", "output", "format", "criteria", "truth", "sector", "occupation"):
        if not case.get(key):
            bad.append("missing " + key)
    if not isinstance(case.get("sector"), dict) or "naics" not in case.get("sector", {}):
        bad.append("sector is not an object with naics")
    if not isinstance(case.get("occupation"), dict) or "soc" not in case.get("occupation", {}):
        bad.append("occupation is not an object with soc")
    if not (d / "revision.md").is_file():
        bad.append("no revision.md")
    if not any((d / "inputs").glob("*")):
        bad.append("no inputs")
    for c in case.get("criteria", []):
        if c.get("grader") == "script":
            if not (EVAL / "checks" / c.get("script", "")).is_file():
                bad.append("check script missing: %s" % c.get("script"))
            for g in c.get("guidelines", []):
                name, _, rule = g.partition("#")
                f = EVAL / "guidelines" / name / "guidelines.json"
                if not f.is_file():
                    bad.append("guideline missing: %s" % name)
                elif rule and rule not in {r["id"] for r in json.loads(f.read_text())["rules"]}:
                    bad.append("rule not defined: %s" % g)
    print("%-30s %s" % (case["id"], "ok" if not bad else "; ".join(sorted(set(bad))[:4])))
    problems += len(bad)
print("cases:", len(CASES), "| problems:", problems)
