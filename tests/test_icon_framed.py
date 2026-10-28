"""Framed generation must use the exact signed-off frameless originals."""
import importlib.util
import json
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/icons'))
import icon_data
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
        self.source = (ROOT / 'native/home/files/.local/share/icons/rose-punk/scalable/apps/firefox.svg').read_bytes()
        (self.primary / 'sample.svg').write_bytes(self.source)
        (self.primary / 'symlink_org.example.App.svg').write_text('sample.svg\n')
        self.approval = self.root / 'approved.json'
        self.dest, self.assets = self.root / 'theme', self.root / 'assets'
        self.layout = self.root / 'layout.json'
        self.entry = {'scale': .8, 'offset': [0, -1], 'source_sha256': framed.digest(self.source)}
        self.layout.write_text(json.dumps({'schema': 1, 'icons': {'sample': self.entry}}))
        layout = patch.object(framed, 'LAYOUT', self.layout)
        layout.start()
        self.addCleanup(layout.stop)

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
        with self.assertRaisesRegex(ValueError, 'source changed'):
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
        self.layout.write_text(json.dumps({'schema': 1, 'icons': {'sample': self.entry, 'second': self.entry}}))
        with self.assertRaisesRegex(ValueError, 'changed since sign-off'):
            self.build()

    def test_native_framed_build_requires_policy_and_records_aliases(self):
        self.approve()
        sources = self.root / 'native/home/files'
        self.dest = sources / '.local/share/icons/rose-punk-framed'
        with patch.object(framed, 'ROOT', self.root), patch.object(icon_data, 'ROOT', self.root):
            sources.mkdir(parents=True)
            manifest = sources.parent / 'files.json'
            manifest.write_text('[]')
            with self.assertRaisesRegex(ValueError, 'Register native icon directory'):
                self.build()
            self.assertFalse(self.assets.exists())
            base = '{{ user.home }}/.local/share/icons/rose-punk-framed'
            manifest.write_text(json.dumps([
                {'path': base + '/scalable/apps', 'kind': 'directory', 'mode': '0755'},
                {'path': base + '/index.theme', 'kind': 'file', 'mode': '0644',
                 'source': 'files/.local/share/icons/rose-punk-framed/index.theme'}]))
            self.build()
            apps = self.dest / 'scalable/apps'
            self.assertEqual({p.name for p in apps.iterdir()}, {'sample.svg'})
            self.assertEqual(icon_data.native_aliases(apps), {'org.example.App.svg': 'sample.svg'})
            self.assertTrue((self.dest / 'index.theme').is_file())

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

    def test_layout_changes_invalidate_signoff_without_altering_originals(self):
        self.approve()
        changed = {**self.entry, 'scale': .72}
        self.layout.write_text(json.dumps({'schema': 1, 'icons': {'sample': changed}}))
        with self.assertRaisesRegex(ValueError, 'layouts changed since sign-off'):
            self.build()
        self.assertEqual((self.primary / 'sample.svg').read_bytes(), self.source)
        self.assertFalse(self.dest.exists())

    def test_aliases_receive_the_canonical_layout_and_reject_drift(self):
        policy = framed.load_layout()
        files = {'scalable/apps/sample.svg': self.source,
                 'scalable/apps/org.example.App.svg': self.source, 'NOTICE.txt': b'notice'}
        output = framed.frame_theme(files, policy, {'org.example.App.svg': 'sample'})
        self.assertEqual(output['scalable/apps/sample.svg'], output['scalable/apps/org.example.App.svg'])
        root = ET.fromstring(output['scalable/apps/sample.svg'])
        self.assertEqual(root.find('./{*}g[@id="framed-artwork"]').get('transform'), framed.transform(self.entry))
        self.assertEqual(output['NOTICE.txt'], b'notice')
        files['scalable/apps/org.example.App.svg'] += b'\n'
        with self.assertRaisesRegex(ValueError, 'source changed'):
            framed.frame_theme(files, policy, {'org.example.App.svg': 'sample'})

    def test_layout_validation_rejects_missing_keys_and_unsafe_numbers(self):
        with self.assertRaisesRegex(ValueError, 'inventory mismatch'):
            framed.load_layout(expected={'new-icon'})
        for change in ({'scale': float('nan')}, {'scale': -1}, {'offset': [0]}, {'offset': [0, 20]}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                framed.load_layout(data={'schema': 1, 'icons': {'sample': {**self.entry, **change}}})

    def test_layout_cannot_push_artwork_outside_the_rounded_tile(self):
        policy = framed.load_layout()
        policy['icons']['sample'].update(scale=1.1, offset=[8, 8])
        with self.assertRaisesRegex(ValueError, 'outside tile'):
            framed.frame_theme({'scalable/apps/sample.svg': self.source}, policy, {})


if __name__ == '__main__':
    unittest.main()
