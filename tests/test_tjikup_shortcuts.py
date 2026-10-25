"""Exercise Fish shortcuts without running live updates or SSH."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FUNCTIONS = ROOT / "home/dot_config/fish/functions"


class ShortcutTests(unittest.TestCase):
    def run_shortcut(self, target, host, arguments=(), bypass=True):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            scripts = {
                "hostname": '#!/bin/sh\nprintf "%s\\n" "$TEST_HOST"\n',
                "tjikup": '#!/usr/bin/python3\nimport json, sys\nprint(json.dumps(sys.argv[1:]))\nsys.exit(7)\n',
                "ssh": '#!/usr/bin/python3\nimport json, subprocess, sys\nprint(json.dumps(sys.argv[1:]), flush=True)\nsys.exit(subprocess.call(["fish", "--no-config", "-c", sys.argv[-1]]))\n',
            }
            if bypass:
                scripts["mullvad-exclude"] = '#!/bin/sh\necho bypass\nexec "$@"\n'
            for name, content in scripts.items():
                script = directory / name
                script.write_text(content)
                script.chmod(0o755)
            environment = dict(os.environ, HOME=temporary, TEST_HOST=host,
                               PATH=f"{temporary}:/usr/bin:/bin")
            result = subprocess.run(
                ["fish", "--no-config", "-c",
                 'set -p fish_function_path "$argv[1]"; set -e argv[1]; $argv',
                 "--", str(FUNCTIONS), target + "tjikup", *arguments],
                env=environment, text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 7, result.stderr)
            return result.stdout.splitlines()

    def test_same_host_runs_locally_and_preserves_status(self):
        for host in ("fi", "li", "si"):
            with self.subTest(host=host):
                self.assertEqual(self.run_shortcut(host, host, ["--dry-run"]),
                                 ['["--dry-run"]'])

    def test_remote_destinations_pty_and_argument_round_trip(self):
        arguments = ["--dry-run", "a b", "", "a'b", '$HOME; echo injected',
                     "(touch /tmp/never-run-tjikup)", "line\nbreak", "雪"]
        for target, destination in (("fi", "io@fi.local"), ("li", "io@li.local"),
                                    ("si", "m@ssh.type.hk")):
            with self.subTest(target=target):
                lines = self.run_shortcut(target, "other", arguments)
                if target == "si":
                    self.assertEqual(lines.pop(0), "bypass")
                ssh_arguments = json.loads(lines[0])
                self.assertEqual(ssh_arguments[:2], ["-t", "-x"])
                self.assertEqual(ssh_arguments[-2], destination)
                self.assertEqual(json.loads(lines[1]), arguments)

    def test_shortcuts_suppress_generic_done_notification(self):
        result = subprocess.run(
            ["fish", "--no-config", "-c",
             'source "$argv[1]"; for name in tjikup sitjikup litjikup fitjikup; '
             'string match -rq -- "$__done_exclude[-1]" "$name --dry-run"; '
             'or exit 1; end; '
             'string match -rq -- "$__done_exclude[-1]" "echo tjikup"; and exit 1; exit 0',
             "--", str(ROOT / "home/dot_config/fish/conf.d/tjikup-notifications.fish")],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
