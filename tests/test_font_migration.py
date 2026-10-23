import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('font_migration', Path(__file__).resolve().parents[1] / 'home/.chezmoitemplates/consolidate-fonts.py')
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)

class FontMigrationTests(unittest.TestCase):
    def test_union_rollback_and_idempotence(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            old = home / '.fonts'; old.mkdir()
            target = home / '.local/share/fonts'; target.mkdir(parents=True)
            (old/'a.ttf').write_bytes(b'a')
            (target/'b.otf').write_bytes(b'b')
            migration.consolidate(home, True)
            self.assertTrue(old.is_symlink())
            self.assertEqual((old/'b.otf').read_bytes(), b'b')
            self.assertEqual((target/'a.ttf').read_bytes(), b'a')
            self.assertEqual(len(list((home/'.local/state/font-migration').glob('*/fonts/a.ttf'))), 1)
            self.assertIn('already', migration.consolidate(home, True))

    def test_conflicts_abort_before_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            old = home/'.fonts'; old.mkdir()
            target = home/'.local/share/fonts'; target.mkdir(parents=True)
            (old/'a.ttf').write_bytes(b'legacy')
            (target/'a.ttf').write_bytes(b'new')
            with self.assertRaisesRegex(RuntimeError, 'conflicts'):
                migration.consolidate(home, True)
            self.assertFalse(old.is_symlink())
            self.assertEqual((target/'a.ttf').read_bytes(), b'new')
