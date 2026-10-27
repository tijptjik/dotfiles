"""Install the real standalone runner into an isolated home, without networking."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import tjikup_support
import tjikup

REPO = Path(__file__).resolve().parents[1]
APP = Path(tjikup.__file__).resolve().parents[2]


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.fleet = self.home / '.local/share/chezmoi'
        (self.fleet / 'scripts').mkdir(parents=True)
        shutil.copy2(REPO / 'scripts/install-tjikup.sh', self.fleet / 'scripts')
        shutil.copy2(REPO / 'scripts/ensure-tooltjik.sh', self.fleet / 'scripts')
        shutil.copy2(REPO / 'scripts/cache-install.py', self.fleet / 'scripts')
        (self.fleet / 'tjikup.json').write_text(
            '{"version":1,"steps":[{"id":"unused","command":["false"]}]}'
        )
        self.system = self.home / '.local/share/chezetc/scripts'
        self.system.mkdir(parents=True)
        (self.system / 'tjikup-apply.py').touch()
        self.tools = self.home / 'source-tool'
        shutil.copytree(APP, self.tools / 'apps/tjikup',
                        ignore=shutil.ignore_patterns('dist', '__pycache__'))
        (self.tools / '.git').mkdir()
        self.bin = self.home / 'stubs'
        self.bin.mkdir()
        cache = self.bin / 'gtk-update-icon-cache'
        cache.write_text('#!/bin/sh\nexit 0\n')
        cache.chmod(0o755)
        self.env = {**os.environ, 'HOME': str(self.home),
                    'PATH': str(self.bin) + os.pathsep + os.environ['PATH'],
                    'TOOLTJIK_REPO': str(self.tools), 'TJIKUP_NOTIFY': '0'}
        for name in ('XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME', 'TJIKUP_CONFIG'):
            self.env.pop(name, None)

    def install(self):
        return subprocess.run(['bash', str(self.fleet / 'scripts/install-tjikup.sh')],
                              env=self.env, text=True, capture_output=True)

    def check_installed(self):
        link = self.home / '.config/tjikup/config.json'
        self.assertEqual(link.resolve(), self.fleet / 'tjikup.json')
        result = subprocess.run([str(self.home / '.local/bin/tjikup'), '--check'],
                                env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.home / '.local/share/icons/tjikup.png').is_file())

    def test_existing_checkout_installs_and_replaces_legacy_entrypoint(self):
        executable = self.home / '.local/bin/tjikup'
        executable.parent.mkdir(parents=True)
        executable.write_text('#!/bin/sh\nexit 99\n')
        executable.chmod(0o755)
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.check_installed()
        self.assertEqual(self.install().returncode, 0)

    @unittest.skipUnless(shutil.which('chezmoi'), 'Chezmoi required')
    def test_managed_config_link_matches_installer_exactly(self):
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        source = self.fleet / 'home'
        source.mkdir()
        config = self.home / 'chezmoi.json'
        config.write_text('{}')
        rendered = subprocess.check_output([
            'chezmoi', '--config', str(config), '--source', str(source),
            '--persistent-state', str(self.home / 'state.db'),
            'execute-template', '-f',
            str(REPO / 'home/dot_config/tjikup/symlink_config.json.tmpl'),
        ], env=self.env, text=True).strip()
        link = self.home / '.config/tjikup/config.json'
        self.assertEqual(os.readlink(link), rendered)

    def test_absent_checkout_is_cloned_before_install(self):
        self.env.pop('TOOLTJIK_REPO')
        clone = self.bin / 'git'
        clone.write_text('#!/bin/sh\nset -eu\ntest "$1" = clone\n'
                         'test "$2" = --progress\n'
                         'test "$3" = https://github.com/tijptjik/tooltjik.git\n'
                         'cp -R "$TEST_TOOL_SOURCE" "$4"\n')
        clone.chmod(0o755)
        self.env['TEST_TOOL_SOURCE'] = str(self.tools)
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.home / '.local/share/tooltjik/.git').is_dir())
        self.check_installed()

    def test_missing_system_adapter_leaves_command_untouched(self):
        (self.system / 'tjikup-apply.py').unlink()
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Initialize/update', result.stderr)
        self.assertFalse((self.home / '.local/bin/tjikup').exists())
