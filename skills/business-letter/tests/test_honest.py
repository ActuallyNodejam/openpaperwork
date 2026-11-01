"""Depth 4, letters: nothing the data file gives is dropped. An unknown key and a value of the wrong shape stop
the build by name (skills/_shared/spec_guard.py, spec.fields.json), and the sender's further particulars print
in the footer. A house rule on the builder's own input, not a rule taken from a standard. Needs python-docx."""
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


BUILDER = "scripts/letter_create.py"


class NothingDropped(unittest.TestCase):
    def test_every_starter_passes_the_guard(self):
        fields = spec_guard.load_fields(HERE / "spec.fields.json")
        for p in sorted((HERE / "templates").glob("*.json")):
            self.assertEqual(spec_guard.problems(json.loads(p.read_text()), fields), [], p.name)

    def test_an_unknown_key_fails_with_its_name_and_where_it_can_go(self):
        data = spec("letter.spec.json")
        data["sender"]["registry_court"] = "Amtsgericht Mannheim"
        rc, said, out = run(BUILDER, data, "letter.docx")
        self.assertNotEqual(rc, 0)
        self.assertIn('unknown key "sender.registry_court"', said)
        self.assertIn('"sender.further"', said)
        self.assertFalse(out.exists(), "nothing is built on an error")

    def test_a_near_miss_names_the_key_that_was_meant(self):
        data = spec("letter.spec.json")
        data["sender"]["register_no"] = "HRB 123456"
        rc, said, _ = run(BUILDER, data, "letter.docx")
        self.assertNotEqual(rc, 0)
        self.assertIn("Did you mean", said)
        self.assertIn('"sender.register_number"', said)

    def test_a_string_in_a_list_field_fails(self):
        data = spec("letter.spec.json")
        data["body"] = "One paragraph given as a string, which would print one letter a line."
        rc, said, out = run(BUILDER, data, "letter.docx")
        self.assertNotEqual(rc, 0)
        self.assertIn('"body" is one string', said)
        self.assertFalse(out.exists())

    def test_a_recipients_email_is_not_silently_left_off(self):
        data = spec("letter.spec.json")
        data["recipient"]["email"] = "office@beispiel-druck.example"
        rc, said, _ = run(BUILDER, data, "letter.docx")
        self.assertNotEqual(rc, 0)
        self.assertIn('unknown key "recipient.email"', said)
        self.assertIn('"body"', said)

    def test_the_further_particulars_line_prints(self):
        for name in ("letter.spec.json", "letter-uk.spec.json"):        # DIN 5008 and a window letter
            data = spec(name)
            data["sender"]["further"] = ["Member of the Example Trade Association, no. 4471"]
            rc, said, out = run(BUILDER, data, "letter.docx")
            self.assertEqual(rc, 0, said)
            self.assertIn("Member of the Example Trade Association, no. 4471", words(out), name)

    def test_a_comment_key_is_let_through_and_never_printed(self):
        data = spec("letter.spec.json")
        data["_note"] = "ask Karin for the reference"
        rc, said, out = run(BUILDER, data, "letter.docx")
        self.assertEqual(rc, 0, said)
        self.assertNotIn("ask Karin", words(out))


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
    """LETTER-EMPTY, a house rule: a letter with no body, or to a town alone, fails."""

    def test_every_starter_has_a_body_and_a_whole_address(self):
        for p in sorted((HERE / "templates").glob("*.json")):
            rc, said, out = run(BUILDER, json.loads(p.read_text()), "letter.docx")
            self.assertEqual(rc, 0, said)
            ok, why = thin("LETTER-EMPTY", out)
            self.assertTrue(ok, "%s: %s" % (p.name, why))

    def test_an_address_holding_only_the_town_fails(self):
        # The measured run: the address window held "Mannheim" alone, and the check was clean.
        data = spec("letter.spec.json")
        data["recipient"] = {"name": data["recipient"]["name"], "city": "Mannheim", "country": "DE"}
        rc, said, out = run(BUILDER, data, "letter.docx")
        self.assertEqual(rc, 0, said)
        ok, why = thin("LETTER-EMPTY", out)
        self.assertFalse(ok)
        self.assertIn("the street and number", why)
        self.assertIn("the postcode", why)
        self.assertIn("Never make an address up", why)
        self.assertIn("House rule", why)
        rc, said = packcheck("business-letter", out)
        self.assertEqual(rc, 1)
        self.assertIn("FAIL LETTER-EMPTY", said)

    def test_an_empty_body_fails(self):
        data = spec("letter.spec.json")
        data["body"] = [" "]
        rc, said, out = run(BUILDER, data, "letter.docx")
        ok, why = thin("LETTER-EMPTY", out)
        self.assertFalse(ok)
        self.assertIn("no body", why)


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


LETTER_NOTES = """Brev som ska iväg i dag, 9 oktober 2026

Avsändare: Exempel Kontorsservice AB, Exempelgatan 8, 411 01 Göteborg. Org.nr 556012-3456.
Tel. 031-000 00 00, info@exempel-kontorsservice.example
Vår referens: KL-2026-31.

Det här ska stå:
- Den 2 oktober 2026 fick vi 60 kartonger. 14 kartonger var vattenskadade (14 av 60).
- Er faktura 90551 på 18 600,00 kr betalar vi senare; till dess håller vi inne 4 340,00 kr.
"""


def swedish_letter():
    data = spec("letter.spec.json")
    data["sender"].update({"name": "Exempel Kontorsservice AB", "street": "Exempelgatan 8", "postcode": "411 01",
                           "city": "Göteborg", "country": "SE", "register_number": "556012-3456",
                           "registered_office": "Göteborg", "phone": "031-000 00 00",
                           "email": "info@exempel-kontorsservice.example"})
    data["sender"].pop("vat_id", None)
    data["references"] = [{"kind": "ours", "value": "KL-2026-31"}]
    data["date"] = "2026-10-09"
    data["subject"], data["salutation"], data["closing"] = "Reklamation av leverans", "Hej Johan,", "Med vänlig hälsning"
    data.pop("enclosures", None)
    data.pop("contact", None)
    data["body"] = ["Den 2 oktober 2026 fick vi 60 kartonger, varav 14 var vattenskadade.",
                    "Er faktura 90551 på 18 600,00 kr betalar vi senare; till dess håller vi inne 4 340,00 kr."]
    return data


class NotesFloor(unittest.TestCase):
    """NOTES-FLOOR, a house rule: a question, never a fail. What the notes hold and the page does not; a token
    the page changes; a figure the page carries and the notes do not."""

    def test_a_letter_that_carries_every_hard_token_of_the_notes_has_no_question(self):
        out = with_notes(BUILDER, swedish_letter(), "brev.docx", LETTER_NOTES)
        ok, why = floor(out)
        self.assertTrue(ok)
        self.assertFalse(why.startswith("WARN"), why)

    def test_a_replaced_email_address_is_named_as_changed(self):
        # The measured run: a layout rule said the address ran 1 mm past the edge, and the agent made up a shorter one.
        data = swedish_letter()
        data["sender"]["email"] = "info@exempel.se"
        out = with_notes(BUILDER, data, "brev.docx", LETTER_NOTES)
        ok, why = floor(out)
        self.assertTrue(ok, "a question, never a fail")
        self.assertTrue(why.startswith("WARN "), why)
        self.assertIn("«info@exempel-kontorsservice.example» is «info@exempel.se» on the page", why)
        self.assertIn("never change a name, an address or a number", why)

    def test_what_the_notes_hold_and_the_page_does_not_is_listed(self):
        data = swedish_letter()
        data["references"] = []
        data["body"] = ["Vi reklamerar 14 av de 60 kartongerna."]
        out = with_notes(BUILDER, data, "brev.docx", LETTER_NOTES)
        ok, why = floor(out)
        self.assertTrue(ok)
        for token in ("KL-2026-31", "90551", "18 600,00", "4 340,00", "2 oktober 2026"):
            self.assertIn("«%s»" % token, why)
        self.assertIn("Put them on the page or say why not", why)

    def test_a_figure_on_the_page_that_is_not_in_the_notes_is_listed(self):
        data = swedish_letter()
        data["body"].append("Vi räknar med att 35 kartonger behöver bytas inom 21 dagar.")
        out = with_notes(BUILDER, data, "brev.docx", LETTER_NOTES)
        ok, why = floor(out)
        self.assertTrue(ok)
        self.assertIn("these figures are on the page and not in your notes", why)
        self.assertIn("«35»", why)
        self.assertIn("«21»", why)
        self.assertIn("Say where each comes from or take it out", why)

    def test_a_share_the_notes_state_in_words_is_not_a_made_up_figure(self):
        data = swedish_letter()
        data["body"].append("Det är 23 procent av leveransen.")           # 14 av 60
        out = with_notes(BUILDER, data, "brev.docx", LETTER_NOTES)
        ok, why = floor(out)
        self.assertNotIn("«23»", why)

    def test_it_does_not_run_when_the_folder_holds_no_notes(self):
        rc, said, out = run(BUILDER, swedish_letter(), "brev.docx")
        self.assertEqual(rc, 0, said)
        ok, why = floor(out)
        self.assertIsNone(ok)
        self.assertIn("no notes", why)

    def test_the_builders_own_data_file_is_never_read_as_a_note(self):
        data = swedish_letter()
        data["_note"] = "IBAN SE35 5000 0000 0549 1000 0003 is for another letter"
        out = with_notes(BUILDER, data, "brev.docx", LETTER_NOTES)
        ok, why = floor(out)
        self.assertNotIn("SE35", why)

    def test_the_pack_check_prints_it_as_a_warning_and_still_exits_clean(self):
        data = swedish_letter()
        data["sender"]["email"] = "info@exempel.se"
        out = with_notes(BUILDER, data, "brev.docx", LETTER_NOTES)
        rc, said = packcheck("business-letter", out)
        self.assertEqual(rc, 0, said)
        self.assertIn("WARN NOTES-FLOOR", said)
        self.assertNotIn("FAIL NOTES-FLOOR", said)

    def test_a_decks_made_up_figures_are_listed_and_its_stated_share_is_not(self):
        # The deck's real run of 2026-10-10: "16 weeks" and "15%" were nowhere in the notes; 71 is 41 of 58.
        notes = ("Complaints nearly doubled, mostly late deliveries (41 of 58 complaints in Q3).\n"
                 "Second packing line: costs GBP 480k once, ready March 2027, adds 60% capacity.\n")
        deck = {"title": "Board update", "pages": [
            {"type": "table", "rows": [["Late deliveries of all complaints", "71"]]},
            {"type": "timeline", "steps": [{"what": "Order placed", "detail": "Supplier lead time is 16 weeks"}]},
            {"type": "summary", "points": ["A Saturday shift adds 15% interim capacity", "The line costs GBP 480k"]}]}
        found = notes_floor.not_in_notes(deck, notes, "business-deck")
        self.assertIn("16 weeks", found)
        self.assertIn("15%", found)
        self.assertNotIn("71", found)
        self.assertNotIn("480", " ".join(found))


# ---- item 5: a layout rule never invites changing a fact -------------------------------------------------------
import re as _re  # noqa: E402

import packcheck as _pc  # noqa: E402


class LayoutMessages(unittest.TestCase):
    """A house rule on the checks' own words: the FAIL line of every rule about fit, width, a window, fill or the
    number of pages ends with what may change and with one sentence."""

    LAYOUT = _re.compile(r"WINDOW|DIN5008|BLOCK|-FIT$|-FILL$|OVERFLOW|OVERLAP|BOUNDS|-GRID$|^DECK-PAGES$")

    def test_every_rule_about_fit_width_window_fill_or_page_count_has_its_ending(self):
        named = {r for rules in _pc.SKILL_RULES.values() for r in rules if self.LAYOUT.search(r)}
        self.assertTrue(named)
        self.assertEqual(sorted(named - set(_pc.LAYOUT_RULES)), [], "a layout rule without its ending")

    def test_every_such_message_ends_with_what_may_change_and_the_sentence(self):
        for rule in _pc.LAYOUT_RULES:
            for evidence in ("the information block runs to 191.0 mm across (info@exempel-kontorsservice.example); "
                             "it ends on the text's right edge, 190 mm", "the address leaves the window."):
                text = _pc.layout_tail(rule, evidence)
                self.assertTrue(text.startswith(evidence.rstrip(".")), rule)
                self.assertIn("What may change:", text, rule)
                self.assertTrue(text.endswith("Never change a name, an address or a number to make it fit."), rule)
                self.assertEqual(_pc.layout_tail(rule, text), text, "said once")

    def test_a_rule_about_anything_else_is_left_as_it_is(self):
        self.assertEqual(_pc.layout_tail("LETTER-COMPANY", "the register number is missing"), "the register number is missing")

    def test_every_module_a_rule_is_routed_to_has_an_import_line_a_plugin_build_can_read(self):
        # A plugin carries the check modules found by reading packcheck's import lines; a name in a table is
        # not one, and a rule whose module the plugin lacks is skipped there without a word.
        source = (HERE.parent / "_checks" / "packcheck.py").read_text()
        for module in sorted(set(_pc.RULE_MODULES.values())):
            self.assertTrue((HERE.parent / "_checks" / (module + ".py")).is_file(), module)
            self.assertRegex(source, r"(?m)^\s*import " + module + r"\s*$", module)
            self.assertIs(_pc.shared_module(module), __import__(module))

    def test_the_pack_check_prints_it_on_a_real_failure(self):
        from docx import Document
        from docx.shared import Mm
        rc, said, out = run(BUILDER, spec("letter.spec.json"), "letter.docx")
        self.assertEqual(rc, 0, said)
        doc = Document(out)
        doc.sections[0].left_margin = Mm(10)                       # off DIN 5008's 25 mm edge
        doc.save(out)
        rc, said = packcheck("business-letter", out)
        self.assertEqual(rc, 1, said)
        line = next(l for l in said.splitlines() if l.startswith("FAIL LETTER-DIN5008"))
        self.assertTrue(line.endswith("Never change a name, an address or a number to make it fit."), line)
        self.assertIn("What may change:", line)


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
        self.refused(BUILDER, spec("letter.spec.json"), "made-beside-the-pack.docx")

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


def bare_letter():
    data = spec("letter.spec.json")
    data["sender"] = {"name": "Exempel Tryck AB"}
    data.pop("contact", None)
    return data


class CompanyFile(unittest.TestCase):
    """A house rule: company.json in the person's folder is the company's own record; every builder fills its
    sender from it and no page says anything else."""

    def test_the_letter_takes_what_its_data_file_leaves_out_from_the_company_file(self):
        rc, said, out = in_company_folder(BUILDER, bare_letter(), "brev.docx")
        self.assertEqual(rc, 0, said)
        self.assertIn("filled sender.street", said)
        text = words(out)
        for value in ("Verkstadsgatan 7", "SE556677889901", "556677-8899", "order@exempeltryck.example"):
            self.assertIn(value, text)
        ok, why = company_rule(out)
        self.assertTrue(ok, why)

    def test_a_data_file_that_says_something_else_stops_the_build(self):
        data = bare_letter()
        data["sender"]["vat_id"] = "SE556677889902"
        rc, said, out = in_company_folder(BUILDER, data, "brev.docx")
        self.assertNotEqual(rc, 0)
        self.assertIn('"sender.vat_id" is "SE556677889902" in the data file and "SE556677889901" in the company file', said)
        self.assertIn("never change a particular to make the two agree", said)
        self.assertFalse(out.exists())

    def test_a_page_that_changes_a_particular_fails_the_check(self):
        rc, said, out = in_company_folder(BUILDER, bare_letter(), "brev.docx")
        self.assertEqual(rc, 0, said)
        changed = json.loads((out.parent / "company.json").read_text())
        changed["register_number"] = "556677-8898"                    # the file now says another number than the page
        (out.parent / "company.json").write_text(json.dumps(changed, ensure_ascii=False))
        ok, why = company_rule(out)
        self.assertFalse(ok)
        self.assertIn("register number is 556677-8898 in the company file and the page does not carry it", why)
        rc, said = packcheck("business-letter", out)
        self.assertEqual(rc, 1)
        self.assertIn("FAIL COMPANY-FILE", said)

    def test_another_companys_letter_is_left_alone(self):
        rc, said, out = in_company_folder(BUILDER, spec("letter-uk.spec.json"), "brev.docx")
        self.assertEqual(rc, 0, said)
        self.assertNotIn("filled", said)
        ok, why = company_rule(out)
        self.assertIsNone(ok)
        self.assertIn("not the company", why)

    def test_without_a_company_file_nothing_changes(self):
        rc, said, out = run(BUILDER, spec("letter.spec.json"), "brev.docx")
        self.assertEqual(rc, 0, said)
        self.assertIsNone(company_rule(out)[0])

    def test_every_starters_own_sender_written_as_the_company_file_passes(self):
        fields = set(spec_guard.load_fields(HERE.parent / "_shared" / "company.fields.json")["fields"])
        for p in sorted((HERE / "templates").glob("*.json")):
            data = json.loads(p.read_text())
            own = {k: v for k, v in data["sender"].items() if k in fields}
            rc, said, out = in_company_folder(BUILDER, data, "letter.docx", own)
            self.assertEqual(rc, 0, "%s: %s" % (p.name, said))
            ok, why = company_rule(out)
            self.assertTrue(ok, "%s: %s" % (p.name, why))

    def test_the_file_is_made_once_and_says_what_the_law_still_wants(self):
        folder = Path(tempfile.mkdtemp())
        script = str(HERE.parent / "_shared" / "company.py")
        r = subprocess.run([sys.executable, script, "make", str(folder / "company.json"), "name=Beispiel Druck GmbH",
                            "country=DE", "street=Musterweg 4", "postcode=68159", "city=Mannheim"],
                           capture_output=True, text=True, cwd=folder)
        self.assertEqual(r.returncode, 0, r.stderr)
        made = json.loads(r.stdout)
        self.assertIn("register_number", made["still_wanted"])
        self.assertIn("Never make one up", made["say"])
        r = subprocess.run([sys.executable, script, "make", str(folder / "company.json"), "unknown=register_number",
                            "unknown=registered_office", "unknown=register", "unknown=managing_directors"],
                           capture_output=True, text=True, cwd=folder)
        self.assertEqual(json.loads(r.stdout)["still_wanted"], [], r.stdout)
        r = subprocess.run([sys.executable, script, "make", str(folder / "company.json"), "court=Amtsgericht Mannheim"],
                           capture_output=True, text=True, cwd=folder)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('unknown key "court"', r.stdout + r.stderr)


# ---- item 8: the sender's own company law ----------------------------------------------------------------------
sys.path.insert(0, str(HERE.parent / "_checks"))
import letter_check as _lc  # noqa: E402


def company_law(path):
    return _lc.check("LETTER-COMPANY", Path(path), {"folder": ""}, "first")


GMBH = {"name": "Beispiel Druck GmbH", "street": "Musterweg 4", "postcode": "68159", "city": "Mannheim", "country": "DE",
        "email": "kontakt@beispiel-druck.example"}


class SendersCompanyLaw(unittest.TestCase):
    """LETTER-COMPANY on a letter: what the sender's own company law asks its letters to state, by the article the
    invoice rule's table cites; the data file's "unknown" is the way out."""

    def letter_from(self, sender):
        data = spec("letter.spec.json")
        data["sender"] = sender
        data.pop("contact", None)
        rc, said, out = run(BUILDER, data, "brief.docx")
        self.assertEqual(rc, 0, said)
        return out

    def test_a_companys_letter_without_its_register_details_fails_with_the_article(self):
        # The measured run: a German letter left the register court off, and the check was clean.
        ok, why = company_law(self.letter_from(dict(GMBH)))
        self.assertFalse(ok)
        self.assertIn("GmbHG § 35a", why)
        for particular in ("registered_office", "register_number", "register", "managing_directors"):
            self.assertIn(particular, why)
        self.assertIn('"unknown"', why)
        self.assertIn("Never make one up", why)

    def test_a_letter_that_states_them_passes(self):
        sender = dict(GMBH, registered_office="Mannheim", register="Amtsgericht Mannheim", register_number="HRB 00000",
                      managing_directors=["Erika Beispiel"])
        ok, why = company_law(self.letter_from(sender))
        self.assertTrue(ok, why)
        self.assertFalse(str(why).startswith("WARN"), why)

    def test_a_particular_declared_unknown_is_a_warning_and_printed_as_nothing(self):
        sender = dict(GMBH, registered_office="Mannheim", register="Amtsgericht Mannheim", register_number="HRB 00000",
                      unknown=["managing_directors"])
        out = self.letter_from(sender)
        ok, why = company_law(out)
        self.assertTrue(ok, why)
        self.assertTrue(why.startswith("WARN "), why)
        self.assertIn("managing_directors", why)
        self.assertIn("say so in your reply", why)
        self.assertNotIn("unknown", words(out).lower())

    def test_every_starter_states_what_its_senders_law_asks(self):
        for p in sorted((HERE / "templates").glob("*.json")):
            rc, said, out = run(BUILDER, json.loads(p.read_text()), "letter.docx")
            self.assertEqual(rc, 0, said)
            ok, why = company_law(out)
            self.assertIn(ok, (True, None), "%s: %s" % (p.name, why))
            self.assertFalse(str(why).startswith("WARN"), "%s: %s" % (p.name, why))


# ---- item 9: one company, one footer ------------------------------------------------------------------------
class OneFooter(unittest.TestCase):
    """The letter writes the sender's own address as the company's invoice and trade document do."""

    def test_every_starters_footer_and_head_use_the_shared_own_address(self):
        sys.path.insert(0, str(HERE / "scripts"))
        import letter
        import letter_create
        import window_letter
        for p in sorted((HERE / "templates").glob("*.json")):
            data = json.loads(p.read_text())
            layout = letter.letter_layout(data)[1]
            lt = window_letter.WindowLetter(data) if layout else letter_create.Letter(data)
            sender = dict(data["sender"], country=data["sender"].get("country") or (layout or {}).get("country"))
            self.assertEqual(lt.footer()[0], letter.own_address(sender, data["recipient"].get("country")), p.name)
            head = lt.letterhead() if layout else lt.return_line()
            self.assertIn(letter.town_line(sender), head, p.name)

    def test_a_british_letter_writes_its_town_line_one_way(self):
        rc, said, out = run(BUILDER, spec("letter-uk.spec.json"), "letter.docx")
        self.assertEqual(rc, 0, said)
        text = words(out)
        self.assertIn("Leeds LS1 4BR", text)
        self.assertNotIn("Leeds, LS1 4BR", text)


if __name__ == "__main__":
    unittest.main()
