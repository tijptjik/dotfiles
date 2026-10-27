"""Check decorated terminal rows without changing report or outcome semantics."""
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import tjikup_support
from fleet_update.icons import HookProgress, title_icon
from fleet_update.presentation import ANSI, summary
from tjikup import runtime


class FleetIconTests(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, {'TJIKUP_KITTY_ICONS': '0'})
        env.start()
        self.addCleanup(env.stop)

    def test_terminal_icons_leave_report_and_outcome_intact(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report"
            with patch.dict(os.environ, {"TJIKUP_ICONS": "1", "TJIKUP_COLOR": "1",
                                        "TJIKUP_COLUMNS": "80", "TJIKUP_REPORT_FILE": str(report)}):
                stream = io.StringIO()
                progress = HookProgress(stream=stream, live=True)
                progress.start("python", "Python (environment)", "SYNC")
                progress.finish("python", "Python (environment)", verb="SYNC", note="no changes")
            self.assertGreaterEqual(stream.getvalue().count("\ue73c Python"), 2)
            self.assertEqual(report.read_text(), "SKIP\t✓\tPython (environment)\tno changes\n")
            outcome = summary(stream.getvalue())
            self.assertEqual((outcome.verb, outcome.note), ("SKIP", "no changes"))

    def test_plain_and_disabled_output_have_no_title_icons(self):
        cases = [{"TJIKUP_COLOR": "0", "TERM": "xterm"},
                 {"TJIKUP_COLOR": "1", "TERM": "dumb"},
                 {"TJIKUP_COLOR": "1", "TERM": "xterm", "TJIKUP_ICONS": "0"}]
        for env in cases:
            with self.subTest(env=env), patch.dict(os.environ, env, clear=True):
                stream = io.StringIO()
                HookProgress(stream=stream, live=False).finish("rust", "Rust (packages)", record=False)
                self.assertIn("✓ Rust (packages)", ANSI.sub("", stream.getvalue()))

    def test_coloured_forwarded_rows_have_icons_and_fit_narrow_width(self):
        with patch.dict(os.environ, {"TERM": "xterm", "TJIKUP_COLOR": "1", "TJIKUP_COLUMNS": "40"}, clear=True):
            stream = io.StringIO()
            HookProgress(stream=stream, live=False).finish(
                "fonts", "Assets (fonts)", note="updated", record=False)
            row = ANSI.sub("", stream.getvalue()).rstrip("\n")
            self.assertIn("✓ \uf031 Assets", row)
            self.assertLessEqual(runtime.display_width(row), 39)

    def test_asset_subtypes_and_unknown_services(self):
        self.assertNotEqual(title_icon("Assets (fonts)"), title_icon("Assets (icon cache)"))
        self.assertEqual(title_icon("Fedora (repositories)"), title_icon("Fedora (release)"))
        self.assertEqual(title_icon("New service"), "\uf013")
        for label in ("Google Chrome stable", "Sublime Text", "Obsidian", "Greetjik", "Gitfetch"):
            with self.subTest(label=label):
                self.assertNotEqual(title_icon(label), title_icon("New service"))


if __name__ == "__main__":
    unittest.main()
