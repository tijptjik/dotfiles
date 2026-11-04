import native_render
"""The persisted TV selection is read on every compositor config load."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DisplayModeTests(unittest.TestCase):
    def test_game_and_desktop_survive_repeated_config_loads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.json"
            config.write_text(json.dumps({"data": {"isDesktop": True, "isLaptop": False}}))
            rendered = subprocess.check_output([
                "render-native", "--config", str(config), "--source", tmp,
                "--persistent-state", str(root / "render-native.db"), "execute-template", "-f",
                str(ROOT / "native/home/files/.config/hypr/monitors.lua.j2"),
            ], text=True)
            state = root / "hypr/display-mode"
            state.parent.mkdir()
            harness = 'local getenv=os.getenv; os.getenv=function(k) if k == "HOME" then return '+json.dumps(tmp)+' end return getenv(k) end; hl = {monitor = function(m) if m.output == "HDMI-A-1" then print(m.disabled and "desktop" or "game") end end}\n'
            for mode in ("desktop", "game", "desktop"):
                if mode == "game":
                    state.write_text("game\n")
                else:
                    state.unlink(missing_ok=True)
                for _ in range(2):
                    result = subprocess.run(["lua", "-"], input=harness + rendered,
                                            text=True, capture_output=True, check=True,
                                            env={**os.environ, "XDG_STATE_HOME": tmp})
                    self.assertEqual(result.stdout.strip(), mode)


    def test_confirmed_overrides_load_after_defaults_for_each_host(self):
        loader = Path.home() / "code/tjikos/apps/bartjik/hypr/monitors.lua"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            installed = root / ".local/lib/bartjik/hypr/monitors.lua"
            installed.parent.mkdir(parents=True)
            installed.write_bytes(loader.read_bytes())
            preferences = root / "config/bartjik/monitors.lua"
            preferences.parent.mkdir(parents=True)
            preferences.write_text('return {{output="HDMI-A-1", disabled=false}, {output="DP-2", scale=2}}\n')
            for host in ("fi", "li", "si"):
                config = root / "context.json"
                config.write_text(json.dumps({"data": {"isDesktop": host == "fi", "isLaptop": host == "li", "isServer": host == "si"}}))
                rendered = subprocess.check_output([
                    "render-native", "--config", str(config), "execute-template", "-f",
                    str(ROOT / "native/home/files/.config/hypr/monitors.lua.j2"),
                ], text=True)
                harness = "local getenv=os.getenv; os.getenv=function(k) if k == 'HOME' then return " + json.dumps(tmp) + " end return getenv(k) end\n"
                harness += 'local rules={}; hl={monitor=function(m) local r=rules[m.output] or {}; for k,v in pairs(m) do r[k]=v end; rules[m.output]=r end}\n'
                check = '\nassert(rules["HDMI-A-1"].disabled == false); assert(rules["DP-2"].scale == 2)\n'
                if host == "fi":
                    check += 'assert(rules["DP-1"].bitdepth == 10); assert(rules["DP-2"].mode == "1920x1080@74.97")\n'
                subprocess.run(["lua", "-"], input=harness + rendered + check,
                               text=True, capture_output=True, check=True,
                               env={**os.environ, "XDG_STATE_HOME": tmp, "XDG_CONFIG_HOME": str(root / "config")})


if __name__ == "__main__":
    unittest.main()
