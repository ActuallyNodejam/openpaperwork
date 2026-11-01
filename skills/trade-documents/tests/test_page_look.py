"""Tests for the look of a trade page (skills/_shared/page_look.py): the tokens it reads from the library's look
file, what it writes into the page, and on a printed page where the closing block and the running line stand.
The printed tests need Chromium (the app's printer or Playwright) and pdftotext; the ones that build an invoice
need the e-invoice pack beside this one."""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'scripts'))
import trade_create as tc  # noqa: E402
sys.path.insert(0, str(HERE.parent / '_shared'))
import page_look  # noqa: E402

letter = tc.letter
INVOICE = HERE.parent / 'e-invoice'
LOOK = HERE.parent / 'business-deck' / 'look.json'
MM = 25.4 / 72


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


def words(pdf, page=1):
    """Every word of one page with its box in mm: (x0, y0, x1, y1, text)."""
    out = subprocess.run(['pdftotext', '-bbox', '-f', str(page), '-l', str(page), str(pdf), '-'], capture_output=True, text=True).stdout
    return [(float(a) * MM, float(b) * MM, float(c) * MM, float(d) * MM, t) for a, b, c, d, t in re.findall(
        r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>', out)]


def trade_pdf(s):
    folder = Path(tempfile.mkdtemp())
    (folder / 'doc.spec.json').write_text(json.dumps(s, ensure_ascii=False))
    out = folder / 'doc.pdf'
    assert tc.main([str(folder / 'doc.spec.json'), str(out)]) == 0
    return out


def invoice_pdf(order):
    """An invoice page printed by the invoice pack's own builder, without the invoice file inside it."""
    folder = Path(tempfile.mkdtemp())
    (folder / 'order.json').write_text(json.dumps(order, ensure_ascii=False))
    done = subprocess.run([sys.executable, str(INVOICE / 'page' / 'build_page.py'), 'order.json', 'invoice.pdf', '--no-facturx'],
                          cwd=folder, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr or done.stdout
    return folder / 'invoice.pdf'


def invoice(name):
    return json.loads((INVOICE / 'templates' / (name + '-spec.json')).read_text())


def look_css(html):
    """The part of a page's style sheet the look wrote."""
    css = re.search(r'<style>(.*?)</style>', html, re.S).group(1)
    return css[css.index('/* look:'):]


class TheTokens(unittest.TestCase):
    def test_the_open_default_in_the_code_is_the_look_files(self):
        """A pack that travels without the look file prints the same page: every number kept in the code is
        the file's."""
        file = json.loads(LOOK.read_text())
        for block in page_look.PAGE_BLOCKS:
            for key, value in page_look.DEFAULT[block].items():
                self.assertEqual(file[block][key], value, '%s.%s' % (block, key))
        with_file, without = page_look.load(), page_look.load(Path(tempfile.mkdtemp()) / 'none.json')
        self.assertEqual(page_look.css(with_file), page_look.css(without))
        self.assertEqual(page_look.script(with_file), page_look.script(without))

    def test_the_report_blocks_names_are_the_long_form_pages(self):
        text = json.loads(LOOK.read_text())['text']
        for key in ('measure', 'side_min', 'top', 'bottom', 'block', 'body', 'small', 'lead', 'h1', 'h2', 'h3', 'title',
                    'para_gap', 'heading_gap', 'figure_gap'):
            self.assertIn(key, text)
        self.assertGreaterEqual(text['body'][0], 11)

    def test_small_print_is_never_under_eight_and_a_half_points(self):
        self.assertGreaterEqual(page_look.load()['trade']['small'][0], 8.5)

    def test_a_company_look_restyles_the_page_and_moves_nothing(self):
        look = json.loads(LOOK.read_text())
        look['face']['name'] = 'Georgia'
        look['face']['title_weight'] = 700
        look['ink']['ink'] = '0B1F33'
        look['text']['h1'] = [26, 31]
        look['trade']['footer_columns'] = [4, 4, 4]
        file = Path(tempfile.mkdtemp()) / 'look.json'
        file.write_text(json.dumps(look))
        own, default = page_look.css(page_look.load(file)), page_look.css()
        self.assertIn('font-family:"Georgia"', own)
        self.assertIn('color:#0B1F33', own)
        self.assertRegex(own, r'h1\{font-size:26pt;line-height:31pt;letter-spacing:-0\.02em;font-weight:700')
        self.assertRegex(own, r'\.head \.name\{[^}]*font-weight:700')
        self.assertRegex(default, r'h1\{font-size:22pt;line-height:27pt;letter-spacing:-0\.02em;font-weight:400')
        self.assertIn('grid-template-columns:calc(33.333% - 3.333mm) calc(33.333% - 3.333mm) calc(33.333% - 3.333mm)', own)
        # The look sets no place: the window, the block and the margins stay the layout's.
        for css in (own, default):
            for selector in ('.field', '.address', '.info{left', '.body{', '@page'):
                self.assertNotIn(selector, css, selector)

    def test_large_type_is_tightened_and_small_print_is_not(self):
        look = page_look.load()
        self.assertIn('letter-spacing:-0.02em', page_look._type(look, look['text']['h2']))
        self.assertNotIn('letter-spacing', page_look._type(look, look['trade']['body']))
        self.assertNotIn('letter-spacing', page_look._type(look, look['trade']['small']))

    def test_the_grid(self):
        self.assertEqual(page_look._span(3, 12, 5), 'calc(25% - 3.75mm)')
        self.assertEqual(page_look._span(6, 12, 5), 'calc(50% - 2.5mm)')
        self.assertEqual(sum(page_look.load()['trade']['footer_columns']), page_look.load()['grid']['columns'])
        # The footer is as wide as the text on every layout, so it wraps on screen as it prints.
        self.assertIn('footer{width:165mm', page_look.css())
        self.assertIn('footer{width:175mm', page_look.css(layout=letter.LAYOUTS['fi']))
        self.assertIn('footer{width:165.1mm', page_look.css(layout=letter.LAYOUTS['us'], paper='Letter'))


class ThePage(unittest.TestCase):
    def pages(self):
        for path in sorted((HERE / 'templates').glob('*.spec.json')):
            s = json.loads(path.read_text())
            yield path.name, tc.page_html(s, tc.compute(s))
        if (INVOICE / 'page' / 'build_page.py').is_file():
            sys.path.insert(0, str(INVOICE / 'page'))
            import build_page
            for path in sorted((INVOICE / 'templates').glob('*-spec.json')):
                order = json.loads(path.read_text())
                order.setdefault('exchange_rate', 11.5)
                locale = build_page.page_locale_for(build_page.locale_of_order(order)[0])
                yield path.name, build_page.on_layout(build_page.paper_for(build_page.build(order, locale), locale), order)

    def test_no_page_asks_for_bold(self):
        """One weight: nothing the look writes and nothing in a page's own markup is bold."""
        seen = 0
        for name, html in self.pages():
            seen += 1
            self.assertNotRegex(look_css(html), r'font-weight:(?!400)', name)
            body = html[html.index('</style>'):]
            self.assertNotRegex(body, r'<b>|<strong>|font-weight', name)
            # What the sheet set bold, the look sets back: the sender's name, the heading, the column heads, the total.
            for selector in (r'\.head \.name', 'h1', r'\.lines th', r'\.sum \.gross td'):
                self.assertRegex(look_css(html), selector + r'\{[^}]*font-weight:400', name)
        self.assertGreaterEqual(seen, 21)

    def test_every_page_is_dressed_once_and_after_its_layout(self):
        for name, html in self.pages():
            css = re.search(r'<style>(.*?)</style>', html, re.S).group(1)
            self.assertEqual(css.count('/* look:'), 1, name)
            if '/* layout:' in css:
                self.assertLess(css.index('/* layout:'), css.index('/* look:'), name)
            self.assertEqual(html.count("document.body.classList.add('compact')"), 1, name)
            self.assertIn('<table class="lines">' if 'trade-builder' in html else "<table class='lines'>", html, name)

    def test_the_closing_block_is_rows_of_key_and_value(self):
        self.assertEqual(page_look.closing([]), '')
        self.assertEqual(page_look.closing([('IBAN', None), ('BIC', '')]), '')
        block = page_look.closing([('Payment terms', '30 days net'), ('IBAN', None), ('Bank', ['A & B Bank', None, 'Account 1'])])
        self.assertEqual(block, '<div class="close"><div class="pay"><div class="k">Payment terms</div><div class="v">30 days net</div>'
                                '<div class="k">Bank</div><div class="v">A &amp; B Bank<br>Account 1</div></div></div>')
        # A quotation closes on its terms; an order confirmation that is paid to a bank says where; a delivery
        # note closes on its delivery term and the line to sign, and never on a bank.
        quote, note = spec('quotation'), spec('delivery-note')
        self.assertEqual([k for k, _ in tc.Page(quote).term_rows() + tc.Page(quote).bank_rows()],
                         [tc.Page(quote).w['delivery_terms'], tc.Page(quote).w['payment_terms']])
        it = tc.Page(spec('order-confirmation-it'))
        self.assertEqual(it.bank_rows(), [('Banca', ['Banca di Esempio', None]), ('IBAN', 'IT60 X054 2811 1010 0000 0123 456'),
                                          ('BIC', 'ESEMITM1XXX')])
        self.assertEqual(tc.Page(dict(note, bank={'iban': 'SE00'})).bank_rows(), [])
        html = tc.page_html(note, tc.compute(note))
        self.assertRegex(html, r'<div class="close"><div class="pay">.*?</div><p class="sign"')
        # The block's keys are no <dt>: TRADE-BLOCK reads the information block's labels from those.
        self.assertNotIn('<dt>%s</dt>' % tc.Page(quote).w['payment_terms'], tc.page_html(quote, tc.compute(quote)))

    @unittest.skipUnless((INVOICE / 'page' / 'build_page.py').is_file(), 'the e-invoice pack is not beside this one')
    def test_an_invoice_closes_on_how_to_pay_it_and_a_credit_note_does_not(self):
        sys.path.insert(0, str(INVOICE / 'page'))
        import build_page
        order = invoice('it-fattura')
        html = build_page.build(order, 'it-IT')
        block = re.search(r'<div class="close">.*?</div></div>', html, re.S).group(0)
        self.assertEqual(re.findall(r'<div class="k">(.*?)</div>', block), ['Pagamento', 'Scadenza', 'IBAN', 'BIC'])
        self.assertIn('<div class="v">IT60 X054 2811 1010 0000 0123 456</div>', block)
        credit = build_page.build(invoice('uk-credit-note'), 'en-GB')
        keys = re.findall(r'<div class="k">(.*?)</div>', credit)
        self.assertNotIn('IBAN', keys)
        self.assertNotIn('Due date', keys)
        # The country's own way to pay, a key and a value each.
        uk = build_page.build(invoice('uk-vat-invoice'), 'en-GB')
        self.assertIn('<div class="k">Sort code</div>', uk)
        self.assertIn('<div class="k">Account</div>', uk)

    def test_a_running_line_for_every_page_after_the_first(self):
        html = '<html><head><title>Invoice INV-1 &amp; Co</title></head><body><footer></footer></body></html>'
        out = page_look.running(html, 3, 'A4')
        self.assertEqual(re.findall(r'<div class="run" style="top:([\d.]+)mm"><span>(.*?)</span><span>(.*?)</span></div>', out),
                         [('312', 'Invoice INV-1 &amp; Co', '2 / 3'), ('609', 'Invoice INV-1 &amp; Co', '3 / 3')])
        self.assertIn('top:294.4mm', page_look.running(html, 2, 'Letter'))
        self.assertEqual(page_look.running(html, 1, 'A4'), html)
        folder = Path(tempfile.mkdtemp())
        (folder / 'two.pdf').write_bytes(b'%PDF-1.4\n1 0 obj<</Type /Pages /Kids[2 0 R 3 0 R]>>\n2 0 obj<</Type /Page>>\n3 0 obj<</Type/Page /Parent 1 0 R>>')
        self.assertEqual(page_look.page_count(folder / 'two.pdf'), 2)
        self.assertEqual(page_look.page_count(folder / 'none.pdf'), 0)


def has_docx():
    try:
        import docx  # noqa: F401
        return True
    except ImportError:
        return False


@unittest.skipUnless(has_docx(), 'python-docx is not installed')
class TheWordFile(unittest.TestCase):
    def test_the_word_file_takes_the_looks_inks_sizes_and_one_weight(self):
        import zipfile
        folder = Path(tempfile.mkdtemp())
        (folder / 'doc.spec.json').write_text(json.dumps(spec('order-confirmation-it'), ensure_ascii=False))
        self.assertEqual(tc.main([str(folder / 'doc.spec.json'), str(folder / 'doc.docx')]), 0)
        with zipfile.ZipFile(folder / 'doc.docx') as z:
            parts = {n: z.read(n).decode('utf-8') for n in z.namelist() if re.fullmatch(r'word/(document|header\d*|footer\d*|styles)\.xml', n)}
        text = ''.join(v for n, v in parts.items() if not n.endswith('styles.xml'))
        look = page_look.load()
        self.assertNotRegex(text, r'<w:b/>|<w:b w:val="(1|true|on)"/>')                    # nothing bold
        self.assertEqual(set(re.findall(r'<w:color w:val="([0-9A-Fa-f]{6})"/>', text)), {look['ink']['second']})
        self.assertIn('<w:color w:val="%s"/>' % look['ink']['ink'], parts['word/styles.xml'])
        self.assertEqual(set(re.findall(r'w:val="single"[^>]*w:color="([0-9A-Fa-f]{6})"', text)),
                         {look['ink']['hairline'], look['ink']['rule']})
        sizes = {int(x) / 2 for x in re.findall(r'<w:sz w:val="(\d+)"/>', text)}
        for step in (look['text']['h1'][0], look['text']['h2'][0], look['text']['lead'][0], look['trade']['small'][0]):
            self.assertIn(step, sizes)
        self.assertLessEqual(max(sizes), look['text']['h1'][0])
        # The closing block: the terms and where to pay, a key and a value each, after the notes.
        body = re.sub(r'<[^>]+>', '|', parts['word/document.xml'])
        self.assertRegex(body, r'Condizioni di pagamento\|+bonifico bancario')
        self.assertRegex(body, r'IBAN\|+IT60 X054 2811 1010 0000 0123 456')
        self.assertLess(body.index('La consegna avviene'), body.index('Condizioni di consegna'))


@unittest.skipUnless(can_print(), 'no Chromium to print with')
class ThePrintedPage(unittest.TestCase):
    def foot(self, pdf, first_footer_word, layout=None, paper='A4'):
        """(where the closing block ends, where the footer starts) on page 1, in mm from the top."""
        ws = words(pdf)
        left = (layout or {}).get('left', letter.GEOMETRY['left'])
        footer_top = max(w[1] for w in ws if w[4] == first_footer_word and abs(w[0] - left) < 1.5)
        body = [w for w in ws if 100 < w[1] < footer_top - 1]
        return max(w[3] for w in body), footer_top

    @unittest.skipUnless((INVOICE / 'page' / 'build_page.py').is_file(), 'the e-invoice pack is not beside this one')
    def test_a_short_invoice_closes_at_the_foot_above_a_footer_of_any_height(self):
        """The closing block ends foot_gap above the footer, for a footer of four lines and for one of eight
        (a sole shareholder, in liquidation): the white is in the middle of the page."""
        gap = page_look.load()['trade']['foot_gap']
        plain, long = invoice('it-fattura'), invoice('it-fattura')
        long['seller']['rea'].update(sole_shareholder=True, in_liquidation=True)
        tops = []
        for order in (plain, long):
            pdf = invoice_pdf(order)
            self.assertEqual(page_look.page_count(pdf), 1)
            end, footer_top = self.foot(pdf, 'Esempio', letter.LAYOUTS['it'])
            tops.append(footer_top)
            self.assertLess(end, footer_top - gap + 1.5)            # clear of the footer
            self.assertGreater(end, footer_top - gap - 5)           # and standing on it, not after the totals
            total = max(w[3] for w in words(pdf) if w[4] == 'documento')
            self.assertGreater(end - total, 40)                     # the white is between the totals and the foot
        self.assertLess(tops[1], tops[0] - 7)                       # the longer footer starts higher, and is cleared

    @unittest.skipUnless((INVOICE / 'page' / 'build_page.py').is_file(), 'the e-invoice pack is not beside this one')
    def test_a_long_invoice_runs_on_under_a_running_line(self):
        order = invoice('uk-vat-invoice')
        order['lines'] = [dict(order['lines'][0], name='Example item %d' % i, quantity=i, unit_price=10) for i in range(1, 26)]
        pdf = invoice_pdf(order)
        self.assertEqual(page_look.page_count(pdf), 2)
        first, second = words(pdf, 1), words(pdf, 2)
        edge = letter.PAPER_MM['A4'][0] - letter.LAYOUTS['uk']['right']
        line = [w for w in second if w[1] < letter.PAGE_TOP - 4]
        self.assertEqual(' '.join(w[4] for w in sorted(line)), 'Invoice %s 2 / 2' % order['number'])
        self.assertAlmostEqual(min(w[0] for w in line), letter.LAYOUTS['uk']['left'], delta=1)
        self.assertAlmostEqual(max(w[2] for w in line), edge, delta=1)
        self.assertNotIn('/', [w[4] for w in first if w[1] < 40])                  # page 1 has the letterhead instead
        # Page 1 ends above the room its footer needs, and the closing block follows the totals on page 2.
        footer_top = max(w[1] for w in first if w[4] == 'Example' and abs(w[0] - letter.LAYOUTS['uk']['left']) < 1.5)
        rows = [w for w in first if w[4] == 'Example' and w[1] < footer_top - 1 and w[1] > 120]
        self.assertLess(max(w[3] for w in rows), footer_top - page_look.load()['trade']['foot_gap'] + 1.5)
        self.assertIn('IBAN', [w[4] for w in second])

    def test_a_page_that_misses_one_page_by_a_little_keeps_to_one(self):
        """The Canadian pro forma on Letter: ten columns, two notes, five closing rows and a footer of six
        lines stand on one page once the page gives up part of its air; nothing passes the right margin."""
        s = spec('proforma-invoice-ca')
        pdf = trade_pdf(s)
        self.assertEqual(page_look.page_count(pdf), 1)
        edge = letter.PAPER_MM['Letter'][0] - letter.LAYOUTS['ca']['right']
        self.assertLessEqual(max(w[2] for w in words(pdf)), edge + 0.5)
        end, footer_top = self.foot(pdf, 'Granite', letter.LAYOUTS['ca'])
        self.assertLess(end, footer_top - 1.5)

    def test_a_table_of_many_columns_ends_on_the_right_margin(self):
        """A quotation of eight columns with a long word in its description, and the Swedish pro forma of ten:
        the table gives way (headings on two lines, then small print) before it passes the text's right edge."""
        for name, lay in (('quotation-nl', letter.LAYOUTS['nl']), ('proforma-invoice', None)):
            pdf = trade_pdf(spec(name))
            right = (lay or letter.GEOMETRY)['right']
            edge = letter.PAPER_MM['A4'][0] - right
            ws = [w for w in words(pdf) if w[1] > 95]
            self.assertLessEqual(max(w[2] for w in ws), edge + 0.5, name)
            self.assertGreaterEqual(max(w[2] for w in ws), edge - 1.5, name)


if __name__ == '__main__':
    unittest.main()
