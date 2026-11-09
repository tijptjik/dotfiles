"""Rehearse first installation in synthetic homes, without upstream execution."""
import native_render
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HerdrAppInstallTests(unittest.TestCase):
    def run_install(self, host, *, installed=False, fail_download=False, fail_install=False):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / 'home'
            binaries = home / '.local/bin'
            binaries.mkdir(parents=True)
            mock = root / 'mock'
            mock.mkdir()
            trace = root / 'trace'
            curl = mock / 'curl'
            curl.write_text('''#!/bin/sh
printf '%s\\n' "$*" >> "$TRACE"
output=''
component=''
while [ "$#" -gt 0 ]; do
  case "$1" in
    */core/install.sh) component=herdr-core ;;
    */app/install.sh) component=herdr-app ;;
    -o) shift; output=$1 ;;
  esac
  shift
done
if [ "$FAIL_DOWNLOAD" = 1 ]; then
  printf 'touch "$HOME/partial-executed"\\n' > "$output"
  exit 22
fi
if [ "$FAIL_INSTALL" = 1 ]; then
  printf 'exit 1\\n' > "$output"
  exit 0
fi
cat > "$output" <<EOF
mkdir -p "$HOME/.local/bin"
printf '#!/bin/sh\\nexit 0\\n' > "$HOME/.local/bin/$component"
chmod +x "$HOME/.local/bin/$component"
EOF
''')
            curl.chmod(0o755)
            if installed:
                for name in ('herdr-core', 'herdr-app'):
                    binary = binaries / name
                    binary.write_text('#!/bin/sh\nexit 0\n')
                    binary.chmod(0o755)
            config = root / 'context.json'
            config.write_text(json.dumps({'data': {
                'isDesktop': host == 'fi', 'isLaptop': host == 'li',
                'isServer': host == 'si', 'isClient': host != 'si'}}))
            # Use native MiniJinja, with all state and files in the fixture.
            env = {**os.environ, 'HOME': str(home), 'TRACE': str(trace),
                   'XDG_STATE_HOME': str(root / 'state'),
                   'XDG_CACHE_HOME': str(root / 'cache'),
                   'XDG_CONFIG_HOME': str(home / '.config'),
                   'FAIL_DOWNLOAD': str(int(fail_download)),
                   'FAIL_INSTALL': str(int(fail_install)),
                   'TJIKUP_NOTIFY': '0', 'TJIKUP_NO_SPIN': '1'}
            script = subprocess.check_output([
                'render-native', '--config', str(config), 'execute-template',
                '-f', str(ROOT / 'native/tasks/home/install-herdr-app.fish.j2')],
                env=env, text=True)
            env['PATH'] = f'{mock}:/usr/bin:/bin'
            result = subprocess.run(['fish', '--no-config', '-c', script],
                                    env=env, text=True, capture_output=True)
            calls = trace.read_text().splitlines() if trace.exists() else []
            self.assertFalse((home / 'partial-executed').exists())
            return result, calls, [(binaries / name).exists()
                                   for name in ('herdr-core', 'herdr-app')]

    def test_installs_core_before_app_on_every_host(self):
        for host in ('fi', 'li', 'si'):
            with self.subTest(host=host):
                result, calls, present = self.run_install(host)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(present, [True, True])
                self.assertEqual(len(calls), 2)
                self.assertIn('/core/install.sh', calls[0])
                self.assertIn('/app/install.sh', calls[1])

    def test_existing_install_is_not_replaced(self):
        result, calls, _ = self.run_install('fi', installed=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(calls, [])

    def test_download_failure_does_not_execute_partial_installer(self):
        result, calls, present = self.run_install('li', fail_download=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(calls), 1)
        self.assertEqual(present, [False, False])

    def test_core_failure_prevents_app_install(self):
        result, calls, present = self.run_install('si', fail_install=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(calls), 1)
        self.assertEqual(present, [False, False])
