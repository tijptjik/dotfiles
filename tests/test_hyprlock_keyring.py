"""Login policy must retain authentication and install its module first."""
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HyprlockKeyringTests(unittest.TestCase):
    def test_client_pam_keeps_host_authentication_and_optional_keyring(self):
        for host in ('fi', 'li'):
            policy = (ROOT / f'system/native/{host}/files/pam.d/hyprlock').read_text()
            lines = [line.split() for line in policy.splitlines() if line and not line.startswith('#')]
            self.assertEqual(lines, [
                ['auth', 'substack', 'system-auth'],
                ['auth', 'optional', '/usr/local/lib/security/pam_oo7_tjik.so', 'unlock_on_auth'],
            ])
        server = (ROOT / 'system/native/si/files/pam.d/hyprlock').read_text()
        self.assertIn('auth    include     system-auth', server)
        self.assertNotIn('pam_oo7_tjik', server)

    def test_installer_is_required_before_system_files_and_has_read_only_check(self):
        recipes = {r['id']: r for r in json.loads((ROOT / 'system/tjikup/recipes.json').read_text())['recipes']}
        install = recipes['system:hyprlock-keyring']
        self.assertIn(install['id'], recipes['system:files']['needs'])
        self.assertFalse(install['optional'])
        self.assertEqual(install['operation'], 'install')
        self.assertFalse(install.get('roles'))
        self.assertEqual(install['check'][-1], '--check')

    def test_server_check_and_apply_do_not_access_the_client_installer(self):
        with tempfile.TemporaryDirectory() as directory:
            for args in ([], ['--check']):
                result = subprocess.run(
                    ['bash', str(ROOT / 'scripts/install-hyprlock-keyring.sh'), *args],
                    env={**os.environ, 'TJIKUP_ROLE': 'server', 'TJIKOS_REPO': directory},
                    capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('not used on servers', result.stdout)
                self.assertEqual(list(Path(directory).iterdir()), [])

    def test_complete_and_configuration_plans_accept_each_device_role(self):
        binary = os.environ.get('TJIKUP_BINARY', str(Path.home() / '.local/bin/tjikup'))
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            profile = directory / 'device.json'
            config = json.loads((ROOT / 'tjikup.json').read_text())
            config['device_file'] = str(profile)
            config['env']['DOTJIK_REPO'] = str(ROOT)
            config['env']['SYSTJIK_REPO'] = str(ROOT / 'system')
            config['includes'] = [str(ROOT / 'tjikup/recipes.json'), str(ROOT / 'system/tjikup/recipes.json')]
            config_path = directory / 'tjikup.json'
            config_path.write_text(json.dumps(config))
            for role in ('desktop', 'laptop', 'server'):
                profile.write_text(json.dumps({
                    'version': 1, 'hostname': socket.gethostname(), 'role': role, 'subscriptions': [],
                }))
                for flags in ([], ['--apply-dotfiles', '--apply-sysfiles']):
                    with self.subTest(role=role, flags=flags):
                        result = subprocess.run(
                            [binary, '--config', str(config_path), '--plan', *flags],
                            env={**os.environ, 'XDG_STATE_HOME': str(directory / 'state')},
                            capture_output=True, text=True,
                        )
                        self.assertEqual(result.returncode, 0, result.stderr)

    def test_check_does_not_build_install_or_clone(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / 'apps/oo7-pam/scripts'
            scripts.mkdir(parents=True)
            marker = root / 'mutation'
            (scripts / 'install.sh').write_text(
                '#!/bin/sh\n[ "$1" = --check ] || touch "$MUTATION"\nexit "$CHECK_STATUS"\n'
            )
            (scripts / 'build.sh').write_text('#!/bin/sh\ntouch "$MUTATION"\n')
            for status in (0, 1):
                result = subprocess.run(
                    ['bash', str(ROOT / 'scripts/install-hyprlock-keyring.sh'), '--check'],
                    env={**os.environ, 'TJIKOS_REPO': str(root), 'MUTATION': str(marker), 'CHECK_STATUS': str(status)},
                    capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, status, result.stderr)
                self.assertFalse(marker.exists())

    def test_startup_lock_has_no_grace_and_requests_oo7(self):
        unit = (ROOT / 'native/home/files/.config/systemd/user/hyprlock-login.service.j2').read_text()
        self.assertIn('Wants=oo7-daemon.service', unit)
        self.assertIn('--grace 0 --immediate-render --no-fade-in', unit)
        self.assertNotIn('After=oo7-daemon.service', unit)
