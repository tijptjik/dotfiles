"""Rendered role guards suppress work and rows, without breaking dependencies."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import tjikup_support
from fleet_update.dag import run, Result
from fleet_update.hook_tasks import HookTasks, rendered_noop

ROOT = Path(__file__).resolve().parents[1]


class HookRoleTests(unittest.TestCase):
    def test_noop_detection_is_conservative(self):
        self.assertTrue(rendered_noop('# comment\n\n'))
        for name in ['FLEET_DEFER_HOOKS', 'FLEET_DEFER_SYSTEM_HOOKS']:
            guard = f'#!/usr/bin/env fish\nif test "${name}" = 1\n    exit 0\nend\n'
            self.assertTrue(rendered_noop(guard))
            self.assertFalse(rendered_noop(guard + 'echo work\n'))
            self.assertFalse(rendered_noop(guard + 'status_msg SKIP - Python "client only"\n'))
        self.assertFalse(rendered_noop('if test "$OTHER" = 1\nexit 0\nend'))

    @unittest.skipUnless(shutil.which('chezmoi') and shutil.which('fish'), 'Chezmoi/Fish required')
    def test_actual_host_guards_and_silent_dependency_barriers(self):
        names = ['obsidian', 'sublime-text', 'llmtrim-install', 'llmtrim', 'codex-lb',
                 'notjik', 'greetjik', 'bartjik', 'rose-punk-icons', 'collie', 'vite']
        plan = json.loads((ROOT / 'scripts/fleet_update/home-plan.json').read_text())
        selected = [x for x in plan if x['id'] in names]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / 'chezmoi.toml'
            config.write_text('[data]\n')
            for host in ['fi', 'li', 'si']:
                data = {'hostname': host, 'isClient': host != 'si', 'isDesktop': host == 'fi',
                        'isLaptop': host == 'li', 'isServer': host == 'si'}
                for item in selected:
                    rendered = subprocess.run(['chezmoi', '--config', str(config), '--source', str(ROOT / 'home'),
                        '--override-data', json.dumps(data), 'execute-template', '--file',
                        str(ROOT / 'home/.chezmoiscripts' / item['file'])],
                        capture_output=True, text=True, check=True).stdout
                    expected = (host == 'si' and item['id'] != 'codex-lb') or (host == 'li' and item['id'] in
                               ['llmtrim-install', 'llmtrim', 'collie', 'vite'])
                    with self.subTest(host=host, hook=item['id']):
                        self.assertEqual(rendered_noop(rendered), expected)
            # Keep a skipped role node in the graph; a dependent native task runs.
            report = root / 'report'
            env = {**os.environ, 'TJIKUP_REPORT_FILE': str(report), 'TJIKUP_COLOR': '0'}
            with patch.dict(os.environ, env), contextlib.redirect_stdout(io.StringIO()) as output:
                hooks = HookTasks(root, root, env)
                tasks = hooks.prepare(ROOT, [
                    {'id': 'gui', 'label': 'Obsidian', 'file': 'guard.fish'},
                    {'id': 'native', 'label': 'Rust', 'file': 'native.fish', 'needs': ['gui']}],
                    lambda item: '#!/usr/bin/env fish\n' if item['id'] == 'gui'
                    else "printf 'CHECK   ✓ Rust    ready\\n'\n")
                results = run(tasks, event=hooks.event)
            self.assertEqual(results['gui'].state, 'skipped')
            self.assertEqual(results['native'].state, 'done')
            self.assertNotIn('Obsidian', output.getvalue())
            self.assertNotIn('Obsidian', report.read_text())
            self.assertIn('Rust', report.read_text())

    def test_service_sections_preserve_individual_outcomes_and_record_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / 'report'
            with patch.dict(os.environ, {'TJIKUP_REPORT_FILE': str(report), 'TJIKUP_COLOR': '0',
                                         'TJIKUP_ICONS': '0'}), contextlib.redirect_stdout(io.StringIO()) as output:
                hooks = HookTasks(root, root, {})
                hooks.items['apps'] = {'label': 'Applications (server)', 'status_sections': True}
                hooks.outputs['apps'] = ('__tjikup_section__:Docker services\n'
                    'SYNC    ... Docker images    checking images\n'
                    'SKIP    ✓ radarr    no changes\n'
                    'WARN    ! mariadb    keeping current image; unavailable\n'
                    '__tjikup_section__:Native applications\nSKIP    ✓ Plex    2 active sessions\n')
                hooks.event('apps', Result('done'))
            text = output.getvalue()
            self.assertLess(text.index('Docker services'), text.index('radarr'))
            self.assertLess(text.index('Native applications'), text.index('Plex'))
            self.assertNotIn('Applications (server)', text)
            self.assertNotIn('...', text)
            self.assertEqual(len(report.read_text().splitlines()), 3)
            self.assertIn('WARN\t!\tmariadb', report.read_text())
            self.assertIn('2 active sessions', report.read_text())


    @unittest.skipUnless(shutil.which('fish'), 'Fish required')
    def test_combined_system_wrapper_honours_rendered_noop(self):
        from types import SimpleNamespace
        from fleet_update import fleet_apply
        home = [{'id': 'chezetc-wrapper', 'label': 'Wrapper', 'file': 'wrapper.fish'}]
        system = [{'id': 'gui', 'label': 'Obsidian', 'file': 'client.fish'}]
        policy = SimpleNamespace(apply_files=lambda repo: None,
            render_hooks=lambda *args: {'client.fish': '#!/usr/bin/env fish\n'})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = {'XDG_STATE_HOME': str(root), 'TJIKUP_COLOR': '0', 'TJIKUP_PROGRESS': '0'}
            with patch.dict(os.environ, env), \
                    patch.object(fleet_apply, 'plans', return_value=(home, system, policy)), \
                    patch('fleet_update.apply_files', return_value=0), \
                    patch.object(fleet_apply, 'render_hook', return_value='echo wrapper\n'), \
                    patch.object(fleet_apply, 'command', return_value=SimpleNamespace(returncode=0)), \
                    patch('fleet_update.hook_tasks.run_command', return_value=SimpleNamespace(stdout='', returncode=0)) as command, \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(fleet_apply.apply(root, root), 0)
            self.assertEqual(command.call_count, 1, 'Only the applicable home hook may execute')
            timings, = (root / 'tjikup/logs').glob('apply-*/timings.json')
            states = {row['id']: row['state'] for row in json.loads(timings.read_text())['tasks']}
            self.assertEqual(states['system:gui'], 'skipped')
            self.assertNotIn('Obsidian', output.getvalue())


if __name__ == '__main__':
    unittest.main()
