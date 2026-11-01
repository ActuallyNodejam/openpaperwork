"""Depth 4, employment statements: nothing the data file gives is dropped. An unknown key, a value of the wrong
shape and an item the chosen law's list has no heading for stop the build by name (skills/_shared/spec_guard.py,
spec.fields.json); a term with no field of its own prints under a last heading, and the employer's further
particulars with the parties. A house rule on the builder's own input. Needs python-docx."""
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


BUILDER = "scripts/statement_create.py"
sys.path.insert(0, str(HERE / "scripts"))
import statement_create as sc  # noqa: E402


class NothingDropped(unittest.TestCase):
    def test_every_starter_passes_the_guard(self):
        fields = spec_guard.load_fields(HERE / "spec.fields.json")
        for p in sorted((HERE / "templates").glob("*.json")):
            self.assertEqual(spec_guard.problems(json.loads(p.read_text()), fields), [], p.name)

    def test_every_starter_gives_nothing_its_law_has_no_heading_for(self):
        for p in sorted((HERE / "templates").glob("*.json")):
            data = json.loads(p.read_text())
            self.assertEqual(sc.not_printed(data, sc.law_of(data)), [], p.name)

    def test_an_unknown_key_fails_with_its_name_and_where_it_can_go(self):
        data = spec("statement-uk.spec.json")
        data["salary"] = "GBP 13.00 an hour"
        data["employer"]["registered_office"] = "12 Sample Square, Manchester M1 1AA"
        rc, said, out = run(BUILDER, data, "statement.docx")
        self.assertNotEqual(rc, 0)
        self.assertIn('unknown key "salary"', said)
        self.assertIn('"pay"', said)
        self.assertIn('unknown key "employer.registered_office"', said)
        self.assertIn('"employer.further"', said)
        self.assertFalse(out.exists(), "nothing is built on an error")

    def test_a_string_in_a_list_field_fails(self):
        data = spec("statement-uk.spec.json")
        data["further"] = "A company car is provided."
        rc, said, out = run(BUILDER, data, "statement.docx")
        self.assertNotEqual(rc, 0)
        self.assertIn('"further" is one string', said)
        self.assertFalse(out.exists())

    def test_an_amount_given_as_text_fails(self):
        data = spec("statement-uk.spec.json")
        data["pay"]["amount"] = "13.00"
        rc, said, _ = run(BUILDER, data, "statement.docx")
        self.assertNotEqual(rc, 0)
        self.assertIn('"pay.amount"', said)

    def test_the_further_lines_print_under_a_last_heading(self):
        data = spec("statement-uk.spec.json")
        data["further"] = ["A company car is provided for business use"]
        data["employer"]["further"] = ["Registered office: 12 Sample Square, Manchester M1 1AA"]
        rc, said, out = run(BUILDER, data, "statement.docx")
        self.assertEqual(rc, 0, said)
        text = words(out)
        self.assertIn("Further particulars", text)
        self.assertIn("A company car is provided for business use.", text)
        self.assertIn("Registered office: 12 Sample Square, Manchester M1 1AA", text)
        self.assertLess(text.index("Further particulars"), text.index("Signatures"))

    def test_the_last_heading_has_words_in_every_language(self):
        for lang in sc.WORDS:
            self.assertIn(lang, sc.FURTHER_HEAD, lang)

    def test_an_item_the_law_has_no_heading_for_is_an_error(self):
        data = spec("statement-uk.spec.json")
        data["breaks"] = "30 minutes unpaid after six hours"            # Norway's item
        rc, said, out = run(BUILDER, data, "statement.docx")
        self.assertNotEqual(rc, 0)
        self.assertIn('"breaks" has no heading in a statement under "law": "uk"', said)
        self.assertIn('"further"', said)
        self.assertFalse(out.exists())


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
    """EMPLOY-EMPTY, a house rule: a heading of the statement with nothing under it fails."""

    def test_every_starter_has_a_line_under_every_heading(self):
        for p in sorted((HERE / "templates").glob("*.json")):
            rc, said, out = run(BUILDER, json.loads(p.read_text()), "statement.docx")
            self.assertEqual(rc, 0, said)
            ok, why = thin("EMPLOY-EMPTY", out)
            self.assertTrue(ok, "%s: %s" % (p.name, why))

    def test_a_heading_alone_fails_by_name(self):
        from docx import Document
        rc, said, out = run(BUILDER, spec("statement-uk.spec.json"), "statement.docx")
        self.assertEqual(rc, 0, said)
        doc = Document(out)
        heads = [i for i, p in enumerate(doc.paragraphs) if p.style.name == "Heading 2"]
        target = doc.paragraphs[heads[3]].text
        for p in doc.paragraphs[heads[3] + 1:heads[4]]:
            p._element.getparent().remove(p._element)
        doc.save(out)
        ok, why = thin("EMPLOY-EMPTY", out)
        self.assertFalse(ok)
        self.assertIn(target[:30], why)
        self.assertIn("House rule", why)
        rc, said = packcheck("employment-statement", out)
        self.assertEqual(rc, 1)
        self.assertIn("FAIL EMPLOY-EMPTY", said)


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
        self.refused(BUILDER, spec("statement-uk.spec.json"), "made-beside-the-pack.docx")

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
    """One company file: a statement names the employer, its number and its address from it."""

    def test_the_statement_takes_the_employer_from_the_company_file(self):
        data = spec("statement-uk.spec.json")
        own = {"name": data["employer"]["name"], "country": "GB", "register_number": "01234567",
               "street": "12 Sample Square", "postcode": "M1 1AA", "city": "Manchester"}
        data["employer"] = {k: v for k, v in data["employer"].items() if k not in ("number", "address")}
        rc, said, out = in_company_folder(BUILDER, data, "statement.docx", own)
        self.assertEqual(rc, 0, said)
        text = words(out)
        self.assertIn("01234567", text)
        self.assertIn("12 Sample Square, M1 1AA Manchester", text)
        ok, why = company_rule(out)
        self.assertTrue(ok, why)


if __name__ == "__main__":
    unittest.main()
