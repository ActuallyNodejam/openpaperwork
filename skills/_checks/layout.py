"""House-style checks for Word files against a case's style truth. Standard library only.

check(rule_id, path, case, stage) -> (passed, evidence)

LAY-PAGE  Page size and all four margins match the style, in every section.
LAY-FONT  One font family: every font the text resolves to, through runs, styles and defaults,
          is the style font. A font left to the theme counts as a different font.
LAY-SIZE  Body text resolves to the style's point size.
LAY-HEAD  Each expected section title is a paragraph in the built-in Heading 1 style, in order,
          and the title uses the built-in Title style.
LAY-FOOT  A footer carries a PAGE field.
"""
import re
import zipfile
from xml.etree import ElementTree as ET

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
PAGES = {'A4': (11906, 16838), 'LETTER': (12240, 15840)}
TWIPS_PER_MM = 1440 / 25.4


def q(tag):
    return W + tag


def load(path):
    z = zipfile.ZipFile(path)
    parts = {n: ET.fromstring(z.read(n)) for n in z.namelist()
             if re.fullmatch(r'word/(document|styles|footer\d*|header\d*)\.xml', n)}
    return parts


def styles_of(parts):
    """Return ({styleId: element}, {style name lower: styleId}, default rPr element or None)."""
    root = parts.get('word/styles.xml')
    by_id, by_name, default = {}, {}, None
    if root is None:
        return by_id, by_name, default
    dd = root.find(q('docDefaults'))
    if dd is not None:
        default = dd.find(q('rPrDefault') + '/' + q('rPr'))
    for s in root.findall(q('style')):
        sid = s.get(q('styleId'))
        by_id[sid] = s
        name = s.find(q('name'))
        if name is not None:
            by_name[name.get(q('val'), '').lower()] = sid
    return by_id, by_name, default


def font_of(rpr):
    if rpr is None:
        return None
    f = rpr.find(q('rFonts'))
    if f is None:
        return None
    if f.get(q('asciiTheme')) or f.get(q('hAnsiTheme')):
        return 'theme font (%s)' % (f.get(q('asciiTheme')) or f.get(q('hAnsiTheme')))
    return f.get(q('ascii')) or f.get(q('hAnsi'))


def size_of(rpr):
    if rpr is None:
        return None
    s = rpr.find(q('sz'))
    return int(s.get(q('val'))) / 2 if s is not None else None


def resolve(getter, run_rpr, style_ids, by_id, default):
    """First value found on the run, then each style and its ancestors, then the document default."""
    v = getter(run_rpr)
    if v is not None:
        return v
    for sid in style_ids:
        seen = set()
        while sid and sid in by_id and sid not in seen:
            seen.add(sid)
            v = getter(by_id[sid].find(q('rPr')))
            if v is not None:
                return v
            based = by_id[sid].find(q('basedOn'))
            sid = based.get(q('val')) if based is not None else None
    return getter(default)


def paragraphs(parts, by_id, by_name):
    normal = next((sid for sid, s in by_id.items() if s.get(q('type')) == 'paragraph' and s.get(q('default')) in ('1', 'true')), None)
    for part_name, root in parts.items():
        if part_name == 'word/styles.xml':
            continue
        for p in root.iter(q('p')):
            ppr = p.find(q('pPr'))
            ps = ppr.find(q('pStyle')) if ppr is not None else None
            pstyle = ps.get(q('val')) if ps is not None else normal
            name = ''
            if pstyle in by_id and by_id[pstyle].find(q('name')) is not None:
                name = by_id[pstyle].find(q('name')).get(q('val'), '')
            runs = []
            for r in p.iter(q('r')):
                text = ''.join(t.text or '' for t in r.findall(q('t')))
                if not text.strip():
                    continue
                rpr = r.find(q('rPr'))
                rs = rpr.find(q('rStyle')) if rpr is not None else None
                chain = [x for x in ((rs.get(q('val')) if rs is not None else None), pstyle) if x]
                runs.append((text, rpr, chain))
            yield part_name, name, runs


def check(rule_id, path, case, stage):
    truth = case['truth']
    style = truth['style']
    parts = load(path)
    by_id, by_name, default = styles_of(parts)
    doc = parts['word/document.xml']
    if rule_id == 'LAY-PAGE':
        want_w, want_h = PAGES[style['page'].upper()]
        mm = truth['margins_mm'][stage]
        want_m = mm * TWIPS_PER_MM
        sects = list(doc.iter(q('sectPr')))
        if not sects:
            return False, 'no section properties'
        for s in sects:
            sz, mar = s.find(q('pgSz')), s.find(q('pgMar'))
            if sz is None or mar is None:
                return False, 'a section has no page size or margins'
            w, h = int(sz.get(q('w'))), int(sz.get(q('h')))
            if abs(w - want_w) > 30 or abs(h - want_h) > 30:
                return False, 'page is %d x %d twips, expected %s (%d x %d)' % (w, h, style['page'], want_w, want_h)
            for side in ('top', 'bottom', 'left', 'right'):
                got = int(mar.get(q(side)))
                if abs(got - want_m) > 30:
                    return False, '%s margin is %.1f mm, expected %s mm' % (side, got / TWIPS_PER_MM, mm)
        return True, '%s with %s mm margins in %d section(s)' % (style['page'], mm, len(sects))
    if rule_id in ('LAY-FONT', 'LAY-SIZE'):
        bad, n = {}, 0
        for part, name, runs in paragraphs(parts, by_id, by_name):
            heading = name.lower().startswith('heading') or name.lower() == 'title'
            for text, rpr, chain in runs:
                n += 1
                if rule_id == 'LAY-FONT':
                    f = resolve(font_of, rpr, chain, by_id, default)
                    if f != style['font']:
                        bad.setdefault(f or 'no font set', text[:40])
                elif not heading and part == 'word/document.xml':
                    s = resolve(size_of, rpr, chain, by_id, default)
                    if s != style['body_pt']:
                        bad.setdefault('%s pt' % s, text[:40])
        if not n:
            return False, 'no text runs'
        if bad:
            return False, 'not %s: %s' % (style['font'] if rule_id == 'LAY-FONT' else '%s pt' % style['body_pt'],
                                          '; '.join('%s in "%s"' % kv for kv in list(bad.items())[:3]))
        return True, 'all %d text runs resolve to %s' % (n, style['font'] if rule_id == 'LAY-FONT' else '%s pt body' % style['body_pt'])
    if rule_id == 'LAY-HEAD':
        heads, titles = [], []
        for part, name, runs in paragraphs({'word/document.xml': doc}, by_id, by_name):
            text = ''.join(t for t, _, _ in runs).strip()
            if name.lower() == 'heading 1':
                heads.append(text)
            if name.lower() == 'title':
                titles.append(text)
        want = truth['sections'][stage]
        clean = lambda s: re.sub(r'^[\d.\s]+', '', s).strip().lower()
        if [clean(h) for h in heads] != [w.lower() for w in want]:
            return False, 'Heading 1 paragraphs are %s, expected %s' % (heads, want)
        if not titles:
            return False, 'no paragraph in the built-in Title style'
        return True, '%d sections in Heading 1 and a Title paragraph' % len(heads)
    if rule_id == 'LAY-FOOT':
        for name, root in parts.items():
            if 'footer' not in name:
                continue
            fields = [f.get(q('instr'), '') for f in root.iter(q('fldSimple'))] + [i.text or '' for i in root.iter(q('instrText'))]
            if any(re.search(r'\bPAGE\b', f) for f in fields):
                return True, 'PAGE field in %s' % name.split('/')[-1]
        return False, 'no footer carries a PAGE field'
    return False, 'unknown rule %s' % rule_id
