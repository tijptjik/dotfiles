"""Framed generation must use the exact signed-off frameless originals."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('framed_icons', ROOT / 'scripts/icons/framed.py')
framed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(framed)


class FramedIconTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.primary = self.root / 'primary'
        self.primary.mkdir()
        self.catalog = {'sample': {}}
        self.source = (ROOT / 'home/dot_local/share/icons/rose-punk/scalable/apps/firefox.svg').read_bytes()
        (self.primary / 'sample.svg').write_bytes(self.source)
        (self.primary / 'symlink_org.example.App.svg').write_text('sample.svg\n')
        self.approval = self.root / 'approved.json'
        self.dest, self.assets = self.root / 'theme', self.root / 'assets'

    def approve(self):
        self.approval.write_text(json.dumps(framed.inventory(self.primary, self.catalog)))

    def build(self):
        return framed.build(self.primary, self.catalog, self.approval, self.dest, self.assets)

    def test_missing_or_stale_signoff_cannot_publish(self):
        with self.assertRaisesRegex(ValueError, 'sign-off is pending'):
            self.build()
        self.assertFalse(self.dest.exists())
        self.assertFalse(self.assets.exists())
        self.approve()
        (self.primary / 'sample.svg').write_bytes(self.source + b'\n')
        with self.assertRaisesRegex(ValueError, 'changed since sign-off'):
            self.build()
        self.assertFalse(self.dest.exists())

    def test_alias_and_catalog_changes_invalidate_signoff(self):
        self.approve()
        (self.primary / 'symlink_extra.svg').write_text('sample.svg\n')
        with self.assertRaisesRegex(ValueError, 'changed since sign-off'):
            self.build()
        self.approve()
        (self.primary / 'second.svg').write_bytes(self.source)
        self.catalog['second'] = {}
        with self.assertRaisesRegex(ValueError, 'changed since sign-off'):
            self.build()

    def test_geometry_and_paints_are_preserved_under_one_transform(self):
        root = ET.fromstring(framed.frame(self.source))
        group = root.find('./{*}g[@id="framed-artwork"]')
        self.assertEqual(group.get('transform'), framed.TRANSFORM)
        self.assertEqual(root.find('./{*}rect').attrib, framed.TILE)
        expected = list(ET.fromstring(self.source))
        self.assertEqual([ET.tostring(n) for n in group], [ET.tostring(n) for n in expected])
        self.assertEqual(sum(n.get('id') == 'tile' for n in root.iter()), 1)
        with self.assertRaisesRegex(ValueError, 'frameless original'):
            framed.frame(ET.tostring(root))

    def test_complete_theme_download_hashes_and_repeatable_build(self):
        self.approve()
        manifest = self.build()
        apps = self.dest / 'scalable/apps'
        self.assertEqual((self.primary / 'sample.svg').read_bytes(), self.source)
        self.assertIn('Name=Rose Punk Framed\n', (self.dest / 'index.theme').read_text())
        self.assertNotIn('Inherits=rose-punk', (self.dest / 'index.theme').read_text())
        self.assertEqual((apps / 'symlink_org.example.App.svg').read_text(), 'sample.svg\n')
        output = (apps / 'sample.svg').read_bytes()
        self.assertEqual(manifest['icons']['sample']['frameless_sha256'], framed.digest(self.source))
        self.assertEqual(manifest['icons']['sample']['framed_sha256'], framed.digest(output))
        archive_path = self.assets / 'rose-punk-framed.zip'
        before = archive_path.read_bytes()
        with zipfile.ZipFile(archive_path) as archive:
            self.assertEqual(len(archive.namelist()), 3)
            self.assertEqual(archive.read('rose-punk-framed/scalable/apps/org.example.App.svg'), output)
        # A repeated build removes retired generated files and is byte-identical.
        (apps / 'retired.svg').write_text('retired')
        self.assertEqual(self.build(), manifest)
        self.assertFalse((apps / 'retired.svg').exists())
        self.assertEqual(archive_path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
