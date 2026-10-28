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
    def test_configure_keeps_private_custom_config(self):
        import tomllib
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'XDG_CONFIG_HOME':directory}), patch('socket.gethostname',return_value='fi'):
            root=ROOT;policy.configure(root)
            p=Path(directory)/'chezmoi/chezmoi.toml';c=tomllib.loads(p.read_text());self.assertTrue(c['data']['isDesktop']);self.assertEqual(p.stat().st_mode & 0o777,0o600)
            self.assertNotIn('autoPush = true',p.read_text())
            p.write_text(p.read_text() + '\n[edit]\ncommand = "editor --wait"\n[data.custom]\nwhen = 2026-10-29T12:34:56Z\nvalues = [1, 2]\n')
            with patch('socket.gethostname', return_value='li'):
                policy.configure(root)
            updated = tomllib.loads(p.read_text())
            self.assertEqual(updated['edit']['command'], 'editor --wait')
            self.assertEqual(updated['data']['custom']['values'], [1, 2])
            self.assertEqual(updated['data']['custom']['when'].year, 2026)
            self.assertTrue(updated['data']['isLaptop'])
            self.assertFalse(updated['data']['isDesktop'])


if __name__ == '__main__':
    unittest.main()
