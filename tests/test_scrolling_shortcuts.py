"""Exercise column boundaries and wrapping without touching desktop windows."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("lua"), "Lua required")
class ScrollingShortcutsTests(unittest.TestCase):
    def test_pair_preserves_other_columns_focus_and_settings(self):
        script = r'''
local windows, active, fit, no_warps, follow_mouse, offset, fail, calls
local function fit_active()
    local start=0
    for _,w in ipairs(windows) do
        if w==active then break end
        start=start+w.layout.column.width
    end
    local finish=start+active.layout.column.width
    if start<offset then offset=start end
    if finish>offset+1 then offset=finish-1 end
end
hl={get_active_window=function() return active end,get_windows=function() return windows end,
    get_config=function(key)
        if key=='cursor:no_warps' then return no_warps end
        if key=='input:follow_mouse' then return follow_mouse end
        return fit
    end,
    config=function(o)
        fit=o.scrolling.focus_fit_method;no_warps=o.cursor.no_warps;follow_mouse=o.input.follow_mouse
    end,
    dsp={layout=function(s) return s end,focus=function(o) return o end,
        cursor={move=function(o) return {cursor=o} end}},
    dispatch=function(action)
        calls=calls+1
        if type(action)=='table' then
            if action.window then
                assert(no_warps, 'temporary focus must not move the pointer')
                active=action.window;fit_active()
            end
            if action.cursor then active=nil end -- hover can see the old geometry
        elseif action=='colresize 0.5' then
            if fail and active==windows[2] then error('resize failed') end
            active.layout.column.width=.5;fit_active()
        elseif action=='fit_into_view' then fit_active() end
    end}
local shortcuts=dofile(arg[1])
local function setup(index)
    windows={};fit=0;no_warps=false;follow_mouse=2;offset=2.8;calls=0;fail=false
    for i,width in ipairs({.25,1,.75,1}) do
        windows[i]={mapped=true,floating=false,fullscreen=0,fullscreen_client=0,workspace={id=1},
            at={x=0,y=0},size={x=100,y=100},
            layout={name='scrolling',column={index=i-1,width=width}}}
    end
    active=windows[index]
end
for _,direction in ipairs({'l','r'}) do
    setup(3)
    local original=active
    shortcuts.pair(direction)
    local neighbor=direction=='l' and 2 or 4
    assert(active==original and fit==0 and not no_warps and follow_mouse==2)
    assert(windows[3].layout.column.width==.5 and windows[neighbor].layout.column.width==.5)
    assert(windows[1].layout.column.width==.25)
    assert(windows[direction=='l' and 4 or 2].layout.column.width==1)
    assert(offset==(direction=='l' and .25 or 1.25), 'pair must fill the viewport')
end
for _,kind in ipairs({'edge','floating','fullscreen','client_fullscreen','scratch','master',
    'unmapped','absent','other_workspace','floating_neighbor','fullscreen_neighbor'}) do
    setup(1)
    local direction='r'
    if kind=='edge' then direction='l'
    elseif kind=='floating' then active.floating=true
    elseif kind=='fullscreen' then active.fullscreen=1
    elseif kind=='client_fullscreen' then active.fullscreen_client=1
    elseif kind=='scratch' then active.workspace.id=-1
    elseif kind=='master' then active.layout.name='master'
    elseif kind=='unmapped' then active.mapped=false
    elseif kind=='absent' then active=nil
    elseif kind=='other_workspace' then windows[2].workspace.id=2
    elseif kind=='floating_neighbor' then windows[2].floating=true
    else windows[2].fullscreen=1 end
    shortcuts.pair(direction);assert(calls==0 and fit==0,kind)
end
setup(3);fail=true
local original=active
assert(not pcall(shortcuts.pair,'l'))
assert(active==original and fit==0 and not no_warps and follow_mouse==2)
'''
        subprocess.run(
            ["lua", "-", str(ROOT / "native/home/files/.config/hypr/scrolling_shortcuts.lua")],
            input=script, text=True, check=True,
        )

    def test_column_operations(self):
        script = r'''
local active, windows, calls
hl = {
    get_active_window = function() return active end,
    get_windows = function() return windows end,
    dsp = {layout = function(message) return message end,
        window = {move = function(options) return options.direction end}},
    dispatch = function(action)
        table.insert(calls, action)
        if action == 'u' or action == 'd' then
            local layout = active.layout
            local i = layout.index_in_column + 1
            local j = i + (action == 'u' and -1 or 1)
            local order = layout.column.windows
            assert(j >= 1 and j <= #order, 'must never move beyond column')
            order[i], order[j] = order[j], order[i]
            layout.index_in_column = j - 1
        end
    end,
}
local shortcuts = dofile(arg[1])
local function setup(index, count)
    calls = {}
    active = {mapped=true, floating=false, workspace={id=1}}
    local order = {}
    for i=1,count do order[i] = i == index+1 and active or tostring(i) end
    active.layout = {name='scrolling', index_in_column=index,
        column={index=1, windows=order}}
    windows = {active}
end
setup(0,3); shortcuts.reorder('u')
assert(table.concat(calls,',') == 'd,d')
assert(active.layout.column.windows[1]=='2' and active.layout.column.windows[2]=='3')
assert(active.layout.column.windows[3]==active)
setup(2,3); shortcuts.reorder('d')
assert(table.concat(calls,',') == 'u,u')
assert(active.layout.column.windows[1]==active)
assert(active.layout.column.windows[2]=='1' and active.layout.column.windows[3]=='2')
setup(1,3); shortcuts.reorder('u'); assert(table.concat(calls,',')=='u')
setup(1,3); shortcuts.reorder('d'); assert(table.concat(calls,',')=='d')
setup(0,1); shortcuts.reorder('u'); shortcuts.reorder('d')
shortcuts.extract('l'); shortcuts.extract('r'); assert(#calls==0)
setup(1,3); shortcuts.extract('l'); shortcuts.extract('r')
assert(table.concat(calls,',')=='consume_or_expel prev,consume_or_expel next')
setup(0,2); shortcuts.transfer('l'); shortcuts.transfer('r'); assert(#calls==0)
local neighbor={mapped=true, floating=false, workspace={id=2},
    layout={name='scrolling', column={index=2}}}
table.insert(windows,neighbor)
shortcuts.transfer('r'); assert(#calls==0) -- other workspace
neighbor.workspace.id=1; neighbor.floating=true
shortcuts.transfer('r'); assert(#calls==0)
neighbor.floating=false; neighbor.layout.column.index=3
shortcuts.transfer('r'); assert(#calls==0) -- not adjacent
neighbor.layout.column.index=2; shortcuts.transfer('r'); assert(calls[1]=='r')
calls={}; neighbor.layout.column.index=0; shortcuts.transfer('l'); assert(calls[1]=='l')
for _,kind in ipairs({'floating','master','unmapped','absent'}) do
    setup(0,2)
    if kind=='floating' then active.floating=true
    elseif kind=='master' then active.layout.name='master'
    elseif kind=='unmapped' then active.mapped=false
    else active=nil end
    shortcuts.reorder('u'); shortcuts.transfer('l'); shortcuts.extract('r')
    assert(#calls==0)
end
'''
        subprocess.run(
            ["lua", "-", str(ROOT / "native/home/files/.config/hypr/scrolling_shortcuts.lua")],
            input=script, text=True, check=True,
        )

    def test_monitor_handoff_and_wrap(self):
        script = r'''
local a={name='A',x=0,y=0,dpms_status=true,active_workspace={id=1,tiled_layout='scrolling'}}
local b={name='B',x=1000,y=0,dpms_status=true,active_workspace={id=2,tiled_layout='scrolling'}}
local w={mapped=true,floating=false,fullscreen=0,workspace=a.active_workspace,monitor=a}
w.layout={name='scrolling',column={index=1,windows={w}}}
local neighbor={mapped=true,floating=false,workspace=a.active_workspace,
    layout={name='scrolling',column={index=0}}}
local calls, monitors={}, {b,a} -- enumeration is deliberately not screen order
package.preload.scrolling_widths=function() return {refresh=function() end} end
package.preload.scrolling_gaps=function() return {update=function() end} end
hl={get_active_window=function() return w end,get_windows=function() return {w,neighbor} end,
    get_monitors=function() return monitors end,
    dsp={layout=function(s) return s end,focus=function(o) return {focus=o.window} end,
        window={move=function(o) return o end}},
    dispatch=function(action)
        calls[#calls+1]=action
        if type(action)=='string' then
            w.layout.column.index=w.layout.column.index+(action=='swapcol l' and -1 or 1)
        elseif action.workspace then
            w.workspace=action.workspace==1 and a.active_workspace or b.active_workspace
            w.monitor=action.workspace==1 and a or b
            w.layout.column.index=0
        end
    end}
local shortcuts=dofile(arg[1])
shortcuts.move_column('l');assert(calls[1]=='swapcol l' and w.monitor==a)
calls={};shortcuts.move_column('l');assert(calls[1].workspace==2 and w.monitor==b)
calls={};shortcuts.move_column('r');assert(calls[1].workspace==1 and w.layout.column.index==0)
w.layout.column.index=1;calls={};shortcuts.move_column('r')
assert(calls[1].workspace==2 and calls[1].follow)
-- One monitor wraps within its own flow by rotating past the other columns.
monitors={a};w.monitor=a;w.workspace=a.active_workspace;w.layout.column.index=1;calls={}
shortcuts.move_column('r');assert(calls[1]=='swapcol l' and w.layout.column.index==0)
-- Scratch, fullscreen and non-scrolling destinations are not transferred.
monitors={a,b};calls={};w.workspace={id=-1};shortcuts.move_column('r');assert(#calls==0)
w.workspace=a.active_workspace;w.fullscreen=1;shortcuts.move_column('l');assert(#calls==0)
w.fullscreen=0;b.active_workspace.tiled_layout='master';shortcuts.move_column('l');assert(#calls==0)
'''
        subprocess.run(['lua', '-', str(ROOT / 'native/home/files/.config/hypr/scrolling_shortcuts.lua')],
                       input=script, text=True, check=True)
