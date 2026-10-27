"""Exercise canonical checkout bootstrap against a local Git remote."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.env = {**os.environ, 'HOME': str(self.home),
                    'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
                    'GIT_AUTHOR_NAME': 'Test', 'GIT_AUTHOR_EMAIL': 'test@example.org',
                    'GIT_COMMITTER_NAME': 'Test', 'GIT_COMMITTER_EMAIL': 'test@example.org'}
        self.env.pop('TOOLTJIK_REPO', None)
        self.remote = self.home / 'remote'
        self.git('init', '-b', 'main', str(self.remote))
        (self.remote / 'README').write_text('old checkout\n')
        self.commit('initial')
        self.checkout = self.home / 'code/tooltjik'
        self.checkout.parent.mkdir(parents=True)
        self.git('clone', str(self.remote), str(self.checkout))
        app = self.remote / 'apps/notjik/scripts/build.sh'
        app.parent.mkdir(parents=True)
        app.touch()
        self.commit('add Notjik')

    def git(self, *args):
        return subprocess.check_output(['git', *args], env=self.env,
                                       text=True, stderr=subprocess.STDOUT).strip()

    def commit(self, message):
        self.git('-C', str(self.remote), 'add', '.')
        self.git('-C', str(self.remote), 'commit', '-m', message)

    def bootstrap(self):
        return subprocess.run(['bash', '-euc',
            'source "$1"; ensure_tooltjik apps/notjik/scripts/build.sh',
            'bootstrap', str(ROOT / 'scripts/ensure-tooltjik.sh')],
            env=self.env, capture_output=True, text=True)

    def test_missing_checkout_is_cloned(self):
        self.checkout.rename(self.home / 'old-checkout')
        self.env.update({
            'GIT_CONFIG_COUNT': '1',
            'GIT_CONFIG_KEY_0': f'url.{self.remote}.insteadOf',
            'GIT_CONFIG_VALUE_0': 'git@github.com:tijptjik/tooltjik.git',
        })
        result = self.bootstrap()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.checkout / 'apps/notjik/scripts/build.sh').is_file())
        self.assertEqual(self.git('-C', str(self.checkout), 'config', '--get',
                                  'remote.origin.url'),
                         'git@github.com:tijptjik/tooltjik.git')

    def test_complete_checkout_works_offline(self):
        self.git('-C', str(self.checkout), 'fetch', 'origin')
        self.git('-C', str(self.checkout), 'merge', '--ff-only', 'origin/main')
        result = self.bootstrap()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.checkout / 'apps/notjik/scripts/build.sh').is_file())
        # A complete checkout works offline on subsequent applies.
        self.git('-C', str(self.checkout), 'remote', 'set-url', 'origin', '/nonexistent')
        self.assertEqual(self.bootstrap().returncode, 0)

    def test_explicit_checkout_is_not_updated(self):
        self.env['TOOLTJIK_REPO'] = str(self.checkout)
        result = self.bootstrap()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Update', result.stderr)
        self.assertFalse((self.checkout / 'apps/notjik').exists())

    def test_default_checkout_is_not_updated(self):
        result = self.bootstrap()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(self.checkout), result.stderr)
        self.assertFalse((self.checkout / 'apps/notjik').exists())

    def test_legacy_checkout_requires_migration_without_cloning(self):
        legacy = self.home / '.local/share/tooltjik'
        legacy.parent.mkdir(parents=True)
        self.checkout.rename(legacy)
        (legacy / 'README').write_text('personal edits\n')
        result = self.bootstrap()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f'Move {legacy}', result.stderr)
        self.assertFalse(self.checkout.exists())
        self.assertEqual((legacy / 'README').read_text(), 'personal edits\n')

    def test_explicit_legacy_checkout_is_supported(self):
        legacy = self.home / '.local/share/tooltjik'
        legacy.parent.mkdir(parents=True)
        self.checkout.rename(legacy)
        app = legacy / 'apps/notjik/scripts/build.sh'
        app.parent.mkdir(parents=True)
        app.touch()
        self.env['TOOLTJIK_REPO'] = str(legacy)
        self.assertEqual(self.bootstrap().returncode, 0)
        self.assertFalse(self.checkout.exists())

    def test_dirty_checkout_is_preserved(self):
        (self.checkout / 'README').write_text('personal edits\n')
        result = self.bootstrap()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Update', result.stderr)
        self.assertEqual((self.checkout / 'README').read_text(), 'personal edits\n')

    def test_diverged_checkout_is_preserved(self):
        (self.checkout / 'local').touch()
        self.git('-C', str(self.checkout), 'add', '.')
        self.git('-C', str(self.checkout), 'commit', '-m', 'local work')
        before = self.git('-C', str(self.checkout), 'rev-parse', 'HEAD')
        self.assertNotEqual(self.bootstrap().returncode, 0)
        self.assertEqual(self.git('-C', str(self.checkout), 'rev-parse', 'HEAD'), before)
