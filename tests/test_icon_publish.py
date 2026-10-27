"""Release publication contracts without network or live site changes."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/icons'))
import publish
import release


class IconPublishTests(unittest.TestCase):
    def snapshot(self, root):
        snapshot = root / '0.1.0'
        snapshot.mkdir()
        artifacts = {'rose-punk.zip': b'primary', 'rose-punk-framed.zip': b'framed', 'gallery.json': b'[]\n'}
        for name, data in artifacts.items():
            (snapshot / name).write_bytes(data)
        (snapshot / 'release.json').write_bytes(publish.encoded({
            'version': '0.1.0', 'artifacts': {name: release.sha256(data) for name, data in artifacts.items()}}))
        return snapshot

    def site(self, root):
        site = root / 'site'
        (site / 'src/lib/content').mkdir(parents=True)
        (site / 'wrangler.jsonc').write_text('{}')
        (site / 'src/lib/content/rose-punk.ts').write_text('export const rosePunkResources: ThemeResource[] = [\n]')
        return site

    def test_rejects_version_path_traversal(self):
        for value in ('../x', '/tmp/x', 'v1', '01.2.3', '1.2.3/other'):
            with self.assertRaises(ValueError):
                publish.validate_version(value)
        publish.validate_version('0.1.0-rc.1')

    def test_registration_is_repeatable_and_preserves_previous_versions(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot, site = self.snapshot(root), self.site(root)
            publish.register(snapshot, site)
            publish.register(snapshot, site)
            registry = json.loads((site / 'public/rose-punk-releases/registry.json').read_text())
            self.assertEqual(registry['latest'], '0.1.0')
            self.assertEqual(len(registry['releases']), 1)
            self.assertEqual((site / 'src/lib/content/rose-punk-icons.json').read_bytes(), b'[]\n')
            second = root / '0.2.0'
            import shutil
            shutil.copytree(snapshot, second)
            manifest = json.loads((second / 'release.json').read_text())
            manifest['version'] = '0.2.0'
            (second / 'release.json').write_bytes(publish.encoded(manifest))
            publish.register(second, site)
            registry = json.loads((site / 'public/rose-punk-releases/registry.json').read_text())
            self.assertEqual([v['version'] for v in registry['releases']], ['0.2.0', '0.1.0'])

    def test_corrupt_snapshot_does_not_modify_site(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot, site = self.snapshot(root), self.site(root)
            (snapshot / 'rose-punk.zip').write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError, 'verification'):
                publish.register(snapshot, site)
            self.assertFalse((site / 'public').exists())

    def test_older_release_controls_stay_out_of_site_gallery(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot, site = self.snapshot(root), self.site(root)
            entries = [{'id': key, 'name': key, 'src': f'/icons/{key}.svg'}
                       for key in ('app', 'fish', 'runtjik', 'runtjik-refresh')]
            original = publish.encoded(entries)
            (snapshot / 'gallery.json').write_bytes(original)
            manifest = json.loads((snapshot / 'release.json').read_text())
            manifest['artifacts']['gallery.json'] = release.sha256(original)
            (snapshot / 'release.json').write_bytes(publish.encoded(manifest))
            publish.register(snapshot, site)
            gallery = json.loads((site / 'src/lib/content/rose-punk-icons.json').read_text())
            self.assertEqual({entry['id'] for entry in gallery}, {'app', 'fish', 'runtjik'})
            self.assertEqual((site / 'public/rose-punk-releases/0.1.0/gallery.json').read_bytes(), original)
            publish.verify_snapshot(site / 'public/rose-punk-releases/0.1.0')

    def test_unpublished_registration_can_be_replaced_and_prunes_old_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot, site = self.snapshot(root), self.site(root)
            publish.register(snapshot, site)
            manifest = json.loads((snapshot / 'release.json').read_text())
            manifest['source_commit'] = 'different'
            (snapshot / 'release.json').write_bytes(publish.encoded(manifest))
            target = site / 'public/rose-punk-releases/0.1.0'
            (target / 'obsolete.svg').write_text('old')
            with patch.object(publish, 'ensure_unpublished') as guard:
                publish.register(snapshot, site)
            guard.assert_called_once_with(snapshot, site)
            self.assertFalse((target / 'obsolete.svg').exists())
            self.assertEqual((target / 'release.json').read_bytes(), (snapshot / 'release.json').read_bytes())
            registry = json.loads((target.parent / 'registry.json').read_text())
            self.assertEqual(registry['releases'][0]['sha256'], release.sha256((snapshot / 'release.json').read_bytes()))

    def test_published_registration_remains_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot, site = self.snapshot(root), self.site(root)
            publish.register(snapshot, site)
            target = site / 'public/rose-punk-releases/0.1.0/release.json'
            before = target.read_bytes()
            manifest = json.loads(before)
            manifest['source_commit'] = 'different'
            (snapshot / 'release.json').write_bytes(publish.encoded(manifest))
            with patch.object(publish, 'ensure_unpublished', side_effect=ValueError('was pushed')):
                with self.assertRaisesRegex(ValueError, 'was pushed'):
                    publish.register(snapshot, site)
            self.assertEqual(target.read_bytes(), before)

    def test_deployment_records_block_replacement(self):
        with tempfile.TemporaryDirectory() as temporary:
            snapshot = self.snapshot(Path(temporary))
            publish.ensure_unpublished(snapshot)
            for suffix in ('-deployment.json', '-deployment-started.json'):
                marker = snapshot.parent / ('0.1.0' + suffix)
                marker.write_text('{}')
                with self.subTest(suffix=suffix), self.assertRaisesRegex(ValueError, 'deployment record'):
                    publish.ensure_unpublished(snapshot)
                marker.unlink()

    def test_guard_allows_local_commits_but_rejects_pushed_history(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot, site = self.snapshot(root), self.site(root)
            remote = root / 'remote.git'

            def git(*args):
                return subprocess.check_output(['git', *args], cwd=site, text=True, stderr=subprocess.PIPE,
                                               env={**os.environ, 'GIT_CONFIG_GLOBAL': '/dev/null',
                                                    'GIT_CONFIG_NOSYSTEM': '1'})

            git('init', '--quiet')
            git('init', '--quiet', '--bare', str(remote))
            git('remote', 'add', 'origin', str(remote))
            publish.register(snapshot, site)
            git('add', 'public/rose-punk-releases')
            git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '--quiet', '-m', 'release')
            publish.ensure_unpublished(snapshot, site)
            git('push', '--quiet', 'origin', 'HEAD:refs/heads/releases')
            # ls-remote must find the push even without local tracking refs.
            git('update-ref', '-d', 'refs/remotes/origin/releases')
            with self.assertRaisesRegex(ValueError, 'was pushed'):
                publish.ensure_unpublished(snapshot, site)

    def test_recut_replaces_only_after_build_succeeds(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot = self.snapshot(root)
            before = (snapshot / 'release.json').read_bytes()
            with patch.object(publish, 'ensure_unpublished') as guard, \
                    patch.object(release, 'check_outputs'), \
                    patch.object(release, 'package', side_effect=ValueError('bad build')):
                with self.assertRaisesRegex(ValueError, 'bad build'):
                    publish.cut({}, {}, root, '0.1.0', root / 'site')
            guard.assert_called_once_with(snapshot, root / 'site')
            self.assertEqual((snapshot / 'release.json').read_bytes(), before)
            inputs = root / 'inputs'
            inputs.mkdir()
            for name in ('catalog.json', 'homepage.json', 'command-icons.json'):
                (inputs / name).write_text('{}')

            def package(trees, files, destination):
                destination.mkdir()
                (destination / 'rose-punk.zip').write_bytes(release.theme_zip({'index.theme': b'theme'}))
                return {}

            with patch.object(publish, 'ensure_unpublished'), \
                    patch.object(release, 'check_outputs'), \
                    patch.object(release, 'package', side_effect=package), \
                    patch.object(publish, 'HERE', inputs), \
                    patch.object(publish.subprocess, 'check_output', return_value='source'):
                self.assertEqual(publish.cut({}, {}, root, '0.1.0'), snapshot)
            self.assertNotEqual((snapshot / 'release.json').read_bytes(), before)
            publish.verify_snapshot(snapshot)

    def test_cut_gallery_excludes_controls_but_downloads_retain_them(self):
        import homepage
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs = root / 'inputs'
            inputs.mkdir()
            (inputs / 'catalog.json').write_bytes(publish.encoded({'app': {'name': 'Application'}}))
            (inputs / 'command-icons.json').write_bytes(publish.encoded({
                'fish': {'name': 'Fish shell', 'role': 'shell'},
                'runtjik-refresh': {'name': 'Refresh index', 'role': 'control'}}))
            (inputs / 'homepage.json').write_bytes(publish.encoded({'service': {'name': 'Service'}}))
            svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><path d="M4 4h56v56H4Z"/></svg>'
            trees = {publish.PRIMARY / 'scalable/apps': {
                key + '.svg': svg for key in ('app', 'fish', 'runtjik-refresh')},
                homepage.DEST: {'service.svg': svg}}

            def package(trees, files, destination):
                destination.mkdir()
                payload = {'index.theme': b'theme', **{
                    'scalable/apps/' + name: data
                    for name, data in trees[publish.PRIMARY / 'scalable/apps'].items()}}
                (destination / 'rose-punk.zip').write_bytes(release.theme_zip(payload))
                return {}

            with patch.object(release, 'check_outputs'), \
                    patch.object(release, 'package', side_effect=package), \
                    patch.object(publish, 'HERE', inputs), \
                    patch.object(publish.subprocess, 'check_output', return_value='source'):
                snapshot = publish.cut(trees, {}, root, '0.1.0')
            gallery = json.loads((snapshot / 'gallery.json').read_text())
            self.assertEqual({entry['id'] for entry in gallery}, {'app', 'fish', 'service'})
            for entry in gallery:
                self.assertEqual((snapshot / 'icons' / (entry['id'] + '.svg')).read_bytes(), svg)
            manifest = publish.verify_snapshot(snapshot)
            self.assertIn('icons/fish.svg', manifest['artifacts'])
            self.assertNotIn('icons/runtjik-refresh.svg', manifest['artifacts'])
            with zipfile.ZipFile(snapshot / 'rose-punk.zip') as archive:
                self.assertEqual(archive.read('rose-punk/scalable/apps/fish.svg'), svg)
                self.assertEqual(archive.read('rose-punk/scalable/apps/runtjik-refresh.svg'), svg)

    def test_failed_directory_swap_restores_original(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot = self.snapshot(root)
            staging = root / '.staging'
            staging.mkdir()
            prepared = staging / 'replacement'
            prepared.mkdir()
            rename = Path.rename

            def fail_install(path, target):
                if path == prepared:
                    raise OSError('cannot install')
                return rename(path, target)

            with patch.object(Path, 'rename', fail_install):
                with self.assertRaisesRegex(OSError, 'cannot install'):
                    publish.replace_snapshot(prepared, snapshot)
            publish.verify_snapshot(snapshot)

    def test_failed_site_check_never_deploys(self):
        import subprocess
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot = self.snapshot(root)
            with patch.object(publish.subprocess, 'check_output', return_value=''), patch.object(publish.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, 'check')) as run:
                with self.assertRaises(subprocess.CalledProcessError):
                    publish.deploy(snapshot, root)
                self.assertEqual(run.call_count, 1)
                self.assertFalse((root / '0.1.0-deployment.json').exists())
                self.assertFalse((root / '0.1.0-deployment-started.json').exists())

    def test_unrelated_site_edits_block_deployment(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot = self.snapshot(root)
            with patch.object(publish.subprocess, 'check_output', return_value=' M src/App.svelte\n'), \
                    patch.object(publish.subprocess, 'run') as run:
                with self.assertRaisesRegex(ValueError, 'unrelated'):
                    publish.deploy(snapshot, root)
                run.assert_not_called()

    def test_public_hash_mismatch_does_not_write_success_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot = self.snapshot(root)
            with patch.object(publish.subprocess, 'check_output', return_value=''), \
                    patch.object(publish.subprocess, 'run'), \
                    patch.object(publish.urllib.request, 'urlopen', return_value=io.BytesIO(b'wrong deployment')):
                with self.assertRaisesRegex(ValueError, 'verification failed'):
                    publish.deploy(snapshot, root)
            self.assertFalse((root / '0.1.0-deployment.json').exists())
            self.assertTrue((root / '0.1.0-deployment-started.json').exists())
            with self.assertRaisesRegex(ValueError, 'deployment record'):
                publish.ensure_unpublished(snapshot)

    def test_framed_archive_keeps_aliases_and_attribution(self):
        import framed
        svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><path fill="#f6c177" d="M0 0H10V10Z"/></svg>'
        files = {'scalable/apps/zed-nightly.svg': framed.frame(svg),
                 'scalable/apps/dev.zed.Zed-Nightly.svg': framed.frame(svg),
                 'index.theme': framed.INDEX.encode(), 'NOTICE.txt': b'attribution'}
        with zipfile.ZipFile(io.BytesIO(release.theme_zip(files, 'rose-punk-framed'))) as archive:
            self.assertEqual(archive.read('rose-punk-framed/scalable/apps/zed-nightly.svg'),
                             archive.read('rose-punk-framed/scalable/apps/dev.zed.Zed-Nightly.svg'))
            self.assertIn(b'id="tile"', archive.read('rose-punk-framed/scalable/apps/zed-nightly.svg'))
            self.assertEqual(archive.read('rose-punk-framed/NOTICE.txt'), b'attribution')


if __name__ == '__main__':
    unittest.main()
