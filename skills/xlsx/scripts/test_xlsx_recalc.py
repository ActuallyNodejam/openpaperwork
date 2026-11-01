#!/usr/bin/env python3
"""A stale native cache must actually change; conversion success is insufficient."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import shutil
import tempfile
import unittest
from zipfile import ZipFile
from openpyxl import Workbook, load_workbook

spec = importlib.util.spec_from_file_location("recalc", Path(__file__).with_name("xlsx_recalc.py"))
recalc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recalc)


@unittest.skipUnless(shutil.which("soffice"), "LibreOffice Calc is optional")
class Recalculation(unittest.TestCase):
    def test_formula_errors_do_not_replace_input_or_destination(self):
        for formula, expected in [("=1/0", "#DIV/0!"), ("=MISSING_FUNCTION(1)", "#NAME?")]:
            with self.subTest(formula=formula), tempfile.TemporaryDirectory() as folder:
                source = Path(folder) / "input.xlsx"
                output = Path(folder) / "existing.xlsx"
                book = Workbook()
                book.active["A1"] = formula
                book.save(source)
                output.write_bytes(b"existing destination")
                before = source.read_bytes()
                for args in ([str(source)], [str(source), "--out", str(output)]):
                    message = io.StringIO()
                    with contextlib.redirect_stdout(message):
                        status = recalc.main(args)
                    receipt = json.loads(message.getvalue())
                    self.assertEqual(status, 1)
                    self.assertFalse(receipt["ok"])
                    self.assertFalse(receipt["saved"])
                    self.assertEqual(receipt["formula_errors"][0]["cell"], "A1")
                    self.assertEqual(receipt["formula_errors"][0]["error"], expected)
                    self.assertEqual(source.read_bytes(), before)
                    self.assertEqual(output.read_bytes(), b"existing destination")

    def test_stale_cache_is_recomputed_without_changing_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "input.xlsx"
            output = root / "recalculated.xlsx"
            book = Workbook()
            sheet = book.active
            sheet["B3"] = 2_000_000
            sheet["B4"] = 51_000
            sheet["B6"] = 0.05
            sheet["B8"] = "=B3*(1+B6)+B4"
            book.save(source)
            with ZipFile(source) as original:
                parts = [(info, original.read(info.filename)) for info in original.infolist()]
            with ZipFile(source, "w") as changed:
                for info, content in parts:
                    if info.filename == "xl/worksheets/sheet1.xml":
                        xml = ET.fromstring(content)
                        ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
                        rate = xml.find(f'.//{ns}c[@r="B6"]/{ns}v')
                        cache = xml.find(f'.//{ns}c[@r="B8"]/{ns}v')
                        self.assertIsNotNone(rate)
                        self.assertIsNotNone(cache)
                        rate.text = "0.1"
                        cache.text = "2151000"
                        content = ET.tostring(xml, encoding="utf-8")
                    changed.writestr(info, content)
            self.assertEqual(load_workbook(source)["Sheet"]["B6"].value, 0.1)
            self.assertEqual(load_workbook(source, data_only=True)["Sheet"]["B8"].value, 2_151_000)
            before = hashlib.sha256(source.read_bytes()).hexdigest()
            message = io.StringIO()
            with contextlib.redirect_stdout(message):
                status = recalc.main([str(source), "--out", str(output)])
            self.assertEqual(status, 0)
            self.assertTrue(json.loads(message.getvalue())["recalculated"])
            self.assertEqual(load_workbook(output, data_only=True)["Sheet"]["B8"].value, 2_251_000)
            self.assertEqual(load_workbook(output)["Sheet"]["B8"].value, "=B3*(1+B6)+B4")
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)


if __name__ == "__main__":
    unittest.main()
