"""Fast-forward a temporary local dependency; never touch live Git remotes."""
import contextlib
import fcntl
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import tjikup_support
from fleet_update.core import UpdateError
from fleet_update.tooltjik_sync import pull, checkout


class TooltjikSyncTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / 'code/tooltjik'
        self.remote = self.root / 'remote'
        env = {'HOME': str(self.root), 'TOOLTJIK_REPO': '', 'TJIKUP_COLOR': '0', 'TJIKUP_COLUMNS': '160',
               'TJIKUP_REPORT_FILE': str(self.root / 'report'),
               'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
               'GIT_AUTHOR_NAME': 'Test', 'GIT_AUTHOR_EMAIL': 'test@example.org',
               'GIT_COMMITTER_NAME': 'Test', 'GIT_COMMITTER_EMAIL': 'test@example.org'}
        self.env_patch = patch.dict(os.environ, env)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.git('init', '-b', 'main', str(self.remote))
        (self.remote / 'file').write_text('original\n')
        self.git('-C', str(self.remote), 'add', '.')
        self.git('-C', str(self.remote), 'commit', '-m', 'initial')
        self.repo.parent.mkdir()
        self.git('clone', str(self.remote), str(self.repo))

    def git(self, *args):
        return subprocess.check_output(['git', *args], text=True, stderr=subprocess.STDOUT).strip()

    def update_remote(self):
        (self.remote / 'file').write_text('upstream\n')
        self.git('-C', str(self.remote), 'commit', '-am', 'upstream change')

    def invoke(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(pull(**kwargs), 0)
        return output.getvalue()

    def test_fast_forward_then_unchanged(self):
        self.update_remote()
        output = self.invoke()
        self.assertIn('PULL    ✓ Tooltjik', output)
        self.assertIn('1 commit · fast-forward', output)
        self.assertEqual((self.repo / 'file').read_text(), 'upstream\n')
        self.assertIn('SKIP    ✓ Tooltjik', self.invoke())

    def test_dirty_staged_and_untracked_work_fail_without_fetching(self):
        for state in ('unstaged', 'staged', 'untracked'):
            with self.subTest(state=state):
                path = self.repo / ('new' if state == 'untracked' else 'file')
                path.write_text('personal work\n')
                if state == 'staged':
                    self.git('-C', str(self.repo), 'add', 'file')
                before = self.git('-C', str(self.repo), 'status', '--porcelain')
                with self.assertRaisesRegex(UpdateError, 'Dirty Tooltjik'):
                    self.invoke()
                self.assertEqual(self.git('-C', str(self.repo), 'status', '--porcelain'), before)
                self.assertEqual(path.read_text(), 'personal work\n')
                self.assertFalse((self.repo / '.git/FETCH_HEAD').exists())
                self.git('-C', str(self.repo), 'restore', '--staged', '--worktree', 'file')
                (self.repo / 'new').unlink(missing_ok=True)

    def test_ahead_and_diverged_history_preserve_commits_without_push(self):
        (self.repo / 'local').write_text('local commit\n')
        self.git('-C', str(self.repo), 'add', 'local')
        self.git('-C', str(self.repo), 'commit', '-m', 'development')
        head = self.git('-C', str(self.repo), 'rev-parse', 'HEAD')
        for diverged in (False, True):
            if diverged:
                self.update_remote()
            remote_head = self.git('-C', str(self.remote), 'rev-parse', 'HEAD')
            output = self.invoke()
            self.assertIn('diverged history' if diverged else 'local commits', output)
            self.assertEqual(self.git('-C', str(self.repo), 'rev-parse', 'HEAD'), head)
            self.assertEqual(self.git('-C', str(self.remote), 'rev-parse', 'HEAD'), remote_head)
            self.assertEqual(self.git('-C', str(self.repo), 'stash', 'list'), '')

    def test_preview_does_not_fetch_lock_or_move_checkout(self):
        self.update_remote()
        self.assertIn('would fetch', self.invoke(dry_run=True))
        self.assertEqual((self.repo / 'file').read_text(), 'original\n')
        self.assertFalse((self.repo / '.git/FETCH_HEAD').exists())
        self.assertFalse((self.repo / '.git/tjikup-sync.lock').exists())

    def test_fetch_failure_is_an_error(self):
        self.git('-C', str(self.repo), 'remote', 'set-url', 'origin', str(self.root / 'missing'))
        with self.assertRaisesRegex(UpdateError, 'fetch.*failed'):
            self.invoke()
        self.assertEqual((self.repo / 'file').read_text(), 'original\n')

    def test_detached_or_untracked_branch_warns_without_fetching(self):
        self.git('-C', str(self.repo), 'branch', '--unset-upstream')
        self.assertIn('no upstream', self.invoke())
        self.git('-C', str(self.repo), 'checkout', '--detach')
        self.assertIn('detached HEAD', self.invoke())
        self.assertFalse((self.repo / '.git/FETCH_HEAD').exists())

    def test_explicit_linked_worktree_uses_its_own_lock(self):
        worktree = self.root / 'worktree'
        self.git('-C', str(self.repo), 'worktree', 'add', '-b', 'work', str(worktree))
        self.git('-C', str(worktree), 'branch', '--set-upstream-to', 'origin/main')
        self.update_remote()
        with patch.dict(os.environ, {'TOOLTJIK_REPO': str(worktree)}):
            self.assertIn('PULL', self.invoke())
        self.assertEqual((worktree / 'file').read_text(), 'upstream\n')
        self.assertEqual((self.repo / 'file').read_text(), 'original\n')

    def test_busy_or_unfinished_operation_blocks_update(self):
        with (self.repo / '.git/tjikup-sync.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            with self.assertRaisesRegex(UpdateError, 'busy'):
                self.invoke()
        (self.repo / '.git/rebase-merge').mkdir()
        with self.assertRaisesRegex(UpdateError, 'unfinished Git operation'):
            self.invoke()

    def test_missing_checkout_is_left_for_bootstrap_and_legacy_is_rejected(self):
        self.repo.rename(self.root / 'saved')
        self.assertIn('installer will bootstrap', self.invoke())
        self.assertFalse(self.repo.exists())
        legacy = self.root / '.local/share/tooltjik'
        legacy.parent.mkdir(parents=True)
        (self.root / 'saved').rename(legacy)
        with self.assertRaisesRegex(UpdateError, 'Move'):
            checkout()

    def test_apply_depends_on_tooltjik_without_committing_or_pushing_it(self):
        plan = json.loads((Path(__file__).resolve().parents[1] / 'scripts/fleet_update/workflow.json').read_text())
        steps = {step['id']: step for step in plan}
        self.assertIn('pull-tooltjik', steps['apply-fleet']['needs'])
        self.assertEqual(steps['pull-tooltjik']['needs'], ['commit'])
        self.assertEqual([step['id'] for step in plan if 'tooltjik' in step['id']], ['pull-tooltjik'])
