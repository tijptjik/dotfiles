"""Exercise post-upgrade plugin builds with synthetic RPMs and compositor IPC."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'native/helpers/home/hyprland-scrolling-gaps.sh'


class HyprlandPluginUpdateTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.home = self.root / 'home'
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.home.mkdir()
        self.repo = self.root / 'repo'
        self.source = self.repo / 'native/home/files/.local/share/hypr/plugins/scrolling-gaps'
        self.source.mkdir(parents=True)
        (self.source / 'main.cpp').write_text('source v1')
        (self.source / 'build.sh').write_text('''#!/bin/bash
set -eu
echo build >> "$TRACE"
[[ "${FAIL_BUILD:-0}" == 0 ]] || exit 7
sleep "${BUILD_DELAY:-0}"
printf '%s\\n%s\\n' "$COMMIT" "$(cat "$(dirname "$0")/main.cpp")" > "$1"
''')
        self.output = self.home / '.local/lib/hypr/scrolling-gaps-local.so'
        self.cache = self.root / 'cache'
        self.trace = self.root / 'trace'
        self.loaded = self.root / 'loaded'
        self.env = {**os.environ, 'HOME': str(self.home), 'DOTJIK_REPO': str(self.repo),
                    'XDG_CACHE_HOME': str(self.cache), 'PATH': str(self.bin) + ':' + os.environ['PATH'],
                    'TRACE': str(self.trace), 'LOADED': str(self.loaded), 'CXX': 'true',
                    'COMMIT': 'a' * 40, 'ABI': 'abi-a', 'RUNNING_ABI': 'abi-a',
                    'HYPRLAND_INSTANCE_SIGNATURE': 'session-a'}
        self.command('Hyprland', 'printf \'{"commit":"%s","abiHash":"%s"}\' "$COMMIT" "$ABI"')
        self.command('rpm', 'printf "%s-devel-1.0-1.test.x86_64" "${@: -1}"')
        self.command('rpmkeys', 'exit 0')
        self.command('dnf', '''echo download >> "$TRACE"
[[ "${FAIL_DOWNLOAD:-0}" == 0 ]] || exit 9
mkdir -p "$3"
touch "$3/headers.rpm"
printf '%s\\n' "$@" > "$TRACE.download"
''')
        self.command('rpm2cpio', 'printf archive')
        self.command('cpio', '''cat >/dev/null
mkdir -p usr/include/hyprland/src
printf '#define GIT_COMMIT_HASH "%s"\\n' "${HEADER_COMMIT:-$COMMIT}" > usr/include/hyprland/src/version.h
''')
        self.command('hyprctl', '''if [[ "$*" == '-j version' ]]; then
    printf '{"abiHash":"%s"}' "$RUNNING_ABI"
elif [[ "$*" == '-j plugin list' ]]; then
    if [[ -f "$LOADED" ]]; then echo '[{"name":"scrolling-gaps"}]'; else echo '[]'; fi
elif [[ "$1" == plugin ]]; then
    echo "$2" >> "$TRACE"
    if [[ "$2" == unload ]]; then rm -f "$LOADED"; echo ok
    elif [[ "${FAIL_LOAD:-0}" == 1 && ! -e "$LOADED.failed" ]]; then
        touch "$LOADED.failed"; echo 'error: load failed'
    else touch "$LOADED"; echo ok; fi
elif [[ "$1" == scrolling-gaps:state ]]; then echo '[]'
else exit 11
fi
''')

    def command(self, name, script):
        path = self.bin / name
        path.write_text('#!/bin/bash\nset -eu\n' + script + '\n')
        path.chmod(0o755)

    def run_helper(self, *args, code=0):
        result = subprocess.run(['bash', str(HELPER), *args], env=self.env,
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result

    def events(self):
        return self.trace.read_text().splitlines() if self.trace.exists() else []

    def test_build_load_reuse_and_missing_binary_repair(self):
        self.run_helper('--check', code=1)
        self.assertFalse(self.cache.exists())
        self.run_helper()
        self.run_helper('--check')
        self.assertEqual(self.events(), ['download', 'build', 'load'])
        self.run_helper()
        self.assertEqual(self.events(), ['download', 'build', 'load'])
        self.output.unlink()
        self.run_helper()
        self.assertEqual(self.events().count('build'), 2)
        self.assertEqual(self.events().count('download'), 1)
        self.assertIn('hyprland-devel-1.0-1.test.x86_64', Path(str(self.trace) + '.download').read_text())

    def test_source_and_binary_changes_rebuild(self):
        self.run_helper()
        (self.source / 'main.cpp').write_text('source v2')
        self.run_helper('--check', code=1)
        self.run_helper()
        self.assertIn('source v2', self.output.read_text())
        self.assertEqual(self.events()[-3:], ['build', 'unload', 'load'])
        self.output.write_text('broken')
        self.run_helper('--check', code=1)
        self.run_helper()
        self.assertIn('source v2', self.output.read_text())

    def test_upgrade_preserves_old_session_until_restart(self):
        self.run_helper()
        self.env.update(COMMIT='b' * 40, ABI='abi-b')
        # The SDK cache changes with the exact installed RPM versions.
        self.command('rpm', 'printf "%s-devel-2.0-1.test.x86_64" "${@: -1}"')
        result = self.run_helper()
        self.assertIn('log out and back in', result.stdout)
        self.assertEqual(self.events()[-2:], ['download', 'build'])
        self.assertTrue(self.loaded.exists())
        self.assertIn('b' * 40, self.output.read_text())
        self.env.update(RUNNING_ABI='abi-b', HYPRLAND_INSTANCE_SIGNATURE='session-b')
        self.loaded.unlink()
        self.run_helper()
        self.assertEqual(self.events()[-1], 'load')
        self.assertEqual(self.events().count('build'), 2)

    def test_headless_build_and_later_activation(self):
        self.env['HYPRLAND_INSTANCE_SIGNATURE'] = ''
        self.assertIn('next login', self.run_helper().stdout)
        self.assertEqual(self.events(), ['download', 'build'])
        self.env['HYPRLAND_INSTANCE_SIGNATURE'] = 'session-a'
        self.run_helper()
        self.assertEqual(self.events()[-1], 'load')

    def test_failed_compilation_preserves_previous_binary_and_retries(self):
        self.run_helper()
        previous = self.output.read_bytes()
        (self.source / 'main.cpp').write_text('source v2')
        self.env['FAIL_BUILD'] = '1'
        self.run_helper(code=7)
        self.assertEqual(self.output.read_bytes(), previous)
        self.run_helper('--check', code=1)
        self.env['FAIL_BUILD'] = '0'
        self.run_helper()
        self.assertIn('source v2', self.output.read_text())

    def test_bad_headers_and_failed_download_never_publish(self):
        self.env['HEADER_COMMIT'] = 'b' * 40
        self.run_helper(code=1)
        self.assertFalse(self.output.exists())
        self.assertNotIn('build', self.events())
        self.env['FAIL_DOWNLOAD'] = '1'
        self.run_helper(code=9)
        self.assertFalse(self.output.exists())

    def test_failed_load_restores_previous_binary_and_fails_recipe(self):
        self.run_helper()
        previous = self.output.read_bytes()
        (self.source / 'main.cpp').write_text('source v2')
        self.env['FAIL_LOAD'] = '1'
        self.run_helper(code=1)
        self.assertEqual(self.output.read_bytes(), previous)
        self.assertTrue(self.loaded.exists())
        self.assertEqual(self.events()[-3:], ['unload', 'load', 'load'])
        self.run_helper('--check', code=1)
        self.env['FAIL_LOAD'] = '0'
        self.run_helper()
        self.assertIn('source v2', self.output.read_text())

    def test_lock_serializes_duplicate_builds(self):
        self.env.update(HYPRLAND_INSTANCE_SIGNATURE='', BUILD_DELAY='0.2')
        processes = [subprocess.Popen(['bash', str(HELPER)], env=self.env,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                     for _ in range(2)]
        for process in processes:
            out, err = process.communicate(timeout=20)
            self.assertEqual(process.returncode, 0, out + err)
        self.assertEqual(self.events(), ['download', 'build'])

    def test_recipe_follows_rpm_updates_and_excludes_servers(self):
        recipes = json.loads((ROOT / 'tjikup/recipes.json').read_text())['recipes']
        recipe = next(r for r in recipes if r['id'] == 'home:hyprland-scrolling-gaps:update')
        self.assertEqual(recipe['roles'], ['desktop', 'laptop'])
        self.assertEqual(recipe['part_of'], 'system:rpm')
        self.assertIn('system:rpm:update', recipe['needs'])
        self.assertEqual(recipe['operation'], 'update')
        self.assertNotIn('check', recipe)  # Activation must also run after a fresh login.
        cleanup = next(r for r in recipes if r['id'] == 'home:reclaim-diskspace')
        self.assertIn(recipe['id'], cleanup['after'])
