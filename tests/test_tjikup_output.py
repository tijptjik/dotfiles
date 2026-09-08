"""Exercise apply output with a real terminal, without applying live dotfiles."""

import contextlib
import io
import os
from pathlib import Path
import pty
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
    def test_terminal_apply_uses_plain_status_output(self):
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
    'source $argv[1]; stage test SYNC Test sleep 0.05',
    '--', str(repo / 'home/.chezmoihelpers/status.fish'),
], dict(__import__('os').environ))
tjikup.run_stream([sys.executable, '-c',
    'import sys; print("prompt-on-stderr", file=sys.stderr, flush=True); print(input())',
], repo)
"""
        with subprocess.Popen(
            [sys.executable, "-B", "-c", code, str(REPO)],
            stdin=slave, stdout=slave, stderr=slave,
            env={**os.environ, "PYTHONPATH": str(REPO / "home/dot_local/lib")},
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
        self.assertIn("SYNC    ✓ Test".encode(), output)
        self.assertIn(b"confirmed", output)
        self.assertNotIn(b"\x1b[?2026", output)
        self.assertNotIn(b"\x1b[?2027", output)
        self.assertNotIn(b"\x1b]11;", output)


if __name__ == "__main__":
    unittest.main()
