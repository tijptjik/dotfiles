"""Resolve fleet SSH over the enrolled tailnet or local Avahi discovery."""

import argparse
import ipaddress
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys


class ConnectionError(RuntimeError):
    pass


def output(command, timeout=5):
    try:
        result = subprocess.run(command, text=True, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout if result.returncode == 0 else ""


def tailnet_status():
    try:
        return json.loads(output(["tailscale", "status", "--json"]) or "{}")
    except ValueError:
        return {}


def tailnet_addresses(host):
    if not shutil.which("tailscale"):
        return []
    status = tailnet_status()
    if not status:
        # The daemon may be installed but not started. Never prompt for sudo
        # or enroll a new device as a side effect of an SSH shortcut.
        output(["sudo", "-n", "systemctl", "start", "tailscaled"], timeout=10)
        status = tailnet_status()
    if status.get("BackendState") == "Stopped":
        print("fleet-ssh: reconnecting the local tailnet", file=sys.stderr)
        output(["tailscale", "up"], timeout=20)
        status = tailnet_status()
    if status.get("BackendState") != "Running":
        return []
    peers = [status.get("Self", {}), *status.get("Peer", {}).values()]
    matches = [peer for peer in peers
               if peer.get("DNSName", "").split(".")[0] == host]
    if len(matches) != 1:
        return []
    addresses = matches[0].get("TailscaleIPs", [])
    # Mullvad's LAN allowance includes IPv6 ULA, but not IPv4 CGNAT space.
    return sorted(addresses, key=lambda address: ipaddress.ip_address(address).version != 6)


def lan_addresses(host):
    addresses = []
    if shutil.which("busctl"):
        # Query over IPv6 first: some Wi-Fi APs drop IPv4 multicast between
        # SSIDs. Avahi returns the interface index needed for link-local SSH.
        for protocol in (1, 0):
            raw = output([
                "busctl", "--system", "--timeout=2", "--json=short", "call", "--",
                "org.freedesktop.Avahi", "/", "org.freedesktop.Avahi.Server",
                "ResolveHostName", "iisiu", "-1", str(protocol), host + ".local", "-1", "0",
            ], timeout=3)
            try:
                interface, _, _, _, address, _ = json.loads(raw)["data"]
                if ipaddress.ip_address(address).is_link_local and ":" in address:
                    address += "%" + socket.if_indextoname(interface)
                addresses.append(address)
            except (ValueError, KeyError, OSError, TypeError):
                continue
            # Yield immediately rather than wait for a failing IPv4 lookup.
            yield address
    for line in output(["getent", "ahosts", host + ".local"], timeout=3).splitlines():
        address = line.split()[0]
        if address not in addresses:
            addresses.append(address)
            yield address


def reachable(address):
    try:
        with socket.create_connection((address, 22), timeout=2):
            return True
    except OSError:
        return False


def resolve(host, transport):
    sources = []
    if transport != "lan":
        sources.append(("tailnet", lambda: tailnet_addresses(host)))
    if transport != "tailnet":
        sources.append(("LAN", lambda: lan_addresses(host)))
    for name, addresses in sources:
        for address in addresses():
            if reachable(address):
                return name, address
    raise ConnectionError(
        f"{host} has no reachable SSH address via {transport}. "
        "Check that the remote device is awake, tailscale is up, and sshd is running. "
        "For a new/expired enrollment, run tailscale up locally first."
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transport", choices=["auto", "lan", "tailnet"],
                        default=os.environ.get("FLEET_SSH_TRANSPORT", "auto"))
    parser.add_argument("host", choices=["fi", "li"])
    parser.add_argument("ssh_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.transport not in {"auto", "lan", "tailnet"}:
        parser.error("FLEET_SSH_TRANSPORT must be auto, lan, or tailnet")
    try:
        transport, address = resolve(args.host, args.transport)
    except ConnectionError as error:
        print(f"fleet-ssh: {error}", file=sys.stderr)
        return 1
    known_hosts = Path.home() / ".config/fleet-ssh/known_hosts"
    print(f"fleet-ssh: {args.host} via {transport} ({address})", file=sys.stderr)
    command = [
        "ssh", "-x", "-o", "ConnectTimeout=10", "-o", "ServerAliveInterval=30",
        "-o", "ServerAliveCountMax=3", "-o", "StrictHostKeyChecking=yes",
        "-o", "HostKeyAlias=" + args.host + ".local",
        "-o", f"UserKnownHostsFile={known_hosts} {Path.home() / '.ssh/known_hosts'}",
        "io@" + address, *args.ssh_args,
    ]
    # Execute once. Auth failures and remote command failures must never rerun
    # the user's command on a second transport.
    os.execvp(command[0], command)


if __name__ == "__main__":
    raise SystemExit(main())
