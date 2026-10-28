"""Dependencies, resource exclusion and safe skips using synthetic work only."""

import importlib.util

import json

import os

from pathlib import Path

import sys

import shutil

import subprocess

import tempfile

import threading

import unittest

from unittest.mock import patch

import tjikup_support



ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location('install_cache', ROOT / 'scripts/cache-install.py')

cache = importlib.util.module_from_spec(spec)

spec.loader.exec_module(cache)

class CacheTests(unittest.TestCase):
    def test_skip_and_repair_modified_missing_or_mode_changed_output(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'XDG_STATE_HOME': directory}):
            root = Path(directory)
            source, output, trace = [root / name for name in ('source', 'output', 'trace')]
            source.write_text('one')
            script = "from pathlib import Path; import sys; s,o,t=map(Path,sys.argv[1:]); o.write_bytes(s.read_bytes()); o.chmod(0o755); t.open('a').write('run\\n')"
            command = [sys.executable, '-c', script, str(source), str(output), str(trace)]
            def install():
                self.assertEqual(cache.cached_install('test', [source], [output], command), 0)
            install(); install()
            self.assertEqual(trace.read_text().count('run'), 1)
            output.unlink(); install()
            output.write_text('drift'); install()
            output.chmod(0o644); install()
            source.write_text('two'); install()
            self.assertEqual(trace.read_text().count('run'), 5)
            self.assertEqual(output.read_text(), 'two')

    def test_failed_install_never_marks_current(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'XDG_STATE_HOME': directory}):
            source = Path(directory) / 'source'; source.write_text('source')
            output = Path(directory) / 'output'; output.write_text('partial')
            self.assertEqual(cache.cached_install('test', [source], [output], [sys.executable, '-c', 'exit(2)']), 2)
            self.assertFalse((Path(directory) / 'tjikup/install/test.json').exists())

if __name__ == '__main__':
    unittest.main()
