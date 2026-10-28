"""Preparation feedback stays live without changing native outcomes or reports."""
import contextlib
import io
import os
from pathlib import Path
import tempfile
import threading
import time
import subprocess
import sys
import pty
import re
import select
import unittest
from unittest.mock import patch

import tjikup_support
from fleet_update.preparation import prepare
from fleet_update import fleet_apply
from fleet_update.dag import Task


class PreparationTests(unittest.TestCase):
    def test_native_rows_suspend_spinner_until_final_settlement(self):
        output = io.StringIO()
        with patch.dict(os.environ, {'TJIKUP_PROGRESS': '1', 'TJIKUP_ICONS': '0',
                                    'TJIKUP_COLOR': '0', 'TERM': 'xterm'}), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            def action():
                print('CONFIG  ✓ Bitwarden access token', flush=True)
                # A native command can replace a pending row across writes.
                sys.stdout.write('INSTALL ... Essential packages\r')
                sys.stdout.write('\x1b[2KINSTALL ✓ Essential packages\n')
                print('continue? ', file=sys.stderr, end='', flush=True)
                time.sleep(.25)
                self.assertEqual(output.getvalue().count('Chezmoi'), 1)
                print('yes', file=sys.stderr, flush=True)
                return 0
            prepare('Chezmoi', 'APPLY', action)
        rendered = output.getvalue()
        self.assertEqual(rendered.count('Chezmoi'), 2)  # Initial transient + final.
        native = rendered[rendered.index('CONFIG'):rendered.index('APPLY   ✓')]
        self.assertNotIn('Chezmoi', native)
        self.assertNotIn('\x1b7', native)

    def test_files_and_home_task_rendering_settle_one_chezmoi_row(self):
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {
                'XDG_STATE_HOME': temporary, 'TJIKUP_PROGRESS': '0',
                'TJIKUP_ICONS': '0', 'TJIKUP_COLOR': '0', 'FLEET_JOBS': '4'}), \
                patch.object(fleet_apply, 'plans', return_value=([], [], None)), \
                patch('fleet_update.apply_files', return_value=0) as files, \
                patch.object(fleet_apply.HookTasks, 'prepare', return_value=[
                    Task('home:chezetc-wrapper', None)]) as render, \
                patch.object(fleet_apply, 'run', return_value={}), \
                contextlib.redirect_stdout(output):
            self.assertEqual(fleet_apply.apply(Path('/unused')), 0)
            files.assert_called_once()
            render.assert_called_once()
        rows = output.getvalue().splitlines()
        self.assertEqual(sum('Chezmoi' in row for row in rows), 1)
        self.assertNotIn('Home hooks', output.getvalue())

    def test_spinner_animates_and_yields_to_diagnostics_and_partial_prompts(self):
        tick = threading.Event()

        class Output(io.StringIO):
            def write(self, value):
                result = super().write(value)
                if "\x1b7" in value:
                    tick.set()
                return result

        output = Output()
        with tempfile.TemporaryDirectory() as temporary:
            report = Path(temporary) / "report"
            with patch.dict(os.environ, {"TJIKUP_PROGRESS": "1", "TERM": "xterm",
                                        "TJIKUP_COLOR": "0", "TJIKUP_ICONS": "0", "TJIKUP_REPORT_FILE": str(report)}), \
                    contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                def action():
                    self.assertIn("Chezmoi", output.getvalue())
                    self.assertTrue(tick.wait(2), "spinner did not animate")
                    self.assertEqual(output.getvalue().count("Chezmoi"), 1)
                    print("native diagnostic", flush=True)
                    print("continue? ", end="", file=sys.stderr, flush=True)
                    before = output.getvalue().count("Chezmoi")
                    time.sleep(.3)
                    self.assertEqual(output.getvalue().count("Chezmoi"), before)
                    print("yes", file=sys.stderr, flush=True)
                    return 0

                result, seconds = prepare("Chezmoi", "APPLY", action)
                self.assertFalse(report.exists())
            self.assertEqual(result, 0)
            self.assertGreater(seconds, 0)
        rendered = output.getvalue()
        self.assertIn("native diagnostic", rendered)
        self.assertIn("continue? yes", re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", rendered))
        self.assertEqual(rendered.count("✓ Chezmoi"), 1)
        self.assertIn("\r\x1b[1A", rendered)
        self.assertIn("\x1b[?25h", rendered)
        # No progress thread may continue writing after settlement.
        settled = rendered
        time.sleep(.15)
        self.assertEqual(output.getvalue(), settled)

    def test_native_stderr_prompt_is_visible_before_reading_input(self):
        master, slave = pty.openpty()
        self.addCleanup(os.close, master)
        code = """
from pathlib import Path
import sys
from fleet_update import run_stream
from fleet_update.preparation import prepare
child = "import sys; sys.stderr.write('continue? '); sys.stderr.flush(); answer=input(); print('confirmed:'+answer, file=sys.stderr, flush=True)"
prepare('Chezmoi', 'APPLY', lambda: run_stream([sys.executable, '-c', child], Path.cwd()))
"""
        env = {**os.environ, 'PYTHONPATH': os.pathsep.join(sys.path),
               'TJIKUP_PROGRESS': '1', 'TJIKUP_COLOR': '0', 'TJIKUP_ICONS': '0', 'TERM': 'xterm'}
        output = b''
        with subprocess.Popen([sys.executable, '-B', '-c', code], stdin=slave,
                              stdout=slave, stderr=slave, env=env) as process:
            os.close(slave)
            answered = False
            deadline = time.monotonic() + 5
            try:
                while time.monotonic() < deadline:
                    if select.select([master], [], [], .1)[0]:
                        try:
                            output += os.read(master, 65536)
                        except OSError:
                            break
                        if b'continue? ' in output and not answered:
                            os.write(master, b'yes\n')
                            answered = True
                    if process.poll() is not None:
                        break
                self.assertEqual(process.wait(timeout=1), 0, output.decode())
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
        self.assertTrue(answered, output.decode())
        self.assertIn(b'confirmed:yes', output)
        self.assertEqual(output.count('✓ Chezmoi'.encode()), 1)

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
                            prepare("Chezmoi", "APPLY", action, exit_code=True)
                    else:
                        result, _ = prepare("Chezmoi", "APPLY", action, exit_code=True)
                        self.assertEqual(result, outcome)
                lines = output.getvalue().splitlines()
                self.assertEqual(len(lines), 1)
                self.assertIn(expected, lines[-1])

    def test_config_refresh_keeps_stop_code_and_never_prepares_hooks(self):
        output = io.StringIO()
        with patch.dict(os.environ, {"TJIKUP_PROGRESS": "0", "TJIKUP_COLOR": "0", "FLEET_JOBS": "4"}), \
                patch.object(fleet_apply, "plans", return_value=([], [], None)), \
                patch("fleet_update.apply_files", return_value=78), \
                patch.object(fleet_apply, "HookTasks") as hooks, contextlib.redirect_stdout(output):
            self.assertEqual(fleet_apply.apply(Path("/unused")), 78)
            hooks.assert_not_called()
        self.assertIn("Chezmoi", output.getvalue())
        self.assertIn("WARN", output.getvalue())


if __name__ == "__main__":
    unittest.main()
