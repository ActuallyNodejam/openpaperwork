"""Offline tests for the business deck's second sample, a proposal, and the four page types it brings: a 2x2
matrix, a figure, a quote, and an appendix divider with backup pages. The sample builds and passes its own
check in the Standard and the Sparse preset; every new rule catches the fault it is written for and names
where it comes from; the builder refuses what it cannot lay out. Needs python-pptx and Pillow."""
import copy
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
CHECKS = HERE.parent / "_checks"
TEMPLATES = HERE / "templates"
sys.path.insert(0, str(HERE / "scripts"))
sys.path.insert(0, str(CHECKS))
import business_deck as bd  # noqa: E402
import deck_build as mk  # noqa: E402
from pptx import Presentation  # noqa: E402
from pptx.dml.color import RGBColor  # noqa: E402
from pptx.util import Emu, Pt  # noqa: E402

SAMPLE = json.loads((TEMPLATES / "proposal.deck.json").read_text(encoding="utf-8"))
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
os.environ.setdefault("BDECK_NO_RENDER", "1")
NEW = ("BDECK-MATRIX", "BDECK-FIGURE", "BDECK-QUOTE", "BDECK-APPENDIX")


def data(**pages):
    """The proposal with pages changed: data(quote={"role": ""}) changes the first quote page; a key set to
    None is dropped; data(table=[None, {...}]) reaches the second table, the backup page."""
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


def built(deck=None, density="standard", edit=None, name="Cleaning proposal 2026.pptx", folder=None):
    out = Path(tempfile.mkdtemp(prefix="bdeck-test-")) / name
    mk.build(copy.deepcopy(deck or SAMPLE), str(out), density, None, str(folder or TEMPLATES))
    if edit:
        prs = Presentation(str(out))
        edit(prs)
        prs.save(str(out))
    return out


def check(rule, path):
    return bd.check(rule, path, {}, "first")


def slides(prs, kind):
    return [s for s in prs.slides if s._element.find(P + "cSld").get("name") == kind]


def shape(slide, name):
    return next(s for s in slide.shapes if s.name == name)


def shapes(slide, name):
    return [s for s in slide.shapes if s.name == name]


def n(kind, nth=0):
    return [i for i, p in enumerate(SAMPLE["pages"], 1) if p["type"] == kind][nth]


def page_of(kind, nth=0):
    return [p for p in SAMPLE["pages"] if p["type"] == kind][nth]


def refused(test, deck, *needles, **kw):
    with test.assertRaises(SystemExit) as stop:
        built(deck, **kw)
    for needle in needles:
        test.assertIn(needle, str(stop.exception))


class Base(unittest.TestCase):
    def fails(self, rule, path, *needles):
        ok, why = check(rule, path)
        self.assertFalse(ok, "%s passed: %s" % (rule, why))
        for needle in needles:
            self.assertIn(needle, why)
        self.assertIn(bd.SOURCE[rule], why)
        return why


class Sample(Base):
    def test_the_proposal_passes_every_rule_in_standard_and_in_sparse(self):
        for preset in ("standard", "sparse"):
            path = built(density=preset)
            for rule in bd.RULES:
                ok, why = check(rule, path)
                self.assertTrue(ok, "%s, %s preset: %s" % (rule, preset, why))

    def test_the_proposal_is_a_proposal_and_holds_the_four_page_types(self):
        kinds = [p["type"] for p in SAMPLE["pages"]]
        self.assertTrue(12 <= len(kinds) <= 16)
        for kind in ("matrix", "figure", "quote", "appendix", "comparison", "timeline", "next-steps", "table"):
            self.assertIn(kind, kinds)
        self.assertLess(kinds.index("closing"), kinds.index("appendix"))
        self.assertEqual(kinds[kinds.index("appendix") + 1:], ["table", "text"])
        board = json.loads((TEMPLATES / "board-update.deck.json").read_text(encoding="utf-8"))
        self.assertNotEqual(board["organisation"], SAMPLE["organisation"])       # two samples, two invented companies

    def test_the_proposals_numbers_add_up(self):
        price, area = page_of("table", 0), page_of("table", 1)
        rows = {r[0]: [float(c.replace(",", "")) for c in r[1:]] for r in price["rows"]}
        total = rows.pop("All six offices")
        self.assertEqual([sum(v[i] for v in rows.values()) for i in range(3)], total)
        self.assertEqual(total, [412.0, 356.0, 56.0])
        for today, offer, saving in rows.values():
            self.assertEqual(today - offer, saving)
        self.assertEqual(page_of("chart")["series"][0]["values"], [v[0] for v in rows.values()])
        self.assertEqual(round(100 * 56 / 412.0), 14)                            # "a cut of 14%"
        floors = {r[0]: [float(c.replace(",", "")) for c in r[1:]] for r in area["rows"]}
        whole = floors.pop("All six offices")
        self.assertEqual(sum(v[0] for v in floors.values()), whole[0])
        for name, (square, today, offer) in list(floors.items()) + [("All six offices", whole)]:
            cost = rows.get(name, total)
            self.assertAlmostEqual(cost[0] * 1000 / square, today, delta=0.051, msg=name)
            self.assertAlmostEqual(cost[1] * 1000 / square, offer, delta=0.051, msg=name)
        options = {o: [r["values"][i] for r in page_of("comparison")["rows"]] for i, o in enumerate(page_of("comparison")["options"])}
        for cost, saving in ([v[0], v[1]] for v in options.values()):
            self.assertEqual(int(cost[4:].replace(",", "")) + int(saving[4:].replace(",", "")), 412000)

    def test_neither_preset_continues_a_page_or_splits_a_table(self):
        for preset in ("standard", "sparse"):
            path = built(density=preset)
            prs = Presentation(str(path))
            self.assertEqual(len(prs.slides), len(SAMPLE["pages"]), preset)
            self.assertFalse([s for s in prs.slides if "/" in s.shapes.title.text_frame.text[-6:]], preset)
            for slide in slides(prs, "table"):
                self.assertEqual(len(next(s for s in slide.shapes if s.has_table).table.rows), 8, preset)
            self.assertTrue(check("BDECK-FIT", path)[0], check("BDECK-FIT", path)[1])

    def test_a_table_that_cannot_continue_closes_its_rows_up_instead_of_leaving_the_page(self):
        """Seven rows, a head and a takeaway under it do not fit a sparse page at the preset's least row pitch,
        and a second page would hold three rows: the rows close up to the floor and everything stays inside."""
        kit = mk.Kit(mk.load_look(str(HERE / "look.json")), mk.load_density(), "sparse", "en-GB")
        prs = Presentation(str(built(density="sparse")))
        for slide in slides(prs, "table"):
            frame = next(s for s in slide.shapes if s.has_table)
            pitch = frame.table.rows[1].height / 12700.0 / kit.body_line
            self.assertLess(pitch, float(kit.build["row.min_pitch"]))
            self.assertGreaterEqual(pitch, float(kit.build["row.floor_pitch"]) - 0.01)
            take = shape(slide, "Takeaway")
            self.assertGreaterEqual(take.top, frame.top + frame.height)
            self.assertLessEqual((take.top + take.height) / 12700.0, kit.body_bottom + 0.5)

    def test_thousands_separators_beside_smaller_numbers_are_one_precision(self):
        self.assertTrue(check("BDECK-TABLE", built())[0])                         # 1,900 above 850
        mixed = copy.deepcopy(page_of("table", 1)["rows"])
        mixed[1][2] = "52"
        self.fails("BDECK-TABLE", built(data(table=[None, {"rows": mixed}])), "decimal places")
        self.assertEqual([bd.decimals(t, True) for t in ("1,900", "850", "7,400.5", "0.850", "12 000", "1.5")], [0, 0, 1, 3, 0, 1])


class Matrix(Base):
    def test_the_matrix_is_drawn_from_shapes_a_colleague_can_move(self):
        for preset in ("standard", "sparse"):
            prs = Presentation(str(built(density=preset)))
            slide = slides(prs, "matrix")[0]
            page = page_of("matrix")
            self.assertEqual([shape(slide, "Quadrant %s" % q).text_frame.text for q in ("top left", "top right", "bottom left", "bottom right")],
                             [page["quadrants"][q] for q in mk.QUADRANTS])
            self.assertEqual([shape(slide, k).text_frame.text for k in ("X axis", "X low", "X high", "Y axis", "Y low", "Y high")],
                             [page["x"]["name"], page["x"]["low"], page["x"]["high"], page["y"]["name"], page["y"]["low"], page["y"]["high"]])
            self.assertEqual(sorted(s.text_frame.text for s in shapes(slide, "Item label")), sorted(i["name"] for i in page["items"]))
            self.assertEqual(len(shapes(slide, "Item mark")), len(page["items"]))
            self.assertEqual(len(shapes(slide, "Quadrant highlight")), 1)
            self.assertFalse([s for s in slide.shapes if s.shape_type == 13], "the matrix is no picture")
            m = bd._matrix(bd.deck_of(built(density=preset)).slides[n("matrix") - 1])
            self.assertEqual(m["lit"], ["quadrant top left"])
            where = {i["name"]: i["quadrant"] for i in m["items"]}
            self.assertEqual(where, {"One contract": "quadrant top left", "Renegotiate contracts": "quadrant bottom left",
                                     "Keep three suppliers": "quadrant bottom left", "Own cleaning team": "quadrant bottom right"})
            # the highlighted quadrant's name is in full ink through the layout's second level, not a colour on a run
            name = shape(slide, "Quadrant top left")._element
            self.assertEqual(name.find(".//" + A + "pPr").get("lvl"), "1")
            self.assertIsNone(name.find(".//" + A + "rPr/" + A + "solidFill"))

    def test_a_dot_stands_where_the_data_puts_it(self):
        deck = bd.deck_of(built())
        m = bd._matrix(deck.slides[n("matrix") - 1])
        x0, y0, x1, y1 = m["box"]
        at = {i["name"]: i["at"] for i in m["items"]}
        order_x = sorted(page_of("matrix")["items"], key=lambda i: i["x"])
        order_y = sorted(page_of("matrix")["items"], key=lambda i: i["y"])
        self.assertEqual([i["name"] for i in order_x], sorted(at, key=lambda k: at[k][0]))
        self.assertEqual([i["name"] for i in order_y], sorted(at, key=lambda k: -at[k][1]))
        for name, (x, y) in at.items():
            self.assertTrue(x0 < x < x1 and y0 < y < y1, name)

    def test_a_matrix_keeps_its_shape_in_sparse(self):
        """Sparse sets a chart's takeaway under it; a matrix laid across the full width would be a strip, so its
        takeaway stands beside it."""
        prs = Presentation(str(built(density="sparse")))
        slide = slides(prs, "matrix")[0]
        m = bd._matrix(bd.deck_of(built(density="sparse")).slides[n("matrix") - 1])
        x0, y0, x1, y1 = m["box"]
        self.assertLessEqual((x1 - x0) / (y1 - y0), 2.2)
        self.assertGreaterEqual(shape(slide, "Takeaway").left / 12700.0, x1)
        self.assertTrue(check("BDECK-WORDS", built(density="sparse"))[0])        # the takeaway keeps to three lines there

    def test_matrix_rule(self):
        page = page_of("matrix")
        self.fails("BDECK-MATRIX", built(data(matrix={"highlight": None})), "highlights no quadrant")
        self.fails("BDECK-MATRIX", built(data(matrix={"title": "The four options differ in what they save and what they take"})),
                   "the title names neither it nor an item in it")
        self.assertTrue(check("BDECK-MATRIX", built(data(matrix={"title": "Only the options in Do now are worth starting this year"})))[0])
        same = dict(page["quadrants"], top_right="Do now")
        self.fails("BDECK-MATRIX", built(data(matrix={"quadrants": same})), "the same name")
        ends = dict(page["x"], high="Little")
        self.fails("BDECK-MATRIX", built(data(matrix={"x": ends})), "both ends of an axis")
        one = [page["items"][0]]
        self.fails("BDECK-MATRIX", built(data(matrix={"items": one})), "places 1 items", "at least 2")
        # two items on one spot: the builder sets their names clear of each other; set on top by hand, the rule says so
        close = page["items"][:1] + [{"name": "Two contracts", "x": 0.22, "y": 0.87}] + page["items"][1:]
        self.assertTrue(check("BDECK-MATRIX", built(data(matrix={"items": close})))[0])

        def stack(prs):
            first, second = shapes(slides(prs, "matrix")[0], "Item label")[:2]
            second.left, second.top = first.left, first.top
        self.fails("BDECK-MATRIX", built(edit=stack), "on top of each other")

        def drop(name):
            def edit(prs):
                el = shape(slides(prs, "matrix")[0], name)._element
                el.getparent().remove(el)
            return edit
        self.fails("BDECK-MATRIX", built(edit=drop("X low")), "the low end of its horizontal axis")
        self.fails("BDECK-MATRIX", built(edit=drop("Y axis")), "what its vertical axis measures")
        self.fails("BDECK-MATRIX", built(edit=drop("Quadrant bottom right")), "names 3 of its four quadrants")

        def two(prs):
            slide = slides(prs, "matrix")[0]
            lit = shape(slide, "Quadrant highlight")
            more = copy.deepcopy(lit._element)
            lit._element.addnext(more)
            more.find(".//" + A + "off").set("x", str(lit.left + lit.width))
        self.fails("BDECK-MATRIX", built(edit=two), "highlights 2 quadrants")

        def away(prs):
            slide = slides(prs, "matrix")[0]
            for s in shapes(slide, "Item mark")[:1] + shapes(slide, "Item label")[:1]:
                s.left = Emu(prs.slide_width - Pt(60))
        self.fails("BDECK-MATRIX", built(edit=away), "outside its axes")

        def turn(prs):
            shape(slides(prs, "matrix")[0], "Y axis").rotation = 270
        self.fails("BDECK-MATRIX", built(edit=turn), "at an angle")
        for rule in ("BDECK-ONE-IDEA", "BDECK-TYPE", "BDECK-CONTRAST", "BDECK-FIT", "BDECK-FILL"):
            self.assertTrue(check(rule, built())[0], rule)

    def test_the_builder_refuses_a_matrix_it_cannot_draw(self):
        page = page_of("matrix")
        refused(self, data(matrix={"x": {"name": "Effort"}}), "names both axes and both ends")
        refused(self, data(matrix={"quadrants": {"top_left": "Do now"}}), "names its four quadrants")
        refused(self, data(matrix={"items": [{"name": "One contract", "x": 22, "y": 88}]}), "0 at the low end")
        refused(self, data(matrix={"items": None}), "places its items")
        refused(self, data(matrix={"highlight": "Later"}), "none of its quadrants")
        long = [dict(page["items"][0], name="One contract for all six offices, with one site lead and a shared pool of cleaners")]
        refused(self, data(matrix={"items": long}), "too long for its quadrant")
        self.assertTrue(check("BDECK-MATRIX", built(data(matrix={"highlight": "top_left"})))[0])      # by its place, too


class Figure(Base):
    def test_the_figure_is_one_picture_whole_at_its_own_proportions(self):
        from PIL import Image
        with Image.open(TEMPLATES / page_of("figure")["image"]) as im:
            wide, high = im.size
        for preset in ("standard", "sparse"):
            path = built(density=preset)
            slide = slides(Presentation(str(path)), "figure")[0]
            pics = [s for s in slide.shapes if s._element.tag == P + "pic"]
            self.assertEqual(len(pics), 1)
            pic = pics[0]
            self.assertAlmostEqual(pic.width / float(pic.height), wide / float(high), places=2)
            self.assertEqual((pic.crop_left, pic.crop_right, pic.crop_top, pic.crop_bottom), (0, 0, 0, 0))
            self.assertTrue(pic.is_placeholder, "the picture sits in the layout's picture placeholder")
            self.assertEqual(pic._element.find(P + "nvPicPr/" + P + "cNvPr").get("descr"), page_of("figure")["alt"])
            self.assertEqual(shape(slide, "Caption").text_frame.text, page_of("figure")["caption"])
            take = shape(slide, "Takeaway")
            self.assertGreaterEqual(take.left, pic.left + pic.width, "%s: the takeaway is beside the picture" % preset)
            seen = bd.deck_of(path).slides[n("figure") - 1].pictures[0]
            self.assertEqual(seen.px, (wide, high))
            self.assertGreater(seen.ink, 0.02)

    def test_a_tall_picture_brings_its_takeaway_to_its_side(self):
        from PIL import Image, ImageDraw
        folder = Path(tempfile.mkdtemp())
        im = Image.new("RGB", (1000, 1414), "white")
        draw = ImageDraw.Draw(im)
        for y in range(120, 1300, 60):
            draw.rectangle([100, y, 900, y + 18], fill=(40, 40, 40))
        im.save(folder / "page.png")
        for preset in ("standard", "sparse"):
            path = built(data(figure={"image": "page.png"}), density=preset, folder=folder)
            slide = slides(Presentation(str(path)), "figure")[0]
            pic = next(s for s in slide.shapes if s._element.tag == P + "pic")
            self.assertAlmostEqual(pic.width / float(pic.height), 1000 / 1414.0, places=2)
            take = shape(slide, "Takeaway")
            self.assertAlmostEqual((take.left - pic.left - pic.width) / 12700.0, 2 * mk.Kit(
                mk.load_look(str(HERE / "look.json")), mk.load_density(), preset, "en-GB").G, delta=1)
            for rule in ("BDECK-FIGURE", "BDECK-FILL", "BDECK-FIT"):
                self.assertTrue(check(rule, path)[0], "%s, %s: %s" % (rule, preset, check(rule, path)[1]))

    def test_figure_rule(self):
        self.fails("BDECK-FIGURE", built(data(figure={"caption": None})), "has no caption")
        self.fails("BDECK-FIGURE", built(data(figure={"caption": page_of("figure")["title"]})), "repeats the title")
        self.fails("BDECK-FIGURE", built(data(figure={"alt": "proposal-audit-report.png"})), "say what the picture shows")
        self.fails("BDECK-SOURCE", built(data(figure={"source": None})), "shows a figure with no source line")

        def stretch(prs):
            pic = next(s for s in slides(prs, "figure")[0].shapes if s._element.tag == P + "pic")
            pic.height = int(pic.height * 0.7)
        self.fails("BDECK-FIGURE", built(edit=stretch), "is stretched", "keep its proportions")

        def shrink(prs):
            pic = next(s for s in slides(prs, "figure")[0].shapes if s._element.tag == P + "pic")
            pic.width, pic.height = int(pic.width * 0.4), int(pic.height * 0.4)
        self.fails("BDECK-FIGURE", built(edit=shrink), "covers 0.0", "show it larger")

        def second(prs):
            slide = slides(prs, "figure")[0]
            slide.shapes.add_picture(str(TEMPLATES / page_of("figure")["image"]), Pt(600), Pt(300), width=Pt(200))
        self.fails("BDECK-FIGURE", built(edit=second), "2 pictures")
        self.fails("BDECK-ONE-IDEA", built(edit=second), "one exhibit a page")
        from PIL import Image
        folder = Path(tempfile.mkdtemp())
        with Image.open(TEMPLATES / page_of("figure")["image"]) as im:
            im.convert("RGB").resize((300, 200)).save(folder / "small.png")
        self.fails("BDECK-FIGURE", built(data(figure={"image": "small.png"}), folder=folder), "pixels an inch", "use a larger file")

        def no_alt(prs):
            pic = next(s for s in slides(prs, "figure")[0].shapes if s._element.tag == P + "pic")
            pic._element.find(P + "nvPicPr/" + P + "cNvPr").set("descr", "")
        self.fails("BDECK-FILE", built(edit=no_alt), "has no alternative text")

    def test_the_builder_refuses_a_figure_it_cannot_show(self):
        refused(self, data(figure={"image": None}), "shows one picture")
        refused(self, data(figure={"image": "missing.png"}), "is not there", "beside the deck's data")
        folder = Path(tempfile.mkdtemp())
        (folder / "notes.png").write_text("not a picture")
        refused(self, data(figure={"image": "notes.png"}), "not a PNG, JPEG or GIF", folder=folder)
        alone = Path(tempfile.mkdtemp())
        shutil.copy(TEMPLATES / "proposal.deck.json", alone)                     # the data without its picture
        refused(self, None, str(alone), folder=alone)


class Quote(Base):
    def test_the_quote_is_the_layouts_largest_step_on_a_content_page_and_nothing_is_added(self):
        look = json.loads((HERE / "look.json").read_text())
        for preset in ("standard", "sparse"):
            path = built(density=preset)
            prs = Presentation(str(path))
            slide = slides(prs, "quote")[0]
            page = page_of("quote")
            self.assertEqual(shape(slide, "Quote").text_frame.text, page["quote"])            # the data's own marks, no others
            self.assertEqual(shape(slide, "Quote name").text_frame.text, page["name"])
            self.assertEqual(shape(slide, "Quote role").text_frame.text, page["role"])
            layout = next(la for la in prs.slide_layouts if la.name == "Quote")
            size = int(next(p for p in layout.placeholders if p.name == "Quote")._element.find(".//" + A + "lvl1pPr/" + A + "defRPr").get("sz")) / 100
            self.assertEqual(size, look["scale"][preset]["headline"][0])
            names = {s.name for s in slide.shapes}
            self.assertEqual(names, {"Title", "Quote", "Quote name", "Quote role", "Source", "Section", "Deck title", "Page number"})
            kit = mk.Kit(mk.load_look(str(HERE / "look.json")), mk.load_density(), preset, "en-GB")
            said, role = shape(slide, "Quote"), shape(slide, "Quote role")
            middle = (said.top + role.top + role.height) / 2.0 / 12700.0
            self.assertAlmostEqual(middle, (kit.body_top + kit.body_bottom) / 2.0, delta=2, msg="%s: the quote stands on the middle of the body" % preset)

    def test_quote_rule(self):
        two = "“I lose a day every month chasing three suppliers. Nobody thanks me for it.”"
        self.fails("BDECK-QUOTE", built(data(quote={"quote": two})), "quotes 2 sentences", "quote one")
        long = "“" + " ".join(["I lose a day every month chasing three suppliers about cleans"] * 3) + ".”"
        self.fails("BDECK-QUOTE", built(data(quote={"quote": long})), "runs to 33 words", "holds 30")
        self.fails("BDECK-QUOTE", built(data(quote={"quote": "“Cleaning is a mess.”"})), "4 words", "a slogan")
        self.fails("BDECK-QUOTE", built(data(quote={"role": "Jordan Example"})), "gives no role for Jordan Example")
        again = copy.deepcopy(SAMPLE)
        more = dict(page_of("quote"), title="Every office manager says the same about three suppliers",
                    quote="“Three suppliers means three people to ring every time a clean is missed.”")
        again["pages"].insert(n("quote"), more)
        self.fails("BDECK-QUOTE", built(again), "2 quote pages", "holds 1")

        def blank(prs):
            el = shape(slides(prs, "quote")[0], "Quote role")._element
            el.getparent().remove(el)
        self.fails("BDECK-QUOTE", built(edit=blank), "gives no role")

        def italic(prs):
            for run in shape(slides(prs, "quote")[0], "Quote").text_frame.paragraphs[0].runs:
                run.font.italic = True
        self.fails("BDECK-QUOTE", built(edit=italic), "dresses its quote with italics")

        def framed(prs):
            said = shape(slides(prs, "quote")[0], "Quote")
            said.fill.solid()
            said.fill.fore_color.rgb = RGBColor(0xF2, 0xF2, 0xF2)
        self.fails("BDECK-QUOTE", built(edit=framed), "a panel")

        def ornament(prs):
            box = slides(prs, "quote")[0].shapes.add_textbox(Pt(44), Pt(130), Pt(80), Pt(80))
            box.text_frame.text = "“"
            box.text_frame.paragraphs[0].runs[0].font.size = Pt(96)
        self.fails("BDECK-QUOTE", built(edit=ornament), "a quotation mark as an ornament")
        self.assertEqual([bd.sentences(t) for t in ("“One. Two.”", "It cost us 3.5 days, e.g. in March.", "Is it done? Yes.", "«Una frase sola.»")],
                         [2, 1, 2, 1])

    def test_the_builder_refuses_a_quote_nobody_said(self):
        refused(self, data(quote={"name": None}), "who said it and their role")
        refused(self, data(quote={"quote": ""}), "one sentence somebody said")


class Appendix(Base):
    def test_backup_pages_keep_their_own_count_and_the_appendix_lists_them(self):
        for preset in ("standard", "sparse"):
            path = built(density=preset)
            prs = Presentation(str(path))
            deck = bd.deck_of(path)
            divider = slides(prs, "appendix")[0]
            self.assertEqual(divider.shapes.title.text_frame.text, "Appendix")
            listed = [(shape(divider, "Backup %d number" % i).text_frame.text, shape(divider, "Backup %d" % i).text_frame.text) for i in (1, 2)]
            self.assertEqual(listed, [("A1", page_of("table", 1)["title"]), ("A2", page_of("text")["title"])])
            behind = [s for s in deck.slides if s.backup]
            self.assertEqual([s.kind for s in behind], ["table", "text"])
            for count, s in enumerate(behind, 1):
                number = next(t for t in s.texts if t.kind == "number")
                self.assertEqual(number.text, "A%d" % count)
                self.assertEqual(s.one("section").text, "Appendix")
            numbered = [next(t for t in s.texts if t.kind == "number").text for s in deck.slides if not s.backup and s.kind != "cover"]
            self.assertEqual(set(numbered), {"‹#›"}, "a page of the storyline is numbered by its place, with the slide-number field")
            self.assertEqual(bd.page_count(deck), 13)

    def test_backup_pages_stand_outside_the_storyline_rules_and_inside_the_others(self):
        short = copy.deepcopy(SAMPLE)
        keep = ("cover", "chart", "comparison", "figures", "timeline", "next-steps", "closing", "appendix")
        cut = [p for i, p in enumerate(short["pages"]) if p["type"] in keep or i > n("appendix") - 1]
        short["pages"] = cut
        path = built(short)
        deck = bd.deck_of(path)
        self.assertEqual((len(deck.slides), bd.page_count(deck)), (10, 7))
        for rule in ("BDECK-STORYLINE", "BDECK-NEXT-STEPS", "BDECK-APPENDIX"):       # seven pages need no summary; the close is the close
            self.assertTrue(check(rule, path)[0], "%s: %s" % (rule, check(rule, path)[1]))
        self.fails("BDECK-TITLE", built(data(table=[None, {"title": "Floor areas"}])), "slide %d" % n("table", 1), "topic label")
        self.fails("BDECK-SOURCE", built(data(table=[None, {"source": None}])), "slide %d" % n("table", 1))
        thin = {"rows": page_of("table", 1)["rows"][:3], "takeaway": None, "points": None, "head": None}
        self.fails("BDECK-FILL", built(data(table=[None, thin])), "slide %d" % n("table", 1))

    def test_a_continued_backup_page_takes_two_numbers_and_one_line_of_the_list(self):
        long = [["Office %d" % i, "1,%d00" % (i % 10), "5%d.0" % (i % 10), "4%d.0" % (i % 10)] for i in range(1, 15)]
        path = built(data(table=[None, {"rows": long}]), density="sparse")
        deck = bd.deck_of(path)
        behind = [s for s in deck.slides if s.backup]
        self.assertEqual([next(t for t in s.texts if t.kind == "number").text for s in behind], ["A1", "A2", "A3", "A4"])
        divider = slides(Presentation(str(path)), "appendix")[0]
        self.assertEqual([s.text_frame.text for s in divider.shapes if s.name.startswith("Backup") and s.name.endswith("number")], ["A1", "A4"])
        self.assertTrue(check("BDECK-APPENDIX", path)[0], check("BDECK-APPENDIX", path)[1])

    def test_the_appendix_takes_its_letter_from_its_name_or_from_the_data(self):
        for change, mark in (({"title": "Backup"}, "B1"), ({"mark": "x"}, "X1"), ({"title": "Bilagor"}, "B1")):
            deck = bd.deck_of(built(data(appendix=change)))
            first = next(s for s in deck.slides if s.backup)
            self.assertEqual(next(t for t in first.texts if t.kind == "number").text, mark)
            self.assertEqual(first.one("section").text, change.get("title", "Appendix"))
            self.assertTrue(check("BDECK-APPENDIX", deck.path)[0])
        refused(self, data(appendix={"title": "2026 backup"}), "under a letter")

    def test_appendix_rule(self):
        def renumber(text):
            def edit(prs):
                slide = slides(prs, "table")[1]
                shape(slide, "Page number").text_frame.paragraphs[0].runs[0].text = text
            return edit
        self.fails("BDECK-APPENDIX", built(edit=renumber("15")), "numbered as a page of the storyline", "A1, A2")
        self.fails("BDECK-APPENDIX", built(edit=renumber("A7")), "numbered A7 where the appendix's count is at 1")
        self.fails("BDECK-APPENDIX", built(edit=renumber("B1")), "one letter for the whole appendix")

        def relabel(prs):
            shape(slides(prs, "text")[0], "Section").text_frame.paragraphs[0].runs[0].text = "Offer"
        self.fails("BDECK-APPENDIX", built(edit=relabel), "carries the appendix's name")
        open_end = copy.deepcopy(SAMPLE)
        open_end["pages"] = [p for p in open_end["pages"] if p["type"] != "closing"]
        self.fails("BDECK-APPENDIX", built(open_end), "opens before the deck has closed")

        def empty(prs):
            ids = prs.slides._sldIdLst
            for sld in list(ids)[-2:]:
                prs.part.drop_rel(sld.rId)
                ids.remove(sld)
        self.fails("BDECK-APPENDIX", built(edit=empty), "no backup page behind it")

    def test_the_builder_refuses_an_appendix_that_is_not_the_last_part(self):
        late = copy.deepcopy(SAMPLE)
        late["pages"].append(late["pages"].pop(n("closing") - 1))
        refused(self, late, "(closing) stands behind the appendix page", "comes last, after the closing page")
        twice = copy.deepcopy(SAMPLE)
        twice["pages"].append({"type": "appendix", "title": "More"})
        refused(self, twice, "2 appendix pages")
        bare = copy.deepcopy(SAMPLE)
        bare["pages"] = bare["pages"][:n("appendix")]
        refused(self, bare, "no backup page behind it")


class RealRun(Base):
    """What a real run by a small model showed on 2026-10-10 (a board update from a page of notes), kept fixed."""

    BOARD = json.loads((TEMPLATES / "board-update.deck.json").read_text(encoding="utf-8"))

    def board(self, **change):
        deck = copy.deepcopy(self.BOARD)
        for kind, new in change.items():
            next(p for p in deck["pages"] if p["type"] == kind).update(new)
        return deck

    def test_a_series_named_plan_is_no_placeholder(self):
        chart = {"kind": "line", "categories": ["April", "May", "June", "July"], "highlight": "Shipped on time",
                 "title": "Orders shipped on time fell under the plan from June",
                 "series": [{"name": "Shipped on time", "values": [96, 95, 93, 91]}, {"name": "Plan", "values": [95, 95, 95, 95]}]}
        path = built(self.board(chart=chart), name="Board update Q3 2026.pptx")
        for rule in ("BDECK-PLACEHOLDER", "BDECK-HIGHLIGHT", "BDECK-CHART-LABELS"):
            self.assertTrue(check(rule, path)[0], "%s: %s" % (rule, check(rule, path)[1]))

    def test_one_line_is_drawn_in_ink_on_a_scale_that_shows_its_change(self):
        chart = {"kind": "line", "highlight": "Q3 2026", "series": [{"name": "Revenue", "values": [5.1, 5.4, 5.6, 5.8, 6.2]}]}
        path = built(self.board(chart=chart), name="Board update Q3 2026.pptx")
        deck = bd.deck_of(path)
        seen = next(s for s in deck.slides if s.kind == "chart").charts[0]
        self.assertEqual(seen.series[0]["colour"], (0x1A, 0x1C, 0x1F), "a single line is the page's subject, not a grey line")
        self.assertGreater(seen.axis_min, 4.0)
        self.assertLess(seen.axis_min, 5.1)
        self.assertLess(seen.axis_max, 7.0)
        for rule in ("BDECK-CHART-HONEST", "BDECK-FILL", "BDECK-CHART-LABELS"):
            self.assertTrue(check(rule, path)[0], "%s: %s" % (rule, check(rule, path)[1]))
        # lines that come near zero keep the zero, and bars always do
        both = bd.deck_of(built(self.BOARD, name="Board update Q3 2026.pptx"))
        charts = [s.charts[0] for s in both.slides if s.charts]
        self.assertEqual([c.axis_min for c in charts], [0.0, 0.0])
        self.fails("BDECK-CHART-HONEST", built(self.board(chart={"axis_min": 12}), name="Board update Q3 2026.pptx"), "start the axis at zero")

    def test_a_running_line_too_long_for_its_line_is_refused_with_a_length(self):
        long = dict(self.BOARD, title="Example Software Ltd: board update for the third quarter of 2026 and the investment case")
        refused(self, long, "the deck's title", "one line of small print", "keep it to about")
        deck = self.board(chart={"section": "Results for the third quarter of the financial year 2026"})
        refused(self, deck, "page 4's section name", "keep it to about")

    def test_a_percent_sign_given_as_the_unit_joins_its_figure(self):
        figures = [{"label": "Gross margin", "value": "31", "unit": "%", "period": "Q3 2026", "note": "One point above plan."},
                   {"label": "Cash at quarter end", "value": "1.9", "unit": "GBP million", "period": "30 September 2026", "note": "0.2 ahead of plan."},
                   {"label": "Order book", "value": "4.4", "unit": "GBP million", "period": "30 September 2026", "note": "3.6 a year ago."}]
        prs = Presentation(str(built(self.board(figures={"figures": figures}), name="Board update Q3 2026.pptx")))
        slide = slides(prs, "figures")[0]
        self.assertEqual(shape(slide, "Figure 1").text_frame.text, "31%")
        self.assertEqual(shape(slide, "Figure 1 text").text_frame.paragraphs[0].text, "Q3 2026")
        self.assertEqual(shape(slide, "Figure 2 text").text_frame.paragraphs[0].text, "GBP million, 30 September 2026")

    def test_the_agendas_sections_are_the_pages_sections(self):
        agenda = {"items": [{"name": "Results"}, {"name": "Customers"}, {"name": "Plan"}, {"name": "Risks"}]}
        why = self.fails("BDECK-STORYLINE", built(self.board(agenda=agenda), name="Board update Q3 2026.pptx"), "the agenda lists 'Risks'", "no page carries")
        stray = self.board(timeline={"section": "Next steps"})
        self.fails("BDECK-STORYLINE", built(stray, name="Board update Q3 2026.pptx"), "carries the section 'Next steps'", "the agenda does not list")
        self.assertNotIn("Next steps", why)

    def test_a_measure_that_prints_like_its_bound_is_told_apart(self):
        self.assertEqual(bd.two(0.166, 0.17), ("0.166", "0.170"))
        self.assertEqual(bd.two(0.12, 0.17), ("0.12", "0.17"))

    def test_the_stop_hooks_call_stands_down_where_a_run_by_hand_fails(self):
        path = built()
        real, argv = bd.deck_of, sys.argv

        def no_pptx(_):
            raise ImportError("No module named 'pptx'")
        bd.deck_of = no_pptx
        kept = os.environ.get("BDECK_UV")
        os.environ["BDECK_UV"] = "1"            # as if uv had been tried: the check must not start itself again from a test
        try:
            self.assertIsNone(bd._through_uv())
            sys.argv = ["packcheck.py", "business-deck", str(path), "--if-claimed", "--in", str(path.parent)]
            self.assertIsNone(bd._through_uv())
            for rule in bd.RULES:
                ok, why = check(rule, path)
                self.assertIn("could not check", why, "the hook's call says nothing it would bounce on")
            sys.argv = ["packcheck.py", "business-deck", str(path)]
            self.assertIn("nothing was checked", check(bd.RULES[0], path)[1])
        finally:
            bd.deck_of, sys.argv = real, argv
            if kept is None:
                os.environ.pop("BDECK_UV", None)
            else:
                os.environ["BDECK_UV"] = kept

    def test_text_given_as_a_list_is_refused_by_name_and_a_column_needs_its_heading(self):
        """The re-run printed a Python list as a table's head, over a header row with no words in it."""
        refused(self, data(table={"head": ["Office", "Today", "Offer"]}), '"head" is one line of text and was given a list',
                'the column headings go in "columns"')
        refused(self, data(chart={"points": "The six offices cost GBP 412,000 a year together"}), '"points" is a list and was given text')
        refused(self, data(figure={"caption": {"text": "Monthly audit report"}}), '"caption" is one line of text')
        self.fails("BDECK-TABLE", built(data(table={"columns": ["Office", "", "Offer", "Saving"]})), "no heading over column 2", "name every column")
        self.assertTrue(check("BDECK-TABLE", built())[0])                         # a comparison's label column needs none

        def leak(prs):
            shape(slides(prs, "table")[0], "Table head").text_frame.paragraphs[0].runs[0].text = \
                "['Q3 performance measure', 'Target %', 'Actual %', 'Difference']"
        self.fails("BDECK-PLACEHOLDER", built(edit=leak), "filler text")

    def test_a_table_that_is_the_whole_page_sits_on_the_middle_of_the_body(self):
        """Four actions without a line of detail each are a whole next-steps page, not a page that hangs."""
        deck = copy.deepcopy(SAMPLE)
        for step in page_of("next-steps")["steps"]:
            pass
        steps = [{k: v for k, v in step.items() if k != "detail"} for step in page_of("next-steps")["steps"]]
        for preset in ("standard", "sparse"):
            kit = mk.Kit(mk.load_look(str(HERE / "look.json")), mk.load_density(), preset, "en-GB")
            path = built(data(next_steps={"steps": steps}), density=preset)
            prs = Presentation(str(path))
            for kind in ("next-steps", "comparison"):
                frame = next(s for s in slides(prs, kind)[0].shapes if s.has_table)
                middle = (frame.top + sum(r.height for r in frame.table.rows) / 2.0) / 12700.0
                self.assertAlmostEqual(middle, (kit.body_top + kit.body_bottom) / 2.0, delta=1.5, msg="%s, %s" % (kind, preset))
            self.assertTrue(check("BDECK-FILL", path)[0], "%s: %s" % (preset, check("BDECK-FILL", path)[1]))
        one = [dict(steps[0])]
        self.fails("BDECK-FILL", built(data(next_steps={"steps": one})), "slide %d" % n("next-steps"))       # one action is still no page


class Knobs(Base):
    def test_turning_a_new_knob_turns_the_verdict(self):
        path = built()
        turns = {"matrix.min_items": ("BDECK-MATRIX", 99), "matrix.max_items": ("BDECK-MATRIX", 1),
                 "quote.min_words": ("BDECK-QUOTE", 99), "quote.max_words": ("BDECK-QUOTE", 3), "quotes.max": ("BDECK-QUOTE", 0),
                 "figure.min_ppi": ("BDECK-FIGURE", 9999), "figure.min_share": ("BDECK-FIGURE", 0.99),
                 "caption.max_lines": ("BDECK-FIGURE", 0), "fill.quote_min": ("BDECK-FILL", 0.99)}
        base = dict(bd.deck_of(path).d)
        for key, (rule, value) in turns.items():
            self.assertIn(key, base)
            self.assertTrue(check(rule, path)[0], "%s before %s is turned" % (rule, key))
            deck = bd.deck_of(path)
            deck.d = dict(base, **{key: value})
            verdict = check(rule, path)[0]
            deck.d = base
            self.assertFalse(verdict, "%s still passes with %s at %s" % (rule, key, value))

    def test_a_check_that_could_read_nothing_is_not_a_clean_check(self):
        """Without python-pptx the pack check skips every rule it cannot run; one rule fails and says how to run
        the check, so the last line is never 'pack check clean: 0 rules passed'."""
        path = built()
        real = bd.deck_of

        def no_pptx(_):
            raise ImportError("No module named 'pptx'")
        bd.deck_of = no_pptx
        try:
            ok, why = check(bd.RULES[0], path)
            self.assertFalse(ok)
            self.assertIn("nothing was checked", why)
            self.assertIn("pip install python-pptx", why)
            self.assertNotIn("could not", why)                # the pack check reads "could not" as a skip
            for rule in bd.RULES[1:]:
                ok, why = check(rule, path)
                self.assertFalse(ok)
                self.assertIn("could not check", why)
        finally:
            bd.deck_of = real
        self.assertTrue(check(bd.RULES[0], path)[0])

    def test_the_new_rules_have_nothing_to_say_about_a_deck_without_these_pages(self):
        board = json.loads((TEMPLATES / "board-update.deck.json").read_text(encoding="utf-8"))
        path = built(board, name="Board update Q3 2026.pptx")
        for rule in NEW:
            ok, why = check(rule, path)
            self.assertTrue(ok, why)
            self.assertIn("no ", why)


if __name__ == "__main__":
    unittest.main()
