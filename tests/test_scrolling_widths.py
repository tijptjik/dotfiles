"""Monitor arrivals reuse ordered native width matches without changing focus."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('lua'), 'Lua required')
class ScrollingWidthTests(unittest.TestCase):
    def test_arrivals_and_exclusions(self):
        script = r'''
local events, rules, actions, timer = {}, {}, {}, nil
local a={name='A',width=2000,height=1200,scale=2,transform=0,reserved={left=0,right=0}}
local b={name='B',width=1000,height=680,scale=1,transform=0,reserved={left=0,right=0}}
local w={address='one',mapped=true,floating=false,workspace={id=1},monitor=a,
    fullscreen=0,fullscreen_client=0,tags={'arrival-width-1*'},
    layout={name='scrolling',column={width=.5}}}
local active=w
a.active_workspace={id=1};b.active_workspace={id=19}
package.preload.scrolling_gaps=function() return {update=function() end,resize=function(width) actions[#actions+1]="colresize "..width end} end
hl={window_rule=function(r) rules[#rules+1]=r end,
    get_active_monitor=function() return a end,get_cursor_pos=function() return {x=17,y=23} end,
    get_windows=function() return {w} end,get_active_window=function() return active end,
    exec_scheduled_prop_refresh_immediately=function() end,
    on=function(e,f) events[e]=f; return {} end,
    timer=function(f,o) assert(o.timeout==1);timer=f; return {} end,
    dsp={layout=function(s) return s end,focus=function(s) return s end,cursor={move=function(s) return s end}},
    dispatch=function(s) actions[#actions+1]=s end}
local widths=dofile(arg[1])
widths.rule({match={class='kitty'},scrolling_width=.5})
widths.rule({match={class='kitty',workspace='m[B]'},scrolling_width=.75})
assert(rules[4].tag=='+arrival-width-2')
widths.start();assert(#actions==0)
w.workspace.id=2;events['window.move_to_workspace']();timer();assert(#actions==0)
w.monitor=b;w.tags={'arrival-width-1*','arrival-width-2*'}
events['window.move_to_workspace']();assert(#actions==0);timer()
assert(actions[1]=='colresize 0.75')
widths.refresh();assert(#actions==1) -- no repeated enforcement
w.layout.column.width=.75;w.monitor=a;w.workspace.id=1;w.tags={'arrival-width-1*'}
active=nil;events['window.move_to_workspace']();timer()
assert(actions[2].window==w and actions[3]=='colresize 0.5')
assert(actions[4].workspace==1 and actions[5].x==17 and actions[5].y==23)
actions={}
-- Scratch visits do not replace the last ordinary monitor.
w.workspace.id=-1;w.monitor=b;widths.refresh();assert(#actions==0)
w.workspace.id=1;w.monitor=a;widths.refresh();assert(#actions==0)
for _,kind in ipairs({'floating','fullscreen','unknown','master'}) do
 w.monitor=a; widths.refresh();w.monitor=b
 w.floating=kind=='floating';w.fullscreen=kind=='fullscreen' and 1 or 0
 w.tags=kind=='unknown' and {} or {'arrival-width-1*'}
 w.layout.name=kind=='master' and 'master' or 'scrolling'
 local before=#actions;widths.refresh();assert(#actions==before)
 w.floating=false;w.fullscreen=0;w.layout.name='scrolling'
end
'''
        subprocess.run(['lua', '-', str(ROOT / 'native/home/files/.config/hypr/scrolling_widths.lua')],
                       input=script, text=True, check=True)
