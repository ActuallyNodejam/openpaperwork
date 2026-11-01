"""Offline tests for the business deck pack: the sample deck builds and passes its own check in the Standard
and the Sparse preset, every rule catches the fault it is written for and names where it comes from, every
bound that says how much a page carries is read from the preset, and the file is a real PowerPoint deck
(native charts and tables, text that leans on its layouts). Needs python-pptx; the rendered-page tests also
need LibreOffice and are skipped without it."""
import copy
import json
import os
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
CHECKS = HERE.parent / "_checks"
sys.path.insert(0, str(HERE / "scripts"))
sys.path.insert(0, str(CHECKS))
import business_deck as bd  # noqa: E402
import deck_build as mk  # noqa: E402
import packcheck  # noqa: E402
from pptx import Presentation  # noqa: E402
from pptx.util import Pt  # noqa: E402

SAMPLE = json.loads((HERE / "templates" / "board-update.deck.json").read_text())
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
os.environ.setdefault("BDECK_NO_RENDER", "1")


def data(**pages):
    """The sample deck with pages changed: data(chart={"source": ""}) changes the first chart page, a key
    set to None is dropped, and data(chart=[None, {...}]) reaches the second."""
    out = copy.deepcopy(SAMPLE)
    for kind, changes in pages.items():
        kind = kind.replace("_", "-")
        found = [p for p in out["pages"] if p["type"] == kind]
        for page, change in zip(found, changes if isinstance(changes, list) else [changes]):
            for key, value in (change or {}).items():
                if value is None:
                    page.pop(key, None)
                else:
                    page[key] = value
    return out


def built(deck=None, density="standard", edit=None, name="Board update Q3 2026.pptx", look=None):
    folder = Path(tempfile.mkdtemp(prefix="bdeck-test-"))
    path = folder / name
    mk.build(copy.deepcopy(deck or SAMPLE), str(path), density, look)
    if edit:
        prs = Presentation(str(path))
        edit(prs)
        prs.save(str(path))
    return path


def check(rule, path):
    return bd.check(rule, path, {}, "first")


def slides(prs, kind):
    return [s for s in prs.slides if s._element.find(P + "cSld").get("name") == kind]


def shape(slide, name):
    return next(s for s in slide.shapes if s.name == name)


def page_of(kind, nth=0):
    return [p for p in SAMPLE["pages"] if p["type"] == kind][nth]


def n(kind, nth=0):
    """The slide number of the sample's nth page of a kind, in the Standard preset."""
    return [i for i, p in enumerate(SAMPLE["pages"], 1) if p["type"] == kind][nth]


def with_dividers(deck=None):
    """The sample with a divider page before the first page of each section."""
    out, seen = copy.deepcopy(deck or SAMPLE), set()
    pages = []
    for page in out["pages"]:
        name = page.get("section")
        if name and name not in seen:
            seen.add(name)
            pages.append({"type": "section", "title": name})
        pages.append(page)
    out["pages"] = pages
    return out


def without(deck, *kinds):
    deck = copy.deepcopy(deck)
    deck["pages"] = [p for p in deck["pages"] if p["type"] not in kinds]
    return deck


class Sample(unittest.TestCase):
    def test_the_sample_deck_passes_every_rule_in_standard_and_in_sparse(self):
        for preset in ("standard", "sparse"):
            path = built(density=preset)
            for rule in bd.RULES:
                ok, why = check(rule, path)
                self.assertTrue(ok, "%s, %s preset: %s" % (rule, preset, why))

    def test_the_sample_is_twelve_to_sixteen_pages_and_its_numbers_add_up(self):
        self.assertTrue(12 <= len(SAMPLE["pages"]) <= 16)
        table = next(p for p in SAMPLE["pages"] if p["type"] == "table")
        for row in table["rows"]:
            self.assertAlmostEqual(float(row[3]) - float(row[2]), float(row[4]), places=6, msg=row[0])
        chart = next(p for p in SAMPLE["pages"] if p["type"] == "chart")
        self.assertEqual(chart["series"][0]["values"][-1], 18.4)
        self.assertEqual(round(100 * (18.4 / 17.4 - 1)), 6)       # "6% ahead of plan"
        self.assertEqual(round(100 * (18.4 / 14.1 - 1)), 30)      # "30% above the third quarter of 2025"

    def test_the_full_preset_builds(self):
        path = built(density="full")
        self.assertEqual(bd.deck_of(path).preset, "full")

    def test_the_rules_are_registered_and_each_names_its_source(self):
        self.assertEqual(packcheck.SKILL_RULES["business-deck"], list(bd.RULES) + ["NOTES-FLOOR"])
        self.assertEqual(packcheck.MODULES["BDECK"], "business_deck")
        for rule in bd.RULES:
            self.assertTrue(bd.SOURCE[rule], rule)
            self.assertIn(rule, bd.RULE)
        pack = json.loads((HERE / "pack.json").read_text())
        self.assertIn("packcheck.py business-deck {file}", pack["check"])
        self.assertEqual(pack["hands_back"], ["*.pdf", "*.pptx"])

    def test_the_check_needs_no_data_file_and_no_case_file(self):
        path = built()
        alone = Path(tempfile.mkdtemp()) / path.name
        shutil.copy(path, alone)
        self.assertEqual(sorted(p.name for p in alone.parent.iterdir()), [alone.name])
        for rule in bd.RULES:
            self.assertTrue(check(rule, alone)[0], rule)
        self.assertNotIn("business-deck", " ".join(sorted(getattr(packcheck, "TRUTH_RULES", []))))


class Rules(unittest.TestCase):
    def fails(self, rule, path, *needles):
        ok, why = check(rule, path)
        self.assertFalse(ok, "%s passed: %s" % (rule, why))
        for needle in needles:
            self.assertIn(needle, why)
        self.assertIn(bd.SOURCE[rule], why)
        return why

    def test_title_is_the_message(self):
        self.fails("BDECK-TITLE", built(data(chart={"title": "Revenue"})), "topic label", "plain language")
        self.fails("BDECK-TITLE", built(data(table={"title": "Next steps"})), "names the kind of page")
        self.fails("BDECK-TITLE", built(data(chart={"title": "Recurring revenue reached a new high in the quarter:"})), "colon")
        self.fails("BDECK-TITLE", built(data(chart={"title": "Recurring Revenue Reached Another Record High This Quarter"})), "Title Case")
        long = " ".join(["Recurring revenue grew again and again"] * 4)
        self.fails("BDECK-TITLE", built(data(chart={"title": long})), "24 words")
        wide = "Recurring revenue reached " + " ".join(["extraordinarily"] * 13) + " levels"
        self.fails("BDECK-TITLE", built(data(chart={"title": wide})), "lines")
        # the cover, the agenda, a section and the closing may be short
        self.assertTrue(check("BDECK-TITLE", built(data(agenda={"title": "Agenda"}, closing={"title": "Thank you"})))[0])

    def test_one_idea_a_page(self):
        twice = page_of("chart")["title"]
        self.fails("BDECK-ONE-IDEA", built(data(figures={"title": twice})), "share the title")

        def second_exhibit(prs):
            slide = slides(prs, "chart")[0]
            slide.shapes.add_table(2, 2, Pt(500), Pt(300), Pt(200), Pt(60))
        self.fails("BDECK-ONE-IDEA", built(edit=second_exhibit), "one exhibit a page")

    def test_storyline_from_eight_pages_on(self):
        self.fails("BDECK-STORYLINE", built(without(SAMPLE, "summary")), "executive summary")
        self.fails("BDECK-STORYLINE", built(without(SAMPLE, "agenda")), "agenda")
        deck = data(summary={"blocks": [dict(b, section="Risks") if i == 0 else b
                                        for i, b in enumerate(SAMPLE["pages"][1]["blocks"])]})
        self.fails("BDECK-STORYLINE", built(deck), "'Risks'", "no section of the deck")
        bare = without(SAMPLE, "section")
        for page in bare["pages"]:
            page.pop("section", None)
        self.fails("BDECK-STORYLINE", built(bare), "no section label")
        short = copy.deepcopy(SAMPLE)
        short["pages"] = [p for p in short["pages"] if p["type"] in ("cover", "chart", "table", "closing")]
        self.assertTrue(check("BDECK-STORYLINE", built(short))[0])

    def test_a_divider_page_is_asked_only_of_a_long_deck(self):
        # thirteen pages: the section's name in the running line is the mark, no divider page is needed
        path = built()
        self.assertFalse(slides(Presentation(str(path)), "section"))
        self.assertTrue(check("BDECK-STORYLINE", path)[0])
        deck = bd.deck_of(path)
        self.assertEqual(deck.d["story.divider_pages"], 20)
        deck.d = dict(deck.d, **{"story.divider_pages": 10})
        self.fails("BDECK-STORYLINE", path, "opens each section with a divider page", "'Results'")
        divided = built(with_dividers())
        deck = bd.deck_of(divided)
        deck.d = dict(deck.d, **{"story.divider_pages": 10})
        self.assertTrue(check("BDECK-STORYLINE", divided)[0], check("BDECK-STORYLINE", divided)[1])
        prs = Presentation(str(divided))
        self.assertEqual([s.shapes.title.text_frame.text for s in slides(prs, "section")], ["Results", "Customers", "Plan"])

    def test_next_steps_have_an_owner_and_a_date(self):
        steps = copy.deepcopy(next(p for p in SAMPLE["pages"] if p["type"] == "next-steps")["steps"])
        steps[1]["owner"] = ""
        self.fails("BDECK-NEXT-STEPS", built(data(next_steps={"steps": steps})), "no owner")
        steps[1]["owner"], steps[2]["date"] = "Head of customer success", "soon"
        self.fails("BDECK-NEXT-STEPS", built(data(next_steps={"steps": steps})), "give a date")
        self.fails("BDECK-NEXT-STEPS", built(without(SAMPLE, "next-steps")), "ends without next steps")
        moved = copy.deepcopy(SAMPLE)
        moved["pages"].insert(4, moved["pages"].pop(n("next-steps") - 1))
        self.fails("BDECK-NEXT-STEPS", built(moved), "last page before the closing")

    def test_a_source_under_every_chart_and_table(self):
        self.fails("BDECK-SOURCE", built(data(chart={"source": ""})), "slide %d" % n("chart"), "no source line", "Analysis Function")
        self.fails("BDECK-SOURCE", built(data(table={"source": "Source: TBD"})), "slide %d" % n("table"), "name where the figures come from")

    def test_no_placeholder_label(self):
        series = [{"name": "Series 1", "values": [14.1, 15.0, 16.2, 17.3, 18.4]}]
        self.fails("BDECK-PLACEHOLDER", built(data(chart={"series": series})), "'Series 1'")
        self.fails("BDECK-PLACEHOLDER", built(data(chart={"takeaway": "Lorem ipsum dolor sit amet."})), "placeholder")
        self.fails("BDECK-PLACEHOLDER", built(data(text={"statement": "[insert the decision here]"})), "filler")
        self.fails("BDECK-PLACEHOLDER", built(data(chart={"measure": "Value", "unit": None, "period": None})), "'Value'")
        # a table may be headed Measure: the word is a placeholder only where a charting tool writes it
        self.assertTrue(check("BDECK-PLACEHOLDER", built())[0])

    def test_chart_head_names_measure_unit_and_period(self):
        self.fails("BDECK-CHART-HEAD", built(data(chart={"unit": None, "period": None})), "name the measure, its unit and the period")
        self.fails("BDECK-CHART-HEAD", built(data(chart={"measure": None, "unit": None, "period": None})), "no head")

    def test_chart_labels_are_direct_and_horizontal(self):
        def legend(prs):
            slides(prs, "chart")[1].shapes[0].part  # touch
            frame = next(s for s in slides(prs, "chart")[1].shapes if s.has_chart)
            frame.chart.has_legend = True
        self.fails("BDECK-CHART-LABELS", built(edit=legend), "legend for 3 series", "Analysis Function")

        def unnamed(prs):
            slide = slides(prs, "chart")[1]
            for s in [s for s in slide.shapes if s.name == "Series label"]:
                s._element.getparent().remove(s._element)
        self.fails("BDECK-CHART-LABELS", built(edit=unnamed), "does not name the series")

        def tilted(prs):
            frame = next(s for s in slides(prs, "chart")[0].shapes if s.has_chart)
            for node in frame.chart._chartSpace.iter(A + "bodyPr"):
                node.set("rot", "-2700000")
        self.fails("BDECK-CHART-LABELS", built(edit=tilted), "horizontal")

        def bare(prs):
            frame = next(s for s in slides(prs, "chart")[0].shapes if s.has_chart)
            frame.chart.plots[0].has_data_labels = False
        self.fails("BDECK-CHART-LABELS", built(edit=bare), "shows no values")

    def test_charts_are_honest(self):
        self.fails("BDECK-CHART-HONEST", built(data(chart={"axis_min": 12})), "start at 12", "zero")

        def pie(prs):
            from pptx.chart.data import CategoryChartData
            from pptx.enum.chart import XL_CHART_TYPE
            cd = CategoryChartData()
            cd.categories = list("ABCDEFG")
            cd.add_series("Share", [1, 2, 3, 4, 5, 6, 7])
            slides(prs, "text")[0].shapes.add_chart(XL_CHART_TYPE.PIE, Pt(60), Pt(200), Pt(300), Pt(250), cd)
        self.fails("BDECK-CHART-HONEST", built(edit=pie), "pie has 7 parts")

        def solid(prs):
            from lxml import etree
            frame = next(s for s in slides(prs, "chart")[0].shapes if s.has_chart)
            chart = frame.chart._chartSpace.find("{http://schemas.openxmlformats.org/drawingml/2006/chart}chart")
            chart.insert(0, etree.Element("{http://schemas.openxmlformats.org/drawingml/2006/chart}view3D"))
        self.fails("BDECK-CHART-HONEST", built(edit=solid), "3D")
        many = [{"name": "Group %d" % i, "values": [1 + i, 2 + i, 3 + i, 4 + i, 5 + i]} for i in range(5)]
        self.fails("BDECK-CHART-HONEST", built(data(chart=[None, {"series": many, "highlight": None}])), "5 series")

    def test_a_chart_earns_its_place(self):
        two = {"categories": ["Q2 2026", "Q3 2026"], "series": [{"name": "Annual recurring revenue", "values": [17.3, 18.4]}]}
        self.fails("BDECK-CHART-EARNS", built(data(chart=two)), "2 values", "key figures")
        repeat = {"categories": ["Q1 2026", "Q2 2026", "Q3 2026"],
                  "series": [{"name": "Annual recurring revenue", "values": [16.2, 17.3, 18.4]}],
                  "points": ["It was 16.2 in the first quarter", "17.3 in the second", "and 18.4 in Q3 2026"]}
        self.fails("BDECK-CHART-EARNS", built(data(chart=repeat)), "repeats the figures")

    def test_one_highlight_on_what_the_title_names(self):
        self.fails("BDECK-HIGHLIGHT", built(data(chart={"highlight": "Q4 2025"})), "'Q4 2025'", "title does not name")
        self.fails("BDECK-HIGHLIGHT", built(data(chart=[None, {"highlight": "Mid-sized accounts"}])), "'Mid-sized accounts'")
        # "larger accounts held steady" does name the large accounts
        self.assertTrue(check("BDECK-HIGHLIGHT", built(data(chart=[None, {"highlight": "Large accounts"}])))[0])
        self.fails("BDECK-HIGHLIGHT", built(data(table={"highlight": "Gross margin"})), "table marks 'Gross margin'")

        def two(prs):
            from pptx.dml.color import RGBColor
            frame = next(s for s in slides(prs, "chart")[0].shapes if s.has_chart)
            point = frame.chart.series[0].points[1]
            point.format.fill.solid()
            point.format.fill.fore_color.rgb = RGBColor(0x1A, 0x1C, 0x1F)
        self.fails("BDECK-HIGHLIGHT", built(edit=two), "highlights 2 marks")
        # no highlight at all is allowed
        self.assertTrue(check("BDECK-HIGHLIGHT", built(data(chart={"highlight": None}, table={"highlight": None})))[0])

    def test_a_table_is_as_tall_as_its_rows_with_numbers_right_aligned(self):
        rows = copy.deepcopy(next(p for p in SAMPLE["pages"] if p["type"] == "table")["rows"])
        mixed = copy.deepcopy(rows)
        mixed[0][2] = "17"
        self.fails("BDECK-TABLE", built(data(table={"rows": mixed})), "one precision down a column", "Analysis Function tables")
        percent = [[r[0], r[1], r[2] + "%", r[3] + "%", r[4]] for r in rows]
        self.fails("BDECK-TABLE", built(data(table={"rows": percent})), "put the unit in the heading")
        self.fails("BDECK-TABLE", built(data(table={"rows": rows[:2]})), "has 2 rows")
        blank = rows[:3] + [["", "", "", "", ""]] + rows[3:]
        self.fails("BDECK-TABLE", built(data(table={"rows": blank})), "blank row")

        def left(prs):
            from pptx.enum.text import PP_ALIGN
            table = next(s for s in slides(prs, "table")[0].shapes if s.has_table).table
            for r in range(len(table.rows)):
                table.cell(r, 3).text_frame.paragraphs[0].alignment = PP_ALIGN.LEFT
        self.fails("BDECK-TABLE", built(edit=left), "right-align numbers and their heading")

        def merged(prs):
            table = next(s for s in slides(prs, "table")[0].shapes if s.has_table).table
            table.cell(1, 0).merge(table.cell(1, 1))
        self.fails("BDECK-TABLE", built(edit=merged), "merged cells")

        def stretched(prs):
            table = next(s for s in slides(prs, "table")[0].shapes if s.has_table).table
            table.rows[2].height = Pt(120)
        self.fails("BDECK-TABLE", built(edit=stretched), "as tall as its rows", "2.2 lines")

        def headless(prs):
            next(s for s in slides(prs, "table")[0].shapes if s.has_table).table.first_row = False
        self.fails("BDECK-TABLE", built(edit=headless), "header row")

    def test_text_fits_its_box(self):
        long = " ".join(["Growth came from larger accounts adding seats and not from any change in price."] * 6)
        self.fails("BDECK-FIT", built(data(chart={"takeaway": long})), "'Takeaway' needs", "cut about")
        word = "Donaudampfschifffahrtsgesellschaftskapitänsmützenabzeichenhersteller"
        self.fails("BDECK-FIT", built(data(process={"steps": [{"name": word}] + page_of("process")["steps"][1:]})), "wider than its box")

    def test_fill_is_inside_the_presets_bounds(self):
        rows = page_of("table")["rows"][:3]
        why = self.fails("BDECK-FILL", built(data(table={"rows": rows, "takeaway": None, "points": None})),
                         "slide %d's lower half" % n("table"))
        self.assertIn("standard preset", why)

        def panel(prs):
            from pptx.dml.color import RGBColor
            take = shape(slides(prs, "text")[0], "Statement")
            take.fill.solid()
            take.fill.fore_color.rgb = RGBColor(0xF2, 0xF2, 0xF2)
        self.fails("BDECK-FILL", built(edit=panel), "the panel 'Statement'", "at least 0.50 full")

    def test_the_half_empty_pages_this_pack_exists_to_fix_fail_in_standard(self):
        # the old deck's table page: two rows stretched down a tall panel
        two = {"rows": page_of("table")["rows"][:2], "takeaway": None, "points": None}

        def stretched(prs):
            frame = next(s for s in slides(prs, "table")[0].shapes if s.has_table)
            for row in frame.table.rows:
                row.height = Pt(110)
        self.fails("BDECK-FILL", built(data(table=two), edit=stretched), "slide %d fills" % n("table"), "asks for 0.27")
        # and its closing page: one line on an empty page
        self.fails("BDECK-FILL", built(data(closing={"title": "Thank you", "contact": None, "small": None})),
                   "the closing page", "not one line")
        self.assertTrue(check("BDECK-FILL", built())[0])

    def test_a_timeline_that_hangs_from_the_title_fails(self):
        self.assertTrue(check("BDECK-FILL", built())[0])

        def hang(prs):
            slide = slides(prs, "timeline")[0]
            parts = [s for s in slide.shapes if s.name.startswith("Milestone") or s.name in ("Axis", "Mark")]
            title = slide.shapes.title
            shift = min(s.top for s in parts) - (title.top + title.height + Pt(8))
            self.assertGreater(shift, Pt(40))          # as built, the line sits on the middle of the body, not under the title
            for s in parts:
                s.top = s.top - shift
        for preset in ("standard", "sparse"):
            path = built(density=preset, edit=hang)
            ok, why = check("BDECK-FILL", path)
            self.assertFalse(ok, "%s: a timeline hung from the title passes: %s" % (preset, why))
            self.assertIn("slide %d's lower half" % n("timeline"), why)

    def test_a_body_that_stops_in_its_upper_half_fails_whatever_the_page_type(self):
        thin = {
            "summary": {"blocks": [{"section": "Results", "lead": "Up."}, {"section": "Customers", "lead": "Down."},
                                   {"section": "Plan", "lead": "Fix."}]},
            "figures": {"figures": [{"label": "Revenue", "value": "18"}, {"label": "Margin", "value": "78"}], "takeaway": None},
            "table": {"rows": page_of("table")["rows"][:3], "takeaway": None, "points": None, "head": None},
            "comparison": {"rows": page_of("comparison")["rows"][:2]},
            "process": {"steps": [{"name": "Call"}, {"name": "Setup"}], "takeaway": None},
            "timeline": {"steps": [{"when": "2026", "what": "Start"}, {"when": "2027", "what": "End"}]},
            "text": {"statement": "The pilot decides.", "points": [{"point": "Churn falls"}]},
            "next_steps": {"steps": [{"action": "Approve", "owner": "Board", "date": "22 October 2026"}]},
        }
        for kind, change in thin.items():
            ok, why = check("BDECK-FILL", built(data(**{kind: change})))
            self.assertFalse(ok, "a thin %s page passes: %s" % (kind, why))
            self.assertIn("slide %d" % n(kind.replace("_", "-")), why, kind)

    def test_words_and_points_are_inside_the_presets_bounds(self):
        wordy = " ".join(["The programme goes on only if the pilot shows that it works for small accounts."] * 8)
        self.fails("BDECK-WORDS", built(data(text={"statement": wordy})), "words", "holds 120")
        thin = {"figures": [{"label": "Revenue", "value": "18.4"}, {"label": "Margin", "value": "78%"}],
                "title": "Revenue and margin both rose this quarter", "takeaway": None}
        self.fails("BDECK-WORDS", built(data(figures=thin)), "at least 25")
        six = ["Point number %d about the quarter" % i for i in range(1, 7)]
        self.fails("BDECK-WORDS", built(data(chart={"points": six})), "lists 6 points", "holds 5")
        long = ["The plan for the quarter was EUR 17.4 million, set in January, when two large accounts were still expected to leave"]
        self.fails("BDECK-WORDS", built(data(chart={"points": long})), "at most two")
        rambling = ("Growth came from larger accounts adding seats over the year and not from any change in the price list, "
                    "which has stayed where it was since 2024 for every size of account.")
        self.fails("BDECK-WORDS", built(data(chart={"takeaway": rambling})), "takeaway runs to", "at most 3 lines")

    def test_type_floors(self):
        def tiny(prs):
            shape(slides(prs, "chart")[0], "Source").text_frame.paragraphs[0].runs[0].font.size = Pt(7)
        self.fails("BDECK-TYPE", built(edit=tiny), "at 7 pt", "under 10 pt")

        def big_title(prs):
            slides(prs, "table")[0].shapes.title.text_frame.paragraphs[0].runs[0].font.size = Pt(30)
        self.fails("BDECK-TYPE", built(edit=big_title), "one title size")

        def small_body(prs):
            for row in next(s for s in slides(prs, "table")[0].shapes if s.has_table).table.rows:
                for cell in row.cells:
                    for run in cell.text_frame.paragraphs[0].runs:
                        run.font.size = Pt(11)
        self.fails("BDECK-TYPE", built(edit=small_body), "most of its text at 11 pt", "at least 14 pt")

    def test_contrast(self):
        def pale(prs):
            from pptx.dml.color import RGBColor
            shape(slides(prs, "chart")[0], "Takeaway").text_frame.paragraphs[0].runs[0].font.color.rgb = RGBColor(0xC8, 0xC8, 0xC8)
        self.fails("BDECK-CONTRAST", built(edit=pale), ":1 against its ground", "WCAG 2.2")

        def faint(prs):
            from pptx.dml.color import RGBColor
            frame = next(s for s in slides(prs, "chart")[0].shapes if s.has_chart)
            frame.chart.series[0].format.fill.solid()
            frame.chart.series[0].format.fill.fore_color.rgb = RGBColor(0xEE, 0xEE, 0xEE)
        self.fails("BDECK-CONTRAST", built(edit=faint), "a mark needs 3:1")
        # the brand's ink at 60 percent is under 4.5:1 for small print; the open default's second ink is not
        self.assertLess(bd.contrast((0x76, 0x77, 0x79), (255, 255, 255)), 4.5)
        self.assertGreater(bd.contrast((0x6A, 0x6B, 0x6D), (255, 255, 255)), 4.5)

    def test_grid_title_and_running_line_at_one_position(self):
        def moved(prs):
            title = slides(prs, "table")[0].shapes.title
            title.top = title.top + Pt(20)
        self.fails("BDECK-GRID", built(edit=moved), "title sits at another position on slide %d" % n("table"))

        def dropped(prs):
            for slide in slides(prs, "chart")[:1]:
                number = shape(slide, "Page number")
                number._element.getparent().remove(number._element)
        self.fails("BDECK-GRID", built(edit=dropped), "no page number")

        def off_line(prs):
            foot = shape(slides(prs, "chart")[0], "Deck title")
            foot.left, foot.top, foot.width, foot.height = Pt(300), Pt(30), Pt(300), Pt(14)
        self.fails("BDECK-GRID", built(edit=off_line), "more than one baseline")

        def edge(prs):
            box = slides(prs, "text")[0].shapes.add_textbox(Pt(4), Pt(300), Pt(200), Pt(30))
            box.text_frame.text = "A note that runs into the left margin of the page"
        self.fails("BDECK-GRID", built(edit=edge), "from a side edge")
        undated = {"meta": [{"key": "Prepared for", "value": "The board"}], "subtitle": "Board update"}
        self.fails("BDECK-GRID", built(data(cover=undated)), "cover carries no date")

    def test_the_files_accessibility_basics(self):
        self.fails("BDECK-FILE", built(name="deck.pptx"), "name it after the deck", "Section 508")

        def no_alt(prs):
            frame = next(s for s in slides(prs, "chart")[0].shapes if s.has_chart)
            frame._element.find(P + "nvGraphicFramePr/" + P + "cNvPr").set("descr", "")
        self.fails("BDECK-FILE", built(edit=no_alt), "no alternative text")
        self.fails("BDECK-FILE", built(edit=lambda prs: setattr(prs.core_properties, "title", "")), "no title in its properties")

        def title_last(prs):
            slide = slides(prs, "text")[0]
            el = slide.shapes.title._element
            el.getparent().append(el)
        self.fails("BDECK-FILE", built(edit=title_last), "before its title")

        def long_alt(prs):
            frame = next(s for s in slides(prs, "chart")[0].shapes if s.has_chart)
            frame._element.find(P + "nvGraphicFramePr/" + P + "cNvPr").set("descr", "x" * 300)
        self.fails("BDECK-FILE", built(edit=long_alt), "keep it to 250")


class Density(unittest.TestCase):
    """Every rule that says how much a page carries reads its bound from the preset."""

    def test_every_density_bound_is_a_number_in_the_preset(self):
        density = json.loads((HERE / "density.json").read_text())
        keys = None
        for name, preset in density["presets"].items():
            numbers = {k for k, v in preset.items() if k != "build"}
            keys = numbers if keys is None else keys
            self.assertEqual(numbers, keys, name)
            for key in numbers:
                self.assertIsInstance(preset[key], (int, float), "%s %s" % (name, key))
        self.assertEqual(density["default"], "standard")
        source = (CHECKS / "business_deck.py").read_text()
        for key in sorted(keys):
            self.assertIn('"%s"' % key, source, "the check never reads %s" % key)

    def test_turning_a_knob_turns_the_verdict(self):
        path = built()
        turns = {"fill.min": ("BDECK-FILL", 0.99), "fill.max": ("BDECK-FILL", 0.05), "lower.min": ("BDECK-FILL", 0.99),
                 "words.min": ("BDECK-WORDS", 500), "words.max": ("BDECK-WORDS", 5), "bullets.max": ("BDECK-WORDS", 1),
                 "takeaway.max_lines": ("BDECK-WORDS", 0),
                 "type.body_min": ("BDECK-TYPE", 30), "type.floor": ("BDECK-TYPE", 20),
                 "title.max_lines": ("BDECK-TITLE", 0), "title.min_words": ("BDECK-TITLE", 20), "title.max_words": ("BDECK-TITLE", 3),
                 "margin.min": ("BDECK-GRID", 0.2), "table.row_pitch": ("BDECK-TABLE", 1.0),
                 "story.min_pages": ("BDECK-STORYLINE", 99), "story.divider_pages": ("BDECK-STORYLINE", 5),
                 "fill.closing_min": ("BDECK-FILL", 0.9), "legend.direct_max": ("BDECK-CHART-LABELS", 1),
                 "series.max": ("BDECK-CHART-HONEST", 1), "chart.min_points": ("BDECK-CHART-EARNS", 50),
                 "table.min_rows": ("BDECK-TABLE", 50), "alt.max_chars": ("BDECK-FILE", 10)}
        base = dict(bd.deck_of(path).d)
        for key, (rule, value) in turns.items():
            self.assertTrue(check(rule, path)[0], "%s before %s is turned" % (rule, key))
            deck = bd.deck_of(path)
            deck.d = dict(base, **{key: value})
            verdict = check(rule, path)[0]
            deck.d = base
            if key == "story.min_pages":
                self.assertTrue(verdict)        # a longer threshold asks for less
                short = without(SAMPLE, "summary")
                self.assertFalse(check(rule, built(short))[0])
            elif key == "legend.direct_max":
                self.assertTrue(verdict)        # three series, no legend, all named: fine under either limit
            else:
                self.assertFalse(verdict, "%s still passes with %s at %s" % (rule, key, value))

    def test_the_preset_is_written_into_the_file_and_read_back(self):
        self.assertEqual(bd.deck_of(built(density="sparse")).preset, "sparse")
        plain = built(edit=lambda prs: setattr(prs.core_properties, "identifier", ""))
        self.assertEqual(bd.deck_of(plain).preset, "standard")

    def test_a_continued_page_is_one_page_of_the_story(self):
        seven = copy.deepcopy(SAMPLE)
        seven["pages"] = [p for p in seven["pages"] if p["type"] in ("cover", "chart", "figures", "table", "next-steps", "closing")]
        self.assertEqual(len(seven["pages"]), 7)
        long = [["Line %d" % i, "EUR million", "%d.0" % i, "%d.5" % i, "+0.5"] for i in range(1, 11)]
        next(p for p in seven["pages"] if p["type"] == "table")["rows"] = long
        path = built(seven, density="sparse")
        deck = bd.deck_of(path)
        self.assertEqual(len(deck.slides), 8)                     # the table continues on a second page
        self.assertEqual(bd.page_count(deck), 7)
        self.assertTrue(check("BDECK-STORYLINE", path)[0])

    def test_sparse_keeps_a_six_row_table_whole_and_continues_only_what_does_not_fit(self):
        prs = Presentation(str(built(density="sparse")))
        self.assertEqual(len(prs.slides), len(SAMPLE["pages"]))
        self.assertFalse([s for s in prs.slides if "/" in s.shapes.title.text_frame.text[-6:]], "no page is continued")
        table = slides(prs, "table")[0]
        self.assertEqual(len(next(s for s in table.shapes if s.has_table).table.rows), 7)
        self.assertIn("moved the wrong way", shape(table, "Takeaway").text_frame.text)        # the takeaway stays with its table
        self.assertEqual(len(next(s for s in slides(prs, "comparison")[0].shapes if s.has_table).table.rows), 7)
        # fourteen rows do not fit a sparse page: they continue, the heading repeated, never under four rows a page
        long = [["Line %d" % i, "EUR million", "%d.0" % i, "%d.5" % i, "+0.5"] for i in range(1, 15)]
        many = Presentation(str(built(data(table={"rows": long}), density="sparse")))
        tables = slides(many, "table")
        self.assertEqual(len(tables), 3)
        self.assertEqual([t.shapes.title.text_frame.text[-5:] for t in tables], ["(1/3)", "(2/3)", "(3/3)"])
        sizes = [len(next(s for s in t.shapes if s.has_table).table.rows) - 1 for t in tables]
        self.assertEqual(sum(sizes), 14)
        self.assertGreaterEqual(min(sizes), 4)
        heads = [[c.text_frame.text for c in next(s for s in t.shapes if s.has_table).table.rows[0].cells] for t in tables]
        self.assertEqual(heads[0], heads[2])
        self.assertEqual([bool([s for s in t.shapes if s.name == "Takeaway"]) for t in tables], [False, False, True])
        # seven rows would leave a page of three: they stay together
        seven = Presentation(str(built(data(table={"rows": long[:7]}), density="sparse")))
        self.assertEqual(len(slides(seven, "table")), 1)
        chart = slides(prs, "chart")[0]
        self.assertNotIn("EUR 17.4 million", " ".join(s.text_frame.text for s in chart.shapes if s.has_text_frame))
        self.assertIn("EUR 17.4 million", chart.notes_slide.notes_text_frame.text)
        standard = Presentation(str(built()))
        self.assertEqual(len(slides(standard, "table")), 1)
        self.assertIn("EUR 17.4 million", " ".join(s.text_frame.text for s in slides(standard, "chart")[0].shapes if s.has_text_frame))


class File(unittest.TestCase):
    """The file is a PowerPoint deck a colleague edits: native charts and tables, text that leans on its layouts."""

    def test_charts_and_tables_are_native(self):
        path = built()
        prs = Presentation(str(path))
        frame = next(s for s in slides(prs, "chart")[0].shapes if s.has_chart)
        self.assertEqual(list(frame.chart.plots[0].categories), ["Q3 2025", "Q4 2025", "Q1 2026", "Q2 2026", "Q3 2026"])
        self.assertEqual(list(frame.chart.series[0].values), [14.1, 15.0, 16.2, 17.3, 18.4])
        self.assertIsNotNone(frame.chart.part.chart_workbook.xlsx_part)       # the data sheet PowerPoint opens to edit
        for kind in ("table", "comparison", "next-steps"):
            self.assertTrue(any(s.has_table for s in slides(prs, kind)[0].shapes), kind)
        names = zipfile.ZipFile(path).namelist()
        self.assertFalse([n for n in names if n.startswith("ppt/media/")], "no page is a picture")

    def test_a_deck_made_earlier_is_never_read_as_the_persons_notes(self):
        # Mac sweep 2026-10-12: a brief made beside q3.pptx asked the client about "0587-4C30-8999" (the table
        # style's GUID) and the deck's cover date, because the deck was read as notes.
        import notes_floor
        path = built()
        with tempfile.TemporaryDirectory() as folder:
            shutil.copy(path, Path(folder) / "q3.pptx")
            (Path(folder) / "notes.txt").write_text("Call Maria on 12 March 2026.\n")
            notes, _ = notes_floor.read_folder(Path(folder) / "brief.pdf")
        self.assertEqual([name for name, _ in notes], ["notes.txt"])
        self.assertNotRegex(notes_floor._office_text(path), r"[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}")

    def test_every_slide_of_the_editable_file_carries_speaker_notes(self):
        # ppt-master bench, 2026-10-10: the editable file had no notes on any slide; the samples carry them now
        prs = Presentation(str(built()))
        for number, slide in enumerate(prs.slides, 1):
            self.assertTrue(slide.has_notes_slide and slide.notes_slide.notes_text_frame.text.strip(), "slide %d" % number)
        folder = Path(tempfile.mkdtemp(prefix="bdeck-notes-"))
        (folder / "d.deck.json").write_text(json.dumps(data(chart={"notes": None}, closing={"notes": " "})))
        with self.assertRaises(SystemExit) as stop:
            mk.main([str(folder / "d.deck.json"), str(folder / "Deck.pptx"), "--no-pdf"])
        said = str(stop.exception)
        self.assertIn("speaker notes on every page", said)
        self.assertIn("4 (chart)", said)
        self.assertIn("13 (closing)", said)
        self.assertFalse((folder / "Deck.pptx").exists())
        # a PDF carries no notes and asks for none
        mk.need_notes(SAMPLE)
        self.assertEqual(mk.editable(data(chart={"notes": None})), False)

    def test_a_bar_below_zero_does_not_sit_on_its_own_name(self):
        from pptx.enum.chart import XL_TICK_LABEL_POSITION
        change = {"kind": "bar", "categories": ["Base", "Rent +10%", "Rent -10%"], "highlight": None,
                  "series": [{"name": "Return", "values": [1.0, 2.2, -0.2]}]}
        chart = next(s for s in slides(Presentation(str(built(data(chart=change)))), "chart")[0].shapes if s.has_chart).chart
        self.assertEqual(chart.category_axis.tick_label_position, XL_TICK_LABEL_POSITION.LOW)
        plain = next(s for s in slides(Presentation(str(built())), "chart")[0].shapes if s.has_chart).chart
        self.assertNotEqual(plain.category_axis.tick_label_position, XL_TICK_LABEL_POSITION.LOW)

    def test_text_takes_its_look_from_the_layout_not_from_the_slide(self):
        path = built()
        prs = Presentation(str(path))
        for slide in prs.slides:
            for sh in slide.placeholders:
                if not sh.has_text_frame:
                    continue
                for node in sh._element.iter(A + "rPr"):
                    self.assertIsNone(node.get("sz"), "%s writes a size on a run" % sh.name)
                    self.assertIsNone(node.get("spc"), "%s writes letter spacing on a run" % sh.name)
                    self.assertIsNone(node.find(A + "solidFill"), "%s writes a colour on a run" % sh.name)
                self.assertIsNone(sh._element.find(P + "txBody/" + A + "lstStyle/" + A + "lvl1pPr"), sh.name)
        cover = next(la for la in prs.slide_layouts if la.name == "Cover")
        self.assertIsNotNone(cover._element.find(P + "cSld/" + P + "bg"))        # the dark ground is the layout's
        for slide in slides(prs, "cover"):
            self.assertFalse([s for s in slide.shapes if s.width and s.width >= prs.slide_width], "no rectangle stands in for a background")
        self.assertEqual(sorted(la.name for la in prs.slide_layouts), sorted(mk.LAYOUTS))

    def test_letter_spacing_is_a_token_on_the_layouts_large_type(self):
        look = json.loads((HERE / "look.json").read_text())
        self.assertEqual(look["tracking"]["em"], -0.02)
        self.assertEqual(look["tracking"]["from_pt"], 14)
        prs = Presentation(str(built()))
        chart = next(la for la in prs.slide_layouts if la.name == "Chart")
        spc = {p.name: p._element.find(".//" + A + "lvl1pPr/" + A + "defRPr").get("spc") for p in chart.placeholders}
        title_size = look["scale"]["standard"]["title"][0]
        self.assertEqual(int(spc["Title"]), round(-0.02 * title_size * 100))
        self.assertEqual(spc["Source"], "0")
        self.assertEqual(chart.placeholders[0]._element.find(".//" + A + "lvl1pPr/" + A + "defRPr").get("b"), "0")
        take = next(p for p in chart.placeholders if p.name == "Takeaway")._element
        self.assertEqual(take.find(".//" + A + "lvl2pPr/" + A + "defRPr").get("spc"), "0")     # body text is not spaced

    def test_the_type_scale_has_a_step_for_each_job(self):
        look = json.loads((HERE / "look.json").read_text())
        for preset in ("standard", "sparse"):
            scale = look["scale"][preset]
            steps = [scale[k][0] for k in ("display", "headline", "title", "lead", "body", "small")]
            self.assertEqual(steps, sorted(steps, reverse=True), preset)
            self.assertEqual(len(set(steps)), 6, preset)
            prs = Presentation(str(built(density=preset)))
            size = lambda layout, name: int(next(p for p in next(la for la in prs.slide_layouts if la.name == layout).placeholders  # noqa: E731
                                                  if p.name == name)._element.find(".//" + A + "lvl1pPr/" + A + "defRPr").get("sz")) / 100
            self.assertEqual(size("Cover", "Title"), scale["display"][0])        # the cover takes the largest type in the deck
            self.assertEqual(size("Closing", "Title"), scale["display"][0])
            self.assertEqual(size("Chart", "Title"), scale["title"][0])
            self.assertEqual(size("Text", "Statement"), scale["lead"][0])       # a statement in the body: one step under the title
            self.assertEqual(size("Chart", "Takeaway"), scale["lead"][0])
            cover = next(la for la in prs.slide_layouts if la.name == "Cover").placeholders[0]._element
            self.assertEqual(int(cover.find(".//" + A + "lvl1pPr/" + A + "defRPr").get("spc")), round(-0.02 * scale["display"][0] * 100))

    def test_the_evidence_pages_share_one_pattern_in_each_preset(self):
        """Chart, chart, table: in Sparse the exhibit takes the full width and its takeaway stands under it; in
        Standard the takeaway stands beside it and a sentence wraps to at most three lines."""
        look = mk.load_look(str(HERE / "look.json"))
        for preset in ("standard", "sparse"):
            kit = mk.Kit(look, mk.load_density(), preset, "en-GB")
            path = built(density=preset)
            prs = Presentation(str(path))
            for kind, exhibit in (("chart", "has_chart"), ("table", "has_table")):
                for slide in slides(prs, kind):
                    frame = next(s for s in slide.shapes if getattr(s, exhibit))
                    take = shape(slide, "Takeaway")
                    if preset == "sparse":
                        self.assertGreaterEqual(take.top, frame.top + frame.height, "%s: the takeaway is under its %s" % (preset, kind))
                        self.assertAlmostEqual(frame.left / 12700.0, kit.X0, delta=1)
                        if kind == "chart":
                            self.assertAlmostEqual(frame.width / 12700.0, kit.CW, delta=1)
                    else:
                        self.assertGreaterEqual(take.left, frame.left + frame.width, "%s: the takeaway is beside its %s" % (preset, kind))
            deck = bd.deck_of(path)
            for s in deck.slides:
                for item in s.named("takeaway"):
                    self.assertLessEqual(len(item.lines(deck.advance)[0]), 3, "slide %d, %s" % (s.n, preset))
            line = shape(slides(prs, "timeline")[0], "Axis")
            self.assertAlmostEqual(line.top / 12700.0, (kit.body_top + kit.body_bottom) / 2.0, delta=1, msg=preset)

    def test_rows_keep_one_rhythm_when_one_of_them_wraps(self):
        blocks = copy.deepcopy(page_of("summary")["blocks"])
        blocks[1]["lead"] = "Churn in small accounts doubled in a year, to 4.2% a quarter, while larger accounts stayed where they were."
        for preset in ("standard", "sparse"):
            path = built(data(summary={"blocks": blocks}), density=preset)
            summary = slides(Presentation(str(path)), "summary")[0]
            tops = [shape(summary, "Block %d" % i).top for i in (1, 2, 3)]
            self.assertAlmostEqual(tops[1] - tops[0], tops[2] - tops[1], delta=Pt(0.5), msg=preset)
            self.assertTrue(check("BDECK-FIT", path)[0], check("BDECK-FIT", path)[1])

    def test_the_builder_writes_no_label_of_its_own(self):
        bare = data(chart={"measure": None, "unit": None, "period": None, "alt": None, "takeaway": None, "points": None})
        path = built(bare)
        text = " ".join(t for s in bd.deck_of(path).slides for _, t in bd.all_text(bd.deck_of(path), s))
        for word in ("Measure", "Value", "Series", "Category"):
            self.assertNotIn(word, text.replace("Measure Unit", ""))
        prs = Presentation(str(path))
        self.assertFalse([s for s in slides(prs, "chart")[0].shapes if s.name == "Chart head"])
        with self.assertRaises(SystemExit) as refused:
            built(data(next_steps={"columns": None}))
        self.assertIn("three column headings", str(refused.exception))

    def test_the_builder_refuses_what_it_does_not_know(self):
        for change, needle in (({"colour": "red"}, "unknown key"), ({"type": "pie"}, "page types are")):
            deck = copy.deepcopy(SAMPLE)
            deck["pages"][4].update(change)
            with self.assertRaises(SystemExit) as refused:
                built(deck)
            self.assertIn(needle, str(refused.exception))

    def test_a_company_look_replaces_the_look_and_nothing_else(self):
        look = json.loads((HERE / "look.json").read_text())
        look["name"] = "Example Studio"
        look["marks"]["highlight"] = "0B5FFF"
        look["face"]["name"] = "Georgia"
        look["running"]["place"] = "bottom"
        look["grid"]["content_from"] = 4
        look["tracking"]["em"] = 0
        file = Path(tempfile.mkdtemp()) / "look.json"
        file.write_text(json.dumps(look))
        path = built(look=str(file))
        deck = bd.deck_of(path)
        self.assertEqual(deck.face, "Georgia")
        chart = deck.slides[n("chart") - 1].charts[0]
        self.assertEqual(chart.series[0]["points"], {4: (0x0B, 0x5F, 0xFF)})
        for rule in ("BDECK-TITLE", "BDECK-STORYLINE", "BDECK-SOURCE", "BDECK-CHART-LABELS", "BDECK-HIGHLIGHT",
                     "BDECK-TABLE", "BDECK-CONTRAST", "BDECK-GRID", "BDECK-FILE"):
            self.assertTrue(check(rule, path)[0], "%s under another look: %s" % (rule, check(rule, path)[1]))


@unittest.skipUnless(mk.soffice(), "LibreOffice is not installed")
class Rendered(unittest.TestCase):
    def test_the_pdf_is_written_and_the_pages_are_measured_on_it(self):
        path = built()
        pdf = mk.write_pdf(str(path))
        self.assertTrue(pdf and os.path.isfile(pdf))
        old = os.environ.pop("BDECK_NO_RENDER", None)
        try:
            bd._CACHE.clear()
            ok, why = check("BDECK-FILL", path)
            self.assertTrue(ok, why)
            if bd._pages(bd.deck_of(path)):
                self.assertIn("measured on the rendered pages", why)
                ok, why = check("BDECK-GRID", path)
                self.assertTrue(ok, why)
                self.assertIn("rendered", why)
        finally:
            if old is not None:
                os.environ["BDECK_NO_RENDER"] = old
            bd._CACHE.clear()


if __name__ == "__main__":
    unittest.main()
