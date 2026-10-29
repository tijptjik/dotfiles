"""Fleet shell notification exclusion policy."""
import unittest
import shutil
import subprocess
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]

class FishNotificationTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('fish'), 'Fish required')
    def test_fish_exclusion_is_scoped_and_idempotent(self):
        script = '''
set -g __done_exclude custom
source $argv[1]
source $argv[1]
test (count $__done_exclude) -eq 2; or exit 1
contains custom $__done_exclude; or exit 2
for cmd in tjikup 'tjikup --dry-run' 'command tjikup' '/home/io/.local/bin/tjikup'
    string match -qr -- $__done_exclude[2] $cmd; or exit 3
end
for cmd in tjikup-other 'echo tjikup' 'sleep 10'
    string match -qr -- $__done_exclude[2] $cmd; and exit 4
end
exit 0
'''
        subprocess.run(['fish', '--no-config', '-c', script, '--', str(REPO / 'native/home/files/.config/fish/conf.d/tjikup-notifications.fish')], check=True)
