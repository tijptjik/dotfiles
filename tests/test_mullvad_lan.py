import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT/'native/tasks/home/run_after_73-mullvad-lan.fish.j2').read_text().split('# Device-independent policy.', 1)[1]
HARNESS = 'function status_msg; echo $argv; end\n' + SCRIPT

class MullvadLanTests(unittest.TestCase):
    def test_allow_is_idempotent_and_block_is_corrected(self):
        for initial in ('allow', 'block'):
            with self.subTest(initial=initial), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root/'state').write_text(initial)
                cli = root/'mullvad'
                cli.write_text('''#!/bin/sh
if [ "$2" = get ]; then printf 'Local network sharing setting: '; cat "$TEST_ROOT/state"; printf '\\n';
else echo "$*" >> "$TEST_ROOT/calls"; printf allow > "$TEST_ROOT/state"; fi
''')
                cli.chmod(0o755)
                result = subprocess.run(['fish','--no-config','-c',HARNESS],env={**os.environ,'PATH':tmp+':/usr/bin','TEST_ROOT':tmp},capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual((root/'state').read_text(),'allow')
                self.assertEqual((root/'calls').exists(), initial=='block')

    def test_set_failure_is_not_hidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            cli=Path(tmp)/'mullvad'
            cli.write_text('#!/bin/sh\nif [ "$2" = get ]; then echo "Local network sharing setting: block"; else exit 7; fi\n')
            cli.chmod(0o755)
            result=subprocess.run(['fish','--no-config','-c',HARNESS],env={**os.environ,'PATH':tmp+':/usr/bin'},capture_output=True,text=True)
            self.assertEqual(result.returncode,7)

    def test_machine_without_mullvad_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=subprocess.run(['/usr/bin/fish','--no-config','-c',HARNESS],env={**os.environ,'PATH':tmp},capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('not installed',result.stdout)
