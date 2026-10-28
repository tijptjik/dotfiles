"""Exercise real hook output without applying live configuration."""
import contextlib
import io
import os
from pathlib import Path
import shutil
import re
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import tjikup_support
from fleet_update.home_apply import apply_hooks
from fleet_update.core import UpdateError
from fleet_update.presentation import summary, timing_report
from fleet_update.hook_tasks import HookTasks
from fleet_update.dag import Result
from tjikup import runtime


class PresentationTests(unittest.TestCase):
    def test_ssh_timing_report_is_compact_and_links_the_originating_host(self):
        path = Path('/tmp/private report/apply-demo/timings.json')
        output = io.StringIO()
        with patch.dict(os.environ, {'TERM': 'xterm-kitty', 'TJIKUP_COLOR': '1',
                                     'TJIKUP_PROGRESS': '1', 'TJIKUP_COLUMNS': '80',
                                     'SSH_CONNECTION': '192.0.2.1 1000 192.0.2.2 22'}), \
                patch('fleet_update.presentation.socket.gethostname', return_value='si'):
            timing_report(path, stream=output)
        rendered = output.getvalue()
        self.assertIn('file://si/tmp/private%20report/apply-demo/timings.json', rendered)
        visible = re.sub(r'\x1b\]8;;.*?\x1b\\', '', rendered)
        visible = re.sub(r'\x1b\[[0-9;]*m', '', visible).rstrip('\n')
        self.assertIn('REPORT  ↗ Task timings', visible)
        self.assertTrue(visible.endswith('apply-demo'))
        self.assertNotIn('/tmp/', visible)
        self.assertLessEqual(runtime.display_width(visible), 80)

    def test_local_report_uses_a_portable_hostless_file_url(self):
        with patch.dict(os.environ, {'TJIKUP_PROGRESS': '1', 'TERM': 'xterm-256color',
                                     'SSH_CONNECTION': ''}):
            output = io.StringIO()
            timing_report('/tmp/private report/timings.json', stream=output)
        self.assertIn('file:///tmp/private%20report/timings.json', output.getvalue())

    def test_remote_shortcut_exports_private_report_instead_of_an_expiring_link(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'timings.json'
            source.write_text('{"tasks": []}\n')
            exported = Path(temporary) / 'remote-export.json'
            output = io.StringIO()
            with patch.dict(os.environ, {'TJIKUP_TIMING_EXPORT': str(exported)}):
                timing_report(source, stream=output)
            self.assertEqual(exported.read_bytes(), source.read_bytes())
            self.assertEqual(exported.stat().st_mode & 0o777, 0o600)
            self.assertEqual(output.getvalue(), '')

    def test_export_never_overwrites_an_existing_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'timings.json'
            source.write_text('{"tasks": []}\n')
            existing = Path(temporary) / 'existing'
            existing.write_text('preserve me')
            output = io.StringIO()
            with patch.dict(os.environ, {'TJIKUP_TIMING_EXPORT': str(existing), 'TERM': 'dumb'}):
                timing_report(source, stream=output)
            self.assertEqual(existing.read_text(), 'preserve me')
            self.assertIn(f'Task timings: {source}', output.getvalue())

    def test_timing_report_keeps_full_paths_in_redirected_or_dumb_output(self):
        for term, progress in [('xterm-kitty', '0'), ('dumb', '1')]:
            with self.subTest(term=term, progress=progress), \
                    patch.dict(os.environ, {'TERM': term, 'TJIKUP_PROGRESS': progress,
                                            'TJIKUP_COLOR': '0'}):
                output = io.StringIO()
                timing_report(Path('/tmp/apply-demo/timings.json'), stream=output)
                self.assertEqual(output.getvalue(), 'Task timings: /tmp/apply-demo/timings.json\n')

    def test_narrow_timing_link_fits_without_colour_or_report_side_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / 'report.tsv'
            report.write_text('original\n')
            output = io.StringIO()
            with patch.dict(os.environ, {'TERM': 'xterm-kitty', 'TJIKUP_PROGRESS': '1',
                                         'TJIKUP_COLOR': '0', 'TJIKUP_COLUMNS': '24',
                                         'TJIKUP_REPORT_FILE': str(report)}):
                timing_report(Path(directory) / 'apply-demo/timings.json', stream=output)
            rendered = output.getvalue()
            visible = re.sub(r'\x1b\]8;;.*?\x1b\\', '', rendered).rstrip('\n')
            self.assertEqual(visible, 'REPORT  ↗ Task timings')
            self.assertNotIn('\x1b[', rendered)
            self.assertLessEqual(runtime.display_width(visible), 24)
            self.assertEqual(report.read_text(), 'original\n')

    def test_notes_and_warnings_survive_ansi_and_pending_rows(self):
        outcome = summary('\x1b[36mSYNC    ... Python\r\x1b[2KSYNC    ✓ Python    86 pkgs\nWARN    ! Missing optional tool\n')
        self.assertEqual(outcome.note, '86 pkgs')
        self.assertEqual(outcome.warnings, ('WARN    ! Missing optional tool',))
        self.assertEqual((outcome.verb, outcome.icon), ('WARN', '!'))

    def test_reported_outcomes_override_planned_actions(self):
        cases = [
            ('SKIP    ✓ Docker    active\n', 'SKIP', '✓', 'active'),
            ('SYNC    ✓ Rust    2 pkgs; no changes\n', 'SKIP', '✓', '2 pkgs; no changes'),
            ('SKIP    - Python    client only\n', 'SKIP', '-', 'client only'),
            ('INSTALL ✓ Tool    installed\nSKIP    ✓ Other    available\n', 'INSTALL', '✓', 'installed'),
            ('INSTALL ✓ Tool\nCONFIG  ✓ Tool    enabled\n', 'APPLY', '✓', 'enabled'),
            ('CHECK   ✓ Docker    active\nSKIP    ✓ Other\n', 'CHECK', '✓', 'active'),
            ('', 'DONE', '✓', ''),
            ('FAILED  ✗ Tool    broken\n', 'FAILED', '✗', ''),
        ]
        for output, verb, icon, note in cases:
            with self.subTest(output=output):
                outcome = summary(output)
                self.assertEqual((outcome.verb, outcome.icon, outcome.note), (verb, icon, note))

    def test_completion_uses_real_skip_in_display_and_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / 'report'
            with patch.dict(os.environ, {'TJIKUP_COLOR': '0', 'TJIKUP_REPORT_FILE': str(report)}), \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                hooks = HookTasks(root, root, {})
                hooks.items['icons'] = {'label': 'Assets (Rose Punk icons)', 'verb': 'UPDATE'}
                hooks.outputs['icons'] = 'UPDATE  ✓ Rose Punk icons    no changes\n'
                hooks.event('icons', Result('done', seconds=.2))
            self.assertIn('SKIP    ✓ Assets (Rose Punk Icons)', output.getvalue())
            self.assertEqual(report.read_text(), 'SKIP\t✓\tAssets (Rose Punk icons)\tno changes\n')

    def test_service_subtype_and_outcome_colours(self):
        with patch.dict(os.environ, {'TJIKUP_COLOR': '1', 'TJIKUP_COLUMNS': '100'}):
            for verb, icon, colour in [('INSTALL', '✓', '32'), ('SKIP', '✓', '90'),
                                       ('WARN', '!', '33'), ('FAILED', '✗', '31'), ('UPDATE', '…', '36')]:
                row = runtime.format_status(verb, icon, 'Assets (fonts)', 'ready')
                self.assertIn(f'\x1b[{colour};1m{verb:<7}', row)
                self.assertIn(f'\x1b[{colour}m{icon}', row)
                self.assertIn('\x1b[97mAssets\x1b[0m \x1b[90m(fonts)', row)

    @unittest.skipUnless(shutil.which('fish'), 'Fish required')
    def test_cached_install_note_survives_stage_wrapper(self):
        helper = Path(__file__).resolve().parents[1] / 'home/.chezmoihelpers/status.fish'
        command = ['fish', '--no-config', '-c',
                   'source $argv[1]; stage_dynamic_note Install INSTALL Example '
                   "printf '__stage_note__:no changes\\n'", '--', str(helper)]
        result = subprocess.run(command, capture_output=True, text=True, check=True,
                                env={**os.environ, 'TJIKUP_COLOR': '0', 'TJIKUP_NO_SPIN': '1'})
        outcome = summary(result.stdout)
        self.assertEqual((outcome.verb, outcome.note), ('SKIP', 'no changes'))

    @unittest.skipUnless(shutil.which('fish'), 'Fish required')
    def test_hook_success_is_one_row_and_failure_keeps_diagnostics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hooks = root / 'home/.chezmoiscripts'
            hooks.mkdir(parents=True)
            hook = hooks / 'run_after_test.fish'
            plan = [{'id': 'python', 'label': 'Python', 'verb': 'SYNC', 'file': hook.name}]
            env = {**os.environ, 'XDG_STATE_HOME': str(root / 'state'), 'TJIKUP_COLOR': '0', 'TJIKUP_PROGRESS': '0'}
            for fail in (False, True):
                with self.subTest(fail=fail):
                    hook.write_text("printf 'SYNC    ... Python\\nUsing Python environment\\nSYNC    ✓ Python    86 pkgs\\n'\n" +
                                    ("echo 'specific failure' >&2\nexit 9\n" if fail else ''))
                    with patch('fleet_update.home_apply.load_plan', return_value=plan), \
                            patch.dict(os.environ, env), contextlib.redirect_stdout(io.StringIO()) as output:
                        if fail:
                            with self.assertRaises(UpdateError):
                                apply_hooks(root, env)
                        else:
                            apply_hooks(root, env)
                    if fail:
                        self.assertIn('specific failure', output.getvalue())
                        self.assertIn('Log:', output.getvalue())
                    else:
                        lines = [line for line in output.getvalue().splitlines() if line.strip()]
                        self.assertEqual(len(lines), 2)
                        self.assertEqual(lines[0], 'Home Configuration')
                        self.assertIn('86 pkgs', output.getvalue())
                        self.assertNotIn('Using Python', output.getvalue())
                        self.assertNotIn('DAG', output.getvalue())
            logs = list((root / 'state/tjikup/logs').glob('home-*/python.log'))
            self.assertEqual(len(logs), 2)
            self.assertTrue(all('Using Python' in log.read_text() for log in logs))

    @unittest.skipUnless(shutil.which('fish'), 'Fish required')
    def test_exclusive_hook_streams_diagnostics_and_summarizes_status_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hooks = root / 'home/.chezmoiscripts'
            hooks.mkdir(parents=True)
            hook = hooks / 'run_after_release.fish'
            hook.write_text("printf 'CHECK   ... Fedora release check    checking\\n'\n"
                            "echo 'Checking release metadata'\n"
                            "printf 'SKIP    ✓ Fedora upgrade    no changes\\n'\n")
            plan = [{'id': 'release', 'label': 'Fedora (release)',
                     'file': hook.name, 'exclusive': True}]
            env = {**os.environ, 'XDG_STATE_HOME': str(root / 'state'),
                   'TJIKUP_COLOR': '0', 'TJIKUP_PROGRESS': '0', 'TJIKUP_ICONS': '0'}
            with patch('fleet_update.home_apply.load_plan', return_value=plan), \
                    patch.dict(os.environ, env), contextlib.redirect_stdout(io.StringIO()) as output:
                apply_hooks(root, env)
            self.assertIn('Checking release metadata', output.getvalue())
            self.assertEqual(output.getvalue().count('Fedora (Release)'), 1)
            self.assertNotIn('Fedora upgrade', output.getvalue())
            self.assertNotIn('Fedora release check', output.getvalue())
            log, = (root / 'state/tjikup/logs').glob('home-*/release.log')
            self.assertIn('SKIP    ✓ Fedora upgrade    no changes', log.read_text())
            self.assertIn('CHECK   ... Fedora release check', log.read_text())

    @unittest.skipUnless(shutil.which('fish'), 'Fish required')
    def test_exclusive_heading_does_not_relabel_later_hooks(self):
        helper = Path(__file__).resolve().parents[1] / 'home/.chezmoihelpers/status.fish'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hooks = root / 'home/.chezmoiscripts'
            hooks.mkdir(parents=True)
            plan = []
            for name, title, exclusive in [('herdr', 'Herdr', True), ('storage', 'Private storage', False)]:
                hook = hooks / f'run_after_{name}.fish'
                hook.write_text(f'source "{helper}"\nsection_header "{title}"\n'
                                f'status_msg CONFIG ✓ "{title}"\n')
                plan.append({'id': name, 'label': title, 'file': hook.name,
                             'exclusive': exclusive, 'needs': [] if exclusive else ['herdr']})
            env = {**os.environ, 'XDG_STATE_HOME': str(root / 'state'),
                   'TJIKUP_COLOR': '0', 'TJIKUP_PROGRESS': '0', 'TJIKUP_NO_SECTIONS': '0'}
            # Direct hook execution keeps its own application section.
            direct = subprocess.run(['fish', '--no-config', str(hooks / plan[0]['file'])],
                                    env=env, capture_output=True, text=True, check=True)
            self.assertIn('\nHerdr\n', direct.stdout)
            with patch('fleet_update.home_apply.load_plan', return_value=plan), \
                    patch.dict(os.environ, env), contextlib.redirect_stdout(io.StringIO()) as output:
                apply_hooks(root, env)
            lines = [line for line in output.getvalue().splitlines() if line.strip()]
            self.assertEqual(lines[0], 'Home Configuration')
            self.assertEqual(lines.count('Home Configuration'), 1)
            self.assertNotIn('Herdr', lines)
            self.assertNotIn('Private storage', lines)
            self.assertTrue(any('CONFIG' in line and 'Herdr' in line for line in lines))
            self.assertIn('Private storage', lines[-1])


if __name__ == '__main__':
    unittest.main()
