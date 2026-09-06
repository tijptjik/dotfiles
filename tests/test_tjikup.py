"""Regression checks that never apply dotfiles or contact Git remotes."""

import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "home/dot_local/lib"))

import tjikup
from tjikup.core import UpdateError


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
