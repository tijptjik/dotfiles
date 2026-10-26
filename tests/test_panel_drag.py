"""Super-drag routing must not move a window beneath an attached panel."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


@unittest.skipUnless(shutil.which("lua"), "Lua is required")
class PanelDragTests(unittest.TestCase):
    def test_layer_hit_and_native_release(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "bartjik-panel-123.rect").write_text("100 200 420 360")
            result = subprocess.run(
                ["lua", "-"], input="""
local cursor={x=130,y=230}
local layer={pid=123,mapped=true}
local moves=0
local drag_dispatcher={}
hl={get_cursor_pos=function()return cursor end,get_layers=function()return {layer} end,
    dispatch=function(dispatcher)
        assert(dispatcher==drag_dispatcher)
        moves=moves+1
        return {}
    end,
    dsp={window={drag=function()return drag_dispatcher end}}}
local h=dofile('home/dot_config/hypr/helpers.lua')
assert(h.panel_under_pointer())
assert(h.panel_aware_drag().pass_event and moves==0)
cursor.x=600
h.panel_aware_drag();assert(moves==1)
cursor.x=130
h.panel_aware_drag();assert(moves==2)
assert(h.panel_aware_drag().pass_event and moves==2)
cursor.x=100;cursor.y=200;assert(not h.panel_under_pointer())
cursor.x=130;cursor.y=230;layer.mapped=false;assert(not h.panel_under_pointer())
print('Panel hit-test, pass-through, native drag release and rounded corners passed')
""",
                cwd=Path(__file__).resolve().parents[1],
                env={**os.environ, "XDG_RUNTIME_DIR": directory},
                text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
