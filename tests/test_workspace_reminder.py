from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('lua'), 'Lua required')
class WorkspaceReminderTests(unittest.TestCase):
    def test_hold_release_and_combo_cancellation(self):
        script = r'''
local timers, commands, mouse, events = {}, {}, {}, {}
hl = {
    dsp = {exec_cmd = function(s) return s end},
    dispatch = function(s) table.insert(commands, s) end,
    on = function(name, cb) events[name]=cb; return {} end,
    bind = function(key, cb, opts)
        assert(opts.non_consuming and opts.ignore_mods)
        mouse[key] = cb
    end,
    timer = function(cb, opts)
        assert(opts.timeout == 400 and opts.type == 'oneshot')
        local t = {cb=cb, enabled=true}
        function t:set_enabled(value) self.enabled=value end
        table.insert(timers, t)
        return t
    end,
}
local r = dofile(arg[1])
r.start()
local function key(code, state) r.key(code, 0, state) end
local function fire() local t=timers[#timers]; if t.enabled then t.cb() end end
local function last(op) assert(commands[#commands]:match(op .. '$')) end
key(133,1); last('hide%-workspaces'); fire(); last('show%-workspaces')
key(133,0); last('hide%-workspaces')
local n=#commands
key(133,1); key(133,0); fire(); assert(#commands==n)
key(133,1); key(38,1); key(38,0); fire(); assert(#commands==n)
key(133,0)
key(50,1); key(133,1); key(50,0); fire(); assert(#commands==n)
key(133,0)
key(134,1); fire(); last('show%-workspaces'); key(10,1); last('show%-workspaces')
events['workspace.active'](); last('show%-workspaces')
key(10,0); key(134,0); last('show%-workspaces')
local settling=timers[#timers]
events['workspace.active'](); assert(not settling.enabled)
last('show%-workspaces'); fire(); last('hide%-workspaces')
key(133,1); local count=#timers; key(133,1); assert(#timers==count)
mouse['mouse:272'](); fire(); last('hide%-workspaces'); key(133,0)
key(133,1); fire(); mouse.mouse_down(); last('show%-workspaces'); key(133,0); last('show%-workspaces'); fire(); last('hide%-workspaces')
'''
        subprocess.run(['lua', '-', str(ROOT / 'native/home/files/.config/hypr/workspace_reminder.lua')],
                       input=script, text=True, check=True)
