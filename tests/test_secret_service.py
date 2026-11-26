import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / 'native/tasks/home/run_after_97-secret-service.fish.j2'


@unittest.skipUnless(shutil.which('fish'), 'Fish required')
class SecretServiceTests(unittest.TestCase):
    def run_hook(self, *, install=False, **options):
        with tempfile.TemporaryDirectory() as tmp:
            prelude = '''
function section_header; end
function status_msg; end
function stage_note
    $argv[5..-1]
end
function rpm
    switch "$argv[2]"
        case oo7-daemon; test "$MISSING" != 1; return $status
        case '*'; return 1
    end
end
function sudo
    echo $argv >> $CALLS
    return $DNF_STATUS
end
function systemctl
    echo $argv >> $CALLS
    switch "$argv[3]"
        case is-active is-enabled
            test "$argv[4]" = oo7-daemon.service; and test "$ACTIVE" = 1
            return $status
        case is-failed; test "$FAILED" = 1; return $status
    end
    return 0
end
'''
            hooks = [HOOK.with_name('install-secret-service.fish.j2'), HOOK] if install else [HOOK]
            script = prelude + '\n'.join(line for hook in hooks for line in hook.read_text().splitlines()
                                          if not line.startswith(('source ', '#!')))
            calls = Path(tmp) / 'calls'
            defaults = dict(MISSING=0, DNF_STATUS=0, ACTIVE=0, FAILED=0)
            defaults.update(options)
            result = subprocess.run(['fish', '--no-config', '-c', script],
                                    env={**os.environ, 'HOME': tmp, 'XDG_CONFIG_HOME': tmp,
                                         'CALLS': str(calls),
                                         **{k: str(v) for k, v in defaults.items()}},
                                    capture_output=True, text=True)
            return result, calls.read_text() if calls.exists() else ''

    def test_installs_before_starting(self):
        result, calls = self.run_hook(install=True, MISSING=1, FAILED=1)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('dnf install -y oo7-daemon pam_oo7 oo7-portal', calls)
        self.assertLess(calls.index('dnf install'), calls.index('enable --now'))
        self.assertIn('--user reset-failed oo7-daemon.service', calls)

    def test_running_oo7_does_not_restart(self):
        result, calls = self.run_hook(ACTIVE=1)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('dnf ', calls)
        self.assertNotIn('enable --now', calls)

    def test_starts_inactive_provider(self):
        result, calls = self.run_hook()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--user enable --now oo7-daemon.service', calls)

    def test_package_failure_stops_before_activation(self):
        result, calls = self.run_hook(install=True, MISSING=1, DNF_STATUS=8)
        self.assertEqual(result.returncode, 8, result.stderr)
        self.assertNotIn('dnf remove', calls)
        self.assertNotIn('enable --now', calls)

    def test_configuration_depends_on_successful_package_installation(self):
        recipes = {recipe['id']: recipe for recipe in
                   json.loads((ROOT / 'tjikup/recipes.json').read_text())['recipes']}
        self.assertIn('home:secrets', recipes['home:configure:secrets']['needs'])
