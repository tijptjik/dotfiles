"""Capture status fields must preserve app identity for the native renderer."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from fleet_capture import stage_unchanged

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("TJIKOS_REPO", Path.home() / "code/tjikos")) / "apps/tjikup/target/debug/tjikup"


class CaptureStatusTests(unittest.TestCase):
    @unittest.skipUnless(BINARY.is_file(), "build tjikup first")
    def test_actual_capture_helper_reaches_native_right_hand_status_column(self):
        names = ["Zed", "Herdr", "Solaar", "Fcitx", "Codex", "Zapzap", "Gtk-bookmarks"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            command = [sys.executable, "-B", "-c",
                       "import sys; sys.path.insert(0, sys.argv[1]); "
                       "from fleet_capture import stage_unchanged; "
                       "[stage_unchanged(name, 'no changes · 0.00s') for name in sys.argv[2:]]",
                       str(ROOT / "scripts"), *names]
            config = root / "config.json"
            config.write_text(json.dumps({"version": 2, "recipes": [{
                "id": "capture", "apply": command,
                "display": {"reports": True, "icon": "Chezmoi"}}]}))
            for fallback in (False, True):
                # Exercise both explicit reports and standalone stdout parsing.
                if fallback:
                    command[3] = "import os; os.environ.pop('TJIKUP_REPORT_FILE', None); " + command[3]
                    config.write_text(json.dumps({"version": 2, "recipes": [{
                        "id": "capture", "apply": command, "display": {"reports": True}}]}))
                output = subprocess.run([str(BINARY), "--config", str(config), "--show-skips"],
                                        env={**os.environ, "XDG_STATE_HOME": str(root / "state"),
                                             "TJIKUP_NOTIFY": "0", "TJIKUP_COLOR": "0", "TERM": "dumb"},
                                        capture_output=True, text=True, timeout=10)
                self.assertEqual(output.returncode, 0, output.stderr)
                rows = [line for line in output.stderr.splitlines() if line.startswith("SKIP")]
                self.assertEqual(len(rows), len(names), output.stderr)
                for line, name in zip(rows, names):
                    self.assertRegex(line, rf"^SKIP\s+✓ {name}\s{{8,}}no changes · 0.00s$")
                self.assertEqual(len({len(line) for line in rows}), 1)

    def test_report_and_plain_output_separate_application_from_skip_reason(self):
        names = ["Zed", "Herdr", "Solaar", "Fcitx", "Codex", "Zapzap", "Gtk-bookmarks"]
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "capture.report"
            with patch.dict(os.environ, {"TJIKUP_REPORT_FILE": str(report)}), contextlib.redirect_stdout(io.StringIO()) as output:
                for name in names:
                    stage_unchanged(name, "no changes · 0.00s")
            rows = [line.split("\t") for line in report.read_text().splitlines()]
            self.assertEqual([row[2] for row in rows], names)
            self.assertTrue(all(row[3] == "no changes · 0.00s" for row in rows))
            for line, name in zip(output.getvalue().splitlines(), names):
                content = line.split("✓", 1)[1].strip()
                self.assertEqual(content.split("  ", 1), [name, "no changes · 0.00s"])

    def test_embedded_newlines_cannot_create_spurious_report_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "capture.report"
            with patch.dict(os.environ, {"TJIKUP_REPORT_FILE": str(report)}), contextlib.redirect_stdout(io.StringIO()):
                stage_unchanged("App", "first\nsecond\tpart")
            self.assertEqual(report.read_text().splitlines(), ["SKIP\t✓\tApp\tfirst second part"])
