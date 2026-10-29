"""Render each role's Transmission files into synthetic homes."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get('TJIKUP_BINARY', str(Path.home() / 'code/tjikos/apps/tjikup/target/debug/tjikup'))


class TransmissionPolicyTests(unittest.TestCase):
    def test_desktop_settings_cannot_replace_server_daemon_state(self):
        entries = [e for e in json.loads((ROOT / 'native/home/files.json').read_text())
                   if '/.config/transmission' in e['path']]
        for host in ('fi', 'li', 'si'):
            with self.subTest(host=host), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                stage = root / 'stage'
                stage.mkdir()
                config = stage / 'home/test/.config/transmission'
                config.mkdir(parents=True)
                config.chmod(0o755)
                server_state = b'{"daemon-only":true,"rpc-port":9091}\n'
                if host == 'si':
                    (config / 'settings.json').write_bytes(server_state)
                for entry in entries:
                    if 'source' in entry:
                        target = root / entry['source']
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(ROOT / 'native/home' / entry['source'], target)
                manifest = {'version': 1, 'id': 'transmission-test', 'context': {
                    'hostname': host, 'is_server': host == 'si', 'is_client': host != 'si',
                    'user': {'home': '/home/test'}}, 'entries': entries}
                (root / 'manifest.json').write_text(json.dumps(manifest))
                result = subprocess.run([BINARY, 'files', 'apply', '--manifest', str(root / 'manifest.json'),
                                '--state-dir', str(root / 'state'), '--root', str(stage)],
                               capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual((config / 'configure-archive-hook.sh').exists(), host == 'si')
                self.assertEqual((config / 'extract.fish').exists(), host != 'si')
                if host == 'si':
                    self.assertEqual((config / 'settings.json').read_bytes(), server_state)
                else:
                    settings = json.loads((config / 'settings.json').read_text())
                    self.assertFalse(settings['rpc-enabled'])
                    self.assertFalse(settings['alt-speed-time-enabled'])
                    self.assertTrue(settings['script-torrent-done-enabled'])
                    self.assertEqual(settings['download-dir'], '/home/test/downloads')

    def test_server_startup_hook_preserves_daemon_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = Path(directory) / 'settings.json'
            settings.write_text(json.dumps({'rpc-port': 9091, 'rpc-password': 'synthetic',
                                             'script-torrent-done-enabled': True}))
            subprocess.run(['sh', str(ROOT / 'native/home/files/.config/transmission/configure-archive-hook.sh')],
                           env={**os.environ, 'TRANSMISSION_SETTINGS_FILE': str(settings),
                                'TRANSMISSION_DOWNLOAD_DIR': '/synthetic/server/downloads'},
                           check=True, capture_output=True)
            value = json.loads(settings.read_text())
            self.assertEqual(value['rpc-password'], 'synthetic')
            self.assertEqual(value['rpc-port'], 9091)
            self.assertFalse(value['script-torrent-done-enabled'])
            self.assertTrue(value['alt-speed-time-enabled'])
            self.assertEqual(value['download-dir'], '/synthetic/server/downloads')
            self.assertEqual(value['umask'], 2)
