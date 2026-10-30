"""Synthetic Tasktjik policy checks; no live host or credential access."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TasktjikPolicyTests(unittest.TestCase):
    def test_each_host_configuration(self):
        for host in ('fi', 'li', 'si'):
            with self.subTest(host=host), tempfile.TemporaryDirectory() as directory:
                config = Path(directory) / 'context.json'
                config.write_text(json.dumps({'data': {'isDesktop': host == 'fi', 'isLaptop': host == 'li', 'isServer': host == 'si'}}))
                result = subprocess.check_output(['python3', '-B', str(ROOT / 'tests/native_render.py'), '--config', str(config), '-f', str(ROOT / 'native/home/files/.config/tasktjik/tasktjik.conf.j2')], text=True)
                settings = tomllib.loads(result)['tasktjik']
                if host == 'si':
                    self.assertEqual(settings['socket'], '/run/tasktjik/api.sock')
                else:
                    self.assertEqual(settings['url'], 'https://si.tailb49776.ts.net/tasktjik')
                self.assertNotIn('authority', settings)


    def test_authority_and_client_ordering(self):
        recipes = {r['id']: r for r in json.loads((ROOT / 'tjikup/recipes.json').read_text())['recipes']}
        self.assertIn('tasktjik', json.loads((ROOT / 'native/home/groups.json').read_text()))
        self.assertIn('si', recipes['home:tasktjik']['hosts'])
        self.assertFalse(recipes['home:tasktjik']['optional'])
        self.assertEqual(recipes['home:activate:tasktjik']['roles'], ['desktop', 'laptop'])
        for app in ('notjik', 'runtjik'):
            self.assertIn('home:tasktjik', recipes['home:' + app]['needs'])
            self.assertIn('home:tasktjik:update', recipes['home:' + app + ':update']['needs'])
        for entry in json.loads((ROOT / 'native/home/files.json').read_text()):
            if entry.get('group') == 'tasktjik' and entry['path'].endswith(('.service', '.timer')):
                self.assertEqual(entry['when'], 'is_client')

    def test_timer_migration_order(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / '.local/bin').mkdir(parents=True)
            (home / '.config/tasktjik').mkdir(parents=True)
            (home / '.config/tasktjik/tasktjik.conf').touch()
            command = home / '.local/bin/tasktjik'
            command.touch()
            command.chmod(0o755)
            systemctl = home / '.local/bin/systemctl'
            systemctl.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$HOME/calls"\n')
            systemctl.chmod(0o755)
            subprocess.run(['bash', str(ROOT / 'scripts/activate-tasktjik.sh')], check=True, env={**os.environ, 'HOME': str(home), 'XDG_CONFIG_HOME': str(home / '.config'), 'PATH': str(home / '.local/bin') + ':' + os.environ['PATH']})
            calls = (home / 'calls').read_text()
            self.assertLess(calls.index('disable --now runtjik-todo.timer'), calls.index('enable --now tasktjik.timer'))

    def test_older_runner_installs_without_new_cache_command(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / 'scripts'
            scripts.mkdir()
            (scripts / 'install-tasktjik.sh').write_text((ROOT / 'scripts/install-tasktjik.sh').read_text())
            (scripts / 'ensure-tjikos.sh').write_text('tool_repo="$TEST_TOOLS"\nensure_tjikos() { :; }\n')
            source = root / 'tools/apps/tasktjik/scripts'
            source.mkdir(parents=True)
            for operation in ('build', 'install'):
                (source / (operation + '.sh')).write_text('echo '+operation+' >> "$TEST_LOG"\n')
            runner = root / 'runner'
            runner.write_text('#!/bin/sh\nif [ "$1" = capabilities ]; then echo "{}"; else exit 99; fi\n')
            runner.chmod(0o755)
            result = subprocess.run(['bash', str(scripts / 'install-tasktjik.sh')], env={**os.environ, 'TJIKUP_BINARY': str(runner), 'TEST_TOOLS': str(root / 'tools'), 'TEST_LOG': str(root / 'calls')}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((root / 'calls').read_text().splitlines(), ['build', 'install'])
