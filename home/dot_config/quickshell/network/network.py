"""Small JSON/stdin bridge to NetworkManager. No shell or secrets in argv."""

import json
import os
import re
import subprocess
import sys


def nmcli(*args, password=None):
    result = subprocess.run(
        ["nmcli", "--colors", "no", "--wait", "25", *args],
        input=(password + "\n") if password is not None else "",
        capture_output=True,
        text=True,
        timeout=30,
        env={**os.environ, "LC_ALL": "C"},
    )
    if result.returncode:
        error = result.stderr.strip() or "NetworkManager could not complete the request."
        if password:
            error = error.replace(password, "[redacted]")
        raise RuntimeError(error)
    return result.stdout.rstrip("\n")


def fields(line):
    """Decode nmcli's escaped colons and backslashes, including SSIDs."""
    result, value, escaped = [], "", False
    for char in line:
        if escaped:
            value += char
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ":":
            result.append(value)
            value = ""
        else:
            value += char
    result.append(value)
    return result


def rows(columns, *args):
    return [fields(line) for line in nmcli("-t", "-f", columns, *args).splitlines() if line]


def address_details(output):
    devices, current = {}, None
    for line in output.splitlines():
        key, separator, value = line.partition(":")
        if not separator:
            continue
        if key == "GENERAL.DEVICE":
            current = dict(ip=[], ipv6=[], gateway="", dns=[], dhcp="")
            devices[value] = current
        elif current is not None:
            if key.startswith("IP4.ADDRESS["):
                current["ip"].append(value)
            elif key.startswith("IP6.ADDRESS["):
                current["ipv6"].append(value)
            elif key == "IP4.GATEWAY":
                current["gateway"] = value
            elif key.startswith("IP4.DNS["):
                current["dns"].append(value)
            elif key.startswith("DHCP4.OPTION["):
                option, _, address = value.partition(" = ")
                if option == "dhcp_server_identifier":
                    current["dhcp"] = address
    return devices


def module_bounds(bar):
    """GTK reports window-relative bounds even when Wayland hides global ones."""
    try:
        import gi
        gi.require_version("Atspi", "2.0")
        from gi.repository import Atspi
        Atspi.set_timeout(300, 500)

        def labels(node, depth=0):
            if node.get_role_name() == "label" and node.get_name().startswith(("\uf1eb", "\uf6ff")):
                rect = node.get_extents(Atspi.CoordType.WINDOW)
                if rect.x >= 0 and rect.width > 0:
                    yield dict(x=rect.x, width=rect.width)
            if depth < 8:
                for index in range(node.get_child_count()):
                    yield from labels(node.get_child_at_index(index), depth + 1)

        desktop = Atspi.get_desktop(0)
        matches = []
        for index in range(desktop.get_child_count()):
            app = desktop.get_child_at_index(index)
            if app.get_name() != "waybar" or app.get_process_id() != bar.get("pid"):
                continue
            for child in range(app.get_child_count()):
                frame = app.get_child_at_index(child)
                rect = frame.get_extents(Atspi.CoordType.WINDOW)
                if rect.width == bar["w"] and rect.height == bar["h"]:
                    matches.extend(labels(frame))
        return matches[0] if len(matches) == 1 else None
    except Exception:
        # Accessibility is optional; the click itself remains a useful anchor.
        return None


def placement(cursor, monitors, layers, locate_module=None):
    """Anchor to the clicked bar in compositor logical coordinates."""
    for monitor in monitors:
        width, height = monitor["width"], monitor["height"]
        if monitor.get("transform", 0) % 2:
            width, height = height, width
        scale = monitor.get("scale", 1)
        width, height = width / scale, height / scale
        if not (monitor["x"] <= cursor["x"] < monitor["x"] + width
                and monitor["y"] <= cursor["y"] < monitor["y"] + height):
            continue
        bars = [layer for level in layers.get(monitor["name"], {}).get("levels", {}).values()
                for layer in level if layer.get("namespace") in ("waybar", "desktop-status", "laptop")]
        clicked = next((bar for bar in bars if bar["x"] <= cursor["x"] <= bar["x"] + bar["w"]
                        and bar["y"] <= cursor["y"] <= bar["y"] + bar["h"]), None)
        candidates = [clicked] if clicked else bars
        if locate_module is not None:
            for bar in candidates:
                bounds = locate_module(bar)
                if bounds:
                    return dict(screen=monitor["name"],
                                x=bar["x"] - monitor["x"] + bounds["x"] + bounds["width"] / 2,
                                bottom=bar["y"] - monitor["y"])
        return dict(screen=monitor["name"], x=cursor["x"] - monitor["x"],
                    bottom=clicked["y"] - monitor["y"] if clicked else height - 60)
    return {}


def anchor():
    def hyprctl(command):
        return json.loads(subprocess.check_output(["hyprctl", "-j", command], text=True, timeout=3))
    try:
        return placement(hyprctl("cursorpos"), hyprctl("monitors"), hyprctl("layers"), module_bounds)
    except (OSError, ValueError, subprocess.SubprocessError):
        return {}


def snapshot():
    devices = []
    for interface, kind, state, connection in rows("DEVICE,TYPE,STATE,CONNECTION", "device", "status"):
        if kind in ("wifi", "ethernet"):
            devices.append(dict(interface=interface, kind=kind, state=state, connection=connection))
    enabled = nmcli("radio", "wifi") == "enabled"
    networks = {}
    if enabled and any(device["kind"] == "wifi" for device in devices):
        for active, ssid, bssid, signal, security, interface in rows(
            "IN-USE,SSID,BSSID,SIGNAL,SECURITY,DEVICE", "device", "wifi", "list", "--rescan", "no"
        ):
            if not ssid:
                continue
            item = dict(ssid=ssid, bssid=bssid, signal=int(signal or 0), security="" if security == "--" else security,
                        interface=interface, active=active == "*")
            key = (interface, ssid, security)
            old = networks.get(key)
            if old is None or (item["active"], item["signal"]) > (old["active"], old["signal"]):
                networks[key] = item
    details = address_details(nmcli("-t", "-f", "GENERAL.DEVICE,IP4.ADDRESS,IP4.GATEWAY,IP4.DNS,DHCP4.OPTION,IP6.ADDRESS", "device", "show"))
    for device in devices:
        device["addresses"] = details.get(device["interface"], {})
    return dict(enabled=enabled, devices=devices,
                networks=sorted(networks.values(), key=lambda item: (not item["active"], -item["signal"], item["ssid"])))


def execute(request):
    action = request.get("action", "status")
    if action == "scan":
        nmcli("device", "wifi", "rescan")
    elif action == "radio":
        if not isinstance(request.get("enabled"), bool):
            raise ValueError("A Wi-Fi radio state is required.")
        nmcli("radio", "wifi", "on" if request["enabled"] else "off")
    elif action in ("connect", "disconnect", "ethernet"):
        interface = request.get("interface", "")
        if not interface or interface.startswith("-"):
            raise ValueError("Select a network interface.")
        if action == "connect":
            bssid = request.get("bssid", "")
            if not re.fullmatch(r"(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}", bssid):
                raise ValueError("Select a visible Wi-Fi network and try again.")
            password = request.get("password", "")
            if any(char in password for char in "\r\n\x00"):
                raise ValueError("The password must be a single line.")
            # --ask reads a missing secret from stdin; it never enters the command line.
            # An empty password lets NetworkManager reuse the saved connection secrets.
            args = (["--ask"] if password else []) + ["device", "wifi", "connect", bssid, "ifname", interface]
            nmcli(*args, password=password if password else None)
        else:
            nmcli("device", "disconnect" if action == "disconnect" else "connect", interface)
    elif action != "status":
        raise ValueError("Unknown networking action.")


def main():
    try:
        request = json.loads(sys.stdin.readline())
        execute(request)
        print(json.dumps(dict(ok=True, **snapshot())))
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        message = "NetworkManager timed out. Check the connection and retry." if isinstance(error, subprocess.TimeoutExpired) else str(error)
        print(json.dumps(dict(ok=False, error=message)))


if __name__ == "__main__":
    if sys.argv[1:] == ["anchor"]:
        print(json.dumps(anchor()))
    else:
        main()
