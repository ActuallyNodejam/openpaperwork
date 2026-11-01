"""TRADE-INCOTERMS: a quotation, order confirmation, pro forma or delivery note that agrees a delivery term
prints the rule, its named place and Incoterms 2020 (ICC Incoterms 2020, INCO-1). The builder always does; the
check catches a page that lost the place after. Needs python-docx."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
CHECKS = HERE.parent / "_checks"
sys.path.insert(0, str(CHECKS))
import purchase_order_check  # noqa: E402


def build(name, out):
    folder = Path(tempfile.mkdtemp())
    (folder / "spec.json").write_text((HERE / "templates" / name).read_text())
    subprocess.run([sys.executable, str(HERE / "scripts" / "trade_create.py"), "spec.json", out],
                   cwd=folder, check=True, capture_output=True)
    return folder / out


def drop_place(path, place):
    import docx
    doc = docx.Document(str(path))
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    if place in p.text:
                        text = p.text.replace(place, "")
                        for run in p.runs[1:]:
                            run._element.getparent().remove(run._element)
                        p.runs[0].text = text
    doc.save(str(path))


class Incoterms(unittest.TestCase):
    def test_a_quotation_states_its_rule_and_place(self):
        out = build("quotation-au.spec.json", "quotation.docx")
        ok, why = purchase_order_check.check("TRADE-INCOTERMS", out, {}, "first")
        self.assertTrue(ok, why)

    def test_a_quotation_without_the_named_place_fails(self):
        out = build("quotation-au.spec.json", "quotation.docx")
        drop_place(out, "Toowoomba QLD")
        ok, why = purchase_order_check.check("TRADE-INCOTERMS", out, {}, "first")
        self.assertFalse(ok)
        self.assertIn("Toowoomba QLD", why)

    def test_a_purchase_order_is_left_to_its_own_rule(self):
        out = build("purchase-order.spec.json", "po.docx")
        ok, why = purchase_order_check.check("TRADE-INCOTERMS", out, {}, "first")
        self.assertIsNone(ok, why)


if __name__ == "__main__":
    unittest.main()
