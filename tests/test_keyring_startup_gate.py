import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / 'native/home/files/.local/bin/after-keyring-unlock'

class KeyringStartupGateTests(unittest.TestCase):
    def test_unavailable_and_locked_do_not_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bus = root / 'busctl'
            bus.write_text('''#!/bin/sh
n=$(cat "$STATE" 2>/dev/null || echo 0)
n=$((n+1)); echo "$n" > "$STATE"
case "$n" in
1) exit 1;;
2) echo 'b true';;
*) echo 'b false';;
esac
''')
            bus.chmod(0o755)
            env = dict(os.environ, PATH=str(root)+':'+os.environ['PATH'], STATE=str(root/'state'))
            subprocess.run([str(GATE), 'sh', '-c', 'cat "$STATE" > "$1"', 'sh', str(root/'launched')], env=env,check=True,timeout=5)
            self.assertEqual((root/'launched').read_text().strip(),'3')
