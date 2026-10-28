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
                    ('dotjik/system', ROOT / 'system/chezetc.toml', 'etc'),
                ):
                    with self.subTest(host=host, checkout=name):
                        checkout = home / '.local/share' / name
                        (checkout / subdir).mkdir(parents=True, exist_ok=True)
                        (checkout / '.chezmoiroot').write_text(subdir + '\n')
                        if subdir == 'home':
                            # This fixture tests relocated source paths; role policy has
                            # separate profile and real-template integration coverage.
                            helper = checkout / 'scripts/device-policy.py'
                            helper.parent.mkdir(exist_ok=True)
                            role = {'fi': 'desktop', 'li': 'laptop', 'si': 'server'}[host]
                            helper.write_text('print(' + repr(role) + ')\n')
                        data = {'chezmoi': {'hostname': host, 'homeDir': str(home),
                                           'username': 'm' if host == 'si' else 'io'}}
                        rendered = subprocess.run([
                            'chezmoi', '--config', str(minimal), '--source', str(checkout),
                            '--override-data', json.dumps(data), 'execute-template',
                            '--file', str(template),
                        ], check=True, text=True, capture_output=True).stdout
                        config = home / (name.replace('/', '-') + '.toml')
                        config.write_text(rendered)
                        self.assertEqual(tomllib.loads(rendered)['sourceDir'], str(checkout))
                        result = subprocess.run([
                            'chezmoi', '--config', str(config), 'source-path',
                        ], check=True, text=True, capture_output=True)
                        self.assertEqual(result.stdout.strip(), str(checkout / subdir))
