"""Run server hooks with real logging helpers and stubbed system commands."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
HOOKS = [
    '35-si-nss-systemd', '36-si-power-policy', '37-si-media-permissions',
    '38-si-transmission-cleanup', '39-si-notifications',
]


class ServerHookLoggingTests(unittest.TestCase):
    def run_hook(self, name, failure=False, missing=False):
        script = (REPO / 'etc/.chezmoitemplates/tjikup' / f'run_{name}.fish.tmpl').read_text()
        script = re.sub(r'{{ include "([^"]+)" }}',
                        lambda m: (REPO / 'etc' / m[1]).read_text(), script)
        script = re.sub(r'{{ (?:if .*?|end) -}}', '', script)
        harness = '''
function rpm; echo 44; end
function systemd-cat; command cat >/dev/null; end
function sudo
    if string match -q '*--check*' -- "$argv"; or test "$argv[1]" = test
        return $TEST_MISSING
    end
    printf '%s\\n' "$argv" >> "$TEST_CALL_LOG"
    echo STUB_SYSTEM_COMMAND
    return $TEST_FAILURE
end
'''
        with tempfile.TemporaryDirectory() as directory:
            calls = Path(directory) / 'calls'
            result = subprocess.run(
                ['fish', '--no-config', '-c', harness + script],
                env={**os.environ, 'TJIKUP_NO_SPIN': '1', 'TJIKUP_COLOR': '0',
                     'TEST_FAILURE': '7' if failure else '0',
                     'TEST_MISSING': '1' if missing else '0',
                     'TEST_CALL_LOG': str(calls)},
                text=True, capture_output=True,
            )
            result.calls = calls.read_text().splitlines() if calls.exists() else []
            return result

    def test_configured_server_hooks_execute_with_real_helpers(self):
        for name in HOOKS:
            with self.subTest(hook=name):
                result = self.run_hook(name)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertTrue(result.calls, 'No system command was exercised')
                if name == '35-si-nss-systemd':
                    self.assertNotIn('STUB_SYSTEM_COMMAND', result.stdout)
                self.assertNotIn('Unknown command', result.stderr)

    def test_command_failure_stops_each_hook(self):
        for name in HOOKS:
            with self.subTest(hook=name):
                result = self.run_hook(name, failure=True)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn('FAILED', result.stdout)
                self.assertEqual(result.stdout.count('STUB_SYSTEM_COMMAND'), 1)

    def test_unprovisioned_services_report_skip(self):
        for name in HOOKS[2:]:
            with self.subTest(hook=name):
                result = self.run_hook(name, missing=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('SKIP', result.stdout)
                self.assertNotIn('STUB_SYSTEM_COMMAND', result.stdout)
