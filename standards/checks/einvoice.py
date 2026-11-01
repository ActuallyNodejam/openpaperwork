"""EN 16931 e-invoice checks for a Cross Industry Invoice XML file. Standard library only.

check(rule_id, path, case, stage) -> (passed, evidence). passed is None when the validator is absent.

EINV-VALID   The file validates as an EN 16931 invoice in the Mustang validator, with no errors.
EINV-HEAD    Number, dates, parties, VAT IDs and currency match the case.
EINV-LINES   Every order line is present with its quantity and net amount.
EINV-VAT     The VAT breakdown has one entry per category and rate with the right base and amount.
EINV-TOTALS  Totals without VAT, VAT and with VAT are right.

Mustang (Apache-2.0) is a separate tool and none of it is in this repository. Point
FILETASK_MUSTANG_JAR at Mustang-CLI-<version>.jar; it runs in the container image named by
FILETASK_JAVA_IMAGE (default eclipse-temurin:21-jre) with no network and read-only mounts.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree as ET

RSM = '{urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100}'
RAM = '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}'
UDT = '{urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100}'
TOL = Decimal('0.006')


def dec(text):
    try:
        return Decimal((text or '').strip())
    except Exception:
        return None


def close(a, b):
    return a is not None and abs(a - b) <= TOL


def iso(el):
    s = el.find(UDT + 'DateTimeString') if el is not None else None
    t = (s.text or '').strip() if s is not None else ''
    return '%s-%s-%s' % (t[:4], t[4:6], t[6:8]) if len(t) == 8 else t


def read(path):
    root = ET.parse(path).getroot()
    if root.tag != RSM + 'CrossIndustryInvoice':
        raise ValueError('root element is %s, not a Cross Industry Invoice' % root.tag.split('}')[-1])
    f = lambda node, p: node.find(p.replace('ram:', RAM).replace('rsm:', RSM)) if node is not None else None
    t = lambda node, p: ((f(node, p).text or '').strip() if f(node, p) is not None else '')
    doc = f(root, 'rsm:ExchangedDocument')
    tx = f(root, 'rsm:SupplyChainTradeTransaction')
    agr, st = f(tx, 'ram:ApplicableHeaderTradeAgreement'), f(tx, 'ram:ApplicableHeaderTradeSettlement')

    def party(tag):
        p = f(agr, 'ram:' + tag)
        return dict(name=t(p, 'ram:Name'), vat=t(p, 'ram:SpecifiedTaxRegistration/ram:ID'), country=t(p, 'ram:PostalTradeAddress/ram:CountryID'))
    lines = []
    for item in tx.findall(RAM + 'IncludedSupplyChainTradeLineItem'):
        lines.append(dict(name=t(item, 'ram:SpecifiedTradeProduct/ram:Name'),
                          qty=dec(t(item, 'ram:SpecifiedLineTradeDelivery/ram:BilledQuantity')),
                          net=dec(t(item, 'ram:SpecifiedLineTradeSettlement/ram:SpecifiedTradeSettlementLineMonetarySummation/ram:LineTotalAmount')),
                          rate=dec(t(item, 'ram:SpecifiedLineTradeSettlement/ram:ApplicableTradeTax/ram:RateApplicablePercent')),
                          cat=t(item, 'ram:SpecifiedLineTradeSettlement/ram:ApplicableTradeTax/ram:CategoryCode')))
    vat = [dict(cat=t(x, 'ram:CategoryCode'), rate=dec(t(x, 'ram:RateApplicablePercent')) or Decimal(0), base=dec(t(x, 'ram:BasisAmount')),
                amount=dec(t(x, 'ram:CalculatedAmount')), reason=t(x, 'ram:ExemptionReason'))
           for x in st.findall(RAM + 'ApplicableTradeTax')]
    tot = f(st, 'ram:SpecifiedTradeSettlementHeaderMonetarySummation')
    return dict(number=t(doc, 'ram:ID'), issue=iso(f(doc, 'ram:IssueDateTime')),
                due=iso(f(st, 'ram:SpecifiedTradePaymentTerms/ram:DueDateDateTime')), currency=t(st, 'ram:InvoiceCurrencyCode'),
                seller=party('SellerTradeParty'), buyer=party('BuyerTradeParty'), lines=lines, vat=vat,
                net=dec(t(tot, 'ram:TaxBasisTotalAmount')), tax=dec(t(tot, 'ram:TaxTotalAmount')), gross=dec(t(tot, 'ram:GrandTotalAmount')))


def mustang(path):
    jar = os.environ.get('FILETASK_MUSTANG_JAR')
    image = os.environ.get('FILETASK_JAVA_IMAGE', 'eclipse-temurin:21-jre')
    if not jar or not Path(jar).is_file() or not shutil.which('docker'):
        return None, 'skipped: the Mustang validator is not available (set FILETASK_MUSTANG_JAR)'
    work = Path(tempfile.mkdtemp(prefix='einv-'))
    try:
        shutil.copyfile(path, work / 'invoice.xml')
        os.chmod(work, 0o755)
        os.chmod(work / 'invoice.xml', 0o644)
        p = subprocess.run(['docker', 'run', '--rm', '--network', 'none', '-v', '%s:/tools/mustang.jar:ro' % jar, '-v', '%s:/data:ro' % work, image,
                            'java', '-jar', '/tools/mustang.jar', '--action', 'validate', '--source', '/data/invoice.xml', '--disable-file-logging'],
                           capture_output=True, text=True, timeout=300)
        status = re.findall(r'<summary status="([a-z]+)"', p.stdout)
        if not status:
            return None, 'skipped: the validator gave no report (%s)' % (p.stderr or p.stdout)[-120:].strip()
        errors = [re.sub(r'\s+', ' ', e)[:150] for e in re.findall(r'<error[^>]*>([^<]*)', p.stdout)]
        if status[-1] == 'valid':
            return True, 'Mustang: valid EN 16931 invoice'
        return False, 'Mustang: invalid; ' + '; '.join(dict.fromkeys(errors))[:400]
    finally:
        shutil.rmtree(work, ignore_errors=True)


def check(rule_id, path, case, stage):
    if rule_id == 'EINV-VALID':
        return mustang(path)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import invoice
    try:
        inv = read(path)
    except (ET.ParseError, ValueError, AttributeError) as e:
        return False, 'not a readable Cross Industry Invoice: %s' % e
    lines, vat, (net, tax, gross) = invoice.expected(case, stage)
    t = case['truth']
    if rule_id == 'EINV-HEAD':
        want = dict(t['header']['first'], **(t['header'][stage] if stage != 'first' else {}))
        got = {'Invoice number': inv['number'], 'Issue date': inv['issue'], 'Due date': inv['due'], 'Seller': inv['seller']['name'],
               'Seller VAT ID': inv['seller']['vat'], 'Buyer': inv['buyer']['name'], 'Buyer VAT ID': inv['buyer']['vat'], 'Currency': inv['currency']}
        for k, v in want.items():
            if v.lower() not in (got.get(k) or '').lower():
                return False, '%s is "%s", expected "%s"' % (k, got.get(k), v)
        return True, '%d header values match' % len(want)
    if rule_id == 'EINV-LINES':
        if len(inv['lines']) != len(lines):
            return False, '%d lines, expected %d' % (len(inv['lines']), len(lines))
        for l in lines:
            row = next((x for x in inv['lines'] if x['name'].strip().lower() == l['desc'].lower()), None)
            if row is None:
                return False, 'line "%s" is missing' % l['desc']
            if not close(row['qty'], l['qty']) or not close(row['net'], l['net']) or not close(row['rate'] if row['rate'] is not None else Decimal(0), l['rate']):
                return False, '%s: quantity %s, net %s, rate %s; expected %s, %s, %s' % (l['desc'], row['qty'], row['net'], row['rate'], l['qty'], l['net'], l['rate'])
        return True, '%d lines match' % len(lines)
    if rule_id == 'EINV-VAT':
        got = {x['rate'].normalize(): x for x in inv['vat']}
        if {k.normalize() for k in vat} != set(got):
            return False, 'VAT rates are %s, expected %s' % (sorted(str(k) for k in got), sorted(str(k) for k in vat))
        for rate, (base, amount) in vat.items():
            x = got[rate.normalize()]
            if not close(x['base'], base) or not close(x['amount'], amount):
                return False, 'rate %s: base %s and VAT %s, expected %s and %s' % (rate, x['base'], x['amount'], base, amount)
        want_cat = t.get('vat_category', {}).get(stage)
        if want_cat and any(x['cat'] != want_cat for x in inv['vat']):
            return False, 'VAT category is %s, expected %s' % (sorted({x['cat'] for x in inv['vat']}), want_cat)
        return True, '%d VAT entries match' % len(vat)
    if rule_id == 'EINV-TOTALS':
        for name, g, e in (('total without VAT', inv['net'], net), ('total VAT', inv['tax'], tax), ('total with VAT', inv['gross'], gross)):
            if not close(g, e):
                return False, '%s is %s, expected %s' % (name, g, e)
        return True, 'totals %s, %s and %s match' % (net, tax, gross)
    return False, 'unknown rule %s' % rule_id
