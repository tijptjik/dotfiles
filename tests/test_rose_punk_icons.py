"""Validate the icon manifest and preserve desktop launch behavior when applying icons."""
import importlib.util
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('icon_install', ROOT / 'scripts/icons/install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class RosePunkIconsTests(unittest.TestCase):
    def test_main_icon_replacement_preserves_actions_and_launch_command(self):
        text = '[Desktop Entry]\nName=Example\nExec=example --safe %U\nIcon=/old.png\n\n[Desktop Action New]\nIcon=other\nExec=example --new\n'
        updated = installer.with_icon(text, 'rose-punk-example')
        self.assertEqual(updated, text.replace('Icon=/old.png', 'Icon=rose-punk-example'))
        self.assertEqual(installer.with_icon(updated, 'rose-punk-example'), updated)

    def test_missing_icon_inserted_before_actions(self):
        text = '[Desktop Entry]\nExec=example\n[Desktop Action New]\nIcon=other\n'
        self.assertEqual(installer.with_icon(text, 'new'), '[Desktop Entry]\nExec=example\nIcon=new\n[Desktop Action New]\nIcon=other\n')

    def test_full_catalog_and_aliases_resolve(self):
        mapping = json.loads((ROOT / 'scripts/icons/apps.json').read_text())
        catalog = json.loads((ROOT / 'scripts/icons/catalog.json').read_text())
        aliases = json.loads((ROOT / 'scripts/icons/theme-aliases.json').read_text())
        self.assertEqual(set(mapping), set(catalog))
        self.assertEqual(sum(not c['installed'] for c in catalog.values()), 10)
        folder = ROOT / 'home/dot_local/share/icons/rose-punk-illustrated/scalable/apps'
        for key in catalog:
            with self.subTest(icon=key):
                root = ET.parse(folder / f'{key}.svg').getroot()
                self.assertEqual(root.get('viewBox'), '0 0 64 64')
                self.assertFalse(any(n.tag.split('}')[-1] == 'image' for n in root.iter()))
                self.assertEqual((folder / f'symlink_rose-punk-{key}.svg').read_text().strip(), key + '.svg')
                for desktop in catalog[key]['desktop_ids']:
                    self.assertIn(desktop, mapping[key])
        for alias, key in aliases.items():
            self.assertFalse(any(c.isspace() for c in alias), "GTK cache rejects icon names with spaces")
            if alias not in catalog:
                self.assertEqual((folder / f'symlink_{alias}.svg').read_text().strip(), key + '.svg')

    def test_five_redraws_use_authentic_vector_geometry(self):
        catalog = json.loads((ROOT / 'scripts/icons/catalog.json').read_text())
        for key in ('firefox','mullvad','thunderbird','gimp','transmission'):
            self.assertEqual(catalog[key]['mode'], 'brand')
            self.assertTrue((ROOT / 'scripts/icons' / catalog[key]['geometry']).is_file())

    def test_vendored_geometry_has_provenance(self):
        import hashlib
        catalog = json.loads((ROOT / 'scripts/icons/catalog.json').read_text())
        provenance = json.loads((ROOT / 'scripts/icons/provenance.json').read_text())
        for key, entry in catalog.items():
            self.assertIn(key, provenance)
            if 'geometry' in entry:
                actual = hashlib.sha256((ROOT / 'scripts/icons' / entry['geometry']).read_bytes()).hexdigest()
                self.assertEqual(actual, provenance[key]['sha256'])
