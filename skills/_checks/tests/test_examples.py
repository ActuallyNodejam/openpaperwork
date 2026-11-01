"""The examples fingerprint and check (skills/_checks/examples.py) on small synthetic files built here.

No client file is read: a sheet with a title, section rows, a header, money formats and a total formula, a few
decks made with python-pptx, and a tiny landscape PDF when Pillow, numpy and poppler are there.
"""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("nodejam_examples", HERE.parent / "examples.py")
EX = importlib.util.module_from_spec(spec)
sys.modules["nodejam_examples"] = EX
spec.loader.exec_module(EX)

try:
    import openpyxl
except ImportError:  # pragma: no cover
    openpyxl = None
try:
    import pptx
except ImportError:  # pragma: no cover
    pptx = None


def make_sheet(path, headers=("Image", "Name", "Qty", "Supplier", "Size", "Price ex VAT"), title="Inventory Alpha",
               zones=("Hall", "Bar"), total=True, title_row=True, sum_formulas=True):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Blad 1"
    row = 1
    if title_row:
        ws.cell(row, 1, title)
        row += 1
    for zone in zones:
        ws.cell(row, 1, "Zone: " + zone).font = openpyxl.styles.Font(bold=True)
        row += 1
        for i, h in enumerate(headers, 1):
            ws.cell(row, i, h).font = openpyxl.styles.Font(bold=True)
        row += 1
        first = row
        for n in range(2):
            for i, h in enumerate(headers, 1):
                if h in ("Name", "Namn"):
                    ws.cell(row, i, "Chair %d" % n)
                elif h in ("Qty", "Quantity", "Antal"):
                    ws.cell(row, i, n + 1)
                elif h.startswith("Price"):
                    ws.cell(row, i, 1200 * (n + 1)).number_format = '#,##0 "kr"'
                elif h == "Supplier":
                    ws.cell(row, i, "Maker")
                elif h == "Size":
                    ws.cell(row, i, "60x60")
            row += 1
        row += 1
    if total:
        ws.cell(row, 1, "Total")
        col = headers.index("Price ex VAT") + 1 if "Price ex VAT" in headers else 6
        ws.cell(row, col, ("=SUM(F4:F5)" if sum_formulas else 3600)).number_format = '#,##0 "kr"'
    for letter, width in zip("ABCDEF", (14, 24, 8, 18, 12, 16)):
        ws.column_dimensions[letter].width = width
    ws.freeze_panes = "A4"
    wb.save(path)


@unittest.skipIf(openpyxl is None, "openpyxl is not installed")
class SheetFingerprint(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.path = self.dir / "Inventory Alpha 2025.xlsx"
        make_sheet(self.path)
        self.fp = EX.fingerprint(self.path)
        self.sheet = self.fp["sheets"][0]

    def test_structure(self):
        s = self.sheet
        self.assertEqual(self.fp["kind"], "sheet")
        self.assertTrue(s["default_name"])
        self.assertEqual(s["header_row"], 3)
        self.assertEqual(s["title"]["pattern"], "Inventory {name}")
        self.assertEqual(s["sections"]["label"], "Zone")
        self.assertEqual(s["sections"]["count"], 2)
        self.assertTrue(s["sections"]["repeats_header"])
        self.assertEqual(s["frozen"], "A4")
        self.assertEqual(s["totals"][0]["label"], "Total")
        self.assertEqual(s["totals"][0]["function"], "SUM")
        self.assertTrue(s["amounts_are_formulas"])

    def test_columns_meaning_format_and_width(self):
        cols = self.sheet["columns"]
        self.assertEqual([c["header"] for c in cols], ["Image", "Name", "Qty", "Supplier", "Size", "Price ex VAT"])
        self.assertEqual([c["meaning"] for c in cols], ["picture", "name", "count", "supplier", "size", "price"])
        price = cols[-1]
        self.assertEqual(price["format_class"], "money")
        self.assertEqual(cols[2]["data"], "integer")
        self.assertEqual(cols[1]["width"], 24.0)
        self.assertEqual(cols[-1]["letter"], "F")

    def test_meaning_from_the_data_when_the_header_says_nothing(self):
        path = self.dir / "x.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Alpha", "Beta", "Gamma"])
        for n in range(3):
            ws.append(["row %d" % n, 1500.0 * (n + 1), 2 + n])
            ws.cell(ws.max_row, 2).number_format = '#,##0.00 "SEK"'
        wb.save(path)
        cols = EX.fingerprint(path)["sheets"][0]["columns"]
        self.assertEqual([c["meaning"] for c in cols], ["text", "price", "count"])

    def test_header_words_in_several_languages(self):
        for header, meaning in (("Leverantör", "supplier"), ("Lieferant", "supplier"), ("Ledtid", "lead time"), ("Mått", "size"),
                                ("Preis", "price"), ("Antall", "count"), ("Benämning", "name"), ("Bild", "picture"),
                                ("Art.nr", "code"), ("Summa", "sum"), ("Kommentar", "note"), ("Yta", "room")):
            self.assertEqual(EX.header_meaning(header), meaning, header)

    def test_csv(self):
        path = self.dir / "list.csv"
        path.write_text("Namn;Antal;Pris\nStol;2;1200\nBord;1;3000\n")
        sheet = EX.fingerprint(path)["sheets"][0]
        self.assertEqual([c["meaning"] for c in sheet["columns"]], ["name", "count", "price"])

    def test_a_word_file_has_no_fingerprint(self):
        self.assertEqual(EX.fingerprint(self.dir / "letter.docx")["kind"], "document")


@unittest.skipIf(openpyxl is None, "openpyxl is not installed")
class SheetCompare(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, True)
        make_sheet(self.dir / "ex.xlsx")
        self.expected = EX.fingerprint(self.dir / "ex.xlsx")

    def run_compare(self, **kw):
        make_sheet(self.dir / "new.xlsx", **kw)
        return EX.compare(self.expected, EX.fingerprint(self.dir / "new.xlsx"))

    def verdicts(self, findings):
        return {f["field"]: f["verdict"] for f in findings}

    def test_the_same_file_is_all_same(self):
        found = EX.compare(self.expected, EX.fingerprint(self.dir / "ex.xlsx"))
        self.assertTrue(found)
        self.assertEqual({f["verdict"] for f in found}, {"same"})

    def test_a_missing_column_fails_and_is_named(self):
        found = self.run_compare(headers=("Image", "Name", "Qty", "Size", "Price ex VAT"))
        v = self.verdicts(found)
        self.assertEqual(v["column 'Supplier'"], "missing")
        note = next(f["note"] for f in found if f["field"] == "column 'Supplier'")
        self.assertIn("Supplier", note)
        self.assertIn("Image, Name, Qty", note)

    def test_a_reordered_column_is_named(self):
        found = self.run_compare(headers=("Image", "Qty", "Name", "Supplier", "Size", "Price ex VAT"))
        order = next(f for f in found if f["field"].startswith("column order"))
        self.assertEqual(order["verdict"], "different")
        self.assertIn("'Name'", order["note"])

    def test_a_synonym_is_close(self):
        found = self.run_compare(headers=("Image", "Name", "Quantity", "Supplier", "Size", "Price ex VAT"))
        v = self.verdicts(found)
        self.assertEqual(v["column 'Qty'"], "close")
        self.assertNotIn("missing", v.values())

    def test_a_missing_title_total_and_formula_are_named(self):
        found = self.run_compare(title_row=False, total=False)
        v = self.verdicts(found)
        self.assertEqual(v["title"], "missing")
        self.assertEqual(v["total row"], "missing")
        found = self.run_compare(sum_formulas=False)
        self.assertEqual(self.verdicts(found)["formulas"], "different")

    def test_a_wrong_title_word_differs(self):
        found = self.run_compare(title="Budget Alpha")
        self.assertEqual(self.verdicts(found)["title"], "different")


class NamePattern(unittest.TestCase):
    def test_one_example_keeps_the_kind_and_company_words(self):
        p = EX.name_pattern("Prislista Exempel Tryck Växjö _ Houwzit.xlsx", ["Example Print"])
        self.assertEqual(p["pattern"], "Artikellista Example Print {name}")
        self.assertTrue(EX.name_matches(p, "Artikellista Example Print Östersund.xlsx"))
        self.assertFalse(EX.name_matches(p, "Budget Example Print Östersund.xlsx"))

    def test_dates_numbers_and_versions_are_variable(self):
        p = EX.name_pattern("Offert 2025-03-14 v2.docx")
        self.assertEqual(p["pattern"], "Offert {date} {version}")

    def test_several_examples_fix_what_they_share(self):
        p = EX.name_pattern(["Rapport Alfa maj.xlsx", "Rapport Beta juni.xlsx"])
        self.assertEqual(p["pattern"], "Rapport {name}")

    def test_a_lower_case_file_name_stays_fixed(self):
        p = EX.name_pattern("acme-hotels-concept-2025.pdf")
        self.assertEqual(p["pattern"], "acme hotels concept {year}")


def png(path, colour, size=(40, 30)):
    from PIL import Image
    Image.new("RGB", size, colour).save(path)


def make_deck(path, ink="202020", ground="F4F0E8", font="Garamond", pictures=True):
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.util import Inches, Pt
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]
    img = path.parent / "pic.png"
    png(img, (120, 90, 60))

    def text(slide, words, top=1.0):
        box = slide.shapes.add_textbox(Inches(1), Inches(top), Inches(8), Inches(2))
        run = box.text_frame.paragraphs[0].add_run()
        run.text = words
        run.font.name = font
        run.font.size = Pt(24)
        run.font.color.rgb = RGBColor.from_string(ink.upper())

    for n in range(6):
        slide = prs.slides.add_slide(blank)
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = RGBColor.from_string(ground.upper())
        if n in (0, 3):
            text(slide, "Section %d" % n)
        elif n in (1, 4) and pictures:
            text(slide, " ".join(["word"] * 40))
            slide.shapes.add_picture(str(img), Inches(8), Inches(1), Inches(4), Inches(3))
        else:
            text(slide, " ".join(["word"] * 200))
    prs.save(path)


@unittest.skipIf(pptx is None, "python-pptx is not installed")
class DeckFingerprint(unittest.TestCase):
    def setUp(self):
        try:
            import PIL  # noqa: F401
        except ImportError:
            self.skipTest("Pillow is not installed")
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, True)

    def deck(self, name, **kw):
        make_deck(self.dir / name, **kw)
        return EX.fingerprint(self.dir / name)

    def test_fields(self):
        fp = self.deck("Concept Alpha.pptx")
        self.assertEqual(fp["kind"], "deck")
        self.assertEqual(fp["pages"], 6)
        self.assertEqual(fp["size"]["aspect"], 1.778)
        self.assertEqual(fp["opening"][0], "divider")
        self.assertEqual(fp["shares"]["divider"], 33.3)
        self.assertEqual(fp["shares"]["text page"], 33.3)
        self.assertEqual(fp["closing"], "text page")
        self.assertEqual(fp["fonts"][0]["font"], "Garamond")
        self.assertEqual(fp["fonts"][0]["ship"], "EB Garamond")
        self.assertEqual(fp["ink"]["hex"], "#202020")
        self.assertEqual(fp["grounds"][0]["hex"], "#f4f0e8")
        self.assertEqual(fp["words_median"], 40)
        self.assertEqual(fp["picture_share"], 33.3)

    def test_compare_ink_and_font(self):
        base = self.deck("a.pptx")
        near = self.deck("b.pptx", ink="262626")
        far = self.deck("c.pptx", ink="CC0000", font="Arial")
        self.assertEqual(EX.compare(base, near) and {f["field"]: f["verdict"] for f in EX.compare(base, near)}["ink"], "same")
        slight = {f["field"]: f["verdict"] for f in EX.compare(base, self.deck("d.pptx", ink="404040"))}
        self.assertEqual(slight["ink"], "close")
        v = {f["field"]: f for f in EX.compare(base, far)}
        self.assertEqual(v["ink"]["verdict"], "different")
        self.assertEqual(v["font Garamond"]["verdict"], "different")
        self.assertIn("#202020", v["ink"]["note"])

    def test_compare_rhythm(self):
        base = self.deck("a.pptx")
        flat = self.deck("e.pptx", pictures=False)
        v = {f["field"]: f["verdict"] for f in EX.compare(base, flat)}
        self.assertEqual(v["pictures per page"], "different")

    def test_a_portrait_text_pdf_is_not_a_deck(self):
        if not shutil.which("pdfinfo"):
            self.skipTest("poppler is not installed")
        from PIL import Image
        pages = [Image.new("RGB", (800, 1100), "white") for _ in range(4)]
        pdf = self.dir / "doc.pdf"
        pages[0].save(pdf, save_all=True, append_images=pages[1:], resolution=100)
        self.assertEqual(EX.fingerprint(pdf)["kind"], "document")

    def test_a_landscape_pdf_is_read_as_a_deck(self):
        try:
            import numpy  # noqa: F401
        except ImportError:
            self.skipTest("numpy is not installed")
        if not (shutil.which("pdfinfo") and shutil.which("pdftoppm") and shutil.which("pdftotext")):
            self.skipTest("poppler is not installed")
        from PIL import Image
        pages = [Image.new("RGB", (1920, 1080), c) for c in ("white", "white", "#242d26", "white")]
        pdf = self.dir / "slides.pdf"
        pages[0].save(pdf, save_all=True, append_images=pages[1:], resolution=144)
        fp = EX.fingerprint(pdf)
        self.assertEqual(fp["kind"], "deck")
        self.assertEqual(fp["source"], "pdf")
        self.assertEqual(fp["pages"], 4)
        self.assertLess(EX.delta_e(fp["grounds"][0]["hex"], "#ffffff"), 3)
        self.assertLess(EX.delta_e(fp["grounds"][1]["hex"], "#242d26"), 3)


@unittest.skipIf(openpyxl is None, "openpyxl is not installed")
class Cli(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, True)
        make_sheet(self.dir / "Inventory Alpha 2025.xlsx")
        self.ex = self.dir / "fp.json"
        self.ex.write_text(json.dumps(EX.fingerprint(self.dir / "Inventory Alpha 2025.xlsx")))

    def run_check(self, name, **kw):
        make_sheet(self.dir / name, **kw)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = EX.main(["check", str(self.dir / name), "--examples", str(self.ex)])
        return code, out.getvalue().splitlines()

    def test_clean_file_exits_0(self):
        code, lines = self.run_check("new.xlsx")
        self.assertEqual(code, 0)
        self.assertRegex(lines[-1], r"^examples check: \d+ fields same, 0 close, 0 off$")

    def test_a_missing_column_exits_1_with_a_fail_line(self):
        code, lines = self.run_check("new.xlsx", headers=("Image", "Name", "Qty", "Size", "Price ex VAT"))
        self.assertEqual(code, 1)
        self.assertTrue(any(l.startswith("FAIL column 'Supplier': ") for l in lines), lines)

    def test_a_synonym_alone_warns_and_exits_0(self):
        code, lines = self.run_check("new.xlsx", headers=("Image", "Name", "Quantity", "Supplier", "Size", "Price ex VAT"))
        self.assertEqual(code, 0)
        self.assertTrue(any(l.startswith("WARN column 'Qty': ") for l in lines), lines)
        self.assertIn("1 close", lines[-1])

    def test_the_command_line_runs_as_a_script(self):
        make_sheet(self.dir / "new.xlsx", headers=("Image", "Name", "Qty", "Size", "Price ex VAT"))
        done = subprocess.run([sys.executable, str(HERE.parent / "examples.py"), "check", str(self.dir / "new.xlsx"),
                               "--examples", str(self.ex), "--if-claimed", "--in", str(self.dir)], capture_output=True, text=True)
        self.assertEqual(done.returncode, 1)
        self.assertIn("FAIL column 'Supplier'", done.stdout)
        done = subprocess.run([sys.executable, str(HERE.parent / "examples.py"), "fingerprint", str(self.dir / "new.xlsx")],
                              capture_output=True, text=True)
        self.assertEqual(json.loads(done.stdout)["kind"], "sheet")

    def test_installed_examples_are_found_above_the_file_and_matched_by_name(self):
        folder = self.dir / "company"
        (folder / ".nodejam" / "examples").mkdir(parents=True)
        wrapper = {"form": "Inventory", "kind": "sheet", "name": EX.name_pattern("Inventory Alpha 2025.xlsx"),
                   "fingerprint": json.loads(self.ex.read_text())}
        (folder / ".nodejam" / "examples" / "co-inventory.json").write_text(json.dumps(wrapper))
        (folder / "work").mkdir()
        make_sheet(folder / "work" / "Inventory Beta.xlsx", headers=("Image", "Name", "Qty", "Size", "Price ex VAT"))
        make_sheet(folder / "work" / "Budget.xlsx", headers=("Image", "Name"))
        for name, code in (("Inventory Beta.xlsx", 1), ("Budget.xlsx", 0)):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(EX.main(["check", str(folder / "work" / name), "--installed"]), code, name)

    def test_the_pack_the_app_installed_is_read_when_the_folder_has_none(self):
        pack = self.dir / "company-pack"
        (pack / "examples").mkdir(parents=True)
        wrapper = {"form": "Inventory", "kind": "sheet", "name": EX.name_pattern("Inventory Alpha 2025.xlsx"),
                   "fingerprint": json.loads(self.ex.read_text())}
        (pack / "examples" / "co-inventory.json").write_text(json.dumps(wrapper))
        (self.dir / "mine").mkdir()
        make_sheet(self.dir / "mine" / "Inventory Gamma.xlsx", headers=("Image", "Name", "Qty", "Size", "Price ex VAT"))
        with mock.patch.dict(os.environ, {"NODEJAM_COMPANY_PACK": str(pack)}):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(EX.main(["check", str(self.dir / "mine" / "Inventory Gamma.xlsx"), "--installed"]), 1)
            self.assertIn("FAIL column 'Supplier'", out.getvalue())

    def test_an_unreadable_file_is_not_checked_not_failed(self):
        bad = self.dir / "bad.xlsx"
        bad.write_text("not a workbook")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = EX.main(["check", str(bad), "--examples", str(self.ex)])
        self.assertEqual(code, 3)
        self.assertTrue(out.getvalue().startswith("pack check not checked:"))


class Merge(unittest.TestCase):
    def test_columns_all_examples_share_stay(self):
        def sheet(headers):
            return {"kind": "sheet", "file": "x.xlsx", "name_pattern": {}, "sheets": [{
                "name": "Blad 1", "title": None, "sections": None, "totals": [{"label": "Total"}],
                "columns": [{"key": h.lower(), "header": h, "meaning": "text"} for h in headers]}]}
        merged = EX.merge([sheet(["A", "B", "C"]), sheet(["A", "C", "D"])])
        self.assertEqual([c["header"] for c in merged["sheets"][0]["columns"]], ["A", "C"])



class ChainTest(unittest.TestCase):
    """Example Print r19, 2026-10-18: a hand-filled list beside a deck made here, and a tidplan laid from a list that
    changed after it."""

    def test_a_hand_filled_list_beside_a_deck_and_a_stale_tidplan_fail(self):
        from openpyxl import Workbook
        from openpyxl.packaging.custom import StringProperty
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "wa" / "koncept" / "ostersund").mkdir(parents=True)
            (root / "wa" / "koncept" / "ostersund" / "roster.json").write_text("{}")
            def a_list(name, drawn):
                wb = Workbook(); ws = wb.active
                ws.append(["Artikellista test"]); ws.append(["Yta: Matsalen"]); ws.append(["Bild", "Benämning", "Antal"])
                ws.append([None, "Stol", 66])
                if drawn:
                    wb.custom_doc_props.append(StringProperty(name="Customer form", value="vaxjo_sheet.py"))
                wb.save(root / name)
                return root / name
            with mock.patch.dict(os.environ, {"NODEJAM_WORK_AREA": str(root / "wa")}):
                self.assertIn("skeleton", EX.chain_findings(a_list("hand.xlsx", False))[0])
                self.assertEqual(EX.chain_findings(a_list("drawn.xlsx", True)), [])
            wb = Workbook()
            for title in ("Beställningar", "Sammanfattning", "Anteckningar"):
                wb.create_sheet(title)
            wb["Anteckningar"].append(["Punkt", "Anteckning", "Källa"])
            wb["Anteckningar"].append(["Block", "En Yta är ett block", "drawn.xlsx"])
            wb.properties.identifier = "tidplan/1.0"
            wb.save(root / "Tidplan.xlsx")
            self.assertEqual(EX.chain_findings(root / "Tidplan.xlsx"), [])
            os.utime(root / "Tidplan.xlsx", (0, os.path.getmtime(root / "drawn.xlsx") - 60))
            self.assertIn("from_list.py", EX.chain_findings(root / "Tidplan.xlsx")[0])
            hand = Workbook(); hand.active.title = "Tidplan"; hand.active.append(["Reception", "v.1"])
            hand.save(root / "Tidplan hand.xlsx")
            self.assertIn("from_list.py", EX.chain_findings(root / "Tidplan hand.xlsx")[0])
            own = Workbook(); own.active.title = "Tidplan"; own.properties.creator = "Sam"
            own.save(root / "Tidplan plan 13.xlsx")
            self.assertEqual(EX.chain_findings(root / "Tidplan plan 13.xlsx"), [])


if __name__ == "__main__":
    unittest.main()



class Fill(unittest.TestCase):
    """A list with the example's columns but empty sizes and prices is named, not passed (tailor proof 2026-10-12)."""

    def test_an_empty_column_the_examples_fill_is_off(self):
        import openpyxl
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)

        def book(path, rows):
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.append(["Name", "Qty", "Size", "Price"])
            for r in rows:
                ws.append(r)
            wb.save(path)
        book(d / "ex.xlsx", [["Chair %d" % i, 2 + i, "W 50 x D 50", 1200 + i] for i in range(12)])
        book(d / "new.xlsx", [["Chair %d" % i, 1, None, 0] for i in range(12)])
        found = {f["field"]: f for f in EX.compare(EX.fingerprint(d / "ex.xlsx"), EX.fingerprint(d / "new.xlsx"))}
        self.assertEqual(found["fill of 'Size'"]["verdict"], "different")
        self.assertEqual(found["fill of 'Price'"]["verdict"], "different")
        self.assertEqual(found["fill of 'Name'"]["verdict"], "same")



class Figures(unittest.TestCase):
    """A placeholder word where the examples hold figures is no fill (run B6: "Saknas" in every price)."""

    def test_saknas_in_a_price_column_is_no_price(self):
        import tempfile
        from openpyxl import Workbook
        with tempfile.TemporaryDirectory() as tmp:
            def book(name, price):
                wb = Workbook(); ws = wb.active
                ws.append(["Benämning", "Antal", "Pris"])
                for k in range(12):
                    ws.append(["Stol %d" % k, 2, price(k)])
                wb.save(f"{tmp}/{name}.xlsx")
                return f"{tmp}/{name}.xlsx"
            example = EX.fingerprint(book("ex", lambda k: 1200 + k))
            got = EX.fingerprint(book("new", lambda k: "Saknas"))
            found = [f for f in EX.compare(example, got) if f["field"] == "fill of 'Pris'"]
            self.assertEqual(found[0]["verdict"], "different")
            self.assertIn("has a figure", found[0]["note"])
