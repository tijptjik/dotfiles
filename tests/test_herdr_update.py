"""Exercise routine Herdr updates without touching binaries or live sessions."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / 'home/.chezmoiscripts/run_after_28-update-herdr.fish.tmpl'


@unittest.skipUnless(shutil.which('chezmoi') and shutil.which('fish'), 'Chezmoi and Fish required')
class HerdrUpdateTests(unittest.TestCase):
    def run_hook(self, mode='update', host='fi', **overrides):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / 'config.json'
            config.write_text(json.dumps({'data': dict(
                isDesktop=host == 'fi', isLaptop=host == 'li',
                isClient=host != 'si', isServer=host == 'si')}))
            helper = root / '.chezmoihelpers'
            helper.mkdir()
            shutil.copy(ROOT / 'home/.chezmoihelpers/status.fish', helper)
            script = subprocess.check_output([
                'chezmoi', '--config', str(config), '--source', temporary,
                '--persistent-state', str(root / 'state.db'),
                'execute-template', '-f', str(HOOK),
            ], text=True)
            subprocess.run(['fish', '--no-config', '-n'], input=script,
                           text=True, capture_output=True, check=True)
            binary = root / 'herdr'
            binary.write_text('''#!/bin/sh
echo "$*" >> "$CALL_LOG"
case "$*" in
    --version)
        if [ "$MODE" = version-fail ]; then exit 8; fi
        cat "$VERSION_FILE" ;;
    update)
        if [ -t 0 ]; then echo 'unsafe terminal input'; exit 90; fi
        if read -r reply; then echo 'unsafe inherited input'; exit 91; fi
        case "$MODE" in
            update) echo 'herdr 0.9.6' > "$VERSION_FILE" ;;
            unchanged) echo 'already up to date (0.9.5)' ;;
            deferred) echo 'Herdr was not updated.' ;;
            fail) echo 'download failed' >&2; exit 7 ;;
        esac ;;
    *) echo 'unexpected command'; exit 92 ;;
esac
''')
            binary.chmod(0o755)
            version = root / 'version'
            version.write_text('herdr 0.9.5\n')
            env = {**os.environ, 'HOME': temporary,
                   'PATH': temporary + os.pathsep + os.environ['PATH'],
                   'CALL_LOG': str(root / 'calls'), 'VERSION_FILE': str(version),
                   'MODE': mode, 'HERDR_ENV': '', 'TERM_PROGRAM': '',
                   'FLEET_DEFER_HOOKS': '0', 'FLEET_UPGRADE': '0',
                   'TJIKUP_COLOR': '0', 'TJIKUP_NO_SPIN': '1',
                   'TJIKUP_REPORT_FILE': str(root / 'report'), **overrides}
            path = root / 'hook.fish'
            path.write_text(script)
            # Input must never reach the updater, even in a serial apply.
            result = subprocess.run(['fish', '--no-config', str(path)], input='yes\n',
                                    text=True, capture_output=True, env=env, timeout=10)
            calls = (root / 'calls').read_text().splitlines() if (root / 'calls').exists() else []
            report = (root / 'report').read_text() if (root / 'report').exists() else ''
            return result, calls, report

    def test_routine_update_on_all_hosts(self):
        for host in ('fi', 'li', 'si'):
            with self.subTest(host=host):
                result, calls, report = self.run_hook(host=host)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(calls, ['--version', 'update', '--version'])
                self.assertIn('UPDATE\t✓\tHerdr\therdr 0.9.5 → herdr 0.9.6', report)

    def test_unchanged_reports_skip(self):
        result, _, report = self.run_hook('unchanged')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('SKIP\t✓\tHerdr\tno changes (herdr 0.9.5)', report)

    def test_failures_propagate_without_success(self):
        for mode, code in (('fail', 7), ('version-fail', 8)):
            with self.subTest(mode=mode):
                result, _, report = self.run_hook(mode)
                self.assertEqual(result.returncode, code, result.stderr)
                self.assertNotIn('✓', report)
                if mode == 'fail':
                    self.assertIn('download failed', result.stdout)
                    self.assertIn('FAILED', report)

    def test_session_deferral_is_not_reported_as_current(self):
        result, _, report = self.run_hook('deferred')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('WARN\t!\tHerdr\tupdate deferred: stop sessions', report)
        self.assertNotIn('no changes', report)

    def test_inside_herdr_never_invokes_updater(self):
        for env in ({'HERDR_ENV': '1'}, {'TERM_PROGRAM': 'herdr'}):
            with self.subTest(env=env):
                result, calls, report = self.run_hook(**env)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(calls, [])
                self.assertIn('update deferred: rerun tjikup outside Herdr', report)

    def test_native_apply_defers_to_scheduler(self):
        result, calls, report = self.run_hook(FLEET_DEFER_HOOKS='1')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, [])
        self.assertEqual(report, '')

    def test_update_precedes_all_herdr_operations(self):
        plan = {item['id']: item for item in json.loads(
            (ROOT / 'scripts/fleet_update/home-plan.json').read_text())}

        def ancestors(name):
            return {dep for parent in plan[name]['needs']
                    for dep in {parent} | ancestors(parent)}

        self.assertEqual(plan['herdr-update']['file'], HOOK.name)
        for name, item in plan.items():
            if name != 'herdr-update' and 'herdr' in item['resources']:
                self.assertIn('herdr-update', ancestors(name), name)


if __name__ == '__main__':
    unittest.main()
