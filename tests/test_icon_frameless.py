"""Validate the primary frameless set without modifying live dotfiles."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/icons'))
ASSETS = ROOT / '.local/icon-reviews/docs/assets/icon-frameless-review'
spec = importlib.util.spec_from_file_location('frameless', ROOT / 'scripts/icons/frameless-review.py')
frameless = importlib.util.module_from_spec(spec)
spec.loader.exec_module(frameless)


@unittest.skipUnless(ASSETS.is_dir(), 'Optional local review archive is absent')
class FramelessIconTests(unittest.TestCase):
    def test_complete_catalog_and_source_snapshot_hashes(self):
        catalog = frameless.gallery_catalog(ROOT / 'scripts/icons')
        manifest = json.loads((ASSETS / 'manifest.json').read_text())['icons']
        self.assertEqual(set(catalog), set(manifest))
        self.assertEqual(set(catalog), {p.stem for p in (ASSETS / 'frameless').glob('*.svg')})
        for key in catalog:
            with self.subTest(icon=key):
                historical = ASSETS / 'framed' / f'{key}.svg'
                source_hash = hashlib.sha256(historical.read_bytes()).hexdigest() if historical.is_file() else None
                self.assertEqual(source_hash, manifest[key]['source_sha256'])
                result = (ASSETS / 'frameless' / f'{key}.svg').read_bytes()
                primary = ROOT / 'native/home/files/.local/share/icons/rose-punk/scalable/apps' / f'{key}.svg'
                self.assertEqual(primary.read_bytes(), result)
                self.assertEqual(hashlib.sha256(result).hexdigest(), manifest[key]['frameless_sha256'])

    def test_identity_geometry_and_paints_survive_tile_removal(self):
        for path in (ASSETS / 'frameless').glob('*.svg'):
            with self.subTest(icon=path.stem):
                if not (ASSETS / 'framed' / path.name).is_file():
                    continue
                source = ET.parse(ASSETS / 'framed' / path.name).getroot()
                # Historical snapshots test the sizing operation, not the current
                # artwork: primary originals can continue to be refined.
                output, _ = frameless.normalize(ET.tostring(source, encoding='unicode'))
                result = ET.fromstring(output)
                group = result.find('./{*}g[@id="frameless-artwork"]')
                self.assertIsNotNone(group)
                self.assertNotIn('tile', [n.get('id') for n in result.iter()])
                # Compare the original flattened nodes/attributes, except the
                # common background and the single outer sizing transform.
                expected = [(n.tag, n.attrib, (n.text or '').strip())
                            for n in source.iter() if n.get('id') != 'tile']
                result.remove(group)
                result.extend(group)
                actual = [(n.tag, n.attrib, (n.text or '').strip()) for n in result.iter()]
                self.assertEqual(expected, actual)

    def test_rendered_art_is_centered_unclipped_and_transparent(self):
        try:
            import gi
            import cairo
            from PIL import Image
            gi.require_version('Rsvg', '2.0')
        except (ImportError, ValueError):
            self.skipTest('SVG rendering requires librsvg, pycairo and Pillow')
        for path in (ASSETS / 'frameless').glob('*.svg'):
            with self.subTest(icon=path.stem):
                alpha = frameless.render(path.read_text(), 256).getchannel('A')
                box = alpha.point(lambda a: 255 if a >= 8 else 0).getbbox()
                left, top, right, bottom = box
                self.assertGreaterEqual(min(left, top), 12)
                self.assertLessEqual(max(right, bottom), 244)
                self.assertLessEqual(abs((left + right) / 2 - 128), 1)
                self.assertLessEqual(abs((top + bottom) / 2 - 128), 1)
                self.assertGreaterEqual(max(right - left, bottom - top), 198)
                self.assertLessEqual(max(right - left, bottom - top), 226)
                self.assertEqual(alpha.getpixel((0, 0)), 0)

    def test_download_matches_reviewed_vectors(self):
        files = list((ASSETS / 'frameless').glob('*.svg'))
        with zipfile.ZipFile(ASSETS / 'rose-punk-frameless.zip') as archive:
            self.assertEqual(len(archive.namelist()), len(files))
            for path in files:
                self.assertEqual(archive.read(f'rose-punk-frameless/{path.name}'), path.read_bytes())


if __name__ == '__main__':
    unittest.main()
