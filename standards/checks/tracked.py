"""Tracked-change checks for Word files, standard library only.

check(rule_id, path, case, stage) -> (passed, evidence)

TRACK-1  The file carries revision marks (w:ins and w:del), and accepting them gives the
         input text with exactly the case's replacements for this stage.
TRACK-2  Rejecting every revision mark restores the input text exactly.
"""
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def views(path):
    """Return (accepted paragraphs, original paragraphs, insert count, delete count)."""
    root = ET.fromstring(zipfile.ZipFile(path).read('word/document.xml'))
    accepted, original, ins, dels = [], [], 0, 0
    for p in root.iter(W + 'p'):
        a, o = [], []

        def walk(node, mode):
            nonlocal ins, dels
            for child in node:
                tag = child.tag
                if tag == W + 'ins':
                    ins += 1
                    walk(child, 'ins')
                elif tag == W + 'del':
                    dels += 1
                    walk(child, 'del')
                elif tag == W + 't':
                    if mode in ('both', 'ins'):
                        a.append(child.text or '')
                    if mode in ('both',):
                        o.append(child.text or '')
                elif tag == W + 'delText':
                    o.append(child.text or '')
                elif tag in (W + 'tab',):
                    if mode != 'del':
                        a.append('\t')
                    o.append('\t')
                elif tag == W + 'p':
                    continue
                else:
                    walk(child, mode)
        walk(p, 'both')
        accepted.append(''.join(a))
        original.append(''.join(o))
    clean = lambda ps: [re.sub(r'\s+', ' ', x).strip() for x in ps if x.strip()]
    return clean(accepted), clean(original), ins, dels


def check(rule_id, path, case, stage):
    truth = case['truth']
    folder = Path(__file__).resolve().parent.parent / next(
        c['path'] for c in __import__('json').loads((Path(__file__).resolve().parent.parent / 'catalogue.json').read_text())
        if c['id'] == case['id'])
    source, _, _, _ = views(folder / 'inputs' / truth['input'])
    accepted, original, ins, dels = views(path)
    if rule_id == 'TRACK-1':
        expected = list(source)
        for old, new in truth['replacements'][stage]:
            hits = [i for i, t in enumerate(expected) if old in t]
            if len(hits) != 1:
                return False, 'case truth: %r found %d times in the input' % (old, len(hits))
            expected[hits[0]] = expected[hits[0]].replace(old, new)
        if not ins or not dels:
            return False, 'no revision marks: %d insertions, %d deletions' % (ins, dels)
        if accepted != expected:
            diff = [(e, a) for e, a in zip(expected, accepted) if e != a] or [('paragraph count', '%d vs %d' % (len(expected), len(accepted)))]
            return False, 'accepted text differs: expected %r, got %r' % diff[0]
        return True, '%d insertions and %d deletions; accepted text matches the requested changes only' % (ins, dels)
    if rule_id == 'TRACK-2':
        if original != source:
            diff = [(s, o) for s, o in zip(source, original) if s != o] or [('paragraph count', '%d vs %d' % (len(source), len(original)))]
            return False, 'rejecting the marks does not restore the input: expected %r, got %r' % diff[0]
        return True, 'rejecting every mark restores the input text'
    return False, 'unknown rule %s' % rule_id
