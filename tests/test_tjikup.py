"""Regression checks that never apply dotfiles or contact Git remotes."""

import contextlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "home/dot_local/lib"))

import tjikup_support
import fleet_update as tjikup
from fleet_update.core import UpdateError
from fleet_update.propagators.zed import update_template


class ZedPropagationTests(unittest.TestCase):
    def propagate(self, source_text, target_text):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target, output = (root / name for name in ("source", "target", "output"))
            source.write_text(source_text)
            target.write_text(target_text)
            update_template(source, target, output)
            return output.read_text()

    def test_missing_settings_preserved_while_shared_scalar_updates(self):
        source = '''{
  // Settings not yet applied on this host.
  "markdown_preview": {"limit_content_width": false},
  "lsp": {"biome": {"binary": {
    "path": "{{ .chezmoi.homeDir }}/.bun/bin/biome",
    "arguments": ["lsp-proxy"]
  }}},
  "font_size": 14
}'''
        updated = self.propagate(source, '{"lsp": {}, "font_size": 16}')
        self.assertEqual(updated, source.replace('"font_size": 14', '"font_size": 16'))

    def test_incompatible_structure_still_fails(self):
        for target in ('{"setting": null}', '{"setting": false}'):
            with self.subTest(target=target), self.assertRaises(UpdateError):
                self.propagate('{"setting": ["value"]}', target)

    def test_shorter_live_array_preserves_missing_source_entries(self):
        self.assertEqual(
            self.propagate('{"models": ["a", "b"]}', '{"models": ["c"]}'),
            '{"models": ["c", "b"]}',
        )


class DirtyStateTests(unittest.TestCase):
    def test_dirty_repository_is_a_failure(self):
        for name, label in (("chezmoi", "Chezmoi"), ("chezetc", "Chezetc")):
            with self.subTest(name=name), \
                    patch.object(tjikup, "git_dirty_paths", return_value=["a", "b"]), \
                    self.assertRaisesRegex(UpdateError, f"Dirty {label}: 2 files"):
                repo = Path("/tmp") / name
                tjikup.warn_dirty_files(repo, repo)

    def test_clean_repository_passes(self):
        with patch.object(tjikup, "git_dirty_paths", return_value=[]):
            tjikup.warn_dirty_files(Path("/tmp/repo"), Path("/tmp/repo"))

    def test_status_failure_is_not_clean(self):
        with patch.object(tjikup.subprocess, "run", return_value=Mock(returncode=1)), \
                self.assertRaisesRegex(UpdateError, "cannot determine dirty status"):
            tjikup.git_dirty_paths(Path("/tmp/repo"))


class PrerequisiteTests(unittest.TestCase):
    def test_toml_check_uses_chezetc_python_from_path(self):
        with patch.object(tjikup.shutil, "which", return_value="/usr/bin/python3"), \
                patch.object(tjikup.subprocess, "run") as command:
            command.return_value.returncode = 0
            self.assertTrue(tjikup.has_python_modules("tomli", "tomli_w"))
            self.assertEqual(command.call_args.args[0],
                             ["/usr/bin/python3", "-c", "import tomli; import tomli_w"])
            command.return_value.returncode = 1
            self.assertFalse(tjikup.has_python_modules("tomli", "tomli_w"))

    def test_missing_python_reports_unavailable(self):
        with patch.object(tjikup.shutil, "which", return_value=None):
            self.assertFalse(tjikup.has_python_modules("tomli", "tomli_w"))


class ApplyTests(unittest.TestCase):
    def run_apply(self, returncode, warning=False):
        result = subprocess.CompletedProcess(
            ["chezmoi", "apply"], returncode, "",
            tjikup.CHEZMOI_CONFIG_WARNING if warning else "",
        )
        with patch.object(tjikup.subprocess, "run", return_value=result), \
                patch.object(tjikup, "stage_label"), \
                contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            return tjikup.run_chezmoi_apply(Path("."), result.args, {})

    def test_success(self):
        self.assertTrue(self.run_apply(0))

    def test_warning_stops_followup(self):
        self.assertFalse(self.run_apply(0, warning=True))

    def test_failure_with_or_without_warning_raises(self):
        for warning in (False, True):
            with self.subTest(warning=warning), self.assertRaises(UpdateError):
                self.run_apply(1, warning=warning)


@unittest.skipUnless(shutil.which("chezmoi"), "chezmoi is not installed")
class ConflictIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="tjikup-conflicts-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "source"
        self.destination = self.root / "destination"
        self.source.mkdir()
        self.destination.mkdir()
        config = self.root / "chezmoi.toml"
        config.write_text("")
        self.command = [
            "chezmoi", "apply", "--config", str(config),
            "--source", str(self.source), "--destination", str(self.destination),
            "--persistent-state", str(self.root / "state.boltdb"),
            "--cache", str(self.root / "cache"),
        ]

    def test_skips_multiple_conflicts_and_applies_clean_changes(self):
        for name in ("a-conflict", "b-conflict", "z-clean"):
            (self.source / name).write_text("original\n")
        subprocess.run(self.command, check=True, capture_output=True, timeout=10)
        for name in ("a-conflict", "b-conflict"):
            (self.destination / name).write_text("local edits\n")

        for tty in (False, True):
            with self.subTest(tty=tty):
                expected = f"updated {tty}\n"
                for name in ("a-conflict", "b-conflict", "z-clean", "new-file"):
                    (self.source / name).write_text(expected)
                with contextlib.redirect_stdout(io.StringIO()), \
                        patch.object(tjikup.sys.stdout, "isatty", return_value=tty):
                    self.assertTrue(tjikup.run_chezmoi_apply(
                        self.root, self.command, dict(os.environ), skip_conflicts=True,
                    ))
                for name in ("a-conflict", "b-conflict"):
                    self.assertEqual((self.destination / name).read_text(), "local edits\n")
                for name in ("z-clean", "new-file"):
                    self.assertEqual((self.destination / name).read_text(), expected)

    def test_other_apply_errors_still_fail(self):
        (self.source / "broken.tmpl").write_text('{{ fail "intentional error" }}')
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()), \
                self.assertRaises(UpdateError):
            tjikup.run_chezmoi_apply(
                self.root, self.command, dict(os.environ), skip_conflicts=True,
            )


class RepositorySyncTests(unittest.TestCase):
    def test_pull_classifies_actual_head_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / ".git").mkdir()
            for after, expected in (("old", 77), ("new", 0)):
                with self.subTest(after=after), \
                        patch.object(tjikup, "git_dirty_paths", return_value=[]), \
                        patch.object(tjikup, "git_ref", side_effect=["old", after]), \
                        patch.object(tjikup, "run") as command:
                    self.assertEqual(tjikup.sync_repo(repo, "pull"), expected)
                    command.assert_called_once_with(
                        ["git", "pull", "--rebase", "--no-autostash"], repo, capture_output=True)

    def test_dirty_work_blocks_pull_and_push_before_mutations(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / ".git").mkdir()
            for action in ("pull", "push"):
                with self.subTest(action=action), \
                        patch.object(tjikup, "git_dirty_paths", return_value=["personal"]), \
                        patch.object(tjikup, "run") as command, \
                        self.assertRaisesRegex(UpdateError, "Dirty"):
                    try:
                        tjikup.sync_repo(repo, action)
                    finally:
                        command.assert_not_called()

    def test_second_sync_waits_for_the_same_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / ".git").mkdir()
            started = threading.Event()
            completed = threading.Event()

            def run_pull(*_args, **_kwargs):
                started.set()

            with (repo / ".git" / "tjikup-sync.lock").open("a") as lock, \
                    patch.object(tjikup, "run", side_effect=run_pull), \
                    patch.object(tjikup, "git_dirty_paths", return_value=[]), \
                    patch.object(tjikup, "git_ref", return_value="head"):
                tjikup.fcntl.flock(lock, tjikup.fcntl.LOCK_EX)
                worker = threading.Thread(
                    target=lambda: (tjikup.sync_repo(repo, "pull"), completed.set())
                )
                worker.start()
                self.assertFalse(started.wait(0.1))
                tjikup.fcntl.flock(lock, tjikup.fcntl.LOCK_UN)
                self.assertTrue(completed.wait(1))
                worker.join()
            self.assertTrue(started.is_set())


class PropagationTests(unittest.TestCase):
    def test_later_failure_leaves_all_sources_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first"
            second = root / "second"
            first.write_text("original first")
            second.write_text("original second")
            good = Mock(source=first, target=first, optional=False)
            good.name = "first"
            good.propagate.side_effect = lambda source, target, output: output.write_text("updated")
            bad = Mock(source=second, target=second, optional=False)
            bad.name = "second"
            bad.propagate.side_effect = UpdateError("invalid configuration")
            with contextlib.ExitStack() as stack:
                stack.enter_context(patch.dict(os.environ))
                stack.enter_context(patch.object(sys, "argv", ["tjikup"]))
                stack.enter_context(patch.object(tjikup, "discover_propagators", return_value=[good, bad]))
                for name in ("stage_label",):
                    stack.enter_context(patch.object(tjikup, name))
                command = stack.enter_context(patch.object(tjikup.subprocess, "run"))
                self.assertEqual(tjikup.capture(root), 1)
                command.assert_not_called()
            self.assertEqual(first.read_text(), "original first")
            self.assertEqual(second.read_text(), "original second")


if __name__ == "__main__":
    unittest.main()
