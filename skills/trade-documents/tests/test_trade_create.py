"""Offline tests for trade_create.py: arithmetic, delivery terms, the purchase order and the three writers."""
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'scripts'))
import trade_create as tc
CHECKS = HERE.parent / '_checks'
sys.path.insert(0, str(CHECKS))
import locale_floor  # noqa: E402
import trade_check  # noqa: E402


def spec(name):
    return json.loads((HERE / 'templates' / (name + '.spec.json')).read_text())


def rows_of(order):
    return [k for k, _ in tc.Page(order).totals(tc.compute(order))]


class Arithmetic(unittest.TestCase):
    def test_vat_once_per_rate(self):
        lines, vat, net, tax, gross = tc.compute(spec('quotation'))
        self.assertEqual([l['net'] for l in lines], [Decimal('1200.00'), Decimal('1037.40')])
        self.assertEqual(vat, [(Decimal('25'), Decimal('1200.00'), Decimal('300.00')), (Decimal('12'), Decimal('1037.40'), Decimal('124.49'))])
        self.assertEqual((net, tax, gross), (Decimal('2237.40'), Decimal('424.49'), Decimal('2661.89')))

    def test_half_up(self):
        self.assertEqual(tc.r2('2.675'), Decimal('2.68'))


class DeliveryTerm(unittest.TestCase):
    def test_written_in_full(self):
        self.assertEqual(tc.delivery_term(dict(delivery_terms=dict(rule='dap', place='Malmö, Sweden'), transport='road')), 'DAP Malmö, Sweden, Incoterms® 2020')

    def test_refuses_unknown_rule_missing_place_and_sea_rule_on_road(self):
        for terms, transport in ((dict(rule='DDU', place='Oslo'), 'road'), (dict(rule='DAP', place=''), 'road'), (dict(rule='FOB', place='Gothenburg'), 'road')):
            with self.assertRaises(ValueError):
                tc.delivery_term(dict(delivery_terms=terms, transport=transport))
        self.assertEqual(tc.delivery_term(dict(delivery_terms=dict(rule='FOB', place='Gothenburg'), transport='sea')), 'FOB Gothenburg, Incoterms® 2020')


class PurchaseOrder(unittest.TestCase):
    def test_the_buyer_writes_it_to_the_supplier(self):
        s = spec('purchase-order')
        self.assertIs(tc.sender(s), s['buyer'])
        self.assertIs(tc.recipient(s), s['seller'])
        self.assertEqual(tc.Page(s).return_line().split(' · ')[0], 'Example Customer AB')
        rows = dict(tc.Page(s).info_rows())
        self.assertEqual(rows['Your quotation'], 'Q-2026-0001')
        self.assertEqual(rows['Supplier VAT ID'], 'DE000000001')
        self.assertIn('Requested delivery date', rows)

    def test_border_and_language(self):
        s = spec('purchase-order')
        self.assertTrue(tc.crosses_border(s))
        self.assertFalse(tc.crosses_border(dict(s, seller=dict(s['seller'], country='Sweden'))))
        self.assertEqual(tc.language(dict(s, language=None))[0], 'sv-SE')
        self.assertEqual(tc.language(spec('quotation')), tc.letter.language(spec('quotation')))

    def test_no_bank_and_the_delivery_address(self):
        s = dict(spec('purchase-order'), bank=dict(iban='SE00 0000'))
        self.assertNotIn('IBAN SE00 0000', [x for col in tc.Page(s).footer() for x in col])
        no_dest = dict(s)
        no_dest.pop('deliver_to')
        self.assertIs(tc.delivery_address(no_dest), s['buyer'])
        self.assertIsNone(tc.delivery_address(dict(spec('quotation'))))


class Labels(unittest.TestCase):
    def test_every_label_in_the_documents_language(self):
        s = dict(spec('quotation'), references=[dict(label='Your enquiry', value='2026-01-12')],
                 dates=[dict(label='Valid until', value='2026-02-14'), dict(label='Lieferzeit', value='2 Wochen')])
        labels = [k for k, _ in tc.Page(s).info_rows()]
        self.assertEqual(labels[:5], ['Offertnummer', 'Datum', 'Er förfrågan', 'Giltig till', 'Leveranstid'])
        self.assertEqual(tc.Page(dict(s, language='de')).info_rows()[2][0], 'Ihre Anfrage')
        self.assertEqual(tc.Page(dict(s, references=[dict(label='Projekt', value='Lager 3')])).info_rows()[2][0], 'Projekt')

    def test_swedish_templates_are_swedish(self):
        for name in ('quotation', 'order-confirmation', 'delivery-note', 'proforma-invoice'):
            text = json.dumps(spec(name), ensure_ascii=False)
            for english in ('Your ', 'Our ', 'Valid until', 'days net', 'Example product', 'Despatch'):
                self.assertNotIn(english, text, name)


class Writers(unittest.TestCase):
    def test_every_document_in_every_format(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ('quotation', 'order-confirmation', 'delivery-note', 'proforma-invoice', 'purchase-order'):
                src = Path(d) / (name + '.json')
                src.write_text(json.dumps(spec(name)))
                for ext in ('docx', 'xlsx', 'pdf'):
                    out = Path(d) / ('%s.%s' % (name, ext))
                    self.assertEqual(tc.main([str(src), str(out)]), 0, name + ext)
                    self.assertGreater(out.stat().st_size, 1000)

    def test_workbook_formulas_carry_saved_results(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / 's.json'
            src.write_text(json.dumps(spec('quotation')))
            out = Path(d) / 'q.xlsx'
            tc.main([str(src), str(out)])
            xml = zipfile.ZipFile(out).read('xl/worksheets/sheet1.xml').decode()
            self.assertIn('<v>2661.89</v>', xml)
            self.assertNotIn('<v></v>', xml)
            self.assertNotIn('<v/>', xml)

    def test_delivery_note_has_no_prices(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / 's.json'
            s = spec('delivery-note')
            s['lines'][0]['unit_price'] = 120.0
            src.write_text(json.dumps(s))
            out = Path(d) / 'dn.xlsx'
            tc.main([str(src), str(out)])
            with zipfile.ZipFile(out) as z:
                xml = ''.join(z.read(n).decode('utf-8', 'replace') for n in z.namelist() if n.endswith('.xml'))
            self.assertNotIn('Unit price', xml)
            self.assertNotIn('>120<', xml)

    def test_bad_spec(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / 's.json'
            src.write_text(json.dumps(dict(type='memo')))
            self.assertEqual(tc.main([str(src), str(Path(d) / 'x.docx')]), 1)


NEW_LOCALES = {'quotation-nb': 'nb-NO', 'delivery-note-nb': 'nb-NO', 'order-confirmation-fi': 'fi-FI',
               'purchase-order-fi': 'fi-FI', 'quotation-us': 'en-US', 'proforma-invoice-ca': 'en-CA',
               'order-confirmation-fr-ca': 'fr-CA', 'quotation-au': 'en-AU'}


class Markets(unittest.TestCase):
    """The Nordic and English-speaking templates: their language, their paper and the pack check's language rule."""

    def test_language_and_paper(self):
        for name, locale in NEW_LOCALES.items():
            self.assertEqual(tc.language(spec(name))[0], locale, name)
            self.assertEqual(tc.Page(spec(name)).paper, 'Letter' if locale in ('en-US', 'en-CA', 'fr-CA') else 'A4', name)
        self.assertEqual(tc.language(dict(spec('quotation-us'), language='en'))[0], 'en-US')
        self.assertEqual(tc.language(dict(spec('quotation-nb'), language=None))[0], 'nb-NO')

    def test_each_market_names_its_tax(self):
        rows = lambda name: ' | '.join(k for k, _ in tc.Page(spec(name)).totals(tc.compute(spec(name))))  # noqa: E731
        # One rate: its own row names the tax (the total of it would only repeat the amount).
        self.assertIn('Sales tax 7%', rows('quotation-us'))
        self.assertIn('GST 10%', rows('quotation-au'))
        self.assertIn('MVA 25 %', rows('quotation-nb'))
        self.assertIn('ALV 25,5 %', rows('order-confirmation-fi'))
        self.assertIn('TPS/TVH 15 %', rows('order-confirmation-fr-ca'))
        # More than one rate: the total row names it too.
        two = dict(spec('quotation-us'))
        two['lines'] = [dict(two['lines'][0], vat_rate=7), dict(two['lines'][0], vat_rate=4)]
        self.assertIn('Total sales tax', rows_of(two))
        quebec = dict(spec('order-confirmation-fr-ca'), tax_name='TVQ')
        self.assertTrue(any('TVQ' in k for k, _ in tc.Page(quebec).totals(tc.compute(quebec))))

    def test_every_template_passes_the_pack_check(self):
        for name in NEW_LOCALES:
            for ext in ('docx', 'xlsx', 'pdf'):
                with self.subTest(template=name, kind=ext), tempfile.TemporaryDirectory() as d:
                    src = Path(d) / (name + '.spec.json')
                    src.write_text(json.dumps(spec(name), ensure_ascii=False))
                    out = Path(d) / ('%s.%s' % (name, ext))
                    self.assertEqual(tc.main([str(src), str(out)]), 0)
                    r = subprocess.run([sys.executable, str(CHECKS / 'packcheck.py'), 'trade-documents', str(out)],
                                       capture_output=True, text=True)
                    self.assertEqual(r.returncode, 0, r.stdout)

    def test_the_check_catches_a_mixed_language_and_the_wrong_paper(self):
        with tempfile.TemporaryDirectory() as d:
            s = dict(spec('quotation-nb'), references=[dict(label='Delivery terms', value='DAP Tromsø')])
            (Path(d) / 's.spec.json').write_text(json.dumps(s, ensure_ascii=False))
            out = Path(d) / 'q.docx'
            tc.main([str(Path(d) / 's.spec.json'), str(out)])
            ok, why = trade_check.check('TRADE-LANG', out, {'locale': 'nb-NO'}, 'first')
            self.assertIs(ok, False, why)
            self.assertIn('Delivery terms', why)
        with tempfile.TemporaryDirectory() as d:
            s = dict(spec('quotation-us'), references=[dict(label='VAT number', value='none')])
            (Path(d) / 's.spec.json').write_text(json.dumps(s))
            out = Path(d) / 'q.docx'
            tc.main([str(Path(d) / 's.spec.json'), str(out)])
            self.assertIs(trade_check.check('TRADE-LANG', out, {'locale': 'en-US'}, 'first')[0], False)
            from docx import Document
            from docx.shared import Mm
            doc = Document(out)
            doc.sections[0].page_width, doc.sections[0].page_height = Mm(210), Mm(297)
            doc.save(out)
            self.assertIs(locale_floor.check('LOCALE-PAPER', out, {'locale': 'en-US'}, 'first')[0], False)

    def test_letter_workbook_prints_on_letter(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / 's.json'
            src.write_text(json.dumps(spec('quotation-us')))
            out = Path(d) / 'q.xlsx'
            tc.main([str(src), str(out)])
            self.assertIn('paperSize="1"', zipfile.ZipFile(out).read('xl/worksheets/sheet1.xml').decode())



WAVE8 = {'quotation-nl': 'nl-NL', 'order-confirmation-be-nl': 'nl-BE', 'delivery-note-be-fr': 'fr-BE',
         'purchase-order-at': 'de-AT', 'proforma-invoice-ie': 'en-IE'}


class Wave8(unittest.TestCase):
    """Belgium, the Netherlands, Austria and Ireland: language, company lines and the pack check."""

    def test_language_and_belgian_region(self):
        for name, locale in WAVE8.items():
            self.assertEqual(tc.language(spec(name))[0], locale, name)
            self.assertEqual(tc.Page(spec(name)).paper, 'A4', name)
        ghent = dict(spec('order-confirmation-be-nl'), language=None)
        self.assertEqual(tc.language(ghent)[0], 'nl-BE')
        liege = dict(spec('delivery-note-be-fr'), language=None)
        self.assertEqual(tc.language(liege)[0], 'fr-BE')
        self.assertEqual(tc.language(dict(liege, language='nl'))[0], 'nl-BE')
        self.assertEqual(tc.language(dict(spec('purchase-order-at'), language='de'))[0], 'de-AT')
        self.assertEqual(tc.language(dict(spec('proforma-invoice-ie'), language='en'))[0], 'en-IE')

    def test_company_lines(self):
        foot = lambda name: [x for col in tc.Page(spec(name)).footer() for x in col]  # noqa: E731
        self.assertIn('KvK-nummer 12345678', foot('quotation-nl'))
        be = foot('order-confirmation-be-nl')
        self.assertEqual(be[be.index('Ondernemingsnummer 0712.345.678') + 1], 'RPR Gent, afdeling Gent')
        self.assertIn("Numéro d'entreprise 0798.765.432", foot('delivery-note-be-fr'))
        # French sets a no-break space before the colon, in the footer as in the rest of a French letter.
        self.assertIn('Siège\u00a0: Quai de la Batte 14, 4000 Liège', foot('delivery-note-be-fr'))
        self.assertIn('RPM Liège, division Liège', foot('delivery-note-be-fr'))
        self.assertIn('FN 412345 k', foot('purchase-order-at'))
        self.assertIn('Landesgericht Linz', foot('purchase-order-at'))
        self.assertIn('Registered in Ireland', foot('proforma-invoice-ie'))
        # A registered office long enough to wrap in the footer's middle column; the pack check still finds it.
        self.assertIn('Registered office: Unit 4, Ballymount Business Park, Dublin 24', foot('proforma-invoice-ie'))
        self.assertIn('Directors: Aoife Brennan, Tomasz Nowak (Polish)', foot('proforma-invoice-ie'))
        self.assertIn('UID-Nr. ATU12345678', foot('purchase-order-at'))

    def test_what_each_country_asks_of_a_company(self):
        missing = tc.letter.company_missing
        ie = dict(spec('proforma-invoice-ie')['seller'])
        ie.pop('managing_directors')
        self.assertTrue(any(m.startswith('managing_directors') for m in missing(ie)))
        be = dict(spec('order-confirmation-be-nl')['seller'], register='Gent')
        self.assertTrue(any(m.startswith('register') for m in missing(be)))
        self.assertEqual(missing(spec('purchase-order-at')['buyer']), [])        # no managing directors in Austria
        self.assertIn('managing_directors', missing(dict(spec('purchase-order-at')['buyer'], country='DE')))

    def test_the_warning_names_the_country_law_and_never_a_number(self):
        # Belgium: the enterprise number missing. The warning names art. 2:20; nothing is made up for the page.
        be = spec('order-confirmation-be-nl')
        be['seller'].pop('register_number')
        why = tc.company_warning(be)
        self.assertIn('register_number', why)
        self.assertIn('art. 2:20', why)
        self.assertFalse(any('Ondernemingsnummer' in x for col in tc.Page(be).footer() for x in col))
        nl = spec('quotation-nl')
        nl['seller'].pop('register_number')
        self.assertIn('Handelsregisterwet 2007 art. 27', tc.company_warning(nl))
        at = spec('purchase-order-at')
        at['buyer'].pop('register')
        self.assertIn('Unternehmensgesetzbuch § 14', tc.company_warning(at))
        self.assertIn('the buyer is a company', tc.company_warning(at))
        # Ireland: an order form or a quotation falls under s.151(2); the directors belong to s.151(1), letters.
        ie = spec('proforma-invoice-ie')
        ie['seller'].pop('managing_directors')
        self.assertIsNone(tc.company_warning(ie))
        ie['seller'].pop('registered_office')
        self.assertIn('Companies Act 2014 s.151(2)', tc.company_warning(ie))
        for name in WAVE8:
            self.assertIsNone(tc.company_warning(spec(name)), name)

    def test_layout_keeps_codes_whole_and_the_signature_on_one_row(self):
        page = tc.Page(spec('delivery-note-be-fr'))
        line = page.sign_line(88)
        self.assertLessEqual(len(line), 96)
        self.assertRegex(line, r'signature\) : _{12,} +Date : _{8,}$')
        self.assertLessEqual(len(tc.Page(spec('delivery-note')).sign_line(88)), 96)
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / 'q.spec.json'
            src.write_text(json.dumps(spec('quotation-nl'), ensure_ascii=False))
            tc.main([str(src), str(Path(d) / 'q.pdf')])
            html = (Path(d) / 'q.html').read_text()
            self.assertIn('<td style="white-space:nowrap">PL-640</td>', html)
            # Excel: a delivery address longer than the columns runs onto a second row, not off the page
            s = spec('delivery-note-be-fr')
            src.write_text(json.dumps(s, ensure_ascii=False))
            out = Path(d) / 'd.xlsx'
            tc.main([str(src), str(out)])
            from openpyxl import load_workbook
            ws = load_workbook(out).active
            cells = [str(c.value) for row in ws.iter_rows(min_col=1, max_col=1) for c in row if c.value]
            start = next(i for i, v in enumerate(cells) if v.startswith('Adresse de livraison'))
            self.assertTrue(cells[start + 1].endswith('Belgique'), cells[start:start + 2])
            self.assertEqual(trade_check.check('TRADE-LANG', out, {'locale': 'fr-BE'}, 'first')[0], True)

    def test_every_template_passes_the_pack_check(self):
        for name in WAVE8:
            for ext in ('docx', 'xlsx', 'pdf'):
                with self.subTest(template=name, kind=ext), tempfile.TemporaryDirectory() as d:
                    src = Path(d) / (name + '.spec.json')
                    src.write_text(json.dumps(spec(name), ensure_ascii=False))
                    out = Path(d) / ('%s.%s' % (name, ext))
                    self.assertEqual(tc.main([str(src), str(out)]), 0)
                    r = subprocess.run([sys.executable, str(CHECKS / 'packcheck.py'), 'trade-documents', str(out)],
                                       capture_output=True, text=True)
                    self.assertEqual(r.returncode, 0, r.stdout)

    def test_austrian_uid_and_dutch_against_belgian(self):
        with tempfile.TemporaryDirectory() as d:
            s = dict(spec('purchase-order-at'), references=[dict(label='USt-IdNr.', value='DE000000001')])
            (Path(d) / 's.spec.json').write_text(json.dumps(s, ensure_ascii=False))
            out = Path(d) / 'b.docx'
            tc.main([str(Path(d) / 's.spec.json'), str(out)])
            ok, why = trade_check.check('TRADE-LANG', out, {'locale': 'de-AT'}, 'first')
            self.assertIs(ok, False, why)
        with tempfile.TemporaryDirectory() as d:
            s = dict(spec('order-confirmation-be-nl'), references=[dict(label='Pakbonnummer', value='PB-1')])
            (Path(d) / 's.spec.json').write_text(json.dumps(s, ensure_ascii=False))
            out = Path(d) / 'o.pdf'
            tc.main([str(Path(d) / 's.spec.json'), str(out)])
            self.assertIs(trade_check.check('TRADE-LANG', out, {'locale': 'nl-BE'}, 'first')[0], False)


if __name__ == '__main__':
    unittest.main()
