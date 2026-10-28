"""Exercise native home policy without changing live files or contacting secrets providers."""
import importlib.util
import json
import os
from pathlib import Path
import runpy
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import tjikup_support
from fleet_capture.propagators.zed import update_template
from fleet_capture.propagators.herdr import PROPAGATOR as HERDR

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get('TJIKOS_REPO', Path.home() / 'code/tjikos')) / 'apps/tjikup/target/debug/tjikup'


class HomeFilesTests(unittest.TestCase):
    def test_jinja_capture_preserves_conditional_settings_and_secret_expressions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'; target = root / 'target'; output = root / 'output'
            text = '''{
  {% if is_desktop %}
  "conditional": 14,
  {% else %}
  "conditional": 12,
  {% endif %}
  "api_key": {{ secret("11111111-2222-3333-4444-555555555555") | json_quote }},
  "home": "{{ user.home }}/code",
  "font_size": 16
}'''
            source.write_text(text)
            target.write_text(json.dumps({'conditional': 90, 'api_key': 'SYNTHETIC-DO-NOT-CAPTURE',
                                          'home': '/another/home/code', 'font_size': 18}))
            update_template(source, target, output)
            self.assertEqual(output.read_text(), text.replace('"font_size": 16', '"font_size": 18'))
            source.write_text('{"path":"{{ user.home }}/old"}')
            target.write_text(json.dumps({'path': str(Path.home() / 'new')}))
            HERDR.propagate(source, target, output)
            self.assertEqual(json.loads(output.read_text()), {'path': '{{ user.home }}/new'})

    def test_editor_finds_native_zed_static_files_and_credential_templates(self):
        module = runpy.run_path(str(ROOT / 'scripts/home-compat.py'))
        with patch('socket.gethostname', return_value='fi'):
            for target, expected in [('.config/zed/settings.json', 'files/.config/zed/settings.json.j2'),
                                     ('.config/fish/config.fish', 'files/.config/fish/config.fish'),
                                     ('.config/fish/conf.d/secrets.fish', 'templates/fish/conf.d/secrets.fish.j2')]:
                self.assertEqual(module['source_path'](ROOT, '/home/io/' + target), ROOT / 'native/home' / expected)

    def test_home_recipe_uses_native_files_and_capture_points_to_existing_sources(self):
        from fleet_capture import discover_propagators
        spec = json.loads((ROOT / 'tjikup/recipes.json').read_text())
        recipe = next(r for r in spec['recipes'] if r['id'] == 'home:files')
        self.assertNotIn('files', recipe)
        self.assertIn('home-files', recipe['apply'])
        for propagator in discover_propagators():
            self.assertTrue(str(propagator.source).startswith('native/home/'))
            self.assertTrue((ROOT / propagator.source).is_file())

    @unittest.skipUnless(BINARY.is_file(), 'build tjikup first')
    def test_all_hosts_render_private_files_links_and_runtime_theme_with_synthetic_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            base = temp / 'home'
            shutil.copytree(ROOT / 'native/home', base)
            provider = temp / 'provider.py'
            provider.write_text("import json,sys\nprint(json.dumps({'id':sys.argv[3],'value':'SYNTHETIC-$HOME-literal'}))\n")
            context = temp / 'context.json'
            context.write_text(json.dumps({'repo_dir': str(ROOT), 'live': {'gtk3_icon_theme': 'chosen-theme', 'gtk4_icon_theme': 'chosen-theme'}}))
            for host, user in [('fi', 'io'), ('li', 'io'), ('si', 'm')]:
                with self.subTest(host=host):
                    spec = json.loads((base / f'files-{host}.json').read_text())
                    spec['host'] = socket.gethostname()
                    spec['bitwarden']['command'] = ['python3', str(provider)]
                    manifest = base / 'fixture.json'; manifest.write_text(json.dumps(spec))
                    destination = temp / host; destination.mkdir()
                    args = [str(BINARY), 'files', 'apply', '--manifest', str(manifest), '--context-file', str(context),
                            '--root', str(destination), '--state-dir', str(temp / (host + '-state'))]
                    result = subprocess.run(args, env={**os.environ, 'BWS_ACCESS_TOKEN': 'SYNTHETIC'}, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    home = destination / 'home' / user
                    self.assertIn('gtk-icon-theme-name=chosen-theme', (home / '.config/gtk-4.0/settings.ini').read_text())
                    self.assertEqual((home / '.local/bin/dotjik').stat().st_mode & 0o777, 0o755)
                    self.assertEqual(os.readlink(home / 'documents/archives'), f'/home/{user}/.mnt/google/private/archives/documents')
                    if host == 'si':
                        docker = home / 'dockers/docker-compose.yaml'
                        self.assertEqual(docker.stat().st_mode & 0o777, 0o600)
                        self.assertIn('SYNTHETIC-$$HOME-literal', docker.read_text())
                        self.assertFalse((home / '.config/zed/settings.json').exists())
                    else:
                        self.assertEqual((home / '.config/zed/settings.json').stat().st_mode & 0o777, 0o600)
                        self.assertEqual((home / '.config/Mullvad VPN').stat().st_mode & 0o777, 0o700)
                        self.assertFalse((home / 'dockers').exists())
                    second = subprocess.run(args, env={**os.environ, 'BWS_ACCESS_TOKEN': 'SYNTHETIC'}, capture_output=True, text=True)
                    self.assertEqual(second.returncode, 0, second.stderr)
                    self.assertIn('SKIP: 0 changed', second.stdout)

    def test_external_repository_check_preserves_existing_work_and_refuses_unmanaged_directory(self):
        module = runpy.run_path(str(ROOT / 'scripts/home-repositories.py'))
        with tempfile.TemporaryDirectory() as directory, \
                patch('socket.gethostname', return_value='fi'), \
                patch.object(Path, 'home', return_value=Path(directory)), \
                patch.object(sys, 'argv', ['home-repositories', 'check']):
            self.assertEqual(module['main'](), 1)
            target = Path(directory) / '.obsidian'
            target.mkdir()
            (target / 'local-note').write_text('preserve')
            with self.assertRaises(SystemExit):
                module['main']()
            subprocess.run(['git', 'init', '--quiet', str(target)], check=True)
            self.assertEqual(module['main'](), 0)
            self.assertEqual((target / 'local-note').read_text(), 'preserve')
