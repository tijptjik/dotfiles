"""Exercise fleet Git shortcuts against disposable repositories only."""
import contextlib
import fcntl
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('tjik_git', ROOT / 'home/dot_local/lib/tjik_git.py')
tjik_git = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tjik_git)


class FleetGitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repos = []
        self.env = patch.dict('os.environ', {'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_NOSYSTEM': '1'})
        self.env.start()
        self.addCleanup(self.env.stop)
        for name in ('dotjik', 'systjik', 'tooltjik'):
            remote = self.root / (name + '.git')
            self.run_git('init', '--bare', '--initial-branch=main', str(remote))
            repo = self.root / name
            self.run_git('clone', str(remote), str(repo))
            self.configure(repo)
            self.commit(repo, 'base', 'base')
            self.run_git('-C', str(repo), 'push', '-u', 'origin', 'main')
            self.repos.append((name, repo))

    def run_git(self, *args):
        return subprocess.run(['git', *args], check=True, text=True,
                              capture_output=True).stdout.strip()

    def configure(self, repo):
        self.run_git('-C', str(repo), 'config', 'user.name', 'Test')
        self.run_git('-C', str(repo), 'config', 'user.email', 'test@example.invalid')

    def commit(self, repo, filename, content):
        (repo / filename).write_text(content)
        self.run_git('-C', str(repo), 'add', filename)
        self.run_git('-C', str(repo), 'commit', '-m', content)

    def sync(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return tjik_git.synchronize(self.repos, **kwargs)

    def test_chezmoi_source_subdirectory_resolves_repository_root(self):
        source = self.repos[0][1] / 'home'
        source.mkdir()
        original_run = subprocess.run

        def run(command, **kwargs):
            if command == ['chezmoi', 'source-path']:
                return subprocess.CompletedProcess(command, 0, str(source) + '\n', '')
            return original_run(command, **kwargs)

        with patch.dict('os.environ', {'DOTJIK_REPO': '',
                                      'SYSTJIK_REPO': str(self.repos[1][1]),
                                      'TOOLTJIK_REPO': str(self.repos[2][1])}), \
                patch.object(tjik_git.subprocess, 'run', side_effect=run):
            self.assertEqual([repo for _, repo in tjik_git.repositories()],
                             [repo for _, repo in self.repos])

    def test_push_only_leaves_uncommitted_changes(self):
        for _, repo in self.repos:
            self.commit(repo, 'local', 'local')
            (repo / 'base').write_text('dirty')
        self.sync()
        for name, repo in self.repos:
            self.assertEqual(self.run_git('-C', str(repo), 'rev-parse', 'HEAD'),
                             self.run_git('--git-dir', str(self.root / (name + '.git')), 'rev-parse', 'main'))
            self.assertEqual((repo / 'base').read_text(), 'dirty')

    def test_rebase_then_push_divergent_history(self):
        for name, repo in self.repos:
            peer = self.root / (name + '-peer')
            self.run_git('clone', str(self.root / (name + '.git')), str(peer))
            self.configure(peer)
            self.commit(peer, 'remote', 'remote')
            self.run_git('-C', str(peer), 'push')
            self.commit(repo, 'local', 'local')
        self.sync(sync=True)
        for name, repo in self.repos:
            self.assertTrue((repo / 'remote').exists())
            self.assertEqual(self.run_git('-C', str(repo), 'rev-list', '--count', 'HEAD'), '3')
            self.assertEqual(self.run_git('-C', str(repo), 'rev-parse', 'HEAD'),
                             self.run_git('--git-dir', str(self.root / (name + '.git')), 'rev-parse', 'main'))

    def test_dirty_last_repo_blocks_all_network_operations(self):
        (self.repos[-1][1] / 'untracked').touch()
        with patch.object(tjik_git, 'git', wraps=tjik_git.git) as calls:
            with self.assertRaisesRegex(tjik_git.SyncError, 'dirty'):
                self.sync(sync=True)
            self.assertFalse(any(call.args[1] in ('pull', 'push') for call in calls.call_args_list))

    def test_active_workflow_blocks_sync(self):
        with (self.repos[0][1] / '.git/tjikup-workflow.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(tjik_git.SyncError, 'another Tjikup'):
                self.sync()

    def test_unfinished_merge_blocks_push(self):
        (self.repos[-1][1] / '.git/MERGE_HEAD').touch()
        with self.assertRaisesRegex(tjik_git.SyncError, 'unfinished Git operation'):
            self.sync()

    def test_missing_upstream_blocks_push(self):
        self.run_git('-C', str(self.repos[-1][1]), 'branch', '--unset-upstream')
        with self.assertRaises(tjik_git.SyncError):
            self.sync()

    def test_dry_run_does_not_write_locks_or_push(self):
        self.commit(self.repos[0][1], 'local', 'local')
        self.sync(dry_run=True)
        self.assertFalse((self.repos[0][1] / '.git/tjikup-workflow.lock').exists())
        self.assertEqual(self.run_git('--git-dir', str(self.root / 'dotjik.git'), 'rev-list', '--count', 'main'), '1')

    def paused_conflict(self, *, apply_backend=False, another_conflict=False):
        repo = self.repos[1][1]
        peer = self.root / 'conflict-peer'
        self.run_git('clone', str(self.root / 'systjik.git'), str(peer))
        self.configure(peer)
        self.commit(peer, 'base', 'remote conflict')
        if another_conflict:
            self.commit(peer, 'second', 'remote second')
        self.run_git('-C', str(peer), 'push')
        self.commit(repo, 'base', 'local conflict')
        if another_conflict:
            self.commit(repo, 'second', 'local second')
        self.run_git('-C', str(repo), 'fetch')
        command = ['git', '-C', str(repo), 'rebase']
        if apply_backend:
            command.append('--apply')
        result = subprocess.run([*command, 'origin/main'], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        return repo

    def stage_resolution(self, repo):
        (repo / 'base').write_text('combined resolution')
        self.run_git('-C', str(repo), 'add', 'base')

    def test_push_continues_staged_resolution_and_keeps_message(self):
        repo = self.paused_conflict()
        self.stage_resolution(repo)
        with patch.dict('os.environ', {'GIT_EDITOR': 'false'}):
            self.sync()
        self.assertEqual(self.run_git('-C', str(repo), 'symbolic-ref', '--short', 'HEAD'), 'main')
        self.assertEqual(self.run_git('-C', str(repo), 'log', '-1', '--format=%s'), 'local conflict')
        self.assertEqual(self.run_git('--git-dir', str(self.root / 'systjik.git'), 'show', 'main:base'), 'combined resolution')

    def test_sync_continues_apply_backend_resolution(self):
        repo = self.paused_conflict(apply_backend=True)
        self.stage_resolution(repo)
        self.sync(sync=True)
        self.assertFalse((repo / '.git/rebase-apply').exists())
        self.assertEqual(self.run_git('-C', str(repo), 'status', '--porcelain'), '')

    def test_clean_edit_stop_continues(self):
        repo = self.repos[1][1]
        self.commit(repo, 'local', 'local')
        with patch.dict('os.environ', {'GIT_SEQUENCE_EDITOR': "sed -i '1s/^pick/edit/'"}):
            self.run_git('-C', str(repo), 'rebase', '-i', 'HEAD~1')
        self.assertTrue((repo / '.git/rebase-merge').exists())
        self.sync(sync=True)
        self.assertFalse((repo / '.git/rebase-merge').exists())

    def test_rebase_dry_run_does_not_continue_or_push(self):
        repo = self.paused_conflict()
        self.stage_resolution(repo)
        before = self.run_git('-C', str(repo), 'status', '--porcelain')
        with patch.object(tjik_git, 'git', wraps=tjik_git.git) as calls:
            self.sync(sync=True, dry_run=True)
            self.assertFalse(any(call.args[1] in ('rebase', 'pull', 'push') for call in calls.call_args_list))
        self.assertTrue((repo / '.git/rebase-merge').exists())
        self.assertEqual(self.run_git('-C', str(repo), 'status', '--porcelain'), before)

    def test_unresolved_rebase_stops_before_continuation_or_network(self):
        self.paused_conflict()
        with patch.object(tjik_git, 'git', wraps=tjik_git.git) as calls:
            with self.assertRaisesRegex(tjik_git.SyncError, 'unresolved conflicts'):
                self.sync()
            self.assertFalse(any(call.args[1] in ('rebase', 'pull', 'push') for call in calls.call_args_list))

    def test_unstaged_edits_during_rebase_are_not_auto_staged(self):
        repo = self.paused_conflict()
        self.stage_resolution(repo)
        (repo / 'base').write_text('extra unstaged edit')
        with self.assertRaisesRegex(tjik_git.SyncError, 'unstaged changes'):
            self.sync()
        self.assertEqual(self.run_git('-C', str(repo), 'show', ':base'), 'combined resolution')

    def test_another_conflict_during_continue_blocks_all_pushes(self):
        repo = self.paused_conflict(another_conflict=True)
        self.stage_resolution(repo)
        with patch.object(tjik_git, 'git', wraps=tjik_git.git) as calls:
            with self.assertRaises(tjik_git.SyncError):
                self.sync()
            self.assertFalse(any(call.args[1] in ('pull', 'push') for call in calls.call_args_list))
        self.assertEqual(self.run_git('-C', str(repo), 'diff', '--name-only', '--diff-filter=U'), 'second')

    def test_bad_later_checkout_blocks_rebase_continuation(self):
        repo = self.paused_conflict()
        self.stage_resolution(repo)
        (self.repos[-1][1] / 'untracked').touch()
        with self.assertRaisesRegex(tjik_git.SyncError, 'dirty'):
            self.sync(sync=True)
        self.assertTrue((repo / '.git/rebase-merge').exists())

    def test_conflicting_pull_stops_before_any_push(self):
        repo = self.repos[1][1]
        peer = self.root / 'peer'
        self.run_git('clone', str(self.root / 'systjik.git'), str(peer))
        self.configure(peer)
        self.commit(peer, 'base', 'remote conflict')
        self.run_git('-C', str(peer), 'push')
        self.commit(repo, 'base', 'local conflict')
        with patch.object(tjik_git, 'git', wraps=tjik_git.git) as calls:
            with self.assertRaises(tjik_git.SyncError):
                self.sync(sync=True)
            self.assertFalse(any(call.args[1] == 'push' for call in calls.call_args_list))
        self.assertTrue((repo / '.git/rebase-merge').exists())


if __name__ == '__main__':
    unittest.main()
