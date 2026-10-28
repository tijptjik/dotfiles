"""Verify headings without touching locks, Docker, packages or backups."""
import contextlib
import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import mock_open, patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('si_update_apps', ROOT / 'etc/si-provision/update_apps.py')
apps = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(apps)


class ServerAppSectionTests(unittest.TestCase):
    def updater(self):
        obj = apps.Updater.__new__(apps.Updater)
        obj.failed = False
        return obj

    def test_headers_bracket_docker_and_native_results(self):
        updater = self.updater()
        calls = []
        with patch('builtins.open', mock_open()), patch.object(apps.fcntl, 'flock'), \
                patch.object(updater, 'update_docker', side_effect=lambda: (calls.append('docker'), apps.report('SKIP', 'radarr', 'no changes'))), \
                patch.object(updater, 'update_plex', side_effect=lambda: (calls.append('plex'), apps.report('SKIP', 'Plex', '2 active session(s)'))), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(updater.run(), 0)
        self.assertEqual(calls, ['docker', 'plex'])
        self.assertEqual(output.getvalue().splitlines(), [
            'SECTION\tDocker services\tbegin', 'SKIP\tradarr\tno changes',
            'SECTION\tNative applications\tbegin', 'SKIP\tPlex\t2 active session(s)'])

    def test_docker_failure_retains_warning_and_native_check(self):
        updater = self.updater()
        with patch('builtins.open', mock_open()), patch.object(apps.fcntl, 'flock'), \
                patch.object(updater, 'update_docker', side_effect=apps.UpdateFailure('safe failure')), \
                patch.object(updater, 'update_plex') as plex, contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(updater.run(), 1)
        plex.assert_called_once()
        self.assertIn('WARN\tDocker images\tsafe failure', output.getvalue())
        self.assertIn('SECTION\tNative applications\tbegin', output.getvalue())

    def test_active_backup_still_blocks_both_updaters(self):
        updater = self.updater()
        with patch('builtins.open', mock_open()), patch.object(apps.fcntl, 'flock', side_effect=BlockingIOError), \
                patch.object(updater, 'update_docker') as docker, patch.object(updater, 'update_plex') as plex, \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(updater.run(), 0)
        docker.assert_not_called()
        plex.assert_not_called()
        self.assertIn('backup or restore in progress', output.getvalue())

    def test_fish_hook_renders_or_forwards_sections_and_keeps_exit_status(self):
        import os
        import re
        import shutil
        import subprocess
        if not shutil.which('fish'):
            self.skipTest('Fish required')
        script = (ROOT / 'etc/.chezmoitemplates/tjikup/run_after_95-si-app-updates.fish.tmpl').read_text()
        script = re.sub(r'{{ include "([^"]+)" }}',
                        lambda m: (ROOT / 'etc' / m[1]).read_text(), script)
        script = re.sub(r'{{ (?:if .*?|end) -}}', '', script)
        harness = '''
function sudo
    printf 'SECTION\\tDocker services\\tbegin\\nSKIP\\tradarr\\tno changes\\nSECTION\\tNative applications\\tbegin\\nSKIP\\tPlex\\t2 active sessions\\n'
    return $TEST_UPDATER_EXIT
end
'''
        for forwarded in (False, True):
            for code in (0, 9):
                with self.subTest(forwarded=forwarded, code=code):
                    result = subprocess.run(['fish', '--no-config', '-c', harness + script],
                        capture_output=True, text=True, env={**os.environ,
                        'FLEET_DEFER_SYSTEM_HOOKS': '0', 'TJIKUP_COLOR': '0',
                        'TJIKUP_NO_SECTIONS': '1' if forwarded else '0',
                        'TJIKUP_STATUS_SECTIONS': '1' if forwarded else '0',
                        'TJIKUP_STATUS_LINES': '1', 'TJIKUP_NO_SPIN': '1',
                        'TEST_UPDATER_EXIT': str(code)})
                    self.assertEqual(result.returncode, code, result.stderr)
                    marker = '__tjikup_section__:Docker services' if forwarded else '\nDocker services\n'
                    self.assertIn(marker, result.stdout)
                    self.assertIn('radarr', result.stdout)
                    self.assertIn('2 active sessions', result.stdout)
                    if code:
                        self.assertIn('FAILED', result.stdout)
