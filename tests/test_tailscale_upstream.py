"""Exercise upstream migration using only synthetic package and service commands."""
import os
from pathlib import Path
import runpy
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class TailscaleUpstream(unittest.TestCase):
    def test_source_migration_and_update_failures(self):
        for host in ('fi', 'li', 'si'):
            with self.subTest(host=host), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                rendered = runpy.run_path(str(ROOT / 'scripts/check-task-templates.py'))['render'](host, root)['system-run_21-tailscale-package.fish']
                repo = root / 'tailscale.repo'
                override = root / 'override.conf'
                override.write_text('ExecStart=/usr/bin/tailscaled\n')
                script = root / 'test.fish'
                harness = '''
function sudo; $argv; end
function systemctl; echo systemctl $argv >> "$TRACE"; end
function rpm
    if test "$argv[2]" = --qf
        if test -f "$MIGRATED"
            printf 'Tailscale Inc <info@tailscale.com>'
        else
            printf 'Fedora Project'
        end
    end
end
function dnf
    echo dnf $argv >> "$TRACE"
    if test "$FAIL_DNF" = 1; return 7; end
    if contains -- check-upgrade $argv; return $UPDATE_STATUS; end
    touch "$MIGRATED"
end
function step_run_note; $argv[3..]; end
function step_run; $argv[2..]; end
function step_skip_ok; end
function step_fail; echo failed; end
'''
                script.write_text(rendered.replace('setup_logging linux-tailscale-package', harness).replace('/etc/yum.repos.d/tailscale.repo', str(repo)).replace('/etc/systemd/system/tailscaled.service.d/override.conf', str(override)))
                trace = root / 'trace'
                marker = root / 'migrated'
                env = {**os.environ, 'TRACE': str(trace), 'MIGRATED': str(marker), 'FAIL_DNF': '0', 'UPDATE_STATUS': '0'}
                def run(mode, fail=False, updates=False):
                    return subprocess.run(['fish', '--no-config', str(script), mode], env={**env, 'FAIL_DNF': str(int(fail)), 'UPDATE_STATUS': '100' if updates else '0'}, capture_output=True, text=True)
                self.assertEqual(run('--check').returncode, 1)
                self.assertFalse(trace.exists())
                result = run('--apply')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('--repo=tailscale-stable distro-sync -y tailscale', trace.read_text())
                self.assertIn('/usr/sbin/tailscaled', override.read_text())
                self.assertEqual(run('--check').returncode, 0)
                before = trace.read_text()
                self.assertEqual(run('--apply').returncode, 0)
                self.assertEqual(trace.read_text(), before)
                self.assertEqual(run('--check-update').returncode, 0)
                transactions = trace.read_text().count('distro-sync')
                self.assertEqual(run('--update').returncode, 0)
                self.assertEqual(trace.read_text().count('distro-sync'), transactions)
                self.assertEqual(run('--check-update', fail=True).returncode, 2)
                self.assertEqual(run('--update', fail=True).returncode, 2)
                self.assertEqual(trace.read_text().count('distro-sync'), transactions)
                self.assertEqual(run('--check-update', updates=True).returncode, 1)
                self.assertEqual(run('--update', updates=True).returncode, 0)
                self.assertEqual(trace.read_text().count('distro-sync'), transactions + 1)
                override.write_text('ExecStart=/usr/bin/tailscaled\n')
                self.assertEqual(run('--check').returncode, 1)
                self.assertEqual(run('--apply').returncode, 0)
                self.assertEqual(run('--check').returncode, 0)
