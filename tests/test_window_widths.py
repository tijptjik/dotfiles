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
    def test_host_chat_startup(self):
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
                    str(ROOT / 'home/dot_config/hypr/execs.lua.tmpl'),
                ], text=True)
                startup = root / 'startup.lua'
                startup.write_text(rendered)
                check = root / 'check.lua'
                check.write_text('''
package.preload.helpers = function()
    return setmetatable({}, {__index = function() return function() end end})
end
hl = {
    on = function(event, callback)
        assert(event == "hyprland.start")
        callback()
    end,
    exec_cmd = print,
}
dofile(arg[1])
''')
                commands = subprocess.check_output(
                    ['lua', str(check), str(startup)], text=True,
                ).splitlines()
                self.assertIn('uwsm app -- /opt/Telegram/Telegram', commands)
                zapzap = [c for c in commands if '/bin/zapzap' in c]
                signal = [c for c in commands if 'org.signal.Signal' in c]
                self.assertEqual(zapzap, ['uwsm app -- /bin/zapzap' +
                                         (' --hideStart' if host == 'li' else '')])
                self.assertEqual(signal, [] if host == 'si' else [
                    'uwsm app -- flatpak run org.signal.Signal' +
                    (' --start-in-tray' if host == 'li' else '')])

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
package.path = arg[3] .. "/?.lua;" .. package.path
dofile(arg[1])
assert(rules.zed.scrolling_width == 1.0)
assert(rules.zed.match.class == "^dev[.]zed[.]Zed(-Preview|-Nightly)?$")
assert(rules.spotify.scrolling_width == 1.0)
assert(rules["codex-lb"].scrolling_width == (arg[2] == "fi" and 1.0 or nil))
assert(rules.zen.scrolling_width == 0.5)
assert(rules.kitty.scrolling_width == 0.5)
assert(rules.telegram.match.initial_title == "negative:^(TelegramDesktop|Media viewer)$")
if arg[2] == "fi" then
    assert(rules.telegram.workspace == "special:chat silent")
    assert(rules.telegram.float)
    assert(rules.telegram.size[1] == 944 and rules.telegram.size[2] == 1280)
    assert(rules.telegram.move[1] == "(1248)" and rules.telegram.move[2] == "(46)")
elseif arg[2] == "li" then
    assert(rules.telegram.workspace == "special:chat silent")
end
local export = rules["telegram-export-dialog"]
assert(export.match.class == rules.telegram.match.class)
assert(export.match.initial_title == "^TelegramDesktop$")
assert(export.float and export.border_size == 0 and export.rounding == 0)
assert(export.no_shadow and export.no_blur and export.no_anim)
assert(export.size == nil and export.move == nil and export.workspace == nil)
assert(rules.spotify.workspace == (arg[2] == "fi" and "20 silent" or arg[2] == "li" and "10 silent" or nil))
for app, width in pairs({files=0.75, sublime=1.0, obsidian=1.0, ["codex-lb"]=1.0, ["system-monitor"]=0.75}) do
    local base = app .. "-width"
    local secondary = app .. "-secondary-width"
    assert(rules[base].scrolling_width == 0.5)
    if arg[2] == "fi" then
        assert(rules[secondary].scrolling_width == width)
        assert(rules[secondary].match.class == rules[base].match.class)
        assert(rules[secondary].match.workspace == "m[DP-2]")
        assert(order[secondary] > order[base])
    else
        assert(rules[secondary] == nil)
    end
end
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
                subprocess.run(['lua', str(check), str(rules), host, str(ROOT / 'home/dot_config/hypr')], check=True)
