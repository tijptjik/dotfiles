"""Managed Codex policy survives capture and renders each host's preferences."""
import json
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CodexPolicyTests(unittest.TestCase):
    def test_capture_cannot_replace_managed_codex_policy(self):
        rules = json.loads((ROOT / 'tjikup/capture.json').read_text())
        self.assertFalse(any(rule['target'] == '.codex/config.toml' for rule in rules))

    def test_each_host_keeps_policy_and_preferences(self):
        for host in ('fi', 'li', 'si'):
            with self.subTest(host=host), tempfile.TemporaryDirectory() as directory:
                config = Path(directory) / 'context.json'
                config.write_text(json.dumps({'data': {
                    'isDesktop': host == 'fi', 'isLaptop': host == 'li',
                }}))
                rendered = subprocess.check_output([
                    'python3', '-B', str(ROOT / 'tests/native_render.py'),
                    '--config', str(config), '-f',
                    str(ROOT / 'native/home/files/.codex/config.toml.j2'),
                ], text=True)
                data = tomllib.loads(rendered)
                self.assertFalse(data['mcp_servers']['chrome-devtools']['enabled'])
                self.assertEqual(data['model_reasoning_effort'], 'low' if host == 'fi' else 'medium')
                self.assertEqual('/home/io/code/eurovision' in data['projects'], host == 'fi')
