import runpy
from pathlib import Path
import unittest


reveal_commands = runpy.run_path(str(Path(__file__).resolve().parents[1] /
    "native/home/files/.local/bin/show-codex"))["reveal_commands"]


class ShowCodexTests(unittest.TestCase):
    def test_reveal_is_idempotent_and_uses_window_monitor(self):
        clients = [{"class": "Chatgpt", "address": "0x123", "monitor": 2,
                    "workspace": {"name": "special:codex"}}]
        monitor = {"id": 2, "name": "eDP-1", "specialWorkspace": {"name": "special:chat"}}
        hidden = reveal_commands([monitor], clients)
        self.assertIn('monitor="eDP-1"', hidden[0])
        self.assertTrue(any("toggle_special" in c for c in hidden))
        monitor["specialWorkspace"]["name"] = "special:codex"
        visible = reveal_commands([monitor], clients)
        self.assertFalse(any("toggle_special" in c for c in visible))
        self.assertIn('"0x123"', visible[-1])

    def test_missing_window_or_monitor_is_noop(self):
        self.assertEqual(reveal_commands([], []), [])
        self.assertEqual(reveal_commands([], [{"class": "Chatgpt", "monitor": 0,
            "workspace": {"name": "special:codex"}}]), [])
