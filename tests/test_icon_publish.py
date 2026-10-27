"""Release publication contracts without network or live site changes."""
import io
import json
from pathlib import Path
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

    def test_existing_version_cannot_be_replaced(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot, site = self.snapshot(root), self.site(root)
            publish.register(snapshot, site)
            manifest = json.loads((snapshot / 'release.json').read_text())
            manifest['source_commit'] = 'different'
            (snapshot / 'release.json').write_bytes(publish.encoded(manifest))
            with self.assertRaisesRegex(ValueError, 'differs'):
                publish.register(snapshot, site)

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
