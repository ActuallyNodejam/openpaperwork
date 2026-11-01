#!/usr/bin/env python3
"""Checks for trade paperwork: quotations, order confirmations, delivery notes and pro forma invoices.

check(rule_id, path, case, stage) -> (passed, evidence). Reads .docx and .xlsx with the standard library and
openpyxl, and .pdf through pdftotext (None, skipped, when pdftotext is missing). Expected values come from
case['truth'][stage]; amounts are computed from its lines with the EN 16931 rule the invoice checks use: each
line net to two decimals half-up, VAT once per rate on the summed nets, tolerance 0.006.

TRD-TYPE     The document names what it is; a pro forma invoice says so in its heading.
TRD-HEAD     Document number, issue date, seller and buyer with their VAT identifiers, and the currency.
TRD-REFS     The earlier documents it answers are referenced by number.
TRD-LINES    Every line is there with its quantities and, where prices belong, its unit price and net amount.
TRD-TOTALS   Total excluding VAT, VAT per rate and total including VAT are stated and right; live formulas in a workbook.
TRD-DATES    The dates this document exists to state (validity, confirmed delivery, despatch) are there.
TRD-PAY      Payment terms are stated.
TRD-SHIP     A delivery note states the number of packages and the gross weight and has a place to sign for receipt.
TRD-NOPRICE  A delivery note shows no price, amount or currency.
TRD-CUSTOMS  A pro forma invoice gives a customs code and country of origin for every line of goods.
TRD-STALE    Nothing the revision replaced is left in the document.
INCO-1       The delivery term is a real Incoterms 2020 rule followed by a named place and "Incoterms 2020".
INCO-2       No sea-only rule (FAS, FOB, CFR, CIF) is used for goods that do not travel by sea.

CLI: python3 trade.py FILE --case case.json [--stage first|revision] [RULE ...]
"""
import datetime
import json
import re
import shutil
import subprocess
import sys
import zipfile
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from xml.etree import ElementTree as ET

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
TOL = Decimal('0.006')
RULES_ANY = ('EXW', 'FCA', 'CPT', 'CIP', 'DAP', 'DPU', 'DDP')
RULES_SEA = ('FAS', 'FOB', 'CFR', 'CIF')
OLD_RULES = ('DAT', 'DAF', 'DES', 'DEQ', 'DDU')
TYPES = {'quotation': r'\b(quotation|quote|offer|angebot|offert|tilbud)\b',
         'order_confirmation': r'\b(order\s+(confirmation|acknowledge?ment)|auftragsbest\u00e4tigung|orderbekr\u00e4ftelse|ordrebekr\u00e6ftelse)\b',
         'delivery_note': r'\b(delivery\s+note|despatch\s+advice|dispatch\s+note|delivery\s+slip|packing\s+slip|lieferschein|f\u00f6ljesedel|f\u00f8lgeseddel)\b',
         'proforma_invoice': r'\b(pro[\s-]?forma\s+invoice|proformarechnung|proformafaktura)\b'}
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']


class Skip(Exception):
    pass


def r2(x):
    return Decimal(str(x)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def squash(s):
    return re.sub(r'[\s  ]+', ' ', s).strip()


def parse_one(t):
    """One token without spaces, read as an amount in every way its separators allow."""
    t = t.strip(".,'")
    if not t:
        return set()
    if ',' in t and '.' in t:
        forms = {t.replace(',', '') if t.rfind('.') > t.rfind(',') else t.replace('.', '').replace(',', '.')}
    elif ',' in t:
        forms = {t.replace(',', '.') if re.search(r',\d{1,2}$', t) else t.replace(',', ''), t.replace(',', '')}
    elif t.count('.') > 1:
        forms = {t.replace('.', '')}
    else:
        forms = {t}
    out = set()
    for f in forms:
        try:
            out.add(Decimal(f))
        except InvalidOperation:
            pass
    return out


def numbers(text):
    """Every amount a piece of text can be read as: 1 234,50 and 1,234.50 and 1234.5 all give 1234.50."""
    out = set()
    for tok in re.findall(r"\d[\d \u00a0\u202f.,']*", text):
        parts = [x for x in re.split(r"[ \u00a0\u202f']+", tok) if x.strip('.,')]
        for i, part in enumerate(parts):
            out |= parse_one(part)
            if re.fullmatch(r'\d{1,3}', part):  # a space as thousands separator: 38 500.00
                joined, j = part, i + 1
                while j < len(parts) and re.fullmatch(r'\d{3}(?:[.,]\d+)?[.,]?', parts[j]):
                    joined += parts[j]
                    out |= parse_one(joined)
                    if not parts[j].isdigit():
                        break
                    j += 1
    return out


def has(nums, value):
    value = Decimal(str(value))
    return any(abs(n - value) <= TOL for n in nums)


class Doc:
    """rows: one string per table row, paragraph, sheet row or text line. formulas: row index -> values of formula cells."""

    def __init__(self, path):
        path = Path(path)
        self.kind = path.suffix.lower().lstrip('.')
        self.rows, self.formulas, self.title = [], {}, ''
        if self.kind == 'docx':
            with zipfile.ZipFile(path) as z:
                names = z.namelist()
                parts = ['word/document.xml'] + sorted(n for n in names if re.fullmatch(r'word/(header|footer)\d*\.xml', n))
                for part in parts:
                    self._docx(ET.fromstring(z.read(part)))
                if 'docProps/core.xml' in names:
                    m = re.search(r'<dc:title>(.*?)</dc:title>', z.read('docProps/core.xml').decode('utf-8', 'replace'), re.S)
                    self.title = m.group(1) if m else ''
        elif self.kind == 'xlsx':
            import openpyxl
            wf, wv = openpyxl.load_workbook(path), openpyxl.load_workbook(path, data_only=True)
            self.title = wf.properties.title or ''
            for ws in wf.worksheets:
                vs = wv[ws.title]
                for row in ws.iter_rows():
                    cells, forms = [], []
                    for c in row:
                        v = vs[c.coordinate].value
                        if c.value is None:
                            continue
                        is_formula = isinstance(c.value, str) and c.value.startswith('=')
                        shown = v if is_formula else c.value
                        if isinstance(shown, (datetime.date, datetime.datetime)):
                            shown = shown.strftime('%Y-%m-%d')
                        elif isinstance(shown, float):
                            shown = repr(round(shown, 4))
                        if shown is not None:
                            cells.append(str(shown))
                        if is_formula and isinstance(v, (int, float)):
                            forms.append(Decimal(repr(round(v, 4))))
                    if cells:
                        self.formulas[len(self.rows)] = forms
                        self.rows.append(' | '.join(cells))
        elif self.kind == 'pdf':
            tool = shutil.which('pdftotext')
            if not tool:
                raise Skip('pdftotext is not installed')
            p = subprocess.run([tool, '-layout', str(path), '-'], capture_output=True, text=True, timeout=120)
            if p.returncode:
                raise ValueError('not a readable PDF: %s' % p.stderr.strip()[:120])
            self.rows = [re.sub(r' {2,}', ' | ', l.strip()) for l in p.stdout.splitlines() if l.strip()]
            info = shutil.which('pdfinfo')
            if info:
                m = re.search(r'^Title:\s*(.*)$', subprocess.run([info, str(path)], capture_output=True, text=True).stdout, re.M)
                self.title = m.group(1).strip() if m else ''
        else:
            raise ValueError('unsupported file type %s' % path.suffix)
        self.rows = [squash(r) for r in self.rows if squash(r)]
        self.text = ' \n '.join(self.rows)
        self.flat = squash(self.text)
        self.nums = numbers(self.text)

    def _docx(self, root):
        body = root.find(W + 'body') if root.find(W + 'body') is not None else root
        def para(p):
            return ''.join(t.text or '' if t.tag == W + 't' else ' ' for t in p.iter() if t.tag in (W + 't', W + 'tab', W + 'br'))
        def walk(el):
            for child in el:
                if child.tag == W + 'p':
                    self.rows.append(para(child))
                elif child.tag == W + 'tbl':
                    for tr in child.findall(W + 'tr'):
                        cells = [' '.join(para(p) for p in tc.iter(W + 'p')) for tc in tr.findall(W + 'tc')]
                        self.rows.append(' | '.join(cells))
                        for tc in tr.findall(W + 'tc'):  # a table inside a cell still counts
                            for inner in tc.findall(W + 'tbl'):
                                walk([inner])
                elif child.tag in (W + 'sdt', W + 'sdtContent'):
                    walk(child)
        walk(body)

    def rows_with(self, needle):
        return [(i, r) for i, r in enumerate(self.rows) if needle.lower() in r.lower()]


def truth(case, stage):
    t = (case or {}).get('truth', {})
    return {**{k: v for k, v in t.items() if k not in ('first', 'revision')}, **(t.get(stage) or {})}


def expected(t):
    lines = []
    for l in t['lines']:
        q, p, d = Decimal(str(l['quantity'])), Decimal(str(l.get('unit_price', 0))), Decimal(str(l.get('discount_percent', 0)))
        lines.append(dict(l, net=r2(q * p * (1 - d / 100)), rate=Decimal(str(l.get('vat_rate', 0)))))
    groups = {}
    for l in lines:
        groups[l['rate']] = groups.get(l['rate'], Decimal(0)) + l['net']
    vat = {rate: (base, r2(base * rate / 100)) for rate, base in groups.items()}
    net = sum((l['net'] for l in lines), Decimal(0))
    tax = sum((v for _, v in vat.values()), Decimal(0))
    return lines, vat, net, tax, net + tax


def date_forms(iso):
    y, m, d = (int(x) for x in iso.split('-'))
    mon = MONTHS[m - 1]
    forms = [iso, '%d %s %d' % (d, mon, y), '%02d %s %d' % (d, mon, y), '%d %s %d' % (d, mon[:3], y), '%02d %s %d' % (d, mon[:3], y),
             '%s %d, %d' % (mon, d, y), '%s %d, %d' % (mon[:3], d, y), '%02d/%02d/%d' % (d, m, y), '%d/%d/%d' % (d, m, y),
             '%02d.%02d.%d' % (d, m, y), '%d.%d.%d' % (d, m, y), '%02d-%02d-%d' % (d, m, y), '%d-%02d-%02d 00:00:00' % (y, m, d),
             '%d %s' % (d, mon), '%s %d' % (mon, d)]
    return forms


def has_date(doc, iso, strict=True):
    forms = date_forms(iso)
    forms = forms[:-2] if strict else forms
    low = doc.flat.lower().replace(',', '')
    return any(f.lower().replace(',', '') in low for f in forms)


def fails(bad, ok):
    return (not bad), (ok if not bad else '; '.join(bad[:8]) + (' (+%d more)' % (len(bad) - 8) if len(bad) > 8 else ''))


def line_rows(doc, l):
    """Rows that carry this line: by item code first, else by the opening words of the description."""
    rows = doc.rows_with(l['code']) if l.get('code') else []
    if not rows and l.get('match'):
        rows = [(i, r) for i, r in enumerate(doc.rows) if re.search(l['match'], r, re.I)]
    if not rows:
        words = ' '.join(l['description'].split()[:3])
        rows = doc.rows_with(words)
    out = []
    for i, r in rows:
        nxt = doc.rows[i + 1] if doc.kind == 'pdf' and i + 1 < len(doc.rows) else ''
        out.append((i, r + ' ' + nxt))
    return out


# ---------- rules ----------

def trd_type(doc, t):
    pat = TYPES[t['doc']]
    head = ' '.join(doc.rows[:8]) + ' ' + doc.title
    if not re.search(pat, head, re.I):
        return False, 'the heading does not name the document: %r' % squash(head)[:90]
    if t['doc'] == 'proforma_invoice' and re.search(r'\b(tax|commercial|vat)\s+invoice\b', ' '.join(doc.rows[:3]), re.I):
        return False, 'the heading reads as a tax or commercial invoice'
    return True, 'named in the heading'


def trd_head(doc, t):
    bad = []
    if t['number'].lower() not in doc.flat.lower():
        bad.append('document number %s missing' % t['number'])
    if not has_date(doc, t['issue_date']):
        bad.append('issue date %s missing' % t['issue_date'])
    for role in ('seller', 'buyer'):
        p = t[role]
        if p['name'].lower() not in doc.flat.lower():
            bad.append('%s name %r missing' % (role, p['name']))
        if p.get('vat_id') and re.sub(r'\W', '', p['vat_id']).lower() not in re.sub(r'\W', '', doc.flat).lower():
            bad.append('%s VAT ID %s missing' % (role, p['vat_id']))
        if p.get('city') and p['city'].lower() not in doc.flat.lower():
            bad.append('%s city %s missing' % (role, p['city']))
    if t['doc'] != 'delivery_note' and t.get('currency') and not re.search(r'\b%s\b' % t['currency'], doc.flat):
        bad.append('currency %s not stated' % t['currency'])
    return fails(bad, 'number, date, parties and currency present')


def trd_refs(doc, t):
    bad = ['reference %s missing' % r for r in t.get('references', []) if r.lower() not in doc.flat.lower()]
    return fails(bad, '%d references present' % len(t.get('references', [])))


def trd_lines(doc, t):
    lines = expected(t)[0]
    bad = []
    for l in lines:
        rows = line_rows(doc, l)
        name = l.get('code') or l['description'][:25]
        if not rows:
            bad.append('line %s missing' % name)
            continue
        if t['doc'] == 'delivery_note':
            done = Decimal(str(l.get('delivered', l['quantity'])))
            rest = Decimal(str(l['quantity'])) - done
            want = [('ordered', l['quantity']), ('delivered', done)] + ([('outstanding', rest)] if rest else [])
        else:
            want = [('quantity', l['quantity']), ('unit price', l['unit_price']), ('net', l['net'])]
        ok = False
        for i, r in rows:
            nums = numbers(r.replace(l.get('code') or '\0', ' '))
            missing = [k for k, v in want if not has(nums, v)]
            if not missing:
                ok = True
                if doc.kind == 'xlsx' and t['doc'] != 'delivery_note' and not any(abs(f - l['net']) <= TOL for f in doc.formulas.get(i, [])):
                    bad.append('line %s: net amount is typed in, not a formula' % name)
                break
        if not ok:
            bad.append('line %s: %s not found on its row' % (name, ', '.join(missing)))
    return fails(bad, '%d lines complete' % len(lines))


def trd_totals(doc, t):
    lines, vat, net, tax, gross = expected(t)
    bad = []
    want = [('total excluding VAT', net), ('total including VAT', gross)]
    for rate, (base, amount) in vat.items():
        if rate > 0:
            want += [('VAT %s%%' % rate.normalize(), amount)]
    if tax > 0:
        want.append(('total VAT', tax))
    for label, value in want:
        if not has(doc.nums, value):
            bad.append('%s %s not stated' % (label, value))
    if tax == 0:
        said = re.search(r'\b0(\.0+)?\s?%|zero[\s-]rated|vat\s*:?\s*0\b|0[.,]00', doc.flat, re.I)
        shown = any(re.search(r'\bvat\b|\btax\b', r, re.I) and has(numbers(re.sub(r'[A-Za-z]+-?\d+', ' ', r)), 0) for r in doc.rows)
        if not (said or shown):
            bad.append('VAT at 0 is not stated')
    if doc.kind == 'xlsx' and not bad:
        forms = [f for fs in doc.formulas.values() for f in fs]
        for label, value in want:
            if not any(abs(f - value) <= TOL for f in forms):
                bad.append('%s is typed in, not a formula' % label)
    return fails(bad, 'totals right: %s net, %s VAT, %s gross' % (net, tax, gross))


def trd_dates(doc, t):
    bad = ['%s %s missing' % (label, iso) for label, iso in t.get('dates', {}).items() if not has_date(doc, iso, strict=False)]
    return fails(bad, '%d dates present' % len(t.get('dates', {})))


def trd_pay(doc, t):
    bad = ['payment terms: nothing matching %r' % p for p in t.get('payment', []) if not re.search(p, doc.flat, re.I)]
    return fails(bad, 'payment terms stated')


def trd_ship(doc, t):
    bad = []
    n = t['packages']
    if not re.search(r'(packages?|parcels?|colli|kolli|packst\u00fccke?|pieces|pallets?|cartons?)\D{0,45}\b%d\b|\b%d\b\s*(packages?|parcels?|colli|kolli)' % (n, n), doc.flat, re.I):
        bad.append('number of packages %d not stated' % n)
    w = Decimal(str(t['gross_weight_kg']))
    if not re.search(r'\b%s(?:[.,]0+)?\s?kg\b' % re.escape(str(w.normalize() if w == w.to_integral_value() else w)).replace(r'\.', '[.,]'), doc.flat, re.I):
        bad.append('gross weight %s kg not stated' % w)
    if not re.search(r'signature|received (in good order )?by|receiver|goods received|unterschrift|underskrift', doc.flat, re.I):
        bad.append('no place to sign for receipt')
    return fails(bad, 'packages, weight and signature line present')


def trd_noprice(doc, t):
    bad = []
    for v in t.get('prices', []):
        if has(doc.nums, v) and Decimal(str(v)) not in [Decimal(str(x)) for x in t.get('allowed_numbers', [])]:
            bad.append('amount %s appears' % v)
    if re.search(r'\b(SEK|EUR|USD|NOK|DKK|kr)\b|[€$£]|unit price|net amount|total (excluding|including)|einzelpreis|nettobetrag|'
                 r'\u00e0-pris|enhedspris|exkl\. moms|ekskl\. moms', doc.flat, re.I):
        bad.append('a price column, total or currency appears')
    return fails(bad, 'no prices on the delivery note')


def trd_customs(doc, t):
    bad = []
    for l in t['lines']:
        if not l.get('hs_code'):
            continue
        rows = line_rows(doc, l)
        hs = re.sub(r'\D', '', l['hs_code'])
        if not any(hs in re.sub(r'[^\d|]', '', r) and l['origin'].lower() in r.lower() for _, r in rows):
            bad.append('line %s: HS code %s or origin %s not on its row' % (l.get('code'), l['hs_code'], l['origin']))
    return fails(bad, 'customs code and origin on every goods line')


def trd_stale(doc, t):
    bad = []
    for s in t.get('stale', []):
        if isinstance(s, (int, float)) or re.fullmatch(r'\d+(\.\d+)?', str(s)):
            if has(doc.nums, s):
                bad.append('old amount %s still there' % s)
        elif re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(s)):
            if has_date(doc, s, strict=False):
                bad.append('old date %s still there' % s)
        elif re.search(str(s), doc.flat, re.I):
            bad.append('old text %r still there' % s)
    bad += ['%r missing' % m for m in t.get('must', []) if not re.search(m, doc.flat, re.I)]
    return fails(bad, 'nothing replaced by the revision is left')


def inco_1(doc, t):
    term = t['incoterm']
    m = re.search(r'\b%s\b[\s,:(-]*([^|\n]{2,70}?)[\s,;(-]*Incoterms\s?[®(R)]{0,3}\s?2020' % term['rule'], doc.flat)
    if not m:
        m = re.search(r'Incoterms\s?[®(R)]{0,3}\s?2020[\s,:;)(-]*\b%s\b[\s,:(-]*([^|\n]{2,40})' % term['rule'], doc.flat)
    if not m:
        found = re.findall(r'\b(?:%s)\b[^|\n]{0,60}' % '|'.join(RULES_ANY + RULES_SEA + OLD_RULES), doc.flat)
        return False, 'expected "%s %s, Incoterms 2020"; found %r' % (term['rule'], term['place'], [f[:60] for f in found[:3]] or 'no delivery term')
    if term['place'].split(',')[0].lower() not in m.group(1).lower():
        return False, 'named place %s missing after %s: %r' % (term['place'], term['rule'], m.group(0)[:80])
    old = [r for r in OLD_RULES if re.search(r'\b%s\b' % r, doc.flat)]
    if old:
        return False, '%s is not an Incoterms 2020 rule' % ', '.join(old)
    return True, m.group(0)[:90]


def inco_2(doc, t):
    if t.get('transport', 'road') in ('sea', 'inland waterway'):
        return True, 'goods travel by sea'
    used = [r for r in RULES_SEA if re.search(r'\b%s\b' % r, doc.flat)]
    return (not used), ('no sea-only rule used' if not used else '%s is a sea-only rule; the goods travel by %s' % (', '.join(used), t.get('transport', 'road')))


RULES = {'TRD-TYPE': trd_type, 'TRD-HEAD': trd_head, 'TRD-REFS': trd_refs, 'TRD-LINES': trd_lines, 'TRD-TOTALS': trd_totals,
         'TRD-DATES': trd_dates, 'TRD-PAY': trd_pay, 'TRD-SHIP': trd_ship, 'TRD-NOPRICE': trd_noprice, 'TRD-CUSTOMS': trd_customs,
         'TRD-STALE': trd_stale, 'INCO-1': inco_1, 'INCO-2': inco_2}


def check(rule_id, path, case, stage):
    if rule_id not in RULES:
        raise KeyError('unknown rule %s' % rule_id)
    try:
        doc = Doc(path)
    except Skip as e:
        return None, 'not run: %s' % e
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, ET.ParseError) as e:
        return False, 'unreadable file: %s' % e
    return RULES[rule_id](doc, truth(case, stage))


def main(argv):
    args, case, stage, rules = list(argv), None, 'first', []
    try:
        path = Path(args.pop(0))
        while args:
            a = args.pop(0)
            if a == '--case':
                case = json.loads(Path(args.pop(0)).read_text())
            elif a == '--stage':
                stage = args.pop(0)
            else:
                rules.append(a)
        if case is None:
            raise IndexError('--case is needed')
    except (IndexError, OSError, json.JSONDecodeError) as e:
        print(__doc__, file=sys.stderr)
        print('error: %s' % e, file=sys.stderr)
        return 2
    rules = rules or [c['rule'] for c in case.get('criteria', []) if c.get('script') == 'trade.py' and c['stage'] in ('both', stage)]
    ok = True
    for r in rules:
        passed, evidence = check(r, path, case, stage)
        ok &= passed is not False
        print(json.dumps(dict(rule=r, passed=passed, evidence=evidence), ensure_ascii=False))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
