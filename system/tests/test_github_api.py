"""Exercise installer authentication and failures without credentials or network."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
from types import SimpleNamespace
import unittest
import urllib.error
import urllib.request
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / ('etc' if (ROOT / 'etc').is_dir() else 'home') / '.chezmoitemplates'
sys.path.insert(0, str(TEMPLATES))
import github_api as api


class GitHubApiTests(unittest.TestCase):
    def test_environment_token_precedence(self):
        for env, token in (({'GH_TOKEN': 'first', 'GITHUB_TOKEN': 'second'}, 'first'),
                           ({'GH_TOKEN': ' ', 'GITHUB_TOKEN': 'second'}, 'second')):
            with self.subTest(env=env), patch.dict(os.environ, env, clear=True), \
                 patch.object(api.subprocess, 'run') as command:
                self.assertEqual(api.github_token(), token)
                command.assert_not_called()

    def test_gh_credentials_use_invoking_user_even_under_sudo(self):
        for uid, env, expected in (
            (1000, {}, ['gh', 'auth', 'token', '--hostname', 'github.com']),
            (0, {'SUDO_USER': 'desktop'}, ['sudo', '-n', '-H', '-u', 'desktop', '--',
                'env', '-u', 'XDG_CONFIG_HOME', '-u', 'GH_CONFIG_DIR',
                'gh', 'auth', 'token', '--hostname', 'github.com']),
            (0, {'SUDO_USER': 'root'}, ['gh', 'auth', 'token', '--hostname', 'github.com']),
        ):
            with self.subTest(uid=uid, env=env), patch.dict(os.environ, env, clear=True), \
                 patch.object(api.os, 'geteuid', return_value=uid), \
                 patch.object(api.subprocess, 'run', return_value=SimpleNamespace(
                     returncode=0, stdout=' login-token\n')) as command:
                self.assertEqual(api.github_token(), 'login-token')
                command.assert_called_once_with(expected, capture_output=True, text=True, timeout=10)

    def test_missing_or_unusable_gh_allows_anonymous_lookup(self):
        with patch.dict(os.environ, {}, clear=True):
            for error in (FileNotFoundError(), subprocess.TimeoutExpired('gh', 10)):
                with self.subTest(error=type(error)), patch.object(api.subprocess, 'run', side_effect=error):
                    self.assertIsNone(api.github_token())
            for code, output in ((1, 'unusable'), (0, '\n')):
                with patch.object(api.subprocess, 'run', return_value=SimpleNamespace(
                        returncode=code, stdout=output)):
                    self.assertIsNone(api.github_token())

    def test_authentication_is_optional_and_in_headers_only(self):
        for token in ('secret-token', None):
            opener = MagicMock()
            opener.open.return_value = io.BytesIO(b'{"tag_name": "v1.0.0"}')
            with self.subTest(auth=bool(token)), patch.object(api, 'github_token', return_value=token), \
                 patch.object(api.urllib.request, 'build_opener', return_value=opener):
                self.assertEqual(api.github_json('https://api.github.com/repos/test/tool/releases/latest'),
                                 {'tag_name': 'v1.0.0'})
                request = opener.open.call_args.args[0]
                self.assertEqual(request.get_header('Authorization'), f'Bearer {token}' if token else None)
                self.assertNotIn('secret-token', request.full_url)
                self.assertEqual(opener.open.call_args.kwargs, {'timeout': 30})

    def test_credentials_cannot_be_sent_to_other_origins_or_redirects(self):
        for url in ('http://api.github.com/test', 'https://github.com/releases/asset',
                    'https://api.github.com.evil.invalid/test', 'https://api.github.com@evil.invalid'):
            with self.subTest(url=url), patch.object(api, 'github_token') as token:
                with self.assertRaises(RuntimeError):
                    api.github_json(url)
                token.assert_not_called()
                with self.assertRaises(RuntimeError):
                    api.GitHubRedirectHandler().redirect_request(
                        urllib.request.Request('https://api.github.com/old'), None, 302, 'redirect', {}, url)

    def test_api_repository_rename_redirect_retains_authentication(self):
        request = urllib.request.Request('https://api.github.com/old', headers={'Authorization': 'Bearer token'})
        redirected = api.GitHubRedirectHandler().redirect_request(
            request, None, 301, 'moved', {}, 'https://api.github.com/new')
        self.assertEqual(redirected.get_header('Authorization'), 'Bearer token')

    def test_http_network_and_invalid_json_errors_are_actionable(self):
        cases = [(urllib.error.HTTPError('https://api.github.com/test', code, 'secret-token', {}, None), message)
                 for code, message in ((401, 'rejected'), (403, 'rate-limited'),
                                       (429, 'rate-limited'), (500, 'HTTP 500'))]
        cases += [(urllib.error.URLError('secret-token'), 'network'), (TimeoutError(), 'network')]
        for error, message in cases:
            opener = MagicMock()
            opener.open.side_effect = error
            with self.subTest(error=error), patch.object(api, 'github_token', return_value='secret-token'), \
                 patch.object(api.urllib.request, 'build_opener', return_value=opener), \
                 patch.object(api.json, 'load') as parse:
                with self.assertRaisesRegex(RuntimeError, message) as caught:
                    api.github_json('https://api.github.com/test')
                self.assertNotIn('secret-token', str(caught.exception))
                parse.assert_not_called()
        opener = MagicMock()
        opener.open.return_value = io.BytesIO(b'not JSON')
        with patch.object(api, 'github_token', return_value=None), \
             patch.object(api.urllib.request, 'build_opener', return_value=opener):
            with self.assertRaisesRegex(RuntimeError, 'invalid JSON'):
                api.github_json('https://api.github.com/test')

    def test_every_api_installer_uses_helper_and_exits_cleanly_on_denial(self):
        scripts = [p for p in TEMPLATES.glob('*.py') if p.name != 'github_api.py'
                   and 'api.github.com' in p.read_text()]
        self.assertTrue(scripts)
        for script in scripts:
            self.assertIn('from github_api import github_json', script.read_text(), script.name)
            with self.subTest(script=script.name), \
                 patch.object(api, 'github_json', side_effect=RuntimeError('GitHub rate-limited (HTTP 403)')), \
                 patch.object(sys, 'argv', [str(script), 'terminal']), \
                 patch.object(os, 'uname', return_value=SimpleNamespace(machine='x86_64')), \
                 patch.object(Path, 'mkdir'), patch.object(subprocess, 'run') as command, \
                 contextlib.redirect_stdout(io.StringIO()) as output:
                with self.assertRaises(SystemExit) as caught:
                    runpy.run_path(str(script), run_name='__main__')
                self.assertEqual(str(caught.exception), 'GitHub rate-limited (HTTP 403)')
                self.assertEqual(output.getvalue(), '')
                command.assert_not_called()


if __name__ == '__main__':
    unittest.main()
