"""Preparation feedback stays live without changing native outcomes or reports."""
import contextlib
import io
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import tjikup_support
from fleet_update.preparation import prepare
from fleet_update import fleet_apply


class PreparationTests(unittest.TestCase):
    def test_heartbeat_arrives_before_action_finishes_and_stops_afterward(self):
        heartbeat = threading.Event()

        class Output(io.StringIO):
            def write(self, value):
                result = super().write(value)
                if "elapsed" in value:
                    heartbeat.set()
                return result

        output = Output()
        with tempfile.TemporaryDirectory() as temporary:
            report = Path(temporary) / "report"
            with patch.dict(os.environ, {"TJIKUP_PROGRESS": "1", "TERM": "xterm",
                                        "TJIKUP_COLOR": "0", "TJIKUP_REPORT_FILE": str(report)}), \
                    contextlib.redirect_stdout(output):
                def action():
                    self.assertIn("starting", output.getvalue())
                    self.assertTrue(heartbeat.wait(2), "no feedback while action is running")
                    print("native diagnostic", flush=True)
                    return 0

                result, seconds = prepare("Chezmoi files", "APPLY", action, interval=0.02)
                self.assertFalse(report.exists())
            self.assertEqual(result, 0)
            self.assertGreater(seconds, 0)
        lines = output.getvalue().splitlines()
        self.assertIn("native diagnostic", lines)
        self.assertIn("✓", lines[-1])
        self.assertNotIn("\x1b", output.getvalue())

    def test_plain_output_and_failed_or_stopped_actions(self):
        for outcome, expected in [(0, "✓"), (78, "WARN"), (3, "FAILED"),
                                  (RuntimeError("failure"), "FAILED"), (KeyboardInterrupt(), "STOP")]:
            with self.subTest(outcome=outcome):
                output = io.StringIO()
                def action():
                    if isinstance(outcome, BaseException):
                        raise outcome
                    return outcome

                with patch.dict(os.environ, {"TJIKUP_PROGRESS": "0", "TJIKUP_COLOR": "0"}), \
                        contextlib.redirect_stdout(output):
                    if isinstance(outcome, BaseException):
                        with self.assertRaises(type(outcome)):
                            prepare("Chezmoi files", "APPLY", action, exit_code=True)
                    else:
                        result, _ = prepare("Chezmoi files", "APPLY", action, exit_code=True)
                        self.assertEqual(result, outcome)
                lines = output.getvalue().splitlines()
                self.assertEqual(len(lines), 2)
                self.assertIn(expected, lines[-1])

    def test_config_refresh_keeps_stop_code_and_never_prepares_hooks(self):
        output = io.StringIO()
        with patch.dict(os.environ, {"TJIKUP_PROGRESS": "0", "TJIKUP_COLOR": "0", "FLEET_JOBS": "4"}), \
                patch.object(fleet_apply, "plans", return_value=([], [], None)), \
                patch("fleet_update.apply_files", return_value=78), \
                patch.object(fleet_apply, "HookTasks") as hooks, contextlib.redirect_stdout(output):
            self.assertEqual(fleet_apply.apply(Path("/unused")), 78)
            hooks.assert_not_called()
        self.assertIn("Chezmoi files", output.getvalue())
        self.assertIn("WARN", output.getvalue())


if __name__ == "__main__":
    unittest.main()
