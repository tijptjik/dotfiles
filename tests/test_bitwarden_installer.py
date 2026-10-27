"""Keep healthy managed CLIs usable when GitHub metadata is unavailable."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / 'home/.chezmoitemplates'
sys.path.insert(0, str(TEMPLATES))
spec = importlib.util.spec_from_file_location('bitwarden_installer', TEMPLATES / 'install-bitwarden-cli.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class BitwardenInstallerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.target = Path(self.directory.name) / '2.1.0/bws'
        self.target.parent.mkdir()
        self.target.write_text('synthetic executable')
        self.target.chmod(0o755)
        self.marker = self.target.parent / '.installed'
        self.marker.write_text('a' * 64 + '\n')

    def usable(self, *, stdout='bws 2.1.0\n', returncode=0, error=None, tool='bws'):
        with patch.object(installer, 'current_install', return_value=('2.1.0', self.target)), \
             patch.object(installer.subprocess, 'run', side_effect=error,
                          return_value=SimpleNamespace(returncode=returncode, stdout=stdout)) as command:
            result = installer.usable_install(tool)
        return result, command

    def test_healthy_managed_install_requires_matching_version_and_receipt(self):
        self.assertTrue(self.usable()[0])
        for content in ('', 'not-a-digest', 'a' * 63):
            self.marker.write_text(content)
            usable, command = self.usable()
            self.assertFalse(usable)
            command.assert_not_called()
        self.marker.unlink()
        self.assertFalse(self.usable()[0])

    def test_missing_nonexecutable_and_broken_commands_are_not_usable(self):
        for kwargs in ({'stdout': 'bws 9.0.0'}, {'returncode': 1},
                       {'error': FileNotFoundError()},
                       {'error': subprocess.TimeoutExpired('bws', 10)}):
            with self.subTest(kwargs=kwargs):
                self.assertFalse(self.usable(**kwargs)[0])
        self.target.chmod(0o644)
        self.assertFalse(self.usable()[0])
        self.target.unlink()
        self.assertFalse(self.usable()[0])
        with patch.object(installer, 'current_install', return_value=(None, None)):
            self.assertFalse(installer.usable_install('bws'))

    def test_vault_check_uses_temporary_appdata_and_no_install_commands(self):
        with patch.dict(os.environ, {'BITWARDENCLI_APPDATA_DIR': '/private/vault'}):
            usable, command = self.usable(tool='bw', stdout='2.1.0\n')
        self.assertTrue(usable)
        self.assertNotEqual(command.call_args.kwargs['env']['BITWARDENCLI_APPDATA_DIR'], '/private/vault')
        self.assertFalse(Path(command.call_args.kwargs['env']['BITWARDENCLI_APPDATA_DIR']).exists())
        self.assertEqual(command.call_args.args[0], [str(self.target), '--version'])

    def test_only_metadata_lookup_failure_can_defer(self):
        with patch.object(installer, 'github_json', side_effect=RuntimeError('HTTP 403')), \
             patch.object(installer, 'usable_install', return_value=True), \
             patch.object(installer, 'run') as mutation, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertFalse(installer.install_tool('bws'))
            self.assertIn('release check deferred: HTTP 403', output.getvalue())
            mutation.assert_not_called()
        for release in (
            {'tag_name': 'bws-v2.1.0', 'assets': []},
            {'tag_name': 'bws-v2.1.0', 'assets': [{'name': 'bws-x86_64-unknown-linux-gnu-2.1.0.zip'}]},
        ):
            with self.subTest(release=release), \
                 patch.object(installer, 'github_json', return_value=[release]), \
                 patch.object(installer, 'usable_install', return_value=True) as fallback:
                with self.assertRaises(RuntimeError):
                    installer.install_tool('bws')
                fallback.assert_not_called()

    def test_unavailable_metadata_still_blocks_missing_or_unhealthy_install(self):
        with patch.object(installer, 'github_json', side_effect=RuntimeError('HTTP 403')), \
             patch.object(installer, 'usable_install', return_value=False):
            with self.assertRaisesRegex(installer.ReleaseLookupError, 'HTTP 403'):
                installer.install_tool('bw')

    def test_main_checks_both_tools_and_returns_warning_only_after_success(self):
        for results, expected in (([True, True], 0), ([False, True], 78), ([False, False], 78)):
            with self.subTest(results=results), \
                 patch.object(installer.os, 'uname', return_value=SimpleNamespace(machine='x86_64')), \
                 patch.object(installer, 'install_tool', side_effect=results) as install:
                self.assertEqual(installer.main(), expected)
                self.assertEqual([call.args[0] for call in install.call_args_list], ['bws', 'bw'])
        with patch.object(installer.os, 'uname', return_value=SimpleNamespace(machine='x86_64')), \
             patch.object(installer, 'install_tool', side_effect=[False, RuntimeError('missing bw')]):
            with self.assertRaisesRegex(RuntimeError, 'missing bw'):
                installer.main()


if __name__ == '__main__':
    unittest.main()
