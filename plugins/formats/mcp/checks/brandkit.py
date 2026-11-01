"""Brand-kit checks for decks against a case's kit truth. Standard library only.

check(rule_id, path, case, stage) -> (passed, evidence)

KIT-RATIO   The slide size has the kit's ratio.
KIT-COUNT   The deck has the number of slides this stage asks for.
KIT-FONT    Every text run resolves to a kit font, set on the run or through the theme fonts.
KIT-COLOR   Every colour written on a slide is in the palette, and every text run has a palette colour.
KIT-WORDS   No slide exceeds the word limit or the body-paragraph limit (footer exempt).
KIT-MINPT   No text run is smaller than the minimum size (footer exempt).
KIT-FOOTER  The footer text is on every slide.
KIT-TITLE   Every slide has text in a title placeholder.
KIT-BOUNDS  No shape extends past the slide edge.
KIT-PLAIN   Nothing decorative: no drawn shape without text and no shadow, unless the kit's style asks for a title rule.
"""
import re
import zipfile
from xml.etree import ElementTree as ET

A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
P = '{http://schemas.openxmlformats.org/presentationml/2006/main}'


def deck(path):
    z = zipfile.ZipFile(path)
    pres = ET.fromstring(z.read('ppt/presentation.xml'))
    rels = ET.fromstring(z.read('ppt/_rels/presentation.xml.rels'))
    target = {r.get('Id'): r.get('Target') for r in rels}
    rid = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
    slides = []
    for s in pres.find(P + 'sldIdLst') if pres.find(P + 'sldIdLst') is not None else []:
        t = target[s.get(rid)]
        slides.append(ET.fromstring(z.read('ppt/' + t.lstrip('/').replace('ppt/', ''))))
    size = pres.find(P + 'sldSz')
    themes = [ET.fromstring(z.read(n)) for n in z.namelist() if re.fullmatch(r'ppt/theme/theme\d+\.xml', n)]
    return slides, (int(size.get('cx')), int(size.get('cy'))), themes


def theme_fonts(themes):
    out = {}
    for t in themes[:1]:
        for kind, key in (('majorFont', '+mj-lt'), ('minorFont', '+mn-lt')):
            el = t.find('.//' + A + kind + '/' + A + 'latin')
            if el is not None:
                out[key] = el.get('typeface')
    return out


def theme_text_colour(themes):
    for t in themes[:1]:
        dk = t.find('.//' + A + 'dk1')
        if dk is not None:
            c = dk.find(A + 'srgbClr')
            if c is not None:
                return c.get('val').upper()
            s = dk.find(A + 'sysClr')
            if s is not None:
                return (s.get('lastClr') or '').upper()
    return None


def shapes(slide):
    """Yield (is_title, text, runs, xfrm) for each shape with a text body; runs are (text, rPr)."""
    for sp in slide.iter(P + 'sp'):
        ph = sp.find(P + 'nvSpPr/' + P + 'nvPr/' + P + 'ph')
        is_title = ph is not None and ph.get('type') in ('title', 'ctrTitle')
        body = sp.find(P + 'txBody')
        paras = []
        if body is not None:
            for p in body.findall(A + 'p'):
                runs = [(''.join(t.text or '' for t in r.findall(A + 't')), r.find(A + 'rPr')) for r in p.findall(A + 'r')]
                runs = [x for x in runs if x[0].strip()]
                if runs:
                    paras.append(runs)
        xfrm = sp.find(P + 'spPr/' + A + 'xfrm')
        yield is_title, paras, xfrm


def text_of(paras):
    return ' '.join(''.join(t for t, _ in runs) for runs in paras).strip()


def check(rule_id, path, case, stage):
    truth = case['truth']
    kit = truth['kit']
    palette = {c.upper().lstrip('#') for c in truth['palette'][stage]}
    footer = kit['footer']
    slides, (cx, cy), themes = deck(path)
    if rule_id == 'KIT-RATIO':
        a, b = (int(x) for x in kit['slide_ratio'].split(':'))
        ok = abs(cx / cy - a / b) < 0.01
        return ok, 'slide is %d x %d EMU, ratio %.3f, expected %s' % (cx, cy, cx / cy, kit['slide_ratio'])
    if rule_id == 'KIT-COUNT':
        want = truth['slides'][stage]
        return len(slides) == want, '%d slides, expected %d' % (len(slides), want)
    fonts = set(kit['fonts'].values())
    tf = theme_fonts(themes)
    problems, n = [], 0
    for i, slide in enumerate(slides, 1):
        sh = list(shapes(slide))
        is_footer = lambda paras: text_of(paras) == footer
        if rule_id == 'KIT-FONT':
            for is_title, paras, _x in sh:
                for runs in paras:
                    for text, rpr in runs:
                        n += 1
                        latin = rpr.find(A + 'latin') if rpr is not None else None
                        face = latin.get('typeface') if latin is not None else None
                        if face in tf:
                            face = tf[face]
                        if face is None:
                            face = tf.get('+mj-lt') if is_title else tf.get('+mn-lt')
                        if face not in fonts:
                            problems.append('slide %d "%s" uses %s' % (i, text[:30], face))
        elif rule_id == 'KIT-COLOR':
            for c in slide.iter(A + 'srgbClr'):
                if c.get('val', '').upper() not in palette:
                    problems.append('slide %d uses #%s' % (i, c.get('val')))
            default = theme_text_colour(themes)
            for _, paras, _ in sh:
                for runs in paras:
                    for text, rpr in runs:
                        n += 1
                        fill = rpr.find(A + 'solidFill') if rpr is not None else None
                        if fill is None and default not in palette:
                            problems.append('slide %d "%s" has no palette colour set' % (i, text[:30]))
        elif rule_id == 'KIT-WORDS':
            body = [(t, paras) for t, paras, _ in sh if not is_footer(paras)]
            words = sum(len(text_of(paras).split()) for _, paras in body)
            bullets = sum(len(paras) for t, paras in body if not t)
            n += 1
            if words > kit['limits']['max_words_per_slide']:
                problems.append('slide %d has %d words' % (i, words))
            if bullets > kit['limits']['max_body_paragraphs']:
                problems.append('slide %d has %d body paragraphs' % (i, bullets))
        elif rule_id == 'KIT-MINPT':
            for _, paras, _ in sh:
                if is_footer(paras):
                    continue
                for runs in paras:
                    for text, rpr in runs:
                        n += 1
                        sz = rpr.get('sz') if rpr is not None else None
                        if sz is None:
                            problems.append('slide %d "%s" has no size set' % (i, text[:30]))
                        elif int(sz) < kit['limits']['min_font_pt'] * 100:
                            problems.append('slide %d "%s" is %.1f pt' % (i, text[:30], int(sz) / 100))
        elif rule_id == 'KIT-FOOTER':
            n += 1
            if not any(is_footer(paras) for _, paras, _ in sh):
                problems.append('slide %d has no footer "%s"' % (i, footer))
        elif rule_id == 'KIT-TITLE':
            n += 1
            if not any(t and text_of(paras) for t, paras, _ in sh):
                problems.append('slide %d has no text in a title placeholder' % i)
        elif rule_id == 'KIT-PLAIN':
            allowed = 1 if (kit.get('style') or {}).get('title_rule') else 0
            drawn = [sp for sp in slide.iter(P + 'sp') if sp.find(P + 'spPr/' + A + 'prstGeom') is not None
                     and sp.find(P + 'nvSpPr/' + P + 'nvPr/' + P + 'ph') is None
                     and not ''.join(x.text or '' for x in sp.iter(A + 't')).strip()]
            n += 1
            if len(drawn) > allowed:
                problems.append('slide %d has %d drawn shape(s) that carry no text; the kit allows %d' % (i, len(drawn), allowed))
            if any(True for _ in slide.iter(A + 'outerShdw')):
                problems.append('slide %d has a shadow' % i)
        elif rule_id == 'KIT-BOUNDS':
            for x in slide.iter(A + 'xfrm'):
                off, ext = x.find(A + 'off'), x.find(A + 'ext')
                if off is None or ext is None:
                    continue
                n += 1
                l, t, w, h = int(off.get('x')), int(off.get('y')), int(ext.get('cx')), int(ext.get('cy'))
                if l < 0 or t < 0 or l + w > cx + 1 or t + h > cy + 1:
                    problems.append('slide %d has a shape past the slide edge' % i)
        else:
            return False, 'unknown rule %s' % rule_id
    if not slides:
        return False, 'no slides'
    if problems:
        return False, '; '.join(problems[:3]) + (' (+%d more)' % (len(problems) - 3) if len(problems) > 3 else '')
    return True, '%d slides checked, %d items, none outside the kit' % (len(slides), n)
