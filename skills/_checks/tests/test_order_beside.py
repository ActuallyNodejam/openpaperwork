"""order_beside: the order is the task's own, never a template of a pack installed in the task folder."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import einvoice_page


class InstalledPacksAreNotOrders(unittest.TestCase):
    def test_skills_in_the_task_folder(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            line = [{"name": "x", "quantity": 1, "unit_price": 1}]
            template = d / ".agents/skills/e-invoice/templates/at-rechnung-spec.json"
            template.parent.mkdir(parents=True)
            template.write_text(json.dumps({"lines": line, "seller": {"country": "AT"}}))
            (d / "invoice-spec.json").write_text(json.dumps({"lines": line, "seller": {"country": "SE"}}))
            found, data = einvoice_page.order_beside(d / "invoice.pdf")
            self.assertEqual(found.name, "invoice-spec.json")
            self.assertEqual(data["seller"]["country"], "SE")


if __name__ == "__main__":
    unittest.main()
