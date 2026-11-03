"""Reject stale local plugins before Hyprland attempts to load their hooks."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('lua'), 'Lua required')
class PluginLoaderTests(unittest.TestCase):
    def test_only_matching_builds_are_registered(self):
        commit = 'a' * 40
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            binary = directory / 'plugin.so'
            script = '''
local calls = 0
hl = {plugin = {load = function(path) calls = calls + 1 end}}
local loader = dofile(arg[1])
local result = loader.load(arg[2])
assert(result == (arg[3] == 'yes'))
assert(calls == (result and 1 or 0))
'''
            for contents, signature, expected in [
                (None, commit + '_1_2', False),
                (b'old\0' + b'b' * 40 + b'\0', commit + '_1_2', False),
                (b'ELF\0' + commit.encode() + b'\0', commit + '_1_2', True),
                (b'ELF\0' + commit.encode() + b'extra\0', commit + '_1_2', False),
                (b'ELF\0' + commit.encode() + b'\0', '', False),
                (b'ELF\0' + commit.encode() + b'\0', 'abc_1_2', False),
            ]:
                with self.subTest(contents=contents, signature=signature):
                    if contents is None:
                        binary.unlink(missing_ok=True)
                    else:
                        binary.write_bytes(contents)
                    subprocess.run([
                        'lua', '-', str(ROOT / 'native/home/files/.config/hypr/plugin_loader.lua'),
                        str(binary), 'yes' if expected else 'no',
                    ], input=script, text=True, check=True, capture_output=True,
                        env={**os.environ, 'HYPRLAND_INSTANCE_SIGNATURE': signature})
