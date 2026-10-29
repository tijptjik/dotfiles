import native_render
"""Lock/unlock and app convergence must not disconnect fleet access."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TailnetPolicyTests(unittest.TestCase):
    def test_lock_wrapper_preserves_arguments_and_status_without_toggling_network(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            hyprlock = root / 'hyprlock'
            hyprlock.write_text('#!/usr/bin/python3\nimport json,sys\nprint(json.dumps(sys.argv[1:]))\nsys.exit(17)\n')
            hyprlock.chmod(0o755)
            tailscale = root / 'tailscale'
            tailscale.write_text('#!/bin/sh\necho unexpected-tailnet-command >&2\nexit 99\n')
            tailscale.chmod(0o755)
            result = subprocess.run(['fish', '--no-config', str(ROOT / 'native/home/files/.local/bin/tailscale-lock'),
                                     '--config', 'a b'],
                                    env={**os.environ, 'PATH': f'{root}:/usr/bin:/bin'},
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 17)
            self.assertEqual(json.loads(result.stdout), ['--config', 'a b'])
            self.assertEqual(result.stderr, '')

    def test_application_hooks_render_without_disconnect_on_all_hosts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for host in ('fi', 'li', 'si'):
                config = root / 'config.json'
                config.write_text(json.dumps({'data': {
                    'isDesktop': host == 'fi', 'isLaptop': host == 'li',
                    'isClient': host != 'si', 'isServer': host == 'si',
                }}))
                for name in ('run_after_70-provision-collie.fish.j2',
                             'run_after_71-configure-vite-tailnet-serve.fish.j2'):
                    with self.subTest(host=host, hook=name):
                        result = subprocess.run([
                            'render-native', '--source', str(ROOT / 'home'), '--config', str(config),
                            '--persistent-state', str(root / 'state.db'), 'execute-template',
                            '-f', str(ROOT / 'native/tasks/home' / name),
                        ], capture_output=True, text=True)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertNotIn('tailscale down', result.stdout)
                        syntax = subprocess.run(['fish', '--no-config', '--no-execute'],
                                                input=result.stdout, text=True, capture_output=True)
                        self.assertEqual(syntax.returncode, 0, syntax.stderr)
