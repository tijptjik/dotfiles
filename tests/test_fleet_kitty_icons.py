"""Exercise actual image packets, line accounting, and safe terminal fallback."""
import base64
import contextlib
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib

import tjikup_support
from fleet_update.icons import HookProgress
from fleet_update.kitty_icons import KittyIcons, cell_size, centred, herdr_cell_size, styled_cells


class KittyIconTests(unittest.TestCase):
    def test_repository_icon_halves_share_column_zero_in_both_terminals(self):
        for herdr in (False, True):
            with self.subTest(herdr=herdr):
                stream = io.StringIO()
                graphics = KittyIcons(stream, geometry=(13, 26), herdr=herdr)
                with patch('fleet_update.kitty_icons.cell_size', return_value=(13, 26)):
                    graphics.print_text('dotjik', 'dotjik    ✗ PULL   PUSH')
                output = re.sub(r'\x1b_G[^\x1b]*\x1b\\', '', stream.getvalue())
                first, second, _ = output.split('\r\n')
                self.assertNotIn('\x1b[0C', output)
                # Strip colour only: cursor movement must remain visible to
                # this assertion, since CSI 0 C offsets the bottom half by one.
                first = re.sub(r'\x1b\[[0-9;]*m', '', first)
                second = re.sub(r'\x1b\[[0-9;]*m', '', second)
                self.assertTrue(first.startswith('\U0010eeee'))
                self.assertTrue(second.startswith('\U0010eeee'))

    def setUp(self):
        self.env = patch.dict(os.environ, {'TERM': 'xterm-kitty', 'TJIKUP_COLOR': '1',
            'TJIKUP_COLUMNS': '80', 'TJIKUP_ICONS': '1'}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_transmitted_canvas_contains_exact_32px_sprite_and_is_cached(self):
        stream = io.StringIO()
        graphics = KittyIcons(stream)
        with patch('fleet_update.kitty_icons.cell_size', return_value=(13, 26)):
            graphics.print('DONE', '✓', 'Python (environment)', 'ready')
            first = stream.getvalue()
            graphics.print('SKIP', '✓', 'Python (environment)', 'no changes')
        packets = re.findall(r'\x1b_G([^;]*);([^\x1b]*)\x1b\\', first)
        self.assertIn('f=32,o=z,s=52,v=52', packets[0][0])
        self.assertIn('U=1,c=4,r=2,q=2', packets[0][0])
        self.assertTrue(packets[-1][0].endswith('m=0'))
        canvas = zlib.decompress(base64.b64decode(''.join(data for _, data in packets)))
        self.assertEqual(len(canvas), 52 * 52 * 4)
        source = zlib.decompress(base64.b64decode(graphics.sprites['Python']))
        for row in range(32):
            start = ((row + 10) * 52 + 10) * 4
            self.assertEqual(canvas[start:start + 128], source[row * 128:(row + 1) * 128])
        self.assertEqual(canvas[:10 * 52 * 4], bytes(10 * 52 * 4))
        self.assertNotIn('\x1b_G', stream.getvalue()[len(first):])
        self.assertEqual(first.count('\U0010eeee'), 8)

    def test_progress_clears_two_lines_per_task_and_preserves_plain_report(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch('fleet_update.kitty_icons.cell_size', return_value=(13, 26)), \
                patch.dict(os.environ, {'TJIKUP_REPORT_FILE': str(Path(directory) / 'report')}):
            stream = io.StringIO()
            progress = HookProgress(stream=stream, live=True)
            progress.start('python', 'Python (environment)', 'SYNC')
            progress.start('rust', 'Rust (packages)', 'SYNC')
            self.assertEqual(progress.height, 4)
            before = len(stream.getvalue())
            progress.finish('python', 'Python (environment)', verb='SYNC', note='no changes')
            self.assertEqual(progress.height, 2)
            frame = stream.getvalue()[before:]
            self.assertTrue(frame.startswith('\x1b[?2026h\r\x1b[4A'))
            self.assertTrue(frame.endswith('\x1b[?2026l'))
            self.assertNotIn('\x1b[?25h', frame)
            progress.discard('rust')
            self.assertEqual(progress.height, 0)
            self.assertTrue(stream.getvalue().endswith('\x1b[?25h\x1b[?2026l'))
            self.assertEqual((Path(directory) / 'report').read_text(),
                             'SKIP\t✓\tPython (environment)\tno changes\n')

    def test_fallback_for_logs_multiplexers_disabled_or_unknown_geometry(self):
        for env in ({'TJIKUP_COLOR': '0'}, {'TERM': 'xterm'}, {'TMUX': '/socket'},
                    {'STY': 'session'}, {'TJIKUP_ICONS': '0'}, {'TJIKUP_KITTY_ICONS': '0'}):
            with self.subTest(env=env), patch.dict(os.environ, env), \
                    patch('fleet_update.kitty_icons.cell_size', return_value=(13, 26)):
                self.assertIsNone(KittyIcons.available(io.StringIO(), False))
        with patch('fleet_update.kitty_icons.cell_size', return_value=None):
            self.assertIsNone(KittyIcons.available(io.StringIO(), True))

    def test_animation_patches_text_without_erasing_images_or_labels(self):
        for herdr in (False, True):
            with self.subTest(herdr=herdr), \
                    patch('fleet_update.kitty_icons.cell_size', return_value=(13, 26)), \
                    patch('fleet_update.kitty_icons.in_herdr', return_value=herdr):
                stream = io.StringIO()
                progress = HookProgress(stream=stream, live=True)
                with patch('tjikup.progress.time.monotonic', return_value=0):
                    progress.start('python', 'Python (environment)', 'SYNC')
                    progress.start('fedora', 'Fedora (RPM packages)')
                stream.seek(0)
                stream.truncate()
                with patch('tjikup.progress.time.monotonic', return_value=.125):
                    progress._refresh()
                output = stream.getvalue()
                for repaint in ('\x1b_G', '\U0010eeee', '\x1b[2K', '\n', 'Python', 'Fedora'):
                    self.assertNotIn(repaint, output)
                self.assertIn('\x1b[4A', output)
                self.assertIn('\x1b[2A', output)
                self.assertIn('⠙', output)
                self.assertEqual(progress.height, 4)
                if not herdr:
                    self.assertIn('\x1b]66;', output)
                    self.assertIn('\x1b[9G', output)

    def test_detached_children_use_parent_geometry_without_terminal_queries(self):
        with patch.dict(os.environ, {'TJIKUP_CELL_SIZE': '13x26'}), \
                patch('fcntl.ioctl', side_effect=OSError('detached')), \
                patch('builtins.open', side_effect=AssertionError('must not open tty')):
            graphics = KittyIcons.available(io.StringIO(), False)
            self.assertEqual(graphics.geometry, (13, 26))
        for hint in ('0x0', '13x0', '9999x9999', 'garbage'):
            with self.subTest(hint=hint), patch.dict(os.environ, {'TJIKUP_CELL_SIZE': hint}), \
                    patch('fcntl.ioctl', side_effect=OSError('detached')), \
                    patch('builtins.open', side_effect=OSError('no tty')):
                self.assertIsNone(KittyIcons.available(io.StringIO(), False))

    def test_workflow_passes_parent_geometry_to_buffered_children(self):
        from fleet_update.workflow import workflow
        import tjikup
        scripts = Path(__file__).resolve().parents[1] / 'scripts'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '.git').mkdir()
            child = root / 'child.py'
            child.write_text("from fleet_update.icons import HookProgress\n"
                             "p = HookProgress(live=False)\n"
                             "p.finish('check', 'Bitwarden', verb='CHECK', record=False)\n"
                             "p.finish('capture', 'Zed', verb='SKIP', record=False)\n")
            (root / 'workflow.json').write_text(json.dumps([
                {'id': 'samples', 'command': [sys.executable, str(child)], 'summary': False}]))
            env = {'PYTHONPATH': str(scripts) + os.pathsep + str(Path(tjikup.__file__).resolve().parents[1])}
            output = io.StringIO()
            with patch.dict(os.environ, env), \
                    patch('fleet_update.workflow.__file__', str(root / 'workflow.py')), \
                    patch('fleet_update.fleet_apply.plans'), \
                    patch('fleet_update.kitty_icons.cell_size', return_value=(13, 26)), \
                    contextlib.redirect_stdout(output):
                self.assertEqual(workflow(root), 0)
            rendered = output.getvalue()
            self.assertIn('s=52,v=52', rendered)
            self.assertNotIn('\uf132', rendered)
            self.assertNotIn('\uf044', rendered)
            text = re.sub(r'\x1b]66;[^;]*;([^\x1b]*)\x1b\\', r'\1', rendered)
            text = re.sub(r'\x1b\[[0-9;]*m', '', text)
            self.assertIn('Bitwarden', text)
            self.assertIn('Zed', text)

    def test_cell_geometry_uses_controlling_tty_for_forwarded_output(self):
        import struct
        with patch('builtins.open', unittest.mock.mock_open()), \
                patch('fcntl.ioctl', return_value=struct.pack('HHHH', 30, 80, 1040, 780)):
            self.assertEqual(cell_size(io.StringIO()), (13, 26))

    def test_detached_runner_uses_inherited_stderr_without_a_controlling_tty(self):
        import struct
        stderr = unittest.mock.Mock()
        stderr.fileno.return_value = 2
        with patch('fleet_update.kitty_icons.sys.stderr', stderr), \
                patch('builtins.open', side_effect=OSError('no controlling tty')), \
                patch('fcntl.ioctl', return_value=struct.pack('HHHH', 30, 80, 1040, 780)) as ioctl:
            self.assertEqual(cell_size(io.StringIO()), (13, 26))
            self.assertEqual(ioctl.call_args.args[0], 2)

    def test_resize_keeps_artwork_size_and_unknown_services_have_a_sprite(self):
        stream = io.StringIO()
        graphics = KittyIcons(stream)
        for geometry, dimensions in [((13, 26), 's=52,v=52'), ((10, 20), 's=40,v=40')]:
            with patch('fleet_update.kitty_icons.cell_size', return_value=geometry):
                graphics.print('DONE', '✓', 'New service', '')
            self.assertIn(dimensions, stream.getvalue())
        self.assertEqual(len(graphics.images), 2)
        with patch('fleet_update.kitty_icons.cell_size', return_value=None):
            stream.seek(0)
            stream.truncate()
            graphics.print('DONE', '✓', 'New service', '')
            self.assertEqual(stream.getvalue().count('\n'), 2)

    def test_centred_text_keeps_original_size_and_safe_payloads(self):
        rendered = centred(styled_cells('\x1b[97mPython\x1b[0m \x1b[90m(environment)\x1b[0m'))
        chunks = re.findall(r'\x1b]66;s=2:n=1:d=2:v=2:w=1;([^\x1b]*)\x1b\\', rendered)
        self.assertEqual(''.join(chunks).rstrip(), 'Python (environment)')
        self.assertTrue(all(len(chunk) == 2 for chunk in chunks))
        self.assertIn('\x1b[90m', rendered)

    def test_all_bundled_sprites_are_32px_rgba(self):
        from fleet_update.icon_catalog import SERVICE_ICONS
        path = Path(__file__).resolve().parents[1] / 'scripts/fleet_update/icons32.json'
        data = json.loads(path.read_text())
        self.assertEqual(data['size'], 32)
        self.assertTrue(set(SERVICE_ICONS).issubset(data['sprites']))
        for label, encoded in data['sprites'].items():
            with self.subTest(label=label):
                self.assertEqual(len(zlib.decompress(base64.b64decode(encoded))), 32 * 32 * 4)

    def test_application_sprites_do_not_fall_back_to_the_gear(self):
        graphics = KittyIcons(io.StringIO())
        for label in ('Google Chrome stable', 'Sublime Text', 'Obsidian', 'Greetjik', 'Gitfetch',
                      'Assets (icon cache)', 'Assets (Rose Punk icons)'):
            with self.subTest(label=label):
                graphics.image(label, 12, 26)
                self.assertIn((label, 12, 26), graphics.images)
                self.assertNotEqual(graphics.sprites[label], graphics.sprites['*'])
        self.assertNotIn('Pony', graphics.sprites)

    def test_image_has_equal_cell_gaps_before_and_after_in_both_terminals(self):
        for herdr in (False, True):
            with self.subTest(herdr=herdr):
                stream = io.StringIO()
                graphics = KittyIcons(stream, herdr=herdr)
                with patch('fleet_update.kitty_icons.cell_size', return_value=(12, 26)):
                    graphics.print('SYNC', '✓', 'Python (environment)', '')
                output = re.sub(r'\x1b_G[^\x1b]*\x1b\\', '', stream.getvalue())
                output = re.sub(r'\x1b]66;[^;]*;([^\x1b]*)\x1b\\', r'\1', output)
                output = re.sub(r'\x1b\[[0-9;]*m', '', output)
                first_row = output.split('\r\n')[0]
                placeholder = '\U0010eeee'
                start, end = first_row.index(placeholder), first_row.rindex(placeholder)
                self.assertEqual(first_row[:start], 'SYNC    ✓ ')
                # Skip the last placeholder's two combining coordinates.
                self.assertEqual(first_row[end + 3:].rstrip(), ' Python (Environment)')

    def test_herdr_uses_its_cell_query_and_plain_text_with_scrolling_images(self):
        with patch.dict(os.environ, {'TERM': 'xterm-256color', 'TERM_PROGRAM': 'herdr', 'HERDR_ENV': '1'}), \
                patch('fleet_update.kitty_icons.cell_size', return_value=None), \
                patch('fleet_update.kitty_icons.herdr_cell_size', return_value=(12, 26)) as query:
            stream = io.StringIO()
            progress = HookProgress(stream=stream, live=True)
            progress.start('python', 'Python (environment)', 'SYNC')
            progress.finish('python', 'Python (environment)', verb='DONE', record=False)
            self.assertEqual(query.call_count, 1)
            output = stream.getvalue()
            self.assertIn('\x1b_G', output)
            self.assertIn('Python', output)
            self.assertIn('Environment', output)
            self.assertNotIn('\x1b]66;', output)
            self.assertIn('\r\x1b[2A', output)
            self.assertEqual(progress.height, 0)

    def test_herdr_without_geometry_falls_back_instead_of_hiding_text(self):
        with patch.dict(os.environ, {'TERM': 'xterm-256color', 'TERM_PROGRAM': 'herdr', 'HERDR_ENV': '1'}), \
                patch('fleet_update.kitty_icons.cell_size', return_value=None), \
                patch('fleet_update.kitty_icons.herdr_cell_size', return_value=None):
            stream = io.StringIO()
            progress = HookProgress(stream=stream, live=False)
            progress.finish('python', 'Python (environment)', record=False)
            self.assertIn('Python', stream.getvalue())
            self.assertNotIn('\x1b_G', stream.getvalue())

    def test_herdr_query_handles_fragmented_reply_and_restores_terminal_modes(self):
        import pty
        import select
        import termios
        import threading
        master, slave = pty.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        original = termios.tcgetattr(slave)
        received = []

        def emulator():
            if select.select([master], [], [], 1)[0]:
                received.append(os.read(master, 64))
                for fragment in (b'\x1b[6;', b'26;', b'12t'):
                    os.write(master, fragment)

        thread = threading.Thread(target=emulator)
        thread.start()
        with os.fdopen(os.dup(slave), 'w') as stream:
            self.assertEqual(herdr_cell_size(stream), (12, 26))
        thread.join(timeout=2)
        self.assertEqual(received, [b'\x1b[16t'])
        self.assertEqual(termios.tcgetattr(slave), original)

    def test_herdr_query_does_not_consume_pending_input(self):
        import pty
        import termios
        master, slave = pty.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        original = termios.tcgetattr(slave)
        os.write(master, b'user input\n')
        with os.fdopen(os.dup(slave), 'w') as stream:
            self.assertIsNone(herdr_cell_size(stream))
        self.assertEqual(termios.tcgetattr(slave), original)
        self.assertEqual(os.read(slave, 128), b'user input\n')

    def test_herdr_query_timeout_restores_terminal_modes(self):
        import pty
        import termios
        master, slave = pty.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        original = termios.tcgetattr(slave)
        with os.fdopen(os.dup(slave), 'w') as stream:
            self.assertIsNone(herdr_cell_size(stream))
        self.assertEqual(termios.tcgetattr(slave), original)


if __name__ == '__main__':
    unittest.main()
