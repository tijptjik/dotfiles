"""Compatibility bridge tests; selection is tested against the native owner."""
import json, os, socket, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import device_policy as policy

class DevicePolicyTests(unittest.TestCase):
    def enrolled(self, directory, role='desktop', subscriptions=None):
        path = Path(directory) / 'tjikup/device.json'
        path.parent.mkdir()
        path.write_text(json.dumps({'version':1, 'hostname':socket.gethostname(),
            'role':role, 'subscriptions':subscriptions or []}))
        return path

    def test_selected_dependencies(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'XDG_CONFIG_HOME':directory}):
            self.enrolled(directory, 'laptop', ['system:zed'])
            context = policy.context(ROOT)
            self.assertTrue(context['is_laptop'])
            self.assertIn('system:zed', context['subscriptions'])
            self.assertNotIn('home:collie', context['subscriptions'])

    def test_aliases_do_not_rewrite_profile(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'XDG_CONFIG_HOME':directory}):
            path = self.enrolled(directory, subscriptions=['home:font-migration','home:rose-punk-icons'])
            before = path.read_bytes()
            context = policy.context(ROOT)
            self.assertIn('home:fonts', context['subscriptions'])
            self.assertIn('home:icons', context['subscriptions'])
            self.assertNotIn('home:font-migration', context['subscriptions'])
            self.assertEqual(path.read_bytes(), before)

    def test_unknown_subscription_fails(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'XDG_CONFIG_HOME':directory}):
            self.enrolled(directory, subscriptions=['missing:recipe'])
            with self.assertRaisesRegex(RuntimeError, 'unknown recipe subscription'):
                policy.context(ROOT)

    def test_existing_hostname_requires_enrollment(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'XDG_CONFIG_HOME':directory}):
            with self.assertRaisesRegex(RuntimeError, 'Enroll'):
                policy.context(ROOT)

    def test_foreign_profile_rejected(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'XDG_CONFIG_HOME':directory}):
            path = self.enrolled(directory)
            value = json.loads(path.read_text()); value['hostname'] = 'foreign-device'
            path.write_text(json.dumps(value))
            with self.assertRaisesRegex(RuntimeError, 'belongs to'):
                policy.context(ROOT)

    def test_configure_leaves_old_configuration_untouched(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'XDG_CONFIG_HOME':directory}):
            self.enrolled(directory)
            old = Path(directory) / 'chezmoi/chezmoi.toml'; old.parent.mkdir(); old.write_text('untouched')
            policy.configure(ROOT)
            self.assertEqual(old.read_text(), 'untouched')
