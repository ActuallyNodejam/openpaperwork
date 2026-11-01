#!/usr/bin/env python3
"""Mechanical checks for academic guideline rules on a .docx. Standard library only. No model calls.

check(rule_id, path, case, stage) -> (passed, evidence) grades one rule of guidelines/apa/7,
guidelines/ieee/2025-03-28 or guidelines/utrgv/2024-08-13 against one output file. Rules that compare
against expected references read case['truth'][stage], which the agent never sees.

CLI: python3 refcheck.py FILE.docx [--case case.json] [--stage first|revision] [RULE ...]
Prints one JSON object per rule and exits 0 when all pass, 1 when any fails, 2 on bad input.

A pass means the stated property holds in the saved file. It does not prove that the prose is
right, that a renderer lays the page out as Word would, or that a source says what it is cited for.
"""
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
INCH = 1440  # twips
YEAR = r'(?:\d{4}[a-z]?|n\.d\.)'
APA_FONTS = {('times new roman', 12), ('calibri', 11), ('arial', 11), ('georgia', 11),
             ('lucida sans unicode', 10), ('computer modern', 10)}  # APA 7, section 2.19


# ---------- docx model ----------

def on(el, name):
    """A toggle property such as w:b is on when present and not switched off."""
    x = el.find(W + name) if el is not None else None
    return None if x is None else x.get(W + 'val', 'true') not in ('0', 'false', 'off', 'none')


class Docx:
    def __init__(self, path):
        with zipfile.ZipFile(path) as z:
            names = set(z.namelist())
            self.doc = ET.fromstring(z.read('word/document.xml'))
            styles = ET.fromstring(z.read('word/styles.xml')) if 'word/styles.xml' in names else None
            theme = ET.fromstring(z.read('word/theme/theme1.xml')) if 'word/theme/theme1.xml' in names else None
            rels = {}
            if 'word/_rels/document.xml.rels' in names:
                rels = {r.get('Id'): r.get('Target') for r in ET.fromstring(z.read('word/_rels/document.xml.rels'))}
            self.footers = {}
            for rid, target in rels.items():
                part = 'word/' + target.lstrip('/').replace('word/', '', 1)
                if 'footer' in target and part in names:
                    self.footers[rid] = ET.fromstring(z.read(part))
        self.theme_font = {}
        if theme is not None:
            for kind in ('major', 'minor'):
                latin = theme.find('.//%s%sFont/%slatin' % (A, kind, A))
                if latin is not None:
                    self.theme_font[kind] = latin.get('typeface')
        self.styles, self.default_para, self.default_ppr, self.default_rpr = {}, None, None, None
        if styles is not None:
            dd = styles.find(W + 'docDefaults')
            if dd is not None:
                self.default_ppr = dd.find(W + 'pPrDefault/' + W + 'pPr')
                self.default_rpr = dd.find(W + 'rPrDefault/' + W + 'rPr')
            for s in styles.findall(W + 'style'):
                sid = s.get(W + 'styleId')
                based = s.find(W + 'basedOn')
                name = s.find(W + 'name')
                self.styles[sid] = dict(type=s.get(W + 'type'), based=based.get(W + 'val') if based is not None else None,
                                        name=(name.get(W + 'val') if name is not None else sid) or '',
                                        ppr=s.find(W + 'pPr'), rpr=s.find(W + 'rPr'))
                if s.get(W + 'type') == 'paragraph' and s.get(W + 'default') in ('1', 'true'):
                    self.default_para = sid
        self.paragraphs, self.sections = [], []
        body = self.doc.find(W + 'body')
        self._walk(body, False)
        final = body.find(W + 'sectPr')
        if final is not None:
            self.sections.append(final)

    def _walk(self, parent, in_table):
        for el in parent:
            if el.tag == W + 'p':
                self.paragraphs.append(self._para(el, in_table))
                sp = el.find(W + 'pPr/' + W + 'sectPr')
                if sp is not None:
                    self.sections.append(sp)
            elif el.tag == W + 'tbl':
                for cell in el.iter(W + 'tc'):
                    self._walk(cell, True)
            elif el.tag in (W + 'sdt', W + 'sdtContent', W + 'customXml'):
                self._walk(el, in_table)

    def chain(self, sid):
        seen = []
        while sid and sid in self.styles and sid not in seen:
            seen.append(sid)
            sid = self.styles[sid]['based']
        return [self.styles[s] for s in seen]

    def ppr_value(self, ppr, style, tag, attr):
        """Resolve a paragraph property attribute: direct, then the style chain, then document defaults."""
        sources = [ppr] + [s['ppr'] for s in self.chain(style or self.default_para)] + [self.default_ppr]
        for src in sources:
            el = src.find(W + tag) if src is not None else None
            if el is not None and el.get(W + attr) is not None:
                return el.get(W + attr)
        return None

    def rpr_sources(self, rpr, rstyle, pstyle):
        return ([rpr] + [s['rpr'] for s in self.chain(rstyle)] +
                [s['rpr'] for s in self.chain(pstyle or self.default_para)] + [self.default_rpr])

    def run_props(self, run, pstyle):
        rpr = run.find(W + 'rPr')
        rs = rpr.find(W + 'rStyle') if rpr is not None else None
        sources = self.rpr_sources(rpr, rs.get(W + 'val') if rs is not None else None, pstyle)
        props = {}
        for key in ('b', 'i', 'caps'):
            props[key] = next((v for v in (on(s, key) for s in sources) if v is not None), False)
        props['u'] = False
        for s in sources:
            u = s.find(W + 'u') if s is not None else None
            if u is not None:
                props['u'] = u.get(W + 'val', 'single') != 'none'
                break
        font, size = None, None
        for s in sources:
            f = s.find(W + 'rFonts') if s is not None else None
            if f is not None and font is None:
                if f.get(W + 'ascii'):
                    font = f.get(W + 'ascii')
                elif f.get(W + 'asciiTheme'):
                    font = self.theme_font.get('major' if 'major' in f.get(W + 'asciiTheme') else 'minor')
            z = s.find(W + 'sz') if s is not None else None
            if z is not None and size is None:
                size = int(z.get(W + 'val')) / 2
        props['font'], props['size'] = font, size if size is not None else 10.0
        return props

    def _para(self, p, in_table):
        ppr = p.find(W + 'pPr')
        ps = ppr.find(W + 'pStyle') if ppr is not None else None
        style = ps.get(W + 'val') if ps is not None else None
        runs, page_break = [], False
        for r in p.iter(W + 'r'):
            text = ''
            for x in r:
                if x.tag == W + 't':
                    text += x.text or ''
                elif x.tag == W + 'tab':
                    text += '\t'
                elif x.tag == W + 'br':
                    if x.get(W + 'type') == 'page':
                        page_break = True
                    else:
                        text += '\n'
            if text:
                runs.append(dict(text=text, **self.run_props(r, style)))

        def num(tag, attr):
            v = self.ppr_value(ppr, style, tag, attr)
            try:
                return int(v) if v is not None else None
            except ValueError:
                return None
        sname = self.styles.get(style or self.default_para, {}).get('name', '') if self.styles else ''
        return dict(text=''.join(r['text'] for r in runs), runs=runs, style=style or '', style_name=sname,
                    in_table=in_table, jc=self.ppr_value(ppr, style, 'jc', 'val') or 'left',
                    left=num('ind', 'left') or num('ind', 'start') or 0, hanging=num('ind', 'hanging') or 0,
                    first=num('ind', 'firstLine') or 0, line=num('spacing', 'line'),
                    line_rule=self.ppr_value(ppr, style, 'spacing', 'lineRule') or 'auto',
                    before=num('spacing', 'before') or 0, after=num('spacing', 'after') or 0,
                    break_before=bool(on(ppr, 'pageBreakBefore')) or page_break or any(
                        on(s['ppr'], 'pageBreakBefore') for s in self.chain(style)))


def bold(p):
    runs = [r for r in p['runs'] if r['text'].strip()]
    return bool(runs) and all(r['b'] for r in runs)


def is_heading(p):
    n = p['style_name'].lower()
    return n.startswith('heading') or n == 'title'


def body_paras(d, refs_at):
    return [p for p in d.paragraphs[:refs_at] if p['text'].strip() and not p['in_table']]


def text_paras(d, refs_at):
    """Running text: non-empty, not in a table, not a heading, and long enough to be prose."""
    return [p for p in body_paras(d, refs_at) if not is_heading(p) and len(p['text'].split()) >= 12]


def find_refs(d, label_re=r'references|bibliography|works cited|reference list'):
    """Index of the last reference-list label paragraph and the entry paragraphs after it."""
    at = None
    for i, p in enumerate(d.paragraphs):
        if re.fullmatch(label_re, p['text'].strip(), re.I):
            at = i
    if at is None:
        return None, []
    entries = []
    for p in d.paragraphs[at + 1:]:
        t = p['text'].strip()
        if not t:
            continue
        if re.match(r'^(appendix|vita)\b', t, re.I) or (is_heading(p) and len(t) < 60):
            break
        entries.append(p)
    return at, entries


# ---------- references and citations ----------

def truth(case, stage):
    t = (case or {}).get('truth', {})
    return t.get(stage) or t.get('first') or {}


def first_key(ref):
    return ref['authors'][0]


def entry_parts(text):
    m = re.match(r'^(?P<auth>.+?)\s\((?P<year>' + YEAR + r')(?:,[^)]*)?\)\.\s*(?P<rest>.*)$', text.strip(), re.S)
    return m.groupdict() if m else None


def match_entry(entry_text, refs):
    """The expected reference this list entry is for: first author or group name, then year."""
    parts = entry_parts(entry_text)
    head = (parts['auth'] if parts else entry_text[:80])
    found = [r for r in refs if head.strip().lower().startswith(first_key(r).lower())]
    if len(found) > 1 and parts:
        found = [r for r in found if r['year'] == parts['year']] or found
    return found[0] if found else None


def citations(text):
    """Author-date citations as (kind, author_text, year, offset). Parenthetical parts are split on ';'."""
    out = []
    for m in re.finditer(r'\(([^()]*?' + YEAR + r'[^()]*)\)', text):
        inner = m.group(1).strip()
        if re.fullmatch(YEAR + r'(?:,\s*(?:p|pp|para)\.\s*[\d–-]+)?', inner):
            out.append(('narrative', text[max(0, m.start() - 90):m.start()], inner[:4] if inner[0].isdigit() else 'n.d.', m.start()))
            continue
        for part in inner.split(';'):
            part = re.sub(r'^\s*(?:e\.g\.,|i\.e\.,|see also|see|cf\.)\s*', '', part.strip())
            pm = re.match(r'^(?P<auth>.+?),\s*(?P<years>' + YEAR + r'(?:,\s*' + YEAR + r')*)(?:,\s*(?:p|pp|para)\..*)?$', part)
            if not pm:
                continue
            for y in re.findall(YEAR, pm.group('years')):
                out.append(('parenthetical', pm.group('auth'), y, m.start()))
    return out


def body_text(d, refs_at):
    return '\n'.join(p['text'] for p in body_paras(d, refs_at))


def cite_matches(c, ref):
    kind, auth, year, _ = c
    if kind == 'narrative':
        tail = auth[-(len(first_key(ref)) + 60):]
        return first_key(ref) in tail
    return first_key(ref) in auth


def classify(cites, refs):
    """Map each citation to the expected reference with that first author; None when there is none."""
    out = []
    for c in cites:
        cands = [r for r in refs if cite_matches(c, r)]
        if c[0] == 'narrative' and len(cands) > 1:  # nearest name before the year wins
            cands.sort(key=lambda r: c[1].rfind(first_key(r)), reverse=True)
        exact = [r for r in cands if r['year'] == c[2]]
        out.append((c, (exact or cands or [None])[0]))
    return out


# ---------- rule implementations ----------

def need_refs(d):
    at, entries = find_refs(d)
    if at is None:
        raise Problem('no reference list label (References) found')
    if not entries:
        raise Problem('reference list is empty')
    return at, entries


class Problem(Exception):
    pass


def fails(bad, ok_msg):
    return (not bad), (ok_msg if not bad else '; '.join(bad[:8]) + (' (+%d more)' % (len(bad) - 8) if len(bad) > 8 else ''))


def apa_cit_1(d, case, stage):
    """Every in-text citation matches a list entry by first author and year, and every entry is cited."""
    at, entries = need_refs(d)
    listed = []
    for e in entries:
        p = entry_parts(e['text'])
        if not p:
            raise Problem('entry has no "Author (Year)." opening: %r' % e['text'][:70])
        listed.append((p['auth'], p['year']))
    cites = citations(body_text(d, at))
    if not cites:
        return False, 'no author-date citations found in the text'
    bad, used = [], set()
    for kind, auth, year, _ in cites:
        hit = [i for i, (a, y) in enumerate(listed) if y == year and a.split(',')[0].strip().rstrip('.') in auth]
        if not hit:
            bad.append('cited %s %s has no list entry' % (re.sub(r'\s+', ' ', auth.strip())[-40:], year))
        used.update(hit)
    bad += ['entry not cited: %s (%s)' % (a[:40], y) for i, (a, y) in enumerate(listed) if i not in used]
    return fails(bad, '%d citations, %d entries, all correspond' % (len(cites), len(listed)))


def case_refset(d, case, stage):
    """The list holds exactly the expected works: none missing, none invented, none duplicated."""
    refs = truth(case, stage).get('references', [])
    at, entries = need_refs(d)
    got = [match_entry(e['text'], refs) for e in entries]
    bad = ['unexpected entry: %r' % e['text'][:60] for e, g in zip(entries, got) if g is None]
    ids = [g['id'] for g in got if g]
    bad += ['duplicate entry: %s' % i for i in sorted({i for i in ids if ids.count(i) > 1})]
    bad += ['missing entry: %s' % r['id'] for r in refs if r['id'] not in ids]
    cites = classify(citations(body_text(d, at)), refs)
    bad += ['citation to an unexpected source: %r' % c[1].strip()[-40:] for c, r in cites if r is None]
    return fails(bad, '%d expected works listed exactly once' % len(refs))


def apa_cit_2(d, case, stage):
    """Three or more authors: first author plus et al. One or two authors: every surname, no et al."""
    refs = truth(case, stage).get('references', [])
    at, _ = need_refs(d)
    bad, n = [], 0
    for c, r in classify(citations(body_text(d, at)), refs):
        if r is None or r.get('group'):
            continue
        n += 1
        auth = c[1][-(len(first_key(r)) + 60):] if c[0] == 'narrative' else c[1]
        auth = auth[auth.rfind(first_key(r)):]
        if len(r['authors']) >= 3:
            if 'et al.' not in auth or r['authors'][1] in auth:
                bad.append('%s: expected "%s et al." got %r' % (r['id'], first_key(r), auth.strip()[:50]))
        elif 'et al' in auth or not all(a in auth for a in r['authors']):
            bad.append('%s: expected all of %s got %r' % (r['id'], ' & '.join(r['authors']), auth.strip()[:50]))
    if n == 0:
        return False, 'no author-date citations of the expected works'
    return fails(bad, '%d citations use the APA author form' % n)


def apa_cit_3(d, case, stage):
    """Two authors: '&' inside parentheses, 'and' in running text."""
    refs = truth(case, stage).get('references', [])
    at, _ = need_refs(d)
    bad, n = [], 0
    for c, r in classify(citations(body_text(d, at)), refs):
        if r is None or r.get('group') or len(r['authors']) != 2:
            continue
        n += 1
        if c[0] == 'parenthetical':
            if not re.search(re.escape(r['authors'][0]) + r'\s*&\s*' + re.escape(r['authors'][1]), c[1]):
                bad.append('%s parenthetical without "&": %r' % (r['id'], c[1].strip()[:50]))
        else:
            tail = c[1][c[1].rfind(first_key(r)):]
            if not re.search(re.escape(r['authors'][0]) + r'\s+and\s+' + re.escape(r['authors'][1]), tail):
                bad.append('%s narrative without "and": %r' % (r['id'], tail.strip()[:50]))
    if n == 0:
        two = [r for r in refs if not r.get('group') and len(r['authors']) == 2]
        return (not two), ('no two-author works expected' if not two else 'no citations of the two-author works found')
    return fails(bad, '%d two-author citations joined correctly' % n)


def sort_key(text):
    p = entry_parts(text)
    head = p['auth'] if p else text
    return re.sub(r'[^a-z ]', '', head.lower()), (p['year'] if p else '')


def apa_ref_1(d, case, stage):
    """Entries in alphabetical order letter by letter by the author element, then year (9.44 to 9.46)."""
    _, entries = need_refs(d)
    keys = [sort_key(e['text']) for e in entries]
    bad = ['%r before %r' % (a[0][:30], b[0][:30]) for a, b in zip(keys, keys[1:]) if a > b]
    return fails(bad, '%d entries in order' % len(entries))


def apa_ref_2(d, case, stage):
    """Each entry has a hanging indent of 0.5 inch (0.4 to 0.6 accepted)."""
    _, entries = need_refs(d)
    bad = ['%r hanging %.2f in' % (e['text'][:30], e['hanging'] / INCH) for e in entries
           if not (0.4 * INCH <= e['hanging'] <= 0.6 * INCH)]
    return fails(bad, '%d entries with 0.5 in hanging indent' % len(entries))


def apa_ref_3(d, case, stage):
    """DOIs are https://doi.org/ links with no label; a work without a DOI gets none invented."""
    refs = truth(case, stage).get('references', [])
    _, entries = need_refs(d)
    bad = []
    for e in entries:
        t = e['text']
        if re.search(r'\bdoi:\s*10\.|dx\.doi\.org|retrieved from\s+https?://doi', t, re.I):
            bad.append('old DOI form in %r' % t[:40])
        r = match_entry(t, refs)
        if r is None:
            continue
        if r.get('doi'):
            if ('https://doi.org/' + r['doi']).lower() not in t.lower():
                bad.append('%s lacks https://doi.org/%s' % (r['id'], r['doi']))
        elif 'doi.org' in t.lower() or re.search(r'\b10\.\d{4,}/', t):
            bad.append('%s has a DOI the source does not have' % r['id'])
    return fails(bad, 'DOIs present and in https://doi.org/ form')


def apa_ref_4(d, case, stage):
    """Author element: every author up to 20 in source order as Surname, I. I., with & before the last."""
    refs = truth(case, stage).get('references', [])
    _, entries = need_refs(d)
    bad = []
    for e in entries:
        r, p = match_entry(e['text'], refs), entry_parts(e['text'])
        if r is None or p is None:
            bad.append('unrecognised entry %r' % e['text'][:40])
            continue
        auth = p['auth']
        if r.get('group'):
            if auth.strip().rstrip('.') != r['authors'][0]:
                bad.append('%s group author written %r' % (r['id'], auth))
            continue
        pos = [auth.find(a) for a in r['authors'][:20]]
        if -1 in pos or pos != sorted(pos):
            bad.append('%s authors missing or out of order: %r' % (r['id'], auth[:60]))
            continue
        if len(r['authors']) >= 2 and not re.search(r'&\s*' + re.escape(r['authors'][min(len(r['authors']), 20) - 1]), auth):
            bad.append('%s no "&" before final author' % r['id'])
        for a in r['authors'][:20]:
            if not re.search(re.escape(a) + r',\s(?:[A-Z]\.(?:[\s-][A-Z]\.)*)', auth):
                bad.append('%s author %s not written as "Surname, I."' % (r['id'], a))
    return fails(bad, 'author elements in APA form')


def apa_ref_5(d, case, stage):
    """The date follows the authors as (Year). and matches the source."""
    refs = truth(case, stage).get('references', [])
    _, entries = need_refs(d)
    bad = []
    for e in entries:
        p = entry_parts(e['text'])
        r = match_entry(e['text'], refs)
        if p is None:
            bad.append('no "(Year)." after authors in %r' % e['text'][:40])
        elif r is not None and p['year'] != r['year']:
            bad.append('%s year %s, expected %s' % (r['id'], p['year'], r['year']))
    return fails(bad, 'dates in (Year). form and correct')


def apa_ref_6(d, case, stage):
    """Volume(issue) as given and page ranges with an en dash, never a hyphen."""
    refs = truth(case, stage).get('references', [])
    _, entries = need_refs(d)
    bad = []
    for e in entries:
        t = e['text']
        t_nodoi = re.sub(r'https?://\S+', '', t)
        if re.search(r'\b\d+\s?-\s?\d+\b', t_nodoi):
            bad.append('hyphen in a number range in %r' % t[:40])
        r = match_entry(t, refs)
        if r is None:
            bad.append('unrecognised entry %r' % e['text'][:40])
            continue
        if r.get('volume') and r.get('issue') and '%s(%s)' % (r['volume'], r['issue']) not in t:
            bad.append('%s lacks %s(%s)' % (r['id'], r['volume'], r['issue']))
        if r.get('pages') and r['pages'] not in t:
            bad.append('%s lacks pages %s' % (r['id'], r['pages']))
    return fails(bad, 'volume, issue and page ranges in APA form')


def italic_span(e, needle, length=None):
    """True, False or None (needle absent) for whether the first length characters of needle are italic."""
    text = e['text']
    i = text.find(needle)
    if i < 0:
        return None
    flags = []
    for r in e['runs']:
        flags += [r['i']] * len(r['text'])
    return all(flags[i:i + (len(needle) if length is None else length)])


def apa_ref_7(d, case, stage):
    """Italics: journal name and volume, book, report or preprint title; never the article or chapter title."""
    refs = truth(case, stage).get('references', [])
    _, entries = need_refs(d)
    bad = []
    for e in entries:
        r = match_entry(e['text'], refs)
        if r is None:
            bad.append('unrecognised entry %r' % e['text'][:40])
            continue
        if r['type'] == 'article':
            checks = [(r['container'], r['container'])]
            if r.get('volume'):
                checks.append((r['volume'], r['volume'] + ('(' if r.get('issue') else '')))
            for part, needle in checks:
                if italic_span(e, needle, len(part)) is False:
                    bad.append('%s %r not italic' % (r['id'], part))
            first_words = r['title'].split(':')[0]
            if italic_span(e, first_words):
                bad.append('%s article title italic' % r['id'])
        elif r['type'] in ('book', 'report', 'preprint'):
            if italic_span(e, r['title'].split(':')[0]) is False:
                bad.append('%s book title not italic' % r['id'])
        elif r['type'] == 'chapter':
            if italic_span(e, r['container'].split(':')[0]) is False:
                bad.append('%s edited book title not italic' % r['id'])
            if italic_span(e, r['title'].split(':')[0]):
                bad.append('%s chapter title italic' % r['id'])
    return fails(bad, 'italics as APA sets them')


def apa_ref_8(d, case, stage):
    """Work titles in sentence case exactly as the source gives them (proper nouns kept)."""
    refs = truth(case, stage).get('references', [])
    _, entries = need_refs(d)
    bad = []
    for e in entries:
        r = match_entry(e['text'], refs)
        if r is None:
            bad.append('unrecognised entry %r' % e['text'][:40])
        elif r['title'] not in e['text']:
            bad.append('%s title not %r' % (r['id'], r['title'][:50]))
    return fails(bad, 'titles in sentence case')


def apa_fmt_1(d, case, stage):
    """The list starts on a label 'References', bold and centered."""
    at, _ = need_refs(d)
    p = d.paragraphs[at]
    bad = []
    if p['text'].strip() != 'References':
        bad.append('label is %r' % p['text'].strip())
    if p['jc'] != 'center':
        bad.append('label alignment %s' % p['jc'])
    if not bold(p):
        bad.append('label not bold')
    return fails(bad, 'References label bold and centered')


def spacing_ratio(p):
    if p['line'] is None:
        return 1.0
    if p['line_rule'] == 'auto':
        return p['line'] / 240
    size = max((r['size'] for r in p['runs']), default=12)
    return p['line'] / 20 / (size * 1.15)


def apa_fmt_2(d, case, stage):
    """Double line spacing for all text, including the reference list, with no extra space between paragraphs."""
    at, entries = need_refs(d)
    paras = body_paras(d, at) + entries
    bad = ['%r spacing %.1f' % (p['text'][:30], spacing_ratio(p)) for p in paras if not 1.9 <= spacing_ratio(p) <= 2.1]
    bad += ['%r has %.0f pt before/after' % (p['text'][:30], max(p['before'], p['after']) / 20)
            for p in paras if max(p['before'], p['after']) > 12 * 20 and not is_heading(p)]
    return fails(bad, '%d paragraphs double spaced' % len(paras))


def font_of(runs):
    return {((r['font'] or '').lower(), r['size']) for r in runs if r['text'].strip()}


def apa_fmt_3(d, case, stage):
    """One accepted font throughout the text: Times New Roman 12, Calibri 11, Arial 11, Georgia 11, Lucida Sans Unicode 10 or Computer Modern 10."""
    at, entries = need_refs(d)
    used = set()
    for p in body_paras(d, at) + entries:
        if not is_heading(p):
            used |= font_of(p['runs'])
    if len(used) != 1:
        return False, 'fonts used: %s' % sorted(used)
    f = used.pop()
    return (f in APA_FONTS), '%s %g pt' % f


def apa_fmt_4(d, case, stage):
    """Body paragraphs start with a 0.5 inch first-line indent."""
    at, _ = need_refs(d)
    paras = text_paras(d, at)
    bad = ['%r first-line %.2f in' % (p['text'][:30], p['first'] / INCH) for p in paras
           if not 0.4 * INCH <= p['first'] <= 0.6 * INCH]
    return fails(bad, '%d paragraphs indented 0.5 in' % len(paras))


def apa_fmt_5(d, case, stage):
    """Level 1 headings are centered, bold and in title case."""
    want = truth(case, stage).get('level1_headings', [])
    bad = []
    for h in want:
        hits = [p for p in d.paragraphs if p['text'].strip() == h]
        if not hits:
            bad.append('heading %r missing' % h)
            continue
        p = hits[0]
        if p['jc'] != 'center' or not bold(p):
            bad.append('%r is %s%s' % (h, p['jc'], '' if bold(p) else ', not bold'))
    return fails(bad, 'level 1 headings centered and bold')


def ieee_numbers(text):
    out = []
    for m in re.finditer(r'\[(\d+(?:\s*[,–-]\s*\d+)*)\]', text):
        for part in re.split(r'\s*,\s*', m.group(1)):
            ab = re.split(r'\s*[–-]\s*', part)
            out += list(range(int(ab[0]), int(ab[-1]) + 1)) if len(ab) == 2 else [int(ab[0])]
    return out


def ieee_cit_1(d, case, stage):
    """Bracketed numbers, assigned in order of first citation."""
    at, _ = need_refs(d)
    nums = ieee_numbers(body_text(d, at))
    if not nums:
        return False, 'no bracketed citations'
    seen = []
    for n in nums:
        if n not in seen:
            seen.append(n)
    return (seen == list(range(1, len(seen) + 1))), 'first-citation order %s' % seen[:15]


def ieee_ref_1(d, case, stage):
    """The list is numbered [1] to [n] in citation order, every number is cited and every citation is listed."""
    at, entries = need_refs(d)
    listed = [int(m.group(1)) for m in (re.match(r'^\s*\[(\d+)\]', e['text']) for e in entries) if m]
    bad = []
    if listed != list(range(1, len(entries) + 1)):
        bad.append('list numbering %s' % listed[:15])
    cited = set(ieee_numbers(body_text(d, at)))
    bad += ['[%d] not cited' % n for n in listed if n not in cited]
    bad += ['[%d] cited, not listed' % n for n in sorted(cited - set(listed))]
    return fails(bad, '%d numbered entries match the citations' % len(entries))


MAJOR = r'(abstract|dedication|acknowledgments?|table of contents|list of tables|list of figures|references|appendix( [a-z])?|vita|chapter [ivxlc]+)'


def majors(d):
    return [(i, p) for i, p in enumerate(d.paragraphs) if re.fullmatch(MAJOR, p['text'].strip(), re.I)]


def utrgv_font_1(d, case, stage):
    """Times New Roman 12 point outside tables and figures."""
    used = set()
    for p in d.paragraphs:
        if p['text'].strip() and not p['in_table'] and not re.match(r'^(Table|Figure)\s+\d', p['text']):
            used |= font_of(p['runs'])
    return (used == {('times new roman', 12)}), 'fonts used: %s' % sorted(used)


def abstract_banner(d):
    """The first non-empty paragraph after the ABSTRACT header: author, title and counts, set as a block."""
    start = next((i for i, p in majors(d) if p['text'].strip().upper() == 'ABSTRACT'), None)
    if start is None:
        return None
    return next((p for p in d.paragraphs[start + 1:] if p['text'].strip()), None)


def utrgv_space_1(d, case, stage):
    """Running text double spaced with 0 pt before and after, and every paragraph first-line indented."""
    at, _ = find_refs(d)
    banner = abstract_banner(d)
    paras = [p for p in text_paras(d, at if at is not None else len(d.paragraphs)) if p['jc'] != 'center' and p is not banner]
    bad = ['%r spacing %.1f' % (p['text'][:30], spacing_ratio(p)) for p in paras if not 1.9 <= spacing_ratio(p) <= 2.1]
    bad += ['%r has space before/after' % p['text'][:30] for p in paras if p['before'] or p['after']]
    bad += ['%r not indented' % p['text'][:30] for p in paras if p['first'] <= 0]
    return fails(bad, '%d text paragraphs double spaced, 0 pt around, indented' % len(paras))


def margins(sect):
    m = sect.find(W + 'pgMar')
    return {k: int(m.get(W + k, 0)) for k in ('top', 'bottom', 'left', 'right', 'footer')} if m is not None else {}


def utrgv_margin_1(d, case, stage):
    """Left, right and bottom margins 1 inch; top 1 inch, or 2 inches on a major header page."""
    if not d.sections:
        return False, 'no section properties'
    bad = []
    for i, s in enumerate(d.sections):
        m = margins(s)
        for k in ('left', 'right', 'bottom'):
            if abs(m.get(k, 0) - INCH) > 20:
                bad.append('section %d %s %.2f in' % (i + 1, k, m.get(k, 0) / INCH))
        if min(abs(m.get('top', 0) - INCH), abs(m.get('top', 0) - 2 * INCH)) > 20:
            bad.append('section %d top %.2f in' % (i + 1, m.get('top', 0) / INCH))
    return fails(bad, '%d sections with UTRGV margins' % len(d.sections))


def utrgv_head_1(d, case, stage):
    """Major headers start a new page, in capitals, centered, not bold, not underlined, 2 inches from the top."""
    hs = majors(d)
    if not hs:
        return False, 'no major headers found'
    tops = [margins(s).get('top', 0) for s in d.sections] or [0]
    bad = []
    for i, p in hs:
        t = p['text'].strip()
        if t != t.upper():
            bad.append('%r not in capitals' % t)
        if p['jc'] != 'center':
            bad.append('%r %s' % (t, p['jc']))
        if any(r['b'] or r['u'] for r in p['runs'] if r['text'].strip()):
            bad.append('%r bold or underlined' % t)
        first = i == 0 or p['break_before'] or not any(q['text'].strip() for q in d.paragraphs[max(0, i - 1):i]) and d.paragraphs[i - 1]['break_before']
        if not first:
            bad.append('%r does not start a page' % t)
        if max(tops) < 2 * INCH - 20 and p['before'] < INCH - 20:
            bad.append('%r not 2 in from top (top margin %.2f in, %.0f pt before)' % (t, max(tops) / INCH, p['before'] / 20))
    return fails(bad, '%d major headers formatted' % len(hs))


def utrgv_ref_1(d, case, stage):
    """References under REFERENCES: alphabetical, hanging indent, single spaced inside an entry, a blank line between entries, only works cited."""
    at, entries = find_refs(d, 'references')
    if at is None:
        return False, 'no REFERENCES header'
    bad = [] if d.paragraphs[at]['text'].strip() == 'REFERENCES' else ['header is %r' % d.paragraphs[at]['text']]
    ok, ev = apa_ref_1(d, case, stage)
    if not ok:
        bad.append(ev)
    bad += ['%r no hanging indent' % e['text'][:30] for e in entries if e['hanging'] <= 0 or e['first'] > 0]
    bad += ['%r not single spaced' % e['text'][:30] for e in entries if spacing_ratio(e) > 1.2]
    gap = [e for e in entries if e['after'] < 200 and e['before'] < 200]
    blank_between = sum(1 for p in d.paragraphs[at + 1:] if not p['text'].strip()) >= len(entries) - 1
    if gap and not blank_between:
        bad.append('%d entries without a blank line after' % len(gap))
    return fails(bad, '%d references in UTRGV form' % len(entries))


def utrgv_abs_1(d, case, stage):
    """The abstract text after its banner paragraph has at most 150 words; hyphenated words count as two."""
    hs = majors(d)
    start = next((i for i, p in hs if p['text'].strip().upper() == 'ABSTRACT'), None)
    if start is None:
        return False, 'no ABSTRACT header'
    end = next((i for i, _ in hs if i > start), len(d.paragraphs))
    body = [p['text'] for p in d.paragraphs[start + 1:end] if p['text'].strip()][1:]
    words = sum(len(re.split(r'[\s\-–]+', t.strip())) for t in body)
    return (0 < words <= 150), '%d words after the banner' % words


def utrgv_cap_1(d, case, stage):
    """Table and figure titles read 'Table 1: Title', numbered in sequence; table titles above tables."""
    bad, seen = [], {'Table': [], 'Figure': []}
    for i, p in enumerate(d.paragraphs):
        m = re.match(r'^(Table|Figure)\s+(\d+(?:\.\d+)?)(\s*[:.\-–]?)\s*(.*)', p['text'].strip())
        if not m or p['in_table'] or len(p['text']) > 200:
            continue
        if m.group(3).strip() != ':':
            bad.append('%r lacks the colon' % p['text'][:30])
        seen[m.group(1)].append(m.group(2))
        if m.group(1) == 'Table' and i + 1 < len(d.paragraphs) and not d.paragraphs[i + 1]['in_table']:
            bad.append('%r is not directly above its table' % p['text'][:30])
    for kind, nums in seen.items():
        simple = [n for n in nums if '.' not in n]
        if simple and simple != [str(k) for k in range(1, len(simple) + 1)]:
            bad.append('%s numbering %s' % (kind, simple))
    if not any(seen.values()):
        return True, 'no table or figure titles'
    return fails(bad, 'captions numbered with colons')


def utrgv_page_1(d, case, stage):
    """Page numbers centered at the bottom, 0.5 inch from the edge."""
    bad, found = [], False
    for i, s in enumerate(d.sections):
        if abs(margins(s).get('footer', 0) - INCH // 2) > 20:
            bad.append('section %d footer distance %.2f in' % (i + 1, margins(s).get('footer', 0) / INCH))
        for ref in s.findall(W + 'footerReference'):
            f = d.footers.get(ref.get(R + 'id'))
            if f is None:
                continue
            instr = ''.join(x.text or '' for x in f.iter(W + 'instrText')) + ''.join(
                x.get(W + 'instr', '') for x in f.iter(W + 'fldSimple'))
            if 'PAGE' in instr:
                found = True
                jcs = [j.get(W + 'val') for j in f.iter(W + 'jc')]
                if 'center' not in jcs:
                    bad.append('section %d page number not centered' % (i + 1))
    if not found:
        bad.append('no PAGE field in any footer')
    return fails(bad, 'page numbers centered at the bottom')


RULES = {
    'APA-CIT-1': apa_cit_1, 'APA-CIT-2': apa_cit_2, 'APA-CIT-3': apa_cit_3,
    'APA-REF-1': apa_ref_1, 'APA-REF-2': apa_ref_2, 'APA-REF-3': apa_ref_3, 'APA-REF-4': apa_ref_4,
    'APA-REF-5': apa_ref_5, 'APA-REF-6': apa_ref_6, 'APA-REF-7': apa_ref_7, 'APA-REF-8': apa_ref_8,
    'APA-FMT-1': apa_fmt_1, 'APA-FMT-2': apa_fmt_2, 'APA-FMT-3': apa_fmt_3, 'APA-FMT-4': apa_fmt_4,
    'APA-FMT-5': apa_fmt_5,
    'IEEE-CIT-1': ieee_cit_1, 'IEEE-REF-1': ieee_ref_1,
    'UTRGV-FONT-1': utrgv_font_1, 'UTRGV-SPACE-1': utrgv_space_1, 'UTRGV-MARGIN-1': utrgv_margin_1,
    'UTRGV-HEAD-1': utrgv_head_1, 'UTRGV-REF-1': utrgv_ref_1, 'UTRGV-ABS-1': utrgv_abs_1,
    'UTRGV-CAP-1': utrgv_cap_1, 'UTRGV-PAGE-1': utrgv_page_1,
    'CASE-REFSET': case_refset,
}


def check(rule_id, path, case, stage):
    """Grade one rule on one file. Returns (passed, evidence); an unreadable file fails with the reason."""
    if rule_id not in RULES:
        raise KeyError('unknown rule %s' % rule_id)
    try:
        d = Docx(path)
    except (OSError, KeyError, zipfile.BadZipFile, ET.ParseError) as e:
        return False, 'unreadable docx: %s' % e
    try:
        return RULES[rule_id](d, case, stage)
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
        print('usage: refcheck.py FILE.docx [--case case.json] [--stage first|revision] [RULE ...] (%s)' % e, file=sys.stderr)
        return 2
    if not rules and case:
        rules = [c['rule'] for c in case.get('criteria', []) if c.get('grader') == 'script' and c['stage'] in ('both', stage)]
    rules = rules or [r for r in RULES if r.startswith('APA')]
    ok = True
    for r in rules:
        passed, evidence = check(r, path, case, stage)
        ok &= passed
        print(json.dumps(dict(rule=r, passed=passed, evidence=evidence)))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
