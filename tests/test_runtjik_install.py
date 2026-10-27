"""Runtjik fleet installation uses fixtures, never live services or dotfiles."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RuntjikInstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        scripts = root / 'scripts'
        scripts.mkdir()
        self.home = root / 'home'
        self.home.mkdir()
        self.log = root / 'calls'
        self.script = scripts / 'install-runtjik.sh'
        self.script.write_text((ROOT / 'scripts/install-runtjik.sh').read_text()
                               .replace('$HOME', '${RUNTJIK_TEST_HOME}'))
        (scripts / 'ensure-tooltjik.sh').write_text('tool_repo="$TOOLTJIK_REPO"\nensure_tooltjik() { :; }\n')
        (scripts / 'cleanup-launcher-entries.py').write_text('')
        (scripts / 'cache-install.py').write_text(
            'import subprocess,sys\nraise SystemExit(subprocess.call(sys.argv[sys.argv.index("--")+1:]))\n')
        tools = root / 'tools/apps/runtjik/scripts'
        tools.mkdir(parents=True)
        (tools / 'build.sh').write_text('#!/bin/sh\necho build >> "$CALL_LOG"\nexit "${BUILD_RESULT:-0}"\n')
        (tools / 'install.sh').write_text('#!/bin/sh\necho install >> "$CALL_LOG"\n')
        bindir = self.home / '.local/bin'
        bindir.mkdir(parents=True)
        for name, body in {
            'runtjik': 'echo check >> "$CALL_LOG"\n',
            'quickshell': 'exit 0\n',
            'systemctl': 'echo "$*" >> "$CALL_LOG"\n'
                         'case "$*" in *is-active*graphical-session*) exit "${SESSION_RESULT:-0}";; '
                         '*is-active*hamr-gtk*) exit 0;; *is-active*) exit 3;; '
                         '*show*KillMode*) echo "${KILL_MODE:-process}";; *is-enabled*) exit 1;; esac\n',
        }.items():
            path = bindir / name
            path.write_text('#!/bin/sh\n' + body)
            path.chmod(0o755)
        self.env = {**os.environ, 'RUNTJIK_TEST_HOME': str(self.home),
                    'TOOLTJIK_REPO': str(root / 'tools'), 'CALL_LOG': str(self.log),
                    'PATH': str(bindir) + os.pathsep + os.environ['PATH']}

    def run_install(self, **env):
        return subprocess.run(['bash', str(self.script)], env={**self.env, **env},
                              capture_output=True, text=True)

    def test_installs_and_checks_before_retiring_launcher(self):
        result = self.run_install()
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.log.read_text().splitlines()
        self.assertLess(calls.index('check'), calls.index('--user stop hamr-gtk.service'))

    def test_preserves_launched_apps_when_old_kill_mode_is_unsafe(self):
        result = self.run_install(KILL_MODE='control-group')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('--user stop hamr-gtk.service', self.log.read_text())

    def test_failed_build_keeps_existing_launcher(self):
        result = self.run_install(BUILD_RESULT='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('--user stop', self.log.read_text())

    def test_headless_host_installs_without_starting_gui(self):
        result = self.run_install(SESSION_RESULT='3')
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.log.read_text()
        self.assertIn('install', calls)
        self.assertNotIn('--user stop', calls)
        self.assertNotIn('--user start', calls)

    def test_hook_runs_on_all_hosts_and_is_in_graph(self):
        plan = json.loads((ROOT / 'scripts/fleet_update/home-plan.json').read_text())
        task = next(row for row in plan if row['id'] == 'runtjik')
        self.assertIn('tjikup', task['needs'])
        self.assertIn('tooltjik', task['resources'])
        hook = (ROOT / 'home/.chezmoiscripts' / task['file']).read_text()
        self.assertNotIn('.isClient', hook)
        self.assertIn('FLEET_DEFER_HOOKS', hook)


if __name__ == '__main__':
    unittest.main()
