"""Login policy must retain authentication and install its module first."""
import json
import os
from pathlib import Path
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
        self.assertEqual(set(install['roles']), {'desktop', 'laptop'})
        self.assertEqual(install['check'][-1], '--check')

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
