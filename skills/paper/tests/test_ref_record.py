"""PAPER-REF-RECORD against a registry record, with the registry stubbed so it runs offline."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_checks"))
import academic_style  # noqa: E402

ENTRY = ("\\bibitem{dekoster2007} R. {de Koster}, T. Le-Duc, and K. J. %s, ``Design and control of warehouse order "
         "picking: A literature review,\'\' \\emph{Eur. J. Oper. Res.}, vol.~182, pp.~481--501, 2007, "
         "doi: 10.1016/j.ejor.2006.07.009.")
RECORD = {"found": True, "authors": ["de Koster", "Le-Duc", "Roodbergen"]}


def verdict(entry):
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "paper.tex"
        path.write_text("\\begin{document}Text.\n\\begin{thebibliography}{1}\n%s\n\\end{thebibliography}\n"
                        "\\end{document}\n" % entry)
        return academic_style.paper_ref_record(path)


class RefRecord(unittest.TestCase):
    def setUp(self):
        self.saved = academic_style._registries_answer, academic_style._record
        academic_style._registries_answer = lambda: True
        academic_style._record = lambda ident: RECORD

    def tearDown(self):
        academic_style._registries_answer, academic_style._record = self.saved

    def test_a_surname_with_a_particle_is_its_author(self):
        ok, why = verdict(ENTRY % "Roodbergen")
        self.assertTrue(ok, why)

    def test_an_author_the_record_does_not_list_still_fails(self):
        ok, why = verdict(ENTRY % "Smith")
        self.assertFalse(ok)
        self.assertIn("Smith", why)


if __name__ == "__main__":
    unittest.main()
