"""Consolidation and migration checks using synthetic credentials only."""
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))


class NativeIntegrationTests(unittest.TestCase):
    def test_graph_has_one_dotfiles_repository_and_no_chezetc_manager(self):
        config = json.loads((ROOT / 'tjikup.json').read_text())
        self.assertEqual(config['env']['SYSTJIK_REPO'], '{config_dir}/system')
        self.assertFalse(any(r['id'].startswith('repo:system:') for r in config['recipes']))
        self.assertNotIn('chezetc', json.dumps(config.get('managers', {})))
        self.assertTrue((ROOT / 'system/tjikup/recipes.json').is_file())

    def test_native_secrets_have_one_owner_and_legacy_sources_are_retained(self):
        mapping = json.loads((ROOT / 'native/home/migration-sources.json').read_text())
        ignore = (ROOT / 'home/.chezmoiignore').read_text().splitlines()
        for source, destination in mapping.items():
            self.assertTrue((ROOT / 'home' / source).is_file())
            self.assertIn(destination, ignore)
        for host, count in [('fi', 7), ('li', 5), ('si', 2)]:
            spec = json.loads((ROOT / 'native/home' / (host + '.json')).read_text())
            self.assertEqual(len(spec['entries']), count)
            for entry in spec['entries']:
                self.assertTrue(entry['sensitive'])
                self.assertEqual(entry['mode'], '0600')
                self.assertTrue((ROOT / 'native/home' / entry['source']).is_file())

    def test_system_helper_selects_native_for_every_fleet_host(self):
        module = runpy.run_path(str(ROOT / 'scripts/native-files.py'))
        for host in ['fi', 'li', 'si']:
            with self.subTest(host=host), patch('socket.gethostname', return_value=host), \
                    patch.object(sys, 'argv', ['native-files', 'system', 'apply']), \
                    patch('subprocess.call', return_value=0) as call:
                self.assertEqual(module['main'](), 0)
                self.assertEqual(call.call_args.args[0][-2:], [str(ROOT / 'scripts/system-files.py'), 'apply'])

    def test_server_decrypts_privately_and_never_calls_chezmoi(self):
        module = runpy.run_path(str(ROOT / 'scripts/system-files.py'))
        staged = []
        def check(argv):
            self.assertEqual(argv[:3], ['sudo','-n','--'])
            manifest = Path(argv[argv.index('--manifest') + 1]);staged.append(manifest)
            spec = json.loads(manifest.read_text())
            secrets = [entry for entry in spec['entries'] if entry.get('sensitive')]
            self.assertEqual(len(secrets),6)
            for entry in secrets:
                source=manifest.parent/entry['source']
                self.assertEqual(source.read_bytes(),b'SYNTHETIC-SECRET')
                self.assertEqual(source.stat().st_mode & 0o777,0o600)
                self.assertEqual(entry['mode'],'0600')
            return 0
        with patch('socket.gethostname',return_value='si'), patch.object(sys,'argv',['system-files','plan']), \
                patch('subprocess.run',return_value=subprocess.CompletedProcess([],0,b'SYNTHETIC-SECRET',b'')) as decrypt, \
                patch('subprocess.call',side_effect=check):
            self.assertEqual(module['main'](),0)
            self.assertEqual(decrypt.call_count,6)
            self.assertTrue(all(call.args[0][0]=='age' for call in decrypt.call_args_list))
        self.assertFalse(staged[0].exists())

    def test_failed_server_decryption_never_starts_native_apply(self):
        module=runpy.run_path(str(ROOT/'scripts/system-files.py'))
        with patch('socket.gethostname',return_value='si'), patch.object(sys,'argv',['system-files','apply']), \
                patch('subprocess.run',return_value=subprocess.CompletedProcess([],1,b'',b'PRIVATE-MARKER')), \
                patch('subprocess.call') as apply:
            with self.assertRaisesRegex(RuntimeError,'decryption failed') as error:module['main']()
            self.assertNotIn('PRIVATE-MARKER',str(error.exception));apply.assert_not_called()

    def test_native_adoption_accepts_only_equal_bytes_and_preserves_live_metadata(self):
        import socket
        from native_adoption import adopt
        binary=os.environ.get('TJIKUP_BINARY',str(Path.home()/'code/tjikos/apps/tjikup/target/debug/tjikup'))
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);target=root/'target';target.write_text('desired');target.chmod(0o644)
            (root/'source').write_text('desired')
            manifest=root/'manifest.json';state=root/'state'
            manifest.write_text(json.dumps({'version':1,'id':'adopt','host':socket.gethostname(),
                'entries':[{'kind':'file','path':str(target),'source':'source','mode':'0600'}]}))
            command=[binary,'files','apply','--manifest',str(manifest),'--state-dir',str(state)]
            before=target.stat().st_ino
            adopt(manifest,state,command)
            self.assertEqual(target.stat().st_ino,before);self.assertEqual(target.stat().st_mode & 0o777,0o644)
            self.assertTrue((state/'adopt.json').exists())
            import shutil
            shutil.rmtree(state);target.write_text('local edit')
            with self.assertRaisesRegex(RuntimeError,'Local changes'):adopt(manifest,state,command)
            self.assertEqual(target.read_text(),'local edit');self.assertFalse(state.exists())

    def test_system_manifests_apply_idempotently_in_isolation(self):
        import shutil
        binary=os.environ.get('TJIKUP_BINARY',str(Path.home()/'code/tjikos/apps/tjikup/target/debug/tjikup'))
        for host in ['li','si']:
            with self.subTest(host=host), tempfile.TemporaryDirectory() as directory:
                root=Path(directory);policy=root/'policy'
                shutil.copytree(ROOT/f'system/native/{host}',policy)
                spec=json.loads((policy/'manifest.json').read_text());spec.pop('host')
                for entry in spec['entries']:
                    if 'uid' in entry:entry['uid']=os.getuid();entry['gid']=os.getgid()
                for name in json.loads((policy/'encrypted.json').read_text()):
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
