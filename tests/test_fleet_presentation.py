"""Exercise real hook output without applying live configuration."""
import contextlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import tjikup_support
from fleet_update.home_apply import apply_hooks
from fleet_update.core import UpdateError
from fleet_update.presentation import summary
from fleet_update.hook_tasks import HookTasks
from fleet_update.dag import Result
from tjikup import runtime


class PresentationTests(unittest.TestCase):
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
            self.assertIn('SKIP    ✓ Assets (Rose Punk icons)', output.getvalue())
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
                        self.assertEqual(lines[0], 'Home configuration')
                        self.assertIn('86 pkgs', output.getvalue())
                        self.assertNotIn('Using Python', output.getvalue())
                        self.assertNotIn('DAG', output.getvalue())
            logs = list((root / 'state/tjikup/logs').glob('home-*/python.log'))
            self.assertEqual(len(logs), 2)
            self.assertTrue(all('Using Python' in log.read_text() for log in logs))

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
            self.assertEqual(lines[0], 'Home configuration')
            self.assertEqual(lines.count('Home configuration'), 1)
            self.assertNotIn('Herdr', lines)
            self.assertNotIn('Private storage', lines)
            self.assertTrue(any('CONFIG' in line and 'Herdr' in line for line in lines))
            self.assertIn('Private storage', lines[-1])


if __name__ == '__main__':
    unittest.main()
