"""Offline tests for build_paper.py: error reading and page counting. No TeX engine needed."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_paper


class FirstError(unittest.TestCase):
    def test_tex_log(self):
        log = 'junk\n! Undefined control sequence.\nl.12 Hello \\foo\n world\n'
        self.assertEqual(build_paper.first_error(log), ('Undefined control sequence.', 12, 'Hello \\foo'))

    def test_tectonic_line(self):
        msg, line, _ = build_paper.first_error('note: x\nerror: paper.tex:3: Undefined control sequence\nerror: halted\n')
        self.assertEqual((msg, line), ('Undefined control sequence', 3))

    def test_empty(self):
        self.assertEqual(build_paper.first_error('')[1], None)


class Pages(unittest.TestCase):
    def test_count(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'a.pdf'
            p.write_bytes(b'%PDF-1.5\n1 0 obj << /Type /Pages /Kids [2 0 R 3 0 R] /Count 2 >> endobj\n')
            self.assertEqual(build_paper.page_count(p), 2)


class Missing(unittest.TestCase):
    def test_no_file(self):
        self.assertEqual(build_paper.main(['/nonexistent/paper.tex']), 2)


if __name__ == '__main__':
    unittest.main()
