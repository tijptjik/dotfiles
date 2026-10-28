"""Commit totals use isolated local Git remotes and synthetic workflow commands."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import tjikup_support
from fleet_update import sync_repo
from fleet_update.workflow import workflow, commit_count


class CommitCountTests(unittest.TestCase):
    def test_pull_rebase_counts_only_incoming_commits_and_push_counts_outgoing(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {
                'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null'}):
            root = Path(temporary)
            remote, seed, checkout = (root / name for name in ('remote.git', 'seed', 'checkout'))

            def git(repo, *args):
                return subprocess.run(['git', '-c', 'user.name=Synthetic', '-c',
                                       'user.email=synthetic@example.invalid', '-C', str(repo), *args],
                                      capture_output=True, text=True, check=True, timeout=10).stdout

            git(root, 'init', '--bare', '--initial-branch=main', str(remote))
            git(root, 'clone', str(remote), str(seed))
            def commit(repo, name):
                (repo / name).write_text('synthetic fixture\n')
                git(repo, 'add', name)
                git(repo, 'commit', '-m', name)
            commit(seed, 'initial')
            git(seed, 'push', '-u', 'origin', 'main')
            git(root, 'clone', str(remote), str(checkout))
            git(checkout, 'config', 'user.name', 'Synthetic')
            git(checkout, 'config', 'user.email', 'synthetic@example.invalid')
            commit(checkout, 'local')
            commit(seed, 'incoming-one')
            commit(seed, 'incoming-two')
            git(seed, 'push')
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(sync_repo(checkout, 'pull'), 0)
                self.assertEqual(sync_repo(checkout, 'pull'), 77)
                self.assertEqual(sync_repo(checkout, 'push'), 0)
                self.assertEqual(sync_repo(checkout, 'push'), 77)
            self.assertEqual(output.getvalue().splitlines(), ['↓2', '↓0', '↑1', '↑0'])
            self.assertEqual(git(checkout, 'rev-parse', 'HEAD'), git(checkout, 'rev-parse', '@{u}'))

    def test_workflow_passes_command_counts_into_repository_panel(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {
                'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null'}):
            root = Path(temporary)
            (root / '.git').mkdir()
            plan = [dict(id=name, command=[sys.executable, '-c', f"print({note!r}); raise SystemExit({code})"],
                         label='Dotjik', verb=verb, skip_codes=[77], needs=[])
                    for name, verb, note, code in (('pull-home', 'PULL', '↓4', 0),
                                                   ('push-home', 'PUSH', '↑0', 77))]
            (root / 'workflow.json').write_text(json.dumps(plan))
            with patch('fleet_update.workflow.__file__', str(root / 'workflow.py')), \
                    patch('fleet_update.fleet_apply.plans'), \
                    patch.dict(os.environ, {'TJIKUP_COLOR': '0', 'TJIKUP_PROGRESS': '0', 'TJIKUP_ICONS': '0'}), \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(workflow(root), 0)
            row = next(line for line in output.getvalue().splitlines() if line.startswith('dotjik'))
            self.assertTrue(row.startswith('dotjik    PULL [changed]  PUSH [unchanged]'))
            self.assertTrue(row.endswith('↓4 ↑0'))

    def test_parser_matches_only_the_requested_operation(self):
        self.assertEqual(commit_count('PULL    ✓ tjikOS    ↓12 · fast-forward\n', 'PULL'), 12)
        self.assertEqual(commit_count('SKIP    ✓ tjikOS    ↑0; no changes\n', 'PUSH'), 0)
        self.assertEqual(commit_count('PULL    ✓ tjikOS    \033[90m↓12 · fast-forward\033[0m\n', 'PULL'), 12)
        self.assertIsNone(commit_count('↓12', 'PUSH'))
        self.assertIsNone(commit_count('fatal: network unavailable', 'PULL'))
