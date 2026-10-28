import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('storage', ROOT/'etc/si-provision/storage.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
CONFIG = json.loads((ROOT/'etc/si-snapraid-maintenance/config.json').read_text())

class StorageTests(unittest.TestCase):
    def test_preserves_installer_and_unrelated_mounts(self):
        original = 'UUID=new-root / btrfs defaults 0 0\nUUID=new-efi /boot/efi vfat defaults 0 2\nserver:/share /srv nfs defaults 0 0\nUUID=dead /mnt/data/disk4 ext4 defaults 0 0\n'
        result = mod.render_fstab(original, CONFIG)
        self.assertIn('UUID=new-root / btrfs', result)
        self.assertIn('UUID=new-efi /boot/efi', result)
        self.assertIn('server:/share /srv', result)
        self.assertNotIn('UUID=dead', result)
        self.assertNotIn('/mnt/data/disk*', result)
        self.assertEqual(result, mod.render_fstab(result, CONFIG))
    def test_rejects_unknown_array(self):
        with self.assertRaises(ValueError):
            mod.render_fstab('UUID=other /mnt/data/disk99 ext4 defaults 0 0\n', CONFIG)
    def test_rejects_broken_block(self):
        with self.assertRaises(ValueError):
            mod.render_fstab(mod.BEGIN+'\n', CONFIG)
    def test_rejects_wrong_disk(self):
        with patch.object(mod, 'command', return_value='wrong ext4'):
            with self.assertRaises(RuntimeError):
                mod.check_mounts(CONFIG)
    def test_rejects_absent_pool(self):
        values = [v+' ext4' for v in CONFIG['mounts'].values()]+['ext4']
        with patch.object(mod, 'command', side_effect=values):
            with self.assertRaises(RuntimeError):
                mod.check_mounts(CONFIG)
    def test_expected_mounts(self):
        values = [v+' ext4' for v in CONFIG['mounts'].values()]+['fuse.mergerfs']
        with patch.object(mod, 'command', side_effect=values):
            mod.check_mounts(CONFIG)
    def test_docker_only_needs_its_data_disk(self):
        with patch.object(mod, 'command', return_value=CONFIG['mounts']['/mnt/data/disk22']+' ext4') as call:
            mod.check_mounts(CONFIG, True)
            self.assertEqual(call.call_count, 1)

if __name__ == '__main__':
    unittest.main()
