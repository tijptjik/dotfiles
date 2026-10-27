"""Fleet routing must not depend on DNS or replay remote commands."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("fleet_ssh", ROOT / "home/dot_local/lib/fleet_ssh.py")
fleet = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fleet)


def status(state="Running"):
    return {"BackendState": state, "Peer": {"peer": {
        "DNSName": "li.example.ts.net.",
        "TailscaleIPs": ["100.81.165.103", "fd7a:115c:a1e0::4c2f:a568"],
    }}}


class FleetSshTests(unittest.TestCase):
    def test_stopped_enrolled_node_is_resumed_and_prefers_ipv6(self):
        with patch.object(fleet.shutil, "which", return_value="/usr/bin/tailscale"), \
             patch.object(fleet, "tailnet_status", side_effect=[status("Stopped"), status()]), \
             patch.object(fleet, "output") as output:
            addresses = fleet.tailnet_addresses("li")
        self.assertEqual(addresses[0], "fd7a:115c:a1e0::4c2f:a568")
        output.assert_called_once_with(["tailscale", "up"], timeout=20)

    def test_missing_daemon_is_started_without_password_prompt(self):
        with patch.object(fleet.shutil, "which", return_value="tailscale"), \
             patch.object(fleet, "tailnet_status", side_effect=[{}, status()]), \
             patch.object(fleet, "output") as output:
            self.assertTrue(fleet.tailnet_addresses("li"))
        output.assert_called_once_with(["sudo", "-n", "systemctl", "start", "tailscaled"], timeout=10)

    def test_login_required_never_enrolls_implicitly(self):
        with patch.object(fleet.shutil, "which", return_value="tailscale"), \
             patch.object(fleet, "tailnet_status", return_value=status("NeedsLogin")), \
             patch.object(fleet, "output") as output:
            self.assertEqual(fleet.tailnet_addresses("li"), [])
        output.assert_not_called()

    def test_ambiguous_peer_names_are_rejected(self):
        peers = status()
        peers["Peer"]["duplicate"] = peers["Peer"]["peer"].copy()
        with patch.object(fleet.shutil, "which", return_value="tailscale"), \
             patch.object(fleet, "tailnet_status", return_value=peers):
            self.assertEqual(fleet.tailnet_addresses("li"), [])

    def test_avahi_ipv6_uses_returned_interface_scope(self):
        data = {"data": [3, 1, "li.local", 1, "fe80::1234", 4]}
        with patch.object(fleet.shutil, "which", return_value="busctl"), \
             patch.object(fleet, "output", return_value=json.dumps(data)) as output, \
             patch.object(fleet.socket, "if_indextoname", return_value="wifi0"):
            self.assertEqual(next(fleet.lan_addresses("li")), "fe80::1234%wifi0")
        self.assertIn("--", output.call_args.args[0])

    def test_unreachable_tailnet_falls_back_to_lan(self):
        with patch.object(fleet, "tailnet_addresses", return_value=["fd7a::1"]), \
             patch.object(fleet, "lan_addresses", return_value=["fe80::1%wifi0"]), \
             patch.object(fleet, "reachable", side_effect=[False, True]):
            self.assertEqual(fleet.resolve("li", "auto"), ("LAN", "fe80::1%wifi0"))

    def test_forced_lan_does_not_activate_tailnet(self):
        with patch.object(fleet, "tailnet_addresses") as tailnet, \
             patch.object(fleet, "lan_addresses", return_value=["192.168.1.235"]), \
             patch.object(fleet, "reachable", return_value=True):
            self.assertEqual(fleet.resolve("li", "lan")[0], "LAN")
        tailnet.assert_not_called()

    def test_unreachable_peer_fails_without_executing_ssh(self):
        with patch.object(fleet, "tailnet_addresses", return_value=[]), \
             patch.object(fleet.os, "execvp") as execute:
            self.assertEqual(fleet.main(["--transport", "tailnet", "li", "hostname"]), 1)
        execute.assert_not_called()

    def test_single_exec_preserves_arguments_and_pins_host_identity(self):
        arguments = ["-t", "printf '%s' 'a b'; exit 7"]
        with patch.object(fleet, "resolve", return_value=("tailnet", "fd7a::1")), \
             patch.object(fleet.os, "execvp") as execute:
            fleet.main(["li", *arguments])
        execute.assert_called_once()
        command = execute.call_args.args[1]
        self.assertIn("StrictHostKeyChecking=yes", command)
        self.assertIn("HostKeyAlias=li.local", command)
        self.assertEqual(command[-3:], ["io@fd7a::1", *arguments])
