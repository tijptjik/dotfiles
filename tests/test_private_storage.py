import importlib.machinery
import importlib.util
from pathlib import Path
import tempfile
import json
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'home/dot_local/bin/executable_private-storage'
loader = importlib.machinery.SourceFileLoader('private_storage', str(SOURCE))
spec = importlib.util.spec_from_loader(loader.name, loader)
storage = importlib.util.module_from_spec(spec)
loader.exec_module(storage)


class PrivateStorageTests(unittest.TestCase):
    def test_hourly_run_never_initializes_missing_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'documents').mkdir()
            with patch.object(storage, 'HOME', root), patch.object(storage, 'STATE', root/'state'), \
                 patch.object(storage, 'settings', return_value={'sharing_approved': True, 'folders':['documents'], 'remote':'drive:private'}), \
                 patch.object(storage, 'run') as run:
                with self.assertRaisesRegex(RuntimeError, 'not been initialized'):
                    storage.sync()
                run.assert_not_called()

    def test_missing_or_symlinked_source_cannot_propagate_deletion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'target').mkdir()
            (root/'documents').symlink_to(root/'target', target_is_directory=True)
            with patch.object(storage, 'HOME', root), patch.object(storage, 'STATE', root/'state'), \
                 patch.object(storage, 'settings', return_value={'sharing_approved': True, 'folders':['documents'], 'remote':'drive:private'}), \
                 patch.object(storage, 'run') as run:
                with self.assertRaisesRegex(RuntimeError, 'real local directory'):
                    storage.sync()
                run.assert_not_called()

    def test_overlapping_operations_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(storage, 'STATE', Path(directory)):
            with storage.locked():
                with self.assertRaisesRegex(RuntimeError, 'Another private'):
                    with storage.locked():
                        self.fail('Second operation acquired lock')

    def test_normal_sync_preserves_conflicts_and_never_resyncs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'documents').mkdir()
            work = root/'state/bisync/documents'
            work.mkdir(parents=True)
            (work/'initialized.json').write_text(json.dumps({'host': storage.HOST, 'remote': 'drive:private/documents'}))
            calls = []
            def run(args, **kwargs):
                calls.append(args)
                Path(args[args.index('--log-file') + 1]).write_text('Sync completed')
            with patch.object(storage, 'HOME', root), patch.object(storage, 'STATE', root/'state'), \
                 patch.object(storage, 'settings', return_value={'sharing_approved': True, 'folders':['documents'], 'remote':'drive:private'}), \
                 patch.object(storage, 'run', side_effect=run):
                storage.sync()
            self.assertEqual(len(calls), 1)
            args = calls[0]
            self.assertNotIn('--resync', args)
            self.assertNotIn('--force', args)
            self.assertIn('--check-access', args)
            self.assertIn('--filters-file', args)
            self.assertIn('--backup-dir1', args)
            self.assertIn('--backup-dir2', args)
            self.assertEqual(args[args.index('--conflict-resolve')+1], 'none')
            self.assertEqual(args[args.index('--max-delete')+1], '5')

    def test_initialization_requires_verified_layout(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(storage, 'CONFIG', Path(directory)), \
             patch.object(storage, 'settings', return_value={'sharing_approved': True, 'folders':['documents']}), \
             patch.object(storage, 'run') as run:
            with self.assertRaisesRegex(RuntimeError, 'reorganization'):
                storage.sync(initial=True)
            run.assert_not_called()

    def test_laptop_initial_merge_prefers_established_cloud_and_retains_local_recovery(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'documents').mkdir()
            (root/'layout-ready').write_text('verified')
            calls = []
            def run(args, **kwargs):
                calls.append(args)
                if '--log-file' in args:
                    Path(args[args.index('--log-file')+1]).write_text('Sync completed')
                return SimpleNamespace(stdout='{"bytes": 0}')
            with patch.object(storage, 'HOME', root), patch.object(storage, 'STATE', root/'state'), \
                 patch.object(storage, 'CONFIG', root), patch.object(storage, 'HOST', 'li'), \
                 patch.object(storage, 'settings', return_value={'sharing_approved': True, 'folders':['documents'], 'remote':'drive:private'}), \
                 patch.object(storage, 'run', side_effect=run):
                storage.sync(initial=True)
            transfers = [args for args in calls if 'bisync' in args]
            self.assertEqual(len(transfers), 2)
            self.assertIn('--dry-run', transfers[0])
            for args in transfers:
                self.assertEqual(args[args.index('--resync-mode')+1], 'path2')
                self.assertIn('--backup-dir1', args)
            receipt = json.loads((root/'state/bisync/documents/initialized.json').read_text())
            self.assertEqual(receipt['host'], 'li')

    def test_unapproved_sharing_blocks_initial_and_normal_sync_before_commands(self):
        for initial in (False, True):
            for approval in (None, False, "true"):
                with self.subTest(initial=initial, approval=approval), \
                     patch.object(storage, 'settings', return_value={'sharing_approved': approval}), \
                     patch.object(storage, 'run') as run:
                    with self.assertRaisesRegex(RuntimeError, 'sharing has not been approved'):
                        storage.sync(initial=initial)
                    run.assert_not_called()
