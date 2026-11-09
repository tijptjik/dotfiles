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
    get_workspaces=function() return {a.active_workspace,b.active_workspace} end,
    get_active_monitor=function() return a end,get_cursor_pos=function() return {x=17,y=23} end,
    get_windows=function() return {w} end,get_active_window=function() return active end,
    exec_scheduled_prop_refresh_immediately=function() end,
    on=function(e,f) events[e]=f; return {} end,
    timer=function(f,o) assert(o.timeout==1);timer=f; return {} end,
    dsp={layout=function(s) return s end,focus=function(s)
        -- Hyprland accepts workspace handles/selectors, not numeric IDs.
        if s.workspace ~= nil then
            assert(type(s.workspace)=='string', 'workspace handles may expire during mirror changes')
        end
        return s
    end,cursor={move=function(s) return s end}},
    dispatch=function(s) actions[#actions+1]=s end}
local widths=dofile(arg[1])
widths.rule({match={class='kitty'},scrolling_width=.5})
widths.rule({match={class='kitty',workspace='m[B]'},scrolling_width=.75})
assert(rules[4].tag=='+arrival-width-2')
widths.start();assert(#actions==0)
-- Special workspace handles have no numeric ID in Hyprland 0.57.
-- Ignore them on open/start/refresh without losing the last ordinary monitor.
local ordinary=w.workspace
w.workspace={name='special:chat',special=true};w.monitor=b
events['window.open'](w);widths.refresh();assert(#actions==0)
w.workspace=ordinary;w.monitor=a
w.workspace.id=2;events['window.move_to_workspace']();timer();assert(#actions==0)
w.monitor=b;w.tags={'arrival-width-1*','arrival-width-2*'}
events['window.move_to_workspace']();assert(#actions==0);timer()
assert(actions[1]=='colresize 0.75')
widths.refresh();assert(#actions==1) -- no repeated enforcement
w.layout.column.width=.75;w.monitor=a;w.workspace.id=1;w.tags={'arrival-width-1*'}
active=nil;events['window.move_to_workspace']();timer()
assert(actions[2].window==w and actions[3]=='colresize 0.5')
assert(actions[4].workspace=="1" and actions[5].x==17 and actions[5].y==23)
actions={}
-- Restore the destination's visible workspace and the original active window.
local original={mapped=true}
active=original;w.monitor=b;w.workspace={id=20}
widths.refresh()
assert(actions[1].window==w and actions[2]=='colresize 0.5')
assert(actions[3].workspace=="19" and actions[4].window==original)
assert(actions[5].x==17 and actions[5].y==23)
actions={}
-- Named workspaces have no numeric ID; retain their handle when restoring.
active=nil;a.active_workspace={name='named'};w.monitor=a
widths.refresh()
assert(actions[3].workspace=="name:named" and actions[4].workspace=="name:named")
assert(actions[5].x==17 and actions[5].y==23)
a.active_workspace={id=1};w.workspace={id=1}
actions={}
-- A drag crosses monitors while temporarily floating; resize after the drop.
w.monitor=a;widths.refresh();actions={}
w.floating=true;w.monitor=b;w.tags={'arrival-width-1*','arrival-width-2*'}
events['window.move_to_workspace']();timer();assert(#actions==0)
w.floating=false;w.layout.column.width=.5;active=w
-- Dropping has no second workspace move event.
events['window.update_state'](w,{float=false});timer()
assert(#actions==1 and actions[1]=='colresize 0.75')
actions={};w.layout.column.width=.6
-- Expired workspace handles are ignored rather than passed to hl.focus.
local old_dispatch=hl.dispatch
local expired=setmetatable({}, {__index=function() error('workspace object is expired') end})
a.active_workspace=expired
w.monitor=a;active=nil
widths.refresh()
for _, action in ipairs(actions) do
 if type(action)=='table' then assert(action.workspace==nil) end
end
a.active_workspace={id=1};hl.dispatch=old_dispatch;actions={}

widths.refresh();assert(#actions==0) -- Later manual resizing remains intact.
w.monitor=a;widths.refresh();actions={}
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

    def test_routed_startup_width_is_applied_once(self):
        script = r'''
local events, timer, actions = {}, nil, {}
local a={name='A',active_workspace={id=1}}
local b={name='B',active_workspace={id=11}}
local original={mapped=true}
local w={address='new',mapped=true,floating=false,workspace={id=1},monitor=a,
    fullscreen=0,fullscreen_client=0,tags={'arrival-width-1*'},
    layout={name='scrolling',column={width=.5}}}
local windows={}
package.preload.scrolling_gaps=function() return {
    update=function() end,
    resize=function(width) w.layout.column.width=width;actions[#actions+1]=width end,
} end
hl={window_rule=function() end,get_windows=function() return windows end,
    get_active_window=function() return original end,get_workspaces=function() return {a.active_workspace,b.active_workspace} end,
    get_active_monitor=function() return a end,
    get_cursor_pos=function() return {x=17,y=23} end,
    exec_scheduled_prop_refresh_immediately=function()
        w.monitor=b;w.workspace=b.active_workspace
        w.tags={'arrival-width-1*','arrival-width-2*'}
    end,
    on=function(event,callback) events[event]=callback;return {} end,
    timer=function(callback) timer=callback;return {} end,
    dsp={focus=function(target) return target end,cursor={move=function(pos) return pos end}},
    dispatch=function(action) actions[#actions+1]=action end}
local widths=dofile(arg[1])
widths.rule({match={class='kitty'},scrolling_width=.5})
widths.rule({match={class='kitty',workspace='m[B]'},scrolling_width=1})
widths.start()
windows={w};events['window.open'](w)
assert(#actions==0) -- Wait until routing and native rule tags have settled.
timer()
assert(w.layout.column.width==1)
assert(actions[1].window==w and actions[2]==1)
assert(actions[3].window==original and actions[4].x==17 and actions[4].y==23)
w.layout.column.width=.75;actions={}
widths.refresh();events['window.move_to_workspace']();timer()
assert(#actions==0 and w.layout.column.width==.75) -- Preserve later manual resizing.
-- A window closed before the callback must not be resized.
events['window.open'](w);events['window.close'](w);windows={};timer()
assert(#actions==0)
'''
        subprocess.run(['lua', '-', str(ROOT / 'native/home/files/.config/hypr/scrolling_widths.lua')],
                       input=script, text=True, check=True)
