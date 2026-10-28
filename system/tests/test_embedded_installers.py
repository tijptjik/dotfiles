"""Exercise Fish extraction: escaped newlines must never turn Python into a comment."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('chezmoi') and shutil.which('fish'), 'Chezmoi and Fish required')
class EmbeddedInstallerTests(unittest.TestCase):
    def test_python_payload_round_trips_through_fish(self):
        for number in ('54', '56', '57'):
            hook = next((ROOT / 'etc/.chezmoitemplates/tjikup').glob(f'run_{number}-*.tmpl'))
            line = next(line.strip() for line in hook.read_text().splitlines()
                        if 'include ' in line and '"$installer"' in line)
            relative = line.split('include "', 1)[1].split('"', 1)[0]
            with self.subTest(hook=hook.name), tempfile.TemporaryDirectory() as directory:
                temp = Path(directory)
                rendered = subprocess.check_output([
                    'chezmoi', '--source', str(ROOT / 'etc'),
                    '--config', str(temp / 'config.toml'),
                    '--persistent-state', str(temp / 'state.db'),
                    'execute-template', line,
                ], text=True)
                output = temp / 'installer.py'
                subprocess.run(['fish', '--no-config', '-c',
                                'set installer $argv[1]\n' + rendered, str(output)], check=True)
                self.assertEqual(output.read_bytes(), (ROOT / 'etc' / relative).read_bytes())
                compile(output.read_text(), str(output), 'exec')
