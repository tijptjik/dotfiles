import fcntl
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'native/home/files/.local/bin/reclaim-diskspace'
FISH = shutil.which('fish')
BUN = shutil.which('bun')
TMPFILES = shutil.which('systemd-tmpfiles')


@unittest.skipUnless(FISH, 'requires fish')
class ReclaimDiskspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='reclaim-test-')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.bin = self.home / 'bin'
        self.bin.mkdir()
        (self.home / 'tmp').mkdir()
        for name in ('mktemp', 'rm', 'realpath', 'id'):
            (self.bin / name).symlink_to(shutil.which(name))
        self.stub('pgrep', 'exit 1')
        self.env = {
            'PATH': str(self.bin), 'HOME': str(self.home),
            'TMPDIR': str(self.home / 'tmp'),
            'XDG_CACHE_HOME': str(self.home / 'cache'),
            'XDG_CONFIG_HOME': str(self.home / 'config'),
            'XDG_DATA_HOME': str(self.home / 'data'),
            'BUN_INSTALL': str(self.home / 'bun'),
            'BUN_INSTALL_CACHE_DIR': str(self.home / 'bun/install/cache'),
        }

    def stub(self, name, body):
        path = self.bin / name
        path.write_text('#!/bin/sh\n' + body + '\n')
        path.chmod(0o755)

    def run_cleanup(self, *args):
        return subprocess.run([FISH, '--no-config', str(SCRIPT), *args],
                              cwd=self.home, env=self.env, capture_output=True, text=True)

    @unittest.skipUnless(BUN, 'requires bun')
    def test_bun_cache_cleared_without_home_manifest(self):
        (self.bin / 'bun').symlink_to(BUN)
        cache = Path(self.env['BUN_INSTALL_CACHE_DIR'])
        cache.mkdir(parents=True)
        sentinel = cache / 'disposable'
        sentinel.write_text('cached package')
        dependency = self.home / 'project/node_modules/keep'
        dependency.parent.mkdir(parents=True)
        dependency.write_text('installed package')
        result = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(sentinel.exists())
        self.assertFalse((self.home / 'package.json').exists())
        self.assertEqual(list((self.home / 'tmp').iterdir()), [])
        self.assertEqual(dependency.read_text(), 'installed package')

    def test_dry_run_never_invokes_bun_or_creates_context(self):
        self.stub('bun', 'touch "$HOME/bun-invoked"; exit 42')
        (self.bin / 'touch').symlink_to(shutil.which('touch'))
        result = self.run_cleanup('--dry-run')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('[dry-run] bun pm cache rm', result.stdout)
        self.assertFalse((self.home / 'bun-invoked').exists())
        self.assertEqual(list((self.home / 'tmp').iterdir()), [])

    def test_bun_failure_is_reported_and_context_removed(self):
        self.stub('bun', 'exit 42')
        result = self.run_cleanup()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('Cleanup finished with 1 failed step(s).', result.stderr)
        self.assertIn('Cleaning up Flatpak dependencies...', result.stdout)
        self.assertEqual(list((self.home / 'tmp').iterdir()), [])

    def mock_sudo(self):
        # Only fixture commands are reachable; never invoke real sudo.
        self.stub('sudo', 'exec "$@"')

    @unittest.skipUnless(TMPFILES, 'requires systemd-tmpfiles')
    def test_coredump_cleanup_preserves_locked_dumps_and_other_data(self):
        self.mock_sudo()
        self.stub('systemd-tmpfiles',
                  f'exec {shlex.quote(TMPFILES)} --root="$HOME/system-root" "$@"')
        root = self.home / 'system-root'
        cores = root / 'var/lib/systemd/coredump'
        cores.mkdir(parents=True)
        finished = cores / 'core.finished'
        active = cores / 'core.active'
        journal = root / 'var/log/journal/keep'
        journal.parent.mkdir(parents=True)
        for path in (finished, active, journal):
            path.write_text('fixture')
        # A symlink inside the dump directory must not expose unrelated data.
        (cores / 'linked-journal').symlink_to(journal.parent)
        with active.open() as handle:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.run_cleanup('--dry-run')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('[dry-run] tmpfiles rule:', result.stdout)
            self.assertTrue(finished.exists())
            result = self.run_cleanup()
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(finished.exists())
            self.assertTrue(active.exists())
            self.assertTrue(cores.is_dir())
            self.assertEqual(journal.read_text(), 'fixture')
        # A redirected coredump directory is also left alone.
        active.unlink()
        cores.rmdir()
        cores.symlink_to('../../log/journal', target_is_directory=True)
        result = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(journal.read_text(), 'fixture')

    def test_coredump_failure_is_reported_and_cleanup_continues(self):
        self.mock_sudo()
        self.stub('systemd-tmpfiles', 'exit 42')
        result = self.run_cleanup()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('Cleanup finished with 1 failed step(s).', result.stderr)
        self.assertIn('Cleaning up Flatpak dependencies...', result.stdout)

    def test_automatic_only_cleans_caches_without_interactive_sudo(self):
        # Record every package/system invocation instead of touching the host.
        for name in ('sudo', 'dnf', 'docker', 'flatpak', 'cliphist', 'systemd-tmpfiles'):
            self.stub(name, 'printf "%s\\n" "$0 $*" >> "$HOME/commands"')
        self.stub('df', 'printf "Mounted Avail\\n/home 104857600\\n/home 104857600\\n"')
        (self.bin / 'awk').symlink_to(shutil.which('awk'))
        result = self.run_cleanup('--automatic')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        commands = (self.home / 'commands').read_text().splitlines()
        self.assertEqual(len(commands), 2, commands)
        self.assertTrue(any('sudo -n systemd-tmpfiles --clean' in line for line in commands))
        self.assertTrue(any('sudo -n dnf clean all' in line for line in commands))
        self.assertIn('net free-space change: 0 MiB', result.stdout)
        for forbidden in ('autoremove', 'repoquery', 'prune', 'repair', 'cliphist'):
            self.assertNotIn(forbidden, '\n'.join(commands))

    def test_automatic_dry_run_and_clipboard_guard(self):
        self.stub('sudo', 'exit 42')
        self.stub('systemd-tmpfiles', 'exit 42')
        result = self.run_cleanup('--automatic', '--dry-run')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('[dry-run] sudo -n systemd-tmpfiles --clean', result.stdout)
        self.assertNotIn('net free-space change:', result.stdout)
        result = self.run_cleanup('--automatic', '--clipboard-history')
        self.assertEqual(result.returncode, 2)

    def test_monthly_policy_runs_after_updates_and_existing_archive_gate(self):
        recipes = json.loads((ROOT / 'tjikup/recipes.json').read_text())['recipes']
        recipes += json.loads((ROOT / 'system/tjikup/recipes.json').read_text())['recipes']
        task = next(r for r in recipes if r['id'] == 'home:reclaim-diskspace')
        self.assertEqual(task['interval_seconds'], 30 * 86400)
        self.assertIn('--automatic', task['apply'])
        self.assertEqual(task['operation'], 'update')
        self.assertIn('home:archive-restore', task['after'])
        self.assertIn('home:files', task['after'])
        for recipe in recipes:
            if recipe.get('operation') == 'update' and recipe is not task and recipe['id'] != 'system:release':
                self.assertIn(recipe['id'], task['after'])
        release = next(r for r in recipes if r['id'] == 'system:release')
        self.assertIn(task['id'], release['after'])
