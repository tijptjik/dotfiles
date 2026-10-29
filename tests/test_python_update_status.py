"""Native Python recipe status uses installed versions, not a successful uv exit."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class PythonUpdateStatusTests(unittest.TestCase):
    def test_unchanged_updated_and_failed_upgrade(self):
        source = (ROOT/'native/tasks/home/run_after_30-python-packages.fish.j2').read_text()
        function = source[source.index('function sync_python_environment'):source.index('\nend')+4]
        for changed, failed, expected in [(False, False, 'SKIP'), (True, False, 'SYNC'), (False, True, None)]:
            with self.subTest(changed=changed, failed=failed), tempfile.TemporaryDirectory() as d:
                root=Path(d);bin=root/'bin';bin.mkdir()
                interpreter=root/'.venv/bin/python';interpreter.parent.mkdir(parents=True);interpreter.touch();interpreter.chmod(0o700)
                uv=bin/'uv';uv.write_text('''#!/usr/bin/python3
import json,os,sys
from pathlib import Path
marker=Path(os.environ['HOME'])/'synced'
if sys.argv[1]=='sync':
    if os.environ['FAIL']=='1':sys.exit(9)
    marker.touch()
elif sys.argv[1:3]==['pip','list']:
    version='2' if marker.exists() and os.environ['CHANGED']=='1' else '1'
    print(json.dumps([{'name':'fixture','version':version}]))
''');uv.chmod(0o700)
                script=root/'recipe.fish';script.write_text(function+'\nsync_python_environment\n')
                env={**os.environ,'HOME':str(root),'PATH':str(bin)+':/usr/bin:/bin','TJIKUP_OPERATION':'update','CHANGED':str(int(changed)),'FAIL':str(int(failed))}
                result=subprocess.run(['fish','--no-config',str(script)],env=env,capture_output=True,text=True)
                if failed:
                    self.assertEqual(result.returncode,9)
                    self.assertNotIn('__stage_verb__',result.stdout)
                else:
                    self.assertEqual(result.returncode,0,result.stderr)
                    self.assertIn('__stage_verb__:'+expected,result.stdout)
                    self.assertIn('1 pkgs',result.stdout)
                    self.assertEqual('no changes' in result.stdout,not changed)

    def test_credentials_render_once_per_apply(self):
        data=json.loads((ROOT/'tjikup/recipes.json').read_text())
        recipes=data['recipes']
        recipe=next(r for r in recipes if r['id']=='home:native-files')
        self.assertNotIn('check',recipe)
        self.assertEqual(recipe['apply'][-2:],['credentials','apply'])
