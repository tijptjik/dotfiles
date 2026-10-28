"""Persist intent without starting an intentionally stopped idle daemon."""

import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "home/dot_local/bin/executable_idle-inhibit"
loader = importlib.machinery.SourceFileLoader("idle_inhibit", str(HELPER))
spec = importlib.util.spec_from_loader(loader.name, loader)
idle = importlib.util.module_from_spec(spec)
loader.exec_module(idle)


class IdleInhibitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.state = self.home / ".local/state/idle-inhibit/state"
        self.active = True
        self.running = False
        self.calls = []
        home = patch.object(idle.Path, "home", return_value=self.home)
        run = patch.object(idle.subprocess, "run", side_effect=self.command)
        home.start()
        run.start()
        self.addCleanup(home.stop)
        self.addCleanup(run.stop)

    def command(self, args, **kwargs):
        self.calls.append(args)
        code = 0
        if args[0] == "pgrep":
            code = 0 if self.running else 1
        elif "is-active" in args:
            code = 0 if self.active else 3
        elif args[0] == "pkill":
            self.running = False
            code = 1
        elif "start" in args:
            # systemd runs this before starting; no lock recursion is allowed.
            self.assertEqual(self.invoke("check"), 0)
            self.running = True
        return subprocess.CompletedProcess(args, code)

    def invoke(self, action):
        with patch.object(idle.sys, "argv", [str(HELPER), action]):
            return idle.main()

    def test_adopt_running_and_stopped_session_without_starting(self):
        for running in (False, True):
            with self.subTest(running=running):
                self.state.unlink(missing_ok=True)
                self.calls.clear()
                self.running = running
                self.invoke("init")
                self.assertEqual(self.state.read_text().strip(), "off" if running else "on")
                self.assertFalse(any("start" in call for call in self.calls))

    def test_headless_install_retains_default(self):
        self.active = False
        self.invoke("init")
        self.assertEqual(self.invoke("check"), 0)

    def test_apply_preserves_saved_choice_even_when_session_changes(self):
        self.invoke("init")
        self.active = False
        self.running = True
        self.calls.clear()
        self.invoke("init")
        self.assertEqual(self.calls, [])
        self.assertEqual(self.invoke("check"), 1)

    def test_bar_toggle_persists_and_controls_service(self):
        self.invoke("toggle")
        self.assertTrue(self.running)
        self.assertEqual(self.state.read_text().strip(), "off")
        self.invoke("toggle")
        self.assertFalse(self.running)
        self.assertEqual(self.invoke("check"), 1)
        self.assertIn(["systemctl", "--user", "stop", "hypridle.service"], self.calls)

    def test_explicit_on_and_off(self):
        self.invoke("on")
        self.assertEqual(self.invoke("check"), 1)
        self.invoke("off")
        self.assertEqual(self.invoke("check"), 0)
        self.assertTrue(self.running)

    def test_invalid_state_is_not_silently_overwritten(self):
        self.state.parent.mkdir(parents=True)
        self.state.write_text("invalid")
        with self.assertRaises(ValueError):
            self.invoke("init")

    def test_waits_for_unmanaged_process_before_starting(self):
        # First query is toggle's current state; subsequent queries wait for
        # the old daemon to release its Wayland connection and IPC socket.
        with patch.object(idle, "running", side_effect=[False, True, False]), patch.object(idle.time, "sleep") as sleep:
            self.invoke("toggle")
        sleep.assert_called_once_with(0.05)
        self.assertTrue(self.running)


class IdlePolicyRenderingTests(unittest.TestCase):
    def test_host_rendering_and_apply_does_not_start_hypridle(self):
        for host in ("fi", "li", "si"):
            with self.subTest(host=host), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                config = root / "config.json"
                config.write_text(json.dumps({"data": {
                    "isDesktop": host == "fi", "isLaptop": host == "li",
                    "isClient": host != "si", "isServer": host == "si",
                }}))
                def render(source):
                    return subprocess.check_output([
                        "chezmoi", "--config", str(config), "--source", tmp,
                        "--persistent-state", str(root / "state.db"),
                        "execute-template", "-f", str(ROOT / source),
                    ], text=True)
                script = render("home/.chezmoitemplates/tjikup/run_after_99-systemd-reload.fish.tmpl")
                subprocess.run(["fish", "--no-config", "-n"], input=script, text=True, check=True)
                self.assertEqual('idle-inhibit" init' in script, host != "si")
                if host == "si":
                    continue
                # Execute the idle setup and generic client helper path with
                # all services missing, the case that formerly undid inhibition.
                section = script[script.index('# Adopt the current idle choice'):script.index('# Voice capture belongs')]
                bindir = root / ".local/bin"
                bindir.mkdir(parents=True)
                stub = bindir / "idle-inhibit"
                stub.write_text('#!/bin/sh\necho "idle-inhibit $*"\n')
                stub.chmod(0o755)
                (bindir / "nightlight").symlink_to(stub)
                harness = '''
function systemctl
    if contains -- is-enabled $argv; return 1; end
    if contains -- is-active $argv; return 0; end
    if contains -- show-environment $argv; echo WAYLAND_DISPLAY=wayland-1; return 0; end
    echo (string join ' ' -- $argv)
end
function user_units_need_reload; return 0; end
function status_msg; end
function stage_note; $argv[5..-1]; end
'''
                result = subprocess.run(["fish", "--no-config"], input=harness + section,
                                        text=True, capture_output=True, check=True,
                                        env={**os.environ, "HOME": tmp})
                self.assertIn("idle-inhibit init", result.stdout)
                self.assertIn("--user enable hypridle.service", result.stdout)
                self.assertNotIn("--user start hypridle.service", result.stdout)
                self.assertNotIn("--user start hyprsunset.service", result.stdout)
                self.assertIn("--user start hyprpaper.service", result.stdout)
                bar = json.loads(render("home/dot_config/bartjik/config.json.tmpl"))
                self.assertEqual(bar["modules"]["idle"]["actions"]["leftClick"][-1], "toggle")
                self.assertTrue(bar["modules"]["filter"]["actions"]["leftClick"][0].endswith("/nightlight"))


class NightlightTests(IdleInhibitTests):
    # Reuse only the fixture and command fake, with nightlight's positive
    # on/off semantics checked separately from idle inhibition.
    def invoke(self, action):
        with patch.object(idle.sys, "argv", ["nightlight", action]):
            return idle.main()

    def setUp(self):
        super().setUp()
        self.state = self.home / ".local/state/nightlight/state"

    def test_adopt_running_and_stopped_session_without_starting(self):
        for running in (False, True):
            self.state.unlink(missing_ok=True)
            self.running = running
            self.invoke("init")
            self.assertEqual(self.state.read_text().strip(), "on" if running else "off")
            self.assertEqual(self.invoke("check"), 0 if running else 1)
        self.assertFalse(any("start" in call for call in self.calls))

    def test_apply_preserves_saved_choice_even_when_session_changes(self):
        self.invoke("init")
        self.active = False
        self.running = True
        self.calls.clear()
        self.invoke("init")
        self.assertEqual(self.calls, [])
        self.assertEqual(self.invoke("check"), 1)

    def test_bar_toggle_persists_and_controls_service(self):
        self.invoke("toggle")
        self.assertTrue(self.running)
        self.assertEqual(self.state.read_text().strip(), "on")
        self.invoke("toggle")
        self.assertFalse(self.running)
        self.assertEqual(self.invoke("check"), 1)
        self.assertIn(["systemctl", "--user", "stop", "hyprsunset.service"], self.calls)

    def test_explicit_on_and_off(self):
        self.invoke("on")
        self.assertEqual(self.invoke("check"), 0)
        self.assertTrue(self.running)
        self.invoke("off")
        self.assertEqual(self.invoke("check"), 1)
        self.assertFalse(self.running)


if __name__ == "__main__":
    unittest.main()
