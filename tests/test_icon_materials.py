"""Protect SVG geometry, paint-server resolution, and the fixed camera reference."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
THEME = ROOT / 'home/dot_local/share/icons/rose-punk/scalable/apps'
spec = importlib.util.spec_from_file_location('icon_materials', ROOT / 'scripts/icons/materials.py')
materials = importlib.util.module_from_spec(spec)
spec.loader.exec_module(materials)


class IconMaterialTests(unittest.TestCase):
    @unittest.skipUnless((ROOT / '.local/icon-reviews/docs/assets/icon-material-review/manifest.json').is_file(), 'Optional local review archive is absent')
    def test_camera_artwork_is_the_optically_sized_frozen_reference(self):
        spec = importlib.util.spec_from_file_location('camera_sizing', ROOT / 'scripts/icons/frameless.py')
        sizing = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sizing)
        frozen = (ROOT / '.local/icon-reviews/docs/assets/icon-material-review/before/camera.svg').read_text()
        self.assertEqual((THEME / 'camera.svg').read_text(), sizing.normalize(frozen)[0])

    def test_shading_preserves_tile_paths_and_nested_stroke_coordinates(self):
        source = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
        <rect id="tile" width="58" height="58" fill="#26233a" stroke="#555169"/>
        <svg viewBox="0 0 24 24" width="48" height="48" x="8" y="8" stroke="#9ccfd8" fill="none">
        <path d="M12 4v16" stroke-width="2"/></svg></svg>'''
        before = ET.fromstring(source)
        after = ET.fromstring(materials.finish(source, 'sample'))
        self.assertEqual(before.find('{*}rect').attrib, after.find('{*}rect').attrib)
        self.assertEqual(before.find('.//{*}path').attrib, after.find('.//{*}path').attrib)
        nested = after.find('{*}svg')
        gradient = nested.find('{*}defs/{*}linearGradient')
        self.assertEqual(gradient.get('gradientUnits'), 'userSpaceOnUse')
        self.assertEqual(float(gradient.get('y2')), 24)
        self.assertEqual(nested.get('stroke'), f"url(#{gradient.get('id')})")

    def test_catalog_has_no_duplicate_or_missing_paint_servers(self):
        catalog = json.loads((ROOT / 'scripts/icons/catalog.json').read_text())
        for key in catalog:
            text = (THEME / f'{key}.svg').read_text()
            root = ET.fromstring(text)
            ids = [n.get('id') for n in root.iter() if n.get('id')]
            with self.subTest(icon=key):
                self.assertEqual(len(ids), len(set(ids)))
                self.assertFalse(set(re.findall(r'url\(#([^)]*)\)', text)) - set(ids))
                self.assertFalse(any(n.tag.rsplit('}', 1)[-1] in ('image', 'script') for n in root.iter()))

    @unittest.skipUnless((ROOT / '.local/icon-reviews/docs/assets/icon-material-review/manifest.json').is_file(), 'Optional local review archive is absent')
    def test_review_hashes_match_generated_art_and_frozen_before(self):
        manifest = json.loads((ROOT / '.local/icon-reviews/docs/assets/icon-material-review/manifest.json').read_text())
        catalog = json.loads((ROOT / 'scripts/icons/catalog.json').read_text())
        self.assertEqual(set(manifest), set(catalog))
        for key, entry in manifest.items():
            states = [('after', THEME)]
            if entry['before_folder'] is None:
                self.assertEqual(catalog[key].get('introduced_batch'), catalog[key]['review_batch'])
                self.assertIsNone(entry['before_sha256'])
                self.assertEqual(entry['treatment'], 'New identity')
            else:
                states.append(('before', ROOT / '.local/icon-reviews/docs/assets/icon-material-review' / entry['before_folder']))
            for state, folder in states:
                with self.subTest(icon=key, state=state):
                    self.assertEqual(hashlib.sha256((folder / f'{key}.svg').read_bytes()).hexdigest(), entry[f'{state}_sha256'])

    @unittest.skipUnless((ROOT / '.local/icon-reviews/docs/assets/icon-material-review/manifest.json').is_file(), 'Optional local review archive is absent')
    def test_retired_apps_are_absent_from_generated_theme_and_active_reviews(self):
        retired = json.loads((ROOT / 'scripts/icons/retired.json').read_text())
        reviews = [(ROOT / '.local/icon-reviews/docs' / name).read_text() for name in
                   ('rose-punk-material-review.html', 'rose-punk-icons-gallery.html', 'rose-punk-color-review.html')]
        for key in retired:
            with self.subTest(icon=key):
                self.assertFalse((THEME / f'{key}.svg').exists())
                self.assertFalse((THEME / f'symlink_rose-punk-{key}.svg').exists())
                for html in reviews:
                    self.assertNotIn(f'/{key}.svg', html)

    def test_clean_material_sources_do_not_get_generic_surface_shading(self):
        for key in ('bluetooth-adapters', 'bluetooth-manager', 'fonts', 'characters', 'audio-player', 'disks'):
            root = ET.parse(THEME / f'{key}.svg')
            group = root.find('.//*[@data-material="authored"]')
            self.assertIsNotNone(group)
            self.assertNotIn('url(#material-', ET.tostring(group, encoding='unicode'))
