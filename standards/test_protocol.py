"""Contract checks using deliberately minimal XML packages, never product outputs."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from xml.sax.saxutils import escape
import zipfile

ROOT = Path(__file__).resolve().parent


def package(path, parts):
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('[Content_Types].xml', '<Types/>')
        z.writestr('_rels/.rels', '<Relationships/>')
        for name, text in parts.items():
            z.writestr(name, text)


def document(path):
    package(path, {'word/document.xml': '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Minimal checker test, not a rendered artifact.</w:t></w:r></w:p></w:body></w:document>'})


def workbook(path, revised=False, wrong_total=False, formula=True):
    data = [['Supplier','Quantity','Unit price EUR','Shipping EUR','Total EUR','Delivery date','Eligible'],
            ['Northlight',12,42.5,30,540,'2026-11-09','Yes'],
            ['Fielddesk',12,39,24,492,'2026-11-14','No'],
            ['Studio Supply',12,49 if revised else 44,0,588 if revised else 528,'2026-11-13' if revised else '2026-11-08','No' if revised else 'Yes']]
    if wrong_total: data[1][4] = 539
    rows=[]
    for n,row in enumerate(data,1):
        cells=[]
        for col,value in zip('ABCDEFG',row):
            ref=col+str(n)
            if isinstance(value,str):
                cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape(value)}</t></is></c>')
            else:
                f=f'<f>B{n}*C{n}+D{n}</f>' if col=='E' and formula else ''
                cells.append(f'<c r="{ref}">{f}<v>{value}</v></c>')
        rows.append('<row>'+''.join(cells)+'</row>')
    ns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    package(path, {
      'xl/workbook.xml': f'<workbook xmlns="{ns}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Comparison" r:id="r1"/><sheet name="Recommendation" r:id="r2"/></sheets></workbook>',
      'xl/_rels/workbook.xml.rels': '<Relationships><Relationship Id="r1" Target="worksheets/sheet1.xml"/><Relationship Id="r2" Target="worksheets/sheet2.xml"/></Relationships>',
      'xl/worksheets/sheet1.xml': f'<worksheet xmlns="{ns}"><sheetData>'+''.join(rows)+'</sheetData></worksheet>',
      'xl/worksheets/sheet2.xml': f'<worksheet xmlns="{ns}"><sheetData><row><c r="A1" t="inlineStr"><is><t>Minimal test recommendation</t></is></c></row></sheetData></worksheet>'})


class Protocol(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.dest=Path(self.temp.name)/'run'
    def tearDown(self): self.temp.cleanup()
    def call(self,*args,code=0):
        result=subprocess.run([sys.executable,str(ROOT/'run.py'),*map(str,args)],capture_output=True,text=True)
        self.assertEqual(result.returncode,code,result.stdout+result.stderr)
        return result
    def prepare(self,case): self.call('prepare',case,self.dest)
    def test_prepare_withholds_revision_and_answers(self):
        self.prepare('brief-001')
        self.assertEqual(sorted(p.name for p in (self.dest/'task').iterdir()),['inputs','request.md'])
        self.assertIsNone(json.loads((self.dest/'run.json').read_text())['attempts']['first']['model_cost_usd'])
        self.call('prepare','brief-001',self.dest,code=2)
    def test_missing_output_fails(self):
        self.prepare('brief-001'); self.call('check',self.dest,'first',code=1)
    def test_bad_zip_fails(self):
        self.prepare('brief-001'); (self.dest/'first/brief.docx').write_text('not a zip')
        self.call('check',self.dest,'first',code=1)
    def test_pass_still_requires_review(self):
        self.prepare('brief-001'); document(self.dest/'first/brief.docx')
        result=json.loads(self.call('check',self.dest,'first').stdout)
        self.assertEqual(result['acceptance'],'needs_review')
        self.assertTrue(result['required_review'])
    def test_revision_freezes_first(self):
        self.prepare('brief-001'); document(self.dest/'first/brief.docx')
        self.call('revision',self.dest); document(self.dest/'revision/brief.docx')
        self.call('check',self.dest,'revision')
        (self.dest/'first/brief.docx').write_text('overwritten')
        self.call('check',self.dest,'revision',code=1)
        self.call('revision',self.dest,code=2)
    def test_revision_cannot_be_scored_before_reveal(self):
        self.prepare('brief-001'); document(self.dest/'revision/brief.docx')
        self.call('check',self.dest,'revision',code=1)
    def test_quote_changes_and_wrong_total(self):
        self.prepare('quotes-001'); workbook(self.dest/'first/comparison.xlsx')
        self.call('check',self.dest,'first'); self.call('revision',self.dest)
        workbook(self.dest/'revision/comparison.xlsx')
        self.call('check',self.dest,'revision',code=1)
        workbook(self.dest/'revision/comparison.xlsx',revised=True)
        self.call('check',self.dest,'revision')
        workbook(self.dest/'revision/comparison.xlsx',revised=True,wrong_total=True)
        self.call('check',self.dest,'revision',code=1)
    def test_hardcoded_totals_are_not_formulas(self):
        self.prepare('quotes-001'); workbook(self.dest/'first/comparison.xlsx',formula=False)
        self.call('check',self.dest,'first',code=1)
    def test_version_drift_is_explicit(self):
        self.prepare('brief-001'); path=self.dest/'run.json'; meta=json.loads(path.read_text())
        meta['source_hashes']={}; path.write_text(json.dumps(meta))
        self.call('check',self.dest,'first',code=2)
    def test_deck_length(self):
        self.prepare('update-001')
        for count,code in [(5,0),(4,1)]:
            parts={'ppt/presentation.xml':'<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:sldIdLst>'+''.join(f'<p:sldId id="{i}"/>' for i in range(count))+'</p:sldIdLst></p:presentation>'}
            parts.update({f'ppt/slides/slide{i+1}.xml':'<a:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:t>Minimal test text</a:t></a:sld>' for i in range(count)})
            package(self.dest/'first/update.pptx',parts); self.call('check',self.dest,'first',code=code)


if __name__=='__main__': unittest.main()
