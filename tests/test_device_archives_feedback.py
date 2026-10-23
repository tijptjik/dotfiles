import contextlib
import io
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "home/dot_local/lib"))
from device_archives.feedback import Feedback, cells
from device_archives.cli import main


class FeedbackTests(unittest.TestCase):
    def test_numeric_columns_align_with_varying_paths_and_values(self):
        f = Feedback(columns=80)
        f.count = 20
        f.index = 1
        first = f.line("BACKUP", "✓", ".ssh", "26", "11.7 KiB", "verified", "17.8s")
        self.assertIn(" 1/20 ", first)
        self.assertNotIn("[", first)
        f.index = 12
        second = f.line(
            "BACKUP",
            "✓",
            ".var/app/rocks.koreader.KOReader/config/koreader",
            "12,345",
            "9.0 MiB",
            "verified",
            "120.1s",
        )
        for a, b in [("26", "12,345"), ("11.7 KiB", "9.0 MiB"), ("17.8s", "120.1s")]:
            self.assertEqual(first.index(a) + len(a), second.index(b) + len(b))
        self.assertEqual(first.index("verified"), second.index("verified"))
        self.assertEqual(first.index(".ssh"), second.index(".var"))
        self.assertIn("…", second)
        self.assertEqual(cells(first), 79)
        self.assertEqual(cells(second), 79)

    def test_narrow_and_unicode_paths_do_not_wrap(self):
        for columns in (24, 40, 60, 80, 120):
            with self.subTest(columns=columns):
                f = Feedback(columns=columns)
                f.count = 20
                line = f.line(
                    "BACKUP",
                    "✓",
                    ".local/中文資料/背景/long-directory",
                    "123,456",
                    "999.9 GiB",
                    "verified",
                    "99999.9s",
                )
                for part in line.splitlines():
                    self.assertLessEqual(cells(part), columns - 1)
                self.assertIn("999.9 GiB", line)
                self.assertIn("99999.9s", line)

    def test_color_and_plain_output_have_identical_columns(self):
        f = Feedback(columns=80)
        f.count = 20
        line = f.line("SKIP", "✓", ".fonts", "442", "—", "unchanged", "2.7s")
        outputs = []
        for color in (False, True):
            f.color = color
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                f._write(line, "SKIP", "✓")
            outputs.append(re.sub(r"\x1b\[[0-9;]*m", "", output.getvalue()))
        self.assertEqual(outputs[0], outputs[1])

    def test_interrupt_clears_multiline_progress_and_reports_abort(self):
        f = Feedback(columns=60)
        f.terminal = True
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(KeyboardInterrupt):
            with f.folder(".fonts", 1, 20):
                f.event("UPLOAD", ".fonts", "tree.tar.zst.age")
                raise KeyboardInterrupt()
        self.assertIn("\x1b[1A", output.getvalue())
        self.assertIn("ABORT", output.getvalue())
        self.assertNotIn("FAILED", output.getvalue())
        self.assertEqual(f.active_lines, 0)

    def test_cli_interrupt_exits_130_without_traceback(self):
        with (
            patch.object(sys, "argv", ["device-archives", "backup"]),
            patch("device_archives.cli.read_json", side_effect=KeyboardInterrupt()),
            self.assertRaises(SystemExit) as exit,
        ):
            main()
        self.assertEqual(exit.exception.code, 130)
