"""Fi-only author key policy; synthetic BWS, no live secrets."""
import json, os, subprocess, tempfile, unittest
from pathlib import Path
from test_cargo_credentials import CargoCredentialTests, ROOT

class WhoopsCredentials(CargoCredentialTests):
    def test_author_key_is_fi_only(self):
        for host in ('fi','li','si','device'):
            with self.subTest(host=host), tempfile.TemporaryDirectory() as tmp:
                command,env,_,_,_=self.fixture(Path(tmp),host)
                command[-1]='whoops-authoring'
                manifest=Path(command[command.index('--manifest')+1])
                spec=json.loads(manifest.read_text())
                secret='00000000-0000-4000-8000-000000000123'
                if host=='fi': spec['context']['whoops_author_secret_id']=secret
                value=json.dumps({'schema':'whoops-author-config/1','synthetic':True,'encryptedKey':{'ciphertext':'synthetic-only'}})
                mock=Path(tmp)/'bws'
                mock.write_text('#!/usr/bin/env python3\nimport json,sys\nassert sys.argv[1:4]=='+repr(['secret','get',secret])+'\nprint('+repr(json.dumps({'id':secret,'value':value}))+')\n')
                manifest.write_text(json.dumps(spec))
                output=Path(tmp)/'destination/fixture/home/.config/whoops/authoring.json'
                for _ in range(2):
                    result=subprocess.run(command,capture_output=True,text=True,env=env)
                    self.assertEqual(result.returncode,0 if host=='fi' else 2,result.stderr)
                    if host!='fi': self.assertIn('unknown file group',result.stderr)
                    self.assertNotIn(value,result.stdout+result.stderr)
                self.assertEqual(output.exists(),host=='fi')
                if host=='fi':
                    self.assertEqual(output.read_text(),value)
                    self.assertEqual(output.stat().st_mode&0o777,0o600)
