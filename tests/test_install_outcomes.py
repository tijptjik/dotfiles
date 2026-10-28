"""Verify app outcomes through the real cache, Fish wrapper and fleet summary."""
import contextlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import tjikup_support
from fleet_update.presentation import summary
from fleet_update.hook_tasks import HookTasks
from fleet_update.dag import Result

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('fish'), 'Fish required')
class InstallOutcomeTests(unittest.TestCase):
    def test_all_apps_install_skip_update_and_repair_without_version_bumps(self):
        for app in ('notjik', 'bartjik', 'runtjik', 'tjikup', 'greetjik'):
            with self.subTest(app=app), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source, output = root / 'source', root / 'installed'
                source.mkdir()
                program = source / 'program.py'
                program.write_text('version one')
                installer = root / 'installer.py'
                installer.write_text(
                    'from pathlib import Path\nimport sys\n'
                    's,o,t = map(Path,sys.argv[1:])\n'
                    'o.mkdir(exist_ok=True)\n'
                    '(o/"program.py").write_bytes((s/"program.py").read_bytes())\n'
                    '(o/"program.py").chmod(0o755)\n'
                    'with t.open("a") as f: f.write("install\\n")\n')
                trace, report = root / 'trace', root / 'report'
                command = ['fish', '--no-config', '-c',
                           'source "$argv[1]"; stage_dynamic_note Install INSTALL "$argv[2]" '
                           'python3 "$argv[3]" "$argv[2]" --input "$argv[4]" '
                           '--output "$argv[5]" -- python3 "$argv[6]" '
                           '"$argv[4]" "$argv[5]" "$argv[7]"', '--',
                           str(ROOT / 'home/.chezmoihelpers/status.fish'), app,
                           str(ROOT / 'scripts/cache-install.py'), str(source), str(output),
                           str(installer), str(trace)]
                env = {**os.environ, 'TJIKUP_COLOR': '0', 'TJIKUP_NO_SPIN': '1',
                       'TJIKUP_STATUS_LINES': '1', 'TJIKUP_REPORT_FILE': str(report),
                       'XDG_STATE_HOME': str(root / 'state')}

                def run(expected, count, note):
                    report.unlink(missing_ok=True)
                    result = subprocess.run(command, env=env, text=True, capture_output=True)
                    self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                    outcome = summary(result.stdout)
                    self.assertEqual((outcome.verb, outcome.note), (expected, note))
                    self.assertEqual(report.read_text(), f'{expected}\t✓\t{app}\t{note}\n')
                    self.assertEqual(len(trace.read_text().splitlines()), count)
                    self.assertNotIn('__stage_', result.stdout)
                    # The fleet records the actual result, even though its
                    # manifest planned INSTALL. Skips stay out of the display.
                    parent_report = root / 'fleet-report'
                    parent_report.unlink(missing_ok=True)
                    rendered = io.StringIO()
                    with patch.dict(os.environ, {
                            'TJIKUP_REPORT_FILE': str(parent_report),
                            'TJIKUP_COLOR': '0', 'TJIKUP_PROGRESS': '0',
                            'TJIKUP_ICONS': '0'}), contextlib.redirect_stdout(rendered):
                        hooks = HookTasks(root, root, {})
                        hooks.items[app] = {'label': app, 'verb': 'INSTALL'}
                        hooks.outputs[app] = result.stdout
                        hooks.event(app, Result('done', seconds=.1))
                    if expected == 'SKIP':
                        self.assertEqual(rendered.getvalue(), '')
                    else:
                        self.assertEqual(summary(rendered.getvalue()).verb, expected)
                    self.assertEqual(parent_report.read_text(), f'{expected}\t✓\t{app}\t{note}\n')

                run('INSTALL', 1, 'installed')
                # Python imports are not a new application release.
                for directory in (source, output):
                    bytecode = directory / '__pycache__'
                    bytecode.mkdir()
                    (bytecode / 'program.cpython-313.pyc').write_bytes(b'generated')
                    (directory / 'old.pyc').write_bytes(b'generated')
                run('SKIP', 1, 'no changes')
                (output / '__pycache__/program.cpython-313.pyc').write_bytes(b'new cache')
                run('SKIP', 1, 'no changes')
                program.write_text('version two')
                run('UPDATE', 2, 'updated')
                run('SKIP', 2, 'no changes')
                # A rebuild that produces identical installed files is a skip.
                (source / 'tests.txt').write_text('only build inputs changed')
                run('SKIP', 3, 'no changes')
                run('SKIP', 3, 'no changes')
                (output / 'program.py').unlink()
                run('UPDATE', 4, 'updated')
                (output / 'program.py').chmod(0o644)
                run('UPDATE', 5, 'updated')
                run('SKIP', 5, 'no changes')

    def test_bartjik_cache_preserves_managed_unit_and_repairs_missing_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scripts = root / 'scripts'
            scripts.mkdir()
            for name in ('cache-install.py', 'install-bartjik.sh', 'ensure-tjikos.sh'):
                shutil.copy2(ROOT / 'scripts' / name, scripts / name)
            unit = root / 'home/dot_config/systemd/user/bartjik.service'
            unit.parent.mkdir(parents=True)
            unit.write_text('managed Fish wrapper\n')
            tools = root / 'tools'
            (tools / '.git').mkdir(parents=True)
            build = tools / 'apps/bartjik/scripts/build.sh'
            build.parent.mkdir(parents=True)
            build.write_text('echo build >> "$CALL_LOG"\n')
            install = tools / 'scripts/install.sh'
            install.parent.mkdir()
            install.write_text('''set -eu
echo install >> "$CALL_LOG"
mkdir -p "$HOME/.local/bin" "$HOME/.local/lib/bartjik" "$HOME/.config/systemd/user"
printf binary > "$HOME/.local/bin/bartjik"
printf control > "$HOME/.local/bin/bartjikctl"
printf code > "$HOME/.local/lib/bartjik/bartjik.py"
printf upstream > "$HOME/.config/systemd/user/bartjik.service"
''')
            stubs = root / 'bin'
            stubs.mkdir()
            for name, body in {'quickshell': 'exit 0', 'pkill': 'exit 1',
                               'systemctl': 'case "$*" in *is-active*) exit 3;; esac\nexit 0'}.items():
                path = stubs / name
                path.write_text('#!/bin/sh\n' + body + '\n')
                path.chmod(0o755)
            home, trace = root / 'live-home', root / 'trace'
            env = {**os.environ, 'HOME': str(home), 'TJIKOS_REPO': str(tools),
                   'CALL_LOG': str(trace), 'XDG_STATE_HOME': str(root / 'state'),
                   'PATH': str(stubs) + os.pathsep + os.environ['PATH']}

            def run(expected, builds):
                result = subprocess.run(['bash', str(scripts / 'install-bartjik.sh')],
                                        env=env, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                self.assertEqual(summary(result.stdout).verb, expected)
                self.assertEqual(trace.read_text().splitlines().count('build'), builds)
                deployed = home / '.config/systemd/user/bartjik.service'
                self.assertEqual(deployed.read_bytes(), unit.read_bytes())

            run('INSTALL', 1)
            run('SKIP', 1)
            bytecode = home / '.local/lib/bartjik/__pycache__'
            bytecode.mkdir()
            (bytecode / 'bartjik.pyc').write_bytes(b'generated')
            run('SKIP', 1)
            unit.write_text('updated managed Fish wrapper\n')
            run('UPDATE', 2)
            (home / '.local/bin/bartjikctl').unlink()
            run('UPDATE', 3)
            run('SKIP', 3)


if __name__ == '__main__':
    unittest.main()
