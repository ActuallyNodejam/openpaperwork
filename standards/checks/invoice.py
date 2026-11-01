"""Invoice arithmetic and field checks for a workbook invoice. Needs openpyxl.

check(rule_id, path, case, stage) -> (passed, evidence)

Expected figures are computed from the case's order.csv with decimal half-up rounding: each line
net to two decimals, then VAT once per rate on the sum of that rate's line nets.

INV-HEAD    The labelled header values match the parties file for this stage.
INV-LINES   Every order line is present with its quantity, price, discount, rate and net; nets are formulas.
INV-VAT     One VAT row per rate with the right taxable and VAT amounts, as formulas.
INV-TOTALS  Totals excluding VAT, VAT and including VAT are right and are formulas.
"""
import csv
import datetime
import json
import re
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

EVAL = Path(__file__).resolve().parent.parent
TOL = Decimal('0.006')


def r2(x):
    return Decimal(x).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def expected(case, stage):
    folder = EVAL / next(c['path'] for c in json.loads((EVAL / 'catalogue.json').read_text()) if c['id'] == case['id'])
    lines = []
    for row in csv.DictReader((folder / 'inputs/order.csv').read_text().splitlines()):
        q, p, d = Decimal(row['Quantity']), Decimal(row['Unit price EUR']), Decimal(row['Discount %'])
        rate = Decimal(0) if case['truth']['reverse_charge'][stage] else Decimal(row['VAT rate %'])
        lines.append(dict(desc=row['Description'], qty=q, price=p, disc=d, rate=rate, net=r2(q * p * (1 - d / 100))))
    vat = {}
    for l in lines:
        vat[l['rate']] = vat.get(l['rate'], Decimal(0)) + l['net']
    vat = {rate: (base, r2(base * rate / 100)) for rate, base in vat.items()}
    net = sum(l['net'] for l in lines)
    tax = sum(v for _, v in vat.values())
    return lines, vat, (net, tax, net + tax)


def norm(v):
    return re.sub(r'\s+', ' ', str(v)).strip().rstrip(':').lower() if v is not None else ''


def num(v):
    if isinstance(v, (int, float)):
        return Decimal(str(v))
    try:
        return Decimal(str(v).replace('%', '').replace(',', '').strip())
    except Exception:
        return None


def pct(v):
    n = num(v)
    if n is None:
        return None
    return n * 100 if (isinstance(v, (int, float)) and 0 < n <= 1) else n


def date(v):
    if isinstance(v, (datetime.datetime, datetime.date)):
        return v.strftime('%Y-%m-%d')
    return str(v).strip()[:10]


class Sheet:
    def __init__(self, path):
        import openpyxl
        wf, wv = openpyxl.load_workbook(path), openpyxl.load_workbook(path, data_only=True)
        name = next((n for n in wf.sheetnames if n.lower() == 'invoice'), None)
        if name is None:
            raise ValueError('no sheet named Invoice')
        self.f, self.v = wf[name], wv[name]
        self.cells = [(c.row, c.column, c.value) for row in self.v.iter_rows() for c in row if c.value is not None]

    def is_formula(self, r, c):
        v = self.f.cell(r, c).value
        return isinstance(v, str) and v.startswith('=')

    def labelled(self, label):
        """Value in the next filled cell to the right of the label cell, with its position."""
        for r, c, v in self.cells:
            if norm(v) == label.lower():
                for k in range(1, 4):
                    val = self.v.cell(r, c + k).value
                    if val is not None:
                        return val, r, c + k
                raw = self.f.cell(r, c + 1).value
                return (None, r, c + 1) if raw is not None else (None, None, None)
        return None, None, None

    def table(self, columns):
        """Rows under the header row that holds every column name; a dict of column -> (value, row, col)."""
        want = [x.lower() for x in columns]
        for r in sorted({r for r, _, _ in self.cells}):
            heads = {}
            for c in range(1, self.v.max_column + 1):
                h = norm(self.v.cell(r, c).value)
                for w in want:
                    if h == w or h.startswith(w + ' '):
                        heads.setdefault(w, c)
            if len(heads) == len(want):
                rows, rr = [], r + 1
                while rr <= self.v.max_row and self.v.cell(rr, heads[want[0]]).value is not None and norm(self.v.cell(rr, heads[want[0]]).value) not in want:
                    rows.append({w: (self.v.cell(rr, heads[w]).value, rr, heads[w]) for w in want})
                    rr += 1
                return rows
        return None


def close(a, b):
    return a is not None and abs(a - b) <= TOL


def check(rule_id, path, case, stage):
    try:
        s = Sheet(path)
    except ValueError as e:
        return False, str(e)
    lines, vat, (net, tax, gross) = expected(case, stage)
    t = case['truth']
    if rule_id == 'INV-HEAD':
        want = dict(t['header']['first'], **(t['header'][stage] if stage != 'first' else {}))
        for label, value in want.items():
            got, _, _ = s.labelled(label)
            if got is None:
                return False, 'label "%s" has no value to its right' % label
            g = date(got) if 'date' in label.lower() else str(got).strip()
            if value.lower() not in g.lower():
                return False, '%s is "%s", expected "%s"' % (label, g, value)
        note = t['note'][stage]
        if note and not any(note.lower() in norm(v) for _, _, v in s.cells):
            return False, 'the note "%s" is missing' % note
        return True, '%d header values match%s' % (len(want), ' and the note is present' if note else '')
    if rule_id == 'INV-LINES':
        rows = s.table(['Description', 'Quantity', 'Unit price', 'Discount %', 'Net amount', 'VAT rate'])
        if rows is None:
            return False, 'no lines table with the six requested columns'
        if len(rows) != len(lines):
            return False, '%d line rows, expected %d' % (len(rows), len(lines))
        for l in lines:
            row = next((x for x in rows if norm(x['description'][0]) == l['desc'].lower()), None)
            if row is None:
                return False, 'line "%s" is missing' % l['desc']
            checks = [('quantity', num(row['quantity'][0]), l['qty']), ('unit price', num(row['unit price'][0]), l['price']),
                      ('discount %', pct(row['discount %'][0]), l['disc']), ('vat rate', pct(row['vat rate'][0]), l['rate']),
                      ('net amount', num(row['net amount'][0]), l['net'])]
            for name, got, exp in checks:
                if not close(got, exp):
                    return False, '%s: %s is %s, expected %s' % (l['desc'], name, got, exp)
            if not s.is_formula(row['net amount'][1], row['net amount'][2]):
                return False, '%s: net amount is not a formula' % l['desc']
        return True, '%d lines match, nets are formulas' % len(lines)
    if rule_id == 'INV-VAT':
        rows = s.table(['VAT rate', 'Taxable amount', 'VAT amount'])
        if rows is None:
            return False, 'no VAT table with VAT rate, Taxable amount and VAT amount'
        got = {}
        for x in rows:
            rate = pct(x['vat rate'][0])
            if rate is not None:
                got[rate.normalize()] = x
        if {k.normalize() for k in vat} != set(got):
            return False, 'VAT rates are %s, expected %s' % (sorted(str(k) for k in got), sorted(str(k) for k in vat))
        for rate, (base, amount) in vat.items():
            x = got[rate.normalize()]
            if not close(num(x['taxable amount'][0]), base) or not close(num(x['vat amount'][0]), amount):
                return False, 'rate %s%%: taxable %s and VAT %s, expected %s and %s' % (rate, x['taxable amount'][0], x['vat amount'][0], base, amount)
            if not s.is_formula(x['taxable amount'][1], x['taxable amount'][2]) or not s.is_formula(x['vat amount'][1], x['vat amount'][2]):
                return False, 'rate %s%%: taxable or VAT amount is not a formula' % rate
        return True, '%d VAT rows match, as formulas' % len(vat)
    if rule_id == 'INV-TOTALS':
        for label, exp in (('Total excluding VAT', net), ('Total VAT', tax), ('Total including VAT', gross)):
            got, r, c = s.labelled(label)
            if r is None:
                return False, 'label "%s" not found' % label
            if not close(num(got), exp):
                return False, '%s is %s, expected %s' % (label, got, exp)
            if not s.is_formula(r, c):
                return False, '%s is not a formula' % label
        return True, 'totals %s, %s and %s match, as formulas' % (net, tax, gross)
    return False, 'unknown rule %s' % rule_id
