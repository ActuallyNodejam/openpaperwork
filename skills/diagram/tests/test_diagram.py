"""The diagram kind: every starter builds and passes its own check, and every rule fails the defect it names.

Standard library only (the PDF and PNG a real build prints are stood in for by small valid files of the right
size, so no browser is needed):
    python3 -m unittest skills/diagram/tests/test_diagram.py
"""
import json
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
CHECKS = SKILL.parent / "_checks"
sys.path.insert(0, str(SKILL / "scripts"))
sys.path.insert(0, str(CHECKS))
import diagram  # noqa: E402
import diagram_check  # noqa: E402

TYPES = ("flowchart", "swimlane", "org-chart", "timeline", "gantt", "quadrant", "layers")


def fake_png(path, width, height, reach):
    """A white PNG width x height whose ink is one black pixel ending at reach (x, y), as a capture whose
    drawing reaches that far."""
    white = b"\x00" + b"\xff" * (3 * width)
    x, y = reach
    inked = b"\x00" + b"\xff" * (3 * (x - 1)) + b"\x00\x00\x00" + b"\xff" * (3 * (width - x))
    rows = white * (y - 1) + inked + white * (height - y)
    chunk = lambda n, d: struct.pack(">I", len(d)) + n + d + struct.pack(">I", zlib.crc32(n + d))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) +
                     chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def whole_png(html, half=False):
    """The PNG a good capture of this page writes: twice its size, ink out to twice its last shape (or, half,
    cut at half width as the app's zoomed capture did on 2026-10-12)."""
    root = diagram_check.svg_tree(html)
    _, _, w, h = diagram_check.viewbox(root)
    xmax, ymax = diagram_check.shapes_extent(root)
    reach = (min(int(2 * xmax), int(2 * w) - 1), min(int(2 * ymax), int(2 * h) - 1))
    if half:
        reach = (int(w), reach[1])
    fake_png(html.with_suffix(".png"), int(2 * w), int(2 * h), reach)


def fake_pdf(path):
    """A whole one-page PDF holding a word and a line, as any PDF reader (pymupdf included) opens it."""
    stream = b"BT /F1 12 Tf 20 60 Td (Diagram) Tj ET 20 20 m 180 20 l S"
    objs = [b"<</Type/Catalog/Pages 2 0 R>>", b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
            b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>",
            b"<</Length %d>>stream\n%s\nendstream" % (len(stream), stream),
            b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>"]
    out, offsets = bytearray(b"%PDF-1.4\n"), []
    for n, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (n, body)
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<</Size %d/Root 1 0 R>>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    path.write_bytes(bytes(out))


def built(folder, kind, change=None):
    data = json.loads((SKILL / "templates" / ("%s.diagram.json" % kind)).read_text())
    if change:
        change(data)
    src = folder / ("%s.diagram.json" % kind)
    src.write_text(json.dumps(data))
    html, svg, width, _, _ = diagram.build(src)
    whole_png(html)
    fake_pdf(html.with_suffix(".pdf"))
    return html


def packcheck(path):
    p = subprocess.run([sys.executable, str(CHECKS / "packcheck.py"), "diagram", str(path)], capture_output=True,
                       text=True, timeout=120)
    return p.returncode, p.stdout + p.stderr


def edit(html, old, new, count=1):
    text = html.read_text()
    assert old in text, old
    html.write_text(text.replace(old, new, count))
    for ext in (".pdf", ".png", ".svg"):
        f = html.with_suffix(ext)
        f.write_bytes(f.read_bytes())


class Starters(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="diagram-"))
        self.addCleanup(shutil.rmtree, self.dir, True)

    def test_every_starter_builds_and_passes(self):
        for kind in TYPES:
            with self.subTest(kind=kind):
                html = built(self.dir, kind)
                code, out = packcheck(html.with_suffix(".pdf"))
                self.assertEqual(code, 0, out)
                self.assertIn("pack check clean: 11 rules passed", out)

    def test_no_remote_reference_and_the_look_file(self):
        html = built(self.dir, "flowchart")
        text = html.read_text()
        self.assertNotIn("googleapis", text)
        self.assertIsNone(re.search(r"https?://(?!www\.w3\.org)", text))
        look = diagram.load_look()
        self.assertIn(look["ink"].lower(), text.lower())


class Defects(unittest.TestCase):
    """Each rule, given the defect it names, fails by name."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="diagram-defect-"))
        self.addCleanup(shutil.rmtree, self.dir, True)

    def fails(self, html, rule):
        code, out = packcheck(html.with_suffix(".pdf"))
        self.assertEqual(code, 1, out)
        self.assertRegex(out, r"FAIL %s\b" % rule)
        return out

    def test_contract_a_bare_title_id(self):
        html = built(self.dir, "flowchart")
        text = html.read_text().replace('id="flowchart-title"', 'id="title"').replace("flowchart-title ", "title ")
        html.write_text(text)
        self.fails(html, "DIAG-CONTRACT")

    def test_offline_a_web_font(self):
        html = built(self.dir, "flowchart")
        edit(html, "<style>", '<link href="https://fonts.googleapis.com/css2?family=Geist" rel="stylesheet"><style>')
        self.fails(html, "DIAG-OFFLINE")

    def test_geometry_a_diagonal_connector(self):
        html = built(self.dir, "flowchart")
        text = html.read_text()
        m = re.search(r'<path class="connector" d="M([\d.]+),([\d.]+)', text)
        edit(html, m.group(0), '<path class="connector" d="M%g,%g L%g,%g M%s,%s' % (
            float(m.group(1)) - 40, float(m.group(2)) - 30, float(m.group(1)), float(m.group(2)),
            m.group(1), m.group(2)))
        self.fails(html, "DIAG-GEOMETRY")

    def test_bounds_text_past_the_edge(self):
        html = built(self.dir, "layers")
        edit(html, 'class="layer-tag">L5', 'class="layer-tag">' + "The company policy, as the board wrote it " * 4)
        self.fails(html, "DIAG-BOUNDS")

    def test_fit_a_name_wider_than_its_box(self):
        html = built(self.dir, "org-chart")
        edit(html, ">Budget<", ">Budget, suppliers and all the costs<")
        self.fails(html, "DIAG-FIT")

    def test_overlap_two_boxes_on_one_another(self):
        html = built(self.dir, "flowchart")
        text = html.read_text()
        boxes = re.findall(r'<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)" rx="[\d.]+" '
                           r'fill="#[0-9A-F]{6}" stroke=', text)
        x, y, w, h = boxes[1]
        edit(html, "</svg>", '<rect x="%g" y="%g" width="%s" height="%s" rx="6" fill="#FFFFFF" stroke="#1A1C1F"/>'
                             '</svg>' % (float(x) + 20, float(y) + 20, w, h))
        self.fails(html, "DIAG-OVERLAP")

    def test_contrast_pale_text(self):
        html = built(self.dir, "quadrant")
        text = re.sub(r'fill="#[0-9A-F]{6}"([^>]*class="item-label">Office plants)', r'fill="#DDDDDD"\1',
                      html.read_text())
        html.write_text(text)
        edit(html, "</svg>", "</svg>")
        self.fails(html, "DIAG-CONTRAST")

    def test_budget_ten_steps(self):
        def ten(d):
            d["steps"] = [{"id": "s%d" % i, "name": "Step %d" % i} for i in range(10)]
            d["links"] = [{"from": "s%d" % i, "to": "s%d" % (i + 1)} for i in range(9)]
            d.pop("legend", None)
        html = built(self.dir, "flowchart", ten)
        self.fails(html, "DIAG-BUDGET")

    def test_label_too_long(self):
        html = built(self.dir, "swimlane")
        edit(html, ">CONTRACT<", ">CONTRACT AND ANNEXES<")
        self.fails(html, "DIAG-LABEL")

    def test_png_cut_at_half_width(self):
        html = built(self.dir, "swimlane")
        whole_png(html, half=True)
        out = self.fails(html, "DIAG-PNG")
        self.assertIn("the right part is missing", out)

    def test_png_not_twice_the_drawing(self):
        html = built(self.dir, "gantt")
        _, _, w, h = diagram_check.viewbox(diagram_check.svg_tree(html))
        fake_png(html.with_suffix(".png"), int(w), int(h), (int(w) - 40, int(h) - 40))
        self.fails(html, "DIAG-PNG")

    def test_png_ink_on_its_edge(self):
        html = built(self.dir, "layers")
        _, _, w, h = diagram_check.viewbox(diagram_check.svg_tree(html))
        fake_png(html.with_suffix(".png"), int(2 * w), int(2 * h), (int(2 * w), int(h)))
        out = self.fails(html, "DIAG-PNG")
        self.assertIn("right edge", out)

    def test_export_missing_png(self):
        html = built(self.dir, "gantt")
        html.with_suffix(".png").unlink()
        self.fails(html, "DIAG-EXPORT")


class Groups(unittest.TestCase):
    """A flowchart in groups: a zone flow over two floors and the stair between, side by side on one slide."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="diagram-groups-"))
        self.addCleanup(shutil.rmtree, self.dir, True)

    def floors(self, d):
        d.clear()
        d.update({"type": "flowchart", "title": "Guest route over two floors", "language": "en",
                  "description": "Zones on the ground floor, the stair and the first floor, in the order a guest "
                                 "passes them.",
                  "steps": [{"id": "a", "name": "Entrance", "group": "Ground floor", "shape": "start"},
                            {"id": "b", "name": "Reception", "group": "Ground floor"},
                            {"id": "c", "name": "Lounge", "group": "Ground floor"},
                            {"id": "d", "name": "Restaurant", "group": "Ground floor"},
                            {"id": "e", "name": "Stair", "group": "Stair", "focal": True},
                            {"id": "f", "name": "Foyer", "group": "First floor"},
                            {"id": "g", "name": "Meeting rooms", "group": "First floor"},
                            {"id": "h", "name": "Great hall", "group": "First floor", "shape": "end"}],
                  "links": [{"from": "a", "to": "b"}, {"from": "b", "to": "c"}, {"from": "c", "to": "d"},
                            {"from": "d", "to": "e"}, {"from": "e", "to": "f"}, {"from": "f", "to": "g"},
                            {"from": "g", "to": "h"}]})

    def test_floors_side_by_side_on_a_slide(self):
        html = built(self.dir, "flowchart", self.floors)
        code, out = packcheck(html.with_suffix(".pdf"))
        self.assertEqual(code, 0, out)
        _, _, w, h = diagram_check.viewbox(diagram_check.svg_tree(html))
        self.assertEqual(w, 1280)
        self.assertLess(h, 720, "eight zones over three groups fit a 16:9 slide")
        self.assertEqual(html.read_text().count('class="group-rule"'), 3)

    def test_zones_with_no_route_stand_down_their_floor(self):
        def bare(d):
            self.floors(d)
            d["links"] = [{"from": "d", "to": "e"}, {"from": "e", "to": "f"}]
        html = built(self.dir, "flowchart", bare)
        code, out = packcheck(html.with_suffix(".pdf"))
        self.assertEqual(code, 0, out)
        _, _, w, h = diagram_check.viewbox(diagram_check.svg_tree(html))
        self.assertEqual(w, 1280, "three columns, not a row of eight")
        self.assertLess(h, 720)

    def test_a_link_that_skips_a_group(self):
        def skip(d):
            self.floors(d)
            d["links"].append({"from": "a", "to": "h"})
        with self.assertRaises(diagram.DiagramError) as caught:
            built(self.dir, "flowchart", skip)
        self.assertIn("next group", str(caught.exception))

    def test_a_step_with_no_group(self):
        def bare(d):
            self.floors(d)
            d["steps"][2].pop("group")
        with self.assertRaises(diagram.DiagramError) as caught:
            built(self.dir, "flowchart", bare)
        self.assertIn("has no group", str(caught.exception))


class Builder(unittest.TestCase):
    """The builder says what to change when the data cannot be drawn, never draws it wrong."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="diagram-data-"))
        self.addCleanup(shutil.rmtree, self.dir, True)

    def refuses(self, kind, change, words):
        with self.assertRaises(diagram.DiagramError) as caught:
            built(self.dir, kind, change)
        self.assertIn(words, str(caught.exception))

    def test_a_long_arrow_label(self):
        self.refuses("flowchart", lambda d: d["links"][0].update(label="once everything is signed"),
                     "longer than 14")

    def test_an_unknown_type(self):
        self.refuses("flowchart", lambda d: d.update(type="axonometric-plan"), "it is one of")

    def test_a_step_in_no_lane(self):
        self.refuses("swimlane", lambda d: d["steps"][0].update(lane="Legal"), "not one of the lanes")

    def test_an_item_on_an_axis(self):
        self.refuses("quadrant", lambda d: d["items"][0].update(x=0.5), "never 0.5")

    def test_two_tops_in_an_org_chart(self):
        self.refuses("org-chart", lambda d: d["people"][1].pop("reports_to"), "one top")


if __name__ == "__main__":
    unittest.main()
