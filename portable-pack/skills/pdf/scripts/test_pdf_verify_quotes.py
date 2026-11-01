import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from reportlab.pdfgen.canvas import Canvas


class QuoteContract(unittest.TestCase):
    def test_cli_citations_and_source_preservation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "source.pdf"
            canvas = Canvas(str(source))
            canvas.drawString(50, 700, "Keep the existing oak table.")
            canvas.showPage()
            canvas.drawString(50, 700, "No lamp model is specified.")
            canvas.save()
            original = hashlib.sha256(source.read_bytes()).hexdigest()
            for quote, pages, status in [
                ("Keep the existing oak table.", [1], 0),
                ("keep  the existing oak table.", [1], 0),
                ("Keep the existing oak table.", [2], 1),
                ("Buy a new oak table.", [1], 1),
                ("Keep the existing oak table.", [0], 2),
                ("Keep the existing oak table.", [True], 2),
                ("", [1], 2),
            ]:
                with self.subTest(quote=quote, pages=pages):
                    manifest = root / "quotes.json"
                    manifest.write_text(json.dumps([{"id": "row-1", "quote": quote, "pages": pages}]))
                    result = subprocess.run([sys.executable, str(Path(__file__).with_name("pdf_verify_quotes.py")), str(source), str(manifest)], capture_output=True, text=True)
                    self.assertEqual(result.returncode, status, result.stdout + result.stderr)
                    self.assertEqual(json.loads(result.stdout)["ok"], status == 0)
                    self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), original)


if __name__ == "__main__":
    unittest.main()
