#!/usr/bin/env python3
"""Mechanical checks for a paper handed back as PDF with its source beside it. Standard library only.

check(rule_id, path, case, stage) -> (passed, evidence). path is the PDF; the source is the .tex with the
same name in the same folder. passed is None when a check could not run (no TeX engine, no poppler, or a
lookup service down), so an outage is never counted as a miss. Rules belong to
guidelines/ieee-conference/1.8b and guidelines/acm-sigconf/2.20, plus CASE-REFS-REAL.

Needs pdfinfo and pdftotext (poppler) for the PDF rules and tectonic on PATH, or its path in
PAPERCHECK_ENGINE, for the build rule. The reference lookup calls Crossref, OpenAlex and arXiv and writes
what they returned to refs-evidence.json beside the PDF.

CLI: python3 papercheck.py PAPER.pdf [--case case.json] [--stage first|revision] [RULE ...]
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from xml.etree import ElementTree as ET

UA = 'OpenPaperwork-papercheck/0.1 (+https://github.com/ActuallyNodejam/openpaperwork)'
PROFILES = {
    'IEEEC': dict(cls='IEEEtran', option='conference', keywords=r'\\begin\{IEEEkeywords\}', keywords_name='Index Terms',
                  extra=[], sizes=('9pt', '11pt', '12pt')),
    'ACMC': dict(cls='acmart', option='sigconf', keywords=r'\\keywords\{', keywords_name='Keywords',
                 extra=[(r'\\ccsdesc', 'CCS Concepts')], sizes=('10pt', '11pt', '12pt')),
}
PLACEHOLDERS = ('TITLE OF THE PAPER', 'ABSTRACT, one paragraph', 'first keyword, second keyword', 'Title of the article')


class Skip(Exception):
    """The check could not run; returned as None."""


class Problem(Exception):
    pass


def truth(case, stage):
    t = (case or {}).get('truth', {})
    return {**{k: v for k, v in t.items() if k not in ('first', 'revision')}, **(t.get(stage) or {})}


def source(path):
    tex = Path(path).with_suffix('.tex')
    if not tex.is_file():
        raise Problem('no %s beside the PDF' % tex.name)
    raw = tex.read_text(errors='replace')
    return tex, re.sub(r'(?<!\\)%.*', '', raw)


def tool(name):
    found = shutil.which(name)
    if not found:
        raise Skip('%s is not installed' % name)
    return found


def pdf_text(path):
    p = subprocess.run([tool('pdftotext'), str(path), '-'], capture_output=True, text=True, timeout=120)
    if p.returncode:
        raise Problem('pdftotext failed: %s' % p.stderr.strip()[:200])
    return p.stdout


def pdf_info(path):
    p = subprocess.run([tool('pdfinfo'), str(path)], capture_output=True, text=True, timeout=60)
    if p.returncode:
        raise Problem('not a readable PDF: %s' % p.stderr.strip()[:200])
    return dict(line.split(':', 1) for line in p.stdout.splitlines() if ':' in line)


def fails(bad, ok):
    return (not bad), (ok if not bad else '; '.join(bad[:8]))


def doc_class(tex):
    m = re.search(r'\\documentclass\s*(?:\[([^\]]*)\])?\s*\{([^}]+)\}', tex)
    if not m:
        raise Problem('no \\documentclass line')
    return [o.strip() for o in (m.group(1) or '').split(',') if o.strip()], m.group(2).strip()


# ---------- rules shared by both publishers ----------

def build(prof, path, case, stage):
    """The source builds to a PDF from a clean folder."""
    tex, _ = source(path)
    engine = os.environ.get('PAPERCHECK_ENGINE') or shutil.which('tectonic')
    if not engine:
        raise Skip('no tectonic to build with')
    tmp = Path(tempfile.mkdtemp(prefix='papercheck-'))
    try:
        for f in tex.parent.iterdir():
            if f.is_file() and f.suffix.lower() in ('.tex', '.bib', '.bst', '.cls', '.sty', '.png', '.jpg', '.jpeg', '.pdf', '.eps') and f.name != Path(path).name:
                shutil.copy(f, tmp / f.name)
        t0 = time.time()
        p = subprocess.run([engine, '-X', 'compile', tex.name], cwd=tmp, capture_output=True, text=True, timeout=900)
        out = tmp / (tex.stem + '.pdf')
        if p.returncode or not out.is_file():
            err = next((l for l in (p.stderr + p.stdout).splitlines() if l.startswith(('error', '!'))), 'build failed')
            if re.search(r'(could not|failed to) (resolve|connect|download|fetch)', p.stderr, re.I):
                raise Skip('engine could not fetch its packages: %s' % err[:150])
            return False, err[:300]
        return True, 'built in %.0fs, %s bytes' % (time.time() - t0, out.stat().st_size)
    except subprocess.TimeoutExpired:
        raise Skip('build timed out')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def klass(prof, path, case, stage):
    """The publisher's class with its conference option, nothing substituted."""
    _, tex = source(path)
    opts, cls = doc_class(tex)
    bad = []
    if cls != prof['cls']:
        bad.append('class is %s, expected %s' % (cls, prof['cls']))
    if prof['option'] not in opts:
        bad.append('option %s missing (has %s)' % (prof['option'], opts or 'none'))
    return fails(bad, '\\documentclass[%s]{%s}' % (','.join(opts), cls))


def layout(prof, path, case, stage):
    """US letter pages and the class's own margins, columns and type size, not overridden in the source."""
    _, tex = source(path)
    opts, _ = doc_class(tex)
    bad = []
    size = pdf_info(path).get('Page size', '')
    m = re.search(r'([\d.]+) x ([\d.]+)', size)
    if not m or abs(float(m.group(1)) - 612) > 2 or abs(float(m.group(2)) - 792) > 2:
        bad.append('page size %s, expected US letter 612 x 792 pt' % size.strip())
    for o in opts:
        if o in prof['sizes'] or o in ('onecolumn', 'a4paper', 'draft', 'manuscript'):
            bad.append('class option %s changes the layout' % o)
    for pat, what in ((r'\\usepackage(\[[^\]]*\])?\{(geometry|fullpage|savetrees|a4wide|setspace|titlesec)\}', 'layout package'),
                      (r'\\(setlength|addtolength)\{\\(textwidth|textheight|columnsep|topmargin|oddsidemargin|evensidemargin|baselineskip)\}', 'page length changed'),
                      (r'\\(linespread|baselinestretch)', 'line spacing changed'), (r'\\(onecolumn)\b', 'one column'),
                      (r'\\(tiny|scriptsize|footnotesize|small)\s+(?!\\bibitem)[^\\]{400,}', 'body text set smaller')):
        m = re.search(pat, tex)
        if m:
            bad.append('%s: %s' % (what, m.group(0)[:50]))
    return fails(bad, 'letter page, class layout untouched')


def pages(prof, path, case, stage):
    """Within the venue's page limit."""
    limit = truth(case, stage).get('page_limit')
    if not limit:
        raise Problem('the case sets no page_limit')
    n = int(pdf_info(path).get('Pages', '0').strip() or 0)
    return (1 <= n <= limit), '%d pages, limit %d' % (n, limit)


def sections(prof, path, case, stage):
    """Abstract, keywords, the required sections in order and the reference list, with no starter text left."""
    _, tex = source(path)
    text = pdf_text(path)
    bad = []
    marks = [(r'\\begin\{abstract\}', 'Abstract'), (prof['keywords'], prof['keywords_name'])] + prof['extra']
    for pat, name in marks:
        if not re.search(pat, tex):
            bad.append('%s missing' % name)
    heads = [re.sub(r'\s+', ' ', h).strip().lower() for h in re.findall(r'\\section\*?\{([^}]*)\}', tex)]
    want = [s.lower() for s in truth(case, stage).get('sections', ['Introduction'])]
    pos = []
    for w in want:
        hit = [i for i, h in enumerate(heads) if w in h]
        if not hit:
            bad.append('section %r missing' % w)
        else:
            pos.append(hit[0])
    if pos != sorted(pos):
        bad.append('sections out of order: %s' % heads)
    if not re.search(r'\\begin\{thebibliography\}|\\bibliography\{|\\printbibliography', tex) or not re.search(r'references', text, re.I):
        bad.append('reference list missing')
    m = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', tex, re.S)
    if m and re.search(r'\\cite', m.group(1)):
        bad.append('citation inside the abstract')
    bad += ['starter text left: %r' % p for p in PLACEHOLDERS if p in text or p in tex]
    if re.search(r'^\s*TEXT\.', tex, re.M):
        bad.append('starter text left: TEXT.')
    return fails(bad, 'abstract, %s and %d required sections present' % (prof['keywords_name'].lower(), len(want)))


def bibitems(tex):
    m = re.search(r'\\begin\{thebibliography\}\{[^}]*\}(.*?)\\end\{thebibliography\}', tex, re.S)
    if not m:
        raise Problem('references are not in the source file (no thebibliography block)')
    items = re.split(r'\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}', m.group(1))[1:]
    return [(items[i].strip(), re.sub(r'\s+', ' ', items[i + 1]).strip()) for i in range(0, len(items), 2)]


def cite_order(tex):
    body = tex.split('\\begin{thebibliography}')[0]
    keys = []
    for m in re.finditer(r'\\cite[tp]?\*?(?:\[[^\]]*\])*\{([^}]+)\}', body):
        for k in m.group(1).split(','):
            if k.strip() not in keys:
                keys.append(k.strip())
    return keys


def refstyle(prof, path, case, stage):
    """Numbered citations, each resolved; every entry cited; IEEE lists entries in order of first citation."""
    _, tex = source(path)
    text = pdf_text(path)
    items = bibitems(tex)
    listed = [k for k, _ in items]
    cited = cite_order(tex)
    bad = []
    if not cited:
        bad.append('no citations in the text')
    bad += ['cited but not listed: %s' % k for k in cited if k not in listed]
    bad += ['listed but never cited: %s' % k for k in listed if k not in cited]
    if '[?]' in text or re.search(r'\(\?\)|\?\?', text):
        bad.append('unresolved citation mark in the PDF')
    if not re.search(r'\[\d+(?:[,–-]\s?\d+)*\]', text):
        bad.append('no numbered citation marks in the PDF')
    if re.search(r'\\usepackage(\[[^\]]*\])?\{(natbib|apacite|biblatex)\}', tex) and prof['cls'] == 'IEEEtran':
        bad.append('author-year citation package loaded')
    if prof['cls'] == 'IEEEtran':
        if [k for k in listed if k in cited] != [k for k in cited if k in listed]:
            bad.append('reference list is not in order of first citation')
        for k, body in items:
            if not re.search(r"``.+?''|“.+?”|\"[^\"]+\"", body) and 'arXiv' not in body:
                bad.append('%s: article title not in quotation marks' % k)
            if not re.search(r'\b(19|20)\d{2}\b', body):
                bad.append('%s: no year' % k)
    else:
        for k, body in items:
            if not re.search(r'\.\s+(19|20)\d{2}\.\s', body):
                bad.append('%s: year does not follow the authors (Authors. Year. Title.)' % k)
    min_refs = truth(case, stage).get('min_references', 1)
    if len(items) < min_refs:
        bad.append('%d references, at least %d asked for' % (len(items), min_refs))
    return fails(bad, '%d numbered references, all cited' % len(items))


def anonymous(prof, path, case, stage):
    """Blind review: no names, organisations, emails or acknowledgments in the PDF, its properties or the visible source."""
    try:
        _, tex = source(path)
        opts, _ = doc_class(tex)
    except Problem:
        tex, opts = None, []
    text = pdf_text(path)
    info = pdf_info(path)
    bad = []
    flat = re.sub(r'\s+', ' ', text).lower()
    props = ' '.join(info.get(k, '') for k in ('Author', 'Title', 'Subject', 'Keywords', 'Creator')).lower()
    for s in truth(case, stage).get('identity', []):
        if s.lower() in flat:
            bad.append('%r appears in the PDF' % s)
        if s.lower() in props:
            bad.append('%r appears in the PDF properties' % s)
    if (tex and re.search(r'\\section\*?\{\s*acknowledg|\\begin\{acks\}', tex, re.I)) or re.search(r'\backnowledg(e)?ments?\b', flat):
        bad.append('acknowledgments present')
    if re.search(r'\b(our|my) (previous|earlier|prior) (work|study|paper)\b', flat):
        bad.append('self-reference in the first person')
    if tex is None:
        if 'anonymous' not in flat[:1500]:
            bad.append('the opening of the paper does not read Anonymous')
    elif prof['cls'] == 'acmart':
        if 'anonymous' not in opts:
            bad.append('acmart anonymous option missing')
    else:
        m = re.search(r'\\author\{(.*?)\}\s*\\maketitle', tex, re.S) or re.search(r'\\author\{(.*?)\n\}', tex, re.S)
        block = m.group(1) if m else ''
        if 'anonymous' not in block.lower():
            bad.append('author block does not read Anonymous')
        if re.search(r'[\w.]+@[\w.]+\.\w+', block):
            bad.append('email in the author block')
    return fails(bad, 'no identifying text found')


# ---------- every reference is a real paper ----------

def fetch(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise Skip('lookup service answered %s for %s' % (e.code, url.split('?')[0]))
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise Skip('lookup service unreachable: %s' % e)


def lookup(doi):
    m = re.fullmatch(r'10\.48550/arxiv\.(.+)', doi, re.I)
    if m:
        feed = ET.fromstring(fetch('https://export.arxiv.org/api/query?id_list=' + urllib.parse.quote(m.group(1))) or b'<feed/>')
        e = feed.find('{http://www.w3.org/2005/Atom}entry')
        t = e.findtext('{http://www.w3.org/2005/Atom}title') if e is not None else None
        return dict(registry='arxiv', title=re.sub(r'\s+', ' ', t).strip(), year=(e.findtext('{http://www.w3.org/2005/Atom}published') or '')[:4]) if t else None
    raw = fetch('https://api.crossref.org/works/' + urllib.parse.quote(doi, safe='/'))
    if raw:
        msg = json.loads(raw)['message']
        return dict(registry='crossref', title=re.sub(r'<[^>]+>', '', (msg.get('title') or [''])[0]),
                    year=str(((msg.get('issued') or {}).get('date-parts') or [[None]])[0][0]))
    raw = fetch('https://api.openalex.org/works/https://doi.org/' + urllib.parse.quote(doi, safe='/') + '?select=title,publication_year')
    if raw:
        w = json.loads(raw)
        return dict(registry='openalex', title=w.get('title') or '', year=str(w.get('publication_year')))
    return None


def words(s):
    return [w for w in re.findall(r'[a-z0-9]+', re.sub(r'\\[a-zA-Z]+|[{}]', ' ', s).lower()) if len(w) > 3]


def pdf_refs(text):
    """Numbered entries from the PDF's reference list, for a paper handed back without its source."""
    m = list(re.finditer(r'^\s*references\s*$', text, re.I | re.M))
    if not m:
        return []
    tail = text[m[-1].end():]
    parts = re.split(r'(?m)^\s*\[(\d+)\]\s*', tail)[1:]
    out = []
    for i in range(0, len(parts) - 1, 2):
        body = re.sub(r'(doi:?|doi\.org/)\s*\n\s*', r'\1 ', parts[i + 1])
        body = re.sub(r'(10\.\d{4,9}/\S*[-/.])\n(\S)', r'\1\2', body)
        out.append((parts[i], re.sub(r'\s+', ' ', body).strip()))
    return out


def refs_real(prof, path, case, stage):
    """Every reference carries a DOI or arXiv id that a registry knows, and the registered title matches the entry."""
    try:
        _, tex = source(path)
        items = bibitems(tex)
    except Problem:
        items = pdf_refs(pdf_text(path))
        if not items:
            raise Problem('no source file and no numbered reference list in the PDF')
    bad, records = [], []
    for key, body in items:
        plain = body.replace('\\_', '_').replace('\\%', '%').replace('\\&', '&')
        m = re.search(r'10\.\d{4,9}/[^\s}]+', plain)
        ax = re.search(r'arXiv:\s*(\d{4}\.\d{4,5})', plain, re.I)
        doi = m.group(0).rstrip('.,;)') if m else '10.48550/arXiv.' + ax.group(1) if ax else None
        if not doi:
            bad.append('%s: no DOI or arXiv id' % key)
            records.append(dict(key=key, doi=None))
            continue
        rec = lookup(doi)
        records.append(dict(key=key, doi=doi, found=bool(rec), record=rec))
        if not rec:
            bad.append('%s: %s is not registered' % (key, doi))
            continue
        want, have = set(words(rec['title'])), set(words(plain))
        overlap = len(want & have) / max(len(want), 1)
        records[-1]['title_overlap'] = round(overlap, 2)
        if overlap < 0.7:
            bad.append('%s: entry does not match the registered title %r' % (key, rec['title'][:60]))
        elif rec.get('year') and rec['year'] not in plain and str(int(rec['year']) + 1) not in plain and str(int(rec['year']) - 1) not in plain:
            bad.append('%s: year differs from the registered %s' % (key, rec['year']))
        time.sleep(0.3)
    try:
        (Path(path).parent / 'refs-evidence.json').write_text(json.dumps(records, indent=1, ensure_ascii=False) + '\n')
    except OSError:
        pass
    return fails(bad, '%d references resolve to registered papers' % len(items))


RULES = {'BUILD-1': build, 'CLASS-1': klass, 'LAYOUT-1': layout, 'PAGE-1': pages, 'SEC-1': sections, 'REF-1': refstyle, 'ANON-1': anonymous}


def check(rule_id, path, case, stage):
    """Grade one rule on one PDF. Returns (passed, evidence); passed is None when the check could not run."""
    path = Path(path)
    try:
        if rule_id == 'CASE-REFS-REAL':
            fn, prof = refs_real, None
        else:
            prefix, _, name = rule_id.partition('-')
            if prefix not in PROFILES or name not in RULES:
                raise KeyError('unknown rule %s' % rule_id)
            fn, prof = RULES[name], PROFILES[prefix]
        if not path.is_file() or path.read_bytes()[:5] != b'%PDF-':
            return False, 'no PDF at %s' % path.name
        return fn(prof, path, case, stage)
    except Skip as e:
        return None, 'not run: %s' % e
    except Problem as e:
        return False, str(e)


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
    except (IndexError, OSError, json.JSONDecodeError) as e:
        print(__doc__, file=sys.stderr)
        print('error: %s' % e, file=sys.stderr)
        return 2
    if not rules and case:
        rules = [c['rule'] for c in case.get('criteria', []) if c.get('grader') == 'script' and c['stage'] in ('both', stage)]
    ok = True
    for r in rules:
        passed, evidence = check(r, path, case, stage)
        ok &= passed is not False
        print(json.dumps(dict(rule=r, passed=passed, evidence=evidence), ensure_ascii=False))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
