"""Exercise reversible workspace gaps without changing fullscreen state."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('lua'), 'Lua required')
class ScrollingGapsTests(unittest.TestCase):
    def test_focus_transitions_restore_gaps_without_fullscreen(self):
        script = r'''
local active, windows, rules, changes, events, timers = nil, {}, {}, {}, {}, {}
hl = {
    get_active_window = function() return active end,
    get_windows = function() return windows end,
    workspace_rule = function(options)
        table.insert(rules, options)
        local handle = {enabled=true}
        function handle:set_enabled(value)
            self.enabled = value; table.insert(changes, {options.workspace, value})
        end
        return handle
    end,
    on = function(event, callback) events[event] = callback; return {} end,
    timer = function(callback) table.insert(timers, callback); return {} end,
}
local function window(width, id, index)
    local w = {mapped=true, floating=false, fullscreen=0, fullscreen_client=0, workspace={id=id or 9}}
    w.layout = {name="scrolling", column={width=width, index=index or 0, windows={w}}}
    return w
end
local policy = dofile(arg[1])
local wide, narrow = window(1), window(.5,9,1)
active = wide; policy.update()
assert(#rules == 1 and rules[1].workspace == "r[9-9] s[false]")
assert(rules[1].gaps_in == 0 and rules[1].gaps_out == 0)
assert(rules[1].border_size == 0 and rules[1].no_rounding)
-- Repeated updates and adjacent full-width windows leave the rule alone.
active = window(1); policy.update(); policy.update()
assert(#rules == 1 and #changes == 0)
active = narrow; policy.update()
assert(#changes == 1 and changes[1][2] == false)
active = wide; policy.update()
assert(#rules == 1 and changes[2][2] == true)
active = window(1,18); policy.update()
assert(#changes == 2 and #rules == 2)
active = nil; policy.update()
assert(#changes == 2)
-- Overlay focus must preserve both already-gapless strips.
active = window(1,-99); policy.update(); assert(#changes == 2)
active = window(.5); active.floating = true; policy.update(); assert(#changes == 2)
active = window(.5,18); policy.update()
assert(changes[3][1] == "r[18-18] s[false]" and changes[3][2] == false)
active = narrow; policy.update(); assert(changes[4][1] == "r[9-9] s[false]" and changes[4][2] == false)
for _, kind in ipairs({"half", "three-quarter", "floating", "unmapped", "fullscreen", "client-fullscreen", "master", "missing", "stacked", "special"}) do
    local w = window(1)
    if kind == "half" then w.layout.column.width = .5
    elseif kind == "three-quarter" then w.layout.column.width = .75
    elseif kind == "floating" then w.floating = true
    elseif kind == "unmapped" then w.mapped = false
    elseif kind == "fullscreen" then w.fullscreen = 2
    elseif kind == "client-fullscreen" then w.fullscreen_client = 2
    elseif kind == "master" then w.layout.name = "master"
    elseif kind == "missing" then w.layout = nil
    elseif kind == "stacked" then table.insert(w.layout.column.windows,{})
    elseif kind == "special" then w.workspace.id = -99 end
    active = w; policy.update()
    assert(#rules == 2 and #changes == 4, kind)
end
active = wide; policy.start(); policy.start()
assert(#timers == 1)
events["window.open"](); events["window.close"](); assert(#timers == 1)
timers[1](); assert(changes[5][2] == true)
active = narrow; events["window.active"](); assert(changes[6][2] == false)
-- Native strip navigation stays available; crossing monitors still works at ends.
local actions = {}
hl.dispatch = function(action) table.insert(actions,action) end
hl.dsp = {
    layout = function(msg) return {kind="layout", msg=msg} end,
    focus = function(options) return {kind="ordinary", options=options} end,
}
active = wide; windows = {wide,narrow}; policy.focus("r")
assert(actions[1].kind == "layout" and actions[1].msg == "focus r")
policy.focus("l"); assert(actions[2].kind == "ordinary")
narrow.workspace.id = 10; policy.focus("r"); assert(actions[3].kind == "ordinary")
'''
        subprocess.run(['lua', '-', str(ROOT / 'home/dot_config/hypr/scrolling_gaps.lua')],
                       input=script, text=True, check=True)
