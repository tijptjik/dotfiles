"""The shared teal replacement must reach local artwork and generated ramps."""
import json
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class IconPaletteTests(unittest.TestCase):
    def test_replacement_reaches_every_generated_icon(self):
        config = json.loads((ROOT / 'scripts/icons/palette.json').read_text())
        catalog = json.loads((ROOT / 'scripts/icons/catalog.json').read_text())
        folder = ROOT / 'native/home/files/.local/share/icons/rose-punk/scalable/apps'
        for key in catalog:
            colors = {c.lower() for c in re.findall(r'#[0-9a-fA-F]{6}', (folder / f'{key}.svg').read_text())}
            with self.subTest(icon=key):
                self.assertFalse(colors.intersection(config['paint_overrides']))

    def test_music_icons_keep_jade_surfaces_and_ivory_functional_marks(self):
        import colorsys
        folder = ROOT / 'native/home/files/.local/share/icons/rose-punk/scalable/apps'
        # The accepted music revisions use related jade ramps, with different
        # shading for Spotify's badge and Audio Player's physical object.
        for key, shape in [('spotify', 'circle'), ('audio-player', 'path')]:
            root = ET.parse(folder / f'{key}.svg')
            fill = root.find(f'.//{{*}}{shape}').get('fill')
            stops = root.findall(f".//*[@id='{fill[5:-1]}']/{{*}}stop")
            self.assertTrue(stops)
            for stop in stops:
                color = stop.get('stop-color')
                rgb = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
                hue, _, _ = colorsys.rgb_to_hsv(*rgb)
                self.assertTrue(0.35 < hue < 0.55, (key, color))
            marks = [n for n in root.iter() if n.get('fill') == '#fff0da'
                     or n.get('stroke') == '#fff0da']
            self.assertTrue(marks, key)
