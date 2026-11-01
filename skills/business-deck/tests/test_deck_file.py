"""Offline tests of the PowerPoint file itself, for what nobody can see without opening PowerPoint: the package is
whole (parts, content types, relationships, ids), every chart carries the workbook "Edit data" opens with the
numbers the chart shows, and the look is the theme's, so changing the theme's ink or face restyles every page."""
import io
import json
import posixpath
import re
import sys
import tempfile
import unittest
import zipfile
from collections import Counter
from pathlib import Path

from lxml import etree

HERE = Path(__file__).resolve().parents[1]
TEMPLATES = HERE / "templates"
sys.path.insert(0, str(HERE / "scripts"))
sys.path.insert(0, str(HERE.parent / "_checks"))
import business_deck as bd  # noqa: E402
import deck_build as mk  # noqa: E402

A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
C = "{http://schemas.openxmlformats.org/drawingml/2006/chart}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
SAMPLES = {"board-update": "Board update Q3 2026.pptx", "proposal": "Cleaning proposal 2026.pptx"}
_BUILT = {}


def built(sample, density="standard"):
    key = (sample, density)
    if key not in _BUILT:
        out = Path(tempfile.mkdtemp(prefix="bdeck-file-")) / SAMPLES[sample]
        deck = json.loads((TEMPLATES / ("%s.deck.json" % sample)).read_text(encoding="utf-8"))
        mk.build(deck, str(out), density, None, str(TEMPLATES))
        _BUILT[key] = out
    return _BUILT[key]


def parts(path):
    z = zipfile.ZipFile(path)
    return z, {n: etree.fromstring(z.read(n), etree.XMLParser(recover=False)) for n in z.namelist() if n.endswith((".xml", ".rels"))}


def restyled(path, ink="0B5FFF", face="Georgia"):
    """A copy of the deck with the theme's first text colour and its faces changed, and nothing else: what
    Design > Variants > Colours and Fonts do in PowerPoint."""
    out = Path(tempfile.mkdtemp(prefix="bdeck-file-")) / path.name
    zin = zipfile.ZipFile(path)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if re.match(r"ppt/theme/theme\d+\.xml$", item.filename):
                text = data.decode("utf-8")
                text, n = re.subn(r'(<a:dk1>\s*<a:srgbClr val=")[0-9A-Fa-f]{6}', r"\g<1>" + ink, text)
                text, m = re.subn(r'(<a:(?:major|minor)Font>\s*<a:latin typeface=")[^"]*', r"\g<1>" + face, text)
                # theme1 is the slide master's; the notes pages bring a theme of their own that no slide reads
                if item.filename.endswith("/theme1.xml"):
                    assert n == 1 and m == 2
                    data = text.encode("utf-8")
            zout.writestr(item, data)
    return out


class Package(unittest.TestCase):
    def test_every_part_is_typed_related_and_parses(self):
        for sample in SAMPLES:
            for density in ("standard", "sparse"):
                z, trees = parts(built(sample, density))
                names = z.namelist()
                self.assertIsNone(z.testzip())
                self.assertEqual(len(names), len({n.lower() for n in names}))
                types = trees["[Content_Types].xml"]
                defaults = {d.get("Extension").lower() for d in types if d.tag.endswith("Default")}
                overrides = {o.get("PartName").lstrip("/") for o in types if o.tag.endswith("Override")}
                self.assertFalse([n for n in names if n != "[Content_Types].xml" and n not in overrides
                                  and n.rsplit(".", 1)[-1].lower() not in defaults], "a part without a content type")
                self.assertFalse(overrides - set(names), "a content type for a part that is not there")
                targets = set()
                for n, tree in trees.items():
                    if not n.endswith(".rels"):
                        continue
                    folder = posixpath.dirname(posixpath.dirname(n))
                    ids = [rel.get("Id") for rel in tree]
                    self.assertEqual(len(ids), len(set(ids)), n)
                    for rel in tree:
                        if rel.get("TargetMode") != "External":
                            target = posixpath.normpath(posixpath.join(folder, rel.get("Target")))
                            self.assertIn(target, names, "%s leads to a part that is not there" % n)
                            targets.add(target)
                    owner = posixpath.join(folder, posixpath.basename(n)[:-5])
                    if owner in trees:
                        used = {v for el in trees[owner].iter() for k, v in el.attrib.items() if k.startswith(R)}
                        self.assertFalse(used - set(ids), "%s uses a relationship it does not have" % owner)
                self.assertFalse([n for n in names if not n.endswith(".rels") and n != "[Content_Types].xml" and n not in targets],
                                 "a part nothing refers to")

    def test_no_id_is_used_twice(self):
        """Duplicate shape, slide or layout ids are what PowerPoint offers to repair a file for."""
        for sample in SAMPLES:
            z, trees = parts(built(sample))
            pres = trees["ppt/presentation.xml"]
            slide_ids = [int(e.get("id")) for e in pres.iter(P + "sldId")]
            self.assertEqual(len(slide_ids), len(set(slide_ids)))
            self.assertTrue(all(256 <= i < 2147483648 for i in slide_ids))
            big = [int(e.get("id")) for e in pres.iter(P + "sldMasterId")]
            for n, tree in trees.items():
                if n.startswith("ppt/slideMasters/slideMaster"):
                    big += [int(e.get("id")) for e in tree.iter(P + "sldLayoutId")]
                if re.match(r"ppt/(slides|slideLayouts|slideMasters)/[^/]+\.xml$", n):
                    ids = Counter(e.get("id") for e in tree.iter(P + "cNvPr"))
                    self.assertFalse([i for i, c in ids.items() if c > 1], "%s uses a shape id twice" % n)
                    for body in list(tree.iter(P + "txBody")) + list(tree.iter(A + "txBody")):
                        self.assertIsNotNone(body.find(A + "bodyPr"), n)
                        self.assertIsNotNone(body.find(A + "p"), n)
            self.assertEqual(len(big), len(set(big)))
            self.assertTrue(all(i >= 2147483648 for i in big))
            self.assertEqual(len(big), 1 + len(mk.LAYOUTS))

    def test_every_chart_carries_the_workbook_edit_data_opens_with_the_charts_own_numbers(self):
        seen = 0
        for sample in SAMPLES:
            z, trees = parts(built(sample))
            for n, tree in trees.items():
                if not re.match(r"ppt/charts/chart\d+\.xml$", n):
                    continue
                link = tree.find(C + "externalData")
                self.assertIsNotNone(link, "%s has no data sheet" % n)
                rels = trees["ppt/charts/_rels/%s.rels" % posixpath.basename(n)]
                target = next(r.get("Target") for r in rels if r.get("Id") == link.get(R + "id"))
                book = zipfile.ZipFile(io.BytesIO(z.read(posixpath.normpath(posixpath.join("ppt/charts", target)))))
                strings = ["".join(t.text or "" for t in si.iter(S + "t")) for si in etree.fromstring(book.read("xl/sharedStrings.xml"))]
                cells = {}
                for cell in etree.fromstring(book.read("xl/worksheets/sheet1.xml")).iter(S + "c"):
                    v = cell.find(S + "v")
                    if v is not None:
                        cells[cell.get("r")] = strings[int(v.text)] if cell.get("t") == "s" else v.text
                for ref in list(tree.iter(C + "numRef")) + list(tree.iter(C + "strRef")):
                    col0, row0, col1, row1 = re.fullmatch(r"Sheet1!\$([A-Z]+)\$(\d+)(?::\$([A-Z]+)\$(\d+))?", ref.findtext(C + "f")).groups()
                    self.assertEqual(col1 or col0, col0)
                    sheet = [cells["%s%d" % (col0, r)] for r in range(int(row0), int(row1 or row0) + 1)]
                    cache = [pt.findtext(C + "v") for pt in ref.iter(C + "pt")]
                    self.assertEqual(len(sheet), len(cache))
                    for a, b in zip(sheet, cache):
                        if ref.tag == C + "numRef":
                            self.assertAlmostEqual(float(a), float(b), places=9)
                        else:
                            self.assertEqual(a, b)
                    seen += 1
        self.assertGreaterEqual(seen, 15)       # three charts, each series with its name, its categories and its values


class Look(unittest.TestCase):
    def test_the_looks_colours_are_the_themes_and_the_face_is_the_themes(self):
        for sample in SAMPLES:
            z, trees = parts(built(sample))
            for n, tree in trees.items():
                if re.match(r"ppt/(slides|charts|slideMasters)/[^/]+\.xml$", n):
                    self.assertFalse([e.get("val") for e in tree.iter(A + "srgbClr")], "%s fixes a colour the theme should carry" % n)
                if re.match(r"ppt/(slides|charts|slideMasters|slideLayouts)/[^/]+\.xml$", n):
                    self.assertEqual({e.get("typeface") for e in tree.iter(A + "latin")} - {"+mn-lt", "+mj-lt"}, set(), n)
            theme = trees["ppt/theme/theme1.xml"]
            look = json.loads((HERE / "look.json").read_text())
            self.assertEqual(theme.find(".//" + A + "dk1/" + A + "srgbClr").get("val"), look["ink"]["ink"])
            self.assertEqual(theme.find(".//" + A + "minorFont/" + A + "latin").get("typeface"), look["face"]["name"])
            self.assertFalse([n for n in z.namelist() if n.startswith("ppt/fonts/")], "no font is embedded")

    def test_changing_the_themes_ink_and_face_restyles_every_page(self):
        blue, old = (0x0B, 0x5F, 0xFF), (0x1A, 0x1C, 0x1F)
        for sample in SAMPLES:
            before = bd.deck_of(built(sample))
            inked = {s.n: sum(1 for t in s.texts for p in t.paras if p.colour == old) for s in before.slides}
            after = bd.Deck(restyled(built(sample)))
            self.assertEqual(after.face, "Georgia")
            for s in after.slides:
                colours = [p.colour for t in s.texts for p in t.paras]
                colours += [p.colour for table in s.tables for row in table.rows for cell in row for p in cell.paras]
                self.assertNotIn(old, colours, "slide %d keeps the old ink" % s.n)
                self.assertEqual(sum(1 for t in s.texts for p in t.paras if p.colour == blue), inked[s.n], "slide %d" % s.n)
                if s.content():
                    self.assertEqual(s.title.paras[0].colour, blue)
                for chart in s.charts:
                    marks = [x["colour"] for x in chart.series] + [c for x in chart.series for c in x["points"].values()]
                    self.assertIn(blue, marks, "slide %d's highlight follows the ink" % s.n)
                    self.assertNotIn(old, marks)
            # the check reads the restyled deck through its theme: contrast, type and the highlight still hold
            # (fit is another matter: a wider face needs more room, and the check says so)
            for rule in ("BDECK-CONTRAST", "BDECK-HIGHLIGHT", "BDECK-TYPE", "BDECK-MATRIX"):
                ok, why = bd.RULE[rule](after)
                self.assertTrue(ok, "%s after the restyle: %s" % (rule, why))

    def test_a_company_accent_has_its_own_place_in_the_theme(self):
        look = json.loads((HERE / "look.json").read_text())
        look["marks"]["highlight"] = "0B5FFF"
        file = Path(tempfile.mkdtemp()) / "look.json"
        file.write_text(json.dumps(look))
        out = Path(tempfile.mkdtemp()) / "Board update Q3 2026.pptx"
        deck = json.loads((TEMPLATES / "board-update.deck.json").read_text(encoding="utf-8"))
        mk.build(deck, str(out), "standard", str(file))
        z, trees = parts(out)
        self.assertEqual(trees["ppt/theme/theme1.xml"].find(".//" + A + "accent1/" + A + "srgbClr").get("val"), "0B5FFF")
        chart = trees["ppt/charts/chart1.xml"]
        self.assertIn("accent1", [e.get("val") for e in chart.iter(A + "schemeClr")])
        self.assertIn("tx1", [e.get("val") for e in trees["ppt/slideLayouts/slideLayout5.xml"].iter(A + "schemeClr")])



class Floor(unittest.TestCase):
    """The floor under every file reads a deck's text at the size it is set in. The ppt-master bench of 2026-10-10
    showed FLOOR-OVERFLOW failing every deck this pack builds, its own samples included: a run with no size of its
    own was read as 18 pt though its layout sets it, so the model was sent back to mend pages that were whole."""

    def test_both_samples_meet_the_overflow_floor_in_every_density(self):
        import floor
        for sample in ("board-update", "proposal"):
            for density in ("sparse", "standard", "full"):
                bad, seen = floor.pptx_overflow(str(built(sample, density)))
                self.assertGreater(seen, 50, "%s %s: the check read the deck's text" % (sample, density))
                self.assertEqual(bad, [], "%s %s" % (sample, density))

    def test_text_is_read_at_the_size_its_layout_sets(self):
        import floor
        from pptx import Presentation
        prs = Presentation(str(built("board-update")))
        sizes = set()
        for slide in prs.slides:
            title = slide.shapes.title
            if title is None or any(r.font.size for p in title.text_frame.paragraphs for r in p.runs):
                continue
            node = title._base_placeholder._element.find(".//" + floor.A + "lvl1pPr/" + floor.A + "defRPr")
            self.assertEqual(floor.pptx_text_size(slide, title), int(node.get("sz")) / 100.0)
            sizes.add(floor.pptx_text_size(slide, title))
        self.assertTrue(sizes and 18.0 not in sizes, sizes)

    def test_text_that_does_not_fit_its_box_still_fails(self):
        import floor
        from pptx import Presentation
        from pptx.enum.text import MSO_AUTO_SIZE
        from pptx.util import Pt
        path = Path(tempfile.mkdtemp(prefix="bdeck-floor-")) / "Overflowing.pptx"
        prs = Presentation(str(built("board-update")))
        # a title with ten times its words, in the placeholder and at the layout's size
        slide = next(s for s in prs.slides if s.shapes.title is not None and s.slide_layout.name == "Chart")
        slide.shapes.title.text_frame.paragraphs[0].runs[0].text = " ".join(
            ["Recurring revenue reached EUR 18.4 million in the third quarter"] * 10)
        # and a drawn box with a sentence at a size written on the run
        last = prs.slides[len(prs.slides) - 1]
        box = last.shapes.add_textbox(Pt(40), Pt(40), Pt(120), Pt(20))
        box.text_frame.word_wrap = True
        box.text_frame.auto_size = MSO_AUTO_SIZE.NONE       # a box that grows with its text cannot overflow
        run = box.text_frame.paragraphs[0].add_run()
        run.text = "This sentence is set at fourteen points in a box one line high and cannot fit it"
        run.font.size = Pt(14)
        prs.save(str(path))
        bad, _ = floor.pptx_overflow(str(path))
        self.assertEqual(len(bad), 2, bad)
        self.assertIn("slide %d " % (list(prs.slides).index(slide) + 1), bad[0])
        self.assertIn("at 14 pt", bad[1])

    def test_lines_break_between_words_at_the_fonts_widths(self):
        import floor
        self.assertEqual(floor.wrapped_lines("Own cleaning team", 12, 105), 1)
        self.assertEqual(floor.wrapped_lines("Own cleaning team", 12, 80), 2)
        self.assertEqual(floor.wrapped_lines("WWWWWWWWWW", 10, 30), 4)       # a word wider than its box breaks inside
        self.assertLess(floor.text_width("illicit", 10), floor.text_width("MMMMMMM", 10) / 2)
        self.assertEqual(floor.text_width("ab", 10, tracking=-0.4), floor.text_width("ab", 10) - 0.8)


if __name__ == "__main__":
    unittest.main()
