"""Theme setup tests use synthetic icons and never modify the live desktop."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('theme_install', ROOT / 'scripts/icons/install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class ThemeSetupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.data, self.state, self.vendor = [self.root / name for name in ('data', 'state', 'vendor')]
        for path in (self.data / 'applications', self.state, self.vendor):
            path.mkdir(parents=True)

    def desktop(self, icon='vendor', command='app %U'):
        return f'[Desktop Entry]\nType=Application\nName=App\nExec={command}\nIcon={icon}\n'

    def records(self, original, installed):
        (self.state / 'desktop-overrides.json').write_text(json.dumps({
            'app.desktop': {'original': original, 'installed': installed}}))

    def test_restores_generated_overlay_and_preserves_vendor(self):
        vendor = self.desktop()
        (self.vendor / 'app.desktop').write_text(vendor)
        target = self.data / 'applications/app.desktop'
        target.write_text(self.desktop('rose-punk-app'))
        self.records(None, target.read_text())
        self.assertEqual(installer.restore_overrides(self.data, self.state, {}, [self.vendor]), (1, []))
        self.assertFalse(target.exists())
        self.assertEqual((self.vendor / 'app.desktop').read_text(), vendor)
        self.assertEqual(installer.restore_overrides(self.data, self.state, {}, [self.vendor]), (0, []))

    def test_edited_launch_command_survives_icon_restoration(self):
        installed = self.desktop('rose-punk-app')
        target = self.data / 'applications/app.desktop'
        target.write_text(self.desktop('rose-punk-app', 'app --custom %U'))
        self.records(self.desktop(), installed)
        self.assertEqual(installer.restore_overrides(self.data, self.state, {}, []), (1, []))
        self.assertEqual(target.read_text(), self.desktop('vendor', 'app --custom %U'))

    def test_managed_native_launcher_is_not_deleted_for_old_overlay_record(self):
        target = self.data / 'applications/app.desktop'
        target.write_text(self.desktop('rose-punk-app', 'native %U'))
        self.records(None, self.desktop('rose-punk-app'))
        self.assertEqual(installer.restore_overrides(self.data, self.state, {'app.desktop': 'app'}, []), (1, []))
        self.assertEqual(target.read_text(), self.desktop('app', 'native %U'))

    def test_unknown_custom_override_is_preserved_and_reported(self):
        target = self.data / 'applications/app.desktop'
        target.write_text(self.desktop('rose-punk-app', 'custom'))
        self.records(None, self.desktop('rose-punk-app'))
        before = target.read_bytes()
        self.assertEqual(installer.restore_overrides(self.data, self.state, {}, []), (0, ['app.desktop']))
        self.assertEqual(target.read_bytes(), before)
        self.assertIn('app.desktop', json.loads((self.state / 'desktop-overrides.json').read_text()))

    def test_linked_launcher_does_not_rewrite_vendor_file(self):
        vendor = self.vendor / 'app.desktop'
        vendor.write_text(self.desktop('rose-punk-app'))
        target = self.data / 'applications/app.desktop'
        target.symlink_to(vendor)
        installer.restore_overrides(self.data, self.state, {'app.desktop': 'app'}, [self.vendor])
        self.assertEqual(installer.main_icon(target.read_text()), 'app')
        self.assertEqual(installer.main_icon(vendor.read_text()), 'rose-punk-app')
        self.assertFalse(target.is_symlink())

    def test_cleanup_only_removes_our_fallback_links(self):
        folder = self.data / 'icons/hicolor/scalable/apps'
        folder.mkdir(parents=True)
        for name in ('app', 'rose-punk-app'):
            (folder / f'{name}.svg').symlink_to('../../../rose-punk-illustrated/scalable/apps/app.svg')
        (folder / 'vendor.svg').write_text('vendor original')
        (folder / 'other.svg').symlink_to('../../../other/scalable/apps/other.svg')
        self.assertEqual(installer.remove_theme_fallbacks(self.data), 2)
        self.assertEqual((folder / 'vendor.svg').read_text(), 'vendor original')
        self.assertTrue((folder / 'other.svg').is_symlink())
        self.assertEqual(installer.remove_theme_fallbacks(self.data), 0)

    def test_install_does_not_select_a_theme(self):
        with patch.dict(os.environ, {'XDG_DATA_HOME': str(self.data), 'XDG_STATE_HOME': str(self.state)}), \
                patch('sys.argv', ['install.py']), patch.object(installer, 'select_theme') as select, \
                patch.object(installer, 'refresh_cache'):
            installer.main()
        select.assert_not_called()

    def test_renames_only_legacy_theme_settings_and_preserves_formatting(self):
        config = self.root / 'config'
        gtk = config / 'gtk-3.0/settings.ini'
        gtk.parent.mkdir(parents=True)
        before = '# personal settings\n[Settings]\ngtk-icon-theme-name=rose-punk-illustrated\nother=1\n'
        gtk.write_text(before)
        qt = config / 'qt6ct/qt6ct.conf'
        qt.parent.mkdir(parents=True)
        qt.write_text('[Appearance]\nicon_theme=Adwaita\n')
        with patch.object(installer.subprocess, 'check_output', return_value="'rose-punk-illustrated'\n"), \
                patch.object(installer.subprocess, 'run') as command:
            self.assertTrue(installer.migrate_legacy_theme(config, True))
        self.assertEqual(gtk.read_text(), before.replace('rose-punk-illustrated', 'rose-punk'))
        self.assertEqual(qt.read_text(), '[Appearance]\nicon_theme=Adwaita\n')
        self.assertFalse((config / 'gtk-4.0/settings.ini').exists())
        command.assert_called_once_with(
            ['gsettings', 'set', 'org.gnome.desktop.interface', 'icon-theme', 'rose-punk'], check=True)
        self.assertFalse(installer.migrate_legacy_theme(config, False))

    def test_migration_preserves_another_desktop_theme(self):
        with patch.object(installer.subprocess, 'check_output', return_value="'Neuwaita'\n"), \
                patch.object(installer.subprocess, 'run') as command:
            self.assertFalse(installer.migrate_legacy_theme(self.root / 'absent', True))
        command.assert_not_called()

    def test_install_waits_for_primary_theme_before_migrating_old_id(self):
        metadata = self.data / 'icons/rose-punk/index.theme'
        metadata.parent.mkdir(parents=True)
        for name, hidden, ready in (('Rose Punk (Outline archive)', True, False),
                                    ('Rose Punk', False, True)):
            with self.subTest(name=name):
                metadata.write_text(f'[Icon Theme]\nName={name}\nHidden={str(hidden).lower()}\n')
                with patch.dict(os.environ, {'XDG_DATA_HOME': str(self.data), 'XDG_STATE_HOME': str(self.state)}), \
                        patch('sys.argv', ['install.py']), patch.object(installer, 'migrate_legacy_theme') as migrate, \
                        patch.object(installer, 'refresh_cache'):
                    installer.main()
                self.assertEqual(migrate.called, ready)

    @unittest.skipUnless(shutil.which('chezmoi'), 'Chezmoi required')
    def test_managed_gtk_templates_preserve_another_theme(self):
        config = self.root / 'config.json'
        config.write_text('{}')
        for version in ('gtk-3.0', 'gtk-4.0'):
            settings = self.root / '.config' / version / 'settings.ini'
            settings.parent.mkdir(parents=True)
            settings.write_text('[Settings]\ngtk-icon-theme-name=Adwaita\n')
            result = subprocess.check_output([
                'chezmoi', '--config', str(config), '--source', str(self.root),
                '--persistent-state', str(self.root / 'state.db'), '--override-data',
                json.dumps({'chezmoi': {'homeDir': str(self.root)}}), 'execute-template', '-f',
                str(ROOT / f'home/dot_config/{version}/settings.ini.tmpl'),
            ], text=True)
            self.assertIn('gtk-icon-theme-name=Adwaita', result)
            self.assertNotIn('rose-punk', result)

    def test_named_theme_and_managed_launchers_do_not_force_artwork(self):
        metadata = (ROOT / 'home/dot_local/share/icons/rose-punk/index.theme').read_text()
        self.assertIn('\nName=Rose Punk\n', metadata)
        self.assertNotIn('icon-theme=', (ROOT / 'home/dot_config/dconf/interface.conf').read_text())
        for path in (ROOT / 'home/dot_local/share/applications').glob('*'):
            if path.is_file():
                self.assertFalse(installer.main_icon(path.read_text()).startswith('rose-punk-'), path.name)

        telegram = ROOT / 'home/dot_local/share/applications/executable_org.telegram.desktop'
        self.assertEqual(installer.main_icon(telegram.read_text()), 'org.telegram.desktop')
