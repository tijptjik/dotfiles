"""Essential pigments must remain visible on light and dark icon surfaces."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('contrast_render', ROOT / 'scripts/icons/frameless.py')
frameless = importlib.util.module_from_spec(spec)
spec.loader.exec_module(frameless)


def luminance(rgb):
    channels = [value / 255 for value in rgb]
    return sum((value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4) * weight
               for value, weight in zip(channels, (.2126, .7152, .0722)))


class IconContrastTests(unittest.TestCase):
    def test_mole_body_and_steam_linkage_contrast_on_light_and_dark_surfaces(self):
        import xml.etree.ElementTree as ET

        folder = ROOT / 'home/dot_local/share/icons/rose-punk/scalable/apps'
        surfaces = ('#eceaf0', '#f0ebe5', '#ffffff', '#26233a', '#191724')
        for key in ('mullvad', 'steam'):
            root = ET.parse(folder / f'{key}.svg')
            # The first path is the exposed body/linkage. Ivory and amber
            # details use their own dark edges rather than a muted pigment.
            fill = root.find('.//{*}path').get('fill')
            colors = ([stop.get('stop-color') for stop in
                       root.findall(f".//*[@id='{fill[5:-1]}']/{{*}}stop")]
                      if fill.startswith('url(#') else [fill])
            self.assertTrue(colors, key)
            for color in colors:
                pigment = luminance(tuple(int(color[i:i + 2], 16) for i in (1, 3, 5)))
                for surface in surfaces:
                    background = luminance(tuple(int(surface[i:i + 2], 16) for i in (1, 3, 5)))
                    low, high = sorted((pigment, background))
                    with self.subTest(icon=key, pigment=color, surface=surface):
                        self.assertGreaterEqual((high + .05) / (low + .05), 3)

    def test_revised_marks_have_three_to_one_pigment_contrast_on_both_surfaces(self):
        surfaces = {
            'gallery light': (236, 234, 240), 'warm light': (240, 235, 229),
            'white': (255, 255, 255), 'plum': (38, 35, 58), 'dark': (25, 23, 36),
        }
        for key in ('signal', 'nginx'):
            folder = 'home/dot_local/share/icons/rose-punk/scalable/apps'
            image = frameless.render((ROOT / folder / f'{key}.svg').read_text(), 128)
            # Evaluate rendered ramps as well as flat fills. Edge antialiasing
            # intentionally blends into the surface and is not pigment contrast.
            pigments = {pixel[:3] for _, pixel in image.getcolors(image.width * image.height)
                        if pixel[3] == 255}
            self.assertTrue(pigments, key)
            for name, surface in surfaces.items():
                background = luminance(surface)
                ratios = []
                for rgb in pigments:
                    low, high = sorted((luminance(rgb), background))
                    ratios.append((high + .05) / (low + .05))
                with self.subTest(icon=key, surface=name):
                    self.assertGreaterEqual(min(ratios), 3)

    def test_bright_marks_contrast_with_their_own_dark_fills(self):
        import xml.etree.ElementTree as ET

        folder = ROOT / 'home/dot_local/share/icons/rose-punk/scalable/apps'
        for key in ('zed', 'zed-nightly', 'zed-preview', 'zen'):
            root = ET.parse(folder / f'{key}.svg')
            backing = root.find(f".//*[@id='{'zen-fill' if key == 'zen' else 'zed-fill'}']")
            self.assertIsNotNone(backing, key)
            background = luminance(tuple(int(backing.get('fill')[i:i + 2], 16) for i in (1, 3, 5)))
            self.assertLess(background, .04)
            pigments = []
            for shape in root.iter():
                if shape.tag.rsplit('}', 1)[-1] not in ('path', 'circle'):
                    continue
                # Zen's outer circle also supplies its dark backing.
                for attribute in ('fill', 'stroke'):
                    value = shape.get(attribute, 'none')
                    if shape is backing and attribute == 'fill':
                        continue
                    if value.startswith('url(#'):
                        paints = [stop.get('stop-color') for stop in
                                  root.findall(f".//*[@id='{value[5:-1]}']/{{*}}stop")]
                    else:
                        paints = [value] if value.startswith('#') else []
                    pigments.extend(paints)
            self.assertTrue(pigments, key)
            for color in pigments:
                foreground = luminance(tuple(int(color[i:i + 2], 16) for i in (1, 3, 5)))
                with self.subTest(icon=key, pigment=color):
                    self.assertGreaterEqual((foreground + .05) / (background + .05), 3)
