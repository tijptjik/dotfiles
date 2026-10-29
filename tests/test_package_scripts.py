"""Execute rendered package phases with synthetic commands, never package managers."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

@unittest.skipUnless(shutil.which('fish'), 'render tools required')
class PackageScripts(unittest.TestCase):
    def test_rpm_and_flatpak_install_and_update_are_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            import runpy
            rendered = runpy.run_path(str(ROOT/'scripts/check-task-templates.py'))['render']('fi',root)['system-run_30-system-update.fish']
            binpath = root / 'bin'; binpath.mkdir()
            # Presence checks are local. All mutating commands are intercepted by
            # the same stage helpers used by the real script.
            for name, body in {'rpm': 'case "$*" in *7zip*) echo 7zip; exit 0;; esac; exit 1',
                               'flatpak': 'case "$*" in *com.obsproject.Studio*) exit 0;; esac; exit 1',
                               'gum': 'exit 0'}.items():
                path = binpath / name
                path.write_text('#!/bin/sh\n' + body + '\n'); path.chmod(0o755)
            harness = '''
function setup_logging; end
function step_header; end
function step_skip_ok; end
function step_ok; end
function step_result_note; end
function step_run_quiet
    echo (string join ' ' -- $argv) >> "$TRACE"
end
function step_run_dnf_update
    echo (string join ' ' -- $argv) >> "$TRACE"
end
function step_run_as
    echo (string join ' ' -- $argv) >> "$TRACE"
end
function snapshot_rpm_versions
    printf '7zip\\t1\\n' > $argv[1]
end
function snapshot_flatpak_versions
    printf 'com.obsproject.Studio\\t1\\n' > $argv[1]
end
function snapshot_flatpak_refs
    printf '' > $argv[1]
end
function count_removed_entries
    set -g package_change_count 0
end
function report_package_updates
    set -g package_update_count 0
end
'''
            script = root / 'phase.fish'
            script.write_text(rendered.replace('setup_logging linux-dnf-update', harness, 1))
            for ecosystem in ['rpm', 'flatpak']:
                for operation in ['install', 'update']:
                    with self.subTest(ecosystem=ecosystem, operation=operation):
                        trace = root / 'trace'; trace.write_text('')
                        result = subprocess.run(['fish', '--no-config', str(script)], text=True,
                            capture_output=True, timeout=30, env={**os.environ, 'HOME':str(root),
                            'PATH': str(binpath)+':/usr/bin:/bin', 'TRACE':str(trace),
                            'FLEET_SYSTEM_PHASE':ecosystem, 'TJIKUP_OPERATION':operation})
                        self.assertEqual(result.returncode, 0, result.stderr)
                        calls = trace.read_text()
                        if operation == 'install':
                            self.assertIn(' install ', calls)
                            self.assertNotIn(' update ', calls)
                            self.assertNotIn('7zip', calls)
                            self.assertNotIn('com.obsproject.Studio', calls)
                        else:
                            self.assertIn(' update ', calls)
                            self.assertNotIn(' install ', calls)

    def test_cargo_partial_group_never_updates_installed_siblings_during_install(self):
        source = ROOT / 'native/tasks/home/run_after_29-rust-packages.fish.j2'
        text = source.read_text()
        body = text[text.index('set rust_packages'):text.index('stage_dynamic_note')]
        for operation, expected in [('install', 'dysk'), ('update', 'serie')]:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory); calls = root / 'calls'
                (root / 'cargo').write_text('''#!/bin/sh
if [ "$*" = 'install --list' ]; then printf 'serie v1.0:\\n'; else echo "$*" >> "$TRACE"; fi
'''); (root / 'cargo').chmod(0o755)
                (root / 'serie').write_text('#!/bin/sh\nexit 0\n'); (root / 'serie').chmod(0o755)
                result = subprocess.run(['fish', '--no-config', '-c', body+'\nsync_rust_packages'],
                    capture_output=True, text=True, env={**os.environ, 'PATH':str(root)+':/usr/bin:/bin',
                    'TRACE':str(calls),'FLEET_UPGRADE':'1' if operation=='update' else '0', 'TJIKUP_OPERATION':operation})
                self.assertEqual(result.returncode,0,result.stderr)
                invoked = calls.read_text().splitlines()
                self.assertEqual(len(invoked),1)
                self.assertTrue(invoked[0].endswith(expected))


class BatchedRpmSnapshots(unittest.TestCase):
    def test_snapshot_uses_one_query_and_ignores_missing_and_duplicate_names(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rpm = root / 'rpm'
            rpm.write_text("#!/bin/sh\necho call >> \"$TRACE\"\nprintf 'alpha\\t1\\npackage absent is not installed\\nalpha\\t2\\nbeta\\t3\\n'\nexit 1\n")
            rpm.chmod(0o755)
            output = root / 'snapshot'
            helper = ROOT / 'native/tasks/assets/system/chezmoitemplates/package_reporting.fish'
            result = subprocess.run(['fish','--no-config','-c',
                'source $argv[1]; snapshot_rpm_versions $argv[2] alpha absent alpha beta',
                '--',str(helper),str(output)], capture_output=True,text=True,
                env={**os.environ,'PATH':str(root)+':/usr/bin:/bin','TRACE':str(root/'calls')})
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(output.read_text(),'alpha\t1\nbeta\t3\n')
            self.assertEqual((root/'calls').read_text(),'call\n')
