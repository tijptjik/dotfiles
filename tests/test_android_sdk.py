"""Exercise SDK bootstrap and repair in synthetic homes without network access."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'native/helpers/home/android-sdk.fish'
DIGEST = '4e4c464f145a7512b57d088ac6c278c03c9eea610886b35a5e0804e74eedf583'


@unittest.skipUnless(shutil.which('fish') and shutil.which('unzip'), 'requires fish and unzip')
class AndroidSdkTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.home = self.root / 'home'
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.home.mkdir()
        self.sdk = self.home / '.local/share/android-sdk'
        self.trace = self.root / 'trace'
        self.archive = self.root / 'tools.zip'
        manager = '''#!/bin/sh
set -eu
printf '%s\\n' "$*" >> "$SDK_TRACE"
[ "${SDK_FAIL:-0}" = 0 ] || exit 7
sdk=${1#--sdk_root=}
mkdir -p "$sdk/platforms/android-35" "$sdk/build-tools/35.0.0" "$sdk/platform-tools"
printf jar > "$sdk/platforms/android-35/android.jar"
for file in build-tools/35.0.0/aapt2 build-tools/35.0.0/apksigner platform-tools/adb; do
    printf '#!/bin/sh\\nexit 0\\n' > "$sdk/$file"
    chmod +x "$sdk/$file"
done
'''
        with zipfile.ZipFile(self.archive, 'w') as archive:
            for name, content, mode in [
                ('cmdline-tools/bin/sdkmanager', manager, 0o100755),
                ('cmdline-tools/lib/sdkmanager-classpath.jar', 'jar', 0o100644),
            ]:
                entry = zipfile.ZipInfo(name)
                entry.create_system = 3
                entry.external_attr = mode << 16
                archive.writestr(entry, content)
        self.script = self.root / 'installer.fish'
        source = HELPER.read_text().replace(DIGEST, hashlib.sha256(self.archive.read_bytes()).hexdigest())
        source = source.replace('/usr/lib/jvm/temurin-21-jdk', str(self.root / 'jdk'))
        self.script.write_text(source)
        java = self.root / 'jdk/bin/java'
        java.parent.mkdir(parents=True)
        java.write_text('#!/bin/sh\nexit 0\n')
        java.chmod(0o755)
        curl = self.bin / 'curl'
        curl.write_text('''#!/bin/sh
set -eu
while [ "$1" != --output ]; do shift; done
cp "$SDK_ARCHIVE" "$2"
''')
        curl.chmod(0o755)
        self.env = {**os.environ, 'HOME': str(self.home), 'XDG_CACHE_HOME': str(self.root / 'cache'),
                    'PATH': str(self.bin) + ':' + os.environ['PATH'], 'SDK_ARCHIVE': str(self.archive),
                    'SDK_TRACE': str(self.trace), 'TJIKUP_OPERATION': 'install', 'SDK_FAIL': '0'}

    def run_helper(self, *args, success=True):
        result = subprocess.run(['fish', '--no-config', str(self.script), *args], env=self.env,
                                capture_output=True, text=True, timeout=15)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_bootstrap_idempotence_repair_and_scoped_update(self):
        self.run_helper('--check', success=False)
        self.assertFalse(self.sdk.exists())
        self.run_helper()
        self.run_helper('--check')
        first = self.trace.read_text()
        self.assertIn('--install platform-tools platforms;android-35 build-tools;35.0.0', first)
        self.assertNotIn('--update', first)
        self.run_helper()
        self.assertEqual(self.trace.read_text(), first)
        (self.sdk / 'platforms/android-35/android.jar').unlink()
        self.run_helper('--check', success=False)
        self.run_helper()
        self.assertEqual(len(self.trace.read_text().splitlines()), 2)
        self.env['TJIKUP_OPERATION'] = 'update'
        self.run_helper()
        self.assertEqual(len(self.trace.read_text().splitlines()), 3)

    def test_bad_checksum_never_extracts(self):
        self.archive.write_bytes(b'corrupt download')
        result = self.run_helper(success=False)
        self.assertIn('checksum mismatch', result.stderr)
        self.assertFalse((self.sdk / 'cmdline-tools/22.0').exists())
        self.assertFalse(self.trace.exists())

    def test_failed_package_install_is_reported(self):
        self.env['SDK_FAIL'] = '1'
        self.assertEqual(self.run_helper(success=False).returncode, 7)
        self.run_helper('--check', success=False)

    def test_damaged_tools_are_repaired_and_preserved(self):
        self.run_helper()
        (self.sdk / 'cmdline-tools/22.0/lib/sdkmanager-classpath.jar').unlink()
        self.run_helper()
        self.run_helper('--check')
        self.assertEqual(len(list(self.sdk.glob('cmdline-tools/.install.*/previous/bin/sdkmanager'))), 1)

    def test_fish_environment_preserves_explicit_sdk(self):
        config = ROOT / 'native/home/files/.config/fish/conf.d/android-sdk.fish'
        env = {**self.env}
        env.pop('ANDROID_HOME', None)
        command = ['fish', '--no-config', '-c', 'source $argv[1]; printf "%s" "$ANDROID_HOME"', str(config)]
        result = subprocess.run(command, env=env, capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout, str(self.sdk))
        env['ANDROID_HOME'] = str(self.root / 'custom')
        result = subprocess.run(command, env=env, capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout, env['ANDROID_HOME'])

    def test_policy_requires_jdk_phase_and_excludes_servers(self):
        recipes = json.loads((ROOT / 'tjikup/recipes.json').read_text())['recipes']
        for name in ['home:android-sdk', 'home:android-sdk:update']:
            recipe = next(recipe for recipe in recipes if recipe['id'] == name)
            self.assertIn('system:rpm', recipe['needs'])
            self.assertEqual(recipe['roles'], ['desktop', 'laptop'])
        files = json.loads((ROOT / 'native/home/files.json').read_text())
        entry = next(entry for entry in files if entry['path'].endswith('/conf.d/android-sdk.fish'))
        self.assertEqual(entry['when'], 'is_client')
