"""Render host rules and check their ordered initial-width policy."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('chezmoi') and shutil.which('lua'), 'Chezmoi and Lua required')
class WindowWidthTests(unittest.TestCase):
    def test_host_width_and_placement_rules(self):
        for host in ('fi', 'li', 'si'):
            with self.subTest(host=host), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                config = root / 'config.json'
                config.write_text(json.dumps({'data': {
                    'isDesktop': host == 'fi', 'isLaptop': host == 'li',
                }}))
                rendered = subprocess.check_output([
                    'chezmoi', '--config', str(config), '--source', str(root),
                    '--persistent-state', str(root / 'state.db'),
                    'execute-template', '-f',
                    str(ROOT / 'home/dot_config/hypr/windows.lua.tmpl'),
                ], text=True)
                rules = root / 'rules.lua'
                rules.write_text(rendered)
                script = r'''
local rules, order = {}, {}
hl = {window_rule = function(rule)
    rules[rule.name] = rule
    order[rule.name] = #order + 1
    table.insert(order, rule.name)
end}
dofile(arg[1])
assert(rules.zed.scrolling_width == 1.0)
assert(rules.zed.match.class == "^dev[.]zed[.]Zed(-Preview|-Nightly)?$")
assert(rules.spotify.scrolling_width == 1.0)
assert(rules.zen.scrolling_width == 0.5)
assert(rules.kitty.scrolling_width == 0.5)
assert(rules.spotify.workspace == (arg[2] == "fi" and "20 silent" or arg[2] == "li" and "10 silent" or nil))
if arg[2] == "fi" then
    for app, width in pairs({zen=1.0, kitty=0.75}) do
        local name = app .. "-secondary-width"
        assert(rules[name].scrolling_width == width)
        assert(rules[name].match.class == app)
        assert(rules[name].match.workspace == "m[DP-2]")
        assert(order[name] > order[app])
    end
else
    assert(rules["zen-secondary-width"] == nil)
    assert(rules["kitty-secondary-width"] == nil)
end
'''
                check = root / 'check.lua'
                check.write_text(script)
                subprocess.run(['lua', str(check), str(rules), host], check=True)
