"""Verify renamed sources without relying on the compatibility symlinks."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('chezmoi'), 'Chezmoi required')
class CheckoutPathsTests(unittest.TestCase):
    def test_rendered_configuration_selects_renamed_sources_for_each_host(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            minimal = home / 'render.toml'
            minimal.write_text('[data]\n')
            for host in ('fi', 'li', 'si'):
                for name, template, subdir in (
                    ('dotjik', ROOT / 'home/.chezmoi.toml.tmpl', 'home'),
                    ('systjik', ROOT.parent / 'systjik/chezetc.toml', 'etc'),
                ):
                    with self.subTest(host=host, checkout=name):
                        checkout = home / '.local/share' / name
                        (checkout / subdir).mkdir(parents=True, exist_ok=True)
                        (checkout / '.chezmoiroot').write_text(subdir + '\n')
                        data = {'chezmoi': {'hostname': host, 'homeDir': str(home),
                                           'username': 'm' if host == 'si' else 'io'}}
                        rendered = subprocess.run([
                            'chezmoi', '--config', str(minimal), '--source', str(checkout),
                            '--override-data', json.dumps(data), 'execute-template',
                            '--file', str(template),
                        ], check=True, text=True, capture_output=True).stdout
                        config = home / (name + '.toml')
                        config.write_text(rendered)
                        self.assertEqual(tomllib.loads(rendered)['sourceDir'], str(checkout))
                        result = subprocess.run([
                            'chezmoi', '--config', str(config), 'source-path',
                        ], check=True, text=True, capture_output=True)
                        self.assertEqual(result.stdout.strip(), str(checkout / subdir))

    def test_system_launcher_defaults_to_systjik_and_preserves_override(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stub = root / 'wrapper'
            stub.write_text('#!/bin/sh\nprintf "%s\\n" "$ETC_SRC" "$@"\n')
            stub.chmod(0o755)
            launcher = root / 'launcher'
            launcher.write_text((ROOT.parent / 'systjik/scripts/chezetc-launcher.sh')
                                .read_text().replace('/opt/chezetc/chezetc', str(stub)))
            env = {**os.environ, 'HOME': str(root)}
            env.pop('ETC_SRC', None)
            env.pop('XDG_DATA_HOME', None)
            for overrides, expected in (
                ({}, root / '.local/share/systjik'),
                ({'XDG_DATA_HOME': str(root / 'data')}, root / 'data/systjik'),
                ({'ETC_SRC': str(root / 'custom')}, root / 'custom'),
            ):
                with self.subTest(overrides=overrides):
                    result = subprocess.run(['sh', str(launcher), 'source-path'],
                                            env={**env, **overrides}, check=True,
                                            text=True, capture_output=True)
                    self.assertEqual(result.stdout.splitlines(), [str(expected), 'source-path'])
