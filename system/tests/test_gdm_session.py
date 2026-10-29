import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tests'))
import native_render
"""Exercise the client GDM session checker and installer in a temporary tree."""
import configparser
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "../native/tasks/system/run_58-hyprland-gdm-session.fish.j2"
ENTRY = ROOT / "../native/tasks/assets/system/templates/hyprland-uwsm.desktop"


@unittest.skipUnless(
    all(shutil.which(name) for name in ("render-native", "fish", "desktop-file-validate")),
    "render-native, fish and desktop-file-validate are required",
)
class GdmSessionTests(unittest.TestCase):
    def test_client_session_checker_and_installer(self):
        for host, client, deferred in (("li", True, False), ("li", True, True),
                                       ("fi", True, False), ("fi", True, True),
                                       ("si", False, False)):
            with self.subTest(host=host, deferred=deferred), tempfile.TemporaryDirectory() as tmp:
                work = Path(tmp)
                target = work / "installed/hyprland-uwsm.desktop"
                calls = work / "install-calls"
                config = work / "config.toml"
                config.write_text("[data]\nisClient = " + str(client).lower() + "\n")
                rendered = subprocess.run(
                    ["render-native", "--config", str(config), "--source", str(ROOT), "execute-template"],
                    input=HOOK.read_text(), text=True, capture_output=True, check=True,
                ).stdout.replace("/usr/local/share/wayland-sessions/hyprland-uwsm.desktop", str(target))
                script = work / "hook.fish"
                script.write_text(rendered)
                subprocess.run(["fish", "--no-config", "--no-execute", str(script)], check=True)
                sudo = work / "sudo"
                sudo.write_text("""#!/usr/bin/python3
import os
from pathlib import Path
import subprocess
import sys
assert sys.argv[1:7] == ['-n', 'install', '-D', '-C', '-m', '644'], sys.argv
assert sys.argv[-1] == os.environ['TEST_SESSION_TARGET'], sys.argv
with Path(os.environ['TEST_INSTALL_CALLS']).open('a') as log:
    log.write('install\\n')
raise SystemExit(subprocess.call(['/usr/bin/install', '-D', '-C', '-m', '644', sys.argv[-2], sys.argv[-1]]))
""")
                sudo.chmod(0o755)
                stat = work / "stat"
                stat.write_text("""#!/usr/bin/python3
import os
from pathlib import Path
import stat
import sys
assert sys.argv[1:3] == ['-c', '%a:%u:%g'], sys.argv
assert sys.argv[3] == os.environ['TEST_SESSION_TARGET'], sys.argv
print(f"{stat.S_IMODE(Path(sys.argv[3]).stat().st_mode):o}:" + os.environ.get('TEST_OWNER_IDS', '0:0'))
""")
                stat.chmod(0o755)
                env = dict(os.environ, PATH=str(work) + os.pathsep + os.environ["PATH"],
                           TEST_SESSION_TARGET=str(target), TEST_INSTALL_CALLS=str(calls),
                           FLEET_DEFER_SYSTEM_HOOKS="1" if deferred else "0", TJIKUP_COLOR="0")
                env.pop("TJIKUP_REPORT_FILE", None)
                command = ["fish", "--no-config", str(script)]

                def run():
                    return subprocess.run(command, env=env, text=True, capture_output=True, check=True).stdout

                first = run()
                if not client:
                    self.assertFalse(target.exists())
                    self.assertFalse(calls.exists())
                    self.assertEqual(first, "")
                    continue
                self.assertIn("CONFIG", first)
                self.assertEqual(target.read_bytes(), ENTRY.read_bytes())
                parsed = configparser.ConfigParser()
                parsed.read(target)
                self.assertEqual(shlex.split(parsed["Desktop Entry"]["Exec"]),
                                 ["uwsm", "start", "-g", "-1", "-e", "-D", "Hyprland", "hyprland.desktop"])
                before = target.stat().st_mtime_ns
                self.assertIn("SKIP", run())
                self.assertEqual(target.stat().st_mtime_ns, before)
                self.assertEqual(calls.read_text().splitlines(), ["install"])
                target.write_text("stale entry\n")
                self.assertIn("CONFIG", run())
                self.assertEqual(target.read_bytes(), ENTRY.read_bytes())
                target.chmod(0o600)
                self.assertIn("CONFIG", run())
                self.assertEqual(target.stat().st_mode & 0o777, 0o644)
                env["TEST_OWNER_IDS"] = "1000:1000"
                self.assertIn("CONFIG", run())
                self.assertEqual(len(calls.read_text().splitlines()), 4)
