"""Original synthetic document geometry cases; no customer fixtures."""
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

from docx import Document
from docx.enum.section import WD_SECTION
from docx.shared import Mm
from docx_validate import validate


class TableWidthTest(unittest.TestCase):
    def add_table(self, document, width):
        table = document.add_table(rows=2, cols=2)
        table.autofit = False
        for column in table.columns:
            column.width = Mm(width / 2)
        for row in table.rows:
            for cell in row.cells:
                cell.width = Mm(width / 2)
                cell.text = "Fictional requirement"
        return table

    def report(self, document):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'fixture.docx'
            document.save(path)
            before = hashlib.sha256(path.read_bytes()).digest()
            report = validate(str(path))
            self.assertEqual(hashlib.sha256(path.read_bytes()).digest(), before)
            return report

    def test_wide_table_is_flagged_in_its_own_section(self):
        document = Document()
        section = document.sections[0]
        section.page_width = Mm(210)
        section.page_height = Mm(297)
        section.left_margin = section.right_margin = Mm(20)
        self.add_table(document, 200)
        section = document.add_section(WD_SECTION.NEW_PAGE)
        section.page_width = Mm(297)
        section.page_height = Mm(210)
        self.add_table(document, 200)
        warnings = [i for i in self.report(document)['issues'] if i['code'] == 'table-width-overflow']
        self.assertEqual(len(warnings), 1)
        self.assertIn('Table 1', warnings[0]['detail'])

    def test_cells_wider_than_grid_are_flagged(self):
        document = Document()
        table = self.add_table(document, 100)
        for row in table.rows:
            for cell in row.cells:
                cell.width = Mm(150)
        self.assertTrue(any(i['code'] == 'table-width-overflow' for i in self.report(document)['issues']))

    def test_fitting_table_does_not_raise_width_warning(self):
        document = Document()
        self.add_table(document, 100)
        self.assertFalse(any(i['code'] == 'table-width-overflow' for i in self.report(document)['issues']))


def one_pixel_png():
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 0, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(b'\x00\x00')) + chunk(b'IEND', b''))


class HeaderRelationshipTest(unittest.TestCase):
    def test_header_picture_keeps_document_references_resolved(self):
        # The header's .rels sits in the same folder as the document's; which one a set
        # yields last follows the hash seed, so the file is checked under several.
        with tempfile.TemporaryDirectory() as folder:
            picture = Path(folder) / 'mark.png'
            picture.write_bytes(one_pixel_png())
            document = Document()
            document.sections[0].header.paragraphs[0].add_run().add_picture(str(picture))
            document.add_picture(str(picture))
            path = Path(folder) / 'fixture.docx'
            document.save(path)
            script = Path(__file__).with_name('docx_validate.py')
            for seed in range(8):
                proc = subprocess.run([sys.executable, str(script), str(path)], capture_output=True, text=True,
                                      env={**os.environ, 'PYTHONHASHSEED': str(seed)})
                codes = [i['code'] for i in json.loads(proc.stdout)['issues']]
                self.assertNotIn('unresolved-reference', codes, f'hash seed {seed}')


if __name__ == '__main__':
    unittest.main()
