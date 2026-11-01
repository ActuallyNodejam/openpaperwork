#!/usr/bin/env python3
"""Offline file-task preparation and partial mechanical grading. No model calls."""
import argparse
import csv
import hashlib
import json
import re
import shutil
import sys
import zipfile
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def case_info(case_id):
    paths = {x['id']: x['path'] for x in json.loads((ROOT / 'catalogue.json').read_text())}
    if case_id not in paths:
        raise ValueError('Unknown case ID')
    folder = ROOT / paths[case_id]
    return folder, json.loads((folder / 'case.json').read_text())


def hashes(folder):
    return {str(p.relative_to(folder)): sha(p) for p in sorted(folder.rglob('*')) if p.is_file()}


def prepare(case_id, dest):
    folder, case = case_info(case_id)
    if ROOT.parent == dest or ROOT.parent in dest.parents:
        raise ValueError('Run directory must be outside the source checkout')
    dest.mkdir(parents=True, exist_ok=False)
    shutil.copytree(folder / 'inputs', dest / 'task' / 'inputs')
    shutil.copyfile(folder / 'request.md', dest / 'task' / 'request.md')
    for stage in ('first', 'revision'):
        (dest / stage).mkdir()
    metrics = dict(wall_seconds=None, human_active_seconds=None, interruptions=None,
                   retries=None, model_cost_usd=None, tool_cost_usd=None,
                   cost_basis=None, transcript=None)
    save(dest / 'run.json', dict(protocol_version='0.1', case_id=case_id,
         case_version=case['version'], source_hashes=hashes(folder),
         product_commit=None, model=None, model_version=None, tools=None,
         skills_version=None, grader_sha256=sha(Path(__file__)), runtime=None,
         attempts={'first': dict(metrics), 'revision': dict(metrics)},
         first_frozen_sha256=None))
    print('Prepared. Give the agent only task/ and its output destination, not this repository.')


def load_run(dest):
    run = json.loads((dest / 'run.json').read_text())
    folder, case = case_info(run['case_id'])
    if run['case_version'] != case['version'] or run['source_hashes'] != hashes(folder):
        raise ValueError('Case source differs from the prepared version; preserve this run and prepare a new one')
    if run['grader_sha256'] != sha(Path(__file__)):
        raise ValueError('Grader differs from the prepared version; use the original grader or record a separate regrade')
    return run, folder, case


def reveal(dest):
    run, folder, case = load_run(dest)
    original = dest / 'first' / case['output']
    if not original.is_file() or original.is_symlink():
        raise ValueError('Save a regular first output file before revealing the revision')
    digest = sha(original)
    if run['first_frozen_sha256'] and run['first_frozen_sha256'] != digest:
        raise ValueError('The frozen first output changed')
    run['first_frozen_sha256'] = digest
    extras = {}
    for name in case.get('extra_outputs', []):
        extra = dest / 'first' / name
        if not extra.is_file() or extra.is_symlink():
            raise ValueError('Save %s beside the first output before revealing the revision' % name)
        extras[name] = sha(extra)
    run['first_frozen_extra'] = extras
    save(dest / 'run.json', run)
    shutil.copyfile(folder / 'revision.md', dest / 'task' / 'revision.md')
    print('First artifact hash frozen. Revision revealed in task/revision.md; keep first/ unchanged.')


def cells(z, sheet):
    shared = []
    if 'xl/sharedStrings.xml' in z.namelist():
        shared = [''.join(e.itertext()) for e in ET.fromstring(z.read('xl/sharedStrings.xml'))]
    root = ET.fromstring(z.read(sheet))
    rows = []
    for row in root.findall('.//s:sheetData/s:row', NS):
        values = {}
        for cell in row.findall('s:c', NS):
            raw = cell.findtext('s:v', default='', namespaces=NS)
            kind = cell.get('t')
            if kind == 's':
                raw = shared[int(raw)]
            if kind == 'inlineStr':
                raw = ''.join(cell.find('s:is', NS).itertext())
            col = re.sub(r'\d+', '', cell.attrib['r'])
            values[col] = (raw, cell.find('s:f', NS) is not None)
        rows.append(values)
    return rows


def sheet_checks(z, folder, stage, add):
    workbook = ET.fromstring(z.read('xl/workbook.xml'))
    rels = {r.attrib['Id']: r.attrib['Target'] for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
    sheets = {}
    for item in workbook.findall('s:sheets/s:sheet', NS):
        target = rels[item.attrib['{' + NS['r'] + '}id']]
        sheets[item.attrib['name'].lower()] = target.lstrip('/') if target.startswith('/') else 'xl/' + target
    add('comparison_and_recommendation_sheets', 'comparison' in sheets and 'recommendation' in sheets)
    if 'comparison' not in sheets or 'recommendation' not in sheets:
        return
    rows = cells(z, sheets['comparison'])
    required = ['Supplier', 'Quantity', 'Unit price EUR', 'Shipping EUR', 'Total EUR', 'Delivery date', 'Eligible']
    header = next((i for i, row in enumerate(rows) if {v[0].strip().lower() for v in row.values()} >= {x.lower() for x in required}), None)
    add('required_columns', header is not None)
    if header is None:
        return
    cols = {value[0].strip().lower(): key for key, value in rows[header].items()}
    expected = list(csv.DictReader((folder / 'inputs/quotes.csv').read_text().splitlines()))
    if stage == 'revision':
        expected[2]['Unit price EUR'] = '49.00'
        expected[2]['Delivery date'] = '2026-11-13'
    epoch1904 = workbook.find('s:workbookPr', NS)
    epoch = date(1904, 1, 1) if epoch1904 is not None and epoch1904.get('date1904') in ('1', 'true') else date(1899, 12, 30)
    for quote in expected:
        name = quote['Supplier']
        match = [r for r in rows[header + 1:] if r.get(cols['supplier'], ('', False))[0].strip() == name]
        add(name + ':single_row', len(match) == 1)
        if len(match) != 1:
            continue
        row = match[0]
        for field in ('Quantity', 'Unit price EUR', 'Shipping EUR'):
            value = row.get(cols[field.lower()], ('', False))[0]
            add(name + ':' + field, Decimal(value) == Decimal(quote[field]))
        total, formula = row.get(cols['total eur'], ('', False))
        amount = Decimal(quote['Quantity']) * Decimal(quote['Unit price EUR']) + Decimal(quote['Shipping EUR'])
        add(name + ':total_formula_present', formula)
        add(name + ':cached_total', Decimal(total) == amount)
        delivery = row.get(cols['delivery date'], ('', False))[0]
        if re.fullmatch(r'\d+(\.0+)?', delivery):
            delivery = (epoch + timedelta(days=int(Decimal(delivery)))).isoformat()
        add(name + ':delivery_date', delivery == quote['Delivery date'])
    recommendation = cells(z, sheets['recommendation'])
    add('recommendation_has_text', any(v[0].strip() for row in recommendation for v in row.values()))


def check(dest, stage):
    run, folder, case = load_run(dest)
    findings = []
    def add(name, passed):
        findings.append({'check': name, 'passed': bool(passed)})
    output = dest / stage / case['output']
    add('regular_output_file', output.is_file() and not output.is_symlink())
    if stage == 'revision' or run['first_frozen_sha256']:
        first = dest / 'first' / case['output']
        add('revision_revealed_and_first_preserved', bool(run['first_frozen_sha256']) and first.is_file() and sha(first) == run['first_frozen_sha256'])
    for name in case.get('extra_outputs', []):
        extra = dest / stage / name
        add('extra_output:' + name, extra.is_file() and not extra.is_symlink())
        frozen = (run.get('first_frozen_extra') or {}).get(name)
        if frozen:
            first_extra = dest / 'first' / name
            add('first_extra_preserved:' + name, first_extra.is_file() and sha(first_extra) == frozen)
    if case['format'] == 'pdf':
        # A PDF is not an Office package: check the file signature here; pages and text are graded elsewhere.
        if output.is_file() and not output.is_symlink():
            add('pdf_header', output.read_bytes()[:5] == b'%PDF-' and output.stat().st_size <= 50_000_000)
    elif case['format'] == 'xml':
        if output.is_file() and not output.is_symlink():
            try:
                ET.fromstring(output.read_bytes())
                add('xml_well_formed', output.stat().st_size <= 50_000_000)
            except ET.ParseError as error:
                findings.append({'check': 'xml_well_formed', 'passed': False, 'detail': str(error)})
    elif case["format"] == "html":
        try:
            from html.parser import HTMLParser

            class Pages(HTMLParser):
                def __init__(self):
                    HTMLParser.__init__(self)
                    self.pages = 0

                def handle_starttag(self, tag, attrs):
                    classes = " ".join(v or "" for k, v in attrs if k == "class")
                    tokens = set(classes.split())
                    if tag in ("section", "div", "article") and (tokens & {"page", "slide", "sheet", "deck-page"}):
                        self.pages += 1

            parser = Pages()
            parser.feed(output.read_text(errors="ignore"))
            add("html_well_formed", True)
            findings.append({"check": "html_has_pages", "passed": parser.pages > 0,
                             "detail": "%d page element(s)" % parser.pages})
        except Exception as error:
            findings.append({"check": "html_well_formed", "passed": False, "detail": str(error)})
    elif case["format"] == "json":
        # A deck arrives as the JSON its builder takes, so check the JSON parses and that the
        # builder can turn it into pages without being told anything else.
        try:
            import json as _json
            spec = _json.loads(output.read_text())
            add("json_well_formed", True)
            pages = spec.get("pages") or []
            findings.append({"check": "json_has_pages", "passed": bool(pages),
                             "detail": "%d page(s) declared" % len(pages)})
            known = {"cover", "numbers", "chart-bullets", "table", "timeline", "closing"}
            unknown = [pg.get("type") for pg in pages if pg.get("type") not in known]
            findings.append({"check": "json_page_types_known", "passed": not unknown,
                             "detail": "unknown: %s" % ", ".join(map(str, unknown)) if unknown else "all known"})
        except Exception as error:
            findings.append({"check": "json_well_formed", "passed": False, "detail": str(error)})
    elif case["format"] == "tex":
        try:
            text = output.read_text(errors="ignore")
            add("tex_documentclass", "\\documentclass" in text)
            add("tex_braces_balanced", text.count("{") == text.count("}"))
        except Exception as error:
            findings.append({"check": "tex_well_formed", "passed": False, "detail": str(error)})
    elif output.is_file() and not output.is_symlink():
        try:
            if output.stat().st_size > 50_000_000:
                raise ValueError('Output exceeds this starter checker limit of 50 MB')
            with zipfile.ZipFile(output) as z:
                if sum(i.file_size for i in z.infolist()) > 100_000_000:
                    raise ValueError('Expanded package exceeds 100 MB')
                ET.fromstring(z.read('[Content_Types].xml'))
                ET.fromstring(z.read('_rels/.rels'))
                add('package_xml_readable', True)
                if case['format'] == 'docx':
                    doc = ET.fromstring(z.read('word/document.xml'))
                    add('editable_document_text', any((e.text or '').strip() for e in doc.findall('.//w:t', NS)))
                if case['format'] == 'pptx':
                    presentation = ET.fromstring(z.read('ppt/presentation.xml'))
                    slides = case.get('slides', 5)
                    if isinstance(slides, dict):
                        slides = slides[stage]
                    add('slide_count', len(presentation.findall('p:sldIdLst/p:sldId', NS)) == slides)
                    parts = [n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)]
                    add('slide_parts', len(parts) == slides)
                    add('editable_slide_text', len(parts) == slides and all(ET.fromstring(z.read(n)).findall('.//a:t', NS) for n in parts))
                if case['format'] == 'xlsx' and case.get('sheet_checks') == 'quotes':
                    sheet_checks(z, folder, stage, add)
        except (ValueError, KeyError, IndexError, TypeError, AttributeError, zipfile.BadZipFile, ET.ParseError, InvalidOperation) as error:
            findings.append({'check': 'package_inspection', 'passed': False, 'detail': str(error)})
    passed = all(x['passed'] for x in findings)
    report = dict(case_id=case['id'], case_version=case['version'], stage=stage,
                  output_sha256=sha(output) if output.is_file() and not output.is_symlink() else None,
                  grader_sha256=sha(Path(__file__)), mechanical_pass=passed,
                  acceptance='needs_review' if passed else 'mechanical_failure', findings=findings,
                  required_review=case['review'] + (case['revised_review'] if stage == 'revision' else []),
                  metrics=run['attempts'][stage], warning='No layout, semantic or recalculation acceptance is inferred.')
    save(dest / 'reports' / (stage + '.json'), report)
    print(json.dumps(report, indent=2))
    return 0 if passed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare'); p.add_argument('case_id'); p.add_argument('directory', type=Path)
    p = sub.add_parser('revision'); p.add_argument('directory', type=Path)
    p = sub.add_parser('check'); p.add_argument('directory', type=Path); p.add_argument('stage', choices=['first', 'revision'])
    args = parser.parse_args()
    dest = args.directory.resolve()
    try:
        if args.command == 'prepare': prepare(args.case_id, dest)
        if args.command == 'revision': reveal(dest)
        if args.command == 'check': return check(dest, args.stage)
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
