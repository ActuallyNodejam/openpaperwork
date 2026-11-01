"""The annual-report builder passes its own check, and the check catches each kind of mistake.

    python3 -m unittest skills/annual-accounts/tests/test_annual_accounts.py      (needs python-docx)
"""
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACK.parent / "_checks"))
import annual_accounts_check as aa  # noqa: E402

SPECS = {"sv": PACK / "templates" / "arsredovisning-konsult.spec.json",
         "en": PACK / "templates" / "annual-report-cleaning.spec.json"}
NEVER = ("compliant", "lawful", "approved", "ready to file", "godkänd", "korrekt")


def build(spec, folder, keep_spec=True):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "spec.json").write_text(json.dumps(spec, ensure_ascii=False))
    out = folder / "report.docx"
    subprocess.run([sys.executable, str(PACK / "scripts" / "annual_create.py"), str(folder / "spec.json"), str(out)],
                   check=True, capture_output=True)
    if not keep_spec:
        (folder / "spec.json").unlink()
    return out


def edit(path, old, new):
    """Replace text inside the Word file, as a person editing the draft by hand would."""
    tmp = path.with_suffix(".tmp")
    with zipfile.ZipFile(path) as src, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == "word/document.xml":
                text = data.decode("utf-8")
                assert old in text, old
                data = text.replace(old, new).encode("utf-8")
            dst.writestr(item, data)
    shutil.move(tmp, path)


def results(path):
    return {rule: aa.check(rule, path, {}, "first") for rule in aa.RULES}


class AnnualAccounts(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.spec = {k: json.loads(v.read_text()) for k, v in SPECS.items()}

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def failing(self, path):
        return {rule for rule, (ok, _) in results(path).items() if ok is False}

    def test_starters_pass_their_own_check_and_never_claim_more(self):
        for lang, spec in self.spec.items():
            for keep in (True, False):
                out = build(spec, self.dir / ("%s-%s" % (lang, keep)), keep_spec=keep)
                for rule, (ok, why) in results(out).items():
                    self.assertTrue(ok, "%s %s: %s" % (lang, rule, why))
                    self.assertFalse(any(w in why.lower() for w in NEVER), why)

    def test_unbalanced_balance_sheet(self):
        spec = copy.deepcopy(self.spec["sv"])
        spec["balance"]["cash"][0] += 12000
        out = build(spec, self.dir / "cash")
        ok, why = aa.check("ANNUAL-BALANCE", out, {}, "first")
        self.assertFalse(ok)
        self.assertIn("12 000", why)

    def test_result_differs_between_statements(self):
        spec = copy.deepcopy(self.spec["sv"])
        spec["balance"]["result"] = [250000, 177700]
        out = build(spec, self.dir / "result")
        self.assertIn("ANNUAL-RESULT", self.failing(out))

    def test_equity_does_not_run_from_last_year(self):
        spec = copy.deepcopy(self.spec["sv"])
        spec["balance"]["retained"] = [300000, 210300]
        out = build(spec, self.dir / "equity")
        self.assertIn("ANNUAL-EQUITY", self.failing(out))

    def test_disposition_does_not_add_up(self):
        spec = copy.deepcopy(self.spec["sv"])
        spec["disposition"]["carried_forward"] = 395200
        out = build(spec, self.dir / "disp")
        ok, why = aa.check("ANNUAL-DISPOSITION", out, {}, "first")
        self.assertFalse(ok)
        self.assertIn("545 200", why)

    def test_dividend_larger_than_the_funds(self):
        spec = copy.deepcopy(self.spec["en"])
        spec["disposition"] = {"dividend": 50000}
        out = build(spec, self.dir / "dividend")
        ok, why = aa.check("ANNUAL-DISPOSITION", out, {}, "first")
        self.assertFalse(ok)
        self.assertIn("larger than", why)

    def test_note_carrying_amount_differs(self):
        spec = copy.deepcopy(self.spec["en"])
        spec["balance"]["equipment"] = [90000, 126000]
        out = build(spec, self.dir / "note")
        ok, why = aa.check("ANNUAL-NOTES", out, {}, "first")
        self.assertFalse(ok)
        self.assertIn("note", why)

    def test_a_subtotal_typed_wrong(self):
        out = build(self.spec["sv"], self.dir / "sum")
        doc = aa.Doc(out)
        rows, _, _ = aa.statement(doc.tables("income"), True)
        cost = next(r for r in rows if r.norm == "summa rörelsekostnader")
        shown = lambda v: aa.fmt(v).replace(" ", "\u00a0").replace("-", "\u2212")  # noqa: E731
        edit(out, shown(cost.cur), shown(cost.cur - 1000))
        ok, why = aa.check("ANNUAL-SUMS", out, {}, "first")
        self.assertFalse(ok)
        self.assertIn("Summa rörelsekostnader", why)

    def test_no_comparatives(self):
        spec = copy.deepcopy(self.spec["sv"])
        spec["first_year"] = True
        out = build(spec, self.dir / "first", keep_spec=False)
        self.assertIsNone(aa.check("ANNUAL-YEARS", out, {}, "first")[0])
        edit(out, " Detta är bolagets första räkenskapsår.", "")
        ok, why = aa.check("ANNUAL-YEARS", out, {}, "first")
        self.assertFalse(ok)
        self.assertIn("last year", why)

    def draft(self):
        """A company that gave this year's trial balance and two figures for last year (the timed run's case)."""
        return {
            "language": "sv",
            "company": {"name": "Exempel Konsult AB", "org_number": "556000-4105", "seat": "Uppsala"},
            "year": {"start": "2025-01-01", "end": "2025-12-31"},
            "prior": {"start": "2024-01-01", "end": "2024-12-31"},
            "unknown": ["prior", "report.events", "signing.date"],
            "report": {"business": "Bolaget bedriver IT-konsulttjänster.",
                       "earlier_years": [{"year": "2024", "net_sales": 1612000, "result_after_financial": 302000}]},
            "income": {"net_sales": [1846000, None], "other_external": [-182400, None],
                       "personnel": [-1132800, None], "depreciation": [-12800, None],
                       "interest_expense": [-1200, None], "tax": [-101100, None]},
            "balance": {"trade_receivables": [186000, None], "cash": [412300, None], "share_capital": [25000, None],
                        "retained": [100900, None], "trade_payables": [38200, None],
                        "tax_liabilities": [21400, None], "st_other": [35500, None]},
            "fixed_assets": {"equipment": {"opening_cost": [64000, None], "opening_depreciation": [-12800, None],
                                           "depreciation": [-12800, None]}},
            "disposition": {"dividend": 150000},
            "principles": ["Inventarier skrivs av linjärt över fem år."],
            "employees": 2, "pledged": [], "contingent": [],
            "signing": {"place": "Uppsala", "board": [{"name": "Lena Exempelsson", "role": "Styrelseordförande"},
                                                      {"name": "Per Prov", "role": "Styrelseledamot"}]},
        }

    def test_a_draft_leaves_what_the_company_has_not_given_empty(self):
        out = build(self.draft(), self.dir / "draft")
        got = results(out)
        self.assertEqual([r for r, (ok, _) in got.items() if ok is False], [])
        for rule in ("ANNUAL-YEARS", "ANNUAL-SIGNED"):
            self.assertTrue(got[rule][0] and got[rule][1].startswith("WARN "), got[rule])
        with zipfile.ZipFile(out) as z:
            text = z.read("word/document.xml").decode("utf-8")
        self.assertIn("Uppsala den ____", text)
        self.assertNotIn("Inga väsentliga händelser", text)
        self.assertIn("1\u00a0612\u00a0000", text)        # last year's net sales, in the multi-year overview

    def test_a_draft_never_mixes_a_known_last_year_into_an_unknown_one(self):
        spec = self.draft()
        spec["income"]["net_sales"] = [1846000, 1612000]
        (self.dir / "mixed").mkdir()
        (self.dir / "mixed" / "spec.json").write_text(json.dumps(spec))
        run = subprocess.run([sys.executable, str(PACK / "scripts" / "annual_create.py"),
                              str(self.dir / "mixed" / "spec.json"), str(self.dir / "mixed" / "report.docx")],
                             capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("income.net_sales", run.stderr)
        self.assertIn("report.earlier_years", run.stderr)

    def test_a_date_not_declared_unknown_is_still_needed(self):
        spec = self.draft()
        spec["unknown"] = ["prior"]
        (self.dir / "dated").mkdir()
        (self.dir / "dated" / "spec.json").write_text(json.dumps(spec))
        run = subprocess.run([sys.executable, str(PACK / "scripts" / "annual_create.py"),
                              str(self.dir / "dated" / "spec.json"), str(self.dir / "dated" / "report.docx")],
                             capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("signing.date", run.stderr)

    def test_missing_signatures_and_org_number(self):
        out = build(self.spec["sv"], self.dir / "sign", keep_spec=False)
        edit(out, ">Underskrifter<", ">Slutligen<")
        edit(out, "556000-0000", "556000")
        failing = self.failing(out)
        self.assertIn("ANNUAL-SIGNED", failing)
        self.assertIn("ANNUAL-PARTS", failing)

    def test_part_not_on_its_own_page(self):
        out = build(self.spec["sv"], self.dir / "pages", keep_spec=False)
        self.assertTrue(aa.check("ANNUAL-PAGES", out, {}, "first")[0])
        with zipfile.ZipFile(out) as z:
            xml = z.read("word/document.xml").decode()
        at = xml.index(">Noter<")
        start = xml.rindex("<w:pageBreakBefore/>", 0, at)
        edit(out, xml[start:at], xml[start:at].replace("<w:pageBreakBefore/>", "", 1))
        ok, why = aa.check("ANNUAL-PAGES", out, {}, "first")
        self.assertFalse(ok)
        self.assertIn("the notes", why)

    def test_header_numbers_and_minus(self):
        out = build(self.spec["en"], self.dir / "look", keep_spec=False)
        with zipfile.ZipFile(out) as z:
            header = " ".join(z.read(n).decode() for n in z.namelist() if n.startswith("word/header"))
            body = z.read("word/document.xml").decode()
        self.assertIn("NUMPAGES", header)
        self.assertIn("556000-0001", header)
        self.assertIn("\u2212173,600", body)
        self.assertNotIn(">-173", body)

    def test_decimals_and_units(self):
        out = build(self.spec["en"], self.dir / "units", keep_spec=False)
        edit(out, "All amounts are in whole Swedish kronor (SEK) unless otherwise stated.", "")
        ok, why = aa.check("ANNUAL-AMOUNTS", out, {}, "first")
        self.assertFalse(ok)
        self.assertIn("unit", why)


if __name__ == "__main__":
    unittest.main()
