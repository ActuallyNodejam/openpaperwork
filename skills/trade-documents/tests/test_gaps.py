"""Trade documents: a discount as an amount, an allowance on the whole document and an amount paid in advance
(EN 16931-1 BG-27, BG-20, BT-113, BT-115; skills/_shared/doc_amounts.py is the one calculator), in each format
and under the sums rule; a purchase order without a delivery term is a question, and a description a PDF wraps
is still found. Seeded faults fail as designed. The PDF test needs Chromium and pdftotext."""
import json
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'scripts'))
import trade_create as tc  # noqa: E402
CHECKS = HERE.parent / '_checks'
sys.path.insert(0, str(CHECKS))
import money_check  # noqa: E402
import purchase_order_check as po  # noqa: E402


def spec(name):
    return json.loads((HERE / 'templates' / (name + '.spec.json')).read_text())


def confirmation():
    """The Swedish order confirmation with an amount off line 1, 5 percent off line 2, an allowance on the whole
    order at the 25 percent rate and 300 paid in advance."""
    s = spec('order-confirmation')
    s['lines'][0].pop('discount_percent', None)
    s['lines'][0].update(discount_amount=100, discount_reason='Kampanjrabatt')
    s['allowances'] = [{'amount': 50, 'reason': 'Orderrabatt', 'vat_rate': 25}]
    s.update(paid_amount=300, paid_date='2026-09-01')
    return s


def built(s, ext):
    folder = Path(tempfile.mkdtemp())
    src = folder / 'doc.spec.json'
    src.write_text(json.dumps(s, ensure_ascii=False))
    out = folder / ('doc.' + ext)
    assert tc.main([str(src), str(out)]) == 0
    return out


sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_trade_w9 import can_print  # noqa: E402


class Money(unittest.TestCase):
    def test_the_settlement_closes(self):
        data = tc.compute(confirmation())
        lines, vat, net, tax, gross = data
        self.assertEqual([l['net'] for l in lines], [Decimal('1100.00'), Decimal('1037.40')])
        self.assertEqual(data.money['line_total'], Decimal('2137.40'))
        self.assertEqual(net, Decimal('2087.40'))                              # BR-CO-13: lines less the allowance
        self.assertEqual(dict((r, v) for r, _, v in vat), {Decimal(25): Decimal('262.50'), Decimal(12): Decimal('124.49')})
        self.assertEqual(gross, Decimal('2474.39'))
        self.assertEqual(data.money['due'], Decimal('2174.39'))                # BR-CO-16

    def test_the_discount_column_is_there_only_when_a_line_has_one(self):
        self.assertIn('Discount', tc.Page(confirmation()).columns())
        plain = spec('order-confirmation')
        for l in plain['lines']:
            l['discount_percent'] = 0
        self.assertNotIn('Discount', tc.Page(plain).columns())

    def test_an_amount_paid_belongs_to_a_document_that_asks_for_payment(self):
        q = dict(spec('quotation'), paid_amount=100)
        with self.assertRaises(ValueError) as why:
            tc.compute(q)
        self.assertIn('paid_amount', str(why.exception))

    def test_what_does_not_close_stops_the_build(self):
        s = confirmation()
        s['paid_amount'] = 99999
        with self.assertRaises(ValueError):
            tc.compute(s)
        s = confirmation()
        s['lines'][1]['discount_amount'] = 1                                   # 5 percent of 1 092,00 is 54,60
        with self.assertRaises((ValueError, SystemExit)):
            tc.compute(s)

    def formats(self):
        return ('docx', 'xlsx') + (('pdf',) if can_print() else ())

    def test_every_format_states_the_discount_the_allowance_and_what_is_left_to_pay(self):
        s = confirmation()
        for ext in self.formats():
            with self.subTest(kind=ext):
                out = built(s, ext)
                doc = po.Doc(out)
                for amount in ('100.00', '54.60', '2137.40', '50.00', '2087.40', '2474.39', '300.00', '2174.39'):
                    self.assertTrue(po.has(doc.nums, amount), '%s not in the %s' % (amount, ext))
                for word in ('Orderrabatt', 'Summa rader', 'Förskottsbetalt', 'Att betala'):
                    self.assertIn(word.lower(), doc.flat.lower(), ext)
                ok, why = money_check.check('TRADE-SUMS', out, None, 'first')
                self.assertIs(ok, True, why)

    def test_a_file_that_does_not_match_its_data_fails_the_sums_rule(self):
        for ext in self.formats():
            with self.subTest(kind=ext):
                out = built(confirmation(), ext)
                src = out.parent / 'doc.spec.json'
                changed = confirmation()
                changed['paid_amount'] = 400                                   # the file still says 300 and 2 174,39
                src.write_text(json.dumps(changed, ensure_ascii=False))
                ok, why = money_check.check('TRADE-SUMS', out, None, 'first')
                self.assertIs(ok, False, why)
                self.assertIn('BT-113', why)
                changed = confirmation()
                changed['allowances'][0]['amount'] = 80
                src.write_text(json.dumps(changed, ensure_ascii=False))
                ok, why = money_check.check('TRADE-SUMS', out, None, 'first')
                self.assertIs(ok, False, why)
                self.assertIn('allowance', why)


class DeliveryTerm(unittest.TestCase):
    def test_a_purchase_order_across_a_border_without_a_term_is_asked_about_and_never_failed(self):
        s = spec('purchase-order')
        s.pop('delivery_terms', None)
        ok, why = po.po_incoterms(po.Doc(built(s, 'docx')), s)
        self.assertIs(ok, True)
        self.assertTrue(why.startswith('WARN'), why)
        self.assertIn('never picked', why)

    def test_a_term_the_file_does_not_print_still_fails(self):
        s = spec('purchase-order')
        out = built(s, 'docx')
        other = dict(s, delivery_terms={'rule': 'FCA', 'place': 'Hamburg, Germany'})
        ok, why = po.po_incoterms(po.Doc(out), other)
        self.assertIs(ok, False, why)


class WrappedDescription(unittest.TestCase):
    class Fake:
        kind = 'pdf'
        rows = ['Referencia | Descripción | Cantidad', 'Maquetación y | 6 h | 48,00 | 0 | 21 | 288,00', 'pruebas de color',
                'Total sin IVA | 3.483,00 EUR']

        def rows_with(self, needle):
            return [(i, r) for i, r in enumerate(self.rows) if needle.lower() in r.lower()]

    def test_a_description_over_two_lines_is_found_on_its_first(self):
        rows = po.line_rows(self.Fake(), {'description': 'Maquetación y pruebas de color'})
        self.assertEqual([i for i, _ in rows], [1])
        self.assertIn('288,00', rows[0][1])

    def test_a_description_that_is_not_there_is_not(self):
        self.assertEqual(po.line_rows(self.Fake(), {'description': 'Maquetación de portada'}), [])


if __name__ == '__main__':
    unittest.main()
