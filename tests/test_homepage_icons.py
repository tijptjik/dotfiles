"""Keep Homepage icon routing, provenance and desktop reuse consistent."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'scripts/icons'
DEST = ROOT / 'home/dockers/homepage/images/rose-punk'
spec = importlib.util.spec_from_file_location('homepage_icons', HERE / 'homepage.py')
homepage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(homepage)


class HomepageIconTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((HERE / 'homepage.json').read_text())

    def test_configuration_routes_to_complete_local_assets(self):
        config = '\n'.join((ROOT / 'home/dockers/homepage' / name).read_text()
                           for name in ('services.yaml', 'bookmarks.yaml'))
        paths = re.findall(r'^\s+icon:\s*(\S+)', config, flags=re.M)
        self.assertEqual(len(paths), 14)
        self.assertTrue(set(paths) <= {f'/images/rose-punk/{key}.svg' for key in self.manifest})
        self.assertEqual({p.name for p in DEST.glob('*.svg')}, set(homepage.render()))

    def test_generated_art_matches_sources_and_shared_desktop_icons(self):
        for key, entry in self.manifest.items():
            with self.subTest(icon=key):
                self.assertEqual((DEST / f'{key}.svg').read_text(), homepage.artwork(entry))
                self.assertEqual(hashlib.sha256((HERE / entry['geometry']).read_bytes()).hexdigest(), entry['sha256'])
                if 'theme_key' in entry:
                    self.assertEqual(entry['geometry'], f"local/{entry['theme_key']}.svg")
                else:
                    self.assertRegex(entry['reference_sha256'], r'^[a-f0-9]{64}$')
                if 'reference' in entry:
                    self.assertEqual(hashlib.sha256((HERE / entry['reference']).read_bytes()).hexdigest(),
                                     entry['reference_sha256'])

    def test_every_compose_service_has_an_explicit_source_and_runtime_sprite(self):
        inventory = json.loads((ROOT / 'scripts/fleet_update/docker-services.json').read_text())
        compose = (ROOT / 'home/dockers/docker-compose.yaml.tmpl').read_text()
        services = set(re.findall(r'^  ([a-z][a-z0-9-]*):\s*$', compose, re.M))
        self.assertEqual(services, set(inventory))
        sprites = json.loads((ROOT / 'scripts/fleet_update/icons32.json').read_text())['sprites']
        for name, entry in inventory.items():
            with self.subTest(service=name):
                self.assertIn(entry['icon'], self.manifest)
                self.assertTrue(entry['glyph'])
                self.assertIn(name, sprites)
                if entry['icon'] != name:
                    self.assertTrue(entry['reuse'])
                self.assertEqual((DEST / f'{name}.svg').read_bytes(),
                                 (DEST / (entry['icon'] + '.svg')).read_bytes())

    def test_changed_source_refuses_generation_before_writing_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.svg'
            source.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
            manifest = {'example': {'geometry': 'source.svg', 'sha256': '0' * 64}}
            (root / 'homepage.json').write_text(json.dumps(manifest))
            with patch.object(homepage, 'HERE', root), patch.object(homepage, 'DEST', root / 'output'):
                with self.assertRaisesRegex(ValueError, 'Changed source without provenance update'):
                    homepage.main()
            self.assertFalse((root / 'output').exists())


    def test_frameless_art_is_centered_and_clear_of_canvas_edges(self):
        for key in self.manifest:
            with self.subTest(icon=key):
                alpha = homepage.frameless.render((DEST / f'{key}.svg').read_text(), 256).getchannel('A')
                left, top, right, bottom = alpha.point(lambda a: 255 if a >= 8 else 0).getbbox()
                self.assertGreaterEqual(min(left, top), 12)
                self.assertLessEqual(max(right, bottom), 244)
                self.assertLessEqual(abs((left + right) / 2 - 128), 1)
                self.assertLessEqual(abs((top + bottom) / 2 - 128), 1)
                self.assertGreaterEqual(max(right - left, bottom - top), 198)
                self.assertLessEqual(max(right - left, bottom - top), 226)
                self.assertEqual(alpha.getpixel((0, 0)), 0)

    def test_homepage_vectors_are_self_contained_and_have_unique_paint_servers(self):
        for key in self.manifest:
            with self.subTest(icon=key):
                text = (DEST / f'{key}.svg').read_text()
                root = ET.fromstring(text)
                self.assertEqual(root.get('viewBox'), '0 0 64 64')
                ids = [n.get('id') for n in root.iter() if n.get('id')]
                self.assertEqual(len(ids), len(set(ids)))
                self.assertNotIn('tile', ids)
                self.assertIn('frameless-artwork', ids)
                self.assertFalse(set(re.findall(r'url\(#([^)]*)\)', text)) - set(ids))
                self.assertFalse(any(n.tag.rsplit('}', 1)[-1] in ('image', 'script', 'style') for n in root.iter()))
                for n in root.iter():
                    for attr, value in n.attrib.items():
                        if attr.rsplit('}', 1)[-1] == 'href':
                            self.assertTrue(value.startswith('#'))
                            self.assertIn(value[1:], ids)
