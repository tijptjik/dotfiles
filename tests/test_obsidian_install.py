import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('obsidian_install', ROOT / 'scripts/install-obsidian.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class ObsidianInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.payload = b'official appimage fixture'
        self.asset = {
            'name': 'Obsidian-1.2.3.AppImage', 'size': len(self.payload),
            'browser_download_url': 'https://github.com/obsidianmd/obsidian-releases/releases/download/v1.2.3/Obsidian-1.2.3.AppImage',
            'digest': 'sha256:' + hashlib.sha256(self.payload).hexdigest(),
        }

    def download(self, command, **kwargs):
        Path(command[command.index('--output') + 1]).write_bytes(self.payload)

    def test_verified_install_is_idempotent_and_preserves_profile(self):
        profile = self.home / '.config/obsidian/obsidian.json'
        profile.parent.mkdir(parents=True)
        profile.write_text('existing vault configuration')
        with patch.object(installer.subprocess, 'run', side_effect=self.download) as download:
            self.assertTrue(installer.install(self.home, self.asset))
            self.assertFalse(installer.install(self.home, self.asset))
            self.assertEqual(download.call_count, 1)
        self.assertEqual((self.home / '.local/bin/obsidian-appimage').read_bytes(), self.payload)
        self.assertEqual(profile.read_text(), 'existing vault configuration')

    def test_failed_checksum_does_not_replace_previous_binary_or_link(self):
        with patch.object(installer.subprocess, 'run', side_effect=self.download):
            installer.install(self.home, self.asset)
        link = self.home / '.local/bin/obsidian-appimage'
        previous = link.resolve()
        next_asset = {**self.asset, 'name': 'Obsidian-1.2.4.AppImage', 'digest': 'sha256:' + '0' * 64}
        with patch.object(installer.subprocess, 'run', side_effect=self.download):
            with self.assertRaisesRegex(ValueError, 'checksum'):
                installer.install(self.home, next_asset)
        self.assertEqual(link.resolve(), previous)
        self.assertEqual(previous.read_bytes(), self.payload)
        self.assertFalse(list(previous.parent.glob('*.download')))

    def test_rejects_release_without_digest_or_with_unexpected_source(self):
        for field, value in [('digest', None), ('browser_download_url', 'https://example.org/Obsidian.AppImage')]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                installer.release_asset({'tag_name': 'v1.2.3', 'assets': [{**self.asset, field: value}]}, 'x86_64')

    @unittest.skipUnless(shutil.which('chezmoi') and shutil.which('fish'), 'Chezmoi and Fish required')
    def test_hooks_only_install_on_clients_and_render_valid_fish(self):
        for host in ('fi', 'li', 'si'):
            config = self.home / 'chezmoi.json'
            config.write_text(json.dumps({'data': {'isClient': host != 'si', 'isServer': host == 'si'}}))
            for name in ('run_after_29-install-sublime-text.fish.tmpl', 'run_after_30-install-obsidian.fish.tmpl'):
                rendered = subprocess.check_output([
                    'chezmoi', '--config', str(config), '--source', str(self.home),
                    '--persistent-state', str(self.home / 'state.db'), 'execute-template',
                    '-f', str(ROOT / 'home/.chezmoitemplates/tjikup' / name),
                ], text=True)
                subprocess.run(['fish', '--no-config', '-n'], input=rendered, text=True, check=True)
                self.assertEqual('stage' in rendered, host != 'si')
