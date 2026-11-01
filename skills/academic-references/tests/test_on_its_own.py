"""A reference list handed back on its own: its form is read, its citing is not (timed run c19, 2026-10-25)."""
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_checks"))
import academic_style  # noqa: E402

TYPES = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/'
         'content-types"><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/'
         'document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main'
         '+xml"/></Types>')
LIST = ["Devlin, J., Chang, M.-W., Lee, K., & Toutanova, K. (2019). BERT: Pre-training of deep bidirectional "
        "transformers for language understanding. In Proceedings of NAACL-HLT (pp. 4171\u20134186).",
        "LeCun, Y., Bengio, Y., & Hinton, G. (2015). Deep learning. Nature, 521(7553), 436\u2013444."]


def docx(folder, paragraphs):
    body = "".join("<w:p><w:r><w:t xml:space=\"preserve\">%s</w:t></w:r></w:p>" % escape(p) for p in paragraphs)
    path = Path(folder) / "references.docx"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", TYPES)
        z.writestr("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/'
                   '2006/main"><w:body>%s</w:body></w:document>' % body)
    return path


class OnItsOwn(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def test_a_list_on_its_own_is_not_sent_back_for_citations(self):
        path = docx(self.dir, ["References"] + LIST)
        for rule in ("APA-REF-CITED", "APA-REFS-NEW-PAGE", "APA-NO-INTRO"):
            ok, why = academic_style.check(rule, path, None, None)
            self.assertTrue(ok or why.startswith("not measured"), (rule, why))
        self.assertEqual(academic_style.uncited_entries(path), [])   # repair_refs.py --remove takes nothing out

    def test_text_above_the_list_still_has_to_cite_it(self):
        path = docx(self.dir, ["Language models changed how text is read by machines, and the field moved fast "
                               "after the transformer (Devlin et al., 2019).", "References"] + LIST)
        ok, why = academic_style.check("APA-REF-CITED", path, None, None)
        self.assertFalse(ok)
        self.assertIn("LeCun 2015", why)
        self.assertNotIn("Devlin", why)            # cited as (Devlin et al., 2019)


if __name__ == "__main__":
    unittest.main()
