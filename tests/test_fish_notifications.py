import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'home/dot_config/fish/conf.d/done-notifications.fish'
FUNCTION = ROOT / 'home/dot_config/fish/functions/__fish_done_notify.fish'


@unittest.skipUnless(shutil.which('fish'), 'Fish required')
class FishNotificationTests(unittest.TestCase):
    def run_fish(self, script):
        with tempfile.TemporaryDirectory() as tmp:
            mock = Path(tmp) / 'notify-send'
            mock.write_text('#!/usr/bin/python3\nimport json, sys\nprint(json.dumps(sys.argv[1:]))\n')
            mock.chmod(0o755)
            env = {key: value for key, value in os.environ.items()
                   if key not in ('SSH_CLIENT', 'SSH_TTY')}
            env.update(HOME=tmp, XDG_CONFIG_HOME=tmp, PATH=tmp + ':/usr/bin:/bin')
            return subprocess.run(
                ['fish', '--no-config', '-c', script, '--', str(CONFIG), str(FUNCTION)],
                env=env, check=True, capture_output=True, text=True,
            ).stdout

    def test_kitty_reports_are_fish_and_preserve_literal_text_and_urgency(self):
        output = self.run_fish(r'''
set -g KITTY_WINDOW_ID 42
source $argv[1]
source $argv[1]
source $argv[2]
set -g __done_notification_duration 3456
set -l title 'Done in 5s'
set -l message '-command "quoted"; echo $HOME (touch /unexpected)'
set -l exit_status 0
eval $__done_notification_command
set exit_status 7
set title 'Failed (7) after 5s'
eval $__done_notification_command
set -g __done_notification_urgency_level low
set -g __done_notification_urgency_level_failure normal
set exit_status 0
eval $__done_notification_command
set exit_status 7
eval $__done_notification_command
''')
        calls = [json.loads(line) for line in output.splitlines()]
        self.assertEqual(len(calls), 4)
        for call, urgency in zip(calls, ['normal', 'critical', 'low', 'normal']):
            self.assertIn('--app-name=fish', call)
            self.assertIn('--hint=string:desktop-entry:fish', call)
            self.assertIn('--hint=int:transient:1', call)
            self.assertIn('--expire-time=3456', call)
            self.assertIn('--urgency=' + urgency, call)
            self.assertEqual(call[-3], '--')
            self.assertEqual(call[-1], '-command "quoted"; echo $HOME (touch /unexpected)')
        self.assertEqual(calls[0][-2], 'Done in 5s')
        self.assertEqual(calls[1][-2], 'Failed (7) after 5s')

    def test_explicit_command_and_remote_delivery_are_preserved(self):
        self.run_fish('''
set -g __done_notification_command custom
source $argv[1]
test "$__done_notification_command" = custom; or exit 1
set -e __done_notification_command
set -gx SSH_CLIENT 'remote 123 22'
source $argv[1]
set -q __done_notification_command; and exit 2
set -e SSH_CLIENT
set -gx SSH_TTY /dev/pts/1
source $argv[1]
set -q __done_notification_command; and exit 3
exit 0
''')

    def test_missing_notify_send_keeps_plugin_default(self):
        self.run_fish('''
set -gx PATH /nonexistent
source $argv[1]
set -q __done_notification_command; and exit 1
exit 0
''')
