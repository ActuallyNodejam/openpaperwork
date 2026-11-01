#!/usr/bin/env python3
"""openpaperwork-checks: the pack checks as one MCP server over stdio, and the same checks from a shell.

  python3 server.py                          serve MCP (JSON-RPC 2.0, one message per line)
  python3 server.py --check FILE [--kit KIT.json] [--slides N]

One tool, check_file. It runs the every-file floor on a .docx, .xlsx or .pptx, and the brand-kit
rules as well when a kit file is given. The check code is checks/floor.py and checks/brandkit.py,
the same modules the library's cases in standards/ are checked with. Needs python-docx, python-pptx and
openpyxl. The PDF/UA rule of the floor is not here: it needs veraPDF, a separate tool.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'checks'))

FLOOR = [('FLOOR-FONT', 'At most two font families in the file.', ('docx', 'xlsx', 'pptx')),
         ('FLOOR-OVERFLOW', 'No text overflows its slide shape, and no cell text or number is cut.', ('xlsx', 'pptx')),
         ('FLOOR-OVERLAP', 'No slide text is hidden behind a picture or an opaque shape.', ('pptx',)),
         ('FLOOR-CONTRAST', 'Coloured text has a contrast of at least 4.5:1, or 3:1 for large text.', ('docx', 'xlsx', 'pptx')),
         ('FLOOR-FORMULA', 'Every formula has a saved result and none is an error value.', ('xlsx',)),
         ('FLOOR-META', 'The file has a title; slides have titles; pictures have alternative text; sheets are named; documents declare a language.', ('docx', 'xlsx', 'pptx'))]
KIT = [('KIT-RATIO', 'The slide size has the kit ratio.'), ('KIT-COUNT', 'The deck has the number of slides asked for.'),
       ('KIT-FONT', 'Every text run resolves to a kit font.'), ('KIT-COLOR', 'Every colour on a slide is in the palette and every text run has a palette colour set.'),
       ('KIT-WORDS', 'No slide is over the word or body-paragraph limit (footer exempt).'), ('KIT-MINPT', 'No text run is under the minimum size (footer exempt).'),
       ('KIT-FOOTER', 'The footer text is on every slide.'), ('KIT-TITLE', 'Every slide has text in a title placeholder.'),
       ('KIT-BOUNDS', 'No shape extends past the slide edge.'), ('KIT-PLAIN', 'Nothing decorative: no drawn shape without text and no shadow, unless the kit style asks for a title rule.')]

TOOL = {
    'name': 'check_file',
    'description': 'Check a finished .docx, .xlsx or .pptx against the every-file floor (fonts, overflow, hidden text, contrast, '
                   'formulas, title and alternative text). Give kit, the path of a brand kit JSON file, to check a deck against '
                   'that kit as well. Returns each rule with pass or fail and what was found. Call it before delivering a file, '
                   'fix what fails, and call it again.',
    'inputSchema': {'type': 'object', 'required': ['path'], 'properties': {
        'path': {'type': 'string', 'description': 'Absolute path of the file to check.'},
        'kit': {'type': 'string', 'description': 'Absolute path of a brand kit JSON file. Decks only.'},
        'slides': {'type': 'integer', 'description': 'The number of slides the deck should have, when the request names one.'}}}}


def run_checks(path, kit=None, slides=None):
    p = Path(path)
    if not p.is_file():
        return {'ok': False, 'error': 'no file at %s' % path}
    ext = p.suffix.lower().lstrip('.')
    if ext not in ('docx', 'xlsx', 'pptx'):
        return {'ok': False, 'error': 'only .docx, .xlsx and .pptx files are checked'}
    import floor
    rules = []
    for rid, text, formats in FLOOR:
        if ext not in formats:
            continue
        try:
            passed, evidence = floor.check(rid, str(p), {}, 'first')
        except Exception as e:  # a file the check cannot read is a failure the agent should see
            passed, evidence = False, 'could not be checked: %s' % e
        rules.append({'rule': rid, 'passed': bool(passed), 'found': evidence, 'text': text})
    if kit:
        if ext != 'pptx':
            return {'ok': False, 'error': 'a kit is checked against a .pptx deck only'}
        import brandkit
        k = json.loads(Path(kit).read_text())
        palette = k.get('palette') or []
        if isinstance(palette, dict):
            palette = list(palette.values())
        case = {'truth': {'kit': k, 'palette': {'first': palette}, 'slides': {'first': slides}}}
        for rid, text in KIT:
            if rid == 'KIT-COUNT' and not slides:
                continue
            try:
                passed, evidence = brandkit.check(rid, str(p), case, 'first')
            except Exception as e:
                passed, evidence = False, 'could not be checked: %s' % e
            rules.append({'rule': rid, 'passed': bool(passed), 'found': evidence, 'text': text})
    failed = [r['rule'] for r in rules if not r['passed']]
    return {'ok': not failed, 'file': str(p), 'passed': len(rules) - len(failed), 'of': len(rules), 'failed': failed, 'rules': rules}


def serve():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        mid, method = msg.get('id'), msg.get('method')
        if mid is None:
            continue  # a notification takes no reply
        if method == 'initialize':
            result = {'protocolVersion': (msg.get('params') or {}).get('protocolVersion', '2024-11-05'),
                      'capabilities': {'tools': {}}, 'serverInfo': {'name': 'openpaperwork-checks', 'version': '0.1.0'}}
        elif method == 'ping':
            result = {}
        elif method == 'tools/list':
            result = {'tools': [TOOL]}
        elif method == 'tools/call':
            params = msg.get('params') or {}
            a = params.get('arguments') or {}
            if params.get('name') != 'check_file':
                out = {'ok': False, 'error': 'unknown tool'}
            else:
                try:
                    out = run_checks(a.get('path', ''), a.get('kit'), a.get('slides'))
                except Exception as e:
                    out = {'ok': False, 'error': str(e)}
            result = {'content': [{'type': 'text', 'text': json.dumps(out, indent=1, ensure_ascii=False)}], 'isError': 'error' in out}
        else:
            sys.stdout.write(json.dumps({'jsonrpc': '2.0', 'id': mid, 'error': {'code': -32601, 'message': 'method not found'}}) + '\n')
            sys.stdout.flush()
            continue
        sys.stdout.write(json.dumps({'jsonrpc': '2.0', 'id': mid, 'result': result}) + '\n')
        sys.stdout.flush()


def main(argv):
    if '--check' in argv:
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument('--check', required=True)
        ap.add_argument('--kit')
        ap.add_argument('--slides', type=int)
        a = ap.parse_args(argv)
        out = run_checks(a.check, a.kit, a.slides)
        print(json.dumps(out, indent=1, ensure_ascii=False))
        return 0 if out.get('ok') else 1
    serve()
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
