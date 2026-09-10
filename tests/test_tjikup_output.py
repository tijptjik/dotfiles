"""Exercise apply output with a real terminal, without applying live dotfiles."""

import contextlib
import io
import os
from pathlib import Path
import pty
import re
import select
import shutil
import subprocess
import sys
import time
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "home/dot_local/lib"))

import tjikup
from tjikup.core import UpdateError


class StreamTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("fish"), "Fish required")
    def test_terminal_settled_rows_keep_colours(self):
        master, slave = pty.openpty()
        self.addCleanup(os.close, master)
        helper = REPO / "home/.chezmoihelpers/status.fish"
        command = [
            "fish", "--no-config", "-c",
            "source $argv[1]; status_msg SYNC ✓ Zed '2 changes'",
            "--", str(helper),
        ]
        with subprocess.Popen(
            command, stdin=slave, stdout=slave, stderr=slave,
            env={**os.environ, "TERM": "xterm-256color"},
        ) as process:
            os.close(slave)
            output = b""
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if select.select([master], [], [], .1)[0]:
                    try:
                        output += os.read(master, 65536)
                    except OSError:
                        break
                if process.poll() is not None:
                    break
            self.assertEqual(process.wait(timeout=1), 0, output)
        self.assertRegex(output, rb"\x1b\[[0-9;]+mSYNC")
        self.assertRegex(output, rb"\x1b\[[0-9;]+m\xe2\x9c\x93")

    @unittest.skipUnless(shutil.which("fish"), "Fish required")
    def test_progress_row_is_replaced_only_for_terminal_output(self):
        helper = REPO / "home/.chezmoihelpers/status.fish"
        script = (
            "source $argv[1]; status_msg UPDATE ... 'Flatpak packages'; "
            "status_msg UPDATE ✓ 'Flatpak packages' 'no changes'"
        )
        for terminal in ("0", "1"):
            with self.subTest(terminal=terminal):
                result = subprocess.run(
                    ["fish", "--no-config", "-c", script, "--", str(helper)],
                    env={**os.environ, "TJIKUP_COLOR": terminal, "TERM": "xterm-256color"},
                    capture_output=True, check=True,
                )
                output = result.stdout.decode()
                if terminal == "1":
                    self.assertIn("\r\x1b[2K", output)
                    self.assertEqual(output.count("\n"), 1)
                else:
                    self.assertNotIn("\x1b", output)
                    self.assertEqual(output.count("\n"), 2)

    @unittest.skipUnless(shutil.which("fish"), "Fish required")
    def test_redirected_status_output_stays_plain(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            tjikup.run_stream([
                "fish", "--no-config", "-c",
                "source $argv[1]; section_header Packages; status_msg SYNC ✓ Test",
                "--", str(REPO / "home/.chezmoihelpers/status.fish"),
            ], REPO, env={**os.environ, "TERM": "xterm-256color", "TJIKUP_COLOR": "1"})
        self.assertIn("SYNC    ✓ Test", output.getvalue())
        self.assertNotIn("\x1b", output.getvalue())

    def test_partial_unicode_output_and_nonzero_exit(self):
        output = io.StringIO()
        command = [sys.executable, "-c", (
            "import os, time; os.write(1, b'\\xe2'); time.sleep(.02); "
            "os.write(1, b'\\x9c\\x93 done'); raise SystemExit(7)"
        )]
        with contextlib.redirect_stdout(output), self.assertRaisesRegex(UpdateError, r"failed \(7\)"):
            tjikup.run_stream(command, REPO)
        self.assertEqual(output.getvalue(), "✓ done")

    def test_timeout(self):
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(UpdateError, "timed out"):
            tjikup.run_stream([sys.executable, "-c", "import time; time.sleep(10)"], REPO, timeout=.1)

    @unittest.skipUnless(shutil.which("fish") and shutil.which("gum"), "Fish and Gum required")
    def test_terminal_apply_keeps_colours_without_terminal_probes(self):
        master, slave = pty.openpty()
        self.addCleanup(os.close, master)
        code = """
import sys
from pathlib import Path
import tjikup
repo = Path(sys.argv[1])
assert sys.stdout.isatty()
tjikup.run_chezmoi_apply(repo, [
    'fish', '--no-config', '-c',
    'source $argv[1]; read -l answer; test "$answer" = skip; or exit 9; '
    'section_header Packages; stage test SYNC Test sleep 0.05',
    '--', str(repo / 'home/.chezmoihelpers/status.fish'),
], dict(__import__('os').environ), skip_conflicts=True)
tjikup.run_stream([sys.executable, '-c',
    'import sys; print("prompt-on-stderr", file=sys.stderr, flush=True); print(input())',
], repo)
"""
        with subprocess.Popen(
            [sys.executable, "-B", "-c", code, str(REPO)],
            stdin=slave, stdout=slave, stderr=slave,
            env={**os.environ, "TERM": "xterm-256color", "PYTHONPATH": str(REPO / "home/dot_local/lib")},
        ) as process:
            os.close(slave)
            output = b""
            replied = False
            deadline = time.monotonic() + 10
            try:
                while time.monotonic() < deadline:
                    if select.select([master], [], [], .1)[0]:
                        try:
                            chunk = os.read(master, 65536)
                        except OSError:
                            break
                        if not chunk:
                            break
                        output += chunk
                        if b"prompt-on-stderr" in output and not replied:
                            os.write(master, b"confirmed\n")
                            replied = True
                    elif process.poll() is not None:
                        break
                self.assertEqual(process.wait(timeout=1), 0, output)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
        plain_output = re.sub(rb"\x1b\[[0-9;]*m", b"", output)
        self.assertIn("SYNC    ✓ Test".encode(), plain_output)
        self.assertRegex(output, rb"\x1b\[[0-9;]+mPackages")
        self.assertRegex(output, rb"\x1b\[[0-9;]+mSYNC")
        self.assertIn(b"confirmed", output)
        self.assertNotIn(b"\x1b[?2026", output)
        self.assertNotIn(b"\x1b[?2027", output)
        self.assertNotIn(b"\x1b]11;", output)


if __name__ == "__main__":
    unittest.main()
