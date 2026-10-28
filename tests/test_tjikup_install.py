from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class InstallTests(unittest.TestCase):
    def test_missing_system_recipes_leave_existing_runner_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory)
            executable=home/'.local/bin/tjikup'
            executable.parent.mkdir(parents=True)
            executable.write_text('original')
            script=home/'checkout/scripts/install-tjikup.sh'
            script.parent.mkdir(parents=True)
            shutil.copy2(ROOT/'scripts/install-tjikup.sh',script)
            result=subprocess.run(['bash',str(script)],env={**os.environ,'HOME':directory},capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(executable.read_text(),'original')

    def test_recipe_validation_precedes_install(self):
        text=(ROOT/'scripts/install-tjikup.sh').read_text()
        self.assertLess(text.index('--check'),text.index('scripts/cache-install.py'))
        self.assertNotIn('PYTHONPATH',text)
