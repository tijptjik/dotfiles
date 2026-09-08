"""Network parsing and credential transport, without changing real connections."""

import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
SOURCE = Path(__file__).resolve().parents[1] / "home/dot_config/quickshell/network/network.py"
SPEC = importlib.util.spec_from_file_location("network", SOURCE)
network = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(network)


class NetworkingTests(unittest.TestCase):
    def test_escaped_ssid_and_bssid(self):
        self.assertEqual(
            network.fields(r"*:Cafe\: A\\B:AA\:BB\:CC\:DD\:EE\:FF:80:WPA2:wlan0"),
            ["*", "Cafe: A\\B", "AA:BB:CC:DD:EE:FF", "80", "WPA2", "wlan0"],
        )

    def test_connected_ap_wins_over_stronger_duplicate(self):
        def fake_nmcli(*args, **kwargs):
            if args == ("radio", "wifi"):
                return "enabled"
            if args[-2:] == ("device", "status"):
                return "wlan0:wifi:connected:Cafe\neno1:ethernet:unavailable:\nlo:loopback:connected:lo"
            return (
                r"*:Cafe:AA\:BB\:CC\:DD\:EE\:01:30:WPA2:wlan0" + "\n" +
                r":Cafe:AA\:BB\:CC\:DD\:EE\:02:90:WPA2:wlan0" + "\n" +
                r":Public:AA\:BB\:CC\:DD\:EE\:03:95:--:wlan0" + "\n" +
                r"::AA\:BB\:CC\:DD\:EE\:04:99:WPA2:wlan0"
            )

        with patch.object(network, "nmcli", side_effect=fake_nmcli):
            state = network.snapshot()
        self.assertEqual(len(state["devices"]), 2)
        self.assertEqual([item["ssid"] for item in state["networks"]], ["Cafe", "Public"])
        self.assertEqual(state["networks"][0]["signal"], 30)
        self.assertEqual(state["networks"][1]["security"], "")

    def test_disabled_radio_does_not_scan(self):
        with patch.object(network, "nmcli", side_effect=["wlan0:wifi:unavailable:", "disabled", "GENERAL.DEVICE:wlan0"]) as command:
            state = network.snapshot()
        self.assertFalse(state["enabled"])
        self.assertEqual(state["networks"], [])
        self.assertEqual(command.call_count, 3)

    def test_dhcp_server_is_distinct_from_gateway_and_dns(self):
        details = network.address_details(
            "GENERAL.DEVICE:wlan0\nIP4.ADDRESS[1]:192.168.1.100/24\n"
            "IP4.GATEWAY:192.168.1.1\nIP4.DNS[1]:192.168.1.2\nIP4.DNS[2]:1.1.1.1\n"
            "DHCP4.OPTION[1]:dhcp_server_identifier = 192.168.1.3\n"
            "IP6.ADDRESS[1]:fe80::1234/64\nGENERAL.DEVICE:eno1\nIP4.GATEWAY:\n"
        )
        self.assertEqual(details["wlan0"]["dhcp"], "192.168.1.3")
        self.assertEqual(details["wlan0"]["gateway"], "192.168.1.1")
        self.assertEqual(details["wlan0"]["dns"], ["192.168.1.2", "1.1.1.1"])
        self.assertEqual(details["wlan0"]["ipv6"], ["fe80::1234/64"])
        self.assertEqual(details["eno1"]["dhcp"], "")

    def test_click_anchor_uses_bar_top_and_monitor_offset(self):
        monitors = [dict(name="DP-2", x=3440, y=720, width=1920, height=1080, scale=1)]
        layers = {"DP-2": {"levels": {"3": [dict(namespace="waybar", x=3440, y=1746, w=620, h=34)]}}}
        self.assertEqual(network.placement(dict(x=3700, y=1760), monitors, layers),
                         dict(screen="DP-2", x=260, bottom=1026))

    def test_scaled_monitor_uses_logical_height_for_fallback(self):
        monitors = [dict(name="eDP-1", x=0, y=0, width=3840, height=2160, scale=2)]
        self.assertEqual(network.placement(dict(x=1000, y=100), monitors, {}),
                         dict(screen="eDP-1", x=1000, bottom=1020))

    def test_exact_label_center_includes_modules_before_wifi(self):
        monitors = [dict(name="DP-1", x=0, y=0, width=3440, height=1440, scale=1)]
        layers = {"DP-1": {"levels": {"1": [dict(namespace="desktop-status", x=2304, y=1387, w=1136, h=33)]}}}
        self.assertEqual(network.placement(dict(x=2670, y=1400), monitors, layers,
                                          lambda bar: dict(x=359, width=148)),
                         dict(screen="DP-1", x=2737, bottom=1387))

    def test_terminal_launch_still_locates_the_network_module(self):
        monitors = [dict(name="DP-1", x=0, y=0, width=3440, height=1440, scale=1)]
        layers = {"DP-1": {"levels": {"1": [dict(namespace="desktop-status", x=2304, y=1387, w=1136, h=33)]}}}
        self.assertEqual(network.placement(dict(x=1200, y=400), monitors, layers,
                                          lambda bar: dict(x=359, width=148)),
                         dict(screen="DP-1", x=2737, bottom=1387))

    def test_password_and_shell_characters_only_travel_over_stdin(self):
        secret = "a secret $(touch /tmp/not-a-command) `id` : \\"
        result = subprocess.CompletedProcess([], 0, "connected\n", "")
        with patch.object(network.subprocess, "run", return_value=result) as command:
            network.execute(dict(action="connect", interface="wlan0", bssid="AA:BB:CC:DD:EE:FF", password=secret))
        args, kwargs = command.call_args
        self.assertNotIn(secret, args[0])
        self.assertIn("--ask", args[0])
        self.assertEqual(kwargs["input"], secret + "\n")
        self.assertFalse(kwargs.get("shell", False))

    def test_existing_connection_does_not_prompt_for_a_new_password(self):
        with patch.object(network.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "", "")) as command:
            network.execute(dict(action="connect", interface="wlan0", bssid="AA:BB:CC:DD:EE:FF", password=""))
        self.assertNotIn("--ask", command.call_args.args[0])
        self.assertEqual(command.call_args.kwargs["input"], "")

    def test_credentials_are_redacted_from_errors(self):
        result = subprocess.CompletedProcess([], 4, "", "Failed: secret-value")
        with patch.object(network.subprocess, "run", return_value=result):
            with self.assertRaisesRegex(RuntimeError, r"Failed: \[redacted\]"):
                network.nmcli("--ask", password="secret-value")

    def test_invalid_targets_and_multiline_passwords_never_run(self):
        base = dict(action="connect", interface="wlan0", bssid="AA:BB:CC:DD:EE:FF")
        for override in ({"bssid": "--help"}, {"interface": "--help"}, {"password": "first\nsecond"}, {"action": "unknown"}):
            with self.subTest(override=override), patch.object(network, "nmcli") as command:
                with self.assertRaises(ValueError):
                    network.execute({**base, **override})
                command.assert_not_called()


if __name__ == "__main__":
    unittest.main()
