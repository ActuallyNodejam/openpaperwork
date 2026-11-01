"""The contract pack's three starters pass their own check, and the check catches each kind of mistake.

    python3 -m unittest skills/contract-drafting/tests/test_contract_drafting.py      (needs python-docx)
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
CHECK = PACK.parent / "_checks" / "packcheck.py"
LAW = {"nda": ("Scotland", "Scotland, with the Court of Session in Edinburgh as the first instance"),
       "dpa": ("Sweden", ""),
       "csa": ("Sweden", "the general courts of Sweden, with Stockholm District Court as the first instance")}


def run(*args):
    return subprocess.run([sys.executable] + [str(a) for a in args], capture_output=True, text=True)


def check(output):
    r = run(CHECK, "contract-drafting", output)
    return r.returncode, r.stdout


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class Agreements(Base):
    def build(self, kind, law=True, mutate=None):
        spec = json.loads((PACK / "templates" / ("%s.spec.json" % kind)).read_text())
        if law:
            spec["governing_law"], spec["courts"] = LAW[kind]
        if mutate:
            mutate(spec)
        folder = self.tmp / kind
        folder.mkdir(exist_ok=True)
        (folder / "spec.json").write_text(json.dumps(spec, ensure_ascii=False))
        out = folder / ("%s.docx" % kind)
        return run(PACK / "scripts" / "agreement_create.py", folder / "spec.json", out), out

    def test_each_template_passes_its_check(self):
        for kind in ("nda", "dpa", "csa"):
            r, out = self.build(kind)
            self.assertEqual(r.returncode, 0, r.stderr)
            code, text = check(out)
            self.assertEqual(code, 0, kind + ": " + text)
            self.assertIn("pack check clean", text)

    def test_courts_the_person_did_not_give_stay_open_for_the_parties(self):
        # Timed run c09, 2026-10-25: "a mutual NDA under English law, two years" named no courts.
        def open_courts(spec):
            spec["governing_law"], spec["courts"], spec["unknown"] = "the laws of England and Wales", "", ["courts"]
        r, out = self.build("nda", law=False, mutate=open_courts)
        self.assertEqual(r.returncode, 0, r.stderr)
        code, text = check(out)
        self.assertEqual(code, 0, text)
        self.assertRegex(text, r"WARN LEGAL-LAW +the Cover Page leaves Jurisdiction open")
        r, _ = self.build("nda", law=False, mutate=lambda s: s.update(governing_law="the laws of England and Wales"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("parties' choice", r.stderr + r.stdout)
        r, _ = self.build("nda", law=False, mutate=lambda s: s.update(unknown=["Purpose"]))
        self.assertNotEqual(r.returncode, 0)

    def test_the_copy_for_signing_shows_no_field_help(self):
        r, out = self.build("csa")
        with zipfile.ZipFile(out) as z:
            self.assertIn("write None for none", z.read("word/document.xml").decode())
        r, out = self.build("csa", mutate=lambda s: s.update({"copy": "signing"}))
        self.assertEqual(r.returncode, 0, r.stderr)
        with zipfile.ZipFile(out) as z:
            xml = z.read("word/document.xml").decode()
        self.assertNotIn("write None for none", xml)
        self.assertIn("General Cap Amount", xml)
        self.assertEqual(check(out)[0], 0)

    def test_the_law_is_never_filled_in(self):
        for kind in ("nda", "dpa", "csa"):
            r, _ = self.build(kind, law=False)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("parties' choice", r.stdout + r.stderr)

    def test_common_paper_text_is_word_for_word(self):
        r, out = self.build("nda")
        with zipfile.ZipFile(out) as z:
            xml = z.read("word/document.xml").decode()
        self.assertIn("rightfully knew or possessed prior to receipt from the Disclosing Party", xml)
        self.assertIn("CC BY 4.0", xml)
        self.assertEqual(xml.count("laws of the State of"), 1)    # only in the notice of the change to Section 9

    def test_a_placeholder_or_missing_field_is_refused(self):
        r, _ = self.build("csa", mutate=lambda s: s["terms"].update({"Fees": "[TBD]"}))
        self.assertIn("placeholder", r.stdout + r.stderr)
        r, _ = self.build("dpa", mutate=lambda s: s["terms"].pop("Categories of Personal Data"))
        self.assertIn("Categories of Personal Data", r.stdout + r.stderr)

    def test_it_takes_effect_when_the_last_party_signs_and_an_ampersand_is_a_name(self):
        # A real run, 2026-10-13: "starts on the date the last of us signs" was refused for want of a calendar
        # date, and "Hughes & Patel Accounting Ltd" failed its own parties and signature rules (read as &amp;).
        def mutate(s):
            s["effective_date"] = "last signature"
            s["parties"][0]["name"] = "Hughes & Patel Accounting Ltd"
        r, out = self.build("nda", mutate=mutate)
        self.assertEqual(r.returncode, 0, r.stderr)
        code, text = check(out)
        self.assertEqual(code, 0, text)
        with zipfile.ZipFile(out) as z:
            self.assertIn("date of the last signature", z.read("word/document.xml").decode("utf-8"))

    def test_a_plain_agreement_still_builds(self):
        spec = json.loads((PACK / "templates" / "nda.spec.json").read_text())
        plain = {"kind": "agreement", "title": "Supply Agreement", "effective_date": "2026-11-01",
                 "parties": spec["parties"], "definitions": [{"term": "Goods", "means": "the printed reports in clause 2"}],
                 "clauses": [{"id": "supply", "heading": "Supply", "text": ["Exempel Tryck supplies the Goods as set out in {ref:fees}."]},
                             {"id": "fees", "heading": "Fees", "text": ["Brightwater pays for the Goods within 30 days."]}],
                 "governing_law": "the laws of Sweden", "courts": "the general courts of Sweden"}
        folder = self.tmp / "plain"
        folder.mkdir()
        (folder / "spec.json").write_text(json.dumps(plain))
        r = run(PACK / "scripts" / "agreement_create.py", folder / "spec.json", folder / "a.docx")
        self.assertEqual(r.returncode, 0, r.stderr)
        code, text = check(folder / "a.docx")
        self.assertEqual(code, 0, text)


class Review(Base):
    def setUp(self):
        super().setUp()
        run(PACK / "tests" / "make_counterparty.py", self.tmp / "their-nda.docx")
        self.review = json.loads((PACK / "templates" / "review.example.json").read_text())

    def build(self, review=None):
        (self.tmp / "review.json").write_text(json.dumps(review or self.review, ensure_ascii=False))
        return run(PACK / "scripts" / "review_create.py", self.tmp / "review.json", self.tmp / "review.docx")

    def test_the_example_review_passes(self):
        r = self.build()
        self.assertEqual(r.returncode, 0, r.stderr)
        code, text = check(self.tmp / "review.docx")
        self.assertEqual(code, 0, text)

    def test_a_made_up_quote_is_refused_and_caught(self):
        bad = json.loads(json.dumps(self.review))
        bad["items"][3]["quote"] = "information independently developed by the Recipient"
        r = self.build(bad)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("is not in their-nda.docx", r.stdout + r.stderr)
        self.build()
        (self.tmp / "review.json").write_text(json.dumps(bad))          # the JSON changed after the build
        code, text = check(self.tmp / "review.docx")
        self.assertIn("FAIL LEGAL-QUOTE", text)

    def test_an_item_without_a_verdict_is_caught(self):
        self.build()
        short = json.loads(json.dumps(self.review))
        short["items"] = [i for i in short["items"] if i["id"] != "remedies"]
        (self.tmp / "review.json").write_text(json.dumps(short))
        code, text = check(self.tmp / "review.docx")
        self.assertIn("FAIL LEGAL-VERDICT", text)
        self.assertIn("Remedies has no verdict", text)

    def test_a_verdict_on_the_whole_agreement_is_caught(self):
        loud = json.loads(json.dumps(self.review))
        loud["items"][1]["note"] = "The rest of the agreement is compliant and safe to sign."
        self.assertEqual(self.build(loud).returncode, 0)
        code, text = check(self.tmp / "review.docx")
        self.assertIn("FAIL LEGAL-WORDING", text)


class Redline(Base):
    def setUp(self):
        super().setUp()
        run(PACK / "tests" / "make_counterparty.py", self.tmp / "their-nda.docx")
        self.spec = json.loads((PACK / "templates" / "redline.example.json").read_text())
        (self.tmp / "redline.json").write_text(json.dumps(self.spec))
        self.out = self.tmp / "their-nda-redline.docx"

    def test_the_example_redline_passes(self):
        r = run(PACK / "scripts" / "redline_create.py", self.tmp / "redline.json")
        self.assertEqual(r.returncode, 0, r.stderr)
        code, text = check(self.out)
        self.assertEqual(code, 0, text)
        with zipfile.ZipFile(self.out) as z:
            xml = z.read("word/document.xml").decode()
            comments = z.read("word/comments.xml").decode()
        self.assertIn('w:author="Exempel Tryck AB"', xml)
        self.assertIn("<w:delText", xml)
        self.assertIn("three years after the agreement ends", comments)

    def test_a_redline_answers_only_for_what_it_added(self):
        # workflows-op c10, 2026-10-25: their NDA carried no title; the redline keeps their file as sent
        # (LEGAL-ORIGINAL), so the floor does not ask it for one.
        theirs = self.tmp / "their-nda.docx"
        with zipfile.ZipFile(theirs) as z:
            parts = [(i, z.read(i.filename)) for i in z.infolist()]
        with zipfile.ZipFile(theirs, "w") as z:
            for info, data in parts:
                z.writestr(info, re.sub(rb"<dc:title>[^<]*</dc:title>", b"", data) if info.filename ==
                           "docProps/core.xml" else data)
        r = run(PACK / "scripts" / "redline_create.py", self.tmp / "redline.json")
        self.assertEqual(r.returncode, 0, r.stderr)
        code, text = check(self.out)
        self.assertEqual(code, 0, text)
        self.assertNotIn("FLOOR-META", text.replace("PASS FLOOR-META", ""))

    def test_the_turn_end_check_claims_a_redline_by_its_json(self):
        # The Stop hook runs the check --if-claimed: the redline.json beside it makes the file the pack's, so a
        # rewritten copy of their agreement is caught at the turn's end too, not only by a full check.
        self.test_a_rewritten_copy_is_caught()
        r = run(CHECK, "contract-drafting", self.out, "--if-claimed", "--in", self.tmp)
        self.assertIn("FAIL LEGAL-REDLINE", r.stdout)

    def test_a_rewritten_copy_is_caught(self):
        with zipfile.ZipFile(self.tmp / "their-nda.docx") as a, zipfile.ZipFile(self.out, "w") as b:
            for info in a.infolist():
                data = a.read(info.filename)
                if info.filename == "word/document.xml":
                    data = data.replace(b"ten (10) years", b"three (3) years")
                b.writestr(info, data)
        code, text = check(self.out)
        self.assertIn("FAIL LEGAL-REDLINE", text)

    def test_text_changed_outside_the_changes_is_caught(self):
        run(PACK / "scripts" / "redline_create.py", self.tmp / "redline.json")
        tampered = self.tmp / "t.docx"
        with zipfile.ZipFile(self.out) as a, zipfile.ZipFile(tampered, "w") as b:
            for info in a.infolist():
                data = a.read(info.filename)
                if info.filename == "word/document.xml":
                    data = data.replace(b"NOK 500,000", b"NOK 50,000")
                b.writestr(info, data)
        shutil.move(tampered, self.out)
        code, text = check(self.out)
        self.assertIn("FAIL LEGAL-ORIGINAL", text)
        self.assertIn("NOK 50,000", text)

    def test_an_ambiguous_find_is_refused(self):
        spec = dict(self.spec, edits=[{"find": "Confidential Information", "replace": "Information"}])
        (self.tmp / "redline.json").write_text(json.dumps(spec))
        r = run(PACK / "scripts" / "redline_create.py", self.tmp / "redline.json")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("appears", r.stdout + r.stderr)

    def test_the_original_is_never_overwritten(self):
        spec = dict(self.spec, output="their-nda.docx")
        (self.tmp / "redline.json").write_text(json.dumps(spec))
        r = run(PACK / "scripts" / "redline_create.py", self.tmp / "redline.json")
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
