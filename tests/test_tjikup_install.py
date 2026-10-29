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
        self.assertLess(text.index('--check'),text.index('cache-install'))
        self.assertNotIn('PYTHONPATH',text)

    def test_incompatible_release_preserves_compatible_runner_without_caching(self):
        self.release_case(candidate=1, installed=0, success=True, installs=False)

    def test_incompatible_release_and_runner_fail_without_replacing_files(self):
        self.release_case(candidate=1, installed=1, success=False, installs=False)

    def test_compatible_release_still_enters_normal_install_path(self):
        self.release_case(candidate=0, installed=0, success=True, installs=True)

    def test_old_release_with_valid_workflow_preserves_cache_capable_runner(self):
        self.release_case(candidate=0, installed=0, success=True, installs=False, candidate_cache=False)

    def test_old_release_and_old_runner_fail_even_with_valid_workflow(self):
        self.release_case(candidate=0, installed=0, success=False, installs=False, candidate_cache=False, installed_cache=False)

    def release_case(self, candidate, installed, success, installs, candidate_cache=True, installed_cache=True):
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory);repo=home/'checkout';tool=home/'tool'
            (repo/'scripts').mkdir(parents=True);(repo/'system/tjikup').mkdir(parents=True)
            (repo/'system/tjikup/recipes.json').write_text('{}')
            (repo/'tjikup.json').write_text('{}')
            shutil.copy2(ROOT/'scripts/install-tjikup.sh',repo/'scripts/install-tjikup.sh')
            (repo/'scripts/ensure-tjikos.sh').write_text('ensure_tjikos() { tool_repo="$TEST_TOOL_REPO"; }\n')
            marker=home/'cache-called'
            (tool/'apps/tjikup/scripts').mkdir(parents=True);(tool/'apps/tjikup/dist').mkdir()
            (tool/'apps/tjikup/scripts/fetch-release.sh').write_text('#!/bin/sh\nexit 0\n')
            for path,code in [(tool/'apps/tjikup/dist/tjikup',candidate),(home/'.local/bin/tjikup',installed)]:
                path.parent.mkdir(parents=True,exist_ok=True);path.write_text('#!/bin/sh\nif [ "$1" = capabilities ]; then\n  echo \'{"bootstrap_archives":1,"native_commands":1,"native_installers":1,"native_maintenance":1,"native_workflow":' + str(int(candidate_cache if path == tool/'apps/tjikup/dist/tjikup' else installed_cache)) + '}\'\n  exit 0\nfi\nif [ \"$1\" = workflow ]; then touch \"$TEST_CACHE_MARKER\"; exit 0; fi\nexit '+str(code)+'\n');path.chmod(0o755)
            target=home/'.local/bin/tjikup';before=target.read_bytes()
            result=subprocess.run(['bash',str(repo/'scripts/install-tjikup.sh')],capture_output=True,text=True,
                env={**os.environ,'HOME':str(home),'XDG_CONFIG_HOME':str(home/'.config'),'TEST_TOOL_REPO':str(tool),'TEST_CACHE_MARKER':str(marker)})
            self.assertEqual(result.returncode==0,success,result.stderr)
            self.assertEqual(target.read_bytes(),before)
            self.assertEqual(marker.exists(),installs)
            if success and not installs:
                self.assertIn('__stage_verb__:SKIP',result.stdout)
                self.assertIn('__stage_note__:awaiting compatible release',result.stdout)
