"""Horizon Europe proposal checks (application form Part B, RIA and IA) for a Word file. Standard library only.

check(rule_id, path, case, stage) -> (passed, evidence)

HE-PAGE      The page is A4 and every margin is at least 15 mm.
HE-FONT      Body text, including text in tables, resolves to at least 11 points.
HE-SPACING   Line spacing is at least single and character spacing is not condensed.
HE-SECTIONS  The form's numbered sections appear as headings, in the form's order.

Rules follow the European Commission's "EU Grants: Application form (HE RIA and IA)", version 5.1
of 22.01.2026. The page limit itself is a render criterion on the case.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import layout
from layout import W, q

REQUIRED = ['Excellence', 'Objectives and ambition', 'Methodology', 'Impact', "Project's pathways towards impact",
            'Measures to maximise impact', 'Quality and efficiency of the implementation', 'Work plan and resources',
            'Capacity of participants and consortium as a whole']
OPTIONAL = 'Summary'
MM = 1440 / 25.4


def clean(s):
    s = re.sub(r'^[\d.\s]+', '', s).replace('’', "'").strip().lower()
    return re.sub(r'\s+', ' ', s)


def check(rule_id, path, case, stage):
    parts = layout.load(path)
    by_id, by_name, default = layout.styles_of(parts)
    doc = parts['word/document.xml']
    if rule_id == 'HE-PAGE':
        sects = list(doc.iter(q('sectPr')))
        if not sects:
            return False, 'no section properties'
        for s in sects:
            sz, mar = s.find(q('pgSz')), s.find(q('pgMar'))
            if sz is None or mar is None:
                return False, 'a section has no page size or margins'
            w, h = sorted((int(sz.get(q('w'))), int(sz.get(q('h')))))
            if abs(w - 11906) > 30 or abs(h - 16838) > 30:
                return False, 'page is %d x %d twips, not A4' % (w, h)
            for side in ('top', 'bottom', 'left', 'right'):
                got = int(mar.get(q(side)))
                if got < 15 * MM - 5:
                    return False, '%s margin is %.1f mm, the form requires at least 15 mm' % (side, got / MM)
        return True, 'A4 with every margin at least 15 mm'
    if rule_id == 'HE-FONT':
        small, n = {}, 0
        for part, name, runs in layout.paragraphs({'word/document.xml': doc}, by_id, by_name):
            low = name.lower()
            if low.startswith('heading') or low in ('title', 'subtitle', 'caption') or 'footnote' in low:
                continue
            for text, rpr, chain in runs:
                n += 1
                size = layout.resolve(layout.size_of, rpr, chain, by_id, default)
                if size is None or size < 11:
                    small.setdefault('%s pt' % size, text[:40])
        if not n:
            return False, 'no body text'
        if small:
            return False, 'below 11 pt: ' + '; '.join('%s in "%s"' % kv for kv in list(small.items())[:3])
        return True, 'all %d body and table runs are at least 11 pt' % n
    if rule_id == 'HE-SPACING':
        for p in doc.iter(q('p')):
            sp = p.find(q('pPr') + '/' + q('spacing'))
            if sp is not None and sp.get(q('line')) and sp.get(q('lineRule'), 'auto') == 'auto' and int(sp.get(q('line'))) < 240:
                return False, 'a paragraph has line spacing %.2f, below single' % (int(sp.get(q('line'))) / 240)
        for r in doc.iter(q('rPr')):
            sp = r.find(q('spacing'))
            if sp is not None and int(sp.get(q('val'), '0')) < 0:
                return False, 'character spacing is condensed'
        return True, 'line spacing is at least single and character spacing is standard'
    if rule_id == 'HE-SECTIONS':
        heads = []
        for part, name, runs in layout.paragraphs({'word/document.xml': doc}, by_id, by_name):
            if name.lower().startswith('heading'):
                heads.append(clean(''.join(t for t, _, _ in runs)))
        pos = -1
        for want in REQUIRED:
            hit = next((i for i, h in enumerate(heads) if i > pos and h.startswith(clean(want))), None)
            if hit is None:
                return False, 'section "%s" is missing or out of order; headings are %s' % (want, heads[:12])
            pos = hit
        if case.get('truth', {}).get('summary_absent', {}).get(stage) and any(h.startswith(OPTIONAL.lower()) for h in heads):
            return False, 'the optional Summary section is still present'
        return True, 'all %d required sections are headings in the form\'s order' % len(REQUIRED)
    return False, 'unknown rule %s' % rule_id
