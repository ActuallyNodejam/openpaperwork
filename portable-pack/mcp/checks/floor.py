"""The every-file floor: checks any Word, Excel or PowerPoint output should pass, whatever the task.

check(rule_id, path, case, stage) -> (passed, evidence). Needs python-docx, python-pptx, openpyxl.

FLOOR-FONT      At most two font families in the file, resolved through runs, styles and the theme.
FLOOR-OVERFLOW  No text is estimated to overflow its slide shape or its spreadsheet cell.
FLOOR-CONTRAST  Text with a set colour has enough contrast against its set background.
FLOOR-FORMULA   Spreadsheet formulas carry saved results and none is an error value.
FLOOR-OVERLAP   No slide text is hidden behind a picture or an opaque shape drawn over it.
FLOOR-META      The file has a title; slides have titles; pictures have alternative text;
                sheets are named; documents declare a language.

The slide overflow estimate, the dark-on-dark rule and the formula and picture issue types are
ported from OfficeCLI (Apache-2.0, Copyright 2026 OfficeCLI), see THIRD_PARTY.md: character width
0.55 x font size, line pitch 1.2 x font size, default insets 0.1 in and 0.05 in, 5 percent
tolerance, shapes with autofit skipped; fill under 30 percent and text under 80 percent brightness.
The hidden-text rule is also OfficeCLI's: a later opaque shape covering at least 20 percent of a text
shape. Two changes here: pictures count as opaque, and the covered share is measured against the
estimated text, not the whole box, so a short line beside a picture is not flagged.
The contrast ratio is the WCAG 2.2 formula (4.5:1, or 3:1 for large text).
"""
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
P = '{http://schemas.openxmlformats.org/presentationml/2006/main}'
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
EMU_PER_PT = 12700.0
ERRORS = ('#REF!', '#DIV/0!', '#VALUE!', '#NAME?', '#N/A', '#NUM!', '#NULL!')


def fmt_of(path):
    return Path(path).suffix.lower().lstrip('.')


def rgb(hex6):
    h = hex6.strip().lstrip('#')
    if len(h) == 8:
        h = h[2:]
    if len(h) != 6 or not re.fullmatch(r'[0-9A-Fa-f]{6}', h):
        return None
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def brightness(c):
    return c[0] * 0.299 + c[1] * 0.587 + c[2] * 0.114


def ratio(fg, bg):
    def lum(c):
        ch = []
        for v in c:
            v = v / 255.0
            ch.append(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
        return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]
    a, b = lum(fg), lum(bg)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def theme_fonts(z, name):
    try:
        t = ET.fromstring(z.read(name))
    except KeyError:
        return {}
    out = {}
    for kind, key in (('majorFont', 'major'), ('minorFont', 'minor')):
        el = t.find('.//' + A + kind + '/' + A + 'latin')
        if el is not None:
            out[key] = el.get('typeface')
    return out


# ---------- Word ----------

def docx_fonts(path):
    import layout
    parts = layout.load(path)
    by_id, by_name, default = layout.styles_of(parts)
    z = zipfile.ZipFile(path)
    tf = theme_fonts(z, 'word/theme/theme1.xml')
    fams = {}
    for part, name, runs in layout.paragraphs(parts, by_id, by_name):
        for text, rpr, chain in runs:
            f = layout.resolve(layout.font_of, rpr, chain, by_id, default) or 'unset'
            m = re.match(r'theme font \((major|minor)', f)
            if m:
                f = tf.get(m.group(1), f)
            fams.setdefault(f, text[:30])
    return fams


def docx_contrast(path):
    import docx
    bad, n = [], 0
    for p in docx.Document(path).paragraphs:
        for r in p.runs:
            if not r.text.strip():
                continue
            col = r._r.find(W + 'rPr/' + W + 'color')
            if col is None or col.get(W + 'val') in (None, 'auto'):
                continue
            fg = rgb(col.get(W + 'val'))
            shd = r._r.find(W + 'rPr/' + W + 'shd')
            bg = rgb(shd.get(W + 'fill')) if shd is not None and shd.get(W + 'fill') not in (None, 'auto') else (255, 255, 255)
            if fg is None or bg is None:
                continue
            n += 1
            size = r.font.size.pt if r.font.size else 11
            need = 3.0 if size >= 18 or (size >= 14 and r.bold) else 4.5
            if ratio(fg, bg) < need:
                bad.append('"%s" %.1f:1' % (r.text[:25], ratio(fg, bg)))
    return bad, n


# ---------- PowerPoint ----------

def pptx_shapes(path):
    from pptx import Presentation
    prs = Presentation(path)
    for i, slide in enumerate(prs.slides, 1):
        bg = slide._element.find('.//' + P + 'bg//' + A + 'srgbClr')
        back = rgb(bg.get('val')) if bg is not None else (255, 255, 255)
        for sh in slide.shapes:
            yield i, slide, sh, back


def pptx_fonts(path):
    z = zipfile.ZipFile(path)
    tf = theme_fonts(z, 'ppt/theme/theme1.xml')
    fams = {}
    for i, slide, sh, _ in pptx_shapes(path):
        if not sh.has_text_frame:
            continue
        is_title = sh.is_placeholder and sh.placeholder_format.type is not None and 'TITLE' in str(sh.placeholder_format.type)
        for para in sh.text_frame.paragraphs:
            for r in para.runs:
                if not r.text.strip():
                    continue
                f = r.font.name
                if f in ('+mj-lt', '+mn-lt') or f is None:
                    f = tf.get('major' if (f == '+mj-lt' or (f is None and is_title)) else 'minor', 'theme')
                fams.setdefault(f, r.text[:30])
    return fams


def pptx_overflow(path):
    """Port of OfficeCLI CheckTextOverflow: estimated wrapped height against the usable box."""
    bad, n = [], 0
    for i, slide, sh, _ in pptx_shapes(path):
        if not sh.has_text_frame or not sh.text_frame.text.strip() or sh.width is None or sh.height is None:
            continue
        body = sh.text_frame._txBody.find(A + 'bodyPr')
        if body is not None and (body.find(A + 'normAutofit') is not None or body.find(A + 'spAutoFit') is not None):
            continue
        inset = lambda k, d: int(body.get(k)) if body is not None and body.get(k) is not None else d
        usable_w = sh.width / EMU_PER_PT - (inset('lIns', 91440) + inset('rIns', 91440)) / EMU_PER_PT
        usable_h = sh.height / EMU_PER_PT - (inset('tIns', 45720) + inset('bIns', 45720)) / EMU_PER_PT
        if usable_w <= 0 or usable_h <= 0:
            bad.append('slide %d: a text shape is smaller than its margins' % i)
            continue
        size = 0.0
        for para in sh.text_frame.paragraphs:
            for r in para.runs:
                if r.font.size:
                    size = max(size, r.font.size.pt)
        size = size or 18.0
        pitch = size * 1.2
        lines = 0
        for para in sh.text_frame.paragraphs:
            for seg in (para.text or '').split('\n'):
                count, width = 1, 0.0
                for ch in seg:
                    cw = size if ord(ch) > 0x2E7F else size * 0.55
                    if width + cw > usable_w and width > 0:
                        count += 1
                        width = cw
                    else:
                        width += cw
                lines += count
        n += 1
        if lines * pitch > usable_h * 1.05:
            bad.append('slide %d "%s": %d lines at %.0f pt need %.0f pt, box has %.0f pt' % (
                i, sh.text_frame.text[:25].replace('\n', ' '), lines, size, lines * pitch, usable_h))
    return bad, n


def pptx_overlap(path):
    """Text covered by a later picture or opaque shape (port of OfficeCLI's occlusion rule, see the module note)."""
    from pptx import Presentation
    from pptx.enum.text import MSO_ANCHOR
    bad, n = [], 0
    for i, slide in enumerate(Presentation(path).slides, 1):
        items = []
        for sh in slide.shapes:
            if None in (sh.left, sh.top, sh.width, sh.height):
                items.append(None)
                continue
            is_pic = sh.shape_type == 13
            sppr = sh._element.find(P + 'spPr')
            opaque = is_pic
            if not is_pic and sppr is not None and sh._element.tag == P + 'sp':
                solid = sppr.find(A + 'solidFill')
                if solid is not None:
                    alpha = solid.find('.//' + A + 'alpha')
                    opaque = alpha is None or int(alpha.get('val', '100000')) >= 80000
                elif any(sppr.find(A + k) is not None for k in ('gradFill', 'blipFill', 'pattFill')):
                    opaque = True
                elif sppr.find(A + 'noFill') is None:
                    # No fill written on the shape: a drawn shape then takes its fill from the theme style.
                    ref = sh._element.find(P + 'style/' + A + 'fillRef')
                    opaque = ref is not None and ref.get('idx') not in (None, '0')
            text = sh.text_frame.text.strip() if sh.has_text_frame else ''
            rect = None
            if text:
                size = max([r.font.size.pt for para in sh.text_frame.paragraphs for r in para.runs if r.font.size] or [18.0])
                box_w = sh.width / EMU_PER_PT
                lines, longest = 0, 0.0
                for seg in text.split('\n'):
                    w = len(seg) * size * 0.55
                    lines += max(1, -(-int(w) // max(1, int(box_w))))
                    longest = max(longest, min(w, box_w))
                tw, th = longest * EMU_PER_PT, min(lines * size * 1.2 * EMU_PER_PT, sh.height)
                anchor = sh.text_frame.vertical_anchor
                top = sh.top + (sh.height - th) / 2 if anchor == MSO_ANCHOR.MIDDLE else sh.top + sh.height - th if anchor == MSO_ANCHOR.BOTTOM else sh.top
                rect = (sh.left, top, tw, th)
            items.append(dict(box=(sh.left, sh.top, sh.width, sh.height), opaque=opaque and not text, text=text, rect=rect))
        for k, a in enumerate(items):
            if not a or not a['rect']:
                continue
            n += 1
            ax, ay, aw, ah = a['rect']
            if aw <= 0 or ah <= 0:
                continue
            covered = 0.0
            for b in items[k + 1:]:
                if not b or not b['opaque']:
                    continue
                bx, by, bw, bh = b['box']
                iw = min(ax + aw, bx + bw) - max(ax, bx)
                ih = min(ay + ah, by + bh) - max(ay, by)
                if iw > 0 and ih > 0:
                    covered += iw * ih  # shapes drawn over the text add up; overlaps between them are counted once too often at worst
            if covered * 5 >= aw * ah:
                bad.append('slide %d: "%s" is behind a picture or filled shape' % (i, a['text'][:30].replace('\n', ' ')))
    return bad, n


def pptx_contrast(path):
    bad, n = [], 0
    below = {}  # slide number -> filled shapes seen so far, in drawing order
    for i, slide, sh, back in pptx_shapes(path):
        fill = sh._element.find(P + 'spPr/' + A + 'solidFill/' + A + 'srgbClr')
        seen = below.setdefault(i, [])
        if not sh.has_text_frame:
            if fill is not None and None not in (sh.left, sh.top, sh.width, sh.height):
                seen.append((sh.left, sh.top, sh.left + sh.width, sh.top + sh.height, rgb(fill.get('val'))))
            continue
        bg = rgb(fill.get('val')) if fill is not None else back
        if fill is None and None not in (sh.left, sh.top, sh.width, sh.height):
            # Text with no fill of its own sits on whatever filled shape was drawn under its centre.
            cx, cy = sh.left + sh.width / 2, sh.top + sh.height / 2
            for l, t, r, b, colour in seen:
                if l <= cx <= r and t <= cy <= b and colour is not None:
                    bg = colour
        if fill is not None and None not in (sh.left, sh.top, sh.width, sh.height):
            seen.append((sh.left, sh.top, sh.left + sh.width, sh.top + sh.height, rgb(fill.get('val'))))
        for para in sh.text_frame.paragraphs:
            for r in para.runs:
                if not r.text.strip():
                    continue
                c = r._r.find(A + 'rPr/' + A + 'solidFill/' + A + 'srgbClr')
                if c is None or bg is None:
                    continue
                fg = rgb(c.get('val'))
                if fg is None:
                    continue
                n += 1
                size = r.font.size.pt if r.font.size else 18
                need = 3.0 if size >= 18 or (size >= 14 and r.font.bold) else 4.5
                dark_on_dark = fill is not None and brightness(bg) < 0.30 * 255 and brightness(fg) < 0.80 * 255
                if ratio(fg, bg) < need or dark_on_dark:
                    bad.append('slide %d "%s" %.1f:1' % (i, r.text[:25], ratio(fg, bg)))
    return bad, n


def pptx_meta(path):
    from pptx import Presentation
    prs = Presentation(path)
    bad = []
    if not (prs.core_properties.title or '').strip():
        bad.append('the deck has no title in its properties')
    for i, slide in enumerate(prs.slides, 1):
        t = slide.shapes.title
        if t is None or not t.text_frame.text.strip():
            bad.append('slide %d has no title' % i)
        for kind, missing in pptx_alt_missing(slide._element):
            bad.append('slide %d has a %s without alternative text' % (i, kind))
    return bad


def pptx_alt_missing(slide_element):
    """Pictures and charts on a slide that carry no alternative text."""
    out = []
    for pic in slide_element.iter(P + 'pic'):
        c = pic.find(P + 'nvPicPr/' + P + 'cNvPr')
        if c is None or not (c.get('descr') or '').strip():
            out.append(('picture', pic))
    for gf in slide_element.iter(P + 'graphicFrame'):
        if gf.find('.//{http://schemas.openxmlformats.org/drawingml/2006/chart}chart') is None:
            continue
        c = gf.find(P + 'nvGraphicFramePr/' + P + 'cNvPr')
        if c is None or not (c.get('descr') or '').strip():
            out.append(('chart', gf))
    return out


# ---------- Excel ----------

def xlsx_books(path):
    import openpyxl
    return openpyxl.load_workbook(path), openpyxl.load_workbook(path, data_only=True)


def xlsx_fonts(path):
    wf, _ = xlsx_books(path)
    fams = {}
    for ws in wf.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if c.value is not None and c.font is not None and c.font.name:
                    fams.setdefault(c.font.name, '%s!%s' % (ws.title, c.coordinate))
    return fams


def shown(value, number_format):
    """Rough displayed text of a number under its format: enough to compare with the column width."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return str(value)
    f = number_format or 'General'
    if f == 'General':
        return None
    dec = len(re.sub(r'[^0#]', '', f.split('.')[1].split(';')[0])) if '.' in f else 0
    v = value * 100 if '%' in f else value
    s = ('{:,.%df}' % dec).format(v) if ',' in f else ('{:.%df}' % dec).format(v)
    extra = len(re.findall(r'"([^"]*)"', f)[0]) if re.findall(r'"([^"]*)"', f) else 0
    return s + ('%' if '%' in f else '') + 'x' * extra


def xlsx_overflow(path):
    from openpyxl.utils import get_column_letter
    wf, wv = xlsx_books(path)
    bad, n = [], 0
    for ws in wf.worksheets:
        vs = wv[ws.title]
        merged = {c for rng in ws.merged_cells.ranges for row in ws[rng.coord] for c in [cell.coordinate for cell in row]}
        for row in ws.iter_rows():
            for c in row:
                v = vs[c.coordinate].value
                if v is None or c.coordinate in merged:
                    continue
                width = ws.column_dimensions[get_column_letter(c.column)].width or 8.43
                n += 1
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    text = shown(v, c.number_format)
                    if text is not None and len(text) > width + 0.5:
                        bad.append('%s!%s shows "%s" in a column %.0f wide' % (ws.title, c.coordinate, text, width))
                    continue
                if not isinstance(v, str):
                    continue  # dates and booleans render by their format, not by str()
                text = v
                wrap = bool(c.alignment and c.alignment.wrap_text)
                if wrap:
                    rd = ws.row_dimensions[c.row]
                    if rd.height:
                        size = (c.font.size if c.font and c.font.size else 11)
                        lines = sum(max(1, -(-len(seg) // max(1, int(width)))) for seg in text.split('\n'))
                        if lines * size * 1.2 > rd.height * 1.05:
                            bad.append('%s!%s needs %d lines, the row fits %.1f' % (ws.title, c.coordinate, lines, rd.height / (size * 1.2)))
                else:
                    right = vs.cell(c.row, c.column + 1).value
                    if right is not None and len(text) > width * 1.25 + 1:
                        bad.append('%s!%s text of %d characters is cut by the next cell (column %.0f wide)' % (ws.title, c.coordinate, len(text), width))
    return bad, n


def xlsx_contrast(path):
    wf, _ = xlsx_books(path)
    bad, n = [], 0
    for ws in wf.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if c.value is None or c.font is None or c.font.color is None or c.font.color.type != 'rgb' or not c.font.color.rgb:
                    continue
                fg = rgb(str(c.font.color.rgb))
                bg = (255, 255, 255)
                if c.fill is not None and c.fill.fill_type == 'solid' and c.fill.fgColor is not None and c.fill.fgColor.type == 'rgb':
                    bg = rgb(str(c.fill.fgColor.rgb)) or bg
                if fg is None:
                    continue
                n += 1
                size = float(c.font.sz or 11)
                need = 3.0 if size >= 18 or (size >= 14 and c.font.b) else 4.5
                if ratio(fg, bg) < need:
                    bad.append('%s!%s %.1f:1' % (ws.title, c.coordinate, ratio(fg, bg)))
    return bad, n


def xlsx_formula(path):
    wf, wv = xlsx_books(path)
    bad, n = [], 0
    for ws in wf.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value.startswith('='):
                    n += 1
                    v = wv[ws.title][c.coordinate].value
                    if v is None:
                        bad.append('%s!%s has no saved result' % (ws.title, c.coordinate))
                    elif isinstance(v, str) and v in ERRORS:
                        bad.append('%s!%s is %s' % (ws.title, c.coordinate, v))
    return bad, n


def head(bad, limit=3):
    return '; '.join(bad[:limit]) + (' (+%d more)' % (len(bad) - limit) if len(bad) > limit else '')


def check(rule_id, path, case, stage):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    f = fmt_of(path)
    if rule_id == 'FLOOR-FONT':
        fams = {'docx': docx_fonts, 'pptx': pptx_fonts, 'xlsx': xlsx_fonts}[f](path)
        ok = len(fams) <= 2
        return ok, '%d font families: %s' % (len(fams), ', '.join(sorted(str(k) for k in fams)))
    if rule_id == 'FLOOR-OVERFLOW':
        if f == 'docx':
            return True, 'text flows across pages in a document'
        bad, n = (pptx_overflow if f == 'pptx' else xlsx_overflow)(path)
        return not bad, head(bad) if bad else '%d text boxes or cells fit' % n
    if rule_id == 'FLOOR-OVERLAP':
        if f != 'pptx':
            return True, 'not a deck'
        bad, n = pptx_overlap(path)
        return not bad, head(bad) if bad else '%d text shapes are clear of pictures and filled shapes' % n
    if rule_id == 'FLOOR-CONTRAST':
        bad, n = {'docx': docx_contrast, 'pptx': pptx_contrast, 'xlsx': xlsx_contrast}[f](path)
        return not bad, head(bad) if bad else '%d coloured text items have enough contrast' % n
    if rule_id == 'FLOOR-FORMULA':
        if f != 'xlsx':
            return True, 'not a spreadsheet'
        bad, n = xlsx_formula(path)
        return not bad, head(bad) if bad else '%d formulas have saved results and no errors' % n
    if rule_id == 'FLOOR-META':
        bad = []
        if f == 'pptx':
            bad = pptx_meta(path)
        elif f == 'docx':
            import docx
            d = docx.Document(path)
            if not (d.core_properties.title or '').strip():
                bad.append('the document has no title in its properties')
            z = zipfile.ZipFile(path)
            if b'w:lang' not in z.read('word/styles.xml') and b'w:lang' not in z.read('word/document.xml'):
                bad.append('no language is declared')
            for dp in d.element.iter('{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}docPr'):
                if not (dp.get('descr') or '').strip():
                    bad.append('a picture has no alternative text')
        else:
            wf, _ = xlsx_books(path)
            if not (wf.properties.title or '').strip():
                bad.append('the workbook has no title in its properties')
            for name in wf.sheetnames:
                if re.fullmatch(r'Sheet\d*', name):
                    bad.append('sheet "%s" has a default name' % name)
        return not bad, head(bad) if bad else 'title, names and alternative text are in place'
    return False, 'unknown rule %s' % rule_id
