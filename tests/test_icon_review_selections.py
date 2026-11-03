"""Keep accepted decisions intact across source, desktop and service builds."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

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

    def test_protected_originals_and_configuration_identity(self):
        selection = json.loads((HERE / 'review-selections.json').read_text())
        byid = {i['id']: i for i in selection['icons']}
        protected = {
            'profilarr', 'audiobookshelf', 'grimmory', 'system-monitor',
            'problem-reporting', 'hyprvoice', 'gum', 'gpu-screen-recorder',
            'unpackerr', 'simplescreenrecorder', 'bookmarks', 'scrutiny',
            'obsidian', 'chrome', 'signal', 'tinty', 'vectorcraft', 'lightcraft',
            'effectcraft', 'designcraft', 'texturecraft', 'soundcraft', 'filmcraft',
            'camera', 'bartjik', 'codex', 'codex-lb', 'kitty', 'zed', 'zed-preview',
            'zed-nightly',
        }
        self.assertEqual({k for k, i in byid.items()
                          if i['before_sha256'] == i['suggested_sha256']}, protected)
        self.assertEqual(set(selection['groups']['configuration']), {'chezmoi', 'chezetc'})
        self.assertFalse({'chezmoi', 'chezetc', 'dotjik', 'systjik'} &
                         set(selection['groups']['tjik-family']))
        catalog = json.loads((HERE / 'catalog.json').read_text())
        aliases = json.loads((HERE / 'theme-aliases.json').read_text())
        for old, new in [('dotjik', 'chezmoi'), ('systjik', 'chezetc')]:
            self.assertNotIn(old, catalog)
            self.assertEqual(catalog[new]['family'], 'configuration')
            self.assertEqual(aliases[old], new)
            self.assertEqual(aliases['rose-punk-' + old], new)
