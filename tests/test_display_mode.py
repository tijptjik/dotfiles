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
            harness = 'hl = {monitor = function(m) if m.output == "HDMI-A-1" then print(m.disabled and "desktop" or "game") end end}\n'
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


if __name__ == "__main__":
    unittest.main()
