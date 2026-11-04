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

    def test_mcp_slots_protocol_and_release(self):
        processes = []
        try:
            for _ in range(4):
                processes.append(subprocess.Popen([str(BIN / 'chrome-devtools-bounded')],
                    env=self.env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, text=True))
                time.sleep(.08)
            fifth = subprocess.run([str(BIN / 'chrome-devtools-bounded')], env=self.env,
                                   capture_output=True, text=True, timeout=3)
            self.assertEqual(fifth.returncode, 75)
            self.assertEqual(fifth.stdout, '')
            for p in processes:
                out, err = p.communicate('protocol\n', timeout=3)
                self.assertEqual((p.returncode, out, err), (0, 'protocol\n', ''))
            result = subprocess.run([str(BIN / 'chrome-devtools-bounded')], env=self.env,
                input='again\n', capture_output=True, text=True, timeout=3)
            self.assertEqual((result.returncode, result.stdout), (0, 'again\n'))
        finally:
            for p in processes:
                if p.poll() is None:
                    p.kill()
                    p.communicate()

    def test_missing_bus_fails_closed(self):
        self.script('systemd-run', 'exit 1')
        marker = self.root / 'unbounded'
        self.assertEqual(self.run_check('touch', str(marker)).returncode, 1)
        self.assertFalse(marker.exists())

    def test_zed_arguments(self):
        self.script('uwsm', 'printf "%s\\n" "$@"')
        result = subprocess.run([str(BIN / 'zed-scoped'), 'preview', 'a b'],
                                env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn('app-development.slice\n', result.stdout)
        self.assertTrue(result.stdout.endswith('/.local/zed-preview.app/bin/zed\na b\n'))

    def test_native_render_all_hosts_and_subset_receipts(self):
        binary = os.environ.get('TJIKUP_BINARY', str(Path.home() / 'code/tjikos/apps/tjikup/target/debug/tjikup'))
        entries = json.loads((ROOT / 'native/home/files.json').read_text())
        names = {'dev-check', 'chrome-devtools-bounded', 'zed-scoped', 'zed', 'zed-preview',
                 'app-development.slice', 'dev.zed.Zed.desktop.j2', 'dev.zed.Zed-Preview.desktop.j2'}
        selected = [e for e in entries if Path(e.get('source', '')).name in names]
        for host in ('fi', 'li', 'si'):
            with self.subTest(host=host):
                policy = self.root / host
                policy.mkdir()
                for e in selected:
                    target = policy / e['source']
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(ROOT / 'native/home' / e['source'], target)
                context = json.loads((ROOT / f'native/home/files-{host}.json').read_text())['context']
                context['user'] = {'name': 'synthetic', 'home': '/home/synthetic'}
                manifest = {'version': 1, 'id': 'fixture-' + host,
                            'context': context, 'entries': selected}
                path = policy / 'manifest.json'
                path.write_text(json.dumps(manifest))
                dest = policy / 'destination'
                dest.mkdir()
                cmd = [binary, 'files', 'apply', '--manifest', str(path),
                       '--state-dir', str(policy / 'state'), '--root', str(dest)]
                result = subprocess.run(cmd, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                manifest['entries'] = selected[:1]
                path.write_text(json.dumps(manifest))
                self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
                manifest['entries'] = selected
                path.write_text(json.dumps(manifest))
                result = subprocess.run(cmd, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('SKIP: 0 changed,', result.stdout)
