"""Keep shell and launcher companions visible in the primary icon previews."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/icons'))
import gallery
import icon_data


class IconGalleryTests(unittest.TestCase):
    def inputs(self, root):
        folder = root / 'scripts/icons'
        folder.mkdir(parents=True)
        (folder / 'catalog.json').write_text(json.dumps({
            'app': {'name': 'Application', 'installed': True}}))
        (folder / 'command-icons.json').write_text(json.dumps({
            'fish': {'name': 'Fish shell', 'role': 'shell'},
            'runtjik-refresh': {'name': 'Refresh index', 'role': 'control'}}))
        return folder

    def test_companions_are_discoverable_without_becoming_installed_apps(self):
        with tempfile.TemporaryDirectory() as temporary:
            catalog = icon_data.gallery_catalog(self.inputs(Path(temporary)))
            self.assertEqual(set(catalog), {'app', 'fish', 'runtjik-refresh'})
            self.assertFalse(catalog['fish']['installed'])
            self.assertEqual(catalog['fish']['availability'], 'Shell')
            self.assertEqual(catalog['runtjik-refresh']['availability'], 'Launcher control')

    def test_conflicting_original_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = self.inputs(Path(temporary))
            (folder / 'command-icons.json').write_text(json.dumps({'app': {'name': 'Other'}}))
            with self.assertRaisesRegex(ValueError, 'Duplicate gallery icon IDs: app'):
                icon_data.gallery_catalog(folder)

    def test_gallery_html_and_contact_sheet_include_shells_and_controls(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.inputs(root)
            theme = root / 'home/dot_local/share/icons/rose-punk/scalable/apps'
            theme.mkdir(parents=True)
            for key in ('app', 'fish', 'runtjik-refresh'):
                (theme / (key + '.svg')).write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
            with patch.object(gallery, 'ROOT', root), patch.object(gallery, 'DEST', theme):
                gallery.main()
            docs = root / '.local/icon-reviews/docs'
            html = (docs / 'rose-punk-icons-gallery.html').read_text()
            sheet = (docs / 'rose-punk-icons-catalog-1.svg').read_text()
            for name in ('Fish shell', 'Refresh index'):
                self.assertIn(name, html)
                self.assertIn(name, sheet)
            self.assertIn('/fish.svg', html)
            self.assertIn('data-kind="Shell"', html)
            self.assertIn('<option>Shell</option>', html)
