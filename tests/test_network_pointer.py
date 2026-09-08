"""Pointer/bar hit testing without moving the real pointer."""

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "home/dot_config/quickshell/network"))
import pointer


class PointerTests(unittest.TestCase):
    def test_hidden_bar_does_not_use_retained_module_bounds(self):
        monitors = [dict(name="DP-1", x=0, y=0)]
        layers = {"DP-1": {"levels": {"1": [dict(namespace="waybar", x=0, y=100, w=900, h=30)]}}}
        def locate(bar):
            self.fail("Hidden bars must not even query accessibility")
        self.assertIsNone(pointer.hover_anchor(dict(x=100, y=110), monitors, layers, locate, visible=False))

    def test_visibility_requires_explicit_controller_state(self):
        with patch.dict(pointer.os.environ, {"XDG_RUNTIME_DIR": "/tmp"}):
            for state in ("hidden", "", "visible\n"):
                with patch.object(pointer.Path, "read_text", return_value=state):
                    self.assertFalse(pointer.waybar_visible())
            with patch.object(pointer.Path, "read_text", return_value="visible"):
                self.assertTrue(pointer.waybar_visible())
            with patch.object(pointer.Path, "read_text", side_effect=FileNotFoundError):
                self.assertFalse(pointer.waybar_visible())

    def test_fades_match_hyprland_duration_and_curve(self):
        settings = [dict(name="fadeLayersOut", overridden=True, speed=5, enabled=True, bezier="ease"),
                    dict(name="fade", overridden=True, speed=7, enabled=True, bezier="ease")]
        curves = [dict(name="ease", X0=.22, Y0=1, X1=.36, Y1=1)]
        fades = pointer.fade_settings([settings, curves])
        self.assertEqual(fades["out"], dict(duration=500, curve=[.22, 1, .36, 1, 1, 1]))
        self.assertEqual(fades["in"]["duration"], 700)
        settings[0]["enabled"] = False
        self.assertEqual(pointer.fade_settings([settings, curves])["out"]["duration"], 0)

    def test_hover_is_limited_to_network_module(self):
        monitors = [dict(name="DP-2", x=3440, y=720, width=1920, height=1080)]
        layers = {"DP-2": {"levels": {"1": [dict(namespace="desktop-status", pid=123,
                                                              x=3800, y=1740, w=900, h=40)]}}}
        locate = lambda bar: dict(x=200, width=120)
        self.assertEqual(pointer.hover_anchor(dict(x=4050, y=1750), monitors, layers, locate),
                         dict(screen="DP-2", x=620, bottom=1020))
        for cursor in (dict(x=3999, y=1750), dict(x=4120, y=1750), dict(x=4050, y=1739)):
            self.assertIsNone(pointer.hover_anchor(cursor, monitors, layers, locate))

    def test_missing_accessibility_bounds_do_not_open_on_other_modules(self):
        monitors = [dict(name="DP-1", x=0, y=0)]
        layers = {"DP-1": {"levels": {"1": [dict(namespace="waybar", x=0, y=100, w=900, h=30)]}}}
        self.assertIsNone(pointer.hover_anchor(dict(x=100, y=110), monitors, layers, lambda bar: None))

    def test_rotated_scaled_monitor_coordinates(self):
        self.assertEqual(pointer.logical_monitors([dict(name="portrait", x=1920, y=0,
                                                        width=3840, height=2160, scale=2, transform=1)]),
                         [dict(name="portrait", x=1920, y=0, width=1080, height=1920)])


if __name__ == "__main__":
    unittest.main()
