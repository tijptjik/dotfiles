"""Regression checks that never apply dotfiles or contact Git remotes."""

import contextlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "home/dot_local/lib"))

import tjikup
from tjikup.core import UpdateError
from tjikup.propagators.zed import update_template


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
                stack.enter_context(patch.object(tjikup, "find_repo", return_value=root))
                stack.enter_context(patch.object(tjikup, "create_report_file", return_value=root / "report"))
                stack.enter_context(patch.object(tjikup, "discover_propagators", return_value=[good, bad]))
                for name in ("splash", "repo_header", "section_header", "run_checks", "stage_label"):
                    stack.enter_context(patch.object(tjikup, name))
                command = stack.enter_context(patch.object(tjikup.subprocess, "run"))
                self.assertEqual(tjikup.main(), 1)
                command.assert_not_called()
            self.assertEqual(first.read_text(), "original first")
            self.assertEqual(second.read_text(), "original second")


if __name__ == "__main__":
    unittest.main()
