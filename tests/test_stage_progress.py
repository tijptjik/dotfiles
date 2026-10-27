"""Exercise live progress redraws and bounded Git metric extraction."""
import importlib.util
import os
import re
from unittest.mock import patch
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

HELPER = Path(__file__).resolve().parents[1] / 'home/.chezmoihelpers/stage-progress.py'
spec = importlib.util.spec_from_file_location('stage_progress', HELPER)
progress = importlib.util.module_from_spec(spec)
spec.loader.exec_module(progress)


class ProgressTests(unittest.TestCase):
    def test_fish_function_stages_animate_and_preserve_results(self):
        for code in (0, 7):
            with self.subTest(code=code):
                result = subprocess.run([
                    'fish', '--no-config', '-c',
                    'source $argv[1]; '
                    'function work; sleep 0.5; echo command-output; return $argv[1]; end; '
                    'stage test UPDATE Test work $argv[2]',
                    str(HELPER.with_name('status.fish')), str(code),
                ], capture_output=True, timeout=5,
                    env={**os.environ, 'TJIKUP_COLOR': '1', 'TJIKUP_NO_SPIN': '0',
                         'TERM': 'xterm-256color'})
                self.assertEqual(result.returncode, code, result.stderr)
                self.assertEqual(result.stderr, b'')
                self.assertIn(b'0s', result.stdout)
                self.assertGreaterEqual(len(set(re.findall('[\u2800-\u28ff]', result.stdout.decode()))), 2)
                if code:
                    self.assertIn(b'FAILED', result.stdout)
                    self.assertIn(b'command-output', result.stdout)
                else:
                    self.assertIn('✓'.encode(), result.stdout)
                    self.assertNotIn(b'command-output', result.stdout)

    def test_transfer_bytes_and_latest_phase(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / 'log'
            log.write_text('private arbitrary output\n' + 'x' * 9000 +
                           '\rReceiving objects: 42% (42/100), 197.50 MiB | 550.00 KiB/s\r')
            self.assertEqual(progress.transfer_progress(log),
                             'Download: 42%, 197.50 MiB | 550.00 KiB/s')
            with log.open('a') as stream:
                stream.write('Resolving deltas: 80% (8/10)\r')
            self.assertEqual(progress.transfer_progress(log), 'Resolving deltas: 80%')
            log.write_text('secret token and arbitrary build output\n')
            self.assertEqual(progress.transfer_progress(log), '')

    def test_spinner_updates_then_stops_on_failed_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            log, status = (Path(directory) / name for name in ('log', 'status'))
            log.write_text('Receiving objects: 42% (42/100), 197.50 MiB | 550.00 KiB/s\r')
            status.touch()
            with subprocess.Popen(['python3', str(HELPER), str(log), str(status),
                                   str(os.getpid()), 'INSTALL Notjik'],
                                  stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                  env={**os.environ, 'TJIKUP_COLUMNS': '100'}) as proc:
                try:
                    time.sleep(.45)
                    status.write_text('7\n')
                    output, _ = proc.communicate(timeout=3)
                finally:
                    if proc.poll() is None:
                        proc.kill()
                        proc.wait()
            self.assertEqual(proc.returncode, 0)
            self.assertIn(b'197.50 MiB | 550.00 KiB/s', output)
            self.assertIn(b'INSTALL Notjik', output)
            self.assertGreaterEqual(len(set(re.findall('[\u2800-\u28ff]', output.decode()))), 2)
            self.assertTrue(output.endswith(b'\r\x1b[2K'))
            self.assertNotIn(b'\x1b[?', output)
            self.assertNotIn(b'\x1b]', output)

    def test_fragmented_terminal_queries_are_answered_privately(self):
        relay = progress.TerminalRelay(123)
        stream = (b'\x1b[?2026$p\x1b[?2027$p\x1b[?u'
                  b'\x1b]11;?\x1b\\\x1b[?25l\x1b[=1;1u'
                  b'\x1b[31mvisible\x1b[m\r\x1b[2K')
        with patch.object(progress.os, 'write') as reply:
            output = b''.join(relay.feed(bytes([byte])) for byte in stream)
        self.assertEqual(output, b'\x1b[31mvisible\x1b[m\r\x1b[2K')
        self.assertEqual([call.args[1] for call in reply.call_args_list], [
            b'\x1b[?2026;0$y', b'\x1b[?2027;0$y', b'\x1b[?0u',
            b'\x1b]11;rgb:0000/0000/0000\x1b\\',
        ])
