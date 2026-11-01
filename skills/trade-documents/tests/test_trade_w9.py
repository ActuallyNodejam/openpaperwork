"""Offline tests for wave 9 of the trade documents: Spain, Italy and Poland (language, company details, the pack
check), and the two rules every trade document now shares with the invoice page: the address as the recipient's
post office reads it, and the information block ending on the text's right edge with one line per label.
The tests that measure a printed page need Chromium (the app's printer or Playwright) and pdftotext."""
import copy
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'scripts'))
import trade_create as tc  # noqa: E402
CHECKS = HERE.parent / '_checks'
sys.path.insert(0, str(CHECKS))
import packcheck  # noqa: E402
import purchase_order_check as po  # noqa: E402
import trade_check  # noqa: E402

WAVE9 = {'quotation-es': 'es-ES', 'order-confirmation-it': 'it-IT', 'purchase-order-pl': 'pl-PL'}
TEMPLATES = sorted(p.name[:-len('.spec.json')] for p in (HERE / 'templates').glob('*.spec.json'))


def spec(name):
    return json.loads((HERE / 'templates' / (name + '.spec.json')).read_text())


def can_print():
    if not shutil.which('pdftotext'):
        return False
    if shutil.which('nodejam-print'):
        return True
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


def built(s, ext, edit=None):
    """A document built in a folder of its own, its spec beside it: the path of the file."""
    folder = Path(tempfile.mkdtemp())
    src = folder / 'doc.spec.json'
    src.write_text(json.dumps(s, ensure_ascii=False))
    out = folder / ('doc.' + ext)
    assert tc.main([str(src), str(out)]) == 0
    if edit:
        page = out.with_suffix('.html')
        page.write_text(edit(page.read_text()))
        tc.letter.print_pdf(page, out, paper=tc.Page(s).paper)
    return out


def foot(s):
    return [x for col in tc.Page(s).footer() for x in col]


class Wave9(unittest.TestCase):
    """Spain, Italy and Poland: the language, each market's tax and what each company law asks on the page."""

    def test_language_and_paper(self):
        for name, locale in WAVE9.items():
            self.assertEqual(tc.language(spec(name))[0], locale, name)
            self.assertEqual(tc.language(dict(spec(name), language=None))[0], locale, name)   # from the country
            self.assertEqual(tc.Page(spec(name)).paper, 'A4', name)
        self.assertEqual(tc.Page(spec('quotation-es')).title(), 'Presupuesto')
        self.assertEqual(tc.Page(spec('order-confirmation-it')).title(), "Conferma d'ordine")
        self.assertEqual(tc.Page(spec('purchase-order-pl')).title(), 'Zamówienie')

    def test_each_market_names_its_tax_and_writes_its_numbers(self):
        rows = lambda name: dict(tc.Page(spec(name)).totals(tc.compute(spec(name))))  # noqa: E731
        self.assertEqual(rows('quotation-es')['Total IVA incluido'], '4.214,43 EUR')
        self.assertEqual(rows('order-confirmation-it')['Totale IVA inclusa'], '6.913,74 EUR')
        self.assertEqual(rows('purchase-order-pl')['Razem brutto'].replace(' ', ' '), '39 062,83 PLN')
        info = dict(tc.Page(spec('purchase-order-pl')).info_rows())
        self.assertEqual(info['Data wystawienia'], '20.10.2026')
        self.assertEqual(info['Państwa oferta'], 'OF-2026-0398')
        self.assertEqual(dict(tc.Page(spec('quotation-es')).info_rows())['Válido hasta'], '13/11/2026')
        # a label written in English prints in the document's language
        self.assertEqual(tc.Page(spec('order-confirmation-it')).label('Valid until'), 'Valido fino al')
        self.assertEqual(tc.Page(spec('purchase-order-pl')).label('Our reference'), 'Nasz znak')

    def test_company_lines_as_each_country_writes_them(self):
        es = foot(spec('quotation-es'))
        self.assertIn('NIF-IVA ESB12345674', es)
        self.assertIn('Domicilio social: Calle del Ejemplo 12, 28001 Madrid', es)
        self.assertIn('Registro Mercantil de Madrid, tomo 12345, folio 67, hoja M-123456', es)
        it = foot(spec('order-confirmation-it'))
        self.assertIn('Sede legale: Via Esempio 21, 40121 Bologna', it)
        self.assertIn('Registro delle Imprese di Bologna n. 12345678903', it)
        self.assertIn('Capitale sociale: 50.000,00 € i.v.', it)
        pl = foot(spec('purchase-order-pl'))                 # the buyer's letter: its own details in the footer
        self.assertIn('NIP PL1234563218', pl)
        self.assertIn('KRS 0000123456', pl)
        self.assertEqual(pl[pl.index('KRS 0000123456') + 1],
                         'Sąd Rejonowy Poznań – Nowe Miasto i Wilda w Poznaniu, VIII Wydział Gospodarczy KRS')
        self.assertIn('Kapitał zakładowy: 50 000,00 zł', pl)
        sole = spec('order-confirmation-it')
        sole['seller']['sole_shareholder'] = True
        self.assertIn('Società con unico socio', foot(sole))

    def test_the_warning_names_the_country_law_and_never_a_number(self):
        for name in WAVE9:
            self.assertIsNone(tc.company_warning(spec(name)), name)
        es = spec('quotation-es')
        es['seller'].pop('register_number')
        why = tc.company_warning(es)
        self.assertIn('register_number', why)
        self.assertIn('Código de Comercio art. 24', why)
        self.assertIn('Directive (EU) 2017/1132 Art. 26', why)
        self.assertFalse(any('tomo' in x or 'hoja' in x for x in foot(es)))          # nothing made up for the page
        capital = spec('quotation-es')
        capital['seller']['share_capital'] = '60.000 €'                              # named without the paid-up capital
        self.assertIn('paid_up_capital', tc.company_warning(capital))
        it = spec('order-confirmation-it')
        it['seller'].pop('share_capital')
        why = tc.company_warning(it)
        self.assertIn('share_capital', why)
        self.assertIn('Codice civile art. 2250', why)
        pl = spec('purchase-order-pl')
        pl['buyer'].pop('register')
        why = tc.company_warning(pl)
        self.assertIn('the buyer is a company', why)
        self.assertIn('Kodeks spółek handlowych art. 206 § 1', why)
        # a spółka akcyjna reads art. 374 § 1, which adds the paid-up capital
        sa = dict(spec('purchase-order-pl'), type='quotation', number='OF-2026-0398')
        sa['seller'] = dict(sa['seller'], registered_office='ul. Wzorcowa 3, 30-001 Kraków', register_number='0000654321',
                            register='Sąd Rejonowy dla Krakowa-Śródmieścia w Krakowie, XI Wydział Gospodarczy KRS',
                            share_capital='1 000 000,00 zł')
        why = tc.company_warning(sa)
        self.assertIn('art. 374 § 1', why)
        self.assertIn('paid_up_capital', why)
        self.assertNotIn('art. 206', why)

    def test_every_starter_passes_the_pack_check_in_every_format(self):
        for name, locale in WAVE9.items():
            for ext in ('docx', 'xlsx', 'pdf'):
                with self.subTest(template=name, kind=ext):
                    out = built(spec(name), ext)
                    r = subprocess.run([sys.executable, str(CHECKS / 'packcheck.py'), 'trade-documents', str(out)],
                                       capture_output=True, text=True, cwd=out.parent)
                    self.assertEqual(r.returncode, 0, r.stdout)
                    self.assertIs(trade_check.check('TRADE-LANG', out, {'locale': locale}, 'first')[0], True)

    def test_the_check_catches_a_label_in_another_language(self):
        for name, locale, label in (('quotation-es', 'es-ES', 'Delivery terms'), ('order-confirmation-it', 'it-IT', 'Condiciones de pago'),
                                    ('purchase-order-pl', 'pl-PL', 'Numero ordine')):
            s = dict(spec(name), references=[dict(label=label, value='X-1')])
            ok, why = trade_check.check('TRADE-LANG', built(s, 'docx'), {'locale': locale}, 'first')
            self.assertIs(ok, False, why)
            self.assertIn(label, why)

    def test_a_purchase_order_is_read_in_spanish_italian_polish_and_dutch(self):
        self.assertIn('5.03.2026', po.date_forms('2026-03-05'))            # Polish: day without a leading zero
        self.assertIn(4000, po.numbers('4.000 ud.'))                       # a point that groups the thousands
        self.assertIn(4, po.numbers('4.000 ud.'))
        for lang in ('pl', 'es', 'it', 'nl'):
            s = dict(spec('purchase-order-pl'), language=lang)
            out = built(s, 'docx')
            for rule in ('TRADE-PO-HEAD', 'TRADE-PO-DELIVERY', 'TRADE-PO-QUOTE', 'TRADE-PO-LINES', 'TRADE-PO-TOTAL'):
                ok, why = po.check(rule, out, {}, 'first')
                self.assertIs(ok, True, '%s %s: %s' % (lang, rule, why))

    def test_the_pack_check_runs_the_block_rule(self):
        self.assertIn('TRADE-BLOCK', packcheck.SKILL_RULES['trade-documents'])


class Addresses(unittest.TestCase):
    """The address field as the letter and the invoice to the same recipient write it (letter.postal_lines)."""

    def test_every_starter_writes_the_recipient_through_postal_lines(self):
        for name in TEMPLATES:
            s = spec(name)
            page = tc.Page(s)
            self.assertEqual(page.address(), tc.letter.postal_lines(tc.recipient(s), tc.sender(s).get('country')), name)
            self.assertEqual(page.address()[0], tc.recipient(s)['name'], name)

    def test_each_post_office_reads_its_own_form(self):
        last = lambda name, n=1: tc.Page(spec(name)).address()[-n:]  # noqa: E731
        self.assertEqual(last('order-confirmation-be-nl'), ['2030 ANTWERPEN'])              # bpost
        self.assertEqual(last('quotation-nl'), ['3818 LE  AMERSFOORT'])                     # PostNL
        self.assertEqual(last('quotation-us'), ['COUNCIL BLUFFS IA  51501'])                # USPS Publication 28
        self.assertEqual(last('quotation-es', 2), ['08001 BARCELONA', 'BARCELONA'])         # Correos: the province below
        self.assertEqual(last('order-confirmation-it', 2), ['CORSO CAMPIONE 9', '10121 TORINO TO'])   # Poste Italiane
        self.assertEqual(last('purchase-order-pl'), ['30-001 KRAKÓW'])                      # Poczta Polska
        # abroad: the country last and in capitals, where the old page wrote it as the spec did
        self.assertEqual(last('proforma-invoice-ie', 3), ['MANCHESTER', 'M17 1AA', 'UNITED KINGDOM'])
        self.assertEqual(last('purchase-order', 2), ['20095 Hamburg', 'GERMANY'])
        self.assertEqual(last('proforma-invoice'), ['NORWAY'])
        # at home: no country line
        self.assertNotIn('España', tc.Page(spec('quotation-es')).address())
        self.assertNotIn('Nederland', tc.Page(spec('quotation-nl')).address())

    def test_the_three_writers_carry_the_same_address(self):
        s = spec('proforma-invoice-ie')
        lines = tc.Page(s).address()
        html = built(s, 'pdf').with_suffix('.html').read_text()
        self.assertIn('<div class="address">%s</div>' % '<br>'.join(lines), html)
        with zipfile.ZipFile(built(s, 'docx')) as z:
            xml = z.read('word/document.xml').decode()
        cells = re.findall(r'<w:t[^>]*>([^<]*)</w:t>', xml)
        start = cells.index(lines[0])
        self.assertEqual(cells[start:start + len(lines)], lines)
        from openpyxl import load_workbook
        ws = load_workbook(built(s, 'xlsx')).active
        column = [str(c.value) for row in ws.iter_rows(min_col=1, max_col=1) for c in row if c.value]
        start = column.index(lines[0])
        self.assertEqual(column[start:start + len(lines)], lines)

    def test_the_return_line_and_the_footer_put_a_british_or_irish_postcode_after_the_town(self):
        self.assertEqual(tc.place_line({'city': 'Manchester', 'postcode': 'M17 1AA', 'country': 'United Kingdom'}),
                         'Manchester M17 1AA')
        self.assertTrue(tc.Page(spec('proforma-invoice-ie')).return_line().endswith('Dublin 24 D24 X2Y3'))
        self.assertEqual(tc.place_line({'city': 'Madrid', 'postcode': '28001', 'country': 'España'}), '28001 Madrid')


class InformationBlock(unittest.TestCase):
    """The block ends on the text's right edge, where the table ends, and no label wraps."""

    def test_the_block_is_as_wide_as_the_text_allows(self):
        self.assertEqual(tc.info_mm('A4'), 65)            # 125 mm to 190 mm
        self.assertEqual(tc.info_mm('Letter'), 70.9)      # 125 mm to 195.9 mm
        css = tc.info_css('A4')
        self.assertIn('.info{width:65mm}', css)
        self.assertIn('.info{display:grid;grid-template-columns:max-content minmax(0,1fr)', css)
        self.assertIn('.info dt{width:auto;white-space:nowrap}', css)
        self.assertIn('.info dd{min-width:0;overflow-wrap:anywhere}', css)

    def test_every_page_carries_the_rule(self):
        grid = '.info{display:grid;grid-template-columns:max-content minmax(0,1fr)'
        for name in ('quotation', 'proforma-invoice', 'purchase-order'):     # DIN 5008 Form B: 125 mm to the right edge
            s = spec(name)
            html = tc.page_html(s, tc.compute(s))
            self.assertIn('.info{width:%smm}' % tc.info_mm(tc.Page(s).paper), html, name)
            self.assertIn(grid, html, name)
            self.assertNotIn('<style>.info dt{width:', html, name)           # the old fixed label column is gone
        for name in ('quotation-es', 'quotation-us', 'delivery-note-be-fr'):  # a country layout: the width that layout gives
            s = spec(name)
            html = tc.page_html(s, tc.compute(s))
            self.assertIn('width:%smm}' % tc.info_mm(tc.Page(s).paper, tc.Page(s).lay), html, name)
            self.assertIn(grid, html, name)

    def test_word_ends_the_block_on_the_right_margin_with_a_label_column_no_label_outgrows(self):
        for name in TEMPLATES:
            s = spec(name)
            page = tc.Page(s)
            rows = page.info_rows()
            label = tc.label_mm(rows, 33.0, page.paper, page.lay)
            self.assertGreaterEqual(label, max(tc.text_mm(k, 8.5) for k, _ in rows), name)
            self.assertLessEqual(label, tc.info_mm(page.paper, page.lay) - 15, name)
        s = spec('purchase-order')                                           # a Swedish buyer: DIN 5008 Form B
        with zipfile.ZipFile(built(s, 'docx')) as z:
            xml = z.read('word/document.xml').decode()
        grid = [int(x) / 56.7 for x in re.findall(r'<w:gridCol w:w="(\d+)"/>', xml.split('</w:tblGrid>')[0])]
        self.assertEqual(len(grid), 3)
        self.assertAlmostEqual(sum(grid), 210 - 25 - 20, delta=0.6)          # the text's width: the block ends at 190 mm
        self.assertAlmostEqual(grid[2], 65, delta=0.3)

    @unittest.skipUnless(can_print(), 'no Chromium or pdftotext to measure a printed page with')
    def test_every_starter_keeps_its_block_inside_the_right_edge(self):
        for name in TEMPLATES:
            with self.subTest(template=name):
                out = built(spec(name), 'pdf')
                self.assertEqual(trade_check.block_problems(out, tc.Page(spec(name)).lay), [], name)
                ok, why = trade_check.check('TRADE-BLOCK', out, {}, 'first')
                self.assertIs(ok, True, why)

    @unittest.skipUnless(can_print(), 'no Chromium or pdftotext to measure a printed page with')
    def test_a_long_value_wraps_in_its_own_column(self):
        s = copy.deepcopy(spec('order-confirmation-it'))
        s['references'].append({'label': 'Nostro riferimento', 'value': 'Ufficio commerciale Italia settentrionale, signora Fontana'})
        out = built(s, 'pdf')
        self.assertEqual(trade_check.block_problems(out, tc.Page(s).lay), [])

    @unittest.skipUnless(can_print(), 'no Chromium or pdftotext to measure a printed page with')
    def test_the_rule_catches_the_old_block_and_a_wrapped_label(self):
        s = copy.deepcopy(spec('quotation'))                                 # a Swedish seller: DIN 5008 Form B
        s['references'].append({'label': 'Vår referens', 'value': 'forsaljning.region.norr.kundtjanst@example-wholesale.example'})
        # The page as it was before: a 75 mm block with values that cannot wrap, 10 mm past the text.
        old = ('.info{display:block;width:75mm}.info div{display:flex;gap:3mm}.info dt{width:34mm;flex:none}'
               '.info dd{min-width:auto;overflow-wrap:normal;white-space:nowrap}')
        out = built(s, 'pdf', edit=lambda h: h.replace('</style>', old + '</style>', 1).replace('<wbr>', ''))
        ok, why = trade_check.check('TRADE-BLOCK', out, {}, 'first')
        self.assertIs(ok, False, why)
        self.assertIn("the text's right edge", why)
        # A label column too narrow for its longest label: the label wraps, and the rule names it.
        narrow = '.info{grid-template-columns:18mm minmax(0,1fr)}.info dt{white-space:normal}'
        out = built(spec('purchase-order-pl'), 'pdf', edit=lambda h: h.replace('</style>', narrow + '</style>', 1))
        ok, why = trade_check.check('TRADE-BLOCK', out, {}, 'first')
        self.assertIs(ok, False, why)
        self.assertIn('wraps', why)
        # Word and Excel are not measured
        self.assertIsNone(trade_check.check('TRADE-BLOCK', built(spec('quotation-es'), 'docx'), {}, 'first')[0])


if __name__ == '__main__':
    unittest.main()
