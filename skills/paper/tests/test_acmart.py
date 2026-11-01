"""The ACM starter carries acmart 2.20 and the builder puts it beside the .tex. No TeX engine needed."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
CLS = SKILL / "templates" / "acm-sigconf" / "acmart.cls"


class Acmart(unittest.TestCase):
    def test_version(self):
        self.assertIn("v2.20 Typesetting articles for the Association for Computing Machinery", CLS.read_text())

    def test_builder_copies_class(self):
        with tempfile.TemporaryDirectory() as d:
            spec = Path(d) / "paper.json"
            spec.write_text(json.dumps({"title": "T", "abstract": "A.", "sections": [{"heading": "One", "paragraphs": ["P."]}]}))
            subprocess.run([sys.executable, str(SKILL / "scripts" / "build_paper.py"), str(spec), str(Path(d) / "paper.tex"),
                            "--template", "acm-sigconf"], check=True, capture_output=True)
            self.assertEqual((Path(d) / "acmart.cls").read_bytes(), CLS.read_bytes())

    def test_acm_front_matter_before_maketitle(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("paper_json_builder", SKILL / "scripts" / "build_paper.py")
        b = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(b)
        tex = b.body({"title": "T", "abstract": "A.", "keywords": ["k"], "sections": []}, "acm-sigconf")
        self.assertLess(tex.index("\\end{abstract}"), tex.index("\\maketitle"))
        self.assertLess(tex.index("\\keywords{k}"), tex.index("\\maketitle"))
        self.assertNotIn("IEEEkeywords", tex)

    def test_ieee_gets_no_class(self):
        with tempfile.TemporaryDirectory() as d:
            spec = Path(d) / "paper.json"
            spec.write_text(json.dumps({"title": "T", "sections": []}))
            subprocess.run([sys.executable, str(SKILL / "scripts" / "build_paper.py"), str(spec), str(Path(d) / "paper.tex")],
                           check=True, capture_output=True)
            self.assertEqual(list(Path(d).glob("*.cls")), [])


if __name__ == "__main__":
    unittest.main()
