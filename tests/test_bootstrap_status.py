"""Bootstrap hooks share Tjikup's status renderer even through piped stdout."""
import os
import pty
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
            self.assertRegex(plain, r'SKIP\s+✓\s+Assets \(user fonts\)\s+no changes')
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

    def test_direct_terminal_stages_do_not_probe_or_consume_input(self):
        # Direct chezmoi apply does not have Tjikup's stdout pipe. Exercise
        # both helpers on a real terminal with stdin supplied separately.
        for shell, filename, script in (
            ('bash', 'status.sh', 'source "$1"; stage test SYNC Test sleep 0.05; read -r answer; printf "answer=%s\\n" "$answer"'),
            ('fish', 'status.fish', 'source $argv[1]; stage test SYNC Test sleep 0.05; read -l answer; printf "answer=%s\\n" "$answer"'),
        ):
            with self.subTest(shell=shell):
                master, slave = pty.openpty()
                try:
                    result = subprocess.run([
                        shell, *(('--no-config',) if shell == 'fish' else ()),
                        '-c', script, '--', str(ROOT / 'home/.chezmoihelpers' / filename),
                    ], input=b'untouched\n', stdout=slave, stderr=slave,
                        env={**os.environ, 'TERM': 'xterm-256color'}, timeout=10)
                    os.close(slave)
                    slave = None
                    output = b''
                    while True:
                        try:
                            chunk = os.read(master, 65536)
                        except OSError:
                            break
                        if not chunk:
                            break
                        output += chunk
                    self.assertEqual(result.returncode, 0, output)
                    self.assertIn(b'answer=untouched', output)
                    self.assertIn('✓ Test'.encode(), ANSI.sub('', output.decode()).encode())
                    self.assertIn(b'\x1b[', output)  # colours are retained
                    self.assertNotIn(b'\x1b[?', output)  # no mode queries
                    self.assertNotIn(b'\x1b]', output)  # no colour queries
                finally:
                    os.close(master)
                    if slave is not None:
                        os.close(slave)
