import tempfile
import unittest
from pathlib import Path
from reportlab.pdfgen.canvas import Canvas
from pdf_verify_identifiers import verify


class IdentifierEvidenceTest(unittest.TestCase):
    def test_sparse_labels_and_actual_claims(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "drawing.pdf"
            canvas = Canvas(str(source))
            canvas.drawString(30, 700, "0101a 0101c 0102a 0104 0104b 90101 0101c")
            canvas.showPage()
            canvas.save()
            pattern = r"0[0-9]{3}[a-z]?"
            expected = ["0101a", "0101c", "0102a", "0104", "0104b"]
            result = verify(source, pattern, expected)
            self.assertTrue(result["ok"])
            self.assertEqual(result["source_count"], 5)
            self.assertEqual(result["source_pages"]["0101c"], [1])
            wrong = verify(source, pattern, ["0101a", "0101b", "0101c", "0102a", "0104"])
            self.assertFalse(wrong["ok"])
            self.assertEqual(wrong["extra"], ["0101b"])
            self.assertEqual(wrong["missing"], ["0104b"])
            self.assertFalse(verify(source, pattern, expected + ["0101a"])["ok"])
            self.assertFalse(verify(source, r"ZZ[0-9]+")["ok"])
            with self.assertRaises(ValueError):
                verify(source, pattern, [101])
            with self.assertRaises(ValueError):
                verify(source, pattern, pages=[2])

    def test_empty_page_does_not_certify_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "drawing.pdf"
            canvas = Canvas(str(source))
            canvas.drawString(30, 700, "0101a")
            canvas.showPage()
            canvas.showPage()
            canvas.save()
            result = verify(source, r"0[0-9]{3}[a-z]?", ["0101a"])
            self.assertFalse(result["ok"])
            self.assertEqual(result["empty_text_pages"], [2])
            self.assertTrue(verify(source, r"0[0-9]{3}[a-z]?", ["0101a"], pages=[1])["ok"])


if __name__ == "__main__":
    unittest.main()
