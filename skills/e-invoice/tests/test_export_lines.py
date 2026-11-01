"""An export line's customs code and origin, EN 16931 BT-158 and BT-159 (agent run 9, 2026-10-14)."""
import json
import sys
import unittest
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
for sub in ("scripts", "page"):
    sys.path.insert(0, str(PACK / sub))
sys.path.insert(0, str(PACK.parent / "_shared"))
import einvoice_create as cii  # noqa: E402


def export():
    spec = json.loads((PACK / "templates" / "se-faktura-rabatt-forskott-spec.json").read_text())
    spec["buyer"] = {"name": "Pacific Hardware Pty Ltd", "street": "22 Dock Road", "postcode": "3207",
                     "city": "Port Melbourne", "country": "AU"}
    spec["exemption_reason"] = "Export of goods outside the EU"
    for line in spec["lines"]:
        line.update(vat_rate=0, vat_category="G", hs_code="8204.11", origin="se")
        for key in ("discount_percent", "discount_amount", "discount_reason", "discount_reason_code"):
            line.pop(key, None)
    for key in ("prepaid", "prepayments", "allowances", "charges"):
        spec.pop(key, None)
    return spec


class ExportLines(unittest.TestCase):
    def test_cii_carries_code_and_origin(self):
        data, _summary, _syntax = cii.document_xml(dict(export(), syntax="cii"))
        xml = data.decode() if isinstance(data, bytes) else data
        self.assertIn('<ram:ClassCode listID="HS">820411</ram:ClassCode>', xml)
        self.assertIn("<ram:OriginTradeCountry>", xml)
        self.assertIn("<ram:ID>SE</ram:ID>", xml)

    def test_origin_is_two_letters(self):
        spec = export()
        spec["lines"][0]["origin"] = "Sweden"
        with self.assertRaises(SystemExit):
            cii.document_xml(dict(spec, syntax="cii"))


if __name__ == "__main__":
    unittest.main()
