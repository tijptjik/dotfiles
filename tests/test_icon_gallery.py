"""Keep application and shell previews separate from launcher controls."""
import json
import re
import runpy
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/icons'))
import gallery
import icon_data


class IconGalleryTests(unittest.TestCase):
    def test_workflow_preview_retains_camera_linked_gradients(self):
        scope_ids = runpy.run_path(str(ROOT / 'scripts/icons/workflow-review.py'))['scope_ids']
        camera = ET.parse(ROOT / 'home/dot_local/share/icons/rose-punk/scalable/apps/camera.svg').getroot()
        scope_ids(camera, 'camera-96-')
        ids = {n.get('id') for n in camera.iter() if n.get('id')}
        references = []
        for node in camera.iter():
            for attr, value in node.attrib.items():
                references.extend(re.findall(r'url\(#([^)]*)\)', value))
                if attr.endswith('}href') and value.startswith('#'):
                    references.append(value[1:])
                    self.assertTrue(value.startswith('#camera-96-'))
        self.assertTrue(references)
        self.assertFalse(set(references) - ids)

    def inputs(self, root):
        folder = root / 'scripts/icons'
        folder.mkdir(parents=True)
        (folder / 'catalog.json').write_text(json.dumps({
            'app': {'name': 'Application', 'installed': True},
            'runtjik': {'name': 'Runtjik', 'installed': False}}))
        (folder / 'command-icons.json').write_text(json.dumps({
            'fish': {'name': 'Fish shell', 'role': 'shell'},
            'runtjik-refresh': {'name': 'Refresh index', 'role': 'control'}}))
        return folder

    def test_shells_are_discoverable_but_launcher_controls_are_excluded(self):
        with tempfile.TemporaryDirectory() as temporary:
            catalog = icon_data.gallery_catalog(self.inputs(Path(temporary)))
            self.assertEqual(set(catalog), {'app', 'fish', 'runtjik'})
            self.assertFalse(catalog['fish']['installed'])
            self.assertEqual(catalog['fish']['availability'], 'Shell')

    def test_conflicting_original_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = self.inputs(Path(temporary))
            (folder / 'command-icons.json').write_text(json.dumps({'app': {'name': 'Other'}}))
            with self.assertRaisesRegex(ValueError, 'Duplicate gallery icon IDs: app'):
                icon_data.gallery_catalog(folder)

    def test_gallery_html_and_contact_sheet_exclude_controls(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.inputs(root)
            theme = root / 'home/dot_local/share/icons/rose-punk/scalable/apps'
            theme.mkdir(parents=True)
            for key in ('app', 'fish', 'runtjik', 'runtjik-refresh'):
                (theme / (key + '.svg')).write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
            with patch.object(gallery, 'ROOT', root), patch.object(gallery, 'DEST', theme):
                gallery.main()
            docs = root / '.local/icon-reviews/docs'
            html = (docs / 'rose-punk-icons-gallery.html').read_text()
            sheet = (docs / 'rose-punk-icons-catalog-1.svg').read_text()
            for name in ('Fish shell', 'Runtjik'):
                self.assertIn(name, html)
                self.assertIn(name, sheet)
            for output in (html, sheet):
                self.assertNotIn('Refresh index', output)
                self.assertNotIn('runtjik-refresh', output)
            self.assertIn('/fish.svg', html)
            self.assertIn('data-kind="Shell"', html)
            self.assertIn('<option>Shell</option>', html)
