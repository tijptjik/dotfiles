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
        (scripts / 'activate-runtjik.sh').write_text((ROOT / 'scripts/activate-runtjik.sh').read_text().replace('$HOME', '${RUNTJIK_TEST_HOME}'))
        (scripts / 'ensure-tjikos.sh').write_text('tool_repo="$TJIKOS_REPO"\nensure_tjikos() { :; }\n')
        (scripts / 'cleanup-launcher-entries.py').write_text(
            'import os,sys\nraise SystemExit(int(os.environ.get("CLEANUP_PENDING", "0")) if "--check" in sys.argv else 0)\n')
        (scripts / 'cache-install.py').write_text(
            'import subprocess,sys\nraise SystemExit(subprocess.call(sys.argv[sys.argv.index("--")+1:]))\n')
        tools = root / 'tools/apps/runtjik/scripts'
        tools.mkdir(parents=True)
        (tools / 'build.sh').write_text('#!/bin/sh\necho build >> "$CALL_LOG"\nexit "${BUILD_RESULT:-0}"\n')
        (tools / 'install.sh').write_text('#!/bin/sh\necho install >> "$CALL_LOG"\n')
        bindir = self.home / '.local/bin'
        bindir.mkdir(parents=True)
        for name, body in {
            'runtjik': 'echo check >> "$CALL_LOG"\nexit "${HEALTH_RESULT:-0}"\n',
            'quickshell': 'exit 0\n',
            'systemctl': 'echo "$*" >> "$CALL_LOG"\n'
                         'case "$*" in *is-active*graphical-session*) exit "${SESSION_RESULT:-0}";; '
                         '*is-active*hamr-gtk*) exit "${LEGACY_ACTIVE:-0}";; *is-active*) exit 3;; '
                         '*show*KillMode*) echo "${KILL_MODE:-process}";; *is-enabled*) exit "${LEGACY_ENABLED:-1}";; esac\n',
        }.items():
            path = bindir / name
            path.write_text('#!/bin/sh\n' + body)
            path.chmod(0o755)
        self.env = {**os.environ, 'RUNTJIK_TEST_HOME': str(self.home), 'XDG_STATE_HOME': str(root / 'state'),
                    'TJIKOS_REPO': str(root / 'tools'), 'CALL_LOG': str(self.log),
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

    def run_check(self, **env):
        return subprocess.run(['bash', str(self.script.with_name('activate-runtjik.sh')), '--check'],
                              env={**self.env, **env}, capture_output=True, text=True)

    def test_activation_check_skips_healthy_install_without_mutations(self):
        for _ in range(2):
            result = self.run_check(LEGACY_ACTIVE='3')
            self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.log.read_text()
        self.assertNotIn('--user stop', calls)
        self.assertNotIn('--user disable', calls)
        self.assertNotIn('install', calls)

    def test_activation_check_detects_pending_work_without_stopping_services(self):
        for env in ({}, {'LEGACY_ACTIVE': '3', 'LEGACY_ENABLED': '0'},
                    {'CLEANUP_PENDING': '1'}, {'HEALTH_RESULT': '1'}):
            result = self.run_check(**env)
            self.assertNotEqual(result.returncode, 0)
        calls = self.log.read_text()
        self.assertNotIn('--user stop', calls)
        self.assertNotIn('--user disable', calls)

    def test_recipe_checks_activation_before_apply(self):
        recipes = json.loads((ROOT / 'tjikup/recipes.json').read_text())['recipes']
        task = next(row for row in recipes if row['id'] == 'home:activate:runtjik')
        self.assertEqual(task['check'], task['apply'] + ['--check'])

    def test_hook_runs_on_all_hosts_and_is_in_graph(self):
        plan = json.loads((ROOT / 'tjikup/recipes.json').read_text())["recipes"]
        task = next(row for row in plan if row['id'] == 'home:runtjik')
        self.assertNotIn('home:tjikup', task['needs'])
        self.assertIn('tjikos', task['resources'])
        hook = (ROOT / 'home/.chezmoitemplates/tjikup' / (task['apply'][-1].split('/')[-1].removeprefix('home-') + '.tmpl')).read_text()
        self.assertNotIn('.isClient', hook)
        self.assertNotIn('FLEET_DEFER_HOOKS', hook)


if __name__ == '__main__':
    unittest.main()
