import native_render
"""Exercise the client migration with synthetic files and mocked services."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class BartjikInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / 'home'
        self.old = self.home / '.config/waybar'
        self.old.mkdir(parents=True)
        (self.old / 'config').write_text('personal settings\n')
        self.tools = self.root / 'tools'
        (self.tools / '.git').mkdir(parents=True)
        build = self.tools / 'apps/bartjik/scripts/build.sh'
        build.parent.mkdir(parents=True)
        build.write_text('echo build >> "$CALL_LOG"\n')
        install = self.tools / 'scripts/install.sh'
        install.parent.mkdir(parents=True)
        install.write_text('echo "install $*" >> "$CALL_LOG"\nexit "${INSTALL_RESULT:-0}"\n')
        commands = self.root / 'bin'
        commands.mkdir()
        for name, body in {
            'quickshell': 'exit 0\n',
            'pkill': 'exit 1\n',
            'install': 'exit 0\n',
            'systemctl': 'echo "$*" >> "$CALL_LOG"\n'
                         'case "$*" in *is-active*graphical-session*) exit "${SESSION_RESULT:-0}";; *is-active*bartjik*) exit "${BARTJIK_RESULT:-0}";; esac\n',
        }.items():
            path = commands / name
            path.write_text('#!/bin/sh\n' + body)
            path.chmod(0o755)
        # Redirect the disposable script copy without changing the real HOME.
        self.script = self.root / 'install.sh'
        self.script.write_text((ROOT / 'scripts/install-bartjik.sh').read_text()
                               .replace('$HOME', '${BARTJIK_TEST_HOME}'))
        (self.root / 'ensure-tjikos.sh').write_text(
            (ROOT / 'scripts/ensure-tjikos.sh').read_text()
            .replace('$HOME', '${BARTJIK_TEST_HOME}'))
        (self.root / 'activate-bartjik.sh').write_text((ROOT / 'scripts/activate-bartjik.sh').read_text().replace('$HOME', '${BARTJIK_TEST_HOME}'))
        engine=self.tools/'apps/tjikup/src/workflow_services.rs'
        engine.parent.mkdir(parents=True,exist_ok=True)
        engine.write_text('synthetic fingerprint')
        self.log = self.root / 'calls'
        self.env = {**os.environ, 'BARTJIK_TEST_HOME': str(self.home),
                    'TJIKOS_REPO': str(self.tools), 'CALL_LOG': str(self.log),
                    'XDG_STATE_HOME': str(self.root / 'state'),
                    'PATH': str(commands) + os.pathsep + os.environ['PATH']}

    def run_install(self, **extra):
        return subprocess.run(['bash', str(self.script)],
                              env={**self.env, **extra}, capture_output=True, text=True)

    def test_install_then_retire_old_server_without_restarting_bartjik(self):
        result = self.run_install()
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.log.read_text().splitlines()
        self.assertLess(calls.index('install bartjik'), calls.index('--user mask --now waybar.service'))
        self.assertIn('--user enable bartjik.service', calls)
        self.assertIn('--user start bartjik.service', calls)
        self.assertFalse(any('restart' in call for call in calls))
        archives = list((self.root / 'state/bartjik/migration').glob('*/waybar/config'))
        self.assertEqual(len(archives), 1)
        self.assertEqual(archives[0].read_text(), 'personal settings\n')
        self.assertFalse(self.old.exists())
        self.assertEqual(self.run_install().returncode, 0)
        self.assertEqual(list((self.root / 'state/bartjik/migration').glob('*/waybar/config')), archives)

    def test_managed_install_defers_activation_and_preserves_old_configuration(self):
        result = self.run_install(TJIKUP_MANAGED_CONFIG='1')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.old.is_dir())
        self.assertNotIn('--user', self.log.read_text())

    def test_install_failure_preserves_old_config_and_service(self):
        result = self.run_install(INSTALL_RESULT='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((self.old / 'config').is_file())
        self.assertNotIn('--user', self.log.read_text())

    def test_headless_install_enables_without_starting(self):
        result = self.run_install(SESSION_RESULT='3')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--user enable bartjik.service', self.log.read_text())
        self.assertNotIn('--user start bartjik.service', self.log.read_text())

    def test_startup_failure_preserves_waybar(self):
        result = self.run_install(BARTJIK_RESULT='3')
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((self.old / 'config').is_file())
        self.assertNotIn('--user mask --now waybar.service', self.log.read_text())

    def test_fleet_plan_orders_bar_after_notifications(self):
        plan = json.loads((ROOT / 'tjikup/recipes.json').read_text())["recipes"]
        bar = next(item for item in plan if item['id'] == 'home:bartjik')
        self.assertEqual(bar['apply'][-1].split('/')[-1].removeprefix('home-') + '.j2', 'run_after_39-install-bartjik.fish.j2')
        self.assertNotIn('home:notjik', bar['needs'])
        activation = next(item for item in plan if item['id'] == 'home:activate:bartjik')
        self.assertIn('home:config:bartjik', activation['needs'])
        self.assertIn('user-systemd', bar['resources'])

    @unittest.skipUnless(shutil.which('render-native'), 'Native renderer required')
    def test_retired_panels_have_no_native_file_sources(self):
        entries=json.loads((ROOT/'native/home/files.json').read_text())
        if isinstance(entries,dict): entries=entries['entries']
        for entry in entries:
            if any(name in entry['path'] for name in ['/.config/waybar','/.config/quickshell/audio','/.config/quickshell/network']):
                self.assertEqual(entry['kind'],'absent')

    def test_native_manifest_has_client_only_configuration(self):
        entries=json.loads((ROOT/'native/home/files.json').read_text())
        if isinstance(entries,dict): entries=entries['entries']
        selected=[e for e in entries if e.get('group') == 'bartjik']
        self.assertTrue(selected)
        self.assertTrue(all(e.get('when') in ['is_client', 'hostname in ["fi", "li"]'] for e in selected))
