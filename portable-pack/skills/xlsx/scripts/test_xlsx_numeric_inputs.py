"""Regression for Q1 measurements stored as text and skipped by SUM."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from openpyxl import Workbook
import xlsx_read


class NumericInputs(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "counts.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.title = "Counts"
        ws["B4"] = "00123"
        ws["C4"] = 4
        ws["D4"] = 4
        ws["E4"] = "4"
        ws["F4"] = '=SUM(C4:E4)'
        ws["C5"] = 0
        ws["D5"] = -2.5
        ws["E5"] = None
        wb.save(self.path)
        self.original = hashlib.sha256(self.path.read_bytes()).hexdigest()

    def check(self, cells, *extra):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = xlsx_read.main([str(self.path), "--check-numbers", "--sheet", "Counts", "--range", cells, *extra])
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(), self.original)
        return code, json.loads(output.getvalue())

    def test_text_measurements_are_not_ready(self):
        code, result = self.check("C4:E4")
        self.assertEqual(code, 1)
        self.assertFalse(result["ok"])
        self.assertEqual(result["numeric_cells"], 2)
        self.assertEqual(result["issues"], [{"cell": "E4", "value": "4", "native_type": "s", "problem": "text_in_numeric_input"}])
        self.assertEqual(result["issue_count"], 1)

    def test_zero_negative_and_missing_preserve_identifiers(self):
        code, result = self.check("C5:E5")
        self.assertEqual(code, 0)
        self.assertTrue(result["ok"])
        self.assertEqual(result["numeric_cells"], 2)
        self.assertEqual(result["blank_cells"], 1)
        self.assertEqual(result["issues"], [])

    def test_formula_is_not_claimed_as_a_verified_input(self):
        code, result = self.check("F4")
        self.assertEqual(code, 1)
        self.assertEqual(result["issues"][0]["problem"], "formula_not_verified")

    def test_unbounded_and_cached_only_checks_are_rejected(self):
        with self.assertRaises(ValueError):
            self.check("C:C")
        with self.assertRaises(ValueError):
            self.check("A1:ZZ1000")
        with self.assertRaises(ValueError):
            self.check("E29:C4")
        with self.assertRaises(ValueError):
            self.check("A0:C4")
        with self.assertRaises(ValueError):
            self.check("C4:E4", "--data-only")
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(), self.original)


if __name__ == "__main__":
    unittest.main()
