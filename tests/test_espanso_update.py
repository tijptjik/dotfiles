"""Exercise Espanso update selection for isolated Fi/Li/Si enrollment profiles."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get('TJIKUP_BINARY', str(Path.home() / 'code/tjikos/apps/tjikup/target/debug/tjikup'))


class EspansoUpdate(unittest.TestCase):
    def test_updates_follow_runtjik_subscription_on_clients_only(self):
        recipes = json.loads((ROOT / 'tjikup/recipes.json').read_text())['recipes']
        selected = [r for r in recipes if r['id'].startswith('home:espanso:')]
        self.assertEqual(len(selected), 2)
        for host, role in [('fi', 'desktop'), ('li', 'laptop'), ('si', 'server')]:
            with self.subTest(host=host), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                profile = root / 'device.json'
                profile.write_text(json.dumps({'version': 1, 'hostname': os.uname().nodename.split('.')[0], 'role': role,
                                               'subscriptions': ['home:runtjik']}))
                graph = {'version': 2, 'device_file': str(profile), 'recipes': [
                    {'id': 'home:runtjik', 'optional': True, 'apply': ['true'], 'operation': 'install',
                     'check': ['true'], 'application': 'runtjik'},
                    {'id': 'require:sudo', 'check': ['true']},
                    {'id': 'fixture:update', 'apply': ['true'], 'operation': 'update'}, *selected]}
                config = root / 'config.json'
                config.write_text(json.dumps(graph))
                result = subprocess.run([BINARY, '--config', str(config), '--apply-package-updates', '--plan'],
                                        env={**os.environ, 'HOME': str(root), 'XDG_CONFIG_HOME': str(root / 'config'),
                                             'XDG_STATE_HOME': str(root / 'state'), 'XDG_CACHE_HOME': str(root / 'cache')},
                                        text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                if role == 'server':
                    self.assertNotIn('Espanso patched updates', result.stdout)
                else:
                    self.assertIn('Espanso patched updates', result.stdout)
                    self.assertIn('home:espanso:update:verify', result.stdout)
                self.assertFalse((root / '.local/bin/espanso').exists())
