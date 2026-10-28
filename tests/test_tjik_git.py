"""Exercise fleet Git shortcuts against disposable repositories only."""
import contextlib
import fcntl
import importlib.util
import io
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('tjik_git', ROOT / 'native/home/files/.local/lib/tjik_git.py')
tjik_git = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tjik_git)


class GitProgressTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('gum'), 'Gum is not installed')
    def test_gum_animates_rows_and_restores_cursor(self):
        output = io.StringIO()
        repos = [('Dotjik', Path('/unused/dot')), ('Systjik', Path('/unused/sys'))]
        with contextlib.redirect_stdout(output), \
                patch.object(output, 'isatty', return_value=True), \
                patch.dict('os.environ', {'TERM': 'xterm-256color', 'TJIKUP_NO_SPIN': '0'}):
            with tjik_git.GitProgress(repos, 'PULL') as progress:
                frames = set()
                deadline = time.monotonic() + 3
                while len(frames) < 2 and time.monotonic() < deadline:
                    time.sleep(.08)
                    progress.draw()
                    frames.update(re.findall('[\u2800-\u28ff]', output.getvalue()))
                progress.complete(0, True)
                progress.complete(1, False)
                progress.draw()
            self.assertIsNotNone(progress.process.poll())
        self.assertGreaterEqual(len(frames), 2)
        self.assertIn('Dotjik   PULL OK', output.getvalue())
        self.assertIn('Systjik  PULL FAILED', output.getvalue())
        self.assertTrue(output.getvalue().endswith('\033[?25h'))


class FleetGitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repos = []
        self.env = patch.dict('os.environ', {'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_NOSYSTEM': '1'})
        self.env.start()
        self.addCleanup(self.env.stop)
        for name in ('dotjik', 'systjik', 'tjikos'):
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

    def test_default_dotfiles_location_needs_no_chezmoi_query(self):
        with patch.dict('os.environ', {'DOTJIK_REPO': '', 'TJIKOS_REPO': str(self.repos[2][1])}), \
                patch.object(tjik_git.Path, 'home', return_value=self.root), \
                patch.object(tjik_git.subprocess, 'run') as run:
            self.assertEqual(tjik_git.repositories()[0], ('Dotjik', self.root / '.local/share/dotjik'))
            run.assert_not_called()

    def test_tjikos_defaults_to_code_even_before_checkout_exists(self):
        with patch.dict('os.environ', {'DOTJIK_REPO': str(self.repos[0][1]),
                                      'SYSTJIK_REPO': str(self.repos[1][1]),
                                      'TJIKOS_REPO': ''}), \
                patch.object(tjik_git.Path, 'home', return_value=self.root):
            self.assertEqual(tjik_git.repositories()[-1],
                             ('tjikOS', self.root / 'code/tjikos'))

    def test_tjikos_override_selects_checkout(self):
        selected = self.root / 'custom-tjikos'
        with patch.dict('os.environ', {'DOTJIK_REPO': str(self.repos[0][1]),
                                      'TJIKOS_REPO': str(selected),
                                      'TOOLTJIK_REPO': str(self.repos[2][1])}):
            self.assertEqual(tjik_git.repositories()[-1], ('tjikOS', selected))

    def test_old_tooltjik_checkouts_do_not_change_tjikos_default(self):
        (self.root / '.local/share/tooltjik').mkdir(parents=True)
        (self.root / 'code/tooltjik').mkdir(parents=True)
        with patch.dict('os.environ', {'DOTJIK_REPO': str(self.repos[0][1]),
                                      'TOOLTJIK_REPO': str(self.root / 'code/tooltjik'),
                                      'TJIKOS_REPO': ''}), \
                patch.object(tjik_git.Path, 'home', return_value=self.root):
            self.assertEqual(tjik_git.repositories()[-1],
                             ('tjikOS', self.root / 'code/tjikos'))

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

    def test_network_stages_overlap_and_all_pulls_finish_before_push(self):
        original_git = tjik_git.git
        barrier = threading.Barrier(3, timeout=5)
        pulled = set()
        pushed = set()
        mutex = threading.Lock()

        def git(repo, *args, **kwargs):
            if args[0] not in ('pull', 'push'):
                return original_git(repo, *args, **kwargs)
            # Each stage can pass only when all three workers are in flight.
            barrier.wait()
            with mutex:
                if args[0] == 'pull':
                    pulled.add(repo)
                else:
                    self.assertEqual(pulled, {path for _, path in self.repos})
                    pushed.add(repo)
            return ''

        with patch.object(tjik_git, 'git', side_effect=git):
            self.sync(sync=True)
        self.assertEqual(pushed, {path for _, path in self.repos})

    def test_failed_parallel_pull_waits_for_peers_and_blocks_push(self):
        original_git = tjik_git.git
        barrier = threading.Barrier(3, timeout=5)
        failed = threading.Event()
        finished = set()
        mutex = threading.Lock()

        def git(repo, *args, **kwargs):
            if args[0] == 'push':
                self.fail('push after failed pull')
            if args[0] != 'pull':
                return original_git(repo, *args, **kwargs)
            barrier.wait()
            if repo == self.repos[0][1]:
                failed.set()
                raise tjik_git.SyncError('deliberate pull failure')
            self.assertTrue(failed.wait(5))
            # The workflow lock must remain held until every peer finishes.
            with (self.repos[0][1] / '.git/tjikup-workflow.lock').open('a') as lock:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with mutex:
                finished.add(repo)
            return ''

        with patch.object(tjik_git, 'git', side_effect=git):
            with self.assertRaisesRegex(tjik_git.SyncError, 'deliberate pull failure'):
                self.sync(sync=True)
        self.assertEqual(finished, {repo for _, repo in self.repos[1:]})

    def test_parallel_push_reports_every_failure(self):
        original_git = tjik_git.git
        barrier = threading.Barrier(3, timeout=5)

        def git(repo, *args, **kwargs):
            if args[0] != 'push':
                return original_git(repo, *args, **kwargs)
            barrier.wait()
            raise tjik_git.SyncError(f'failed {repo.name}')

        with patch.object(tjik_git, 'git', side_effect=git):
            with self.assertRaises(tjik_git.SyncError) as raised:
                self.sync()
        for name, _ in self.repos:
            self.assertIn(f'failed {name}', str(raised.exception))

    def test_plain_progress_reports_each_stage_and_completion(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch.object(tjik_git.shutil, 'which') as gum:
            tjik_git.synchronize(self.repos, sync=True)
        gum.assert_not_called()
        for name, _ in self.repos:
            for stage in ('PULL', 'PUSH'):
                self.assertIn(f'{name}: {stage} RUNNING', output.getvalue())
                self.assertIn(f'{name}: {stage} OK', output.getvalue())

    def test_success_output_is_quiet_unless_verbose(self):
        original_git = tjik_git.git
        noise = ('ControlSocket /tmp/test already exists, disabling multiplexing\n'
                 'To example.invalid:repo.git\n   abc..def main -> main')

        def git(repo, *args, **kwargs):
            if args[0] in ('pull', 'push'):
                return noise
            return original_git(repo, *args, **kwargs)

        (self.repos[0][1] / 'base').write_text('dirty')
        for verbose in (False, True):
            with self.subTest(verbose=verbose):
                output = io.StringIO()
                with contextlib.redirect_stdout(output), patch.object(tjik_git, 'git', side_effect=git):
                    tjik_git.synchronize(self.repos, verbose=verbose)
                rendered = output.getvalue()
                self.assertIn('uncommitted changes are not pushed', rendered)
                for name, repo in self.repos:
                    self.assertIn(f'{name}: PUSH OK', rendered)
                    self.assertEqual(str(repo) in rendered, verbose)
                self.assertEqual(noise in rendered, verbose)

    def test_default_cli_reports_failed_git_output(self):
        repo = self.repos[1][1]
        hook = self.root / 'systjik.git/hooks/pre-receive'
        hook.write_text('#!/bin/sh\necho "deliberate remote rejection" >&2\nexit 1\n')
        hook.chmod(0o755)
        self.commit(repo, 'rejected', 'rejected')
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors), \
                patch.object(tjik_git, 'repositories', return_value=self.repos), \
                patch('sys.argv', ['tjik_git.py', 'push']):
            self.assertEqual(tjik_git.main(), 1)
        self.assertIn('systjik: PUSH FAILED', output.getvalue())
        self.assertIn('dotjik: PUSH OK', output.getvalue())
        self.assertIn('deliberate remote rejection', errors.getvalue())
        self.assertIn('pre-receive hook declined', errors.getvalue())

    def test_dry_run_keeps_repository_paths_and_commands(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            tjik_git.synchronize(self.repos, dry_run=True)
        for name, repo in self.repos:
            self.assertIn(f'{name}: {repo}', output.getvalue())
            self.assertIn(f'{name}: git push', output.getvalue())

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
