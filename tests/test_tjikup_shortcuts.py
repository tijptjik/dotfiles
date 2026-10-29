"""Exercise Fish shortcuts without running live updates or SSH."""
import json
import os
from pathlib import Path
import pty
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FUNCTIONS = ROOT / "native/home/files/.config/fish/functions"


class ShortcutTests(unittest.TestCase):
    def run_shortcut(self, target, host, arguments=(), bypass=True, report=False,
                     broken_transfer=False, columns=None, update_status=7):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            scripts = {
                "hostname": '#!/bin/sh\nprintf "%s\\n" "$TEST_HOST"\n',
                "tjikup": '''#!/usr/bin/python3
import json, os, sys
if sys.argv[1:3] == ['workflow','timing']:
    os.execv(os.environ['NATIVE_TJIKUP'],[os.environ['NATIVE_TJIKUP'],*sys.argv[1:]])
print(json.dumps(sys.argv[1:]))
if os.environ.get("TEST_REPORT"):
    with open(os.environ["TJIKUP_TIMING_EXPORT"], "x") as stream:
        json.dump({"tasks": [{"id": "real-result", "state": "failed"}]}, stream)
sys.exit(int(os.environ["UPDATE_STATUS"]))
''',
            }
            transport = '''#!/usr/bin/python3
import json, os, subprocess, sys
if "-t" in sys.argv:
    print(json.dumps(sys.argv[1:]), flush=True)
elif os.environ.get("BROKEN_TRANSFER"):
    print("connection lost", file=sys.stderr)
    sys.exit(255)
sys.exit(subprocess.call(["fish", "--no-config", "-c", sys.argv[-1]]))
'''
            scripts.update(ssh=transport, **{'fleet-ssh': transport})
            if bypass:
                scripts["mullvad-exclude"] = '#!/bin/sh\nif [ "$2" = -t ]; then echo bypass; fi\nexec "$@"\n'
            for name, content in scripts.items():
                script = directory / name
                script.write_text(content)
                script.chmod(0o755)
            environment = dict(os.environ, HOME=temporary, TEST_HOST=host,
                               XDG_STATE_HOME=str(directory / 'state'),
                               UPDATE_STATUS=str(update_status), NATIVE_TJIKUP=os.environ['TJIKUP_BINARY'],
                               PATH=f"{temporary}:/usr/bin:/bin")
            if report:
                environment['TEST_REPORT'] = '1'
            if broken_transfer:
                environment['BROKEN_TRANSFER'] = '1'
            master = slave = None
            if columns:
                master, slave = pty.openpty()
                environment.update(TERM='xterm-256color', TJIKUP_COLUMNS=str(columns))
            result = subprocess.run(
                ["fish", "--no-config", "-c",
                 'set -p fish_function_path "$argv[1]"; set -e argv[1]; $argv',
                 "--", str(FUNCTIONS), target + "tjikup", *arguments],
                env=environment, text=True, stdout=slave if columns else subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if columns:
                os.close(slave)
                output = bytearray()
                try:
                    while block := os.read(master, 4096):
                        output.extend(block)
                except OSError:
                    pass  # PTY signals EOF with EIO after the writer closes.
                finally:
                    os.close(master)
                result.stdout = output.decode()
            self.assertEqual(result.returncode, update_status, result.stderr)
            if report and not broken_transfer:
                cached = list((directory / 'state/tjikup/logs').glob('*/timings.json'))
                self.assertEqual(len(cached), 1, result.stderr)
                self.assertEqual(json.loads(cached[0].read_text()),
                                 {'tasks': [{'id': 'real-result', 'state': 'failed'}]})
                self.assertEqual(cached[0].stat().st_mode & 0o777, 0o600)
                self.assertEqual(cached[0].parent.stat().st_mode & 0o777, 0o700)
                self.assertNotIn('REPORT', result.stdout)
                self.assertNotIn('Task timings:', result.stdout)
                self.assertFalse(Path('/tmp/tjikup-' + cached[0].parent.name + '.json').exists())
            elif broken_transfer:
                self.assertNotIn('Task timings:', result.stdout)
                # The exported report stays available for recovery after a
                # failed transfer; clean up only this test's own artifact.
                for cached in (directory / 'state/tjikup/logs').glob('*'):
                    Path('/tmp/tjikup-' + cached.name + '.json').unlink(missing_ok=True)
            return result.stdout.splitlines()

    def test_remote_reports_survive_failed_updates_without_replaying_them(self):
        for target in ('fi', 'li', 'si'):
            with self.subTest(target=target):
                rows = self.run_shortcut(target, 'other', ['quoted arg'], report=True)
                self.assertEqual(rows.count('["quoted arg"]'), 1)

    def test_report_transfer_failure_preserves_update_status_and_emits_no_link(self):
        self.run_shortcut('si', 'other', report=True, broken_transfer=True)

    def test_successful_remote_update_keeps_timings_private_and_silent(self):
        for columns in (24, 80):
            with self.subTest(columns=columns):
                self.run_shortcut('si', 'other', report=True, columns=columns, update_status=0)

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
                if target == "si":
                    self.assertEqual(ssh_arguments[:2], ["-t", "-x"])
                    self.assertEqual(ssh_arguments[-2], destination)
                else:
                    self.assertEqual(ssh_arguments[:2], [target, "-t"])
                self.assertEqual(json.loads(lines[1]), arguments)

    def test_shortcuts_suppress_generic_done_notification(self):
        result = subprocess.run(
            ["fish", "--no-config", "-c",
             'source "$argv[1]"; for name in tjikup sitjikup litjikup fitjikup; '
             'string match -rq -- "$__done_exclude[-1]" "$name --dry-run"; '
             'or exit 1; end; '
             'string match -rq -- "$__done_exclude[-1]" "echo tjikup"; and exit 1; exit 0',
             "--", str(ROOT / "native/home/files/.config/fish/conf.d/tjikup-notifications.fish")],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
