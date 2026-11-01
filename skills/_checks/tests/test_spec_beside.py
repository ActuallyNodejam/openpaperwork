"""spec_beside: a document is read with its own spec, not the first JSON in its folder (agent run 9)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import letter_check


class OwnSpecFirst(unittest.TestCase):
    def test_packing_list_beside_its_invoice(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            parties = {"seller": {"name": "S"}, "buyer": {"name": "B"}}
            (d / "commercial-invoice.spec.json").write_text(json.dumps(dict(parties, type="proforma_invoice")))
            (d / "packing-list.spec.json").write_text(json.dumps(dict(parties, type="delivery_note")))
            self.assertEqual(letter_check.spec_beside(d / "packing-list.docx")["type"], "delivery_note")
            self.assertEqual(letter_check.spec_beside(d / "commercial-invoice.docx")["type"], "proforma_invoice")
            self.assertEqual(letter_check.spec_beside(d / "other.docx")["type"], "proforma_invoice")
            (d / "packing-list.spec.json").rename(d / "z-note-spec.json")
            self.assertEqual(letter_check.spec_beside(d / "z-note.pdf")["type"], "delivery_note")


if __name__ == "__main__":
    unittest.main()
