import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('zed_launcher',ROOT/'scripts/preserve-zed-launcher.py')
launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)

class ZedLauncherTests(unittest.TestCase):
    def fixture(self, home, channel):
        suffix='' if channel=='stable' else '-'+channel
        appid='dev.zed.Zed'+('' if channel=='stable' else '-'+channel.capitalize())
        bundle=home/('.local/zed'+suffix+'.app/share/applications');bundle.mkdir(parents=True)
        (bundle/(appid+'.desktop')).write_text('[Desktop Entry]\nTryExec=zed\nExec=zed %U\nIcon=zed\n')
        target=home/'.local/share/applications'/(appid+'.desktop');target.parent.mkdir(parents=True)
        return target

    def test_update_restores_launcher_even_when_installer_fails(self):
        for channel in ['stable','preview']:
            for code in [0,1]:
                with self.subTest(channel=channel,code=code), tempfile.TemporaryDirectory() as directory, patch.dict(os.environ,{},clear=True):
                    home=Path(directory);target=self.fixture(home,channel)
                    target.write_bytes(b'custom themed launcher\n');target.chmod(0o755)
                    def install(command):
                        target.write_bytes(launcher.vendor_launcher(home,channel));return code
                    with patch.object(launcher.subprocess,'call',side_effect=install):
                        self.assertEqual(launcher.run(home,channel,['installer']),code)
                    self.assertEqual(target.read_bytes(),b'custom themed launcher\n')
                    self.assertEqual(target.stat().st_mode & 0o777,0o755)

    def test_fresh_install_leaves_launcher_creation_to_native_policy(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ,{},clear=True):
            home=Path(directory);target=self.fixture(home,'stable')
            def install(command):target.write_bytes(launcher.vendor_launcher(home,'stable'));return 0
            with patch.object(launcher.subprocess,'call',side_effect=install):
                self.assertEqual(launcher.run(home,'stable',['installer']),0)
            self.assertFalse(target.exists())

    def test_unexpected_concurrent_edit_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ,{},clear=True):
            home=Path(directory);target=self.fixture(home,'stable');target.write_text('original')
            def install(command):target.write_text('independent edit');return 0
            with patch.object(launcher.subprocess,'call',side_effect=install):
                with self.assertRaisesRegex(RuntimeError,'Unexpected launcher edit'):
                    launcher.run(home,'stable',['installer'])
            self.assertEqual(target.read_text(),'independent edit')
            saved=list((home/'.local/state/tjikup/zed-launchers').glob('*/'+target.name))
            self.assertEqual(len(saved),1);self.assertEqual(saved[0].read_text(),'original')

    def test_symlink_is_rejected_before_installer(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ,{},clear=True):
            home=Path(directory);target=self.fixture(home,'stable');target.symlink_to(home/'other')
            with patch.object(launcher.subprocess,'call') as install:
                with self.assertRaisesRegex(RuntimeError,'regular file'):launcher.run(home,'stable',['installer'])
                install.assert_not_called()

    def test_launchers_belong_to_zed_group(self):
        import json
        for filename in ['files.json','portable-files.json']:
            entries=json.loads((ROOT/'native/home'/filename).read_text())
            launchers=[entry for entry in entries if entry['path'].endswith(('/dev.zed.Zed.desktop','/dev.zed.Zed-Preview.desktop'))]
            if filename == 'files.json':
                self.assertTrue(launchers)
            self.assertTrue(all(entry['group']=='zed' for entry in launchers))

    def test_unmanaged_portable_launchers_are_left_to_upstream(self):
        import json
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory);base=repo/'native/home';base.mkdir(parents=True)
            (base/'files-device.json').write_text(json.dumps({'entries_files':['portable-files.json']}))
            (base/'portable-files.json').write_text('[]')
            with patch.object(launcher.socket,'gethostname',return_value='new-machine'):
                self.assertFalse(launcher.is_managed(repo,repo/'user','stable'))
            (base/'files-fi.json').write_text(json.dumps({'entries_files':['files.json']}))
            (base/'files.json').write_text(json.dumps([{'path':'{{ user.home }}/.local/share/applications/dev.zed.Zed.desktop'}]))
            with patch.object(launcher.socket,'gethostname',return_value='fi'):
                self.assertTrue(launcher.is_managed(repo,repo/'user','stable'))
