"""Exercise the official Chrome bootstrap without package manager changes."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ChromeBootstrapTests(unittest.TestCase):
    def render(self, root, client):
        config = root / 'chezmoi.json'
        config.write_text(json.dumps({'data': {'isClient': client, 'isServer': not client}}))
        return subprocess.check_output([
            'chezmoi', '--config', str(config), '--source', str(ROOT / 'etc'),
            '--persistent-state', str(root / 'state.db'), 'execute-template', '-f',
            str(ROOT / 'etc/.chezmoitemplates/tjikup/run_21-install-chrome.fish.tmpl'),
        ], text=True)

    @unittest.skipUnless(shutil.which('chezmoi') and shutil.which('fish'), 'Chezmoi/Fish required')
    def test_client_bootstrap_and_error_propagation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rendered = self.render(root, True)
            subprocess.run(['fish', '--no-config', '-n'], input=rendered, text=True, check=True)
            # Use the actual policy body with mocked logging and external calls.
            body = rendered[rendered.index("# Bootstrap Chrome"):]
            harness = '''
function rpm; return $MOCK_INSTALLED; end
function uname; echo $MOCK_ARCH; end
function step_skip_ok; echo ALREADY_INSTALLED; end
function step_fail; echo FAILED; end
function step_run_quiet
    printf '%s\\n' (string join ' ' -- $argv)
    return $MOCK_INSTALL_RESULT
end
'''
            for installed, arch, result, expected in [('0','x86_64','0',0),('1','x86_64','0',0),('1','x86_64','7',7),('1','aarch64','0',1)]:
                env={**os.environ,'MOCK_INSTALLED':installed,'MOCK_ARCH':arch,'MOCK_INSTALL_RESULT':result}
                completed=subprocess.run(['fish','--no-config','-c',harness+body],env=env,text=True,capture_output=True)
                self.assertEqual(completed.returncode,expected,completed.stderr)
                self.assertEqual('dl.google.com/linux/direct/' in completed.stdout,installed=='1' and arch=='x86_64')
                if expected == 0:
                    self.assertIn('google-chrome.enabled=1', completed.stdout)

    @unittest.skipUnless(shutil.which('chezmoi') and shutil.which('fish'), 'Chezmoi/Fish required')
    def test_server_has_no_install_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            rendered=self.render(Path(tmp),False)
            self.assertNotIn('dnf install',rendered)
            subprocess.run(['fish','--no-config','-n'],input=rendered,text=True,check=True)

    def test_bootstrap_precedes_rpm_phase_if_scheduler_is_present(self):
        path=ROOT/'scripts/tjikup-plan.json'
        if not path.exists():self.skipTest('This checkout runs scripts in Chezmoi filename order')
        plan={item['id']:item for item in json.loads(path.read_text())}
        self.assertIn('chrome',plan['rpm']['needs'])
        self.assertEqual(plan['chrome']['needs'],['repos'])
