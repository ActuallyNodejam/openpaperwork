"""Offline tests for the deck as a PDF, the file that is handed back: both samples pass every rule on their own
printed pages in the Standard and the Sparse preset; the page rules are measured on the pages, not estimated; a
seeded overflow fails; the PDF has real text, a title, a language, bookmarks and page labels and carries no speaker
notes; the PowerPoint file is written when it is asked for; a title's closing full stop and a label in Title
Case are handled the same way in both outputs; and html-deck is no second door.

Needs pypdf, pypdfium2 and a way to print (nodejam-print inside the app, or Playwright with its Chromium); the
tests that build the PowerPoint file need python-pptx as well. Without a printer the printing tests are skipped."""
import copy
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
CHECKS = HERE.parent / "_checks"
sys.path.insert(0, str(HERE / "scripts"))
sys.path.insert(0, str(CHECKS))
os.environ.setdefault("BDECK_NO_RENDER", "1")      # an editable file's pages are estimated here; a PDF's never are
import business_deck as bd  # noqa: E402
import deck_build as mk  # noqa: E402
import deck_html as html  # noqa: E402

PRINTER = bool(shutil.which("nodejam-print") or importlib.util.find_spec("playwright"))
SAMPLES = {name: json.loads((HERE / "templates" / ("%s.deck.json" % name)).read_text()) for name in ("board-update", "proposal")}
BOARD = SAMPLES["board-update"]


def pdf_of(deck, density="standard", name="Board update Q3 2026.pdf", look=None):
    folder = Path(tempfile.mkdtemp(prefix="bdeck-pdf-"))
    path = folder / name
    html.build_pdf(copy.deepcopy(deck), str(path), density, look, str(HERE / "templates"))
    return path


def changed(kind, nth=0, **keys):
    """The board sample with keys of its nth page of a kind changed."""
    deck = copy.deepcopy(BOARD)
    page = [p for p in deck["pages"] if p["type"] == kind][nth]
    page.update(keys)
    return deck


def renamed(deck, names):
    """The deck with its sections renamed everywhere they are written: the agenda, the summary and the pages."""
    deck = copy.deepcopy(deck)
    for page in deck["pages"]:
        if page.get("section") in names:
            page["section"] = names[page["section"]]
        for item in page.get("items") or []:
            if isinstance(item, dict) and item.get("name") in names:
                item["name"] = names[item["name"]]
        for block in page.get("blocks") or []:
            if isinstance(block, dict) and block.get("section") in names:
                block["section"] = names[block["section"]]
    return deck


def check(rule, path):
    return bd.check(rule, path, {}, "first")


def description(path):
    from pypdf import PdfReader
    root = PdfReader(str(path)).trailer["/Root"]
    return json.loads(root["/PieceInfo"][bd.PIECE]["/Private"].get_data().decode("utf-8"))


@unittest.skipUnless(PRINTER, "nothing here can print a page (no nodejam-print, no Playwright)")
class Printed(unittest.TestCase):
    """Both samples as PDF, in both presets the pack ships as good."""

    @classmethod
    def setUpClass(cls):
        cls.built = {(name, preset): pdf_of(deck, preset, name="%s %s.pdf" % (name, preset))
                     for name, deck in SAMPLES.items() for preset in ("standard", "sparse")}

    def test_both_samples_pass_every_rule_in_standard_and_sparse(self):
        for key, path in self.built.items():
            for rule in bd.RULES:
                ok, why = check(rule, path)
                self.assertTrue(ok, "%s, %s: %s" % (key, rule, why))
                self.assertFalse(str(why).startswith("WARN"), "%s, %s: %s" % (key, rule, why))

    def test_the_page_rules_are_measured_on_the_printed_pages(self):
        path = self.built[("board-update", "standard")]
        self.assertIn("measured on the rendered pages", check("BDECK-FILL", path)[1])
        self.assertIn("measured on the printed pages", check("BDECK-FIT", path)[1])
        self.assertIn("measured on the rendered pages", check("BDECK-GRID", path)[1])
        deck = bd.deck_of(path)
        self.assertTrue(deck.printed)
        for s in deck.slides:
            for item in deck.every_text(s):
                self.assertTrue(item.real and all(item.real), "slide %d, %s was not found on its page" % (s.n, item.name))
                self.assertIsNotNone(item.ink)

    def test_sizes_and_lines_come_from_the_page_not_from_the_description(self):
        # The same pages with a description that claims every text twice its size: the check still reads 24 pt titles.
        from pypdf import PdfReader, PdfWriter
        from pypdf.generic import DecodedStreamObject, NameObject
        source = self.built[("board-update", "standard")]
        data = description(source)
        for slide in data["slides"]:
            for item in slide["items"]:
                for para in item.get("paras") or []:
                    para["size"] = para["size"] * 2
        writer = PdfWriter(clone_from=PdfReader(str(source)))
        stream = DecodedStreamObject()
        stream.set_data(json.dumps(data).encode("utf-8"))
        writer._root_object["/PieceInfo"][bd.PIECE][NameObject("/Private")] = writer._add_object(stream)
        other = source.parent / "claimed.pdf"
        with open(other, "wb") as handle:
            writer.write(handle)
        deck = bd.deck_of(other)
        titles = {s.title.paras[0].size for s in deck.slides if s.content()}
        self.assertEqual(titles, {24.0})

    def test_the_pdf_has_real_text_a_title_a_language_bookmarks_and_page_labels(self):
        from pypdf import PdfReader
        path = self.built[("proposal", "standard")]
        deck = SAMPLES["proposal"]
        reader = PdfReader(str(path))
        self.assertEqual(reader.metadata.title, deck["title"])
        self.assertEqual(reader.metadata.author, deck["organisation"])
        self.assertEqual(str(reader.trailer["/Root"]["/Lang"]), deck.get("language") or "en-GB")
        for n, page in enumerate(reader.pages, 1):
            self.assertGreater(len((page.extract_text() or "").strip()), 10, "page %d has no text" % n)
        marks = []

        def walk(items):
            for item in items:
                if isinstance(item, list):
                    walk(item)
                else:
                    marks.append(item.title)
        walk(reader.outline)
        sections = {p["section"] for p in deck["pages"] if p.get("section")}
        self.assertTrue(sections and sections <= set(marks), "sections %s not all in the bookmarks %s" % (sections, marks[:8]))
        self.assertIn("Appendix", marks)
        labels = reader.page_labels
        self.assertEqual(labels[0], "1")
        self.assertEqual(labels[-2:], ["A1", "A2"])
        self.assertTrue(check("BDECK-FILE", path)[0])

    def test_no_speaker_notes_in_the_pdf(self):
        from pypdf import PdfReader
        deck = copy.deepcopy(BOARD)
        for n, page in enumerate(deck["pages"]):
            page["notes"] = "Say this aloud on page %d: the auditors have not signed off yet." % (n + 1)
        path = pdf_of(deck, "sparse")
        notes = [p["notes"] for p in deck["pages"]]
        kept_off = [d for p in BOARD["pages"] for s in p.get("steps") or [] for d in [s.get("detail")] if d]
        self.assertTrue(kept_off)
        told = json.dumps(description(path)) + " ".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
        told += path.read_bytes().decode("latin-1")
        for words in notes + kept_off:
            self.assertNotIn(words[:40], told)

    def test_the_check_needs_no_data_file_and_no_case_file(self):
        path = self.built[("proposal", "sparse")]
        alone = Path(tempfile.mkdtemp()) / path.name
        shutil.copy(path, alone)
        self.assertEqual(sorted(p.name for p in alone.parent.iterdir()), [alone.name])
        for rule in bd.RULES:
            self.assertTrue(check(rule, alone)[0], rule)

    def test_the_pack_check_takes_the_pdf(self):
        path = self.built[("board-update", "standard")]
        run = subprocess.run([sys.executable, str(CHECKS / "packcheck.py"), "business-deck", str(path)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        # The deck's own rules and the notes floor that runs under every pack.
        self.assertIn("pack check clean: %d rules passed" % (len(bd.RULES) + 1), run.stdout)

    def test_charts_are_drawn_from_the_data_and_tables_are_tables(self):
        folder = Path(tempfile.mkdtemp(prefix="bdeck-pdf-"))
        out = folder / "deck.pdf"
        html.build_pdf(copy.deepcopy(BOARD), str(out), "standard", None, str(HERE / "templates"), keep_html=True)
        page = (folder / "deck.html").read_text()
        self.assertIn('<svg class="ch" role="img"', page)
        self.assertGreaterEqual(page.count('<table class="tb"'), 3)
        self.assertIn('<th scope="col"', page)
        self.assertIn('lang="en-GB"', page)
        chart = bd.deck_of(out).slides[3].charts[0]
        first = [p for p in BOARD["pages"] if p["type"] == "chart"][0]
        self.assertEqual(chart.series[0]["values"], [float(v) for v in first["series"][0]["values"]])
        self.assertEqual(chart.axis_min, 0.0)

    def test_the_look_is_the_token_file_no_number_typed_into_the_page(self):
        # another look file: its inks and sizes are the page's, in the description and on the printed page
        look = json.loads((HERE / "look.json").read_text())
        look["ink"]["ink"] = look["marks"]["highlight"] = look["ink"]["rule"] = "0B3D91"
        look["scale"]["standard"]["title"] = [26, 31]
        folder = Path(tempfile.mkdtemp(prefix="bdeck-look-"))
        (folder / "look.json").write_text(json.dumps(look))
        path = pdf_of(BOARD, look=str(folder / "look.json"))
        deck = bd.deck_of(path)
        title = deck.slides[3].title.paras[0]
        self.assertEqual((title.size, title.colour), (26.0, (0x0B, 0x3D, 0x91)))
        for rule in ("BDECK-FIT", "BDECK-CONTRAST", "BDECK-TYPE", "BDECK-HIGHLIGHT"):
            self.assertTrue(check(rule, path)[0], check(rule, path)[1])


@unittest.skipUnless(PRINTER, "nothing here can print a page (no nodejam-print, no Playwright)")
class Faults(unittest.TestCase):
    """What the printed pages catch."""

    def test_a_seeded_overflow_fails_on_the_pdf(self):
        long = " ".join(["The pilot goes on only if every one of the three results holds for two quarters in a row"] * 10)
        ok, why = check("BDECK-FIT", pdf_of(changed("text", statement=long)))
        self.assertFalse(ok)
        self.assertIn("'Statement'", why)
        # a statement that fills its box and no more passes: the lines are counted on the page
        fits = " ".join(["The pilot goes on only if every one of the three results holds for two quarters in a row"] * 6)
        path = pdf_of(changed("text", statement=fits))
        self.assertTrue(check("BDECK-FIT", path)[0])
        statement = next(t for s in bd.deck_of(path).slides for t in s.texts if t.key == "statement")
        self.assertGreaterEqual(statement.real[0], 12)

    def test_a_word_broken_at_its_hyphen_is_still_on_the_page(self):
        # From the real run: "the current two-shift operation" broke after "two-" and was called missing.
        self.assertEqual(bd._letters("two-\x02\r\nshift"), bd._letters("two-shift"))
        joined = "A like-for-like month-on-month year-on-year end-to-end day-to-day state-of-the-art first-in-class up-to-date " \
                 "door-to-door back-to-back one-to-one plan"
        points = ["Capacity constraints make the current two-shift operation unsustainable",
                  "Decline accelerated in June when three large customers moved to weekly orders"]
        deck = changed("chart", takeaway="On-time delivery has fallen every month since April as the line filled.", points=points)
        [p for p in deck["pages"] if p["type"] == "text"][0]["statement"] = joined
        path = pdf_of(deck)
        ok, why = check("BDECK-FIT", path)
        self.assertTrue(ok, why)
        for s in bd.deck_of(path).slides:
            for item in s.texts:
                self.assertTrue(all(item.real), "slide %d, %s" % (s.n, item.name))

    def test_a_word_wider_than_its_column_fails_on_the_pdf(self):
        deck = changed("chart", takeaway="Growth came from Grossaccountexpansionprogrammeseatsaddition, not from price.")
        ok, why = check("BDECK-FIT", pdf_of(deck))
        self.assertFalse(ok)
        self.assertTrue("past the side of its box" in why or "wider than its box" in why, why)

    def test_a_title_of_three_printed_lines_fails(self):
        title = "Recurring revenue reached EUR 18.4 million in the third quarter of 2026, which is six per cent ahead of the plan " \
                "the board approved last year and well ahead of the year before that"
        ok, why = check("BDECK-TITLE", pdf_of(changed("chart", title=title)))
        self.assertFalse(ok)
        self.assertIn("lines", why)

    def test_type_under_the_floor_is_read_off_the_page(self):
        look = json.loads((HERE / "look.json").read_text())
        look["scale"]["standard"]["chart"] = 7
        folder = Path(tempfile.mkdtemp(prefix="bdeck-look-"))
        (folder / "look.json").write_text(json.dumps(look))
        ok, why = check("BDECK-TYPE", pdf_of(BOARD, look=str(folder / "look.json")))
        self.assertFalse(ok)
        self.assertIn("7 pt", why)

    def test_a_table_column_with_no_heading_fails_on_the_pdf(self):
        columns = list([p for p in BOARD["pages"] if p["type"] == "table"][0]["columns"])
        columns[1] = ""
        ok, why = check("BDECK-TABLE", pdf_of(changed("table", columns=columns)))
        self.assertFalse(ok)
        self.assertIn("no heading over column 2", why)

    def test_a_list_given_as_a_tables_head_is_refused_by_name(self):
        with self.assertRaises(SystemExit) as stop:
            pdf_of(changed("table", head=["Measure", "Unit", "Plan"]))
        self.assertIn('"head" is one line of text and was given a list', str(stop.exception))

    def test_a_bar_axis_that_does_not_start_at_zero_fails_on_the_pdf_too(self):
        ok, why = check("BDECK-CHART-HONEST", pdf_of(changed("chart", axis_min=10)))
        self.assertFalse(ok)
        self.assertIn("start the axis at zero", why)

    def test_a_pdf_the_builder_did_not_write_is_not_taken_for_a_deck(self):
        from pypdf import PdfReader, PdfWriter
        source = pdf_of(BOARD)
        writer = PdfWriter(clone_from=PdfReader(str(source)))
        del writer._root_object["/PieceInfo"]
        bare = source.parent / "Exported by hand.pdf"
        with open(bare, "wb") as handle:
            writer.write(handle)
        ok, why = check("BDECK-FILE", bare)
        self.assertFalse(ok)
        self.assertIn("was not written by this pack's builder", why)
        self.assertIn("deck_build.py", why)
        ok, why = check("BDECK-FIT", bare)
        self.assertFalse(ok)
        self.assertIn("could not check", why)
        run = subprocess.run([sys.executable, str(CHECKS / "packcheck.py"), "business-deck", str(bare)], capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertNotIn("pack check clean", run.stdout)


@unittest.skipUnless(PRINTER, "nothing here can print a page (no nodejam-print, no Playwright)")
class Outputs(unittest.TestCase):
    """What a build hands back, and when the PowerPoint file is written."""

    def run_build(self, deck, out, *flags, look=None):
        folder = Path(tempfile.mkdtemp(prefix="bdeck-out-"))
        (folder / "deck.deck.json").write_text(json.dumps(deck))
        argv = [str(folder / "deck.deck.json"), str(folder / out)] + list(flags) + (["--look", look] if look else [])
        mk.main(argv)
        return folder

    def test_the_pdf_alone_is_the_default(self):
        folder = self.run_build(BOARD, "Board update.pdf")
        self.assertTrue((folder / "Board update.pdf").is_file())
        self.assertEqual(sorted(p.suffix for p in folder.iterdir()), [".json", ".pdf"])

    def test_the_powerpoint_file_is_written_when_asked_for(self):
        folder = self.run_build(BOARD, "Board update.pdf", "--editable")
        self.assertTrue((folder / "Board update.pdf").is_file() and (folder / "Board update.pptx").is_file())
        for rule in bd.RULES:
            ok, why = check(rule, folder / "Board update.pptx")
            self.assertTrue(ok, "%s: %s" % (rule, why))
        # the PDF beside it is the pack's own print, not a drawing of the PowerPoint file's pages
        self.assertIsNone(bd._pdf_beside(bd.deck_of(folder / "Board update.pptx")))

    def test_the_data_or_a_companys_look_can_ask_for_it_every_time(self):
        folder = self.run_build(dict(BOARD, editable=True), "Board update.pdf")
        self.assertTrue((folder / "Board update.pptx").is_file())
        look = json.loads((HERE / "look.json").read_text())
        self.assertIs(look["output"]["editable"], False)
        look["output"]["editable"] = True
        home = Path(tempfile.mkdtemp(prefix="bdeck-look-"))
        (home / "look.json").write_text(json.dumps(look))
        folder = self.run_build(BOARD, "Board update.pdf", look=str(home / "look.json"))
        self.assertTrue((folder / "Board update.pptx").is_file())
        with self.assertRaises(SystemExit):
            self.run_build(dict(BOARD, editable="yes"), "Board update.pdf")

    def test_an_out_path_ending_in_pptx_writes_both_and_no_pdf_writes_it_alone(self):
        folder = self.run_build(BOARD, "Board update.pptx")
        self.assertTrue((folder / "Board update.pdf").is_file() and (folder / "Board update.pptx").is_file())
        folder = self.run_build(BOARD, "Board update.pptx", "--no-pdf")
        self.assertEqual(sorted(p.suffix for p in folder.iterdir()), [".json", ".pptx"])

    @unittest.skipUnless(importlib.util.find_spec("playwright"), "the stand-in for the app's printer prints with Playwright")
    def test_inside_the_app_the_apps_own_printer_is_asked_first(self):
        # A stand-in for the app's Resources/bin/nodejam-print, with its command line: <in.html> <out.pdf> --width N --height N.
        tools = Path(tempfile.mkdtemp(prefix="bdeck-bin-"))
        tool = tools / "nodejam-print"
        tool.write_text("#!%s\nimport os, sys\nsys.path.insert(0, %r)\nimport deck_html\n"
                        "assert os.path.isabs(sys.argv[1]) and os.path.isabs(sys.argv[2]), sys.argv\n"
                        "assert sys.argv[3:] == ['--width', '1280', '--height', '720'], sys.argv\n"
                        "deck_html._playwright(sys.argv[1], sys.argv[2])\n" % (sys.executable, str(HERE / "scripts")))
        tool.chmod(0o755)
        before = os.environ["PATH"]
        os.environ["PATH"] = str(tools) + os.pathsep + before
        try:
            out = Path(tempfile.mkdtemp(prefix="bdeck-app-")) / "Board update.pdf"
            name, count, how, kept = html.build_pdf(copy.deepcopy(BOARD), str(out), "standard", None, str(HERE / "templates"))
        finally:
            os.environ["PATH"] = before
        self.assertEqual((name, count, how, kept), ("standard", 13, "the app", 0))
        self.assertTrue(check("BDECK-FILE", out)[0])

    def test_a_file_inside_the_skills_own_folder_is_refused(self):
        with self.assertRaises(SystemExit) as stop:
            mk.main([str(HERE / "templates" / "board-update.deck.json"), str(HERE / "templates" / "board-update.pdf")])
        self.assertIn("inside the skill's own folder", str(stop.exception))
        self.assertFalse((HERE / "templates" / "board-update.pdf").exists())


class TitleStops(unittest.TestCase):
    """One closing full stop comes off a page's title; what belongs to the words stays."""

    def test_what_comes_off_and_what_stays(self):
        show = lambda text, kind="chart": mk.shown_title(text, kind, 6)  # noqa: E731
        self.assertEqual(show("Churn in small accounts doubled in a year."), "Churn in small accounts doubled in a year")
        self.assertEqual(show("Is churn in small accounts the real problem?"), "Is churn in small accounts the real problem?")
        self.assertEqual(show("Churn doubled, and nobody saw it coming!"), "Churn doubled, and nobody saw it coming!")
        self.assertEqual(show("Costs fell at every office of Example Freight Ltd."), "Costs fell at every office of Example Freight Ltd.")
        self.assertEqual(show("The U.S. offices open at 9 a.m."), "The U.S. offices open at 9 a.m.")
        self.assertEqual(show("Vol. 3 of the audit covers Riverside."), "Vol. 3 of the audit covers Riverside")
        self.assertEqual(show("And then the contract ran out..."), "And then the contract ran out...")
        self.assertEqual(show("And then the contract ran out…"), "And then the contract ran out…")
        self.assertEqual(show("Churn doubled"), "Churn doubled")

    def test_a_cover_or_closing_statement_that_is_a_full_sentence_keeps_its_stop(self):
        sentence = "We ask the board to approve the pilot today."
        for kind in ("cover", "closing"):
            self.assertEqual(mk.shown_title(sentence, kind, 6), sentence)
            self.assertEqual(mk.shown_title("Board update.", kind, 6), "Board update")
        self.assertEqual(mk.shown_title(sentence, "text", 6), sentence[:-1])

    @unittest.skipUnless(PRINTER, "nothing here can print a page (no nodejam-print, no Playwright)")
    def test_both_outputs_set_the_same_titles(self):
        from pptx import Presentation
        deck = copy.deepcopy(BOARD)
        for page in deck["pages"]:
            page["title"] = page["title"] + "."
        folder = Path(tempfile.mkdtemp(prefix="bdeck-stop-"))
        mk.build(copy.deepcopy(deck), str(folder / "deck.pptx"), "standard")
        in_file = [s.shapes.title.text for s in Presentation(str(folder / "deck.pptx")).slides]
        on_page = [s.title.text for s in bd.deck_of(pdf_of(deck)).slides]
        self.assertEqual(in_file, on_page)
        for kind, title in zip([p["type"] for p in BOARD["pages"]], in_file):
            self.assertEqual(title.endswith("."), kind in ("cover", "closing"), title)


class Labels(unittest.TestCase):
    """A section or running label in Title Case is asked about, never failed and never rewritten."""

    def words(self, deck, pdf=False):
        if pdf:
            return check("BDECK-WORDS", pdf_of(deck))
        folder = Path(tempfile.mkdtemp(prefix="bdeck-case-"))
        mk.build(copy.deepcopy(deck), str(folder / "deck.pptx"), "standard")
        return check("BDECK-WORDS", folder / "deck.pptx"), folder / "deck.pptx"

    def test_title_case_section_labels_warn(self):
        (ok, why), path = self.words(renamed(BOARD, {"Results": "The Results", "Plan": "Solution Options"}))
        self.assertTrue(ok)
        self.assertTrue(why.startswith("WARN "), why)
        self.assertIn("sentence case", why)
        self.assertIn("'The Results'", why)
        self.assertIn("'Solution Options'", why)
        self.assertIn("'Solution options'", why)
        # the builder set the label as it was written
        self.assertIn("Solution Options", {t.text for s in bd.deck_of(path).slides for t in s.texts})

    def test_a_name_or_a_short_form_alone_does_not_trip_it(self):
        quiet = {"Results": "Q3 results", "Customers": BOARD["organisation"], "Plan": "VAT Q3"}
        (ok, why), _ = self.words(renamed(BOARD, quiet))
        self.assertTrue(ok)
        self.assertFalse(why.startswith("WARN"), why)
        (ok, why), _ = self.words(renamed(BOARD, {"Results": "Q3 Performance"}))     # one capital beside a short form
        self.assertFalse(why.startswith("WARN"), why)
        (ok, why), _ = self.words(BOARD)
        self.assertFalse(why.startswith("WARN"), why)

    def test_one_capital_beside_a_short_form_warns_when_the_deck_writes_the_word_small(self):
        deck = renamed(BOARD, {"Results": "Q3 Performance"})
        cover = [p for p in deck["pages"] if p["type"] == "cover"][0]
        cover["subtitle"] = "How performance held in the third quarter"
        (ok, why), _ = self.words(deck)
        self.assertTrue(ok and why.startswith("WARN "), why)
        self.assertIn("'Q3 Performance'", why)
        self.assertIn("'Q3 performance'", why)

    def test_the_organisation_left_out_comes_from_the_company_file(self):
        folder = Path(tempfile.mkdtemp(prefix="bdeck-company-"))
        (folder / "company.json").write_text(json.dumps({"name": "Example Studio Ltd", "country": "GB"}))
        deck = {k: v for k, v in copy.deepcopy(BOARD).items() if k != "organisation"}
        self.assertEqual(mk.own_company(deck, str(folder / "board.deck.json")), "Example Studio Ltd")
        self.assertEqual(deck["organisation"], "Example Studio Ltd")
        given = copy.deepcopy(BOARD)
        self.assertIsNone(mk.own_company(given, str(folder / "board.deck.json")))
        self.assertEqual(given["organisation"], BOARD["organisation"])
        bare = {k: v for k, v in copy.deepcopy(BOARD).items() if k != "organisation"}
        self.assertIsNone(mk.own_company(bare, str(Path(tempfile.mkdtemp(prefix="bdeck-none-")) / "board.deck.json")))

    def test_a_running_title_in_title_case_warns(self):
        (ok, why), _ = self.words(dict(BOARD, title="Board Update, Third Quarter 2026"))
        self.assertTrue(ok and why.startswith("WARN "), why)
        self.assertIn("running title", why)

    @unittest.skipUnless(PRINTER, "nothing here can print a page (no nodejam-print, no Playwright)")
    def test_the_same_on_the_pdf_and_through_the_pack_check(self):
        path = pdf_of(renamed(BOARD, {"Plan": "Solution Options"}))
        ok, why = check("BDECK-WORDS", path)
        self.assertTrue(ok and why.startswith("WARN ") and "'Solution Options'" in why, why)
        run = subprocess.run([sys.executable, str(CHECKS / "packcheck.py"), "business-deck", str(path)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout)
        self.assertIn("WARN BDECK-WORDS", run.stdout)


class OneDoor(unittest.TestCase):
    """A deck asked for with no format named has one pack to go to, and it hands back a PDF first."""

    def test_the_pack_hands_back_the_pdf_first(self):
        pack = json.loads((HERE / "pack.json").read_text())
        self.assertEqual(pack["hands_back"], ["*.pdf", "*.pptx"])
        self.assertTrue(pack["default"].endswith(".pdf"))
        skill = (HERE / "SKILL.md").read_text()
        self.assertIn('deck_build.py "<name>.deck.json" "<name>.pdf"', skill)
        self.assertIn('packcheck.py business-deck "<name>.pdf"', skill)
        self.assertIn("neither PowerPoint nor Keynote", skill)
        self.assertNotIn("html-deck", skill)

    def test_html_deck_points_here(self):
        other = HERE.parent / "html-deck" / "SKILL.md"
        if not other.is_file():
            return
        text = other.read_text()
        head = text.split("---")[1]
        self.assertIn("business-deck", head)
        self.assertNotIn("Build a business presentation", head)

    def test_the_page_pictures_run_through_uv_where_pillow_is_missing(self):
        source = (HERE / "scripts" / "deck_look.py").read_text()
        self.assertIn('"--with", "pillow", "--with", "pypdfium2"', source)
        self.assertLess(source.index("    through_uv()"), source.index("    images = pages_of("))

    def test_the_builder_prints_through_the_apps_printer_first(self):
        source = (HERE / "scripts" / "deck_html.py").read_text()
        source = source[source.index("def print_pdf("):]
        self.assertLess(source.index('shutil.which("nodejam-print")'), source.index("_playwright(page, pdf)"))
        self.assertNotIn("soffice", source)


if __name__ == "__main__":
    unittest.main()
