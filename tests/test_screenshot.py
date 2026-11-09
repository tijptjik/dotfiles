"""Screenshot clipboard publication waits for the frozen surface to exit."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "native/home/files/.local/bin/screenshot"


class ScreenshotTests(unittest.TestCase):
    def run_capture(self, outcome, save=False, origin="0xabc", dim=True):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bindir = root / "bin"
            bindir.mkdir()
            hyprctl = bindir / "hyprctl"
            hyprctl.write_text("""#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
root = Path(os.environ['HOME'])
args = sys.argv[1:]
with (root / 'hypr-calls').open('a') as log:
    log.write(json.dumps(args) + chr(10))
if args == ['activewindow', '-j']:
    print(json.dumps({'address': os.environ['ORIGIN']}))
elif args == ['monitors', '-j']:
    print(json.dumps([{'name': 'DP-1', 'sdrBrightness': 1.25}]))
elif args[0] == 'dispatch':
    assert args[1] == 'hl.dsp.focus({window=' + chr(34) + 'address:' + os.environ['ORIGIN'] + chr(34) + '})'
    assert (root / 'overlay-closed').exists()
    (root / 'focus-restored').touch()
elif args[0] != 'eval':
    raise AssertionError(args)
""")
            hyprctl.chmod(0o755)
            mock = bindir / "hyprshot"
            mock.write_text("""#!/usr/bin/env python3
import os, time
from pathlib import Path
root = Path(os.environ['HOME'])
(root / 'args').write_text(' '.join(__import__('sys').argv[1:]))
if os.environ['OUTCOME'] != 'success':
    (root / 'overlay-closed').touch()
if os.environ['OUTCOME'] == 'failure':
    raise SystemExit(1)
if os.environ['OUTCOME'] == 'cancel':
    raise SystemExit(0)
# Model Hyprshot returning while its overlay still holds the output pipe.
if os.fork() == 0:
    time.sleep(0.15)
    (root / 'overlay-closed').touch()
    os._exit(0)
os.write(1, bytes.fromhex('89504e470d0a1a0a') + b'synthetic')
os._exit(0)
""")
            mock.chmod(0o755)
            copy = bindir / "wl-copy"
            copy.write_text("""#!/usr/bin/env python3
import os, sys
from pathlib import Path
root = Path(os.environ['HOME'])
assert (root / 'overlay-closed').exists(), 'clipboard published before overlay exit'
if os.environ['ORIGIN']:
    assert (root / 'focus-restored').exists(), 'clipboard before keyboard focus'
assert sys.argv[1:] == ['--type', 'image/png']
(root / 'clipboard').write_bytes(sys.stdin.buffer.read())
""")
            copy.chmod(0o755)
            history = bindir / "cliphist"
            history.write_text("#!/usr/bin/env python3\nimport os,sys\nfrom pathlib import Path\nassert sys.argv[1:] == ['store']\nPath(os.environ['HOME'], 'history').write_bytes(sys.stdin.buffer.read())\n")
            history.chmod(0o755)
            result = subprocess.run([str(SCRIPT), "region", *(["save"] if save else [])],
                env={**os.environ, "HOME": tmp, "XDG_RUNTIME_DIR": tmp,
                     "PATH": str(bindir) + os.pathsep + os.environ["PATH"], "OUTCOME": outcome, "ORIGIN": origin, "SCREENSHOT_DIM": str(int(dim))},
                capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 1 if outcome == "failure" else 0, result.stderr)
            self.assertEqual((root / "clipboard").exists(), outcome == "success")
            self.assertFalse(list(root.glob("screenshot.*.png")))
            calls = [json.loads(line) for line in (root / "hypr-calls").read_text().splitlines()]
            self.assertNotIn(["reload"], calls)
            self.assertEqual((root / "focus-restored").exists(), bool(origin))
            if dim:
                self.assertIn(["eval", 'hl.monitor({output="DP-1",sdrbrightness=1.25})'], calls)
                if origin:
                    self.assertEqual(calls[-1], ["dispatch", 'hl.dsp.focus({window="address:' + origin + '"})'])
            else:
                self.assertFalse(any(call[0] == "eval" for call in calls))
            if outcome == "success":
                self.assertEqual((root / "history").read_bytes(), (root / "clipboard").read_bytes())
                self.assertIn("--raw", (root / "args").read_text())
                saved = list((root / "media/images/screenshots").glob("*.png"))
                self.assertEqual(len(saved), int(save))
                if save:
                    self.assertEqual(saved[0].read_bytes(), (root / "clipboard").read_bytes())
                    self.assertEqual(saved[0].stat().st_mode & 0o777, 0o600)

    def test_copy_waits_for_overlay(self):
        self.run_capture("success")

    def test_no_original_window(self):
        self.run_capture("success", origin="")

    def test_laptop_does_not_adjust_monitor(self):
        self.run_capture("success", dim=False)

    def test_save_and_copy(self):
        self.run_capture("success", save=True)

    def test_cancel_preserves_clipboard(self):
        self.run_capture("cancel")

    def test_failure_preserves_clipboard(self):
        self.run_capture("failure")


if __name__ == "__main__":
    unittest.main()
