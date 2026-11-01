"""Depth 4, annual accounts: nothing the data file gives is dropped. An unknown key, a value of the wrong shape
and a line the income statement or balance sheet does not have stop the build by name
(skills/_shared/spec_guard.py, spec.fields.json). A house rule on the builder's own input. Needs python-docx."""
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


BUILDER = "scripts/annual_create.py"


def first():
    return spec(sorted(p.name for p in (HERE / "templates").glob("*.json"))[0])


class NothingDropped(unittest.TestCase):
    def test_every_starter_passes_the_guard(self):
        fields = spec_guard.load_fields(HERE / "spec.fields.json")
        for p in sorted((HERE / "templates").glob("*.json")):
            self.assertEqual(spec_guard.problems(json.loads(p.read_text()), fields), [], p.name)

    def test_an_unknown_key_fails_with_its_name_and_where_it_can_go(self):
        data = first()
        data["going_concern"] = "The board sees no doubt about the company's ability to continue."
        rc, said, out = run(BUILDER, data, "report.docx")
        self.assertNotEqual(rc, 0)
        self.assertIn('unknown key "going_concern"', said)
        self.assertIn('"notes"', said)
        self.assertFalse(out.exists(), "nothing is built on an error")

    def test_a_string_in_a_list_field_fails(self):
        data = first()
        data["principles"] = "Inventarier skrivs av linjärt över fem år."
        rc, said, out = run(BUILDER, data, "report.docx")
        self.assertNotEqual(rc, 0)
        self.assertIn('"principles" is one string', said)
        self.assertFalse(out.exists())

    def test_a_line_the_layout_does_not_have_fails_by_name(self):
        data = first()
        data["income"]["bank_fees"] = [-1200, -900]
        rc, said, out = run(BUILDER, data, "report.docx")
        self.assertNotEqual(rc, 0)
        self.assertIn('"income.bank_fees" is not a line of the income statement', said)
        self.assertFalse(out.exists())

    def test_a_free_note_prints(self):
        data = first()
        data["notes"] = list(data.get("notes") or []) + [{"title": "Leasing", "text": "The company leases two vans until 2028."}]
        rc, said, out = run(BUILDER, data, "report.docx")
        self.assertEqual(rc, 0, said)
        self.assertIn("The company leases two vans until 2028.", words(out))


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
        self.refused(BUILDER, first(), "made-beside-the-pack.docx")

    def test_every_example_in_skill_md_runs_the_builder_from_the_working_folder(self):
        text = (HERE / "SKILL.md").read_text()
        runs = _re6.findall(r"python3? [^\n`]*?(?:_create|build_page)\.py[^\n`]*", text)
        self.assertTrue(runs)
        for line in runs:
            self.assertRegex(line, r"^python3 <skill folder>/(scripts|page)/", line)
        self.assertIn("Work in the working folder", text)


if __name__ == "__main__":
    unittest.main()
