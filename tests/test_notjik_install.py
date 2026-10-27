"""Exercise the client migration with synthetic files and mocked services."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class NotjikInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / 'home'
        self.old = self.home / '.config/dunst'
        self.old.mkdir(parents=True)
        (self.old / 'dunstrc').write_text('personal settings\n')
        self.tools = self.root / 'tools'
        (self.tools / '.git').mkdir(parents=True)
        build = self.tools / 'apps/notjik/scripts/build.sh'
        build.parent.mkdir(parents=True)
        build.write_text('echo build >> "$CALL_LOG"\n')
        install = self.tools / 'scripts/install.sh'
        install.parent.mkdir(parents=True)
        install.write_text('echo "install $*" >> "$CALL_LOG"\nexit "${INSTALL_RESULT:-0}"\n')
        commands = self.root / 'bin'
        commands.mkdir()
        for name, body in {
            'quickshell': 'exit 0\n',
            'systemctl': 'echo "$*" >> "$CALL_LOG"\n'
                         'case "$*" in *is-active*) exit "${SESSION_RESULT:-0}";; esac\n',
        }.items():
            path = commands / name
            path.write_text('#!/bin/sh\n' + body)
            path.chmod(0o755)
        # Redirect the disposable script copy without changing the real HOME.
        self.script = self.root / 'install.sh'
        self.script.write_text((ROOT / 'scripts/install-notjik.sh').read_text()
                               .replace('$HOME', '${NOTJIK_TEST_HOME}'))
        (self.root / 'ensure-tjikos.sh').write_text(
            (ROOT / 'scripts/ensure-tjikos.sh').read_text()
            .replace('$HOME', '${NOTJIK_TEST_HOME}'))
        shutil.copy2(ROOT / 'scripts/cache-install.py', self.root / 'cache-install.py')
        self.log = self.root / 'calls'
        self.env = {**os.environ, 'NOTJIK_TEST_HOME': str(self.home),
                    'TJIKOS_REPO': str(self.tools), 'CALL_LOG': str(self.log),
                    'XDG_STATE_HOME': str(self.root / 'state'),
                    'PATH': str(commands) + os.pathsep + os.environ['PATH']}

    def run_install(self, **extra):
        return subprocess.run(['bash', str(self.script)],
                              env={**self.env, **extra}, capture_output=True, text=True)

    def test_install_then_retire_old_server_without_restarting_notjik(self):
        result = self.run_install()
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.log.read_text().splitlines()
        self.assertLess(calls.index('install notjik'), calls.index('--user mask --now dunst.service'))
        self.assertIn('--user enable notjik.service', calls)
        self.assertIn('--user start notjik.service', calls)
        self.assertFalse(any('restart' in call for call in calls))
        archives = list((self.root / 'state/notjik/migration').glob('*/config/dunstrc'))
        self.assertEqual(len(archives), 1)
        self.assertEqual(archives[0].read_text(), 'personal settings\n')
        self.assertFalse(self.old.exists())
        self.assertEqual(self.run_install().returncode, 0)
        self.assertEqual(list((self.root / 'state/notjik/migration').glob('*/config/dunstrc')), archives)

    def test_install_failure_preserves_old_config_and_service(self):
        result = self.run_install(INSTALL_RESULT='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((self.old / 'dunstrc').is_file())
        self.assertNotIn('--user', self.log.read_text())

    def test_headless_install_enables_without_starting(self):
        result = self.run_install(SESSION_RESULT='3')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--user enable notjik.service', self.log.read_text())
        self.assertNotIn('--user start notjik.service', self.log.read_text())

    @unittest.skipUnless(shutil.which('chezmoi') and shutil.which('fish'), 'Chezmoi and Fish required')
    def test_client_only_hook_and_server_exclusions(self):
        for host in ('fi', 'li', 'si'):
            with self.subTest(host=host):
                config = self.root / 'chezmoi.json'
                config.write_text(json.dumps({'data': {
                    'isClient': host != 'si', 'isServer': host == 'si',
                }}))
                def render(path):
                    return subprocess.check_output([
                        'chezmoi', '--config', str(config), '--source', str(self.root),
                        '--persistent-state', str(self.root / 'state.db'),
                        'execute-template', '-f', str(ROOT / path),
                    ], text=True)
                hook = render('home/.chezmoiscripts/run_after_37-install-notjik.fish.tmpl')
                subprocess.run(['fish', '--no-config', '-n'], input=hook, text=True, check=True)
                self.assertEqual('install-notjik.sh' in hook, host != 'si')
                ignored = render('home/.chezmoiignore').splitlines()
                self.assertEqual('.config/systemd/user/notjik.service.d' in ignored, host == 'si')


if __name__ == '__main__':
    unittest.main()
