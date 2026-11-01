#!/usr/bin/env python3
"""Turn a paper source file into a PDF and report the result as JSON. Standard library only.

  build_paper.py PAPER.tex [--out DIR]

Looks for a TeX engine by name on PATH (tectonic, then latexmk, then pdflatex), then for
bin/tectonic beside this file, then fetches tectonic once into the cache (engine.py). Prints {ok, pdf, pages, engine, seconds} or {ok: false, error, line,
context, hint}. Exit 0 on success, 1 on a failed build, 3 when no engine is available.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def engine():
    sys.path.insert(0, str(HERE))
    from engine import engine as find_engine

    return find_engine()


def page_count(pdf):
    data = pdf.read_bytes()
    counts = [int(n) for n in re.findall(rb'/Type\s*/Pages\b[^>]*?/Count\s+(\d+)', data)] + \
             [int(n) for n in re.findall(rb'/Count\s+(\d+)[^>]*?/Type\s*/Pages\b', data)]
    if counts:
        return max(counts)
    n = len(re.findall(rb'/Type\s*/Page\b(?!s)', data))
    if n:
        return n
    tool = shutil.which('pdfinfo')
    if tool:
        m = re.search(r'Pages:\s+(\d+)', subprocess.run([tool, str(pdf)], capture_output=True, text=True).stdout)
        return int(m.group(1)) if m else None
    return None


def first_error(log):
    """The first line starting with '!' names the problem; the 'l.<n>' line after it is the source line."""
    lines = log.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r'^(?:error: )?(?:.*?:(\d+): )?(!? ?.*)$', line) if line.startswith('error:') else None
        if line.startswith('!') or m:
            msg = line.lstrip('! ').strip() if line.startswith('!') else m.group(2).strip()
            src = m.group(1) if m and m.group(1) else None
            for nxt in lines[i + 1:i + 12]:
                lm = re.match(r'^l\.(\d+)\s?(.*)', nxt)
                if lm:
                    src = src or lm.group(1)
                    return msg, int(src), lm.group(2).strip()
            return msg, int(src) if src else None, ''
    return (lines[-1] if lines else 'the build produced no output'), None, ''


HINTS = [
    (r'Undefined control sequence', 'A command is used that no loaded package defines. Load the package or remove the command.'),
    (r"File `(.+?)' not found", 'A file the paper refers to is missing. Check the name and that it sits beside the paper.'),
    (r'Missing \$ inserted', 'A maths symbol such as _ or ^ is used outside maths. Escape it (\\_) or put it between $...$.'),
    (r'Environment (.+?) undefined', 'An environment is used without the package that defines it.'),
    (r'Citation .* undefined|There were undefined (citations|references)', 'A citation key has no matching reference entry.'),
    (r'Misplaced alignment tab|Extra alignment tab', 'A table row has an unescaped & or more columns than declared.'),
    (r'Runaway argument|File ended while scanning', 'A brace { is never closed.'),
]


def main(argv):
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2
    src = Path(argv[0]).resolve()
    out = Path(argv[argv.index('--out') + 1]).resolve() if '--out' in argv else src.parent
    if not src.is_file():
        print(json.dumps(dict(ok=False, error='no such file: %s' % src)))
        return 2
    if src.suffix.lower() == '.json':
        # The paper's JSON: the builder beside this file writes the .tex with the starter's preamble first.
        tex = src.with_suffix('.tex')
        extra = ['--template', argv[argv.index('--template') + 1]] if '--template' in argv else []
        made = subprocess.run([sys.executable, str(Path(__file__).resolve().parent / 'scripts' / 'build_paper.py'),
                               str(src), str(tex)] + extra, capture_output=True, text=True)
        if made.returncode or not tex.is_file():
            print(json.dumps(dict(ok=False, error=(made.stderr or made.stdout).strip()[-400:])))
            return 1
        src = tex
    name, path = engine()
    if not name:
        print(json.dumps(dict(ok=False, error='no_engine', hint='No TeX engine is on this computer and it could not be fetched, '
                                                               'most likely because there is no internet connection. Say so plainly and offer '
                                                               'the paper as a Word file in the same layout instead.')))
        return 3
    out.mkdir(parents=True, exist_ok=True)
    cmd = {'tectonic': [path, '-X', 'compile', '--outdir', str(out), src.name],
           'latexmk': [path, '-pdf', '-interaction=nonstopmode', '-halt-on-error', '-outdir=' + str(out), src.name],
           'pdflatex': [path, '-interaction=nonstopmode', '-halt-on-error', '-output-directory', str(out), src.name]}[name]
    t0 = time.time()
    runs = 2 if name == 'pdflatex' else 1  # tectonic and latexmk rerun until references settle
    for _ in range(runs):
        p = subprocess.run(cmd, cwd=src.parent, capture_output=True, text=True, timeout=900)
        if p.returncode:
            break
    pdf = out / (src.stem + '.pdf')
    log = p.stdout + '\n' + p.stderr
    if p.returncode or not pdf.is_file():
        msg, line, context = first_error(log)
        hint = next((h for pat, h in HINTS if re.search(pat, log)), 'Read the message, fix that line in the source and build again.')
        print(json.dumps(dict(ok=False, engine=name, error=msg, line=line, context=context, hint=hint), ensure_ascii=False))
        return 1
    missing = sorted(set(re.findall(r'Missing character: There is no .*? \("([0-9A-Fa-f]+)\)', log)))
    if missing:
        chars = ", ".join("U+%04X %s" % (int(c, 16), chr(int(c, 16))) for c in missing)
        print(json.dumps(dict(ok=False, engine=name, error="the font has no glyph for " + chars + "; the PDF would drop it",
                              hint="Write it the TeX way (--- for an em dash, -- for an en dash, \\ldots, ``quotes'') "
                                   "or keep the starter's preamble, which maps these, then build again."), ensure_ascii=False))
        return 1
    warnings = sorted(set(re.findall(r'(Citation `[^\']+\' .*? undefined|Reference `[^\']+\' .*? undefined|Overfull \\hbox \([\d.]+pt too wide\))', log)))
    print(json.dumps(dict(ok=True, pdf=str(pdf), pages=page_count(pdf), engine=name, seconds=round(time.time() - t0, 1),
                          warnings=warnings[:20]), ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
