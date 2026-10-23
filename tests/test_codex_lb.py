"""Render host policies and exercise service transitions with mocked systemctl."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / 'home/.chezmoiscripts'


@unittest.skipUnless(shutil.which('chezmoi') and shutil.which('fish'), 'chezmoi and Fish required')
class CodexLbTests(unittest.TestCase):
    def render(self, name, host):
        data = dict(isDesktop=host == 'fi', isLaptop=host == 'li',
                    isClient=host != 'si', isServer=host == 'si')
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / 'config.json'
            config.write_text(json.dumps({'data': data}))
            return subprocess.check_output([
                'chezmoi', '--config', str(config), '--source', tmp,
                '--persistent-state', str(Path(tmp) / 'state.db'),
                'execute-template', '-f', str(HOOKS / name),
            ], text=True)

    def test_runtime_on_both_clients_only(self):
        for host in ('fi', 'li', 'si'):
            with self.subTest(host=host):
                script = self.render('run_after_33-codex-lb.fish.tmpl', host)
                subprocess.run(['fish', '--no-config', '-n'], input=script, text=True, check=True)
                self.assertEqual('uv pip install' in script, host != 'si')
                self.assertNotIn('uses desktop master', script)

    def test_service_transition_and_failure(self):
        for host, fail in (('fi', ''), ('li', ''), ('si', ''), ('li', 'disable')):
            with self.subTest(host=host, fail=fail), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                command = root / 'systemctl'
                command.write_text('#!/bin/sh\necho "$*" >> "$CALL_LOG"\n'
                                   'if [ -n "$FAIL_COMMAND" ] && [ "$2" = "$FAIL_COMMAND" ]; then exit 1; fi\n')
                command.chmod(0o755)
                script = self.render('run_after_99-systemd-reload.fish.tmpl', host)
                # Exercise the Codex transition without the unrelated user-unit setup.
                script = script.split('function user_units_need_reload')[0]
                script = '\n'.join(line for line in script.splitlines()
                                   if not line.startswith(('source ', 'section_header ')))
                result = subprocess.run(['fish', '--no-config'], input=script, text=True,
                                        env={**os.environ, 'PATH': tmp + ':' + os.environ['PATH'],
                                             'CALL_LOG': str(root / 'calls'), 'FAIL_COMMAND': fail})
                calls = (root / 'calls').read_text().splitlines() if (root / 'calls').exists() else []
                enable = '--user enable --now codex-lb.service'
                if host == 'si' or fail:
                    self.assertNotIn(enable, calls)
                else:
                    self.assertEqual(result.returncode, 0)
                    self.assertEqual(calls[-1], enable)
                    old = 'codex-lb-laptop.service' if host == 'fi' else 'codex-lb-client.socket'
                    self.assertIn('--user disable --now ' + old, calls)
                    if host == 'li':
                        self.assertIn('--user stop codex-lb-client.service', calls)
                if fail:
                    self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
