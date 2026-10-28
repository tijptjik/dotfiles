"""Strata release lookup regressions without network or live installation writes."""
import contextlib
import copy
import importlib.util
import sys
import io
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
import urllib.error
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'etc/.chezmoitemplates/update-client-cli-releases.py'
HOOK = ROOT / 'etc/.chezmoitemplates/tjikup/run_53-install-strata.fish.tmpl'
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'etc/.chezmoitemplates'))
spec = importlib.util.spec_from_file_location('strata_updater', SOURCE)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class StrataReleaseTests(unittest.TestCase):
    def setUp(self):
        self.release = {
            'tag_name': 'v1.2.3',
            'assets': [{'name': 'strata-1.2.3-x86_64-unknown-linux-gnu.tar.gz',
                        'digest': 'sha256:' + 'AB' * 32}],
        }

    def test_metadata_selector_emits_only_version_and_checksum(self):
        output = io.StringIO()
        with patch.object(installer, 'github_json', return_value=self.release) as lookup, \
             patch.object(installer.sys, 'argv', ['updater', 'strata-metadata']), \
             patch.object(installer.os, 'uname', return_value=SimpleNamespace(machine='x86_64')), \
             patch.object(installer, 'install') as install, contextlib.redirect_stdout(output):
            installer.main()
        self.assertEqual(output.getvalue(), '1.2.3|' + 'ab' * 32 + '\n')
        lookup.assert_called_once_with('https://api.github.com/repos/lgse/strata/releases/latest')
        install.assert_not_called()

    def test_invalid_release_metadata_is_rejected(self):
        variants = []
        for tag in ('nightly', 'v1.2.3-rc1', ''):
            variants.append(dict(self.release, tag_name=tag))
        for flag in ('draft', 'prerelease'):
            variants.append(dict(self.release, **{flag: True}))
        variants.append(dict(self.release, assets=[]))
        for digest in (None, '', 'sha256:abc', 'md5:' + 'ab' * 32):
            release = copy.deepcopy(self.release)
            release['assets'][0]['digest'] = digest
            variants.append(release)
        for release in variants:
            with self.subTest(release=release), \
                 patch.object(installer, 'github_json', return_value=release):
                with self.assertRaises(RuntimeError):
                    installer.strata_release_metadata()

    @unittest.skipUnless(shutil.which('fish'), 'fish is required')
    def test_hook_lookup_failure_cleans_up_and_stops_before_installation(self):
        source = HOOK.read_text()
        function = source[source.index('function install_strata\n'):source.index('# Fedora dependencies')]
        include = '{{ include ".chezmoitemplates/update-client-cli-releases.py" | b64enc | quote }}'
        function = function.replace(include, "'cGFzcw=='")
        function = function.replace('{{ include ".chezmoitemplates/github_api.py" | b64enc | quote }}', "'cGFzcw=='")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            function = function.replace('/usr/local/bin/strata', str(root / 'strata'))
            script = f'''function uname
    echo x86_64
end
function mktemp
    mkdir '{root}/metadata'
    echo '{root}/metadata'
end
function python3
    echo 'GitHub release lookup was denied or rate-limited (HTTP 403)' >&2
    return 1
end
function sudo
    touch '{root}/unexpected-install'
    return 1
end
{function}
install_strata
exit $status
'''
            result = subprocess.run(['fish', '--no-config'], input=script, text=True, capture_output=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn('HTTP 403', result.stderr)
            self.assertNotIn('Traceback', result.stderr)
            self.assertEqual(result.stdout, '')
            self.assertFalse((root / 'metadata').exists())
            self.assertFalse((root / 'unexpected-install').exists())


if __name__ == '__main__':
    unittest.main()
