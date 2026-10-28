import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('media_permissions', ROOT / 'etc/si-media-permissions/permissions.py')
permissions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(permissions)


class MediaPermissionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.root = self.base / 'videos'
        self.root.mkdir(mode=0o700)
        self.media = self.root / 'film.mkv'
        self.media.write_bytes(b'unchanged media contents')
        self.media.chmod(0o600)

    def tearDown(self):
        self.temporary.cleanup()

    def scan(self, apply):
        fd = os.open(self.root, permissions.DIR_FLAGS)
        journal = permissions.Journal(self.base / 'journal')
        try:
            return permissions.scan_root(self.root, fd, os.getgid(), apply, journal)
        finally:
            os.close(fd)
            journal.close()

    def test_dry_run_never_changes_permissions_or_creates_a_journal(self):
        result = self.scan(False)
        self.assertEqual(result['changed'], 2)
        self.assertEqual(stat.S_IMODE(self.root.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(self.media.stat().st_mode), 0o600)
        self.assertFalse((self.base / 'journal').exists())

    def test_repair_preserves_owner_content_mtime_and_other_access(self):
        before = self.media.stat()
        result = self.scan(True)
        self.assertEqual(result['changed'], 2)
        self.assertEqual(stat.S_IMODE(self.root.stat().st_mode), 0o2770)
        self.assertEqual(stat.S_IMODE(self.media.stat().st_mode), 0o660)
        after = self.media.stat()
        self.assertEqual((before.st_uid, before.st_size, before.st_mtime_ns), (after.st_uid, after.st_size, after.st_mtime_ns))
        self.assertEqual(self.media.read_bytes(), b'unchanged media contents')
        journal = list((self.base / 'journal').glob('changes-*.jsonl'))[0]
        rows = [json.loads(line) for line in journal.read_text().splitlines()]
        self.assertEqual(len(rows), 2)
        self.assertEqual(stat.S_IMODE(journal.stat().st_mode), 0o600)
        self.assertEqual(self.scan(True)['changed'], 0)

    def test_symlink_files_and_directories_do_not_escape_the_video_root(self):
        outside = self.base / 'private'
        outside.mkdir(mode=0o700)
        secret = outside / 'secret'
        secret.write_text('private')
        secret.chmod(0o600)
        (self.root / 'linked-file.mkv').symlink_to(secret)
        (self.root / 'linked-folder').symlink_to(outside, target_is_directory=True)
        self.scan(True)
        self.assertEqual(stat.S_IMODE(outside.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(secret.stat().st_mode), 0o600)

    def test_symlink_root_component_is_refused(self):
        (self.base / 'alias').symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(OSError):
            permissions.open_root(self.base, 'alias')

    def test_wrong_scope_fails_before_storage_checks_or_changes(self):
        with patch.dict('sys.modules', {'storage': types.SimpleNamespace(check_mounts=lambda config: self.fail('guard was reached'))}):
            with self.assertRaisesRegex(RuntimeError, 'scope'):
                permissions.guarded_scan({'gid': 950, 'group': 'media', 'roots': ['private/wgs']}, {}, True, self.base / 'state')
        self.assertEqual(stat.S_IMODE(self.media.stat().st_mode), 0o600)

    def test_missing_mount_guard_stops_before_any_changes(self):
        def reject(config):
            raise RuntimeError('wrong disk UUID')
        policy = {'gid': 950, 'group': 'media', 'roots': sorted(permissions.ALLOWED)}
        with patch.object(permissions.grp, 'getgrnam', return_value=types.SimpleNamespace(gr_gid=950)), patch.dict('sys.modules', {'storage': types.SimpleNamespace(check_mounts=reject)}):
            with self.assertRaisesRegex(RuntimeError, 'wrong disk UUID'):
                permissions.guarded_scan(policy, {}, True, self.base / 'state')
        self.assertEqual(stat.S_IMODE(self.media.stat().st_mode), 0o600)

    def test_incomplete_scope_is_validated_before_mutation(self):
        mount = self.base / 'data'
        public = mount / 'public'
        public.mkdir(parents=True)
        movies = public / 'movies'
        movies.mkdir(mode=0o700)
        policy = {'gid': 950, 'group': 'media', 'roots': sorted(permissions.ALLOWED)}
        config = {'layout': [['data', 'd1', str(mount)]]}
        with patch.object(permissions.grp, 'getgrnam', return_value=types.SimpleNamespace(gr_gid=950)), patch.dict('sys.modules', {'storage': types.SimpleNamespace(check_mounts=lambda config: None)}):
            with self.assertRaisesRegex(RuntimeError, 'Missing media roots'):
                permissions.guarded_scan(policy, config, True, self.base / 'state')
        self.assertEqual(stat.S_IMODE(movies.stat().st_mode), 0o700)
        self.assertFalse((self.base / 'state').exists())


if __name__ == '__main__':
    unittest.main()
