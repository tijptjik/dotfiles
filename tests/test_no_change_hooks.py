import native_render
"""No-change reruns perform checks and never invoke unnecessary mutators."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class NoChangeHooksTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.home = self.root / 'home'
        self.home.mkdir()
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.trace = self.root / 'trace'
        self.env = {**os.environ, 'HOME': str(self.home), 'PATH': str(self.bin) + ':' + os.environ['PATH'],
                    'TRACE': str(self.trace), 'TJIKUP_NO_SPIN': '1', 'TJIKUP_COLOR': '0',
                    'TJIKUP_STATUS_LINES': '1', 'TJIKUP_REPORT_FILE': str(self.root / 'report'),
                    'FLEET_DEFER_HOOKS': '0', 'FLEET_UPGRADE': '0'}
        self.config = self.root / 'config.json'
        self.config.write_text(json.dumps({'data': {'isClient': True, 'isDesktop': True,
                                                   'isLaptop': False, 'isServer': False}}))

    def stub(self, name, code):
        path = self.bin / name
        path.write_text(f'#!{sys.executable}\n' + code)
        path.chmod(0o755)
        return path

    def script(self, name):
        path = ROOT / 'native/tasks/home' / name
        if not name.endswith('.j2'):
            return path.read_text()
        rendered = subprocess.check_output([
            'render-native', '--config', str(self.config), '--source', str(self.root),
            '--persistent-state', str(self.root / 'state.db'),
            'execute-template', '-f', str(path)], text=True)
        rendered = rendered.replace('test -S', 'test -f')  # Mock socket readiness, not a live Herdr session.
        return rendered.replace(str(self.root / '.render-nativehelpers/status.fish'),
                                str(ROOT / 'native/helpers/home/status.fish'))

    def run_hook(self, name, *, prefix='', **env):
        result = subprocess.run(['fish', '--no-config', '-c', prefix + self.script(name)],
                                env={**self.env, **env}, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def calls(self):
        return self.trace.read_text().splitlines() if self.trace.exists() else []

    def test_python_checks_environment_before_sync_and_reports_package_count(self):
        self.stub('uv', r'''import json,os,sys
from pathlib import Path
args=sys.argv[1:]
with open(os.environ['TRACE'],'a') as f: f.write(' '.join(args)+'\n')
if args[0]=='sync' and '--check' in args: sys.exit(int(os.environ.get('OUTDATED','0')))
if args[:2]==['pip','list']: print(json.dumps([{'name':'one'},{'name':'two'}]))
''')
        output = self.run_hook('run_after_30-python-packages.fish.j2')
        self.assertIn('SKIP    ✓ Python', output)
        self.assertIn('2 pkgs; no changes', output)
        self.assertFalse(any(row.startswith('sync ') and '--check' not in row for row in self.calls()))
        output = self.run_hook('run_after_30-python-packages.fish.j2', OUTDATED='1')
        self.assertIn('SYNC    ✓ Python', output)
        self.assertTrue(any(row.startswith('sync ') and '--check' not in row for row in self.calls()))

    def test_codex_lb_keeps_current_runtime_and_reports_unchanged_upgrade(self):
        runtime = self.home / '.codex-lb/runtime/bin'
        runtime.mkdir(parents=True)
        version = subprocess.check_output(['/usr/bin/python3', '-c',
            'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'], text=True).strip()
        python = runtime / 'python'
        python.write_text(f'#!{sys.executable}\nimport sys\nprint({version!r} if "sys.version_info" in sys.argv[-1] else "1.0")\n')
        python.chmod(0o755)
        (runtime / 'codex-lb').write_text('#!/bin/sh\nexit 0\n')
        (runtime / 'codex-lb').chmod(0o755)
        self.stub('uv', "import os,sys\nwith open(os.environ['TRACE'],'a') as f: f.write(' '.join(sys.argv[1:])+'\\n')\n")
        output = self.run_hook('run_after_33-codex-lb.fish.j2')
        self.assertIn('SKIP    ✓ Codex LB', output)
        self.assertEqual(self.calls(), [])
        output = self.run_hook('run_after_33-codex-lb.fish.j2', FLEET_UPGRADE='1')
        self.assertIn('SKIP    ✓ Codex LB', output)
        self.assertTrue(any('--upgrade-package codex-lb' in call for call in self.calls()))

    def test_herdr_does_not_relink_an_enabled_plugin_at_the_right_path(self):
        directory = self.home / '.config/herdr'
        directory.mkdir(parents=True)
        (directory / 'herdr.sock').touch()
        self.stub('herdr', r'''import json,os,sys
from pathlib import Path
args=sys.argv[1:]
with open(os.environ['TRACE'],'a') as f: f.write(' '.join(args)+'\n')
ids=['herdr-file-viewer','herdr-navigator','herdr-spreader','local-files']
print(json.dumps({'result':{'plugins':[{'plugin_id':id,'enabled':True,
'plugin_root':str(Path.home()/'.config/herdr/plugins/local/local-files')} for id in ids]}}))
''')
        output = self.run_hook('run_after_32-provision-herdr-plugins.fish.j2')
        output += self.run_hook('configure-herdr.fish.j2')
        self.assertNotIn('CONFIG', output)
        self.assertEqual(output.count('SKIP'), 4)
        self.assertTrue(all(call == 'plugin list --json' for call in self.calls()))

    def test_installed_sublime_and_archive_dependency_are_skipped(self):
        output = self.run_hook('run_after_29-install-sublime-text.fish.j2',
                               prefix='function rpm; return 0; end\nfunction sudo; exit 97; end\n')
        self.assertIn('SKIP    ✓ Sublime Text', output)
        # Replace only the dependency probe; never run the live package manager.

    def test_font_and_icon_native_freshness_checks_report_skips(self):
        self.stub('fc-cache', "print('/fixture/fonts: skipping, existing cache is valid: 1 fonts, 0 dirs')\n")
        self.assertIn('SKIP    ✓ Fonts', self.run_hook('run_after_72-refresh-user-fonts.fish'))
        icon = self.home / '.local/share/icons/hicolor/256x256/apps/tjikup-notification.png'
        icon.parent.mkdir(parents=True)
        icon.write_bytes(b'fixture')
        self.stub('gtk-update-icon-cache', 'pass\n')
        self.assertIn('SKIP    ✓ Icon cache', self.run_hook('run_after_36-tjikup-icon-cache.fish'))
        self.stub('fc-cache', "print('/fixture/fonts: caching, new cache contents: 2 fonts, 0 dirs')\n")
        self.assertIn('UPDATE  ✓ Fonts', self.run_hook('run_after_72-refresh-user-fonts.fish'))
        self.stub('gtk-update-icon-cache', "from pathlib import Path\n(Path.home()/'.local/share/icons/hicolor/icon-theme.cache').write_bytes(b'cache')\n")
        self.assertIn('UPDATE  ✓ Icon cache', self.run_hook('run_after_36-tjikup-icon-cache.fish'))

    def test_converged_storage_does_not_reload_enable_or_stop_units(self):
        for name in ('documents','media','projects','resources'):
            (self.home / name).mkdir()
        self.stub('systemctl', r'''import os,sys
args=sys.argv[1:]
with open(os.environ['TRACE'],'a') as f: f.write(' '.join(args)+'\n')
if 'show' in args: print('no\nno')
elif any(x.startswith('rclone_sync.') for x in args): sys.exit(1)
elif not ('is-enabled' in args or 'is-active' in args): sys.exit(96)
''')
        output = self.run_hook('run_after_98-private-storage.fish.j2')
        self.assertIn('SKIP    ✓ Synctjik (private assets)', output)
        for mutator in ('enable --now','disable --now','daemon-reload','restart'):
            self.assertFalse(any(mutator in call for call in self.calls()), self.calls())


if __name__ == '__main__':
    unittest.main()
