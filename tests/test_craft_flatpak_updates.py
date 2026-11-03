"""Keep GitHub bundle updates scoped to subscribed clients and installed apps."""
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get('TJIKUP_BINARY', str(Path.home() / 'code/tjikos/apps/tjikup/target/debug/tjikup'))
APPS = ('pdfcraft', 'wordcraft')


class CraftFlatpakUpdatesTests(unittest.TestCase):
    def test_normal_flatpak_subscription_selects_updates_without_new_enrollment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile = root / 'device.json'
            config = json.loads((ROOT / 'tjikup.json').read_text())
            config['device_file'] = str(profile)
            config['env']['DOTJIK_REPO'] = str(ROOT)
            config['env']['SYSTJIK_REPO'] = str(ROOT / 'system')
            config['includes'] = [str(ROOT / 'tjikup/recipes.json'), str(ROOT / 'system/tjikup/recipes.json')]
            config_path = root / 'tjikup.json'
            config_path.write_text(json.dumps(config))
            cases = [
                ('desktop', ['system:flatpak'], [], True),
                ('laptop', ['system:flatpak'], [], True),
                ('desktop', ['system:flatpak'], ['--apply-package-updates'], True),
                ('desktop', ['system:flatpak'], ['--skip-package-updates'], False),
                ('desktop', ['system:flatpak'], ['--apply-dotfiles', '--apply-sysfiles'], False),
                ('desktop', [], [], False),
                ('server', [], [], False),
            ]
            for role, subscriptions, flags, expected in cases:
                with self.subTest(role=role, subscriptions=subscriptions, flags=flags):
                    profile.write_text(json.dumps({
                        'version': 1, 'hostname': socket.gethostname(),
                        'role': role, 'subscriptions': subscriptions,
                    }))
                    result = subprocess.run(
                        [BINARY, '--config', str(config_path), '--plan', *flags],
                        env={**os.environ, 'XDG_STATE_HOME': str(root / 'state')},
                        capture_output=True, text=True,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    ids = {line.split(' · ')[0] for line in result.stdout.splitlines() if not line.startswith(' ')}
                    for app in APPS:
                        self.assertEqual(f'system:{app}:update' in ids, expected, result.stdout)
                        self.assertNotIn(f'system:{app}', ids)

    def test_update_presence_checks_only_accept_the_system_installation(self):
        policies = json.loads((ROOT / 'tjikup/package-checks.json').read_text())
        recipes = {recipe['application']: recipe for recipe in
                   json.loads((ROOT / 'system/tjikup/recipes.json').read_text())['recipes']
                   if recipe['id'] in {f'system:{app}:update' for app in APPS}}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'tjikup').mkdir()
            (root / 'bin').mkdir()
            (root / 'tjikup/package-checks.json').write_text(json.dumps({app: policies[app] for app in APPS}))
            profile = root / 'device.json'
            profile.write_text(json.dumps({
                'version': 1, 'hostname': socket.gethostname(), 'role': 'desktop', 'subscriptions': [],
            }))
            (root / 'tjikup.json').write_text(json.dumps({
                'version': 2, 'device_file': str(profile), 'recipes': [{'id': 'fixture', 'check': ['true']}],
            }))
            flatpak = root / 'bin/flatpak'
            flatpak.write_text('#!/bin/sh\n'
                               '[ "$1" = info ] && [ "$2" = --system ] && [ "$3" = "$CRAFT_APP_ID" ] || exit 9\n'
                               'exit "$CRAFT_INSTALLED_STATUS"\n')
            flatpak.chmod(0o755)
            for app in APPS:
                for installed, expected in [('0', 1), ('1', 0)]:
                    with self.subTest(app=app, installed=installed):
                        command = recipes[app]['check']
                        self.assertEqual(command[:2], ['tjikup', 'workflow'])
                        result = subprocess.run(
                            [BINARY, 'workflow', '--repo', str(root), *command[2:]],
                            env={**os.environ, 'PATH': str(root / 'bin') + ':' + os.environ['PATH'],
                                 'CRAFT_APP_ID': f'ai.storyteller.{app}', 'CRAFT_INSTALLED_STATUS': installed},
                            capture_output=True, text=True,
                        )
                        self.assertEqual(result.returncode, expected, result.stderr)
