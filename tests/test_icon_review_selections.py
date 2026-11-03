"""Keep accepted decisions intact across source, desktop and service builds."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'scripts/icons'
sys.path.insert(0, str(HERE))
import fullset
import homepage


class ReviewedSelectionTests(unittest.TestCase):
    def test_every_selection_reaches_all_outputs_without_repainting(self):
        selection = json.loads((HERE / 'review-selections.json').read_text())
        icons, _ = fullset.render()
        services = homepage.render()
        catalog = json.loads((HERE / 'catalog.json').read_text())
        self.assertEqual(len(selection['icons']), 167)
        self.assertEqual(len({i['id'] for i in selection['icons']}), 167)
        for item in selection['icons']:
            key = item['id']
            with self.subTest(icon=key):
                expected = (ROOT / item['output']).read_bytes()
                self.assertEqual(hashlib.sha256(expected).hexdigest(), item['suggested_sha256'])
                for outputs in [icons, services]:
                    if key + '.svg' in outputs:
                        self.assertEqual(outputs[key + '.svg'], expected)
                if key in catalog and catalog[key]['mode'] == 'reviewed-svg':
                    self.assertEqual((HERE / catalog[key]['geometry']).read_bytes(), expected)

    def test_protected_originals_and_system_identity(self):
        selection = json.loads((HERE / 'review-selections.json').read_text())
        byid = {i['id']: i for i in selection['icons']}
        protected = {
            'profilarr', 'audiobookshelf', 'grimmory', 'system-monitor',
            'problem-reporting', 'hyprvoice', 'gum', 'gpu-screen-recorder',
            'unpackerr', 'simplescreenrecorder', 'bookmarks', 'scrutiny',
            'obsidian', 'chrome', 'signal', 'tinty',
            'camera', 'bartjik', 'codex', 'codex-lb', 'kitty', 'zed', 'zed-preview',
            'zed-nightly',
        }
        self.assertEqual({k for k, i in byid.items()
                          if i['before_sha256'] == i['suggested_sha256']}, protected)
        # The requested Craft finish changes paint and edges, not the retained
        # animal silhouettes. Keep the original paths as geometry references.
        for key in ('vectorcraft', 'lightcraft', 'effectcraft', 'designcraft',
                    'texturecraft', 'soundcraft', 'filmcraft'):
            with self.subTest(craft_geometry=key):
                def paths(path):
                    return Counter(n.get('d') for n in ET.parse(path).getroot().iter()
                                   if n.tag.endswith('}path'))
                original = paths(HERE / 'local' / f'{key}.svg')
                revised = paths(HERE / 'local/reviewed' / f'{key}.svg')
                self.assertFalse(original - revised)
        self.assertNotIn('configuration', selection['groups'])
        self.assertTrue({'chezmoi', 'chezetc'} <= set(selection['groups']['system-hardware']))
        self.assertFalse({'chezmoi', 'chezetc', 'dotjik', 'systjik'} &
                         set(selection['groups']['tjik-family']))
        catalog = json.loads((HERE / 'catalog.json').read_text())
        aliases = json.loads((HERE / 'theme-aliases.json').read_text())
        for old, new in [('dotjik', 'chezmoi'), ('systjik', 'chezetc')]:
            self.assertNotIn(old, catalog)
            self.assertEqual(catalog[new]['family'], 'configuration')
            self.assertEqual(aliases[old], new)
            self.assertEqual(aliases['rose-punk-' + old], new)
