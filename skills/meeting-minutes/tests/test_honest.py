"""Depth 4, minutes: nothing the data file gives is dropped. An unknown key, a value of the wrong shape and a
key these minutes have no line for stop the build by name (skills/_shared/spec_guard.py, spec.fields.json);
facts about the meeting with no field of their own print before the first item; who abstained, a unanimous
decision and the previous minutes in the person's own words are printed, not left off. A house rule on the
builder's own input. Needs python-docx."""
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


BUILDER = "scripts/minutes_create.py"
sys.path.insert(0, str(HERE / "scripts"))
import minutes_create as mk  # noqa: E402


def board():
    data = spec("board-minutes-uk.spec.json")
    return copy.deepcopy(data)


class NothingDropped(unittest.TestCase):
    def test_every_starter_passes_the_guard(self):
        fields = spec_guard.load_fields(HERE / "spec.fields.json")
        for p in sorted((HERE / "templates").glob("*.json")):
            self.assertEqual(spec_guard.problems(json.loads(p.read_text()), fields), [], p.name)

    def test_every_starter_gives_nothing_its_language_has_no_line_for(self):
        for p in sorted((HERE / "templates").glob("*.json")):
            self.assertEqual(mk.not_printed(json.loads(p.read_text())), [], p.name)

    def test_an_unknown_key_fails_with_its_name_and_where_it_can_go(self):
        # The measured run's own keys: every agenda heading printed and nothing under any of them.
        data = board()
        data["items"][0] = {"title": "Management accounts", "description": "Revenue 2,460,000 pounds year to date.",
                            "resolution": "It was resolved to note the accounts."}
        data["apologies"] = ["Ian Cole"]
        rc, said, out = run(BUILDER, data, "minutes.docx")
        self.assertNotEqual(rc, 0)
        self.assertIn('unknown key "items[0].description"', said)
        self.assertIn('the item\'s "notes"', said)
        self.assertIn('unknown key "items[0].resolution"', said)
        self.assertIn('"decisions"', said)
        self.assertIn('unknown key "apologies"', said)
        self.assertIn('"absent"', said)
        self.assertFalse(out.exists(), "nothing is built on an error")

    def test_a_string_in_a_list_field_fails(self):
        data = board()
        data["present"] = "Margaret Hale, David Osei, Ruth Finch"
        rc, said, out = run(BUILDER, data, "minutes.docx")
        self.assertNotEqual(rc, 0)
        self.assertIn('"present" is one string', said)
        self.assertFalse(out.exists())

    def test_the_free_lines_print_before_the_first_item(self):
        data = board()
        data["notes"] = ["Notice of the meeting had been given to all directors.", "The quorum is two directors."]
        rc, said, out = run(BUILDER, data, "minutes.docx")
        self.assertEqual(rc, 0, said)
        text = words(out)
        self.assertIn("Notice of the meeting had been given to all directors.", text)
        self.assertLess(text.index("The quorum is two directors."), text.index(data["items"][0]["title"]))

    def test_an_items_notes_may_be_paragraphs(self):
        data = board()
        data["items"][0]["notes"] = ["Three bids were received.", "The lowest compliant bid was 64,800 pounds."]
        rc, said, out = run(BUILDER, data, "minutes.docx")
        self.assertEqual(rc, 0, said)
        self.assertIn("The lowest compliant bid was 64,800 pounds.", words(out))

    def test_the_previous_minutes_in_the_persons_words_are_printed(self):
        data = board()
        data["previous_minutes"] = "The minutes of the meeting of 10 September 2026 were approved and signed by the chair."
        rc, said, out = run(BUILDER, data, "minutes.docx")
        self.assertEqual(rc, 0, said)
        self.assertIn("10 September 2026 were approved and signed by the chair", words(out))

    def test_who_abstained_is_named(self):
        data = board()
        data["items"][0]["decisions"] = [{"text": "that the bid of Example Cleaning Machines Ltd be accepted",
                                          "for": ["Margaret Hale", "Ruth Finch"], "abstained": ["David Osei"]}]
        rc, said, out = run(BUILDER, data, "minutes.docx")
        self.assertEqual(rc, 0, said)
        self.assertIn("Abstained: David Osei.", words(out))

    def test_a_unanimous_decision_says_so_in_every_language(self):
        for loc, w in mk.WORDS.items():
            self.assertTrue(w.get("unanimous"), loc)
            self.assertTrue(w.get("voted_abstained"), loc)
        data = board()
        data["items"][0]["decisions"] = [{"text": "that the accounts be approved", "unanimous": True}]
        rc, said, out = run(BUILDER, data, "minutes.docx")
        self.assertEqual(rc, 0, said)
        self.assertIn("The resolution was passed unanimously.", words(out))

    def test_a_key_these_minutes_have_no_line_for_is_an_error(self):
        data = board()
        data["convened"] = {"date": "2026-10-01", "how": "by e-mail to every director"}       # Spain's field
        rc, said, out = run(BUILDER, data, "minutes.docx")
        self.assertNotEqual(rc, 0)
        self.assertIn('"convened" has no line in en-GB minutes', said)
        self.assertIn('"notes"', said)
        self.assertFalse(out.exists())

    def test_a_danish_general_meeting_prints_the_shareholders_it_is_given(self):
        data = spec("generalforsamling-dk.spec.json")
        rc, said, out = run(BUILDER, data, "protokol.docx")
        self.assertEqual(rc, 0, said)
        text = words(out)
        for row in data["shareholders"]:
            self.assertIn(row["name"], text)


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
    """MINUTES-EMPTY, a house rule: a heading with nothing under it fails."""

    def test_every_starter_has_something_under_every_item(self):
        for p in sorted((HERE / "templates").glob("*.json")):
            rc, said, out = run(BUILDER, json.loads(p.read_text()), "minutes.docx")
            self.assertEqual(rc, 0, said)
            ok, why = thin("MINUTES-EMPTY", out)
            self.assertTrue(ok, "%s: %s" % (p.name, why))

    def test_headings_with_nothing_under_them_fail_by_name(self):
        # The measured run: every agenda heading and nothing under any of them, and a clean check.
        data = board()
        data["items"] = [{"title": "Declarations of interest"}, {"title": "Management accounts"},
                         {"title": "Interim dividend", "decisions": ["that an interim dividend of 0.40 pounds a share be paid"]}]
        rc, said, out = run(BUILDER, data, "minutes.docx")
        self.assertEqual(rc, 0, said)
        ok, why = thin("MINUTES-EMPTY", out)
        self.assertFalse(ok)
        self.assertIn("Declarations of interest", why)
        self.assertIn("Management accounts", why)
        self.assertNotIn("Interim dividend", why)
        self.assertIn("House rule", why)
        rc, said = packcheck("meeting-minutes", out)
        self.assertEqual(rc, 1)
        self.assertIn("FAIL MINUTES-EMPTY", said)

    def test_the_last_item_before_the_signatures_is_read_too(self):
        data = board()
        data["items"] = [{"title": "Management accounts", "notes": "Noted."}, {"title": "Next meeting"}]
        rc, said, out = run(BUILDER, data, "minutes.docx")
        self.assertEqual(rc, 0, said)
        ok, why = thin("MINUTES-EMPTY", out)
        self.assertFalse(ok)
        self.assertIn("Next meeting", why)

    def test_saying_in_words_that_nothing_was_decided_passes(self):
        data = board()
        data["items"] = [{"title": "Any other business", "notes": "No other business was raised and nothing was decided."}]
        rc, said, out = run(BUILDER, data, "minutes.docx")
        self.assertEqual(rc, 0, said)
        self.assertTrue(thin("MINUTES-EMPTY", out)[0])


# ---- item 4: the notes floor -----------------------------------------------------------------------------------
sys.path.insert(0, str(HERE.parent / "_checks"))
import notes_floor  # noqa: E402


def floor(path):
    return notes_floor.check("NOTES-FLOOR", Path(path), {"folder": ""}, "first")


def with_notes(builder, data, name, notes):
    """Build in a folder that also holds the person's notes, as a chat folder does."""
    rc, said, out = run(builder, data, name)
    assert rc == 0, said
    (out.parent / "notes.txt").write_text(notes)
    return out


MINUTES_NOTES = """Board meeting held on Thursday 8 October 2026 at 10:00. Closed at 11:25. Company number 09876543.
2. Minutes of the meeting of 10 September 2026 approved and signed by the chair.
3. Management accounts to 30 September 2026: revenue 2,460,000 pounds year to date, operating profit 187,000 pounds.
4. Resolved to accept the bid of Example Cleaning Machines Ltd, 64,800 pounds excluding VAT.
"""


class NotesFloor(unittest.TestCase):
    """NOTES-FLOOR on minutes: the dates and amounts the notes hold and the minutes do not."""

    def test_minutes_that_leave_the_figures_out_are_asked_about_them(self):
        data = board()
        data["date"], data["start"], data["end"] = "2026-10-08", "10:00", "11:25"
        data["items"] = [{"title": "Management accounts", "notes": "The accounts were noted."},
                         {"title": "Equipment tender", "decisions": ["that the bid of Example Cleaning Machines Ltd be accepted"]}]
        out = with_notes(BUILDER, data, "minutes.docx", MINUTES_NOTES)
        ok, why = floor(out)
        self.assertTrue(ok, "a question, never a fail")
        self.assertTrue(why.startswith("WARN "), why)
        for token in ("10 September 2026", "30 September 2026", "2,460,000", "187,000", "64,800"):
            self.assertIn("«%s»" % token, why)
        self.assertNotIn("8 October 2026", why)

    def test_minutes_that_record_them_have_no_question(self):
        data = board()
        data["date"], data["start"], data["end"] = "2026-10-08", "10:00", "11:25"
        data["previous_minutes"] = "The minutes of the meeting of 10 September 2026 were approved and signed by the chair."
        data["items"] = [{"title": "Management accounts", "notes": "The management accounts to 30 September 2026 were noted: "
                          "revenue 2,460,000 pounds year to date and operating profit 187,000 pounds."},
                         {"title": "Equipment tender", "decisions": ["that the bid of Example Cleaning Machines Ltd, 64,800 pounds excluding VAT, be accepted"]}]
        out = with_notes(BUILDER, data, "minutes.docx", MINUTES_NOTES)
        ok, why = floor(out)
        self.assertTrue(ok)
        self.assertFalse(why.startswith("WARN"), why)


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
        self.refused(BUILDER, board(), "made-beside-the-pack.docx")

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
    """One company file: minutes name the company and its register number from it."""

    def test_the_minutes_take_the_company_and_its_number_from_the_company_file(self):
        data = board()
        data.pop("body")
        data.pop("company_number", None)
        own = {"name": "Example Analytics Ltd", "country": "GB", "register_number": "01234567"}
        rc, said, out = in_company_folder(BUILDER, data, "minutes.docx", own)
        self.assertEqual(rc, 0, said)
        text = words(out)
        self.assertIn("Example Analytics Ltd", text)
        self.assertIn("01234567", text)
        ok, why = company_rule(out)
        self.assertTrue(ok, why)

    def test_minutes_with_another_number_stop_the_build(self):
        data = board()
        data["body"], data["company_number"] = "Example Analytics Ltd", "07654321"
        own = {"name": "Example Analytics Ltd", "country": "GB", "register_number": "01234567"}
        rc, said, out = in_company_folder(BUILDER, data, "minutes.docx", own)
        self.assertNotEqual(rc, 0)
        self.assertIn("company_number", said)
        self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
