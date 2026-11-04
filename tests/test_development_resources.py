"""Resource wrappers use fake services and synthetic runtime directories."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
FILES = ROOT / 'native/home/files'
BIN = FILES / '.local/bin'


class DevelopmentResourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.fake = self.root / 'bin'
        self.fake.mkdir()
        self.env = {**os.environ, 'XDG_RUNTIME_DIR': str(self.root),
                    'PATH': f'{self.fake}:{BIN}:' + os.environ['PATH']}
        self.env.pop('DOTJIK_DEV_CHECK', None)
        self.script('systemd-run', 'while [[ $1 != -- ]]; do shift; done\nshift\nexec "$@"')
        self.script('npx', 'read -r line\nprintf "%s\\n" "$line"')

    def script(self, name, body):
        p = self.fake / name
        p.write_text('#!/usr/bin/env bash\nset -eu\n' + body + '\n')
        p.chmod(0o755)

    def run_check(self, *args):
        return subprocess.run([str(BIN / 'dev-check'), *args], env=self.env,
                              capture_output=True, text=True, timeout=5)

    def test_nested_exit_and_arguments(self):
        result = self.run_check('dev-check', 'printf', '%s', 'argument with spaces')
        self.assertEqual(result.stdout, 'argument with spaces')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.run_check('bash', '-c', 'exit 23').returncode, 23)
        self.assertEqual(self.run_check('true').returncode, 0)

    def test_serialization(self):
        ready = self.root / 'ready'
        release = self.root / 'release'
        p = subprocess.Popen([str(BIN / 'dev-check'), 'bash', '-c',
                              'touch "$1"; while [[ ! -f $2 ]]; do sleep .02; done',
                              '--', str(ready), str(release)], env=self.env)
        self.addCleanup(lambda: p.poll() is None and p.kill())
        deadline = time.monotonic() + 3
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(.02)
        self.assertTrue(ready.exists())
        q = subprocess.Popen([str(BIN / 'dev-check'), 'touch', str(self.root / 'second')], env=self.env)
        self.addCleanup(lambda: q.poll() is None and q.kill())
        time.sleep(.1)
        self.assertFalse((self.root / 'second').exists())
        release.touch()
        self.assertEqual(p.wait(timeout=3), 0)
        self.assertEqual(q.wait(timeout=3), 0)
        self.assertTrue((self.root / 'second').exists())


    def test_missing_bus_fails_closed(self):
        self.script('systemd-run', 'exit 1')
        marker = self.root / 'unbounded'
        self.assertEqual(self.run_check('touch', str(marker)).returncode, 1)
        self.assertFalse(marker.exists())
