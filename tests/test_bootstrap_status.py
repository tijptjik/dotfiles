"""Bootstrap hooks share Tjikup's status renderer even through piped stdout."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ANSI = re.compile(r'\x1b\[[0-9;]*[A-Za-z]')


class BootstrapStatusTests(unittest.TestCase):
    def test_bash_rows_match_fish_with_colour_and_terminal_width(self):
        for colour in ('0', '1'):
            for width in ('45', '90'):
                env = {**os.environ, 'TJIKUP_COLOR': colour, 'TJIKUP_COLUMNS': width,
                       'TERM': 'xterm-256color'}
                bash = subprocess.run(['bash', '-c',
                    'source "$1"; STAGE_NOTE="best effort" __stage_label SYNC "✓" "System packages"',
                    '--', str(ROOT/'home/.chezmoihelpers/status.sh')],
                    env=env, capture_output=True, text=True, check=True)
                fish = subprocess.run(['fish', '--no-config', '-c',
                    'source $argv[1]; status_msg SYNC "✓" "System packages" "best effort"',
                    str(ROOT/'home/.chezmoihelpers/status.fish')],
                    env=env, capture_output=True, text=True, check=True)
                self.assertEqual(bash.stdout, fish.stdout)
                self.assertEqual('\x1b[' in bash.stdout, colour == '1')
                self.assertLessEqual(len(ANSI.sub('', bash.stdout).strip()), int(width))

    def test_font_hook_emits_skip_row_without_changing_consolidated_fonts(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home/'.local/share/fonts').mkdir(parents=True)
            (home/'.fonts').symlink_to('.local/share/fonts')
            result = subprocess.run(['python3', str(ROOT/'home/.chezmoitemplates/consolidate-fonts.py'),
                '--apply', '--status-helper', str(ROOT/'home/.chezmoihelpers/status.fish')],
                env={**os.environ, 'HOME': tmp, 'TJIKUP_COLOR': '1', 'TERM': 'xterm-256color'},
                capture_output=True, text=True, check=True)
            plain = ANSI.sub('', result.stdout)
            self.assertRegex(plain, r'SKIP\s+✓\s+User fonts\s+no changes')
            self.assertIn('\x1b[', result.stdout)
            self.assertTrue((home/'.fonts').is_symlink())

    def test_bash_progress_is_replaced_across_renderer_processes(self):
        result = subprocess.run(['bash', '-c',
            'source "$1"; STAGE_NOTE="best effort" stage packages SYNC "System packages" true',
            '--', str(ROOT/'home/.chezmoihelpers/status.sh')],
            env={**os.environ, 'TJIKUP_COLOR': '1', 'TERM': 'xterm-256color', 'TJIKUP_NO_SPIN': '1'},
            capture_output=True, check=True)
        self.assertIn(b'\r\x1b[2K', result.stdout)
        self.assertEqual(result.stdout.count(b'\n'), 1)
