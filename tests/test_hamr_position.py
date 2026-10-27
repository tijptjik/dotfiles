"""Render the real Hamr templates and exercise the hook without live services."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
HOME_SOURCE = REPO / "home"
HOOK = HOME_SOURCE / ".chezmoiscripts/run_onchange_after_74-hamr-position.py.tmpl"


@unittest.skipUnless(shutil.which("chezmoi"), "chezmoi is required to render templates")
class HamrPositionTests(unittest.TestCase):
    def test_centering_preserves_state_and_second_run_is_noop(self):
        for laptop, monitor, height in [(False, "DP-1", 1440), (True, "eDP-1", 1200)]:
            with self.subTest(monitor=monitor), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source = root / "source"
                templates = source / ".chezmoitemplates"
                templates.mkdir(parents=True)
                shutil.copy(HOME_SOURCE / ".chezmoitemplates/hamr-y-ratio", templates)
                config = root / "chezmoi.toml"
                config.write_text("")
                data = {"isClient": True, "isDesktop": not laptop, "isLaptop": laptop}

                def render(path):
                    return subprocess.check_output(
                        ["chezmoi", "--config", str(config), "--source", str(source),
                         "--override-data", json.dumps(data), "execute-template"],
                        input=path.read_text(), text=True,
                    )

                ratio = json.loads(render(HOME_SOURCE / "dot_config/hamr/config.json.tmpl"))["appearance"]["launcherYRatio"]
                self.assertEqual(int(ratio * height), (height - 682) // 2)
                hook = root / "hook.py"
                hook.write_text(render(HOOK))
                state = root / "state/hamr/states.json"
                state.parent.mkdir(parents=True)
                original = {"launcher": {"compactMode": True, "monitorPositions": {
                    "other": {"xRatio": 0.2, "yRatio": 0.3}}}, "pinnedPanels": [{"id": "keep"}]}
                state.write_text(json.dumps(original))
                binary = root / "bin"
                binary.mkdir()
                systemctl = binary / "systemctl"
                systemctl.write_text(
                    f"#!{sys.executable}\nimport json, os, pathlib, sys\n"
                    "with open(os.environ['CALL_LOG'], 'a') as log: log.write(' '.join(sys.argv[1:]) + '\\n')\n"
                    "if 'stop' in sys.argv:\n"
                    " p = pathlib.Path(os.environ['STATE_FILE']); data = json.loads(p.read_text())\n"
                    " data['shutdownFlush'] = True; p.write_text(json.dumps(data))\n"
                )
                systemctl.chmod(0o755)
                log = root / "calls"
                env = {**os.environ, "PATH": f"{binary}:{os.environ['PATH']}",
                       "XDG_STATE_HOME": str(root / "state"), "STATE_FILE": str(state),
                       "CALL_LOG": str(log)}
                subprocess.run([sys.executable, str(hook)], env=env, check=True)
                expected = original
                expected["launcher"]["monitorPositions"][monitor] = {"xRatio": 0.5, "yRatio": ratio}
                expected["shutdownFlush"] = True
                self.assertEqual(json.loads(state.read_text()), expected)
                calls = log.read_text()
                self.assertIn("--user stop hamr-gtk.service", calls)
                self.assertIn("--user start hamr-gtk.service", calls)
                subprocess.run([sys.executable, str(hook)], env=env, check=True)
                self.assertEqual(log.read_text(), calls)


if __name__ == "__main__":
    unittest.main()
