import native_render
"""Render host rules and check their ordered initial-width policy."""
import json
import shlex
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('render-native') and shutil.which('lua'), 'Native renderer and Lua required')
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
                    'render-native', '--config', str(config), '--source', str(root),
                    '--persistent-state', str(root / 'state.db'),
                    'execute-template', '-f',
                    str(ROOT / 'native/home/files/.config/hypr/execs.lua.j2'),
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
                gated = [c for c in commands if 'after-keyring-unlock' in c]
                self.assertTrue(gated)
                commands = [shlex.split(c)[-1] if 'after-keyring-unlock' in c else c
                            for c in commands]
                self.assertIn('uwsm app -- /usr/bin/mullvad-exclude /opt/Telegram/Telegram', commands)
                zapzap = [c for c in commands if '/bin/zapzap' in c]
                signal = [c for c in commands if 'org.signal.Signal' in c]
                self.assertEqual(zapzap, ['uwsm app -- /usr/bin/mullvad-exclude /bin/zapzap' +
                                         (' --hideStart' if host == 'li' else '')])
                self.assertEqual(signal, [] if host == 'si' else [
                    'uwsm app -- /usr/bin/mullvad-exclude flatpak run org.signal.Signal' +
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
                    'render-native', '--config', str(config), '--source', str(root),
                    '--persistent-state', str(root / 'state.db'),
                    'execute-template', '-f',
                    str(ROOT / 'native/home/files/.config/hypr/windows.lua.j2'),
                ], text=True)
                rules = root / 'rules.lua'
                rules.write_text(rendered)
                script = r'''
local rules, order, events, actions = {}, {}, {}, {}
local active, timer
hl = {on=function(event, callback) events[event]=callback; return {} end,
get_active_window=function() return active end,
timer=function(callback, options) assert(options.timeout==1);timer=callback;return {} end,
dsp={window={move=function(spec) return spec end}},
dispatch=function(spec) actions[#actions+1]=spec end,
window_rule = function(rule)
    rules[rule.name] = rule
    order[rule.name] = #order + 1
    table.insert(order, rule.name)
end}
package.path = arg[3] .. "/?.lua;" .. package.path
dofile(arg[1])
local settings = rules["tasktjik-settings"]
assert(settings.float and settings.no_anim and settings.no_blur)
assert(settings.match.class == "^org[.]quickshell$" and settings.match.initial_title == "^Tasktjik Settings$")
local parent = {mapped=true,pid=42,at={x=120,y=140},size={x=1000,y=700}}
local window = {address="settings",class="org.quickshell",initial_title="Tasktjik Settings",mapped=true,pid=42,size={x=900,y=660}}
active=parent;events["window.open_early"](window)
active=window;events["window.open"](window)
assert(#actions==0);timer()
assert(#actions==1 and actions[1].window==window and actions[1].x==170 and actions[1].y==160 and actions[1].relative==false)
-- Never center over a different application's window.
parent.pid=7;active=parent;timer=nil
events["window.open_early"](window);events["window.open"](window)
assert(timer==nil and #actions==1)
-- The invoker may disappear before the deferred placement runs.
parent.pid=42;active=parent;events["window.open_early"](window);events["window.open"](window)
parent.mapped=false;timer();assert(#actions==1)
assert(rules.zed.scrolling_width == 1.0)
assert(rules.zed.match.class == "^dev[.]zed[.]Zed(-Preview|-Nightly)?$")
assert(rules.spotify.scrolling_width == 1.0)
assert(rules["codex-lb"].scrolling_width == (arg[2] == "fi" and 1.0 or nil))
assert(rules.zen.scrolling_width == 0.5)
assert(rules.kitty.scrolling_width == (arg[2] == "li" and 1.0 or 0.5))
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
    for app, width in pairs({zen=1.0, kitty=1.0}) do
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
                subprocess.run(['lua', str(check), str(rules), host, str(ROOT / 'native/home/files/.config/hypr')], check=True)
