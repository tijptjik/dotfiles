"""Exercise detached-window stacking without touching the live compositor."""
from pathlib import Path
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which("lua"), "Lua is required")
class DetachedCardTests(unittest.TestCase):
    def test_focus_changes_raise_only_detached_cards_without_changing_focus(self):
        helper = Path(__file__).resolve().parents[1] / "native/home/files/.config/hypr/helpers.lua"
        script = r'''
local events, timers, raised = {}, {}, {}
local ordinary = {address="editor", initial_title="Editor", mapped=true, floating=true}
local panel = {address="panel", initial_title="bartjik-detached:1", mapped=true, floating=true}
local notice = {address="notice", initial_title="notjik-detached:1", mapped=true, floating=true}
local closed = {address="closed", initial_title="notjik-detached:2", mapped=false, floating=true}
local active = ordinary
hl = {
    get_active_window=function() return active end,
    get_windows=function() return {ordinary, panel, notice, closed} end,
    dsp={window={alter_zorder=function(options)
        assert(options.mode == "top")
        return options.window.address
    end}},
    dispatch=function(address) table.insert(raised, address) end,
    on=function(event, callback) assert(not events[event]); events[event]=callback; return {} end,
    timer=function(callback, options)
        assert(options.type == "oneshot")
        local timer = {callback=callback, enabled=true}
        function timer:set_enabled(enabled) self.enabled=enabled end
        table.insert(timers, timer)
        return timer
    end,
}
local helpers = dofile(arg[1])
helpers.start_detached_cards()
helpers.start_detached_cards()
assert(#timers == 1)
timers[#timers].callback()
assert(table.concat(raised, ",") == "panel,notice")
assert(active == ordinary)
raised = {}
active = panel
events["window.active"]()
events["window.open"]()
assert(not timers[#timers-1].enabled)
timers[#timers].callback()
assert(table.concat(raised, ",") == "notice,panel")
assert(active == panel)
raised = {}
active = nil
events["window.active"]()
timers[#timers].callback()
assert(table.concat(raised, ",") == "panel,notice")
'''
        result = subprocess.run(["lua", "-", str(helper)], input=script, text=True,
                                capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
