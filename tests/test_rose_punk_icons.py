"""Validate the icon manifest and preserve desktop launch behavior when applying icons."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('icon_install', ROOT / 'scripts/icons/install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class RosePunkIconsTests(unittest.TestCase):
    def test_coverage_honors_hidden_user_overrides(self):
        spec = importlib.util.spec_from_file_location('icon_audit', ROOT / 'scripts/icons/audit.py')
        audit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(audit)
        with tempfile.TemporaryDirectory() as directory:
            user, system = Path(directory) / 'user', Path(directory) / 'system'
            user.mkdir(); system.mkdir()
            (system / 'monitor.desktop').write_text('[Desktop Entry]\nType=Application\nName=Java Monitor\n')
            (user / 'monitor.desktop').write_text('[Desktop Entry]\nType=Application\nName=Java Monitor\nHidden=true\n')
            (system / 'editor.desktop').write_text('[Desktop Entry]\nType=Application\nName=System Editor\n')
            (user / 'editor.desktop').write_text('[Desktop Entry]\nType=Application\nName=User Editor\n')
            self.assertEqual(audit.inventory([user, system]), {'editor.desktop': 'User Editor'})

    def test_theme_settings_preserve_other_sections_and_qt_geometry(self):
        text = '[SettingsWindow]\ngeometry=@ByteArray(\\x1\\xd9)\n\n[Appearance]\nstyle=Fusion\nicon_theme=old\n'
        updated = installer.with_ini_setting(text, 'Appearance', 'icon_theme', 'rose-punk')
        self.assertEqual(updated, text.replace('icon_theme=old', 'icon_theme=rose-punk'))
        self.assertEqual(installer.with_ini_setting(updated, 'Appearance', 'icon_theme', 'rose-punk'), updated)
        self.assertEqual(installer.with_ini_setting('[Settings]\nother=1\n[Next]\nx=2\n',
                        'Settings', 'gtk-icon-theme-name', 'rose-punk'),
                        '[Settings]\nother=1\ngtk-icon-theme-name=rose-punk\n[Next]\nx=2\n')

    def test_theme_selection_updates_desktop_gtk_and_qt_without_rewriting_preferences(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(installer.subprocess, 'check_output', return_value="'Neuwaita'\n"), \
                patch.object(installer.subprocess, 'run') as run:
            config = Path(directory)
            (config / 'gtk-3.0').mkdir()
            (config / 'gtk-3.0/settings.ini').write_text('[Settings]\ngtk-application-prefer-dark-theme=0\n')
            self.assertTrue(installer.select_theme(config, 'rose-punk', True))
            self.assertIn('gtk-application-prefer-dark-theme=0', (config / 'gtk-3.0/settings.ini').read_text())
            self.assertIn('icon_theme=rose-punk', (config / 'qt6ct/qt6ct.conf').read_text())
            run.assert_called_once_with(['gsettings', 'set', 'org.gnome.desktop.interface',
                                        'icon-theme', 'rose-punk'], check=True)
            self.assertFalse(installer.select_theme(config, 'rose-punk', False))

    def test_theme_fingerprint_detects_changed_artwork_without_desktop_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / 'app.svg').write_text('<svg/>')
            before = installer.icon_fingerprint(folder)
            (folder / 'app.svg').write_text('<svg><circle/></svg>')
            self.assertNotEqual(before, installer.icon_fingerprint(folder))
            after = installer.icon_fingerprint(folder)
            (folder / 'icon-theme.cache').write_bytes(b'cache-only-change')
            self.assertEqual(after, installer.icon_fingerprint(folder))

    def test_codex_uses_the_wavy_identity_with_filled_faces(self):
        mapping = json.loads((ROOT / 'scripts/icons/apps.json').read_text())
        self.assertIn('codex-desktop.desktop', mapping['codex'])
        self.assertNotIn('codex-desktop.desktop', mapping['chatgpt'])
        expected = ET.parse(ROOT / 'scripts/icons/upstream/codex-lobe.svg').find('{*}path').get('d')
        for key in ('codex', 'codex-lb'):
            rendered = ET.parse(ROOT / f'home/dot_local/share/icons/rose-punk/scalable/apps/{key}.svg')
            mark = rendered.find('.//{*}path')
            self.assertEqual(mark.get('d'), expected)
            self.assertNotEqual(mark.get('fill'), 'none')
            self.assertIsNone(mark.get('stroke'))

    def test_selected_outline_references_keep_geometry_and_effective_weight(self):
        folder = ROOT / 'home/dot_local/share/icons/rose-punk/scalable/apps'
        for key, source in (('hyprvoice', 'references/lucide-audio-lines'),
                            ('oo7', 'references/tabler-fingerprint')):
            expected = ET.parse(ROOT / f'scripts/icons/{source}.svg').getroot()
            rendered = ET.parse(folder / f'{key}.svg').getroot()
            nested = rendered.find('.//{*}svg')
            self.assertEqual(nested.get('width'), '48')
            self.assertEqual(nested.get('stroke-width'), '2')
            self.assertEqual([n.get('d') for n in expected.iter() if n.tag.endswith('}path')],
                             [n.get('d') for n in nested.iter() if n.tag.endswith('}path')])

    def test_contact_sheets_preserve_namespaces_and_unique_ids(self):
        for path in (ROOT / '.local/icon-reviews/docs').glob('rose-punk-icons-catalog-*.svg'):
            with self.subTest(sheet=path.name):
                root = ET.parse(path).getroot()
                ids = [n.get('id') for n in root.iter() if n.get('id')]
                self.assertEqual(len(ids), len(set(ids)))
                self.assertTrue(any(n.tag.endswith('}svg') for n in list(root.iter())[1:]))

    def test_tjikup_reuses_notjik_frame_with_up_chevron(self):
        folder = ROOT / 'scripts/icons/local'
        notjik = ET.parse(folder / 'notjik.svg').getroot()
        tjikup = ET.parse(folder / 'tjikup.svg').getroot()
        self.assertEqual(notjik.find('{*}rect').attrib, tjikup.find('{*}rect').attrib)
        self.assertIsNone(tjikup.find('{*}circle'))
        self.assertEqual(tjikup.find('{*}path').get('d'), 'm24 36 8-8 8 8')

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
        self.assertFalse({k for k, c in catalog.items() if not c['installed']})
        folder = ROOT / 'home/dot_local/share/icons/rose-punk/scalable/apps'
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

    def test_retained_brand_contours_use_authentic_vector_geometry(self):
        catalog = json.loads((ROOT / 'scripts/icons/catalog.json').read_text())
        for key in ('gimp',):
            original_mark = ET.parse(ROOT / f'scripts/icons/upstream/{key}.svg').find('.//{*}path').get('d')
            local = ET.parse(ROOT / 'scripts/icons' / catalog[key]['geometry'])
            self.assertIn(original_mark, [node.get('d') for node in local.findall('.//{*}path')])
        fox = ET.parse(ROOT / 'scripts/icons/upstream/firefoxbrowser.svg').find('.//{*}path').get('d')
        rendered = ET.parse(ROOT / 'home/dot_local/share/icons/rose-punk/scalable/apps/firefox.svg')
        self.assertIn(fox, [node.get('d') for node in rendered.findall('.//{*}path')])
        original = ET.parse(ROOT / 'scripts/icons/upstream/mullvad.svg').getroot()
        refined = ET.parse(ROOT / 'scripts/icons/local/mullvad.svg').getroot()
        original_path = original.find('.//{*}path').get('d')
        mole_only = 'M13.651 3.363' + original_path.split('zm1.651 3.363', 1)[1]
        # Only the jagged neck edge is softened; hat and face stay authentic.
        new_path = refined.find('.//{*}path').get('d')
        self.assertEqual(new_path.split('l3.553 1.4')[0], mole_only.split('l3.553 1.4')[0])
        self.assertEqual(new_path.split('-2.667 3.419')[1], mole_only.split('-2.667 3.419')[1])
        self.assertLess(len(new_path), len(mole_only))

    def test_zed_channels_have_distinct_desktop_mappings_and_colors(self):
        mapping = json.loads((ROOT / 'scripts/icons/apps.json').read_text())
        colors = set()
        geometry = []
        for key, desktop in [('zed', 'dev.zed.Zed.desktop'),
                             ('zed-preview', 'dev.zed.Zed-Preview.desktop'),
                             ('zed-nightly', 'dev.zed.Zed-Nightly.desktop')]:
            self.assertIn(desktop, mapping[key])
            self.assertEqual([k for k, ids in mapping.items() if desktop in ids], [key])
            mark = ET.parse(ROOT / f'scripts/icons/local/{key}.svg').find('.//{*}path')
            colors.add(mark.get('fill'))
            geometry.append(mark.get('d'))
        self.assertEqual(len(colors), 3)
        self.assertEqual(len(set(geometry)), 1)
        preview = ET.parse(ROOT / 'scripts/icons/local/zed-preview.svg').find('.//{*}path')
        self.assertEqual(preview.get('fill'), '#5685ff')
        nightly = ET.parse(ROOT / 'scripts/icons/local/zed-nightly.svg').find('.//{*}path')
        self.assertEqual(nightly.get('fill'), '#f6c177')

    def test_retired_icons_are_not_reintroduced_by_aliases(self):
        retired = {'audacity', 'inkscape', 'libreoffice', 'edge', 'teams', 'notion', 'slack', 'vscode',
                   'rustdesk', 'metadata-cleaner', 'kimi-ai', 'jetbrains-toolbox', 'java-monitor',
                   'homeworld-remastered-collection', 'tramoramic-experience', 'witcher-2',
                   'datagrip', 'beekeeper-studio', 'azahar'}
        retired.update(json.loads((ROOT / 'scripts/icons/retired.json').read_text()))
        for filename in ('catalog.json', 'apps.json'):
            data = json.loads((ROOT / 'scripts/icons' / filename).read_text())
            self.assertFalse(retired.intersection(data))
        aliases = json.loads((ROOT / 'scripts/icons/theme-aliases.json').read_text())
        self.assertFalse(retired.intersection(aliases.values()))

    def test_vendored_geometry_has_provenance(self):
        import hashlib
        catalog = json.loads((ROOT / 'scripts/icons/catalog.json').read_text())
        provenance = json.loads((ROOT / 'scripts/icons/provenance.json').read_text())
        for key, entry in catalog.items():
            self.assertIn(key, provenance)
            if 'geometry' in entry:
                actual = hashlib.sha256((ROOT / 'scripts/icons' / entry['geometry']).read_bytes()).hexdigest()
                self.assertEqual(actual, provenance[key]['sha256'])
