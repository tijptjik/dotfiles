"""Apply native system policy to synthetic roots; never touch /etc."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
class NativeIntegrationTests(unittest.TestCase):
    def test_system_manifests_apply_idempotently_in_isolation(self):
        import shutil
        binary=os.environ.get('TJIKUP_BINARY',str(Path.home()/'code/tjikos/apps/tjikup/target/debug/tjikup'))
        for host in ['fi','li','si']:
            with self.subTest(host=host), tempfile.TemporaryDirectory() as directory:
                root=Path(directory);policy=root/'policy'
                shutil.copytree(ROOT/f'system/native/{host}',policy)
                spec=json.loads((policy/'manifest.json').read_text());spec.pop('host')
                for entry in spec['entries']:
                    if 'uid' in entry:entry['uid']=os.getuid();entry['gid']=os.getgid()
                for name in json.loads((policy/'encrypted.json').read_text()) if (policy/'encrypted.json').exists() else []:
                    source=policy/name;source.parent.mkdir(parents=True,exist_ok=True)
                    source.write_text('SYNTHETIC-ENCRYPTED-CONTENT')
                (policy/'manifest.json').write_text(json.dumps(spec))
                destination=root/'destination';destination.mkdir()
                command=[binary,'files','apply','--manifest',str(policy/'manifest.json'),
                         '--state-dir',str(root/'state'),'--root',str(destination)]
                for attempt in range(2):
                    result=subprocess.run(command,capture_output=True,text=True)
                    self.assertEqual(result.returncode,0,result.stderr)
                    if attempt:self.assertIn('SKIP: 0 changed,',result.stdout)
                self.assertFalse((destination/'etc/fstab').exists() and host=='si')
