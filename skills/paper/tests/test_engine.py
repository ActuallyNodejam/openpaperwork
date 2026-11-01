"""Offline tests for engine.py: the one-time tectonic fetch, its checksum and the cache. No network."""
import hashlib
import io
import os
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import engine


def archive(body=b'#!/bin/sh\necho tectonic\n'):
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode='w:gz') as tar:
        info = tarfile.TarInfo('tectonic')
        info.size = len(body)
        tar.addfile(info, io.BytesIO(body))
    return data.getvalue()


class Fetch(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.root = Path(self.dir.name)
        self.env = mock.patch.dict(os.environ, {'NODEJAM_TEX_CACHE': str(self.root / 'cache'), 'PATH': ''})
        self.env.start()
        self.tarball = self.root / 'tectonic.tar.gz'
        self.tarball.write_bytes(archive())
        self.url = self.tarball.as_uri()
        self.sha = hashlib.sha256(self.tarball.read_bytes()).hexdigest()
        self.said = []

    def tearDown(self):
        self.env.stop()
        self.dir.cleanup()

    def test_fetch_keeps_a_checked_engine_in_the_cache(self):
        path, reason = engine.fetch(self.url, self.sha, say=self.said.append)
        self.assertIsNone(reason)
        self.assertTrue(os.access(path, os.X_OK))
        self.assertEqual(engine.find(), ('tectonic', path))
        self.assertIn('one time', self.said[0])

    def test_a_wrong_checksum_leaves_nothing_behind(self):
        path, reason = engine.fetch(self.url, '0' * 64, say=self.said.append)
        self.assertIsNone(path)
        self.assertIn('checksum mismatch', reason)
        self.assertEqual(engine.find(), (None, None))

    def test_offline_is_a_reason_not_a_crash(self):
        path, reason = engine.fetch((self.root / 'missing.tar.gz').as_uri(), self.sha, say=self.said.append)
        self.assertIsNone(path)
        self.assertIn('download failed', reason)

    def test_an_engine_on_path_wins_and_nothing_is_fetched(self):
        bin_dir = self.root / 'bin'
        bin_dir.mkdir()
        exe = bin_dir / 'pdflatex'
        exe.write_text('#!/bin/sh\n')
        exe.chmod(0o755)
        with mock.patch.dict(os.environ, {'PATH': str(bin_dir)}), mock.patch.object(engine, 'fetch') as fetch:
            self.assertEqual(engine.engine(), ('pdflatex', str(exe)))
            fetch.assert_not_called()

    def test_every_pinned_release_has_a_checksum(self):
        for triple, sha in engine.RELEASES.values():
            self.assertRegex(sha, r'^[0-9a-f]{64}$', triple)


if __name__ == '__main__':
    unittest.main()
