"""Consolidation and migration checks using synthetic credentials only."""
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class NativeIntegrationTests(unittest.TestCase):
    def test_graph_has_one_dotfiles_repository_and_no_chezetc_manager(self):
        config = json.loads((ROOT / 'tjikup.json').read_text())
        self.assertEqual(config['env']['SYSTJIK_REPO'], '{config_dir}/system')
        self.assertFalse(any(r['id'].startswith('repo:system:') for r in config['recipes']))
        self.assertNotIn('chezetc', json.dumps(config['managers']))
        self.assertTrue((ROOT / 'system/tjikup/recipes.json').is_file())

    def test_native_secrets_have_one_owner_and_legacy_sources_are_retained(self):
        mapping = json.loads((ROOT / 'native/home/migration-sources.json').read_text())
        ignore = (ROOT / 'home/.chezmoiignore').read_text().splitlines()
        for source, destination in mapping.items():
            self.assertTrue((ROOT / 'home' / source).is_file())
            self.assertIn(destination, ignore)
        for host, count in [('fi', 7), ('li', 5), ('si', 2)]:
            spec = json.loads((ROOT / 'native/home' / (host + '.json')).read_text())
            self.assertEqual(len(spec['entries']), count)
            for entry in spec['entries']:
                self.assertTrue(entry['sensitive'])
                self.assertEqual(entry['mode'], '0600')
                self.assertTrue((ROOT / 'native/home' / entry['source']).is_file())

    def test_system_helper_selects_native_fi_and_legacy_server_without_hooks(self):
        module = runpy.run_path(str(ROOT / 'scripts/native-files.py'))
        for host in ['fi', 'li', 'si']:
            with self.subTest(host=host), patch('socket.gethostname', return_value=host), \
                    patch.object(sys, 'argv', ['native-files', 'system', 'apply']), \
                    patch('subprocess.call', return_value=0) as call:
                self.assertEqual(module['main'](), 0)
                argv = call.call_args.args[0]
                if host == 'fi':
                    self.assertEqual(argv[:3], ['sudo', '-n', '--'])
                    self.assertIn(str(ROOT / 'system/native/fi/manifest.json'), argv)
                else:
                    self.assertIn(str(ROOT / 'scripts/legacy-system.py'), argv)
                    self.assertIn('--exclude=scripts', argv)

    def test_legacy_adapter_selects_consolidated_source_and_private_identity(self):
        module = runpy.run_path(str(ROOT / 'scripts/legacy-system.py'))
        with tempfile.TemporaryDirectory() as directory, \
                patch.dict(os.environ, {'XDG_STATE_HOME': directory}), \
                patch('socket.gethostname', return_value='si'), \
                patch.object(sys, 'argv', ['legacy-system', 'execute-template']), \
                patch('subprocess.call', return_value=0) as call:
            self.assertEqual(module['main'](), 0)
            config = tomllib.loads((Path(directory) / 'tjikup/legacy-system/config.toml').read_text())
            self.assertEqual(config['sourceDir'], str(ROOT / 'system/etc'))
            self.assertEqual(config['destDir'], '/etc')
            self.assertTrue(config['data']['isServer'])
            self.assertEqual(config['age']['identity'], str(Path.home() / '.keys/chezmoi.txt'))
            self.assertIn('TJIKUP_COLOR', call.call_args.args[0][2])

    def test_migration_refuses_drift_and_keeps_create_only_values(self):
        adopt = runpy.run_path(str(ROOT / 'scripts/migrate-native-home.py'))['adopt']
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'native/home').mkdir(parents=True)
            (root / 'native/home/migration-sources.json').write_text(json.dumps({'source.tmpl': 'secret'}))
            target = root / 'secret'; target.write_text('SYNTHETIC-LOCAL')
            manifest = root / 'manifest.json'
            spec = {'version': 1, 'id': 'test', 'host': 'fi', 'context': {'user': {'home': str(root)}},
                    'entries': [{'path': '{{ user.home }}/secret'}]}
            manifest.write_text(json.dumps(spec))
            with patch('subprocess.run', return_value=subprocess.CompletedProcess([], 0, b'SYNTHETIC-DESIRED')) as run:
                with self.assertRaisesRegex(RuntimeError, 'differs from its legacy template'):
                    adopt(root, manifest, root / 'state', 'tjikup')
                self.assertEqual(run.call_count, 1)
            self.assertEqual(target.read_text(), 'SYNTHETIC-LOCAL')
            spec['entries'][0]['create_only'] = True
            manifest.write_text(json.dumps(spec))
            def native(argv, **kwargs):
                baseline = json.loads(Path(argv[4]).read_text())
                self.assertEqual(baseline['entries'][0]['path'], str(target))
                return subprocess.CompletedProcess(argv, 0, 'SKIP: 0 changed, 1 unchanged\n')
            with patch('subprocess.run', side_effect=native) as run:
                adopt(root, manifest, root / 'state', 'tjikup')
                self.assertEqual(run.call_count, 1)
            self.assertEqual(target.read_text(), 'SYNTHETIC-LOCAL')
