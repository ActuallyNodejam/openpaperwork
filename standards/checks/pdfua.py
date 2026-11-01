"""Accessible-PDF check: export a tagged PDF with LibreOffice and validate it against PDF/UA-1 with veraPDF.

check(rule_id, path, case, stage) -> (passed, evidence). passed is None when the tool is not
available, and the rule is then skipped.

veraPDF is a separate, optional tool (dual GPLv3+ / MPLv2+). Nothing from it is in this repository.
It runs from its published container image with no network and a read-only mount. Set
FILETASK_VERAPDF to another image, or to an empty string to switch the check off.

Scope, measured on hand-built files on 2026-10-03 with LibreOffice 24.2 and veraPDF 1.30.2:
- docx: every PDF/UA-1 rule counts; a titled document passes.
- pptx: clause 7.1 test 3 (content neither tagged nor an artifact) is ignored, because the Impress
  exporter leaves slide content untagged even in a clean deck. Clause 7.3 test 1 (figure without
  alternative text) is ignored only when every picture and chart in the deck carries alternative
  text, because the exporter drops it for native charts; floor.py checks the source instead.
- xlsx: skipped. The Calc exporter writes no structure tree, so no workbook can pass.
"""
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

FILTER = {'docx': 'writer_pdf_Export', 'pptx': 'impress_pdf_Export'}
OPTS = '{"PDFUACompliance":{"type":"boolean","value":"true"},"UseTaggedPDF":{"type":"boolean","value":"true"}}'
IGNORE = {'pptx': {('7.1', 3)}}


def source_alt_complete(path):
    """True when every picture and chart in a deck has alternative text in the file itself."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import floor
    from pptx import Presentation
    return not any(floor.pptx_alt_missing(s._element) for s in Presentation(path).slides)


def check(rule_id, path, case, stage):
    if rule_id != 'FLOOR-PDFUA':
        return False, 'unknown rule %s' % rule_id
    fmt = Path(path).suffix.lower().lstrip('.')
    image = os.environ.get('FILETASK_VERAPDF', 'verapdf/cli:latest')
    if fmt not in FILTER:
        return None, 'skipped: no tagged PDF export for %s' % fmt
    if not image or not shutil.which('docker') or not shutil.which('soffice'):
        return None, 'skipped: veraPDF or LibreOffice is not available'
    work = Path(tempfile.mkdtemp(prefix='ua-'))
    try:
        src = work / ('in.' + fmt)
        shutil.copyfile(path, src)
        subprocess.run(['soffice', '-env:UserInstallation=file://%s/lo' % work, '--headless', '--norestore', '--convert-to',
                        'pdf:%s:%s' % (FILTER[fmt], OPTS), '--outdir', str(work), str(src)], capture_output=True, timeout=180)
        pdf = work / 'in.pdf'
        if not pdf.is_file():
            return False, 'LibreOffice could not export a tagged PDF'
        os.chmod(work, 0o755)
        os.chmod(pdf, 0o644)
        p = subprocess.run(['docker', 'run', '--rm', '--network', 'none', '-v', '%s:/data:ro' % work, image,
                            '-f', 'ua1', '--format', 'json', '/data/in.pdf'], capture_output=True, text=True, timeout=300)
        try:
            v = json.loads(p.stdout)['report']['jobs'][0]['validationResult']
        except (ValueError, KeyError, IndexError):
            return None, 'skipped: veraPDF gave no report (%s)' % (p.stderr or p.stdout)[-120:].strip()
        v = v[0] if isinstance(v, list) else v
        ignore = set(IGNORE.get(fmt, set()))
        if fmt == 'pptx' and source_alt_complete(path):
            ignore.add(('7.3', 1))
        failed = [r for r in v['details'].get('ruleSummaries', []) if (r['clause'], r['testNumber']) not in ignore]
        if failed:
            return False, '; '.join('PDF/UA-1 %s test %s x%s: %s' % (r['clause'], r['testNumber'], r.get('failedChecks'), r['description'][:90])
                                    for r in failed[:3])
        return True, 'PDF/UA-1: %d rules passed%s' % (v['details']['passedRules'], ', exporter finding 7.1-3 ignored' if fmt in IGNORE else '')
    finally:
        shutil.rmtree(work, ignore_errors=True)
