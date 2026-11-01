"""Offline tests for trade documents on the letter layout of the country they are sent from: the same sheet the
sender's invoice and letter sit on (skills/_shared/letter.py), in PDF, Word and Excel, and the rule that measures
it (TRADE-WINDOW). The tests that measure a printed page need Chromium (the app's printer or Playwright) and
pdftotext; the ones that set a page beside an invoice page need the e-invoice pack beside this one."""
import copy
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
CHECKS = HERE.parent / '_checks'
sys.path.insert(0, str(CHECKS))
import einvoice_page  # noqa: E402
import letter_check  # noqa: E402
import packcheck  # noqa: E402
import trade_check  # noqa: E402

letter = tc.letter
INVOICE = HERE.parent / 'e-invoice'
TEMPLATES = sorted(p.name[:-len('.spec.json')] for p in (HERE / 'templates').glob('*.spec.json'))
# The seventeen countries by where their letter puts the address; Germany, Sweden and France keep DIN 5008 Form B.
LEFT = ('GB', 'AU', 'NO', 'DK', 'FI', 'NL', 'AT', 'IE')
RIGHT = ('BE', 'ES', 'IT', 'PL')
LETTER = ('US', 'CA')
FORM_B = ('DE', 'SE', 'FR')


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


def sent_from(code):
    """The Swedish quotation starter as a company in another country would send it, written in English."""
    s = spec('quotation')
    s['language'] = 'en'
    s['seller'] = dict(s['seller'], country=code)
    return s


def rule(html, selector):
    """The declarations a page's own style sheet ends up giving a selector, later rules over earlier ones."""
    css = re.search(r'<style>(.*?)</style>', html, re.S).group(1)
    out = {}
    for body in re.findall(r'(?<![\w.#-])%s\{([^}]*)\}' % re.escape(selector), css):
        for part in body.split(';'):
            if ':' in part:
                k, v = part.split(':', 1)
                out[k.strip()] = v.strip()
    return out


def mm(value):
    return float(str(value).replace('mm', '') or 0)


def address_box(html):
    """(x, y, width) in mm of the address on a page built on the shared letter sheet: where its first line
    starts and how wide it may run."""
    field, ret = rule(html, '.field'), rule(html, '.return')
    pad = mm(field.get('padding-left', 0))
    above = 0 if ret.get('display') == 'none' else mm(ret['height'])
    return round(mm(field['left']) + pad, 2), round(mm(field['top']) + above, 2), round(mm(field['width']) - pad, 2)


class WhichLayout(unittest.TestCase):
    """The layout is the sender's country's, asked for the way the invoice page asks for it."""

    def test_every_starter_asks_the_shared_letter_as_an_invoice_does(self):
        for name in TEMPLATES:
            s = spec(name)
            want = letter.letter_layout({'sender': tc.sender(s), 'layout': s.get('layout')})
            self.assertEqual(tc.layout_of(s), want, name)
            self.assertEqual(tc.Page(s).lay, want[1], name)
            code = tc.country(tc.sender(s).get('country'))
            self.assertEqual(want[0], letter.COUNTRY_LAYOUT.get(code, 'din5008-b'), name)

    def test_the_seventeen_countries_in_three_groups(self):
        for code in LEFT + RIGHT + LETTER:
            page = tc.Page(sent_from(code))
            self.assertIs(page.lay, letter.LAYOUTS[letter.COUNTRY_LAYOUT[code]], code)
            self.assertEqual(page.paper, page.lay['paper'], code)
            self.assertEqual(page.how, 'left' if code in RIGHT else 'above' if code in LETTER else 'beside', code)
        for code in FORM_B:
            page = tc.Page(sent_from(code))
            self.assertIsNone(page.lay, code)
            self.assertEqual(page.layout_name(), 'DIN 5008:2020 Form B')
        self.assertEqual(len(LEFT + RIGHT + LETTER + FORM_B), 17)

    def test_a_purchase_order_sits_on_the_buyers_layout(self):
        self.assertEqual(tc.layout_of(spec('purchase-order-pl'))[0], 'pl')
        self.assertEqual(tc.layout_of(spec('purchase-order-at'))[0], 'at')
        self.assertEqual(tc.layout_of(spec('purchase-order-fi'))[0], 'fi')
        self.assertIsNone(tc.layout_of(spec('purchase-order'))[1])          # a Swedish buyer, whatever the supplier's country
        turned = dict(spec('purchase-order'), buyer=spec('quotation-es')['seller'])
        self.assertEqual(tc.layout_of(turned)[0], 'es')

    def test_a_layout_by_name_and_a_layout_on_the_other_paper(self):
        s = spec('quotation-es')
        self.assertIsNone(tc.Page(dict(s, layout='din5008')).lay)           # the spec asks for Form B
        self.assertEqual(tc.Page(dict(spec('quotation'), layout='uk')).lid, 'uk')
        # A US seller writing Swedish prints on A4: the No. 10 layout belongs to Letter, so the page keeps Form B.
        us = dict(spec('quotation-us'), language='sv')
        self.assertEqual(tc.Page(us).paper, 'A4')
        self.assertIsNone(tc.Page(us).lay)
        gb = dict(sent_from('GB'), language='en-US')                         # and a British one writing en-US on Letter
        self.assertEqual(tc.Page(gb).paper, 'Letter')
        self.assertIsNone(tc.Page(gb).lay)

    def test_the_summary_names_the_layout(self):
        import contextlib
        import io
        for name, want in (('quotation-es', 'Spain: A4, window on the right'), ('quotation', 'DIN 5008:2020 Form B')):
            folder = Path(tempfile.mkdtemp())
            (folder / 'doc.spec.json').write_text(json.dumps(spec(name), ensure_ascii=False))
            seen = io.StringIO()
            with contextlib.redirect_stdout(seen):
                self.assertEqual(tc.main([str(folder / 'doc.spec.json'), str(folder / 'doc.docx')]), 0)
            self.assertTrue(json.loads(seen.getvalue())['layout'].startswith(want), name)


def as_trade(party, recipient=False):
    """An invoice's party as a trade document's data file takes it: the keys the trade builder has a field for,
    and of the recipient the ones the page shows. The builder refuses any other (depth 4: nothing given is
    dropped), and an invoice's seller carries keys of its own (its e-invoice address, its national numbers)."""
    known = json.loads((HERE / 'spec.fields.json').read_text())['defs']['party']
    return {k: v for k, v in party.items() if k in known and (not recipient or k in tc.RECIPIENT_PRINTS)}


class ThePage(unittest.TestCase):
    """The PDF's page: the shared sheet moved onto the layout with the shared letter's own arithmetic."""

    def page(self, s):
        return tc.page_html(s, tc.compute(s))

    def test_the_address_and_the_block_stand_where_the_layout_puts_them(self):
        for code in LEFT + RIGHT + LETTER:
            s = sent_from(code)
            lay = tc.Page(s).lay
            html = self.page(s)
            self.assertIn('content="%s"' % lay['name'], html, code)
            ax, ay, aw, _ah, line = letter.layout_address(lay)
            self.assertEqual(address_box(html), (round(ax, 2), round(ay, 2), round(aw, 2)), code)
            self.assertEqual(rule(html, '.address')['line-height'], '%smm' % line, code)     # the layout's own line height
            x0, y0, x1, _y1 = letter.window_box(lay)
            self.assertGreaterEqual(ax, x0 - 0.01, code)
            self.assertGreaterEqual(ay, y0 - 0.01, code)
            self.assertLessEqual(ax + aw, x1 + 0.01, code)
            self.assertEqual(rule(html, '.return').get('display'), 'none', code)          # no return line in the window
            info = rule(html, '.info')
            ix, iy, iw, how = letter.layout_info(lay)
            self.assertEqual((mm(info['left']), mm(info['top']), mm(info['width'])), (round(ix, 2), round(iy, 2), round(iw, 2)), code)
            wx, wy, ww, _wh = lay['window']
            edge = letter.PAPER_MM[lay['paper']][0] - lay['right']
            if code in RIGHT:
                self.assertLess(ix + iw, wx, code)                              # left of the window, ending before it
                self.assertEqual(ix, lay['left'], code)
            elif code in LETTER:
                self.assertIn('translateY(-100%)', info.get('transform', ''), code)   # it ends above the window
                self.assertLess(iy, wy, code)
                self.assertAlmostEqual(ix + iw, edge, places=1, msg=code)
            else:
                self.assertGreaterEqual(ix, wx + ww, code)                       # right of the window
                self.assertLessEqual(ix + iw, edge + 0.01, code)
            self.assertEqual(mm(rule(html, '.body')['padding-left']), round(lay['left'], 2), code)
            self.assertEqual(mm(rule(html, 'footer')['right']), round(lay['right'], 2), code)

    def test_form_b_keeps_its_field_its_return_line_and_its_block(self):
        g = letter.GEOMETRY
        for code in FORM_B:
            html = self.page(sent_from(code))
            self.assertIn('content="DIN 5008:2020 Form B"', html, code)
            self.assertEqual(address_box(html), (g['field_x'] + 5, g['field_y'] + g['return_h'], g['field_w'] - 5), code)
            self.assertNotEqual(rule(html, '.return').get('display'), 'none', code)
            self.assertEqual(mm(rule(html, '.info')['left']), g['info_x'], code)
            self.assertEqual(mm(rule(html, '.info')['width']), tc.info_mm('A4'), code)

    def test_the_heading_follows_the_window_or_the_block(self):
        es, us = self.page(sent_from('ES')), self.page(sent_from('US'))
        self.assertIn('Math.max(95*mm,(info.offsetTop+info.offsetHeight))', es)      # the lower of the two
        end = round(letter.LAYOUTS['us']['window'][1] + letter.LAYOUTS['us']['window'][3], 2)
        self.assertIn('const low=(%s*mm);' % end, us)                               # a block above the window pushes nothing
        self.assertNotIn('Math.max(', us)

    @unittest.skipUnless((INVOICE / 'page' / 'build_page.py').is_file(), 'the e-invoice pack is not beside this one')
    def test_the_shared_arithmetic_is_the_invoice_pages(self):
        sys.path.insert(0, str(INVOICE / 'page'))
        import build_page
        for lid, lay in letter.LAYOUTS.items():
            self.assertEqual(letter.layout_css(lay, build_page.INFO_GRID), build_page.layout_css(lay), lid)

    @unittest.skipUnless((INVOICE / 'page' / 'build_page.py').is_file(), 'the e-invoice pack is not beside this one')
    def test_a_trade_document_and_an_invoice_of_one_seller_share_the_address_window(self):
        """Every invoice starter's seller sends its buyer a quotation: the two pages put the address at the same
        rectangle, on the same layout."""
        sys.path.insert(0, str(INVOICE / 'page'))
        import build_page
        seen = set()
        for path in sorted((INVOICE / 'templates').glob('*-spec.json')):
            order = json.loads(path.read_text())
            order.setdefault('exchange_rate', 11.5)
            locale = build_page.page_locale_for(build_page.locale_of_order(order)[0])
            invoice = build_page.on_layout(build_page.paper_for(build_page.build(order, locale), locale), order)
            quote = {'type': 'quotation', 'number': 'Q-1', 'issue_date': '2026-10-12', 'currency': order['currency'],
                     'seller': order['seller'], 'buyer': order['buyer'],
                     'lines': [{'code': 'A-1', 'description': 'Example item', 'quantity': 2, 'unit': 'pcs', 'unit_price': 10, 'vat_rate': 0}]}
            if order.get('language'):
                quote['language'] = order['language']
            page = tc.Page(quote)
            self.assertEqual(page.paper, build_page.paper_of(locale), path.name)
            self.assertEqual(tc.layout_of(quote), build_page.layout_of(order), path.name)
            mine = self.page(quote)
            self.assertEqual(address_box(mine), address_box(invoice), path.name)
            if page.lay:
                # On a layout the window's height and the address's line height are the layout's too.
                for key in ('max-height', 'line-height', 'overflow'):
                    self.assertEqual(rule(mine, '.address')[key], rule(invoice, '.address')[key], path.name)
                self.assertEqual({k: rule(mine, '.info')[k] for k in ('left', 'top', 'width')},
                                 {k: rule(invoice, '.info')[k] for k in ('left', 'top', 'width')}, path.name)
            self.assertEqual(page.address(), build_page.buyer_address(order), path.name)     # and the same lines in it
            seen.add(tc.country(order['seller'].get('country')))
        self.assertGreaterEqual(seen, set(LEFT + RIGHT + LETTER), 'an invoice starter for every country with a layout')

    @unittest.skipUnless(can_print() and (INVOICE / 'page' / 'build_page.py').is_file(), 'no Chromium, pdftotext or invoice pack')
    def test_the_two_printed_pages_start_the_address_at_one_place(self):
        sys.path.insert(0, str(INVOICE / 'page'))
        import build_page
        for name in ('es-factura-spec.json', 'nl-factuur-spec.json', 'us-invoice-spec.json', 'xrechnung-credit-note-spec.json'):
            order = json.loads((INVOICE / 'templates' / name).read_text())
            locale = build_page.page_locale_for(build_page.locale_of_order(order)[0])
            folder = Path(tempfile.mkdtemp())
            (folder / 'invoice.html').write_text(build_page.on_layout(build_page.paper_for(build_page.build(order, locale), locale), order))
            build_page.print_pdf(folder / 'invoice.html', folder / 'invoice.pdf', build_page.paper_of(locale))
            quote = {'type': 'quotation', 'number': 'Q-1', 'issue_date': '2026-10-12', 'currency': order['currency'],
                     'seller': as_trade(order['seller']), 'buyer': as_trade(order['buyer'], recipient=True),
                     'lines': [{'code': 'A-1', 'description': 'Example item', 'quantity': 2, 'unit': 'pcs', 'unit_price': 10, 'vat_rate': 0}]}
            first = tc.Page(quote).address()[0].split()[0]
            x, y, _w = address_box(tc.page_html(quote, tc.compute(quote)))

            def where(pdf):
                # The buyer's name where the address starts, not the same word somewhere else on the page.
                hits = [w for w in einvoice_page.page_words(pdf) if w[4] == first]
                return min(hits, key=lambda w: abs(w[0] - x) + abs(w[1] - y))[:2]
            a, b = where(folder / 'invoice.pdf'), where(built(quote, 'pdf'))
            self.assertAlmostEqual(a[0], x, delta=0.3, msg=name)                 # on the left edge of the address
            self.assertLess(abs(a[1] - y), 2, name)                              # its first line
            self.assertAlmostEqual(a[0], b[0], delta=0.3, msg=name)
            self.assertAlmostEqual(a[1], b[1], delta=0.3, msg=name)


class Word(unittest.TestCase):
    """The Word file puts the address at the layout's own place and the block where the PDF has it."""

    def test_every_starter_on_a_layout_has_its_margins_its_window_and_its_block(self):
        for name in TEMPLATES:
            s = spec(name)
            page = tc.Page(s)
            out = built(s, 'docx')
            d = trade_check.docx_sheet(out)
            lines = page.address()
            row, at = next((r, i) for r, (_h, cells) in enumerate(d['rows']) for i, (_w, text) in enumerate(cells)
                           if text.split('\n')[0] == lines[0])
            cells = d['rows'][row][1]
            self.assertEqual(cells[at][1].split('\n'), lines, name)
            if not page.lay:
                self.assertAlmostEqual(d['margins']['top'], letter.GEOMETRY['field_y'], delta=0.1, msg=name)
                self.assertIsNone(trade_check.check('TRADE-WINDOW', out, {}, 'first')[0], name)
                self.assertIs(letter_check.check('LETTER-DIN5008', out, {}, 'first')[0], True, name)
                continue
            lay = page.lay
            ax, ay, _aw, _ah, _line = letter.layout_address(lay)
            ix, iy, iw, how = letter.layout_info(lay)
            self.assertAlmostEqual(d['size'][0], letter.PAPER_MM[lay['paper']][0], delta=0.1, msg=name)
            self.assertAlmostEqual(d['margins']['left'], lay['left'], delta=0.1, msg=name)
            self.assertAlmostEqual(d['margins']['right'], lay['right'], delta=0.1, msg=name)
            over = [h for h, _cells in d['rows'][:row]]
            self.assertNotIn(None, over, name)                                   # fixed rows down to the address
            self.assertAlmostEqual(d['margins']['top'] + sum(over), ay, delta=0.1, msg=name)
            self.assertAlmostEqual(d['margins']['left'] + sum(w for w, _t in cells[:at]), ax, delta=0.1, msg=name)
            widths = [w for w, _t in d['rows'][0][1]]
            if how == 'left':
                self.assertAlmostEqual(widths[0], iw, delta=0.1, msg=name)        # the block first, on the left margin
                self.assertEqual(at, 2, name)
            else:
                self.assertAlmostEqual(widths[-1], iw, delta=0.1, msg=name)       # the block last, ending on the right margin
                self.assertAlmostEqual(lay['left'] + sum(widths[:-1]), ix, delta=0.1, msg=name)
            if how == 'above':
                self.assertAlmostEqual(d['margins']['top'] + over[0], iy, delta=0.1, msg=name)   # the block's row ends above the window
            self.assertLessEqual(sum(widths), letter.PAPER_MM[lay['paper']][0] - lay['left'] - lay['right'] + 0.1, name)
            ok, why = trade_check.check('TRADE-WINDOW', out, {}, 'first')
            self.assertIs(ok, True, '%s: %s' % (name, why))
            self.assertIsNone(letter_check.check('LETTER-DIN5008', out, {}, 'first')[0], name)

    def test_no_return_line_on_a_layout_and_one_on_form_b(self):
        es, se = spec('quotation-es'), spec('quotation')
        self.assertNotIn(tc.Page(es).return_line(), letter_check.text_of(built(es, 'docx')))
        self.assertIn(tc.Page(se).return_line(), letter_check.text_of(built(se, 'docx')))

    def test_a_long_block_above_a_no_10_window_is_set_closer_never_cut(self):
        s = spec('quotation-us')
        s['references'] = [{'label': 'Reference %d' % i, 'value': 'R-%d' % i} for i in range(1, 11)]
        out = built(s, 'docx')
        self.assertIs(trade_check.check('TRADE-WINDOW', out, {}, 'first')[0], True)
        import zipfile
        with zipfile.ZipFile(out) as z:
            xml = z.read('word/document.xml').decode()
        rows = len(tc.Page(s).info_rows())
        room = letter.layout_info(letter.LAYOUTS['us'])[1] - tc.WORD_TOP
        spacing = [int(x) / 20 * 0.3528 for x in re.findall(r'<w:spacing w:line="(\d+)" w:lineRule="exact"/>', xml)]
        tight = [x for x in spacing if abs(x - room / rows) < 0.05]
        self.assertEqual(len(tight), 2 * rows)                                    # every label and value on the closer line
        self.assertLessEqual(rows * tight[0], room + 0.2)

    def test_the_rule_catches_a_page_on_another_countrys_sheet(self):
        out = built(spec('quotation-es'), 'docx')
        other = dict(spec('quotation-es'), seller=dict(spec('quotation-es')['seller'], country='NL'))
        (out.parent / 'doc.spec.json').write_text(json.dumps(other, ensure_ascii=False))
        ok, why = trade_check.check('TRADE-WINDOW', out, {}, 'first')
        self.assertIs(ok, False, why)
        self.assertIn('the address starts 120.0 mm across', why)
        # A file with no fixed rows above its address (written by hand): the rule says how to build it.
        import zipfile
        doc = out.parent / 'hand.docx'
        with zipfile.ZipFile(out) as z, zipfile.ZipFile(doc, 'w') as o:
            for n in z.namelist():
                data = z.read(n)
                if n == 'word/document.xml':
                    data = data.replace(b'w:hRule="exact"', b'w:hRule="atLeast"')
                o.writestr(n, data)
        (out.parent / 'doc.spec.json').write_text(json.dumps(spec('quotation-es'), ensure_ascii=False))
        ok, why = trade_check.check('TRADE-WINDOW', doc, {}, 'first')
        self.assertIs(ok, False, why)
        self.assertIn('trade_create.py', why)


class Workbook(unittest.TestCase):
    """The workbook keeps the address on the side the PDF has it."""

    def cells(self, s):
        from openpyxl import load_workbook
        ws = load_workbook(built(s, 'xlsx')).active
        return {c.coordinate: str(c.value) for row in ws.iter_rows() for c in row if c.value is not None}, ws

    def find(self, cells, text):
        ref = next(k for k, v in cells.items() if v == text)
        col, row = re.match(r'([A-Z]+)(\d+)', ref).groups()
        return col, int(row)

    def test_a_window_on_the_right_puts_the_address_right_of_the_block(self):
        from openpyxl.utils import column_index_from_string as index
        for name in ('quotation-es', 'order-confirmation-it', 'purchase-order-pl', 'order-confirmation-be-nl', 'delivery-note-be-fr'):
            s = spec(name)
            page = tc.Page(s)
            cells, _ws = self.cells(s)
            label, value = page.info_rows()[0]
            lc, lr = self.find(cells, label)
            vc, _vr = self.find(cells, str(value))
            ac, ar = self.find(cells, page.address()[0])
            self.assertEqual((lc, lr), ('A', 3), name)                           # the block on the left edge, under the letterhead
            self.assertEqual(ar, 3, name)                                        # the address level with it
            self.assertLess(index(vc), index(ac), name)                          # and to its right
            self.assertNotIn('A2', cells, name)                                  # no return line, as on the PDF

    def test_a_window_on_the_left_keeps_the_address_on_the_left(self):
        for name in ('quotation-nl', 'proforma-invoice-ie', 'quotation-au', 'order-confirmation-fi'):
            s = spec(name)
            page = tc.Page(s)
            cells, _ws = self.cells(s)
            self.assertEqual(self.find(cells, page.address()[0]), ('A', 3), name)
            self.assertNotEqual(self.find(cells, page.info_rows()[0][0])[0], 'A', name)
            self.assertNotIn('A2', cells, name)

    def test_a_no_10_window_puts_the_block_above_the_address(self):
        for name in ('quotation-us', 'order-confirmation-fr-ca', 'proforma-invoice-ca'):
            s = spec(name)
            page = tc.Page(s)
            cells, _ws = self.cells(s)
            rows = page.info_rows()
            self.assertEqual(self.find(cells, rows[0][0])[1], 3, name)
            last = self.find(cells, rows[-1][0])[1]
            col, row = self.find(cells, page.address()[0])
            self.assertEqual(col, 'A', name)
            self.assertGreater(row, last, name)                                  # the address starts under the block
            self.assertNotEqual(self.find(cells, rows[0][0])[0], 'A', name)      # which stands on the right

    def test_form_b_is_as_it_was(self):
        s = spec('quotation')
        cells, _ws = self.cells(s)
        self.assertEqual(cells['A2'], tc.Page(s).return_line())
        self.assertEqual(self.find(cells, tc.Page(s).address()[0]), ('A', 4))


class Addresses(unittest.TestCase):
    """Which addresses are a block, written as the post office reads them, and which are one line and stay."""

    def test_the_footers_first_column_is_the_companys_own_address(self):
        # One company, one footer (depth 4, item 9): the imprint its letter and its invoice print
        # (letter.own_address), in ordinary case. The post office's capitals are for the address field alone.
        for name in TEMPLATES:
            s = spec(name)
            page = tc.Page(s)
            self.assertEqual(page.footer()[0], letter.own_address(tc.own(tc.sender(s)), tc.recipient(s).get('country')), name)
        who = lambda name: tc.Page(spec(name)).footer()[0]  # noqa: E731
        self.assertEqual(who('quotation-es')[1:], ['Calle del Ejemplo 12', '28001 Madrid'])                # the province is the town's own name
        self.assertEqual(who('order-confirmation-it')[-2:], ['Via Esempio 21', '40121 Bologna (BO)'])
        self.assertEqual(who('purchase-order-pl')[-1], '60-001 Poznań')
        self.assertEqual(who('quotation-us')[-2:], ['400 Example Avenue', 'Lincoln, NE 68508'])            # the town as the data writes it
        self.assertEqual(who('proforma-invoice-ie')[-2:], ['Dublin 24 D24 X2Y3', 'IRELAND'])               # abroad: the country last
        self.assertEqual(who('proforma-invoice')[-1], 'SWEDEN')
        self.assertNotIn('España', who('quotation-es'))                                                    # at home: none

    def test_a_one_line_address_stays_as_it_was(self):
        es = tc.Page(spec('quotation-es'))
        self.assertEqual(es.footer(block=False)[0], ['Ejemplo Imprenta S.L.', 'Calle del Ejemplo 12', '28001 Madrid', 'España'])
        self.assertEqual(es.footer(block=False)[1:], es.footer()[1:])             # the other two columns do not change
        se = tc.Page(spec('quotation'))
        self.assertTrue(se.return_line().endswith('411 14 Göteborg'))               # the return line of a Form B page
        pl = spec('purchase-order-pl')
        line = ', '.join(tc.Page(pl).party(tc.delivery_address(pl), False))        # the delivery line
        self.assertIn('60-002 Poznań', line)
        self.assertNotIn('POZNAŃ', line)

    def test_the_three_writers_print_them_that_way(self):
        s = spec('purchase-order-pl')
        page = tc.Page(s)
        html = tc.page_html(s, tc.compute(s))
        self.assertIn('<footer><div>%s</div>' % '<br>'.join(letter.keep(x) for x in page.footer()[0]), html)
        self.assertIn('60-002 Poznań', html)
        word = letter_check.text_of(built(s, 'docx'))
        self.assertIn('60-001 Poznań', word)
        self.assertNotIn('60-001 POZNAŃ', word)
        self.assertIn('60-002 Poznań', word)
        from openpyxl import load_workbook
        ws = load_workbook(built(s, 'xlsx')).active
        texts = [str(c.value) for row in ws.iter_rows() for c in row if c.value is not None]
        self.assertIn(' · '.join(page.footer(block=False)[0]), texts)


class Rule(unittest.TestCase):
    """TRADE-WINDOW is one of the pack's rules and measures the printed page."""

    def test_the_pack_check_runs_it_and_din_5008_stands_aside(self):
        self.assertIn('TRADE-WINDOW', packcheck.SKILL_RULES['trade-documents'])
        self.assertIn('LETTER-DIN5008', packcheck.SKILL_RULES['trade-documents'])
        self.assertIsNone(trade_check.check('TRADE-WINDOW', built(spec('quotation-es'), 'xlsx'), {}, 'first')[0])
        self.assertIsNone(trade_check.layout_for(spec('quotation')))
        self.assertEqual(trade_check.layout_for(spec('purchase-order-pl'))['country'], 'PL')
        self.assertIsNone(trade_check.layout_for(spec('quotation-us'), 210.0))     # a US document on A4 is a Form B page
        self.assertEqual(trade_check.layout_for(spec('quotation-us'), 215.9)['country'], 'US')

    def test_a_file_with_no_spec_beside_it_is_read_from_a_cases_truth(self):
        s = dict(spec('purchase-order'), buyer=dict(spec('purchase-order')['buyer'], country='Denmark'))
        out = built(s, 'docx')
        (out.parent / 'doc.spec.json').unlink()
        self.assertIsNone(trade_check.check('TRADE-WINDOW', out, {}, 'first')[0])           # nothing says what the file is
        case = {'truth': dict({k: v for k, v in s.items() if k != 'type'}, doc='purchase_order')}
        ok, why = trade_check.check('TRADE-WINDOW', out, case, 'first')                      # the buyer's country: Denmark
        self.assertIs(ok, True, why)
        self.assertIn('C5/E65', why)
        self.assertIsNone(letter_check.check('LETTER-DIN5008', out, case, 'first')[0])

    def test_every_starter_passes_the_pack_check_in_word_and_excel(self):
        for name in TEMPLATES:
            for ext in ('docx', 'xlsx'):
                with self.subTest(template=name, kind=ext):
                    out = built(spec(name), ext)
                    r = subprocess.run([sys.executable, str(CHECKS / 'packcheck.py'), 'trade-documents', str(out)],
                                       capture_output=True, text=True, cwd=out.parent)
                    self.assertEqual(r.returncode, 0, r.stdout)

    @unittest.skipUnless(can_print(), 'no Chromium or pdftotext to measure a printed page with')
    def test_every_starter_passes_the_pack_check_as_a_pdf(self):
        for name in TEMPLATES:
            with self.subTest(template=name):
                s = spec(name)
                out = built(s, 'pdf')
                r = subprocess.run([sys.executable, str(CHECKS / 'packcheck.py'), 'trade-documents', str(out)],
                                   capture_output=True, text=True, cwd=out.parent)
                self.assertEqual(r.returncode, 0, r.stdout)
                ok, why = trade_check.check('TRADE-WINDOW', out, {}, 'first')
                self.assertIs(ok, True if tc.Page(s).lay else None, '%s: %s' % (name, why))
                self.assertIs(trade_check.check('TRADE-BLOCK', out, {}, 'first')[0], True, name)

    @unittest.skipUnless(can_print(), 'no Chromium or pdftotext to measure a printed page with')
    def test_a_page_from_each_of_the_seventeen_countries_is_on_its_sheet(self):
        for code in LEFT + RIGHT + LETTER + FORM_B:
            with self.subTest(country=code):
                s = sent_from(code)
                out = built(s, 'pdf')
                lay = tc.Page(s).lay
                ok, why = trade_check.check('TRADE-WINDOW', out, {}, 'first')
                self.assertIs(ok, True if lay else None, '%s: %s' % (code, why))
                ok, why = trade_check.check('TRADE-BLOCK', out, {}, 'first')
                self.assertIs(ok, True, '%s: %s' % (code, why))
                ok, why = letter_check.check('LETTER-DIN5008', out, {}, 'first')
                self.assertIs(ok, None if lay else True, '%s: %s' % (code, why))
                if lay:
                    # The first address line starts where the layout says, to a third of a millimetre across.
                    first = tc.Page(s).address()[0].split()[0]
                    x0, y0, x1, y1 = letter.window_box(lay)
                    hit = min((w for w in einvoice_page.page_words(out) if w[4] == first and y0 - 1 <= w[1] <= y1), key=lambda w: w[1])
                    self.assertAlmostEqual(hit[0], lay['address_at'][0], delta=0.3, msg=code)
                    self.assertGreaterEqual(hit[1], y0 - 0.5, code)

    @unittest.skipUnless(can_print(), 'no Chromium or pdftotext to measure a printed page with')
    def test_the_rule_catches_what_leaves_the_sheet(self):
        s = spec('quotation-es')
        cases = (
            ('.field{left:25mm}', 'outside the window'),                                           # the address back on the left
            ('.body{padding-left:35mm}', 'the text starts 35.0 mm across'),                        # another left margin
            ('.body{padding-right:35mm}', "the layout's right margin puts it at 190.0 mm"),        # a table that ends short
        )
        for css, words in cases:
            out = built(s, 'pdf', edit=lambda h, css=css: h.replace('</style>', css + '</style>', 1))
            ok, why = trade_check.check('TRADE-WINDOW', out, {}, 'first')
            self.assertIs(ok, False, '%s: %s' % (css, why))
            self.assertIn(words, why)
            self.assertIn('the sheet is Spain: A4, window on the right', why)       # which sheet, and what it rests on
            self.assertIn('Correos, Dimensiones y pesos de los envíos', why)
        stray = '<div style="position:absolute;left:150mm;top:80mm;font-size:8pt">Ref-77</div>'
        out = built(s, 'pdf', edit=lambda h: h.replace('<footer>', stray + '<footer>', 1))
        ok, why = trade_check.check('TRADE-WINDOW', out, {}, 'first')
        self.assertIs(ok, False, why)
        self.assertIn('something else shows in the window: Ref-77', why)

    @unittest.skipUnless(can_print(), 'no Chromium or pdftotext to measure a printed page with')
    def test_the_block_rule_knows_each_side(self):
        # Left of a window on the right, the block ends before the window.
        s = copy.deepcopy(spec('quotation-es'))
        out = built(s, 'pdf', edit=lambda h: h.replace('</style>', '.info{width:95mm}.info dt{width:60mm}</style>', 1))
        ok, why = trade_check.check('TRADE-BLOCK', out, {}, 'first')
        self.assertIs(ok, False, why)
        self.assertIn('before the window', why)
        # Above a No. 10 window, it ends above the window.
        out = built(spec('quotation-us'), 'pdf', edit=lambda h: h.replace('</style>', '.info{transform:none}</style>', 1))
        ok, why = trade_check.check('TRADE-BLOCK', out, {}, 'first')
        self.assertIs(ok, False, why)
        self.assertIn('above the window', why)
        # Beside a window on the left, it ends on the text's right edge, and a label that wraps is named.
        old = ('.info{display:block;width:85mm}.info div{display:flex;gap:3mm}.info dt{width:34mm;flex:none}'
               '.info dd{min-width:auto;overflow-wrap:normal;white-space:nowrap}')
        s = copy.deepcopy(spec('quotation-nl'))
        s['references'].append({'label': 'Onze referentie', 'value': 'afdeling.verkoop.regio.noord@polderlicht-installatietechniek.example'})
        out = built(s, 'pdf', edit=lambda h: h.replace('</style>', old + '</style>', 1).replace('<wbr>', ''))
        ok, why = trade_check.check('TRADE-BLOCK', out, {}, 'first')
        self.assertIs(ok, False, why)
        self.assertIn("the text's right edge", why)
        narrow = '.info{grid-template-columns:18mm minmax(0,1fr)}.info dt{white-space:normal}'
        out = built(spec('purchase-order-pl'), 'pdf', edit=lambda h: h.replace('</style>', narrow + '</style>', 1))
        ok, why = trade_check.check('TRADE-BLOCK', out, {}, 'first')
        self.assertIs(ok, False, why)
        self.assertIn('wraps', why)


if __name__ == '__main__':
    unittest.main()
