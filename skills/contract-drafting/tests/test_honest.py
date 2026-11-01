"""Depth 4, agreements, reviews and redlines: nothing the data file gives is dropped. An unknown key, a value of
the wrong shape and a term the chosen standard's Cover Page does not have stop the build by name
(skills/_shared/spec_guard.py; spec.fields.json, review.fields.json, redline.fields.json). What the parties
agreed beyond the Cover Page prints under its modifications. A house rule on the builder's own input. Needs
python-docx."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent / "_shared"))
import spec_guard  # noqa: E402


def spec(name):
    return json.loads((HERE / "templates" / name).read_text())


def run(builder, data, out_name, *extra):
    """Build in a folder of its own, the data file beside the output as a chat folder holds both.
    Returns (exit code, what the builder printed, the output path)."""
    folder = Path(tempfile.mkdtemp())
    (folder / "spec.json").write_text(json.dumps(data, ensure_ascii=False))
    r = subprocess.run([sys.executable, str(HERE / builder), str(folder / "spec.json"), str(folder / out_name), *extra],
                       capture_output=True, text=True, cwd=folder)
    return r.returncode, r.stdout + r.stderr, folder / out_name


def words(path):
    """Every word a Word file shows: body, tables, headers and footers."""
    import re
    out = []
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if re.match(r"word/(document|header\d*|footer\d*)\.xml$", name):
                xml = z.read(name).decode("utf-8", "replace")
                xml = re.sub(r"</w:p>", "\n", xml)
                out.append(re.sub(r"<[^>]+>", "", xml))
    return "\n".join(out).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')


BUILDER = "scripts/agreement_create.py"


def nda():
    data = spec("nda.spec.json")
    data["governing_law"], data["courts"] = "the laws of Sweden", "the general courts of Sweden"
    return data


class NothingDropped(unittest.TestCase):
    def test_every_starter_passes_the_guard(self):
        for fields, names in (("spec.fields.json", ("nda.spec.json", "dpa.spec.json", "csa.spec.json")),
                              ("review.fields.json", ("review.example.json",)),
                              ("redline.fields.json", ("redline.example.json",))):
            known = spec_guard.load_fields(HERE / fields)
            for name in names:
                self.assertEqual(spec_guard.problems(spec(name), known), [], name)

    def test_an_unknown_key_fails_with_its_name_and_where_it_can_go(self):
        data = nda()
        data["parties"][0]["vat_id"] = "SE556677889901"
        data["non_solicit"] = "Neither party hires the other's staff for twelve months."
        rc, said, out = run(BUILDER, data, "nda.docx")
        self.assertNotEqual(rc, 0)
        self.assertIn('unknown key "parties[0].vat_id"', said)
        self.assertIn('"registration"', said)
        self.assertIn('unknown key "non_solicit"', said)
        self.assertIn('"modifications"', said)
        self.assertFalse(out.exists(), "nothing is built on an error")

    def test_a_string_in_a_list_field_fails(self):
        data = nda()
        data["modifications"] = "Clause 5 does not apply."
        rc, said, out = run(BUILDER, data, "nda.docx")
        self.assertNotEqual(rc, 0)
        self.assertIn('"modifications" is one string', said)
        self.assertFalse(out.exists())

    def test_a_term_the_cover_page_does_not_have_fails_by_name(self):
        data = nda()
        data["terms"]["Non-Solicitation Period"] = "twelve months"
        rc, said, out = run(BUILDER, data, "nda.docx")
        self.assertNotEqual(rc, 0)
        self.assertIn('"Non-Solicitation Period"', said)
        self.assertIn("modifications", said)
        self.assertFalse(out.exists())

    def test_what_the_parties_agreed_beyond_the_cover_page_prints(self):
        data = nda()
        data["modifications"] = ["Neither party hires the other's staff for twelve months after the Effective Date."]
        rc, said, out = run(BUILDER, data, "nda.docx")
        self.assertEqual(rc, 0, said)
        self.assertIn("Neither party hires the other's staff for twelve months", words(out).replace("&apos;", "'"))

    def test_a_review_and_a_redline_refuse_an_unknown_key(self):
        for builder, name, key in (("scripts/review_create.py", "review.example.json", "overall"),
                                   ("scripts/redline_create.py", "redline.example.json", "reason")):
            data = spec(name)
            data[key] = "fine to sign"
            rc, said, _ = run(builder, data, "out.docx")
            self.assertNotEqual(rc, 0, builder)
            self.assertIn('unknown key "%s"' % key, said, builder)


# ---- item 2: thin pages fail -----------------------------------------------------------------------------------
sys.path.insert(0, str(HERE.parent / "_checks"))
import thin_pages  # noqa: E402


def thin(rule, path):
    return thin_pages.check(rule, path, {"folder": ""}, "first")


def packcheck(skill, path):
    r = subprocess.run([sys.executable, str(HERE.parent / "_checks" / "packcheck.py"), skill, str(path)],
                       capture_output=True, text=True, cwd=Path(path).parent)
    return r.returncode, r.stdout + r.stderr


class ThinPages(unittest.TestCase):
    """LEGAL-EMPTY, a house rule: a heading of the agreement with nothing under it fails."""

    def test_the_standard_agreements_have_text_under_every_heading(self):
        rc, said, out = run(BUILDER, nda(), "nda.docx")
        self.assertEqual(rc, 0, said)
        ok, why = thin("LEGAL-EMPTY", out)
        self.assertTrue(ok, why)

    def test_a_clause_heading_alone_fails_by_name(self):
        from docx import Document
        rc, said, out = run(BUILDER, nda(), "nda.docx")
        self.assertEqual(rc, 0, said)
        doc = Document(out)
        doc.add_heading("Non-solicitation", level=2)
        doc.save(out)
        ok, why = thin("LEGAL-EMPTY", out)
        self.assertFalse(ok)
        self.assertIn("Non-solicitation", why)
        self.assertIn("House rule", why)


# ---- item 6: the file lands in the person's folder -------------------------------------------------------------
import os as _os  # noqa: E402
import re as _re6  # noqa: E402


class InThePersonsFolder(unittest.TestCase):
    """A house rule on the builders: an output path inside the library's own folder is refused, and the message
    names the working folder; every example in SKILL.md runs the builder from the working folder."""

    def refused(self, builder, data, name):
        folder = Path(tempfile.mkdtemp())
        (folder / "spec.json").write_text(json.dumps(data, ensure_ascii=False))
        target = HERE / "templates" / name                         # beside the pack, where nobody looks
        env = dict(_os.environ, CLAUDE_PROJECT_DIR=str(folder))
        env.pop("OLDPWD", None)
        r = subprocess.run([sys.executable, str(HERE / builder), str(folder / "spec.json"), str(target)],
                           capture_output=True, text=True, cwd=HERE / "templates", env=env)
        try:
            said = r.stdout + r.stderr
            self.assertNotEqual(r.returncode, 0, builder)
            self.assertIn("inside the library's own folder", said, builder)
            self.assertIn(str(folder.resolve()), said, "the working folder is named")
            self.assertFalse(target.exists(), "nothing is written beside the pack")
        finally:
            if target.exists():
                target.unlink()

    def test_an_output_path_inside_the_library_is_refused_and_the_working_folder_named(self):
        self.refused(BUILDER, nda(), "made-beside-the-pack.docx")

    def test_every_example_in_skill_md_runs_the_builder_from_the_working_folder(self):
        text = (HERE / "SKILL.md").read_text()
        runs = _re6.findall(r"python3? [^\n`]*?(?:_create|build_page)\.py[^\n`]*", text)
        self.assertTrue(runs)
        for line in runs:
            self.assertRegex(line, r"^python3 <skill folder>/(scripts|page)/", line)
        self.assertIn("Work in the working folder", text)


# ---- item 7: a company's facts are written once ---------------------------------------------------------------
sys.path.insert(0, str(HERE.parent / "_checks"))
import company  # noqa: E402
import company_check  # noqa: E402

COMPANY = {"name": "Exempel Tryck AB", "street": "Verkstadsgatan 7", "postcode": "417 07", "city": "Göteborg",
           "country": "SE", "vat_id": "SE556677889901", "register_number": "556677-8899",
           "registered_office": "Göteborg", "email": "order@exempeltryck.example", "phone": "031-000 00 00",
           "payment": {"bank": "Exempelbanken", "iban": "SE35 5000 0000 0549 1000 0003", "bic": "ESSESESS"}}


def in_company_folder(builder, data, name, company_file=None):
    """Build in a folder that holds the company file, as the person's folder does."""
    folder = Path(tempfile.mkdtemp())
    (folder / "company.json").write_text(json.dumps(company_file or COMPANY, ensure_ascii=False))
    (folder / "spec.json").write_text(json.dumps(data, ensure_ascii=False))
    r = subprocess.run([sys.executable, str(HERE / builder), str(folder / "spec.json"), str(folder / name)],
                       capture_output=True, text=True, cwd=folder)
    return r.returncode, r.stdout + r.stderr, folder / name


def company_rule(path):
    return company_check.check("COMPANY-FILE", Path(path), {"folder": ""}, "first")


class CompanyFile(unittest.TestCase):
    """One company file: an agreement names the company's registration and address from it."""

    def test_the_agreement_takes_its_own_party_from_the_company_file(self):
        data = nda()
        own = {"name": data["parties"][0]["name"], "country": "SE", "register_number": data["parties"][0]["registration"],
               "street": "Verkstadsgatan 7", "postcode": "417 07", "city": "Gothenburg"}
        data["parties"][0] = {k: v for k, v in data["parties"][0].items() if k not in ("registration", "address")}
        rc, said, out = in_company_folder(BUILDER, data, "nda.docx", own)
        self.assertEqual(rc, 0, said)
        text = words(out)
        self.assertIn(own["register_number"], text)
        self.assertIn("Verkstadsgatan 7, 417 07 Gothenburg", text)

    def test_an_agreement_with_another_registration_stops_the_build(self):
        data = nda()
        own = {"name": data["parties"][0]["name"], "country": "SE", "register_number": "559999-0000"}
        rc, said, out = in_company_folder(BUILDER, data, "nda.docx", own)
        self.assertNotEqual(rc, 0)
        self.assertIn("registration", said)
        self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
