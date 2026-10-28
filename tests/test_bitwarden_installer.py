"""Keep normal convergence local and explicit upgrades product-specific."""
import contextlib
import importlib.util
import io
import os
import re
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
        with patch.object(installer, 'latest_tag', return_value='bws-v2.1.0'), \
             patch.object(installer, 'github_json', side_effect=RuntimeError('HTTP 403')), \
             patch.object(installer, 'usable_install', return_value=True), \
             patch.object(installer, 'run') as mutation, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(installer.install_tool('bws'), installer.InstallResult.DEFERRED)
            self.assertIn('release check deferred: HTTP 403', output.getvalue())
            mutation.assert_not_called()
        for release in (
            {'tag_name': 'bws-v2.1.0', 'assets': []},
            {'tag_name': 'bws-v2.1.0', 'assets': [{'name': 'bws-x86_64-unknown-linux-gnu-2.1.0.zip'}]},
        ):
            with self.subTest(release=release), \
                 patch.object(installer, 'latest_tag', return_value='bws-v2.1.0'), \
                 patch.object(installer, 'github_json', return_value=release), \
                 patch.object(installer, 'usable_install', return_value=True) as fallback:
                with self.assertRaises(RuntimeError):
                    installer.install_tool('bws')
                fallback.assert_not_called()

    def test_unavailable_metadata_still_blocks_missing_or_unhealthy_install(self):
        with patch.object(installer, 'latest_tag', return_value='cli-v2026.10.0'), \
             patch.object(installer, 'github_json', side_effect=RuntimeError('HTTP 403')), \
             patch.object(installer, 'usable_install', return_value=False):
            with self.assertRaisesRegex(installer.ReleaseLookupError, 'HTTP 403'):
                installer.install_tool('bw')

    def test_main_checks_both_tools_and_returns_warning_only_after_success(self):
        current, updated, deferred = installer.InstallResult.CURRENT, installer.InstallResult.UPDATED, installer.InstallResult.DEFERRED
        for results, expected in (([updated, updated], 0), ([current, updated], 0), ([current, current], 10), ([deferred, updated], 78), ([deferred, deferred], 78)):
            with self.subTest(results=results), \
                 patch.object(installer.os, 'uname', return_value=SimpleNamespace(machine='x86_64')), \
                 patch.object(installer, 'lookup_releases', return_value={'bws': (), 'bw': ()}), \
                 patch.object(installer, 'install_tool', side_effect=results) as install:
                self.assertEqual(installer.main(status_exit_code=True, upgrade=True), expected)
                self.assertEqual([call.args[0] for call in install.call_args_list], ['bws', 'bw'])
        with patch.object(installer.os, 'uname', return_value=SimpleNamespace(machine='x86_64')), \
             patch.object(installer, 'lookup_releases', return_value={'bws': (), 'bw': ()}), \
             patch.object(installer, 'install_tool', side_effect=[deferred, RuntimeError('missing bw')]):
            with self.assertRaisesRegex(RuntimeError, 'missing bw'):
                installer.main(status_exit_code=True, upgrade=True)

    def test_installed_tools_skip_without_network_subprocess_or_install(self):
        with patch.object(installer.os, 'uname', return_value=SimpleNamespace(machine='x86_64')), \
             patch.object(installer, 'current_install', return_value=('2.1.0', self.target)), \
             patch.object(installer, 'lookup_releases') as lookup, \
             patch.object(installer.subprocess, 'run') as process, \
             patch.object(installer, 'install_tool') as install, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(installer.main(), 0)  # Bootstrap callers expect success.
            self.assertEqual(installer.main(status_exit_code=True), 10)
        lookup.assert_not_called()
        process.assert_not_called()
        install.assert_not_called()

    def test_missing_tool_only_is_looked_up_and_installed(self):
        with patch.object(installer.os, 'uname', return_value=SimpleNamespace(machine='x86_64')), \
             patch.object(installer, 'recorded_install', side_effect=lambda tool: tool == 'bw'), \
             patch.object(installer, 'lookup_releases', return_value={'bws': ()}) as lookup, \
             patch.object(installer, 'install_tool', return_value=installer.InstallResult.UPDATED) as install:
            self.assertEqual(installer.main(status_exit_code=True), 0)
        lookup.assert_called_once_with(['bws'])
        install.assert_called_once_with('bws', release=())

    def test_upgrade_checks_even_recorded_tools(self):
        with patch.object(installer.os, 'uname', return_value=SimpleNamespace(machine='x86_64')), \
             patch.object(installer, 'recorded_install', return_value=True), \
             patch.object(installer, 'lookup_releases', return_value={'bws': (), 'bw': ()}) as lookup, \
             patch.object(installer, 'install_tool', return_value=installer.InstallResult.CURRENT):
            self.assertEqual(installer.main(upgrade=True, status_exit_code=True), 10)
        lookup.assert_called_once_with(['bws', 'bw'])

    def test_official_cli_redirect_selects_exact_product(self):
        location = 'https://github.com/bitwarden/clients/releases/download/cli-v2026.10.0/bw-linux-2026.10.0.zip'
        with patch.object(installer, 'public_metadata', return_value=location) as request:
            self.assertEqual(installer.latest_tag('bw'), 'cli-v2026.10.0')
        request.assert_called_once_with('https://bitwarden.com/download/?app=cli&platform=linux', redirect=True)
        for invalid in (location.replace('github.com', 'example.invalid'),
                        location.replace('cli-v', 'web-v'),
                        location.replace('bw-linux-2026.10.0', 'bw-linux-2026.9.0')):
            with self.subTest(invalid=invalid), patch.object(installer, 'public_metadata', return_value=invalid):
                with self.assertRaises(RuntimeError):
                    installer.latest_tag('bw')

    def test_bws_stable_package_identity_and_version(self):
        crate = {'name': 'bws', 'repository': 'https://github.com/bitwarden/sdk-sm', 'max_stable_version': '2.1.0'}
        with patch.object(installer, 'public_metadata', return_value={'crate': crate}) as request:
            self.assertEqual(installer.latest_tag('bws'), 'bws-v2.1.0')
        request.assert_called_once_with('https://crates.io/api/v1/crates/bws')
        for override in ({'name': 'other'}, {'repository': 'https://example.invalid'},
                         {'max_stable_version': '2.2.0-beta'}, {'max_stable_version': None}):
            with self.subTest(override=override), \
                 patch.object(installer, 'public_metadata', return_value={'crate': {**crate, **override}}):
                with self.assertRaises(RuntimeError):
                    installer.latest_tag('bws')

    def test_exact_release_lookup_and_validation(self):
        release = {'tag_name': 'bws-v2.1.0', 'assets': [{
            'name': 'bws-x86_64-unknown-linux-gnu-2.1.0.zip',
            'digest': 'sha256:' + 'a' * 64,
            'browser_download_url': 'https://example.invalid/release.zip'}]}
        with patch.object(installer, 'latest_tag', return_value='bws-v2.1.0'), \
             patch.object(installer, 'github_json', return_value=release) as request:
            self.assertEqual(installer.latest_asset('bws'), ('2.1.0', 'https://example.invalid/release.zip', 'a' * 64))
        request.assert_called_once_with('https://api.github.com/repos/bitwarden/sdk-sm/releases/tags/bws-v2.1.0')
        for override in ({'tag_name': 'python-v2.1.0'}, {'draft': True}, {'prerelease': True},
                         {'assets': []}, {'assets': [{**release['assets'][0], 'digest': 'sha256:bad'}]}):
            with self.subTest(override=override), \
                 patch.object(installer, 'latest_tag', return_value='bws-v2.1.0'), \
                 patch.object(installer, 'github_json', return_value={**release, **override}):
                with self.assertRaises(RuntimeError):
                    installer.latest_asset('bws')

    def test_metadata_lookups_overlap_but_do_not_install(self):
        import threading
        both_started = threading.Barrier(2)
        def lookup(tool):
            both_started.wait(timeout=2)
            return ('2.1.0', 'https://example.invalid/' + tool, 'a' * 64)
        with patch.object(installer, 'latest_asset', side_effect=lookup), \
             patch.object(installer, 'install_tool') as mutation:
            result = installer.lookup_releases()
        self.assertEqual(set(result), {'bws', 'bw'})
        mutation.assert_not_called()

    def test_prefetched_network_error_defers_only_healthy_tools(self):
        release = installer.ReleaseLookupError('offline')
        with patch.object(installer, 'usable_install', return_value=True), \
             patch.object(installer, 'latest_asset') as lookup, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(installer.install_tool('bws', release), installer.InstallResult.DEFERRED)
        lookup.assert_not_called()
        with patch.object(installer, 'usable_install', return_value=False):
            with self.assertRaises(installer.ReleaseLookupError):
                installer.install_tool('bws', release)

    def test_current_install_neither_downloads_nor_runs_privileged_commands(self):
        binary_dir = Path(self.directory.name) / 'bin'
        binary_dir.mkdir()
        (binary_dir / 'bws').symlink_to(self.target)
        def path(value):
            return binary_dir if value == '/usr/local/bin' else Path(value)
        with patch.object(installer, 'Path', side_effect=path), \
             patch.object(installer, 'current_install', return_value=('2.1.0', self.target)), \
             patch.object(installer, 'run') as mutation, \
             patch.object(installer.urllib.request, 'urlopen') as download, \
             contextlib.redirect_stdout(io.StringIO()):
            result = installer.install_tool('bws', ('2.1.0', 'https://example.invalid/release.zip', 'a' * 64))
        self.assertEqual(result, installer.InstallResult.CURRENT)
        mutation.assert_not_called()
        download.assert_not_called()



class BitwardenTimingTests(unittest.TestCase):
    def test_hook_forwards_explicit_upgrade_flag(self):
        import base64
        template = (ROOT / 'home/.chezmoitemplates/tjikup/run_before_02-install-bws.fish.tmpl').read_text()
        template = template.replace('{{ .chezmoi.sourceDir }}', str(ROOT / 'home'))
        synthetic = b"import os, sys\nassert sys.argv[1:] == ['--status-exit-code'] + (['--upgrade'] if os.environ.get('FLEET_UPGRADE') == '1' else [])\nsys.exit(10)\n"
        for name, content in [('github_api.py', b''), ('install-bitwarden-cli.py', synthetic)]:
            template = template.replace('{{ include ".chezmoitemplates/' + name + '" | b64enc | quote }}',
                                        "'" + base64.b64encode(content).decode() + "'")
        for upgrade in ('', '0', '1'):
            with self.subTest(upgrade=upgrade), tempfile.TemporaryDirectory() as directory:
                hook = Path(directory) / 'hook.fish'
                report = Path(directory) / 'report'
                hook.write_text(template)
                env = {**os.environ, 'FLEET_UPGRADE': upgrade, 'TJIKUP_REPORT_FILE': str(report)}
                result = subprocess.run(['fish', '--no-config', str(hook)], env=env,
                                        capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                row = report.read_text()
                self.assertTrue(row.startswith('SKIP\t'), row)
                self.assertIn('no changes' if upgrade == '1' else 'already installed', row)

    def test_shell_result_and_decorated_row_include_timing_for_every_outcome(self):
        ANSI = re.compile(r"\x1b\[[0-9;]*m")

        template = (ROOT / 'home/.chezmoitemplates/tjikup/run_before_02-install-bws.fish.tmpl').read_text()
        template = template.replace('{{ .chezmoi.sourceDir }}', str(ROOT / 'home'))
        # Run the real hook's status/timing control flow with a synthetic installer.
        start = template.index('function update_bitwarden_clis')
        end = template.index('\nif not contains -- /usr/local/bin')
        template = template[:start] + (
            'function update_bitwarden_clis\n'
            '    sleep 0.03\n'
            '    echo synthetic diagnostic\n'
            '    return $SYNTHETIC_RESULT\n'
            'end\n') + template[end:]
        for code, verb, expected in ((0, 'UPDATE', 0), (10, 'SKIP', 0), (78, 'WARN', 0), (3, 'FAILED', 3)):
            with self.subTest(code=code), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                hook, report = root / 'hook.fish', root / 'report'
                hook.write_text(template)
                env = {**os.environ, 'SYNTHETIC_RESULT': str(code), 'TJIKUP_COLOR': '0',
                       'TJIKUP_ICONS': '0', 'TJIKUP_COLUMNS': '200',
                       'TJIKUP_REPORT_FILE': str(report)}
                result = subprocess.run(['fish', '--no-config', str(hook)], env=env,
                                        capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, expected, result.stderr)
                rows = report.read_text().splitlines()
                self.assertEqual(len(rows), 1)
                fields = rows[0].split('\t')
                self.assertEqual(fields[0], verb)
                timing = re.match(r'(\d+\.\d{2})s', fields[3])
                self.assertIsNotNone(timing, rows[0])
                self.assertGreater(float(timing[1]), 0)
                native = next(line for line in result.stdout.splitlines()
                              if line.startswith(verb) and '...' not in line)
                with patch.dict(os.environ, env):
                    decorated = ANSI.sub('', (native))
                self.assertIn(timing[0], decorated)
                if code in (78, 3):
                    self.assertIn('synthetic diagnostic', result.stdout)
                if code == 78:
                    self.assertIn('release check deferred; managed installs kept', fields[3])


if __name__ == '__main__':
    unittest.main()
