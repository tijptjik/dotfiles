"""Exercise real hook output without applying live configuration."""
import contextlib
import io
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import tjikup_support
from fleet_update.home_apply import apply_hooks
from fleet_update.core import UpdateError
from fleet_update.presentation import summary


class PresentationTests(unittest.TestCase):
    def test_notes_and_warnings_survive_ansi_and_pending_rows(self):
        note, warnings = summary('\x1b[36mSYNC    ... Python\r\x1b[2KSYNC    ✓ Python    86 pkgs\nWARN    ! Missing optional tool\n')
        self.assertEqual(note, '86 pkgs')
        self.assertEqual(warnings, ['WARN    ! Missing optional tool'])

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
                        self.assertEqual(len(output.getvalue().splitlines()), 1)
                        self.assertIn('86 pkgs', output.getvalue())
                        self.assertNotIn('Using Python', output.getvalue())
                        self.assertNotIn('DAG', output.getvalue())
            logs = list((root / 'state/tjikup/logs').glob('home-*/python.log'))
            self.assertEqual(len(logs), 2)
            self.assertTrue(all('Using Python' in log.read_text() for log in logs))


if __name__ == '__main__':
    unittest.main()
