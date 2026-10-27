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

    def test_all_25_icons_and_aliases_are_valid(self):
        mapping = json.loads((ROOT / 'scripts/icons/apps.json').read_text())
        self.assertEqual(len(mapping), 25)
        for key in mapping:
            icon = ROOT / f'home/dot_local/share/icons/rose-punk/scalable/apps/{key}.svg'
            tree = ET.parse(icon)
            self.assertEqual(tree.getroot().get('viewBox'), '0 0 64 64')
            alias = ROOT / f'home/dot_local/share/icons/hicolor/scalable/apps/symlink_rose-punk-{key}.svg'
            self.assertEqual(alias.read_text().strip(), f'../../../rose-punk/scalable/apps/{key}.svg')

    def test_both_directions_cover_every_app_and_themed_alias(self):
        mapping = json.loads((ROOT / 'scripts/icons/apps.json').read_text())
        aliases = json.loads((ROOT / 'scripts/icons/theme-aliases.json').read_text())
        for theme in ('rose-punk', 'rose-punk-illustrated'):
            folder = ROOT / 'home/dot_local/share/icons' / theme / 'scalable/apps'
            for key in mapping:
                ET.parse(folder / f'{key}.svg')
                self.assertEqual((folder / f'symlink_rose-punk-{key}.svg').read_text().strip(), key + '.svg')
            for alias, key in aliases.items():
                if alias != key:
                    self.assertEqual((folder / f'symlink_{alias}.svg').read_text().strip(), key + '.svg')
        for key in mapping:
            base = ROOT / 'home/dot_local/share/icons'
            self.assertNotEqual((base / f'rose-punk/scalable/apps/{key}.svg').read_bytes(),
                                (base / f'rose-punk-illustrated/scalable/apps/{key}.svg').read_bytes())
