import json, os, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import device_policy as policy

class DevicePolicyTests(unittest.TestCase):
    def test_new_hostname_uses_role_and_selected_dependencies(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'XDG_CONFIG_HOME':directory}), patch('socket.gethostname',return_value='new-laptop'):
            p=Path(directory)/'tjikup/device.json';p.parent.mkdir();p.write_text(json.dumps({'version':1,'hostname':'new-laptop','role':'laptop','subscriptions':['system:zed']}))
            c=policy.context(ROOT)
            self.assertTrue(c['is_client']);self.assertTrue(c['is_laptop']);self.assertFalse(c['is_server'])
            self.assertIn('system:zed',c['subscriptions']);self.assertNotIn('home:collie',c['subscriptions'])
            self.assertNotIn('system:apps',c['subscriptions'])
    def test_unknown_host_without_profile_fails(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'XDG_CONFIG_HOME':directory}), patch('socket.gethostname',return_value='new-host'):
            with self.assertRaisesRegex(RuntimeError,'enroll'):policy.context(ROOT)
    def test_existing_devices_keep_legacy_roles(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'XDG_CONFIG_HOME':directory}):
            for host,role in policy.LEGACY.items():
                with patch('socket.gethostname',return_value=host):self.assertEqual(policy.context(Path('/tmp'))['role'],role)
    def test_new_server_never_inherits_si_storage(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'XDG_CONFIG_HOME':directory}), patch('socket.gethostname',return_value='new-server'):
            p=Path(directory)/'tjikup/device.json';p.parent.mkdir();p.write_text(json.dumps({'version':1,'hostname':'new-server','role':'server','subscriptions':['system:apps']}))
            with self.assertRaisesRegex(RuntimeError,'unavailable'):policy.context(ROOT)
    def test_configure_validates_without_touching_legacy_config(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'XDG_CONFIG_HOME':directory}), patch('socket.gethostname',return_value='fi'):
            p=Path(directory)/'chezmoi/chezmoi.toml';p.parent.mkdir();p.write_text('untouched')
            with patch('subprocess.run',side_effect=AssertionError('no external renderer')):
                policy.configure(ROOT)
            self.assertEqual(p.read_text(),'untouched')
            self.assertEqual(policy.context(ROOT)['home_source'],str(ROOT/'home'))


if __name__ == '__main__':
    unittest.main()
