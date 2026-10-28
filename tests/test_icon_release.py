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
    def native_fixture(self, root):
        folder = root / 'native/home/files/dockers/homepage/images/rose-punk'
        folder.mkdir(parents=True)
        parent = {'path': '{{ user.home }}/dockers/homepage/images/rose-punk',
                  'kind': 'directory', 'mode': '0755', 'when': 'hostname == "si"'}
        unrelated = {'path': '{{ user.home }}/unrelated', 'kind': 'absent'}
        manifest = root / 'native/home/files.json'
        manifest.write_text(json.dumps([parent, unrelated]))
        return folder, manifest, parent, unrelated

    def test_native_sources_aliases_conditions_retirement_and_release_receipt(self):
        with tempfile.TemporaryDirectory() as temporary, \
                patch.object(icon_data, 'ROOT', Path(temporary)):
            folder, manifest, parent, unrelated = self.native_fixture(Path(temporary))
            outputs = {'app.svg': b'<svg/>', 'symlink_alias.svg': b'app.svg\n'}
            icon_data.write_tree(folder, outputs)
            self.assertEqual(icon_data.differences(folder, outputs), [])
            self.assertEqual({p.name for p in folder.iterdir()}, {'app.svg'})
            self.assertEqual(icon_data.native_aliases(folder), {'alias.svg': 'app.svg'})
            entries = json.loads(manifest.read_text())
            self.assertEqual(entries[:2], [parent, unrelated])
            self.assertTrue(all(e['when'] == parent['when'] for e in entries[2:]))
            self.assertEqual(icon_data.generated_files(folder, outputs), {
                folder / 'app.svg': b'<svg/>', manifest: manifest.read_bytes()})
            old_manifest = (manifest.read_bytes(), manifest.stat().st_mtime_ns)
            icon_data.write_tree(folder, outputs)
            self.assertEqual((manifest.read_bytes(), manifest.stat().st_mtime_ns), old_manifest)
            icon_data.write_tree(folder, {'new.svg': b'new'})
            self.assertFalse((folder / 'app.svg').exists())
            self.assertEqual(icon_data.differences(folder, {'new.svg': b'new'}), [])
            retired = [e for e in json.loads(manifest.read_text()) if e['path'].endswith(('/app.svg', '/alias.svg'))]
            self.assertEqual(len(retired), 2)
            self.assertTrue(all(e['kind'] == 'absent' and e['when'] == parent['when'] for e in retired))

    def test_native_check_detects_alias_and_file_ownership_drift(self):
        with tempfile.TemporaryDirectory() as temporary, \
                patch.object(icon_data, 'ROOT', Path(temporary)):
            folder, manifest, _, _ = self.native_fixture(Path(temporary))
            outputs = {'app.svg': b'app', 'symlink_alias.svg': b'app.svg\n'}
            icon_data.write_tree(folder, outputs)
            entries = json.loads(manifest.read_text())
            entries[-1]['target'] = 'wrong.svg'
            manifest.write_text(json.dumps(entries))
            self.assertIn('manifest changed or missing: alias.svg', icon_data.differences(folder, outputs))
            entries = [entry for entry in entries if not entry['path'].endswith('/app.svg')]
            manifest.write_text(json.dumps(entries))
            self.assertIn('manifest changed or missing: app.svg', icon_data.differences(folder, outputs))

    def test_partial_native_producer_preserves_other_icons_and_metadata(self):
        with tempfile.TemporaryDirectory() as temporary, \
                patch.object(icon_data, 'ROOT', Path(temporary)):
            folder, manifest, _, _ = self.native_fixture(Path(temporary))
            icon_data.write_tree(folder, {'app.svg': b'app', 'control.svg': b'control'})
            entries = json.loads(manifest.read_text())
            entries[-1].update(mode='0600', uid=123)
            manifest.write_text(json.dumps(entries))
            outputs = {'control.svg': b'updated', 'symlink_control-alias.svg': b'control.svg\n'}
            (folder / 'symlink_control-alias.svg').write_bytes(b'control.svg\n')
            icon_data.write_tree(folder, outputs, prune=False)
            self.assertEqual((folder / 'app.svg').read_bytes(), b'app')
            self.assertFalse((folder / 'symlink_control-alias.svg').exists())
            entries = json.loads(manifest.read_text())
            self.assertEqual(entries[-2]['mode'], '0600')
            self.assertEqual(entries[-2]['uid'], 123)
            self.assertEqual(icon_data.differences(folder, {**outputs, 'app.svg': b'app'}), [])

    def test_native_validation_precedes_writes(self):
        with tempfile.TemporaryDirectory() as temporary, \
                patch.object(icon_data, 'ROOT', Path(temporary)):
            folder, manifest, _, _ = self.native_fixture(Path(temporary))
            with self.assertRaisesRegex(ValueError, 'Register native icon directory'):
                icon_data.write_tree(folder.parent / 'unregistered', {'app.svg': b'app'})
            self.assertFalse((folder.parent / 'unregistered').exists())
            with self.assertRaisesRegex(ValueError, 'no generated original'):
                icon_data.write_tree(folder, {'app.svg': b'app', 'symlink_alias.svg': b'unknown.svg\n'})
            self.assertEqual(list(folder.iterdir()), [])
            icon_data.write_tree(folder, {'app.svg': b'app'})
            entries = json.loads(manifest.read_text())
            entries[-1]['when'] = 'hostname == "fi"'
            manifest.write_text(json.dumps(entries))
            with self.assertRaisesRegex(ValueError, 'host condition'):
                icon_data.write_tree(folder, {'app.svg': b'changed'})
            self.assertEqual((folder / 'app.svg').read_bytes(), b'app')

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
