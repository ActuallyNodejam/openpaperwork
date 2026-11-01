#!/usr/bin/env python3
"""Find the TeX engine for the paper skill, or fetch tectonic once. Standard library only.

  engine.py            print {"name", "path"} of the engine a build would use, fetching it if needed
  engine.py --no-fetch print it without fetching ({"name": null} when there is none)

Order: tectonic, latexmk or pdflatex on PATH (the app puts a bundled tectonic there), bin/tectonic
beside the skill, a tectonic fetched earlier into the person's cache, then a fetch: the pinned
tectonic release from GitHub, checked against its SHA-256, kept in the cache. Tectonic itself
fetches the TeX packages a paper needs on first use, into its own cache.
"""
import hashlib
import io
import json
import os
import platform
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
VERSION = '0.17.0'
# Each release's SHA-256, checked before the engine is unpacked.
RELEASES = {
    ('Darwin', 'arm64'): ('aarch64-apple-darwin', 'a3f1cac7c5678f01661a92212f58480ae3b0634115d880dbc59e2953ded45667'),
    ('Darwin', 'x86_64'): ('x86_64-apple-darwin', '7c90ef5b6ddb1eb1937e4337add5237b79338e4b9676459fa91187d24d6cdf80'),
    ('Linux', 'x86_64'): ('x86_64-unknown-linux-musl', '8533d07f9ccbd7a65824b9e0459041bca34af1eb33daba48f59215593753a3b7'),
}
URL = 'https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%40{v}/tectonic-{v}-{t}.tar.gz'


def cache_dir():
    if os.environ.get('NODEJAM_TEX_CACHE'):
        return Path(os.environ['NODEJAM_TEX_CACHE'])
    if sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Caches'
    else:
        base = Path(os.environ.get('XDG_CACHE_HOME') or Path.home() / '.cache')
    return base / 'Tectonic' / ('engine-' + VERSION)


def cached():
    exe = cache_dir() / 'tectonic'
    return exe if exe.is_file() and os.access(exe, os.X_OK) else None


def find():
    for name in ('tectonic', 'latexmk', 'pdflatex'):
        found = shutil.which(name)
        if found:
            return name, found
    local = HERE / 'bin' / ('tectonic.exe' if os.name == 'nt' else 'tectonic')
    if local.is_file() and os.access(local, os.X_OK):
        return 'tectonic', str(local)
    exe = cached()
    return ('tectonic', str(exe)) if exe else (None, None)


def fetch(url=None, sha=None, say=None):
    """Fetch the pinned tectonic into the cache. Returns its path, or None and the reason."""
    release = RELEASES.get((platform.system(), platform.machine()))
    if url is None:
        if not release:
            return None, 'no tectonic build for %s %s' % (platform.system(), platform.machine())
        url, sha = URL.format(v=VERSION, t=release[0]), release[1]
    (say or (lambda text: print(text, file=sys.stderr)))(
        'Getting the PDF engine for papers, one time (about 22 MB)...')
    try:
        with urllib.request.urlopen(url, timeout=120) as response:
            data = response.read()
    except Exception as error:  # offline, proxy, GitHub down: the caller offers the Word file
        return None, 'download failed: %s' % error
    got = hashlib.sha256(data).hexdigest()
    if got != sha:
        return None, 'checksum mismatch: got %s' % got
    target = cache_dir()
    target.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        member = next((m for m in archive.getmembers() if m.isfile() and Path(m.name).name == 'tectonic'), None)
        if member is None:
            return None, 'no tectonic in the archive'
        body = archive.extractfile(member).read()
    # Written beside, then moved, so a half-written engine is never found.
    with tempfile.NamedTemporaryFile(dir=target, delete=False) as part:
        part.write(body)
    os.chmod(part.name, 0o755)
    os.replace(part.name, target / 'tectonic')
    return str(target / 'tectonic'), None


def engine(allow_fetch=True):
    """(name, path) of the engine to use, fetching tectonic once when nothing is installed."""
    name, path = find()
    if name or not allow_fetch:
        return name, path
    path, _ = fetch()
    return ('tectonic', path) if path else (None, None)


if __name__ == '__main__':
    name, path = engine(allow_fetch='--no-fetch' not in sys.argv[1:])
    print(json.dumps(dict(name=name, path=path)))
