"""Lua navigation must not resize other columns or change fullscreen state."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('lua'), 'Lua required')
class ScrollingGapsTests(unittest.TestCase):
    def test_navigation_and_width_dispatch_without_workspace_mutations(self):
        script = r'''
local active, windows
local trace={}
hl={
    get_active_window=function() return active end,
    get_windows=function() return windows end,
    dsp={layout=function(msg) return msg end,focus=function() return 'monitor' end},
    dispatch=function(action) table.insert(trace,action) end,
    workspace_rule=function() error('workspace gaps must remain fixed') end,
}
local function window(width,index,id)
    return {mapped=true,floating=false,workspace={id=id or 9},
        layout={name='scrolling',column={width=width,index=index}}}
end
local policy=dofile(arg[1])
local wide,narrow,far=window(1,0),window(.5,1),window(.75,2)
active=wide;windows={far,narrow,wide}
policy.focus('r');assert(table.concat(trace,',')=='focus r')
trace={};policy.focus('l');assert(table.concat(trace,',')=='monitor')
active=narrow;trace={};policy.focus('l');assert(table.concat(trace,',')=='focus l')
active=far;trace={};policy.focus('r');assert(table.concat(trace,',')=='monitor')
for _,width in ipairs({1,.75,.5,.25}) do
    trace={};policy.resize(width)
    assert(table.concat(trace,',')=='colresize '..tostring(width))
end
-- Another workspace must not be treated as an adjacent column.
active=wide;windows={wide,window(.5,1,18)};trace={}
policy.focus('r');assert(table.concat(trace,',')=='monitor')
for _,kind in ipairs({'floating','special','master','absent'}) do
    active=window(.5,0)
    if kind=='floating' then active.floating=true
    elseif kind=='special' then active.workspace.id=-99
    elseif kind=='master' then active.layout.name='master'
    else active=nil end
    trace={};policy.resize(1);policy.update();assert(#trace==0)
end
'''
        subprocess.run(['lua', '-', str(ROOT / 'home/dot_config/hypr/scrolling_gaps.lua')],
                       input=script, text=True, check=True)
