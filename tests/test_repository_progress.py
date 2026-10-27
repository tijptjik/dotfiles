"""Repository cells retain ordering and accurately encode operation results."""
import io
import os
import unittest
from unittest.mock import patch

import tjikup_support
from fleet_update.repository_progress import RepositoryProgress
from fleet_update.presentation import ANSI


class RepositoryProgressTests(unittest.TestCase):
    def test_no_color_terminal_rows_fit_narrow_terminal(self):
        with patch.dict(os.environ, {"TJIKUP_COLOR": "0"}):
            panel = RepositoryProgress(stream=io.StringIO(), live=True)
            panel.states["dotjik"] = {"PULL": "changed", "PUSH": "unchanged"}
            self.assertEqual(panel.line("dotjik"), "dotjik    PULL↑  PUSH✓")
            self.assertLess(len(panel.line("tjikos")), 24)
            self.assertTrue(panel.line("tjikos").startswith("tjikOS"))

    def test_colors_for_each_state_and_fixed_order(self):
        with patch.dict(os.environ, {"TJIKUP_COLOR": "1"}):
            panel = RepositoryProgress(stream=io.StringIO(), live=False)
            self.assertEqual(list(panel.states), ["dotjik", "systjik", "tjikos"])
            for state, code in (("pending", "90"), ("running", "1"),
                                ("changed", "94;1"), ("unchanged", "36"),
                                ("failed", "31;1")):
                for verb in ("PULL", "PUSH"):
                    with self.subTest(state=state, verb=verb):
                        panel.update("dotjik", verb, state)
                        line = panel.line("dotjik")
                        self.assertIn(f"\033[{code}m{verb}\033[0m", line)
                        self.assertEqual(ANSI.sub("", line), "dotjik    PULL  PUSH")

    def test_blocked_push_does_not_hide_dirty_failure(self):
        panel = RepositoryProgress(stream=io.StringIO(), live=False)
        panel.update("dotjik", "PUSH", "failed")
        panel.update("dotjik", "PUSH", "blocked")
        self.assertEqual(panel.states["dotjik"]["PUSH"], "failed")

    def test_plain_output_only_emits_three_final_rows(self):
        output = io.StringIO()
        with patch.dict(os.environ, {"TJIKUP_COLOR": "0"}), \
                patch("fleet_update.repository_progress.runtime.section_header"), \
                RepositoryProgress(stream=output, live=False) as panel:
            panel.open()
            panel.update("systjik", "PULL", "running")
            panel.update("systjik", "PULL", "changed")
            panel.update("dotjik", "PULL", "failed")
            panel.settle()
            panel.settle()
        lines = output.getvalue().splitlines()
        self.assertEqual(len(lines), 3)
        self.assertTrue(lines[0].startswith("dotjik    PULL [failed]"))
        self.assertTrue(lines[1].startswith("systjik   PULL [changed]"))
        self.assertTrue(lines[2].endswith("PUSH [disabled]"))
        self.assertNotIn("\033", output.getvalue())

    def test_live_panel_keeps_completed_rows_until_settled(self):
        output = io.StringIO()
        with patch.dict(os.environ, {"TJIKUP_COLOR": "1"}), \
                patch("fleet_update.repository_progress.runtime.section_header"), \
                RepositoryProgress(stream=output, live=True) as panel:
            panel.open()
            panel.update("dotjik", "PULL", "changed")
            panel.update("dotjik", "PUSH", "unchanged")
            self.assertEqual(panel.height, 3)
            panel.settle()
            self.assertEqual(panel.height, 0)
            self.assertFalse(panel.rows)
        self.assertIn("\033[3A", output.getvalue())
        self.assertIn("\033[?25h", output.getvalue())
