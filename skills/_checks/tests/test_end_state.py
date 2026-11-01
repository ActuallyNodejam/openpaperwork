"""The library's checks judge the file on disk, never the chat's word that it was written.

Four cases for every document kind (Word, Excel, PowerPoint, PDF, SVG, PNG), run against every pack that hands that
kind back (found from the packs' own pack.json files, so a new pack is covered the day it lands):

  a  the agent says done and writes nothing           the file is not there        -> FAIL OUTPUT-MISSING
  b  it writes an empty or a placeholder file         0 bytes, no text, filler     -> FAIL OUTPUT-EMPTY / -PLACEHOLDER / -UNOPENABLE
  c  it leaves the input untouched but claims an edit the file is older than the   -> FAIL OUTPUT-STALE
                                                      request (NODEJAM_TURN_STARTED)
  d  a real good file                                 passes the gate; where the pack's dependencies are
                                                      present, passes the pack's own check too

Standard library only for a, b, c and the gate half of d, so it runs on any Python:
    python3 -m unittest skills/_checks/tests/test_end_state.py
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import struct
import zipfile
import zlib
from pathlib import Path

CHECKS = Path(__file__).resolve().parent.parent
SKILLS = CHECKS.parent
sys.path.insert(0, str(CHECKS))
import end_state  # noqa: E402

PACKCHECK = CHECKS / "packcheck.py"
REAL_TEXT = ("Quarterly report for the property group. Revenue rose four percent on the quarter, driven by the "
             "north and south sites, and the board asked for a plan to keep costs flat through the winter.")


def packs():
    """(pack name, kinds it hands back) for every pack whose check is packcheck.py."""
    found = []
    for f in sorted(SKILLS.rglob("pack.json")):
        spec = json.loads(f.read_text())
        if "packcheck.py" in (spec.get("check") or "") and spec.get("hands_back"):
            found.append((str(f.parent.relative_to(SKILLS)), [k.lstrip("*") for k in spec["hands_back"]]))
    return found


# ---- the four kinds, built by hand so no library is needed ------------------------------------------------------

def put(path, parts):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, body in parts.items():
            z.writestr(name, body)
    return path


NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_S = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"


def docx(path, text):
    body = "<w:p><w:r><w:t>%s</w:t></w:r></w:p>" % text if text else "<w:p/>"
    return put(path, {"[Content_Types].xml": "<Types/>",
                      "word/document.xml": '<w:document xmlns:w="%s"><w:body>%s</w:body></w:document>' % (NS_W, body)})


def xlsx(path, strings=(), numbers=()):
    cells = "".join('<c t="s"><v>%d</v></c>' % i for i in range(len(strings))) + \
            "".join("<c><v>%s</v></c>" % n for n in numbers)
    shared = "".join("<si><t>%s</t></si>" % s for s in strings)
    return put(path, {"[Content_Types].xml": "<Types/>",
                      "xl/workbook.xml": '<workbook xmlns="%s"/>' % NS_S,
                      "xl/sharedStrings.xml": '<sst xmlns="%s">%s</sst>' % (NS_S, shared),
                      "xl/worksheets/sheet1.xml": '<worksheet xmlns="%s"><sheetData><row>%s</row></sheetData></worksheet>'
                                                  % (NS_S, cells)})


def pptx(path, texts):
    runs = "".join("<a:p><a:r><a:t>%s</a:t></a:r></a:p>" % t for t in texts)
    return put(path, {"[Content_Types].xml": "<Types/>",
                      "ppt/presentation.xml": '<p:presentation xmlns:p="%s"/>' % NS_P,
                      "ppt/slides/slide1.xml": '<p:sld xmlns:p="%s" xmlns:a="%s"><p:txBody>%s</p:txBody></p:sld>'
                                               % (NS_P, NS_A, runs)})


def pdf(path, text=None, pages=1):
    """A whole PDF of `pages` pages with correct offsets; with text, a line of it on each."""
    stream = ("BT /F1 12 Tf 72 720 Td (%s) Tj ET" % text).encode() if text else b""
    kids = " ".join("%d 0 R" % (5 + i * 2) for i in range(pages))
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            ("<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, pages)).encode(),
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>", b""]
    for i in range(pages):
        n = 5 + i * 2
        objs.append(("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents %d 0 R "
                     "/Resources << /Font << /F1 3 0 R >> >> >>" % (n + 1)).encode())
        objs.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
    objs[3] = b"<< >>"
    out, offsets = b"%PDF-1.4\n", []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    path.write_bytes(out)
    return path


def svg(path, body):
    path.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100"><title>t</title>'
                    '<rect width="100%%" height="100%%" fill="#fff"/>%s</svg>' % body, encoding="utf-8")
    return path


def png(path, flat=False):
    """An 8 x 8 RGB picture: two colours, or one flat colour (a blank capture)."""
    rows = b"".join(b"\x00" + b"".join(bytes((255, 255, 255)) if flat or (x + y) % 3 else bytes((26, 28, 31))
                                         for x in range(8)) for y in range(8))
    chunk = lambda name, data: struct.pack(">I", len(data)) + name + data + struct.pack(">I", zlib.crc32(name + data))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 8, 8, 8, 2, 0, 0, 0)) +
                     chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))
    return path


def good(kind, path):
    return {".svg": lambda: svg(path, '<rect x="10" y="10" width="80" height="40" stroke="#000"/>'
                                      '<text x="20" y="35">Order placed</text>'),
            ".png": lambda: png(path),
            ".docx": lambda: docx(path, REAL_TEXT),
            ".xlsx": lambda: xlsx(path, ["Site", "Revenue"], [120, 4]),
            ".pptx": lambda: pptx(path, ["Quarterly report", REAL_TEXT]),
            ".pdf": lambda: pdf(path, REAL_TEXT)}[kind]()


def hollow_files(kind, folder):
    """Case b for one kind: (label, path) of files that exist and hold nothing real."""
    zero = folder / ("zero" + kind)
    zero.write_bytes(b"")
    cases = [("zero bytes", zero)]
    junk = folder / ("junk" + kind)
    junk.write_bytes(b"this is not that kind of file, whatever its name says")
    cases.append(("not a real file", junk))
    if kind == ".docx":
        cases += [("no text", docx(folder / "blank.docx", "")),
                  ("lorem ipsum", docx(folder / "lorem.docx", "Lorem ipsum dolor sit amet, consectetur adipiscing elit."
                                                              " Sed do eiusmod tempor incididunt ut labore."))]
    if kind == ".xlsx":
        cases += [("no cell", xlsx(folder / "blank.xlsx")),
                  ("placeholder cells", xlsx(folder / "filler.xlsx", ["Your text here", "TBD"]))]
    if kind == ".pptx":
        cases += [("no text", pptx(folder / "blank.pptx", [])),
                  ("click to add", pptx(folder / "filler.pptx", ["Click to add title", "Click to add text"]))]
    if kind == ".pdf":
        cases += [("placeholder page", pdf(folder / "filler.pdf", "Lorem ipsum dolor sit amet"))]
    if kind == ".svg":
        cases += [("draws nothing", svg(folder / "blank.svg", "")),
                  ("template filler", svg(folder / "filler.svg", "<text>[Diagram title]</text>"))]
    if kind == ".png":
        cases += [("one flat colour", png(folder / "flat.png", flat=True))]
    return cases


def run(skill, path, env=None, *args):
    e = dict(os.environ)
    e.pop("NODEJAM_TURN_STARTED", None)
    e.update(env or {})
    p = subprocess.run([sys.executable, str(PACKCHECK), skill, str(path), *args], capture_output=True, text=True, env=e,
                       cwd=str(path.parent), timeout=300)
    return p.returncode, p.stdout + p.stderr


class Gate(unittest.TestCase):
    """The shared gate, on every kind, with no pack in the way."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="end-state-"))

    def rules(self, path, since=None):
        return [rule for rule, _ in end_state.judge(path, since)]

    def test_a_file_never_written_is_missing(self):
        self.assertEqual(self.rules(self.dir / "report.docx"), ["OUTPUT-MISSING"])

    def test_b_a_file_that_holds_nothing_fails_in_every_kind(self):
        for kind in (".docx", ".xlsx", ".pptx", ".pdf", ".svg", ".png"):
            folder = self.dir / kind[1:]
            folder.mkdir()
            for label, path in hollow_files(kind, folder):
                with self.subTest(kind=kind, case=label):
                    if label == "placeholder page" and not self.has_pdf_reader():
                        self.skipTest("a PDF's text needs PyMuPDF")
                    self.assertTrue(set(self.rules(path)) & {"OUTPUT-EMPTY", "OUTPUT-PLACEHOLDER", "OUTPUT-UNOPENABLE"},
                                    "%s %s passed the gate" % (kind, label))

    def test_c_a_file_older_than_the_request_is_not_this_turns_work(self):
        for kind in (".docx", ".xlsx", ".pptx", ".pdf", ".svg", ".png"):
            path = good(kind, self.dir / ("input" + kind))
            old = time.time() - 3600
            os.utime(path, (old, old))
            with self.subTest(kind=kind):
                self.assertEqual(self.rules(path, since=str(int(time.time() * 1000))), ["OUTPUT-STALE"])
                self.assertEqual(self.rules(path), [], "with no request time the age is not judged")
                os.environ["NODEJAM_TURN_STARTED"] = str(int(time.time() * 1000))
                try:
                    self.assertEqual(self.rules(path), ["OUTPUT-STALE"])
                finally:
                    del os.environ["NODEJAM_TURN_STARTED"]

    def test_d_a_good_file_stands_in_every_kind(self):
        for kind in (".docx", ".xlsx", ".pptx", ".pdf", ".svg", ".png"):
            path = good(kind, self.dir / ("good" + kind))
            with self.subTest(kind=kind):
                self.assertEqual(end_state.judge(path, str(int((time.time() - 60) * 1000))), [])

    def test_a_file_edited_after_the_request_is_fresh(self):
        path = good(".docx", self.dir / "mine.docx")
        self.assertEqual(self.rules(path, since=str(int((time.time() - 5) * 1000))), [])

    @staticmethod
    def has_pdf_reader():
        try:
            import pymupdf  # noqa: F401
            return True
        except ImportError:
            try:
                import fitz  # noqa: F401
                return True
            except ImportError:
                return False


class OpenGaps(unittest.TestCase):
    """A file well made and not finished: the gaps left for the person (a real run, 2026-10-13)."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="open-gap-"))

    def test_each_marker_the_agents_write_is_a_gap(self):
        for marker in ("[TO CONFIRM: who signs for the company]", "[TBD]", "[tbc: the start date]", "[?]",
                       "[Zu best\u00e4tigen: K\u00fcndigungsfrist]", "[\u00c0 confirmer : le salaire]",
                       "[att bekr\u00e4fta]", "[Missing: notice period]", "[to be confirmed]",
                       "[minute-taker to be confirmed]", "[signatory TBC]", "[date]", "[Datum]", "[Name]"):
            with self.subTest(marker=marker):
                path = docx(self.dir / "statement.docx", REAL_TEXT + " Notice: " + marker)
                self.assertEqual(end_state.open_gaps(path), [marker])
                self.assertEqual(end_state.judge(path), [], "the gate still stands; the pack check fails it")

    def test_brackets_that_are_content_are_not_gaps(self):
        for text in ("The price holds 85 % at full load (TBR-1).", "Refer to [1] and [Smith 2020].",
                     "The account [Offene Posten] is reconciled.", "Clause [4.2] applies.", "[Confirmed by the board]",
                     "Signed [name withheld at the request of the author]."):
            with self.subTest(text=text):
                self.assertEqual(end_state.open_gaps(docx(self.dir / "page.docx", REAL_TEXT + " " + text)), [])

    def test_the_pack_check_fails_a_page_with_gaps_and_names_the_first(self):
        path = docx(self.dir / "letter.docx", REAL_TEXT + " Signed for the company by [TO CONFIRM: name].")
        code, out = run("every-file", path)
        self.assertEqual(code, 1, out)
        self.assertIn("OUTPUT-OPEN-GAP", out)
        self.assertIn("[TO CONFIRM: name]", out)

    def test_a_sheet_and_a_page_are_read_too(self):
        self.assertEqual(end_state.open_gaps(xlsx(self.dir / "s.xlsx", ["Rate", "[TBD]"], [3])), ["[TBD]"])
        page = self.dir / "page.html"
        page.write_text("<html><body><p>%s [TODO: the total]</p></body></html>" % REAL_TEXT, encoding="utf-8")
        self.assertEqual(end_state.open_gaps(page), ["[TODO: the total]"])


class EveryPack(unittest.TestCase):
    """The same cases through packcheck.py itself, for each pack and each kind it hands back."""

    def test_every_pack_fails_the_three_ways_of_not_doing_the_job(self):
        seen = 0
        for skill, kinds in packs():
            for kind in kinds:
                folder = Path(tempfile.mkdtemp(prefix="end-state-pack-"))
                with self.subTest(pack=skill, kind=kind, case="a nothing written"):
                    code, out = run(skill, folder / ("report" + kind))
                    self.assertEqual(code, 1, out)
                    self.assertIn("FAIL OUTPUT-MISSING", out)
                for label, path in hollow_files(kind, folder):
                    if label == "placeholder page" and not Gate.has_pdf_reader():
                        continue
                    with self.subTest(pack=skill, kind=kind, case="b " + label):
                        code, out = run(skill, path)
                        self.assertEqual(code, 1, out)
                        self.assertRegex(out, r"FAIL OUTPUT-(EMPTY|PLACEHOLDER|UNOPENABLE)")
                stale = good(kind, folder / ("brought" + kind))
                old = time.time() - 3600
                os.utime(stale, (old, old))
                with self.subTest(pack=skill, kind=kind, case="c input untouched"):
                    code, out = run(skill, stale, {"NODEJAM_TURN_STARTED": str(int(time.time() * 1000))})
                    self.assertEqual(code, 1, out)
                    self.assertIn("FAIL OUTPUT-STALE", out)
                with self.subTest(pack=skill, kind=kind, case="c --since"):
                    code, out = run(skill, stale, None, "--since", str(int(time.time() * 1000)))
                    self.assertEqual((code, "FAIL OUTPUT-STALE" in out), (1, True), out)
                seen += 1
        self.assertGreater(seen, 20, "the packs were not found")


class GoodFiles(unittest.TestCase):
    """Case d through the pack's own rules: a real file made with the real libraries is clean."""

    def setUp(self):
        # The libraries live in the pack's own Python (runtime/python); a bare one, like CI's library job, runs
        # every case above and skips these.
        try:
            import docx, openpyxl, pptx  # noqa: F401
        except ImportError as exc:
            self.skipTest("a real file needs %s" % exc.name)
        self.dir = Path(tempfile.mkdtemp(prefix="end-state-good-"))

    def clean(self, skill, path):
        code, out = run(skill, path, {"NODEJAM_TURN_STARTED": str(int((time.time() - 120) * 1000))})
        self.assertEqual(code, 0, out)
        self.assertNotIn("FAIL", out)

    def test_word(self):
        import docx as word
        # A good Word file starts from the skills template: the blank defaults Cambria fails DOCX-FONT.
        d = word.Document(str(Path(__file__).resolve().parents[2] / "docx" / "templates" / "standard.docx"))
        d.core_properties.title = "Quarterly report"
        d.core_properties.language = "en-GB"
        d.add_heading("Quarterly report", 1)
        d.add_paragraph(REAL_TEXT)
        path = self.dir / "report.docx"
        d.save(path)
        for skill in ("docx", "every-file"):
            self.clean(skill, path)

    def test_excel(self):
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Revenue"
        ws.append(["Site", "Q1", "Q2"])
        ws.append(["North", 120, 126])
        ws.append(["South", 80, 83])
        wb.properties.title = "Revenue by site"
        path = self.dir / "schedule.xlsx"
        wb.save(path)
        for skill in ("xlsx", "every-file"):
            self.clean(skill, path)

    def test_powerpoint(self):
        import pptx as slides
        p = slides.Presentation()
        s = p.slides.add_slide(p.slide_layouts[1])
        s.shapes.title.text = "Quarterly report"
        s.placeholders[1].text = "Revenue rose four percent on the quarter."
        p.core_properties.title = "Quarterly report"
        path = self.dir / "deck.pptx"
        p.save(path)
        self.clean("every-file", path)


class CompressedPages(unittest.TestCase):
    """Without a PDF reader the gate still finds a page kept in a compressed object stream (agent run 8)."""

    def test_object_stream_page(self):
        import end_state
        def made(inner):
            packed = zlib.compress(inner)
            return (b"%PDF-1.5\n4 0 obj\n<< /Type /ObjStm /N 2 /First 8 /Filter /FlateDecode /Length "
                    + str(len(packed)).encode() + b" >>\nstream\n" + packed + b"\nendstream\nendobj\n"
                    + b"startxref\n0\n%%EOF\n")
        data = made(b"1 0 2 40 << /Type /Catalog /Pages 2 0 R >> << /Type /Page /Parent 2 0 R >>")
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "paper.pdf"
            path.write_bytes(data)
            hidden = {name: sys.modules.get(name) for name in ("pymupdf", "fitz")}
            try:
                sys.modules["pymupdf"] = None
                sys.modules["fitz"] = None
                self.assertEqual(end_state.pdf(path), [])
                path.write_bytes(made(b"1 0 2 40 << /Type /Catalog /Pages 2 0 R >> << /Type /Pages /Kids [] >>"))
                self.assertTrue(end_state.pdf(path))
            finally:
                for name, mod in hidden.items():
                    if mod is None:
                        sys.modules.pop(name, None)
                    else:
                        sys.modules[name] = mod


if __name__ == "__main__":
    unittest.main()
