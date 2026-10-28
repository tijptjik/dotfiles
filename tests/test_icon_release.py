"""Release integrity checks run against temporary outputs without live dotfiles."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import io

ROOT = Path(__file__).resolve().parents[1]
# These CLI modules share the same explicit import root when executed normally.
sys.path.insert(0, str(ROOT / 'scripts/icons'))
import icon_data
import release


class IconReleaseTests(unittest.TestCase):
    def test_rebuild_prunes_retired_svgs_and_check_detects_missing_changed_extra(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / 'retired.svg').write_bytes(b'old')
            outputs = {'app.svg': b'<svg/>', 'symlink_app-alias.svg': b'app.svg\n'}
            icon_data.write_tree(folder, outputs)
            self.assertEqual(icon_data.differences(folder, outputs), [])
            self.assertFalse((folder / 'retired.svg').exists())
            (folder / 'app.svg').write_bytes(b'drift')
            (folder / 'symlink_app-alias.svg').unlink()
            (folder / 'unexpected.svg').write_bytes(b'extra')
            self.assertEqual(icon_data.differences(folder, outputs), [
                'missing: symlink_app-alias.svg', 'stale: unexpected.svg', 'changed: app.svg'])

    def test_aliases_are_derived_without_reusing_generated_output(self):
        catalog = {'app': {'icon_names': ['app.svg', '/absolute/icon.png'],
                           'desktop_ids': ['org.example.App.desktop']}}
        with patch.object(icon_data, 'read_json', return_value={'old-app': 'app'}):
            self.assertEqual(icon_data.aliases_for(catalog), {
                'app': 'app', 'old-app': 'app', 'org.example.App': 'app'})
        with patch.object(icon_data, 'read_json', return_value={}):
            self.assertNotIn('old-app', icon_data.aliases_for(catalog))

    def test_alias_collision_and_missing_original_fail_before_writing(self):
        catalog = {'app': {'icon_names': ['shared'], 'desktop_ids': []},
                   'other': {'icon_names': ['shared'], 'desktop_ids': []}}
        with self.assertRaisesRegex(ValueError, 'Conflicting alias'):
            icon_data.aliases_for(catalog)
        with patch.object(icon_data, 'read_json', return_value={'alias': 'missing'}):
            with self.assertRaisesRegex(ValueError, 'missing icon'):
                icon_data.aliases_for({})

    def test_source_hash_and_path_validation(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(icon_data, 'HERE', Path(temporary)):
            source = Path(temporary) / 'source.svg'
            source.write_bytes(b'<svg/>')
            with self.assertRaisesRegex(ValueError, 'provenance'):
                icon_data.verify_source('source.svg', 'invalid')
            with self.assertRaisesRegex(ValueError, 'invalid icon source'):
                icon_data.source_file('../outside.svg')

    def test_failed_render_does_not_change_generated_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'app.svg'
            output.write_bytes(b'original')
            with patch('sys.argv', ['release.py', 'build']), \
                    patch.object(release, 'generated_outputs', side_effect=ValueError('bad source')):
                with self.assertRaises(SystemExit) as result:
                    release.main()
            self.assertEqual(result.exception.code, 1)
            self.assertEqual(output.read_bytes(), b'original')

    def test_installable_zip_is_repeatable_and_materializes_aliases(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(release, 'PRIMARY', Path(temporary)):
            (Path(temporary) / 'index.theme').write_bytes(b'[Icon Theme]\nName=Rose Punk\n')
            icons = {'app.svg': b'<svg/>', 'symlink_alias.svg': b'app.svg\n'}
            files = release.theme_files(icons)
            first = release.theme_zip(files)
            self.assertEqual(first, release.theme_zip(dict(reversed(list(files.items())))))
            with zipfile.ZipFile(io.BytesIO(first)) as archive:
                self.assertEqual(archive.read('rose-punk/scalable/apps/alias.svg'), b'<svg/>')
                self.assertFalse(any('symlink_' in name for name in archive.namelist()))
                self.assertEqual(archive.namelist(), sorted(archive.namelist()))
                self.assertTrue(all(info.date_time == (2026, 1, 1, 0, 0, 0) for info in archive.infolist()))

    def test_stale_output_blocks_packaging_before_artifacts_are_written(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(release, 'ROOT', root):
                with self.assertRaisesRegex(ValueError, 'stale'):
                    release.package({root / 'icons': {'app.svg': b'<svg/>'}}, {}, root / 'release')
            self.assertFalse((root / 'release').exists())

    def test_service_downloads_include_helpers_without_replacing_desktop_art(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(release, 'PRIMARY', Path(temporary)):
            (Path(temporary) / 'index.theme').write_bytes(b'[Icon Theme]\nName=Rose Punk\n')
            desktop = {'shared.svg': b'desktop', 'symlink_alias.svg': b'shared.svg\n'}
            services = {'shared.svg': b'service variant', 'homepage.svg': b'house',
                        'profilarr.svg': b'parent', 'profilarr-parser.svg': b'parent'}
            files = release.theme_files(desktop, services)
            with zipfile.ZipFile(io.BytesIO(release.theme_zip(files))) as archive:
                self.assertEqual(archive.read('rose-punk/scalable/apps/homepage.svg'), b'house')
                self.assertEqual(archive.read('rose-punk/scalable/apps/profilarr-parser.svg'), b'parent')
                self.assertEqual(archive.read('rose-punk/scalable/apps/shared.svg'), b'desktop')
                self.assertEqual(archive.read('rose-punk/scalable/apps/alias.svg'), b'desktop')


if __name__ == '__main__':
    unittest.main()
