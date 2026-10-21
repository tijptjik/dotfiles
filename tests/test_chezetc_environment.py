"""Check the managed chezetc fix without touching an installed wrapper."""

import contextlib
import io
import os
from pathlib import Path
import runpy
import shlex
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "home/dot_local/lib"))
import tjikup


HOOK = Path(__file__).resolve().parents[1] / "home/.chezmoiscripts/run_after_34-configure-chezetc.py"
configure_chezetc = runpy.run_path(str(HOOK))["configure_chezetc"]


class ChezetcEnvironmentTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("fish"), "Fish required")
    def test_colours_survive_wrapper_environment_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sudo = root / "sudo"
            # Model sudo's allowlist without privilege escalation or live apply.
            sudo.write_text(f"#!{sys.executable}\n" + '''
import os, sys
names = sys.argv[1].split('=', 1)[1].split(',')
env = {name: os.environ[name] for name in ['PATH', 'TERM', *names] if name in os.environ}
os.execvpe(sys.argv[3], sys.argv[3:], env)
''')
            sudo.chmod(0o755)
            wrapper = root / "chezetc"
            wrapper.write_text("#!/bin/bash\nsudo --preserve-env=PATH,EDITOR,VISUAL -- " + shlex.join([
                shutil.which("fish"), "--no-config", "-c",
                'source $argv[1]; section_header Packages; status_msg SYNC ✓ Test; '
                'printf "preflight=%s report=%s\\n" "$TJIKUP_SKIP_PREFLIGHT" "$TJIKUP_REPORT_FILE"',
                "--", str(REPO / "home/.chezmoihelpers/status.fish"),
            ]) + "\n")
            wrapper.chmod(0o755)
            environment = {
                **os.environ, "PATH": f"{root}:{os.environ['PATH']}",
                "TERM": "xterm-256color", "TJIKUP_SKIP_PREFLIGHT": "1",
                "TJIKUP_REPORT_FILE": str(root / "report"),
            }
            def output(terminal):
                captured = io.StringIO()
                with contextlib.redirect_stdout(captured), patch.object(captured, "isatty", return_value=terminal):
                    tjikup.run_stream([str(wrapper)], root, env=environment)
                return captured.getvalue()

            self.assertNotIn("\x1b", output(True))
            configure_chezetc(wrapper)
            coloured = output(True)
            self.assertRegex(coloured, r"\x1b\[[0-9;]+mSYNC")
            self.assertIn(f"preflight=1 report={root / 'report'}", coloured)
            self.assertIn("SYNC\t✓\tTest", (root / "report").read_text())
            self.assertNotIn("\x1b", output(False))

    def test_upstream_allowlist_is_extended_idempotently(self):
        with tempfile.TemporaryDirectory() as directory:
            wrapper = Path(directory) / "chezetc"
            source = (
                "#!/bin/bash\n# local customization\n"
                "sudo --preserve-env=PATH,EDITOR,VISUAL -- \\\n"
                '    chezmoi "$@"\n'
            )
            wrapper.write_text(source)
            wrapper.chmod(0o755)
            configure_chezetc(wrapper)
            expected = source.replace(
                "PATH,EDITOR,VISUAL",
                "PATH,EDITOR,VISUAL,TJIKUP_COLOR,TJIKUP_NO_SPIN,"
                "TJIKUP_REPORT_FILE,TJIKUP_SKIP_PREFLIGHT",
            )
            self.assertEqual(wrapper.read_text(), expected)
            self.assertEqual(wrapper.stat().st_mode & 0o777, 0o755)
            before = wrapper.stat().st_mtime_ns
            configure_chezetc(wrapper)
            self.assertEqual(wrapper.read_text(), expected)
            self.assertEqual(wrapper.stat().st_mtime_ns, before)

    def test_partial_patch_and_custom_allowlist_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            wrapper = Path(directory) / "chezetc"
            wrapper.write_text("sudo --preserve-env=PATH,CUSTOM,TJIKUP_COLOR -- chezmoi\n")
            configure_chezetc(wrapper)
            self.assertEqual(wrapper.read_text(), (
                "sudo --preserve-env=PATH,CUSTOM,TJIKUP_COLOR,TJIKUP_NO_SPIN,"
                "TJIKUP_REPORT_FILE,TJIKUP_SKIP_PREFLIGHT -- chezmoi\n"
            ))

    def test_missing_installation_is_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            configure_chezetc(Path(directory) / "missing")

    def test_unknown_wrapper_fails_without_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            wrapper = Path(directory) / "chezetc"
            source = "#!/bin/bash\nsudo chezmoi\n"
            wrapper.write_text(source)
            with self.assertRaisesRegex(RuntimeError, "unrecognized sudo"):
                configure_chezetc(wrapper)
            self.assertEqual(wrapper.read_text(), source)
