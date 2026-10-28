"""Package presence and phase dispatch use isolated local state only."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import tjikup_support

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get('TJIKOS_REPO', str(Path.home() / 'code/tjikos'))) / 'apps/tjikup/target/debug/tjikup'
spec = importlib.util.spec_from_file_location('package_task', ROOT / 'scripts/package-task.py')
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)

class PackagePhases(unittest.TestCase):
    def test_partial_group_dispatch_and_nonapplicable_roles(self):
        for values, mode, expected in [
            ([True, True], 'install', False), ([True, False], 'install', True),
            ([False, False], 'install', True), ([True, False], 'update', True),
            ([False, False], 'update', False), (None, 'install', False), (None, 'update', False),
        ]:
            with self.subTest(values=values, mode=mode), \
                    patch.object(package, 'presence', return_value=values), \
                    patch.object(package, 'context', return_value={'role': 'desktop'}), \
                    patch.object(package.subprocess, 'call', return_value=0) as call, \
                    patch.dict(os.environ, {'TJIKUP_OPERATION': mode}), \
                    patch.object(sys, 'argv', ['package-task', 'run', 'terminal', '--', 'synthetic']):
                self.assertEqual(package.main(), 0)
                self.assertEqual(call.called, expected)
                if expected:
                    call.assert_called_once_with(['synthetic'])

    def test_plugin_presence_is_local_and_matches_exact_id(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'HOME': directory}), \
                patch.object(package.subprocess, 'run', side_effect=AssertionError('must not run commands')):
            root = Path(directory) / '.config/herdr/plugins/github/herdr.collie-abcdef'
            root.mkdir(parents=True)
            (root / 'herdr-plugin.toml').write_text('id = "herdr.collie"\n')
            self.assertTrue(package.test({'plugin': 'herdr.collie'}))
            self.assertFalse(package.test({'plugin': 'herdr'}))

    def test_install_checks_use_only_local_queries(self):
        calls = []
        def query(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0)
        with patch.object(package.subprocess, 'run', side_effect=query), \
                patch.object(package.shutil, 'which', return_value='/synthetic/tool'):
            self.assertTrue(package.test({'rpm': 'example'}))
            self.assertTrue(package.test({'flatpak': 'example.App'}))
        self.assertEqual(calls, [['rpm', '-q', 'example'], ['flatpak', 'info', '--system', 'example.App']])

    @unittest.skipUnless(BINARY.is_file(), 'build tjikup first')
    def test_real_plans_for_modes_and_device_companions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            documents = []
            for path in ['tjikup.json', 'tjikup/recipes.json', 'system/tjikup/recipes.json']:
                documents.append(json.loads((ROOT / path).read_text()))
            config = {'version': 2, 'device_file': str(root / 'device.json'),
                      'recipes': [], 'prerequisites': []}
            for doc in documents:
                for r in doc.get('prerequisites', []):
                    config['prerequisites'].append({'id': r['id'], 'check': ['true']})
                for r in doc['recipes']:
                    item = {k: v for k, v in r.items() if k in {
                        'id', 'needs', 'after', 'operation', 'scope', 'part_of', 'optional', 'roles', 'hosts'}}
                    if any(key in r for key in ['apply', 'render', 'files', 'git', 'autocommit']):
                        item['apply'] = ['touch', 'BAD']
                    if 'check' in r:
                        item['check'] = ['true']
                    config['recipes'].append(item)
            path = root / 'config.json'; path.write_text(json.dumps(config))
            for role in ['desktop', 'laptop', 'server']:
                for all_optional in [False, True]:
                    subscriptions = [r['id'] for r in config['recipes'] if r.get('optional')
                                     and (not r.get('roles') or role in r['roles'])
                                     and (not r.get('hosts') or os.uname().nodename in r['hosts'])] if all_optional else []
                    (root / 'device.json').write_text(json.dumps({'version': 1, 'hostname': os.uname().nodename,
                                                                'role': role, 'subscriptions': subscriptions}))
                    for mode in [[], ['--skip-package-updates'], ['--apply-dotfiles'], ['--apply-sysfiles'],
                                 ['--apply-package-updates'], ['--apply-dotfiles', '--apply-sysfiles', '--apply-package-updates']]:
                        with self.subTest(role=role, all_optional=all_optional, mode=mode):
                            result = subprocess.run([str(BINARY), '--config', str(path), '--plan', *mode],
                                                    capture_output=True, text=True)
                            self.assertEqual(result.returncode, 0, result.stderr)
                            if mode and mode != ['--skip-package-updates']:
                                self.assertNotIn('repo:home:push ·', result.stdout)
                                self.assertNotIn('capture:live ·', result.stdout)
                self.assertFalse((root / 'BAD').exists())

    def test_declared_file_groups_have_targets_and_unique_destinations(self):
        groups = set(json.loads((ROOT / 'native/home/groups.json').read_text()))
        recipes = json.loads((ROOT / 'tjikup/recipes.json').read_text())['recipes']
        for recipe in recipes:
            args = recipe.get('apply', [])
            if '--group' in args:
                self.assertIn(args[args.index('--group') + 1], groups)
        for name in ['files.json', 'portable-files.json']:
            entries = json.loads((ROOT / 'native/home' / name).read_text())
            paths = [entry['path'] for entry in entries]
            self.assertEqual(len(paths), len(set(paths)), name)
            self.assertTrue({entry['group'] for entry in entries} <= groups)

    def test_redispatch_preserves_phase_environment(self):
        helper = (ROOT / 'system/etc/.chezmoihelpers/desktop-user.fish').read_text()
        self.assertIn('TJIKUP_OPERATION,TJIKUP_MANAGED_CONFIG,TJIKUP_SELECTED_RUN,FLEET_UPGRADE', helper)
