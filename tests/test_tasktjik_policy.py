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
            if entry.get('group') == 'tasktjik' and entry.get('source', '').endswith('.j2'):
                self.assertTrue(entry.get('template'))
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

    def test_server_enrollment_follows_install_and_survives_cache_hits(self):
        for cached_runner, cache_hit, enrolled in ((False, False, True), (True, False, True), (True, True, True), (True, False, False)):
            with self.subTest(cached_runner=cached_runner, cache_hit=cache_hit, enrolled=enrolled), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                home = root / 'home'
                commands = home / '.local/bin'
                commands.mkdir(parents=True)
                scripts = root / 'scripts'
                scripts.mkdir()
                (scripts / 'install-tasktjik.sh').write_text((ROOT / 'scripts/install-tasktjik.sh').read_text())
                (scripts / 'ensure-tjikos.sh').write_text('tool_repo="$TEST_TOOLS"\nensure_tjikos() { :; }\n')
                source = root / 'tools/apps/tasktjik'
                (source / 'scripts').mkdir(parents=True)
                (source / 'systemd').mkdir()
                for unit in ('tasktjik.service', 'tasktjik.timer'):
                    (source / 'systemd' / unit).write_text('[Unit]\n')
                (home / '.config/systemd/user').mkdir(parents=True)
                if enrolled:
                    (home / '.config/notjik').mkdir()
                    (home / '.config/notjik/sync.json').write_text('{}')
                current = root / 'current-tasktjik'
                current.write_text('#!/bin/sh\n[ "$*" = "enroll --notifications" ] || exit 91\necho enroll >> "$TEST_LOG"\n')
                current.chmod(0o755)
                tasktjik = commands / 'tasktjik'
                tasktjik.write_text(current.read_text() if cache_hit else '#!/bin/sh\necho stale >> "$TEST_LOG"\nexit 2\n')
                tasktjik.chmod(0o755)
                (source / 'scripts/build.sh').write_text('echo build >> "$TEST_LOG"\n')
                (source / 'scripts/install.sh').write_text('echo install >> "$TEST_LOG"\ncp "$TEST_CURRENT" "$HOME/.local/bin/tasktjik"\n')
                for name, body in {
                    'hostname': 'echo si',
                    'systemctl': 'echo "systemctl $*" >> "$TEST_LOG"',
                }.items():
                    command = commands / name
                    command.write_text('#!/bin/sh\n' + body + '\n')
                    command.chmod(0o755)
                runner = root / 'runner'
                runner.write_text('#!/bin/sh\nif [ "$1" = capabilities ]; then echo ' + json.dumps(json.dumps({'tasktjik_install_cache': int(cached_runner)})) + '; exit; fi\necho cache >> "$TEST_LOG"\n' + ('exit 0\n' if cache_hit else 'while [ "$1" != -- ]; do shift; done\nshift\nexec "$@"\n'))
                runner.chmod(0o755)
                env = {**os.environ, 'HOME': str(home), 'XDG_CONFIG_HOME': str(home / '.config'), 'PATH': str(commands) + ':' + os.environ['PATH'], 'TJIKUP_BINARY': str(runner), 'TEST_TOOLS': str(root / 'tools'), 'TEST_LOG': str(root / 'calls'), 'TEST_CURRENT': str(current)}
                result = subprocess.run(['bash', str(scripts / 'install-tasktjik.sh')], env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                calls = (root / 'calls').read_text().splitlines()
                self.assertNotIn('stale', calls)
                self.assertEqual(calls.count('enroll'), int(enrolled))
                if enrolled:
                    self.assertLess(calls.index('enroll'), calls.index('systemctl --user enable --now tasktjik.timer'))
                    if not cache_hit:
                        self.assertLess(calls.index('install'), calls.index('enroll'))
                    override = home / '.config/systemd/user/tasktjik.service.d/socket-group.conf'
                    self.assertIn('sg tasktjik', override.read_text())
                    self.assertIn('sg notjik', override.read_text())
                else:
                    self.assertFalse(any(call.startswith('systemctl') for call in calls))
