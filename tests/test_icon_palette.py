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
        folder = ROOT / 'home/dot_local/share/icons/rose-punk/scalable/apps'
        for key in catalog:
            colors = {c.lower() for c in re.findall(r'#[0-9a-fA-F]{6}', (folder / f'{key}.svg').read_text())}
            with self.subTest(icon=key):
                self.assertFalse(colors.intersection(config['paint_overrides']))
        # Local scanner paint must resolve before material shading.
        for key in ('document-scanner',):
            text = (folder / f'{key}.svg').read_text()
            self.assertIn(config['paint_overrides']['#31748f'], text)

    def test_spotify_and_audio_player_share_the_requested_mint_material(self):
        folder = ROOT / 'home/dot_local/share/icons/rose-punk/scalable/apps'
        spotify = ET.parse(folder / 'spotify.svg')
        audio = ET.parse(folder / 'audio-player.svg')
        badge = spotify.find('.//{*}circle')
        mark = spotify.find('.//{*}path')
        # User selected the lighter shared music palette; the former dark-jade
        # 3:1 requirement no longer describes the requested artwork.
        gradient = spotify.find(f".//*[@id='{badge.get('fill')[5:-1]}']")
        audio_gradient = audio.find(".//*[@id='mint-clean']")
        self.assertEqual([(n.get('offset', '0'), n.get('stop-color')) for n in gradient],
                         [(n.get('offset', '0'), n.get('stop-color')) for n in audio_gradient])
        self.assertEqual(mark.get('stroke'), '#fff5e9')
        self.assertGreaterEqual(float(mark.get('stroke-width')), 3)
