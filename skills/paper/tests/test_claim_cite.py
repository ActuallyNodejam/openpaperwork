"""PAPER-CLAIM-CITE: a claim about the field or others' work names its source (agent run 8, 2026-10-14)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_checks"))
import academic_style

HEAD = "\\documentclass{article}\n\\begin{document}\n\\begin{abstract}Models often fail.\\end{abstract}\n"
FOOT = "\n\\begin{thebibliography}{1}\\bibitem{yao} S. Yao.\\end{thebibliography}\n\\end{document}\n"


def verdict(body):
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "paper.tex"
        path.write_text(HEAD + body + FOOT)
        return academic_style.check("PAPER-CLAIM-CITE", path, None, None)[0]


class ClaimCite(unittest.TestCase):
    def test_uncited_claim_fails(self):
        self.assertFalse(verdict("When models like GPT-3.5 are prompted, they often violate the rules. The rest."))

    def test_cited_claim_passes(self):
        self.assertTrue(verdict("Models often violate the rules \\cite{yao}. The rest."))

    def test_topic_sentence_cited_next(self):
        self.assertTrue(verdict("Recent work shows agents improve. \\cite{yao} interleaves reasoning and action."))

    def test_own_work_and_future_work_pass(self):
        self.assertTrue(verdict("We often saw the check pass. Further research should test larger samples."))

    def test_abstract_is_not_read(self):
        self.assertTrue(verdict("Plain text."))


if __name__ == "__main__":
    unittest.main()
