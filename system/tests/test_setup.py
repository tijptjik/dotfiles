"""The compatibility setup installs the unified runner before its launcher."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SetupTests(unittest.TestCase):
    def test_setup_requires_parent_and_propagates_installer_failure(self):
        for status in [0, 1]:
            with self.subTest(status=status), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / 'system/scripts').mkdir(parents=True)
                (root / 'scripts').mkdir()
                shutil.copy2(ROOT / 'setup.sh', root / 'system/setup.sh')
                result = subprocess.run(['bash', str(root / 'system/setup.sh')], capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                (root / 'tjikup.json').write_text('{}')
                (root / 'scripts/install-tjikup.sh').write_text(f'exit {status}\n')
                (root / 'system/scripts/install-chezetc-wrapper.sh').write_text('touch "' + str(root / 'installed') + '"\n')
                result = subprocess.run(['bash', str(root / 'system/setup.sh')], capture_output=True)
                self.assertEqual(result.returncode, status)
                self.assertEqual((root / 'installed').exists(), status == 0)
